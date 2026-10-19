/* MySifa — panneau « Données de prod » d'un dossier.
 *
 * Partagé par le déstockage (MyStock, planning) et la synthèse détaillée de
 * MyProd : cartes de temps, opérateurs, saisies colorées par nature
 * d'opération. Un seul rendu, sinon les deux écrans divergent au premier
 * correctif.
 *
 * Entrée : { stats, saisies, alerte, comparaison?, alertes? } — `stats` vient de
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
  function libelleOperation(r) {
    return String((r && r.operation) || '').replace(/^\s*\d{1,3}\s*(?:[-–:.]\s*|\s+)/, '');
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
    + '.dp-code{display:inline-block;padding:2px 9px;margin-right:6px;border-radius:999px;font-weight:600;'
    + 'color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);border:1px solid color-mix(in srgb,var(--c) 40%,transparent)}'
    + '.dp-cpt{font-weight:700;color:var(--text);font-variant-numeric:tabular-nums}'
    + '.dp-cpt-lib{margin-right:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted)}'
    + '.dp-saisies td.dp-com{min-width:0;width:100%}'
    + '.dp-clos{margin-left:6px;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:700;color:white;background:var(--accent)}'
    + '.dp-vide{color:var(--muted)}'
    + '.dp-frise{position:relative;height:30px;border-radius:8px;background:var(--bg);border:1px solid var(--border)}'
    + '.dp-frise i{position:absolute;top:0;bottom:0;background:var(--c);box-shadow:inset -1px 0 0 var(--card);cursor:default}'
    + '.dp-frise i:first-child{border-radius:7px 0 0 7px}.dp-frise i:last-child{border-radius:0 7px 7px 0}'
    + '.dp-frise i:hover{z-index:2;filter:brightness(1.15);box-shadow:0 0 0 2px var(--card),0 0 0 3px var(--c)}'
    + '.dp-frise i::after{content:attr(data-bulle);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);'
    + 'width:max-content;max-width:260px;padding:7px 10px;border-radius:8px;background:var(--text);color:var(--card);'
    + 'font-size:12px;font-weight:500;line-height:1.45;white-space:pre-line;text-align:left;'
    + 'box-shadow:0 4px 14px rgba(0,0,0,.18);opacity:0;pointer-events:none;transition:opacity .1s}'
    + '.dp-frise i.g::after{left:0;transform:none}.dp-frise i.d::after{left:auto;right:0;transform:none}'
    + '.dp-frise i:hover::after{opacity:1}'
    + '.dp-frise b{position:absolute;top:-7px;z-index:3;width:12px;height:12px;margin-left:-6px;border-radius:50%;'
    + 'background:var(--c,var(--accent));border:2px solid var(--card);box-sizing:border-box;cursor:default}'
    + '.dp-frise b:hover{transform:scale(1.3)}'
    + '.dp-frise b::after{content:attr(data-bulle);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);'
    + 'width:max-content;max-width:320px;padding:7px 10px;border-radius:8px;background:var(--text);color:var(--card);'
    + 'font-size:12px;font-weight:500;line-height:1.5;white-space:pre-line;text-align:left;'
    + 'box-shadow:0 4px 14px rgba(0,0,0,.18);opacity:0;pointer-events:none;transition:opacity .1s}'
    + '.dp-frise b.g::after{left:0;transform:none}.dp-frise b.d::after{left:auto;right:0;transform:none}'
    + '.dp-frise b:hover::after{opacity:1}'
    + '.dp-cartes.dp-3{grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:8px}'
    + '.dp-cartes.dp-3+.dp-cartes.dp-3{margin-bottom:14px}'
    + '.dp-carte-sub{font-size:11px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}'
    + '.dp-devis{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 8px;font-size:12px;color:var(--muted)}'
    + '.dp-devis .dp-cmp-concl{margin-left:0}'
    + '.dp-ident{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}'
    + '.dp-ident span{display:inline-flex;align-items:baseline;gap:6px;padding:5px 10px;border-radius:8px;'
    + 'background:var(--bg);border:1px solid var(--border);font-size:13px;font-weight:600;color:var(--text)}'
    + '.dp-ident em{font-style:normal;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}'
    + '.dp-frise-axe{position:relative;height:16px;margin:4px 0 14px;font-size:10px;color:var(--muted);font-variant-numeric:tabular-nums}'
    + '.dp-frise-axe span{position:absolute;transform:translateX(-50%);white-space:nowrap}'
    + '.dp-frise-axe span.dp-frise-jour{transform:none;font-weight:700;color:var(--text2)}'
    + '.dp-frise u{position:absolute;top:-4px;bottom:-4px;width:3px;margin-left:-1.5px;background:var(--card);z-index:1}'
    + '.dp-cmp-tete{display:flex;align-items:center;gap:8px;flex-wrap:wrap}'
    + '.dp-cmp-src{font-weight:500;text-transform:none;letter-spacing:0;color:var(--muted)}'
    + '.dp-cmp-concl{margin-left:auto;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;text-transform:none;letter-spacing:0;'
    + 'color:var(--c);background:color-mix(in srgb,var(--c) 12%,transparent);border:1px solid color-mix(in srgb,var(--c) 40%,transparent)}'
    + '.dp-ec{font-weight:700;font-variant-numeric:tabular-nums}'
    + '.dp-ec.bon{color:var(--success)}.dp-ec.mauvais{color:var(--danger)}'
    + '.dp-avert{margin:-6px 0 14px;font-size:12px;color:var(--warn)}'
    + '.dp-al{margin-bottom:14px}'
    + '.dp-al-bloc{border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:10px;background:var(--card)}'
    + '.dp-al-nom{font-size:13px;font-weight:700;color:var(--text);display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}'
    + '.dp-al-nom span{font-size:11px;font-weight:500;color:var(--muted)}'
    + '.dp-al-grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-top:8px}'
    + '.dp-al-g{border:1px solid var(--border);border-left:4px solid var(--c,var(--accent));border-radius:8px;padding:8px 10px;'
    + 'background:color-mix(in srgb,var(--c,var(--accent)) 6%,var(--card))}'
    + '.dp-al-g-lib{font-size:11px;font-weight:700;color:var(--text2);display:flex;justify-content:space-between;gap:8px}'
    + '.dp-al-g-lib b{font-variant-numeric:tabular-nums;color:var(--text)}'
    + '.dp-al-svg{display:block;width:100%;height:auto;margin-top:4px;overflow:visible}'
    + '.dp-al-svg .ligne{fill:none;stroke:var(--c,var(--accent));stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}'
    + '.dp-al-svg .aire{fill:var(--c,var(--accent));opacity:.14;stroke:none}'
    + '.dp-al-svg .grille{stroke:var(--border);stroke-width:1}'
    + '.dp-al-svg .pt{fill:var(--c,var(--accent));stroke:var(--card);stroke-width:2}'
    + '.dp-al-svg .cible{fill:transparent;cursor:default}'
    + '.dp-al-svg .cible:hover+.pt,.dp-al-svg .pt:hover{r:5.5}'
    + '.dp-al-svg text{font-size:10px;fill:var(--muted);font-variant-numeric:tabular-nums}'
    + '.dp-al-choix{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}'
    + '.dp-al-c{padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;color:var(--success);'
    + 'border:1px solid color-mix(in srgb,var(--success) 45%,transparent);background:color-mix(in srgb,var(--success) 12%,var(--card))}'
    + '.dp-al-c b{color:inherit}'
    + '.dp-al-c.nc{color:var(--danger);border-color:color-mix(in srgb,var(--danger) 45%,transparent);'
    + 'background:color-mix(in srgb,var(--danger) 12%,var(--card))}';

  // ── Alertes validées pendant le dossier ─────────────────────────────────
  // Une valeur relevée = une courbe dans le temps (une seule série : le titre
  // la nomme, pas de légende). Une question à choix n'est pas un graphe : le
  // compte de chaque réponse, les non-conformes marquées « NC » en toutes
  // lettres. Chaque point dit sa valeur, son heure et son opérateur au survol.
  function nombreFr(v) {
    const n = parseFloat(String(v == null ? '' : v).replace(',', '.').trim());
    return isFinite(n) ? n : null;
  }
  function courbe(points, unite) {
    const W = 300, H = 92, G = 34, D = 10, Hh = 10, B = 18;
    const ys = points.map(p => p.v);
    let lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
    if (lo === hi) { lo -= Math.abs(lo) * 0.05 || 1; hi += Math.abs(hi) * 0.05 || 1; }
    const ts = points.map(p => p.t);
    const t0 = Math.min.apply(null, ts), t1 = Math.max.apply(null, ts);
    const x = (p, i) => G + (t1 > t0 ? (p.t - t0) / (t1 - t0) : (points.length > 1 ? i / (points.length - 1) : 0.5)) * (W - G - D);
    const y = (v) => Hh + (1 - (v - lo) / (hi - lo)) * (H - Hh - B);
    const fmt = (v) => nombre(Math.round(v * 1000) / 1000);
    const pts = points.map((p, i) => [x(p, i), y(p.v)]);
    let svg = '<svg class="dp-al-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Évolution sur le dossier">'
      + '<line class="grille" x1="' + G + '" x2="' + (W - D) + '" y1="' + y(hi) + '" y2="' + y(hi) + '"/>'
      + '<line class="grille" x1="' + G + '" x2="' + (W - D) + '" y1="' + y(lo) + '" y2="' + y(lo) + '"/>'
      + '<text x="' + (G - 6) + '" y="' + (y(hi) + 3) + '" text-anchor="end">' + fmt(hi) + '</text>'
      + '<text x="' + (G - 6) + '" y="' + (y(lo) + 3) + '" text-anchor="end">' + fmt(lo) + '</text>'
      + '<text x="' + G + '" y="' + (H - 3) + '">' + esc(dateCourte(points[0].iso).slice(6)) + '</text>'
      + (points.length > 1 ? '<text x="' + (W - D) + '" y="' + (H - 3) + '" text-anchor="end">'
        + esc(dateCourte(points[points.length - 1].iso).slice(6)) + '</text>' : '');
    if (pts.length > 1) {
      const trace = pts.map(q => q[0].toFixed(1) + ',' + q[1].toFixed(1)).join(' ');
      svg += '<polygon class="aire" points="' + pts[0][0].toFixed(1) + ',' + y(lo) + ' ' + trace + ' '
        + pts[pts.length - 1][0].toFixed(1) + ',' + y(lo) + '"/>'
        + '<polyline class="ligne" points="' + trace + '"/>';
    }
    points.forEach((p, i) => {
      const titre = esc(fmt(p.v) + (unite ? ' ' + unite : '') + ' · ' + dateCourte(p.iso) + (p.qui ? ' · ' + p.qui : ''));
      svg += '<circle class="cible" cx="' + pts[i][0].toFixed(1) + '" cy="' + pts[i][1].toFixed(1) + '" r="10"><title>' + titre + '</title></circle>'
        + '<circle class="pt" cx="' + pts[i][0].toFixed(1) + '" cy="' + pts[i][1].toFixed(1) + '" r="4"><title>' + titre + '</title></circle>';
    });
    return svg + '</svg>';
  }
  function alertesHtml(alertes) {
    if (!alertes || !alertes.length) return '<div class="dp-vide" style="font-size:13px;margin-bottom:14px">Aucune alerte validée sur ce dossier.</div>';
    const parAlerte = {};
    alertes.forEach(a => { (parAlerte[a.alert_id || a.nom] = parAlerte[a.alert_id || a.nom] || []).push(a); });
    const teintes = ['var(--accent)', 'var(--c4)', 'var(--c2)', 'var(--warn)', 'var(--c3)'];
    let ng = 0;
    const teinte = () => ' style="--c:' + teintes[(ng++) % teintes.length] + '"';
    let h = '<div class="dp-al">';
    Object.keys(parAlerte).forEach(k => {
      const acks = parAlerte[k];
      const items = (acks[acks.length - 1].items || []);
      h += '<div class="dp-al-bloc"><div class="dp-al-nom">' + esc(acks[0].nom)
        + '<span>' + acks.length + ' validation' + (acks.length > 1 ? 's' : '') + ' · '
        + esc(dateCourte(acks[0].ack_at)) + (acks.length > 1 ? ' → ' + esc(dateCourte(acks[acks.length - 1].ack_at)) : '') + '</span></div>'
        + '<div class="dp-al-grille">';
      items.forEach((it, idx) => {
        const cle = String(idx);
        if (it.type === 'value') {
          const pts = acks.map(a => ({v: nombreFr((a.reponses || {})[cle]), iso: a.ack_at,
            t: Date.parse(String(a.ack_at || '').replace(' ', 'T')) || 0, qui: a.user_nom || ''})).filter(p => p.v !== null);
          if (!pts.length) return;
          const der = pts[pts.length - 1].v;
          h += '<div class="dp-al-g"' + teinte() + '><div class="dp-al-g-lib">' + esc(it.label || 'Valeur')
            + '<span>dernière <b>' + nombre(der) + (it.unit ? ' ' + esc(it.unit) : '') + '</b></span></div>'
            + courbe(pts, it.unit || '') + '</div>';
        } else {
          const comptes = {};
          acks.forEach(a => {
            let r = (a.reponses || {})[cle];
            (Array.isArray(r) ? r : (r == null || r === '' ? [] : [r])).forEach(v => { comptes[v] = (comptes[v] || 0) + 1; });
          });
          const nc = new Set(it.nc_responses || []);
          const cles = Object.keys(comptes);
          if (!cles.length) return;
          h += '<div class="dp-al-g" style="--c:var(--success)"><div class="dp-al-g-lib">' + esc(it.label || 'Contrôle') + '</div><div class="dp-al-choix">'
            + cles.sort((a, b) => comptes[b] - comptes[a]).map(v => '<span class="dp-al-c' + (nc.has(v) ? ' nc' : '') + '">'
              + esc(v) + (nc.has(v) ? ' · NC' : '') + ' <b>×' + comptes[v] + '</b></span>').join('')
            + '</div></div>';
        }
      });
      h += '</div>';
      const coms = acks.filter(a => (a.commentaire || '').trim());
      if (coms.length) h += '<div style="margin-top:8px;font-size:12px;color:var(--text2)">'
        + coms.map(a => '<div>' + esc(dateCourte(a.ack_at)) + ' · ' + esc(a.user_nom || '') + ' : « ' + esc(a.commentaire) + ' »</div>').join('') + '</div>';
      h += '</div>';
    });
    return h + '</div>';
  }

  // ── Théorique (devis) contre réel ───────────────────────────────────────
  // Même calcul que la Rentabilité (`comparaison_pour_dossier`), lu tel quel :
  // l'écart vient du serveur, l'écran ne fait que dire s'il est bon ou non.
  // Un temps plus court est bon ; une vitesse ou une quantité plus haute aussi.
  // Écart rendu par le serveur, coloré selon le sens qui est bon.
  function ecartHtml(ec, cle, plusEstMieux) {
    const t = (ec || {})[cle];
    if (!t) return '<span class="dp-vide">—</span>';
    const n = parseFloat(String(t).replace(',', '.'));
    const sens = !isFinite(n) || n === 0 ? '' : ((n > 0) === plusEstMieux ? ' bon' : ' mauvais');
    return '<span class="dp-ec' + sens + '">' + esc(t) + '</span>';
  }
  function devisSource(c) {
    const dv = c.devis || {};
    return 'Devis' + (dv.client ? ' ' + esc(dv.client) : '') + (dv.date_devis ? ' du ' + esc(String(dv.date_devis).slice(0, 10).split('-').reverse().join('/')) : '')
      + (c.palier && Number(c.palier.qte_retenue) > 0 ? ' · recalé sur ' + nombre(c.palier.qte_retenue) + ' étiquettes' : '');
  }
  function devisConclusion(c) {
    const concl = c.conclusion || {};
    const coul = {success: 'var(--success)', warn: 'var(--warn)', danger: 'var(--danger)'}[concl.color] || 'var(--muted)';
    return concl.label ? '<span class="dp-cmp-concl" style="--c:' + coul + '">' + esc(concl.label) + '</span>' : '';
  }

  function comparaisonHtml(c) {
    if (!c || !c.theorique || !c.reel) return '';
    const th = c.theorique, re = c.reel, ec = c.ecarts || {};
    const m = (v) => (v == null || v === '' || !isFinite(Number(v))) ? '<span class="dp-vide">—</span>' : nombre(Math.round(Number(v)));
    const dmin = (v) => Number(v || 0) ? duree(v) : '<span class="dp-vide">—</span>';
    const vit = (v) => Number(v || 0) ? nombre(Math.round(Number(v) * 10) / 10) + ' m/min' : '<span class="dp-vide">—</span>';
    const ecart = (cle, plusEstMieux) => ecartHtml(ec, cle, plusEstMieux);
    const ligne = (lib, t, r, e) => '<tr><td style="font-weight:600;color:var(--text)">' + lib + '</td>'
      + '<td class="n">' + t + '</td><td class="n">' + r + '</td><td class="n">' + e + '</td></tr>';
    const dv = c.devis || {};
    const src = 'Devis' + (dv.client ? ' ' + esc(dv.client) : '') + (dv.date_devis ? ' du ' + esc(String(dv.date_devis).slice(0, 10).split('-').reverse().join('/')) : '')
      // Palier retenu : le devis a été recalé sur la quantité réellement commandée.
      + (c.palier && Number(c.palier.qte_retenue) > 0 ? ' · recalé sur ' + nombre(c.palier.qte_retenue) + ' étiquettes' : '');
    const concl = c.conclusion || {};
    const coul = {success: 'var(--success)', warn: 'var(--warn)', danger: 'var(--danger)'}[concl.color] || 'var(--muted)';
    const avert = (c.avertissements || []).map(a => esc(a.message || a.texte || a)).filter(Boolean);
    return '<div class="dp-titre dp-cmp-tete">Théorique vs réel <span class="dp-cmp-src">' + src + '</span>'
      + (concl.label ? '<span class="dp-cmp-concl" style="--c:' + coul + '">' + esc(concl.label) + '</span>' : '') + '</div>'
      + '<div class="dp-wrap"><table class="dp-t"><thead><tr><th></th><th class="n">Théorique</th><th class="n">Réel</th><th class="n">Écart</th></tr></thead><tbody>'
      + ligne('Calage', dmin(th.temps_calage_mn), dmin(re.temps_calage_mn), ecart('temps_calage_mn', false))
      + ligne('Production', dmin(th.temps_production_mn), dmin(re.temps_production_mn), ecart('temps_production_mn', false))
      + ligne('Gâche de calage', th.metrage_calage_ml ? m(th.metrage_calage_ml) + ' m' : m(null),
              re.metrage_calage_ml != null ? m(re.metrage_calage_ml) + ' m' : m(null), ecart('metrage_calage_ml', false))
      + ligne('Métrage', th.metrage_ml ? m(th.metrage_ml) + ' m' : m(null), re.metrage_ml ? m(re.metrage_ml) + ' m' : m(null), ecart('metrage_ml', false))
      + ligne('Étiquettes', m(th.qte_etiquettes), m(re.qte_etiquettes), ecart('qte_etiquettes', true))
      + ligne('Vitesse', vit(th.vitesse), vit(re.vitesse), ecart('vitesse', true))
      + ligne('Vitesse calage compris', vit(th.vitesse_avec_calage), vit(re.vitesse_avec_calage), ecart('vitesse_avec_calage', true))
      + '</tbody></table></div>'
      + (avert.length ? '<div class="dp-avert">' + avert.join(' · ') + '</div>' : '');
  }

  // ── Déroulé : une bande par saisie, de son heure à celle de la suivante ──
  // L'axe ne garde que les jours de production : chaque jour qui a des
  // saisies occupe une plage, de sa première à sa dernière saisie, et les
  // jours se suivent sans la nuit ni le week-end entre eux. Une saisie dont
  // la suivante tombe un autre jour s'arrête là : la nuit n'est ni du
  // calage, ni de la production.
  const JOURS_COURTS = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
  function friseHtml(saisies, alertes) {
    const rows = (saisies || []).filter(r => r && r.date_operation)
      .slice().sort((a, b) => String(a.date_operation).localeCompare(String(b.date_operation)));
    if (rows.length < 2) return '';
    const ms = (iso) => new Date(String(iso || '').replace(' ', 'T').slice(0, 19)).getTime();
    const t = (r) => ms(r.date_operation);
    const jour = (iso) => String(iso || '').slice(0, 10);

    // Plages de jour : bornes, puis largeur proportionnelle à leur durée.
    const plages = [];
    rows.forEach(r => {
      const j = jour(r.date_operation), v = t(r);
      if (!isFinite(v)) return;
      const p = plages[plages.length - 1];
      if (p && p.j === j) p.f = v; else plages.push({j: j, d: v, f: v});
    });
    plages.forEach(p => { p.dur = Math.max(p.f - p.d, 60000); });
    const total = plages.reduce((s, p) => s + p.dur, 0);
    if (!total) return '';
    let cumul = 0;
    plages.forEach(p => { p.x = cumul / total * 100; p.w = p.dur / total * 100; cumul += p.dur; });
    const pos = (v, j) => {
      const p = plages.filter(q => q.j === j)[0];
      if (!p || v < p.d || v > p.f) return null;
      return p.x + (v - p.d) / p.dur * p.w;
    };

    let bandes = '';
    for (let i = 0; i < rows.length - 1; i++) {
      const a = rows[i], b = rows[i + 1];
      if (jour(a.date_operation) !== jour(b.date_operation)) continue;
      const xa = pos(t(a), jour(a.date_operation)), xb = pos(t(b), jour(b.date_operation));
      if (xa == null || xb == null || !(xb > xa)) continue;
      const x = xa, w = xb - xa;
      const c = (DP_CATS[String(a.operation_category || '').toLowerCase()] || [null, 'var(--muted)'])[1];
      const lib = libelleOperation(a);
      // Bulle ancrée à gauche ou à droite près des bords : centrée, elle
      // déborderait de la carte.
      const cote = x + w / 2 < 18 ? ' class="g"' : (x + w / 2 > 82 ? ' class="d"' : '');
      bandes += '<i' + cote + ' style="left:' + x.toFixed(3) + '%;width:' + w.toFixed(3) + '%;--c:' + c + '" data-bulle="'
        + esc(lib + '\n'
          + dateCourte(a.date_operation).slice(6) + ' → ' + dateCourte(b.date_operation).slice(6)
          + ' · ' + duree((t(b) - t(a)) / 60000) + (a.operateur ? '\n' + a.operateur : ''))
          .replace(/\n/g, '&#10;') + '"></i>';
    }

    // Repères : le nom du jour au début de sa plage (s'il y en a plusieurs),
    // et des heures pleines là où la plage a la place.
    const plusieurs = plages.length > 1;
    let reperes = '', separations = '';
    plages.forEach((p, k) => {
      const d = new Date(p.d);
      if (plusieurs) {
        reperes += '<span class="dp-frise-jour" style="left:' + p.x.toFixed(2) + '%">'
          + JOURS_COURTS[d.getDay()] + ' ' + String(d.getDate()).padStart(2, '0') + '/'
          + String(d.getMonth() + 1).padStart(2, '0') + '</span>';
        if (k) separations += '<u style="left:' + p.x.toFixed(3) + '%"></u>';
      }
      const places = Math.floor(p.w / 11);
      if (places < 1) return;
      const heures = (p.f - p.d) / 3600000;
      const pas = Math.max(1, Math.ceil(heures / places)) * 3600000;
      const h0 = new Date(p.d); h0.setMinutes(0, 0, 0);
      for (let v = h0.getTime() + 3600000; v < p.f; v += pas) {
        const x = pos(v, p.j);
        if (x == null || x - p.x < (plusieurs ? 9 : 3) || x > 97) continue;
        reperes += '<span style="left:' + x.toFixed(2) + '%">' + String(new Date(v).getHours()).padStart(2, '0') + ':00</span>';
      }
    });

    // Relevés d'alerte : un point à l'heure de la validation, la réponse au
    // survol. Rouge si une réponse est non conforme.
    let points = '';
    (alertes || []).forEach(a => {
      const x = pos(ms(a.ack_at), jour(a.ack_at));
      if (x == null) return;
      const items = a.items || [], rep = a.reponses || {};
      let nc = false;
      const lignes = items.map((it, i) => {
        const r = rep[String(i)];
        const vals = Array.isArray(r) ? r : (r == null || r === '' ? [] : [r]);
        if (!vals.length) return '';
        const ko = vals.some(v => (it.nc_responses || []).indexOf(v) !== -1);
        if (ko) nc = true;
        return (it.label || 'Contrôle') + ' : ' + vals.join(', ') + (it.unit ? ' ' + it.unit : '') + (ko ? ' · NC' : '');
      }).filter(Boolean);
      points += '<b' + (x < 18 ? ' class="g"' : (x > 82 ? ' class="d"' : '')) + ' style="left:' + x.toFixed(3) + '%'
        + (nc ? ';--c:var(--danger)' : '') + '" data-bulle="'
        + esc([(a.nom || 'Alerte') + ' · ' + dateCourte(a.ack_at).slice(6) + (a.user_nom ? ' · ' + a.user_nom : '')]
          .concat(lignes, a.commentaire ? ['« ' + a.commentaire + ' »'] : []).join('\n')).replace(/\n/g, '&#10;')
        + '"></b>';
    });
    return '<div class="dp-titre">Déroulé <span class="dp-cmp-src">' + esc(dateCourte(rows[0].date_operation))
      + ' → ' + esc(dateCourte(rows[rows.length - 1].date_operation))
      + (plusieurs ? ' · ' + plages.length + ' jours de production' : '') + '</span>'
      + '</div>'
      + '<div class="dp-frise">' + bandes + separations + points + '</div><div class="dp-frise-axe">' + reperes + '</div>';
  }

  // Fiche dossier de MyProd : durée / métrage / vitesse, puis calage /
  // production / arrêts, chacun avec la valeur du devis rattaché s'il y en a un.
  function cartesFicheHtml(d) {
    const st = d.stats || {}, tt = st.temps_totaux || {}, q = st.quantites || {};
    const c = d.comparaison && d.comparaison.theorique && d.comparaison.reel ? d.comparaison : null;
    const th = c ? c.theorique : {}, ec = c ? (c.ecarts || {}) : {};
    const carte = (lib, val, coul, sub) => '<div class="dp-carte" style="--c:' + coul + '">'
      + '<div class="dp-carte-lib">' + lib + '</div><div class="dp-carte-val">' + val + '</div>'
      + (sub ? '<div class="dp-carte-sub">' + sub + '</div>' : '') + '</div>';
    const vit = (v) => nombre(Math.round(Number(v) * 10) / 10) + ' m/min';
    const devis = (v, fmt, cle, plusEstMieux) => (c && Number(v || 0))
      ? 'Devis ' + fmt(v) + ' · ' + ecartHtml(ec, cle, plusEstMieux) : '';
    return (c ? '<div class="dp-devis">' + devisSource(c) + devisConclusion(c) + '</div>' : '')
      + '<div class="dp-cartes dp-3">'
      + carte('Durée totale', duree(tt.duree_totale_min), 'var(--text2)')
      + carte('Métrage', q.metrage_m ? nombre(Math.round(q.metrage_m)) + ' m' : '—', d.alerte ? 'var(--danger)' : 'var(--accent)',
        devis(th.metrage_ml, (v) => nombre(Math.round(v)) + ' m', 'metrage_ml', false))
      + carte('Vitesse', st.vitesse_aberrante ? '<span style="color:var(--danger);font-weight:400">erreur saisie</span>'
          : st.vitesse_m_min ? vit(st.vitesse_m_min) : '—', 'var(--accent)', devis(th.vitesse, vit, 'vitesse', true))
      + '</div><div class="dp-cartes dp-3">'
      + carte('Calage', duree(tt.calage_min), DP_CATS.calage[1], devis(th.temps_calage_mn, duree, 'temps_calage_mn', false))
      + carte('Production', duree(tt.production_min), DP_CATS.production[1],
        devis(th.temps_production_mn, duree, 'temps_production_mn', false))
      + carte('Arrêts', duree(tt.arret_min), DP_CATS.arret[1])
      + '</div>';
  }

  // Format, laize et matière du dossier : ce qui décrit le produit fabriqué.
  function identiteHtml(id) {
    if (!id) return '';
    const puce = (lib, v) => v ? '<span><em>' + lib + '</em>' + esc(v) + '</span>' : '';
    const h = puce('Format', String(id.format || '').replace(/(\d+)\.0\b/g, '$1')) + puce('Laize', id.laize_mm ? nombre(id.laize_mm) + ' mm' : '')
      + puce('Matière', id.matiere);
    return h ? '<div class="dp-ident">' + h + '</div>' : '';
  }

  // `opts.fiche` : fiche dossier de MyProd — cartes resserrées, devis dans
  // les cartes, déroulé des saisies.
  function prodHtml(d, opts) {
    const fiche = !!(opts && opts.fiche);
    const st = d.stats || {};
    const tt = st.temps_totaux || {};
    const q = st.quantites || {};
    const carte = (lib, val, c) => '<div class="dp-carte"' + (c ? ' style="--c:' + c + '"' : '') + '>'
      + '<div class="dp-carte-lib">' + lib + '</div><div class="dp-carte-val">' + val + '</div></div>';
    const vide = '<span class="dp-vide">—</span>';
    const dur = (m) => Number(m || 0) ? duree(m) : vide;
    let h = '<style>' + DP_CSS + '</style><div class="dp">';
    if (d.alerte) h += '<div class="dp-alerte">' + esc(d.alerte.charAt(0).toUpperCase() + d.alerte.slice(1)) + '.</div>';
    if (fiche) h += identiteHtml(d.identite) + cartesFicheHtml(d) + friseHtml(d.saisies, d.alertes);
    else h += '<div class="dp-cartes">'
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
    if (!fiche) h += comparaisonHtml(d.comparaison);
    // Caché par défaut : la page qui l'affiche pose un bouton qui le déplie
    // (MySifaDonneesProd.basculerAlertes). Sans liste d'alertes, rien.
    if (Array.isArray(d.alertes)) {
      h += '<div class="dp-alertes" hidden><div class="dp-titre">Alertes validées <span class="dp-n">'
        + d.alertes.length + '</span></div>' + alertesHtml(d.alertes) + '</div>';
    }

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
    // Colonnes utiles seulement : la machine si le dossier en a connu
    // plusieurs. Un seul compteur :
    // celui du début sur le 01, celui de la fin sur le 89.
    const multiMachine = new Set(rows.map(r => r.machine || '')).size > 1;
    h += '<div class="dp-wrap dp-haut"><table class="dp-t dp-saisies"><thead><tr>'
      + '<th>Date</th><th>Opération</th><th>Opérateur</th>' + (multiMachine ? '<th>Machine</th>' : '')
      + '<th class="n">Compteur</th><th>Commentaire</th>'
      + '</tr></thead><tbody>'
      + rows.map(r => {
        const code = String(r.operation_code || '');
        const borne = code === '01' || code === '89';
        const c = (DP_CATS[String(r.operation_category || '').toLowerCase()] || [null, 'var(--muted)'])[1];
        const cpt = (v) => v ? '<span class="dp-cpt">' + nombre(v) + '</span>' : '';
        // La saisie qui clôture le dossier se lit « Dossier clôturé », pas
        // « Fin de production » suivi d'un badge.
        const libelle = r.fin_dossier ? 'Dossier clôturé' : libelleOperation(r);
        return '<tr' + (borne ? ' class="dp-borne"' : '') + '>'
          + '<td>' + esc(dateCourte(r.date_operation)) + '</td>'
          // Le libellé dans la pastille de couleur : le numéro d'opération
          // ne dit rien à l'opérateur qui relit sa saisie.
          + '<td><span class="dp-code" style="--c:' + (borne ? 'var(--text)' : c) + '">' + esc(libelle) + '</span>'
          + '</td>'
          + '<td>' + esc(r.operateur || '') + '</td>' + (multiMachine ? '<td>' + esc(r.machine || '') + '</td>' : '')
          + '<td class="n">' + (code === '01' && r.metrage_prevu ? '<span class="dp-cpt-lib">début</span>' + cpt(r.metrage_prevu)
            : code === '89' && r.metrage_reel ? '<span class="dp-cpt-lib">fin</span>' + cpt(r.metrage_reel) : '') + '</td>'
          + '<td class="dp-com">' + esc(r.commentaire || '') + '</td></tr>';
      }).join('')
      + '</tbody></table></div></div>';
    return h;
  }

  function basculerAlertes(panneau, ouvert) {
    const z = panneau && panneau.querySelector('.dp-alertes');
    if (!z) return false;
    z.hidden = (ouvert === undefined) ? !z.hidden : !ouvert;
    return !z.hidden;
  }

  window.MySifaDonneesProd = { html: prodHtml, basculerAlertes: basculerAlertes, css: DP_CSS };
})();
