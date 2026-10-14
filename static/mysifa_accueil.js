/*
 * MySifa — Colonne « Mes widgets » de l'accueil.
 *
 * Chargé par mysifa_blocs.js sur / uniquement. La colonne vit HORS de #root :
 * le portail reconstruit son DOM à chaque render(), et une iframe retirée puis
 * réinsérée se recharge. En restant à côté, les widgets ne bougent jamais
 * quand le portail se redessine.
 *
 * Un widget = une iframe qui charge la vraie page du bloc. Le nom de l'iframe
 * (« mysifa-bloc|<nom>|<objet> ») met la page en mode embarqué : elle n'affiche
 * plus que le bloc et renvoie ses valeurs clés par postMessage.
 *
 * Paliers (largeur vue par la page, zoom compris) :
 *   ≥ 1600 px   colonne de 380 px
 *   1200-1599   colonne de 300 px
 *   900-1199    colonne compacte de 220 px : toutes les valeurs, libellé
 *               au-dessus du chiffre (plus de valeur principale seule :
 *               l'indicateur paraissait replié, retour du 06/10/2026)
 *   < 900       section repliable en haut de l'accueil
 *
 * Toute donnée affichée passe par textContent ou esc().
 */
(function () {
  "use strict";
  if (window.MySifaAccueil) return;
  window.MySifaAccueil = {};

  var ORIGINE = location.origin;
  // Même version que ce script (posée par mysifa_blocs.js depuis APP_VERSION).
  var VERSION = (function () {
    var src = (document.currentScript && document.currentScript.src) || "";
    var m = src.match(/[?&]v=([^&]+)/);
    return m ? m[1] : "";
  })();
  var RAFRAICHISSEMENT_MS = 60000;
  var CONFIRMATIONS_ABSENCE = 2;   // un objet n'est déclaré disparu qu'après 2 constats
  var HAUTEURS_PX = { s: 150, m: 250, l: 400 };

  var W = {
    widgets: [],
    edition: false,
    repliee: false,          // état affiché (dépend de la largeur)
    replieeBureau: false,    // préférence serveur, colonne ≥ 900 px
    avis: [],
    disparus: [],
    cartes: {}               // id → { el, iframe, valeurs, absences, w }
  };
  var racine = null;
  var minuteur = null;       // rafraîchissement chaque minute
  var ecoutes = false;       // resize / visibilitychange posés une seule fois
  var demarrage = false;     // demarrer() en cours

  /* Repli sur téléphone : propre à l'appareil et replié par défaut, pour que
     les applis restent en haut de l'écran. Il ne touche pas la préférence de
     la colonne sur ordinateur (un seul réglage serveur les liait). */
  var TELEPHONE = window.matchMedia("(max-width:899px)");
  var CLE_REPLI_TEL = "mysifa_accueil_repli_tel";

  function replieeTelephone() {
    try { return localStorage.getItem(CLE_REPLI_TEL) !== "0"; } catch (e) { return true; }
  }

  function etatRepli() {
    return TELEPHONE.matches ? replieeTelephone() : W.replieeBureau;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function api(chemin, opts) {
    opts = opts || {};
    var init = { method: opts.method || "GET", credentials: "include", headers: {} };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    return fetch(chemin, init).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) {
          var e = new Error((d && typeof d.detail === "string" && d.detail) || ("Erreur " + r.status));
          e.status = r.status;
          throw e;
        }
        return d;
      });
    });
  }

  function icone(nom) {
    var p = {
      reglages: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
      tableau: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
      replier: '<path d="m15 18-6-6 6-6"/>',
      deplier: '<path d="m9 18 6-6-6-6"/>',
      fermer: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
      valeurs: '<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M2 14h4"/><path d="M10 8h4"/><path d="M18 16h4"/>',
      demande: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M12 7v6"/><path d="M9 10h6"/>',
      "taille-s": '<path d="M4 12h16"/>',
      "taille-m": '<rect x="4" y="6" width="16" height="12" rx="2"/>',
      "taille-l": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 16v-4"/><path d="M12 16V9"/><path d="M16 16v-6"/>',
      corbeille: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>'
    }[nom] || "";
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + "</svg>";
  }

  /* Pastille d'appli : une icône par appli, nommée dans APPLIS de
     app/services/blocs_registre.py (le test vérifie qu'aucune ne manque). */
  var ICONES_APPLI = {
    atelier: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    planning: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h6"/><path d="M10 13h7"/><path d="M7 17h5"/>',
    maintenance: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M12 11v6"/><path d="M9 14h6"/>',
    stock: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/>',
    erp: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>',
    ao: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    compta: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/><path d="M8 11h.01"/><path d="M12 11h.01"/><path d="M16 11h.01"/><path d="M8 15h.01"/><path d="M12 15h.01"/><path d="M16 15v3"/><path d="M8 18h4"/>',
    expe: '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62L18.3 9.38a1 1 0 0 0-.78-.38H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
    qualite: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/>',
    bat: '<circle cx="13.5" cy="6.5" r="1"/><circle cx="17.5" cy="10.5" r="1"/><circle cx="8.5" cy="7.5" r="1"/><circle cx="6.5" cy="12.5" r="1"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.65-.75 1.65-1.69 0-.44-.18-.84-.44-1.13-.29-.29-.44-.65-.44-1.13a1.64 1.64 0 0 1 1.67-1.67h2c3.05 0 5.56-2.5 5.56-5.55C21.97 6.01 17.46 2 12 2z"/>',
    rh: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    coffre: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    calendrier: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    taches: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="m9 12 2 2 4-4"/>',
    messages: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
    accueil: '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>'
  };

  function iconeAppli(nom) {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (ICONES_APPLI[nom] || ICONES_APPLI.accueil) + "</svg>";
  }

  /* ── Style ─────────────────────────────────────────────────────────── */
  // Une seule feuille : l'aperçu de la capture et la colonne la partagent.
  function poserStyle() {
    if (document.getElementById("mysifa-accueil-style")) return;
    var st = document.createElement("style");
    st.id = "mysifa-accueil-style";
    st.textContent = [
      "#mysifa-accueil{--mac-w:300px;font:13px 'Segoe UI',system-ui,sans-serif;color:var(--text,#f1f5f9);box-sizing:border-box}",
      "#mysifa-accueil *{box-sizing:border-box}",
      "@media (min-width:900px){",
      // z-index 110 : au-dessus de .portal-page (z-index 1), dont la boîte
      // déborde sous la colonne. À 1, la page passait devant et captait tous
      // les clics de la colonne (régression du 04/10/2026). Les voiles des
      // visites guidées (9500, 20000) restent au-dessus.
      "  #mysifa-accueil{position:fixed;left:0;top:var(--mac-top,0px);bottom:96px;width:var(--mac-w);z-index:110;padding:16px 0 0 16px;display:flex;flex-direction:column}",
      "  body.mysifa-accueil-on #root{margin-left:var(--mac-w)}",
      "  #mysifa-accueil.repliee{width:56px}",
      "  body.mysifa-accueil-on.mysifa-accueil-repliee #root{margin-left:56px}",
      "}",
      "@media (min-width:1600px){#mysifa-accueil{--mac-w:380px}}",
      "@media (min-width:900px) and (max-width:1199px){#mysifa-accueil{--mac-w:220px}}",
      // position + z-index : sans eux, la section reste dans le flux SOUS les
      // calques fixes du fond animé (body::before/::after, z-index 0) et les
      // indicateurs paraissent grisés sur téléphone (constaté le 07/10/2026).
      "@media (max-width:899px){",
      "  #mysifa-accueil{padding:12px 16px 0;width:100%;position:relative;z-index:2}",
      // Repliée sur téléphone, le titre reste : une icône seule ne dit pas
      // ce qu'elle déplie. Le titre se touche aussi pour déplier.
      "  #mysifa-accueil.repliee .mac-titre{display:block;cursor:pointer}",
      "  #mysifa-accueil.repliee .mac-tete{margin-bottom:4px}",
      "}",
      // Titre sur sa propre ligne, boutons dessous : « Mes tableaux de bord »
      // ne tient pas à côté des boutons dans une colonne de 300 px.
      ".mac-tete{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 10px;padding-right:8px}",
      ".mac-tete .mac-titre{order:-1;flex:1 0 100%}",
      ".mac-tete .mac-perso{margin-left:auto}",
      ".mac-titre{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted,#94a3b8);flex:1;min-width:0;line-height:1.25}",
      ".mac-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:30px;min-width:30px;padding:0 8px;border-radius:10px;cursor:pointer;",
      "  background:var(--card,#111827);color:var(--text2,#cbd5e1);border:1px solid var(--border,#1e293b);font:600 12px 'Segoe UI',system-ui,sans-serif}",
      ".mac-btn:hover{background:var(--bg,#0a0e17);color:var(--accent,#22d3ee)}",
      ".mac-btn.on{background:var(--accent-bg,rgba(34,211,238,.12));border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}",
      ".mac-liste{flex:1;overflow-y:auto;overflow-x:hidden;padding:0 8px 16px 0;display:flex;flex-direction:column;gap:10px}",
      "#mysifa-accueil.repliee .mac-liste,#mysifa-accueil.repliee .mac-titre,#mysifa-accueil.repliee .mac-perso,#mysifa-accueil.repliee .mac-avis,#mysifa-accueil.repliee .mac-demande{display:none}",
      ".mac-demande{display:flex;align-items:center;gap:6px;margin:8px 0 10px;padding:6px 8px;border:1px dashed var(--border,#1e293b);border-radius:10px;background:none;color:var(--muted,#94a3b8);font:12px 'Segoe UI',system-ui,sans-serif;cursor:pointer;text-align:left;flex-shrink:0}",
      ".mac-demande:hover{color:var(--accent,#22d3ee);border-color:var(--accent,#22d3ee);background:var(--accent-bg,rgba(34,211,238,.08))}",
      // --mac-a : teinte de l'appli (APPLIS du registre), une variable du
      // thème. Filet à gauche, pastille et survol la reprennent.
      ".mac-carte{--mac-a:var(--accent,#22d3ee);position:relative;background:var(--card,#111827);border:1px solid var(--border,#1e293b);border-radius:12px;overflow:hidden;flex-shrink:0;transition:border-color .15s}",
      ".mac-carte::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--mac-a);pointer-events:none}",
      ".mac-carte:hover{border-color:color-mix(in srgb,var(--mac-a) 45%,var(--border,#1e293b))}",
      ".mac-carte.alerte{background:color-mix(in srgb,var(--danger,#f87171) 6%,var(--card,#111827));border-color:color-mix(in srgb,var(--danger,#f87171) 55%,var(--border,#1e293b))}",
      ".mac-carte.alerte::before{background:var(--danger,#f87171)}",
      ".mac-ctete{display:flex;align-items:center;gap:6px;padding:9px 10px 2px 14px;cursor:pointer;min-width:0}",
      ".mac-ctete:hover .mac-nom{color:var(--mac-a)}",
      ".mac-nom{flex:1;min-width:0;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-appli{display:inline-flex;align-items:center;gap:4px;flex-shrink:0;max-width:45%;padding:2px 7px;border-radius:999px;font:600 11px 'Segoe UI',system-ui,sans-serif;",
      "  color:var(--mac-a);background:color-mix(in srgb,var(--mac-a) 13%,transparent)}",
      ".mac-appli span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-appli svg{flex-shrink:0}",
      ".mac-filtres{margin:0 10px 0 14px;font-size:11px;color:var(--muted,#94a3b8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-point{display:none;flex-shrink:0;padding:2px 7px;border-radius:999px;background:var(--danger,#f87171);color:white;font:600 11px 'Segoe UI',system-ui,sans-serif}",
      ".mac-carte.alerte .mac-point{display:inline-flex}",
      ".mac-cadre{position:relative;border-top:1px solid var(--border,#1e293b)}",
      ".mac-cadre iframe{display:block;width:100%;border:0;background:transparent}",
      // Le voile ne sert qu'en mode Personnaliser : il rend la carte saisissable
      // pour le glisser-déposer. Hors édition, l'iframe défile librement.
      ".mac-cadre .mac-voile{position:absolute;inset:0;display:none}",
      "#mysifa-accueil.edition .mac-cadre .mac-voile{display:block;cursor:grab}",
      ".mac-corb{display:none;align-items:center;justify-content:center;width:26px;height:26px;border-radius:8px;cursor:pointer;flex-shrink:0;",
      "  background:var(--bg,#0a0e17);color:var(--muted,#94a3b8);border:1px solid var(--border,#1e293b)}",
      ".mac-ctete:hover .mac-corb,.mac-corb:focus-visible,.mac-corb.confirmer{display:inline-flex}",
      ".mac-corb:hover,.mac-corb.confirmer{color:#fff;background:var(--danger,#f87171);border-color:var(--danger,#f87171)}",
      ".mac-corb.confirmer{width:auto;padding:0 8px;font:600 11px 'Segoe UI',system-ui,sans-serif}",
      "#mysifa-accueil.edition .mac-corb{display:none!important}",
      // Écran tactile : pas de survol, la corbeille reste visible.
      "@media (hover:none){.mac-corb{display:inline-flex}}",
      ".mac-attente{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted,#94a3b8);pointer-events:none}",
      ".mac-carte.prete .mac-attente{display:none}",
      // Avant que le script embarqué n'ait isolé le bloc, l'iframe montre la
      // page entière : on ne la dévoile qu'au premier état reçu.
      ".mac-carte:not(.prete) .mac-cadre iframe{visibility:hidden}",
      // Rendu caché à taille d'ordinateur : même mise en page qu'à la capture.
      ".mac-hors{position:absolute!important;left:-10000px!important;top:0!important;width:1100px!important;height:700px!important;visibility:hidden!important}",
      ".mac-hors iframe{width:1100px!important;height:700px!important}",
      ".mac-indispo{display:none;padding:10px;color:var(--muted,#94a3b8);font-size:12px;line-height:1.4}",
      ".mac-carte.absent .mac-indispo{display:block}",
      ".mac-carte.absent .mac-cadre{position:absolute!important;left:-10000px!important;visibility:hidden!important}",
      // Valeurs : la première en grand (chiffre ou badge d'état), les
      // nombres suivants en tuiles, les textes suivants sur une ligne.
      ".mac-vals{display:flex;flex-direction:column;gap:6px;padding:6px 10px 0 14px}",
      ".mac-vals:empty{display:none}",
      ".mac-grand{display:flex;align-items:baseline;flex-wrap:wrap;gap:0 6px;min-width:0}",
      ".mac-grand .v{font-size:24px;font-weight:700;line-height:1.15;font-variant-numeric:tabular-nums;color:var(--text,#f1f5f9)}",
      ".mac-grand.texte .v{font-size:17px}",
      ".mac-grand .mac-badge{align-self:center}",
      ".mac-grand .u{font-size:13px;font-weight:600;color:var(--muted,#94a3b8)}",
      ".mac-grand .l{font-size:12px;color:var(--muted,#94a3b8);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".mac-grand.alerte .v,.mac-grand.alerte .u{color:var(--danger,#f87171)}",
      // Ton d'un état : TONS_ETAT de config.py → couleur du thème.
      ".mac-badge{--t:var(--muted,#94a3b8);display:inline-flex;align-items:center;gap:6px;align-self:flex-start;max-width:100%;padding:3px 10px;border-radius:999px;",
      "  font:600 13px 'Segoe UI',system-ui,sans-serif;color:var(--t);background:color-mix(in srgb,var(--t) 13%,transparent);border:1px solid color-mix(in srgb,var(--t) 35%,transparent)}",
      ".mac-badge span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-badge::before{content:'';flex-shrink:0;width:8px;height:8px;border-radius:50%;background:var(--t)}",
      ".mac-badge.ton-ok{--t:var(--success,#34d399)}",
      ".mac-badge.ton-ok::before{box-shadow:0 0 0 3px color-mix(in srgb,var(--t) 25%,transparent)}",
      ".mac-badge.ton-warn{--t:var(--warn,#fbbf24)}",
      ".mac-badge.ton-danger{--t:var(--danger,#f87171)}",
      ".mac-badge.petit{padding:1px 8px;font-size:11px;gap:5px}",
      ".mac-badge.petit::before{width:6px;height:6px}",
      ".mac-tuiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}",
      ".mac-tuile{min-width:0;padding:5px 8px;border-radius:8px;background:var(--bg,#0a0e17)}",
      ".mac-tuile .v{display:block;font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--text,#f1f5f9);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-tuile .u{font-size:11px;font-weight:600;color:var(--muted,#94a3b8);margin-left:3px}",
      ".mac-tuile .l{display:block;font-size:11px;color:var(--muted,#94a3b8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-tuile.alerte{background:color-mix(in srgb,var(--danger,#f87171) 12%,transparent)}",
      ".mac-tuile.alerte .v,.mac-tuile.alerte .u{color:var(--danger,#f87171)}",
      ".mac-meta{display:flex;flex-wrap:wrap;align-items:center;gap:2px 0;font-size:12px;color:var(--text2,#cbd5e1);min-width:0}",
      ".mac-meta > span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}",
      ".mac-meta > span + span::before{content:'·';margin:0 6px;color:var(--muted,#94a3b8)}",
      ".mac-meta b{font-weight:700;color:var(--text,#f1f5f9)}",
      ".mac-meta .alerte b{color:var(--danger,#f87171)}",
      ".mac-pied{display:flex;align-items:center;gap:8px;padding:6px 10px 8px 14px;font-size:11px;color:var(--muted,#94a3b8);min-width:0}",
      ".mac-pied .seuil{flex:1;min-width:0;color:var(--danger,#f87171);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-pied .maj{margin-left:auto;white-space:nowrap;flex-shrink:0}",
      ".mac-pied .maj.ancienne{color:var(--warn,#fbbf24)}",
      // Tendance (« ↑ 12 % ») : couleur selon le sens de la série, pas du signe.
      ".mac-tend{font-size:11px;font-weight:600;color:var(--muted,#94a3b8);white-space:nowrap}",
      ".mac-tend.bon{color:var(--success,#34d399)}",
      ".mac-tend.mauvais{color:var(--danger,#f87171)}",
      ".mac-pied .tend{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}",
      ".mac-pied .tend:empty,.mac-pied .seuil:empty{display:none}",
      ".mac-prin{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;min-width:0}",
      ".mac-prin .mac-grand{flex:1;min-width:0}",
      ".mac-spark{flex-shrink:0;display:block;width:84px;height:28px}",
      // Grand format : graphique sur 30 jours ou liste, sous les valeurs.
      ".mac-extra{padding:8px 10px 0 14px}",
      ".mac-extra:empty{display:none}",
      ".mac-graph svg{display:block;width:100%;height:auto;overflow:visible}",
      ".mac-graph-pied{display:flex;justify-content:space-between;gap:6px;margin-top:2px;font-size:11px;color:var(--muted,#94a3b8)}",
      ".mac-graph-pied span:nth-child(2){min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center}",
      ".mac-li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 8px;align-items:center;padding:5px 0;border-top:1px solid var(--border,#1e293b);font-size:12px}",
      ".mac-li:first-child{border-top:0;padding-top:0}",
      ".mac-li .n{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text,#f1f5f9)}",
      ".mac-li .q{font-size:11px;color:var(--muted,#94a3b8);font-variant-numeric:tabular-nums;white-space:nowrap}",
      ".mac-li .bar{grid-column:1/-1;height:4px;border-radius:2px;background:var(--bg,#0a0e17);overflow:hidden}",
      ".mac-li .bar i{display:block;height:100%;background:var(--danger,#f87171)}",
      ".mac-li-plus{font-size:11px;color:var(--muted,#94a3b8);padding-top:4px}",
      ".mac-li-vide{font-size:12px;color:var(--muted,#94a3b8);font-style:italic}",
      // Compact : une ligne — nom, valeur, tendance. Le reste se cache.
      ".mac-court{display:none;align-items:center;gap:6px;flex-shrink:0;min-width:0;max-width:60%}",
      ".mac-court .v{font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-court .u{font-size:11px;font-weight:600;color:var(--muted,#94a3b8)}",
      ".mac-court.alerte .v,.mac-court.alerte .u{color:var(--danger,#f87171)}",
      ".mac-carte.t-s .mac-court{display:inline-flex}",
      ".mac-carte.t-s .mac-vals,.mac-carte.t-s .mac-pied,.mac-carte.t-s .mac-filtres,.mac-carte.t-s .mac-appli,.mac-carte.t-s .mac-extra{display:none!important}",
      ".mac-carte.t-s .mac-ctete{padding:8px 10px 8px 14px}",
      ".mac-carte.t-s.alerte .mac-point{width:9px;height:9px;padding:0;font-size:0}",
      // Barre de filtres du grand format : pastilles sous le titre.
      ".mac-fbar{display:flex;flex-wrap:wrap;align-items:flex-start;gap:4px 6px;padding:6px 10px 0 14px}",
      ".mac-fbar[hidden]{display:none}",
      ".mac-fbar.en-cours{opacity:.6;pointer-events:none}",
      ".mac-fgr{display:inline-flex;flex-wrap:wrap;gap:2px;padding:2px;border-radius:9px;background:var(--bg,#0a0e17);border:1px solid var(--border,#1e293b)}",
      ".mac-fgr button{font:600 11px 'Segoe UI',system-ui,sans-serif;border:0;background:transparent;color:var(--text2,#cbd5e1);padding:2px 7px;border-radius:7px;cursor:pointer;white-space:nowrap}",
      ".mac-fgr button:hover{color:var(--mac-a)}",
      ".mac-fgr button.on{background:color-mix(in srgb,var(--mac-a) 14%,transparent);color:var(--mac-a);cursor:default}",
      ".mac-fmulti{font-size:11px;color:var(--text2,#cbd5e1);max-width:100%}",
      ".mac-fmulti summary{cursor:pointer;font-weight:600;padding:3px 8px;border-radius:9px;background:var(--bg,#0a0e17);border:1px solid var(--border,#1e293b);list-style:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-fmulti summary::-webkit-details-marker{display:none}",
      ".mac-fmulti summary::after{content:' ▾';color:var(--muted,#94a3b8)}",
      ".mac-fmulti div{display:flex;flex-wrap:wrap;gap:2px 10px;padding:6px 4px 0}",
      ".mac-fmulti label{display:inline-flex;align-items:center;gap:4px;cursor:pointer}",
      // Barre affichée : le sous-titre des filtres ferait doublon.
      ".mac-carte.a-fbar .mac-filtres{display:none!important}",
      "#mysifa-accueil.edition .mac-fbar{display:none}",
      ".mac-tailles{display:inline-flex;gap:2px;padding:2px;border-radius:9px;background:var(--card,#111827);border:1px solid var(--border,#1e293b)}",
      ".mac-tailles .mac-btn{border:0;height:22px;min-width:24px;padding:0 4px;background:transparent}",
      ".mac-tailles .mac-btn.on{background:var(--accent-bg,rgba(34,211,238,.12));color:var(--accent,#22d3ee)}",
      "@media (min-width:900px) and (max-width:1199px){",
      "  .mac-carte .mac-cadre{position:absolute!important;left:-10000px!important;width:1100px!important;visibility:hidden!important}",
      "  .mac-carte .mac-cadre iframe{width:1100px!important;height:700px!important}",
      // Colonne de 220 px : pastille réduite à l'icône, tuiles en une colonne.
      "  .mac-appli span{display:none}",
      "  .mac-appli{padding:3px 5px}",
      "  .mac-grand .v{font-size:20px}",
      "  .mac-grand .l{flex-basis:100%}",
      "  .mac-tuiles{grid-template-columns:minmax(0,1fr)}",
      "  .mac-pied .seuil{display:none}",
      "  .mac-carte.alerte .mac-point{width:9px;height:9px;padding:0;font-size:0}",
      "  .mac-perso span{display:none}",
      "}",
      ".mac-outils{display:none;align-items:center;gap:4px;padding:6px 8px;border-top:1px solid var(--border,#1e293b);background:var(--bg,#0a0e17)}",
      "#mysifa-accueil.edition .mac-outils{display:flex}",
      "#mysifa-accueil.edition .mac-carte{cursor:grab}",
      ".mac-outils .mac-btn{height:26px;min-width:26px;padding:0 6px;font-size:11px}",
      ".mac-outils .mac-esp{flex:1}",
      ".mac-outils .mac-sup-ok,.mac-outils [data-act=sup]:hover{background:var(--danger,#f87171);border-color:var(--danger,#f87171);color:#fff}",
      ".mac-outils input{flex:1;min-width:0;font:13px 'Segoe UI',system-ui,sans-serif;background:var(--card,#111827);color:var(--text,#f1f5f9);border:1px solid var(--border,#1e293b);border-radius:8px;padding:4px 6px}",
      ".mac-carte.glisse{position:fixed;z-index:200;opacity:.92;box-shadow:0 12px 32px rgba(0,0,0,.25);pointer-events:none}",
      ".mac-place{border:2px dashed var(--accent,#22d3ee);border-radius:12px;background:var(--accent-bg,rgba(34,211,238,.12));flex-shrink:0}",
      // Au doigt, seule l'en-tête attrape la carte : bloquer le geste sur toute
      // la carte empêchait de faire défiler la page en mode Personnaliser.
      "#mysifa-accueil.edition .mac-carte{user-select:none}",
      "#mysifa-accueil.edition .mac-ctete{touch-action:none}",
      "#mysifa-accueil.edition .mac-ctete::before{content:'';flex-shrink:0;width:10px;height:14px;opacity:.55;",
      "  background-image:radial-gradient(currentColor 1.1px,transparent 1.6px);background-size:5px 5px}",
      ".mac-vide{border:1px dashed var(--border,#1e293b);border-radius:12px;padding:14px;color:var(--muted,#94a3b8);line-height:1.45}",
      ".mac-vide-t{font-weight:700;color:var(--text,#f1f5f9);font-size:14px;margin-bottom:4px}",
      ".mac-vide-p{margin:0 0 10px;font-size:12px}",
      ".mac-etapes{list-style:none;margin:0 0 12px;padding:0;display:flex;flex-direction:column;gap:8px}",
      ".mac-etapes li{display:flex;gap:8px;align-items:flex-start;color:var(--text2,#cbd5e1)}",
      ".mac-num{flex-shrink:0;width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:var(--accent-bg,rgba(34,211,238,.12));color:var(--accent,#22d3ee);font-weight:700;font-size:11px}",
      ".mac-capico{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--accent,#22d3ee);color:var(--bg,#0a0e17);vertical-align:middle;margin:0 1px}",
      "@media (hover:none){.mac-clavier{display:none}}",
      ".mac-vide kbd{font:600 11px 'Segoe UI',system-ui,sans-serif;border:1px solid var(--border,#1e293b);border-bottom-width:2px;border-radius:5px;padding:0 4px;background:var(--card,#111827);color:var(--text,#f1f5f9)}",
      ".mac-essai{display:flex;flex-direction:column;gap:6px}",
      ".mac-essai-t{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}",
      ".mac-essai-l{display:block;padding:7px 10px;border-radius:9px;border:1px solid var(--accent,#22d3ee);color:var(--accent,#22d3ee);background:var(--accent-bg,rgba(34,211,238,.08));text-decoration:none;font-weight:600;font-size:12px}",
      ".mac-essai-l::after{content:' →'}",
      ".mac-essai-l:hover{background:var(--accent,#22d3ee);color:var(--bg,#0a0e17)}",
      ".mac-avis{display:flex;flex-direction:column;gap:6px;margin:0 8px 10px 0}",
      ".mac-avis div{display:flex;gap:6px;align-items:flex-start;background:var(--card,#111827);border:1px solid var(--warn,#fbbf24);border-radius:10px;padding:8px 10px;color:var(--text2,#cbd5e1)}",
      ".mac-avis span{flex:1}",
      ".mac-avis button{background:none;border:0;color:var(--muted,#94a3b8);cursor:pointer;padding:0}"
    ].join("\n");
    document.head.appendChild(st);
  }

  function majHaut() {
    if (!racine) return;
    var pt = parseFloat(getComputedStyle(document.body).paddingTop) || 0;
    racine.style.setProperty("--mac-top", pt + "px");
  }

  /* ── Valeurs et alertes ────────────────────────────────────────────── */
  function nombre(v) {
    var n = parseFloat(String(v == null ? "" : v).replace(/\s/g, "").replace(",", ".").replace(/[^0-9.\-]/g, ""));
    return isNaN(n) ? null : n;
  }

  /* Une alerte compare un nombre à un seuil. Une valeur texte (état, nom)
     n'en déclenche jamais, même posée avant le 06/10/2026. */
  function alerteDeclenchee(alerte, valeur) {
    if (!alerte || valeur == null || valeur === "") return false;
    var x = nombre(valeur), s = nombre(alerte.seuil);
    if (x === null || s === null) return false;
    if (alerte.op === "=") return x === s;
    return alerte.op === ">" ? x > s : x < s;
  }

  var TONS = { ok: 1, warn: 1, danger: 1, neutre: 1 };
  var OPS_ALERTE = { ">": "plus de", "<": "moins de", "=": "égal à" };

  /* « Métrage (m) » → libellé « Métrage », unité « m ». L'unité ne suit que
     le libellé : aucune n'est connue du code. */
  function decouperLibelle(lib) {
    var m = /^(.*\S)\s*\(([^()]{1,6})\)$/.exec(String(lib || ""));
    return m ? { lib: m[1], unite: m[2] } : { lib: String(lib || ""), unite: "" };
  }

  // 37112 → « 37 112 ». Une valeur déjà mise en forme par la page reste telle quelle.
  function formater(val) {
    var t = String(val);
    if (/^-?\d{4,}([.,]\d+)?$/.test(t)) {
      return Number(t.replace(",", ".")).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
    }
    return t;
  }

  // Unité affichée à côté du chiffre, sauf si la valeur la porte déjà (« 42 min »).
  function uniteDe(texte, unite) {
    if (!unite || !/^-?[\d\s\u202f\u00a0.,]+$/.test(texte)) return "";
    return unite;
  }

  function span(cls, texte) {
    var e = document.createElement("span");
    if (cls) e.className = cls;
    e.textContent = texte;
    return e;
  }

  function badge(texte, ton, petit) {
    var b = document.createElement("span");
    b.className = "mac-badge ton-" + (TONS[ton] ? ton : "neutre") + (petit ? " petit" : "");
    b.appendChild(span("", texte));
    return b;
  }

  function horodatage(c) {
    var z = c.el.querySelector(".mac-pied .maj");
    if (!z) return;
    if (!c.majLe) { z.textContent = ""; return; }
    var min = Math.floor((Date.now() - c.majLe) / 60000);
    var d = new Date(c.majLe);
    z.textContent = min < 1 ? "à l'instant" : min < 60 ? "il y a " + min + " min"
      : "à " + String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
    z.title = "Dernière mise à jour : " + d.toLocaleString("fr-FR");
    // Rafraîchi chaque minute : au-delà de 5, la page d'origine ne répond plus.
    z.classList.toggle("ancienne", min >= 5);
  }

  /* Taille : s compact, m standard, l grand. Le grand format n'existe que
     pour un bloc qui a une série ou une liste (registre), et pas dans la
     colonne de 220 px, trop étroite pour un graphique : il y redevient
     standard, le choix restant enregistré pour un écran plus large. */
  var COLONNE_ETROITE = window.matchMedia("(min-width:900px) and (max-width:1199px)");
  var SERIE_MS = 10 * 60000;   // les jours passés ne bougent plus : série relue toutes les 10 min
  var GRAPHE_JOURS = 30, GRAPHE_MAX = 93, SPARK_JOURS = 14, LISTE_MAX = 5;
  // Passage dans la colonne de 220 px ou retour : le grand format suit.
  function surLargeur() {
    Object.keys(W.cartes).forEach(function (id) { afficherValeurs(W.cartes[id]); });
    lireSources();
  }
  if (COLONNE_ETROITE.addEventListener) COLONNE_ETROITE.addEventListener("change", surLargeur);
  else if (COLONNE_ETROITE.addListener) COLONNE_ETROITE.addListener(surLargeur);

  function taille(c) {
    var h = c.w.hauteur;
    if (h === "s") return "s";
    if (h === "l" && c.w.bloc_info && c.w.bloc_info.grand && !COLONNE_ETROITE.matches) return "l";
    return "m";
  }

  function appliquerTaille(c) {
    var t = taille(c);
    c.el.classList.remove("t-s", "t-m", "t-l");
    c.el.classList.add("t-" + t);
    return t;
  }

  function jourDecale(n) {
    var d = new Date(); d.setDate(d.getDate() + n);
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  // « 75 » minutes → « 1h 15min », comme fMin des pages MyProd.
  function valeurUnite(v, unite) {
    if (v == null) return "—";
    if (unite === "min") {
      var h = Math.floor(v / 60), m = Math.round(v % 60);
      return h > 0 ? h + "h " + String(m).padStart(2, "0") + "min" : m + " min";
    }
    return Math.round(v).toLocaleString("fr-FR") + (unite ? " " + unite : "");
  }

  /* Réglages d'affichage portés par l'adresse capturée (PARAMS_AFFICHAGE du
     registre) : bloc_vue (liste ou courbe) et bloc_horizon (7, 30, 90). Ils
     ne changent aucun chiffre et ne comptent pas dans la clé des relevés. */
  function paramUrl(url, k) {
    try { return new URL(url, ORIGINE).searchParams.get(k); } catch (e) { return null; }
  }
  function avecParam(url, k, v) {
    try {
      var u = new URL(url, ORIGINE);
      if (v == null || v === "") u.searchParams.delete(k); else u.searchParams.set(k, v);
      return u.pathname + u.search + u.hash;
    } catch (e) { return url; }
  }
  function aHistorique(c) {
    var h = c.w.bloc_info && c.w.bloc_info.historique;
    return !!(h && Object.keys(h).length);
  }
  // Grand format : « graphique » (série MyProd), « liste » ou « courbe » (relevés).
  function modeGrand(c) {
    var bi = c.w.bloc_info || {};
    if ((bi.valeurs || []).some(function (v) { return v.serie; })) return "graphique";
    if (bi.liste && aHistorique(c)) return paramUrl(c.w.url_capture, "bloc_vue") === "courbe" ? "courbe" : "liste";
    if (bi.liste) return "liste";
    if (aHistorique(c)) return "courbe";
    return null;
  }
  var HORIZONS = ["7", "30", "90"];
  function horizon(c) {
    var h = paramUrl(c.w.url_capture, "bloc_horizon");
    return HORIZONS.indexOf(h) >= 0 ? Number(h) : 30;
  }

  // Valeur numérique du moment d'une clé (nombre déclaré, sinon le texte lu).
  function valeurDuMoment(c, cle) {
    var n = c.nombres && c.nombres[cle];
    if (typeof n === "number") return n;
    return nombre(c.valeurs ? c.valeurs[cle] : null);
  }

  /* Tendance d'une valeur relevée : en standard et compact, la valeur du
     moment contre celle d'hier (18 h) ; en courbe, contre le premier jour de
     l'horizon. Écart en nombre pour un compte, en % au-delà de 100. */
  function tendanceReleve(c, it) {
    var R = c.releves && c.releves.jours;
    if (!R || !it.histo) return null;
    var cur = valeurDuMoment(c, it.cle);
    if (cur == null) return null;
    var ref = null, lib = "";
    if (taille(c) === "l" && modeGrand(c) === "courbe") {
      var jours = joursEntre(jourDecale(-(horizon(c) - 1)), jourDecale(-1));
      for (var i = 0; i < jours.length; i++) {
        var x = R[jours[i]] && R[jours[i]][it.cle];
        if (typeof x === "number") { ref = x; lib = i === 0 ? "en " + horizon(c) + " j" : "depuis le " + jours[i].slice(8, 10) + "/" + jours[i].slice(5, 7); break; }
      }
    } else {
      var h = R[jourDecale(-1)] && R[jourDecale(-1)][it.cle];
      if (typeof h === "number") { ref = h; lib = "vs hier"; }
    }
    if (ref == null) return null;
    var d = cur - ref;
    var enPct = Math.abs(ref) >= 100;
    var mesure = enPct ? (ref ? Math.round(d / Math.abs(ref) * 100) : 0) : Math.round(d * 100) / 100;
    var bon = d === 0 || it.histo === "=" ? null : (it.histo === "+") === (d > 0);
    return {
      court: (d > 0 ? "↑ " : d < 0 ? "↓ " : "= ") + Math.abs(mesure).toLocaleString("fr-FR") + (enPct ? " %" : ""),
      libelle: lib,
      cls: "mac-tend" + (bon === true ? " bon" : bon === false ? " mauvais" : "")
    };
  }

  function tendanceDe(c, it) {
    if (!it.serie && it.histo) return tendanceReleve(c, it);
    var t = c.serie && c.serie.tendances && c.serie.tendances[it.cle];
    if (!t || !it.serie || !t.precedent) return null;
    var pct = Math.round((t.actuel - t.precedent) / Math.abs(t.precedent) * 100);
    var bon = pct === 0 ? null : (it.serie === "+") === (pct > 0);
    return {
      court: (pct > 0 ? "↑ " : pct < 0 ? "↓ " : "= ") + Math.abs(pct) + " %",
      libelle: t.libelle,
      cls: "mac-tend" + (bon === true ? " bon" : bon === false ? " mauvais" : "")
    };
  }

  // Barres jour par jour ; un jour sans saisie (week-end, fermeture) reste un trait.
  // Les n derniers jours jusqu'à aujourd'hui (AAAA-MM-JJ).
  function derniersJours(n) {
    var out = [];
    for (var i = n - 1; i >= 0; i--) out.push(jourDecale(-i));
    return out;
  }

  // Jours d'une période, bornes comprises.
  function joursEntre(du, au) {
    var out = [], d = new Date(du + "T12:00:00"), fin = new Date(au + "T12:00:00");
    while (d <= fin && out.length < 400) {
      out.push(d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"));
      d.setDate(d.getDate() + 1);
    }
    return out;
  }

  /* Jours du grand graphique : la période capturée dès qu'elle couvre au
     moins 7 jours (7 j, 30 j, mois) — le graphique suit alors le filtre ;
     sinon (aujourd'hui, dernier jour) les 30 derniers jours, une barre seule
     ne montrant rien. Au-delà de 93 jours, les 93 derniers de la période. */
  function joursGraphe(c) {
    var s_ = c.serie || {};
    if (/^\d{4}-\d{2}-\d{2}$/.test(s_.du || "") && /^\d{4}-\d{2}-\d{2}$/.test(s_.au || "")) {
      var j = joursEntre(s_.du, s_.au);
      if (j.length >= 7) return j.slice(-GRAPHE_MAX);
    }
    return derniersJours(GRAPHE_JOURS);
  }

  function barres(c, cle, dates, larg, haut, regle, unite) {
    var J = (c.serie && c.serie.jours) || {};
    var jours = dates.length;
    var vals = dates.map(function (j) { return { j: j, v: J[j] && J[j][cle] != null ? J[j][cle] : null }; });
    var seuil = regle && (regle.op === "<" || regle.op === ">") && c.serie.quotidien ? nombre(regle.seuil) : null;
    var max = Math.max.apply(null, vals.map(function (x) { return x.v || 0; }).concat([seuil || 0])) || 1;
    max *= 1.08;
    var pas = larg / jours, lb = Math.max(2, pas * 0.74);
    var out = "";
    vals.forEach(function (x, k) {
      var X = (k * pas + (pas - lb) / 2).toFixed(1);
      // Info-bulle : la date et la valeur du jour, pour dater une aberration.
      var date = x.j.slice(8, 10) + "/" + x.j.slice(5, 7);
      if (!x.v) {
        out += '<rect x="' + X + '" y="0" width="' + pas.toFixed(1) + '" height="' + haut + '" fill="transparent"><title>' +
          date + " : aucune saisie</title></rect>" +
          '<rect x="' + X + '" y="' + (haut - 2) + '" width="' + lb.toFixed(1) + '" height="2" rx="1" fill="var(--border)" pointer-events="none"/>';
        return;
      }
      var hb = Math.max(2, x.v / max * (haut - 2));
      var rouge = seuil != null && alerteDeclenchee(regle, x.v);
      out += '<rect x="' + X + '" y="' + (haut - hb).toFixed(1) + '" width="' + lb.toFixed(1) + '" height="' + hb.toFixed(1) +
        '" rx="1.5" fill="' + (rouge ? "var(--danger)" : "var(--mac-a)") + '"><title>' + date + " : " + esc(valeurUnite(x.v, unite)) +
        (rouge ? " (hors seuil)" : "") + "</title></rect>";
    });
    return { svg: out, vals: vals, seuil: seuil, max: max };
  }

  function sparkline(c, it) {
    var b = barres(c, it.cle, derniersJours(SPARK_JOURS), 84, 28, null, it.uniteLib);
    var e = document.createElement("span");
    e.innerHTML = '<svg class="mac-spark" viewBox="0 0 84 28" aria-hidden="true">' + b.svg + "</svg>";
    return e.firstChild;
  }

  function graphique(c, it) {
    var H = 96, L = 276;
    var b = barres(c, it.cle, joursGraphe(c), L, H, it.regle, it.uniteLib);
    var svg = b.svg;
    if (b.seuil != null) {
      var y = (H - b.seuil / b.max * (H - 2)).toFixed(1);
      svg += '<line x1="0" y1="' + y + '" x2="' + L + '" y2="' + y + '" stroke="var(--danger)" stroke-width="1" stroke-dasharray="4 3"/>' +
        '<text x="' + (L - 2) + '" y="' + Math.max(9, y - 3) + '" font-size="9" font-weight="600" fill="var(--danger)" text-anchor="end">Seuil</text>';
    }
    var g = document.createElement("div");
    g.className = "mac-graph";
    g.innerHTML = '<svg viewBox="0 0 ' + L + " " + H + '" role="img" aria-label="' + esc(it.lib) + " sur " + b.vals.length + ' jours">' + svg + "</svg>";
    var pleins = b.vals.filter(function (x) { return x.v; });
    var moy = pleins.length ? pleins.reduce(function (t, x) { return t + x.v; }, 0) / pleins.length : null;
    var hors = b.seuil != null ? pleins.filter(function (x) { return alerteDeclenchee(it.regle, x.v); }).length : 0;
    var pied = document.createElement("div");
    pied.className = "mac-graph-pied";
    var d0 = b.vals[0].j, d1 = b.vals[b.vals.length - 1].j;
    pied.appendChild(span("", d0.slice(8, 10) + "/" + d0.slice(5, 7)));
    var mil = span("", (moy == null ? "Aucune saisie" : "Moy. " + valeurUnite(moy, it.uniteLib) + " / jour") +
      (hors ? " · " + hors + " j hors seuil" : ""));
    mil.title = "Moyenne des jours travaillés sur " + b.vals.length + " jours";
    pied.appendChild(mil);
    pied.appendChild(span("", d1.slice(8, 10) + "/" + d1.slice(5, 7)));
    g.appendChild(pied);
    return g;
  }

  /* Points d'une courbe de niveau : la valeur retenue de chaque jour (18 h)
     et sa fourchette ; aujourd'hui, la valeur du moment. Un jour sans relevé
     reste un trou, jamais un zéro. */
  function pointsReleves(c, cle, jours) {
    var R = (c.releves && c.releves.jours) || {}, MI = (c.releves && c.releves.minimums) || {}, MA = (c.releves && c.releves.maximums) || {};
    var auj = jourDecale(0);
    return jours.map(function (j) {
      var v = R[j] && typeof R[j][cle] === "number" ? R[j][cle] : null;
      var mi = MI[j] && typeof MI[j][cle] === "number" ? MI[j][cle] : null;
      var ma = MA[j] && typeof MA[j][cle] === "number" ? MA[j][cle] : null;
      if (j === auj) {
        var cur = valeurDuMoment(c, cle);
        if (cur != null) {
          v = cur;
          mi = mi == null ? cur : Math.min(mi, cur);
          ma = ma == null ? cur : Math.max(ma, cur);
        }
      }
      return { j: j, v: v, mi: mi, ma: ma, enCours: j === auj };
    });
  }

  function svgCourbe(pts, L, H, opts) {
    opts = opts || {};
    var vals = [];
    pts.forEach(function (p) { [p.v, opts.bande ? p.mi : null, opts.bande ? p.ma : null].forEach(function (x) { if (x != null) vals.push(x); }); });
    if (opts.seuil != null) vals.push(opts.seuil);
    if (!vals.length) return { svg: "", vide: true };
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    if (lo === hi) { lo -= 1; hi += 1; }
    var marge = (hi - lo) * 0.1;
    lo = Math.max(lo - marge, Math.min.apply(null, vals) >= 0 ? 0 : -Infinity);
    hi += marge;
    var haut = H - 4, pas = pts.length > 1 ? L / (pts.length - 1) : L;
    var X = function (k) { return (pts.length > 1 ? k * pas : L / 2).toFixed(1); };
    var Y = function (v) { return (2 + haut - (v - lo) / (hi - lo) * haut).toFixed(1); };
    var out = "";
    // Segments contigus : un jour manquant coupe la courbe et la bande.
    var segs = [], cur = [];
    pts.forEach(function (p, k) { if (p.v == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push(k); });
    if (cur.length) segs.push(cur);
    if (opts.bande) {
      segs.forEach(function (sg) {
        var haut_ = sg.map(function (k) { return X(k) + "," + Y(pts[k].ma != null ? pts[k].ma : pts[k].v); });
        var bas = sg.slice().reverse().map(function (k) { return X(k) + "," + Y(pts[k].mi != null ? pts[k].mi : pts[k].v); });
        if (sg.length === 1) {
          var k0 = sg[0];
          out += '<line x1="' + X(k0) + '" y1="' + Y(pts[k0].ma != null ? pts[k0].ma : pts[k0].v) + '" x2="' + X(k0) + '" y2="' + Y(pts[k0].mi != null ? pts[k0].mi : pts[k0].v) +
            '" stroke="var(--mac-a)" stroke-opacity=".25" stroke-width="6" stroke-linecap="round"/>';
        } else {
          out += '<polygon points="' + haut_.concat(bas).join(" ") + '" fill="var(--mac-a)" fill-opacity=".14"/>';
        }
      });
    }
    if (opts.seuil != null) {
      out += '<line x1="0" y1="' + Y(opts.seuil) + '" x2="' + L + '" y2="' + Y(opts.seuil) + '" stroke="var(--danger)" stroke-width="1" stroke-dasharray="4 3"/>';
    }
    segs.forEach(function (sg) {
      if (sg.length > 1) {
        out += '<polyline points="' + sg.map(function (k) { return X(k) + "," + Y(pts[k].v); }).join(" ") +
          '" fill="none" stroke="var(--mac-a)" stroke-width="' + (opts.trait || 2) + '" stroke-linejoin="round" stroke-linecap="round"/>';
      }
    });
    if (opts.points) {
      pts.forEach(function (p, k) {
        if (p.v == null) return;
        var rouge = opts.regle && alerteDeclenchee(opts.regle, p.v);
        var coul = rouge ? "var(--danger)" : "var(--mac-a)";
        out += p.enCours
          ? '<circle cx="' + X(k) + '" cy="' + Y(p.v) + '" r="3.5" fill="var(--card)" stroke="' + coul + '" stroke-width="2"/>'
          : '<circle cx="' + X(k) + '" cy="' + Y(p.v) + '" r="' + (pts.length > 40 ? 1.4 : 2.2) + '" fill="' + coul + '"/>';
      });
    }
    // Info-bulles : une zone par jour.
    if (opts.bulles) {
      pts.forEach(function (p, k) {
        var x0 = Math.max(0, Number(X(k)) - pas / 2);
        var date = p.j.slice(8, 10) + "/" + p.j.slice(5, 7);
        var t = p.v == null ? date + " : aucun relevé"
          : date + (p.enCours ? " (en cours)" : " à 18 h") + " : " + valeurUnite(p.v, opts.unite) +
            (p.mi != null && p.ma != null && p.mi !== p.ma ? " · dans la journée " + valeurUnite(p.mi, opts.unite) + " – " + valeurUnite(p.ma, opts.unite) : "");
        out += '<rect x="' + x0.toFixed(1) + '" y="0" width="' + Math.max(2, pas).toFixed(1) + '" height="' + H + '" fill="transparent"><title>' + esc(t) + "</title></rect>";
      });
    }
    return { svg: out, vide: false };
  }

  /* Jours de la courbe : l'horizon choisi, mais à partir du premier relevé
     quand l'historique est plus court (7 jours au moins) — sinon quelques
     points s'écrasent sur la droite d'un axe vide. */
  function joursCourbe(c) {
    var n = horizon(c), debut = jourDecale(-(n - 1));
    var depuis = c.releves && c.releves.depuis;
    if (depuis && depuis > debut) debut = depuis < jourDecale(-6) ? depuis : jourDecale(-6);
    return joursEntre(debut, jourDecale(0));
  }

  function courbe(c, it) {
    var H = 96, L = 276, n = horizon(c);
    var jours = joursCourbe(c);
    var pts = pointsReleves(c, it.cle, jours);
    var seuil = it.regle && (it.regle.op === "<" || it.regle.op === ">") ? nombre(it.regle.seuil) : null;
    var g = document.createElement("div");
    g.className = "mac-graph mac-courbe";
    var d = svgCourbe(pts, L, H, { bande: true, points: true, bulles: true, seuil: seuil, regle: it.regle, unite: it.uniteLib });
    var avecHisto = pts.some(function (p) { return p.v != null && !p.enCours; });
    g.innerHTML = '<svg viewBox="-4 0 ' + (L + 8) + " " + H + '" role="img" aria-label="' + esc(it.lib) + " sur " + n + ' jours">' + d.svg + "</svg>";
    var pied = document.createElement("div");
    pied.className = "mac-graph-pied";
    var d0 = jours[0];
    pied.appendChild(span("", d0.slice(8, 10) + "/" + d0.slice(5, 7)));
    var depuis = c.releves && c.releves.depuis;
    var mil;
    if (!avecHisto) mil = span("", "Premier relevé ce soir à 18 h");
    else if (depuis && depuis > jourDecale(-(n - 1))) mil = span("", "Historique depuis le " + depuis.slice(8, 10) + "/" + depuis.slice(5, 7));
    else {
      var pleins = pts.filter(function (p) { return p.v != null; });
      var moy = pleins.reduce(function (t, p) { return t + p.v; }, 0) / pleins.length;
      mil = span("", "Moy. " + valeurUnite(moy, it.uniteLib));
    }
    mil.title = "Valeur relevée chaque jour à 18 h ; la bande montre le minimum et le maximum de la journée.";
    pied.appendChild(mil);
    pied.appendChild(span("", "auj."));
    g.appendChild(pied);
    return g;
  }

  function sparklineReleves(c, it) {
    var pts = pointsReleves(c, it.cle, derniersJours(SPARK_JOURS));
    var d = svgCourbe(pts, 84, 28, { trait: 1.6, points: false });
    var e = document.createElement("span");
    e.innerHTML = '<svg class="mac-spark" viewBox="-2 0 88 28" aria-hidden="true">' + d.svg + "</svg>";
    return e.firstChild;
  }

  function liste(c) {
    var z = document.createElement("div");
    var L = c.liste;
    if (!L) return z;
    if (!L.lignes || !L.lignes.length) { z.appendChild(span("mac-li-vide", "Aucune ligne.")); return z; }
    L.lignes.slice(0, LISTE_MAX).forEach(function (l) {
      var r = document.createElement("div");
      r.className = "mac-li";
      var n = span("n", l.libelle || "—");
      n.title = l.libelle || "";
      r.appendChild(n);
      r.appendChild(span("q", l.detail || ""));
      if (l.ratio != null) {
        var bar = document.createElement("span");
        bar.className = "bar";
        var i = document.createElement("i");
        i.style.width = Math.round(Math.max(0.03, l.ratio) * 100) + "%";
        bar.appendChild(i);
        r.appendChild(bar);
      }
      z.appendChild(r);
    });
    var reste = (L.total || L.lignes.length) - LISTE_MAX;
    if (reste > 0) z.appendChild(span("mac-li-plus", "+ " + reste + (reste > 1 ? " autres" : " autre")));
    return z;
  }

  /* Grand format : les filtres du bloc (période, liste, vue, machines) se
     règlent sur la carte même, en pastilles. Le choix est enregistré dans
     l'adresse capturée de l'indicateur (PATCH url_capture), comme depuis le
     questionnaire de Personnaliser, qui garde tous les filtres (dates
     choisies comprises). Décision du 14/10/2026. */
  var PERIODE_COURT = { today: "Auj.", yesterday: "Dernier jour", last7: "7 j", last30: "30 j",
                        thisMonth: "Mois", prevMonth: "Mois dernier" };

  function barreFiltres(c) {
    var z = c.el.querySelector(".mac-fbar");
    if (!z) return;
    var F = window.MySifaBlocsFiltres;
    var enCourbe = taille(c) === "l" && modeGrand(c) === "courbe";
    var aFiltres = !!(F && F.existe(c.w.bloc));
    var voir = !c.apercu && taille(c) === "l" && (aFiltres || enCourbe);
    c.el.classList.toggle("a-fbar", !!voir);
    if (!voir) { z.hidden = true; return; }
    if (!aFiltres) c.defsF = c.defsF || [];
    if (!c.defsF) {
      if (!c.defsChargement) {
        c.defsChargement = F.preparer(c.w.bloc, api).then(function (defs) {
          c.defsF = defs || [];
          barreFiltres(c);
        }).catch(function () { c.defsChargement = null; });
      }
      return;
    }
    var etat = F ? F.lire(c.defsF, c.w.url_capture) : {};
    var h = "";
    // Horizon de la courbe (réglage d'affichage, bloc_horizon).
    if (enCourbe) {
      var hz = String(horizon(c));
      h += '<span class="mac-fgr" role="group" aria-label="Horizon">' + HORIZONS.map(function (x) {
        return '<button type="button" data-fcle="bloc_horizon" data-fv="' + x + '"' +
          (x === hz ? ' class="on" aria-pressed="true"' : ' aria-pressed="false"') + ' title="Courbe sur ' + x + ' jours">' + x + " j</button>";
      }).join("") + "</span>";
    }
    c.defsF.forEach(function (f) {
      var v = etat[f.cle];
      if (f.type === "periode" || f.type === "choix") {
        var opts = (f.choix || []).filter(function (o) { return o.v !== "dates" || v === "dates"; });
        h += '<span class="mac-fgr" role="group" aria-label="' + esc(f.libelle) + '">' + opts.map(function (o) {
          var lib = f.type === "periode" ? (PERIODE_COURT[o.v] || (o.v === "dates" ? F.decrire([f], etat) || "Dates" : o.l)) : o.l;
          return '<button type="button" data-fcle="' + esc(f.cle) + '" data-fv="' + esc(o.v) + '"' +
            (o.v === v ? ' class="on" aria-pressed="true"' : ' aria-pressed="false"') +
            (o.v === "dates" ? ' title="Dates choisies : à changer depuis Personnaliser"' : ' title="' + esc(o.l) + '"') +
            ">" + esc(lib) + "</button>";
        }).join("") + "</span>";
      } else if (f.type === "multi" && (f.choix || []).length) {
        var sel = v || [];
        var resume = sel.length ? sel.map(function (x) {
          var o = f.choix.filter(function (y) { return y.v === x; })[0];
          return o ? o.l : x;
        }).join(", ") : (f.vide || "Tout");
        h += '<details class="mac-fmulti"' + (c.multiOuvert === f.cle ? " open" : "") + ' data-fcle="' + esc(f.cle) + '">' +
          "<summary>" + esc(f.libelle) + " : " + esc(resume) + "</summary><div>" +
          f.choix.map(function (o) {
            return '<label><input type="checkbox" data-fmulti="' + esc(f.cle) + '" value="' + esc(o.v) + '"' +
              (sel.indexOf(o.v) >= 0 ? " checked" : "") + ">" + esc(o.l) + "</label>";
          }).join("") + "</div></details>";
      }
      // « jour » (date figée) : seulement dans Personnaliser.
    });
    z.innerHTML = h;
    z.hidden = !h;
    if (z.dataset.ecoute) return;
    z.dataset.ecoute = "1";
    function appliquer(etat2) {
      var url = F.ecrire(c.defsF, c.w.url_capture, etat2);
      if (url === c.w.url_capture) return;
      z.classList.add("en-cours");
      patcher(c, { url_capture: url }).catch(function () {}).then(function () { z.classList.remove("en-cours"); });
    }
    z.addEventListener("click", function (e) {
      e.stopPropagation();
      var b = e.target.closest("button[data-fv]");
      if (!b || b.classList.contains("on") || z.classList.contains("en-cours")) return;
      if (b.getAttribute("data-fv") === "dates") return;
      if (b.getAttribute("data-fcle") === "bloc_horizon") {
        z.classList.add("en-cours");
        patcher(c, { url_capture: avecParam(c.w.url_capture, "bloc_horizon", b.getAttribute("data-fv")) })
          .catch(function () {}).then(function () { z.classList.remove("en-cours"); });
        return;
      }
      var etat2 = F.lire(c.defsF, c.w.url_capture);
      etat2[b.getAttribute("data-fcle")] = b.getAttribute("data-fv");
      appliquer(etat2);
    });
    z.addEventListener("toggle", function (e) {
      var d = e.target.closest && e.target.closest("details[data-fcle]");
      if (d) c.multiOuvert = d.open ? d.getAttribute("data-fcle") : (c.multiOuvert === d.getAttribute("data-fcle") ? null : c.multiOuvert);
    }, true);
    z.addEventListener("change", function (e) {
      var t = e.target;
      if (!t.matches("input[data-fmulti]")) return;
      var cle = t.getAttribute("data-fmulti");
      var etat2 = F.lire(c.defsF, c.w.url_capture);
      etat2[cle] = Array.prototype.map.call(z.querySelectorAll('input[data-fmulti="' + cle + '"]:checked'), function (x) { return x.value; });
      appliquer(etat2);
    });
  }

  function afficherValeurs(c) {
    var t_ = appliquerTaille(c);
    barreFiltres(c);
    var w = c.w;
    var defs = {};
    ((w.bloc_info && w.bloc_info.valeurs) || []).forEach(function (v) { defs[v.cle] = v; });
    var items = (w.valeurs || []).map(function (v) {
      var d = defs[v.cle] || {};
      var val = c.valeurs ? c.valeurs[v.cle] : undefined;
      var nb_ = c.nombres && c.nombres[v.cle] != null ? c.nombres[v.cle] : val;
      var texte = d.nombre === false;
      var lu = decouperLibelle(d.libelle || v.cle);
      var t = val == null || val === "" ? "" : (texte ? String(val) : formater(val));
      return {
        cle: v.cle, texte: texte, ton: d.ton ? ((c.tons && c.tons[v.cle]) || "neutre") : null,
        lib: lu.lib, libComplet: d.libelle || v.cle, unite: uniteDe(t, lu.unite), uniteLib: lu.unite, t: t,
        alerte: !texte && alerteDeclenchee(v.alerte, nb_), regle: v.alerte, serie: d.serie || null,
        histo: (c.w.bloc_info && c.w.bloc_info.historique && c.w.bloc_info.historique[v.cle]) || null
      };
    });
    var zone = c.el.querySelector(".mac-vals");
    zone.innerHTML = "";
    var enAlerte = items.filter(function (it) { return it.alerte; });

    var prin = items[0], grand = null;
    if (prin) {
      if (prin.ton && prin.t) {
        var b = badge(prin.t, prin.ton);
        b.title = prin.libComplet;
        zone.appendChild(b);
      } else {
        var g = document.createElement("div");
        g.className = "mac-grand" + (prin.texte ? " texte" : "") + (prin.alerte ? " alerte" : "");
        g.appendChild(span("v", prin.t || "—"));
        if (prin.t && prin.unite) g.appendChild(span("u", prin.unite));
        g.appendChild(span("l", prin.lib));
        grand = g;
        var avecSpark = t_ === "m" && ((prin.serie && c.serie) ||
          (prin.histo && c.releves && Object.keys(c.releves.jours || {}).length));
        if (avecSpark) {
          var lp = document.createElement("div");
          lp.className = "mac-prin";
          lp.appendChild(g);
          lp.appendChild(prin.serie ? sparkline(c, prin) : sparklineReleves(c, prin));
          zone.appendChild(lp);
        } else {
          zone.appendChild(g);
        }
      }
    }

    // Une carte d'état (badge en tête) range tout le reste sur une ligne ;
    // sinon les nombres vont en tuiles. Une valeur vide ne prend aucune place.
    var etat = !!(prin && prin.ton && prin.t);
    var tuiles = document.createElement("div");
    tuiles.className = "mac-tuiles";
    var meta = document.createElement("div");
    meta.className = "mac-meta";
    items.slice(1).forEach(function (it) {
      if (!it.t) return;
      if (it.texte || etat) {
        var m = document.createElement("span");
        m.title = it.libComplet;
        if (it.ton && grand) {
          // Appréciation d'un chiffre (« 74 · Bon ») : à côté de lui.
          var bg = badge(it.t, it.ton, true);
          bg.title = it.libComplet;
          grand.appendChild(bg);
          return;
        }
        if (it.ton) m.appendChild(badge(it.t, it.ton, true));
        else if (it.texte) m.textContent = it.t;
        else {
          if (it.alerte) m.className = "alerte";
          m.appendChild(document.createTextNode(it.lib + " "));
          var bb = document.createElement("b");
          bb.textContent = it.t + (it.unite ? " " + it.unite : "");
          m.appendChild(bb);
        }
        meta.appendChild(m);
        return;
      }
      var tu = document.createElement("div");
      tu.className = "mac-tuile" + (it.alerte ? " alerte" : "");
      tu.title = it.libComplet;
      var v = span("v", it.t);
      if (it.unite) v.appendChild(span("u", it.unite));
      tu.appendChild(v);
      tu.appendChild(span("l", it.lib));
      tuiles.appendChild(tu);
    });
    if (tuiles.childNodes.length) zone.appendChild(tuiles);
    if (meta.childNodes.length) zone.appendChild(meta);

    var seuil = c.el.querySelector(".mac-pied .seuil");
    if (enAlerte.length) {
      var a = enAlerte[0], r = a.regle || {};
      var s_ = formater(String(r.seuil == null ? "" : r.seuil).replace(/\s/g, ""));
      // La valeur fautive est déjà en rouge : le pied ne rappelle que la règle.
      seuil.textContent = enAlerte.length > 1 ? enAlerte.length + " seuils dépassés"
        : "Seuil : " + (OPS_ALERTE[r.op] || r.op || "") + " " + s_ + (a.uniteLib ? " " + a.uniteLib : "");
    } else {
      seuil.textContent = "";
    }
    // Tendance de la première valeur suivie jour par jour ; l'alerte passe devant.
    var suivie = items.filter(function (it) { return tendanceDe(c, it); })[0];
    var td = suivie ? tendanceDe(c, suivie) : null;
    var zt = c.el.querySelector(".mac-pied .tend");
    zt.className = "tend" + (td && !enAlerte.length ? " " + td.cls : "");
    zt.textContent = td && !enAlerte.length ? td.court + " " + td.libelle : "";
    zt.title = td ? (items.length > 1 ? suivie.lib + " " : "") + td.court + " " + td.libelle : "";

    // Compact : la première valeur et sa tendance, dans l'en-tête.
    var court = c.el.querySelector(".mac-court");
    court.innerHTML = "";
    court.className = "mac-court" + (prin && prin.alerte ? " alerte" : "");
    if (prin) {
      if (prin.ton && prin.t) court.appendChild(badge(prin.t, prin.ton, true));
      else {
        court.appendChild(span("v", prin.t || "—"));
        if (prin.t && prin.unite) court.appendChild(span("u", prin.unite));
      }
      var tp = tendanceDe(c, prin);
      if (tp) { var e_ = span(tp.cls, tp.court); e_.title = tp.libelle; court.appendChild(e_); }
    }

    // Grand : graphique de la première valeur suivie, sinon la liste du bloc.
    var extra = c.el.querySelector(".mac-extra");
    extra.innerHTML = "";
    if (t_ === "l") {
      var mg = modeGrand(c);
      if (mg === "graphique") {
        var ig = items.filter(function (it) { return it.serie; })[0];
        if (ig && c.serie) extra.appendChild(graphique(c, ig));
      } else if (mg === "courbe") {
        var ih = items.filter(function (it) { return it.histo; })[0];
        if (ih && c.releves) extra.appendChild(courbe(c, ih));
      } else if (mg === "liste" && c.liste) {
        extra.appendChild(liste(c));
      }
    }

    c.el.classList.toggle("alerte", enAlerte.length > 0);
    c.el.querySelector(".mac-point").title = enAlerte.length
      ? "Alerte : " + enAlerte.map(function (x) { return x.libComplet; }).join(", ") : "";
    horodatage(c);
  }

  /* ── Cartes ────────────────────────────────────────────────────────── */
  /* Sous-titre : les filtres capturés en clair (« 7 derniers jours ·
     Cohésio 2 »), pour distinguer deux indicateurs du même bloc. Rien pour
     un bloc sans filtre. */
  function afficherFiltres(c) {
    var F = window.MySifaBlocsFiltres;
    var z = c.el.querySelector(".mac-filtres");
    if (!z || !F || !F.existe(c.w.bloc)) return;
    F.preparer(c.w.bloc, api).then(function (defs) {
      var t = F.decrire(defs, F.lire(defs, c.w.url_capture));
      z.textContent = t;
      z.title = t;
      z.hidden = !t;
    }).catch(function () { /* sous-titre facultatif */ });
  }

  function srcIframe(w) {
    var u = new URL(w.url, ORIGINE);
    u.searchParams.set("widget", w.bloc);
    if (w.objet) u.searchParams.set("widget_objet", w.objet);
    return u.pathname + u.search + u.hash;
  }

  function ouvrir(w, e) {
    if (W.edition || !w.url) return;
    if (e && (e.metaKey || e.ctrlKey)) window.open(w.url, "_blank", "noopener");
    else location.href = w.url;
  }

  /* Squelette d'une carte et pastille d'appli : le même pour la colonne et
     pour l'aperçu de la capture (MySifaAccueil.apercu). */
  function squelette(w) {
    var el = document.createElement("div");
    el.className = "mac-carte aff-valeurs";
    el.setAttribute("data-id", w.id);
    el.innerHTML =
      '<div class="mac-ctete" title="Ouvrir la page"><span class="mac-nom"></span><span class="mac-court"></span><span class="mac-point">Alerte</span><span class="mac-appli" hidden></span>' +
      '<button type="button" class="mac-corb" title="Supprimer cet indicateur" aria-label="Supprimer cet indicateur">' + icone("corbeille") + "</button></div>" +
      '<div class="mac-filtres" hidden></div>' +
      '<div class="mac-fbar" hidden></div>' +
      '<div class="mac-vals"></div>' +
      '<div class="mac-extra"></div>' +
      '<div class="mac-pied"><span class="tend"></span><span class="seuil"></span><span class="maj"></span></div>' +
      '<div class="mac-indispo">Bloc indisponible à cette taille. Cliquez sur le titre pour ouvrir la page.</div>' +
      '<div class="mac-cadre"><div class="mac-attente">Chargement…</div><div class="mac-voile"></div></div>' +
      '<div class="mac-outils"></div>';
    el.querySelector(".mac-nom").textContent = w.nom;
    var app = w.bloc_info && w.bloc_info.appli_info;
    if (app) {
      // Teinte : un nom de variable du thème fixé par le registre (TEINTES).
      if (/^(accent|c[1-5])$/.test(app.teinte)) el.style.setProperty("--mac-a", "var(--" + app.teinte + ")");
      var pa = el.querySelector(".mac-appli");
      pa.innerHTML = iconeAppli(app.icone);
      pa.appendChild(span("", app.libelle));
      pa.title = app.libelle;
      pa.hidden = false;
    }
    return el;
  }

  /* Aperçu d'un indicateur pas encore créé, pour le questionnaire de capture
     (mysifa_blocs.js) : même carte, mêmes règles d'affichage. Les valeurs
     viennent de la source du bloc, avec les filtres choisis dans le
     questionnaire — comme sur l'accueil une fois créé ; en attendant sa
     réponse, et pour un bloc sans source, ce sont celles de la page. Série
     et liste sont lues par les mêmes sources que la colonne. Rend { el, maj(w) } : maj redessine
     après un changement de taille, de valeurs, de nom ou de filtres. */
  function apercu(o) {
    poserStyle();
    var c = { el: null, iframe: null, w: o.w, valeurs: o.valeurs || {}, nombres: o.nombres || {},
              tons: o.tons || {}, majLe: Date.now(), serie: null, liste: null, apercu: true };
    c.el = squelette(o.w);
    c.el.classList.add("prete", "mac-apercu");
    ["mac-corb", "mac-cadre", "mac-outils", "mac-indispo"].forEach(function (k) {
      var x = c.el.querySelector("." + k);
      if (x) x.remove();
    });
    c.el.querySelector(".mac-ctete").removeAttribute("title");
    function sousTitre() {
      var F = window.MySifaBlocsFiltres;
      var z = c.el.querySelector(".mac-filtres");
      if (!F || !F.existe(c.w.bloc)) return;
      F.preparer(c.w.bloc, api).then(function (defs) {
        var t = F.decrire(defs, F.lire(defs, c.w.url_capture));
        z.textContent = t;
        z.hidden = !t;
      }).catch(function () { /* sous-titre facultatif */ });
    }
    // Valeurs recalculées pour les filtres choisis (période, machines…).
    function valeursSource() {
      chargerSources().then(function () {
        var src = sourceDe(c.w);
        if (!src || c.valeursCapture === c.w.url_capture) return;
        var cap = c.valeursCapture = c.w.url_capture;
        var params;
        try { params = new URL(cap, ORIGINE).searchParams; } catch (e) { params = new URLSearchParams(); }
        Promise.resolve().then(function () { return src({ json: api, objet: c.w.objet, params: params }); })
          .then(function (res) {
            if (!res || res.introuvable || c.valeursCapture !== cap) return;   // filtres changés entre-temps
            c.valeurs = res.valeurs || {};
            c.nombres = res.nombres || {};
            c.tons = res.tons || {};
            c.majLe = Date.now();
            afficherValeurs(c);
          }).catch(function () { /* on garde les valeurs de la page */ });
      });
    }
    function extras() {
      chargerSources().then(function () {
        var S_ = window.MySifaBlocsSeries || {}, L_ = window.MySifaBlocsListes || {};
        var bi = c.w.bloc_info || {};
        var params;
        try { params = new URL(c.w.url_capture, ORIGINE).searchParams; } catch (e) { params = new URLSearchParams(); }
        var ctx = { json: api, objet: c.w.objet, params: params };
        var aSerie = typeof S_[c.w.bloc] === "function" && (bi.valeurs || []).some(function (v) { return v.serie; });
        if (aSerie && c.serieCapture !== c.w.url_capture) {
          c.serieCapture = c.w.url_capture;
          Promise.resolve().then(function () { return S_[c.w.bloc](ctx); })
            .then(function (r) { c.serie = r || null; afficherValeurs(c); }).catch(function () {});
        }
        var pr = chargerReleves(c);
        if (pr) pr.then(function () { afficherValeurs(c); });
        if (taille(c) === "l" && modeGrand(c) === "liste" && typeof L_[c.w.bloc] === "function" && c.listeCapture !== c.w.url_capture) {
          c.listeCapture = c.w.url_capture;
          Promise.resolve().then(function () { return L_[c.w.bloc](ctx); })
            .then(function (r) { c.liste = r || null; afficherValeurs(c); }).catch(function () {});
        }
      });
    }
    afficherValeurs(c);
    sousTitre();
    valeursSource();
    extras();
    return {
      el: c.el,
      maj: function (w2) {
        var filtresChanges = w2.url_capture !== c.w.url_capture;
        c.w = w2;
        c.el.querySelector(".mac-nom").textContent = w2.nom || "";
        afficherValeurs(c);
        if (filtresChanges) sousTitre();
        valeursSource();
        extras();
      }
    };
  }
  window.MySifaAccueil.apercu = apercu;

  function creerCarte(w) {
    var el = squelette(w);
    var c = { el: el, iframe: null, valeurs: null, absences: 0, w: w };
    afficherFiltres(c);
    el.querySelector(".mac-ctete").addEventListener("click", function (e) {
      if (e.target.closest(".mac-corb")) return;
      ouvrir(w, e);
    });
    var corb = el.querySelector(".mac-corb");
    corb.addEventListener("click", function (e) {
      e.stopPropagation();
      // Deux temps : un clic arme, le second supprime. Un widget mal visé ne
      // disparaît pas sur un geste involontaire.
      if (!corb.classList.contains("confirmer")) {
        corb.classList.add("confirmer");
        corb.textContent = "Supprimer ?";
        setTimeout(function () {
          if (!corb.isConnected || !corb.classList.contains("confirmer")) return;
          corb.classList.remove("confirmer");
          corb.innerHTML = icone("corbeille");
        }, 4000);
        return;
      }
      supprimer(c, null);
    });

    var cadre = el.querySelector(".mac-cadre");
    W.cartes[w.id] = c;
    // Bloc avec source : les valeurs viennent de l'API, aucune page chargée.
    if (sourceDe(w)) {
      c.iframe = null;
      cadre.remove();
      dessinerOutils(c);
      afficherValeurs(c);
      return c;
    }
    var iframe = document.createElement("iframe");
    iframe.name = "mysifa-bloc|" + encodeURIComponent(w.bloc) + "|" + encodeURIComponent(w.objet || "");
    iframe.title = w.nom;
    iframe.setAttribute("tabindex", "-1");
    iframe.setAttribute("aria-hidden", "true");
    // Widgets « valeurs » uniquement (décision du 04/10/2026) : la page est
    // chargée hors écran, seul son chiffre remonte.
    cadre.classList.add("mac-hors");
    cadre.insertBefore(iframe, cadre.firstChild);

    c.iframe = iframe;
    W.cartes[w.id] = c;
    dessinerOutils(c);
    afficherValeurs(c);
    return c;
  }

  /* La taille choisie (petit, moyen, grand) est un plafond : un bloc plus
     court que son cadre ne laisse pas de vide sous lui. */
  function ajusterHauteur(c) {
    if (!c.iframe) return;
    if (c.el.classList.contains("aff-valeurs")) { c.iframe.style.height = ""; return; }
    // Jamais plus haut que large : beaucoup de pages passent en vue téléphone
    // quand l'écran est en portrait étroit, et le bloc n'y existe pas toujours.
    var larg = c.iframe.clientWidth || 300;
    var max = Math.min(HAUTEURS_PX[c.w.hauteur], larg - 1);
    var h = c.hauteurBloc ? Math.min(max, Math.max(60, c.hauteurBloc + 4)) : max;
    c.iframe.style.height = h + "px";
  }

  function demarrerIframes() {
    // Échelonné : dix pages qui démarrent dans la même seconde saturent un poste lent.
    var ids = Object.keys(W.cartes);
    ids.forEach(function (id, i) {
      var c = W.cartes[id];
      if (!c.iframe || c.iframe.getAttribute("src")) return;
      setTimeout(function () { c.iframe.src = srcIframe(c.w); }, i * 350);
    });
  }

  function dessinerOutils(c) {
    var o = c.el.querySelector(".mac-outils");
    var w = c.w;
    if (c.renommage) {
      o.innerHTML = "";
      var inp = document.createElement("input");
      inp.type = "text";
      inp.maxLength = 80;
      inp.value = w.nom;
      var ok = document.createElement("button");
      ok.type = "button";
      ok.className = "mac-btn on";
      ok.textContent = "OK";
      var valider = function () {
        var n = inp.value.trim();
        if (!n) { inp.focus(); return; }
        patcher(c, { nom: n }).then(function () { c.renommage = false; dessinerOutils(c); });
      };
      ok.addEventListener("click", valider);
      inp.addEventListener("keydown", function (e) {
        if (e.key === "Enter") valider();
        if (e.key === "Escape") { c.renommage = false; dessinerOutils(c); }
      });
      o.appendChild(inp);
      o.appendChild(ok);
      setTimeout(function () { inp.focus(); inp.select(); }, 0);
      return;
    }
    var tailles = [["s", "Compact : une ligne, une seule valeur"], ["m", "Standard"]];
    if (w.bloc_info && w.bloc_info.grand) {
      var mg_ = (w.bloc_info.valeurs || []).some(function (v) { return v.serie; }) ? "graphique"
        : (w.bloc_info.liste ? (aHistorique(c) ? "liste ou courbe" : "liste") : "courbe");
      tailles.push(["l", { graphique: "Grand : graphique jour par jour", liste: "Grand : liste détaillée",
                           "liste ou courbe": "Grand : liste détaillée ou courbe", courbe: "Grand : courbe jour par jour" }[mg_]]);
    }
    var hc = w.hauteur === "s" || w.hauteur === "l" ? w.hauteur : "m";
    o.innerHTML =
      '<span class="mac-tailles" role="group" aria-label="Taille">' + tailles.map(function (t) {
        return '<button type="button" class="mac-btn' + (t[0] === hc ? " on" : "") + '" data-act="taille" data-t="' + t[0] +
          '" title="' + t[1] + '" aria-pressed="' + (t[0] === hc) + '">' + icone("taille-" + t[0]) + "</button>";
      }).join("") + "</span>" +
      '<span class="mac-esp"></span>' +
      '<button type="button" class="mac-btn" data-act="val" title="Valeurs affichées et alertes">' + icone("valeurs") + "</button>" +
      '<button type="button" class="mac-btn" data-act="nom" title="Renommer">' + icone("reglages") + "</button>" +
      '<button type="button" class="mac-btn' + (c.confirmer ? " mac-sup-ok" : "") + '" data-act="sup" title="Supprimer">' +
      (c.confirmer ? "Supprimer ?" : icone("corbeille")) + "</button>";
    o.onclick = function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      e.stopPropagation();
      if (b.getAttribute("data-act") === "taille") {
        var nt = b.getAttribute("data-t");
        if (nt === hc) return;
        var champs = { hauteur: nt };
        // Compact = une seule valeur (COMPACT_UNE_VALEUR côté serveur) : on
        // garde la première, et on le dit ; « Modifier » rajoute les autres.
        var vals = w.valeurs || [];
        var gardee = null;
        if (nt === "s" && vals.length > 1) {
          champs.valeurs = [vals[0]];
          var d0 = ((w.bloc_info && w.bloc_info.valeurs) || []).filter(function (v) { return v.cle === vals[0].cle; })[0];
          gardee = d0 ? d0.libelle : vals[0].cle;
        }
        patcher(c, champs).then(function () {
          dessinerOutils(c);
          lireSources();
          if (gardee) avis("« " + w.nom + " » en compact : seule « " + gardee + " » est gardée. Pour en afficher plusieurs, repassez en standard.");
        }).catch(function () {});
        return;
      }
      if (b.getAttribute("data-act") === "val") {
        modifierValeurs(c);
      } else if (b.getAttribute("data-act") === "nom") {
        c.renommage = true;
        dessinerOutils(c);
      } else if (b.getAttribute("data-act") === "sup") {
        if (!c.confirmer) {
          c.confirmer = true;
          dessinerOutils(c);
          setTimeout(function () { if (c.confirmer) { c.confirmer = false; dessinerOutils(c); } }, 4000);
          return;
        }
        supprimer(c, null);
      }
    };
  }

  /* Même questionnaire qu'à la capture (mysifa_blocs.js), prérempli. */
  function modifierValeurs(c) {
    var w = c.w;
    var mb = window.MySifaBlocs;
    if (!mb || !mb.questionnaire || !w.bloc_info || !(w.bloc_info.valeurs || []).length) {
      avis("Valeurs non modifiables pour cet indicateur.");
      return;
    }
    var coches = [], alertes = {};
    var textes = {};
    w.bloc_info.valeurs.forEach(function (v) { if (v.nombre === false) textes[v.cle] = true; });
    (w.valeurs || []).forEach(function (v) {
      coches.push(v.cle);
      if (v.alerte && v.alerte.op && !textes[v.cle]) alertes[v.cle] = { op: v.alerte.op, seuil: String(v.alerte.seuil) };
    });
    var F = window.MySifaBlocsFiltres;
    var defsP = (F && F.existe(w.bloc)) ? F.preparer(w.bloc, api).catch(function () { return []; }) : Promise.resolve([]);
    /* La carte suit le questionnaire en direct : elle est l'aperçu. Rien
       n'est enregistré avant « Enregistrer » ; « Annuler », Échap ou un autre
       panneau la remettent comme avant. */
    var lecture = null;
    function relire() {
      clearTimeout(lecture);
      lecture = setTimeout(function () { if (W.cartes[w.id] === c) lireSources(); }, 250);
    }
    function vue(champs) {
      var urlAvant = c.w.url_capture;
      c.w = Object.assign({}, w, champs);
      c.el.querySelector(".mac-nom").textContent = c.w.nom;
      afficherValeurs(c);
      if (c.w.url_capture !== urlAvant) { afficherFiltres(c); if (!c.iframe) relire(); }
      else if ("hauteur" in champs && champs.hauteur !== w.hauteur && !c.iframe) relire();
    }
    defsP.then(function (filtres) {
    mb.questionnaire({
      bloc: w.bloc_info,
      filtres: filtres,
      url: w.url_capture,
      actuelles: c.valeurs || {},
      coches: coches,
      alertes: alertes,
      titre: "Modifier l'indicateur",
      sousTitre: "Capturé : " + w.bloc_info.libelle,
      nom: w.nom,
      taille: w.hauteur,
      bouton: "Enregistrer",
      surChange: function (p) {
        vue({ nom: p.nom || w.nom, valeurs: p.valeurs.length ? p.valeurs : w.valeurs,
              hauteur: p.hauteur || w.hauteur, url_capture: p.url || w.url_capture });
      },
      annuler: function () {
        if (W.cartes[w.id] !== c) return;
        var urlTempo = c.w.url_capture, hTempo = c.w.hauteur;
        c.w = w;
        c.el.querySelector(".mac-nom").textContent = w.nom;
        afficherValeurs(c);
        if (urlTempo !== w.url_capture) afficherFiltres(c);
        if ((urlTempo !== w.url_capture || hTempo !== w.hauteur) && !c.iframe) relire();
      },
      envoyer: function (p) {
        var champs = { nom: p.nom, valeurs: p.valeurs };
        if (p.hauteur && p.hauteur !== (w.hauteur || "m")) champs.hauteur = p.hauteur;
        if (p.url && p.url !== w.url_capture) champs.url_capture = p.url;
        return patcher(c, champs);
      }
    });
    });
  }

  function patcher(c, champs) {
    return api("/api/accueil/widgets/" + c.w.id, { method: "PATCH", body: champs })
      .then(function (w) {
        for (var k in champs) c.w[k] = w[k];
        c.el.querySelector(".mac-nom").textContent = c.w.nom;
        if ("url_capture" in champs) {
          // Filtres changés : nouvelle adresse à ouvrir, nouveaux chiffres.
          c.w.url = w.url;
          afficherFiltres(c);
          if (c.iframe) c.iframe.src = srcIframe(c.w);
          else lireSources();
        }
        if (c.iframe) c.iframe.title = c.w.nom;
        afficherValeurs(c);
        // Taille changée depuis le questionnaire : boutons à jour, liste ou série à lire.
        if ("hauteur" in champs) { dessinerOutils(c); lireSources(); }
      })
      .catch(function (e) { avis(e.message); throw e; });
  }

  function supprimer(c, motif) {
    return api("/api/accueil/widgets/" + c.w.id, { method: "DELETE" })
      .catch(function () { /* déjà supprimé : on retire quand même */ })
      .then(function () {
        c.el.remove();
        delete W.cartes[c.w.id];
        W.widgets = W.widgets.filter(function (x) { return x.id !== c.w.id; });
        if (motif) avis(motif);
        if (!W.widgets.length) dessinerListe();
      });
  }

  /* ── Avis (widget retiré, erreur) ──────────────────────────────────── */
  function avis(texte) {
    W.avis.push(texte);
    dessinerAvis();
  }

  function dessinerAvis() {
    var z = racine.querySelector(".mac-avis");
    z.innerHTML = "";
    W.avis.forEach(function (t, i) {
      var d = document.createElement("div");
      var s = document.createElement("span");
      s.textContent = t;
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", "Fermer");
      b.innerHTML = icone("fermer");
      b.addEventListener("click", function () { W.avis.splice(i, 1); dessinerAvis(); });
      d.appendChild(s);
      d.appendChild(b);
      z.appendChild(d);
    });
  }

  /* ── Colonne vide : mode d'emploi en trois étapes ─────────────────────
     Les guides in-app ne s'ouvrent qu'aux superadmins : pour tous les autres,
     c'est ici que se découvre la capture. « Essayer sur… » propose quelques
     blocs que l'utilisateur peut capturer et ouvre leur page capture lancée
     (?capture=<bloc>, lu par mysifa_blocs.js). */
  var ICONE_CAPTURE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>';
  var SUGGESTIONS_MAX = 3;

  function dessinerVide(liste) {
    liste.innerHTML =
      '<div class="mac-vide">' +
      '<div class="mac-vide-t">Épinglez les chiffres que vous suivez</div>' +
      '<p class="mac-vide-p">Stocks à réapprovisionner, machines en marche, départs du jour… ils s\'affichent ici et se mettent à jour chaque minute.</p>' +
      '<ol class="mac-etapes">' +
      '<li><span class="mac-num">1</span><span>Ouvrez une appli.</span></li>' +
      '<li><span class="mac-num">2</span><span>Cliquez sur <span class="mac-capico" title="Bouton de capture">' + ICONE_CAPTURE + '</span> en bas à droite<span class="mac-clavier">, ou faites <kbd>Alt</kbd>+<kbd>C</kbd></span>.</span></li>' +
      '<li><span class="mac-num">3</span><span>Cliquez sur un bloc entouré, cochez les valeurs à afficher.</span></li>' +
      '</ol>' +
      '<div class="mac-essai"></div>' +
      '</div>';
    api("/api/accueil/blocs").then(function (d) {
      var zone = liste.querySelector(".mac-essai");
      if (!zone) return;
      // Un bloc par appli, dans l'ordre du registre ; ceux de l'accueil
      // lui-même n'ont pas besoin d'un détour.
      var vus = {}, choix = [];
      (d.blocs || []).forEach(function (b) {
        if (choix.length >= SUGGESTIONS_MAX || vus[b.appli] || b.appli === "portail" || b.objet) return;
        vus[b.appli] = true;
        choix.push(b);
      });
      if (!choix.length) return;
      var t = document.createElement("div");
      t.className = "mac-essai-t";
      t.textContent = "Essayer sur :";
      zone.appendChild(t);
      choix.forEach(function (b) {
        var a = document.createElement("a");
        a.className = "mac-essai-l";
        a.href = urlEssai(b);
        a.textContent = b.libelle;
        zone.appendChild(a);
      });
    }).catch(function () { /* sans suggestions, les trois étapes suffisent */ });
  }

  function urlEssai(b) {
    try {
      var u = new URL(b.url, ORIGINE);
      u.searchParams.set("capture", b.nom);
      return u.pathname + u.search + u.hash;
    } catch (e) { return b.url; }
  }

  /* ── Liste et glisser-déposer ──────────────────────────────────────── */
  function dessinerListe() {
    var liste = racine.querySelector(".mac-liste");
    if (!W.widgets.length) {
      dessinerVide(liste);
      return;
    }
    W.widgets.forEach(function (w) {
      var c = W.cartes[w.id] || creerCarte(w);
      liste.appendChild(c.el);
    });
    demarrerIframes();
  }

  /* Glisser-déposer au pointeur plutôt qu'en glisser natif HTML5 : ce
     dernier est capricieux sous Safari et n'existe pas au doigt. La carte
     attrapée suit le pointeur ; une place vide montre où elle tombera. */
  function brancherGlisser(liste) {
    var g = null;

    liste.addEventListener("pointerdown", function (e) {
      if (!W.edition || e.button > 0) return;
      var carte = e.target.closest(".mac-carte");
      if (!carte || e.target.closest("button,input")) return;
      if (e.pointerType === "touch" && !e.target.closest(".mac-ctete")) return;
      var r = carte.getBoundingClientRect();
      g = { carte: carte, dy: e.clientY - r.top, x0: e.clientX, y0: e.clientY, actif: false, r: r, id: e.pointerId };
      try { carte.setPointerCapture(e.pointerId); } catch (err) { /* navigateur ancien */ }
    });

    liste.addEventListener("pointermove", function (e) {
      if (!g || e.pointerId !== g.id) return;
      if (!g.actif) {
        if (Math.abs(e.clientY - g.y0) < 5 && Math.abs(e.clientX - g.x0) < 5) return;
        g.actif = true;
        g.place = document.createElement("div");
        g.place.className = "mac-place";
        g.place.style.height = g.r.height + "px";
        liste.insertBefore(g.place, g.carte);
        g.carte.classList.add("glisse");
        g.carte.style.width = g.r.width + "px";
        g.carte.style.left = g.r.left + "px";
      }
      e.preventDefault();
      g.carte.style.top = (e.clientY - g.dy) + "px";
      var autres = liste.querySelectorAll(".mac-carte:not(.glisse)");
      var avant = null;
      for (var i = 0; i < autres.length; i++) {
        var ra = autres[i].getBoundingClientRect();
        if (e.clientY < ra.top + ra.height / 2) { avant = autres[i]; break; }
      }
      liste.insertBefore(g.place, avant);
    });

    function lacher(e) {
      if (!g || (e && e.pointerId !== g.id)) return;
      var fini = g;
      g = null;
      if (!fini.actif) return;
      liste.insertBefore(fini.carte, fini.place);
      fini.place.remove();
      fini.carte.classList.remove("glisse");
      fini.carte.style.width = fini.carte.style.left = fini.carte.style.top = "";
      var ids = Array.prototype.map.call(liste.querySelectorAll(".mac-carte"), function (el) {
        return parseInt(el.getAttribute("data-id"), 10);
      });
      var parId = {};
      W.widgets.forEach(function (w) { parId[w.id] = w; });
      W.widgets = ids.map(function (id) { return parId[id]; }).filter(Boolean);
      api("/api/accueil/widgets-ordre", { method: "PUT", body: { ids: ids } })
        .catch(function (err) { avis(err.message); });
    }
    liste.addEventListener("pointerup", lacher);
    liste.addEventListener("pointercancel", lacher);
  }

  function basculerEdition() {
    W.edition = !W.edition;
    racine.classList.toggle("edition", W.edition);
    racine.querySelector(".mac-perso").classList.toggle("on", W.edition);
    racine.querySelector(".mac-perso").lastChild.textContent = W.edition ? "Terminer" : "Personnaliser";
    Object.keys(W.cartes).forEach(function (id) {
      var c = W.cartes[id];
      c.renommage = false;
      c.confirmer = false;
      dessinerOutils(c);
    });
  }

  function basculerRepli(sauver) {
    if (!racine) return;
    racine.classList.toggle("repliee", W.repliee);
    document.body.classList.toggle("mysifa-accueil-repliee", W.repliee);
    var b = racine.querySelector(".mac-repli");
    // Icône de tableau de bord (demande du 06/10/2026) : la flèche ne disait
    // pas à quoi sert la colonne. L'état se lit au fond actif et à l'infobulle.
    b.innerHTML = icone("tableau");
    b.classList.toggle("on", W.repliee);
    b.title = W.repliee ? "Afficher mes tableaux de bord" : "Replier mes tableaux de bord";
    b.setAttribute("aria-label", b.title);
    b.setAttribute("aria-expanded", W.repliee ? "false" : "true");
    if (!sauver) return;
    if (TELEPHONE.matches) {
      try { localStorage.setItem(CLE_REPLI_TEL, W.repliee ? "1" : "0"); } catch (e) { /* stockage bloqué : repli non retenu */ }
      return;
    }
    W.replieeBureau = W.repliee;
    api("/api/accueil/prefs", { method: "PUT", body: { colonne_repliee: W.repliee } }).catch(function () {});
  }

  function inverserRepli() {
    W.repliee = !W.repliee;
    basculerRepli(true);
  }

  /* ── Messages des iframes ──────────────────────────────────────────── */
  window.addEventListener("message", function (e) {
    if (e.origin !== ORIGINE) return;
    var d = e.data || {};
    if (d.source !== "mysifa-blocs") return;
    var c = null;
    Object.keys(W.cartes).some(function (id) {
      var f = W.cartes[id].iframe;
      if (f && f.contentWindow === e.source) { c = W.cartes[id]; return true; }
      return false;
    });
    if (!c) return;
    if (d.type === "etat") {
      c.absences = 0;
      c.valeurs = d.valeurs || {};
      c.nombres = d.nombres || {};
      c.tons = d.tons || {};
      c.majLe = Date.now();
      c.el.classList.remove("absent");
      c.hauteurBloc = d.hauteur || 0;
      ajusterHauteur(c);
      c.el.classList.add("prete");
      afficherValeurs(c);
    } else if (d.type === "ouvrir") {
      if (!W.edition && c.w.url) {
        if (d.nouvelOnglet) window.open(c.w.url, "_blank", "noopener");
        else location.href = c.w.url;
      }
    } else if (d.type === "absent") {
      c.el.classList.add("absent", "prete");
    } else if (d.type === "rechargement") {
      c.el.classList.remove("prete");
    } else if (d.type === "introuvable") {
      c.absences += 1;
      if (c.absences >= CONFIRMATIONS_ABSENCE) {
        supprimer(c, "Indicateur retiré : « " + c.w.nom + " » — l'élément suivi n'existe plus.");
      } else {
        // Premier constat : on recharge pour écarter une page simplement lente.
        setTimeout(function () {
          if (!W.cartes[c.w.id]) return;
          c.el.classList.remove("prete");
          c.iframe.src = srcIframe(c.w);
        }, 15000);
      }
    }
  });

  /* ── Sources (static/mysifa_blocs_sources.js) ──────────────────────── */
  function sourceDe(w) {
    var S = window.MySifaBlocsSources;
    return (S && typeof S[w.bloc] === "function") ? S[w.bloc] : null;
  }

  /* Série (tendance, mini-courbe, graphique) et liste (grand format) : mêmes
     API que les valeurs, servies par le cache du tour. La série n'est relue
     que toutes les 10 minutes, ou quand les filtres changent. */
  function chargerExtras(c, json, params) {
    var bi = c.w.bloc_info || {};
    var S_ = window.MySifaBlocsSeries || {}, L_ = window.MySifaBlocsListes || {};
    var ctx = { json: json, objet: c.w.objet, params: params };
    var attente = [];
    var aSerie = typeof S_[c.w.bloc] === "function" && (bi.valeurs || []).some(function (v) { return v.serie; });
    if (aSerie && (!c.serieLe || Date.now() - c.serieLe > SERIE_MS || c.serieCapture !== c.w.url_capture)) {
      attente.push(Promise.resolve().then(function () { return S_[c.w.bloc](ctx); }).then(function (r) {
        c.serie = r || null; c.serieLe = Date.now(); c.serieCapture = c.w.url_capture;
      }).catch(function () { /* série facultative : la carte reste sans tendance */ }));
    }
    if (taille(c) === "l" && modeGrand(c) === "liste" && typeof L_[c.w.bloc] === "function") {
      attente.push(Promise.resolve().then(function () { return L_[c.w.bloc](ctx); }).then(function (r) {
        c.liste = r || null;
      }).catch(function () { /* liste facultative */ }));
    }
    var p_ = chargerReleves(c);
    if (p_) attente.push(p_);
    if (attente.length) Promise.all(attente).then(function () { if (W.cartes[c.w.id]) afficherValeurs(c); });
  }

  /* Relevés d'un indicateur (GET /api/accueil/releves/{bloc}) : relus toutes
     les 10 minutes — la valeur du jour ne se fige qu'à 18 h —, ou quand
     filtres, objet ou horizon changent. */
  function chargerReleves(c) {
    if (!aHistorique(c)) return null;
    var n = Math.max(horizon(c), SPARK_JOURS + 1);
    var cle = c.w.url_capture + "|" + (c.w.objet || "") + "|" + n;
    if (c.relevesCle === cle && c.relevesLe && Date.now() - c.relevesLe < SERIE_MS) return null;
    c.relevesCle = cle;
    var q = new URLSearchParams({ url: c.w.url_capture || "", objet: c.w.objet || "", jours: String(n) });
    return api("/api/accueil/releves/" + encodeURIComponent(c.w.bloc) + "?" + q.toString()).then(function (r) {
      if (c.relevesCle !== cle) return;
      c.releves = r || null;
      c.relevesLe = Date.now();
    }).catch(function () { c.relevesCle = null; /* pas d'historique : carte sans courbe */ });
  }

  function lireSources() {
    // Cache d'un tour : dix widgets sur la même API = un seul appel.
    var cache = {};
    function json(url) {
      if (!cache[url]) cache[url] = api(url);
      return cache[url];
    }
    Object.keys(W.cartes).forEach(function (id) {
      var c = W.cartes[id];
      var src = sourceDe(c.w);
      if (!src || c.iframe) return;
      var params;
      try { params = new URL(c.w.url_capture, ORIGINE).searchParams; } catch (e) { params = new URLSearchParams(); }
      Promise.resolve()
        .then(function () { return src({ json: json, objet: c.w.objet, params: params }); })
        .then(function (res) {
          if (!W.cartes[c.w.id]) return;
          if (res && res.introuvable) {
            c.absences += 1;
            if (c.absences >= CONFIRMATIONS_ABSENCE) {
              supprimer(c, "Indicateur retiré : « " + c.w.nom + " » — l'élément suivi n'existe plus.");
            }
            return;
          }
          c.absences = 0;
          c.valeurs = (res && res.valeurs) || {};
          c.nombres = (res && res.nombres) || {};
          c.tons = (res && res.tons) || {};
          c.majLe = Date.now();
          c.el.classList.add("prete");
          afficherValeurs(c);
          chargerExtras(c, json, params);
        })
        .catch(function (e) {
          // Session expirée : plus rien ne doit rester à l'écran.
          if (e && e.status === 401) { demonter(); return; }
          // API momentanément indisponible : on garde les dernières valeurs.
          c.el.classList.add("prete");
        });
    });
  }

  function chargerScript(nom, pret) {
    if (pret()) return Promise.resolve();
    return new Promise(function (ok) {
      var s = document.createElement("script");
      s.src = "/static/" + nom + (VERSION ? "?v=" + VERSION : "");
      s.onload = s.onerror = function () { ok(); };
      document.head.appendChild(s);
    });
  }

  // Sources des valeurs et description des filtres (sous-titres, questionnaire).
  function chargerSources() {
    return Promise.all([
      chargerScript("mysifa_blocs_sources.js", function () { return !!window.MySifaBlocsSources; }),
      chargerScript("mysifa_blocs_filtres.js", function () { return !!window.MySifaBlocsFiltres; })
    ]);
  }

  function rafraichir() {
    if (!racine || document.hidden) return;
    Object.keys(W.cartes).forEach(function (id) { horodatage(W.cartes[id]); });
    lireSources();
    Object.keys(W.cartes).forEach(function (id) {
      var f = W.cartes[id].iframe;
      if (!f) return;
      try { f.contentWindow.postMessage({ source: "mysifa-blocs", type: "rafraichir" }, ORIGINE); } catch (e) { /* pas encore chargée */ }
    });
  }


  /* ── Guide in-app (moteur partagé : static/mysifa_guides.js) ─────────── */
  // Étape 1 : tâches par service. Les autres étapes montrent, en mini-maquette,
  // les vrais composants : bouton de capture, questionnaire, colonne, édition.
  var TACHES_PAR_SERVICE = {
    production: [
      "Épingler l'état de sa machine ou le temps d'arrêt du jour depuis MyProd.",
      "Suivre les dossiers en attente de sa machine depuis le Planning.",
      "Poser une alerte rouge sur les arrêts au-delà d'un seuil."
    ],
    logistique: [
      "Épingler les départs programmés et les envois en retard depuis MyExpé.",
      "Suivre les matières sous seuil depuis le tableau de bord MyStock.",
      "Garder un œil sur les transports à programmer du Pilotage."
    ],
    administration: [
      "Épingler les notes de frais à valider, les BAT en attente, les NC ouvertes.",
      "Suivre les fins de contrat proches depuis l'Outil RH.",
      "Retrouver d'un clic la page d'origine pour agir."
    ],
    direction: [
      "Composer une colonne de pilotage : production, stock, expéditions, qualité.",
      "Poser des alertes sur les chiffres qui demandent une décision.",
      "Ouvrir la page d'origine depuis un indicateur pour creuser un chiffre."
    ]
  };

  function bulletsGuide(role) {
    function bloc(titre, items) {
      return '<div class="mguide-svc"><div class="mguide-svc-hd">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
        titre + '</div><ul class="mguide-svc-list">' + items.map(function (x) { return "<li>" + x + "</li>"; }).join("") + "</ul></div>";
    }
    var T = TACHES_PAR_SERVICE, out = '<div class="mguide-tasks">';
    if (role === "superadmin" || role === "direction") {
      out += bloc("Production", T.production) + bloc("Logistique et expéditions", T.logistique) +
        bloc("Administration", T.administration) + bloc("Direction", T.direction);
    } else if (role === "fabrication") {
      out += bloc("Ce que vous pouvez épingler", T.production);
    } else if (role === "logistique" || role === "expedition") {
      out += bloc("Ce que vous pouvez épingler", T.logistique);
    } else {
      out += bloc("Ce que vous pouvez épingler", T.administration);
    }
    return out + "</div>";
  }

  var ICO = function (d) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + d + "</svg>";
  };
  var SVG = '<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI">';

  var GUIDE_ACCUEIL = {
    // tous: true — exception à la règle « guides réservés aux superadmins »
    // (mysifa_guides.js) : c'est le mode d'emploi de l'accueil de chacun.
    "accueil-widgets": { tous: true, steps: [
      {
        icon: ICO('<rect x="3" y="3" width="7" height="18" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>'),
        title: "Mes tableaux de bord",
        body: "<p>La colonne de gauche réunit les chiffres que vous suivez au quotidien, pris directement dans les applis. Chacun se met à jour <strong>chaque minute</strong> et ouvre sa page d'origine au clic.</p>",
        extra: "__BULLETS__",
        illu: SVG +
          '<rect x="6" y="6" width="328" height="138" rx="10" fill="var(--bg)" stroke="var(--border)"/>' +
          '<text x="16" y="24" font-size="9" font-weight="700" fill="var(--muted)">MES TABLEAUX DE BORD</text>' +
          // Même dessin que les cartes : filet de la couleur de l'appli,
          // pastille « Alerte », badge d'état coloré.
          '<rect x="14" y="32" width="110" height="34" rx="7" fill="var(--card)" stroke="var(--border)"/><rect x="15" y="33" width="3" height="32" fill="var(--c2)"/><text x="24" y="45" font-size="8" font-weight="700" fill="var(--text)">Stocks à réappro.</text><text x="24" y="60" font-size="13" font-weight="700" fill="var(--text)">6</text><text x="36" y="60" font-size="8" fill="var(--muted)">matières sous seuil</text>' +
          '<rect x="14" y="72" width="110" height="34" rx="7" fill="var(--card)" stroke="var(--danger)"/><rect x="14" y="72" width="110" height="34" rx="7" fill="var(--danger)" opacity=".07"/><rect x="15" y="73" width="3" height="32" fill="var(--danger)"/><text x="24" y="85" font-size="8" font-weight="700" fill="var(--text)">Départs</text><rect x="90" y="77" width="29" height="11" rx="5.5" fill="var(--danger)"/><text x="104.5" y="85" font-size="6.5" font-weight="700" fill="#fff" text-anchor="middle">Alerte</text><text x="24" y="100" font-size="13" font-weight="700" fill="var(--danger)">1</text><text x="36" y="100" font-size="8" fill="var(--muted)">départ en attente</text>' +
          '<rect x="14" y="112" width="110" height="26" rx="7" fill="var(--card)" stroke="var(--border)"/><rect x="15" y="113" width="3" height="24" fill="var(--c1)"/><text x="24" y="128" font-size="8" font-weight="700" fill="var(--text)">Cohésio 2</text><rect x="66" y="119" width="52" height="12" rx="6" fill="var(--success)" opacity=".15"/><circle cx="73" cy="125" r="2.2" fill="var(--success)"/><text x="78" y="127.5" font-size="6.5" font-weight="700" fill="var(--success)">Production</text>' +
          '<rect x="140" y="32" width="186" height="106" rx="8" fill="var(--card)" stroke="var(--border)" opacity=".6"/>' +
          [0, 1, 2].map(function (i) { return '<rect x="' + (154 + i * 58) + '" y="52" width="46" height="40" rx="7" fill="var(--bg)" stroke="var(--border)"/>'; }).join("") +
          '<text x="233" y="114" font-size="8" fill="var(--muted)" text-anchor="middle">Vos applis restent à leur place</text></svg>'
      },
      {
        icon: ICO('<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M12 8v8"/><path d="M8 12h8"/>'),
        title: "Capturer un bloc",
        body: "<p>Dans une appli, le <strong>bouton de capture</strong> en bas à droite (ou <span class=\"mguide-tag\">Alt+C</span>) efface le reste de la page : seuls les blocs épinglables restent, <strong>entourés</strong>. Au survol, un aperçu montre les valeurs qu'ils afficheraient. Cliquez sur celui qui vous intéresse.</p>",
        illu: SVG +
          '<rect x="6" y="6" width="328" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/>' +
          '<rect x="90" y="12" width="160" height="16" rx="6" fill="var(--card)" stroke="var(--accent)"/><text x="170" y="23" font-size="7" fill="var(--text)" text-anchor="middle">Capture : cliquez sur un bloc</text>' +
          '<g opacity=".18"><rect x="18" y="36" width="56" height="100" rx="6" fill="var(--muted)"/><rect x="250" y="96" width="76" height="40" rx="6" fill="var(--muted)"/></g>' +
          '<rect x="84" y="38" width="112" height="44" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-width="2"/><text x="94" y="54" font-size="8" font-weight="700" fill="var(--text)">Chiffres du stock</text><text x="94" y="72" font-size="12" font-weight="700" fill="var(--text)">6</text>' +
          '<rect x="84" y="92" width="156" height="44" rx="7" fill="none" stroke="var(--accent)" stroke-width="2"/><text x="94" y="108" font-size="8" font-weight="700" fill="var(--text)">Stocks à réapprovisionner</text>' +
          '<rect x="206" y="34" width="120" height="54" rx="7" fill="var(--card)" stroke="var(--accent)"/><text x="214" y="47" font-size="7.5" font-weight="700" fill="var(--accent)">Chiffres du stock</text>' +
          '<text x="214" y="60" font-size="7" fill="var(--muted)">MP à approvisionner</text><text x="318" y="60" font-size="7" font-weight="700" fill="var(--text)" text-anchor="end">6</text>' +
          '<text x="214" y="71" font-size="7" fill="var(--muted)">Expéditions du jour</text><text x="318" y="71" font-size="7" font-weight="700" fill="var(--text)" text-anchor="end">3</text>' +
          '<text x="214" y="82" font-size="6.5" fill="var(--muted)">Cliquez pour choisir…</text></svg>'
      },
      {
        icon: ICO('<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'),
        title: "Choisir les valeurs",
        body: "<p>Un panneau s'ouvre : cochez <strong>jusqu'à 4 valeurs</strong>, dans l'ordre où vous voulez les voir. Une alerte facultative passe un <strong>nombre</strong> en rouge au-dessus, en dessous ou à égalité d'un seuil. Un texte (état, opérateur) s'affiche sans alerte. Les <strong>filtres</strong> de la page (période, machine…) s'y affichent et se modifient. Choisissez enfin la <strong>taille</strong> : compact, standard, ou grand quand le bloc a un graphique ou une liste. Au centre de l'écran, un <strong>aperçu</strong> montre l'indicateur tel qu'il apparaîtra sur votre accueil.</p>",
        illu: SVG +
          '<rect x="80" y="6" width="180" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/>' +
          '<text x="92" y="22" font-size="8.5" font-weight="700" fill="var(--text)">Ajouter à mes tableaux de bord</text>' +
          '<rect x="92" y="30" width="156" height="34" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="99" y="37" width="9" height="9" rx="2" fill="var(--accent)"/><text x="114" y="45" font-size="8" fill="var(--text)">Arrêts (min)</text>' +
          '<rect x="99" y="50" width="142" height="10" rx="3" fill="var(--card)" stroke="var(--border)"/><text x="103" y="58" font-size="6.5" fill="var(--danger)">Rouge au-dessus de 60</text>' +
          '<rect x="92" y="68" width="156" height="28" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="99" y="73" width="9" height="9" rx="2" fill="var(--accent)"/><text x="114" y="81" font-size="8" fill="var(--text)">État</text><text x="114" y="91" font-size="6.5" fill="var(--muted)">Valeur texte : pas d\'alerte possible.</text>' +
          '<rect x="92" y="100" width="156" height="14" rx="4" fill="var(--bg)" stroke="var(--accent)"/><text x="98" y="110" font-size="7" fill="var(--text)">Cohésio 2</text>' +
          '<rect x="196" y="120" width="52" height="18" rx="6" fill="var(--accent)"/><text x="222" y="132" font-size="7.5" fill="#fff" text-anchor="middle" font-weight="700">Ajouter</text></svg>'
      },
      {
        icon: ICO('<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>'),
        title: "Lire et ouvrir",
        body: "<p>L'indicateur relit ses chiffres <strong>chaque minute</strong>, directement auprès de l'appli. La pastille de couleur dit de quelle appli vient le chiffre, le badge donne l'état d'une machine d'un coup d'œil, et une carte rouge marquée <strong>Alerte</strong> signale un seuil dépassé. L'heure de la dernière lecture s'affiche en bas. Un clic ouvre la page d'origine <strong>avec ses filtres</strong> : c'est là que l'on agit. Une période capturée (« 7 derniers jours ») reste glissante. En <strong>grand format</strong>, les filtres (période, machines, liste) se changent directement sur la carte, et le graphique suit la période choisie. Un chiffre relevé chaque jour (stock, NC, retards…) s'y affiche en <strong>courbe</strong> : la valeur de 18 h, et en bande le minimum et le maximum de la journée.</p>",
        illu: SVG +
          '<rect x="20" y="20" width="130" height="64" rx="8" fill="var(--card)" stroke="var(--danger)"/><rect x="20" y="20" width="130" height="64" rx="8" fill="var(--danger)" opacity=".07"/><rect x="21" y="21" width="3" height="62" fill="var(--danger)"/><text x="30" y="36" font-size="8.5" font-weight="700" fill="var(--text)">Temps de prod.</text><rect x="112" y="28" width="32" height="12" rx="6" fill="var(--danger)"/><text x="128" y="36.5" font-size="7" font-weight="700" fill="#fff" text-anchor="middle">Alerte</text>' +
          '<text x="30" y="56" font-size="13" font-weight="700" fill="var(--danger)">1h 12min</text><text x="86" y="56" font-size="7.5" fill="var(--muted)">Arrêts</text>' +
          '<text x="30" y="75" font-size="6.5" font-weight="700" fill="var(--danger)">Seuil : plus de 60 min</text><text x="142" y="75" font-size="6.5" fill="var(--muted)" text-anchor="end">à l\'instant</text>' +
          '<path d="M155 49h40" stroke="var(--accent)" stroke-width="1.6" marker-end="url(#fl)"/><defs><marker id="fl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--accent)"/></marker></defs>' +
          '<rect x="200" y="14" width="126" height="122" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="210" y="30" font-size="8.5" font-weight="700" fill="var(--text)">MyProd · Production</text>' +
          '<rect x="210" y="38" width="44" height="10" rx="4" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="232" y="45.5" font-size="6" fill="var(--accent)" text-anchor="middle">7 derniers j.</text>' +
          '<rect x="210" y="56" width="106" height="30" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="210" y="94" width="106" height="30" rx="6" fill="var(--bg)" stroke="var(--border)"/></svg>'
      },
      {
        icon: ICO('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
        title: "Personnaliser la colonne",
        body: "<p><span class=\"mguide-hl\">Personnaliser</span> permet de <strong>glisser</strong> chaque indicateur à sa place. Sous chacun : trois boutons règlent la <strong>taille</strong> (compact sur une ligne, standard, grand avec graphique sur 30 jours ou liste quand le bloc en a), les curseurs changent les <strong>filtres</strong>, les <strong>valeurs</strong> et leurs alertes, le crayon le <strong>renomme</strong>, la corbeille le supprime (deux clics). L'icône tableau, en haut, replie la colonne.</p>",
        illu: SVG +
          '<rect x="80" y="10" width="180" height="130" rx="10" fill="var(--bg)" stroke="var(--border)"/>' +
          '<rect x="90" y="18" width="90" height="16" rx="5" fill="var(--card)" stroke="var(--border)"/><text x="135" y="29" font-size="7" fill="var(--text2)" text-anchor="middle">TABLEAUX DE BORD</text>' +
          '<rect x="186" y="18" width="64" height="16" rx="5" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="218" y="29" font-size="7" fill="var(--accent)" text-anchor="middle">Terminer</text>' +
          '<rect x="90" y="42" width="160" height="44" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="98" y="56" font-size="8" font-weight="700" fill="var(--text)">Départs programmés</text>' +
          '<rect x="90" y="70" width="160" height="16" rx="0" fill="var(--bg)" stroke="var(--border)"/>' +
          '<rect x="194" y="72" width="14" height="12" rx="3" fill="var(--card)" stroke="var(--border)"/><path d="M198 75v6M201 75v6M204 75v6" stroke="var(--text2)" stroke-width="1"/>' +
          '<rect x="212" y="72" width="14" height="12" rx="3" fill="var(--card)" stroke="var(--border)"/><path d="M216 81l5-5" stroke="var(--text2)" stroke-width="1.2"/>' +
          '<rect x="230" y="72" width="14" height="12" rx="3" fill="var(--danger)"/>' +
          '<rect x="90" y="94" width="160" height="38" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="4 3"/><text x="170" y="117" font-size="7.5" fill="var(--accent)" text-anchor="middle">déposer ici</text></svg>'
      },
      {
        icon: ICO('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M12 7v6"/><path d="M9 10h6"/>'),
        title: "Un chiffre manque ?",
        body: "<p>Si le chiffre que vous voulez suivre n'est capturable nulle part, utilisez <strong>Faire une demande de tableau de bord</strong>, en bas de la colonne : choisissez l'application, décrivez le chiffre. La demande part aux administrateurs de MySifa.</p>",
        illu: SVG +
          '<rect x="14" y="10" width="120" height="130" rx="10" fill="var(--bg)" stroke="var(--border)"/>' +
          '<rect x="22" y="18" width="104" height="30" rx="6" fill="var(--card)" stroke="var(--border)"/><rect x="22" y="54" width="104" height="30" rx="6" fill="var(--card)" stroke="var(--border)"/>' +
          '<rect x="22" y="104" width="104" height="26" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="3 2"/><text x="74" y="115" font-size="6.5" fill="var(--accent)" text-anchor="middle">Faire une demande</text><text x="74" y="124" font-size="6.5" fill="var(--accent)" text-anchor="middle">de tableau de bord</text>' +
          '<path d="M134 117h28" stroke="var(--accent)" stroke-width="1.6" marker-end="url(#fl2)"/><defs><marker id="fl2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--accent)"/></marker></defs>' +
          '<rect x="168" y="10" width="158" height="130" rx="10" fill="var(--card)" stroke="var(--border)"/><text x="178" y="27" font-size="8" font-weight="700" fill="var(--text)">Faire une demande</text>' +
          '<text x="178" y="42" font-size="6.5" fill="var(--muted)">APPLICATION CONCERNÉE</text><rect x="178" y="46" width="138" height="14" rx="4" fill="var(--bg)" stroke="var(--border)"/><text x="184" y="56" font-size="7" fill="var(--text)">MyExpé</text>' +
          '<text x="178" y="72" font-size="6.5" fill="var(--muted)">QUEL CHIFFRE ?</text><rect x="178" y="76" width="138" height="34" rx="4" fill="var(--bg)" stroke="var(--border)"/><text x="184" y="88" font-size="6.5" fill="var(--text2)">Palettes parties cette semaine…</text>' +
          '<rect x="248" y="116" width="68" height="16" rx="5" fill="var(--accent)"/><text x="282" y="127" font-size="7" fill="#fff" text-anchor="middle" font-weight="700">Envoyer</text></svg>'
      }
    ]}
  };

  function bootGuide() {
    try {
      if (!window.MySifaGuides) return;
      var role = "";
      try { role = (typeof S !== "undefined" && S.user && S.user.role) || ""; } catch (e) { role = ""; }
      MySifaGuides.configure({ role: role });
      var g = JSON.parse(JSON.stringify(GUIDE_ACCUEIL));
      g["accueil-widgets"].steps[0].extra = bulletsGuide(role);
      MySifaGuides.registerMany(g);
      MySifaGuides.boot().then(function () {
        var slot = racine && racine.querySelector(".mac-guide");
        if (slot && typeof MySifaGuides.bookBtn === "function") slot.innerHTML = MySifaGuides.bookBtn("accueil-widgets");
        MySifaGuides.autoOpen("accueil-widgets");
      });
    } catch (e) { /* guide indisponible : la colonne fonctionne sans */ }
  }

  /* ── Démarrage ─────────────────────────────────────────────────────── */
  function monter() {
    poserStyle();
    racine = document.createElement("aside");
    racine.id = "mysifa-accueil";
    racine.setAttribute("aria-label", "Mes tableaux de bord");
    racine.innerHTML =
      '<div class="mac-tete">' +
      '<button type="button" class="mac-btn mac-repli"></button>' +
      '<span class="mac-titre">Mes tableaux de bord</span>' +
      '<span class="mac-guide"></span>' +
      '<button type="button" class="mac-btn mac-perso" title="Réorganiser, redimensionner, renommer">' + icone("reglages") + "<span>Personnaliser</span></button>" +
      "</div>" +
      '<div class="mac-avis"></div>' +
      '<div class="mac-liste"></div>' +
      '<button type="button" class="mac-demande" title="Envoyer une demande aux administrateurs">' + icone("demande") +
      "<span>Faire une demande de tableau de bord</span></button>";
    var rootApp = document.getElementById("root");
    document.body.insertBefore(racine, rootApp || document.body.firstChild);
    document.body.classList.add("mysifa-accueil-on");
    majHaut();

    racine.querySelector(".mac-perso").addEventListener("click", basculerEdition);
    racine.querySelector(".mac-demande").addEventListener("click", function () {
      if (window.MySifaBlocs && window.MySifaBlocs.demander) window.MySifaBlocs.demander();
    });
    racine.querySelector(".mac-repli").addEventListener("click", inverserRepli);
    racine.querySelector(".mac-titre").addEventListener("click", function () {
      if (TELEPHONE.matches && W.repliee) inverserRepli();
    });
    brancherGlisser(racine.querySelector(".mac-liste"));
    basculerRepli(false);
    dessinerListe();
    lireSources();
    W.disparus.forEach(function (w) {
      api("/api/accueil/widgets/" + w.id, { method: "DELETE" }).catch(function () {});
      avis("Indicateur retiré : « " + w.nom + " » — ce bloc n'existe plus dans MySifa.");
    });

    bootGuide();
    minuteur = setInterval(rafraichir, RAFRAICHISSEMENT_MS);
    if (!ecoutes) {
      ecoutes = true;
      window.addEventListener("resize", majHaut);
      // Rotation, fenêtre redimensionnée : chaque largeur reprend son repli.
      var changeLargeur = function () { W.repliee = etatRepli(); basculerRepli(false); };
      if (TELEPHONE.addEventListener) TELEPHONE.addEventListener("change", changeLargeur);
      else if (TELEPHONE.addListener) TELEPHONE.addListener(changeLargeur);
      document.addEventListener("visibilitychange", function () { if (!document.hidden) rafraichir(); });
    }
  }

  /* Déconnexion ou session expirée : le portail affiche l'écran de connexion
     SANS recharger la page (S.app = 'login'). La colonne vit hors de #root :
     sans ce démontage, elle restait affichée avec les chiffres de
     l'utilisateur précédent (constaté en prod le 06/10/2026). On retire tout :
     DOM, état, minuteur. Une nouvelle connexion repart de zéro. */
  function demonter() {
    if (minuteur) { clearInterval(minuteur); minuteur = null; }
    if (racine) { racine.remove(); racine = null; }
    document.body.classList.remove("mysifa-accueil-on", "mysifa-accueil-repliee");
    W.widgets = []; W.disparus = []; W.avis = []; W.cartes = {};
    W.edition = false; W.repliee = false; W.replieeBureau = false;
  }

  /* Suit l'affichage du portail. Page du portail absente (écran de
     connexion, autre vue) : la colonne est masquée tout de suite, puis
     démontée si la session est finie. Page revenue : réaffichée, ou
     remontée pour l'utilisateur qui vient de se connecter. */
  var verifPrevue = false;
  function surveiller() {
    if (verifPrevue) return;
    verifPrevue = true;
    setTimeout(function () {
      verifPrevue = false;
      var portail = !!document.querySelector(".portal-page");
      if (portail && !racine) { demarrer(); return; }
      if (!racine) return;
      if (portail) {
        racine.style.display = "";
        document.body.classList.add("mysifa-accueil-on");
        return;
      }
      if (racine.style.display === "none") return;
      racine.style.display = "none";
      document.body.classList.remove("mysifa-accueil-on");
      api("/api/accueil/prefs").catch(function (e) { if (e && e.status === 401) demonter(); });
    }, 0);
  }

  /* Le portail n'est monté que pour un utilisateur connecté : on attend sa
     page, et un 401 sur l'API suffit à ne rien afficher (écran de connexion). */
  function demarrer() {
    if (demarrage || racine) return;
    demarrage = true;
    Promise.all([api("/api/accueil/widgets"), api("/api/accueil/prefs")]).then(function (r) {
      var tous = r[0].widgets || [];
      // « desactive » (bloc coupé par le superadmin) et « inaccessible »
      // (droits retirés) : masqués, pas supprimés — ils reviennent avec l'accès.
      W.widgets = tous.filter(function (w) { return w.etat === "ok"; });
      W.disparus = tous.filter(function (w) { return w.etat === "disparu"; });
      W.replieeBureau = !!r[1].colonne_repliee;
      W.repliee = etatRepli();
      return chargerSources().then(function () {
        // Entre-temps, l'utilisateur a pu quitter le portail (déconnexion).
        if (document.querySelector(".portal-page") && !racine) monter();
      });
    }).catch(function () { /* non connecté ou API indisponible : pas de colonne */ })
      .then(function () { demarrage = false; });
  }

  // On attend la page du portail, aussi lente soit-elle : un poste chargé ne
  // doit pas perdre sa colonne parce que le portail a mis 15 s à s'afficher.
  // L'observation reste active ensuite : déconnexion, reconnexion.
  // Chargé hors de l'accueil pour le seul aperçu de la capture : pas de colonne.
  if (window.__mysifaAccueilApercuSeul) return;
  new MutationObserver(surveiller).observe(document.documentElement, { childList: true, subtree: true });
  surveiller();
})();
