"""MySifa — Envoi d'emails (SMTP + fallback Microsoft Graph).

Contrat: `send_email()` retourne True/False et **ne lève jamais**.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import smtplib
import ssl
import time
import json
import urllib.error
import urllib.parse
import urllib.request
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

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

# Mention d'ouverture (RGPD art. 13) : le destinataire doit savoir que l'email
# est instrumenté. Volontairement en pied de mail, dans la même typo grise que
# la signature automatique — informer sans transformer l'email en avertissement.
_SUIVI_NOTE = {
    "fr": "Cet email comporte un indicateur d'ouverture : SIFA est informé de sa consultation.",
    "en": "This email includes an open indicator: SIFA is notified when it is viewed.",
}


def _suivi_blocs(pixel_url: str | None, lang: str = "fr") -> tuple[str, str]:
    """Retourne (note_html, pixel_html) — vides si aucun suivi n'est posé.

    Les deux vont ensemble : pas de pixel sans mention, pas de mention sans
    pixel. Les dissocier produirait soit un suivi silencieux, soit un
    avertissement mensonger.
    """
    if not pixel_url:
        return "", ""
    texte = _SUIVI_NOTE.get("en" if str(lang).lower().startswith("en") else "fr")
    note = (
        '<p style="margin:8px 0 0;font-size:10px;color:#cbd5e1;line-height:1.5;'
        f'text-align:center">{_esc(texte)}</p>'
    )
    pixel = (
        f'<img src="{_esc(pixel_url)}" width="1" height="1" border="0" alt="" '
        'style="display:block;width:1px;height:1px;border:0;outline:none;'
        'opacity:0;overflow:hidden">'
    )
    return note, pixel



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
    pixel_url: str | None = None,
    lang: str = "fr",
    marque: str = "MySifa",
) -> str:
    """Enveloppe HTML email MySifa (dark header, typo Segoe UI).

    `marque` est le nom affiche en tete et en pied. Il vaut « MySifa » pour
    tout ce qui part vers un utilisateur interne, et « SIFA » pour ce qui part
    vers un tiers — un transporteur repond a SIFA, pas a un logiciel dont il
    n'a pas a connaitre le nom.
    """
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
    foot = footer_note or f"Notification automatique {_esc(marque)} — {_esc(public_base_url())}"
    suivi_note, suivi_pixel = _suivi_blocs(pixel_url, lang)
    return f"""<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:24px 32px">
    <div style="font-size:20px;font-weight:800;color:#22d3ee;letter-spacing:-.3px">{_esc(marque)}</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">{_esc(subtitle)}</div>
  </div>
  <div style="padding:32px;font-size:14px;color:#334155;line-height:1.65">
    {body_html}
    {cta_block}
    {contact_block}
    <p style="margin:20px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;border-top:1px solid #e2e8f0;padding-top:14px;text-align:center">
      {foot}
    </p>
    {suivi_note}
  </div>
  {suivi_pixel}
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
    <input type="radio" name="sifa-lang" id="sifa-lang-fr" style="display:none!important">
    <input type="radio" name="sifa-lang" id="sifa-lang-en" checked style="display:none!important">
    <div style="text-align:center;margin:0 0 18px">
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">
        Langue / Language
      </div>
      <label for="sifa-lang-fr" style="cursor:pointer;margin:0 8px;display:inline-block;vertical-align:middle" title="Français">{_EMAIL_FLAG_FR}</label>
      <label for="sifa-lang-en" style="cursor:pointer;margin:0 8px;display:inline-block;vertical-align:middle" title="English">{_EMAIL_FLAG_GB}</label>
    </div>
    <style type="text/css">
      .sifa-em-fr {{ display:none !important; }}
      #sifa-lang-fr:checked ~ .sifa-em-en {{ display:none !important; }}
      #sifa-lang-fr:checked ~ .sifa-em-fr {{ display:block !important; }}
    </style>"""


def _rfq_email_body_block(
    *,
    demande: dict,
    user: dict,
    lang: str,
    portail_lien: str,
) -> str:
    from app.services.expe_email_i18n import (
        expe_rfq_email_strings,
        expe_type_envoi_label,
        expe_type_palette_label,
    )

    cp = (demande.get("code_postal_destination") or "—").strip()
    poids = demande.get("poids_total_kg")
    nb_pal = demande.get("nb_palette")
    type_raw = (demande.get("type_envoi") or "messagerie").strip()
    type_palette_raw = (demande.get("type_palette") or "").strip()
    contraintes = (demande.get("contraintes") or "").strip()
    user_nom = user.get("nom") or user.get("email") or user.get("identifiant") or "SIFA"
    s = expe_rfq_email_strings(lang, cp=cp, user_nom=user_nom)
    type_envoi = expe_type_envoi_label(type_raw, lang)
    type_palette_label = expe_type_palette_label(type_palette_raw, lang)

    detail_rows: list[tuple[str, str]] = [
        (s["type_label"], f"<span style=\"color:#0891b2\">{_esc(type_envoi)}</span>"),
    ]
    if poids is not None and str(poids).strip() != "":
        detail_rows.append((s["weight_label"], f"{_esc(poids)} kg"))
    if nb_pal is not None and str(nb_pal).strip() != "":
        detail_rows.append((s["pallets_label"], _esc(nb_pal)))
    if type_palette_label:
        detail_rows.append((s["pallet_type_label"], _esc(type_palette_label)))
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

    # Les trois etapes en table et non en <ol> : Outlook rend les listes avec
    # des marges qu'il decide lui-meme, et la puce numerotee disparait sur
    # certains clients. Une table avec pastille dessinee tient partout.
    def _etape(num: str, texte: str) -> str:
        return (
            "<tr>"
            "<td style=\"padding:0 12px 12px 0;vertical-align:top;width:26px\">"
            "<div style=\"width:24px;height:24px;border-radius:12px;background:#0891b2;"
            "color:#ffffff;font-size:12px;font-weight:800;text-align:center;line-height:24px\">"
            f"{num}</div></td>"
            "<td style=\"padding:0 0 12px;vertical-align:top;font-size:14px;color:#475569;"
            f"line-height:1.6\">{texte}</td>"
            "</tr>"
        )

    how_block = f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;margin:0 0 4px">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#0891b2;font-weight:800;margin-bottom:14px">
        {_esc(s["how_title"])}
      </div>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse">
        <tbody>
          {_etape("1", s["step1"])}
          {_etape("2", s["step2"])}
          {_etape("3", s["step3"])}
        </tbody>
      </table>
      <p style="margin:2px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">{_esc(s["hint"])}</p>
    </div>"""

    exclusive_block = f"""
    <div style="background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.35);border-radius:10px;
                padding:12px 16px;margin:18px 0 0;font-size:13px;color:#475569;line-height:1.6">
      {s["exclusive"]}
    </div>"""

    return f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">{_esc(s["hello"])}</p>
    <p style="margin:0 0 22px;font-size:14px;color:#475569;line-height:1.65">{s["intro"]}</p>
    {cp_highlight}
    {detail_table}
    <p style="margin:0 0 16px;font-size:14px;color:#475569;line-height:1.65">{s["ask"]}</p>
    {how_block}
    {cta}
    {exclusive_block}
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
    pixel_url: str | None = None,
    langue: str | None = None,
    relance: bool = False,
    message_perso: str | None = None,
    date_limite: str | None = None,
) -> tuple[str, str]:
    """Sujet et corps HTML — demande de tarif transport (MyExpé → transporteur).

    `langue` vaut 'fr' ou 'en' : le mail part alors dans cette seule langue.
    Toute autre valeur (dont None) conserve l'ancien comportement bilingue avec
    sélecteur de drapeaux — c'est le cas des transporteurs dont on ne connaît
    pas encore la langue, où doubler vaut mieux que se tromper.

    `relance` ne change pas le corps du message mais son enveloppe : sujet
    préfixé et bandeau de rappel. Renvoyer un texte identique à l'original
    laisserait le destinataire croire à un doublon technique.
    """
    from app.services.expe_email_i18n import expe_rfq_email_strings

    cp = (demande.get("code_postal_destination") or "—").strip()
    lien = (portail_lien or "").strip()
    lang = str(langue or "").strip().lower()[:2]
    mono = lang if lang in ("fr", "en") else None

    s_fr = expe_rfq_email_strings("fr", cp=cp, user_nom="")
    s_en = expe_rfq_email_strings("en", cp=cp, user_nom="")

    entete = ""
    if relance:
        txt = (
            "Reminder — we have not received your quote yet."
            if mono == "en"
            else "Rappel — nous n'avons pas encore reçu votre tarif."
        )
        entete += (
            '<div style="background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.35);'
            'border-radius:10px;padding:12px 16px;margin:0 0 20px;font-size:13px;'
            f'font-weight:700;color:#92400e;text-align:center">{_esc(txt)}</div>'
        )
    if message_perso:
        entete += (
            '<div style="background:rgba(34,211,238,.08);border:1px solid rgba(34,211,238,.28);'
            'border-radius:10px;padding:14px 16px;margin:0 0 20px;font-size:14px;color:#0f172a;'
            f'line-height:1.6;white-space:pre-wrap">{_esc(message_perso)}</div>'
        )
    if date_limite:
        lbl = "Reply expected before" if mono == "en" else "Réponse attendue avant le"
        entete += (
            '<p style="margin:0 0 18px;font-size:13px;text-align:center;color:#475569">'
            f'{_esc(lbl)} <strong style="color:#0f172a">{_esc(date_limite)}</strong></p>'
        )

    if mono:
        inner = entete + _rfq_email_body_block(
            demande=demande, user=user, lang=mono, portail_lien=lien
        )
        s = s_en if mono == "en" else s_fr
        subtitle = s["subtitle"]
        footer_note = s["footer"]
        subject = s["subject"]
        if relance:
            subject = ("Reminder — " if mono == "en" else "Relance — ") + subject
    else:
        fr_body = _rfq_email_body_block(demande=demande, user=user, lang="fr", portail_lien=lien)
        en_body = _rfq_email_body_block(demande=demande, user=user, lang="en", portail_lien=lien)
        inner = (
            f"{entete}{_email_lang_picker_html()}"
            f'<div class="sifa-em-fr">{fr_body}</div>'
            f'<div class="sifa-em-en">{en_body}</div>'
        )
        subtitle = "Demande de tarif / Transport quote"
        footer_note = f"{s_fr['footer']} / {s_en['footer']}"
        subject = f"Demande de tarif transport / Transport quote — SIFA — {cp}"
        if relance:
            subject = "Relance / Reminder — " + subject

    body = email_mysifa_layout(
        subtitle=subtitle,
        body_html=inner,
        cta_href=None,
        cta_label=None,
        footer_note=footer_note,
        footer_contact=True,
        pixel_url=pixel_url,
        marque="SIFA",
        # La mention d'ouverture RGPD suit la langue du mail. En bilingue elle
        # reste en français : il faut trancher, et c'est la langue par défaut.
        lang=mono or "fr",
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
    pixel_url: str | None = None,
    lang: str = "fr",
) -> str:
    """Enveloppe HTML email MySifa — version light, neutre, compatible Outlook/Gmail/iOS Mail.

    `pixel_url` : image 1x1 de suivi d'ouverture, ajoutée en toute fin de corps.
    Placée APRES le pied de page pour qu'un client mail qui tronque le message
    (« ... afficher le message complet » de Gmail) ne coupe pas le contenu utile
    juste avant elle. Sans `alt` ni dimensions visibles : un lecteur d'écran ne
    doit rien annoncer, et un client qui bloque les images ne doit pas afficher
    de cadre vide.
    """
    cta_block = ""
    if cta_href and cta_label:
        cta_block = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:28px auto 8px">
      <tr>
        <td align="center" bgcolor="#0891b2" style="background:#0891b2;border-radius:10px;padding:15px 34px;mso-padding-alt:15px 34px">
          <a href="{_esc(cta_href)}" style="color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:.2px;font-family:'Segoe UI',Arial,sans-serif;line-height:1">{_esc(cta_label)}</a>
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

    suivi_note, pixel_block = _suivi_blocs(pixel_url, lang)

    # #fffffe et non #ffffff : Outlook n'inverse que le blanc PUR en mode
    # sombre. Un blanc a un point pres, invisible a l'oeil, echappe au filtre.
    return f"""<div class="ms-bg" style="background:#f1f5f9;padding:24px 12px">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" width="600" class="ms-card" bgcolor="#fffffe" style="max-width:600px;margin:0 auto;background:#fffffe;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;font-family:'Segoe UI',Arial,sans-serif">
    <tr>
      <td style="padding:24px 36px;border-bottom:1px solid #e2e8f0">
        <div class="ms-title" style="font-size:18px;line-height:1.3;letter-spacing:-.2px;font-family:'Segoe UI',Arial,sans-serif">
          <span style="color:#0f172a;font-weight:800">SIFA</span>
          <span style="color:#0f172a;font-weight:600"> {_esc(subtitle)}</span>
          <span style="color:#94a3b8;font-weight:500"> — via <span style="color:#0891b2;font-weight:700">MySifa</span></span>
        </div>
      </td>
    </tr>
    <tr>
      <td class="ms-text" style="padding:32px 36px 28px;font-size:14px;color:#334155;line-height:1.65">
        {body_html}
        {cta_block}
        {contact_block}
        <p style="margin:22px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;border-top:1px solid #e2e8f0;padding-top:16px;text-align:center">
          {foot}
        </p>
        {suivi_note}
      </td>
    </tr>
  </table>
  {pixel_block}
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
    pixel_url: str | None = None,
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
        pixel_url=pixel_url,
        lang=lang,
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
        qty_s = _format_number(ln.get("quantite"), "fr")
        unite_ligne = _localize_unite(ln.get("unite"), "fr")
        rows_html += (
            f"<tr>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px\">{_esc(ln.get('ref_produit'))}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right;white-space:nowrap\">{_esc(qty_s)} {_esc(unite_ligne)}</td>"
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
    retention_comment: str | None = None,
    retention_file_name: str | None = None,
    pixel_url: str | None = None,
) -> tuple[str, str]:
    """Sujet et corps HTML — confirmation transporteur : sa proposition de
    devis a été retenue, voici le récap de la mission. Envoyé au transporteur
    après clic sur « Retenir » côté MyExpé.
    """
    from app.services.expe_email_i18n import expe_type_palette_label

    cp = (demande.get("code_postal_destination") or "—").strip()
    ref_dem = (demande.get("reference") or "").strip()
    client = (demande.get("client") or depart.get("client") or "").strip()
    type_envoi = (demande.get("type_envoi") or "").strip()
    type_palette_raw = (demande.get("type_palette") or "").strip()
    type_palette_label = expe_type_palette_label(type_palette_raw, "fr")
    poids = demande.get("poids_total_kg")
    nb_pal = demande.get("nb_palette")
    contraintes = (demande.get("contraintes") or "").strip()
    date_enl = (depart.get("date_enlevement") or "").strip()[:10]
    nom_trp = (reponse.get("nom_transporteur") or "Transporteur").strip()
    prix = reponse.get("prix")
    delai = reponse.get("delai_jours")
    commentaire = (reponse.get("commentaire") or "").strip()
    retention_msg = (retention_comment or "").strip()
    retention_file = (retention_file_name or "").strip()
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
    if type_palette_label:
        detail_rows.append(("Type de palette", _esc(type_palette_label)))
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

    retention_block = ""
    if retention_msg:
        retention_block += (
            "<div style=\"background:rgba(34,211,238,.08);border:1px solid rgba(34,211,238,.28);"
            "border-radius:10px;padding:14px 16px;margin:0 0 18px\">"
            "<div style=\"font-size:11px;color:#0891b2;text-transform:uppercase;"
            "letter-spacing:.5px;font-weight:800;margin-bottom:6px\">Message SIFA</div>"
            f"<div style=\"font-size:14px;color:#0f172a;line-height:1.6;white-space:pre-wrap\">"
            f"{_esc(retention_msg)}</div></div>"
        )
    if retention_file:
        retention_block += (
            "<p style=\"margin:0 0 18px;font-size:13px;color:#475569\">"
            "Un fichier est joint à ce courriel : "
            f"<strong style=\"color:#0f172a\">{_esc(retention_file)}</strong>.</p>"
        )

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
    {retention_block}
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
        footer_note="SIFA — Service expéditions",
        footer_contact=True,
        pixel_url=pixel_url,
        marque="SIFA",
    )
    return subject, body



def email_offre_retenue(
    ao: dict,
    fourni: dict,
    message_perso: str | None = None,
    pixel_url: str | None = None,
) -> tuple[str, str]:
    """Email envoyé au fournisseur retenu après clôture de l'AO.

    Corrigé le 30/07/2026 : l'appel au layout passait `title_html=` et
    `content_html=`, deux arguments que `email_mysifa_layout()` n'a jamais
    acceptés. Chaque clôture levait donc un TypeError, avalé par le `try/except`
    de `cloturer_ao` — le fournisseur retenu n'a jamais reçu cet email, et seule
    une ligne de warning dans les logs le signalait.
    """
    langue = (fourni.get("langue") or "fr").lower()
    ref = ao.get("reference") or ""
    titre = ao.get("titre") or "Appel d\'offres"
    nom_fournisseur = _esc(fourni.get("nom_fournisseur") or "")
    perso = f"<p>{_esc(message_perso)}</p>" if message_perso else ""

    if langue == "en":
        subject = f"Your quote has been selected — {ref}"
        subtitle = "Quote selected"
        body_html = (
            f"<p>Dear {nom_fournisseur},</p>"
            f"<p>We are pleased to inform you that your quote for the RFQ "
            f"<strong>{_esc(ref)}</strong> ({_esc(titre)}) has been selected.</p>"
            + perso
            + "<p>Our team will contact you shortly to finalize the order.</p>"
            + "<p>Best regards,</p>"
        )
    else:
        subject = f"Votre offre a été retenue — {ref}"
        subtitle = "Offre retenue"
        body_html = (
            f"<p>Bonjour {nom_fournisseur},</p>"
            f"<p>Nous avons le plaisir de vous informer que votre offre pour "
            f"l'appel d'offres <strong>{_esc(ref)}</strong> ({_esc(titre)}) a été retenue.</p>"
            + perso
            + "<p>Notre équipe reviendra vers vous rapidement pour finaliser la commande.</p>"
            + "<p>Cordialement,</p>"
        )

    body = email_mysifa_layout(
        subtitle=subtitle,
        body_html=body_html,
        footer_contact=True,
        pixel_url=pixel_url,
        lang=langue,
    )
    return subject, body


def email_message_fournisseur(
    reference: str,
    message: str,
    lien_portail: str,
    langue: str = "fr",
    pixel_url: str | None = None,
) -> tuple[str, str]:
    """Email annonçant un message interne déposé pour le fournisseur.

    Reprend l'enveloppe MySifa au lieu du `<div>` brut d'origine : même
    identité visuelle que l'invitation, bouton d'accès au portail, et suivi
    d'ouverture — c'est en pratique l'email de relance d'un AO sans réponse.
    """
    en = str(langue).lower().startswith("en")
    if en:
        subject = f"[MySifa] New message — {reference}"
        subtitle = "New message"
        intro = (
            f"<p>You have received a message regarding RFQ "
            f"<strong>{_esc(reference)}</strong>.</p>"
        )
        cta = "Open the request"
    else:
        subject = f"[MySifa] Nouveau message — {reference}"
        subtitle = "Nouveau message"
        intro = (
            f"<p>Vous avez reçu un message concernant l'appel d'offres "
            f"<strong>{_esc(reference)}</strong>.</p>"
        )
        cta = "Accéder à la demande"

    corps = (
        intro
        + '<div style="margin:18px 0;padding:14px 16px;background:#f8fafc;'
        'border-left:3px solid #0891b2;border-radius:0 8px 8px 0;font-size:14px;'
        f'color:#334155;line-height:1.65;white-space:pre-wrap">{_esc(message)}</div>'
    )
    body = email_mysifa_layout_light(
        subtitle=subtitle,
        body_html=corps,
        cta_href=lien_portail,
        cta_label=cta,
        footer_contact=True,
        pixel_url=pixel_url,
        lang="en" if en else "fr",
    )
    return subject, body


class _SendPreflightError(Exception):
    """Sentinelle interne : erreur *avant* toute tentative reelle d'envoi.
    Signale a l'orchestrateur qu'il est sur qu'aucun message n'est parti
    et qu'il peut donc essayer le provider suivant sans risque de doublon.
    """


_EMAIL_DOC_HEAD = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<!-- Rendu clair force. Sans ces declarations, Outlook.com, Apple Mail et
     Outlook mobile en mode sombre inversent les couleurs : le fond blanc vire
     au gris ardoise et les gris de texte deviennent illisibles. L'email SIFA
     doit ressortir identique chez tout le monde. -->
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<style>
  :root { color-scheme: light only; supported-color-schemes: light only; }
  /* Outlook reecrit les couleurs inline en mode sombre et marque les elements
     modifies : data-ogsb pour un fond, data-ogsc pour un texte. On y repose
     les valeurs claires, seul moyen de reprendre la main sur ce client. */
  [data-ogsb] .ms-bg   { background-color: #f1f5f9 !important; }
  [data-ogsb] .ms-card { background-color: #fffffe !important; }
  [data-ogsc] .ms-title { color: #0f172a !important; }
  [data-ogsc] .ms-text  { color: #334155 !important; }
  [data-ogsc] .ms-muted { color: #64748b !important; }
</style>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9">
"""


def _wrap_email_document(html_body: str) -> str:
    """Enveloppe un corps HTML dans un document complet a rendu clair force.

    Applique au seul point de passage de TOUS les emails (`send_email`) plutot
    qu'a chaque gabarit : un email construit ailleurs dans l'app en beneficie
    sans qu'on ait a y penser. Un corps deja complet est laisse tel quel.
    """
    corps = str(html_body or "")
    if "<html" in corps[:400].lower():
        return corps
    return _EMAIL_DOC_HEAD + corps + "\n</body>\n</html>"


def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    reply_to: str | None = None,
    cc: str | list[str] | None = None,
    attachments: list[dict] | None = None,
    from_upn: str | None = None,
) -> bool:
    """
    Envoie un email HTML via Microsoft Graph (prod SIFA) ou SMTP.

    `from_upn` : boite expeditrice a utiliser pour CE message, au lieu de la
    boite globale `MS_SENDER_UPN`. Un module dont les mails engagent un
    service (MyExpe : les demandes de tarif partent du service expeditions)
    doit expedier depuis SA boite, pas depuis celle de la personne qui a
    clique. Requiert que l'application Graph ait la permission d'envoyer
    depuis cette boite ; si l'envoi Graph echoue, le fallback SMTP part avec
    l'adresse SMTP_FROM habituelle.
    Retourne True si OK, False sinon — ne leve jamais d'exception.

    Les provides sont essayes dans l'ordre `SUPPORT_EMAIL_PROVIDER` puis l'autre.
    IMPORTANT : le fallback automatique entre les deux providers a ete restreint
    pour ne pas envoyer le meme email deux fois. Si un provider est configure
    et que l'appel reseau part reellement (i.e. autre chose qu'une erreur de
    config avant emission), on ne bascule PAS sur l'autre provider — le message
    pourrait avoir ete accepte cote serveur pendant qu'on lisait une reponse
    incomplete, et un fallback deposerait une seconde copie chez le destinataire.

    `attachments` : liste de {filename, content(bytes), mime?} — inline uniquement.
    """
    expediteur = (from_upn or "").strip() or MS_SENDER_UPN

    recipients = [to] if isinstance(to, str) else [str(x) for x in to]
    recipients = [r.strip() for r in recipients if r and str(r).strip()]
    if not recipients:
        logger.error("send_email: aucun destinataire")
        return False

    html_body = _wrap_email_document(html_body)

    cc_list: list[str] = []
    if cc:
        cc_list = [cc] if isinstance(cc, str) else [str(x) for x in cc]
        cc_list = [c.strip() for c in cc_list if c and str(c).strip()]

    atts: list[dict] = []
    for a in attachments or []:
        try:
            name = str(a.get("filename") or "fichier").strip() or "fichier"
            content = a.get("content")
            if content is None:
                continue
            if not isinstance(content, (bytes, bytearray)):
                logger.warning("send_email: pj '%s' ignoree (content non bytes)", name)
                continue
            mime = (a.get("mime") or "").strip()
            if not mime:
                mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            atts.append({"filename": name, "content": bytes(content), "mime": mime})
        except Exception:
            continue

    def _can_smtp() -> bool:
        return bool(SMTP_HOST)

    def _can_graph() -> bool:
        return bool(MS_TENANT_ID and MS_CLIENT_ID and MS_CLIENT_SECRET and expediteur)

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
        # Token fetch : si ca echoue on est sur qu'aucun message n'a ete envoye
        # → l'appelant peut relever une SendPreflightError qui autorise le
        # fallback SMTP. Une fois le POST sendMail lance, toute erreur est
        # traitee comme "peut-etre parti" et interdit le fallback.
        try:
            token = _graph_get_token()
        except Exception as e:
            raise _SendPreflightError(str(e)) from e

        url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(expediteur)}/sendMail"
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
        if atts:
            payload["message"]["attachments"] = [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": a["filename"],
                    "contentType": a["mime"],
                    "contentBytes": base64.b64encode(a["content"]).decode("ascii"),
                }
                for a in atts
            ]

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if getattr(r, "status", 202) not in (200, 201, 202):
                    raise RuntimeError("Graph sendMail refuse")
        except urllib.error.HTTPError as e:
            # 403 (acces refuse) et 404 (boite inconnue) : Graph a REFUSE la
            # requete, aucun message n'a ete depose. C'est un preflight, pas
            # un "peut-etre parti" — le fallback SMTP est donc sur, et sans
            # lui une permission Mail.Send manquante sur la boite du service
            # ferait partir toutes les demandes de tarif en echec.
            if e.code in (403, 404):
                if from_upn:
                    logger.error(
                        "send_email: Graph refuse d'envoyer depuis '%s' (HTTP %s). "
                        "Verifier la permission Mail.Send de l'application sur "
                        "cette boite (et l'ApplicationAccessPolicy du tenant).",
                        expediteur,
                        e.code,
                    )
                raise _SendPreflightError(f"Graph HTTP {e.code} sur {expediteur}") from e
            raise

    def _send_smtp() -> None:
        # Root multipart mixed pour supporter attachments + alternative HTML.
        if atts:
            root = MIMEMultipart("mixed")
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(html_body, "html", "utf-8"))
            root.attach(alt)
            for a in atts:
                maintype, _, subtype = a["mime"].partition("/")
                part = MIMEBase(maintype or "application", subtype or "octet-stream")
                part.set_payload(a["content"])
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=a["filename"],
                )
                root.attach(part)
            msg = root
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(html_body, "html", "utf-8"))

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

        context = ssl.create_default_context()
        all_rcpt = list(recipients) + list(cc_list)
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                # A partir de sendmail() on est en "peut-etre parti" — toute
                # erreur remontee ne doit plus declencher de fallback.
                smtp.sendmail(SMTP_FROM, all_rcpt, msg.as_string())
        except smtplib.SMTPConnectError as e:
            # Impossible de se connecter → on sait qu'aucun mail n'est parti,
            # on autorise le fallback via la sentinelle _SendPreflightError.
            raise _SendPreflightError(str(e)) from e

    try:
        provider = (SUPPORT_EMAIL_PROVIDER or "").strip().lower()
        # Si provider est force, on l'essaie en premier, sinon on privilegie Graph si dispo (prod).
        if provider in {"smtp", "graph"}:
            order = [provider, "graph" if provider == "smtp" else "smtp"]
        else:
            order = ["graph", "smtp"]

        last_err: Exception | None = None
        for idx, p in enumerate(order):
            try:
                if p == "graph":
                    if not _can_graph():
                        # Non configure → on peut essayer l'autre provider sans risque.
                        raise _SendPreflightError("Graph non configure (MS_* manquants)")
                    _send_graph()
                else:
                    if not _can_smtp():
                        raise _SendPreflightError("SMTP non configure (SMTP_HOST manquant)")
                    _send_smtp()
                last_err = None
                break
            except _SendPreflightError as e:
                # Erreur avant emission reelle : on peut passer au provider suivant.
                last_err = e
                continue
            except Exception as e:
                # Erreur pendant/apres emission : le message a peut-etre ete
                # accepte cote serveur. Ne pas tenter le second provider pour
                # eviter le doublon chez le destinataire — on remonte l'echec.
                logger.warning(
                    "send_email: %s a leve apres tentative d'envoi (%s) — pas de fallback pour eviter le doublon",
                    p,
                    e,
                )
                last_err = e
                break

        if last_err is not None:
            raise last_err
        return True
    except Exception as exc:
        logger.error("Echec envoi email: %s", exc, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# MyCalendrier — invitation à une réunion
# ---------------------------------------------------------------------------


def _bouton_reponse(href: str, libelle: str, fond: str, bord: str, texte: str) -> str:
    """Un bouton de réponse, en table : Outlook ignore un <a> qui fait le malin."""
    return (
        '<td align="center" style="padding:0 4px">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">'
        f'<tr><td align="center" bgcolor="{fond}" '
        f'style="background:{fond};border:1px solid {bord};border-radius:9px;'
        f'padding:13px 6px;mso-padding-alt:13px 6px">'
        f'<a href="{_esc(href)}" style="color:{texte};'
        "font-size:13px;font-weight:700;text-decoration:none;line-height:1;"
        f'font-family:\'Segoe UI\',Arial,sans-serif">{_esc(libelle)}</a>'
        "</td></tr></table></td>"
    )


def email_invitation_reunion(
    *,
    titre: str,
    jour_num: str,
    mois_court: str,
    jour_semaine: str,
    heures: str,
    duree: str = "",
    lieu: str = "",
    visio: str = "",
    organisateur: str = "",
    participants: str = "",
    note: str = "",
    lien_app: str = "",
    lien_reponse: str = "",
    annulation: bool = False,
) -> tuple[str, str]:
    """Sujet + corps HTML d'une invitation (ou d'une annulation) de réunion.

    Un invité externe reçoit trois boutons de réponse pointant sur son lien
    signé : accepter depuis le mail, sans compte MySifa ni détour. Un invité
    interne reçoit le bouton « Ouvrir dans MySifa » du gabarit.

    Tout est en tables : le gabarit `email_mysifa_layout_light` est le seul qui
    tienne dans Outlook — la version `email_mysifa_layout` s'étalait sur toute
    la largeur de la fenêtre et transformait le bouton en texte surligné.
    """
    accent = "#dc2626" if annulation else "#0891b2"
    fond_pave = "#fef2f2" if annulation else "#f0f9ff"
    bord_pave = "#fecaca" if annulation else "#bae6fd"

    bandeau = ""
    if annulation:
        bandeau = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="margin:0 0 20px;background:#fef2f2;border:1px solid #fecaca;border-radius:10px">'
            '<tr><td style="padding:13px 16px;font-size:13px;font-weight:700;color:#b91c1c">'
            "Cette réunion est annulée — vous pouvez retirer le créneau de votre agenda."
            "</td></tr></table>"
        )

    # Pavé date : le quantième en gros à gauche, l'horaire à droite.
    pave = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
      style="margin:0 0 22px;background:{fond_pave};border:1px solid {bord_pave};border-radius:12px">
      <tr>
        <td width="88" align="center" valign="middle" style="padding:16px 10px 16px 16px">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="72"
            bgcolor="{accent}" style="background:{accent};border-radius:10px">
            <tr><td align="center" style="padding:9px 4px 3px;font-size:24px;line-height:1;
              font-weight:800;color:#ffffff;font-family:'Segoe UI',Arial,sans-serif">{_esc(jour_num)}</td></tr>
            <tr><td align="center" style="padding:0 4px 9px;font-size:11px;line-height:1.2;
              font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:.6px;
              font-family:'Segoe UI',Arial,sans-serif">{_esc(mois_court)}</td></tr>
          </table>
        </td>
        <td valign="middle" style="padding:16px 16px 16px 6px">
          <div style="font-size:14px;font-weight:800;color:#0f172a">{_esc(jour_semaine[:1].upper() + jour_semaine[1:])}</div>
          <div style="margin-top:3px;font-size:15px;font-weight:700;color:{accent}">{_esc(heures)}</div>
          {f'<div style="margin-top:3px;font-size:12px;color:#64748b">{_esc(duree)}</div>' if duree else ''}
        </td>
      </tr>
    </table>"""

    lignes = []
    for label, valeur, brut in (
        ("Lieu", _esc(lieu), False),
        (
            "Visioconférence",
            f'<a href="{_esc(visio)}" style="color:#0891b2;text-decoration:none">{_esc(visio)}</a>',
            True,
        ),
        ("Organisateur", _esc(organisateur), False),
        ("Participants", _esc(participants), False),
    ):
        source = visio if brut else valeur
        if not source:
            continue
        lignes.append(
            '<tr><td style="padding:9px 0;font-size:12px;color:#64748b;width:140px;'
            f'vertical-align:top">{label}</td>'
            '<td style="padding:9px 0;font-size:13px;color:#0f172a;font-weight:600">'
            f"{valeur}</td></tr>"
        )
    detail = (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="margin:0 0 6px;border-collapse:collapse">{"".join(lignes)}</table>'
        if lignes
        else ""
    )

    note_bloc = ""
    if note:
        note_bloc = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="margin:18px 0 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px">'
            '<tr><td style="padding:14px 16px;font-size:13px;color:#475569;line-height:1.6;'
            f'white-space:pre-line">{_esc(note)}</td></tr></table>'
        )

    rsvp = ""
    if lien_reponse and not annulation:
        sep = "&" if "?" in lien_reponse else "?"
        rsvp = f"""
    <p style="margin:26px 0 10px;font-size:12px;font-weight:700;color:#64748b;
      text-transform:uppercase;letter-spacing:.55px">Votre réponse</p>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
      <tr>
        {_bouton_reponse(f"{lien_reponse}{sep}reponse=accepte", "Accepter", "#0e9f6e", "#0e9f6e", "#ffffff")}
        {_bouton_reponse(f"{lien_reponse}{sep}reponse=peut_etre", "Peut-être", "#fffffe", "#cbd5e1", "#334155")}
        {_bouton_reponse(f"{lien_reponse}{sep}reponse=refuse", "Refuser", "#fffffe", "#fca5a5", "#b91c1c")}
      </tr>
    </table>
    <p style="margin:10px 0 0;font-size:11px;color:#94a3b8;text-align:center">
      Un clic suffit — votre réponse arrive directement dans le calendrier de l'organisateur.
    </p>"""

    inner = f"""
    {bandeau}
    <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#64748b;
      text-transform:uppercase;letter-spacing:.55px">{'Réunion annulée' if annulation else 'Vous êtes invité'}</p>
    <h1 style="margin:0 0 20px;font-size:21px;line-height:1.3;color:#0f172a;font-weight:800">{_esc(titre)}</h1>
    {pave}
    {detail}
    {note_bloc}
    {rsvp}"""

    sujet = ("Réunion annulée — " if annulation else "Invitation — ") + (titre or "Réunion")
    corps = email_mysifa_layout_light(
        subtitle="Calendrier",
        body_html=inner,
        cta_href=None if (annulation or lien_reponse) else (lien_app or None),
        cta_label=None if (annulation or lien_reponse) else "Ouvrir dans MySifa",
        footer_note="Invitation envoyée depuis MyCalendrier — MySifa",
    )
    return sujet, corps
