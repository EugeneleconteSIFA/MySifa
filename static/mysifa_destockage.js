/* MySifa — vérification et relecture du déstockage d'un dossier.
 *
 * Une seule modale pour deux écrans : le planning (bouton de déstockage d'un
 * dossier) et MyStock › Déstockage. Deux copies d'un écran où le chiffre vu
 * doit être le chiffre écrit auraient divergé au premier correctif.
 *
 * Deux moments, la même modale :
 * - AVANT la sortie (dossier « à destocker ») : on vérifie ce qui va sortir,
 *   on corrige, puis « Valider le déstockage ». Rien ne sort sans ce clic —
 *   un bouton qui écrivait directement dans le stock dérangeait (10/09/2026).
 * - APRÈS : relecture de ce qui est sorti, ajustement, annulation.
 *
 * Unités : on saisit dans l'unité de l'atelier — mètres linéaires, kilos,
 * mandrins, cartons, palettes — et la colonne « simplifié » montre ce que ça
 * représente en bobines, tubes ou palettes. Les facteurs viennent du serveur,
 * qui s'en sert aussi pour écrire.
 *
 * Tout se règle depuis la modale : une référence manquante se crée, un
 * conditionnement manquant se complète, la fiche matière s'ouvre à côté.
 *
 * API : MySifaDestockage.ouvrir(entryId, {
 *   reference, fermer(), toast(msg, type), onChange(etat, reserve), icone
 * })
 */
(function () {
  'use strict';

  const E = { opts: null, data: null, cand: {}, rows: [], entryId: null, edition: null };

  const UNITES = {ml: ['ml', 'ml'], kg: ['kg', 'kg'], bobine: ['bobine', 'bobines'],
    tube: ['tube', 'tubes'], palette: ['palette', 'palettes'], carton: ['carton', 'cartons'],
    mandrin: ['mandrin', 'mandrins'], u: ['u', 'u']};

  // Ce qu'il faut sur une fiche matière pour convertir, par nature de ligne.
  const CHAMPS_CONDITIONNEMENT = {
    support: [['metres_lineaires_par_bobine', 'Mètres linéaires par bobine']],
    glassine: [['metres_lineaires_par_bobine', 'Mètres linéaires par bobine']],
    carton: [['unites_par_palette', 'Cartons par palette']],
    mandrin: [['longueur_tube_mm', 'Longueur du tube (mm)'], ['unites_par_palette', 'Tubes par palette']],
    adhesif: [],
    palette: [],
  };
  const NATURES = {support: 'Frontal', glassine: 'Glassine', adhesif: 'Adhésif',
    mandrin: 'Mandrin', carton: 'Carton', palette: 'Palette', ajout: 'Ajout'};
  const LIBELLES_CATEGORIE = {frontal: 'Frontal', complexe: 'Complexe', glassine: 'Glassine',
    adhesif: 'Adhésif', mandrin: 'Mandrin', carton: 'Carton', palette: 'Palette'};

  function natureLigne(l) {
    if (l.attendue && l.kind === 'support') return 'Frontal / complexe';
    return NATURES[l.kind] || l.kind || '';
  }

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
      if (r.status === 403) msg = 'Action réservée aux administrateurs matières.';
      throw new Error(msg);
    }
    const ct = r.headers.get('content-type') || '';
    return ct.includes('application/json') ? r.json() : null;
  }

  function apercu() { return ((E.data && E.data.dossier) || {}).destockage === 'todo'; }
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

  function cleLigne(l) { return (l.kind || '') + '|' + (l.source_value || '') + '|' + (l.hors_fiche ? l.matiere_id : ''); }

  function preparer(d, garder) {
    const cand = {};
    Object.values(d.candidats || {}).forEach(liste => (liste || []).forEach(c => { cand[c.matiere_id] = c; }));
    const lignes = (d.lignes || []).filter(l => l.matiere_id || l.destockable === false);
    const avant = {};
    (garder || []).forEach(r => { avant[cleLigne(r.ligne)] = r; });
    const enApercu = (d.dossier || {}).destockage === 'todo';
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
      // Ajusté = ce qui doit AU TOTAL être sorti. Avant la sortie, on part du
      // consommé calculé ; après, du sorti. Une ligne restée en réserve part
      // du consommé, pour que la compléter la fasse sortir d'un geste.
      let val = dejaSorti ? l.sorti_reel
        : ((enApercu || l.destockable === false) ? l.consomme : (l.sorti_reel ?? 0));
      if (val === null || val === undefined) val = 0;
      // Adhésif ou glassine d'un complexe : déjà dans la bobine. Proposés à
      // zéro, saisissables si on en a réellement ajouté.
      if (l.inclus_complexe && !dejaSorti) val = 0;
      if (conv.entier) val = Math.round(Number(val));
      const row = {ligne: l, mid: l.matiere_id || null, lid: l.laize_id ?? null, val: Number(val)};
      // Après une création ou un complément de fiche, la modale se recharge :
      // ce que l'utilisateur avait déjà saisi ne doit pas disparaître.
      const p = avant[cleLigne(l)];
      if (p) {
        row.val = p.val;
        if (p.mid && (p.mid !== l.matiere_id || !l.matiere_id)) { row.mid = p.mid; row.lid = p.lid; }
      }
      return row;
    });
    E.cand = cand;
    E.data = d;
    E.rows.forEach(r => {
      if (r.mid && r.lid == null) r.lid = laizeParDefaut(candidat(r.mid));
    });
  }

  function boutonPetit(attr, i, libelle) {
    return '<button type="button" ' + attr + '="' + i + '" style="margin-top:6px;margin-right:6px;padding:5px 10px;'
      + 'border-radius:7px;border:1px solid var(--accent);background:var(--bg);color:var(--accent);'
      + 'font-family:inherit;font-size:12px;font-weight:700;cursor:pointer">' + libelle + '</button>';
  }

  function simplifieHtml(i) {
    const r = E.rows[i];
    const c = candidat(r.mid);
    const conv = (c && c.conversion) || {};
    if (!r.mid) {
      const l0 = r.ligne;
      // Ligne ajoutée parce que le dossier consomme forcément cette matière
      // (carton, palette, frontal…) alors que la fiche n'en dit rien.
      if (l0.attendue) {
        return '<span style="color:' + (l0.facultative ? 'var(--muted)' : 'var(--warn)') + '">'
          + esc((l0.manque || [])[0] || 'Matière à choisir') + '</span><br>'
          + boutonPetit('data-dr-creer', i, 'Créer une référence');
      }
      return '<span style="color:var(--warn)">Référence manquante — choisir une matière ou la créer</span><br>'
        + boutonPetit('data-dr-creer', i, 'Créer cette référence');
    }
    if (conv.facteur_simplifie == null || conv.facteur_stock == null) {
      const peutCompleter = (CHAMPS_CONDITIONNEMENT[c && c.kind] || []).length > 0;
      let h = '';
      if (conv.facteur_simplifie != null) {
        const n0 = Number(r.val || 0) * Number(conv.facteur_simplifie);
        h += '<span style="font-variant-numeric:tabular-nums">' + nombre(n0) + '</span> '
          + esc(unite(conv.unite_simplifiee, n0)) + '<br>';
      }
      h += '<span style="color:var(--warn)">' + esc(conv.manque || 'Conversion impossible') + '</span><br>'
        + (peutCompleter ? boutonPetit('data-dr-fiche', i, 'Compléter la fiche') : '');
      return h;
    }
    const n = Number(r.val || 0) * Number(conv.facteur_simplifie);
    let h = '<span style="font-variant-numeric:tabular-nums">' + nombre(n) + '</span> ' + esc(unite(conv.unite_simplifiee, n));
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

  const STYLE_CHAMP = 'width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);'
    + 'border-radius:7px;padding:7px 9px;color:var(--text);font-family:inherit;font-size:13px';

  function champ(nom, libelle, valeur, type) {
    return '<label style="display:flex;flex-direction:column;gap:4px;font-size:11px;font-weight:600;'
      + 'text-transform:uppercase;letter-spacing:.4px;color:var(--muted);min-width:170px;flex:1">'
      + esc(libelle) + '<input data-dr-champ="' + nom + '" type="' + (type || 'number') + '" '
      + (type === 'text' ? '' : 'step="any" min="0" ') + 'value="' + esc(valeur == null ? '' : valeur) + '" '
      + 'style="' + STYLE_CHAMP + ';text-transform:none;letter-spacing:0;font-weight:400"></label>';
  }

  function editionHtml(i) {
    const r = E.rows[i];
    const l = r.ligne;
    const ed = E.edition;
    let corps = '';
    if (ed.mode === 'creer') {
      const cats = l.categories_remplacement || [];
      const cat = ed.categorie || cats[0] || '';
      const selCat = '<label style="display:flex;flex-direction:column;gap:4px;font-size:11px;font-weight:600;'
        + 'text-transform:uppercase;letter-spacing:.4px;color:var(--muted);min-width:150px">Catégorie'
        + '<select data-dr-champ="categorie" style="' + STYLE_CHAMP + '">'
        + cats.map(k => '<option value="' + esc(k) + '"' + (k === cat ? ' selected' : '') + '>'
          + esc(LIBELLES_CATEGORIE[k] || k) + '</option>').join('') + '</select></label>';
      corps = selCat
        + champ('reference', 'Référence', ed.reference != null ? ed.reference : l.source_value, 'text')
        + champ('designation', 'Désignation', ed.designation != null ? ed.designation : l.source_value, 'text')
        + (CHAMPS_CONDITIONNEMENT[l.kind] || []).map(([n, lib]) => champ(n, lib, '')).join('')
        + (cat === 'palette' ? champ('palettes_par_pile', 'Palettes par pile', 1) : '');
    } else {
      const c = candidat(r.mid) || {};
      corps = (CHAMPS_CONDITIONNEMENT[c.kind] || []).map(([n, lib]) => champ(n, lib, '')).join('');
    }
    const titre = ed.mode === 'creer'
      ? (l.source_value ? 'Créer la référence « ' + esc(l.source_value) + ' »'
        : 'Créer une référence — ' + esc(natureLigne(l).toLowerCase()))
      : 'Compléter la fiche de « ' + esc((candidat(r.mid) || {}).reference || '') + ' »';
    const aide = ed.mode === 'creer'
      ? (l.source_value
        ? 'La matière est créée dans MyStock et associée à cette valeur de fiche : les prochains dossiers la trouveront seuls.'
        : 'La matière est créée dans MyStock et retenue pour ce dossier. Pensez à compléter la fiche technique du produit.')
      : 'Les champs laissés vides ne sont pas modifiés. Le reste de la fiche s\'édite dans MyStock.';
    return '<tr data-dr-edition="' + i + '"><td colspan="6" style="padding:10px 12px 14px;border-bottom:1px solid var(--border)">'
      + '<div style="border:1px solid var(--accent);border-radius:10px;padding:12px 14px;background:var(--bg)">'
      + '<div style="font-weight:700;font-size:13px;margin-bottom:4px">' + titre + '</div>'
      + '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">' + aide + '</div>'
      + '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">' + corps + '</div>'
      + '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">'
      + '<button type="button" data-dr-edition-annuler style="padding:7px 12px;border-radius:8px;border:1px solid var(--border);'
      + 'background:var(--card);color:var(--text);font-family:inherit;cursor:pointer">Annuler</button>'
      + '<button type="button" data-dr-edition-valider style="padding:7px 14px;border-radius:8px;border:1px solid var(--accent);'
      + 'background:var(--accent);color:white;font-family:inherit;font-weight:700;cursor:pointer">'
      + (ed.mode === 'creer' ? 'Créer la référence' : 'Enregistrer la fiche') + '</button>'
      + '</div></div></td></tr>';
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

    const selStyle = 'flex:1;min-width:0;width:100%;max-width:340px;background:var(--bg);border:1px solid var(--border);'
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
    } else if (r.mid && c && ['frontal', 'complexe', 'glassine'].includes(c.categorie)) {
      laizeHtml = '<span style="color:var(--warn)">aucune laize sur la matière</span> '
        + boutonPetit('data-dr-lier', i, 'Ajouter la laize du dossier');
    }
    const remplace = (r.mid && l.matiere_id && r.mid !== l.matiere_id)
      ? 'remplace « ' + esc(l.matiere_ref || l.source_value || '') + ' »'
      : (!l.matiere_id && r.mid && l.source_value ? 'pour « ' + esc(l.source_value) + ' »'
        : (l.remplace && r.mid === l.matiere_id ? 'remplace « ' + esc(l.remplace.matiere_ref || '') + ' »' : ''));
    const sous = [laizeHtml, remplace, l.hors_fiche ? 'ajoutée à la main' : '',
      l.depuis_of ? 'd\'après l\'OF (fiche technique vide)' : '',
      l.inclus_complexe ? 'déjà dans le complexe — à ne sortir que si on en a ajouté' : '',
      (l.attendue && r.mid) ? 'absente de la fiche technique' : ''].filter(Boolean)
      .join('<span style="color:var(--muted)"> · </span>');

    const bloque = !r.mid || conv.facteur_stock == null;
    const step = conv.entier ? '1' : (conv.unite_reelle === 'ml' ? '1' : '0.001');
    const u = conv.unite_reelle || l.besoin_unite || '';
    // Une ligne à compléter se voit d'un coup d'œil : liseré et fond, pas
    // seulement un texte orange noyé dans la dernière colonne.
    const aCompleter = (bloque && !(l.facultative && !r.mid)) || (c && (c.laizes || []).length && r.lid == null);
    const fond = (i % 2) ? 'background:var(--bg);' : '';
    const td = 'padding:10px 12px;vertical-align:middle;border-bottom:1px solid var(--border);' + fond;
    const lien = r.mid ? '<a href="/stock?matiere=' + encodeURIComponent(r.mid) + '" target="_blank" rel="noopener" '
      + 'title="Ouvrir la fiche matière" style="flex:none;display:inline-flex;align-items:center;justify-content:center;'
      + 'width:30px;height:30px;border-radius:7px;border:1px solid var(--border);color:var(--accent);text-decoration:none;'
      + 'font-weight:700">↗</a>' : '';
    const ecart = (l.consomme != null && !bloque) ? Number(r.val || 0) - Number(l.consomme) : null;
    const ecartHtml = ecart == null ? '<span style="color:var(--muted)">—</span>'
      : (Math.abs(ecart) < 1e-6 ? '<span style="color:var(--muted)">=</span>'
        : '<span style="font-weight:700;color:var(--warn)">' + (ecart > 0 ? '+' : '−') + nombre(Math.abs(ecart))
          + ' ' + esc(unite(u, Math.abs(ecart))) + '</span>');
    let html = '<tr data-dr-i="' + i + '">'
      + '<td style="' + td + 'border-left:3px solid ' + (aCompleter ? 'var(--warn)' : 'transparent') + ';white-space:nowrap">'
      + '<span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted)">'
      + esc(natureLigne(l)) + '</span></td>'
      + '<td style="' + td + '">'
      + '<div style="display:flex;gap:6px;align-items:center">' + select + lien + '</div>'
      + (sous ? '<div style="font-size:11.5px;color:var(--muted);margin-top:5px">' + sous + '</div>' : '') + '</td>'
      + '<td style="' + td + 'text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;color:var(--text2)">'
      + (l.consomme != null ? nombre(l.consomme) + ' <span style="color:var(--muted)">' + esc(unite(u, l.consomme)) + '</span>' : '—') + '</td>'
      + '<td style="' + td + 'text-align:right;white-space:nowrap">'
      + '<input type="number" step="' + step + '" min="0" data-dr-q="' + i + '" value="' + Number(r.val || 0) + '"'
      + (bloque ? ' disabled' : '')
      + ' style="width:104px;text-align:right;background:var(--card);border:1px solid var(--border);border-radius:7px;'
      + 'padding:7px 9px;color:var(--text);font-family:inherit;font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;'
      + (bloque ? 'opacity:.45' : '') + '">'
      + '<span style="display:inline-block;width:62px;text-align:left;font-size:12px;color:var(--muted);padding-left:6px">'
      + esc(unite(u, r.val)) + '</span></td>'
      + '<td data-dr-ecart="' + i + '" style="' + td + 'text-align:right;white-space:nowrap;font-size:12.5px">' + ecartHtml + '</td>'
      + '<td data-dr-simpl="' + i + '" style="' + td + 'font-size:12.5px">' + simplifieHtml(i) + '</td>'
      + '</tr>';
    if (E.edition && E.edition.i === i) html += editionHtml(i);
    return html;
  }

  function rendreLignes() {
    const tb = document.getElementById('dr-tbody');
    if (!tb) return;
    tb.innerHTML = E.rows.length
      ? E.rows.map((_, i) => ligneHtml(i)).join('')
      : '<tr><td colspan="6" style="padding:18px;text-align:center;color:var(--muted)">Aucune ligne.</td></tr>';
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
    if (E.edition && E.edition.i === i) E.edition = null;
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
    const te = document.querySelector('[data-dr-ecart="' + i + '"]');
    if (te && r.ligne.consomme != null) {
      const u = ((candidat(r.mid) || {}).conversion || r.ligne.conversion || {}).unite_reelle || '';
      const e = r.val - Number(r.ligne.consomme);
      te.innerHTML = Math.abs(e) < 1e-6 ? '<span style="color:var(--muted)">=</span>'
        : '<span style="font-weight:700;color:var(--warn)">' + (e > 0 ? '+' : '−') + nombre(Math.abs(e)) + ' ' + esc(unite(u, Math.abs(e))) + '</span>';
    }
  }

  async function recharger() {
    const garder = E.rows.map(r => ({ligne: r.ligne, mid: r.mid, lid: r.lid, val: r.val}));
    const d = await appel('/api/stock/destockage/' + E.entryId + '/relecture');
    preparer(d, garder);
    const body = document.getElementById('dr-body');
    if (body) { body.innerHTML = corpsHtml(d); rendreLignes(); }
  }

  function lireEdition() {
    const zone = document.querySelector('[data-dr-edition]');
    const out = {};
    if (!zone) return out;
    zone.querySelectorAll('[data-dr-champ]').forEach(inp => {
      const v = String(inp.value || '').trim();
      if (v !== '') out[inp.getAttribute('data-dr-champ')] = v;
    });
    return out;
  }

  async function lier(i, mid) {
    const l = E.rows[i].ligne;
    return appel('/api/stock/destockage/' + E.entryId + '/rattacher', {
      method: 'POST',
      body: JSON.stringify({matiere_id: mid, kind: l.hors_fiche ? '' : l.kind, source_value: l.hors_fiche ? '' : l.source_value}),
    });
  }

  async function validerEdition(bouton) {
    const ed = E.edition;
    if (!ed) return;
    const r = E.rows[ed.i];
    const v = lireEdition();
    if (bouton) bouton.disabled = true;
    try {
      if (ed.mode === 'creer') {
        if (!v.reference || !v.designation) throw new Error('Référence et désignation obligatoires.');
        const categorie = v.categorie || (r.ligne.categories_remplacement || [])[0];
        const cree = await appel('/api/stock/matieres', {method: 'POST', body: JSON.stringify({
          categorie: categorie, reference: v.reference, designation: v.designation,
          unites_par_palette: v.unites_par_palette, longueur_tube_mm: v.longueur_tube_mm,
          palettes_par_pile: v.palettes_par_pile,
        })});
        if (v.metres_lineaires_par_bobine) {
          await appel('/api/stock/matieres/' + cree.id, {method: 'PUT',
            body: JSON.stringify({metres_lineaires_par_bobine: v.metres_lineaires_par_bobine})});
        }
        const lien = await lier(ed.i, cree.id);
        r.mid = cree.id;
        r.lid = lien && lien.laize_id != null ? lien.laize_id : null;
        if (!r.val && r.ligne.consomme) r.val = Number(r.ligne.consomme);
        toast('Référence « ' + v.reference + ' » créée et associée.', 'success');
      } else {
        const champs = {};
        ['metres_lineaires_par_bobine', 'unites_par_palette', 'longueur_tube_mm'].forEach(k => {
          if (v[k] != null) champs[k] = v[k];
        });
        if (!Object.keys(champs).length) throw new Error('Aucun champ renseigné.');
        await appel('/api/stock/matieres/' + r.mid, {method: 'PUT', body: JSON.stringify(champs)});
        toast('Fiche matière complétée.', 'success');
      }
      E.edition = null;
      await recharger();
    } catch (e) {
      toast(e.message || 'Enregistrement impossible.', 'danger');
      if (bouton) bouton.disabled = false;
    }
  }

  function corpsHtml(d) {
    const dossier = d.dossier || {};
    const enApercu = dossier.destockage === 'todo';
    const reserve = (dossier.destockage_reserve || '').trim();
    const blocage = ((d.controle || {}).blocage || '').trim();
    let bandeau = '';
    if (enApercu) {
      bandeau = '<div style="margin-bottom:14px;padding:11px 14px;border-radius:9px;background:var(--bg);'
        + 'border:1px solid var(--accent);font-size:12.5px;line-height:1.6;color:var(--text)">'
        + '<b style="color:var(--accent)">Vérifier avant de déstocker</b><br>Rien n\'est encore sorti du stock. '
        + 'Contrôlez les quantités, complétez ce qui manque, puis validez.'
        + (blocage ? '<br><span style="color:var(--warn)">Le calcul automatique a refusé ce dossier : '
          + esc(blocage) + ' Saisissez les quantités à la main.</span>' : '')
        + '</div>';
    } else if (reserve) {
      bandeau = '<div style="margin-bottom:14px;padding:11px 14px;border-radius:9px;background:var(--bg);'
        + 'border:1px solid var(--warn);font-size:12.5px;line-height:1.6;color:var(--text)">'
        + '<b style="color:var(--warn)">Déstocké avec réserves</b><br>' + esc(reserve) + '</div>';
    }
    const notes = ((d.controle || {}).notes || []);
    if (notes.length) {
      bandeau += '<div style="margin-bottom:14px;padding:10px 14px;border-radius:9px;background:var(--bg);'
        + 'border:1px solid var(--border);font-size:12.5px;line-height:1.6;color:var(--text2)">'
        + notes.map(esc).join('<br>') + '</div>';
    }
    const etatTxt = dossier.destockage === 'reserve' ? 'avec réserves'
      : (dossier.destockage === 'done' ? 'complet' : 'à faire');
    const quand = (dossier.destockage_at || '').slice(0, 16).replace('T', ' ');
    const relu = dossier.destockage_relu_par
      ? ' · relu par ' + esc(dossier.destockage_relu_par)
        + (dossier.destockage_relu_at ? ' le ' + esc(String(dossier.destockage_relu_at).slice(0, 16).replace('T', ' ')) : '')
      : '';
    const th = 'padding:10px 12px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-bottom:1px solid var(--border)';
    const lever = (!enApercu && dossier.destockage === 'reserve')
      ? '<label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2);margin-right:auto">'
        + '<input type="checkbox" id="dr-lever"> Lever la réserve — les manques ont été traités</label>'
      : '<span style="margin-right:auto"></span>';
    const boutons = enApercu
      ? '<button type="button" data-dr-action="fermer" style="padding:9px 14px;border-radius:8px;border:1px solid var(--border);'
        + 'background:var(--bg);color:var(--text);font-family:inherit;font-weight:600;cursor:pointer">Annuler</button>'
        + '<button type="button" data-dr-action="enregistrer" style="padding:9px 16px;border-radius:8px;border:1px solid var(--accent);'
        + 'background:var(--accent);color:white;font-family:inherit;font-weight:700;cursor:pointer">Valider le déstockage</button>'
      : '<button type="button" data-dr-action="annuler" style="padding:9px 14px;border-radius:8px;border:1px solid var(--border);'
        + 'background:var(--bg);color:var(--danger);font-family:inherit;font-weight:600;cursor:pointer">Annuler tout le déstockage</button>'
        + '<button type="button" data-dr-action="enregistrer" style="padding:9px 16px;border-radius:8px;border:1px solid var(--accent);'
        + 'background:var(--accent);color:white;font-family:inherit;font-weight:700;cursor:pointer">Enregistrer</button>';
    return bandeau
      + '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">Déstockage ' + esc(etatTxt)
      + (quand ? ' · ' + esc(quand) : '') + (dossier.destockage_par ? ' par ' + esc(dossier.destockage_par) : '') + relu
      + '. « Ajusté » est la quantité réellement consommée, AU TOTAL, dans l\'unité de l\'atelier. '
      + 'Une matière peut être remplacée par une autre de la même catégorie.</div>'
      + '<div style="overflow-x:auto;border:1px solid var(--border);border-radius:10px">'
      + '<table style="width:100%;border-collapse:collapse;font-size:13px;min-width:900px">'
      + '<thead><tr style="background:var(--bg)">'
      + '<th style="' + th + ';text-align:left;width:86px">Nature</th>'
      + '<th style="' + th + ';text-align:left">Matière</th>'
      + '<th style="' + th + ';text-align:right;width:120px">Consommé</th>'
      + '<th style="' + th + ';text-align:right;width:190px">Ajusté</th>'
      + '<th style="' + th + ';text-align:right;width:110px">Écart</th>'
      + '<th style="' + th + ';text-align:left;width:250px">Simplifié</th>'
      + '</tr></thead><tbody id="dr-tbody"></tbody></table></div>'
      + '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:16px">' + lever + boutons + '</div>';
  }

  function brancher(body) {
    body.addEventListener('change', (ev) => {
      const t = ev.target;
      if (t.hasAttribute('data-dr-mat')) changerMatiere(Number(t.getAttribute('data-dr-mat')), t.value);
      else if (t.hasAttribute('data-dr-lz')) {
        const r = E.rows[Number(t.getAttribute('data-dr-lz'))];
        if (r) { r.lid = t.value === '' ? null : Number(t.value); rendreLignes(); }
      } else if (t.getAttribute('data-dr-champ') === 'categorie' && E.edition) {
        const v = lireEdition();
        E.edition = Object.assign(E.edition, {categorie: t.value, reference: v.reference, designation: v.designation});
        rendreLignes();
      }
    });
    body.addEventListener('input', (ev) => {
      const t = ev.target;
      if (t.hasAttribute('data-dr-q')) changerQuantite(Number(t.getAttribute('data-dr-q')), t.value);
    });
    body.addEventListener('click', async (ev) => {
      const t = ev.target.closest('button');
      if (!t) return;
      if (t.hasAttribute('data-dr-creer')) { E.edition = {i: Number(t.getAttribute('data-dr-creer')), mode: 'creer'}; rendreLignes(); return; }
      if (t.hasAttribute('data-dr-fiche')) { E.edition = {i: Number(t.getAttribute('data-dr-fiche')), mode: 'completer'}; rendreLignes(); return; }
      if (t.hasAttribute('data-dr-edition-annuler')) { E.edition = null; rendreLignes(); return; }
      if (t.hasAttribute('data-dr-edition-valider')) { validerEdition(t); return; }
      if (t.hasAttribute('data-dr-lier')) {
        const i = Number(t.getAttribute('data-dr-lier'));
        t.disabled = true;
        try {
          const res = await lier(i, E.rows[i].mid);
          if (res && res.laize_id != null) E.rows[i].lid = res.laize_id;
          await recharger();
        } catch (e) { toast(e.message || 'Rattachement impossible.', 'danger'); t.disabled = false; }
        return;
      }
      const a = t.getAttribute('data-dr-action');
      if (a === 'enregistrer') enregistrer(t);
      else if (a === 'annuler') annulerTout();
      else if (a === 'fermer') fermer();
    });
  }

  async function ouvrir(entryId, opts) {
    E.opts = opts || {};
    E.entryId = entryId;
    E.data = null; E.rows = []; E.cand = {}; E.edition = null;
    const root = document.getElementById('mroot');
    if (!root) return;
    const ref = E.opts.reference || 'Dossier';
    // Styles portés par la modale elle-même : le planning et MyStock n'ont
    // pas les mêmes classes de modale.
    root.innerHTML = '<div data-dr-overlay style="position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.55);'
      + 'display:flex;align-items:flex-start;justify-content:center;padding:4vh 12px;overflow-y:auto">'
      + '<div role="dialog" aria-modal="true" style="background:var(--card);color:var(--text);border:1px solid var(--border);'
      + 'border-radius:14px;width:100%;max-width:1240px;padding:22px 24px;box-shadow:0 20px 60px rgba(0,0,0,.35)">'
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

  async function enregistrer(bouton) {
    const enApercu = apercu();
    const lignes = [];
    const aLier = [];
    for (let i = 0; i < E.rows.length; i++) {
      const r = E.rows[i];
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
      // Une valeur de fiche sans correspondance, résolue à l'écran : on la
      // retient pour les prochains dossiers.
      if (!r.ligne.matiere_id && r.ligne.source_value && !r.ligne.hors_fiche) aLier.push(i);
    }
    if (!lignes.length) { toast('Aucune quantité à enregistrer.', 'info'); return; }
    const lever = document.getElementById('dr-lever');
    if (bouton) bouton.disabled = true;
    try {
      for (const i of aLier) {
        try { await lier(i, E.rows[i].mid); } catch (e) { /* l'association est un confort, pas une condition */ }
      }
      const r = await appel('/api/stock/destockage/' + E.entryId + '/ajuster', {
        method: 'POST', body: JSON.stringify({lignes, lever_reserve: !!(lever && lever.checked)})});
      const n = (r.ajustements || []).length;
      fermer();
      if (E.opts.onChange) {
        E.opts.onChange(r.destockage || 'done',
          r.destockage === 'reserve' ? ((r.reserves || []).join(' ; ') || (E.data.dossier || {}).destockage_reserve) : null);
      }
      if (enApercu) {
        toast(n + ' matière(s) sortie(s) du stock' + ((r.reserves || []).length ? ' — avec réserves.' : '.'),
          (r.reserves || []).length ? 'info' : 'success');
      } else {
        toast(n ? n + ' ajustement(s) enregistré(s).' : 'Relecture enregistrée — aucun écart.', 'success');
      }
    } catch (e) {
      toast(e.message || 'Enregistrement impossible.', 'danger');
      if (bouton) bouton.disabled = false;
    }
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
