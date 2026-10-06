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
    repliee: false,
    avis: [],
    disparus: [],
    cartes: {}               // id → { el, iframe, valeurs, absences, w }
  };
  var racine = null;

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
      corbeille: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>'
    }[nom] || "";
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + "</svg>";
  }

  /* ── Style ─────────────────────────────────────────────────────────── */
  function poserStyle() {
    var st = document.createElement("style");
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
      "@media (max-width:899px){#mysifa-accueil{padding:12px 16px 0;width:100%}}",
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
      ".mac-carte{position:relative;background:var(--card,#111827);border:1px solid var(--border,#1e293b);border-radius:12px;overflow:hidden;flex-shrink:0}",
      ".mac-carte.alerte{border-color:var(--danger,#f87171);box-shadow:0 0 0 1px var(--danger,#f87171)}",
      ".mac-ctete{display:flex;align-items:center;gap:6px;padding:8px 10px;cursor:pointer}",
      ".mac-ctete:hover .mac-nom{color:var(--accent,#22d3ee)}",
      ".mac-nom{flex:1;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-point{width:8px;height:8px;border-radius:50%;background:var(--danger,#f87171);display:none;flex-shrink:0}",
      ".mac-carte.alerte .mac-point{display:block}",
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
      ".mac-vals{display:flex;flex-direction:column;gap:2px;padding:4px 10px 10px}",
      ".mac-val{display:flex;align-items:baseline;gap:8px}",
      ".mac-val .lib{color:var(--muted,#94a3b8);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-val .v{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--text,#f1f5f9)}",
      ".mac-val.alerte .v{color:var(--danger,#f87171)}",
      "@media (min-width:900px) and (max-width:1199px){",
      "  .mac-carte .mac-cadre{position:absolute!important;left:-10000px!important;width:1100px!important;visibility:hidden!important}",
      "  .mac-carte .mac-cadre iframe{width:1100px!important;height:700px!important}",
      "  .mac-vals{gap:4px}",
      "  .mac-val{flex-direction:column;align-items:stretch;gap:0}",
      "  .mac-val .lib{font-size:11px}",
      "  .mac-val .v{font-size:17px;line-height:1.2}",
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
      "#mysifa-accueil.edition .mac-carte{touch-action:none;user-select:none}",
      ".mac-vide{border:1px dashed var(--border,#1e293b);border-radius:12px;padding:14px;color:var(--muted,#94a3b8);line-height:1.45}",
      ".mac-vide-t{font-weight:700;color:var(--text,#f1f5f9);font-size:14px;margin-bottom:4px}",
      ".mac-vide-p{margin:0 0 10px;font-size:12px}",
      ".mac-etapes{list-style:none;margin:0 0 12px;padding:0;display:flex;flex-direction:column;gap:8px}",
      ".mac-etapes li{display:flex;gap:8px;align-items:flex-start;color:var(--text2,#cbd5e1)}",
      ".mac-num{flex-shrink:0;width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:var(--accent-bg,rgba(34,211,238,.12));color:var(--accent,#22d3ee);font-weight:700;font-size:11px}",
      ".mac-capico{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--accent,#22d3ee);color:var(--bg,#0a0e17);vertical-align:middle;margin:0 1px}",
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

  function afficherValeurs(c) {
    var w = c.w;
    var libs = {}, textes = {};
    ((w.bloc_info && w.bloc_info.valeurs) || []).forEach(function (v) {
      libs[v.cle] = v.libelle;
      if (v.nombre === false) textes[v.cle] = true;
    });
    var zone = c.el.querySelector(".mac-vals");
    zone.innerHTML = "";
    var enAlerte = [];
    (w.valeurs || []).forEach(function (v) {
      var val = c.valeurs ? c.valeurs[v.cle] : undefined;
      var nb_ = c.nombres && c.nombres[v.cle] != null ? c.nombres[v.cle] : val;
      var ligne = document.createElement("div");
      ligne.className = "mac-val";
      var lib = document.createElement("span");
      lib.className = "lib";
      lib.textContent = libs[v.cle] || v.cle;
      var nb = document.createElement("span");
      nb.className = "v";
      nb.textContent = val == null || val === "" ? "—" : val;
      if (!textes[v.cle] && alerteDeclenchee(v.alerte, nb_)) { ligne.classList.add("alerte"); enAlerte.push(libs[v.cle] || v.cle); }
      ligne.appendChild(nb);
      ligne.appendChild(lib);
      zone.appendChild(ligne);
    });
    c.el.classList.toggle("alerte", enAlerte.length > 0);
    c.el.querySelector(".mac-point").title = enAlerte.length ? "Alerte : " + enAlerte.join(", ") : "";
  }

  /* ── Cartes ────────────────────────────────────────────────────────── */
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

  function creerCarte(w) {
    var el = document.createElement("div");
    el.className = "mac-carte aff-valeurs";
    el.setAttribute("data-id", w.id);
    el.innerHTML =
      '<div class="mac-ctete" title="Ouvrir la page"><span class="mac-nom"></span><span class="mac-point"></span>' +
      '<button type="button" class="mac-corb" title="Supprimer cet indicateur" aria-label="Supprimer cet indicateur">' + icone("corbeille") + "</button></div>" +
      '<div class="mac-vals"></div>' +
      '<div class="mac-indispo">Bloc indisponible à cette taille. Cliquez sur le titre pour ouvrir la page.</div>' +
      '<div class="mac-cadre"><div class="mac-attente">Chargement…</div><div class="mac-voile"></div></div>' +
      '<div class="mac-outils"></div>';
    var c = { el: el, iframe: null, valeurs: null, absences: 0, w: w };
    el.querySelector(".mac-nom").textContent = w.nom;
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
    o.innerHTML =
      '<span class="mac-esp"></span>' +
      '<button type="button" class="mac-btn" data-act="val" title="Valeurs affichées et alertes">' + icone("valeurs") + "</button>" +
      '<button type="button" class="mac-btn" data-act="nom" title="Renommer">' + icone("reglages") + "</button>" +
      '<button type="button" class="mac-btn' + (c.confirmer ? " mac-sup-ok" : "") + '" data-act="sup" title="Supprimer">' +
      (c.confirmer ? "Supprimer ?" : icone("corbeille")) + "</button>";
    o.onclick = function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      e.stopPropagation();
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
    mb.questionnaire({
      bloc: w.bloc_info,
      actuelles: c.valeurs || {},
      coches: coches,
      alertes: alertes,
      titre: "Modifier l'indicateur",
      sousTitre: "Capturé : " + w.bloc_info.libelle,
      nom: w.nom,
      bouton: "Enregistrer",
      envoyer: function (p) { return patcher(c, { nom: p.nom, valeurs: p.valeurs }); }
    });
  }

  function patcher(c, champs) {
    return api("/api/accueil/widgets/" + c.w.id, { method: "PATCH", body: champs })
      .then(function (w) {
        for (var k in champs) c.w[k] = w[k];
        c.el.querySelector(".mac-nom").textContent = c.w.nom;
        if (c.iframe) c.iframe.title = c.w.nom;
        afficherValeurs(c);
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
      '<li><span class="mac-num">2</span><span>Cliquez sur <span class="mac-capico" title="Bouton de capture">' + ICONE_CAPTURE + '</span> en bas à droite, ou faites <kbd>Alt</kbd>+<kbd>C</kbd>.</span></li>' +
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
    if (sauver) api("/api/accueil/prefs", { method: "PUT", body: { colonne_repliee: W.repliee } }).catch(function () {});
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
          c.el.classList.add("prete");
          afficherValeurs(c);
        })
        .catch(function () {
          // API momentanément indisponible : on garde les dernières valeurs.
          c.el.classList.add("prete");
        });
    });
  }

  function chargerSources() {
    if (window.MySifaBlocsSources) return Promise.resolve();
    return new Promise(function (ok) {
      var s = document.createElement("script");
      s.src = "/static/mysifa_blocs_sources.js" + (VERSION ? "?v=" + VERSION : "");
      s.onload = s.onerror = function () { ok(); };
      document.head.appendChild(s);
    });
  }

  function rafraichir() {
    if (document.hidden) return;
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
          '<rect x="14" y="32" width="110" height="34" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="22" y="45" font-size="8" font-weight="700" fill="var(--text)">Stocks à réapprovisionner</text><text x="22" y="60" font-size="13" font-weight="700" fill="var(--text)">6</text><text x="34" y="60" font-size="8" fill="var(--muted)">matières sous seuil</text>' +
          '<rect x="14" y="72" width="110" height="34" rx="7" fill="var(--card)" stroke="var(--danger)"/><text x="22" y="85" font-size="8" font-weight="700" fill="var(--text)">Départs programmés</text><circle cx="116" cy="82" r="3" fill="var(--danger)"/><text x="22" y="100" font-size="13" font-weight="700" fill="var(--danger)">1</text><text x="34" y="100" font-size="8" fill="var(--muted)">départ en attente</text>' +
          '<rect x="14" y="112" width="110" height="26" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="22" y="129" font-size="8" font-weight="700" fill="var(--text)">Cohésio 2 · En production</text>' +
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
        body: "<p>Un panneau s'ouvre : cochez <strong>jusqu'à 4 valeurs</strong>, dans l'ordre où vous voulez les voir. Une alerte facultative passe un <strong>nombre</strong> en rouge au-dessus, en dessous ou à égalité d'un seuil. Un texte (état, opérateur) s'affiche sans alerte.</p>",
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
        body: "<p>L'indicateur relit ses chiffres <strong>chaque minute</strong>, directement auprès de l'appli. Un point rouge signale une alerte. Un clic ouvre la page d'origine <strong>avec ses filtres</strong> : c'est là que l'on agit. Une période capturée (« 7 derniers jours ») reste glissante.</p>",
        illu: SVG +
          '<rect x="20" y="20" width="130" height="58" rx="8" fill="var(--card)" stroke="var(--danger)"/><text x="30" y="36" font-size="8.5" font-weight="700" fill="var(--text)">Temps de production</text><circle cx="140" cy="33" r="3" fill="var(--danger)"/>' +
          '<text x="30" y="56" font-size="13" font-weight="700" fill="var(--danger)">1h 12min</text><text x="30" y="70" font-size="7.5" fill="var(--muted)">Arrêts (min)</text>' +
          '<path d="M155 49h40" stroke="var(--accent)" stroke-width="1.6" marker-end="url(#fl)"/><defs><marker id="fl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--accent)"/></marker></defs>' +
          '<rect x="200" y="14" width="126" height="122" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="210" y="30" font-size="8.5" font-weight="700" fill="var(--text)">MyProd · Production</text>' +
          '<rect x="210" y="38" width="44" height="10" rx="4" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="232" y="45.5" font-size="6" fill="var(--accent)" text-anchor="middle">7 derniers j.</text>' +
          '<rect x="210" y="56" width="106" height="30" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="210" y="94" width="106" height="30" rx="6" fill="var(--bg)" stroke="var(--border)"/></svg>'
      },
      {
        icon: ICO('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
        title: "Personnaliser la colonne",
        body: "<p><span class=\"mguide-hl\">Personnaliser</span> permet de <strong>glisser</strong> chaque indicateur à sa place. Sous chacun : les curseurs changent les <strong>valeurs</strong> et leurs alertes, le crayon le <strong>renomme</strong>, la corbeille le supprime (deux clics). L'icône tableau, en haut, replie la colonne.</p>",
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
    window.addEventListener("resize", majHaut);

    racine.querySelector(".mac-perso").addEventListener("click", basculerEdition);
    racine.querySelector(".mac-demande").addEventListener("click", function () {
      if (window.MySifaBlocs && window.MySifaBlocs.demander) window.MySifaBlocs.demander();
    });
    racine.querySelector(".mac-repli").addEventListener("click", function () {
      W.repliee = !W.repliee;
      basculerRepli(true);
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
    setInterval(rafraichir, RAFRAICHISSEMENT_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) rafraichir(); });
  }

  /* Le portail n'est monté que pour un utilisateur connecté : on attend sa
     page, et un 401 sur l'API suffit à ne rien afficher (écran de connexion). */
  function demarrer() {
    Promise.all([api("/api/accueil/widgets"), api("/api/accueil/prefs")]).then(function (r) {
      var tous = r[0].widgets || [];
      // « desactive » (bloc coupé par le superadmin) et « inaccessible »
      // (droits retirés) : masqués, pas supprimés — ils reviennent avec l'accès.
      W.widgets = tous.filter(function (w) { return w.etat === "ok"; });
      W.disparus = tous.filter(function (w) { return w.etat === "disparu"; });
      W.repliee = !!r[1].colonne_repliee;
      return chargerSources().then(monter);
    }).catch(function () { /* non connecté ou API indisponible : pas de colonne */ });
  }

  // On attend la page du portail, aussi lente soit-elle : un poste chargé ne
  // doit pas perdre sa colonne parce que le portail a mis 15 s à s'afficher.
  if (document.querySelector(".portal-page")) {
    demarrer();
  } else {
    var guet = new MutationObserver(function () {
      if (!document.querySelector(".portal-page")) return;
      guet.disconnect();
      demarrer();
    });
    guet.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
