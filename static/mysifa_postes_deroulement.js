/* Paramètres › Machines › Postes de déroulement.
 *
 * Deux choses sur un même écran, parce qu'elles répondent à la même question
 * — « sur quel poste va la bobine qu'on vient de scanner ? » :
 *
 *   1. les postes de la machine choisie et leur nombre de places ;
 *   2. la reconnaissance des bobines : ce qui l'empêche d'être automatique
 *      (fournisseurs ambigus, fournisseurs sans catégorie) et les règles de
 *      préfixe par fournisseur qui la débloquent.
 *
 * API : app/routers/bobines_montees.py.
 */
(function () {
  'use strict';

  var LABEL_CAT = { frontal: 'Frontal', complexe: 'Complexe', glassine: 'Glassine' };
  var etat = { data: null, machineId: null, el: null };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function notifier(msg, err) {
    if (typeof window.toast === 'function') return window.toast(msg, err);
    if (typeof window.showToast === 'function') return window.showToast(msg, err ? 'danger' : 'success');
  }
  async function appel(path, opt) {
    var r = await fetch(path, Object.assign({ credentials: 'include' }, opt || {}));
    var j = {};
    try { j = await r.json(); } catch (e) { j = {}; }
    if (!r.ok) {
      var d = j.detail;
      throw new Error((d && typeof d === 'object') ? (d.message || JSON.stringify(d)) : (d || ('Erreur ' + r.status)));
    }
    return j;
  }
  function json(method, body) {
    return { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  }

  var S_CARTE = 'background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:14px';
  var S_TITRE = 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 10px';
  var S_CHAMP = 'background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px 10px;color:var(--text);font:inherit;font-size:13px';
  var S_BTN2 = 'background:var(--card);border:1px solid var(--border);border-radius:10px;padding:7px 12px;color:var(--text);font:inherit;font-size:12px;font-weight:700;cursor:pointer';

  function machine() {
    var d = etat.data;
    if (!d) return null;
    return d.machines.filter(function (m) { return String(m.id) === String(etat.machineId); })[0] || null;
  }

  function blocPostes() {
    var m = machine();
    if (!m) return '<p class="sub">Machine introuvable ou inactive.</p>';
    var d = etat.data;
    var lignes = d.postes.map(function (p) {
      var cfg = m.postes.filter(function (x) { return x.poste === p.code; })[0] || { places: 0 };
      var cats = p.categories.map(function (c) { return LABEL_CAT[c] || c; }).join(', ');
      return '<tr>' +
        '<td style="padding:8px 10px;font-weight:700">' + esc(p.label) + '</td>' +
        '<td style="padding:8px 10px;color:var(--muted);font-size:12px">' + esc(cats) + '</td>' +
        '<td style="padding:8px 10px"><input type="number" min="0" max="' + d.places_max + '" step="1" ' +
        'class="mpd-places" data-poste="' + esc(p.code) + '" value="' + esc(cfg.places) + '" ' +
        'style="' + S_CHAMP + ';width:80px"></td>' +
        '</tr>';
    }).join('');
    var avert = m.sans_matiere_premiere
      ? '<p class="sub" style="font-size:12px;margin:0 0 10px">Poste marqué « sans matière première » : laissez 0 place, aucune bobine n’y est suivie.</p>'
      : '';
    return '<div style="' + S_CARTE + '">' +
      '<h4 style="' + S_TITRE + '">Postes de ' + esc(m.nom) + '</h4>' +
      '<p class="sub" style="font-size:12px;margin:0 0 10px">Nombre de bobines qu’un poste porte en même temps (celle qui roule et celle qui prend le relais). ' +
      'Scanner une bobine sur un poste plein démonte la plus ancienne. 0 place = pas de poste.</p>' + avert +
      '<div style="overflow-x:auto"><table style="border-collapse:collapse;font-size:13px;min-width:360px">' +
      '<thead><tr style="color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.5px">' +
      '<th style="text-align:left;padding:4px 10px">Poste</th><th style="text-align:left;padding:4px 10px">Accepte</th>' +
      '<th style="text-align:left;padding:4px 10px">Places</th></tr></thead><tbody>' + lignes + '</tbody></table></div>' +
      '<button type="button" class="btn" id="mpd-save-postes" style="margin-top:12px">Enregistrer les postes</button>' +
      '</div>';
  }

  function blocDiagnostic() {
    var dg = etat.data.diagnostic || {};
    var morceaux = [];
    if ((dg.ambigus || []).length) {
      morceaux.push('<div style="margin-bottom:8px"><strong style="color:var(--warn)">À départager</strong> — ces fiches désignent les deux postes et n’ont aucune règle : ' +
        dg.ambigus.map(function (f) {
          return esc(f.nom) + ' <span style="color:var(--muted)">(' + esc(f.categories.join(', ')) + ')</span>';
        }).join(' · ') +
        '. Ajoutez une règle de préfixe, ou corrigez les catégories dans Fournisseurs.</div>');
    }
    if ((dg.sans_categorie || []).length) {
      morceaux.push('<div><strong style="color:var(--warn)">Sans catégorie de bobine</strong> — déjà scannés, mais leur fiche ne dit pas frontal, complexe ou glassine : ' +
        dg.sans_categorie.map(function (f) {
          return esc(f.nom) + ' <span style="color:var(--muted)">(' + f.scans + ' scan' + (f.scans > 1 ? 's' : '') + ')</span>';
        }).join(' · ') + '.</div>');
    }
    if (!morceaux.length) {
      morceaux.push('<div style="color:var(--success);font-weight:700">Chaque fournisseur de bobines désigne un seul poste, ou a sa règle.</div>');
    }
    return '<div style="' + S_CARTE + ';font-size:13px;line-height:1.5">' +
      '<h4 style="' + S_TITRE + '">Reconnaissance des bobines</h4>' + morceaux.join('') + '</div>';
  }

  function blocRegles() {
    var d = etat.data;
    var lignes = d.regles.map(function (r) {
      return '<tr style="border-top:1px solid var(--border)">' +
        '<td style="padding:8px 10px;font-weight:700">' + esc(r.fournisseur || ('#' + r.fournisseur_id)) + '</td>' +
        '<td style="padding:8px 10px;font-family:ui-monospace,monospace">' +
        (r.motif ? esc(r.motif) + '…' : '<span style="color:var(--muted);font-family:inherit">tout autre code</span>') + '</td>' +
        '<td style="padding:8px 10px">' + esc(LABEL_CAT[r.categorie] || r.categorie) + '</td>' +
        '<td style="padding:8px 10px;color:var(--muted)">' + esc(r.note || '') + '</td>' +
        '<td style="padding:8px 10px;text-align:right;white-space:nowrap">' +
        '<button type="button" class="mpd-toggle" data-id="' + r.id + '" data-actif="' + (r.actif ? 1 : 0) + '" style="' + S_BTN2 + '">' +
        (r.actif ? 'Désactiver' : 'Activer') + '</button> ' +
        '<button type="button" class="mpd-suppr" data-id="' + r.id + '" style="' + S_BTN2 + ';color:var(--danger)">Supprimer</button>' +
        '</td></tr>';
    }).join('');
    var bobineFirst = d.fournisseurs.slice().sort(function (a, b) {
      var ab = a.categories.some(function (c) { return LABEL_CAT[c]; }) ? 0 : 1;
      var bb = b.categories.some(function (c) { return LABEL_CAT[c]; }) ? 0 : 1;
      return ab - bb || String(a.nom).localeCompare(String(b.nom), 'fr');
    });
    var opts = bobineFirst.map(function (f) {
      return '<option value="' + f.id + '">' + esc(f.nom) + '</option>';
    }).join('');
    var cats = d.categories.map(function (c) {
      return '<option value="' + c + '">' + esc(LABEL_CAT[c] || c) + '</option>';
    }).join('');
    return '<div style="' + S_CARTE + '">' +
      '<h4 style="' + S_TITRE + '">Règles de préfixe par fournisseur</h4>' +
      '<p class="sub" style="font-size:12px;margin:0 0 10px">Pour un fournisseur qui livre plusieurs natures : le début du code-barres qui désigne chacune. ' +
      'Le préfixe le plus long gagne ; un préfixe vide vaut « tout autre code ».</p>' +
      (lignes
        ? '<div style="overflow-x:auto"><table style="border-collapse:collapse;font-size:13px;width:100%;min-width:560px">' +
          '<thead><tr style="color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.5px">' +
          '<th style="text-align:left;padding:4px 10px">Fournisseur</th><th style="text-align:left;padding:4px 10px">Préfixe</th>' +
          '<th style="text-align:left;padding:4px 10px">Nature</th><th style="text-align:left;padding:4px 10px">Note</th><th></th></tr></thead>' +
          '<tbody>' + lignes + '</tbody></table></div>'
        : '<p class="sub" style="font-size:12px">Aucune règle.</p>') +
      '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end;margin-top:12px">' +
      '<label style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px">Fournisseur' +
      '<select id="mpd-r-fourn" style="' + S_CHAMP + ';min-width:180px">' + opts + '</select></label>' +
      '<label style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px">Préfixe' +
      '<input id="mpd-r-motif" maxlength="20" placeholder="Ex. G (vide = tout autre code)" style="' + S_CHAMP + ';width:200px;font-family:ui-monospace,monospace"></label>' +
      '<label style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px">Nature' +
      '<select id="mpd-r-cat" style="' + S_CHAMP + '">' + cats + '</select></label>' +
      '<label style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px;flex:1;min-width:160px">Note' +
      '<input id="mpd-r-note" maxlength="200" style="' + S_CHAMP + '"></label>' +
      '<button type="button" class="btn" id="mpd-r-add">Ajouter la règle</button>' +
      '</div></div>' +
      '<div style="' + S_CARTE + ';display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between">' +
      '<span class="sub" style="font-size:12px;max-width:620px">Après avoir corrigé une fiche fournisseur ou ajouté une règle : réapprendre la nature des formes de code depuis les scans passés.</span>' +
      '<button type="button" id="mpd-reconstruire" style="' + S_BTN2 + '">Réapprendre depuis l’historique</button>' +
      '</div>';
  }

  function peindre() {
    if (!etat.el) return;
    if (!etat.data) { etat.el.innerHTML = '<p class="sub">Chargement…</p>'; return; }
    etat.el.innerHTML = blocPostes() + blocDiagnostic() + blocRegles();
    brancher();
  }

  function brancher() {
    var el = etat.el;
    var save = el.querySelector('#mpd-save-postes');
    if (save) save.addEventListener('click', async function () {
      var postes = [].map.call(el.querySelectorAll('.mpd-places'), function (i) {
        var n = parseInt(i.value, 10);
        return { poste: i.getAttribute('data-poste'), places: isNaN(n) ? 0 : n, actif: 1 };
      });
      try {
        await appel('/api/settings/machines/' + etat.machineId + '/postes-deroulement', json('PUT', { postes: postes }));
        notifier('Postes enregistrés.');
        await charger();
      } catch (e) { notifier(e.message, true); }
    });
    var add = el.querySelector('#mpd-r-add');
    if (add) add.addEventListener('click', async function () {
      try {
        await appel('/api/settings/regles-code', json('POST', {
          fournisseur_id: parseInt(el.querySelector('#mpd-r-fourn').value, 10),
          motif: el.querySelector('#mpd-r-motif').value,
          categorie: el.querySelector('#mpd-r-cat').value,
          note: el.querySelector('#mpd-r-note').value,
        }));
        notifier('Règle ajoutée.');
        await charger();
      } catch (e) { notifier(e.message, true); }
    });
    [].forEach.call(el.querySelectorAll('.mpd-suppr'), function (b) {
      b.addEventListener('click', async function () {
        try {
          await appel('/api/settings/regles-code/' + b.getAttribute('data-id'), { method: 'DELETE' });
          notifier('Règle supprimée.');
          await charger();
        } catch (e) { notifier(e.message, true); }
      });
    });
    [].forEach.call(el.querySelectorAll('.mpd-toggle'), function (b) {
      b.addEventListener('click', async function () {
        var r = etat.data.regles.filter(function (x) { return String(x.id) === b.getAttribute('data-id'); })[0];
        if (!r) return;
        try {
          await appel('/api/settings/regles-code/' + r.id, json('PUT', {
            fournisseur_id: r.fournisseur_id, motif: r.motif, categorie: r.categorie,
            note: r.note, actif: r.actif ? 0 : 1,
          }));
          await charger();
        } catch (e) { notifier(e.message, true); }
      });
    });
    var rec = el.querySelector('#mpd-reconstruire');
    if (rec) rec.addEventListener('click', async function () {
      rec.disabled = true;
      try {
        var r = await appel('/api/settings/postes-deroulement/reconstruire', { method: 'POST' });
        notifier(r.apprises + ' scan(s) appris sur ' + r.scans + '.');
        await charger();
      } catch (e) { notifier(e.message, true); }
      finally { rec.disabled = false; }
    });
  }

  async function charger() {
    try {
      etat.data = await appel('/api/settings/postes-deroulement');
    } catch (e) {
      etat.data = null;
      if (etat.el) etat.el.innerHTML = '<p class="sub">' + esc(e.message) + '</p>';
      return;
    }
    peindre();
  }

  window.MysPostesDeroulement = {
    render: function (el, machineId) {
      etat.el = el;
      etat.machineId = machineId;
      if (etat.data) peindre();
      charger();
    },
  };
})();
