/*
 * MyTools — éditeur PDF : traitements par lot et actions enregistrées.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Une action = une suite d'étapes nommée (filigrane, numérotation, OCR,
 * nettoyage, compression, renommage), rejouée sur plusieurs PDF ; chaque
 * fichier est traité à part et téléchargé sous son nouveau nom. Les actions
 * sont gardées en base, par utilisateur (/api/tools/pdf/actions) : ce sont
 * des outils de travail que l'on retrouve sur tous ses postes, pas une
 * préférence d'affichage. Les fichiers, eux, ne quittent pas le poste.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  var TYPES = {
    filigrane: { libelle: 'Filigrane', defaut: { texte: 'CONFIDENTIEL', opacite: 0.15, angle: 45, taille: 60 } },
    numerotation: { libelle: 'Numérotation', defaut: { modele: 'Page {n} / {N}', position: 'bas-centre' } },
    ocr: { libelle: 'OCR des pages sans texte', defaut: {} },
    nettoyage: { libelle: 'Nettoyer les métadonnées', defaut: {} },
    compression: { libelle: 'Compression des images', defaut: { dpi: 150, qualite: 70 } },
    renommage: { libelle: 'Renommer', defaut: { modele: '{nom}-traite' } }
  };
  /* ── Fonctions pures (tests) ──────────────────────────────────────── */
  function nomFichier(modele, nom, n, date) {
    var base = String(nom || 'document').replace(/\.pdf$/i, '');
    var r = String(modele || '{nom}').replace(/\{nom\}/g, base).replace(/\{n\}/g, String(n)).replace(/\{date\}/g, String(date || '').replace(/\//g, '-'));
    r = r.replace(/[\\/:*?"<>|]+/g, '-').trim() || base;
    return /\.pdf$/i.test(r) ? r : r + '.pdf';
  }
  function etapesValides(l) {
    return (Array.isArray(l) ? l : []).filter(function (e) { return e && TYPES[e.type]; })
      .map(function (e) { return { type: e.type, p: Object.assign({}, TYPES[e.type].defaut, e.p || {}) }; });
  }

  M._interne = M._interne || {};
  M._interne.lot = { nomFichier: nomFichier, etapesValides: etapesValides, TYPES: TYPES };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function bouton(t, cls, bulle) { var b = el('button', 'tpdf-b' + (cls ? ' ' + cls : ''), t); b.type = 'button'; b.setAttribute('data-bulle', bulle || t); return b; }

    api.IC.lot = '<rect x="7" y="3.5" width="12" height="14" rx="1.5"/><path d="M5 7v12a1.5 1.5 0 0 0 1.5 1.5H15"/><path d="M10 10.5l2 2 4-4"/>';
    var mp = EXT.menus.pages || (EXT.menus.pages = { libelle: 'Pages', icone: 'pages', ordre: 1, items: [] });
    mp.items.push({ separe: true }, { act: 'lot', icone: 'lot', libelle: 'Traitement par lot et actions…', bulle: 'Lot' });
    // Disponible même sans document ouvert (EXT.actions.lot.sansDoc).

    async function api_(methode, chemin, corps) {
      var r = await fetch('/api/tools/pdf/actions' + (chemin || ''), { method: methode, credentials: 'same-origin',
        headers: corps ? { 'Content-Type': 'application/json' } : {}, body: corps ? JSON.stringify(corps) : undefined });
      var j = null; try { j = await r.json(); } catch (e) { j = null; }
      if (!r.ok) throw new Error((j && j.detail) || 'Service indisponible (' + r.status + ').');
      return j;
    }

    function editeurEtape(e, supprimer, maj) {
      var b = el('div', 'tpdf-lot-etape'), t = el('div', 'tpdf-ligne tpdf-ligne-esp');
      t.appendChild(el('b', null, TYPES[e.type].libelle));
      var x = el('button', 'tpdf-btn tpdf-btn-mini'); x.type = 'button'; x.innerHTML = api.ico('fermer', 12); x.setAttribute('data-bulle', 'Retirer'); x.setAttribute('aria-label', 'Retirer l\'étape'); x.addEventListener('click', supprimer);
      t.appendChild(x); b.appendChild(t);
      function champ(lib, cle, type) {
        var i = el('input', 'tpdf-champ'); i.type = type || 'text'; if (type === 'number') i.step = 'any'; i.value = e.p[cle];
        i.addEventListener('change', function () { e.p[cle] = type === 'number' ? parseFloat(i.value) : i.value; maj(); });
        b.appendChild(api.champ(lib, i));
      }
      if (e.type === 'filigrane') { champ('Texte', 'texte'); champ('Opacité (0–1)', 'opacite', 'number'); champ('Angle', 'angle', 'number'); }
      if (e.type === 'numerotation') { champ('Modèle ({n}, {N})', 'modele'); }
      if (e.type === 'compression') { champ('Résolution maximale (dpi)', 'dpi', 'number'); champ('Qualité JPEG (30–95)', 'qualite', 'number'); }
      if (e.type === 'renommage') { champ('Nom ({nom}, {n}, {date})', 'modele'); }
      return b;
    }

    async function traiter(f, etapes, n, progres) {
      var s = S(), avant = { misePage: s.misePage, nettoyer: s.nettoyer }, ids = [], b = new Uint8Array(await f.arrayBuffer());
      if (!/\.pdf$/i.test(f.name) && f.type !== 'application/pdf') b = await api.imageVersPdf(b);
      var src = await api.ajouterSource(f.name, b); ids.push(src.id);
      var pages = src.metas.map(function (_, i) { return api.nouvellePage(src.id, i); });
      try {
        var mp2 = null;
        etapes.forEach(function (e) {
          if (e.type === 'filigrane' || e.type === 'numerotation') {
            mp2 = mp2 || { numero: { actif: false, modele: 'Page {n} / {N}', position: 'bas-centre', taille: 9 }, entete: { gauche: '', centre: '', droite: '', taille: 9 }, pied: { gauche: '', centre: '', droite: '', taille: 9 },
              bates: { actif: false, prefixe: '', debut: 1, chiffres: 6, position: 'bas-droite', taille: 9 },
              filigrane: { actif: false, type: 'texte', texte: '', taille: 60, couleur: '#d92626', opacite: 0.15, angle: 45, image: null, echelle: 50 }, pages: 'toutes', marge: 24 };
            if (e.type === 'filigrane') Object.assign(mp2.filigrane, { actif: true, texte: e.p.texte, opacite: e.p.opacite, angle: e.p.angle, taille: e.p.taille || 60 });
            else Object.assign(mp2.numero, { actif: true, modele: e.p.modele, position: e.p.position || 'bas-centre' });
          }
        });
        if (etapes.some(function (e) { return e.type === 'ocr'; }) && EXT.ocr) {
          var vides = [];
          for (var i = 0; i < pages.length; i++) { s.pages.push(pages[i]); var vide = await EXT.ocr.sansTexte(pages[i]); s.pages.pop(); if (vide) vides.push(pages[i]); }
          if (vides.length) await EXT.ocr.reconnaitre(vides, function (k, t) { progres('OCR ' + k + ' / ' + t); });
        }
        s.misePage = mp2 || null;
        s.nettoyer = etapes.some(function (e) { return e.type === 'nettoyage'; }) || avant.nettoyer;
        var out = await api.construire(pages);
        var comp = etapes.filter(function (e) { return e.type === 'compression'; })[0];
        if (comp && M._interne.pages && M._interne.pages.optimiserImages) out = (await M._interne.pages.optimiserImages(out, comp.p.dpi || 150, Math.max(0.3, Math.min(0.95, (comp.p.qualite || 70) / 100)))).octets;
        var ren = etapes.filter(function (e) { return e.type === 'renommage'; })[0];
        return { octets: out, nom: ren ? nomFichier(ren.p.modele, f.name, n, api.dateDuJour()) : f.name.replace(/\.(png|jpe?g)$/i, '.pdf') };
      } finally {
        s.misePage = avant.misePage; s.nettoyer = avant.nettoyer;
        ids.forEach(function (id) { try { s.sources[id].pdf.destroy(); } catch (e) { /* libéré */ } delete s.sources[id]; });
      }
    }

    function panneauLot() {
      var corps = el('div'), etat = { etapes: [], fichiers: [] };
      var haut = el('div', 'tpdf-ligne tpdf-ligne-esp'), actions = el('select', 'tpdf-champ'), o0 = el('option', null, '— Actions enregistrées —'); o0.value = ''; actions.appendChild(o0);
      haut.appendChild(api.champ('Action', actions));
      var retirerA = bouton('Retirer l\'action', '', 'Retirer'); haut.appendChild(retirerA);
      corps.appendChild(haut);
      var zone = el('div', 'tpdf-lot-etapes'); corps.appendChild(zone);
      var ajout = el('div', 'tpdf-ligne'), typ = el('select', 'tpdf-champ');
      Object.keys(TYPES).forEach(function (k) { var o = el('option', null, TYPES[k].libelle); o.value = k; typ.appendChild(o); });
      var bAj = bouton('Ajouter l\'étape', '', 'Ajouter'); ajout.appendChild(typ); ajout.appendChild(bAj); corps.appendChild(ajout);
      var lgN = el('div', 'tpdf-ligne'), nom = el('input', 'tpdf-champ'); nom.type = 'text'; nom.placeholder = 'Nom de l\'action'; nom.maxLength = 80;
      var bSv = bouton('Enregistrer l\'action', '', 'Enregistrer'); lgN.appendChild(nom); lgN.appendChild(bSv); corps.appendChild(lgN);
      var fic = el('input', 'tpdf-champ'); fic.type = 'file'; fic.multiple = true; fic.accept = '.pdf,application/pdf,image/png,image/jpeg';
      corps.appendChild(api.champ('Fichiers à traiter (chacun à part)', fic));
      var res = el('div', 'tpdf-resultat'); corps.appendChild(res);
      corps.appendChild(el('p', 'tpdf-aide', 'Les fichiers sont traités sur ce poste ; seule la liste des étapes d\'une action est enregistrée sur le serveur.'));
      function dessiner() {
        zone.textContent = '';
        if (!etat.etapes.length) zone.appendChild(el('p', 'tpdf-aide', 'Aucune étape.'));
        etat.etapes.forEach(function (e, i) { zone.appendChild(editeurEtape(e, function () { etat.etapes.splice(i, 1); dessiner(); }, function () {})); });
      }
      var liste = [];
      async function charger() {
        try { liste = (await api_('GET')).actions || []; } catch (e) { liste = []; }
        actions.querySelectorAll('option:not(:first-child)').forEach(function (o) { o.remove(); });
        liste.forEach(function (a) { var o = el('option', null, a.nom); o.value = String(a.id); actions.appendChild(o); });
      }
      actions.addEventListener('change', function () {
        var a = liste.find(function (x) { return String(x.id) === actions.value; }); if (!a) return;
        etat.etapes = etapesValides(a.etapes); nom.value = a.nom; dessiner();
      });
      retirerA.addEventListener('click', async function () {
        var a = liste.find(function (x) { return String(x.id) === actions.value; }); if (!a) { api.toast('Choisir une action.', 'info'); return; }
        try { await api_('DELETE', '/' + a.id); api.toast('Action « ' + a.nom + ' » retirée.', 'success'); etat.etapes = []; nom.value = ''; dessiner(); await charger(); }
        catch (e) { api.toast(e.message, 'danger'); }
      });
      bAj.addEventListener('click', function () { etat.etapes.push({ type: typ.value, p: Object.assign({}, TYPES[typ.value].defaut) }); dessiner(); });
      bSv.addEventListener('click', async function () {
        if (!nom.value.trim()) { api.toast('Nom obligatoire.', 'danger'); nom.focus(); return; }
        if (!etat.etapes.length) { api.toast('Ajouter au moins une étape.', 'danger'); return; }
        try { await api_('PUT', '', { nom: nom.value.trim(), etapes: etat.etapes }); api.toast('Action « ' + nom.value.trim() + ' » enregistrée.', 'success'); await charger(); }
        catch (e) { api.toast(e.message, 'danger'); }
      });
      dessiner(); charger();
      api.ouvrirModale('Traitement par lot', corps, [
        { txt: 'Fermer', fn: api.fermerModale },
        { txt: 'Traiter les fichiers', plein: true, fn: async function () {
          var f = Array.prototype.slice.call(fic.files || []);
          if (!f.length) { api.toast('Choisir les fichiers à traiter.', 'danger'); return; }
          if (!etat.etapes.length) { api.toast('Ajouter au moins une étape.', 'danger'); return; }
          api.occuper('Traitement par lot…');
          var ok = 0;
          try {
            for (var i = 0; i < f.length; i++) {
              res.textContent = 'Fichier ' + (i + 1) + ' / ' + f.length + ' : ' + f[i].name + '…';
              try {
                var r = await traiter(f[i], etapesValides(etat.etapes), i + 1, function (m) { res.textContent = f[i].name + ' — ' + m + '…'; });
                api.telecharger(r.octets, r.nom); ok++;
                await new Promise(function (x) { setTimeout(x, 300); });
              } catch (e) { api.toast('« ' + f[i].name + ' » : ' + api.msgErreur(e), 'danger'); }
            }
            res.textContent = ok + ' fichier(s) traité(s) sur ' + f.length + '.';
            api.toast(res.textContent, ok ? 'success' : 'danger');
          } finally { api.liberer(); }
        } }
      ], { cle: 'lot', large: true });
    }
    EXT.actions.lot = { sansDoc: true, fn: panneauLot }; EXT.panneaux.lot = panneauLot;
    EXT.boutons.push({ groupe: 'vide', html: '<button type="button" class="tpdf-b" data-act="lot" data-bulle="Lot">' + api.ico('lot', 16) + '<span>Traitement par lot</span></button>' });
  });
})();
