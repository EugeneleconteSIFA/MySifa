"""MySifa — page publique de réponse à une invitation (invité externe).

Une seule page, sans compte ni session : le destinataire arrive par le lien
signé reçu dans l'e-mail d'invitation, voit le créneau et répond. Elle est
volontairement autonome (styles inline, aucun script) — elle s'ouvre aussi bien
depuis un webmail que depuis un téléphone.
"""

from __future__ import annotations

from html import escape


def _bouton(jeton: str, statut: str, libelle: str, couleur: str, actif: bool) -> str:
    bord = couleur if actif else "#e2e8f0"
    fond = couleur if actif else "#ffffff"
    texte = "#ffffff" if actif else "#334155"
    return f"""
      <form method="post" action="/calendrier/invitation/{escape(jeton)}/reponse" style="flex:1;margin:0">
        <input type="hidden" name="statut" value="{escape(statut)}">
        <button type="submit" style="width:100%;padding:13px 10px;border:1px solid {bord};
          border-radius:10px;background:{fond};color:{texte};font-size:13px;font-weight:700;
          font-family:inherit;cursor:pointer">{escape(libelle)}</button>
      </form>"""


def page_invitation(ctx: dict) -> str:
    """ctx : titre, quand, organisateur, lieu, visio, note, statut, jeton, annule."""
    titre = escape(str(ctx.get("titre") or "Réunion"))
    quand = escape(str(ctx.get("quand") or ""))
    organisateur = escape(str(ctx.get("organisateur") or ""))
    lieu = escape(str(ctx.get("lieu") or ""))
    visio = str(ctx.get("visio") or "").strip()
    note = escape(str(ctx.get("note") or ""))
    statut = str(ctx.get("statut") or "en_attente")
    jeton = str(ctx.get("jeton") or "")
    annule = bool(ctx.get("annule"))

    libelles = {
        "accepte": "Vous avez accepté cette invitation.",
        "refuse": "Vous avez décliné cette invitation.",
        "peut_etre": "Vous avez répondu « peut-être ».",
    }
    bandeau = ""
    if annule:
        bandeau = (
            '<div style="margin:0 0 18px;padding:12px 14px;border-radius:10px;'
            'background:#fef2f2;color:#b91c1c;font-weight:700;font-size:13px">'
            "Cette réunion a été annulée par l'organisateur.</div>"
        )
    elif statut in libelles:
        bandeau = (
            '<div style="margin:0 0 18px;padding:12px 14px;border-radius:10px;'
            'background:#ecfeff;color:#0e7490;font-weight:600;font-size:13px">'
            f"{escape(libelles[statut])} Vous pouvez encore changer d'avis.</div>"
        )

    lignes = [("Quand", quand), ("Organisateur", organisateur)]
    if lieu:
        lignes.append(("Lieu", lieu))
    if visio:
        lignes.append(
            ("Visioconférence", f'<a href="{escape(visio)}" style="color:#0891b2">'
                                f"{escape(visio)}</a>")
        )
    detail = "".join(
        '<tr><td style="padding:7px 0;color:#64748b;width:150px;vertical-align:top">'
        f"{k}</td><td style=\"padding:7px 0;color:#0f172a\">{v}</td></tr>"
        for k, v in lignes
    )
    note_bloc = (
        f'<p style="margin:16px 0 0;color:#475569;white-space:pre-line">{note}</p>'
        if note
        else ""
    )
    actions = (
        ""
        if annule
        else '<div style="display:flex;gap:8px;margin-top:22px">'
        + _bouton(jeton, "accepte", "Accepter", "#0e9f6e", statut == "accepte")
        + _bouton(jeton, "peut_etre", "Peut-être", "#d97706", statut == "peut_etre")
        + _bouton(jeton, "refuse", "Refuser", "#dc2626", statut == "refuse")
        + "</div>"
    )

    return f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titre} — Invitation MySifa</title>
</head>
<body style="margin:0;background:#f1f5f9;font-family:'Segoe UI',system-ui,sans-serif">
  <div style="max-width:560px;margin:40px auto;padding:0 16px">
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden">
      <div style="background:#0a0e17;padding:22px 28px">
        <div style="font-size:19px;font-weight:800;color:#22d3ee">MySifa</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:5px;text-transform:uppercase;
          letter-spacing:.6px;font-weight:600">Invitation à une réunion</div>
      </div>
      <div style="padding:28px;font-size:14px;color:#334155;line-height:1.6">
        {bandeau}
        <h1 style="margin:0 0 16px;font-size:19px;color:#0f172a">{titre}</h1>
        <table style="width:100%;border-collapse:collapse;font-size:13px">{detail}</table>
        {note_bloc}
        {actions}
      </div>
    </div>
    <p style="text-align:center;font-size:11px;color:#94a3b8;margin-top:16px">
      Réponse enregistrée dans le calendrier de l'organisateur.
    </p>
  </div>
</body></html>"""
