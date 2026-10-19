"""MySifa - Assets de l'onglet EUDR (MyQualite > Certifications SIFA > EUDR).

JS et CSS injectes dans /qualite par le placeholder __EUDR_ASSETS__, apres ceux
de l'onglet FSC dont on reprend les classes (fsc-hero, fsc-btn, fsc-kpis).

L'onglet suit le questionnaire EUDR envoye aux fournisseurs : qui a ete
sollicite, qui a ouvert le lien, qui a repondu et ce qu'il a repondu (role,
perimetre, transmission des numeros de reference des DDS).

API : app/routers/qualite_eudr.py.
"""

EUDR_JS = r"""
// ══════════════════════════════════════════════════════════════════════
// Certifications SIFA - onglet 4 : EUDR
// ══════════════════════════════════════════════════════════════════════

S.eudr = {
  data: null,        // reponse de /api/qualite/eudr/fournisseurs
  q: '',
  filtre: 'tous',    // tous | sollicites | attente | repondus | jamais
  sel: new Set(),
  bobines: true,     // seulement les fournisseurs de bobines papier (categories frontal/complexe/glassine)
};
try{ const _eb = localStorage.getItem('mysifa_eudr_bobines'); if(_eb !== null) S.eudr.bobines = _eb === '1'; }catch(e){}

const EUDR_LANGUES = {en:'Anglais', fr:'Français', es:'Espagnol'};

const EUDR_STATUTS = {
  jamais:   {lbl:'Non sollicité', cls:''},
  envoyee:  {lbl:'Envoyé',        cls:'warn'},
  ouverte:  {lbl:'Lien ouvert',   cls:'info'},
  repondue: {lbl:'Répondu',       cls:'ok'},
};

async function eudrEnter(){
  const root = document.getElementById('content');
  if(!root) return;
  if(!S.eudr.data){
    root.innerHTML = `${sifaTabsHtml('eudr')}
      <div class="fsc-hero"><div class="fsc-hero-txt"><h1>EUDR</h1><p>Chargement des fournisseurs…</p></div></div>`;
  }
  await eudrLoad();
}

async function eudrLoad(){
  try{
    const r = await api('/api/qualite/eudr/fournisseurs');
    if(!r.ok){ showToast('Chargement EUDR impossible.','danger'); return; }
    S.eudr.data = await r.json();
    if(gedActiveTab() !== 'eudr') return;
    eudrRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

function eudrLignes(){
  const d = S.eudr.data; if(!d) return [];
  const q = (S.eudr.q||'').trim().toLowerCase();
  return (d.fournisseurs||[]).filter(l => {
    if(S.eudr.bobines && !l.bobines) return false;
    if(q && [l.nom,l.groupe,l.pays].join(' ').toLowerCase().indexOf(q) === -1) return false;
    if(S.eudr.filtre === 'sollicites') return l.statut !== 'jamais';
    if(S.eudr.filtre === 'attente') return l.statut === 'envoyee' || l.statut === 'ouverte';
    if(S.eudr.filtre === 'repondus') return l.statut === 'repondue';
    if(S.eudr.filtre === 'jamais') return l.statut === 'jamais';
    return true;
  });
}

function eudrRender(){
  const root = document.getElementById('content');
  const d = S.eudr.data;
  if(!root || !d) return;
  const all = (d.fournisseurs||[]).filter(l => !S.eudr.bobines || l.bobines);
  const n = st => all.filter(l => l.statut === st).length;
  const sollicites = all.length - n('jamais');
  const kpi = (f, val, lbl) =>
    `<button type="button" class="fsc-kpi eudr-kpi${S.eudr.filtre===f?' active':''}" data-f="${f}" onclick="eudrSetFiltre('${f}')">
       <span class="fsc-kpi-val">${val}</span><span class="fsc-kpi-lbl">${escHtml(lbl)}</span></button>`;
  const admin = fscEstAdmin();
  root.innerHTML = `${sifaTabsHtml('eudr')}
    <div class="fsc-hero">
      <div class="fsc-hero-txt">
        <h1>EUDR</h1>
        <p>Règlement (UE) 2023/1115 sur les produits zéro déforestation. Chaque fournisseur reçoit un lien personnel vers un questionnaire (anglais, français ou espagnol) : périmètre, rôle, codes NC, transmission des numéros de référence des déclarations de diligence raisonnée. Les réponses arrivent ici ; la personne qui a envoyé la demande est prévenue par email.</p>
      </div>
      <div class="fsc-hero-actions">
        <a class="fsc-btn" href="/qualite/eudr/apercu?lang=fr" target="_blank" rel="noopener" title="Le formulaire tel que le voit le fournisseur — rien n'est enregistré">Aperçu du questionnaire</a>
        <button type="button" class="fsc-btn" onclick="eudrOuvrirPdf()" title="Le questionnaire à remplir à la main, en anglais, français ou espagnol">Questionnaire PDF</button>
        ${admin ? `<button type="button" class="fsc-btn" onclick="eudrOuvrirLiensCommuns()" title="Un seul lien à coller dans un email adressé à plusieurs fournisseurs">Lien commun</button>` : ''}
        ${admin ? `<button type="button" class="btn btn-accent" id="eudr-send-btn" onclick="eudrOuvrirEnvoi()" title="Cochez un ou plusieurs fournisseurs : chacun reçoit son lien personnel">Envoyer le questionnaire${S.eudr.sel.size ? ` (${S.eudr.sel.size})` : ''}</button>` : ''}
      </div>
    </div>
    <div class="fsc-kpis">
      ${kpi('sollicites', sollicites, 'Fournisseurs sollicités')}
      ${kpi('attente', n('envoyee')+n('ouverte'), 'En attente de réponse')}
      ${kpi('repondus', n('repondue'), 'Ont répondu')}
      ${kpi('jamais', n('jamais'), 'Jamais sollicités')}
    </div>
    ${eudrRattacherHtml(admin)}
    <div class="eudr-bar">
      <input type="text" id="eudr-q" class="eudr-search" placeholder="Rechercher (fournisseur, groupe, pays)"
        value="${escAttr(S.eudr.q)}" oninput="S.eudr.q=this.value;eudrRenderList()"
        onkeydown="if(event.key==='Escape'){this.value='';S.eudr.q='';eudrRenderList()}">
      <button type="button" class="fsc-btn sm${S.eudr.bobines?' primary':''}" onclick="eudrSetBobines(!S.eudr.bobines)" title="Fournisseurs dont la fiche porte la catégorie frontal (bobine papier), complexe ou glassine">Bobines papier et complexes</button>
      <button type="button" class="fsc-btn sm${S.eudr.filtre==='tous'?' primary':''}" onclick="eudrSetFiltre('tous')">Tous les statuts</button>
      <span class="eudr-selinfo" id="eudr-selinfo"></span>
    </div>
    <div id="eudr-list"></div>`;
  eudrRenderList();
}

function eudrSetFiltre(f){ S.eudr.filtre = f; eudrRender(); }
function eudrSetBobines(on){
  S.eudr.bobines = !!on;
  try{ localStorage.setItem('mysifa_eudr_bobines', on ? '1' : '0'); }catch(e){}
  eudrRender();
}

function eudrRenderList(){
  const box = document.getElementById('eudr-list'); if(!box) return;
  const rows = eudrLignes();
  const admin = fscEstAdmin();
  const info = document.getElementById('eudr-selinfo');
  if(info) info.textContent = S.eudr.sel.size ? `${S.eudr.sel.size} sélectionné(s)` : (admin ? 'Cochez les fournisseurs à solliciter, puis « Envoyer le questionnaire ».' : '');
  const sb = document.getElementById('eudr-send-btn');
  if(sb) sb.textContent = 'Envoyer le questionnaire' + (S.eudr.sel.size ? ` (${S.eudr.sel.size})` : '');
  if(!rows.length){
    box.innerHTML = `<div class="eudr-empty">${S.eudr.q ? `Aucun résultat pour « ${escHtml(S.eudr.q)} »` : 'Aucun fournisseur dans cette vue.'}</div>`;
    return;
  }
  const tous = rows.every(l => S.eudr.sel.has(l.id));
  box.innerHTML = `<div class="eudr-table">
    <div class="eudr-row eudr-head">
      ${admin ? `<span><input type="checkbox" ${tous?'checked':''} onchange="eudrSelTous(this.checked)" title="Tout sélectionner"></span>` : ''}
      <span>Fournisseur</span><span>Statut</span><span>Dernier envoi</span><span>Rôle déclaré</span><span>Transmission des références</span><span></span>
    </div>
    ${rows.map(l => {
      const st = EUDR_STATUTS[l.statut] || EUDR_STATUTS.jamais;
      const rep = l.reponse;
      return `<div class="eudr-row${admin?'':' ro'}">
        ${admin ? `<span><input type="checkbox" ${S.eudr.sel.has(l.id)?'checked':''} onchange="eudrSel(${l.id},this.checked)"></span>` : ''}
        <span><b>${escHtml(l.nom)}</b> <span class="fsc-muted">${escHtml(l.pays||'')}</span>
          ${(l.demandes||[]).length
            ? `<div class="eudr-dest">Envoyé à ${(l.demandes||[]).map(d => escHtml(d.email) +
                (admin ? ` <button type="button" class="eudr-dest-x" title="Retirer ce destinataire : son lien cesse de fonctionner" onclick="eudrAnnulerDemande(${d.id})">×</button>` : '')).join(', ')}</div>`
            : (l.emails.length ? '' : '<div class="eudr-warn">Aucun email connu</div>')}</span>
        <span><span class="eudr-badge ${st.cls}">${escHtml(st.lbl)}</span></span>
        <span class="fsc-muted">${l.derniere_demande ? escHtml(fmtDate(l.derniere_demande)) : '—'}</span>
        <span>${rep ? escHtml(rep.libelles.role || '—') : '—'}</span>
        <span>${rep ? escHtml(rep.libelles.transmission || '—') : '—'}</span>
        <span class="eudr-acts">${rep ? `<button type="button" class="fsc-btn sm" onclick="eudrVoirReponse(${l.id})">Voir la réponse</button>` : ''}
          ${admin ? `<button type="button" class="fsc-btn sm" onclick="eudrOuvrirSaisie(${l.id})" title="Réponse reçue par courrier, email ou téléphone">Saisie manuelle</button>` : ''}</span>
      </div>`;
    }).join('')}
  </div>`;
}

async function eudrAnnulerDemande(id){
  const l = (S.eudr.data.fournisseurs||[]).find(x => (x.demandes||[]).some(d => d.id === id));
  const d = l && l.demandes.find(x => x.id === id);
  if(!d || !confirm(`Retirer ${d.email} pour ${l.nom} ? Le lien envoyé à cette adresse ne fonctionnera plus.`)) return;
  try{
    const r = await api(`/api/qualite/eudr/demandes/${id}/annuler`, {method:'POST'});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Retrait impossible.','danger'); return; }
    S.eudr.data.fournisseurs = j.fournisseurs || S.eudr.data.fournisseurs;
    showToast('Destinataire retiré.','success');
    eudrRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

// ─── Saisie manuelle ─────────────────────────────────────────────────
// Réponse reçue hors formulaire : rôle, périmètre, transmission, commentaire
// obligatoire, courrier en pièce jointe. Le fournisseur passe en « Répondu ».
function eudrOuvrirSaisie(fid){
  const l = (S.eudr.data.fournisseurs||[]).find(x => x.id === fid); if(!l) return;
  const ch = S.eudr.data.choix || {};
  const sel = (name, lbl) => `<label class="eudr-f"><span>${escHtml(lbl)}</span>
    <select id="eudr-m-${name}"><option value="">— Non précisé —</option>
      ${Object.keys(ch[name]||{}).map(k => `<option value="${escAttr(k)}">${escHtml(ch[name][k].court)}</option>`).join('')}
    </select></label>`;
  eudrMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>${escHtml(l.nom)} — saisie manuelle</h3></div>
      <div class="modal-bd">
        <p style="margin:0 0 12px">Pour une réponse reçue par courrier, email ou téléphone. Le fournisseur passe en « Répondu » ; les liens déjà envoyés restent valables.</p>
        ${sel('role','Rôle')}
        ${sel('perimetre','Produits dans le périmètre')}
        ${sel('transmission','Transmission des références')}
        <label class="eudr-f"><span>Commentaire *</span>
          <textarea id="eudr-m-commentaire" rows="4" placeholder="Ce que le fournisseur a répondu, et sa source (courrier du 13/10, appel…)"></textarea></label>
        <label class="eudr-f"><span>Pièce jointe — PDF, image, email (.msg, .eml) ou Word, 15 Mo maximum</span>
          <input type="file" id="eudr-m-piece" accept=".pdf,.png,.jpg,.jpeg,.webp,.msg,.eml,.docx"></label>
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
        <button type="button" class="btn btn-accent" id="eudr-m-go" onclick="eudrEnregistrerSaisie(${fid})">Enregistrer</button>
      </div>
    </div>
  </div>`;
  requestAnimationFrame(() => { const t = document.getElementById('eudr-m-commentaire'); if(t) t.focus(); });
}

async function eudrEnregistrerSaisie(fid){
  const com = document.getElementById('eudr-m-commentaire').value.trim();
  if(!com){ showToast('Commentaire obligatoire — résumez ce que le fournisseur a répondu.','danger'); return; }
  const fd = new FormData();
  ['role','perimetre','transmission'].forEach(k => fd.append(k, document.getElementById('eudr-m-'+k).value));
  fd.append('commentaire', com);
  const f = document.getElementById('eudr-m-piece').files[0];
  if(f) fd.append('piece', f);
  const go = document.getElementById('eudr-m-go'); go.disabled = true; go.textContent = 'Enregistrement…';
  try{
    const r = await api(`/api/qualite/eudr/fournisseurs/${fid}/saisie`, {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Enregistrement impossible.','danger'); go.disabled = false; go.textContent = 'Enregistrer'; return; }
    S.eudr.data.fournisseurs = j.fournisseurs || S.eudr.data.fournisseurs;
    closeMroot();
    showToast('Réponse enregistrée.','success');
    eudrRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); go.disabled = false; go.textContent = 'Enregistrer'; }
}

// ─── Questionnaire PDF ───────────────────────────────────────────────
// ─── Lien commun ─────────────────────────────────────────────────────
// Un lien unique pour un email adressé à plusieurs fournisseurs. Les réponses
// arrivent sans fiche : bloc « à rattacher » au-dessus de la liste.
function eudrOuvrirLiensCommuns(){
  const liens = S.eudr.data.liens_communs || [];
  eudrMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>Lien commun</h3></div>
      <div class="modal-bd">
        <p style="margin:0 0 12px">Un lien à coller dans un email adressé à plusieurs fournisseurs. Chacun indique sa société sur la page d'accueil ; sa réponse arrive dans « Réponses à rattacher », où vous la rangez sous la bonne fiche. Les liens personnels restent préférables quand l'adresse du fournisseur est connue.</p>
        ${liens.length ? liens.map(l => `
          <div class="eudr-lien">
            <div class="eudr-lien-hd"><b>${escHtml(l.libelle)}</b>
              <span class="fsc-muted">${escHtml(EUDR_LANGUES[l.langue] || l.langue)} · ${l.nb_reponses} réponse(s) · créé le ${escHtml(fmtDate(l.created_at))}</span></div>
            <div class="eudr-lien-url">
              <input type="text" readonly value="${escAttr(l.url)}" onclick="this.select()">
              <button type="button" class="fsc-btn sm" onclick="eudrCopierLien(this.previousElementSibling.value)">Copier</button>
              <button type="button" class="fsc-btn sm" onclick="eudrDesactiverLien(${l.id})" title="Le lien cessera de fonctionner">Désactiver</button>
            </div>
          </div>`).join('') : '<p class="fsc-muted" style="margin:0 0 12px">Aucun lien commun actif.</p>'}
        <div class="eudr-lien-new">
          <label class="eudr-f" style="flex:1"><span>Nouveau lien — libellé</span>
            <input type="text" id="eudr-lc-lib" placeholder="Ex. Email distributeurs octobre"></label>
          <label class="eudr-f"><span>Langue d'ouverture</span>
            <select id="eudr-lc-lang">${Object.keys(EUDR_LANGUES).map(k => `<option value="${k}">${EUDR_LANGUES[k]}</option>`).join('')}</select></label>
        </div>
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="closeMroot()">Fermer</button>
        <button type="button" class="btn btn-accent" onclick="eudrCreerLien()">Créer le lien</button>
      </div>
    </div>
  </div>`;
}

async function eudrCopierLien(url){
  try{ await navigator.clipboard.writeText(url); showToast('Lien copié.','success'); }
  catch(e){ showToast('Copie impossible — sélectionnez le lien et copiez-le.','danger'); }
}

async function eudrCreerLien(){
  const libelle = document.getElementById('eudr-lc-lib').value.trim();
  if(!libelle){ showToast('Libellé obligatoire — par exemple « Email distributeurs octobre ».','danger'); return; }
  try{
    const r = await api('/api/qualite/eudr/liens-communs', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({libelle, langue: document.getElementById('eudr-lc-lang').value})});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Création impossible.','danger'); return; }
    S.eudr.data.liens_communs = j.liens_communs || [];
    showToast('Lien créé.','success');
    eudrOuvrirLiensCommuns();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

async function eudrDesactiverLien(id){
  if(!confirm("Désactiver ce lien ? Il cessera de fonctionner pour tous ceux qui l'ont reçu. Les réponses déjà reçues restent.")) return;
  try{
    const r = await api(`/api/qualite/eudr/liens-communs/${id}/desactiver`, {method:'POST'});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Désactivation impossible.','danger'); return; }
    S.eudr.data.liens_communs = j.liens_communs || [];
    showToast('Lien désactivé.','success');
    eudrOuvrirLiensCommuns();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

function eudrRattacherHtml(admin){
  const items = S.eudr.data.a_rattacher || [];
  if(!items.length) return '';
  const fours = (S.eudr.data.fournisseurs||[]).slice().sort((a,b) => a.nom.localeCompare(b.nom));
  return `<div class="eudr-ratt">
    <div class="eudr-ratt-hd">${items.length} réponse(s) reçue(s) par lien commun, à rattacher à une fiche fournisseur</div>
    ${items.map(x => `<div class="eudr-ratt-row">
      <div class="eudr-ratt-qui"><b>${escHtml(x.repondant_societe || '—')}</b>
        <span class="fsc-muted">${escHtml([x.repondant_nom, x.repondant_email].filter(Boolean).join(' · '))} · ${escHtml(fmtDateTime(x.created_at))} · ${escHtml(x.lien_libelle)}</span>
        <span>${escHtml(x.reponse.libelles.role || '—')}</span></div>
      ${admin ? `<select id="eudr-ratt-${x.id}"><option value="">— Choisir le fournisseur —</option>
          ${fours.map(f => `<option value="${f.id}"${f.id===x.suggestion?' selected':''}>${escHtml(f.nom)}</option>`).join('')}</select>
        <button type="button" class="btn btn-accent" onclick="eudrRattacher(${x.id})">Rattacher</button>` : ''}
    </div>`).join('')}
  </div>`;
}

async function eudrRattacher(id){
  const fid = document.getElementById('eudr-ratt-'+id).value;
  if(!fid){ showToast('Choisissez le fournisseur.','danger'); return; }
  try{
    const r = await api(`/api/qualite/eudr/a-rattacher/${id}`, {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({fournisseur_id: parseInt(fid, 10)})});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Rattachement impossible.','danger'); return; }
    S.eudr.data.fournisseurs = j.fournisseurs || S.eudr.data.fournisseurs;
    S.eudr.data.a_rattacher = j.a_rattacher || [];
    showToast('Réponse rattachée.','success');
    eudrRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

function eudrOuvrirPdf(){
  const fours = (S.eudr.data.fournisseurs||[]).filter(l => !S.eudr.bobines || l.bobines);
  const un = S.eudr.sel.size === 1 ? [...S.eudr.sel][0] : null;
  eudrMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>Questionnaire PDF</h3></div>
      <div class="modal-bd">
        <p style="margin:0 0 12px">Les mêmes questions que le formulaire en ligne, à remplir à la main. Votre adresse email figure comme adresse de retour ; la réponse se saisit ensuite avec « Saisie manuelle ».</p>
        <label class="eudr-f"><span>Langue</span>
          <select id="eudr-pdf-lang">${Object.keys(EUDR_LANGUES).map(k => `<option value="${k}">${EUDR_LANGUES[k]}</option>`).join('')}</select></label>
        <label class="eudr-f"><span>Fournisseur (nom imprimé en tête)</span>
          <select id="eudr-pdf-four"><option value="">— Questionnaire vierge —</option>
            ${fours.map(l => `<option value="${l.id}"${l.id===un?' selected':''}>${escHtml(l.nom)}</option>`).join('')}</select></label>
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
        <button type="button" class="btn btn-accent" onclick="eudrTelechargerPdf()">Ouvrir le PDF</button>
      </div>
    </div>
  </div>`;
  const sl = document.getElementById('eudr-pdf-four');
  sl.addEventListener('change', () => {
    const l = fours.find(x => String(x.id) === sl.value);
    if(l && l.langue) document.getElementById('eudr-pdf-lang').value = l.langue;
  });
  if(un){ const l = fours.find(x => x.id === un); if(l && l.langue) document.getElementById('eudr-pdf-lang').value = l.langue; }
}

function eudrTelechargerPdf(){
  const q = new URLSearchParams({lang: document.getElementById('eudr-pdf-lang').value});
  const f = document.getElementById('eudr-pdf-four').value;
  if(f) q.set('fournisseur_id', f);
  window.open('/api/qualite/eudr/questionnaire.pdf?' + q.toString(), '_blank', 'noopener');
  closeMroot();
}

function eudrSel(id, on){ if(on) S.eudr.sel.add(id); else S.eudr.sel.delete(id); eudrRenderList(); }
function eudrSelTous(on){ eudrLignes().forEach(l => on ? S.eudr.sel.add(l.id) : S.eudr.sel.delete(l.id)); eudrRenderList(); }

function eudrMroot(){
  return document.getElementById('mroot') || (function(){
    const d = document.createElement('div'); d.id = 'mroot'; document.body.appendChild(d); return d;
  })();
}

// ─── Envoi ───────────────────────────────────────────────────────────
function eudrOuvrirEnvoi(){
  const d = S.eudr.data; if(!d) return;
  const choisis = (d.fournisseurs||[]).filter(l => S.eudr.sel.has(l.id));
  if(!choisis.length){ showToast('Cochez au moins un fournisseur dans la liste.','info'); return; }
  eudrMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>Envoyer le questionnaire EUDR</h3></div>
      <div class="modal-bd">
        <p style="margin:0 0 12px">Un email part de votre boîte, avec un lien personnel par adresse, dans la langue choisie (le fournisseur peut en changer sur le formulaire). Un fournisseur déjà sollicité reçoit une relance avec le même lien. Séparez plusieurs adresses par une virgule.</p>
        ${choisis.map(l => `
          <div class="eudr-envoi">
            <div class="eudr-envoi-nom"><b>${escHtml(l.nom)}</b> <span class="fsc-muted">${escHtml((EUDR_STATUTS[l.statut]||{}).lbl||'')}</span></div>
            <input type="text" class="eudr-envoi-mail" data-id="${l.id}" value="${escAttr(l.emails.slice(0,1).join(', '))}" placeholder="adresse@fournisseur.com">
            <select class="eudr-envoi-lang" data-id="${l.id}" title="Langue de l'email et du formulaire">
              ${Object.keys(EUDR_LANGUES).map(k => `<option value="${k}"${(l.langue||'en')===k?' selected':''}>${EUDR_LANGUES[k]}</option>`).join('')}
            </select>
          </div>`).join('')}
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
        <button type="button" class="btn btn-accent" id="eudr-go" onclick="eudrEnvoyer()">Envoyer</button>
      </div>
    </div>
  </div>`;
}

async function eudrEnvoyer(){
  const envois = [...document.querySelectorAll('.eudr-envoi-mail')].map(i => ({
    fournisseur_id: parseInt(i.dataset.id, 10),
    emails: i.value.split(/[,;\s]+/).map(s => s.trim()).filter(Boolean),
    langue: (document.querySelector(`.eudr-envoi-lang[data-id="${i.dataset.id}"]`)||{}).value || 'en',
  }));
  const vides = envois.filter(e => !e.emails.length).length;
  if(vides){ showToast(`${vides} fournisseur(s) sans adresse — complétez ou décochez-les.`,'danger'); return; }
  const go = document.getElementById('eudr-go'); if(go){ go.disabled = true; go.textContent = 'Envoi…'; }
  try{
    const r = await api('/api/qualite/eudr/demander', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({envois})});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Envoi impossible.','danger'); if(go){go.disabled=false;go.textContent='Envoyer';} return; }
    closeMroot();
    S.eudr.data.fournisseurs = j.fournisseurs || S.eudr.data.fournisseurs;
    S.eudr.sel.clear();
    const ko = (j.echecs||[]).length + (j.sans_email||[]).length;
    showToast(`Questionnaire envoyé à ${(j.envoyes||[]).length} fournisseur(s).` + (ko ? ` ${ko} échec(s) : ${[...(j.echecs||[]),...(j.sans_email||[])].join(', ')}.` : ''), ko ? 'danger' : 'success');
    eudrRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); if(go){go.disabled=false;go.textContent='Envoyer';} }
}

// ─── Lecture d'une réponse ───────────────────────────────────────────
async function eudrVoirReponse(fid){
  const l = (S.eudr.data.fournisseurs||[]).find(x => x.id === fid); if(!l) return;
  let hist = [];
  try{
    const r = await api(`/api/qualite/eudr/fournisseurs/${fid}/reponses`);
    if(r.ok) hist = (await r.json()).reponses || [];
  }catch(e){ if(e.message === 'unauth') return; }
  const rep = hist[0] || l.reponse; if(!rep) return;
  const lib = rep.libelles || {};
  // v arrive deja echappe : escHtml() au point d'appel.
  const ligne = (k, v) => v ? `<div class="eudr-kv"><span>${escHtml(k)}</span><span>${v}</span></div>` : '';
  eudrMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>${escHtml(l.nom)} — réponse EUDR</h3></div>
      <div class="modal-bd">
        <p class="fsc-muted" style="margin:0 0 12px">${rep.source === 'manuel' ? `Saisie manuelle par ${escHtml(rep.saisi_par || '—')} le` : 'Reçue le'} ${escHtml(fmtDateTime(rep.created_at))}${hist.length > 1 ? ` · ${hist.length} réponses au total, la plus récente fait foi` : ''}</p>
        ${rep.piece_filename ? `<p style="margin:0 0 12px"><a class="fsc-btn sm" href="/api/qualite/eudr/reponses/${rep.id}/piece" target="_blank" rel="noopener">Pièce jointe : ${escHtml(rep.piece_original || 'fichier')}</a></p>` : ''}
        ${ligne('Société', escHtml(rep.repondant_societe))}
        ${ligne('Répondant', escHtml([rep.repondant_nom, rep.repondant_fonction, rep.repondant_email, rep.repondant_tel].filter(Boolean).join(' · ')))}
        ${ligne('Établissement', escHtml(lib.etablissement))}
        ${ligne('Produits dans le périmètre', escHtml(lib.perimetre))}
        ${ligne('Codes NC', escHtml(rep.codes_nc))}
        ${ligne('Rôle', escHtml(lib.role))}
        ${ligne('DDS à partir du', escHtml(rep.date_debut_dds ? fmtDate(rep.date_debut_dds) : ''))}
        ${ligne('Transmission des références', escHtml(lib.transmission))}
        ${ligne('Précisions', escHtml(rep.transmission_detail))}
        ${ligne('Une référence par livraison', escHtml(lib.ref_par_livraison))}
        ${ligne('Fournisseurs amont', escHtml(rep.amont))}
        ${ligne('Géolocalisation disponible', escHtml(lib.geolocalisation))}
        ${ligne('Essences', escHtml(rep.essences))}
        ${ligne('Pays de récolte', escHtml(rep.pays_recolte))}
        ${ligne('Contact EUDR', escHtml([rep.contact_nom, rep.contact_email].filter(Boolean).join(' · ')))}
        ${ligne('Commentaire', escHtml(rep.commentaire))}
      </div>
      <div class="modal-ft"><button type="button" class="fsc-btn" onclick="closeMroot()">Fermer</button></div>
    </div>
  </div>`;
}

(function(){
  const st = document.createElement('style');
  st.textContent = `
  .eudr-kpi.active{border-color:var(--accent);background:var(--accent-bg)}
  .eudr-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
  .eudr-search{flex:1;min-width:220px;max-width:420px;padding:9px 12px;border-radius:10px;border:1px solid var(--border);
    background:var(--card);color:var(--text);font:inherit;font-size:13px}
  .eudr-search:focus{outline:none;border-color:var(--accent)}
  .eudr-selinfo{font-size:12px;color:var(--muted)}
  .eudr-table{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
  .eudr-row{display:grid;grid-template-columns:32px minmax(180px,2fr) 120px 110px minmax(140px,1.5fr) minmax(150px,1.5fr) 150px;
    gap:10px;align-items:center;padding:10px 14px;border-top:1px solid var(--border);font-size:13px;color:var(--text2)}
  .eudr-row.ro{grid-template-columns:minmax(180px,2fr) 120px 110px minmax(140px,1.5fr) minmax(150px,1.5fr) 150px}
  .eudr-head{border-top:none;font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;color:var(--muted)}
  .eudr-row b{color:var(--text)}
  .eudr-ratt{background:var(--card);border:1px solid var(--accent);border-radius:12px;padding:12px 14px;margin-bottom:12px}
  .eudr-ratt-hd{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--accent);margin-bottom:8px}
  .eudr-ratt-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 0;border-top:1px solid var(--border)}
  .eudr-ratt-qui{flex:1;min-width:240px;display:flex;flex-direction:column;font-size:13px;color:var(--text2)}
  .eudr-ratt-qui b{color:var(--text)}
  .eudr-ratt-row select{padding:8px 10px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font:inherit;font-size:13px;min-width:200px}
  .eudr-lien{padding:10px 0;border-bottom:1px solid var(--border)}
  .eudr-lien-hd{display:flex;gap:10px;flex-wrap:wrap;align-items:baseline;margin-bottom:6px}
  .eudr-lien-url{display:flex;gap:6px;flex-wrap:wrap}
  .eudr-lien-url input{flex:1;min-width:220px;padding:7px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);
    color:var(--text);font-family:ui-monospace,Consolas,monospace;font-size:12px}
  .eudr-lien-new{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
  .eudr-lien-new input[type=text]{width:100%;padding:9px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font:inherit;font-size:13px}
  .eudr-acts{display:flex;gap:6px;flex-wrap:wrap}
  .eudr-f{display:block;margin-bottom:12px}
  .eudr-f span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;color:var(--muted);margin-bottom:5px}
  .eudr-f select,.eudr-f textarea,.eudr-f input[type=file]{width:100%;padding:9px 12px;border-radius:10px;border:1px solid var(--border);
    background:var(--bg);color:var(--text);font:inherit;font-size:13px}
  .eudr-dest{font-size:11.5px;color:var(--muted);word-break:break-all}
  .eudr-dest-x{border:1px solid var(--border);background:var(--bg);color:var(--muted);border-radius:6px;width:18px;height:18px;line-height:14px;
    font-size:13px;cursor:pointer;padding:0;margin-left:2px}
  .eudr-dest-x:hover{color:var(--danger);border-color:var(--danger)}
  .eudr-warn{font-size:11px;color:var(--danger);font-weight:600}
  .eudr-badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11.5px;font-weight:700;
    border:1px solid var(--border);color:var(--muted)}
  .eudr-badge.ok{color:var(--success);border-color:var(--success)}
  .eudr-badge.warn{color:var(--warn);border-color:var(--warn)}
  .eudr-badge.info{color:var(--accent);border-color:var(--accent)}
  .eudr-empty{padding:30px;text-align:center;color:var(--muted);background:var(--card);border:1px solid var(--border);border-radius:12px}
  .eudr-envoi{display:flex;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);flex-wrap:wrap}
  .eudr-envoi-nom{flex:1;min-width:180px}
  .eudr-envoi-lang{padding:9px 10px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font:inherit;font-size:13px}
  .eudr-envoi-mail{flex:1.4;min-width:220px;padding:9px 12px;border-radius:10px;border:1px solid var(--border);
    background:var(--bg);color:var(--text);font:inherit;font-size:13px}
  .eudr-kv{display:grid;grid-template-columns:200px 1fr;gap:12px;padding:8px 0;border-bottom:1px solid var(--border)}
  .eudr-kv span:first-child{font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;color:var(--muted)}
  .eudr-kv span:last-child{color:var(--text);white-space:pre-wrap}
  @media (max-width:900px){
    .eudr-row,.eudr-row.ro{grid-template-columns:1fr 1fr}
    .eudr-head{display:none}
    .eudr-kv{grid-template-columns:1fr}
  }
  `;
  document.head.appendChild(st);
})();
"""
