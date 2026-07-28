"""MySifa - Assets de l'explorateur de documents (GED qualite).

Ce module ne contient que du CSS et du JS, injectes dans la page /qualite via le
placeholder __GED_ASSETS__. Il est separe de qualite_page.py pour une raison
simple : cette page depasse deja 7 000 lignes, y ajouter un explorateur de
fichiers complet la rendrait impossible a maintenir. Meme motif que
expe_assets.py et portal_assets.py.

Le bloc est injecte a l'interieur du <script> existant, juste avant init() :
les declarations de fonctions sont donc hoistees et visibles depuis le reste
de la page (notamment sifaTabsHtml(), appelee par renderSifaDocsList).

Navigation : colonnes horizontales facon Finder (Miller columns). Chaque niveau
de l'arborescence est une colonne ; cliquer un dossier ouvre son contenu dans la
colonne suivante a droite, sans recharger la page. Le detail d'un document
s'ouvre en tiroir superpose, pour ne pas manger la largeur des colonnes.
"""

GED_JS = r"""
// ══════════════════════════════════════════════════════════════════════
// Certifications SIFA - onglet 2 : Explorateur de documents (GED)
// Navigation en colonnes horizontales (Miller columns, facon Finder).
// ══════════════════════════════════════════════════════════════════════

S.ged = {
  tab: 'docs',        // 'docs' = documents clients (existant) | 'explorer'
  path: [0],          // chemin courant : [0, id1, id2, ...] - 0 = racine
  cols: [],           // contenu de chaque niveau, aligne sur path
  trashCount: 0,
  q: '',              // recherche en cours
  results: null,      // resultats de recherche
  detail: null,       // document ouvert dans le tiroir
  trash: null,        // vue corbeille
  mode: 'browse',     // 'browse' | 'search' | 'trash'
  selFile: null,      // id du fichier selectionne (surlignage colonne)
  _focusQ: false,
  _searchTimer: null,
  _drag: null,        // {kind:'file'|'folder', id}
  _escBound: false,
};

try{ var _gt = localStorage.getItem('mysifa_sifa_tab'); if(_gt) S.ged.tab = _gt; }catch(e){}

// ─── Onglets de la page Certifications SIFA ──────────────────────────
function gedActiveTab(){ return (S.ged && S.ged.tab) || 'docs'; }

function sifaTabsHtml(active){
  const t = active || gedActiveTab();
  const tab = (k, label, hint) =>
    `<button type="button" class="sifa-tab${t===k?' active':''}" onclick="setSifaTab('${k}')" title="${escAttr(hint)}">${escHtml(label)}</button>`;
  return `<div class="sifa-tabs">
    ${tab('docs','Documents clients','Generer les Declarations UE et attestations a envoyer aux clients')}
    ${tab('explorer','Explorateur','Parcourir, deposer et rechercher les documents qualite')}
  </div>`;
}

function setSifaTab(k){
  S.ged.tab = k;
  try{ localStorage.setItem('mysifa_sifa_tab', k); }catch(e){}
  if(k === 'explorer') gedEnter();
  else if(typeof loadSifaDocsList === 'function') loadSifaDocsList();
}

// ─── Helpers ─────────────────────────────────────────────────────────
function gedCwd(){ return S.ged.path[S.ged.path.length - 1] || 0; }
function gedCurCol(){ return S.ged.cols[S.ged.cols.length - 1] || null; }

function gedFmtSize(b){
  if(b === null || b === undefined) return '';
  if(b < 1024) return b + ' o';
  if(b < 1048576) return (b/1024).toFixed(1) + ' Ko';
  return (b/1048576).toFixed(1) + ' Mo';
}

const GED_EXT_CLASS = {
  pdf:'pdf', doc:'doc', docx:'doc', odt:'doc', rtf:'doc',
  xls:'xls', xlsx:'xls', xlsm:'xls', csv:'xls', ods:'xls',
  ppt:'ppt', pptx:'ppt', odp:'ppt',
  png:'img', jpg:'img', jpeg:'img', gif:'img', webp:'img', svg:'img', bmp:'img', heic:'img',
  zip:'zip', rar:'zip', '7z':'zip', tar:'zip', gz:'zip',
};
function gedExtClass(ext){ return GED_EXT_CLASS[(ext||'').toLowerCase()] || 'gen'; }
function gedIsPreviewable(ext){
  const e = (ext||'').toLowerCase();
  return e === 'pdf' || ['png','jpg','jpeg','gif','webp','svg','bmp'].indexOf(e) !== -1;
}
function gedFileIco(ext){
  const e = (ext||'').toUpperCase().slice(0,4) || '?';
  return `<span class="ged-ext ged-ext-${gedExtClass(ext)}">${escHtml(e)}</span>`;
}
const GED_FOLDER_SVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
const GED_CHEVRON_SVG = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';

function gedLinkBadge(t){
  if(!t) return '';
  const lbl = {client:'Client', fournisseur:'Fournisseur', norme:'Norme'}[t] || t;
  return `<span class="ged-link-badge">${escHtml(lbl)}</span>`;
}

// ─── Chargement des colonnes ─────────────────────────────────────────
async function gedFetchCol(folderId){
  const r = await api('/api/qualite/ged/folders/' + (folderId||0));
  if(!r.ok) return null;
  return await r.json();
}

async function gedLoadTrashCount(){
  try{
    const r = await api('/api/qualite/ged/tree');
    if(r.ok){ const d = await r.json(); S.ged.trashCount = d.trash_count || 0; }
  }catch(e){}
}

async function gedEnter(){
  S.ged.mode = 'browse';
  if(!S.ged.cols.length){
    const c0 = await gedFetchCol(0);
    if(!c0) return;
    S.ged.path = [0];
    S.ged.cols = [c0];
  }
  await gedLoadTrashCount();
  gedRender();
}

// Clic sur un dossier dans la colonne d'index colIndex
async function gedSelectFolder(colIndex, folderId){
  const c = await gedFetchCol(folderId);
  if(!c){ showToast('Dossier introuvable','danger'); return gedRefresh(); }
  S.ged.path = S.ged.path.slice(0, colIndex + 1).concat([folderId]);
  S.ged.cols = S.ged.cols.slice(0, colIndex + 1).concat([c]);
  S.ged.mode = 'browse';
  S.ged.selFile = null;
  gedRender();
}

// Remonter a un niveau du fil d'Ariane
function gedGoToDepth(i){
  S.ged.path = S.ged.path.slice(0, i + 1);
  S.ged.cols = S.ged.cols.slice(0, i + 1);
  S.ged.mode = 'browse';
  S.ged.selFile = null;
  gedRender();
}

// Ouvrir un dossier par son id, d'ou qu'on vienne (resultat de recherche,
// panneau detail...). On reconstruit tout le chemin depuis son fil d'Ariane.
async function gedOpen(folderId){
  S.ged.mode = 'browse';
  S.ged.results = null;
  S.ged.trash = null;
  const target = await gedFetchCol(folderId || 0);
  if(!target){
    showToast('Dossier introuvable','danger');
    S.ged.path = [0]; S.ged.cols = [];
    return gedEnter();
  }
  const ids = [0].concat((target.breadcrumb||[]).map(b => b.id));
  const cols = await Promise.all(ids.map(id =>
    id === (folderId||0) ? Promise.resolve(target) : gedFetchCol(id)));
  S.ged.path = ids;
  S.ged.cols = cols.map((c,i) => c || {folder:null, breadcrumb:[], folders:[], files:[]});
  gedRender();
}

// Recharge toutes les colonnes du chemin courant (apres upload, suppression...)
async function gedRefresh(){
  await gedLoadTrashCount();
  if(S.ged.mode === 'search') return gedRunSearch();
  if(S.ged.mode === 'trash')  return gedOpenTrash();

  const cols = [];
  const path = [];
  for(const id of S.ged.path){
    const c = await gedFetchCol(id);
    if(!c) break;              // dossier disparu : on s'arrete a ce niveau
    path.push(id); cols.push(c);
  }
  S.ged.path = path.length ? path : [0];
  S.ged.cols = cols.length ? cols : [await gedFetchCol(0)];
  gedRender();
}

// ─── Rendu principal ─────────────────────────────────────────────────
function gedRender(){
  const root = document.getElementById('content');
  if(!root) return;

  let main = '';
  if(S.ged.mode === 'trash')       main = gedTrashHtml();
  else if(S.ged.mode === 'search') main = gedResultsHtml();
  else                             main = gedBrowseHtml();

  root.innerHTML = `
    ${sifaTabsHtml('explorer')}
    <div class="ged-searchbar">
      <svg class="ged-search-ico" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="search" id="ged-q" placeholder="Rechercher dans les noms, les tags et le contenu des documents..."
             value="${escAttr(S.ged.q)}"
             oninput="gedOnSearch(this.value)"
             onkeydown="if(event.key==='Escape'){gedClearSearch();}">
      ${S.ged.q ? `<button class="ged-search-x" onclick="gedClearSearch()" title="Effacer">&times;</button>` : ''}
    </div>
    <div class="ged-shell">${main}</div>
    ${S.ged.detail ? `<div class="ged-drawer-backdrop" onclick="gedCloseDetail()"></div>
                      <aside class="ged-drawer">${gedDetailHtml()}</aside>` : ''}
    <input type="file" id="ged-file-input" multiple style="display:none"
           onchange="gedUpload(this.files, gedCwd()); this.value='';">
    <input type="file" id="ged-version-input" style="display:none"
           onchange="gedUploadVersion(this.files); this.value='';">
  `;

  // La colonne la plus a droite est celle qui vient d'etre ouverte : on la
  // ramene dans le champ de vision plutot que de laisser l'utilisateur
  // chercher ou son clic a atterri.
  const wrap = document.getElementById('ged-cols');
  if(wrap) wrap.scrollLeft = wrap.scrollWidth;

  if(S.ged._focusQ){
    const inp = document.getElementById('ged-q');
    if(inp){ inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
    S.ged._focusQ = false;
  }

  if(!S.ged._escBound){
    document.addEventListener('keydown', function(e){
      if(e.key !== 'Escape' || !S.ged.detail) return;
      // Une modale ouverte par-dessus (apercu, edition) a la priorite sur le
      // tiroir : Echap la ferme d'abord. #mroot est cree a la demande, donc
      // il peut ne pas exister du tout.
      const mr = document.getElementById('mroot');
      if(mr && mr.innerHTML.trim()) return;
      gedCloseDetail();
    });
    S.ged._escBound = true;
  }
}

// ─── Vue navigation : colonnes horizontales ──────────────────────────
function gedBrowseHtml(){
  if(!S.ged.cols.length) return '<div class="ged-empty">Chargement...</div>';

  // Fil d'Ariane : miroir du chemin, permet de remonter d'un clic
  const bcParts = S.ged.path.map((id, i) => {
    const nom = i === 0 ? 'Racine'
      : ((S.ged.cols[i] && S.ged.cols[i].folder && S.ged.cols[i].folder.nom) || '...');
    const last = i === S.ged.path.length - 1;
    return `${i ? '<span class="ged-bc-sep">/</span>' : ''}<span class="ged-bc-item${last?' cur':''}" onclick="gedGoToDepth(${i})">${escHtml(nom)}</span>`;
  }).join('');

  const cols = S.ged.cols.map((c, i) => gedColumnHtml(c, i)).join('');

  return `
    <div class="ged-bc">${bcParts}</div>
    <div class="ged-toolbar">
      <button class="btn btn-ghost ged-btn" onclick="gedNewFolder()">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouveau dossier
      </button>
      <button class="btn btn-accent ged-btn" onclick="document.getElementById('ged-file-input').click()">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        Envoyer des fichiers
      </button>
      <button class="btn btn-ghost ged-btn" onclick="gedZip(gedCwd())" title="Telecharger ce dossier et son contenu en ZIP">ZIP</button>
      ${gedCwd() ? `<button class="btn btn-ghost ged-btn" onclick="gedFolderProps(gedCwd())">Proprietes</button>` : ''}
      <div class="ged-toolbar-sp"></div>
      <button class="btn btn-ghost ged-btn" onclick="gedOpenTrash()" title="Corbeille - rien n'est purge automatiquement">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        Corbeille${S.ged.trashCount ? ` <span class="ged-count">${S.ged.trashCount}</span>` : ''}
      </button>
    </div>
    <div class="ged-cols" id="ged-cols">${cols}</div>
    <div class="ged-hint-bar">Glisser-deposer des fichiers dans une colonne pour les ajouter - glisser une ligne sur un dossier pour la deplacer</div>
  `;
}

function gedColumnHtml(c, i){
  const fid = S.ged.path[i] || 0;
  const nextId = S.ged.path[i+1] || null;   // dossier ouvert dans la colonne suivante
  const titre = i === 0 ? 'Racine' : ((c.folder && c.folder.nom) || '...');

  const folders = (c.folders||[]).map(f => `
    <div class="ged-row ged-row-folder${nextId===f.id?' open':''}"
         draggable="true" ondragstart="gedDragStart(event,'folder',${f.id})"
         ondragover="gedDragOver(event,this)" ondragleave="gedDragLeave(this)"
         ondrop="gedDrop(event, ${f.id}, this)"
         onclick="gedSelectFolder(${i}, ${f.id})">
      <span class="ged-row-ico folder">${GED_FOLDER_SVG}</span>
      <span class="ged-row-name" title="${escAttr(f.nom)}">${escHtml(f.nom)}</span>
      ${f.link_type ? gedLinkBadge(f.link_type) : ''}
      <span class="ged-row-acts">
        <span class="ged-row-act" title="Renommer" onclick="event.stopPropagation();gedRenameFolder(${i},${f.id})">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>
        </span>
        <span class="ged-row-act" title="ZIP" onclick="event.stopPropagation();gedZip(${f.id})">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        </span>
        <span class="ged-row-act del" title="Corbeille" onclick="event.stopPropagation();gedDeleteFolder(${i},${f.id})">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
        </span>
      </span>
      <span class="ged-row-chev">${GED_CHEVRON_SVG}</span>
    </div>
  `).join('');

  const files = (c.files||[]).map(f => `
    <div class="ged-row ged-row-file${S.ged.selFile===f.id?' sel':''}"
         draggable="true" ondragstart="gedDragStart(event,'file',${f.id})"
         onclick="gedOpenFile(${f.id})">
      <span class="ged-row-ico">${gedFileIco(f.ext)}</span>
      <span class="ged-row-body">
        <span class="ged-row-name" title="${escAttr(f.nom)}">${escHtml(f.nom)}</span>
        <span class="ged-row-meta">${gedFmtSize(f.size_bytes)}${(f.version||1)>1?` - v${f.version}`:''}${f.index_status && f.index_status!=='ok' ? ' - <span class="ged-warn-dot" title="Contenu non indexe : ce document ne ressortira pas sur une recherche par mot du texte. Ajoutez des tags.">non indexe</span>' : ''}</span>
      </span>
      <span class="ged-row-acts">
        ${gedIsPreviewable(f.ext) ? `<span class="ged-row-act" title="Apercu" onclick="event.stopPropagation();gedPreview(${f.id})">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </span>` : ''}
        <a class="ged-row-act" title="Telecharger" href="/api/qualite/ged/files/${f.id}/download" onclick="event.stopPropagation()">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        </a>
        <span class="ged-row-act del" title="Corbeille" onclick="event.stopPropagation();gedDeleteFile(${f.id})">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
        </span>
      </span>
    </div>
  `).join('');

  const n = (c.folders||[]).length + (c.files||[]).length;

  return `
    <div class="ged-col${i === S.ged.cols.length-1 ? ' last' : ''}"
         ondragover="gedDragOver(event,this)" ondragleave="gedDragLeave(this)"
         ondrop="gedDrop(event, ${fid}, this)">
      <div class="ged-col-hd">
        <span class="ged-col-title" title="${escAttr(titre)}">${escHtml(titre)}</span>
        <span class="ged-col-n">${n}</span>
      </div>
      <div class="ged-col-bd">
        ${folders}${files}
        ${n ? '' : '<div class="ged-col-empty">Dossier vide<br><span>Deposez des fichiers ici</span></div>'}
      </div>
    </div>
  `;
}

// ─── Recherche ───────────────────────────────────────────────────────
function gedOnSearch(v){
  S.ged.q = v;
  clearTimeout(S.ged._searchTimer);
  if(!v || v.trim().length < 2){
    if(S.ged.mode === 'search'){ S.ged.mode='browse'; S.ged.results=null; S.ged._focusQ=true; gedRender(); }
    return;
  }
  S.ged._searchTimer = setTimeout(gedRunSearch, 260);
}

function gedClearSearch(){
  S.ged.q = '';
  S.ged.results = null;
  S.ged.mode = 'browse';
  gedRender();
}

async function gedRunSearch(){
  const q = (S.ged.q||'').trim();
  if(q.length < 2) return;
  try{
    const r = await api('/api/qualite/ged/search?q=' + encodeURIComponent(q));
    if(!r.ok){ showToast('Erreur recherche','danger'); return; }
    S.ged.results = await r.json();
    S.ged.mode = 'search';
    S.ged._focusQ = true;
    gedRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

function gedResultsHtml(){
  const d = S.ged.results || {results:[]};
  const rows = (d.results||[]).map(f => `
    <div class="ged-res" onclick="gedOpenFile(${f.id})">
      <div class="ged-res-ico">${gedFileIco(f.ext)}</div>
      <div class="ged-res-body">
        <div class="ged-res-name">${escHtml(f.nom)}</div>
        <div class="ged-res-path" onclick="event.stopPropagation();gedOpen(${f.folder_id||0})" title="Ouvrir le dossier">
          ${escHtml(f.path||'/')}
        </div>
        ${f.extrait ? `<div class="ged-res-snip">${f.extrait}</div>` : ''}
        ${f.tags ? `<div class="ged-tags">${f.tags.split(',').map(t=>`<span class="ged-tag">${escHtml(t)}</span>`).join('')}</div>` : ''}
      </div>
      <div class="ged-res-actions">
        ${gedIsPreviewable(f.ext) ? `<button class="ged-row-act" title="Apercu" onclick="event.stopPropagation();gedPreview(${f.id})">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </button>` : ''}
        <a class="ged-row-act" title="Telecharger" href="/api/qualite/ged/files/${f.id}/download" onclick="event.stopPropagation()">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        </a>
      </div>
    </div>
  `).join('');

  return `
    <div class="ged-res-hd">
      <div><b>${d.count||0}</b> resultat${(d.count||0)>1?'s':''} pour &laquo; ${escHtml(S.ged.q)} &raquo;</div>
      <button class="btn btn-ghost ged-btn" onclick="gedClearSearch()">Retour a l'arborescence</button>
    </div>
    ${(d.results||[]).length ? `<div class="ged-res-list">${rows}</div>` :
      `<div class="ged-empty">Aucun document trouve.<br><span class="ged-empty-hint">La recherche porte sur le nom, les tags, la description et le texte des PDF, Word et Excel. Un PDF scanne n'a pas de couche texte : il ne peut se retrouver que par son nom ou ses tags.</span></div>`}
  `;
}

// ─── Tiroir de detail (superpose) ────────────────────────────────────
async function gedOpenFile(id){
  try{
    const r = await api('/api/qualite/ged/files/' + id);
    if(!r.ok){ showToast('Document introuvable','danger'); return; }
    S.ged.detail = await r.json();
    S.ged.selFile = id;
    if(S.ged.detail.link_type && S.ged.detail.link_id){
      try{
        const lr = await api('/api/qualite/ged/link-label?type=' + encodeURIComponent(S.ged.detail.link_type)
                             + '&id=' + S.ged.detail.link_id);
        if(lr.ok) S.ged.detail.link_label = (await lr.json()).label;
      }catch(e){}
    }
    gedRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

function gedCloseDetail(){ S.ged.detail = null; S.ged.selFile = null; gedRender(); }

function gedDetailHtml(){
  const f = S.ged.detail;
  if(!f) return '';
  const vers = (f.versions||[]).map(v => `
    <div class="ged-ver${v.is_current?' cur':''}">
      <div class="ged-ver-hd">
        <b>v${v.version}</b>${v.is_current?' <span class="ged-ver-cur">courante</span>':''}
        <span class="ged-ver-meta">${gedFmtSize(v.size_bytes)} - ${escHtml(fmtDateTime(v.uploaded_at))}${v.uploaded_by_nom?' - '+escHtml(v.uploaded_by_nom):''}</span>
      </div>
      ${v.commentaire?`<div class="ged-ver-com">${escHtml(v.commentaire)}</div>`:''}
      <div class="ged-ver-acts">
        <a class="ged-mini" href="/api/qualite/ged/files/${f.id}/download?version=${v.version}">Telecharger</a>
        ${v.is_current?'':`<button class="ged-mini" onclick="gedRestoreVersion(${f.id},${v.version})">Remettre en courante</button>`}
      </div>
    </div>
  `).join('');

  const apercu = gedIsPreviewable(f.ext)
    ? `<div class="ged-d-thumb" onclick="gedPreview(${f.id})" title="Agrandir">
         ${['png','jpg','jpeg','gif','webp','svg','bmp'].indexOf((f.ext||'').toLowerCase())!==-1
           ? `<img src="/api/qualite/ged/files/${f.id}/preview" alt="">`
           : `<iframe src="/api/qualite/ged/files/${f.id}/preview#toolbar=0" title="Apercu"></iframe><span class="ged-d-thumb-ov">Agrandir</span>`}
       </div>`
    : '';

  return `
    <div class="ged-drawer-hd">
      <div class="ged-drawer-ico">${gedFileIco(f.ext)}</div>
      <div class="ged-drawer-title" title="${escAttr(f.nom)}">${escHtml(f.nom)}</div>
      <button class="ged-drawer-x" onclick="gedCloseDetail()" title="Fermer (Echap)">&times;</button>
    </div>
    <div class="ged-drawer-bd">
      ${apercu}
      <div class="ged-d-row"><span class="ged-d-lbl">Emplacement</span>
        <span class="ged-d-val ged-d-link" onclick="gedOpen(${f.folder_id||0})">${escHtml(f.path||'/')}</span></div>
      <div class="ged-d-row"><span class="ged-d-lbl">Taille</span>
        <span class="ged-d-val">${gedFmtSize(f.size_bytes)}</span></div>
      <div class="ged-d-row"><span class="ged-d-lbl">Depose</span>
        <span class="ged-d-val">${escHtml(fmtDateTime(f.created_at))}${f.created_by_nom?' par '+escHtml(f.created_by_nom):''}</span></div>
      ${f.link_type?`<div class="ged-d-row"><span class="ged-d-lbl">Rattachement</span>
        <span class="ged-d-val">${gedLinkBadge(f.link_type)} ${escHtml(f.link_label||('#'+f.link_id))}</span></div>`:''}
      <div class="ged-d-row"><span class="ged-d-lbl">Indexation</span>
        <span class="ged-d-val">${f.index_status==='ok'
          ? '<span class="ged-ok-dot">contenu indexe</span>'
          : '<span class="ged-warn-dot" title="Aucun texte extrait : PDF scanne, image, ou format non supporte. Ajoutez des tags pour pouvoir le retrouver.">contenu non indexe</span>'}</span></div>
      ${f.description?`<div class="ged-d-block"><div class="ged-d-lbl">Description</div><div class="ged-d-desc">${escHtml(f.description)}</div></div>`:''}
      ${f.tags?`<div class="ged-d-block"><div class="ged-d-lbl">Tags</div>
        <div class="ged-tags">${f.tags.split(',').map(t=>`<span class="ged-tag">${escHtml(t)}</span>`).join('')}</div></div>`:''}

      <div class="ged-d-acts">
        <a class="btn btn-accent ged-btn" href="/api/qualite/ged/files/${f.id}/download">Telecharger</a>
        <button class="btn btn-ghost ged-btn" onclick="gedEditMeta(${f.id})">Modifier</button>
        <button class="btn btn-ghost ged-btn" onclick="gedAskVersion(${f.id})">Nouvelle version</button>
        <button class="btn btn-ghost ged-btn ged-btn-danger" onclick="gedDeleteFile(${f.id})">Corbeille</button>
      </div>

      <div class="ged-d-block">
        <div class="ged-d-lbl">Versions (${(f.versions||[]).length})</div>
        <div class="ged-ver-list">${vers}</div>
      </div>
    </div>
  `;
}

// ─── Actions dossiers ────────────────────────────────────────────────
async function gedNewFolder(){
  const nom = prompt('Nom du nouveau dossier :', '');
  if(nom === null) return;
  if(!nom.trim()){ showToast('Nom vide','danger'); return; }
  try{
    const r = await api('/api/qualite/ged/folders', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({parent_id: gedCwd() || null, nom: nom.trim()})
    });
    if(!r.ok){ showToast('Erreur creation dossier','danger'); return; }
    await gedRefresh();
    showToast('Dossier cree.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

function _gedFolderIn(colIndex, id){
  const c = S.ged.cols[colIndex];
  return (c && (c.folders||[]).find(x => x.id === id)) || {};
}

async function gedRenameFolder(colIndex, id){
  const cur = _gedFolderIn(colIndex, id);
  const nom = prompt('Renommer le dossier :', cur.nom || '');
  if(nom === null || !nom.trim()) return;
  try{
    const r = await api('/api/qualite/ged/folders/' + id, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nom: nom.trim()})
    });
    if(!r.ok){ showToast('Erreur renommage','danger'); return; }
    await gedRefresh();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

async function gedDeleteFolder(colIndex, id){
  const cur = _gedFolderIn(colIndex, id);
  const n = (cur.nb_files||0) + (cur.nb_folders||0);
  const msg = n
    ? 'Mettre "' + (cur.nom||'ce dossier') + '" et son contenu (' + n + ' element' + (n>1?'s':'') + ') a la corbeille ?'
    : 'Mettre "' + (cur.nom||'ce dossier') + '" a la corbeille ?';
  if(!confirm(msg)) return;
  try{
    const r = await api('/api/qualite/ged/folders/' + id, {method:'DELETE'});
    if(!r.ok){ showToast('Erreur suppression','danger'); return; }
    // Si on supprime un dossier ouvert plus a droite, on remonte au niveau du clic
    const at = S.ged.path.indexOf(id);
    if(at !== -1){ S.ged.path = S.ged.path.slice(0, at); S.ged.cols = S.ged.cols.slice(0, at); }
    await gedRefresh();
    showToast('Deplace dans la corbeille.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

function gedZip(folderId){
  showToast('Preparation du ZIP...','info');
  window.location.href = '/api/qualite/ged/folders/' + (folderId||0) + '/zip';
}

// ─── Actions fichiers ────────────────────────────────────────────────
async function gedUpload(fileList, folderId){
  if(!fileList || !fileList.length) return;
  const fd = new FormData();
  for(let i = 0; i < fileList.length; i++) fd.append('files', fileList[i]);
  showToast(fileList.length + ' fichier' + (fileList.length>1?'s':'') + ' en cours d\'envoi...','info');
  try{
    const r = await api('/api/qualite/ged/folders/' + (folderId||0) + '/files',
                        {method:'POST', body: fd});
    if(!r.ok){ showToast('Erreur envoi','danger'); return; }
    const d = await r.json();
    await gedRefresh();
    if((d.errors||[]).length){
      showToast(d.errors.length + ' fichier(s) refuse(s) : ' + d.errors[0].detail, 'danger');
    } else {
      showToast((d.created||[]).length + ' fichier(s) ajoute(s).','success');
    }
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

async function gedDeleteFile(id){
  if(!confirm('Mettre ce document a la corbeille ?')) return;
  try{
    const r = await api('/api/qualite/ged/files/' + id, {method:'DELETE'});
    if(!r.ok){ showToast('Erreur suppression','danger'); return; }
    if(S.ged.detail && S.ged.detail.id === id){ S.ged.detail = null; S.ged.selFile = null; }
    await gedRefresh();
    showToast('Deplace dans la corbeille.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

let _gedVersionTarget = null;
function gedAskVersion(id){
  _gedVersionTarget = id;
  document.getElementById('ged-version-input').click();
}
async function gedUploadVersion(fileList){
  if(!fileList || !fileList.length || !_gedVersionTarget) return;
  const com = prompt('Commentaire de version (optionnel) :', '');
  const fd = new FormData();
  fd.append('file', fileList[0]);
  fd.append('commentaire', com || '');
  const id = _gedVersionTarget;
  try{
    const r = await api('/api/qualite/ged/files/' + id + '/version', {method:'POST', body: fd});
    if(!r.ok){
      let msg = 'Erreur envoi version';
      try{ const j = await r.json(); if(j && j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger'); return;
    }
    await gedRefresh();
    await gedOpenFile(id);
    showToast('Nouvelle version enregistree.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
  finally{ _gedVersionTarget = null; }
}

async function gedRestoreVersion(fileId, version){
  if(!confirm('Remettre la version ' + version + ' en version courante ?')) return;
  try{
    const r = await api('/api/qualite/ged/files/' + fileId + '/versions/' + version + '/restore',
                        {method:'POST'});
    if(!r.ok){ showToast('Erreur','danger'); return; }
    await gedRefresh();
    await gedOpenFile(fileId);
    showToast('Version ' + version + ' remise en courante.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

// ─── Apercu plein ecran ──────────────────────────────────────────────
function gedPreview(id){
  const wrap = _refMroot();
  const src = '/api/qualite/ged/files/' + id + '/preview';
  let f = (S.ged.detail && S.ged.detail.id === id) ? S.ged.detail : null;
  if(!f){
    for(const c of (S.ged.cols||[])){
      const hit = (c.files||[]).find(x => x.id === id);
      if(hit){ f = hit; break; }
    }
  }
  if(!f && S.ged.results) f = (S.ged.results.results||[]).find(x => x.id === id);
  f = f || {};
  const isImg = ['png','jpg','jpeg','gif','webp','svg','bmp'].indexOf((f.ext||'').toLowerCase()) !== -1;
  wrap.innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal ged-modal-preview">
        <div class="modal-hd">
          <h3>${escHtml(f.nom||'Apercu')}</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button>
        </div>
        <div class="modal-bd ged-preview-bd">
          ${isImg ? `<img src="${src}" alt="${escAttr(f.nom||'')}">`
                  : `<iframe src="${src}" title="Apercu"></iframe>`}
        </div>
        <div class="modal-ft">
          <a class="btn btn-ghost" href="${src}" target="_blank">Ouvrir dans un onglet</a>
          <a class="btn btn-accent" href="/api/qualite/ged/files/${id}/download">Telecharger</a>
        </div>
      </div>
    </div>`;
}

// ─── Modales metadonnees ─────────────────────────────────────────────
async function gedEditMeta(id){
  let f = (S.ged.detail && S.ged.detail.id === id) ? S.ged.detail : null;
  if(!f){
    const r = await api('/api/qualite/ged/files/' + id);
    if(!r.ok){ showToast('Document introuvable','danger'); return; }
    f = await r.json();
  }
  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal" style="max-width:520px">
        <div class="modal-hd"><h3>Modifier le document</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button></div>
        <div class="modal-bd">
          <div class="aud-info-cell" style="margin-bottom:12px">
            <div class="aud-info-label">Nom</div>
            <input type="text" id="gedm-nom" value="${escAttr(f.nom||'')}">
          </div>
          <div class="aud-info-cell" style="margin-bottom:12px">
            <div class="aud-info-label">Description</div>
            <textarea id="gedm-desc" rows="3">${escHtml(f.description||'')}</textarea>
          </div>
          <div class="aud-info-cell" style="margin-bottom:12px">
            <div class="aud-info-label">Tags (separes par des virgules)</div>
            <input type="text" id="gedm-tags" value="${escAttr(f.tags||'')}"
                   placeholder="fsc, certificat, 2026">
            <div class="ged-hint">Les tags sont cherchables. Indispensables sur un PDF scanne, qui n'a pas de contenu texte a indexer.</div>
          </div>
          <div class="aud-info-cell">
            <div class="aud-info-label">Rattachement (optionnel)</div>
            <div style="display:flex;gap:8px">
              <select id="gedm-ltype" onchange="gedLoadLinkOptions('gedm')" style="flex:0 0 140px">
                <option value="">Aucun</option>
                <option value="client"${f.link_type==='client'?' selected':''}>Client</option>
                <option value="fournisseur"${f.link_type==='fournisseur'?' selected':''}>Fournisseur</option>
                <option value="norme"${f.link_type==='norme'?' selected':''}>Norme RSE</option>
              </select>
              <select id="gedm-lid" style="flex:1"><option value="">-</option></select>
            </div>
          </div>
        </div>
        <div class="modal-ft">
          <button class="btn btn-ghost" onclick="closeMroot()">Annuler</button>
          <button class="btn btn-accent" onclick="gedSaveMeta(${id})">Enregistrer</button>
        </div>
      </div>
    </div>`;
  if(f.link_type) await gedLoadLinkOptions('gedm', f.link_id);
}

async function gedLoadLinkOptions(prefix, preselect){
  const t = document.getElementById(prefix + '-ltype').value;
  const sel = document.getElementById(prefix + '-lid');
  if(!t){ sel.innerHTML = '<option value="">-</option>'; return; }
  try{
    const r = await api('/api/qualite/ged/link-options?type=' + encodeURIComponent(t));
    if(!r.ok) return;
    const d = await r.json();
    sel.innerHTML = '<option value="">- choisir -</option>' + (d.options||[]).map(o =>
      `<option value="${o.id}"${preselect && o.id===preselect?' selected':''}>${escHtml(o.label||('#'+o.id))}</option>`
    ).join('');
  }catch(e){}
}

async function gedSaveMeta(id){
  const nom  = document.getElementById('gedm-nom').value.trim();
  const desc = document.getElementById('gedm-desc').value;
  const tags = document.getElementById('gedm-tags').value;
  const lt   = document.getElementById('gedm-ltype').value;
  const li   = document.getElementById('gedm-lid').value;
  if(lt && !li){ showToast('Choisir la cible du rattachement, ou remettre "Aucun".','danger'); return; }
  try{
    const r = await api('/api/qualite/ged/files/' + id, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nom, description: desc, tags,
                            link_type: lt || null, link_id: li ? parseInt(li,10) : null})
    });
    if(!r.ok){ showToast('Erreur enregistrement','danger'); return; }
    closeMroot();
    await gedRefresh();
    await gedOpenFile(id);
    showToast('Document mis a jour.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

async function gedFolderProps(id){
  const r0 = await api('/api/qualite/ged/folders/' + id);
  if(!r0.ok){ showToast('Dossier introuvable','danger'); return; }
  const f = (await r0.json()).folder || {};
  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal" style="max-width:480px">
        <div class="modal-hd"><h3>Proprietes du dossier</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button></div>
        <div class="modal-bd">
          <div class="aud-info-cell" style="margin-bottom:12px">
            <div class="aud-info-label">Nom</div>
            <input type="text" id="gedf-nom" value="${escAttr(f.nom||'')}">
          </div>
          <div class="aud-info-cell" style="margin-bottom:12px">
            <div class="aud-info-label">Description</div>
            <textarea id="gedf-desc" rows="3">${escHtml(f.description||'')}</textarea>
          </div>
          <div class="aud-info-cell">
            <div class="aud-info-label">Rattachement (optionnel)</div>
            <div style="display:flex;gap:8px">
              <select id="gedf-ltype" onchange="gedLoadLinkOptions('gedf')" style="flex:0 0 140px">
                <option value="">Aucun</option>
                <option value="client"${f.link_type==='client'?' selected':''}>Client</option>
                <option value="fournisseur"${f.link_type==='fournisseur'?' selected':''}>Fournisseur</option>
                <option value="norme"${f.link_type==='norme'?' selected':''}>Norme RSE</option>
              </select>
              <select id="gedf-lid" style="flex:1"><option value="">-</option></select>
            </div>
          </div>
        </div>
        <div class="modal-ft">
          <button class="btn btn-ghost" onclick="closeMroot()">Annuler</button>
          <button class="btn btn-accent" onclick="gedSaveFolderProps(${id})">Enregistrer</button>
        </div>
      </div>
    </div>`;
  if(f.link_type) await gedLoadLinkOptions('gedf', f.link_id);
}

async function gedSaveFolderProps(id){
  const nom  = document.getElementById('gedf-nom').value.trim();
  const desc = document.getElementById('gedf-desc').value;
  const lt   = document.getElementById('gedf-ltype').value;
  const li   = document.getElementById('gedf-lid').value;
  if(lt && !li){ showToast('Choisir la cible du rattachement, ou remettre "Aucun".','danger'); return; }
  try{
    const r = await api('/api/qualite/ged/folders/' + id, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nom, description: desc,
                            link_type: lt || null, link_id: li ? parseInt(li,10) : null})
    });
    if(!r.ok){ showToast('Erreur enregistrement','danger'); return; }
    closeMroot();
    await gedRefresh();
    showToast('Dossier mis a jour.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

// ─── Glisser-deposer : fichiers du bureau ET deplacement interne ─────
function gedDragStart(ev, kind, id){
  S.ged._drag = {kind, id};
  try{ ev.dataTransfer.setData('text/plain', kind + ':' + id); }catch(e){}
  ev.dataTransfer.effectAllowed = 'move';
}
function gedDragOver(ev, el){
  ev.preventDefault();
  ev.stopPropagation();
  if(el) el.classList.add('over');
}
function gedDragLeave(el){ if(el) el.classList.remove('over'); }

async function gedDrop(ev, targetFolderId, el){
  ev.preventDefault();
  ev.stopPropagation();
  if(el) el.classList.remove('over');

  // 1) Fichiers venant du bureau
  if(ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files.length){
    return gedUpload(ev.dataTransfer.files, targetFolderId);
  }
  // 2) Deplacement interne
  const d = S.ged._drag;
  S.ged._drag = null;
  if(!d) return;
  const tgt = targetFolderId || null;
  try{
    if(d.kind === 'folder'){
      if(d.id === targetFolderId) return;
      const r = await api('/api/qualite/ged/folders/' + d.id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({move:true, parent_id: tgt})
      });
      if(!r.ok){
        let msg = 'Deplacement impossible';
        try{ const j = await r.json(); if(j && j.detail) msg = j.detail; }catch(e){}
        showToast(msg,'danger'); return;
      }
      // Le dossier deplace peut avoir quitte le chemin ouvert : on le tronque
      const at = S.ged.path.indexOf(d.id);
      if(at !== -1){ S.ged.path = S.ged.path.slice(0, at); S.ged.cols = S.ged.cols.slice(0, at); }
    } else {
      const r = await api('/api/qualite/ged/files/' + d.id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({move:true, folder_id: tgt})
      });
      if(!r.ok){ showToast('Deplacement impossible','danger'); return; }
    }
    await gedRefresh();
    showToast('Deplace.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

// ─── Corbeille ───────────────────────────────────────────────────────
async function gedOpenTrash(){
  try{
    const r = await api('/api/qualite/ged/trash');
    if(!r.ok){ showToast('Erreur corbeille','danger'); return; }
    S.ged.trash = await r.json();
    S.ged.mode = 'trash';
    S.ged.results = null;
    gedRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

function gedTrashHtml(){
  const groups = (S.ged.trash && S.ged.trash.groups) || [];
  const rows = groups.map(g => `
    <div class="ged-trash-row">
      <div class="ged-trash-ico">${g.kind==='folder'?GED_FOLDER_SVG:gedFileIco((g.files[0]||{}).ext)}</div>
      <div class="ged-trash-body">
        <div class="ged-trash-name">${escHtml(g.label)}</div>
        <div class="ged-trash-meta">
          ${g.count} element${g.count>1?'s':''} - supprime le ${escHtml(fmtDateTime(g.deleted_at))}${g.deleted_by_nom?' par '+escHtml(g.deleted_by_nom):''}
        </div>
      </div>
      <div class="ged-trash-acts">
        <button class="btn btn-ghost ged-btn" onclick="gedTrashRestore('${escAttr(g.trash_id)}')">Restaurer</button>
        ${S.isQualiteAdmin?`<button class="btn btn-ghost ged-btn ged-btn-danger" onclick="gedTrashPurge('${escAttr(g.trash_id)}')">Supprimer definitivement</button>`:''}
      </div>
    </div>
  `).join('');

  return `
    <div class="ged-res-hd">
      <div><b>Corbeille</b> <span class="ged-empty-hint">- rien n'est purge automatiquement</span></div>
      <button class="btn btn-ghost ged-btn" onclick="S.ged.mode='browse';gedRender()">Retour a l'arborescence</button>
    </div>
    ${groups.length ? `<div class="ged-trash-list">${rows}</div>`
                    : '<div class="ged-empty">La corbeille est vide.</div>'}
  `;
}

async function gedTrashRestore(tid){
  try{
    const r = await api('/api/qualite/ged/trash/' + tid + '/restore', {method:'POST'});
    if(!r.ok){ showToast('Erreur restauration','danger'); return; }
    await gedLoadTrashCount();
    await gedOpenTrash();
    showToast('Restaure.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

async function gedTrashPurge(tid){
  if(!confirm('Suppression DEFINITIVE : les fichiers seront effaces du disque et ne pourront pas etre recuperes. Continuer ?')) return;
  try{
    const r = await api('/api/qualite/ged/trash/' + tid, {method:'DELETE'});
    if(!r.ok){ showToast('Erreur purge','danger'); return; }
    await gedLoadTrashCount();
    await gedOpenTrash();
    showToast('Supprime definitivement.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur reseau','danger'); }
}

// ─── CSS ─────────────────────────────────────────────────────────────
(function injectGedCSS(){
  if(document.getElementById('ged-css')) return;
  const st = document.createElement('style');
  st.id = 'ged-css';
  st.textContent = `
  .sifa-tabs{display:flex;gap:4px;padding:4px;background:var(--card);border:1px solid var(--border);
    border-radius:10px;margin-bottom:16px;width:fit-content}
  .sifa-tab{padding:8px 18px;border-radius:7px;border:none;background:transparent;color:var(--text2);
    font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s;white-space:nowrap}
  .sifa-tab:hover{color:var(--text)}
  .sifa-tab.active{background:var(--accent);color:var(--btn-fg)}

  .ged-searchbar{position:relative;margin-bottom:14px}
  .ged-searchbar input{width:100%;padding:11px 38px 11px 38px;background:var(--card);
    border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;
    font-family:inherit;transition:.15s}
  .ged-searchbar input:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px var(--accent-bg)}
  .ged-search-ico{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
  .ged-search-x{position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;
    color:var(--muted);font-size:20px;cursor:pointer;line-height:1;padding:0 4px}
  .ged-search-x:hover{color:var(--danger)}

  .ged-shell{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}

  .ged-bc{display:flex;align-items:center;gap:5px;flex-wrap:wrap;padding:12px 16px;
    border-bottom:1px solid var(--border);font-size:12.5px}
  .ged-bc-item{padding:3px 8px;border-radius:6px;cursor:pointer;color:var(--text2);transition:.12s}
  .ged-bc-item:hover{background:var(--accent-bg);color:var(--accent)}
  .ged-bc-item.cur{color:var(--text);font-weight:700}
  .ged-bc-sep{color:var(--muted)}

  .ged-toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:12px 16px;
    border-bottom:1px solid var(--border)}
  .ged-toolbar-sp{flex:1}
  .ged-btn{padding:7px 12px;font-size:12px;display:inline-flex;align-items:center;gap:5px;
    text-decoration:none;white-space:nowrap}
  .ged-btn-danger:hover{color:var(--danger);border-color:var(--danger)}
  .ged-count{font-size:10px;background:var(--accent-bg);color:var(--accent);border-radius:999px;
    padding:1px 6px;font-weight:800}

  /* ── Colonnes horizontales (Miller columns) ── */
  .ged-cols{display:flex;overflow-x:auto;overflow-y:hidden;height:calc(100vh - 340px);min-height:320px;
    scroll-behavior:smooth}
  .ged-col{flex:0 0 246px;display:flex;flex-direction:column;min-width:0;
    border-right:1px solid var(--border);background:var(--card);transition:background .12s}
  .ged-col.last{background:var(--card)}
  .ged-col.over{background:var(--accent-bg)}
  .ged-col-hd{display:flex;align-items:center;gap:6px;padding:8px 12px;border-bottom:1px solid var(--border);
    background:var(--bg);position:sticky;top:0;z-index:1}
  .ged-col-title{flex:1;min-width:0;font-size:10.5px;font-weight:800;text-transform:uppercase;
    letter-spacing:.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ged-col-n{font-size:10px;color:var(--muted);background:var(--card);border:1px solid var(--border);
    border-radius:999px;padding:0 6px}
  .ged-col-bd{flex:1;overflow-y:auto;padding:5px 5px 12px}
  .ged-col-empty{padding:26px 12px;text-align:center;color:var(--muted);font-size:11.5px;line-height:1.6}
  .ged-col-empty span{font-size:10.5px;opacity:.7}

  .ged-row{position:relative;display:flex;align-items:center;gap:7px;padding:7px 8px;border-radius:7px;
    cursor:pointer;color:var(--text2);font-size:12.5px;transition:.12s;user-select:none}
  .ged-row:hover{background:var(--accent-bg);color:var(--accent)}
  .ged-row.open{background:var(--accent-bg);color:var(--accent);font-weight:700}
  .ged-row.sel{background:var(--accent-bg);color:var(--accent);box-shadow:inset 2px 0 0 var(--accent)}
  .ged-row.over{background:var(--accent-bg);outline:2px dashed var(--accent);outline-offset:-2px}
  .ged-row-ico{flex:0 0 auto;display:flex;align-items:center}
  .ged-row-ico.folder{color:var(--accent)}
  .ged-row-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}
  .ged-row-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ged-row-meta{font-size:10px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ged-row-chev{flex:0 0 auto;color:var(--muted);opacity:.6}
  .ged-row.open .ged-row-chev{color:var(--accent);opacity:1}
  .ged-row-acts{position:absolute;right:24px;top:50%;transform:translateY(-50%);display:none;gap:3px;
    background:var(--card);border-radius:6px;padding:1px}
  .ged-row-file .ged-row-acts{right:5px}
  .ged-row:hover .ged-row-acts{display:flex}
  .ged-row-act{width:20px;height:20px;display:flex;align-items:center;justify-content:center;border-radius:5px;
    background:var(--bg);color:var(--text2);border:1px solid var(--border);cursor:pointer;transition:.12s}
  .ged-row-act:hover{color:var(--accent);border-color:var(--accent)}
  .ged-row-act.del:hover{color:var(--danger);border-color:var(--danger)}

  .ged-hint-bar{padding:9px 16px;border-top:1px solid var(--border);font-size:10.5px;color:var(--muted);
    background:var(--bg)}

  .ged-ext{display:inline-flex;align-items:center;justify-content:center;min-width:32px;height:20px;
    padding:0 5px;border-radius:5px;font-size:9px;font-weight:800;letter-spacing:.3px;
    background:var(--border);color:var(--text2)}
  .ged-ext-pdf{background:rgba(248,113,113,.16);color:#f87171}
  .ged-ext-doc{background:rgba(96,165,250,.16);color:#60a5fa}
  .ged-ext-xls{background:rgba(52,211,153,.16);color:#34d399}
  .ged-ext-ppt{background:rgba(251,146,60,.16);color:#fb923c}
  .ged-ext-img{background:rgba(167,139,250,.16);color:#a78bfa}
  .ged-ext-zip{background:rgba(251,191,36,.16);color:#fbbf24}

  .ged-link-badge{flex:0 0 auto;font-size:8.5px;font-weight:700;padding:1px 5px;border-radius:999px;
    background:var(--bg);border:1px solid var(--border);color:var(--muted)}
  .ged-tags{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px}
  .ged-tag{font-size:9.5px;padding:1px 6px;border-radius:999px;background:var(--accent-bg);
    color:var(--accent);border:1px solid var(--border)}

  .ged-empty{padding:56px 20px;text-align:center;color:var(--muted);font-size:13px;line-height:1.6}
  .ged-empty-hint{font-size:11.5px;color:var(--muted);opacity:.85}

  .ged-res-hd{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 16px;
    border-bottom:1px solid var(--border);font-size:13px;color:var(--text2);flex-wrap:wrap}
  .ged-res-list{display:flex;flex-direction:column;max-height:calc(100vh - 300px);overflow-y:auto}
  .ged-res{display:flex;gap:12px;align-items:flex-start;padding:12px 16px;border-bottom:1px solid var(--border);
    cursor:pointer;transition:.12s}
  .ged-res:hover{background:var(--accent-bg)}
  .ged-res-ico{flex:0 0 auto;padding-top:2px}
  .ged-res-body{flex:1;min-width:0}
  .ged-res-name{font-size:13px;font-weight:700;color:var(--text);word-break:break-word}
  .ged-res-path{font-size:11px;color:var(--muted);margin-top:2px;cursor:pointer;display:inline-block}
  .ged-res-path:hover{color:var(--accent);text-decoration:underline}
  .ged-res-snip{font-size:11.5px;color:var(--text2);margin-top:5px;line-height:1.5;
    background:var(--bg);border:1px solid var(--border);border-radius:7px;padding:6px 9px}
  .ged-res-snip mark{background:var(--accent-bg);color:var(--accent);font-weight:700;padding:0 2px;border-radius:3px}
  .ged-res-actions{flex:0 0 auto;display:flex;gap:5px}

  /* ── Tiroir de detail, superpose ── */
  .ged-drawer-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:900;
    animation:gedFade .16s ease-out}
  .ged-drawer{position:fixed;top:0;right:0;bottom:0;width:380px;max-width:92vw;z-index:901;
    background:var(--card);border-left:1px solid var(--border);box-shadow:-16px 0 40px rgba(0,0,0,.28);
    display:flex;flex-direction:column;animation:gedSlide .18s cubic-bezier(.32,.72,0,1)}
  @keyframes gedFade{from{opacity:0}to{opacity:1}}
  @keyframes gedSlide{from{transform:translateX(24px);opacity:0}to{transform:translateX(0);opacity:1}}
  .ged-drawer-hd{display:flex;align-items:flex-start;gap:9px;padding:16px 14px 12px;
    border-bottom:1px solid var(--border)}
  .ged-drawer-ico{flex:0 0 auto;padding-top:1px}
  .ged-drawer-title{flex:1;font-size:13.5px;font-weight:700;color:var(--text);word-break:break-word;line-height:1.35}
  .ged-drawer-x{background:none;border:none;color:var(--muted);font-size:24px;line-height:1;cursor:pointer;padding:0 2px}
  .ged-drawer-x:hover{color:var(--danger)}
  .ged-drawer-bd{flex:1;overflow-y:auto;padding:14px 14px 24px}

  .ged-d-thumb{position:relative;height:170px;border:1px solid var(--border);border-radius:9px;overflow:hidden;
    margin-bottom:14px;background:var(--bg);cursor:pointer;display:flex;align-items:center;justify-content:center}
  .ged-d-thumb img{max-width:100%;max-height:100%;object-fit:contain}
  .ged-d-thumb iframe{width:100%;height:100%;border:none;pointer-events:none}
  .ged-d-thumb-ov{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    background:rgba(0,0,0,.32);color:#fff;font-size:11px;font-weight:700;opacity:0;transition:.15s}
  .ged-d-thumb:hover .ged-d-thumb-ov{opacity:1}

  .ged-d-row{display:flex;gap:8px;font-size:11.5px;margin-bottom:8px;align-items:baseline}
  .ged-d-lbl{flex:0 0 92px;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:700}
  .ged-d-val{flex:1;min-width:0;color:var(--text2);word-break:break-word}
  .ged-d-link{cursor:pointer;color:var(--accent)}
  .ged-d-link:hover{text-decoration:underline}
  .ged-d-block{margin-top:14px;padding-top:12px;border-top:1px solid var(--border)}
  .ged-d-desc{font-size:12px;color:var(--text2);line-height:1.5;margin-top:5px;white-space:pre-wrap}
  .ged-d-acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:16px}
  .ged-ok-dot{color:var(--ok);font-weight:600}
  .ged-warn-dot{color:var(--warn);font-weight:600;cursor:help;border-bottom:1px dotted var(--warn)}

  .ged-ver-list{display:flex;flex-direction:column;gap:8px;margin-top:8px}
  .ged-ver{padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);font-size:11.5px}
  .ged-ver.cur{border-color:var(--accent)}
  .ged-ver-hd{display:flex;flex-wrap:wrap;gap:6px;align-items:baseline;color:var(--text)}
  .ged-ver-cur{font-size:9px;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);
    background:var(--accent-bg);padding:1px 6px;border-radius:999px;font-weight:800}
  .ged-ver-meta{font-size:10px;color:var(--muted)}
  .ged-ver-com{font-size:11px;color:var(--text2);margin-top:4px;font-style:italic}
  .ged-ver-acts{display:flex;gap:8px;margin-top:6px}
  .ged-mini{font-size:10.5px;color:var(--accent);background:none;border:none;padding:0;cursor:pointer;
    text-decoration:none;font-family:inherit}
  .ged-mini:hover{text-decoration:underline}

  .ged-trash-list{display:flex;flex-direction:column;max-height:calc(100vh - 300px);overflow-y:auto}
  .ged-trash-row{display:flex;gap:12px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border)}
  .ged-trash-ico{flex:0 0 auto;color:var(--muted)}
  .ged-trash-body{flex:1;min-width:0}
  .ged-trash-name{font-size:13px;font-weight:600;color:var(--text);word-break:break-word}
  .ged-trash-meta{font-size:11px;color:var(--muted);margin-top:2px}
  .ged-trash-acts{flex:0 0 auto;display:flex;gap:6px;flex-wrap:wrap}

  .ged-hint{font-size:10.5px;color:var(--muted);margin-top:4px;line-height:1.45}
  .ged-modal-preview{max-width:1000px;width:94vw}
  .ged-preview-bd{padding:0;height:70vh;display:flex;align-items:center;justify-content:center;background:var(--bg)}
  .ged-preview-bd iframe{width:100%;height:100%;border:none}
  .ged-preview-bd img{max-width:100%;max-height:100%;object-fit:contain}

  .modal-bd input[type=text], .modal-bd select, .modal-bd textarea{
    width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 10px;
    color:var(--text);font-family:inherit;font-size:13px}
  .modal-bd input[type=text]:focus, .modal-bd select:focus, .modal-bd textarea:focus{
    border-color:var(--accent);outline:none}

  @media(max-width:900px){
    .ged-cols{height:auto;max-height:none;flex-direction:column;overflow-x:hidden}
    .ged-col{flex:1 1 auto;border-right:none;border-bottom:1px solid var(--border);max-height:260px}
    .ged-col-bd{max-height:210px}
    .ged-drawer{width:100%;max-width:100%}
  }
  `;
  document.head.appendChild(st);
})();
"""
