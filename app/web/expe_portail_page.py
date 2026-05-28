"""MySifa — Portail transporteur public (MyExpé)."""

from __future__ import annotations

import html as html_module
import json

from app.web.expe_portail_i18n import PORTAIL_I18N


def _esc(s: object) -> str:
    return html_module.escape(str(s or ""))


_PORTAIL_FAVICON_HEAD = """
  <link rel="icon" href="/static/expe_portail_favicon.svg" type="image/svg+xml">
  <link rel="icon" type="image/png" sizes="32x32" href="/static/expe_portail_favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/static/expe_portail_favicon-180.png">
"""

_PORTAIL_FOOTER = """
    <footer class="foot">
      <div class="foot-brand">SIFA — Roubaix (59)</div>
      <div class="foot-contact">
        <a href="tel:+33320690101">03 20 69 01 01</a>
        <span class="foot-sep">·</span>
        <a href="mailto:expeditions@sifa.pro">expeditions@sifa.pro</a>
      </div>
      <div class="foot-note" id="i18n-foot-note">Portail sécurisé MySifa</div>
    </footer>
"""


def get_portail_404_html() -> str:
    return """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#0a0e17">
  <title>Lien invalide — MySifa</title>
""" + _PORTAIL_FAVICON_HEAD + """
  <style>
    :root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--danger:#f87171}
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column;padding:24px 16px 20px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:40px 32px;max-width:460px;text-align:center;margin:auto}
    h1{font-size:18px;font-weight:800;margin-bottom:12px}
    p{font-size:14px;color:var(--muted);line-height:1.6}
    .foot{margin-top:auto;padding-top:16px;border-top:1px solid var(--border);text-align:center;font-size:11px;color:var(--muted);line-height:1.7}
    .foot-brand{font-weight:600;color:var(--text2);margin-bottom:4px}
    .foot-contact{font-size:12px}
    .foot-contact a{color:var(--accent);text-decoration:none}
    .foot-contact a:hover{text-decoration:underline}
    .foot-sep{margin:0 6px;color:var(--border)}
    .foot-note{margin-top:6px;font-size:10px}
  </style>
</head>
<body>
  <div class="card">
    <h1>Lien invalide ou expiré</h1>
    <p>Ce lien n'est pas reconnu. Contactez votre interlocuteur SIFA pour obtenir un nouveau lien.</p>
  </div>
""" + _PORTAIL_FOOTER + """
</body>
</html>"""


def get_portail_html(token: str, lang: str = "fr") -> str:
    token_js = json.dumps(token)
    init_lang = lang if lang in ("fr", "en") else "fr"
    lang_js = json.dumps(init_lang)
    i18n_js = json.dumps(PORTAIL_I18N, ensure_ascii=False)
    html = """<!DOCTYPE html>
<html lang=""" + json.dumps(init_lang) + """>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#0a0e17">
  <title>Portail transporteur — MySifa</title>
""" + _PORTAIL_FAVICON_HEAD + """
  <style>
    :root{
      --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
      --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
      --success:#34d399;--warn:#fbbf24;--danger:#f87171;
    }
    body.light{
      --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
      --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
      --success:#059669;--warn:#d97706;--danger:#dc2626;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
    .wrap{max-width:860px;margin:0 auto;padding:20px 16px 48px}
    .hdr{
      display:flex;justify-content:space-between;align-items:flex-start;gap:16px;
      flex-wrap:wrap;margin-bottom:16px;
    }
    .hdr-brand strong{color:var(--accent);font-size:16px;font-weight:800;letter-spacing:-.3px}
    .hdr-brand div{font-size:13px;color:var(--muted);margin-top:4px;line-height:1.5}
    .hdr-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
    .chip{font-size:12px;color:var(--muted);font-family:ui-monospace,monospace;padding:6px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card)}
    .theme-btn{
      padding:8px 12px;border-radius:10px;border:1px solid var(--border);background:var(--card);
      color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;
    }
    .theme-btn:hover{border-color:var(--accent);color:var(--accent)}
    .lang-btn{
      padding:6px 8px;border-radius:10px;border:1px solid var(--border);background:var(--card);
      cursor:pointer;display:inline-flex;align-items:center;justify-content:center;line-height:0;
    }
    .lang-btn:hover{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
    .lang-btn svg{display:block;border-radius:2px}
    .banner{
      background:var(--card);border:1px solid var(--border);border-radius:12px;
      padding:20px 22px;margin-bottom:16px;
    }
    .banner h1{font-size:18px;font-weight:700;margin-bottom:8px;color:var(--text)}
    .banner p{font-size:13px;color:var(--text2);line-height:1.65;margin:0}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 16px 14px}
    .muted{color:var(--muted)}
    .list{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px}
    .d{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:14px}
    .d h3{font-size:14px;font-weight:900;margin-bottom:6px}
    .meta{font-size:12px;color:var(--text2);line-height:1.7}
    .btn{border-radius:10px;padding:10px 16px;font-weight:900;cursor:pointer;font-family:inherit;border:1px solid var(--border);background:transparent;color:var(--text);transition:filter .15s,border-color .15s,color .15s,background .15s}
    .btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
    .btn-accent{
      background:var(--accent);border-color:var(--accent);color:#0a0e17;
      font-weight:700;
    }
    .btn-accent:hover{filter:brightness(1.05);color:#0a0e17}
    body.light .btn-accent{color:#fff}
    .btn-ghost{background:transparent}
    .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px}
    label{display:block;font-size:11px;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
    input,textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:11px 12px;color:var(--text);font-size:14px;font-family:inherit}
    input:focus,textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
    body.light input:focus,body.light textarea:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
    .modal-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;padding:18px;z-index:9999}
    body.light .modal-ov{background:rgba(15,23,42,.42)}
    .modal{width:100%;max-width:520px;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px}
    .mh{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}
    .mh h2{font-size:15px;font-weight:900;margin:0}
    .x{width:34px;height:34px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--muted);cursor:pointer;font-size:18px;line-height:1}
    .x:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
    .toast{position:fixed;right:16px;bottom:16px;z-index:10000;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;max-width:min(520px,calc(100vw - 32px));display:none}
    .toast.ok{border-color:rgba(52,211,153,.35)}
    .toast.bad{border-color:rgba(248,113,113,.35)}
    .foot{margin-top:28px;padding-top:16px;border-top:1px solid var(--border);text-align:center;font-size:11px;color:var(--muted);line-height:1.7}
    .foot-brand{font-weight:600;color:var(--text2);margin-bottom:4px}
    .foot-contact{font-size:12px}
    .foot-contact a{color:var(--accent);text-decoration:none}
    .foot-contact a:hover{text-decoration:underline}
    .foot-sep{margin:0 6px;color:var(--border)}
    .foot-note{margin-top:6px;font-size:10px}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hdr">
      <div class="hdr-brand">
        <strong>MySifa</strong>
        <div id="i18n-subtitle">Portail transporteur — demandes de tarif SIFA</div>
      </div>
      <div class="hdr-actions">
        <div class="chip" id="who">Chargement…</div>
        <button type="button" class="lang-btn" id="langBtn" title="English" aria-label="English"></button>
        <button type="button" class="theme-btn" id="themeBtn">Thème</button>
      </div>
    </header>

    <div class="banner">
      <h1 id="i18n-banner-title">Vos demandes de tarif</h1>
      <p id="i18n-banner-text">
        Pour chaque envoi, indiquez un <strong>prix HT</strong> et un <strong>délai</strong> (en jours).
        La réponse est enregistrée dès validation.
      </p>
    </div>

    <div class="card">
      <div class="list" id="list"></div>
    </div>
""" + _PORTAIL_FOOTER + """
  </div>

  <div class="modal-ov" id="ov">
    <div class="modal">
      <div class="mh">
        <h2 id="mt">Répondre</h2>
        <button class="x" id="mx" type="button" aria-label="Close">×</button>
      </div>
      <div class="row">
        <div style="flex:1;min-width:160px">
          <label id="i18n-label-prix">Prix HT (€)</label>
          <input type="number" step="0.01" id="prix">
        </div>
        <div style="width:160px">
          <label id="i18n-label-delai">Délai (jours)</label>
          <input type="number" step="1" id="delai">
        </div>
      </div>
      <div style="margin-top:10px">
        <label id="i18n-label-com">Commentaire (optionnel)</label>
        <textarea id="com" rows="3"></textarea>
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
  const INIT_LANG = __LANG_JS__;
  const I18N = __I18N_JS__;
  const S = { data:null, editing:null, lang: INIT_LANG };

  const FLAG_FR = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 3 2" aria-hidden="true"><rect width="1" height="2" fill="#002395"/><rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#ED2939"/></svg>';
  const FLAG_GB = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 60 30" aria-hidden="true"><rect width="60" height="30" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="3"/><path d="M30,0 V30 M0,15 H60" stroke="#fff" stroke-width="10"/><path d="M30,0 V30 M0,15 H60" stroke="#C8102E" stroke-width="6"/></svg>';

  function t(k){ return (I18N[S.lang]&&I18N[S.lang][k])||k; }
  function esc(s){ return String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c])); }
  function typeLabel(code){
    const c=String(code||'').trim();
    return t('type_'+c) !== 'type_'+c ? t('type_'+c) : (c||'');
  }
  function readLang(){
    try{
      const q=new URLSearchParams(location.search).get('lang');
      if(q==='en'||q==='fr') return q;
      const s=localStorage.getItem('mysifa_portail_lang');
      if(s==='en'||s==='fr') return s;
    }catch(e){}
    return INIT_LANG==='en'?'en':'fr';
  }
  function updateLangBtn(){
    const btn=document.getElementById('langBtn');
    if(!btn) return;
    if(S.lang==='fr'){
      btn.innerHTML=FLAG_GB;
      btn.title=t('langToEn');
      btn.setAttribute('aria-label', t('langToEn'));
    }else{
      btn.innerHTML=FLAG_FR;
      btn.title=t('langToFr');
      btn.setAttribute('aria-label', t('langToFr'));
    }
  }
  function applyI18n(){
    document.documentElement.lang=S.lang;
    document.title=t('pageTitle');
    const sub=document.getElementById('i18n-subtitle'); if(sub) sub.textContent=t('subtitle');
    const bt=document.getElementById('i18n-banner-title'); if(bt) bt.textContent=t('bannerTitle');
    const bx=document.getElementById('i18n-banner-text'); if(bx) bx.innerHTML=t('bannerText');
    const tb=document.getElementById('themeBtn'); if(tb){ tb.textContent=t('theme'); tb.title=t('themeTitle'); }
    const lp=document.getElementById('i18n-label-prix'); if(lp) lp.textContent=t('labelPrice');
    const ld=document.getElementById('i18n-label-delai'); if(ld) ld.textContent=t('labelDelay');
    const lc=document.getElementById('i18n-label-com'); if(lc) lc.textContent=t('labelComment');
    const com=document.getElementById('com'); if(com) com.placeholder=t('commentPh');
    const ca=document.getElementById('cancel'); if(ca) ca.textContent=t('cancel');
    const sa=document.getElementById('save'); if(sa) sa.textContent=t('save');
    const fn=document.getElementById('i18n-foot-note'); if(fn) fn.textContent=t('footNote');
    updateLangBtn();
  }
  function setLang(lang){
    S.lang=(lang==='en')?'en':'fr';
    try{ localStorage.setItem('mysifa_portail_lang', S.lang); }catch(e){}
    applyI18n();
    if(S.data) render();
  }
  function apiErr(j,txt){
    if(!j) return txt||t('error');
    const d=j.detail;
    if(typeof d==='string') return d;
    if(Array.isArray(d)) return d.map(x=>x.msg||(x.loc?x.loc.join('.'):'')||String(x)).filter(Boolean).join(' — ')||txt;
    return txt||t('error');
  }
  function showToast(msg,kind){
    const el=document.getElementById('toast');
    el.className='toast '+(kind==='ok'?'ok':'bad');
    el.textContent=msg;
    el.style.display='block';
    clearTimeout(el._to);
    el._to=setTimeout(()=>{ el.style.display='none'; },3200);
  }
  async function api(path, opts){
    const r=await fetch(path, Object.assign({credentials:'omit'}, opts||{}));
    const txt=await r.text();
    let j=null; try{ j=JSON.parse(txt); }catch(e){}
    if(!r.ok) throw new Error(apiErr(j,txt)||('HTTP '+r.status));
    return j;
  }
  function openModal(item){
    S.editing=item;
    document.getElementById('mt').textContent=t('request')+' #'+item.demande_id+' — '+(item.code_postal_destination||'');
    document.getElementById('prix').value = item.prix!=null ? String(item.prix) : '';
    document.getElementById('delai').value = item.delai_jours!=null ? String(item.delai_jours) : '';
    document.getElementById('com').value = item.commentaire||'';
    document.getElementById('ov').style.display='flex';
    setTimeout(()=>{ document.getElementById('prix').focus(); },0);
  }
  function closeModal(){ document.getElementById('ov').style.display='none'; S.editing=null; }

  function render(){
    const who=document.getElementById('who');
    const list=document.getElementById('list');
    const d=S.data;
    who.textContent = d ? (t('account')+': '+(d.email||t('dash'))) : t('loading');
    list.innerHTML='';
    const rows=(d&&d.demandes)||[];
    if(!rows.length){
      list.innerHTML = '<div class="d"><h3>'+esc(t('noRequests'))+'</h3><div class="meta">'+esc(t('noRequestsDesc'))+'</div></div>';
      return;
    }
    rows.forEach(it=>{
      const meta = [
        it.poids_total_kg!=null ? (it.poids_total_kg+' kg') : null,
        it.nb_palette!=null ? (it.nb_palette+' '+t('pallets')) : null,
        it.type_envoi ? typeLabel(it.type_envoi) : null,
        it.contraintes ? (t('constraints')+': '+it.contraintes) : null,
      ].filter(Boolean).join(' · ');
      const canReply = it.demande_statut!=='cloturee' && !['retenue','recue'].includes(it.reponse_statut);
      const btn = canReply ? '<button class="btn btn-accent" data-id="'+it.demande_id+'">'+esc(t('reply'))+'</button>' : '';
      const deja = !canReply && it.prix!=null ? '<span class="muted">'+esc(t('saved'))+'</span>' : '';
      const priceTxt = it.prix!=null ? (t('price')+': <strong>'+Number(it.prix).toFixed(2)+' €</strong>') : (t('price')+': '+t('dash'));
      const delTxt = it.delai_jours!=null ? (t('delay')+': <strong>J+'+it.delai_jours+'</strong>') : (t('delay')+': '+t('dash'));
      const html = '<div class="d"><h3>'+esc(t('request'))+' #'+it.demande_id+' — '+esc(it.code_postal_destination||'')+'</h3>'
        +'<div class="meta"><span class="muted">'+esc(meta||'')+'</span>'+deja+'<br>'
        +'<span class="muted">'+esc(t('created'))+' '+(it.created_at||'').slice(0,10)+'</span></div>'
        +'<div class="row" style="justify-content:space-between"><div class="meta">'+priceTxt+' · '+delTxt+'</div>'+btn+'</div></div>';
      const wrap=document.createElement('div');
      wrap.innerHTML=html;
      const node=wrap.firstElementChild;
      const b=node.querySelector('button[data-id]');
      if(b) b.addEventListener('click',()=>openModal(it));
      list.appendChild(node);
    });
  }

  async function load(){
    S.data = await api('/api/portail/expe/'+encodeURIComponent(TOKEN));
    render();
  }

  document.getElementById('langBtn').addEventListener('click',()=>{
    setLang(S.lang==='fr'?'en':'fr');
  });
  document.getElementById('mx').addEventListener('click',closeModal);
  document.getElementById('cancel').addEventListener('click',closeModal);
  document.getElementById('ov').addEventListener('click',e=>{ if(e.target.id==='ov') closeModal(); });
  document.getElementById('save').addEventListener('click', async ()=>{
    const it=S.editing; if(!it) return;
    const prix=parseFloat(document.getElementById('prix').value);
    const delai=parseInt(document.getElementById('delai').value,10);
    if(!isFinite(prix) || prix<=0){ showToast(t('toastPrice'), 'bad'); return; }
    if(!isFinite(delai) || delai<0){ showToast(t('toastDelay'), 'bad'); return; }
    try{
      await api('/api/portail/expe/'+encodeURIComponent(TOKEN)+'/demandes/'+it.demande_id+'/repondre', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          reponse_id: it.reponse_id,
          prix,
          delai_jours: delai,
          commentaire: (document.getElementById('com').value||'').trim()||null
        })
      });
      showToast(t('toastSaved'), 'ok');
      closeModal();
      await load();
    }catch(e){ showToast(e.message||t('error'), 'bad'); }
  });

  document.getElementById('themeBtn').addEventListener('click',()=>{
    document.body.classList.toggle('light');
    try{ localStorage.setItem('mysifa_theme', document.body.classList.contains('light')?'light':'dark'); }catch(e){}
  });
  try{ if(localStorage.getItem('mysifa_theme')==='light') document.body.classList.add('light'); }catch(e){}

  S.lang=readLang();
  applyI18n();
  load().catch(e=>{ document.getElementById('who').textContent=t('error'); showToast(e.message||t('error'), 'bad'); });
  </script>
</body>
</html>"""
    return (
        html.replace("__TOKEN_JS__", token_js)
        .replace("__LANG_JS__", lang_js)
        .replace("__I18N_JS__", i18n_js)
    )

