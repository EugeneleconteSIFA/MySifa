"""
Coûts matières — accès de l'administration des ventes, limité au prix d'achat.

L'ADV ouvre la liste des matières pour y corriger un prix d'achat ; tout le
reste du module (produits, fournisseurs, paramétrage, coûts au m², marges)
lui reste fermé. La restriction vit dans le code (`ROLES_PRICING_PRIX_ACHAT`
de config.py, `_prix_achat_seul` de app/routers/pricing.py) ; cette migration
ne fait qu'ouvrir la porte de l'application dans la matrice d'accès, où le
seed de 2026 avait posé « none » pour ce rôle.

Seule une ligne encore à « none » passe en lecture : un réglage choisi depuis
Paramètres › Accès n'est pas écrasé. Le niveau ne donne aucun droit
d'écriture : la saisie du prix est accordée par le rôle, pas par la matrice.
"""

from datetime import datetime

NOM = "pricing_acces_adv"


def appliquer(conn):
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_access_defaults'"
    ).fetchone():
        return
    now = datetime.now().isoformat()
    n = conn.execute(
        """UPDATE role_access_defaults SET level='read', updated_at=?, updated_by=?
            WHERE role='administration_ventes' AND app_id='pricing'
              AND module_id='_app' AND level='none'""",
        (now, f"migration {NOM}"),
    ).rowcount
    n += conn.execute(
        """INSERT OR IGNORE INTO role_access_defaults
               (role, app_id, module_id, level, updated_at, updated_by)
           VALUES ('administration_ventes', 'pricing', '_app', 'read', ?, ?)""",
        (now, f"migration {NOM}"),
    ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} ligne(s) d'accès ADV ouverte(s) sur Coûts matières.")
