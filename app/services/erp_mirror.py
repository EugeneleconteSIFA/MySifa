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

# Un export n'est pas une page : il ramène tout le résultat du filtre. Le
# plafond existe pour qu'un écran de 400 000 lignes exporté par distraction ne
# tienne pas le serveur — au-delà, l'app demande de resserrer le filtre plutôt
# que de rendre un fichier tronqué en silence.
TAILLE_EXPORT_MAX = 20000


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
    # Un numéro de pièce à 0 veut dire « pas de pièce » : une ligne de BL sans
    # facture porte `fac_no = 0`, ce qui n'est pas la facture numéro zéro.
    if type_col in ("prix", "id") and f == 0:
        return None
    return v


def nettoyer(valeur, type_col):
    """Traduit une valeur RVGI en valeur affichable. `None` = rien à montrer."""
    if valeur is None:
        return None
    if type_col in ("date", "datetime"):
        return _propre_date(valeur)
    if type_col in ("nombre", "qte", "prix", "montant", "pct", "id"):
        return _propre_nombre(valeur, type_col)
    if isinstance(valeur, str):
        v = valeur.strip()
        return v or None
    return valeur


# ── Filtres par colonne (en-têtes de grille) ─────────────────────────────────
# Le rail de gauche porte les filtres MÉTIER déclarés au catalogue — Position,
# Client, plage de dates. Ceci répond à l'autre besoin, celui qu'on va chercher
# dans Excel : poser une condition libre sur n'importe quelle colonne AFFICHÉE,
# avec l'opérateur qu'on veut. Les deux se combinent en ET : un filtre
# d'en-tête n'efface jamais un filtre de rail.
#
# Rien de ce qui vient du client n'entre dans le SQL. Le nom de colonne est
# résolu contre les colonnes de l'écran (donc contre le catalogue),
# l'opérateur contre la table ci-dessous, et la valeur passe en paramètre lié.

# Un numéro de pièce (`id`, `of`) est rangé avec les nombres : « supérieur à
# 9911600 » a un sens sur un carnet de commandes, et les opérateurs de motif
# lui restent ouverts plus bas — c'est « contient 2606 » qu'on tape le plus.
FAMILLE_PAR_TYPE = {
    "nombre": "nombre", "qte": "nombre", "prix": "nombre",
    "montant": "nombre", "pct": "nombre", "id": "nombre", "of": "nombre",
    "date": "date", "datetime": "date",
    "enum": "enum",
    "bool": "bool",
}

# Un nombre garde « contient » et « commence par » : sur un numéro de pièce,
# chercher « 2606 » est le geste le plus fréquent de tous.
OPS_PAR_FAMILLE = {
    "texte":  ["contient", "contient_pas", "egal", "different",
               "commence", "finit", "vide", "non_vide"],
    "nombre": ["egal", "different", "sup", "sup_egal", "inf", "inf_egal",
               "entre", "contient", "commence", "vide", "non_vide"],
    "date":   ["egal", "different", "sup", "sup_egal", "inf", "inf_egal",
               "entre", "vide", "non_vide"],
    "enum":   ["egal", "different", "vide", "non_vide"],
    "bool":   ["egal", "different"],
}

# Les libellés sont ceux de l'écran, pas ceux de SQL — et ils changent avec la
# famille : « supérieur à » sur une quantité se dit « après le » sur une date.
LABELS_OPS = {
    "contient": "Contient",
    "contient_pas": "Ne contient pas",
    "egal": "Est égal à",
    "different": "Est différent de",
    "commence": "Commence par",
    "finit": "Finit par",
    "sup": "Supérieur à",
    "sup_egal": "Supérieur ou égal à",
    "inf": "Inférieur à",
    "inf_egal": "Inférieur ou égal à",
    "entre": "Compris entre",
    "vide": "Est vide",
    "non_vide": "N’est pas vide",
}

LABELS_OPS_DATE = {
    "egal": "Le",
    "different": "Sauf le",
    "sup": "Après le",
    "sup_egal": "À partir du",
    "inf": "Avant le",
    "inf_egal": "Jusqu’au",
    "entre": "Entre le",
    "vide": "Non renseignée",
    "non_vide": "Renseignée",
}

LABELS_OPS_LISTE = {
    "egal": "Est",
    "different": "N’est pas",
    "vide": "Est vide",
    "non_vide": "N’est pas vide",
}

# Combien de valeurs l'opérateur attend. Ce qui n'est pas ici en attend une.
NB_VALEURS = {"vide": 0, "non_vide": 0, "entre": 2}


def famille_de(type_col):
    return FAMILLE_PAR_TYPE.get(str(type_col or "texte"), "texte")


def operateurs_disponibles():
    """Table servie au client : quels opérateurs pour quelle famille, et
    comment les nommer. Une seule source de vérité — la page n'en redéfinit
    aucun de son côté."""
    out = {}
    for fam, ops in OPS_PAR_FAMILLE.items():
        if fam == "date":
            libs = dict(LABELS_OPS, **LABELS_OPS_DATE)
        elif fam in ("enum", "bool"):
            libs = dict(LABELS_OPS, **LABELS_OPS_LISTE)
        else:
            libs = LABELS_OPS
        out[fam] = [
            {"cle": o, "label": libs[o], "valeurs": NB_VALEURS.get(o, 1)}
            for o in ops
        ]
    return {"familles": FAMILLE_PAR_TYPE, "operateurs": out}


def _expr_texte(col):
    """La colonne telle qu'elle S'AFFICHE, en texte.

    Sur une colonne composite (`code1`/`code2` montrés « 890/0112 »), filtrer
    sur le premier morceau seulement ferait mentir la grille : on reconstruit
    la valeur assemblée, avec le même séparateur.
    """
    if col.get("parts"):
        bouts = ["COALESCE(CAST(%s AS TEXT),'')" % _ref(p) for p in col["parts"]]
        joint = str(col.get("joint", "/")).replace("'", "''")
        return "(" + (" || '%s' || " % joint).join(bouts) + ")"
    return "CAST(%s AS TEXT)" % _ref(col["c"])


def _ref_brute(col):
    """La colonne SQL elle-même, pour ce qui se compare en nombre ou en date."""
    return _ref(col["c"]) if col.get("c") else _ref(col["parts"][0])


def _echapper_like(v):
    """Un « % » tapé par l'utilisateur est un pourcentage, pas un joker."""
    return str(v).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _nombre(v):
    """La virgule décimale française est acceptée : on tape « 1 250,50 »."""
    s = str(v)
    for c in (" ", " ", "\xa0"):
        s = s.replace(c, "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        raise ValueError("« %s » n’est pas un nombre." % v)


def _condition_vide(col, fam, brut, txt):
    """« Vide » au sens de l'écran, sentinelles RVGI comprises.

    RVGI n'a pas de NULL : une date non renseignée vaut 30/11/1999, un prix non
    renseigné vaut 0, « pas de maximum » vaut 99999999999.99. La grille les
    affiche déjà comme « rien » (`nettoyer`) ; le filtre doit dire la même
    chose, sinon « est vide » ne ramènerait aucune des lignes qui montrent un
    tiret.
    """
    morceaux = ["%s IS NULL" % brut, "TRIM(%s) = ''" % txt]
    if fam == "date":
        morceaux.append("substr(%s,1,10) IN ('%s','%s')" % (txt, DATE_VIDE, DATE_INFINIE))
    if fam == "nombre":
        morceaux.append("ABS(CAST(%s AS REAL)) >= %r" % (brut, MAX_SENTINELLE))
        if col.get("type") in ("prix", "id"):
            morceaux.append("CAST(%s AS REAL) = 0" % brut)
    return "(" + " OR ".join(morceaux) + ")"


_CMP = {"egal": "=", "different": "<>", "sup": ">", "sup_egal": ">=",
        "inf": "<", "inf_egal": "<="}


def condition_colonne(col, op, valeurs):
    """(fragment SQL, paramètres) pour un filtre d'en-tête.

    « Est différent de » et « ne contient pas » ramènent AUSSI les cellules
    vides : une case sans valeur ne contient pas la chaîne cherchée, et
    l'écarter serait un piège — SQL, lui, laisse les NULL de côté tout seul.
    """
    fam = famille_de(col.get("type"))
    if op not in OPS_PAR_FAMILLE.get(fam, OPS_PAR_FAMILLE["texte"]):
        raise ValueError("Opérateur « %s » inapplicable à cette colonne." % op)
    txt = _expr_texte(col)
    brut = _ref_brute(col)

    if op in ("vide", "non_vide"):
        vide = _condition_vide(col, fam, brut, txt)
        return (vide if op == "vide" else "NOT %s" % vide), []

    if fam == "date":
        # Les dates du miroir portent une heure : toute comparaison au jour se
        # fait sur les dix premiers caractères, sinon « le 26/08 » ne trouve
        # jamais « 2026-08-26 09:12 ».
        cible = "substr(%s,1,10)" % txt
        if op == "entre":
            return "(%s BETWEEN ? AND ?)" % cible, [valeurs[0], valeurs[1]]
        if op == "different":
            return "(%s IS NULL OR %s <> ?)" % (cible, cible), [valeurs[0]]
        return "(%s %s ?)" % (cible, _CMP[op]), [valeurs[0]]

    if fam == "nombre" and op not in ("contient", "commence"):
        num = "CAST(%s AS REAL)" % brut
        if op == "entre":
            a, b = _nombre(valeurs[0]), _nombre(valeurs[1])
            if a > b:
                a, b = b, a
            return "(%s BETWEEN ? AND ?)" % num, [a, b]
        if op == "different":
            return "(%s IS NULL OR %s <> ?)" % (brut, num), [_nombre(valeurs[0])]
        return "(%s %s ?)" % (num, _CMP[op]), [_nombre(valeurs[0])]

    # Texte, énumération, booléen — et les recherches de motif sur un nombre.
    # `UPPER` des deux côtés : chercher « lidl » doit trouver « LIDL ».
    cible = "UPPER(%s)" % txt
    v = str(valeurs[0])
    motif = _echapper_like(v).upper()
    if op == "contient":
        return "(%s LIKE ? ESCAPE '\\')" % cible, ["%" + motif + "%"]
    if op == "contient_pas":
        return ("(%s IS NULL OR %s NOT LIKE ? ESCAPE '\\')" % (txt, cible),
                ["%" + motif + "%"])
    if op == "commence":
        return "(%s LIKE ? ESCAPE '\\')" % cible, [motif + "%"]
    if op == "finit":
        return "(%s LIKE ? ESCAPE '\\')" % cible, ["%" + motif]
    if op == "different":
        return "(%s IS NULL OR %s <> ?)" % (txt, cible), [v.upper()]
    return "(%s = ?)" % cible, [v.upper()]


def conditions_colonnes(colonnes, filtres_col):
    """Traduit les `c_<colonne>=<operateur>:<valeur>` en conditions.

    Un filtre incomplet (opérateur posé, valeur pas encore tapée) est ignoré :
    la grille ne doit pas se vider pendant qu'on remplit le champ.
    """
    par_nom = {c["nom"]: c for c in colonnes}
    sortie = []
    for nom, expr in (filtres_col or {}).items():
        col = par_nom.get(nom)
        if not col:
            continue          # colonne inconnue de cet écran : ignorée sans bruit
        if col.get("sans_filtre"):
            continue          # colonne qui refuse le filtre d'en-tête, cf. `_c`
        op, _, reste = str(expr or "").partition(":")
        op = op.strip()
        if not op:
            continue
        attendu = NB_VALEURS.get(op, 1)
        vals = [x.strip() for x in str(reste).split("|")] if attendu else []
        vals = vals[:attendu]
        if len(vals) < attendu or any(v == "" for v in vals):
            continue
        sortie.append(condition_colonne(col, op, vals))
    return sortie


# ── Moteur de liste générique ────────────────────────────────────────────────

def _from(ec):
    """Clause FROM + jointures de l'écran, validées.

    Une jointure marquée `obligatoire` sort en `JOIN`, pas en `LEFT JOIN`. Ce
    n'est pas une optimisation, c'est une règle de lecture : sur un écran de
    lignes de document, une ligne dont l'entête a disparu de l'ERP n'est pas un
    document. RVGI lit la pièce puis ses lignes — il ne peut pas montrer une
    ligne sans pièce, et nous non plus.

    Le cas est réel et massif : au 28/08/2026, 744 des 880 lignes de commande
    « En cours » du miroir n'avaient plus d'entête, échouées là depuis 2019, et
    neuf d'entre elles seulement avaient jamais produit un BL. En `LEFT JOIN`,
    l'écran affichait 920 commandes à traiter là où RVGI en montrait 178.
    """
    _ident(ec["table"])
    depart = '"%s" %s' % (ec["table"], _ident(ec["alias"]))
    for j in ec.get("jointures", []):
        _ident(j["table"])
        _ident(j["alias"])
        _ref(j["gauche"])
        _ref(j["droite"])
        # `et` : les conditions supplementaires d'une jointure a plusieurs
        # colonnes. Une ligne de reception ne se rapproche pas de sa ligne de
        # commande sur le seul numero de piece — il faut aussi le numero de
        # ligne, sinon chaque reception ramene TOUTES les lignes de sa commande
        # et l'ecran multiplie ses lignes sans le dire.
        conditions = ["%s = %s" % (j["gauche"], j["droite"])]
        for gauche, droite in j.get("et", []):
            _ref(gauche)
            _ref(droite)
            conditions.append("%s = %s" % (gauche, droite))
        depart += ' %s "%s" %s ON %s' % (
            "JOIN" if j.get("obligatoire") else "LEFT JOIN",
            j["table"], j["alias"], " AND ".join(conditions)
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


def _ou_et_params(ec, q, filtres, extra, ratt, filtre_ratt, filtres_col=None):
    """Le WHERE d'un écran, construit une seule fois pour les deux vues.

    La vue par ligne et la vue par pièce doivent filtrer exactement pareil :
    deux constructions parallèles finiraient par diverger, et « 845 lignes »
    ne correspondrait plus à « 312 commandes ». Une seule fonction, donc, et
    les deux vues l'appellent.

    Aucune valeur de l'utilisateur n'entre dans le SQL : les références de
    colonne viennent du catalogue et passent par `_ref`, tout le reste part
    en paramètre lié.

    `filtres_col` : les filtres d'en-tête, `{nom_de_colonne: "operateur:valeur"}`.
    Ils s'ajoutent en ET aux filtres du rail, jamais à leur place. Ils sont
    résolus contre les colonnes de l'ÉCRAN, donc contre les lignes — y compris
    dans la vue par pièce, ou ils filtrent avant le regroupement. C'est la
    seule lecture qui vaille dans les deux vues : « les commandes qui ont une
    ligne comme ça ». Filtrer après agrégation demanderait un HAVING, et un
    filtre posé sur « Lignes » (COUNT(*)) n'aurait pas le meme sens d'une vue
    a l'autre.
    """
    colonnes = ec["colonnes"]
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
        if f.get("type") == "enum" and "|" in valeur:
            # Un filtre d'énumération peut viser plusieurs codes à la fois :
            # « non soldée » vaut 0 ou 1. Les codes viennent du catalogue via
            # `choix`, jamais du client — mais ils transitent par lui, donc on
            # les recolle ici en paramètres liés, un par code.
            codes = [v for v in valeur.split("|") if v != ""]
            if not codes:
                continue
            conditions.append("CAST(%s AS TEXT) IN (%s)" % (
                f["col"], ",".join("?" for _ in codes)))
            params.extend(codes)
        elif f.get("type") == "date_min":
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

    # Filtres d'en-tête : une condition libre par colonne AFFICHÉE, en ET avec
    # tout le reste. La colonne est résolue contre `colonnes`, donc contre le
    # catalogue — un nom inventé par le client ne désigne rien.
    for fragment, valeurs in conditions_colonnes(colonnes, filtres_col):
        conditions.append(fragment)
        params.extend(valeurs)

    ou = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return ou, params


def lister(ec, q="", filtres=None, tri=None, sens="asc", page=1,
           taille=TAILLE_PAGE_DEFAUT, extra=None, compter=True, rattachement=False,
           filtre_ratt="", filtres_col=None, plafond=None):
    """Liste paginée d'un écran. Renvoie colonnes, lignes, total.

    `extra` : conditions supplémentaires, sous forme de couples
    (fragment SQL déjà validé, valeur). Sert aux pièces liées, qui joignent
    sur des colonnes que l'utilisateur ne filtre pas lui-même.

    `compter=False` : on renvoie `total = None` au lieu de compter. Le COUNT
    est un balayage complet de la table ; sur une recherche qui interroge les
    vingt-sept écrans d'un coup, il double le travail pour un chiffre que
    personne ne lit.

    `filtres_col` : les filtres d'en-tête. Ils partent dans le WHERE commun aux
    deux vues — voir `_ou_et_params`.

    `plafond` : plafond de taille de page. Il vaut `TAILLE_PAGE_MAX` pour une
    grille — au-delà elle devient illisible avant d'être lente — et
    `TAILLE_EXPORT_MAX` pour un export, qui n'a pas à s'arrêter à un écran.
    """
    filtres = filtres or {}
    taille = max(1, min(int(taille or TAILLE_PAGE_DEFAUT), int(plafond or TAILLE_PAGE_MAX)))
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

    ou, params = _ou_et_params(ec, q, filtres, extra, ratt, filtre_ratt, filtres_col)
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
                          taille=taille, extra=extra, compter=compter,
                          filtres_col=filtres_col, plafond=plafond)
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


def lister_groupe(ec, groupe, q="", filtres=None, tri=None, sens="asc", page=1,
                  taille=TAILLE_PAGE_DEFAUT, extra=None, compter=True,
                  filtre_ratt="", filtres_col=None, plafond=None):
    """La même liste, mais une ligne par pièce.

    Mêmes filtres, même recherche, même écran : seule la maille change. On
    regroupe sur le numéro de pièce et on agrège ce qui s'agrège — le
    catalogue a déjà décidé quoi, dans `colonnes_groupees`.

    Le rattachement MySifa n'est pas proposé ici : il se raisonne ligne par
    ligne (une commande peut être à moitié rattachée), et une pastille unique
    au niveau de la pièce dirait quelque chose de faux. Le filtre reste donc
    inopérant dans cette vue, et l'écran le dit.

    `_id` de chaque ligne vaut `MIN(cle_ligne)` : cliquer une pièce ouvre la
    modale, qui montre de toute façon la pièce entière.
    """
    filtres = filtres or {}
    taille = max(1, min(int(taille or TAILLE_PAGE_DEFAUT), int(plafond or TAILLE_PAGE_MAX)))
    page = max(1, int(page or 1))

    colonnes = groupe["colonnes"]
    cle = groupe["cle"]
    _ref(cle)

    select = []
    for c in colonnes:
        _ident(c["nom"])
        select.append('%s AS "%s"' % (c["expr"], c["nom"]))
    _ref(ec["cle_ligne"])
    select.append('MIN(%s) AS "_id"' % ec["cle_ligne"])

    ou, params = _ou_et_params(ec, q, filtres, extra, None, "", filtres_col)
    depart = _from(ec)

    # Tri : sur une colonne de la vue, donc sur son expression agrégée. Un
    # nom inconnu retombe sur la clé de pièce, jamais sur du SQL libre.
    par_nom = {c["nom"]: c for c in colonnes}
    if tri and tri in par_nom:
        col_tri = par_nom[tri]["expr"]
        tri_retenu = tri
    else:
        col_tri = cle
        tri_retenu = None
        sens = "desc"
    sens_sql = "DESC" if str(sens).lower() == "desc" else "ASC"

    sql = ("SELECT %s FROM %s%s GROUP BY %s ORDER BY %s %s LIMIT ? OFFSET ?"
           % (", ".join(select), depart, ou, cle, col_tri, sens_sql))

    with get_erp_db() as conn:
        total = None
        if compter:
            total = conn.execute(
                "SELECT COUNT(DISTINCT %s) FROM %s%s" % (cle, depart, ou), params
            ).fetchone()[0]
        brut = conn.execute(sql, params + [taille, (page - 1) * taille]).fetchall()

    lignes = []
    for r in brut:
        d = {"_id": r["_id"]}
        for c in colonnes:
            d[c["nom"]] = nettoyer(r[c["nom"]], c.get("type"))
        lignes.append(d)

    return {
        "vue": "piece",
        "colonnes": [{k: v for k, v in c.items() if k != "expr"} for c in colonnes],
        "lignes": lignes,
        "total": total,
        "page": page,
        "taille": taille,
        "tri": tri_retenu,
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
    cols, rangs = _etoffer_lignes_piece(ec, p, numero, lignes, libelles, types, absorbees)

    return {
        "numero": numero,
        "label": p.get("label") or "La pièce",
        "entete": champs,
        "colonnes_entete": sorted(entete.keys()),
        "brut_entete": entete,
        "colonnes": cols,
        "lignes": rangs,
        "total": lignes["total"],
        "tronque": lignes["total"] > len(lignes["lignes"]),
    }


def _etoffer_lignes_piece(ec, p, numero, lignes, libelles, types, absorbees):
    """Toutes les colonnes de la ligne, pas seulement celles de la grille.

    Pourquoi
    --------
    Le détail d'une ligne était rendu deux fois : une fois dans le tableau des
    lignes du document, une fois en blocs de champs juste en dessous. Le
    lecteur devait faire la correspondance de tête entre « ligne 3 » du tableau
    et le bloc du bas — et les deux se contredisaient à l'œil dès qu'on
    changeait de ligne.

    Le tableau porte donc maintenant TOUT ce que la ligne sait, et le bloc du
    bas disparaît. Un document se lit alors ligne par ligne, ce qui est la
    seule façon de comparer deux lignes entre elles.

    Ce qu'on écarte, et pourquoi
    ----------------------------
    Une colonne vide sur TOUTES les lignes du document n'apprend rien et
    pousserait les utiles hors de l'écran. Ce n'est pas masquer : il n'y a rien
    à montrer. Les colonnes techniques de RVGI (`corbeille`, `salm`, `bloq`,
    `dtem`) sortent aussi — elles ne parlent de la ligne à personne.

    Les colonnes nommées passent devant les autres : c'est ce qui rend le
    défilement horizontal supportable.
    """
    base = list(lignes["colonnes"])
    rangs = lignes["lignes"]
    if not rangs:
        return base, rangs

    deja = {c["nom"] for c in base}
    # On relit par les identifiants que `lister()` vient de rendre, pas par le
    # numéro de pièce : la clé primaire est indexée, `CAST(numero AS TEXT)` ne
    # l'est pas et forçait un balayage des 34 000 lignes de `cde_ligne` — 350 ms
    # au lieu de 30 pour ouvrir une fiche.
    pk = ec["cle_ligne"].split(".")[-1]
    _ident(pk)
    ids = [r.get("_id") for r in rangs if r.get("_id") is not None]
    if not ids:
        return base, rangs
    sql = 'SELECT * FROM "%s" WHERE "%s" IN (%s)' % (
        ec["table"], pk, ",".join("?" * len(ids)))
    try:
        with get_erp_db() as conn:
            brutes = {r[pk]: dict(r) for r in conn.execute(sql, ids)}
    except sqlite3.Error:
        return base, rangs      # une lecture ratée ne doit pas vider le tableau
    if not brutes:
        return base, rangs

    nommes, anonymes, valuees = [], [], set()
    ordre = list(brutes[next(iter(brutes))].keys())
    for court in ordre:
        if court in deja or court in absorbees:
            continue
        if court in ("id", "corbeille", "salm", "bloq", "dtem"):
            continue
        (nommes if court in libelles else anonymes).append(court)

    for r in rangs:
        b = brutes.get(r.get("_id"))
        if not b:
            continue
        for court in nommes + anonymes:
            v = nettoyer(b.get(court), types.get(court))
            if v is None or v == "":
                continue
            r[court] = v
            valuees.add(court)

    for court in nommes + anonymes:
        if court not in valuees:
            continue
        base.append({"nom": court,
                     "label": libelles.get(court, court),
                     "type": types.get(court, "texte")})
    return base, rangs


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


_TYPES_COLONNES = {}


def _type_colonne(conn, table, col):
    """Le type déclaré d'une colonne du miroir, mis en cache.

    Le miroir est reconstruit à chaque synchro mais son SCHÉMA ne change pas
    d'une reconstruction à l'autre — il est dérivé de HFSQL. Un cache pour la
    durée du processus est donc sans risque, et évite un PRAGMA par lien.
    """
    if table not in _TYPES_COLONNES:
        _TYPES_COLONNES[table] = {
            r[1]: (r[2] or "").upper()
            for r in conn.execute('PRAGMA table_info("%s")' % table)
        }
    return _TYPES_COLONNES[table].get(col, "")


def _table_de_ref(ec, ref):
    """De « e.numclt » à la table que l'alias `e` désigne dans cet écran."""
    alias = ref.split(".")[0] if "." in ref else ec["alias"]
    if alias == ec["alias"]:
        return ec["table"]
    for j in ec.get("jointures", []):
        if j["alias"] == alias:
            return j["table"]
    return None


def _condition_lien(ec, ref, valeur):
    """La comparaison qui retrouve les pièces liées, sans casser les index.

    Le miroir porte 361 index à colonne unique, et ce sont eux qui font la
    différence entre 40 ms et 400 ms sur une table de 35 000 lignes. Or
    `CAST(colonne AS TEXT) = ?` les rend tous inutilisables : SQLite ne peut
    pas chercher dans un index une valeur qu'il doit d'abord transformer.

    On compare donc dans le type de la colonne quand c'est possible — un
    entier avec un entier — et on ne retombe sur le CAST que pour les colonnes
    texte, où il ne coûte rien. C'est le même résultat, en dix fois moins de
    temps.
    """
    with get_erp_db() as conn:
        typ = _type_colonne(conn, _table_de_ref(ec, ref) or ec["table"], ref.split(".")[-1])
    brut = str(valeur).strip()
    if typ.startswith(("INT", "REAL", "NUM", "FLOA", "DOUB")):
        try:
            return ("%s = ?" % ref, int(brut) if typ.startswith("INT") else float(brut))
        except (TypeError, ValueError):
            pass
    if typ.startswith(("TEXT", "CHAR", "CLOB", "VARCHAR")):
        # Affinité TEXT : ce qui est en base y est déjà sous forme de texte,
        # le CAST ne convertirait rien et coûterait l'index.
        return ("%s = ?" % ref, brut)
    # Type inconnu ou colonne sans type déclaré : le CAST reste le filet.
    return ("CAST(%s AS TEXT) = ?" % ref, brut)


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
            # `numcde` peut être INTEGER d'un côté et TEXT de l'autre : on
            # compare dans le type de la colonne CIBLE, pour rester sur son
            # index (voir `_condition_lien`).
            extra.append(_condition_lien(cible, ref_cible, v))
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
