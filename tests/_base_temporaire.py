"""
Base SQLite jetable pour un test. À importer AVANT `database`, `config` ou
tout module `app.*` :

    import _base_temporaire  # noqa: F401  — base jetable, avant tout le reste
    import database

POURQUOI. Importer `database` lance `init_db()`, donc toutes les migrations,
sur la base que désigne `config.DB_PATH` — par défaut `data/production.db`
du dossier courant. Un test qui ne fixe pas son chemin migre et écrit dans la
base locale du poste. Et dans un clone ou un worktree neuf, où cette base
n'existe pas encore, `scripts/ci_local.sh` lance huit tests en parallèle qui
la créent et la migrent en même temps : deux `ALTER TABLE` identiques se
croisent (« duplicate column name ») et la CI tombe sans rien de cassé dans
le code (constaté le 15/10/2026).

`config` lit `DB_PATH` dans l'environnement au moment de son premier import :
il suffit donc de le poser ici, avant lui. Le fichier est supprimé en fin de
test.
"""
import atexit
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

if "config" in sys.modules:
    # Trop tard : le chemin de la base est déjà lu. Mieux vaut échouer ici que
    # laisser le test écrire dans la base du poste.
    raise RuntimeError("_base_temporaire doit être importé avant config / database / app.*")

_fd, DB = tempfile.mkstemp(prefix="mysifa_test_", suffix=".db")
os.close(_fd)
os.environ["DB_PATH"] = DB


@atexit.register
def _nettoyer():
    for suffixe in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(DB + suffixe)
        except OSError:
            pass
