"""MySifa — Portail fournisseur public : questionnaire EUDR.

Page autonome ouverte par le lien de l'email (`/portail/eudr/<jeton>`), sans
compte. En anglais, français ou espagnol : sélecteur en haut de page, langue
initiale = ?lang= de l'adresse, sinon celle de la demande.
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


# Textes du formulaire par langue. __ORG__ est remplacé par le nom de
# l'entreprise. Les libellés des choix viennent de l'API (config.EUDR_CHOIX).
_I18N = {
    "en": {
        "brand": "__ORG__ · Supplier portal", "title": "EUDR questionnaire",
        "lead": "Regulation (EU) 2023/1115 on deforestation-free products — questionnaire for",
        "loading": "Loading…", "invalid": "Invalid or expired link.",
        "network_load": "Network error — please reload the page.",
        "already": "You already answered on {d}. Your previous answers are pre-filled — submitting again records an update.",
        "s_company": "Your company", "q_etab": "Where is the company invoicing __ORG__ established?",
        "s_scope": "Scope", "q_scope": "Do the products you supply to __ORG__ fall under the EUDR?",
        "h_scope": "Paper and paperboard (chapters 47 and 48 of the Combined Nomenclature) are in scope; plastic films are not.",
        "q_cn": "CN / HS codes of the products concerned", "h_cn": "For example 4810 92, 4821 10.",
        "q_role": "Your role under the EUDR",
        "q_date": "From which date will your due diligence statements cover our deliveries?",
        "s_refs": "Reference numbers",
        "q_trans": "How will you send us the reference and verification numbers of the due diligence statements?",
        "q_detail": "Details", "ph_detail": "Format, field on the document, portal address…",
        "q_perdel": "Will each delivery carry its own reference number?",
        "q_amont": "Your upstream suppliers",
        "h_amont": "If you do not file the statement yourself: who does (paper mill, pulp supplier, importer)?",
        "ph_amont": "Company name and country",
        "s_origin": "Origin of the wood",
        "h_origin": "For goods shipped from outside the EU, __ORG__ files the due diligence statement and needs the following data.",
        "q_geo": "Can you provide the geolocation of the plots of land where the wood was harvested?",
        "q_species": "Wood species (scientific and common name)", "q_countries": "Countries of harvest",
        "s_contacts": "Contacts", "q_name": "Your name", "q_position": "Your position", "q_email": "Your email",
        "q_cname": "EUDR contact person (if different)", "q_cemail": "EUDR contact email", "q_comment": "Comments",
        "submit": "Submit my answers", "e_role": "Please indicate your role under the EUDR.",
        "e_name": "Please enter your name.", "e_email": "Please enter a valid email address.",
        "e_submit": "Submission failed — please try again.", "e_network": "Network error — please try again.",
        "done_t": "Thank you — your answers have been recorded.",
        "done_p": "You can come back to this page with the same link to update them.",
        "foot": "__ORG__ supplier portal — personal link, do not share.",
        "preview": "Preview — this is what the supplier sees. Nothing is sent.",
    },
    "fr": {
        "brand": "__ORG__ · Portail fournisseur", "title": "Questionnaire EUDR",
        "lead": "Règlement (UE) 2023/1115 relatif aux produits zéro déforestation — questionnaire pour",
        "loading": "Chargement…", "invalid": "Lien invalide ou expiré.",
        "network_load": "Erreur réseau — rechargez la page.",
        "already": "Vous avez déjà répondu le {d}. Vos réponses sont préremplies — un nouvel envoi enregistre une mise à jour.",
        "s_company": "Votre entreprise", "q_etab": "Où est établie la société qui facture __ORG__ ?",
        "s_scope": "Périmètre", "q_scope": "Les produits que vous livrez à __ORG__ entrent-ils dans le périmètre de l'EUDR ?",
        "h_scope": "Le papier et le carton (chapitres 47 et 48 de la nomenclature combinée) sont concernés ; les films plastiques ne le sont pas.",
        "q_cn": "Codes NC / SH des produits concernés", "h_cn": "Par exemple 4810 92, 4821 10.",
        "q_role": "Votre rôle au sens de l'EUDR",
        "q_date": "À partir de quelle date vos déclarations de diligence raisonnée couvriront-elles nos livraisons ?",
        "s_refs": "Numéros de référence",
        "q_trans": "Comment nous transmettrez-vous les numéros de référence et de vérification des déclarations de diligence raisonnée ?",
        "q_detail": "Précisions", "ph_detail": "Format, champ du document, adresse du portail…",
        "q_perdel": "Chaque livraison portera-t-elle son propre numéro de référence ?",
        "q_amont": "Vos fournisseurs amont",
        "h_amont": "Si vous ne déposez pas la déclaration vous-même : qui la dépose (papeterie, fournisseur de pâte, importateur) ?",
        "ph_amont": "Raison sociale et pays",
        "s_origin": "Origine du bois",
        "h_origin": "Pour les marchandises expédiées hors de l'UE, __ORG__ dépose la déclaration de diligence raisonnée et a besoin des données suivantes.",
        "q_geo": "Pouvez-vous fournir la géolocalisation des parcelles où le bois a été récolté ?",
        "q_species": "Essences de bois (nom scientifique et nom commun)", "q_countries": "Pays de récolte",
        "s_contacts": "Contacts", "q_name": "Votre nom", "q_position": "Votre fonction", "q_email": "Votre email",
        "q_cname": "Contact EUDR (si différent)", "q_cemail": "Email du contact EUDR", "q_comment": "Commentaires",
        "submit": "Envoyer mes réponses", "e_role": "Indiquez votre rôle au sens de l'EUDR.",
        "e_name": "Indiquez votre nom.", "e_email": "Indiquez une adresse email valide.",
        "e_submit": "Envoi impossible — réessayez.", "e_network": "Erreur réseau — réessayez.",
        "done_t": "Merci — vos réponses sont enregistrées.",
        "done_p": "Vous pouvez revenir sur cette page avec le même lien pour les mettre à jour.",
        "foot": "Portail fournisseur __ORG__ — lien personnel, ne pas partager.",
        "preview": "Aperçu — c'est ce que voit le fournisseur. Rien n'est envoyé.",
    },
    "es": {
        "brand": "__ORG__ · Portal de proveedores", "title": "Cuestionario EUDR",
        "lead": "Reglamento (UE) 2023/1115 relativo a los productos libres de deforestación — cuestionario para",
        "loading": "Cargando…", "invalid": "Enlace no válido o caducado.",
        "network_load": "Error de red — vuelva a cargar la página.",
        "already": "Ya respondió el {d}. Sus respuestas anteriores aparecen rellenadas — un nuevo envío registra una actualización.",
        "s_company": "Su empresa", "q_etab": "¿Dónde está establecida la empresa que factura a __ORG__?",
        "s_scope": "Ámbito", "q_scope": "¿Los productos que suministran a __ORG__ están incluidos en el ámbito del EUDR?",
        "h_scope": "El papel y el cartón (capítulos 47 y 48 de la Nomenclatura Combinada) están incluidos; las películas plásticas no.",
        "q_cn": "Códigos NC / SA de los productos afectados", "h_cn": "Por ejemplo 4810 92, 4821 10.",
        "q_role": "Su papel según el EUDR",
        "q_date": "¿A partir de qué fecha sus declaraciones de diligencia debida cubrirán nuestras entregas?",
        "s_refs": "Números de referencia",
        "q_trans": "¿Cómo nos enviarán los números de referencia y de verificación de las declaraciones de diligencia debida?",
        "q_detail": "Detalles", "ph_detail": "Formato, campo del documento, dirección del portal…",
        "q_perdel": "¿Cada entrega llevará su propio número de referencia?",
        "q_amont": "Sus proveedores anteriores en la cadena",
        "h_amont": "Si no presentan ustedes la declaración: ¿quién la presenta (fábrica de papel, proveedor de pasta, importador)?",
        "ph_amont": "Razón social y país",
        "s_origin": "Origen de la madera",
        "h_origin": "Para las mercancías enviadas desde fuera de la UE, __ORG__ presenta la declaración de diligencia debida y necesita los datos siguientes.",
        "q_geo": "¿Pueden facilitar la geolocalización de las parcelas donde se cosechó la madera?",
        "q_species": "Especies de madera (nombre científico y común)", "q_countries": "Países de cosecha",
        "s_contacts": "Contactos", "q_name": "Su nombre", "q_position": "Su cargo", "q_email": "Su correo electrónico",
        "q_cname": "Contacto EUDR (si es distinto)", "q_cemail": "Correo del contacto EUDR", "q_comment": "Comentarios",
        "submit": "Enviar mis respuestas", "e_role": "Indique su papel según el EUDR.",
        "e_name": "Indique su nombre.", "e_email": "Indique una dirección de correo válida.",
        "e_submit": "No se pudo enviar — inténtelo de nuevo.", "e_network": "Error de red — inténtelo de nuevo.",
        "done_t": "Gracias — sus respuestas han quedado registradas.",
        "done_p": "Puede volver a esta página con el mismo enlace para actualizarlas.",
        "foot": "Portal de proveedores de __ORG__ — enlace personal, no compartir.",
        "preview": "Vista previa — esto es lo que ve el proveedor. No se envía nada.",
    },
}


def get_eudr_portail_html(token: str, apercu: dict | None = None) -> str:
    """Page du formulaire. `apercu` : données factices servies par MyQualité
    (bouton « Aperçu du questionnaire ») — la page ne contacte alors aucune API
    et n'enregistre rien."""
    org = APP_ORG_NAME
    i18n = json.dumps(_I18N, ensure_ascii=False).replace("__ORG__", org).replace("</", "<\\/")
    return (_PAGE
            .replace("__HEAD__", _HEAD)
            .replace("__ORG_HTML__", _esc(org))
            .replace("__I18N__", i18n)
            .replace("__TOKEN__", json.dumps(token))
            .replace("__APERCU__", json.dumps(apercu, ensure_ascii=False).replace("</", "<\\/")))


_PAGE = r"""<!DOCTYPE html>
<html lang="en"><head>__HEAD__<title>EUDR — __ORG_HTML__</title>
<style>
  .top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:6px}
  .langs{display:flex;gap:4px}
  .langs button{padding:5px 10px;border-radius:8px;border:1px solid var(--border);background:var(--card);
    color:var(--text2);font:inherit;font-size:12px;font-weight:700;cursor:pointer}
  .langs button.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
</style>
</head>
<body><div class="wrap">
  <div class="top">
    <div class="brand" id="t-brand"></div>
    <div class="langs" id="langs">
      <button type="button" data-l="en">EN</button><button type="button" data-l="fr">FR</button><button type="button" data-l="es">ES</button>
    </div>
  </div>
  <div class="card" id="t-preview" style="display:none;border-color:var(--accent);color:var(--accent);font-weight:700;font-size:13px;padding:12px 16px"></div>
  <h1 id="t-title"></h1>
  <p class="lead" id="lead"></p>
  <div id="root"><div class="card" id="t-loading"></div></div>
  <div class="foot" id="t-foot"></div>
</div>
<script>
const TOKEN = __TOKEN__;
const APERCU = __APERCU__;
const API = '/api/portail/eudr/' + encodeURIComponent(TOKEN);
const I18N = __I18N__;
let D = null;
let LANG = (new URLSearchParams(location.search).get('lang') || '').slice(0,2).toLowerCase();
if(!I18N[LANG]) LANG = '';
const t = k => (I18N[LANG || 'en'] || I18N.en)[k] || I18N.en[k] || k;

function esc(s){ const d=document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML; }

function entete(){
  document.documentElement.lang = LANG || 'en';
  document.getElementById('t-brand').textContent = t('brand');
  document.getElementById('t-title').textContent = t('title');
  document.getElementById('t-foot').textContent = t('foot');
  const pv = document.getElementById('t-preview');
  if(APERCU){ pv.style.display = 'block'; pv.textContent = t('preview'); }
  document.getElementById('lead').textContent = D ? t('lead') + ' ' + D.fournisseur + '.' : '';
  document.querySelectorAll('#langs button').forEach(b => b.classList.toggle('on', b.dataset.l === (LANG||'en')));
}

// Valeurs en cours de saisie : reprises quand on change de langue.
function valeurs(){
  const f = document.getElementById('f'); if(!f) return null;
  const v = {}; new FormData(f).forEach((x,k) => { v[k] = x; }); return v;
}

function radios(name, cur, req){
  const opts = (D.choix[LANG][name]||{});
  return '<div class="opts">' + Object.keys(opts).map(k =>
    '<label class="opt"><input type="radio" name="'+name+'" value="'+esc(k)+'"'+(cur[name]===k?' checked':'')+
    (req?' required':'')+'><span>'+esc(opts[k])+'</span></label>').join('') + '</div>';
}
function txt(name, cur, type){ return '<input type="'+(type||'text')+'" name="'+name+'" value="'+esc(cur[name]||'')+'">'; }
function area(name, cur, ph){ return '<textarea name="'+name+'" placeholder="'+esc(ph||'')+'">'+esc(cur[name]||'')+'</textarea>'; }

function render(cur){
  entete();
  const p = D.precedente || {};
  cur = cur || Object.assign({repondant_email: D.email || ''}, p);
  const req = ' <span class="req">*</span>';
  document.getElementById('root').innerHTML = `
  <form id="f" novalidate>
    ${D.precedente ? '<div class="card"><p class="note" style="margin:0">'+esc(t('already').replace('{d}', (p.created_at||'').slice(0,10)))+'</p></div>' : ''}
    <div class="card"><h2>${esc(t('s_company'))}</h2>
      <div class="q"><div class="ql">${esc(t('q_etab'))}</div>${radios('etablissement', cur)}</div>
    </div>
    <div class="card"><h2>${esc(t('s_scope'))}</h2>
      <div class="q"><div class="ql">${esc(t('q_scope'))}</div><div class="hint">${esc(t('h_scope'))}</div>${radios('perimetre', cur)}</div>
      <div class="q"><label>${esc(t('q_cn'))}</label><div class="hint">${esc(t('h_cn'))}</div>${txt('codes_nc', cur)}</div>
      <div class="q"><div class="ql">${esc(t('q_role'))}${req}</div>${radios('role', cur, true)}</div>
      <div class="q"><label>${esc(t('q_date'))}</label>${txt('date_debut_dds', cur, 'date')}</div>
    </div>
    <div class="card"><h2>${esc(t('s_refs'))}</h2>
      <div class="q"><div class="ql">${esc(t('q_trans'))}</div>${radios('transmission', cur)}</div>
      <div class="q"><label>${esc(t('q_detail'))}</label>${area('transmission_detail', cur, t('ph_detail'))}</div>
      <div class="q"><div class="ql">${esc(t('q_perdel'))}</div>${radios('ref_par_livraison', cur)}</div>
      <div class="q"><label>${esc(t('q_amont'))}</label><div class="hint">${esc(t('h_amont'))}</div>${area('amont', cur, t('ph_amont'))}</div>
    </div>
    <div class="card nonue" id="bloc-nonue"><h2>${esc(t('s_origin'))}</h2>
      <p class="note" style="margin:-6px 0 14px">${esc(t('h_origin'))}</p>
      <div class="q"><div class="ql">${esc(t('q_geo'))}</div>${radios('geolocalisation', cur)}</div>
      <div class="row">
        <div class="q"><label>${esc(t('q_species'))}</label>${txt('essences', cur)}</div>
        <div class="q"><label>${esc(t('q_countries'))}</label>${txt('pays_recolte', cur)}</div>
      </div>
    </div>
    <div class="card"><h2>${esc(t('s_contacts'))}</h2>
      <div class="row">
        <div class="q"><label>${esc(t('q_name'))}${req}</label>${txt('repondant_nom', cur)}</div>
        <div class="q"><label>${esc(t('q_position'))}</label>${txt('repondant_fonction', cur)}</div>
      </div>
      <div class="q"><label>${esc(t('q_email'))}${req}</label>${txt('repondant_email', cur, 'email')}</div>
      <div class="row">
        <div class="q"><label>${esc(t('q_cname'))}</label>${txt('contact_nom', cur)}</div>
        <div class="q"><label>${esc(t('q_cemail'))}</label>${txt('contact_email', cur, 'email')}</div>
      </div>
      <div class="q"><label>${esc(t('q_comment'))}</label>${area('commentaire', cur, '')}</div>
    </div>
    <div class="card">
      <button type="submit" class="btn" id="go">${esc(t('submit'))}</button>
      <div class="err" id="err"></div>
    </div>
  </form>`;
  const f = document.getElementById('f');
  const majNonUe = () => {
    const v = (f.querySelector('input[name=etablissement]:checked')||{}).value;
    document.getElementById('bloc-nonue').style.display = v === 'non_eu' ? 'block' : 'none';
  };
  f.addEventListener('change', majNonUe); majNonUe();
  f.addEventListener('submit', envoyer);
}

function changerLangue(l){
  if(!I18N[l] || l === LANG) return;
  const cur = valeurs();
  LANG = l;
  try{ const u = new URL(location.href); u.searchParams.set('lang', l); history.replaceState(null, '', u); }catch(e){}
  if(D && cur){
    render(cur);
    if(!APERCU) fetch(API + '/langue', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({langue:l})}).catch(() => {});
  } else {
    entete();
    const ld = document.getElementById('t-loading'); if(ld) ld.textContent = t('loading');
  }
}
document.querySelectorAll('#langs button').forEach(b => b.addEventListener('click', () => changerLangue(b.dataset.l)));

async function envoyer(ev){
  ev.preventDefault();
  const body = valeurs(); body.langue = LANG;
  const err = document.getElementById('err'), go = document.getElementById('go');
  err.textContent = '';
  if(!body.role){ err.textContent = t('e_role'); return; }
  if(!(body.repondant_nom||'').trim()){ err.textContent = t('e_name'); return; }
  if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test((body.repondant_email||'').trim())){ err.textContent = t('e_email'); return; }
  if(APERCU){ err.textContent = t('preview'); return; }
  go.disabled = true;
  try{
    const r = await fetch(API, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ err.textContent = j.detail || t('e_submit'); go.disabled = false; return; }
    document.getElementById('root').innerHTML =
      '<div class="card done"><h2>'+esc(t('done_t'))+'</h2><p>'+esc(t('done_p'))+'</p></div>';
    window.scrollTo(0,0);
  }catch(e){ err.textContent = t('e_network'); go.disabled = false; }
}

entete();
document.getElementById('t-loading').textContent = t('loading');
(async () => {
  try{
    if(APERCU){ D = APERCU; }
    else {
      const r = await fetch(API);
      if(!r.ok){ document.getElementById('root').innerHTML = '<div class="card">'+esc(t('invalid'))+'</div>'; return; }
      D = await r.json();
    }
    if(!LANG) LANG = I18N[D.langue] ? D.langue : 'en';
    render();
  }catch(e){ document.getElementById('root').innerHTML = '<div class="card">'+esc(t('network_load'))+'</div>'; }
})();
</script>
</body></html>"""
