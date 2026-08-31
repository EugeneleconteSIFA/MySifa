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
      <div class="foot-note" id="i18n-foot-note">Portail sécurisé SIFA</div>
    </footer>
"""


def get_portail_404_html() -> str:
    return """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#0a0e17">
  <title>Lien invalide — SIFA</title>
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
<script src="/static/mysifa_impersonate.js"></script>
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
  <title>Portail transporteur — SIFA</title>
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
      --success:#059669;--warn:#d24b00;--danger:#dc2626;
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
    .list{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px;margin-top:12px}
    /* Carte demande — une hiérarchie explicite plutôt qu'un empilement de
       lignes grises : en-tête, faits chiffrés, contrainte, échéance, offre,
       documents. Une seule couleur d'accent (le CP et les liens), une seule
       couleur d'alerte à la fois. */
    .d{background:var(--bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;
      display:flex;flex-direction:column}
    .d.closed{opacity:.7}
    .d-head{padding:14px 16px;border-bottom:1px solid var(--border);
      background:color-mix(in srgb,var(--card) 55%,transparent)}
    .d-ref{font-size:12px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;
      color:var(--muted);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .d-cp{display:flex;align-items:baseline;gap:10px;margin-top:6px}
    .d-cp-lbl{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
    .d-cp-val{font-size:26px;font-weight:800;letter-spacing:-.5px;color:var(--accent);line-height:1.1}
    .d.closed .d-cp-val{color:var(--text2)}
    .badge{display:inline-flex;align-items:center;padding:2px 10px;border-radius:20px;font-size:10px;font-weight:800;letter-spacing:.4px;text-transform:uppercase}
    .badge-closed{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger);border:1px solid color-mix(in srgb,var(--danger) 40%,transparent)}
    /* Faits chiffrés : les cinq informations étaient concaténées avec des
       points médians, rien ne distinguait un poids d'une contrainte. */
    /* Filets par `gap` sur fond bordure plutôt que `border-right` : les
       tuiles reviennent à la ligne selon la largeur de la carte, et un
       border-right laisserait des filets orphelins en bout de rangée. */
    /* Deux colonnes fixes et non `auto-fit` : la largeur qui compte est celle
       de la CARTE, pas celle de la fenêtre, et `auto-fit` laissait des cases
       vides en fin de rangée — qui se voient, puisque le fond du conteneur
       fait le filet. */
    .facts{display:grid;grid-template-columns:repeat(2,1fr);
      gap:1px;background:var(--border);border-bottom:1px solid var(--border)}
    .fact{padding:9px 12px;background:var(--bg);display:flex;flex-direction:column;gap:3px;min-width:0}
    /* Nombre impair de faits : la dernière tuile prend la rangée entière. */
    .fact:last-child:nth-child(odd){grid-column:1 / -1}
    .fact-l{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .fact-v{font-size:14px;font-weight:700;color:var(--text);line-height:1.3;overflow-wrap:anywhere}
    .note{padding:10px 16px;border-bottom:1px solid var(--border);
      background:color-mix(in srgb,var(--warn) 6%,transparent)}
    .note-l{display:block;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
      color:var(--warn);margin-bottom:3px}
    .note-v{font-size:13px;color:var(--text2);line-height:1.5}
    .dl{display:flex;align-items:center;justify-content:space-between;gap:10px;
      padding:9px 16px;border-bottom:1px solid var(--border);font-size:12px}
    .dl-l{font-weight:700;color:var(--text2);text-transform:uppercase;font-size:10px;letter-spacing:.5px}
    .dl-v{font-size:14px;font-weight:800;color:var(--text);font-variant-numeric:tabular-nums}
    .dl-late{background:color-mix(in srgb,var(--danger) 10%,transparent)}
    .dl-late .dl-l,.dl-late .dl-v{color:var(--danger)}
    /* Le bloc offre : c'est l'action attendue, il doit se voir en premier
       coup d'œil et ne pas ressembler au reste de la carte. */
    .offer{padding:14px 16px;border-bottom:1px solid var(--border)}
    .offer-t{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
      color:var(--muted);margin-bottom:8px}
    .offer-todo{background:color-mix(in srgb,var(--accent) 7%,transparent)}
    .offer-ask{font-size:13px;color:var(--text2);margin-bottom:12px;line-height:1.5}
    .offer-done{background:color-mix(in srgb,var(--success) 7%,transparent)}
    .offer-vals{display:flex;align-items:baseline;gap:10px}
    .offer-v{font-size:20px;font-weight:800;color:var(--success);font-variant-numeric:tabular-nums}
    .offer-sep{color:var(--muted)}
    .offer-c{font-size:12px;color:var(--text2);margin-top:6px;line-height:1.5}
    .btn-sm{padding:6px 12px;font-size:12px;margin-top:10px}
    .sect{padding:12px 16px;border-bottom:1px solid var(--border)}
    .sect-t{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
      color:var(--muted);margin-bottom:7px}
    .d-foot{padding:9px 16px;font-size:11px;color:var(--muted);margin-top:auto}
    .closed-note{margin:12px 16px;padding:8px 12px;background:color-mix(in srgb,var(--danger) 8%,transparent);border-left:3px solid var(--danger);border-radius:6px;font-size:12px;color:var(--text2);line-height:1.55}
    .fl{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--accent);
      text-decoration:none;padding:3px 0;line-height:1.4}
    .fl svg{flex-shrink:0}
    .fl:hover span{text-decoration:underline}
    .upl{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;cursor:pointer;
      padding:8px 14px;border:1px dashed var(--border);border-radius:9px;color:var(--text2)}
    .upl:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
    .files-h{font-size:11px;color:var(--muted);margin-top:7px;line-height:1.5}
    /* Fichier choisi mais pas encore parti : il doit se distinguer d'un
       fichier déjà déposé, sinon on croit l'envoi déjà fait. */
    .fl-pending{color:var(--text2);cursor:default}
    .fl-pending span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .fl-tag{font-style:normal;font-size:10px;font-weight:800;text-transform:uppercase;
      letter-spacing:.5px;color:var(--warn);white-space:nowrap}
    .fl-x{width:22px;height:22px;flex-shrink:0;border-radius:6px;border:1px solid var(--border);
      background:transparent;color:var(--muted);cursor:pointer;font-size:14px;line-height:1}
    .fl-x:hover{border-color:var(--danger);color:var(--danger)}
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
        <strong>SIFA</strong>
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
      <div style="margin-top:12px">
        <label id="i18n-label-files">Pièces jointes (optionnel)</label>
        <div id="m-files"></div>
        <label class="upl" for="m-file-input" id="i18n-add-file">Joindre un fichier</label>
        <input type="file" id="m-file-input" hidden>
        <div class="files-h" id="i18n-file-hint"></div>
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
  const S = { data:null, editing:null, lang: INIT_LANG, pendingFiles: [] };

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
    const lf=document.getElementById('i18n-label-files'); if(lf) lf.textContent=t('labelFiles');
    const af=document.getElementById('i18n-add-file'); if(af) af.innerHTML=CLIP+' '+esc(t('addFile'));
    const fh=document.getElementById('i18n-file-hint'); if(fh) fh.textContent=t('fileHint');
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
  // Fichiers choisis dans le modal mais pas encore partis. Ils ne sont envoyés
  // qu'APRÈS l'enregistrement de l'offre : si le prix est refusé, on ne laisse
  // pas un fichier orphelin rattaché à une réponse qui n'existe pas encore.
  function renderModalFiles(){
    const zone=document.getElementById('m-files');
    const it=S.editing;
    if(!zone) return;
    zone.innerHTML='';
    const deja=(it&&it.mes_fichiers)||[];
    deja.forEach(function(p){
      const a=document.createElement('a');
      a.className='fl';
      a.href='/portail/expe/'+encodeURIComponent(TOKEN)+'/pj/'+p.id;
      a.target='_blank'; a.rel='noopener';
      a.innerHTML=CLIP+'<span>'+esc(p.filename||'')+'</span>';
      zone.appendChild(a);
    });
    S.pendingFiles.forEach(function(f,i){
      const row=document.createElement('div');
      row.className='fl fl-pending';
      row.innerHTML=CLIP+'<span>'+esc(f.name)+'</span>'
        +'<em class="fl-tag">'+esc(t('pendingFiles'))+'</em>';
      const del=document.createElement('button');
      del.type='button'; del.className='fl-x'; del.textContent='×'; del.title=t('remove');
      del.addEventListener('click',function(){ S.pendingFiles.splice(i,1); renderModalFiles(); });
      row.appendChild(del);
      zone.appendChild(row);
    });
    const add=document.getElementById('i18n-add-file');
    if(add) add.style.display=(deja.length+S.pendingFiles.length>=5)?'none':'inline-flex';
  }

  function openModal(item){
    S.editing=item;
    S.pendingFiles=[];
    const ref = item.reference ? (t('request')+' '+item.reference) : (t('request')+' #'+item.demande_id);
    document.getElementById('mt').textContent=ref+' — '+(item.code_postal_destination||'');
    document.getElementById('prix').value = item.prix!=null ? String(item.prix) : '';
    document.getElementById('delai').value = item.delai_jours!=null ? String(item.delai_jours) : '';
    document.getElementById('com').value = item.commentaire||'';
    renderModalFiles();
    document.getElementById('ov').style.display='flex';
    setTimeout(()=>{ document.getElementById('prix').focus(); },0);
  }
  function closeModal(){
    document.getElementById('ov').style.display='none';
    S.editing=null; S.pendingFiles=[];
  }

  // Trombone en SVG inline plutôt qu'en emoji : l'emoji dépend de la police
  // installée sur le poste du transporteur et casse l'alignement des lignes.
  const CLIP='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    +'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
    +'><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19'
    +'a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>';

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
      const paletteKey = it.type_palette ? String(it.type_palette).trim().toLowerCase() : '';
      const paletteLabelKey = paletteKey ? ('pallet_'+paletteKey) : '';
      const paletteLabel = paletteLabelKey && t(paletteLabelKey)!==paletteLabelKey ? t(paletteLabelKey) : paletteKey;
      const isClosed = it.demande_statut==='cloturee';
      const aRepondu = it.prix!=null;
      const canReply = !isClosed;

      // ── En-tête : référence + code postal en évidence ──
      // Le CP est LA donnée sur laquelle un transporteur décide s'il chiffre
      // ou non. Il était noyé dans le titre, il devient le point d'ancrage.
      const ref = it.reference ? (t('request')+' '+it.reference) : (t('request')+' #'+it.demande_id);
      const closedBadge = isClosed ? '<span class="badge badge-closed">'+esc(t('closedBadge'))+'</span>' : '';
      const head = '<div class="d-head">'
        +'<div class="d-ref">'+esc(ref)+closedBadge+'</div>'
        +'<div class="d-cp"><span class="d-cp-lbl">'+esc(t('destination'))+'</span>'
        +'<span class="d-cp-val">'+esc(it.code_postal_destination||t('dash'))+'</span></div>'
        +'</div>';

      // ── Faits : une tuile par donnée, plutôt qu'une ligne grise unique ──
      // Les cinq informations étaient concaténées avec des points médians :
      // rien ne distinguait le poids d'une contrainte de livraison.
      const fait=function(lbl,val){
        return val ? '<div class="fact"><span class="fact-l">'+esc(lbl)+'</span>'
          +'<span class="fact-v">'+esc(val)+'</span></div>' : '';
      };
      const facts = '<div class="facts">'
        + fait(t('weight'), it.poids_total_kg!=null ? (it.poids_total_kg+' kg') : '')
        + fait(t('pallets'), it.nb_palette!=null ? String(it.nb_palette) : '')
        + fait(t('shipmentType'), it.type_envoi ? typeLabel(it.type_envoi) : '')
        + fait(t('palletType'), paletteLabel)
        + '</div>';

      // ── Contraintes : encadré à part, jamais fondu dans les faits ──
      const note = it.contraintes
        ? '<div class="note"><span class="note-l">'+esc(t('constraints'))+'</span>'
          +'<span class="note-v">'+esc(it.contraintes)+'</span></div>'
        : '';

      // ── Échéance : un seul bandeau, une seule couleur à la fois ──
      let dlNote='';
      const dl=(it.date_limite||'').slice(0,10);
      if(dl && !isClosed){
        const auj=new Date().toISOString().slice(0,10);
        const tard = dl<auj;
        dlNote = '<div class="dl'+(tard?' dl-late':'')+'">'
          +'<span class="dl-l">'+esc(tard?t('deadlineLate'):t('deadline'))+'</span>'
          +'<span class="dl-v">'+esc(dl)+'</span></div>';
      }

      // ── Votre offre : le bloc qui appelle à l'action ──
      let offre;
      if(aRepondu){
        offre = '<div class="offer offer-done">'
          +'<div class="offer-t">'+esc(t('yourOffer'))+'</div>'
          +'<div class="offer-vals"><span class="offer-v">'+Number(it.prix).toFixed(2)+' €</span>'
          +'<span class="offer-sep">·</span><span class="offer-v">J+'+esc(it.delai_jours)+'</span></div>'
          + (it.commentaire ? '<div class="offer-c">'+esc(it.commentaire)+'</div>' : '')
          + (canReply ? '<button class="btn btn-ghost btn-sm" data-id="'+it.demande_id+'">'+esc(t('editReply'))+'</button>' : '')
          +'</div>';
      }else if(canReply){
        offre = '<div class="offer offer-todo">'
          +'<div class="offer-t">'+esc(t('yourOffer'))+'</div>'
          +'<div class="offer-ask">'+esc(t('awaitingOffer'))+'</div>'
          +'<button class="btn btn-accent" data-id="'+it.demande_id+'">'+esc(t('reply'))+'</button>'
          +'</div>';
      }else{
        offre = '';
      }

      // ── Documents ──
      const docs=(it.pieces_jointes||[]);
      const mine=(it.mes_fichiers||[]);
      const lien=function(p){
        return '<a class="fl" href="/portail/expe/'+encodeURIComponent(TOKEN)+'/pj/'+p.id
          +'" target="_blank" rel="noopener">'+CLIP+'<span>'+esc(p.filename||'')+'</span></a>';
      };
      const sect=function(titre,contenu){
        return '<div class="sect"><div class="sect-t">'+esc(titre)+'</div>'+contenu+'</div>';
      };
      const docsHtml = docs.length ? sect(t('docs'), docs.map(lien).join('')) : '';
      const mineHtml = mine.length ? sect(t('myFiles'), mine.map(lien).join('')) : '';

      const closedNote = isClosed ? '<div class="closed-note">'+esc(t('closedNote'))+'</div>' : '';
      const cree = '<div class="d-foot">'+esc(t('created'))+' '+esc((it.created_at||'').slice(0,10))+'</div>';

      const wrap=document.createElement('div');
      wrap.innerHTML = '<div class="d'+(isClosed?' closed':'')+'">'
        +head+facts+note+dlNote+offre+docsHtml+mineHtml+closedNote+cree+'</div>';
      const node=wrap.firstElementChild;
      node.querySelectorAll('button[data-id]').forEach(function(b){
        b.addEventListener('click',()=>openModal(it));
      });
      list.appendChild(node);
    });
  }

  async function load(){
    S.data = await api('/api/portail/expe/'+encodeURIComponent(TOKEN));
    render();
  }

  // Dépôt d'un fichier joint à l'offre. Sans cela, la cotation PDF partait par
  // mail à côté du portail et n'entrait jamais dans le comparatif.
  // Retourne true/false plutôt que de lever : l'appelant enchaîne plusieurs
  // fichiers et un échec sur l'un ne doit pas annuler les autres.
  async function envoyerFichier(demandeId, f){
    const fd=new FormData(); fd.append('file', f);
    try{
      const r=await fetch('/api/portail/expe/'+encodeURIComponent(TOKEN)+'/demandes/'+demandeId+'/piece-jointe',
        {method:'POST', body:fd});
      if(!r.ok){
        let msg=t('error');
        try{ const j=await r.json(); msg=j.detail||msg; }catch(e){}
        showToast(msg, 'bad');
        return false;
      }
      return true;
    }catch(e){ showToast(e.message||t('error'), 'bad'); return false; }
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
      // L'offre est enregistrée : on peut envoyer les fichiers. Un échec
      // d'upload ne remet pas l'offre en cause, il est signalé à part.
      let ko=0;
      for(const f of S.pendingFiles){
        const ok=await envoyerFichier(it.demande_id, f);
        if(!ok) ko++;
      }
      showToast(ko?(t('toastSaved')+' — '+ko+' '+t('error')):t('toastSaved'), ko?'bad':'ok');
      closeModal();
      await load();
    }catch(e){ showToast(e.message||t('error'), 'bad'); }
  });

  document.getElementById('m-file-input').addEventListener('change',function(ev){
    const f=(ev.target.files&&ev.target.files[0])||null;
    ev.target.value='';
    if(!f) return;
    if(f.size > 20*1024*1024){ showToast(t('fileTooBig'), 'bad'); return; }
    S.pendingFiles.push(f);
    renderModalFiles();
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

