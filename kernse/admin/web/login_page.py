"""
Kernse-admin — pages HTML de login et de saisie 2FA.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from kernse.admin.config import APP_VERSION, IS_STAGING
from kernse.shared.auth.dependency import SuperadminContext, require_superadmin_no_2fa


router = APIRouter(tags=["auth-ui"])


def _esc(v: object) -> str:
    return (
        str(v)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _shared_head(title: str) -> str:
    return f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} — Kernse Admin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;600;700;800&family=Poppins:wght@900&family=JetBrains+Mono:wght@600;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy:#182444; --orange:#F2652B; --orange-bg:#fce4d6;
    --bg:#f6f4ef; --surf:#fff; --line:#e6e2d7;
    --ink:#182444; --ink-2:#4e5872; --muted:#8b91a4;
    --red:#cf3b32; --red-bg:#f7e2e0; --amber:#bf7d12; --amber-bg:#f6ecd6;
    --r:14px;
    --shadow:0 1px 2px rgba(24,36,68,.05), 0 20px 40px rgba(24,36,68,.10);
    --sans:'Inter Tight',system-ui,sans-serif; --mono:'JetBrains Mono',monospace;
    --brand:'Poppins',var(--sans);
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--ink);font-family:var(--sans);min-height:100vh;display:flex;flex-direction:column}}
  .banner{{background:var(--red);color:#fff;text-align:center;padding:6px;font-weight:800;font-size:12px;letter-spacing:.5px}}
  main{{flex:1;display:flex;align-items:center;justify-content:center;padding:40px 20px}}
  .card{{background:var(--surf);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:36px 40px;max-width:420px;width:100%}}
  .wm{{font-family:var(--brand);font-weight:900;font-size:32px;letter-spacing:-1.4px;color:var(--navy);margin-bottom:6px;text-align:center}}
  .wm em{{color:var(--orange);font-style:normal;margin-left:-3px}}
  .sub{{text-align:center;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:26px;font-weight:800}}
  form{{display:flex;flex-direction:column;gap:14px}}
  label{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:800;color:var(--ink-2);margin-bottom:4px;display:block}}
  input[type=email], input[type=password], input[type=text] {{
    width:100%;padding:12px 16px;border:1px solid var(--line);border-radius:10px;
    background:#fff;color:var(--ink);font-size:14px;font-family:var(--sans);
  }}
  input:focus{{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(242,101,43,.15)}}
  .btn{{background:var(--orange);color:#fff;border:none;padding:12px 20px;border-radius:10px;font-weight:800;font-size:14px;cursor:pointer;font-family:var(--sans);transition:filter .15s}}
  .btn:hover{{filter:brightness(1.05)}}
  .err{{background:var(--red-bg);color:var(--red);padding:10px 14px;border-radius:10px;font-size:13px;font-weight:600;margin-bottom:14px;display:none}}
  .err.on{{display:block}}
  footer{{padding:20px;text-align:center;color:var(--muted);font-size:11px;font-family:var(--mono)}}
  .code-input{{font-family:var(--mono);font-size:22px;text-align:center;letter-spacing:6px}}
</style>
</head><body>
"""


def _staging_banner() -> str:
    if IS_STAGING:
        return '<div class="banner">STAGING — v1</div>'
    return ""


def _footer() -> str:
    return f'<footer>Kernse Admin · v{_esc(APP_VERSION)}</footer></body></html>'


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    expired = "expired" in request.query_params

    err_html = ""
    if expired:
        err_html = '<div class="err on">Session expirée. Reconnectez-vous.</div>'

    html = f"""{_shared_head("Connexion")}
{_staging_banner()}
<main>
  <div class="card">
    <div class="wm">K<em>ernse</em></div>
    <div class="sub">Console plateforme</div>
    {err_html}
    <div class="err" id="err"></div>
    <form id="login-form" method="POST" action="/auth/login">
      <div>
        <label for="email">Email superadmin</label>
        <input type="email" id="email" name="email" required autocomplete="username" autofocus>
      </div>
      <div>
        <label for="password">Mot de passe</label>
        <input type="password" id="password" name="password" required autocomplete="current-password" minlength="12">
      </div>
      <button type="submit" class="btn">Se connecter</button>
    </form>
  </div>
</main>
{_footer()}
<script>
document.getElementById('login-form').addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  const form = ev.target;
  const btn = form.querySelector('button');
  const err = document.getElementById('err');
  err.classList.remove('on');
  btn.disabled = true; btn.textContent = 'Connexion...';
  const body = new FormData(form);
  try {{
    const r = await fetch('/auth/login', {{ method:'POST', body, credentials:'include', redirect:'follow' }});
    if (r.redirected) {{ window.location = r.url; return; }}
    if (!r.ok) {{
      const j = await r.json().catch(()=>({{}}));
      err.textContent = j.detail || 'Identifiants invalides.';
      err.classList.add('on');
      btn.disabled = false; btn.textContent = 'Se connecter';
    }}
  }} catch (e) {{
    err.textContent = e.message || 'Erreur réseau.';
    err.classList.add('on');
    btn.disabled = false; btn.textContent = 'Se connecter';
  }}
}});
</script>
"""
    return HTMLResponse(html)
