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
      'border-radius:10px 10px 0 0;padding:10px 17px;font-size:14px;font-weight:700;cursor:pointer;',
      'font-family:inherit;border-bottom-color:transparent}',
      '.pmem-tab:hover{color:var(--text);border-color:var(--accent)}',
      '.pmem-tab.is-on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      '.pmem-body{padding:18px 22px 22px;overflow-y:auto;flex:1}',
      '.pmem-empty{text-align:center;color:var(--muted);font-size:14px;padding:40px 12px}',
      '.pmem-card{background:var(--bg);border:1px solid var(--border);border-radius:12px;',
      'padding:14px 16px;margin-bottom:10px}',
      '.pmem-card-hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}',
      '.pmem-card-date{font-size:14px;font-weight:800;color:var(--text)}',
      '.pmem-card-meta{font-size:13px;color:var(--muted)}',
      '.pmem-kpis{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:4px}',
      // Deux colonnes sans filet ni fond : ce qui les separe est le blanc, pas
      // un trait. Une bordure ferait lire deux blocs distincts la ou il s'agit
      // de deux faces de la meme production.
      '.pmem-serie{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);',
      'gap:14px 30px;margin-top:2px}',
      '@media(max-width:760px){.pmem-serie{grid-template-columns:1fr;gap:16px}}',
      '.pmem-col-lbl{font-size:11px;font-weight:800;text-transform:uppercase;',
      'letter-spacing:.6px;color:var(--muted);margin-bottom:9px}',
      '.pmem-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));',
      'gap:11px 18px}',
      '.pmem-rien{font-size:13px;color:var(--muted);font-style:italic}',
      '.pmem-kpi{display:flex;flex-direction:column;gap:1px}',
      '.pmem-kpi-lbl{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}',
      '.pmem-kpi-val{font-size:16px;font-weight:800;color:var(--text)}',
      '.pmem-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}',
      '.pmem-chip{font-size:12px;font-weight:700;padding:4px 11px;border-radius:20px;',
      'background:var(--card);border:1px solid var(--border);color:var(--text2)}',
      '.pmem-chip.is-warn{border-color:var(--warn);color:var(--warn)}',
      '.pmem-chip.is-accent{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      /* Info prod : le commentaire attache a UN dossier. Il se distingue des
         notes produit (qui valent pour toute la reference) par le libelle et,
         pour le dossier en cours, par la teinte d'alerte — c'est une consigne
         a lire avant de lancer, pas un element d'historique. */
      '.pmem-info{border-left:3px solid var(--accent)}',
      '.pmem-info.is-courant{border-left-color:#fbbf24;background:rgba(251,191,36,.08)}',
      '.pmem-info-txt{font-size:14px;line-height:1.6;color:var(--text);white-space:pre-wrap;word-break:break-word}',
      '.pmem-info-ft{font-size:11px;color:var(--muted);margin-top:7px}',
      '.pmem-serie-info{margin-top:12px;padding-top:11px;border-top:1px solid var(--border)}',
      '.pmem-serie-info .pmem-info-txt{font-size:13px}',
      '.pmem-note{background:var(--bg);border:1px solid var(--border);border-left:3px solid var(--accent);',
      'border-radius:10px;padding:12px 14px;margin-bottom:10px}',
      '.pmem-note.is-epingle{border-left-color:var(--warn)}',
      '.pmem-note.is-obsolete{opacity:.55;border-left-color:var(--muted)}',
      '.pmem-note-txt{font-size:14px;line-height:1.6;color:var(--text);white-space:pre-wrap;word-break:break-word}',
      '.pmem-note-ft{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:10px;',
      'font-size:12px;color:var(--muted)}',
      '.pmem-btn{background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:10px;',
      'padding:8px 14px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .15s}',
      '.pmem-btn:hover{border-color:var(--accent);color:var(--accent)}',
      '.pmem-btn-sm{padding:6px 12px;font-size:12px;border-radius:8px}',
      '.pmem-btn-accent{background:var(--accent);border-color:var(--accent);color:var(--bg)}',
      '.pmem-btn-accent:hover{filter:brightness(1.06);color:var(--bg)}',
      // Ouvrir un document est une action frequente et sans risque : elle se
      // signale par une teinte, pas par un aplat. Un aplat plein a chaque
      // ligne d'un tableau de 461 entrees fait une colonne de pastilles
      // bleues, et plus rien ne ressort.
      '.pmem-btn-doc{background:var(--accent-bg);border-color:transparent;color:var(--accent);',
      'font-weight:800}',
      '.pmem-btn-doc:hover{border-color:var(--accent);color:var(--accent)}',
      '.pmem-btn.is-on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      /* Les deux verdicts portes sur une note ne sont pas symetriques : l'un
         confirme qu'elle sert, l'autre la retire. Une teinte au repos, l'aplat
         au survol — `color:var(--bg)` sur l'aplat reste lisible dans les deux
         themes puisque --bg bascule avec eux. Le bouton de remise en vigueur
         reste neutre : remettre une note n'est pas un geste destructif. */
      '.pmem-btn-ok{background:rgba(52,211,153,.14);border-color:rgba(52,211,153,.55);',
      'color:var(--success)}',
      '.pmem-btn-ok:hover{background:var(--success);border-color:var(--success);color:var(--bg)}',
      '.pmem-btn-ok.is-on{background:var(--success);border-color:var(--success);color:var(--bg)}',
      '.pmem-btn-ko{background:rgba(248,113,113,.14);border-color:rgba(248,113,113,.55);',
      'color:var(--danger)}',
      '.pmem-btn-ko:hover{background:var(--danger);border-color:var(--danger);color:#fff}',
      '.pmem-form{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-bottom:14px}',
      '.pmem-form textarea,.pmem-form select,.pmem-input{width:100%;box-sizing:border-box;background:var(--card);',
      'border:1px solid var(--border);border-radius:10px;padding:11px 14px;color:var(--text);font-size:14px;',
      'font-family:inherit;outline:none;transition:border-color .15s}',
      '.pmem-form textarea:focus,.pmem-form select:focus,.pmem-input:focus{border-color:var(--accent)}',
      '.pmem-form-row{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}',
      '.pmem-lbl{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;',
      'color:var(--muted);display:block;margin-bottom:5px}',
      '.pmem-tablecard{background:var(--card);border:1px solid var(--border);border-radius:12px;',
      'overflow:hidden}',
      '.pmem-tbl{width:100%;border-collapse:collapse;font-size:14px;background:var(--card)}',
      '.pmem-tbl th{text-align:left;font-size:11px;font-weight:800;text-transform:uppercase;',
      'letter-spacing:.5px;color:var(--muted);padding:11px 14px;background:var(--card);',
      'border-bottom:1px solid var(--border)}',
      '.pmem-tbl td{padding:12px 14px;border-bottom:1px solid var(--border);color:var(--text2)}',
      '.pmem-tbl tbody tr:last-child td{border-bottom:none}',
      '.pmem-tbl tbody tr:hover td{background:var(--accent-bg);color:var(--text)}',
      '.pmem-tbl .pmem-chip{font-size:12px}',
      '.pmem-scroll{overflow-x:auto}',
      // Onglets sobres (« Scans d'OF ») : la barre est une SURFACE blanche et
      // l'onglet actif se signale par un trait et du texte fonce. Deux essais
      // ecartes avant celui-ci : un aplat colore par onglet, qui ajoutait une
      // emphase la ou le tableau en dessous en demande deja ; puis des onglets
      // transparents, qui laissaient passer le bleute de MyProd — trois
      // teintes empilees pour une seule zone de lecture.
      '.pmem-tabs.is-sobre{gap:0;background:var(--card);border:1px solid var(--border);',
      'border-radius:12px;padding:3px 16px 0;margin-bottom:14px}',
      '.pmem-tabs.is-sobre .pmem-tab{background:transparent;border:none;border-radius:0;',
      'border-bottom:2px solid transparent;color:var(--muted);padding:10px 2px;margin-right:24px}',
      '.pmem-tabs.is-sobre .pmem-tab:hover{color:var(--text);border-bottom-color:var(--border)}',
      '.pmem-tabs.is-sobre .pmem-tab.is-on{background:transparent;color:var(--text);',
      'border-bottom-color:var(--accent)}',
      // En page, MyProd colle ses propres marges aux onglets : on rend a la
      // barre son cadre complet.
      '.pmem-panel.pmem-inline .pmem-tabs.is-sobre{padding:3px 16px 0;margin-top:4px}',
      // Tableau sobre : le survol et la ligne selectionnee restent des gris,
      // la couleur reste disponible pour ce qui alerte (« non lu »).
      '.pmem-tbl-sobre tbody tr:hover td{background:var(--bg);color:var(--text)}',
      '.pmem-tbl-sobre tbody tr.is-sel td{background:var(--bg);color:var(--text);',
      'box-shadow:inset 2px 0 0 var(--accent)}',
      '.pmem-file-n{font-weight:800;color:var(--text);font-size:13px;word-break:break-word}',
      '.pmem-file-m{font-size:11px;color:var(--muted);margin-top:3px}',
      // Suggestions de dossier : la liste se pose SOUS le champ sans pousser
      // le formulaire, sinon les boutons sautent a chaque frappe.
      '.pmem-sugg-wrap{position:relative}',
      '.pmem-sugg{display:none;position:absolute;left:0;right:0;top:calc(100% + 4px);z-index:30;',
      'background:var(--card);border:1px solid var(--border);border-radius:10px;',
      'box-shadow:0 10px 24px rgba(0,0,0,.18);max-height:280px;overflow-y:auto}',
      '.pmem-sugg.is-open{display:block}',
      '.pmem-sugg-i{display:block;width:100%;text-align:left;background:transparent;border:none;',
      'border-bottom:1px solid var(--border);padding:9px 12px;cursor:pointer;font-family:inherit}',
      '.pmem-sugg-i:last-child{border-bottom:none}',
      '.pmem-sugg-i:hover{background:var(--bg)}',
      '.pmem-sugg-h{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:13px;color:var(--text)}',
      '.pmem-sugg-m{font-size:11px;color:var(--muted);margin-top:3px}',
      '.pmem-sugg-vide{padding:11px 12px;font-size:12px;color:var(--muted)}',
      '.pmem-sugg-note{font-size:12px;color:var(--text2);margin-top:7px;min-height:16px}',
      '.pmem-sugg-note.is-warn{color:var(--warn);font-weight:700}',
      '.pmem-split{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:14px}',
      '@media(max-width:820px){.pmem-split{grid-template-columns:1fr}}',
      '.pmem-frame{width:100%;height:460px;border:1px solid var(--border);border-radius:10px;background:var(--bg)}',
      '.pmem-panel.pmem-inline{max-width:none;max-height:none;border:none;background:transparent}',
      // En page, MyProd affiche deja le titre et le sous-titre : les repeter
      // donnait deux en-tetes identiques l'un sous l'autre.
      '.pmem-panel.pmem-inline .pmem-hd{display:none}',
      '.pmem-panel.pmem-inline .pmem-body{padding:16px 0 0;overflow:visible}',
      '.pmem-panel.pmem-inline .pmem-tabs{padding:12px 0 0}',
      '.pmem-panel.pmem-inline .pmem-x{display:none}',
      '.pmem-drop{border:2px dashed var(--border);border-radius:12px;padding:22px 18px;',
      'text-align:center;background:var(--bg);cursor:pointer;transition:border-color .15s,background .15s;',
      'margin-bottom:14px}',
      '.pmem-drop:hover,.pmem-drop.is-over{border-color:var(--accent);background:var(--accent-bg)}',
      '.pmem-drop-t{font-size:13px;font-weight:800;color:var(--text)}',
      '.pmem-drop-s{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.5}',
      '.pmem-prog{height:6px;border-radius:99px;background:var(--border);overflow:hidden;margin-top:12px}',
      '.pmem-prog-b{height:100%;background:var(--accent);width:0;transition:width .2s}',
      '.pmem-toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:2400;',
      'background:var(--card);border:1px solid var(--accent);color:var(--text);border-radius:10px;',
      'padding:11px 18px;font-size:13px;font-weight:600;box-shadow:0 8px 26px rgba(0,0,0,.28)}',
      '.pmem-toast.is-danger{border-color:var(--danger)}',
      '.pmem-hist-btn{display:inline-flex;align-items:center;gap:8px;background:var(--card);',
      'border:1px solid var(--border);color:var(--text);border-radius:10px;padding:7px 13px;',
      'font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;text-align:left}',
      '.pmem-hist-btn:hover{background:var(--bg);border-color:var(--accent);color:var(--accent)}',
      /* Signalement conducteur : ce produit a deja tourne, il y a quelque chose
         a lire avant de demarrer. Un bouton gris parmi d'autres boutons gris ne
         se voit pas depuis un poste machine. */
      '.pmem-hist-btn.is-signal{border-color:rgba(251,191,36,.55);background:rgba(251,191,36,.12)}',
      '.pmem-hist-btn.is-signal:hover{border-color:#fbbf24;color:var(--text);background:rgba(251,191,36,.18)}',
      '.pmem-hist-pastille{display:inline-flex;align-items:center;justify-content:center;',
      'min-width:20px;height:20px;padding:0 6px;border-radius:999px;background:#fbbf24;',
      'color:#1f2937;font-size:11px;font-weight:800;line-height:1;flex:none}',
      '.pmem-hist-corps{display:flex;flex-direction:column;gap:1px;min-width:0}',
      '.pmem-hist-titre{font-size:12px;font-weight:800}',
      '.pmem-hist-detail{font-size:11px;font-weight:600;color:var(--text2)}',
      '.pmem-hist-tag{font-size:10px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;',
      'color:#fbbf24;flex:none}',
      /* La pulsation s'arrete des que le conducteur a ouvert l'historique de ce
         dossier : un signal qui clignote pour toujours devient du decor. */
      '.pmem-hist-btn.is-neuf{animation:pmem-pulse 2.2s ease-in-out infinite}',
      '@keyframes pmem-pulse{0%,100%{box-shadow:0 0 0 0 rgba(251,191,36,.45)}',
      '50%{box-shadow:0 0 0 7px rgba(251,191,36,0)}}',
      '@media (prefers-reduced-motion:reduce){.pmem-hist-btn.is-neuf{animation:none}}',
      /* Apercu d'un scan. Il se pose PAR-DESSUS le panneau produit sans le
         demonter : on referme, on est revenu exactement ou on en etait — la
         production passee qu'on etait en train de lire. */
      '.pmem-doc-ov{position:fixed;inset:0;background:rgba(0,0,0,.66);z-index:2300;',
      'display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}',
      '.pmem-doc-panel{background:var(--card);border:1px solid var(--border);border-radius:14px;',
      'width:min(1100px,100%);height:100%;display:flex;flex-direction:column;overflow:hidden;',
      'box-shadow:0 24px 64px rgba(0,0,0,.45)}',
      '.pmem-doc-hd{display:flex;align-items:center;gap:12px;padding:11px 14px;',
      'border-bottom:1px solid var(--border);flex-shrink:0}',
      '.pmem-doc-t{font-size:14px;font-weight:800;color:var(--text);white-space:nowrap}',
      '.pmem-doc-m{font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;',
      'white-space:nowrap;min-width:0}',
      // Le PDF occupe toute la bande restante : c'est lui qu'on est venu voir.
      '.pmem-doc-frame{flex:1;width:100%;border:none;background:var(--bg);min-height:0}',
      '.pmem-doc-load{padding:26px 12px;text-align:center;font-size:13px;color:var(--muted)}',
    ].join('');
    document.head.appendChild(s);
  }

  // ── Overlay ────────────────────────────────────────────────────────
  var state = { tab: 'series', data: null, mode: 'fiche', noDossier: null, docs: null, sel: null };

  // Contenant de rendu. `null` = surcouche modale (ouverture depuis un bouton) ;
  // un element = page de MyProd (entree de barre laterale). La vue est
  // construite une seule fois : c'est le contenant qui change, pas l'ecran.
  var contenantInline = null;

  function close() {
    fermerApercuScan();
    var ov = document.getElementById(OVERLAY_ID);
    if (ov) ov.remove();
    document.removeEventListener('keydown', onKey);
  }

  function onKey(e) {
    if (e.key !== 'Escape') return;
    // Un apercu de scan ouvert par-dessus se ferme en premier : Echap ne doit
    // pas renvoyer le conducteur a la case depart en un seul appui.
    if (document.getElementById('pmem-doc-overlay')) return;
    close();
  }

  function mount(node) {
    ensureStyle();
    if (contenantInline) {
      if (!contenantInline.isConnected) { contenantInline = null; }
      else {
        contenantInline.innerHTML = '';
        node.classList.add('pmem-inline');
        contenantInline.appendChild(node);
        return;
      }
    }
    close();
    var ov = el('div', { className: 'pmem-ov', id: OVERLAY_ID });
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    ov.appendChild(node);
    document.body.appendChild(ov);
    document.addEventListener('keydown', onKey);
  }

  // ── Apercu d'un scan, dans MySifa ──────────────────────────────────
  // Ouvrir le PDF dans un onglet coutait plusieurs secondes : Chrome monte une
  // page neuve, charge son lecteur PDF, et l'operateur perd de vue le panneau
  // qu'il lisait. L'apercu se pose ici par-dessus le panneau, dans la meme
  // page ; on le referme et on est revenu ou on en etait.
  var DOC_OV_ID = 'pmem-doc-overlay';
  var docsPrecharges = {};

  function docUrl(id) { return '/api/produits/documents/' + id + '/pdf'; }

  // Le survol precede le clic de quelques centaines de millisecondes : de quoi
  // avoir le fichier en cache avant meme que l'iframe le demande. Le serveur
  // autorise desormais le cache navigateur sur ces scans (ils ne changent
  // jamais), donc la requete n'est faite qu'une fois par document.
  function prechargerScan(id) {
    if (!id || docsPrecharges[id]) return;
    docsPrecharges[id] = true;
    try {
      fetch(docUrl(id), { credentials: 'same-origin', cache: 'force-cache' })
        // Le corps est lu et jete : c'est sa lecture complete qui fait entrer
        // le fichier dans le cache du navigateur. Une reponse laissee en
        // suspens n'y arrive pas.
        .then(function (r) { return r.ok ? r.blob() : null; })
        .then(function () {})
        .catch(function () { docsPrecharges[id] = false; });
    } catch (e) { docsPrecharges[id] = false; }
  }

  function fermerApercuScan() {
    var ov = document.getElementById(DOC_OV_ID);
    if (ov) ov.remove();
    document.removeEventListener('keydown', onDocKey);
  }

  function onDocKey(e) {
    if (e.key !== 'Escape') return;
    // L'apercu se ferme seul : le panneau produit qui est dessous reste ouvert.
    e.stopPropagation();
    fermerApercuScan();
  }

  function apercuScan(doc) {
    if (!doc || !doc.id) return;
    ensureStyle();
    fermerApercuScan();

    var titre = 'OF ' + (doc.of_numero || '—');
    var metas = [doc.no_dossier ? 'dossier ' + doc.no_dossier : null,
                 doc.machine || null, doc.client || null,
                 doc.fichier_origine || null].filter(Boolean).join(' \u00b7 ');

    var frame = el('iframe', {
      className: 'pmem-doc-frame',
      // #view=FitH : la page arrive a la largeur du cadre, sans reglage manuel.
      src: docUrl(doc.id) + '#view=FitH',
      title: 'Scan ' + titre,
    });

    var panneau = el('div', { className: 'pmem-doc-panel' }, [
      el('div', { className: 'pmem-doc-hd' }, [
        el('span', { className: 'pmem-doc-t', text: titre }),
        metas ? el('span', { className: 'pmem-doc-m', text: metas }) : null,
        el('span', { style: 'flex:1' }),
        // La porte de sortie vers l'onglet reste ouverte : impression, zoom au
        // clavier, second ecran — l'apercu ne doit pas retirer ce qui existait.
        el('button', {
          type: 'button', className: 'pmem-btn pmem-btn-sm',
          text: 'Ouvrir dans un onglet',
          onclick: function () { window.open(docUrl(doc.id), '_blank'); },
        }),
        el('button', {
          className: 'pmem-x', type: 'button', title: 'Fermer l\'apercu',
          onclick: fermerApercuScan, text: '\u00d7',
        }),
      ]),
      frame,
    ]);

    var ov = el('div', { className: 'pmem-doc-ov', id: DOC_OV_ID }, [panneau]);
    ov.addEventListener('click', function (e) { if (e.target === ov) fermerApercuScan(); });
    document.body.appendChild(ov);
    document.addEventListener('keydown', onDocKey);
  }

  // Bouton d'ouverture d'un scan — un seul endroit, pour que les trois listes
  // (productions, documents, file de scans) se comportent pareil.
  function boutonScan(doc, label) {
    var b = el('button', {
      type: 'button', className: 'pmem-btn pmem-btn-sm pmem-btn-doc',
      title: 'Apercu du scan dans MySifa',
      text: label || 'Ouvrir le scan',
      onclick: function (e) { e.stopPropagation(); apercuScan(doc); },
    });
    b.addEventListener('mouseenter', function () { prechargerScan(doc.id); });
    b.addEventListener('focus', function () { prechargerScan(doc.id); });
    return b;
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

  // Une serie n'existe qu'a la cloture du dossier. Voir quatre dossiers de la
  // reference au planning et deux lignes ici passe pour une perte de donnees
  // tant que personne ne dit ou sont les deux autres. On le dit.
  function blocDossiersReference(d) {
    var dr = d.dossiers_reference || null;
    if (!dr || !dr.total) return null;
    if (!dr.en_cours && !dr.a_venir) return null;

    var restes = [];
    if (dr.en_cours) restes.push(dr.en_cours + ' en cours de production');
    if (dr.a_venir) restes.push(dr.a_venir + (dr.a_venir > 1 ? ' n\'ont' : ' n\'a') + ' pas encore tourne');

    var produits = dr.produits
      ? (dr.produits + (dr.produits > 1 ? ' ont produit et figurent ci-dessous' : ' a produit et figure ci-dessous'))
      : 'aucun n\'a encore produit';

    return el('div', { className: 'pmem-card' }, [
      el('div', { className: 'pmem-card-hd' }, [
        el('span', { className: 'pmem-card-date', text: 'Dossiers de cette reference' }),
        el('span', { className: 'pmem-card-meta', text: dr.total + ' au planning' }),
      ]),
      el('div', {
        style: 'font-size:13px;color:var(--text2);line-height:1.6',
        text: produits.charAt(0).toUpperCase() + produits.slice(1) + ', ' + restes.join(', ') + '.',
      }),
      el('div', {
        style: 'font-size:11px;color:var(--muted);margin-top:8px;line-height:1.5',
        text: 'Une production n\'entre dans l\'historique qu\'a la cloture du dossier (code 89). '
            + 'Les dossiers en cours ou a venir n\'y sont donc pas encore.',
      }),
    ]);
  }

  // Info prod du dossier ouvert : la consigne qui concerne la production en
  // cours, pas l'historique. Elle passe donc avant tout le reste.
  function blocInfoProdCourant(d) {
    var info = d.info_prod || null;
    if (!info || !info.texte) return null;
    var qui = info.updated_par || info.auteur || '';
    var quand = fDate(info.updated_at || info.created_at);
    var pied = [];
    if (qui) pied.push(qui);
    if (quand && quand !== '—') pied.push(quand);
    return el('div', { className: 'pmem-card pmem-info is-courant' }, [
      el('div', { className: 'pmem-card-hd' }, [
        el('span', { className: 'pmem-card-date', text: 'Info prod de ce dossier' }),
        el('span', { className: 'pmem-card-meta', text: d.no_dossier || '' }),
      ]),
      el('div', { className: 'pmem-info-txt', text: info.texte }),
      pied.length ? el('div', { className: 'pmem-info-ft', text: pied.join(' · ') }) : null,
    ]);
  }

  // Info prod d'une serie passee : ce que le conducteur d'alors a note en
  // cloturant son dossier. Elle se lit sous ses chiffres, dans sa carte.
  function blocInfoProdSerie(s) {
    var txt = (s && s.info_prod) ? String(s.info_prod).trim() : '';
    if (!txt) return null;
    var qui = s.info_prod_par || '';
    return el('div', { className: 'pmem-serie-info' }, [
      el('div', { className: 'pmem-col-lbl', text: 'Info prod' }),
      el('div', { className: 'pmem-info-txt', text: txt }),
      qui ? el('div', { className: 'pmem-info-ft', text: qui }) : null,
    ]);
  }

  // ── Rendu : series ─────────────────────────────────────────────────
  function renderSeries(d) {
    var series = d.series || [];
    var etatDossiers = blocDossiersReference(d);
    var infoCourant = blocInfoProdCourant(d);
    if (!series.length) {
      var tete = [];
      if (infoCourant) tete.push(infoCourant);
      if (etatDossiers) tete.push(etatDossiers);
      var diag = blocRattrapage(d, false);
      if (diag) return tete.concat([diag]);
      if (tete.length) return tete;
      return [el('div', { className: 'pmem-empty', text: 'Aucune production anterieure enregistree pour cette reference.' })];
    }
    var out = [];
    if (infoCourant) out.push(infoCourant);
    if (etatDossiers) out.push(etatDossiers);
    var med = d.medianes || {};
    if (med.base_series) {
      out.push(el('div', { className: 'pmem-card' }, [
        el('div', { className: 'pmem-card-hd' }, [
          el('span', { className: 'pmem-card-date', text: 'Reperes' }),
          el('span', { className: 'pmem-card-meta', text: 'medianes sur les ' + med.base_series + ' dernieres series' }),
        ]),
        el('div', { className: 'pmem-kpis' }, [
          kpi('Calage', fMin(med.calage_min)),
          kpi('Nettoyage', fMin(med.nettoyage_min)),
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
            text: labelArret(a.code, a.label) + ' — ' + n + '/' + tot + ' series · ' + fMin(a.minutes),
          });
        })),
      ]));
    }

    series.forEach(function (s) {
      var arrets = s.arrets_par_code || {};
      var codes = Object.keys(arrets).sort(function (a, b) {
        return ((arrets[b] || {}).minutes || 0) - ((arrets[a] || {}).minutes || 0);
      });
      var docs = (d.documents || []).filter(function (x) { return x.no_dossier === s.no_dossier; });

      // Colonne gauche — ce qui a coince. Vide, elle le dit : « aucun arret »
      // est une information, pas un blanc.
      var gauche = [el('div', { className: 'pmem-col-lbl', text: 'Arrets et erreurs' })];
      if (codes.length) {
        gauche.push(el('div', { className: 'pmem-chips', style: 'margin-top:0' },
          codes.map(function (c) {
            var a = arrets[c] || {};
            return el('span', { className: 'pmem-chip', text: labelArret(c, a.label) + ' · ' + fMin(a.minutes) });
          })));
      }
      if (s.nb_nc) {
        gauche.push(el('div', { className: 'pmem-chips' }, [
          el('span', { className: 'pmem-chip is-warn',
                       text: s.nb_nc + ' non-conformite' + (s.nb_nc > 1 ? 's' : '') }),
        ]));
      }
      if (!codes.length && !s.nb_nc) {
        gauche.push(el('div', { className: 'pmem-rien', text: 'Aucun arret ni non-conformite.' }));
      }

      // Colonne droite — ce que la production a donne.
      var droite = [
        el('div', { className: 'pmem-col-lbl', text: 'Production' }),
        el('div', { className: 'pmem-stats' }, [
          kpi('Calage', fMin(s.temps_calage_min)),
          kpi('Nettoyage', fMin(s.temps_nettoyage_min)),
          kpi('Production', fMin(s.temps_prod_min)),
          kpi('Arrets', fMin(s.temps_arret_min)),
          kpi('Metrage', s.metrage_m != null ? fNum(s.metrage_m) + ' m' : '—'),
          kpi('Vitesse', s.vitesse_m_min != null ? fNum(s.vitesse_m_min, 1) + ' m/mn' : '—'),
          kpi('Etiquettes', s.etiquettes != null ? fNum(s.etiquettes) : '—'),
        ]),
      ];

      // Le scan est une action, pas une donnee : il monte dans l'en-tete.
      var entete = [
        el('span', { className: 'pmem-card-date', text: fDate(s.date_fin || s.date_debut) }),
        el('span', { className: 'pmem-card-meta',
                     text: [s.machine, s.no_dossier, (s.operateurs || []).join(', ')]
                             .filter(Boolean).join(' · ') }),
      ];
      if (docs.length) {
        entete.push(el('span', { style: 'flex:1' }));
        docs.forEach(function (doc) {
          var b = boutonScan(doc, 'Ouvrir le scan' + (doc.of_numero ? ' ' + doc.of_numero : ''));
          // L'en-tete aligne sur la ligne de base : un bouton s'y poserait
          // de travers a cote du texte.
          b.style.alignSelf = 'center';
          entete.push(b);
        });
      }

      out.push(el('div', { className: 'pmem-card' }, [
        el('div', { className: 'pmem-card-hd' }, entete),
        el('div', { className: 'pmem-serie' }, [
          el('div', {}, gauche),
          el('div', {}, droite),
        ]),
        blocInfoProdSerie(s),
      ]));
    });
    return out;
  }

  // Le libelle stocke porte le code en prefixe (« 53 - Casse bande ») parce que
  // c'est ce que l'operateur saisit. Dans la fiche produit, le code n'apprend
  // rien : la puce est deja identifiee par son libelle, et le numero encombre
  // une ligne qui doit se lire d'un coup d'oeil.
  function labelArret(code, label) {
    var s = String(label == null ? '' : label).trim();
    s = s.replace(/^\d{1,3}\s*[-\u2013\u2014.:]\s*/, '').trim();
    return s || ('Code ' + code);
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
    // Sans cle produit, une note n'a nulle part ou s'accrocher : le dossier
    // n'a que son info prod, qui se lit dans l'onglet Productions.
    if (!ref) {
      return [el('div', { className: 'pmem-empty',
        text: 'Ce dossier n\'est rattache a aucune reference produit : les notes partagees ne sont pas disponibles.' })];
    }

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
      className: 'pmem-btn pmem-btn-sm pmem-btn-ok' + (s.vote_utilisateur ? ' is-on' : ''),
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
        type: 'button',
        className: 'pmem-btn pmem-btn-sm' + (s.obsolete ? '' : ' pmem-btn-ko'),
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
      var ops = Array.isArray(doc.serie_operateurs) ? doc.serie_operateurs : [];
      // Ligne du haut : quand, et sur quelle machine. C'est ce qu'on cherche
      // en premier dans une pile de scans.
      var haut = [doc.machine, doc.client].filter(Boolean).join(' · ');
      // Ligne du bas : ce que la production a donne, et de quoi retrouver le
      // dossier papier. Tout vient de la base — rien n'est relu dans le PDF.
      var bas = [];
      if (doc.no_dossier) bas.push('dossier ' + doc.no_dossier);
      if (doc.etiquettes) bas.push(fNum(doc.etiquettes) + ' etiquettes');
      if (doc.serie_metrage_m) bas.push(fNum(doc.serie_metrage_m) + ' m');
      if (doc.of_laize) bas.push('laize ' + fNum(doc.of_laize) + ' mm');
      if (doc.of_format) bas.push(doc.of_format);
      if (ops.length) bas.push(ops.join(', '));
      if (doc.nb_pages) bas.push(doc.nb_pages + ' page' + (doc.nb_pages > 1 ? 's' : ''));

      var enfants = [
        el('div', { className: 'pmem-card-hd' }, [
          el('span', { className: 'pmem-card-date', text: fDate(doc.date_document || doc.importe_le) }),
          el('span', { className: 'pmem-card-meta', text: 'OF ' + (doc.of_numero || '—') }),
          haut ? el('span', { className: 'pmem-card-meta', text: haut }) : null,
        ]),
      ];
      if (bas.length) {
        enfants.push(el('div', {
          style: 'font-size:12px;color:var(--muted);line-height:1.5',
          text: bas.join(' · '),
        }));
      }
      enfants.push(el('div', { className: 'pmem-chips' }, [
        boutonScan(doc, 'Ouvrir le scan'),
        // Le fichier d'origine porte souvent une precision que la base n'a
        // pas (« marche 748 », « L1 », « Reliquat ») : on la garde visible.
        doc.fichier_origine
          ? el('span', { className: 'pmem-chip', title: doc.chemin_origine || '',
                         text: doc.fichier_origine })
          : null,
      ]));
      return el('div', { className: 'pmem-card' }, enfants);
    });
  }

  // ── Rendu courant ──────────────────────────────────────────────────
  function renderCourant() {
    if (state.mode === 'rattachement') { renderScans(); return; }
    if (state.mode === 'liste') { renderListe(); return; }

    var d = state.data || {};
    var ident = d.identite || {};
    var metas = [];
    if (d.nb_series) metas.push(d.nb_series + ' production' + (d.nb_series > 1 ? 's' : ''));
    if (d.derniere_production) metas.push('derniere le ' + fDate(d.derniere_production));
    var dr = d.dossiers_reference || null;
    if (dr && dr.total > (d.nb_series || 0)) metas.push(dr.total + ' dossiers au planning');
    if ((d.machines || []).length) metas.push((d.machines || []).join(', '));
    if ((d.clients || []).length) metas.push((d.clients || []).slice(0, 3).join(', '));

    var body;
    if (state.tab === 'savoirs') body = renderSavoirs(d);
    else if (state.tab === 'documents') body = renderDocuments(d);
    else body = renderSeries(d);

    mount(panel(
      header(d.ref_produit_norm || d.no_dossier || '—', ident.designation || '', metas),
      tabsBar([
        { key: 'series', label: 'Productions', count: (d.series || []).length },
        { key: 'savoirs', label: 'Notes', count: (d.savoirs || []).length },
        { key: 'documents', label: 'OF scannes', count: (d.documents || []).length },
      ]),
      body
    ));
  }

  // Un numero de dossier porte un slash dans la moitie des cas (« 1068/0002 -
  // Reliquat 2 »). Dans le chemin, meme encode en %2F, il est redecode avant le
  // routage : l'appel tombait sur la route fourre-tout de la fiche produit, qui
  // repondait « Aucun dossier de production rattache a la reference
  // dossier/1068/0002 - .../historique ». En parametre de requete, aucun
  // caractere du numero n'a de sens pour le routeur.
  function urlHistorique(noDossier) {
    return '/api/produits/dossier-historique?no_dossier='
         + encodeURIComponent(noDossier || '');
  }

  async function recharger() {
    if (state.mode === 'liste') { await chargerListe(); return; }
    if (state.mode === 'rattachement') { await chargerScans(); return; }
    if (state.mode === 'historique' && state.noDossier) {
      state.data = await api(urlHistorique(state.noDossier));
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
    contenantInline = null;
    await chargerTypes();
    state = { tab: 'series', data: null, mode: 'historique', noDossier: noDossier, docs: null, sel: null };
    try {
      state.data = await api(urlHistorique(noDossier));
    } catch (e) { toast(e.message || 'Historique indisponible.', 'danger'); return; }
    if (!state.data || !state.data.disponible) { toast('Aucun historique pour ce produit.'); return; }
    renderCourant();
  }

  async function openFiche(ref) {
    contenantInline = null;
    await chargerTypes();
    state = { tab: 'series', data: null, mode: 'fiche', noDossier: null, docs: null, sel: null };
    try {
      state.data = await api('/api/produits/' + encodeURI(ref));
    } catch (e) { toast(e.message || 'Fiche indisponible.', 'danger'); return; }
    renderCourant();
  }

  // ── Liste des produits ─────────────────────────────────────────────
  async function openListe(q) {
    contenantInline = null;
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
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', function () { openFiche(p.ref_produit_norm); });
      return tr;
    });

    var table = rows.length
      ? el('div', { className: 'pmem-tablecard pmem-scroll' }, [
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

  // ── Depot manuel de scans depuis le navigateur ─────────────────────
  // L'import par script suppose une machine qui voit le partage reseau, un
  // Python installe et une tache planifiee. Pour une reprise ponctuelle —
  // « les OF de cette annee » — c'est trois obstacles pour rien : on ouvre le
  // dossier, on selectionne, on depose. Le serveur fait exactement le meme
  // travail que pour un depot par script, deduplication comprise : reposer
  // deux fois les memes fichiers ne cree pas de doublon.
  function zoneDepot(onFini) {
    ensureStyle();
    var input = el('input', {
      type: 'file', multiple: 'multiple', accept: 'application/pdf,.pdf',
      style: 'display:none',
    });
    var titre = el('div', { className: 'pmem-drop-t', text: 'Deposer des OF scannes' });
    var sous = el('div', {
      className: 'pmem-drop-s',
      text: 'Glissez vos PDF ici, ou cliquez pour les choisir. '
          + 'Le numero d\'OF et la reference produit sont lus dans le nom du fichier.',
    });
    var barre = el('div', { className: 'pmem-prog-b' });
    var prog = el('div', { className: 'pmem-prog', style: 'display:none' }, [barre]);
    var zone = el('div', { className: 'pmem-drop' }, [titre, sous, prog, input]);

    var enCours = false;

    async function envoyer(fichiers) {
      var liste = Array.prototype.slice.call(fichiers || []).filter(function (f) {
        return /\.pdf$/i.test(f.name);
      });
      if (!liste.length) { toast('Aucun PDF dans la selection.', 'danger'); return; }
      if (enCours) return;
      enCours = true;
      prog.style.display = 'block';

      var ok = 0, doublons = 0, rattaches = 0, echecs = 0;
      for (var i = 0; i < liste.length; i++) {
        var f = liste[i];
        titre.textContent = 'Envoi ' + (i + 1) + ' / ' + liste.length + '…';
        sous.textContent = f.name;
        barre.style.width = Math.round((i / liste.length) * 100) + '%';
        var fd = new FormData();
        fd.append('file', f, f.name);
        // `lastModified` est la date du fichier sur le partage, pas celle de
        // l'envoi. C'est ce qui permet d'ordonner des scans deposes en bloc.
        try {
          if (f.lastModified) {
            fd.append('date_fichier',
              new Date(f.lastModified).toISOString().slice(0, 19));
          }
        } catch (e) { /* date illisible : le serveur retombera sur l'OF */ }
        try {
          var r = await api('/api/produits/documents', { method: 'POST', body: fd });
          if (r && r.doublon) doublons += 1;
          else { ok += 1; if (r && r.statut === 'rattache') rattaches += 1; }
        } catch (e) {
          echecs += 1;
        }
      }
      barre.style.width = '100%';

      var msg = ok + ' scan(s) enregistre(s), dont ' + rattaches + ' rattache(s) a un produit';
      if (doublons) msg += ' · ' + doublons + ' deja connu(s)';
      if (echecs) msg += ' · ' + echecs + ' en echec';
      toast(msg + '.', echecs ? 'danger' : 'info');

      enCours = false;
      prog.style.display = 'none';
      titre.textContent = 'Deposer des OF scannes';
      sous.textContent = 'Glissez vos PDF ici, ou cliquez pour les choisir.';
      input.value = '';
      if (onFini) await onFini();
    }

    zone.addEventListener('click', function () { if (!enCours) input.click(); });
    input.addEventListener('change', function (e) { envoyer(e.target.files); });
    ['dragenter', 'dragover'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault(); e.stopPropagation(); zone.classList.add('is-over');
      });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault(); e.stopPropagation(); zone.classList.remove('is-over');
      });
    });
    zone.addEventListener('drop', function (e) {
      if (e.dataTransfer && e.dataTransfer.files) envoyer(e.dataTransfer.files);
    });
    return zone;
  }

  // ── File de rattachement des scans ─────────────────────────────────
  async function openRattachement() {
    contenantInline = null;
    state = { tab: 'scannes', data: null, mode: 'rattachement', noDossier: null,
              docs: null, sel: null, q: '' };
    await chargerScans();
  }

  async function chargerScans() {
    try {
      var r = await api('/api/produits/documents?q=' + encodeURIComponent(state.q || ''));
      state.tous = r.documents || [];
      state.total = r.total || 0;
      state.nbARattacher = r.a_rattacher || 0;
    } catch (e) { toast(e.message || 'Erreur.', 'danger'); return; }
    if (state.tab === 'rattacher') { await chargerDocs(); return; }
    renderScans();
  }

  async function chargerDocs() {
    try {
      var r = await api('/api/produits/documents/a-rattacher');
      state.docs = r.documents || [];
      state.nbARattacher = r.total || 0;
      if (state.sel && !state.docs.some(function (d) { return d.id === state.sel; })) state.sel = null;
      if (!state.sel && state.docs.length) state.sel = state.docs[0].id;
    } catch (e) { toast(e.message || 'Erreur.', 'danger'); return; }
    renderScans();
  }

  function scansOnglets() {
    var defs = [
      { key: 'scannes', label: 'Scannes', count: state.total },
      { key: 'rattacher', label: 'A rattacher', count: state.nbARattacher },
    ];
    return el('div', { className: 'pmem-tabs is-sobre' }, defs.map(function (t) {
      return el('button', {
        type: 'button',
        className: 'pmem-tab' + (state.tab === t.key ? ' is-on' : ''),
        text: t.label + (t.count != null ? '  (' + t.count + ')' : ''),
        onclick: function () {
          state.tab = t.key;
          if (t.key === 'rattacher' && !state.docs) { chargerDocs(); return; }
          renderScans();
        },
      });
    }));
  }

  // ── Onglet « Scannes » : ce qu'on a deja, pas seulement les echecs ──────
  function vueScannes() {
    var input = el('input', {
      className: 'pmem-input', type: 'text', id: 'pmem-scans-q',
      placeholder: 'Rechercher (n\u00b0 d\'OF, reference, dossier, client, nom de fichier)…',
      value: state.q || '',
    });
    var t0 = null;
    input.addEventListener('input', function (e) {
      state.q = e.target.value;
      clearTimeout(t0);
      t0 = setTimeout(function () {
        var pos = input.selectionStart;
        chargerScans().then(function () {
          var n = document.getElementById('pmem-scans-q');
          if (n) { n.focus(); try { n.setSelectionRange(pos, pos); } catch (x) {} }
        });
      }, 220);
    });

    var docs = state.tous || [];
    if (!docs.length) {
      return [el('div', { style: 'margin-bottom:14px' }, [input]),
              el('div', {
                className: 'pmem-empty',
                text: state.q ? ('Aucun scan pour « ' + state.q + ' »')
                              : 'Aucun OF scanne pour l\'instant.',
              })];
    }

    var lignes = docs.map(function (d) {
      var infos = [];
      if (d.machine) infos.push(d.machine);
      if (d.client) infos.push(d.client);
      if (d.etiquettes) infos.push(fNum(d.etiquettes) + ' etiq.');
      if (d.of_laize) infos.push('laize ' + fNum(d.of_laize) + ' mm');

      var cellRef = el('td', {});
      if (d.ref_produit_norm) {
        var b = boutonFiche(d.ref_produit_norm, { label: d.ref_produit_norm });
        if (b) cellRef.appendChild(b);
        else cellRef.textContent = d.ref_produit_norm;
      } else {
        cellRef.appendChild(el('span', { className: 'pmem-chip is-warn', text: 'a rattacher' }));
      }

      var tr = el('tr', {}, [
        el('td', { text: fDate(d.date_document || d.importe_le) }),
        el('td', {}, [el('strong', { text: d.of_numero || '—' })]),
        cellRef,
        el('td', { text: d.no_dossier || '—' }),
        el('td', { text: infos.join(' · ') || '—' }),
        el('td', { title: d.chemin_origine || '', text: d.fichier_origine || '—' }),
      ]);
      var tdAct = el('td', {});
      tdAct.appendChild(boutonScan(d, 'Ouvrir'));
      tr.appendChild(tdAct);
      tr.style.cursor = 'default';
      return tr;
    });

    var table = el('div', { className: 'pmem-tablecard pmem-scroll' }, [
      el('table', { className: 'pmem-tbl pmem-tbl-sobre' }, [
        el('thead', {}, [el('tr', {},
          ['Date', 'OF', 'Produit', 'Dossier', 'Production', 'Fichier', '']
            .map(function (h) { return el('th', { text: h }); }))]),
        el('tbody', {}, lignes),
      ]),
    ]);

    var pied = docs.length < (state.total || 0)
      ? el('div', {
          style: 'font-size:11px;color:var(--muted);margin-top:10px',
          text: docs.length + ' scans affiches sur ' + state.total + '. Affinez la recherche.',
        })
      : null;

    return [el('div', { style: 'margin-bottom:14px' }, [input]), table, pied];
  }

  // ── Onglet « A rattacher » : la file, avec apercu cote a cote ───────────
  // La file est un tableau a fond blanc, pas une pile de boutons accentues :
  // vingt aplats de couleur empilaient vingt fois la meme emphase et la ligne
  // reellement selectionnee ne se distinguait plus des autres.
  function vueARattacher() {
    var docs = state.docs || [];
    if (!docs.length) {
      return [el('div', {
        className: 'pmem-empty',
        text: 'Aucun scan en attente de rattachement.',
      })];
    }

    var sel = docs.filter(function (d) { return d.id === state.sel; })[0] || docs[0];

    var lignes = docs.map(function (doc) {
      var meta = [fDate(doc.date_document || doc.importe_le),
                  doc.texte_extrait ? null : 'sans OCR'].filter(Boolean).join(' · ');
      var tr = el('tr', { className: doc.id === sel.id ? 'is-sel' : '' }, [
        el('td', {}, [
          el('div', { className: 'pmem-file-n', text: doc.fichier_origine || doc.fichier }),
          el('div', { className: 'pmem-file-m', text: meta }),
        ]),
        el('td', {}, [
          doc.of_numero
            ? el('strong', { text: doc.of_numero })
            : el('span', { className: 'pmem-chip is-warn', text: 'non lu' }),
        ]),
      ]);
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', function () {
        if (state.sel === doc.id) return;
        state.sel = doc.id;
        renderScans();
      });
      return tr;
    });

    var liste = el('div', { className: 'pmem-tablecard pmem-scroll' }, [
      el('table', { className: 'pmem-tbl pmem-tbl-sobre' }, [
        el('thead', {}, [el('tr', {}, ['Fichier', 'OF']
          .map(function (h) { return el('th', { text: h }); }))]),
        el('tbody', {}, lignes),
      ]),
    ]);

    // ── Recherche vivante du dossier ──────────────────────────────────
    // Le champ demandait un numero de dossier connu par coeur. Sur un scan
    // dont l'OF n'a justement pas ete lu, personne ne l'a : on cherche donc
    // sur tout ce que le document peut porter (dossier, OF, reference,
    // client) et on montre, AVANT de valider, la reference produit que le
    // rattachement va reellement ecrire.
    var choix = null;

    var champ = el('input', {
      className: 'pmem-input', type: 'text', id: 'pmem-dos', autocomplete: 'off',
      placeholder: 'N° de dossier, n° d\'OF, référence produit ou client…',
      value: sel.of_numero || '',
    });
    var boite = el('div', { className: 'pmem-sugg' });
    var apercu = el('div', { className: 'pmem-sugg-note' });

    function poserApercu() {
      apercu.className = 'pmem-sugg-note';
      if (!choix) { apercu.textContent = ''; return; }
      if (choix.ref_produit_norm) {
        apercu.textContent = 'Dossier ' + choix.no_dossier + ' → référence '
          + choix.ref_produit_norm
          + (choix.client ? ' · ' + choix.client : '');
      } else {
        apercu.className = 'pmem-sugg-note is-warn';
        apercu.textContent = 'Dossier ' + choix.no_dossier
          + ' : aucune référence produit rattachable — le rattachement sera refusé.';
      }
    }

    function viderSugg() { boite.textContent = ''; boite.classList.remove('is-open'); }

    function poserSugg(cands, q) {
      boite.textContent = '';
      if (!cands.length) {
        boite.appendChild(el('div', { className: 'pmem-sugg-vide',
          text: 'Aucun dossier pour « ' + q + ' »' }));
        boite.classList.add('is-open');
        return;
      }
      cands.forEach(function (c) {
        var infos = [c.client, c.machine, c.numero_of ? 'OF ' + c.numero_of : null,
                     fDate(c.date) !== '—' ? fDate(c.date) : null].filter(Boolean);
        var ligne = el('button', { type: 'button', className: 'pmem-sugg-i' }, [
          el('div', { className: 'pmem-sugg-h' }, [
            el('strong', { text: c.no_dossier }),
            c.ref_produit_norm
              ? el('span', { className: 'pmem-chip is-accent', text: c.ref_produit_norm })
              : el('span', { className: 'pmem-chip is-warn', text: 'sans référence' }),
          ]),
          el('div', { className: 'pmem-sugg-m', text: infos.join(' · ') || '—' }),
        ]);
        ligne.addEventListener('click', function () {
          choix = c;
          champ.value = c.no_dossier;
          viderSugg();
          poserApercu();
        });
        boite.appendChild(ligne);
      });
      boite.classList.add('is-open');
    }

    var tSugg = null, seqSugg = 0;
    champ.addEventListener('input', function () {
      choix = null;
      poserApercu();
      var q = (champ.value || '').trim();
      clearTimeout(tSugg);
      if (q.length < 2) { viderSugg(); return; }
      var seq = ++seqSugg;
      tSugg = setTimeout(async function () {
        try {
          var r = await api('/api/produits/dossiers/recherche?q=' + encodeURIComponent(q));
          if (seq !== seqSugg) return;   // reponse d'une frappe deja depassee
          poserSugg(r.dossiers || [], q);
        } catch (e) { viderSugg(); }
      }, 220);
    });
    champ.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') viderSugg();
    });

    // Un scan dont l'OF a ete lu arrive avec ce numero pre-rempli : autant
    // proposer tout de suite les dossiers correspondants plutot que
    // d'attendre une frappe qui n'a pas lieu d'etre.
    if ((champ.value || '').trim().length >= 2) {
      champ.dispatchEvent(new Event('input'));
    }

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
        await chargerScans();
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
        await chargerScans();
      } catch (e) { toast(e.message || 'Erreur.', 'danger'); }
    });

    var droite = el('div', {}, [
      el('label', { className: 'pmem-lbl', text: 'Rattacher a un dossier' }),
      el('div', { className: 'pmem-sugg-wrap' }, [champ, boite]),
      apercu,
      el('div', { className: 'pmem-form-row' }, [btnOk, btnKo]),
      el('iframe', { className: 'pmem-frame', src: '/api/produits/documents/' + sel.id + '/pdf',
                     style: 'margin-top:12px' }),
    ]);

    return [el('div', { className: 'pmem-split' }, [liste, droite])];
  }

  function renderScans() {
    var corps = state.tab === 'rattacher' ? vueARattacher() : vueScannes();
    mount(panel(
      header('Scans d\'OF', 'Deposer des scans, et rattacher ceux qui n\'ont pas pu l\'etre',
             [(state.total || 0) + ' scan(s)',
              (state.nbARattacher || 0) + ' en attente de rattachement']),
      scansOnglets(),
      [zoneDepot(chargerScans)].concat(corps)
    ));
    if (state.tab === 'scannes') {
      requestAnimationFrame(function () {
        var n = document.getElementById('pmem-scans-q');
        if (n && state.q) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); }
      });
    }
  }

  // ── Bouton « Historique » pour Saisieprod ──────────────────────────
  // Retourne null quand la reference n'a jamais ete produite : l'appelant
  // n'insere alors rien. Un bouton toujours present qui ouvre « aucune
  // donnee » perd sa credibilite en trois ouvertures.
  var HIST_VU_PREFIX = 'pmem_hist_vu_';

  function histCle(apercu, noDossier) {
    var base = String(noDossier || (apercu && apercu.no_dossier) || '').trim().toUpperCase();
    // Une info prod ecrite (ou corrigee) APRES la premiere consultation doit
    // resignaler : la cle porte donc sa date. Sans ca, une consigne ajoutee en
    // Tracabilite pendant la production n'atteindrait jamais le conducteur qui
    // a deja ouvert le panneau une fois.
    var info = apercu && apercu.info_prod;
    var stamp = info ? String(info.updated_at || info.created_at || '') : '';
    return stamp ? base + '|' + stamp : base;
  }

  function histDejaConsulte(cle) {
    if (!cle) return false;
    try { return localStorage.getItem(HIST_VU_PREFIX + cle) === '1'; } catch (e) { return false; }
  }

  function histMarquerConsulte(cle) {
    if (!cle) return;
    try { localStorage.setItem(HIST_VU_PREFIX + cle, '1'); } catch (e) { /* mode prive */ }
  }

  function boutonHistorique(apercu, noDossier) {
    if (!apercu || !apercu.disponible) return null;
    ensureStyle();
    var parts = [];
    // L'info prod passe en tete : elle parle de CE dossier, les autres
    // comptages parlent de la reference.
    var aInfo = !!(apercu.info_prod && apercu.info_prod.texte);
    if (aInfo) parts.push('info prod');
    if (apercu.nb_series) parts.push(apercu.nb_series + ' production' + (apercu.nb_series > 1 ? 's' : ''));
    if (apercu.nb_savoirs) parts.push(apercu.nb_savoirs + ' note' + (apercu.nb_savoirs > 1 ? 's' : ''));
    if (apercu.nb_documents) parts.push(apercu.nb_documents + ' scan' + (apercu.nb_documents > 1 ? 's' : ''));
    var total = (aInfo ? 1 : 0) + (apercu.nb_series || 0) + (apercu.nb_savoirs || 0)
              + (apercu.nb_documents || 0);
    var cle = histCle(apercu, noDossier);
    var consulte = histDejaConsulte(cle);
    // Une note d'atelier est une consigne tiree d'une production passee : c'est
    // ce qui doit arreter le conducteur avant qu'il lance la machine.
    var titre = aInfo
      ? 'Info prod sur ce dossier \u2014 a lire'
      : (apercu.nb_savoirs
          ? 'Deja produit \u2014 notes d\'atelier a lire'
          : 'Deja produit \u2014 verifier les dossiers passes');
    var b = el('button', {
      type: 'button',
      className: 'pmem-hist-btn is-signal' + (consulte ? '' : ' is-neuf'),
      title: 'Historique de la reference ' + (apercu.ref_produit_norm || '')
             + ' \u2014 ' + parts.join(' \u00b7 '),
    }, [
      el('span', { className: 'pmem-hist-pastille', text: String(total) }),
      el('span', { className: 'pmem-hist-corps' }, [
        el('span', { className: 'pmem-hist-titre', text: titre }),
        el('span', { className: 'pmem-hist-detail', text: parts.join(' \u00b7 ') }),
      ]),
      consulte ? null : el('span', { className: 'pmem-hist-tag', text: 'A consulter' }),
    ]);
    b.addEventListener('click', function () {
      histMarquerConsulte(cle);
      b.classList.remove('is-neuf');
      var tag = b.querySelector('.pmem-hist-tag');
      if (tag) tag.remove();
      openHistorique(noDossier || apercu.no_dossier);
    });
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

  // Rend la vue « Scans d'OF » DANS une page de MyProd plutot qu'en surcouche.
  // Le contenant est fourni par l'appelant a chaque rendu : MyProd reconstruit
  // son DOM entierement, garder une reference d'un rendu a l'autre pointerait
  // sur un element detache.
  async function monterScansDans(contenant) {
    // Contenant detache : MyProd a deja re-rendu depuis. Sans ce garde-fou,
    // mount() basculerait en surcouche et ferait surgir une modale que
    // personne n'a demandee.
    if (!contenant || !contenant.isConnected) return;
    // Le contenant reste actif tant qu'il est dans le document : les actions de
    // la vue (depot, rattachement, mise a l'ecart) rappellent chargerDocs(), et
    // ce second rendu doit rester dans la page, pas repartir en surcouche.
    // Quand MyProd change de page, l'element est detache et mount() bascule
    // tout seul en surcouche.
    contenantInline = contenant;
    state = { tab: 'scannes', data: null, mode: 'rattachement',
              noDossier: null, docs: null, sel: null, q: '' };
    await chargerScans();
  }

  window.MySifaProduitMemoire = {
    openHistorique: openHistorique,
    openFiche: openFiche,
    openListe: openListe,
    openRattachement: openRattachement,
    boutonHistorique: boutonHistorique,
    boutonFiche: boutonFiche,
    monterScansDans: monterScansDans,
    normRef: normRef,
    fermer: close,
  };
})();
