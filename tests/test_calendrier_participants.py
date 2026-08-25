"""
MyCalendrier — invites d'une reunion : structure de base et invariants.

Lancer : python3 tests/test_calendrier_participants.py

Le test ne passe pas par les endpoints (ils demandent FastAPI et une session) :
il verifie ce dont ils dependent — la migration, la contrainte d'unicite d'une
invitation, la conservation des reponses quand une reunion est annulee, et les
deux requetes qui ne sont evidentes ni l'une ni l'autre : « qui est pris sur ce
creneau » et « combien d'invitations sans reponse ».
"""

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(58) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config  # noqa: E402
config.DB_PATH = db
import app.core.database as dbmod  # noqa: E402
dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

with dbmod.get_db() as conn:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check("table cal_event_participants creee", "cal_event_participants" in tables, True)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(cal_events_perso)").fetchall()}
    check("colonne annule ajoutee", "annule" in cols, True)
    check("colonnes de serie ajoutees",
          {"serie_id", "recurrence"} <= cols, True)

    # Ids hauts : init_db seede deja des comptes sur les premiers ids.
    ORG, INVITE, TIERS = 901, 902, 903
    for i, (nom, mail) in zip(
        (ORG, INVITE, TIERS),
        [("Organisateur", "org@sifa.pro"), ("Invitee", "inv@sifa.pro"), ("Tiers", "tiers@sifa.pro")],
    ):
        conn.execute(
            """INSERT INTO users (id, email, nom, password_hash, role, actif, created_at)
               VALUES (?, ?, ?, 'x', 'administration', 1, '2026-08-24T08:00:00')""",
            (i, mail, nom),
        )
    conn.execute(
        """INSERT INTO cal_events_perso (id, user_id, titre, date_debut, date_fin, all_day, prive)
           VALUES (1, 901, 'Point hebdo', '2026-09-01T10:00', '2026-09-01T11:00', 0, 0)"""
    )
    conn.execute(
        "INSERT INTO cal_event_participants (event_id, user_id) VALUES (1, 902)"
    )
    conn.commit()

    statut = conn.execute(
        "SELECT statut FROM cal_event_participants WHERE event_id=1 AND user_id=902"
    ).fetchone()["statut"]
    check("invitation en attente par defaut", statut, "en_attente")

    # Une double invitation ne cree pas de doublon (INSERT OR IGNORE cote code).
    conn.execute(
        "INSERT OR IGNORE INTO cal_event_participants (event_id, user_id) VALUES (1, 902)"
    )
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM cal_event_participants WHERE event_id=1"
    ).fetchone()[0]
    check("pas de doublon d'invitation", n, 1)

    # « Qui est deja pris » : l'organisateur ET l'invite qui n'a pas refuse.
    def occupes(debut, fin, ids):
        marks = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT DISTINCT q.user_id FROM (
                SELECT e.user_id AS user_id, e.date_debut, e.date_fin, e.annule
                  FROM cal_events_perso e
                UNION ALL
                SELECT p.user_id AS user_id, e.date_debut, e.date_fin, e.annule
                  FROM cal_event_participants p
                  JOIN cal_events_perso e ON e.id = p.event_id
                 WHERE p.statut <> 'refuse'
            ) q
            WHERE q.user_id IN ({marks})
              AND COALESCE(q.annule, 0) = 0
              AND q.date_debut < ? AND q.date_fin > ?
            """,
            (*ids, fin, debut),
        ).fetchall()
        return sorted(int(r["user_id"]) for r in rows)

    check("organisateur et invite occupes",
          occupes("2026-09-01T10:30", "2026-09-01T11:30", [ORG, INVITE, TIERS]), [ORG, INVITE])
    check("creneau voisin libre",
          occupes("2026-09-01T11:00", "2026-09-01T12:00", [ORG, INVITE, TIERS]), [])

    conn.execute(
        "UPDATE cal_event_participants SET statut='refuse' WHERE event_id=1 AND user_id=902"
    )
    conn.commit()
    check("un refus libere le creneau de l'invite",
          occupes("2026-09-01T10:30", "2026-09-01T11:30", [ORG, INVITE, TIERS]), [ORG])

    # Annulation : la reunion et ses reponses restent, mais sortent des vues.
    conn.execute("UPDATE cal_events_perso SET annule=1 WHERE id=1")
    conn.execute(
        "UPDATE cal_event_participants SET statut='en_attente' WHERE event_id=1"
    )
    conn.commit()
    check("invites conserves apres annulation",
          conn.execute("SELECT COUNT(*) FROM cal_event_participants WHERE event_id=1").fetchone()[0],
          1)
    check("reunion annulee : plus personne d'occupe",
          occupes("2026-09-01T10:30", "2026-09-01T11:30", [ORG, INVITE, TIERS]), [])

    # Pastille : une invitation sur une reunion annulee ne compte pas.
    def en_attente(uid):
        return conn.execute(
            """SELECT COUNT(*) FROM cal_event_participants p
                 JOIN cal_events_perso e ON e.id = p.event_id
                WHERE p.user_id = ? AND p.statut = 'en_attente'
                  AND COALESCE(e.annule, 0) = 0
                  AND date(substr(e.date_fin, 1, 10)) >= date('2026-08-24')""",
            (uid,),
        ).fetchone()[0]

    check("pastille ignore les reunions annulees", en_attente(INVITE), 0)
    conn.execute("UPDATE cal_events_perso SET annule=0 WHERE id=1")
    conn.commit()
    check("pastille compte l'invitation sans reponse", en_attente(INVITE), 1)


    # ------------------------------------------------------------------
    # Rappel propre a l'evenement, invites externes, delegation
    # ------------------------------------------------------------------
    conn.execute(
        """INSERT INTO cal_events_perso
               (id, user_id, titre, date_debut, date_fin, all_day, prive, rappel_minutes)
           VALUES (2, 901, 'Comite', '2026-09-02T10:00', '2026-09-02T11:00', 0, 0, 60)"""
    )
    conn.execute(
        """INSERT INTO cal_events_perso
               (id, user_id, titre, date_debut, date_fin, all_day, prive, rappel_minutes)
           VALUES (3, 901, 'Sans rappel', '2026-09-02T10:00', '2026-09-02T11:00', 0, 0, 0)"""
    )
    conn.commit()

    # Meme regle que /api/calendrier/notifications : la fenetre depend de la
    # ligne, pas d'une constante — c'est la partie que SQLite doit calculer.
    def rappels_dus(maintenant):
        return sorted(
            int(r["id"])
            for r in conn.execute(
                """SELECT e.id FROM cal_events_perso e
                    WHERE COALESCE(e.all_day, 0) = 0
                      AND COALESCE(e.annule, 0) = 0
                      AND COALESCE(e.rappel_minutes, 10) > 0
                      AND e.date_debut >= ?
                      AND datetime(e.date_debut) <=
                          datetime(?, '+' || COALESCE(e.rappel_minutes, 10) || ' minutes')""",
                (maintenant, maintenant),
            ).fetchall()
        )

    check("rappel a 60 min : rien 90 min avant", rappels_dus("2026-09-02T08:30"), [])
    check("rappel a 60 min : du 45 min avant", rappels_dus("2026-09-02T09:15"), [2])
    check("rappel a 0 : jamais rappele", 3 in rappels_dus("2026-09-02T09:59"), False)

    conn.execute(
        """INSERT INTO cal_event_invites_ext (event_id, email, jeton)
           VALUES (2, 'client@exemple.fr', 'jeton-abc')"""
    )
    conn.commit()
    doublon = True
    try:
        conn.execute(
            """INSERT INTO cal_event_invites_ext (event_id, email, jeton)
               VALUES (2, 'client@exemple.fr', 'jeton-def')"""
        )
        conn.commit()
    except Exception:
        conn.rollback()
        doublon = False
    check("un externe n'est invite qu'une fois", doublon, False)
    check("le jeton identifie l'invitation",
          conn.execute(
              "SELECT statut FROM cal_event_invites_ext WHERE jeton = 'jeton-abc'"
          ).fetchone()["statut"],
          "en_attente")

    conn.execute(
        "INSERT INTO cal_delegations (proprietaire_id, delegue_id) VALUES (901, 902)"
    )
    conn.commit()
    check("delegation lisible dans le sens du delegue",
          [int(r["proprietaire_id"]) for r in conn.execute(
              "SELECT proprietaire_id FROM cal_delegations WHERE delegue_id = 902"
          ).fetchall()],
          [901])
    check("pas de delegation en double",
          conn.execute(
              "SELECT COUNT(*) FROM cal_delegations WHERE proprietaire_id=901 AND delegue_id=902"
          ).fetchone()[0],
          1)


# ---------------------------------------------------------------------------
# Recurrence : depliage d'une serie
# ---------------------------------------------------------------------------
from datetime import date as _date, datetime as _dt  # noqa: E402
from app.services.cal_recurrence import occurrences_serie  # noqa: E402


def _jours(regle, d0, d1, fin):
    occ = occurrences_serie(d0, d1, regle, fin)
    return [x[0].strftime("%d/%m") for x in occ]


D0 = _dt(2026, 8, 28, 9, 0)   # un vendredi
D1 = _dt(2026, 8, 28, 10, 0)
check("hebdo : un creneau par semaine",
      _jours("hebdo", D0, D1, _date(2026, 9, 18)), ["28/08", "04/09", "11/09", "18/09"])
check("ouvres : le week-end est saute",
      _jours("ouvres", D0, D1, _date(2026, 9, 2)), ["28/08", "31/08", "01/09", "02/09"])
check("bihebdo : une semaine sur deux",
      _jours("bihebdo", D0, D1, _date(2026, 9, 30)), ["28/08", "11/09", "25/09"])
# Le piege du mensuel : sans ancrage sur le premier creneau, un 31 ramene au 28
# de fevrier resterait au 28 tous les mois suivants.
check("mensuel : le quantieme ne derive pas",
      _jours("mensuel", _dt(2026, 1, 31, 9, 0), _dt(2026, 1, 31, 10, 0), _date(2026, 5, 15)),
      ["31/01", "28/02", "31/03", "30/04"])
check("la duree du creneau est conservee",
      (occurrences_serie(D0, D1, "hebdo", _date(2026, 9, 4))[1][1]
       - occurrences_serie(D0, D1, "hebdo", _date(2026, 9, 4))[1][0]).seconds // 60,
      60)
check("une fin anterieure ne cree rien de plus que le premier creneau",
      len(occurrences_serie(D0, D1, "hebdo", _date(2026, 8, 28))), 1)

os.unlink(db)
print()
if FAIL:
    print(f"{len(FAIL)} echec(s) : " + ", ".join(FAIL))
    sys.exit(1)
print("Tous les controles passent.")
