"""Nouvel ERP — document imprimable d'une pièce (A4, « Imprimer › PDF »).

Une page HTML autonome, en noir sur blanc quel que soit le thème : c'est un
document qui part chez le client. Les mentions viennent de la base (société,
taux de TVA, conditions), jamais du code.

Mentions d'une facture (art. 242 nonies A annexe II CGI, L441-9 C. com.) :
numéro unique, date, identité et TVA intracommunautaire des deux parties,
désignation, quantité, prix unitaire HT, taux et montant de TVA par taux,
total HT et TTC, date d'échéance, pénalités de retard et indemnité forfaitaire
de 40 €, mention d'exonération le cas échéant.
"""
from __future__ import annotations

import html
from datetime import date

from app.services.gc import calculs, fichiers, pieces

TITRES = {
    "devis": "Devis", "marche": "Marché", "commande": "Accusé de réception de commande", "bl": "Bon de livraison",
    "facture": "Facture", "avoir": "Avoir", "cde_fournisseur": "Bon de commande",
    "reception": "Bon de réception", "facture_fournisseur": "Facture fournisseur",
    "of": "Ordre de fabrication", "aof": "Demande de prix",
}
SANS_PRIX = {"bl", "reception", "of"}


def _e(v) -> str:
    return html.escape(str(v if v is not None else ""))


def _euros(c) -> str:
    if c is None:
        return ""
    s = f"{abs(int(c)) / 100:,.2f}".replace(",", " ").replace(".", ",")
    return ("−" if int(c) < 0 else "") + s + " €"


def _qte(m, dec=3) -> str:
    v = int(m or 0) / 1000
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s


def _date(s) -> str:
    s = str(s or "")
    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}" if len(s) >= 10 else ""


def _adresse(conn, adr_id) -> list[str]:
    if not adr_id:
        return []
    a = conn.execute("SELECT * FROM gc_tiers_adresses WHERE id=?", (adr_id,)).fetchone()
    if not a:
        return []
    cp_ville = " ".join(x for x in (a["code_postal"], a["ville"]) if x)
    lignes = [a["adresse1"], a["adresse2"], cp_ville]
    if a["pays"] and a["pays"] != "FR":
        lignes.append(a["pays"])
    return [x for x in lignes if x]


_TEXTES_RELANCE = {
    1: ("Rappel d'échéance",
        "Sauf erreur ou omission de notre part, les factures ci-dessous restent impayées à ce jour. "
        "Nous vous remercions de bien vouloir procéder à leur règlement, ou de nous indiquer s'il s'agit d'un oubli "
        "de notre part. Si votre paiement est en cours, merci de ne pas tenir compte de ce courrier."),
    2: ("Relance",
        "Malgré notre précédent rappel, les factures ci-dessous restent impayées. Nous vous demandons de procéder "
        "à leur règlement sous huit jours. Nous restons à votre disposition pour tout échange à ce sujet."),
    3: ("Mise en demeure de payer",
        "Malgré nos relances, les factures ci-dessous restent impayées. Nous vous mettons en demeure de régler la "
        "somme indiquée sous huit jours à compter de la réception du présent courrier. À défaut, nous serons "
        "contraints d'engager une procédure de recouvrement. Des pénalités de retard et l'indemnité forfaitaire de "
        "40 € par facture sont exigibles de plein droit (art. L441-10 du Code de commerce)."),
}


def rendre_relance(conn, tiers_id: int, niveau: int = 1) -> str:
    from app.services.gc import compta
    niveau = niveau if niveau in _TEXTES_RELANCE else 1
    soc = fichiers.lire_societe(conn)
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone()
    if not t:
        return "<p>Client introuvable.</p>"
    jour = date.today().isoformat()
    ech = compta.echeances_echues(conn, tiers_id, jour)
    adr_id = conn.execute(
        """SELECT id FROM gc_tiers_adresses WHERE tiers_id=? AND type='facturation' AND actif=1
           ORDER BY par_defaut DESC, id LIMIT 1""", (tiers_id,)).fetchone()
    adr = _adresse(conn, adr_id["id"]) if adr_id else []
    titre, texte = _TEXTES_RELANCE[niveau]
    lignes = "".join(
        f'<tr><td><b>{_e(e["numero"])}</b></td><td>{_date(e["date_piece"])}</td><td>{_e(e["ref_tiers"])}</td>'
        f'<td>{_date(e["date_echeance"])}</td><td class="n">{_euros(e["montant_cents"])}</td>'
        f'<td class="n">{_euros(e["reste_cents"])}</td></tr>' for e in ech)
    total = sum(e["reste_cents"] for e in ech)
    soc_adr = [soc.get("adresse1"), soc.get("adresse2"), " ".join(x for x in (soc.get("code_postal"), soc.get("ville")) if x)]
    banque = f"<p>Règlement par virement — IBAN {_e(soc['iban'])}</p>" if soc.get("iban") else ""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>{_e(titre)} — {_e(t["raison_sociale"])}</title>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ margin: 0; font: 10.5pt/1.5 'Segoe UI', system-ui, sans-serif; color: black; background: white; }}
.page {{ max-width: 180mm; margin: 0 auto; padding: 8mm 0; }}
.tete {{ display: flex; justify-content: space-between; margin-bottom: 14mm; }}
.dest {{ margin-left: auto; width: 80mm; }}
h1 {{ font-size: 14pt; margin: 10mm 0 4mm; }}
table {{ width: 100%; border-collapse: collapse; margin: 6mm 0; }}
th {{ text-align: left; font-size: 8.5pt; text-transform: uppercase; border-bottom: 1.5px solid black; padding: 2mm 1.5mm; }}
td {{ border-bottom: 1px solid gainsboro; padding: 2mm 1.5mm; }}
.n {{ text-align: right; white-space: nowrap; }}
tr.total td {{ border-top: 1.5px solid black; font-weight: 700; }}
.barre {{ position: sticky; top: 0; background: whitesmoke; border-bottom: 1px solid gainsboro; padding: 8px; text-align: center; }}
.barre button {{ font: inherit; font-weight: 700; padding: 6px 16px; border-radius: 8px; border: 1px solid silver; background: white; cursor: pointer; }}
@media print {{ .barre {{ display: none; }} .page {{ padding: 0; }} }}
</style></head><body>
<div class="barre"><button onclick="window.print()">Imprimer / enregistrer en PDF</button></div>
<div class="page">
  <div class="tete"><div><b>{_e(soc.get("raison_sociale") or "")}</b><br>{"<br>".join(_e(x) for x in soc_adr if x)}</div></div>
  <div class="dest"><b>{_e(t["raison_sociale"])}</b><br>{"<br>".join(_e(x) for x in adr)}</div>
  <p style="text-align:right;margin-top:8mm">{_e(soc.get("ville") or "")}, le {_date(jour)}</p>
  <h1>{_e(titre)}</h1>
  <p>Madame, Monsieur,</p>
  <p>{_e(texte)}</p>
  <table><thead><tr><th>Facture</th><th>Date</th><th>Votre réf.</th><th>Échéance</th><th class="n">Montant TTC</th><th class="n">Reste dû</th></tr></thead>
  <tbody>{lignes}<tr class="total"><td colspan="5">Total restant dû</td><td class="n">{_euros(total)}</td></tr></tbody></table>
  {banque}
  <p>Nous vous prions d'agréer, Madame, Monsieur, nos salutations distinguées.</p>
  <p style="margin-top:12mm">Service comptabilité — {_e(soc.get("raison_sociale") or "")}</p>
</div></body></html>"""


def _chaine(conn, ligne_id: int) -> dict:
    """Pièces d'origine d'une ligne : {'commande': (numero, rang), 'bl': (numero, date)}."""
    out = {}
    lid = ligne_id
    for _ in range(4):
        r = conn.execute(
            """SELECT la.id, la.rang, la.ligne_amont_id, pa.type, pa.numero, pa.date_piece
               FROM gc_pieces_lignes l JOIN gc_pieces_lignes la ON la.id=l.ligne_amont_id
               JOIN gc_pieces pa ON pa.id=la.piece_id WHERE l.id=?""", (lid,)).fetchone()
        if not r:
            break
        if r["type"] in ("commande", "marche", "cde_fournisseur") and r["type"] not in out:
            out[r["type"]] = (r["numero"], r["rang"])
        if r["type"] in ("bl", "reception") and r["type"] not in out:
            out[r["type"]] = (r["numero"], r["date_piece"])
        lid = r["id"]
    return out


def _unite_vente(base: int, unite: str, libelles: dict) -> str:
    if int(base or 1) == 1000:
        return "Prix et Quantité au mille"
    lib = libelles.get(unite, unite or "")
    if not lib:
        return ""
    l_ = lib.lower()
    # « à l' » devant une voyelle, « à la » pour les unités féminines, sinon « au ».
    if l_[:1] in "aeiouyéèh":
        article = "à l'"
    elif l_.split()[0] in ("bobine", "planche", "feuille", "palette", "boîte", "caisse", "heure"):
        article = "à la "
    else:
        article = "au "
    return f"Prix et Quantité {article}{l_}"


def _pct(bp) -> str:
    return f"{int(bp) / 100:,.2f} %".replace(".", ",")


def donnees(conn, piece_id: int, modele: str = "") -> dict:
    """Contenu d'un document de pièce, indépendant du rendu (HTML ou PDF).

    Le texte riche n'utilise que `<b>` et `<br/>` sur du texte échappé :
    les deux moteurs (navigateur, reportlab) le lisent tel quel.
    `modele='expedition'` sur une commande : l'ordre d'expédition interne.
    """
    from app.services.gc import fsc
    p = pieces.charger(conn, piece_id)
    soc = fichiers.lire_societe(conn)
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (p["tiers_id"],)).fetchone()
    unites = {r["code"]: r for r in conn.execute("SELECT * FROM gc_unites").fetchall()}
    unites_lib = {k: v["libelle"] for k, v in unites.items()}
    tvas = {r["code"]: r for r in conn.execute("SELECT * FROM gc_tva").fetchall()}
    typ = p["type"]
    expedition = typ == "commande" and modele == "expedition"
    vente = pieces.TYPES[typ]["sens"] == "vente"
    titres = dict(TITRES, commande="Confirmation de commande")
    titre = "Ordre d'expédition" if expedition else titres.get(typ, typ)
    numero = p["numero"] or "BROUILLON"
    D = {"type": typ, "titre": titre, "numero": numero, "brouillon": not p["numero"],
         "titre_complet": f"{titre} {'No ' if typ not in ('facture', 'avoir') else ''}{numero}"}

    # ── Colonnes ─────────────────────────────────────────────────────
    if expedition:
        cols = [("Quantité", "d"), ("Unité de vente", "g"), ("Stock restant", "d"), ("", "g")]
    elif typ == "bl":
        cols = [("Quantité commandée", "d"), ("Quantité déjà livrée", "d"), ("Quantité livrée", "d"), ("Reliquat", "d")]
    elif typ == "reception":
        cols = [("Qté commandée", "d"), ("Qté livrée", "d")]
    elif typ == "of":
        cols = [("Quantité", "d"), ("Unité", "g")]
    elif typ in ("cde_fournisseur", "aof"):
        cols = [("Quantité", "d"), ("P.U. H.T.", "d"), ("Unité d'achat", "g"), ("Montant H.T.", "d"), ("Date de livraison", "c")]
    else:
        cols = [("Quantité", "d"), ("P.U. H.T.", "d"), ("Montant H.T.", "d"), ("TVA", "d")]
    D["colonnes"] = cols

    fsc_present = False
    lignes = []
    for l in p["lignes"]:
        if not l["article_id"]:
            lignes.append({"texte": True, "des": [f"<i>{_e(l['libelle'])}</i>"], "cells": [""] * len(cols)})
            continue
        art = conn.execute("SELECT * FROM gc_articles WHERE id=?", (l["article_id"],)).fetchone()
        dec = int(unites[l["unite"]]["decimales"]) if l["unite"] in unites else 3
        ch = _chaine(conn, l["id"])
        droite = []
        if vente and p["ref_tiers"] and typ in ("bl", "facture", "avoir"):
            droite.append(f"V/Réf commande : {_e(p['ref_tiers'])}")
        if l.get("ref_client"):
            droite.append(f"V/Réf produit : {_e(l['ref_client'])}")
        libelle_doc = l["libelle"]
        if vente and "designation_docs" in t.keys() and t["designation_docs"] == "client" and art["libelle_client"]:
            libelle_doc = art["libelle_client"]
        des = []
        lib_lignes = [x for x in str(libelle_doc or "").splitlines() if x.strip()]
        for x in (art["designation"] if "designation" in art.keys() else "",
                  art["conditionnement"] if "conditionnement" in art.keys() else ""):
            lib_lignes += [y for y in str(x or "").splitlines() if y.strip()]
        des += [_e(x) for x in lib_lignes]
        uv = _unite_vente(l["base_prix"], l["unite"], unites_lib)
        if typ in ("bl", "facture", "avoir", "commande") and uv and not expedition:
            des.append(f"Unité de vente : {_e(uv)}")
        if typ in ("cde_fournisseur", "aof"):
            des.append(f"Unité d'achat : {_e(uv or unites_lib.get(l['unite'], ''))}")
        rappel = []
        if "commande" in ch:
            rappel.append(f"Commande No {_e(ch['commande'][0])}/{ch['commande'][1]}")
        elif typ in ("commande", "marche") and p["numero"]:
            rappel.append(f"Cde : {_e(p['numero'])}/{l['rang']}")
        if "bl" in ch:
            rappel.append(f"BL No {_e(ch['bl'][0])} du {_date(ch['bl'][1])}")
        if "cde_fournisseur" in ch:
            rappel.append(f"Notre Cde : {_e(ch['cde_fournisseur'][0])}/{ch['cde_fournisseur'][1]}")
        if rappel:
            des.append(" · ".join(rappel))
        if vente and typ in ("bl", "facture", "avoir", "commande"):
            a = fsc.allegation_ligne(conn, l["id"]) if typ != "commande" else None
            if a and a[0] in fsc.FSC:
                fsc_present = True
                des.append(f"<b>{_e(fsc.libelle(a))}{' — ' + _e(soc.get('fsc_certificat')) if soc.get('fsc_certificat') else ''}</b>")
            elif typ == "commande" and "fsc_requis" in art.keys() and art["fsc_requis"]:
                fsc_present = True
                des.append("<b>Certifié FSC</b>")

        q = _qte(l["quantite_milli"], dec)
        if expedition:
            stock = conn.execute("SELECT COALESCE(SUM(quantite_milli),0) s FROM gc_mouvements WHERE article_id=?",
                                 (l["article_id"],)).fetchone()["s"]
            orig = pieces.ORIGINES.get(l.get("origine_prod") or "", "")
            cells = [q, _e(unites_lib.get(l["unite"], l["unite"])), _qte(stock, dec),
                     f"{_e(orig)}<br/>{_date(l.get('date_expedition') or p.get('date_expedition'))}"]
        elif typ == "bl":
            cde_q = deja = None
            if l["ligne_amont_id"]:
                cde_q = int(conn.execute("SELECT quantite_milli FROM gc_pieces_lignes WHERE id=?",
                                         (l["ligne_amont_id"],)).fetchone()["quantite_milli"])
                deja = int(conn.execute(
                    """SELECT COALESCE(SUM(lv.quantite_milli),0) q FROM gc_pieces_lignes lv JOIN gc_pieces pv ON pv.id=lv.piece_id
                       WHERE lv.ligne_amont_id=? AND pv.type='bl' AND pv.statut NOT IN ('annule','brouillon') AND lv.id!=?""",
                    (l["ligne_amont_id"], l["id"])).fetchone()["q"])
            reliquat = max(0, cde_q - deja - int(l["quantite_milli"])) if cde_q is not None else None
            cells = [_qte(cde_q, dec) if cde_q is not None else "", _qte(deja, dec) if deja is not None else "",
                     f"<b>{q}</b>", _qte(reliquat, dec) if reliquat is not None else ""]
        elif typ == "reception":
            cde_q = None
            if l["ligne_amont_id"]:
                cde_q = conn.execute("SELECT quantite_milli FROM gc_pieces_lignes WHERE id=?",
                                     (l["ligne_amont_id"],)).fetchone()["quantite_milli"]
            cells = [_qte(cde_q, dec) if cde_q is not None else "", q]
        elif typ == "of":
            cells = [q, _e(unites_lib.get(l["unite"], l["unite"]))]
        else:
            pu = f'{l["prix_cents"] / 100:,.3f}'.replace(",", " ").replace(".", ",")
            if l["remise_bp"]:
                pu += f'<br/>−{int(l["remise_bp"]) / 100:g} %'.replace(".", ",")
            mt = _euros(l["montant_ht_cents"]).replace(" €", "")
            if typ in ("cde_fournisseur", "aof"):
                cells = [q, pu, _e(unites_lib.get(l["unite"], l["unite"])), mt,
                         _date(l.get("date_livraison") or p.get("date_livraison"))]
            else:
                cells = [q, pu, mt, _pct(l["taux_tva_bp"])]
        lignes.append({"texte": False, "code": _e(l["article_code"]), "droite": droite, "des": des, "cells": cells})
    D["lignes"] = lignes

    # ── Totaux ou pied de BL ─────────────────────────────────────────
    D["totaux"] = None
    mentions_tva = []
    if typ in ("facture", "avoir", "devis", "commande", "marche", "cde_fournisseur", "aof", "facture_fournisseur") and not expedition:
        tot = calculs.totaux(p["lignes"], p["remise_bp"], p.get("escompte_bp") or 0, p.get("acompte_cents") or 0)
        brut_total = sum(x["ht_brut"] for x in tot["bases"])
        rangees = []
        for b in tot["bases"]:
            code = next((l["tva_code"] for l in p["lignes"] if l["article_id"] and int(l["taux_tva_bp"]) == b["taux_bp"]), None)
            rangees.append([_euros(brut_total), _euros(b["ht"]), "Exonéré" if not b["taux_bp"] else _pct(b["taux_bp"]),
                            _euros(b["tva"]), _euros(b["ht"] + b["tva"])])
            if code in tvas and tvas[code]["mention"]:
                mentions_tva.append(tvas[code]["mention"])
        remises = []
        if tot["remise"]:
            remises.append(f"Remise {_euros(tot['remise'])}")
        if tot["escompte"]:
            remises.append(f"Escompte {_euros(tot['escompte'])}")
        D["totaux"] = {
            "genre": "montants",
            "entetes": ["Montant total H.T.", "Base H.T.", "Taux", "Montant TVA", "Montant TTC"],
            "rangees": rangees, "remises": " · ".join(remises),
            "tva_debits": typ in ("facture", "avoir") and bool(soc.get("tva_sur_debits")),
            "acompte": _euros(tot["acompte"]) if tot["acompte"] else "",
            "net_libelle": "Net en votre faveur" if typ == "avoir" else "Net à payer",
            "net": _euros(tot["net_a_payer"]),
        }
    elif typ in ("bl", "reception"):
        tr = conn.execute("SELECT nom FROM expe_transporteurs WHERE id=?", (p.get("transporteur_id"),)).fetchone() \
            if p.get("transporteur_id") else None
        ent = ["Mode de " + ("livraison" if typ == "bl" else "réception"), "Nbre de colis", "Nbre de palettes",
               "Poids en kg", "Récépissé"] + (["Visa et nom"] if typ == "reception" else [])
        val = [_e(tr["nom"] if tr else "Par nos soins"), _e(p.get("nb_colis") or ""), _e(p.get("nb_palettes") or ""),
               _qte(p["poids_g"], 3) if p.get("poids_g") else "", _e(p.get("recepisse") or "")] + ([""] if typ == "reception" else [])
        D["totaux"] = {"genre": "pied", "entetes": ent, "valeurs": val}

    # ── Cartouches ───────────────────────────────────────────────────
    contact = conn.execute("SELECT nom FROM gc_tiers_contacts WHERE id=?", (p["contact_id"],)).fetchone() \
        if p.get("contact_id") else None
    suivi = []
    if typ in ("cde_fournisseur", "aof") and p.get("date_livraison"):
        suivi.append(("Date de réception souhaitée", _date(p["date_livraison"])))
    if p.get("cree_par"):
        suivi.append(("Commande suivie par" if typ in ("commande", "cde_fournisseur", "devis", "aof") else
                      "Livraison suivie par" if typ == "bl" else "Suivi par", p["cree_par"]))
    if contact:
        suivi.append(("À l'attention de", contact["nom"]))
    if typ == "devis" and p.get("date_validite"):
        suivi.append(("Valable jusqu'au", _date(p["date_validite"])))
    if typ == "marche":
        suivi += [("Ouverture", _date(p.get("date_ouverture"))), ("Fermeture", _date(p.get("date_validite")))]
    if p.get("ref_tiers") and typ in ("commande", "devis", "marche"):
        suivi.append(("Vos références", p["ref_tiers"]))
    if typ == "facture_fournisseur":
        suivi.append(("N° de facture fournisseur", p.get("ref_tiers") or ""))
    if typ == "reception" and p.get("ref_tiers"):
        suivi.append(("BL fournisseur", p["ref_tiers"]))
    D["cartouche"] = {"entetes": ["Date", "Client" if vente else "Fournisseur", "Page"],
                      "valeurs": [_date(p["date_piece"]), _e(t["code"]), "1"],
                      "suivi": [f"{_e(a)} : {_e(b)}" for a, b in suivi if b]}

    D["reglement"] = None
    if typ in ("facture", "avoir", "facture_fournisseur", "cde_fournisseur", "commande", "devis") and not expedition:
        cond = conn.execute("SELECT * FROM gc_conditions_paiement WHERE code=?", (p["condition_paiement"],)).fetchone() \
            if p["condition_paiement"] else None
        mode = conn.execute("SELECT libelle FROM gc_modes_paiement WHERE code=?", (p["mode_paiement"],)).fetchone() \
            if p["mode_paiement"] else None
        ech = ", ".join(_date(e["date_echeance"]) for e in p["echeances"])
        if not ech and typ == "facture" and cond:
            ech = _date(calculs.date_echeance(date.fromisoformat(p["date_piece"][:10]), cond["jours"], bool(cond["fin_de_mois"]),
                                              cond["jour_du_mois"]).isoformat())
        D["reglement"] = {"mode": _e(mode["libelle"] if mode else ""), "conditions": _e(cond["libelle"] if cond else ""),
                          "echeance": ech}
    origine = []
    if typ in ("facture", "avoir") and soc.get("mention_origine"):
        origine += [_e(x) for x in soc["mention_origine"].splitlines() if x.strip()]
    if typ == "avoir" and p.get("piece_annulee_id"):
        f = conn.execute("SELECT numero, date_piece FROM gc_pieces WHERE id=?", (p["piece_annulee_id"],)).fetchone()
        if f:
            origine.append(f"Avoir sur facture {_e(f['numero'])} du {_date(f['date_piece'])}")
    D["origine"] = origine
    D["contact"] = (_e(contact["nom"]) if contact else "") if typ == "bl" else None

    # ── Adresses ─────────────────────────────────────────────────────
    fact = [_e(x) for x in _adresse(conn, p["adresse_facturation_id"])]
    livr = [_e(x) for x in _adresse(conn, p["adresse_livraison_id"])]
    nom = _e(t["raison_sociale"])
    adresses = []
    if vente:
        bloc_fact = {"titre": "Adresse de facturation", "lignes": [nom] + fact + (
            [f"V/No TVA : {_e(t['tva_intra'])}"] if t["tva_intra"] and typ in ("facture", "avoir") else []),
            "barree": typ == "bl" or expedition}
        bloc_livr = {"titre": "Adresse de livraison", "lignes": [nom] + (livr or fact), "barree": False}
        if typ in ("facture", "avoir"):
            adresses = [bloc_livr, bloc_fact]
        elif typ in ("devis", "marche") and not livr:
            adresses = [bloc_fact]
        else:
            adresses = [bloc_fact, bloc_livr]
    else:
        soc_adr_l = [_e(x) for x in (soc.get("adresse1"), soc.get("adresse2"),
                                     " ".join(x for x in (soc.get("code_postal"), soc.get("ville")) if x)) if x]
        adresses = [{"titre": "Fournisseur", "lignes": [f"<b>{nom}</b>"] + fact, "barree": False},
                    {"titre": "Adresse de réception" if typ == "reception" else "Adresse de livraison",
                     "lignes": [f"<b>{_e(soc.get('raison_sociale') or '')}</b>"] + soc_adr_l, "barree": False}]
    D["adresses"] = adresses

    # ── Mentions et pied ─────────────────────────────────────────────
    mentions = []
    if p["notes"]:
        mentions.append(_e(p["notes"]))
    mentions += [_e(m) for m in mentions_tva]
    if fsc_present and soc.get("fsc_certificat"):
        mentions.append(_e(f"Certificat FSC : {soc['fsc_certificat']}" + (f" — licence {soc['fsc_licence']}" if soc.get("fsc_licence") else "")))
    D["affacturage"] = _e(soc.get("texte_affacturage") or "") if typ in ("facture", "avoir") else ""
    if typ in ("facture", "avoir"):
        mentions.append(_e(soc.get("texte_penalites") or soc.get("penalites_retard") or ""))
        if soc.get("texte_reserve_propriete"):
            mentions.append(_e(soc["texte_reserve_propriete"]))
    if vente and soc.get("texte_juridiction"):
        mentions.append(_e(soc["texte_juridiction"]))
    D["mentions"] = [m for m in mentions if m]

    soc_lignes = [x for x in (soc.get("adresse1"), soc.get("adresse2"),
                              " ".join(x for x in (soc.get("code_postal"), soc.get("ville")) if x)) if x]
    if soc.get("telephone"):
        soc_lignes.append(f"Tél. {soc['telephone']}")
    ident = ([f"TVA : {soc['tva_intra']}"] if soc.get("tva_intra") else []) + ([f"SIRET : {soc['siret']}"] if soc.get("siret") else [])
    D["societe"] = {"nom": _e(soc.get("raison_sociale") or ""), "lignes": [_e(x) for x in soc_lignes],
                    "ident": [_e(x) for x in ident]}
    legal = " · ".join(x for x in (
        " ".join(x for x in (soc.get("forme_juridique"),
                             ("au capital de " + _euros(soc["capital_cents"])) if soc.get("capital_cents") else "") if x),
        soc.get("rcs") or "", ("APE " + soc["ape"]) if soc.get("ape") else "") if x)
    D["pied"] = [f"Siège social : {_e(', '.join(soc_lignes))}", f"{_e(soc.get('raison_sociale') or '')} {_e(legal)}"]
    return D


def rendre(conn, piece_id: int, modele: str = "") -> str:
    """Document A4 en HTML (aperçu, impression navigateur)."""
    D = donnees(conn, piece_id, modele)
    cols = D["colonnes"]
    al = {"d": "n", "g": "", "c": "c"}

    def adr(a):
        return (f"<div class='adr{' barree' if a['barree'] else ''}'><div class='lib'>{_e(a['titre'])}</div>"
                + "<br>".join(a["lignes"]) + "</div>")

    corps = []
    for l in D["lignes"]:
        if l["texte"]:
            corps.append(f"<tr class='texte'><td colspan='{len(cols) + 1}'>{l['des'][0]}</td></tr>")
            continue
        tete = f"<div class='code'><span>{l['code']}</span><b>{'<br>'.join(l['droite'])}</b></div>"
        des = tete + "".join(f"<div>{x}</div>" for x in l["des"])
        corps.append("<tr><td class='des'>" + des + "</td>"
                     + "".join(f"<td class='{al[c[1]]}'>{v}</td>" for c, v in zip(cols, l["cells"])) + "</tr>")
    tete_cols = "<tr><th>Désignation</th>" + "".join(f"<th>{_e(c[0])}</th>" for c in cols) + "</tr>"
    tot = D["totaux"]
    totaux_html = ""
    if tot and tot["genre"] == "montants":
        totaux_html = ((f"<div class='remises'>{tot['remises']}</div>" if tot["remises"] else "")
                       + "<table class='totaux'><tr>" + "".join(f"<th>{e}</th>" for e in tot["entetes"]) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in tot["rangees"]) + "</table>"
                       + ("<div class='mini'>TVA sur les débits</div>" if tot["tva_debits"] else "")
                       + (f"<div class='net petit'><span>Acompte :</span><b>{tot['acompte']}</b></div>" if tot["acompte"] else "")
                       + f"<div class='net'><span>{tot['net_libelle']} :</span><b>{tot['net']}</b></div>")
    elif tot:
        totaux_html = ("<table class='totaux pied-bl'><tr>" + "".join(f"<th>{e}</th>" for e in tot["entetes"]) + "</tr><tr>"
                       + "".join(f"<td>{v}</td>" for v in tot["valeurs"]) + "</tr></table>")
    cart = D["cartouche"]
    cartouche = ("<table class='cart'><tr>" + "".join(f"<th>{e}</th>" for e in cart["entetes"]) + "</tr><tr>"
                 + "".join(f"<td>{v}</td>" for v in cart["valeurs"]) + "</tr>"
                 + (f"<tr><td colspan='3' class='suivi'>{'<br>'.join(cart['suivi'])}</td></tr>" if cart["suivi"] else "")
                 + "</table>")
    rg = D["reglement"]
    reglement = ""
    if rg:
        reglement = ("<table class='regl'><tr><th>Mode de règlement</th>" + ("<th>Échéance</th>" if rg["echeance"] else "") + "</tr>"
                     f"<tr><td>{rg['mode']}<br>{rg['conditions']}</td>" + (f"<td class='ech'>{rg['echeance']}</td>" if rg["echeance"] else "")
                     + "</tr></table>")
    origine = "<div class='origine'>" + "<br>".join(D["origine"]) + "</div>" if D["origine"] else ""
    contact_box = f"<div class='adr contact'><div class='lib'>Contact</div>{D['contact']}</div>" if D["contact"] is not None else ""
    mentions = ([f"<p class='affact'>{D['affacturage']}</p>"] if D["affacturage"] else []) + [f"<p>{m}</p>" for m in D["mentions"]]
    S = D["societe"]
    filigrane = '<div class="filigrane">BROUILLON</div>' if D["brouillon"] else ""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<title>{_e(D['titre'])} {_e(D['numero'])}</title>
<style>
@page {{ size: A4; margin: 12mm 12mm 14mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 9.5pt/1.35 'Segoe UI', system-ui, sans-serif; color: black; background: white; }}
.page {{ max-width: 190mm; margin: 0 auto; padding: 6mm 0; position: relative; }}
.haut {{ display: grid; grid-template-columns: 1fr 1.15fr; gap: 6mm; }}
.soc b {{ font-size: 15pt; letter-spacing: .5px; }}
.soc div {{ font-size: 8.5pt; }}
h1 {{ margin: 0 0 3mm; font-size: 16pt; }}
.adr {{ border: 1px solid dimgray; padding: 2mm 3mm; margin-bottom: 3mm; min-height: 24mm; font-size: 10pt; }}
.adr .lib {{ text-align: center; text-decoration: underline; font-size: 9pt; }}
.adr.barree {{ background: linear-gradient(to top right, transparent calc(50% - .5px), dimgray, transparent calc(50% + .5px)),
                           linear-gradient(to bottom right, transparent calc(50% - .5px), dimgray, transparent calc(50% + .5px)); }}
.adr.contact {{ min-height: 18mm; }}
.milieu {{ display: grid; grid-template-columns: 1fr 1.15fr; gap: 6mm; margin: 2mm 0 4mm; align-items: start; }}
table {{ border-collapse: collapse; width: 100%; }}
.cart th, .cart td, .regl th, .regl td {{ border: 1px solid dimgray; padding: 1.5mm 2mm; text-align: center; font-weight: 400; }}
.cart td {{ font-size: 11pt; }}
.cart td.suivi, .regl td {{ text-align: left; font-size: 9pt; }}
.regl td.ech {{ text-align: center; font-size: 11pt; }}
.origine {{ font-size: 9.5pt; margin-top: 2mm; }}
table.lignes {{ border: 1px solid dimgray; }}
table.lignes th {{ border: 1px solid dimgray; font-weight: 400; padding: 1.5mm; text-align: center; font-size: 9pt; }}
table.lignes td {{ border-left: 1px solid dimgray; border-right: 1px solid dimgray; padding: 2.5mm 1.5mm 1mm; vertical-align: top; }}
table.lignes td.des {{ font-size: 8.5pt; width: 52%; }}
table.lignes td.des .code {{ display: flex; justify-content: space-between; gap: 4mm; }}
table.lignes td.des .code b {{ text-align: right; }}
table.lignes tr.texte td {{ font-style: italic; }}
table.lignes tbody tr:last-child td {{ padding-bottom: 30mm; }}
.n {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.c {{ text-align: center; }}
table.totaux th, table.totaux td {{ border: 1px solid dimgray; padding: 1.5mm 2mm; font-weight: 400; text-align: center; }}
table.totaux td {{ font-size: 11pt; text-align: right; }}
table.pied-bl td {{ text-align: center; font-size: 10pt; }}
.remises {{ text-align: right; font-size: 9pt; margin: 1mm 0; }}
.mini {{ font-size: 8pt; }}
.net {{ display: flex; justify-content: flex-end; gap: 10mm; margin-top: 1mm; font-size: 12pt; }}
.net span, .net b {{ border: 1px solid dimgray; padding: 1.5mm 4mm; }}
.net.petit {{ font-size: 10pt; }}
.mentions {{ margin-top: 4mm; font-size: 7.5pt; }}
.mentions p {{ margin: 0 0 1mm; }}
.affact {{ color: firebrick; font-weight: 700; }}
.pied {{ margin-top: 6mm; font-size: 7.5pt; text-align: center; }}
.filigrane {{ position: fixed; top: 40%; left: 0; right: 0; text-align: center; font-size: 72pt; font-weight: 800;
  color: gainsboro; transform: rotate(-24deg); pointer-events: none; z-index: -1; }}
.barre {{ position: sticky; top: 0; background: whitesmoke; border-bottom: 1px solid gainsboro; padding: 8px; text-align: center; }}
.barre button, .barre a {{ font: inherit; font-weight: 700; padding: 6px 16px; border-radius: 8px; border: 1px solid silver;
  background: white; cursor: pointer; color: black; text-decoration: none; }}
@media print {{ .barre {{ display: none; }} .page {{ padding: 0; }} }}
</style></head>
<body>
<!-- mysifa-boutons-off -->
<div class="barre"><button onclick="window.print()">Imprimer</button>
  <a href="?{'modele=' + _e(modele) + '&' if modele else ''}format=pdf">Télécharger le PDF</a></div>
{filigrane}
<div class="page">
  <div class="haut">
    <div class="soc"><b>{S['nom']}</b>{"".join(f"<div>{x}</div>" for x in S['lignes'])}
      <div style="margin-top:2mm">{"<br>".join(S['ident'])}</div></div>
    <div><h1>{_e(D['titre_complet'])}</h1>{"".join(adr(a) for a in D['adresses'])}</div>
  </div>
  <div class="milieu"><div>{cartouche}{origine}</div><div>{reglement}{contact_box}</div></div>
  <table class="lignes"><thead>{tete_cols}</thead><tbody>{"".join(corps)}</tbody></table>
  {totaux_html}
  <div class="mentions">{"".join(mentions)}</div>
  <div class="pied">{"<br>".join(D['pied'])}</div>
</div>
</body></html>"""
