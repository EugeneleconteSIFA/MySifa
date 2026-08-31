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
   - metrage du dossier = somme des ecarts de compteur (fin - debut) par
     cycle, exactement comme `dossier_stats._enrich_metrage` qui alimente
     `produit_series.metrage_m` et la liste des saisies de MyProd.

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
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Au-dela de cet ecart entre deux saisies d'un meme operateur, on ne regarde
# plus un arret machine mais une fin de journee. Meme valeur que
# `app/services/arret_seuils.py`.
ECART_MAX_MIN = 480.0


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
        "metrage_total_debut", "metrage_total_fin",
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


def intervalles(saisies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chaque saisie et le temps qui la separe de la suivante DU MEME OPERATEUR.

    C'est la brique commune au calcul des temps et au trace de la frise : la
    repartition par categorie n'est qu'une somme de ces intervalles, et la
    frise n'est que leur mise en place sur un axe. Les calculer deux fois,
    c'est se donner deux chronologies pour un meme dossier.
    """
    out: List[Dict[str, Any]] = []
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
            out.append({
                "saisie_id": ligne.get("id"),
                "operateur": _txt(ligne.get("operateur")),
                "machine": _txt(ligne.get("machine")),
                "no_dossier": _txt(ligne.get("no_dossier")),
                "client": _txt(ligne.get("client")),
                "designation": _txt(ligne.get("designation")),
                "debut": debut, "fin": fin, "minutes": minutes,
                "categorie": _txt(ligne.get("operation_category")).lower() or "autre",
                "code": _txt(ligne.get("operation_code")),
                "operation": _txt(ligne.get("operation")),
                "douteuse": minutes > ECART_MAX_MIN,
            })
    out.sort(key=lambda i: (i["debut"], i["saisie_id"] or 0))
    return out


def temps_par_categorie(saisies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Repartition du temps du dossier, par categorie d'operation.

    `minutes` ne plafonne rien, pour rester aligne sur le calcul historique ;
    `minutes_douteuses` isole les ecarts qui depassent ECART_MAX_MIN,
    c'est-a-dire les saisies restees ouvertes d'un jour a l'autre.
    """
    par_cat: Dict[str, Dict[str, float]] = {}
    par_code: Dict[str, Dict[str, Any]] = {}
    ouvertes: List[Dict[str, Any]] = []

    for iv in intervalles(saisies):
        bloc = par_cat.setdefault(iv["categorie"], {"minutes": 0.0, "minutes_douteuses": 0.0,
                                                    "occurrences": 0.0})
        bloc["minutes"] += iv["minutes"]
        bloc["occurrences"] += 1
        if iv["douteuse"]:
            bloc["minutes_douteuses"] += iv["minutes"]

        detail = par_code.setdefault(iv["code"], {
            "code": iv["code"], "operation": iv["operation"],
            "categorie": iv["categorie"], "minutes": 0.0, "occurrences": 0,
        })
        detail["minutes"] += iv["minutes"]
        detail["occurrences"] += 1

        if iv["douteuse"]:
            ouvertes.append({
                "saisie_id": iv["saisie_id"], "operateur": iv["operateur"],
                "date_operation": iv["debut"].strftime("%Y-%m-%dT%H:%M:%S"),
                "operation": iv["operation"], "code": iv["code"],
                "minutes": iv["minutes"],
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

def _compteur(saisie: Dict[str, Any], *champs: str) -> Optional[float]:
    """Premier compteur machine renseigne parmi `champs`, sinon None.

    L'ordre porte l'histoire du schema : les compteurs vivent dans
    `metrage_total_debut` / `metrage_total_fin` depuis leur introduction,
    `metrage_prevu` / `metrage_reel` restent le repli des lignes anterieures.
    """
    for champ in champs:
        v = saisie.get(champ)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def metrage_dossier(saisies: List[Dict[str, Any]], code_fin: str = "89",
                    code_debut: str = "01", code_annul: str = "90") -> Dict[str, Any]:
    """Metrage produit = somme des ecarts de compteur (fin - debut) par cycle.

    Regle reprise TELLE QUELLE de `app/services/dossier_stats.py::_enrich_metrage`,
    qui alimente `produit_series.metrage_m` et la liste des saisies de MyProd.
    La reproduire a l'identique n'est pas du zele : c'est la seule facon que ce
    dossier n'affiche pas ici un metrage different de celui qu'un operateur
    relit ailleurs.

    1. Les compteurs sont dans `metrage_total_debut` / `metrage_total_fin` ;
       `metrage_prevu` / `metrage_reel` ne sont que le repli des lignes
       anterieures. Ne lire que l'ancien couple rend muette toute saisie qui ne
       le remplit plus — metrage a 0 sur un dossier pourtant produit.
    2. Le compteur de debut appartient au DOSSIER, pas a l'operateur : quand
       une equipe prend la suite d'une autre, celle qui cloture n'a pas pose le
       code de debut.
    3. Sans compteur de debut connu, il n'y a pas de metrage — on ne prend pas
       0 pour origine, sinon c'est le compteur machine entier qui sort.
    4. Le code d'annulation borne un cycle comme le code de fin : le temps et
       la matiere ont ete consommes, seule la livraison n'a pas eu lieu. La
       ligne d'annulation porte elle-meme son compteur de debut.
    """
    ordonnees = sorted(saisies, key=lambda r: (_txt(r.get("date_operation")), r.get("id") or 0))
    debuts: List[Tuple[str, float]] = []
    total = 0.0
    cycles = 0
    fins_sans_debut = 0

    for r in ordonnees:
        code = _txt(r.get("operation_code"))
        quand = _txt(r.get("date_operation"))

        if code == code_debut:
            ctr = _compteur(r, "metrage_total_debut", "metrage_prevu")
            if ctr is not None:
                debuts.append((quand, ctr))
            continue

        if code not in (code_fin, code_annul):
            continue

        fin_ctr = _compteur(r, "metrage_total_fin", "metrage_reel")
        if fin_ctr is None:
            continue

        debut_ctr = (_compteur(r, "metrage_total_debut", "metrage_prevu")
                     if code == code_annul else None)
        if debut_ctr is None:
            avant = [c for q, c in debuts if q <= quand]
            debut_ctr = avant[-1] if avant else None
        if debut_ctr is None:
            fins_sans_debut += 1
            continue

        total += max(0.0, fin_ctr - debut_ctr)
        cycles += 1

    return {
        "reel": round(total, 1),
        "fiable": cycles > 0,
        "cycles": cycles,
        # Une cloture dont le compteur de debut manque : le metrage est
        # incomplet, et l'ecran doit pouvoir le dire.
        "fins_sans_debut": fins_sans_debut,
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
                 code_debut: str = "01", code_annul: str = "90") -> Dict[str, Any]:
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
    metrage = metrage_dossier(saisies, code_fin, code_debut, code_annul)
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
    notes = notes_dossier(conn, no_dossier)

    # Etat de suivi : chaque remontee porte sa cle, son etat de validation et
    # de quoi savoir si son texte se corrige depuis l'ecran.
    etats = _etats_ecrits(conn, no_dossier)

    def _suivi(objet: Dict[str, Any], origine: str, reference: Any,
               modifiable: bool) -> Dict[str, Any]:
        cle = cle_ecrit(origine, reference)
        etat = etats.get(cle, {})
        objet["cle"] = cle
        objet["origine"] = origine
        objet["reference"] = reference
        objet["modifiable"] = modifiable
        objet["valide"] = bool(etat.get("valide"))
        objet["valide_par"] = etat.get("valide_par", "")
        objet["valide_le"] = etat.get("valide_le", "")
        objet["masque"] = bool(etat.get("masque"))
        objet["masque_par"] = etat.get("masque_par", "")
        return objet

    if info:
        _suivi(info, "info_prod", no_dossier, True)
    for c in coms:
        # Un motif d'annulation est la trace d'un geste, pas une remontee que
        # l'on complete apres coup : il se valide, il ne se corrige pas.
        _suivi(c, c.get("origine") or "commentaire", c.get("saisie_id"),
               (c.get("origine") or "commentaire") == "commentaire")
    for sx in seuils:
        _suivi(sx, "arret", sx.get("saisie_id"), True)
        # Meme forme que les autres remontees : l'ecran n'a pas a savoir que
        # celle-ci range son texte sous un autre nom.
        sx["texte"] = sx.get("explication_texte") or ""
    for n in notes:
        _suivi(n, "note", n.get("id"), True)

    # Une reponse n'est pas une remontee de plus : elle appartient a celle
    # qu'elle commente. Ajoutee a la file, elle la noyait ; rangee dessous, elle
    # se lit comme une conversation.
    par_parent: Dict[str, List[Dict[str, Any]]] = {}
    libres: List[Dict[str, Any]] = []
    for n in notes:
        parent = _txt(n.get("cle_ecrit"))
        (par_parent.setdefault(parent, []) if parent else libres).append(n)
    for porteur in ([info] if info else []) + coms + seuils + notes:
        porteur["reponses"] = par_parent.get(porteur.get("cle", ""), [])
    notes = libres

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
            "notes": notes,
        },
        "seuils": seuils,
        "non_conformites": ncs,
    }
    cr["frise"] = frise_dossier(conn, no_dossier)
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
            "texte": ("Metrage non calculable — aucun compteur de debut releve "
                      "(code de debut sans metrage, ou dossier repris sans reprise du compteur)."),
        })
    elif cr["metrage"].get("fins_sans_debut"):
        points.append({
            "cle": "metrage_incomplet",
            "texte": (f"{cr['metrage']['fins_sans_debut']} cloture sans compteur de debut : "
                      "le metrage affiche est incomplet."),
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
        "nb_commentaires": len(cr["ecrits"]["commentaires"]) + len(cr["ecrits"]["notes"]),
        "nb_a_traiter": sum(
            1 for e in ([cr["ecrits"]["info_prod"]] if cr["ecrits"]["info_prod"] else [])
            + cr["ecrits"]["commentaires"] + cr["ecrits"]["notes"] + cr["seuils"]
            if not e.get("valide")),
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
            "client": c["identite"]["client"],
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

    def _porter(source: Dict[str, Any], no_d: str, texte: str, auteur: str,
                date: str, operation: str = "") -> None:
        ecrits.append({
            "no_dossier": no_d, "texte": texte, "auteur": auteur, "date": date,
            "operation": operation,
            "origine": source.get("origine", ""), "cle": source.get("cle", ""),
            "reference": source.get("reference"),
            "modifiable": bool(source.get("modifiable")),
            "valide": bool(source.get("valide")),
            "valide_par": source.get("valide_par", ""),
            "valide_le": source.get("valide_le", ""),
            "masque": bool(source.get("masque")),
            "masque_par": source.get("masque_par", ""),
            "reponses": source.get("reponses") or [],
        })

    for c in crs:
        no_d = c["no_dossier"]
        info = c["ecrits"]["info_prod"]
        if info and info.get("substantiel"):
            _porter(info, no_d, info["texte"], _txt(info.get("auteur")),
                    _txt(info.get("updated_at") or info.get("created_at")))
        for sx in c["seuils"]:
            if sx.get("explication_texte"):
                _porter(sx, no_d, sx["explication_texte"], _txt(sx.get("operateur")),
                        _txt(sx.get("created_at")), _txt(sx.get("operation")))
        for cm in c["ecrits"]["commentaires"]:
            _porter(cm, no_d, cm["texte"], cm["operateur"], cm["date"],
                    cm.get("operation", ""))
        for n in c["ecrits"]["notes"]:
            _porter(n, no_d, n["texte"], _txt(n.get("auteur")),
                    _txt(n.get("updated_at") or n.get("created_at")))
    ecrits.sort(key=lambda e: e.get("date") or "")
    # Les remontees hors sujet quittent la liste principale sans disparaitre.
    ecrits_masques = [e for e in ecrits if e.get("masque")]
    ecrits = [e for e in ecrits if not e.get("masque")]

    # Vigilance agregee — les memes cles, comptees, jamais rattachees a un nom.
    compte_vigilance: Dict[str, int] = {}
    for c in crs:
        for v in c["vigilance"]:
            compte_vigilance[v["cle"]] = compte_vigilance.get(v["cle"], 0) + 1

    return {
        "machine": _txt(machine),
        "toutes_machines": not _txt(machine),
        "machines_couvertes": sorted({c["identite"]["machine"] for c in crs
                                      if c["identite"].get("machine")}),
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
        "ecrits_masques": ecrits_masques,
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


# ─── Suivi des remontees : validation, notes ─────────────────────────────────
#
# Une remontee vient de trois tables differentes (commentaire de saisie, info
# prod, explication d'arret) plus les notes ajoutees ici. Une CLE stable les
# reconcilie, pour qu'un seul mecanisme de suivi les couvre toutes.
# Voir app/core/migrations/2026_08_28_retour_prod_suivi.py.

def cle_ecrit(origine: str, reference: Any) -> str:
    prefixe = {
        "commentaire": "saisie", "annulation": "saisie",
        "info_prod": "infoprod", "arret": "seuil", "note": "note",
    }.get(_txt(origine), _txt(origine) or "ecrit")
    return f"{prefixe}:{_txt(reference)}"


def _etats_ecrits(conn, no_dossier: str) -> Dict[str, Dict[str, Any]]:
    cols = _colonnes(conn, "retour_prod_ecrits")
    if not cols:
        return {}
    masque = "masque" in cols
    champs = "cle, valide, valide_par, valide_le" + (", masque, masque_par" if masque else "")
    rows = conn.execute(
        f"""SELECT {champs} FROM retour_prod_ecrits
             WHERE TRIM(COALESCE(no_dossier,'')) = TRIM(?)""",
        (no_dossier,),
    ).fetchall()
    return {r["cle"]: {
        "valide": bool(r["valide"]), "valide_par": _txt(r["valide_par"]),
        "valide_le": _txt(r["valide_le"]),
        "masque": bool(r["masque"]) if masque else False,
        "masque_par": _txt(r["masque_par"]) if masque else "",
    } for r in rows}


def masquer_ecrit(conn, cle: str, no_dossier: str, masque: bool, par: str) -> Dict[str, Any]:
    """Sort une remontee de la liste principale, sans rien effacer.

    Masquer n'est pas valider : une remontee masquee n'a pas ete traitee, elle
    n'avait rien a traiter. Confondre les deux ferait passer « 10h » pour un
    probleme resolu.
    """
    cols = _colonnes(conn, "retour_prod_ecrits")
    if "masque" not in cols:
        return {}
    maintenant = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO retour_prod_ecrits (cle, no_dossier, masque, masque_par, masque_le)
           VALUES (?,?,?,?,?)
           ON CONFLICT(cle) DO UPDATE SET
             no_dossier=excluded.no_dossier, masque=excluded.masque,
             masque_par=excluded.masque_par, masque_le=excluded.masque_le""",
        (_txt(cle), _txt(no_dossier), 1 if masque else 0,
         _txt(par) if masque else "", maintenant if masque else ""),
    )
    conn.commit()
    return {"cle": _txt(cle), "masque": bool(masque),
            "masque_par": _txt(par) if masque else ""}


def valider_ecrit(conn, cle: str, no_dossier: str, valide: bool, par: str) -> Dict[str, Any]:
    """Marque une remontee comme traitee, ou revient dessus.

    Une remontee validee reste affichee : la valider ne l'efface pas, elle dit
    seulement que quelqu'un l'a prise. Ce qui disparait de l'ecran n'est jamais
    relu, et une remontee non traitee doit rester sous les yeux.
    """
    if not _table_existe(conn, "retour_prod_ecrits"):
        return {}
    maintenant = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO retour_prod_ecrits (cle, no_dossier, valide, valide_par, valide_le)
           VALUES (?,?,?,?,?)
           ON CONFLICT(cle) DO UPDATE SET
             no_dossier=excluded.no_dossier, valide=excluded.valide,
             valide_par=excluded.valide_par, valide_le=excluded.valide_le""",
        (_txt(cle), _txt(no_dossier), 1 if valide else 0,
         _txt(par) if valide else "", maintenant if valide else ""),
    )
    conn.commit()
    return {"cle": _txt(cle), "valide": bool(valide),
            "valide_par": _txt(par) if valide else "",
            "valide_le": maintenant if valide else ""}


def notes_dossier(conn, no_dossier: str) -> List[Dict[str, Any]]:
    if not _table_existe(conn, "retour_prod_notes"):
        return []
    rows = conn.execute(
        """SELECT id, no_dossier, cle_ecrit, texte, auteur, created_at, updated_at, updated_par
             FROM retour_prod_notes
            WHERE TRIM(no_dossier) = TRIM(?)
            ORDER BY created_at, id""",
        (no_dossier,),
    ).fetchall()
    return [dict(r) for r in rows]


def ajouter_note(conn, no_dossier: str, texte: str, auteur: str,
                 cle_reponse: str = "") -> Optional[Dict[str, Any]]:
    """Note ajoutee depuis la feuille. `cle_reponse` la rattache a une remontee."""
    texte = _txt(texte)
    if not texte or not _table_existe(conn, "retour_prod_notes"):
        return None
    cur = conn.execute(
        """INSERT INTO retour_prod_notes (no_dossier, cle_ecrit, texte, auteur, created_at)
           VALUES (?,?,?,?,?)""",
        (_txt(no_dossier), _txt(cle_reponse) or None, texte, _txt(auteur),
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM retour_prod_notes WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row) if row else None


def modifier_note(conn, note_id: int, texte: str, auteur: str) -> Optional[Dict[str, Any]]:
    """Corrige une note. Un texte vide la supprime — une note vide n'est pas une note."""
    if not _table_existe(conn, "retour_prod_notes"):
        return None
    texte = _txt(texte)
    if not texte:
        conn.execute("DELETE FROM retour_prod_notes WHERE id=?", (int(note_id),))
        conn.commit()
        return None
    conn.execute(
        """UPDATE retour_prod_notes SET texte=?, updated_at=?, updated_par=? WHERE id=?""",
        (texte, datetime.now().isoformat(timespec="seconds"), _txt(auteur), int(note_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM retour_prod_notes WHERE id=?", (int(note_id),)).fetchone()
    return dict(row) if row else None


def modifier_commentaire_saisie(conn, saisie_id: int, texte: str) -> bool:
    """Corrige le commentaire porte par une saisie de production.

    On ne touche pas au motif d'annulation : c'est la trace d'un geste, pas une
    remontee que l'on complete apres coup.
    """
    if "commentaire" not in _colonnes(conn, "production_data"):
        return False
    cur = conn.execute(
        "UPDATE production_data SET commentaire=? WHERE id=?",
        (_txt(texte) or None, int(saisie_id)),
    )
    conn.commit()
    return bool(cur.rowcount)


# ─── Dernier jour travaille ──────────────────────────────────────────────────

def dernier_jour_saisi(conn, avant: str = "") -> Optional[str]:
    """Dernier jour (AAAA-MM-JJ) portant au moins une saisie, jusqu'a `avant` inclus.

    « Hier » est un mauvais repere dans un atelier qui ne tourne pas sept jours
    sur sept : un lundi matin, il designe un dimanche vide. Ce qu'on veut voir
    en ouvrant l'ecran, c'est la derniere journee REELLEMENT travaillee —
    vendredi, ou samedi si l'equipe est venue.

    Le calcul ne peut pas se faire dans le navigateur : lui seul sait quel jour
    on est, mais pas ou se trouve la derniere saisie.

    `avant` vide vaut la veille : on ne remonte jamais la journee en cours, meme
    si quelqu'un a deja pointe ce matin.
    """
    cols = _colonnes(conn, "production_data")
    if not cols:
        return None
    if not _txt(avant):
        avant = (date.today() - timedelta(days=1)).isoformat()
    borne = _txt(avant)[:10] + "T23:59:59"
    filtre_annule = " AND COALESCE(est_annule, 0) = 0" if "est_annule" in cols else ""
    row = conn.execute(
        f"""SELECT SUBSTR(date_operation, 1, 10) AS jour
              FROM production_data
             WHERE date_operation <= ?
               AND TRIM(COALESCE(date_operation, '')) <> ''{filtre_annule}
             ORDER BY date_operation DESC
             LIMIT 1""",
        (borne,),
    ).fetchone()
    return _txt(row["jour"]) if row and _txt(row["jour"]) else None


# ─── Frise de production ─────────────────────────────────────────────────────
#
# Meme allure que le planning, mais posee sur de VRAIES dates : le planning
# range des creneaux par sequence dans la semaine avec une largeur tiree du
# prevu (`planning_entries.duree_heures`), la frise pose ce qui s'est reellement
# passe, d'apres les saisies.
#
# L'axe ne montre que les plages travaillees : une journee d'atelier tient dans
# huit heures, et un axe minuit-minuit noierait les slots sous deux tiers de
# vide. Les nuits et les jours chomes sont replies en un trait.
#
# Les positions sont calculees ici, en pourcentage : l'ecran n'a qu'a poser des
# rectangles. Une geometrie calculee dans le navigateur serait invisible aux
# tests, et c'est precisement le genre de calcul qui derape en silence.

_JOURS_COURTS = ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim")


def _bornes_jour(quand: datetime) -> Tuple[datetime, datetime]:
    debut = quand.replace(hour=0, minute=0, second=0, microsecond=0)
    return debut, debut + timedelta(days=1)


def _axe_ouvre(intervalles_periode: List[Dict[str, Any]],
               debut: datetime, fin: datetime) -> List[Dict[str, Any]]:
    """Une plage par journee travaillee, large a proportion de sa duree reelle.

    Une journee sans aucune saisie n'a pas de plage : elle se replie. Deux
    journees de longueurs differentes gardent des largeurs differentes — sans
    quoi une demi-journee et une journee de douze heures se ressembleraient.

    Les saisies restees ouvertes d'un jour a l'autre ne definissent PAS l'axe :
    une ligne oubliee un soir couvrirait la nuit entiere et deplierait ce qu'on
    cherche justement a replier. Elles restent dessinees dans leur slot — c'est
    l'axe qu'elles ne commandent pas. Faute de mieux, on retombe dessus.
    """
    fiables = [iv for iv in intervalles_periode if not iv.get("douteuse")]
    retenus = fiables or intervalles_periode
    par_jour: Dict[str, Dict[str, datetime]] = {}
    for iv in retenus:
        d = max(iv["debut"], debut)
        f = min(iv["fin"], fin)
        if f <= d:
            continue
        curseur = d
        while curseur < f:
            jour_debut, jour_fin = _bornes_jour(curseur)
            tranche_fin = min(f, jour_fin)
            cle = jour_debut.strftime("%Y-%m-%d")
            plage = par_jour.get(cle)
            if plage is None:
                par_jour[cle] = {"debut": curseur, "fin": tranche_fin}
            else:
                plage["debut"] = min(plage["debut"], curseur)
                plage["fin"] = max(plage["fin"], tranche_fin)
            curseur = jour_fin

    plages = [{"jour": cle, **v} for cle, v in sorted(par_jour.items())]
    total = sum((p["fin"] - p["debut"]).total_seconds() for p in plages)
    if total <= 0:
        return []

    axe: List[Dict[str, Any]] = []
    curseur_x = 0.0
    for i, p in enumerate(plages):
        secondes = (p["fin"] - p["debut"]).total_seconds()
        largeur = secondes / total * 100.0
        precedent = plages[i - 1]["jour"] if i else None
        replie = False
        if precedent:
            veille = datetime.strptime(p["jour"], "%Y-%m-%d") - timedelta(days=1)
            replie = veille.strftime("%Y-%m-%d") != precedent
        axe.append({
            "jour": p["jour"],
            "label": (_JOURS_COURTS[datetime.strptime(p["jour"], "%Y-%m-%d").weekday()]
                      + " " + datetime.strptime(p["jour"], "%Y-%m-%d").strftime("%d/%m")),
            "debut": p["debut"].strftime("%Y-%m-%dT%H:%M:%S"),
            "fin": p["fin"].strftime("%Y-%m-%dT%H:%M:%S"),
            "heures": round(secondes / 3600.0, 1),
            "x": round(curseur_x, 4),
            "largeur": round(largeur, 4),
            # Vrai quand des journees entieres sans saisie separent celle-ci de
            # la precedente : l'ecran y pose un trait, pas du vide.
            "coupure_avant": replie,
            "_d": p["debut"], "_f": p["fin"],
        })
        curseur_x += largeur
    return axe


def _position(axe: List[Dict[str, Any]], quand: datetime) -> float:
    """Position en % d'un instant sur l'axe replie. Sature aux bornes."""
    if not axe:
        return 0.0
    if quand <= axe[0]["_d"]:
        return 0.0
    for plage in axe:
        if quand <= plage["_f"]:
            if quand < plage["_d"]:
                return plage["x"]          # tombe dans un repli : debut de plage
            duree = (plage["_f"] - plage["_d"]).total_seconds()
            if duree <= 0:
                return plage["x"]
            avance = (quand - plage["_d"]).total_seconds() / duree
            return plage["x"] + avance * plage["largeur"]
    return 100.0


def frise(conn, debut: str, fin: str, machine: str = "", code_fin: str = "89",
          code_debut: str = "01", code_annul: str = "90") -> Dict[str, Any]:
    """Ce qui est passe sur les machines pendant la periode, pose sur un axe.

    Un dossier commence souvent avant la periode et finit apres : son slot est
    alors coupe, et porte un marqueur de debordement de chaque cote. Le tronquer
    sans le dire ferait croire a une production plus courte qu'elle ne fut.
    """
    d_deb, d_fin = _dt(debut), _dt(fin)
    if d_deb is None or d_fin is None or d_fin <= d_deb:
        return {"vide": True, "axe": [], "lignes": []}

    cols = _colonnes(conn, "production_data")
    if not cols:
        return {"vide": True, "axe": [], "lignes": []}
    filtre_annule = " AND COALESCE(est_annule, 0) = 0" if "est_annule" in cols else ""
    params: List[Any] = [debut, fin]
    filtre_machine = ""
    if _txt(machine):
        filtre_machine = " AND TRIM(LOWER(COALESCE(machine,''))) = TRIM(LOWER(?))"
        params.append(_txt(machine))

    couples = conn.execute(
        f"""SELECT DISTINCT TRIM(no_dossier) AS no_dossier, TRIM(machine) AS machine
              FROM production_data
             WHERE date_operation >= ? AND date_operation <= ?
               AND TRIM(COALESCE(no_dossier, '')) <> ''{filtre_annule}{filtre_machine}""",
        params,
    ).fetchall()
    if not couples:
        return {"vide": True, "axe": [], "lignes": []}

    # Toutes les saisies du dossier, pas seulement celles de la periode : sinon
    # un dossier commence la veille perdrait son debut et sa premiere phase.
    brut: Dict[str, List[Dict[str, Any]]] = {}
    for c in couples:
        no_d = c["no_dossier"]
        if no_d not in brut:
            brut[no_d] = intervalles(_saisies(conn, no_d))

    dans_periode: List[Dict[str, Any]] = []
    for ivs in brut.values():
        for iv in ivs:
            if iv["fin"] > d_deb and iv["debut"] < d_fin:
                if not _txt(machine) or iv["machine"].strip().lower() == _txt(machine).lower():
                    dans_periode.append(iv)
    axe = _axe_ouvre(dans_periode, d_deb, d_fin)
    if not axe:
        return {"vide": True, "axe": [], "lignes": []}

    par_machine: Dict[str, List[Dict[str, Any]]] = {}
    for no_d, ivs in brut.items():
        machines = {iv["machine"] for iv in ivs if iv["machine"]}
        for m in sorted(machines):
            if _txt(machine) and m.strip().lower() != _txt(machine).lower():
                continue
            propres = [iv for iv in ivs if iv["machine"] == m]
            visibles = [iv for iv in propres if iv["fin"] > d_deb and iv["debut"] < d_fin]
            if not visibles:
                continue
            slot = _slot(propres, visibles, axe, d_deb, d_fin, no_d)
            if slot:
                par_machine.setdefault(m, []).append(slot)

    lignes = []
    for m in sorted(par_machine):
        slots = sorted(par_machine[m], key=lambda s: s["x"])
        lignes.append({"machine": m, "slots": slots})

    for plage in axe:
        plage.pop("_d", None)
        plage.pop("_f", None)

    return {"vide": not lignes, "axe": axe, "lignes": lignes,
            "periode": {"debut": debut, "fin": fin}}


def _slot(tous: List[Dict[str, Any]], visibles: List[Dict[str, Any]],
          axe: List[Dict[str, Any]], d_deb: datetime, d_fin: datetime,
          no_dossier: str) -> Optional[Dict[str, Any]]:
    """Un dossier sur une machine : sa barre, ses phases, ses debordements."""
    debut_reel = min(iv["debut"] for iv in tous)
    fin_reelle = max(iv["fin"] for iv in tous)
    d0 = max(debut_reel, d_deb)
    f0 = min(fin_reelle, d_fin)
    x = _position(axe, d0)
    fin_x = _position(axe, f0)
    largeur = max(fin_x - x, 0.35)          # un slot tres court reste cliquable

    # Les phases, dans l'ordre, sans chevauchement : deux conducteurs sur le
    # meme dossier se relaient, mais leurs saisies peuvent se croiser d'une
    # minute. On rabote plutot que de superposer deux rectangles.
    segments: List[Dict[str, Any]] = []
    borne = None
    for iv in sorted(visibles, key=lambda i: i["debut"]):
        s_deb = max(iv["debut"], d0)
        s_fin = min(iv["fin"], f0)
        if borne is not None and s_deb < borne:
            s_deb = borne
        if s_fin <= s_deb:
            continue
        borne = s_fin
        sx = _position(axe, s_deb)
        sf = _position(axe, s_fin)
        if largeur <= 0:
            continue
        segments.append({
            "categorie": iv["categorie"],
            "label": LIBELLES_CATEGORIES.get(iv["categorie"],
                                             iv["categorie"].capitalize() or "Autre"),
            "operation": iv["operation"],
            "code": iv["code"],
            "minutes": round(iv["minutes"], 1),
            "x": round(max(0.0, (sx - x) / largeur * 100.0), 3),
            "largeur": round(max(0.0, (sf - sx) / largeur * 100.0), 3),
        })

    derniere = max(tous, key=lambda i: i["debut"])
    return {
        "no_dossier": no_dossier,
        "client": _txt(derniere.get("client")),
        "designation": _txt(derniere.get("designation")),
        "operateurs": sorted({iv["operateur"] for iv in tous if iv["operateur"]}),
        "debut": debut_reel.strftime("%Y-%m-%dT%H:%M:%S"),
        "fin": fin_reelle.strftime("%Y-%m-%dT%H:%M:%S"),
        "minutes": round(sum(iv["minutes"] for iv in tous), 1),
        "x": round(x, 3),
        "largeur": round(largeur, 3),
        "deborde_avant": debut_reel < d_deb,
        "deborde_apres": fin_reelle > d_fin,
        "segments": segments,
    }


def frise_dossier(conn, no_dossier: str) -> Dict[str, Any]:
    """La frise d'un seul dossier, sur sa propre etendue.

    Meme composant que la frise machine, borne au dossier : dans son
    compte-rendu, ce qui interesse n'est pas ce que la machine a fait autour,
    c'est l'enchainement de ses propres phases.
    """
    ivs = intervalles(_saisies(conn, no_dossier))
    if not ivs:
        return {"vide": True, "axe": [], "lignes": []}
    d_deb = min(iv["debut"] for iv in ivs)
    d_fin = max(iv["fin"] for iv in ivs)
    axe = _axe_ouvre(ivs, d_deb, d_fin)
    if not axe:
        return {"vide": True, "axe": [], "lignes": []}
    par_machine: Dict[str, List[Dict[str, Any]]] = {}
    for m in sorted({iv["machine"] for iv in ivs if iv["machine"]} or {""}):
        propres = [iv for iv in ivs if iv["machine"] == m] or ivs
        slot = _slot(propres, propres, axe, d_deb, d_fin, _txt(no_dossier))
        if slot:
            par_machine.setdefault(m or "—", []).append(slot)
    for plage in axe:
        plage.pop("_d", None)
        plage.pop("_f", None)
    lignes = [{"machine": m, "slots": par_machine[m]} for m in sorted(par_machine)]
    return {"vide": not lignes, "axe": axe, "lignes": lignes,
            "periode": {"debut": d_deb.strftime("%Y-%m-%dT%H:%M:%S"),
                        "fin": d_fin.strftime("%Y-%m-%dT%H:%M:%S")}}
