"""
SIFA — Chiffrage d'un devis : les postes en euros du classeur.

Le socle (`devis_parser`) lit les temps, les métrages et la quantité : de quoi
comparer un atelier, pas de quoi dire si un dossier a gagné de l'argent. Ce
module lit ce qui manque pour la rentabilité — coût matière, outil,
emballage, transport, coût de production, prix de vente, marge brute, coût
horaire — sur la feuille « Prix » du modèle maison.

PAR LIBELLÉ, JAMAIS PAR COORDONNÉE. Le taux horaire est en B44 sur un modèle
et en B43 sur un autre ; le MB % passe de L5 à L7. Une lecture par cellule
fixe rendrait un chiffre faux sans prévenir. On cherche le libellé, on prend
la valeur voisine, et on garde la cellule lue (`sources`) pour que l'écran
puisse dire d'où vient chaque montant.

LES VALEURS LUES SONT CONTRÔLÉES, PAS CRUES. `rentabilite_calcul.controler_devis`
refait le calcul du classeur à partir des postes lus et signale tout écart :
c'est ce contrôle, joué sur tous les devis importés, qui prouve que le moteur
reproduit bien le classeur — et qui attrape un libellé mal lu.

Comme le parser, ce module ne devine jamais : un poste absent reste absent
(None), il ne devient pas zéro.
"""
import json
import os
import re
from datetime import datetime
from typing import Any, Optional

from app.services.devis_parser import _find_value, charger_feuilles

# (clé, motif du libellé, décalage de colonne, unité, libellé affiché)
# Le décalage vaut 3 pour le métrage du bloc « CALCUL Temps et métrage », qui
# pose le temps en J et le métrage en L sur la ligne d'un même libellé.
# Quand la cellule voisine est vide, `_find_value` lit la cellule SOUS le
# libellé : c'est le cas de « surmarge s/ dossier » et de « Cout Horaire ».
POSTES = (
    ("prix_m2_corrige",      r"^prix\s+corrig",                       1, "€/m²", "Prix matière corrigé"),
    ("prix_m2_base",         r"^prix\s+au\s+m\s*[2²]\s*$",             1, "€/m²", "Prix matière au m²"),
    ("num_matiere",          r"^mati[eè]re\s+n",                      1, "",     "Matière n°"),
    ("cout_matiere",         r"^co[uû]t\s+mati[eè]re",                1, "€",    "Coût matière"),
    ("cout_encre",           r"^co[uû]t\s+encre",                     1, "€",    "Coût encre"),
    ("cout_cliche",          r"^co[uû]t\s+clich",                     1, "€",    "Coût cliché"),
    ("cout_outil",           r"^co[uû]t\s+outil",                     1, "€",    "Coût outil"),
    ("cout_emballage",       r"^co[uû]t\s+emballage",                 1, "€",    "Coût emballage et mandrins"),
    ("cout_production",      r"^co[uû]t\s+production",                1, "€",    "Coût production"),
    ("cout_conditionnement", r"^co[uû]t\s+conditionnement",           1, "€",    "Coût conditionnement"),
    ("cout_manutention",     r"^co[uû]t\s+manutention",               1, "€",    "Coût manutention"),
    ("cout_transport",       r"^co[uû]t\s+transport",                 1, "€",    "Coût transport"),
    ("prix_revient",         r"^prix\s+normal\s+de\s+vente",          1, "€",    "Prix de revient"),
    ("remise",               r"^remise\s*$",                          1, "€",    "Remise"),
    ("surmarge",             r"^surmarge\s*$",                        1, "€",    "Surmarge"),
    ("surmarge_taux",        r"^surmarge\s+s\s*/?\s*dossier",         1, "",     "Taux de surmarge"),
    ("prix_vente",           r"^budget\s*$",                          1, "€",    "Prix de vente"),
    ("marge_brute",          r"^marge\s+brute\s+r[ée]elle",           1, "€",    "Marge brute"),
    ("cout_horaire",         r"^co[uû]t\s+horaire",                   1, "€/h",  "Coût horaire (MB par heure)"),
    ("taux_horaire",         r"^co[uû]t\s+kdo",                       1, "€/h",  "Taux machine (KDO)"),
    ("temps_total_mn",       r"^s\s*/?\s*total$",                     1, "mn",   "Temps total devisé"),
    ("metrage_total_ml",     r"^s\s*/?\s*total$",                     3, "ml",   "Métrage total devisé"),
)

CHAMPS_CHIFFRAGE = tuple(p[0] for p in POSTES)
LIBELLES = {p[0]: (p[4], p[3]) for p in POSTES}

# Postes que la marge brute du classeur retire du prix de vente. Le coût de
# production n'en fait PAS partie : le temps machine pèse sur le coût horaire,
# pas sur la marge brute (formule `Prix!J18`).
POSTES_DIRECTS = ("cout_matiere", "cout_encre", "cout_cliche", "cout_outil",
                  "cout_emballage", "cout_transport")


def _nombre(valeur) -> Optional[float]:
    if valeur is None:
        return None
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return None
    return None if v != v else v  # NaN


def lire_chiffrage(file_bytes: bytes, filename: str) -> dict:
    """Lit les postes en euros d'un classeur de devis.

    Rend `{"valeurs": {clé: nombre|None}, "sources": {clé: "Prix!J4"},
    "erreurs": [...]}`. Un classeur sans feuille Prix rend des valeurs
    toutes à None et une erreur — jamais une exception.
    """
    valeurs: dict[str, Any] = {c: None for c in CHAMPS_CHIFFRAGE}
    sources: dict[str, str] = {}
    erreurs: list[str] = []

    if str(filename or "").lower().rsplit(".", 1)[-1] not in ("xlsx", "xlsm", "xls"):
        return {"valeurs": valeurs, "sources": sources,
                "erreurs": ["Pas un classeur : chiffrage non lu."]}

    feuilles, err = charger_feuilles(file_bytes, filename)
    erreurs.extend(err)
    nom_prix = next((s for s in feuilles if "prix" in s.lower()), None)
    if not nom_prix:
        erreurs.append("Feuille « Prix » introuvable : chiffrage non lu.")
        return {"valeurs": valeurs, "sources": sources, "erreurs": erreurs}

    df = feuilles[nom_prix]
    for cle, motif, decalage, _unite, _libelle in POSTES:
        try:
            v, coord = _find_value(df, motif, col_offset=decalage, sheet_name=nom_prix)
        except Exception as e:  # une feuille malformée ne doit rien casser
            erreurs.append(f"{cle} : {e}")
            continue
        if cle == "num_matiere":
            if v is not None and str(v).strip():
                txt = str(v).strip()
                valeurs[cle] = txt[:-2] if txt.endswith(".0") else txt
                sources[cle] = coord
            continue
        n = _nombre(v)
        if n is None:
            continue
        valeurs[cle] = n
        if coord:
            sources[cle] = coord
    return {"valeurs": valeurs, "sources": sources, "erreurs": erreurs}


def prix_m2_retenu(valeurs: dict) -> Optional[float]:
    """Le prix au m² que le classeur applique : le corrigé s'il est saisi."""
    corrige = valeurs.get("prix_m2_corrige")
    if corrige:
        return corrige
    return valeurs.get("prix_m2_base") or None


# ══════════════════════════════════════════════════════════════════
# Persistance
# ══════════════════════════════════════════════════════════════════

def table_presente(conn) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='devis_chiffrage'"
    ).fetchone())


def enregistrer(conn, devis_id: int, lecture: dict) -> bool:
    """Remplace le chiffrage d'un devis. Ne commite pas : l'appelant le fait."""
    if not table_presente(conn):
        return False
    v = lecture.get("valeurs") or {}
    cols = list(CHAMPS_CHIFFRAGE)
    conn.execute("DELETE FROM devis_chiffrage WHERE devis_id=?", (devis_id,))
    conn.execute(
        f"""INSERT INTO devis_chiffrage
            (devis_id, {", ".join(cols)}, sources_json, erreurs_json, lu_at)
            VALUES ({", ".join("?" * (len(cols) + 4))})""",
        (devis_id, *[v.get(c) for c in cols],
         json.dumps(lecture.get("sources") or {}, ensure_ascii=False),
         json.dumps(lecture.get("erreurs") or [], ensure_ascii=False),
         datetime.now().isoformat(timespec="seconds")),
    )
    return True


def lire_et_enregistrer(conn, devis_id: int, file_bytes: bytes, filename: str) -> bool:
    """Le geste des chemins d'import : lire puis poser. Jamais bloquant."""
    try:
        return enregistrer(conn, devis_id, lire_chiffrage(file_bytes, filename))
    except Exception:
        return False


def chemin_fichier(fichier_chemin: Optional[str]) -> Optional[str]:
    """Le chemin réel du classeur conservé, ou None s'il n'existe plus.

    `_conserver_fichier` enregistre un NOM relatif au dossier des devis
    (`DEVIS_UPLOAD_DIR`) ; un chemin absolu reste accepté.
    """
    nom = str(fichier_chemin or "").strip()
    if not nom:
        return None
    if not os.path.isabs(nom):
        from config import DEVIS_UPLOAD_DIR
        nom = os.path.join(DEVIS_UPLOAD_DIR, os.path.basename(nom))
    return nom if os.path.isfile(nom) else None


def relire_depuis_fichier(conn, devis_id: int) -> Optional[dict]:
    """Relit le classeur conservé à l'import. None si le fichier a disparu."""
    row = conn.execute(
        "SELECT filename, fichier_chemin FROM devis WHERE id=?", (devis_id,)
    ).fetchone()
    if not row:
        return None
    chemin = chemin_fichier(row["fichier_chemin"])
    if not chemin:
        return None
    with open(chemin, "rb") as f:
        contenu = f.read()
    lecture = lire_chiffrage(contenu, row["filename"] or chemin)
    enregistrer(conn, devis_id, lecture)
    return lecture


def chiffrage_du_devis(conn, devis_id: int) -> Optional[dict]:
    """Le chiffrage en base, valeurs et sources. None s'il n'a pas été lu."""
    if not table_presente(conn):
        return None
    row = conn.execute(
        "SELECT * FROM devis_chiffrage WHERE devis_id=?", (devis_id,)
    ).fetchone()
    if not row:
        return None
    valeurs = {c: row[c] for c in CHAMPS_CHIFFRAGE}
    try:
        sources = json.loads(row["sources_json"] or "{}")
    except (TypeError, ValueError):
        sources = {}
    return {"valeurs": valeurs, "sources": sources, "lu_at": row["lu_at"]}
