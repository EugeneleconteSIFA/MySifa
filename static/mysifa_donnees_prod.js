/* MySifa — panneau « Données de prod » d'un dossier.
 *
 * Partagé par le déstockage (MyStock, planning) et la synthèse détaillée de
 * MyProd : cartes de temps, opérateurs, saisies colorées par nature
 * d'opération. Un seul rendu, sinon les deux écrans divergent au premier
 * correctif.
 *
 * Entrée : { stats, saisies, alerte } — `stats` vient de
 * `build_dossier_production_stats`, les saisies de production_data.
 * API : MySifaDonneesProd.html(d) → chaîne HTML.
 */
(function () {
  'use strict';

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

  // ── Données de prod ─────────────────────────────────────────────────────
  // Ce qu'on regarde pour juger une quantité : les chiffres de la fiche
  // dossier du planning (même calcul serveur) et les saisies de MyProd.
  function duree(min) {
    const m = Math.round(Number(min || 0));
    if (!m) return '—';
    const h = Math.floor(m / 60);
    return h ? h + ' h ' + String(m % 60).padStart(2, '0') : m + ' min';
  }
  function dateCourte(iso) {
    const t = String(iso || '');
    return t.length >= 16 ? t.slice(8, 10) + '/' + t.slice(5, 7) + ' ' + t.slice(11, 16) : t;
  }
  // Une couleur par nature d'opération, la même dans les cartes, la légende et
  // les pastilles des saisies : on lit la journée d'un coup d'œil.
  const DP_CATS = {
    calage: ['Calage', 'var(--c4)'],
    production: ['Production', 'var(--success)'],
    arret: ['Arrêt', 'var(--danger)'],
    nettoyage: ['Nettoyage', 'var(--c2)'],
    technique: ['Technique', 'var(--text2)'],
    appro: ['Appro', 'var(--muted)'],
    personnel: ['Début / fin', 'var(--text)'],
  };
  const DP_CSS = ''
    + '.dp{border:1px solid var(--border);border-radius:12px;padding:14px;background:var(--card)}'
    + '.dp-alerte{margin-bottom:12px;padding:8px 12px;border-radius:9px;border:1px solid var(--danger);'
    + 'background:color-mix(in srgb,var(--danger) 10%,transparent);color:var(--danger);font-size:12px;font-weight:600}'
    + '.dp-cartes{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:8px;margin-bottom:14px}'
    + '.dp-carte{padding:9px 12px;border-radius:9px;border:1px solid var(--border);border-left:4px solid var(--c,var(--border));'
    + 'background:color-mix(in srgb,var(--c,var(--bg)) 8%,var(--card))}'
    + '.dp-carte-lib{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}'
    + '.dp-carte-val{font-size:15px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums;margin-top:2px}'
    + '.dp-titre{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;text-transform:uppercase;'
    + 'letter-spacing:.5px;color:var(--text2);margin:4px 0 6px}'
    + '.dp-titre .dp-n{padding:1px 7px;border-radius:999px;background:var(--bg);border:1px solid var(--border);color:var(--muted)}'
    + '.dp-legende{display:flex;flex-wrap:wrap;gap:10px;margin-left:auto;font-weight:600;text-transform:none;letter-spacing:0;color:var(--muted)}'
    + '.dp-legende span{display:inline-flex;align-items:center;gap:4px}'
    + '.dp-pt{width:8px;height:8px;border-radius:50%;background:var(--c);display:inline-block}'
    + '.dp-wrap{border:1px solid var(--border);border-radius:10px;overflow:auto;margin-bottom:14px}'
    + '.dp-wrap.dp-haut{max-height:340px}'
    + '.dp-t{width:100%;border-collapse:collapse;font-size:12px}'
    + '.dp-t th{position:sticky;top:0;z-index:1;background:var(--bg);text-align:left;padding:7px 10px;font-size:10px;font-weight:700;'
    + 'text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap}'
    + '.dp-t td{padding:7px 10px;border-bottom:1px solid var(--border);color:var(--text2);white-space:nowrap}'
    + '.dp-t th+th,.dp-t td+td{border-left:1px solid var(--border)}'
    + '.dp-t tbody tr:nth-child(even) td{background:color-mix(in srgb,var(--bg) 55%,transparent)}'
    + '.dp-t tbody tr:hover td{background:var(--accent-bg)}'
    + '.dp-t tbody tr:last-child td{border-bottom:none}'
    + '.dp-t .n{text-align:right;font-variant-numeric:tabular-nums}'
    + '.dp-t .dp-tot td{font-weight:700;color:var(--text);background:var(--bg)}'
    + '.dp-t tr.dp-borne td{background:color-mix(in srgb,var(--accent) 7%,transparent)}'
    + '.dp-t td.dp-com{white-space:normal;min-width:140px}'
    + '.dp-code{display:inline-block;min-width:24px;padding:1px 6px;margin-right:6px;border-radius:6px;text-align:center;font-weight:700;'
    + 'color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);border:1px solid color-mix(in srgb,var(--c) 40%,transparent)}'
    + '.dp-cpt{font-family:ui-monospace,Consolas,monospace;font-weight:700;color:var(--text)}'
    + '.dp-clos{margin-left:6px;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:700;color:white;background:var(--accent)}'
    + '.dp-vide{color:var(--muted)}';

  function prodHtml(d) {
    const st = d.stats || {};
    const tt = st.temps_totaux || {};
    const q = st.quantites || {};
    const carte = (lib, val, c) => '<div class="dp-carte"' + (c ? ' style="--c:' + c + '"' : '') + '>'
      + '<div class="dp-carte-lib">' + lib + '</div><div class="dp-carte-val">' + val + '</div></div>';
    const vide = '<span class="dp-vide">—</span>';
    const dur = (m) => Number(m || 0) ? duree(m) : vide;
    let h = '<style>' + DP_CSS + '</style><div class="dp">';
    if (d.alerte) h += '<div class="dp-alerte">' + esc(d.alerte.charAt(0).toUpperCase() + d.alerte.slice(1)) + '.</div>';
    h += '<div class="dp-cartes">'
      + carte('Durée totale', duree(tt.duree_totale_min), 'var(--text2)')
      + carte('Calage', duree(tt.calage_min), DP_CATS.calage[1])
      + carte('Production', duree(tt.production_min), DP_CATS.production[1])
      + carte('Arrêts', duree(tt.arret_min), DP_CATS.arret[1])
      + (Number(tt.nettoyage_min || 0) ? carte('Nettoyage', duree(tt.nettoyage_min), DP_CATS.nettoyage[1]) : '')
      + carte('Étiquettes', nombre(q.etiquettes), 'var(--accent)')
      + carte('Métrage', q.metrage_m ? nombre(Math.round(q.metrage_m)) + ' m' : '—', d.alerte ? 'var(--danger)' : 'var(--accent)')
      + carte('Vitesse', st.vitesse_aberrante ? '<span style="color:var(--danger);font-weight:400">erreur saisie</span>'
          : st.vitesse_m_min ? nombre(Math.round(st.vitesse_m_min * 10) / 10) + ' m/min' : '—', 'var(--accent)')
      + '</div>';

    const ops = st.operateurs || [];
    if (ops.length) {
      const tot = (k) => ops.reduce((s, o) => s + Number(o[k] || 0), 0);
      h += '<div class="dp-titre">Opérateurs <span class="dp-n">' + ops.length + '</span></div>'
        + '<div class="dp-wrap"><table class="dp-t"><thead><tr><th>Opérateur</th><th class="n">Saisies</th>'
        + '<th class="n">Calage</th><th class="n">Production</th><th class="n">Arrêts</th><th class="n">Total</th></tr></thead><tbody>'
        + ops.map(o => '<tr><td style="font-weight:600;color:var(--text)">' + esc(o.operateur || '?') + '</td>'
          + '<td class="n">' + nombre(o.nb_saisies) + '</td><td class="n">' + dur(o.calage_min) + '</td>'
          + '<td class="n">' + dur(o.prod_min) + '</td><td class="n">' + dur(o.arret_min) + '</td>'
          + '<td class="n" style="font-weight:700;color:var(--text)">' + dur(o.minutes) + '</td></tr>').join('')
        + (ops.length > 1 ? '<tr class="dp-tot"><td>Total</td><td class="n">' + nombre(tot('nb_saisies')) + '</td>'
          + '<td class="n">' + dur(tot('calage_min')) + '</td><td class="n">' + dur(tot('prod_min')) + '</td>'
          + '<td class="n">' + dur(tot('arret_min')) + '</td><td class="n">' + dur(tot('minutes')) + '</td></tr>' : '')
        + '</tbody></table></div>';
    }

    const rows = d.saisies || [];
    const legende = Object.values(DP_CATS).map(([lib, c]) =>
      '<span><i class="dp-pt" style="--c:' + c + '"></i>' + lib + '</span>').join('');
    h += '<div class="dp-titre">Saisies <span class="dp-n">' + rows.length + '</span>'
      + (rows.length ? '<span class="dp-legende">' + legende + '</span>' : '') + '</div>';
    if (!rows.length) return h + '<div class="dp-vide" style="font-size:13px">Aucune saisie de production pour ce dossier.</div></div>';
    h += '<div class="dp-wrap dp-haut"><table class="dp-t"><thead><tr>'
      + '<th>Date</th><th>Opération</th><th>Opérateur</th><th>Machine</th>'
      + '<th class="n">Qté traitée</th><th class="n">Compteur début</th><th class="n">Compteur fin</th><th>Commentaire</th>'
      + '</tr></thead><tbody>'
      + rows.map(r => {
        const code = String(r.operation_code || '');
        const borne = code === '01' || code === '89';
        const c = (DP_CATS[String(r.operation_category || '').toLowerCase()] || [null, 'var(--muted)'])[1];
        const cpt = (v) => v ? '<span class="dp-cpt">' + nombre(v) + '</span>' : '';
        const libelle = String(r.operation || '').replace(/^\s*\d+\s*-\s*/, '');
        return '<tr' + (borne ? ' class="dp-borne"' : '') + '>'
          + '<td>' + esc(dateCourte(r.date_operation)) + '</td>'
          + '<td><span class="dp-code" style="--c:' + (borne ? 'var(--text)' : c) + '">' + esc(code) + '</span>'
          + esc(libelle) + (r.fin_dossier ? '<span class="dp-clos">Dossier clôturé</span>' : '') + '</td>'
          + '<td>' + esc(r.operateur || '') + '</td><td>' + esc(r.machine || '') + '</td>'
          + '<td class="n">' + (r.quantite_traitee ? nombre(r.quantite_traitee) : '') + '</td>'
          + '<td class="n">' + (code === '01' ? cpt(r.metrage_prevu) : '') + '</td>'
          + '<td class="n">' + (code === '89' ? cpt(r.metrage_reel) : '') + '</td>'
          + '<td class="dp-com">' + esc(r.commentaire || '') + '</td></tr>';
      }).join('')
      + '</tbody></table></div></div>';
    return h;
  }

  window.MySifaDonneesProd = { html: prodHtml };
})();
