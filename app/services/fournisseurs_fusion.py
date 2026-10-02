"""
Fusion de deux fiches fournisseur (`fournisseurs_fsc`) qui désignent la même société.

LE code de fusion de MySifa : le bouton de Paramètres
(`/api/fournisseurs/{source}/merge/{cible}`), l'écran des tiers RVGI, le
script `scripts/fusion_fournisseurs_doublons.py` et les migrations de reprise
passent tous par `fusionner`. Deux implémentations dériveraient, et c'est un
lot de fusions qui découvrirait la table oubliée.

Le cas type : une fiche d'usage au nom court (« Likexin ») qui porte les prix,
les certificats et les appels d'offres, et la fiche importée de RVGI
(« SHENZHEN LIKEXIN INDUSTRIAL Co. ») qui porte le numéro fournisseur, donc
les articles. Deux fiches pour un fournisseur, c'est deux lignes sur la page
d'une matière, un certificat FSC qu'on ne retrouve pas en production, un prix
qui ne suit pas.

Ce que fait `fusionner(source, cible)`
--------------------------------------
- Tout ce qui pointe la source pointe la cible. Les colonnes sont trouvées par
  introspection du schéma : une table ajoutée demain est reprise sans y
  penser. Sur une clé unique déjà occupée par la cible, la cible gagne — y
  compris un index d'expression, que l'introspection ne voit pas
  (`mp_matiere_prix`, unique sur `COALESCE(fournisseur_id, 0)`). Un prix
  principal de la source garde son statut principal.
- L'historique écrit par NOM (réceptions, saisies MyProd) prend le nom de la
  cible : l'effacer couperait la traçabilité d'une réception déjà produite.
- La cible récupère ce qu'elle n'a pas (adresse, SIRET, licence…) et le lien
  RVGI de la source si elle n'en a pas — sans quoi « importer les manquants »
  recréerait le doublon au prochain import.
- La source est supprimée. Sauf si elle garde un lien RVGI que la cible n'a pas
  pu prendre (les deux fiches étaient liées, cas BURBAN : deux tiers RVGI
  actifs) : supprimée, elle libérerait un tiers vivant que l'import
  recréerait. Elle reste alors, désactivée, avec `fusionne_dans` qui renvoie
  vers la cible ; un article RVGI de ce tiers se rattache à la cible.
- Les variantes fournisseur rendues jumelles (variante provisoire du prix +
  variante complète de l'article) sont fondues.

Ne gère pas la transaction : l'appelant commite ou annule.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

# Colonnes qui portent l'id d'un fournisseur (fournisseurs_fsc.id).
_COLS_ID = ("fournisseur_id", "fournisseur_fsc_id", "source_fournisseur_id",
            "fsc_fournisseur_id", "fournisseur_retenu_id")
# Colonnes qui portent son NOM, jointes en texte ailleurs.
_COLS_NOM = ("fournisseur", "fournisseur_manual")

# Ce que la cible n'a pas et que la source portait : récupéré plutôt que perdu.
_RECUPERABLES = (
    "licence", "certificat", "groupe", "branche", "adresse",
    "code_postal", "ville", "siret", "tva_intracom", "rcs",
    "telephone", "email", "fax", "mode_reglement", "mode_livraison",
    "delai_expedition_jours", "regime_tva", "notes",
    "traca_photo_url", "traca_explication", "traca_exemple_code",
    "fsc_date_expiration",
)
# Le lien ERP n'est pas un champ vide qu'on complète, c'est une clé : il passe
# en bloc, et seulement si la cible n'en a aucun.
_LIEN_RVGI = ("rvgi_numero", "rvgi_code", "rvgi_etat", "rvgi_motif", "rvgi_score",
              "rvgi_lie_le", "rvgi_maj_le", "rvgi_rs", "rvgi_groupe", "rvgi_bloq")


def _colonnes(conn, table: str) -> list:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def assurer_colonne(conn) -> None:
    if "fusionne_dans" not in _colonnes(conn, "fournisseurs_fsc"):
        conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN fusionne_dans INTEGER")


def _fiche(conn, fid: int) -> Optional[Dict[str, Any]]:
    cur = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (fid,))
    r = cur.fetchone()
    return dict(zip([c[0] for c in cur.description], r)) if r else None


def _vide(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def references(conn):
    """Introspecte le schéma : où l'id (ou le nom) d'un fournisseur est-il porté ?

    Renvoie (refs_id, refs_nom, refs_json) :
      refs_id   [(table, colonne, colonnes_uniques)]
      refs_nom  [(table, colonne)]
      refs_json [(table, colonne)]   listes d'ids en JSON
    """
    refs_id, refs_nom, refs_json = [], [], []
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        if t == "fournisseurs_fsc":
            continue
        try:
            cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
        except sqlite3.Error:
            continue
        uniques = {c[1] for c in cols if c[5]}
        try:
            for idx in conn.execute(f'PRAGMA index_list("{t}")').fetchall():
                if idx[2]:
                    for ic in conn.execute(f'PRAGMA index_info("{idx[1]}")').fetchall():
                        if ic[2]:
                            uniques.add(ic[2])
        except sqlite3.Error:
            pass
        for c in (c[1] for c in cols):
            if c in _COLS_ID:
                refs_id.append((t, c, uniques))
            elif c in _COLS_NOM:
                refs_nom.append((t, c))
            elif "fournisseur" in c and (c.endswith("_json") or c.endswith("_ids")):
                refs_json.append((t, c))
    return refs_id, refs_nom, refs_json


def _prix(conn, sid: int, did: int) -> int:
    """mp_matiere_prix : une ligne par (déclinaison, fournisseur), un principal par déclinaison."""
    if "fournisseur_id" not in _colonnes(conn, "mp_matiere_prix"):
        return 0
    n = 0
    for pid, decl, principal in conn.execute(
            "SELECT id, declinaison_id, principal FROM mp_matiere_prix WHERE fournisseur_id=?",
            (did,)).fetchall():
        sienne = conn.execute(
            "SELECT id FROM mp_matiere_prix WHERE declinaison_id=? AND fournisseur_id=?",
            (decl, sid)).fetchone()
        if sienne is None:
            conn.execute("UPDATE mp_matiere_prix SET fournisseur_id=? WHERE id=?", (sid, pid))
        else:
            if principal:
                conn.execute("UPDATE mp_matiere_prix SET principal=1 WHERE id=?", (sienne[0],))
            conn.execute("DELETE FROM mp_matiere_prix WHERE id=?", (pid,))
        n += 1
    return n


def fusionner(conn: sqlite3.Connection, source_id: int, cible_id: int,
              auteur: str = "") -> Dict[str, Any]:
    """Fond la fiche `source_id` dans `cible_id`. Ne committe pas.

    Lève ValueError (demande absurde) ou LookupError (fiche absente).
    """
    assurer_colonne(conn)
    sid, cid = int(source_id), int(cible_id)
    if sid == cid:
        raise ValueError("Source et cible identiques — rien à fusionner.")
    src, tgt = _fiche(conn, sid), _fiche(conn, cid)
    if not src:
        raise LookupError("Fournisseur source non trouvé")
    if not tgt:
        raise LookupError("Fournisseur cible non trouvé")
    if src.get("fusionne_dans"):
        raise ValueError(f"« {src['nom']} » est déjà fusionné.")

    moved: Dict[str, int] = {}
    renamed: Dict[str, int] = {}
    json_rewrites = 0

    def compte(cle, n):
        if n:
            moved[cle] = moved.get(cle, 0) + n

    compte("mp_matiere_prix", _prix(conn, cid, sid))
    matieres = {r[0] for r in conn.execute(
        "SELECT DISTINCT matiere_id FROM mp_variantes WHERE fournisseur_id=?", (sid,))} \
        if "fournisseur_id" in _colonnes(conn, "mp_variantes") else set()

    refs_id, refs_nom, refs_json = references(conn)
    for table, col, uniques in refs_id:
        if col in uniques:
            n = conn.execute(f'UPDATE OR IGNORE "{table}" SET "{col}"=? WHERE "{col}"=?',
                             (cid, sid)).rowcount
            reste = conn.execute(f'DELETE FROM "{table}" WHERE "{col}"=?', (sid,)).rowcount
            compte(table, n)
            if reste:
                moved[f"{table} (doublons écartés)"] = reste
            continue
        try:
            compte(table, conn.execute(f'UPDATE "{table}" SET "{col}"=? WHERE "{col}"=?',
                                       (cid, sid)).rowcount)
        except sqlite3.IntegrityError:
            # Index unique sur une expression : invisible à l'introspection.
            n = conn.execute(f'UPDATE OR IGNORE "{table}" SET "{col}"=? WHERE "{col}"=?',
                             (cid, sid)).rowcount
            reste = conn.execute(f'DELETE FROM "{table}" WHERE "{col}"=?', (sid,)).rowcount
            compte(table, n)
            if reste:
                moved[f"{table} (doublons écartés)"] = reste

    for table, col in refs_nom:
        n = conn.execute(f'UPDATE "{table}" SET "{col}"=? WHERE TRIM("{col}")=TRIM(?)',
                         (tgt["nom"], src["nom"])).rowcount
        if n:
            renamed[table] = renamed.get(table, 0) + n

    for table, col in refs_json:
        for rid, brut in conn.execute(
                f'SELECT rowid, "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" LIKE ?',
                (f"%{sid}%",)).fetchall():
            try:
                val = json.loads(brut)
            except (ValueError, TypeError):
                continue
            if not isinstance(val, list):
                continue
            neuf, change = [], False
            for x in val:
                y = cid if (isinstance(x, int) and x == sid) or (isinstance(x, str) and x == str(sid)) else x
                change = change or y != x
                if y not in neuf:
                    neuf.append(y)
            if change:
                conn.execute(f'UPDATE "{table}" SET "{col}"=? WHERE rowid=?', (json.dumps(neuf), rid))
                json_rewrites += 1

    # La fiche cible récupère ce qu'elle n'a pas.
    cols = set(tgt)
    maj: Dict[str, Any] = {}
    for champ in _RECUPERABLES:
        if champ in cols and _vide(tgt[champ]) and not _vide(src.get(champ)):
            maj[champ] = src[champ]
    if "categories" in cols:
        def _liste(v):
            try:
                p = json.loads(v) if v else []
                return p if isinstance(p, list) else []
            except (ValueError, TypeError):
                return []
        union = _liste(tgt["categories"])
        for c in _liste(src.get("categories")):
            if c not in union:
                union.append(c)
        if union != _liste(tgt["categories"]):
            maj["categories"] = json.dumps(union, ensure_ascii=False)
            if "sous_traitant" in cols and "sous_traitant" in union:
                maj["sous_traitant"] = 1
    if "has_fsc" in cols and not tgt["has_fsc"] and src.get("has_fsc"):
        maj["has_fsc"] = 1
    lien_transfere = "rvgi_numero" in cols and _vide(tgt["rvgi_numero"]) and not _vide(src.get("rvgi_numero"))
    if lien_transfere:
        for champ in _LIEN_RVGI:
            if champ in cols:
                maj[champ] = src.get(champ)
        # La source rend son numéro avant que la cible le prenne.
        conn.execute("UPDATE fournisseurs_fsc SET rvgi_numero=NULL WHERE id=?", (sid,))
    maintenant = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    if maj:
        maj["updated_at"] = maintenant
        conn.execute("UPDATE fournisseurs_fsc SET %s WHERE id=?" % ",".join(f'"{k}"=?' for k in maj),
                     list(maj.values()) + [cid])

    # Une fiche déjà fusionnée dans la source suit jusqu'à la cible.
    conn.execute("UPDATE fournisseurs_fsc SET fusionne_dans=? WHERE fusionne_dans=?", (cid, sid))
    conservee = (not lien_transfere) and not _vide(src.get("rvgi_numero"))
    if conservee:
        trace = (f"Fusionné dans « {tgt['nom']} » (#{cid}) le {maintenant[:10]}"
                 + (f" par {auteur}" if auteur else "") + " — gardé pour son lien RVGI.")
        conn.execute(
            "UPDATE fournisseurs_fsc SET actif=0, fusionne_dans=?, updated_at=?, "
            "notes=TRIM(COALESCE(notes,'') || ' ' || ?) WHERE id=?",
            (cid, maintenant, trace, sid))
    else:
        conn.execute("DELETE FROM fournisseurs_fsc WHERE id=?", (sid,))

    variantes = 0
    if matieres:
        from app.services.mp_variantes import fusionner_provisoires
        variantes = fusionner_provisoires(conn, matieres)

    return {"source": {"id": sid, "nom": src["nom"]},
            "target": {"id": cid, "nom": tgt["nom"]},
            "moved": moved, "renamed": renamed, "json_rewrites": json_rewrites,
            "champs_recuperes": sorted(k for k in maj if k != "updated_at"),
            "lien_rvgi_transfere": bool(lien_transfere),
            "source_conservee": bool(conservee),
            "variantes_fusionnees": variantes}


def resoudre(conn: sqlite3.Connection, fournisseur_id):
    """L'id à utiliser pour un fournisseur : lui-même, ou la fiche dans laquelle il a été fusionné."""
    if fournisseur_id is None:
        return None
    if "fusionne_dans" not in _colonnes(conn, "fournisseurs_fsc"):
        return int(fournisseur_id)
    vu = set()
    fid = int(fournisseur_id)
    while fid not in vu:
        vu.add(fid)
        r = conn.execute("SELECT fusionne_dans FROM fournisseurs_fsc WHERE id=?", (fid,)).fetchone()
        if not r or not r[0]:
            return fid
        fid = int(r[0])
    return fid


def par_numero_rvgi(conn: sqlite3.Connection, numero) -> Optional[int]:
    """Le fournisseur MySifa d'un numéro fournisseur RVGI (fusions suivies, fiche active d'abord)."""
    try:
        num = int(str(numero).strip())
    except (TypeError, ValueError):
        return None
    if "rvgi_numero" not in _colonnes(conn, "fournisseurs_fsc"):
        return None
    r = conn.execute(
        "SELECT id FROM fournisseurs_fsc WHERE rvgi_numero=? ORDER BY COALESCE(actif,1) DESC, id LIMIT 1",
        (num,)).fetchone()
    return resoudre(conn, r[0]) if r else None
