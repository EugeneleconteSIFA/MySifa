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

# Position d'une ligne (ENUMS["position"]) : 0 = en cours, 1 = partielle,
# 2 = soldée.
#
# Le carnet retient « en cours », pas « non soldée ». La nuance vaut 68 lignes :
# sur les 91 lignes « partielle » du miroir au 28/08/2026, 10 datent de 2026 —
# les seules que l'écran de RVGI montre — et 81 de 2015 à 2024, sans le moindre
# BL, avec `orig` et `prod` à 255, la sentinelle « non renseigné ». Ce sont des
# reliquats d'avant les champs que RVGI utilise aujourd'hui. `<> POS_SOLDEE`
# les faisait toutes entrer ; `= POS_EN_COURS` aligne la tuile sur l'écran
# Commandes, qui s'ouvre lui aussi sur « En cours ».
POS_EN_COURS = 0
POS_SOLDEE = 2

MAX_LIGNES_LISTE = 12

# Une ligne de commande ne porte pas forcément un produit. RVGI y met aussi
# les frais de port, les frais de cliché, les frais d'outils, les créations de
# document : des lignes de refacturation, jamais « livrées », qui restent
# ouvertes indéfiniment. Relevé sur les données réelles le 27/08/2026 : elles
# remontaient dans « en retard » avec 4 200 jours d'ancienneté, depuis 2015,
# et noyaient les vrais retards.
#
# Une référence produit SIFA s'écrit `famille/numéro` — `code1`/`code2`, les
# deux renseignés. C'est la seule marque structurelle disponible sur la ligne
# elle-même ; le libellé (« Frais de port ») ne se filtre pas, il change.
def _ligne_produit(alias="l"):
    # `code1`/`code2`/`code3` sont forcés en TEXTE à l'import, dans toutes les
    # tables (`import_rvgi_csv.COLS_TEXTE_FORCE`) : sans ça, `code1` vaut 890
    # en entier dans `cde_ligne` et « FR » en texte dans `fic_art`, et la
    # jointure ne remonte rien sans lever d'erreur.
    #
    # Conséquence ici : `code1 > 0` compare du texte à un entier. En SQLite un
    # TEXTE est TOUJOURS supérieur à un INTEGER, quel qu'il soit — le test
    # était donc vrai pour « 0 » comme pour « 601 », et ne filtrait rien. La
    # comparaison se fait sur la chaîne, pas sur une valeur numérique.
    return (" AND ".join(
        "TRIM(COALESCE(%s.%s, '')) NOT IN ('', '0')" % (alias, c)
        for c in ("code1", "code2")))


# Une ligne de commande dont l'entête a disparu n'est pas une commande.
#
# `export_rvgi_csv.ps1` filtre `corbeille = 0` table par table : quand RVGI met
# une commande à la corbeille sans marquer ses lignes, l'entête ne sort pas de
# l'export et les lignes, elles, sortent. Elles arrivent dans le miroir sans
# parent, leur position reste « en cours » pour l'éternité — personne ne les
# soldera — et un compteur bâti sur la seule table des lignes les prend pour du
# travail à faire. Mesuré le 28/08/2026 : 744 des 880 lignes `lpos = 0`, 493
# numéros de commande, échoués là depuis 2019, dont neuf seulement avaient
# jamais produit un BL. La tuile annonçait 683 commandes à traiter.
#
# Le prédicat est un EXISTS corrélé et non une jointure : il s'ajoute à un
# `WHERE` déjà écrit, sans toucher au `FROM` ni risquer de collision d'alias
# avec les jointures que certaines requêtes posent déjà.
def _existe_piece(sch, entete="cde_entete", alias="l", cle="numero"):
    if not sch.a(entete, cle):
        return "1=1"          # entête absente du miroir : on ne filtre rien
    return ("EXISTS (SELECT 1 FROM %s __p WHERE __p.%s = %s.%s)"
            % (entete, cle, alias, cle))


# Passé ce délai, une ligne en retard n'est plus un retard sur lequel agir :
# c'est une ligne que personne ne fermera. Comptée à part, pas cachée.
JOURS_DORMANT = 90

# « À venir ou en cours » : ce que la production a encore devant elle. Une
# ligne dont la date d'expédition est passée depuis plus longtemps n'attend
# plus de dossier, elle attend un ménage.
JOURS_EN_COURS = 30

# Une date réelle, par opposition aux sentinelles de RVGI (`30/11/1999` pour
# « non renseignée », `31/12/2099` pour « pas de fin »). Comparer sans ce
# garde-fou fait passer toute ligne sans date promise pour une ligne en
# retard — mesuré sur le jeu de test : 289 faux retards sur 384 lignes.
# Les dates du miroir ne sont pas nues : `_propre_date` teste la sentinelle
# avec `startswith`, parce que RVGI écrit « 2026-08-26 » suivi d'une heure.
# Une égalité stricte sur la colonne ne rapproche donc jamais rien — c'est
# ce qui affichait « rentré hier : 0 » un jour où sept commandes étaient
# entrées. Les comparaisons de jour passent toutes par ici.
def _jour(col):
    return "substr(%s, 1, 10)" % col


def _mois(col):
    return "substr(%s, 1, 7)" % col


def _date_reelle(col):
    return "%s IS NOT NULL AND %s > '2000-01-01' AND %s < '2090-01-01'" % (col, col, col)

FORMULES = {
    "carnet": "lignes de commande à traiter : qtep > 0, position « en cours », "
              "portant une référence produit (code1/code2), et dont la "
              "commande existe encore (entête présente dans le miroir)",
    "retard": "carnet dont la date d'expédition est passée depuis moins de "
              "90 jours ; au-delà la ligne est comptée comme dormante",
    "dormant": "lignes en cours dont l'expédition est passée depuis plus de "
               "90 jours — RVGI ne les solde jamais, elles ne se rattrapent plus",
    "semaine": "carnet dont amje tombe dans les 7 prochains jours",
    "a_facturer": "liv_ligne : qte livrée > qte facturée",
    "sans_dossier": "lignes en fabrication à venir ou en cours (expédition "
                    "des 30 derniers jours ou à venir) sans dossier MySifa rattaché",
    "hors_prod": "carnet dont l'origine est stock ou sous-traitance",
    "rentre": "Σ du total HT des lignes de commande créées ce jour-là, "
              "par cde_entete.amjc",
    "facture": "Σ du total HT des lignes de facture, par mois de "
               "vte_entete.amjf",
    "facturable": "part non facturée du total HT de la ligne de commande "
                  "d'origine, au prorata de (qte livrée − qte facturée)",
    "encours": "Σ du total HT du carnet, au prorata de ce qui reste à traiter",
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
        # Fin du mois courant : une pièce datée dans le futur — faute de
        # frappe dans l'ERP — ne doit pas ajouter un mois à la série.
        "fin_mois": ((debut_mois + timedelta(days=32)).replace(day=1)
                     - timedelta(days=1)).isoformat(),
        "fin_semaine": (j + timedelta(days=7)).isoformat(),
        # Trente jours ouvrés remontent à environ six semaines.
        "il_y_a_30j": (j - timedelta(days=41)).isoformat(),
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
            # Une commande porte plusieurs lignes : les deux comptes sont
            # affichés partout. « 845 lignes » ne veut rien dire sans « sur
            # 312 commandes », et c'est la commande qu'on rappelle au client.
            produit = _ligne_produit("l") if sch.a("cde_ligne", "code1", "code2") else "1=1"
            ouvert = ("l.qtep > 0 AND COALESCE(l.lpos, 0) = %d AND %s AND %s"
                      % (POS_EN_COURS, produit, _existe_piece(sch)))
            date_ok = _date_reelle(_jour("l.amje"))
            limite_dormant = (date.fromisoformat(b["aujourdhui"])
                              - timedelta(days=JOURS_DORMANT)).isoformat()

            def _compte(where, params=()):
                r = _lignes(conn, "SELECT COUNT(*) AS lignes, "
                            "COUNT(DISTINCT l.numero) AS commandes "
                            "FROM cde_ligne l WHERE " + where, params)
                return {"lignes": _entier(r[0]["lignes"]) if r else 0,
                        "commandes": _entier(r[0]["commandes"]) if r else 0}

            sortie["carnet"] = _compte(ouvert)
            sortie["carnet"]["retard"] = _compte(
                ouvert + " AND " + date_ok + " AND substr(l.amje,1,10) < ? AND substr(l.amje,1,10) >= ?",
                (b["aujourdhui"], limite_dormant))
            sortie["carnet"]["dormant"] = _compte(
                ouvert + " AND " + date_ok + " AND substr(l.amje,1,10) < ?", (limite_dormant,))
            sortie["carnet"]["semaine"] = _compte(
                ouvert + " AND " + date_ok + " AND substr(l.amje,1,10) >= ? AND substr(l.amje,1,10) < ?",
                (b["aujourdhui"], b["fin_semaine"]))
            sortie["carnet"]["jours_dormant"] = JOURS_DORMANT
            # La date charnière, pour que le lien « les voir » ouvre le carnet
            # sur exactement les lignes que la tuile compte.
            sortie["carnet"]["dormant"]["avant"] = limite_dormant

            # Les lignes en retard, avec leur client — la liste d'action. On
            # part des plus récentes : une ligne de la semaine dernière se
            # rattrape, une ligne de l'an dernier ne se rattrape plus.
            joint_clt = ("LEFT JOIN cde_entete e ON e.numero = l.numero"
                         if sch.a("cde_entete", "numero", "rs") else "")
            champ_clt = "e.rs" if joint_clt else "''"
            sortie["retards"] = _lignes(conn, """
                SELECT l.id AS id, l.numero AS numero, l.ligne AS ligne,
                       %s AS client, l.des1 AS designation,
                       l.code1 AS code1, l.code2 AS code2,
                       l.qtep AS reste, l.amje AS expedition, l.orig AS origine
                  FROM cde_ligne l %s
                 WHERE %s AND %s AND substr(l.amje,1,10) < ? AND substr(l.amje,1,10) >= ?
              ORDER BY substr(l.amje,1,10) DESC
                 LIMIT %d
            """ % (champ_clt, joint_clt, ouvert, date_ok, MAX_LIGNES_LISTE),
                (b["aujourdhui"], limite_dormant))

            # Ce que le filtre « ligne produit » a écarté, en clair. Une
            # règle de filtrage qu'on ne peut pas vérifier d'un coup d'œil
            # finit par écarter la mauvaise chose sans que personne ne le voie.
            sortie["ecartees"] = _ecartees(conn, sch, b)

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
            reste = ("l.qte > COALESCE(l.qtefac, 0) AND %s"
                     % _existe_piece(sch, entete="liv_entete"))
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
    produit = _ligne_produit("l") if sch.a("cde_ligne", "code1", "code2") else "1=1"
    depuis = (date.fromisoformat(sortie["bornes"]["aujourdhui"])
              - timedelta(days=JOURS_EN_COURS)).isoformat()
    rows = _lignes(conn, """
        SELECT COUNT(*) AS lignes, COUNT(DISTINCT l.numero) AS commandes
          FROM cde_ligne l
         WHERE l.qtep > 0 AND COALESCE(l.lpos, 0) = ? AND l.orig = ? AND %s
           AND %s AND %s AND substr(l.amje,1,10) >= ?
           AND NOT EXISTS (
                 SELECT 1 FROM mysifa.rvgi_rattachements r
                  WHERE r.piece = 'commande'
                    AND r.numero = CAST(l.numero AS TEXT)
                    AND (r.ligne IS NULL OR r.ligne = l.ligne))
    """ % (produit, _existe_piece(sch), _date_reelle(_jour("l.amje"))),
        (POS_EN_COURS, ORIG_FABRICATION, depuis))
    if not rows:
        sortie["indispo"].append("Lignes sans dossier : table rvgi_rattachements absente")
        return None
    return {"lignes": _entier(rows[0]["lignes"]),
            "commandes": _entier(rows[0]["commandes"]),
            "depuis": depuis, "jours": JOURS_EN_COURS}


def _ecartees(conn, sch, b):
    """Ce que le filtre « ligne produit » retire du carnet, en clair.

    Frais de port, frais de cliché, frais d'outils : RVGI les porte sur des
    lignes de commande sans référence produit, et personne ne les solde
    jamais. Le tableau de bord les écarte — mais il montre lesquelles, et
    combien, pour qu'on puisse contredire la règle si elle se trompe.
    """
    if not sch.a("cde_ligne", "code1", "code2", "des1", "qtep", "lpos"):
        return None
    # Même périmètre que le carnet, sinon la ligne « écartées » compterait des
    # frais de port de commandes qui n'existent plus, et le total ne se
    # raccorderait à rien.
    hors = ("l.qtep > 0 AND COALESCE(l.lpos,0) = %d AND %s AND NOT (%s)"
            % (POS_EN_COURS, _existe_piece(sch), _ligne_produit("l")))
    total = _entier(_un(conn, "SELECT COUNT(*) FROM cde_ligne l WHERE " + hors))
    if not total:
        return {"lignes": 0, "libelles": []}
    return {
        "lignes": total,
        "libelles": _lignes(conn, """
            SELECT COALESCE(NULLIF(TRIM(l.des1), ''), '(sans libellé)') AS libelle,
                   COUNT(*) AS lignes
              FROM cde_ligne l WHERE %s
          GROUP BY libelle ORDER BY lignes DESC LIMIT 8
        """ % hors),
    }


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
        # `NULL` plutôt que rien : les requêtes tournent, les comptages
        # restent justes, et seuls les montants ressortent vides.
        m_cde = montant_cde or "NULL"
        m_fac = montant_fac or "NULL"
        if montant_cde is None:
            sortie["indispo"].append(
                "Montants des commandes : aucune colonne de total HT sur "
                "cde_ligne — voir « Contrôle du calcul »")
        if montant_fac is None:
            sortie["indispo"].append(
                "Montants des factures : aucune colonne de total HT sur "
                "vte_ligne — voir « Contrôle du calcul »")
        sortie["diagnostic_prix"] = [
            _diagnostic_complet(conn, sch, "cde_ligne", "l",
                                "cde_entete", "amjc", b["debut_mois"]),
            _diagnostic_complet(conn, sch, "vte_ligne", "l",
                                "vte_entete", "amjf", b["debut_mois"]),
        ]

        # ── Le rentré : la veille, le mois, la série ─────────────────────
        if not sch.a("cde_entete", "numero", "amjc"):
            sortie["indispo"].append(
                "Rentré : " + sch.manque("cde_entete", "numero", "amjc"))
            sortie["hier"] = None
            sortie["rentre"] = None
            sortie["jours"] = []
        else:
            sortie["hier"] = _rentre_du_jour(conn, sch, m_cde, b["veille"])
            sortie["rentre"] = {
                "mois": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM cde_ligne l
                      JOIN cde_entete e ON e.numero = l.numero
                     WHERE substr(e.amjc,1,10) >= ?""" % m_cde, (b["debut_mois"],))),
                "mois_n1": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM cde_ligne l
                      JOIN cde_entete e ON e.numero = l.numero
                     WHERE substr(e.amjc,1,10) >= ? AND substr(e.amjc,1,10) < ?""" % m_cde,
                    (b["debut_mois_n1"], b["fin_mois_n1"]))),
            }
            sortie["jours"] = _calendrier(
                _lignes(conn, """
                    SELECT substr(e.amjc,1,10) AS jour, SUM(%s) AS montant
                      FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
                     WHERE substr(e.amjc,1,10) >= ? AND substr(e.amjc,1,10) <= ?
                  GROUP BY jour ORDER BY jour
                """ % m_cde, (b["il_y_a_30j"], b["aujourdhui"])),
                b["il_y_a_30j"], b["aujourdhui"])

        # ── Le facturé ───────────────────────────────────────────────────
        if not sch.a("vte_entete", "numero", "amjf"):
            sortie["indispo"].append(
                "Facturé : " + sch.manque("vte_entete", "numero", "amjf"))
            sortie["facture"] = None
        else:
            sortie["facture"] = {
                "mois": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM vte_ligne l
                      JOIN vte_entete e ON e.numero = l.numero
                     WHERE substr(e.amjf,1,10) >= ?""" % m_fac, (b["debut_mois"],))),
                "mois_n1": _nombre(_un(conn, """
                    SELECT SUM(%s) FROM vte_ligne l
                      JOIN vte_entete e ON e.numero = l.numero
                     WHERE substr(e.amjf,1,10) >= ? AND substr(e.amjf,1,10) < ?""" % m_fac,
                    (b["debut_mois_n1"], b["fin_mois_n1"]))),
            }
            sortie["top_clients"] = _lignes(conn, """
                SELECT e.rs AS client, SUM(%s) AS montant
                  FROM vte_ligne l JOIN vte_entete e ON e.numero = l.numero
                 WHERE substr(e.amjf,1,10) >= ? AND COALESCE(e.rs,'') <> ''
              GROUP BY e.rs ORDER BY montant DESC LIMIT 6
            """ % m_fac, (b["debut_mois"],)) if sch.a("vte_entete", "rs") else []

        # ── La série 12 mois, les deux courbes sur la même échelle ───────
        sortie["serie"] = _serie_12_mois(conn, sch, m_cde, m_fac, b)

        # ── Le facturable ────────────────────────────────────────────────
        sortie["facturable"] = _facturable(conn, sch, sortie)

        # ── L'encours du carnet ──────────────────────────────────────────
        if sch.a("cde_ligne", "qtep", "lpos", "qte"):
            vivante = _existe_piece(sch)
            sortie["carnet"] = {
                "montant": _nombre(_un(conn, """
                    SELECT SUM(CASE WHEN l.qte > 0
                                    THEN (%s) * (l.qtep * 1.0 / l.qte) ELSE NULL END)
                      FROM cde_ligne l
                     WHERE l.qtep > 0 AND COALESCE(l.lpos,0) = ? AND %s
                """ % (m_cde, vivante), (POS_EN_COURS,))),
                "lignes": _entier(_un(conn,
                    "SELECT COUNT(*) FROM cde_ligne l WHERE l.qtep > 0 "
                    "AND COALESCE(l.lpos,0) = ? AND " + vivante, (POS_EN_COURS,))),
            }
        else:
            sortie["carnet"] = None

    return sortie


# ── Unité de vente ───────────────────────────────────────────────────────────
#
# `pun` est un prix à l'unité de VENTE, pas à l'étiquette. SIFA vend au mille :
# une ligne de 4 243 200 étiquettes à 4,82 vaut 20 452 €, pas 20 452 224 €.
#
# Deux colonnes décrivent cette unité, et une seule est fiable :
#   `suv` — le code de l'unité (« M » pour mille, « U » pour unité) ;
#   `vuv` — le coefficient chiffré, renseigné sur une partie des lignes seulement.
#
# Relevé le 27/08/2026 : sur `cde_ligne`, la moitié des lignes `suv = M` porte
# `vuv = 1000` et l'autre moitié `vuv = 1`. Les deux moitiés ont les mêmes
# quantités et les mêmes prix — c'est donc `vuv` qui est incomplet, pas les
# lignes qui diffèrent. Se fier à lui seul faisait ressortir un mois à onze
# milliards d'euros.
#
# La règle retenue : le code `suv` décide, `vuv` ne sert que de repli quand le
# code est vide ou inconnu. Un code non répertorié est signalé par le
# diagnostic — il n'est jamais deviné.
# ATTENTION — `suv` n'est PAS toujours une lettre. Relevé sur `vte_ligne` :
# il vaut « 3 ». La correspondance ci-dessous ne couvre donc qu'une partie des
# cas, et c'est assumé : elle ne sert plus qu'au repli, quand aucune colonne
# de total HT n'existe. Un code absent d'ici n'est jamais deviné — il ressort
# dans le diagnostic, et le montant de ces lignes est à considérer comme faux.
DIVISEUR_UNITE = {
    "M": 1000.0,   # au mille
    "U": 1.0,      # à l'unité
}


def _expr_diviseur(sch, table, alias):
    """L'expression SQL qui ramène `pun` au prix d'une étiquette."""
    a_suv = sch.a(table, "suv")
    a_vuv = sch.a(table, "vuv")
    if not a_suv and not a_vuv:
        return "1"
    repli = ("COALESCE(NULLIF(%s.vuv, 0), 1)" % alias) if a_vuv else "1"
    if not a_suv:
        return repli
    cas = " ".join(
        "WHEN UPPER(TRIM(COALESCE(%s.suv, ''))) = '%s' THEN %s"
        % (alias, code, coef) for code, coef in sorted(DIVISEUR_UNITE.items()))
    return "(CASE %s ELSE %s END)" % (cas, repli)


# Les colonnes de total HT de ligne, dans l'ordre de préférence. RVGI les
# calcule lui-même — la modale de détail les affiche « Total HT net » et
# « Total HT brut » — et un total lu vaut infiniment mieux qu'un total
# reconstruit à partir de colonnes dont personne n'a la définition.
COLS_TOTAL_HT = ("htn", "htb", "mtht", "totht", "mht", "htnet", "mtnet", "montht")


def _expr_montant(sch, table, alias):
    """Le montant d'une ligne : le total HT que RVGI a déjà calculé.

    Relevé le 27/08/2026 sur les données réelles, et c'est ce qui a mis fin à
    trois hypothèses successives :

      commande — qte 70 200 000 × pun 0,1420 = 9 968 400, et la ligne porte
                 « Total HT net » = 9 968,40. Le rapport est bien de mille.
      facture  — qte 25 890 000, pun 8 802, et `htn` = 8 802 aussi. Le rapport
                 n'est plus de mille du tout.

    Autrement dit `pun` ne se rapporte pas à la même unité d'une table à
    l'autre, et aucun coefficient unique ne raccommode les deux. Mais `htn`
    est juste dans les deux cas. On le lit, on ne le recalcule pas.

    La reconstruction `qte × pun ÷ unité` ne sert plus que de repli si aucune
    colonne de total n'existe — et le diagnostic affiche alors les deux.
    """
    for col in COLS_TOTAL_HT:
        if sch.a(table, col):
            return "COALESCE(%s.%s, 0)" % (alias, col)
    # Aucune colonne de total : la reconstruction reste calculée pour le
    # comparatif du diagnostic, mais elle ne remonte PAS aux tuiles. Un
    # chiffre d'affaires faux d'un facteur mille est pire que pas de chiffre
    # du tout — on le lit, on décide dessus, et personne ne voit passer
    # l'erreur.
    return None


def _expr_montant_reconstruit(sch, table, alias):
    """Repli : quantité × prix unitaire, ramené à l'unité de vente.

    `net` a été essayé et écarté. Relevé sur les données réelles le
    27/08/2026 : il vaut 1,00 sur toutes les lignes de facture, quantité et
    prix quelconques. Ce n'est pas un montant, c'est un drapeau — et il
    donnait un chiffre d'affaires mensuel à deux chiffres.

    Reste `qte × pun`. Mais `pun` est un prix unitaire au sens de RVGI, pas à
    l'étiquette : SIFA vend au mille. `vuv`, le coefficient de vente porté par
    la ligne, tient ce diviseur — 1000 pour des étiquettes, 1 pour un frais de
    port facturé à l'unité. Sans lui, 4 243 200 étiquettes à 4,82 ressortent à
    20 millions d'euros au lieu de 20 452.

    Le coefficient n'est appliqué que si la colonne existe. `_diagnostic_prix`
    montre le calcul sur des lignes réelles, pour qu'on puisse le contredire.
    """
    if not sch.a(table, "qte", "pun"):
        return None
    return ("COALESCE(%s.qte, 0) * COALESCE(%s.pun, 0) / %s"
            % (alias, alias, _expr_diviseur(sch, table, alias)))


# Les trois pistes pour ramener `pun` au prix d'une étiquette, et d'où elles
# viennent. Aucune n'est établie : l'écran les calcule toutes les trois sur le
# mois en cours et montre les trois totaux. Celui qui ressemble au chiffre
# d'affaires réel désigne la bonne.
def _diviseurs_candidats(sch, table, alias, alias_art):
    cands = []
    for col in COLS_TOTAL_HT:
        if sch.a(table, col):
            cands.append(("colonne " + col, None,
                          "total HT de la ligne, calculé par RVGI — lu, pas reconstruit"))
    if alias_art:
        cands.append(("article.cuv", "NULLIF(%s.cuv, 0)" % alias_art,
                      "coefficient d'unité de VENTE porté par la fiche article"))
    if sch.a(table, "suv"):
        cas = " ".join("WHEN UPPER(TRIM(COALESCE(%s.suv,''))) = '%s' THEN %s"
                       % (alias, c, v) for c, v in sorted(DIVISEUR_UNITE.items()))
        cands.append(("ligne.suv", "(CASE %s ELSE NULL END)" % cas,
                      "code d'unité de la ligne : M = mille, U = unité"))
    if sch.a(table, "vuv"):
        cands.append(("ligne.vuv", "NULLIF(%s.vuv, 0)" % alias,
                      "coefficient chiffré de la ligne — incomplet"))
    cands.append(("aucun", "1", "qte × pun brut, sans correction"))
    return cands


def _comparatif_diviseurs(conn, sch, table, alias, entete, col_date, depuis):
    """Le même mois, calculé avec chaque diviseur candidat."""
    if not sch.a(table, "qte", "pun") or not sch.a(entete, "numero", col_date):
        return []
    art = "fic_art" if sch.a("fic_art", "code1", "code2", "cuv") else None
    jointure = ("LEFT JOIN fic_art a ON a.code1 = %s.code1 AND a.code2 = %s.code2"
                % (alias, alias)) if (art and sch.a(table, "code1", "code2")) else ""
    out = []
    for nom, expr, quoi in _diviseurs_candidats(sch, table, alias,
                                                "a" if jointure else None):
        if expr is None:
            # Méthode « colonne de total » : rien à diviser, on somme la colonne.
            valeur = "COALESCE(%s.%s, 0)" % (alias, nom.split(" ", 1)[1])
        else:
            valeur = ("COALESCE(%s.qte,0) * COALESCE(%s.pun,0) / COALESCE(%s, 1)"
                      % (alias, alias, expr))
        montant = _un(conn, """
            SELECT SUM(%s)
              FROM %s %s %s
              JOIN %s e ON e.numero = %s.numero
             WHERE substr(e.%s, 1, 10) >= ?
        """ % (valeur, table, alias, jointure, entete, alias, col_date), (depuis,))
        out.append({"methode": nom, "quoi": quoi, "montant": _nombre(montant)})
    return out


def _diagnostic_prix(conn, sch, table, alias):
    """Ce que la table porte vraiment comme prix, sur des lignes réelles.

    Un chiffre d'affaires reconstruit à partir de colonnes dont personne n'a
    la définition écrite ne vaut rien tant qu'on ne l'a pas confronté à
    l'ERP. Plutôt que d'affirmer, cet écran montre son arithmétique : quelles
    colonnes de prix existent, et six lignes avec leur calcul détaillé.
    Ouvrir la même commande dans RVGI et comparer prend dix secondes.

    Le jour où c'est validé, ce bloc peut disparaître — pas avant.
    """
    candidates = (("qte", "pub", "pun", "net", "suv", "vuv")
                  + COLS_TOTAL_HT + ("des1",))
    presentes = [c for c in candidates if sch.a(table, c)]
    if not sch.a(table, "qte", "pun"):
        return {"table": table, "colonnes": presentes, "echantillon": [],
                "note": "ni qte ni pun : aucun montant reconstructible"}

    champs = ", ".join("%s.%s AS %s" % (alias, c, c) for c in presentes)
    montant = _expr_montant(sch, table, alias)
    rows = _lignes(conn, """
        SELECT %s, (%s) AS montant_calcule
          FROM %s %s
         WHERE %s.qte > 0 AND %s.pun IS NOT NULL AND %s.pun <> 0
      ORDER BY %s.qte DESC
         LIMIT 6
    """ % (champs, montant, table, alias, alias, alias, alias, alias))

    # `net` constant sur tout un échantillon n'est pas un montant : le dire
    # explicitement évite qu'on y revienne dans six mois.
    net_plat = None
    if sch.a(table, "net"):
        distincts = _un(conn, "SELECT COUNT(DISTINCT %s.net) FROM %s %s "
                              "WHERE %s.qte > 0 LIMIT 1"
                        % (alias, table, alias, alias))
        net_plat = (distincts is not None and int(distincts) <= 2)

    # Ce que `suv` et `vuv` contiennent RÉELLEMENT, par combinaison. C'est la
    # question à laquelle personne n'a la réponse écrite : si `vuv` vaut 1 sur
    # des lignes vendues au mille, le montant est multiplié par mille et un
    # mois ressort à onze milliards d'euros.
    unites = []
    if sch.a(table, "suv") or sch.a(table, "vuv"):
        cles = [c for c in ("suv", "vuv") if sch.a(table, c)]
        sel = ", ".join("%s.%s AS %s" % (alias, c, c) for c in cles)
        unites = _lignes(conn, """
            SELECT %s, COUNT(*) AS lignes,
                   MIN(%s.qte) AS qte_min, MAX(%s.qte) AS qte_max,
                   MIN(%s.pun) AS pun_min, MAX(%s.pun) AS pun_max,
                   SUM(%s) AS montant
              FROM %s %s
             WHERE %s.qte > 0
          GROUP BY %s
          ORDER BY lignes DESC
             LIMIT 10
        """ % (sel, alias, alias, alias, alias, montant, table, alias, alias,
               ", ".join(cles)))

    # Et les lignes qui pèsent le plus lourd : c'est là que se voit l'erreur.
    lourdes = _lignes(conn, """
        SELECT %s.numero AS numero, %s, (%s) AS montant_calcule
          FROM %s %s
         WHERE %s.qte > 0 AND %s.pun IS NOT NULL AND %s.pun <> 0
      ORDER BY montant_calcule DESC
         LIMIT 8
    """ % (alias, champs, montant, table, alias, alias, alias, alias))

    # Un code d'unité qu'on ne connaît pas retombe sur `vuv`, donc souvent
    # sur 1 : c'est exactement le cas qui multiplie un montant par mille. Il
    # doit se voir, pas se noyer.
    inconnus = []
    if sch.a(table, "suv"):
        inconnus = [u for u in unites
                    if str(u.get("suv") or "").strip().upper() not in DIVISEUR_UNITE
                    and (u.get("qte_max") or 0) > 1000]

    # Un code d'unité inconnu n'a d'importance que si le montant est
    # reconstruit. Dès lors qu'on lit le total HT de la ligne, `suv` ne sert
    # plus à rien — crier au loup à ce moment-là ferait ignorer l'alerte le
    # jour où elle compte vraiment.
    reconstruit = not any(sch.a(table, c) for c in COLS_TOTAL_HT)
    if not reconstruit:
        inconnus = []

    # Toutes les colonnes numériques de la table, avec leur ordre de grandeur.
    # Quand aucune colonne de total connue n'existe, c'est là-dedans qu'elle
    # se cache sous un autre nom — et une moyenne parle plus qu'un nom.
    candidates_total = []
    if reconstruit:
        for c in sorted(sch.cols(table)):
            if c in ("id", "numero", "ligne", "corbeille") or c.startswith("code"):
                continue
            r = _lignes(conn, """
                SELECT COUNT(*) AS n, AVG(%s.%s) AS moyenne,
                       MIN(%s.%s) AS mini, MAX(%s.%s) AS maxi
                  FROM %s %s
                 WHERE typeof(%s.%s) IN ('integer','real') AND %s.%s <> 0
            """ % (alias, c, alias, c, alias, c, table, alias, alias, c, alias, c))
            if r and _entier(r[0]["n"]) > 0:
                candidates_total.append({
                    "colonne": c, "lignes": _entier(r[0]["n"]),
                    "moyenne": _nombre(r[0]["moyenne"]),
                    "mini": _nombre(r[0]["mini"]), "maxi": _nombre(r[0]["maxi"]),
                })
        candidates_total.sort(key=lambda x: -(x["lignes"] or 0))

    return {"table": table, "colonnes": presentes,
            "colonnes_toutes": sorted(sch.cols(table)),
            "candidates_total": candidates_total, "echantillon": rows,
            "net_plat": net_plat, "formule": montant, "reconstruit": reconstruit,
            "diviseurs": DIVISEUR_UNITE,
            "unites": unites, "unites_inconnues": inconnus, "lourdes": lourdes}


def _diagnostic_complet(conn, sch, table, alias, entete, col_date, depuis):
    d = _diagnostic_prix(conn, sch, table, alias)
    d["comparatif"] = _comparatif_diviseurs(conn, sch, table, alias,
                                            entete, col_date, depuis)
    d["periode"] = depuis
    return d


def _rentre_du_jour(conn, sch, montant, jour):
    """Le détail d'une journée de prise de commande, commande par commande."""
    entete = _lignes(conn, """
        SELECT COUNT(DISTINCT l.numero) AS commandes, COUNT(*) AS lignes,
               COUNT(DISTINCT e.numclt) AS clients, SUM(%s) AS montant
          FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
         WHERE substr(e.amjc,1,10) = ?
    """ % montant, (jour,))
    tete = entete[0] if entete else {}
    champ_clt = "e.rs" if sch.a("cde_entete", "rs") else "''"
    champ_orig = "l.orig" if sch.a("cde_ligne", "orig") else "NULL"
    items = _lignes(conn, """
        SELECT MIN(l.id) AS id, l.numero AS numero, %s AS client, COUNT(*) AS lignes,
               SUM(%s) AS montant, MIN(NULLIF(l.amje,'')) AS expedition,
               MAX(%s) AS origine
          FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
         WHERE substr(e.amjc,1,10) = ?
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
         WHERE substr(e.amjc,1,10) >= ? AND substr(e.amjc,1,10) <= ?
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
    """Les jours OUVRÉS de la période, y compris ceux où rien n'est rentré.

    Un lundi sans commande vaut zéro et doit se voir : la requête ne rend que
    les jours peuplés, et recoller les trous montrerait une activité continue
    là où il y a des creux. Les samedis et dimanches, eux, ne sont pas des
    creux — personne ne prend de commande le week-end. Vingt-deux barres à
    zéro par mois n'apprennent rien et écrasent l'échelle des autres.
    """
    par_jour = {str(r.get("jour") or "")[:10]: _nombre(r.get("montant")) or 0.0
                for r in rows}
    j = date.fromisoformat(debut)
    stop = date.fromisoformat(fin)
    out = []
    while j <= stop:
        if j.weekday() < 5:          # 5 = samedi, 6 = dimanche
            cle = j.isoformat()
            out.append({"jour": cle, "montant": par_jour.get(cle, 0.0)})
        j += timedelta(days=1)
    return out


def _serie_12_mois(conn, sch, m_cde, m_fac, b):
    """Rentré et facturé mois par mois — deux séries, une seule échelle."""
    par_mois = {}

    def _verser(rows, cle):
        for r in rows:
            mois = str(r.get("mois") or "")[:7]
            if len(mois) != 7:
                continue
            par_mois.setdefault(mois, {"mois": mois, "rentre": None, "facture": None})
            par_mois[mois][cle] = _nombre(r.get("montant"))

    if sch.a("cde_entete", "numero", "amjc"):
        _verser(_lignes(conn, """
            SELECT substr(e.amjc, 1, 7) AS mois, SUM(%s) AS montant
              FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
             WHERE substr(e.amjc,1,10) >= ? AND substr(e.amjc,1,10) <= ?
          GROUP BY mois ORDER BY mois
        """ % m_cde, (b["debut_serie"], b["fin_mois"])), "rentre")

    if sch.a("vte_entete", "numero", "amjf"):
        _verser(_lignes(conn, """
            SELECT substr(e.amjf, 1, 7) AS mois, SUM(%s) AS montant
              FROM vte_ligne l JOIN vte_entete e ON e.numero = l.numero
             WHERE substr(e.amjf,1,10) >= ? AND substr(e.amjf,1,10) <= ?
          GROUP BY mois ORDER BY mois
        """ % m_fac, (b["debut_serie"], b["fin_mois"])), "facture")

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

    # Même arithmétique que partout ailleurs : le prix de RVGI est à l'unité
    # de vente, pas à l'étiquette. Oublier le coefficient ici donnait un
    # facturable à 140 millions d'euros pour 18 bons de livraison.
    # La ligne de commande porte son total HT : le reste à facturer en est la
    # fraction non encore facturée. Refaire le calcul de prix ici rejouerait
    # les mêmes hypothèses douteuses sur `pun` et l'unité de vente.
    total_cde = None
    for col in COLS_TOTAL_HT:
        if sch.a("cde_ligne", col):
            total_cde = "COALESCE(c.%s, 0)" % col
            break
    if total_cde:
        valeur = ("CASE WHEN COALESCE(c.qte, 0) > 0 THEN %s * "
                  "((l.qte - COALESCE(l.qtefac, 0)) / c.qte) ELSE NULL END" % total_cde)
    else:
        # Pas de total HT sur la ligne de commande : le facturable n'est pas
        # chiffrable. Le reconstruire à partir de `pun` rejouerait l'erreur
        # d'un facteur mille — on rend le nombre de BL, pas un faux montant.
        valeur = "NULL"
        sortie["indispo"].append(
            "Facturable : aucune colonne de total HT sur cde_ligne")
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
        cond = (" AND " + _date_reelle(_jour("l.amje"))
                + " AND substr(l.amje,1,10) <= ?" + (" AND substr(l.amje,1,10) > ?" if bas else ""))
        params = (haut,) + ((bas,) if bas else ())
        ages.append({
            "label": libelle,
            "montant": _nombre(_un(conn, "SELECT SUM(%s) %s %s" % (valeur, base, cond), params)),
        })
    return {"montant": total, "bl": bl, "ages": ages}
