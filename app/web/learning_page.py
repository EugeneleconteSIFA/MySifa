"""MySifa — Page MyLearning (route /learning).

Étape 1 (squelette) : placeholder minimaliste — aucun contenu de formation
n'est encore publié. La page affiche un état vide propre, avec un lien de
retour vers le portail. La coquille visuelle (sidebar, topbar mobile,
lecteur vidéo, quiz, dashboard progression) sera ajoutée à l'étape 2
en même temps que l'admin de création de contenu.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/learning", response_class=HTMLResponse)
def learning_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/learning", status_code=302)
        raise
    html = LEARNING_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    html = html.replace("__USER_NOM__", user.get("nom", ""))
    return HTMLResponse(content=html)


LEARNING_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>MyLearning — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<style>
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;
  --accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--muted:#64748b;
  --accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
*{box-sizing:border-box}
body{
  margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:24px;
}
.wrap{
  max-width:640px;width:100%;
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:40px 32px;
}
.brand{
  font-size:32px;font-weight:800;letter-spacing:.5px;margin-bottom:4px;
}
.brand span{color:var(--accent)}
.sub{
  font-size:11px;color:var(--muted);letter-spacing:1.5px;
  text-transform:uppercase;margin-bottom:28px;
}
h1{
  font-size:22px;font-weight:700;margin:0 0 12px 0;
}
.lead{
  font-size:14px;color:var(--text2);line-height:1.7;margin:0 0 24px 0;
}
.empty{
  padding:24px;border:1px dashed var(--border);border-radius:10px;
  background:var(--bg);color:var(--muted);font-size:13px;line-height:1.6;
  margin-bottom:24px;
}
.empty b{color:var(--text2)}
.actions{display:flex;gap:12px;flex-wrap:wrap}
.btn{
  border-radius:10px;padding:10px 18px;font-weight:700;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;font-family:inherit;font-size:13px;
  transition:filter .15s,color .15s,border-color .15s,background .15s;
  text-decoration:none;display:inline-flex;align-items:center;gap:8px;
}
.btn:hover{filter:brightness(1.05);color:var(--text);border-color:var(--text2)}
.btn-accent{background:var(--accent);color:#0a0e17;border-color:var(--accent)}
.btn-accent:hover{color:#0a0e17;border-color:var(--accent)}
.version{
  margin-top:28px;font-size:10px;color:var(--muted);
  font-family:'JetBrains Mono',ui-monospace,monospace;
  letter-spacing:1px;
}
</style>
</head>
<body>
<div class="wrap">
  <div class="brand">My<span>Learning</span></div>
  <div class="sub">MODULE E-LEARNING SIFA</div>

  <h1>Bonjour __USER_NOM__</h1>
  <p class="lead">
    MyLearning centralise les formations vidéo pour prendre en main les
    outils MySifa selon votre poste. Chaque parcours débloque un ensemble
    de gestes métier — saisie, validation, gestion de stock, expédition
    ou administration.
  </p>

  <div class="empty">
    <b>Aucune formation publiée pour le moment.</b><br>
    Le catalogue de parcours arrive prochainement. Vous serez notifié dès
    la publication du premier parcours.
  </div>

  <div class="actions">
    <a href="/" class="btn btn-accent">Retour au portail</a>
  </div>

  <div class="version">MySifa __V_LABEL__ · MyLearning</div>
</div>
</body>
</html>
"""
