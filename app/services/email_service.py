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
) -> str:
    """Enveloppe HTML email MySifa (dark header, typo Segoe UI)."""
    cta_block = ""
    if cta_href and cta_label:
        cta_block = f"""
    <div style="margin:26px 0 8px;text-align:center">
      <a href="{_esc(cta_href)}" style="background:#22d3ee;color:#0a0e17;font-weight:800;font-size:14px;padding:12px 24px;border-radius:10px;text-decoration:none;display:inline-block">
        {_esc(cta_label)}
      </a>
    </div>
    <p style="margin:10px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;text-align:center;word-break:break-all">
      Si le bouton ne fonctionne pas :<br>
      <span style="font-family:ui-monospace,monospace;font-size:11px">{_esc(cta_href)}</span>
    </p>"""
    foot = footer_note or f"Notification automatique MySifa — {_esc(public_base_url())}"
    return f"""<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:22px 28px">
    <div style="font-size:20px;font-weight:800;color:#22d3ee;letter-spacing:-.3px">MySifa</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:4px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">{_esc(subtitle)}</div>
  </div>
  <div style="padding:28px 32px;font-size:14px;color:#334155;line-height:1.65">
    {body_html}
    {cta_block}
    <p style="margin:20px 0 0;font-size:11px;color:#94a3b8;line-height:1.6;border-top:1px solid #e2e8f0;padding-top:14px">
      {foot}
    </p>
  </div>
</div>"""


def email_invitation_ao(
    ao: dict,
    fournisseur: dict,
    lien_portail: str,
    lignes: list[dict],
) -> tuple[str, str]:
    """Sujet et corps HTML pour l'invitation fournisseur à répondre à un AO."""
    reference = ao.get("reference") or ""
    titre = ao.get("titre") or ""
    nom = fournisseur.get("nom_fournisseur") or ""
    date_limite = ao.get("date_limite") or ""

    rows_html = ""
    for ln in lignes:
        rows_html += (
            f"<tr>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a\">{_esc(ln.get('ref_produit'))}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569\">{_esc(ln.get('designation'))}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569;text-align:right\">{_esc(ln.get('quantite'))} {_esc(ln.get('unite') or '')}</td>"
            f"</tr>"
        )
    if not rows_html:
        rows_html = (
            "<tr><td colspan=\"3\" style=\"padding:12px;font-size:13px;color:#94a3b8\">"
            "Aucune ligne détaillée pour le moment.</td></tr>"
        )

    limite_block = ""
    if date_limite:
        limite_block = (
            f"<p style=\"margin:0 0 24px;font-size:13px;color:#475569\">"
            f"Date limite de réponse : <strong>{_esc(date_limite)}</strong></p>"
        )

    subject = f"[MySifa] Demande de prix — {reference} — {titre}"
    body = f"""<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:24px 32px">
    <div style="font-size:20px;font-weight:700;color:#22d3ee;letter-spacing:-0.5px">MySifa</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px">Demande de prix</div>
  </div>
  <div style="padding:32px">
    <p style="margin:0 0 16px;font-size:14px;color:#0f172a">Bonjour {_esc(nom)},</p>
    <p style="margin:0 0 24px;font-size:14px;color:#475569;line-height:1.6">
      Vous êtes invité à soumettre une offre pour la demande de prix <strong>{_esc(reference)}</strong> — {_esc(titre)}.
    </p>
    <table style="width:100%;border-collapse:collapse;margin:0 0 24px">
      <thead>
        <tr style="background:#f1f5f9">
          <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Réf.</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Désignation</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Quantité</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    {limite_block}
    <div style="margin:32px 0;text-align:center">
      <a href="{_esc(lien_portail)}" style="background:#22d3ee;color:#0a0e17;font-weight:700;font-size:14px;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">
        Accéder à la demande de prix
      </a>
    </div>
    <p style="margin:0;font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:16px;line-height:1.6">
      Ce lien est personnel et sécurisé. Ne le partagez pas.<br>
      MySifa — {_esc(public_base_url())}
    </p>
  </div>
</div>"""
    return subject, body


def email_accuse_reception(
    ao: dict,
    fournisseur: dict,
    lignes: list[dict],
    reponses: list[dict],
) -> tuple[str, str]:
    """Sujet et corps HTML — accusé de réception envoyé au responsable interne."""
    reference = ao.get("reference") or ""
    titre = ao.get("titre") or ""
    nom = fournisseur.get("nom_fournisseur") or ""

    rep_by_ligne = {int(r["ligne_id"]): r for r in reponses if r.get("ligne_id") is not None}
    rows_html = ""
    for ln in lignes:
        lid = ln.get("id")
        rep = rep_by_ligne.get(int(lid)) if lid is not None else None
        prix = rep.get("prix_unitaire") if rep else None
        delai = rep.get("delai_jours") if rep else None
        prix_s = f"{prix:.2f} €" if prix is not None else "—"
        delai_s = str(delai) if delai is not None else "—"
        rows_html += (
            f"<tr>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px\">{_esc(ln.get('ref_produit'))}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569\">{_esc(ln.get('designation'))}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right\">{_esc(ln.get('quantite'))} {_esc(ln.get('unite') or '')}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right\">{_esc(prix_s)}</td>"
            f"<td style=\"padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:right\">{_esc(delai_s)}</td>"
            f"</tr>"
        )
    if not rows_html:
        rows_html = (
            "<tr><td colspan=\"5\" style=\"padding:12px;color:#94a3b8\">Aucune ligne.</td></tr>"
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
          <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#64748b">Désignation</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;color:#64748b">Qté</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;color:#64748b">Prix</th>
          <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;color:#64748b">Délai</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p style="margin:0;font-size:13px;color:#475569">Connectez-vous à MySifa pour consulter la comparaison des prix.</p>
  </div>
</div>"""
    return subject, body


def email_expe_reponse_recue(
    *,
    demande: dict,
    nom_transporteur: str,
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

    prix_s = f"{float(prix):.2f} €"
    delai_s = f"J+{int(delai_jours)}"

    subject = f"[MySifa] Réponse transporteur — Demande #{demande_id} — {nom_transporteur}"
    expe_url = f"{public_base_url()}/expe"
    inner = f"""
    <p style="margin:0 0 14px;color:#0f172a">
      Le transporteur <strong>{_esc(nom_transporteur)}</strong> a répondu à la demande <strong>#{_esc(demande_id)}</strong>.
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
