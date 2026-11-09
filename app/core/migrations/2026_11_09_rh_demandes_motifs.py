"""
Planning RH : motifs d'absence et demandes des employés.

`rh_motifs_absence` remplace la liste figée CP / maladie / autre du code. Un
motif porte son libellé, le solde sur lequel il s'impute (`decompte` : cp, rtt
ou aucun), s'il peut être demandé par un employé (`demandable` — la maladie se
déclare, elle ne se demande pas) et son ordre. `rh_conges.type_conge` garde le
`code` du motif : les congés existants (CP, maladie, autre, RTT) retrouvent
leur motif sans reprise.

`rh_demandes` reçoit les demandes déposées par les employés eux-mêmes :
absence (avec un motif), aménagement d'horaire (heures souhaitées) ou autre.
Le responsable du planning RH la valide ou la refuse ; une absence validée
crée le congé correspondant (`conge_id`).

Accès : tout employé doit pouvoir ouvrir Planning RH pour déposer sa demande.
Les rôles qui n'y avaient pas accès (niveau absent ou `none`) passent en
lecture ; la vue planning et la gestion des congés restent filtrées par rôle
dans l'API. Les exceptions par personne ne sont pas touchées.
"""

NOM = "rh_demandes_motifs"
DEPEND = ["notifications_services"]

# (code, libellé, décompte, demandable, ordre) — valeurs SIFA de départ,
# éditables ensuite dans Planning RH › Demandes › Motifs.
_MOTIFS = (
    ("CP", "Congés payés", "cp", 1, 1),
    ("RTT", "RTT", "rtt", 1, 2),
    ("formation", "Formation", "aucun", 1, 3),
    ("evenement_familial", "Événement familial", "aucun", 1, 4),
    ("sans_solde", "Congé sans solde", "aucun", 1, 5),
    ("maladie", "Maladie", "aucun", 0, 6),
    ("autre", "Autre", "aucun", 1, 9),
)

_ROLES = (
    "superadmin", "direction", "administration", "administration_ventes",
    "administration_technique", "fabrication", "logistique", "comptabilite",
    "expedition", "commercial",
)


def _table(conn, nom):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)).fetchone()


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_motifs_absence (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               code        TEXT NOT NULL UNIQUE,
               libelle     TEXT NOT NULL,
               decompte    TEXT NOT NULL DEFAULT 'aucun',
               demandable  INTEGER NOT NULL DEFAULT 1,
               actif       INTEGER NOT NULL DEFAULT 1,
               ordre       INTEGER NOT NULL DEFAULT 0,
               cree_le     TEXT NOT NULL DEFAULT (datetime('now')),
               modifie_le  TEXT,
               modifie_par TEXT
           )"""
    )
    for code, libelle, decompte, demandable, ordre in _MOTIFS:
        conn.execute(
            """INSERT OR IGNORE INTO rh_motifs_absence (code, libelle, decompte, demandable, ordre)
               VALUES (?, ?, ?, ?, ?)""",
            (code, libelle, decompte, demandable, ordre),
        )

    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_demandes (
               id             INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id        INTEGER NOT NULL REFERENCES users(id),
               nature         TEXT NOT NULL,
               motif_code     TEXT,
               date_debut     TEXT NOT NULL,
               date_fin       TEXT NOT NULL,
               nb_jours       REAL,
               heure_debut    TEXT,
               heure_fin      TEXT,
               commentaire    TEXT,
               statut         TEXT NOT NULL DEFAULT 'en_attente',
               decision_par   TEXT,
               decision_le    TEXT,
               decision_note  TEXT,
               conge_id       INTEGER REFERENCES rh_conges(id) ON DELETE SET NULL,
               cree_le        TEXT NOT NULL,
               cree_par       TEXT
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_demandes_user ON rh_demandes(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_demandes_statut ON rh_demandes(statut)")

    n_roles = 0
    if _table(conn, "role_access_defaults"):
        for role in _ROLES:
            n_roles += conn.execute(
                """INSERT OR IGNORE INTO role_access_defaults (role, app_id, module_id, level, updated_at, updated_by)
                   VALUES (?, 'planning_rh', '_app', 'read', datetime('now'), 'migration rh_demandes_motifs')""",
                (role,),
            ).rowcount
            n_roles += conn.execute(
                """UPDATE role_access_defaults
                      SET level = 'read', updated_at = datetime('now'), updated_by = 'migration rh_demandes_motifs'
                    WHERE role = ? AND app_id = 'planning_rh' AND module_id = '_app' AND level = 'none'""",
                (role,),
            ).rowcount
    # Pastille « Demandes RH à valider » active d'emblée pour les responsables
    # (réglable ensuite dans Paramètres › Notifications).
    if _table(conn, "notif_regles"):
        conn.execute(
            """INSERT OR IGNORE INTO notif_regles (code, actif, roles, push, updated_at, updated_by)
               VALUES ('rh.demandes_a_valider', 1, '["comptabilite", "direction", "superadmin"]', 0,
                       datetime('now'), 'migration rh_demandes_motifs')"""
        )
    conn.commit()
    print(f"[MySifa] migration {NOM} : motifs d'absence et demandes RH créés, "
          f"{n_roles} rôle(s) ouvert(s) à Planning RH.")
