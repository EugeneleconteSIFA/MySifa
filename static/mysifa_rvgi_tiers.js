/* Clients et fournisseurs : ce que RVGI en dit, dans les Paramètres MySifa.
 *
 * Ce fichier est autonome — aucune dépendance à l'intérieur de settings_page.
 * Il expose `MysRvgiTiers`, et la page l'appelle en trois endroits :
 *
 *     MysRvgiTiers.barre(el, 'client'|'fournisseur', onFini)
 *         le bandeau d'état + le bouton de synchro + « à confirmer »
 *     MysRvgiTiers.badge(fiche)
 *         la pastille d'origine, pour une ligne de liste
 *     MysRvgiTiers.bloc(el, perimetre, fiche, onFini)
 *         le bloc de la fiche : lien, valeurs RVGI, contacts, adresses
 *
 * Le reste de la page ne change pas de comportement. C'est délibéré : le
 * référentiel fournisseurs est lu par une trentaine de modules, et la
 * consigne était que tout continue à fonctionner exactement comme avant.
 */
(function (global) {
  'use strict';

  var CSS = [
    '.rt-barre{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:11px 14px;',
    '  border:1px solid var(--border);border-radius:12px;background:var(--bg);margin-bottom:14px}',
    '.rt-barre .rt-t{font-size:12.5px;font-weight:700;display:flex;align-items:center;gap:7px}',
    '.rt-barre .rt-s{font-size:12px;color:var(--muted);flex:1 1 240px;min-width:0}',
    '.rt-barre .rt-a{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto}',
    '.rt-chip{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:2px 9px;',
    '  font-size:11px;font-weight:700;white-space:nowrap;border:1px solid transparent}',
    '.rt-chip.erp{background:rgba(34,211,238,.14);color:var(--accent);border-color:rgba(34,211,238,.32)}',
    '.rt-chip.att{background:rgba(234,179,8,.16);color:#a16207;border-color:rgba(234,179,8,.35)}',
    '.rt-chip.loc{background:rgba(148,163,184,.18);color:var(--muted);border-color:rgba(148,163,184,.35)}',
    '.rt-chip.blo{background:rgba(248,113,113,.15);color:#f87171;border-color:rgba(248,113,113,.35)}',
    /* Le bloc RVGI d'une fiche */
    '.rt-bloc{border:1px solid var(--border);border-radius:12px;background:var(--card);overflow:hidden;margin-bottom:14px}',
    '.rt-tete{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;background:var(--bg);',
    '  border-bottom:1px solid var(--border)}',
    '.rt-tete .n{font-size:12.5px;font-weight:800}',
    '.rt-tete .m{font-size:11.5px;color:var(--muted);font-family:ui-monospace,Menlo,Consolas,monospace}',
    '.rt-corps{padding:12px 14px}',
    '.rt-grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:2px 20px}',
    '.rt-l{display:flex;gap:12px;padding:6px 0;font-size:12.5px;border-bottom:1px solid var(--border)}',
    '.rt-l .k{color:var(--muted);flex:0 0 45%}',
    '.rt-l .v{margin-left:auto;text-align:right;font-weight:600;word-break:break-word}',
    '.rt-l .v.vide{color:var(--muted);font-weight:400}',
    '.rt-note{font-size:11.5px;color:var(--muted);margin:0 0 10px;line-height:1.5}',
    '.rt-cad{border:1px dashed var(--border);border-radius:10px;padding:12px;color:var(--muted);font-size:12.5px}',
    /* Recherche d'une fiche RVGI à lier */
    '.rt-rech{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}',
    '.rt-rech input{flex:1;min-width:200px;padding:8px 11px;border-radius:9px;border:1.5px solid var(--border);',
    '  background:var(--bg);color:var(--text);font:inherit;font-size:13px;outline:none}',
    '.rt-res{border:1px solid var(--border);border-radius:10px;overflow:hidden;max-height:260px;overflow-y:auto}',
    '.rt-res .r{display:flex;align-items:center;gap:10px;padding:8px 12px;font-size:12.5px;cursor:pointer;',
    '  border-bottom:1px solid var(--border)}',
    '.rt-res .r:last-child{border-bottom:none}',
    '.rt-res .r:hover{background:rgba(34,211,238,.08)}',
    '.rt-res .r .num{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent);font-weight:700;flex:0 0 auto}',
    '.rt-res .r .rs{flex:1 1 0;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}',
    '.rt-res .r .vi{flex:0 0 auto;color:var(--muted);font-size:11.5px}',
    /* Tableau générique du module (à confirmer, RVGI seuls, contacts) */
    '.rt-tab{width:100%;border-collapse:collapse;font-size:12.5px}',
    '.rt-tab th{text-align:left;padding:8px 10px;font-size:10px;font-weight:800;letter-spacing:.5px;',
    '  text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap}',
    '.rt-tab td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}',
    '.rt-tab tr:last-child td{border-bottom:none}',
    '.rt-tab .mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}',
    '.rt-tab .dim{color:var(--muted)}',
    '.rt-vs{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}',
    '.rt-vs .c{min-width:0}',
    '.rt-vs .h{font-size:10px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;color:var(--muted);margin-bottom:2px}',
    /* Un candidat de mapping : le radio et sa fiche, cliquables ensemble. */
    '.rt-cand{display:flex;align-items:flex-start;gap:8px;padding:4px 0;cursor:pointer;line-height:1.45}',
    '.rt-cand + .rt-cand{border-top:1px dashed var(--border)}',
    '.rt-cand input{margin-top:3px;flex:0 0 auto;accent-color:var(--accent)}',
    '.rt-cand:hover{color:var(--text)}',
    '.rt-cand .dim{display:block}',
    '@media (max-width:640px){.rt-vs{grid-template-columns:1fr}}',
    /* Fond de dialogue du module */
    '.rt-fond{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:900;display:flex;',
    '  align-items:center;justify-content:center;padding:18px}',
    '.rt-boite{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;',
    '  width:min(980px,96vw);max-height:92vh;overflow:auto}',
    '.rt-boite h3{margin:0 0 4px;font-size:16px}',
  ].join('');

  function styles() {
    if (document.getElementById('rt-css')) return;
    var s = document.createElement('style');
    s.id = 'rt-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function nb(v) {
    var n = Number(v);
    return isFinite(n) ? n.toLocaleString('fr-FR') : String(v == null ? '—' : v);
  }
  function quand(s) {
    var m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if (!m) return String(s || '').slice(0, 10).split('-').reverse().join('/');
    return m[3] + '/' + m[2] + '/' + m[1] + ' à ' + m[4] + 'h' + m[5];
  }
  async function api(url, opts) {
    var r = await fetch(url, Object.assign({ credentials: 'include' }, opts || {}));
    if (!r.ok) {
      var m = 'Erreur ' + r.status;
      try { var j = await r.json(); m = j.detail || m; } catch (e) {}
      throw new Error(m);
    }
    return r.json();
  }
  function post(url, corps) {
    return api(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: corps === undefined ? undefined : JSON.stringify(corps),
    });
  }

  var LABELS = {
    client: { un: 'client', des: 'clients', le: 'Le client' },
    fournisseur: { un: 'fournisseur', des: 'fournisseurs', le: 'Le fournisseur' },
  };

  // ── La pastille d'origine ────────────────────────────────────────────────
  //
  // Trois états, et ils ne disent pas la même chose. « ERP » : la fiche est
  // pilotée par RVGI. « À confirmer » : un rapprochement est proposé, personne
  // ne l'a validé — donc RVGI ne la pilote PAS encore. « MySifa » : saisie ici,
  // et rien ne viendra l'écraser.

  function badge(f) {
    if (!f) return '';
    var e = f.rvgi_etat || 'manuel';
    if (e === 'lie') {
      var bloque = f.rvgi_bloq === 2;
      return '<span class="rt-chip erp" title="Fiche pilotée par RVGI n° ' + esc(f.rvgi_numero) +
             (f.rvgi_maj_le ? ' — mise à jour le ' + esc(quand(f.rvgi_maj_le)) : '') + '">RVGI ' +
             esc(f.rvgi_code || f.rvgi_numero) + '</span>' +
             (bloque ? '<span class="rt-chip blo" title="Bloqué dans l\'ERP">bloqué</span>' : '');
    }
    if (e === 'a_confirmer') {
      return '<span class="rt-chip att" title="Un rapprochement RVGI est proposé et attend une validation">à confirmer</span>';
    }
    return '<span class="rt-chip loc" title="Fiche créée dans MySifa, sans équivalent RVGI">MySifa</span>';
  }

  // ── Le bandeau au-dessus d'une liste ─────────────────────────────────────

  async function barre(el, perimetre, onFini) {
    styles();
    if (!el) return;
    var L = LABELS[perimetre] || LABELS.client;
    el.className = 'rt-barre';
    el.innerHTML = '<span class="rt-s">Lecture de RVGI…</span>';
    var e;
    try { e = await api('/api/rvgi-tiers/etat?perimetre=' + perimetre); }
    catch (err) {
      el.innerHTML = '<span class="rt-t">RVGI</span><span class="rt-s">' + esc(err.message) + '</span>';
      return;
    }
    if (!e.disponible) {
      el.innerHTML = '<span class="rt-t">RVGI</span><span class="rt-s">' +
                     esc(e.raison || 'Miroir indisponible.') + '</span>';
      return;
    }

    var att = e.a_confirmer || 0;
    var seuls = e.rvgi_seuls || 0;
    // Pas de bouton de synchro, et c'est voulu : l'alignement tourne après
    // chaque reconstruction du miroir, sans que personne y pense. Le bandeau
    // dit quand ça a eu lieu, pas comment le déclencher.
    var derniere = e.derniere_synchro && e.derniere_synchro.lance_le;
    el.innerHTML =
      '<span class="rt-t">' + esc(L.des.charAt(0).toUpperCase() + L.des.slice(1)) + ' RVGI</span>' +
      '<span class="rt-s">' + nb(e.lies) + ' fiche' + (e.lies > 1 ? 's' : '') + ' pilotée' +
        (e.lies > 1 ? 's' : '') + ' par l\'ERP sur ' + nb(e.mysifa_total) +
        (e.manuels ? ' · ' + nb(e.manuels) + ' propre' + (e.manuels > 1 ? 's' : '') + ' à MySifa' : '') +
        (derniere ? ' · aligné le ' + esc(quand(derniere))
                  : (e.miroir ? ' · miroir relevé le ' + esc(quand(e.miroir)) : '')) +
        '</span>' +
      '<span class="rt-a">' +
        (seuls ? '<button type="button" class="btn btn-sec btn-sm" data-rt="seuls">' +
                 nb(seuls) + ' dans RVGI seulement</button>' : '') +
        '<button type="button" class="btn' + (att ? '' : ' btn-sec') + ' btn-sm" data-rt="map">' +
        (att ? nb(att) + ' à relier' : 'Relier à RVGI') + '</button>' +
      '</span>';

    el.querySelector('[data-rt="map"]').addEventListener('click', function () {
      ouvrirMapping(perimetre, function () { barre(el, perimetre, onFini); if (onFini) onFini(); });
    });
    var b2 = el.querySelector('[data-rt="seuls"]');
    if (b2) b2.addEventListener('click', function () {
      ouvrirRvgiSeuls(perimetre, function () { barre(el, perimetre, onFini); if (onFini) onFini(); });
    });
  }

  // Le toast de la page si elle en a un, sinon rien de bloquant : une alerte
  // modale au milieu d'une synchro serait pire que le silence.
  function dire(msg, erreur) {
    if (typeof global.showToast === 'function') { global.showToast(msg, erreur ? 'error' : undefined); return; }
    if (typeof global.toast === 'function') { global.toast(msg); return; }
    if (erreur) alert(msg); else console.log('[RVGI] ' + msg);
  }

  // ── Le dialogue « à confirmer » ──────────────────────────────────────────
  //
  // Un rapprochement se juge en voyant les deux fiches l'une en face de
  // l'autre. Un score seul ne dit rien : c'est le SIRET, la ville et le nom
  // qui tranchent.

  function fond(html) {
    styles();
    var f = document.createElement('div');
    f.className = 'rt-fond';
    f.innerHTML = '<div class="rt-boite">' + html + '</div>';
    f.addEventListener('mousedown', function (ev) { if (ev.target === f) f.remove(); });
    document.addEventListener('keydown', function esc_(ev) {
      if (ev.key === 'Escape') { f.remove(); document.removeEventListener('keydown', esc_); }
    });
    document.body.appendChild(f);
    return f;
  }

  async function ouvrirMapping(perimetre, onFini) {
    var L = LABELS[perimetre] || LABELS.client;
    var f = fond('<h3>Relier les fiches à RVGI</h3>' +
      '<p class="rt-note">L\'alignement tourne tout seul après chaque synchro et ' +
      'pose les liens certains — SIRET, code ERP, nom identique. Ce qui reste est ' +
      'ici : soit un candidat proposé qui attend un accord, soit une fiche MySifa ' +
      'qui <b>ressemble</b> à une fiche RVGI sans y être identique. ' +
      'Un lien confirmé rend la fiche pilotée par l\'ERP ; un lien faux ferait ' +
      'écraser cette fiche par les données d\'un autre ' + esc(L.un) + '.</p>' +
      '<div id="rt-map-corps">Lecture de RVGI…</div>' +
      '<div style="display:flex;justify-content:flex-end;margin-top:14px">' +
      '<button type="button" class="btn btn-sec btn-sm" data-rt="fermer">Fermer</button></div>');
    f.querySelector('[data-rt="fermer"]').addEventListener('click', function () {
      f.remove(); if (onFini) onFini();
    });
    var corps = f.querySelector('#rt-map-corps');
    var r;
    try { r = await api('/api/rvgi-tiers/a-mapper?perimetre=' + perimetre); }
    catch (e) { corps.innerHTML = '<div class="rt-cad">' + esc(e.message) + '</div>'; return; }
    if (!r.lignes.length) {
      corps.innerHTML = '<div class="rt-cad">Tout est relié. Les fiches restantes ' +
        'sont propres à MySifa — aucune fiche RVGI ne leur ressemble.</div>';
      return;
    }

    corps.innerHTML = '<table class="rt-tab"><thead><tr>' +
      '<th style="width:34%">Fiche MySifa</th><th>Fiche RVGI</th>' +
      '<th style="width:1px"></th></tr></thead><tbody>' +
      r.lignes.map(function (x, i) {
        var m = x.mysifa;
        return '<tr data-i="' + i + '">' +
          '<td><div style="font-weight:700">' + esc(m.nom || '—') +
            (x.origine === 'suggere'
              ? ' <span class="rt-chip att">ressemblance</span>'
              : ' <span class="rt-chip erp">proposé</span>') + '</div>' +
            '<div class="dim mono">' + esc(m.siret || 'sans SIRET') +
            (m.ville ? ' · ' + esc(m.ville) : '') + '</div></td>' +
          '<td>' + (x.candidats.length
            ? x.candidats.map(function (c, j) {
                return '<label class="rt-cand"><input type="radio" name="c' + i + '" ' +
                  'value="' + esc(c.numero) + '"' + (j === 0 ? ' checked' : '') + '>' +
                  '<span><b>' + esc(c.rs || '—') + '</b>' +
                  (c.actif ? '' : ' <span class="rt-chip blo">bloqué</span>') +
                  '<span class="dim mono"> n° ' + esc(c.numero) +
                  (c.code ? ' · ' + esc(c.code) : '') +
                  (c.siret ? ' · ' + esc(c.siret) : '') +
                  (c.ville ? ' · ' + esc(c.ville) : '') +
                  (c.motif === 'siret' ? ' · même SIRET'
                    : (c.score ? ' · ' + Math.round(c.score * 100) + ' %' : '')) +
                  '</span></span></label>';
              }).join('')
            : '<span class="dim">candidat introuvable dans le miroir</span>') +
          '</td>' +
          '<td style="white-space:nowrap">' +
            (x.candidats.length
              ? '<button type="button" class="btn btn-sm" data-rt="oui">Relier</button> ' : '') +
            '<button type="button" class="btn btn-sec btn-sm" data-rt="non">Aucune</button>' +
          '</td></tr>';
      }).join('') + '</tbody></table>';

    corps.querySelectorAll('tr[data-i]').forEach(function (tr) {
      var x = r.lignes[Number(tr.getAttribute('data-i'))];
      var oui = tr.querySelector('[data-rt="oui"]');
      if (oui) oui.addEventListener('click', function () {
        var choisi = tr.querySelector('input[type=radio]:checked');
        decider(tr, perimetre, x.id, choisi ? Number(choisi.value) : null);
      });
      // « Aucune » n'est pas un rejet définitif : la fiche reste propre à
      // MySifa, et la synchro suivante ne la reproposera pas puisqu'aucun
      // lien certain n'existe. Elle réapparaîtra ici si l'ERP change.
      tr.querySelector('[data-rt="non"]').addEventListener('click', function () {
        decider(tr, perimetre, x.id, null);
      });
    });
  }

  async function decider(tr, perimetre, fiche_id, rvgi_numero) {
    tr.querySelectorAll('button, input').forEach(function (b) { b.disabled = true; });
    try {
      await post('/api/rvgi-tiers/lier',
                 { perimetre: perimetre, fiche_id: fiche_id, rvgi_numero: rvgi_numero });
      tr.style.opacity = '.45';
      tr.querySelector('td:last-child').innerHTML =
        '<span class="rt-chip ' + (rvgi_numero ? 'erp">reliée' : 'loc">laissée à MySifa') + '</span>';
    } catch (e) {
      dire(e.message, true);
      tr.querySelectorAll('button, input').forEach(function (b) { b.disabled = false; });
    }
  }

  // ── Le dialogue « dans RVGI seulement » ──────────────────────────────────

  async function ouvrirRvgiSeuls(perimetre, onFini) {
    var L = LABELS[perimetre] || LABELS.client;
    var f = fond('<h3>Dans RVGI, pas encore dans MySifa</h3>' +
      '<p class="rt-note">La synchro reprend d\'elle-même les fiches actives. ' +
      'Celles qui restent ici sont bloquées dans l\'ERP, ou portent un nom déjà ' +
      'utilisé. Cochez celles dont vous avez besoin.</p>' +
      '<div class="rt-rech"><input type="search" id="rt-s-q" placeholder="Rechercher un ' + esc(L.un) + '…">' +
      '<label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px">' +
      '<input type="checkbox" id="rt-s-bl"> voir aussi les bloqués</label></div>' +
      '<div id="rt-s-corps">Chargement…</div>' +
      '<div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px">' +
      '<button type="button" class="btn btn-sec btn-sm" data-rt="fermer">Fermer</button>' +
      '<button type="button" class="btn btn-sm" data-rt="imp" disabled>Importer la sélection</button></div>');
    f.querySelector('[data-rt="fermer"]').addEventListener('click', function () {
      f.remove(); if (onFini) onFini();
    });
    var corps = f.querySelector('#rt-s-corps');
    var champ = f.querySelector('#rt-s-q');
    var bl = f.querySelector('#rt-s-bl');
    var bouton = f.querySelector('[data-rt="imp"]');
    var minuteur = null;

    async function peindre() {
      corps.innerHTML = 'Chargement…';
      var r;
      try {
        r = await api('/api/rvgi-tiers/rvgi-seuls?perimetre=' + perimetre +
                      '&q=' + encodeURIComponent(champ.value.trim()) +
                      '&inclure_bloques=' + (bl.checked ? '1' : '0'));
      } catch (e) { corps.innerHTML = '<div class="rt-cad">' + esc(e.message) + '</div>'; return; }
      if (!r.lignes.length) {
        corps.innerHTML = '<div class="rt-cad">Rien à importer' +
          (champ.value.trim() ? ' pour « ' + esc(champ.value.trim()) + ' »' : '') + '.</div>';
        majBouton();
        return;
      }
      corps.innerHTML = '<table class="rt-tab"><thead><tr><th style="width:1px"></th>' +
        '<th>N°</th><th>Raison sociale</th><th>Ville</th><th>SIRET</th><th>État</th>' +
        '</tr></thead><tbody>' + r.lignes.map(function (x) {
          return '<tr><td><input type="checkbox" data-num="' + x.numero + '"></td>' +
            '<td class="mono">' + esc(x.code || x.numero) + '</td>' +
            '<td style="font-weight:600">' + esc(x.rs || '—') + '</td>' +
            '<td class="dim">' + esc([x.cp, x.ville].filter(Boolean).join(' ') || '—') + '</td>' +
            '<td class="mono dim">' + esc(x.siret || '—') + '</td>' +
            '<td>' + (x.actif ? '<span class="rt-chip erp">actif</span>'
                              : '<span class="rt-chip blo">bloqué</span>') + '</td></tr>';
        }).join('') + '</tbody></table>';
      corps.querySelectorAll('input[data-num]').forEach(function (c) {
        c.addEventListener('change', majBouton);
      });
      majBouton();
    }

    function coches() {
      return Array.prototype.slice.call(corps.querySelectorAll('input[data-num]:checked'))
        .map(function (c) { return Number(c.getAttribute('data-num')); });
    }
    function majBouton() {
      var n = coches().length;
      bouton.disabled = !n;
      bouton.textContent = n ? 'Importer ' + n + ' fiche' + (n > 1 ? 's' : '') : 'Importer la sélection';
    }

    champ.addEventListener('input', function () { clearTimeout(minuteur); minuteur = setTimeout(peindre, 250); });
    bl.addEventListener('change', peindre);
    bouton.addEventListener('click', async function () {
      bouton.disabled = true;
      try {
        var r = await post('/api/rvgi-tiers/importer', { perimetre: perimetre, numeros: coches() });
        dire(nb(r.importes) + ' fiche(s) importée(s) depuis RVGI.');
        await peindre();
        if (onFini) onFini();
      } catch (e) { dire(e.message, true); bouton.disabled = false; }
    });
    peindre();
  }

  // ── Le bloc RVGI d'une fiche ─────────────────────────────────────────────

  var TITRES_CLIENT = [
    ['code', 'Code ERP'], ['rs', 'Raison sociale'], ['adr1', 'Adresse'],
    ['adr2', 'Adresse (suite)'], ['cp', 'Code postal'], ['vil', 'Ville'],
    ['pays', 'Pays'], ['siret', 'SIRET'], ['ntva', 'TVA intracom.'],
    ['rcs', 'RCS'], ['tel', 'Téléphone'], ['fax', 'Télécopie'], ['mail', 'E-mail'],
    ['_groupe', 'Groupe'], ['_representant', 'Représentant'], ['nbjliv', 'Délai (jours)'],
  ];
  var TITRES_FOU = [
    ['code', 'Code ERP'], ['rs', 'Raison sociale RVGI'], ['adr1', 'Adresse'],
    ['cp', 'Code postal'], ['vil', 'Ville'], ['pays', 'Pays'], ['siret', 'SIRET'],
    ['ntva', 'TVA intracom.'], ['rcs', 'RCS'], ['tel', 'Téléphone'],
    ['fax', 'Télécopie'], ['mail', 'E-mail'], ['_groupe', 'Groupe'],
    ['nbjliv', 'Délai (jours)'], ['http', 'Site'],
  ];

  async function bloc(el, perimetre, fiche, onFini) {
    styles();
    if (!el) return;
    var L = LABELS[perimetre] || LABELS.client;
    var lie = fiche && fiche.rvgi_etat === 'lie' && fiche.rvgi_numero;

    if (!lie) {
      el.className = 'rt-bloc';
      el.innerHTML = '<div class="rt-tete"><span class="n">RVGI</span>' +
        badge(fiche) + '</div><div class="rt-corps">' +
        '<p class="rt-note">Cette fiche n\'est pas pilotée par l\'ERP : ce qui est saisi ici y reste. ' +
        'La relier à une fiche RVGI rendra son identité et ses coordonnées ' +
        'à l\'ERP, qui les réécrira à chaque synchro.</p>' +
        '<div class="rt-rech"><input type="search" data-rt="q" placeholder="Chercher un ' +
        esc(L.un) + ' dans RVGI (nom ou code)…"></div>' +
        '<div data-rt="res"></div></div>';
      brancherRecherche(el, perimetre, fiche, onFini);
      return;
    }

    el.className = 'rt-bloc';
    el.innerHTML = '<div class="rt-tete"><span class="n">Fiche RVGI</span>' + badge(fiche) +
      '<span class="m">n° ' + esc(fiche.rvgi_numero) + '</span>' +
      (fiche.rvgi_maj_le ? '<span class="m">reprise le ' + esc(quand(fiche.rvgi_maj_le)) + '</span>' : '') +
      '<span style="margin-left:auto"><button type="button" class="btn btn-sec btn-sm" data-rt="detacher">' +
      'Détacher</button></span></div><div class="rt-corps">Lecture de RVGI…</div>';

    el.querySelector('[data-rt="detacher"]').addEventListener('click', function () {
      if (!confirm('Détacher cette fiche de RVGI ?\n\nSes champs redeviennent modifiables ' +
                   'dans MySifa, et la synchro ne les touchera plus.')) return;
      post('/api/rvgi-tiers/lier', { perimetre: perimetre, fiche_id: fiche.id, rvgi_numero: null })
        .then(function () { dire('Fiche détachée de RVGI.'); if (onFini) onFini(); })
        .catch(function (e) { dire(e.message, true); });
    });

    var corps = el.querySelector('.rt-corps');
    var r;
    try {
      r = await api('/api/rvgi-tiers/fiche?perimetre=' + perimetre + '&numero=' + fiche.rvgi_numero);
    } catch (e) { corps.innerHTML = '<div class="rt-cad">' + esc(e.message) + '</div>'; return; }

    var f = r.fiche || {};
    var titres = perimetre === 'client' ? TITRES_CLIENT : TITRES_FOU;
    var lignes = titres.map(function (t) {
      var v = f[t[0]];
      var vide = v == null || v === '' || v === 0;
      return '<div class="rt-l"><span class="k">' + esc(t[1]) + '</span>' +
             '<span class="v' + (vide ? ' vide' : '') + '">' + esc(vide ? '—' : v) + '</span></div>';
    }).join('');

    var alerte = '';
    if (f.bloq === 2) {
      alerte = '<div class="rt-cad" style="border-color:rgba(248,113,113,.4);color:#f87171;margin-bottom:10px">' +
               esc(L.le) + ' est bloqué dans RVGI. MySifa ne le désactive pas tout seul — ' +
               'c\'est à vous de décider si vous continuez à travailler avec.</div>';
    }

    // Le nom d'un fournisseur ne se réécrit pas tout seul : trop de modules le
    // joignent en texte. On le propose, avec le contrôle qui va avec.
    var nomDiff = '';
    if (perimetre === 'fournisseur' && f.rs && String(f.rs).trim() !== String(fiche.nom || '').trim()) {
      nomDiff = '<div class="rt-cad" style="margin-bottom:10px">' +
        'MySifa l\'appelle <b>' + esc(fiche.nom) + '</b>, RVGI <b>' + esc(f.rs) + '</b>. ' +
        'Le nom n\'est pas repris automatiquement : plusieurs modules ' +
        '(fabrication, stock, GED) retrouvent ce fournisseur par son nom, et le ' +
        'changer sans le vouloir romprait ces liens. À faire depuis le champ « Nom ».' +
        '</div>';
    }

    corps.innerHTML = alerte + nomDiff +
      '<p class="rt-note">Ces champs sont pilotés par l\'ERP : ' +
      esc((r.champs_pilotes || []).join(', ')) +
      '. Ils sont réécrits à chaque synchro — les modifier ici ne servirait à rien.</p>' +
      '<div class="rt-grille">' + lignes + '</div>' +
      '<div data-rt="plus" style="margin-top:12px"></div>';

    var plus = corps.querySelector('[data-rt="plus"]');
    if (perimetre === 'fournisseur') chargerContacts(plus, fiche.rvgi_numero);
    else chargerAdresses(plus, fiche.rvgi_numero);
  }

  function brancherRecherche(el, perimetre, fiche, onFini) {
    var champ = el.querySelector('[data-rt="q"]');
    var res = el.querySelector('[data-rt="res"]');
    var minuteur = null;
    champ.addEventListener('input', function () {
      clearTimeout(minuteur);
      minuteur = setTimeout(async function () {
        var q = champ.value.trim();
        if (q.length < 2) { res.innerHTML = ''; return; }
        var r;
        try { r = await api('/api/rvgi-tiers/candidats?perimetre=' + perimetre + '&q=' + encodeURIComponent(q)); }
        catch (e) { res.innerHTML = '<div class="rt-cad">' + esc(e.message) + '</div>'; return; }
        if (!r.candidats.length) {
          res.innerHTML = '<div class="rt-cad">Aucune fiche RVGI ne correspond. ' +
            'Le miroir a jusqu\'à douze heures de retard : une fiche créée ce matin ' +
            'dans l\'ERP peut ne pas y être encore.</div>';
          return;
        }
        res.innerHTML = '<div class="rt-res">' + r.candidats.map(function (c) {
          return '<div class="r" data-num="' + c.numero + '">' +
            '<span class="num">' + esc(c.code || c.numero) + '</span>' +
            '<span class="rs">' + esc(c.rs || '—') + '</span>' +
            '<span class="vi">' + esc(c.ville || '') + (c.actif ? '' : ' · bloqué') + '</span>' +
            '</div>';
        }).join('') + '</div>';
        res.querySelectorAll('.r[data-num]').forEach(function (d) {
          d.addEventListener('click', function () {
            var num = Number(d.getAttribute('data-num'));
            post('/api/rvgi-tiers/lier', { perimetre: perimetre, fiche_id: fiche.id, rvgi_numero: num })
              .then(function () {
                dire('Fiche reliée à RVGI. Elle sera reprise à la prochaine synchro.');
                if (onFini) onFini();
              })
              .catch(function (e) { dire(e.message, true); });
          });
        });
      }, 260);
    });
  }

  // Les interlocuteurs RVGI d'un fournisseur. On ne les fusionne pas dans les
  // contacts MySifa : celle-ci est tenue à la main, avec ses langues et ses
  // destinataires d'AO. On les montre, c'est déjà ce qui manquait.
  async function chargerContacts(el, numero) {
    var r;
    try { r = await api('/api/rvgi-tiers/contacts?numero=' + numero); }
    catch (e) { return; }
    if (!r.contacts.length) return;
    el.innerHTML = '<div class="rt-tete" style="border-top:1px solid var(--border);margin:0 -14px;padding:9px 14px">' +
      '<span class="n">Interlocuteurs dans RVGI</span><span class="m">' + r.contacts.length + '</span></div>' +
      '<table class="rt-tab"><thead><tr><th>Nom</th><th>Service</th><th>Téléphone</th><th>E-mail</th></tr></thead>' +
      '<tbody>' + r.contacts.map(function (c) {
        return '<tr><td style="font-weight:600">' +
          esc([c.prenom, c.nom].filter(Boolean).join(' ') || '—') +
          (c.principal ? ' <span class="rt-chip erp">principal</span>' : '') + '</td>' +
          '<td class="dim">' + esc(c.service || '—') + '</td>' +
          '<td class="mono">' + esc(c.tel || c.gsm || '—') + '</td>' +
          '<td class="mono">' + esc(c.mail || '—') + '</td></tr>';
      }).join('') + '</tbody></table>';
  }

  // Les adresses de livraison d'un client : 6 186 dans le miroir, et c'est
  // exactement ce que MyExpé cherche au moment de préparer un départ.
  async function chargerAdresses(el, numero) {
    var r;
    try { r = await api('/api/rvgi-tiers/adresses?numero=' + numero); }
    catch (e) { return; }
    if (!r.adresses.length) return;
    el.innerHTML = '<div class="rt-tete" style="border-top:1px solid var(--border);margin:0 -14px;padding:9px 14px">' +
      '<span class="n">Adresses de livraison RVGI</span><span class="m">' + r.adresses.length + '</span></div>' +
      '<table class="rt-tab"><thead><tr><th>N°</th><th>Destinataire</th><th>Adresse</th><th>Contact</th></tr></thead>' +
      '<tbody>' + r.adresses.map(function (a) {
        return '<tr><td class="mono dim">' + esc(a.numadr) + '</td>' +
          '<td style="font-weight:600">' + esc(a.rs || '—') + '</td>' +
          '<td>' + esc([a.adr1, a.adr2].filter(Boolean).join(', ') || '—') +
          '<div class="dim">' + esc([a.cp, a.ville, a.pays].filter(Boolean).join(' ')) + '</div></td>' +
          '<td class="dim">' + esc(a.contact || '—') +
          (a.contact_mail ? '<div class="mono">' + esc(a.contact_mail) + '</div>' : '') + '</td></tr>';
      }).join('') + '</tbody></table>';
  }

  global.MysRvgiTiers = {
    barre: barre, badge: badge, bloc: bloc,
    mapping: ouvrirMapping, rvgiSeuls: ouvrirRvgiSeuls,
    estPilote: function (f) { return !!(f && f.rvgi_etat === 'lie' && f.rvgi_numero); },
  };
})(window);
