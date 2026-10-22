/* MyTools › Étiquettes spécifiques — moteur (logique pure, sans DOM).
 *
 * Formules et conditions, dates calculées, GS1 (AI, clé, SSCC), valeurs d'une
 * étiquette, lecture d'un CSV ou d'un collage Excel, contrôles de lisibilité,
 * étiquette logistique palette. Chargé dans la page (window.EtiqMoteur) et
 * dans node pour les tests (tests/test_etiq_moteur.js).
 *
 * MIROIR de app/services/etiq_formules.py et etiq_gs1.py : l'aperçu (ici) et
 * l'impression (serveur) doivent sortir la même valeur. Les deux rejouent
 * tests/etiq_formules_cas.json. Évaluateur sûr : analyseur à descente
 * récursive sur une grammaire fermée, jamais d'eval ni de Function.
 */
(function (racine, fabrique) {
  const M = fabrique();
  if (typeof module === 'object' && module.exports) module.exports = M;
  else racine.EtiqMoteur = M;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const LONGUEUR_MAX = 1000, SORTIE_MAX = 2000, PROFONDEUR_MAX = 60;
  class ErreurFormule extends Error {}

  // ── Valeurs ─────────────────────────────────────────────────────────
  const NOMBRE_RE = /^-?\d+(\.\d+)?$/;
  function nombre(v) {
    if (typeof v === 'boolean') return v ? 1 : 0;
    if (typeof v === 'number') return v;
    const s = String(v == null ? '' : v).replace(/ /g, '').replace(/ /g, '').replace(/,/g, '.');
    if (!NOMBRE_RE.test(s)) throw new ErreurFormule('« ' + String(v == null ? '' : v).slice(0, 30) + ' » n\'est pas un nombre.');
    return parseFloat(s);
  }
  function estNombre(v) {
    if (typeof v === 'number') return true;
    if (typeof v === 'string' && v.trim()) { try { nombre(v); return true; } catch (e) { return false; } }
    return false;
  }
  function texte(v) {
    if (typeof v === 'boolean') return v ? 'VRAI' : 'FAUX';
    if (typeof v === 'number') {
      if (!isFinite(v)) throw new ErreurFormule('Résultat numérique invalide.');
      if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
      return v.toFixed(10).replace(/0+$/, '').replace(/\.$/, '').replace('.', ',');
    }
    return v == null ? '' : String(v);
  }
  function vrai(v) {
    if (typeof v === 'boolean') return v;
    if (typeof v === 'number') return v !== 0;
    const s = String(v == null ? '' : v).trim();
    return !!s && s !== '0' && s.toUpperCase() !== 'FAUX';
  }
  // Arrondi au plus proche, moitié vers l'extérieur (comme Decimal ROUND_HALF_UP)
  function arrondi(x, n) {
    n = parseInt(n || 0, 10);
    const sgn = x < 0 ? -1 : 1, ax = Math.abs(x);
    const r = /e/i.test(String(ax)) ? Math.round(ax * Math.pow(10, n)) / Math.pow(10, n)
      : Number(Math.round(Number(ax + 'e' + n)) + 'e-' + n);
    return sgn * r;
  }

  // ── Analyse lexicale ────────────────────────────────────────────────
  const JETON = /\s+|\{\{\s*[A-Za-z_][A-Za-z0-9_]*\s*\}\}|\d+(?:\.\d+)?|"(?:[^"]|"")*"|'(?:[^']|'')*'|[A-Za-z_][A-Za-z0-9_]*|<=|>=|<>|!=|[=<>+\-*/&(),;]/y;
  function jetons(expr) {
    const out = [];
    let i = 0;
    while (i < expr.length) {
      JETON.lastIndex = i;
      const m = JETON.exec(expr);
      if (!m) throw new ErreurFormule('Caractère inattendu « ' + expr[i] + ' » (position ' + (i + 1) + ').');
      i = JETON.lastIndex;
      const v = m[0];
      if (/^\s+$/.test(v)) continue;
      if (v.startsWith('{{')) out.push(['nom', v.replace(/[{}\s]/g, '').toLowerCase(), true]);
      else if (/^\d/.test(v)) out.push(['nombre', parseFloat(v), false]);
      else if (v[0] === '"' || v[0] === "'") out.push(['chaine', v.slice(1, -1).split(v[0] + v[0]).join(v[0]), false]);
      else if (/^[A-Za-z_]/.test(v)) out.push(['nom', v, false]);
      else out.push(['op', v === ',' ? ';' : v, false]);
    }
    out.push(['fin', null, false]);
    return out;
  }

  // ── Fonctions ───────────────────────────────────────────────────────
  function fZeros(x, n) {
    const s = texte(x), signe = s.startsWith('-') ? '-' : '';
    return signe + s.replace(/^-+/, '').padStart(parseInt(nombre(n), 10), '0');
  }
  function fTexte(x, n) {
    n = Math.max(0, Math.min(10, parseInt(nombre(n == null ? 0 : n), 10)));
    return arrondi(nombre(x), n).toFixed(n).replace('.', ',');
  }
  function fCleGs1(t) {
    const ch = texte(t).replace(/\D/g, '');
    if (!ch) throw new ErreurFormule('CLE_GS1 : chiffres attendus.');
    return cleGs1(ch);
  }
  const ent = (n) => parseInt(nombre(n), 10);
  const FONCTIONS = {
    MAJUSCULE: [1, 1, t => texte(t).toUpperCase()],
    MAJ: [1, 1, t => texte(t).toUpperCase()],
    MINUSCULE: [1, 1, t => texte(t).toLowerCase()],
    CONCAT: [1, null, (...a) => a.map(texte).join('')],
    GAUCHE: [1, 2, (t, n = 1) => texte(t).slice(0, Math.max(0, ent(n)))],
    DROITE: [1, 2, (t, n = 1) => (ent(n) > 0 ? texte(t).slice(-ent(n)) : '')],
    STXT: [3, 3, (t, d, n) => { const dd = Math.max(1, ent(d)); return texte(t).slice(dd - 1, dd - 1 + Math.max(0, ent(n))); }],
    LONGUEUR: [1, 1, t => texte(t).length],
    SUPPRESPACE: [1, 1, t => texte(t).split(/\s+/).filter(Boolean).join(' ')],
    REMPLACER: [3, 3, (t, a, b) => (texte(a) ? texte(t).split(texte(a)).join(texte(b)) : texte(t))],
    SI: [2, 3, (c, a, b = '') => (vrai(c) ? a : b)],
    VIDE: [1, 1, t => !texte(t).trim()],
    ET: [1, null, (...a) => a.every(vrai)],
    OU: [1, null, (...a) => a.some(vrai)],
    NON: [1, 1, x => !vrai(x)],
    ARRONDI: [1, 2, (x, n = 0) => arrondi(nombre(x), ent(n))],
    ENT: [1, 1, x => Math.floor(nombre(x))],
    ABS: [1, 1, x => Math.abs(nombre(x))],
    MIN: [1, null, (...a) => Math.min(...a.map(nombre))],
    MAX: [1, null, (...a) => Math.max(...a.map(nombre))],
    TEXTE: [1, 2, fTexte],
    ZEROS: [2, 2, fZeros],
    NUM: [1, 1, t => nombre(t)],
    CLE_GS1: [1, 1, fCleGs1],
  };

  function comparer(a, op, b) {
    let x, y;
    if (estNombre(a) && estNombre(b)) { x = nombre(a); y = nombre(b); }
    else { x = texte(a).toLowerCase(); y = texte(b).toLowerCase(); }
    switch (op) {
      case '=': return x === y;
      case '<>': case '!=': return x !== y;
      case '<': return x < y;
      case '>': return x > y;
      case '<=': return x <= y;
      default: return x >= y;
    }
  }

  function Analyseur(expr, valeurs) {
    this.j = jetons(expr); this.i = 0; this.v = valeurs; this.prof = 0;
  }
  Analyseur.prototype = {
    voir() { return this.j[this.i]; },
    prendre(op) {
      const t = this.j[this.i];
      if (op !== undefined && !(t[0] === 'op' && t[1] === op)) {
        throw new ErreurFormule('« ' + op + ' » attendu, ' + (t[0] === 'fin' ? 'la fin' : '« ' + t[1] + ' »') + ' trouvé.');
      }
      this.i++;
      return t;
    },
    estOp(...ops) { const t = this.voir(); return t[0] === 'op' && ops.includes(t[1]); },
    descendre() { if (++this.prof > PROFONDEUR_MAX) throw new ErreurFormule('Formule trop imbriquée.'); },
    expression() {
      this.descendre();
      let g = this.concat();
      while (this.estOp('=', '<>', '!=', '<', '>', '<=', '>=')) {
        const op = this.prendre()[1];
        g = comparer(g, op, this.concat());
      }
      this.prof--;
      return g;
    },
    concat() {
      let g = this.somme();
      while (this.estOp('&')) { this.prendre(); g = texte(g) + texte(this.somme()); }
      return g;
    },
    somme() {
      let g = this.produit();
      while (this.estOp('+', '-')) {
        const op = this.prendre()[1], d = this.produit();
        g = op === '+' ? nombre(g) + nombre(d) : nombre(g) - nombre(d);
      }
      return g;
    },
    produit() {
      let g = this.unaire();
      while (this.estOp('*', '/')) {
        const op = this.prendre()[1], d = this.unaire();
        if (op === '*') g = nombre(g) * nombre(d);
        else { const b = nombre(d); if (b === 0) throw new ErreurFormule('Division par zéro.'); g = nombre(g) / b; }
      }
      return g;
    },
    unaire() {
      if (this.estOp('-')) { this.prendre(); this.descendre(); const r = -nombre(this.unaire()); this.prof--; return r; }
      return this.primaire();
    },
    primaire() {
      const [typ, val, accolades] = this.prendre();
      if (typ === 'nombre' || typ === 'chaine') return val;
      if (typ === 'op' && val === '(') { const r = this.expression(); this.prendre(')'); return r; }
      if (typ === 'nom') {
        if (!accolades && this.estOp('(')) return this.appel(val.toUpperCase());
        if (!accolades && val.toUpperCase() === 'VRAI') return true;
        if (!accolades && val.toUpperCase() === 'FAUX') return false;
        const k = val.toLowerCase();
        return Object.prototype.hasOwnProperty.call(this.v, k) ? this.v[k] : '';
      }
      if (typ === 'fin') throw new ErreurFormule('Formule incomplète.');
      throw new ErreurFormule('« ' + val + ' » inattendu.');
    },
    appel(nom) {
      if (!Object.prototype.hasOwnProperty.call(FONCTIONS, nom)) throw new ErreurFormule('Fonction inconnue : ' + nom + '.');
      const [mini, maxi, fn] = FONCTIONS[nom];
      this.prendre('(');
      const args = [];
      if (!this.estOp(')')) {
        args.push(this.expression());
        while (this.estOp(';')) { this.prendre(); args.push(this.expression()); }
      }
      this.prendre(')');
      if (args.length < mini || (maxi !== null && args.length > maxi)) {
        const borne = mini === maxi ? String(mini) : (maxi ? mini + ' à ' + maxi : mini + ' ou plus');
        throw new ErreurFormule(nom + ' : ' + borne + ' argument(s) attendu(s).');
      }
      return fn(...args);
    },
  };

  function evaluerBrut(expr, valeurs) {
    expr = String(expr || '').trim();
    if (!expr) return '';
    if (expr.length > LONGUEUR_MAX) throw new ErreurFormule('Formule trop longue — ' + LONGUEUR_MAX + ' caractères au plus.');
    const v = {};
    for (const [k, x] of Object.entries(valeurs || {})) v[String(k).toLowerCase()] = x;
    const a = new Analyseur(expr, v);
    const r = a.expression();
    if (a.voir()[0] !== 'fin') throw new ErreurFormule('« ' + a.voir()[1] + ' » inattendu après la formule.');
    return r;
  }
  function evaluer(expr, valeurs) {
    try { return { valeur: texte(evaluerBrut(expr, valeurs)).slice(0, SORTIE_MAX), erreur: '' }; }
    catch (e) { return { valeur: '', erreur: e instanceof ErreurFormule ? e.message : 'Formule invalide.' }; }
  }
  function conditionVraie(expr, valeurs) {
    if (!String(expr || '').trim()) return true;
    try { return vrai(evaluerBrut(expr, valeurs)); } catch (e) { return false; }
  }

  // ── Dates ───────────────────────────────────────────────────────────
  const MOIS_COURTS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
  const MOIS_LONGS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  const p2 = n => String(n).padStart(2, '0');
  function semaineIso(d) {
    const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const j = t.getUTCDay() || 7;
    t.setUTCDate(t.getUTCDate() + 4 - j);
    const an = t.getUTCFullYear();
    const sem = Math.ceil(((t - Date.UTC(an, 0, 1)) / 864e5 + 1) / 7);
    return [an, sem, j];
  }
  function jourAnnee(d) {
    return Math.round((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - Date.UTC(d.getFullYear(), 0, 1)) / 864e5) + 1;
  }
  function formaterDate(d, fmt) {
    const [iy, iw, ij] = semaineIso(d);
    const codes = {
      d: p2(d.getDate()), m: p2(d.getMonth() + 1), Y: String(d.getFullYear()).padStart(4, '0'), y: p2(d.getFullYear() % 100),
      H: p2(d.getHours()), M: p2(d.getMinutes()), S: p2(d.getSeconds()), j: String(jourAnnee(d)).padStart(3, '0'),
      V: p2(iw), G: String(iy).padStart(4, '0'), g: p2(iy % 100), u: String(ij),
      b: MOIS_COURTS[d.getMonth()], B: MOIS_LONGS[d.getMonth()], '%': '%',
    };
    fmt = fmt || '%d/%m/%Y';
    let out = '';
    for (let i = 0; i < fmt.length; i++) {
      if (fmt[i] === '%' && i + 1 < fmt.length && Object.prototype.hasOwnProperty.call(codes, fmt[i + 1])) { out += codes[fmt[i + 1]]; i++; }
      else out += fmt[i];
    }
    return out;
  }
  function lireDate(s) {
    s = String(s || '').trim();
    let m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(s);
    let a, mo, j;
    if (m) { a = +m[1]; mo = +m[2]; j = +m[3]; }
    else if ((m = /^(\d{2}|\d{4})(\d{2})(\d{2})$/.exec(s))) { a = +m[1]; if (a < 100) a += 2000; mo = +m[2]; j = +m[3]; }
    else {
      m = /^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})$/.exec(s);
      if (!m) return null;
      j = +m[1]; mo = +m[2]; a = +m[3]; if (a < 100) a += 2000;
    }
    const d = new Date(a, mo - 1, j);
    if (d.getFullYear() !== a || d.getMonth() !== mo - 1 || d.getDate() !== j) return null;
    return d;
  }
  function ajouterMois(d, n) {
    const m = d.getMonth() + parseInt(n, 10);
    const a = d.getFullYear() + Math.floor(m / 12), mm = ((m % 12) + 12) % 12;
    const dernier = new Date(a, mm + 1, 0).getDate();
    return new Date(a, mm, Math.min(d.getDate(), dernier), d.getHours(), d.getMinutes(), d.getSeconds());
  }
  function calculerDate(v, valeurs, maintenant) {
    maintenant = maintenant || new Date();
    const base = String(v.base || 'impression').trim().toLowerCase();
    let d;
    if (base === 'impression') d = new Date(maintenant.getTime());
    else {
      const lu = lireDate((valeurs || {})[base]);
      if (!lu) return '';
      d = new Date(lu.getFullYear(), lu.getMonth(), lu.getDate(), maintenant.getHours(), maintenant.getMinutes());
    }
    if (v.decalage_mois) d = ajouterMois(d, v.decalage_mois);
    d.setDate(d.getDate() + (parseInt(v.decalage_jours, 10) || 0));
    return formaterDate(d, v.format || '%d/%m/%Y');
  }

  // ── GS1 ─────────────────────────────────────────────────────────────
  function cleGs1(ch) {
    let t = 0;
    for (let i = 0; i < ch.length; i++) t += parseInt(ch[ch.length - 1 - i], 10) * (i % 2 === 0 ? 3 : 1);
    return String((10 - t % 10) % 10);
  }
  function sscc(extension, prefixe, serie) {
    prefixe = String(prefixe || '').replace(/\D/g, '');
    if (prefixe.length < 7 || prefixe.length > 10) throw new ErreurFormule('Préfixe GS1 invalide — 7 à 10 chiffres.');
    const l = 16 - prefixe.length;
    const base = String(extension || '0').slice(0, 1) + prefixe + String(serie).padStart(l, '0');
    if (base.length !== 17) throw new ErreurFormule('Série SSCC épuisée pour le préfixe ' + prefixe + '.');
    return base + cleGs1(base);
  }
  const AI = {
    '00': ['SSCC', 18, 18, 'n', true], '01': ['GTIN', 14, 14, 'n', true], '02': ['CONTENT', 14, 14, 'n', true],
    '10': ['BATCH/LOT', null, 20, 'an', false], '11': ['PROD DATE', 6, 6, 'date', false],
    '15': ['BEST BEFORE', 6, 6, 'date', false], '17': ['USE BY', 6, 6, 'date', false],
    '21': ['SERIAL', null, 20, 'an', false], '37': ['COUNT', null, 8, 'n', false],
    '400': ['ORDER NUMBER', null, 30, 'an', false], '420': ['SHIP TO POST', null, 20, 'an', false],
  };
  for (let x = 0; x < 6; x++) { AI['310' + x] = ['NET WEIGHT (kg)', 6, 6, 'n', false]; AI['330' + x] = ['GROSS WEIGHT (kg)', 6, 6, 'n', false]; }
  function decouperAi(valeur) {
    const out = [], re = /\((\d{2,4})\)([^(]*)/g, s = String(valeur || '').replace(/\s+/g, '');
    let m;
    while ((m = re.exec(s))) out.push([m[1], m[2]]);
    return out;
  }
  function dateGs1Ok(s) {
    if (!/^\d{6}$/.test(s)) return false;
    const a = 2000 + +s.slice(0, 2), m = +s.slice(2, 4), j = +s.slice(4);
    if (m < 1 || m > 12) return false;
    if (j === 0) return true;
    const d = new Date(a, m - 1, j);
    return d.getMonth() === m - 1 && d.getDate() === j;
  }
  function controlerGs1(valeur) {
    const g = decouperAi(valeur);
    if (!g.length) return ['Aucun identifiant d\'application — écrire les AI entre parenthèses, ex. (00)…'];
    const out = [];
    for (const [ai, data] of g) {
      if (!AI[ai]) { out.push('AI (' + ai + ') non pris en charge.'); continue; }
      const [lib, fixe, maxi, typ, cle] = AI[ai];
      if (!data) { out.push('AI (' + ai + ') ' + lib + ' : donnée vide.'); continue; }
      if ((typ === 'n' || typ === 'date') && !/^\d+$/.test(data)) { out.push('AI (' + ai + ') ' + lib + ' : chiffres uniquement.'); continue; }
      if (fixe && data.length !== fixe) { out.push('AI (' + ai + ') ' + lib + ' : ' + fixe + ' chiffres attendus, ' + data.length + ' reçus.'); continue; }
      if (data.length > maxi) { out.push('AI (' + ai + ') ' + lib + ' : ' + maxi + ' caractères au plus.'); continue; }
      if (typ === 'date' && !dateGs1Ok(data)) out.push('AI (' + ai + ') ' + lib + ' : date AAMMJJ invalide (' + data + ').');
      if (cle && cleGs1(data.slice(0, -1)) !== data.slice(-1)) out.push('AI (' + ai + ') ' + lib + ' : clé de contrôle fausse (attendu ' + cleGs1(data.slice(0, -1)) + ').');
    }
    if (g[0][0] !== '00' && g.some(x => x[0] === '00')) out.push('Le SSCC (00) se place en tête de son code-barres.');
    return out;
  }

  // ── Valeurs d'une étiquette ─────────────────────────────────────────
  const PLACEHOLDER = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g;
  function substituer(t, vals) { return String(t || '').replace(PLACEHOLDER, (_, n) => { const v = vals[n.toLowerCase()]; return v == null ? '' : String(v); }); }

  /* opts : saisies {nom: valeur} (saisies et sources), plan {nom: {premier, pas}}
   * (numéros réservés par le serveur ; à défaut, départ de chaque compteur et
   * série 1 des SSCC), index (rang dans la série), maintenant, systeme
   * {fsc_licence, gs1_prefixe}. */
  function valeurs(layout, opts) {
    opts = opts || {};
    const saisies = opts.saisies || {}, plan = opts.plan || {}, index = opts.index || 0;
    const out = Object.assign({}, opts.systeme || {});
    const vars = (layout && layout.variables) || [];
    for (const v of vars) {
      if (v.type === 'fixe') out[v.nom] = v.valeur || '';
      else if (v.type === 'saisie' || v.type === 'source') out[v.nom] = saisies[v.nom] != null ? String(saisies[v.nom]) : (v.valeur || '');
      else if (v.type === 'compteur') {
        const p = plan[v.nom] || { premier: v.debut == null ? 1 : v.debut, pas: v.pas || 1 };
        out[v.nom] = (v.prefixe || '') + String(p.premier + index * (p.pas || 1)).padStart(v.longueur || 0, '0') + (v.suffixe || '');
      } else if (v.type === 'sscc') {
        const p = plan[v.nom] || { premier: 1 };
        try { out[v.nom] = sscc(v.extension, v.prefixe_gs1, p.premier + index); } catch (e) { out[v.nom] = ''; }
      }
    }
    for (let passe = 0; passe < 2; passe++) {
      for (const v of vars) {
        if (v.type === 'date') out[v.nom] = calculerDate(v, out, opts.maintenant);
        else if (v.type === 'formule') out[v.nom] = evaluer(v.expression || '', out).valeur;
      }
    }
    return out;
  }
  function visible(e, vals) {
    if (e.condition && !conditionVraie(e.condition, vals)) return false;
    if (e.masquer_si_vide && (e.type === 'texte' || e.type === 'code_barre')) {
      // Vide = toutes les variables citées sont vides, ou le texte entier s'il n'en cite aucune.
      const noms = [...String(e.valeur || '').matchAll(PLACEHOLDER)].map(m => m[1].toLowerCase());
      if (noms.length ? !noms.some(n => String(vals[n] == null ? '' : vals[n]).trim()) : !substituer(e.valeur, vals).trim()) return false;
    }
    return true;
  }
  function verrouille(e, layout) {
    if (e.verrou) return true;
    const c = ((layout && layout.calques) || []).find(x => x.id === e.calque);
    return !!(c && c.verrou);
  }

  // ── CSV / collage Excel ─────────────────────────────────────────────
  function lireTableau(brut) {
    const t = String(brut || '').replace(/^﻿/, '').replace(/\r\n?/g, '\n').replace(/\n+$/, '');
    if (!t.trim()) return { entetes: [], lignes: [] };
    const premiere = t.split('\n')[0];
    const sep = premiere.includes('\t') ? '\t' : ((premiere.match(/;/g) || []).length >= (premiere.match(/,/g) || []).length ? ';' : ',');
    const lignes = [];
    let champ = '', ligne = [], guillemets = false;
    for (let i = 0; i < t.length; i++) {
      const c = t[i];
      if (guillemets) {
        if (c === '"' && t[i + 1] === '"') { champ += '"'; i++; }
        else if (c === '"') guillemets = false;
        else champ += c;
      } else if (c === '"' && champ === '') guillemets = true;
      else if (c === sep) { ligne.push(champ); champ = ''; }
      else if (c === '\n') { ligne.push(champ); lignes.push(ligne); ligne = []; champ = ''; }
      else champ += c;
    }
    ligne.push(champ); lignes.push(ligne);
    const nettes = lignes.filter(l => l.some(x => String(x).trim()));
    const entetes = (nettes.shift() || []).map((x, i) => String(x).trim() || ('Colonne ' + (i + 1)));
    return { entetes, lignes: nettes.map(l => entetes.map((_, i) => String(l[i] == null ? '' : l[i]).trim())), separateur: sep };
  }
  const normer = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '');
  // Variable → colonne, par nom ou libellé (« Lot », « N° de lot », « lot »).
  function correspondanceAuto(entetes, variables) {
    const out = {};
    const libres = entetes.map((e, i) => [normer(e), i]);
    for (const v of variables) {
      if (!['saisie', 'source', 'fixe'].includes(v.type)) continue;
      const cles = [normer(v.nom), normer(v.libelle), normer((v.champ || '').split('.').pop())].filter(Boolean);
      const trouve = libres.find(([n]) => cles.includes(n)) || libres.find(([n]) => cles.some(c => c.length > 2 && (n.includes(c) || c.includes(n))));
      if (trouve) out[v.nom] = trouve[1];
    }
    return out;
  }
  function enregistrementsDepuis(tableau, correspondance) {
    return tableau.lignes.map(l => {
      const r = {};
      for (const [nom, col] of Object.entries(correspondance || {})) if (col !== null && col !== '' && col !== undefined && l[col] !== undefined) r[nom] = l[col];
      return r;
    });
  }

  // ── Lisibilité ──────────────────────────────────────────────────────
  // Règles par famille : points imprimante minimaux par module, dimension X
  // conseillée, zone de silence (en modules). Sources : spécifications
  // générales GS1 (5.4, 5.5, 6.6), ISO/IEC 16022 (DataMatrix), 18004 (QR).
  const REGLES_CODES = {
    code128: { min_points: 2, x_min: 0.25, silence: 10, lin: true },
    gs1_128: { min_points: 2, x_min: 0.25, silence: 10, lin: true },
    ean13: { min_points: 2, x_min: 0.264, silence: 11, lin: true },
    ean8: { min_points: 2, x_min: 0.264, silence: 7, lin: true },
    upca: { min_points: 2, x_min: 0.264, silence: 9, lin: true },
    code39: { min_points: 2, x_min: 0.25, silence: 10, lin: true },
    itf14: { min_points: 2, x_min: 0.495, silence: 10, lin: true },
    datamatrix: { min_points: 3, x_min: 0.255, silence: 1 },
    gs1_datamatrix: { min_points: 3, x_min: 0.255, silence: 1 },
    qrcode: { min_points: 3, x_min: 0.33, silence: 4 },
    pdf417: { min_points: 2, x_min: 0.25, silence: 2 },
  };
  const BORD_MIN_MM = 1.5;
  /* e : élément code_barre ; taille {w, h} en mm, rendue ; ctx {dpi, L, H,
   * voisins: [{x,y,w,h,nom}]} ; donnees : valeur substituée. */
  function lisibilite(e, taille, ctx, donnees) {
    const r = REGLES_CODES[e.symbologie] || REGLES_CODES.code128;
    const out = [];
    const nom = e.nom || e.id;
    const pts = e.module * ctx.dpi / 25.4, ptsR = Math.max(1, Math.round(pts));
    const xReel = ptsR * 25.4 / ctx.dpi;
    if (ptsR < r.min_points) out.push({ gravite: 'bloquant', message: `« ${nom} » : module de ${fmt(e.module)} mm = ${ptsR} point(s) à ${ctx.dpi} dpi, illisible. ${r.min_points} points au moins (${fmt(r.min_points * 25.4 / ctx.dpi)} mm).` });
    else if (xReel < r.x_min - 1e-9) out.push({ gravite: 'attention', message: `« ${nom} » : module imprimé de ${fmt(xReel)} mm, sous les ${fmt(r.x_min)} mm conseillés pour ce code.` });
    if (Math.abs(pts - ptsR) > 0.25 && ptsR >= r.min_points) out.push({ gravite: 'info', message: `« ${nom} » : ${fmt(e.module)} mm n'est pas un nombre entier de points à ${ctx.dpi} dpi — imprimé à ${fmt(xReel)} mm. Choisir ${fmt(Math.round(pts) * 25.4 / ctx.dpi)} mm.` });
    if (r.lin && e.hauteur < Math.max(6.35, 0.15 * taille.w)) out.push({ gravite: 'attention', message: `« ${nom} » : barres de ${fmt(e.hauteur)} mm, trop basses (au moins ${fmt(Math.max(6.35, 0.15 * taille.w))} mm, 15 % de la largeur).` });
    if (e.symbologie === 'gs1_128' && /\(00\)/.test(donnees || '')) {
      if (xReel < 0.495 - 1e-9) out.push({ gravite: 'attention', message: `« ${nom} » : SSCC logistique — dimension X de 0,495 mm au moins (GS1), ${fmt(xReel)} mm ici.` });
      if (e.hauteur < 31.75) out.push({ gravite: 'attention', message: `« ${nom} » : SSCC logistique — barres de 31,75 mm au moins (GS1), ${fmt(e.hauteur)} mm ici.` });
    }
    const zs = r.silence * xReel;
    const gauche = e.x, droite = ctx.L - (e.x + taille.w), haut = e.y, bas = ctx.H - (e.y + taille.h);
    const bordH = r.lin ? Math.max(zs, BORD_MIN_MM) : Math.max(zs, BORD_MIN_MM);
    if (gauche < bordH - 1e-9 || droite < bordH - 1e-9) out.push({ gravite: gauche < 0 || droite < 0 ? 'bloquant' : 'attention', message: `« ${nom} » : ${fmt(Math.min(gauche, droite))} mm du bord, zone de silence de ${fmt(bordH)} mm nécessaire.` });
    if (haut < BORD_MIN_MM - 1e-9 || bas < BORD_MIN_MM - 1e-9) out.push({ gravite: haut < 0 || bas < 0 ? 'bloquant' : 'attention', message: `« ${nom} » : trop près du bord ${haut < bas ? 'haut' : 'bas'} (${fmt(Math.min(haut, bas))} mm, ${fmt(BORD_MIN_MM)} mm au moins).` });
    for (const v of ctx.voisins || []) {
      const zx0 = e.x - zs, zx1 = e.x + taille.w + zs, zy0 = e.y - (r.lin ? 0 : zs), zy1 = e.y + taille.h + (r.lin ? 0 : zs);
      if (v.x < zx1 && v.x + v.w > zx0 && v.y < zy1 && v.y + v.h > zy0) { out.push({ gravite: 'attention', message: `« ${nom} » : « ${v.nom} » empiète sur sa zone de silence.` }); break; }
    }
    if (e.symbologie === 'gs1_128' || e.symbologie === 'gs1_datamatrix') for (const m of controlerGs1(donnees)) out.push({ gravite: 'bloquant', message: `« ${nom} » : ${m}` });
    return out;
  }
  function fmt(n) { return String(Math.round(n * 1000) / 1000).replace('.', ','); }

  /* Contrôles mécaniques de toute l'étiquette avant impression.
   * boites : {id: {x,y,w,h}} mesurées sur l'aperçu (texte réel, code rendu). */
  function controleLocal(layout, vals, ctx, boites) {
    const out = [];
    const els = (layout.elements || []).filter(e => visible(e, vals));
    for (const e of els) {
      const b = boites && boites[e.id];
      const nom = e.nom || e.id;
      if (e.type === 'texte') {
        const t = substituer(e.valeur, vals);
        if (/\{\{/.test(t)) out.push({ gravite: 'bloquant', element_id: e.id, message: `« ${nom} » : variable non remplacée.` });
        if (e.taille < 1.5) out.push({ gravite: 'attention', element_id: e.id, message: `« ${nom} » : caractères de ${fmt(e.taille)} mm, difficilement lisibles (1,5 mm au moins).` });
        if (e.largeur && b && b.coupe) out.push({ gravite: 'attention', element_id: e.id, message: `« ${nom} » : texte coupé — il ne tient pas en ${e.lignes || 1} ligne(s) de ${fmt(e.largeur)} mm.` });
        if (e.inverse && !els.some(c => c.type === 'cadre' && c.plein && c.x <= e.x && c.y <= e.y && c.x + c.largeur >= e.x + (b ? b.w : 0) && c.y + c.hauteur >= e.y + e.taille)) {
          out.push({ gravite: 'bloquant', element_id: e.id, message: `« ${nom} » : texte blanc hors d'un aplat noir — invisible à l'impression.` });
        }
      }
      if (b && (b.x < -0.01 || b.y < -0.01 || b.x + b.w > ctx.L + 0.01 || b.y + b.h > ctx.H + 0.01)) {
        out.push({ gravite: 'bloquant', element_id: e.id, message: `« ${nom} » dépasse de l'étiquette.` });
      }
    }
    const usage = ctx.usage || '';
    const tous = els.map(e => substituer(e.valeur, vals)).join(' ');
    if (usage === 'palette' && !els.some(e => e.type === 'code_barre' && /\(00\)/.test(e.valeur || ''))) {
      out.push({ gravite: 'attention', message: 'Étiquette palette sans SSCC (00) en code-barres.' });
    }
    if (els.some(e => e.type === 'picto' && e.picto === 'fsc')) {
      const lic = (vals.fsc_licence || '').trim();
      if (!lic || !tous.concat(' ', els.map(e => substituer(e.legende, vals)).join(' ')).includes(lic)) {
        out.push({ gravite: 'bloquant', message: 'Mention FSC sans numéro de licence (FSC_LICENCE_SIFA à renseigner, ou légende vide).' });
      }
    }
    return out;
  }

  // ── Étiquette logistique palette (GS1) ──────────────────────────────
  /* opts : {largeur, hauteur, prefixe, extension, ai: ['02','37','10','15','3102'],
   * expediteur: true, destinataire: true}. Rend {largeur_mm, hauteur_mm, layout}.
   * Disposition GS1 : texte libre en haut, données en clair au milieu,
   * codes-barres en bas, le SSCC toujours le plus bas. */
  function etiquetteLogistique(opts) {
    opts = opts || {};
    const L = opts.largeur || 105, H = opts.hauteur || 148, m = 4;
    const ai = opts.ai || ['02', '37', '10', '15'];
    const els = [], vars = [];
    let y = m, n = 1;
    const id = () => 'g' + (n++);
    const fond = (o) => Object.assign({ calque: 'fond', verrou: true }, o);
    const donnee = (o) => Object.assign({ calque: 'donnees', verrou: false }, o);
    if (opts.expediteur !== false) {
      els.push(fond({ id: id(), type: 'texte', nom: 'Expéditeur', x: m, y, valeur: '{{expediteur}}', taille: 3, largeur: (L - 2 * m) / 2 - 1, lignes: 3 }));
      vars.push({ nom: 'expediteur', libelle: 'Expéditeur', type: 'fixe', valeur: opts.expediteur_texte || '' });
    }
    if (opts.destinataire !== false) {
      els.push(donnee({ id: id(), type: 'texte', nom: 'Destinataire', x: L / 2 + 1, y, valeur: '{{client_nom}}\n{{client_adresse}}', taille: 3, largeur: (L - 2 * m) / 2 - 1, lignes: 3, masquer_si_vide: true }));
      vars.push({ nom: 'client_nom', libelle: 'Client', type: 'source', champ: 'client.raison_sociale', valeur: '' });
      vars.push({ nom: 'client_adresse', libelle: 'Ville du client', type: 'source', champ: 'client.ville', valeur: '' });
    }
    y += 12;
    els.push(fond({ id: id(), type: 'ligne', nom: 'Séparation haut', x: m, y, orientation: 'h', longueur: L - 2 * m, epaisseur: 0.4 }));
    y += 2;
    const lignesClair = [['00', 'SSCC', '{{sscc}}']];
    vars.push({ nom: 'sscc', libelle: 'SSCC', type: 'sscc', extension: String(opts.extension || '0'), prefixe_gs1: String(opts.prefixe || '') });
    const codeProduit = [];
    if (ai.includes('02')) { vars.push({ nom: 'gtin', libelle: 'GTIN du contenu (14 chiffres)', type: 'saisie', valeur: '', obligatoire: true }); lignesClair.push(['02', 'CONTENT', '{{gtin}}']); codeProduit.push('(02){{gtin}}'); }
    if (ai.includes('37')) { vars.push({ nom: 'quantite', libelle: 'Nombre d\'unités', type: 'source', champ: 'dossier.etiquettes_par_carton', valeur: '' }); lignesClair.push(['37', 'COUNT', '{{quantite}}']); codeProduit.push('(37){{quantite}}'); }
    if (ai.includes('10')) { vars.push({ nom: 'lot', libelle: 'Lot', type: 'source', champ: 'dossier.reference', valeur: '' }); lignesClair.push(['10', 'BATCH/LOT', '{{lot}}']); }
    if (ai.includes('11') || ai.includes('15')) vars.push({ nom: 'date_fabrication', libelle: 'Date de fabrication', type: 'date', base: 'impression', format: '%y%m%d', decalage_jours: 0 });
    if (ai.includes('11')) { lignesClair.push(['11', 'PROD DATE', '{{date_fabrication}}']); codeProduit.push('(11){{date_fabrication}}'); }
    if (ai.includes('15')) { vars.push({ nom: 'ddm', libelle: 'Date de durabilité (DDM)', type: 'date', base: 'date_fabrication', format: '%y%m%d', decalage_mois: 24 }); lignesClair.push(['15', 'BEST BEFORE', '{{ddm}}']); codeProduit.push('(15){{ddm}}'); }
    if (ai.includes('3102')) {
      vars.push({ nom: 'poids_kg', libelle: 'Poids net (kg)', type: 'saisie', valeur: '', obligatoire: false });
      vars.push({ nom: 'poids_ai', libelle: 'Poids net AI 3102', type: 'formule', expression: 'ZEROS(ARRONDI(NUM(poids_kg)*100;0);6)' });
      lignesClair.push(['3102', 'NET WEIGHT (kg)', '{{poids_kg}}']); codeProduit.push('(3102){{poids_ai}}');
    }
    if (ai.includes('10')) codeProduit.push('(10){{lot}}');   // longueur variable : en dernier
    for (const [a, lib, val] of lignesClair) {
      els.push(fond({ id: id(), type: 'texte', nom: 'Intitulé ' + a, x: m, y, valeur: lib, taille: 2.4 }));
      els.push(donnee({ id: id(), type: 'texte', nom: 'Valeur ' + a, x: m + 30, y: y - 0.5, valeur: val, taille: a === '00' ? 4.5 : 3.6, gras: true, masquer_si_vide: a !== '00' }));
      y += a === '00' ? 6.5 : 5.2;
    }
    y += 1;
    els.push(fond({ id: id(), type: 'ligne', nom: 'Séparation codes', x: m, y, orientation: 'h', longueur: L - 2 * m, epaisseur: 0.4 }));
    const zs = 6;   // 10 X de zone de silence (X 0,5 mm imprimé 0,5005 mm à 203 dpi) + marge
    const hSscc = 32, hProd = 25;
    const ySscc = H - m - hSscc - 4;
    if (codeProduit.length) {
      const yProd = Math.max(y + 3, ySscc - hProd - 8);
      els.push(donnee({ id: id(), type: 'code_barre', nom: 'GS1-128 contenu', x: zs, y: yProd, symbologie: 'gs1_128', valeur: codeProduit.join(''), hauteur: hProd, module: 0.375, lisible: true }));
    }
    els.push(donnee({ id: id(), type: 'code_barre', nom: 'GS1-128 SSCC', x: zs, y: ySscc, symbologie: 'gs1_128', valeur: '(00){{sscc}}', hauteur: hSscc, module: 0.5, lisible: true }));
    return { largeur_mm: L, hauteur_mm: H, layout: { elements: els, variables: vars,
      calques: [{ id: 'fond', nom: 'Fond figé (logo, mentions)', verrou: true }, { id: 'donnees', nom: 'Données', verrou: false }] } };
  }

  return {
    ErreurFormule, nombre, texte, vrai, arrondi, evaluer, evaluerBrut, conditionVraie, FONCTIONS: Object.keys(FONCTIONS),
    formaterDate, lireDate, ajouterMois, calculerDate, semaineIso,
    cleGs1, sscc, AI, decouperAi, controlerGs1,
    substituer, valeurs, visible, verrouille,
    lireTableau, correspondanceAuto, enregistrementsDepuis,
    REGLES_CODES, lisibilite, controleLocal, etiquetteLogistique,
  };
});
