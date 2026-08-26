"""Journalise l'IP source des signaux d'engagement transporteur (MyExpé).

Sans elle, impossible de distinguer un chargement du pixel venu du
transporteur d'un chargement venu de nos propres bureaux : la boîte
`expeditions@sifa.pro` reçoit le même corps de mail, donc le même pixel, et
chaque relecture interne gonflait le compteur « Email ouvert » du
transporteur.

La colonne sert à deux choses :

- classer à l'écriture (`EXPE_IPS_INTERNES` dans `config.py`) ;
- rendre le reclassement manuel a posteriori vérifiable — quand on marque un
  hit comme « c'était nous », on veut pouvoir relire d'où il venait.

Rien n'est rempli rétroactivement : les événements existants n'ont jamais
porté cette information, l'inventer serait pire que de l'avoir vide.
"""

NOM = "expe_devis_evenement_ip"


def appliquer(conn):
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(expe_devis_evenements)"
    ).fetchall()}
    if not cols:
        # Table pas encore créée (base neuve) : `_migrate()` la crée avec la
        # colonne, il n'y a rien à reprendre ici.
        return
    if "ip" not in cols:
        conn.execute("ALTER TABLE expe_devis_evenements ADD COLUMN ip TEXT")
        conn.commit()
        print("[MySifa] migration expe_devis_evenement_ip : colonne ip ajoutee.")
