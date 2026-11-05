/*
 * MySifa — Chat interne (/messages) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/messages_page.py ; ne fait que déclarer
 * des fonctions. init() appelle messagesDemarrerUrl() une fois les canaux
 * chargés, à la place de sa lecture de `?channel=`.
 *
 * Inventaire du 20/10/2026 (variables de premier niveau de la page, #mroot) :
 *   channel=<id>   conversation ouverte (activeId) — clé déjà utilisée par
 *                  les liens vers cette page, conservée
 *   fenêtres       epingles (messages épinglés), reglages (réglages du
 *                  canal), nouvelle_discussion, nouveau_canal,
 *                  transfert=<id du message>, gif
 * Hors adresse : réactions et sélecteur d'émojis (bulles d'un geste), menu
 * d'un message, mention en cours, son activé (préférence), message en cours
 * d'écriture, recherche de GIF.
 */
let _msgUrlPrete = false;
let _msgDemarre = false;
let _msgFen = null;           // {cle, id, vu, depuis}

const _MSG_OUVREURS = [
  ['openPinnedMessages', 'epingles',            () => activeId],
  ['openChannelSettings', 'reglages',           () => activeId],
  ['openNewDm',           'nouvelle_discussion', () => 1],
  ['openNewChannel',      'nouveau_canal',       () => 1],
  ['startForward',        'transfert',           a => a[0]],
  ['openGifPicker',       'gif',                 () => 1],
];

function messagesEnvelopper() {
  _MSG_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    window[nom] = function () {
      let v = null;
      try { v = valeur(arguments); } catch (e) {}
      if (v !== null && v !== undefined && v !== '') _msgFen = { cle, id: String(v), vu: false, depuis: Date.now() };
      return orig.apply(this, arguments);
    };
    window[nom].__adresse = true;
  });
}

// Fenêtre suivie : « vue » dès que #mroot est occupé, close dès qu'il se vide.
function _msgFenetre() {
  const f = _msgFen;
  if (!f) return null;
  const m = document.getElementById('mroot');
  if (m && m.childElementCount) { f.vu = true; return f; }
  if (f.vu || Date.now() - f.depuis > 5000) { _msgFen = null; return null; }
  return f;
}

function messagesParams() {
  const p = {};
  let nav = 'liste';
  if (activeId) { p.channel = activeId; nav = 'canal:' + activeId; }
  const f = _msgFenetre();
  if (f) { p[f.cle] = f.id; nav += '|' + f.cle + ':' + f.id; }
  return { params: p, nav };
}
function messagesSyncUrl() {
  if (!_msgUrlPrete || !window.MySifaUrl) return;
  try { const r = messagesParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function messagesUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; messagesSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

async function messagesAllerUrl(complet) {
  const u = MySifaUrl.lire();
  let voulue = null;
  _MSG_OUVREURS.forEach(o => { const v = u.get(o[1], null); if (v && v.length <= 40) voulue = { cle: o[1], id: v }; });
  const ouverte = _msgFenetre();
  if (ouverte && !(voulue && voulue.cle === ouverte.cle && voulue.id === ouverte.id)) { closeModal(); _msgFen = null; }
  const c = parseInt(u.get('channel', '0'), 10) || null;
  const existe = c && channels.some(ch => Number(ch.id) === c);
  if (existe && Number(activeId) !== c) await selectChannel(c);
  else if (!c && complet && activeId) {
    // Retour à la liste : aucune conversation choisie.
    activeId = null;
    document.body.classList.remove('chat-active');
    renderChannelLists();
  }
  if (!voulue || (_msgFenetre() && _msgFen.cle === voulue.cle && _msgFen.id === voulue.id)) return;
  if (voulue.cle === 'nouvelle_discussion') await openNewDm();
  else if (voulue.cle === 'nouveau_canal') { if (ADMIN_ROLES.has(window.__MYSIFA_ROLE__)) await openNewChannel(); }
  else if (!activeId) return;
  else if (voulue.cle === 'epingles') await openPinnedMessages();
  else if (voulue.cle === 'reglages') await openChannelSettings();
  else if (voulue.cle === 'gif') await openGifPicker();
  else if (voulue.cle === 'transfert') {
    const id = Number(voulue.id);
    for (let i = 0; i < 20 && !messages.some(m => m.id === id); i++) await new Promise(r => setTimeout(r, 150));
    if (messages.some(m => m.id === id)) await startForward(id);
  }
}

async function messagesDemarrerUrl() {
  if (_msgDemarre || !window.MySifaUrl) return;
  _msgDemarre = true;
  messagesEnvelopper();
  try { await messagesAllerUrl(false); } catch (e) {}
  _msgUrlPrete = true;
  messagesSyncUrl();
  messagesUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_msgUrlPrete) await messagesAllerUrl(true); });
}
