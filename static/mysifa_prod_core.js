/* ────────────────────────────────────────────────────────────────────
 * MySifa — Page /prod (standalone) — boilerplate
 *
 * Ce fichier sera rempli progressivement par les étapes 2e à 2l du
 * refactor. Pour l'instant : juste un bootstrap minimal pour vérifier
 * que la page coquille charge correctement.
 *
 * Activation : via le flag PROD_STANDALONE dans .env (par défaut OFF).
 * Tant que le flag est OFF, /prod passe par le monolithe html.py et ce
 * fichier n'est jamais chargé.
 * ──────────────────────────────────────────────────────────────────── */

(function(){
  'use strict';

  // Placeholder : juste pour vérifier que le script est bien chargé.
  // Aux étapes suivantes (2e+), ce bloc accueillera : helpers JS, state S,
  // loads, renders, checkAuth, doLogin, render(), bootstrap.
  console.info('[mysifa_prod_core] coquille chargée — étape 2d');

  // Exposition d'un marqueur pour faciliter le debugging dans la console.
  window.__MYSIFA_PROD_STANDALONE__ = {
    stage: '2d',
    description: 'Coquille standalone — contenu à venir',
    loadedAt: new Date().toISOString(),
  };
})();
