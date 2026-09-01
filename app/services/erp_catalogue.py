"""Catalogue des écrans ERP — définition déclarative.

Un écran = une table du miroir RVGI, éventuellement jointe à son entête, avec
la liste des colonnes à montrer, ce sur quoi on cherche, ce sur quoi on filtre,
et comment le détail se regroupe. Le moteur générique
(`app/services/erp_mirror.py`) ne connaît que cette structure : ajouter un
écran, c'est ajouter une entrée ici, pas écrire une page.

Les colonnes sont validées contre le miroir réel avant usage
(`adapter_ecran`) : une colonne que RVGI n'expose pas est retirée au lieu de
faire tomber la requête. Le relevé d'inventaire donne le modèle, le miroir
donne la vérité.

Codes RVGI
----------
RVGI affiche ses énumérations sous la forme « 1 - Fabrication ». Les libellés
ne sont dans aucune table : ils sont codés dans l'application WinDev. Ceux
d'ici ont été relevés sur les écrans de l'ERP. Un code inconnu s'affiche brut —
on ne masque jamais une valeur qu'on ne sait pas traduire, ce serait pire que
de montrer le code.
"""

# ── Énumérations relevées sur les écrans RVGI ───────────────────────────────
ENUMS = {
    "origine": {
        "1": "Fabrication",
        "2": "Stock",
        "3": "Sous-traitance",
    },
    "position": {
        "0": "En cours",
        "1": "Partielle",
        "2": "Soldée",
    },
    "colisage": {
        "0": "En cours",
        "1": "Partiel",
        "2": "Terminé",
    },
    "position_facture": {
        "0": "Non facturé",
        "1": "Partiel",
        "2": "Facturé",
    },
    "laboratoire": {
        "1": "Renouvellement",
    },
    "type_produit": {
        "1": "Produits",
        "11": "Clichés",
        "19": "Cartons",
    },
}

# L'ordre et les noms sont ceux de la barre de menus de RVGI — Fichiers,
# Ventes, Stocks, Production, Achats, Comptabilités. Quelqu'un qui passe d'un
# écran à l'autre toute la journée n'a pas à réapprendre où sont les choses.
# `type: parametres` sort un domaine du fil du process : Fichiers regroupe des
# référentiels, pas des étapes de la vie d'une commande. L'affichage le range
# donc en bas, sur toute la largeur, au lieu de lui donner une colonne dans le
# flux.
DOMAINES = [
    {"cle": "fichiers", "label": "Fichiers", "type": "parametres"},
    {"cle": "ventes", "label": "Ventes"},
    {"cle": "stocks", "label": "Stocks"},
    {"cle": "production", "label": "Production"},
    {"cle": "achats", "label": "Achats"},
    {"cle": "comptabilites", "label": "Comptabilités"},
]

# Ordre d'affichage à l'intérieur d'un domaine : celui du flux de RVGI, pas
# celui du catalogue. Un écran absent d'ici passe à la fin de son domaine.
ORDRE_ECRANS = [
    # Fichiers
    "articles", "clients", "fournisseurs", "outils", "machines",
    "prix_vente", "prix_achat", "prix_client",
    # Ventes — le flux : devis, marchés, commandes, livraisons, factures
    "devis", "marches", "commandes", "livraisons", "factures",
    # Stocks
    "stock_pf", "mouvements_pf", "stock_matiere", "mouvements_matiere",
    # Production — ordonnancement, fabrication, déclarations, matière, colisage
    "dossiers", "fiches_fabrication", "declarations", "sorties_matiere", "colisage",
    # Achats — appel d'offres, commande, réception, facture
    "appels_offres", "commandes_fournisseur", "receptions", "factures_fournisseur",
    # Comptabilités
    "echeances",
]


def rang(cle):
    """Position d'un écran dans l'ordre d'affichage."""
    try:
        return ORDRE_ECRANS.index(cle)
    except ValueError:
        return len(ORDRE_ECRANS)

# Libellés des colonnes RVGI qui reviennent partout. Servent au panneau de
# détail, y compris pour les champs qu'aucun écran ne montre en liste.
LABELS = {
    "id": "Identifiant", "numero": "Numéro", "ligne": "Ligne",
    "amjc": "Date de création", "amjd": "Date du devis", "amje": "Date d'expédition",
    "amjl": "Date de livraison", "amjf": "Date de facture", "amjh": "Horodatage",
    "amjv": "Fin de validité", "amj": "Date", "amjb": "Date du BAT",
    "amjo": "Date d'ouverture", "amjp": "Date prévue", "amjr": "Date réelle",
    "dtem": "Dernière modification",
    "numclt": "N° client", "numfou": "N° fournisseur", "numfouclt": "N° tiers",
    "rs": "Raison sociale", "groupeclt": "Groupe client", "groupefou": "Groupe fournisseur",
    "code": "Code", "code1": "Code 1", "code2": "Code 2", "code3": "Code 3",
    "des1": "Désignation", "des2": "Désignation 2", "des3": "Désignation 3",
    "des4": "Désignation 4",
    "libc1": "Libellé 1", "libc2": "Libellé 2", "libc3": "Libellé 3", "libc4": "Libellé 4",
    "cltd1": "Libellé client 1", "cltd2": "Libellé client 2",
    "cltc1": "Réf. client 1", "cltc2": "Réf. client 2", "cltc3": "Réf. client 3",
    "qte": "Quantité", "qtep": "Quantité à traiter", "qtex": "Qtex (sens non établi)",
    "qtef": "Quantité fabriquée", "qtes": "Quantité sortie", "qtefac": "Quantité facturée",
    "qte1": "Quantité mouvementée", "qte2": "Stock après mouvement",
    "qtemin": "Quantité mini", "qtemax": "Quantité maxi",
    "pa": "Prix d'achat", "pv": "Prix de vente", "pub": "Prix unitaire brut",
    "pun": "Prix unitaire net", "net": "Net", "htn": "Total HT net", "htb": "Total HT brut",
    "ttcn": "Total TTC", "tva": "TVA", "rem": "Remise", "mt": "Montant",
    "franco": "Franco", "escompte": "Escompte", "devise": "Devise",
    "fam": "Famille", "sfam": "Sous-famille", "gamme": "Gamme", "nomen": "Nomenclature",
    "depot": "Dépôt", "rang": "Rang", "lot": "N° de lot", "refbl": "Réf. BL",
    "ref": "Référence fournisseur", "vref": "Référence client", "nref": "Notre référence",
    "operateur": "Opérateur", "com": "Commentaire", "mvt": "Type de mouvement",
    "stk": "Stock", "mini": "Stock minimum", "maxi": "Stock maximum",
    "ftl": "Format L", "fth": "Format H", "fta": "Format A",
    "orig": "Origine", "lpos": "Position", "pos": "Position", "lab": "Laboratoire",
    "pcol": "Colisage", "bat": "BAT", "modliv": "Mode de livraison",
    "nbjliv": "Délai (jours)", "numcde": "N° de commande", "lignecde": "Ligne de commande",
    "livbl": "N° de BL", "livno": "N° de commande", "livlg": "Ligne de commande",
    "nofac": "N° de facture", "fac_no": "N° de facture", "fac_lg": "Ligne de facture",
    "sol": "Soldé", "reg": "Mode de règlement", "adv": "Chargé d'affaires",
    "cp": "Code postal", "ville": "Ville", "vil": "Ville", "pays": "Pays",
    "adr1": "Adresse", "adr2": "Adresse (suite)", "mail": "E-mail", "tel": "Téléphone",
    "siret": "SIRET", "ntva": "N° TVA", "lrs": "Livré à", "lville": "Ville de livraison",
    "machine": "Machine", "mach": "Machine", "dos": "Dossier", "pt": "Code opération",
    "nbt": "Nombre de poses", "nbl": "Poses en laize", "nba": "Poses en avance",
    "colis": "Colis", "pds": "Poids", "pal": "Palettes", "col": "Colis",
    "nom": "Nom", "pre": "Prénom", "service": "Service",
}


# ── Les numéros qui identifient, et ceux qui comptent ────────────────────────
#
# Une facture « 26 060 187 » ne se lit pas : c'est un numéro, pas une quantité,
# et le séparateur de milliers en fait un nombre qu'on essaie de comparer à un
# autre. RVGI, WinDev et le client l'écrivent tous « 26060187 » — et c'est cette
# chaîne-là qu'on recopie dans un mail ou qu'on tape dans une recherche.
#
# On ne peut pas le déduire du type SQL : les deux sont des entiers. C'est le
# NOM de la colonne qui dit ce qu'elle est. La liste ci-dessous ne retient donc
# que les numéros de pièce et de ligne — pas les codes de classement (`fam`,
# `depot`, `reg`), qui restent en dessous du millier et n'ont jamais montré de
# séparateur de toute façon.
COLONNES_IDENTITE = {
    "numero", "numcde", "numdev", "numfac", "nofac", "fac_no", "fac_lg",
    "livno", "livbl", "livlg", "numclt", "numfou", "numfouclt", "numart",
    "ligne", "lignecde", "ligneech", "rang", "dos",
}


def _c(ref, nom, label, type="texte", largeur=None, enum=None, aligne=None):
    # Un numéro de pièce déclaré « nombre » est corrigé ici, une fois, plutôt
    # qu'à la main dans les quarante endroits qui le déclarent.
    if type == "nombre" and nom in COLONNES_IDENTITE:
        type = "id"
    d = {"c": ref, "nom": nom, "label": label, "type": type}
    if largeur:
        d["largeur"] = largeur
    if enum:
        d["enum"] = enum
    if aligne:
        d["aligne"] = aligne
    return d


def _article(a, nom="article", label="Réf. article"):
    """Clé article RVGI : `code1`/`code2` affichés « 890/0112 »."""
    return {
        "parts": ["%s.code1" % a, "%s.code2" % a],
        "joint": "/",
        "nom": nom,
        "label": label,
        "type": "ref",
        "largeur": 100,
    }


ECRANS = [
    # ── Ventes ───────────────────────────────────────────────────────────────
    {
        "cle": "devis",
        "label": "Devis",
        "domaine": "ventes",
        "resume": "Lignes de devis et leur entête client.",
        "table": "dev_ligne", "alias": "l",
        "jointures": [{"table": "dev_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("e.amjd", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° devis", "nombre", 90),
            _c("l.ligne", "ligne", "Lg", "nombre", 45),
            _c("e.rs", "client", "Client", "client", 190),
            _c("e.amjd", "date", "Date", "date", 95),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 240),
            _c("l.qte", "qte", "Quantité", "qte", 100),
            _c("l.pun", "pun", "PU net", "prix", 90),
            _c("l.net", "net", "Net", "montant", 100),
            _c("l.amjv", "amjv", "Validité", "date", 95),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero", "l.code1", "l.code2", "l.vref"],
        "filtres": [
            {"nom": "client", "label": "Client", "col": "e.rs", "type": "contient", "exemple": "LIDL"},
            {"nom": "depuis", "label": "Depuis le", "col": "e.amjd", "type": "date_min"},
            {"nom": "jusqua", "label": "Jusqu'au", "col": "e.amjd", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Devis", "champs": ["numero", "ligne", "amjd", "rs", "numclt", "vref"]},
            {"titre": "Article", "champs": ["code1", "code2", "code3", "des1", "des2", "des3", "des4", "fam", "sfam"]},
            {"titre": "Chiffrage", "champs": ["qte", "pub", "pun", "net", "pa", "tva", "rem"]},
        ],
    },
    {
        "cle": "commandes",
        "label": "Commandes",
        "domaine": "ventes",
        "resume": "Le carnet : une ligne par ligne de commande, avec sa date d'expédition et son avancement.",
        "table": "cde_ligne", "alias": "l",
        "jointures": [{"table": "cde_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("l.amje", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° / OF", "of", 90),
            _c("l.ligne", "ligne", "Lg", "nombre", 45),
            _c("e.rs", "client", "Client", "client", 190),
            _c("e.amjc", "date", "Créée le", "date", 95),
            _c("l.amje", "amje", "Expédition", "date", 95),
            _c("l.amjl", "amjl", "Livraison", "date", 95),
            _c("l.lpos", "lpos", "Position", "enum", 110, enum="position"),
            _c("l.orig", "orig", "Origine", "enum", 110, enum="origine"),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 240),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.qtep", "qtep", "À traiter", "qte", 105),
            _c("l.pun", "pun", "PU net", "prix", 85),
            _c("l.bat", "bat", "BAT", "bool", 55),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero", "l.code1", "l.code2", "l.vref", "l.nref"],
        "filtres": [
            {"nom": "client", "label": "Client", "col": "e.rs", "type": "contient", "exemple": "LIDL"},
            # Un carnet s'ouvre sur ce qui est en cours, pas sur dix ans
            # d'archives : le filtre est posé d'entrée, et reste effaçable.
            #
            # « En cours » seul, et non « non soldée », après mesure le
            # 28/08/2026 : les 91 lignes « Partielle » du miroir se lisent 10
            # de 2026 — celles que l'écran de RVGI montre — et 81 de 2015 à
            # 2024, sans le moindre BL, dont `orig` et `prod` valent 255, la
            # sentinelle « non renseigné ». Ce sont des reliquats d'avant les
            # champs que RVGI utilise aujourd'hui. Les faire entrer par défaut
            # remplacerait un bruit par un autre. Le choix composé reste offert
            # dans le rail pour qui veut les deux positions.
            {"nom": "position", "label": "Position", "col": "l.lpos", "type": "enum",
             "enum": "position", "defaut": "0",
             "choix": [{"v": "0|1", "label": "Non soldée (en cours ou partielle)"}]},
            {"nom": "origine", "label": "Origine", "col": "l.orig", "type": "enum", "enum": "origine"},
            {"nom": "depuis", "label": "Expédition depuis", "col": "l.amje", "type": "date_min"},
            {"nom": "jusqua", "label": "Expédition jusqu'au", "col": "l.amje", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Commande", "champs": ["numero", "ligne", "amjc", "rs", "numclt", "groupeclt", "vref", "nref"]},
            {"titre": "Échéances", "champs": ["amje", "amjl", "nbjliv", "modliv", "lpos", "bat", "amjb"]},
            {"titre": "Article", "champs": ["code1", "code2", "code3", "des1", "des2", "des3", "des4", "fam", "sfam", "gamme"]},
            {"titre": "Quantités et prix", "champs": ["qte", "qtep", "qtex", "pub", "pun", "net", "pa", "orig", "lab", "pcol"]},
            {"titre": "Livraison", "champs": ["lrs", "ladr1", "ladr2", "lcp", "lville", "lpays"]},
        ],
    },
    {
        "cle": "livraisons",
        "label": "Bons de livraison",
        "domaine": "ventes",
        "resume": "Lignes de BL, rattachées à leur commande d'origine.",
        "table": "liv_ligne", "alias": "l",
        "jointures": [{"table": "liv_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("l.amje", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° BL", "nombre", 90),
            _c("e.lrs", "client", "Livré à", "client", 190),
            _c("e.numclt", "numclt", "N° client", "nombre", 80),
            _c("l.amje", "amje", "Expédié le", "date", 95),
            _c("l.numcde", "numcde", "Commande", "of", 90),
            _c("l.lignecde", "lignecde", "Lg cde", "nombre", 60),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.qtefac", "qtefac", "Facturée", "qte", 100),
            _c("l.pds", "pds", "Poids", "nombre", 80),
            _c("l.fac_no", "fac_no", "Facture", "nombre", 90),
        ],
        "recherche": ["e.lrs", "l.numero", "l.numcde", "l.note"],
        "filtres": [
            {"nom": "client", "label": "Destinataire", "col": "e.lrs", "type": "contient", "exemple": "LIDL"},
            {"nom": "commande", "label": "N° de commande", "col": "l.numcde", "type": "egal", "exemple": "9932399"},
            {"nom": "depuis", "label": "Depuis le", "col": "l.amje", "type": "date_min"},
            {"nom": "jusqua", "label": "Jusqu'au", "col": "l.amje", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Bon de livraison", "champs": ["numero", "amje", "lrs", "numclt", "col", "pal", "pds", "modliv"]},
            {"titre": "Origine", "champs": ["numcde", "lignecde", "lpos"]},
            {"titre": "Quantités", "champs": ["qte", "qtefac", "depot"]},
            {"titre": "Facturation", "champs": ["fac_no", "fac_lg"]},
        ],
    },
    {
        "cle": "factures",
        "label": "Factures de vente",
        "domaine": "ventes",
        "resume": "Ce qui a réellement été vendu, par référence, depuis 2015.",
        "table": "vte_ligne", "alias": "l",
        "jointures": [{"table": "vte_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("e.amjf", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° facture", "nombre", 100),
            _c("e.rs", "client", "Client", "client", 190),
            _c("e.amjf", "amjf", "Date", "date", 95),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 240),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.pun", "pun", "PU net", "prix", 90),
            _c("l.net", "net", "Net", "montant", 100),
            _c("l.livbl", "livbl", "BL", "nombre", 85),
            _c("l.livno", "livno", "Commande", "of", 90),
            _c("l.mach", "mach", "Machine", "texte", 90),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero", "l.code1", "l.code2", "l.livno"],
        "filtres": [
            {"nom": "client", "label": "Client", "col": "e.rs", "type": "contient", "exemple": "LIDL"},
            {"nom": "commande", "label": "N° de commande", "col": "l.livno", "type": "egal", "exemple": "9932399"},
            {"nom": "depuis", "label": "Depuis le", "col": "e.amjf", "type": "date_min"},
            {"nom": "jusqua", "label": "Jusqu'au", "col": "e.amjf", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Facture", "champs": ["numero", "amjf", "rs", "numclt", "ligne"]},
            {"titre": "Article", "champs": ["code1", "code2", "code3", "des1", "des2", "des3", "des4", "fam", "sfam"]},
            {"titre": "Montants", "champs": ["qte", "pub", "pun", "net", "htn", "tva", "ttcn", "pa"]},
            {"titre": "Rattachement", "champs": ["livbl", "livno", "livlg", "mach"]},
        ],
    },
    {
        "cle": "echeances",
        "label": "Échéances clients",
        "domaine": "comptabilites",
        "resume": "Échéancier des factures de vente, soldé ou non.",
        "table": "ecc_ech", "alias": "l",
        "cle_ligne": "l.id",
        "tri_defaut": ("l.amje", "desc"),
        "colonnes": [
            _c("l.nofac", "nofac", "Facture", "nombre", 100),
            _c("l.rs", "client", "Client", "client", 200),
            _c("l.amje", "amje", "Échéance", "date", 100),
            _c("l.mt", "mt", "Montant", "montant", 110),
            _c("l.sol", "sol", "Soldé", "bool", 70),
            _c("l.ligneech", "ligneech", "Éch.", "nombre", 55),
            _c("l.nbech", "nbech", "Nb éch.", "nombre", 65),
            _c("l.reg", "reg", "Règlement", "nombre", 90),
            _c("l.ville", "ville", "Ville", "texte", 140),
        ],
        "recherche": ["l.rs", "l.nofac", "l.com"],
        "filtres": [
            {"nom": "client", "label": "Client", "col": "l.rs", "type": "contient", "exemple": "LIDL"},
            {"nom": "solde", "label": "Soldé", "col": "l.sol", "type": "enum", "enum": "oui_non"},
            {"nom": "depuis", "label": "Échéance depuis", "col": "l.amje", "type": "date_min"},
            {"nom": "jusqua", "label": "Échéance jusqu'au", "col": "l.amje", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Échéance", "champs": ["nofac", "amje", "mt", "sol", "ligneech", "nbech"]},
            {"titre": "Client", "champs": ["rs", "numclt", "ville", "cp", "reg"]},
        ],
    },
    {
        "cle": "marches",
        "label": "Marchés",
        "domaine": "ventes",
        "resume": "Marchés et appels de livraison.",
        "table": "cdm_ligne", "alias": "l",
        "jointures": [{"table": "cdm_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("e.amjc", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° marché", "nombre", 95),
            _c("l.ligne", "ligne", "Lg", "nombre", 45),
            _c("e.rs", "client", "Client", "client", 190),
            _c("e.amjc", "amjc", "Créé le", "date", 95),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 240),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.qtep", "qtep", "Livrée", "qte", 100),
            _c("l.amjf", "amjf", "Fin", "date", 95),
            _c("l.pun", "pun", "PU net", "prix", 90),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero", "l.code1", "l.code2"],
        "filtres": [
            {"nom": "client", "label": "Client", "col": "e.rs", "type": "contient", "exemple": "LIDL"},
            {"nom": "depuis", "label": "Depuis le", "col": "e.amjc", "type": "date_min"},
        ],
        "detail": [
            {"titre": "Marché", "champs": ["numero", "ligne", "amjc", "amjo", "amjf", "rs", "numclt"]},
            {"titre": "Article", "champs": ["code1", "code2", "des1", "des2", "fam", "sfam"]},
            {"titre": "Quantités", "champs": ["qte", "qtep", "pub", "pun", "net"]},
        ],
    },

    # ── Achats ───────────────────────────────────────────────────────────────
    {
        "cle": "commandes_fournisseur",
        "label": "Commandes fournisseurs",
        "domaine": "achats",
        "resume": "Achats matière, sous-traitance, clichés et fournitures.",
        "table": "cdf_ligne", "alias": "l",
        "jointures": [{"table": "cdf_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("e.amjc", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° cde", "nombre", 85),
            _c("l.ligne", "ligne", "Lg", "nombre", 45),
            _c("e.rs", "fournisseur", "Fournisseur", "client", 190),
            _c("e.amjc", "amjc", "Créée le", "date", 95),
            _c("l.amjl", "amjl", "Livraison", "date", 95),
            _c("l.lpos", "lpos", "Position", "enum", 110, enum="position"),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 240),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.pa", "pa", "Prix d'achat", "prix", 100),
            _c("e.vref", "vref", "Référence", "texte", 180),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero", "l.code1", "l.code2", "e.vref"],
        "filtres": [
            {"nom": "fournisseur", "label": "Fournisseur", "col": "e.rs", "type": "contient", "exemple": "QRT"},
            {"nom": "position", "label": "Position", "col": "l.lpos", "type": "enum",
             "enum": "position", "defaut": "0",
             "choix": [{"v": "0|1", "label": "Non soldée (en cours ou partielle)"}]},
            {"nom": "depuis", "label": "Depuis le", "col": "e.amjc", "type": "date_min"},
        ],
        "detail": [
            {"titre": "Commande", "champs": ["numero", "ligne", "amjc", "amjl", "rs", "numfou", "vref", "lpos"]},
            {"titre": "Article", "champs": ["code1", "code2", "code3", "des1", "des2", "des3", "fam", "sfam"]},
            {"titre": "Quantités et prix", "champs": ["qte", "qtb", "metb", "pa", "pun", "net", "cua"]},
        ],
    },
    {
        "cle": "receptions",
        "label": "Réceptions",
        "domaine": "achats",
        "resume": "Lignes de réception fournisseur, avec le n° de BL et le lot.",
        "table": "lif_ligne", "alias": "l",
        # Facultative, et c'est voulu : `cdf_entete` n'est pas l'entête du bon
        # de réception, c'est la commande fournisseur qui l'a déclenché. Une
        # réception sans commande reste une réception.
        "jointures": [{"table": "cdf_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero"}],
        "cle_ligne": "l.id",
        "tri_defaut": ("l.amjl", "desc"),
        "colonnes": [
            _c("l.ref", "ref", "Référence BR", "code", 130),
            _c("l.numero", "numero", "Commande", "nombre", 90),
            _c("l.ligne", "ligne", "Lg", "nombre", 45),
            _c("l.amjl", "amjl", "Réception", "date", 100),
            _c("e.rs", "fournisseur", "Fournisseur", "client", 190),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.lot", "lot", "N° de lot", "code", 120),
            _c("l.depot", "depot", "Dépôt", "nombre", 70),
            _c("l.fac_no", "fac_no", "Facture", "nombre", 90),
            _c("l.operateur", "operateur", "Opérateur", "nombre", 80),
        ],
        "recherche": ["l.ref", "l.numero", "l.lot", "e.rs", "l.note"],
        "filtres": [
            {"nom": "fournisseur", "label": "Fournisseur", "col": "e.rs", "type": "contient", "exemple": "QRT"},
            {"nom": "lot", "label": "N° de lot", "col": "l.lot", "type": "contient", "exemple": "BL137434"},
            {"nom": "depuis", "label": "Réception depuis", "col": "l.amjl", "type": "date_min"},
            {"nom": "jusqua", "label": "Réception jusqu'au", "col": "l.amjl", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Réception", "champs": ["ref", "amjl", "amje", "qte", "lot", "depot", "operateur"]},
            {"titre": "Commande", "champs": ["numero", "ligne", "rs", "numfou", "lpos"]},
            {"titre": "Facturation", "champs": ["fac_no", "fac_lg", "daa"]},
            {"titre": "Notes", "champs": ["note", "note2", "com"]},
        ],
    },
    {
        "cle": "factures_fournisseur",
        "label": "Factures fournisseurs",
        "domaine": "achats",
        "resume": "Lignes de facture d'achat.",
        "table": "vtf_ligne", "alias": "l",
        "jointures": [{"table": "vtf_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("e.amjf", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N° facture", "nombre", 100),
            _c("e.rs", "fournisseur", "Fournisseur", "client", 190),
            _c("e.amjf", "amjf", "Date", "date", 95),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 240),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.pa", "pa", "Prix d'achat", "prix", 100),
            _c("l.net", "net", "Net", "montant", 100),
            _c("l.livno", "livno", "Commande", "nombre", 90),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero", "l.code1", "l.code2"],
        "filtres": [
            {"nom": "fournisseur", "label": "Fournisseur", "col": "e.rs", "type": "contient", "exemple": "QRT"},
            {"nom": "depuis", "label": "Depuis le", "col": "e.amjf", "type": "date_min"},
        ],
        "detail": [
            {"titre": "Facture", "champs": ["numero", "amjf", "rs", "numfou", "ligne"]},
            {"titre": "Article", "champs": ["code1", "code2", "des1", "des2", "fam", "sfam"]},
            {"titre": "Montants", "champs": ["qte", "pa", "pun", "net", "htn", "tva", "ttcn"]},
        ],
    },
    {
        "cle": "appels_offres",
        "label": "Appels d'offres",
        "domaine": "achats",
        "resume": "Consultations fournisseurs. Module arrêté depuis mars 2025.",
        "table": "aof_ligne", "alias": "l",
        "jointures": [{"table": "aof_entete", "alias": "e",
                       "gauche": "e.numero", "droite": "l.numero",
                       "obligatoire": True}],
        "cle_ligne": "l.id",
        "tri_defaut": ("e.amjc", "desc"),
        "colonnes": [
            _c("l.numero", "numero", "N°", "nombre", 85),
            _c("e.rs", "fournisseur", "Fournisseur", "client", 190),
            _c("e.amjc", "amjc", "Date", "date", 95),
            _article("l"),
            _c("l.des1", "des1", "Désignation", "texte", 260),
            _c("l.qte", "qte", "Quantité", "qte", 110),
            _c("l.pa", "pa", "Prix d'achat", "prix", 100),
        ],
        "recherche": ["e.rs", "l.des1", "l.numero"],
        "filtres": [
            {"nom": "fournisseur", "label": "Fournisseur", "col": "e.rs", "type": "contient", "exemple": "QRT"},
        ],
        "detail": [
            {"titre": "Appel d'offres", "champs": ["numero", "ligne", "amjc", "rs", "numfou"]},
            {"titre": "Article", "champs": ["code1", "code2", "des1", "des2", "qte", "pa"]},
        ],
    },

    # ── Stocks ───────────────────────────────────────────────────────────────
    {
        "cle": "stock_pf",
        "label": "Stock produits finis",
        "domaine": "stocks",
        "resume": "Fiche stock d'un article : suivi, seuils. La QUANTITÉ vit dans les mouvements.",
        "table": "fic_art", "alias": "a",
        "cle_ligne": "a.id",
        "tri_defaut": ("a.code1", "asc"),
        "colonnes": [
            _article("a"),
            _c("a.code3", "code3", "Code 3", "code", 80),
            _c("a.numclt", "numclt", "Client", "nombre", 75),
            _c("a.libc1", "libc1", "Désignation", "texte", 260),
            # `stk` ne vaut que 1 ou 2 sur les 7 679 articles : c'est un
            # indicateur de suivi, PAS une quantité. L'afficher en « Stock
            # réel » faisait lire « 2 étiquettes » là où il y en a deux
            # millions. La quantité réelle est `qte2` du dernier mouvement de
            # `stk_hist` — voir `erp_stock.py`.
            _c("a.stk", "stk", "Suivi en stock", "nombre", 110),
            _c("a.mini", "mini", "Minimum", "qte", 95),
            _c("a.maxi", "maxi", "Maximum", "qte", 95),
            _c("a.ftl", "ftl", "Format L", "nombre", 85),
            _c("a.fth", "fth", "Format H", "nombre", 85),
            _c("a.cltc1", "cltc1", "Réf. client", "code", 120),
        ],
        "recherche": ["a.libc1", "a.libc2", "a.code1", "a.code2", "a.cltc1", "a.cltc2"],
        "filtres": [
            {"nom": "client", "label": "N° client", "col": "a.numclt", "type": "egal", "exemple": "890"},
            {"nom": "famille", "label": "Famille", "col": "a.fam", "type": "egal", "exemple": "2"},
            {"nom": "designation", "label": "Désignation", "col": "a.libc1", "type": "contient", "exemple": "étiquette 45 x 25"},
        ],
        "detail": [
            {"titre": "Article", "champs": ["code1", "code2", "code3", "numclt", "numart", "libc1", "libc2", "libc3", "libc4"]},
            {"titre": "Stock", "champs": ["stk", "mini", "maxi", "depot", "rang", "pstk"]},
            {"titre": "Format et poids", "champs": ["ftl", "fth", "pdsn", "pdsb", "coul", "cliche"]},
            {"titre": "Classement", "champs": ["fam", "sfam", "gamme", "nomen", "douane"]},
            {"titre": "Références client", "champs": ["cltc1", "cltc2", "cltc3", "cltd1", "cltd2", "cltd3", "cltd4"]},
        ],
    },
    {
        "cle": "mouvements_pf",
        "label": "Mouvements produits finis",
        "domaine": "stocks",
        "resume": "Entrées et sorties de stock PF, à la minute.",
        "table": "stk_hist", "alias": "m",
        "cle_ligne": "m.id",
        "tri_defaut": ("m.amjh", "desc"),
        "colonnes": [
            _c("m.amjh", "amjh", "Horodatage", "datetime", 140),
            _article("m"),
            _c("m.code3", "code3", "Code 3", "code", 80),
            _c("m.des1", "des1", "Libellé", "texte", 240),
            _c("m.mvt", "mvt", "Mouvement", "nombre", 90),
            _c("m.qte1", "qte1", "Quantité", "qte", 110),
            _c("m.qte2", "qte2", "Stock après", "qte", 110),
            _c("m.numcde", "numcde", "Commande", "of", 95),
            _c("m.refbl", "refbl", "BL", "code", 95),
            _c("m.lot", "lot", "Lot", "code", 110),
            _c("m.numfouclt", "numfouclt", "Tiers", "nombre", 75),
        ],
        "recherche": ["m.des1", "m.des2", "m.code1", "m.code2", "m.numcde", "m.lot", "m.refbl"],
        "filtres": [
            {"nom": "article", "label": "Code 1", "col": "m.code1", "type": "egal", "exemple": "890"},
            {"nom": "commande", "label": "N° de commande", "col": "m.numcde", "type": "egal", "exemple": "9932399"},
            {"nom": "depuis", "label": "Depuis le", "col": "m.amjh", "type": "date_min"},
            {"nom": "jusqua", "label": "Jusqu'au", "col": "m.amjh", "type": "date_max"},
        ],
        "detail": [
            {"titre": "Mouvement", "champs": ["amjh", "mvt", "qte1", "qte2", "depot", "rang", "operateur"]},
            {"titre": "Article", "champs": ["code1", "code2", "code3", "des1", "des2"]},
            {"titre": "Rattachement", "champs": ["numcde", "ligne", "refbl", "lot", "numfouclt"]},
        ],
    },
    {
        "cle": "stock_matiere",
        "label": "Stock matières",
        "domaine": "stocks",
        "resume": "Stock matière par référence et par laize.",
        "table": "mat_mat", "alias": "m",
        "cle_ligne": "m.id",
        "tri_defaut": ("m.code1", "asc"),
        "colonnes": [
            _article("m"),
            _c("m.libc1", "libc1", "Désignation", "texte", 280),
            _c("m.libc2", "libc2", "Complément", "texte", 200),
            _c("m.stk", "stk", "Stock", "qte", 110),
            _c("m.mini", "mini", "Minimum", "qte", 95),
            _c("m.maxi", "maxi", "Maximum", "qte", 95),
            _c("m.pds", "pds", "Grammage", "nombre", 90),
            _c("m.pa", "pa", "Prix d'achat", "prix", 100),
            _c("m.numfou", "numfou", "Fournisseur", "nombre", 90),
        ],
        "recherche": ["m.libc1", "m.libc2", "m.code1", "m.code2", "m.ref"],
        "filtres": [
            {"nom": "designation", "label": "Désignation", "col": "m.libc1", "type": "contient", "exemple": "velin"},
            {"nom": "famille", "label": "Sous-famille", "col": "m.sfam", "type": "egal", "exemple": "1"},
        ],
        "detail": [
            {"titre": "Matière", "champs": ["code1", "code2", "code3", "libc1", "libc2", "sfam", "nomen"]},
            {"titre": "Caractéristiques", "champs": ["m1_lai", "m1_epais", "m1_adh", "m1_pro", "m1_syn", "m1_film", "m1_abs", "coul", "pds"]},
            {"titre": "Stock", "champs": ["stk", "mini", "maxi", "depot", "rang"]},
            {"titre": "Achat", "champs": ["numfou", "ref", "pa", "cua", "cuc", "amjv"]},
        ],
    },
    {
        "cle": "mouvements_matiere",
        "label": "Mouvements matières",
        "domaine": "stocks",
        "resume": "Entrées et sorties matière, la laize portée par le code 3.",
        "table": "stm_hist", "alias": "m",
        "cle_ligne": "m.id",
        "tri_defaut": ("m.amjh", "desc"),
        "colonnes": [
            _c("m.amjh", "amjh", "Horodatage", "datetime", 140),
            _article("m"),
            _c("m.code3", "code3", "Laize", "code", 80),
            _c("m.des1", "des1", "Libellé", "texte", 260),
            _c("m.mvt", "mvt", "Mouvement", "nombre", 90),
            _c("m.qte1", "qte1", "Quantité", "qte", 110),
            _c("m.qte2", "qte2", "Stock après", "qte", 110),
            _c("m.numcde", "numcde", "Commande", "nombre", 95),
            _c("m.lot", "lot", "Lot", "code", 110),
        ],
        "recherche": ["m.des1", "m.des2", "m.code1", "m.code2", "m.lot", "m.refbl"],
        "filtres": [
            {"nom": "article", "label": "Code 1", "col": "m.code1", "type": "egal", "exemple": "890"},
            {"nom": "lot", "label": "N° de lot", "col": "m.lot", "type": "contient", "exemple": "BL137434"},
            {"nom": "depuis", "label": "Depuis le", "col": "m.amjh", "type": "date_min"},
        ],
        "detail": [
            {"titre": "Mouvement", "champs": ["amjh", "mvt", "qte1", "qte2", "depot", "rang", "operateur"]},
            {"titre": "Matière", "champs": ["code1", "code2", "code3", "des1", "des2"]},
            {"titre": "Rattachement", "champs": ["numcde", "ligne", "refbl", "lot", "numfouclt"]},
        ],
    },

    # ── Référentiels ─────────────────────────────────────────────────────────
    {
        "cle": "articles",
        "label": "Articles",
        "domaine": "fichiers",
        "resume": "Le référentiel produits finis : libellés, formats, classement.",
        "table": "fic_art", "alias": "a",
        "cle_ligne": "a.id",
        "tri_defaut": ("a.code1", "asc"),
        "colonnes": [
            _article("a"),
            _c("a.code3", "code3", "Code 3", "code", 80),
            _c("a.libc1", "libc1", "Libellé 1", "texte", 240),
            _c("a.libc2", "libc2", "Libellé 2", "texte", 220),
            _c("a.libc3", "libc3", "Libellé 3", "texte", 180),
            _c("a.fam", "fam", "Famille", "nombre", 80),
            _c("a.sfam", "sfam", "Sous-famille", "nombre", 90),
            _c("a.ftl", "ftl", "Format L", "nombre", 85),
            _c("a.fth", "fth", "Format H", "nombre", 85),
            _c("a.amj", "amj", "Créé le", "date", 95),
        ],
        "recherche": ["a.libc1", "a.libc2", "a.libc3", "a.code1", "a.code2", "a.cltc1", "a.numart"],
        "filtres": [
            {"nom": "client", "label": "N° client", "col": "a.numclt", "type": "egal", "exemple": "890"},
            {"nom": "famille", "label": "Famille", "col": "a.fam", "type": "egal", "exemple": "2"},
            {"nom": "libelle", "label": "Libellé", "col": "a.libc1", "type": "contient", "exemple": "étiquette 45 x 25"},
        ],
        "detail": [
            {"titre": "Article", "champs": ["code1", "code2", "code3", "numart", "numclt", "amj"]},
            {"titre": "Libellés", "champs": ["libc1", "libc2", "libc3", "libc4"]},
            {"titre": "Côté client", "champs": ["cltc1", "cltc2", "cltc3", "cltd1", "cltd2", "cltd3", "cltd4"]},
            {"titre": "Format et poids", "champs": ["ftl", "fth", "pdsn", "pdsb", "coul", "cliche"]},
            {"titre": "Classement", "champs": ["fam", "sfam", "gamme", "nomen", "douane", "cua", "cuv", "cuc"]},
        ],
    },
    {
        "cle": "clients",
        "label": "Clients",
        "domaine": "fichiers",
        "resume": "Fiches clients : identité, groupe, conditions.",
        "table": "fic_clt", "alias": "c",
        "cle_ligne": "c.id",
        "tri_defaut": ("c.rs", "asc"),
        "colonnes": [
            _c("c.numero", "numero", "N°", "nombre", 70),
            _c("c.code", "code", "Code", "code", 110),
            _c("c.rs", "rs", "Raison sociale", "client", 240),
            _c("c.vil", "vil", "Ville", "texte", 160),
            _c("c.cp", "cp", "CP", "code", 80),
            _c("c.groupe", "groupe", "Groupe", "nombre", 80),
            _c("c.tel", "tel", "Téléphone", "texte", 120),
            _c("c.nbjliv", "nbjliv", "Délai", "nombre", 70),
            _c("c.reg", "reg", "Règlement", "nombre", 90),
            _c("c.bloq", "bloq", "Bloqué", "bool", 70),
        ],
        "recherche": ["c.rs", "c.code", "c.vil", "c.siret", "c.numero"],
        "filtres": [
            {"nom": "ville", "label": "Ville", "col": "c.vil", "type": "contient", "exemple": "ROUBAIX"},
            {"nom": "groupe", "label": "Groupe", "col": "c.groupe", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Identité", "champs": ["numero", "code", "rs", "groupe", "siret", "ntva", "rcs", "ean"]},
            {"titre": "Adresse", "champs": ["adr1", "adr2", "bp", "cp", "vil", "pays", "cpays"]},
            {"titre": "Contact", "champs": ["tel", "fax", "mail", "http"]},
            {"titre": "Conditions", "champs": ["modeliv", "nbjliv", "franco", "remise", "escompte", "reg", "del", "dev", "lang", "adv"]},
        ],
    },
    {
        "cle": "fournisseurs",
        "label": "Fournisseurs",
        "domaine": "fichiers",
        "resume": "Fiches fournisseurs : identité, groupe, conditions.",
        "table": "fic_fou", "alias": "f",
        "cle_ligne": "f.id",
        "tri_defaut": ("f.rs", "asc"),
        "colonnes": [
            _c("f.numero", "numero", "N°", "nombre", 70),
            _c("f.code", "code", "Code", "code", 110),
            _c("f.rs", "rs", "Raison sociale", "client", 240),
            _c("f.vil", "vil", "Ville", "texte", 160),
            _c("f.cp", "cp", "CP", "code", 80),
            _c("f.groupe", "groupe", "Groupe", "nombre", 80),
            _c("f.tel", "tel", "Téléphone", "texte", 120),
            _c("f.nbjliv", "nbjliv", "Délai", "nombre", 70),
            _c("f.bloq", "bloq", "Bloqué", "bool", 70),
        ],
        "recherche": ["f.rs", "f.code", "f.vil", "f.siret", "f.numero"],
        "filtres": [
            {"nom": "ville", "label": "Ville", "col": "f.vil", "type": "contient", "exemple": "ROUBAIX"},
            {"nom": "groupe", "label": "Groupe", "col": "f.groupe", "type": "egal", "exemple": "1092"},
        ],
        "detail": [
            {"titre": "Identité", "champs": ["numero", "code", "rs", "groupe", "siret", "ntva", "rcs"]},
            {"titre": "Adresse", "champs": ["adr1", "adr2", "bp", "cp", "vil", "pays", "cpays"]},
            {"titre": "Contact", "champs": ["tel", "fax", "mail", "http"]},
            {"titre": "Conditions", "champs": ["modeliv", "nbjliv", "franco", "remise", "escompte", "reg", "dev", "lang"]},
        ],
    },
    {
        "cle": "outils",
        "label": "Outils de découpe",
        "domaine": "fichiers",
        "resume": "Outils physiques. `nbt` est le nombre de poses qui fait foi.",
        "table": "out_dec", "alias": "o",
        "cle_ligne": "o.id",
        "tri_defaut": ("o.numero", "desc"),
        "colonnes": [
            _c("o.numero", "numero", "N° outil", "nombre", 90),
            _c("o.code", "code", "Code", "code", 110),
            _c("o.machine", "machine", "Machine", "texte", 110),
            _c("o.ftl", "ftl", "Format L", "nombre", 85),
            _c("o.fta", "fta", "Format A", "nombre", 85),
            _c("o.nbl", "nbl", "Poses laize", "nombre", 90),
            _c("o.nba", "nba", "Poses avance", "nombre", 95),
            _c("o.nbt", "nbt", "Poses (total)", "nombre", 100),
            _c("o.numclt", "numclt", "Client", "nombre", 75),
            _c("o.etat", "etat", "État", "nombre", 70),
        ],
        "recherche": ["o.code", "o.numero", "o.com", "o.machine"],
        "filtres": [
            {"nom": "machine", "label": "Machine", "col": "o.machine", "type": "contient", "exemple": "COHESIO"},
            {"nom": "client", "label": "N° client", "col": "o.numclt", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Outil", "champs": ["numero", "code", "machine", "etat", "forme", "amj"]},
            {"titre": "Poses", "champs": ["nbl", "nba", "nbt", "nbeti", "espl", "espa", "eche"]},
            {"titre": "Format", "champs": ["ftl", "fta", "lt", "at", "ft", "nbd", "ray", "qm"]},
            {"titre": "Rattachement", "champs": ["numclt", "rclt", "depot", "rang", "com"]},
        ],
    },
    {
        "cle": "machines",
        "label": "Machines",
        "domaine": "fichiers",
        "resume": "Parc machines et capacités déclarées dans l'ERP.",
        "table": "mac_pro", "alias": "m",
        "cle_ligne": "m.id",
        "tri_defaut": ("m.code", "asc"),
        "colonnes": [
            _c("m.code", "code", "Code", "code", 90),
            _c("m.nom", "nom", "Machine", "texte", 200),
            _c("m.lai", "lai", "Laize max", "nombre", 100),
            _c("m.nbcoul", "nbcoul", "Couleurs", "nombre", 90),
            _c("m.vit", "vit", "Vitesse", "nombre", 90),
            _c("m.tht", "tht", "Taux horaire", "prix", 110),
            _c("m.thd", "thd", "Taux dorure", "prix", 110),
            _c("m.nbout", "nbout", "Outils", "nombre", 80),
        ],
        "recherche": ["m.nom", "m.code", "m.com"],
        "filtres": [],
        "detail": [
            {"titre": "Machine", "champs": ["code", "nom", "type", "lai", "nbcoul", "nbpap", "nbout", "vit", "tvit"]},
            {"titre": "Taux horaires", "champs": ["tht", "thd", "ths", "cci", "ccd", "ccg", "ce", "pe", "cs", "ps"]},
        ],
    },
    {
        "cle": "prix_vente",
        "label": "Prix de vente",
        "domaine": "fichiers",
        "resume": "Paliers de prix de vente par article.",
        "table": "fic_artv", "alias": "p",
        "cle_ligne": "p.id",
        "tri_defaut": ("p.code1", "asc"),
        "colonnes": [
            _article("p"),
            _c("p.code3", "code3", "Code 3", "code", 80),
            _c("p.qtemin", "qtemin", "Quantité mini", "qte", 110),
            _c("p.qtemax", "qtemax", "Quantité maxi", "qte", 110),
            _c("p.pv", "pv", "Prix de vente", "prix", 110),
            _c("p.amj", "amj", "Depuis le", "date", 95),
            _c("p.amjv", "amjv", "Validité", "date", 95),
        ],
        "recherche": ["p.code1", "p.code2"],
        "filtres": [
            {"nom": "article", "label": "Code 1", "col": "p.code1", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Palier", "champs": ["code1", "code2", "code3", "qtemin", "qtemax", "pv", "amj", "amjv", "grille", "cuv"]},
        ],
    },
    {
        "cle": "prix_achat",
        "label": "Prix d'achat",
        "domaine": "fichiers",
        "resume": "Prix d'achat par article et par fournisseur.",
        "table": "fic_arta", "alias": "p",
        "cle_ligne": "p.id",
        "tri_defaut": ("p.code1", "asc"),
        "colonnes": [
            _article("p"),
            _c("p.numfou", "numfou", "Fournisseur", "nombre", 100),
            _c("p.ref", "ref", "Réf. fournisseur", "code", 140),
            _c("p.qtemin", "qtemin", "Quantité mini", "qte", 110),
            _c("p.qtemax", "qtemax", "Quantité maxi", "qte", 110),
            _c("p.pa", "pa", "Prix d'achat", "prix", 110),
            _c("p.def", "def", "Par défaut", "bool", 90),
            _c("p.amjv", "amjv", "Validité", "date", 95),
        ],
        "recherche": ["p.code1", "p.code2", "p.ref", "p.libt1"],
        "filtres": [
            {"nom": "fournisseur", "label": "N° fournisseur", "col": "p.numfou", "type": "egal", "exemple": "1092"},
            {"nom": "article", "label": "Code 1", "col": "p.code1", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Prix d'achat", "champs": ["code1", "code2", "code3", "numfou", "ref", "qtemin", "qtemax", "pa", "def", "amj", "amjv", "cua", "cuc"]},
        ],
    },
    {
        "cle": "prix_client",
        "label": "Prix négociés client",
        "domaine": "fichiers",
        "resume": "Prix négociés par client, avec la référence de son côté.",
        "table": "fic_artc", "alias": "p",
        "cle_ligne": "p.id",
        "tri_defaut": ("p.code1", "asc"),
        "colonnes": [
            _article("p"),
            _c("p.numclt", "numclt", "Client", "nombre", 85),
            _c("p.cltc2", "cltc2", "Réf. client", "code", 140),
            _c("p.qtemin", "qtemin", "Quantité mini", "qte", 110),
            _c("p.qtemax", "qtemax", "Quantité maxi", "qte", 110),
            _c("p.pv", "pv", "Prix négocié", "prix", 110),
            _c("p.amjd", "amjd", "Depuis le", "date", 95),
            _c("p.amjv", "amjv", "Validité", "date", 95),
        ],
        "recherche": ["p.code1", "p.code2", "p.cltc2", "p.libc1"],
        "filtres": [
            {"nom": "client", "label": "N° client", "col": "p.numclt", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Prix négocié", "champs": ["code1", "code2", "code3", "numclt", "cltc1", "cltc2", "cltc3", "libc1", "libc2", "qtemin", "qtemax", "pv", "amjd", "amjv"]},
        ],
    },

    # ── Production (historique) ──────────────────────────────────────────────
    {
        "cle": "fiches_fabrication",
        "label": "Fiches de fabrication",
        "domaine": "production",
        "resume": "L'équivalent RVGI des fiches techniques : machines, matières, outils, carton.",
        "table": "gpr_ff", "alias": "f",
        "cle_ligne": "f.id",
        "tri_defaut": ("f.dtem", "desc"),
        "colonnes": [
            _article("f"),
            _c("f.nmac1", "nmac1", "Machine 1", "texte", 110),
            _c("f.laimat", "laimat", "Laize matière", "nombre", 110),
            _c("f.ndec1", "ndec1", "Outil", "nombre", 90),
            _c("f.nbcoul", "nbcoul", "Couleurs", "nombre", 90),
            _c("f.cartnbetiq", "cartnbetiq", "Étiq./carton", "nombre", 110),
            _c("f.palnbcart", "palnbcart", "Cartons/palette", "nombre", 120),
            _c("f.dtem", "dtem", "Modifiée le", "datetime", 140),
        ],
        "recherche": ["f.code1", "f.code2"],
        "filtres": [
            {"nom": "article", "label": "Code 1", "col": "f.code1", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Fiche", "champs": ["code1", "code2", "dtem"]},
            {"titre": "Machines", "champs": ["nmac1", "nmac2", "nmac3", "nmac4", "nmac5", "vitmac1", "vitmac2"]},
            {"titre": "Matières", "champs": ["m1cod1", "m1cod2", "laimat", "m2cod1", "m2cod2", "laimat2"]},
            {"titre": "Outils", "champs": ["ndec1", "ndec2", "ndec3", "laiout"]},
            {"titre": "Impression", "champs": ["nbcoul", "repiquage", "impdorsal", "nbelame", "perfotls", "perfointer"]},
            {"titre": "Conditionnement", "champs": ["c1_ner", "c1_dmax", "cartlarg", "cartlong", "carthaut", "cartnbetiq", "cartpds", "cartcode1", "cartcode2"]},
            {"titre": "Palettisation", "champs": ["pallargeur", "pallongueur", "palnbcart", "palnbetage", "palcode1", "palcode2"]},
        ],
    },
    {
        "cle": "dossiers",
        "label": "Dossiers d'ordonnancement",
        "domaine": "production",
        "resume": "Module arrêté en avril 2026, MyProd a pris le relais. Conservé comme historique.",
        "table": "cdi_entete", "alias": "d",
        "cle_ligne": "d.id",
        "tri_defaut": ("d.amjc", "desc"),
        "colonnes": [
            _c("d.numero", "numero", "N° dossier", "nombre", 95),
            _c("d.amjc", "amjc", "Créé le", "date", 95),
            _c("d.numclt", "numclt", "Client", "nombre", 80),
            _c("d.machine", "machine", "Machine", "nombre", 90),
            _c("d.qte", "qte", "Quantité", "qte", 110),
            _c("d.laizem", "laizem", "Laize", "nombre", 85),
            _c("d.nbcoul", "nbcoul", "Couleurs", "nombre", 85),
            _c("d.amjp", "amjp", "Prévu le", "date", 95),
            _c("d.amjr", "amjr", "Réalisé le", "date", 95),
            _c("d.pos", "pos", "Position", "nombre", 85),
        ],
        "recherche": ["d.numero", "d.com"],
        "filtres": [
            {"nom": "client", "label": "N° client", "col": "d.numclt", "type": "egal", "exemple": "890"},
        ],
        "detail": [
            {"titre": "Dossier", "champs": ["numero", "amjc", "amjp", "amjr", "pos", "prio", "numclt"]},
            {"titre": "Fabrication", "champs": ["machine", "travail", "qte", "laizem", "nbcoul", "vit", "ndec"]},
            {"titre": "Temps", "champs": ["tpcm", "tpsm", "tpst", "tpcco", "tpsco"]},
        ],
    },
    {
        "cle": "declarations",
        "label": "Déclarations de production",
        "domaine": "production",
        "resume": "Saisies d'atelier RVGI, mêmes codes opération que MyProd. Arrêtées en avril 2026.",
        "table": "gpr_gpr", "alias": "g",
        "cle_ligne": "g.id",
        "tri_defaut": ("g.amj", "desc"),
        "colonnes": [
            _c("g.amj", "amj", "Date", "date", 100),
            _c("g.dos", "dos", "Dossier", "nombre", 90),
            _c("g.ligne", "ligne", "Lg", "nombre", 50),
            _c("g.pt", "pt", "Opération", "code", 90),
            _c("g.mach", "mach", "Machine", "nombre", 85),
            _c("g.operateur", "operateur", "Opérateur", "nombre", 90),
            _c("g.qtef", "qtef", "Quantité", "qte", 110),
            _c("g.numclt", "numclt", "Client", "nombre", 80),
            _c("g.service", "service", "Service", "nombre", 80),
        ],
        "recherche": ["g.dos", "g.pt"],
        "filtres": [
            {"nom": "dossier", "label": "Dossier", "col": "g.dos", "type": "egal", "exemple": "1018"},
            {"nom": "operation", "label": "Code opération", "col": "g.pt", "type": "egal", "exemple": "01"},
            {"nom": "depuis", "label": "Depuis le", "col": "g.amj", "type": "date_min"},
        ],
        "detail": [
            {"titre": "Déclaration", "champs": ["amj", "dos", "ligne", "pt", "mach", "operateur", "qtef", "service", "orig"]},
        ],
    },
    {
        "cle": "sorties_matiere",
        "label": "Sorties matière",
        "domaine": "production",
        "resume": "Sorties matière par dossier, avec les numéros de lot. Arrêtées en avril 2026.",
        "table": "gpr_mat", "alias": "s",
        "cle_ligne": "s.id",
        "tri_defaut": ("s.amj", "desc"),
        "colonnes": [
            _c("s.amj", "amj", "Date", "date", 100),
            _c("s.dos", "dos", "Dossier", "nombre", 90),
            _article("s", "matiere", "Matière"),
            _c("s.lai", "lai", "Laize", "nombre", 85),
            _c("s.qtes", "qtes", "Sortie", "qte", 110),
            _c("s.qtev", "qtev", "Retour", "qte", 110),
            _c("s.reflot", "reflot", "Lot", "code", 130),
            _c("s.mach", "mach", "Machine", "nombre", 85),
            _c("s.operateur", "operateur", "Opérateur", "nombre", 90),
        ],
        "recherche": ["s.dos", "s.reflot", "s.code1", "s.code2"],
        "filtres": [
            {"nom": "dossier", "label": "Dossier", "col": "s.dos", "type": "egal", "exemple": "1018"},
            {"nom": "lot", "label": "N° de lot", "col": "s.reflot", "type": "contient", "exemple": "BL137434"},
        ],
        "detail": [
            {"titre": "Sortie", "champs": ["amj", "dos", "ligne", "qtes", "qtev", "reflot", "mach", "operateur", "service"]},
            {"titre": "Matière", "champs": ["code1", "code2", "code3", "lai", "type"]},
        ],
    },
    {
        "cle": "colisage",
        "label": "Colisage",
        "domaine": "production",
        "resume": "Colis et palettes déclarés à l'expédition.",
        "table": "col_ligne", "alias": "c",
        "cle_ligne": "c.id",
        "tri_defaut": ("c.amjc", "desc"),
        "colonnes": [
            _c("c.numero", "numero", "N°", "nombre", 85),
            _c("c.amjc", "amjc", "Date", "date", 95),
            _c("c.numcde", "numcde", "Commande", "of", 95),
            _c("c.lignecde", "lignecde", "Lg cde", "nombre", 60),
            _c("c.numbl", "numbl", "BL", "nombre", 90),
            _c("c.colis", "colis", "Colis", "nombre", 80),
            _c("c.numpal", "numpal", "Palette", "nombre", 85),
            _c("c.des1", "des1", "Désignation", "texte", 240),
            _c("c.numclt", "numclt", "Client", "nombre", 80),
        ],
        "recherche": ["c.des1", "c.numcde", "c.numbl", "c.numero"],
        "filtres": [
            {"nom": "commande", "label": "N° de commande", "col": "c.numcde", "type": "egal", "exemple": "9932399"},
        ],
        "detail": [
            {"titre": "Colisage", "champs": ["numero", "amjc", "ligne", "colis", "numpal", "typp", "des1"]},
            {"titre": "Rattachement", "champs": ["numcde", "lignecde", "numbl", "numclt", "operateur"]},
        ],
    },
]


# ── Pièces liées ─────────────────────────────────────────────────────────────
# RVGI ne déclare aucune clé étrangère : les liens ci-dessous sont
# conventionnels, déduits des noms et vérifiés sur les données (cf.
# docs/rvgi/data_rvgi.md §3). Chacun dit : « depuis cette ligne, va chercher
# dans tel écran les lignes dont telle colonne vaut telle valeur de la ligne
# courante ».
#
#   {"label": ..., "ecran": <clé d'écran>, "sur": {<colonne cible>: <champ source>}}
#
# Deux règles de prudence appliquées partout :
#   - jamais de jointure sur `numero` seul entre deux domaines : chaque famille
#     a sa propre numérotation. On passe par la colonne de report explicite
#     (`numcde`, `livbl`, `livno`, `nofac`, `refbl`) ;
#   - un lien dont la valeur source est vide n'est pas proposé.

LIENS = {
    "commandes": [
        {"label": "Bons de livraison", "ecran": "livraisons", "sur": {"l.numcde": "numero"}},
        {"label": "Factures", "ecran": "factures", "sur": {"l.livno": "numero"}},
        {"label": "Mouvements de stock", "ecran": "mouvements_pf", "sur": {"m.numcde": "numero"}},
        # `col_ligne.numcde` existe mais vaut 0 sur TOUTES les lignes du miroir :
        # le colisage porte le numéro de commande dans `numero`. Vérifié le
        # 25/08/2026 sur les 257 lignes de colisage présentes.
        {"label": "Colisage", "ecran": "colisage", "sur": {"c.numero": "numero"}},
        {"label": "L'article", "ecran": "articles", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "Prix négociés du client", "ecran": "prix_client",
         "sur": {"p.code1": "code1", "p.code2": "code2"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "livraisons": [
        {"label": "La commande", "ecran": "commandes", "sur": {"l.numero": "numcde"}},
        {"label": "Factures", "ecran": "factures", "sur": {"l.livbl": "numero"}},
        {"label": "Mouvements de stock", "ecran": "mouvements_pf", "sur": {"m.refbl": "numero"}},
        {"label": "Colisage", "ecran": "colisage", "sur": {"c.numbl": "numero"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "factures": [
        {"label": "La commande", "ecran": "commandes", "sur": {"l.numero": "livno"}},
        {"label": "Le bon de livraison", "ecran": "livraisons", "sur": {"l.numero": "livbl"}},
        {"label": "Échéances", "ecran": "echeances", "sur": {"l.nofac": "numero"}},
        {"label": "L'article", "ecran": "articles", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "echeances": [
        {"label": "La facture", "ecran": "factures", "sur": {"l.numero": "nofac"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "devis": [
        {"label": "L'article", "ecran": "articles", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "marches": [
        {"label": "L'article", "ecran": "articles", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "Commandes de l'article", "ecran": "commandes",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "commandes_fournisseur": [
        {"label": "Réceptions", "ecran": "receptions", "sur": {"l.numero": "numero"}},
        {"label": "Factures fournisseurs", "ecran": "factures_fournisseur", "sur": {"l.livno": "numero"}},
        {"label": "Le fournisseur", "ecran": "fournisseurs", "sur": {"f.numero": "numfou"}},
        {"label": "L'article", "ecran": "articles",
         "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "La matière", "ecran": "stock_matiere",
         "sur": {"m.code1": "code1", "m.code2": "code2"}},
    ],
    "receptions": [
        {"label": "La commande fournisseur", "ecran": "commandes_fournisseur", "sur": {"l.numero": "numero"}},
        # `lot` est NULL partout dans le miroir, des deux côtés : RVGI ne s'en
        # sert pas. Le rapprochement se fait par le n° de commande fournisseur,
        # que la réception porte dans `numero` et le mouvement dans `numcde`.
        {"label": "Mouvements matière", "ecran": "mouvements_matiere", "sur": {"m.numcde": "numero"}},
        {"label": "Le fournisseur", "ecran": "fournisseurs", "sur": {"f.numero": "numfou"}},
    ],
    "factures_fournisseur": [
        {"label": "La commande fournisseur", "ecran": "commandes_fournisseur", "sur": {"l.numero": "livno"}},
        {"label": "Le fournisseur", "ecran": "fournisseurs", "sur": {"f.numero": "numfou"}},
        {"label": "L'article", "ecran": "articles",
         "sur": {"a.code1": "code1", "a.code2": "code2"}},
    ],
    "stock_pf": [
        {"label": "Mouvements de stock", "ecran": "mouvements_pf",
         "sur": {"m.code1": "code1", "m.code2": "code2"}},
        {"label": "Commandes", "ecran": "commandes", "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Prix de vente", "ecran": "prix_vente", "sur": {"p.code1": "code1", "p.code2": "code2"}},
        {"label": "Fiche de fabrication", "ecran": "fiches_fabrication",
         "sur": {"f.code1": "code1", "f.code2": "code2"}},
    ],
    "articles": [
        {"label": "Stock", "ecran": "stock_pf", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "Mouvements de stock", "ecran": "mouvements_pf",
         "sur": {"m.code1": "code1", "m.code2": "code2"}},
        {"label": "Commandes", "ecran": "commandes", "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Factures", "ecran": "factures", "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Prix de vente", "ecran": "prix_vente", "sur": {"p.code1": "code1", "p.code2": "code2"}},
        {"label": "Prix d'achat", "ecran": "prix_achat", "sur": {"p.code1": "code1", "p.code2": "code2"}},
        {"label": "Prix négociés", "ecran": "prix_client", "sur": {"p.code1": "code1", "p.code2": "code2"}},
        {"label": "Fiche de fabrication", "ecran": "fiches_fabrication",
         "sur": {"f.code1": "code1", "f.code2": "code2"}},
        # L'amont de la chaîne : ce qui a été chiffré avant d'être commandé.
        {"label": "Devis", "ecran": "devis", "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Marchés", "ecran": "marches", "sur": {"l.code1": "code1", "l.code2": "code2"}},
        # Et le côté achat : le même code peut désigner une matière achetée.
        {"label": "Commandes fournisseur", "ecran": "commandes_fournisseur",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Factures fournisseur", "ecran": "factures_fournisseur",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Appels d'offres", "ecran": "appels_offres",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Stock matière", "ecran": "stock_matiere",
         "sur": {"m.code1": "code1", "m.code2": "code2"}},
        {"label": "Mouvements matière", "ecran": "mouvements_matiere",
         "sur": {"m.code1": "code1", "m.code2": "code2"}},
        {"label": "Sorties matière", "ecran": "sorties_matiere",
         "sur": {"s.code1": "code1", "s.code2": "code2"}},
    ],
    "clients": [
        {"label": "Commandes", "ecran": "commandes", "sur": {"e.numclt": "numero"}},
        {"label": "Factures", "ecran": "factures", "sur": {"e.numclt": "numero"}},
        {"label": "Échéances", "ecran": "echeances", "sur": {"l.numclt": "numero"}},
        {"label": "Articles du client", "ecran": "articles", "sur": {"a.numclt": "numero"}},
        # La chaîne complète, dans l'ordre où elle se déroule : devis, marché,
        # commande, BL, facture, échéance. Les maillons manquants sont ici.
        {"label": "Devis", "ecran": "devis", "sur": {"e.numclt": "numero"}},
        {"label": "Marchés", "ecran": "marches", "sur": {"e.numclt": "numero"}},
        {"label": "Bons de livraison", "ecran": "livraisons", "sur": {"e.numclt": "numero"}},
        {"label": "Colisage", "ecran": "colisage", "sur": {"c.numclt": "numero"}},
        {"label": "Dossiers de production", "ecran": "dossiers", "sur": {"d.numclt": "numero"}},
        {"label": "Sorties matière", "ecran": "sorties_matiere", "sur": {"s.numclt": "numero"}},
    ],
    "fournisseurs": [
        {"label": "Commandes fournisseurs", "ecran": "commandes_fournisseur",
         "sur": {"e.numfou": "numero"}},
        # `lif_ligne` ne porte pas le fournisseur : la réception le tient de la
        # commande fournisseur, que l'écran joint déjà en `cdf_entete e`.
        {"label": "Réceptions", "ecran": "receptions", "sur": {"e.numfou": "numero"}},
        {"label": "Factures fournisseurs", "ecran": "factures_fournisseur",
         "sur": {"e.numfou": "numero"}},
        {"label": "Appels d'offres", "ecran": "appels_offres", "sur": {"e.numfou": "numero"}},
        {"label": "Matières fournies", "ecran": "stock_matiere", "sur": {"m.numfou": "numero"}},
        {"label": "Prix d'achat", "ecran": "prix_achat", "sur": {"p.numfou": "numero"}},
    ],
    "outils": [
        {"label": "Fiches de fabrication", "ecran": "fiches_fabrication", "sur": {"f.ndec1": "numero"}},
    ],
    "fiches_fabrication": [
        {"label": "L'article", "ecran": "articles", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "L'outil de découpe", "ecran": "outils", "sur": {"o.numero": "ndec1"}},
        {"label": "Commandes de l'article", "ecran": "commandes",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
    ],
    "mouvements_pf": [
        {"label": "L'article", "ecran": "articles", "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "La commande", "ecran": "commandes", "sur": {"l.numero": "numcde"}},
        {"label": "Le bon de livraison", "ecran": "livraisons", "sur": {"l.numero": "refbl"}},
    ],
    "mouvements_matiere": [
        {"label": "La matière", "ecran": "stock_matiere", "sur": {"m.code1": "code1", "m.code2": "code2"}},
        # Voir la note sur « receptions » : `lot` n'est jamais renseigné.
        {"label": "Réceptions", "ecran": "receptions", "sur": {"l.numero": "numcde"}},
    ],
    "stock_matiere": [
        {"label": "Mouvements matière", "ecran": "mouvements_matiere",
         "sur": {"m.code1": "code1", "m.code2": "code2"}},
        {"label": "Le fournisseur", "ecran": "fournisseurs", "sur": {"f.numero": "numfou"}},
        {"label": "L'article", "ecran": "articles",
         "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "Commandes fournisseur", "ecran": "commandes_fournisseur",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
        {"label": "Sorties matière", "ecran": "sorties_matiere",
         "sur": {"s.code1": "code1", "s.code2": "code2"}},
    ],
    "dossiers": [
        {"label": "Déclarations de production", "ecran": "declarations", "sur": {"g.dos": "numero"}},
        {"label": "Sorties matière", "ecran": "sorties_matiere", "sur": {"s.dos": "numero"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "declarations": [
        {"label": "Le dossier", "ecran": "dossiers", "sur": {"d.numero": "dos"}},
        {"label": "Sorties matière du dossier", "ecran": "sorties_matiere", "sur": {"s.dos": "dos"}},
    ],
    "sorties_matiere": [
        {"label": "Le dossier", "ecran": "dossiers", "sur": {"d.numero": "dos"}},
        {"label": "La matière", "ecran": "stock_matiere", "sur": {"m.code1": "code1", "m.code2": "code2"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
    "appels_offres": [
        {"label": "Le fournisseur", "ecran": "fournisseurs", "sur": {"f.numero": "numfou"}},
        {"label": "L'article", "ecran": "articles",
         "sur": {"a.code1": "code1", "a.code2": "code2"}},
        {"label": "Commandes fournisseur", "ecran": "commandes_fournisseur",
         "sur": {"l.code1": "code1", "l.code2": "code2"}},
    ],
    "colisage": [
        # `col_ligne.numcde` vaut 0 partout : c'est `numero` qui porte le
        # numéro de commande (voir la note du lien inverse, écran commandes).
        {"label": "La commande", "ecran": "commandes", "sur": {"l.numero": "numero"}},
        {"label": "Le bon de livraison", "ecran": "livraisons", "sur": {"l.numero": "numbl"}},
        # Le retour au fichier : depuis n'importe quel maillon, la fiche du
        # tiers concerné. C'est le geste qu'on fait le plus souvent et qui
        # obligeait jusqu'ici à retourner à la grille des clients.
        {"label": "Le client", "ecran": "clients", "sur": {"c.numero": "numclt"}},
    ],
}

PAR_CLE = {e["cle"]: e for e in ECRANS}


def ecran(cle):
    return PAR_CLE.get(cle)


def adapter_ecran(ec, colonnes_par_table):
    """Élague l'écran de ce que le miroir n'a pas.

    Le catalogue décrit RVGI tel que le relevé le montre ; le miroir, lui, ne
    contient que ce que l'export a ramené. Une colonne manquante ferait tomber
    la requête entière : on la retire, et l'écran affiche le reste.

    Renvoie `None` si la table principale ou la clé de ligne manquent — l'écran
    n'a alors pas lieu d'exister et n'est pas proposé.
    """
    principales = colonnes_par_table.get(ec["table"])
    if not principales:
        return None

    dispo = {ec["alias"]: principales}
    jointures = []
    for j in ec.get("jointures", []):
        cols = colonnes_par_table.get(j["table"])
        if not cols:
            continue
        dispo[j["alias"]] = cols
        jointures.append(j)

    def existe(ref):
        alias, _, col = str(ref).partition(".")
        if not col:
            return False
        return col in dispo.get(alias, set())

    if not existe(ec["cle_ligne"]):
        return None

    # Une jointure dont la colonne de rapprochement manque est abandonnée —
    # sauf si elle est `obligatoire` : l'écran repose dessus pour ne pas montrer
    # de lignes sans pièce. L'abandonner en silence rendrait l'écran faux, donc
    # on préfère ne pas le proposer du tout.
    perdues = [j for j in jointures if not (existe(j["gauche"]) and existe(j["droite"]))]
    if any(j.get("obligatoire") for j in perdues):
        return None
    jointures = [j for j in jointures if existe(j["gauche"]) and existe(j["droite"])]
    alias_gardes = {ec["alias"]} | {j["alias"] for j in jointures}

    def ref_ok(ref):
        alias = str(ref).partition(".")[0]
        return alias in alias_gardes and existe(ref)

    colonnes = []
    for c in ec["colonnes"]:
        refs = c["parts"] if c.get("parts") else [c["c"]]
        gardees = [r for r in refs if ref_ok(r)]
        if not gardees:
            continue
        if c.get("parts"):
            c = dict(c, parts=gardees)
        colonnes.append(c)
    if not colonnes:
        return None

    tri_col, tri_sens = ec["tri_defaut"]
    if not ref_ok(tri_col):
        tri_col = colonnes[0]["c"] if colonnes[0].get("c") else colonnes[0]["parts"][0]
        tri_sens = "asc"

    adapte = dict(ec)
    adapte["jointures"] = jointures
    adapte["colonnes"] = colonnes
    adapte["tri_defaut"] = (tri_col, tri_sens)
    adapte["recherche"] = [r for r in ec.get("recherche", []) if ref_ok(r)]
    adapte["filtres"] = [f for f in ec.get("filtres", []) if ref_ok(f["col"])]
    adapte["labels_detail"] = dict(LABELS, **(ec.get("labels_detail") or {}))
    adapte["liens"] = LIENS.get(ec["cle"], [])
    adapte["piece"] = piece_de(adapte)
    r = RATTACHABLE.get(ec["cle"])
    # Le rattachement ne se propose que si les colonnes qu'il joint existent
    # vraiment dans le miroir.
    if r and ref_ok("%s.numero" % ec["alias"]):
        if r["col_ligne"] and not ref_ok("%s.%s" % (ec["alias"], r["col_ligne"])):
            r = dict(r, col_ligne=None)
        if r["col_qte"] and not ref_ok("%s.%s" % (ec["alias"], r["col_qte"])):
            r = dict(r, col_qte=None)
        adapte["rattachable"] = r
    return adapte


# ── Écrans de lignes de document ─────────────────────────────────────────────

# Une pièce est déduite, pas déclarée. RVGI applique partout la même forme :
# `<dom>_ligne` porte les lignes, `<dom>_entete` porte la pièce, et la jointure
# se fait sur `numero`. Un nouvel écran de lignes hérite donc de la vue « pièce »
# sans qu'on ait à y penser — et un écran qui n'est pas un document (un article,
# un client, un mouvement) n'en hérite jamais.
#
# `PIECE_LABELS` ne sert qu'à nommer la section. Une clé absente donne
# « La pièce », ce qui reste juste.
PIECE_LABELS = {
    "devis": "Le devis",
    "commandes": "La commande",
    "livraisons": "Le bon de livraison",
    "factures": "La facture",
    "marches": "Le marché",
    "commandes_fournisseur": "La commande fournisseur",
    "receptions": "La commande fournisseur",
    "factures_fournisseur": "La facture fournisseur",
    "appels_offres": "L'appel d'offres",
    "colisage": "Le colisage",
}


def piece_de(ec):
    """L'entête de pièce d'un écran de lignes, si l'écran en est un."""
    alias = ec["alias"]
    for j in ec.get("jointures", []):
        if j["droite"] == "%s.numero" % alias and j["gauche"].endswith(".numero"):
            return {
                "table": j["table"],
                "alias": j["alias"],
                "cle": "numero",
                "col_ligne": "%s.numero" % alias,
                "label": PIECE_LABELS.get(ec["cle"], "La pièce"),
                "tri": _colonne_de_ligne(ec),
            }
    return None


# ── Écrans qui portent un rattachement MySifa ────────────────────────────────
#
# Deux, et deux seulement : ce que MySifa fabrique se rattache à une ligne de
# commande, ce qu'il expédie à un bon de livraison. Le reste — articles,
# clients, factures — n'a rien à rattacher, et une colonne vide sur vingt-cinq
# écrans coûterait une jointure pour rien.
RATTACHABLE = {
    "commandes":  {"piece": "commande",  "col_ligne": "ligne", "col_qte": "qte"},
    "livraisons": {"piece": "livraison", "col_ligne": None,    "col_qte": "qte"},
}


def _colonne_de_ligne(ec):
    """Sur quoi trier les lignes À L'INTÉRIEUR d'une pièce.

    Le numéro de ligne quand l'écran en montre un, son rang sinon. À défaut,
    `_id` : l'ordre dans lequel RVGI a écrit les lignes, qui est le bon.
    """
    noms = {c["nom"] for c in ec["colonnes"]}
    for candidat in ("ligne", "rang", "lignecde"):
        if candidat in noms:
            return candidat
    return "_id"


# ── Menu de service ──────────────────────────────────────────────────────────
#
# Le tiroir montre tout ; ce menu-ci montre le peu qu'on ouvre vraiment. Il se
# déploie au survol de la marque RVGI, en tête de page, et sert de raccourci
# permanent : deux tableaux de bord d'abord, puis les écrans que le service
# consulte tous les jours.
#
# Un service n'a pas moins de DROITS que les autres — l'accès à /erp est le
# même pour tous (`ROLES_ADMIN`). Il a moins d'habitudes. Ce menu range les
# habitudes ; le tiroir reste la porte vers les 27 écrans.

TABLEAUX_DE_BORD = [
    {
        "cle": "tdb_adv",
        "label": "TDB ADV",
        "resume": "Le fil commande → dossier de production → BL, "
                  "et les documents qui attendent une vérification.",
    },
    {
        "cle": "tdb_direction",
        "label": "TDB Direction",
        "resume": "Rentré, facturable, facturé — et le rentré de la veille, "
                  "commande par commande.",
    },
]

CLES_TDB = {t["cle"] for t in TABLEAUX_DE_BORD}

# Écrans mis en avant, dans l'ordre où le service les ouvre.
_MENU_ADV = ["commandes", "livraisons", "factures", "colisage", "clients", "articles"]
_MENU_DIRECTION = ["commandes", "factures", "echeances", "clients", "marches", "prix_vente"]
_MENU_TECHNIQUE = ["articles", "fiches_fabrication", "outils", "machines",
                   "stock_matiere", "receptions"]
# L'expédition ne lit l'ERP que pour ce qu'elle expédie : le BL, la commande
# qui le motive, et le colisage. Ni factures, ni prix, ni échéances.
_MENU_EXPEDITION = ["livraisons", "commandes", "colisage", "clients"]

MENU_SERVICE = {
    "superadmin": {"tdb": ["tdb_adv", "tdb_direction"], "ecrans": _MENU_ADV},
    "direction": {"tdb": ["tdb_direction", "tdb_adv"], "ecrans": _MENU_DIRECTION},
    "administration_ventes": {"tdb": ["tdb_adv"], "ecrans": _MENU_ADV},
    "administration": {"tdb": ["tdb_adv"], "ecrans": _MENU_ADV},
    "administration_technique": {"tdb": ["tdb_adv"], "ecrans": _MENU_TECHNIQUE},
    "expedition": {"tdb": [], "ecrans": _MENU_EXPEDITION},
}

# Un rôle inconnu ne se retrouve pas devant un menu vide : il reçoit le carnet.
MENU_DEFAUT = {"tdb": [], "ecrans": ["commandes", "livraisons", "factures"]}


def menu_du_role(role, ecrans_disponibles=None):
    """Le menu de survol pour ce rôle, réduit à ce que le miroir contient.

    `ecrans_disponibles` est l'ensemble des clés d'écran réellement servies par
    `/api/erp/meta` : un miroir partiel n'a pas à proposer une entrée qui
    ouvrirait un écran vide.
    """
    conf = MENU_SERVICE.get(str(role or ""), MENU_DEFAUT)
    par_cle = {t["cle"]: t for t in TABLEAUX_DE_BORD}
    tdb = [par_cle[c] for c in conf.get("tdb", []) if c in par_cle]

    ecrans = []
    for cle in conf.get("ecrans", []):
        if ecrans_disponibles is not None and cle not in ecrans_disponibles:
            continue
        ec = ecran(cle)
        if ec:
            ecrans.append({"cle": cle, "label": ec["label"], "resume": ec.get("resume", "")})
    return {"tdb": tdb, "ecrans": ecrans}


# ── Vue par pièce ────────────────────────────────────────────────────────────
#
# Une ligne de commande n'est pas une commande. « 845 lignes en retard », c'est
# 312 commandes — et c'est la commande qu'on rappelle au client, pas la ligne.
# Les écrans de RVGI sont tous au niveau ligne ; cette vue les regroupe sur le
# numéro de pièce, sans changer d'écran ni de filtres.
#
# Ce qui est constant dans une pièce (client, date d'entête) est repris tel
# quel. Les quantités et les montants sont sommés. Une date de ligne donne la
# plus proche. Le reste — désignation, référence article, prix unitaire,
# position — n'a pas de sens agrégé et disparaît : une colonne en moins vaut
# mieux qu'une moyenne que personne n'a demandée.

# Types de colonne qu'on peut sommer sans mentir.
_SOMMABLES = ("qte", "montant")


def groupable(ec):
    """Cet écran a-t-il une pièce sur laquelle regrouper ?"""
    return piece_de(ec) is not None


def colonnes_groupees(ec):
    """Les colonnes de la vue par pièce, dérivées de celles de l'écran.

    Chaque colonne porte `expr` : l'expression SQL agrégée. Les références
    sont celles du catalogue, jamais une saisie utilisateur.
    """
    p = piece_de(ec)
    if not p:
        return None
    alias_piece = p["alias"]
    col_numero = p["col_ligne"]          # ex. « l.numero »

    colonnes = []
    vus = set()

    def ajouter(nom, label, type_, largeur, expr, aligne=None):
        if nom in vus:
            return
        vus.add(nom)
        c = {"nom": nom, "label": label, "type": type_,
             "largeur": largeur, "expr": expr}
        if aligne:
            c["aligne"] = aligne
        colonnes.append(c)

    # 1. Le numéro de pièce — la clé du regroupement, en tête.
    ref = next((c for c in ec["colonnes"]
                if c.get("c") == col_numero), None)
    ajouter(ref["nom"] if ref else "numero",
            ref["label"] if ref else "N°",
            ref.get("type") if ref else "nombre",
            ref.get("largeur") if ref else 100,
            col_numero)

    # 2. Le nombre de lignes : c'est l'information que la vue apporte.
    ajouter("_lignes", "Lignes", "nombre", 62, "COUNT(*)")

    # 3. Ce que porte l'entête est constant dans la pièce : on le reprend.
    for c in ec["colonnes"]:
        if c.get("parts") or not c.get("c"):
            continue
        if c["c"] == col_numero:
            continue
        if c["c"].split(".")[0] == alias_piece:
            ajouter(c["nom"], c["label"], c.get("type"), c.get("largeur"),
                    "MIN(%s)" % c["c"], c.get("aligne"))

    # 4. Les colonnes de ligne : sommes et dates au plus tôt, rien d'autre.
    for c in ec["colonnes"]:
        if c.get("parts") or not c.get("c"):
            continue
        if c["c"] == col_numero or c["c"].split(".")[0] == alias_piece:
            continue
        if c.get("type") in _SOMMABLES:
            ajouter(c["nom"], "Σ " + c["label"], c.get("type"),
                    c.get("largeur"), "SUM(%s)" % c["c"], c.get("aligne"))
        elif c.get("type") == "date":
            ajouter(c["nom"], c["label"], "date", c.get("largeur"),
                    "MIN(%s)" % c["c"], c.get("aligne"))

    return {"cle": col_numero, "colonnes": colonnes,
            "label": PIECE_LABELS.get(ec["cle"], "La pièce")}
