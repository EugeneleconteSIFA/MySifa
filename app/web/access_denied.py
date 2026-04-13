"""Page HTML commune lorsque le rôle ne permet pas l'application."""

from __future__ import annotations

import html as html_lib
from typing import Optional

from fastapi.responses import HTMLResponse

_DEFAULT_DETAIL = (
    "Vous n'avez pas les droits d'accès à cette application. "
    "Merci de contacter un administrateur si vous pensez qu'il s'agit d'une erreur."
)


def access_denied_response(
    application_label: str,
    *,
    detail: Optional[str] = None,
    status_code: int = 403,
) -> HTMLResponse:
    """Réponse 403 lisible dans le navigateur (pas du JSON brut)."""
    msg = _DEFAULT_DETAIL if detail is None else (detail or _DEFAULT_DETAIL)
    safe_label = html_lib.escape(str(application_label or "Application"))
    safe_msg = html_lib.escape(str(msg))
    body = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0f172a">
<title>Accès refusé — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<style>
body{{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;
  display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:24px;box-sizing:border-box;}}
.box{{max-width:520px;background:#1e293b;border:1px solid #334155;border-radius:16px;padding:28px 32px;box-sizing:border-box;}}
h1{{font-size:20px;margin:0 0 14px;color:#f87171;font-weight:800;}}
p{{font-size:15px;line-height:1.6;margin:0 0 18px;color:#cbd5e1;}}
.meta{{font-size:13px;color:#94a3b8;margin-bottom:20px;}}
.meta span.app{{font-weight:700;color:#22d3ee;}}
.actions{{display:flex;flex-wrap:wrap;gap:10px;}}
a.btn{{display:inline-block;padding:10px 18px;background:#0891b2;color:#fff;text-decoration:none;border-radius:10px;font-weight:600;font-size:14px;}}
a.btn:hover{{filter:brightness(1.08);}}
a.btn2{{display:inline-block;padding:10px 18px;background:transparent;color:#94a3b8;text-decoration:none;border-radius:10px;font-weight:600;font-size:14px;border:1px solid #475569;}}
a.btn2:hover{{border-color:#22d3ee;color:#22d3ee;}}
</style>
</head>
<body>
<div class="box">
  <h1>Accès refusé</h1>
  <p>{safe_msg}</p>
  <p class="meta">Application : <span class="app">{safe_label}</span></p>
  <div class="actions">
    <a class="btn" href="/">Retour au portail MySifa</a>
    <a class="btn2" href="javascript:history.back()">Page précédente</a>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=body, status_code=status_code)
