/**
 * MySifa — Mes notes : favoris, récentes et mentions ; boutons de la note
 * (favori, recherche, historique, commentaires, export) ; historique des
 * versions ; export PDF / Word / impression ; modèles ; commentaires en marge.
 *
 * Se branche sur la page par window.MySifaNotesPage (static/mysifa_notes.js).
 * API : app/routers/notes_outils.py.
 * Adresse : `historique=1` (+ `version=<id>`), `commentaires=1` (onglet du
 * panneau). Hors adresse : le menu d'export et le choix d'un modèle (gestes
 * d'un instant), la saisie d'un commentaire.
 */
(function () {
  'use strict';
  var PAGE = window.MySifaNotesPage;
  if (!PAGE) return;
  var S = PAGE.S;
  var esc = PAGE.esc;
  var api = PAGE.api;
  var toast = PAGE.toast;

  var R = { favoris: [], recentes: [], mentions: [] };
  var C = { liste: [], resolus: false, brouillon: null, personnes: null, mentions: {}, charge: null };
  var H = { ouvert: false, versions: [], vid: null, ed: null };

  var I = {
    etoile: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>',
    etoilePleine: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>',
    horloge: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/></svg>',
    bulle: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4z"/></svg>',
    export: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><polyline points="7 10 12 15 17 10"/><path d="M5 19h14"/></svg>',
    loupe: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><line x1="16" y1="16" x2="21" y2="21"/></svg>',
  };

  function note() { return S.vue === 'note' ? S.courante : null; }
  function estFavori(id) { return R.favoris.some(function (f) { return f.id === id; }); }
  function aujourdhui() {
    return new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }
  function fermerMroot() { var r = document.getElementById('mroot'); if (r) r.innerHTML = ''; }

  /* ── Favoris, récentes, mentions (barre latérale) ─────────────────────── */

  function chargerRaccourcis() {
    return api('/api/postits/raccourcis').then(function (d) {
      R.favoris = d.favoris || [];
      R.recentes = d.recentes || [];
      R.mentions = d.mentions || [];
      rendreRaccourcis();
      rendreOutils();
    }).catch(function () {});
  }

  function rendreRaccourcis() {
    var el = document.getElementById('nt-raccourcis');
    if (!el) return;
    var courant = note() ? note().id : null;
    function item(n, extra) {
      return '<button type="button" class="nt-rac' + (n.id === courant ? ' active' : '') + '" data-ouvrir="' + n.id + '"' +
        (extra || '') + '><span class="nt-rac-nom">' + esc(n.title || 'Sans titre') + '</span></button>';
    }
    var html = '';
    if (R.mentions.length) {
      html += '<div class="nav-section-label msb-section"><span>Mentions</span><span class="nt-nb nt-nb-alerte">' + R.mentions.length + '</span></div>' +
        R.mentions.slice(0, 5).map(function (m) {
          return '<button type="button" class="nt-rac nt-rac-mention" data-ouvrir="' + m.note_id + '" data-com="1" title="' + esc(m.extrait) + '">' +
            '<span class="nt-rac-nom">' + esc(m.titre) + '</span><span class="nt-rac-detail">' + esc(m.par) + '</span></button>';
        }).join('');
    }
    if (R.favoris.length) {
      html += '<div class="nav-section-label msb-section"><span>Favoris</span></div>' + R.favoris.map(function (f) { return item(f); }).join('');
    }
    var fav = {};
    R.favoris.forEach(function (f) { fav[f.id] = 1; });
    var rec = R.recentes.filter(function (r) { return !fav[r.id]; }).slice(0, 5);
    if (rec.length) {
      html += '<div class="nav-section-label msb-section"><span>Récentes</span></div>' + rec.map(function (r) { return item(r); }).join('');
    }
    el.innerHTML = html;
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#nt-raccourcis [data-ouvrir], #nt-accueil-plus [data-ouvrir]');
    if (!b) return;
    var id = Number(b.dataset.ouvrir);
    PAGE.ouvrir(id).then(function () {
      if (b.dataset.com) PAGE.ouvrirOngletPanneau('commentaires');
    });
  });

  PAGE.sur('accueil', function (zone) {
    if (!zone) return;
    var cartes = R.favoris.map(function (f) { return PAGE.parId(f.id); }).filter(Boolean);
    if (!cartes.length) { zone.innerHTML = ''; return; }
    zone.innerHTML = '<div class="nt-section nt-section-espace">Favoris</div><div class="nt-grille">' + cartes.map(PAGE.carte).join('') + '</div>';
  });

  /* ── Boutons de la note ───────────────────────────────────────────────── */

  function rendreOutils() {
    var el = document.getElementById('nt-outils');
    var n = note();
    if (!el || !n) return;
    var fav = estFavori(n.id);
    var ouverts = C.liste.filter(function (c) { return !c.parent_id && !c.resolu; }).length;
    el.innerHTML =
      '<button type="button" class="btn btn-petit nt-icone' + (fav ? ' actif' : '') + '" data-act="favori" title="' + (fav ? 'Retirer des favoris' : 'Ajouter aux favoris') + '" aria-label="Favori">' + (fav ? I.etoilePleine : I.etoile) + '</button>' +
      '<button type="button" class="btn btn-petit nt-icone" data-act="chercher" title="Rechercher dans la note (Cmd/Ctrl + F)" aria-label="Rechercher">' + I.loupe + '</button>' +
      '<button type="button" class="btn btn-petit nt-icone" data-act="historique" title="Historique des versions" aria-label="Historique">' + I.horloge + '</button>' +
      '<button type="button" class="btn btn-petit nt-icone' + (ouverts ? ' actif' : '') + '" data-act="commentaires" title="Commentaires" aria-label="Commentaires">' + I.bulle +
      (ouverts ? '<span class="nt-icone-nb">' + ouverts + '</span>' : '') + '</button>' +
      '<button type="button" class="btn btn-petit nt-icone" data-act="exporter" title="Exporter ou imprimer" aria-label="Exporter">' + I.export + '</button>';
  }

  PAGE.actions.favori = function () {
    var n = note();
    if (!n) return;
    var veut = !estFavori(n.id);
    api('/api/postits/' + n.id + '/favori', { method: 'PUT', body: { favori: veut } }).then(function () {
      toast(veut ? 'Ajoutée aux favoris.' : 'Retirée des favoris.');
      return chargerRaccourcis();
    }).catch(function (e) { toast(e.message, 'danger'); });
  };
  PAGE.actions.commentaires = function () { PAGE.ouvrirOngletPanneau('commentaires'); PAGE.ecrireAdresse(); };

  var _derniere = null;
  PAGE.sur('note', function (n) {
    rendreOutils();
    rendreRaccourcis();
    if (_derniere === n.id) { marquer(); return; }   /* simple redessin de la même note */
    _derniere = n.id;
    C.liste = [];
    C.brouillon = null;
    C.personnes = null;
    api('/api/postits/' + n.id + '/consultee', { method: 'POST' }).then(chargerRaccourcis).catch(function () {});
    chargerCommentaires();
    proposerModeles(n);
  });
  PAGE.sur('fermeture', function () { fermerExport(); _derniere = null; if (H.ed) { H.ed.detruire(); H.ed = null; } });

  /* ── Export et impression ─────────────────────────────────────────────── */

  function fermerExport() {
    var m = document.getElementById('nt-export');
    if (m) m.remove();
  }

  PAGE.actions.exporter = function (bouton) {
    var n = note();
    if (!n) return;
    if (document.getElementById('nt-export')) return fermerExport();
    var m = document.createElement('div');
    m.id = 'nt-export';
    m.className = 'nt-menu';
    m.setAttribute('role', 'menu');
    m.innerHTML =
      '<a role="menuitem" href="/api/postits/' + n.id + '/export.pdf"><b>PDF</b><small>Télécharger la note</small></a>' +
      '<a role="menuitem" href="/api/postits/' + n.id + '/export.docx"><b>Word</b><small>Fichier .docx modifiable</small></a>' +
      '<button type="button" role="menuitem" data-ex="imprimer"><b>Imprimer…</b><small>Toute imprimante de ce poste</small></button>' +
      '<button type="button" role="menuitem" data-ex="reseau"><b>Imprimante MySifa…</b><small>Imprimantes de l\'atelier et des bureaux</small></button>' +
      '<button type="button" role="menuitem" data-ex="modele"><b>Enregistrer comme modèle</b><small>Réutiliser cette trame</small></button>';
    document.body.appendChild(m);
    var r = bouton.getBoundingClientRect();
    m.style.top = (r.bottom + 6) + 'px';
    m.style.left = Math.max(12, Math.min(window.innerWidth - 260, r.right - 240)) + 'px';
    m.addEventListener('click', function (e) {
      var b = e.target.closest('[data-ex], a');
      if (!b) return;
      fermerExport();
      if (b.tagName === 'A') { toast('Export en cours…', 'info'); return; }
      if (b.dataset.ex === 'imprimer') window.open('/note/' + n.id + '/imprimer', '_blank', 'noopener');
      if (b.dataset.ex === 'reseau') imprimerReseau(n);
      if (b.dataset.ex === 'modele') enregistrerModele(n);
    });
  };

  document.addEventListener('mousedown', function (e) {
    var m = document.getElementById('nt-export');
    if (m && !m.contains(e.target) && !e.target.closest('[data-act="exporter"]')) fermerExport();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fermerExport(); });

  var _impression = null;
  function chargerImpression() {
    if (window.openPrintModal) return Promise.resolve();
    if (_impression) return _impression;
    _impression = new Promise(function (ok, ko) {
      var l = document.createElement('link');
      l.rel = 'stylesheet';
      l.href = '/static/mysifa_print_modal.css?v=notes1';
      document.head.appendChild(l);
      var sc = document.createElement('script');
      sc.src = '/static/mysifa_print_modal.js?v=notes1';
      sc.onload = function () { ok(); };
      sc.onerror = function () { _impression = null; ko(new Error('Impression indisponible.')); };
      document.head.appendChild(sc);
    });
    return _impression;
  }

  function imprimerReseau(n) {
    chargerImpression().then(function () {
      window.openPrintModal({ entityType: 'note', entityId: n.id, usageKey: 'note_document',
        title: 'Imprimer la note', subtitle: n.title || 'Sans titre' });
    }).catch(function (e) { toast(e.message, 'danger'); });
  }

  /* ── Modèles ──────────────────────────────────────────────────────────── */

  var _modeles = null;
  function chargerModeles() {
    return api('/api/postits/modeles').then(function (l) { _modeles = l || []; return _modeles; });
  }

  /* {date} dans un modèle : remplacé par la date du jour. */
  function preparer(blocs) {
    var d = aujourdhui();
    return (blocs || []).map(function (b) {
      var x = JSON.parse(JSON.stringify(b));
      if (x.texte) x.texte = x.texte.split('{date}').join(d);
      if (x.html) x.html = x.html.split('{date}').join(esc(d));
      if (x.lignes) x.lignes = x.lignes.map(function (l) { return l.map(function (c) { return String(c || '').split('{date}').join(esc(d)); }); });
      return x;
    });
  }

  function choisirModele() {
    return new Promise(function (resoudre) {
      chargerModeles().then(function (liste) {
        var root = document.getElementById('mroot');
        root.innerHTML =
          '<div class="nt-modal-fond" id="nt-mod-fond"><div class="nt-modal nt-modal-modeles" role="dialog" aria-modal="true" aria-label="Modèles">' +
          '<div class="nt-modal-tete"><h3>Insérer un modèle</h3><button type="button" class="nt-fermer" data-m="fermer" aria-label="Fermer">×</button></div>' +
          (liste.length ? '<div class="nt-modeles">' + liste.map(function (m, k) {
            return '<div class="nt-modele"><button type="button" class="nt-modele-choix" data-k="' + k + '"><b>' + esc(m.nom) + '</b><small>' +
              esc(m.description || (m.commun ? 'Modèle commun' : 'Mon modèle')) + '</small></button>' +
              (m.commun ? '' : '<button type="button" class="nt-fermer" data-suppr="' + m.id + '" title="Supprimer ce modèle" aria-label="Supprimer">×</button>') + '</div>';
          }).join('') + '</div>' : '<p class="nt-modal-aide">Aucun modèle.</p>') +
          '<p class="nt-modal-aide">Une note peut devenir un modèle : Exporter › Enregistrer comme modèle.</p></div></div>';
        var fond = document.getElementById('nt-mod-fond');
        function fin(v) { fermerMroot(); document.removeEventListener('keydown', clavier, true); resoudre(v); }
        function clavier(e) { if (e.key === 'Escape') { e.preventDefault(); fin(null); } }
        document.addEventListener('keydown', clavier, true);
        fond.addEventListener('click', function (e) {
          if (e.target === fond || e.target.closest('[data-m="fermer"]')) return fin(null);
          var s = e.target.closest('[data-suppr]');
          if (s) {
            api('/api/postits/modeles/' + s.dataset.suppr, { method: 'DELETE' }).then(function () {
              toast('Modèle supprimé.');
              fin(null);
            }).catch(function (er) { toast(er.message, 'danger'); });
            return;
          }
          var c = e.target.closest('[data-k]');
          if (c) fin(preparer(liste[Number(c.dataset.k)].blocs));
        });
      }).catch(function (e) { toast(e.message, 'danger'); resoudre(null); });
    });
  }

  function enregistrerModele(n) {
    var root = document.getElementById('mroot');
    root.innerHTML =
      '<div class="nt-modal-fond" id="nt-mod-fond"><div class="nt-modal" role="dialog" aria-modal="true" aria-label="Enregistrer comme modèle">' +
      '<h3>Enregistrer comme modèle</h3><p class="nt-modal-aide">Le contenu actuel de la note devient une trame réutilisable, pour vous seul. ' +
      'Écrivez {date} là où la date du jour doit apparaître.</p>' +
      '<input type="text" class="nt-champ" id="nt-mod-nom" maxlength="200" placeholder="Nom du modèle" value="' + esc(n.title === 'Sans titre' ? '' : n.title) + '">' +
      '<div class="nt-modal-actions" style="margin-top:14px"><button type="button" class="btn" data-m="0">Annuler</button>' +
      '<button type="button" class="btn btn-accent" data-m="1">Enregistrer</button></div></div></div>';
    var inp = document.getElementById('nt-mod-nom');
    function valider() {
      var nom = inp.value.trim();
      if (!nom) { inp.focus(); return; }
      if (S.ed) S.ed.vider();
      api('/api/postits/modeles', { method: 'POST', body: { note_id: n.id, nom: nom } })
        .then(function () { fermerMroot(); toast('Modèle enregistré.'); _modeles = null; })
        .catch(function (e) { toast(e.message, 'danger'); });
    }
    document.getElementById('nt-mod-fond').addEventListener('click', function (e) {
      var b = e.target.closest('[data-m]');
      if (e.target.id === 'nt-mod-fond' || (b && b.dataset.m === '0')) return fermerMroot();
      if (b) valider();
    });
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') valider();
      if (e.key === 'Escape') fermerMroot();
    });
    requestAnimationFrame(function () { inp.focus(); inp.select(); });
  }

  /* Note vide : on propose de partir d'un modèle, comme une page neuve de Notion. */
  function proposerModeles(n) {
    if (PAGE.droit() === 'lire') return;
    var vide = !(n.blocs || []).some(function (b) { return (b.texte || '').trim() || b.type !== 'p'; });
    if (!vide) return;
    (_modeles ? Promise.resolve(_modeles) : chargerModeles()).then(function (liste) {
      var corps = document.getElementById('nt-corps');
      if (!corps || !liste.length || note() !== n || document.querySelector('.nt-modeles-bande')) return;
      var bande = document.createElement('div');
      bande.className = 'nt-modeles-bande';
      bande.innerHTML = '<span>Commencer avec :</span>' + liste.slice(0, 6).map(function (m, k) {
        return '<button type="button" data-k="' + k + '">' + esc(m.nom) + '</button>';
      }).join('');
      corps.parentNode.insertBefore(bande, corps.nextSibling);
      bande.addEventListener('mousedown', function (e) { if (e.target.closest('[data-k]')) e.preventDefault(); });
      bande.addEventListener('click', function (e) {
        var b = e.target.closest('[data-k]');
        if (!b || !S.ed) return;
        S.ed.insererBlocs(preparer(liste[Number(b.dataset.k)].blocs), 0);
        bande.remove();
      });
      corps.addEventListener('input', function cacher() {
        if ((corps.textContent || '').trim()) { bande.remove(); corps.removeEventListener('input', cacher); }
      });
    }).catch(function () {});
  }

  /* ── Historique des versions ──────────────────────────────────────────── */

  function quandLong(s) {
    if (!s) return '';
    var d = String(s).slice(0, 10).split('-');
    return d[2] + '/' + d[1] + '/' + d[0] + ' à ' + String(s).slice(11, 16);
  }

  PAGE.actions.historique = function () { ouvrirHistorique(null); };

  function ouvrirHistorique(vid) {
    var n = note();
    if (!n) return;
    if (S.ed) S.ed.vider();
    H.ouvert = true;
    PAGE.adresse.historique = 1;
    PAGE.adresse.version = vid || null;
    PAGE.ecrireAdresse();
    var root = document.getElementById('mroot');
    root.innerHTML =
      '<div class="nt-modal-fond" id="nt-hist-fond"><div class="nt-modal nt-modal-hist" role="dialog" aria-modal="true" aria-label="Historique">' +
      '<div class="nt-modal-tete"><h3>Historique de « ' + esc(n.title || 'Sans titre') + ' »</h3>' +
      '<button type="button" class="nt-fermer" data-h="fermer" aria-label="Fermer">×</button></div>' +
      '<div class="nt-hist"><div class="nt-hist-liste" id="nt-hist-liste"><div class="nt-arbre-vide">Chargement…</div></div>' +
      '<div class="nt-hist-apercu"><div class="nt-hist-barre" id="nt-hist-barre"></div><div class="nt-hist-corps" id="nt-hist-corps">' +
      '<p class="nt-modal-aide">Choisissez une version à gauche pour la relire.</p></div></div></div></div></div>';
    var fond = document.getElementById('nt-hist-fond');
    fond.addEventListener('click', function (e) {
      if (e.target === fond || e.target.closest('[data-h="fermer"]')) return fermerHistorique();
      var v = e.target.closest('[data-version]');
      if (v) return voirVersion(Number(v.dataset.version));
      if (e.target.closest('[data-h="restaurer"]')) restaurer();
    });
    document.addEventListener('keydown', echapHist, true);
    api('/api/postits/' + n.id + '/versions').then(function (d) {
      H.versions = d.versions || [];
      rendreListeVersions();
      if (vid) voirVersion(vid);
      else if (H.versions.length) voirVersion(H.versions[0].id);
    }).catch(function (e) { toast(e.message, 'danger'); });
  }

  function echapHist(e) { if (e.key === 'Escape' && H.ouvert) { e.preventDefault(); fermerHistorique(); } }

  function fermerHistorique(sansAdresse) {
    H.ouvert = false;
    document.removeEventListener('keydown', echapHist, true);
    if (H.ed) { H.ed.detruire(); H.ed = null; }
    if (document.getElementById('nt-hist-fond')) fermerMroot();
    PAGE.adresse.historique = null;
    PAGE.adresse.version = null;
    if (!sansAdresse) PAGE.ecrireAdresse();
  }

  function rendreListeVersions() {
    var el = document.getElementById('nt-hist-liste');
    if (!el) return;
    if (!H.versions.length) {
      el.innerHTML = '<div class="nt-arbre-vide">Pas encore de version : elles sont gardées au fil de l\'écriture (une toutes les 10 minutes au plus).</div>';
      return;
    }
    el.innerHTML = H.versions.map(function (v) {
      return '<button type="button" class="nt-hist-item' + (v.id === H.vid ? ' sel' : '') + '" data-version="' + v.id + '">' +
        '<b>' + esc(quandLong(v.cree_le)) + '</b><small>' + esc(v.auteurs.join(', ') || (v.raison === 'avant restauration' ? 'Avant une restauration' : '—')) + '</small>' +
        '<span>' + esc(v.extrait || 'Note vide') + '</span></button>';
    }).join('');
  }

  function voirVersion(vid) {
    var n = note();
    if (!n) return;
    H.vid = vid;
    PAGE.adresse.version = vid;
    PAGE.ecrireAdresse();
    rendreListeVersions();
    api('/api/postits/' + n.id + '/versions/' + vid).then(function (v) {
      var barre = document.getElementById('nt-hist-barre');
      var corps = document.getElementById('nt-hist-corps');
      if (!barre || !corps) return;
      barre.innerHTML = '<span>Version du ' + esc(quandLong(v.cree_le)) + '</span>' +
        (PAGE.droit() !== 'lire' ? '<button type="button" class="btn btn-accent btn-petit" data-h="restaurer">Restaurer cette version</button>' : '');
      corps.innerHTML = '<div class="nt-hist-titre">' + esc(v.titre || 'Sans titre') + '</div><div id="nt-hist-ed"></div>';
      if (H.ed) H.ed.detruire();
      H.ed = window.MySifaNotesEditeur.monter(document.getElementById('nt-hist-ed'), { blocs: v.blocs }, { lectureSeule: true });
    }).catch(function (e) { toast(e.message, 'danger'); });
  }

  function restaurer() {
    var n = note();
    var v = H.versions.filter(function (x) { return x.id === H.vid; })[0];
    if (!n || !v) return;
    PAGE.confirmer('Restaurer cette version ?',
      'La note reprend son contenu du ' + quandLong(v.cree_le) + '. L\'état actuel est gardé dans l\'historique.', 'Restaurer', false)
      .then(function (ok) {
        if (!ok) return ouvrirHistorique(H.vid);
        return api('/api/postits/' + n.id + '/versions/' + v.id + '/restaurer', { method: 'POST' }).then(function () {
          fermerHistorique(true);
          toast('Version restaurée.');
          return PAGE.chargerArbre().then(function () { return PAGE.ouvrir(n.id); });
        });
      })
      .catch(function (e) { toast(e.message, 'danger'); });
  }

  PAGE.sur('adresse', function (u) {
    var veut = u.get('historique', null) === '1';
    var vid = u.get('version', null);
    if (veut && !H.ouvert) ouvrirHistorique(vid && /^\d+$/.test(vid) ? Number(vid) : null);
    else if (veut && vid && /^\d+$/.test(vid) && Number(vid) !== H.vid) voirVersion(Number(vid));
    else if (!veut && H.ouvert) fermerHistorique(true);
  });

  /* ── Commentaires ─────────────────────────────────────────────────────── */

  function chargerCommentaires() {
    var n = note();
    if (!n) return Promise.resolve();
    var id = n.id;
    return api('/api/postits/' + id + '/commentaires').then(function (d) {
      if (!note() || note().id !== id) return;
      C.liste = d.commentaires || [];
      marquer();
      rendreOutils();
      var zone = document.getElementById('nt-coms');
      if (zone) rendreCommentaires(zone);
      R.mentions = R.mentions.filter(function (m) { return m.note_id !== id; });
      rendreRaccourcis();
    }).catch(function () {});
  }

  function marquer() {
    if (!S.ed) return;
    var parUid = {};
    C.liste.forEach(function (c) {
      if (!c.parent_id && !c.resolu && c.bloc_uid) parUid[c.bloc_uid] = (parUid[c.bloc_uid] || 0) + 1;
    });
    S.ed.marquerCommentaires(parUid);
    var nb = document.getElementById('nt-pa-nb-com');
    var ouverts = C.liste.filter(function (c) { return !c.parent_id && !c.resolu; }).length;
    if (nb) nb.textContent = ouverts ? String(ouverts) : '';
  }

  var _recharge = null;
  PAGE.sur('com-distant', function () {
    clearTimeout(_recharge);
    _recharge = setTimeout(chargerCommentaires, 250);
  });

  PAGE.optionsEditeur = function () {
    return {
      surCommenter: function (info) {
        C.brouillon = { bloc_uid: info.bloc_uid, citation: (info.citation || '').trim().slice(0, 300) };
        PAGE.ouvrirOngletPanneau('commentaires');
        PAGE.ecrireAdresse();
        var zone = document.getElementById('nt-coms');
        if (zone) rendreCommentaires(zone);
        requestAnimationFrame(function () { var t = document.getElementById('nt-com-texte'); if (t) t.focus(); });
      },
      ouvrirCommentaires: function (uid) {
        PAGE.ouvrirOngletPanneau('commentaires');
        PAGE.ecrireAdresse();
        requestAnimationFrame(function () {
          var fil = document.querySelector('.nt-fil-com[data-bloc="' + String(uid).replace(/[^A-Za-z0-9_-]/g, '') + '"]');
          if (fil) { fil.scrollIntoView({ block: 'center' }); fil.classList.add('flash'); setTimeout(function () { fil.classList.remove('flash'); }, 1200); }
        });
      },
      choisirModele: choisirModele,
    };
  };

  PAGE.sur('commentaires', function (zone) { rendreCommentaires(zone); });

  function texteAvecMentions(t) {
    var h = esc(t);
    (C.personnes || []).forEach(function (p) {
      var m = '@' + esc(p.nom);
      if (h.indexOf(m) >= 0) h = h.split(m).join('<span class="nt-mention">' + m + '</span>');
    });
    return h.replace(/\n/g, '<br>');
  }

  function rendreCommentaires(zone) {
    if (!zone) return;
    var n = note();
    if (!n) return;
    if (!C.personnes) {
      C.personnes = [];
      api('/api/postits/' + n.id + '/personnes').then(function (l) { C.personnes = l || []; var z = document.getElementById('nt-coms'); if (z) rendreCommentaires(z); }).catch(function () {});
    }
    var racines = C.liste.filter(function (c) { return !c.parent_id; });
    var visibles = racines.filter(function (c) { return C.resolus || !c.resolu; });
    var nbResolus = racines.filter(function (c) { return c.resolu; }).length;
    var html = '<div class="nt-com-form">' +
      (C.brouillon && C.brouillon.citation ? '<div class="nt-com-citation">« ' + esc(C.brouillon.citation) + ' »<button type="button" class="nt-fermer" data-c="sans-citation" aria-label="Retirer la citation">×</button></div>' : '') +
      '<textarea id="nt-com-texte" class="nt-champ" rows="2" placeholder="' + (C.brouillon && C.brouillon.citation ? 'Commenter ce passage' : 'Commenter la note') + ' — @ pour mentionner"></textarea>' +
      '<div class="nt-com-actions"><button type="button" class="btn btn-accent btn-petit" data-c="envoyer">Commenter</button></div></div>';
    if (!visibles.length) {
      html += '<div class="nt-arbre-vide">' + (racines.length ? 'Tous les commentaires sont résolus.' : 'Aucun commentaire. Sélectionnez un passage de la note puis « Commenter ».') + '</div>';
    }
    html += visibles.map(function (c) {
      var reponses = C.liste.filter(function (x) { return x.parent_id === c.id; });
      return '<div class="nt-fil-com' + (c.resolu ? ' resolu' : '') + '" data-id="' + c.id + '" data-bloc="' + esc(c.bloc_uid || '') + '">' +
        (c.citation ? '<button type="button" class="nt-com-citation lien" data-c="aller" title="Voir le passage dans la note">« ' + esc(c.citation) + ' »</button>' : '') +
        [c].concat(reponses).map(function (x) {
          return '<div class="nt-com" data-cid="' + x.id + '"><div class="nt-com-tete"><b>' + esc(x.nom) + '</b><span>' + esc(PAGE.quand(x.cree_le)) +
            (x.modifie_le ? ' · modifié' : '') + '</span>' +
            (x.peut_modifier ? '<button type="button" class="nt-com-lien" data-c="modifier">Modifier</button>' : '') +
            (x.peut_supprimer ? '<button type="button" class="nt-com-lien" data-c="supprimer">Supprimer</button>' : '') + '</div>' +
            '<div class="nt-com-texte">' + texteAvecMentions(x.texte) + '</div></div>';
        }).join('') +
        '<div class="nt-com-pied">' +
        (c.resolu ? '<span class="nt-com-resolu">Résolu par ' + esc(c.resolu_par || '—') + '</span><button type="button" class="nt-com-lien" data-c="rouvrir">Rouvrir</button>'
          : '<button type="button" class="nt-com-lien" data-c="repondre">Répondre</button><button type="button" class="nt-com-lien" data-c="resoudre">Résoudre</button>') +
        '</div></div>';
    }).join('');
    if (nbResolus) html += '<button type="button" class="nt-com-lien nt-com-voir" data-c="resolus">' + (C.resolus ? 'Masquer' : 'Afficher') + ' les résolus (' + nbResolus + ')</button>';
    zone.innerHTML = html;
    brancherSaisie(document.getElementById('nt-com-texte'), function () { envoyer(null); });
    if (!zone._branche) {
      zone._branche = true;
      zone.addEventListener('click', surClicCommentaires);
    }
  }

  function surClicCommentaires(e) {
    var b = e.target.closest('[data-c]');
    if (!b) return;
    var n = note();
    var fil = b.closest('.nt-fil-com');
    var com = b.closest('.nt-com');
    var cid = com ? Number(com.dataset.cid) : fil ? Number(fil.dataset.id) : null;
    var a = b.dataset.c;
    if (a === 'envoyer') return envoyer(null);
    if (a === 'sans-citation') { C.brouillon = null; return rendreCommentaires(document.getElementById('nt-coms')); }
    if (a === 'resolus') { C.resolus = !C.resolus; return rendreCommentaires(document.getElementById('nt-coms')); }
    if (a === 'aller') {
      var row = document.querySelector('#nt-corps .pb[data-uid="' + String(fil.dataset.bloc).replace(/[^A-Za-z0-9_-]/g, '') + '"]');
      if (row) { row.scrollIntoView({ block: 'center', behavior: 'smooth' }); row.classList.add('pb-flash'); setTimeout(function () { row.classList.remove('pb-flash'); }, 1400); }
      else toast('Le passage commenté n\'existe plus dans la note.', 'info');
      return;
    }
    if (a === 'repondre') {
      if (fil.querySelector('.nt-com-reponse')) return;
      var f = document.createElement('div');
      f.className = 'nt-com-reponse';
      f.innerHTML = '<textarea class="nt-champ" rows="2" placeholder="Répondre — @ pour mentionner"></textarea><div class="nt-com-actions">' +
        '<button type="button" class="btn btn-petit" data-c="annuler-reponse">Annuler</button><button type="button" class="btn btn-accent btn-petit" data-c="envoyer-reponse">Répondre</button></div>';
      fil.appendChild(f);
      var ta = f.querySelector('textarea');
      brancherSaisie(ta, function () { envoyer(Number(fil.dataset.id), ta); });
      ta.focus();
      return;
    }
    if (a === 'annuler-reponse') { b.closest('.nt-com-reponse').remove(); return; }
    if (a === 'envoyer-reponse') return envoyer(Number(fil.dataset.id), fil.querySelector('.nt-com-reponse textarea'));
    if (a === 'resoudre' || a === 'rouvrir') {
      return api('/api/postits/' + n.id + '/commentaires/' + fil.dataset.id, { method: 'PATCH', body: { resolu: a === 'resoudre' } })
        .then(chargerCommentaires).catch(function (er) { toast(er.message, 'danger'); });
    }
    if (a === 'supprimer') {
      return PAGE.confirmer('Supprimer ce commentaire ?', 'Les réponses éventuelles disparaissent avec lui.', 'Supprimer', true).then(function (ok) {
        if (!ok) return;
        return api('/api/postits/' + n.id + '/commentaires/' + cid, { method: 'DELETE' }).then(chargerCommentaires);
      }).catch(function (er) { toast(er.message, 'danger'); });
    }
    if (a === 'modifier') {
      var x = C.liste.filter(function (y) { return y.id === cid; })[0];
      var zoneT = com.querySelector('.nt-com-texte');
      zoneT.innerHTML = '<textarea class="nt-champ" rows="3"></textarea><div class="nt-com-actions"><button type="button" class="btn btn-petit" data-c="annuler-modif">Annuler</button>' +
        '<button type="button" class="btn btn-accent btn-petit" data-c="valider-modif">Enregistrer</button></div>';
      var t2 = zoneT.querySelector('textarea');
      t2.value = x ? x.texte : '';
      t2.focus();
      return;
    }
    if (a === 'annuler-modif') return rendreCommentaires(document.getElementById('nt-coms'));
    if (a === 'valider-modif') {
      var t3 = com.querySelector('textarea');
      return api('/api/postits/' + n.id + '/commentaires/' + cid, { method: 'PATCH', body: { texte: t3.value } })
        .then(chargerCommentaires).catch(function (er) { toast(er.message, 'danger'); });
    }
  }

  function envoyer(parentId, ta) {
    var n = note();
    ta = ta || document.getElementById('nt-com-texte');
    if (!n || !ta) return;
    var texte = ta.value.trim();
    if (!texte) { ta.focus(); return; }
    var mentions = (C.personnes || []).filter(function (p) { return texte.indexOf('@' + p.nom) >= 0; }).map(function (p) { return p.id; });
    var corps = { texte: texte, mentions: mentions, parent_id: parentId };
    if (!parentId && C.brouillon) { corps.bloc_uid = C.brouillon.bloc_uid; corps.citation = C.brouillon.citation; }
    api('/api/postits/' + n.id + '/commentaires', { method: 'POST', body: corps }).then(function (r) {
      C.brouillon = null;
      if (r.sans_acces && r.sans_acces.length) {
        toast(r.sans_acces.join(', ') + ' n\'' + (r.sans_acces.length > 1 ? 'ont' : 'a') + ' pas accès à la note : pas de notification. Partagez-la d\'abord.', 'danger');
      } else if (mentions.length) {
        toast('Commentaire publié, ' + mentions.length + ' personne' + (mentions.length > 1 ? 's' : '') + ' notifiée' + (mentions.length > 1 ? 's' : '') + '.');
      }
      return chargerCommentaires();
    }).catch(function (e) { toast(e.message, 'danger'); });
  }

  /* Saisie d'un commentaire : Cmd/Ctrl + Entrée envoie, « @ » propose les collègues. */
  function brancherSaisie(ta, envoi) {
    if (!ta) return;
    var menu = null;
    var sel = 0;
    var choix = [];
    function fermer() { if (menu) { menu.remove(); menu = null; } }
    function maj() {
      var avant = ta.value.slice(0, ta.selectionStart);
      var m = /(^|\s)@([^\s@]{0,30})$/.exec(avant);
      if (!m) return fermer();
      var q = m[2].toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      choix = (C.personnes || []).filter(function (p) {
        return p.nom.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').indexOf(q) >= 0;
      }).slice(0, 6);
      if (!choix.length) return fermer();
      if (!menu) {
        menu = document.createElement('div');
        menu.className = 'nt-menu nt-menu-personnes';
        document.body.appendChild(menu);
        menu.addEventListener('mousedown', function (e) {
          e.preventDefault();
          var it = e.target.closest('[data-k]');
          if (it) inserer(choix[Number(it.dataset.k)]);
        });
      }
      sel = Math.min(sel, choix.length - 1);
      menu.innerHTML = choix.map(function (p, k) {
        return '<button type="button" data-k="' + k + '" class="' + (k === sel ? 'sel' : '') + '"><b>' + esc(p.nom) + '</b>' +
          (p.acces ? '' : '<small>Pas d\'accès à la note</small>') + '</button>';
      }).join('');
      var r = ta.getBoundingClientRect();
      menu.style.left = Math.max(12, Math.min(window.innerWidth - 252, r.left)) + 'px';
      menu.style.top = (r.bottom + 4) + 'px';
    }
    function inserer(p) {
      if (!p) return;
      var avant = ta.value.slice(0, ta.selectionStart).replace(/@([^\s@]{0,30})$/, '@' + p.nom + ' ');
      ta.value = avant + ta.value.slice(ta.selectionStart);
      ta.setSelectionRange(avant.length, avant.length);
      fermer();
      ta.focus();
    }
    ta.addEventListener('input', maj);
    ta.addEventListener('blur', function () { setTimeout(fermer, 150); });
    ta.addEventListener('keydown', function (e) {
      if (menu && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
        e.preventDefault();
        sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + choix.length) % choix.length;
        maj();
        return;
      }
      if (menu && (e.key === 'Enter' || e.key === 'Tab')) { e.preventDefault(); inserer(choix[sel]); return; }
      if (menu && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); fermer(); return; }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); envoi(); }
    });
  }

  /* Le titre change : favoris et récentes suivent sans attendre. */
  document.addEventListener('input', function (e) {
    if (e.target.id !== 'nt-titre' || !note()) return;
    var t = e.target.value.trim() || 'Sans titre';
    R.favoris.concat(R.recentes).forEach(function (x) { if (x.id === note().id) x.title = t; });
    rendreRaccourcis();
  });

  chargerRaccourcis();
})();
