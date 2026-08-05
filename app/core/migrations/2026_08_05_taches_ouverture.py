"""
Ouverture effective du gestionnaire de tâches aux services.

La migration `taches_service_perimetre` a seedé la matrice avec `none` pour
tous les services : le parti pris était de ne rien changer au démarrage et
d'ouvrir service par service à la main. Décision revue à l'usage — une tâche
doit pouvoir être assignée à n'importe qui, et un assigné qui reçoit un 403 en
cliquant sur sa pastille n'a aucun sens. Le défaut devient donc `write` :
chacun gère ses tâches et celles de son service.

Pourquoi une seconde migration plutôt que corriger la première : elle est déjà
passée sur les bases de staging, son `NOM` y est enregistré, elle ne se
rejouera pas — et son `INSERT OR IGNORE` ne réécrirait de toute façon pas des
lignes existantes.

Le filtre sur `updated_by` est ce qui rend l'opération sûre : seules les lignes
posées par le seed initial sont relevées. Un service repassé à `none`
délibérément dans Paramètres porte un autre auteur et n'est pas touché.

Sur une base où la première migration n'est pas encore passée (production),
elle seedera directement `write` et celle-ci ne trouvera rien à faire.
"""

NOM = "taches_ouverture_services"
DEPEND = ["taches_service_perimetre"]

_SEED_INITIAL = "migration taches_service_perimetre"


def appliquer(conn):
    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_access_defaults'"
    ).fetchone()
    if not existe:
        return

    cur = conn.execute(
        "UPDATE role_access_defaults SET level='write', updated_by=? "
        " WHERE app_id='taches' AND module_id='_app' "
        "   AND level='none' AND updated_by=?",
        ("migration " + NOM, _SEED_INITIAL),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {cur.rowcount} service(s) ouvert(s) "
          "en ecriture sur le gestionnaire de taches.")
