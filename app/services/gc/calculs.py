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


def totaux(lignes: list[dict], remise_piece_bp: int = 0, escompte_bp: int = 0, acompte_cents: int = 0) -> dict:
    """Totaux d'une pièce, dans l'ordre de RVGI : HT brut → remise → HT net →
    escompte → HT net financier → TVA → TTC → acompte → net à payer.

    `lignes` : dicts avec `montant_ht_cents` et `taux_tva_bp`. Retourne
    {ht, tva, ttc, remise, escompte, acompte, net_a_payer,
     bases: [{taux_bp, ht_brut, remise, escompte, ht, tva}]} où `ht` est le
    HT net financier, base de la TVA.
    """
    par_taux: dict[int, int] = {}
    for l in lignes:
        t = int(l.get("taux_tva_bp") or 0)
        par_taux[t] = par_taux.get(t, 0) + int(l.get("montant_ht_cents") or 0)
    bases = []
    ht = tva = rem = esc = 0
    for t in sorted(par_taux):
        brut = par_taux[t]
        r = div_arrondi(brut * int(remise_piece_bp or 0), 10000)
        net = brut - r
        e = div_arrondi(net * int(escompte_bp or 0), 10000)
        net_f = net - e
        tv = div_arrondi(net_f * t, 10000)
        bases.append({"taux_bp": t, "ht_brut": brut, "remise": r, "escompte": e, "ht": net_f, "tva": tv})
        ht += net_f
        tva += tv
        rem += r
        esc += e
    acompte = int(acompte_cents or 0)
    return {"ht": ht, "tva": tva, "ttc": ht + tva, "remise": rem, "escompte": esc, "acompte": acompte,
            "net_a_payer": ht + tva - acompte, "bases": bases}


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


def conditionnement_bobines(quantite_milli: int, unite: str, laize_dmm: int | None,
                            ml_par_bobine_milli: int | None) -> dict | None:
    """Équivalent en mètres linéaires et en bobines d'une quantité achetée au m².

    56 400 m² en laize 470 mm = 120 000 ML ; en bobines de 12 000 ML = 10 bobines.
    None si l'unité n'est pas le m² ou si la laize manque."""
    if (unite or "").upper() not in ("M2", "M²") or not laize_dmm:
        return None
    ml_milli = div_arrondi(int(quantite_milli) * 10000, int(laize_dmm))   # m² / (laize mm / 1000)
    out = {"ml_milli": ml_milli, "laize_mm": int(laize_dmm) / 10, "bobines": None, "ml_par_bobine_milli": ml_par_bobine_milli}
    if ml_par_bobine_milli:
        out["bobines"] = -(-ml_milli // int(ml_par_bobine_milli))          # arrondi au supérieur
    return out


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
    s = conn.execute("SELECT * FROM gc_sequences WHERE code=?", (code,)).fetchone()
    if not s:
        raise ValueError(f"Aucune séquence de numérotation pour « {code} ».")
    cles = s.keys()
    reinit = s["reinit"] if "reinit" in cles and s["reinit"] else ("annuelle" if int(s["annuel"]) else "jamais")
    mois = int(s["mois"]) if "mois" in cles else 0
    n = int(s["prochain"])
    if reinit == "annuelle" and int(s["annee"]) != d.year:
        n = 1
    elif reinit == "mensuelle" and (int(s["annee"]), mois) != (d.year, d.month):
        n = 1
    if "mois" in cles:
        conn.execute("UPDATE gc_sequences SET prochain=?, annee=?, mois=? WHERE code=?", (n + 1, d.year, d.month, code))
    else:
        conn.execute("UPDATE gc_sequences SET prochain=?, annee=? WHERE code=?", (n + 1, d.year, code))
    return formater_numero(s["format"], n, d)
