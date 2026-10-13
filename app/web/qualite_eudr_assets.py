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
        ${admin ? `<button type="button" class="btn btn-accent" id="eudr-send-btn" onclick="eudrOuvrirEnvoi()">Envoyer le questionnaire</button>` : ''}
      </div>
    </div>
    <div class="fsc-kpis">
      ${kpi('sollicites', sollicites, 'Fournisseurs sollicités')}
      ${kpi('attente', n('envoyee')+n('ouverte'), 'En attente de réponse')}
      ${kpi('repondus', n('repondue'), 'Ont répondu')}
      ${kpi('jamais', n('jamais'), 'Jamais sollicités')}
    </div>
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
  if(info) info.textContent = S.eudr.sel.size ? `${S.eudr.sel.size} sélectionné(s)` : '';
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
          ${l.emails.length ? '' : '<div class="eudr-warn">Aucun email connu</div>'}</span>
        <span><span class="eudr-badge ${st.cls}">${escHtml(st.lbl)}</span></span>
        <span class="fsc-muted">${l.derniere_demande ? escHtml(fmtDate(l.derniere_demande)) : '—'}</span>
        <span>${rep ? escHtml(rep.libelles.role || '—') : '—'}</span>
        <span>${rep ? escHtml(rep.libelles.transmission || '—') : '—'}</span>
        <span>${rep ? `<button type="button" class="fsc-btn sm" onclick="eudrVoirReponse(${l.id})">Voir la réponse</button>` : ''}</span>
      </div>`;
    }).join('')}
  </div>`;
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
        <p class="fsc-muted" style="margin:0 0 12px">Reçue le ${escHtml(fmtDateTime(rep.created_at))}${hist.length > 1 ? ` · ${hist.length} réponses au total, la plus récente fait foi` : ''}</p>
        ${ligne('Répondant', escHtml([rep.repondant_nom, rep.repondant_fonction, rep.repondant_email].filter(Boolean).join(' · ')))}
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
  .eudr-row{display:grid;grid-template-columns:32px minmax(180px,2fr) 120px 110px minmax(140px,1.5fr) minmax(150px,1.5fr) 130px;
    gap:10px;align-items:center;padding:10px 14px;border-top:1px solid var(--border);font-size:13px;color:var(--text2)}
  .eudr-row.ro{grid-template-columns:minmax(180px,2fr) 120px 110px minmax(140px,1.5fr) minmax(150px,1.5fr) 130px}
  .eudr-head{border-top:none;font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;color:var(--muted)}
  .eudr-row b{color:var(--text)}
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
