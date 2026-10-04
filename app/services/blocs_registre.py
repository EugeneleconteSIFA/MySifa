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
from urllib.parse import parse_qsl, urlencode, urlsplit

# Plafond décidé le 03/10/2026 : au-delà, un widget devient illisible.
VALEURS_MAX = 4
NOM_WIDGET_MAX = 80
HAUTEURS = ("s", "m", "l")
AFFICHAGES = ("bloc", "valeurs")
TYPES = ("chiffre", "liste", "tableau", "graphique", "etat", "objet", "fiche")
# Opérateurs d'alerte : comparaison numérique, ou égalité pour un état
# (« rouge si Arrêt »).
ALERTE_OPS = (">", "<", "=")

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
    "expe.departs.programmes": Bloc(
        appli="expe",
        libelle="Départs programmés",
        url="/expe#suivi_departs",
        type="tableau",
        valeurs=(("lignes", "Départs en attente"),),
        acces="expe",
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
        acces="prod", objet="machine",
    ),
    "prod.ensemble.sanity": Bloc(
        appli="prod", libelle="Qualité de saisie", url="/prod?page=production",
        type="chiffre", valeurs=(("score", "Score"),), acces="prod",
    ),
    "prod.ensemble.quantites": Bloc(
        appli="prod", libelle="Quantités produites", url="/prod?page=production",
        type="chiffre",
        valeurs=(("metrage", "Métrage (m)"), ("dossiers", "Dossiers produits"),
                 ("vitesse", "Vitesse (m/min)")),
        acces="prod",
    ),
    "prod.ensemble.temps": Bloc(
        appli="prod", libelle="Temps de production", url="/prod?page=production",
        type="chiffre",
        valeurs=(("production", "Production (min)"), ("calage", "Calage (min)"),
                 ("arrets", "Arrêts (min)")),
        acces="prod",
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
    ),
    # ── Planning machine (app/web/planning_page.py) ──
    "planning.dossiers": Bloc(
        appli="planning", libelle="Dossiers au planning", url="/planning",
        type="objet",
        valeurs=(("en-cours", "Dossier en cours"), ("attente", "Dossiers en attente"),
                 ("charge", "Charge en attente (h)")),
        acces="planning", objet="machine",
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
    ),
    # ── Coffre RH (app/web/rh_coffre_page.py) ──
    "rh-coffre.ndf": Bloc(
        appli="rh_coffre", libelle="Notes de frais à valider", url="/rh/coffre#ndf",
        type="chiffre",
        valeurs=(("a-valider", "Notes à valider"), ("montant", "Montant à valider (€)")),
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
    ),
    # ── MyCompta › Outil RH (app/web/compta_rh_outil_assets.py) ──
    "compta.rh.contrats": Bloc(
        appli="compta", libelle="Suivi RH des employés", url="/compta#rhoutil",
        type="chiffre",
        valeurs=(("fin-proche", "Fins de contrat proches ou dépassées"),
                 ("a-renseigner", "Statuts de contrat à renseigner"),
                 ("incomplets", "Dossiers incomplets")),
        acces="compta",
    ),
    "portail.atelier.machine": Bloc(
        appli="portail",
        libelle="Machine de l'atelier",
        url="/",
        type="objet",
        valeurs=(("etat", "État"), ("avancement", "Avancement (%)")),
        objet="machine",
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


def url_widget(nom: str, url_capture: str) -> str | None:
    """URL à ouvrir pour un widget : la page capturée avec ses filtres.

    Si le bloc a changé de place depuis la capture (autre page ou autre onglet
    en ancre), on part de son emplacement actuel et on y reporte les filtres
    capturés qui ne contredisent pas l'emplacement.
    """
    r = resoudre(nom)
    if not r:
        return None
    bloc = r[1]
    if _emplacement(url_capture) == _emplacement(bloc.url):
        return url_capture
    base = urlsplit(bloc.url)
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

    if creation or "nom" in data:
        nom = str(data.get("nom") or "").strip()
        if not nom:
            raise ValueError("Nom du widget obligatoire.")
        if len(nom) > NOM_WIDGET_MAX:
            raise ValueError(f"Nom trop long — {NOM_WIDGET_MAX} caractères au maximum.")
        out["nom"] = nom

    if creation or "valeurs" in data:
        valeurs = data.get("valeurs") or []
        if not isinstance(valeurs, list):
            raise ValueError("Valeurs invalides.")
        if len(valeurs) > VALEURS_MAX:
            raise ValueError(f"{VALEURS_MAX} valeurs au maximum par widget.")
        cles_bloc = {c for c, _ in bloc.valeurs} if bloc else None
        vues, propres = set(), []
        for v in valeurs:
            cle = str((v or {}).get("cle") or "")
            if not _CLE_RE.match(cle) or cle in vues:
                raise ValueError("Valeur clé invalide.")
            if cles_bloc is not None and cle not in cles_bloc:
                raise ValueError("Valeur clé inconnue pour ce bloc.")
            vues.add(cle)
            propres.append({"cle": cle, "alerte": _valider_alerte(v.get("alerte"))})
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
            raise ValueError("Hauteur invalide — s, m ou l.")
        out["hauteur"] = hauteur

    if creation and not out.get("valeurs"):
        raise ValueError("Cochez au moins une valeur.")
    return out


def _valider_alerte(alerte) -> dict | None:
    if not alerte:
        return None
    if not isinstance(alerte, dict):
        raise ValueError("Alerte invalide.")
    op = alerte.get("op")
    if op not in ALERTE_OPS:
        raise ValueError("Alerte invalide — au-dessus, en dessous ou égal à.")
    seuil = str(alerte.get("seuil") if alerte.get("seuil") is not None else "").strip()
    if not seuil:
        raise ValueError("Seuil d'alerte manquant.")
    if op in (">", "<"):
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
        cles = [c for c, _ in b.valeurs]
        if len(set(cles)) != len(cles) or any(not _CLE_RE.match(c) for c in cles):
            errs.append(f"{nom} : clés de valeurs invalides ou en double")
        for a in b.alias:
            if a in BLOCS:
                errs.append(f"{nom} : l'alias {a} est aussi un nom actuel")
            if a in alias_vus:
                errs.append(f"{nom} : l'alias {a} est déjà porté par {alias_vus[a]}")
            alias_vus[a] = nom
    return errs
