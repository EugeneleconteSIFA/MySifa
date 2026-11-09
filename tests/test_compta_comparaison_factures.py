# -*- coding: utf-8 -*-
"""Comparaison factures RVGI / grand-livre CW (app/services/compta_comparaison_factures.py).

Ce que ce test protège :

1. **Le rapprochement HT / TTC.** RVGI donne le HT, CW le TTC : une facture
   est concordante pour un taux légal (20 %, 0 %…), pas seulement à égalité.
2. **Chaque écart a son statut et sa piste** : montant (escompte, montant
   rond, signe inversé), date, numéro voisin, absente d'un côté, TVA isolée.
3. **La lecture de l'analyse des ventes RVGI** : la quantité et le HT, qui
   portent tous deux des espaces de milliers, sont séparés sans ambiguïté.

Données synthétiques : les PDF réels contiennent des données clients.
"""
import sys

sys.path.insert(0, ".")

from app.services import compta_comparaison_factures as c


def _rv(*f):
    return {"factures": [{"numero": n, "date": d, "client": "CLIENT", "ht": ht} for n, d, ht in f],
            "total_ht": None}


def _cw(*f):
    return {"factures": [{"numero": n, "date": d, "compte": "CCLIENT", "client": "CLIENT",
                          "ttc": ttc, "libelle": ""} for n, d, ttc in f]}


def _par_numero(res):
    return {l["numero"]: l for l in res["lignes"]}


def test_concordance_tva_20_et_0():
    res = c.comparer(_rv(("1", "2026-10-01", 2020.00), ("2", "2026-10-01", 3030.60)),
                     _cw(("1", "2026-10-01", 2424.00), ("2", "2026-10-01", 3030.60)))
    l = _par_numero(res)
    assert l["1"]["statut"] == "ok" and l["1"]["taux"] == 20.0
    assert l["2"]["statut"] == "ok" and l["2"]["taux"] == 0.0


def test_totaux_ttc_comparables():
    # Le total HT RVGI ne se compare pas au TTC CW : on compare le TTC RVGI
    # calculé (HT + TVA reconnue) au TTC CW, et l'écart vaut la somme des écarts.
    res = c.comparer(_rv(("1", "2026-10-01", 2020.00), ("2", "2026-10-02", 556.79),
                         ("3", "2026-10-03", 100.00)),
                     _cw(("1", "2026-10-01", 2424.00), ("2", "2026-10-02", 654.78)))
    assert res["total_ttc_rvgi"] == round(2424.00 + 668.15 + 120.00, 2)
    assert res["ecart_ttc"] == round(2424.00 + 654.78 - res["total_ttc_rvgi"], 2)
    assert res["nb_taux_supposes"] == 2


def test_escompte_et_montant_rond():
    res = c.comparer(_rv(("1", "2026-10-02", 556.79), ("2", "2026-10-22", 731.49)),
                     _cw(("1", "2026-10-02", 654.78), ("2", "2026-10-22", 411.49)))
    l = _par_numero(res)
    assert l["1"]["statut"] == "montant" and "2 %" in l["1"]["piste"]
    assert l["2"]["statut"] == "montant" and "montant rond" in l["2"]["piste"]


def test_signe_inverse():
    res = c.comparer(_rv(("1", "2026-10-06", 10.0)), _cw(("1", "2026-10-06", -12.0)))
    assert "signe opposé" in res["lignes"][0]["piste"]


def test_date_numero_et_absentes():
    res = c.comparer(
        _rv(("10", "2026-10-22", 996.0), ("26100500", "2026-10-05", 100.0), ("26100501", "2026-10-05", 50.0)),
        _cw(("10", "2026-10-21", 1195.20), ("26100005", "2026-10-05", 120.0), ("99", "2026-10-07", 5.0)),
    )
    l = _par_numero(res)
    assert l["10"]["statut"] == "date"
    assert l["26100500"]["statut"] == "numero" and l["26100500"]["numero_cw"] == "26100005"
    assert l["26100501"]["statut"] == "rvgi_seul"
    assert l["99"]["statut"] == "cw_seul"
    assert res["compte"]["ok"] == 0


def test_tva_isolee_dans_un_compte():
    rv = _rv(*[(str(i), "2026-10-01", 100.0) for i in range(4)])
    cw = _cw(*[(str(i), "2026-10-01", 120.0) for i in range(3)], ("3", "2026-10-01", 100.0))
    l = _par_numero(c.comparer(rv, cw))
    assert l["3"]["statut"] == "tva"
    assert all(l[str(i)]["statut"] == "ok" for i in range(3))


def test_lecture_rvgi():
    page = "\n".join([
        "Analyse des ventes par client 05/11/2026",
        "Du 01/10/2026 au 31/10/2026",
        "Client No pièce Date Quantité Total HT N",
        "95 - BOULANGER",
        "26100143 28/10/2026 278 000,00 4 787,16",
        "26100019 08/10/2026 -1 000,00 -6 059,20",
        "Total BOULANGER : 277 000,00 -1 272,04",
        "Total HT Net : -1 272,04",
    ])
    origine = c._texte_pdf
    c._texte_pdf = lambda data: [page]
    try:
        r = c.lire_rvgi(b"")
    finally:
        c._texte_pdf = origine
    assert r["periode"] == ("2026-10-01", "2026-10-31")
    assert r["total_ht"] == -1272.04
    assert [(f["numero"], f["date"], f["client"], f["ht"]) for f in r["factures"]] == [
        ("26100143", "2026-10-28", "BOULANGER", 4787.16),
        ("26100019", "2026-10-08", "BOULANGER", -6059.20),
    ]


def test_bilan_des_corrections():
    # v1 : 3 écarts (montant, absente de CW, écriture CW sans facture).
    rv1 = _rv(("1", "2026-10-01", 100.0), ("2", "2026-10-02", 50.0), ("3", "2026-10-03", 10.0))
    cw1 = _cw(("1", "2026-10-01", 115.0), ("3", "2026-10-03", 12.0), ("99", "2026-10-09", 5.0))
    v1 = c.comparer(rv1, cw1)
    # v2 (grand-livre corrigé) : 1 corrigé, 99 retirée, 2 toujours absente,
    # et une erreur nouvelle sur la 3.
    cw2 = _cw(("1", "2026-10-01", 120.0), ("3", "2026-10-03", 13.0))
    v2 = c.comparer(rv1, cw2)
    n = c.bilan(v1, v2)
    l = {x["cle"]: x for x in v2["lignes"]}
    assert l["1|2026-10-01"]["evolution"] == "corrige"
    assert l["99|2026-10-09"]["statut"] == "retire" and l["99|2026-10-09"]["evolution"] == "corrige"
    assert l["2|2026-10-02"]["evolution"] == "restant"
    assert l["3|2026-10-03"]["evolution"] == "nouveau"
    assert n == {"corriges": 2, "restants": 1, "nouveaux": 1}


def test_justification_tient_tant_que_les_montants():
    res = c.comparer(_rv(("1", "2026-10-02", 556.79)), _cw(("1", "2026-10-02", 654.78)))
    ligne = res["lignes"][0]
    justifs = {ligne["cle"]: {"signature": c.signature(ligne), "commentaire": "Escompte voulu",
                              "par": "X", "le": "2026-11-10T09:00:00"}}
    assert c.appliquer_justifications(res, justifs) == 0
    assert res["lignes"][0]["justif"]["commentaire"] == "Escompte voulu"
    assert c.compter_a_traiter(c.ecarts_compacts(res), justifs) == 0
    # Montant CW modifié : la justification ne vaut plus.
    res2 = c.comparer(_rv(("1", "2026-10-02", 556.79)), _cw(("1", "2026-10-02", 650.00)))
    assert c.appliquer_justifications(res2, justifs) == 1
    assert res2["lignes"][0]["justif_caduque"] == "Escompte voulu"


if __name__ == "__main__":
    # La CI lance `python tests/test_x.py`, sans pytest.
    tests = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for t in tests:
        t()
    print(f"test_compta_comparaison_factures : OK ({len(tests)} cas)")
