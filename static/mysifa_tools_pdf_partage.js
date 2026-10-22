/*
 * MyTools — éditeur PDF : partager le document.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * S'appuie sur les API existantes, sans en créer :
 *   messagerie      GET /api/chat/channels, POST /api/chat/channels/{id}/messages (pièce jointe)
 *   NC (MyQualité)  GET /api/qualite/nc, POST /api/qualite/nc/{id}/fichiers
 *   dossier / OF    POST /api/produits/documents (no_dossier, of_numero) — mémoire produit
 *   tâche           POST /api/taches/{id}/fichiers
 *   tiers           parapheur (window.MyToolsParapheur.ouvrir), Espace SIFA du destinataire
 * Ici, le PDF quitte le poste : il est envoyé au serveur MySifa, à la demande.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function bouton(t, cls, bulle) { var b = el('button', 'tpdf-b' + (cls ? ' ' + cls : ''), t); b.type = 'button'; b.setAttribute('data-bulle', bulle || t); return b; }
    async function lireJson(r) { var j = null; try { j = await r.json(); } catch (e) { j = null; } if (!r.ok) throw new Error((j && (j.detail || j.message)) || 'Service indisponible (' + r.status + ').'); return j; }
    async function envoyerFichier(url, champ, extra) {
      var fd = new FormData(), b = await api.construire();
      fd.append(champ, new Blob([b], { type: 'application/pdf' }), api.nomBase() + '.pdf');
      Object.keys(extra || {}).forEach(function (k) { fd.append(k, extra[k]); });
      return lireJson(await fetch(url, { method: 'POST', body: fd, credentials: 'same-origin' }));
    }

    api.IC.partager = '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 10.8l7.6-3.6M8.2 13.2l7.6 3.6"/>';
    api.BULLES.partager = 'Partager';
    EXT.boutons.push({ groupe: 'fichier', html: api.bouton('partager', 'partager', 'Partager le document', { doc: 1 }) });

    function panneauPartager() {
      var corps = el('div'), onglets = el('div', 'tpdf-seg'), zone = el('div', 'tpdf-partage');
      [['messagerie', 'Messagerie'], ['rattacher', 'Rattacher'], ['tiers', 'À remplir par un tiers']].forEach(function (x, i) {
        var b = el('button', 'tpdf-btn' + (i ? '' : ' tpdf-actif'), x[1]); b.type = 'button'; b.setAttribute('data-bulle', x[1]);
        b.addEventListener('click', function () { onglets.querySelectorAll('button').forEach(function (y) { y.classList.toggle('tpdf-actif', y === b); }); afficher(x[0]); });
        onglets.appendChild(b);
      });
      corps.appendChild(onglets); corps.appendChild(zone);
      corps.appendChild(el('p', 'tpdf-aide', 'Le PDF tel qu\'il sera enregistré (annotations comprises) est envoyé au serveur MySifa.'));
      function afficher(o) {
        zone.textContent = '';
        if (o === 'messagerie') return messagerie();
        if (o === 'rattacher') return rattacher();
        return tiers();
      }
      async function messagerie() {
        var canal = el('select', 'tpdf-champ'), msg = el('textarea', 'tpdf-champ'), go = bouton('Envoyer', 'tpdf-b-plein', 'Envoyer');
        msg.rows = 3; msg.placeholder = 'Message (facultatif)';
        zone.appendChild(api.champ('Discussion', canal)); zone.appendChild(api.champ('Message', msg)); zone.appendChild(go);
        try {
          var j = await lireJson(await fetch('/api/chat/channels', { credentials: 'same-origin' }));
          var l = Array.isArray(j) ? j : (j.channels || j.items || []);
          if (!l.length) { var o0 = el('option', null, 'Aucune discussion'); o0.value = ''; canal.appendChild(o0); }
          l.forEach(function (c) { var o = el('option', null, c.name || c.other_nom || c.titre || ('Discussion ' + c.id)); o.value = c.id; canal.appendChild(o); });
        } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
        go.addEventListener('click', async function () {
          if (!canal.value) { api.toast('Choisir une discussion.', 'danger'); return; }
          go.disabled = true; api.occuper('Envoi…');
          try {
            await envoyerFichier('/api/chat/channels/' + encodeURIComponent(canal.value) + '/messages', 'file', { body: msg.value.trim() });
            api.toast('Document envoyé dans la discussion.', 'success'); api.fermerModale();
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
          finally { go.disabled = false; api.liberer(); }
        });
      }
      function rattacher() {
        var cible = el('select', 'tpdf-champ');
        [['dossier', 'Dossier de production / OF'], ['nc', 'Non-conformité (MyQualité)'], ['tache', 'Tâche']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; cible.appendChild(o); });
        zone.appendChild(api.champ('Rattacher à', cible));
        var detail = el('div'); zone.appendChild(detail);
        var go = bouton('Rattacher', 'tpdf-b-plein', 'Rattacher'); zone.appendChild(go);
        var champs = {};
        async function maj() {
          detail.textContent = ''; champs = {};
          if (cible.value === 'dossier') {
            champs.dossier = el('input', 'tpdf-champ'); champs.dossier.type = 'text'; champs.dossier.placeholder = 'Référence dossier';
            champs.of = el('input', 'tpdf-champ'); champs.of.type = 'text'; champs.of.placeholder = 'Numéro d\'OF (facultatif)';
            detail.appendChild(api.champ('Référence dossier', champs.dossier)); detail.appendChild(api.champ('Numéro d\'OF', champs.of));
          } else if (cible.value === 'nc') {
            champs.nc = el('select', 'tpdf-champ'); detail.appendChild(api.champ('Non-conformité', champs.nc));
            try {
              var j = await lireJson(await fetch('/api/qualite/nc', { credentials: 'same-origin' }));
              var l = Array.isArray(j) ? j : (j.items || j.ncs || j.rows || []);
              l.slice(0, 300).forEach(function (n) { var o = el('option', null, (n.numero || ('NC ' + n.id)) + ' — ' + (n.titre || n.objet || n.description || '').slice(0, 60)); o.value = n.id; champs.nc.appendChild(o); });
              if (!l.length) { var o0 = el('option', null, 'Aucune NC'); o0.value = ''; champs.nc.appendChild(o0); }
            } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
          } else {
            champs.tache = el('input', 'tpdf-champ'); champs.tache.type = 'number'; champs.tache.min = 1; champs.tache.placeholder = 'Numéro de la tâche';
            detail.appendChild(api.champ('Tâche n°', champs.tache));
          }
        }
        cible.addEventListener('change', maj); maj();
        go.addEventListener('click', async function () {
          go.disabled = true; api.occuper('Envoi…');
          try {
            if (cible.value === 'dossier') {
              if (!champs.dossier.value.trim() && !champs.of.value.trim()) throw new Error('Référence dossier ou numéro d\'OF obligatoire.');
              var r = await envoyerFichier('/api/produits/documents', 'file', { no_dossier: champs.dossier.value.trim(), of_numero: champs.of.value.trim() });
              api.toast(r && r.statut === 'rattache' ? 'Document rattaché au dossier.' : 'Document déposé ; rattachement à confirmer dans la mémoire produit.', 'success');
            } else if (cible.value === 'nc') {
              if (!champs.nc.value) throw new Error('Choisir une non-conformité.');
              await envoyerFichier('/api/qualite/nc/' + encodeURIComponent(champs.nc.value) + '/fichiers', 'file');
              api.toast('Document joint à la non-conformité.', 'success');
            } else {
              var t = parseInt(champs.tache.value, 10); if (!(t > 0)) throw new Error('Numéro de tâche invalide.');
              await envoyerFichier('/api/taches/' + t + '/fichiers', 'fichier');
              api.toast('Document joint à la tâche.', 'success');
            }
            api.fermerModale();
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
          finally { go.disabled = false; api.liberer(); }
        });
      }
      function tiers() {
        zone.appendChild(el('p', 'tpdf-aide', 'Le document part dans le parapheur : le destinataire le reçoit dans son Espace SIFA, avec une zone de signature. Les champs restent remplissables dans le PDF qu\'il télécharge.'));
        zone.appendChild(el('p', 'tpdf-aide tpdf-avert', 'Limite actuelle : le parapheur recueille la signature, pas les valeurs saisies dans les champs en ligne. Pour un questionnaire rempli en ligne dans l\'Espace, utiliser l\'outil Formulaires.'));
        var go = bouton('Préparer l\'envoi', 'tpdf-b-plein', 'Envoyer'); zone.appendChild(go);
        go.addEventListener('click', async function () {
          var s = S(), garde = s.aplatir; s.aplatir = false;
          try {
            if (!window.MyToolsParapheur && api.MON_SRC) { try { await api.chargerScript(api.MON_SRC.replace(/mysifa_tools_pdf\.js/, 'mysifa_tools_parapheur.js')); } catch (e) { /* signalé ci-dessous */ } }
            if (!window.MyToolsParapheur) throw new Error('Parapheur indisponible pour le moment.');
            var b = await api.construire();
            api.fermerModale();
            window.MyToolsParapheur.ouvrir({ octets: b, nom: api.nomBase() + '.pdf' });
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
          finally { s.aplatir = garde; }
        });
      }
      afficher('messagerie');
      api.ouvrirModale('Partager le document', corps, [{ txt: 'Fermer', fn: api.fermerModale }], { cle: 'partager' });
    }
    EXT.actions.partager = { fn: panneauPartager }; EXT.panneaux.partager = panneauPartager;
  });
})();
