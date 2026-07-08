"""MySifa — Système d'habilitations MyLearning

Ce module centralise les codes de permission utilisés par le système
d'habilitation "bloquant progressif" (voir CLAUDE.md — module MyLearning).

Convention : `<app>.<action>` en snake_case.

Modèle de fonctionnement (mis en place progressivement) :
  1. Une formation valide 1..N `permission_code` (table formation_permissions).
  2. Quand un utilisateur termine une formation (visionnage + quiz), les
     permissions correspondantes sont insérées dans user_habilitations.
  3. Les endpoints sensibles utilisent le décorateur `require_habilitation(code)`
     pour bloquer les non habilités (message + lien vers la formation).
  4. Le frontend utilise `hasPerm(code)` pour griser les boutons concernés.

Étape 1 (actuelle) : le décorateur est présent mais NE BLOQUE PAS encore
(mode passthrough). Il logge simplement les tentatives pour permettre
d'observer le trafic avant l'activation réelle.

Étape 2 : activation progressive, permission par permission, avec écran
"Formation requise" côté UI et 403 côté API.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

logger = logging.getLogger("mysifa.permissions")


# ─── Tranche 1 (MVP — actif en priorité une fois les formations créées) ──
# Ces 10 codes couvrent les gestes vraiment critiques (impact opérationnel
# fort en cas d'erreur). C'est le périmètre validé par Eugène pour la
# première vague d'habilitation.
PROD_SAISIE_OPERATEUR    = "prod.saisie_operateur"
PROD_SUPPRESSION_SAISIE  = "prod.suppression_saisie"
PLANNING_CREATION_DOSSIER    = "planning.creation_dossier"
PLANNING_SUPPRESSION_DOSSIER = "planning.suppression_dossier"
PLANNING_CHANGEMENT_STATUT   = "planning.changement_statut"
STOCK_MOUVEMENT              = "stock.mouvement"
STOCK_INVENTAIRE_VALIDATION  = "stock.inventaire_validation"
EXPE_CREATION_DEPART         = "expe.creation_depart"
EXPE_VALIDATION_DEPART       = "expe.validation_depart"
EXPE_SUPPRESSION_DEPART      = "expe.suppression_depart"

TRANCHE_1: tuple[str, ...] = (
    PROD_SAISIE_OPERATEUR,
    PROD_SUPPRESSION_SAISIE,
    PLANNING_CREATION_DOSSIER,
    PLANNING_SUPPRESSION_DOSSIER,
    PLANNING_CHANGEMENT_STATUT,
    STOCK_MOUVEMENT,
    STOCK_INVENTAIRE_VALIDATION,
    EXPE_CREATION_DEPART,
    EXPE_VALIDATION_DEPART,
    EXPE_SUPPRESSION_DEPART,
)


# ─── Tranche 2 — gestes importants mais moins fréquents ──────────────────
PLANNING_MODIFICATION_DOSSIER = "planning.modification_dossier"
PLANNING_REORDONNER           = "planning.reordonner"
PLANNING_RESET_SAISIE         = "planning.reset_saisie"
PLANNING_SPLIT_DOSSIER        = "planning.split_dossier"
STOCK_SORTIE_FIFO             = "stock.sortie_fifo"
STOCK_TRANSFERT_EMPLACEMENT   = "stock.transfert_emplacement"
STOCK_GESTION_PRODUIT         = "stock.gestion_produit"
STOCK_GESTION_MATIERE         = "stock.gestion_matiere"
STOCK_RECEPTION_MARCHANDISE   = "stock.reception_marchandise"
EXPE_MODIFICATION_DEPART      = "expe.modification_depart"
EXPE_INVALIDATION_DEPART      = "expe.invalidation_depart"
EXPE_GESTION_TRANSPORTEUR     = "expe.gestion_transporteur"

TRANCHE_2: tuple[str, ...] = (
    PLANNING_MODIFICATION_DOSSIER,
    PLANNING_REORDONNER,
    PLANNING_RESET_SAISIE,
    PLANNING_SPLIT_DOSSIER,
    STOCK_SORTIE_FIFO,
    STOCK_TRANSFERT_EMPLACEMENT,
    STOCK_GESTION_PRODUIT,
    STOCK_GESTION_MATIERE,
    STOCK_RECEPTION_MARCHANDISE,
    EXPE_MODIFICATION_DEPART,
    EXPE_INVALIDATION_DEPART,
    EXPE_GESTION_TRANSPORTEUR,
)


# ─── Tranche 3 — admin / compta / paie / RH / qualité ────────────────────
COMPTA_GESTION_ACHETEUR = "compta.gestion_acheteur"
COMPTA_GESTION_BANQUE   = "compta.gestion_banque"
COMPTA_GESTION_COMPTE   = "compta.gestion_compte"
PAIE_VARIABLES_MENSUELLES = "paie.variables_mensuelles"
PAIE_FIX_EMPLOYE          = "paie.fix_employe"
RH_PLANNING_MODIFICATION  = "rh.planning_modification"
RH_CONGES_MODIFICATION    = "rh.conges_modification"
RH_SOLDES_MAJ             = "rh.soldes_maj"
SETTINGS_GESTION_UTILISATEURS = "settings.gestion_utilisateurs"
QUALITE_NC_VALIDATION         = "qualite.nc_validation"

TRANCHE_3: tuple[str, ...] = (
    COMPTA_GESTION_ACHETEUR,
    COMPTA_GESTION_BANQUE,
    COMPTA_GESTION_COMPTE,
    PAIE_VARIABLES_MENSUELLES,
    PAIE_FIX_EMPLOYE,
    RH_PLANNING_MODIFICATION,
    RH_CONGES_MODIFICATION,
    RH_SOLDES_MAJ,
    SETTINGS_GESTION_UTILISATEURS,
    QUALITE_NC_VALIDATION,
)


# ─── Catalogue complet (toutes tranches confondues) ──────────────────────
ALL_PERMISSIONS: tuple[str, ...] = TRANCHE_1 + TRANCHE_2 + TRANCHE_3


# ─── Descriptions humaines (utilisées pour l'admin et les messages 403) ──
PERMISSION_LABELS: dict[str, str] = {
    PROD_SAISIE_OPERATEUR:    "Saisir une opération de production",
    PROD_SUPPRESSION_SAISIE:  "Supprimer une saisie de production",
    PLANNING_CREATION_DOSSIER:    "Créer un dossier au planning atelier",
    PLANNING_SUPPRESSION_DOSSIER: "Supprimer un dossier du planning",
    PLANNING_CHANGEMENT_STATUT:   "Changer le statut d'un dossier (attente / en_cours / terminé)",
    PLANNING_MODIFICATION_DOSSIER: "Modifier un dossier au planning",
    PLANNING_REORDONNER:          "Réordonner les dossiers au planning",
    PLANNING_RESET_SAISIE:        "Réinitialiser les saisies d'un dossier",
    PLANNING_SPLIT_DOSSIER:       "Fractionner un dossier en deux",
    STOCK_MOUVEMENT:              "Créer un mouvement de stock (entrée / sortie / transfert)",
    STOCK_INVENTAIRE_VALIDATION:  "Valider l'inventaire physique",
    STOCK_SORTIE_FIFO:            "Sortir un lot par FIFO",
    STOCK_TRANSFERT_EMPLACEMENT:  "Déplacer un lot entre emplacements",
    STOCK_GESTION_PRODUIT:        "Créer / modifier / supprimer un produit fini",
    STOCK_GESTION_MATIERE:        "Créer / modifier / supprimer une matière première",
    STOCK_RECEPTION_MARCHANDISE:  "Enregistrer une réception de marchandise",
    EXPE_CREATION_DEPART:    "Créer un départ expédition",
    EXPE_MODIFICATION_DEPART: "Modifier un départ expédition",
    EXPE_VALIDATION_DEPART:  "Valider un départ expédition",
    EXPE_INVALIDATION_DEPART: "Remettre un départ en suivi",
    EXPE_SUPPRESSION_DEPART: "Supprimer un départ expédition",
    EXPE_GESTION_TRANSPORTEUR: "Gérer les transporteurs",
    COMPTA_GESTION_ACHETEUR: "Gérer les fiches acheteurs",
    COMPTA_GESTION_BANQUE:   "Gérer les comptes bancaires",
    COMPTA_GESTION_COMPTE:   "Gérer les comptes analytiques",
    PAIE_VARIABLES_MENSUELLES: "Saisir les variables de paie mensuelles",
    PAIE_FIX_EMPLOYE:          "Modifier le salaire fixe d'un employé",
    RH_PLANNING_MODIFICATION:  "Modifier le planning du personnel",
    RH_CONGES_MODIFICATION:    "Gérer les congés (création / modification)",
    RH_SOLDES_MAJ:             "Mettre à jour les soldes de congés",
    SETTINGS_GESTION_UTILISATEURS: "Créer / modifier / désactiver des utilisateurs",
    QUALITE_NC_VALIDATION:         "Valider une non-conformité qualité",
}


# ─── Helpers ──────────────────────────────────────────────────────────────
def is_known_permission(code: str) -> bool:
    """Vrai si `code` fait partie du catalogue déclaré."""
    return code in ALL_PERMISSIONS


def user_has_permission(user_id: int, code: str) -> bool:
    """Retourne True si l'utilisateur a validé une formation qui débloque
    la permission `code`. Le super admin est toujours habilité.

    Étape 1 : les tables sont vides tant qu'aucune formation n'est publiée,
    donc cette fonction renverra False pour tout non-superadmin. C'est
    intentionnel — le décorateur `require_habilitation` ne bloque pas
    encore, il logge seulement les tentatives.
    """
    # Import différé pour éviter les cycles à l'import de config.
    from app.core.database import get_db

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT role FROM users WHERE id=? LIMIT 1",
                (user_id,),
            ).fetchone()
            if row is None:
                return False
            # Super admin : bypass systématique.
            if row["role"] == "superadmin":
                return True
            hit = conn.execute(
                "SELECT 1 FROM user_habilitations "
                "WHERE user_id=? AND permission_code=? LIMIT 1",
                (user_id, code),
            ).fetchone()
            return hit is not None
    except Exception as e:
        # En cas de souci DB, on log et on laisse passer (fail-open à
        # l'étape 1 pour ne rien casser).
        logger.warning("user_has_permission(%s, %s) — erreur DB : %s", user_id, code, e)
        return True


def require_habilitation(code: str, *, enforce: bool = False) -> Callable:
    """Décorateur FastAPI qui vérifie qu'un utilisateur a la permission
    `code`. À l'étape 1, `enforce=False` par défaut : le décorateur ne
    bloque rien mais log toute tentative sans habilitation. Activer
    `enforce=True` permission par permission une fois les formations
    publiées.

    Usage attendu (étape 2+) :
        @router.post("/api/expe/departs")
        @require_habilitation(EXPE_CREATION_DEPART, enforce=True)
        def creer_depart(request: Request, ...):
            ...
    """
    if not is_known_permission(code):
        # On lève au démarrage plutôt qu'en runtime : erreur de dev.
        raise ValueError(f"Permission inconnue : {code!r}")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Le user est injecté par FastAPI via Depends dans la plupart
            # des routers MySifa. On cherche `request` dans les kwargs
            # ou dans les args pour extraire l'utilisateur.
            request = kwargs.get("request")
            if request is None:
                for a in args:
                    if hasattr(a, "cookies") and hasattr(a, "url"):
                        request = a
                        break
            user = None
            if request is not None:
                try:
                    from app.services.auth_service import get_current_user

                    user = get_current_user(request)
                except Exception:
                    user = None
            if user and not user_has_permission(user.get("id"), code):
                logger.info(
                    "require_habilitation MISS user=%s code=%s enforce=%s path=%s",
                    user.get("id"),
                    code,
                    enforce,
                    getattr(request, "url", "?"),
                )
                if enforce:
                    from fastapi import HTTPException

                    label = PERMISSION_LABELS.get(code, code)
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "code": "formation_requise",
                            "permission": code,
                            "label": label,
                            "message": (
                                f"Cette action requiert la formation « {label} ». "
                                "Rendez-vous dans MyLearning pour la valider."
                            ),
                        },
                    )
            return await func(*args, **kwargs) if _is_coroutine(func) else func(*args, **kwargs)

        return wrapper

    return decorator


def _is_coroutine(func: Callable) -> bool:
    import asyncio

    return asyncio.iscoroutinefunction(func)
