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
- mandrins (u)  : qte_etiquettes / nb_etiq_bobin
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
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.routers.stock import require_stock_matieres_admin, stock_config_float

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
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19]).date()
    except (TypeError, ValueError):
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None


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
           pe.position,
           m.nom AS machine_nom,
           oi.qte_etiquettes AS qte_etiquettes,
           oi.qte_bobines    AS qte_bobines,
           oi.metrage        AS of_metrage,
           oi.laize          AS of_laize
    FROM planning_entries pe
    LEFT JOIN machines m ON m.id = pe.machine_id
    LEFT JOIN of_imports oi ON oi.id = pe.of_import_id
    WHERE pe.statut IN ('attente', 'en_cours')
    ORDER BY COALESCE(pe.planned_start, pe.date_livraison, '9999'), pe.position
"""

_SQL_FT = """
    SELECT id, reference, ref_produit_norm, machine,
           support, glassine, adhesif, qte_au_mille, eti_laize, eti_longueur,
           mod_laize, mod_longueur, mod_nb_front, laize, laize_optimale,
           mandrin_dia, nb_etiq_bobin, nb_bobines_carton, cartons,
           palette_type, palette_nb_cartons_sol, palette_nb_cartons_hauteur
    FROM fiches_techniques
"""

_FT_FIELDS = (
    "support", "glassine", "adhesif", "qte_au_mille", "eti_laize", "eti_longueur",
    "mod_laize", "mod_longueur", "mod_nb_front", "laize", "laize_optimale",
    "mandrin_dia", "nb_etiq_bobin", "nb_bobines_carton", "cartons",
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


def _load_dossiers(conn) -> list:
    """Dossiers du planning (attente/en_cours) + fiche technique associée.

    Tie-breaker machine identique à planning.py : fiche dont `machine`
    correspond à la machine du dossier > fiche sans machine > autre, puis
    id croissant. Chaque dossier reçoit les champs ft_* (None si aucune fiche).
    """
    pes = [dict(r) for r in conn.execute(_SQL_PE).fetchall()]
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
    nb_front = _f(pe.get("ft_mod_nb_front"))
    mod_long = _f(pe.get("ft_mod_longueur"))
    if qte and nb_front and mod_long:
        return {
            "metrage": qte / nb_front * mod_long / 1000.0,
            "source": "fiche",
            "variables": [
                {"label": "Quantité étiquettes", "champ": "of_imports.qte_etiquettes",
                 "origine": "OF", "valeur": qte, "unite": "étiq"},
                {"label": "Nb de front", "champ": "fiches_techniques.mod_nb_front",
                 "origine": "Fiche technique", "valeur": nb_front, "unite": ""},
                {"label": "Longueur module", "champ": "fiches_techniques.mod_longueur",
                 "origine": "Fiche technique", "valeur": mod_long, "unite": "mm"},
            ],
            "manque": [],
        }

    manque = []
    if not of_metrage:
        manque.append("Métrage de l'OF (of_imports.metrage)")
    if not qte:
        manque.append("Quantité d'étiquettes de l'OF")
    if not nb_front:
        manque.append("Nb de front de la fiche technique (mod_nb_front)")
    if not mod_long:
        manque.append("Longueur module de la fiche technique (mod_longueur)")
    return {"metrage": None, "source": None, "variables": [], "manque": manque}


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

    # ── Bobines (frontal / complexe / glassine) : besoin en mètres linéaires ──
    # Toutes les bobines d'un dossier voient passer le même métrage.
    for kind, col in (("support", "ft_support"), ("glassine", "ft_glassine")):
        if not pe.get(col):
            continue
        if metrage:
            src = "métrage OF" if met["source"] == "of" else "métrage calculé fiche"
            _add(kind, pe[col], metrage,
                 f"{_n(metrage, 'm')} ({src})", met["variables"])
        else:
            _add(kind, pe[col], None, "Métrage indisponible",
                 met["variables"], met["manque"])

    # ── Adhésif : kilos = grammage (g/m²) × surface enduite (m²) ──
    # surface = métrage (m) × laize (mm) / 1000
    if pe.get("ft_adhesif"):
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
    nb_eb = _f(pe.get("ft_nb_etiq_bobin"))
    nb_mandrins = 0.0
    if pe.get("ft_mandrin_dia"):
        if qte and nb_eb:
            nb_mandrins = qte / nb_eb
            tub = _mandrin_tubes(pe, mapping, nb_mandrins, perte_pct)
            variables = [
                {"label": "Quantité étiquettes", "champ": "of_imports.qte_etiquettes",
                 "origine": "OF", "valeur": qte, "unite": "étiq"},
                {"label": "Étiquettes par bobine", "champ": "fiches_techniques.nb_etiq_bobin",
                 "origine": "Fiche technique", "valeur": nb_eb, "unite": ""},
            ]
            formule = f"{_n(qte)} étiq ÷ {_n(nb_eb)} étiq/bobine"
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
            manque = []
            if not qte:
                manque.append("Quantité d'étiquettes de l'OF")
            if not nb_eb:
                manque.append("Étiquettes par bobine (nb_etiq_bobin)")
            _add("mandrin", pe["ft_mandrin_dia"], None,
                 "Calcul impossible", [], manque)

    # ── Cartons : nb bobines / bobines par carton ──
    nb_bc = _f(pe.get("ft_nb_bobines_carton"))
    nb_cartons = 0.0
    if pe.get("ft_cartons"):
        if nb_bc and nb_mandrins > 0:
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
            "of_metrage": pe.get("of_metrage"),
            "of_laize": pe.get("of_laize"),
            "besoins": besoins,
            "besoins_mapped_count": sum(1 for b in besoins if b["mapped"]),
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
                }
            a = agg[key]
            a["nb_dossiers"] += 1
            if not b["calculable"]:
                a["nb_dossiers_incalculables"] += 1
                continue
            a["besoin_7j"] += b["quantite"] * r7
            a["besoin_15j"] += b["quantite"] * r15
            a["besoin_total"] += b["quantite"]
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
    return {
        "lignes": lignes,
        "count": len(lignes),
        "today": today.isoformat(),
        "borne_7j": borne_7.isoformat(),
        "borne_15j": borne_15.isoformat(),
    }


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
                "Chaque bobine finie consomme un mandrin. Le nombre de bobines se "
                "déduit de la quantité à produire divisée par le nombre d'étiquettes "
                "par bobine défini sur la fiche technique.",
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
                {"label": "Étiquettes par bobine", "champ": "fiches_techniques.nb_etiq_bobin",
                 "unite": ""},
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
            "resume": "Besoin en unités — dépend du calcul des mandrins.",
            "formule": "Besoin (u) = Nb de bobines ÷ Bobines par carton",
            "paragraphes": [
                "Le nombre de bobines est celui calculé pour les mandrins. S'il n'est "
                "pas calculable, le besoin en cartons ne l'est pas non plus.",
            ],
            "variables": [
                {"label": "Valeur source", "champ": "fiches_techniques.cartons"},
                {"label": "Nb de bobines", "champ": "voir « Mandrins »", "unite": "bobines"},
                {"label": "Bobines par carton", "champ": "fiches_techniques.nb_bobines_carton",
                 "unite": ""},
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
