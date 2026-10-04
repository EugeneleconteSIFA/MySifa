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
 *   900-1199    colonne compacte de 172 px : valeur principale seule
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
      replier: '<path d="m15 18-6-6 6-6"/>',
      deplier: '<path d="m9 18 6-6-6-6"/>',
      fermer: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
      corbeille: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>',
      poignee: '<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>'
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
      // z-index 1, comme .portal-page : la page vient après la colonne dans le
      // document, donc ses voiles (guide, modales) passent devant elle. Les deux
      // ne se chevauchent pas — la page est décalée de la largeur de la colonne.
      "  #mysifa-accueil{position:fixed;left:0;top:var(--mac-top,0px);bottom:96px;width:var(--mac-w);z-index:1;padding:16px 0 0 16px;display:flex;flex-direction:column}",
      "  body.mysifa-accueil-on #root{margin-left:var(--mac-w)}",
      "  #mysifa-accueil.repliee{width:56px}",
      "  body.mysifa-accueil-on.mysifa-accueil-repliee #root{margin-left:56px}",
      "}",
      "@media (min-width:1600px){#mysifa-accueil{--mac-w:380px}}",
      "@media (min-width:900px) and (max-width:1199px){#mysifa-accueil{--mac-w:172px}}",
      "@media (max-width:899px){#mysifa-accueil{padding:12px 16px 0;width:100%}}",
      ".mac-tete{display:flex;align-items:center;gap:6px;margin:0 0 10px;padding-right:8px}",
      ".mac-titre{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted,#94a3b8);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".mac-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:30px;min-width:30px;padding:0 8px;border-radius:10px;cursor:pointer;",
      "  background:var(--card,#111827);color:var(--text2,#cbd5e1);border:1px solid var(--border,#1e293b);font:600 12px 'Segoe UI',system-ui,sans-serif}",
      ".mac-btn:hover{background:var(--bg,#0a0e17);color:var(--accent,#22d3ee)}",
      ".mac-btn.on{background:var(--accent-bg,rgba(34,211,238,.12));border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}",
      ".mac-liste{flex:1;overflow-y:auto;overflow-x:hidden;padding:0 8px 16px 0;display:flex;flex-direction:column;gap:10px}",
      "#mysifa-accueil.repliee .mac-liste,#mysifa-accueil.repliee .mac-titre,#mysifa-accueil.repliee .mac-perso,#mysifa-accueil.repliee .mac-avis{display:none}",
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
      "  .mac-val:nth-child(n+2){display:none}",
      "  .mac-val .lib{display:none}",
      "  .mac-perso,.mac-outils{display:none!important}",
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
      ".mac-poignee{cursor:grab}",
      ".mac-vide{border:1px dashed var(--border,#1e293b);border-radius:12px;padding:14px;color:var(--muted,#94a3b8);line-height:1.5}",
      ".mac-vide b{color:var(--text,#f1f5f9)}",
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

  function alerteDeclenchee(alerte, valeur) {
    if (!alerte || valeur == null || valeur === "") return false;
    if (alerte.op === "=") {
      var a = nombre(valeur), b = nombre(alerte.seuil);
      if (a !== null && b !== null && /^[\s\d.,\-]+$/.test(String(alerte.seuil))) return a === b;
      return String(valeur).trim().toLowerCase() === String(alerte.seuil).trim().toLowerCase();
    }
    var x = nombre(valeur), s = nombre(alerte.seuil);
    if (x === null || s === null) return false;
    return alerte.op === ">" ? x > s : x < s;
  }

  function afficherValeurs(c) {
    var w = c.w;
    var libs = {};
    ((w.bloc_info && w.bloc_info.valeurs) || []).forEach(function (v) { libs[v.cle] = v.libelle; });
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
      if (alerteDeclenchee(v.alerte, nb_)) { ligne.classList.add("alerte"); enAlerte.push(libs[v.cle] || v.cle); }
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
      '<button type="button" class="mac-corb" title="Supprimer ce widget" aria-label="Supprimer ce widget">' + icone("corbeille") + "</button></div>" +
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
      '<span class="mac-btn mac-poignee" title="Glisser pour déplacer">' + icone("poignee") + "</span>" +
      '<span class="mac-esp"></span>' +
      '<button type="button" class="mac-btn" data-act="nom" title="Renommer">' + icone("reglages") + "</button>" +
      '<button type="button" class="mac-btn' + (c.confirmer ? " mac-sup-ok" : "") + '" data-act="sup" title="Supprimer">' +
      (c.confirmer ? "Supprimer ?" : icone("corbeille")) + "</button>";
    o.onclick = function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      e.stopPropagation();
      if (b.getAttribute("data-act") === "nom") {
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

  /* ── Liste et glisser-déposer ──────────────────────────────────────── */
  function dessinerListe() {
    var liste = racine.querySelector(".mac-liste");
    if (!W.widgets.length) {
      liste.innerHTML = '<div class="mac-vide"><b>Aucun widget pour l\'instant.</b><br>' +
        "Dans une appli, cliquez sur le bouton de capture (ou Alt+C), puis sur un bloc : " +
        "il s'ajoute ici et se met à jour chaque minute.</div>";
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
    b.innerHTML = icone(W.repliee ? "deplier" : "replier");
    b.title = W.repliee ? "Afficher mes widgets" : "Replier la colonne";
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
        supprimer(c, "Widget retiré : « " + c.w.nom + " » — l'élément suivi n'existe plus.");
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
              supprimer(c, "Widget retiré : « " + c.w.nom + " » — l'élément suivi n'existe plus.");
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
      "Ouvrir la page d'origine depuis un widget pour creuser un chiffre."
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
    "accueil-widgets": { steps: [
      {
        icon: ICO('<rect x="3" y="3" width="7" height="18" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>'),
        title: "Mes widgets",
        body: "<p>La colonne de gauche réunit les chiffres que vous suivez au quotidien, pris directement dans les applis. Chacun se met à jour <strong>chaque minute</strong> et ouvre sa page d'origine au clic.</p>",
        extra: "__BULLETS__",
        illu: SVG +
          '<rect x="6" y="6" width="328" height="138" rx="10" fill="var(--bg)" stroke="var(--border)"/>' +
          '<text x="16" y="24" font-size="9" font-weight="700" fill="var(--muted)">MES WIDGETS</text>' +
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
        body: "<p>Dans n'importe quelle appli, le <strong>bouton de capture</strong> du coin bas-droit (ou <span class=\"mguide-tag\">Alt+C</span>) entoure de pointillés chaque bloc qu'on peut épingler. Cliquez sur celui qui vous intéresse.</p>",
        illu: SVG +
          '<rect x="6" y="6" width="328" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/>' +
          '<rect x="90" y="14" width="160" height="18" rx="6" fill="var(--card)" stroke="var(--accent)"/><text x="170" y="26" font-size="7.5" fill="var(--text)" text-anchor="middle">Capture : cliquez sur un bloc</text>' +
          '<rect x="18" y="42" width="140" height="42" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="4 3" stroke-width="1.5"/><text x="28" y="58" font-size="8" font-weight="700" fill="var(--text)">Temps</text><text x="28" y="74" font-size="11" font-weight="700" fill="var(--text)">1h 57min</text>' +
          '<rect x="170" y="42" width="140" height="42" rx="7" fill="none" stroke="var(--accent)" stroke-dasharray="4 3"/><text x="180" y="58" font-size="8" font-weight="700" fill="var(--text)">Quantités</text><text x="180" y="74" font-size="11" font-weight="700" fill="var(--text)">12 505 m</text>' +
          '<rect x="18" y="92" width="292" height="36" rx="7" fill="none" stroke="var(--accent)" stroke-dasharray="4 3"/><text x="28" y="114" font-size="8" fill="var(--muted)">Statut des machines</text>' +
          '<circle cx="312" cy="128" r="11" fill="var(--accent)"/><path d="M307 128h10M312 123v10" stroke="#fff" stroke-width="1.6"/></svg>'
      },
      {
        icon: ICO('<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'),
        title: "Choisir les valeurs",
        body: "<p>Un panneau s'ouvre : cochez <strong>jusqu'à 4 valeurs</strong>, dans l'ordre où vous voulez les voir. Pour chacune, une alerte facultative la passe <strong>en rouge</strong> au-dessus ou en dessous d'un seuil.</p>",
        illu: SVG +
          '<rect x="80" y="6" width="180" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/>' +
          '<text x="92" y="24" font-size="9" font-weight="700" fill="var(--text)">Ajouter à mon accueil</text>' +
          '<rect x="92" y="32" width="156" height="34" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="99" y="39" width="9" height="9" rx="2" fill="var(--accent)"/><text x="114" y="47" font-size="8" fill="var(--text)">Arrêts (min)</text>' +
          '<rect x="99" y="52" width="142" height="10" rx="3" fill="var(--card)" stroke="var(--border)"/><text x="103" y="60" font-size="6.5" fill="var(--danger)">Rouge au-dessus de 60</text>' +
          '<rect x="92" y="70" width="156" height="18" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="99" y="75" width="9" height="9" rx="2" fill="none" stroke="var(--muted)"/><text x="114" y="83" font-size="8" fill="var(--text2)">Calage (min)</text>' +
          '<rect x="92" y="96" width="156" height="14" rx="4" fill="var(--bg)" stroke="var(--accent)"/><text x="98" y="106" font-size="7" fill="var(--text)">Temps de production</text>' +
          '<rect x="160" y="118" width="88" height="18" rx="6" fill="var(--accent)"/><text x="204" y="130" font-size="7.5" fill="#fff" text-anchor="middle" font-weight="700">Ajouter à mon accueil</text></svg>'
      },
      {
        icon: ICO('<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>'),
        title: "Lire et ouvrir",
        body: "<p>Le widget relit ses chiffres <strong>chaque minute</strong>, directement auprès de l'appli. Un point rouge signale une alerte. Un clic ouvre la page d'origine <strong>avec ses filtres</strong> : c'est là que l'on agit. Une période capturée (« 7 derniers jours ») reste glissante.</p>",
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
        body: "<p><span class=\"mguide-hl\">Personnaliser</span> fait apparaître sous chaque widget une poignée pour le <strong>glisser</strong> à sa place, un crayon pour le <strong>renommer</strong> et la <strong>corbeille</strong> (deux clics). La flèche en haut replie la colonne.</p>",
        illu: SVG +
          '<rect x="80" y="10" width="180" height="130" rx="10" fill="var(--bg)" stroke="var(--border)"/>' +
          '<rect x="90" y="18" width="62" height="16" rx="5" fill="var(--card)" stroke="var(--border)"/><text x="121" y="29" font-size="7" fill="var(--text2)" text-anchor="middle">‹ MES WIDGETS</text>' +
          '<rect x="186" y="18" width="64" height="16" rx="5" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="218" y="29" font-size="7" fill="var(--accent)" text-anchor="middle">Terminer</text>' +
          '<rect x="90" y="42" width="160" height="44" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="98" y="56" font-size="8" font-weight="700" fill="var(--text)">Départs programmés</text>' +
          '<rect x="90" y="70" width="160" height="16" rx="0" fill="var(--bg)" stroke="var(--border)"/>' +
          '<text x="100" y="81" font-size="8" fill="var(--muted)">⠿</text><rect x="212" y="72" width="14" height="12" rx="3" fill="var(--card)" stroke="var(--border)"/><rect x="230" y="72" width="14" height="12" rx="3" fill="var(--danger)"/>' +
          '<rect x="90" y="94" width="160" height="38" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="4 3"/><text x="170" y="117" font-size="7.5" fill="var(--accent)" text-anchor="middle">déposer ici</text></svg>'
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
    racine.setAttribute("aria-label", "Mes widgets");
    racine.innerHTML =
      '<div class="mac-tete">' +
      '<button type="button" class="mac-btn mac-repli"></button>' +
      '<span class="mac-titre">Mes widgets</span>' +
      '<span class="mac-guide"></span>' +
      '<button type="button" class="mac-btn mac-perso" title="Réorganiser, redimensionner, renommer">' + icone("reglages") + "<span>Personnaliser</span></button>" +
      "</div>" +
      '<div class="mac-avis"></div>' +
      '<div class="mac-liste"></div>';
    var rootApp = document.getElementById("root");
    document.body.insertBefore(racine, rootApp || document.body.firstChild);
    document.body.classList.add("mysifa-accueil-on");
    majHaut();
    window.addEventListener("resize", majHaut);

    racine.querySelector(".mac-perso").addEventListener("click", basculerEdition);
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
      avis("Widget retiré : « " + w.nom + " » — ce bloc n'existe plus dans MySifa.");
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
