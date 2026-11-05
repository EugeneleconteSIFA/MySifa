/* Paramètres › Communication › Types de réunion.
   Référentiel de l'espace Réunions (table reunion_types) : la logique lit les
   attributs d'un type, jamais son libellé.
   Données : GET  /api/reunions/types/admin
             POST /api/reunions/types/admin            (création)
             PUT  /api/reunions/types/admin/{id}       (modification)
             DELETE /api/reunions/types/admin/{id}     (supprimé si inutilisé, désactivé sinon)
   Accès : section « communication » (direction, superadmin), revérifié par l'API. */
(function () {
  'use strict';

  var API = '/api/reunions/types/admin';
  var S = { data: null, edition: null };   // edition : id en cours de modification, ou 'nouveau'

  function req(path, opt) {
    return fetch(API + path, Object.assign({ credentials: 'include', headers: { 'Content-Type': 'application/json' } }, opt || {}))
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error((j && j.detail) || ('Erreur ' + r.status));
          return j;
        });
      });
  }
  function toastMsg(msg, err) {
    if (typeof window.toast === 'function') window.toast(msg, err);
  }
  function el(tag, attrs) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') e.textContent = v;
      else if (k === 'style') e.style.cssText = v;
      else if (k.slice(0, 2) === 'on') e.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'value') e.value = v;
      else if (k === 'checked') e.checked = !!v;
      else e.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c === null || c === undefined || c === false) continue;
      e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return e;
  }

  var BTN = 'border-radius:10px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;';
  var BTN_CARD = BTN + 'background:var(--bg);border:1px solid var(--border);color:var(--text)';
  var BTN_ACCENT = BTN + 'background:var(--accent);border:1px solid var(--accent);color:white';
  var BTN_DANGER = BTN + 'background:var(--danger);border:1px solid var(--danger);color:white';
  var CHAMP = 'background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit';
  var CARTE = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-bottom:10px';

  function libelleRoles(codes) {
    var R = {};
    ((S.data && S.data.roles) || []).forEach(function (r) { R[r.code] = r.libelle; });
    return (codes || []).map(function (c) { return R[c] || c; }).join(', ');
  }
  function resumeType(t) {
    var V = (S.data && S.data.visibilites) || {};
    var vis = t.visibilite_defaut === 'roles' ? 'Rôles : ' + libelleRoles(t.roles_defaut) : (V[t.visibilite_defaut] || t.visibilite_defaut);
    return [
      'Visible : ' + vis,
      t.structuration_ia ? 'brief proposé par l’IA' : 'sans IA (transcription seule)',
      t.chiffres_prod ? 'chiffres de production' : '',
      t.nb_reunions + ' réunion(s)'
    ].filter(Boolean).join(' · ');
  }

  function formulaire(t, racine) {
    var d = {
      libelle: t ? t.libelle : '',
      ordre: t ? t.ordre : ((S.data.types || []).length + 1),
      actif: t ? t.actif : true,
      visibilite_defaut: t ? t.visibilite_defaut : 'participants',
      roles_defaut: t ? t.roles_defaut.slice() : [],
      structuration_ia: t ? t.structuration_ia : true,
      chiffres_prod: t ? t.chiffres_prod : false
    };
    var V = S.data.visibilites || {};
    var vis = el('select', { style: CHAMP, onChange: function () { d.visibilite_defaut = vis.value; boiteRoles.style.display = vis.value === 'roles' ? '' : 'none'; } });
    Object.keys(V).forEach(function (k) { vis.appendChild(el('option', { value: k, text: V[k] })); });
    vis.value = d.visibilite_defaut;
    var boiteRoles = el('div', { style: 'display:flex;gap:10px;flex-wrap:wrap;margin-top:8px' });
    (S.data.roles || []).forEach(function (r) {
      if (r.code === 'superadmin') return;
      var c = el('input', { type: 'checkbox', checked: d.roles_defaut.indexOf(r.code) >= 0, onChange: function () {
        d.roles_defaut = d.roles_defaut.filter(function (x) { return x !== r.code; });
        if (c.checked) d.roles_defaut.push(r.code);
      } });
      boiteRoles.appendChild(el('label', { style: 'display:inline-flex;gap:6px;align-items:center;font-size:12px;color:var(--text2)' }, c, r.libelle));
    });
    boiteRoles.style.display = d.visibilite_defaut === 'roles' ? '' : 'none';
    var caseOpt = function (cle, libelle, aide) {
      var c = el('input', { type: 'checkbox', checked: d[cle], onChange: function () { d[cle] = c.checked; } });
      return el('label', { style: 'display:flex;gap:8px;align-items:flex-start;font-size:13px;margin-top:10px;color:var(--text)' },
        c, el('span', null, libelle, el('span', { style: 'display:block;font-size:12px;color:var(--muted)', text: aide })));
    };
    var lab = function (t) { return el('div', { style: 'font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:12px 0 6px', text: t }); };
    var enregistrer = function () {
      if (!d.libelle.trim()) { toastMsg('Libellé obligatoire.', true); return; }
      var p = t ? req('/' + t.id, { method: 'PUT', body: JSON.stringify(d) }) : req('', { method: 'POST', body: JSON.stringify(d) });
      p.then(function () { toastMsg(t ? 'Type enregistré.' : 'Type créé.'); S.edition = null; charger(); })
        .catch(function (e) { toastMsg(e.message, true); });
    };
    return el('div', { style: CARTE + ';border-color:var(--accent)' },
      el('div', { style: 'display:grid;grid-template-columns:minmax(0,1fr) 110px;gap:10px' },
        el('div', null, lab('Libellé'), el('input', { type: 'text', value: d.libelle, style: CHAMP + ';width:100%', onInput: function (ev) { d.libelle = ev.target.value; } })),
        el('div', null, lab('Ordre'), el('input', { type: 'number', value: d.ordre, style: CHAMP + ';width:100%', onInput: function (ev) { d.ordre = ev.target.value; } }))),
      lab('Visible par défaut'), vis, boiteRoles,
      el('div', { style: 'font-size:12px;color:var(--muted);margin-top:6px', text: 'Le créateur et les participants voient toujours leurs réunions.' }),
      caseOpt('structuration_ia', 'Compte-rendu proposé par l’IA', 'Le texte de la transcription est envoyé à Claude pour proposer notes, décisions et actions. Décoché : transcription seule, rien ne quitte le serveur.'),
      caseOpt('chiffres_prod', 'Chiffres de production', 'La réunion porte sur une plage de dates et des machines (points de production de MyProd).'),
      caseOpt('actif', 'Actif', 'Un type inactif n’est plus proposé ; ses réunions restent.'),
      el('div', { style: 'display:flex;gap:8px;justify-content:flex-end;margin-top:14px;flex-wrap:wrap' },
        el('button', { type: 'button', style: BTN_CARD, text: 'Annuler', onClick: function () { S.edition = null; rendre(racine); } }),
        el('button', { type: 'button', style: BTN_ACCENT, text: 'Enregistrer', onClick: enregistrer })));
  }

  function rendre(racine) {
    racine.innerHTML = '';
    if (!S.data) { racine.appendChild(el('div', { style: 'color:var(--muted);font-size:13px', text: 'Chargement…' })); return; }
    (S.data.types || []).forEach(function (t) {
      if (S.edition === t.id) { racine.appendChild(formulaire(t, racine)); return; }
      racine.appendChild(el('div', { style: CARTE + ';display:flex;gap:12px;align-items:center;flex-wrap:wrap' + (t.actif ? '' : ';opacity:.6') },
        el('div', { style: 'flex:1;min-width:220px' },
          el('div', { style: 'font-size:14px;font-weight:700;color:var(--text)', text: t.libelle + (t.actif ? '' : ' (inactif)') }),
          el('div', { style: 'font-size:12px;color:var(--muted);margin-top:3px', text: resumeType(t) })),
        el('button', { type: 'button', style: BTN_CARD, text: 'Modifier', onClick: function () { S.edition = t.id; rendre(racine); } }),
        el('button', { type: 'button', style: BTN_DANGER, text: t.nb_reunions ? 'Désactiver' : 'Supprimer', onClick: function () {
          var msg = t.nb_reunions ? 'Désactiver « ' + t.libelle + ' » ? Ses ' + t.nb_reunions + ' réunion(s) restent.' : 'Supprimer « ' + t.libelle + ' » ?';
          if (!window.confirm(msg)) return;
          req('/' + t.id, { method: 'DELETE' })
            .then(function (r) { toastMsg(r.resultat === 'supprime' ? 'Type supprimé.' : 'Type désactivé.'); charger(); })
            .catch(function (e) { toastMsg(e.message, true); });
        } })));
    });
    if (S.edition === 'nouveau') racine.appendChild(formulaire(null, racine));
    else racine.appendChild(el('button', { type: 'button', style: BTN_CARD, text: '+ Ajouter un type', onClick: function () { S.edition = 'nouveau'; rendre(racine); } }));
  }

  function charger() {
    var racine = document.getElementById('reuniontypes-root');
    if (!racine) return;
    req('').then(function (d) { S.data = d; rendre(racine); })
      .catch(function (e) { racine.textContent = 'Chargement impossible — ' + e.message + '.'; });
  }

  window.initReunionTypesPanel = function () {
    var racine = document.getElementById('reuniontypes-root');
    if (!racine) return;
    rendre(racine);
    charger();
  };
})();
