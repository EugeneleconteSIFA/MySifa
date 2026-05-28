"""MySifa — Portail transporteur public (MyExpé)."""

from __future__ import annotations

import html as html_module
import json


def _esc(s: object) -> str:
    return html_module.escape(str(s or ""))


def get_portail_404_html() -> str:
    return """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#0a0e17">
  <title>Lien invalide — MySifa</title>
  <style>
    :root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--danger:#f87171}
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:40px 32px;max-width:460px;text-align:center}
    h1{font-size:18px;font-weight:800;margin-bottom:12px}
    p{font-size:14px;color:var(--muted);line-height:1.6}
  </style>
</head>
<body>
  <div class="card">
    <h1>Lien invalide ou expiré</h1>
    <p>Ce lien n'est pas reconnu. Contactez votre interlocuteur SIFA pour obtenir un nouveau lien.</p>
  </div>
</body>
</html>"""


def get_portail_html(token: str) -> str:
    token_js = json.dumps(token)
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#0a0e17">
  <title>Portail transporteur — MySifa</title>
  <style>
    :root{{
      --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
      --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
      --success:#34d399;--warn:#fbbf24;--danger:#f87171;
    }}
    body.light{{
      --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
      --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
      --success:#059669;--warn:#d97706;--danger:#dc2626;
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
    .wrap{{max-width:920px;margin:0 auto;padding:20px 16px 48px}}
    .hdr{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
    .brand strong{{color:var(--accent);font-size:18px;font-weight:900;letter-spacing:-.4px}}
    .brand div{{font-size:12px;color:var(--muted);margin-top:2px}}
    .chip{{font-size:12px;color:var(--muted);font-family:ui-monospace,monospace;padding:6px 10px;border:1px solid var(--border);border-radius:10px;background:var(--card)}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 16px 14px}}
    .muted{{color:var(--muted)}}
    .list{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px}}
    .d{{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:14px}}
    .d h3{{font-size:14px;font-weight:900;margin-bottom:6px}}
    .meta{{font-size:12px;color:var(--text2);line-height:1.7}}
    .pill{{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:3px 10px;font-size:11px;font-weight:800;margin-right:6px;border:1px solid var(--border)}}
    .pill.ok{{color:var(--success);background:rgba(52,211,153,.10);border-color:rgba(52,211,153,.25)}}
    .pill.warn{{color:var(--warn);background:rgba(251,191,36,.10);border-color:rgba(251,191,36,.25)}}
    .pill.muted{{color:var(--muted);background:rgba(148,163,184,.10)}}
    .btn{{border-radius:10px;padding:10px 16px;font-weight:900;cursor:pointer;font-family:inherit;border:1px solid var(--border);background:transparent;color:var(--text);transition:filter .15s,border-color .15s,color .15s,background .15s}}
    .btn:hover{{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}}
    .btn-accent{{background:var(--accent);border-color:var(--accent);color:var(--bg)}}
    .btn-accent:hover{{filter:brightness(1.05)}}
    .btn-ghost{{background:transparent}}
    .row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px}}
    label{{display:block;font-size:11px;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
    input,textarea{{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:11px 12px;color:var(--text);font-size:14px;font-family:inherit}}
    input:focus,textarea:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}}
    body.light input:focus,body.light textarea:focus{{box-shadow:0 0 0 3px rgba(8,145,178,.12)}}
    .modal-ov{{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;padding:18px;z-index:9999}}
    body.light .modal-ov{{background:rgba(15,23,42,.42)}}
    .modal{{width:100%;max-width:520px;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px}}
    .mh{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}}
    .mh h2{{font-size:15px;font-weight:900;margin:0}}
    .x{{width:34px;height:34px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--muted);cursor:pointer;font-size:18px;line-height:1}}
    .x:hover{{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}}
    .toast{{position:fixed;right:16px;bottom:16px;z-index:10000;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;max-width:min(520px,calc(100vw - 32px));display:none}}
    .toast.ok{{border-color:rgba(52,211,153,.35)}}
    .toast.bad{{border-color:rgba(248,113,113,.35)}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hdr">
      <div class="brand">
        <strong>MySifa</strong>
        <div>Portail transporteur — réponse aux demandes de tarif</div>
      </div>
      <div class="chip" id="who">Chargement…</div>
    </div>

    <div class="card">
      <div style="font-size:13px;color:var(--text2);line-height:1.7">
        Merci de répondre pour chaque demande avec un <strong>prix HT</strong> et un <strong>délai</strong> estimé.<br>
        Les réponses sont enregistrées immédiatement.
      </div>
      <div class="list" id="list"></div>
    </div>
  </div>

  <div class="modal-ov" id="ov">
    <div class="modal">
      <div class="mh">
        <h2 id="mt">Répondre</h2>
        <button class="x" id="mx" type="button">×</button>
      </div>
      <div class="row">
        <div style="flex:1;min-width:160px">
          <label>Prix HT (€)</label>
          <input type="number" step="0.01" id="prix">
        </div>
        <div style="width:160px">
          <label>Délai (jours)</label>
          <input type="number" step="1" id="delai">
        </div>
      </div>
      <div style="margin-top:10px">
        <label>Commentaire (optionnel)</label>
        <textarea id="com" rows="3" placeholder="Conditions, contraintes, horaires…"></textarea>
      </div>
      <div class="row" style="justify-content:flex-end;margin-top:12px">
        <button class="btn btn-ghost" type="button" id="cancel">Annuler</button>
        <button class="btn btn-accent" type="button" id="save">Enregistrer</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
  const TOKEN = __TOKEN_JS__;
  const S = {{ data:null, editing:null }};

  function esc(s){{ return String(s??'').replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}}[c])); }}
  function pill(st){{
    const m={{ envoyee:['Envoyée','muted'], ouvert:['Ouverte','warn'], recue:['Reçue','ok'], retenue:['Retenue','ok'], refusee:['Refusée','muted'], echec:['Échec','muted'] }};
    const x=m[st]||[st||'—','muted'];
    return `<span class="pill ${x[1]}">${esc(x[0])}</span>`;
  }}
  function showToast(msg,kind){{
    const t=document.getElementById('toast');
    t.className='toast '+(kind==='ok'?'ok':'bad');
    t.textContent=msg;
    t.style.display='block';
    clearTimeout(t._to);
    t._to=setTimeout(()=>{{t.style.display='none';}},3200);
  }}
  async function api(path, opts){{
    const r=await fetch(path, Object.assign({{credentials:'omit'}}, opts||{{}}));
    const txt=await r.text();
    let j=null; try{{ j=JSON.parse(txt); }}catch(e){{}}
    if(!r.ok) throw new Error((j&&j.detail)||txt||('HTTP '+r.status));
    return j;
  }}
  function openModal(item){{
    S.editing=item;
    document.getElementById('mt').textContent='Demande #'+item.demande_id+' — '+(item.code_postal_destination||'');
    document.getElementById('prix').value = item.prix!=null ? String(item.prix) : '';
    document.getElementById('delai').value = item.delai_jours!=null ? String(item.delai_jours) : '';
    document.getElementById('com').value = item.commentaire||'';
    document.getElementById('ov').style.display='flex';
    setTimeout(()=>{{ document.getElementById('prix').focus(); }},0);
  }}
  function closeModal(){{ document.getElementById('ov').style.display='none'; S.editing=null; }}

  function render(){{
    const who=document.getElementById('who');
    const list=document.getElementById('list');
    const d=S.data;
    who.textContent = d ? ('Compte: '+(d.email||'—')) : 'Chargement…';
    list.innerHTML='';
    const rows=(d&&d.demandes)||[];
    if(!rows.length){{
      list.innerHTML = `<div class="d"><h3>Aucune demande</h3><div class="meta">Aucune demande de tarif n’est associée à ce lien.</div></div>`;
      return;
    }}
    rows.forEach(it=>{{
      const meta = [
        it.poids_total_kg!=null ? (it.poids_total_kg+' kg') : null,
        it.nb_palette!=null ? (it.nb_palette+' pal.') : null,
        it.type_envoi ? it.type_envoi : null,
        it.contraintes ? ('Contraintes: '+it.contraintes) : null,
      ].filter(Boolean).join(' · ');
      const canReply = it.demande_statut!=='cloturee' && it.reponse_statut!=='retenue';
      const btn = canReply ? `<button class="btn btn-accent" data-id="${it.demande_id}">Répondre</button>` : '';
      const html = `
        <div class="d">
          <h3>Demande #${it.demande_id} — ${esc(it.code_postal_destination||'')}</h3>
          <div class="meta">
            ${pill(it.reponse_statut)}<span class="muted">${esc(meta||'')}</span><br>
            <span class="muted">Créée le ${(it.created_at||'').slice(0,10)}</span>
          </div>
          <div class="row" style="justify-content:space-between">
            <div class="meta">${it.prix!=null?('Prix: <strong>'+Number(it.prix).toFixed(2)+' €</strong>'):'Prix: —'} · ${it.delai_jours!=null?('Délai: <strong>J+'+it.delai_jours+'</strong>'):'Délai: —'}</div>
            ${btn}
          </div>
        </div>`;
      const wrap=document.createElement('div');
      wrap.innerHTML=html;
      const node=wrap.firstElementChild;
      const b=node.querySelector('button[data-id]');
      if(b) b.addEventListener('click',()=>openModal(it));
      list.appendChild(node);
    }});
  }}

  async function load(){{
    S.data = await api('/api/portail/expe/'+encodeURIComponent(TOKEN));
    render();
  }}

  document.getElementById('mx').addEventListener('click',closeModal);
  document.getElementById('cancel').addEventListener('click',closeModal);
  document.getElementById('ov').addEventListener('click',e=>{{ if(e.target.id==='ov') closeModal(); }});
  document.getElementById('save').addEventListener('click', async ()=>{{
    const it=S.editing; if(!it) return;
    const prix=parseFloat(document.getElementById('prix').value);
    const delai=parseInt(document.getElementById('delai').value,10);
    if(!isFinite(prix) || prix<=0){{ showToast('Prix invalide.', 'bad'); return; }}
    if(!isFinite(delai) || delai<0){{ showToast('Délai invalide.', 'bad'); return; }}
    try{{
      await api('/api/portail/expe/'+encodeURIComponent(TOKEN)+'/demandes/'+it.demande_id+'/repondre', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{
          prix,
          delai_jours: delai,
          commentaire: (document.getElementById('com').value||'').trim()||null
        }})
      }});
      showToast('Réponse enregistrée.', 'ok');
      closeModal();
      await load();
    }}catch(e){{ showToast(e.message||'Erreur', 'bad'); }}
  }});

  load().catch(e=>{{ document.getElementById('who').textContent='Erreur'; showToast(e.message||'Erreur', 'bad'); }});
  </script>
</body>
</html>"""
    return html.replace("__TOKEN_JS__", token_js)

