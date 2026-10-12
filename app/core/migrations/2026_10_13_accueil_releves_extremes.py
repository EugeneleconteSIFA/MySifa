"""
Relevés d'accueil : valeur figée à l'heure de référence, minimum et maximum.

Jusqu'ici la ligne du jour était réécrite à chaque passage, donc portait l'état
de la nuit (dernier passage avant minuit). Décision du 13/10/2026 : la valeur
du jour est celle de l'heure de référence (`RELEVES_HEURE_FIGEE`, 18 h), et le
minimum et le maximum de la journée sont gardés à côté.

- minimums / maximums : objets JSON {clé: nombre}, sur toute la journée ;
- vu_le : heure du dernier passage. `maj_le` ne bouge plus une fois la valeur
  figée ; c'est `vu_le` qui dit si la boucle tourne encore.

Les lignes déjà écrites (12 et 13/10) gardent leur valeur : faute d'autre
passage connu, elle sert de minimum et de maximum.
"""


NOM = "accueil_releves_extremes"
DEPEND = ["accueil_releves_table"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(accueil_releves)").fetchall()}
    for col in ("minimums", "maximums"):
        if col not in cols:
            conn.execute(f"ALTER TABLE accueil_releves ADD COLUMN {col} TEXT NOT NULL DEFAULT '{{}}'")
    if "vu_le" not in cols:
        conn.execute("ALTER TABLE accueil_releves ADD COLUMN vu_le TEXT")
    n = 0
    for bloc, objet, filtres, jour, valeurs, mini, maj in conn.execute(
        "SELECT bloc, objet, filtres, jour, valeurs, minimums, maj_le FROM accueil_releves"
    ).fetchall():
        if mini not in (None, "", "{}"):
            continue
        conn.execute(
            "UPDATE accueil_releves SET minimums=?, maximums=?, vu_le=COALESCE(vu_le, ?)"
            " WHERE bloc=? AND objet=? AND filtres=? AND jour=?",
            (valeurs or "{}", valeurs or "{}", maj, bloc, objet, filtres, jour),
        )
        n += 1
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} relevé(s) repris.")
