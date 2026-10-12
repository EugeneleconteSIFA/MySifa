"""MySifa — Portail fournisseur public : questionnaire EUDR.

Page autonome ouverte par le lien de l'email (`/portail/eudr/<jeton>`), sans
compte. En anglais : c'est la langue d'échange avec les fournisseurs papier.
Même habillage sombre que le portail transporteur. Les choix proposés viennent
de l'API (`config.EUDR_CHOIX`), pas de cette page.
"""

from __future__ import annotations

import html as html_module
import json

from config import APP_ORG_NAME


def _esc(s: object) -> str:
    return html_module.escape(str(s or ""))


_HEAD = """
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#0a0e17"><!-- hex-ok -->
  <meta name="robots" content="noindex,nofollow">
  <link rel="icon" href="/static/expe_portail_favicon.svg" type="image/svg+xml">
  <style>
    :root{--bg:#0a0e17;--card:#111827;--card2:#0f172a;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1; /* hex-ok : theme du portail public */
      --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--danger:#f87171;--ok:#34d399} /* hex-ok */
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;
      padding:24px 16px 32px;line-height:1.5}
    .wrap{max-width:760px;margin:0 auto}
    .brand{font-size:12px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
    h1{font-size:22px;font-weight:800;margin-bottom:8px}
    .lead{font-size:14px;color:var(--text2);margin-bottom:20px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin-bottom:14px}
    .card h2{font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--accent);margin-bottom:14px}
    .q{margin-bottom:16px}
    .q:last-child{margin-bottom:0}
    .q > label, .q > .ql{display:block;font-size:14px;font-weight:600;margin-bottom:6px}
    .hint{font-size:12px;color:var(--muted);margin:-2px 0 8px}
    input[type=text],input[type=email],input[type=date],textarea,select{width:100%;padding:10px 12px;border-radius:9px;
      border:1px solid var(--border);background:var(--card2);color:var(--text);font:inherit;font-size:14px}
    input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent)}
    textarea{min-height:70px;resize:vertical}
    .opts{display:flex;flex-direction:column;gap:6px}
    .opt{display:flex;gap:10px;align-items:flex-start;padding:9px 12px;border:1px solid var(--border);border-radius:9px;
      cursor:pointer;font-size:14px;color:var(--text2)}
    .opt:has(input:checked){border-color:var(--accent);background:var(--accent-bg);color:var(--text)}
    .opt input{margin-top:3px;accent-color:var(--accent)}
    .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    @media (max-width:560px){.row{grid-template-columns:1fr}}
    .req{color:var(--danger)}
    .btn{display:inline-block;padding:12px 22px;border-radius:10px;border:none;background:var(--accent);color:white;
      font-weight:800;font-size:15px;cursor:pointer;font-family:inherit}
    .btn:disabled{opacity:.5;cursor:default}
    .err{color:var(--danger);font-size:13px;font-weight:600;margin-top:10px;min-height:18px}
    .done{text-align:center;padding:36px 22px}
    .done h2{color:var(--ok);font-size:18px;text-transform:none;letter-spacing:0;margin-bottom:8px}
    .done p{color:var(--text2);font-size:14px}
    .note{font-size:12px;color:var(--muted);margin-top:8px}
    .nonue{display:none}
    .foot{margin-top:24px;text-align:center;font-size:11px;color:var(--muted)}
  </style>
"""


def get_eudr_404_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head>{_HEAD}<title>Invalid link — {_esc(APP_ORG_NAME)}</title></head>
<body><div class="wrap"><div class="card done">
  <h2 style="color:var(--text)">Invalid or expired link</h2>
  <p>This link is not recognised. Please contact your {_esc(APP_ORG_NAME)} contact for a new link.</p>
</div></div></body></html>"""


def get_eudr_portail_html(token: str) -> str:
    org = _esc(APP_ORG_NAME)
    return f"""<!DOCTYPE html>
<html lang="en"><head>{_HEAD}<title>EUDR questionnaire — {org}</title></head>
<body><div class="wrap">
  <div class="brand">{org} · Supplier portal</div>
  <h1>EUDR questionnaire</h1>
  <p class="lead" id="lead">Regulation (EU) 2023/1115 on deforestation-free products.</p>
  <div id="root"><div class="card">Loading…</div></div>
  <div class="foot">{org} supplier portal — personal link, do not share.</div>
</div>
<script>
const TOKEN = {json.dumps(token)};
const API = '/api/portail/eudr/' + encodeURIComponent(TOKEN);
let D = null;

function esc(s){{ const d=document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML; }}

function radios(name, req){{
  const opts = (D.choix[name]||{{}});
  const cur = (D.precedente||{{}})[name] || '';
  return '<div class="opts">' + Object.keys(opts).map(k =>
    '<label class="opt"><input type="radio" name="'+name+'" value="'+esc(k)+'"'+(cur===k?' checked':'')+
    (req?' required':'')+'><span>'+esc(opts[k])+'</span></label>').join('') + '</div>';
}}
function txt(name, type){{
  const v = (D.precedente||{{}})[name] || '';
  return '<input type="'+(type||'text')+'" name="'+name+'" value="'+esc(v)+'">';
}}
function area(name, ph){{
  const v = (D.precedente||{{}})[name] || '';
  return '<textarea name="'+name+'" placeholder="'+esc(ph||'')+'">'+esc(v)+'</textarea>';
}}

function render(){{
  document.getElementById('lead').textContent =
    'Regulation (EU) 2023/1115 on deforestation-free products — questionnaire for ' + D.fournisseur + '.';
  const p = D.precedente || {{}};
  document.getElementById('root').innerHTML = `
  <form id="f" novalidate>
    ${{D.precedente ? '<div class="card"><p class="note" style="margin:0">You already answered on '+esc((p.created_at||'').slice(0,10))+
      '. Your previous answers are pre-filled — submitting again records an update.</p></div>' : ''}}
    <div class="card"><h2>Your company</h2>
      <div class="q"><div class="ql">Where is the company invoicing {org} established?</div>${{radios('etablissement')}}</div>
    </div>
    <div class="card"><h2>Scope</h2>
      <div class="q"><div class="ql">Do the products you supply to {org} fall under the EUDR?</div>
        <div class="hint">Paper and paperboard (chapters 47 and 48 of the Combined Nomenclature) are in scope; plastic films are not.</div>
        ${{radios('perimetre')}}</div>
      <div class="q"><label>CN / HS codes of the products concerned</label>
        <div class="hint">For example 4810 92, 4821 10.</div>${{txt('codes_nc')}}</div>
      <div class="q"><div class="ql">Your role under the EUDR <span class="req">*</span></div>${{radios('role', true)}}</div>
      <div class="q"><label>From which date will your due diligence statements cover our deliveries?</label>${{txt('date_debut_dds','date')}}</div>
    </div>
    <div class="card"><h2>Reference numbers</h2>
      <div class="q"><div class="ql">How will you send us the reference and verification numbers of the due diligence statements?</div>${{radios('transmission')}}</div>
      <div class="q"><label>Details</label>${{area('transmission_detail','Format, field on the document, portal address…')}}</div>
      <div class="q"><div class="ql">Will each delivery carry its own reference number?</div>${{radios('ref_par_livraison')}}</div>
      <div class="q"><label>Your upstream suppliers</label>
        <div class="hint">If you do not file the statement yourself: who does (paper mill, pulp supplier, importer)?</div>
        ${{area('amont','Company name and country')}}</div>
    </div>
    <div class="card nonue" id="bloc-nonue"><h2>Origin of the wood</h2>
      <p class="note" style="margin:-6px 0 14px">For goods shipped from outside the EU, {org} files the due diligence statement and needs the following data.</p>
      <div class="q"><div class="ql">Can you provide the geolocation of the plots of land where the wood was harvested?</div>${{radios('geolocalisation')}}</div>
      <div class="row">
        <div class="q"><label>Wood species (scientific and common name)</label>${{txt('essences')}}</div>
        <div class="q"><label>Countries of harvest</label>${{txt('pays_recolte')}}</div>
      </div>
    </div>
    <div class="card"><h2>Contacts</h2>
      <div class="row">
        <div class="q"><label>Your name <span class="req">*</span></label>${{txt('repondant_nom')}}</div>
        <div class="q"><label>Your position</label>${{txt('repondant_fonction')}}</div>
      </div>
      <div class="q"><label>Your email <span class="req">*</span></label>
        <input type="email" name="repondant_email" value="${{esc(p.repondant_email || D.email || '')}}"></div>
      <div class="row">
        <div class="q"><label>EUDR contact person (if different)</label>${{txt('contact_nom')}}</div>
        <div class="q"><label>EUDR contact email</label>${{txt('contact_email','email')}}</div>
      </div>
      <div class="q"><label>Comments</label>${{area('commentaire','')}}</div>
    </div>
    <div class="card">
      <button type="submit" class="btn" id="go">Submit my answers</button>
      <div class="err" id="err"></div>
    </div>
  </form>`;
  const f = document.getElementById('f');
  const majNonUe = () => {{
    const v = (f.querySelector('input[name=etablissement]:checked')||{{}}).value;
    document.getElementById('bloc-nonue').style.display = v === 'non_eu' ? 'block' : 'none';
  }};
  f.addEventListener('change', majNonUe); majNonUe();
  f.addEventListener('submit', envoyer);
}}

async function envoyer(ev){{
  ev.preventDefault();
  const f = ev.target, body = {{}};
  new FormData(f).forEach((v,k) => {{ body[k] = v; }});
  const err = document.getElementById('err'), go = document.getElementById('go');
  err.textContent = '';
  if(!body.role){{ err.textContent = 'Please indicate your role under the EUDR.'; return; }}
  if(!(body.repondant_nom||'').trim()){{ err.textContent = 'Please enter your name.'; return; }}
  go.disabled = true;
  try{{
    const r = await fetch(API, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)}});
    const j = await r.json().catch(() => ({{}}));
    if(!r.ok){{ err.textContent = j.detail || 'Submission failed — please try again.'; go.disabled = false; return; }}
    document.getElementById('root').innerHTML =
      '<div class="card done"><h2>Thank you — your answers have been recorded.</h2>'+
      '<p>You can come back to this page with the same link to update them.</p></div>';
    window.scrollTo(0,0);
  }}catch(e){{ err.textContent = 'Network error — please try again.'; go.disabled = false; }}
}}

(async () => {{
  try{{
    const r = await fetch(API);
    if(!r.ok){{ document.getElementById('root').innerHTML = '<div class="card">Invalid or expired link.</div>'; return; }}
    D = await r.json(); render();
  }}catch(e){{ document.getElementById('root').innerHTML = '<div class="card">Network error — please reload the page.</div>'; }}
}})();
</script>
</body></html>"""
