/*
 * MySifa — Démarrage des boutons flottants sur les pages qui ne le font pas.
 *
 * main.py injecte dans toute page connectée les scripts des boutons flottants
 * qui lui manquent (dock, post-it, assistant IA, calculette, messagerie), puis
 * ce fichier. Les pages qui incluaient déjà ces boutons les démarrent
 * elles-mêmes après avoir lu l'utilisateur ; les autres n'ont jamais appelé
 * MySifaDock.bootPageWidgets(). Ce script le fait à leur place, une fois la
 * page chargée.
 *
 * Réglages par appli (Paramètres › Audit › Widgets et tableaux de bord) :
 * window.__MYSIFA_BOUTONS__, posé dans le <head> par main.py avec le CSS qui
 * masque les boutons coupés. Rien à masquer ici.
 *
 * La messagerie démarre seule (chat_widget.js lit /api/auth/me) : elle n'est
 * pas concernée.
 */
(function () {
  "use strict";
  if (window.top !== window) return;   // page chargée dans un widget ou une iframe
  var conf = window.__MYSIFA_BOUTONS__ || {};
  function actif(k) { return (conf.off || []).indexOf(k) < 0; }

  // La page a déjà démarré ses boutons : leurs racines existent.
  function dejaDemarre() {
    return !!(document.getElementById("postit-dock-root") || document.getElementById("ai-chat-root"));
  }

  function poserUtilisateur(u) {
    window.__MYSIFA_UID__ = u.id;
    window.__MYSIFA_NOM__ = u.nom || "";
    window.__MYSIFA_ROLE__ = u.role || "";
    window.__MYSIFA_USER__ = { nom: u.nom || "", role: u.role || "" };
    if (!window.__MYSIFA_APP__ && conf.appli) window.__MYSIFA_APP__ = conf.appli;
  }

  // La calculette n'est montée par le dock que dans une liste d'applis
  // historique : le réglage par appli la remplace.
  function calculette() {
    if (!actif("calculette") || typeof window._calc_mount !== "function") return;
    if (!document.getElementById("_calc_fab")) window._calc_mount();
  }

  function demarrer() {
    var dock = window.MySifaDock;
    if (dejaDemarre()) {
      calculette();
      if (dock && typeof dock.layout === "function") dock.layout();
      return;
    }
    var suite = function () {
      if (dock && typeof dock.bootPageWidgets === "function") dock.bootPageWidgets();
      calculette();
      if (dock && typeof dock.layout === "function") dock.layout();
    };
    if (window.__MYSIFA_UID__ && window.__MYSIFA_USER__) { suite(); return; }
    fetch("/api/auth/me", { credentials: "include" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        if (!u || !u.id) return;          // écran de connexion, session expirée
        if (!window.__MYSIFA_UID__ || !window.__MYSIFA_USER__) poserUtilisateur(u);
        suite();
      })
      .catch(function () { /* sans utilisateur, pas de boutons */ });
  }

  // Laisse à la page le temps de démarrer elle-même (elle lit /api/auth/me
  // au chargement) : on n'intervient qu'ensuite, et seulement si rien n'a
  // démarré.
  function planifier() { setTimeout(demarrer, 1500); }
  if (document.readyState === "complete") planifier();
  else window.addEventListener("load", planifier, { once: true });
})();
