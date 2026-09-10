"""
Enregistre, sur chaque « Fin de production » (89), si le dossier est clôturé.

À la fin de production, l'opérateur choisit « Dossier terminé » ou « À
reprendre plus tard ». Le choix pilotait le planning et la mémoire produit,
mais n'était écrit nulle part dans `production_data` : une fois la saisie
passée, rien ne permettait plus de distinguer une vraie clôture d'un arrêt
en fin de poste. La liste des Saisies de MyProd en a besoin pour marquer la
fin d'un dossier.

- `fin_dossier` : 1 = dossier clôturé, 0 = à reprendre, NULL = inconnu
  (toute ligne qui n'est pas un 89, et les 89 saisis à la main).

Reprise de l'existant, en deux temps :
- depuis la première série de la mémoire produit, un 89 est une clôture si
  une série du même dossier a été figée dans les 15 minutes qui suivent : la
  série n'est matérialisée que sur « Dossier terminé », dans la même requête ;
- avant cette date, faute de trace, le dernier 89 d'un dossier est tenu pour
  sa clôture et les précédents pour des reprises.
"""

NOM = "saisie_fin_dossier"


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "production_data" not in tables:
        print("[MySifa] migration saisie_fin_dossier : table production_data absente.")
        return

    if "fin_dossier" not in _colonnes(conn, "production_data"):
        conn.execute("ALTER TABLE production_data ADD COLUMN fin_dossier INTEGER")

    debut_series = None
    if "produit_series" in tables:
        row = conn.execute("SELECT MIN(cloture_le) FROM produit_series").fetchone()
        debut_series = row[0] if row else None

    par_serie = 0
    if debut_series:
        par_serie = conn.execute(
            """UPDATE production_data
                  SET fin_dossier = CASE WHEN EXISTS (
                        SELECT 1 FROM produit_series ps
                         WHERE TRIM(ps.no_dossier) = TRIM(production_data.no_dossier)
                           AND ps.cloture_le >= production_data.date_operation
                           AND ps.cloture_le <= strftime('%Y-%m-%dT%H:%M:%S',
                                                         production_data.date_operation,
                                                         '+15 minutes')
                      ) THEN 1 ELSE 0 END
                WHERE operation_code = '89'
                  AND fin_dossier IS NULL
                  AND TRIM(COALESCE(no_dossier,'')) <> ''
                  AND date_operation >= ?""",
            (debut_series,),
        ).rowcount

    avant = conn.execute(
        """UPDATE production_data
              SET fin_dossier = CASE WHEN NOT EXISTS (
                    SELECT 1 FROM production_data x
                     WHERE x.operation_code = '89'
                       AND TRIM(x.no_dossier) = TRIM(production_data.no_dossier)
                       AND x.date_operation > production_data.date_operation
                  ) THEN 1 ELSE 0 END
            WHERE operation_code = '89'
              AND fin_dossier IS NULL
              AND TRIM(COALESCE(no_dossier,'')) <> ''
              AND (? IS NULL OR date_operation < ?)""",
        (debut_series, debut_series),
    ).rowcount

    conn.commit()
    print(
        f"[MySifa] migration saisie_fin_dossier : {par_serie} fin(s) de production "
        f"reprise(s) par la mémoire produit, {avant} par le dernier 89 du dossier."
    )
