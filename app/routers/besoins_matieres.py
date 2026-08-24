"""
MyStock — Besoins matières
==========================

Calcule les besoins en matières premières à partir des dossiers de production
au planning (statut 'attente' ou 'en_cours'). S'appuie sur :

- `planning_entries` : les dossiers, avec dates prévues (planned_start/end,
  date_livraison) et lien vers `of_imports` (qte_etiquettes à produire).
- `fiches_techniques` : jointes via `ref_produit_norm` avec tie-breaker
  machine — même logique que `app/routers/planning.py` (l. 3238+).
- `mp_fiche_mapping` (v215) : table de correspondance éditable entre les
  champs texte des fiches (support, glassine, adhesif, mandrin_dia, cartons,
  palette_type) et les références de `matieres_premieres`.

Unités de besoin (révision « unités métier ») :
- matières en bobine (frontal / complexe via `support`, et `glassine`) → mètres
  linéaires (ml) : c'est le métrage de l'OF qui traverse la machine, identique
  pour toutes les bobines d'un même dossier.
- adhésif → kilos : surface enduite × grammage.
- mandrins / cartons / palettes → unités (inchangé).

Formules :
- métrage (ml)  : of_imports.metrage — la quantité d'étiquettes à produire est
                  portée par l'OF, donc le métrage aussi. Repli géométrique
                  quand l'OF n'est pas importé :
                  qte_etiquettes / mod_nb_front * mod_longueur / 1000
- support  (ml) : métrage
- glassine (ml) : métrage
- adhésif  (kg) : grammage(g/m²) * métrage(m) * laize(mm)/1000 / 1000
                  grammage = matieres_premieres.weight_gsm (saisi sur la fiche
                  matière), repli fiches_techniques.qte_au_mille
                  laize    = of_imports.laize, repli fiche technique
Postes sans matière première (repiquage) : frontal, glassine et adhésif ne
sont pas comptés — la matière a été consommée en amont. Mandrins, cartons et
palettes restent calculés : le conditionnement, lui, est bien consommé.

- mandrins (u)  : of_imports.nb_mandrins, sinon of_imports.qte_bobines,
                  sinon qte_etiquettes / nb_etiq_bobin (champ de la fiche, ou
                  nombre relu dans la phrase de conditionnement)
- cartons  (u)  : mandrins / nb_bobines_carton
- palettes (u)  : cartons / (palette_nb_cartons_sol * palette_nb_cartons_hauteur)

Chaque besoin transporte sa trace de calcul (`variables`) : la liste ordonnée
des entrées utilisées, avec leur origine (OF, fiche technique, matière) — c'est
ce que consomme le modal d'explication côté MyStock.

Fenêtre 7j / 15j : today + N comme borne. Pour un dossier à cheval sur la
borne (planned_start < borne < planned_end), on applique une règle de trois
sur la durée qui tombe dans la fenêtre.

Accès : rôles _STOCK_MATIERES_ADMIN_ROLES (voir stock.py).
"""
import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.services.carnet_snapshot import (
    agreger as agreger_carnet, capturer as capturer_carnet, capturer_si_besoin,
    couverture as couverture_carnet,
)
from app.services.coherence_fiche import (
    alerte_courte, controler as controler_fiche, nb_fronts,
)
from app.services.date_livraison import parse_date_livraison
from app.services.documents_verite import historique_document
from app.routers.stock import (
    require_stock_matieres_admin,
    require_stock_write,
    stock_config_float,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["besoins-matieres"])

_KINDS = ("support", "glassine", "adhesif", "mandrin", "carton", "palette")

# Unité de besoin par kind. Les bobines se comptent en mètres linéaires,
# l'adhésif au kilo, le reste à l'unité.
_KIND_UNITE = {
    "support": "ml",
    "glassine": "ml",
    "adhesif": "kg",
    "mandrin": "u",
    "carton": "u",
    "palette": "u",
}

# Kinds dont le stock est tenu en bobines et doit être converti en ml pour être
# comparable au besoin (via matieres_premieres.metres_lineaires_par_bobine).
_KINDS_BOBINE = frozenset({"support", "glassine"})

# ── Utilitaires ─────────────────────────────────────────────────────────

def _f(v) -> Optional[float]:
    """Cast robuste en float positif (None si vide/invalide/≤0)."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_iso(s) -> Optional[date]:
    """Date d'un champ du planning, ISO ou saisie à la main.

    `date_livraison` est un champ TEXTE et le reste : c'est l'atelier qui
    l'écrit. « 07/04/2026 » et « A livrer le 03/04 » tombaient ici en None, et
    `_ratio_dans_fenetre` les comptait alors à 100 % dans TOUTES les fenêtres,
    « à 7 jours » comprise — soit 11 % des dossiers surévaluant le besoin
    court terme, sans que rien ne le signale.
    """
    return parse_date_livraison(s)


def _ratio_dans_fenetre(pe: dict, today: date, borne: date) -> float:
    """Ratio du dossier tombant dans la fenêtre [today, borne].

    Règles :
    - Dossier sans dates → ratio 1 (n'est pas encore parvenu, on compte tout).
    - Dossier en retard (fin < today) → ratio 1 (besoin immédiat).
    - Dossier entièrement avant la borne → ratio 1.
    - Dossier entièrement après la borne (start > borne) → ratio 0.
    - Dossier à cheval → proportion des jours dans la fenêtre / durée totale.
    """
    ps = _parse_iso(pe.get("planned_start"))
    pe_end = _parse_iso(pe.get("planned_end"))
    dl = _parse_iso(pe.get("date_livraison"))
    # Fallback : sans planned_end, on prend date_livraison
    if not pe_end:
        pe_end = dl
    if not ps and not pe_end:
        return 1.0  # aucune info temporelle → dossier ouvert, tout compte
    if not ps:
        # Fin connue mais pas de début : on suppose durée d'un jour
        ps = pe_end
    if not pe_end:
        pe_end = ps
    if pe_end < ps:
        pe_end = ps
    # Dossier en retard : besoin immédiat
    if pe_end < today:
        return 1.0
    # Entièrement dans la fenêtre
    if pe_end <= borne:
        return 1.0
    # Entièrement après la borne
    if ps > borne:
        return 0.0
    # À cheval : proportion
    total = (pe_end - ps).days + 1
    debut_effectif = max(ps, today)
    fin_effective = min(pe_end, borne)
    dans = (fin_effective - debut_effectif).days + 1
    return max(0.0, min(1.0, dans / total)) if total > 0 else 1.0


# ── Requête source : dossiers du planning + fiches techniques ──────────

# NOTE : l'ancienne version faisait le tie-breaker machine dans une sous-requête
# corrélée du ON (LEFT JOIN fiches_techniques ft ON ft.id = (SELECT ...)).
# SQLite refuse la référence à une colonne d'un CTE ou d'une autre table du
# FROM externe depuis cette sous-requête ("no such column: pe_ext.machine_nom"
# / "no such column: m.nom") → 500 systématique sur les 3 endpoints GET.
# On fait désormais le match fiche technique en Python : même logique que
# planning.py (l. 3261+), mais multi-machines en un seul passage.

_SQL_PE = """
    SELECT pe.id, pe.machine_id, pe.reference, pe.client, pe.description,
           pe.ref_produit, pe.ref_produit_norm, pe.numero_of, pe.statut,
           pe.planned_start, pe.planned_end, pe.date_livraison, pe.duree_heures,
           pe.position, pe.of_import_id,
           m.nom AS machine_nom,
           COALESCE(m.sans_matiere_premiere, 0) AS poste_sans_matiere,
           oi.qte_etiquettes AS qte_etiquettes,
           oi.qte_bobines    AS qte_bobines,
           oi.metrage        AS of_metrage,
           oi.laize          AS of_laize,
           -- L'OF chiffre souvent lui-meme le conditionnement : ces valeurs
           -- priment sur toute reconstitution a partir de la fiche technique.
           oi.nb_mandrins    AS of_nb_mandrins,
           oi.nb_cartons     AS of_nb_cartons,
           oi.conditionnement AS of_conditionnement,
           COALESCE(oi.valide, 0) AS of_valide,
           oi.valide_par          AS of_valide_par,
           oi.valide_at           AS of_valide_at,
           -- Pourquoi la validation est tombée. Une pastille qui repasse au
           -- rouge sans dire pourquoi sera recochée sans être relue.
           oi.invalide_at         AS of_invalide_at,
           oi.invalide_motif      AS of_invalide_motif
    FROM planning_entries pe
    LEFT JOIN machines m ON m.id = pe.machine_id
    LEFT JOIN of_imports oi ON oi.id = pe.of_import_id
    WHERE pe.statut IN ('attente', 'en_cours')
    ORDER BY COALESCE(pe.planned_start, pe.date_livraison, '9999'), pe.position
"""

_SQL_FT = """
    SELECT id, reference, ref_produit_norm, machine,
           COALESCE(valide, 0) AS valide, valide_par, valide_at,
           invalide_at, invalide_motif,
           support, glassine, adhesif, qte_au_mille, eti_laize, eti_longueur,
           mod_laize, mod_longueur, mod_nb_front, laize, laize_optimale,
           -- Le vrai nombre de fronts vit dans l'outil de découpe :
           -- `mod_nb_front` vaut 1 sur 878 fiches sur 909 (constat du
           -- 7 août 2026), `outil1_nb_front` est confirmé par la géométrie
           -- sur 868. Cf. app/services/coherence_fiche.py.
           outil1_nb_front,
           mandrin_dia, nb_etiq_bobin, nb_bobines_carton, cartons,
           conditionnement,
           palette_type, palette_nb_cartons_sol, palette_nb_cartons_hauteur
    FROM fiches_techniques
"""

_FT_FIELDS = (
    "support", "glassine", "adhesif", "qte_au_mille", "eti_laize", "eti_longueur",
    "valide", "valide_par", "valide_at", "invalide_at", "invalide_motif",
    "mod_laize", "mod_longueur", "mod_nb_front", "outil1_nb_front",
    "laize", "laize_optimale",
    "mandrin_dia", "nb_etiq_bobin", "nb_bobines_carton", "cartons",
    "conditionnement",
    "palette_type", "palette_nb_cartons_sol", "palette_nb_cartons_hauteur",
)


def _ft_key(norm, ref) -> str:
    """Clé de rapprochement fiche↔dossier : ref_produit_norm si présent,
    sinon la référence textuelle en minuscules — même COALESCE que le SQL
    d'origine et que planning.py."""
    n = (norm or "").strip()
    if n:
        return n
    return (ref or "").strip().lower()


# Même requête que _SQL_PE, mais sur un dossier précis quel que soit son statut :
# on déstocke une production terminée, donc hors du périmètre de la vue Besoins.
_SQL_PE_UN = _SQL_PE.replace(
    "WHERE pe.statut IN ('attente', 'en_cours')", "WHERE pe.id = ?"
).replace("ORDER BY COALESCE(pe.planned_start, pe.date_livraison, '9999'), pe.position", "")


def _load_dossiers(conn, sql: Optional[str] = None, params: tuple = (),
                   filtre=None) -> list:
    """Dossiers du planning (attente/en_cours) + fiche technique associée.

    Tie-breaker machine identique à planning.py : fiche dont `machine`
    correspond à la machine du dossier > fiche sans machine > autre, puis
    id croissant. Chaque dossier reçoit les champs ft_* (None si aucune fiche).

    `filtre` est appliqué aux lignes brutes, AVANT le rapprochement de fiche.
    Il ne sert que là où l'appelant sait déjà écarter la majorité des lignes
    sur un critère que SQL ne sait pas exprimer — le format des dates d'Access,
    typiquement. Le rapprochement est le poste coûteux : le faire pour des
    lignes qu'on jette ensuite double le coût de l'écran pour rien.
    """
    pes = [dict(r) for r in conn.execute(sql or _SQL_PE, params).fetchall()]
    if filtre is not None:
        pes = [pe for pe in pes if filtre(pe)]
    if not pes:
        return []
    fts = [dict(r) for r in conn.execute(_SQL_FT).fetchall()]

    by_key: dict = {}
    for ft in fts:
        by_key.setdefault(_ft_key(ft.get("ref_produit_norm"), ft.get("reference")), []).append(ft)

    for pe in pes:
        cands = by_key.get(_ft_key(pe.get("ref_produit_norm"), pe.get("ref_produit"))) or []
        best = None
        if cands:
            mach = (pe.get("machine_nom") or "").strip().lower()

            def _rank(ft):
                fm = (ft.get("machine") or "").strip().lower()
                if fm and fm == mach:
                    r = 0
                elif not fm:
                    r = 1
                else:
                    r = 2
                return (r, ft["id"])

            best = min(cands, key=_rank)
        pe["ft_id"] = best["id"] if best else None
        for f in _FT_FIELDS:
            pe[f"ft_{f}"] = best.get(f) if best else None
    return pes


def _load_mapping(conn) -> dict:
    """Retourne dict {(kind, source_value_lower): {matiere_id, reference, designation, unite_stock}}."""
    rows = conn.execute("""
        SELECT m.kind, m.source_value, m.matiere_id,
               mp.reference, mp.designation, mp.categorie,
               mp.metres_lineaires_par_bobine, mp.weight_gsm, mp.weight_per_m2,
               mp.longueur_tube_mm, mp.unites_par_palette
        FROM mp_fiche_mapping m
        JOIN matieres_premieres mp ON mp.id = m.matiere_id
    """).fetchall()
    out = {}
    for r in rows:
        keys = r.keys()
        out[(r["kind"], (r["source_value"] or "").strip().lower())] = {
            "matiere_id": r["matiere_id"],
            "reference": r["reference"],
            "designation": r["designation"],
            "categorie": r["categorie"],
            "metres_lineaires_par_bobine": (
                r["metres_lineaires_par_bobine"]
                if "metres_lineaires_par_bobine" in keys else None
            ),
            "weight_gsm": r["weight_gsm"] if "weight_gsm" in keys else None,
            "weight_per_m2": r["weight_per_m2"] if "weight_per_m2" in keys else None,
            # Mandrins : longueur du tube acheté et nombre de tubes par palette.
            # Ce sont les deux seules données qui traduisent un besoin en mandrins
            # en une commande de tubes, puis de palettes.
            "longueur_tube_mm": r["longueur_tube_mm"] if "longueur_tube_mm" in keys else None,
            "unites_par_palette": r["unites_par_palette"] if "unites_par_palette" in keys else None,
        }
    return out


def _n(v, unite: str = "") -> str:
    """Formatage court d'un nombre pour les libellés de formule."""
    if v is None:
        return "?"
    f = float(v)
    s = f"{f:,.0f}".replace(",", " ") if abs(f) >= 1000 else f"{f:g}"
    return s + (f" {unite}" if unite else "")


def _metrage_dossier(pe: dict) -> dict:
    """Métrage linéaire (m) du dossier + sa provenance.

    L'OF porte la quantité d'étiquettes à produire, donc le métrage : c'est la
    source de référence (`of_imports.metrage`). Quand le dossier n'a pas d'OF
    importé, on retombe sur la géométrie de la fiche technique :
    nb de tours = qte_etiquettes / mod_nb_front, longueur = mod_longueur (mm).

    Retourne { metrage, source ('of'|'fiche'|None), variables[], manque[] }.
    """
    of_metrage = _f(pe.get("of_metrage"))
    if of_metrage:
        return {
            "metrage": of_metrage,
            "source": "of",
            "variables": [
                {"label": "Métrage OF", "champ": "of_imports.metrage",
                 "origine": "OF", "valeur": of_metrage, "unite": "m"},
            ],
            "manque": [],
        }

    qte = _f(pe.get("qte_etiquettes"))
    mod_long = _f(pe.get("ft_mod_longueur"))

    # Le nombre de fronts est au DÉNOMINATEUR : s'y tromper d'un facteur 18
    # multiplie le besoin en frontal par 18. `mod_nb_front` valait 1 sur 878
    # fiches sur 909 — un champ que personne ne remplit, pas une valeur. Le
    # nombre de poses de l'outil de découpe est le bon, et la géométrie le
    # confirme sur 868 fiches. Cf. app/services/coherence_fiche.py.
    ft = {
        "mod_nb_front": pe.get("ft_mod_nb_front"),
        "outil1_nb_front": pe.get("ft_outil1_nb_front"),
        "mod_laize": pe.get("ft_mod_laize"),
        "laize_optimale": pe.get("ft_laize_optimale"),
        "laize": pe.get("ft_laize"),
    }
    res_front = nb_fronts(ft, pe.get("of_laize"))
    nb_front = res_front["valeur"]
    coherence = controler_fiche(ft, pe.get("of_laize"))

    if qte and nb_front and mod_long:
        return {
            "metrage": qte / nb_front * mod_long / 1000.0,
            "source": "fiche",
            "variables": [
                {"label": "Quantité étiquettes", "champ": "of_imports.qte_etiquettes",
                 "origine": "OF", "valeur": qte, "unite": "étiq"},
                {"label": "Nb de front", "champ": res_front["champ"],
                 "origine": {"outil": "Fiche technique — outil de découpe",
                             "module": "Fiche technique — module",
                             "geometrie": "Déduit de la laize"}.get(
                                 res_front["source"], "Fiche technique"),
                 "valeur": nb_front, "unite": ""},
                {"label": "Longueur module", "champ": "fiches_techniques.mod_longueur",
                 "origine": "Fiche technique", "valeur": mod_long, "unite": "mm"},
            ],
            "manque": [],
            "coherence": coherence,
            "alerte": alerte_courte(coherence),
        }

    manque = []
    if not of_metrage:
        manque.append("Métrage de l'OF (of_imports.metrage)")
    if not qte:
        manque.append("Quantité d'étiquettes de l'OF")
    if not nb_front:
        manque.append("Nb de front de la fiche technique "
                      "(outil1_nb_front, ou mod_nb_front, ou laize + mod_laize)")
    if not mod_long:
        manque.append("Longueur module de la fiche technique (mod_longueur)")
    return {"metrage": None, "source": None, "variables": [], "manque": manque,
            "coherence": coherence, "alerte": alerte_courte(coherence)}


def _laize_dossier(pe: dict) -> dict:
    """Laize retenue (mm) + provenance : l'OF d'abord, la fiche technique en repli."""
    of_laize = _f(pe.get("of_laize"))
    if of_laize:
        return {"laize": of_laize, "source": "of",
                "champ": "of_imports.laize", "origine": "OF"}
    ft_laize = _f(pe.get("ft_laize_optimale")) or _f(pe.get("ft_laize"))
    if ft_laize:
        champ = ("fiches_techniques.laize_optimale"
                 if _f(pe.get("ft_laize_optimale")) else "fiches_techniques.laize")
        return {"laize": ft_laize, "source": "fiche",
                "champ": champ, "origine": "Fiche technique"}
    return {"laize": None, "source": None, "champ": None, "origine": None}


def _matiere_ml_par_bobine(mapping: dict, kind: str, source_value: str):
    """Métrage par bobine de la matière associée à (kind, source_value)."""
    m = mapping.get((kind, (source_value or "").strip().lower()))
    return m.get("metres_lineaires_par_bobine") if m else None


# « Bobine de 1.000 étiquettes », « Bobines de 1 000 etiq. » : la phrase de
# conditionnement porte le nombre d'étiquettes par bobine bien plus souvent que
# le champ dédié de la fiche technique, laissé vide dans la plupart des fiches.
_RE_ETIQ_BOBINE = re.compile(
    r"bobines?\s*(?:de|:)?\s*(\d[\d\s\u202f\u00a0.,]*)\s*(?:é|e)tiq",
    re.IGNORECASE,
)


def _entier_fr(txt) -> Optional[int]:
    """« 1.000 », « 1 000 », « 1 000 » → 1000.

    Les séparateurs de milliers français (point, espace, espace fine) sont
    retirés sans distinction : un nombre d'étiquettes par bobine est toujours
    entier, aucun risque de confondre avec une décimale.
    """
    chiffres = re.sub(r"\D", "", str(txt or ""))
    if not chiffres:
        return None
    try:
        v = int(chiffres)
    except ValueError:
        return None
    return v if v > 0 else None


def _etiq_par_bobine(pe: dict) -> dict:
    """Étiquettes par bobine, avec sa provenance.

    Le champ dédié `nb_etiq_bobin` est vide sur beaucoup de fiches alors que la
    phrase de conditionnement porte l'information. On lit dans l'ordre : le
    champ, la phrase de la fiche, puis celle de l'OF.
    """
    v = _f(pe.get("ft_nb_etiq_bobin"))
    if v:
        return {"valeur": v, "champ": "fiches_techniques.nb_etiq_bobin",
                "origine": "Fiche technique"}
    for cle, champ, origine in (
        ("ft_conditionnement", "fiches_techniques.conditionnement",
         "Fiche technique (conditionnement)"),
        ("of_conditionnement", "of_imports.conditionnement", "OF (conditionnement)"),
    ):
        m = _RE_ETIQ_BOBINE.search(str(pe.get(cle) or ""))
        if m:
            n = _entier_fr(m.group(1))
            if n:
                return {"valeur": float(n), "champ": champ, "origine": origine}
    return {"valeur": None, "champ": None, "origine": None}


def _nb_bobines_dossier(pe: dict, qte: Optional[float]) -> dict:
    """Nombre de bobines produites — c'est aussi le nombre de mandrins consommés.

    Trois sources, de la plus directe à la plus reconstituée :
    l'OF quand il chiffre lui-même les mandrins, la quantité de bobines de l'OF,
    puis la quantité d'étiquettes divisée par les étiquettes par bobine.
    """
    n = _f(pe.get("of_nb_mandrins"))
    if n:
        return {"nb": n, "formule": f"{_n(n)} mandrins (chiffrés sur l'OF)",
                "variables": [
                    {"label": "Mandrins", "champ": "of_imports.nb_mandrins",
                     "origine": "OF", "valeur": n, "unite": "u"}],
                "manque": []}

    nb_bob = _f(pe.get("qte_bobines"))
    if nb_bob:
        return {"nb": nb_bob,
                "formule": f"{_n(nb_bob)} bobines (OF) × 1 mandrin/bobine",
                "variables": [
                    {"label": "Quantité bobines", "champ": "of_imports.qte_bobines",
                     "origine": "OF", "valeur": nb_bob, "unite": "bobines"}],
                "manque": []}

    eb = _etiq_par_bobine(pe)
    if qte and eb["valeur"]:
        return {"nb": qte / eb["valeur"],
                "formule": f"{_n(qte)} étiq ÷ {_n(eb['valeur'])} étiq/bobine",
                "variables": [
                    {"label": "Quantité étiquettes", "champ": "of_imports.qte_etiquettes",
                     "origine": "OF", "valeur": qte, "unite": "étiq"},
                    {"label": "Étiquettes par bobine", "champ": eb["champ"],
                     "origine": eb["origine"], "valeur": eb["valeur"], "unite": ""}],
                "manque": []}

    manque = []
    if not qte and not nb_bob:
        manque.append("Quantité d'étiquettes ou de bobines de l'OF")
    if not eb["valeur"]:
        manque.append("Étiquettes par bobine — champ « Nb étiq./bobine » vide sur la "
                      "fiche et phrase de conditionnement non exploitable")
    return {"nb": None, "formule": "Calcul impossible", "variables": [], "manque": manque}


def _mandrin_tubes(pe: dict, mapping: dict, nb_mandrins: float,
                   perte_pct: float) -> dict:
    """Traduit un besoin en mandrins en nombre de tubes, puis de palettes.

    Les mandrins s'achètent en tubes qu'on redécoupe à la laize du module : un
    tube de L mm rend, une fois la perte de coupe retirée, L × (1 − perte) de
    longueur utile, dont on tire des mandrins de `mod_laize` mm de haut.

    Le besoin reste exprimé en mandrins — c'est l'unité de l'atelier. Les tubes
    et les palettes sont la traduction à l'achat, affichée à côté.
    """
    vide = {"tubes": None, "palettes": None, "mandrins_par_tube": None,
            "detail_tubes": None, "manque_tubes": []}
    m = mapping.get(("mandrin", str(pe.get("ft_mandrin_dia") or "").strip().lower()))
    laize_mod = _f(pe.get("ft_mod_laize"))
    lg_tube = _f(m.get("longueur_tube_mm")) if m else None
    upp = _f(m.get("unites_par_palette")) if m else None

    manque = []
    if not laize_mod:
        manque.append("Laize module de la fiche technique (mod_laize)")
    if not lg_tube:
        manque.append("Longueur tube — à saisir sur la fiche matière mandrin")
    if not laize_mod or not lg_tube or not nb_mandrins:
        return {**vide, "manque_tubes": manque}

    utile = lg_tube * (1.0 - perte_pct / 100.0)
    if utile <= 0:
        return {**vide, "manque_tubes": ["Perte de coupe ≥ 100 % — réglage à corriger"]}

    tubes = nb_mandrins * laize_mod / utile
    palettes = tubes / upp if upp else None
    detail = (f"{_n(round(nb_mandrins, 1))} mandrins × {_n(laize_mod)} mm "
              f"÷ ({_n(lg_tube)} mm − {_n(perte_pct)} %) = "
              f"{_n(round(tubes, 1))} tubes")
    if palettes is not None:
        detail += f" ÷ {_n(upp)} tubes/palette = {_n(round(palettes, 2))} palettes"
    else:
        manque.append("Tubes par palette — à saisir sur la fiche matière mandrin")
    return {
        "tubes": round(tubes, 3),
        "palettes": round(palettes, 3) if palettes is not None else None,
        "mandrins_par_tube": round(utile / laize_mod, 2),
        "detail_tubes": detail,
        "manque_tubes": manque,
    }


def _compute_besoins_dossier(pe: dict, mapping: dict,
                             perte_pct: float = 10.0) -> list:
    """Calcule la liste des besoins MP pour un dossier de prod.

    Retourne une liste de dicts :
      { kind, source_value, matiere_id?, matiere_ref?, matiere_designation?,
        quantite, unite, mapped, formule, variables[], source_metrage? }

    `variables` est la trace de calcul : chaque entrée utilisée, son champ
    d'origine et sa valeur. C'est ce qu'affiche le modal « ? » de MyStock.
    """
    besoins = []
    qte = _f(pe.get("qte_etiquettes")) or 0

    met = _metrage_dossier(pe)
    metrage = met["metrage"]
    lz = _laize_dossier(pe)

    def _add(kind: str, source_value, quantite, formule: str,
             variables=None, manque=None, extra=None):
        # L'unité n'est pas passée par l'appelant : elle est déduite du kind,
        # pour qu'elle ne puisse pas diverger de _KIND_UNITE.
        unite = _KIND_UNITE.get(kind, "u")
        sv = (source_value or "").strip() if source_value else ""
        if not sv:
            return
        key = (kind, sv.lower())
        m = mapping.get(key)
        calculable = quantite is not None and quantite > 0
        besoins.append({
            "kind": kind,
            "source_value": sv,
            "matiere_id": m["matiere_id"] if m else None,
            "matiere_ref": m["reference"] if m else None,
            "matiere_designation": m["designation"] if m else None,
            "matiere_categorie": m["categorie"] if m else None,
            "quantite": round(quantite, 3) if calculable else None,
            "unite": unite,
            "mapped": m is not None,
            "calculable": calculable,
            "formule": formule,
            "variables": variables or [],
            "manque": manque or [],
            "source_metrage": met["source"] if kind in ("support", "glassine", "adhesif") else None,
            **(extra or {}),
        })

    # Postes sans matière première : le repiquage est un atelier, on y
    # surimprime des étiquettes déjà fabriquées. Le frontal, la glassine et
    # l'adhésif ont été consommés en amont — les recompter ici serait un
    # doublon. Le conditionnement, lui, est bien consommé : les étiquettes
    # repiquées sont rembobinées sur mandrin, mises en carton et palettisées.
    sans_mp = bool(pe.get("poste_sans_matiere"))

    # ── Bobines (frontal / complexe / glassine) : besoin en mètres linéaires ──
    # Toutes les bobines d'un dossier voient passer le même métrage.
    for kind, col in (("support", "ft_support"), ("glassine", "ft_glassine")):
        if sans_mp:
            break
        if not pe.get(col):
            continue
        # La laize voyage avec le besoin : une bobine ne se commande pas, ne se
        # stocke pas et ne se déstocke pas hors de sa laize. L'agréger sans elle
        # donnait un total juste en mètres, mais inutilisable pour commander.
        extra_lz = {"laize_mm": lz.get("laize")}
        if metrage:
            src = "métrage OF" if met["source"] == "of" else "métrage calculé fiche"
            _add(kind, pe[col], metrage,
                 f"{_n(metrage, 'm')} ({src})", met["variables"], extra=extra_lz)
        else:
            _add(kind, pe[col], None, "Métrage indisponible",
                 met["variables"], met["manque"], extra=extra_lz)

    # ── Adhésif : kilos = grammage (g/m²) × surface enduite (m²) ──
    # surface = métrage (m) × laize (mm) / 1000
    if pe.get("ft_adhesif") and not sans_mp:
        # Grammage : porté par la référence adhésif (weight_gsm, g/m²). Le champ
        # « Grammage » de la fiche technique sert de repli tant que la matière
        # n'est pas renseignée.
        mp_adh = mapping.get(("adhesif", str(pe["ft_adhesif"]).strip().lower()))
        grammage = _f(mp_adh.get("weight_gsm")) if mp_adh else None
        gram_champ = "matieres_premieres.weight_gsm"
        gram_origine = "Matière première"
        if not grammage and mp_adh:
            # weight_per_m2 est en kg/m² (base de calcul du pricing) : ×1000 → g/m².
            kg_m2 = _f(mp_adh.get("weight_per_m2"))
            if kg_m2:
                grammage = kg_m2 * 1000.0
                gram_champ = "matieres_premieres.weight_per_m2 (kg/m² × 1000)"
        if not grammage:
            grammage = _f(pe.get("ft_qte_au_mille"))
            if grammage:
                gram_champ = "fiches_techniques.qte_au_mille"
                gram_origine = "Fiche technique"
        laize = lz["laize"]
        variables = list(met["variables"])
        if laize:
            variables.append({
                "label": "Laize", "champ": lz["champ"],
                "origine": lz["origine"], "valeur": laize, "unite": "mm",
            })
        if grammage:
            variables.append({
                "label": "Grammage", "champ": gram_champ,
                "origine": gram_origine, "valeur": grammage, "unite": "g/m²",
            })
        if metrage and laize and grammage:
            surface = metrage * (laize / 1000.0)
            _add("adhesif", pe["ft_adhesif"], surface * grammage / 1000.0,
                 f"{_n(metrage, 'm')} × {_n(laize)} mm ÷ 1000 = "
                 f"{_n(round(surface, 1), 'm²')} × {_n(grammage)} g/m² ÷ 1000",
                 variables)
        else:
            manque = list(met["manque"])
            if not laize:
                manque.append("Laize de l'OF (of_imports.laize) ou de la fiche technique")
            if not grammage:
                manque.append("Grammage — à saisir sur la fiche matière adhésif "
                              "(ni weight_gsm, ni qte_au_mille renseignés)")
            _add("adhesif", pe["ft_adhesif"], None,
                 "Calcul impossible", variables, manque)

    # ── Mandrins : 1 par bobine ──
    bob = _nb_bobines_dossier(pe, qte)
    nb_mandrins = bob["nb"] or 0.0
    if pe.get("ft_mandrin_dia"):
        if bob["nb"]:
            tub = _mandrin_tubes(pe, mapping, nb_mandrins, perte_pct)
            variables = list(bob["variables"])
            formule = bob["formule"]
            if tub["tubes"] is not None:
                # La conversion en tubes n'est pas le besoin : c'est ce qu'il faut
                # commander pour le couvrir. On l'expose à côté, jamais à la place.
                mp_man = mapping.get(
                    ("mandrin", str(pe.get("ft_mandrin_dia") or "").strip().lower())) or {}
                variables += [
                    {"label": "Laize module", "champ": "fiches_techniques.mod_laize",
                     "origine": "Fiche technique", "valeur": _f(pe.get("ft_mod_laize")),
                     "unite": "mm"},
                    {"label": "Longueur tube", "champ": "matieres_premieres.longueur_tube_mm",
                     "origine": "Matière première",
                     "valeur": _f(mp_man.get("longueur_tube_mm")), "unite": "mm"},
                    {"label": "Perte de coupe", "champ": "stock_config.mandrin_perte_coupe_pct",
                     "origine": "Paramètres", "valeur": perte_pct, "unite": "%"},
                    {"label": "Mandrins par tube", "champ": "calculé",
                     "origine": "Calcul", "valeur": tub["mandrins_par_tube"], "unite": ""},
                ]
                formule += " · " + tub["detail_tubes"]
            _add("mandrin", pe["ft_mandrin_dia"], nb_mandrins, formule, variables,
                 tub["manque_tubes"] or None, extra={
                     "besoin_tubes": tub["tubes"],
                     "besoin_palettes": tub["palettes"],
                     "mandrins_par_tube": tub["mandrins_par_tube"],
                 })
        else:
            _add("mandrin", pe["ft_mandrin_dia"], None,
                 bob["formule"], bob["variables"], bob["manque"])

    # ── Cartons : chiffrés sur l'OF, sinon nb bobines / bobines par carton ──
    nb_bc = _f(pe.get("ft_nb_bobines_carton"))
    of_cart = _f(pe.get("of_nb_cartons"))
    nb_cartons = 0.0
    if pe.get("ft_cartons"):
        if of_cart:
            nb_cartons = of_cart
            _add("carton", pe["ft_cartons"], nb_cartons,
                 f"{_n(of_cart)} cartons (chiffrés sur l'OF)", [
                     {"label": "Cartons", "champ": "of_imports.nb_cartons",
                      "origine": "OF", "valeur": of_cart, "unite": "u"},
                 ])
        elif nb_bc and nb_mandrins > 0:
            nb_cartons = nb_mandrins / nb_bc
            _add("carton", pe["ft_cartons"], nb_cartons,
                 f"{nb_mandrins:.1f} bobines ÷ {_n(nb_bc)} bobines/carton", [
                     {"label": "Nb de bobines", "champ": "calculé (mandrins)",
                      "origine": "Calcul", "valeur": round(nb_mandrins, 1), "unite": "bobines"},
                     {"label": "Bobines par carton", "champ": "fiches_techniques.nb_bobines_carton",
                      "origine": "Fiche technique", "valeur": nb_bc, "unite": ""},
                 ])
        else:
            manque = []
            if nb_mandrins <= 0:
                manque.append("Nombre de bobines (dépend du calcul mandrins)")
            if not nb_bc:
                manque.append("Bobines par carton (nb_bobines_carton)")
            _add("carton", pe["ft_cartons"], None, "Calcul impossible", [], manque)


    # ── Palettes : cartons / (cartons_sol × cartons_hauteur) ──
    ncs = _f(pe.get("ft_palette_nb_cartons_sol"))
    nch = _f(pe.get("ft_palette_nb_cartons_hauteur"))
    if pe.get("ft_palette_type"):
        if ncs and nch and nb_cartons > 0:
            _add("palette", pe["ft_palette_type"], nb_cartons / (ncs * nch),
                 f"{nb_cartons:.1f} cartons ÷ ({_n(ncs)}×{_n(nch)})", [
                     {"label": "Nb de cartons", "champ": "calculé (cartons)",
                      "origine": "Calcul", "valeur": round(nb_cartons, 1), "unite": "cartons"},
                     {"label": "Cartons au sol", "champ": "fiches_techniques.palette_nb_cartons_sol",
                      "origine": "Fiche technique", "valeur": ncs, "unite": ""},
                     {"label": "Cartons en hauteur", "champ": "fiches_techniques.palette_nb_cartons_hauteur",
                      "origine": "Fiche technique", "valeur": nch, "unite": ""},
                 ])
        else:
            manque = []
            if nb_cartons <= 0:
                manque.append("Nombre de cartons (dépend du calcul cartons)")
            if not ncs or not nch:
                manque.append("Plan de palettisation (cartons au sol × en hauteur)")
            _add("palette", pe["ft_palette_type"], None,
                 "Calcul impossible", [], manque)

    return besoins


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/api/stock/besoins-matieres/par-dossier")
def besoins_par_dossier(request: Request):
    """Retourne une ligne par dossier de production (statut attente/en_cours),
    avec le détail des besoins MP calculés."""
    require_stock_matieres_admin(request)
    with get_db() as conn:
        # Photo du carnet, une fois par jour. Cet écran est ouvert tous les
        # jours ouvrés par l'administration : ça suffit à alimenter la série
        # sans dépendre d'un cron à installer sur le VPS. Best-effort et muet
        # — rien de ce qui sert à une prévision d'automne ne justifie de faire
        # échouer l'affichage des besoins d'aujourd'hui.
        capturer_si_besoin(conn)
        mapping = _load_mapping(conn)
        rows = _load_dossiers(conn)
        perte_pct = stock_config_float(conn, "mandrin_perte_coupe_pct")
    dossiers = []
    for pe in rows:
        besoins = _compute_besoins_dossier(pe, mapping, perte_pct)
        dossiers.append({
            "id": pe["id"],
            "reference": pe.get("reference"),
            "client": pe.get("client"),
            "description": pe.get("description"),
            "ref_produit": pe.get("ref_produit"),
            "numero_of": pe.get("numero_of"),
            "machine_nom": pe.get("machine_nom"),
            "statut": pe.get("statut"),
            "planned_start": pe.get("planned_start"),
            "planned_end": pe.get("planned_end"),
            "date_livraison": pe.get("date_livraison"),
            "qte_etiquettes": pe.get("qte_etiquettes"),
            "ft_id": pe.get("ft_id"),
            # La laize du dossier : c'est elle qui décide quelle bobine sortira
            # du stock, donc elle a sa place à côté des besoins.
            "laize": _laize_dossier(pe).get("laize"),
            # Les deux documents consultables depuis la vue par dossier : l'OF
            # importé et la fiche technique rapprochée.
            "of_import_id": pe.get("of_import_id"),
            # Validation humaine des deux documents : c'est elle qui autorise
            # le défalquage automatique du stock en fin de production.
            "of_valide": int(pe.get("of_valide") or 0),
            "of_valide_par": pe.get("of_valide_par"),
            "of_invalide_motif": pe.get("of_invalide_motif"),
            "ft_valide": int(pe.get("ft_valide") or 0),
            "ft_valide_par": pe.get("ft_valide_par"),
            "ft_invalide_motif": pe.get("ft_invalide_motif"),
            "destockage": pe.get("destockage") or "todo",
            "of_metrage": pe.get("of_metrage"),
            "of_laize": pe.get("of_laize"),
            # Cohérence géométrique de la fiche. Un besoin calculé sur une
            # fiche qui ne boucle pas est faux d'un facteur connu : autant le
            # dire sur la ligne plutôt que de laisser partir la commande.
            "fiche_alerte": _metrage_dossier(pe).get("alerte"),
            "besoins": besoins,
            "besoins_mapped_count": sum(1 for b in besoins if b["mapped"]),
            "besoins_total_count": len(besoins),
            "besoins_incalculables_count": sum(1 for b in besoins if not b["calculable"]),
        })
    return {"dossiers": dossiers, "count": len(dossiers)}


_SQL_PE_PASSES = _SQL_PE.replace(
    "WHERE pe.statut IN ('attente', 'en_cours')",
    "WHERE COALESCE(pe.statut, '') NOT IN ('attente', 'en_cours')"
).replace(
    "ORDER BY COALESCE(pe.planned_start, pe.date_livraison, '9999'), pe.position",
    "ORDER BY COALESCE(pe.planned_end, pe.date_livraison, '0000') DESC, pe.id DESC"
)


# ── Les mois passés : les OF scannés que le planning ne porte plus ────────
#
# `planning_entries` est un miroir du planning vivant : un dossier livré il y a
# huit mois n'y est plus. Une fenêtre de douze mois passés lue sur cette seule
# table afficherait donc des mois vides, et un mois vide se lit « on n'a rien
# produit » — exactement le contresens qu'on veut éviter.
#
# Les OF, eux, restent : `of_imports` garde chaque OF scanné, avec son délai
# client et sa référence produit — donc de quoi retrouver la fiche technique et
# recalculer le besoin exactement comme pour un dossier du planning.
#
# On ne prend QUE les OF qu'aucun dossier du planning ne porte
# (`pe.of_import_id IS NULL`) : sinon le même OF compterait deux fois, une fois
# par le planning et une fois par lui-même. La complémentarité est stricte, pas
# une préférence de source.
_SQL_OF_ORPHELINS = """
    SELECT ('of-' || oi.id)  AS id,
           NULL              AS machine_id,
           oi.reference      AS reference,
           NULL              AS client,
           NULL              AS description,
           oi.reference      AS ref_produit,
           -- Indispensable, pas cosmétique : `of_imports.reference` arrive
           -- d'Access sous sa forme longue (« 1013/0068 - COHESIO 1 »), alors
           -- que les fiches sont indexées sur la clé normalisée par le trigger
           -- `trg_ft_ref_produit_norm_*`. Sans cette normalisation les deux
           -- clés ne se rencontrent jamais, aucune fiche n'est rapprochée, et
           -- l'OF ne produit aucun besoin — en silence, puisque rien n'échoue.
           norm_ref_produit(oi.reference) AS ref_produit_norm,
           oi.of_numero      AS numero_of,
           'termine'         AS statut,
           oi.date_creation  AS planned_start,
           oi.delai_client   AS planned_end,
           oi.delai_client   AS date_livraison,
           NULL              AS duree_heures,
           0                 AS position,
           oi.id             AS of_import_id,
           oi.machine        AS machine_nom,
           COALESCE(m.sans_matiere_premiere, 0) AS poste_sans_matiere,
           oi.qte_etiquettes AS qte_etiquettes,
           oi.qte_bobines    AS qte_bobines,
           oi.metrage        AS of_metrage,
           oi.laize          AS of_laize,
           oi.nb_mandrins    AS of_nb_mandrins,
           oi.nb_cartons     AS of_nb_cartons,
           oi.conditionnement AS of_conditionnement,
           COALESCE(oi.valide, 0) AS of_valide,
           oi.valide_par          AS of_valide_par,
           oi.valide_at           AS of_valide_at,
           oi.invalide_at         AS of_invalide_at,
           oi.invalide_motif      AS of_invalide_motif,
           -- Les matières PORTÉES PAR L'OF LUI-MÊME. `access_sync_of.py` les
           -- recopie depuis la fiche Access au moment où l'OF est créé
           -- (`f.matsupport`, `f.matglassine`, `f.matadhesif`). C'est ce qui
           -- rend l'archive exploitable sans fiche technique — et c'est même
           -- la meilleure source pour un mois révolu : la fiche d'aujourd'hui
           -- a pu changer depuis, l'OF dit ce qui a réellement été engagé.
           oi.matiere        AS of_matiere,
           oi.glassine       AS of_glassine,
           oi.adhesif_label  AS of_adhesif_label,
           oi.mandrins_dia   AS of_mandrins_dia,
           oi.cartons_type   AS of_cartons_type,
           oi.qte_au_mille   AS of_qte_au_mille
    FROM of_imports oi
    LEFT JOIN machines m ON LOWER(TRIM(m.nom)) = LOWER(TRIM(oi.machine))
    LEFT JOIN planning_entries pe ON pe.of_import_id = oi.id
    WHERE pe.id IS NULL
"""


# Ce que l'OF sait dire de lui-même, et le champ de fiche technique que ça
# remplace. `_compute_besoins_dossier` ne lit QUE les champs ft_* : c'est par
# eux qu'il faut passer, sans quoi il faudrait dupliquer les six formules.
_OF_VERS_FT = (
    ("ft_support",     "of_matiere"),
    ("ft_glassine",    "of_glassine"),
    ("ft_adhesif",     "of_adhesif_label"),
    ("ft_mandrin_dia", "of_mandrins_dia"),
    ("ft_cartons",     "of_cartons_type"),
    ("ft_qte_au_mille", "of_qte_au_mille"),
)


def _matieres_depuis_of(pe: dict) -> None:
    """Fait dire à l'OF quelles matières il engage, en place.

    Mesuré le 24/08/2026 : sur 592 OF que le planning ne porte plus, 81
    seulement (13,7 %) se rapprochent d'une fiche technique — `fiches_techniques`
    ne garde que les produits actifs, pas ceux d'il y a un an. Faire dépendre
    l'archive de ce rapprochement revenait à la jeter à 86 %, et à afficher
    douze mois de courbes à plat qu'on lit comme une activité nulle.

    Or l'OF n'a besoin de personne : `access_sync_of.py` y recopie
    `f.matsupport`, `f.matglassine` et `f.matadhesif` au moment de sa création.
    La quantité, elle, continue de passer par les formules communes
    (métrage × laize × grammage) — une seconde formule pour le passé rendrait
    les deux moitiés du graphe incomparables, ce qui est précisément ce que
    l'écran sert à faire.

    L'OF PRIME sur la fiche, il ne la complète pas : sur un mois révolu, la
    fiche d'aujourd'hui a pu être corrigée depuis, alors que l'OF est le
    document qui a été produit. La fiche ne sert que là où l'OF se tait.
    """
    for champ_ft, champ_of in _OF_VERS_FT:
        v = pe.get(champ_of)
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        pe[champ_ft] = v


def _mois_of(pe: dict) -> Optional[str]:
    """Mois 'AAAA-MM' visé par un OF : son délai client, sinon sa création."""
    d = parse_date_livraison(pe.get("date_livraison")) \
        or parse_date_livraison(pe.get("planned_start"))
    return f"{d.year:04d}-{d.month:02d}" if d else None


def _load_of_orphelins(conn, depuis: Optional[str] = None) -> list:
    """OF scannés qu'aucun dossier du planning ne porte, prêts pour le calcul.

    `depuis` ('AAAA-MM') borne la fenêtre. Le tri se fait en Python plutôt que
    dans le WHERE parce que `delai_client` arrive d'Access dans plusieurs
    formats de date — une comparaison lexicale SQL y serait fausse une fois
    sur deux. Il reste appliqué avant le rapprochement de fiche technique,
    qui est le vrai poste de coût sur une table d'archive.

    Best-effort : la colonne `valide` de `of_imports` est arrivée par migration,
    et un déploiement en retard ne doit pas faire tomber la vue Tendance à 500 —
    elle rendrait alors les seuls mois que le planning couvre, ce qui est une
    dégradation lisible, pas une panne.
    """
    def _dans_fenetre(pe):
        m = _mois_of(pe)
        return bool(m) and (not depuis or m >= depuis)

    try:
        return _load_dossiers(conn, _SQL_OF_ORPHELINS, filtre=_dans_fenetre)
    except Exception:
        logger.exception("[besoins] OF orphelins illisibles — la fenêtre passée "
                         "de la vue Tendance se limitera au planning.")
        return []


@router.get("/api/stock/besoins-matieres/par-dossier-passes")
def besoins_dossiers_passes(request: Request):
    """Dossiers sortis de production : ce qui reste à déstocker, et ce qui l'est.

    La vue par dossier ne montre que la production en cours — c'est ce qu'on
    veut pour approvisionner. Mais le déstockage se fait *après*, donc sur des
    dossiers qui ont justement quitté ce périmètre : sans cette vue, ils
    devenaient introuvables.
    """
    require_stock_matieres_admin(request)
    try:
        limite = int(request.query_params.get("limit") or 300)
    except (TypeError, ValueError):
        limite = 300
    limite = max(1, min(limite, 1000))

    with get_db() as conn:
        mapping = _load_mapping(conn)
        rows = _load_dossiers(conn, _SQL_PE_PASSES)
        perte_pct = stock_config_float(conn, "mandrin_perte_coupe_pct")
        rows = rows[:limite]
        # Un seul aller-retour pour savoir qui a déstocké quoi : la modale n'a
        # pas à être ouverte pour que la liste sache ce qui est déjà sorti.
        mvts = {}
        for r in conn.execute(
            """SELECT m.planning_entry_id AS pid, COUNT(*) AS n,
                      MIN(m.created_by_name) AS qui, MIN(m.created_at) AS quand
               FROM mp_mouvements m
               WHERE m.planning_entry_id IS NOT NULL
                 AND m.type_mouvement = 'sortie'
                 -- Une sortie ne porte jamais annule_mouvement_id : c'est la
                 -- contre-passation qui la désigne. On exclut donc les sorties
                 -- *visées* par une annulation, pas celles qui en portent une —
                 -- sinon un dossier annulé continuait d'apparaître déstocké.
                 AND NOT EXISTS (SELECT 1 FROM mp_mouvements c
                                 WHERE c.annule_mouvement_id = m.id)
               GROUP BY m.planning_entry_id"""
        ).fetchall():
            mvts[int(r["pid"])] = dict(r)

    dossiers = []
    for pe in rows:
        besoins = _compute_besoins_dossier(pe, mapping, perte_pct)
        docs = _etat_documents(pe)
        m = mvts.get(int(pe["id"])) or {}
        dossiers.append({
            "id": pe["id"],
            "reference": pe.get("reference"),
            "client": pe.get("client"),
            "ref_produit": pe.get("ref_produit"),
            "numero_of": pe.get("numero_of"),
            "machine_nom": pe.get("machine_nom"),
            "statut": pe.get("statut"),
            "planned_end": pe.get("planned_end"),
            "date_livraison": pe.get("date_livraison"),
            "qte_etiquettes": pe.get("qte_etiquettes"),
            "of_import_id": pe.get("of_import_id"),
            "ft_id": pe.get("ft_id"),
            "of_valide": int(pe.get("of_valide") or 0),
            "of_valide_par": pe.get("of_valide_par"),
            "of_invalide_motif": pe.get("of_invalide_motif"),
            "ft_valide": int(pe.get("ft_valide") or 0),
            "ft_valide_par": pe.get("ft_valide_par"),
            "ft_invalide_motif": pe.get("ft_invalide_motif"),
            "destockage": pe.get("destockage") or "todo",
            "destockable": docs["complet"],
            "blocage": docs["blocage"],
            "nb_mouvements": int(m.get("n") or 0),
            "destocke_par": m.get("qui"),
            "destocke_at": m.get("quand"),
            "besoins": besoins,
            "besoins_total_count": len(besoins),
            "besoins_incalculables_count": sum(1 for b in besoins if not b["calculable"]),
        })
    return {"dossiers": dossiers, "count": len(dossiers)}


@router.get("/api/stock/besoins-matieres/par-echeance")
def besoins_par_echeance(request: Request):
    """Agrège les besoins MP par référence, avec split sous 7j / 15j / total.

    Règle de proportionnalité pour les dossiers à cheval sur la borne
    (durée dans la fenêtre / durée totale du dossier)."""
    require_stock_matieres_admin(request)
    today = date.today()
    borne_7 = today + timedelta(days=7)
    borne_15 = today + timedelta(days=15)

    with get_db() as conn:
        mapping = _load_mapping(conn)
        rows = _load_dossiers(conn)
        # Stock actuel pour comparaison.
        # mp_stock : catégories non laizées, dans leur unité de gestion
        #            (kg pour l'adhésif, palette/unité pour le reste).
        # mp_stock_laize : catégories bobine, en BOBINES — converti plus bas en
        #            mètres linéaires pour être comparable au besoin.
        perte_pct = stock_config_float(conn, "mandrin_perte_coupe_pct")
        stock_map: dict = {}
        stock_bobines: dict = {}
        for r in conn.execute("SELECT matiere_id, SUM(quantite) AS q FROM mp_stock GROUP BY matiere_id").fetchall():
            stock_map[int(r["matiere_id"])] = float(r["q"] or 0)
        for r in conn.execute("SELECT matiere_id, SUM(quantite) AS q FROM mp_stock_laize GROUP BY matiere_id").fetchall():
            stock_bobines[int(r["matiere_id"])] = float(r["q"] or 0)
        # Détail par laize : c'est le stock réellement mobilisable pour un
        # dossier, celui qu'on compare au besoin d'une laize précise.
        stock_par_laize: dict = {}
        for r in conn.execute(
            """SELECT s.matiere_id, l.valeur_mm, l.label, s.quantite
               FROM mp_stock_laize s JOIN mp_laizes l ON l.id = s.laize_id"""
        ).fetchall():
            stock_par_laize[(int(r["matiere_id"]), float(r["valeur_mm"] or 0))] = {
                "quantite": float(r["quantite"] or 0), "label": r["label"],
            }

    # Agrégation par (kind, source_value)
    agg: dict = {}
    for pe in rows:
        r7 = _ratio_dans_fenetre(pe, today, borne_7)
        r15 = _ratio_dans_fenetre(pe, today, borne_15)
        besoins = _compute_besoins_dossier(pe, mapping, perte_pct)
        for b in besoins:
            key = (b["kind"], (b["source_value"] or "").strip().lower())
            if key not in agg:
                agg[key] = {
                    "kind": b["kind"],
                    "source_value": b["source_value"],
                    "matiere_id": b["matiere_id"],
                    "matiere_ref": b["matiere_ref"],
                    "matiere_designation": b["matiere_designation"],
                    "matiere_categorie": b.get("matiere_categorie"),
                    "unite": b["unite"],
                    "besoin_7j": 0.0,
                    "besoin_15j": 0.0,
                    "besoin_total": 0.0,
                    "mapped": b["mapped"],
                    "nb_dossiers": 0,
                    "nb_dossiers_incalculables": 0,
                    "formule_exemple": None,
                    # Mandrins : traduction du besoin à l'achat. Chaque dossier a
                    # sa propre laize de module, donc ses propres tubes — on somme
                    # les tubes dossier par dossier, jamais après coup.
                    "besoin_7j_tubes": 0.0,
                    "besoin_15j_tubes": 0.0,
                    "besoin_total_tubes": 0.0,
                    "besoin_total_palettes": 0.0,
                    "nb_dossiers_sans_tubes": 0,
                    # Ventilation par laize (bobines uniquement) : le total en
                    # mètres ne dit pas quelle bobine commander.
                    "par_laize": {},
                }
            a = agg[key]
            a["nb_dossiers"] += 1
            if not b["calculable"]:
                a["nb_dossiers_incalculables"] += 1
                continue
            a["besoin_7j"] += b["quantite"] * r7
            a["besoin_15j"] += b["quantite"] * r15
            a["besoin_total"] += b["quantite"]
            if b["kind"] in _KINDS_BOBINE:
                cle_lz = b.get("laize_mm")
                cle_lz = float(cle_lz) if cle_lz else None
                pl = a["par_laize"].setdefault(cle_lz, {
                    "laize_mm": cle_lz, "besoin_7j": 0.0, "besoin_15j": 0.0,
                    "besoin_total": 0.0, "nb_dossiers": 0,
                })
                pl["besoin_7j"] += b["quantite"] * r7
                pl["besoin_15j"] += b["quantite"] * r15
                pl["besoin_total"] += b["quantite"]
                pl["nb_dossiers"] += 1
            bt = b.get("besoin_tubes")
            if bt is None:
                if b["kind"] == "mandrin":
                    a["nb_dossiers_sans_tubes"] += 1
            else:
                a["besoin_7j_tubes"] += bt * r7
                a["besoin_15j_tubes"] += bt * r15
                a["besoin_total_tubes"] += bt
                a["besoin_total_palettes"] += b.get("besoin_palettes") or 0.0
            if not a["formule_exemple"]:
                a["formule_exemple"] = b["formule"]

    lignes = []
    for a in agg.values():
        for k in ("besoin_7j", "besoin_15j", "besoin_total",
                  "besoin_7j_tubes", "besoin_15j_tubes",
                  "besoin_total_tubes", "besoin_total_palettes"):
            a[k] = round(a[k], 3)
        if a["kind"] != "mandrin":
            # Hors mandrins, la notion de tube n'existe pas : on ne laisse pas
            # traîner des zéros que le front pourrait afficher.
            for k in ("besoin_7j_tubes", "besoin_15j_tubes",
                      "besoin_total_tubes", "besoin_total_palettes",
                      "nb_dossiers_sans_tubes"):
                a[k] = None
        # Stock ramené dans l'unité du besoin.
        stock = None
        stock_note = None
        mid = a["matiere_id"]
        if mid:
            if a["kind"] in _KINDS_BOBINE:
                bobines = stock_bobines.get(mid, 0.0) + stock_map.get(mid, 0.0)
                ml_bobine = _f(_matiere_ml_par_bobine(mapping, a["kind"], a["source_value"]))
                a["ml_par_bobine"] = ml_bobine
                if ml_bobine:
                    stock = round(bobines * ml_bobine, 3)
                    stock_note = (f"{_n(bobines)} bobines × {_n(ml_bobine, 'm')}/bobine")
                else:
                    stock_note = ("Métrage par bobine non renseigné sur la matière — "
                                  "stock non convertible en ml")
            elif a["kind"] == "mandrin":
                # Le stock d'un mandrin se tient en palettes de tubes, le besoin en
                # mandrins. Sans la longueur de tube ni le nombre de tubes par
                # palette, les deux ne sont pas comparables : on le dit plutôt que
                # d'afficher des palettes en face de mandrins.
                palettes_stock = stock_map.get(mid, 0.0) + stock_bobines.get(mid, 0.0)
                mp_man = mapping.get((a["kind"], (a["source_value"] or "").strip().lower())) or {}
                upp = _f(mp_man.get("unites_par_palette"))
                tubes_besoin = a["besoin_total_tubes"] or 0
                ratio = (a["besoin_total"] / tubes_besoin) if tubes_besoin > 0 else None
                a["stock_palettes"] = round(palettes_stock, 3)
                if upp and ratio:
                    tubes_stock = palettes_stock * upp
                    stock = round(tubes_stock * ratio, 3)
                    a["stock_tubes"] = round(tubes_stock, 3)
                    stock_note = (
                        f"{_n(palettes_stock)} palettes × {_n(upp)} tubes/palette = "
                        f"{_n(round(tubes_stock, 1))} tubes ≈ {_n(round(stock, 0))} mandrins "
                        f"(à {_n(round(ratio, 2))} mandrins/tube sur les dossiers en cours)"
                    )
                elif not upp:
                    stock_note = ("Tubes par palette non renseigné sur la matière — "
                                  "stock non convertible en mandrins")
                else:
                    stock_note = ("Longueur tube ou laize module manquante — "
                                  "stock non convertible en mandrins")
            elif a["kind"] == "carton":
                # Un carton se stocke à la palette mais se consomme à l'unité :
                # sans la conversion, une palette de 672 cartons s'affichait
                # « 1 u » en face d'un besoin de 672, et tout ressortait en manque.
                palettes_stock = stock_map.get(mid, 0.0) + stock_bobines.get(mid, 0.0)
                mp_cart = mapping.get((a["kind"], (a["source_value"] or "").strip().lower())) or {}
                cpp = _f(mp_cart.get("unites_par_palette"))
                a["stock_palettes"] = round(palettes_stock, 3)
                if cpp:
                    stock = round(palettes_stock * cpp, 3)
                    stock_note = (f"{_n(palettes_stock)} palettes × {_n(cpp)} cartons/palette "
                                  f"= {_n(stock)} cartons")
                else:
                    stock_note = ("Cartons par palette non renseigné sur la matière — "
                                  "stock non convertible en cartons")
            else:
                stock = round(stock_map.get(mid, 0.0) + stock_bobines.get(mid, 0.0), 3)
        a["stock_actuel"] = stock
        a["stock_note"] = stock_note
        a["manque_7j"] = None
        if mid and stock is not None:
            a["manque_7j"] = round(max(0, a["besoin_7j"] - stock), 3)
        lignes.append(a)
    # Tri : d'abord les non mappés (à corriger), puis manque décroissant, puis besoin 7j
    lignes.sort(key=lambda x: (
        x["mapped"],
        -(x.get("manque_7j") or 0),
        -x["besoin_7j"],
    ))
    groupe = _regrouper_par_matiere(lignes, stock_par_laize)
    return {
        "lignes": lignes,
        "count": len(lignes),
        # Vue « par matière » : même calcul, regroupé sur la référence MySifa.
        # Servi par le même endpoint pour que les trois vues montrent toujours
        # les mêmes chiffres, à la même seconde.
        "matieres": groupe["matieres"],
        "non_associees": groupe["non_associees"],
        "today": today.isoformat(),
        "borne_7j": borne_7.isoformat(),
        "borne_15j": borne_15.isoformat(),
    }


def _ml_par_bobine_ligne(a: dict) -> Optional[float]:
    """Mètres linéaires par bobine de la matière d'une ligne agrégée.

    Posé par l'agrégation par échéance, qui l'a déjà lu sur la matière. On ne
    le redemande pas à la base : la ligne le porte, c'est la même valeur.
    """
    return _f(a.get("ml_par_bobine"))


def _regrouper_par_matiere(lignes: list, stock_par_laize: Optional[dict] = None) -> dict:
    """Regroupe les lignes de besoin par référence matière MySifa.

    Plusieurs valeurs de fiche technique peuvent pointer vers la même référence
    (« Couché », « Couché 80 »). C'est au niveau de la référence qu'on commande,
    donc c'est ce total-là qui compte pour l'appro — la vue par échéance, elle,
    reste au niveau de la valeur de fiche pour pouvoir corriger un mapping.

    Les bobines font exception : une référence frontal, glassine ou complexe
    sort en **une ligne par laize**. Une bobine de 306 ne remplace pas une
    bobine de 500, et le stock lui-même est tenu laize par laize — agréger les
    deux donnait un total juste en mètres mais impossible à commander.

    Retourne { matieres: [...], non_associees: [...] }. Les besoins sans matière
    associée ne sont pas noyés dans le tableau : ils sortent à part, en fin de
    vue, car ils appellent une action différente (associer, pas commander).
    """
    stock_par_laize = stock_par_laize or {}
    par_mat: dict = {}
    non_associees: list = []

    def _entree(cle, a, laize_mm):
        """Crée (ou retrouve) la ligne agrégée d'une référence, laize comprise."""
        m = par_mat.get(cle)
        if m is not None:
            return m
        # Le stock est porté par la référence, pas par la valeur de fiche : on le
        # prend une fois et on ne l'additionne jamais, sinon deux valeurs mappées
        # sur la même référence le compteraient deux fois.
        stock = a.get("stock_actuel")
        note = a.get("stock_note")
        if laize_mm is not None:
            # Stock de CETTE laize, converti en mètres pour rester comparable au
            # besoin. Sans conversion on afficherait des bobines face à des ml.
            info = stock_par_laize.get((a["matiere_id"], laize_mm))
            ml = _ml_par_bobine_ligne(a)
            if info is None:
                stock, note = None, ("Laize absente de cette matière — "
                                     "stock non comparable")
            elif ml:
                stock = round(info["quantite"] * ml, 3)
                note = (f"{_n(info['quantite'])} bobines de {_n(laize_mm)} mm "
                        f"× {_n(ml, 'm')}/bobine")
            else:
                stock, note = None, ("Métrage par bobine non renseigné — "
                                     "stock non convertible en ml")
        m = par_mat[cle] = {
            "matiere_id": a["matiere_id"],
            "matiere_ref": a["matiere_ref"],
            "matiere_designation": a["matiere_designation"],
            "matiere_categorie": a.get("matiere_categorie"),
            "kind": a["kind"],
            "unite": a["unite"],
            "laize_mm": laize_mm,
            "besoin_7j": 0.0,
            "besoin_15j": 0.0,
            "besoin_total": 0.0,
            "stock_actuel": stock,
            "stock_note": note,
            "stock_palettes": a.get("stock_palettes"),
            "besoin_total_tubes": None,
            "besoin_total_palettes": None,
            "nb_dossiers": 0,
            "nb_dossiers_incalculables": 0,
            "sources": [],
        }
        return m

    for a in lignes:
        if not a.get("mapped") or not a.get("matiere_id"):
            non_associees.append({
                "kind": a["kind"],
                "source_value": a["source_value"],
                "unite": a["unite"],
                "besoin_7j": a["besoin_7j"],
                "besoin_15j": a["besoin_15j"],
                "besoin_total": a["besoin_total"],
                "nb_dossiers": a["nb_dossiers"],
                "nb_dossiers_incalculables": a["nb_dossiers_incalculables"],
            })
            continue

        mid = a["matiere_id"]
        bobine = a["kind"] in _KINDS_BOBINE
        ventil = (a.get("par_laize") or {}) if bobine else {}

        if bobine and ventil:
            for laize_mm, part in ventil.items():
                m = _entree((mid, laize_mm), a, laize_mm)
                m["besoin_7j"] += part["besoin_7j"]
                m["besoin_15j"] += part["besoin_15j"]
                m["besoin_total"] += part["besoin_total"]
                m["nb_dossiers"] += part["nb_dossiers"]
                m["sources"].append({
                    "source_value": a["source_value"],
                    "besoin_total": round(part["besoin_total"], 3),
                    "nb_dossiers": part["nb_dossiers"],
                })
            # Les dossiers non chiffrés n'ont pas de laize à eux : ils restent
            # rattachés à la première ligne de la référence, signalés hors total.
            if a["nb_dossiers_incalculables"]:
                prem = next((par_mat[(mid, lz)] for lz in ventil), None)
                if prem is not None:
                    prem["nb_dossiers_incalculables"] += a["nb_dossiers_incalculables"]
            continue

        m = _entree(mid, a, None)
        m["besoin_7j"] += a["besoin_7j"]
        m["besoin_15j"] += a["besoin_15j"]
        m["besoin_total"] += a["besoin_total"]
        m["nb_dossiers"] += a["nb_dossiers"]
        m["nb_dossiers_incalculables"] += a["nb_dossiers_incalculables"]
        for cle in ("besoin_total_tubes", "besoin_total_palettes"):
            v = a.get(cle)
            if v:
                m[cle] = (m[cle] or 0.0) + v
        m["sources"].append({
            "source_value": a["source_value"],
            "besoin_total": a["besoin_total"],
            "nb_dossiers": a["nb_dossiers"],
        })

    matieres = []
    for m in par_mat.values():
        for k in ("besoin_7j", "besoin_15j", "besoin_total",
                  "besoin_total_tubes", "besoin_total_palettes"):
            if m[k] is not None:
                m[k] = round(m[k], 3)
        m["manque_7j"] = (round(max(0.0, m["besoin_7j"] - m["stock_actuel"]), 3)
                          if m["stock_actuel"] is not None else None)
        m["sources"].sort(key=lambda s: -(s["besoin_total"] or 0))
        matieres.append(m)

    # Ce qui manque d'abord, puis le besoin le plus proche : l'ordre de l'appro.
    matieres.sort(key=lambda x: (-(x.get("manque_7j") or 0), -x["besoin_7j"]))
    non_associees.sort(key=lambda x: (-(x["besoin_total"] or 0), -x["nb_dossiers"]))
    return {"matieres": matieres, "non_associees": non_associees}


# ─────────────────────────────────────────────────────────────────────────
# Rattachement des documents d'un dossier non chiffré
#
# Un dossier sort « n.c. » pour deux raisons seulement : aucun OF rattaché, ou
# aucune fiche technique rapprochée. Les deux se corrigent depuis la ligne, sans
# quitter Besoins matières — et surtout, la correction s'écrit dans les tables
# de référence, donc elle vaut pour MyProd, le planning et l'expédition, pas
# seulement pour cet écran.
#
# - OF : `_promote_of_link` (of_import.py) aligne `planning_of_links` ET
#   `planning_entries.of_import_id`. Les deux sont nécessaires : le slot du
#   planning lit la colonne, le panneau OF lit la table de liens.
# - Fiche technique : le rapprochement se fait sur `ref_produit_norm`. On aligne
#   cette clé sans toucher à `ref_produit`, qui reste ce que l'atelier lit.
# ─────────────────────────────────────────────────────────────────────────


def _dossier_ou_404(conn, planning_id: int):
    row = conn.execute(
        """SELECT pe.id, pe.reference, pe.numero_of, pe.ref_produit,
                  pe.ref_produit_norm, pe.of_import_id, pe.statut,
                  m.nom AS machine_nom
           FROM planning_entries pe
           LEFT JOIN machines m ON m.id = pe.machine_id
           WHERE pe.id = ?""",
        (planning_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Dossier introuvable.")
    return row


def _like(v) -> str:
    return "%" + str(v or "").strip() + "%"


@router.get("/api/stock/besoins-matieres/dossier/{planning_id}/documents")
def dossier_documents(planning_id: int, request: Request):
    """OF et fiches techniques rattachables à un dossier.

    Sans `q`, on propose ce que le dossier laisse deviner : son numéro d'OF et
    sa référence produit. Avec `q`, c'est une recherche libre — le cas où le
    document existe sous un libellé qui ne ressemble à rien de ce qu'on attend.
    """
    require_stock_matieres_admin(request)
    q = (request.query_params.get("q") or "").strip()

    with get_db() as conn:
        pe = _dossier_ou_404(conn, planning_id)

        if q:
            ofs = conn.execute(
                """SELECT id, of_numero, reference, machine, qte_etiquettes,
                          qte_bobines, date_creation, date_import
                   FROM of_imports
                   WHERE LOWER(COALESCE(of_numero,'')) LIKE LOWER(?)
                      OR LOWER(COALESCE(reference,''))  LIKE LOWER(?)
                      OR LOWER(COALESCE(machine,''))    LIKE LOWER(?)
                   ORDER BY date_import DESC, id DESC LIMIT 25""",
                (_like(q), _like(q), _like(q)),
            ).fetchall()
            fiches = conn.execute(
                """SELECT id, reference, designation, client, machine, ref_produit_norm
                   FROM fiches_techniques
                   WHERE LOWER(COALESCE(reference,''))   LIKE LOWER(?)
                      OR LOWER(COALESCE(designation,'')) LIKE LOWER(?)
                      OR LOWER(COALESCE(client,''))      LIKE LOWER(?)
                   ORDER BY reference COLLATE NOCASE LIMIT 25""",
                (_like(q), _like(q), _like(q)),
            ).fetchall()
        else:
            num = (pe["numero_of"] or "").strip()
            ref = (pe["ref_produit"] or "").strip()
            ofs = conn.execute(
                """SELECT id, of_numero, reference, machine, qte_etiquettes,
                          qte_bobines, date_creation, date_import
                   FROM of_imports
                   WHERE (? != '' AND LOWER(COALESCE(of_numero,'')) LIKE LOWER(?))
                      OR (? != '' AND LOWER(COALESCE(reference,'')) LIKE LOWER(?))
                   ORDER BY date_import DESC, id DESC LIMIT 25""",
                (num, _like(num), ref, _like(ref)),
            ).fetchall()
            norm = (pe["ref_produit_norm"] or "").strip()
            fiches = conn.execute(
                """SELECT id, reference, designation, client, machine, ref_produit_norm
                   FROM fiches_techniques
                   WHERE (? != '' AND ref_produit_norm = ?)
                      OR (? != '' AND LOWER(COALESCE(reference,'')) LIKE LOWER(?))
                   ORDER BY reference COLLATE NOCASE LIMIT 25""",
                (norm, norm, ref, _like(ref)),
            ).fetchall()

    return {
        "dossier": {
            "planning_id": pe["id"],
            "reference": pe["reference"],
            "numero_of": pe["numero_of"],
            "ref_produit": pe["ref_produit"],
            "machine": pe["machine_nom"],
            "of_import_id": pe["of_import_id"],
            "a_un_of": pe["of_import_id"] is not None,
        },
        "recherche": q,
        "ofs": [dict(r) for r in ofs],
        "fiches": [dict(r) for r in fiches],
    }


@router.post("/api/stock/besoins-matieres/dossier/{planning_id}/rattacher-of")
async def rattacher_of(planning_id: int, request: Request):
    """Fait d'un OF existant l'OF actif du dossier. Body : { of_id }."""
    user = require_stock_matieres_admin(request)
    body = await request.json()
    of_id = body.get("of_id")
    if not isinstance(of_id, int):
        raise HTTPException(400, "of_id (entier) requis.")

    # Import local : of_import.py n'a pas à connaître Besoins matières, et un
    # import au niveau module créerait un cycle le jour où l'inverse arrivera.
    from app.routers.of_import import (
        _promote_of_link, _invalidate_pending_count_cache,
    )

    qui = (user.get("nom") or user.get("email") or "besoins_matieres")
    with get_db() as conn:
        _dossier_ou_404(conn, planning_id)
        oi = conn.execute(
            "SELECT id, of_numero FROM of_imports WHERE id=?", (of_id,)
        ).fetchone()
        if not oi:
            raise HTTPException(404, "OF introuvable.")
        _promote_of_link(conn, planning_id, of_id, qui)
        # Rattachement décidé par un humain : l'auto-link ne doit plus le défaire.
        try:
            conn.execute(
                "UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?",
                (planning_id,),
            )
        except Exception:
            pass  # colonne absente sur une base ancienne : le lien reste valide
        conn.commit()
    # Le dossier sort de la liste « sans OF » : le badge de MyProd doit suivre.
    _invalidate_pending_count_cache()
    return {"ok": True, "planning_id": planning_id, "of_id": of_id,
            "of_numero": oi["of_numero"]}


_VALIDATION_ROLES = frozenset({
    "superadmin", "direction",
    # La famille administration : c'est l'administration technique qui relit les
    # fiches et déstocke, elle doit pouvoir lever son propre blocage.
    "administration", "administration_technique", "administration_ventes",
})


def _require_validation_docs(request: Request) -> dict:
    user = require_stock_write(request)
    if user.get("role") not in _VALIDATION_ROLES:
        raise HTTPException(403, "Validation réservée à la Direction et à l'Administration.")
    return user


async def _basculer_validation(request: Request, table: str, doc_id: int, libelle: str):
    """Valide ou dévalide un document. Body : { valide: true|false }.

    La validation porte un nom et une date : une case cochée sans auteur ne
    veut rien dire le jour où le stock est faux et qu'on cherche pourquoi.
    """
    user = _require_validation_docs(request)
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    valide = 1 if bool((body or {}).get("valide", True)) else 0
    qui = (user.get("nom") or user.get("email") or "").strip() or None
    with get_db() as conn:
        row = conn.execute(f"SELECT id FROM {table} WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"{libelle} introuvable.")
        conn.execute(
            f"UPDATE {table} SET valide=?, valide_par=?, "
            f"valide_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?",
            (valide, qui if valide else None, doc_id),
        )
        conn.commit()
    return {"ok": True, "valide": valide, "valide_par": qui if valide else None}


@router.post("/api/stock/besoins-matieres/of/{of_id}/validation")
async def valider_of(of_id: int, request: Request):
    """Valide (ou dévalide) un ordre de fabrication."""
    return await _basculer_validation(request, "of_imports", of_id, "OF")


@router.post("/api/stock/besoins-matieres/fiche/{fiche_id}/validation")
async def valider_fiche(fiche_id: int, request: Request):
    """Valide (ou dévalide) une fiche technique."""
    return await _basculer_validation(request, "fiches_techniques", fiche_id, "Fiche technique")


def _historique(request: Request, table: str, doc_id: int, libelle: str) -> dict:
    """Ce qui a changé sur un document, et depuis quelle source.

    C'est la contrepartie du verrou : demander une relecture n'a de sens que si
    le relecteur peut voir CE QUI a bougé depuis la dernière. Sinon il revalide
    au jugé, et la case redevient une formalité.

    Lecture seule, et ouverte à tous ceux qui voient déjà le tableau Besoins
    matières : comprendre pourquoi un déstockage est bloqué ne demande pas le
    droit de le débloquer.
    """
    require_stock_matieres_admin(request)
    with get_db() as conn:
        row = conn.execute(
            f"SELECT id, COALESCE(valide,0) AS valide, valide_par, valide_at, "
            f"invalide_at, invalide_motif FROM {table} WHERE id=?", (doc_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"{libelle} introuvable.")
        lignes = historique_document(conn, table, doc_id)
    # Les changements postérieurs à la dernière validation sont ceux qui
    # restent à relire. Les autres sont déjà couverts par la case cochée.
    depuis = (row["valide_at"] or "") if row["valide"] else ""
    for li in lignes:
        li["depuis_validation"] = bool(depuis) and str(li["at"] or "") > depuis
    return {
        "document": dict(row),
        "historique": lignes,
        "a_relire": [li for li in lignes if li["depuis_validation"]],
    }


def _mois_glissants(depuis: date, avant: int, apres: int) -> list:
    """Liste 'AAAA-MM' de M-avant à M+apres, mois courant compris."""
    an, mo = depuis.year, depuis.month - avant
    an += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    out = []
    for _ in range(avant + 1 + apres):
        out.append(f"{an:04d}-{mo:02d}")
        mo += 1
        if mo > 12:
            mo, an = 1, an + 1
    return out


def _agreger_of_orphelins(conn, debut: Optional[str] = None) -> tuple:
    """Même agrégat que `agreger_carnet`, mais sur les OF sans dossier planning.

    Retourne (cumul, vus) au format de `agreger_carnet` : (mois, matiere_id,
    kind) → { q, unite, inc, ref, designation, source_value } et l'ensemble des
    identifiants d'OF vus par clé, pour ne pas compter deux fois un même OF qui
    porterait deux besoins de la même matière.
    """
    # Le tri par date est fait par `_load_of_orphelins`, avant le
    # rapprochement de fiche technique : c'est lui le poste de coût sur le
    # fond d'archive, pas le calcul du besoin.
    dossiers = _load_of_orphelins(conn, debut)
    if not dossiers:
        return {}, {}
    mapping = _load_mapping(conn)
    perte = stock_config_float(conn, "mandrin_perte_coupe_pct")

    cumul: dict = {}
    vus: dict = {}
    for pe in dossiers:
        mois = _mois_of(pe)
        if not mois:
            continue  # un OF sans date exploitable ne pèse sur aucun mois
        _matieres_depuis_of(pe)
        for b in _compute_besoins_dossier(pe, mapping, perte):
            cle = (mois, b.get("matiere_id"), b.get("kind"))
            agg = cumul.setdefault(cle, {
                "q": 0.0, "q_actif": 0.0, "unite": b.get("unite"), "inc": 0,
                "ref": b.get("matiere_ref"), "designation": b.get("matiere_designation"),
                "source_value": b.get("source_value"),
            })
            vus.setdefault(cle, set()).add(pe["id"])
            q = b.get("quantite")
            if q is None:
                agg["inc"] += 1
            else:
                agg["q"] += float(q)
            if not agg["unite"]:
                agg["unite"] = b.get("unite")
    return cumul, vus


@router.get("/api/stock/besoins-matieres/tendance")
def besoins_tendance(request: Request):
    """Besoin par matière et par mois de livraison, sur une fenêtre glissante.

    Les trois autres vues répondent à « de quoi ai-je besoin » ; celle-ci
    répond à « quand ». C'est la question de l'acheteur : un besoin de frontal
    étalé sur quatre mois ne se commande pas comme le même volume concentré
    sur trois semaines.

    La fenêtre par défaut est 12 mois passés + le mois courant + 6 mois à
    venir. Le passé n'est pas décoratif : c'est la seule référence disponible
    pour juger si un mois à venir est plein ou creux. Sans lui, un carnet qui
    ne s'est pas encore rempli et une baisse d'activité ont exactement la même
    allure.

    Deux sources, strictement complémentaires :

    - le planning (`planning_entries`, tous statuts) pour ce qu'il porte
      encore — l'essentiel du futur et les derniers mois écoulés ;
    - les OF scannés qu'aucun dossier du planning ne porte plus
      (`of_imports`), datés par leur délai client, pour les mois plus anciens.

    Le mois d'une ligne est celui de la LIVRAISON, pas de la production : c'est
    l'engagement client qui fixe la date à laquelle la matière doit être là.
    """
    require_stock_matieres_admin(request)

    def _q(nom, defaut, mini, maxi):
        try:
            return max(mini, min(maxi, int(request.query_params.get(nom) or defaut)))
        except (TypeError, ValueError):
            return defaut

    # `mois` reste accepté pour ne pas casser un lien ou un signet existant :
    # il ne pilotait que l'horizon futur, il continue de ne piloter que lui.
    # 12 mois révolus + le mois courant + 5 à venir = 18 colonnes.
    futur = _q("futur", _q("mois", 6, 2, 18) - 1, 1, 24)
    passe = _q("passe", 12, 0, 36)
    horizon = futur + 1
    kind_filtre = (request.query_params.get("kind") or "").strip() or None

    # Fenêtre glissante. Ce qui tombe avant est ignoré (trop vieux pour
    # éclairer une décision d'achat) ; ce qui tombe après est regroupé dans un
    # « au-delà » plutôt que tronqué en silence — un besoin oublié parce qu'il
    # sortait de la fenêtre serait pire qu'un besoin affiché en vrac.
    auj = date.today()
    mois_courant = f"{auj.year:04d}-{auj.month:02d}"
    tous_mois = _mois_glissants(auj, passe, futur)
    mois_passes = [m for m in tous_mois if m < mois_courant]
    mois_futurs = [m for m in tous_mois if m >= mois_courant]
    debut, borne = tous_mois[0], tous_mois[-1]
    AU_DELA = "au-dela"

    with get_db() as conn:
        cumul, vus, vus_actifs, dossiers = agreger_carnet(conn)
        cumul_of, vus_of = _agreger_of_orphelins(conn, debut)
        couv = couverture_carnet(conn)

    # Une seule fusion des deux sources : le reste du calcul ne sait plus d'où
    # vient une ligne, et ne peut donc pas les traiter différemment par erreur.
    # `origines` garde la trace par mois, pour que l'écran puisse dire « ce
    # mois-là vient des OF scannés » sans que ça change un seul chiffre.
    origines: dict = {}
    for src, (c, v) in (("planning", (cumul, vus)), ("of", (cumul_of, vus_of))):
        for (mois, _mid, _kind) in c:
            origines.setdefault(mois, set()).add(src)

    lignes: dict = {}
    passe_total = 0.0
    hors_fenetre = 0.0
    for src_cumul, src_vus in ((cumul, vus), (cumul_of, vus_of)):
        for (mois, mid, kind), agg in src_cumul.items():
            if kind_filtre and kind != kind_filtre:
                continue
            if mois < debut:
                # Trop vieux pour éclairer un achat, mais un dossier encore
                # actif sur un mois échu est un retard : il reste compté.
                hors_fenetre += agg["q"]
                passe_total += agg.get("q_actif", 0.0)
                continue
            # Le retard : ce qui reste à produire sur un mois déjà échu. Compté
            # sur le planning seul — un OF sorti du planning n'a plus de reste.
            if mois < mois_courant:
                passe_total += agg.get("q_actif", 0.0)
            col = mois if mois <= borne else AU_DELA
            cle = (mid, kind)
            li = lignes.setdefault(cle, {
                "matiere_id": mid,
                "libelle": (agg.get("ref") or agg.get("designation")
                            or agg.get("source_value") or "Non associée"),
                "designation": agg.get("designation"),
                "kind": kind,
                "unite": agg.get("unite"),
                "par_mois": {},
                "total": 0.0,
                "total_futur": 0.0,
                "total_au_dela": 0.0,
                "dossiers": set(),
                "incalculables": 0,
            })
            cell = li["par_mois"].setdefault(col, {"q": 0.0, "dossiers": 0, "inc": 0})
            cell["q"] += agg["q"]
            cell["dossiers"] += len(src_vus.get((mois, mid, kind), ()))
            cell["inc"] += agg["inc"]
            li["total"] += agg["q"]
            # `total_futur` s'arrête à la borne de la fenêtre, et le reste est
            # compté à part. L'écran affiche les deux côte à côte : si le
            # premier contenait le second, le lecteur additionnerait deux fois
            # la même matière.
            if col == AU_DELA:
                li["total_au_dela"] += agg["q"]
            elif mois >= mois_courant:
                li["total_futur"] += agg["q"]
            li["dossiers"] |= src_vus.get((mois, mid, kind), set())
            li["incalculables"] += agg["inc"]

    colonnes = tous_mois + [AU_DELA]
    out = []
    for li in lignes.values():
        serie = [{"mois": c, "passe": c < mois_courant and c != AU_DELA,
                  **li["par_mois"].get(c, {"q": 0.0, "dossiers": 0, "inc": 0})}
                 for c in colonnes]
        out.append({
            **{k: v for k, v in li.items() if k not in ("par_mois", "dossiers")},
            "serie": serie,
            "max": max((p["q"] for p in serie), default=0.0),
            "nb_dossiers": len(li["dossiers"]),
            "non_associee": li["matiere_id"] is None,
        })
    # Le poids à venir d'abord : c'est ce qui reste à commander qui classe la
    # liste, pas le volume déjà livré. À égalité, le total sur la fenêtre.
    out.sort(key=lambda l: (l["kind"], -l["total_futur"], -l["total"]))

    # Regroupement par catégorie de matière, fait ici plutôt que dans l'écran :
    # l'ordre des catégories et le libellé de chacune sont les mêmes partout
    # dans MyStock, et les dupliquer côté navigateur garantirait qu'ils
    # finissent par diverger.
    cat_libelles = {"support": "Frontal", "glassine": "Glassine",
                    "adhesif": "Adhésif", "mandrin": "Mandrins",
                    "carton": "Cartons", "palette": "Palettes"}
    cats: dict = {}
    for l in out:
        c = cats.setdefault(l["kind"], {
            "kind": l["kind"],
            "libelle": cat_libelles.get(l["kind"], l["kind"]),
            "unite": l.get("unite"),
            "total": 0.0, "total_futur": 0.0, "total_au_dela": 0.0,
            "nb_matieres": 0, "incalculables": 0,
            "lignes": [],
        })
        c["total"] += l["total"]
        c["total_futur"] += l["total_futur"]
        c["total_au_dela"] += l["total_au_dela"]
        c["incalculables"] += l["incalculables"]
        # Le rang dans la catégorie, figé ici. C'est lui qui choisira la teinte
        # de la courbe : une couleur assignée sur la position dans une liste
        # filtrée changerait à chaque caractère tapé dans la recherche, et une
        # matière ne serait plus reconnaissable d'un écran à l'autre.
        l["rang"] = c["nb_matieres"]
        c["nb_matieres"] += 1
        c["lignes"].append(l)
        if not c["unite"]:
            c["unite"] = l.get("unite")
    ordre = list(_KINDS)
    categories = sorted(cats.values(),
                        key=lambda c: (ordre.index(c["kind"])
                                       if c["kind"] in ordre else 99))
    for c in categories:
        c["total"] = round(c["total"], 2)
        c["total_futur"] = round(c["total_futur"], 2)
        c["total_au_dela"] = round(c["total_au_dela"], 2)

    return {
        "colonnes": colonnes,
        "mois": mois_futurs,
        "mois_passes": mois_passes,
        "mois_courant": mois_courant,
        "horizon": horizon,
        "passe": passe,
        "futur": futur,
        "lignes": out,
        "categories": categories,
        # D'où vient chaque mois. Sert uniquement à l'affichage : un mois que
        # seuls les OF documentent se lit autrement qu'un mois planifié.
        "origines": {m: sorted(s) for m, s in origines.items() if m in tous_mois},
        "hors_fenetre": round(hors_fenetre, 2),
        "reste_sur_mois_echus": round(passe_total, 2),
        # Tant que la série de photos est trop courte, l'écran ne doit pas
        # laisser croire qu'il montre une tendance mesurée dans le temps : il
        # montre l'état du carnet aujourd'hui, réparti par mois.
        "historique": couv,
    }


@router.get("/api/stock/besoins-matieres/fiches-incoherentes")
def fiches_incoherentes(request: Request):
    """Fiches techniques dont la géométrie ne boucle pas.

    Le nombre de fronts multiplié par la laize du module doit tenir dans la
    laize de la bobine. Quand ce n'est pas le cas, le besoin en frontal calculé
    depuis cette fiche est faux d'un facteur qu'on sait nommer — et c'est ce
    facteur qui classe la liste : une fiche qui surestime d'un facteur 18 se
    corrige avant une qui se trompe d'un front.

    Aucune correction automatique. Une fiche fausse se répare dans Access, à la
    source ; compenser en silence à chaque lecture cacherait le problème
    pendant que les commandes continuent de partir de travers.
    """
    require_stock_matieres_admin(request)
    with get_db() as conn:
        fiches = [dict(r) for r in conn.execute(_SQL_FT).fetchall()]
        # Combien de dossiers du planning s'appuient sur chaque fiche : une
        # fiche fausse mais inutilisée n'est pas une urgence.
        dossiers = _load_dossiers(conn, _SQL_PE.replace(
            "WHERE pe.statut IN ('attente', 'en_cours')", ""))
    usage: dict = {}
    for pe in dossiers:
        if pe.get("ft_id"):
            usage[pe["ft_id"]] = usage.get(pe["ft_id"], 0) + 1

    items, indeterminables = [], 0
    for ft in fiches:
        res = controler_fiche(ft)
        if res["verdict"] == "indeterminable":
            indeterminables += 1
            continue
        if res["verdict"] == "coherent":
            continue
        items.append({
            "fiche_id": ft["id"],
            "reference": ft.get("reference"),
            "machine": ft.get("machine"),
            "dossiers_concernes": usage.get(ft["id"], 0),
            "nb_front_retenu": res["retenu"],
            "nb_front_outil": res["nb_front_outil"],
            "nb_front_module": res["nb_front_declare_module"],
            "nb_front_geometrique": res["nb_front_geometrique"],
            "laize": res["laize_utile"],
            "mod_laize": res["mod_laize"],
            "facteur_erreur": res["facteur_erreur"],
            "message": res["message"],
        })
    # Impact d'abord : facteur d'erreur, puis nombre de dossiers qui en dépendent.
    items.sort(key=lambda i: (-(i["facteur_erreur"] or 0), -i["dossiers_concernes"]))
    return {
        "total_fiches": len(fiches),
        "incoherentes": len(items),
        "indeterminables": indeterminables,
        "items": items[:200],
    }


@router.get("/api/stock/besoins-matieres/carnet/couverture")
def carnet_couverture(request: Request):
    """Où en est l'accumulation des photos du carnet.

    Sert à répondre à une question simple et qu'on se posera forcément :
    « à partir de quand la prévision sera-t-elle calibrée ? ». Tant que
    `horizons_calibrables` est vide, aucun modèle fondé sur le remplissage du
    carnet ne peut être honnête — et il vaut mieux que l'écran le dise.
    """
    require_stock_matieres_admin(request)
    with get_db() as conn:
        return couverture_carnet(conn)


@router.post("/api/stock/besoins-matieres/carnet/capturer")
def carnet_capturer(request: Request):
    """Force la photo du jour (la recalcule si elle existe déjà)."""
    require_stock_matieres_admin(request)
    with get_db() as conn:
        res = capturer_carnet(conn, force=True)
        conn.commit()
    return res


@router.get("/api/stock/besoins-matieres/of/{of_id}/historique")
def historique_of(of_id: int, request: Request):
    """Changements de valeur d'un ordre de fabrication."""
    return _historique(request, "of_imports", of_id, "OF")


@router.get("/api/stock/besoins-matieres/fiche/{fiche_id}/historique")
def historique_fiche(fiche_id: int, request: Request):
    """Changements de valeur d'une fiche technique."""
    return _historique(request, "fiches_techniques", fiche_id, "Fiche technique")


@router.post("/api/stock/besoins-matieres/dossier/{planning_id}/rattacher-fiche")
async def rattacher_fiche(planning_id: int, request: Request):
    """Rapproche une fiche technique d'un dossier. Body : { fiche_id }.

    On aligne `ref_produit_norm` — la clé de jointure — sans toucher à
    `ref_produit`, le libellé que l'atelier lit sur le planning. Attention : une
    modification ultérieure de `ref_produit` recalcule la clé par trigger et
    défait ce rapprochement ; c'est le prix à payer pour ne pas réécrire le
    libellé du dossier dans le dos de l'utilisateur.
    """
    require_stock_matieres_admin(request)
    body = await request.json()
    fiche_id = body.get("fiche_id")
    if not isinstance(fiche_id, int):
        raise HTTPException(400, "fiche_id (entier) requis.")

    with get_db() as conn:
        _dossier_ou_404(conn, planning_id)
        ft = conn.execute(
            "SELECT id, reference, ref_produit_norm FROM fiches_techniques WHERE id=?",
            (fiche_id,),
        ).fetchone()
        if not ft:
            raise HTTPException(404, "Fiche technique introuvable.")
        norm = (ft["ref_produit_norm"] or "").strip()
        if not norm:
            raise HTTPException(
                400,
                "Cette fiche n'a pas de clé produit normalisée — corrigez sa "
                "référence dans MyProd avant de la rapprocher.",
            )
        conn.execute(
            "UPDATE planning_entries SET ref_produit_norm=? WHERE id=?",
            (norm, planning_id),
        )
        conn.commit()
    return {"ok": True, "planning_id": planning_id, "fiche_id": fiche_id,
            "reference": ft["reference"]}


# ═════════════════════════════════════════════════════════════════════════
# Déstockage de production
#
# Quand une production est réellement terminée, la matière consommée doit
# sortir du stock. Le bouton « À destocker » du planning ne changeait qu'un
# statut : le stock ne bougeait pas, il aurait fallu ressaisir chaque sortie à
# la main — donc personne ne le faisait.
#
# Le déstockage part du même calcul que Besoins matières, avec une différence
# de fond : on ne cherche plus ce qu'il faudra, mais ce qui a été consommé. Le
# métrage réellement produit (production_data) prime donc sur le théorique de
# l'OF, et les quantités sont exprimées dans l'unité de gestion du stock — en
# bobines, pas en mètres linéaires.
#
# Rien n'est bloquant : une matière non associée est listée et ignorée, un
# stock qui passe en négatif est signalé mais enregistré. La matière a été
# consommée ; refuser de l'écrire rendrait le stock plus faux, pas moins.
# ═════════════════════════════════════════════════════════════════════════


def _production_reelle(conn, pe: dict) -> dict:
    """Quantités réellement produites, lues dans les saisies d'atelier.

    Retourne { metrage, etiquettes, source } — source vaut 'reel' dès qu'une
    saisie exploitable existe, 'theorique' sinon.
    """
    vide = {"metrage": None, "etiquettes": None, "source": "theorique"}
    no_dossier = (pe.get("numero_of") or pe.get("reference") or "").strip()
    if not no_dossier:
        return vide
    try:
        from app.services.dossier_stats import build_dossier_production_stats
        rows = conn.execute(
            """SELECT id, operateur, date_operation, operation, operation_code,
                      operation_category, machine, no_dossier, client, designation,
                      quantite_a_traiter, quantite_traitee,
                      COALESCE(metrage_total_debut, metrage_prevu) AS metrage_prevu,
                      COALESCE(metrage_total_fin, metrage_reel)   AS metrage_reel
               FROM production_data
               WHERE TRIM(no_dossier) = TRIM(?)
                 AND COALESCE(est_annule, 0) = 0""",
            (no_dossier,),
        ).fetchall()
        stats = build_dossier_production_stats([dict(r) for r in rows], no_dossier)
    except Exception:
        return vide
    q = (stats or {}).get("quantites") or {}
    metrage = _f(q.get("metrage_m"))
    etiquettes = _f(q.get("etiquettes"))
    if not metrage and not etiquettes:
        return vide
    return {"metrage": metrage, "etiquettes": etiquettes, "source": "reel"}


def _laizes_matiere(conn, matiere_id: int) -> list:
    """Laizes associées à une matière, avec leur stock actuel en bobines."""
    rows = conn.execute(
        """SELECT l.id AS laize_id, l.valeur_mm, l.label,
                  COALESCE(s.quantite, 0) AS stock
           FROM mp_matiere_laizes ml
           JOIN mp_laizes l ON l.id = ml.laize_id
           LEFT JOIN mp_stock_laize s
                  ON s.matiere_id = ml.matiere_id AND s.laize_id = ml.laize_id
           WHERE ml.matiere_id = ?
           ORDER BY l.valeur_mm""",
        (matiere_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _quantite_a_destocker(b: dict, mp: dict) -> dict:
    """Traduit un besoin dans l'unité de gestion du stock.

    Le besoin s'exprime dans l'unité de l'atelier (mètres linéaires, kilos,
    unités) ; le stock se tient dans celle du magasin (bobines, kilos,
    palettes). C'est cette dernière qu'il faut mouvementer, sinon on retire
    3 658 « bobines » à une référence qui en compte douze.

    Les bobines restent fractionnaires : 0,73 bobine est ce qui a réellement
    été consommé. Arrondir à la bobine entière ferait dériver le stock d'un
    reliquat à chaque dossier.
    """
    kind = b["kind"]
    q = b.get("quantite")
    if q is None:
        return {"quantite": None, "unite": None,
                "manque": ["Besoin non chiffré — voir Besoins matières"]}

    if kind in _KINDS_BOBINE:
        ml = _f(mp.get("metres_lineaires_par_bobine"))
        if not ml:
            return {"quantite": None, "unite": "bobine",
                    "manque": ["Mètres linéaires par bobine non renseignés sur la matière"]}
        return {"quantite": round(q / ml, 4), "unite": "bobine",
                "detail": f"{_n(q, 'm')} ÷ {_n(ml, 'm')}/bobine", "manque": []}

    if kind == "adhesif":
        return {"quantite": round(q, 4), "unite": "kg", "manque": []}

    if kind == "mandrin":
        pal = _f(b.get("besoin_palettes"))
        if not pal:
            return {"quantite": None, "unite": "palette",
                    "manque": ["Longueur tube ou tubes par palette manquants sur la matière"]}
        return {"quantite": round(pal, 4), "unite": "palette",
                "detail": f"{_n(round(q))} mandrins", "manque": []}

    if kind == "carton":
        upp = _f(mp.get("unites_par_palette"))
        if not upp:
            return {"quantite": None, "unite": "palette",
                    "manque": ["Cartons par palette non renseignés sur la matière"]}
        return {"quantite": round(q / upp, 4), "unite": "palette",
                "detail": f"{_n(round(q))} cartons ÷ {_n(upp)}/palette", "manque": []}

    # Palettes : le besoin est déjà dans l'unité de gestion.
    return {"quantite": round(q, 4), "unite": "palette", "manque": []}


def _etat_documents(pe: dict) -> dict:
    """Validation des deux documents dont dépend le calcul du déstockage.

    Le défalquage lit l'OF et la fiche technique pour décider ce qui sort du
    stock. Si l'un des deux est faux, c'est le stock qui devient faux — et on
    ne s'en aperçoit qu'à l'inventaire suivant. On exige donc que les deux
    aient été relus et validés par quelqu'un avant tout mouvement automatique.
    """
    of_id = pe.get("of_import_id")
    ft_id = pe.get("ft_id")
    of_ok = bool(of_id) and bool(int(pe.get("of_valide") or 0))
    ft_ok = bool(ft_id) and bool(int(pe.get("ft_valide") or 0))

    manquants = []
    if not of_id:
        manquants.append("aucun OF rattaché")
    elif not of_ok:
        manquants.append("OF non validé")
    if not ft_id:
        manquants.append("aucune fiche technique rapprochée")
    elif not ft_ok:
        manquants.append("fiche technique non validée")

    # Une validation qui est TOMBÉE ne se raconte pas comme une validation
    # jamais faite : dans le premier cas un chiffre a bougé sous une relecture
    # déjà acquise, et c'est précisément ce qu'il faut aller regarder.
    motifs = [m for m in (pe.get("of_invalide_motif") if of_id and not of_ok else None,
                          pe.get("ft_invalide_motif") if ft_id and not ft_ok else None)
              if m]

    blocage = None
    if not (of_ok and ft_ok):
        blocage = ("Déstockage impossible tant que les deux documents ne sont "
                   "pas validés — " + ", ".join(manquants) + ".")
        if motifs:
            blocage += " " + " ".join(motifs)

    return {
        "of_id": of_id,
        "of_valide": of_ok,
        "of_valide_par": pe.get("of_valide_par"),
        "of_invalide_at": pe.get("of_invalide_at"),
        "of_invalide_motif": pe.get("of_invalide_motif"),
        "ft_id": ft_id,
        "ft_valide": ft_ok,
        "ft_valide_par": pe.get("ft_valide_par"),
        "ft_invalide_at": pe.get("ft_invalide_at"),
        "ft_invalide_motif": pe.get("ft_invalide_motif"),
        "complet": of_ok and ft_ok,
        "motifs_invalidation": motifs,
        "blocage": blocage,
    }


def _destockage_lignes(conn, planning_id: int) -> dict:
    """Prépare le déstockage d'un dossier : une ligne par matière consommée."""
    dossiers = _load_dossiers(conn, _SQL_PE_UN, (planning_id,))
    if not dossiers:
        raise HTTPException(404, "Dossier introuvable.")
    pe = dossiers[0]
    mapping = _load_mapping(conn)
    perte_pct = stock_config_float(conn, "mandrin_perte_coupe_pct")

    # Le réel prime sur le théorique : on substitue avant de calculer, pour que
    # toute la cascade (métrage → adhésif, étiquettes → mandrins → cartons)
    # reparte des quantités effectivement produites.
    reel = _production_reelle(conn, pe)
    pe_calc = dict(pe)
    if reel["source"] == "reel":
        if reel["metrage"]:
            pe_calc["of_metrage"] = reel["metrage"]
        if reel["etiquettes"]:
            pe_calc["qte_etiquettes"] = reel["etiquettes"]
            # Les bobines de l'OF décrivent le prévu : elles primeraient sur la
            # quantité réelle dans le calcul des mandrins.
            pe_calc["qte_bobines"] = None
            pe_calc["of_nb_mandrins"] = None
            pe_calc["of_nb_cartons"] = None

    besoins = _compute_besoins_dossier(pe_calc, mapping, perte_pct)
    lz = _laize_dossier(pe_calc)

    lignes = []
    for b in besoins:
        mp = mapping.get((b["kind"], (b["source_value"] or "").strip().lower())) or {}
        conv = _quantite_a_destocker(b, mp)
        mid = b.get("matiere_id")
        laizes, laize_suggeree = [], None
        stock = None
        if mid:
            if b["kind"] in _KINDS_BOBINE:
                laizes = _laizes_matiere(conn, mid)
                cible = _f(lz.get("laize"))
                if cible:
                    for l in laizes:
                        if abs(float(l["valeur_mm"] or 0) - cible) < 0.5:
                            laize_suggeree = l["laize_id"]
                            break
                if laize_suggeree is None and len(laizes) == 1:
                    laize_suggeree = laizes[0]["laize_id"]
                if laize_suggeree is not None:
                    stock = next((float(l["stock"]) for l in laizes
                                  if l["laize_id"] == laize_suggeree), None)
            else:
                r = conn.execute(
                    "SELECT quantite FROM mp_stock WHERE matiere_id=?", (mid,)
                ).fetchone()
                stock = float(r["quantite"]) if r else 0.0

        manque = list(conv.get("manque") or [])
        if not b.get("mapped"):
            manque.append("Valeur de fiche non associée à une référence MySifa")
        if b["kind"] in _KINDS_BOBINE and mid and laize_suggeree is None:
            manque.append("Laize du dossier absente des laizes de cette matière — à choisir")

        lignes.append({
            "kind": b["kind"],
            "source_value": b["source_value"],
            "matiere_id": mid,
            "matiere_ref": b.get("matiere_ref"),
            "matiere_designation": b.get("matiere_designation"),
            "mapped": bool(b.get("mapped")),
            "besoin": b.get("quantite"),
            "besoin_unite": b.get("unite"),
            "quantite": conv.get("quantite"),
            "unite": conv.get("unite"),
            "detail": conv.get("detail"),
            "laizee": b["kind"] in _KINDS_BOBINE,
            "laizes": laizes,
            "laize_id": laize_suggeree,
            "stock_actuel": round(stock, 4) if stock is not None else None,
            "manque": manque,
            "destockable": bool(mid) and conv.get("quantite") is not None and (
                b["kind"] not in _KINDS_BOBINE or laize_suggeree is not None),
        })

    deja = [dict(r) for r in conn.execute(
        """SELECT m.id, m.matiere_id, m.type_mouvement, m.quantite, m.quantite_apres,
                  m.laize_id, m.note, m.created_at, m.created_by_name,
                  m.annule_mouvement_id, mp.reference AS matiere_ref
           FROM mp_mouvements m
           LEFT JOIN matieres_premieres mp ON mp.id = m.matiere_id
           WHERE m.planning_entry_id = ?
           ORDER BY m.id""",
        (planning_id,),
    ).fetchall()]

    docs = _etat_documents(pe)
    return {
        "dossier": {
            "planning_id": pe["id"],
            "reference": pe.get("reference"),
            "numero_of": pe.get("numero_of"),
            "client": pe.get("client"),
            "machine": pe.get("machine_nom"),
            "statut": pe.get("statut"),
            "destockage": pe.get("destockage") or "todo",
        },
        "documents": docs,
        "blocage": docs["blocage"],
        "source_calcul": reel["source"],
        "reel": {"metrage": reel["metrage"], "etiquettes": reel["etiquettes"]},
        "theorique": {"metrage": _f(pe.get("of_metrage")),
                      "etiquettes": _f(pe.get("qte_etiquettes"))},
        "laize_dossier": lz.get("laize"),
        "lignes": lignes,
        "mouvements": deja,
    }


@router.get("/api/stock/destockage/{planning_id}")
def destockage_preview(planning_id: int, request: Request):
    """Ce qui sera retiré du stock à la clôture de ce dossier."""
    require_stock_write(request)
    with get_db() as conn:
        return _destockage_lignes(conn, planning_id)


@router.post("/api/stock/destockage/{planning_id}/valider")
async def destockage_valider(planning_id: int, request: Request):
    """Enregistre les sorties de stock d'une production terminée.

    Body : { lignes: [{ matiere_id, quantite, laize_id? }], note? }
    Les quantités viennent de la modale : ce sont celles que l'opératrice a
    validées, pas celles qu'on a calculées. Un ajustement de sa part est donc
    la vérité — le calcul n'était qu'une proposition.
    """
    user = require_stock_write(request)
    body = await request.json()
    lignes = body.get("lignes")
    if not isinstance(lignes, list) or not lignes:
        raise HTTPException(400, "Aucune ligne à déstocker.")
    note_libre = (body.get("note") or "").strip()

    from app.routers.stock import appliquer_mouvement_mp

    with get_db() as conn:
        pe = conn.execute(
            "SELECT id, reference, numero_of, destockage FROM planning_entries WHERE id=?",
            (planning_id,),
        ).fetchone()
        if not pe:
            raise HTTPException(404, "Dossier introuvable.")
        if (pe["destockage"] or "todo") == "done":
            raise HTTPException(400, "Ce dossier est déjà déstocké.")

        # Verrou documentaire : on ne bouge pas le stock sur la foi d'un OF ou
        # d'une fiche que personne n'a relus. Le contrôle est refait ici et pas
        # seulement à l'affichage — un appel direct à l'API doit buter dessus.
        etat = _load_dossiers(conn, _SQL_PE_UN, (planning_id,))
        docs = _etat_documents(etat[0]) if etat else {"complet": False,
            "blocage": "Dossier introuvable."}
        if not docs["complet"]:
            raise HTTPException(400, docs["blocage"])

        no_dossier = (pe["numero_of"] or pe["reference"] or "").strip()
        base_note = f"Déstockage production {no_dossier}".strip()
        if note_libre:
            base_note += f" — {note_libre}"

        faits, negatifs = [], []
        for li in lignes:
            try:
                mid = int(li.get("matiere_id"))
                qte = float(str(li.get("quantite")).replace(",", "."))
            except (TypeError, ValueError):
                raise HTTPException(400, "Ligne invalide (matiere_id / quantité).") from None
            if qte <= 0:
                continue  # une ligne remise à zéro est un refus explicite de déstocker
            laize_id = li.get("laize_id")
            laize_id = int(laize_id) if laize_id not in (None, "") else None
            res = appliquer_mouvement_mp(
                conn, user, mid, "sortie", qte,
                laize_id=laize_id, note=base_note,
                planning_entry_id=planning_id, no_dossier=no_dossier,
                # Les deux documents qui ont servi au calcul. Le dossier seul
                # ne suffit pas : il change d'OF, et une fiche se modifie.
                of_import_id=docs.get("of_id"), fiche_id=docs.get("ft_id"),
                autoriser_negatif=True,
            )
            faits.append({"matiere_id": mid, **res})
            if res["negatif"]:
                negatifs.append(mid)

        if not faits:
            raise HTTPException(400, "Toutes les lignes sont à zéro : rien à déstocker.")

        conn.execute(
            "UPDATE planning_entries SET destockage='done', updated_at=? WHERE id=?",
            (datetime.now().isoformat(), planning_id),
        )
        conn.commit()

    return {"success": True, "destockage": "done", "mouvements": faits,
            "stocks_negatifs": negatifs}


@router.post("/api/stock/destockage/{planning_id}/annuler")
async def destockage_annuler(planning_id: int, request: Request):
    """Contre-passe le déstockage d'un dossier.

    On n'efface rien : chaque sortie est annulée par une entrée de même
    quantité, rattachée à l'originale. Les deux écritures restent à
    l'historique — c'est la seule façon honnête de raconter qu'on s'est trompé.
    """
    user = require_stock_write(request)
    from app.routers.stock import appliquer_mouvement_mp

    with get_db() as conn:
        pe = conn.execute(
            "SELECT id, reference, numero_of, destockage FROM planning_entries WHERE id=?",
            (planning_id,),
        ).fetchone()
        if not pe:
            raise HTTPException(404, "Dossier introuvable.")

        no_dossier = (pe["numero_of"] or pe["reference"] or "").strip()
        # Sorties de ce dossier qui n'ont pas déjà été contre-passées.
        a_annuler = conn.execute(
            """SELECT m.id, m.matiere_id, m.quantite, m.laize_id
               FROM mp_mouvements m
               WHERE m.planning_entry_id = ?
                 AND m.type_mouvement = 'sortie'
                 AND m.annule_mouvement_id IS NULL
                 AND NOT EXISTS (SELECT 1 FROM mp_mouvements c
                                 WHERE c.annule_mouvement_id = m.id)
               ORDER BY m.id""",
            (planning_id,),
        ).fetchall()

        rendus = []
        for m in a_annuler:
            res = appliquer_mouvement_mp(
                conn, user, int(m["matiere_id"]), "entree", float(m["quantite"]),
                laize_id=m["laize_id"],
                note=f"Annulation déstockage production {no_dossier}",
                planning_entry_id=planning_id, no_dossier=no_dossier,
                annule_mouvement_id=int(m["id"]),
            )
            rendus.append({"matiere_id": m["matiere_id"], **res})

        conn.execute(
            "UPDATE planning_entries SET destockage='todo', updated_at=? WHERE id=?",
            (datetime.now().isoformat(), planning_id),
        )
        conn.commit()

    return {"success": True, "destockage": "todo", "mouvements": rendus}


@router.get("/api/stock/besoins-matieres/mapping")
def list_mapping(request: Request):
    """Liste toutes les correspondances FT→MP + valeurs FT non mappées détectées
    dans les dossiers actifs (pour aider à peupler la table)."""
    require_stock_matieres_admin(request)
    with get_db() as conn:
        maps = [dict(r) for r in conn.execute("""
            SELECT m.id, m.kind, m.source_value, m.matiere_id, m.notes,
                   m.created_at, m.updated_at,
                   mp.reference AS matiere_ref, mp.designation AS matiere_designation,
                   mp.categorie AS matiere_categorie
            FROM mp_fiche_mapping m
            JOIN matieres_premieres mp ON mp.id = m.matiere_id
            ORDER BY m.kind, LOWER(m.source_value)
        """).fetchall()]
        rows = _load_dossiers(conn)

    mapping_keys = {(m["kind"], (m["source_value"] or "").strip().lower()) for m in maps}
    seen: dict = {}
    for pe in rows:
        for kind, col in (("support", "ft_support"), ("glassine", "ft_glassine"),
                          ("adhesif", "ft_adhesif"),
                          ("mandrin", "ft_mandrin_dia"), ("carton", "ft_cartons"),
                          ("palette", "ft_palette_type")):
            v = pe.get(col)
            if not v or not str(v).strip():
                continue
            key = (kind, str(v).strip().lower())
            if key in mapping_keys:
                continue
            if key not in seen:
                seen[key] = {"kind": kind, "source_value": str(v).strip(), "count": 0}
            seen[key]["count"] += 1
    non_mappe = sorted(seen.values(), key=lambda x: (x["kind"], -x["count"]))
    return {"mapping": maps, "non_mappe": non_mappe}


@router.post("/api/stock/besoins-matieres/mapping")
async def upsert_mapping(request: Request):
    """Crée ou met à jour une correspondance FT→MP.
    Body : { kind, source_value, matiere_id, notes? }"""
    require_stock_matieres_admin(request)
    body = await request.json()
    kind = (body.get("kind") or "").strip()
    source_value = (body.get("source_value") or "").strip()
    matiere_id = body.get("matiere_id")
    notes = (body.get("notes") or "").strip() or None
    if kind not in _KINDS:
        raise HTTPException(400, f"kind invalide (attendu : {'|'.join(_KINDS)})")
    if not source_value:
        raise HTTPException(400, "source_value requis")
    try:
        matiere_id = int(matiere_id)
    except (TypeError, ValueError):
        raise HTTPException(400, "matiere_id numérique requis")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        if not conn.execute("SELECT id FROM matieres_premieres WHERE id=?", (matiere_id,)).fetchone():
            raise HTTPException(404, "Matière introuvable")
        existing = conn.execute(
            "SELECT id FROM mp_fiche_mapping WHERE kind=? AND LOWER(TRIM(source_value))=LOWER(TRIM(?)) LIMIT 1",
            (kind, source_value),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE mp_fiche_mapping SET matiere_id=?, notes=?, updated_at=? WHERE id=?",
                (matiere_id, notes, now, existing["id"]),
            )
            new_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO mp_fiche_mapping (kind, source_value, matiere_id, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (kind, source_value, matiere_id, notes, now, now),
            )
            new_id = cur.lastrowid
        conn.commit()
    return {"ok": True, "id": new_id}


@router.delete("/api/stock/besoins-matieres/mapping/{map_id}")
def delete_mapping(request: Request, map_id: int):
    require_stock_matieres_admin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM mp_fiche_mapping WHERE id=?", (map_id,))
        conn.commit()
    return {"ok": True}


# ── Documentation du calcul (modal « ? » de MyStock) ───────────────────
#
# Source unique de vérité : le front n'invente rien, il affiche ce bloc.
# Toute modification d'une formule ci-dessus doit être répercutée ici.

_EXPLICATIONS = {
    "intro": (
        "Les besoins sont calculés à partir des dossiers du planning en statut "
        "« en attente » ou « en cours ». Chaque dossier est rapproché de sa fiche "
        "technique (par référence produit normalisée, avec priorité à la fiche de "
        "la machine du dossier), puis de son OF importé quand il existe. Les "
        "valeurs libres des fiches (support, glassine, adhésif, mandrin, carton, "
        "palette) sont converties en références de matières premières via la table "
        "de correspondances."
    ),
    "sections": [
        {
            "id": "mapping",
            "titre": "Correspondances fiche technique → matière première",
            "type": "mappe",
            "resume": "Comment une valeur texte de fiche devient une référence MyStock.",
            "paragraphes": [
                "Les fiches techniques contiennent du texte libre : « PP BLANC 60 », "
                "« GLASSINE BLANCHE 60 », « Carton 400×300 »… MyStock ne sait pas "
                "relier ce texte à une référence tant qu'une correspondance n'a pas "
                "été enregistrée.",
                "La correspondance se fait sur le couple (type, valeur texte), en "
                "ignorant la casse et les espaces de bord. Une même valeur peut donc "
                "exister pour deux types différents sans conflit.",
                "Tant qu'une valeur n'est pas associée, son besoin est calculé et "
                "affiché, mais sans stock ni manque : la ligne apparaît en orange "
                "avec le bouton « Associer ».",
            ],
            "variables": [
                {"label": "Type", "champ": "mp_fiche_mapping.kind",
                 "detail": "support, glassine, adhesif, mandrin, carton ou palette"},
                {"label": "Valeur source", "champ": "mp_fiche_mapping.source_value",
                 "detail": "le texte lu dans la fiche technique"},
                {"label": "Matière", "champ": "mp_fiche_mapping.matiere_id",
                 "detail": "la référence de matieres_premieres visée"},
            ],
        },
        {
            "id": "metrage",
            "titre": "Métrage du dossier",
            "type": "calcul",
            "resume": "Base commune de tous les besoins bobine et adhésif.",
            "formule": "Métrage = of_imports.metrage",
            "formule_repli": "Métrage = qté étiquettes ÷ nb de front × longueur module ÷ 1000",
            "paragraphes": [
                "C'est l'OF qui porte la quantité d'étiquettes à produire, donc le "
                "métrage : on lit directement le métrage de l'OF importé.",
                "Si le dossier n'a pas d'OF importé, on reconstitue le métrage depuis "
                "la géométrie de la fiche technique : le nombre de tours de module "
                "(quantité ÷ nb de front) multiplié par la longueur du module, en "
                "millimètres, ramenée en mètres.",
                "La provenance du métrage est indiquée sur chaque ligne : « OF » ou "
                "« fiche ».",
            ],
            "variables": [
                {"label": "Métrage OF", "champ": "of_imports.metrage",
                 "unite": "m", "detail": "source prioritaire"},
                {"label": "Quantité étiquettes", "champ": "of_imports.qte_etiquettes",
                 "unite": "étiq", "detail": "repli"},
                {"label": "Nb de front", "champ": "fiches_techniques.mod_nb_front",
                 "unite": "", "detail": "repli — étiquettes en largeur"},
                {"label": "Longueur module", "champ": "fiches_techniques.mod_longueur",
                 "unite": "mm", "detail": "repli — développé d'un tour"},
            ],
        },
        {
            "id": "support",
            "titre": "Support (frontal / complexe)",
            "type": "calcul",
            "resume": "Besoin en mètres linéaires.",
            "formule": "Besoin (ml) = Métrage",
            "paragraphes": [
                "Une matière en bobine se consomme au mètre linéaire : toute la "
                "longueur de l'OF traverse la machine, quelle que soit la taille des "
                "étiquettes découpées dedans.",
                "Le stock, tenu en bobines, est converti en mètres linéaires pour "
                "être comparable : bobines × métrage par bobine de la matière. Si le "
                "métrage par bobine n'est pas renseigné sur la fiche matière, le "
                "stock et le manque restent vides.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.support",
                 "detail": "texte mappé vers une matière frontal ou complexe"},
                {"label": "Métrage", "champ": "voir « Métrage du dossier »", "unite": "m"},
                {"label": "Métrage par bobine",
                 "champ": "matieres_premieres.metres_lineaires_par_bobine",
                 "unite": "m", "detail": "sert à convertir le stock en ml"},
            ],
        },
        {
            "id": "glassine",
            "titre": "Glassine",
            "type": "calcul",
            "resume": "Besoin en mètres linéaires.",
            "formule": "Besoin (ml) = Métrage",
            "paragraphes": [
                "Même logique que le support : la glassine (le dorsal siliconé) "
                "défile sur toute la longueur de l'OF.",
                "La valeur source vient du champ « Glassine » de la fiche technique, "
                "distinct du support. Un dossier peut donc générer deux besoins "
                "bobine du même métrage.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.glassine",
                 "detail": "texte mappé vers une matière de catégorie glassine"},
                {"label": "Métrage", "champ": "voir « Métrage du dossier »", "unite": "m"},
            ],
        },
        {
            "id": "adhesif",
            "titre": "Adhésif",
            "type": "calcul",
            "resume": "Besoin en kilos, via le grammage et la surface enduite.",
            "formule": "Besoin (kg) = Grammage (g/m²) × Métrage (m) × Laize (mm) ÷ 1000 ÷ 1000",
            "paragraphes": [
                "L'adhésif se stocke et s'achète au kilo. On passe donc par la "
                "surface enduite : le métrage multiplié par la laize donne des m², "
                "que le grammage convertit en grammes, puis en kilos.",
                "Le grammage (g/m²) est une caractéristique de la référence "
                "adhésif : il se saisit sur la fiche matière. Tant qu'il n'est "
                "pas renseigné, on utilise en repli le champ « Grammage » de la "
                "fiche technique (colonne qte_au_mille).",
                "La laize retenue est celle de l'OF — la laize réellement lancée. "
                "En l'absence d'OF, on prend la laize optimale de la fiche technique, "
                "puis la laize simple.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.adhesif",
                 "detail": "texte mappé vers une matière de catégorie adhésif"},
                {"label": "Grammage", "champ": "matieres_premieres.weight_gsm",
                 "unite": "g/m²",
                 "detail": "saisi sur la fiche matière ; replis successifs : "
                           "weight_per_m2 (kg/m² × 1000), puis "
                           "fiches_techniques.qte_au_mille"},
                {"label": "Métrage", "champ": "voir « Métrage du dossier »", "unite": "m"},
                {"label": "Laize", "champ": "of_imports.laize",
                 "unite": "mm",
                 "detail": "repli : fiches_techniques.laize_optimale puis .laize"},
            ],
        },
        {
            "id": "mandrin",
            "titre": "Mandrins",
            "type": "calcul",
            "resume": "Besoin en mandrins — un par bobine produite, traduit en "
                      "tubes puis en palettes à commander.",
            "formule": "Besoin (u) = Quantité étiquettes ÷ Étiquettes par bobine · "
                       "Tubes = Mandrins × Laize module ÷ (Longueur tube − perte de coupe)",
            "paragraphes": [
                "Chaque bobine finie consomme un mandrin. Le nombre de bobines a "
                "trois sources possibles, lues dans cet ordre : le nombre de mandrins "
                "chiffré sur l'OF, la quantité de bobines de l'OF, puis la quantité "
                "d'étiquettes divisée par le nombre d'étiquettes par bobine.",
                "Ce dernier nombre vient du champ « Nb étiq./bobine » de la fiche "
                "technique ; s'il est vide, il est relu dans la phrase de "
                "conditionnement (« Bobine de 1.000 étiquettes »), sur la fiche puis "
                "sur l'OF. C'est ce qui évite qu'une fiche complète par ailleurs "
                "sorte « n.c. » sur les mandrins, les cartons et les palettes.",
                "Les mandrins ne s'achètent pas à l'unité : ils sont découpés dans "
                "des tubes. Un tube donne, une fois la perte de coupe retirée, autant "
                "de mandrins que la laize du module tient de fois dans sa longueur. "
                "La longueur du tube et le nombre de tubes par palette se saisissent "
                "sur la fiche matière du mandrin, la perte de coupe dans "
                "Paramètres → Mandrins.",
                "Ce résultat sert aussi de base au calcul des cartons.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.mandrin_dia",
                 "detail": "diamètre mandrin, mappé vers une référence mandrin"},
                {"label": "Quantité étiquettes", "champ": "of_imports.qte_etiquettes",
                 "unite": "étiq"},
                {"label": "Étiquettes par bobine",
                 "champ": "fiches_techniques.nb_etiq_bobin ou conditionnement",
                 "unite": "", "detail": "repli sur « Bobine de N étiquettes »"},
                {"label": "Mandrins / bobines de l'OF",
                 "champ": "of_imports.nb_mandrins ou qte_bobines",
                 "detail": "prioritaires quand l'OF les renseigne"},
                {"label": "Laize module", "champ": "fiches_techniques.mod_laize",
                 "unite": "mm", "detail": "hauteur du mandrin découpé dans le tube"},
                {"label": "Longueur tube", "champ": "matieres_premieres.longueur_tube_mm",
                 "unite": "mm"},
                {"label": "Tubes par palette", "champ": "matieres_premieres.unites_par_palette",
                 "unite": ""},
                {"label": "Perte de coupe", "champ": "stock_config.mandrin_perte_coupe_pct",
                 "unite": "%"},
            ],
        },
        {
            "id": "carton",
            "titre": "Cartons",
            "type": "calcul",
            "resume": "Besoin en unités — chiffré sur l'OF, sinon reconstruit "
                      "depuis le calcul des mandrins.",
            "formule": "Besoin (u) = Nb de cartons de l'OF, "
                       "sinon Nb de bobines ÷ Bobines par carton",
            "paragraphes": [
                "Quand l'OF chiffre lui-même les cartons, c'est cette valeur qui fait "
                "foi : elle décrit la commande réelle, pas une reconstitution.",
                "Sinon, le nombre de bobines est celui calculé pour les mandrins. S'il "
                "n'est pas calculable, le besoin en cartons ne l'est pas non plus.",
                "Le stock, lui, est tenu en palettes : il est converti en cartons via "
                "« Cartons par palette » de la fiche matière. Sans ce champ, le stock "
                "reste affiché comme non comparable plutôt que confondu avec un "
                "nombre de palettes.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.cartons"},
                {"label": "Cartons de l'OF", "champ": "of_imports.nb_cartons",
                 "detail": "prioritaire quand l'OF le renseigne"},
                {"label": "Nb de bobines", "champ": "voir « Mandrins »", "unite": "bobines"},
                {"label": "Bobines par carton", "champ": "fiches_techniques.nb_bobines_carton",
                 "unite": ""},
                {"label": "Cartons par palette", "champ": "matieres_premieres.unites_par_palette",
                 "unite": "", "detail": "conversion du stock, tenu en palettes"},
            ],
        },
        {
            "id": "palette",
            "titre": "Palettes",
            "type": "calcul",
            "resume": "Besoin en unités — dépend du calcul des cartons.",
            "formule": "Besoin (u) = Nb de cartons ÷ (Cartons au sol × Cartons en hauteur)",
            "paragraphes": [
                "Le plan de palettisation de la fiche technique donne le nombre de "
                "cartons par palette. Une palette entamée compte pour une fraction : "
                "le total est arrondi à l'affichage, pas dans le calcul.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.palette_type"},
                {"label": "Nb de cartons", "champ": "voir « Cartons »", "unite": "cartons"},
                {"label": "Cartons au sol", "champ": "fiches_techniques.palette_nb_cartons_sol"},
                {"label": "Cartons en hauteur", "champ": "fiches_techniques.palette_nb_cartons_hauteur"},
            ],
        },
        {
            "id": "fenetres",
            "titre": "Fenêtres 7 jours / 15 jours",
            "type": "calcul",
            "resume": "Comment un dossier est réparti dans le temps.",
            "formule": "Besoin fenêtre = Besoin total × (jours du dossier dans la fenêtre ÷ durée du dossier)",
            "paragraphes": [
                "Un dossier entièrement contenu dans la fenêtre compte pour 100 %. "
                "Un dossier entièrement après la borne compte pour 0 %.",
                "Un dossier à cheval sur la borne est réparti au prorata des jours "
                "qui tombent dans la fenêtre.",
                "Un dossier en retard (fin prévue déjà passée) compte pour 100 % : "
                "le besoin est immédiat. Un dossier sans aucune date compte aussi "
                "pour 100 %.",
            ],
            "variables": [
                {"label": "Début prévu", "champ": "planning_entries.planned_start"},
                {"label": "Fin prévue", "champ": "planning_entries.planned_end",
                 "detail": "repli : date_livraison"},
            ],
        },
        {
            "id": "stock",
            "titre": "Stock et manque",
            "type": "calcul",
            "resume": "Pourquoi le stock affiché peut différer de la fiche matière.",
            "formule": "Manque 7j = max(0 ; Besoin 7j − Stock)",
            "paragraphes": [
                "Le stock est toujours ramené dans l'unité du besoin, sinon la "
                "soustraction n'aurait pas de sens.",
                "Bobines (support, glassine) : stock en bobines × métrage par bobine "
                "→ mètres linéaires. Sans métrage par bobine renseigné, le stock "
                "reste vide.",
                "Adhésif : le stock est déjà tenu au kilo, il est utilisé tel quel.",
                "Mandrins, cartons, palettes : stock repris tel quel.",
            ],
            "variables": [
                {"label": "Stock bobines", "champ": "mp_stock_laize.quantite",
                 "unite": "bobines"},
                {"label": "Stock autres", "champ": "mp_stock.quantite"},
                {"label": "Métrage par bobine",
                 "champ": "matieres_premieres.metres_lineaires_par_bobine", "unite": "m"},
            ],
        },
    ],
}


@router.get("/api/stock/besoins-matieres/explications")
def explications(request: Request):
    """Documentation du mapping et des formules, consommée par le modal « ? »."""
    require_stock_matieres_admin(request)
    return _EXPLICATIONS
