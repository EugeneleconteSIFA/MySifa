/*
 * MySifa — Messagerie flottante (chat_widget.js) : son état dans l'adresse
 * (.claude/rules/url-etat.md).
 *
 * Injecté par main.py (_boutons_flottants) après les fichiers du widget, sur
 * toute page connectée où la messagerie est active. Une seule clé :
 *   chat=<id du canal>   panneau ouvert sur une conversation
 *   chat=ouvert          panneau ouvert, aucune conversation choisie
 * La clé vit à côté de celles de la page, qui ne la connaît pas : on enveloppe
 * MySifaUrl.ecrire pour qu'une écriture de la page la garde.
 *
 * Remplacement seulement, jamais d'entrée d'historique : la messagerie se
 * superpose à toutes les applis, et Retour doit continuer de reculer dans
 * l'appli elle-même, pas d'ouvrir et fermer la discussion.
 * À l'ouverture d'une adresse portant `chat=`, le panneau se rouvre sur ce
 * canal (lien partagé, rechargement).
 */
(function () {
  "use strict";
  if (window.__mysifaChatUrl) return;
  window.__mysifaChatUrl = true;
  try { if (window.top !== window) return; } catch (e) { return; }

  var derniere = null;

  function valeur() {
    var c = window._CW;
    if (!c || !c.open) return null;
    return c.activeId ? String(c.activeId) : "ouvert";
  }

  function ecrire() {
    try {
      var v = valeur();
      var sp = new URLSearchParams(location.search || "");
      if ((sp.get("chat") || null) === v) return;
      if (v) sp.set("chat", v); else sp.delete("chat");
      var qs = sp.toString();
      history.replaceState(history.state, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    } catch (e) { /* l'adresse est un confort */ }
  }

  function envelopper() {
    var U = window.MySifaUrl;
    if (!U || !U.ecrire || U.ecrire.__chat) return;
    var orig = U.ecrire;
    U.ecrire = function (params, opts) {
      var p = Object.assign({}, params || {});
      var v = valeur();
      if (v) p.chat = v; else delete p.chat;
      return orig.call(this, p, opts);
    };
    U.ecrire.__chat = true;
  }

  function declencheur() {
    return document.getElementById("cw-bubble") || document.getElementById("cw-bar");
  }

  function attendre(cond, max) {
    return new Promise(function (ok) {
      var n = 0;
      var t = setInterval(function () {
        var v = false;
        try { v = !!cond(); } catch (e) {}
        if (v || ++n > (max || 60)) { clearInterval(t); ok(v); }
      }, 250);
    });
  }

  function rouvrir() {
    var voulu = null;
    try { voulu = new URLSearchParams(location.search || "").get("chat"); } catch (e) {}
    if (!voulu) return Promise.resolve();
    return attendre(function () { return window._CW && declencheur(); }).then(function (pret) {
      if (!pret) return;
      var c = window._CW;
      if (!c.open) declencheur().click();
      if (!/^\d+$/.test(voulu)) return;
      return attendre(function () { return c.open && c.channels && c.channels.length; }, 40).then(function () {
        var id = Number(voulu);
        var existe = (c.channels || []).some(function (ch) { return Number(ch.id) === id; });
        if (existe && Number(c.activeId) !== id && c.selectChannel) return c.selectChannel(id);
      });
    });
  }

  function demarrer() {
    envelopper();
    rouvrir().catch(function () {}).then(function () {
      // Le widget ne signale ni ouverture ni changement de canal : on relève
      // son état deux fois par seconde, et on n'écrit que s'il a bougé.
      setInterval(function () {
        envelopper();
        var v = valeur();
        if (v !== derniere) { derniere = v; ecrire(); }
      }, 500);
    });
    // Une page qui réapplique une adresse ancienne au Retour : la messagerie,
    // elle, n'a pas bougé — on remet sa clé.
    window.addEventListener("popstate", function () { setTimeout(ecrire, 0); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
})();
