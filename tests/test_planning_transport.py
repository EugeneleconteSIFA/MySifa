"""
Planning de production : la contrainte transport, et surtout ce qu'elle ne
change pas.

Le planning est la piece centrale de MySifa. Une regle qui s'y greffe doit
d'abord prouver qu'elle est INVISIBLE quand elle ne s'applique pas : mêmes
dates, même ordre, mêmes creneaux qu'avant. C'est la moitie de ce fichier, et
c'est la moitie qui compte le plus — il n'existait aucun test de planning dans
le depot avant celui-ci.

L'autre moitie verifie ce que la regle fait quand elle s'applique :

- la marge de 20 % occupe reellement le creneau et decale la file ;
- `duree_heures` n'est jamais reecrite en base ;
- un reordonnancement qui ferait rater un enlevement est refuse ;
- un jour passe en chome qui ferait rater un enlevement est refuse, et
  n'est pas ecrit ;
- un dossier deja en retard ne bloque pas les gestes qui ne l'aggravent pas ;
- depuis le 04/09/2026, le gel H-48 s'ajoute par-dessus : il ne refuse
  jamais, il fait signer, et il ignore le seuil de palettes.

Les assertions sont RELATIVES (avant/apres) et non calendaires : le planning
part de l'instant courant, un test qui figerait des dates casserait au premier
week-end.

Lancer : python3 tests/test_planning_transport.py
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp(prefix="mysifa_tp_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")

import database  # noqa: E402  — toujours avant tout app.* (cf. CLAUDE.md)
from database import get_db  # noqa: E402
from app.routers import planning as P  # noqa: E402
from app.services import transport_planning as tp  # noqa: E402

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def vrai(cas, cond):
    verifier(cas, bool(cond), True)


MACHINE_ID = 1
JOUR = timedelta(days=1)


def _init_machine(conn):
    conn.execute("DELETE FROM planning_entries")
    conn.execute("DELETE FROM expe_depart_dossiers")
    conn.execute("DELETE FROM expe_departs")
    conn.execute("DELETE FROM planning_day_worked")
    conn.execute("DELETE FROM planning_day_horaires")
    conn.execute("DELETE FROM planning_holidays")
    conn.execute("DELETE FROM machines")
    conn.execute(
        """INSERT INTO machines (id, nom, code, horaires_lundi, horaires_mardi,
                                 horaires_mercredi, horaires_jeudi, horaires_vendredi,
                                 horaires_samedi, actif, created_at, journee_entiere)
           VALUES (?,?,?,?,?,?,?,?,?,1,?,0)""",
        (MACHINE_ID, "Cohesio test", "CT", "5,21", "5,21", "5,21", "5,21",
         "5,21", "5,21", datetime.now().isoformat()),
    )
    # Machine ouverte 5h-21h tous les jours sur 60 jours : le test mesure la
    # regle, pas le calendrier d'atelier — sans ça, un dimanche deplacerait
    # toutes les fins. On evite volontairement la fenetre 0h-24h : elle expose
    # un decalage d'un jour du moteur de planning quand un creneau tombe pile
    # a minuit, qui n'a rien a voir avec la contrainte transport.
    jour = datetime.now().date()
    for k in range(-2, 60):
        d = (jour + timedelta(days=k)).isoformat()
        conn.execute(
            "INSERT INTO planning_day_worked (machine_id, date, is_worked) VALUES (?,?,1)",
            (MACHINE_ID, d),
        )
        conn.execute(
            """INSERT INTO planning_day_horaires
                 (machine_id, date, heure_debut, heure_fin, journee_entiere)
               VALUES (?,?,5,21,0)""",
            (MACHINE_ID, d),
        )
    conn.commit()


def _ajouter(conn, ref, duree, position):
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO planning_entries
             (machine_id, position, reference, numero_of, client, duree_heures,
              statut, notes, created_at, updated_at, a_placer, valide)
           VALUES (?,?,?,?,?,?, 'attente', '', ?, ?, 0, 1)""",
        (MACHINE_ID, position, ref, ref, "Client", duree, now, now),
    )
    conn.commit()
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def _depart(conn, entry_id, jours, palettes, transporteur="CEVA"):
    d = (datetime.now().date() + timedelta(days=jours)).isoformat()
    cur = conn.execute(
        """INSERT INTO expe_departs
             (date_enlevement, transporteur, nb_palette, statut, created_at,
              planning_entry_id)
           VALUES (?,?,?, 'en_attente', ?, ?)""",
        (d, transporteur, palettes, datetime.now().isoformat(), entry_id),
    )
    did = cur.lastrowid
    conn.execute(
        """INSERT INTO expe_depart_dossiers (depart_id, planning_entry_id, created_at)
           VALUES (?,?,?)""",
        (did, entry_id, datetime.now().isoformat()),
    )
    conn.commit()
    return did


def _timeline(conn):
    entries = P._ordre_timeline(P._entries_enrichies(conn, MACHINE_ID))
    mac = dict(conn.execute("SELECT * FROM machines WHERE id=?", (MACHINE_ID,)).fetchone())
    cfgs, off, dw, dh = P._load_planning_calendar_maps(conn, MACHINE_ID)
    return P._compute_timeline_slots(
        conn, MACHINE_ID, mac, cfgs, off, dw, dh, entries, persist=False
    )


def _fins(slots):
    return {s["entry_id"]: s["end"] for s in slots}


def _heures_ouvrees(conn, iso_a, iso_b):
    """Ecart entre deux fins, en heures MACHINE — la seule mesure stable ici.

    Comparer des heures d'horloge ferait dependre le test de l'heure a laquelle
    on le lance : deux heures de production a cheval sur une nuit d'atelier
    valent seize heures de calendrier.
    """
    mac = dict(conn.execute("SELECT * FROM machines WHERE id=?", (MACHINE_ID,)).fetchone())
    cal = P._load_planning_calendar_maps(conn, MACHINE_ID)
    f = P._hours_for_date_factory(mac, cal[0], cal[1], cal[2], cal[3])
    a = datetime.strptime(iso_a, "%Y-%m-%dT%H:%M:%S")
    b = datetime.strptime(iso_b, "%Y-%m-%dT%H:%M:%S")
    return round(P._work_hours_between(f, min(a, b), max(a, b)), 2)


def _depart_le(conn, entry_id, jour_iso, palettes, transporteur="CEVA"):
    """Depart a une date donnee (et non a N jours) — les tests calent la date
    sur la fin de production calculee, pas sur le calendrier."""
    cur = conn.execute(
        """INSERT INTO expe_departs
             (date_enlevement, transporteur, nb_palette, statut, created_at,
              planning_entry_id)
           VALUES (?,?,?, 'en_attente', ?, ?)""",
        (jour_iso, transporteur, palettes, datetime.now().isoformat(), entry_id),
    )
    did = cur.lastrowid
    conn.execute(
        """INSERT INTO expe_depart_dossiers (depart_id, planning_entry_id, created_at)
           VALUES (?,?,?)""",
        (did, entry_id, datetime.now().isoformat()),
    )
    conn.commit()
    return did


def _base(durees=(10.0, 10.0, 10.0, 10.0)):
    with get_db() as conn:
        _init_machine(conn)
        ids = [_ajouter(conn, f"OF-{i+1}", d, i + 1) for i, d in enumerate(durees)]
    return ids


# ── 1. Sans transport reserve, rien ne change ──────────────────────────────
print("\n1. Non-regression — sans transport reserve, le planning est identique")

ids = _base()
with get_db() as conn:
    ref_slots = _timeline(conn)
    ref_fins = _fins(ref_slots)
verifier("4 creneaux calcules", len(ref_slots), 4)
vrai("aucun creneau ne porte de transport", all(s["transport"] is None for s in ref_slots))

with get_db() as conn:
    _depart(conn, ids[0], 10, 5.0)          # sous le seuil
    _depart(conn, ids[1], 10, None)         # palettes inconnues
    _depart(conn, ids[2], -3, 30.0)         # enlevement deja passe
    apres = _timeline(conn)
verifier("dates inchangees avec des departs non qualifiants", _fins(apres), ref_fins)
vrai("toujours aucun camion", all(s["transport"] is None for s in apres))

with get_db() as conn:
    _depart(conn, ids[0], 20, 12.0)         # qualifiant, mais regle desactivee
    tp.enregistrer_params(conn, {"actif": False})
    eteint = _timeline(conn)
verifier("regle desactivee : dates inchangees", _fins(eteint), ref_fins)
vrai("regle desactivee : aucun camion", all(s["transport"] is None for s in eteint))

with get_db() as conn:
    tp.enregistrer_params(conn, {"actif": True})

# ── 2. La marge occupe le creneau ──────────────────────────────────────────
print("\n2. Marge — elle allonge le creneau et decale la file")

ids = _base()
with get_db() as conn:
    avant = _timeline(conn)
    fins_avant = _fins(avant)
    _depart(conn, ids[0], 30, 12.0)
    apres = _timeline(conn)
    fins_apres = _fins(apres)
    duree_db = conn.execute(
        "SELECT duree_heures FROM planning_entries WHERE id=?", (ids[0],)
    ).fetchone()[0]

with get_db() as conn:
    d0 = _heures_ouvrees(conn, fins_avant[ids[0]], fins_apres[ids[0]])
    d3 = _heures_ouvrees(conn, fins_avant[ids[3]], fins_apres[ids[3]])
verifier("le dossier contraint gagne 20 % de 10 h", d0, 2.0)
verifier("le dernier dossier est decale d'autant", d3, 2.0)
verifier("duree_heures n'a pas ete reecrite en base", duree_db, 10.0)

s0 = [s for s in apres if s["entry_id"] == ids[0]][0]
vrai("le creneau porte un camion", s0["transport"] is not None)
verifier("marge annoncee au front", s0["transport"]["marge_heures"], 2.0)
verifier("palettes annoncees", s0["transport"]["palettes"], 12.0)
verifier("transporteur annonce", s0["transport"]["transporteur"], "CEVA")
verifier("tension verte (30 jours d'avance)", s0["transport"]["tension"], "ok")
vrai("les autres creneaux restent sans camion",
     all(s["transport"] is None for s in apres if s["entry_id"] != ids[0]))

# ── 3. Refus d'un reordonnancement ─────────────────────────────────────────
print("\n3. Refus dur — le reordonnancement qui ferait rater l'enlevement")

from fastapi import HTTPException  # noqa: E402

ids = _base((10.0, 20.0, 20.0, 20.0))
with get_db() as conn:
    # L'enlevement est cale au lendemain de la fin calculee : la file actuelle
    # tient, la deplacer ne tient plus. Caler sur une date fixe rendrait le
    # resultat dependant de l'heure a laquelle le test tourne.
    fin0 = _fins(_timeline(conn))[ids[0]][:10]
    lendemain = (datetime.strptime(fin0, "%Y-%m-%d").date() + JOUR).isoformat()
    _depart_le(conn, ids[0], lendemain, 9.0)
    ordre_ok = list(ids)
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, ordre_ok)
    except HTTPException as e:
        erreur = e
verifier("l'ordre actuel ne declenche rien", erreur, None)

with get_db() as conn:
    ordre_ko = ids[1:] + [ids[0]]   # le dossier contraint passe en dernier
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, ordre_ko)
    except HTTPException as e:
        erreur = e
vrai("passer le dossier contraint en dernier est refuse", erreur is not None)
verifier("code HTTP 409", getattr(erreur, "status_code", None), 409)
vrai("le message nomme le dossier", "OF-1" in str(getattr(erreur, "detail", "")))
vrai("le message nomme le transporteur", "CEVA" in str(getattr(erreur, "detail", "")))

with get_db() as conn:
    positions = [
        int(r["id"]) for r in conn.execute(
            "SELECT id FROM planning_entries WHERE machine_id=? ORDER BY position",
            (MACHINE_ID,)).fetchall()
    ]
verifier("aucune position n'a bouge", positions, ids)

# ── 4. Sans transport, le reordonnancement reste libre ─────────────────────
print("\n4. Non-regression — sans transport reserve, tout reordonnancement passe")

ids = _base((10.0, 20.0, 20.0, 20.0))
with get_db() as conn:
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, list(reversed(ids)))
    except HTTPException as e:
        erreur = e
verifier("ordre inverse accepte", erreur, None)

with get_db() as conn:
    _depart(conn, ids[0], 10, 4.0)  # petit depart, et loin : rien ne s'applique
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, list(reversed(ids)))
    except HTTPException as e:
        erreur = e
verifier("petit depart lointain : ordre inverse toujours accepte", erreur, None)

# ── 4 bis. Le gel, lui, ne connait pas le seuil de palettes ────────────────
# Depuis le 04/09/2026 : le meme petit depart, mais a moins de 48 h, ne refuse
# toujours pas — il demande de signer. C'est la difference entre les deux
# regles, et c'est le seul endroit du planning ou l'outil demande « pourquoi ».
print("\n4 bis. Gel H-48 — le petit depart imminent demande une confirmation")

ids = _base((10.0, 20.0, 20.0, 20.0))
with get_db() as conn:
    _depart(conn, ids[0], 1, 4.0)   # 4 palettes : hors contrainte transport
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, list(reversed(ids)))
    except HTTPException as e:
        erreur = e
vrai("enlevement demain : confirmation demandee", erreur is not None)
verifier("code HTTP 409", getattr(erreur, "status_code", None), 409)
verifier("code de la regle", (getattr(erreur, "detail", None) or {}).get("code"), "gel_transport")
vrai("le detail nomme le dossier",
     "OF-1" in str((getattr(erreur, "detail", None) or {}).get("dossiers")))

with get_db() as conn:
    erreur = None
    try:
        P._garde_transport_reorder(
            conn, MACHINE_ID, list(reversed(ids)), None,
            {"confirme_gel": True, "motif_gel": "accord client obtenu pour le 12"},
        )
    except HTTPException as e:
        erreur = e
verifier("confirme avec motif : le geste passe", erreur, None)

with get_db() as conn:
    erreur = None
    try:
        P._garde_transport_reorder(
            conn, MACHINE_ID, list(reversed(ids)), None, {"confirme_gel": True}
        )
    except HTTPException as e:
        erreur = e
vrai("confirme sans motif : toujours refuse", erreur is not None)
verifier("et le refus dit pourquoi",
         (getattr(erreur, "detail", None) or {}).get("motif_manquant"), True)

# ── 5. Un dossier deja en retard ne bloque pas ce qui ne l'aggrave pas ─────
print("\n5. Existant — deja en retard, mais on ne bloque que l'aggravation")

ids = _base((10.0, 20.0, 20.0, 20.0))
with get_db() as conn:
    _depart(conn, ids[3], -0, 9.0)  # enlevement AUJOURD'HUI : intenable
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, ids[:3] + [ids[3]])
    except HTTPException as e:
        erreur = e
verifier("ordre identique : pas de refus sur un retard preexistant", erreur, None)

with get_db() as conn:
    erreur = None
    try:
        P._garde_transport_reorder(conn, MACHINE_ID, [ids[3]] + ids[:3])
    except HTTPException as e:
        erreur = e
verifier("remonter le dossier en retard en tete : accepte", erreur, None)

# ── 6. Calendrier — un jour chome qui ferait rater l'enlevement ────────────
print("\n6. Refus dur — le jour chome qui repousse la production")

ids = _base((30.0, 20.0, 20.0, 20.0))
demain = (datetime.now().date() + JOUR).isoformat()
apres_demain = (datetime.now().date() + 2 * JOUR).isoformat()
with get_db() as conn:
    fin0 = _fins(_timeline(conn))[ids[0]][:10]
    lendemain = (datetime.strptime(fin0, "%Y-%m-%d").date() + JOUR).isoformat()
    _depart_le(conn, ids[0], lendemain, 9.0)
    avant = P._transport_avant(conn, MACHINE_ID)
    conn.execute(
        "UPDATE planning_day_worked SET is_worked=0 WHERE machine_id=? AND date IN (?,?)",
        (MACHINE_ID, demain, apres_demain),
    )
    erreur = None
    try:
        P._garde_transport_apres_ecriture(conn, MACHINE_ID, avant)
    except HTTPException as e:
        erreur = e
    # Pas de commit : la connexion se referme, SQLite annule la transaction.
vrai("chomer deux jours de production est refuse", erreur is not None)
vrai("le message nomme le dossier concerne", "OF-1" in str(getattr(erreur, "detail", "")))

with get_db() as conn:
    reste = [
        int(r["is_worked"]) for r in conn.execute(
            "SELECT is_worked FROM planning_day_worked WHERE machine_id=? AND date IN (?,?)",
            (MACHINE_ID, demain, apres_demain)).fetchall()
    ]
verifier("les jours sont restes travailles (transaction annulee)", reste, [1, 1])

print()
if FAIL:
    print(f"ECHEC : {len(FAIL)} cas")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("Planning + contrainte transport : tous les cas passent.")
