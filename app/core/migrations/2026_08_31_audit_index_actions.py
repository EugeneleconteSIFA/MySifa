"""
Index du journal des actions, avant que son volume ne change d'ordre.

Jusqu'ici `audit_logs` recevait les gestes de sept routers : quelques centaines
de lignes par mois, que trois index (created_at, user_id, module) suffisaient à
tenir. Le journal couvre desormais TOUTES les ecritures de MySifa, saisies
d'atelier comprises — soit plusieurs milliers de lignes par mois.

Deux acces deviennent alors couteux et n'avaient pas d'index :

- le filtre par action (`WHERE action = 'DELETE'`), qui faisait un balayage
  complet de la table ;
- le filtre par module combine au tri chronologique, ou l'index sur `module`
  seul obligeait SQLite a trier le sous-ensemble a chaque page.

Le compose (module, created_at DESC) sert les deux cas : filtrer un module et
paginer dedans, ce qui est exactement ce que fait la page Parametres.

Aucune donnee n'est touchee, aucune ligne n'est supprimee : la retention du
journal reste entiere et se decide ailleurs.
"""

NOM = "audit_logs_index_action"


def appliquer(conn):
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_module_date "
        "ON audit_logs(module, created_at DESC)"
    )
    conn.commit()
    print("[MySifa] migration audit_logs_index_action : index action + (module, date) en place.")
