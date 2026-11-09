"""
Planning RH : outils du responsable et échanges entre collègues.

Lancer : python3 tests/test_rh_planning_outils.py

Ce test verrouille :
1. Génération : recopie de la semaine source, inversion matin / après-midi
   une semaine sur deux sur une machine en mode « alterne » (attribut, pas
   nom), personne déjà affectée laissée telle quelle, semaine de congé
   écartée (samedi compris), jours de congé retirés ; l'aperçu n'écrit rien.
2. Publication : première publication prévient tout le monde, une
   republication seulement les personnes dont la semaine a changé (y compris
   celles retirées) ; l'état « modifiés » liste ces personnes.
3. Seuil d'absences : validation bloquée (409) au-delà du seuil du service,
   passe avec forcer=['seuil'].
4. Échange : le collègue accepte, le responsable valide, les deux
   affectations sont interverties ; un échange refusé par le collègue est clos.
5. Équité : jours par créneau et samedis comptés par personne.
6. Notes d'équipe : un opérateur ne voit que celles qui le visent (tous, son
   service, une machine où il est affecté).
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_rh_outils_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.routers import planning_rh_demandes as dm, planning_rh_outils as ou  # noqa: E402

_now = datetime.now().isoformat(timespec="seconds")
with get_db() as c:
    def compte(nom, role):
        return c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                         (nom.lower().replace(" ", ".") + "@local", nom, "x", role, _now)).lastrowid
    A = compte("Alice Outils", "fabrication")
    B = compte("Bruno Outils", "fabrication")
    C = compte("Chloe Outils", "fabrication")
    L = compte("Leo Outils", "logistique")
    R = compte("Resp Outils", "direction")
    M_ALT = c.execute("INSERT INTO machines (nom, code, actif) VALUES ('Machine Alt Test','MAT',1)").lastrowid
    M_FIX = c.execute("INSERT INTO machines (nom, code, actif) VALUES ('Machine Fixe Test','MFT',1)").lastrowid
    c.execute("INSERT INTO rh_machine_config (machine_id, mode_alternance) VALUES (?, 'alterne')", (M_ALT,))

    def aff(u, sem, m, cr, jours=31):
        return c.execute("INSERT INTO rh_planning_postes (user_id, semaine, machine_id, poste, creneau, jours) "
                         "VALUES (?,?,?,?,?,?)", (u, sem, m, "conducteur", cr, jours)).lastrowid
    aff(A, "2027-W10", M_ALT, "matin")
    aff(B, "2027-W10", M_FIX, "matin", 63)
    aff(C, "2027-W10", M_ALT, "aprem")
    aff(C, "2027-W11", M_FIX, "nuit")          # déjà affectée en W11
    # B en congé toute la W12, A en congé le lundi de la W11 (8 mars 2027)
    c.execute("INSERT INTO rh_conges (user_id,date_debut,date_fin,nb_jours,type_conge,statut) "
              "VALUES (?, '2027-03-22', '2027-03-26', 5, 'CP', 'valide')", (B,))
    c.execute("INSERT INTO rh_conges (user_id,date_debut,date_fin,nb_jours,type_conge,statut) "
              "VALUES (?, '2027-03-15', '2027-03-15', 1, 'CP', 'valide')", (A,))
    c.commit()

COURANT = {}
POUSSES = []


def en_tant_que(uid, role):
    COURANT.clear()
    COURANT.update({"id": uid, "nom": f"user{uid}", "email": f"u{uid}@local", "role": role})


for mod in (dm, ou):
    mod.get_current_user = lambda request: dict(COURANT)
    mod._require_conge_edit = lambda request: dict(COURANT)
    mod._require_atelier_view = lambda request: dict(COURANT)
    mod.log_action = lambda **k: None
ou._require_atelier_edit = lambda request: dict(COURANT)
ou._push = lambda uid, titre, corps, url: POUSSES.append((uid, titre)) or 1
dm._push = lambda uid, titre, corps, url="": POUSSES.append((uid, titre))


class Req:
    def __init__(self, body=None):
        self._b = body or {}
        self.client = None

    async def json(self):
        return json.loads(json.dumps(self._b))


ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(64) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def appel(f, *a):
    try:
        r = f(*a)
        if asyncio.iscoroutine(r):
            r = asyncio.run(r)
        return 200, r
    except HTTPException as e:
        return e.status_code, e.detail


def affs(sem):
    with get_db() as c:
        return {(r["user_id"], r["creneau"], r["jours"]) for r in c.execute(
            "SELECT user_id, creneau, jours FROM rh_planning_postes WHERE semaine = ?", (sem,)).fetchall()}


en_tant_que(R, "direction")

# 1. Génération.
st, ap = appel(ou.generer_planning, Req({"source": "2027-W10", "semaines": 2}))
check("aperçu : rien d'écrit", affs("2027-W12"), set())
st, g = appel(ou.generer_planning, Req({"source": "2027-W10", "semaines": 2, "appliquer": True}))
w11, w12 = affs("2027-W11"), affs("2027-W12")
check("W11 machine alternée : matin → après-midi", (A, "aprem", 30) in w11)
check("W11 : jour de congé retiré (lundi)", (A, "aprem", 31) in w11, False)
check("W11 machine fixe : créneau inchangé, samedi gardé", (B, "matin", 63) in w11)
check("W11 : personne déjà affectée laissée telle quelle", {x for x in w11 if x[0] == C}, {(C, "nuit", 31)})
check("W12 machine alternée : retour au matin", (A, "matin", 31) in w12)
check("W12 : semaine entière de congé écartée", any(x[0] == B for x in w12), False)
check("ignorées : déjà affectée et en congé", sorted({i["raison"] for i in g["ignorees"]}), ["déjà affecté(e)", "en congé"])
check("semaine source vide refusée (400)", appel(ou.generer_planning, Req({"source": "2027-W40"}))[0], 400)

# 2. Publication.
POUSSES.clear()
p1 = ou.publier_semaine("2027-W11", Req())
check("1re publication : tout le monde prévenu", len(p1["prevenus"]), 3)
etat = ou.get_publications(Req(), from_week="2027-W11")["semaines"][0]
check("publiée, aucun changement", (etat["version"], etat["modifies"]), (1, []))
with get_db() as c:
    c.execute("UPDATE rh_planning_postes SET creneau = 'matin' WHERE user_id = ? AND semaine = '2027-W11'", (A,))
    c.execute("DELETE FROM rh_planning_postes WHERE user_id = ? AND semaine = '2027-W11'", (B,))
    c.commit()
etat = ou.get_publications(Req(), from_week="2027-W11")["semaines"][0]
check("modifiés depuis publication", etat["modifies"], ["Alice Outils", "Bruno Outils"])
POUSSES.clear()
p2 = ou.publier_semaine("2027-W11", Req())
check("republication : seulement les changés", p2["prevenus"], ["Alice Outils", "Bruno Outils"])
check("version incrémentée", p2["version"], 2)

# 3. Seuil d'absences (fabrication : max 1 ; B déjà absent en W12).
ou.set_seuils.__wrapped__ if hasattr(ou.set_seuils, "__wrapped__") else None
appel(ou.set_seuils, Req({"seuils": [{"service": "fabrication", "max_absents": 1}]}))
en_tant_que(C, "fabrication")
st, dc = appel(dm.create_demande, Req({"nature": "absence", "motif_code": "CP",
                                        "date_debut": "2027-03-24", "date_fin": "2027-03-24"}))
en_tant_que(R, "direction")
lst = {d["id"]: d for d in dm.list_demandes(Req(), statut="en_attente")["demandes"]}
check("liste : absents simultanés renvoyés", (lst[dc["id"]]["absents"]["pic"], lst[dc["id"]]["absents"]["seuil"]), (1, 1))
st, det = appel(dm.decider_demande, dc["id"], Req({"decision": "valider"}))
check("seuil dépassé : confirmation (409)", (st, isinstance(det, dict) and det.get("conflict_type")), (409, "seuil"))
st, ok = appel(dm.decider_demande, dc["id"], Req({"decision": "valider", "forcer": ["seuil", "planning"]}))
check("seuil forcé : validée", ok["statut"] if st == 200 else (st, ok), "validee")

# 4. Échange en W10 : A (matin, M_ALT) ↔ C (aprem, M_ALT).
with get_db() as c:
    ida = c.execute("SELECT id FROM rh_planning_postes WHERE user_id=? AND semaine='2027-W10'", (A,)).fetchone()[0]
    idc = c.execute("SELECT id FROM rh_planning_postes WHERE user_id=? AND semaine='2027-W10'", (C,)).fetchone()[0]
en_tant_que(A, "fabrication")
opts = dm.options_echange(Req(), semaine="2027-W10")
check("options : collègues de la semaine", sorted(x["user_nom"] for x in opts["collegues"]), ["Bruno Outils", "Chloe Outils"])
st, e = appel(dm.create_demande, Req({"nature": "echange", "affectation_id": ida, "affectation_cible_id": idc}))
check("échange créé, en attente du collègue", e["statut"] if st == 200 else (st, e), "attente_collegue")
check("échange : doublon refusé (409)", appel(dm.create_demande, Req(
    {"nature": "echange", "affectation_id": ida, "affectation_cible_id": idc}))[0], 409)
en_tant_que(R, "direction")
check("responsable : échange non accepté masqué", e["id"] in {d["id"] for d in dm.list_demandes(Req())["demandes"]}, False)
en_tant_que(B, "fabrication")
check("réponse par un autre que le collègue (403)", appel(dm.repondre_echange, e["id"], Req({"accepter": True}))[0], 403)
en_tant_que(C, "fabrication")
check("collègue : échange reçu", e["id"] in {d["id"] for d in dm.mes_demandes(Req())["recues"]})
st, e2 = appel(dm.repondre_echange, e["id"], Req({"accepter": True}))
check("collègue accepte → en attente du responsable", e2["statut"], "en_attente")
en_tant_que(R, "direction")
st, e3 = appel(dm.decider_demande, e["id"], Req({"decision": "valider"}))
with get_db() as c:
    u_a = c.execute("SELECT user_id, creneau FROM rh_planning_postes WHERE id=?", (ida,)).fetchone()
    u_c = c.execute("SELECT user_id, creneau FROM rh_planning_postes WHERE id=?", (idc,)).fetchone()
check("validé : affectations interverties", ((u_a[0], u_a[1]), (u_c[0], u_c[1])), ((C, "matin"), (A, "aprem")))
en_tant_que(A, "fabrication")
with get_db() as c:
    ida2 = c.execute("SELECT id FROM rh_planning_postes WHERE user_id=? AND semaine='2027-W12'", (A,)).fetchone()[0]
    idc2 = c.execute("SELECT id FROM rh_planning_postes WHERE user_id=? AND semaine='2027-W12'", (C,)).fetchone()[0]
st, e4 = appel(dm.create_demande, Req({"nature": "echange", "affectation_id": ida2, "affectation_cible_id": idc2}))
en_tant_que(C, "fabrication")
st, e5 = appel(dm.repondre_echange, e4["id"], Req({"accepter": False}))
check("refus du collègue : demande close", e5["statut"], "refusee")

# 5. Équité.
en_tant_que(R, "direction")
eq = {p["nom"]: p for p in ou.get_equite(Req(), annee=2027)["personnes"]}
check("équité : samedis comptés (Bruno)", eq["Bruno Outils"]["samedis"], 1)
check("équité : nuits comptées (Chloé)", eq["Chloe Outils"]["nuit"], 5)

# 6. Notes d'équipe.
ou.create_note_equipe and appel(ou.create_note_equipe, Req({"semaine_debut": "2027-W10", "texte": "Pour tous"}))
appel(ou.create_note_equipe, Req({"semaine_debut": "2027-W10", "texte": "Logistique chargée",
                                  "cible_type": "service", "cible_valeur": "logistique"}))
appel(ou.create_note_equipe, Req({"semaine_debut": "2027-W10", "semaine_fin": "2027-W11",
                                  "texte": "Encre", "cible_type": "machine", "cible_valeur": M_FIX,
                                  "importance": "important", "prevenir": True}))
check("note bornée (texte vide refusé)", appel(ou.create_note_equipe, Req({"semaine_debut": "2027-W10"}))[0], 400)
en_tant_que(L, "logistique")
vues = [n["texte"] for n in ou.get_notes_equipe(Req(), from_week="2027-W10")["notes"]]
check("logisticien : tous + logistique", sorted(vues), ["Logistique chargée", "Pour tous"])
en_tant_que(B, "fabrication")
vues = [n["texte"] for n in ou.get_notes_equipe(Req(), from_week="2027-W10")["notes"]]
check("affecté à la machine : note machine en tête", vues, ["Encre", "Pour tous"])

print()
print("ÉCHECS : " + ", ".join(ECHECS) if ECHECS else "Tous les contrôles passent.")
sys.exit(1 if ECHECS else 0)
