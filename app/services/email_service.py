"""MySifa — Envoi d'emails (SMTP + fallback Microsoft Graph).

Contrat: `send_email()` retourne True/False et **ne lève jamais**.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import time
import json
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import html as html_module

from config import (
    public_base_url,
    MS_CLIENT_ID,
    MS_CLIENT_SECRET,
    MS_SENDER_UPN,
    MS_TENANT_ID,
    SMTP_FROM,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_USER,
    SUPPORT_EMAIL_PROVIDER,
)

logger = logging.getLogger(__name__)

_GRAPH_TOKEN = {"access_token": None, "expires_at": 0.0}


def _esc(text: object) -> str:
    return html_module.escape(str(text or ""))


def email_mysifa_layout(
    *,
    subtitle: str,
    body_html: str,
    cta_href: str | None = None,
    cta_label: str | None = None,
    footer_note: str | None = None,
    footer_contact: bool = False,
) -> str:
    """Enveloppe HTML email MySifa (dark header, typo Segoe UI)."""
    cta_block = ""
    if cta_href and cta_label:
        cta_block = f"""
    <div style="margin:26px 0 8px;text-align:center">
      <a href="{_esc(cta_href)}" style="background:#22d3ee;color:#0a0e17;font-weight:800;font-size:14px;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">
        {_esc(cta_label)}
      </a>
    </div>
    <p style="margin:12px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;text-align:center;word-break:break-all">
      Si le bouton ne fonctionne pas, copier ce lien :<br>
      <a href="{_esc(cta_href)}" style="font-family:ui-monospace,monospace;font-size:11px;color:#0891b2;text-decoration:none">{_esc(cta_href)}</a>
    </p>"""
    contact_block = ""
    if footer_contact:
        contact_block = """
    <p style="margin:14px 0 0;font-size:12px;color:#64748b;line-height:1.7;text-align:center">
      <strong style="color:#0f172a">SIFA — Roubaix (59)</strong><br>
      <a href="tel:+33320690101" style="color:#0891b2;text-decoration:none">03 20 69 01 01</a>
      &nbsp;·&nbsp;
      <a href="mailto:expeditions@sifa.pro" style="color:#0891b2;text-decoration:none">expeditions@sifa.pro</a>
    </p>"""
    foot = footer_note or f"Notification automatique MySifa — {_esc(public_base_url())}"
    return f"""<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:24px 32px">
    <div style="font-size:20px;font-weight:800;color:#22d3ee;letter-spacing:-.3px">MySifa</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">{_esc(subtitle)}</div>
  </div>
  <div style="padding:32px;font-size:14px;color:#334155;line-height:1.65">
    {body_html}
    {cta_block}
    {contact_block}
    <p style="margin:20px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;border-top:1px solid #e2e8f0;padding-top:14px;text-align:center">
      {foot}
    </p>
  </div>
</div>"""


def _email_detail_table(rows: list[tuple[str, str]]) -> str:
    """Tableau label / valeur pour emails (valeurs déjà échappées si besoin)."""
    body_rows = ""
    for label, value in rows:
        body_rows += (
            f"<tr>"
            f"<td style=\"padding:11px 14px;border-bottom:1px solid #e2e8f0;font-size:11px;"
            f"text-transform:uppercase;letter-spacing:.45px;color:#64748b;font-weight:700;"
            f"width:40%;vertical-align:top\">{_esc(label)}</td>"
            f"<td style=\"padding:11px 14px;border-bottom:1px solid #e2e8f0;font-size:14px;"
            f"color:#0f172a;font-weight:600;vertical-align:top\">{value}</td>"
            f"</tr>"
        )
    return (
        "<table role=\"presentation\" style=\"width:100%;border-collapse:collapse;"
        "background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin:0 0 22px\">"
        f"<tbody>{body_rows}</tbody></table>"
    )


_EMAIL_FLAG_FR = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 3 2" '
    'style="display:block;border-radius:2px;border:1px solid #e2e8f0">'
    '<rect width="1" height="2" fill="#002395"/><rect x="1" width="1" height="2" fill="#fff"/>'
    '<rect x="2" width="1" height="2" fill="#ED2939"/></svg>'
)
_EMAIL_FLAG_GB = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 60 30" '
    'style="display:block;border-radius:2px;border:1px solid #e2e8f0">'
    '<rect width="60" height="30" fill="#012169"/>'
    '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>'
    '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="3"/>'
    '<path d="M30,0 V30 M0,15 H60" stroke="#fff" stroke-width="10"/>'
    '<path d="M30,0 V30 M0,15 H60" stroke="#C8102E" stroke-width="6"/></svg>'
)


def _email_lang_picker_html() -> str:
    """Sélecteur FR/EN (radios + CSS — clients mail modernes)."""
    return f"""
    <input type="radio" name="mysifa-lang" id="mysifa-lang-fr" style="display:none!important">
    <input type="radio" name="mysifa-lang" id="mysifa-lang-en" checked style="display:none!important">
    <div style="text-align:center;margin:0 0 18px">
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">
        Langue / Language
      </div>
      <label for="mysifa-lang-fr" style="cursor:pointer;margin:0 8px;display:inline-block;vertical-align:middle" title="Français">{_EMAIL_FLAG_FR}</label>
      <label for="mysifa-lang-en" style="cursor:pointer;margin:0 8px;display:inline-block;vertical-align:middle" title="English">{_EMAIL_FLAG_GB}</label>
    </div>
    <style type="text/css">
      .mysifa-em-fr {{ display:none !important; }}
      #mysifa-lang-fr:checked ~ .mysifa-em-en {{ display:none !important; }}
      #mysifa-lang-fr:checked ~ .mysifa-em-fr {{ display:block !important; }}
    </style>"""


def _rfq_email_body_block(
    *,
    demande: dict,
    user: dict,
    lang: str,
    portail_lien: str,
) -> str:
    from app.services.expe_email_i18n import expe_rfq_email_strings, expe_type_envoi_label

    cp = (demande.get("code_postal_destination") or "—").strip()
    poids = demande.get("poids_total_kg")
    nb_pal = demande.get("nb_palette")
    type_raw = (demande.get("type_envoi") or "messagerie").strip()
    contraintes = (demande.get("contraintes") or "").strip()
    user_nom = user.get("nom") or user.get("email") or user.get("identifiant") or "SIFA"
    s = expe_rfq_email_strings(lang, cp=cp, user_nom=user_nom)
    type_envoi = expe_type_envoi_label(type_raw, lang)

    detail_rows: list[tuple[str, str]] = [
        (s["type_label"], f"<span style=\"color:#0891b2\">{_esc(type_envoi)}</span>"),
    ]
    if poids is not None and str(poids).strip() != "":
        detail_rows.append((s["weight_label"], f"{_esc(poids)} kg"))
    if nb_pal is not None and str(nb_pal).strip() != "":
        detail_rows.append((s["pallets_label"], _esc(nb_pal)))
    if contraintes:
        detail_rows.append((s["constraints_label"], _esc(contraintes)))

    detail_table = _email_detail_table(detail_rows)
    cp_highlight = f"""
    <div style="background:rgba(34,211,238,.10);border:1px solid rgba(34,211,238,.28);border-radius:12px;
                padding:16px 20px;margin:0 0 22px;text-align:center">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#0891b2;font-weight:800">
        {_esc(s["cp_label"])}
      </div>
      <div style="font-size:26px;font-weight:800;color:#0f172a;margin-top:6px;letter-spacing:-.5px">{_esc(cp)}</div>
    </div>"""

    cta = ""
    lien = (portail_lien or "").strip()
    if lien:
        lang_q = f"{lien}{'&' if '?' in lien else '?'}lang={lang}"
        cta = f"""
    <div style="margin:24px 0 8px;text-align:center">
      <a href="{_esc(lang_q)}" style="background:#22d3ee;color:#0a0e17;font-weight:800;font-size:14px;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">
        {_esc(s["cta"])}
      </a>
    </div>"""

    return f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">{_esc(s["hello"])}</p>
    <p style="margin:0 0 22px;font-size:14px;color:#475569;line-height:1.65">{s["intro"]}</p>
    {cp_highlight}
    {detail_table}
    <p style="margin:0 0 6px;font-size:14px;color:#475569;line-height:1.65">{s["ask"]}</p>
    <p style="margin:0;font-size:13px;color:#94a3b8;line-height:1.6">{_esc(s["hint"])}</p>
    {cta}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      {_esc(s["regards"])}<br>
      <strong style="color:#0f172a;font-size:14px">{_esc(user_nom)}</strong><br>
      {_esc(s["service"])}
    </p>"""


def email_expe_rfq_transport(
    *,
    demande: dict,
    user: dict,
    portail_lien: str,
) -> tuple[str, str]:
    """Sujet et corps HTML — demande de tarif transport (MyExpé → transporteur, FR/EN)."""
    from app.services.expe_email_i18n import expe_rfq_email_strings

    cp = (demande.get("code_postal_destination") or "—").strip()
    lien = (portail_lien or "").strip()
    s_fr = expe_rfq_email_strings("fr", cp=cp, user_nom="")
    s_en = expe_rfq_email_strings("en", cp=cp, user_nom="")

    fr_body = _rfq_email_body_block(demande=demande, user=user, lang="fr", portail_lien=lien)
    en_body = _rfq_email_body_block(demande=demande, user=user, lang="en", portail_lien=lien)

    picker = _email_lang_picker_html()
    inner = (
        f"{picker}"
        f'<div class="mysifa-em-fr">{fr_body}</div>'
        f'<div class="mysifa-em-en">{en_body}</div>'
    )

    subject = f"Demande de tarif transport / Transport quote — SIFA — {cp}"

    body = email_mysifa_layout(
        subtitle="Demande de tarif / Transport quote",
        body_html=inner,
        cta_href=None,
        cta_label=None,
        footer_note=f"{s_fr['footer']} / {s_en['footer']}",
        footer_contact=True,
    )
    return subject, body


def email_mysifa_layout_light(
    *,
    subtitle: str,
    body_html: str,
    cta_href: str | None = None,
    cta_label: str | None = None,
    footer_note: str | None = None,
    footer_contact: bool = False,
    copy_link_label: str = "Si le bouton ne fonctionne pas, copiez ce lien :",
) -> str:
    """Enveloppe HTML email MySifa — version light, neutre, compatible Outlook/Gmail/iOS Mail."""
    cta_block = ""
    if cta_href and cta_label:
        cta_block = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:28px auto 8px">
      <tr>
        <td align="center" bgcolor="#0891b2" style="background:#0891b2;border-radius:10px">
          <a href="{_esc(cta_href)}" style="display:inline-block;padding:14px 32px;color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:.2px;font-family:'Segoe UI',Arial,sans-serif">{_esc(cta_label)}</a>
        </td>
      </tr>
    </table>
    <p style="margin:12px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;text-align:center;word-break:break-all">
      {_esc(copy_link_label)}<br>
      <a href="{_esc(cta_href)}" style="font-family:Consolas,'Courier New',monospace;font-size:11px;color:#0891b2;text-decoration:none">{_esc(cta_href)}</a>
    </p>"""

    contact_block = ""
    if footer_contact:
        contact_block = """
    <p style="margin:18px 0 0;font-size:12px;color:#64748b;line-height:1.7;text-align:center">
      <strong style="color:#0f172a">SIFA — Roubaix (59)</strong><br>
      <a href="tel:+33320690101" style="color:#0891b2;text-decoration:none">03 20 69 01 01</a>
      &nbsp;·&nbsp;
      <a href="mailto:expeditions@sifa.pro" style="color:#0891b2;text-decoration:none">expeditions@sifa.pro</a>
    </p>"""

    foot = footer_note or f"MySifa — {_esc(public_base_url())}"

    return f"""<div style="background:#f1f5f9;padding:24px 12px">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" width="600" style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;font-family:'Segoe UI',Arial,sans-serif">
    <tr>
      <td style="padding:24px 36px;border-bottom:1px solid #e2e8f0">
        <div style="font-size:18px;line-height:1.3;letter-spacing:-.2px;font-family:'Segoe UI',Arial,sans-serif">
          <span style="color:#0f172a;font-weight:800">SIFA</span>
          <span style="color:#0f172a;font-weight:600"> {_esc(subtitle)}</span>
          <span style="color:#94a3b8;font-weight:500"> — via <span style="color:#0891b2;font-weight:700">MySifa</span></span>
        </div>
      </td>
    </tr>
    <tr>
      <td style="padding:32px 36px 28px;font-size:14px;color:#334155;line-height:1.65">
        {body_html}
        {cta_block}
        {contact_block}
        <p style="margin:22px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;border-top:1px solid #e2e8f0;padding-top:16px;text-align:center">
          {foot}
        </p>
      </td>
    </tr>
  </table>
</div>"""


def _localize_unite(unite: str | None, lang: str) -> str:
    """Localise l'unité affichée dans les lignes (fallback raisonnable si custom)."""
    u = (unite or "").strip().lower()
    if u in ("", "unité", "unite", "label", "labels", "étiquette", "etiquette", "étiquettes", "etiquettes"):
        return "labels" if lang == "en" else "étiquettes"
    if u in ("mille", "milliers"):
        return "thousand" if lang == "en" else "mille"
    if u in ("bobine", "bobines", "roll", "rolls"):
        return "rolls" if lang == "en" else "bobines"
    return unite or ""


def _format_number(value, lang: str) -> str:
    """Formate un nombre pour affichage email :
       - les entiers (ou floats sans partie décimale) → sans .0
       - séparateur de milliers : espace insécable en français, virgule en anglais.
    """
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    if n.is_integer():
        s = f"{int(n):,}"
    else:
        s = f"{n:,.2f}".rstrip("0").rstrip(".")
    if lang == "en":
        return s
    # FR : espace insécable comme séparateur, virgule comme décimale
    return s.replace(",", " ").replace(".", ",")


def _ao_invitation_email_strings(lang: str, *, reference: str, titre: str, nom: str) -> dict[str, str]:
    """Textes email invitation AO (FR/EN), single-lang."""
    nom_esc = _esc(nom)
    ref_esc = _esc(reference)
    titre_esc = _esc(titre)
    titre_suffix = f" — {titre_esc}" if titre else ""
    if lang == "en":
        return {
            "subtitle": "Quote request",
            "hello": f"Hello {nom_esc or 'Sir/Madam'},",
            "intro": (
                f"You are invited to submit a quote for the request "
                f"<strong style=\"color:#0f172a\">{ref_esc}</strong>{titre_suffix}."
            ),
            "th_ref": "Reference",
            "th_qty": "Quantity",
            "th_labels_roll": "Labels / roll",
            "no_lines": "No line items for now.",
            "deadline_label": "Reply by",
            "cta": "Submit your quote / more details",
            "copy_link": "If the button does not work, copy this link:",
            "footer": "This link is personal and secure. Do not share it.",
            "subject": f"[SIFA] Quote request — {reference}" + (f" — {titre}" if titre else ""),
        }
    return {
        "subtitle": "Demande de prix",
        "hello": f"Bonjour {nom_esc or 'Madame, Monsieur'},",
        "intro": (
            f"Vous êtes invité à soumettre une offre pour la demande de prix "
            f"<strong style=\"color:#0f172a\">{ref_esc}</strong>{titre_suffix}."
        ),
        "th_ref": "Référence",
        "th_qty": "Quantité",
        "th_labels_roll": "Étiq. / bobine",
        "no_lines": "Aucune ligne détaillée pour le moment.",
        "deadline_label": "Date limite",
        "cta": "Soumettre votre offre / Voir le détail",
        "copy_link": "Si le bouton ne fonctionne pas, copiez ce lien :",
        "footer": "Ce lien est personnel et sécurisé. Ne le partagez pas.",
        "subject": f"[SIFA] Demande de prix — {reference}" + (f" — {titre}" if titre else ""),
    }


def email_invitation_ao(
    ao: dict,
    fournisseur: dict,
    lien_portail: str,
    lignes: list[dict],
) -> tuple[str, str]:
    """Sujet et corps HTML pour l'invitation fournisseur (single-lang d'apr&egrave;s `fournisseur['langue']`)."""
    reference = ao.get("reference") or ""
    titre = ao.get("titre") or ""
    nom = fournisseur.get("nom_fournisseur") or ""
    date_limite = ao.get("date_limite") or ""
    lang_raw = (str(fournisseur.get("langue") or "fr")).strip().lower()
    lang = "en" if lang_raw == "en" else "fr"

    s = _ao_invitation_email_strings(lang, reference=reference, titre=titre, nom=nom)

    # Tableau des lignes
    rows_html = ""
    for ln in lignes:
        labels_roll = ln.get("etiquettes_par_bobine")
        labels_roll_str = _esc(_format_number(labels_roll, lang)) if labels_roll is not None else "&mdash;"
        unite_loc = _localize_unite(ln.get("unite"), lang)
        qty_str = _esc(_format_number(ln.get("quantite"), lang))
        rows_html += (
            f"<tr>"
            f"<td style=\"padding:12px 14px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a;font-weight:600\">{_esc(ln.get('ref_produit'))}</td>"
            f"<td style=\"padding:12px 14px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569;text-align:right;white-space:nowrap\">{qty_str} {_esc(unite_loc)}</td>"
            f"<td style=\"padding:12px 14px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569;text-align:right\">{labels_roll_str}</td>"
            f"</tr>"
        )
    if not rows_html:
        rows_html = (
            f"<tr><td colspan=\"3\" style=\"padding:18px;font-size:13px;color:#94a3b8;text-align:center\">"
            f"{s['no_lines']}</td></tr>"
        )

    # Pavé deadline (table pour Outlook)
    deadline_block = ""
    if date_limite:
        deadline_block = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px">
      <tr>
        <td style="padding:14px 18px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.55px;font-weight:700">{_esc(s['deadline_label'])}</td>
        <td style="padding:14px 18px;font-size:15px;color:#0f172a;font-weight:800;text-align:right">{_esc(date_limite)}</td>
      </tr>
    </table>"""

    inner = f"""
    <p style="margin:0 0 12px;font-size:15px;color:#0f172a;font-weight:700">{s['hello']}</p>
    <p style="margin:0 0 24px;font-size:14px;color:#475569;line-height:1.65">{s['intro']}</p>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse:separate;border-spacing:0;margin:0 0 22px;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">
      <thead>
        <tr style="background:#f1f5f9">
          <th align="left" style="padding:11px 14px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#64748b;font-weight:700">{s['th_ref']}</th>
          <th align="right" style="padding:11px 14px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#64748b;font-weight:700">{s['th_qty']}</th>
          <th align="right" style="padding:11px 14px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#64748b;font-weight:700">{s['th_labels_roll']}</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    {deadline_block}"""

    subject = s["subject"]
    body = email_mysifa_layout_light(
        subtitle=s["subtitle"],
        body_html=inner,
        cta_href=lien_portail,
        cta_label=s["cta"],
        footer_note=s["footer"],
        footer_contact=True,
        copy_link_label=s["copy_link"],
    )
    return subject, body


def _unite_quotation_label(unite: str | None) -> str:
    u = (unite or "mille").strip().lower()
    if u == "bobine":
        return "Par bobine"
    return "Au mille"


def _format_quotation_email(rep: dict | None) -> str:
    if not rep:
        return "—"
    q = rep.get("quotation")
    if q is None:
        q = rep.get("prix_unitaire")
    if q is None:
        return "—"
    try:
        qf = float(q)
    except (TypeError, ValueError):
        return "—"
    devise = (rep.get("devise") or "EUR").strip().upper()
    if devise not in ("EUR", "USD"):
        devise = "EUR"
    return f"{qf:.4g} {devise}"


def _fiche_technique_link(ref_produit: str | None, produits_by_ref: dict[str, int]) -> str:
    ref = (ref_produit or "").strip()
    if not ref:
        return "—"
    produit_id = produits_by_ref.get(ref.lower())
    if not produit_id:
        return "—"
    url = f"{public_base_url()}/api/ao/produits/{produit_id}/export"
    return (
        f'<a href="{_esc(url)}" style="color:#0891b2;font-weight:600;text-decoration:none">'
        f"Fiche technique</a>"
    )


def email_accuse_reception(
    ao: dict,
    fournisseur: dict,
    lignes: list[dict],
    reponses: list[dict],
    *,
    produits_by_ref: dict[str, int] | None = None,
) -> tuple[str, str]:
    """Sujet et corps HTML — accusé de réception envoyé au responsable interne."""
    reference = ao.get("reference") or ""
    titre = ao.get("titre") or ""
    nom = fournisseur.get("nom_fournisseur") or ""
    produits_map = produits_by_ref or {}

    rep_by_ligne = {int(r["ligne_id"]): r for r in reponses if r.get("ligne_id") is not None}
    rows_html = ""
    for ln in lignes:
        lid = ln.get("id")
        rep = rep_by_ligne.get(int(lid)) if lid is not None else None
        delai = rep.get("delai_jours") if rep else None
        quotation_s = _format_quotation_email(rep)
        unite_s = _unite_quotation_label(rep.get("unite_quotation") if rep else None)
        delai_s = str(delai) if delai is not None else "—"
        fiche_s = _fiche_technique_link(ln.get("ref_produit"), produits_map)
        rows_html += (
            f"<tr>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px\">{_esc(ln.get('ref_produit'))}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right\">{_esc(ln.get('quantite'))} {_esc(ln.get('unite') or '')}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right\">{_esc(quotation_s)}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px\">{_esc(unite_s)}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right\">{_esc(delai_s)}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px\">{fiche_s}</td>"
            f"</tr>"
        )
    if not rows_html:
        rows_html = (
            "<tr><td colspan=\"6\" style=\"padding:12px;color:#94a3b8\">Aucune ligne.</td></tr>"
        )

    ao_id = ao.get("id")
    ao_link = ""
    if ao_id:
        ao_url = f"{public_base_url()}/ao"
        ao_link = (
            f'<p style="margin:0 0 16px;font-size:13px;color:#475569">'
            f'<a href="{_esc(ao_url)}" style="color:#0891b2;font-weight:600;text-decoration:none">'
            f"Ouvrir la demande dans MySifa</a></p>"
        )

    subject = f"[MySifa] Réponse reçue — {reference} — {nom}"
    body = f"""<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:24px 32px">
    <div style="font-size:20px;font-weight:700;color:#22d3ee">MySifa</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px">Réponse fournisseur</div>
  </div>
  <div style="padding:32px">
    <p style="margin:0 0 20px;font-size:14px;color:#0f172a;line-height:1.6">
      Le fournisseur <strong>{_esc(nom)}</strong> a soumis une offre pour <strong>{_esc(reference)}</strong>.
    </p>
    <p style="margin:0 0 20px;font-size:13px;color:#475569">{_esc(titre)}</p>
    <table style="width:100%;border-collapse:collapse;margin:0 0 24px">
      <thead>
        <tr style="background:#f1f5f9">
          <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#64748b">Réf.</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;color:#64748b">Qté</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;color:#64748b">Quotation</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#64748b">Unité</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;color:#64748b">Délai (j)</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#64748b">Fiche</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    {ao_link}
    <p style="margin:0;font-size:13px;color:#475569">La fiche technique ouvre le détail produit (connexion MySifa requise).</p>
  </div>
</div>"""
    return subject, body


def _expe_label_transporteur(nom: str | None, email: str | None) -> str:
    """Libellé affiché : nom du transporteur, email entre parenthèses si distinct."""
    n = (nom or "").strip()
    e = (email or "").strip()
    if n and e and n.lower() != e.lower():
        return f"{n} ({e})"
    return n or e or "Transporteur"


def email_expe_reponse_recue(
    *,
    demande: dict,
    nom_transporteur: str,
    email_transporteur: str | None = None,
    prix: float,
    delai_jours: int,
    commentaire: str | None,
) -> tuple[str, str]:
    """Sujet et corps HTML — notification interne 'réponse transporteur reçue' (MyExpé)."""
    cp = demande.get("code_postal_destination") or ""
    type_envoi = demande.get("type_envoi") or ""
    poids = demande.get("poids_total_kg")
    nb_pal = demande.get("nb_palette")
    contraintes = demande.get("contraintes") or ""
    demande_id = demande.get("id")
    label = _expe_label_transporteur(nom_transporteur, email_transporteur)

    prix_s = f"{float(prix):.2f} €"
    delai_s = f"J+{int(delai_jours)}"

    subject = f"[MySifa] Réponse transporteur — Demande #{demande_id} — {label}"
    expe_url = f"{public_base_url()}/expe"
    inner = f"""
    <p style="margin:0 0 14px;color:#0f172a">
      Le transporteur <strong>{_esc(label)}</strong> a répondu à la demande <strong>#{_esc(demande_id)}</strong>.
    </p>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;margin:0 0 16px">
      <div style="font-size:13px;color:#64748b;line-height:1.7">
        Destination : <strong style="color:#0f172a">{_esc(cp)}</strong><br>
        Type d'envoi : <strong style="color:#0f172a">{_esc(type_envoi)}</strong><br>
        {('Poids : <strong style="color:#0f172a">'+_esc(poids)+' kg</strong><br>') if poids is not None else ''}
        {('Palettes : <strong style="color:#0f172a">'+_esc(nb_pal)+'</strong><br>') if nb_pal is not None else ''}
        {('Contraintes : '+_esc(contraintes)+'<br>') if contraintes else ''}
      </div>
    </div>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px">
      <tr>
        <td style="background:rgba(34,211,238,.10);border:1px solid rgba(34,211,238,.25);border-radius:10px;padding:10px 14px">
          <div style="font-size:11px;color:#0891b2;text-transform:uppercase;letter-spacing:.5px;font-weight:800">Prix HT</div>
          <div style="font-size:16px;color:#0f172a;font-weight:900">{_esc(prix_s)}</div>
        </td>
        <td width="12"></td>
        <td style="background:rgba(52,211,153,.10);border:1px solid rgba(52,211,153,.25);border-radius:10px;padding:10px 14px">
          <div style="font-size:11px;color:#059669;text-transform:uppercase;letter-spacing:.5px;font-weight:800">Délai</div>
          <div style="font-size:16px;color:#0f172a;font-weight:900">{_esc(delai_s)}</div>
        </td>
      </tr>
    </table>
    {f'<p style="margin:0 0 8px;color:#475569"><strong>Commentaire</strong><br>{_esc(commentaire)}</p>' if commentaire else ''}"""
    body = email_mysifa_layout(
        subtitle="Réponse transporteur reçue",
        body_html=inner,
        cta_href=expe_url,
        cta_label="Ouvrir MyExpé",
    )
    return subject, body


def email_expe_devis_confirmation(
    *,
    demande: dict,
    reponse: dict,
    depart: dict,
    user: dict,
) -> tuple[str, str]:
    """Sujet et corps HTML — confirmation transporteur : sa proposition de
    devis a été retenue, voici le récap de la mission. Envoyé au transporteur
    après clic sur « Retenir » côté MyExpé.
    """
    cp = (demande.get("code_postal_destination") or "—").strip()
    ref_dem = (demande.get("reference") or "").strip()
    client = (demande.get("client") or depart.get("client") or "").strip()
    type_envoi = (demande.get("type_envoi") or "").strip()
    poids = demande.get("poids_total_kg")
    nb_pal = demande.get("nb_palette")
    contraintes = (demande.get("contraintes") or "").strip()
    date_enl = (depart.get("date_enlevement") or "").strip()[:10]
    nom_trp = (reponse.get("nom_transporteur") or "Transporteur").strip()
    prix = reponse.get("prix")
    delai = reponse.get("delai_jours")
    commentaire = (reponse.get("commentaire") or "").strip()
    user_nom = (
        user.get("nom") or user.get("email") or user.get("identifiant") or "SIFA"
    )

    detail_rows: list[tuple[str, str]] = []
    if ref_dem:
        detail_rows.append(("Référence devis", _esc(ref_dem)))
    if client:
        detail_rows.append(("Client final", _esc(client)))
    detail_rows.append(("Destination (CP)", f"<strong style=\"color:#0f172a\">{_esc(cp)}</strong>"))
    if date_enl:
        detail_rows.append(("Date d'enlèvement prévue", _esc(date_enl)))
    if type_envoi:
        detail_rows.append(("Type d'envoi", _esc(type_envoi)))
    if poids not in (None, ""):
        detail_rows.append(("Poids total", f"{_esc(poids)} kg"))
    if nb_pal not in (None, ""):
        detail_rows.append(("Nombre de palettes", _esc(nb_pal)))
    if prix not in (None, ""):
        try:
            prix_s = f"{float(prix):.2f} €"
        except (TypeError, ValueError):
            prix_s = _esc(prix)
        detail_rows.append(("Prix retenu", f"<strong style=\"color:#0f172a\">{prix_s}</strong>"))
    if delai not in (None, ""):
        try:
            delai_s = f"J+{int(delai)}"
        except (TypeError, ValueError):
            delai_s = _esc(delai)
        detail_rows.append(("Délai annoncé", _esc(delai_s)))
    if contraintes:
        detail_rows.append(("Contraintes", _esc(contraintes)))
    if commentaire:
        detail_rows.append(("Votre commentaire", _esc(commentaire)))

    detail_table = _email_detail_table(detail_rows)

    inner = f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">
      Bonjour {_esc(nom_trp)},
    </p>
    <p style="margin:0 0 18px;font-size:14px;color:#475569;line-height:1.65">
      Nous vous confirmons que votre proposition a été
      <strong style="color:#0891b2">retenue</strong> pour le transport ci-dessous.
      Merci de bien vouloir organiser l'enlèvement selon les modalités indiquées et
      de nous confirmer la prise en charge par retour de mail.
    </p>
    {detail_table}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      Cordialement,<br>
      <strong style="color:#0f172a;font-size:14px">{_esc(user_nom)}</strong><br>
      Service Expéditions — SIFA
    </p>"""

    subject = f"Confirmation transport SIFA — {cp}"
    if ref_dem:
        subject = f"Confirmation transport SIFA — {ref_dem} — {cp}"

    body = email_mysifa_layout(
        subtitle="Proposition retenue",
        body_html=inner,
        cta_href=None,
        cta_label=None,
        footer_contact=True,
    )
    return subject, body



def email_offre_retenue(ao: dict, fourni: dict, message_perso: str | None = None) -> tuple[str, str]:
    """Email envoye au fournisseur retenu apres cloture de l'AO."""
    langue = (fourni.get("langue") or "fr").lower()
    ref = ao.get("reference") or ""
    titre = ao.get("titre") or "Appel d\'offres"
    nom_fournisseur = fourni.get("nom_fournisseur") or ""

    if langue == "en":
        subject = f"Your quote has been selected — {ref}"
        greeting = f"Dear {nom_fournisseur},"
        body_html = (
            f"<p>{greeting}</p>"
            f"<p>We are pleased to inform you that your quote for the RFQ <strong>{ref}</strong> ({titre}) has been selected.</p>"
            + (f"<p>{message_perso}</p>" if message_perso else "")
            + "<p>Our team will contact you shortly to finalize the order.</p>"
            + "<p>Best regards,</p>"
        )
    else:
        subject = f"Votre offre a ete retenue — {ref}"
        greeting = f"Bonjour {nom_fournisseur},"
        body_html = (
            f"<p>{greeting}</p>"
            f"<p>Nous avons le plaisir de vous informer que votre offre pour l\'appel d\'offres <strong>{ref}</strong> ({titre}) a ete retenue.</p>"
            + (f"<p>{message_perso}</p>" if message_perso else "")
            + "<p>Notre equipe reviendra vers vous rapidement pour finaliser la commande.</p>"
            + "<p>Cordialement,</p>"
        )

    body = email_mysifa_layout(
        title_html=subject,
        content_html=body_html,
        footer_contact=True,
    )
    return subject, body


def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    reply_to: str | None = None,
    cc: str | list[str] | None = None,
) -> bool:
    """
    Envoie un email HTML via SMTP (STARTTLS) + fallback Microsoft Graph (si configuré).
    Retourne True si OK, False sinon — ne lève jamais d'exception.
    """
    recipients = [to] if isinstance(to, str) else [str(x) for x in to]
    recipients = [r.strip() for r in recipients if r and str(r).strip()]
    if not recipients:
        logger.error("send_email: aucun destinataire")
        return False

    cc_list: list[str] = []
    if cc:
        cc_list = [cc] if isinstance(cc, str) else [str(x) for x in cc]
        cc_list = [c.strip() for c in cc_list if c and str(c).strip()]

    def _can_smtp() -> bool:
        return bool(SMTP_HOST)

    def _can_graph() -> bool:
        return bool(MS_TENANT_ID and MS_CLIENT_ID and MS_CLIENT_SECRET and MS_SENDER_UPN)

    def _graph_get_token() -> str:
        now = time.time()
        if _GRAPH_TOKEN["access_token"] and float(_GRAPH_TOKEN["expires_at"] or 0) - now > 60:
            return str(_GRAPH_TOKEN["access_token"])

        url = f"https://login.microsoftonline.com/{MS_TENANT_ID}/oauth2/v2.0/token"
        data = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": MS_CLIENT_ID,
                "client_secret": MS_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
            }
        ).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
        j = json.loads(raw)
        tok = j.get("access_token")
        exp = j.get("expires_in", 3600)
        if not tok:
            raise RuntimeError("Token Graph manquant")
        _GRAPH_TOKEN["access_token"] = tok
        try:
            _GRAPH_TOKEN["expires_at"] = now + float(exp)
        except Exception:
            _GRAPH_TOKEN["expires_at"] = now + 3600.0
        return str(tok)

    def _send_graph() -> None:
        token = _graph_get_token()
        url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(MS_SENDER_UPN)}/sendMail"
        payload: dict = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in recipients],
            },
            "saveToSentItems": "true",
        }
        if cc_list:
            payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_list
            ]
        if reply_to:
            payload["message"]["replyTo"] = [{"emailAddress": {"address": reply_to}}]

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=20) as r:
            if getattr(r, "status", 202) not in (200, 201, 202):
                raise RuntimeError("Graph sendMail refusé")

    def _send_smtp() -> None:
        msg = MIMEMultipart("alternative")
        from_header = (
            f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
            if SMTP_FROM_NAME
            else SMTP_FROM
        )
        msg["From"] = from_header
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        context = ssl.create_default_context()
        all_rcpt = list(recipients) + list(cc_list)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            if SMTP_USER and SMTP_PASS:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.sendmail(SMTP_FROM, all_rcpt, msg.as_string())

    try:
        provider = (SUPPORT_EMAIL_PROVIDER or "").strip().lower()
        # Si provider est forcé, on l'essaie en premier, sinon on privilégie Graph si dispo (prod).
        if provider in {"smtp", "graph"}:
            order = [provider, "graph" if provider == "smtp" else "smtp"]
        else:
            order = ["graph", "smtp"]

        last_err: Exception | None = None
        for p in order:
            try:
                if p == "graph":
                    if not _can_graph():
                        raise RuntimeError("Graph non configuré (MS_* manquants)")
                    _send_graph()
                else:
                    if not _can_smtp():
                        raise RuntimeError("SMTP non configuré (SMTP_HOST manquant)")
                    _send_smtp()
                last_err = None
                break
            except Exception as e:
                last_err = e
                continue

        if last_err is not None:
            raise last_err
        return True
    except Exception as exc:
        logger.error("Échec envoi email: %s", exc, exc_info=True)
        return False
