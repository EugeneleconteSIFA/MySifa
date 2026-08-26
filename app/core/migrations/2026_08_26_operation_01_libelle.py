"""
Renomme le code 01 « Début de production » en « Démarrer un dossier ».

Le code 01 n'ouvre pas une période de production : il ouvre un dossier, et
l'opérateur enchaîne le plus souvent sur du calage ou du nettoyage. Trois
libellés portaient le mot « production » pour trois choses différentes (01
ouvrir un dossier, 03 la machine tourne, 89 fermer le dossier ou la journée).
Le référentiel réserve désormais ce mot à l'état machine.

Le libellé n'est écrasé que s'il vaut encore la valeur historique : une
instance qui l'a déjà personnalisé dans Paramètres › Opérations garde le sien.
"""

NOM = "operation_01_libelle_demarrer_dossier"

_ANCIEN = "Début de production"
_NOUVEAU = "Démarrer un dossier"


def appliquer(conn):
    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='operation_codes' LIMIT 1"
    ).fetchone()
    if not existe:
        # Table pas encore créée : le seed initial lira operations.json, qui
        # porte déjà le nouveau libellé. Rien à reprendre.
        return

    cur = conn.execute(
        "UPDATE operation_codes SET label=? WHERE code='01' AND label=?",
        (_NOUVEAU, _ANCIEN),
    )
    conn.commit()
    if cur.rowcount:
        print(f"[MySifa] migration {NOM} : code 01 renommé en « {_NOUVEAU} ».")
    else:
        print(f"[MySifa] migration {NOM} : code 01 déjà à jour ou personnalisé, inchangé.")
