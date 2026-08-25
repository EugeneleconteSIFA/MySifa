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

from config import DB_PATH, ERP_MIRROR_DB

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
def get_erp_db(avec_mysifa=False):
    """Connexion SQLite en lecture seule sur le miroir.

    `avec_mysifa=True` attache EN PLUS la base de production de MySifa, elle
    aussi en `mode=ro`, sous le schéma `mysifa`. Une seule chose l'exige : la
    colonne de rattachement des écrans, qui doit pouvoir être filtrée et triée
    — donc jointe dans la même requête.

    Les deux bases restent en lecture seule au niveau du pilote : attacher
    n'ouvre aucun droit d'écriture, ni vers RVGI, ni vers MySifa.
    """
    if not miroir_present():
        raise FileNotFoundError(
            "Miroir ERP absent (%s). Lancer scripts/export_rvgi_csv.ps1 depuis un "
            "poste du réseau SIFA, puis scripts/import_rvgi_csv.py." % ERP_MIRROR_DB
        )
    uri = Path(ERP_MIRROR_DB).absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        if avec_mysifa:
            try:
                conn.execute(
                    "ATTACH DATABASE ? AS mysifa",
                    [Path(DB_PATH).absolute().as_uri() + "?mode=ro"],
                )
            except sqlite3.Error:
                # Base de production illisible : l'écran perd sa colonne de
                # rattachement, il ne tombe pas. `mysifa_attachee()` le dit.
                pass
        yield conn
    finally:
        conn.close()


def mysifa_attachee(conn):
    """La base de production est-elle jointe à cette connexion ?"""
    try:
        return any(r[1] == "mysifa" for r in conn.execute("PRAGMA database_list"))
    except sqlite3.Error:
        return False


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


# Ce que MySifa a rattaché à une ligne de RVGI, exprimé en SQL. Deux
# sous-requêtes corrélées : combien de rattachements portent cette ligne, et
# quelle quantité ils couvrent. Un rattachement posé sur la pièce entière
# (`ligne IS NULL`) répond pour toutes ses lignes — c'est ce qui permet de
# rattacher une commande de 84 lignes en un seul enregistrement.
_SQL_RATT_OU = (
    " FROM mysifa.rvgi_rattachements r"
    " WHERE r.piece = '%s'"
    "   AND TRIM(CAST(r.numero AS TEXT)) = TRIM(CAST(%s AS TEXT))"
    "   AND (r.ligne IS NULL OR r.ligne = %s)"
)


def _sql_rattachement(piece, col_numero, col_ligne):
    """(compte, quantité couverte, quantité non chiffrée) pour une ligne."""
    ou = _SQL_RATT_OU % (piece, col_numero, col_ligne)
    return (
        "(SELECT COUNT(*)%s)" % ou,
        "(SELECT COALESCE(SUM(r.qte), 0)%s)" % ou,
        "(SELECT COUNT(*)%s AND r.qte IS NULL)" % ou,
        "(SELECT COUNT(*)%s AND r.etat = 'a_verifier')" % ou,
    )


def _colonnes_rattachement(ec):
    """L'écran porte-t-il un rattachement, et sur quelle nature de pièce ?"""
    p = ec.get("rattachable")
    if not p:
        return None
    alias = ec["alias"]
    col_ligne = p.get("col_ligne")
    return {
        "piece": p["piece"],
        "numero": "%s.numero" % alias,
        "ligne": ("%s.%s" % (alias, col_ligne)) if col_ligne else "NULL",
        "col_qte": ("%s.%s" % (alias, p["col_qte"])) if p.get("col_qte") else None,
    }


def _etat_rattachement(r, ratt, ligne):
    """Traduit les compteurs SQL en un état lisible.

    « Rattaché » ne veut pas dire « couvert » : un dossier peut n'avoir pris
    qu'une partie de la ligne. C'est cette nuance qui rend la colonne utile —
    sinon elle ne dirait que « quelqu'un s'en est occupé ».
    """
    n = int(r["_ratt_n"] or 0)
    if not n:
        return {"etat": "non", "n": 0}
    if int(r["_ratt_douteux"] or 0):
        return {"etat": "douteux", "n": n}
    if int(r["_ratt_tout"] or 0):
        return {"etat": "oui", "n": n}          # au moins un rattachement couvre tout
    pris = float(r["_ratt_qte"] or 0)
    total = None
    if ratt["col_qte"]:
        brut = ligne.get(ratt["col_qte"].split(".")[-1])
        try:
            total = float(brut) if brut is not None else None
        except (TypeError, ValueError):
            total = None
    if total and pris + 1e-6 < total:
        return {"etat": "partiel", "n": n, "pris": pris, "total": total}
    return {"etat": "oui", "n": n, "pris": pris, "total": total}


def lister(ec, q="", filtres=None, tri=None, sens="asc", page=1,
           taille=TAILLE_PAGE_DEFAUT, extra=None, compter=True, rattachement=False,
           filtre_ratt=""):
    """Liste paginée d'un écran. Renvoie colonnes, lignes, total.

    `extra` : conditions supplémentaires, sous forme de couples
    (fragment SQL déjà validé, valeur). Sert aux pièces liées, qui joignent
    sur des colonnes que l'utilisateur ne filtre pas lui-même.

    `compter=False` : on renvoie `total = None` au lieu de compter. Le COUNT
    est un balayage complet de la table ; sur une recherche qui interroge les
    vingt-sept écrans d'un coup, il double le travail pour un chiffre que
    personne ne lit.
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

    ratt = _colonnes_rattachement(ec) if rattachement else None
    if ratt:
        _ref(ratt["numero"])
        if ratt["ligne"] != "NULL":
            _ref(ratt["ligne"])
        if ratt["col_qte"]:
            _ref(ratt["col_qte"])
        n, somme, sans_qte, douteux = _sql_rattachement(
            ratt["piece"], ratt["numero"], ratt["ligne"])
        select.append('%s AS "_ratt_n"' % n)
        select.append('%s AS "_ratt_qte"' % somme)
        select.append('%s AS "_ratt_tout"' % sans_qte)
        select.append('%s AS "_ratt_douteux"' % douteux)

    conditions = []
    params = []

    for cond in ec.get("conditions", []):
        conditions.append(cond)

    for fragment, valeur in (extra or []):
        conditions.append(fragment)
        params.append(valeur)

    # Filtrer sur l'état de rattachement suppose de joindre les deux bases : on
    # le fait dans la requête, pas après coup, sinon « ne montrer que les
    # commandes non rattachées » ne pourrait pas se paginer.
    if ratt and filtre_ratt:
        n, somme, sans_qte, douteux = _sql_rattachement(
            ratt["piece"], ratt["numero"], ratt["ligne"])
        qte = ratt["col_qte"]
        if filtre_ratt == "non":
            conditions.append("%s = 0" % n)
        elif filtre_ratt == "oui":
            conditions.append("%s > 0" % n)
        elif filtre_ratt == "douteux":
            conditions.append("%s > 0" % douteux)
        elif filtre_ratt == "partiel" and qte:
            # Partiel = rattaché, mais toutes les quantités sont chiffrées et
            # leur somme reste sous la quantité de la ligne.
            conditions.append(
                "(%s > 0 AND %s = 0 AND %s < COALESCE(%s, 0))" % (n, sans_qte, somme, qte))
        elif filtre_ratt == "partiel":
            conditions.append("(%s > 0 AND %s = 0)" % (n, sans_qte))

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
    if tri == "_id":
        # Ordre naturel de la pièce : celui dans lequel RVGI a écrit les lignes.
        # Sert quand l'écran ne montre aucun numéro de ligne.
        col_tri = ec["cle_ligne"]
    elif tri and tri in par_col:
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

    with get_erp_db(avec_mysifa=bool(ratt)) as conn:
        if ratt and not mysifa_attachee(conn):
            # Sans la base de production, la colonne n'a pas de sens : on rend
            # l'écran sans elle plutôt qu'une erreur.
            return lister(ec, q=q, filtres=filtres, tri=tri, sens=sens, page=page,
                          taille=taille, extra=extra, compter=compter)
        total = None
        if compter:
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
        if ratt:
            d["_ratt"] = _etat_rattachement(r, ratt, d)
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


def _identiques(a, b):
    """Deux valeurs RVGI disent-elles la même chose ?

    Comparaison en texte : le miroir type colonne par colonne, et le même
    numéro peut être INTEGER d'un côté, TEXT de l'autre.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        try:
            return abs(float(a) - float(b)) < 1e-9
        except (TypeError, ValueError):
            pass
    return str(a).strip() == str(b).strip()


def _libelles_et_types(ec):
    """Libellé et type d'affichage de chaque colonne courte de l'écran."""
    libelles, types = {}, {}
    for c in ec["colonnes"]:
        refs = c["parts"] if c.get("parts") else [c["c"]]
        for ref in refs:
            court = ref.split(".")[-1]
            libelles.setdefault(court, c.get("label") or court)
            types.setdefault(court, c.get("type") if not c.get("parts") else "texte")
    for court, lib in (ec.get("labels_detail") or {}).items():
        libelles[court] = lib
    return libelles, types


def _composites(ec):
    """Les colonnes que l'écran assemble : `code1` + `code2` → « 986/0005 ».

    Rendre « Code 1 : 986 » puis « Code 2 : 0005 » sur deux lignes oblige le
    lecteur à recomposer de tête une référence que la grille, elle, affiche
    déjà assemblée. On applique donc au détail la composition déjà déclarée
    pour la grille — une seule source de vérité.

    Renvoie {première part → définition} et l'ensemble des parts absorbées.
    """
    par_tete, absorbees = {}, set()
    for c in ec["colonnes"]:
        if not c.get("parts"):
            continue
        parts = [p.split(".")[-1] for p in c["parts"]]
        if not parts:
            continue
        par_tete[parts[0]] = {
            "nom": c["nom"], "label": c.get("label") or c["nom"],
            "type": c.get("type") or "ref", "parts": parts,
            "joint": c.get("joint") or "/",
        }
        absorbees.update(parts)
    return par_tete, absorbees


def _valeur_composite(defn, brut):
    bouts = [str(brut.get(p) or "").strip() for p in defn["parts"]]
    bouts = [b for b in bouts if b]
    return defn["joint"].join(bouts) if bouts else None


def detail(ec, ident, exclure=None, entete=None):
    """Toutes les colonnes de la ligne, groupées comme l'écran le déclare.

    Le reste — ce que le catalogue ne nomme pas — est renvoyé dans un groupe
    « Autres champs ». On ne masque rien : un écran ERP qui cache une colonne
    oblige à rouvrir RVGI, et le bouton n'a plus d'intérêt.

    `exclure` : colonnes déjà montrées ailleurs — typiquement celles de l'entête
    d'une pièce, affichées dans leur propre section. Les répéter dans le détail
    de la ligne ferait croire à deux informations là où il n'y en a qu'une.

    `entete` : la pièce, quand il y en a une. Un champ que la ligne porte à
    l'identique de son entête — la date de livraison, le mode de règlement —
    n'est pas répété. Mais s'il DIFFÈRE, il reste : une échéance propre à une
    ligne est une information, et la masquer serait mentir.
    """
    _ref(ec["cle_ligne"])
    depart = _from(ec)
    with get_erp_db() as conn:
        row = conn.execute(
            "SELECT * FROM %s WHERE %s = ?" % (depart, ec["cle_ligne"]), [ident]
        ).fetchone()
        if row is None:
            return None
        brut = dict(row)
        # `SELECT *` sur une jointure rend deux colonnes du même nom, et la
        # dernière gagne : l'entête écrasait silencieusement la valeur de la
        # ligne. On relit donc la ligne seule, et c'est ELLE qui fait foi.
        _ident(ec["table"])
        col_cle = _ident(ec["cle_ligne"].split(".")[-1])
        propre = conn.execute(
            'SELECT * FROM "%s" WHERE "%s" = ?' % (ec["table"], col_cle), [ident]
        ).fetchone()
        if propre is not None:
            brut.update(dict(propre))

    exclure = set(exclure or ())
    for court, valeur in (entete or {}).items():
        if court in brut and _identiques(brut[court], valeur):
            exclure.add(court)
    libelles, types = _libelles_et_types(ec)
    composites, absorbees = _composites(ec)

    def champ(court):
        """Un champ prêt à afficher — ou le composite qu'il ouvre."""
        if court in composites:
            defn = composites[court]
            return {"nom": defn["nom"], "label": defn["label"], "type": defn["type"],
                    "valeur": _valeur_composite(defn, brut)}
        if court in absorbees:
            return None          # part déjà rendue par son composite
        return {"nom": court, "label": libelles.get(court, court),
                "type": types.get(court, "texte"),
                "valeur": nettoyer(brut[court], types.get(court))}

    groupes = []
    vus = set()
    for g in ec.get("detail", []):
        champs = []
        for court in g["champs"]:
            if court not in brut or court in exclure or court in vus:
                continue
            vus.add(court)
            c = champ(court)
            if c is None:
                continue
            if court in composites:
                vus.update(composites[court]["parts"])
            champs.append(c)
        if champs:
            groupes.append({"titre": g["titre"], "champs": champs})

    autres = []
    for court in brut:
        if court in vus or court in exclure or court in ("corbeille", "salm", "bloq"):
            continue
        vus.add(court)
        c = champ(court)
        if c is None:
            continue
        if court in composites:
            vus.update(composites[court]["parts"])
        autres.append(c)
    if autres:
        groupes.append({"titre": "Autres champs", "champs": autres, "replie": True})

    return {"id": ident, "groupes": groupes}


# ── Recherche globale ────────────────────────────────────────────────────────

# Une recherche qui interroge vingt-sept écrans doit rendre la main. On borne
# donc le temps passé : au-delà, on renvoie ce qu'on a et on le DIT, plutôt que
# de faire attendre devant un champ qui ne répond pas.
BUDGET_RECHERCHE_S = 6.0
RESULTATS_PAR_ECRAN = 5


def recherche_globale(ecrans, q, par_ecran=RESULTATS_PAR_ECRAN,
                      budget_s=BUDGET_RECHERCHE_S):
    """Cherche la même chaîne dans tous les écrans, et rend ce qui répond.

    Chaque écran déclare déjà les colonnes sur lesquelles il se cherche
    (`recherche`) : un numéro, un nom de client, une désignation, une
    référence. On réutilise cette déclaration au lieu d'en inventer une
    seconde — la recherche globale trouve exactement ce que la recherche de
    l'écran trouverait.
    """
    import time

    q = str(q or "").strip()
    if len(q) < 2:
        return {"q": q, "resultats": [], "tronque": False, "ecrans_vus": 0}

    # « 571/0122 » est une référence article telle qu'on la LIT. En base, ce
    # sont deux colonnes : la chercher en texte ne trouve rien. On la reconnaît
    # ici et on interroge les deux morceaux — sur les écrans qui déclarent la
    # colonne composée, c'est-à-dire ceux qui affichent cette référence.
    m_ref = re.match(r"^\s*([A-Za-z0-9]{1,8})\s*/\s*([A-Za-z0-9]{1,8})\s*$", q)

    debut = time.monotonic()
    resultats, vus, tronque = [], 0, False
    for ec in ecrans:
        if not ec.get("recherche"):
            continue          # un écran sans colonne cherchable ne répond pas
        if time.monotonic() - debut > budget_s:
            tronque = True
            break
        vus += 1
        try:
            extra, texte = None, q
            if m_ref:
                parts = next((c["parts"] for c in ec["colonnes"]
                              if c.get("parts") and len(c["parts"]) == 2), None)
                if parts:
                    extra = [("CAST(%s AS TEXT) = ?" % _ref(parts[0]), m_ref.group(1)),
                             ("CAST(%s AS TEXT) = ?" % _ref(parts[1]), m_ref.group(2))]
                    texte = ""
            # `par_ecran + 1` : une ligne de rab pour savoir s'il y en a plus,
            # sans payer le COUNT.
            res = lister(ec, q=texte, taille=par_ecran + 1, compter=False, extra=extra)
        except Exception:
            continue          # un écran qui casse n'emporte pas la recherche
        lignes = res["lignes"]
        if not lignes:
            continue
        encore = len(lignes) > par_ecran
        resultats.append({
            "cle": ec["cle"],
            "label": ec["label"],
            "domaine": ec["domaine"],
            "colonnes": res["colonnes"][:4],
            "lignes": lignes[:par_ecran],
            "encore": encore,
        })
    return {"q": q, "resultats": resultats, "tronque": tronque, "ecrans_vus": vus}


# ── La pièce derrière la ligne ───────────────────────────────────────────────
#
# Une commande, un marché, un BL, une facture ne sont pas des lignes : ce sont
# des documents qui en portent plusieurs. Ouvrir une ligne sans montrer la
# pièce oblige à retourner à la grille pour savoir ce qu'il y avait d'autre
# dessus — exactement le geste que cet écran est censé supprimer.

MAX_LIGNES_PIECE = 300


def piece(ec, ident):
    """L'entête de la pièce et TOUTES ses lignes, autour de la ligne ouverte.

    Renvoie None pour un écran qui n'est pas un écran de lignes de document
    (un article, un client, un mouvement de stock n'ont pas d'entête).
    """
    p = ec.get("piece")
    if not p:
        return None
    _ref(ec["cle_ligne"])
    _ref(p["col_ligne"])
    _ident(p["table"])
    _ident(p["cle"])

    with get_erp_db() as conn:
        row = conn.execute(
            "SELECT %s AS num FROM %s WHERE %s = ?" % (p["col_ligne"], _from(ec), ec["cle_ligne"]),
            [ident],
        ).fetchone()
        if row is None or row["num"] is None:
            return None
        numero = row["num"]

        entete = conn.execute(
            'SELECT * FROM "%s" WHERE CAST(%s AS TEXT) = ?' % (p["table"], p["cle"]),
            [str(numero).strip()],
        ).fetchone()
        entete = dict(entete) if entete is not None else {}

    libelles, types = _libelles_et_types(ec)
    composites, absorbees = _composites(ec)

    # Un entête RVGI porte 80 champs, dont la moitié sont des reliquats
    # techniques. On ne masque rien — mais on met en avant ceux qu'on sait
    # nommer, et on replie les autres. « Nommé » veut dire : le catalogue ou
    # le dictionnaire de libellés lui donne un nom français.
    nommes = set(libelles)

    champs, vus = [], set()
    for court, valeur in entete.items():
        if court in vus or court in ("id", "corbeille", "salm", "bloq", "dtem"):
            continue
        vus.add(court)
        if court in composites:
            defn = composites[court]
            vus.update(defn["parts"])
            champs.append({"nom": defn["nom"], "label": defn["label"],
                           "type": defn["type"], "principal": True,
                           "valeur": _valeur_composite(defn, entete)})
            continue
        if court in absorbees:
            continue
        champs.append({"nom": court, "label": libelles.get(court, court),
                       "type": types.get(court, "texte"),
                       "principal": court in nommes,
                       "valeur": nettoyer(valeur, types.get(court))})

    # Les lignes de la pièce sont rendues avec les colonnes de la grille : ce
    # que l'écran a déjà retenu comme utile, on ne le redéclare pas ailleurs.
    # Une pièce se lit de la ligne 1 à la dernière. Le tri par défaut de
    # l'écran — le plus récent d'abord — n'a aucun sens à l'intérieur d'un
    # document : il les rendrait à l'envers.
    lignes = lister(
        ec, taille=MAX_LIGNES_PIECE,
        extra=[("CAST(%s AS TEXT) = ?" % p["col_ligne"], str(numero).strip())],
        tri=p.get("tri") or "_id", sens="asc",
    )

    return {
        "numero": numero,
        "label": p.get("label") or "La pièce",
        "entete": champs,
        "colonnes_entete": sorted(entete.keys()),
        "brut_entete": entete,
        "colonnes": lignes["colonnes"],
        "lignes": lignes["lignes"],
        "total": lignes["total"],
        "tronque": lignes["total"] > len(lignes["lignes"]),
    }


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
    for rang, lien in enumerate(ec.get("liens", [])):
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
                "label": lien["label"], "ecran": lien["ecran"], "rang": rang,
                "erreur": str(e)[:200], "total": 0, "colonnes": [], "lignes": [],
                "valeurs": valeurs,
            })
            continue

        resultats.append({
            "label": lien["label"],
            "ecran": lien["ecran"],
            "rang": rang,
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
