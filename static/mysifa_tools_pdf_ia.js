/*
 * MyTools — éditeur PDF : fonctions IA (menu « IA », camaïeu violet).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Seules ces fonctions font sortir le document du poste :
 *   résumer, poser une question, extraire des données en tableau (CSV),
 *   détecter les champs d'un PDF à plat → envoi du PDF produit à
 *     /api/tools/pdf/ia/* (Claude, suivi dans ia_usage) ;
 *   traduire en gardant la mise en page → chaque bloc de texte est envoyé à
 *     /api/translate (DeepL), puis posé à la place du texte d'origine avec le
 *     moteur de « Modifier le texte ».
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // Champ détecté (coordonnées 0–1000, origine haut-gauche) -> boîte en points.
  function boiteDetectee(c, W, H) {
    return { x: c.x / 1000 * W, y: c.y / 1000 * H, w: Math.max(8, c.l / 1000 * W), h: Math.max(8, c.h / 1000 * H) };
  }
  // Un bloc qui mérite traduction : au moins deux lettres, pas qu'un code ou un nombre.
  function aTraduire(t) { return /\p{L}{2,}/u.test(String(t || '')) && !/^[\p{Lu}\d\s._\/-]{1,6}$/u.test(String(t).trim()); }
  // Taille réduite pour qu'un texte traduit tienne dans la largeur d'origine (60 % au plus bas).
  function tailleAjustee(taille, largeurCible, largeurTexte) {
    if (!(largeurTexte > largeurCible * 1.02) || !(largeurCible > 0)) return taille;
    return Math.max(taille * 0.6, taille * largeurCible / largeurTexte);
  }

  M._interne = M._interne || {};
  M._interne.ia = { boiteDetectee: boiteDetectee, aTraduire: aTraduire, tailleAjustee: tailleAjustee };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    var MENTION = 'Le PDF est envoyé à l\'assistant IA (Claude) pour cette demande ; rien n\'est conservé par l\'outil.';

    Object.assign(api.IC, {
      ia: '<path d="M12 3l1.9 5.4L19.5 10l-5.6 1.6L12 17l-1.9-5.4L4.5 10l5.6-1.6z"/><path d="M18.5 15.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z"/>',
      resumer: '<path d="M5 6h14M5 10h14M5 14h9M5 18h6"/>',
      question: '<path d="M4.5 5.5h15v10h-8l-4 3.5v-3.5h-3z"/><path d="M10 9a2 2 0 1 1 2.5 1.9c-.4.1-.5.4-.5.8v.3M12 14h.01"/>',
      traduire: '<path d="M4 6h8M8 4v2M5.5 6c.5 3 2.5 5 5 6"/><path d="M10.5 6c-.5 3-2.5 5.5-6 6.5"/><path d="M12.5 20l3.5-9 3.5 9M13.8 17h4.4"/>',
      extraireIa: '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M9 9.5v10M15 9.5v10"/>',
      champsIa: '<rect x="3.5" y="6.5" width="17" height="11" rx="2"/><path d="M7 10v4M6 10h2M6 14h2M11 12h6"/>'
    });
    EXT.menus.ia = { libelle: 'IA', icone: 'ia', ordre: 9, ia: true, items: [
      { act: 'iaResumer', icone: 'resumer', libelle: 'Résumer le document', bulle: 'Résumer', doc: 1 },
      { act: 'iaQuestion', icone: 'question', libelle: 'Poser une question au document', bulle: 'Question', doc: 1 },
      { act: 'iaExtraire', icone: 'extraireIa', libelle: 'Extraire des données (CSV)', bulle: 'Extraire', doc: 1 },
      { act: 'iaTraduire', icone: 'traduire', libelle: 'Traduire en gardant la mise en page', bulle: 'Traduire', doc: 1 },
      { act: 'iaChamps', icone: 'champsIa', libelle: 'Détecter les champs (PDF à plat)', bulle: 'Champs', doc: 1 }
    ] };

    async function envoyer(route, champs) {
      var b = await api.construire(), fd = new FormData();
      fd.append('pdf', new Blob([b], { type: 'application/pdf' }), api.nomBase() + '.pdf');
      Object.keys(champs || {}).forEach(function (k) { fd.append(k, champs[k]); });
      var r = await fetch('/api/tools/pdf/ia/' + route, { method: 'POST', body: fd, credentials: 'same-origin' });
      var j = null; try { j = await r.json(); } catch (e) { j = null; }
      if (!r.ok) throw new Error((j && j.detail) || ('service IA indisponible (' + r.status + ')'));
      return j;
    }
    // Bouton IA qui pulse pendant l'appel ; erreurs en toast.
    function lancer(bouton, zone, fn) {
      return async function () {
        if (bouton.disabled) return;
        bouton.disabled = true; bouton.classList.add('ia-travail'); zone.classList.add('ia-travail');
        try { await fn(); }
        catch (e) { api.toast(e && e.message ? e.message.replace(/^Opération impossible — /, '') : 'Erreur IA.', 'danger'); }
        finally { bouton.disabled = false; bouton.classList.remove('ia-travail'); zone.classList.remove('ia-travail'); }
      };
    }
    function boutonIa(txt, bulle) { var b = el('button', 'tpdf-b ia-btn', txt); b.type = 'button'; b.setAttribute('data-bulle', bulle || txt); return b; }
    function copier(txt) {
      try { navigator.clipboard.writeText(txt); api.toast('Copié.', 'success'); } catch (e) { api.toast('Copie impossible dans ce navigateur.', 'danger'); }
    }

    /* ── Résumer ──────────────────────────────────────────────────────── */
    function panneauResumer() {
      var corps = el('div'), go = boutonIa('Résumer', 'Résumer'), out = el('div', 'tpdf-ia-sortie');
      corps.appendChild(el('p', 'ia-texte', MENTION)); corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        out.textContent = 'Lecture du document…';
        var r = await envoyer('resumer');
        out.textContent = r.texte;
      }));
      api.ouvrirModale('Résumer le document', corps, [
        { txt: 'Copier', bulle: 'Copier', fn: function () { if (out.textContent) copier(out.textContent); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'ia-resumer', ia: true });
    }
    EXT.actions.iaResumer = { fn: panneauResumer }; EXT.panneaux['ia-resumer'] = panneauResumer;

    /* ── Question ─────────────────────────────────────────────────────── */
    function panneauQuestion() {
      var corps = el('div'), fil = el('div', 'tpdf-ia-fil'), q = el('textarea', 'tpdf-champ'), go = boutonIa('Demander', 'Demander');
      q.rows = 2; q.placeholder = 'Ex. Quelle est la date d\'échéance ? Quelles pénalités en cas de retard ?';
      corps.appendChild(el('p', 'ia-texte', MENTION)); corps.appendChild(fil); corps.appendChild(q); corps.appendChild(go);
      var envoi = lancer(go, fil, async function () {
        var v = q.value.trim(); if (!v) { q.focus(); return; }
        fil.appendChild(el('div', 'tpdf-ia-q', v)); q.value = '';
        var att = el('div', 'tpdf-ia-r', '…'); fil.appendChild(att);
        try { var r = await envoyer('question', { question: v }); att.textContent = r.reponse; }
        catch (e) { att.remove(); throw e; }
        fil.scrollTop = fil.scrollHeight;
      });
      go.addEventListener('click', envoi);
      q.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); envoi(); } });
      api.ouvrirModale('Poser une question au document', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-question', ia: true });
      requestAnimationFrame(function () { q.focus(); });
    }
    EXT.actions.iaQuestion = { fn: panneauQuestion }; EXT.panneaux['ia-question'] = panneauQuestion;

    /* ── Extraire des données ─────────────────────────────────────────── */
    function panneauExtraire() {
      var corps = el('div'), nat = el('select', 'tpdf-champ'), cons = el('textarea', 'tpdf-champ'), go = boutonIa('Extraire', 'Extraire'), out = el('div', 'tpdf-ia-sortie');
      [['facture', 'Facture'], ['bl', 'Bon de livraison'], ['fiche', 'Fiche technique'], ['libre', 'Autre (préciser)']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; nat.appendChild(o); });
      cons.rows = 2; cons.placeholder = 'Facultatif : colonnes voulues, pages à lire…';
      corps.appendChild(el('p', 'ia-texte', MENTION));
      corps.appendChild(api.champ('Type de document', nat)); corps.appendChild(api.champ('Consigne', cons));
      corps.appendChild(go); corps.appendChild(out);
      var donnees = null;
      go.addEventListener('click', lancer(go, out, async function () {
        out.textContent = 'Lecture du document…';
        donnees = await envoyer('extraire', { nature: nat.value, consigne: cons.value });
        out.textContent = '';
        var t = el('table', 'tpdf-ia-table'), th = el('tr');
        donnees.colonnes.forEach(function (c) { th.appendChild(el('th', null, c)); }); t.appendChild(th);
        donnees.lignes.forEach(function (l) { var tr = el('tr'); l.forEach(function (c) { tr.appendChild(el('td', null, c)); }); t.appendChild(tr); });
        var w = el('div', 'tpdf-ia-tablewrap'); w.appendChild(t); out.appendChild(w);
        out.appendChild(el('p', 'tpdf-aide', donnees.lignes.length + ' ligne' + (donnees.lignes.length > 1 ? 's' : '') + (donnees.remarques ? ' · ' + donnees.remarques : '')));
      }));
      api.ouvrirModale('Extraire des données', corps, [
        { txt: 'Télécharger le CSV', bulle: 'CSV', fn: function () {
          if (!donnees) { api.toast('Lancer l\'extraction d\'abord.', 'info'); return; }
          var csv = (M._interne.revision && M._interne.revision.csv) ? M._interne.revision.csv([donnees.colonnes].concat(donnees.lignes)) : '';
          var u = api.urlObjet(new Blob([csv], { type: 'text/csv;charset=utf-8' })), a = el('a'); a.href = u; a.download = api.nomBase() + '-donnees.csv'; a.style.display = 'none';
          S().el.appendChild(a); a.click(); a.remove();
        } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'ia-extraire', ia: true, large: true });
    }
    EXT.actions.iaExtraire = { fn: panneauExtraire }; EXT.panneaux['ia-extraire'] = panneauExtraire;

    /* ── Détecter les champs ──────────────────────────────────────────── */
    function panneauChamps() {
      var corps = el('div'), go = boutonIa('Détecter les champs', 'Détecter'), out = el('div', 'tpdf-ia-sortie');
      corps.appendChild(el('p', 'ia-texte', MENTION));
      corps.appendChild(el('p', 'tpdf-aide', 'Les zones à remplir (lignes, cases, cadres) deviennent des champs remplissables, à vérifier et ajuster comme les autres (outil Champ).'));
      corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        if (!EXT.types.champ) throw new Error('Module formulaires indisponible.');
        out.textContent = 'Lecture du document…';
        var r = await envoyer('champs'), s = S(), avant = api.snapshot(), n = 0;
        var pris = [];
        Object.keys(s.sources).forEach(function (k) { s.sources[k].champs.forEach(function (c) { pris.push(c.nom); }); });
        s.pages.forEach(function (p) { p.annots.forEach(function (a) { if (a.t === 'champ') pris.push(a.nom); }); });
        r.champs.forEach(function (c) {
          var p = s.pages[c.page - 1]; if (!p) return;
          var d = api.dims(p), b = boiteDetectee(c, d.w, d.h);
          var nom = c.nom && pris.indexOf(c.nom) < 0 ? c.nom : M._interne.formulaires.nomUnique(c.nom || 'Champ', pris);
          pris.push(nom);
          var genre = c.type === 'case' ? 'case' : c.type;
          var a = { id: api.nid('n'), t: 'champ', genre: genre, nom: nom, requis: false, defaut: genre === 'case' ? false : '',
            options: c.options || [], taille: 0, x: b.x, y: b.y, w: b.w, h: b.h };
          if (genre === 'case') { var cote = Math.max(10, Math.min(b.w, b.h)); a.w = a.h = cote; }
          p.annots.push(a); n++;
        });
        if (n) { api.pushHist(avant); api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre(); }
        out.textContent = n ? n + ' champ' + (n > 1 ? 's posés' : ' posé') + ' — vérifier les positions, puis enregistrer.' : 'Aucune zone à remplir trouvée.';
        if (n) api.toast(out.textContent, 'success');
      }));
      api.ouvrirModale('Détecter les champs', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-champs', ia: true });
    }
    EXT.actions.iaChamps = { fn: panneauChamps }; EXT.panneaux['ia-champs'] = panneauChamps;

    /* ── Traduire en gardant la mise en page ──────────────────────────── */
    function panneauTraduire() {
      var s = S(), corps = el('div'), langue = el('select', 'tpdf-champ'), pages = el('select', 'tpdf-champ'), go = boutonIa('Traduire', 'Traduire'), out = el('div', 'tpdf-ia-sortie');
      [['courante', 'Page courante'], ['toutes', 'Toutes les pages']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; pages.appendChild(o); });
      fetch('/api/translate/langs', { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) {
        (j.langs || []).forEach(function (l) { var o = el('option', null, l.label); o.value = l.code; langue.appendChild(o); });
        langue.value = (j.langs || []).some(function (l) { return l.code === 'EN-GB'; }) ? 'EN-GB' : ((j.langs || [])[0] || {}).code || '';
      }).catch(function () { var o = el('option', null, 'Anglais'); o.value = 'EN-GB'; langue.appendChild(o); });
      corps.appendChild(el('p', 'ia-texte', 'Chaque bloc de texte est envoyé au service de traduction (DeepL), puis posé à la place de l\'original avec la même police, taille réduite si la traduction est plus longue.'));
      corps.appendChild(api.champ('Traduire vers', langue)); corps.appendChild(api.champ('Pages', pages));
      corps.appendChild(el('p', 'tpdf-aide tpdf-avert', (EXT.texte && EXT.texte.AVERTISSEMENT) || ''));
      corps.appendChild(el('p', 'tpdf-aide', 'Pages pivotées, recadrées ou scannées ignorées. Chaque bloc traduit reste modifiable ; Ctrl+Z annule tout.'));
      corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        if (!EXT.texte) throw new Error('Module « Modifier le texte » indisponible.');
        var l = pages.value === 'toutes' ? s.pages.slice() : [api.pageCourante()], avant = api.snapshot(), n = 0, ign = 0, erreurs = 0;
        api.occuper('Traduction…');
        try {
          for (var i = 0; i < l.length; i++) {
            var p = l[i], info = await EXT.texte.blocsPage(p);
            if (!info) { ign++; continue; }
            var blocs = info.blocs.filter(function (b) { return aTraduire(b.str); });
            for (var k = 0; k < blocs.length; k += 4) {
              out.textContent = 'Page ' + (s.pages.indexOf(p) + 1) + ' — blocs ' + (k + 1) + ' à ' + Math.min(blocs.length, k + 4) + ' sur ' + blocs.length + '…';
              await Promise.all(blocs.slice(k, k + 4).map(async function (bl) {
                var r = await fetch('/api/translate', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ text: bl.str, target_lang: langue.value }) });
                if (!r.ok) { erreurs++; return; }
                var tr = ((await r.json()) || {}).translated;
                if (!tr || tr === bl.str) return;
                var a = EXT.texte.trouverRemplace(p, bl.premier);
                if (!a) { a = await EXT.texte.preparer(p, info.d, bl, info.tc, info.bornes); p.annots.push(a); }
                var taille0 = a.tailleOrig || a.taille; a.tailleOrig = taille0;
                a.texte = tr; a.esp = 0; a.largeur = null;
                a.taille = tailleAjustee(taille0, a.w, EXT.texte.mesure(tr, Object.assign({}, a, { taille: taille0 })));
                n++;
              }));
            }
          }
        } finally { api.liberer(); }
        if (n) { api.pushHist(avant); api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre(); }
        out.textContent = n + ' bloc' + (n > 1 ? 's traduits' : ' traduit') + (ign ? ' · ' + ign + ' page(s) ignorée(s)' : '') + (erreurs ? ' · ' + erreurs + ' bloc(s) en échec' : '') + '.';
        if (n) api.toast(out.textContent, 'success'); else if (erreurs) throw new Error('Service de traduction indisponible.');
      }));
      api.ouvrirModale('Traduire en gardant la mise en page', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-traduire', ia: true });
    }
    EXT.actions.iaTraduire = { fn: panneauTraduire }; EXT.panneaux['ia-traduire'] = panneauTraduire;

    /* ── Lot 4 : sélection, contrats, BAT, génération ─────────────────── */
    Object.assign(api.IC, {
      iaZone: '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/><path d="M12 8l1 2.6 2.6 1-2.6 1L12 15l-1-2.4-2.6-1 2.6-1z"/>',
      contrats: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M8.5 13h7M8.5 16.5h4"/>',
      batIa: '<rect x="3.5" y="5" width="11" height="14" rx="1.5"/><path d="M6.5 9h5M6.5 12h5"/><path d="M15.5 13.5l2 2 4-4.5"/>',
      generer: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 11v6M9 14h6"/>'
    });
    api.LIBELLES.iaZone = 'Sélection pour l\'IA';
    api.AIDE_OUTIL.iaZone = 'Tracer un cadre autour du passage à expliquer ou reformuler.';
    EXT.menus.ia.items.push({ separe: true },
      { act: 'iaSelection', icone: 'iaZone', libelle: 'Expliquer ou reformuler un passage', bulle: 'Passage', doc: 1 },
      { act: 'iaContrats', icone: 'contrats', libelle: 'Comparer deux contrats', bulle: 'Contrats', doc: 1 },
      { act: 'iaBat', icone: 'batIa', libelle: 'Vérifier le BAT contre la fiche technique', bulle: 'Vérifier', doc: 1 },
      { act: 'iaGenerer', icone: 'generer', libelle: 'Remplir le modèle à partir de données', bulle: 'Générer', doc: 1 });

    EXT.actions.iaSelection = { fn: function () { api.choisirOutil('iaZone'); } };
    EXT.outils.iaZone = { down: function (pt) { return { t: 'iazone', x: pt.x, y: pt.y, w: 0, h: 0 }; } };
    EXT.types.iazone = {
      boiteTournante: true,
      tailleDefaut: function () { return [200, 60]; },
      dessiner: function (a, g, z) { api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, 'class': 'tpdf-iazone', 'stroke-width': 1.5 / z }, g); },
      apresCreation: function (a) {
        var s = S(), p = api.pageCourante(), d = api.dims(p);
        setTimeout(async function () {
          p.annots = p.annots.filter(function (x) { return x !== a; }); s.annSel = null; api.choisirOutil('select'); api.dessinerCalque();
          var items = await api.texteDe(p), dedans = items.filter(function (it) {
            if (!it.transform || !it.str || !it.str.trim()) return false;
            var q = api.versVue(d.meta.view, d.R, it.transform[4], it.transform[5]);
            return q[0] >= a.x - 2 && q[0] <= a.x + a.w && q[1] >= a.y && q[1] <= a.y + a.h + 4;
          });
          var texte = dedans.map(function (it) { return it.str + (it.hasEOL ? '\n' : ' '); }).join('').replace(/[ \t]+\n/g, '\n').trim();
          panneauSelection(texte);
        }, 0);
      },
      exporter: async function () { /* cadre de travail */ }
    };
    function panneauSelection(texte) {
      var corps = el('div'), src = el('textarea', 'tpdf-champ'), out = el('div', 'tpdf-ia-sortie'), lg = el('div', 'tpdf-ligne');
      src.rows = 5; src.value = texte || '';
      corps.appendChild(el('p', 'ia-texte', 'Seul le passage ci-dessous est envoyé à l\'assistant IA.'));
      corps.appendChild(api.champ('Passage', src));
      if (!texte) corps.appendChild(el('p', 'tpdf-aide', 'Aucun texte dans ce cadre (scan ?) : coller le passage ou lancer l\'OCR.'));
      [['expliquer', 'Expliquer'], ['reformuler', 'Reformuler'], ['resumer', 'Résumer']].forEach(function (x) {
        var b = boutonIa(x[1], x[1]);
        b.addEventListener('click', lancer(b, out, async function () {
          if (!src.value.trim()) throw new Error('Aucun texte sélectionné.');
          var fd = new FormData(); fd.append('texte', src.value); fd.append('mode', x[0]);
          var r = await fetch('/api/tools/pdf/ia/selection', { method: 'POST', body: fd, credentials: 'same-origin' });
          var j = null; try { j = await r.json(); } catch (e) { j = null; }
          if (!r.ok) throw new Error((j && j.detail) || 'Service IA indisponible.');
          out.textContent = j.texte;
        }));
        lg.appendChild(b);
      });
      corps.appendChild(lg); corps.appendChild(out);
      api.ouvrirModale('Passage sélectionné', corps, [
        { txt: 'Copier le résultat', bulle: 'Copier', fn: function () { if (out.textContent) copier(out.textContent); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { ia: true });
    }

    function panneauContrats() {
      var corps = el('div'), fic = el('input', 'tpdf-champ'), go = boutonIa('Comparer les clauses', 'Comparer'), out = el('div', 'tpdf-ia-sortie');
      fic.type = 'file'; fic.accept = '.pdf,application/pdf';
      corps.appendChild(el('p', 'ia-texte', 'Les deux PDF sont envoyés à l\'assistant IA (Claude) pour cette demande.'));
      corps.appendChild(api.champ('Autre version du contrat (le document ouvert sert de référence)', fic));
      corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        var f = fic.files && fic.files[0]; if (!f) throw new Error('Choisir l\'autre version.');
        out.textContent = 'Lecture des deux versions…';
        var r = await envoyer('contrats', { pdf2: new File([await f.arrayBuffer()], f.name, { type: 'application/pdf' }) });
        out.textContent = r.texte;
      }));
      api.ouvrirModale('Comparer deux contrats', corps, [
        { txt: 'Copier', bulle: 'Copier', fn: function () { if (out.textContent) copier(out.textContent); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'ia-contrats', ia: true, large: true });
    }
    EXT.actions.iaContrats = { fn: panneauContrats }; EXT.panneaux['ia-contrats'] = panneauContrats;

    function panneauBat() {
      var corps = el('div'), q = el('input', 'tpdf-champ'), fiches = el('select', 'tpdf-champ'), go = boutonIa('Vérifier le BAT', 'Vérifier'), out = el('div', 'tpdf-lc');
      q.type = 'search'; q.placeholder = 'Rechercher une fiche (référence, format, support…)';
      corps.appendChild(el('p', 'ia-texte', 'Le BAT (document ouvert) et la fiche technique choisie sont envoyés à l\'assistant IA.'));
      corps.appendChild(api.champ('Fiche technique', q)); corps.appendChild(fiches); corps.appendChild(go); corps.appendChild(out);
      var minuteur = null;
      async function chercher() {
        try {
          var r = await fetch('/api/fiches-techniques/list?limit=50&q=' + encodeURIComponent(q.value.trim()), { credentials: 'same-origin' });
          var j = await r.json(); if (!r.ok) throw new Error((j && j.detail) || 'Fiches techniques inaccessibles.');
          fiches.textContent = '';
          (j.rows || []).forEach(function (f) { var o = el('option', null, [f.reference, f.designation || f.format, f.client].filter(Boolean).join(' — ')); o.value = f.id; fiches.appendChild(o); });
          if (!(j.rows || []).length) { var o0 = el('option', null, 'Aucun résultat pour « ' + q.value + ' »'); o0.value = ''; fiches.appendChild(o0); }
        } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      }
      q.addEventListener('input', function () { clearTimeout(minuteur); minuteur = setTimeout(chercher, 250); });
      chercher();
      go.addEventListener('click', lancer(go, out, async function () {
        if (!fiches.value) throw new Error('Choisir une fiche technique.');
        out.textContent = '';
        var r = await envoyer('bat', { fiche_id: fiches.value });
        out.appendChild(el('p', 'tpdf-resultat', r.synthese));
        var lib = { conforme: 'Conforme', ecart: 'Écart', a_verifier: 'À vérifier' };
        r.points.forEach(function (pt) {
          var b = el('button', 'tpdf-lc-item tpdf-bat-' + pt.statut); b.type = 'button';
          b.appendChild(el('span', 'tpdf-lc-nom', pt.sujet)); b.appendChild(el('span', 'tpdf-lc-type', lib[pt.statut] || pt.statut));
          b.appendChild(el('span', 'tpdf-lc-val', 'Attendu : ' + pt.attendu + ' · Constaté : ' + pt.constate));
          b.addEventListener('click', function () { api.fermerModale(); api.allerPage(Math.max(0, (pt.page || 1) - 1), true); });
          out.appendChild(b);
        });
      }));
      api.ouvrirModale('Vérifier le BAT', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-bat', ia: true, large: true });
    }
    EXT.actions.iaBat = { fn: panneauBat }; EXT.panneaux['ia-bat'] = panneauBat;

    function panneauGenerer() {
      var corps = el('div'), don = el('textarea', 'tpdf-champ'), go = boutonIa('Remplir le modèle', 'Remplir'), out = el('div', 'tpdf-ia-sortie');
      var champs = EXT.formulaire ? EXT.formulaire.champsDuDocument() : [];
      don.rows = 6; don.placeholder = 'Coller les données : texte libre, courriel, ligne de tableau…';
      corps.appendChild(el('p', 'ia-texte', 'Le modèle (document ouvert) et les données sont envoyés à l\'assistant IA, qui remplit les champs.'));
      corps.appendChild(el('p', 'tpdf-aide', champs.length ? champs.length + ' champ(s) dans le modèle. Pour un CSV d\'une ligne par document, sans IA : Réviser › Réponses du formulaire.' : 'Ce document n\'a pas de champ : en créer (outil Champ) ou les détecter (IA › Détecter les champs).'));
      corps.appendChild(api.champ('Données', don)); corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        if (!champs.length) throw new Error('Ce modèle n\'a pas de champ à remplir.');
        out.textContent = 'Remplissage…';
        var r = await envoyer('remplir', { champs: JSON.stringify(champs.map(function (f) { return { nom: f.nom, type: f.cree ? f.cree.genre : (f.c && f.c.type), options: (f.cree ? f.cree.options : f.c && f.c.options) || [] }; })), donnees: don.value });
        var noms = Object.keys(r.valeurs || {});
        var avant = api.snapshot(), n = EXT.formulaire.appliquer(noms, noms.map(function (k) { return r.valeurs[k]; }));
        api.pushHist(avant); api.rendrePage(); api.rendreProps(); api.dessinerCalque();
        out.textContent = n + ' champ(s) rempli(s). Vérifier, puis enregistrer.';
      }));
      api.ouvrirModale('Remplir le modèle à partir de données', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-generer', ia: true });
    }
    EXT.actions.iaGenerer = { fn: panneauGenerer }; EXT.panneaux['ia-generer'] = panneauGenerer;
  });
})();
