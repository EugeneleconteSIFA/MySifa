/**
 * mysifa_alert_form.js — Formulaire d'édition d'alerte maintenance (module partagé).
 *
 * Source de vérité unique du formulaire, utilisé par :
 *   - /settings   → app/web/settings_page.py
 *   - /maintenance → app/web/maintenance_page.py
 *
 * Avant ce module (jusqu'à v2.4.13), le formulaire était dupliqué dans les 2
 * fichiers Python — chaque évolution devait être portée à la main dans les
 * deux copies. Plusieurs divergences se sont produites (v2.3.28, v2.3.45,
 * merge myao v2.4.12, libellé bouton v2.4.13). L'extraction ici élimine
 * définitivement la classe de bug.
 *
 * Dépendances runtime attendues (fournies par la page hôte) :
 *   - window.esc(s), window.escAttr(s), window.escHtml(s)
 *   - window.toast(msg, isErr)
 *   - window.document
 *
 * Toutes les fonctions internes sont ré-exposées sur window.* pour que les
 * onclick="_afOnTypeChange(this)" inline continuent à fonctionner.
 */
(function () {
  'use strict';
  if (window.MysifaAlertForm) return;

  // Fallbacks défensifs si la page hôte ne fournit pas esc/escAttr/escHtml/toast
  var esc     = window.esc     || function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var escAttr = window.escAttr || function (s) { return esc(s).replace(/"/g, '&quot;'); };
  var escHtml = window.escHtml || esc;
  var toast   = window.toast   || function (m, err) { if (window.console) window.console.log('[alert-form]', m, err ? 'ERROR' : ''); };

  // ── _ALERT_TRIGGER_TYPES ──
  // v2.5.6 : « Manuel » retiré. Il ne déclenchait rien (jamais évalué par
  // /alerts/active) — une alerte réglée dessus restait invisible pour
  // l'opérateur. Les alertes historiques qui le portent encore en base ne
  // sont PAS migrées : le select réaffiche l'option uniquement pour
  // celles-là (via _triggerOptsFor), avec un bandeau d'avertissement, pour
  // qu'aucune alerte dormante ne se mette à sonner par accident au save.
  var _ALERT_TRIGGER_TYPES = [
  { v: 'periodic', l: 'Périodique — toutes les X minutes, en production' },
  { v: 'calendar', l: 'Calendaire — à heure fixe' },
  { v: 'event',    l: 'Événementiel — sur action métier' },
];

  var _ALERT_TRIGGER_TYPE_LEGACY = { v: 'manual', l: 'Manuel — obsolète, ne déclenche rien' };

  function _isLegacyTriggerType(t) { return t === 'manual'; }

  // Construit les <option> du select : les types courants, plus l'option
  // obsolète en tête si (et seulement si) l'alerte ouverte l'utilise encore.
  function _triggerOptsFor(currentType) {
    var list = _ALERT_TRIGGER_TYPES.slice();
    if (_isLegacyTriggerType(currentType)) list.unshift(_ALERT_TRIGGER_TYPE_LEGACY);
    return list.map(function (t) {
      return '<option value="' + t.v + '"' + (t.v === currentType ? ' selected' : '') + '>' + esc(t.l) + '</option>';
    }).join('');
  }

  // ── _ALERT_TRIGGER_EVENTS ──
  var _ALERT_TRIGGER_EVENTS = [
  { v: 'dossier_start',  l: 'Début de dossier' },
  { v: 'dossier_end',    l: 'Fin de dossier' },
  // v2.3.28 : after_calage manquait — le select forcait tout return à
  // 'dossier_start' au save via /maintenance (les alertes réglées sur
  // 'après calage' basculaient silencieusement à 'début de dossier').
  { v: 'after_calage',   l: 'Après calage (fin de calage → reprise prod)' },
];

  // ── _ALERT_MACHINES ──
  var _ALERT_MACHINES = ['*', 'Cohésio 1', 'Cohésio 2', 'DSI', 'Repiquage'];

  // ── _ALERT_ROLES ──
  var _ALERT_ROLES = ['*', 'fabrication', 'logistique', 'expedition', 'comptabilite', 'commercial', 'administration', 'administration_ventes', 'administration_technique', 'direction', 'superadmin'];

  // ── _ALERT_DAYS ──
  var _ALERT_DAYS = [
  { v: 'mon', l: 'Lun' }, { v: 'tue', l: 'Mar' }, { v: 'wed', l: 'Mer' },
  { v: 'thu', l: 'Jeu' }, { v: 'fri', l: 'Ven' }, { v: 'sat', l: 'Sam' }, { v: 'sun', l: 'Dim' },
];


  // ── _alertDefaults ──
  function _alertDefaults(existing) {
  const p = existing || {};
  const trig = Object.assign({}, p.trigger || {});
  // Compat rétro : si seul interval_hours est présent, on convertit en minutes.
  if (trig.interval_minutes == null && trig.interval_hours != null) {
    trig.interval_minutes = Math.round(Number(trig.interval_hours) * 60);
    delete trig.interval_hours;
  }
  // Target : nouveau format = { machines: [...] }. Compat avec ancien { machine, role }.
  const rawTarget = p.target || {};
  let machines = rawTarget.machines;
  if (!Array.isArray(machines)) {
    if (typeof rawTarget.machine === 'string' && rawTarget.machine) {
      machines = [rawTarget.machine];
    } else {
      machines = ['*'];
    }
  }
  // Checklist : normalisation des items pour inclure le champ type (choice/value)
  // et la conversion des anciens items "string" en objets.
  const cl = Object.assign({ enabled: false, items: [] }, p.checklist || {});
  if (!Array.isArray(cl.items)) cl.items = [];
  cl.items = cl.items.map(it => {
    if (typeof it === 'string') {
      return { type: 'choice', label: it, responses: ['Conforme'] };
    }
    const t = (it && it.type) || 'choice';
    if (t === 'value') {
      return {
        type: 'value',
        label: (it && it.label) || '',
        unit: (it && it.unit) || '',
        min: (it && it.min != null && it.min !== '') ? Number(it.min) : null,
        max: (it && it.max != null && it.max !== '') ? Number(it.max) : null,
        // v2.3.45 : préserver required (v2.2.86 dans settings_page — oublié ici)
        required: !!(it && it.required),
        // Plusieurs mesures (ex. début / milieu / fin de prod) : un libellé
        // par mesure. Vide = une seule valeur, comme avant.
        points: _afPoints(it && it.points),
        placeholder: (it && typeof it.placeholder === 'string') ? it.placeholder : '',
        help: (it && typeof it.help === 'string') ? it.help : '',
        target_value: (it && it.target_value != null && it.target_value !== '') ? Number(it.target_value) : null,
        out_of_range_is_nc: !!(it && it.out_of_range_is_nc),
      };
    }
    const responses = Array.isArray(it && it.responses) ? it.responses.filter(r => typeof r === 'string' && r.trim()) : [];
    const ncResp = (it && Array.isArray(it.nc_responses))
      ? it.nc_responses.filter(r => typeof r === 'string' && r.trim())
      : [];
    // v2.5.21 : comment_responses — réponses qui exigent un commentaire de
    // l'opérateur. Doit être préservé ici, sinon la case COM se décoche à
    // chaque réouverture de la modale (même piège que required en v2.3.45).
    const comResp = (it && Array.isArray(it.comment_responses))
      ? it.comment_responses.filter(r => typeof r === 'string' && r.trim())
      : [];
    return {
      type: 'choice',
      label: (it && it.label) || '',
      responses: responses.length ? responses : ['Conforme'],
      multi: (it && it.multi === false) ? false : true,
      allow_other: !!(it && it.allow_other),
      other_is_nc: !!(it && it.other_is_nc),
      other_needs_comment: !!(it && it.other_needs_comment),
      nc_responses: ncResp,
      comment_responses: comResp,
      // v2.3.45 : préserver required (v2.2.86 dans settings_page — oublié ici)
      required: !!(it && it.required),
      help: (it && typeof it.help === 'string') ? it.help : '',
    };
  });
  return {
    description: (typeof p.description === 'string') ? p.description : '',
    // v2.5.6 : défaut 'periodic' (avant 'manual', qui ne déclenchait rien).
    trigger: Object.assign({ type: 'periodic', interval_minutes: 120, grace_minutes: 5, time: '08:00', days: ['mon','tue','wed','thu','fri'], event: 'dossier_start' }, trig),
    target: { machines: machines },
    validation: Object.assign({ button_label: 'Valider' }, p.validation || {}),
    dismiss_button: Object.assign({ enabled: false, label: 'Fermer l\'alerte' }, p.dismiss_button || {}),
    checklist: cl,
    placement: (p && ['top-right','center'].indexOf(p.placement) >= 0) ? p.placement : 'top-right',  // v2.3.12
    size: (p && ['small','medium','large'].indexOf(p.size) >= 0) ? p.size : 'medium',  // v2.3.12
    block_production: !!(p && p.block_production),  // v2.3.22 : persistance à la ré-ouverture
  };
}


  // ── _alertIsConfigured ──
  function _alertIsConfigured(a) {
  // Une alerte est "configurée" dès qu'elle a au moins une clé de paramètre
  // (trigger / target / validation / checklist) renseignée par l'admin.
  // Les alertes auto-créées par la migration v133 démarrent avec params={}.
  if (!a || !a.params || typeof a.params !== 'object') return false;
  return Object.keys(a.params).length > 0;
}


  // ── _daysLabel ──
  // v2.5.6 : rend les jours cochés en français court ("Lun, Mar, Mer") plutôt
  // qu'en codes bruts ("mon, tue, wed"), et détecte les deux cas courants.
  function _daysLabel(days) {
    if (!Array.isArray(days) || !days.length) return 'tous les jours';
    if (days.length === 7) return 'tous les jours';
    const week = ['mon','tue','wed','thu','fri'];
    if (days.length === 5 && week.every(d => days.indexOf(d) >= 0)) return 'du lundi au vendredi';
    const map = {};
    _ALERT_DAYS.forEach(d => { map[d.v] = d.l; });
    return _ALERT_DAYS.filter(d => days.indexOf(d.v) >= 0).map(d => map[d.v]).join(', ');
  }


  // ── _alertTriggerLabel ──
  function _alertTriggerLabel(t) {
  if (!t || !t.type) return 'Déclencheur non défini';
  // v2.5.6 : type obsolète — signalé explicitement dans la liste des alertes.
  if (t.type === 'manual')   return 'Manuel — obsolète, ne déclenche rien';
  if (t.type === 'periodic') {
    const m = (t.interval_minutes != null) ? t.interval_minutes
              : (t.interval_hours != null ? Math.round(t.interval_hours * 60) : '?');
    return 'Périodique — toutes les ' + m + ' min, en production';
  }
  if (t.type === 'calendar') return 'Calendaire — ' + (t.time || '??:??') + ' (' + _daysLabel(t.days) + ')';
  if (t.type === 'event') {
    const ev = (_ALERT_TRIGGER_EVENTS.find(e => e.v === t.event) || {}).l || t.event;
    return 'Événementiel — ' + ev;
  }
  return t.type;
}


  // ── _renderAlertFormFields ──
  function _renderAlertFormFields(params, opts) {
  opts = opts || {};
  _afDernierOpts = opts;
  _afInjectCss();
  const d = _alertDefaults(params);
  // Machines (multi-sélection via dropdown)
  const machineList = _ALERT_MACHINES.filter(m => m !== '*');
  const selectedMachines = (d.target && Array.isArray(d.target.machines)) ? d.target.machines : ['*'];
  const isAllMachines = selectedMachines.includes('*');
  const machineCheckboxes = machineList.map(m => {
    const checked = (!isAllMachines && selectedMachines.includes(m)) ? 'checked' : '';
    const disabled = isAllMachines ? ' disabled' : '';
    const rowCls = isAllMachines ? 'af-md-row is-disabled' : 'af-md-row';
    const safeM = escAttr(m);
    return '<div class="' + rowCls + '" onclick="_afRowClickByValue(event, \'' + safeM + '\')">'
      + '<input type="checkbox" class="af-machine" value="' + safeM + '"' + (checked ? ' ' + checked : '') + disabled + ' onchange="_afOnMachineChange()">'
      + '<div class="af-md-row-text">' + esc(m) + '</div>'
      + '</div>';
  }).join('');
  let machinesInitialLabel;
  if (isAllMachines) {
    machinesInitialLabel = 'Toutes les machines';
  } else if (selectedMachines.length === 0) {
    machinesInitialLabel = 'Aucune machine sélectionnée';
  } else if (selectedMachines.length === 1) {
    machinesInitialLabel = selectedMachines[0];
  } else if (selectedMachines.length <= 3) {
    machinesInitialLabel = selectedMachines.join(', ');
  } else {
    machinesInitialLabel = selectedMachines.length + ' machines';
  }
  const triggerOpts = _triggerOptsFor(d.trigger.type);
  // v2.5.6 : bandeau affiché uniquement pour les alertes encore stockées sur
  // l'ancien déclencheur « Manuel ». Aucune migration en base n'ayant été
  // faite, l'admin doit choisir lui-même un vrai déclencheur — le bandeau
  // évite qu'il découvre le problème par une alerte qui ne sonne jamais.
  const legacyTriggerBanner = _isLegacyTriggerType(d.trigger.type)
    ? '<div class="alert-field-sub" style="border-style:solid;border-color:var(--danger);background:rgba(239,68,68,.08);margin-bottom:10px">'
      +   '<p style="margin:0;font-size:12px;color:var(--text)"><strong>Déclencheur obsolète.</strong> Cette alerte utilise « Manuel », un type supprimé qui ne déclenchait rien : elle n\'est jamais apparue chez l\'opérateur. Choisis un déclencheur réel ci-dessous pour la rendre active.</p>'
      + '</div>'
    : '';
  const eventOpts = _ALERT_TRIGGER_EVENTS.map(e =>
    '<option value="' + e.v + '"' + (e.v === d.trigger.event ? ' selected' : '') + '>' + esc(e.l) + '</option>'
  ).join('');
  const daysHtml = _ALERT_DAYS.map(day => {
    const checked = (d.trigger.days || []).indexOf(day.v) >= 0 ? 'checked' : '';
    return '<label style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;background:var(--card);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:12px"><input type="checkbox" class="af-day" value="' + day.v + '" ' + checked + ' style="margin:0">' + day.l + '</label>';
  }).join(' ');

  const nomBlock = opts.nomReadonly
    ? '<div class="alert-field"><label class="alert-field-label">Titre <span style="color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400">— synchronisé avec le code</span></label><input type="text" class="alert-field-input" value="' + escAttr(opts.nomValue || '') + '" disabled></div>'
    : '<div class="alert-field"><label class="alert-field-label">Titre de l\'alerte <span style="color:var(--danger)">*</span></label><input type="text" id="af-nom" class="alert-field-input" maxlength="120" placeholder="Ex. Contrôle qualité Cohésio 1" value="' + escAttr(opts.nomValue || '') + '"></div>';

  const descBlock = '<div class="alert-field">'
    +   '<label class="alert-field-label">Description <span style="color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400">— contexte affiché à l\'opérateur</span></label>'
    +   '<textarea id="af-description" class="alert-field-input" rows="2" maxlength="800" placeholder="Ex. Vérifier la tension Errepi et le serrage de la bobine — noter la valeur exacte pour analyse.">' + esc(d.description || '') + '</textarea>'
    +   '<div class="alert-field-help">Optionnel. Affiché sous le titre de l\'alerte quand elle apparaît chez l\'opérateur.</div>'
    + '</div>';
  // v2.6 : formulaire en sections repliables, chacune résumée dans son
  // en-tête (« Périodique — toutes les 120 min », « 3 machines »…) pour
  // retrouver un réglage sans tout déplier. Le questionnaire est ouvert.
  const _nbPoints = (d.checklist.items || []).filter(it => it && it.label).length;
  return '<div class="af-champs">' + nomBlock
    + descBlock
    + _afSection('questionnaire', 'Questionnaire', _afSumQuestionnaire(d.checklist.enabled, _nbPoints), ''
    // v2.3.33 : questionnaire remonté juste après la description (l'admin
    // pense d'abord au contenu, ensuite au paramétrage technique)
    + '<div class="alert-field">'
    +   '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px">'
    +     '<div>'
    +       '<label class="alert-field-label" style="margin-bottom:2px">Activer le questionnaire</label>'
    +       '<span style="font-size:11px;color:var(--muted)">Ex. découpe nette, colle conforme, centrage OK… L\'opérateur cochera chaque point lors de la validation.</span>'
    +     '</div>'
    +     '<label class="toggle"><input type="checkbox" id="af-checklist-enabled" ' + (d.checklist.enabled ? 'checked' : '') + ' onchange="_afOnChecklistToggle()"><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
    +   '</div>'
    +   '<div id="af-checklist-wrap" style="' + (d.checklist.enabled ? '' : 'display:none;') + '">'
    +     '<div id="af-checklist-items" ondragover="_afDragOver(event)" ondrop="event.preventDefault()" style="display:flex;flex-direction:column;gap:6px;margin-bottom:8px">' + _afRenderChecklistItems(d.checklist.items) + '</div>'
    +     '<button type="button" class="btn-sm btn-ghost" onclick="_afAddChecklistItem()" style="margin-bottom:10px"><span style="font-weight:700;margin-right:4px">+</span> Ajouter un point de contrôle</button>'
    +   '</div>'
    + '</div>'
    + '<div class="alert-field-sub" style="border-style:solid;background:var(--accent-bg);border-color:var(--accent);margin-top:14px">'
    +   '<p style="margin:0;font-size:12px;color:var(--text)"><strong>Zone de commentaires</strong> — toujours disponible pour l\'opérateur (champ texte libre, optionnel, joint à chaque acquittement).</p>'
    + '</div>'
    , true)
    + _afSection('declencheur', 'Déclenchement', _alertTriggerLabel(d.trigger), ''
    +   '<div class="alert-field">'
    +     '<label class="alert-field-label">Déclencheur <span style="color:var(--danger)">*</span></label>'
    +     legacyTriggerBanner
    +     '<select id="af-trigger-type" class="alert-field-input" onchange="_afOnTriggerChange()">' + triggerOpts + '</select>'
    +     '<div id="af-trigger-sub" class="alert-field-sub">'
    +       '<div data-trigger-for="manual" style="font-size:12px;color:var(--muted)">Type supprimé — aucun déclenchement, l\'alerte reste dormante tant qu\'un autre déclencheur n\'est pas choisi.</div>'
    +       '<div data-trigger-for="periodic">'
    +         '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
    +           '<div>'
    +             '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Intervalle entre alertes (min)</label>'
    +             '<input type="number" id="af-trigger-interval-minutes" class="alert-field-input" min="1" max="10080" step="1" value="' + d.trigger.interval_minutes + '">'
    +           '</div>'
    +           '<div>'
    +             '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Délai avant 1ère alerte (min)</label>'
    +             '<input type="number" id="af-trigger-grace-minutes" class="alert-field-input" min="0" max="120" step="1" value="' + (d.trigger.grace_minutes != null ? d.trigger.grace_minutes : 5) + '">'
    +           '</div>'
    +         '</div>'
    +         '<div class="alert-field-sub" style="border-style:solid;border-color:var(--accent);background:var(--accent-bg);margin-top:8px">'
    +           '<p style="margin:0;font-size:12px;color:var(--text)"><strong>Ne fonctionne qu\'en production.</strong> L\'alerte n\'est évaluée que si la <strong>dernière saisie de la machine est un 03 (Production) ou un 88 (Reprise)</strong>. Machine à l\'arrêt, en calage (02), en événement personnel (86), ou simplement sur un 01 (Début de dossier) : le compteur est gelé et rien ne s\'affiche. Toute saisie hors 03/88 clôt la session en cours et remet le compteur à zéro — la prochaine reprise repart sur le délai avant 1ère alerte.</p>'
    +         '</div>'
    +         '<div class="alert-field-help">La <strong>première alerte</strong> de chaque session de production s\'affiche après le délai indiqué (par défaut 5 min). Les alertes suivantes s\'affichent toutes les X minutes après la dernière validation. Utiliser des délais différents entre alertes pour les espacer naturellement au démarrage.</div>'
    +       '</div>'
    +       '<div data-trigger-for="calendar">'
    +         '<div class="alert-field-row">'
    +           '<div><label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Heure</label><input type="time" id="af-trigger-time" class="alert-field-input" value="' + esc(d.trigger.time) + '"></div>'
    +           '<div></div>'
    +         '</div>'
    +         '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2);margin-top:8px">Jours</label>'
    +         '<div style="display:flex;flex-wrap:wrap;gap:6px">' + daysHtml + '</div>'
    +         '<div class="alert-field-sub" style="border-style:solid;border-color:var(--accent);background:var(--accent-bg);margin-top:10px">'
    +           '<p style="margin:0;font-size:12px;color:var(--text)"><strong>Fonctionne machine à l\'arrêt.</strong> Contrairement au périodique, aucune condition de production : l\'alerte devient due à l\'heure indiquée et s\'affiche dès qu\'un opérateur ciblé ouvre son écran. Typiquement un contrôle de prise de poste, avant tout démarrage.</p>'
    +         '</div>'
    +         '<div class="alert-field-help">Un opérateur qui arrive après l\'heure voit quand même le contrôle : l\'alerte <strong>reste affichée tant qu\'elle n\'a pas été validée</strong>, y compris les jours suivants. Elle ne s\'empile pas — l\'occurrence du jour remplace celle de la veille. Chaque machine ciblée valide de son côté. Une alerte créée après l\'heure du jour ne rattrape pas l\'occurrence passée : elle démarre à la suivante.</div>'
    +       '</div>'
    +       '<div data-trigger-for="event">'
    +         '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Événement</label>'
    +         '<select id="af-trigger-event" class="alert-field-input" onchange="_afOnTriggerEventChange()">' + eventOpts + '</select>'
    +       '</div>'
    +     '</div>'
    +   '</div>'
    , _isLegacyTriggerType(d.trigger.type))
    + _afSection('machines', 'Machines ciblées', machinesInitialLabel, ''
    +   '<div class="alert-field">'
    +     '<label class="alert-field-label">Machines ciblées <span style="color:var(--danger)">*</span></label>'
    +     '<div class="af-md-wrap">'
    +       '<button type="button" class="af-md-trigger" onclick="_afToggleMachinesPanel(event)">'
    +         '<span id="af-md-label" class="af-md-trigger-label">' + esc(machinesInitialLabel) + '</span>'
    +         '<span class="af-md-trigger-caret">▼</span>'
    +       '</button>'
    +       '<div id="af-md-panel" class="af-md-panel">'
    +         '<div class="af-md-row" onclick="_afRowClick(event, \'af-target-all\')">'
    +           '<input type="checkbox" id="af-target-all" ' + (isAllMachines ? 'checked' : '') + ' onchange="_afOnAllMachinesToggle()">'
    +           '<div class="af-md-row-text"><strong>Toutes les machines</strong><span class="af-md-row-hint">présentes et futures</span></div>'
    +         '</div>'
    +         '<div class="af-md-sep"></div>'
    +         machineCheckboxes
    +       '</div>'
    +     '</div>'
    +     '<div class="alert-field-help">Les alertes sont toujours visibles par les opérateurs <strong>fabrication</strong> ainsi que par le super administrateur (pour les tests).</div>'
    +   '</div>'
    , false)
    + _afSection('affichage', 'Affichage et blocage', _afSumAffichage(d.placement, d.size, d.block_production), ''
    // v2.3.33 : section Affichage — Placement + Taille uniquement
    +   '<div class="alert-field">'
    +     '<div style="font-size:11px;font-weight:800;color:var(--text2);text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px">Affichage</div>'
    +     '<div class="alert-field-row" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
    +       '<div><label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Placement à l\'écran</label>'
    +         '<select id="af-placement" class="alert-field-input">'
    +           '<option value="top-right"' + (d.placement === 'top-right' ? ' selected' : '') + '>Coin haut droit</option>'
    +           '<option value="center"' + (d.placement === 'center' ? ' selected' : '') + '>Centre</option>'
    +         '</select>'
    +       '</div>'
    +       '<div><label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Taille</label>'
    +         '<select id="af-size" class="alert-field-input">'
    +           '<option value="small"' + (d.size === 'small' ? ' selected' : '') + '>Petite</option>'
    +           '<option value="medium"' + (d.size === 'medium' ? ' selected' : '') + '>Moyenne</option>'
    +           '<option value="large"' + (d.size === 'large' ? ' selected' : '') + '>Grande</option>'
    +         '</select>'
    +       '</div>'
    +     '</div>'
    +   '</div>'
    // v2.3.33 : Bloquer la production — section séparée d'Affichage
    +   '<div class="alert-field" style="border-top:1px solid var(--border);padding-top:14px;margin-top:14px">'
    +     '<div style="display:flex;align-items:center;gap:12px;justify-content:space-between">'
    +       '<div>'
    +         '<label class="alert-field-label" style="margin-bottom:2px">Bloque la production</label>'
    +         '<span style="font-size:11px;color:var(--muted)">Quand activé, l\'opérateur ne peut plus saisir la moindre opération de production tant que cette alerte n\'a pas été validée. Backdrop bloquant côté opérateur + refus HTTP 423 côté serveur.</span>'
    +       '</div>'
    +       '<label class="toggle"><input type="checkbox" id="af-block-production"' + (d.block_production ? ' checked' : '') + '><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
    +     '</div>'
    +   '</div>'
    , false)
    + _afSection('esquive', 'Fermeture sans saisie', _afSumEsquive(d.dismiss_button), ''
    +   '<div class="alert-field">'
    +     '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px">'
    +       '<div>'
    +         '<label class="alert-field-label" style="margin-bottom:2px">Autoriser la fermeture sans saisie</label>'
    +         '<span style="font-size:11px;color:var(--muted)">Ajoute un 2e bouton pour esquiver l\'alerte. Une trace est conservée dans l\'historique sous "Fermetures auto".</span>'
    +       '</div>'
    +       '<label class="toggle"><input type="checkbox" id="af-dismiss-enabled" ' + (d.dismiss_button.enabled ? 'checked' : '') + ' onchange="_afOnDismissToggle()"><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
    +     '</div>'
    +     '<div id="af-dismiss-wrap" style="' + (d.dismiss_button.enabled ? '' : 'display:none;') + '">'
    +       '<input type="text" id="af-dismiss-label" class="alert-field-input" maxlength="40" value="' + escAttr(d.dismiss_button.label) + '" placeholder="Fermer l\'alerte">'
    +       '<div class="alert-field-help">Libellé du bouton d\'esquive (bouton orange à côté du bouton principal Valider). Ce libellé apparaît aussi dans l\'historique (ex. « Fermée auto (esquive) : Pas d\'Errepi »).</div>'
    +     '</div>'
    +   '</div>'
    , false)
    + '</div>';
}


  // ── _afChecklistCard ──
  function _afChecklistCard(item) {
  const safeLabel = ((item && item.label) || '').replace(/"/g, '&quot;');
  const type = (item && item.type) || 'choice';
  // v2.3.28 : case "Obligatoire" — manquait dans maintenance_page.py, la
  // valeur ne pouvait donc jamais être true côté /maintenance. Elle
  // s'affiche à la lecture (checked selon item.required) et son état
  // est envoyé au backend par _afReadParams.
  const isRequired = !!(item && item.required);
  const typeOpts = '<option value="choice"' + (type === 'choice' ? ' selected' : '') + '>Cases à cocher</option>'
                 + '<option value="value"' + (type === 'value' ? ' selected' : '') + '>Valeur à saisir</option>';
  return '<div class="af-cl-card" ondragstart="_afDragStart(event)" ondragend="_afDragEnd(event)" style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:8px">'
    + '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
    +   '<span class="af-cl-poignee" title="Glisser pour réordonner" onmousedown="_afArmDrag(this)" onmouseup="_afDisarmDrag(this)" ontouchstart="_afArmDrag(this)">'
    +     '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="9" cy="6" r="1.6"/><circle cx="15" cy="6" r="1.6"/><circle cx="9" cy="12" r="1.6"/><circle cx="15" cy="12" r="1.6"/><circle cx="9" cy="18" r="1.6"/><circle cx="15" cy="18" r="1.6"/></svg>'
    +   '</span>'
    +   '<input type="text" class="alert-field-input af-cl-label" maxlength="200" placeholder="Ex. Découpe" value="' + safeLabel + '" style="flex:1;min-width:140px;font-weight:500">'
    +   '<select class="alert-field-input af-cl-type" onchange="_afOnTypeChange(this)" style="flex:0 0 auto;width:auto;padding:8px 10px;font-size:13px">' + typeOpts + '</select>'
    +   '<button type="button" class="btn-sm af-cl-dupliquer" onclick="_afDuplicateItem(this)" title="Dupliquer ce point de contrôle" aria-label="Dupliquer">'
    +     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>'
    +   '</button>'
    +   '<button type="button" class="btn-sm btn-ghost danger" onclick="_afRemoveItem(this)" title="Supprimer ce point de contrôle" style="flex:0 0 auto">×</button>'
    + '</div>'
    + '<label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2);cursor:pointer;padding:4px 2px">'
    +   '<input type="checkbox" class="af-cl-required"' + (isRequired ? ' checked' : '') + ' style="width:14px;height:14px;accent-color:var(--danger);cursor:pointer">'
    +   '<span>Obligatoire <span style="color:var(--muted);font-weight:500">(l\'opérateur ne peut pas valider tant que cette question n\'est pas répondue)</span></span>'
    + '</label>'
    + _afChecklistCardBody(item)
    + '<div>'
    +   '<div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Méthode opératoire <span style="text-transform:none;letter-spacing:0">(optionnel)</span></div>'
    +   '<textarea class="alert-field-input af-cl-help" rows="2" maxlength="300" placeholder="Ex. Peser 10 étiquettes sur la balance de précision, diviser par 10." style="padding:6px 10px;font-size:13px;resize:vertical">' + esc((item && item.help) || '') + '</textarea>'
    +   '<div class="alert-field-help" style="margin-top:4px">Affiché sous la question, chez l\'opérateur.</div>'
    + '</div>'
    + '</div>';
}


  // ── _afChecklistCardBody ──
  function _afChecklistCardBody(item) {
  const type = (item && item.type) || 'choice';
  if (type === 'value') {
    const safeUnit = ((item && item.unit) || '').replace(/"/g, '&quot;');
    const safeMin = (item && item.min != null && item.min !== '') ? String(item.min) : '';
    const safeMax = (item && item.max != null && item.max !== '') ? String(item.max) : '';
    const safeCible = (item && item.target_value != null && item.target_value !== '') ? String(item.target_value) : '';
    const oorNc = !!(item && item.out_of_range_is_nc);
    const safePh = escAttr((item && item.placeholder) || '');
    const pts = _afPoints(item && item.points);
    const multiOn = pts.length > 1;
    const ptsTxt = escAttr((multiOn ? pts : _AF_POINTS_DEFAUT).join(' / '));
    return '<div class="af-cl-body" data-type="value">'
      + '<div class="af-cl-grid4">'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Unité</div><input type="text" class="alert-field-input af-cl-unit" maxlength="20" placeholder="bar, °C, mm…" value="' + safeUnit + '" style="padding:6px 10px;font-size:13px"></div>'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Min</div><input type="number" step="any" class="alert-field-input af-cl-min" placeholder="2.5" value="' + safeMin + '" style="padding:6px 10px;font-size:13px"></div>'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Cible</div><input type="number" step="any" class="alert-field-input af-cl-cible" placeholder="2.85" value="' + safeCible + '" style="padding:6px 10px;font-size:13px"></div>'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Max</div><input type="number" step="any" class="alert-field-input af-cl-max" placeholder="3.2" value="' + safeMax + '" style="padding:6px 10px;font-size:13px"></div>'
      + '</div>'
      + '<div class="alert-field-help" style="margin-top:6px">Pour pression, température, dimension… Min, Cible et Max sont optionnels. La cible s\'affiche chez l\'opérateur avec l\'écart de sa mesure.</div>'
      + '<label style="display:flex;align-items:center;gap:8px;margin-top:8px;cursor:pointer;font-size:12px;color:var(--text2)">'
      +   '<input type="checkbox" class="af-cl-oor-nc"' + (oorNc ? ' checked' : '') + ' style="width:14px;height:14px;accent-color:var(--danger);cursor:pointer">'
      +   '<span>Valeur hors tolérance = <strong style="color:var(--danger)">non-conformité</strong> <span style="color:var(--muted)">(signalée dans l\'historique des contrôles ; Min ou Max requis)</span></span>'
      + '</label>'
      + '<div style="margin-top:8px"><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Texte d\'exemple dans le champ <span style="text-transform:none;letter-spacing:0">(optionnel)</span></div>'
      +   '<input type="text" class="alert-field-input af-cl-placeholder" maxlength="60" placeholder="Valeur" value="' + safePh + '" style="padding:6px 10px;font-size:13px"></div>'
      + '<label style="display:flex;align-items:center;gap:8px;margin-top:8px;padding-top:8px;border-top:1px dashed var(--border);cursor:pointer;font-size:12px;color:var(--text2)">'
      +   '<input type="checkbox" class="af-cl-points-toggle"' + (multiOn ? ' checked' : '') + ' onchange="_afOnPointsToggle(this)" style="width:14px;height:14px;accent-color:var(--accent);cursor:pointer">'
      +   '<span><strong style="color:var(--text)">Plusieurs valeurs</strong> à saisir pour ce point (ex. début, milieu et fin de production)</span>'
      + '</label>'
      + '<div class="af-cl-points-wrap" style="display:' + (multiOn ? 'block' : 'none') + ';margin-top:6px;margin-left:22px">'
      +   '<input type="text" class="alert-field-input af-cl-points" maxlength="300" placeholder="Début de prod / Milieu de prod / Fin de prod" value="' + ptsTxt + '" style="padding:6px 10px;font-size:13px">'
      +   '<div class="alert-field-help" style="margin-top:4px">Un libellé par mesure, séparés par « / » (10 au plus). Si le point est obligatoire, toutes les mesures doivent être saisies.</div>'
      + '</div>'
      + '</div>';
  }
  // type "choice"
  const responses = (item && Array.isArray(item.responses) && item.responses.length) ? item.responses : ['Conforme'];
  const ncList = (item && Array.isArray(item.nc_responses)) ? item.nc_responses.map(String) : [];
  // v2.5.21 : comList = réponses marquées « commentaire obligatoire » (case COM)
  const comList = (item && Array.isArray(item.comment_responses)) ? item.comment_responses.map(String) : [];
  const responsesHtml = responses.map((r) => _afResponseRow(
    r,
    ncList.indexOf(String(r)) !== -1,
    comList.indexOf(String(r)) !== -1
  )).join('');
  const multi = (item && item.multi === false) ? false : true;
  return '<div class="af-cl-body" data-type="choice">'
    + '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
    +   '<div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Réponses possibles</div>'
    +   '<select class="alert-field-input af-cl-multi-sel" style="flex:0 0 auto;width:auto;padding:5px 8px;font-size:12px">'
    +     '<option value="multi"' + (multi ? ' selected' : '') + '>Plusieurs réponses (cases)</option>'
    +     '<option value="single"' + (!multi ? ' selected' : '') + '>Une seule réponse (radio)</option>'
    +   '</select>'
    + '</div>'
    + '<div class="af-cl-responses" style="display:flex;flex-direction:column;gap:4px">' + responsesHtml + '</div>'
    + '<button type="button" class="btn-sm btn-ghost" onclick="_afAddResponse(this)" style="margin-top:6px;font-size:12px"><span style="font-weight:700;margin-right:4px">+</span> Ajouter une réponse</button>'
    + '<label style="display:flex;align-items:center;gap:8px;margin-top:8px;padding-top:8px;border-top:1px dashed var(--border);cursor:pointer;font-size:12px;color:var(--text2)">'
    +   '<input type="checkbox" class="af-cl-other-toggle"' + ((item && item.allow_other) ? ' checked' : '') + ' onchange="_afOnOtherToggle(this)" style="width:14px;height:14px;accent-color:var(--accent);cursor:pointer">'
    +   '<span>Ajouter une réponse <strong style="color:var(--text)">« Autre »</strong> avec zone d\'explication optionnelle</span>'
    + '</label>'
    + '<label class="af-cl-other-nc-lbl" style="display:' + ((item && item.allow_other) ? 'flex' : 'none') + ';align-items:center;gap:8px;margin-top:4px;margin-left:22px;cursor:pointer;font-size:12px;color:var(--text2)">'
    +   '<input type="checkbox" class="af-cl-other-nc"' + ((item && item.other_is_nc) ? ' checked' : '') + ' style="width:13px;height:13px;accent-color:var(--danger);cursor:pointer">'
    +   '<span>Traiter <strong style="color:var(--text)">« Autre »</strong> comme une <strong style="color:var(--danger)">non-conformité</strong></span>'
    + '</label>'
    // v2.5.21 : équivalent COM pour la réponse « Autre ». Sa zone d'explication
    // passe alors d'optionnelle à obligatoire.
    + '<label class="af-cl-other-com-lbl" style="display:' + ((item && item.allow_other) ? 'flex' : 'none') + ';align-items:center;gap:8px;margin-top:4px;margin-left:22px;cursor:pointer;font-size:12px;color:var(--text2)">'
    +   '<input type="checkbox" class="af-cl-other-com"' + ((item && item.other_needs_comment) ? ' checked' : '') + ' style="width:13px;height:13px;accent-color:var(--accent);cursor:pointer">'
    +   '<span>Rendre l\'explication <strong style="color:var(--text)">obligatoire</strong> quand <strong style="color:var(--text)">« Autre »</strong> est choisi</span>'
    + '</label>'
    // v2.5.21 : légende des deux puces — sans elle, « NC » et « COM » sont
    // deux acronymes muets pour l'admin qui découvre l'écran.
    + '<div style="margin-top:8px;font-size:11px;color:var(--muted);line-height:1.6">'
    +   '<strong style="color:var(--text2)">NC</strong> — la réponse marque la ligne comme non conforme dans l\'historique.<br>'
    +   '<strong style="color:var(--text2)">COM</strong> — la réponse ouvre une zone de commentaire obligatoire ; l\'opérateur ne peut pas valider tant qu\'elle est vide.'
    + '</div>'
    + '</div>';
}


  // ── _afRenderChecklistItems ──
  function _afRenderChecklistItems(items) {
  const list = (items && items.length) ? items : [{ label: '', responses: ['Conforme'] }];
  return list.map(_afChecklistCard).join('');
}


  // ── _afAddChecklistItem ──
  function _afAddChecklistItem() {
  const wrap = document.getElementById('af-checklist-items');
  if (!wrap) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = _afChecklistCard({ type: 'choice', label: '', responses: ['Conforme'], multi: true, allow_other: false });
  const card = tmp.firstElementChild;
  wrap.appendChild(card);
  card.querySelector('.af-cl-label')?.focus();
}


  // ── _afRemoveItem ──
  function _afRemoveItem(btn) {
  const card = btn.closest('.af-cl-card');
  if (card) card.remove();
}


  // ── _afResponseRow ──
  function _afResponseRow(value, isNc, needsCom) {
  const safeVal = (value || '').replace(/"/g, '&quot;');
  const ncChecked = isNc ? ' checked' : '';
  const comChecked = needsCom ? ' checked' : '';
  return '<div class="af-cl-resp-row" style="display:flex;gap:6px;align-items:center">'
    + '<input type="text" class="alert-field-input af-cl-resp-input" maxlength="100" placeholder="Ex. Nette" value="' + safeVal + '" style="flex:1;padding:6px 10px;font-size:13px">'
    // v2.5.20 : plus de background inline — la puce NC vit dans une .af-cl-card
    // deja peinte en var(--bg), elle serait bleu sur bleu. Le fond est desormais
    // pilote par le CSS (.af-cl-nc-lbl -> var(--card)), ce qui laisse aussi
    // l'etat coche (:has(input:checked)) reprendre la main.
    + '<label class="af-cl-nc-lbl" title="Cocher si cette réponse signale une non-conformité" style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:6px;border:1px solid var(--border);cursor:pointer;font-size:11px;color:var(--text2);white-space:nowrap;user-select:none">'
    +   '<input type="checkbox" class="af-cl-resp-nc"' + ncChecked + ' style="width:12px;height:12px;accent-color:var(--danger);cursor:pointer">'
    +   '<span>NC</span>'
    + '</label>'
    // v2.5.21 : puce COM — quand elle est cochée, choisir cette réponse ouvre
    // une zone de commentaire obligatoire sous le point de contrôle chez
    // l'opérateur, et bloque Valider tant qu'elle est vide. Indépendante de NC :
    // une réponse peut être NC seule, COM seule, ou les deux.
    + '<label class="af-cl-com-lbl" title="Cocher si cette réponse exige un commentaire obligatoire de l\'opérateur" style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:6px;border:1px solid var(--border);cursor:pointer;font-size:11px;color:var(--text2);white-space:nowrap;user-select:none">'
    +   '<input type="checkbox" class="af-cl-resp-com"' + comChecked + ' style="width:12px;height:12px;accent-color:var(--accent);cursor:pointer">'
    +   '<span>COM</span>'
    + '</label>'
    + '<button type="button" class="btn-sm btn-ghost danger" onclick="_afRemoveResponse(this)" title="Supprimer cette réponse">×</button>'
    + '</div>';
}


  // ── _afAddResponse ──
  function _afAddResponse(btn) {
  const card = btn.closest('.af-cl-card');
  if (!card) return;
  const list = card.querySelector('.af-cl-responses');
  if (!list) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = _afResponseRow('');
  const row = tmp.firstElementChild;
  list.appendChild(row);
  row.querySelector('.af-cl-resp-input')?.focus();
}


  // ── _afRemoveResponse ──
  function _afRemoveResponse(btn) {
  const row = btn.closest('.af-cl-resp-row');
  if (!row) return;
  const list = row.parentElement;
  if (!list) { row.remove(); return; }
  // Garde au moins une réponse par point
  if (list.querySelectorAll('.af-cl-resp-row').length <= 1) {
    toast('Un point doit garder au moins une réponse', true);
    return;
  }
  row.remove();
}



  // ── Sections repliables ──
  function _afSection(key, title, summary, body, open) {
    return '<section class="af-sec' + (open ? ' open' : '') + '" data-sec="' + key + '">'
      + '<button type="button" class="af-sec-head" onclick="_afToggleSection(this)" aria-expanded="' + (open ? 'true' : 'false') + '">'
      +   '<span class="af-sec-titre">' + esc(title) + '</span>'
      +   '<span class="af-sec-sum" data-sum="' + key + '">' + esc(summary || '') + '</span>'
      +   '<svg class="af-sec-caret" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
      + '</button>'
      + '<div class="af-sec-body">' + body + '</div>'
      + '</section>';
  }
  function _afToggleSection(btn) {
    const sec = btn.closest('.af-sec');
    if (!sec) return;
    const open = !sec.classList.contains('open');
    sec.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function _afOpenSection(key) {
    document.querySelectorAll('.af-sec' + (key ? '[data-sec="' + key + '"]' : '')).forEach(sec => {
      sec.classList.add('open');
      sec.querySelector('.af-sec-head')?.setAttribute('aria-expanded', 'true');
    });
  }
  function _afSumQuestionnaire(enabled, n) {
    if (!enabled) return 'Désactivé';
    return n + ' point' + (n > 1 ? 's' : '') + ' de contrôle';
  }
  function _afSumAffichage(placement, size, block) {
    const pl = placement === 'center' ? 'Centre' : 'Coin haut droit';
    const sz = ({ small: 'petite', medium: 'moyenne', large: 'grande' })[size] || 'moyenne';
    return pl + ' · ' + sz + (block ? ' · bloque la production' : '');
  }
  function _afSumEsquive(db) {
    return (db && db.enabled) ? '« ' + (db.label || 'Fermer l\'alerte') + ' »' : 'Désactivée';
  }
  // Recalcule les résumés depuis les champs, à chaque saisie.
  function _afRefreshSummaries() {
    const set = (k, v) => { const t = document.querySelector('[data-sum="' + k + '"]'); if (t) t.textContent = v; };
    const clOn = !!document.getElementById('af-checklist-enabled')?.checked;
    const n = Array.from(document.querySelectorAll('.af-cl-card .af-cl-label')).filter(i => (i.value || '').trim()).length;
    set('questionnaire', _afSumQuestionnaire(clOn, n));
    const tt = document.getElementById('af-trigger-type')?.value;
    if (tt) {
      const trig = { type: tt,
        interval_minutes: document.getElementById('af-trigger-interval-minutes')?.value || '?',
        time: document.getElementById('af-trigger-time')?.value || '',
        days: Array.from(document.querySelectorAll('.af-day:checked')).map(x => x.value),
        event: document.getElementById('af-trigger-event')?.value || '' };
      set('declencheur', _alertTriggerLabel(trig));
    }
    const ml = document.getElementById('af-md-label');
    if (ml) set('machines', ml.textContent || '');
    set('affichage', _afSumAffichage(document.getElementById('af-placement')?.value, document.getElementById('af-size')?.value, !!document.getElementById('af-block-production')?.checked));
    set('esquive', _afSumEsquive({ enabled: !!document.getElementById('af-dismiss-enabled')?.checked, label: (document.getElementById('af-dismiss-label')?.value || '').trim() }));
  }

  // ── Dupliquer / réordonner les points de contrôle ──
  function _afDuplicateItem(btn) {
    const card = btn.closest('.af-cl-card');
    if (!card) return;
    const item = _afReadCard(card) || { type: card.querySelector('.af-cl-type')?.value || 'choice', label: '' };
    if (item.label) item.label = (item.label + ' (copie)').slice(0, 200);
    const tmp = document.createElement('div');
    tmp.innerHTML = _afChecklistCard(item);
    const copie = tmp.firstElementChild;
    card.after(copie);
    const lbl = copie.querySelector('.af-cl-label');
    if (lbl) { lbl.focus(); lbl.select(); }
  }
  // Le glisser ne part que de la poignée : une carte toujours « draggable »
  // empêcherait de sélectionner le texte de ses champs.
  function _afArmDrag(handle) {
    const card = handle.closest('.af-cl-card');
    if (card) card.setAttribute('draggable', 'true');
  }
  // Clic sur la poignée sans glisser : la carte redevient normale.
  function _afDisarmDrag(handle) {
    const card = handle.closest('.af-cl-card');
    if (card && card !== _afDragged) card.removeAttribute('draggable');
  }
  let _afDragged = null;
  function _afDragStart(ev) {
    const card = ev.target.closest && ev.target.closest('.af-cl-card');
    if (!card || card.getAttribute('draggable') !== 'true') return;
    _afDragged = card;
    card.classList.add('af-cl-glisse');
    try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', ''); } catch (e) {}
  }
  function _afDragEnd(ev) {
    const card = ev.target.closest && ev.target.closest('.af-cl-card');
    if (card) { card.classList.remove('af-cl-glisse'); card.removeAttribute('draggable'); }
    _afDragged = null;
  }
  function _afDragOver(ev) {
    if (!_afDragged) return;
    ev.preventDefault();
    const list = ev.currentTarget;
    const cards = Array.from(list.querySelectorAll(':scope > .af-cl-card')).filter(c => c !== _afDragged);
    let avant = null;
    for (const c of cards) {
      const r = c.getBoundingClientRect();
      if (ev.clientY < r.top + r.height / 2) { avant = c; break; }
    }
    if (avant) { if (_afDragged.nextElementSibling !== avant) list.insertBefore(_afDragged, avant); }
    else if (list.lastElementChild !== _afDragged) list.appendChild(_afDragged);
  }


  // ── Assistant IA ──
  // Crée ou modifie l'alerte depuis une consigne ou une fiche de contrôle
  // jointe (app/routers/maintenance_alertes_ia.py). La proposition remplit le
  // formulaire ; rien n'est enregistré avant « Enregistrer » / « Créer ».
  var _afDernierOpts = {};
  var _afIaAvant = null;   // {nom, params} — pour « Annuler la modification »
  var _afIaModeles = null;
  var _AF_IA_EXEMPLES = {
    creer: [
      "Contrôle des produits finis toutes les 2 heures en production : centrage de l'étiquette, poids de l'étiquette en début, milieu et fin de production",
      "Contrôle de prise de poste à 6 h, du lundi au vendredi, sur toutes les machines : propreté, sécurité, outillage",
      "Après le calage : vérifier la tension et le serrage de la bobine, noter la tension mesurée",
    ],
    modifier: [
      "Ajoute un point « Propreté de la machine » avec les réponses Conforme / Non conforme",
      "Rends obligatoires tous les points de contrôle",
      "Passe le déclencheur à toutes les 90 minutes",
    ],
  };

  function _afIaMode(champs) {
    const aDuContenu = Array.from(champs.querySelectorAll('.af-cl-card .af-cl-label')).some(i => (i.value || '').trim())
      || ((champs.querySelector('#af-description') || {}).value || '').trim();
    return aDuContenu ? 'modifier' : 'creer';
  }

  // Lecture complète du formulaire, sans message d'erreur ni ouverture des
  // sections : sert à transmettre l'état courant et à pouvoir l'annuler.
  function _afLireSilencieux() {
    const ouvertes = Array.from(document.querySelectorAll('.af-sec.open')).map(x => x.getAttribute('data-sec'));
    const t = toast;
    let p = null;
    toast = function () {};
    try { p = _afReadParams(); } catch (e) { p = null; }
    finally {
      toast = t;
      document.querySelectorAll('.af-sec').forEach(sec => {
        const on = ouvertes.indexOf(sec.getAttribute('data-sec')) !== -1;
        sec.classList.toggle('open', on);
        sec.querySelector('.af-sec-head')?.setAttribute('aria-expanded', on ? 'true' : 'false');
      });
    }
    return p;
  }

  async function _afIaChargerModeles() {
    if (_afIaModeles) return _afIaModeles;
    try {
      const r = await fetch('/api/maintenance/alerts/ia/modeles', { credentials: 'include' });
      if (r.ok) _afIaModeles = await r.json();
    } catch (e) {}
    return _afIaModeles || { modeles: [], defaut: '' };
  }

  function _afIaBarreHtml() {
    return '<div class="af-ia-barre">'
      + '<button type="button" class="af-ia-btn" onclick="_afIaOuvrir(this)">'
      +   '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.9 5.8H20l-4.9 3.6 1.9 5.8L12 14.6l-4.9 3.6 1.9-5.8L4 8.8h6.1z"/></svg>'
      +   '<span class="af-ia-btn-lbl">Créer avec l\'IA</span>'
      + '</button>'
      + '<span class="af-ia-aide">Décrire l\'alerte, ou joindre une fiche de contrôle papier : le formulaire se remplit, à relire avant d\'enregistrer.</span>'
      + '</div>'
      + '<div class="af-ia-panneau" hidden></div>'
      + '<div class="af-ia-note" hidden></div>';
  }

  function _afIaMajBouton(col) {
    const champs = col.querySelector('.af-champs');
    const lbl = col.querySelector('.af-ia-btn-lbl');
    if (champs && lbl) lbl.textContent = _afIaMode(champs) === 'modifier' ? 'Modifier avec l\'IA' : 'Créer avec l\'IA';
  }

  async function _afIaOuvrir(btn) {
    const col = btn.closest('.af-col-form');
    const panneau = col && col.querySelector('.af-ia-panneau');
    if (!panneau) return;
    if (!panneau.hidden) { panneau.hidden = true; return; }
    const mode = _afIaMode(col.querySelector('.af-champs'));
    const m = await _afIaChargerModeles();
    const opts = (m.modeles || []).map(x => '<option value="' + escAttr(x.id) + '"' + (x.id === m.defaut ? ' selected' : '') + '>' + esc(x.libelle) + '</option>').join('');
    panneau.innerHTML = '<label class="alert-field-label">Consigne</label>'
      + '<div class="af-ia-ex">' + _AF_IA_EXEMPLES[mode].map((t, i) => '<button type="button" data-ex="' + i + '">' + esc(t) + '</button>').join('') + '</div>'
      + '<textarea class="alert-field-input af-ia-consigne" rows="3" maxlength="6000" placeholder="' + escAttr('Ex. ' + _AF_IA_EXEMPLES[mode][0]) + '"></textarea>'
      + '<div class="af-ia-ligne">'
      +   '<label><span class="af-ia-mini">Fiche de contrôle (optionnel)</span><input type="file" class="af-ia-fichiers" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.gif"></label>'
      +   '<label><span class="af-ia-mini">Modèle</span><select class="alert-field-input af-ia-modele">' + opts + '</select></label>'
      + '</div>'
      + '<div class="af-ia-actions"><button type="button" class="btn-sm" onclick="this.closest(\'.af-ia-panneau\').hidden=true">Fermer</button>'
      + '<button type="button" class="af-ia-go" onclick="_afIaGenerer(this)">Générer</button></div>';
    panneau.querySelectorAll('[data-ex]').forEach(b => b.addEventListener('click', () => {
      const t = panneau.querySelector('.af-ia-consigne');
      t.value = _AF_IA_EXEMPLES[mode][+b.getAttribute('data-ex')]; t.focus();
    }));
    panneau.hidden = false;
    requestAnimationFrame(() => panneau.querySelector('.af-ia-consigne')?.focus());
  }

  async function _afIaGenerer(btn) {
    const col = btn.closest('.af-col-form');
    const panneau = col.querySelector('.af-ia-panneau');
    const consigne = (panneau.querySelector('.af-ia-consigne').value || '').trim();
    const fichiers = Array.from(panneau.querySelector('.af-ia-fichiers').files || []);
    if (!consigne && !fichiers.length) { toast('Décrire l\'alerte souhaitée ou joindre une fiche de contrôle.', true); return; }
    if (fichiers.length > 5) { toast('5 documents au plus.', true); return; }
    const trop = fichiers.find(f => f.size > 15 * 1024 * 1024);
    if (trop) { toast('« ' + trop.name + ' » dépasse 15 Mo.', true); return; }
    const nomEl = col.querySelector('#af-nom');
    const nomFixe = col.querySelector('.af-champs .alert-field-input[disabled]');
    const creation = _afIaMode(col.querySelector('.af-champs')) === 'creer';
    const avant = { nom: nomEl ? nomEl.value : '', params: _afLireSilencieux() };
    const fd = new FormData();
    fd.append('consigne', consigne);
    fd.append('nom', nomEl ? nomEl.value : (nomFixe ? nomFixe.value : ''));
    fd.append('params', JSON.stringify(avant.params || {}));
    fd.append('modele', panneau.querySelector('.af-ia-modele')?.value || '');
    fichiers.forEach(f => fd.append('fichiers', f));
    btn.disabled = true; btn.textContent = 'Claude prépare l\'alerte…';
    let p = null;
    try {
      const r = await fetch('/api/maintenance/alerts/ia/proposer', { method: 'POST', body: fd, credentials: 'include' });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) toast((j && typeof j.detail === 'string') ? j.detail : 'Génération impossible.', true);
      else p = j;
    } catch (e) { toast('Erreur réseau', true); }
    btn.disabled = false; btn.textContent = 'Générer';
    if (!p) return;
    panneau.hidden = true;
    _afIaAvant = avant.params ? avant : null;
    _afIaAppliquer(col, p.nom, p.params);
    const note = col.querySelector('.af-ia-note');
    note.innerHTML = '<div><b>Proposition de l\'IA</b> (' + esc(p.modele_libelle || p.modele || '') + ') — à relire avant d\'enregistrer.<br>' + esc(p.resume || '')
      + ((p.remarques || []).length ? '<ul>' + p.remarques.map(r => '<li>' + esc(r) + '</li>').join('') + '</ul>' : '') + '</div>'
      + '<div class="af-ia-note-actions">'
      + (_afIaAvant ? '<button type="button" class="btn-sm" onclick="_afIaAnnuler(this)">Annuler la modification</button>' : '')
      + '<button type="button" class="btn-sm" onclick="this.closest(\'.af-ia-note\').hidden=true">Masquer</button></div>';
    note.hidden = false;
    toast(creation ? 'Alerte proposée — à relire.' : 'Modification appliquée — à relire.');
  }

  // exact : le titre est remis tel quel, même vide (annulation).
  function _afIaAppliquer(col, nom, params, exact) {
    const champs = col.querySelector('.af-champs');
    if (!champs) return;
    const nomEl = col.querySelector('#af-nom');
    const opts = Object.assign({}, _afDernierOpts);
    if (nomEl) opts.nomValue = exact ? (nom || '') : ((nom || '').trim() || nomEl.value);
    const tmp = document.createElement('div');
    tmp.innerHTML = _renderAlertFormFields(params, opts);
    champs.replaceWith(tmp.firstElementChild);
    try { _afOnTriggerChange(); } catch (e) {}
    _afIaMajBouton(col);
  }

  function _afIaAnnuler(btn) {
    const col = btn.closest('.af-col-form');
    if (!col || !_afIaAvant) return;
    _afIaAppliquer(col, _afIaAvant.nom, _afIaAvant.params, true);
    _afIaAvant = null;
    col.querySelector('.af-ia-note').hidden = true;
    toast('Modification annulée.');
  }

  // ── Aperçu opérateur en direct ──
  // Lecture silencieuse du formulaire (aucun toast) : ce qui sert à dessiner
  // la carte chez l'opérateur.
  function _afPreviewParams() {
    const clOn = !!document.getElementById('af-checklist-enabled')?.checked;
    const items = clOn ? Array.from(document.querySelectorAll('.af-cl-card')).map(_afReadCard).filter(Boolean) : [];
    return {
      description: (document.getElementById('af-description')?.value || '').trim(),
      size: document.getElementById('af-size')?.value || 'medium',
      dismiss_button: { enabled: !!document.getElementById('af-dismiss-enabled')?.checked,
                        label: (document.getElementById('af-dismiss-label')?.value || '').trim() || 'Fermer l\'alerte' },
      checklist: { enabled: items.length > 0, items: items },
    };
  }
  // Monte l'aperçu à côté du formulaire dans la fenêtre `overlay` (ou tout
  // conteneur qui porte .alert-modal / .alert-modal-body). Rien n'est envoyé.
  function mount(overlay) {
    _afInjectCss();
    const modal = overlay && (overlay.querySelector('.alert-modal') || overlay);
    const body = modal && modal.querySelector('.alert-modal-body');
    if (!body || body.querySelector('.af-col-form')) return;
    modal.classList.add('af-avec-apercu');
    const col = document.createElement('div');
    col.className = 'af-col-form';
    col.insertAdjacentHTML('afterbegin', _afIaBarreHtml());
    while (body.firstChild) col.appendChild(body.firstChild);
    _afIaAvant = null;
    _afIaMajBouton(col);
    const aside = document.createElement('aside');
    aside.className = 'af-col-apercu';
    aside.innerHTML = '<div class="af-apercu-titre">Aperçu opérateur</div>'
      + '<div class="af-apercu-zone"></div>'
      + '<div class="alert-field-help" style="margin-top:8px">Se met à jour pendant la saisie. Les réponses tapées ici ne sont pas enregistrées.</div>';
    body.classList.add('af-grille');
    body.appendChild(col);
    body.appendChild(aside);
    const zone = aside.querySelector('.af-apercu-zone');
    const nomFixe = (col.querySelector('#af-nom') ? null : (col.querySelector('.alert-field-input[disabled]')?.value || ''));
    let timer = null;
    const dessiner = () => {
      timer = null;
      _afRefreshSummaries();
      if (!window.MysifaAlerts || typeof window.MysifaAlerts.apercu !== 'function') {
        zone.innerHTML = '<div class="alert-field-help">Aperçu indisponible sur cette page.</div>';
        return;
      }
      const nom = nomFixe != null ? nomFixe : ((col.querySelector('#af-nom')?.value || '').trim() || 'Titre de l\'alerte');
      try { window.MysifaAlerts.apercu({ id: 'apercu', nom: nom, params: _afPreviewParams() }, zone); }
      catch (e) { zone.innerHTML = '<div class="alert-field-help">Aperçu indisponible.</div>'; }
    };
    const planifier = () => { if (!timer) timer = setTimeout(() => { dessiner(); _afIaMajBouton(col); }, 120); };
    col.addEventListener('input', planifier);
    col.addEventListener('change', planifier);
    // Ajout, suppression, duplication, glisser, changement de type : la
    // structure des cartes change sans événement de saisie.
    try { new MutationObserver(planifier).observe(col, { childList: true, subtree: true }); } catch (e) {}
    dessiner();
  }

  function _afInjectCss() {
    if (document.getElementById('mysifa-alert-form-css')) return;
    const st = document.createElement('style');
    st.id = 'mysifa-alert-form-css';
    st.textContent = [
      '.af-sec{border:1px solid var(--border);border-radius:10px;margin-top:10px;background:var(--card)}',
      '.af-sec-head{all:unset;box-sizing:border-box;width:100%;display:flex;align-items:center;gap:10px;padding:11px 14px;cursor:pointer;border-radius:10px}',
      '.af-sec-head:hover{background:var(--accent-bg)}',
      '.af-sec-head:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}',
      '.af-sec-titre{font-weight:700;font-size:14px;color:var(--text);flex:0 0 auto}',
      '.af-sec-sum{flex:1;min-width:0;font-size:12px;color:var(--muted);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.af-sec-caret{flex:0 0 auto;color:var(--muted);transition:transform .15s}',
      '.af-sec.open .af-sec-caret{transform:rotate(180deg)}',
      '.af-sec-body{padding:4px 14px 14px}',
      '.af-sec:not(.open) .af-sec-body{display:none}',
      '.af-cl-grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}',
      '.af-ia-barre{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}',
      '.af-ia-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 13px;border-radius:9px;border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);font:inherit;font-size:13px;font-weight:700;cursor:pointer}',
      '.af-ia-btn:hover{filter:brightness(1.05)}',
      '.af-ia-aide{flex:1;min-width:200px;font-size:11px;color:var(--muted)}',
      '.af-ia-panneau{border:1px solid var(--accent);border-radius:10px;padding:12px;margin-bottom:12px;background:var(--bg)}',
      '.af-ia-panneau textarea{resize:vertical;background:var(--card)}',
      '.af-ia-ex{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px}',
      '.af-ia-ex button{padding:5px 10px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--text2);font:inherit;font-size:12px;cursor:pointer;text-align:left}',
      '.af-ia-ex button:hover{border-color:var(--accent);color:var(--accent)}',
      '.af-ia-ligne{display:grid;grid-template-columns:minmax(0,1fr) 200px;gap:10px;margin-top:8px}',
      '.af-ia-ligne label{display:flex;flex-direction:column;gap:4px;min-width:0}',
      '.af-ia-ligne select{background:var(--card)}',
      '.af-ia-mini{font-size:11px;color:var(--muted)}',
      '@media(max-width:600px){.af-ia-ligne{grid-template-columns:minmax(0,1fr)}}',
      '.af-ia-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:10px}',
      '.af-ia-go{padding:8px 16px;border-radius:9px;border:none;background:var(--accent);color:white;font:inherit;font-weight:700;cursor:pointer}',
      '.af-ia-go:disabled{opacity:.6;cursor:wait}',
      '.af-ia-note{display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap;border:1px solid var(--accent);background:var(--accent-bg);border-radius:10px;padding:10px 12px;margin-bottom:12px;font-size:13px;color:var(--text)}',
      '.af-ia-note[hidden],.af-ia-panneau[hidden]{display:none}',
      '.af-ia-note>div:first-child{flex:1;min-width:220px}',
      '.af-ia-note b{color:var(--accent)}',
      '.af-ia-note ul{margin:6px 0 0;padding-left:18px;color:var(--text2);font-size:12px}',
      '.af-ia-note-actions{display:flex;gap:6px;flex-wrap:wrap}',
      '@media(max-width:520px){.af-cl-grid4{grid-template-columns:repeat(2,minmax(0,1fr))}}',
      '.af-cl-poignee{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;width:22px;height:30px;color:var(--muted);cursor:grab;border-radius:6px}',
      '.af-cl-poignee:hover{color:var(--accent);background:var(--accent-bg)}',
      '.af-cl-glisse{opacity:.45;border-style:dashed !important}',
      '.af-cl-dupliquer{flex:0 0 auto;display:inline-flex;align-items:center;background:var(--card);border:1px solid var(--border);color:var(--text2);border-radius:8px;padding:6px 8px;cursor:pointer}',
      '.af-cl-dupliquer:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}',
      '.alert-modal.af-avec-apercu{max-width:1060px}',
      '.af-grille{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:20px;align-items:start}',
      '.af-col-apercu{position:sticky;top:0;padding:12px;border-radius:12px;background:var(--bg);border:1px solid var(--border)}',
      '.af-apercu-titre{font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}',
      '.af-apercu-zone .ta-sim-alert{width:100% !important}',
      '@media(max-width:900px){.af-grille{grid-template-columns:minmax(0,1fr)}.af-col-apercu{position:static}}'
    ].join('\n');
    document.head.appendChild(st);
  }


  // ── _afReadCard ──
  // Lit une carte « point de contrôle » du formulaire. null = carte ignorée
  // (libellé vide, aucune réponse). Sert à l'enregistrement, à la duplication
  // et à l'aperçu.
  function _afReadCard(card) {
      const label = (card.querySelector('.af-cl-label')?.value || '').trim();
      if (!label) return null;
      const type = card.querySelector('.af-cl-type')?.value || 'choice';
      if (type === 'value') {
        const unit = (card.querySelector('.af-cl-unit')?.value || '').trim();
        const minStr = (card.querySelector('.af-cl-min')?.value || '').trim();
        const maxStr = (card.querySelector('.af-cl-max')?.value || '').trim();
        const item = { type: 'value', label: label };
        if (unit) item.unit = unit;
        if (minStr !== '' && !isNaN(parseFloat(minStr))) item.min = parseFloat(minStr);
        if (maxStr !== '' && !isNaN(parseFloat(maxStr))) item.max = parseFloat(maxStr);
        const cibleStr = (card.querySelector('.af-cl-cible')?.value || '').trim();
        if (cibleStr !== '' && !isNaN(parseFloat(cibleStr))) item.target_value = parseFloat(cibleStr);
        if (card.querySelector('.af-cl-oor-nc')?.checked) item.out_of_range_is_nc = true;
        // v2.3.28 : required manquait — les items marqués obligatoires
        // repassaient optionnels à chaque save via /maintenance.
        if (card.querySelector('.af-cl-required')?.checked) item.required = true;
        const ph = (card.querySelector('.af-cl-placeholder')?.value || '').trim();
        if (ph) item.placeholder = ph;
        if (card.querySelector('.af-cl-points-toggle')?.checked) {
          const pts = _afPoints(card.querySelector('.af-cl-points')?.value || '');
          if (pts.length > 1) item.points = pts;
        }
        const helpV = (card.querySelector('.af-cl-help')?.value || '').trim();
        if (helpV) item.help = helpV;
        return item;
      }
      const responses = [];
      const ncResponses = [];
      // v2.5.21 : comResponses = réponses cochées COM (commentaire obligatoire)
      const comResponses = [];
      card.querySelectorAll('.af-cl-resp-row').forEach(row => {
        const r = (row.querySelector('.af-cl-resp-input')?.value || '').trim();
        if (!r) return;
        responses.push(r);
        if (row.querySelector('.af-cl-resp-nc')?.checked) ncResponses.push(r);
        if (row.querySelector('.af-cl-resp-com')?.checked) comResponses.push(r);
      });
      if (!responses.length) return null;
      const multiSel = card.querySelector('.af-cl-multi-sel')?.value;
      const multi = (multiSel === 'single') ? false : true;
      const allowOther = !!card.querySelector('.af-cl-other-toggle')?.checked;
      const otherIsNc = allowOther && !!card.querySelector('.af-cl-other-nc')?.checked;
      const otherNeedsComment = allowOther && !!card.querySelector('.af-cl-other-com')?.checked;
      // v2.3.28 : required manquait — les items requis repassaient
      // optionnels à chaque save via /maintenance.
      const _reqCk = !!card.querySelector('.af-cl-required')?.checked;
      const _choiceItem = { type: 'choice', label: label, responses: responses, multi: multi, allow_other: allowOther, other_is_nc: otherIsNc, nc_responses: ncResponses, comment_responses: comResponses, other_needs_comment: otherNeedsComment };
      if (_reqCk) _choiceItem.required = true;
      const _helpC = (card.querySelector('.af-cl-help')?.value || '').trim();
      if (_helpC) _choiceItem.help = _helpC;
      return _choiceItem;
  }


  // ── _afReadParams ──
  function _afReadParams() {
  // v2.3.33 : force l'ouverture de la section Paramètres pour que les
  // erreurs de validation portant sur des champs cachés soient visibles.
  try { _afOpenSettings(); } catch(_) {}
  const t = document.getElementById('af-trigger-type').value || 'periodic';
  const trig = { type: t };
  // v2.5.6 : garde-fou — le type obsolète ne peut pas être (re)choisi
  // volontairement ; il n'est présent dans le select que pour les alertes
  // historiques, et sauvegarder dans cet état laisserait l'alerte muette.
  if (t === 'manual') {
    toast('Choisis un déclencheur : « Manuel » est supprimé et ne déclenche rien.', true);
    return null;
  }
  if (t === 'periodic') {
    const mInp = document.getElementById('af-trigger-interval-minutes');
    const m = parseInt(mInp.value, 10);
    if (!(m >= 1 && m <= 10080)) { toast('Intervalle invalide (1 ≤ minutes ≤ 10080)', true); return null; }
    trig.interval_minutes = m;
    const gInp = document.getElementById('af-trigger-grace-minutes');
    if (gInp) {
      const g = parseInt(gInp.value, 10);
      if (isNaN(g) || g < 0 || g > 120) { toast('Délai avant 1ère alerte invalide (0 à 120 min)', true); return null; }
      trig.grace_minutes = g;
    }
  } else if (t === 'calendar') {
    const tm = document.getElementById('af-trigger-time').value || '';
    if (!/^\d{2}:\d{2}$/.test(tm)) { toast('Heure invalide (HH:MM)', true); return null; }
    trig.time = tm;
    const days = Array.from(document.querySelectorAll('.af-day:checked')).map(el => el.value);
    if (!days.length) { toast('Au moins un jour requis', true); return null; }
    trig.days = days;
  } else if (t === 'event') {
    trig.event = document.getElementById('af-trigger-event').value || 'dossier_start';
    // v2.2.42 : filter_conditionnement (Filtre produit) retiré.
    delete trig.filter_conditionnement;
  }
  // Lecture du questionnaire (cartes : label + réponses possibles)
  const clEnabled = !!document.getElementById('af-checklist-enabled')?.checked;
  const items = [];
  if (clEnabled) {
    document.querySelectorAll('.af-cl-card').forEach(card => {
      const it = _afReadCard(card);
      if (it) items.push(it);
    });
  }
  // Cible (lue en premier — interrompt si rien sélectionné)
  let _tgt;
  {
    const all = !!document.getElementById('af-target-all')?.checked;
    if (all) {
      _tgt = { machines: ['*'] };
    } else {
      const ms = Array.from(document.querySelectorAll('.af-machine:checked')).map(el => el.value);
      if (!ms.length) { toast('Sélectionne au moins une machine', true); return null; }
      _tgt = { machines: ms };
    }
  }
  const descEl = document.getElementById('af-description');
  const descVal = descEl ? (descEl.value || '').trim() : '';
  return {
    description: descVal.slice(0, 800),
    trigger: trig,
    target: _tgt,
    // v2.3.33 : validation.button_label figée à 'Valider' côté backend,
    // plus de champ front. On garde l'objet pour éviter un 422 sur rétro-compat.
    validation: {},
    // v2.3.21 : placement + size par alerte (dans maintenance_page.py aussi)
    placement: (document.getElementById('af-placement')?.value || 'top-right'),
    size: (document.getElementById('af-size')?.value || 'medium'),
    // v2.3.22 : block_production par alerte — sinon la valeur en base est écrasée à False à chaque save via /maintenance
    block_production: !!document.getElementById('af-block-production')?.checked,
    dismiss_button: (function(){
      const en = !!document.getElementById('af-dismiss-enabled')?.checked;
      if(!en) return { enabled: false, label: '' };
      const lbl = (document.getElementById('af-dismiss-label').value || 'Fermer l\'alerte').trim() || 'Fermer l\'alerte';
      return { enabled: true, label: lbl };
    })(),
    checklist: {
      enabled: clEnabled && items.length > 0,
      items: items,
    },
  };
}


  // ── _afPoints ──
  // Libellés des mesures d'un point « Valeur à saisir » : liste ou texte
  // séparé par « / ». Moins de deux libellés = une seule valeur.
  const _AF_POINTS_DEFAUT = ['Début de prod', 'Milieu de prod', 'Fin de prod'];
  function _afPoints(v) {
    const arr = Array.isArray(v) ? v : (typeof v === 'string' ? v.split('/') : []);
    const out = arr.map(x => String(x == null ? '' : x).trim().slice(0, 40)).filter(Boolean).slice(0, 10);
    return out.length > 1 ? out : [];
  }

  function _afOnPointsToggle(cb) {
    const wrap = cb.closest('.af-cl-body')?.querySelector('.af-cl-points-wrap');
    if (wrap) wrap.style.display = cb.checked ? 'block' : 'none';
  }


  // ── _afOnTypeChange ──
  function _afOnTypeChange(sel) {
  const card = sel.closest('.af-cl-card');
  if (!card) return;
  const oldBody = card.querySelector('.af-cl-body');
  if (!oldBody) return;
  const newType = sel.value;
  const defaultItem = (newType === 'value')
    ? { type: 'value', label: '', unit: '', min: null, max: null }
    : { type: 'choice', label: '', responses: ['Conforme'], multi: true, allow_other: false };
  const tmp = document.createElement('div');
  tmp.innerHTML = _afChecklistCardBody(defaultItem);
  const newBody = tmp.firstElementChild;
  if (newBody) oldBody.replaceWith(newBody);
}


  // ── _afOnTriggerChange ──
  function _afOnTriggerChange() {
  const t = document.getElementById('af-trigger-type')?.value || 'periodic';
  document.querySelectorAll('#af-trigger-sub > [data-trigger-for]').forEach(el => {
    el.style.display = (el.getAttribute('data-trigger-for') === t) ? '' : 'none';
  });
}


  // ── _afOnTriggerEventChange ──
  function _afOnTriggerEventChange() { /* no-op */ }

function _afRowClick(ev, inputId) {
  // Click n'importe où sur la ligne → toggle l'input. On ignore le click direct
  // sur l'input pour éviter le double toggle (l'input gère son propre click).
  if (ev.target.tagName === 'INPUT') return;
  const inp = document.getElementById(inputId);
  if (!inp || inp.disabled) return;
  inp.checked = !inp.checked;
  inp.dispatchEvent(new Event('change', { bubbles: true }));
}


  // ── _afOnChecklistToggle ──
  function _afOnChecklistToggle() {
  const enabled = document.getElementById('af-checklist-enabled')?.checked;
  const wrap = document.getElementById('af-checklist-wrap');
  if (wrap) wrap.style.display = enabled ? '' : 'none';
  if (enabled) {
    const cards = document.querySelectorAll('.af-cl-card');
    if (!cards.length) _afAddChecklistItem();
  }
}


  // ── _afOnDismissToggle ──
  function _afOnDismissToggle() {
  const en = document.getElementById('af-dismiss-enabled')?.checked;
  const wrap = document.getElementById('af-dismiss-wrap');
  if (wrap) wrap.style.display = en ? '' : 'none';
}


  // ── _afOnMachineChange ──
  function _afOnMachineChange() {
  const allChk = document.getElementById('af-target-all');
  if (allChk && allChk.checked) {
    const anyIndividual = Array.from(document.querySelectorAll('.af-machine:checked')).length > 0;
    if (anyIndividual) allChk.checked = false;
  }
  _afUpdateMachinesLabel();
}


  // ── _afOnAllMachinesToggle ──
  function _afOnAllMachinesToggle() {
  const allChk = document.getElementById('af-target-all');
  if (!allChk) return;
  document.querySelectorAll('.af-machine').forEach(el => {
    el.disabled = allChk.checked;
    if (allChk.checked) el.checked = false;
    const row = el.closest('.af-md-row');
    if (row) row.classList.toggle('is-disabled', allChk.checked);
  });
  _afUpdateMachinesLabel();
}


  // ── _afOnOtherToggle ──
  function _afOnOtherToggle(cb){
  const body = cb.closest('.af-cl-body');
  if(!body) return;
  // v2.5.21 : les deux sous-options d'« Autre » (NC et commentaire obligatoire)
  // suivent le même sort — affichées avec « Autre », décochées quand il part,
  // pour ne pas laisser un flag actif sur une réponse qui n'existe plus.
  [['.af-cl-other-nc-lbl', '.af-cl-other-nc'],
   ['.af-cl-other-com-lbl', '.af-cl-other-com']].forEach(function(pair){
    const lbl = body.querySelector(pair[0]);
    if(!lbl) return;
    if(cb.checked){ lbl.style.display = 'flex'; return; }
    lbl.style.display = 'none';
    const inp = lbl.querySelector(pair[1]);
    if(inp) inp.checked = false;
  });
}


  // ── _afToggleMachinesPanel ──
  function _afToggleMachinesPanel(ev) {
  if (ev) ev.stopPropagation();
  const panel = document.getElementById('af-md-panel');
  if (!panel) return;
  panel.classList.toggle('open');
}


  // ── _afRowClick ──
  function _afRowClick(ev, inputId) {
  // Click n'importe où sur la ligne → toggle l'input. On ignore le click direct
  // sur l'input pour éviter le double toggle (l'input gère son propre click).
  if (ev.target.tagName === 'INPUT') return;
  const inp = document.getElementById(inputId);
  if (!inp || inp.disabled) return;
  inp.checked = !inp.checked;
  inp.dispatchEvent(new Event('change', { bubbles: true }));
}


  // ── _afRowClickByValue ──
  function _afRowClickByValue(ev, value) {
  if (ev.target.tagName === 'INPUT') return;
  const row = ev.currentTarget;
  const inp = row.querySelector('input.af-machine');
  if (!inp || inp.disabled) return;
  inp.checked = !inp.checked;
  inp.dispatchEvent(new Event('change', { bubbles: true }));
}


  // ── _afUpdateMachinesLabel ──
  function _afUpdateMachinesLabel() {
  const lbl = document.getElementById('af-md-label');
  if (!lbl) return;
  const all = !!document.getElementById('af-target-all')?.checked;
  lbl.style.color = '';
  if (all) { lbl.textContent = 'Toutes les machines'; return; }
  const selected = Array.from(document.querySelectorAll('.af-machine:checked')).map(el => el.value);
  if (!selected.length) {
    lbl.textContent = 'Aucune machine sélectionnée';
    lbl.style.color = 'var(--danger)';
    return;
  }
  if (selected.length === 1) lbl.textContent = selected[0];
  else if (selected.length <= 3) lbl.textContent = selected.join(', ');
  else lbl.textContent = selected.length + ' machines';
}


  // ── _afToggleSettings / _afOpenSettings ──
  // Compat : l'ancien bloc « Paramètres » est devenu quatre sections.
  // _afReadParams ouvre tout, pour que l'erreur signalée soit visible.
  function _afToggleSettings(){
  const secs = Array.from(document.querySelectorAll('.af-sec:not([data-sec="questionnaire"])'));
  const open = !secs.every(sec => sec.classList.contains('open'));
  secs.forEach(sec => sec.classList.toggle('open', open));
}
  function _afOpenSettings(){
  _afOpenSection(null);
}

  // ─────────────────────────────────────────────────────────
  // Expose tout sur window pour compat onclick="..." inline
  // ─────────────────────────────────────────────────────────
  try { window._alertDefaults = _alertDefaults; } catch(e) {}
  try { window._alertIsConfigured = _alertIsConfigured; } catch(e) {}
  try { window._alertTriggerLabel = _alertTriggerLabel; } catch(e) {}
  try { window._renderAlertFormFields = _renderAlertFormFields; } catch(e) {}
  try { window._afChecklistCard = _afChecklistCard; } catch(e) {}
  try { window._afChecklistCardBody = _afChecklistCardBody; } catch(e) {}
  try { window._afRenderChecklistItems = _afRenderChecklistItems; } catch(e) {}
  try { window._afAddChecklistItem = _afAddChecklistItem; } catch(e) {}
  try { window._afRemoveItem = _afRemoveItem; } catch(e) {}
  try { window._afResponseRow = _afResponseRow; } catch(e) {}
  try { window._afAddResponse = _afAddResponse; } catch(e) {}
  try { window._afRemoveResponse = _afRemoveResponse; } catch(e) {}
  try { window._afReadParams = _afReadParams; } catch(e) {}
  try { window._afOnTypeChange = _afOnTypeChange; } catch(e) {}
  try { window._afOnTriggerChange = _afOnTriggerChange; } catch(e) {}
  try { window._afOnTriggerEventChange = _afOnTriggerEventChange; } catch(e) {}
  try { window._afOnChecklistToggle = _afOnChecklistToggle; } catch(e) {}
  try { window._afOnDismissToggle = _afOnDismissToggle; } catch(e) {}
  try { window._afOnMachineChange = _afOnMachineChange; } catch(e) {}
  try { window._afOnAllMachinesToggle = _afOnAllMachinesToggle; } catch(e) {}
  try { window._afOnOtherToggle = _afOnOtherToggle; } catch(e) {}
  try { window._afOnPointsToggle = _afOnPointsToggle; } catch(e) {}
  try { window._afToggleSection = _afToggleSection; } catch(e) {}
  try { window._afIaOuvrir = _afIaOuvrir; } catch(e) {}
  try { window._afIaGenerer = _afIaGenerer; } catch(e) {}
  try { window._afIaAnnuler = _afIaAnnuler; } catch(e) {}
  try { window._afDuplicateItem = _afDuplicateItem; } catch(e) {}
  try { window._afArmDrag = _afArmDrag; } catch(e) {}
  try { window._afDisarmDrag = _afDisarmDrag; } catch(e) {}
  try { window._afDragStart = _afDragStart; } catch(e) {}
  try { window._afDragEnd = _afDragEnd; } catch(e) {}
  try { window._afDragOver = _afDragOver; } catch(e) {}
  try { window._afToggleMachinesPanel = _afToggleMachinesPanel; } catch(e) {}
  try { window._afRowClick = _afRowClick; } catch(e) {}
  try { window._afRowClickByValue = _afRowClickByValue; } catch(e) {}
  try { window._afUpdateMachinesLabel = _afUpdateMachinesLabel; } catch(e) {}
  try { window._afToggleSettings = _afToggleSettings; } catch(e) {}
  try { window._afOpenSettings = _afOpenSettings; } catch(e) {}
  try { window._daysLabel = _daysLabel; } catch(e) {}
  try { window._triggerOptsFor = _triggerOptsFor; } catch(e) {}
  try { window._isLegacyTriggerType = _isLegacyTriggerType; } catch(e) {}
  try { window._ALERT_TRIGGER_TYPES = _ALERT_TRIGGER_TYPES; } catch(e) {}
  try { window._ALERT_TRIGGER_EVENTS = _ALERT_TRIGGER_EVENTS; } catch(e) {}
  try { window._ALERT_MACHINES = _ALERT_MACHINES; } catch(e) {}
  try { window._ALERT_ROLES = _ALERT_ROLES; } catch(e) {}
  try { window._ALERT_DAYS = _ALERT_DAYS; } catch(e) {}

  window.MysifaAlertForm = {
    mount: mount,
    _afReadCard: _afReadCard,
    _alertDefaults: _alertDefaults,
    _alertIsConfigured: _alertIsConfigured,
    _alertTriggerLabel: _alertTriggerLabel,
    _renderAlertFormFields: _renderAlertFormFields,
    _afChecklistCard: _afChecklistCard,
    _afChecklistCardBody: _afChecklistCardBody,
    _afRenderChecklistItems: _afRenderChecklistItems,
    _afAddChecklistItem: _afAddChecklistItem,
    _afRemoveItem: _afRemoveItem,
    _afResponseRow: _afResponseRow,
    _afAddResponse: _afAddResponse,
    _afRemoveResponse: _afRemoveResponse,
    _afReadParams: _afReadParams,
    _afOnTypeChange: _afOnTypeChange,
    _afOnTriggerChange: _afOnTriggerChange,
    _afOnTriggerEventChange: _afOnTriggerEventChange,
    _afOnChecklistToggle: _afOnChecklistToggle,
    _afOnDismissToggle: _afOnDismissToggle,
    _afOnMachineChange: _afOnMachineChange,
    _afOnAllMachinesToggle: _afOnAllMachinesToggle,
    _afOnOtherToggle: _afOnOtherToggle,
    _afToggleMachinesPanel: _afToggleMachinesPanel,
    _afRowClick: _afRowClick,
    _afRowClickByValue: _afRowClickByValue,
    _afUpdateMachinesLabel: _afUpdateMachinesLabel,
    _afToggleSettings: _afToggleSettings,
    _afOpenSettings: _afOpenSettings,
    _daysLabel: _daysLabel,
    _triggerOptsFor: _triggerOptsFor,
    _isLegacyTriggerType: _isLegacyTriggerType,
    _ALERT_TRIGGER_TYPES: _ALERT_TRIGGER_TYPES,
    _ALERT_TRIGGER_EVENTS: _ALERT_TRIGGER_EVENTS,
    _ALERT_MACHINES: _ALERT_MACHINES,
    _ALERT_ROLES: _ALERT_ROLES,
    _ALERT_DAYS: _ALERT_DAYS
  };
})();
