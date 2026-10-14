"""Export des écritures comptables au format FEC (art. A47 A-1 du LPF).

Journaux produits, sur une période (date de pièce / de règlement) :
- ventes : facture → débit client TTC ; crédit ventes HT (par compte de
  famille) ; crédit TVA collectée (par taux). Avoir : sens inverse.
- achats : facture fournisseur → débit achats HT, débit TVA déductible,
  crédit fournisseur TTC.
- banque : encaissement → débit banque, crédit client ; paiement → débit
  fournisseur, crédit banque.

Chaque écriture est équilibrée au centime (test : tests/test_gc_export.py).
La remise de pied se répartit sur les comptes d'un même taux au prorata, le
dernier compte absorbant l'arrondi — le total HT par taux reste celui de la
facture.
"""
from __future__ import annotations

from app.services.gc import calculs

COLONNES = ["JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum", "CompteLib",
            "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
            "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise"]


def reglages(conn) -> dict:
    return {r["cle"]: r["valeur"] for r in conn.execute("SELECT cle, valeur FROM gc_compta_reglages").fetchall()}


def _d(s: str | None) -> str:
    return (s or "")[:10].replace("-", "")


def _ecriture(journal, num, date, piece_ref, piece_date, lib, valid, lignes):
    """lignes : (compte, compte_lib, aux, aux_lib, debit_cents, credit_cents)."""
    out = []
    for compte, clib, aux, alib, deb, cre in lignes:
        if not deb and not cre:
            continue
        out.append({"JournalCode": journal[0], "JournalLib": journal[1], "EcritureNum": num, "EcritureDate": _d(date),
                    "CompteNum": compte, "CompteLib": clib, "CompAuxNum": aux, "CompAuxLib": alib,
                    "PieceRef": piece_ref, "PieceDate": _d(piece_date), "EcritureLib": lib,
                    "debit_cents": int(deb), "credit_cents": int(cre), "EcritureLet": "", "DateLet": "",
                    "ValidDate": _d(valid), "Montantdevise": "", "Idevise": ""})
    return out


def _ventilation(conn, piece) -> tuple[list[tuple[str, int, int]], dict]:
    """[(compte_produit_ou_charge, taux_bp, ht_net)], totaux — remise de pied répartie."""
    sens = "compte_vente" if piece["type"] in ("facture", "avoir") else "compte_achat"
    defaut_cle = "compte_vente_defaut" if sens == "compte_vente" else "compte_achat_defaut"
    defaut = reglages(conn).get(defaut_cle, "")
    lignes = conn.execute(
        f"""SELECT l.montant_ht_cents, l.taux_tva_bp, COALESCE(NULLIF(f.{sens}, ''), ?) AS compte
            FROM gc_pieces_lignes l JOIN gc_articles a ON a.id=l.article_id
            LEFT JOIN gc_familles f ON f.code=a.famille
            WHERE l.piece_id=?""", (defaut, piece["id"])).fetchall()
    esc = piece["escompte_bp"] if "escompte_bp" in piece.keys() else 0
    tot = calculs.totaux([dict(l) for l in lignes], piece["remise_bp"], esc or 0)
    par = {}
    for l in lignes:
        k = (l["compte"], int(l["taux_tva_bp"]))
        par[k] = par.get(k, 0) + int(l["montant_ht_cents"])
    out = []
    for b in tot["bases"]:
        comptes = sorted((k for k in par if k[1] == b["taux_bp"]), key=lambda k: k[0])
        reste = b["ht"]
        for i, k in enumerate(comptes):
            v = reste if i == len(comptes) - 1 else (calculs.div_arrondi(par[k] * b["ht"], b["ht_brut"]) if b["ht_brut"] else 0)
            out.append((k[0], k[1], v))
            reste -= v
    return out, tot


def ecritures(conn, debut: str, fin: str) -> list[dict]:
    R = reglages(conn)
    jv = (R.get("journal_ventes", "VT"), "Ventes")
    ja = (R.get("journal_achats", "AC"), "Achats")
    jb = (R.get("journal_banque", "BQ"), "Banque")
    tva = {r["code"]: r for r in conn.execute("SELECT * FROM gc_tva").fetchall()}
    taux_compte = {}
    for r in tva.values():
        taux_compte.setdefault(int(r["taux_bp"]), (r["compte_collecte"], r["compte_deductible"]))
    out = []
    n = 0

    for p in conn.execute(
        """SELECT p.*, t.raison_sociale, t.code AS tiers_code, t.compte_auxiliaire FROM gc_pieces p
           JOIN gc_tiers t ON t.id=p.tiers_id
           WHERE p.type IN ('facture','avoir','facture_fournisseur') AND p.numero IS NOT NULL AND p.statut!='annule'
             AND substr(p.date_piece,1,10) BETWEEN ? AND ? ORDER BY p.date_piece, p.id""", (debut, fin)).fetchall():
        n += 1
        vente = p["type"] in ("facture", "avoir")
        signe = -1 if p["type"] == "avoir" else 1
        aux = p["compte_auxiliaire"] or p["tiers_code"]
        vent, tot = _ventilation(conn, p)
        lib = f"{'Avoir' if p['type'] == 'avoir' else 'Facture'} {p['numero']} {p['raison_sociale']}"[:100]
        lignes = []
        if vente:
            tiers_l = (R.get("compte_clients", ""), "Clients", aux, p["raison_sociale"], tot["ttc"], 0)
            prod = [(c, "Ventes", "", "", 0, v) for c, _, v in vent]
            taxe = [(taux_compte.get(b["taux_bp"], ("", ""))[0], f"TVA collectée {b['taux_bp'] / 100:g} %", "", "", 0, b["tva"])
                    for b in tot["bases"] if b["tva"]]
            lignes = [tiers_l] + prod + taxe
        else:
            tiers_l = (R.get("compte_fournisseurs", ""), "Fournisseurs", aux, p["raison_sociale"], 0, tot["ttc"])
            charge = [(c, "Achats", "", "", v, 0) for c, _, v in vent]
            taxe = [(taux_compte.get(b["taux_bp"], ("", ""))[1], f"TVA déductible {b['taux_bp'] / 100:g} %", "", "", b["tva"], 0)
                    for b in tot["bases"] if b["tva"]]
            lignes = charge + taxe + [tiers_l]
        if signe < 0:   # avoir : on inverse débit et crédit
            lignes = [(c, cl, a, al, cr, db) for c, cl, a, al, db, cr in lignes]
        out += _ecriture(jv if vente else ja, f"{(jv if vente else ja)[0]}{n:06d}", p["date_piece"], p["numero"],
                         p["date_piece"], lib, p["valide_le"], lignes)

    for r in conn.execute(
        """SELECT r.*, t.raison_sociale, t.code AS tiers_code, t.compte_auxiliaire FROM gc_reglements r
           JOIN gc_tiers t ON t.id=r.tiers_id
           WHERE substr(r.date_reglement,1,10) BETWEEN ? AND ? ORDER BY r.date_reglement, r.id""", (debut, fin)).fetchall():
        n += 1
        aux = r["compte_auxiliaire"] or r["tiers_code"]
        m = int(r["montant_cents"])
        # Banque du règlement : son compte et son journal, sinon les réglages généraux.
        bq = conn.execute("SELECT compte, journal FROM gc_banques WHERE code=?", (r["banque"],)).fetchone() \
            if "banque" in r.keys() and r["banque"] else None
        compte_bq = (bq["compte"] if bq and bq["compte"] else R.get("compte_banque", ""))
        jbr = ((bq["journal"], "Banque") if bq and bq["journal"] else jb)
        lib = f"Règlement {r['raison_sociale']} {r['reference'] or ''}".strip()[:100]
        if r["sens"] == "encaissement":
            lignes = [(compte_bq, "Banque", "", "", m, 0),
                      (R.get("compte_clients", ""), "Clients", aux, r["raison_sociale"], 0, m)]
        else:
            lignes = [(R.get("compte_fournisseurs", ""), "Fournisseurs", aux, r["raison_sociale"], m, 0),
                      (compte_bq, "Banque", "", "", 0, m)]
        out += _ecriture(jbr, f"{jbr[0]}{n:06d}", r["date_reglement"], r["reference"] or f"REG{r['id']}",
                         r["date_reglement"], lib, r["cree_le"], lignes)
    return out


def _montant(c: int) -> str:
    return f"{int(c) / 100:.2f}".replace(".", ",")


def fec(lignes: list[dict]) -> str:
    """Texte FEC : séparateur tabulation, montants à virgule, dates AAAAMMJJ."""
    rows = ["\t".join(COLONNES)]
    for l in lignes:
        v = dict(l, Debit=_montant(l["debit_cents"]), Credit=_montant(l["credit_cents"]))
        rows.append("\t".join(str(v.get(c, "")).replace("\t", " ").replace("\n", " ") for c in COLONNES))
    return "\r\n".join(rows) + "\r\n"


def controles(lignes: list[dict]) -> list[str]:
    """Écritures déséquilibrées et comptes vides : à corriger avant export."""
    pb = []
    par = {}
    for l in lignes:
        par.setdefault(l["EcritureNum"], [0, 0, l["PieceRef"]])
        par[l["EcritureNum"]][0] += l["debit_cents"]
        par[l["EcritureNum"]][1] += l["credit_cents"]
        if not l["CompteNum"]:
            pb.append(f"{l['PieceRef']} : compte manquant ({l['CompteLib']}) — Paramètres › Comptabilité.")
    for num, (d, c, ref) in par.items():
        if d != c:
            pb.append(f"{ref} : écriture {num} déséquilibrée ({_montant(d)} / {_montant(c)}).")
    return sorted(set(pb))
