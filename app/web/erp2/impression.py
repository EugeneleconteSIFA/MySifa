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
    "of": "Ordre de fabrication",
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


def rendre(conn, piece_id: int) -> str:
    p = pieces.charger(conn, piece_id)
    soc = fichiers.lire_societe(conn)
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (p["tiers_id"],)).fetchone()
    unites = {r["code"]: r for r in conn.execute("SELECT * FROM gc_unites").fetchall()}
    tvas = {r["code"]: r for r in conn.execute("SELECT * FROM gc_tva").fetchall()}
    sans_prix = p["type"] in SANS_PRIX
    titre = TITRES.get(p["type"], p["type"])
    numero = p["numero"] or "BROUILLON"

    # ── Lignes ───────────────────────────────────────────────────────
    corps = []
    for l in p["lignes"]:
        if not l["article_id"]:
            corps.append(f'<tr class="texte"><td colspan="{3 if sans_prix else 6}">{_e(l["libelle"])}</td></tr>')
            continue
        dec = int(unites[l["unite"]]["decimales"]) if l["unite"] in unites else 3
        desig = f'<b>{_e(l["article_code"])}</b> {_e(l["libelle"])}'
        if sans_prix:
            corps.append(f'<tr><td>{desig}</td><td class="n">{_qte(l["quantite_milli"], dec)}</td><td>{_e(l["unite"])}</td></tr>')
        else:
            base = f' <small>/ {_qte(l["base_prix"] * 1000, 0)}</small>' if int(l["base_prix"]) > 1 else ""
            rem = f'{int(l["remise_bp"]) / 100:g} %'.replace(".", ",") if l["remise_bp"] else ""
            corps.append(
                f'<tr><td>{desig}</td><td class="n">{_qte(l["quantite_milli"], dec)} {_e(l["unite"])}</td>'
                f'<td class="n">{_euros(l["prix_cents"])}{base}</td><td class="n">{rem}</td>'
                f'<td class="n">{_e(l["tva_code"])}</td><td class="n">{_euros(l["montant_ht_cents"])}</td></tr>')
    entete_lignes = ('<tr><th>Désignation</th><th class="n">Quantité</th><th>Unité</th></tr>' if sans_prix else
                     '<tr><th>Désignation</th><th class="n">Quantité</th><th class="n">Prix unitaire HT</th>'
                     '<th class="n">Remise</th><th class="n">TVA</th><th class="n">Montant HT</th></tr>')

    # ── Totaux et mentions ───────────────────────────────────────────
    totaux = ""
    mentions = []
    if not sans_prix:
        tot = calculs.totaux(p["lignes"], p["remise_bp"])
        rows = []
        if tot["remise"]:
            rows.append(("Total HT brut", _euros(sum(b["ht_brut"] for b in tot["bases"]))))
            rows.append((f'Remise {int(p["remise_bp"]) / 100:g} %'.replace(".", ","), "− " + _euros(tot["remise"])))
        rows.append(("Total HT", _euros(tot["ht"])))
        for b in tot["bases"]:
            rows.append((f'TVA {b["taux_bp"] / 100:g} % sur {_euros(b["ht"])}'.replace(".", ","), _euros(b["tva"])))
        rows.append(("Total TTC" if p["type"] != "avoir" else "Total TTC en votre faveur", _euros(tot["ttc"])))
        totaux = '<table class="totaux">' + "".join(
            f'<tr class="{"fort" if i == len(rows) - 1 else ""}"><td>{_e(a)}</td><td class="n">{b}</td></tr>'
            for i, (a, b) in enumerate(rows)) + "</table>"
        for code in sorted({l["tva_code"] for l in p["lignes"] if l["article_id"]} - {None}):
            if code in tvas and tvas[code]["mention"]:
                mentions.append(tvas[code]["mention"])

    infos = []
    if p["ref_tiers"]:
        infos.append(("Votre référence" if pieces.TYPES[p["type"]]["sens"] == "vente" else "Référence fournisseur", p["ref_tiers"]))
    if p["type"] == "devis" and p["date_validite"]:
        infos.append(("Valable jusqu'au", _date(p["date_validite"])))
    if p["type"] == "marche" and p["date_validite"]:
        infos.append(("Fin du marché", _date(p["date_validite"])))
    if p["date_livraison"] and p["type"] in ("commande", "cde_fournisseur", "devis"):
        infos.append(("Livraison prévue", _date(p["date_livraison"])))
    cond = None
    if p["condition_paiement"]:
        cond = conn.execute("SELECT libelle FROM gc_conditions_paiement WHERE code=?", (p["condition_paiement"],)).fetchone()
    if cond and not sans_prix:
        infos.append(("Conditions de paiement", cond["libelle"]))
    if p["mode_paiement"] and not sans_prix:
        m = conn.execute("SELECT libelle FROM gc_modes_paiement WHERE code=?", (p["mode_paiement"],)).fetchone()
        if m:
            infos.append(("Mode de paiement", m["libelle"]))
    if p["echeances"]:
        infos.append(("Échéance", ", ".join(_date(e["date_echeance"]) for e in p["echeances"])))
    elif p["type"] == "facture" and p["statut"] == "brouillon":
        c = conn.execute("SELECT * FROM gc_conditions_paiement WHERE code=?", (p["condition_paiement"],)).fetchone() if p["condition_paiement"] else None
        if c:
            e = calculs.date_echeance(date.fromisoformat(p["date_piece"][:10]), c["jours"], bool(c["fin_de_mois"]), c["jour_du_mois"])
            infos.append(("Échéance", _date(e.isoformat())))
    if p["type"] == "avoir" and p["piece_annulee_id"]:
        f = conn.execute("SELECT numero, date_piece FROM gc_pieces WHERE id=?", (p["piece_annulee_id"],)).fetchone()
        if f:
            infos.append(("Sur facture", f"{f['numero']} du {_date(f['date_piece'])}"))
    amont = [a for a in p["amont"] if a["numero"]]
    if amont and p["type"] in ("bl", "facture"):
        lib = "Commande" if p["type"] == "bl" else "Bon(s) de livraison"
        infos.append((lib, ", ".join(a["numero"] for a in amont)))

    if p["type"] in ("facture", "avoir"):
        if soc.get("penalites_retard"):
            mentions.append(soc["penalites_retard"])
        mentions.append("Pas d'escompte pour paiement anticipé.")
    if p["notes"]:
        mentions.insert(0, p["notes"])
    banque = ""
    if p["type"] == "facture" and soc.get("iban"):
        banque = f'<div class="banque">Règlement par virement — IBAN {_e(soc["iban"])}{" · BIC " + _e(soc["bic"]) if soc.get("bic") else ""}</div>'

    # ── Blocs société / tiers ────────────────────────────────────────
    soc_adr = [soc.get("adresse1"), soc.get("adresse2"),
               " ".join(x for x in (soc.get("code_postal"), soc.get("ville")) if x)]
    soc_contact = " · ".join(x for x in (soc.get("telephone"), soc.get("email")) if x)
    legal = " · ".join(x for x in (
        " ".join(x for x in (soc.get("forme_juridique"),
                             ("au capital de " + _euros(soc["capital_cents"])) if soc.get("capital_cents") else "") if x),
        ("SIRET " + soc["siret"]) if soc.get("siret") else "",
        soc.get("rcs") or "", ("APE " + soc["ape"]) if soc.get("ape") else "",
        ("TVA " + soc["tva_intra"]) if soc.get("tva_intra") else "") if x)

    fact = _adresse(conn, p["adresse_facturation_id"])
    livr = _adresse(conn, p["adresse_livraison_id"]) if p["type"] in ("devis", "commande", "bl") else []
    bloc_tiers = (f'<div class="adr"><div class="lib">{"Client" if pieces.TYPES[p["type"]]["sens"] == "vente" else "Fournisseur"}</div>'
                  f'<b>{_e(t["raison_sociale"])}</b><br>' + "<br>".join(_e(x) for x in fact) +
                  (f'<br><small>TVA {_e(t["tva_intra"])}</small>' if t["tva_intra"] else "") +
                  f'<br><small>Code {_e(t["code"])}</small></div>')
    if livr and livr != fact:
        bloc_tiers += f'<div class="adr"><div class="lib">Livraison</div><b>{_e(t["raison_sociale"])}</b><br>' + "<br>".join(_e(x) for x in livr) + "</div>"

    infos_html = "".join(f"<div><span>{_e(a)}</span><b>{_e(b)}</b></div>" for a, b in infos)
    mentions_html = "".join(f"<p>{_e(m)}</p>" for m in mentions)
    filigrane = '<div class="filigrane">BROUILLON</div>' if not p["numero"] else ""

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<title>{_e(titre)} {_e(numero)}</title>
<style>
@page {{ size: A4; margin: 14mm 14mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 10pt/1.4 'Segoe UI', system-ui, sans-serif; color: black; background: white; }}
.page {{ max-width: 190mm; margin: 0 auto; padding: 8mm 0; position: relative; }}
.tete {{ display: flex; justify-content: space-between; gap: 10mm; margin-bottom: 8mm; }}
.soc b {{ font-size: 13pt; }}
.soc small, .adr small {{ color: dimgray; }}
.doc {{ text-align: right; }}
.doc h1 {{ margin: 0; font-size: 16pt; letter-spacing: .5px; }}
.doc .num {{ font-size: 12pt; font-weight: 700; margin-top: 2mm; }}
.tiers {{ display: flex; gap: 6mm; justify-content: flex-end; margin-bottom: 6mm; }}
.adr {{ width: 80mm; border: 1px solid silver; border-radius: 2mm; padding: 3mm 4mm; }}
.adr .lib {{ font-size: 8pt; text-transform: uppercase; letter-spacing: .5px; color: dimgray; margin-bottom: 1mm; }}
.infos {{ display: flex; flex-wrap: wrap; gap: 2mm 8mm; margin-bottom: 5mm; }}
.infos div {{ display: flex; flex-direction: column; }}
.infos span {{ font-size: 8pt; color: dimgray; text-transform: uppercase; letter-spacing: .4px; }}
table.lignes {{ width: 100%; border-collapse: collapse; }}
table.lignes th {{ font-size: 8pt; text-transform: uppercase; letter-spacing: .4px; text-align: left; border-bottom: 1.5px solid black; padding: 2mm 1.5mm; }}
table.lignes td {{ border-bottom: 1px solid gainsboro; padding: 2mm 1.5mm; vertical-align: top; }}
table.lignes tr.texte td {{ font-style: italic; color: dimgray; }}
.n {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
td small {{ color: dimgray; }}
table.totaux {{ margin: 5mm 0 0 auto; border-collapse: collapse; min-width: 75mm; }}
table.totaux td {{ padding: 1.2mm 1.5mm; }}
table.totaux tr.fort td {{ border-top: 1.5px solid black; font-weight: 700; font-size: 11pt; }}
.mentions {{ margin-top: 8mm; font-size: 8pt; color: dimgray; }}
.mentions p {{ margin: 0 0 1.5mm; }}
.banque {{ margin-top: 4mm; font-size: 9pt; }}
.pied {{ margin-top: 10mm; padding-top: 2mm; border-top: 1px solid silver; font-size: 7.5pt; color: dimgray; text-align: center; }}
.filigrane {{ position: fixed; top: 40%; left: 0; right: 0; text-align: center; font-size: 72pt; font-weight: 800;
  color: gainsboro; transform: rotate(-24deg); pointer-events: none; z-index: -1; }}
.barre {{ position: sticky; top: 0; background: whitesmoke; border-bottom: 1px solid gainsboro; padding: 8px; text-align: center; }}
.barre button {{ font: inherit; font-weight: 700; padding: 6px 16px; border-radius: 8px; border: 1px solid silver; background: white; cursor: pointer; }}
@media print {{ .barre {{ display: none; }} .page {{ padding: 0; }} }}
</style></head>
<body>
<!-- mysifa-boutons-off -->
<div class="barre"><button onclick="window.print()">Imprimer / enregistrer en PDF</button></div>
{filigrane}
<div class="page">
  <div class="tete">
    <div class="soc"><b>{_e(soc.get("raison_sociale") or "")}</b><br>{"<br>".join(_e(x) for x in soc_adr if x)}
      {f"<br><small>{_e(soc_contact)}</small>" if soc_contact else ""}</div>
    <div class="doc"><h1>{_e(titre)}</h1><div class="num">N° {_e(numero)}</div><div>du {_date(p["date_piece"])}</div></div>
  </div>
  <div class="tiers">{bloc_tiers}</div>
  <div class="infos">{infos_html}</div>
  <table class="lignes"><thead>{entete_lignes}</thead><tbody>{"".join(corps)}</tbody></table>
  {totaux}
  {banque}
  <div class="mentions">{mentions_html}</div>
  <div class="pied">{_e(soc.get("raison_sociale") or "")}{" · " + _e(legal) if legal else ""}</div>
</div>
</body></html>"""
