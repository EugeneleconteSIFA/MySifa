"""Tableaux de bord de l'app ERP — lecture seule.

Deux écrans d'accueil montés sur le miroir RVGI : l'ADV suit le fil
commande → dossier de production → bon de livraison, la direction suit
l'argent — ce qui est rentré, ce qui est facturable, ce qui est facturé.

Quatre règles, dans cet ordre d'importance :

1. **Lecture seule.** Tout passe par `erp_mirror.get_erp_db()`, ouvert en
   `mode=ro`. La base de MySifa, quand elle est attachée, l'est aussi. RVGI
   est la source, MySifa lit.
2. **Aucune interpolation d'entrée utilisateur.** Ces écrans ne prennent
   aucun paramètre libre : les seules valeurs liées sont des dates calculées
   ici même.
3. **Un chiffre absent ne fait pas tomber l'écran.** Le miroir peut manquer
   une table (export partiel) ou une colonne (version de RVGI, champ
   renommé). Chaque bloc est calculé isolément : ce qui échoue vaut `None`,
   l'écran affiche « — » et dit pourquoi, au lieu de rendre un 500.
4. **Chaque chiffre porte sa formule.** `FORMULES` accompagne la réponse et
   s'affiche sous la tuile. Un total qu'on ne peut pas expliquer, personne
   ne le croit — et c'est ce qui tue un tableau de bord.

Ce que ce module ne fait PAS : les contrôles côté MySifa (OF, fiches
techniques, mappings, scans). Ils ont déjà leurs routes et leurs écrans ;
le tableau de bord ADV les appelle depuis le navigateur pour que le compteur
et l'écran qu'il ouvre ne puissent jamais diverger.
"""

import sqlite3
from datetime import date, timedelta

from app.services import erp_mirror as miroir

# Les lignes « mortes » de RVGI sont déjà écartées à l'export
# (`export_rvgi_csv.ps1` pose `WHERE corbeille = 0`) : le miroir ne contient
# que du vivant, inutile de refiltrer ici.

# Origine d'une ligne de commande (ENUMS["origine"] du catalogue).
ORIG_FABRICATION = 1
ORIG_STOCK = 2
ORIG_SOUS_TRAITANCE = 3

# Position d'une ligne (ENUMS["position"]) : 2 = soldée.
POS_SOLDEE = 2

MAX_LIGNES_LISTE = 12

# Une date réelle, par opposition aux sentinelles de RVGI (`30/11/1999` pour
# « non renseignée », `31/12/2099` pour « pas de fin »). Comparer sans ce
# garde-fou fait passer toute ligne sans date promise pour une ligne en
# retard — mesuré sur le jeu de test : 289 faux retards sur 384 lignes.
def _date_reelle(col):
    return "%s IS NOT NULL AND %s > '2000-01-01' AND %s < '2090-01-01'" % (col, col, col)

FORMULES = {
    "carnet": "cde_ligne : qtep > 0 et position ≠ soldée",
    "retard": "carnet dont la date d'expédition est passée "
              "(les lignes sans date promise n'en sont pas)",
    "semaine": "carnet dont amje tombe dans les 7 prochains jours",
    "a_facturer": "liv_ligne : qte livrée > qte facturée",
    "sans_dossier": "carnet en fabrication sans rattachement à un dossier MySifa",
    "hors_prod": "carnet dont l'origine est stock ou sous-traitance",
    "rentre": "Σ net (montant net de ligne) des lignes de commande créées "
              "ce jour-là, par cde_entete.amjc",
    "facture": "Σ net (montant net de ligne) des lignes de facture, "
               "par mois de vte_entete.amjf",
    "facturable": "Σ (qte − qtefac) × pun de la commande, sur les BL non soldés",
    "encours": "Σ net du carnet restant à traiter",
}


# ── Outillage défensif ───────────────────────────────────────────────────────

def _tables(conn):
    try:
        return miroir.tables_presentes(conn)
    except sqlite3.Error:
        return set()


def _colonnes(conn, table):
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


class _Schema:
    """Ce que le miroir contient vraiment, une seule lecture pour tout l'écran."""

    def __init__(self, conn):
        self.conn = conn
        self.tables = _tables(conn)
        self._cols = {}

    def cols(self, table):
        if table not in self._cols:
            self._cols[table] = _colonnes(self.conn, table) if table in self.tables else set()
        return self._cols[table]

    def a(self, table, *colonnes):
        """La table existe et porte toutes ces colonnes ?"""
        if table not in self.tables:
            return False
        dispo = self.cols(table)
        return all(c in dispo for c in colonnes)

    def manque(self, table, *colonnes):
        if table not in self.tables:
            return "table %s absente du miroir" % table
        absentes = [c for c in colonnes if c not in self.cols(table)]
        if absentes:
            return "colonnes absentes sur %s : %s" % (table, ", ".join(absentes))
        return None


def _un(conn, sql, params=()):
    """Première colonne de la première ligne, ou None si la requête casse."""
    try:
        r = conn.execute(sql, params).fetchone()
    except sqlite3.Error:
        return None
    if not r:
        return None
    return r[0]


def _lignes(conn, sql, params=()):
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error:
        return []


def _nombre(v):
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _entier(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


# ── Dates ────────────────────────────────────────────────────────────────────

def _bornes(aujourdhui=None):
    j = aujourdhui or date.today()
    veille = j - timedelta(days=1)
    debut_mois = j.replace(day=1)
    # Même mois, l'an dernier — pour comparer à périmètre égal.
    debut_mois_n1 = debut_mois.replace(year=debut_mois.year - 1)
    fin_mois_n1 = (debut_mois_n1 + timedelta(days=32)).replace(day=1)
    return {
        "aujourdhui": j.isoformat(),
        "veille": veille.isoformat(),
        "debut_mois": debut_mois.isoformat(),
        "fin_semaine": (j + timedelta(days=7)).isoformat(),
        "il_y_a_30j": (j - timedelta(days=29)).isoformat(),
        "debut_mois_n1": debut_mois_n1.isoformat(),
        "fin_mois_n1": fin_mois_n1.isoformat(),
        "debut_serie": (debut_mois.replace(day=1) - timedelta(days=340)).replace(day=1).isoformat(),
    }


_MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
               "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _libelle_mois(cle):
    """« 2026-08 » → « août »."""
    try:
        an, mois = cle.split("-")
        return _MOIS_COURT[int(mois) - 1]
    except (ValueError, IndexError):
        return cle


# ── Tableau de bord ADV ──────────────────────────────────────────────────────

def adv():
    """Le fil commande → dossier → BL, côté RVGI.

    Ce que ce bloc ne contient pas : les compteurs d'OF, de fiches techniques
    et de scans. Ils vivent dans MySifa et le navigateur va les chercher à
    leur propre route, celle-là même que le lien de la tuile ouvre.
    """
    b = _bornes()
    sortie = {
        "present": miroir.miroir_present(),
        "bornes": b,
        "formules": FORMULES,
        "indispo": [],
    }
    if not sortie["present"]:
        return sortie

    with miroir.get_erp_db(avec_mysifa=True) as conn:
        sch = _Schema(conn)
        sortie["mysifa_attachee"] = miroir.mysifa_attachee(conn)

        # ── Le carnet ────────────────────────────────────────────────────
        manque = sch.manque("cde_ligne", "qtep", "lpos", "amje", "numero", "ligne")
        if manque:
            sortie["indispo"].append("Carnet : " + manque)
            sortie["carnet"] = None
        else:
            ouvert = "l.qtep > 0 AND COALESCE(l.lpos, 0) <> %d" % POS_SOLDEE
            sortie["carnet"] = {
                "lignes": _entier(_un(conn, "SELECT COUNT(*) FROM cde_ligne l WHERE " + ouvert)),
                "retard": _entier(_un(
                    conn,
                    "SELECT COUNT(*) FROM cde_ligne l WHERE " + ouvert
                    + " AND " + _date_reelle("l.amje") + " AND l.amje < ?", (b["aujourdhui"],))),
                "semaine": _entier(_un(
                    conn,
                    "SELECT COUNT(*) FROM cde_ligne l WHERE " + ouvert
                    + " AND " + _date_reelle("l.amje")
                    + " AND l.amje >= ? AND l.amje < ?", (b["aujourdhui"], b["fin_semaine"]))),
            }

            # Les lignes en retard, avec leur client — la liste d'action.
            joint_clt = ("LEFT JOIN cde_entete e ON e.numero = l.numero"
                         if sch.a("cde_entete", "numero", "rs") else "")
            champ_clt = "e.rs" if joint_clt else "''"
            sortie["retards"] = _lignes(conn, """
                SELECT l.id AS id, l.numero AS numero, l.ligne AS ligne,
                       %s AS client, l.des1 AS designation,
                       l.qtep AS reste, l.amje AS expedition, l.orig AS origine
                  FROM cde_ligne l %s
                 WHERE %s AND %s AND l.amje < ?
              ORDER BY l.amje ASC
                 LIMIT %d
            """ % (champ_clt, joint_clt, ouvert, _date_reelle("l.amje"), MAX_LIGNES_LISTE),
                (b["aujourdhui"],))

            # Origine : seules les lignes en fabrication attendent un dossier.
            if "orig" in sch.cols("cde_ligne"):
                sortie["hors_prod"] = {
                    "stock": _entier(_un(
                        conn, "SELECT COUNT(*) FROM cde_ligne l WHERE " + ouvert
                        + " AND l.orig = ?", (ORIG_STOCK,))),
                    "sous_traitance": _entier(_un(
                        conn, "SELECT COUNT(*) FROM cde_ligne l WHERE " + ouvert
                        + " AND l.orig = ?", (ORIG_SOUS_TRAITANCE,))),
                }
            else:
                sortie["hors_prod"] = None
                sortie["indispo"].append("Origine des lignes : colonne orig absente")

        # ── Livré, pas encore facturé ────────────────────────────────────
        manque = sch.manque("liv_ligne", "qte", "qtefac", "numero", "amje")
        if manque:
            sortie["indispo"].append("À facturer : " + manque)
            sortie["a_facturer"] = None
        else:
            reste = "l.qte > COALESCE(l.qtefac, 0)"
            joint_bl = ("LEFT JOIN liv_entete e ON e.numero = l.numero"
                        if sch.a("liv_entete", "numero", "lrs") else "")
            champ_bl = "e.lrs" if joint_bl else "''"
            sortie["a_facturer"] = {
                "bl": _entier(_un(conn, "SELECT COUNT(DISTINCT l.numero) FROM liv_ligne l WHERE " + reste)),
                "lignes": _entier(_un(conn, "SELECT COUNT(*) FROM liv_ligne l WHERE " + reste)),
            }
            sortie["a_facturer_items"] = _lignes(conn, """
                SELECT MIN(l.id) AS id, l.numero AS bl, MIN(l.amje) AS expedition, %s AS client,
                       COUNT(*) AS lignes, SUM(l.qte - COALESCE(l.qtefac,0)) AS reste
                  FROM liv_ligne l %s
                 WHERE %s
              GROUP BY l.numero
              ORDER BY MIN(l.amje) ASC
                 LIMIT %d
            """ % (champ_bl, joint_bl, reste, MAX_LIGNES_LISTE))

        # ── Le rattachement dossier ↔ commande, côté MySifa ──────────────
        sortie["dossiers"] = _etats_dossiers(conn, sortie)
        sortie["sans_dossier"] = _sans_dossier(conn, sch, sortie)

    return sortie


def _etats_dossiers(conn, sortie):
    """Répartition des dossiers de production par état vis-à-vis de RVGI.

    `planning_entries.rvgi_etat` est écrit par `rvgi_rattachement.recalculer_etat`
    et vaut : lie · partiel · a_verifier · a_rattacher · hors_commande.
    """
    if not miroir.mysifa_attachee(conn):
        sortie["indispo"].append("États de rattachement : base MySifa non attachée")
        return None
    rows = _lignes(conn, """
        SELECT COALESCE(NULLIF(TRIM(COALESCE(rvgi_etat, '')), ''), 'a_rattacher') AS etat,
               COUNT(*) AS n
          FROM mysifa.planning_entries
         WHERE COALESCE(statut, '') <> 'termine'
      GROUP BY etat
    """)
    if not rows:
        return None
    return {r["etat"]: _entier(r["n"]) for r in rows}


def _sans_dossier(conn, sch, sortie):
    """Lignes de commande en fabrication qu'aucun dossier ne couvre.

    Le rattachement pointe la clé métier (numéro + ligne) et non l'`id` du
    miroir, qui est reconstruit à chaque synchro. `numero` y est stocké en
    texte : le CAST n'est pas cosmétique, sans lui SQLite ne rapproche jamais
    un INTEGER d'un TEXT et la tuile afficherait tout le carnet.
    """
    if not miroir.mysifa_attachee(conn):
        return None
    if not sch.a("cde_ligne", "qtep", "lpos", "orig", "numero", "ligne"):
        return None
    n = _un(conn, """
        SELECT COUNT(*)
          FROM cde_ligne l
         WHERE l.qtep > 0 AND COALESCE(l.lpos, 0) <> ? AND l.orig = ?
           AND NOT EXISTS (
                 SELECT 1 FROM mysifa.rvgi_rattachements r
                  WHERE r.piece = 'commande'
                    AND r.numero = CAST(l.numero AS TEXT)
                    AND (r.ligne IS NULL OR r.ligne = l.ligne))
    """, (POS_SOLDEE, ORIG_FABRICATION))
    if n is None:
        sortie["indispo"].append("Lignes sans dossier : table rvgi_rattachements absente")
    return _entier(n)


# ── Tableau de bord direction ────────────────────────────────────────────────

def direction():
    """Rentré, facturable, facturé — plus le rentré de la veille, au détail.

    Le rentré de la veille est complet dès la synchro de 5 h : les commandes
    de la journée écoulée sont toutes dans l'export. Il reste recalculé à
    chaque passage, donc une commande modifiée après coup le fait bouger —
    c'est la photo de l'ERP, pas un chiffre figé.
    """
    b = _bornes()
    sortie = {
        "present": miroir.miroir_present(),
        "bornes": b,
        "formules": FORMULES,
        "indispo": [],
    }
    if not sortie["present"]:
        return sortie

    with miroir.get_erp_db() as conn:
        sch = _Schema(conn)

        montant_cde = _expr_montant(sch, "cde_ligne", "l")
        montant_fac = _expr_montant(sch, "vte_ligne", "l")
        sortie["controle_montant"] = {
            "commandes": _controle_montant(conn, sch, "cde_ligne", "l"),
            "factures": _controle_montant(conn, sch, "vte_ligne", "l"),
        }

        # ── Le rentré : la veille, le mois, la série ─────────────────────
        if montant_cde is None or not sch.a("cde_entete", "numero", "amjc"):
            sortie["indispo"].append(
                "Rentré : " + (sch.manque("cde_entete", "numero", "amjc")
                               or "aucune colonne de montant sur cde_ligne"))
            sortie["hier"] = None
            sortie["rentre"] = None
            sortie["jours"] = []
        else:
            sortie["hier"] = _rentre_du_jour(conn, sch, montant_cde, b["veille"])
            sortie["rentre"] = {
                "mois": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM cde_ligne l
                      JOIN cde_entete e ON e.numero = l.numero
                     WHERE e.amjc >= ?""" % montant_cde, (b["debut_mois"],))),
                "mois_n1": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM cde_ligne l
                      JOIN cde_entete e ON e.numero = l.numero
                     WHERE e.amjc >= ? AND e.amjc < ?""" % montant_cde,
                    (b["debut_mois_n1"], b["fin_mois_n1"]))),
            }
            sortie["jours"] = _calendrier(
                _lignes(conn, """
                    SELECT e.amjc AS jour, SUM(%s) AS montant
                      FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
                     WHERE e.amjc >= ? AND e.amjc <= ?
                  GROUP BY e.amjc ORDER BY e.amjc
                """ % montant_cde, (b["il_y_a_30j"], b["aujourdhui"])),
                b["il_y_a_30j"], b["aujourdhui"])

        # ── Le facturé ───────────────────────────────────────────────────
        if montant_fac is None or not sch.a("vte_entete", "numero", "amjf"):
            sortie["indispo"].append(
                "Facturé : " + (sch.manque("vte_entete", "numero", "amjf")
                                or "aucune colonne de montant sur vte_ligne"))
            sortie["facture"] = None
        else:
            sortie["facture"] = {
                "mois": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM vte_ligne l
                      JOIN vte_entete e ON e.numero = l.numero
                     WHERE e.amjf >= ?""" % montant_fac, (b["debut_mois"],))),
                "mois_n1": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM vte_ligne l
                      JOIN vte_entete e ON e.numero = l.numero
                     WHERE e.amjf >= ? AND e.amjf < ?""" % montant_fac,
                    (b["debut_mois_n1"], b["fin_mois_n1"]))),
            }
            sortie["top_clients"] = _lignes(conn, """
                SELECT e.rs AS client, SUM(%s) AS montant
                  FROM vte_ligne l JOIN vte_entete e ON e.numero = l.numero
                 WHERE e.amjf >= ? AND COALESCE(e.rs,'') <> ''
              GROUP BY e.rs ORDER BY montant DESC LIMIT 6
            """ % montant_fac, (b["debut_mois"],)) if sch.a("vte_entete", "rs") else []

        # ── La série 12 mois, les deux courbes sur la même échelle ───────
        sortie["serie"] = _serie_12_mois(conn, sch, montant_cde, montant_fac, b)

        # ── Le facturable ────────────────────────────────────────────────
        sortie["facturable"] = _facturable(conn, sch, sortie)

        # ── L'encours du carnet ──────────────────────────────────────────
        if montant_cde and sch.a("cde_ligne", "qtep", "lpos", "qte"):
            sortie["carnet"] = {
                "montant": _nombre(_un(conn, """
                    SELECT SUM(CASE WHEN l.qte > 0
                                    THEN (%s) * (l.qtep * 1.0 / l.qte) ELSE 0 END)
                      FROM cde_ligne l
                     WHERE l.qtep > 0 AND COALESCE(l.lpos,0) <> ?
                """ % montant_cde, (POS_SOLDEE,))),
                "lignes": _entier(_un(conn,
                    "SELECT COUNT(*) FROM cde_ligne l WHERE l.qtep > 0 "
                    "AND COALESCE(l.lpos,0) <> ?", (POS_SOLDEE,))),
            }
        else:
            sortie["carnet"] = None

    return sortie


def _expr_montant(sch, table, alias):
    """Le montant d'une ligne : `net`, le montant net de RVGI.

    Arbitré le 27/08/2026 : dans RVGI, `pub` est le prix unitaire brut, `pun`
    le prix unitaire net, et `net` le montant net de la ligne — c'est `net`
    qui fait foi. `htn` puis `qte × pun` ne servent que de repli si la colonne
    manque dans le miroir ; la formule retenue remonte à l'écran, qui
    l'affiche sous la tuile.
    """
    for col in ("net", "htn"):
        if sch.a(table, col):
            return "COALESCE(%s.%s, 0)" % (alias, col)
    if sch.a(table, "qte", "pun"):
        return "COALESCE(%s.qte,0) * COALESCE(%s.pun,0)" % (alias, alias)
    return None


def _controle_montant(conn, sch, table, alias):
    """Mesure ce que `net` contient vraiment, au lieu de le supposer.

    L'hypothèse « `net` est un montant de ligne » tient tout le chiffre
    d'affaires de l'écran. Si elle était fausse — si `net` doublait `pun` —
    le CA serait divisé par la quantité, en silence, et personne ne verrait
    rien : les ordres de grandeur d'un mois n'alertent pas quand on ne les
    connaît pas par cœur.

    Alors on compare, sur un échantillon de lignes chiffrées, `net` à
    `qte × pun` d'un côté et à `pun` de l'autre. Le verdict remonte à
    l'écran, qui alerte s'il n'est pas celui attendu. Aucune correction
    automatique : si RVGI dit autre chose que ce qu'on croit, c'est la
    lecture qu'il faut reprendre, pas le chiffre qu'il faut rattraper.
    """
    if not sch.a(table, "net", "qte", "pun"):
        return None
    rows = _lignes(conn, """
        SELECT %s.net AS net, %s.qte AS qte, %s.pun AS pun
          FROM %s %s
         WHERE %s.net IS NOT NULL AND %s.net <> 0
           AND %s.qte > 0 AND %s.pun IS NOT NULL AND %s.pun <> 0
         LIMIT 500
    """ % (alias, alias, alias, table, alias, alias, alias, alias, alias, alias))
    if len(rows) < 20:
        return {"verdict": "indetermine", "echantillon": len(rows),
                "raison": "trop peu de lignes chiffrées pour conclure"}

    proche = lambda a, b: abs(a - b) <= 0.01 * max(abs(a), abs(b), 1.0)
    sur_ligne = sur_unitaire = 0
    for r in rows:
        try:
            net, qte, pun = float(r["net"]), float(r["qte"]), float(r["pun"])
        except (TypeError, ValueError):
            continue
        if proche(net, qte * pun):
            sur_ligne += 1
        if proche(net, pun):
            sur_unitaire += 1

    n = len(rows)
    verdict = "indetermine"
    if sur_ligne >= 0.8 * n and sur_ligne > sur_unitaire:
        verdict = "montant_de_ligne"
    elif sur_unitaire >= 0.8 * n and sur_unitaire > sur_ligne:
        verdict = "prix_unitaire"
    return {"verdict": verdict, "echantillon": n,
            "sur_ligne": sur_ligne, "sur_unitaire": sur_unitaire, "table": table}


def _rentre_du_jour(conn, sch, montant, jour):
    """Le détail d'une journée de prise de commande, commande par commande."""
    entete = _lignes(conn, """
        SELECT COUNT(DISTINCT l.numero) AS commandes, COUNT(*) AS lignes,
               COUNT(DISTINCT e.numclt) AS clients, SUM(%s) AS montant
          FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
         WHERE e.amjc = ?
    """ % montant, (jour,))
    tete = entete[0] if entete else {}
    champ_clt = "e.rs" if sch.a("cde_entete", "rs") else "''"
    champ_orig = "l.orig" if sch.a("cde_ligne", "orig") else "NULL"
    items = _lignes(conn, """
        SELECT MIN(l.id) AS id, l.numero AS numero, %s AS client, COUNT(*) AS lignes,
               SUM(%s) AS montant, MIN(NULLIF(l.amje,'')) AS expedition,
               MAX(%s) AS origine
          FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
         WHERE e.amjc = ?
      GROUP BY l.numero, %s
      ORDER BY montant DESC
         LIMIT %d
    """ % (champ_clt, montant, champ_orig, champ_clt, MAX_LIGNES_LISTE), (jour,))
    # Moyenne des 30 jours glissants, week-ends compris : c'est la référence
    # honnête. Comparer un mardi à la moyenne des seuls jours ouvrés gonfle
    # mécaniquement le résultat.
    moyenne = _un(conn, """
        SELECT SUM(%s) / 30.0 FROM cde_ligne l
          JOIN cde_entete e ON e.numero = l.numero
         WHERE e.amjc >= ? AND e.amjc <= ?
    """ % montant, ((date.fromisoformat(jour) - timedelta(days=29)).isoformat(), jour))
    return {
        "date": jour,
        "montant": _nombre(tete.get("montant")),
        "commandes": _entier(tete.get("commandes")),
        "lignes": _entier(tete.get("lignes")),
        "clients": _entier(tete.get("clients")),
        "moyenne_30j": _nombre(moyenne),
        "items": items,
    }


def _calendrier(rows, debut, fin):
    """Trente jours de suite, y compris ceux où rien n'est rentré.

    Un jour sans commande vaut zéro, il ne vaut pas « rien » : la requête ne
    rend que les jours peuplés, et une bande qui les recollerait montrerait
    une activité continue là où il y a des week-ends.
    """
    par_jour = {str(r.get("jour") or ""): _nombre(r.get("montant")) or 0.0 for r in rows}
    j = date.fromisoformat(debut)
    stop = date.fromisoformat(fin)
    out = []
    while j <= stop:
        cle = j.isoformat()
        out.append({"jour": cle, "montant": par_jour.get(cle, 0.0)})
        j += timedelta(days=1)
    return out


def _serie_12_mois(conn, sch, montant_cde, montant_fac, b):
    """Rentré et facturé mois par mois — deux séries, une seule échelle."""
    par_mois = {}

    def _verser(rows, cle):
        for r in rows:
            mois = str(r.get("mois") or "")[:7]
            if len(mois) != 7:
                continue
            par_mois.setdefault(mois, {"mois": mois, "rentre": None, "facture": None})
            par_mois[mois][cle] = _nombre(r.get("montant"))

    if montant_cde and sch.a("cde_entete", "numero", "amjc"):
        _verser(_lignes(conn, """
            SELECT substr(e.amjc,1,7) AS mois, SUM(%s) AS montant
              FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
             WHERE e.amjc >= ? GROUP BY mois ORDER BY mois
        """ % montant_cde, (b["debut_serie"],)), "rentre")

    if montant_fac and sch.a("vte_entete", "numero", "amjf"):
        _verser(_lignes(conn, """
            SELECT substr(e.amjf,1,7) AS mois, SUM(%s) AS montant
              FROM vte_ligne l JOIN vte_entete e ON e.numero = l.numero
             WHERE e.amjf >= ? GROUP BY mois ORDER BY mois
        """ % montant_fac, (b["debut_serie"],)), "facture")

    serie = sorted(par_mois.values(), key=lambda x: x["mois"])[-12:]
    for m in serie:
        m["label"] = _libelle_mois(m["mois"])
    return serie


def _facturable(conn, sch, sortie):
    """Livré, pas encore facturé — et depuis combien de temps.

    Valorisé au prix unitaire de la ligne de commande d'origine : le BL ne
    porte pas de prix. L'écart avec la facture réelle est donc normal (remises
    de pied, port), et l'écran le dit plutôt que de le masquer.
    """
    manque = sch.manque("liv_ligne", "qte", "qtefac", "numcde", "lignecde", "amje")
    if manque:
        sortie["indispo"].append("Facturable : " + manque)
        return None
    if not sch.a("cde_ligne", "numero", "ligne", "pun"):
        sortie["indispo"].append("Facturable : pas de prix unitaire sur cde_ligne")
        return None

    valeur = ("(l.qte - COALESCE(l.qtefac,0)) * COALESCE(c.pun, 0)")
    base = """
        FROM liv_ligne l
        LEFT JOIN cde_ligne c ON c.numero = l.numcde AND c.ligne = l.lignecde
       WHERE l.qte > COALESCE(l.qtefac, 0)
    """
    total = _nombre(_un(conn, "SELECT SUM(%s) %s" % (valeur, base)))
    bl = _entier(_un(conn, "SELECT COUNT(DISTINCT l.numero) %s" % base))

    aujourdhui = sortie["bornes"]["aujourdhui"]
    tranches = [
        ("Livré cette semaine", 0, 7),
        ("8 – 15 jours", 7, 15),
        ("16 – 30 jours", 15, 30),
        ("Plus de 30 jours", 30, None),
    ]
    ages = []
    for libelle, mini, maxi in tranches:
        haut = (date.fromisoformat(aujourdhui) - timedelta(days=mini)).isoformat()
        bas = ((date.fromisoformat(aujourdhui) - timedelta(days=maxi)).isoformat()
               if maxi is not None else None)
        cond = (" AND " + _date_reelle("l.amje")
                + " AND l.amje <= ?" + (" AND l.amje > ?" if bas else ""))
        params = (haut,) + ((bas,) if bas else ())
        ages.append({
            "label": libelle,
            "montant": _nombre(_un(conn, "SELECT SUM(%s) %s %s" % (valeur, base, cond), params)),
        })
    return {"montant": total, "bl": bl, "ages": ages}
