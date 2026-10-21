/* Réglages des notes de frais : catégories proposées aux salariés.
 *
 * Coffre RH (/rh/coffre) › Notes de frais, bouton « Réglages ». Les salariés
 * n'y ont pas accès : Mon coffre ne fait que lire les catégories actives, et
 * l'API /api/rh-coffre/ndf-categories refuse les autres rôles que la
 * comptabilité et le superadmin.
 *
 * La fenêtre travaille sur une copie de la liste : renommer, changer la TVA
 * ou le taux kilométrique, réordonner, supprimer, ajouter. Rien ne part avant
 * « Enregistrer », qui envoie la liste entière en une fois (PUT). Une
 * catégorie supprimée est désactivée côté serveur : les notes qui la portent
 * gardent leur libellé.
 *
 * Les taux de TVA proposés ne se règlent pas ici : ce sont les taux légaux,
 * NDF_TAUX_TVA de config.py.
 *
 * Adresse : la page la tient (static/rh_coffre_url.js écrit ?reglages=ndf
 * tant que estOuvert()). ouvrir({surAdresse}) la prévient à l'ouverture et à
 * la fermeture ; fermer(true) ferme sans la prévenir (Retour du navigateur).
 */
(function () {
  'use strict';

  var API = '/api/rh-coffre/ndf-categories';
  var etat = { liste: [], taux: [20, 10, 5.5, 0], modifie: false, back: null, surChange: null, surAdresse: null };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmtTaux(t) { return t ? String(t).replace('.', ',') + ' %' : 'Sans TVA'; }
  function message(msg, type) {
    if (typeof window.toast === 'function') window.toast(msg, type);
  }
  async function api(url, opts) {
    opts = opts || {};
    opts.credentials = 'include';
    if (opts.body) opts.headers = { 'Content-Type': 'application/json' };
    var r = await fetch(url, opts);
    if (!r.ok) {
      var m = 'Erreur';
      try { var j = await r.json(); m = j.detail || m; } catch (e) {}
      throw new Error(m);
    }
    return r.json();
  }
  function prevenirAdresse() {
    if (typeof etat.surAdresse === 'function') { try { etat.surAdresse(); } catch (e) {} }
  }

  function injecterStyle() {
    if (document.getElementById('nr-style')) return;
    var st = document.createElement('style');
    st.id = 'nr-style';
    st.textContent = [
      '.nr-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:450;display:flex;align-items:center;justify-content:center;padding:16px}',
      '.nr-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:760px;width:100%;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.35);color:var(--text)}',
      '.nr-head{display:flex;align-items:center;gap:12px;padding:18px 22px 14px;border-bottom:1px solid var(--border)}',
      '.nr-head h3{margin:0;font-size:16px;font-weight:700}',
      '.nr-sub{font-size:12px;color:var(--muted);margin-top:2px}',
      '.nr-close{margin-left:auto;width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text2);cursor:pointer;font-size:18px;line-height:1;font-family:inherit}',
      '.nr-close:hover{background:var(--card);color:var(--accent);border-color:var(--accent)}',
      '.nr-body{padding:16px 22px;overflow:auto}',
      '.nr-modal input,.nr-modal select{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 10px;color:var(--text);font-size:13px;font-family:inherit;outline:none;min-height:36px;box-sizing:border-box}',
      '.nr-modal input:focus,.nr-modal select:focus{border-color:var(--accent)}',
      '.nr-table{width:100%;border-collapse:collapse;font-size:13px}',
      '.nr-table th{text-align:left;padding:8px 6px;color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}',
      '.nr-table td{padding:8px 6px;border-bottom:1px solid var(--border);vertical-align:middle}',
      '.nr-table input[data-f=libelle]{width:100%;min-width:140px}',
      '.nr-table select[data-f=taux_tva],.nr-table select[data-f=saisie]{width:120px}',
      '.nr-km{display:inline-flex;align-items:center;gap:6px;color:var(--text2)}',
      '.nr-km input{width:84px;text-align:right;font-variant-numeric:tabular-nums}',
      '.nr-muet{font-size:12px;color:var(--muted)}',
      '.nr-nb{font-size:12px;color:var(--muted);text-align:right;white-space:nowrap}',
      '.nr-ordre{display:flex;flex-direction:column;gap:2px}',
      '.nr-icone{width:26px;height:20px;padding:0;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text2);cursor:pointer;font-size:10px;line-height:1;font-family:inherit}',
      '.nr-icone:hover:not(:disabled){border-color:var(--accent);color:var(--accent);background:var(--card)}',
      '.nr-icone:disabled{opacity:.3;cursor:default}',
      '.nr-suppr{width:30px;height:30px;font-size:16px}',
      '.nr-suppr:hover:not(:disabled){border-color:var(--danger);color:var(--danger)}',
      '.nr-ajout{margin-top:12px;padding:8px 14px;border-radius:9px;border:1px dashed var(--border);background:var(--card);color:var(--text2);font-weight:600;font-size:13px;cursor:pointer;font-family:inherit}',
      '.nr-ajout:hover{border-color:var(--accent);color:var(--accent)}',
      '.nr-note{font-size:12px;color:var(--muted);line-height:1.55;margin:14px 0 0}',
      '.nr-foot{display:flex;align-items:center;gap:8px;padding:14px 22px;border-top:1px solid var(--border)}',
      '.nr-foot .nr-sep{flex:1}',
      '.nr-etat{font-size:12px;color:var(--muted)}',
      '.nr-btn{padding:9px 16px;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit}',
      '.nr-btn.secondaire{border:1px solid var(--border);background:var(--bg);color:var(--text2)}',
      '.nr-btn.secondaire:hover{background:var(--card);border-color:var(--accent);color:var(--accent)}',
      '.nr-btn.primaire{border:none;background:var(--accent);color:white}',
      '.nr-btn.primaire:hover:not(:disabled){filter:brightness(1.08)}',
      '.nr-btn:disabled{opacity:.45;cursor:default}',
      '@media(max-width:640px){.nr-table th:nth-child(5),.nr-table td:nth-child(5){display:none}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function selectTva(c) {
    return '<select data-f="taux_tva">' + etat.taux.map(function (t) {
      return '<option value="' + t + '"' + (Number(c.taux_tva) === t ? ' selected' : '') + '>' + fmtTaux(t) + '</option>';
    }).join('') + '</select>';
  }

  function ligne(c, i, n) {
    var km = c.saisie === 'km';
    var saisie = c.id == null
      ? '<select data-f="saisie"><option value="montant"' + (km ? '' : ' selected') + '>Montant</option>' +
        '<option value="km"' + (km ? ' selected' : '') + '>Kilomètres</option></select>'
      : '<span class="nr-muet">' + (km ? 'Kilomètres' : 'Montant') + '</span>';
    var taux = km
      ? '<span class="nr-km"><input type="number" data-f="taux_km" step="0.001" min="0" value="' +
        (c.taux_km != null ? esc(c.taux_km) : '') + '" placeholder="0,000">€ / km</span>'
      : selectTva(c);
    var nb = c.nb_notes || 0;
    return '<tr data-i="' + i + '">' +
      '<td><div class="nr-ordre">' +
        '<button type="button" class="nr-icone" data-act="monter" title="Monter"' + (i === 0 ? ' disabled' : '') + '>▲</button>' +
        '<button type="button" class="nr-icone" data-act="descendre" title="Descendre"' + (i === n - 1 ? ' disabled' : '') + '>▼</button>' +
      '</div></td>' +
      '<td><input type="text" data-f="libelle" maxlength="60" value="' + esc(c.libelle) + '" placeholder="Nom de la catégorie"></td>' +
      '<td>' + saisie + '</td>' +
      '<td>' + taux + '</td>' +
      '<td class="nr-nb">' + (c.id == null ? 'Nouvelle' : nb + ' note' + (nb > 1 ? 's' : '')) + '</td>' +
      '<td style="text-align:right"><button type="button" class="nr-icone nr-suppr" data-act="supprimer" title="Supprimer" aria-label="Supprimer">×</button></td>' +
      '</tr>';
  }

  function rendre(focusI) {
    var n = etat.liste.length;
    etat.back.querySelector('.nr-body').innerHTML =
      '<table class="nr-table">' +
        '<thead><tr><th></th><th>Catégorie</th><th>Saisie</th><th>TVA par défaut / taux</th><th style="text-align:right">Utilisée</th><th></th></tr></thead>' +
        '<tbody>' + etat.liste.map(function (c, i) { return ligne(c, i, n); }).join('') + '</tbody>' +
      '</table>' +
      '<button type="button" class="nr-ajout" data-act="ajouter">+ Ajouter une catégorie</button>' +
      '<p class="nr-note">Les salariés voient les catégories dans cet ordre. La TVA indiquée est proposée par défaut, le salarié peut la changer. ' +
      'Une catégorie en kilomètres calcule le montant à partir de la distance et du taux par km. Supprimer une catégorie la retire du formulaire ; ' +
      'les notes déjà saisies gardent leur libellé et leurs montants.<br>Taux de TVA proposés : ' + etat.taux.map(fmtTaux).join(', ') +
      ' (taux légaux, fixés dans le code).</p>';
    if (focusI != null) {
      var champ = etat.back.querySelector('tr[data-i="' + focusI + '"] input[data-f=libelle]');
      if (champ) champ.focus();
    }
    majPied();
  }

  function majPied() {
    var b = etat.back.querySelector('[data-act=enregistrer]');
    if (b) b.disabled = !etat.modifie;
    var e = etat.back.querySelector('.nr-etat');
    if (e) e.textContent = etat.modifie ? 'Modifications non enregistrées' : '';
  }
  function marquer() { etat.modifie = true; majPied(); }

  async function charger() {
    var j = await api(API);
    etat.taux = j.taux_tva || etat.taux;
    etat.liste = (j.categories || []).map(function (c) {
      return { id: c.id, libelle: c.libelle, saisie: c.saisie, taux_tva: c.taux_tva, taux_km: c.taux_km, nb_notes: c.nb_notes };
    });
    etat.modifie = false;
    rendre();
  }

  async function enregistrer() {
    var corps = etat.liste.map(function (c) {
      return { id: c.id, libelle: (c.libelle || '').trim(), saisie: c.saisie, taux_tva: c.taux_tva, taux_km: c.taux_km };
    });
    if (corps.some(function (c) { return !c.libelle; })) { message('Chaque catégorie doit avoir un nom.', 'err'); return; }
    var b = etat.back.querySelector('[data-act=enregistrer]');
    b.disabled = true;
    try {
      await api(API, { method: 'PUT', body: JSON.stringify({ categories: corps }) });
      message('Réglages enregistrés.');
      await charger();
      if (typeof etat.surChange === 'function') { try { etat.surChange(); } catch (e) {} }
    } catch (err) {
      message(err.message, 'err');
      majPied();
    }
  }

  function surClic(e) {
    var b = e.target.closest('[data-act]');
    if (!b || !etat.back.contains(b)) return;
    var act = b.getAttribute('data-act');
    var tr = b.closest('tr');
    var i = tr ? Number(tr.getAttribute('data-i')) : -1;
    if (act === 'monter' || act === 'descendre') {
      var j = act === 'monter' ? i - 1 : i + 1;
      var x = etat.liste[i]; etat.liste[i] = etat.liste[j]; etat.liste[j] = x;
      marquer(); rendre();
    } else if (act === 'supprimer') {
      etat.liste.splice(i, 1);
      marquer(); rendre();
    } else if (act === 'ajouter') {
      etat.liste.push({ id: null, libelle: '', saisie: 'montant', taux_tva: 20, taux_km: null, nb_notes: 0 });
      marquer(); rendre(etat.liste.length - 1);
    } else if (act === 'enregistrer') {
      enregistrer();
    } else if (act === 'annuler' || act === 'fermer') {
      demanderFermeture();
    }
  }

  // Les champs mettent à jour la copie sans redessiner : la saisie garde son focus.
  function surSaisie(e) {
    var el = e.target.closest('[data-f]');
    if (!el) return;
    var tr = el.closest('tr');
    if (!tr || !etat.back || !etat.back.contains(tr)) return;
    var c = etat.liste[Number(tr.getAttribute('data-i'))];
    if (!c) return;
    var f = el.getAttribute('data-f');
    if (f === 'libelle') c.libelle = el.value;
    else if (f === 'taux_tva') c.taux_tva = Number(el.value);
    else if (f === 'taux_km') c.taux_km = el.value;
    else if (f === 'saisie') {
      c.saisie = el.value;
      if (c.saisie === 'km') c.taux_tva = 0; else c.taux_tva = 20;
      marquer(); rendre(); return;
    }
    marquer();
  }

  async function demanderFermeture() {
    if (etat.modifie && typeof window.mysifaConfirm === 'function') {
      var ok = await window.mysifaConfirm({
        title: 'Abandonner les modifications',
        message: 'Les changements faits dans les réglages ne seront pas enregistrés.',
        confirmLabel: 'Abandonner', danger: true
      });
      if (!ok) return;
    }
    fermer(false);
  }

  function fermer(technique) {
    if (!etat.back) return;
    etat.back.remove();
    etat.back = null;
    etat.modifie = false;
    document.removeEventListener('keydown', surTouche);
    if (technique !== true) prevenirAdresse();
  }
  function surTouche(e) {
    if (e.key === 'Escape' && !document.querySelector('.mysifa-cfm-ov')) demanderFermeture();
  }

  async function ouvrir(opts) {
    opts = opts || {};
    etat.surChange = opts.surChange || null;
    etat.surAdresse = opts.surAdresse || null;
    if (etat.back) return;
    injecterStyle();
    var back = document.createElement('div');
    back.className = 'nr-back';
    back.innerHTML =
      '<div class="nr-modal" role="dialog" aria-modal="true" aria-label="Réglages des notes de frais">' +
        '<div class="nr-head">' +
          '<div><h3>Réglages des notes de frais</h3><div class="nr-sub">Catégories proposées aux salariés et barème kilométrique.</div></div>' +
          '<button type="button" class="nr-close" data-act="fermer" aria-label="Fermer">×</button>' +
        '</div>' +
        '<div class="nr-body"><p class="nr-note">Chargement…</p></div>' +
        '<div class="nr-foot">' +
          '<span class="nr-etat"></span><span class="nr-sep"></span>' +
          '<button type="button" class="nr-btn secondaire" data-act="annuler">Annuler</button>' +
          '<button type="button" class="nr-btn primaire" data-act="enregistrer" disabled>Enregistrer</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(back);
    etat.back = back;
    back.addEventListener('click', function (e) {
      if (e.target === back) { demanderFermeture(); return; }
      surClic(e);
    });
    back.addEventListener('input', surSaisie);
    back.addEventListener('change', function (e) { if (e.target.matches('select')) surSaisie(e); });
    document.addEventListener('keydown', surTouche);
    prevenirAdresse();
    try {
      await charger();
    } catch (err) {
      back.querySelector('.nr-body').innerHTML = '<p class="nr-note" style="color:var(--danger)">' + esc(err.message) + '</p>';
    }
  }

  window.MySifaNdfReglages = {
    ouvrir: ouvrir,
    fermer: fermer,
    estOuvert: function () { return !!etat.back; }
  };
})();
