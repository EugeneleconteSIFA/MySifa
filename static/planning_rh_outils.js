/*
 * MySifa — Planning RH : outils du responsable et vue employé sur ordinateur.
 *
 * Chargé AVANT le script principal de /planning-rh : il ne fait que déclarer
 * des fonctions. S, api(), render(), toast(), icon(), escHtml(), fmtDateFull(),
 * weekMonday(), addWeeks(), toLocalDateStr()… appartiennent au script principal.
 *
 *   - Générer : recopier une semaine sur les suivantes (rotation par machine) ;
 *   - Publication : semaine provisoire / publiée, notification des changements ;
 *   - Notes d'équipe : messages du responsable, affichés aux personnes visées ;
 *   - Équité : nuits, samedis, matins, après-midi par personne sur l'année ;
 *   - Vue employé sur ordinateur (au-delà de 900 px ; le téléphone garde la sienne).
 * API : app/routers/planning_rh_outils.py.
 */

const PRH_CRENEAUX = { matin: 'Matin', aprem: 'Après-midi', nuit: 'Nuit', journee: 'Journée' };

function prhOutEtat() {
  if (!S.out) S.out = { pubs: {}, notes: [], equite: null, gen: null, note: null, services: [] };
  return S.out;
}
function prhEstOperateur() { return !!S.user && !S.isEditor && !S.isReadOnlyAdmin; }

async function prhOutilsCharger(from, to) {
  const o = prhOutEtat();
  const [p, n] = await Promise.all([
    api('/publications?from_week=' + from + '&to_week=' + to).catch(() => null),
    api('/notes-equipe?from_week=' + from + '&to_week=' + to).catch(() => null),
  ]);
  o.pubs = {};
  ((p && p.semaines) || []).forEach(s => { o.pubs[s.semaine] = s; });
  o.notes = (n && n.notes) || [];
}

function prhNotesSemaine(ws) {
  return (prhOutEtat().notes || []).filter(n => n.semaine_debut <= ws && n.semaine_fin >= ws);
}
function prhSemCourt(ws) { return 'S' + String(ws).split('-W')[1]; }
function prhPlageSem(n) {
  return n.semaine_debut === n.semaine_fin ? prhSemCourt(n.semaine_debut) : prhSemCourt(n.semaine_debut) + ' → ' + prhSemCourt(n.semaine_fin);
}

// ── En-tête du planning (responsable) ─────────────────────────────
function prhOutilsBoutonsEntete() {
  if (!S.isEditor) return '';
  const aPublier = getWeeksToShow().filter(ws => {
    const p = prhOutEtat().pubs[ws];
    return p && (!p.version || (p.modifies || []).length);
  }).length;
  return `
    <button type="button" class="rh-icon-btn" onclick="prhOuvrirGenerer()" title="Recopier une semaine sur les suivantes">${icon('calendar', 13)} Générer</button>
    <button type="button" class="rh-icon-btn" onclick="prhOuvrirPublication()" title="Publier le planning aux équipes">${icon('mail', 13)} Publier${aPublier ? `<span class="rh-nav-count">${aPublier}</span>` : ''}</button>
    <button type="button" class="rh-icon-btn" onclick="prhOuvrirNote()" title="Note à l'attention d'une équipe">${icon('edit', 13)} Note</button>`;
}

// ── Bandeau des notes au-dessus de la grille ─────────────────────
function prhBandeauNotes(semaines) {
  const vues = new Set();
  const notes = [];
  semaines.forEach(ws => prhNotesSemaine(ws).forEach(n => { if (!vues.has(n.id)) { vues.add(n.id); notes.push(n); } }));
  if (!notes.length) return null;
  const el = document.createElement('div'); el.className = 'rh-notes-bandeau';
  notes.forEach(n => {
    const it = document.createElement('div'); it.className = 'rh-note' + (n.importance === 'important' ? ' important' : '');
    const meta = document.createElement('div'); meta.className = 'rh-note-meta';
    meta.textContent = prhPlageSem(n) + ' · ' + n.cible_libelle + (n.cree_par_nom ? ' · ' + n.cree_par_nom : '');
    const txt = document.createElement('div'); txt.className = 'rh-note-texte'; txt.textContent = n.texte;
    it.appendChild(meta); it.appendChild(txt);
    if (S.isEditor) {
      const acts = document.createElement('div'); acts.className = 'rh-note-acts';
      acts.innerHTML = `<button class="rh-act-btn" onclick="prhOuvrirNote(${n.id})">Modifier</button>
        <button class="rh-act-btn del" onclick="prhSupprimerNote(${n.id})">Retirer</button>`;
      it.appendChild(acts);
    }
    el.appendChild(it);
  });
  return el;
}

// ── Générer ───────────────────────────────────────────────────────
function prhOuvrirGenerer() {
  const ws = getWeeksToShow();
  prhOutEtat().gen = { source: ws[0], semaines: 4, apercu: null, enCours: false };
  S.modal = 'generer'; render();
}

async function prhGenerer(appliquer) {
  const g = prhOutEtat().gen; if (!g || g.enCours) return;
  g.enCours = true; render();
  try {
    const r = await api('/planning/generer', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: g.source, semaines: g.semaines, appliquer: !!appliquer }) });
    if (appliquer) {
      toast(r.creees.length + ' affectation(s) créée(s).', 'success');
      S.modal = null; prhOutEtat().gen = null;
      await loadData();
      return;
    }
    g.apercu = r;
  } catch (e) { toast(e.message, 'error'); }
  g.enCours = false; render();
}

function buildGenererModal() {
  const g = prhOutEtat().gen; if (!g) return null;
  const ov = prhOverlay();
  const box = document.createElement('div'); box.className = 'rh-modal-box'; box.style.maxWidth = '620px';
  const choix = [-2, -1, 0, 1, 2, 3].map(i => addWeeks(getWeeksToShow()[0], i));
  if (choix.indexOf(g.source) === -1) choix.unshift(g.source);
  let apercu = '';
  if (g.apercu) {
    const parSem = {};
    g.apercu.creees.forEach(c => { parSem[c.semaine] = (parSem[c.semaine] || 0) + 1; });
    apercu = `<div class="rh-gen-apercu">
      <div class="rh-gen-ligne"><strong>${g.apercu.creees.length}</strong> affectation(s) à créer :
        ${Object.keys(parSem).map(s => prhSemCourt(s) + ' (' + parSem[s] + ')').join(', ') || '—'}</div>
      ${g.apercu.creees.some(c => c.partiel) ? '<div class="rh-dm-aide">Jours de congé retirés pour : ' + escHtml([...new Set(g.apercu.creees.filter(c => c.partiel).map(c => c.nom + ' ' + prhSemCourt(c.semaine)))].join(', ')) + '</div>' : ''}
      ${g.apercu.ignorees.length ? '<div class="rh-gen-ignorees"><div class="rh-dm-aide">Non recopiés :</div>' + g.apercu.ignorees.map(i => '<div>' + escHtml(prhSemCourt(i.semaine) + ' · ' + i.nom + ' — ' + i.raison) + '</div>').join('') + '</div>' : ''}
    </div>`;
  }
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>Générer le planning</h3>
    <p class="rh-dm-aide" style="margin-bottom:12px">Recopie la semaine source sur les semaines suivantes. Sur les machines réglées en « alterné », matin et après-midi s'inversent une semaine sur deux. Les personnes déjà affectées ne sont pas touchées ; les congés validés sont retirés.</p>
    <div class="rh-dm-grid">
      <div class="rh-field"><label>Semaine source</label>
        <select onchange="prhOutEtat().gen.source=this.value;prhOutEtat().gen.apercu=null;render();">
          ${choix.map(s => `<option value="${s}"${s === g.source ? ' selected' : ''}>${fmtWeekLabel(s)}</option>`).join('')}</select></div>
      <div class="rh-field"><label>Semaines à remplir</label>
        <select onchange="prhOutEtat().gen.semaines=parseInt(this.value);prhOutEtat().gen.apercu=null;render();">
          ${[1, 2, 3, 4, 5, 6, 8].map(n => `<option value="${n}"${n === g.semaines ? ' selected' : ''}>${n} semaine${n > 1 ? 's' : ''}</option>`).join('')}</select></div>
    </div>
    ${apercu}
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="S.modal=null;render();">Annuler</button>
      ${g.apercu
        ? `<button class="rh-btn primary"${g.enCours || !g.apercu.creees.length ? ' disabled' : ''} onclick="prhGenerer(true)">${icon('check', 13)} Créer ${g.apercu.creees.length} affectation(s)</button>`
        : `<button class="rh-btn primary"${g.enCours ? ' disabled' : ''} onclick="prhGenerer(false)">Aperçu</button>`}
    </div>`;
  ov.appendChild(box);
  return ov;
}

// ── Publication ───────────────────────────────────────────────────
function prhOuvrirPublication() { S.modal = 'publication'; render(); }

async function prhPublier(ws) {
  try {
    const r = await api('/publications/' + ws, { method: 'POST' });
    toast(prhSemCourt(ws) + ' publiée · ' + r.prevenus.length + ' personne(s) prévenue(s).', 'success');
    const w = getWeeksToShow();
    await prhOutilsCharger(w[0], w[w.length - 1]);
  } catch (e) { toast(e.message, 'error'); }
  render();
}

function prhEtatPub(p) {
  if (!p || !p.version) return { cls: 'brouillon', txt: 'Provisoire' };
  if ((p.modifies || []).length) return { cls: 'modifie', txt: 'Modifié depuis publication' };
  return { cls: 'publie', txt: 'Publié le ' + fmtDateFull(p.publie_le) };
}

function buildPublicationModal() {
  const ov = prhOverlay();
  const box = document.createElement('div'); box.className = 'rh-modal-box'; box.style.maxWidth = '620px';
  const lignes = getWeeksToShow().map(ws => {
    const p = prhOutEtat().pubs[ws] || {};
    const e = prhEtatPub(p);
    const detail = p.version && (p.modifies || []).length
      ? 'Changé pour : ' + escHtml(p.modifies.join(', '))
      : (p.version ? 'Version ' + p.version + (p.publie_par ? ' · ' + escHtml(p.publie_par) : '') : (p.personnes || 0) + ' personne(s) affectée(s)');
    const aFaire = !p.version || (p.modifies || []).length;
    return `<tr>
      <td style="font-weight:600">${fmtWeekLabel(ws)}</td>
      <td><span class="rh-pub ${e.cls}">${e.txt}</span><div class="rh-dm-note">${detail}</div></td>
      <td style="text-align:right">${aFaire ? `<button class="rh-act-btn ok" onclick="prhPublier('${ws}')">${p.version ? 'Republier' : 'Publier'}</button>` : ''}</td>
    </tr>`;
  }).join('');
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>Publier le planning</h3>
    <p class="rh-dm-aide" style="margin-bottom:12px">Publier envoie une notification à chaque personne affectée. Une republication ne prévient que celles dont la semaine a changé. Les employés voient les semaines non publiées marquées « provisoire ».</p>
    <div class="rh-dm-scroll"><table class="rh-table"><tbody>${lignes}</tbody></table></div>
    <div class="rh-modal-acts"><button class="rh-btn secondary" onclick="S.modal=null;render();">Fermer</button></div>`;
  ov.appendChild(box);
  return ov;
}

// ── Notes d'équipe ────────────────────────────────────────────────
async function prhServices() {
  const o = prhOutEtat();
  if (o.services.length) return o.services;
  try { const d = await api('/absences-seuils'); o.services = (d && d.seuils) || []; } catch (e) {}
  return o.services;
}

async function prhOuvrirNote(id) {
  await prhServices();
  const n = id ? (prhOutEtat().notes || []).find(x => x.id === id) : null;
  const ws = getWeeksToShow()[0];
  prhOutEtat().note = n
    ? { id: n.id, texte: n.texte, semaine_debut: n.semaine_debut, semaine_fin: n.semaine_fin, cible_type: n.cible_type, cible_valeur: n.cible_valeur, importance: n.importance, prevenir: false }
    : { id: null, texte: '', semaine_debut: ws, semaine_fin: ws, cible_type: 'tous', cible_valeur: '', importance: 'info', prevenir: true };
  S.modal = 'note'; render();
}

function buildNoteModal() {
  const f = prhOutEtat().note; if (!f) return null;
  const ov = prhOverlay();
  const box = document.createElement('div'); box.className = 'rh-modal-box'; box.style.maxWidth = '560px';
  const sems = Array.from({ length: 12 }, (_, i) => addWeeks(getWeeksToShow()[0], i - 2));
  [f.semaine_debut, f.semaine_fin].forEach(s => { if (sems.indexOf(s) === -1) sems.push(s); });
  sems.sort();
  const optSem = sel => sems.map(s => `<option value="${s}"${s === sel ? ' selected' : ''}>${fmtWeekLabel(s)}</option>`).join('');
  const services = prhOutEtat().services.map(s => `<option value="${escHtml(s.service)}"${String(f.cible_valeur) === s.service ? ' selected' : ''}>${escHtml(s.libelle)}</option>`).join('');
  const machines = (S.machines || []).map(m => `<option value="${m.id}"${String(f.cible_valeur) === String(m.id) ? ' selected' : ''}>${escHtml(m.nom)}</option>`).join('');
  box.innerHTML = `
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x', 16)}</button>
    <h3>${f.id ? 'Modifier la note' : "Note à l'attention d'une équipe"}</h3>
    <div class="rh-field"><label>Message *</label>
      <textarea id="prh-note-texte" rows="3" maxlength="500" placeholder="Ex. : beaucoup de préparation en logistique cette semaine, merci de faire preuve d'adaptabilité."></textarea></div>
    <div class="rh-field"><label>Destinataires</label>
      <div class="rh-dm-pills">
        ${[['tous', 'Tout le monde'], ['service', 'Un service'], ['machine', 'Une machine']].map(([k, v]) =>
          `<button type="button" class="rh-dm-pill${f.cible_type === k ? ' active' : ''}" onclick="prhNoteChamp('cible_type','${k}')">${v}</button>`).join('')}
      </div></div>
    ${f.cible_type === 'service' ? `<div class="rh-field"><label>Service</label><select onchange="prhNoteChamp('cible_valeur',this.value,true)"><option value="">Choisir…</option>${services}</select></div>` : ''}
    ${f.cible_type === 'machine' ? `<div class="rh-field"><label>Machine</label><select onchange="prhNoteChamp('cible_valeur',this.value,true)"><option value="">Choisir…</option>${machines}</select>
      <small class="rh-dm-aide">Visible des personnes affectées à cette machine sur la période.</small></div>` : ''}
    <div class="rh-dm-grid">
      <div class="rh-field"><label>Du</label><select onchange="prhNoteChamp('semaine_debut',this.value)">${optSem(f.semaine_debut)}</select></div>
      <div class="rh-field"><label>Au</label><select onchange="prhNoteChamp('semaine_fin',this.value)">${optSem(f.semaine_fin)}</select></div>
    </div>
    <div class="rh-field">
      <label class="rh-dm-check"><input type="checkbox"${f.importance === 'important' ? ' checked' : ''} onchange="prhNoteChamp('importance',this.checked?'important':'info',true)"> Important (mis en avant)</label>
      ${f.id ? '' : `<label class="rh-dm-check"><input type="checkbox"${f.prevenir ? ' checked' : ''} onchange="prhNoteChamp('prevenir',this.checked,true)"> Envoyer une notification aux personnes concernées</label>`}
    </div>
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="S.modal=null;render();">Annuler</button>
      <button class="rh-btn primary" onclick="prhEnregistrerNote()">${icon('check', 13)} ${f.id ? 'Enregistrer' : 'Publier la note'}</button>
    </div>`;
  const t = box.querySelector('#prh-note-texte');
  t.value = f.texte || '';
  t.addEventListener('input', () => { f.texte = t.value; });
  ov.appendChild(box);
  return ov;
}

function prhNoteChamp(cle, v, sansRendu) {
  const f = prhOutEtat().note; if (!f) return;
  f[cle] = v;
  if (cle === 'cible_type') f.cible_valeur = '';
  if (cle === 'semaine_debut' && f.semaine_fin < v) f.semaine_fin = v;
  if (!sansRendu) render();
}

async function prhEnregistrerNote() {
  const f = prhOutEtat().note; if (!f) return;
  if (!String(f.texte || '').trim()) { toast('Message obligatoire.', 'error'); return; }
  if (f.cible_type !== 'tous' && !f.cible_valeur) { toast('Choisissez les destinataires.', 'error'); return; }
  try {
    const corps = JSON.stringify(f);
    const r = f.id
      ? await api('/notes-equipe/' + f.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: corps })
      : await api('/notes-equipe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: corps });
    toast(f.id ? 'Note modifiée.' : ('Note publiée' + (r.prevenus ? ' · ' + r.prevenus + ' personne(s) prévenue(s)' : '') + '.'), 'success');
    S.modal = null; prhOutEtat().note = null;
    const w = getWeeksToShow(); await prhOutilsCharger(w[0], w[w.length - 1]);
  } catch (e) { toast(e.message, 'error'); }
  render();
}

async function prhSupprimerNote(id) {
  if (!confirm('Retirer cette note ?')) return;
  try {
    await api('/notes-equipe/' + id, { method: 'DELETE' });
    prhOutEtat().notes = prhOutEtat().notes.filter(n => n.id !== id);
    toast('Note retirée.', 'success');
  } catch (e) { toast(e.message, 'error'); }
  render();
}

// ── Équité ────────────────────────────────────────────────────────
async function prhChargerEquite() {
  const o = prhOutEtat();
  o.equiteEnCours = true;
  try { o.equite = await api('/equite?annee=' + S.annee); } catch (e) { o.equite = { personnes: [] }; toast(e.message, 'error'); }
  o.equiteEnCours = false;
  render();
}

function buildEquiteTab() {
  const o = prhOutEtat();
  const wrap = document.createElement('div'); wrap.className = 'rh-conges-wrap';
  if (!o.equite || o.equite.annee !== S.annee) {
    if (!o.equiteEnCours) prhChargerEquite();
    wrap.innerHTML = '<div class="rh-loading"><div class="rh-spinner"></div> Chargement…</div>';
    return wrap;
  }
  const ps = o.equite.personnes || [];
  const cols = [['semaines', 'Semaines'], ['matin', 'Matin'], ['aprem', 'Après-midi'], ['nuit', 'Nuit'], ['journee', 'Journée'], ['samedis', 'Samedis'], ['total', 'Total jours']];
  const moy = {};
  cols.forEach(([k]) => { const v = ps.filter(p => p[k] > 0 || k === 'total'); moy[k] = v.length ? v.reduce((a, p) => a + p[k], 0) / v.length : 0; });
  const max = {}; cols.forEach(([k]) => { max[k] = Math.max(1, ...ps.map(p => p[k])); });
  const sec = document.createElement('div'); sec.className = 'rh-section';
  sec.innerHTML = `
    <div class="rh-section-hdr"><span class="rh-section-title">${icon('users', 13)} Répartition ${S.annee}</span></div>
    <p class="rh-dm-aide" style="padding:10px 16px 0">Jours planifiés par créneau, semaines passées et à venir. En couleur : nuits et samedis au-delà d'un quart de la moyenne de ceux qui en font.</p>
    <div class="rh-dm-scroll"><table class="rh-table rh-equite">
      <thead><tr><th>Employé</th>${cols.map(([, l]) => `<th>${l}</th>`).join('')}</tr></thead>
      <tbody>${ps.length ? ps.map(p => `<tr><td style="font-weight:600">${escHtml(p.nom)}</td>${cols.map(([k]) => {
        const haut = (k === 'nuit' || k === 'samedis') && p[k] > 0 && p[k] > moy[k] * 1.25;
        return `<td><div class="rh-eq-cell${haut ? ' haut' : ''}"><span>${p[k]}</span><i style="width:${Math.round(p[k] / max[k] * 100)}%"></i></div></td>`;
      }).join('')}</tr>`).join('') : `<tr><td colspan="${cols.length + 1}" class="rh-empty">Aucune affectation en ${S.annee}.</td></tr>`}</tbody>
      ${ps.length ? `<tfoot><tr><td>Moyenne</td>${cols.map(([k]) => `<td>${(Math.round(moy[k] * 10) / 10).toString().replace('.', ',')}</td>`).join('')}</tr></tfoot>` : ''}
    </table></div>`;
  wrap.appendChild(sec);
  return wrap;
}

// ── Vue employé sur ordinateur ────────────────────────────────────
function prhHorairesCreneau(machineId, creneau) {
  const c = (S.machineConfigs || []).find(x => String(x.machine_id) === String(machineId));
  if (!c || !['matin', 'aprem', 'nuit'].includes(creneau)) return '';
  return (c[creneau + '_debut'] || '') + '–' + (c[creneau + '_fin'] || '');
}

function prhVueEmployeBureau() {
  const wrap = document.createElement('div'); wrap.className = 'rh-emp';
  const base = addWeeks(weekStr(new Date()), S.opOffset);
  const weeks = Array.from({ length: S.opViewRange }, (_, i) => addWeeks(base, i));
  const uid = S.user.id;

  // Barre : navigation + horizon + raccourcis
  const barre = document.createElement('div'); barre.className = 'rh-emp-barre';
  barre.innerHTML = `
    <div class="rh-wk-nav">
      <button type="button" onclick="S.opOffset-=S.opViewRange;loadData();" title="Précédent">${icon('chevron_left', 14)}</button>
      <button type="button" class="rh-wk-today" onclick="S.opOffset=0;loadData();">Aujourd'hui</button>
      <button type="button" onclick="S.opOffset+=S.opViewRange;loadData();" title="Suivant">${icon('chevron_right', 14)}</button>
    </div>
    <div class="rh-emp-titre">${weeks.length === 1 ? fmtWeekLong(weeks[0]) : fmtWeekLabel(weeks[0]) + ' → ' + fmtWeekLabel(weeks[weeks.length - 1])}</div>
    <div class="rh-range-tabs">${rhDesktopRangeOpts().map(n => `<button type="button" class="rh-range-tab${S.opViewRange === n ? ' active' : ''}" onclick="S.opViewRange=${n};loadData();">${n} sem.</button>`).join('')}</div>
    <button type="button" class="rh-icon-btn" onclick="setTab('demandes');prhOuvrirDemande()">${icon('plus', 13)} Faire une demande</button>`;
  wrap.appendChild(barre);

  // Notes de la période, une fois chacune
  const notes = prhBandeauNotes(weeks);
  if (notes) wrap.appendChild(notes);

  const grille = document.createElement('div'); grille.className = 'rh-emp-semaines';
  grille.style.gridTemplateColumns = `repeat(${Math.min(weeks.length, 2)}, minmax(0, 1fr))`;
  weeks.forEach(ws => grille.appendChild(prhCarteSemaine(ws, uid)));
  wrap.appendChild(grille);
  return wrap;
}

function prhCarteSemaine(ws, uid) {
  const carte = document.createElement('div'); carte.className = 'rh-emp-carte' + (isCurrentWeek(ws) ? ' courante' : '');
  const lun = weekMonday(ws);
  const plans = S.planning.filter(p => p.user_id === uid && p.semaine === ws);
  const congeBits = congeJoursBitmask(uid, ws);
  const conges = userCongesThisWeek(uid, ws);
  const horaires = typeof prhHorairesSemaine === 'function' ? prhHorairesSemaine(uid, ws) : [];
  const pub = prhOutEtat().pubs[ws];
  const etat = pub && pub.version ? { cls: 'publie', txt: 'Publié' } : { cls: 'brouillon', txt: 'Provisoire' };
  const maint = (S.myMaintenance || []);

  const tete = document.createElement('div'); tete.className = 'rh-emp-tete';
  tete.innerHTML = `<div><div class="rh-emp-sem">Semaine ${ws.split('-W')[1]}${isCurrentWeek(ws) ? ' <span class="rh-emp-cette">cette semaine</span>' : ''}</div>
    <div class="rh-dm-aide">${fmtDateShort(lun)} – ${fmtDateShort(new Date(lun.getTime() + 5 * 86400000))}</div></div>
    ${plans.length ? `<span class="rh-pub ${etat.cls}" title="${etat.cls === 'brouillon' ? 'Le planning de cette semaine peut encore changer' : ''}">${etat.txt}</span>` : ''}`;
  carte.appendChild(tete);

  // Résumé du poste
  if (plans.length) {
    const res = document.createElement('div'); res.className = 'rh-emp-postes';
    plans.forEach(p => {
      const l = document.createElement('div'); l.className = 'rh-emp-poste';
      const h = prhHorairesCreneau(p.machine_id, p.creneau);
      l.innerHTML = `<span class="rh-emp-creneau c-${escHtml(p.creneau)}">${escHtml(PRH_CRENEAUX[p.creneau] || p.creneau)}</span>
        <span class="rh-emp-machine">${escHtml(p.machine_nom || POSTE_LABELS[p.poste] || '')}</span>
        <span class="rh-dm-aide">${escHtml(POSTE_LABELS[p.poste] || p.poste)}${h ? ' · ' + h : ''}</span>`;
      res.appendChild(l);
    });
    carte.appendChild(res);
  }

  // Bande des jours
  const jours = document.createElement('div'); jours.className = 'rh-emp-jours';
  for (let i = 0; i < 6; i++) {
    const d = new Date(lun); d.setDate(lun.getDate() + i);
    const iso = toLocalDateStr(d);
    const p = plans.find(x => ((x.jours !== undefined ? x.jours : 31) >> i) & 1);
    const enConge = (congeBits >> i) & 1;
    const hz = horaires.find(h => h.date_debut <= iso && h.date_fin >= iso);
    const mt = maint.filter(m => m.date_prevue === iso);
    if (i === 5 && !p && !enConge && !mt.length) continue;
    const c = document.createElement('div');
    const aujourdhui = iso === toLocalDateStr(new Date());
    let corps;
    if (enConge) {
      const cg = conges.find(x => x.date_debut <= iso && x.date_fin >= iso);
      corps = `<span class="rh-emp-etat conge">${escHtml((cg && (TYPE_CONGE_LABELS[cg.type_conge] || cg.type_conge)) || 'Absent')}</span>`;
      c.className = 'rh-emp-jour conge';
    } else if (p) {
      const h = hz ? hz.heure_debut + '–' + hz.heure_fin : prhHorairesCreneau(p.machine_id, p.creneau);
      corps = `<span class="rh-emp-etat c-${escHtml(p.creneau)}">${escHtml(PRH_CRENEAUX[p.creneau] || p.creneau)}</span>
        ${h ? `<span class="rh-emp-heures${hz ? ' amenage' : ''}" title="${hz ? 'Horaire aménagé' : ''}">${escHtml(h)}</span>` : ''}`;
      c.className = 'rh-emp-jour travaille';
    } else {
      corps = '<span class="rh-emp-etat repos">—</span>';
      c.className = 'rh-emp-jour repos';
    }
    if (aujourdhui) c.className += ' aujourdhui';
    c.innerHTML = `<div class="rh-emp-jlib">${JOURS_LABELS[i]} <b>${d.getDate()}</b></div>${corps}`;
    mt.forEach(m => {
      const b = document.createElement('button'); b.className = 'rh-emp-maint'; b.type = 'button';
      b.innerHTML = icon('wrench', 11) + ' ' + escHtml(m.heure_debut || 'Maintenance');
      b.onclick = () => openMyMaintDetail(m.id);
      c.appendChild(b);
    });
    jours.appendChild(c);
  }
  // Une seule ligne de jours, quelle que soit la largeur de la carte.
  jours.style.gridTemplateColumns = `repeat(${jours.children.length}, minmax(0, 1fr))`;
  carte.appendChild(jours);

  if (!plans.length && !congeBits) {
    const vide = document.createElement('div'); vide.className = 'rh-emp-vide';
    vide.textContent = 'Pas encore d\'affectation cette semaine.';
    carte.appendChild(vide);
  }
  return carte;
}

function prhOverlay() {
  const ov = document.createElement('div'); ov.className = 'rh-modal-ov';
  ov.addEventListener('mousedown', e => { if (e.target === ov) { S.modal = null; render(); } });
  return ov;
}
