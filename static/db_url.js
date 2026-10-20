/*
 * MySifa — Base de données (/db) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/db_viewer_page.py ; ne fait que déclarer
 * des fonctions. Le démarrage de la page appelle dbDemarrerUrl().
 *
 * Inventaire du 20/10/2026 : `table` (S.activeTable), `vue=schema`
 * (S.view, données par défaut), `page`, `lignes` (S.limit, 50 par défaut),
 * `tri` (`colonne:asc|desc`). Aucune fenêtre sur cette page.
 * Hors adresse : recherche dans la table, filtre de la liste des tables,
 * question posée à l'IA.
 */
let _dbUrlPrete = false;
let _dbDemarre = false;
let _dbAccueil = null;        // contenu « Sélectionnez une table », pour y revenir

function dbParams() {
  const p = {};
  let nav = 'accueil';
  if (S.activeTable) {
    p.table = S.activeTable; nav = 'table:' + S.activeTable;
    if (S.view === 'schema') { p.vue = 'schema'; nav += '/schema'; }
    else {
      if (S.page > 1) p.page = S.page;
      if (S.limit !== 50) p.lignes = S.limit;
      if (S.orderCol) p.tri = S.orderCol + ':' + (S.orderDir === 'DESC' ? 'desc' : 'asc');
    }
  }
  return { params: p, nav };
}

function dbSyncUrl() {
  if (!_dbUrlPrete || !window.MySifaUrl) return;
  try { const r = dbParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function dbUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; dbSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

async function dbAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const t = u.get('table', null);
  if (!t || !(S.tables || []).some(x => x.name === t)) {
    if (complet && S.activeTable) {
      // Retour à l'accueil de la page : aucune table choisie.
      S.activeTable = null; S.data = null; S.schema = [];
      renderTables();
      const tb = document.getElementById('topbar'); if (tb) tb.style.display = 'none';
      const c = document.getElementById('content'); if (c && _dbAccueil !== null) c.innerHTML = _dbAccueil;
    }
    return;
  }
  const vue = u.get('vue', 'data', ['data', 'schema']);
  if (S.view !== vue) {
    // switchView recharge la table courante : on la retire d'abord si elle
    // doit changer, pour ne charger que la bonne.
    if (S.activeTable !== t) S.activeTable = null;
    switchView(vue);
  }
  if (S.activeTable !== t) await selectTable(t);
  if (vue !== 'data') return;
  const page = Math.max(1, parseInt(u.get('page', '1'), 10) || 1);
  const lignes = parseInt(u.get('lignes', '50'), 10);
  const limite = [25, 50, 100, 200].indexOf(lignes) !== -1 ? lignes : 50;
  const tri = u.get('tri', '');
  const m = /^(.+):(asc|desc)$/.exec(tri);
  const col = m ? m[1] : null, sens = m && m[2] === 'desc' ? 'DESC' : 'ASC';
  if (S.page !== page || S.limit !== limite || S.orderCol !== col || (col && S.orderDir !== sens)) {
    S.page = page; S.limit = limite; S.orderCol = col; S.orderDir = sens;
    const sel = document.getElementById('limit-sel'); if (sel) sel.value = String(limite);
    for (let i = 0; i < 40 && S.loading; i++) await new Promise(r => setTimeout(r, 100));
    await loadRows();
  }
}

async function dbDemarrerUrl() {
  if (_dbDemarre || !window.MySifaUrl) return;
  _dbDemarre = true;
  const c = document.getElementById('content');
  _dbAccueil = c ? c.innerHTML : null;
  try { await dbAllerUrl(false); } catch (e) {}
  _dbUrlPrete = true;
  dbSyncUrl();
  dbUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_dbUrlPrete) await dbAllerUrl(true); });
}
