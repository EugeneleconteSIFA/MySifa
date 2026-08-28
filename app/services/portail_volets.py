"""Volets du portail — le catalogue des sous-menus.

Le portail affiche deux familles de raccourcis : la barre d'icônes en haut à
droite (profil, paramètres, calendrier, tâches, messagerie, base, ERP) et les
tuiles d'application au centre. Chacun ouvre au survol un volet qui donne les
destinations réelles du module, plutôt que d'obliger à ouvrir la page pour
choisir ensuite un onglet.

Ce fichier est le référentiel de ces volets. Il est en Python, côté serveur,
pour la même raison que `erp_catalogue.py` : le portail ne doit rien savoir des
écrans de SIFA. Un client Kernse reçoit ses volets à lui, filtrés par ses rôles,
sans qu'une ligne de JavaScript n'ait à changer. Écrire ces entrées en dur dans
le front reviendrait à livrer « Besoins matières » et « Colisage » à une
imprimerie qui n'a ni l'un ni l'autre.

Trois règles pour ajouter une entrée :

1. **Une URL qui existe.** Chaque `url` ci-dessous a été relevée dans les routes
   FastAPI ou dans la liste des ancres valides de la page visée (par exemple
   `QUALITE_PERSIST_VIEWS` pour `/qualite#audits-list`). Une entrée qui pointe
   vers une ancre inventée ouvre la page sur son onglet par défaut sans le dire :
   l'utilisateur croit avoir raté son clic.
2. **Pas de compteur inventé.** `compteur` ne peut valoir qu'une des sources que
   le portail connaît déjà (`taches`, `messages`, `calendrier`, `qualite`,
   `rh_coffre`). Le front y met le nombre qu'il a déjà chargé ; il n'affiche rien
   s'il ne l'a pas. Un badge faux est pire que pas de badge.
3. **Deux entrées minimum, sinon pas de volet.** Un volet qui ne propose que la
   page elle-même ajoute un survol et n'apporte rien.
"""

from __future__ import annotations

from typing import Any, Optional

# ── Rôles ────────────────────────────────────────────────────────────────────
#
# `roles=None` sur une entrée signifie « tout le monde ». Sinon c'est la liste
# exacte des rôles qui la voient. Le filtrage se fait ici, jamais dans le front :
# une entrée absente de la réponse n'existe pas pour ce navigateur.

_ADMIN = ("superadmin", "direction")
_ADMIN_LARGE = ("superadmin", "direction", "administration",
                "administration_ventes", "administration_technique")


def _entree(cle, label, url, icone, resume="", roles=None, compteur=None):
    return {"cle": cle, "label": label, "url": url, "icone": icone,
            "resume": resume, "roles": roles, "compteur": compteur}


def _groupe(titre, entrees):
    return {"titre": titre, "entrees": entrees}


# ── Volets de la barre d'icônes ──────────────────────────────────────────────

VOLETS_RAIL = [
    {
        "cle": "profil",
        "titre": "Mon profil",
        "resume": "Compte, affichage et notifications",
        "icone": "user",
        "roles": None,
        "groupes": [
            _groupe("Mon compte", [
                _entree("profil_info", "Mes informations", "/profil#info", "user",
                        "Nom, coordonnées, mot de passe"),
                _entree("profil_prefs", "Préférences d'affichage", "/profil#prefs", "sliders",
                        "Thème, palette, fluidité du poste"),
                _entree("profil_notifs", "Mes notifications", "/profil#notifs", "alert-circle",
                        "Alertes, annonces, rappels"),
            ]),
            _groupe("Mes vues", [
                _entree("profil_cal", "Mes agendas & couleurs", "/profil#calendrier", "calendar"),
                _entree("profil_dash", "Mes dashboards", "/profil#dashboards", "trending-up"),
            ]),
        ],
        "pied": {"label": "Ouvrir mon profil", "url": "/profil"},
    },
    {
        "cle": "settings",
        "titre": "Paramètres",
        "resume": "Administration de l'instance",
        "icone": "sliders",
        "roles": _ADMIN_LARGE,
        "groupes": [
            _groupe("Utilisateurs", [
                _entree("set_users", "Comptes & rôles", "/settings#users", "users"),
                _entree("set_matrix", "Matrice d'accès", "/settings#matrix", "shield-check", roles=_ADMIN),
                _entree("set_defaults", "Accès par défaut", "/settings#defaults", "shield-check", roles=_ADMIN),
            ]),
            _groupe("Référentiels atelier", [
                _entree("set_machines", "Machines", "/settings#machines", "tool"),
                _entree("set_ops", "Codes opérations", "/settings#operations", "grid"),
                _entree("set_empl", "Emplacements", "/settings#emplacements", "package"),
            ]),
            _groupe("Contacts", [
                _entree("set_clients", "Clients", "/settings#clients", "users"),
                _entree("set_fourn", "Fournisseurs", "/settings#fournisseurs", "truck"),
            ]),
            _groupe("Déploiement & audit", [
                _entree("set_updates", "Annonces de mise à jour", "/settings#updates", "alert-circle", roles=_ADMIN),
                _entree("set_promote", "Promouvoir & santé du dépôt", "/settings#promote", "cloud-upload", roles=_ADMIN),
                _entree("set_audit", "Journal d'audit", "/settings#audit", "file-text", roles=_ADMIN),
            ]),
        ],
        "pied": {"label": "Ouvrir les paramètres", "url": "/settings"},
    },
    {
        "cle": "taches",
        "titre": "Gestionnaire de tâches",
        "resume": "Ce que l'équipe doit traiter",
        "icone": "check-circle",
        "roles": None,
        "groupes": [
            _groupe("Vues", [
                _entree("tac_kanban", "Kanban", "/taches#kanban", "grid",
                        "À faire, en cours, terminé", compteur="taches"),
                _entree("tac_liste", "Liste", "/taches#liste", "file-text",
                        "Toutes les tâches actives, filtrables"),
                _entree("tac_arch", "Archives", "/taches#archives", "folder"),
            ]),
        ],
        "pied": {"label": "Ouvrir le gestionnaire", "url": "/taches"},
    },
    {
        "cle": "messages",
        "titre": "Messagerie",
        "resume": "Conversations d'équipe",
        "icone": "mail",
        "roles": None,
        "groupes": [
            _groupe("Raccourcis", [
                _entree("msg_ouvrir", "Mes conversations", "/messages", "mail",
                        compteur="messages"),
                _entree("msg_annonces", "Annonces diffusées", "/settings#updates", "alert-circle",
                        roles=_ADMIN),
            ]),
        ],
        "pied": {"label": "Ouvrir la messagerie", "url": "/messages"},
    },
    {
        "cle": "calendrier",
        "titre": "Calendrier",
        "resume": "Événements et invitations",
        "icone": "calendar",
        "roles": None,
        "groupes": [
            _groupe("Mon agenda", [
                _entree("cal_ouvrir", "Mes événements", "/calendrier", "calendar",
                        compteur="calendrier"),
                _entree("cal_couleurs", "Agendas & couleurs", "/profil#calendrier", "sliders"),
            ]),
            _groupe("Équipe", [
                _entree("cal_prh", "Planning du personnel", "/planning-rh#planning", "users"),
                _entree("cal_conges", "Congés", "/planning-rh#conges", "sun"),
            ]),
        ],
        "pied": {"label": "Ouvrir le calendrier", "url": "/calendrier"},
    },
    {
        "cle": "db",
        "titre": "Base de données",
        "resume": "Consultation et santé technique",
        "icone": "database",
        "roles": _ADMIN,
        "groupes": [
            _groupe("Consultation", [
                _entree("db_explorer", "Explorateur de tables", "/db", "grid"),
            ]),
            _groupe("Technique", [
                _entree("db_sante", "Santé du dépôt & migrations", "/settings#promote", "shield-check"),
                _entree("db_perf", "Fluidité des postes", "/perf-postes", "trending-up"),
            ]),
        ],
        "pied": {"label": "Ouvrir la base", "url": "/db"},
    },
    {
        # Seul volet dont le contenu ne vient pas d'ici : les écrans RVGI
        # dépendent de ce que le miroir contient réellement, et c'est
        # `/api/erp/menu` qui le sait (catalogue ERP + rôle + écrans servis).
        # Le catalogue ne déclare donc que l'enveloppe.
        "cle": "erp",
        "titre": "ERP — lecture RVGI",
        "resume": "Miroir en lecture seule",
        "icone": "database",
        "roles": _ADMIN_LARGE,
        "source": "erp",
        "groupes": [],
        "pied": {"label": "Ouvrir l'ERP", "url": "/erp"},
    },
]


# ── Volets des tuiles d'application ──────────────────────────────────────────
#
# La clé est l'identifiant de tuile utilisé par le portail (`data-portal-id`).
# Une tuile absente d'ici garde son clic simple, sans volet — c'est le cas des
# modules qui n'ont qu'une seule destination.

VOLETS_TUILES = {
    "prod": {
        "titre": "MyProd",
        "groupes": [_groupe("Aller à", [
            _entree("prod_suivi", "Suivi de production", "/prod", "wrench"),
            _entree("prod_planning", "Planning atelier", "/planning", "calendar"),
        ])],
        "pied": {"label": "Ouvrir MyProd", "url": "/prod"},
    },
    "stock": {
        "titre": "MyStock",
        "groupes": [_groupe("Aller à", [
            _entree("stock_produits", "Stocks produits", "/stock", "package"),
            _entree("stock_traca", "Traçabilité bobines", "/stock?tab=traca", "grid"),
            _entree("stock_pricing", "Produits & coûts matières", "/pricing/mystock", "calculator"),
        ])],
        "pied": {"label": "Ouvrir MyStock", "url": "/stock"},
    },
    "print": {
        "titre": "MyPrint",
        "groupes": [_groupe("Aller à", [
            _entree("print_traca", "Étiquettes de traçabilité", "/stock?tab=traca", "printer"),
            _entree("print_imprimantes", "Imprimantes", "/settings#printers", "sliders",
                    roles=_ADMIN_LARGE),
        ])],
        "pied": {"label": "Ouvrir MyPrint", "url": "/stock?tab=traca"},
    },
    "pricing": {
        "titre": "Coûts matières",
        "groupes": [
            _groupe("Référentiel", [
                _entree("pri_mystock", "Produits MyStock", "/pricing/mystock", "package"),
                _entree("pri_materials", "Matières", "/pricing/materials", "grid"),
                _entree("pri_products", "Produits devisés", "/pricing/products", "calculator"),
            ]),
            _groupe("Paramétrage", [
                _entree("pri_fourn", "Fournisseurs", "/pricing/fournisseurs", "truck"),
                _entree("pri_settings", "Marges & paramètres", "/pricing/settings", "sliders"),
            ]),
        ],
        "pied": {"label": "Ouvrir Coûts matières", "url": "/pricing"},
    },
    "qualite": {
        "titre": "MyQualité",
        "groupes": [_groupe("Aller à", [
            _entree("qua_nc", "Non-conformités", "/qualite#list", "shield-check", compteur="qualite"),
            _entree("qua_audits", "Audits client", "/qualite#audits-list", "check-circle"),
            _entree("qua_ress", "Ressources & certificats", "/qualite#ressources-list", "folder"),
            _entree("qua_ref", "Référentiel", "/qualite#ref-list", "file-text"),
        ])],
        "pied": {"label": "Ouvrir MyQualité", "url": "/qualite"},
    },
    "coffre": {
        "titre": "Mon coffre",
        "groupes": [_groupe("Aller à", [
            _entree("cof_bul", "Mes bulletins de paie", "/coffre#bulletins", "lock"),
            _entree("cof_doc", "Mes documents", "/coffre#documents", "folder"),
            _entree("cof_ndf", "Mes notes de frais", "/coffre#ndf", "calculator"),
        ])],
        "pied": {"label": "Ouvrir Mon coffre", "url": "/coffre"},
    },
    "rh_coffre": {
        "titre": "Coffre RH",
        "groupes": [_groupe("Aller à", [
            _entree("rhc_bul", "Dépôt des bulletins", "/rh/coffre#bulletins", "folder"),
            _entree("rhc_ndf", "Notes de frais à valider", "/rh/coffre#ndf", "calculator",
                    compteur="rh_coffre"),
        ])],
        "pied": {"label": "Ouvrir Coffre RH", "url": "/rh/coffre"},
    },
    "planning_rh": {
        "titre": "Planning RH",
        "groupes": [_groupe("Aller à", [
            _entree("prh_planning", "Planning du personnel", "/planning-rh#planning", "users"),
            _entree("prh_conges", "Congés", "/planning-rh#conges", "sun"),
        ])],
        "pied": {"label": "Ouvrir Planning RH", "url": "/planning-rh"},
    },
    "maintenance": {
        "titre": "Maintenance",
        "groupes": [_groupe("Aller à", [
            _entree("mai_planning", "Planning des interventions", "/maintenance#planning", "calendar"),
            _entree("mai_ctrl", "Contrôles", "/maintenance#controles", "check-circle"),
            _entree("mai_ops", "Opérations", "/maintenance#operations", "tool"),
        ])],
        "pied": {"label": "Ouvrir Maintenance", "url": "/maintenance"},
    },
}


# ── Filtrage ─────────────────────────────────────────────────────────────────

def _visible(roles: Optional[tuple], role: str) -> bool:
    return True if not roles else str(role or "") in roles


def _volet_filtre(volet: dict, role: str) -> Optional[dict]:
    """Le volet réduit à ce que ce rôle a le droit de voir, ou None."""
    if not _visible(volet.get("roles"), role):
        return None
    groupes = []
    for g in volet.get("groupes", []):
        entrees = [e for e in g["entrees"] if _visible(e.get("roles"), role)]
        if entrees:
            groupes.append({"titre": g["titre"],
                            "entrees": [{k: v for k, v in e.items() if k != "roles"}
                                        for e in entrees]})
    # Un volet sans entrée n'a d'intérêt que s'il est rempli ailleurs (ERP).
    if not groupes and volet.get("source") is None:
        return None
    out = {k: v for k, v in volet.items() if k not in ("roles", "groupes")}
    out["groupes"] = groupes
    return out


def volets_pour(role: str) -> dict[str, Any]:
    """Les volets visibles par ce rôle : barre d'icônes et tuiles."""
    rail = {}
    for v in VOLETS_RAIL:
        f = _volet_filtre(v, role)
        if f:
            rail[f["cle"]] = f
    tuiles = {}
    for cle, v in VOLETS_TUILES.items():
        f = _volet_filtre(v, role)
        if f:
            tuiles[cle] = f
    return {"rail": rail, "tuiles": tuiles}
