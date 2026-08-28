# -*- coding: utf-8 -*-
"""
Lecture SQL encadrée, pour comprendre un bug en regardant les données.

Un bug ne prévient pas de la table qu'il faudra ouvrir : « ce métrage est faux »
demande l'OF, ses opérations, la bobine scannée, le calage, et la question
suivante dépend de la réponse à la première. Une liste de requêtes préétablies
ne couvre jamais le cas qui arrive — il faut du SELECT libre.

Filtrer du SQL par expression régulière serait une illusion : les contournements
sont innombrables. Ce module s'appuie donc sur l'autoriseur de SQLite, une
fonction que le moteur appelle AVANT chaque accès — chaque table, chaque
colonne, chaque fonction — et qui répond autoriser, refuser, ou renvoyer NULL.
Le refus ne dépend pas de la façon dont la requête est tournée : il est appliqué
au moment de lire la donnée.

Quatre protections, indépendantes les unes des autres :

  1. Base ouverte en `mode=ro` — aucune écriture possible, même si tout le reste
     tombait. (Même mécanisme que `_promote_history_from_db()` dans settings.py.)
  2. Autoriseur — liste blanche de tables, colonnes sensibles masquées, liste
     blanche de fonctions SQL, tout le reste refusé.
  3. Compteur d'opérations — une jointure cartésienne sur deux grosses tables
     bloquerait le processus applicatif ; la requête est avortée au-delà d'un
     plafond.
  4. Plafond de lignes — la réponse reste lisible et transportable.

La liste blanche est le seul réglage qui demande une décision humaine. Elle est
en liste BLANCHE et non en liste noire : une table créée dans six mois est
refusée par défaut, plutôt qu'exposée par oubli.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Any, Optional

# ─── Réglages ─────────────────────────────────────────────────────────────────

# Tables lisibles — 158 des 221 tables de la base du 28 août 2026.
#
# Construite par DIFFÉRENCE : chaque table de la base a été rangée dans un
# groupe métier ou dans un motif d'exclusion, et le classement a été vérifié
# exhaustif (aucune table oubliée). Une table créée après cette date n'est
# dans aucun groupe, donc refusée — c'est le comportement voulu.
#
# Les 63 exclusions, par motif :
#   secret   (4)  api_keys, sessions, cal_feed_tokens, push_subscriptions
#   identité (1)  users — à réintégrer avec masquage une fois ses colonnes vues
#   RH/paie  (8)  paie_*, rh_conges*, documents_rh*, notes_de_frais, user_habilitations
#   finance  (3)  compta_banques, compta_comptes, compta_acheteurs
#   privé   (23)  chat_*, messages, *_messages, postits, cal_* personnels
#   personnel(13) affectations, horaires, présences et progressions nominatives :
#                 planning_entries, planning_day_*, rh_planning_postes,
#                 taches_assignes, maintenance_event_operators, audit_auditeurs,
#                 user_*_progress*, formation_permissions, user_printer_defaults
#   sécurité (1)  audit_logs — journal de sécurité, ne sert pas à déboguer un métrage
#   bruit   (10)  index FTS internes, bat_pdfs, table de sauvegarde, caches de traduction
TABLES_LISIBLES: set[str] = {
    # ── Production, OF et fabrication (16 tables, 8 160 lignes)
    "fab_matieres_utilisees", "fiches_techniques", "machines", "of_imports",
    "operation_codes", "perf_releves", "production_data", "produit_documents",
    "produit_savoirs", "produit_savoirs_utile", "produit_series", "produits",
    "produits_finis", "rent_links", "rent_prod_links", "repiquage_carton_courant",

    # ── Stock matiere premiere (20 tables, 1 434 lignes)
    "matiere_base", "matiere_config", "matiere_laize_fournisseurs", "matiere_params",
    "matieres_premieres", "mp_fiche_mapping", "mp_grammages", "mp_laizes",
    "mp_matiere_declinaison", "mp_matiere_grammages", "mp_matiere_laizes",
    "mp_matiere_prix", "mp_mouvements", "mp_prix_historique", "mp_produit",
    "mp_produit_composant", "mp_stock", "mp_stock_laize", "mp_valorisation",
    "mp_valorisation_historique",

    # ── Stock, lots et emplacements (14 tables, 20 648 lignes)
    "documents_valeurs_historique", "emplacements_plan", "inventaires_matieres",
    "inventaires_sessions", "lots_stock", "mouvement_palettes", "mouvements_stock",
    "mouvements_stock_lots", "stock_compare_instantanes", "stock_compare_lignes",
    "stock_config", "stock_emplacements", "stock_reception_items", "stock_receptions",

    # ── Produits finis (5 tables, 571 lignes)
    "pf_mouvements", "pf_reception_items", "pf_receptions", "pf_valorisation",
    "pf_valorisation_historique",

    # ── Couts matieres (8 tables, 228 lignes)
    "mc_material", "mc_material_category", "mc_material_price_history", "mc_product",
    "mc_product_extra_material", "mc_setting", "mc_supplier", "mc_tarif_fournisseur",

    # ── Appels d'offres, devis, clients (17 tables, 1 633 lignes)
    "ao_carnet_clients", "ao_carnet_fournisseurs", "ao_demandes", "ao_evenements",
    "ao_fournisseurs", "ao_lignes", "ao_lignes_series", "ao_pieces_jointes", "ao_produits",
    "ao_reponses", "carnet_snapshots", "clients", "devis", "devis_dossiers", "dossiers",
    "fournisseur_contacts", "fournisseurs_fsc",

    # ── Expeditions et transport (14 tables, 57 435 lignes)
    "expe_delais", "expe_demandes_devis", "expe_depart_dossiers", "expe_departs",
    "expe_devis_evenements", "expe_devis_pieces_jointes", "expe_devis_reponses",
    "expe_palettes_contestations", "expe_palettes_mouvements", "expe_portal_transporteurs",
    "expe_tarifs", "expe_tarifs_frais", "expe_transporteurs",
    "expe_transporteurs_prospects",

    # ── Planning (9 tables, 1 246 lignes)
    "planning_config",
    "planning_holidays", "planning_of_links",
    "rh_machine_config",

    # ── Maintenance (11 tables, 574 lignes)
    "maintenance_alert_acks", "maintenance_alert_settings", "maintenance_alerts",
    "maintenance_codes", "maintenance_docs",
    "maintenance_event_ops", "maintenance_events", "maintenance_template_ops",
    "maintenance_templates", "maintenance_usure_pieces",

    # ── Qualite, audits, non-conformites (22 tables, 471 lignes)
    "audit_certifications_demandees", "audit_dossiers", "audit_fichiers",
    "audit_folders", "audit_fournisseurs", "audit_matrice_overrides", "nc_dossiers",
    "nc_fichiers", "nc_service_acknowledgments", "qualite_cert_expiration_annonces",
    "qualite_fournisseur_certificat_fiches", "qualite_fournisseur_certificats",
    "qualite_ged_file_versions", "qualite_ged_files", "qualite_ged_folders",
    "qualite_ref_audit_liens", "qualite_ref_fiches", "qualite_ref_fichiers",
    "qualite_ref_questions", "qualite_sifa_doc_templates", "qualite_sifa_doc_versions",

    # ── Impression et etiquettes (6 tables, 133 lignes)
    "bat_entries", "imprimante_templates", "imprimantes", "print_agents", "print_jobs",

    # ── ERP, RVGI et imports (5 tables, 4 326 lignes)
    "imports", "reconciliation_lines", "reconciliation_snapshots", "rvgi_rattachements",
    "rvgi_tiers_synchros",

    # ── Taches (6 tables, 193 lignes)
    "taches", "taches_activite", "taches_checklist",
    "taches_commentaires", "taches_fichiers",

    # ── Formation (9 tables, 48 lignes)
    "formation_modules", "formation_quiz", "formation_videos",
    "formations", "role_parcours_defaut",

    # ── Roles, acces et tableaux de bord (4 tables, 101 lignes)
    "dashboards", "role_access_defaults", "user_access_overrides", "user_dashboards",

    # ── Deploiement et schema (5 tables, 524 lignes)
    "promotion_history", "schema_migrations", "schema_migrations_fichiers",
    "update_acknowledgements", "update_announcements",
}

# Colonnes rendues NULL même dans une table par ailleurs lisible.
# Le masquage résiste à substr(), length(), group_concat() et aux filtres LIKE :
# la colonne n'est jamais lue, donc il n'y a rien à reconstituer.
COLONNES_MASQUEES: set[tuple[str, str]] = set()

# Les fonctions SQL passent AUSSI par l'autoriseur. Sans cette liste, même
# count() et LIKE sont refusés — piège vérifié.
FONCTIONS_AUTORISEES: set[str] = {
    "count", "sum", "avg", "min", "max", "total",
    "abs", "round", "length", "substr", "instr", "replace", "trim",
    "ltrim", "rtrim", "lower", "upper", "printf", "format",
    "like", "glob", "coalesce", "ifnull", "nullif", "iif", "typeof",
    "date", "time", "datetime", "julianday", "strftime", "unixepoch",
    "group_concat", "json_extract", "row_number", "rank", "dense_rank",
}

LIGNES_MAX = 200          # au-delà, la réponse est tronquée et le dit
OPERATIONS_MAX = 2_000_000  # garde-fou contre une requête qui part en vrille
DELAI_OUVERTURE = 5.0      # secondes d'attente si la base est verrouillée


class DiagnosticRefus(Exception):
    """Requête refusée par l'encadrement. Le message est montrable tel quel."""


class DiagnosticTropLong(Exception):
    """Requête avortée : elle dépassait le plafond d'opérations."""


# ─── Autoriseur ───────────────────────────────────────────────────────────────

def _construire_autoriseur(refus: list[str]):
    """Fabrique la fonction que SQLite appelle avant chaque accès.

    `refus` collecte les motifs pour le journal : quand une requête est
    bloquée, on veut pouvoir dire QUELLE table a été refusée, pas seulement
    que « ça n'a pas marché ».
    """

    def autoriseur(action, arg1, arg2, base, declencheur):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK

        if action == sqlite3.SQLITE_FUNCTION:
            nom = (arg2 or "").lower()
            if nom in FONCTIONS_AUTORISEES:
                return sqlite3.SQLITE_OK
            refus.append(f"fonction {nom}()")
            return sqlite3.SQLITE_DENY

        if action == sqlite3.SQLITE_READ:
            table, colonne = arg1, arg2
            if (table, colonne) in COLONNES_MASQUEES:
                # IGNORE et non DENY : la colonne revient NULL au lieu de faire
                # échouer la requête. On peut donc lire la table utilisateurs
                # pour un diagnostic de rôle sans jamais approcher le hash.
                return sqlite3.SQLITE_IGNORE
            if table not in TABLES_LISIBLES:
                motif = f"table {table}"
                if motif not in refus:
                    refus.append(motif)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        # Tout le reste — écriture, DDL, ATTACH, PRAGMA, transaction — refusé.
        return sqlite3.SQLITE_DENY

    return autoriseur


# ─── Exécution ────────────────────────────────────────────────────────────────

def executer(
    chemin_db: str,
    sql: str,
    parametres: Optional[tuple] = None,
    lignes_max: int = LIGNES_MAX,
) -> dict[str, Any]:
    """Exécute une lecture encadrée. Ne lève jamais rien d'inattendu.

    Renvoie : colonnes, lignes, tronque, nb_lignes, duree_ms, sql.
    Lève DiagnosticRefus si l'encadrement a bloqué, DiagnosticTropLong si la
    requête a dépassé le plafond d'opérations.
    """
    if not TABLES_LISIBLES:
        raise DiagnosticRefus(
            "Aucune table n'est déclarée lisible : TABLES_LISIBLES est vide. "
            "Tant qu'elle l'est, ce module ne rend rien — c'est voulu."
        )

    refus: list[str] = []
    depart = time.monotonic()

    # mode=ro : le fichier est ouvert en lecture seule par le système. Aucune
    # écriture n'est possible même si l'autoriseur était contourné.
    con = sqlite3.connect(
        f"file:{chemin_db}?mode=ro", uri=True, timeout=DELAI_OUVERTURE
    )
    try:
        con.row_factory = sqlite3.Row

        compteur = {"n": 0}

        def progression():
            compteur["n"] += 1
            return 1 if compteur["n"] > (OPERATIONS_MAX // 1000) else 0

        con.set_progress_handler(progression, 1000)
        con.set_authorizer(_construire_autoriseur(refus))

        try:
            curseur = con.execute(sql, parametres or ())
        except (sqlite3.Warning, sqlite3.ProgrammingError) as exc:
            # sqlite3 refuse plusieurs instructions dans un seul execute().
            raise DiagnosticRefus(f"Une seule requête à la fois : {exc}") from exc
        except sqlite3.DatabaseError as exc:
            # Un refus de l'autoriseur remonte en DatabaseError (« access to X
            # is prohibited »), pas en OperationalError : attraper la classe
            # parente couvre les deux, l'erreur de syntaxe comprise.
            texte = str(exc)
            if "prohibited" in texte or "not authorized" in texte:
                detail = ", ".join(refus) if refus else texte
                raise DiagnosticRefus(f"Accès refusé : {detail}") from exc
            if "interrupted" in texte.lower():
                raise DiagnosticTropLong(
                    "Requête avortée : elle dépassait le plafond d'opérations. "
                    "Ajoute un WHERE ou une LIMIT."
                ) from exc
            raise DiagnosticRefus(f"SQL invalide : {texte}") from exc

        colonnes = [d[0] for d in (curseur.description or [])]
        brut = curseur.fetchmany(lignes_max + 1)
        tronque = len(brut) > lignes_max
        lignes = [list(r) for r in brut[:lignes_max]]

        return {
            "sql": sql,
            "colonnes": colonnes,
            "lignes": lignes,
            "nb_lignes": len(lignes),
            "tronque": tronque,
            "duree_ms": round((time.monotonic() - depart) * 1000, 1),
        }
    finally:
        try:
            con.set_authorizer(None)
            con.set_progress_handler(None, 0)
        except Exception:
            pass
        con.close()


def tables_lisibles_du_schema(chemin_db: str) -> list[str]:
    """Liste les tables du schéma, pour aider à composer la liste blanche.

    Volontairement hors de l'encadrement : sert à préparer TABLES_LISIBLES, pas
    à répondre à une requête de diagnostic. À n'appeler que depuis un script
    d'administration, jamais depuis l'endpoint.
    """
    con = sqlite3.connect(f"file:{chemin_db}?mode=ro", uri=True, timeout=DELAI_OUVERTURE)
    try:
        return [
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
    finally:
        con.close()
