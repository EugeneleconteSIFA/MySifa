/* Parametres > Fabrication > Impression — couleurs d'encre des BAT.
 *
 * Fichier autonome : la page settings n'y accroche que initEncresPanel()
 * (setTab) et le panneau #panel-encres. API : /api/encres (app/routers/encres.py).
 *
 * Deux vues : le referentiel (ce qui est saisi) et les designations reellement
 * presentes dans les fiches, avec la teinte que le BAT leur donne aujourd'hui.
 * La seconde est la liste de travail : une designation sans teinte tombe sur
 * le violet neutre du BAT, et un clic sur « Ajouter » pre-remplit le code.
 */
(function () {
  'use strict';

  var S = { encres: [], saisies: [], editId: null, pret: false, sub: 'ref', testTimer: null,
            filtre: '', filtreTimer: null };

  function correspond(champs) {
    if (!S.filtre) return true;
    var f = S.filtre;
    return champs.some(function (v) { return String(v == null ? '' : v).toLowerCase().indexOf(f) >= 0; });
  }
  function encresVisibles() {
    return S.encres.filter(function (r) { return correspond([r.cle, r.code, r.libelle, r.hex]); });
  }
  function saisiesVisibles() {
    return S.saisies.filter(function (r) {
      var src = r.source === 'referentiel' ? 'référentiel' : (r.source === 'nom' ? 'nom simple' : 'sans teinte');
      return correspond([r.designation, r.cle_proposee, r.hex, src]);
    });
  }
  function majCompte() {
    var out = el('enc-compte');
    if (!out) return;
    var tot = S.sub === 'ref' ? S.encres.length : S.saisies.length;
    var vis = S.sub === 'ref' ? encresVisibles().length : saisiesVisibles().length;
    out.textContent = (vis === tot ? tot : vis + ' / ' + tot) + (S.sub === 'ref' ? ' couleur(s)' : ' désignation(s)');
  }

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function el(id) { return document.getElementById(id); }
  function notifier(msg, err) {
    if (typeof window.toast === 'function') window.toast(msg, err);
    else if (err) window.alert(msg);
  }
  async function appel(path, opt) {
    var r = await fetch(path, Object.assign({ credentials: 'include' }, opt || {}));
    var j = await r.json().catch(function () { return {}; });
    if (!r.ok) throw new Error(j.detail || ('Erreur ' + r.status));
    return j;
  }
  function hexValide(v) { return /^#[0-9A-Fa-f]{6}$/.test(String(v || '').trim()); }
  function pastille(hex, taille) {
    var t = taille || 18;
    if (!hex) {
      return '<span style="display:inline-block;width:' + t + 'px;height:' + t + 'px;border-radius:5px;'
        + 'border:1px dashed var(--muted);vertical-align:middle"></span>';
    }
    return '<span style="display:inline-block;width:' + t + 'px;height:' + t + 'px;border-radius:5px;'
      + 'border:1px solid var(--border);vertical-align:middle;background:' + esc(hex) + '"></span>';
  }
  function sourceTxt(src) {
    if (src === 'referentiel') return 'Référentiel';
    if (src === 'nom') return '<span style="color:var(--muted)">Nom simple</span>';
    return '<span style="color:var(--warn)">Sans teinte</span>';
  }

  /* ── Chargement ─────────────────────────────────────────── */
  async function charger() {
    try {
      var d = await appel('/api/encres');
      S.encres = d.encres || [];
      rendreListe();
    } catch (e) {
      el('enc-list').innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
    }
    chargerSaisies();
  }

  async function chargerSaisies() {
    try {
      var d = await appel('/api/encres/a-rapprocher');
      S.saisies = d.lignes || [];
      var badge = el('enc-sans-teinte');
      if (badge) badge.textContent = d.sans_teinte ? '· ' + d.sans_teinte + ' sans teinte' : '';
      rendreSaisies();
    } catch (e) {
      el('enc-saisies').innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
    }
  }

  /* ── Rendu ──────────────────────────────────────────────── */
  function rendreListe() {
    var box = el('enc-list');
    if (!box) return;
    majCompte();
    if (!S.encres.length) {
      box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune couleur. Le BAT ne reconnaît que les noms simples (noir, jaune…).</p>';
      return;
    }
    var liste = encresVisibles();
    if (!liste.length) {
      box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune couleur ne correspond au filtre.</p>';
      return;
    }
    var rows = liste.map(function (r) {
      return '<tr' + (r.actif ? '' : ' style="opacity:.5"') + '>'
        + '<td>' + pastille(r.hex) + '</td>'
        + '<td><b>' + esc(r.cle) + '</b>'
        + (r.code !== r.cle ? '<div style="font-size:11px;color:var(--muted)">saisi : ' + esc(r.code) + '</div>' : '')
        + '</td>'
        + '<td>' + (r.libelle ? esc(r.libelle) : '<span style="color:var(--muted)">—</span>') + '</td>'
        + '<td style="font-family:monospace">' + esc(r.hex) + '</td>'
        + '<td>' + (r.actif ? 'Active' : 'Inactive') + '</td>'
        + '<td><div class="op-act">'
        + '<button type="button" class="btn-sm btn-ghost" onclick="encOpenForm(' + r.id + ')">Modifier</button>'
        + '<button type="button" class="btn-sm btn-ghost danger" onclick="encDelete(' + r.id + ')">Supprimer</button>'
        + '</div></td></tr>';
    }).join('');
    box.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
      + '<th></th><th>Code</th><th>Libellé</th><th>Teinte</th><th>État</th><th>Actions</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function rendreSaisies() {
    var box = el('enc-saisies');
    if (!box) return;
    majCompte();
    if (!S.saisies.length) {
      box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune désignation d\'encre dans les fiches.</p>';
      return;
    }
    var liste = saisiesVisibles();
    if (!liste.length) {
      box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune désignation ne correspond au filtre.</p>';
      return;
    }
    var rows = liste.map(function (r) {
      var i = S.saisies.indexOf(r);
      var action = r.source === 'referentiel' ? ''
        : '<button type="button" class="btn-sm btn-ghost" onclick="encAddFrom(' + i + ')">Ajouter</button>';
      return '<tr>'
        + '<td>' + pastille(r.hex) + '</td>'
        + '<td><b>' + esc(r.designation) + '</b></td>'
        + '<td style="color:var(--muted)">' + esc(r.cle_proposee) + '</td>'
        + '<td>' + r.occurrences + '</td>'
        + '<td>' + sourceTxt(r.source) + '</td>'
        + '<td><div class="op-act">' + action + '</div></td></tr>';
    }).join('');
    box.innerHTML = '<p class="sub" style="margin:0 0 10px">Désignations présentes dans les fiches techniques et les fiches MyAO. '
      + '« Nom simple » : teinte générique trouvée dans le nom (rouge, bleu…), à préciser si besoin.</p>'
      + '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
      + '<th></th><th>Désignation</th><th>Clé</th><th>Fiches</th><th>Teinte</th><th>Actions</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  /* ── Formulaire ─────────────────────────────────────────── */
  function syncHex(depuis) {
    var pick = el('enc-picker'), txt = el('enc-hex');
    if (depuis === 'picker') txt.value = pick.value.toUpperCase();
    else if (hexValide(txt.value)) pick.value = txt.value.trim();
  }

  var cleTimer = null;
  function apercuCle() {
    clearTimeout(cleTimer);
    cleTimer = setTimeout(async function () {
      var v = el('enc-code').value.trim();
      var out = el('enc-cle');
      if (!v) { out.textContent = ''; return; }
      try {
        var d = await appel('/api/encres/tester?designation=' + encodeURIComponent(v));
        out.textContent = d.cles && d.cles.length ? 'Code rapproché sous : ' + d.cles[0] : '';
      } catch (e) { out.textContent = ''; }
    }, 250);
  }

  function ouvrir(id, preset) {
    S.editId = id || null;
    var r = id ? S.encres.find(function (x) { return x.id === id; }) : null;
    var p = preset || {};
    el('enc-form-title').textContent = r ? 'Modifier la couleur' : 'Nouvelle couleur';
    el('enc-code').value = r ? r.code : (p.code || '');
    el('enc-libelle').value = r ? (r.libelle || '') : (p.libelle || '');
    el('enc-hex').value = r ? r.hex : (p.hex || '');
    el('enc-picker').value = hexValide(el('enc-hex').value) ? el('enc-hex').value : '#888888';
    el('enc-actif').checked = r ? !!r.actif : true;
    el('enc-form-wrap').classList.remove('hidden');
    apercuCle();
    el('enc-code').focus();
  }

  function fermer() {
    S.editId = null;
    el('enc-form-wrap').classList.add('hidden');
  }

  async function enregistrer() {
    var body = {
      code: el('enc-code').value.trim(),
      libelle: el('enc-libelle').value.trim() || null,
      hex: el('enc-hex').value.trim(),
      actif: el('enc-actif').checked,
    };
    if (!body.code) { notifier('Code manquant — ex. 485 C.', true); return; }
    if (!hexValide(body.hex)) { notifier('Teinte invalide — format #RRGGBB.', true); return; }
    try {
      var path = S.editId ? '/api/encres/' + S.editId : '/api/encres';
      await appel(path, {
        method: S.editId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      notifier('Couleur enregistrée.');
      fermer();
      charger();
    } catch (e) { notifier(e.message, true); }
  }

  async function supprimer(id) {
    var r = S.encres.find(function (x) { return x.id === id; });
    if (!window.confirm('Supprimer la couleur ' + (r ? r.cle : '') + ' ? Les BAT concernés retomberont sur la teinte neutre.')) return;
    try {
      await appel('/api/encres/' + id, { method: 'DELETE' });
      notifier('Couleur supprimée.');
      charger();
    } catch (e) { notifier(e.message, true); }
  }

  /* ── Test d'une désignation ─────────────────────────────── */
  function tester() {
    clearTimeout(S.testTimer);
    S.testTimer = setTimeout(async function () {
      var v = el('enc-test').value.trim();
      var out = el('enc-test-out');
      if (!v) { out.innerHTML = ''; return; }
      try {
        var d = await appel('/api/encres/tester?designation=' + encodeURIComponent(v));
        var cle = d.cles && d.cles.length ? ' · clé ' + esc(d.cles[0]) : '';
        out.innerHTML = pastille(d.hex, 16) + ' '
          + (d.hex ? '<span style="font-family:monospace;color:var(--text)">' + esc(d.hex) + '</span> · ' : '')
          + sourceTxt(d.source) + cle;
      } catch (e) { out.textContent = e.message; }
    }, 250);
  }

  function setSub(sub) {
    S.sub = sub === 'saisies' ? 'saisies' : 'ref';
    document.querySelectorAll('[data-encsub]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.encsub === S.sub);
    });
    el('enc-list').classList.toggle('hidden', S.sub !== 'ref');
    el('enc-saisies').classList.toggle('hidden', S.sub !== 'saisies');
    majCompte();
  }

  /* ── Export CSV de la vue affichee ─────────────────────── */
  // Point-virgule et BOM UTF-8 : Excel en francais ouvre le fichier sans
  // assistant d'import et garde les accents.
  function cellule(v) {
    var t = String(v == null ? '' : v);
    return /[";\n\r]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
  }
  function exporter() {
    var entetes, lignes, nom;
    if (S.sub === 'ref') {
      entetes = ['Cle', 'Code saisi', 'Libelle', 'Teinte', 'Etat', 'Modifie le', 'Par'];
      lignes = encresVisibles().map(function (r) {
        return [r.cle, r.code, r.libelle || '', r.hex, r.actif ? 'Active' : 'Inactive',
                (r.updated_at || '').replace('T', ' ').slice(0, 16), r.updated_by || ''];
      });
      nom = 'encres_referentiel';
    } else {
      entetes = ['Designation', 'Cle', 'Fiches', 'Teinte', 'Origine de la teinte'];
      lignes = saisiesVisibles().map(function (r) {
        var src = r.source === 'referentiel' ? 'Referentiel' : (r.source === 'nom' ? 'Nom simple' : 'Sans teinte');
        return [r.designation, r.cle_proposee, r.occurrences, r.hex || '', src];
      });
      nom = 'encres_designations_saisies';
    }
    if (!lignes.length) { notifier('Rien à exporter.', true); return; }
    var csv = '\ufeff' + [entetes].concat(lignes).map(function (l) {
      return l.map(cellule).join(';');
    }).join('\r\n');
    var d = new Date();
    var jour = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    var url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    var a = document.createElement('a');
    a.href = url;
    a.download = nom + '_' + jour + '.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    notifier(lignes.length + ' ligne(s) exportée(s).');
  }

  /* ── Points d'entree ────────────────────────────────────── */
  window.initEncresPanel = function () {
    if (!S.pret) {
      S.pret = true;
      el('enc-picker').addEventListener('input', function () { syncHex('picker'); });
      el('enc-hex').addEventListener('input', function () { syncHex('texte'); });
      el('enc-code').addEventListener('input', apercuCle);
      el('enc-test').addEventListener('input', tester);
      el('enc-filtre').addEventListener('input', function () {
        clearTimeout(S.filtreTimer);
        S.filtreTimer = setTimeout(function () {
          S.filtre = el('enc-filtre').value.trim().toLowerCase();
          rendreListe();
          rendreSaisies();
        }, 150);
      });
    }
    charger();
  };
  window.encOpenForm = function (id) { ouvrir(id); };
  window.encCloseForm = fermer;
  window.encSaveForm = enregistrer;
  window.encDelete = supprimer;
  window.encSetSub = setSub;
  window.encExport = exporter;
  window.encAddFrom = function (i) {
    var r = S.saisies[i];
    if (!r) return;
    setSub('ref');
    ouvrir(null, { code: r.cle_proposee || r.designation, hex: r.hex || '' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
})();
