/**
 * MySifa — préférences d'apparence partagées (palette, style, mode clair/sombre).
 * Clés localStorage : mysifa_palette, mysifa_style, theme (mode).
 */
(function (global) {
  'use strict';

  var LS_PALETTE = 'mysifa_palette';
  var LS_STYLE = 'mysifa_style';
  var LS_MODE = 'theme';

  var PALETTES = ['mysifa', 'ambre', 'pivoine', 'foret', 'cendre', 'braise'];
  var STYLES = ['defaut', 'mini', 'round'];
  // Conserver les anciennes classes (forge/cocon) pour compatibilité.
  var THEME_CLASSES = ['light', 'palette-ambre', 'palette-pivoine', 'palette-forge', 'palette-cocon', 'palette-foret', 'palette-cendre', 'palette-braise', 'style-mini', 'style-round'];

  function normalizePalette(p) {
    // Alias pour rétrocompatibilité (anciennes prefs)
    if (p === 'forge') p = 'ambre';
    if (p === 'cocon') p = 'pivoine';
    return PALETTES.indexOf(p) >= 0 ? p : 'mysifa';
  }

  function normalizeStyle(s) {
    return STYLES.indexOf(s) >= 0 ? s : 'defaut';
  }

  function loadPrefs() {
    try {
      return {
        palette: normalizePalette(localStorage.getItem(LS_PALETTE) || 'mysifa'),
        style: normalizeStyle(localStorage.getItem(LS_STYLE) || 'defaut'),
        mode: localStorage.getItem(LS_MODE) === 'light' ? 'light' : 'dark',
      };
    } catch (e) {
      return { palette: 'mysifa', style: 'defaut', mode: 'dark' };
    }
  }

  function savePrefs(prefs) {
    try {
      localStorage.setItem(LS_PALETTE, normalizePalette(prefs.palette));
      localStorage.setItem(LS_STYLE, normalizeStyle(prefs.style));
      localStorage.setItem(LS_MODE, prefs.mode === 'light' ? 'light' : 'dark');
    } catch (e) { /* ignore */ }
  }

  function clearThemeClasses(el) {
    if (!el) return;
    THEME_CLASSES.forEach(function (c) {
      el.classList.remove(c);
    });
  }

  function applyPrefs(prefs) {
    prefs = prefs || loadPrefs();
    prefs = {
      palette: normalizePalette(prefs.palette),
      style: normalizeStyle(prefs.style),
      mode: prefs.mode === 'light' ? 'light' : 'dark',
    };

    var targets = [document.documentElement];
    if (document.body) targets.push(document.body);

    targets.forEach(function (el) {
      clearThemeClasses(el);
      if (prefs.mode === 'light') el.classList.add('light');
      if (prefs.palette !== 'mysifa') el.classList.add('palette-' + prefs.palette);
      if (prefs.style !== 'defaut') el.classList.add('style-' + prefs.style);
    });

    return prefs;
  }

  function isLight() {
    return loadPrefs().mode === 'light';
  }

  function toggleMode() {
    var prefs = loadPrefs();
    prefs.mode = prefs.mode === 'light' ? 'dark' : 'light';
    savePrefs(prefs);
    applyPrefs(prefs);
    return prefs;
  }

  function setPrefs(partial, opts) {
    var prefs = loadPrefs();
    if (partial && partial.palette != null) prefs.palette = normalizePalette(partial.palette);
    if (partial && partial.style != null) prefs.style = normalizeStyle(partial.style);
    if (partial && partial.mode != null) prefs.mode = partial.mode === 'light' ? 'light' : 'dark';
    savePrefs(prefs);
    applyPrefs(prefs);
    if (opts && opts.syncServer) syncToServer(prefs);
    return prefs;
  }

  function parseThemePrefs(raw) {
    if (!raw) return null;
    try {
      var tp = typeof raw === 'string' ? JSON.parse(raw) : raw;
      if (!tp || typeof tp !== 'object') return null;
      var out = {};
      if (tp.palette != null) out.palette = normalizePalette(tp.palette);
      if (tp.style != null) out.style = normalizeStyle(tp.style);
      if (tp.mode === 'light' || tp.mode === 'dark') out.mode = tp.mode;
      return out;
    } catch (e) {
      return null;
    }
  }

  function mergeFromUser(user) {
    if (!user || user.theme_prefs == null) return loadPrefs();
    var sp = parseThemePrefs(user.theme_prefs);
    if (!sp) return loadPrefs();
    var prefs = loadPrefs();
    if (sp.palette != null) prefs.palette = sp.palette;
    if (sp.style != null) prefs.style = sp.style;
    if (sp.mode != null) prefs.mode = sp.mode;
    savePrefs(prefs);
    applyPrefs(prefs);
    if (global.MySifaCalendar && typeof global.MySifaCalendar.mergeFromUser === 'function') {
      global.MySifaCalendar.mergeFromUser(user);
    }
    return prefs;
  }

  function themePrefsPayload(prefs) {
    prefs = prefs || loadPrefs();
    var tp = {
      palette: prefs.palette,
      style: prefs.style,
      mode: prefs.mode,
    };
    if (global.MySifaCalendar && typeof global.MySifaCalendar.buildThemePrefsPayload === 'function') {
      return global.MySifaCalendar.buildThemePrefsPayload(tp);
    }
    return tp;
  }

  function syncToServer(prefs) {
    return fetch('/api/auth/me', {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme_prefs: themePrefsPayload(prefs) }),
    }).catch(function () {});
  }

  function initFromStorage() {
    return applyPrefs(loadPrefs());
  }

  global.MySifaTheme = {
    loadPrefs: loadPrefs,
    savePrefs: savePrefs,
    applyPrefs: applyPrefs,
    initFromStorage: initFromStorage,
    isLight: isLight,
    toggleMode: toggleMode,
    setPrefs: setPrefs,
    mergeFromUser: mergeFromUser,
    syncToServer: syncToServer,
    themePrefsPayload: themePrefsPayload,
    parseThemePrefs: parseThemePrefs,
  };

  if (document.body) {
    initFromStorage();
  } else {
    document.addEventListener('DOMContentLoaded', initFromStorage);
  }
})(typeof window !== 'undefined' ? window : this);
