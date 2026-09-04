"""
Socle de l'integration des receptions RVGI dans le stock MyStock.

Trois objets, et une seule idee : une ligne de reception de l'ERP doit pouvoir
devenir un mouvement de stock, une fois et une seule.

`erp_article_matiere` -- l'appariement. Un article RVGI pointe UNE matiere
MyStock. La cle est le TRIPLET `(code1, code2, type_code)`, pas le couple :
`mat_mat` porte plusieurs lignes pour un meme couple, une par type, et
`1183/0001` designe une glassine en type 2 et un velin en type 3. Apparier sur
le couple seul confondrait deux matieres qui n'ont rien a voir. Releve du
04/09/2026.

La LAIZE n'est pas dans la cle. Elle se lit sur `cdf_ligne.code3` au moment de
la reception et se cree a la volee si elle est nouvelle : la mettre dans la cle
multiplierait par cinq ou six le nombre d'appariements a tenir a jour, pour une
information que l'ERP donne deja ligne par ligne.

`erp_reception_integree` -- ce qui a deja ete traite. Sans elle, chaque synchro
rejouerait les memes receptions et le stock doublerait a chaque passage. La cle
est `lif_id`, l'identifiant HFSQL de la ligne de reception : il traverse les
reconstructions du miroir (c'est deja lui qui ouvre la modale de detail dans
/erp). Les quatre colonnes de controle a cote permettent de reperer une
reattribution d'identifiant, qui rendrait cette hypothese fausse.

`stock_config` -- la date de mise en service. Aucune reprise retroactive : le
stock actuel de MyStock est la reference, et rien ne doit bouger sous les pieds
du magasin. Tant que la cle est vide, l'integration ne prend rien.
"""

NOM = "reception_rvgi_socle"

CLE_DEPUIS = "reception_rvgi_depuis"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS erp_article_matiere (
            code1           TEXT    NOT NULL,
            code2           TEXT    NOT NULL,
            type_code       INTEGER NOT NULL,
            matiere_id      INTEGER NOT NULL,
            origine         TEXT,
            notes           TEXT,
            created_at      TEXT,
            created_by_name TEXT,
            PRIMARY KEY (code1, code2, type_code)
        );

        CREATE INDEX IF NOT EXISTS idx_eam_matiere
            ON erp_article_matiere(matiere_id);

        CREATE TABLE IF NOT EXISTS erp_reception_integree (
            lif_id          INTEGER PRIMARY KEY NOT NULL,
            numero          INTEGER,
            ligne           INTEGER,
            amjl            TEXT,
            qte_rvgi        REAL,
            matiere_id      INTEGER,
            laize_id        INTEGER,
            quantite        REAL,
            unite           TEXT,
            regime          TEXT,
            mouvement_id    INTEGER,
            reception_id    INTEGER,
            integre_at      TEXT,
            integre_par     TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_eri_matiere
            ON erp_reception_integree(matiere_id);
        CREATE INDEX IF NOT EXISTS idx_eri_date
            ON erp_reception_integree(amjl);

        CREATE TABLE IF NOT EXISTS stock_config (
            cle        TEXT PRIMARY KEY NOT NULL,
            valeur     TEXT,
            updated_at TEXT
        );
        """
    )
    # Une reception de bobines attend le magasin : elle prend la forme d'une
    # `stock_receptions` sans bobine, que le scan viendra remplir. Trois
    # colonnes suffisent a la relier a l'ERP -- inutile d'ouvrir une table
    # parallele, celle-ci porte deja `rvgi_cde`, `rvgi_bl` et
    # `rvgi_qte_attendue` depuis la reprise manuelle des receptions RVGI.
    colonnes = {r[1] for r in conn.execute("PRAGMA table_info(stock_receptions)")}
    for nom, sql_type in (("rvgi_lif_id", "INTEGER"),
                          ("rvgi_matiere_id", "INTEGER"),
                          ("rvgi_laize_id", "INTEGER")):
        if nom not in colonnes:
            conn.execute("ALTER TABLE stock_receptions ADD COLUMN %s %s" % (nom, sql_type))
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sr_rvgi_lif "
                 "ON stock_receptions(rvgi_lif_id)")

    # Vide et pas une date : tant que personne n'a decide du jour de bascule,
    # l'integration ne doit RIEN prendre. Une valeur par defaut ferait entrer
    # un historique en stock au premier demarrage.
    conn.execute(
        "INSERT OR IGNORE INTO stock_config (cle, valeur) VALUES (?, '')",
        (CLE_DEPUIS,),
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM erp_article_matiere").fetchone()[0]
    print(f"[MySifa] migration reception_rvgi : socle en place, {n} appariement(s).")
