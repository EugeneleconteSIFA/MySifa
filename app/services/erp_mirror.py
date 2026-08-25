"""Miroir RVGI — lecture seule.

Ce module est le SEUL chemin d'accès au miroir de l'ERP (`data/erp_mirror.db`,
alimenté par `scripts/import_rvgi_csv.py` depuis les CSV de
`scripts/export_rvgi_csv.ps1`).

Trois garanties, dans cet ordre d'importance :

1. **Lecture seule au niveau du pilote.** La connexion est ouverte en
   `mode=ro` : une écriture ne se contente pas d'être interdite par
   convention, elle échoue. RVGI est la source, MySifa lit.
2. **Aucune interpolation d'entrée utilisateur.** Les noms de table, de
   colonne et de tri viennent du catalogue d'écrans et sont validés par
   `_ident()`. Tout le reste passe en paramètre lié.
3. **Sentinelles neutralisées à la lecture, jamais en base.** RVGI n'a pas de
   NULL : il écrit `30/11/1999` pour une date vide, `99999999999.99` pour
   « pas de maximum », `0` pour un prix non renseigné. Le miroir garde ces
   valeurs telles quelles — c'est ce que contient l'ERP — et c'est ici qu'on
   les traduit en « rien ». Corriger en base ferait mentir le miroir sur sa
   source.

Le miroir peut être absent (poste hors réseau, export jamais lancé) :
`miroir_present()` le dit, et l'app ERP l'annonce au lieu de tomber en erreur.
"""

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import ERP_MIRROR_DB

# ── Sentinelles RVGI ─────────────────────────────────────────────────────────
DATE_VIDE = "1999-11-30"        # date non renseignée
DATE_INFINIE = "2099-12-31"     # pas de fin de validité
MAX_SENTINELLE = 99999999999.0  # « pas de maximum »

RE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Taille de page : au-delà, la grille devient illisible avant d'être lente.
TAILLE_PAGE_DEFAUT = 100
TAILLE_PAGE_MAX = 500


def _ident(nom):
    """Valide un identifiant SQL. Refuse tout ce qui n'est pas un nom simple."""
    if not RE_IDENT.match(str(nom or "")):
        raise ValueError("Identifiant SQL invalide : %r" % (nom,))
    return nom


def valider_ref(expr):
    """Alias public de `_ref`, pour les appelants hors module."""
    return _ref(expr)


def _ref(expr):
    """Valide une référence `alias.colonne` (ou `colonne` seule)."""
    parties = str(expr or "").split(".")
    if len(parties) > 2:
        raise ValueError("Référence de colonne invalide : %r" % (expr,))
    for p in parties:
        _ident(p)
    return expr


def miroir_present():
    return bool(ERP_MIRROR_DB) and os.path.exists(ERP_MIRROR_DB)


@contextmanager
def get_erp_db():
    """Connexion SQLite en lecture seule sur le miroir."""
    if not miroir_present():
        raise FileNotFoundError(
            "Miroir ERP absent (%s). Lancer scripts/export_rvgi_csv.ps1 depuis un "
            "poste du réseau SIFA, puis scripts/import_rvgi_csv.py." % ERP_MIRROR_DB
        )
    uri = Path(ERP_MIRROR_DB).absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def tables_presentes(conn):
    return {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def meta():
    """Fraîcheur du miroir : ce qui a été importé, quand, depuis quel relevé."""
    if not miroir_present():
        return {"present": False, "tables": [], "importe_le": None, "releve_le": None, "lignes": 0}
    with get_erp_db() as conn:
        if "erp_meta" not in tables_presentes(conn):
            return {"present": True, "tables": [], "importe_le": None, "releve_le": None, "lignes": 0}
        lignes = [dict(r) for r in conn.execute(
            "SELECT nom, lignes, colonnes, importe_le, releve_le FROM erp_meta ORDER BY nom"
        )]
    total = sum(int(r.get("lignes") or 0) for r in lignes)
    return {
        "present": True,
        "tables": lignes,
        "importe_le": max((r.get("importe_le") or "") for r in lignes) if lignes else None,
        "releve_le": max((r.get("releve_le") or "") for r in lignes) if lignes else None,
        "lignes": total,
    }


# ── Neutralisation des sentinelles ───────────────────────────────────────────

def _propre_date(v):
    s = str(v or "").strip()
    if not s:
        return None
    if s.startswith(DATE_VIDE) or s.startswith(DATE_INFINIE):
        return None
    return s


def _propre_nombre(v, type_col):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if abs(f) >= MAX_SENTINELLE:
        return None
    # Un prix à 0 dans RVGI veut dire « non renseigné », jamais « gratuit ».
    # Une quantité à 0, elle, est une vraie quantité.
    if type_col == "prix" and f == 0:
        return None
    return v


def nettoyer(valeur, type_col):
    """Traduit une valeur RVGI en valeur affichable. `None` = rien à montrer."""
    if valeur is None:
        return None
    if type_col in ("date", "datetime"):
        return _propre_date(valeur)
    if type_col in ("nombre", "qte", "prix", "montant", "pct"):
        return _propre_nombre(valeur, type_col)
    if isinstance(valeur, str):
        v = valeur.strip()
        return v or None
    return valeur


# ── Moteur de liste générique ────────────────────────────────────────────────

def _from(ec):
    """Clause FROM + jointures de l'écran, validées."""
    _ident(ec["table"])
    depart = '"%s" %s' % (ec["table"], _ident(ec["alias"]))
    for j in ec.get("jointures", []):
        _ident(j["table"])
        _ident(j["alias"])
        _ref(j["gauche"])
        _ref(j["droite"])
        depart += ' LEFT JOIN "%s" %s ON %s = %s' % (
            j["table"], j["alias"], j["gauche"], j["droite"]
        )
    return depart


def _tables_requises(ec):
    noms = [ec["table"]] + [j["table"] for j in ec.get("jointures", [])]
    return set(noms)


def ecran_disponible(ec, presentes):
    """Un écran n'existe que si sa table principale a été importée."""
    return ec["table"] in presentes


def lister(ec, q="", filtres=None, tri=None, sens="asc", page=1,
           taille=TAILLE_PAGE_DEFAUT, extra=None):
    """Liste paginée d'un écran. Renvoie colonnes, lignes, total.

    `extra` : conditions supplémentaires, sous forme de couples
    (fragment SQL déjà validé, valeur). Sert aux pièces liées, qui joignent
    sur des colonnes que l'utilisateur ne filtre pas lui-même.
    """
    filtres = filtres or {}
    taille = max(1, min(int(taille or TAILLE_PAGE_DEFAUT), TAILLE_PAGE_MAX))
    page = max(1, int(page or 1))

    colonnes = ec["colonnes"]
    select = []
    for c in colonnes:
        _ident(c["nom"])
        # Colonne composite : `code1` + `code2` affichés « 890/0112 ». Les
        # morceaux sont sélectionnés séparément et assemblés en Python — pas
        # de concaténation SQL, donc pas d'expression à valider.
        if c.get("parts"):
            for i, p in enumerate(c["parts"]):
                _ref(p)
                select.append('%s AS "%s__%d"' % (p, c["nom"], i))
        else:
            _ref(c["c"])
            select.append('%s AS "%s"' % (c["c"], c["nom"]))
    _ref(ec["cle_ligne"])
    select.append('%s AS "_id"' % ec["cle_ligne"])

    conditions = []
    params = []

    for cond in ec.get("conditions", []):
        conditions.append(cond)

    for fragment, valeur in (extra or []):
        conditions.append(fragment)
        params.append(valeur)

    # Recherche plein-texte sur les colonnes déclarées par l'écran.
    q = (q or "").strip()
    if q and ec.get("recherche"):
        morceaux = []
        for ref in ec["recherche"]:
            _ref(ref)
            morceaux.append("CAST(%s AS TEXT) LIKE ?" % ref)
            params.append("%" + q + "%")
        conditions.append("(" + " OR ".join(morceaux) + ")")

    # Filtres : uniquement ceux que l'écran déclare.
    par_nom = {f["nom"]: f for f in ec.get("filtres", [])}
    for nom, valeur in filtres.items():
        f = par_nom.get(nom)
        if not f:
            continue
        valeur = str(valeur if valeur is not None else "").strip()
        if valeur == "":
            continue
        _ref(f["col"])
        if f.get("type") == "date_min":
            conditions.append("%s >= ?" % f["col"])
            params.append(valeur)
        elif f.get("type") == "date_max":
            conditions.append("%s <= ?" % f["col"])
            params.append(valeur)
        elif f.get("type") == "contient":
            conditions.append("CAST(%s AS TEXT) LIKE ?" % f["col"])
            params.append("%" + valeur + "%")
        else:
            conditions.append("CAST(%s AS TEXT) = ?" % f["col"])
            params.append(valeur)

    ou = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    depart = _from(ec)

    # Tri : la colonne doit appartenir à l'écran, sinon on retombe sur le tri
    # par défaut. Aucun nom de colonne ne vient du client sans passer par là.
    par_col = {c["nom"]: c for c in colonnes}
    if tri and tri in par_col:
        c_tri = par_col[tri]
        col_tri = c_tri["c"] if c_tri.get("c") else c_tri["parts"][0]
    else:
        col_tri = ec["tri_defaut"][0]
        sens = ec["tri_defaut"][1]
    _ref(col_tri)
    sens_sql = "DESC" if str(sens).lower() == "desc" else "ASC"

    sql = "SELECT %s FROM %s%s ORDER BY %s %s LIMIT ? OFFSET ?" % (
        ", ".join(select), depart, ou, col_tri, sens_sql
    )

    with get_erp_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM %s%s" % (depart, ou), params
        ).fetchone()[0]
        brut = conn.execute(sql, params + [taille, (page - 1) * taille]).fetchall()

    lignes = []
    for r in brut:
        d = {"_id": r["_id"]}
        for c in colonnes:
            if c.get("parts"):
                bouts = []
                for i in range(len(c["parts"])):
                    v = r["%s__%d" % (c["nom"], i)]
                    v = str(v).strip() if v is not None else ""
                    if v:
                        bouts.append(v)
                d[c["nom"]] = c.get("joint", "/").join(bouts) or None
            else:
                d[c["nom"]] = nettoyer(r[c["nom"]], c.get("type"))
        lignes.append(d)

    return {
        "colonnes": [
            {k: v for k, v in c.items() if k != "c"} for c in colonnes
        ],
        "lignes": lignes,
        "total": total,
        "page": page,
        "taille": taille,
        "tri": tri if (tri and tri in par_col) else None,
        "sens": sens_sql.lower(),
    }


def detail(ec, ident):
    """Toutes les colonnes de la ligne, groupées comme l'écran le déclare.

    Le reste — ce que le catalogue ne nomme pas — est renvoyé dans un groupe
    « Autres champs ». On ne masque rien : un écran ERP qui cache une colonne
    oblige à rouvrir RVGI, et le bouton n'a plus d'intérêt.
    """
    _ref(ec["cle_ligne"])
    depart = _from(ec)
    sql = "SELECT * FROM %s WHERE %s = ?" % (depart, ec["cle_ligne"])
    with get_erp_db() as conn:
        row = conn.execute(sql, [ident]).fetchone()
        if row is None:
            return None
        brut = dict(row)

    libelles = {}
    types = {}
    for c in ec["colonnes"]:
        refs = c["parts"] if c.get("parts") else [c["c"]]
        for ref in refs:
            court = ref.split(".")[-1]
            libelles.setdefault(court, c.get("label") or court)
            types.setdefault(court, c.get("type") if not c.get("parts") else "texte")
    for court, lib in (ec.get("labels_detail") or {}).items():
        libelles[court] = lib

    groupes = []
    vus = set()
    for g in ec.get("detail", []):
        champs = []
        for court in g["champs"]:
            if court not in brut:
                continue
            vus.add(court)
            champs.append({
                "nom": court,
                "label": libelles.get(court, court),
                "type": types.get(court, "texte"),
                "valeur": nettoyer(brut[court], types.get(court)),
            })
        if champs:
            groupes.append({"titre": g["titre"], "champs": champs})

    autres = []
    for court, valeur in brut.items():
        if court in vus or court in ("corbeille", "salm", "bloq"):
            continue
        autres.append({
            "nom": court,
            "label": libelles.get(court, court),
            "type": types.get(court, "texte"),
            "valeur": nettoyer(valeur, types.get(court)),
        })
    if autres:
        groupes.append({"titre": "Autres champs", "champs": autres, "replie": True})

    return {"id": ident, "groupes": groupes}


def compter(ec):
    """Nombre de lignes d'un écran, pour les cartes du menu."""
    try:
        with get_erp_db() as conn:
            if ec["table"] not in tables_presentes(conn):
                return None
            ou = ""
            if ec.get("conditions"):
                ou = " WHERE " + " AND ".join(ec["conditions"])
            return conn.execute(
                'SELECT COUNT(*) FROM "%s" %s%s' % (ec["table"], _ident(ec["alias"]), ou)
            ).fetchone()[0]
    except Exception:
        return None


# ── Pièces liées ─────────────────────────────────────────────────────────────

def ligne_brute(ec, ident):
    """La ligne source, toutes colonnes, pour alimenter les jointures."""
    _ref(ec["cle_ligne"])
    sql = "SELECT * FROM %s WHERE %s = ?" % (_from(ec), ec["cle_ligne"])
    with get_erp_db() as conn:
        row = conn.execute(sql, [ident]).fetchone()
    return dict(row) if row is not None else None


def liens(ec, ident, resoudre, par_lien=5):
    """Les pièces rattachées à une ligne, écran par écran.

    `resoudre(cle)` rend l'écran cible adapté au miroir, ou None. Chaque lien
    déclare `sur` : {colonne de l'écran cible : champ de la ligne source}. Un
    lien dont la valeur source est vide est ignoré — mieux vaut ne rien
    proposer qu'un onglet qui ramène toute la table.
    """
    source = ligne_brute(ec, ident)
    if source is None:
        return []

    resultats = []
    for lien in ec.get("liens", []):
        cible = resoudre(lien["ecran"])
        if not cible:
            continue

        extra = []
        valeurs = {}
        complet = True
        for ref_cible, champ_source in lien["sur"].items():
            _ref(ref_cible)
            v = source.get(champ_source)
            if v is None or str(v).strip() == "":
                complet = False
                break
            # Comparaison en texte : le miroir type colonne par colonne, et
            # `numcde` peut être INTEGER d'un côté, TEXT de l'autre.
            extra.append(("CAST(%s AS TEXT) = ?" % ref_cible, str(v).strip()))
            valeurs[ref_cible.split(".")[-1]] = v
        if not complet or not extra:
            continue

        try:
            res = lister(cible, taille=par_lien, extra=extra)
        except Exception as e:
            # Un lien qui casse se signale au lieu de disparaitre : sinon une
            # jointure fausse passe pour « aucune piece rattachee ».
            resultats.append({
                "label": lien["label"], "ecran": lien["ecran"],
                "erreur": str(e)[:200], "total": 0, "colonnes": [], "lignes": [],
                "valeurs": valeurs,
            })
            continue

        resultats.append({
            "label": lien["label"],
            "ecran": lien["ecran"],
            "total": res["total"],
            "colonnes": res["colonnes"][: lien.get("colonnes", 5)],
            "lignes": [
                {k: v for k, v in l.items()
                 if k == "_id" or k in {c["nom"] for c in res["colonnes"][: lien.get("colonnes", 5)]}}
                for l in res["lignes"]
            ],
            "valeurs": valeurs,
        })
    return resultats
