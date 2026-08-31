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
check("sans reference, aucune courbe",
      "if (!st.besoinsTendRefs.length) {" in _js, True)
check("et l'ecran dit quoi faire",
      "Cherchez une matière ci-dessus" in _js, True)
# La grille de cases a cocher est retiree : 42 references sur cinq colonnes,
# quarante lignes a lire pour en cocher deux, et la moitie de l'ecran mangee
# avant la premiere courbe. Un champ de recherche a la place.
check("plus de grille de cases", "bes-tsel-liste" in _js, False)
check("plus de panneau depliable", "bes-tsel-panel" in _js, False)
check("un champ de recherche", "Rechercher une matière…" in _js, True)
check("huit resultats au maximum", ".slice(0, 8);" in _js, True)
# Les regles de searchbar de la maison : Escape vide, les fleches naviguent,
# Entree valide sans soumettre.
check("Echap vide le champ", "if (e.key === 'Escape')" in _js, True)
check("les fleches naviguent",
      "e.key === 'ArrowDown' || e.key === 'ArrowUp'" in _js, True)
check("Entree retient le resultat surligne",
      "if (e.key === 'Enter' && hi >= 0)" in _js, True)
check("un resultat deja retenu ne se propose plus",
      "vus = cat.filter(r => !sel.has(r.cle)" in _js, True)

# Une bobine passe par la modale de laizes ; ce qui n'en est pas entre direct.
check("la modale de laizes existe", "function _besTendModaleLaizes(" in _js, True)
check("elle n'apparait que sur une bobine",
      "if ((ref.laizes || []).length) { _besTendModaleLaizes(ref); return; }" in _js, True)
check("rien n'y est preselectionne d'office",
      "const choisies = new Set((ref.laizes || []).filter(l => dejaSel.has(l)));" in _js, True)
check("mais tout se prend d'un clic", "Toutes les laizes" in _js, True)
check("on ne valide pas sans laize", "valider.disabled = choisies.size === 0;" in _js, True)
check("la pastille rappelle les laizes retenues", "bes-tsel-chip-lz" in _js, True)
check("et laisse les rouvrir", "Changer les laizes de " in _js, True)
check("une laize orpheline est oubliee",
      "function _besTendNettoyerLaizes()" in _js, True)
# Le bouton de validation suit le gabarit des modales de MyStock. `btn-primary`
# n'existe pas dans cette page : il rendait un bouton gris.
check("le bouton de validation est a l'accent",
      "cls: 'btn btn-accent bes-lz-valider'" in _js, True)
check("et sans style, il ne serait pas au gabarit",
      ".bes-lz-valider{" in _js, True)

# Les dernieres references consultees : un acheteur revient sur les memes
# matieres toute la semaine, les retaper chaque matin se paie tous les jours.
check("les recentes sont gardees", "BES_TEND_RECENTS_CLE" in _js, True)
check("six au maximum", "const BES_TEND_RECENTS_MAX = 6;" in _js, True)
check("avec leurs laizes",
      "_besTendPousserRecent(ref, [...choisies].sort((a, b) => a - b));" in _js, True)
check("elles se rejouent d'un clic", "function _besTendRejouerRecent(" in _js, True)
check("sous le champ, et seulement quand il est vide",
      "if (recents.length && !(S.besoinsTendRefQ || '').trim())" in _js, True)
check("une reference deja tracee n'y figure plus",
      "_besTendRecents().filter(r => !sel.has(r.cle))" in _js, True)
# Navigation privee, site data bloque : la rangee disparait, rien d'autre.
check("un stockage refuse ne casse pas la page (lecture)",
      "function _besTendRecents()" in _js and "catch (e) {\n    return [];" in _js, True)
check("ni a l'ecriture",
      "function _besTendPousserRecent(ref, laizes) {\n  try {" in _js, True)

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



print("\n7. Le filtre de laize ne concerne que les bobines")
# Choisir une laize pour le frontal ne doit pas faire disparaitre le mandrin
# qu'on a retenu a cote : il n'a pas de laize, la question ne le concerne pas.
_mois2 = _mois


def _faux_mixte(*a, **k):
    cumul = {
        (_mois2, 7, "support"): {
            "q": 8000.0, "q_actif": 8000.0, "unite": "ml", "inc": 0,
            "ref": "PP90", "designation": None, "source_value": "PP",
            "laizes": {102: {"q": 5000.0, "q_actif": 5000.0, "inc": 0, "ids": {1}},
                       76: {"q": 3000.0, "q_actif": 3000.0, "inc": 0, "ids": {2}}},
        },
        (_mois2, 9, "mandrin"): {
            "q": 400.0, "q_actif": 400.0, "unite": "u", "inc": 0,
            "ref": "MANDRIN 76", "designation": None, "source_value": "76",
            "laizes": {None: {"q": 400.0, "q_actif": 400.0, "inc": 0, "ids": {1}}},
        },
    }
    vus = {(_mois2, 7, "support"): {1, 2}, (_mois2, 9, "mandrin"): {1}}
    return cumul, vus, dict(vus), []


_vrai2 = bm.agreger_carnet
bm.agreger_carnet = _faux_mixte
try:
    d = bm.besoins_tendance(_Req({"refs": "7,9", "laizes": "102", "detail": "laize"}))
    kinds = sorted({l["kind"] for l in d["lignes"]})
    check("le mandrin survit au filtre de laize", kinds, ["mandrin", "support"])
    check("le frontal est reduit a la laize demandee",
          [l["total"] for l in d["lignes"] if l["kind"] == "support"], [5000.0])
    check("le mandrin garde son volume",
          [l["total"] for l in d["lignes"] if l["kind"] == "mandrin"], [400.0])
finally:
    bm.agreger_carnet = _vrai2



print("\n8. La prevision ne couvre que les mois a venir")
# Sur un mois echu le chiffre est connu et deja trace : une prevision
# par-dessus une mesure ne prevoit rien, et l'ecart entre les deux ne se lisait
# que comme un defaut. Retire le 31/08/2026.
from datetime import date as _date

_auj2 = _date.today()


def _mois_glissants(n_passes):
    an, mo = _auj2.year, _auj2.month - n_passes
    an += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    out = []
    for _ in range(n_passes + 7):
        out.append(f"{an:04d}-{mo:02d}")
        mo += 1
        if mo > 12:
            mo, an = 1, an + 1
    return out


_tous = _mois_glissants(14)
_courant = f"{_auj2.year:04d}-{_auj2.month:02d}"
_passes = [m for m in _tous if m < _courant]
# Douze mois mesures, en dents de scie : une moyenne mobile aurait donne des
# valeurs franchement differentes des mesures — c'est ce qu'on ne veut plus.
_par_mois = {m: {"q": 100000.0 if i % 2 else 20000.0} for i, m in enumerate(_passes)}
_doc = set(_passes)

_t = bm._tendance(_par_mois, _tous, _courant, _doc, {})
check("la prevision est calculee", _t is not None, True)
_idx = {m: i for i, m in enumerate(_tous)}
check("aucune valeur sur les mois revolus",
      [v for m, v in zip(_tous, _t["valeurs"]) if m < _courant and v is not None], [])
check("une valeur sur chaque mois a venir",
      all(_t["valeurs"][_idx[m]] is not None for m in _tous if m >= _courant), True)
# Le niveau reste la mediane des six derniers mois mesures : sur une dent de
# scie 20/100, la mediane vaut 60 000 — une moyenne aurait donne pareil ici,
# mais un seul gros marche ferait diverger les deux.
check("le niveau vient des derniers mois mesures", _t["niveau"], 60000.0)
check("il s'appuie sur six mois", _t["recents"], 6)
check("et compte les mois mesures", _t["n"], len(_passes))
# Sous cinq mois mesures, rien : deux ou trois points suffisent a dessiner
# n'importe quelle prevision.
_court = {m: {"q": 1000.0} for m in _passes[-3:]}
check("trop peu de mesures, pas de prevision",
      bm._tendance(_court, _tous, _courant, set(_passes[-3:]), {}), None)

_js2 = open("app/web/stock_page.py", encoding="utf-8").read()
check("l'ecran ne parle plus de courbe lissee",
      "la courbe lissée sur 3 mois" in _js2, False)
check("il annonce une prevision", "Masquer la prévision" in _js2, True)


print()
if ko:
    print(f"ECHEC — {ko} verification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
