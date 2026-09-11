"""
Planning : ce que le planificateur peut faire de l'ordre des dossiers.

Le 11/09/2026, sur Cohesio 2, le planificateur est reste bloque par trois
garde-fous empiles :

- impossible de mettre Maitre Coq 1068/0002 Reliquat 3 en debut de prod : un
  dossier en attente (SOLUROAD Reliquat 9932324) trainait AU-DESSUS de l'en-cours
  XEROX 9932478, et la regle « l'en-cours garde son rang exact » refusait tout
  ce qui passait devant lui ;
- « Inserer apres » refuse derriere le dossier en cours — le cas le plus courant ;
- « Changer de machine » supprimait le dossier PUIS le recreait ailleurs : a la
  seconde etape refusee, le dossier avait disparu (Maitre Coq Reliquat 4, ressaisi
  a la main).

Ces cas verrouillent les decisions prises :

- deux regles d'ordre et seulement deux : la tete d'historique ne bouge pas, les
  termines / en cours gardent leur ordre entre eux ;
- « Passer en tete » place un dossier juste apres l'historique et le sort de
  « a placer » ;
- inserer ou placer derriere l'en-cours est permis, au milieu de l'historique
  non ;
- changer de machine garde l'id du dossier, et un refus ne perd rien ;
- cote ecran, les fleches sautent les termines et l'en-cours au lieu de
  s'arreter net dessus.

Lancer : python3 tests/test_planning_ordre.py
"""

import asyncio
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def vrai(cas, cond):
    verifier(cas, bool(cond), True)


# ── Chargement du router avec une base jetable ─────────────────────────────
#
# On charge `app/routers/planning.py` tel quel, en ne remplacant que ce qui
# touche au monde exterieur : la base, la session, le journal. La garde
# transport est la vraie, mais muette faute de tables MyExpe : ses propres cas
# vivent dans test_gel_transport.py / test_planning_transport.py. Ici on
# verifie seulement qu'un refus apres ecriture annule tout (section 4).

DB_FILE = Path(tempfile.mkdtemp()) / "planning_ordre.db"


@contextmanager
def _get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()  # sans commit : comme la vraie, une exception annule tout


JOURNAL = []
USER = {"id": 1, "nom": "Planificateur test", "email": "p@test", "role": "superadmin"}


def _module(nom, **attrs):
    m = types.ModuleType(nom)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[nom] = m
    return m


try:  # FastAPI est la dans le depot ; le stub ne sert qu'hors environnement.
    from fastapi import HTTPException  # noqa: F401
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code, detail=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _Router:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, _nom):
            return lambda *a, **k: (lambda f: f)

    _module("fastapi", APIRouter=_Router, Request=object, HTTPException=HTTPException)
    _module("fastapi.responses", JSONResponse=dict)

_module("database", get_db=_get_db)
_module(
    "config",
    FSC_CLAIMS_REQUERABLES=("fsc_100", "fsc_mix_credit"),
    ROLE_FABRICATION="fabrication",
    ROLE_DIRECTION="direction",
    ROLE_SUPERADMIN="superadmin",
)
_module("app")
_module("app.services")
_module("app.services.audit_service", log_action=lambda **k: JOURNAL.append(k))
_module("app.services.date_livraison", parse_date_livraison=lambda v: v)
_module("app.services.palettes_estimation", nb_palettes=lambda e: None)
_spec_tp = importlib.util.spec_from_file_location(
    "app.services.transport_planning", RACINE / "app" / "services" / "transport_planning.py"
)
_tp = importlib.util.module_from_spec(_spec_tp)
sys.modules["app.services.transport_planning"] = _tp
_spec_tp.loader.exec_module(_tp)
sys.modules["app.services"].transport_planning = _tp
sys.modules["app.services"].palettes_estimation = sys.modules["app.services.palettes_estimation"]
_module("services")
_module(
    "services.auth_service",
    require_admin=lambda request: USER,
    get_current_user=lambda request: USER,
    user_has_app_access=lambda user, app: True,
)
_module("services.dossier_stats", build_dossier_production_stats=lambda *a, **k: {})

_spec = importlib.util.spec_from_file_location("planning_router", RACINE / "app" / "routers" / "planning.py")
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)
HTTPException = pl.HTTPException


class Req:
    def __init__(self, body=None):
        self._body = body or {}
        self.query_params = {}
        self.client = None

    async def json(self):
        return self._body


def appel(fn, *args, body=None):
    """Execute un endpoint ; renvoie (code, reponse ou detail)."""
    try:
        res = fn(*args, Req(body))
        if asyncio.iscoroutine(res):
            res = asyncio.run(res)
        return 200, res
    except HTTPException as exc:
        return exc.status_code, exc.detail


# ── La machine du 11/09/2026 ──────────────────────────────────────────────

T, EC, A = "termine", "en_cours", "attente"
COH1, COH2 = 1, 3

# (id, client, statut, a_placer) dans l'ordre de la liste de Cohesio 2 a 11h29.
COHESIO2 = [
    (551, "Bouvard 3e cadence", T, 0),
    (552, "BOUVARD box", T, 0),
    (566, "SOLUROAD 9932324", T, 0),
    (900, "SOLUROAD Reliquat 9932324", A, 0),
    (520, "XEROX 9932478", EC, 0),
    (517, "STI 9932472", A, 0),
    (466, "STI 9932354", A, 0),
    (43, "BOUVARD 718/2", T, 0),
    (541, "LSDH Reliquat", A, 0),
    (557, "SCACHAP 9932389", T, 0),
    (292, "Evergreen L2-3-4", A, 1),
    (543, "GLS Marche 768", A, 0),
    (556, "KIABI M760", T, 0),
    (573, "HADDAD", A, 1),
    (571, "PROSOL", A, 1),
    (574, "Maitre Coq Reliquat 3", A, 0),
]
COHESIO1 = [
    (700, "Cohesio 1 termine", T, 0),
    (701, "Cohesio 1 en cours", EC, 0),
    (575, "Maitre Coq Reliquat 4", A, 0),
    (702, "Cohesio 1 attente", A, 0),
]


def remplir():
    if DB_FILE.exists():
        DB_FILE.unlink()
    conn = sqlite3.connect(DB_FILE)
    conn.executescript(
        """
        CREATE TABLE machines (id INTEGER PRIMARY KEY, nom TEXT, code TEXT, actif INTEGER DEFAULT 1);
        CREATE TABLE of_imports (id INTEGER PRIMARY KEY, qte_etiquettes REAL, qte_bobines REAL);
        CREATE TABLE fiches_techniques (
            id INTEGER PRIMARY KEY, reference TEXT, ref_produit_norm TEXT, machine TEXT,
            nb_bobines_carton REAL, palette_nb_cartons_sol REAL, palette_nb_cartons_hauteur REAL,
            support TEXT, adhesif TEXT, palette_type TEXT, cartons TEXT, mandrin_dia REAL,
            nb_etiq_bobin REAL);
        CREATE TABLE planning_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id INTEGER, position INTEGER,
            reference TEXT, client TEXT, description TEXT, format_l REAL, format_h REAL,
            duree_heures REAL DEFAULT 8, statut TEXT DEFAULT 'attente', statut_force INTEGER DEFAULT 0,
            statut_reel TEXT DEFAULT 'reellement_en_attente', notes TEXT,
            created_at TEXT, updated_at TEXT, created_by TEXT, updated_by TEXT,
            planned_start TEXT, planned_end TEXT, planned_end_manual INTEGER DEFAULT 0,
            a_placer INTEGER DEFAULT 0, valide INTEGER DEFAULT 1,
            numero_of TEXT, ref_produit TEXT, ref_produit_norm TEXT, laize REAL,
            date_livraison TEXT, commentaire TEXT, exigences_production TEXT, dos_rvgi TEXT,
            fsc_requis INTEGER DEFAULT 0, fsc_type_requis TEXT DEFAULT '',
            departement_livraison TEXT DEFAULT '', prise_rdv INTEGER DEFAULT 0,
            date_livraison_imposee INTEGER DEFAULT 0, group_id TEXT, of_import_id INTEGER,
            etiquettes_par_carton INTEGER);
        INSERT INTO machines (id, nom) VALUES (1, 'Cohésio 1'), (3, 'Cohésio 2');
        """
    )
    for mid, lignes in ((COH2, COHESIO2), (COH1, COHESIO1)):
        for pos, (eid, client, st, ap) in enumerate(lignes, start=1):
            conn.execute(
                """INSERT INTO planning_entries
                   (id, machine_id, position, reference, client, statut, statut_force, a_placer,
                    planned_start, planned_end)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (eid, mid, pos, client, client, st, 1 if st != A else 0, ap,
                 "2026-09-01T06:00:00" if st != A else None,
                 "2026-09-01T10:00:00" if st != A else None),
            )
    conn.commit()
    conn.close()


def ordre(mid):
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT id, position FROM planning_entries WHERE machine_id=? ORDER BY position", (mid,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows], [r[1] for r in rows]


def champ(eid, col):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(f"SELECT {col} FROM planning_entries WHERE id=?", (eid,)).fetchone()
    conn.close()
    return row[0] if row else None


def ids_de(lignes):
    return [l[0] for l in lignes]


STATUTS = {eid: st for eid, _, st, _ in COHESIO2 + COHESIO1}


# ── 1. La regle d'ordre ───────────────────────────────────────────────────
print("\n1. Regle d'ordre")

cur = ids_de(COHESIO2)
voulu = [551, 552, 566, 574, 900, 520, 517, 466, 43, 541, 557, 292, 543, 556, 573, 571]
vrai("Maitre Coq en debut de prod, au-dessus de SOLUROAD : accepte",
     pl._ordre_verrouille_respecte(cur, voulu, STATUTS))

voulu = cur[:5] + [574] + [i for i in cur[5:] if i != 574]
vrai("Maitre Coq juste apres l'en-cours : accepte",
     pl._ordre_verrouille_respecte(cur, voulu, STATUTS))

voulu = [551, 574, 552] + [i for i in cur[2:] if i != 574]
vrai("Maitre Coq au milieu de l'historique : refuse",
     not pl._ordre_verrouille_respecte(cur, voulu, STATUTS))

vrai("l'en-cours repasse DERRIERE des termines : refuse",
     not pl._ordre_verrouille_respecte(
         cur, [551, 552, 566, 900, 43, 520, 517, 466, 541, 557, 292, 543, 556, 573, 571, 574], STATUTS))

voulu = [551, 552, 566, 900, 517, 520, 466, 43, 541, 557, 292, 543, 556, 573, 571, 574]
vrai("un dossier en attente passe devant l'en-cours : accepte",
     pl._ordre_verrouille_respecte(cur, voulu, STATUTS))

verifier("longueur de la tete d'historique", pl._longueur_tete(cur, STATUTS), 3)


# ── 2. Passer en tete / placer apres ──────────────────────────────────────
print("\n2. Passer en tete, placer juste apres")

remplir()
JOURNAL.clear()
code, _ = appel(pl.deplacer_entry, COH2, 574, body={"en_tete": True})
verifier("Passer en tete : accepte", code, 200)
ids, pos = ordre(COH2)
verifier("Maitre Coq devient le premier dossier apres l'historique", ids[:5], [551, 552, 566, 574, 900])
verifier("positions contigues", pos, list(range(1, len(ids) + 1)))
verifier("l'en-cours n'a pas quitte la liste", 520 in ids, True)
verifier("un seul evenement au journal", len(JOURNAL), 1)
vrai("le journal nomme le dossier", "Maitre Coq Reliquat 3" in JOURNAL[-1]["objet"])

remplir()
code, _ = appel(pl.deplacer_entry, COH2, 292, body={"en_tete": True})
verifier("Passer en tete un dossier « a placer » : accepte", code, 200)
verifier("… il n'est plus « a placer »", champ(292, "a_placer"), 0)

remplir()
code, _ = appel(pl.deplacer_entry, COH2, 574, body={"apres_id": 520})
verifier("placer juste apres l'en-cours : accepte", code, 200)
ids, _ = ordre(COH2)
verifier("… Maitre Coq suit XEROX", ids[ids.index(520) + 1], 574)

remplir()
code, _ = appel(pl.deplacer_entry, COH2, 574, body={"apres_id": 551})
verifier("placer au milieu de l'historique : refuse", code, 400)
verifier("… rien n'a bouge", ordre(COH2)[0], ids_de(COHESIO2))

code, _ = appel(pl.deplacer_entry, COH2, 520, body={"en_tete": True})
verifier("deplacer le dossier en cours : refuse", code, 400)
code, _ = appel(pl.deplacer_entry, COH2, 556, body={"en_tete": True})
verifier("deplacer un termine : refuse", code, 400)
code, _ = appel(pl.deplacer_entry, COH2, 574, body={})
verifier("ni en_tete ni apres_id : refuse", code, 400)


# ── 3. Inserer apres ──────────────────────────────────────────────────────
print("\n3. Inserer apres")

remplir()
code, rep = appel(pl.insert_after, COH2, 520, body={"reference": "Marché 745 - Reliquat 3", "duree_heures": 4})
verifier("inserer juste apres le dossier en cours : accepte", code, 200)
ids, pos = ordre(COH2)
nouveau = ids[ids.index(520) + 1]
vrai("… le nouveau dossier suit XEROX", nouveau not in ids_de(COHESIO2))
verifier("… il n'est pas « a placer » par defaut", champ(nouveau, "a_placer"), 0)
verifier("… positions contigues", pos, list(range(1, len(ids) + 1)))

remplir()
code, _ = appel(pl.insert_after, COH2, 900, body={"reference": "X", "duree_heures": 4})
verifier("inserer apres un dossier en attente suivi de l'en-cours : accepte", code, 200)

remplir()
code, _ = appel(pl.insert_after, COH2, 566, body={"reference": "X", "duree_heures": 4})
verifier("inserer apres le dernier dossier produit : accepte", code, 200)

remplir()
code, _ = appel(pl.insert_after, COH2, 551, body={"reference": "X", "duree_heures": 4})
verifier("inserer au milieu de l'historique : refuse", code, 400)
verifier("… rien n'a ete cree", ordre(COH2)[0], ids_de(COHESIO2))


# ── 4. Changer de machine ─────────────────────────────────────────────────
print("\n4. Changer de machine")

remplir()
JOURNAL.clear()
code, rep = appel(pl.changer_machine_entry, COH1, 575, body={"machine_cible": COH2, "apres_id": 520})
verifier("Reliquat 4 de Cohesio 1 vers Cohesio 2, apres XEROX : accepte", code, 200)
verifier("… meme id", champ(575, "machine_id"), COH2)
ids2, pos2 = ordre(COH2)
ids1, pos1 = ordre(COH1)
verifier("… place juste apres l'en-cours", ids2[ids2.index(520) + 1], 575)
verifier("… Cohesio 2 : positions contigues", pos2, list(range(1, len(ids2) + 1)))
verifier("… Cohesio 1 : il n'y est plus, positions recompactees", (ids1, pos1), ([700, 701, 702], [1, 2, 3]))
verifier("… creneau remis a zero", champ(575, "planned_start"), None)
verifier("… un seul evenement au journal", len(JOURNAL), 1)
vrai("… le journal dit d'ou et vers ou", "Cohésio 1 → Cohésio 2" in JOURNAL[-1]["objet"])

remplir()
code, _ = appel(pl.changer_machine_entry, COH1, 575, body={"machine_cible": COH2, "en_tete": True})
verifier("vers Cohesio 2 en tete de production : accepte", code, 200)
verifier("… premier apres l'historique", ordre(COH2)[0][3], 575)

remplir()
code, _ = appel(pl.changer_machine_entry, COH1, 575, body={"machine_cible": COH2})
verifier("sans place precise : fin de liste", (code, ordre(COH2)[0][-1]), (200, 575))

remplir()
code, _ = appel(pl.changer_machine_entry, COH1, 575, body={"machine_cible": COH2, "apres_id": 551})
verifier("place refusee sur la machine cible : 400", code, 400)
verifier("… LE DOSSIER EST TOUJOURS SUR COHESIO 1", (champ(575, "machine_id"), ordre(COH1)[0]),
         (COH1, ids_de(COHESIO1)))

code, _ = appel(pl.changer_machine_entry, COH1, 701, body={"machine_cible": COH2, "en_tete": True})
verifier("changer de machine un dossier en cours : refuse", code, 400)
code, _ = appel(pl.changer_machine_entry, COH1, 575, body={"machine_cible": COH1})
verifier("machine cible = machine source : refuse", code, 400)

# Refus APRES ecriture (garde transport, gel non confirme) : la transaction
# doit s'annuler en entier, les deux machines comprises.
remplir()
_garde = pl._garde_transport_apres_ecriture
calls = {"n": 0}


def _garde_qui_refuse(conn, machine_id, avant, request=None, body=None):
    calls["n"] += 1
    if machine_id == COH2:
        raise HTTPException(409, "Enlevement compromis.")
    return []


pl._garde_transport_apres_ecriture = _garde_qui_refuse
code, _ = appel(pl.changer_machine_entry, COH1, 575, body={"machine_cible": COH2, "en_tete": True})
pl._garde_transport_apres_ecriture = _garde
verifier("refus transport sur la cible : 409", code, 409)
verifier("… rien n'a bouge sur Cohesio 1", ordre(COH1)[0], ids_de(COHESIO1))
verifier("… rien n'a bouge sur Cohesio 2", ordre(COH2)[0], ids_de(COHESIO2))


# ── 5. L'ecran ────────────────────────────────────────────────────────────
print("\n5. Ecran : fleches, glisser-deposer, bouton « Passer en tete »")

src = (RACINE / "app" / "web" / "planning_page.py").read_text(encoding="utf-8")


def bloc(debut, fin):
    i = src.index(debut)
    return src[i:src.index(fin, i)]


js = (
    bloc("function reorderKeepsLocked(", "function setupTlDD(")
    + bloc("// ── Place d'un dossier dans la file", "async function passerEnTete(")
    + bloc("async function moveEntry(", "// ── Place d'un dossier dans la file")
)
entries = [{"id": eid, "statut": st, "a_placer": ap} for eid, _, st, ap in COHESIO2]
harnais = """
const S={entries:%s};
let _suppressAutoScroll=false, envoye=null, toast=null;
const CAN_EDIT=true, MID=3;
const document={querySelector:()=>null,getElementById:()=>null};
function requestAnimationFrame(f){}
function showToast(m){toast=m;}
function apiErrorMessage(e,f){return f;}
async function load(){}
async function api(p,o){envoye=JSON.parse(o.body).entry_ids;}
%s
const idx=id=>S.entries.findIndex(e=>e.id===id);
(async()=>{
  const out={};
  out.tete=longueurTete();
  out.voisinHautHADDAD=S.entries[attenteVoisine(idx(573),-1)].id;
  out.enTeteSOLUROAD=estEnTete(idx(900));
  out.enTeteMaitreCoq=estEnTete(idx(574));
  await moveEntry(573,-1); out.monterHADDAD=envoye;
  envoye=null; toast=null; await moveEntry(900,-1); out.monterPremier=[envoye,toast];
  envoye=null; await moveEntry(900,+1); out.descendreSOLUROAD=envoye;
  const ids=S.entries.map(e=>e.id); const [m]=ids.splice(idx(574),1); ids.splice(ids.indexOf(520)+1,0,m);
  out.deposerSurEnCours=reorderKeepsLocked(S.entries.map(e=>e.id),ids);
  console.log(JSON.stringify(out));
})();
""" % (json.dumps(entries), js)

with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(harnais)
    chemin_js = f.name
r = subprocess.run(["node", chemin_js], capture_output=True, text=True)
if r.returncode != 0:
    FAIL.append("execution JS : " + r.stderr[:300])
    print("  ECHEC  execution JS —", r.stderr.strip()[:300])
else:
    out = json.loads(r.stdout.strip().splitlines()[-1])
    verifier("tete d'historique vue par l'ecran", out["tete"], 3)
    verifier("monter HADDAD : son voisin est GLS, pas KIABI termine", out["voisinHautHADDAD"], 543)
    verifier("SOLUROAD est deja le prochain dossier", out["enTeteSOLUROAD"], True)
    verifier("Maitre Coq ne l'est pas", out["enTeteMaitreCoq"], False)
    verifier(
        "fleche haut sur HADDAD : passe au-dessus de KIABI termine au lieu de s'arreter",
        out["monterHADDAD"],
        [551, 552, 566, 900, 520, 517, 466, 43, 541, 557, 292, 573, 543, 556, 571, 574],
    )
    verifier("fleche haut sur le premier dossier : rien envoye, message",
             out["monterPremier"], [None, "Déjà le prochain dossier à produire."])
    verifier(
        "fleche bas sur SOLUROAD : passe sous l'en-cours, derriere STI",
        out["descendreSOLUROAD"],
        [551, 552, 566, 520, 517, 900, 466, 43, 541, 557, 292, 543, 556, 573, 571, 574],
    )
    verifier("deposer Maitre Coq sur l'en-cours : accepte", out["deposerSurEnCours"], True)

vrai("le bouton « Passer en tete » est rendu", "passerEnTete(${e.id})" in src)
vrai("changer de machine passe par l'endpoint atomique", "/changer-machine`" in src)
vrai("plus aucune suppression dans confirmSwitch",
     "method:\"DELETE\"" not in bloc("async function confirmSwitch(", "// ── Modals ──"))

try:
    DB_FILE.unlink()
except OSError:
    pass

print()
if FAIL:
    print(f"{len(FAIL)} echec(s)")
    sys.exit(1)
print("Tous les cas passent.")
