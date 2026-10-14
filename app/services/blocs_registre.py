"""Registre des blocs capturables en widget d'accueil.

Un bloc est une zone d'une page (un compteur, une liste, une carte machine)
que l'utilisateur peut épingler dans la colonne « Mes widgets » de l'accueil.
Le widget affiche le bloc réel, chargé dans sa page d'origine avec les droits
et les filtres de l'utilisateur : ce registre ne calcule rien, il dit seulement
OÙ vit chaque bloc et CE QU'IL SAIT montrer en valeur clé.

Pourquoi dans le code et pas en base : un bloc n'existe que si une page le
dessine. Le jour où on déplace ou renomme un bloc, la page et le registre
changent dans le même commit, sinon les widgets des utilisateurs cassent.
Le registre décrit le logiciel MySifa, pas l'entreprise : rien ici n'est une
donnée SIFA.

Côté page, un bloc se marque ainsi (cf. .claude/rules/widgets-blocs.md) :

    data-bloc="stock.dashboard.reappro"         nom stable, obligatoire
    data-bloc-objet="12"                        objet suivi (machine, dossier…)
    data-bloc-valeur-lignes="4"                 une valeur clé par attribut

Le test tests/test_blocs_registre.py croise ce registre avec les data-bloc du
code : un bloc disparu sans alias, ou un nom en double, bloque la CI.

Le module est volontairement pur Python (aucun import FastAPI ni base) : sa
validation se teste partout, y compris sur un poste sans dépendances.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

# Plafond décidé le 03/10/2026 : au-delà, un widget devient illisible.
VALEURS_MAX = 4
NOM_WIDGET_MAX = 80
# Taille de l'indicateur (colonne `hauteur`, nom gardé depuis l'affichage
# « bloc ») : s compact (une ligne), m standard, l grand (graphique ou liste).
HAUTEURS = ("s", "m", "l")
# Compact = une ligne : seule la première valeur s'y lit, en garder plusieurs
# n'aurait pas de sens (décision du 14/10/2026).
COMPACT_UNE_VALEUR = "Compact : une seule valeur à afficher."
# Sens d'une série : « + » quand une hausse est une bonne nouvelle (métrage),
# « - » quand c'est l'inverse (arrêts). Il colore la tendance.
SENS_SERIE = ("+", "-")
AFFICHAGES = ("bloc", "valeurs")
TYPES = ("chiffre", "liste", "tableau", "graphique", "etat", "objet", "fiche")
# Opérateurs d'alerte : comparaison numérique, ou égalité pour un état
# (« rouge si Arrêt »).
ALERTE_OPS = (">", "<", "=")

# Teintes d'appli : variables du thème (static/mysifa_theme.css), qui
# changent avec la palette de l'utilisateur. --c5 est écartée : rouge dans
# toutes les palettes, elle se confondrait avec une alerte.
TEINTES = ("accent", "c1", "c2", "c3", "c4")
# Icônes dessinées par mysifa_accueil.js (ICONES_APPLI).
ICONES_APPLI = ("atelier", "planning", "maintenance", "stock", "erp", "ao", "compta",
                "expe", "qualite", "bat", "rh", "coffre", "calendrier", "taches",
                "messages", "accueil")


@dataclass(frozen=True)
class Appli:
    libelle: str
    icone: str
    teinte: str


# Appli d'un bloc → pastille de l'indicateur (nom, icône, couleur). Décrit le
# logiciel, pas l'entreprise. Les teintes regroupent des familles : atelier,
# gestion, flux, personnel. Une appli nouvelle au registre s'ajoute ici, sinon
# le test échoue.
APPLIS: dict[str, Appli] = {
    "prod": Appli("MyProd", "atelier", "c1"),
    "planning": Appli("Planning", "planning", "c1"),
    "maintenance": Appli("Maintenance", "maintenance", "c1"),
    "stock": Appli("MyStock", "stock", "c2"),
    "erp": Appli("ERP", "erp", "c2"),
    "ao": Appli("MyAO", "ao", "c2"),
    "compta": Appli("MyCompta", "compta", "c2"),
    "expe": Appli("MyExpé", "expe", "c3"),
    "qualite": Appli("MyQualité", "qualite", "c3"),
    "bat": Appli("MyBAT", "bat", "c3"),
    "planning_rh": Appli("Planning RH", "rh", "c4"),
    "myrh": Appli("MyRH", "rh", "c4"),
    "rh_coffre": Appli("Coffre RH", "coffre", "c4"),
    "calendrier": Appli("Calendrier", "calendrier", "c4"),
    "taches": Appli("Tâches", "taches", "c4"),
    "messages": Appli("Messagerie", "messages", "c4"),
    "portail": Appli("Accueil", "accueil", "accent"),
}

# Couleur d'une valeur en badge : TONS_ETAT de config.py, recopié ici pour
# garder le module pur (le test vérifie que les deux listes concordent).
TONS = ("ok", "warn", "danger", "neutre")

_NOM_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")
_CLE_RE = re.compile(r"^[a-z0-9-]+$")


@dataclass(frozen=True)
class Bloc:
    appli: str
    libelle: str
    url: str                      # emplacement actuel : chemin + requête + ancre
    type: str
    valeurs: tuple = ()           # ((cle, libelle), …) — au moins une : le widget n'affiche qu'elles
    acces: str | None = None      # app_id passé à user_has_app_access ; None = tout connecté
    objet: str | None = None      # nature de l'objet suivi (« machine »), sinon None
    alias: tuple = field(default=())  # anciens noms, pour les widgets créés avant un renommage
    # Clés dont la valeur est un texte (état, nom, référence) : affichées, mais
    # sans alerte — une alerte compare à un seuil, elle n'a de sens que sur un
    # nombre. Toute clé absente d'ici est un nombre.
    textes: tuple = ()
    # Bloc cliquable sur un objet (tuile de catégorie, carte machine) : où mène
    # le clic, « {objet} » remplacé par l'objet suivi. L'indicateur ouvre alors
    # cette page-là, pas celle où le bloc a été capturé.
    lien: str | None = None
    # Clés texte affichées en badge coloré (état, appréciation). La page pose
    # data-bloc-ton-<cle> (ok, warn, danger, neutre) et la source rend
    # tons={cle: …}, tous deux lus d'un champ de l'API, jamais du libellé.
    tons: tuple = ()
    # Clés qui ont une série par jour (source SERIES de mysifa_blocs_sources.js) :
    # ((cle, sens), …). Elles reçoivent la tendance et la mini-courbe, et
    # ouvrent le grand format en graphique sur 30 jours. Une série s'additionne
    # jour par jour : une moyenne ou une vitesse n'en est pas une.
    series: tuple = ()
    # Le bloc sait lister ses lignes (source LISTES) : grand format en liste.
    liste: bool = False

    @property
    def grand(self) -> bool:
        return bool(self.series) or self.liste


# Nom stable → bloc. Un nom ne change JAMAIS : pour renommer, créer le nouveau
# nom et poser l'ancien dans `alias`.
BLOCS: dict[str, Bloc] = {
    "stock.dashboard.reappro": Bloc(
        appli="stock",
        libelle="Stocks à réapprovisionner",
        url="/stock?tab=dashboard",
        type="liste",
        valeurs=(("lignes", "Matières sous seuil"),),
        acces="stock",
        liste=True,
    ),
    "stock.matieres.categorie": Bloc(
        appli="stock", libelle="Catégorie de matières", url="/stock?tab=matieres",
        type="objet",
        valeurs=(("references", "Références"), ("sous-seuil", "Sous le seuil")),
        acces="stock", objet="categorie", lien="/stock?tab=matieres&cat={objet}",
        liste=True,
    ),
    "stock.monitoring.kpis": Bloc(
        appli="stock", libelle="Monitoring stocks PF", url="/stock?tab=monitoring",
        type="chiffre",
        valeurs=(("comparees", "Références comparées"), ("ecarts", "Écarts"),
                 ("sans-corresp", "Sans correspondance"), ("negatifs", "Stocks négatifs")),
        acces="stock",
    ),
    "stock.dashboard.kpis": Bloc(
        appli="stock",
        libelle="Chiffres du stock",
        url="/stock?tab=dashboard",
        type="chiffre",
        valeurs=(("mp", "MP à approvisionner"), ("a-expedier", "Références à expédier"),
                 ("departs", "Expéditions aujourd'hui"), ("refs", "Références en stock")),
        acces="stock",
    ),
    "stock.besoins.kpis": Bloc(
        appli="stock", libelle="Besoins matières", url="/stock?tab=besoins-matieres",
        type="chiffre",
        valeurs=(("a-associer", "Références à associer"), ("dossiers", "Dossiers"),
                 ("mappees", "Références associées")),
        acces="stock",
    ),
    # ── MyStock › Produits finis, Contrôle, Traçabilité, Inventaire ──
    "stock.pf.kpis": Bloc(
        appli="stock", libelle="Produits finis", url="/stock?tab=produits-finis",
        type="chiffre",
        valeurs=(("references", "Références en stock"), ("mouvements", "Mouvements aujourd'hui"),
                 ("emplacements", "Emplacements occupés")),
        acces="stock",
    ),
    "stock.valorisation.kpis": Bloc(
        appli="stock", libelle="Valorisation du stock", url="/stock?tab=valorisation",
        type="chiffre",
        valeurs=(("total", "Stock valorisé (€)"), ("mp", "Matières premières (€)"),
                 ("pf", "Produits finis (€)"), ("pf-sans-prix", "Produits finis sans prix")),
        acces="stock",
    ),
    "stock.bobines.kpis": Bloc(
        appli="stock", libelle="Traçabilité des bobines", url="/stock?tab=bobines",
        type="chiffre",
        valeurs=(("bobines", "Bobines"), ("metrage", "Métrage (m)"),
                 ("ecarts", "Écarts au compteur"), ("sans-matiere", "Bobines sans matière")),
        acces="stock",
    ),
    "stock.inventaire.anciennete": Bloc(
        appli="stock", libelle="Ancienneté de l'inventaire", url="/stock?tab=inventaire",
        type="chiffre",
        valeurs=(("rouge", "Emplacements à plus de 60 j ou jamais"), ("orange", "Emplacements à 30-60 j"),
                 ("a-jour", "Emplacements à moins de 30 j"), ("emplacements", "Emplacements avec stock")),
        acces="stock",
    ),
    "expe.departs.programmes": Bloc(
        appli="expe",
        libelle="Départs programmés",
        url="/expe#suivi_departs",
        type="tableau",
        valeurs=(("lignes", "Départs en attente"),),
        acces="expe",
        liste=True,
    ),
    # ── MyProd › Production › Vue d'ensemble (static/mysifa_prod_core.js) ──
    "prod.ensemble.machines": Bloc(
        appli="prod", libelle="Statut des machines", url="/prod?page=production",
        type="etat", valeurs=(("en-marche", "Machines en marche"),), acces="prod",
    ),
    "prod.ensemble.machine": Bloc(
        appli="prod", libelle="Machine", url="/prod?page=production", type="objet",
        valeurs=(("etat", "État"), ("depuis", "Depuis (min)"), ("operateur", "Opérateur"),
                 ("dossier", "Dossier")),
        textes=("etat", "operateur", "dossier"),
        acces="prod", objet="machine",
        tons=("etat",),
    ),
    "prod.ensemble.sanity": Bloc(
        appli="prod", libelle="Qualité de saisie", url="/prod?page=production",
        type="chiffre", valeurs=(("score", "Score"),), acces="prod",
    ),
    # ── MyProd › Production › Erreurs & Qualité (static/mysifa_prod_core.js) ──
    "prod.erreurs.score": Bloc(
        appli="prod", libelle="Sanity Score", url="/prod?page=production#erreurs",
        type="chiffre",
        valeurs=(("score", "Score"), ("mention", "Appréciation"), ("journees", "Journées")),
        textes=("mention",), acces="prod",
        tons=("mention",),
    ),
    "prod.erreurs.kpis": Bloc(
        appli="prod", libelle="Erreurs & Qualité", url="/prod?page=production#erreurs",
        type="chiffre",
        valeurs=(("operations", "Total opérations"), ("critique", "Critique"), ("attention", "Attention"),
                 ("normal", "Normal"), ("erreurs", "Erreurs de saisie")),
        acces="prod",
    ),
    "prod.ensemble.quantites": Bloc(
        appli="prod", libelle="Quantités produites", url="/prod?page=production",
        type="chiffre",
        valeurs=(("metrage", "Métrage (m)"), ("dossiers", "Dossiers produits"),
                 ("vitesse", "Vitesse (m/min)")),
        acces="prod",
        series=(("metrage", "+"),),
    ),
    "prod.ensemble.temps": Bloc(
        appli="prod", libelle="Temps de production", url="/prod?page=production",
        type="chiffre",
        valeurs=(("production", "Production (min)"), ("calage", "Calage (min)"),
                 ("arrets", "Arrêts (min)")),
        acces="prod",
        series=(("calage", "-"), ("production", "+"), ("arrets", "-")),
    ),
    "prod.ensemble.par-dossier": Bloc(
        appli="prod", libelle="Synthèse par dossier", url="/prod?page=production",
        type="tableau", valeurs=(("lignes", "Dossiers"),), acces="prod",
    ),
    "prod.ensemble.par-operateur": Bloc(
        appli="prod", libelle="Synthèse par opérateur", url="/prod?page=production",
        type="tableau", valeurs=(("lignes", "Opérateurs"),), acces="prod",
    ),
    "prod.ensemble.par-machine": Bloc(
        appli="prod", libelle="Synthèse par machine", url="/prod?page=production",
        type="tableau", valeurs=(("lignes", "Machines"),), acces="prod",
    ),
    "prod.ensemble.par-jour": Bloc(
        appli="prod", libelle="Synthèse par jour", url="/prod?page=production",
        type="tableau", valeurs=(("lignes", "Jours"),), acces="prod",
    ),
    # ── MyExpé › Pilotage (app/web/expe_pilotage_assets.py) ──
    "expe.pilotage.resume": Bloc(
        appli="expe", libelle="Pilotage des expéditions", url="/expe#pilotage",
        type="chiffre",
        valeurs=(("retard", "En retard"), ("a-programmer", "À programmer"),
                 ("palettes", "Palettes à réserver"), ("programme", "Transport programmé"),
                 ("sans-bl", "Sans BL")),
        acces="expe",
    ),
    "expe.pilotage.envois": Bloc(
        appli="expe", libelle="Envois à piloter", url="/expe#pilotage",
        type="tableau", valeurs=(("lignes", "Envois"),), acces="expe",
        liste=True,
    ),
    # ── MyExpé › Palettes Europe (app/web/expe_assets.py) ──
    "expe.palettes.totaux": Bloc(
        appli="expe", libelle="Palettes Europe", url="/expe#palettes_europe",
        type="chiffre",
        valeurs=(("solde", "Solde dû par les transporteurs"), ("envoyees", "Palettes envoyées"),
                 ("retournees", "Palettes retournées"), ("litiges", "Palettes en litige")),
        acces="expe",
    ),
    "expe.palettes.transporteur": Bloc(
        appli="expe", libelle="Compte palettes d'un transporteur", url="/expe#palettes_europe",
        type="objet",
        valeurs=(("solde", "Solde dû"), ("donnees", "Palettes remises"),
                 ("rendues", "Palettes rendues"), ("litiges", "Palettes en litige")),
        acces="expe", objet="transporteur",
    ),
    # ── MyExpé › Taxe carburant (app/web/expe_carburant_assets.py) ──
    "expe.carburant.resume": Bloc(
        appli="expe", libelle="Taxe carburant", url="/expe#carburant",
        type="chiffre",
        valeurs=(("en-attente", "En attente de réponse"), ("anciens", "Taux de plus de 45 j"),
                 ("jamais", "Jamais mise à jour"), ("a-jour", "À jour"),
                 ("actifs", "Transporteurs actifs"), ("moyen", "Taux moyen (%)")),
        acces="expe",
    ),
    # ── Planning machine (app/web/planning_page.py) ──
    "planning.dossiers": Bloc(
        appli="planning", libelle="Dossiers au planning", url="/planning",
        type="objet",
        valeurs=(("en-cours", "Dossier en cours"), ("attente", "Dossiers en attente"),
                 ("charge", "Charge en attente (h)")),
        textes=("en-cours",),
        acces="planning", objet="machine", lien="/planning?machine={objet}",
    ),
    # ── Gestionnaire de tâches (app/web/taches_page.py) ──
    "taches.compteurs": Bloc(
        appli="taches", libelle="Tâches", url="/taches",
        type="chiffre",
        valeurs=(("mes-taches", "Mes tâches ouvertes"), ("mes-retards", "Mes tâches en retard"),
                 ("en-retard", "En retard (équipe)"), ("non-assignees", "Non assignées")),
    ),
    # ── MyQualité (app/web/qualite_page.py) ──
    "qualite.nc.statuts": Bloc(
        appli="qualite", libelle="Non-conformités", url="/qualite#list",
        type="chiffre",
        valeurs=(("ouvertes", "NC non clôturées"), ("en-analyse", "En analyse"),
                 ("action-corrective", "Action corrective"), ("en-verification", "En vérification"),
                 ("non-lues", "Messages non lus")),
        acces="qualite",
        liste=True,
    ),
    # ── Coffre RH (app/web/rh_coffre_page.py) ──
    "rh-coffre.ndf": Bloc(
        appli="rh_coffre", libelle="Notes de frais à valider", url="/rh/coffre#ndf",
        type="chiffre",
        valeurs=(("a-valider", "Notes à valider"), ("montant", "Montant à valider (€)")),
        liste=True,
    ),
    # ── Messagerie (app/web/messages_page.py) ──
    "messages.non-lus": Bloc(
        appli="messages", libelle="Messagerie", url="/messages",
        type="chiffre",
        valeurs=(("non-lus", "Messages non lus"), ("directs", "Messages directs non lus"),
                 ("mentions", "Canaux où je suis mentionné")),
    ),
    # ── MyBAT (app/web/bat_page.py) ──
    "bat.statuts": Bloc(
        appli="bat", libelle="Bons à tirer", url="/bat",
        type="chiffre",
        valeurs=(("en-attente", "En attente de validation"), ("a-faire", "À faire"),
                 ("valides", "Validés")),
        liste=True,
    ),
    # ── Maintenance (app/web/maintenance_page.py) — sans source API ──
    "maintenance.statuts": Bloc(
        appli="maintenance", libelle="Maintenance périodique", url="/maintenance#maintenance",
        type="chiffre",
        valeurs=(("en-retard", "Opérations en retard"), ("bientot", "Dues bientôt"),
                 ("jamais", "Jamais saisies"), ("a-jour", "À jour")),
    ),
    # ── MyAO (app/web/ao_page.py) ──
    "ao.appels": Bloc(
        appli="ao", libelle="Appels d'offres", url="/ao",
        type="chiffre",
        valeurs=(("envoyees", "Appels en cours"), ("reponses", "Réponses reçues"),
                 ("brouillons", "Brouillons")),
        liste=True,
    ),
    "prod.of.a-traiter": Bloc(
        appli="prod", libelle="OF à traiter", url="/prod?page=of",
        type="chiffre",
        valeurs=(("total", "OF à traiter"), ("mappings", "Mappings à valider"),
                 ("sans-of", "Dossiers sans OF")),
        acces="prod",
    ),
    # ── Calendrier (app/web/calendrier_page.py) ──
    "calendrier.agenda": Bloc(
        appli="calendrier", libelle="Mon agenda", url="/calendrier",
        type="liste",
        valeurs=(("aujourdhui", "Événements aujourd'hui"), ("demain", "Événements demain")),
    ),
    # ── Planning RH (app/web/planning_rh_page.py) ──
    "planning-rh.conges": Bloc(
        appli="planning_rh", libelle="Congés", url="/planning-rh#conges",
        type="liste",
        valeurs=(("absents", "Absents aujourd'hui"), ("a-valider", "Congés posés à valider")),
        acces="planning_rh",
        liste=True,
    ),
    # ── MyRH › Outil RH (app/web/compta_rh_outil_assets.py) ──
    # Le nom garde son préfixe « compta » : l'Outil RH vivait dans MyCompta et
    # un nom de bloc ne change jamais (widgets déjà épinglés). Seuls l'URL et
    # l'accès ont suivi le déménagement vers MyRH.
    "compta.rh.contrats": Bloc(
        appli="myrh", libelle="Suivi RH des employés", url="/rh",
        type="chiffre",
        liste=True,
        valeurs=(("fin-proche", "Fins de contrat proches ou dépassées"),
                 ("a-renseigner", "Statuts de contrat à renseigner"),
                 ("incomplets", "Dossiers incomplets")),
        acces="myrh",
    ),
    # ── ERP RVGI › Tableaux de bord (app/web/erp_page.py, app/services/erp_tdb.py) ──
    # « erp » n'est pas une application du contrôle d'accès : /erp est ouvert
    # par rôle (ROLES_ERP), et accueil_widgets traduit cet accès-là.
    "erp.adv.kpis": Bloc(
        appli="erp", libelle="TDB ADV — carnet", url="/erp#/tdb_adv",
        type="chiffre",
        valeurs=(("commandes", "Commandes à traiter"), ("semaine", "À expédier sous 7 jours"),
                 ("retard", "Commandes en retard"), ("a-facturer", "BL à facturer"),
                 ("sans-dossier", "Commandes sans dossier de prod")),
        acces="erp",
    ),
    "erp.direction.kpis": Bloc(
        appli="erp", libelle="TDB Direction — chiffres du mois", url="/erp#/tdb_direction",
        type="chiffre",
        valeurs=(("rentre-mois", "Rentré ce mois (€)"), ("facturable", "Facturable (€)"),
                 ("facture-mois", "Facturé ce mois (€)"), ("carnet", "Carnet restant (€)")),
        acces="erp",
    ),
    "erp.direction.hier": Bloc(
        appli="erp", libelle="TDB Direction — rentré hier", url="/erp#/tdb_direction",
        type="chiffre",
        valeurs=(("montant", "Rentré hier (€)"), ("commandes", "Commandes rentrées hier"),
                 ("ecart", "Écart à la moyenne 30 j (%)")),
        acces="erp",
    ),
    "erp.achats.kpis": Bloc(
        appli="erp", libelle="TDB Achats", url="/erp#/tdb_achats",
        type="chiffre",
        valeurs=(("retard", "Commandes fournisseurs en retard"), ("semaine", "Attendues sous 7 jours"),
                 ("ouvertes", "Commandes fournisseurs ouvertes"), ("receptions", "Lignes reçues sur 7 jours")),
        acces="erp",
    ),
    "portail.atelier.machine": Bloc(
        appli="portail",
        libelle="Machine de l'atelier",
        url="/",
        type="objet",
        valeurs=(("etat", "État"), ("avancement", "Avancement (%)")),
        textes=("etat",),
        objet="machine", lien="/planning?machine={objet}",
        tons=("etat",),
    ),
}


def _index_alias() -> dict[str, str]:
    idx = {}
    for nom, b in BLOCS.items():
        for a in b.alias:
            idx[a] = nom
    return idx


def resoudre(nom: str) -> tuple[str, Bloc] | None:
    """Nom actuel et bloc, en suivant un éventuel alias. None si le bloc a disparu."""
    if nom in BLOCS:
        return nom, BLOCS[nom]
    actuel = _index_alias().get(nom)
    if actuel:
        return actuel, BLOCS[actuel]
    return None


def _emplacement(url: str) -> tuple[str, str]:
    p = urlsplit(url)
    return p.path or "/", p.fragment


def url_widget(nom: str, url_capture: str, objet: str | None = None) -> str | None:
    """URL à ouvrir pour un widget : la page capturée avec ses filtres.

    Bloc à objet qui déclare un `lien` : on ouvre la page de l'objet (liste
    des cartons, planning de la machine), filtres capturés reportés quand ils
    ne la contredisent pas. Si le bloc a changé de place depuis la capture
    (autre page ou autre onglet en ancre), on part de son emplacement actuel
    avec la même règle.
    """
    r = resoudre(nom)
    if not r:
        return None
    bloc = r[1]
    if bloc.lien and objet:
        return _avec_filtres(bloc.lien.replace("{objet}", quote(str(objet), safe=":")), url_capture)
    if _emplacement(url_capture) == _emplacement(bloc.url):
        return url_capture
    return _avec_filtres(bloc.url, url_capture)


def _avec_filtres(cible: str, url_capture: str) -> str:
    """`cible`, complétée des paramètres capturés qu'elle ne fixe pas déjà."""
    base = urlsplit(cible)
    params = dict(parse_qsl(base.query, keep_blank_values=True))
    for k, v in parse_qsl(urlsplit(url_capture).query, keep_blank_values=True):
        params.setdefault(k, v)
    out = base.path or "/"
    if params:
        out += "?" + urlencode(params)
    if base.fragment:
        out += "#" + base.fragment
    return out


def url_capture_valide(url: str) -> bool:
    """Chemin interne uniquement : jamais d'URL absolue ni de « //hote »."""
    if not isinstance(url, str) or not url.startswith("/") or url.startswith("//"):
        return False
    if len(url) > 2000 or "\\" in url:
        return False
    return not urlsplit(url).scheme and not urlsplit(url).netloc


def valider_widget(data: dict, *, creation: bool) -> dict:
    """Contrôle et normalise un widget reçu du front. Lève ValueError (message affichable)."""
    out: dict = {}

    if creation or "bloc" in data:
        r = resoudre(str(data.get("bloc") or ""))
        if not r:
            raise ValueError("Bloc inconnu — il n'est plus capturable.")
        nom_bloc, bloc = r
        out["bloc"] = nom_bloc
    else:
        bloc = None

    if creation:
        url = data.get("url_capture")
        if not url_capture_valide(url):
            raise ValueError("Adresse de capture invalide.")
        out["url_capture"] = url
        objet = data.get("objet")
        if bloc.objet:
            if objet in (None, ""):
                raise ValueError("Objet suivi manquant.")
            out["objet"] = str(objet)[:120]
        else:
            out["objet"] = None
    elif "url_capture" in data:
        # Filtres modifiés après coup (questionnaire « Modifier l'indicateur ») :
        # seule l'adresse change, jamais le bloc ni l'objet suivi.
        url = data.get("url_capture")
        if not url_capture_valide(url):
            raise ValueError("Adresse de capture invalide.")
        out["url_capture"] = url

    if creation or "nom" in data:
        nom = str(data.get("nom") or "").strip()
        if not nom:
            raise ValueError("Nom de l'indicateur obligatoire.")
        if len(nom) > NOM_WIDGET_MAX:
            raise ValueError(f"Nom trop long — {NOM_WIDGET_MAX} caractères au maximum.")
        out["nom"] = nom

    if creation or "valeurs" in data:
        valeurs = data.get("valeurs") or []
        if not isinstance(valeurs, list):
            raise ValueError("Valeurs invalides.")
        if len(valeurs) > VALEURS_MAX:
            raise ValueError(f"{VALEURS_MAX} valeurs au maximum par indicateur.")
        cles_bloc = {c for c, _ in bloc.valeurs} if bloc else None
        vues, propres = set(), []
        for v in valeurs:
            cle = str((v or {}).get("cle") or "")
            if not _CLE_RE.match(cle) or cle in vues:
                raise ValueError("Valeur clé invalide.")
            if cles_bloc is not None and cle not in cles_bloc:
                raise ValueError("Valeur clé inconnue pour ce bloc.")
            vues.add(cle)
            numerique = bloc is None or cle not in bloc.textes
            propres.append({"cle": cle, "alerte": _valider_alerte(v.get("alerte"), numerique)})
        out["valeurs"] = propres

    if creation or "affichage" in data:
        # Depuis le 04/10/2026, un widget n'affiche que des valeurs. « bloc »
        # reste accepté pour les widgets créés avant.
        aff = data.get("affichage") or "valeurs"
        if aff not in AFFICHAGES:
            raise ValueError("Affichage invalide — bloc ou valeurs.")
        out["affichage"] = aff

    if creation or "hauteur" in data:
        hauteur = data.get("hauteur") or "m"
        if hauteur not in HAUTEURS:
            raise ValueError("Taille invalide — compact, standard ou grand.")
        if hauteur == "l" and bloc is not None and not bloc.grand:
            raise ValueError("Grand format indisponible : ce bloc n'a ni historique ni liste.")
        out["hauteur"] = hauteur

    if creation and not out.get("valeurs"):
        raise ValueError("Cochez au moins une valeur.")
    if out.get("hauteur") == "s" and len(out.get("valeurs") or []) > 1:
        raise ValueError(COMPACT_UNE_VALEUR)
    return out


def _valider_alerte(alerte, numerique: bool = True) -> dict | None:
    if not alerte:
        return None
    if not isinstance(alerte, dict):
        raise ValueError("Alerte invalide.")
    if not numerique:
        raise ValueError("Pas d'alerte sur une valeur texte — le seuil se compare à un nombre.")
    op = alerte.get("op")
    if op not in ALERTE_OPS:
        raise ValueError("Alerte invalide — au-dessus, en dessous ou égal à.")
    seuil = str(alerte.get("seuil") if alerte.get("seuil") is not None else "").strip()
    if not seuil:
        raise ValueError("Seuil d'alerte manquant.")
    try:
        float(seuil.replace(",", "."))
    except ValueError:
        raise ValueError("Seuil d'alerte : un nombre est attendu.") from None
    return {"op": op, "seuil": seuil[:60]}


def erreurs_registre() -> list[str]:
    """Incohérences internes du registre (le test les fait échouer)."""
    errs = []
    alias_vus: dict[str, str] = {}
    for nom, b in BLOCS.items():
        if not _NOM_RE.match(nom):
            errs.append(f"{nom} : nom invalide (appli.onglet.bloc, minuscules)")
        if b.type not in TYPES:
            errs.append(f"{nom} : type {b.type!r} inconnu")
        if not url_capture_valide(b.url):
            errs.append(f"{nom} : url invalide")
        if not b.valeurs:
            errs.append(f"{nom} : aucune valeur clé — un widget n'affiche que des valeurs")
        if b.lien is not None:
            if not b.objet or "{objet}" not in b.lien:
                errs.append(f"{nom} : lien sans objet — « {{objet}} » attendu, et objet= renseigné")
            elif not url_capture_valide(b.lien.replace("{objet}", "x")):
                errs.append(f"{nom} : lien invalide")
        cles = [c for c, _ in b.valeurs]
        if len(set(cles)) != len(cles) or any(not _CLE_RE.match(c) for c in cles):
            errs.append(f"{nom} : clés de valeurs invalides ou en double")
        for t in b.tons:
            if t not in b.textes:
                errs.append(f"{nom} : tons cite {t!r}, absent des textes — seul un texte se colore")
        for t, sens in b.series:
            if t not in cles or t in b.textes:
                errs.append(f"{nom} : série {t!r} absente des valeurs, ou valeur texte")
            if sens not in SENS_SERIE:
                errs.append(f"{nom} : sens de série {sens!r} invalide (+ ou -)")
        if b.appli not in APPLIS:
            errs.append(f"{nom} : appli {b.appli!r} absente d'APPLIS (pastille de l'indicateur)")
        for t in b.textes:
            if t not in cles:
                errs.append(f"{nom} : textes cite {t!r}, absent des valeurs")
        for a in b.alias:
            if a in BLOCS:
                errs.append(f"{nom} : l'alias {a} est aussi un nom actuel")
            if a in alias_vus:
                errs.append(f"{nom} : l'alias {a} est déjà porté par {alias_vus[a]}")
            alias_vus[a] = nom
    for cle, a in APPLIS.items():
        if a.teinte not in TEINTES:
            errs.append(f"APPLIS[{cle}] : teinte {a.teinte!r} inconnue")
        if a.icone not in ICONES_APPLI:
            errs.append(f"APPLIS[{cle}] : icône {a.icone!r} inconnue")
    return errs
