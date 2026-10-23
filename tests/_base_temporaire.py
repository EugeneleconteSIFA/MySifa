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


# ─── Base modèle déjà migrée ─────────────────────────────────────────
# Migrer une base vide coûte une douzaine de secondes de CPU SQLite (≈7 600
# requêtes, surtout des ALTER TABLE qui reparsent tout le schéma) — c'était
# 12 s sur les 15 de test_fournisseurs_merge.py (23/10/2026). On migre donc une
# seule fois une base modèle, rangée sous l'empreinte du code qui la produit,
# et chaque test en reçoit une copie. `import database` y rejoue ensuite les
# migrations : toutes déjà passées, il ne fait que vérifier.
#
# L'empreinte couvre database.py, les fichiers de migration, config.py et
# operations.json : changer une migration invalide le modèle tout seul.
# MYSIFA_TEST_SANS_CACHE=1 force l'ancienne voie (migration complète).

def _empreinte() -> str:
    import hashlib
    h = hashlib.sha1()
    fichiers = [RACINE / "app/core/database.py", RACINE / "config.py",
                RACINE / "operations.json"]
    fichiers += sorted((RACINE / "app/core/migrations").rglob("*.py"))
    for f in fichiers:
        h.update(str(f.relative_to(RACINE)).encode())
        try:
            h.update(f.read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:16]


def _base_modele():
    import sqlite3
    import subprocess
    dossier = Path(tempfile.gettempdir()) / "mysifa_test_modeles"
    dossier.mkdir(exist_ok=True)
    modele = dossier / f"{_empreinte()}.db"
    if modele.exists():
        return str(modele)
    # Construite à part puis renommée : un test parallèle ne lit jamais une
    # base à moitié migrée. Deux constructions simultanées font le travail en
    # double, sans rien casser (os.replace est atomique).
    _fd2, brouillon = tempfile.mkstemp(dir=dossier, suffix=".tmp")
    os.close(_fd2)
    env = dict(os.environ, DB_PATH=brouillon)
    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(RACINE)!r}); import database"],
        cwd=RACINE, env=env, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, text=True,
    )
    if r.returncode != 0:
        sys.stderr.write("[_base_temporaire] base modèle non construite, "
                         "migration complète dans le test :\n" + r.stderr[-2000:])
        for suffixe in ("", "-wal", "-shm"):
            try:
                os.remove(brouillon + suffixe)
            except OSError:
                pass
        return None
    # Ramène le WAL dans le fichier principal avant de le publier.
    conn = sqlite3.connect(brouillon)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.close()
    for suffixe in ("-wal", "-shm"):
        try:
            os.remove(brouillon + suffixe)
        except OSError:
            pass
    os.replace(brouillon, modele)
    return str(modele)


if os.environ.get("MYSIFA_TEST_SANS_CACHE") != "1":
    _modele = _base_modele()
    if _modele:
        import sqlite3 as _sqlite3
        _src = _sqlite3.connect(_modele)
        _dst = _sqlite3.connect(DB)
        _src.backup(_dst)
        _dst.close()
        _src.close()


@atexit.register
def _nettoyer():
    for suffixe in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(DB + suffixe)
        except OSError:
            pass
