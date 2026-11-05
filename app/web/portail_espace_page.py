"""Espace SIFA — page publique du destinataire (`/portail/{jeton}`).

Une seule page pour tout ce que SIFA adresse à cette personne : les
formulaires se remplissent ici (moteur commun `static/mysifa_formulaire.js`),
les autres demandes (appels d'offres, devis transport, EUDR) sont des cartes
qui ouvrent leur page. Marque SIFA, jamais MySifa (règle « Marque côté
transporteur », .claude/rules/expe-notes-transporteurs.md).

Adresse : `?formulaire=<id>` ouvre un formulaire (lien des emails) ; Retour
ramène à la liste.
Documents à signer (MyTools › Parapheur) : `?signature=<id>`, et `#signer=<jeton>`
dans le lien de l'email — rendus par static/mysifa_parapheur_signer.js
(`ParapheurEspace`), branché ici en trois points : carte, adresse, retour.

API : app/routers/portail_espace.py.
"""
from html import escape

from app.web.components import bloc_tokens
from config import APP_ORG_NAME


def get_espace_html(token: str) -> str:
    return (
        _PAGE.replace("__TOKENS__", bloc_tokens())
        .replace("__ORG__", escape(APP_ORG_NAME))
        .replace("__TOKEN_JS__", escape(token, quote=True))
    )


def get_espace_404_html() -> str:
    return (
        _PAGE_404.replace("__TOKENS__", bloc_tokens()).replace("__ORG__", escape(APP_ORG_NAME))
    )


_CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;font-size:14px;line-height:1.5}
.es-haut{background:var(--card);border-bottom:1px solid var(--border)}
.es-haut-in{max-width:880px;margin:0 auto;padding:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.es-marque{font-size:20px;font-weight:800;letter-spacing:.5px;color:var(--accent)}
.es-titre{font-size:14px;color:var(--text2)}
.es-qui{margin-left:auto;font-size:12px;color:var(--muted);overflow-wrap:anywhere}
main{max-width:880px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:20px;margin:0 0 4px}
.es-intro{color:var(--text2);margin:0 0 20px}
.es-sec{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:22px 0 8px}
.es-liste{display:flex;flex-direction:column;gap:8px}
.es-carte{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;text-decoration:none;color:inherit;cursor:pointer;font:inherit;text-align:left;width:100%}
.es-carte:hover{border-color:var(--accent)}
.es-carte:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.es-ico{flex:0 0 auto;width:38px;height:38px;border-radius:10px;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center}
.es-carte-main{flex:1;min-width:0}
.es-carte-titre{font-weight:700;overflow-wrap:anywhere}
.es-carte-detail{font-size:12px;color:var(--muted);margin-top:2px;overflow-wrap:anywhere}
.es-badge{flex:0 0 auto;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px;border:1px solid var(--border);color:var(--text2);white-space:nowrap}
.es-badge.attente{border-color:var(--accent);color:var(--accent)}
.es-badge.ok{border-color:var(--success);color:var(--success)}
.es-badge.retard{border-color:var(--danger);color:var(--danger)}
.es-vide{background:var(--card);border:1px dashed var(--border);border-radius:12px;padding:18px;color:var(--muted);text-align:center}
.es-retour{display:inline-flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:7px 12px;color:var(--text2);font:inherit;font-size:13px;font-weight:600;cursor:pointer;margin-bottom:14px}
.es-retour:hover{border-color:var(--accent);color:var(--accent)}
.es-form{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px}
.es-meta{font-size:12px;color:var(--muted);margin:0 0 14px}
.es-message{border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 8px 8px 0;padding:10px 12px;white-space:pre-wrap;margin:0 0 14px;color:var(--text)}
.es-desc{white-space:pre-wrap;color:var(--text2);margin:0 0 16px}
.es-info{border:1px solid var(--success);border-radius:10px;padding:10px 12px;color:var(--text);margin:0 0 16px;font-size:13px}
.es-pied{border-top:1px solid var(--border);margin-top:20px;padding-top:16px;display:flex;flex-direction:column;gap:10px}
.es-pied label{font-size:12px;font-weight:600;color:var(--text2)}
.es-pied input{width:100%;max-width:360px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:9px 11px;color:var(--text);font:inherit}
.es-pied input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.es-manque{font-size:12px;color:var(--danger)}
.es-btn{align-self:flex-start;background:var(--accent);color:white;border:none;border-radius:10px;padding:11px 20px;font:inherit;font-weight:700;cursor:pointer}
.es-btn:disabled{opacity:.55;cursor:not-allowed}
.es-btn:hover:not(:disabled){filter:brightness(1.05)}
.es-merci{background:var(--card);border:1px solid var(--success);border-radius:14px;padding:24px;text-align:center}
.es-merci h2{margin:0 0 6px;font-size:18px}
.es-toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:var(--danger);color:white;padding:10px 16px;border-radius:10px;font-size:13px;max-width:calc(100vw - 32px);display:none}
footer{max-width:880px;margin:0 auto;padding:0 16px 32px;font-size:12px;color:var(--muted)}
@media(max-width:560px){.es-carte{flex-wrap:wrap}.es-badge{margin-left:50px}.es-form{padding:14px}}
"""

_PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Votre espace __ORG__</title>
<link rel="icon" href="/static/expe_portail_favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/mysifa_tools_parapheur.css?v=1">
<style>__TOKENS__
""" + _CSS + """</style>
</head>
<body class="light">
<script>try{if(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)document.body.classList.remove('light');}catch(e){}</script>
<header class="es-haut"><div class="es-haut-in">
  <span class="es-marque">__ORG__</span><span class="es-titre">Votre espace</span>
  <span class="es-qui" id="es-qui"></span>
</div></header>
<main id="es-main"><p class="es-intro">Chargement…</p></main>
<footer>Ce lien est personnel : il donne accès aux demandes que __ORG__ vous a adressées. Merci de ne pas le transférer.</footer>
<div class="es-toast" id="es-toast" role="alert"></div>
<script src="/static/mysifa_formulaire.js?v=3"></script>
<script src="/static/mysifa_bulles.js"></script>
<script src="/static/mysifa_parapheur_signer.js?v=1"></script>
<script>
'use strict';
const TOKEN = "__TOKEN_JS__";
const API = '/api/portail/espace/' + encodeURIComponent(TOKEN);
const E = {data: null, form: null, envoi: false};
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateFr = (s) => { if(!s) return ''; const p = String(s).slice(0,10).split('-'); return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : String(s); };
const ICO = {
  formulaire: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/></svg>',
  ao: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15h6"/></svg>',
  expe: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="6" width="14" height="10" rx="1"/><path d="M15 9h4l3 3v4h-7"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
  eudr: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22V12"/><path d="M12 12C12 7 8 4 4 4c0 5 3 8 8 8z"/><path d="M12 14c0-4 3-7 8-7 0 4-3 7-8 7z"/></svg>',
};

function toast(msg){
  const t = document.getElementById('es-toast');
  t.textContent = msg; t.style.display = 'block';
  clearTimeout(toast._t); toast._t = setTimeout(() => { t.style.display = 'none'; }, 4000);
}
async function appel(chemin, opts){
  const r = await fetch(API + chemin, Object.assign({headers: {'Content-Type': 'application/json'}}, opts || {}));
  let j = null; try{ j = await r.json(); }catch(e){}
  if(!r.ok){ const err = new Error((j && j.detail && typeof j.detail === 'string') ? j.detail : 'Erreur ' + r.status); err.detail = j && j.detail; throw err; }
  return j;
}

function badge(e){
  if(e.module === 'formulaire'){
    if(e.statut === 'repondu') return '<span class="es-badge ok">Répondu le ' + esc(dateFr(e.repondu_le)) + '</span>';
    if(e.echeance && e.echeance < new Date().toISOString().slice(0,10)) return '<span class="es-badge retard">Échéance dépassée</span>';
    return '<span class="es-badge attente">À compléter' + (e.echeance ? ' avant le ' + esc(dateFr(e.echeance)) : '') + '</span>';
  }
  return e.a_traiter ? '<span class="es-badge attente">À traiter</span>' : '<span class="es-badge ok">À jour</span>';
}
function carte(e){
  if(e.module === 'signature' && window.ParapheurEspace) return ParapheurEspace.carte(e);
  const detail = [e.detail, e.de ? 'de ' + e.de : '', e.envoye_le ? 'envoyé le ' + dateFr(e.envoye_le) : ''].filter(Boolean).join(' · ');
  const corps = '<span class="es-ico">' + (ICO[e.module] || ICO.formulaire) + '</span>'
    + '<span class="es-carte-main"><span class="es-carte-titre">' + esc(e.titre) + '</span>'
    + '<span class="es-carte-detail" style="display:block">' + esc(detail) + '</span></span>' + badge(e);
  if(e.module === 'formulaire') return '<button type="button" class="es-carte" onclick="ouvrir(' + Number(e.id) + ')">' + corps + '</button>';
  return '<a class="es-carte" href="' + esc(e.url) + '">' + corps + '</a>';
}

function rendreListe(){
  const d = E.data, m = document.getElementById('es-main');
  const att = d.a_traiter || [], ok = d.traites || [];
  m.innerHTML = '<h1>' + esc(d.nom ? 'Bonjour ' + d.nom : 'Bonjour') + '</h1>'
    + '<p class="es-intro">Retrouvez ici tout ce que __ORG__ vous a adressé.</p>'
    + '<div class="es-sec">À traiter (' + att.length + ')</div>'
    + (att.length ? '<div class="es-liste">' + att.map(carte).join('') + '</div>' : '<div class="es-vide">Rien à traiter pour le moment.</div>')
    + (ok.length ? '<div class="es-sec">Déjà traité (' + ok.length + ')</div><div class="es-liste">' + ok.map(carte).join('') + '</div>' : '');
  document.title = 'Votre espace __ORG__';
}

async function charger(){
  try{
    E.data = await appel('');
    document.getElementById('es-qui').textContent = E.data.email || '';
  }catch(e){ document.getElementById('es-main').innerHTML = '<div class="es-vide">' + esc(e.message) + '</div>'; return; }
  await suivreAdresse();
}

async function suivreAdresse(){
  if(window.ParapheurEspace && await ParapheurEspace.suivre({api: API, main: document.getElementById('es-main'), retour: retour,
      recharger: async () => { E.data = await appel(''); }})) return;
  const id = new URLSearchParams(location.search).get('formulaire');
  if(id && /^\\d+$/.test(id)) await afficherFormulaire(Number(id));
  else { E.form = null; rendreListe(); }
}

async function ouvrir(id){
  history.pushState({formulaire: id}, '', '?formulaire=' + id);
  await afficherFormulaire(id);
  window.scrollTo(0, 0);
}
function retour(){
  if(history.state && (history.state.formulaire || history.state.signature)) history.back();
  else { history.replaceState(null, '', location.pathname); E.form = null; rendreListe(); }
}
window.addEventListener('popstate', () => { suivreAdresse(); });

async function afficherFormulaire(id){
  const m = document.getElementById('es-main');
  let f;
  try{ f = await appel('/formulaires/' + id); }
  catch(e){ m.innerHTML = '<button type="button" class="es-retour" onclick="retour()">← Votre espace</button><div class="es-vide">' + esc(e.message) + '</div>'; return; }
  E.form = f;
  const envoi = [f.de ? 'Envoyé par ' + f.de : 'Envoyé', f.envoye_le ? 'le ' + dateFr(f.envoye_le) : ''].filter(Boolean).join(' ');
  const meta = [envoi, f.echeance ? 'réponse attendue avant le ' + dateFr(f.echeance) : ''].filter(Boolean).join(' · ');
  m.innerHTML = '<button type="button" class="es-retour" onclick="retour()">← Votre espace</button>'
    + '<div class="es-form"><h1></h1><p class="es-meta"></p>'
    + (f.message ? '<p class="es-message"></p>' : '')
    + (f.description ? '<p class="es-desc"></p>' : '')
    + (f.reponse ? '<div class="es-info">Vous avez répondu le ' + esc(dateFr(f.reponse.soumis_le)) + '. Vous pouvez modifier votre réponse et l\\'envoyer à nouveau.</div>' : '')
    + '<div id="es-questions"></div>'
    + '<div class="es-pied"><label for="es-nom">Votre nom</label><input id="es-nom" maxlength="200" autocomplete="name">'
    + '<div class="es-manque" id="es-manque"></div>'
    + '<button type="button" class="es-btn" id="es-envoyer" onclick="envoyer()">Envoyer ma réponse</button></div></div>';
  m.querySelector('h1').textContent = f.titre;
  m.querySelector('.es-meta').textContent = meta;
  if(f.message) m.querySelector('.es-message').textContent = f.message;
  if(f.description) m.querySelector('.es-desc').textContent = f.description;
  document.getElementById('es-nom').value = (f.reponse && f.reponse.repondant_nom) || E.data.nom || '';
  document.title = f.titre + ' — __ORG__';
  MysifaFormulaire.rendre(f.schema, document.getElementById('es-questions'), {onChange: majBouton, valeurs: f.reponse ? f.reponse.reponses : null});
  majBouton();
}

function majBouton(){
  const zone = document.getElementById('es-questions');
  const btn = document.getElementById('es-envoyer');
  if(!zone || !btn) return;
  const manque = MysifaFormulaire.manquantes(zone);
  btn.disabled = manque.length > 0 || E.envoi;
  const qs = zone._mfQuestions || {};
  document.getElementById('es-manque').textContent = manque.length
    ? 'Réponse obligatoire manquante : ' + manque.map(id => (qs[id] && qs[id].label) || '').filter(Boolean).slice(0, 4).join(' · ') + (manque.length > 4 ? '…' : '')
    : '';
}

async function envoyer(){
  const zone = document.getElementById('es-questions');
  if(!E.form || E.envoi || MysifaFormulaire.manquantes(zone).length) return;
  E.envoi = true; majBouton();
  const btn = document.getElementById('es-envoyer'); btn.textContent = 'Envoi…';
  try{
    await appel('/formulaires/' + E.form.id, {method: 'POST', body: JSON.stringify({reponses: MysifaFormulaire.lire(zone), repondant_nom: document.getElementById('es-nom').value})});
    E.data = await appel('');
    document.getElementById('es-main').innerHTML = '<div class="es-merci"><h2>Réponse envoyée.</h2><p style="margin:0 0 16px;color:var(--text2)">Merci. __ORG__ a bien reçu votre réponse.</p><button type="button" class="es-retour" style="margin:0" onclick="retour()">← Votre espace</button></div>';
    window.scrollTo(0, 0);
  }catch(e){
    toast(Array.isArray(e.detail) ? 'Réponse obligatoire manquante : ' + e.detail.join(' · ') : e.message);
    btn.textContent = 'Envoyer ma réponse';
  }finally{ E.envoi = false; majBouton(); }
}

charger();
</script>
</body>
</html>
"""

_PAGE_404 = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Lien invalide — __ORG__</title>
<link rel="icon" href="/static/expe_portail_favicon.svg" type="image/svg+xml">
<style>__TOKENS__
""" + _CSS + """</style></head>
<body class="light"><header class="es-haut"><div class="es-haut-in"><span class="es-marque">__ORG__</span></div></header>
<main><div class="es-vide">Ce lien n'est pas valide ou n'est plus actif. Contactez votre interlocuteur chez __ORG__ pour en recevoir un nouveau.</div></main>
</body></html>
"""
