"""
Périmètre de service pour le gestionnaire de tâches (/taches).

L'application était réservée au super administrateur. Elle s'ouvre aux services :
chacun gère ses propres tâches et celles de son service.

Deux choses sont posées ici.

**Une colonne `service` sur la tâche.** C'est elle qui dit à quel service la
tâche appartient — pas l'assignation, qui bouge, et pas le créateur, qui peut
déposer une demande pour l'atelier depuis l'administration. Un service EST un
rôle (voir `TACHES_SERVICES_CODES` dans config.py) : la question « qui doit voir
cette tâche » a la même réponse que « qui travaille dessus ». Reprise des
tâches existantes : le service du créateur, donc `superadmin` pour l'historique
de dev — invisible aux autres services, ce qui est le comportement voulu.

**Le seed de la matrice d'accès.** L'app `taches` entre dans
`role_access_defaults` avec `none` partout sauf direction et superadmin, qui
gardent l'accès total qu'ils avaient déjà. Autrement dit : après cette
migration, RIEN ne change pour personne. L'ouverture d'un service se fait
ensuite dans Paramètres → Accès, sans redéploiement.

`INSERT OR IGNORE` : un niveau déjà réglé à la main n'est jamais réécrit, la
migration peut donc être rejouée sans annuler une ouverture déjà décidée.
"""

from datetime import datetime

NOM = "taches_service_perimetre"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(taches)").fetchall()}
    if not cols:
        return  # table absente (harnais de test) : rien à faire

    # ── 1. Colonne de service ──────────────────────────────────────────────
    if "service" not in cols:
        conn.execute("ALTER TABLE taches ADD COLUMN service TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_taches_service ON taches(service) "
        "WHERE deleted_at IS NULL"
    )

    repris = conn.execute(
        "UPDATE taches SET service = ("
        "  SELECT u.role FROM users u WHERE u.id = taches.createur_user_id"
        ") WHERE service IS NULL AND createur_user_id IS NOT NULL"
    ).rowcount

    # ── 2. Seed de la matrice d'accès ──────────────────────────────────────
    # Table absente = base antérieure à la migration 186 : le repli
    # `default_app_access_for_role` prend le relais, rien à seeder.
    a_matrice = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_access_defaults'"
    ).fetchone()
    seedes = 0
    if a_matrice:
        from config import (
            ASSIGNABLE_ROLES,
            ROLE_DIRECTION,
            ROLE_SUPERADMIN,
        )
        maintenant = datetime.now().isoformat(timespec="seconds")
        acces_total = {ROLE_DIRECTION, ROLE_SUPERADMIN}
        for role in sorted(ASSIGNABLE_ROLES | acces_total):
            cur = conn.execute(
                "INSERT OR IGNORE INTO role_access_defaults "
                "(role, app_id, module_id, level, updated_at, updated_by) "
                "VALUES (?,'taches','_app',?,?,?)",
                (role, "admin" if role in acces_total else "none",
                 maintenant, "migration " + NOM),
            )
            seedes += cur.rowcount

    conn.commit()
    print(f"[MySifa] migration {NOM} : {repris} tache(s) rattachee(s) a un service, "
          f"{seedes} niveau(x) d'acces seede(s).")
