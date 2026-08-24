/**
 * MySifa — couleurs des calendriers (MyCalendrier), stockées dans theme_prefs.calendar_colors.
 */
(function (global) {
  'use strict';

  var LS_CAL_COLORS = 'mysifa_cal_colors';
  var HEX_RE = /^#[0-9A-Fa-f]{6}$/;

  /* L'ordre de ce tableau est celui de la liste des calendriers : « Mon
   * calendrier » d'abord, le reste sous le chevron « Autres calendriers ».
   * `defaut: false` = calendrier décoché à la première ouverture — les
   * plannings machines, la paie et les expéditions encombrent la vue de
   * quelqu'un qui vient y chercher ses réunions. */
  var CAL_DEFS = [
    { id: 'perso', label: 'Mon calendrier', color: '#f97316', mien: true },
    { id: 'collegues', label: 'Collègues', color: '#38bdf8' },
    { id: 'conges', label: 'Congés', color: '#fbbf24' },
    { id: 'anniversaires', label: 'Anniversaires', color: '#34d399' },
    { id: 'feries', label: 'Jours fériés', color: '#f87171' },
    { id: 'paie', label: 'Paie', color: '#a78bfa', defaut: false },
    { id: 'expeditions', label: 'Expéditions', color: '#f97316', defaut: false },
    { id: 'production_1', label: 'Cohésio 1', color: '#22d3ee', defaut: false },
    { id: 'production_2', label: 'Cohésio 2', color: '#3A7BD5', defaut: false },
    { id: 'production_3', label: 'DSI', color: '#a78bfa', defaut: false },
    { id: 'production_4', label: 'Repiquage', color: '#34d399', defaut: false },
  ];

  function visibleParDefaut(calId) {
    var c = CAL_DEFS.find(function (x) { return x.id === calId; });
    return !c || c.defaut !== false;
  }

  function defaultColorsMap() {
    var o = {};
    CAL_DEFS.forEach(function (c) {
      o[c.id] = c.color;
    });
    return o;
  }

  function validHex(h) {
    return typeof h === 'string' && HEX_RE.test(h);
  }

  function normalizeColorsMap(partial) {
    var base = defaultColorsMap();
    var out = {};
    CAL_DEFS.forEach(function (c) {
      var v = partial && partial[c.id];
      out[c.id] = validHex(v) ? v : base[c.id];
    });
    return out;
  }

  function loadColorsMap() {
    try {
      var raw = localStorage.getItem(LS_CAL_COLORS);
      if (raw) return normalizeColorsMap(JSON.parse(raw));
    } catch (e) { /* ignore */ }
    return defaultColorsMap();
  }

  function saveColorsLocal(map) {
    try {
      localStorage.setItem(LS_CAL_COLORS, JSON.stringify(map));
    } catch (e) { /* ignore */ }
  }

  function applyColorsToDefs(map) {
    map = map || loadColorsMap();
    CAL_DEFS.forEach(function (c) {
      if (map[c.id]) c.color = map[c.id];
    });
    return map;
  }

  function parseThemePrefsRaw(raw) {
    if (!raw) return null;
    try {
      return typeof raw === 'string' ? JSON.parse(raw) : raw;
    } catch (e) {
      return null;
    }
  }

  function parseCalendarColorsFromThemePrefs(raw) {
    var tp = parseThemePrefsRaw(raw);
    if (!tp || !tp.calendar_colors || typeof tp.calendar_colors !== 'object') return null;
    return normalizeColorsMap(tp.calendar_colors);
  }

  function mergeFromUser(user) {
    var fromServer = user && parseCalendarColorsFromThemePrefs(user.theme_prefs);
    if (fromServer) {
      saveColorsLocal(fromServer);
      applyColorsToDefs(fromServer);
      return fromServer;
    }
    applyColorsToDefs(loadColorsMap());
    return loadColorsMap();
  }

  function setColor(calId, hex) {
    if (!CAL_DEFS.some(function (c) { return c.id === calId; })) return null;
    if (!validHex(hex)) return null;
    var map = loadColorsMap();
    map[calId] = hex;
    saveColorsLocal(map);
    var def = CAL_DEFS.find(function (c) { return c.id === calId; });
    if (def) def.color = hex;
    return map;
  }

  function resetColor(calId) {
    var base = defaultColorsMap();
    return setColor(calId, base[calId]);
  }

  function colorFor(id) {
    var c = CAL_DEFS.find(function (x) { return x.id === id; });
    return c ? c.color : '#22d3ee';
  }

  function getColorsForServer() {
    return loadColorsMap();
  }

  function profilUrl(calId) {
    return '/profil?tab=calendrier#cal-' + encodeURIComponent(calId);
  }

  function buildThemePrefsPayload(themePrefs) {
    themePrefs = themePrefs || {};
    var out = {};
    if (themePrefs.palette != null) out.palette = themePrefs.palette;
    if (themePrefs.style != null) out.style = themePrefs.style;
    if (themePrefs.mode != null) out.mode = themePrefs.mode;
    if (themePrefs.bg_anim != null) out.bg_anim = !!themePrefs.bg_anim;
    else if (themePrefs.bgAnim != null) out.bg_anim = !!themePrefs.bgAnim;
    out.calendar_colors = getColorsForServer();
    return out;
  }

  applyColorsToDefs(loadColorsMap());

  global.MySifaCalendar = {
    CAL_DEFS: CAL_DEFS,
    visibleParDefaut: visibleParDefaut,
    defaultColorsMap: defaultColorsMap,
    loadColorsMap: loadColorsMap,
    mergeFromUser: mergeFromUser,
    setColor: setColor,
    resetColor: resetColor,
    colorFor: colorFor,
    getColorsForServer: getColorsForServer,
    profilUrl: profilUrl,
    validHex: validHex,
    buildThemePrefsPayload: buildThemePrefsPayload,
    parseCalendarColorsFromThemePrefs: parseCalendarColorsFromThemePrefs,
  };
})(typeof window !== 'undefined' ? window : this);
