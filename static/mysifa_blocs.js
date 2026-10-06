/*
 * MySifa — Blocs capturables en widget d'accueil.
 *
 * Injecté dans TOUTES les pages HTML par main.py (même mécanisme que le
 * raccourci de création de tâche). Trois rôles, selon le contexte :
 *
 *   1. Page ouverte DANS un widget (iframe de l'accueil) : « mode embarqué ».
 *      La page ne montre plus que le bloc demandé et envoie ses valeurs clés
 *      à l'accueil par postMessage. Le bloc est celui de la vraie page : droits,
 *      filtres et calculs sont ceux de l'appli, rien n'est recalculé ici.
 *   2. Page normale qui contient des blocs capturables : bouton « Capturer »
 *      et raccourci Alt+C. Les blocs s'entourent d'un cadre ; un clic ouvre le
 *      questionnaire et crée le widget.
 *   3. Accueil (/) : charge mysifa_accueil.js, la colonne « Mes widgets ».
 *
 * Contrat côté page (voir .claude/rules/widgets-blocs.md) :
 *   data-bloc="appli.onglet.bloc"     nom stable, déclaré dans blocs_registre.py
 *   data-bloc-objet="12"              objet suivi (machine, dossier…)
 *   data-bloc-objet-libelle="Cohésio 2"  nom lisible de l'objet (facultatif)
 *   data-bloc-valeur-<cle>="…"        une valeur clé par attribut
 *
 * Toute donnée affichée passe par textContent ou esc() : jamais de HTML brut
 * venu de la page ou du serveur.
 */
(function () {
  "use strict";
  if (window.MySifaBlocs) return;

  var ORIGINE = location.origin;
  // Même version que ce script : main.py l'injecte avec ?v=APP_VERSION.
  var VERSION = (function () {
    var src = (document.currentScript && document.currentScript.src) || "";
    var m = src.match(/[?&]v=([^&]+)/);
    return m ? m[1] : "";
  })();
  var PREFIXE_VALEUR = "data-bloc-valeur-";

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
          var msg = (d && (d.detail || d.message)) || ("Erreur " + r.status);
          if (typeof msg !== "string") msg = "Requête refusée.";
          throw new Error(msg);
        }
        return d;
      });
    });
  }

  function selecteurBloc(nom, objet) {
    var css = window.CSS && CSS.escape ? CSS.escape : function (s) { return String(s).replace(/"/g, '\\"'); };
    var sel = '[data-bloc="' + css(nom) + '"]';
    if (objet) sel += '[data-bloc-objet="' + css(objet) + '"]';
    return sel;
  }

  /* Valeurs clés lues sur l'élément du bloc. « lignes » se déduit d'un tableau
     quand la page ne l'a pas déclarée. */
  function lireValeurs(el) {
    var out = {};
    for (var i = 0; i < el.attributes.length; i++) {
      var a = el.attributes[i];
      if (a.name.indexOf(PREFIXE_VALEUR) === 0) out[a.name.slice(PREFIXE_VALEUR.length)] = a.value;
    }
    if (!("lignes" in out)) {
      var lignes = el.querySelectorAll("[data-bloc-ligne]");
      if (!lignes.length) lignes = el.querySelectorAll("tbody tr");
      if (lignes.length) out.lignes = String(lignes.length);
    }
    return out;
  }

  /* Nombre à comparer pour une alerte, quand le texte affiché n'en est pas un
     (« 1h 57min » → data-bloc-nombre-calage="117"). */
  function lireNombres(el) {
    var out = {};
    for (var i = 0; i < el.attributes.length; i++) {
      var a = el.attributes[i];
      if (a.name.indexOf("data-bloc-nombre-") === 0) out[a.name.slice(17)] = a.value;
    }
    return out;
  }

  /* Contexte embarqué : posé par l'accueil dans le nom de l'iframe (il survit
     aux rechargements et aux réécritures d'URL), ou en paramètre d'URL pour
     tester une page à la main. */
  function contexteEmbarque() {
    var n = String(window.name || "");
    if (n.indexOf("mysifa-bloc|") === 0) {
      var p = n.split("|");
      return { nom: decodeURIComponent(p[1] || ""), objet: decodeURIComponent(p[2] || "") || null };
    }
    try {
      var q = new URLSearchParams(location.search);
      if (q.get("widget")) return { nom: q.get("widget"), objet: q.get("widget_objet") || null };
    } catch (e) { /* navigateur sans URLSearchParams */ }
    return null;
  }

  var EMBARQUE = window.parent !== window ? contexteEmbarque() : null;
  var crochetRafraichir = null;

  window.MySifaBlocs = {
    embarque: !!EMBARQUE,
    /* Une page peut fournir un rafraîchissement léger (recharger ses données
       sans recharger le document). Sans crochet, le widget recharge la page.
       Équivalent posable avant le chargement : window.mysifaBlocsRafraichir. */
    surRafraichir: function (fn) { crochetRafraichir = typeof fn === "function" ? fn : null; },
    lireValeurs: lireValeurs,
    lireNombres: lireNombres
  };

  if (EMBARQUE && EMBARQUE.nom) { modeEmbarque(EMBARQUE); return; }
  if (window.top !== window) return;

  if (location.pathname === "/") {
    var s = document.createElement("script");
    s.src = "/static/mysifa_accueil.js" + (VERSION ? "?v=" + VERSION : "");
    s.defer = true;
    document.head.appendChild(s);
  }
  modeCapture();

  /* ════════════════════════════════════════════════════════════════════
     1. Mode embarqué
     ════════════════════════════════════════════════════════════════════ */
  function modeEmbarque(ctx) {
    var html = document.documentElement;
    html.classList.add("mysifa-bloc-embed");
    var style = document.createElement("style");
    style.textContent = [
      "html.mysifa-bloc-embed,html.mysifa-bloc-embed body{margin:0!important;padding:0!important;min-height:0!important;height:auto!important}",
      // Un tableau plus haut ou plus large que le cadre défile dans le widget.
      "html.mysifa-bloc-embed{overflow:auto!important;scrollbar-width:thin}",
      "html.mysifa-bloc-embed body{overflow:visible!important}",
      "html.mysifa-bloc-embed .mysifa-bloc-cible{cursor:pointer}",
      "html.mysifa-bloc-embed body *:not(.mysifa-bloc-chemin):not(.mysifa-bloc-cible):not(.mysifa-bloc-cible *){display:none!important}",
      "html.mysifa-bloc-embed .mysifa-bloc-chemin{display:block!important;margin:0!important;padding:0!important;border:0!important;max-width:none!important;width:auto!important;min-width:0!important;min-height:0!important;height:auto!important;position:static!important;transform:none!important;overflow:visible!important;box-shadow:none!important;background:transparent!important;animation:none!important}",
      "html.mysifa-bloc-embed .mysifa-bloc-cible{display:block!important;position:static!important;margin:0!important;max-width:none!important;width:auto!important;",
      "  border:0!important;border-radius:0!important;box-shadow:none!important;background:transparent!important}",
      // Une animation d'entrée figée laisse le contenu à demi transparent.
      "html.mysifa-bloc-embed *,html.mysifa-bloc-embed *::before,html.mysifa-bloc-embed *::after{animation:none!important;transition:none!important}",
      // Le cadre se fond dans la carte du widget.
      "html.mysifa-bloc-embed{background:transparent!important}",
      "html.mysifa-bloc-embed body{background:var(--card,transparent)!important}",
      // Le widget porte déjà le nom : l'en-tête du bloc (titre, « Masquer »,
      // « + Ajouter », filtres) disparaît. Un contenu replié par l'utilisateur
      // dans la page s'affiche quand même dans le widget.
      "html.mysifa-bloc-embed .mysifa-bloc-cible [data-bloc-entete]{display:none!important}",
      "html.mysifa-bloc-embed .mysifa-bloc-cible [data-bloc-contenu]{display:block!important}"
    ].join("\n");
    (document.head || html).appendChild(style);

    var dernierEnvoi = "";
    var minuteurAbsence = null;
    var minuteurMaj = null;
    var observateurTaille = null;

    function envoyer(type, extra) {
      var msg = { source: "mysifa-blocs", type: type, nom: ctx.nom, objet: ctx.objet };
      for (var k in extra || {}) msg[k] = extra[k];
      try { window.parent.postMessage(msg, ORIGINE); } catch (e) { /* accueil fermé */ }
    }

    function isoler(cible) {
      var anciens = document.querySelectorAll(".mysifa-bloc-chemin,.mysifa-bloc-cible");
      for (var i = 0; i < anciens.length; i++) anciens[i].classList.remove("mysifa-bloc-chemin", "mysifa-bloc-cible");
      cible.classList.add("mysifa-bloc-cible");
      for (var p = cible.parentElement; p && p !== html; p = p.parentElement) p.classList.add("mysifa-bloc-chemin");
    }

    /* Le CSS ne suffit pas : un widget flottant qui pose son propre
       « display:… !important » sur un id (bulle de messagerie) l'emporte. Un
       style inline !important, lui, prime toujours. */
    function masquerHorsChemin(cible) {
      for (var n = cible; n && n.parentElement && n !== document.body; n = n.parentElement) {
        for (var c = n.parentElement.firstElementChild; c; c = c.nextElementSibling) {
          if (c === n || /^(SCRIPT|STYLE|LINK|META)$/.test(c.tagName)) continue;
          if (c.style.getPropertyValue("display") !== "none" || c.style.getPropertyPriority("display") !== "important") {
            c.style.setProperty("display", "none", "important");
          }
        }
      }
    }

    function surveillerAbsence() {
      clearTimeout(minuteurAbsence);
      minuteurAbsence = setTimeout(function () {
        if (document.querySelector(selecteurBloc(ctx.nom, ctx.objet))) return;
        // Les autres objets du même bloc sont là, pas celui-ci : il a disparu
        // (dossier clôturé…). Sinon c'est le bloc entier qui manque — page qui
        // change de mise en page selon la taille, onglet replié : on ne
        // supprime rien.
        var famille = ctx.objet && document.querySelector(selecteurBloc(ctx.nom, null));
        envoyer(famille ? "introuvable" : "absent", {});
      }, 20000);
    }

    function maj() {
      var cible = document.querySelector(selecteurBloc(ctx.nom, ctx.objet));
      if (!cible) return;
      if (!cible.classList.contains("mysifa-bloc-cible")) {
        isoler(cible);
        // La hauteur change une fois le reste de la page masqué : on la suit.
        if (window.ResizeObserver) {
          if (observateurTaille) observateurTaille.disconnect();
          observateurTaille = new ResizeObserver(function () { planifier(); });
          observateurTaille.observe(cible);
        }
      }
      masquerHorsChemin(cible);
      var etat = {
        valeurs: lireValeurs(cible),
        nombres: lireNombres(cible),
        objetLibelle: cible.getAttribute("data-bloc-objet-libelle") || null,
        hauteur: Math.ceil(cible.getBoundingClientRect().height)
      };
      var cle = JSON.stringify(etat);
      if (cle === dernierEnvoi) return;
      dernierEnvoi = cle;
      envoyer("etat", etat);
    }

    function planifier(mutations) {
      // Nos propres changements de classe ne doivent pas relancer la boucle.
      if (mutations && mutations.every(function (m) {
        return m.type === "attributes" && (m.attributeName === "class" || m.attributeName === "style");
      })) return;
      clearTimeout(minuteurMaj);
      minuteurMaj = setTimeout(maj, 150);
    }

    /* Le widget défile mais ne s'utilise pas : un clic n'agit jamais dans la
       page embarquée (bouton « Masquer », lien de fiche…). Il demande à
       l'accueil d'ouvrir la page d'origine, où l'on peut agir. */
    function verrouiller(e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      if (e.type === "click") envoyer("ouvrir", { nouvelOnglet: !!(e.metaKey || e.ctrlKey) });
    }
    ["click", "dblclick", "auxclick", "submit"].forEach(function (t) {
      document.addEventListener(t, verrouiller, true);
    });

    new MutationObserver(planifier).observe(html, {
      childList: true, subtree: true, characterData: true, attributes: true
    });
    planifier();
    surveillerAbsence();

    window.addEventListener("message", function (e) {
      if (e.origin !== ORIGINE || e.source !== window.parent) return;
      var d = e.data || {};
      if (d.source !== "mysifa-blocs" || d.type !== "rafraichir") return;
      dernierEnvoi = "";
      // Le crochet peut aussi être posé par la page avant que ce script ne
      // charge : window.mysifaBlocsRafraichir = function () { … }.
      var crochet = crochetRafraichir || (typeof window.mysifaBlocsRafraichir === "function" ? window.mysifaBlocsRafraichir : null);
      if (crochet) {
        try { crochet(); surveillerAbsence(); return; } catch (err) { /* repli : rechargement */ }
      }
      // Prévenir l'accueil : il masque le cadre le temps que la page se recharge.
      envoyer("rechargement", {});
      location.reload();
    });
  }

  /* ════════════════════════════════════════════════════════════════════
     2. Mode capture
     ════════════════════════════════════════════════════════════════════ */
  function modeCapture() {
    var registre = null;          // { nom: bloc } capturables pour cet utilisateur
    var registreOk = false;       // faux hors connexion (écran de login, site public)
    var valeursMax = 4;
    var survole = null;
    var chargement = null;
    var actif = false;
    var bouton = null, bandeau = null, bulle = null, panneau = null, styleOk = false;
    var minuteurScan = null;

    function chargerRegistre() {
      if (chargement) return chargement;
      chargement = api("/api/accueil/blocs").then(function (d) {
        registreOk = true;
        registre = {};
        (d.blocs || []).forEach(function (b) { registre[b.nom] = b; });
        valeursMax = d.valeurs_max || 4;
        return registre;
      }).catch(function () { registre = {}; return registre; });
      return chargement;
    }

    function blocsDeLaPage() {
      if (!registre) return [];
      var els = document.querySelectorAll("[data-bloc]");
      var out = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].closest("#mysifa-accueil")) continue;
        // Un bloc masqué (vue mobile seulement, onglet replié) ne se capture pas.
        if (!els[i].getClientRects().length) continue;
        if (registre[els[i].getAttribute("data-bloc")]) out.push(els[i]);
      }
      return out;
    }

    function poserStyle() {
      if (styleOk) return;
      styleOk = true;
      var st = document.createElement("style");
      st.textContent = [
        ".mysifa-cap-btn{position:fixed;right:24px;bottom:24px;z-index:8003;width:48px;height:48px;border-radius:50%;border:none;cursor:pointer;",
        "  display:flex;align-items:center;justify-content:center;background:var(--accent,#22d3ee);color:var(--bg,#0a0e17);",
        "  box-shadow:0 4px 16px rgba(34,211,238,.35);transition:transform .18s,box-shadow .18s}",
        ".mysifa-cap-btn:hover{transform:scale(1.08)}",
        ".mysifa-cap-btn svg{display:block;color:var(--bg,#0a0e17)}",
        ".mysifa-cap-btn.on{box-shadow:0 0 0 3px var(--accent-bg,rgba(34,211,238,.35)),0 6px 24px rgba(34,211,238,.5)}",
        // Tout ce qui n'est pas capturable s'efface : seuls les blocs restent lisibles.
        "html.mysifa-capture .mysifa-cap-attenue{opacity:.15!important;filter:grayscale(1) blur(1px)!important;transition:opacity .2s,filter .2s}",
        "html.perf-eco.mysifa-capture .mysifa-cap-attenue{filter:none!important;transition:none!important}",
        "html.mysifa-capture .mysifa-capturable{outline:2px solid var(--accent,#22d3ee)!important;outline-offset:4px;cursor:copy!important;",
        "  box-shadow:0 0 0 8px var(--accent-bg,rgba(34,211,238,.10)),0 0 28px rgba(34,211,238,.30)!important;border-radius:8px}",
        "html.mysifa-capture .mysifa-capturable.survol{outline-width:3px!important;background-color:var(--accent-bg,rgba(34,211,238,.12))!important;",
        "  box-shadow:0 0 0 8px var(--accent-bg,rgba(34,211,238,.18)),0 0 36px rgba(34,211,238,.55)!important}",
        ".mysifa-cap-bandeau{position:fixed;left:50%;top:12px;transform:translateX(-50%);z-index:2147482001;display:flex;gap:12px;align-items:center;",
        "  background:var(--card,#111827);color:var(--text,#f1f5f9);border:1px solid var(--accent,#22d3ee);border-radius:12px;padding:8px 10px 8px 14px;",
        "  font:13px 'Segoe UI',system-ui,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.2);max-width:calc(100vw - 32px)}",
        ".mysifa-cap-bandeau button,.mysifa-cap-pan button{font:600 12px 'Segoe UI',system-ui,sans-serif;border-radius:10px;padding:7px 12px;cursor:pointer;",
        "  background:var(--bg,#0a0e17);color:var(--text,#f1f5f9);border:1px solid var(--border,#1e293b)}",
        "@media (max-width:600px){.mysifa-cap-bandeau{left:12px;right:12px;transform:none;max-width:none}}",
        // Bulle de survol = aperçu de l'indicateur : nom et valeurs qu'il pourrait afficher.
        ".mysifa-cap-bulle{position:fixed;z-index:2147482002;pointer-events:none;background:var(--card,#111827);color:var(--text,#f1f5f9);",
        "  border:1px solid var(--accent,#22d3ee);box-shadow:0 8px 24px rgba(0,0,0,.35);font:12px 'Segoe UI',system-ui,sans-serif;",
        "  padding:8px 10px;border-radius:10px;display:none;width:260px;box-sizing:border-box}",
        ".mysifa-cap-bulle .cb-t{font-weight:700;margin-bottom:6px;color:var(--accent,#22d3ee)}",
        ".mysifa-cap-bulle .cb-v{display:flex;justify-content:space-between;gap:10px;padding:2px 0;border-top:1px solid var(--border,#1e293b)}",
        ".mysifa-cap-bulle .cb-v span:first-child{color:var(--muted,#94a3b8);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
        ".mysifa-cap-bulle .cb-v b{font-variant-numeric:tabular-nums;white-space:nowrap}",
        ".mysifa-cap-bulle .cb-a{margin-top:6px;color:var(--muted,#94a3b8);font-size:11px}",
        ".mysifa-cap-pan{position:fixed;top:0;right:0;bottom:0;width:380px;max-width:100vw;z-index:2147482003;overflow:auto;",
        "  background:var(--card,#111827);color:var(--text,#f1f5f9);border-left:1px solid var(--border,#1e293b);",
        "  box-shadow:-10px 0 30px rgba(0,0,0,.25);padding:20px;font:13px 'Segoe UI',system-ui,sans-serif;box-sizing:border-box}",
        ".mysifa-cap-pan h2{font-size:15px;margin:0 0 4px}",
        ".mysifa-cap-pan .cap-sous{color:var(--muted,#94a3b8);margin:0 0 18px}",
        ".mysifa-cap-pan .cap-lbl{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted,#94a3b8);margin:16px 0 8px}",
        ".mysifa-cap-pan .cap-val{border:1px solid var(--border,#1e293b);border-radius:10px;padding:8px 10px;margin-bottom:6px;background:var(--bg,#0a0e17)}",
        ".mysifa-cap-pan .cap-val label{display:flex;gap:8px;align-items:center;cursor:pointer}",
        ".mysifa-cap-pan .cap-val .cap-cur{margin-left:auto;color:var(--muted,#94a3b8);font-variant-numeric:tabular-nums}",
        ".mysifa-cap-pan .cap-num{display:inline-flex;width:18px;height:18px;border-radius:50%;align-items:center;justify-content:center;",
        "  font-size:11px;font-weight:700;background:var(--accent,#22d3ee);color:#fff}",
        ".mysifa-cap-pan .cap-alerte{display:flex;gap:6px;margin-top:8px}",
        ".mysifa-cap-pan .cap-sans-alerte{margin-top:6px;font-size:12px;color:var(--muted,#94a3b8)}",
        ".mysifa-cap-pan .cap-alerte select{flex:1}",
        ".mysifa-cap-pan .cap-alerte input{width:96px;flex:none}",
        ".mysifa-cap-pan select,.mysifa-cap-pan input[type=text]{font:13px 'Segoe UI',system-ui,sans-serif;background:var(--card,#111827);",
        "  color:var(--text,#f1f5f9);border:1px solid var(--border,#1e293b);border-radius:8px;padding:6px 8px;min-width:0}",
        ".mysifa-cap-pan input.cap-nom{width:100%;box-sizing:border-box}",
        ".mysifa-cap-pan select.cap-appli{width:100%;box-sizing:border-box;font:13px 'Segoe UI',system-ui,sans-serif;background:var(--card,#111827);color:var(--text,#f1f5f9);border:1px solid var(--border,#1e293b);border-radius:8px;padding:7px 8px}",
        ".mysifa-cap-pan textarea.cap-texte{width:100%;box-sizing:border-box;resize:vertical;font:13px 'Segoe UI',system-ui,sans-serif;background:var(--card,#111827);color:var(--text,#f1f5f9);border:1px solid var(--border,#1e293b);border-radius:8px;padding:8px}",
        ".mysifa-cap-pan .cap-choix{display:flex;gap:6px;flex-wrap:wrap}",
        ".mysifa-cap-pan .cap-choix button.on{background:var(--accent-bg,rgba(34,211,238,.12));border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}",
        ".mysifa-cap-pan .cap-err{color:var(--danger,#f87171);min-height:18px;margin-top:12px}",
        ".mysifa-cap-pan .cap-pied{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}",
        ".mysifa-cap-pan button.cap-ok{background:var(--accent,#22d3ee);border-color:var(--accent,#22d3ee);color:#fff}",
        ".mysifa-cap-toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:2147482004;background:var(--card,#111827);",
        "  color:var(--text,#f1f5f9);border:1px solid var(--border,#1e293b);border-radius:10px;padding:10px 16px;",
        "  font:13px 'Segoe UI',system-ui,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.2);display:flex;align-items:center;gap:12px}",
        ".mysifa-cap-toast button{font:600 12px 'Segoe UI',system-ui,sans-serif;border-radius:8px;padding:5px 10px;cursor:pointer;background:var(--accent,#22d3ee);color:#fff;border:none}"
      ].join("\n");
      document.head.appendChild(st);
    }

    function toast(texte, action, faire) {
      var t = document.createElement("div");
      t.className = "mysifa-cap-toast";
      t.textContent = texte;
      if (action) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = action;
        b.addEventListener("click", function () { t.remove(); faire(); });
        t.appendChild(b);
      }
      document.body.appendChild(t);
      setTimeout(function () { t.remove(); }, action ? 6000 : 2600);
    }

    /* Le bouton vit dans le dock commun des boutons flottants (mysifa_dock.js :
       messagerie, assistant, post-it…) comme bouton « extra » : le dock le
       range avec les autres et le masque avec eux. Les pages sans dock
       (MyQualité, Tâches, Coffre…) reçoivent le même aspect, et le bouton se
       pose seul au-dessus de ce qui flotte déjà en bas à droite. */
    function avecDock() {
      return !!(window.MySifaDock && typeof window.MySifaDock.layout === "function");
    }

    function placerSeul() {
      if (!bouton || avecDock()) return;
      var bas = 24, l = window.innerWidth, h = window.innerHeight;
      var els = document.body.querySelectorAll("body > *, body > * > *");
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        if (el === bouton || el.contains(bouton)) continue;
        var cs = getComputedStyle(el);
        if (cs.position !== "fixed" || cs.display === "none" || cs.visibility === "hidden") continue;
        var r = el.getBoundingClientRect();
        if (!r.width || !r.height || r.height > h / 2) continue;
        if (r.right < l - 90 || r.bottom < h - 260) continue;
        bas = Math.max(bas, Math.round(h - r.top + 12));
      }
      bouton.style.right = "24px";
      bouton.style.bottom = Math.min(bas, h - 60) + "px";
    }

    function ranger() {
      if (!bouton) return;
      if (avecDock()) {
        try { window.MySifaDock.layout(); } catch (e) { /* dock indisponible */ }
      } else {
        placerSeul();
      }
    }

    function creerBouton() {
      if (bouton) return;
      poserStyle();
      bouton = document.createElement("button");
      bouton.type = "button";
      bouton.id = "mysifa-cap-fab";
      bouton.className = "mysifa-dock-fab mysifa-dock-extra mysifa-cap-btn";
      bouton.title = "Ajouter un bloc à mes tableaux de bord (Alt+C)";
      bouton.setAttribute("aria-label", "Ajouter un bloc à mes tableaux de bord");
      bouton.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>';
      bouton.addEventListener("click", function () { actif ? quitter() : entrer(); });
      document.body.appendChild(bouton);
      ranger();
      window.addEventListener("resize", ranger);
      // Les autres boutons du dock arrivent souvent après nous.
      setTimeout(ranger, 800);
      setTimeout(ranger, 2500);
    }

    function scanner(muts) {
      // La bulle, le bandeau et le panneau changent sans cesse : ne pas
      // recalculer la page (et perdre le survol) pour eux.
      if (muts && muts.every(function (m) {
        return m.target.closest && m.target.closest(NOTRE_UI);
      })) return;
      clearTimeout(minuteurScan);
      minuteurScan = setTimeout(function () {
        if (actif) marquer();
      }, 400);
    }

    function marquer() {
      var anciens = document.querySelectorAll(".mysifa-capturable");
      for (var i = 0; i < anciens.length; i++) anciens[i].classList.remove("mysifa-capturable", "survol");
      var blocs = blocsDeLaPage();
      blocs.forEach(function (el) { el.classList.add("mysifa-capturable"); });
      attenuer(blocs);
      if (survole && survole.isConnected) survole.classList.add("survol");
    }

    /* Efface tout ce qui n'est ni un bloc capturable ni un de ses ancêtres :
       on remonte de chaque bloc jusqu'à <body>, et chaque frère hors de ce
       chemin est atténué. Les blocs gardent leur contenu intact. */
    var NOTRE_UI = ".mysifa-cap-pan,.mysifa-cap-bandeau,.mysifa-cap-btn,.mysifa-cap-bulle,.mysifa-cap-toast";
    function desattenuer() {
      var a = document.querySelectorAll(".mysifa-cap-attenue");
      for (var i = 0; i < a.length; i++) a[i].classList.remove("mysifa-cap-attenue");
    }
    function attenuer(blocs) {
      desattenuer();
      var chemin = new Set();
      blocs.forEach(function (el) {
        for (var n = el; n && n !== document.body; n = n.parentElement) chemin.add(n);
      });
      var parents = [document.body];
      chemin.forEach(function (n) { if (!n.classList.contains("mysifa-capturable")) parents.push(n); });
      parents.forEach(function (p) {
        for (var i = 0; i < p.children.length; i++) {
          var c = p.children[i];
          if (chemin.has(c) || /^(SCRIPT|STYLE|LINK|META|TEMPLATE)$/.test(c.tagName)) continue;
          if (c.matches(NOTRE_UI)) continue;
          c.classList.add("mysifa-cap-attenue");
        }
      });
    }

    function dessinerBulle(bloc) {
      var b = registre[bloc.getAttribute("data-bloc")] || {};
      var lib = bloc.getAttribute("data-bloc-objet-libelle");
      var vals = lireValeurs(bloc);
      bulle.innerHTML = "";
      var t = document.createElement("div");
      t.className = "cb-t";
      t.textContent = (b.libelle || "Bloc") + (lib ? " · " + lib : "");
      bulle.appendChild(t);
      (b.valeurs || []).slice(0, 8).forEach(function (v) {
        var l = document.createElement("div");
        l.className = "cb-v";
        var k = document.createElement("span");
        k.textContent = v.libelle;
        var x = document.createElement("b");
        x.textContent = vals[v.cle] != null && vals[v.cle] !== "" ? vals[v.cle] : "—";
        l.appendChild(k);
        l.appendChild(x);
        bulle.appendChild(l);
      });
      var a = document.createElement("div");
      a.className = "cb-a";
      a.textContent = "Cliquez pour choisir les valeurs à afficher (" + valeursMax + " au maximum).";
      bulle.appendChild(a);
    }

    function placerBulle(bloc) {
      var r = bloc.getBoundingClientRect();
      bulle.style.display = "block";
      var h = bulle.offsetHeight, w = bulle.offsetWidth;
      var haut = r.top - h - 10;
      if (haut < 8) haut = Math.min(window.innerHeight - h - 8, r.bottom + 10);
      if (haut < 8) haut = 8;
      bulle.style.top = haut + "px";
      bulle.style.left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8)) + "px";
    }

    function blocSous(cible) {
      var el = cible && cible.closest ? cible.closest(".mysifa-capturable") : null;
      return el || null;
    }

    function dansNotreUi(cible) {
      return !!(cible && cible.closest && cible.closest(".mysifa-cap-pan,.mysifa-cap-bandeau,.mysifa-cap-btn"));
    }

    function entrer() {
      chargerRegistre().then(function () {
        if (!blocsDeLaPage().length) {
          toast("Aucun bloc capturable sur cette page pour l'instant.", "Faire une demande", demander);
          return;
        }
        poserStyle();
        actif = true;
        document.documentElement.classList.add("mysifa-capture");
        if (bouton) bouton.classList.add("on");
        marquer();
        bandeau = document.createElement("div");
        bandeau.className = "mysifa-cap-bandeau";
        var txt = document.createElement("span");
        txt.textContent = "Capture : cliquez sur un bloc pour l'ajouter à vos tableaux de bord. Échap pour quitter.";
        var q = document.createElement("button");
        q.type = "button";
        q.textContent = "Quitter";
        q.addEventListener("click", quitter);
        bandeau.appendChild(txt);
        bandeau.appendChild(q);
        document.body.appendChild(bandeau);
        bulle = document.createElement("div");
        bulle.className = "mysifa-cap-bulle";
        document.body.appendChild(bulle);
      });
    }

    function quitter() {
      actif = false;
      document.documentElement.classList.remove("mysifa-capture");
      var anciens = document.querySelectorAll(".mysifa-capturable");
      for (var i = 0; i < anciens.length; i++) anciens[i].classList.remove("mysifa-capturable", "survol");
      desattenuer();
      if (bouton) bouton.classList.remove("on");
      if (bandeau) { bandeau.remove(); bandeau = null; }
      if (bulle) { bulle.remove(); bulle = null; }
      fermerPanneau();
    }

    /* Tant que la capture est active, aucun clic ne doit atteindre la page :
       un bloc est souvent cliquable (ouvrir une fiche), et la capture ne doit
       rien déclencher d'autre que le questionnaire. */
    function intercepter(e) {
      if (!actif || panneau || dansNotreUi(e.target)) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      if (e.type !== "click") return;
      var bloc = blocSous(e.target);
      if (bloc) ouvrirPanneau(bloc);
    }
    ["pointerdown", "mousedown", "mouseup", "click", "dblclick"].forEach(function (t) {
      document.addEventListener(t, intercepter, true);
    });

    document.addEventListener("mouseover", function (e) {
      if (!actif || panneau || !bulle) return;
      var anciens = document.querySelectorAll(".mysifa-capturable.survol");
      for (var i = 0; i < anciens.length; i++) anciens[i].classList.remove("survol");
      var bloc = blocSous(e.target);
      if (!bloc) { survole = null; bulle.style.display = "none"; return; }
      bloc.classList.add("survol");
      survole = bloc;
      dessinerBulle(bloc);
      placerBulle(bloc);
    }, true);

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && (actif || panneau)) {
        if (panneau) fermerPanneau(); else quitter();
        return;
      }
      if (!e.altKey || e.ctrlKey || e.metaKey || e.code !== "KeyC") return;
      var t = e.target;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      e.preventDefault();
      actif ? quitter() : entrer();
    });

    function fermerPanneau() {
      if (panneau) { panneau.remove(); panneau = null; }
    }

    /* Une page dont les filtres ne vivent pas dans l'URL (période de MyProd…)
       les déclare par window.mysifaBlocsContexte() : { bloc_periode: "last7",
       bloc_machine: ["C1"] }. Ils rejoignent l'adresse capturée, où la source
       du widget les relit. */
    function urlCapture() {
      var u = new URL(location.href);
      u.searchParams.delete("widget");
      u.searchParams.delete("widget_objet");
      if (typeof window.mysifaBlocsContexte === "function") {
        try {
          var ctx = window.mysifaBlocsContexte() || {};
          Object.keys(ctx).forEach(function (k) {
            if (k.indexOf("bloc_") !== 0) return;
            u.searchParams.delete(k);
            [].concat(ctx[k]).forEach(function (v) {
              if (v !== null && v !== undefined && v !== "") u.searchParams.append(k, String(v));
            });
          });
        } catch (e) { /* contexte indisponible : l'adresse seule suffit */ }
      }
      return u.pathname + u.search + u.hash;
    }

    /* Le questionnaire : valeurs à afficher (4 au maximum, dans l'ordre),
       une alerte facultative par valeur, le nom. Il sert à la création
       (capture d'un bloc) comme à la modification d'un indicateur existant
       (bouton « Valeurs » de l'accueil, via MySifaBlocs.questionnaire). */
    function questionnaire(o) {
      var bloc = o.bloc;
      var actuelles = o.actuelles || {};
      var etat = {
        coches: (o.coches && o.coches.length) ? o.coches.slice()
          : (bloc.valeurs.length ? [bloc.valeurs[0].cle] : []),
        alertes: JSON.parse(JSON.stringify(o.alertes || {}))
      };
      // Pas d'alerte sur une valeur texte (seuil = nombre) : celles posées
      // avant le 06/10/2026 tombent au prochain enregistrement.
      bloc.valeurs.forEach(function (v) { if (v.nombre === false) delete etat.alertes[v.cle]; });
      poserStyle();
      fermerPanneau();
      panneau = document.createElement("aside");
      panneau.className = "mysifa-cap-pan";
      panneau.setAttribute("role", "dialog");
      panneau.setAttribute("aria-label", o.titre);
      document.body.appendChild(panneau);

      function dessiner() {
        var h = "<h2>" + esc(o.titre) + "</h2>" +
          '<p class="cap-sous">' + esc(o.sousTitre) + "</p>";
        if (bloc.valeurs.length) {
          h += '<div class="cap-lbl">Valeurs à afficher (' + valeursMax + " au maximum)</div>";
          bloc.valeurs.forEach(function (v) {
            var rang = etat.coches.indexOf(v.cle);
            var al = etat.alertes[v.cle] || { op: "", seuil: "" };
            h += '<div class="cap-val"><label>' +
              '<input type="checkbox" data-cle="' + esc(v.cle) + '"' + (rang >= 0 ? " checked" : "") + ">" +
              (rang >= 0 ? '<span class="cap-num">' + (rang + 1) + "</span>" : "") +
              "<span>" + esc(v.libelle) + "</span>" +
              '<span class="cap-cur">' + esc(actuelles[v.cle] != null && actuelles[v.cle] !== "" ? actuelles[v.cle] : "—") + "</span></label>";
            if (rang >= 0 && v.nombre === false) {
              h += '<div class="cap-sans-alerte">Valeur texte : pas d\'alerte possible.</div>';
            } else if (rang >= 0) {
              h += '<div class="cap-alerte"><select data-alerte-op="' + esc(v.cle) + '">' +
                '<option value=""' + (al.op === "" ? " selected" : "") + ">Pas d'alerte</option>" +
                '<option value=">"' + (al.op === ">" ? " selected" : "") + ">Rouge au-dessus de</option>" +
                '<option value="<"' + (al.op === "<" ? " selected" : "") + ">Rouge en dessous de</option>" +
                '<option value="="' + (al.op === "=" ? " selected" : "") + ">Rouge si égal à</option></select>" +
                '<input type="text" data-alerte-seuil="' + esc(v.cle) + '" value="' + esc(al.seuil) + '"' +
                (al.op ? "" : ' style="display:none"') + ' inputmode="decimal" placeholder="Nombre"></div>';
            }
            h += "</div>";
          });
        }
        var nomActuel = panneau.querySelector("input.cap-nom");
        var nomVal = nomActuel ? nomActuel.value : (o.nom || "");
        h += '<div class="cap-lbl">Nom</div><input type="text" class="cap-nom" maxlength="80" value="' + esc(nomVal) + '">' +
          '<div class="cap-err" role="alert"></div>' +
          '<div class="cap-pied"><button type="button" data-act="annuler">Annuler</button>' +
          '<button type="button" class="cap-ok" data-act="ok">' + esc(o.bouton) + "</button></div>";
        panneau.innerHTML = h;
      }

      function erreur(t) { var z = panneau.querySelector(".cap-err"); if (z) z.textContent = t || ""; }

      panneau.addEventListener("change", function (e) {
        var t = e.target;
        if (t.matches("input[type=checkbox][data-cle]")) {
          var cle = t.getAttribute("data-cle");
          var i = etat.coches.indexOf(cle);
          if (t.checked && i < 0) {
            if (etat.coches.length >= valeursMax) { t.checked = false; erreur(valeursMax + " valeurs au maximum."); return; }
            etat.coches.push(cle);
          } else if (!t.checked && i >= 0) {
            etat.coches.splice(i, 1);
            delete etat.alertes[cle];
          }
          dessiner();
        } else if (t.matches("select[data-alerte-op]")) {
          var c = t.getAttribute("data-alerte-op");
          etat.alertes[c] = { op: t.value, seuil: (etat.alertes[c] || {}).seuil || "" };
          dessiner();
        }
      });
      panneau.addEventListener("input", function (e) {
        var t = e.target;
        if (t.matches("input[data-alerte-seuil]")) {
          var c = t.getAttribute("data-alerte-seuil");
          etat.alertes[c] = { op: (etat.alertes[c] || {}).op || "", seuil: t.value };
        }
        erreur("");
      });
      panneau.addEventListener("click", function (e) {
        var b = e.target.closest("button");
        if (!b) return;
        if (b.getAttribute("data-act") === "annuler") { fermerPanneau(); if (o.annuler) o.annuler(); return; }
        if (b.getAttribute("data-act") === "ok") valider(b);
      });

      function valider(b) {
        var nomW = (panneau.querySelector("input.cap-nom").value || "").trim();
        if (!nomW) { erreur("Nom de l'indicateur obligatoire."); return; }
        if (!etat.coches.length) { erreur("Cochez au moins une valeur."); return; }
        var valeurs = [];
        for (var i = 0; i < etat.coches.length; i++) {
          var cle = etat.coches[i];
          var al = etat.alertes[cle];
          if (al && al.op) {
            if (!String(al.seuil || "").trim()) { erreur("Seuil d'alerte manquant."); return; }
            if (isNaN(parseFloat(String(al.seuil).trim().replace(",", ".")))) { erreur("Seuil d'alerte : un nombre est attendu."); return; }
            valeurs.push({ cle: cle, alerte: { op: al.op, seuil: String(al.seuil).trim() } });
          } else {
            valeurs.push({ cle: cle, alerte: null });
          }
        }
        b.disabled = true;
        Promise.resolve(o.envoyer({ nom: nomW, valeurs: valeurs })).then(function () {
          fermerPanneau();
        }).catch(function (err) {
          b.disabled = false;
          erreur(err && err.message ? err.message : "Enregistrement impossible.");
        });
      }

      dessiner();
      var champ = panneau.querySelector("input.cap-nom");
      if (champ) champ.focus();
    }

    function ouvrirPanneau(el) {
      var nom = el.getAttribute("data-bloc");
      var bloc = registre[nom];
      if (!bloc) return;
      var objet = el.getAttribute("data-bloc-objet") || null;
      var objetLib = el.getAttribute("data-bloc-objet-libelle") || null;
      var url = urlCapture();
      questionnaire({
        bloc: bloc,
        actuelles: lireValeurs(el),
        titre: "Ajouter à mes tableaux de bord",
        sousTitre: "Capturé : " + bloc.libelle + (objetLib ? " · " + objetLib : ""),
        // Un objet suivi se nomme par lui-même (« Cohésio 2 »), sinon le bloc.
        nom: objetLib || bloc.libelle,
        bouton: "Ajouter",
        envoyer: function (p) {
          return api("/api/accueil/widgets", {
            method: "POST",
            body: { bloc: nom, objet: objet, url_capture: url, nom: p.nom, valeurs: p.valeurs, affichage: "valeurs", hauteur: "m" }
          }).then(function () {
            quitter();
            toast("Indicateur ajouté à vos tableaux de bord.");
          });
        }
      });
    }

    /* Demande de tableau de bord : un chiffre qui n'est pas encore
       capturable. Le serveur en fait une tâche du Gestionnaire de tâches,
       assignée aux superadmins (POST /api/accueil/demandes). */
    function demander() {
      poserStyle();
      fermerPanneau();
      panneau = document.createElement("aside");
      panneau.className = "mysifa-cap-pan";
      panneau.setAttribute("role", "dialog");
      panneau.setAttribute("aria-label", "Faire une demande de tableau de bord");
      panneau.innerHTML =
        "<h2>Faire une demande de tableau de bord</h2>" +
        '<p class="cap-sous">Décrivez le chiffre que vous aimeriez suivre. La demande est transmise aux administrateurs de MySifa.</p>' +
        '<div class="cap-lbl">Application concernée</div>' +
        '<select class="cap-appli"><option value="">Chargement…</option></select>' +
        '<div class="cap-lbl">Quel chiffre voulez-vous suivre ?</div>' +
        '<textarea class="cap-texte" maxlength="2000" rows="6" placeholder="Par exemple : le nombre de palettes parties cette semaine, par transporteur."></textarea>' +
        '<div class="cap-err" role="alert"></div>' +
        '<div class="cap-pied"><button type="button" data-act="annuler">Annuler</button>' +
        '<button type="button" class="cap-ok" data-act="ok">Envoyer la demande</button></div>';
      document.body.appendChild(panneau);
      var zone = panneau.querySelector(".cap-texte");
      var choix = panneau.querySelector(".cap-appli");
      var err = panneau.querySelector(".cap-err");
      zone.addEventListener("input", function () { err.textContent = ""; });
      choix.addEventListener("change", function () { err.textContent = ""; });
      // Depuis une appli (/stock, /planning-rh…), elle est présélectionnée ;
      // depuis l'accueil, le demandeur choisit.
      var ici = (location.pathname.split("/")[1] || "").replace(/-/g, "_");
      api("/api/accueil/demandes/applis").then(function (d) {
        choix.innerHTML = '<option value="">Choisir une application…</option>';
        (d.applis || []).forEach(function (a) {
          var o = document.createElement("option");
          o.value = a.code;
          o.textContent = a.label;
          if (a.code === ici) o.selected = true;
          choix.appendChild(o);
        });
      }).catch(function () { err.textContent = "Liste des applications indisponible — réessayez."; });
      panneau.addEventListener("click", function (e) {
        var b = e.target.closest("button");
        if (!b) return;
        if (b.getAttribute("data-act") === "annuler") { fermerPanneau(); return; }
        if (b.getAttribute("data-act") !== "ok") return;
        var texte = zone.value.trim();
        if (!choix.value) { err.textContent = "Choisissez l'application concernée."; choix.focus(); return; }
        if (texte.length < 10) { err.textContent = "Décrivez le chiffre en quelques mots (10 caractères au moins)."; return; }
        b.disabled = true;
        api("/api/accueil/demandes", { method: "POST", body: { texte: texte, appli: choix.value } })
          .then(function () { fermerPanneau(); toast("Demande envoyée."); })
          .catch(function (e2) { b.disabled = false; err.textContent = e2.message; });
      });
      zone.focus();
    }

    window.MySifaBlocs.questionnaire = function (o) {
      return chargerRegistre().then(function () { questionnaire(o); });
    };
    window.MySifaBlocs.demander = demander;

    new MutationObserver(scanner).observe(document.documentElement, { childList: true, subtree: true });
    chargerRegistre().then(function () { if (registreOk) creerBouton(); });
  }
})();
