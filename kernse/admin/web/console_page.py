"""
Kernse-admin — rendu HTML de la console plateforme.

Une seule page principale : /admin qui liste les clients avec leurs cards.
Chaque card offre les actions Promouvoir / Détacher épingle / Voir logs.
En haut de page, un bloc « Promouvoir tout le monde » avec un input git_ref
et un aperçu du nombre de clients concernés (épinglés exclus).

Rendu en chaînes Python (cohérent avec le pattern MySifa), design system
Kernse (navy/orange/crème).
"""
from __future__ import annotations

from kernse.shared.auth.dependency import SuperadminContext, require_superadmin

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from kernse.admin.config import APP_TITLE, APP_VERSION, IS_STAGING
from kernse.shared.db.database import list_active_clients, platform_db
from kernse.shared.models.client import Client


router = APIRouter(tags=["console"])



def _esc(v: object) -> str:
    """Échappement HTML minimal (aligné sur la règle MySifa escHtml)."""
    return (
        str(v)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _client_card(c: Client) -> str:
    pin_badge = ""
    if c.pinned:
        pin_badge = (
            f'<span class="tag tag-navy" title="{_esc(c.pinned_reason or "")}">'
            f'Épinglé · {_esc((c.pinned_at or "")[:10])}</span>'
        )

    status_badge = '<span class="tag tag-ok">Actif</span>'
    if c.suspended:
        status_badge = '<span class="tag tag-danger">Suspendu</span>'

    ref = _esc(c.deployed_ref or "—")
    deployed_at = _esc((c.deployed_at or "jamais")[:16].replace("T", " "))
    plan = _esc(c.plan)
    subdomain = _esc(c.subdomain)

    unpin_html = ""
    if c.pinned:
        unpin_html = (
            f'<button class="btn btn-ghost" data-action="unpin" data-client-id="{_esc(c.id)}">'
            f"Détacher l'épingle</button>"
        )

    # Le bouton "Promouvoir" n'a de sens que sur une instance déjà provisionnée.
    # Sinon on affiche l'action "Provisionner l'instance" avec un starter kit.
    if not c.deployed_ref:
        actions_html = f"""
        <select class="starter-kit">
          <option value="">Aucun starter kit</option>
          <option value="imprimerie">Starter kit — imprimerie</option>
          <option value="usinage">Starter kit — usinage</option>
          <option value="plasturgie">Starter kit — plasturgie</option>
          <option value="assemblage">Starter kit — assemblage</option>
          <option value="decoupe">Starter kit — découpe</option>
        </select>
        <button class="btn btn-accent" data-action="provision" data-client-id="{_esc(c.id)}">
          Provisionner l\'instance
        </button>
        """
    else:
        actions_html = f"""
        <input type="text" class="promote-ref" placeholder="git ref (SHA ou tag)" maxlength="40">
        <button class="btn btn-accent" data-action="promote" data-client-id="{_esc(c.id)}">
          Promouvoir ce client
        </button>
        {unpin_html}
        """

    return f"""
    <article class="card client-card" data-client-id="{_esc(c.id)}">
      <header>
        <h3>{_esc(c.company_name)} <span class="mini">· {subdomain}</span></h3>
        <div class="badges">{status_badge} {pin_badge}
          <span class="tag tag-accent">{plan}</span>
        </div>
      </header>
      <dl>
        <dt>Version déployée</dt><dd class="mono">{ref}</dd>
        <dt>Dernière promotion</dt><dd>{deployed_at}</dd>
        <dt>Contact</dt><dd>{_esc(c.contact_email)}</dd>
      </dl>
      <footer class="card-actions">{actions_html}</footer>
    </article>
    """


def _render_console(clients: list[Client], banner: str) -> str:
    total = len(clients)
    pinned = sum(1 for c in clients if c.pinned)
    suspended = sum(1 for c in clients if c.suspended)
    eligible_mass = total - pinned - suspended

    cards = "\n".join(_client_card(c) for c in clients) or (
        '<p class="empty">Aucun client pour l\'instant. Utilise le formulaire « Nouveau client » ci-dessus.</p>'
    )

    return f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(APP_TITLE)} — console</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;600;700;800&family=JetBrains+Mono:wght@600;800&family=Poppins:wght@900&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy:#182444; --orange:#F2652B; --orange-bg:#fce4d6;
    --bg:#f6f4ef; --surf:#fff; --line:#e6e2d7;
    --ink:#182444; --ink-2:#4e5872; --muted:#8b91a4;
    --green:#1f9d57; --green-bg:#e3f3ea;
    --red:#cf3b32; --red-bg:#f7e2e0;
    --amber:#bf7d12; --amber-bg:#f6ecd6;
    --r:14px; --shadow:0 1px 2px rgba(24,36,68,.05), 0 12px 32px rgba(24,36,68,.08);
    --sans:'Inter Tight',system-ui,sans-serif; --mono:'JetBrains Mono',monospace;
    --brand:'Poppins',var(--sans);
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.5}}
  .banner-staging{{background:var(--red);color:#fff;font-weight:800;text-align:center;padding:6px}}
  header.top{{background:var(--navy);color:#fff;padding:14px 24px;display:flex;align-items:center;gap:12px}}
  header.top .wm{{font-family:var(--brand);font-weight:900;font-size:22px;letter-spacing:-1px}}
  header.top .wm em{{color:var(--orange);font-style:normal;margin-left:-3px}}
  header.top .ver{{margin-left:auto;font-family:var(--mono);font-size:11px;opacity:.7}}
  main{{max-width:1200px;margin:0 auto;padding:24px}}
  h1{{font-family:var(--brand);font-size:28px;font-weight:900;letter-spacing:-.8px;margin-bottom:16px}}
  h1 em{{color:var(--orange);font-style:normal}}
  .stats{{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}}
  .stat{{background:var(--surf);border:1px solid var(--line);border-radius:var(--r);padding:12px 18px}}
  .stat .num{{font-family:var(--mono);font-size:22px;font-weight:800;color:var(--orange)}}
  .stat .lab{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:800}}
  .card{{background:var(--surf);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:16px 20px;margin-bottom:14px}}
  .mass-promote{{border-left:3px solid var(--orange);background:var(--orange-bg)}}
  .mass-promote h2{{font-family:var(--brand);font-size:18px;margin-bottom:8px}}
  .mass-promote p{{color:var(--ink-2);margin-bottom:10px}}
  .mass-promote form{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
  .client-card header{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}}
  .client-card h3{{font-size:16px;font-weight:800}}
  .client-card h3 .mini{{font-weight:400;color:var(--muted);font-family:var(--mono);font-size:12px}}
  .client-card dl{{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;margin:10px 0}}
  .client-card dt{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:800;align-self:center}}
  .client-card dd{{color:var(--ink-2)}}
  .card-actions{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}}
  .tag{{display:inline-block;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:999px;white-space:nowrap}}
  .tag-ok{{background:var(--green-bg);color:var(--green)}}
  .tag-danger{{background:var(--red-bg);color:var(--red)}}
  .tag-accent{{background:var(--orange-bg);color:var(--orange)}}
  .tag-navy{{background:var(--navy);color:#fff}}
  .badges{{display:flex;gap:6px;flex-wrap:wrap}}
  .mono{{font-family:var(--mono)}}
  input[type=text]{{border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-family:var(--mono);font-size:13px;flex:1;min-width:180px;background:#fff;color:var(--ink)}}
  input[type=text]:focus{{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(242,101,43,.15)}}
  .btn{{border:none;border-radius:10px;padding:9px 16px;font-weight:800;font-family:var(--sans);font-size:13px;cursor:pointer;transition:filter .15s}}
  .btn:hover{{filter:brightness(1.05)}}
  .btn-accent{{background:var(--orange);color:#fff}}
  .btn-ghost{{background:transparent;color:var(--ink-2);border:1px solid var(--line)}}
  .empty{{padding:40px;text-align:center;color:var(--muted)}}
  #toast{{position:fixed;bottom:20px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:10px;box-shadow:var(--shadow);opacity:0;transform:translateY(20px);transition:all .2s;pointer-events:none;max-width:400px;font-size:13px}}
  #toast.on{{opacity:1;transform:translateY(0)}}
  #toast.err{{background:var(--red)}}
  .form-row{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
  .form-row input, .form-row select {{padding:9px 12px;border:1px solid var(--line);border-radius:10px;font-size:13px;background:#fff;color:var(--ink);font-family:var(--sans)}}
  .form-row input:focus, .form-row select:focus {{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(242,101,43,.15)}}
  .err {{background:var(--red-bg);color:var(--red);padding:8px 12px;border-radius:8px;font-size:12px;margin-bottom:10px;display:none}}
  .err.on {{display:block}}
  select.starter-kit {{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:12px;background:#fff}}
</style>
</head>
<body>
{banner}
<header class="top">
  <div class="wm">K<em>ernse</em></div>
  <span class="mini">Console plateforme</span>
  <span class="ver">v{_esc(APP_VERSION)}</span>
</header>
<main>
  <h1>Flotte <em>Kernse</em></h1>

  <div class="stats">
    <div class="stat"><div class="num">{total}</div><div class="lab">Clients actifs</div></div>
    <div class="stat"><div class="num">{pinned}</div><div class="lab">Épinglés</div></div>
    <div class="stat"><div class="num">{suspended}</div><div class="lab">Suspendus</div></div>
    <div class="stat"><div class="num">{eligible_mass}</div><div class="lab">Éligibles mass-promote</div></div>
  </div>

  <section class="card mass-promote">
    <h2>Promouvoir tout le monde</h2>
    <p>Cible <b>{eligible_mass} client(s)</b> — les {pinned} épinglé(s) et {suspended} suspendu(s) sont ignoré(s).</p>
    <form id="mass-form">
      <input type="text" id="mass-ref" placeholder="git ref (SHA court ou tag)" required maxlength="40">
      <input type="text" id="mass-notes" placeholder="notes (facultatif)" maxlength="200">
      <button type="submit" class="btn btn-accent">Promouvoir la flotte</button>
    </form>
  </section>

  <section class="card create-client">
    <h2 style="font-family:var(--brand);font-size:18px;margin-bottom:6px">Nouveau client</h2>
    <p style="color:var(--ink-2);font-size:13px;margin-bottom:14px">
      Crée l\'entrée plateforme. L\'instance physique (dossier, DB, systemd, nginx) est provisionnée dans un second temps via le bouton « Provisionner l\'instance » sur la fiche du client.
    </p>
    <div class="err" id="create-err"></div>
    <form id="create-form">
      <div class="form-row">
        <input type="text" name="slug" placeholder="slug (ex. durand-imprimerie)"
               required pattern="[a-z0-9](-?[a-z0-9]){{1,39}}" title="minuscules, chiffres et tirets uniquement"
               style="flex:1;min-width:180px">
        <input type="text" name="company_name" placeholder="Nom de l\'entreprise" required
               style="flex:1;min-width:180px">
      </div>
      <div class="form-row" style="margin-top:8px">
        <input type="text" name="subdomain" placeholder="sous-domaine (ex. durand.kernse.fr)"
               required style="flex:1;min-width:180px">
        <select name="plan" style="min-width:140px">
          <option value="atelier">Plan Atelier</option>
          <option value="usine">Plan Usine</option>
          <option value="custom">Plan custom</option>
        </select>
      </div>
      <div class="form-row" style="margin-top:8px">
        <input type="email" name="contact_email" placeholder="Email du superadmin de l\'organisation"
               required style="flex:1">
        <button type="submit" class="btn btn-accent">Créer le client</button>
      </div>
    </form>
  </section>

  <section id="clients">
    {cards}
  </section>
</main>

<div id="toast"></div>

<script>
const SUPERADMIN = document.cookie.split('; ').find(r=>r.startsWith('kernse_admin_email='))?.split('=')[1] || '';

function toast(msg, err) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.toggle('err', !!err);
  t.classList.add('on');
  setTimeout(()=>t.classList.remove('on'), 4200);
}}

async function api(path, options) {{
  const opts = Object.assign({{headers:{{}}, credentials:'include'}}, options||{{}});
  opts.headers['X-Kernse-Superadmin'] = SUPERADMIN;
  if (opts.body && !(opts.body instanceof FormData)) {{
    opts.headers['Content-Type'] = 'application/json';
  }}
  const r = await fetch(path, opts);
  const data = await r.json().catch(()=>({{error:'JSON invalide'}}));
  if (!r.ok) throw new Error(data.detail || data.error || ('HTTP ' + r.status));
  return data;
}}

document.addEventListener('click', async (ev) => {{
  const btn = ev.target.closest('button[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const cid = btn.dataset.clientId;

  if (action === 'promote') {{
    const refInput = btn.parentElement.querySelector('.promote-ref');
    const ref = (refInput.value || '').trim();
    if (!ref) return toast('Ref git requis.', true);
    if (!confirm(`Promouvoir ce client vers ${{ref}} ? (il sera épinglé automatiquement)`)) return;
    btn.disabled = true;
    try {{
      const res = await api(`/api/v1/promotion/client/${{cid}}`, {{
        method: 'POST',
        body: JSON.stringify({{git_ref: ref, pin_after: true}}),
      }});
      toast(res.ok ? `Client promu vers ${{res.to_ref}}.` : ('Échec : ' + (res.error||'?')), !res.ok);
      if (res.ok) setTimeout(()=>location.reload(), 800);
    }} catch (e) {{ toast(e.message, true); }}
    finally {{ btn.disabled = false; }}
  }}

  if (action === 'provision') {{
    const select = btn.parentElement.querySelector('.starter-kit');
    const kit = select ? select.value : '';
    if (!confirm(`Provisionner physiquement l\'instance ? Cela va créer le dossier, la DB, le service systemd et le vhost nginx. Ça peut prendre 30-90 secondes.`)) return;
    btn.disabled = true; btn.textContent = 'Provisionnement...';
    try {{
      const res = await api(`/api/v1/provision/client/${{cid}}`, {{
        method: 'POST',
        body: JSON.stringify(kit ? {{starter_kit: kit}} : {{}}),
      }});
      if (res.ok) {{
        toast(`Instance provisionnée : ${{res.subdomain}} → port ${{res.port}}, ref ${{res.deployed_ref}}. N\'oublie pas de faire certbot pour ce sous-domaine.`);
        setTimeout(()=>location.reload(), 1500);
      }} else {{
        toast('Échec : ' + (res.error || '?'), true);
        btn.disabled = false; btn.textContent = 'Provisionner l\'instance';
      }}
    }} catch (e) {{ toast(e.message, true); btn.disabled = false; btn.textContent = 'Provisionner l\'instance'; }}
  }}

  if (action === 'unpin') {{
    if (!confirm('Détacher l\\'épingle ? Le client redeviendra éligible aux promotions de masse.')) return;
    btn.disabled = true;
    try {{
      await api(`/api/v1/promotion/client/${{cid}}/unpin`, {{
        method: 'POST',
        body: JSON.stringify({{}}),
      }});
      toast('Épingle détachée.');
      setTimeout(()=>location.reload(), 600);
    }} catch (e) {{ toast(e.message, true); }}
    finally {{ btn.disabled = false; }}
  }}
}});

// --- Formulaire "Nouveau client" ---
document.getElementById('create-form').addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  const form = ev.target;
  const btn = form.querySelector('button[type=submit]');
  const err = document.getElementById('create-err');
  err.classList.remove('on');
  const data = Object.fromEntries(new FormData(form).entries());
  btn.disabled = true; btn.textContent = 'Création...';
  try {{
    const res = await api('/api/v1/clients', {{
      method: 'POST',
      body: JSON.stringify(data),
    }});
    toast(`Client ${{res.slug}} créé — provisionne maintenant l\'instance depuis sa fiche.`);
    setTimeout(()=>location.reload(), 800);
  }} catch (e) {{
    err.textContent = e.message;
    err.classList.add('on');
    btn.disabled = false; btn.textContent = 'Créer le client';
  }}
}});

// --- Auto-fill du sous-domaine depuis le slug ---
document.querySelector('input[name=slug]').addEventListener('input', (ev) => {{
  const slug = (ev.target.value || '').trim();
  const sub = document.querySelector('input[name=subdomain]');
  if (slug && (!sub.value || sub.dataset.autofill === '1')) {{
    sub.value = slug + '.kernse.fr';
    sub.dataset.autofill = '1';
  }}
}});
document.querySelector('input[name=subdomain]').addEventListener('input', (ev) => {{
  ev.target.dataset.autofill = '0';
}});

document.getElementById('mass-form').addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  const ref = document.getElementById('mass-ref').value.trim();
  const notes = document.getElementById('mass-notes').value.trim();
  if (!ref) return toast('Ref git requis.', true);
  if (!confirm(`Promouvoir TOUS les clients éligibles vers ${{ref}} ? Les épinglés seront ignorés.`)) return;
  const btn = ev.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Promotion en cours...';
  try {{
    const res = await api('/api/v1/promotion/all', {{
      method: 'POST',
      body: JSON.stringify({{git_ref: ref, notes: notes || null}}),
    }});
    toast(`${{res.promoted.length}} promu(s), ${{res.failures.length}} échec(s), ${{res.skipped_pinned.length}} épinglé(s) ignoré(s).`);
    setTimeout(()=>location.reload(), 1500);
  }} catch (e) {{ toast(e.message, true); }}
  finally {{ btn.disabled = false; btn.textContent = 'Promouvoir la flotte'; }}
}});
</script>
</body></html>
"""


@router.get("/admin", response_class=HTMLResponse)
def console_home(_ctx: SuperadminContext = Depends(require_superadmin)) -> HTMLResponse:
    banner = ""
    if IS_STAGING:
        banner = '<div class="banner-staging">STAGING — v1 · aucune action réelle en production</div>'
    with platform_db() as conn:
        rows = list_active_clients(conn)
    clients = [Client.from_row(r) for r in rows]
    html = _render_console(clients, banner)
    return HTMLResponse(html)
