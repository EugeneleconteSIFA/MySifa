"""
Mise à jour du miroir RVGI à la demande (app/services/erp_synchro.py).

Le VPS ne voit pas RVGI : le bouton dépose une demande, le poste SIFA la
relève, l'import du miroir la clôt. Ce test protège le cycle :

1. deux clics rapprochés ne font qu'une demande ;
2. le poste relève la demande une fois, puis plus rien ;
3. la fin de l'import clôt la demande (terminée ou en échec) ;
4. une demande relevée qui n'aboutit pas ne bloque pas les suivantes ;
5. une demande jamais relevée est signalée (poste éteint ?).

Base temporaire : aucune base réelle n'est lue.
"""
import importlib.util
import sqlite3
import sys
from datetime import timedelta

sys.path.insert(0, ".")
from app.services import erp_synchro as es  # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
spec = importlib.util.spec_from_file_location("mig", "app/core/migrations/2026_11_24_erp_synchro_demandes.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
mig.appliquer(conn)
mig.appliquer(conn)                       # rejouable

print("\nDemande")
r1 = es.demander(conn, "ADV Test")
r2 = es.demander(conn, "Autre")
check("première demande créée", r1["nouvelle"], True)
check("deux clics = une demande", (r2["nouvelle"], r2["demande"]["id"]), (False, r1["demande"]["id"]))

print("\nRelève par le poste")
p1 = es.prendre(conn)
p2 = es.prendre(conn)
check("le poste relève la demande", p1 and p1["id"], r1["demande"]["id"])
check("puis plus rien à relever", p2, None)
etat = es.etat(conn, {"present": True, "importe_le": "2026-11-24 10:00:00"}, {"statut": "en cours"})
check("état : prise", etat["demande"]["statut"], "prise")
check("une demande prise reste la demande ouverte", es.demander(conn, "X")["nouvelle"], False)

print("\nFin de l'import")
check("l'import clôt la demande", es.terminer(conn, True), 1)
check("statut terminée", es.etat(conn, {}, {})["demande"]["statut"], "terminee")
check("un import sans demande ne touche à rien", es.terminer(conn, True), 0)
es.demander(conn, "ADV Test")
es.prendre(conn)
es.terminer(conn, False, "Import partiel")
d = es.etat(conn, {}, {})["demande"]
check("échec avec son message", (d["statut"], d["message"]), ("echec", "Import partiel"))

print("\nPoste muet")
r = es.demander(conn, "ADV Test")
es.prendre(conn)
vieux = es._iso(es.maintenant() - es.DELAI_SANS_REPONSE - timedelta(minutes=1))
conn.execute("UPDATE erp_synchro_demandes SET prise_le=? WHERE id=?", (vieux, r["demande"]["id"]))
check("une demande prise sans réponse est dite en échec", es.etat(conn, {}, {})["demande"]["statut"], "echec")
r3 = es.demander(conn, "ADV Test")
check("et une nouvelle demande peut partir", r3["nouvelle"], True)
ancienne = conn.execute("SELECT statut, message FROM erp_synchro_demandes WHERE id=?", (r["demande"]["id"],)).fetchone()
check("l'abandonnée est close dans l'historique", tuple(ancienne), ("echec", "Sans réponse du poste SIFA"))
vieux = es._iso(es.maintenant() - es.DELAI_NON_RELEVEE - timedelta(minutes=1))
conn.execute("UPDATE erp_synchro_demandes SET demande_le=? WHERE id=?", (vieux, r3["demande"]["id"]))
check("une demande jamais relevée est signalée", bool(es.etat(conn, {}, {})["demande"].get("alerte")), True)

print()
if ko:
    print(f"test_erp_synchro : {ko} échec(s)")
    sys.exit(1)
print("test_erp_synchro : OK")
