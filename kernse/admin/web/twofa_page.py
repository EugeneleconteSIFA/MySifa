"""
Kernse-admin — pages HTML 2FA (setup + verify).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from kernse.admin.config import APP_VERSION, IS_STAGING
from kernse.admin.web.login_page import _esc, _footer, _shared_head, _staging_banner
from kernse.shared.auth.dependency import SuperadminContext, require_superadmin_no_2fa
from kernse.shared.auth.totp import generate_secret, otpauth_uri
from kernse.shared.db.database import platform_db


router = APIRouter(tags=["auth-ui"])


@router.get("/2fa/verify", response_class=HTMLResponse)
def verify_page(
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin_no_2fa),
) -> HTMLResponse:
    """Page de saisie du code 2FA après login."""
    html = f"""{_shared_head("Code 2FA")}
{_staging_banner()}
<main>
  <div class="card">
    <div class="wm">K<em>ernse</em></div>
    <div class="sub">Vérification 2FA</div>
    <p style="text-align:center;color:var(--ink-2);margin-bottom:20px;font-size:14px">
      Ouvrez votre application d'authentification et saisissez le code à 6 chiffres.
    </p>
    <div class="err" id="err"></div>
    <form id="verify-form" method="POST" action="/auth/2fa/verify">
      <div>
        <label for="code">Code à 6 chiffres</label>
        <input type="text" id="code" name="code" required inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" autocomplete="one-time-code" class="code-input" autofocus>
      </div>
      <button type="submit" class="btn">Valider</button>
    </form>
    <p style="text-align:center;margin-top:16px;font-size:12px">
      <a href="/auth/logout" onclick="fetch('/auth/logout',{{method:'POST',credentials:'include'}}).then(()=>location='/login');return false;" style="color:var(--muted);text-decoration:none">Se déconnecter</a>
    </p>
  </div>
</main>
{_footer()}
<script>
document.getElementById('verify-form').addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  const form = ev.target;
  const btn = form.querySelector('button');
  const err = document.getElementById('err');
  err.classList.remove('on');
  btn.disabled = true; btn.textContent = 'Vérification...';
  const body = new FormData(form);
  try {{
    const r = await fetch('/auth/2fa/verify', {{ method:'POST', body, credentials:'include', redirect:'follow' }});
    if (r.redirected) {{ window.location = r.url; return; }}
    if (!r.ok) {{
      const j = await r.json().catch(()=>({{}}));
      err.textContent = j.detail || 'Code invalide.';
      err.classList.add('on');
      btn.disabled = false; btn.textContent = 'Valider';
      form.querySelector('input').value = '';
      form.querySelector('input').focus();
    }}
  }} catch (e) {{
    err.textContent = e.message || 'Erreur réseau.';
    err.classList.add('on');
    btn.disabled = false; btn.textContent = 'Valider';
  }}
}});
</script>
"""
    return HTMLResponse(html)


@router.get("/2fa/setup", response_class=HTMLResponse)
def setup_page(
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin_no_2fa),
) -> HTMLResponse:
    """Page d'activation de la 2FA — génère un nouveau secret, affiche
    l'otpauth URI (copiable) et un champ de confirmation par code."""
    with platform_db() as conn:
        row = conn.execute(
            "SELECT totp_secret FROM superadmins WHERE email = ? LIMIT 1",
            (ctx.email,),
        ).fetchone()
    already = bool(row and row["totp_secret"])

    if already:
        html = f"""{_shared_head("2FA déjà activée")}
{_staging_banner()}
<main>
  <div class="card">
    <div class="wm">K<em>ernse</em></div>
    <div class="sub">2FA</div>
    <p style="text-align:center;color:var(--ink-2);margin-bottom:20px">
      La 2FA est déjà active sur ce compte ({_esc(ctx.email)}).<br>
      Pour la désactiver, utilisez l'endpoint <code>POST /auth/2fa/disable</code> avec votre mot de passe.
    </p>
    <p style="text-align:center"><a href="/admin" class="btn" style="text-decoration:none;display:inline-block">Retour à la console</a></p>
  </div>
</main>
{_footer()}"""
        return HTMLResponse(html)

    secret = generate_secret()
    uri = otpauth_uri(secret_b32=secret, email=ctx.email)

    html = f"""{_shared_head("Activer la 2FA")}
{_staging_banner()}
<main>
  <div class="card">
    <div class="wm">K<em>ernse</em></div>
    <div class="sub">Activer la 2FA</div>
    <ol style="margin:0 0 20px 20px;color:var(--ink-2);font-size:14px;line-height:1.7">
      <li>Ouvrez Google Authenticator, Authy ou 1Password.</li>
      <li>Ajoutez un compte manuel avec le secret ci-dessous.</li>
      <li>Saisissez le code à 6 chiffres généré pour confirmer.</li>
    </ol>
    <div style="background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:16px">
      <label style="display:block;margin-bottom:6px">Secret (base32)</label>
      <code style="font-family:var(--mono);font-size:13px;word-break:break-all;color:var(--ink)">{_esc(secret)}</code>
    </div>
    <details style="margin-bottom:16px">
      <summary style="cursor:pointer;color:var(--muted);font-size:12px">Voir l'URI otpauth (utile pour un QR code)</summary>
      <code style="display:block;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:11px;font-family:var(--mono);margin-top:6px;word-break:break-all">{_esc(uri)}</code>
    </details>
    <div class="err" id="err"></div>
    <form id="enable-form">
      <input type="hidden" name="secret" value="{_esc(secret)}">
      <div>
        <label for="code">Code à 6 chiffres</label>
        <input type="text" id="code" name="code" required inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" autocomplete="one-time-code" class="code-input" autofocus>
      </div>
      <button type="submit" class="btn">Activer la 2FA</button>
    </form>
  </div>
</main>
{_footer()}
<script>
document.getElementById('enable-form').addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  const form = ev.target;
  const btn = form.querySelector('button');
  const err = document.getElementById('err');
  err.classList.remove('on');
  btn.disabled = true; btn.textContent = 'Activation...';
  const body = new FormData(form);
  try {{
    const r = await fetch('/auth/2fa/enable', {{ method:'POST', body, credentials:'include' }});
    const j = await r.json().catch(()=>({{}}));
    if (r.ok) {{ window.location = '/admin'; return; }}
    err.textContent = j.detail || 'Code invalide.';
    err.classList.add('on');
    btn.disabled = false; btn.textContent = 'Activer la 2FA';
    form.querySelector('input[name=code]').value = '';
  }} catch (e) {{
    err.textContent = e.message || 'Erreur réseau.';
    err.classList.add('on');
    btn.disabled = false; btn.textContent = 'Activer la 2FA';
  }}
}});
</script>
"""
    return HTMLResponse(html)
