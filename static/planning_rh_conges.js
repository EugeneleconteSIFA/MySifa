/*
 * MySifa — Planning RH : formulaire de congé et calendrier des absences.
 *
 * Formulaire (onglet Congés) : les dates font foi. Le nombre de jours est
 * celui des jours ouvrés de la période (fériés retirés, PRH_FERIES), ajustable
 * seulement pour une demi-journée. Un motif qui ne se décompte pas des CP
 * (absence justifiée : événement familial, formation…) demande en plus la part
 * retirée du solde CP (`jours_cp`, 0 par défaut).
 *
 * Calendrier : un mois, une ligne par employé, une case par jour. Couleur selon
 * le solde du motif (CP, RTT, absence justifiée), posé non validé en hachuré,
 * week-ends et fériés grisés ; en pied, le nombre d'absents par jour.
 * Adresse : `affichage=calendrier`, `mois=AAAA-MM`, `absents=1`
 * (planning_rh_url.js).
 *
 * Chargé avant le script principal : S, render(), escHtml(), icon(),
 * prhMotifsOptions(), TYPE_CONGE_LABELS ne sont lus qu'à l'appel.
 */

// ── Commun ─────────────────────────────────────────────────────────
function prhMotifDecompte(code) {
  const m = ((S.dm && S.dm.motifs) || []).find(x => x.code === code);
  if (m) return m.decompte || 'aucun';
  return code === 'CP' ? 'cp' : code === 'RTT' ? 'rtt' : 'aucun';
}

function prhJourIso(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function prhJourOuvre(iso) {
  const j = new Date(iso + 'T00:00:00').getDay();
  return j !== 0 && j !== 6 && !((window.PRH_FERIES || {})[iso]);
}

function prhJoursFmt(n) {
  const v = parseFloat(n);
  return isNaN(v) ? '—' : String(v).replace('.', ',');
}

// ── Formulaire de congé ────────────────────────────────────────────
function prhCongeFormVide() {
  return { user_id: '', date_debut: '', date_fin: '', nb_jours: '', nb_manuel: false,
    type_conge: 'CP', jours_cp: '', note: '' };
}

// Formulaire rempli depuis un congé existant (modification).
function prhCongeFormDepuis(c) {
  const ouvres = prhJoursOuvres(c.date_debut, c.date_fin);
  const nb = parseFloat(c.nb_jours);
  return { user_id: c.user_id, date_debut: c.date_debut, date_fin: c.date_fin,
    nb_jours: c.nb_jours, nb_manuel: ouvres == null || nb !== ouvres,
    type_conge: c.type_conge, jours_cp: c.jours_cp == null ? '' : c.jours_cp, note: c.note || '' };
}

function prhCongeChamp(cle, val) {
  const f = S.congeForm;
  if (cle === 'nb_manuel' && val) f.nb_jours = prhJoursOuvres(f.date_debut, f.date_fin) || '';
  f[cle] = val;
  if (cle === 'date_debut' && (!f.date_fin || f.date_fin < val)) f.date_fin = val;
  if (['date_debut', 'date_fin', 'type_conge', 'nb_manuel'].includes(cle)) render();
}

// Corps envoyé à l'API : sans ajustement, le serveur compte les jours ouvrés.
function prhCongeCorps() {
  const f = S.congeForm;
  const corps = { user_id: f.user_id, date_debut: f.date_debut, date_fin: f.date_fin,
    type_conge: f.type_conge, note: f.note, nb_jours: f.nb_manuel ? f.nb_jours : '' };
  if (prhMotifDecompte(f.type_conge) !== 'cp') corps.jours_cp = f.jours_cp === '' ? 0 : f.jours_cp;
  return corps;
}

function prhCongeFormHtml() {
  const f = S.congeForm;
  const optionsMotifHtml = prhMotifsOptions(f.type_conge || 'CP');   // déjà échappées
  const personnesHtml = S.personnel.map(p => `<option value="${Number(p.id)}"${f.user_id == p.id ? ' selected' : ''}>${S.view === 'rh' && p.role ? '[' + escHtml(p.role) + '] ' : ''}${escHtml(p.nom)}</option>`).join('');
  const ouvres = prhJoursOuvres(f.date_debut, f.date_fin);
  const dec = prhMotifDecompte(f.type_conge);
  const joursHtml = f.nb_manuel
    ? `<div class="rh-cg-jours">
         <input type="number" min="0.5" step="0.5" value="${escHtml(String(f.nb_jours))}" onchange="prhCongeChamp('nb_jours',this.value)">
         <button type="button" class="rh-cg-lien" onclick="prhCongeChamp('nb_manuel',false)" title="Revenir aux jours ouvrés de la période">Recalculer</button>
       </div>`
    : `<div class="rh-cg-jours">
         <span><strong>${ouvres == null ? '—' : ouvres}</strong> jour${ouvres > 1 ? 's' : ''} ouvré${ouvres > 1 ? 's' : ''}</span>
         <button type="button" class="rh-cg-lien" onclick="prhCongeChamp('nb_manuel',true)" title="Demi-journée ou cas particulier">Ajuster</button>
       </div>`;
  const decompteLib = dec === 'cp' ? 'Décompté des CP' : dec === 'rtt' ? 'Décompté des RTT' : 'Absence justifiée';
  const cpHtml = dec === 'cp' || dec === 'rtt' ? '' : `
        <div class="rh-field" style="margin:0">
          <label>Dont jours décomptés des CP</label>
          <input type="number" min="0" step="0.5" value="${escHtml(String(f.jours_cp))}" placeholder="0"
            onchange="S.congeForm.jours_cp=this.value">
        </div>
        <div class="rh-dm-aide rh-cg-aide">Part de l'absence retirée du solde CP. 0 si le motif couvre toute l'absence.</div>`;
  return `
      <div class="rh-cg-grid">
        <div class="rh-field" style="margin:0">
          <label>Employé *</label>
          <select onchange="S.congeForm.user_id=this.value">
            <option value="">Sélectionner…</option>${personnesHtml}
          </select>
        </div>
        <div class="rh-field" style="margin:0">
          <label>Motif <span class="rh-cg-tag">${decompteLib}</span></label>
          <select onchange="prhCongeChamp('type_conge',this.value)">${optionsMotifHtml}</select>
        </div>
        <div class="rh-field" style="margin:0">
          <label>Note</label>
          <input type="text" id="prh-cg-note" maxlength="200" placeholder="Optionnel">
        </div>
        <div class="rh-field" style="margin:0">
          <label>Du *</label>
          <input type="date" value="${escHtml(f.date_debut)}" onchange="prhCongeChamp('date_debut',this.value)">
        </div>
        <div class="rh-field" style="margin:0">
          <label>Au *</label>
          <input type="date" value="${escHtml(f.date_fin)}" onchange="prhCongeChamp('date_fin',this.value)">
        </div>
        <div class="rh-field" style="margin:0">
          <label>Jours</label>${joursHtml}
        </div>${cpHtml}
      </div>`;
}

// La note est une saisie libre : posée en propriété après le rendu.
function prhCongeFormBrancher(racine) {
  const note = racine.querySelector('#prh-cg-note');
  if (!note) return;
  note.value = S.congeForm.note || '';
  note.addEventListener('input', () => { S.congeForm.note = note.value; });
}

// Cellule « Jours » de la liste.
function prhCongeJoursHtml(c) {
  let h = `<strong>${prhJoursFmt(c.nb_jours)}j</strong>`;
  const jcp = parseFloat(c.jours_cp);
  if (prhMotifDecompte(c.type_conge) !== 'cp' && jcp > 0) {
    h += ` <span class="rh-cg-dont" title="Part retirée du solde CP">dont ${prhJoursFmt(jcp)} CP</span>`;
  }
  return h;
}

// ── Affichage liste / calendrier ───────────────────────────────────
function prhCongesAffichage(v) { S.congesAffichage = v === 'calendrier' ? 'calendrier' : 'liste'; render(); }

function prhCalMoisCourant() { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); }

function prhCalMois(decalage) {
  if (decalage === 0) { S.congesMois = prhCalMoisCourant(); render(); return; }
  const [a, m] = (S.congesMois || prhCalMoisCourant()).split('-').map(Number);
  const d = new Date(a, m - 1 + decalage, 1);
  S.congesMois = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  render();
}

function prhCalAbsents(v) { S.congesCalAbsents = !!v; render(); }

function prhCongesBasculeHtml() {
  const cal = S.congesAffichage === 'calendrier';
  return `<div class="rh-dm-pills">
      <button type="button" class="rh-dm-pill${cal ? '' : ' active'}" onclick="prhCongesAffichage('liste')">Liste</button>
      <button type="button" class="rh-dm-pill${cal ? ' active' : ''}" onclick="prhCongesAffichage('calendrier')">${icon('calendar', 12)} Calendrier</button>
    </div>`;
}

const PRH_CAL_MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
  'septembre', 'octobre', 'novembre', 'décembre'];
const PRH_CAL_JOURS = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];
const PRH_CAL_CLASSES = { cp: 'cp', rtt: 'rtt', aucun: 'abs' };

function prhCalendrierHtml() {
  const moisIso = S.congesMois || prhCalMoisCourant();
  const [a, m] = moisIso.split('-').map(Number);
  const nbJours = new Date(a, m, 0).getDate();
  const jours = [];
  for (let i = 1; i <= nbJours; i++) {
    const d = new Date(a, m - 1, i);
    const iso = prhJourIso(d);
    jours.push({ iso, n: i, lettre: PRH_CAL_JOURS[d.getDay()], ouvre: prhJourOuvre(iso), ferie: (window.PRH_FERIES || {})[iso] || '' });
  }
  const debut = jours[0].iso, fin = jours[nbJours - 1].iso, auj = prhJourIso(new Date());

  // Congés du mois par employé et par jour (un refus n'est pas une absence).
  const parUser = {};
  (S.conges || []).forEach(c => {
    if (c.statut === 'refuse' || c.date_fin < debut || c.date_debut > fin) return;
    const u = parUser[c.user_id] || (parUser[c.user_id] = {});
    jours.forEach(j => { if (j.iso >= c.date_debut && j.iso <= c.date_fin) u[j.iso] = c; });
  });
  let personnes = (S.personnel || []).slice().sort((x, y) => String(x.nom).localeCompare(String(y.nom), 'fr'));
  if (S.congesCalAbsents) personnes = personnes.filter(p => parUser[p.id]);
  const absentsParJour = jours.map(() => 0);

  const lignes = personnes.map(p => {
    const u = parUser[p.id] || {};
    let total = 0;
    const cases = jours.map((j, k) => {
      const c = u[j.iso];
      const cls = ['rh-cal-c'];
      if (!j.ouvre) cls.push('off');
      if (j.iso === auj) cls.push('auj');
      let attr = j.ferie ? ` title="${escHtml(j.ferie)}"` : '';
      if (c && j.ouvre) {
        cls.push('on', PRH_CAL_CLASSES[prhMotifDecompte(c.type_conge)] || 'abs');
        if (c.statut === 'pose') cls.push('pose');
        total += 1; absentsParJour[k] += 1;
        const lib = TYPE_CONGE_LABELS[c.type_conge] || c.type_conge;
        const jcp = parseFloat(c.jours_cp);
        const dont = prhMotifDecompte(c.type_conge) !== 'cp' && jcp > 0 ? ` (dont ${prhJoursFmt(jcp)} CP)` : '';
        const titre = `${p.nom} · ${lib} · ${fmtDateFull(c.date_debut)} → ${fmtDateFull(c.date_fin)} · ${prhJoursFmt(c.nb_jours)} j${dont}${c.statut === 'pose' ? ' · posé, non validé' : ''}`;
        attr = ` title="${escHtml(titre)}"`;
        if (S.isEditor) attr += ` onclick="editConge(${Number(c.id)})"`;
      }
      return `<td class="${cls.join(' ')}"${attr}></td>`;
    }).join('');
    return `<tr><th class="rh-cal-nom" scope="row">${escHtml(p.nom)}</th>${cases}<td class="rh-cal-tot">${total || ''}</td></tr>`;
  }).join('');

  const entete = jours.map(j => `<th class="rh-cal-j${j.ouvre ? '' : ' off'}${j.iso === auj ? ' auj' : ''}"${j.ferie ? ` title="${escHtml(j.ferie)}"` : ''}><span>${j.lettre}</span>${j.n}</th>`).join('');
  const pied = jours.map((j, k) => `<td class="rh-cal-pied${j.ouvre ? '' : ' off'}">${j.ouvre && absentsParJour[k] ? absentsParJour[k] : ''}</td>`).join('');
  const vide = `<tr><td colspan="${nbJours + 2}" class="rh-empty">${S.congesCalAbsents ? 'Aucune absence ce mois-ci.' : 'Aucun employé.'}</td></tr>`;

  return `
    <div class="rh-cal-barre">
      <div class="rh-cal-nav">
        <button type="button" class="rh-icon-btn" onclick="prhCalMois(-1)" aria-label="Mois précédent">‹</button>
        <span class="rh-cal-titre">${PRH_CAL_MOIS[m - 1]} ${a}</span>
        <button type="button" class="rh-icon-btn" onclick="prhCalMois(1)" aria-label="Mois suivant">›</button>
        ${moisIso !== prhCalMoisCourant() ? '<button type="button" class="rh-icon-btn" onclick="prhCalMois(0)">Ce mois-ci</button>' : ''}
      </div>
      <label class="rh-dm-check rh-cal-filtre"><input type="checkbox"${S.congesCalAbsents ? ' checked' : ''} onchange="prhCalAbsents(this.checked)"> Seulement les absents</label>
      <div class="rh-cal-legende">
        <span><i class="rh-cal-c on cp"></i>CP</span>
        <span><i class="rh-cal-c on rtt"></i>RTT</span>
        <span><i class="rh-cal-c on abs"></i>Absence justifiée</span>
        <span><i class="rh-cal-c on cp pose"></i>Posé, non validé</span>
      </div>
    </div>
    <div class="rh-cal-scroll"><table class="rh-cal">
      <thead><tr><th class="rh-cal-nom"></th>${entete}<th class="rh-cal-tot" title="Jours d'absence ouvrés dans le mois">Jours</th></tr></thead>
      <tbody>${lignes || vide}</tbody>
      ${lignes ? `<tfoot><tr><th class="rh-cal-nom" scope="row">Absents</th>${pied}<td class="rh-cal-tot"></td></tr></tfoot>` : ''}
    </table></div>`;
}
