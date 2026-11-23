/*
 * MySifa — Planning RH : fermetures collectives (fermeture annuelle, pont…).
 *
 * Une fermeture pose un congé à chaque employé actif sur la même période,
 * avec un motif par défaut. Chaque congé reste ajustable un par un : motif
 * (sans solde, RTT…), nombre de jours, ou retrait (l'employé travaille).
 * API : app/routers/planning_rh_fermetures.py.
 *
 * Fenêtre unique S.modal === 'fermetures', trois écrans tenus dans S.fm :
 *   liste          (S.fm.detail null, S.fm.form null)
 *   formulaire     (S.fm.form : création, ou modification si form.id)
 *   détail         (S.fm.detail : situation employé par employé)
 * Adresse : `fermetures=ouvertes`, `fermeture=<id>` ou `fermeture=<id>-modifier`
 * (planning_rh_url.js). La création en cours n'a pas d'adresse.
 *
 * Chargé après le script principal : S, api(), render(), icon(), toast(),
 * escHtml(), fmtDateFull(), prhMotifsOptions(), TYPE_CONGE_LABELS existent.
 */

const PRH_FM_ETATS = {
  couvert: 'Congé posé',
  deja_absent: 'Déjà absent',
  a_ajouter: 'Sans congé',
  exclu: 'Retiré',
};

function prhFmEtat() {
  if (!S.fm) S.fm = { liste: [], detail: null, form: null, soldes: {}, charge: false };
  return S.fm;
}

function prhPeutFermetures() { return !!S.canEditRH; }

async function prhFmChargerListe() {
  const fm = prhFmEtat();
  try {
    const d = await api('/fermetures');
    fm.liste = (d && d.fermetures) || [];
  } catch (e) { toast(e.message, 'error'); }
  fm.charge = true;
}

async function prhFmChargerSoldes(annee) {
  const fm = prhFmEtat();
  try {
    const d = await api('/soldes?scope=rh&annee=' + encodeURIComponent(annee));
    fm.soldes = {};
    ((d && d.soldes) || []).forEach(s => { fm.soldes[s.user_id] = s; });
    fm.soldesAnnee = annee;
  } catch (e) { fm.soldes = {}; }
}

// Après une écriture : la page (congés, soldes) suit.
async function prhFmRafraichirPage() {
  try { await loadData(); } catch (e) {}
  try { await loadSoldes(); } catch (e) {}
}

async function prhOuvrirFermetures() {
  if (!prhPeutFermetures()) return;
  const fm = prhFmEtat();
  fm.detail = null; fm.form = null;
  S.modal = 'fermetures'; render();
  await prhFmChargerListe();
  render();
}

async function prhFmOuvrir(id, modifier) {
  if (!prhPeutFermetures()) return;
  const fm = prhFmEtat();
  try {
    const d = await api('/fermetures/' + encodeURIComponent(id));
    fm.detail = d; fm.form = null;
    await prhFmChargerSoldes(String(d.date_debut).slice(0, 4));
    S.modal = 'fermetures';
    if (modifier) prhFmModifier();
    else render();
  } catch (e) { toast(e.message, 'error'); }
}

function prhFmFermer() { const fm = prhFmEtat(); fm.detail = null; fm.form = null; S.modal = null; render(); }
function prhFmRetourListe() { const fm = prhFmEtat(); fm.detail = null; fm.form = null; render(); prhFmChargerListe().then(render); }

// ── Formulaire ────────────────────────────────────────────────────
function prhFmNouvelle() {
  const fm = prhFmEtat();
  const an = S.annee || new Date().getFullYear();
  fm.detail = null;
  fm.form = { id: null, libelle: 'Fermeture annuelle', date_debut: an + '-12-28', date_fin: an + '-12-31',
    nb_jours: '', nb_auto: true, type_conge: 'CP', note: '', apercu: null, exclus: {} };
  render();
  prhFmApercu();
}

function prhFmModifier() {
  const fm = prhFmEtat(); const d = fm.detail; if (!d) return;
  fm.form = { id: d.id, libelle: d.libelle, date_debut: d.date_debut, date_fin: d.date_fin,
    nb_jours: d.nb_jours, nb_auto: false, type_conge: d.type_conge, note: d.note || '', apercu: null, exclus: {} };
  render();
}

function prhFmAnnulerForm() { const fm = prhFmEtat(); fm.form = null; render(); }

let _prhFmApercuJeton = 0;
async function prhFmApercu() {
  const f = prhFmEtat().form; if (!f || !f.date_debut || !f.date_fin) return;
  const jeton = ++_prhFmApercuJeton;
  try {
    const d = await api('/fermetures/apercu?du=' + encodeURIComponent(f.date_debut) + '&au=' + encodeURIComponent(f.date_fin));
    if (jeton !== _prhFmApercuJeton || prhFmEtat().form !== f) return;
    f.apercu = d; f.erreur = null;
    if (f.nb_auto && d) f.nb_jours = d.nb_jours;
  } catch (e) {
    if (jeton !== _prhFmApercuJeton) return;
    f.apercu = null; f.erreur = e.message;
  }
  render();
}

function prhFmChamp(cle, val) {
  const f = prhFmEtat().form; if (!f) return;
  f[cle] = val;
  if (cle === 'nb_jours') f.nb_auto = false;
  if (cle === 'date_debut' || cle === 'date_fin') {
    if (f.date_debut && f.date_fin && f.date_fin < f.date_debut && cle === 'date_debut') f.date_fin = f.date_debut;
    if (!f.id) prhFmApercu(); else render();
  }
}

function prhFmBasculer(uid, coche) {
  const f = prhFmEtat().form; if (!f) return;
  if (coche) delete f.exclus[uid]; else f.exclus[uid] = true;
  render();
}

function prhFmTous(coche) {
  const f = prhFmEtat().form; if (!f || !f.apercu) return;
  f.exclus = {};
  if (!coche) f.apercu.employes.forEach(e => { if (e.etat === 'a_ajouter') f.exclus[e.user_id] = true; });
  render();
}

async function prhFmEnregistrer() {
  const fm = prhFmEtat(); const f = fm.form; if (!f) return;
  if (!String(f.libelle || '').trim()) { toast('Nom de la fermeture obligatoire.', 'error'); return; }
  if (!f.date_debut || !f.date_fin) { toast('Dates de début et de fin obligatoires.', 'error'); return; }
  const nb = parseFloat(f.nb_jours);
  if (!(nb > 0)) { toast('Nombre de jours invalide — valeur supérieure à 0.', 'error'); return; }
  const corps = { libelle: f.libelle.trim(), date_debut: f.date_debut, date_fin: f.date_fin,
    nb_jours: nb, type_conge: f.type_conge, note: f.note };
  try {
    let d;
    if (f.id) {
      d = await api('/fermetures/' + f.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
      toast('Fermeture modifiée.', 'success');
    } else {
      corps.exclus = Object.keys(f.exclus).map(Number);
      d = await api('/fermetures', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
      const b = (d && d.bilan) || {};
      toast((b.ajoutes || 0) + ' congé(s) posé(s).', 'success');
    }
    fm.form = null; fm.detail = d;
    await prhFmChargerSoldes(String(d.date_debut).slice(0, 4));
    await prhFmRafraichirPage();
  } catch (e) { toast(e.message, 'error'); }
  render();
}

// ── Détail : ajustements employé par employé ─────────────────────
async function prhFmAjuster(uid, corps) {
  const fm = prhFmEtat(); const d = fm.detail; if (!d) return;
  try {
    fm.detail = await api('/fermetures/' + d.id + '/employes/' + uid, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
    await prhFmChargerSoldes(String(d.date_debut).slice(0, 4));
    await prhFmRafraichirPage();
    toast('Enregistré.', 'success');
  } catch (e) { toast(e.message, 'error'); }
  render();
}

function prhFmRetirer(uid, nom) {
  if (!confirm(nom + ' travaille pendant la fermeture : son congé est supprimé. Continuer ?')) return;
  prhFmAjuster(uid, { inclus: false });
}

async function prhFmAppliquer() {
  const fm = prhFmEtat(); const d = fm.detail; if (!d) return;
  try {
    fm.detail = await api('/fermetures/' + d.id + '/appliquer', { method: 'POST' });
    toast(((fm.detail.bilan || {}).ajoutes || 0) + ' congé(s) posé(s).', 'success');
    await prhFmChargerSoldes(String(d.date_debut).slice(0, 4));
    await prhFmRafraichirPage();
  } catch (e) { toast(e.message, 'error'); }
  render();
}

async function prhFmSupprimer() {
  const fm = prhFmEtat(); const d = fm.detail; if (!d) return;
  const n = (d.compte && d.compte.couvert) || 0;
  if (!confirm('Supprimer « ' + d.libelle + ' » et les ' + n + ' congé(s) posés par cette fermeture ?')) return;
  try {
    await api('/fermetures/' + d.id, { method: 'DELETE' });
    toast('Fermeture supprimée.', 'success');
    await prhFmRafraichirPage();
    prhFmRetourListe();
  } catch (e) { toast(e.message, 'error'); render(); }
}

// ── Rendu ─────────────────────────────────────────────────────────
function _prhFmPeriode(f) {
  return fmtDateFull(f.date_debut) + (f.date_fin !== f.date_debut ? ' → ' + fmtDateFull(f.date_fin) : '');
}
function _prhFmMotifLibelle(code) { return TYPE_CONGE_LABELS[code] || code || ''; }
function _prhFmJours(n) { const v = parseFloat(n); return (isNaN(v) ? '—' : String(v).replace('.', ',')) + ' j'; }

function _prhFmListeHtml(fm) {
  const lignes = (fm.liste || []).map(f => `
    <tr class="rh-fm-ligne" onclick="prhFmOuvrir(${Number(f.id)})">
      <td style="font-weight:600">${escHtml(f.libelle)}</td>
      <td>${_prhFmPeriode(f)}</td>
      <td>${_prhFmJours(f.nb_jours)}</td>
      <td>${escHtml(f.type_libelle || f.type_conge)}</td>
      <td>${Number(f.nb_conges) || 0}</td>
    </tr>`).join('');
  return `
    <h3>Fermetures collectives</h3>
    <p class="rh-dm-aide" style="margin-bottom:12px">Une fermeture pose le même congé à tous les employés actifs. Le motif et les jours restent modifiables employé par employé.</p>
    <div class="rh-dm-scroll"><table class="rh-table">
      <thead><tr><th>Fermeture</th><th>Période</th><th>Jours</th><th>Motif par défaut</th><th>Congés</th></tr></thead>
      <tbody>${lignes || `<tr><td colspan="5" class="rh-empty">${fm.charge ? 'Aucune fermeture.' : 'Chargement…'}</td></tr>`}</tbody>
    </table></div>
    <div class="rh-modal-acts"><button class="rh-btn primary" onclick="prhFmNouvelle()">${icon('plus', 13)} Nouvelle fermeture</button></div>`;
}

function _prhFmFormHtml(fm) {
  const f = fm.form;
  const ap = f.apercu;
  let personnes = '';
  if (!f.id) {
    if (f.erreur) personnes = `<p class="rh-dm-aide" style="color:var(--danger)">${escHtml(f.erreur)}</p>`;
    else if (!ap) personnes = '<p class="rh-dm-aide">Chargement des employés…</p>';
    else {
      const aPoser = ap.employes.filter(e => e.etat === 'a_ajouter');
      const nCoches = aPoser.filter(e => !f.exclus[e.user_id]).length;
      const lignes = ap.employes.map(e => {
        const absent = e.etat === 'deja_absent';
        const info = absent && e.absence
          ? `Déjà absent : ${escHtml(e.absence.libelle || e.absence.type_conge)} du ${fmtDateFull(e.absence.date_debut)} au ${fmtDateFull(e.absence.date_fin)}`
          : '';
        return `<label class="rh-fm-pers${absent ? ' off' : ''}" title="${escHtml(info)}">
          <input type="checkbox"${absent ? ' disabled' : (f.exclus[e.user_id] ? '' : ' checked')}
            onchange="prhFmBasculer(${Number(e.user_id)},this.checked)">
          <span>${escHtml(e.nom)}</span>${absent ? '<span class="rh-fm-mini">déjà absent</span>' : ''}
        </label>`;
      }).join('');
      personnes = `
        <div class="rh-fm-pers-hdr">
          <span>${nCoches} employé(s) sur ${aPoser.length} recevront le congé</span>
          <span><button class="rh-act-btn" onclick="prhFmTous(true)">Tous</button>
                <button class="rh-act-btn" onclick="prhFmTous(false)">Aucun</button></span>
        </div>
        <div class="rh-fm-pers-grid">${lignes}</div>`;
    }
  }
  const optionsMotifHtml = prhMotifsOptions(f.type_conge || 'CP');   // déjà échappées
  const feries = ap && ap.feries && ap.feries.length
    ? `<div class="rh-dm-aide">Férié(s) non compté(s) : ${ap.feries.map(x => escHtml(x.libelle) + ' (' + fmtDateFull(x.date) + ')').join(', ')}</div>` : '';
  return `
    <h3>${f.id ? 'Modifier la fermeture' : 'Nouvelle fermeture collective'}</h3>
    <div class="rh-field"><label>Nom *</label><input type="text" id="prh-fm-lib" maxlength="80" placeholder="ex : Fermeture annuelle"></div>
    <div class="rh-fm-grid3">
      <div class="rh-field"><label>Du *</label><input type="date" value="${escHtml(f.date_debut)}" onchange="prhFmChamp('date_debut',this.value)"></div>
      <div class="rh-field"><label>Au *</label><input type="date" value="${escHtml(f.date_fin)}" onchange="prhFmChamp('date_fin',this.value)"></div>
      <div class="rh-field"><label title="Jours décomptés à chaque employé">Jours *</label>
        <input type="number" min="0.5" step="0.5" value="${escHtml(String(f.nb_jours))}" onchange="prhFmChamp('nb_jours',this.value)"></div>
    </div>
    ${feries}
    <div class="rh-dm-grid">
      <div class="rh-field"><label>Motif par défaut</label>
        <select onchange="prhFmChamp('type_conge',this.value)">${optionsMotifHtml}</select></div>
      <div class="rh-field"><label>Note</label><input type="text" id="prh-fm-note" maxlength="200" placeholder="Optionnel"></div>
    </div>
    ${f.id ? '<p class="rh-dm-aide">Les dates s\'appliquent à tous les congés de la fermeture. Le motif et les jours, seulement aux employés qui n\'ont pas été ajustés un par un.</p>' : ''}
    ${personnes}
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="${f.id ? 'prhFmAnnulerForm()' : 'prhFmRetourListe()'}">Annuler</button>
      <button class="rh-btn primary" onclick="prhFmEnregistrer()">${icon('check', 13)} ${f.id ? 'Enregistrer' : 'Créer et poser les congés'}</button>
    </div>`;
}

function _prhFmDetailHtml(fm) {
  const d = fm.detail;
  const c = d.compte || {};
  const pastilles = Object.keys(PRH_FM_ETATS).filter(k => c[k]).map(k =>
    `<span class="rh-badge rh-fm-${k}">${c[k]} · ${PRH_FM_ETATS[k]}</span>`).join(' ');
  const lignes = (d.employes || []).map(e => {
    const uid = Number(e.user_id);
    const s = fm.soldes[uid];
    const restant = s ? s.restant_cp : null;
    const restantHtml = restant == null ? '—'
      : `<span style="font-weight:700;color:${restant < 0 ? 'var(--danger)' : 'var(--text2)'}">${String(restant).replace('.', ',')} j</span>`;
    const role = e.role ? ` <span class="rh-fm-mini">${escHtml(e.role)}</span>` : '';
    let motifHtml = '—', jours = '—', action = '', etat = `<span class="rh-badge rh-fm-${e.etat}">${PRH_FM_ETATS[e.etat] || e.etat}</span>`;
    if (e.etat === 'couvert') {
      const optionsHtml = prhMotifsOptions(e.type_conge);   // déjà échappées
      motifHtml = `<select class="rh-fm-sel" onchange="prhFmAjuster(${uid},{type_conge:this.value})">${optionsHtml}</select>`;
      jours = `<input class="rh-fm-nb" type="number" min="0.5" step="0.5" value="${escHtml(String(e.nb_jours))}"
        onchange="prhFmAjuster(${uid},{nb_jours:parseFloat(this.value)})">`;
      action = e.inactif ? '' : `<button class="rh-act-btn" onclick="prhFmRetirer(${uid},${escHtml(JSON.stringify(e.nom))})">Retirer</button>`;
      if (e.planning && e.planning.length) {
        etat += `<div class="rh-dm-note" style="color:var(--danger)">Affecté au planning : ${e.planning.map(p => escHtml(p.semaine) + ' (' + p.jours.map(escHtml).join(', ') + ')').join(' ; ')}</div>`;
      }
    } else if (e.etat === 'deja_absent' && e.absence) {
      motifHtml = `<span class="rh-fm-mini">${escHtml(e.absence.libelle || e.absence.type_conge)} · ${fmtDateFull(e.absence.date_debut)} → ${fmtDateFull(e.absence.date_fin)}</span>`;
    } else if (e.etat === 'exclu' || e.etat === 'a_ajouter') {
      action = `<button class="rh-act-btn" onclick="prhFmAjuster(${uid},{inclus:true})">Poser le congé</button>`;
    }
    return `<tr>
      <td style="font-weight:600">${escHtml(e.nom)}${role}${e.inactif ? ' <span class="rh-fm-mini">inactif</span>' : ''}</td>
      <td>${etat}</td><td>${motifHtml}</td><td>${jours}</td><td>${restantHtml}</td><td style="white-space:nowrap">${action}</td>
    </tr>`;
  }).join('');
  const manquants = c.a_ajouter || 0;
  return `
    <button class="rh-act-btn" style="margin-bottom:10px" onclick="prhFmRetourListe()">← Fermetures</button>
    <h3>${escHtml(d.libelle)}</h3>
    <div class="rh-fm-resume">
      <span>${_prhFmPeriode(d)}</span><span>·</span><span>${_prhFmJours(d.nb_jours)}</span><span>·</span>
      <span>${escHtml(_prhFmMotifLibelle(d.type_conge))} par défaut</span>
    </div>
    ${d.note ? `<div class="rh-dm-note">${escHtml(d.note)}</div>` : ''}
    <div class="rh-dm-pills" style="margin:12px 0">${pastilles}</div>
    ${manquants ? `<div class="rh-fm-alerte">${manquants} employé(s) actif(s) sans congé sur cette fermeture (arrivés depuis, par exemple).
      <button class="rh-btn primary" onclick="prhFmAppliquer()">${icon('plus', 13)} Poser leurs congés</button></div>` : ''}
    <div class="rh-dm-scroll"><table class="rh-table">
      <thead><tr><th>Employé</th><th>État</th><th>Motif</th><th>Jours</th><th title="Solde CP restant sur l'année, fermeture comprise">CP restant</th><th></th></tr></thead>
      <tbody>${lignes || '<tr><td colspan="6" class="rh-empty">Aucun employé.</td></tr>'}</tbody>
    </table></div>
    <div class="rh-modal-acts">
      <button class="rh-btn danger" onclick="prhFmSupprimer()">${icon('trash', 13)} Supprimer</button>
      <button class="rh-btn secondary" onclick="prhFmModifier()">${icon('edit', 13)} Modifier</button>
    </div>`;
}

function buildFermeturesModal() {
  const fm = prhFmEtat();
  const ov = document.createElement('div'); ov.className = 'rh-modal-ov';
  ov.addEventListener('mousedown', e => { if (e.target === ov) prhFmFermer(); });
  const box = document.createElement('div'); box.className = 'rh-modal-box rh-fm-box';
  const corps = fm.form ? _prhFmFormHtml(fm) : fm.detail ? _prhFmDetailHtml(fm) : _prhFmListeHtml(fm);
  box.innerHTML = `<button class="rh-modal-close" onclick="prhFmFermer()">${icon('x', 16)}</button>` + corps;
  // Saisies libres : posées en propriété, jamais interpolées dans le HTML.
  if (fm.form) {
    const lib = box.querySelector('#prh-fm-lib');
    lib.value = fm.form.libelle || '';
    lib.addEventListener('input', () => { fm.form.libelle = lib.value; });
    const note = box.querySelector('#prh-fm-note');
    note.value = fm.form.note || '';
    note.addEventListener('input', () => { fm.form.note = note.value; });
  }
  ov.appendChild(box);
  return ov;
}
