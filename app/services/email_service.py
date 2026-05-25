"""MySifa — Envoi d'emails SMTP (infrastructure générique)."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import html as html_module

from config import BASE_URL, SMTP_FROM, SMTP_FROM_NAME, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


def _esc(text: object) -> str:
    return html_module.escape(str(text or ""))


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
      MySifa — {_esc(BASE_URL)}
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


def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    reply_to: str | None = None,
    cc: str | list[str] | None = None,
) -> bool:
    """
    Envoie un email HTML via SMTP (STARTTLS).
    Retourne True si OK, False sinon — ne lève jamais d'exception.
    """
    if not SMTP_HOST:
        logger.warning("Email non configuré")
        return False

    recipients = [to] if isinstance(to, str) else [str(x) for x in to]
    recipients = [r.strip() for r in recipients if r and str(r).strip()]
    if not recipients:
        logger.error("send_email: aucun destinataire")
        return False

    try:
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
        if cc:
            cc_list = [cc] if isinstance(cc, str) else [str(x) for x in cc]
            cc_list = [c.strip() for c in cc_list if c and str(c).strip()]
            if cc_list:
                msg["Cc"] = ", ".join(cc_list)
                recipients = list(recipients) + cc_list

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            if SMTP_USER and SMTP_PASS:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.sendmail(SMTP_FROM, recipients, msg.as_string())

        return True
    except Exception as exc:
        logger.error("Échec envoi email: %s", exc, exc_info=True)
        return False
