/* ────────────────────────────────────────────────────────────────────
 * MySifa — Memoire produit (front partage)
 *
 * Un seul objet : la reference produit. Trois portes d'entree :
 *   - Saisieprod  : bouton « Historique », visible seulement si la reference
 *                   a deja ete produite  → openHistorique(noDossier)
 *   - MyProd      : liste des produits et fiche complete
 *                   → openListe() / openFiche(ref)
 *   - MyProd      : file des scans d'OF a rattacher
 *                   → openRattachement()
 *
 * Volontairement autonome : pas de dependance a window.__prodCore ni au
 * moteur de rendu de Saisieprod. Le meme fichier est charge par /prod et
 * par /fabrication, et les deux pages voient exactement la meme fiche.
 * ──────────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var OVERLAY_ID = 'pmem-overlay';
  var STYLE_ID = 'pmem-style';

  // ── Helpers ────────────────────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'className') n.className = v;
      else if (k === 'html') n.innerHTML = v;
      else if (k === 'text') n.textContent = v;
      else if (k.indexOf('on') === 0 && typeof v === 'function') n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v);
    });
    (children || []).forEach(function (c) {
      if (c == null || c === false) return;
      n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return n;
  }

  function fNum(v, dec) {
    if (v == null || v === '') return '—';
    var n = parseFloat(v);
    if (isNaN(n)) return '—';
    return n.toLocaleString('fr-FR', {
      minimumFractionDigits: dec || 0, maximumFractionDigits: dec == null ? 0 : dec,
    });
  }

  function fMin(v) {
    if (v == null) return '—';
    var m = Math.round(parseFloat(v));
    if (isNaN(m)) return '—';
    if (m < 60) return m + ' mn';
    return Math.floor(m / 60) + ' h ' + String(m % 60).padStart(2, '0');
  }

  function fDate(s) {
    if (!s) return '—';
    var d = String(s).slice(0, 10).split('-');
    if (d.length !== 3) return String(s).slice(0, 10);
    return d[2] + '/' + d[1] + '/' + d[0];
  }

  function toast(msg, type) {
    if (typeof window.showToast === 'function') { window.showToast(msg, type || 'info'); return; }
    if (window.__prodCore && typeof window.__prodCore.toast === 'function') {
      window.__prodCore.toast(msg, type || 'info'); return;
    }
    var t = el('div', { className: 'pmem-toast' + (type === 'danger' ? ' is-danger' : ''), text: msg });
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }

  async function api(path, options) {
    var opts = Object.assign({ credentials: 'same-origin' }, options || {});
    opts.headers = Object.assign({}, opts.headers || {});
    if (opts.body && !(opts.body instanceof FormData) && !opts.headers['Content-Type']) {
      opts.headers['Content-Type'] = 'application/json';
    }
    var r = await fetch(path, opts);
    var data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (!r.ok) {
      var msg = (data && (data.detail || data.message)) || ('Erreur ' + r.status);
      if (typeof msg !== 'string') msg = 'Erreur ' + r.status;
      throw new Error(msg);
    }
    return data;
  }

  // ── Styles ─────────────────────────────────────────────────────────
  // Aucune couleur en dur : uniquement les variables du design system, pour
  // que le theme clair reste juste sans double maintenance.
  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = [
      '.pmem-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2200;display:flex;',
      'align-items:flex-start;justify-content:center;padding:24px 16px;box-sizing:border-box;overflow-y:auto}',
      '.pmem-panel{background:var(--card);border:1px solid var(--border);border-radius:14px;',
      'width:100%;max-width:980px;box-sizing:border-box;display:flex;flex-direction:column;',
      'max-height:calc(100vh - 48px);overflow:hidden}',
      '.pmem-hd{display:flex;align-items:flex-start;gap:14px;padding:18px 22px 14px;',
      'border-bottom:1px solid var(--border);flex-shrink:0}',
      '.pmem-hd-main{flex:1;min-width:0}',
      '.pmem-ref{font-size:17px;font-weight:800;color:var(--accent);letter-spacing:.3px}',
      '.pmem-desig{font-size:13px;color:var(--text2);margin-top:3px;overflow:hidden;text-overflow:ellipsis}',
      '.pmem-sub{font-size:12px;color:var(--muted);margin-top:6px;display:flex;flex-wrap:wrap;gap:4px 14px}',
      '.pmem-x{background:var(--bg);border:1px solid var(--border);color:var(--text2);border-radius:10px;',
      'width:34px;height:34px;cursor:pointer;font-size:19px;line-height:1;font-family:inherit;flex-shrink:0}',
      '.pmem-x:hover{color:var(--text);border-color:var(--accent)}',
      '.pmem-tabs{display:flex;gap:6px;padding:12px 22px 0;flex-shrink:0;flex-wrap:wrap}',
      '.pmem-tab{background:var(--bg);border:1px solid var(--border);color:var(--text2);',
      'border-radius:10px 10px 0 0;padding:9px 15px;font-size:13px;font-weight:700;cursor:pointer;',
      'font-family:inherit;border-bottom-color:transparent}',
      '.pmem-tab:hover{color:var(--text);border-color:var(--accent)}',
      '.pmem-tab.is-on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      '.pmem-body{padding:18px 22px 22px;overflow-y:auto;flex:1}',
      '.pmem-empty{text-align:center;color:var(--muted);font-size:13px;padding:36px 12px}',
      '.pmem-card{background:var(--bg);border:1px solid var(--border);border-radius:12px;',
      'padding:14px 16px;margin-bottom:10px}',
      '.pmem-card-hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}',
      '.pmem-card-date{font-size:13px;font-weight:800;color:var(--text)}',
      '.pmem-card-meta{font-size:12px;color:var(--muted)}',
      '.pmem-kpis{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:4px}',
      '.pmem-kpi{display:flex;flex-direction:column;gap:1px}',
      '.pmem-kpi-lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}',
      '.pmem-kpi-val{font-size:14px;font-weight:800;color:var(--text)}',
      '.pmem-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}',
      '.pmem-chip{font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px;',
      'background:var(--card);border:1px solid var(--border);color:var(--text2)}',
      '.pmem-chip.is-warn{border-color:var(--warn);color:var(--warn)}',
      '.pmem-chip.is-accent{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      '.pmem-note{background:var(--bg);border:1px solid var(--border);border-left:3px solid var(--accent);',
      'border-radius:10px;padding:12px 14px;margin-bottom:10px}',
      '.pmem-note.is-epingle{border-left-color:var(--warn)}',
      '.pmem-note.is-obsolete{opacity:.55;border-left-color:var(--muted)}',
      '.pmem-note-txt{font-size:13px;line-height:1.55;color:var(--text);white-space:pre-wrap;word-break:break-word}',
      '.pmem-note-ft{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:9px;',
      'font-size:11px;color:var(--muted)}',
      '.pmem-btn{background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:10px;',
      'padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .15s}',
      '.pmem-btn:hover{border-color:var(--accent);color:var(--accent)}',
      '.pmem-btn-sm{padding:5px 10px;font-size:11px;border-radius:8px}',
      '.pmem-btn-accent{background:var(--accent);border-color:var(--accent);color:var(--bg)}',
      '.pmem-btn-accent:hover{filter:brightness(1.06);color:var(--bg)}',
      '.pmem-btn.is-on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      '.pmem-form{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-bottom:14px}',
      '.pmem-form textarea,.pmem-form select,.pmem-input{width:100%;box-sizing:border-box;background:var(--card);',
      'border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;',
      'font-family:inherit;outline:none;transition:border-color .15s}',
      '.pmem-form textarea:focus,.pmem-form select:focus,.pmem-input:focus{border-color:var(--accent)}',
      '.pmem-form-row{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}',
      '.pmem-lbl{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;',
      'color:var(--muted);display:block;margin-bottom:5px}',
      '.pmem-tbl{width:100%;border-collapse:collapse;font-size:13px}',
      '.pmem-tbl th{text-align:left;font-size:10px;font-weight:800;text-transform:uppercase;',
      'letter-spacing:.5px;color:var(--muted);padding:8px 10px;border-bottom:1px solid var(--border)}',
      '.pmem-tbl td{padding:9px 10px;border-bottom:1px solid var(--border);color:var(--text2)}',
      '.pmem-tbl tr{cursor:pointer}',
      '.pmem-tbl tbody tr:hover td{background:var(--accent-bg);color:var(--text)}',
      '.pmem-scroll{overflow-x:auto}',
      '.pmem-split{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:14px}',
      '@media(max-width:820px){.pmem-split{grid-template-columns:1fr}}',
      '.pmem-frame{width:100%;height:460px;border:1px solid var(--border);border-radius:10px;background:var(--bg)}',
      '.pmem-toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:2400;',
      'background:var(--card);border:1px solid var(--accent);color:var(--text);border-radius:10px;',
      'padding:11px 18px;font-size:13px;font-weight:600;box-shadow:0 8px 26px rgba(0,0,0,.28)}',
      '.pmem-toast.is-danger{border-color:var(--danger)}',
      '.pmem-hist-btn{display:inline-flex;align-items:center;gap:6px;background:var(--card);',
      'border:1px solid var(--border);color:var(--text);border-radius:10px;padding:7px 13px;',
      'font-size:12px;font-weight:700;cursor:pointer;font-family:inherit}',
      '.pmem-hist-btn:hover{background:var(--bg);border-color:var(--accent);color:var(--accent)}',
    ].join('');
    document.head.appendChild(s);
  }

  // ── Overlay ────────────────────────────────────────────────────────
  var state = { tab: 'series', data: null, mode: 'fiche', noDossier: null, docs: null, sel: null };

  function close() {
    var ov = document.getElementById(OVERLAY_ID);
    if (ov) ov.remove();
    document.removeEventListener('keydown', onKey);
  }

  function onKey(e) { if (e.key === 'Escape') close(); }

  function mount(node) {
    ensureStyle();
    close();
    var ov = el('div', { className: 'pmem-ov', id: OVERLAY_ID });
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    ov.appendChild(node);
    document.body.appendChild(ov);
    document.addEventListener('keydown', onKey);
  }

  function panel(header, tabs, body) {
    return el('div', { className: 'pmem-panel' }, [header, tabs, el('div', { className: 'pmem-body' }, body)]);
  }

  function header(titre, sousTitre, metas) {
    return el('div', { className: 'pmem-hd' }, [
      el('div', { className: 'pmem-hd-main' }, [
        el('div', { className: 'pmem-ref', text: titre }),
        sousTitre ? el('div', { className: 'pmem-desig', text: sousTitre }) : null,
        (metas && metas.length)
          ? el('div', { className: 'pmem-sub' }, metas.map(function (m) { return el('span', { text: m }); }))
          : null,
      ]),
      el('button', { className: 'pmem-x', type: 'button', title: 'Fermer', onclick: close, text: '×' }),
    ]);
  }

  function tabsBar(items) {
    return el('div', { className: 'pmem-tabs' }, items.map(function (t) {
      return el('button', {
        type: 'button',
        className: 'pmem-tab' + (state.tab === t.key ? ' is-on' : ''),
        onclick: function () { state.tab = t.key; renderCourant(); },
        text: t.label + (t.count != null ? '  (' + t.count + ')' : ''),
      });
    }));
  }

  // ── Rattrapage de l'historique ─────────────────────────────────────
  // Une serie n'existe qu'a partir du moment ou elle a ete figee : au code 89
  // pour les productions a venir, par le rattrapage pour celles d'avant. Tant
  // que le rattrapage n'a pas tourne, une reference qui a pourtant produit
  // parait vide. On le dit, et on donne le bouton a qui peut le lancer.
  var LOT_RATTRAPAGE = 200;

  async function lancerRattrapage(btn) {
    if (btn) btn.disabled = true;
    var reprises = 0, orphelins = 0, tours = 0, offset = 0;
    try {
      // Par lots : sur plusieurs annees d'historique, un rattrapage en une
      // seule requete tiendrait plusieurs minutes et finirait en timeout de
      // passerelle — avec la moitie du travail fait et aucun moyen de le
      // savoir. Chaque lot est commite, donc une interruption ne perd rien.
      while (tours < 100) {
        tours += 1;
        if (btn) btn.textContent = 'Rattrapage… ' + reprises + ' reprise(s)';
        var r = await api('/api/produits/rattrapage?limit=' + LOT_RATTRAPAGE
                          + '&offset=' + offset, { method: 'POST' });
        reprises += r.materialisees || 0;
        orphelins += r.non_rattachables || 0;
        // Les dossiers non rattachables restent candidats a chaque passe : on
        // avance l'offset de leur nombre, sinon le lot suivant retomberait sur
        // eux indefiniment. Un lot incomplet signifie qu'on a tout vu.
        offset += Math.max(0, (r.candidats || 0) - (r.materialisees || 0));
        if (!r.candidats || r.candidats < LOT_RATTRAPAGE) break;
      }
      var msg = reprises + ' production(s) reprise(s)';
      if (orphelins) msg += ' — ' + orphelins + ' dossier(s) rattachables a aucune reference produit';
      toast(msg + '.');
      await recharger();
    } catch (e) {
      toast(e.message || 'Rattrapage impossible.', 'danger');
      if (btn) { btn.disabled = false; btn.textContent = 'Lancer le rattrapage'; }
    }
  }

  function blocRattrapage(d, contexteListe) {
    var n = contexteListe
      ? ((d.couverture && (d.couverture.dossiers_termines - d.couverture.series_materialisees)) || 0)
      : ((d.a_materialiser || []).length);
    if (n <= 0) return null;

    var texte = contexteListe
      ? n + ' dossier(s) termine(s) n\'ont pas encore de fiche produit.'
      : n + ' production(s) de cette reference ont eu lieu, mais ne sont pas encore reprises dans l\'historique.';

    var enfants = [
      el('div', { className: 'pmem-card-hd' }, [
        el('span', { className: 'pmem-card-date', text: 'Historique pas encore repris' }),
      ]),
      el('div', { style: 'font-size:13px;color:var(--text2);line-height:1.6', text: texte }),
      el('div', {
        style: 'font-size:11px;color:var(--muted);margin-top:8px;line-height:1.5',
        text: 'Les productions a venir se rangent toutes seules a la cloture du dossier. '
            + 'Celles d\'avant demandent un rattrapage, a lancer une fois.',
      }),
    ];

    if (d.est_superadmin) {
      var btn = el('button', { type: 'button', className: 'pmem-btn pmem-btn-accent', text: 'Lancer le rattrapage' });
      btn.addEventListener('click', function () { lancerRattrapage(btn); });
      enfants.push(el('div', { className: 'pmem-form-row' }, [btn]));
    } else {
      enfants.push(el('div', {
        style: 'font-size:11px;color:var(--muted);margin-top:10px',
        text: 'Le rattrapage se lance depuis un compte superadmin.',
      }));
    }
    return el('div', { className: 'pmem-card' }, enfants);
  }

  // ── Rendu : series ─────────────────────────────────────────────────
  function renderSeries(d) {
    var series = d.series || [];
    if (!series.length) {
      var diag = blocRattrapage(d, false);
      if (diag) return [diag];
      return [el('div', { className: 'pmem-empty', text: 'Aucune production anterieure enregistree pour cette reference.' })];
    }
    var out = [];
    var med = d.medianes || {};
    if (med.base_series) {
      out.push(el('div', { className: 'pmem-card' }, [
        el('div', { className: 'pmem-card-hd' }, [
          el('span', { className: 'pmem-card-date', text: 'Reperes' }),
          el('span', { className: 'pmem-card-meta', text: 'medianes sur les ' + med.base_series + ' dernieres series' }),
        ]),
        el('div', { className: 'pmem-kpis' }, [
          kpi('Calage', fMin(med.calage_min)),
          kpi('Production', fMin(med.prod_min)),
          kpi('Arrets', fMin(med.arret_min)),
          kpi('Vitesse', med.vitesse_m_min != null ? fNum(med.vitesse_m_min, 1) + ' m/mn' : '—'),
          kpi('Metrage', med.metrage_m != null ? fNum(med.metrage_m) + ' m' : '—'),
        ]),
      ]));
    }
    if ((d.arrets_recurrents || []).length) {
      out.push(el('div', { className: 'pmem-card' }, [
        el('div', { className: 'pmem-card-hd' }, [
          el('span', { className: 'pmem-card-date', text: 'Arrets recurrents' }),
        ]),
        el('div', { className: 'pmem-chips' }, d.arrets_recurrents.map(function (a) {
          var n = a.series, tot = series.length;
          return el('span', {
            className: 'pmem-chip' + (n >= Math.max(2, Math.ceil(tot / 2)) ? ' is-warn' : ''),
            text: (a.label || ('Code ' + a.code)) + ' — ' + n + '/' + tot + ' series · ' + fMin(a.minutes),
          });
        })),
      ]));
    }

    series.forEach(function (s) {
      var arrets = s.arrets_par_code || {};
      var codes = Object.keys(arrets);
      var docs = (d.documents || []).filter(function (x) { return x.no_dossier === s.no_dossier; });
      out.push(el('div', { className: 'pmem-card' }, [
        el('div', { className: 'pmem-card-hd' }, [
          el('span', { className: 'pmem-card-date', text: fDate(s.date_fin || s.date_debut) }),
          el('span', { className: 'pmem-card-meta', text: [s.machine, s.no_dossier, (s.operateurs || []).join(', ')].filter(Boolean).join(' · ') }),
        ]),
        el('div', { className: 'pmem-kpis' }, [
          kpi('Calage', fMin(s.temps_calage_min)),
          kpi('Production', fMin(s.temps_prod_min)),
          kpi('Arrets', fMin(s.temps_arret_min)),
          kpi('Metrage', s.metrage_m != null ? fNum(s.metrage_m) + ' m' : '—'),
          kpi('Vitesse', s.vitesse_m_min != null ? fNum(s.vitesse_m_min, 1) + ' m/mn' : '—'),
          kpi('Etiquettes', s.etiquettes != null ? fNum(s.etiquettes) : '—'),
        ]),
        codes.length ? el('div', { className: 'pmem-chips' }, codes.map(function (c) {
          var a = arrets[c] || {};
          return el('span', { className: 'pmem-chip', text: (a.label || ('Code ' + c)) + ' · ' + fMin(a.minutes) });
        })) : null,
        (s.nb_nc ? el('div', { className: 'pmem-chips' }, [
          el('span', { className: 'pmem-chip is-warn', text: s.nb_nc + ' non-conformite' + (s.nb_nc > 1 ? 's' : '') }),
        ]) : null),
        docs.length ? el('div', { className: 'pmem-chips' }, docs.map(function (doc) {
          return el('button', {
            type: 'button', className: 'pmem-btn pmem-btn-sm',
            onclick: function () { window.open('/api/produits/documents/' + doc.id + '/pdf', '_blank'); },
            text: 'OF scanne' + (doc.of_numero ? ' ' + doc.of_numero : ''),
          });
        })) : null,
      ]));
    });
    return out;
  }

  function kpi(lbl, val) {
    return el('div', { className: 'pmem-kpi' }, [
      el('span', { className: 'pmem-kpi-lbl', text: lbl }),
      el('span', { className: 'pmem-kpi-val', text: val }),
    ]);
  }

  // ── Rendu : savoirs ────────────────────────────────────────────────
  function renderSavoirs(d) {
    var out = [];
    var ref = d.ref_produit_norm;

    var ta = el('textarea', { rows: '3', placeholder: 'Ce qu\'il faut savoir la prochaine fois que cette reference passe…' });
    var sel = el('select', {}, (window.__PMEM_TYPES__ || []).map(function (t) {
      return el('option', { value: t.cle, text: t.label });
    }));
    var btn = el('button', { type: 'button', className: 'pmem-btn pmem-btn-accent', text: 'Enregistrer la note' });
    btn.addEventListener('click', async function () {
      var txt = (ta.value || '').trim();
      if (!txt) { toast('Note vide.', 'danger'); return; }
      btn.disabled = true;
      try {
        await api('/api/produits/' + encodeURI(ref) + '/savoirs', {
          method: 'POST',
          body: JSON.stringify({ texte: txt, type: sel.value, no_dossier: state.noDossier || null }),
        });
        ta.value = '';
        toast('Note enregistree.');
        await recharger();
      } catch (e) { toast(e.message || 'Erreur.', 'danger'); }
      btn.disabled = false;
    });

    out.push(el('div', { className: 'pmem-form' }, [
      el('label', { className: 'pmem-lbl', text: 'Ajouter une note sur ce produit' }),
      ta,
      el('div', { className: 'pmem-form-row' }, [
        el('div', { style: 'flex:1;min-width:160px' }, [sel]),
        btn,
      ]),
      el('div', {
        style: 'font-size:11px;color:var(--muted);margin-top:8px;line-height:1.5',
        text: 'Publiee immediatement. Votre nom et la date restent affiches, et vous pouvez la corriger ou la marquer perimee a tout moment.',
      }),
    ]));

    var savoirs = d.savoirs || [];
    if (!savoirs.length) {
      out.push(el('div', { className: 'pmem-empty', text: 'Aucune note pour l\'instant.' }));
      return out;
    }
    savoirs.forEach(function (s) { out.push(noteCard(s, d)); });
    return out;
  }

  function noteCard(s, d) {
    var actions = [];

    var voteBtn = el('button', {
      type: 'button',
      className: 'pmem-btn pmem-btn-sm' + (s.vote_utilisateur ? ' is-on' : ''),
      text: 'Ca m\'a servi' + (s.utile_count ? ' (' + s.utile_count + ')' : ''),
    });
    voteBtn.addEventListener('click', async function () {
      try {
        await api('/api/produits/savoirs/' + s.id + '/utile', { method: 'POST' });
        await recharger();
      } catch (e) { toast(e.message || 'Erreur.', 'danger'); }
    });
    actions.push(voteBtn);

    // On n'affiche « perimer » qu'a l'auteur et aux admins : le serveur refuse
    // de toute facon, mais un bouton qui echoue systematiquement se lit comme
    // un bug, pas comme une regle.
    var peutEditer = !!d.est_admin || (!!d.moi && s.auteur === d.moi);
    if (peutEditer) {
      var obs = el('button', {
        type: 'button', className: 'pmem-btn pmem-btn-sm',
        text: s.obsolete ? 'Remettre en vigueur' : 'Marquer perimee',
      });
      obs.addEventListener('click', async function () {
        var motif = null;
        if (!s.obsolete) {
          motif = window.prompt('Pourquoi cette note ne vaut-elle plus ? (facultatif)') || '';
        }
        try {
          await api('/api/produits/savoirs/' + s.id + '/obsolete', {
            method: 'POST', body: JSON.stringify({ motif: motif, remettre: !!s.obsolete }),
          });
          await recharger();
        } catch (e) { toast(e.message || 'Erreur.', 'danger'); }
      });
      actions.push(obs);
    }

    return el('div', {
      className: 'pmem-note' + (s.epingle ? ' is-epingle' : '') + (s.obsolete ? ' is-obsolete' : ''),
    }, [
      el('div', { className: 'pmem-chips', style: 'margin-top:0;margin-bottom:8px' }, [
        el('span', { className: 'pmem-chip is-accent', text: s.type_label || 'Autre' }),
        s.machine ? el('span', { className: 'pmem-chip', text: s.machine }) : null,
        s.epingle ? el('span', { className: 'pmem-chip is-warn', text: 'Epinglee' }) : null,
        s.obsolete ? el('span', { className: 'pmem-chip', text: 'Perimee' }) : null,
      ]),
      el('div', { className: 'pmem-note-txt', text: s.texte }),
      s.obsolete && s.obsolete_motif
        ? el('div', { style: 'font-size:11px;color:var(--muted);margin-top:6px', text: 'Motif : ' + s.obsolete_motif })
        : null,
      el('div', { className: 'pmem-note-ft' }, [
        el('span', { text: (s.auteur || '?') + ' · ' + fDate(s.created_at) + (s.no_dossier_source ? ' · dossier ' + s.no_dossier_source : '') }),
        el('span', { style: 'flex:1' }),
      ].concat(actions)),
    ]);
  }

  // ── Rendu : documents ──────────────────────────────────────────────
  function renderDocuments(d) {
    var docs = d.documents || [];
    if (!docs.length) {
      return [el('div', { className: 'pmem-empty', text: 'Aucun OF scanne rattache a cette reference.' })];
    }
    return docs.map(function (doc) {
      return el('div', { className: 'pmem-card' }, [
        el('div', { className: 'pmem-card-hd' }, [
          el('span', { className: 'pmem-card-date', text: 'OF ' + (doc.of_numero || '—') }),
          el('span', {
            className: 'pmem-card-meta',
            text: [doc.no_dossier ? 'dossier ' + doc.no_dossier : null, fDate(doc.importe_le),
                   doc.nb_pages ? doc.nb_pages + ' page' + (doc.nb_pages > 1 ? 's' : '') : null]
              .filter(Boolean).join(' · '),
          }),
        ]),
        el('div', { className: 'pmem-chips' }, [
          el('button', {
            type: 'button', className: 'pmem-btn pmem-btn-sm',
            onclick: function () { window.open('/api/produits/documents/' + doc.id + '/pdf', '_blank'); },
            text: 'Ouvrir le scan',
          }),
        ]),
      ]);
    });
  }

  // ── Rendu courant ──────────────────────────────────────────────────
  function renderCourant() {
    if (state.mode === 'rattachement') { renderRattachement(); return; }
    if (state.mode === 'liste') { renderListe(); return; }

    var d = state.data || {};
    var ident = d.identite || {};
    var metas = [];
    if (d.nb_series) metas.push(d.nb_series + ' production' + (d.nb_series > 1 ? 's' : ''));
    if (d.derniere_production) metas.push('derniere le ' + fDate(d.derniere_production));
    if ((d.machines || []).length) metas.push((d.machines || []).join(', '));
    if ((d.clients || []).length) metas.push((d.clients || []).slice(0, 3).join(', '));

    var body;
    if (state.tab === 'savoirs') body = renderSavoirs(d);
    else if (state.tab === 'documents') body = renderDocuments(d);
    else body = renderSeries(d);

    mount(panel(
      header(d.ref_produit_norm || '—', ident.designation || '', metas),
      tabsBar([
        { key: 'series', label: 'Productions', count: (d.series || []).length },
        { key: 'savoirs', label: 'Notes', count: (d.savoirs || []).length },
        { key: 'documents', label: 'OF scannes', count: (d.documents || []).length },
      ]),
      body
    ));
  }

  async function recharger() {
    if (state.mode === 'liste') { await chargerListe(); return; }
    if (state.mode === 'rattachement') { await chargerDocs(); return; }
    if (state.mode === 'historique' && state.noDossier) {
      state.data = await api('/api/produits/dossier/' + encodeURIComponent(state.noDossier) + '/historique');
    } else if (state.data && state.data.ref_produit_norm) {
      state.data = await api('/api/produits/' + encodeURI(state.data.ref_produit_norm));
    }
    renderCourant();
  }

  async function chargerTypes() {
    if (window.__PMEM_TYPES__) return;
    try {
      var r = await api('/api/produits/savoirs/types');
      window.__PMEM_TYPES__ = (r && r.types) || [];
    } catch (e) { window.__PMEM_TYPES__ = [{ cle: 'autre', label: 'Autre' }]; }
  }

  // ── Portes d'entree ────────────────────────────────────────────────
  async function openHistorique(noDossier) {
    await chargerTypes();
    state = { tab: 'series', data: null, mode: 'historique', noDossier: noDossier, docs: null, sel: null };
    try {
      state.data = await api('/api/produits/dossier/' + encodeURIComponent(noDossier) + '/historique');
    } catch (e) { toast(e.message || 'Historique indisponible.', 'danger'); return; }
    if (!state.data || !state.data.disponible) { toast('Aucun historique pour ce produit.'); return; }
    renderCourant();
  }

  async function openFiche(ref) {
    await chargerTypes();
    state = { tab: 'series', data: null, mode: 'fiche', noDossier: null, docs: null, sel: null };
    try {
      state.data = await api('/api/produits/' + encodeURI(ref));
    } catch (e) { toast(e.message || 'Fiche indisponible.', 'danger'); return; }
    renderCourant();
  }

  // ── Liste des produits ─────────────────────────────────────────────
  async function openListe(q) {
    state = { tab: 'liste', data: null, mode: 'liste', noDossier: null, docs: null, sel: null };
    state.q = q || '';
    await chargerListe();
  }

  async function chargerListe() {
    try {
      state.liste = await api('/api/produits?q=' + encodeURIComponent(state.q || ''));
    } catch (e) { toast(e.message || 'Erreur.', 'danger'); return; }
    renderListe();
  }

  function renderListe() {
    var d = state.liste || { produits: [] };
    var input = el('input', {
      className: 'pmem-input', type: 'text', id: 'pmem-search',
      placeholder: 'Rechercher (reference, designation, client…)', value: state.q || '',
    });
    var t0 = null;
    input.addEventListener('input', function (e) {
      state.q = e.target.value;
      clearTimeout(t0);
      t0 = setTimeout(function () {
        var pos = input.selectionStart;
        chargerListe().then(function () {
          var n = document.getElementById('pmem-search');
          if (n) { n.focus(); try { n.setSelectionRange(pos, pos); } catch (x) {} }
        });
      }, 220);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.stopPropagation(); state.q = ''; input.value = ''; chargerListe(); }
    });

    var rows = (d.produits || []).map(function (p) {
      var tr = el('tr', {}, [
        el('td', {}, [el('strong', { style: 'color:var(--accent)', text: p.ref_produit_norm })]),
        el('td', { text: p.designation || '—' }),
        el('td', { text: String(p.nb_series) }),
        el('td', { text: fDate(p.derniere_production) }),
        el('td', { text: (p.machines || []).join(', ') || '—' }),
        el('td', { text: (p.nb_savoirs || 0) + ' note' + ((p.nb_savoirs || 0) > 1 ? 's' : '') }),
        el('td', { text: (p.nb_documents || 0) + ' scan' + ((p.nb_documents || 0) > 1 ? 's' : '') }),
      ]);
      tr.addEventListener('click', function () { openFiche(p.ref_produit_norm); });
      return tr;
    });

    var table = rows.length
      ? el('div', { className: 'pmem-scroll' }, [
          el('table', { className: 'pmem-tbl' }, [
            el('thead', {}, [el('tr', {}, ['Reference', 'Designation', 'Productions', 'Derniere', 'Machines', 'Notes', 'Scans']
              .map(function (h) { return el('th', { text: h }); }))]),
            el('tbody', {}, rows),
          ]),
        ])
      : el('div', {
          className: 'pmem-empty',
          text: state.q ? ('Aucun resultat pour « ' + state.q + ' »')
                        : 'Aucune reference avec un historique de production.',
        });

    var diagListe = blocRattrapage(d, true);
    mount(panel(
      header('Produits', 'Historique de production par reference', [(d.produits || []).length + ' reference(s)']),
      el('div', { className: 'pmem-tabs' }),
      [el('div', { style: 'margin-bottom:14px' }, [input])]
        .concat(diagListe ? [diagListe] : [])
        .concat([table])
    ));
    requestAnimationFrame(function () {
      var n = document.getElementById('pmem-search');
      if (n && !state.q) n.focus();
    });
  }

  // ── File de rattachement des scans ─────────────────────────────────
  async function openRattachement() {
    state = { tab: 'rattachement', data: null, mode: 'rattachement', noDossier: null, docs: null, sel: null };
    await chargerDocs();
  }

  async function chargerDocs() {
    try {
      var r = await api('/api/produits/documents/a-rattacher');
      state.docs = r.documents || [];
      state.total = r.total || 0;
      if (state.sel && !state.docs.some(function (d) { return d.id === state.sel; })) state.sel = null;
      if (!state.sel && state.docs.length) state.sel = state.docs[0].id;
    } catch (e) { toast(e.message || 'Erreur.', 'danger'); return; }
    renderRattachement();
  }

  function renderRattachement() {
    var docs = state.docs || [];
    if (!docs.length) {
      mount(panel(
        header('Scans a rattacher', 'OF termines dont le numero n\'a pas pu etre lu', []),
        el('div', { className: 'pmem-tabs' }),
        [el('div', { className: 'pmem-empty', text: 'Aucun scan en attente. Tout est rattache.' })]
      ));
      return;
    }

    var liste = el('div', {}, docs.map(function (doc) {
      var on = doc.id === state.sel;
      var b = el('button', {
        type: 'button',
        className: 'pmem-btn' + (on ? ' is-on' : ''),
        style: 'display:block;width:100%;text-align:left;margin-bottom:6px',
      }, [
        el('div', { style: 'font-weight:800', text: doc.fichier_origine || doc.fichier }),
        el('div', {
          style: 'font-size:11px;color:var(--muted);margin-top:3px',
          text: [fDate(doc.importe_le), doc.of_numero ? 'OF lu ' + doc.of_numero : 'numero non lu',
                 doc.texte_extrait ? null : 'sans OCR'].filter(Boolean).join(' · '),
        }),
      ]);
      b.addEventListener('click', function () { state.sel = doc.id; renderRattachement(); });
      return b;
    }));

    var sel = docs.filter(function (d) { return d.id === state.sel; })[0] || docs[0];
    var champ = el('input', {
      className: 'pmem-input', type: 'text', id: 'pmem-dos',
      placeholder: 'Numero de dossier (ex. 9932056)', value: sel.of_numero || '',
    });

    var btnOk = el('button', { type: 'button', className: 'pmem-btn pmem-btn-accent', text: 'Rattacher' });
    btnOk.addEventListener('click', async function () {
      var v = (champ.value || '').trim();
      if (!v) { toast('Numero de dossier requis.', 'danger'); return; }
      btnOk.disabled = true;
      try {
        var r = await api('/api/produits/documents/' + sel.id + '/rattacher', {
          method: 'POST', body: JSON.stringify({ no_dossier: v }),
        });
        toast('Scan rattache a ' + r.ref_produit_norm + '.');
        state.sel = null;
        await chargerDocs();
      } catch (e) { toast(e.message || 'Erreur.', 'danger'); }
      btnOk.disabled = false;
    });

    var btnKo = el('button', { type: 'button', className: 'pmem-btn', text: 'Ecarter' });
    btnKo.addEventListener('click', async function () {
      if (!window.confirm('Ecarter ce scan ? Il reste conserve mais n\'apparaitra plus dans la file.')) return;
      try {
        await api('/api/produits/documents/' + sel.id + '/rattacher', {
          method: 'POST', body: JSON.stringify({ ecarter: true }),
        });
        state.sel = null;
        await chargerDocs();
      } catch (e) { toast(e.message || 'Erreur.', 'danger'); }
    });

    var droite = el('div', {}, [
      el('label', { className: 'pmem-lbl', text: 'Rattacher a un dossier' }),
      champ,
      el('div', { className: 'pmem-form-row' }, [btnOk, btnKo]),
      el('iframe', { className: 'pmem-frame', src: '/api/produits/documents/' + sel.id + '/pdf', style: 'margin-top:12px' }),
    ]);

    mount(panel(
      header('Scans a rattacher', 'OF termines dont le numero n\'a pas pu etre lu automatiquement',
             [state.total + ' en attente']),
      el('div', { className: 'pmem-tabs' }),
      [el('div', { className: 'pmem-split' }, [liste, droite])]
    ));
  }

  // ── Bouton « Historique » pour Saisieprod ──────────────────────────
  // Retourne null quand la reference n'a jamais ete produite : l'appelant
  // n'insere alors rien. Un bouton toujours present qui ouvre « aucune
  // donnee » perd sa credibilite en trois ouvertures.
  function boutonHistorique(apercu, noDossier) {
    if (!apercu || !apercu.disponible) return null;
    ensureStyle();
    var parts = [];
    if (apercu.nb_series) parts.push(apercu.nb_series + ' production' + (apercu.nb_series > 1 ? 's' : ''));
    if (apercu.nb_savoirs) parts.push(apercu.nb_savoirs + ' note' + (apercu.nb_savoirs > 1 ? 's' : ''));
    if (apercu.nb_documents) parts.push(apercu.nb_documents + ' scan' + (apercu.nb_documents > 1 ? 's' : ''));
    var b = el('button', {
      type: 'button', className: 'pmem-hist-btn',
      title: 'Historique de la reference ' + (apercu.ref_produit_norm || ''),
      text: 'Historique — ' + parts.join(' · '),
    });
    b.addEventListener('click', function () { openHistorique(noDossier || apercu.no_dossier); });
    return b;
  }

  // Cle produit normalisee — meme regle que app/services/fiche_ref_parser.py
  // (« 1013/0068 - COHESIO 2 - L570 » et « 1315-0004 » donnent la meme cle que
  // cote serveur). Sert aux onglets OF et Fiches techniques, dont le libelle
  // porte la variante machine ou laize.
  function normRef(value) {
    if (!value) return null;
    var m = /^\s*(\d{1,5})\s*[\/\-]\s*(\d{1,5})/.exec(String(value));
    if (!m) return null;
    var famille = String(parseInt(m[1], 10));
    var numero = m[2];
    if (numero.length < 4) numero = ('0000' + numero).slice(-4);
    return famille + '/' + numero;
  }

  // Petit bouton « Fiche produit » a poser dans une ligne de tableau.
  function boutonFiche(refBrute, opts) {
    var ref = normRef(refBrute);
    if (!ref) return null;
    ensureStyle();
    var o = opts || {};
    var b = el('button', {
      type: 'button',
      className: o.className || 'pmem-btn pmem-btn-sm',
      title: 'Historique de production de ' + ref,
      text: o.label || 'Fiche produit',
    });
    b.addEventListener('click', function (e) { e.stopPropagation(); openFiche(ref); });
    return b;
  }

  window.MySifaProduitMemoire = {
    openHistorique: openHistorique,
    openFiche: openFiche,
    openListe: openListe,
    openRattachement: openRattachement,
    boutonHistorique: boutonHistorique,
    boutonFiche: boutonFiche,
    normRef: normRef,
    fermer: close,
  };
})();
