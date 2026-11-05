/* MySifa — Réunions : l'espace commun (/reunions).
 *
 * Trois vues, toutes dans l'adresse (.claude/rules/url-etat.md) :
 *   liste    /reunions[?type=<id>]          réunions visibles, mes écoutes
 *   reunion  /reunions?reunion=<id>         compte-rendu : notes, décisions, actions
 *   ecoute   /reunions?ecoute=<id>          brief proposé à relire et valider
 * Fenêtre : ?nouvelle=1 (création d'une réunion). Hors adresse : la
 * confirmation de suppression (étape d'un geste en cours).
 *
 * Rien n'est filtré ici : l'API ne renvoie que ce que la personne voit
 * (app/routers/reunions.py, rn.peut_voir). Les saisies libres sont posées par
 * textContent / value, jamais par innerHTML.
 *
 * L'enregistrement vit sur sa propre page (/reunions/ecoute, mysifa_ecoute.js).
 */
(function () {
  'use strict';

  var BOOT = window.__REUNIONS__ || {};
  var S = {
    vue: 'liste',
    type: '',
    reunionId: null,
    ecouteId: null,
    nouvelle: false,
    ctx: null,
    reunions: null,
    ecoutes: null,
    reunion: null,
    ecoute: null,
    brief: null,             // brief en cours de relecture (copie modifiable)
    briefPour: null,         // id de l'écoute dont `brief` est la copie
    enreg: '',               // état de l'enregistrement automatique
    erreur: null
  };
  var minuteurNotes = null;
  var minuteurSuivi = null;

  /* ── Outils ─────────────────────────────────────────────────── */

  function h(tag, attrs) {
    var el = document.createElement(tag);
    var a = attrs || {};
    Object.keys(a).forEach(function (k) {
      var v = a[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'className') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'html') el.innerHTML = v;            // SVG statiques uniquement
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'value') el.value = v;
      else if (k === 'checked') el.checked = !!v;
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) ajouter(el, arguments[i]);
    return el;
  }
  function ajouter(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { ajouter(el, x); }); return; }
    el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }
  function toast(msg, type) {
    var w = document.getElementById('toast-wrap');
    if (!w) return;
    var t = h('div', {className: 'toast ' + (type || 'success'), text: msg});
    w.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }
  async function api(chemin, init) {
    var opts = Object.assign({credentials: 'include', headers: {}}, init || {});
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
      opts.headers['Content-Type'] = 'application/json';
    }
    var r = await fetch(chemin, opts);
    if (r.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); throw new Error('Session expirée.'); }
    var d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) throw new Error((d && d.detail) || ('Erreur ' + r.status));
    return d;
  }
  function dateFr(s) {
    if (!s) return '';
    var d = String(s).slice(0, 10).split('-');
    return d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0] : String(s);
  }
  function heureFr(s) { return s && String(s).length >= 16 ? String(s).slice(11, 16) : ''; }
  function duree(sec) {
    sec = Math.round(Number(sec) || 0);
    var hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60);
    return hh ? hh + ' h ' + String(mm).padStart(2, '0') : mm + ' min';
  }
  function aujourdhui() {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function modalOuverte() { var m = document.getElementById('mroot'); return !!(m && m.firstElementChild); }
  function lignes(t) {
    return String(t || '').split('\n').map(function (l) { return l.replace(/^\s*[-•·*]\s*/, '').trim(); })
      .filter(function (l) { return l; });
  }
  var TONS = {enregistrement: 'danger', a_transcrire: 'neutre', transcription: '', a_structurer: '',
              proposition: 'warn', validee: 'ok', erreur: 'danger', abandonnee: 'neutre'};
  function pastilleStatut(e) {
    return h('span', {className: 'reu-pastille ' + (TONS[e.statut] || ''), text: e.statut_libelle || e.statut});
  }
  var ICONE_MICRO = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 10.5a6.5 6.5 0 0 0 13 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8.5" y1="21" x2="15.5" y2="21"/></svg>';
  var ICONE_LISTE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg>';
  var ICONE_ACTIONS = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';

  function libelleVisibilite(r) {
    var V = (S.ctx && S.ctx.visibilites) || {};
    if (r.visibilite === 'roles') {
      var R = {};
      ((S.ctx && S.ctx.roles) || []).forEach(function (x) { R[x.code] = x.libelle; });
      return (r.roles_visibles || []).map(function (c) { return R[c] || c; }).join(', ') || V.roles || 'Rôles';
    }
    return V[r.visibilite] || r.visibilite || '';
  }

  /* ── Adresse ────────────────────────────────────────────────── */

  function ecrireAdresse() {
    if (!window.MySifaUrl) return;
    var p = {}, nav = 'liste';
    if (S.vue === 'reunion' && S.reunionId) { p.reunion = S.reunionId; nav = 'reunion'; }
    else if (S.vue === 'ecoute' && S.ecouteId) { p.ecoute = S.ecouteId; nav = 'ecoute'; }
    else if (S.type) { p.type = S.type; }
    if (S.nouvelle) { p.nouvelle = '1'; nav += '/nouvelle'; }
    window.MySifaUrl.ecrire(p, {navigation: nav});
  }
  function lireAdresse() {
    var u = window.MySifaUrl ? window.MySifaUrl.lire() : null;
    var g = function (k) { return u ? u.get(k) : new URLSearchParams(location.search).get(k); };
    var rid = g('reunion'), eid = g('ecoute'), t = g('type');
    S.reunionId = rid && /^\d+$/.test(rid) ? Number(rid) : null;
    S.ecouteId = eid && /^\d+$/.test(eid) ? Number(eid) : null;
    S.type = t && /^\d+$/.test(t) ? t : '';
    S.vue = S.ecouteId ? 'ecoute' : (S.reunionId ? 'reunion' : 'liste');
    S.nouvelle = g('nouvelle') === '1';
  }

  /* ── Chargements ────────────────────────────────────────────── */

  async function chargerListe() {
    var q = S.type ? '?type=' + encodeURIComponent(S.type) : '';
    var res = await Promise.all([api('/api/reunions' + q), api('/api/reunions/ecoutes')]);
    S.reunions = res[0].reunions || [];
    S.ecoutes = res[1].ecoutes || [];
  }
  async function chargerReunion() {
    S.reunion = null;
    var d = await api('/api/reunions/' + S.reunionId + '?avec_prod=false');
    S.reunion = d.reunion;
  }
  async function chargerEcoute() {
    var d = await api('/api/reunions/ecoutes/' + S.ecouteId);
    S.ecoute = d;
    if (d.ecoute.statut === 'proposition' && S.briefPour !== d.ecoute.id) {
      S.brief = briefInitial(d.ecoute);
      S.briefPour = d.ecoute.id;
    }
  }
  async function charger() {
    S.erreur = null;
    try {
      if (!S.ctx) S.ctx = await api('/api/reunions/contexte');
      if (S.vue === 'reunion') await chargerReunion();
      else if (S.vue === 'ecoute') await chargerEcoute();
      else await chargerListe();
    } catch (e) {
      S.erreur = e.message;
    }
    render();
  }

  /* ── Barre latérale ─────────────────────────────────────────── */

  function renderNav() {
    var hote = document.getElementById('reu-nav-types');
    if (!hote || !S.ctx) return;
    hote.innerHTML = '';
    var actif = function (t) { return S.vue === 'liste' && S.type === t; };
    hote.appendChild(h('button', {type: 'button', className: 'nav-btn' + (actif('') ? ' active' : ''),
      html: ICONE_LISTE + '<span>Toutes</span>', onClick: function () { allerListe(''); }}));
    (S.ctx.types || []).forEach(function (t) {
      var b = h('button', {type: 'button', className: 'nav-btn' + (actif(String(t.id)) ? ' active' : ''),
        html: ICONE_LISTE, onClick: function () { allerListe(String(t.id)); }});
      b.appendChild(h('span', {text: t.libelle}));
      hote.appendChild(b);
    });
    if (S.ctx.moi && S.ctx.moi.voit_prod) {
      hote.appendChild(h('div', {className: 'nav-section-label msb-section'}, h('span', {text: 'Suivi'})));
      var a = h('a', {className: 'nav-btn', href: '/prod?page=production&sous=reunions', html: ICONE_ACTIONS});
      a.appendChild(h('span', {text: "Actions de l'atelier"}));
      hote.appendChild(a);
    }
  }

  /* ── Navigation ─────────────────────────────────────────────── */

  function fermerSidebar() { document.body.classList.remove('sb-open'); }
  function allerListe(type) {
    S.vue = 'liste'; S.type = type || ''; S.reunionId = null; S.ecouteId = null; S.nouvelle = false;
    fermerSidebar(); arreterSuivi();
    S.reunions = null; render(); charger();
  }
  function ouvrirReunion(id) {
    S.vue = 'reunion'; S.reunionId = id; S.ecouteId = null; S.nouvelle = false;
    arreterSuivi(); S.reunion = null; render(); charger();
  }
  function ouvrirEcoute(id) {
    S.vue = 'ecoute'; S.ecouteId = id; S.reunionId = null; S.nouvelle = false;
    S.ecoute = null; render(); charger();
  }

  /* ── Rendu ──────────────────────────────────────────────────── */

  function render() {
    renderNav();
    var c = document.getElementById('content');
    if (!c) return;
    var y = c.parentElement ? c.parentElement.scrollTop : 0;
    c.innerHTML = '';
    if (S.erreur) {
      c.appendChild(h('div', {className: 'reu-carte'},
        h('div', {className: 'reu-avert'}, h('strong', {text: 'Chargement impossible. '}), S.erreur),
        h('button', {type: 'button', className: 'btn', text: 'Retour à la liste', onClick: function () { allerListe(''); }})));
    } else if (S.vue === 'reunion') {
      c.appendChild(S.reunion ? vueReunion(S.reunion) : h('div', {className: 'reu-chargement', text: 'Chargement…'}));
    } else if (S.vue === 'ecoute') {
      c.appendChild(S.ecoute ? vueEcoute(S.ecoute) : h('div', {className: 'reu-chargement', text: 'Chargement…'}));
    } else {
      c.appendChild(vueListe());
    }
    if (c.parentElement) c.parentElement.scrollTop = y;
    var sous = document.getElementById('mobile-sub');
    if (sous) sous.textContent = S.vue === 'reunion' ? 'Compte-rendu' : (S.vue === 'ecoute' ? 'Brief' : 'Comptes-rendus');
    document.title = (S.vue === 'reunion' && S.reunion ? S.reunion.titre + ' — ' : '') + 'Réunions — MySifa';
    if (S.nouvelle && S.ctx && !modalOuverte()) modaleNouvelle();
    if (!S.nouvelle && modalOuverte() && document.getElementById('reu-modal-nouvelle')) fermerModale(true);
    ecrireAdresse();
  }

  /* Liste */
  function vueListe() {
    var racine = h('div');
    var typeCourant = (S.ctx && S.ctx.types || []).filter(function (t) { return String(t.id) === S.type; })[0];
    racine.appendChild(h('div', {className: 'reu-tete'},
      h('div', null, h('h1', {text: typeCourant ? 'Réunions · ' + typeCourant.libelle : 'Réunions'}),
        h('p', {text: 'Comptes-rendus, décisions et actions de toutes les réunions que vous pouvez voir.'})),
      h('div', {className: 'reu-rangee'},
        h('a', {className: 'btn btn-accent', href: '/reunions/ecoute', html: ICONE_MICRO + '<span>Écouter une réunion</span>'}),
        h('button', {type: 'button', className: 'btn', text: '+ Nouvelle réunion',
          onClick: function () { S.nouvelle = true; render(); }}))));

    var enCours = (S.ecoutes || []).filter(function (e) { return e.statut !== 'validee'; });
    if (enCours.length) {
      var carte = h('div', {className: 'reu-carte'}, h('h2', {text: 'Mes écoutes'}));
      enCours.forEach(function (e) { carte.appendChild(ligneEcoute(e)); });
      racine.appendChild(carte);
    }

    var filtres = h('div', {className: 'reu-filtres'});
    [{id: '', libelle: 'Toutes'}].concat((S.ctx && S.ctx.types) || []).forEach(function (t) {
      filtres.appendChild(h('button', {type: 'button', className: 'reu-filtre' + (S.type === String(t.id) ? ' actif' : ''),
        text: t.libelle, onClick: function () { allerListe(String(t.id)); }}));
    });
    racine.appendChild(filtres);

    if (S.reunions === null) { racine.appendChild(h('div', {className: 'reu-chargement', text: 'Chargement…'})); return racine; }
    if (!S.reunions.length) {
      racine.appendChild(h('div', {className: 'reu-vide', text: 'Aucune réunion pour l’instant. « Écouter une réunion » enregistre la prochaine et propose son compte-rendu.'}));
      return racine;
    }
    S.reunions.forEach(function (r) {
      var meta = h('div', {className: 'reu-ligne-meta'});
      if (r.type) meta.appendChild(h('span', {className: 'reu-pastille neutre', text: r.type.libelle}));
      if (r.ouverte) meta.appendChild(h('span', {className: 'reu-pastille', text: 'Ouverte'}));
      if (r.nb_actions) meta.appendChild(h('span', {text: r.actions_restantes + ' action(s) restante(s) sur ' + r.nb_actions}));
      if (r.participants && r.participants.length) meta.appendChild(h('span', {text: r.participants.join(', ')}));
      racine.appendChild(h('div', {className: 'reu-ligne', role: 'button', tabindex: '0',
        onClick: function () { ouvrirReunion(r.id); },
        onKeydown: function (ev) { if (ev.key === 'Enter') ouvrirReunion(r.id); }},
        h('div', {className: 'reu-ligne-date', text: dateFr(r.date_debut) + (r.date_fin && r.date_fin !== r.date_debut ? ' → ' + dateFr(r.date_fin) : '')}),
        h('div', {className: 'reu-ligne-corps'}, h('div', {className: 'reu-ligne-titre', text: r.titre}), meta)));
    });
    return racine;
  }

  function ligneEcoute(e) {
    var meta = h('div', {className: 'reu-ligne-meta'}, pastilleStatut(e));
    if (e.type) meta.appendChild(h('span', {text: e.type.libelle}));
    if (e.duree_s) meta.appendChild(h('span', {text: duree(e.duree_s)}));
    if (e.attente_min) meta.appendChild(h('span', {text: 'brief dans ~' + e.attente_min + ' min'}));
    if (e.statut === 'erreur' && e.erreur) meta.appendChild(h('span', {text: e.erreur}));
    return h('div', {className: 'reu-ligne', role: 'button', tabindex: '0',
      onClick: function () { if (e.statut === 'enregistrement') location.href = '/reunions/ecoute'; else ouvrirEcoute(e.id); }},
      h('div', {className: 'reu-ligne-date', text: dateFr(e.demarre_le) + ' ' + heureFr(e.demarre_le)}),
      h('div', {className: 'reu-ligne-corps'}, h('div', {className: 'reu-ligne-titre', text: e.titre || 'Écoute n° ' + e.id}), meta));
  }

  /* Compte-rendu */
  function enregistrerPlus(champs) {
    S.enreg = 'Enregistrement…'; peindreEtat();
    clearTimeout(minuteurNotes);
    minuteurNotes = setTimeout(async function () {
      try {
        var r = await api('/api/reunions/' + S.reunion.id, {method: 'POST', body: champs()});
        S.reunion.updated_at = r.updated_at;
        S.enreg = 'Enregistré'; peindreEtat();
      } catch (e) { S.enreg = ''; peindreEtat(); toast(e.message, 'danger'); }
    }, 700);
  }
  function peindreEtat() {
    var el = document.getElementById('reu-etat-enreg');
    if (el) el.textContent = S.enreg;
  }
  function champsTexte() {
    return {titre: S.reunion.titre, notes: S.reunion.notes, decisions: S.reunion.decisions};
  }

  function vueReunion(r) {
    var peut = r.droits && r.droits.modifier, gere = r.droits && r.droits.gerer;
    var racine = h('div');
    racine.appendChild(h('div', {className: 'reu-rangee', style: 'margin-bottom:12px'},
      h('button', {type: 'button', className: 'btn btn-petit', text: '← Réunions', onClick: function () { allerListe(S.type); }}),
      r.type ? h('span', {className: 'reu-pastille neutre', text: r.type.libelle}) : null,
      h('span', {className: 'reu-muet', text: dateFr(r.date_debut) + (r.date_fin && r.date_fin !== r.date_debut ? ' → ' + dateFr(r.date_fin) : '')}),
      h('span', {className: 'reu-muet', text: '· Visible : ' + libelleVisibilite(r)}),
      h('span', {className: 'reu-enreg', id: 'reu-etat-enreg', text: S.enreg})));

    if (peut) {
      racine.appendChild(h('input', {type: 'text', className: 'reu-champ', style: 'font-size:20px;font-weight:800;margin-bottom:14px',
        value: r.titre, 'aria-label': 'Titre', onInput: function (ev) { r.titre = ev.target.value; enregistrerPlus(champsTexte); }}));
    } else {
      racine.appendChild(h('h1', {style: 'font-size:22px;font-weight:800;margin-bottom:14px', text: r.titre}));
    }

    var gauche = h('div');
    var zone = function (titre, cle, aide) {
      var carte = h('div', {className: 'reu-carte'}, h('h2', {text: titre}));
      if (peut) {
        carte.appendChild(h('textarea', {value: r[cle] || '', placeholder: aide, 'aria-label': titre,
          onInput: function (ev) { r[cle] = ev.target.value; enregistrerPlus(champsTexte); }}));
      } else {
        carte.appendChild(h('div', {style: 'white-space:pre-wrap;font-size:13px;line-height:1.6', text: r[cle] || '—'}));
      }
      return carte;
    };
    gauche.appendChild(zone('Notes', 'notes', 'Les points abordés…'));
    gauche.appendChild(zone('Décisions', 'decisions', 'Une décision par ligne'));
    gauche.appendChild(carteActions(r, peut));

    var droite = h('div');
    droite.appendChild(carteParticipants(r, peut));
    if (gere) droite.appendChild(carteVisibilite(r));
    if (r.ecoutes && r.ecoutes.length) {
      var ce = h('div', {className: 'reu-carte'}, h('h2', {text: 'Écoutes'}));
      r.ecoutes.forEach(function (e) {
        ce.appendChild(h('div', {className: 'reu-muet', style: 'margin-bottom:4px',
          text: dateFr(e.demarre_le) + ' ' + heureFr(e.demarre_le) + (e.duree_s ? ' · ' + duree(e.duree_s) : '') + (e.valide_le ? ' · brief validé' : '')}));
      });
      droite.appendChild(ce);
    }
    if (gere) {
      droite.appendChild(h('div', {className: 'reu-carte'},
        h('div', {className: 'reu-rangee'},
          h('button', {type: 'button', className: 'btn btn-petit', text: r.ouverte ? 'Clore la réunion' : 'Rouvrir', onClick: async function () {
            try { var x = await api('/api/reunions/' + r.id + '/clore', {method: 'POST', body: {rouvrir: !r.ouverte}}); S.reunion = Object.assign(S.reunion, x); render(); toast(x.ouverte ? 'Réunion rouverte.' : 'Réunion close.'); }
            catch (e) { toast(e.message, 'danger'); }
          }}),
          h('button', {type: 'button', className: 'btn btn-petit btn-danger', text: 'Supprimer', onClick: function () { confirmerSuppression(r); }}))));
    }
    racine.appendChild(h('div', {className: 'reu-grille'}, gauche, droite));
    return racine;
  }

  function carteActions(r, peut) {
    var carte = h('div', {className: 'reu-carte'}, h('h2', {text: 'Actions'}));
    if (!r.actions || !r.actions.length) carte.appendChild(h('div', {className: 'reu-muet', text: 'Aucune action.'}));
    (r.actions || []).forEach(function (a) {
      var meta = [a.responsable || 'Non attribuée', a.echeance ? 'pour le ' + dateFr(a.echeance) : ''].filter(Boolean).join(' · ');
      carte.appendChild(h('div', {className: 'reu-action' + (a.fait ? ' fait' : '')},
        h('input', {type: 'checkbox', checked: a.fait, 'aria-label': 'Fait', onChange: async function (ev) {
          try { var x = await api('/api/reunions/actions/' + a.id, {method: 'POST', body: {fait: ev.target.checked}}); Object.assign(a, x.action || {}); render(); }
          catch (e) { ev.target.checked = !ev.target.checked; toast(e.message, 'danger'); }
        }}),
        h('div', {className: 'reu-action-corps'}, h('div', {className: 'reu-action-texte', text: a.texte}), h('div', {className: 'reu-action-meta', text: meta})),
        peut ? h('button', {type: 'button', className: 'reu-retirer', 'aria-label': 'Retirer', text: '×', onClick: async function () {
          try { await api('/api/reunions/actions/' + a.id, {method: 'POST', body: {texte: ''}}); r.actions = r.actions.filter(function (x) { return x.id !== a.id; }); render(); toast('Action retirée.'); }
          catch (e) { toast(e.message, 'danger'); }
        }}) : null));
    });
    if (peut) {
      var texte = h('input', {type: 'text', placeholder: 'Nouvelle action', 'aria-label': 'Nouvelle action'});
      var resp = h('input', {type: 'text', placeholder: 'Responsable', list: 'reu-personnes', 'aria-label': 'Responsable'});
      var ech = h('input', {type: 'date', 'aria-label': 'Échéance'});
      var ajouterAction = async function () {
        if (!texte.value.trim()) { texte.focus(); return; }
        try {
          var a = await api('/api/reunions/' + r.id + '/actions', {method: 'POST', body: {texte: texte.value, responsable: resp.value, echeance: ech.value}});
          r.actions = (r.actions || []).concat([a]); render(); toast('Action ajoutée.');
        } catch (e) { toast(e.message, 'danger'); }
      };
      texte.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') ajouterAction(); });
      carte.appendChild(h('div', {className: 'reu-ajout-action'}, texte, resp, ech,
        h('button', {type: 'button', className: 'btn btn-petit', text: 'Ajouter', onClick: ajouterAction})));
      carte.appendChild(listePersonnes());
    }
    return carte;
  }

  function listePersonnes() {
    var dl = h('datalist', {id: 'reu-personnes'});
    ((S.ctx && S.ctx.personnes) || []).forEach(function (p) { dl.appendChild(h('option', {value: p.nom})); });
    return dl;
  }

  function carteParticipants(r, peut) {
    var carte = h('div', {className: 'reu-carte'}, h('h2', {text: 'Participants'}));
    var noms = (r.participants || []).map(function (p) { return p.nom; });
    var puces = h('div', {className: 'reu-puces'});
    if (!noms.length) puces.appendChild(h('span', {className: 'reu-muet', text: 'Aucun participant noté.'}));
    var poser = async function (liste) {
      try { var x = await api('/api/reunions/' + r.id, {method: 'POST', body: {participants: liste}}); S.reunion = Object.assign(S.reunion, x); render(); }
      catch (e) { toast(e.message, 'danger'); }
    };
    noms.forEach(function (n) {
      puces.appendChild(h('span', {className: 'reu-puce'}, n,
        peut ? h('button', {type: 'button', 'aria-label': 'Retirer ' + n, text: '×', onClick: function () { poser(noms.filter(function (x) { return x !== n; })); }}) : null));
    });
    carte.appendChild(puces);
    if (peut) {
      var champ = h('input', {type: 'text', placeholder: 'Ajouter un participant', list: 'reu-personnes', style: 'margin-top:10px', 'aria-label': 'Ajouter un participant'});
      champ.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' && champ.value.trim()) poser(noms.concat([champ.value.trim()]));
      });
      champ.addEventListener('change', function () {
        var v = champ.value.trim();
        if (v && ((S.ctx && S.ctx.personnes) || []).some(function (p) { return p.nom === v; })) poser(noms.concat([v]));
      });
      carte.appendChild(champ);
      carte.appendChild(listePersonnes());
    }
    return carte;
  }

  function selectVisibilite(valeur, roles, surChange) {
    var V = (S.ctx && S.ctx.visibilites) || {};
    var sel = h('select', {'aria-label': 'Visibilité', onChange: function () { surChange(sel.value, lireRoles()); peindreRoles(); }});
    Object.keys(V).forEach(function (k) { sel.appendChild(h('option', {value: k, text: V[k]})); });
    sel.value = valeur || 'participants';
    var boite = h('div', {className: 'reu-roles'});
    var cases = [];
    ((S.ctx && S.ctx.roles) || []).forEach(function (x) {
      if (x.code === 'superadmin') return;
      var c = h('input', {type: 'checkbox', checked: (roles || []).indexOf(x.code) >= 0, onChange: function () { surChange(sel.value, lireRoles()); }});
      c.dataset.role = x.code;
      cases.push(c);
      boite.appendChild(h('label', null, c, x.libelle));
    });
    function lireRoles() { return cases.filter(function (c) { return c.checked; }).map(function (c) { return c.dataset.role; }); }
    function peindreRoles() { boite.style.display = sel.value === 'roles' ? '' : 'none'; }
    peindreRoles();
    return h('div', null, sel, boite,
      h('div', {className: 'reu-muet', style: 'margin-top:8px;font-size:12px', text: 'Le créateur et les participants voient toujours la réunion.'}));
  }

  function carteVisibilite(r) {
    var carte = h('div', {className: 'reu-carte'}, h('h2', {text: 'Visibilité'}));
    var minuteur = null;
    carte.appendChild(selectVisibilite(r.visibilite, r.roles_visibles, function (vis, roles) {
      clearTimeout(minuteur);
      minuteur = setTimeout(async function () {
        if (vis === 'roles' && !roles.length) return;
        try {
          var x = await api('/api/reunions/' + r.id, {method: 'POST', body: {visibilite: vis, roles_visibles: roles}});
          S.reunion.visibilite = x.visibilite; S.reunion.roles_visibles = x.roles_visibles;
          toast('Visibilité enregistrée.');
        } catch (e) { toast(e.message, 'danger'); }
      }, 500);
    }));
    return carte;
  }

  function confirmerSuppression(r) {
    var root = document.getElementById('mroot');
    root.innerHTML = '';
    root.appendChild(h('div', {className: 'reu-voile', onClick: function (ev) { if (ev.target === ev.currentTarget) root.innerHTML = ''; }},
      h('div', {className: 'reu-modal', role: 'dialog', 'aria-modal': 'true'},
        h('h3', {text: 'Supprimer la réunion ?'}),
        h('p', {className: 'reu-muet', text: '« ' + r.titre + ' », ses notes, décisions et actions sont supprimées. Cette opération ne s’annule pas.'}),
        h('div', {className: 'reu-rangee'},
          h('button', {type: 'button', className: 'btn', text: 'Annuler', onClick: function () { root.innerHTML = ''; }}),
          h('button', {type: 'button', className: 'btn btn-danger', text: 'Supprimer', onClick: async function () {
            try { await api('/api/reunions/' + r.id, {method: 'DELETE'}); root.innerHTML = ''; toast('Réunion supprimée.'); allerListe(S.type); }
            catch (e) { toast(e.message, 'danger'); }
          }})))));
  }

  /* Nouvelle réunion */
  function fermerModale(sansAdresse) {
    var root = document.getElementById('mroot');
    if (root) root.innerHTML = '';
    if (S.nouvelle) { S.nouvelle = false; if (!sansAdresse) ecrireAdresse(); }
  }
  function modaleNouvelle() {
    var types = (S.ctx && S.ctx.types) || [];
    var d = {type_id: S.type || (types[0] && String(types[0].id)) || '', titre: '', date_debut: aujourdhui(), participants: []};
    var typeDe = function (id) { return types.filter(function (t) { return String(t.id) === String(id); })[0]; };
    var t0 = typeDe(d.type_id);
    d.visibilite = t0 ? t0.visibilite_defaut : 'participants';
    d.roles = t0 ? t0.roles_defaut.slice() : [];
    var hoteVis = h('div');
    var peindreVis = function () {
      hoteVis.innerHTML = '';
      hoteVis.appendChild(selectVisibilite(d.visibilite, d.roles, function (v, r) { d.visibilite = v; d.roles = r; }));
    };
    var sel = h('select', {'aria-label': 'Type', onChange: function () {
      d.type_id = sel.value; var t = typeDe(d.type_id);
      if (t) { d.visibilite = t.visibilite_defaut; d.roles = t.roles_defaut.slice(); peindreVis(); }
    }});
    types.forEach(function (t) { sel.appendChild(h('option', {value: String(t.id), text: t.libelle})); });
    sel.value = d.type_id;
    peindreVis();
    var titre = h('input', {type: 'text', placeholder: 'Sujet de la réunion', 'aria-label': 'Titre', onInput: function (ev) { d.titre = ev.target.value; }});
    var jour = h('input', {type: 'date', value: d.date_debut, 'aria-label': 'Date', onInput: function (ev) { d.date_debut = ev.target.value; }});
    var creer = async function () {
      if (d.visibilite === 'roles' && !d.roles.length) { toast('Choisir au moins un rôle.', 'danger'); return; }
      try {
        var r = await api('/api/reunions', {method: 'POST', body: {espace: true, type_id: d.type_id, titre: d.titre,
          date_debut: d.date_debut, date_fin: d.date_debut, visibilite: d.visibilite, roles_visibles: d.roles}});
        fermerModale(true);
        toast('Réunion créée.');
        ouvrirReunion(r.id);
      } catch (e) { toast(e.message, 'danger'); }
    };
    var root = document.getElementById('mroot');
    root.innerHTML = '';
    root.appendChild(h('div', {className: 'reu-voile', id: 'reu-modal-nouvelle', onClick: function (ev) { if (ev.target === ev.currentTarget) fermerModale(); }},
      h('div', {className: 'reu-modal', role: 'dialog', 'aria-modal': 'true'},
        h('h3', {text: 'Nouvelle réunion'}),
        h('label', {className: 'reu-label', text: 'Type'}), sel,
        h('label', {className: 'reu-label', text: 'Titre'}), titre,
        h('label', {className: 'reu-label', text: 'Date'}), jour,
        h('label', {className: 'reu-label', text: 'Visible par'}), hoteVis,
        h('div', {className: 'reu-rangee'},
          h('button', {type: 'button', className: 'btn', text: 'Annuler', onClick: function () { fermerModale(); }}),
          h('button', {type: 'button', className: 'btn btn-accent', text: 'Créer', onClick: creer})))));
    requestAnimationFrame(function () { titre.focus(); });
  }

  /* Écoute : suivi et brief à valider */
  function briefInitial(e) {
    var p = e.proposition || {};
    var notes = [p.resume || '', p.notes || ''].filter(function (x) { return x.trim(); }).join('\n\n');
    if (p.points_ouverts && p.points_ouverts.length) {
      notes += (notes ? '\n\n' : '') + 'Points ouverts :\n' + p.points_ouverts.map(function (x) { return '- ' + x; }).join('\n');
    }
    var type = e.type || null;
    return {
      titre: p.titre || e.titre || '',
      type_id: type ? String(type.id) : '',
      date: String(e.demarre_le || '').slice(0, 10),
      reunion_id: e.reunion_id ? String(e.reunion_id) : '',
      notes: notes,
      decisions: (p.decisions || []).join('\n'),
      actions: (p.actions || []).map(function (a) { return {texte: a.texte || '', responsable: a.responsable || '', echeance: a.echeance || ''}; }),
      participants: (p.participants || []).slice(),
      visibilite: null,
      roles: null
    };
  }

  function arreterSuivi() { clearTimeout(minuteurSuivi); minuteurSuivi = null; }
  function suivre() {
    arreterSuivi();
    minuteurSuivi = setTimeout(async function () {
      if (S.vue !== 'ecoute' || modalOuverte()) { suivre(); return; }
      try { await chargerEcoute(); render(); } catch (e) { /* nouvel essai au prochain tour */ }
    }, 15000);
  }

  function vueEcoute(d) {
    var e = d.ecoute;
    var racine = h('div');
    racine.appendChild(h('div', {className: 'reu-rangee', style: 'margin-bottom:12px'},
      h('button', {type: 'button', className: 'btn btn-petit', text: '← Réunions', onClick: function () { allerListe(''); }}),
      pastilleStatut(e),
      h('span', {className: 'reu-muet', text: 'Écoute du ' + dateFr(e.demarre_le) + ' à ' + heureFr(e.demarre_le) + (e.duree_s ? ' · ' + duree(e.duree_s) : '')})));

    if (e.statut === 'proposition') { arreterSuivi(); racine.appendChild(vueValidation(d)); return racine; }

    var carte = h('div', {className: 'reu-carte'});
    if (e.statut === 'enregistrement') {
      carte.appendChild(h('h2', {text: 'Enregistrement en cours'}));
      carte.appendChild(h('p', {className: 'reu-muet', text: 'L’écoute se poursuit sur la page d’enregistrement.'}));
      carte.appendChild(h('div', {className: 'reu-rangee', style: 'margin-top:12px'}, h('a', {className: 'btn btn-accent', href: '/reunions/ecoute', text: 'Reprendre l’enregistrement'})));
      suivre();
    } else if (['a_transcrire', 'transcription', 'a_structurer'].indexOf(e.statut) >= 0) {
      carte.appendChild(h('h2', {text: e.statut_libelle}));
      carte.appendChild(h('p', {className: 'reu-muet', text: e.attente_min
        ? 'Brief prêt dans ~' + e.attente_min + ' min. Cette page se met à jour toute seule ; vous pouvez la quitter, une notification vous préviendra.'
        : 'Cette page se met à jour toute seule.'}));
      suivre();
    } else if (e.statut === 'erreur') {
      carte.appendChild(h('h2', {text: 'L’écoute n’a pas abouti'}));
      carte.appendChild(h('div', {className: 'reu-avert', text: e.erreur || 'Erreur inconnue.'}));
      carte.appendChild(h('div', {className: 'reu-rangee'},
        h('button', {type: 'button', className: 'btn btn-accent', text: 'Relancer', onClick: async function () {
          try { await api('/api/reunions/ecoutes/' + e.id + '/relancer', {method: 'POST'}); toast('Écoute relancée.'); charger(); }
          catch (x) { toast(x.message, 'danger'); }
        }}),
        boutonAbandon(e)));
    } else if (e.statut === 'validee') {
      carte.appendChild(h('h2', {text: 'Brief validé'}));
      carte.appendChild(h('div', {className: 'reu-rangee'}, e.reunion_id ? h('button', {type: 'button', className: 'btn btn-accent', text: 'Ouvrir la réunion', onClick: function () { ouvrirReunion(e.reunion_id); }}) : null));
    } else {
      carte.appendChild(h('h2', {text: 'Écoute abandonnée'}));
      carte.appendChild(h('p', {className: 'reu-muet', text: e.erreur || 'L’audio et la transcription ont été effacés.'}));
    }
    if (['a_transcrire', 'transcription', 'a_structurer', 'enregistrement'].indexOf(e.statut) >= 0) {
      carte.appendChild(h('div', {className: 'reu-rangee', style: 'margin-top:14px'}, boutonAbandon(e)));
    }
    racine.appendChild(carte);
    return racine;
  }

  function boutonAbandon(e) {
    return h('button', {type: 'button', className: 'btn btn-danger btn-petit', text: 'Abandonner', onClick: function () {
      var root = document.getElementById('mroot');
      root.innerHTML = '';
      root.appendChild(h('div', {className: 'reu-voile', onClick: function (ev) { if (ev.target === ev.currentTarget) root.innerHTML = ''; }},
        h('div', {className: 'reu-modal', role: 'dialog', 'aria-modal': 'true'},
          h('h3', {text: 'Abandonner cette écoute ?'}),
          h('p', {className: 'reu-muet', text: 'L’audio et la transcription sont effacés. Rien n’est écrit dans les réunions.'}),
          h('div', {className: 'reu-rangee'},
            h('button', {type: 'button', className: 'btn', text: 'Annuler', onClick: function () { root.innerHTML = ''; }}),
            h('button', {type: 'button', className: 'btn btn-danger', text: 'Abandonner', onClick: async function () {
              try { await api('/api/reunions/ecoutes/' + e.id + '/abandonner', {method: 'POST'}); root.innerHTML = ''; toast('Écoute abandonnée.'); allerListe(''); }
              catch (x) { toast(x.message, 'danger'); }
            }})))));
    }});
  }

  function vueValidation(d) {
    var e = d.ecoute, b = S.brief;
    var types = d.types || [];
    var gauche = h('div', {className: 'reu-carte'}, h('h2', {text: 'Brief proposé'}));
    if (e.morceaux_manquants && e.morceaux_manquants.length) {
      gauche.appendChild(h('div', {className: 'reu-avert'}, h('strong', {text: 'Passages manquants. '}),
        e.morceaux_manquants.length + ' passage(s) de 30 s ne sont pas arrivés au serveur : le brief ne les couvre pas.'));
    }
    if (!(e.type && e.type.structuration_ia === false) && !e.proposition) {
      gauche.appendChild(h('div', {className: 'reu-avert', text: 'Aucune proposition : rédiger le brief à partir de la transcription.'}));
    }
    if (e.type && e.type.structuration_ia === false) {
      gauche.appendChild(h('div', {className: 'reu-muet', style: 'margin-bottom:10px', text: 'Type de réunion sans proposition IA : la transcription n’a pas quitté le serveur. Rédiger le brief à partir d’elle.'}));
    }
    gauche.appendChild(h('div', {className: 'reu-muet', style: 'font-size:12px', text: 'Proposition à relire : la transcription ne sait pas qui parle, les responsables sont déduits des noms prononcés.'}));

    gauche.appendChild(h('label', {className: 'reu-label', text: 'Titre'}));
    gauche.appendChild(h('input', {type: 'text', value: b.titre, onInput: function (ev) { b.titre = ev.target.value; }}));

    var rattache = h('select', {'aria-label': 'Réunion', onChange: function () { b.reunion_id = rattache.value; render(); }});
    rattache.appendChild(h('option', {value: '', text: 'Nouvelle réunion'}));
    (d.reunions || []).forEach(function (r) {
      rattache.appendChild(h('option', {value: String(r.id), text: dateFr(r.date_debut) + ' · ' + r.titre}));
    });
    rattache.value = b.reunion_id || '';
    gauche.appendChild(h('label', {className: 'reu-label', text: 'Enregistrer dans'}));
    gauche.appendChild(rattache);

    if (!b.reunion_id) {
      var selType = h('select', {'aria-label': 'Type', onChange: function () { b.type_id = selType.value; b.visibilite = null; b.roles = null; render(); }});
      types.forEach(function (t) { selType.appendChild(h('option', {value: String(t.id), text: t.libelle})); });
      if (!b.type_id && types[0]) b.type_id = String(types[0].id);
      selType.value = b.type_id;
      var t = types.filter(function (x) { return String(x.id) === String(b.type_id); })[0];
      if (b.visibilite === null) { b.visibilite = t ? t.visibilite_defaut : 'participants'; b.roles = t ? t.roles_defaut.slice() : []; }
      gauche.appendChild(h('div', {className: 'reu-deux'},
        h('div', null, h('label', {className: 'reu-label', text: 'Type'}), selType),
        h('div', null, h('label', {className: 'reu-label', text: 'Date'}), h('input', {type: 'date', value: b.date, onInput: function (ev) { b.date = ev.target.value; }}))));
      gauche.appendChild(h('label', {className: 'reu-label', text: 'Visible par'}));
      gauche.appendChild(selectVisibilite(b.visibilite, b.roles, function (v, r) { b.visibilite = v; b.roles = r; }));
    }

    gauche.appendChild(h('label', {className: 'reu-label', text: 'Notes'}));
    gauche.appendChild(h('textarea', {value: b.notes, style: 'min-height:200px', onInput: function (ev) { b.notes = ev.target.value; }}));
    gauche.appendChild(h('label', {className: 'reu-label', text: 'Décisions — une par ligne'}));
    gauche.appendChild(h('textarea', {value: b.decisions, onInput: function (ev) { b.decisions = ev.target.value; }}));

    gauche.appendChild(h('label', {className: 'reu-label', text: 'Actions'}));
    var hoteActions = h('div');
    b.actions.forEach(function (a, i) {
      hoteActions.appendChild(h('div', {className: 'reu-prop-action'},
        h('input', {type: 'text', value: a.texte, placeholder: 'Action', 'aria-label': 'Action', onInput: function (ev) { a.texte = ev.target.value; }}),
        h('input', {type: 'text', value: a.responsable, placeholder: 'Responsable', list: 'reu-personnes', 'aria-label': 'Responsable', onInput: function (ev) { a.responsable = ev.target.value; }}),
        h('input', {type: 'date', value: a.echeance, 'aria-label': 'Échéance', onInput: function (ev) { a.echeance = ev.target.value; }}),
        h('button', {type: 'button', className: 'reu-retirer', 'aria-label': 'Retirer', text: '×', onClick: function () { b.actions.splice(i, 1); render(); }})));
    });
    if (!b.actions.length) hoteActions.appendChild(h('div', {className: 'reu-muet', style: 'margin-bottom:6px', text: 'Aucune action proposée.'}));
    gauche.appendChild(hoteActions);
    gauche.appendChild(h('button', {type: 'button', className: 'btn btn-petit', text: '+ Ajouter une action', onClick: function () { b.actions.push({texte: '', responsable: '', echeance: ''}); render(); }}));

    gauche.appendChild(h('label', {className: 'reu-label', text: 'Participants'}));
    var puces = h('div', {className: 'reu-puces'});
    b.participants.forEach(function (n, i) {
      puces.appendChild(h('span', {className: 'reu-puce'}, n, h('button', {type: 'button', 'aria-label': 'Retirer ' + n, text: '×', onClick: function () { b.participants.splice(i, 1); render(); }})));
    });
    gauche.appendChild(puces);
    var champP = h('input', {type: 'text', placeholder: 'Ajouter un participant', list: 'reu-personnes', style: 'margin-top:8px', 'aria-label': 'Ajouter un participant'});
    champP.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' && champP.value.trim()) { b.participants.push(champP.value.trim()); render(); }
    });
    gauche.appendChild(champP);
    var dl = h('datalist', {id: 'reu-personnes'});
    (d.personnes || []).forEach(function (p) { dl.appendChild(h('option', {value: p.nom})); });
    gauche.appendChild(dl);

    var droite = h('div', {className: 'reu-carte'}, h('h2', {text: 'Transcription'}));
    var tr = h('div', {className: 'reu-transcription'});
    String(e.transcription || '').split('\n').forEach(function (l) {
      var m = /^(\[[\d:]+\])\s?(.*)$/.exec(l);
      var div = h('div');
      if (m) { div.appendChild(h('span', {className: 'reu-t-temps', text: m[1]})); div.appendChild(document.createTextNode(m[2])); }
      else div.textContent = l;
      tr.appendChild(div);
    });
    if (!e.transcription) tr.appendChild(h('div', {className: 'reu-muet', text: 'Transcription vide.'}));
    droite.appendChild(tr);
    if (e.purge_le) droite.appendChild(h('div', {className: 'reu-muet', style: 'margin-top:8px;font-size:12px', text: 'Effacée le ' + dateFr(e.purge_le) + '.'}));

    var valider = async function (bouton) {
      if (!b.reunion_id && b.visibilite === 'roles' && !(b.roles || []).length) { toast('Choisir au moins un rôle.', 'danger'); return; }
      bouton.disabled = true;
      try {
        var corps = {titre: b.titre, type_id: b.type_id || null, date: b.date, reunion_id: b.reunion_id || null,
          notes: b.notes, decisions: lignes(b.decisions), participants: b.participants,
          actions: b.actions.filter(function (a) { return a.texte.trim(); }),
          visibilite: b.visibilite, roles_visibles: b.roles};
        var res = await api('/api/reunions/ecoutes/' + e.id + '/valider', {method: 'POST', body: corps});
        S.brief = null; S.briefPour = null;
        toast('Brief validé.');
        ouvrirReunion(res.reunion.id);
      } catch (x) { bouton.disabled = false; toast(x.message, 'danger'); }
    };
    var btnValider = h('button', {type: 'button', className: 'btn btn-accent', text: 'Valider le brief', onClick: function () { valider(btnValider); }});
    return h('div', null,
      h('div', {className: 'reu-valid'}, gauche, droite),
      h('div', {className: 'reu-pied-valid'}, boutonAbandon(e), btnValider));
  }

  /* ── Démarrage ──────────────────────────────────────────────── */

  window.toggleSidebar = function () { document.body.classList.toggle('sb-open'); };
  window.closeSidebar = fermerSidebar;
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && modalOuverte()) fermerModale();
  });
  if (window.MySifaUrl) {
    window.MySifaUrl.surRetour(function () {
      var avant = S.vue + ':' + S.reunionId + ':' + S.ecouteId + ':' + S.type;
      lireAdresse();
      if (!S.nouvelle && modalOuverte()) fermerModale(true);
      if (avant !== S.vue + ':' + S.reunionId + ':' + S.ecouteId + ':' + S.type) {
        arreterSuivi(); S.reunion = null; S.ecoute = null; S.reunions = null;
        render(); return charger();
      }
      render();
    });
  }
  lireAdresse();
  render();
  charger();
})();
