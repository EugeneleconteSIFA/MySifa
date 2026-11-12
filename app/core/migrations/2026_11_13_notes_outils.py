"""
Mes notes : historique des versions, modèles, favoris, notes récentes, commentaires.

- `note_versions` : photo d'une note (titre + contenu) prise avant une série
  de modifications, au plus une toutes les 10 minutes d'écriture, et avant
  toute restauration ou remplacement complet. `auteurs` : ids des personnes
  qui ont écrit depuis la photo précédente.
- `note_modeles` : modèles de note. `user_id` NULL = modèle proposé à tous
  (seedés ici, génériques) ; sinon modèle personnel enregistré depuis une note.
  `cle` identifie les modèles seedés (INSERT OR IGNORE).
- `note_favoris` : notes épinglées par chacun, avec leur ordre.
- `note_recents` : dernière ouverture d'une note par chacun.
- `note_commentaires` : commentaires en marge, rattachés à un bloc (`bloc_uid`)
  et au passage cité ; réponses par `parent_id` ; résolution.
"""

import json

NOM = "notes_outils"
DEPEND = ["notes_collaboration"]

_MODELES = (
    ("reunion", "Réunion", "Date, participants, points, décisions, actions", [
        {"uid": "m1", "type": "h2", "texte": "Réunion du {date}"},
        {"uid": "m2", "type": "p", "html": "<b>Participants :</b> "},
        {"uid": "m3", "type": "h3", "texte": "Ordre du jour"},
        {"uid": "m4", "type": "num", "texte": ""},
        {"uid": "m5", "type": "h3", "texte": "Décisions"},
        {"uid": "m6", "type": "puce", "texte": ""},
        {"uid": "m7", "type": "h3", "texte": "Actions"},
        {"uid": "m8", "type": "todo", "texte": "", "coche": False},
    ]),
    ("suivi_dossier", "Suivi de dossier", "Contexte, échanges datés, points ouverts", [
        {"uid": "m1", "type": "h2", "texte": "Dossier "},
        {"uid": "m2", "type": "encadre", "texte": "Contexte : "},
        {"uid": "m3", "type": "h3", "texte": "Échanges"},
        {"uid": "m4", "type": "puce", "html": "<b>{date}</b> — "},
        {"uid": "m5", "type": "h3", "texte": "Points ouverts"},
        {"uid": "m6", "type": "todo", "texte": "", "coche": False},
    ]),
    ("retour_atelier", "Retour d'atelier", "Constat, cause, action, suivi", [
        {"uid": "m1", "type": "h2", "texte": "Retour du {date}"},
        {"uid": "m2", "type": "tableau", "entete": True, "lignes": [
            ["Constat", "Cause", "Action", "Responsable"], ["", "", "", ""], ["", "", "", ""]]},
        {"uid": "m3", "type": "h3", "texte": "À suivre"},
        {"uid": "m4", "type": "todo", "texte": "", "coche": False},
    ]),
)


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS note_versions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          note_id INTEGER NOT NULL,
          titre TEXT,
          contenu TEXT,
          auteurs TEXT,
          raison TEXT,
          cree_le TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_note_versions_note ON note_versions(note_id, cree_le);

        CREATE TABLE IF NOT EXISTS note_modeles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          cle TEXT UNIQUE,
          user_id INTEGER,
          nom TEXT NOT NULL,
          description TEXT,
          contenu TEXT NOT NULL,
          cree_le TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS note_favoris (
          user_id INTEGER NOT NULL,
          note_id INTEGER NOT NULL,
          ordre INTEGER NOT NULL DEFAULT 0,
          cree_le TEXT NOT NULL,
          PRIMARY KEY (user_id, note_id)
        );

        CREATE TABLE IF NOT EXISTS note_recents (
          user_id INTEGER NOT NULL,
          note_id INTEGER NOT NULL,
          vu_le TEXT NOT NULL,
          PRIMARY KEY (user_id, note_id)
        );

        CREATE TABLE IF NOT EXISTS note_commentaires (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          note_id INTEGER NOT NULL,
          bloc_uid TEXT,
          citation TEXT,
          texte TEXT NOT NULL,
          user_id INTEGER NOT NULL,
          parent_id INTEGER,
          resolu INTEGER NOT NULL DEFAULT 0,
          resolu_par INTEGER,
          resolu_le TEXT,
          cree_le TEXT NOT NULL,
          modifie_le TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_note_commentaires_note ON note_commentaires(note_id);
        """
    )
    for cle, nom, desc, blocs in _MODELES:
        conn.execute(
            "INSERT OR IGNORE INTO note_modeles (cle, user_id, nom, description, contenu, cree_le) "
            "VALUES (?, NULL, ?, ?, ?, '2026-11-13T00:00:00')",
            (cle, nom, desc, json.dumps(blocs, ensure_ascii=False)),
        )
    conn.commit()
