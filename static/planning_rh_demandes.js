/*
 * MySifa — Planning RH : demandes des employés et motifs d'absence.
 *
 * Chargé AVANT le script principal de /planning-rh (comme planning_rh_url.js) :
 * il ne fait que déclarer des fonctions. S, api(), render(), toast(), icon(),
 * escHtml(), fmtDateFull(), TYPE_CONGE_LABELS appartiennent au script
 * principal et ne sont lus qu'à l'appel.
 *
 * Onglet « Demandes » (S.tab === 'demandes'), ouvert à tout employé :
 *   - Mes demandes : déposer une absence (motif), un aménagement d'horaire ou
 *     une autre demande ; annuler tant qu'elle attend ;
 *   - À valider (responsables) : valider, refuser avec un motif ;
 *   - Motifs d'absence (responsables) : référentiel rh_motifs_absence.
 * API : app/routers/planning_rh_demandes.py.
 */

const PRH_DM_STATUTS = { attente_collegue: 'En attente du collègue', en_attente: 'En attente', validee: 'Validée', refusee: 'Refusée', annulee: 'Annulée' };
const PRH_DM_NATURES = { absence: 'Absence', horaire: "Aménagement d'horaire", echange: 'Échange de créneau', autre: 'Autre demande' };
const PRH_DM_CRENEAUX = { matin: 'matin', aprem: 'après-midi', nuit: 'nuit', journee: 'journée' };
const PRH_DM_DECOMPTES = { cp: 'Congés payés', rtt: 'RTT', aucun: 'Aucun solde' };

function prhDmEtatInitial() {
  if (S.dm) return;
  S.dm = {
    motifs: [],            // tous les motifs (actifs et désactivés) — libellés
    mes: [],               // demandes de l'utilisateur connecté
    aValider: [],          // demandes vues par le responsable
    filtre: 'en_attente',  // en_attente | toutes
    form: null,            // formulaire de nouvelle demande (modale 'demande')
    refus: null,           // { id, note } (modale 'refus')
    motifEdit: null,       // brouillon d'un motif (modale 'motifs')
    charge: false,
  };
}

function prhPeutValider() { return !!(S.canEditRH || S.canEditAtelier); }
function prhDemandesSeules() { return !!S.user && !S.hasAtelier && !S.hasRH; }

// Libellés des motifs : alimentent TYPE_CONGE_LABELS, lu partout dans la page.
function prhAppliquerMotifs(motifs) {
  S.dm.motifs = motifs || [];
  if (typeof TYPE_CONGE_LABELS === 'object' && S.dm.motifs.length) {
    Object.keys(TYPE_CONGE_LABELS).forEach(k => { delete TYPE_CONGE_LABELS[k]; });
    S.dm.motifs.forEach(m => { TYPE_CONGE_LABELS[m.code] = m.libelle; });
  }
}
function prhMotifsActifs(demandablesSeulement) {
  return (S.dm.motifs || []).filter(m => m.actif && (!demandablesSeulement || m.demandable));
}
function prhMotifsOptions(selection) {
  const liste = prhMotifsActifs(false);
  const src = liste.length ? liste.map(m => [m.code, m.libelle]) : Object.entries(TYPE_CONGE_LABELS);
  return src.map(([k, v]) => `<option value="${escHtml(k)}"${selection === k ? ' selected' : ''}>${escHtml(v)}</option>`).join('');
}

async function prhChargerMotifs() {
  prhDmEtatInitial();
  try {
    const d = await api('/motifs?tous=1');
    if (d) prhAppliquerMotifs(d.motifs);
  } catch (e) { /* page utilisable sans référentiel : libellés par défaut */ }
}

async function prhChargerDemandes() {
  prhDmEtatInitial();
  if (S.dm.enCours) return;
  S.dm.enCours = true;
  try {
    const mes = await api('/demandes/mes');
    S.dm.mes = (mes && mes.demandes) || [];
    S.dm.recues = (mes && mes.recues) || [];
  } catch (e) { toast('Erreur demandes : ' + e.message, 'error'); }
  if (prhPeutValider()) {
    try {
      const q = S.dm.filtre === 'en_attente' ? '?statut=en_attente' : ('?annee=' + S.annee);
      const d = await api('/demandes' + q);
      S.dm.aValider = (d && d.demandes) || [];
    } catch (e) { S.dm.aValider = []; }
  }
  S.dm.charge = true;
  S.dm.enCours = false;
  render();
}

// Pastille de l'onglet : demandes en attente vues par le responsable.
async function prhCompterAValider() {
  prhDmEtatInitial();
  if (!prhPeutValider()) return;
  try {
    const d = await api('/demandes?statut=en_attente');
    S.dm.nbAttente = ((d && d.demandes) || []).length;
    if (S.dm.filtre === 'en_attente') S.dm.aValider = (d && d.demandes) || [];
    if (typeof renderSidebar === 'function') renderSidebar();
  } catch (e) {}
}

function prhDmPeriode(d) {
  const deb = fmtDateFull(d.date_debut), fin = fmtDateFull(d.date_fin);
  return deb === fin ? deb : deb + ' → ' + fin;
}
function prhDmObjet(d) {
  if (d.nature === 'absence') return escHtml(d.motif_libelle || TYPE_CONGE_LABELS[d.motif_code] || d.motif_code || 'Absence')
    + (d.nb_jours != null ? ` · <strong>${parseFloat(d.nb_jours)}j</strong>` : '');
  if (d.nature === 'horaire') return "Horaire " + escHtml(d.heure_debut || '') + '–' + escHtml(d.heure_fin || '');
  if (d.nature === 'echange') return prhDmAff(d.aff_machine, d.aff_creneau) + ' ↔ ' + escHtml(d.cible_nom || '?')
    + ' (' + prhDmAff(d.cible_machine, d.cible_creneau) + ')';
  return 'Autre demande';
}
function prhDmAff(machine, creneau) {
  return escHtml([machine, PRH_DM_CRENEAUX[creneau] || creneau].filter(Boolean).join(' · ') || 'créneau supprimé');
}
// Collègues du même service déjà absents (renvoyé par l'API pour une absence en attente).
function prhDmAbsents(d) {
  const a = d.absents;
  if (!a || !a.noms || !a.noms.length) return '';
  const depasse = a.seuil != null && a.pic + 1 > a.seuil;
  return `<div class="rh-dm-absents${depasse ? ' depasse' : ''}">${icon('alert', 11)} Déjà absents : ${escHtml(a.noms.join(', '))}`
    + (a.seuil != null ? ` · max ${a.seuil}` : '') + '</div>';
}
function prhDmBadge(statut) {
  return `<span class="rh-badge dm-${escHtml(statut)}">${escHtml(PRH_DM_STATUTS[statut] || statut)}</span>`;
}

// ── Onglet ────────────────────────────────────────────────────────
function buildDemandesTab() {
  prhDmEtatInitial();
  if (!S.dm.charge && !S.dm.enCours) { prhChargerDemandes(); }
  const wrap = document.createElement('div'); wrap.className = 'rh-conges-wrap';

  // === Mes demandes ===
  const mes = document.createElement('div'); mes.className = 'rh-section';
  const lignesMes = (S.dm.mes || []).map(d => `
    <tr>
      <td>${escHtml(PRH_DM_NATURES[d.nature] || d.nature)}</td>
      <td>${prhDmObjet(d)}</td>
      <td>${prhDmPeriode(d)}</td>
      <td class="rh-dm-com">${escHtml(d.commentaire) || '—'}</td>
      <td>${prhDmBadge(d.statut)}${d.decision_note ? `<div class="rh-dm-note">${escHtml(d.decision_note)}</div>` : ''}</td>
      <td>${d.statut === 'en_attente' || d.statut === 'attente_collegue' ? `<button class="rh-act-btn del" onclick="prhAnnulerDemande(${d.id})">Annuler</button>` : ''}</td>
    </tr>`).join('');
  const recues = (S.dm.recues || []).filter(d => d.statut === 'attente_collegue');
  if (recues.length) {
    const rc = document.createElement('div'); rc.className = 'rh-section rh-dm-recues';
    rc.innerHTML = `
      <div class="rh-section-hdr"><span class="rh-section-title">${icon('users', 13)} Échanges proposés par un collègue</span></div>
      <div class="rh-dm-scroll"><table class="rh-table"><tbody>${recues.map(d => `
        <tr>
          <td style="font-weight:600">${escHtml(d.user_nom)}</td>
          <td>Semaine ${escHtml(String(d.semaine || '').split('-W')[1] || '')}</td>
          <td>Vous lui donnez : <strong>${prhDmAff(d.cible_machine, d.cible_creneau)}</strong><br>Vous prenez : <strong>${prhDmAff(d.aff_machine, d.aff_creneau)}</strong></td>
          <td class="rh-dm-com">${escHtml(d.commentaire) || '—'}</td>
          <td style="white-space:nowrap">
            <button class="rh-act-btn ok" onclick="prhRepondreEchange(${d.id},true)">${icon('check', 11)} Accepter</button>
            <button class="rh-act-btn del" onclick="prhRepondreEchange(${d.id},false)">${icon('x', 11)} Refuser</button>
          </td>
        </tr>`).join('')}</tbody></table></div>`;
    wrap.appendChild(rc);
  }
  mes.innerHTML = `
    <div class="rh-section-hdr">
      <span class="rh-section-title">${icon('mail', 13)} Mes demandes</span>
      <button class="rh-icon-btn" onclick="prhOuvrirDemande()">${icon('plus', 12)} Nouvelle demande</button>
    </div>
    <div class="rh-dm-scroll"><table class="rh-table">
      <thead><tr><th>Type</th><th>Objet</th><th>Période</th><th>Commentaire</th><th>Statut</th><th></th></tr></thead>
      <tbody>${lignesMes || `<tr><td colspan="6" class="rh-empty">${S.dm.charge ? 'Aucune demande. Congé, formation, aménagement d\'horaire : « Nouvelle demande ».' : 'Chargement…'}</td></tr>`}</tbody>
    </table></div>`;
  wrap.appendChild(mes);

  if (!prhPeutValider()) return wrap;

  // === À valider ===
  const val = document.createElement('div'); val.className = 'rh-section';
  const lignes = (S.dm.aValider || []).map(d => `
    <tr>
      <td style="font-weight:600">${escHtml(d.user_nom)}</td>
      <td>${escHtml(PRH_DM_NATURES[d.nature] || d.nature)}</td>
      <td>${prhDmObjet(d)}${d.statut === 'en_attente' ? prhDmAbsents(d) : ''}</td>
      <td>${d.nature === 'echange' ? 'Semaine ' + escHtml(String(d.semaine || '').split('-W')[1] || '') : prhDmPeriode(d)}</td>
      <td class="rh-dm-com">${escHtml(d.commentaire) || '—'}</td>
      <td>${prhDmBadge(d.statut)}${d.decision_par ? `<div class="rh-dm-note">${escHtml(d.decision_par)}${d.decision_note ? ' · ' + escHtml(d.decision_note) : ''}</div>` : ''}</td>
      <td style="white-space:nowrap">${d.statut === 'en_attente' ? `
        <button class="rh-act-btn ok" onclick="prhDecider(${d.id},'valider')">${icon('check', 11)} Valider</button>
        <button class="rh-act-btn del" onclick="prhOuvrirRefus(${d.id})">${icon('x', 11)} Refuser</button>` : ''}</td>
    </tr>`).join('');
  val.innerHTML = `
    <div class="rh-section-hdr">
      <span class="rh-section-title">${icon('check', 13)} Demandes à traiter</span>
      <div class="rh-dm-pills">
        <button class="rh-dm-pill${S.dm.filtre === 'en_attente' ? ' active' : ''}" onclick="prhFiltreDemandes('en_attente')">En attente</button>
        <button class="rh-dm-pill${S.dm.filtre === 'toutes' ? ' active' : ''}" onclick="prhFiltreDemandes('toutes')">Toutes ${S.annee}</button>
        <button class="rh-icon-btn" onclick="prhOuvrirMotifs()">${icon('settings', 12)} Motifs d'absence</button>
        <button class="rh-icon-btn" onclick="prhOuvrirSeuils()">${icon('users', 12)} Seuils d'absence</button>
      </div>
    </div>
    <div class="rh-dm-scroll"><table class="rh-table">
      <thead><tr><th>Employé</th><th>Type</th><th>Objet</th><th>Période</th><th>Commentaire</th><th>Statut</th><th>Actions</th></tr></thead>
      <tbody>${lignes || `<tr><td colspan="7" class="rh-empty">${S.dm.filtre === 'en_attente' ? 'Aucune demande en attente.' : 'Aucune demande pour ' + S.annee + '.'}</td></tr>`}</tbody>
    </table></div>`;
  wrap.appendChild(val);
  return wrap;
}

function prhFiltreDemandes(f) {
  S.dm.filtre = (f === 'toutes') ? 'toutes' : 'en_attente';
  prhChargerDemandes();
}

// ── Nouvelle demande ──────────────────────────────────────────────
function prhOuvrirDemande(nature) {
  prhDmEtatInitial();
  const motifs = prhMotifsActifs(true);
  S.dm.form = {
    nature: nature || 'absence',
    motif_code: (motifs[0] && motifs[0].code) || 'CP',
    date_debut: '', date_fin: '', nb_jours: '',
    heure_debut: '', heure_fin: '', commentaire: '',
  };
  S.modal = 'demande'; render();
}

function prhJoursOuvres(deb, fin) {
  if (!deb || !fin || fin < deb) return null;
  let n = 0; const d = new Date(deb + 'T00:00:00'); const f = new Date(fin + 'T00:00:00');
  while (d <= f) { const j = d.getDay(); if (j !== 0 && j !== 6) n++; d.setDate(d.getDate() + 1); }
  return n;
}

function prhDmChamp(cle, valeur) {
  S.dm.form[cle] = valeur;
  if (cle === 'nature' && valeur === 'echange' && !S.dm.form.semaine) { prhDmChampSemaine(weekStr(new Date())); return; }
  if (cle === 'date_debut' && (!S.dm.form.date_fin || S.dm.form.date_fin < valeur)) S.dm.form.date_fin = valeur;
  if (cle === 'nature' || cle === 'date_debut' || cle === 'date_fin') render();
}

function buildDemandeModal() {
  const f = S.dm.form; if (!f) return null;
  const ov = document.createElement('div'); ov.className = 'rh-modal-ov';
  ov.addEventListener('mousedown', e => { if (e.target === ov) { S.modal = null; render(); } });
  const box = document.createElement('div'); box.className = 'rh-modal-box';
  const ouvres = prhJoursOuvres(f.date_debut, f.date_fin);
  const natures = Object.entries(PRH_DM_NATURES).map(([k, v]) =>
    `<button type="button" class="rh-dm-pill${f.nature === k ? ' active' : ''}" onclick="prhDmChamp('nature','${k}')">${escHtml(v)}</button>`).join('');
  const motifs = prhMotifsActifs(true).map(m =>
    `<option value="${escHtml(m.code)}"${f.motif_code === m.code ? ' selected' : ''}>${escHtml(m.libelle)}</option>`).join('');
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>Nouvelle demande</h3>
    <div class="rh-field"><label>Type de demande</label><div class="rh-dm-pills">${natures}</div></div>
    ${f.nature === 'echange' ? prhDmChampsEchange(f) : ''}
    ${f.nature === 'absence' ? `
      <div class="rh-field"><label>Motif *</label>
        <select onchange="prhDmChamp('motif_code',this.value)">${motifs}</select></div>` : ''}
    <div class="rh-dm-grid"${f.nature === 'echange' ? ' hidden' : ''}>
      <div class="rh-field"><label>${f.nature === 'horaire' ? 'Du *' : 'Date début *'}</label>
        <input type="date" value="${escHtml(f.date_debut)}" onchange="prhDmChamp('date_debut',this.value)"></div>
      <div class="rh-field"><label>${f.nature === 'horaire' ? 'Au *' : 'Date fin *'}</label>
        <input type="date" value="${escHtml(f.date_fin)}" min="${escHtml(f.date_debut)}" onchange="prhDmChamp('date_fin',this.value)"></div>
    </div>
    ${f.nature === 'absence' ? `
      <div class="rh-field"><label>Nombre de jours</label>
        <input type="number" min="0.5" step="0.5" value="${escHtml(f.nb_jours)}" placeholder="${ouvres != null ? ouvres + ' jour(s) ouvré(s)' : 'Calculé sur les jours ouvrés'}"
          onchange="prhDmChamp('nb_jours',this.value)">
        <small class="rh-dm-aide">Laisser vide pour compter les jours ouvrés de la période. Demi-journée : 0,5.</small></div>` : ''}
    ${f.nature === 'horaire' ? `
      <div class="rh-dm-grid">
        <div class="rh-field"><label>Heure d'arrivée souhaitée *</label>
          <input type="time" value="${escHtml(f.heure_debut)}" onchange="prhDmChamp('heure_debut',this.value)"></div>
        <div class="rh-field"><label>Heure de départ souhaitée *</label>
          <input type="time" value="${escHtml(f.heure_fin)}" onchange="prhDmChamp('heure_fin',this.value)"></div>
      </div>` : ''}
    <div class="rh-field"><label>${f.nature === 'absence' || f.nature === 'echange' ? 'Commentaire' : 'Motif de la demande *'}</label>
      <textarea id="prh-dm-com" rows="3" maxlength="1000" placeholder="${f.nature === 'absence' ? 'Optionnel' : 'Expliquez votre demande'}"
        oninput="S.dm.form.commentaire=this.value"></textarea></div>
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="S.modal=null;render();">Annuler</button>
      <button class="rh-btn primary" id="prh-dm-envoyer" onclick="prhEnvoyerDemande()">${icon('check', 13)} Envoyer la demande</button>
    </div>`;
  // Saisie libre : textContent, jamais interpolée dans le HTML.
  box.querySelector('#prh-dm-com').value = f.commentaire || '';
  ov.appendChild(box);
  return ov;
}

async function prhEnvoyerDemande() {
  const f = S.dm.form; if (!f) return;
  if (f.nature === 'echange') {
    if (!f.affectation_id || !f.affectation_cible_id) { toast('Choisissez votre créneau et celui du collègue.', 'error'); return; }
    return prhEnvoyerCorps({ nature: 'echange', affectation_id: f.affectation_id, affectation_cible_id: f.affectation_cible_id, commentaire: f.commentaire });
  }
  if (!f.date_debut) { toast('Date de début obligatoire.', 'error'); return; }
  const corps = { nature: f.nature, date_debut: f.date_debut, date_fin: f.date_fin || f.date_debut, commentaire: f.commentaire };
  if (f.nature === 'absence') { corps.motif_code = f.motif_code; if (f.nb_jours !== '') corps.nb_jours = parseFloat(String(f.nb_jours).replace(',', '.')); }
  if (f.nature === 'horaire') { corps.heure_debut = f.heure_debut; corps.heure_fin = f.heure_fin; }
  return prhEnvoyerCorps(corps);
}

async function prhEnvoyerCorps(corps) {
  const btn = document.getElementById('prh-dm-envoyer'); if (btn) btn.disabled = true;
  try {
    await api('/demandes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
    toast('Demande envoyée.', 'success');
    S.modal = null; S.dm.form = null;
    await prhChargerDemandes();
    prhCompterAValider();
  } catch (e) { toast(e.message, 'error'); if (btn) btn.disabled = false; }
}

async function prhAnnulerDemande(id) {
  if (!confirm('Annuler cette demande ?')) return;
  try {
    await api('/demandes/' + id + '/annuler', { method: 'POST' });
    toast('Demande annulée.', 'success');
    await prhChargerDemandes();
    prhCompterAValider();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Décision du responsable ───────────────────────────────────────
async function prhDecider(id, decision, note, forcer) {
  forcer = forcer || [];
  const r = await fetch(API + '/demandes/' + id + '/decision', {
    credentials: 'include', method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note: note || '', forcer }),
  });
  if (r.status === 401) { window.location.href = '/'; return; }
  const d = await r.json().catch(() => ({}));
  // Conflit à confirmer (seuil d'absences, planning) : un par un, puis on renvoie.
  if (r.status === 409 && d.detail && d.detail.conflict_type) {
    if (confirm(d.detail.message)) return prhDecider(id, decision, note, forcer.concat([d.detail.conflict_type]));
    return;
  }
  if (!r.ok) { toast((typeof d.detail === 'string' ? d.detail : '') || ('Erreur ' + r.status), 'error'); return; }
  toast(decision === 'valider' ? 'Demande validée.' : 'Demande refusée.', 'success');
  S.modal = null; S.dm.refus = null;
  await prhChargerDemandes();
  prhCompterAValider();
  // Une absence validée devient un congé : planning et soldes à jour.
  if (decision === 'valider' && (S.hasAtelier || S.hasRH)) { loadData(); if (S.soldes && S.soldes.length) loadSoldes(); }
}

function prhOuvrirRefus(id) { S.dm.refus = { id, note: '' }; S.modal = 'refus'; render(); }

function buildRefusModal() {
  const rf = S.dm.refus; if (!rf) return null;
  const d = (S.dm.aValider || []).find(x => x.id === rf.id);
  const ov = document.createElement('div'); ov.className = 'rh-modal-ov';
  ov.addEventListener('mousedown', e => { if (e.target === ov) { S.modal = null; render(); } });
  const box = document.createElement('div'); box.className = 'rh-modal-box';
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>Refuser la demande</h3>
    ${d ? `<p class="rh-dm-aide" style="margin-bottom:12px">${escHtml(d.user_nom)} · ${prhDmObjet(d)} · ${prhDmPeriode(d)}</p>` : ''}
    <div class="rh-field"><label>Motif du refus * (visible par le demandeur)</label>
      <textarea id="prh-refus-note" rows="3" maxlength="500" oninput="S.dm.refus.note=this.value"></textarea></div>
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="S.modal=null;render();">Annuler</button>
      <button class="rh-btn danger" onclick="prhConfirmerRefus()">${icon('x', 13)} Refuser</button>
    </div>`;
  box.querySelector('#prh-refus-note').value = rf.note || '';
  ov.appendChild(box);
  requestAnimationFrame(() => { const t = document.getElementById('prh-refus-note'); if (t) t.focus(); });
  return ov;
}

function prhConfirmerRefus() {
  const rf = S.dm.refus; if (!rf) return;
  if (!String(rf.note || '').trim()) { toast('Motif du refus obligatoire.', 'error'); return; }
  prhDecider(rf.id, 'refuser', rf.note);
}

// ── Motifs d'absence (référentiel) ────────────────────────────────
function prhOuvrirMotifs() { S.dm.motifEdit = null; S.modal = 'motifs'; render(); }

function prhEditerMotif(id) {
  const m = id ? (S.dm.motifs || []).find(x => x.id === id) : null;
  S.dm.motifEdit = m ? { ...m } : { id: null, libelle: '', decompte: 'aucun', demandable: 1, actif: 1 };
  render();
}

function buildMotifsModal() {
  const ov = document.createElement('div'); ov.className = 'rh-modal-ov';
  ov.addEventListener('mousedown', e => { if (e.target === ov) { S.modal = null; render(); } });
  const box = document.createElement('div'); box.className = 'rh-modal-box'; box.style.maxWidth = '620px';
  const ed = S.dm.motifEdit;
  const lignes = (S.dm.motifs || []).map(m => `
    <tr class="${m.actif ? '' : 'rh-dm-inactif'}">
      <td style="font-weight:600">${escHtml(m.libelle)}</td>
      <td>${escHtml(PRH_DM_DECOMPTES[m.decompte] || m.decompte)}</td>
      <td>${m.demandable ? '✓' : '—'}</td>
      <td>${m.actif ? 'Actif' : 'Désactivé'}</td>
      <td><button class="rh-act-btn" onclick="prhEditerMotif(${m.id})">Modifier</button></td>
    </tr>`).join('');
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>Motifs d'absence</h3>
    <p class="rh-dm-aide" style="margin-bottom:12px">Le décompte dit sur quel solde le motif s'impute. « Demandable » : proposé aux employés dans leurs demandes.</p>
    <div class="rh-dm-scroll"><table class="rh-table">
      <thead><tr><th>Motif</th><th>Décompte</th><th>Demandable</th><th>État</th><th></th></tr></thead>
      <tbody>${lignes || '<tr><td colspan="5" class="rh-empty">Aucun motif.</td></tr>'}</tbody>
    </table></div>
    ${ed ? `
      <div class="rh-dm-edit">
        <div class="rh-field"><label>Libellé *</label><input type="text" id="prh-motif-lib" maxlength="60"></div>
        <div class="rh-dm-grid">
          <div class="rh-field"><label>Décompte</label>
            <select onchange="S.dm.motifEdit.decompte=this.value">${Object.entries(PRH_DM_DECOMPTES).map(([k, v]) => `<option value="${k}"${ed.decompte === k ? ' selected' : ''}>${v}</option>`).join('')}</select></div>
          <div class="rh-field"><label>Options</label>
            <label class="rh-dm-check"><input type="checkbox"${ed.demandable ? ' checked' : ''} onchange="S.dm.motifEdit.demandable=this.checked?1:0"> Demandable par les employés</label>
            <label class="rh-dm-check"><input type="checkbox"${ed.actif ? ' checked' : ''} onchange="S.dm.motifEdit.actif=this.checked?1:0"> Actif</label></div>
        </div>
        <div class="rh-modal-acts" style="margin-top:4px">
          <button class="rh-btn secondary" onclick="S.dm.motifEdit=null;render();">Annuler</button>
          <button class="rh-btn primary" onclick="prhEnregistrerMotif()">${icon('check', 13)} Enregistrer</button>
        </div>
      </div>` : `
      <div class="rh-modal-acts"><button class="rh-btn primary" onclick="prhEditerMotif(null)">${icon('plus', 13)} Nouveau motif</button></div>`}`;
  if (ed) {
    const lib = box.querySelector('#prh-motif-lib');
    lib.value = ed.libelle || '';
    lib.addEventListener('input', () => { S.dm.motifEdit.libelle = lib.value; });
  }
  ov.appendChild(box);
  return ov;
}

async function prhEnregistrerMotif() {
  const ed = S.dm.motifEdit; if (!ed) return;
  if (!String(ed.libelle || '').trim()) { toast('Libellé obligatoire.', 'error'); return; }
  const corps = { libelle: ed.libelle.trim(), decompte: ed.decompte, demandable: !!ed.demandable, actif: !!ed.actif };
  try {
    if (ed.id) await api('/motifs/' + ed.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
    else await api('/motifs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
    toast('Motif enregistré.', 'success');
    S.dm.motifEdit = null;
    await prhChargerMotifs();
  } catch (e) { toast(e.message, 'error'); }
  render();
}

// ── Horaires aménagés validés, affichés dans le planning ──────────
// Chargés avec le planning atelier (loadData) : S.dmHoraires.
async function prhChargerHoraires(from, to) {
  try {
    const d = await api('/horaires?from_week=' + encodeURIComponent(from) + '&to_week=' + encodeURIComponent(to));
    S.dmHoraires = (d && d.horaires) || [];
  } catch (e) { S.dmHoraires = []; }
}

function prhHorairesSemaine(userId, ws) {
  const lun = weekMonday(ws); const dim = new Date(lun); dim.setDate(lun.getDate() + 6);
  const a = toLocalDateStr(lun), b = toLocalDateStr(dim);
  return (S.dmHoraires || []).filter(h => h.user_id === userId && h.date_debut <= b && h.date_fin >= a);
}

function prhHoraireLibelle(h) {
  const per = h.date_debut === h.date_fin ? 'le ' + fmtDateFull(h.date_debut)
    : 'du ' + fmtDateFull(h.date_debut) + ' au ' + fmtDateFull(h.date_fin);
  return 'Horaire aménagé ' + (h.heure_debut || '') + '–' + (h.heure_fin || '') + ' ' + per;
}

// Badge sous le nom d'une personne dans une cellule de la grille.
function prhBadgeHoraire(userId, ws) {
  const hs = prhHorairesSemaine(userId, ws);
  if (!hs.length) return null;
  const b = document.createElement('span');
  b.className = 'rh-horaire-inline-badge';
  b.textContent = hs.map(h => (h.heure_debut || '') + '–' + (h.heure_fin || '')).join(' · ');
  b.title = hs.map(prhHoraireLibelle).join('\n');
  return b;
}

// ── Échanges de créneau ───────────────────────────────────────────
async function prhDmChampSemaine(ws) {
  const f = S.dm.form; if (!f) return;
  f.semaine = ws; f.affectation_id = ''; f.affectation_cible_id = ''; f.options = null;
  render();
  try { f.options = await api('/echanges/options?semaine=' + encodeURIComponent(ws)); }
  catch (e) { f.options = { miennes: [], collegues: [] }; toast(e.message, 'error'); }
  if (f.options.miennes.length === 1) f.affectation_id = String(f.options.miennes[0].id);
  if (S.dm.form === f) render();
}

function prhDmChampsEchange(f) {
  const sems = Array.from({ length: 6 }, (_, i) => addWeeks(weekStr(new Date()), i));
  const lib = a => [a.machine_nom, PRH_DM_CRENEAUX[a.creneau] || a.creneau].filter(Boolean).join(' · ');
  const o = f.options;
  let corps;
  if (!o) corps = '<div class="rh-dm-aide">Chargement des créneaux…</div>';
  else if (!o.miennes.length) corps = '<div class="rh-dm-aide">Vous n\'êtes pas affecté(e) cette semaine : rien à échanger.</div>';
  else corps = `
    <div class="rh-field"><label>Mon créneau *</label>
      <select onchange="S.dm.form.affectation_id=this.value"><option value="">Choisir…</option>
        ${o.miennes.map(a => `<option value="${a.id}"${String(f.affectation_id) === String(a.id) ? ' selected' : ''}>${escHtml(lib(a))}</option>`).join('')}</select></div>
    <div class="rh-field"><label>Créneau du collègue *</label>
      <select onchange="S.dm.form.affectation_cible_id=this.value"><option value="">Choisir…</option>
        ${o.collegues.map(a => `<option value="${a.id}"${String(f.affectation_cible_id) === String(a.id) ? ' selected' : ''}>${escHtml(a.user_nom + ' — ' + lib(a))}</option>`).join('')}</select>
      <small class="rh-dm-aide">Le collègue reçoit la demande et l'accepte, puis le responsable valide.</small></div>`;
  return `<div class="rh-field"><label>Semaine</label>
      <select onchange="prhDmChampSemaine(this.value)">${sems.map(s => `<option value="${s}"${s === f.semaine ? ' selected' : ''}>${fmtWeekLabel(s)}</option>`).join('')}</select></div>` + corps;
}

async function prhRepondreEchange(id, accepter) {
  if (!accepter && !confirm('Refuser cet échange ?')) return;
  try {
    await api('/demandes/' + id + '/reponse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ accepter }) });
    toast(accepter ? 'Échange accepté — en attente du responsable.' : 'Échange refusé.', 'success');
    await prhChargerDemandes();
    prhCompterAValider();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Seuils d'absences simultanées ─────────────────────────────────
async function prhOuvrirSeuils() {
  try { const d = await api('/absences-seuils'); S.dm.seuils = (d && d.seuils) || []; }
  catch (e) { toast(e.message, 'error'); return; }
  S.modal = 'seuils'; render();
}

function buildSeuilsModal() {
  const ov = document.createElement('div'); ov.className = 'rh-modal-ov';
  ov.addEventListener('mousedown', e => { if (e.target === ov) { S.modal = null; render(); } });
  const box = document.createElement('div'); box.className = 'rh-modal-box';
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>Seuils d'absences simultanées</h3>
    <p class="rh-dm-aide" style="margin-bottom:12px">Nombre maximal de personnes d'un même service absentes le même jour. Au-delà, la validation d'une absence demande confirmation. Vide : pas de limite.</p>
    <table class="rh-table"><tbody>${(S.dm.seuils || []).map((s, i) => `
      <tr><td style="font-weight:600">${escHtml(s.libelle)}</td>
        <td style="width:120px"><div class="rh-field" style="margin:0"><input type="number" min="1" max="99" value="${s.max_absents == null ? '' : s.max_absents}" placeholder="—"
          onchange="S.dm.seuils[${i}].max_absents=this.value"></div></td></tr>`).join('')}</tbody></table>
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="S.modal=null;render();">Annuler</button>
      <button class="rh-btn primary" onclick="prhEnregistrerSeuils()">${icon('check', 13)} Enregistrer</button>
    </div>`;
  ov.appendChild(box);
  return ov;
}

async function prhEnregistrerSeuils() {
  try {
    await api('/absences-seuils', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seuils: (S.dm.seuils || []).map(s => ({ service: s.service, max_absents: s.max_absents === '' ? null : s.max_absents })) }) });
    toast('Seuils enregistrés.', 'success');
    S.modal = null;
    S.dm.charge = false;
  } catch (e) { toast(e.message, 'error'); }
  render();
}
