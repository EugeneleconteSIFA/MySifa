"""
Planning RH : seuils d'absences simultanées, publication des semaines et
échanges de créneau entre collègues.

- `rh_absences_seuils` : nombre maximal d'absents en même temps par service
  (rôle). Aucune valeur SIFA n'est seedée : sans ligne, pas de limite. Se
  règle dans Planning RH › Demandes › Réglages.
- `rh_planning_publications` : une semaine publiée (date, auteur). Sans ligne,
  la semaine est provisoire.
- `rh_planning_publie` : ce que chaque personne avait reçu à la dernière
  publication (empreinte de ses affectations de la semaine). Une republication
  ne prévient que les personnes dont l'empreinte a changé.
- `rh_notes_equipe` : notes du responsable à l'attention d'une équipe
  (« beaucoup de préparation en logistique cette semaine »), sur une plage de
  semaines, visant tout le monde, un service (rôle) ou une machine.
- `rh_demandes` gagne les colonnes d'un échange : l'affectation du demandeur,
  celle du collègue, le collègue et sa réponse.
"""

NOM = "rh_planning_outils"
DEPEND = ["rh_demandes_motifs"]


def _cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_absences_seuils (
               service      TEXT PRIMARY KEY,
               max_absents  INTEGER NOT NULL,
               modifie_le   TEXT,
               modifie_par  TEXT
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_planning_publications (
               semaine      TEXT PRIMARY KEY,
               publie_le    TEXT NOT NULL,
               publie_par   TEXT,
               version      INTEGER NOT NULL DEFAULT 1
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_planning_publie (
               semaine      TEXT NOT NULL,
               user_id      INTEGER NOT NULL REFERENCES users(id),
               empreinte    TEXT NOT NULL,
               PRIMARY KEY (semaine, user_id)
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_notes_equipe (
               id              INTEGER PRIMARY KEY AUTOINCREMENT,
               semaine_debut   TEXT NOT NULL,
               semaine_fin     TEXT NOT NULL,
               cible_type      TEXT NOT NULL DEFAULT 'tous',
               cible_valeur    TEXT,
               texte           TEXT NOT NULL,
               importance      TEXT NOT NULL DEFAULT 'info',
               cree_le         TEXT NOT NULL,
               cree_par        TEXT,
               cree_par_nom    TEXT
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_notes_equipe_sem ON rh_notes_equipe(semaine_debut, semaine_fin)")
    cols = _cols(conn, "rh_demandes")
    for nom, decl in (
        ("affectation_id", "INTEGER"),
        ("affectation_cible_id", "INTEGER"),
        ("cible_user_id", "INTEGER REFERENCES users(id)"),
        ("cible_reponse", "TEXT"),
        ("cible_reponse_le", "TEXT"),
        ("semaine", "TEXT"),
    ):
        if nom not in cols:
            conn.execute(f"ALTER TABLE rh_demandes ADD COLUMN {nom} {decl}")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_demandes_cible ON rh_demandes(cible_user_id)")
    conn.commit()
