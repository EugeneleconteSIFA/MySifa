"""
Besoins matieres, vue Tendance : selection de references et detail par laize.

Vingt matieres sur dix-huit mois font vingt courbes et six cartes. C'est
lisible pour surveiller l'ensemble, inutilisable pour preparer UNE commande —
et une bobine ne se commande jamais hors de sa laize : un besoin de frontal
agrege toutes laizes confondues est juste en metres et inutilisable pour
passer commande.

Ce que ces cas verrouillent :

  - la laize voyage avec le besoin, arrondie au millimetre entier (76 et 76.0
    designent la meme bobine ; deux cles scinderaient la courbe en deux
    moities qui ne veulent rien dire) ;
  - l'eclatement par laize d'une cle d'agregat SOMME exactement son total. La
    photo quotidienne du carnet n'ecrit que ce total : si les deux divergent,
    l'ecran et la serie de calibration ne racontent plus la meme chose ;
  - la selection restreint ce qui est RENDU, jamais ce qui est calcule, et le
    catalogue renvoye a cote reste complet — sinon l'ecran ne saurait plus
    proposer ce qu'on vient de deselectionner ;
  - une entree illisible (`refs=zzz`) ne fait pas tomber l'ecran a 500.

Lancer : python3 tests/test_besoins_tendance_laize.py
"""
import sys

sys.path.insert(0, ".")
import database  # noqa: F401  — le shim d'abord, toujours (voir CLAUDE.md)

from app.services.carnet_snapshot import laize_mm
import app.routers.besoins_matieres as bm

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


print("\n1. La laize d'un besoin, en millimetres entiers")
check("un entier reste entier", laize_mm({"laize_mm": 102}), 102)
check("un flottant s'arrondit", laize_mm({"laize_mm": 76.4}), 76)
check("une chaine est lue", laize_mm({"laize_mm": "102"}), 102)
check("zero n'est pas une laize", laize_mm({"laize_mm": 0}), None)
check("absente vaut None", laize_mm({}), None)
check("illisible vaut None", laize_mm({"laize_mm": "n/a"}), None)


print("\n2. La laize voyage avec le besoin, pas seulement avec le dossier")
pe = {
    "id": 1, "statut": "attente", "qte_etiquettes": 100000,
    "ft_support": "PP BLANC", "ft_glassine": "GLASSINE 60",
    "of_laize": 102.0, "of_metrage": 5000,
    "ft_mandrin_dia": "76", "ft_etiq_par_bobine": 1000,
}
besoins = {b["kind"]: b for b in bm._compute_besoins_dossier(pe, {}, 10.0)}
check("le frontal porte sa laize", laize_mm(besoins["support"]), 102)
check("la glassine aussi", laize_mm(besoins["glassine"]), 102)
# Un mandrin se compte en unites : lui coller une laize melangerait deux
# grandeurs dans la meme colonne.
check("le mandrin n'en a pas", laize_mm(besoins["mandrin"]), None)


print("\n3. L'eclatement par laize somme exactement le total")
# On rejoue a la main ce que fait `agreger` : deux dossiers, deux laizes, une
# seule cle (mois, matiere, nature). Le total de la cle doit valoir la somme
# de ses laizes — c'est ce total, et lui seul, que la photo quotidienne ecrit.
agg = {"q": 0.0, "laizes": {}}
for laize, quantite in ((102, 5000.0), (76, 3000.0), (102, 1200.0)):
    sub = agg["laizes"].setdefault(laize, {"q": 0.0, "ids": set()})
    sub["q"] += quantite
    agg["q"] += quantite
check("deux laizes distinctes", sorted(agg["laizes"]), [76, 102])
check("la meme laize se cumule", agg["laizes"][102]["q"], 6200.0)
check("la somme des laizes EST le total",
      round(sum(v["q"] for v in agg["laizes"].values()), 3), round(agg["q"], 3))


print("\n4. L'ecran repond, quelle que soit la selection")
bm.require_stock_matieres_admin = lambda r: {"id": 1, "nom": "test"}


class _Req:
    def __init__(self, qp):
        self.query_params = qp


cas = [
    ("aucune selection", {}, {"refs": [], "laizes": [], "detail": ""}),
    ("detail par laize", {"detail": "laize"}, {"refs": [], "laizes": [], "detail": "laize"}),
    ("references et laizes", {"refs": "12,na", "laizes": "76, 102"},
     {"refs": ["12", "na"], "laizes": [76, 102], "detail": ""}),
    # Un signet bricole a la main ne doit pas rendre l'ecran inaccessible :
    # une reference illisible est ignoree, pas fatale.
    ("saisie illisible ignoree", {"refs": "zzz", "laizes": "abc"},
     {"refs": [], "laizes": [], "detail": ""}),
]
for libelle, qp, attendu in cas:
    d = bm.besoins_tendance(_Req(qp))
    check(libelle, d["selection"], attendu)
    check(f"  {libelle} : le catalogue accompagne la reponse",
          isinstance(d.get("references"), list), True)

# Le catalogue ne retrecit pas avec la selection : c'est lui qui peuple le
# selecteur, et une liste filtree rendrait la deselection impossible.
tout = bm.besoins_tendance(_Req({}))
filtre = bm.besoins_tendance(_Req({"refs": "999999"}))
check("le catalogue survit au filtre",
      len(filtre["references"]), len(tout["references"]))
check("mais plus aucune ligne ne passe", filtre["lignes"], [])


print("\n5. Un carnet pour de vrai : deux laizes d'une meme matiere")
# La base de developpement est vide : on injecte l'agregat directement, la ou
# `agreger` le produirait. C'est le contrat entre le service et l'ecran qu'on
# verrouille ici, pas le calcul du besoin — teste ailleurs.
import json
from datetime import date

_auj = date.today()
_mois = f"{_auj.year:04d}-{_auj.month:02d}"


def _faux_agregat(*a, **k):
    cumul = {
        (_mois, 7, "support"): {
            "q": 8000.0, "q_actif": 8000.0, "unite": "ml", "inc": 0,
            "ref": "PP90", "designation": "PP blanc 90", "source_value": "PP BLANC",
            "laizes": {
                102: {"q": 5000.0, "q_actif": 5000.0, "inc": 0, "ids": {1, 2}},
                76: {"q": 3000.0, "q_actif": 3000.0, "inc": 0, "ids": {2}},
            },
        },
    }
    vus = {(_mois, 7, "support"): {1, 2}}
    return cumul, vus, dict(vus), []


_vrai = bm.agreger_carnet
bm.agreger_carnet = _faux_agregat
try:
    plein = bm.besoins_tendance(_Req({}))
    detail = bm.besoins_tendance(_Req({"detail": "laize"}))
    une = bm.besoins_tendance(_Req({"laizes": "102", "detail": "laize"}))

    check("sans detail : une seule ligne", len(plein["lignes"]), 1)
    check("qui porte le total des deux laizes", plein["lignes"][0]["total"], 8000.0)
    # Deux laizes demandees par le meme dossier ne font pas deux dossiers.
    _cell = [p for p in plein["lignes"][0]["serie"] if p["mois"] == _mois][0]
    check("les dossiers ne sont pas comptes deux fois", _cell["dossiers"], 2)

    check("avec detail : une ligne par laize", len(detail["lignes"]), 2)
    check("chacune nommee par sa laize",
          sorted(l["libelle"] for l in detail["lignes"]),
          ["PP90 · 102 mm", "PP90 · 76 mm"])
    check("la somme des lignes est conservee",
          sum(l["total"] for l in detail["lignes"]), 8000.0)

    check("filtrer une laize ne garde qu'elle", len(une["lignes"]), 1)
    check("et son seul volume", une["lignes"][0]["total"], 5000.0)
    check("le catalogue annonce les deux laizes",
          sorted(next(r["laizes"] for r in une["references"] if r["matiere_id"] == 7)),
          [76, 102])

    # Les identifiants de dossiers servent au decompte, jamais a la reponse :
    # un `set` dans le JSON ferait tomber l'ecran a 500.
    check("la reponse reste serialisable", isinstance(json.dumps(detail), str), True)
    check("aucun ensemble d'identifiants ne fuit",
          "_ids" in json.dumps(detail), False)
finally:
    bm.agreger_carnet = _vrai



print("\n6. L'ecran : on choisit d'abord, on trace ensuite")
# Quarante-deux references sur dix-huit mois, deux laizes chacune : tout
# tracer d'entree donne un mur de courbes que personne ne lit. L'ecran attend
# donc qu'on lui dise ce qu'on est en train d'acheter.
_js = open("app/web/stock_page.py", encoding="utf-8").read()

check("le detail par laize n'est plus une option",
      "S.besoinsTendDetail" in _js, False)
check("il est toujours demande au serveur",
      "p.set('detail', 'laize');" in _js, True)
check("le panneau s'ouvre a l'arrivee",
      "if (S.besoinsTendSelOpen == null) S.besoinsTendSelOpen = true;" in _js, True)
check("sans reference, aucune courbe",
      "if (!st.besoinsTendRefs.length) {" in _js, True)
check("et l'ecran dit quoi faire",
      "Choisissez une ou plusieurs références ci-dessus" in _js, True)
# Les laizes ne se proposent qu'une fois la matiere connue, et seulement si
# elle est en bobine : un mandrin n'a pas de laize.
check("les laizes viennent des seules references retenues",
      "const retenues = cat.filter(r => sel.has(r.cle));" in _js, True)
check("aucune laize proposee tant que rien n'est choisi",
      "? [...new Set(retenues.flatMap(r => r.laizes || []))].sort((a, b) => a - b)"
      in _js, True)
check("une laize orpheline est oubliee",
      "function _besTendNettoyerLaizes()" in _js, True)

# Le pave d'explication est retire : trois paragraphes au-dessus d'un ecran
# consulte chaque jour ouvre finissent par ne plus etre lus, et poussaient les
# courbes sous la ligne de flottaison.
# La chaine RENDUE, pas la phrase : le commentaire qui explique le retrait a
# parfaitement le droit de nommer ce qu'il retire.
check("plus de pave « Ce que montre cet ecran »",
      "'Ce que montre cet écran : '" in _js, False)
check("plus de style pour ce pave", "bes-tend-note" in _js, False)
# Le retard, lui, survit : ce n'est pas une explication de l'ecran mais une
# anomalie du carnet.
check("le retard reste signale", "bes-tend-retard" in _js, True)
check("et seulement s'il y en a un",
      "if (data.reste_sur_mois_echus > 0) {" in _js, True)


print()
if ko:
    print(f"ECHEC — {ko} verification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
