/*
 * MySifa — L'adresse de la page dit ce qu'on regarde.
 *
 * Convention (.claude/rules/url-etat.md) : le chemin désigne l'appli, la query
 * porte TOUT l'état visible — onglet, sous-onglet, filtres, tri, objet ouvert.
 * Une valeur égale au défaut de la page n'est pas écrite : l'adresse reste
 * courte, et un lien ancien garde son sens si un défaut change.
 *
 * La page décrit son état, ce fichier tient l'adresse :
 *
 *   MySifaUrl.ecrire({page:'production', sous:'saisies', machine:['A','B']},
 *                    {navigation:'production/saisies'});
 *
 * `navigation` est la clé de ce qui fait un « endroit » (onglet, sous-onglet,
 * objet ouvert). Quand elle change, l'adresse s'EMPILE : Retour y ramène.
 * Sinon (un filtre, un tri) elle se REMPLACE : dix filtres essayés ne font pas
 * dix retours pour sortir de la page.
 *
 *   MySifaUrl.surRetour(async function (params) { …réappliquer… });
 *
 * Pendant le rappel, toute écriture remplace : réappliquer un état ne doit
 * pas recréer l'entrée qu'on vient de quitter. Le rappel n'a PAS lieu pour un
 * recul que ce fichier a lui-même déclenché (voir plus bas).
 *
 * Revenir là d'où l'on vient (fermer une fiche, « ← Retour à la liste »)
 * RECULE dans l'historique au lieu d'empiler : sinon Retour, juste après,
 * rouvrirait la fiche qu'on vient de fermer. Le recul n'a lieu que si
 * l'adresse visée est exactement celle qu'on avait quittée ; un filtre
 * changé entre-temps fait empiler normalement.
 *
 * Une page embarquée (widget d'accueil, iframe) n'empile jamais : l'historique
 * d'un iframe se mêle à celui de la page qui le contient, et Retour sur
 * l'accueil ferait reculer le widget au lieu de la page.
 */
(function () {
  "use strict";
  if (window.MySifaUrl) return;

  // Paramètres qui n'appartiennent pas à l'état de la page : on ne les
  // efface pas en réécrivant l'adresse. bloc_… et capture sont lus puis
  // retirés par mysifa_blocs.js, next par l'écran de connexion.
  var ETRANGERS = /^(bloc_|capture$|embed$|next$)/;

  var navCourante = null;
  var enRetour = 0;
  // Recul demandé (history.back) dont le popstate n'est pas encore arrivé :
  // les écritures sont suspendues, c'est lui qui fixera l'adresse.
  var reculEnCours = false;
  // Écriture demandée pendant ce recul (une fenêtre fermée puis, dans le même
  // geste, un éditeur ouvert) : appliquée dès que le recul est arrivé.
  var enAttente = null;
  function finRecul() {
    reculEnCours = false;
    var a = enAttente; enAttente = null;
    if (a) ecrire(a.params, a.opts);
  }

  function embarque() {
    try {
      if (window.MySifaBlocs && window.MySifaBlocs.embarque) return true;
      return window.top !== window;
    } catch (e) { return true; }
  }

  function vide(v) {
    return v === undefined || v === null || v === false || v === "" ||
      (Array.isArray(v) && !v.length);
  }

  function construire(params) {
    var sp = new URLSearchParams();
    Object.keys(params || {}).forEach(function (k) {
      var v = params[k];
      if (vide(v)) return;
      if (Array.isArray(v)) v.forEach(function (x) { if (!vide(x)) sp.append(k, String(x)); });
      else sp.set(k, v === true ? "1" : String(v));
    });
    try {
      new URLSearchParams(location.search || "").forEach(function (v, k) {
        if (ETRANGERS.test(k)) sp.append(k, v);
      });
    } catch (e) { /* adresse illisible : on n'en garde rien */ }
    return sp.toString();
  }

  function lire(search) {
    var sp;
    try { sp = new URLSearchParams(search === undefined ? (location.search || "") : search); }
    catch (e) { sp = new URLSearchParams(); }
    return {
      // Une valeur, ou `defaut` si absente ou hors de `admises`.
      get: function (k, defaut, admises) {
        var v = sp.get(k);
        if (v === null || v === "") return defaut === undefined ? null : defaut;
        if (admises && admises.indexOf(v) === -1) return defaut === undefined ? null : defaut;
        return v;
      },
      tous: function (k) { return sp.getAll(k).filter(function (x) { return x !== ""; }); },
      a: function (k) { return sp.has(k); },
      brut: sp
    };
  }

  // Ancienne forme « #sous-onglet » : lue une fois pour ne casser aucun lien,
  // puis l'adresse est réécrite au format query par le premier ecrire().
  function hashHerite() {
    try { return (location.hash || "").replace(/^#\/?/, "").trim(); }
    catch (e) { return ""; }
  }

  function ecrire(params, opts) {
    opts = opts || {};
    var qs = construire(params);
    // `opts.chemin` : page dont le routeur change aussi le chemin (MyCoûts,
    // /pricing/mystock/12). Chemin et paramètres partent dans UNE entrée.
    var cible = (opts.chemin || location.pathname) + (qs ? "?" + qs : "") + (opts.hash ? "#" + opts.hash : "");
    var nav = opts.navigation === undefined ? navCourante : String(opts.navigation);
    var actuelle = location.pathname + location.search + location.hash;
    if (reculEnCours) { enAttente = { params: params, opts: opts }; return; }
    var st = history.state || {};
    var libre = !enRetour && !embarque() && navCourante !== null && nav !== navCourante;
    try {
      if (libre && st.depuisUrl === cible) {
        reculEnCours = true;
        // Filet si le popstate n'arrive jamais (navigateur qui l'avale).
        setTimeout(function () { if (reculEnCours) finRecul(); }, 1500);
        history.back();
        return;
      }
      if (libre) {
        history.pushState({ mysifaNav: nav, depuisUrl: actuelle }, "", cible);
      } else {
        // Même endroit : on garde d'où l'on venait, pour que la fermeture
        // recule encore après un filtre ou un tri.
        var etat = nav === st.mysifaNav ? Object.assign({}, st, { mysifaNav: nav }) : { mysifaNav: nav };
        if (cible !== actuelle || st.mysifaNav !== nav) history.replaceState(etat, "", cible);
      }
      navCourante = nav;
    } catch (e) { /* l'adresse est un confort, jamais un blocage */ }
  }

  function surRetour(fn) {
    window.addEventListener("popstate", function (ev) {
      var propre = reculEnCours;
      navCourante = ev.state && ev.state.mysifaNav !== undefined ? ev.state.mysifaNav : null;
      // Recul déclenché par ecrire() lui-même : la page est DÉJÀ dans l'état
      // que porte cette adresse (c'est elle qui l'a demandé). La réappliquer
      // annulerait ce que le même geste a ouvert entre-temps — on n'applique
      // que l'écriture mise en attente.
      if (propre) { finRecul(); return; }
      reculEnCours = false;
      enRetour++;
      var fin = function () { enRetour = Math.max(0, enRetour - 1); };
      try {
        var r = fn(lire(), ev);
        if (r && typeof r.then === "function") r.then(fin, fin);
        else fin();
      } catch (e) { fin(); }
    });
  }

  window.MySifaUrl = {
    lire: lire,
    ecrire: ecrire,
    surRetour: surRetour,
    hashHerite: hashHerite,
    construire: construire
  };
})();
