"""
Mes notes : mise en forme riche, images, partage et rédaction à plusieurs.

- Chaque bloc reçoit un identifiant stable `uid` (dans le JSON de
  `postits.contenu`) : deux personnes qui écrivent en même temps échangent des
  opérations sur des blocs nommés, jamais des positions qui bougent.
- `postits.revision` : compteur de la note, +1 par opération appliquée.
- `note_ops` : journal des opérations, lu par le flux temps réel des autres
  éditeurs (les plus anciennes sont élaguées, voir app/services/notes.py).
- `note_partages` : une note (et ses sous-pages) partagée avec un utilisateur,
  en lecture ou en écriture.
- `note_presences` : qui a la note ouverte, et dans quel bloc.
- `note_images` : images insérées dans une note (fichier sous
  UPLOAD_DIR/notes/AAAA/MM/).
"""

import json
import uuid

NOM = "notes_collaboration"
DEPEND = ["notes_espace"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()}
    if not cols:
        return
    if "revision" not in cols:
        conn.execute("ALTER TABLE postits ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS note_ops (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          note_id INTEGER NOT NULL,
          revision INTEGER NOT NULL,
          user_id INTEGER,
          client TEXT,
          op TEXT NOT NULL,
          cree_le TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_note_ops_note_rev ON note_ops(note_id, revision);

        CREATE TABLE IF NOT EXISTS note_partages (
          note_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          droit TEXT NOT NULL DEFAULT 'ecrire',
          partage_par INTEGER,
          cree_le TEXT NOT NULL,
          PRIMARY KEY (note_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_note_partages_user ON note_partages(user_id);

        CREATE TABLE IF NOT EXISTS note_presences (
          note_id INTEGER NOT NULL,
          client TEXT NOT NULL,
          user_id INTEGER NOT NULL,
          bloc TEXT,
          vu_le REAL NOT NULL,
          PRIMARY KEY (note_id, client)
        );

        CREATE TABLE IF NOT EXISTS note_images (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          note_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          chemin TEXT NOT NULL,
          nom TEXT,
          mime TEXT NOT NULL,
          taille INTEGER NOT NULL DEFAULT 0,
          cree_le TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_note_images_note ON note_images(note_id);
        """
    )
    # Identifiant stable sur chaque bloc existant.
    n = 0
    for pid, contenu in conn.execute("SELECT id, contenu FROM postits").fetchall():
        try:
            blocs = json.loads(contenu) if contenu else []
        except (TypeError, ValueError):
            continue
        if not isinstance(blocs, list):
            continue
        change = False
        for b in blocs:
            if isinstance(b, dict) and not b.get("uid"):
                b["uid"] = uuid.uuid4().hex[:12]
                change = True
        if change:
            conn.execute("UPDATE postits SET contenu=? WHERE id=?", (json.dumps(blocs, ensure_ascii=False), pid))
            n += 1
    conn.commit()
    if n:
        print(f"[MySifa] migration notes_collaboration : {n} note(s) reçoivent des identifiants de blocs.")
