"""
Seuils d'arret — quand la repetition d'un arret cesse d'etre de la routine.

Un arret n'est pas un incident : il y en a, il y en aura, et le code le dit
deja. « 53 — Casse bande » se suffit a lui-meme. Ce qui manquait n'etait pas
la qualification d'un arret, c'etait quelqu'un pour regarder l'accumulation.

Trois compteurs tournent en parallele sur un couple (dossier, machine, code) :

- la repetition — la Nieme fois, N dependant du code ;
- la duree d'un seul arret ;
- la duree cumulee du meme code sur la production.

Le premier des trois qui tombe fait un franchissement : la ligne part au
rapport de prod, et les trois compteurs repartent a zero.

Deux garde-fous qui decident si la regle sera tenable a l'atelier :

- certains codes exigent une explication des la premiere fois, sans compteur
  (`mode = 'permanent'`) — l'intervention technique et l'approvisionnement,
  ou la repetition n'apprend rien que la premiere occurrence ne disait deja ;
- un franchissement n'exige une explication que si le champ commentaire est
  vide. Sur juin-aout 2026, 49 des 71 franchissements portaient deja un texte
  ecrit spontanement : la regle ne cree pas la matiere du rapport, elle la
  ramasse.

Les seuils vivent en base et s'editent en Parametres — aucune valeur SIFA
n'est ecrite en dur ici, le seed n'est qu'un point de depart cale sur les
saisies reelles de juin a aout 2026.
"""

NOM = "arret_seuils"

# Cale sur l'export Saisies du 27/08/2026 (2 179 lignes, 336 arrets,
# 128 productions) : 71 franchissements sur 12 semaines, dont 22 exigeant
# reellement une explication — 7 % des arrets.
SEED_REGLES = [
    # (cible_type, cible,  mode,         repetitions, commentaire)
    ("code",      "64",    "permanent",  0,  "Intervention technique"),
    ("categorie", "appro", "permanent",  0,  "Approvisionnement et attente matiere"),
    ("code",      "53",    "repetition", 4,  "Casse bande"),
    ("code",      "51",    "repetition", 4,  "Casse Echenillage"),
    ("code",      "50",    "repetition", 3,  "Arret machine"),
    ("code",      "62",    "repetition", 3,  "Remplissage colle Errepi"),
    ("defaut",    "",      "repetition", 2,  "Tout autre code d'arret"),
]

SEED_PARAMS = [
    ("duree_unitaire_min", "60"),
    ("duree_cumul_min", "90"),
    ("categories_surveillees", "arret,appro,technique"),
]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS arret_seuils (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cible_type  TEXT NOT NULL,
            cible       TEXT NOT NULL DEFAULT '',
            machine     TEXT,
            mode        TEXT NOT NULL,
            repetitions INTEGER NOT NULL DEFAULT 0,
            libelle     TEXT,
            actif       INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL,
            updated_at  TEXT,
            updated_par TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_arret_seuils_cible
            ON arret_seuils(cible_type, cible, COALESCE(machine,''));

        CREATE TABLE IF NOT EXISTS arret_seuils_params (
            cle    TEXT PRIMARY KEY NOT NULL,
            valeur TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS arret_seuils_franchis (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            saisie_id           INTEGER NOT NULL,
            no_dossier          TEXT,
            machine             TEXT,
            operation_code      TEXT NOT NULL,
            operation           TEXT,
            operateur           TEXT,
            regle               TEXT NOT NULL,
            compteur            INTEGER NOT NULL DEFAULT 0,
            duree_saisie_min    REAL,
            duree_cumul_min     REAL,
            commentaire_present INTEGER NOT NULL DEFAULT 0,
            explication_exigee  INTEGER NOT NULL DEFAULT 0,
            explication_texte   TEXT,
            explication_le      TEXT,
            created_at          TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_arret_franchis_date
            ON arret_seuils_franchis(created_at);
        CREATE INDEX IF NOT EXISTS idx_arret_franchis_dossier
            ON arret_seuils_franchis(no_dossier, machine, operation_code, id);
        CREATE INDEX IF NOT EXISTS idx_arret_franchis_saisie
            ON arret_seuils_franchis(saisie_id);
        """
    )

    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")

    for cible_type, cible, mode, repetitions, libelle in SEED_REGLES:
        conn.execute(
            """INSERT OR IGNORE INTO arret_seuils
               (cible_type, cible, machine, mode, repetitions, libelle, actif, created_at)
               VALUES (?,?,NULL,?,?,?,1,?)""",
            (cible_type, cible, mode, repetitions, libelle, now),
        )
    for cle, valeur in SEED_PARAMS:
        conn.execute(
            "INSERT OR IGNORE INTO arret_seuils_params (cle, valeur) VALUES (?,?)",
            (cle, valeur),
        )
    conn.commit()
    print("[MySifa] migration arret_seuils : tables et seuils par defaut en place.")
