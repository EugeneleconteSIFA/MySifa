/**
 * MySifa — Mes notes (/note) : arborescence, recherche, note ouverte, corbeille.
 *
 * Données : app/routers/postit.py (une note = une ligne de `postits`).
 * Éditeur : static/mysifa_notes_editeur.js (commun avec les post-its).
 * Adresse : `note=<id>` (+ `partage=1`), `vue=corbeille`, `nouvelle=1` (lu puis remplacé).
 * Partage et rédaction à plusieurs : l'éditeur suit le flux de la note
 * ouverte (opérations des autres, présence) ; la page affiche qui est là.
 * Hors adresse : la recherche (saisie en cours), les branches dépliées de
 * l'arbre et le panneau d'actions rapides (préférences d'affichage,
 * localStorage `mysifa_notes_ouvertes` et `mysifa_notes_panneau`).
 */
(function () {
  'use strict';

  var S = {
    notes: [],          // arbre : notes vivantes sans contenu
    partagees: [],      // notes partagées avec moi (racines et sous-pages)
    corbeille: [],
    partage: false,     // fenêtre de partage ouverte
    presences: [],
    vue: 'accueil',     // accueil | note | corbeille
    courante: null,     // note ouverte, contenu compris
    ed: null,           // éditeur monté sur la note ouverte
    q: '',
    ouvertes: {},
    pret: false,
  };
  var _titreTimer = null;
  var _dragNote = null;

  /* ── Outils ─────────────────────────────────────────────────────────── */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function sansAccent(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function toast(msg, type) {
    var w = document.getElementById('toast-wrap');
    if (!w) return;
    var t = document.createElement('div');
    t.className = 'toast ' + (type || 'success');
    t.textContent = msg;
    w.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }
  async function api(chemin, init) {
    var opts = Object.assign({ credentials: 'include', headers: {} }, init || {});
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
      opts.headers['Content-Type'] = 'application/json';
    }
    var r = await fetch(chemin, opts);
    if (r.status === 401) {
      location.href = '/?next=' + encodeURIComponent(location.pathname + location.search);
      throw new Error('Session expirée.');
    }
    var d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) throw new Error((d && d.detail) || ('Erreur ' + r.status));
    return d;
  }
  function quand(s) {
    if (!s) return '';
    var j = String(s).slice(0, 10).split('-');
    var auj = new Date();
    var cle = auj.getFullYear() + '-' + String(auj.getMonth() + 1).padStart(2, '0') + '-' + String(auj.getDate()).padStart(2, '0');
    var heure = String(s).length >= 16 ? String(s).slice(11, 16) : '';
    if (String(s).slice(0, 10) === cle) return 'aujourd\'hui' + (heure ? ' à ' + heure : '');
    return j.length === 3 ? j[2] + '/' + j[1] + '/' + j[0] : String(s);
  }
  function parId(id) {
    id = Number(id);
    for (var i = 0; i < S.notes.length; i++) if (Number(S.notes[i].id) === id) return S.notes[i];
    for (var j = 0; j < S.partagees.length; j++) if (Number(S.partagees[j].id) === id) return S.partagees[j];
    return null;
  }
  function enfants(pid, liste) {
    return (liste || (pid && !S.notes.some(function (n) { return n.id === pid; }) ? S.partagees : S.notes))
      .filter(function (n) { return (n.parent_id || null) === (pid || null); })
      .sort(function (a, b) { return (a.ordre - b.ordre) || (a.id - b.id); });
  }
  function ancetres(note) {
    var out = [];
    var p = note && note.parent_id ? parId(note.parent_id) : null;
    var garde = 0;
    while (p && garde++ < 50) {
      out.unshift(p);
      p = p.parent_id ? parId(p.parent_id) : null;
    }
    return out;
  }
  function titre(n) { return (n && n.title) || 'Sans titre'; }

  function lireOuvertes() {
    try { S.ouvertes = JSON.parse(localStorage.getItem('mysifa_notes_ouvertes') || '{}') || {}; }
    catch (e) { S.ouvertes = {}; }
  }
  function ecrireOuvertes() {
    try { localStorage.setItem('mysifa_notes_ouvertes', JSON.stringify(S.ouvertes)); } catch (e) {}
  }

  /* Confirmation dans #mroot (jamais de confirm() natif). */
  function confirmer(titreMsg, texte, libelle, danger) {
    return new Promise(function (ok) {
      var root = document.getElementById('mroot');
      root.innerHTML =
        '<div class="nt-modal-fond"><div class="nt-modal" role="dialog" aria-modal="true">' +
        '<h3>' + esc(titreMsg) + '</h3><p>' + esc(texte) + '</p>' +
        '<div class="nt-modal-actions"><button type="button" class="btn" data-r="0">Annuler</button>' +
        '<button type="button" class="btn ' + (danger ? 'btn-danger' : 'btn-accent') + '" data-r="1">' + esc(libelle) + '</button></div>' +
        '</div></div>';
      function fin(v) {
        root.innerHTML = '';
        document.removeEventListener('keydown', clavier, true);
        ok(v);
      }
      function clavier(e) {
        if (e.key === 'Escape') { e.preventDefault(); fin(false); }
        if (e.key === 'Enter') { e.preventDefault(); fin(true); }
      }
      document.addEventListener('keydown', clavier, true);
      root.querySelector('.nt-modal-fond').addEventListener('mousedown', function (e) {
        var b = e.target.closest('[data-r]');
        if (b) return fin(b.dataset.r === '1');
        if (e.target.classList.contains('nt-modal-fond')) fin(false);
      });
      requestAnimationFrame(function () {
        var b = root.querySelector('[data-r="1"]');
        if (b) b.focus();
      });
    });
  }

  /* ── Données ────────────────────────────────────────────────────────── */

  async function chargerArbre() {
    var r = await Promise.all([api('/api/postits/notes'), api('/api/postits/notes?corbeille=1')]);
    S.notes = (r[0] && r[0].notes) || [];
    S.partagees = (r[0] && r[0].partagees) || [];
    S.corbeille = (r[1] && r[1].notes) || [];
  }

  async function creerNote(parentId) {
    try {
      var n = await api('/api/postits', {
        method: 'POST',
        body: { type: 'someday', title: 'Sans titre', parent_id: parentId || null, sur_ecran: 0, blocs: [] },
      });
      await chargerArbre();
      if (parentId) { S.ouvertes[parentId] = 1; ecrireOuvertes(); }
      await ouvrir(n.id, { focusTitre: true });
      return n;
    } catch (e) {
      toast(e.message || 'Création impossible.', 'danger');
      return null;
    }
  }

  function majResume(note) {
    var n = parId(note.id);
    if (!n) return;
    n.title = note.title;
    n.modifie_le = note.modifie_le || n.modifie_le;
    if (note.blocs) {
      var txt = window.MySifaNotesEditeur ? window.MySifaNotesEditeur.texte(note.blocs) : '';
      n.texte = txt;
      n.extrait = txt.replace(/\s+/g, ' ').slice(0, 160);
    }
  }

  function moi() { return Number((window.__NOTES__ && window.__NOTES__.user && window.__NOTES__.user.id) || 0); }
  function droit() { return (S.courante && S.courante.droit) || 'proprio'; }

  /* ── Navigation ─────────────────────────────────────────────────────── */

  /* Modules de la page (static/mysifa_notes_*.js) : ils s'abonnent aux rendus,
     ajoutent des actions (data-act) et lisent l'état par window.MySifaNotesPage. */
  var PAGE = { actions: {}, abonnes: {} };
  function crochets(quoi, arg) {
    (PAGE.abonnes[quoi] || []).forEach(function (fn) { try { fn(arg); } catch (e) { console.error(e); } });
  }

  function fermerEditeur() {
    crochets('fermeture');
    if (_titreTimer) { clearTimeout(_titreTimer); _titreTimer = null; enregistrerTitre(); }
    if (S.ed) { S.ed.detruire(); S.ed = null; }
    S.presences = [];
    S.partage = false;
  }

  async function ouvrir(id, opts) {
    opts = opts || {};
    fermerEditeur();
    try {
      S.courante = await api('/api/postits/' + Number(id));
    } catch (e) {
      toast(e.message || 'Note introuvable.', 'danger');
      S.courante = null;
      return allerAccueil();
    }
    if (S.courante.supprime_le) {
      toast('Cette note est dans la corbeille.', 'danger');
      S.courante = null;
      return allerCorbeille();
    }
    S.vue = 'note';
    ancetres(S.courante).forEach(function (a) { S.ouvertes[a.id] = 1; });
    ecrireOuvertes();
    document.body.classList.remove('sb-open');
    rendre();
    if (opts.focusTitre) {
      var t = document.getElementById('nt-titre');
      if (t) { t.focus(); t.select(); }
    }
  }

  function allerAccueil() {
    fermerEditeur();
    S.vue = 'accueil';
    S.courante = null;
    document.body.classList.remove('sb-open');
    rendre();
  }

  function allerCorbeille() {
    fermerEditeur();
    S.vue = 'corbeille';
    S.courante = null;
    document.body.classList.remove('sb-open');
    rendre();
  }

  /* ── Adresse ────────────────────────────────────────────────────────── */

  function ecrireAdresse() {
    if (!window.MySifaUrl) return;
    var p = {};
    var nav = 'accueil';
    if (S.vue === 'note' && S.courante) {
      p.note = S.courante.id;
      nav = 'note';
      if (S.partage) { p.partage = 1; nav = 'note/partage'; }
      Object.keys(PAGE.adresse).forEach(function (k) {
        if (PAGE.adresse[k] != null && PAGE.adresse[k] !== '') { p[k] = PAGE.adresse[k]; nav += '/' + k; }
      });
    }
    else if (S.vue === 'corbeille') { p.vue = 'corbeille'; nav = 'corbeille'; }
    window.MySifaUrl.ecrire(p, { navigation: nav });
  }

  async function lireAdresse(u) {
    if (u.get('vue', null, ['corbeille'])) return allerCorbeille();
    var id = u.get('note', null);
    if (id && /^\d+$/.test(id)) {
      if (!(S.vue === 'note' && S.courante && String(S.courante.id) === id)) await ouvrir(Number(id));
      crochets('adresse', u);
      if (u.get('commentaires', null) === '1' && !(document.body.classList.contains('nt-panneau-ouvert') && ongletPanneau() === 'commentaires')) {
        ouvrirOngletPanneau('commentaires');
      }
      var veut = u.get('partage', null) === '1' && droit() === 'proprio';
      if (veut && !S.partage) ouvrirPartage();
      else if (!veut && S.partage) fermerPartage(true);
      return;
    }
    allerAccueil();
  }

  /* ── Rendu ──────────────────────────────────────────────────────────── */

  function rendre() {
    rendreArbre();
    rendreContenu();
    ecrireAdresse();
    var sub = document.getElementById('mobile-sub');
    if (sub) sub.textContent = S.vue === 'note' && S.courante ? titre(S.courante) : S.vue === 'corbeille' ? 'Corbeille' : 'Toutes les notes';
    document.title = (S.vue === 'note' && S.courante ? titre(S.courante) + ' — ' : '') + 'Mes notes — MySifa';
  }

  function correspond(n, q) {
    return sansAccent(titre(n) + ' ' + (n.texte || '')).indexOf(q) >= 0;
  }

  function rendreArbre() {
    var el = document.getElementById('nt-arbre');
    var elP = document.getElementById('nt-arbre-partage');
    var lbl = document.getElementById('nt-label-partage');
    if (!el) return;
    var acc = document.getElementById('nt-nav-accueil');
    if (acc) acc.classList.toggle('active', S.vue === 'accueil');
    var cb = document.getElementById('nt-nav-corbeille');
    if (cb) cb.classList.toggle('active', S.vue === 'corbeille');
    var nb = document.getElementById('nt-nb-corbeille');
    if (nb) {
      var jetees = {};
      S.corbeille.forEach(function (n) { jetees[n.id] = n; });
      var nbTetes = S.corbeille.filter(function (n) {
        var p = n.parent_id ? jetees[n.parent_id] : null;
        return !(p && p.supprime_le === n.supprime_le);
      }).length;
      nb.textContent = nbTetes ? String(nbTetes) : '';
    }
    var courant = S.vue === 'note' && S.courante ? S.courante.id : null;
    var q = sansAccent(S.q.trim());

    if (q) {
      if (lbl) lbl.hidden = true;
      if (elP) elP.innerHTML = '';
      var trouves = S.notes.concat(S.partagees).filter(function (n) { return correspond(n, q); });
      if (!trouves.length) {
        el.innerHTML = '<div class="nt-arbre-vide">Aucun résultat pour « ' + esc(S.q.trim()) + ' »</div>';
        return;
      }
      el.innerHTML = trouves.map(function (n) {
        var chemin = ancetres(n).map(titre).join(' / ');
        if (n.partagee && !chemin) chemin = 'Partagée par ' + (n.proprietaire || 'un collègue');
        return '<div class="nt-item' + (n.id === courant ? ' active' : '') + '" data-id="' + n.id + '" style="--nt-p:0">' +
          '<span class="nt-item-ico">' + ICONE_NOTE + '</span>' +
          '<span class="nt-item-txt"><span class="nt-item-nom">' + esc(titre(n)) + '</span>' +
          (chemin ? '<span class="nt-item-chemin">' + esc(chemin) + '</span>' : '') + '</span></div>';
      }).join('');
      return;
    }

    function arbre(liste, glisser) {
      var html = '';
      (function branche(pid, prof) {
        enfants(pid, liste).forEach(function (n) {
          var fils = enfants(n.id, liste);
          var ouvert = !!S.ouvertes[n.id];
          var peutAjouter = !n.partagee || n.droit === 'ecrire';
          html +=
            '<div class="nt-item' + (n.id === courant ? ' active' : '') + '" data-id="' + n.id + '"' + (glisser ? ' draggable="true"' : '') + ' style="--nt-p:' + prof + '">' +
            '<button type="button" class="nt-chev' + (fils.length ? '' : ' vide') + (ouvert ? ' ouvert' : '') + '" data-act="plier" tabindex="-1" aria-label="' + (ouvert ? 'Replier' : 'Déplier') + '">' + ICONE_CHEV + '</button>' +
            '<span class="nt-item-nom">' + esc(titre(n)) + '</span>' +
            (n.nb_partages ? '<span class="nt-item-postit" title="Partagée avec ' + n.nb_partages + ' collègue' + (n.nb_partages > 1 ? 's' : '') + '">' + ICONE_PARTAGE + '</span>' : '') +
            (n.sur_ecran ? '<span class="nt-item-postit" title="Affichée en post-it">' + ICONE_POSTIT + '</span>' : '') +
            (peutAjouter ? '<button type="button" class="nt-item-plus" data-act="sous" title="Ajouter une sous-page" tabindex="-1">' + ICONE_PLUS + '</button>' : '') +
            '</div>';
          if (fils.length && ouvert) branche(n.id, prof + 1);
        });
      })(null, 0);
      return html;
    }

    el.innerHTML = S.notes.length ? arbre(S.notes, true) : '<div class="nt-arbre-vide">Aucune note pour l\'instant</div>';
    if (elP) elP.innerHTML = S.partagees.length ? arbre(S.partagees, false) : '';
    if (lbl) lbl.hidden = !S.partagees.length;
  }

  function rendreContenu() {
    var c = document.getElementById('content');
    if (!c) return;
    if (S.vue !== 'note') {
      var pa = document.getElementById('nt-panneau');
      if (pa) { pa.hidden = true; pa.dataset.note = ''; }
      document.body.classList.remove('nt-panneau-ouvert');
    }
    if (S.vue === 'note' && S.courante) return rendreNote(c);
    if (S.vue === 'corbeille') return rendreCorbeille(c);
    rendreAccueil(c);
  }

  function carte(n) {
    var chemin = ancetres(n).map(titre).join(' / ');
    if (n.partagee && n.racine_partage) chemin = 'Partagée par ' + (n.proprietaire || 'un collègue');
    return '<button type="button" class="nt-carte" data-id="' + n.id + '">' +
      '<span class="nt-carte-titre">' + esc(titre(n)) + '</span>' +
      (chemin ? '<span class="nt-carte-chemin">' + esc(chemin) + '</span>' : '') +
      '<span class="nt-carte-extrait">' + (n.extrait ? esc(n.extrait) : '<em>Note vide</em>') + '</span>' +
      '<span class="nt-carte-pied">' + esc(quand(n.modifie_le || n.created_at)) +
      (n.sur_ecran ? ' · <span class="nt-pastille">Post-it</span>' : '') +
      (n.nb_partages ? ' · <span class="nt-pastille">Partagée</span>' : '') +
      (n.partagee ? ' · <span class="nt-pastille">' + (n.droit === 'lire' ? 'Lecture' : 'Modification') + '</span>' : '') +
      '</span></button>';
  }

  function rendreAccueil(c) {
    var recentes = S.notes.slice().sort(function (a, b) {
      return String(b.modifie_le || b.created_at || '').localeCompare(String(a.modifie_le || a.created_at || ''));
    });
    var html =
      '<div class="nt-tete"><div><h1>Mes notes</h1>' +
      '<p class="nt-sous">' + (S.notes.length ? S.notes.length + ' note' + (S.notes.length > 1 ? 's' : '') + ' · personnelles, sauf celles que vous partagez' : 'Personnelles, sauf celles que vous partagez') + '</p></div>' +
      '<button type="button" class="btn btn-accent" data-act="nouvelle">' + ICONE_PLUS + 'Nouvelle note</button></div>';
    if (!recentes.length) {
      html +=
        '<div class="nt-vide"><div class="nt-vide-ico">' + ICONE_NOTE + '</div>' +
        '<h2>Aucune note</h2><p>Une note s\'écrit librement : tapez « / » pour insérer un titre, une case à cocher, une liste, une sous-page…</p>' +
        '<button type="button" class="btn btn-accent" data-act="nouvelle">' + ICONE_PLUS + 'Créer une note</button></div>';
    } else {
      html += '<div class="nt-section">Modifiées récemment</div><div class="nt-grille">' +
        recentes.map(carte).join('') + '</div>';
    }
    html += '<div id="nt-accueil-plus"></div>';
    var racinesPartagees = S.partagees.filter(function (n) { return n.racine_partage; });
    if (racinesPartagees.length) {
      html += '<div class="nt-section nt-section-espace">Partagées avec moi</div><div class="nt-grille">' +
        racinesPartagees.map(carte).join('') + '</div>';
    }
    c.innerHTML = html;
    crochets('accueil', document.getElementById('nt-accueil-plus'));
  }

  function rendreCorbeille(c) {
    var html = '<div class="nt-tete"><div><h1>Corbeille</h1><p class="nt-sous">Rien n\'est supprimé automatiquement. Une note restaurée revient avec ses sous-pages.</p></div></div>';
    /* Une sous-page jetée avec son parent ne s'affiche pas à part : elle revient avec lui. */
    var jetees = {};
    S.corbeille.forEach(function (n) { jetees[n.id] = n; });
    var tetes = S.corbeille.filter(function (n) {
      var p = n.parent_id ? jetees[n.parent_id] : null;
      return !(p && p.supprime_le === n.supprime_le);
    });
    if (!tetes.length) {
      html += '<div class="nt-vide"><div class="nt-vide-ico">' + ICONE_CORBEILLE + '</div><h2>Corbeille vide</h2></div>';
    } else {
      html += '<div class="nt-liste">' + tetes.map(function (n) {
        var nbSous = 0;
        (function compter(pid) {
          S.corbeille.forEach(function (x) { if (x.parent_id === pid && x.supprime_le === n.supprime_le) { nbSous++; compter(x.id); } });
        })(n.id);
        return '<div class="nt-ligne" data-id="' + n.id + '">' +
          '<span class="nt-ligne-ico">' + ICONE_NOTE + '</span>' +
          '<span class="nt-ligne-txt"><b>' + esc(titre(n)) + '</b><small>Supprimée ' + esc(quand(n.supprime_le)) +
          (nbSous ? ' · avec ' + nbSous + ' sous-page' + (nbSous > 1 ? 's' : '') : '') + (n.extrait ? ' · ' + esc(n.extrait) : '') + '</small></span>' +
          '<button type="button" class="btn btn-petit" data-act="restaurer">Restaurer</button>' +
          '<button type="button" class="btn btn-petit btn-danger" data-act="purger">Supprimer</button></div>';
      }).join('') + '</div>';
    }
    c.innerHTML = html;
  }

  function rendreNote(c) {
    var n = S.courante;
    var d = droit();
    var racine = d === 'proprio' ? '<a href="/note" class="nt-fil-lien" data-act="accueil">Mes notes</a>'
      : '<span class="nt-fil-lien nt-fil-partage">Partagée par ' + esc(n.proprietaire || 'un collègue') + '</span>';
    var fil = ancetres(n).map(function (a) {
      return '<a href="/note?note=' + a.id + '" data-id="' + a.id + '" class="nt-fil-lien">' + esc(titre(a)) + '</a><span class="nt-fil-sep">/</span>';
    }).join('');
    var actions = '<span class="nt-outils" id="nt-outils"></span>' +
      '<button type="button" class="btn btn-petit nt-btn-panneau" data-act="panneau" aria-label="Panneau : actions et commentaires" hidden>' + ICONE_PANNEAU + '</button>';
    if (d === 'proprio') {
      var nbP = (n.partages || []).length;
      actions +=
        '<button type="button" class="btn btn-petit' + (nbP ? ' actif' : '') + '" data-act="partager" title="Partager avec des collègues">' + ICONE_PARTAGE +
        (nbP ? 'Partagée · ' + nbP : 'Partager') + '</button>' +
        '<button type="button" class="btn btn-petit' + (n.sur_ecran ? ' actif' : '') + '" data-act="ecran" title="' +
        (n.sur_ecran ? 'Retirer le post-it de l\'écran' : 'Afficher cette note en post-it sur toutes vos pages') + '">' + ICONE_POSTIT +
        (n.sur_ecran ? 'Post-it' : 'En post-it') + '</button>';
    } else {
      actions += '<span class="nt-droit">' + (d === 'lire' ? 'Lecture seule' : 'Vous pouvez modifier') + '</span>';
    }
    if (d !== 'lire') actions += '<button type="button" class="btn btn-petit" data-act="sous">' + ICONE_PLUS + 'Sous-page</button>';
    if (d === 'proprio') actions += '<button type="button" class="btn btn-petit nt-btn-suppr" data-act="supprimer" title="Mettre à la corbeille">' + ICONE_CORBEILLE + '</button>';
    else if ((parId(n.id) || {}).racine_partage) actions += '<button type="button" class="btn btn-petit" data-act="quitter" title="Retirer cette note de vos notes partagées">Quitter</button>';
    c.innerHTML =
      '<div class="nt-barre">' +
      '<div class="nt-fil">' + racine + '<span class="nt-fil-sep">/</span>' + fil +
      '<span class="nt-fil-cur" id="nt-fil-cur">' + esc(titre(n)) + '</span></div>' +
      '<div class="nt-actions">' +
      '<span class="nt-presents" id="nt-presents"></span>' +
      '<span class="nt-modif" id="nt-modif">' + (n.modifie_le ? 'Modifiée ' + esc(quand(n.modifie_le)) : '') + '</span>' +
      actions + '</div></div>' +
      '<div class="nt-page">' +
      '<textarea class="nt-titre" id="nt-titre" rows="1" placeholder="Sans titre" maxlength="200" spellcheck="true"' + (d === 'lire' ? ' readonly' : '') + '>' +
      esc(n.title === 'Sans titre' ? '' : n.title) + '</textarea>' +
      '<div class="nt-corps" id="nt-corps"></div>' +
      enfantsHtml(n) +
      '</div>';
    var ta = document.getElementById('nt-titre');
    ajusterTitre(ta);
    monterEditeur(document.getElementById('nt-corps'), n);
    rendrePresences();
    var pa = document.getElementById('nt-panneau');
    if (pa) pa.dataset.note = '';
    rendrePanneau();
    crochets('note', n);
  }

  /* Qui d'autre a la note ouverte : initiales, une fois par personne. */
  function rendrePresences() {
    var el = document.getElementById('nt-presents');
    if (!el) return;
    var vus = {};
    var gens = (S.presences || []).filter(function (p) {
      if (vus[p.user_id]) return false;
      vus[p.user_id] = 1;
      return true;
    });
    var E = window.MySifaNotesEditeur;
    el.innerHTML = gens.map(function (p) {
      return '<span class="nt-present" style="--nt-present:' + (E ? E.couleur(p.user_id) : 'var(--accent)') + '" title="' + esc(p.nom) + ' est sur la note">' +
        esc(E ? E.initiales(p.nom) : '?') + '</span>';
    }).join('');
  }

  /* Sous-pages sans lien dans le contenu : listées sous la note, pour ne pas les perdre. */
  function enfantsHtml(n) {
    var liees = {};
    (n.blocs || []).forEach(function (b) { if (b.type === 'page') liees[b.ref] = 1; });
    var autres = enfants(n.id).filter(function (f) { return !liees[f.id]; });
    if (!autres.length) return '';
    return '<div class="nt-enfants"><div class="nt-section">Sous-pages</div>' + autres.map(function (f) {
      return '<a class="nt-enfant" href="/note?note=' + f.id + '" data-id="' + f.id + '">' + ICONE_NOTE + '<span>' + esc(titre(f)) + '</span></a>';
    }).join('') + '</div>';
  }

  function ajusterTitre(ta) {
    if (!ta) return;
    ta.style.height = '0';
    ta.style.height = ta.scrollHeight + 'px';
  }

  function monterEditeur(corps, note) {
    if (!corps || !window.MySifaNotesEditeur) return;
    var d = droit();
    S.ed = window.MySifaNotesEditeur.monter(corps, note, Object.assign({
      noteId: note.id,
      flux: true,
      lectureSeule: d === 'lire',
      poignees: d !== 'lire',
      placeholder: 'Écrire librement, ou « / » pour insérer un titre, une liste, une image, une sous-page…',
      surChange: function () {
        var m = document.getElementById('nt-modif');
        if (m) m.textContent = 'Modification…';
      },
      surEnregistre: function (r) {
        if (!r || !S.courante || S.courante.id !== note.id) return;
        S.courante.modifie_le = r.modifie_le || S.courante.modifie_le;
        var m = document.getElementById('nt-modif');
        if (m) m.textContent = 'Enregistrée';
        majResume(S.courante);
      },
      surPresences: function (liste) {
        S.presences = liste || [];
        rendrePresences();
      },
      surTitre: function (t) {
        if (!S.courante || S.courante.id !== note.id) return;
        S.courante.title = t;
        majResume(S.courante);
        var ta = document.getElementById('nt-titre');
        if (ta && document.activeElement !== ta) { ta.value = t === 'Sans titre' ? '' : t; ajusterTitre(ta); }
        var cur = document.getElementById('nt-fil-cur');
        if (cur) cur.textContent = t;
        rendreArbre();
      },
      recharger: function () {
        api('/api/postits/' + note.id).then(function (n) {
          if (!S.courante || S.courante.id !== note.id) return;
          S.courante.blocs = n.blocs;
          S.courante.revision = n.revision;
          if (S.ed) S.ed.remplacer(n);
        }).catch(function () {
          toast('Cette note ne vous est plus accessible.', 'danger');
          chargerArbre().then(allerAccueil);
        });
      },
      creerSousPage: d === 'lire' ? null : function () {
        return api('/api/postits', {
          method: 'POST',
          body: { type: 'someday', title: 'Sans titre', parent_id: note.id, sur_ecran: 0, blocs: [] },
        }).then(function (sp) {
          return chargerArbre().then(function () {
            S.ouvertes[note.id] = 1;
            ecrireOuvertes();
            rendreArbre();
            return sp;
          });
        }).catch(function (e) { toast(e.message || 'Création impossible.', 'danger'); });
      },
      ouvrirPage: function (id) {
        ouvrir(id, { focusTitre: true });
      },
      titrePage: function (ref) {
        var p = parId(ref);
        return p ? titre(p) : null;
      },
      signaler: function (msg, type) { toast(msg, type || 'danger'); },
      surCommentaires: function () { crochets('com-distant'); },
    }, PAGE.optionsEditeur ? PAGE.optionsEditeur(note) : {}));
  }

  function enregistrerTitre() {
    var n = S.courante;
    var ta = document.getElementById('nt-titre');
    if (!n || !ta) return;
    var t = ta.value.replace(/\s+/g, ' ').trim() || 'Sans titre';
    if (t === n.title) return;
    n.title = t;
    majResume(n);
    api('/api/postits/' + n.id, { method: 'PATCH', body: { title: t, client: window.MySifaNotesEditeur ? window.MySifaNotesEditeur.client : '' }, keepalive: true })
      .then(function (r) {
        if (r) n.modifie_le = r.modifie_le;
      })
      .catch(function (e) { toast(e.message || 'Titre non enregistré.', 'danger'); });
  }

  /* ── Panneau d'actions rapides (droite) ─────────────────────────────── */

  var MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');
  var TOUCHE = MAC ? '⌘' : 'Ctrl';

  function panneauPrefere() {
    try {
      var v = localStorage.getItem('mysifa_notes_panneau');
      if (v === '1' || v === '0') return v === '1';
    } catch (e) {}
    return window.innerWidth >= 1200;
  }

  function panneauDisponible() {
    return S.vue === 'note' && S.courante && S.ed;
  }

  /* Onglet du panneau : actions rapides (qui peut écrire) ou commentaires. */
  function ongletPanneau() {
    if (droit() === 'lire') return 'commentaires';
    return S.ongletPanneau === 'commentaires' ? 'commentaires' : 'actions';
  }

  function ouvrirOngletPanneau(onglet) {
    S.ongletPanneau = onglet;
    var el = document.getElementById('nt-panneau');
    if (el) el.dataset.note = '';
    basculerPanneau(true);
  }

  function basculerPanneau(force) {
    var ouvert = force == null ? !panneauPrefere() : !!force;
    try { localStorage.setItem('mysifa_notes_panneau', ouvert ? '1' : '0'); } catch (e) {}
    rendrePanneau();
  }

  function rendrePanneau() {
    var el = document.getElementById('nt-panneau');
    if (!el) return;
    var dispo = panneauDisponible();
    var ouvert = dispo && panneauPrefere();
    el.hidden = !ouvert;
    document.body.classList.toggle('nt-panneau-ouvert', ouvert);
    var btn = document.querySelector('[data-act="panneau"]');
    if (btn) {
      btn.hidden = !dispo;
      btn.classList.toggle('actif', ouvert);
      btn.title = (ouvert ? 'Masquer' : 'Afficher') + ' le panneau : actions et commentaires (' + TOUCHE + ' + \\)';
    }
    var onglet = ongletPanneau();
    PAGE.adresse.commentaires = ouvert && onglet === 'commentaires' ? 1 : null;
    if (!ouvert || el.dataset.note === String(S.courante.id) + onglet) return;
    el.dataset.note = String(S.courante.id) + onglet;
    var onglets = '<div class="nt-pa-onglets" role="tablist">' +
      (droit() !== 'lire' ? '<button type="button" role="tab" data-onglet="actions"' + (onglet === 'actions' ? ' class="sel" aria-selected="true"' : '') + '>Actions</button>' : '') +
      '<button type="button" role="tab" data-onglet="commentaires"' + (onglet === 'commentaires' ? ' class="sel" aria-selected="true"' : '') +
      '>Commentaires<span class="nt-pa-nb" id="nt-pa-nb-com"></span></button>' +
      '<button type="button" class="nt-fermer" data-cmd="fermer" title="Masquer (' + TOUCHE + ' + \\)" aria-label="Masquer le panneau">×</button></div>';
    if (onglet === 'commentaires') {
      el.innerHTML = onglets + '<div id="nt-coms"></div>';
      crochets('commentaires', document.getElementById('nt-coms'));
      return;
    }
    var cmds = window.MySifaNotesEditeur.commandes(S.ed);
    var parCle = {};
    cmds.forEach(function (c) { parCle[c.cle] = c; });
    function bouton(cle, libelle, icone, aide) {
      return '<button type="button" class="nt-pa-btn" data-cmd="' + cle + '" title="' + esc(aide || libelle) + '">' +
        '<span class="nt-pa-ico">' + icone + '</span><span>' + esc(libelle) + '</span></button>';
    }
    var inserer = ['p', 'h1', 'h2', 'h3', 'todo', 'puce', 'num', 'bascule', 'tableau', 'citation', 'encadre', 'code', 'sep', 'image', 'page', 'mysifa', 'modele', 'date', 'heure']
      .filter(function (k) { return parCle[k]; })
      .map(function (k) { var c = parCle[k]; return bouton(k, c.libelle, esc(c.icone), c.aide); }).join('');
    var formats = [
      ['gras', 'Gras', '<b>G</b>', TOUCHE + ' + B'],
      ['italique', 'Italique', '<i>I</i>', TOUCHE + ' + I'],
      ['souligne', 'Souligné', '<u>S</u>', TOUCHE + ' + U'],
      ['barre', 'Barré', '<s>B</s>', TOUCHE + ' + Maj + S'],
      ['code_ligne', 'Code', '&lt;/&gt;', TOUCHE + ' + E'],
      ['lien_texte', 'Lien', '↗', TOUCHE + ' + K'],
    ].map(function (f) {
      return '<button type="button" class="nt-pa-fmt" data-cmd="' + f[0] + '" title="' + esc(f[1] + ' (' + f[3] + ')') + '" aria-label="' + esc(f[1]) + '">' + f[2] + '</button>';
    }).join('');
    var raccourcis = [
      ['/', 'menu d\'insertion'],
      ['# ', 'titre (## et ### : plus petits)'],
      ['- ', 'liste à puces'],
      ['1. ', 'liste numérotée'],
      ['[] ', 'case à cocher'],
      ['> ', 'citation'],
      ['---', 'séparateur'],
      ['-->', 'flèche →'],
      ['Tab', 'décaler (Maj + Tab : revenir)'],
      [TOUCHE + ' + Entrée', 'cocher la case'],
      ['Maj + Entrée', 'retour à la ligne dans le bloc'],
      ['@', 'lier un dossier, une machine, un client, une note'],
      [TOUCHE + ' + F', 'rechercher dans la note'],
      [TOUCHE + ' + K', 'rechercher une note (hors texte)'],
    ].map(function (r) {
      return '<div class="nt-pa-rac"><kbd>' + esc(r[0]) + '</kbd><span>' + esc(r[1]) + '</span></div>';
    }).join('');
    el.innerHTML = onglets +
      '<div class="nt-pa-section">Mise en forme</div><div class="nt-pa-formats">' + formats + '</div>' +
      '<p class="nt-pa-aide">Sélectionnez du texte, puis cliquez.</p>' +
      '<div class="nt-pa-section">Insérer</div><div class="nt-pa-grille">' + inserer + '</div>' +
      '<div class="nt-pa-section">Bloc</div><div class="nt-pa-grille">' +
      bouton('dupliquer', 'Dupliquer', '⧉', 'Copie le bloc juste en dessous') +
      bouton('supprimer', 'Supprimer', '×', 'Retire le bloc où est le curseur') +
      bouton('effacer_cochees', 'Effacer cochées', '✓', 'Retire les cases cochées de la note') +
      '</div>' +
      '<div class="nt-pa-section">Raccourcis</div><div class="nt-pa-raccourcis">' + raccourcis + '</div>';
  }

  function brancherPanneau() {
    var el = document.getElementById('nt-panneau');
    if (!el) return;
    /* mousedown empêché : le curseur et la sélection restent dans la note. */
    el.addEventListener('mousedown', function (e) {
      if (e.target.closest('#nt-coms')) return;
      if (e.target.closest('[data-cmd], [data-onglet]')) e.preventDefault();
    });
    el.addEventListener('click', function (e) {
      var o = e.target.closest('[data-onglet]');
      if (o) { ouvrirOngletPanneau(o.dataset.onglet); ecrireAdresse(); return; }
      if (e.target.closest('#nt-coms')) return;
      var b = e.target.closest('[data-cmd]');
      if (!b || !S.ed) return;
      var cmd = b.dataset.cmd;
      if (cmd === 'fermer') return basculerPanneau(false);
      if (cmd === 'effacer_cochees') {
        if (!S.ed.aCoche()) return toast('Aucune case cochée dans cette note.', 'info');
        return S.ed.effacerCochees();
      }
      S.ed.commande(cmd);
      if (window.innerWidth < 1100) basculerPanneau(false);
    });
  }

  /* ── Partage ────────────────────────────────────────────────────────── */

  var _annuaire = null;

  function echapPartage(e) {
    if (e.key !== 'Escape' || !S.partage) return;
    if (e.target && e.target.id === 'nt-partage-q' && e.target.value) return;
    e.preventDefault();
    fermerPartage();
  }

  function ouvrirPartage() {
    if (!S.courante || droit() !== 'proprio') return;
    S.partage = true;
    var root = document.getElementById('mroot');
    root.innerHTML =
      '<div class="nt-modal-fond" id="nt-partage-fond"><div class="nt-modal nt-modal-partage" role="dialog" aria-modal="true" aria-label="Partager la note">' +
      '<div class="nt-modal-tete"><h3>Partager « ' + esc(titre(S.courante)) + ' »</h3>' +
      '<button type="button" class="nt-fermer" data-p="fermer" aria-label="Fermer">×</button></div>' +
      '<p class="nt-modal-aide">Les collègues ajoutés voient la note et ses sous-pages. En modification, vous écrivez ensemble, en direct.</p>' +
      '<input type="search" id="nt-partage-q" class="nt-champ" placeholder="Ajouter un collègue (nom)" autocomplete="off">' +
      '<div class="nt-partage-resultats" id="nt-partage-res"></div>' +
      '<div class="nt-section">Accès</div><div class="nt-partage-liste" id="nt-partage-liste"></div>' +
      '</div></div>';
    rendrePartages();
    ecrireAdresse();
    document.addEventListener('keydown', echapPartage, true);
    var fond = document.getElementById('nt-partage-fond');
    fond.addEventListener('mousedown', function (e) {
      if (e.target === fond) fermerPartage();
    });
    fond.addEventListener('click', surClicPartage);
    fond.addEventListener('change', function (e) {
      var sel = e.target.closest('select[data-user]');
      if (sel) partagerAvec(Number(sel.dataset.user), sel.value);
    });
    var q = document.getElementById('nt-partage-q');
    q.addEventListener('input', rendreResultats);
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && q.value) { e.preventDefault(); e.stopPropagation(); q.value = ''; rendreResultats(); }
      if (e.key === 'Enter') {
        var b = document.querySelector('#nt-partage-res [data-ajout]');
        if (b) { e.preventDefault(); partagerAvec(Number(b.dataset.ajout), 'ecrire'); }
      }
    });
    if (!_annuaire) {
      api('/api/postits/annuaire').then(function (l) { _annuaire = l || []; rendreResultats(); }).catch(function () { _annuaire = []; });
    }
    requestAnimationFrame(function () { q.focus(); });
  }

  function fermerPartage(sansAdresse) {
    S.partage = false;
    document.removeEventListener('keydown', echapPartage, true);
    var root = document.getElementById('mroot');
    if (root && root.querySelector('#nt-partage-fond')) root.innerHTML = '';
    if (!sansAdresse) ecrireAdresse();
  }

  function rendrePartages() {
    var el = document.getElementById('nt-partage-liste');
    if (!el || !S.courante) return;
    var liste = S.courante.partages || [];
    el.innerHTML = '<div class="nt-partage-ligne"><span class="nt-present" style="--nt-present:var(--accent)">' +
      esc(window.MySifaNotesEditeur ? window.MySifaNotesEditeur.initiales((window.__NOTES__ && window.__NOTES__.user.nom) || 'Moi') : '') +
      '</span><span class="nt-partage-nom">' + esc((window.__NOTES__ && window.__NOTES__.user.nom) || 'Vous') + '</span><span class="nt-partage-droit">Auteur</span></div>' +
      liste.map(function (p) {
        return '<div class="nt-partage-ligne"><span class="nt-present" style="--nt-present:' + (window.MySifaNotesEditeur ? window.MySifaNotesEditeur.couleur(p.user_id) : 'var(--accent)') + '">' +
          esc(window.MySifaNotesEditeur ? window.MySifaNotesEditeur.initiales(p.nom) : '') + '</span>' +
          '<span class="nt-partage-nom">' + esc(p.nom || 'Utilisateur') + '</span>' +
          '<select class="nt-champ nt-champ-petit" data-user="' + p.user_id + '" aria-label="Accès de ' + esc(p.nom || '') + '">' +
          '<option value="ecrire"' + (p.droit === 'ecrire' ? ' selected' : '') + '>Modification</option>' +
          '<option value="lire"' + (p.droit === 'lire' ? ' selected' : '') + '>Lecture</option></select>' +
          '<button type="button" class="nt-fermer" data-retirer="' + p.user_id + '" title="Retirer l\'accès" aria-label="Retirer l\'accès">×</button></div>';
      }).join('');
  }

  function rendreResultats() {
    var el = document.getElementById('nt-partage-res');
    var q = document.getElementById('nt-partage-q');
    if (!el || !q) return;
    var t = sansAccent(q.value.trim());
    if (!t) { el.innerHTML = ''; return; }
    if (!_annuaire) { el.innerHTML = '<div class="nt-arbre-vide">Chargement…</div>'; return; }
    var deja = {};
    (S.courante.partages || []).forEach(function (p) { deja[p.user_id] = 1; });
    var res = _annuaire.filter(function (u) { return !deja[u.id] && sansAccent(u.nom).indexOf(t) >= 0; }).slice(0, 8);
    el.innerHTML = res.length ? res.map(function (u) {
      return '<button type="button" class="nt-partage-res" data-ajout="' + u.id + '"><span class="nt-partage-nom">' + esc(u.nom) + '</span>' +
        '<span class="nt-partage-role">' + esc(u.role || '') + '</span><span class="nt-partage-ajout">Ajouter</span></button>';
    }).join('') : '<div class="nt-arbre-vide">Aucun résultat pour « ' + esc(q.value.trim()) + ' »</div>';
  }

  function surClicPartage(e) {
    var a = e.target.closest('[data-ajout], [data-retirer], [data-p]');
    if (!a) return;
    if (a.dataset.p === 'fermer') return fermerPartage();
    if (a.dataset.ajout) return partagerAvec(Number(a.dataset.ajout), 'ecrire', true);
    if (a.dataset.retirer) return retirerPartage(Number(a.dataset.retirer));
  }

  async function partagerAvec(userId, droitPartage, ajout) {
    try {
      var liste = await api('/api/postits/' + S.courante.id + '/partages', { method: 'PUT', body: { user_id: userId, droit: droitPartage } });
      S.courante.partages = liste || [];
      var n = parId(S.courante.id);
      if (n) n.nb_partages = S.courante.partages.length;
      if (ajout) {
        var q = document.getElementById('nt-partage-q');
        if (q) { q.value = ''; q.focus(); }
        toast('Note partagée.');
      }
      rendrePartages();
      rendreResultats();
      rendreArbre();
      majBoutonPartage();
    } catch (e) {
      toast(e.message || 'Partage impossible.', 'danger');
    }
  }

  async function retirerPartage(userId) {
    try {
      await api('/api/postits/' + S.courante.id + '/partages/' + userId, { method: 'DELETE' });
      S.courante.partages = (S.courante.partages || []).filter(function (p) { return p.user_id !== userId; });
      var n = parId(S.courante.id);
      if (n) n.nb_partages = S.courante.partages.length;
      rendrePartages();
      rendreResultats();
      rendreArbre();
      majBoutonPartage();
    } catch (e) {
      toast(e.message || 'Modification impossible.', 'danger');
    }
  }

  function majBoutonPartage() {
    var b = document.querySelector('[data-act="partager"]');
    if (!b || !S.courante) return;
    var nb = (S.courante.partages || []).length;
    b.classList.toggle('actif', !!nb);
    b.innerHTML = ICONE_PARTAGE + (nb ? 'Partagée · ' + nb : 'Partager');
  }

  async function quitterPartage() {
    var n = S.courante;
    if (!n) return;
    var ok = await confirmer('Quitter cette note ?', '« ' + titre(n) + ' » disparaîtra de vos notes partagées. Son auteur pourra la repartager.', 'Quitter', true);
    if (!ok) return;
    try {
      await api('/api/postits/' + n.id + '/partages/' + moi(), { method: 'DELETE' });
      await chargerArbre();
      toast('Note retirée de vos notes partagées.');
      allerAccueil();
    } catch (e) {
      toast(e.message || 'Modification impossible.', 'danger');
    }
  }

  /* ── Actions ────────────────────────────────────────────────────────── */

  async function basculerEcran() {
    var n = S.courante;
    if (!n) return;
    try {
      var r = await api('/api/postits/' + n.id, { method: 'PATCH', body: { sur_ecran: !n.sur_ecran } });
      n.sur_ecran = r.sur_ecran;
      var s = parId(n.id);
      if (s) s.sur_ecran = r.sur_ecran;
      toast(n.sur_ecran ? 'Note affichée en post-it.' : 'Post-it retiré de l\'écran.');
      if (S.ed) S.ed.vider();
      rendre();
    } catch (e) {
      toast(e.message || 'Modification impossible.', 'danger');
    }
  }

  async function supprimer(id) {
    var n = parId(id) || S.courante;
    if (!n) return;
    var nbSous = 0;
    (function compter(pid) { enfants(pid).forEach(function (f) { nbSous++; compter(f.id); }); })(n.id);
    var ok = await confirmer(
      'Mettre à la corbeille ?',
      '« ' + titre(n) + ' »' + (nbSous ? ' et ses ' + nbSous + ' sous-page' + (nbSous > 1 ? 's' : '') : '') + ' — restaurable depuis la corbeille.',
      'Mettre à la corbeille',
      true
    );
    if (!ok) return;
    try {
      if (S.ed && S.courante && S.courante.id === n.id) S.ed.vider();
      await api('/api/postits/' + n.id, { method: 'DELETE' });
      await chargerArbre();
      toast('Note mise à la corbeille.');
      if (S.courante && (S.courante.id === n.id || !parId(S.courante.id))) {
        var parent = n.parent_id ? parId(n.parent_id) : null;
        if (parent) return ouvrir(parent.id);
        return allerAccueil();
      }
      rendre();
    } catch (e) {
      toast(e.message || 'Suppression impossible.', 'danger');
    }
  }

  async function restaurer(id) {
    try {
      await api('/api/postits/' + id + '/restaurer', { method: 'POST' });
      await chargerArbre();
      toast('Note restaurée.');
      rendre();
    } catch (e) {
      toast(e.message || 'Restauration impossible.', 'danger');
    }
  }

  async function purger(id) {
    var n = null;
    S.corbeille.forEach(function (x) { if (x.id === id) n = x; });
    var ok = await confirmer('Supprimer définitivement ?', '« ' + titre(n) + ' » sera effacée sans retour possible.', 'Supprimer', true);
    if (!ok) return;
    try {
      await api('/api/postits/' + id + '/definitif', { method: 'DELETE' });
      await chargerArbre();
      toast('Note supprimée.');
      rendre();
    } catch (e) {
      toast(e.message || 'Suppression impossible.', 'danger');
    }
  }

  async function deplacer(id, parentId) {
    if (id === parentId) return;
    try {
      await api('/api/postits/' + id, { method: 'PATCH', body: { parent_id: parentId || null } });
      await chargerArbre();
      if (parentId) { S.ouvertes[parentId] = 1; ecrireOuvertes(); }
      if (S.courante && S.courante.id === id) S.courante.parent_id = parentId || null;
      rendre();
    } catch (e) {
      toast(e.message || 'Déplacement impossible.', 'danger');
    }
  }

  /* ── Événements ─────────────────────────────────────────────────────── */

  function brancher() {
    document.getElementById('nt-nouvelle').addEventListener('click', function () {
      creerNote(null);
    });
    document.getElementById('nt-nav-accueil').addEventListener('click', allerAccueil);
    document.getElementById('nt-nav-corbeille').addEventListener('click', allerCorbeille);

    var q = document.getElementById('nt-q');
    q.addEventListener('input', function () {
      S.q = q.value;
      rendreArbre();
    });
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { q.value = ''; S.q = ''; rendreArbre(); }
      if (e.key === 'Enter') {
        var premier = document.querySelector('#nt-arbre .nt-item');
        if (premier) { e.preventDefault(); ouvrir(Number(premier.dataset.id)); }
      }
    });

    var arbre = document.getElementById('nt-arbre');
    arbre.addEventListener('click', function (e) {
      var item = e.target.closest('.nt-item');
      if (!item) return;
      var id = Number(item.dataset.id);
      var act = e.target.closest('[data-act]');
      if (act && act.dataset.act === 'plier') {
        if (S.ouvertes[id]) delete S.ouvertes[id];
        else S.ouvertes[id] = 1;
        ecrireOuvertes();
        return rendreArbre();
      }
      if (act && act.dataset.act === 'sous') return creerNote(id);
      ouvrir(id);
    });
    arbre.addEventListener('dragstart', function (e) {
      var item = e.target.closest('.nt-item');
      if (!item) return;
      _dragNote = Number(item.dataset.id);
      try { e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', item.textContent); } catch (err) {}
    });
    function survol(e, el) {
      if (!_dragNote || !el) return;
      e.preventDefault();
      document.querySelectorAll('.nt-cible').forEach(function (x) { x.classList.remove('nt-cible'); });
      el.classList.add('nt-cible');
    }
    arbre.addEventListener('dragover', function (e) { survol(e, e.target.closest('.nt-item')); });
    arbre.addEventListener('drop', function (e) {
      var item = e.target.closest('.nt-item');
      if (!_dragNote || !item) return;
      e.preventDefault();
      var de = _dragNote;
      _dragNote = null;
      document.querySelectorAll('.nt-cible').forEach(function (x) { x.classList.remove('nt-cible'); });
      deplacer(de, Number(item.dataset.id));
    });
    var racine = document.getElementById('nt-racine');
    racine.addEventListener('dragover', function (e) { survol(e, racine); });
    racine.addEventListener('drop', function (e) {
      if (!_dragNote) return;
      e.preventDefault();
      var de = _dragNote;
      _dragNote = null;
      racine.classList.remove('nt-cible');
      deplacer(de, null);
    });
    document.addEventListener('dragend', function () {
      _dragNote = null;
      document.querySelectorAll('.nt-cible').forEach(function (x) { x.classList.remove('nt-cible'); });
    });

    var content = document.getElementById('content');
    content.addEventListener('click', function (e) {
      var a = e.target.closest('[data-act]');
      var act = a && a.dataset.act;
      if (act === 'nouvelle') return creerNote(null);
      if (act === 'accueil') { e.preventDefault(); return allerAccueil(); }
      if (act === 'ecran') return basculerEcran();
      if (act === 'partager') return ouvrirPartage();
      if (act && PAGE.actions[act]) { e.preventDefault(); return PAGE.actions[act](a, e); }
      if (act === 'panneau') return basculerPanneau();
      if (act === 'quitter') return quitterPartage();
      if (act === 'sous' && S.courante) return creerNote(S.courante.id);
      if (act === 'supprimer' && S.courante) return supprimer(S.courante.id);
      var ligne = e.target.closest('.nt-ligne');
      if (act === 'restaurer' && ligne) return restaurer(Number(ligne.dataset.id));
      if (act === 'purger' && ligne) return purger(Number(ligne.dataset.id));
      /* Liens internes (fil d'Ariane, cartes, sous-pages, blocs « page ») : sans recharger. */
      var lien = e.target.closest('.nt-carte, .nt-fil-lien[data-id], .nt-enfant, .pb-lien');
      if (lien && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
        var id = Number(lien.dataset.id || lien.dataset.ref);
        if (id) { e.preventDefault(); ouvrir(id); }
      }
    });
    content.addEventListener('input', function (e) {
      if (e.target.id !== 'nt-titre') return;
      ajusterTitre(e.target);
      var cur = document.getElementById('nt-fil-cur');
      var t = e.target.value.trim() || 'Sans titre';
      if (cur) cur.textContent = t;
      document.title = t + ' — Mes notes — MySifa';
      var sub = document.getElementById('mobile-sub');
      if (sub) sub.textContent = t;
      var nom =document.querySelector('#nt-arbre .nt-item[data-id="' + S.courante.id + '"] .nt-item-nom');
      if (nom) nom.textContent = t;
      if (_titreTimer) clearTimeout(_titreTimer);
      _titreTimer = setTimeout(function () { _titreTimer = null; enregistrerTitre(); }, 600);
    });
    content.addEventListener('keydown', function (e) {
      if (e.target.id !== 'nt-titre') return;
      if (e.key === 'Enter' || (e.key === 'ArrowDown' && !e.shiftKey)) {
        e.preventDefault();
        if (S.ed) S.ed.focus(0, 0);
      }
    });
    content.addEventListener('focusout', function (e) {
      if (e.target.id === 'nt-titre' && _titreTimer) {
        clearTimeout(_titreTimer);
        _titreTimer = null;
        enregistrerTitre();
      }
    });

    /* Cmd/Ctrl+K : recherche ; Cmd/Ctrl+Alt+N : nouvelle note. */
    document.addEventListener('keydown', function (e) {
      var mod = e.metaKey || e.ctrlKey;
      if (mod && !e.shiftKey && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        document.body.classList.add('sb-open');
        q.focus();
        q.select();
      }
      if (mod && (e.key === '\\' || e.code === 'Backslash') && panneauDisponible()) {
        e.preventDefault();
        basculerPanneau();
      }
      if (mod && e.altKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        creerNote(null);
      }
    });

    window.addEventListener('pagehide', function () {
      if (_titreTimer) { clearTimeout(_titreTimer); _titreTimer = null; enregistrerTitre(); }
    });
  }

  /* ── Icônes ─────────────────────────────────────────────────────────── */

  var ICONE_PARTAGE = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.6-3 2.8-4.6 5.5-4.6s4.9 1.6 5.5 4.6"/><circle cx="17" cy="9" r="2.4"/><path d="M16 13.6c2.3.1 4 1.5 4.5 4"/></svg>';
  var ICONE_PANNEAU = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="15" y1="4" x2="15" y2="20"/></svg>';
  var ICONE_NOTE = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 16h4"/></svg>';
  var ICONE_CHEV = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>';
  var ICONE_PLUS = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  var ICONE_POSTIT = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5h12l4 4v10H5V5z"/><path d="M17 5v4h4"/></svg>';
  var ICONE_CORBEILLE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

  /* ── Démarrage ──────────────────────────────────────────────────────── */

  Object.assign(PAGE, {
    S: S, api: api, toast: toast, esc: esc, quand: quand, titre: titre, parId: parId, droit: droit, moi: moi,
    ouvrir: ouvrir, rendre: rendre, rendreArbre: rendreArbre, chargerArbre: chargerArbre,
    confirmer: confirmer, ecrireAdresse: ecrireAdresse, allerAccueil: allerAccueil,
    carte: carte, ouvrirOngletPanneau: ouvrirOngletPanneau, basculerPanneau: basculerPanneau,
    rendrePanneau: rendrePanneau, ongletPanneau: ongletPanneau, creerNote: creerNote,
    sur: function (quoi, fn) { (PAGE.abonnes[quoi] = PAGE.abonnes[quoi] || []).push(fn); },
    /* Paramètres d'adresse ajoutés par les modules : {cle: valeur} quand la note est ouverte. */
    adresse: {},
  });
  window.MySifaNotesPage = PAGE;

  window.toggleSidebar = function () { document.body.classList.toggle('sb-open'); };
  window.closeSidebar = function () { document.body.classList.remove('sb-open'); };

  async function demarrer() {
    lireOuvertes();
    brancher();
    brancherPanneau();
    try {
      await chargerArbre();
    } catch (e) {
      document.getElementById('content').innerHTML = '<div class="nt-vide"><h2>Chargement impossible</h2><p>' + esc(e.message || '') + '</p></div>';
      return;
    }
    S.pret = true;
    var u = window.MySifaUrl ? window.MySifaUrl.lire() : null;
    if (u && u.get('nouvelle', null) === '1') {
      /* Lien « Nouvelle note » (explorateur MyQualité) : l'adresse devient celle de la note créée. */
      try { history.replaceState(history.state, '', '/note'); } catch (e) {}
      await creerNote(null);
    } else if (u) {
      await lireAdresse(u);
    } else {
      allerAccueil();
    }
    if (window.MySifaUrl) window.MySifaUrl.surRetour(lireAdresse);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();
