/* Réglages des notes de frais : barème kilométrique et catégories.
 *
 * Coffre RH (/rh/coffre) › Notes de frais, bouton « Réglages ». Les salariés
 * n'y ont pas accès : Mon coffre ne fait que lire les catégories actives, et
 * l'API /api/rh-coffre/ndf-categories refuse les autres rôles que la
 * comptabilité et le superadmin.
 *
 * Les taux de TVA proposés ne se règlent pas ici : ce sont les taux légaux,
 * NDF_TAUX_TVA de config.py.
 *
 * Adresse : ?reglages=ndf tant que la fenêtre est ouverte (relue au
 * chargement par depuisAdresse()).
 */
(function () {
  'use strict';

  var API = '/api/rh-coffre/ndf-categories';
  var CLE_URL = 'reglages';
  var etat = { cats: [], taux: [20, 10, 5.5, 0], back: null, surChange: null };

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

  function ecrireAdresse(ouvert) {
    try {
      var u = new URL(location.href);
      if (ouvert) u.searchParams.set(CLE_URL, 'ndf');
      else u.searchParams.delete(CLE_URL);
      if (u.href !== location.href) history.replaceState(history.state, '', u.href);
    } catch (e) {}
  }

  function injecterStyle() {
    if (document.getElementById('nr-style')) return;
    var st = document.createElement('style');
    st.id = 'nr-style';
    st.textContent = [
      '.nr-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:450;display:flex;align-items:center;justify-content:center;padding:16px}',
      '.nr-modal{background:var(--card);border:1px solid var(--border);border-top:3px solid var(--accent);border-radius:14px;max-width:860px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 24px 64px rgba(0,0,0,.35);color:var(--text)}',
      '.nr-head{display:flex;align-items:center;gap:12px;padding:18px 22px;background:var(--accent-bg);border-bottom:1px solid var(--border)}',
      '.nr-ico{width:36px;height:36px;flex-shrink:0;border-radius:10px;background:var(--accent);color:white;display:flex;align-items:center;justify-content:center}',
      '.nr-head h3{margin:0;font-size:16px;font-weight:700}',
      '.nr-sub{font-size:12px;color:var(--text2);margin-top:2px}',
      '.nr-close{margin-left:auto;width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-size:18px;line-height:1}',
      '.nr-close:hover{background:var(--bg);color:var(--accent)}',
      '.nr-body{padding:18px 22px}',
      '.nr-section{border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:14px;background:var(--bg)}',
      '.nr-section.km{background:color-mix(in srgb,var(--accent) 7%,var(--card));border-color:color-mix(in srgb,var(--accent) 30%,var(--border))}',
      '.nr-titre{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}',
      '.nr-titre::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--accent)}',
      '.nr-hint{font-size:12px;color:var(--muted);margin:0 0 12px;line-height:1.5}',
      '.nr-km-ligne{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:8px}',
      '.nr-km-nom{font-size:13px;font-weight:600;min-width:180px;flex:1}',
      '.nr-km-champ{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text2)}',
      '.nr-modal input,.nr-modal select{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 10px;color:var(--text);font-size:13px;font-family:inherit;outline:none;min-height:36px}',
      '.nr-modal input:focus,.nr-modal select:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}',
      '.nr-km-champ input{width:96px;text-align:right;font-family:"SF Mono","Consolas",monospace;font-weight:700}',
      '.nr-table{width:100%;border-collapse:collapse;font-size:13px}',
      '.nr-table th{text-align:left;padding:8px;color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}',
      '.nr-table td{padding:8px;border-bottom:1px solid var(--border);vertical-align:middle}',
      '.nr-table tr:last-child td{border-bottom:none}',
      '.nr-table tr.inactive td{opacity:.55}',
      '.nr-table input[type=text]{width:100%;min-width:120px}',
      '.nr-table tr.nouveau td{background:var(--card)}',
      '.nr-ordre{display:flex;flex-direction:column;gap:2px}',
      '.nr-ordre button{width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:5px;background:var(--card);color:var(--text2);cursor:pointer;font-size:10px;line-height:1}',
      '.nr-ordre button:hover:not(:disabled){background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}',
      '.nr-ordre button:disabled{opacity:.3;cursor:default}',
      '.nr-btn{padding:8px 14px;border-radius:9px;border:none;background:var(--accent);color:white;font-weight:700;font-size:12px;cursor:pointer;font-family:inherit;white-space:nowrap}',
      '.nr-btn:hover{filter:brightness(1.08)}',
      '.nr-switch{display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;color:var(--text2)}',
      '.nr-switch input{width:16px;height:16px;min-height:0;accent-color:var(--accent)}',
      '.nr-nb{font-size:12px;color:var(--muted);text-align:right}',
      '.nr-tva{display:flex;flex-wrap:wrap;gap:6px}',
      '.nr-tva span{padding:4px 10px;border-radius:999px;background:var(--card);border:1px solid var(--border);font-size:12px;color:var(--text2)}',
      '@media(max-width:640px){.nr-km-nom{min-width:0;flex-basis:100%}.nr-table th:nth-child(5),.nr-table td:nth-child(5){display:none}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function optionsTva(sel, desactive) {
    return '<select data-f="taux_tva"' + (desactive ? ' disabled' : '') + '>' +
      etat.taux.map(function (t) {
        return '<option value="' + t + '"' + (Number(sel) === t ? ' selected' : '') + '>' + fmtTaux(t) + '</option>';
      }).join('') + '</select>';
  }

  function ligneCategorie(c, i, n) {
    var km = c.saisie === 'km';
    return '<tr data-id="' + c.id + '" class="' + (c.actif ? '' : 'inactive') + '">' +
      '<td><div class="nr-ordre">' +
        '<button type="button" data-monter="' + i + '" title="Monter"' + (i === 0 ? ' disabled' : '') + '>▲</button>' +
        '<button type="button" data-descendre="' + i + '" title="Descendre"' + (i === n - 1 ? ' disabled' : '') + '>▼</button>' +
      '</div></td>' +
      '<td><input type="text" data-f="libelle" maxlength="60" value="' + esc(c.libelle) + '"></td>' +
      '<td>' + (km ? '<span style="font-size:12px;color:var(--muted)">Kilomètres</span>' : 'Montant') + '</td>' +
      '<td>' + (km ? '<span style="font-size:12px;color:var(--muted)">—</span>' : optionsTva(c.taux_tva)) + '</td>' +
      '<td class="nr-nb">' + (c.nb_notes || 0) + '</td>' +
      '<td><label class="nr-switch"><input type="checkbox" data-f="actif"' + (c.actif ? ' checked' : '') + '>Active</label></td>' +
      '<td style="text-align:right"><button type="button" class="nr-btn" data-enregistrer="' + c.id + '">Enregistrer</button></td>' +
      '</tr>';
  }

  function ligneNouvelle() {
    return '<tr class="nouveau" data-id="new">' +
      '<td></td>' +
      '<td><input type="text" data-f="libelle" maxlength="60" placeholder="Nouvelle catégorie"></td>' +
      '<td><select data-f="saisie"><option value="montant">Montant</option><option value="km">Kilomètres</option></select></td>' +
      '<td><span data-zone="tva">' + optionsTva(20) + '</span>' +
        '<span data-zone="km" style="display:none" class="nr-km-champ"><input type="number" data-f="taux_km" step="0.001" min="0" placeholder="0,000">€/km</span></td>' +
      '<td></td><td></td>' +
      '<td style="text-align:right"><button type="button" class="nr-btn" data-ajouter="1">Ajouter</button></td>' +
      '</tr>';
  }

  function rendre() {
    var cats = etat.cats;
    var kms = cats.filter(function (c) { return c.saisie === 'km'; });
    var corps = etat.back.querySelector('.nr-body');
    corps.innerHTML =
      '<div class="nr-section km">' +
        '<div class="nr-titre">Barème kilométrique</div>' +
        '<p class="nr-hint">Montant remboursé par kilomètre. Il s’applique aux nouvelles notes ; une note déjà saisie garde le taux de sa date.</p>' +
        (kms.length ? kms.map(function (c) {
          return '<div class="nr-km-ligne" data-id="' + c.id + '">' +
            '<span class="nr-km-nom">' + esc(c.libelle) + (c.actif ? '' : ' <span style="font-size:11px;color:var(--muted)">(inactive)</span>') + '</span>' +
            '<span class="nr-km-champ"><input type="number" data-f="taux_km" step="0.001" min="0" value="' + (c.taux_km != null ? esc(c.taux_km) : '') + '">€ par km</span>' +
            '<button type="button" class="nr-btn" data-km="' + c.id + '">Enregistrer</button>' +
          '</div>';
        }).join('') : '<p class="nr-hint" style="margin:0">Aucune catégorie en kilomètres. Ajoutez-en une ci-dessous avec le type « Kilomètres ».</p>') +
      '</div>' +
      '<div class="nr-section">' +
        '<div class="nr-titre">Catégories</div>' +
        '<p class="nr-hint">Proposées aux salariés dans cet ordre. La TVA indiquée est celle choisie par défaut ; le salarié peut la changer. Une catégorie déjà utilisée se désactive au lieu de se supprimer : les notes existantes la gardent.</p>' +
        '<div style="overflow-x:auto"><table class="nr-table">' +
          '<thead><tr><th></th><th>Libellé</th><th>Saisie</th><th>TVA par défaut</th><th style="text-align:right">Notes</th><th></th><th></th></tr></thead>' +
          '<tbody>' + cats.map(function (c, i) { return ligneCategorie(c, i, cats.length); }).join('') + ligneNouvelle() + '</tbody>' +
        '</table></div>' +
      '</div>' +
      '<div class="nr-section">' +
        '<div class="nr-titre">Taux de TVA proposés</div>' +
        '<p class="nr-hint">Taux légaux français, identiques pour tous : ils ne se modifient pas ici.</p>' +
        '<div class="nr-tva">' + etat.taux.map(function (t) { return '<span>' + fmtTaux(t) + '</span>'; }).join('') + '</div>' +
      '</div>';
  }

  async function charger() {
    var j = await api(API);
    etat.cats = j.categories || [];
    etat.taux = j.taux_tva || etat.taux;
    rendre();
  }

  async function apresModif(msg) {
    message(msg);
    await charger();
    if (typeof etat.surChange === 'function') {
      try { etat.surChange(); } catch (e) {}
    }
  }

  function valeur(tr, f) {
    var el = tr.querySelector('[data-f="' + f + '"]');
    if (!el) return undefined;
    return el.type === 'checkbox' ? el.checked : el.value;
  }

  async function surClic(e) {
    var b = e.target.closest('button');
    if (!b || !etat.back.contains(b)) return;
    try {
      if (b.dataset.km) {
        var ligne = b.closest('.nr-km-ligne');
        await api(API + '/' + b.dataset.km, { method: 'PATCH', body: JSON.stringify({ taux_km: valeur(ligne, 'taux_km') }) });
        await apresModif('Barème enregistré.');
      } else if (b.dataset.enregistrer) {
        var tr = b.closest('tr');
        var corps = { libelle: (valeur(tr, 'libelle') || '').trim(), actif: valeur(tr, 'actif') };
        var tva = valeur(tr, 'taux_tva');
        if (tva !== undefined) corps.taux_tva = Number(tva);
        if (!corps.libelle) { message('Libellé requis.', 'err'); return; }
        await api(API + '/' + b.dataset.enregistrer, { method: 'PATCH', body: JSON.stringify(corps) });
        await apresModif('Catégorie enregistrée.');
      } else if (b.dataset.ajouter) {
        var trn = b.closest('tr');
        var saisie = valeur(trn, 'saisie');
        var nouv = { libelle: (valeur(trn, 'libelle') || '').trim(), saisie: saisie };
        if (!nouv.libelle) { message('Libellé requis.', 'err'); return; }
        if (saisie === 'km') {
          nouv.taux_km = valeur(trn, 'taux_km');
          if (!nouv.taux_km) { message('Taux par km requis pour une catégorie en kilomètres.', 'err'); return; }
        } else {
          nouv.taux_tva = Number(valeur(trn, 'taux_tva'));
        }
        await api(API, { method: 'POST', body: JSON.stringify(nouv) });
        await apresModif('Catégorie ajoutée.');
      } else if (b.dataset.monter || b.dataset.descendre) {
        var i = Number(b.dataset.monter || b.dataset.descendre);
        var j = b.dataset.monter ? i - 1 : i + 1;
        var a = etat.cats[i], c = etat.cats[j];
        if (!a || !c) return;
        // Ordres distincts même si deux catégories partageaient la même valeur.
        var oa = (j + 1) * 10, oc = (i + 1) * 10;
        await api(API + '/' + a.id, { method: 'PATCH', body: JSON.stringify({ ordre: oa }) });
        await api(API + '/' + c.id, { method: 'PATCH', body: JSON.stringify({ ordre: oc }) });
        await apresModif('Ordre enregistré.');
      }
    } catch (err) {
      message(err.message, 'err');
    }
  }

  function surChangement(e) {
    var sel = e.target.closest('[data-f="saisie"]');
    if (!sel) return;
    var tr = sel.closest('tr');
    var km = sel.value === 'km';
    tr.querySelector('[data-zone="tva"]').style.display = km ? 'none' : '';
    tr.querySelector('[data-zone="km"]').style.display = km ? '' : 'none';
  }

  function fermer() {
    if (!etat.back) return;
    etat.back.remove();
    etat.back = null;
    document.removeEventListener('keydown', surTouche);
    ecrireAdresse(false);
  }
  function surTouche(e) { if (e.key === 'Escape') fermer(); }

  async function ouvrir(opts) {
    opts = opts || {};
    etat.surChange = opts.surChange || null;
    if (etat.back) return;
    injecterStyle();
    var back = document.createElement('div');
    back.className = 'nr-back';
    back.innerHTML =
      '<div class="nr-modal" role="dialog" aria-label="Réglages des notes de frais">' +
        '<div class="nr-head">' +
          '<div class="nr-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></div>' +
          '<div><h3>Réglages des notes de frais</h3><div class="nr-sub">Barème kilométrique et catégories proposées aux salariés.</div></div>' +
          '<button type="button" class="nr-close" aria-label="Fermer">×</button>' +
        '</div>' +
        '<div class="nr-body"><p class="nr-hint">Chargement…</p></div>' +
      '</div>';
    document.body.appendChild(back);
    etat.back = back;
    back.addEventListener('click', function (e) {
      if (e.target === back || e.target.closest('.nr-close')) { fermer(); return; }
      surClic(e);
    });
    back.addEventListener('change', surChangement);
    document.addEventListener('keydown', surTouche);
    ecrireAdresse(true);
    try {
      await charger();
    } catch (err) {
      back.querySelector('.nr-body').innerHTML = '<p class="nr-hint" style="color:var(--danger)">' + esc(err.message) + '</p>';
    }
  }

  // Rouvre la fenêtre si l'adresse la porte (rafraîchissement, lien partagé).
  function depuisAdresse(opts) {
    try {
      if (new URLSearchParams(location.search).get(CLE_URL) === 'ndf') ouvrir(opts);
    } catch (e) {}
  }

  window.MySifaNdfReglages = { ouvrir: ouvrir, fermer: fermer, depuisAdresse: depuisAdresse };
})();
