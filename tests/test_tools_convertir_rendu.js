// Rendu de MyTools › Convertir sur un DOM minimal : tuiles cliquables (sans
// fichier : choisir un fichier ; avec : choisir le format de sortie), formats
// et bouton affichés après dépôt. node tests/test_tools_convertir_rendu.js
const vm = require('vm'), fs = require('fs');
const src = fs.readFileSync(require('path').join(__dirname, '..', 'static', 'mysifa_tools_convertir.js'), 'utf8');
const stubs = {}; let clic = null, change = null;
function el(sel) {
  return { sel, innerHTML: '', dataset: {}, className: '', accept: '', files: [], value: '',
    classList: { toggle() {}, add() {}, remove() {} },
    addEventListener(t, f) { if (t === 'click') clic = f; if (t === 'change' && sel === '[data-fichiers]') change = f; },
    querySelector(s) { return stubs[s] || (stubs[s] = el(s)); }, querySelectorAll() { return []; },
    setAttribute() {}, getAttribute() { return null; }, appendChild() {}, click() {} };
}
const host = el('host');
const ctx = { console, setTimeout, clearTimeout, Promise, URL: { createObjectURL() { return ''; } },
  fetch: async () => ({ ok: true, json: async () => ({ outils: { convert: true, potrace: true }, paquets: {} }) }),
  document: { createElement: () => host, head: { appendChild() {} } } };
ctx.window = ctx; vm.createContext(ctx); vm.runInContext(src, ctx);
const ok = (c, m) => { console.log((c ? 'ok ' : 'KO ') + m); if (!c) process.exitCode = 1; };
(async () => {
  ctx.MyToolsConvertir.mount({ appendChild() {}, innerHTML: '' }, { toast() {} });
  await new Promise(r => setTimeout(r, 20));
  const z = n => stubs['[data-zone="' + n + '"]'].innerHTML;
  ok(/data-source="image"/.test(z('familles')) && !/Sur ce poste|serveur/i.test(z('familles')), 'sans fichier : tuiles cliquables, sans poste/serveur');
  stubs['[data-fichiers]'].files = [{ name: 'logo.png', size: 1000, type: 'image/png' }];
  change();
  ok(/data-cible="svg"/.test(z('cibles')), 'png : formats de sortie affichés');
  ok(/data-dest="svg"/.test(z('familles')) && /data-dest="pdf"/.test(z('familles')), 'png : tuile Image vectorielle et PDF');
  const b = { disabled: false, dataset: { dest: 'svg' } };
  await clic({ target: { closest: () => b } });
  ok(/data-cible="svg" ?|tconv-pastille actif" data-cible="svg"/.test(z('cibles')) && /actif" data-dest="svg"/.test(z('familles')), 'clic Image vectorielle : SVG choisi');
  ok(/tconv-go/.test(z('action')), 'bouton Convertir présent');
})();
