/*
 * MySifa — Portail (/) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Servi par le gabarit commun app/web/html.py, inactif hors de « / » : les
 * autres applis du gabarit (MyExpé, MyCompta, MyRH) tiennent leur adresse
 * elles-mêmes. Ne fait que déclarer des fonctions.
 *
 * Inventaire du 20/10/2026 (applis de la barre verticale rendues dans le
 * portail même) :
 *   app=messages   Messagerie (S.app) : `filtre` (non traités par défaut,
 *                  traites, tous), `message` (S.msgSelId)
 *   traduction=1   fenêtre MyTraduction : `de`, `vers` (langues ; le texte
 *                  n'entre jamais dans l'adresse)
 *   contact=1      fenêtre « Contacter le support » (S.contactOpen)
 * Hors adresse : sélection multiple de messages, vue mobile liste/détail.
 */
let _portUrlPrete = false;
let _portDemarre = false;
const _portSurPage = () => location.pathname === '/';
const _PORT_FILTRES = { non_traites: 'unread', traites: 'read', tous: 'all' };

function _portTraduction() {
  const ov = document.querySelector('.mytraduction-overlay');
  if (!ov) return null;
  const s = document.getElementById('myt-source'), t = document.getElementById('myt-target');
  return { de: s ? s.value : '', vers: t ? t.value : '' };
}

function portailParams() {
  const p = {};
  let nav = S.app === 'messages' ? 'messages' : 'portail';
  if (S.app === 'messages') {
    p.app = 'messages';
    const f = Object.keys(_PORT_FILTRES).find(k => _PORT_FILTRES[k] === (S.msgFilter || 'unread'));
    if (f && f !== 'non_traites') p.filtre = f;
    if (S.msgSelId) { p.message = S.msgSelId; nav += '/' + S.msgSelId; }
  }
  const tr = _portTraduction();
  if (tr) {
    p.traduction = 1; nav += '|traduction';
    if (tr.de && tr.de !== 'auto') p.de = tr.de;
    if (tr.vers) p.vers = tr.vers;
  }
  if (S.contactOpen) { p.contact = 1; nav += '|contact'; }
  return { params: p, nav };
}

function portailSyncUrl() {
  if (!_portUrlPrete || !_portSurPage() || !window.MySifaUrl || !S.user) return;
  if (S.app !== 'portal' && S.app !== 'messages') return;
  try { const r = portailParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function portailUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  const planifier = () => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; portailSyncUrl(); });
  };
  new MutationObserver(planifier).observe(document.body, { childList: true, subtree: true });
  // Les langues changent sans toucher au DOM.
  document.addEventListener('change', e => { if (e.target && /^myt-(source|target)$/.test(e.target.id || '')) planifier(); }, true);
}

function _portAttendre(cond) {
  return new Promise(ok => { let n = 0; const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250); });
}

async function portailAllerUrl(complet) {
  const u = MySifaUrl.lire();
  // Messagerie (réservée au superadmin : renderMessagesApp le vérifie).
  if (u.get('app') === 'messages') {
    const patch = {};
    if (S.app !== 'messages') patch.app = 'messages';
    const f = u.a('filtre') ? _PORT_FILTRES[u.get('filtre')] : (complet ? 'unread' : undefined);
    if (f && f !== S.msgFilter) { patch.msgFilter = f; patch.msgSelIds = []; }
    const m = u.get('message', null);
    const id = m && /^\d+$/.test(m) ? Number(m) : null;
    if (u.a('message') || complet) { if (id !== S.msgSelId) patch.msgSelId = id; }
    if (Object.keys(patch).length) set(patch);
    if (!S.msgList) {
      try { await loadMessagesUnread(); } catch (e) {}
      try { await loadMessages(); } catch (e) {}
    }
  } else if (complet && S.app === 'messages') {
    set({ app: 'portal' });
  }
  // Fenêtre « Contacter le support ».
  const contact = u.get('contact') === '1';
  if (contact !== !!S.contactOpen && (contact || complet)) set({ contactOpen: contact });
  // MyTraduction : les langues voulues passent par ses préférences, qu'elle
  // relit à l'ouverture.
  const voulue = u.get('traduction') === '1';
  const ouverte = _portTraduction();
  if (ouverte && !voulue && complet) {
    const b = document.querySelector('.mytraduction-overlay .mytraduction-close');
    if (b) b.click();
  } else if (voulue) {
    const de = u.get('de', 'auto'), vers = u.get('vers', null);
    if (ouverte) {
      const s = document.getElementById('myt-source'), t = document.getElementById('myt-target');
      if (s && s.value !== de) s.value = de;
      if (t && vers && t.value !== vers) t.value = vers;
    } else if (typeof openMyTraduction === 'function') {
      try {
        const prefs = JSON.parse(localStorage.getItem('mytraduction_prefs') || '{}') || {};
        prefs.source = de; if (vers) prefs.target = vers;
        localStorage.setItem('mytraduction_prefs', JSON.stringify(prefs));
      } catch (e) {}
      await openMyTraduction();
    }
  }
}

// Démarre dès que l'utilisateur est connu ; ne démarre qu'une fois.
async function portailDemarrerUrl() {
  if (_portDemarre || !_portSurPage() || !window.MySifaUrl) return;
  _portDemarre = true;
  await _portAttendre(() => S.user && S.app !== 'login');
  if (!S.user) { _portDemarre = false; return; }
  try { await portailAllerUrl(false); } catch (e) {}
  _portUrlPrete = true;
  portailSyncUrl();
  portailUrlObserver();
}

if (window.MySifaUrl && _portSurPage()) {
  MySifaUrl.surRetour(async () => { if (_portUrlPrete && S.user) await portailAllerUrl(true); });
}
