"""
Compte-rendu de dossier de production — centralisation.

Ce que la production d'un dossier a produit comme information est aujourd'hui
eclate sur cinq tables et quatre ecrans : les temps et le metrage dans
`production_data`, l'info prod de cloture dans `dossier_info_prod`, les
commentaires de saisie figes dans `produit_series`, les seuils d'arret franchis
et le mot du conducteur dans `arret_seuils_franchis`, les non-conformites dans
`nc_dossiers`. Personne ne voit l'ensemble, et surtout pas celui qui l'a ecrit.

Ce module assemble le tout en un objet unique par dossier, et agrege ces objets
par machine et par semaine pour le retour a l'atelier.

Deux principes de conception :

1. `conn` et rien d'autre. Aucun import de `database`, `config` ou FastAPI :
   le module se teste sur une base sqlite en memoire (voir
   `tests/test_rapport_dossier.py`) et les codes d'operation arrivent en
   parametres, jamais en dur.

2. Les chiffres reprennent les conventions du rapport hebdomadaire qui
   precedait ce module (`app/services/weekly_report.py`, supprime le
   28/08/2026 — voir l'historique git), pour qu'un dossier n'affiche jamais
   deux valeurs selon l'ecran :

   - duree d'une saisie = ecart avec la saisie suivante DU MEME OPERATEUR,
     saisies annulees exclues (`est_annule`) ;
   - temps de production = somme des saisies de categorie `production` ;
   - metrage du dossier = MAX - MIN des `metrage_reel` releves sur le code de
     fin, parce que l'operateur releve un compteur machine et non un delta ;
     une valeur unique n'est retenue que sous `SEUIL_COMPTEUR`.

   Une seule chose est calculee plus largement, et elle est nommee autrement :
   l'ancien rapport intitulait « calage » le seul code 02, alors que le
   referentiel compte plusieurs codes de calage et de changement. Ici la ligne
   s'appelle « calage et changements » et couvre toute la categorie.

Sur le plafonnement : l'ecart entre deux saisies n'est pas plafonne, comme dans
l'ancien rapport hebdomadaire. Mais une journee terminee sans code de fin
laisse une saisie ouverte jusqu'au lendemain, et le temps qui en sort n'est pas
du temps machine. Ces ecarts sont donc comptes dans `minutes` ET isoles dans
`minutes_douteuses`, ce qui permet a l'ecran de le dire au lieu de le taire.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

# Au-dela de cet ecart entre deux saisies d'un meme operateur, on ne regarde
# plus un arret machine mais une fin de journee. Meme valeur que
# `app/services/arret_seuils.py`.
ECART_MAX_MIN = 480.0

# Au-dela de ce metrage, une valeur unique relevee en fin de dossier est un
# compteur machine brut, pas une production. Seuil repris de l'ancien rapport.
SEUIL_COMPTEUR = 1_000_000.0

# Categories du referentiel operations.json, telles qu'elles sont stockees sur
# chaque saisie (`production_data.operation_category`). Lire la colonne plutot
# que le fichier : c'est la categorie au moment de la saisie qui fait foi.
CAT_PRODUCTION = "production"
CAT_CALAGE = "calage"
CAT_ARRET = "arret"
CAT_NETTOYAGE = "nettoyage"
CAT_PAUSE = "pause"

LIBELLES_CATEGORIES: Dict[str, str] = {
    CAT_PRODUCTION: "Production",
    CAT_CALAGE: "Calage et changements",
    CAT_ARRET: "Arrets",
    CAT_NETTOYAGE: "Nettoyage",
    CAT_PAUSE: "Pauses",
    "appro": "Approvisionnement",
    "technique": "Intervention technique",
    "personnel": "Entrees et sorties",
}

# Categories qui pesent sur la disponibilite machine — celles dont on parle a
# l'atelier. `pause` et `personnel` en sont volontairement exclues : ce n'est
# pas la machine qui s'arrete, c'est la journee qui s'organise.
CATEGORIES_COUTEUSES = (CAT_ARRET, "appro", "technique")


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def _table_existe(conn, nom: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone() is not None


def _colonnes(conn, table: str) -> set:
    if not _table_existe(conn, table):
        return set()
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _f(valeur: Any, defaut: float = 0.0) -> float:
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return defaut


def _txt(valeur: Any) -> str:
    return ("" if valeur is None else str(valeur)).strip()


def _dt(valeur: Any) -> Optional[datetime]:
    """`date_operation` est stocke en '%Y-%m-%dT%H:%M:%S', heure Paris."""
    s = _txt(valeur)
    if not s:
        return None
    s = s.replace(" ", "T")[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def mediane(valeurs: Sequence[float]) -> Optional[float]:
    vals = sorted(v for v in valeurs if v is not None)
    if not vals:
        return None
    n = len(vals)
    milieu = n // 2
    if n % 2:
        return float(vals[milieu])
    return (float(vals[milieu - 1]) + float(vals[milieu])) / 2.0


def _ecart_pct(valeur: Optional[float], repere: Optional[float]) -> Optional[float]:
    if valeur is None or not repere:
        return None
    return (float(valeur) - float(repere)) / float(repere) * 100.0


def _minutes_txt(minutes: Optional[float]) -> str:
    """'95' -> '1 h 35'. Sert aussi bien a l'ecran qu'a la feuille imprimee."""
    if minutes is None:
        return "—"
    m = int(round(float(minutes)))
    if m < 60:
        return f"{m} min"
    h, reste = divmod(m, 60)
    return f"{h} h" if reste == 0 else f"{h} h {reste:02d}"


# ─── Saisies et temps ────────────────────────────────────────────────────────

def _saisies(conn, no_dossier: str) -> List[Dict[str, Any]]:
    """Saisies non annulees du dossier, triees par operateur puis par date.

    L'ordre importe : la duree d'une saisie est l'ecart avec la suivante du
    meme operateur. Deux conducteurs sur la meme machine ne se chainent pas.
    """
    cols = _colonnes(conn, "production_data")
    if not cols:
        return []
    optionnelles = [c for c in (
        "commentaire", "est_annule", "annule_motif", "annule_par", "annule_le",
        "metrage_reel", "metrage_prevu", "nb_cartons",
    ) if c in cols]
    champs = ["id", "operateur", "date_operation", "operation", "operation_code",
              "operation_category", "machine", "no_dossier", "client",
              "designation", "quantite_a_traiter", "quantite_traitee"]
    champs = [c for c in champs if c in cols] + optionnelles
    filtre_annule = " AND COALESCE(est_annule, 0) = 0" if "est_annule" in cols else ""
    rows = conn.execute(
        f"""SELECT {', '.join(champs)}
              FROM production_data
             WHERE TRIM(COALESCE(no_dossier, '')) = TRIM(?){filtre_annule}
             ORDER BY operateur, date_operation, id""",
        (no_dossier,),
    ).fetchall()
    return [dict(r) for r in rows]


def temps_par_categorie(saisies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Repartition du temps du dossier, par categorie d'operation.

    Chaque saisie porte le temps qui la separe de la suivante du meme
    operateur. `minutes` ne plafonne rien, pour rester aligne sur le rapport
    hebdomadaire ; `minutes_douteuses` isole les ecarts qui depassent
    ECART_MAX_MIN, c'est-a-dire les saisies restees ouvertes d'un jour a
    l'autre.
    """
    par_cat: Dict[str, Dict[str, float]] = {}
    par_code: Dict[str, Dict[str, Any]] = {}
    ouvertes: List[Dict[str, Any]] = []

    par_operateur: Dict[str, List[Dict[str, Any]]] = {}
    for s in saisies:
        par_operateur.setdefault(_txt(s.get("operateur")), []).append(s)

    for _op, lignes in par_operateur.items():
        lignes = sorted(lignes, key=lambda r: (_txt(r.get("date_operation")), r.get("id") or 0))
        for i, ligne in enumerate(lignes):
            debut = _dt(ligne.get("date_operation"))
            suivante = lignes[i + 1] if i + 1 < len(lignes) else None
            fin = _dt(suivante.get("date_operation")) if suivante else None
            if debut is None or fin is None:
                continue
            minutes = (fin - debut).total_seconds() / 60.0
            if minutes <= 0:
                continue
            douteuse = minutes > ECART_MAX_MIN

            cat = _txt(ligne.get("operation_category")).lower() or "autre"
            bloc = par_cat.setdefault(cat, {"minutes": 0.0, "minutes_douteuses": 0.0,
                                            "occurrences": 0.0})
            bloc["minutes"] += minutes
            bloc["occurrences"] += 1
            if douteuse:
                bloc["minutes_douteuses"] += minutes

            code = _txt(ligne.get("operation_code"))
            detail = par_code.setdefault(code, {
                "code": code,
                "operation": _txt(ligne.get("operation")),
                "categorie": cat,
                "minutes": 0.0,
                "occurrences": 0,
            })
            detail["minutes"] += minutes
            detail["occurrences"] += 1

            if douteuse:
                ouvertes.append({
                    "saisie_id": ligne.get("id"),
                    "operateur": _txt(ligne.get("operateur")),
                    "date_operation": _txt(ligne.get("date_operation")),
                    "operation": _txt(ligne.get("operation")),
                    "code": code,
                    "minutes": minutes,
                })

    total = sum(b["minutes"] for b in par_cat.values())
    categories = []
    for cat, bloc in par_cat.items():
        categories.append({
            "categorie": cat,
            "label": LIBELLES_CATEGORIES.get(cat, cat.capitalize() if cat else "Autre"),
            "minutes": round(bloc["minutes"], 1),
            "minutes_douteuses": round(bloc["minutes_douteuses"], 1),
            "occurrences": int(bloc["occurrences"]),
            "part_pct": round(bloc["minutes"] / total * 100.0, 1) if total > 0 else 0.0,
        })
    categories.sort(key=lambda c: -c["minutes"])

    codes = sorted(par_code.values(), key=lambda c: -c["minutes"])
    for c in codes:
        c["minutes"] = round(c["minutes"], 1)

    return {
        "total_minutes": round(total, 1),
        "categories": categories,
        "par_code": codes,
        "saisies_ouvertes": sorted(ouvertes, key=lambda o: -o["minutes"]),
    }


def _minutes_de(temps: Dict[str, Any], categorie: str) -> float:
    for c in temps.get("categories", []):
        if c["categorie"] == categorie:
            return float(c["minutes"])
    return 0.0


# ─── Metrage ─────────────────────────────────────────────────────────────────

def metrage_dossier(saisies: List[Dict[str, Any]], code_fin: str) -> Dict[str, Any]:
    """Metrage produit, deduit des releves de compteur en fin de session.

    Convention reprise de l'ancien rapport : l'operateur releve un compteur
    machine, donc plusieurs sessions donnent plusieurs valeurs croissantes.
    Le metrage produit est leur ecart. Une valeur unique n'est retenue que si
    elle ressemble a une production et non a un compteur.
    """
    valeurs = [
        _f(s.get("metrage_reel"))
        for s in saisies
        if _txt(s.get("operation_code")) == code_fin and _f(s.get("metrage_reel")) > 0
    ]
    if len(valeurs) >= 2:
        reel = max(valeurs) - min(valeurs)
        fiable = True
    elif len(valeurs) == 1:
        reel = valeurs[0] if valeurs[0] < SEUIL_COMPTEUR else 0.0
        fiable = valeurs[0] < SEUIL_COMPTEUR
    else:
        reel = 0.0
        fiable = False

    prevus = [_f(s.get("metrage_prevu")) for s in saisies if _f(s.get("metrage_prevu")) > 0]
    prevu = max(prevus) if prevus else None

    return {
        "reel": round(reel, 1),
        "prevu": round(prevu, 1) if prevu else None,
        "fiable": fiable,
        "ecart_pct": _ecart_pct(reel, prevu) if prevu else None,
        "releves": len(valeurs),
    }


# ─── Ce qui a ete ecrit ──────────────────────────────────────────────────────

# Reponses qui remplissent le champ sans rien apprendre. Comparees apres
# suppression des espaces, de la ponctuation et des accents : « R.A.S. »,
# « ras », « Néant » et « RAS. » sont la meme reponse.
MENTIONS_VIDES = frozenset({"RAS", "NEANT", "RIEN", "NA", "AUCUN", "AUCUNE", "OK", "-"})


def est_sans_contenu(texte: str) -> bool:
    """Vrai si l'info prod est une formule d'acquittement et non une information."""
    nu = unicodedata.normalize("NFKD", _txt(texte).upper())
    nu = "".join(c for c in nu if not unicodedata.combining(c))
    nu = re.sub(r"[^A-Z0-9]", "", nu)
    return nu in MENTIONS_VIDES or nu == ""


def info_prod(conn, no_dossier: str) -> Optional[Dict[str, Any]]:
    """L'info prod obligatoire a la cloture. « R.A.S. » compte comme une reponse."""
    if not _table_existe(conn, "dossier_info_prod"):
        return None
    row = conn.execute(
        """SELECT no_dossier, ref_produit_norm, texte, auteur,
                  created_at, updated_at, updated_par
             FROM dossier_info_prod
            WHERE TRIM(no_dossier) = TRIM(?)""",
        (no_dossier,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    texte = _txt(d.get("texte"))
    d["texte"] = texte
    # « R.A.S. » est une reponse valide, mais ce n'est pas une information :
    # l'ecran doit pouvoir distinguer les deux sans re-parser le texte.
    d["substantiel"] = not est_sans_contenu(texte)
    return d


def commentaires(conn, no_dossier: str, saisies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ce que les conducteurs ont ecrit sur ce dossier.

    Deux sources, dans cet ordre de confiance : les saisies vivantes de
    `production_data` (a jour), et a defaut le JSON fige dans
    `produit_series.commentaires` si le dossier a ete materialise et que ses
    saisies ont disparu. Les motifs d'annulation comptent : un dossier annule
    en calage porte une explication qui vaut d'etre lue.
    """
    out: List[Dict[str, Any]] = []
    vus: set = set()

    for s in saisies:
        texte = _txt(s.get("commentaire"))
        if texte:
            cle = (s.get("id"), "commentaire")
            if cle not in vus:
                vus.add(cle)
                out.append({
                    "saisie_id": s.get("id"),
                    "date": _txt(s.get("date_operation")),
                    "operateur": _txt(s.get("operateur")),
                    "operation": _txt(s.get("operation")),
                    "texte": texte,
                    "origine": "commentaire",
                })
        motif = _txt(s.get("annule_motif"))
        if motif:
            cle = (s.get("id"), "annulation")
            if cle not in vus:
                vus.add(cle)
                out.append({
                    "saisie_id": s.get("id"),
                    "date": _txt(s.get("annule_le")) or _txt(s.get("date_operation")),
                    "operateur": _txt(s.get("annule_par")) or _txt(s.get("operateur")),
                    "operation": _txt(s.get("operation")),
                    "texte": motif,
                    "origine": "annulation",
                })

    if not out and _table_existe(conn, "produit_series"):
        row = conn.execute(
            "SELECT commentaires FROM produit_series WHERE TRIM(no_dossier) = TRIM(?)",
            (no_dossier,),
        ).fetchone()
        if row and _txt(row["commentaires"]):
            try:
                for c in json.loads(row["commentaires"]) or []:
                    if _txt(c.get("texte")):
                        out.append({
                            "saisie_id": c.get("saisie_id"),
                            "date": _txt(c.get("date")),
                            "operateur": _txt(c.get("operateur")),
                            "operation": _txt(c.get("operation")),
                            "texte": _txt(c.get("texte")),
                            "origine": _txt(c.get("origine")) or "commentaire",
                        })
            except (ValueError, TypeError):
                pass

    out.sort(key=lambda c: c.get("date") or "")
    return out


def seuils_franchis(conn, no_dossier: str) -> List[Dict[str, Any]]:
    """Seuils d'arret franchis sur ce dossier, avec le mot du conducteur."""
    if not _table_existe(conn, "arret_seuils_franchis"):
        return []
    rows = conn.execute(
        """SELECT id, saisie_id, machine, operation_code, operation, operateur,
                  regle, compteur, duree_saisie_min, duree_cumul_min,
                  commentaire_present, explication_exigee, explication_texte,
                  explication_le, created_at
             FROM arret_seuils_franchis
            WHERE TRIM(COALESCE(no_dossier, '')) = TRIM(?)
            ORDER BY created_at, id""",
        (no_dossier,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["explication_texte"] = _txt(d.get("explication_texte"))
        d["sans_explication"] = bool(d.get("explication_exigee")) and not d["explication_texte"]
        d["duree_saisie_txt"] = _minutes_txt(d.get("duree_saisie_min"))
        d["duree_cumul_txt"] = _minutes_txt(d.get("duree_cumul_min"))
        out.append(d)
    return out


def non_conformites(conn, no_dossier: str) -> List[Dict[str, Any]]:
    cols = _colonnes(conn, "nc_dossiers")
    if "no_dossier" not in cols:
        return []
    champs = [c for c in ("id", "numero", "titre", "gravite", "statut", "date_nc",
                          "type_nc", "service_concerne") if c in cols]
    rows = conn.execute(
        f"""SELECT {', '.join(champs)} FROM nc_dossiers
             WHERE TRIM(COALESCE(no_dossier, '')) = TRIM(?)
             ORDER BY date_nc DESC, id DESC""",
        (no_dossier,),
    ).fetchall()
    return [dict(r) for r in rows]


# ─── Reperes de la reference ─────────────────────────────────────────────────

def _ref_produit(conn, no_dossier: str) -> Optional[str]:
    for table, champ in (("produit_series", "ref_produit_norm"),
                         ("dossier_info_prod", "ref_produit_norm")):
        if champ not in _colonnes(conn, table):
            continue
        row = conn.execute(
            f"SELECT {champ} FROM {table} WHERE TRIM(no_dossier) = TRIM(?)",
            (no_dossier,),
        ).fetchone()
        if row and _txt(row[champ]):
            return _txt(row[champ])
    return None


def reperes_reference(conn, ref_produit_norm: Optional[str],
                      no_dossier_exclu: str = "") -> Dict[str, Any]:
    """Ce que la meme reference a donne les fois precedentes.

    C'est le seul retour qui ait une valeur pour un conducteur : non pas
    « tu as fait 620 m/h », mais « cette reference tourne d'habitude a 700 ».
    La mediane plutot que la moyenne — une serie ratee ne doit pas deplacer
    le repere.

    ATTENTION A LA DEFINITION. `produit_series.vitesse_m_min` est calcule par
    `app/services/dossier_stats.py` comme metrage / (production + arret), et
    non metrage / production. Le repere renvoye ici porte donc la CADENCE,
    arrets inclus, et ne se compare qu'a une cadence calculee de la meme
    facon — jamais a une vitesse de production seule, qui serait toujours
    superieure et ferait passer chaque semaine pour un progres.

    UNITE : metres par MINUTE, sans conversion. C'est l'unite de la machine
    (le conducteur regle une vitesse en m/min), celle de `produit_series`, et
    celle qu'affiche tout le reste de MySifa. Convertir en m/h donnerait un
    nombre exact et illisible a l'atelier.
    """
    vide = {"ref_produit_norm": ref_produit_norm, "series": 0,
            "cadence_mediane_m_min": None, "calage_median_min": None,
            "arret_median_min": None}
    if not ref_produit_norm or not _table_existe(conn, "produit_series"):
        return vide
    cols = _colonnes(conn, "produit_series")
    rows = conn.execute(
        """SELECT no_dossier, vitesse_m_min, temps_calage_min, temps_arret_min,
                  temps_prod_min, metrage_m, date_fin
             FROM produit_series
            WHERE ref_produit_norm = ?
              AND TRIM(COALESCE(no_dossier, '')) <> TRIM(?)
            ORDER BY date_fin DESC""",
        (ref_produit_norm, no_dossier_exclu),
    ).fetchall() if {"vitesse_m_min", "temps_calage_min"} <= cols else []
    if not rows:
        return vide

    cadences = [_f(r["vitesse_m_min"]) for r in rows if _f(r["vitesse_m_min"]) > 0]
    calages = [_f(r["temps_calage_min"]) for r in rows if _f(r["temps_calage_min"]) > 0]
    arrets = [_f(r["temps_arret_min"]) for r in rows if _f(r["temps_arret_min"]) > 0]

    return {
        "ref_produit_norm": ref_produit_norm,
        "series": len(rows),
        "cadence_mediane_m_min": mediane(cadences),
        "calage_median_min": mediane(calages),
        "arret_median_min": mediane(arrets),
    }


# ─── Compte-rendu d'un dossier ───────────────────────────────────────────────

def compte_rendu(conn, no_dossier: str, code_fin: str = "89",
                 code_debut: str = "01") -> Dict[str, Any]:
    """Tout ce que la production de ce dossier a produit comme information.

    Les codes de debut et de fin arrivent en parametres — ils vivent dans
    `config.py`, pas ici.
    """
    no_dossier = _txt(no_dossier)
    saisies = _saisies(conn, no_dossier)
    if not saisies:
        return {"no_dossier": no_dossier, "existe": False}

    derniere = max(saisies, key=lambda s: _txt(s.get("date_operation")))
    premiere = min(saisies, key=lambda s: _txt(s.get("date_operation")))
    fins = [s for s in saisies if _txt(s.get("operation_code")) == code_fin]

    conducteurs = sorted({_txt(s.get("operateur")) for s in saisies if _txt(s.get("operateur"))})

    temps = temps_par_categorie(saisies)
    metrage = metrage_dossier(saisies, code_fin)
    minutes_prod = _minutes_de(temps, CAT_PRODUCTION)
    # m/min partout : unite de la machine et du reste de MySifa.
    vitesse = (metrage["reel"] / minutes_prod) if minutes_prod > 0 and metrage["reel"] > 0 else None
    # Cadence : meme denominateur que `produit_series.vitesse_m_min`
    # (production + arret), seule base comparable au repere historique.
    minutes_cadence = minutes_prod + _minutes_de(temps, CAT_ARRET)
    cadence = (metrage["reel"] / minutes_cadence) if minutes_cadence > 0 and metrage["reel"] > 0 else None

    ref = _ref_produit(conn, no_dossier)
    reperes = reperes_reference(conn, ref, no_dossier)

    info = info_prod(conn, no_dossier)
    coms = commentaires(conn, no_dossier, saisies)
    seuils = seuils_franchis(conn, no_dossier)
    ncs = non_conformites(conn, no_dossier)

    minutes_calage = _minutes_de(temps, CAT_CALAGE)
    minutes_arret = sum(_minutes_de(temps, c) for c in CATEGORIES_COUTEUSES)

    cr = {
        "no_dossier": no_dossier,
        "existe": True,
        "identite": {
            "client": _txt(derniere.get("client")) or _txt(premiere.get("client")),
            "designation": _txt(derniere.get("designation")) or _txt(premiere.get("designation")),
            "ref_produit_norm": ref,
            "machine": _txt(derniere.get("machine")),
            "conducteurs": conducteurs,
            "date_debut": _txt(premiere.get("date_operation")),
            "date_fin": _txt(derniere.get("date_operation")),
            "cloture": bool(fins),
            "nb_saisies": len(saisies),
        },
        "temps": temps,
        "metrage": metrage,
        "vitesse_m_min": round(vitesse, 1) if vitesse else None,
        "cadence_m_min": round(cadence, 1) if cadence else None,
        "reference": reperes,
        "ecarts": {
            "cadence_pct": _ecart_pct(cadence, reperes.get("cadence_mediane_m_min")),
            "calage_pct": _ecart_pct(minutes_calage or None, reperes.get("calage_median_min")),
        },
        "ecrits": {
            "info_prod": info,
            "commentaires": coms,
        },
        "seuils": seuils,
        "non_conformites": ncs,
    }
    cr["vigilance"] = _vigilance(cr, minutes_arret)
    return cr


def _vigilance(cr: Dict[str, Any], minutes_arret: float) -> List[Dict[str, str]]:
    """Les points a signaler — factuels, actionnables, jamais nominatifs.

    Une liste vide est un resultat : elle veut dire que le dossier est complet.
    """
    points: List[Dict[str, str]] = []
    ident = cr["identite"]

    if ident["cloture"] and not cr["ecrits"]["info_prod"]:
        points.append({
            "cle": "info_prod_absente",
            "texte": "Dossier cloture sans info prod — la note de cloture n'a pas ete enregistree.",
        })

    sans_expl = [s for s in cr["seuils"] if s.get("sans_explication")]
    if sans_expl:
        points.append({
            "cle": "seuils_sans_explication",
            "texte": (f"{len(sans_expl)} seuil d'arret franchi sans explication"
                      if len(sans_expl) == 1 else
                      f"{len(sans_expl)} seuils d'arret franchis sans explication"),
        })

    ouvertes = cr["temps"].get("saisies_ouvertes") or []
    if ouvertes:
        total = sum(o["minutes"] for o in ouvertes)
        points.append({
            "cle": "saisie_ouverte",
            "texte": (f"{len(ouvertes)} saisie restee ouverte d'un jour a l'autre "
                      f"({_minutes_txt(total)} comptes) — le temps affiche est a prendre avec reserve."
                      if len(ouvertes) == 1 else
                      f"{len(ouvertes)} saisies restees ouvertes d'un jour a l'autre "
                      f"({_minutes_txt(total)} comptes) — le temps affiche est a prendre avec reserve."),
        })

    if ident["cloture"] and not cr["metrage"]["fiable"]:
        points.append({
            "cle": "metrage_non_fiable",
            "texte": "Metrage non exploitable — un seul releve de compteur, pas d'ecart calculable.",
        })

    total_min = cr["temps"]["total_minutes"]
    if total_min > 0 and minutes_arret / total_min > 0.30:
        points.append({
            "cle": "arrets_eleves",
            "texte": (f"Arrets et attentes : {_minutes_txt(minutes_arret)} sur "
                      f"{_minutes_txt(total_min)}, soit plus de 30 % du temps passe."),
        })

    return points


# ─── Centralisation : les comptes-rendus d'une periode ───────────────────────

def dossiers_clotures(conn, debut: str, fin: str, machine: str = "",
                      code_fin: str = "89") -> List[str]:
    """Numeros des dossiers ayant au moins une saisie de fin dans la periode.

    `debut` et `fin` sont des chaines '%Y-%m-%dT%H:%M:%S' — meme format que
    `date_operation`, comparaison lexicographique.
    """
    cols = _colonnes(conn, "production_data")
    if not cols:
        return []
    filtre_annule = " AND COALESCE(est_annule, 0) = 0" if "est_annule" in cols else ""
    params: List[Any] = [code_fin, debut, fin]
    filtre_machine = ""
    if _txt(machine):
        filtre_machine = " AND TRIM(LOWER(COALESCE(machine,''))) = TRIM(LOWER(?))"
        params.append(_txt(machine))
    rows = conn.execute(
        f"""SELECT DISTINCT TRIM(no_dossier) AS no_dossier
              FROM production_data
             WHERE operation_code = ?
               AND date_operation >= ? AND date_operation <= ?
               AND TRIM(COALESCE(no_dossier, '')) <> ''{filtre_annule}{filtre_machine}
             ORDER BY no_dossier""",
        params,
    ).fetchall()
    return [r["no_dossier"] for r in rows]


def resume(cr: Dict[str, Any]) -> Dict[str, Any]:
    """Projection compacte d'un compte-rendu, pour une liste ou un tableau."""
    if not cr.get("existe"):
        return {"no_dossier": cr.get("no_dossier", ""), "existe": False}
    ident = cr["identite"]
    info = cr["ecrits"]["info_prod"]
    return {
        "no_dossier": cr["no_dossier"],
        "existe": True,
        "client": ident["client"],
        "designation": ident["designation"],
        "machine": ident["machine"],
        "ref_produit_norm": ident["ref_produit_norm"],
        "date_fin": ident["date_fin"],
        "cloture": ident["cloture"],
        "conducteurs": ident["conducteurs"],
        "metrage_reel": cr["metrage"]["reel"],
        "vitesse_m_min": cr["vitesse_m_min"],
        "cadence_m_min": cr["cadence_m_min"],
        "ecart_cadence_pct": cr["ecarts"]["cadence_pct"],
        "minutes_total": cr["temps"]["total_minutes"],
        "info_prod": bool(info),
        "info_prod_substantielle": bool(info and info.get("substantiel")),
        "nb_commentaires": len(cr["ecrits"]["commentaires"]),
        "nb_seuils": len(cr["seuils"]),
        "nb_seuils_sans_explication": sum(1 for s in cr["seuils"] if s.get("sans_explication")),
        "nb_nc": len(cr["non_conformites"]),
        "nb_vigilance": len(cr["vigilance"]),
    }


def comptes_rendus_periode(conn, debut: str, fin: str, machine: str = "",
                           code_fin: str = "89", limite: int = 200) -> List[Dict[str, Any]]:
    """Les comptes-rendus d'une periode, en projection compacte."""
    numeros = dossiers_clotures(conn, debut, fin, machine, code_fin)[:max(0, limite)]
    out = []
    for no_d in numeros:
        cr = compte_rendu(conn, no_d, code_fin=code_fin)
        if cr.get("existe"):
            out.append(resume(cr))
    out.sort(key=lambda r: r.get("date_fin") or "", reverse=True)
    return out


# ─── Retour a l'atelier ──────────────────────────────────────────────────────

def retour_atelier(conn, machine: str, debut: str, fin: str,
                   code_fin: str = "89") -> Dict[str, Any]:
    """Ce qu'on rend aux conducteurs d'une machine, pour une semaine.

    Trois regles de conception, qui expliquent ce qui n'y figure pas :

    1. Par machine, jamais par personne. La completude d'une saisie mesure
       l'ergonomie de l'outil et la charge de l'equipe autant que le conducteur.
       Un classement nominatif transformerait un probleme de moyens en
       palmares, et ce n'est pas ce qu'on cherche a obtenir.
    2. Le repere est la reference, pas la moyenne d'atelier. « Cette reference
       tourne d'habitude a 700 m/h » se discute a la machine ; « tu es en
       dessous de la moyenne » ne se discute pas.
    3. Ce que les conducteurs ont ecrit leur revient. C'est la contrepartie de
       l'info prod obligatoire a la cloture : si le texte ne redescend jamais,
       il devient une formalite et se remplit en « R.A.S. ».
    """
    numeros = dossiers_clotures(conn, debut, fin, machine, code_fin)
    crs = [compte_rendu(conn, n, code_fin=code_fin) for n in numeros]
    crs = [c for c in crs if c.get("existe")]

    minutes_prod = sum(_minutes_de(c["temps"], CAT_PRODUCTION) for c in crs)
    minutes_calage = sum(_minutes_de(c["temps"], CAT_CALAGE) for c in crs)
    minutes_arret = sum(sum(_minutes_de(c["temps"], k) for k in CATEGORIES_COUTEUSES) for c in crs)
    minutes_total = sum(c["temps"]["total_minutes"] for c in crs)
    metrage = sum(c["metrage"]["reel"] for c in crs)

    conducteurs = sorted({n for c in crs for n in c["identite"]["conducteurs"]})

    # References produites, avec l'ecart au repere historique.
    refs: List[Dict[str, Any]] = []
    for c in crs:
        if c["cadence_m_min"] is None:
            continue
        refs.append({
            "no_dossier": c["no_dossier"],
            "ref_produit_norm": c["identite"]["ref_produit_norm"],
            "designation": c["identite"]["designation"],
            "metrage": c["metrage"]["reel"],
            "vitesse_m_min": c["vitesse_m_min"],
            "cadence_m_min": c["cadence_m_min"],
            "cadence_reference_m_min": c["reference"].get("cadence_mediane_m_min"),
            "series_passees": c["reference"].get("series", 0),
            "ecart_pct": c["ecarts"]["cadence_pct"],
        })
    refs.sort(key=lambda r: -(r["metrage"] or 0))

    # Ce qui a coute du temps, par code, tous dossiers confondus.
    par_code: Dict[str, Dict[str, Any]] = {}
    for c in crs:
        for code in c["temps"]["par_code"]:
            if code["categorie"] not in CATEGORIES_COUTEUSES:
                continue
            agg = par_code.setdefault(code["code"], {
                "code": code["code"], "operation": code["operation"],
                "categorie": code["categorie"], "minutes": 0.0, "occurrences": 0,
                "dossiers": 0,
            })
            agg["minutes"] += code["minutes"]
            agg["occurrences"] += code["occurrences"]
            agg["dossiers"] += 1
    couteux = sorted(par_code.values(), key=lambda a: -a["minutes"])[:5]
    for a in couteux:
        a["minutes"] = round(a["minutes"], 1)
        a["minutes_txt"] = _minutes_txt(a["minutes"])

    # Ce que les conducteurs ont ecrit cette semaine.
    ecrits: List[Dict[str, Any]] = []
    for c in crs:
        info = c["ecrits"]["info_prod"]
        if info and info.get("substantiel"):
            ecrits.append({
                "no_dossier": c["no_dossier"], "origine": "info_prod",
                "texte": info["texte"], "auteur": _txt(info.get("auteur")),
                "date": _txt(info.get("created_at")),
            })
        for s in c["seuils"]:
            if s.get("explication_texte"):
                ecrits.append({
                    "no_dossier": c["no_dossier"], "origine": "arret",
                    "texte": s["explication_texte"],
                    "auteur": _txt(s.get("operateur")),
                    "date": _txt(s.get("created_at")),
                    "operation": _txt(s.get("operation")),
                })
        for cm in c["ecrits"]["commentaires"]:
            ecrits.append({
                "no_dossier": c["no_dossier"], "origine": cm["origine"],
                "texte": cm["texte"], "auteur": cm["operateur"], "date": cm["date"],
                "operation": cm.get("operation", ""),
            })
    ecrits.sort(key=lambda e: e.get("date") or "")

    # Vigilance agregee — les memes cles, comptees, jamais rattachees a un nom.
    compte_vigilance: Dict[str, int] = {}
    for c in crs:
        for v in c["vigilance"]:
            compte_vigilance[v["cle"]] = compte_vigilance.get(v["cle"], 0) + 1

    return {
        "machine": _txt(machine),
        "periode": {"debut": debut, "fin": fin},
        "dossiers": len(crs),
        "conducteurs": conducteurs,
        "production": {
            "minutes_production": round(minutes_prod, 1),
            "minutes_calage": round(minutes_calage, 1),
            "minutes_arret": round(minutes_arret, 1),
            "minutes_total": round(minutes_total, 1),
            "metrage": round(metrage, 1),
            "vitesse_m_min": round(metrage / minutes_prod, 1) if minutes_prod > 0 else None,
            "part_arret_pct": round(minutes_arret / minutes_total * 100.0, 1) if minutes_total > 0 else 0.0,
        },
        "references": refs,
        "arrets_couteux": couteux,
        "ecrits": ecrits,
        "vigilance": compte_vigilance,
        "nb_nc": sum(len(c["non_conformites"]) for c in crs),
    }


def machines_periode(conn, debut: str, fin: str, code_fin: str = "89") -> List[str]:
    """Machines ayant cloture au moins un dossier sur la periode."""
    cols = _colonnes(conn, "production_data")
    if not cols:
        return []
    filtre_annule = " AND COALESCE(est_annule, 0) = 0" if "est_annule" in cols else ""
    rows = conn.execute(
        f"""SELECT DISTINCT TRIM(machine) AS machine
              FROM production_data
             WHERE operation_code = ?
               AND date_operation >= ? AND date_operation <= ?
               AND TRIM(COALESCE(machine, '')) <> ''{filtre_annule}
             ORDER BY machine""",
        (code_fin, debut, fin),
    ).fetchall()
    return [r["machine"] for r in rows]


# ─── Recherche libre ─────────────────────────────────────────────────────────

def rechercher_dossiers(conn, terme: str, limite: int = 20,
                        code_fin: str = "89") -> List[Dict[str, Any]]:
    """Dossiers portant des saisies, cherches sur numero, client ou designation.

    La liste d'une periode ne montre que les dossiers CLOTURES pendant cette
    periode. Or un compte-rendu se consulte aussi sur un dossier encore en
    cours, ou clos il y a trois mois — c'est meme la le plus utile, quand on
    reprend une reference. Cette recherche ouvre donc `compte_rendu` sur
    n'importe quel dossier ayant au moins une saisie, sans condition de date
    ni de cloture.
    """
    terme = _txt(terme)
    if len(terme) < 2:
        return []
    cols = _colonnes(conn, "production_data")
    if not cols:
        return []
    filtre_annule = " AND COALESCE(est_annule, 0) = 0" if "est_annule" in cols else ""
    like = f"%{terme}%"
    prefixe = f"{terme}%"
    n = max(1, min(int(limite), 100))

    rows = conn.execute(
        f"""SELECT TRIM(no_dossier) AS no_dossier,
                   MAX(client)      AS client,
                   MAX(designation) AS designation,
                   MAX(machine)     AS machine,
                   MAX(date_operation) AS derniere_saisie,
                   MIN(date_operation) AS premiere_saisie,
                   COUNT(*)         AS nb_saisies,
                   MAX(CASE WHEN operation_code = ? THEN 1 ELSE 0 END) AS cloture
              FROM production_data
             WHERE TRIM(COALESCE(no_dossier, '')) <> ''{filtre_annule}
               AND (LOWER(COALESCE(no_dossier, ''))  LIKE LOWER(?)
                 OR LOWER(COALESCE(client, ''))      LIKE LOWER(?)
                 OR LOWER(COALESCE(designation, '')) LIKE LOWER(?))
             GROUP BY TRIM(no_dossier)
             ORDER BY CASE WHEN LOWER(TRIM(no_dossier)) LIKE LOWER(?) THEN 0 ELSE 1 END,
                      derniere_saisie DESC
             LIMIT ?""",
        (code_fin, like, like, like, prefixe, n),
    ).fetchall()

    return [{
        "no_dossier": r["no_dossier"],
        "client": _txt(r["client"]),
        "designation": _txt(r["designation"]),
        "machine": _txt(r["machine"]),
        "derniere_saisie": _txt(r["derniere_saisie"]),
        "premiere_saisie": _txt(r["premiere_saisie"]),
        "nb_saisies": int(r["nb_saisies"] or 0),
        "cloture": bool(r["cloture"]),
    } for r in rows]
