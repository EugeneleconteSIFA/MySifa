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
      "  #mysifa-accueil{position:fixed;left:0;top:var(--mac-top,0px);bottom:96px;width:var(--mac-w);z-index:110;padding:16px 0 0 16px;display:flex;flex-direction:column}",
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
      ".mac-cadre iframe{display:block;width:100%;border:0;background:var(--bg,#0a0e17)}",
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
      ".mac-h-s .mac-val:nth-child(n+3){display:none}",
      ".mac-carte.aff-bloc .mac-vals{display:none}",
      "@media (min-width:900px) and (max-width:1199px){",
      "  .mac-carte .mac-cadre{position:absolute!important;left:-10000px!important;width:1100px!important;visibility:hidden!important}",
      "  .mac-carte .mac-cadre iframe{width:1100px!important;height:700px!important}",
      "  .mac-carte.aff-bloc .mac-vals{display:flex}",
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
      ".mac-carte.glisse{opacity:.5}",
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
    el.className = "mac-carte mac-h-" + w.hauteur + " aff-" + w.affichage;
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
    var iframe = document.createElement("iframe");
    iframe.name = "mysifa-bloc|" + encodeURIComponent(w.bloc) + "|" + encodeURIComponent(w.objet || "");
    iframe.title = w.nom;
    iframe.setAttribute("tabindex", "-1");
    iframe.setAttribute("aria-hidden", "true");
    if (w.affichage === "valeurs") cadre.classList.add("mac-hors");
    else iframe.style.height = Math.min(HAUTEURS_PX[w.hauteur], 299) + "px";
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
    if (c.w.affichage === "valeurs") { c.iframe.style.height = ""; return; }
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
      if (c.iframe.getAttribute("src")) return;
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
      '<span class="mac-btn" title="Glisser pour déplacer">' + icone("poignee") + "</span>" +
      ["s", "m", "l"].map(function (k) {
        return '<button type="button" class="mac-btn' + (w.hauteur === k ? " on" : "") + '" data-h="' + k + '" title="' +
          ({ s: "Petit", m: "Moyen", l: "Grand" })[k] + '">' + k.toUpperCase() + "</button>";
      }).join("") +
      (w.valeurs && w.valeurs.length
        ? '<button type="button" class="mac-btn" data-act="aff" title="Basculer bloc complet / valeurs seules">' +
          (w.affichage === "bloc" ? "Valeurs" : "Bloc") + "</button>"
        : "") +
      '<span class="mac-esp"></span>' +
      '<button type="button" class="mac-btn" data-act="nom" title="Renommer">' + icone("reglages") + "</button>" +
      '<button type="button" class="mac-btn' + (c.confirmer ? " mac-sup-ok" : "") + '" data-act="sup" title="Supprimer">' +
      (c.confirmer ? "Supprimer ?" : icone("corbeille")) + "</button>";
    o.onclick = function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      e.stopPropagation();
      if (b.hasAttribute("data-h")) {
        var h = b.getAttribute("data-h");
        patcher(c, { hauteur: h }).then(function () {
          c.el.className = c.el.className.replace(/mac-h-[sml]/, "mac-h-" + h);
          ajusterHauteur(c);
          dessinerOutils(c);
        });
      } else if (b.getAttribute("data-act") === "aff") {
        var aff = c.w.affichage === "bloc" ? "valeurs" : "bloc";
        patcher(c, { affichage: aff }).then(function () {
          c.el.classList.remove("aff-bloc", "aff-valeurs");
          c.el.classList.add("aff-" + aff);
          var cadre = c.el.querySelector(".mac-cadre");
          cadre.classList.toggle("mac-hors", aff === "valeurs");
          ajusterHauteur(c);
          dessinerOutils(c);
        });
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

  function patcher(c, champs) {
    return api("/api/accueil/widgets/" + c.w.id, { method: "PATCH", body: champs })
      .then(function (w) {
        for (var k in champs) c.w[k] = w[k];
        c.el.querySelector(".mac-nom").textContent = c.w.nom;
        c.iframe.title = c.w.nom;
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

  var glisse = null;
  function brancherGlisser(liste) {
    liste.addEventListener("dragstart", function (e) {
      if (!W.edition) { e.preventDefault(); return; }
      glisse = e.target.closest(".mac-carte");
      if (!glisse) return;
      glisse.classList.add("glisse");
      e.dataTransfer.effectAllowed = "move";
      try { e.dataTransfer.setData("text/plain", glisse.getAttribute("data-id")); } catch (err) { /* IE */ }
    });
    liste.addEventListener("dragover", function (e) {
      if (!glisse) return;
      e.preventDefault();
      var cible = e.target.closest(".mac-carte");
      if (!cible || cible === glisse) return;
      var r = cible.getBoundingClientRect();
      liste.insertBefore(glisse, e.clientY < r.top + r.height / 2 ? cible : cible.nextSibling);
    });
    liste.addEventListener("dragend", function () {
      if (!glisse) return;
      glisse.classList.remove("glisse");
      glisse = null;
      var ids = Array.prototype.map.call(liste.querySelectorAll(".mac-carte"), function (el) {
        return parseInt(el.getAttribute("data-id"), 10);
      });
      var parId = {};
      W.widgets.forEach(function (w) { parId[w.id] = w; });
      W.widgets = ids.map(function (id) { return parId[id]; }).filter(Boolean);
      api("/api/accueil/widgets-ordre", { method: "PUT", body: { ids: ids } })
        .catch(function (e) { avis(e.message); });
    });
  }

  function basculerEdition() {
    W.edition = !W.edition;
    racine.classList.toggle("edition", W.edition);
    racine.querySelector(".mac-perso").classList.toggle("on", W.edition);
    racine.querySelector(".mac-perso").lastChild.textContent = W.edition ? "Terminer" : "Personnaliser";
    Object.keys(W.cartes).forEach(function (id) {
      var c = W.cartes[id];
      c.el.draggable = W.edition;
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
      if (W.cartes[id].iframe.contentWindow === e.source) { c = W.cartes[id]; return true; }
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

  function rafraichir() {
    if (document.hidden) return;
    Object.keys(W.cartes).forEach(function (id) {
      var f = W.cartes[id].iframe;
      try { f.contentWindow.postMessage({ source: "mysifa-blocs", type: "rafraichir" }, ORIGINE); } catch (e) { /* pas encore chargée */ }
    });
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
    W.disparus.forEach(function (w) {
      api("/api/accueil/widgets/" + w.id, { method: "DELETE" }).catch(function () {});
      avis("Widget retiré : « " + w.nom + " » — ce bloc n'existe plus dans MySifa.");
    });

    setInterval(rafraichir, RAFRAICHISSEMENT_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) rafraichir(); });
  }

  /* Le portail n'est monté que pour un utilisateur connecté : on attend sa
     page, et un 401 sur l'API suffit à ne rien afficher (écran de connexion). */
  function attendrePortail(essais) {
    if (document.querySelector(".portal-page")) {
      Promise.all([api("/api/accueil/widgets"), api("/api/accueil/prefs")]).then(function (r) {
        var tous = r[0].widgets || [];
        // « desactive » (bloc coupé par le superadmin) et « inaccessible »
        // (droits retirés) : masqués, pas supprimés — ils reviennent avec l'accès.
        W.widgets = tous.filter(function (w) { return w.etat === "ok"; });
        W.disparus = tous.filter(function (w) { return w.etat === "disparu"; });
        W.repliee = !!r[1].colonne_repliee;
        monter();
      }).catch(function () { /* non connecté ou API indisponible : pas de colonne */ });
      return;
    }
    if (essais > 0) setTimeout(function () { attendrePortail(essais - 1); }, 300);
  }
  attendrePortail(40);
})();
