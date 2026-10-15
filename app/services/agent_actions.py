"""
Agent IA — catalogue fermé des écritures, et leur exécution.

L'agent ne connaît que ce catalogue. Chaque action pointe vers un écran
MySifa EXISTANT (méthode + chemin) : rien n'est réécrit ici. À la
confirmation, l'appel est rejoué en interne avec les cookies de
l'utilisateur, donc avec ses droits, les validations de l'écran et sa
ligne dans le journal d'audit — exactement comme s'il avait cliqué.

`preparer()` contrôle la demande avant qu'elle n'atteigne l'utilisateur :
paramètres connus, types, valeurs permises, identifiants qui existent en
base. Une carte n'affiche donc jamais un « produit 4512 » inexistant.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from config import ROLES_ADMIN, ROLES_ADMINISTRATION_ALL, ROLES_PROD, ROLE_DIRECTION, ROLE_SUPERADMIN


class ActionInvalide(ValueError):
    """Message factuel renvoyé à l'agent (qui corrige ou pose une question)."""


ROLES_MATIERES_ADMIN = {ROLE_SUPERADMIN, ROLE_DIRECTION} | ROLES_ADMINISTRATION_ALL
ROLES_MP_ENTREE_SORTIE = {ROLE_SUPERADMIN, ROLE_DIRECTION, "administration_technique"}


def _stock_ecriture(user: dict) -> bool:
    from app.services.auth_service import user_has_app_access
    return user.get("role") != "commercial" and user_has_app_access(user, "stock")


def _role_dans(roles):
    return lambda user: user.get("role") == ROLE_SUPERADMIN or user.get("role") in roles


def _tous(user: dict) -> bool:
    return True


# Paramètre : (type, requis, libellé, aide/valeurs)
#   type : str | int | num | bool | date | datetime | ids (liste d'entiers) | enum:a,b,c
#   Un paramètre dont le nom figure entre {accolades} dans le chemin va dans l'URL.
CATALOGUE: list[dict[str, Any]] = [
    # ── Stock produits finis ─────────────────────────────────────────────
    {
        "cle": "stock_deplacer_lot", "libelle": "Déplacement de stock", "module": "stock",
        "methode": "POST", "chemin": "/api/stock/deplacer-lot", "lien": "/stock", "autorise": _stock_ecriture,
        "aide": "Déplace le lot le plus ancien (FIFO, en entier) d'un produit fini d'un emplacement à un autre. "
                "Pour une quantité partielle : stock_mouvement_pf en sortie puis en entrée.",
        "params": {
            "produit_id": ("int", True, "Produit (produits.id)", ""),
            "emplacement_source": ("str", True, "Depuis", "code emplacement, ex. A121 ; Z0/Z1 zones spéciales"),
            "emplacement_destination": ("str", True, "Vers", "code emplacement"),
            "fsc": ("enum:0,1", False, "Segment FSC", "facultatif"),
        },
    },
    {
        "cle": "stock_mouvement_pf", "libelle": "Mouvement de stock produit fini", "module": "stock",
        "methode": "POST", "chemin": "/api/stock/mouvement", "lien": "/stock", "autorise": _stock_ecriture,
        "aide": "Entrée, sortie, ou inventaire (fixe la quantité absolue) d'un produit fini sur un emplacement.",
        "params": {
            "produit_id": ("int", True, "Produit (produits.id)", ""),
            "emplacement": ("str", True, "Emplacement", "code, ex. B121"),
            "type_mouvement": ("enum:entree,sortie,inventaire", True, "Mouvement", ""),
            "quantite": ("num", True, "Quantité", "> 0"),
            "note": ("str", False, "Note", ""),
            "no_dossier": ("str", False, "Dossier", ""),
            "date_entree": ("date", False, "Date d'entrée", "AAAA-MM-JJ"),
            "fsc": ("enum:0,1", False, "FSC (sortie)", ""),
        },
    },
    # ── Matières premières ───────────────────────────────────────────────
    {
        "cle": "stock_mouvement_mp", "libelle": "Mouvement de stock matière", "module": "stock",
        "methode": "POST", "chemin": "/api/stock/matieres/mouvement", "lien": "/stock?tab=matieres",
        "autorise": _stock_ecriture,
        "aide": "Entrée, sortie ou ajustement (fixe la quantité absolue) d'une matière première. "
                "laize_id obligatoire pour frontal, glassine, complexe (voir mp_matiere_laizes). "
                "Entrée/sortie réservées à superadmin, direction, administration_technique.",
        "params": {
            "matiere_id": ("int", True, "Matière (matieres_premieres.id)", ""),
            "type_mouvement": ("enum:entree,sortie,ajustement", True, "Mouvement", ""),
            "quantite": ("num", True, "Quantité", "> 0 ; absolue pour un ajustement"),
            "laize_id": ("int", False, "Laize", ""),
            "unite_saisie": ("enum:kg,carton,palette", False, "Unité (adhésifs)", ""),
            "ref_bl": ("str", False, "Réf. BL", ""),
            "note": ("str", False, "Note", ""),
        },
    },
    {
        "cle": "matiere_creer", "libelle": "Nouvelle matière première", "module": "stock",
        "methode": "POST", "chemin": "/api/stock/matieres", "lien": "/stock?tab=matieres",
        "autorise": _role_dans(ROLES_MATIERES_ADMIN),
        "aide": "Crée une matière au référentiel.",
        "params": {
            "categorie": ("enum:mandrin,palette,adhesif,carton,frontal,glassine,complexe,encre,autre", True, "Catégorie", ""),
            "reference": ("str", True, "Référence", ""),
            "designation": ("str", True, "Désignation", ""),
            "seuil_alerte": ("num", False, "Seuil d'alerte", ""),
            "sous_categorie": ("str", False, "Sous-catégorie", ""),
            "couleur": ("str", False, "Couleur", ""),
            "abbreviation": ("str", False, "Abréviation", ""),
        },
    },
    {
        "cle": "matiere_modifier", "libelle": "Modification d'une matière", "module": "stock",
        "methode": "PUT", "chemin": "/api/stock/matieres/{matiere_id}", "lien": "/stock?tab=matieres",
        "autorise": _role_dans(ROLES_MATIERES_ADMIN),
        "aide": "Modifie les champs donnés d'une matière (les autres restent inchangés).",
        "params": {
            "matiere_id": ("int", True, "Matière (matieres_premieres.id)", ""),
            "reference": ("str", False, "Référence", ""),
            "designation": ("str", False, "Désignation", ""),
            "seuil_alerte": ("num", False, "Seuil d'alerte", ""),
            "actif": ("enum:0,1", False, "Active", ""),
            "couleur": ("str", False, "Couleur", ""),
            "sous_categorie": ("str", False, "Sous-catégorie", ""),
            "abbreviation": ("str", False, "Abréviation", ""),
            "metres_lineaires_par_bobine": ("num", False, "Mètres par bobine", ""),
            "unites_par_palette": ("num", False, "Unités par palette", ""),
            "matiere_fsc": ("enum:0,1", False, "FSC", ""),
            "intervalle_inventaire_jours": ("int", False, "Intervalle d'inventaire (j)", ""),
            "kg_par_carton": ("num", False, "kg par carton", ""),
            "cartons_par_palette": ("num", False, "Cartons par palette", ""),
            "weight_gsm": ("num", False, "Grammage (g/m²)", ""),
            "epaisseur_um": ("num", False, "Épaisseur (µm)", ""),
        },
    },
    # ── Prix ─────────────────────────────────────────────────────────────
    {
        "cle": "prix_matiere", "libelle": "Prix d'achat d'une matière", "module": "stock",
        "methode": "PUT", "chemin": "/api/stock/valorisation/{matiere_id}", "lien": "/stock?tab=valorisation",
        "autorise": _role_dans(ROLES_MATIERES_ADMIN),
        "aide": "Prix de valorisation MyStock (historisé). Matière en laize : prix_eur_m2 (et/ou "
                "metres_lineaires_par_bobine). Autre matière : prix_unitaire. Lire d'abord le prix actuel "
                "(matieres_premieres.prix_eur_m2 ou mp_valorisation_historique) et le citer.",
        "params": {
            "matiere_id": ("int", True, "Matière (matieres_premieres.id)", ""),
            "prix_eur_m2": ("num", False, "Prix €/m²", ""),
            "prix_unitaire": ("num", False, "Prix unitaire €", ""),
            "metres_lineaires_par_bobine": ("num", False, "Mètres par bobine", ""),
            "note": ("str", False, "Motif", ""),
        },
        "un_parmi": ("prix_eur_m2", "prix_unitaire", "metres_lineaires_par_bobine"),
    },
    {
        "cle": "prix_produit_fini", "libelle": "Prix d'un produit fini", "module": "stock",
        "methode": "PUT", "chemin": "/api/stock/valorisation/pf/{produit_id}", "lien": "/stock?tab=valorisation",
        "autorise": _role_dans(ROLES_MATIERES_ADMIN),
        "aide": "Prix unitaire HT de valorisation d'un produit fini.",
        "params": {
            "produit_id": ("int", True, "Produit (produits.id)", ""),
            "prix_unitaire_ht": ("num", True, "Prix unitaire HT €", ""),
        },
    },
    # ── Production ───────────────────────────────────────────────────────
    {
        "cle": "saisie_modifier", "libelle": "Modification d'une saisie de production", "module": "prod",
        "methode": "PUT", "chemin": "/api/saisies/{row_id}", "lien": "/prod",
        "autorise": _tous,
        "aide": "Modifie une ligne de production_data (id = row_id). Pas de durée directe : on corrige "
                "date_operation, l'opération ou les quantités/métrages. operation = libellé complet commençant "
                "par son code (ex. « 01 Début de production »). Une opération 90 ne peut pas changer de code. "
                "Toujours lire la ligne actuelle et citer l'ancienne valeur.",
        "params": {
            "row_id": ("int", True, "Saisie (production_data.id)", ""),
            "date_operation": ("datetime", False, "Date et heure", "AAAA-MM-JJTHH:MM:SS, heure de Paris"),
            "operation": ("str", False, "Opération", ""),
            "machine": ("str", False, "Machine", ""),
            "no_dossier": ("str", False, "Dossier", ""),
            "operateur": ("str", False, "Opérateur", "admin seulement"),
            "quantite_a_traiter": ("num", False, "Quantité à traiter", ""),
            "quantite_traitee": ("num", False, "Quantité traitée", ""),
            "metrage_prevu": ("num", False, "Métrage prévu", ""),
            "metrage_reel": ("num", False, "Métrage réel", ""),
            "metrage_total_debut": ("num", False, "Compteur début", ""),
            "metrage_total_fin": ("num", False, "Compteur fin", ""),
            "commentaire": ("str", False, "Commentaire", ""),
            "note": ("str", True, "Motif de la correction", "conservé dans modifie_note"),
        },
    },
    {
        "cle": "saisie_supprimer", "libelle": "Suppression d'une saisie de production", "module": "prod",
        "methode": "DELETE", "chemin": "/api/saisies/{row_id}", "lien": "/prod",
        "autorise": _tous,
        "aide": "Supprime une ligne de production_data. Réservé aux corrections d'erreurs manifestes.",
        "params": {"row_id": ("int", True, "Saisie (production_data.id)", "")},
    },
    {
        "cle": "planning_ajouter", "libelle": "Dossier au planning", "module": "planning",
        "methode": "POST", "chemin": "/api/planning/machines/{machine_id}/entries", "lien": "/planning",
        "autorise": _role_dans(ROLES_ADMIN),
        "aide": "Ajoute un dossier sur une machine (machines.id, actif=1). Sans position, placement "
                "automatique : selon la date de livraison si statut attente, sinon en fin de file.",
        "params": {
            "machine_id": ("int", True, "Machine (machines.id)", ""),
            "reference": ("str", True, "Référence dossier", ""),
            "duree_heures": ("num", True, "Durée (h)", "0,75 à 720"),
            "client": ("str", False, "Client", ""),
            "description": ("str", False, "Description", ""),
            "date_livraison": ("date", False, "Livraison", "AAAA-MM-JJ"),
            "date_livraison_imposee": ("enum:0,1", False, "Date imposée", ""),
            "statut": ("enum:attente,en_cours,termine", False, "Statut", "défaut attente"),
            "numero_of": ("str", False, "N° OF", ""),
            "ref_produit": ("str", False, "Réf. produit", ""),
            "laize": ("str", False, "Laize", ""),
            "format_l": ("str", False, "Format L", ""),
            "format_h": ("str", False, "Format H", ""),
            "notes": ("str", False, "Notes", ""),
            "fsc_requis": ("enum:0,1", False, "FSC requis", ""),
            "fsc_type_requis": ("enum:fsc_100,fsc_mix,fsc_mix_credit,fsc_recycled", False, "Type FSC", "si FSC requis"),
        },
    },
    # ── Organisation ─────────────────────────────────────────────────────
    {
        "cle": "calendrier_evenement", "libelle": "Événement au calendrier", "module": "calendrier",
        "methode": "POST", "chemin": "/api/calendrier/events/perso", "lien": "/calendrier",
        "autorise": _tous,
        "aide": "Rendez-vous, visite client, déplacement. Dates ISO AAAA-MM-JJTHH:MM (heure de Paris). "
                "participants = ids d'utilisateurs (users.id, actif=1).",
        "params": {
            "titre": ("str", True, "Titre", ""),
            "date_debut": ("datetime", True, "Début", ""),
            "date_fin": ("datetime", True, "Fin", ""),
            "all_day": ("bool", False, "Journée entière", ""),
            "lieu": ("str", False, "Lieu", ""),
            "note": ("str", False, "Note", ""),
            "visio": ("str", False, "Lien visio", ""),
            "participants": ("ids", False, "Participants", "users.id"),
            "rappel_minutes": ("enum:0,5,10,15,30,60,120,1440", False, "Rappel (min)", ""),
            "prive": ("bool", False, "Privé", ""),
        },
    },
    {
        "cle": "tache_creer", "libelle": "Nouvelle tâche", "module": "taches",
        "methode": "POST", "chemin": "/api/taches", "lien": "/taches",
        "autorise": _tous,
        "aide": "Tâche du gestionnaire. module = code d'application (stock, planning, prod, fabrication…). "
                "assignes = ids d'utilisateurs actifs.",
        "params": {
            "titre": ("str", True, "Titre", ""),
            "description": ("str", False, "Description", ""),
            "type": ("enum:bug,evolution,feature,technique,support,autre", False, "Type", ""),
            "priorite": ("enum:basse,normale,haute,critique", False, "Priorité", ""),
            "statut": ("enum:backlog,a_faire,en_cours,revue,termine", False, "Statut", "défaut backlog"),
            "module": ("str", False, "Module", ""),
            "assignes": ("ids", False, "Assignés", "users.id"),
            "echeance": ("date", False, "Échéance", "AAAA-MM-JJ"),
        },
    },
    {
        "cle": "reunion_action", "libelle": "Action de point de production", "module": "reunions",
        "methode": "POST", "chemin": "/api/reunions/{reunion_id}/actions", "lien": "/prod#reunions",
        "autorise": _role_dans(ROLES_PROD),
        "aide": "Ajoute une action à une réunion (reunions.id ; la plus récente ouverte si l'utilisateur dit "
                "« la réunion en cours »).",
        "params": {
            "reunion_id": ("int", True, "Réunion (reunions.id)", ""),
            "texte": ("str", True, "Action", ""),
            "responsable": ("str", False, "Responsable", "nom"),
            "echeance": ("date", False, "Échéance", "AAAA-MM-JJ"),
        },
    },
    {
        "cle": "postit_creer", "libelle": "Nouveau post-it", "module": "postit",
        "methode": "POST", "chemin": "/api/postits", "lien": "",
        "autorise": _tous,
        "aide": "Post-it personnel de l'utilisateur : type today (aujourd'hui) ou someday (un jour).",
        "params": {
            "type": ("enum:today,someday", True, "Quand", ""),
            "title": ("str", True, "Titre", ""),
        },
    },
    {
        "cle": "postit_tache", "libelle": "Ligne de post-it", "module": "postit",
        "methode": "POST", "chemin": "/api/postits/{postit_id}/tasks", "lien": "",
        "autorise": _tous,
        "aide": "Ajoute une ligne à un post-it de l'utilisateur (postits.id).",
        "params": {
            "postit_id": ("int", True, "Post-it (postits.id)", ""),
            "text": ("str", True, "Ligne", ""),
        },
    },
    # ── Contrôles de cohérence ───────────────────────────────────────────
    {
        "cle": "coherence_expliquer", "libelle": "Écart de cohérence expliqué", "module": "settings",
        "methode": "POST", "chemin": "/api/settings/coherence/{ecart_id}/expliquer",
        "lien": "/settings#coherence",
        "autorise": _role_dans({ROLE_DIRECTION, ROLE_SUPERADMIN}),
        "aide": "Marque un écart de cohérence (coherence_ecarts.id, lu avec mysifa_ecarts) comme "
                "expliqué : il reste visible mais sort de la pastille. À proposer quand l'utilisateur "
                "donne la raison de l'écart ; l'explication reprend ses mots.",
        "params": {
            "ecart_id": ("int", True, "Écart (coherence_ecarts.id)", ""),
            "explication": ("str", True, "Explication", "pourquoi l'écart est normal"),
        },
    },
]
_PAR_CLE = {a["cle"]: a for a in CATALOGUE}


def catalogue_pour(user: dict) -> list[dict]:
    return [a for a in CATALOGUE if a["autorise"](user)]


def description_catalogue(actions: list[dict]) -> str:
    lignes = []
    for a in actions:
        ps = []
        for nom, (typ, req, lib, aide) in a["params"].items():
            t = typ.replace("enum:", "un de : ")
            ps.append(f"{nom}{'*' if req else ''} ({t}{' — ' + aide if aide else ''})")
        lignes.append(f"- {a['cle']} — {a['libelle']}. {a['aide']}\n  Paramètres (* obligatoire) : " + "; ".join(ps))
    return "\n".join(lignes)


# ── Validation ───────────────────────────────────────────────────────────

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$")


def _convertir(nom: str, typ: str, v: Any):
    if typ == "str":
        s = str(v).strip()
        if not s:
            raise ActionInvalide(f"« {nom} » est vide.")
        return s[:4000]
    if typ == "int":
        try:
            return int(str(v).strip())
        except ValueError:
            raise ActionInvalide(f"« {nom} » doit être un entier.")
    if typ == "num":
        try:
            return float(str(v).replace(",", ".").strip())
        except ValueError:
            raise ActionInvalide(f"« {nom} » doit être un nombre.")
    if typ == "bool":
        return v in (True, 1, "1", "true", "oui", "True")
    if typ == "date":
        s = str(v).strip()[:10]
        if not _DATE_RE.match(s):
            raise ActionInvalide(f"« {nom} » : date attendue AAAA-MM-JJ.")
        return s
    if typ == "datetime":
        s = str(v).strip().replace(" ", "T")
        if not _DT_RE.match(s):
            raise ActionInvalide(f"« {nom} » : date et heure attendues AAAA-MM-JJTHH:MM.")
        return s
    if typ == "ids":
        vals = v if isinstance(v, list) else [v]
        try:
            return [int(x) for x in vals]
        except (TypeError, ValueError):
            raise ActionInvalide(f"« {nom} » : liste d'identifiants entiers attendue.")
    if typ == "objets":
        # Liste d'objets (lignes d'une pièce…) : la forme est contrôlée par
        # l'action qui la déclare (`construire`, `detailler`).
        if not isinstance(v, list) or not all(isinstance(x, dict) for x in v):
            raise ActionInvalide(f"« {nom} » : liste d'objets attendue.")
        if len(json.dumps(v)) > 20000:
            raise ActionInvalide(f"« {nom} » : liste trop longue.")
        return v
    if typ.startswith("enum:"):
        permis = typ[5:].split(",")
        s = str(v).strip().lower() if not isinstance(v, bool) else ("1" if v else "0")
        if s not in permis:
            raise ActionInvalide(f"« {nom} » : valeur « {v} » hors liste ({', '.join(permis)}).")
        return int(s) if s.isdigit() and nom not in ("statut",) else s
    raise ActionInvalide(f"Type inconnu pour « {nom} ».")


# Identifiants à vérifier en base, et libellé lisible pour la carte.
_RESOLVEURS = {
    "produit_id": ("SELECT reference || COALESCE(' — ' || designation, '') FROM produits WHERE id=?", "Produit"),
    "matiere_id": ("SELECT reference || ' — ' || COALESCE(designation, '') FROM matieres_premieres WHERE id=?", "Matière"),
    "machine_id": ("SELECT nom FROM machines WHERE id=?", "Machine"),
    "row_id": ("SELECT COALESCE(no_dossier,'?') || ' · ' || COALESCE(operation,'') || ' · ' || "
               "COALESCE(substr(date_operation,1,16),'') || ' · ' || COALESCE(machine,'') "
               "FROM production_data WHERE id=?", "Saisie"),
    "reunion_id": ("SELECT COALESCE(titre, 'Réunion') || ' (' || substr(COALESCE(date_debut,''),1,10) || ')' "
                   "FROM reunions WHERE id=?", "Réunion"),
    "laize_id": ("SELECT 'laize ' || id FROM mp_matiere_laizes WHERE id=?", "Laize"),
    "ecart_id": ("SELECT titre || ' — ' || COALESCE(detail, '') FROM coherence_ecarts WHERE id=?", "Écart"),
}


def _libelle_id(conn, nom: str, v: int) -> str:
    sql, quoi = _RESOLVEURS[nom]
    try:
        row = conn.execute(sql, (v,)).fetchone()
    except Exception:
        return str(v)   # table absente sur une base ancienne : l'écran tranchera
    if not row:
        raise ActionInvalide(f"{quoi} {v} introuvable — résoudre l'identifiant avec les outils de lecture.")
    return f"{row[0]} (#{v})"


def _noms_users(conn, ids: list[int]) -> str:
    noms = []
    for i in ids:
        row = conn.execute("SELECT nom FROM users WHERE id=? AND COALESCE(actif,1)=1", (i,)).fetchone()
        if not row:
            raise ActionInvalide(f"Utilisateur {i} introuvable ou inactif.")
        noms.append(row[0])
    return ", ".join(noms)


def preparer(user: dict, cle: str, params: dict, conn=None) -> dict:
    """Rend {cle, libelle, module, methode, chemin, corps, details}. Lève ActionInvalide."""
    a = _PAR_CLE.get(cle)
    if not a:
        raise ActionInvalide(f"Action « {cle} » inconnue.")
    if not a["autorise"](user):
        raise ActionInvalide(f"Action « {a['libelle']} » non permise pour le rôle {user.get('role')}.")
    if not isinstance(params, dict):
        raise ActionInvalide("Paramètres attendus sous forme d'objet.")
    inconnus = set(params) - set(a["params"])
    if inconnus:
        raise ActionInvalide(f"Paramètre(s) inconnu(s) : {', '.join(sorted(inconnus))}.")
    valeurs = {}
    for nom, (typ, req, _lib, _aide) in a["params"].items():
        v = params.get(nom)
        if v is None or (isinstance(v, str) and not v.strip()):
            if req:
                raise ActionInvalide(f"Paramètre obligatoire manquant : {nom}.")
            continue
        valeurs[nom] = _convertir(nom, typ, v)
    if a.get("un_parmi") and not any(k in valeurs for k in a["un_parmi"]):
        raise ActionInvalide(f"Donner au moins un de : {', '.join(a['un_parmi'])}.")

    from database import get_db
    details = []
    with (get_db() if conn is None else _Nul(conn)) as c:
        if a.get("detailler"):
            details.extend(a["detailler"](c, valeurs))
        for nom, v in valeurs.items():
            lib = a["params"][nom][2]
            if a.get("detailler") and (a["params"][nom][0] in ("ids", "objets") or nom.endswith("_id")):
                continue
            if nom in _RESOLVEURS:
                details.append([lib.split(" (")[0], _libelle_id(c, nom, v)])
            elif a["params"][nom][0] == "ids":
                details.append([lib, _noms_users(c, v)])
            elif nom not in ("note",) or cle != "saisie_modifier":
                details.append([lib, "oui" if v is True else ("non" if v is False else v)])
        if cle == "saisie_modifier":
            details.append(["Motif", valeurs["note"]])

    chemin = a["chemin"]
    corps = {}
    for nom, v in valeurs.items():
        if "{" + nom + "}" in chemin:
            chemin = chemin.replace("{" + nom + "}", str(int(v)))
        else:
            corps[nom] = v
    if a.get("construire"):
        corps = a["construire"](corps)
    return {"cle": cle, "libelle": a["libelle"], "module": a["module"], "methode": a["methode"],
            "chemin": chemin, "corps": corps, "details": details, "lien": a.get("lien", "")}


# ── Lectures d'écran ─────────────────────────────────────────────────────
# Ce qu'un écran AFFICHE se lit à l'écran, pas en SQL : le stock d'un
# emplacement n'est pas la somme des mouvements ni des lots, c'est ce que
# calcule l'écran MyStock. Même mécanique que les écritures (appel interne
# avec la session de l'utilisateur), en GET seulement.
LECTURES: list[dict[str, Any]] = [
    {"cle": "stock_emplacement", "chemin": "/api/stock/emplacements/{emplacement}",
     "aide": "Contenu d'un emplacement tel que MyStock l'affiche (références, quantités, inventaire).",
     "params": {"emplacement": ("str", True, "code, ex. A141")}},
    {"cle": "stock_recherche", "chemin": "/api/stock/search",
     "aide": "Recherche MyStock (produits finis et emplacements) sur un fragment.",
     "params": {"q": ("str", True, "fragment de référence, désignation ou emplacement")}},
    {"cle": "stock_produits", "chemin": "/api/stock/produits",
     "aide": "Liste des produits finis avec leur stock total, filtrée par q.",
     "params": {"q": ("str", False, "fragment")}},
    {"cle": "stock_produit_emplacements", "chemin": "/api/stock/produits/{produit_id}/emplacements",
     "aide": "Où se trouve un produit fini, emplacement par emplacement.",
     "params": {"produit_id": ("int", True, "produits.id")}},
    {"cle": "stock_emplacements_liste", "chemin": "/api/stock/emplacements-list",
     "aide": "Liste des codes d'emplacement connus.", "params": {}},
    {"cle": "matieres", "chemin": "/api/stock/matieres",
     "aide": "Matières premières avec leur stock (écran Matières premières).", "params": {}},
    {"cle": "matiere_laizes", "chemin": "/api/stock/matieres/{matiere_id}/laizes",
     "aide": "Stock d'une matière par laize.", "params": {"matiere_id": ("int", True, "matieres_premieres.id")}},
    {"cle": "planning_machines", "chemin": "/api/planning/machines",
     "aide": "Machines du planning (id, nom).", "params": {}},
    {"cle": "planning_dossiers", "chemin": "/api/planning/machines/{machine_id}/entries",
     "aide": "Dossiers au planning d'une machine, dans l'ordre de la file.",
     "params": {"machine_id": ("int", True, "machines.id")}},
    {"cle": "saisies", "chemin": "/api/saisies",
     "aide": "Saisies de production (écran Saisies) filtrées.",
     "params": {"no_dossier": ("str", False, ""), "machine": ("str", False, ""), "operateur": ("str", False, ""),
                "date_from": ("str", False, "AAAA-MM-JJ"), "date_to": ("str", False, "AAAA-MM-JJ"),
                "limit": ("int", False, "défaut 100")}},
    {"cle": "taches_meta", "chemin": "/api/taches/meta",
     "aide": "Listes de référence des tâches : modules, services, utilisateurs assignables.", "params": {}},
    {"cle": "calendrier_invitables", "chemin": "/api/calendrier/invitables",
     "aide": "Personnes qu'on peut inviter à un événement (ids).", "params": {}},
    {"cle": "reunion_en_cours", "chemin": "/api/reunions/contexte",
     "aide": "Point de production ouvert par l'utilisateur, s'il y en a un.", "params": {}},
    {"cle": "reunions", "chemin": "/api/reunions",
     "aide": "Points de production, du plus récent au plus ancien.", "params": {}},
    {"cle": "mes_postits", "chemin": "/api/postits",
     "aide": "Post-its de l'utilisateur connecté (les siens seulement).", "params": {}},
]
_LECTURES = {l["cle"]: l for l in LECTURES}


def description_lectures() -> str:
    lignes = []
    for l in LECTURES:
        ps = ", ".join(f"{n}{'*' if r else ''}" + (f" ({a})" if a else "") for n, (_t, r, a) in l["params"].items())
        lignes.append(f"- {l['cle']} — {l['aide']}" + (f" Paramètres : {ps}" if ps else ""))
    return "\n".join(lignes)


async def lire(app, cookies: dict, cle: str, params: dict) -> Any:
    """GET interne sur un écran du catalogue. Lève ActionInvalide."""
    import httpx
    from urllib.parse import quote
    l = _LECTURES.get(cle)
    if not l:
        raise ActionInvalide(f"Écran « {cle} » inconnu.")
    params = params if isinstance(params, dict) else {}
    inconnus = set(params) - set(l["params"])
    if inconnus:
        raise ActionInvalide(f"Paramètre(s) inconnu(s) : {', '.join(sorted(inconnus))}.")
    chemin, query = l["chemin"], {}
    for nom, (typ, req, _a) in l["params"].items():
        v = params.get(nom)
        if v in (None, ""):
            if req:
                raise ActionInvalide(f"Paramètre obligatoire manquant : {nom}.")
            continue
        v = _convertir(nom, typ, v)
        if "{" + nom + "}" in chemin:
            chemin = chemin.replace("{" + nom + "}", quote(str(v), safe=""))
        else:
            query[nom] = v
    if cle == "saisies":
        query.setdefault("limit", 100)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mysifa.interne",
                                 cookies=cookies, timeout=60) as client:
        r = await client.get(chemin, params=query)
    try:
        data = r.json()
    except Exception:
        data = r.text[:2000]
    if r.status_code >= 400:
        raise ActionInvalide(f"Écran {cle} : {_message(data, r.status_code) or r.status_code}")
    if cle == "stock_emplacement" and isinstance(data, dict):
        # L'écran affiche aussi l'historique de l'emplacement : sans lui,
        # l'agent ne confond plus le stock présent avec les mouvements passés.
        data = {k: v for k, v in data.items() if k not in ("mouvements", "historique")}
    return data


class _Nul:
    """Contexte qui rend une connexion déjà ouverte sans la fermer."""
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *a):
        return False


# ── Exécution ────────────────────────────────────────────────────────────

def _message(data: Any, statut: int) -> str:
    if isinstance(data, dict):
        d = data.get("detail")
        if isinstance(d, str):
            return d
        if isinstance(d, list):
            return "; ".join(str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in d)[:300]
        if isinstance(d, dict):
            return str(d.get("message") or d)[:300]
        if data.get("warning"):
            return str(data["warning"])[:300]
    return "" if statut < 400 else f"Erreur {statut}."


async def executer(request, action: dict) -> dict:
    """Rejoue l'appel dans l'application, avec les cookies de l'utilisateur.

    Le contrôle de droits, la validation et le journal sont ceux de l'écran
    appelé. Rend {ok, statut_http, message, lien, reponse}.
    """
    import httpx
    corps = json.loads(action.get("corps_json") or "{}")
    lien = _PAR_CLE.get(action["cle"], {}).get("lien", "")
    try:
        transport = httpx.ASGITransport(app=request.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://mysifa.interne",
                                     cookies=dict(request.cookies), timeout=60) as client:
            kw: dict[str, Any] = {}
            if action["methode"] in ("POST", "PUT", "PATCH"):
                kw["json"] = corps
            r = await client.request(action["methode"], action["chemin"], **kw)
    except Exception as e:
        return {"ok": False, "statut_http": 0, "message": f"Appel interne en échec : {type(e).__name__}.", "lien": ""}
    try:
        data = r.json()
    except Exception:
        data = None
    ok = 200 <= r.status_code < 300 and not (isinstance(data, dict) and data.get("success") is False)
    msg = _message(data, r.status_code)
    if ok and not msg:
        nid = data.get("id") if isinstance(data, dict) else None
        msg = f"Identifiant {nid}." if nid else ""
    return {"ok": ok, "statut_http": r.status_code, "message": msg, "lien": lien if ok else "",
            "reponse": data if isinstance(data, (dict, list)) else None}


# ── Nouvel ERP ───────────────────────────────────────────────────────────
# Ses actions et lectures vivent dans leur propre module, au même format.
from app.services import agent_actions_erp as _erp  # noqa: E402

CATALOGUE.extend(_erp.ACTIONS)
_PAR_CLE.update({a["cle"]: a for a in _erp.ACTIONS})
LECTURES.extend(_erp.LECTURES)
_LECTURES.update({l["cle"]: l for l in _erp.LECTURES})
