"""Nouvel ERP — coque et connexion.

Servi uniquement par son sous-domaine : le middleware `router_hote_erp`
(main.py) réécrit `erp.mysifa.com/<chemin>` en `ERP2_PREFIXE/<chemin>`. Toutes
les URL de l'ERP renvoient la même coque ; la navigation se fait côté client
(`static/erp/erp.js`), qui lit le chemin réel de la barre d'adresse.

La page ne porte que le squelette HTML. Le style vit dans `static/erp/erp.css`,
le comportement dans `static/erp/erp.js` : les deux grossiront avec le design
system de l'ERP, ils n'ont rien à faire dans une chaîne Python.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from config import APP_VERSION, ERP2_PREFIXE, ROLES_ERP2, public_base_url
from app.services.auth_service import get_current_user

router = APIRouter(include_in_schema=False)


def _entete(titre: str) -> str:
    v = f"v{APP_VERSION}"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titre}</title>
<link rel="icon" type="image/png" sizes="32x32" href="/static/erp/erp_icon_32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/erp/erp_icon_16.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/erp/erp_icon_192.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/erp/erp_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v={v}">
<link rel="stylesheet" href="/static/mysifa_sidebar.css?v={v}">
<link rel="stylesheet" href="/static/mysifa_perf.css?v={v}">
<link rel="stylesheet" href="/static/erp/erp.css?v={v}">
<script src="/static/mysifa_perf.js?v={v}"></script>
<script src="/static/mysifa_theme.js?v={v}"></script>
</head>
"""


# Marqueur `mysifa-boutons-off` : l'ERP a sa propre coque, les boutons
# flottants de MySifa (tâche rapide, support, capture de bloc) n'y vont pas.
_CONNEXION = """<body class="erp-connexion">
<!-- mysifa-boutons-off -->
<main class="erp-cx">
  <form class="erp-cx-carte" id="cx" autocomplete="on">
    <div class="erp-cx-marque"><img src="/static/erp/erp_icon_192.png" alt="">ERP</div>
    <p class="erp-cx-sous">SIFA — accès réservé</p>
    <label class="erp-label" for="cx-id">Identifiant ou email</label>
    <input class="erp-input" id="cx-id" name="username" autocomplete="username" required autofocus>
    <label class="erp-label" for="cx-mdp">Mot de passe</label>
    <input class="erp-input" id="cx-mdp" name="password" type="password" autocomplete="current-password" required>
    <p class="erp-cx-erreur" id="cx-err" role="alert"></p>
    <button class="erp-btn erp-btn-accent" type="submit" id="cx-ok">Se connecter</button>
  </form>
</main>
<script>
document.getElementById("cx").addEventListener("submit", async function (e) {
  e.preventDefault();
  var err = document.getElementById("cx-err"), ok = document.getElementById("cx-ok");
  err.textContent = ""; ok.disabled = true;
  try {
    var r = await fetch("/api/auth/login", {
      method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        email: document.getElementById("cx-id").value.trim(),
        password: document.getElementById("cx-mdp").value
      })
    });
    if (r.ok) { location.reload(); return; }
    err.textContent = r.status === 401 ? "Identifiants invalides." : "Connexion impossible — réessayer.";
  } catch (x) {
    err.textContent = "Serveur injoignable.";
  }
  ok.disabled = false;
});
</script>
</body>
</html>
"""

_COQUE = """<body class="erp">
<!-- mysifa-boutons-off -->
<div id="erp-app"></div>
<script>window.ERP_CONFIG = {version: "__V__", mysifa: "__MYSIFA__"};</script>
<script src="/static/erp/erp.js?v=__V__"></script>
</body>
</html>
"""


@router.get(ERP2_PREFIXE, response_class=HTMLResponse)
@router.get(ERP2_PREFIXE + "/{chemin:path}", response_class=HTMLResponse)
def erp2_page(request: Request, chemin: str = ""):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return HTMLResponse(_entete("Connexion — ERP") + _CONNEXION)
        raise
    if user.get("role") not in ROLES_ERP2:
        from app.web.access_denied import access_denied_response
        return access_denied_response(
            "ERP",
            detail="Le nouvel ERP est en construction : accès réservé au super administrateur.",
        )
    return HTMLResponse(_entete("ERP — SIFA") + _COQUE
        .replace("__V__", f"v{APP_VERSION}")
        .replace("__MYSIFA__", public_base_url().replace('"', "")))
