/* MySifa — relecture du déstockage d'un dossier.
 *
 * Une seule modale pour deux écrans : le planning (bouton « Destocké » d'un
 * dossier) et MyStock › Déstockage. Elle vivait dans planning_page.py ; la
 * copier dans stock_page.py aurait donné deux relectures qui divergent au
 * premier correctif — et c'est précisément un écran où le chiffre vu doit
 * être le chiffre écrit.
 *
 * Unités (10/09/2026) : on saisit dans l'unité de l'atelier — mètres
 * linéaires, kilos, mandrins, cartons, palettes — et la colonne « simplifié »
 * montre ce que ça représente en bobines, tubes ou palettes. Les facteurs
 * viennent du serveur, qui s'en sert aussi pour écrire.
 *
 * Aucune correction n'écrase un mouvement passé : le serveur écrit la
 * différence, dans un sens ou dans l'autre.
 *
 * API : MySifaDestockage.ouvrir(entryId, {
 *   reference, fermer(), toast(msg, type), onChange(etat, reserve), icone
 * })
 */
(function () {
  'use strict';

  const E = { opts: null, data: null, cand: {}, rows: [], entryId: null };

  const UNITES = {ml: ['ml', 'ml'], kg: ['kg', 'kg'], bobine: ['bobine', 'bobines'],
    tube: ['tube', 'tubes'], palette: ['palette', 'palettes'], carton: ['carton', 'cartons'],
    mandrin: ['mandrin', 'mandrins'], u: ['u', 'u']};

  function esc(v) {
    return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function nombre(v) {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    if (!isFinite(n)) return '—';
    return n.toLocaleString('fr-FR', {maximumFractionDigits: 3});
  }
  function unite(u, n) {
    const p = UNITES[u] || [u || '', u || ''];
    return (n !== null && n !== undefined && Math.abs(Number(n)) > 1) ? p[1] : p[0];
  }
  function toast(msg, type) {
    try { if (E.opts && E.opts.toast) { E.opts.toast(msg, type); return; } } catch (e) {}
    console.log(msg);
  }
  function fermer() {
    if (E.opts && typeof E.opts.fermer === 'function') { E.opts.fermer(); return; }
    const root = document.getElementById('mroot');
    if (root) root.innerHTML = '';
  }
  async function appel(path, options) {
    const o = options || {};
    const r = await fetch(path, Object.assign({credentials: 'include'}, o, {
      headers: Object.assign({'Content-Type': 'application/json'}, o.headers || {}),
    }));
    if (!r.ok) {
      let msg = 'Erreur ' + r.status;
      try {
        const j = await r.json();
        const d = j && j.detail;
        if (typeof d === 'string') msg = d;
        else if (d && d.message) msg = d.message;
        else if (d) msg = JSON.stringify(d);
      } catch (e) {}
      throw new Error(msg);
    }
    const ct = r.headers.get('content-type') || '';
    return ct.includes('application/json') ? r.json() : null;
  }

  function candidat(mid) { return E.cand[mid] || null; }

  function laizeParDefaut(c) {
    const laizes = (c && c.laizes) || [];
    if (!laizes.length) return null;
    const cible = Number((E.data && E.data.laize_dossier) || 0);
    if (cible) {
      const l = laizes.find(x => Math.abs(Number(x.valeur_mm || 0) - cible) < 0.5);
      if (l) return l.laize_id;
    }
    return laizes.length === 1 ? laizes[0].laize_id : null;
  }

  function preparer(d) {
    const cand = {};
    Object.values(d.candidats || {}).forEach(liste => (liste || []).forEach(c => { cand[c.matiere_id] = c; }));
    const lignes = (d.lignes || []).filter(l => l.matiere_id || l.destockable === false);
    E.rows = lignes.map(l => {
      // La matière de la ligne, même absente des candidats (désactivée
      // depuis) : sinon la liste afficherait une autre matière que celle
      // réellement sortie.
      if (l.matiere_id && !cand[l.matiere_id]) {
        cand[l.matiere_id] = {matiere_id: l.matiere_id, reference: l.matiere_ref,
          designation: l.matiere_designation, categorie: l.matiere_categorie,
          kind: l.kind, conversion: l.conversion || {}, laizes: l.laizes || []};
      }
      const conv = l.conversion || {};
      const dejaSorti = Math.abs(Number(l.sorti || 0)) > 1e-9;
      // Ajusté = ce qui doit AU TOTAL être sorti. Une ligne déjà sortie part
      // de son sorti ; une ligne restée en réserve part du consommé, pour que
      // la remplacer par une matière convertible la fasse sortir d'un geste.
      let val = dejaSorti ? l.sorti_reel : (l.destockable === false ? l.consomme : (l.sorti_reel ?? 0));
      if (val === null || val === undefined) val = 0;
      if (conv.entier) val = Math.round(Number(val));
      return {ligne: l, mid: l.matiere_id || null, lid: l.laize_id ?? null, val: Number(val)};
    });
    E.cand = cand;
    E.data = d;
  }

  function simplifieHtml(i) {
    const r = E.rows[i];
    const c = candidat(r.mid);
    const conv = (c && c.conversion) || {};
    if (!r.mid) return '<span style="color:var(--warn)">Choisir une matière</span>';
    if (conv.facteur_simplifie == null) {
      return '<span style="color:var(--warn)">' + esc(conv.manque || 'Conversion impossible') + '</span>';
    }
    const n = Number(r.val || 0) * Number(conv.facteur_simplifie);
    let h = '<span style="font-variant-numeric:tabular-nums">' + nombre(n) + '</span> ' + esc(unite(conv.unite_simplifiee, n));
    if (conv.facteur_stock == null && conv.manque) {
      h += '<div style="font-size:11px;color:var(--warn)">' + esc(conv.manque) + '</div>';
    }
    const l = r.ligne;
    const meme = r.mid === l.matiere_id && (r.lid ?? null) === (l.laize_id ?? null);
    if (l.sorti_reel != null && Math.abs(Number(l.sorti || 0)) > 1e-9
        && (!meme || Math.abs(Number(l.sorti_reel) - Number(r.val || 0)) > 1e-6)) {
      h += '<div style="font-size:11px;color:var(--muted)">déjà sorti : ' + nombre(l.sorti_reel) + ' '
        + esc(unite((l.conversion || {}).unite_reelle, l.sorti_reel))
        + (meme ? '' : ' de ' + esc(l.matiere_ref || '')) + '</div>';
    }
    return h;
  }

  function ligneHtml(i) {
    const r = E.rows[i];
    const l = r.ligne;
    const c = candidat(r.mid);
    const conv = (c && c.conversion) || l.conversion || {};
    const options = [];
    const vus = new Set();
    (l.categories_remplacement || []).forEach(cat => ((E.data.candidats || {})[cat] || []).forEach(o => {
      vus.add(o.matiere_id);
      options.push(o);
    }));
    if (r.mid && !vus.has(r.mid) && c) { options.unshift(c); vus.add(r.mid); }
    if (l.matiere_id && !vus.has(l.matiere_id) && candidat(l.matiere_id)) options.unshift(candidat(l.matiere_id));

    const selStyle = 'width:100%;max-width:280px;background:var(--bg);border:1px solid var(--border);'
      + 'border-radius:7px;padding:6px 8px;color:var(--text);font-family:inherit;font-size:13px;font-weight:700';
    const opts = (r.mid ? '' : '<option value="">' + esc(l.source_value || 'Choisir une matière') + '</option>')
      + options.map(o => '<option value="' + o.matiere_id + '"' + (o.matiere_id === r.mid ? ' selected' : '') + '>'
        + esc(o.reference || '') + (o.designation && o.designation !== o.reference ? ' — ' + esc(o.designation) : '')
        + '</option>').join('');
    const select = '<select data-dr-mat="' + i + '" style="' + selStyle + '">' + opts + '</select>';

    const laizes = (c && c.laizes) || [];
    let laizeHtml = '';
    if (laizes.length && (laizes.length > 1 || r.lid == null || !laizes.some(x => x.laize_id === r.lid))) {
      laizeHtml = '<select data-dr-lz="' + i + '" style="margin-top:5px;background:var(--bg);border:1px solid var(--border);'
        + 'border-radius:7px;padding:4px 7px;color:var(--text);font-family:inherit;font-size:12px">'
        + (r.lid == null ? '<option value="">Laize à choisir</option>' : '')
        + laizes.map(x => '<option value="' + x.laize_id + '"' + (x.laize_id === r.lid ? ' selected' : '') + '>'
          + esc(Math.round(Number(x.valeur_mm || 0)) + ' mm') + '</option>').join('')
        + '</select>';
    } else if (r.lid != null) {
      const lz = laizes.find(x => x.laize_id === r.lid);
      if (lz) laizeHtml = '<span>' + Math.round(Number(lz.valeur_mm || 0)) + ' mm</span>';
    }
    const remplace = (r.mid && l.matiere_id && r.mid !== l.matiere_id)
      ? 'remplace « ' + esc(l.matiere_ref || l.source_value || '') + ' »'
      : (l.remplace && r.mid === l.matiere_id ? 'remplace « ' + esc(l.remplace.matiere_ref || '') + ' »' : '');
    const sous = [laizeHtml, remplace, l.hors_fiche ? 'ajoutée à la main' : ''].filter(Boolean)
      .join('<span style="color:var(--muted)"> · </span>');

    const bloque = !r.mid || conv.facteur_stock == null;
    const step = conv.entier ? '1' : (conv.unite_reelle === 'ml' ? '1' : '0.001');
    const u = conv.unite_reelle || l.besoin_unite || '';
    return '<tr data-dr-i="' + i + '">'
      + '<td style="padding:9px 10px;vertical-align:top">' + select
      + '<div style="font-size:11px;color:var(--muted);margin-top:3px">' + sous + '</div></td>'
      + '<td style="padding:9px 10px;text-align:right;vertical-align:top;color:var(--muted);white-space:nowrap">'
      + (l.consomme != null ? nombre(l.consomme) + ' ' + esc(unite(u, l.consomme)) : '—') + '</td>'
      + '<td style="padding:9px 10px;text-align:right;vertical-align:top;white-space:nowrap">'
      + '<input type="number" step="' + step + '" min="0" data-dr-q="' + i + '" value="' + Number(r.val || 0) + '"'
      + (bloque ? ' disabled' : '')
      + ' style="width:110px;text-align:right;background:var(--bg);border:1px solid var(--border);border-radius:7px;'
      + 'padding:7px 9px;color:var(--text);font-family:inherit;font-size:13px;' + (bloque ? 'opacity:.5' : '') + '">'
      + '<span style="display:inline-block;min-width:54px;text-align:left;font-size:11.5px;color:var(--muted);padding-left:4px">'
      + esc(unite(u, r.val)) + '</span></td>'
      + '<td data-dr-simpl="' + i + '" style="padding:9px 10px;vertical-align:top;font-size:12.5px">' + simplifieHtml(i) + '</td>'
      + '</tr>';
  }

  function rendreLignes() {
    const tb = document.getElementById('dr-tbody');
    if (!tb) return;
    tb.innerHTML = E.rows.length
      ? E.rows.map((_, i) => ligneHtml(i)).join('')
      : '<tr><td colspan="4" style="padding:18px;text-align:center;color:var(--muted)">Aucune ligne.</td></tr>';
  }

  function changerMatiere(i, valeur) {
    const r = E.rows[i];
    if (!r) return;
    const mid = valeur === '' ? null : Number(valeur);
    const avant = candidat(r.mid);
    r.mid = mid;
    const c = candidat(mid);
    r.lid = (mid === r.ligne.matiere_id) ? (r.ligne.laize_id ?? laizeParDefaut(c)) : laizeParDefaut(c);
    // La quantité réelle ne change pas avec la matière : 18 000 ml restent
    // 18 000 ml, seul le nombre de bobines bouge.
    if (c && c.conversion && c.conversion.entier) r.val = Math.round(Number(r.val || 0));
    if (!avant && c && !r.val && r.ligne.consomme) r.val = Number(r.ligne.consomme);
    rendreLignes();
  }

  function changerQuantite(i, valeur) {
    const r = E.rows[i];
    if (!r) return;
    const q = parseFloat(String(valeur).replace(',', '.'));
    r.val = isNaN(q) ? 0 : q;
    // Pas de re-rendu de la ligne : il ferait perdre le focus du champ.
    const td = document.querySelector('[data-dr-simpl="' + i + '"]');
    if (td) td.innerHTML = simplifieHtml(i);
  }

  function corpsHtml(d) {
    const dossier = d.dossier || {};
    const reserve = (dossier.destockage_reserve || '').trim();
    const bandeau = reserve
      ? '<div style="margin-bottom:14px;padding:11px 14px;border-radius:9px;background:var(--bg);'
        + 'border:1px solid var(--warn);font-size:12.5px;line-height:1.6;color:var(--text)">'
        + '<b style="color:var(--warn)">Déstocké avec réserves</b><br>' + esc(reserve) + '</div>'
      : '';
    const etatTxt = dossier.destockage === 'reserve' ? 'avec réserves'
      : (dossier.destockage === 'done' ? 'complet' : 'non déstocké');
    const quand = (dossier.destockage_at || '').slice(0, 16).replace('T', ' ');
    const relu = dossier.destockage_relu_par
      ? ' · relu par ' + esc(dossier.destockage_relu_par)
        + (dossier.destockage_relu_at ? ' le ' + esc(String(dossier.destockage_relu_at).slice(0, 16).replace('T', ' ')) : '')
      : '';
    const th = 'padding:9px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)';
    const lever = dossier.destockage === 'reserve'
      ? '<label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2);margin-right:auto">'
        + '<input type="checkbox" id="dr-lever"> Lever la réserve — les manques ont été traités</label>'
      : '<span style="margin-right:auto"></span>';
    return bandeau
      + '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">Déstockage ' + esc(etatTxt)
      + (quand ? ' · ' + esc(quand) : '') + (dossier.destockage_par ? ' par ' + esc(dossier.destockage_par) : '') + relu
      + '. « Ajusté » est la quantité réellement consommée, AU TOTAL, dans l\'unité de l\'atelier ;'
      + ' le serveur écrit la différence. Une matière peut être remplacée par une autre de la même catégorie.</div>'
      + '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">'
      + '<thead><tr style="background:var(--bg)">'
      + '<th style="' + th + ';text-align:left">Matière</th>'
      + '<th style="' + th + ';text-align:right">Consommé</th>'
      + '<th style="' + th + ';text-align:right">Ajusté</th>'
      + '<th style="' + th + ';text-align:left">Simplifié</th>'
      + '</tr></thead><tbody id="dr-tbody"></tbody></table></div>'
      + '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:16px">' + lever
      + '<button type="button" data-dr-action="annuler" style="padding:9px 14px;border-radius:8px;border:1px solid var(--border);'
      + 'background:var(--bg);color:var(--danger);font-family:inherit;font-weight:600;cursor:pointer">Annuler tout le déstockage</button>'
      + '<button type="button" data-dr-action="enregistrer" style="padding:9px 16px;border-radius:8px;border:1px solid var(--accent);'
      + 'background:var(--accent);color:white;font-family:inherit;font-weight:700;cursor:pointer">Enregistrer</button>'
      + '</div>';
  }

  function brancher(body) {
    body.addEventListener('change', (ev) => {
      const t = ev.target;
      if (t.hasAttribute('data-dr-mat')) changerMatiere(Number(t.getAttribute('data-dr-mat')), t.value);
      else if (t.hasAttribute('data-dr-lz')) {
        const r = E.rows[Number(t.getAttribute('data-dr-lz'))];
        if (r) { r.lid = t.value === '' ? null : Number(t.value); rendreLignes(); }
      }
    });
    body.addEventListener('input', (ev) => {
      const t = ev.target;
      if (t.hasAttribute('data-dr-q')) changerQuantite(Number(t.getAttribute('data-dr-q')), t.value);
    });
    body.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-dr-action]');
      if (!b) return;
      if (b.getAttribute('data-dr-action') === 'enregistrer') enregistrer();
      else annulerTout();
    });
  }

  async function ouvrir(entryId, opts) {
    E.opts = opts || {};
    E.entryId = entryId;
    E.data = null; E.rows = []; E.cand = {};
    const root = document.getElementById('mroot');
    if (!root) return;
    const ref = E.opts.reference || 'Dossier';
    // Styles portés par la modale elle-même : le planning et MyStock n'ont
    // pas les mêmes classes de modale, et une relecture qui s'affiche sans
    // fond sur l'un des deux écrans ne se lit pas.
    root.innerHTML = '<div data-dr-overlay style="position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.55);'
      + 'display:flex;align-items:flex-start;justify-content:center;padding:4vh 12px;overflow-y:auto">'
      + '<div role="dialog" aria-modal="true" style="background:var(--card);color:var(--text);border:1px solid var(--border);'
      + 'border-radius:14px;width:100%;max-width:1040px;padding:22px 24px;box-shadow:0 20px 60px rgba(0,0,0,.35)">'
      + '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;gap:12px">'
      + '<h3 style="margin:0;font-size:18px;color:var(--text);display:flex;align-items:center;gap:8px">'
      + (E.opts.icone || '') + ' Déstockage — ' + esc(ref) + '</h3>'
      + '<button type="button" data-dr-fermer style="padding:8px 14px;border-radius:8px;border:1px solid var(--border);'
      + 'background:var(--bg);color:var(--text);font-family:inherit;cursor:pointer">Fermer</button></div>'
      + '<div id="dr-body"><div style="padding:24px;text-align:center;color:var(--muted)">Chargement…</div></div>'
      + '</div></div>';
    const overlay = root.querySelector('[data-dr-overlay]');
    overlay.addEventListener('click', (ev) => { if (ev.target === overlay) fermer(); });
    root.querySelector('[data-dr-fermer]').addEventListener('click', fermer);
    const body = document.getElementById('dr-body');
    try {
      const d = await appel('/api/stock/destockage/' + entryId + '/relecture');
      preparer(d);
      body.innerHTML = corpsHtml(d);
      brancher(body);
      rendreLignes();
    } catch (err) {
      body.innerHTML = '<div style="padding:20px;color:var(--danger)">' + esc(err.message || 'Relecture impossible.') + '</div>';
    }
  }

  async function enregistrer() {
    const lignes = [];
    for (const r of E.rows) {
      // Les matières qui portaient déjà une sortie sur cette ligne sont
      // renvoyées à zéro ; la matière retenue porte la quantité. Le serveur
      // additionne par matière et laize : garder la même matière revient à
      // « 0 + quantité ».
      (r.ligne.cles_initiales || []).forEach(([mid, lid]) =>
        lignes.push({matiere_id: mid, laize_id: lid ?? null, quantite_reelle: 0}));
      if (!r.mid) continue;
      const c = candidat(r.mid);
      const conv = (c && c.conversion) || {};
      const q = Number(r.val || 0);
      if (conv.facteur_stock == null) {
        if (q > 0 && r.mid !== r.ligne.matiere_id) {
          toast('« ' + (c ? c.reference : '') + ' » : ' + (conv.manque || 'conversion impossible') + '.', 'danger');
          return;
        }
        continue;
      }
      if (conv.entier && Math.abs(q - Math.round(q)) > 1e-9) {
        toast('« ' + c.reference + ' » : nombre entier de ' + unite(conv.unite_reelle, 2) + ' attendu.', 'danger');
        return;
      }
      if (q > 0 && (c.laizes || []).length && r.lid == null) {
        toast('« ' + c.reference + ' » : laize à choisir.', 'danger');
        return;
      }
      lignes.push({matiere_id: r.mid, laize_id: r.lid ?? null, quantite_reelle: q});
    }
    if (!lignes.length) { toast('Aucune quantité à enregistrer.', 'info'); return; }
    const lever = document.getElementById('dr-lever');
    try {
      const r = await appel('/api/stock/destockage/' + E.entryId + '/ajuster', {
        method: 'POST', body: JSON.stringify({lignes, lever_reserve: !!(lever && lever.checked)})});
      const n = (r.ajustements || []).length;
      fermer();
      if (E.opts.onChange) E.opts.onChange(r.destockage || 'done', r.destockage === 'reserve' ? (E.data.dossier || {}).destockage_reserve : null);
      toast(n ? n + ' ajustement(s) enregistré(s).' : 'Relecture enregistrée — aucun écart.', 'success');
    } catch (e) { toast(e.message || 'Enregistrement impossible.', 'danger'); }
  }

  async function annulerTout() {
    if (!confirm('Annuler tout le déstockage de ce dossier ?\n\nCe qui reste sorti sera rendu au stock par une écriture inverse. Les écritures restent à l\'historique.')) return;
    try {
      const r = await appel('/api/stock/destockage/' + E.entryId + '/annuler', {method: 'POST'});
      fermer();
      if (E.opts.onChange) E.opts.onChange('todo', null);
      toast('Déstockage annulé — ' + (r.mouvements || []).length + ' mouvement(s) contre-passé(s).', 'success');
    } catch (e) { toast(e.message || 'Annulation impossible.', 'danger'); }
  }

  window.MySifaDestockage = {ouvrir: ouvrir, _etat: E};
})();
