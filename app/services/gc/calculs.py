"""Calculs de pièce : montants de ligne, totaux, TVA, échéances, numéros.

Tout est en entiers : centimes, millièmes de quantité, points de base. Une
seule règle d'arrondi, au demi supérieur (en valeur absolue), appliquée :
- au montant HT de chaque ligne ;
- à la remise de pied, par taux de TVA ;
- à la TVA, par taux, sur la base HT nette du taux.

`static/erp/erp_pieces.js` reproduit `montant_ligne` et `totaux` pour
l'affichage pendant la saisie ; le serveur recalcule toujours à
l'enregistrement, c'est son chiffre qui fait foi. Toute modification ici se
reporte là-bas (test : tests/test_gc_calculs.py).
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta


def div_arrondi(num: int, den: int) -> int:
    """Division entière arrondie au demi supérieur, symétrique autour de zéro."""
    if den <= 0:
        raise ValueError("dénominateur nul ou négatif")
    signe = -1 if num < 0 else 1
    n = abs(num)
    return signe * ((2 * n + den) // (2 * den))


def montant_ligne(quantite_milli: int, prix_cents: int, base_prix: int = 1, remise_bp: int = 0) -> int:
    """Montant HT d'une ligne, en centimes.

    quantité (millièmes) × prix (centimes pour `base_prix` unités) × (1 − remise).
    """
    base = max(1, int(base_prix or 1))
    num = int(quantite_milli) * int(prix_cents) * (10000 - int(remise_bp or 0))
    return div_arrondi(num, 1000 * base * 10000)


def totaux(lignes: list[dict], remise_piece_bp: int = 0) -> dict:
    """Totaux d'une pièce.

    `lignes` : dicts avec `montant_ht_cents` et `taux_tva_bp`. Retourne
    {ht, tva, ttc, remise, bases: [{taux_bp, ht_brut, remise, ht, tva}]}.
    """
    par_taux: dict[int, int] = {}
    for l in lignes:
        t = int(l.get("taux_tva_bp") or 0)
        par_taux[t] = par_taux.get(t, 0) + int(l.get("montant_ht_cents") or 0)
    bases = []
    ht = tva = rem = 0
    for t in sorted(par_taux):
        brut = par_taux[t]
        r = div_arrondi(brut * int(remise_piece_bp or 0), 10000)
        net = brut - r
        tv = div_arrondi(net * t, 10000)
        bases.append({"taux_bp": t, "ht_brut": brut, "remise": r, "ht": net, "tva": tv})
        ht += net
        tva += tv
        rem += r
    return {"ht": ht, "tva": tva, "ttc": ht + tva, "remise": rem, "bases": bases}


def date_echeance(d: date, jours: int, fin_de_mois: bool = False, jour_du_mois: int = 0) -> date:
    """Échéance d'une facture datée `d`.

    « 30 jours fin de mois » : date + 30 jours, puis fin de ce mois.
    `jour_du_mois` = N : le N du mois suivant la date obtenue (« le 10 »).
    """
    e = d + timedelta(days=int(jours or 0))
    if fin_de_mois:
        e = e.replace(day=calendar.monthrange(e.year, e.month)[1])
    if jour_du_mois:
        a, m = (e.year + 1, 1) if e.month == 12 else (e.year, e.month + 1)
        e = date(a, m, min(int(jour_du_mois), calendar.monthrange(a, m)[1]))
    return e


_JETON = re.compile(r"\{(AAAA|AA|MM|N(?::(\d+))?)\}")


def formater_numero(fmt: str, n: int, d: date) -> str:
    """'FA{AA}{N:05}' + 12 + 2026-10-14 → 'FA2600012'."""
    def rempl(m: re.Match) -> str:
        j = m.group(1)
        if j == "AAAA":
            return f"{d.year:04d}"
        if j == "AA":
            return f"{d.year % 100:02d}"
        if j == "MM":
            return f"{d.month:02d}"
        largeur = int(m.group(2) or 0)
        return str(n).zfill(largeur)
    return _JETON.sub(rempl, fmt)


def prendre_numero(conn, code: str, d: date) -> str:
    """Attribue le numéro suivant de la séquence `code`, dans la transaction
    de l'appelant. Le compteur repart à 1 au changement d'année si la
    séquence est annuelle. À appeler juste avant le commit : un rollback
    rend le numéro, il n'y a donc jamais de trou."""
    s = conn.execute(
        "SELECT format, prochain, annuel, annee FROM gc_sequences WHERE code=?", (code,)
    ).fetchone()
    if not s:
        raise ValueError(f"Aucune séquence de numérotation pour « {code} ».")
    n = int(s["prochain"])
    if int(s["annuel"]) and int(s["annee"]) != d.year:
        n = 1
    conn.execute(
        "UPDATE gc_sequences SET prochain=?, annee=? WHERE code=?", (n + 1, d.year, code)
    )
    return formater_numero(s["format"], n, d)
