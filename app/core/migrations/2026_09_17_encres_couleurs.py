"""Référentiel des couleurs d'encre (Paramètres › Fabrication › Impression).

Le BAT teinte la zone imprimée avec la couleur de l'encre. Sans référentiel,
seuls les noms simples (noir, jaune…) étaient reconnus et tout Pantone
tombait sur le violet neutre. La table associe un code (« 485 C »,
« BLEU CLAIR ») à une teinte écran.

`cle` est la forme canonique calculée par `app.services.encres_couleurs.cle`
(« P.485 C » et « 485C » donnent « 485 C ») : c'est elle qui porte l'unicité.

Seed : les références Pantone relevées dans les fiches techniques SIFA le
17/09/2026, teintes sRGB publiées pour la gamme Solid Coated. Ce sont des
approximations écran, modifiables dans Paramètres. Les versions U retombent
sur la version C tant qu'elles ne sont pas saisies.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

NOM = "encres_couleurs"

SEED = [
    ("BLACK C", "Pantone Black C", "#2D2926"),
    ("YELLOW C", "Pantone Yellow C", "#FEDD00"),
    ("PROCESS BLUE C", "Pantone Process Blue C", "#0085CA"),
    ("REFLEX BLUE C", "Pantone Reflex Blue C", "#001489"),
    ("GREEN C", "Pantone Green C", "#00AB84"),
    ("PURPLE C", "Pantone Purple C", "#BB29BB"),
    ("VIOLET C", "Pantone Violet C", "#440099"),
    ("WARM RED C", "Pantone Warm Red C", "#F9423A"),
    ("RUBINE RED C", "Pantone Rubine Red C", "#CE0058"),
    ("RHODAMINE RED C", "Pantone Rhodamine Red C", "#E10098"),
    ("021 C", "Pantone Orange 021 C", "#FE5000"),
    ("032 C", "Pantone Red 032 C", "#EF3340"),
    ("072 C", "Pantone Blue 072 C", "#10069F"),
    ("101 C", "Pantone 101 C", "#F7EA48"),
    ("107 C", "Pantone 107 C", "#FBE122"),
    ("109 C", "Pantone 109 C", "#FFD100"),
    ("116 C", "Pantone 116 C", "#FFCD00"),
    ("123 C", "Pantone 123 C", "#FFC72C"),
    ("135 C", "Pantone 135 C", "#FFC658"),
    ("136 C", "Pantone 136 C", "#FFBF3F"),
    ("162 C", "Pantone 162 C", "#FFBE9F"),
    ("165 C", "Pantone 165 C", "#FF671F"),
    ("178 C", "Pantone 178 C", "#FF585D"),
    ("185 C", "Pantone 185 C", "#E4002B"),
    ("186 C", "Pantone 186 C", "#C8102E"),
    ("192 C", "Pantone 192 C", "#E40046"),
    ("199 C", "Pantone 199 C", "#D50032"),
    ("206 C", "Pantone 206 C", "#CE0037"),
    ("210 C", "Pantone 210 C", "#F99FC9"),
    ("212 C", "Pantone 212 C", "#F04E98"),
    ("280 C", "Pantone 280 C", "#012169"),
    ("286 C", "Pantone 286 C", "#0033A0"),
    ("290 C", "Pantone 290 C", "#B9D9EB"),
    ("291 C", "Pantone 291 C", "#9BCBEB"),
    ("292 C", "Pantone 292 C", "#69B3E7"),
    ("300 C", "Pantone 300 C", "#005EB8"),
    ("313 C", "Pantone 313 C", "#0092BC"),
    ("354 C", "Pantone 354 C", "#00B140"),
    ("359 C", "Pantone 359 C", "#A1D884"),
    ("361 C", "Pantone 361 C", "#43B02A"),
    ("428 C", "Pantone 428 C", "#C1C6C8"),
    ("432 C", "Pantone 432 C", "#333F48"),
    ("472 C", "Pantone 472 C", "#E59E6D"),
    ("484 C", "Pantone 484 C", "#9A3324"),
    ("485 C", "Pantone 485 C", "#DA291C"),
    ("647 C", "Pantone 647 C", "#236192"),
    ("1205 C", "Pantone 1205 C", "#F8E08E"),
    ("1375 C", "Pantone 1375 C", "#FF9E1B"),
    ("1655 C", "Pantone 1655 C", "#FC4C02"),
    ("2587 C", "Pantone 2587 C", "#8246AF"),
    ("2592 C", "Pantone 2592 C", "#9B26B6"),
    ("2728 C", "Pantone 2728 C", "#0047BB"),
    ("2746 C", "Pantone 2746 C", "#171C8F"),
    ("3395 C", "Pantone 3395 C", "#00C389"),
    ("5265 C", "Pantone 5265 C", "#403A60"),
    ("7408 C", "Pantone 7408 C", "#F6BE00"),
    ("7424 C", "Pantone 7424 C", "#E24585"),
    ("7545 C", "Pantone 7545 C", "#425563"),
    ("COOL GRAY 11 C", "Pantone Cool Gray 11 C", "#53565A"),
]


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS encres_couleurs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT    NOT NULL,
            cle         TEXT    NOT NULL,
            libelle     TEXT,
            hex         TEXT    NOT NULL,
            actif       INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT,
            updated_by  TEXT
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_encres_couleurs_cle "
        "ON encres_couleurs(cle)"
    )
    quand = datetime.now().isoformat(timespec="seconds")
    n = 0
    for code, libelle, hx in SEED:
        cur = conn.execute(
            "INSERT OR IGNORE INTO encres_couleurs"
            " (code, cle, libelle, hex, actif, created_at) VALUES (?,?,?,?,1,?)",
            (code, code, libelle, hx, quand),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} couleur(s) d'encre ajoutée(s).")
