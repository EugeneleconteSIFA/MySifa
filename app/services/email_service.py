"""MySifa — Envoi d'emails SMTP (infrastructure générique)."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_FROM, SMTP_FROM_NAME, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    reply_to: str | None = None,
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
