/* MySifa — barre « Reprendre où j'en étais »
 *
 * Les derniers écrans ouverts par l'utilisateur, rappelés en haut de page. La
 * liste vient du serveur (/api/portail/recents) et non du navigateur : dans
 * l'atelier on change de poste, et un historique gardé en localStorage ne suit
 * pas l'opérateur.
 *
 * La barre ne s'affiche que s'il y a quelque chose à reprendre. Un nouvel
 * arrivant, ou quelqu'un qui vient de vider son historique, ne voit pas une
 * bande vide occuper le haut de son écran.
 *
 * Écriture : window.MySifaRecents.enregistrer({cle, libelle, url, module}).
 * Le portail appelle cette fonction quand on ouvre un écran depuis un volet ou
 * une tuile ; les pages module pourront l'appeler à leur tour.
 */
(function () {
  'use strict';

  var API = '/api/portail/recents';
  var etat = { liste: [], barre: null };

  function svg(p, taille) {
    return '<svg width="' + taille + '" height="' + taille + '" viewBox="0 0 24 24" ' +
      'fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + p + '</svg>';
  }
  var ICO_HORLOGE = '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>';
  var ICO_FLECHE = '<path d="M5 12h13"/><path d="m12 6 6 6-6 6"/>';

  function retirerBarre() {
    if (etat.barre && etat.barre.parentNode) etat.barre.parentNode.removeChild(etat.barre);
    etat.barre = null;
    document.body.classList.remove('has-msf-recents');
  }

  function chip(rec) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'msf-rec';
    b.title = rec.libelle + (rec.module ? ' — ' + rec.module : '');

    var ico = document.createElement('span');
    ico.className = 'msf-rec-ico';
    ico.innerHTML = svg(ICO_FLECHE, 13);
    b.appendChild(ico);

    // textContent et jamais innerHTML : le libellé vient de la base, donc d'une
    // écriture antérieure du front. Une injection y serait rejouée sur chaque
    // page qui affiche la barre.
    if (rec.module) {
      var m = document.createElement('b');
      m.textContent = rec.module;
      b.appendChild(m);
    }
    var l = document.createElement('span');
    l.textContent = (rec.module ? '· ' : '') + rec.libelle;
    b.appendChild(l);

    b.addEventListener('click', function () { window.location.href = rec.url; });
    return b;
  }

  function dessiner() {
    retirerBarre();
    if (!etat.liste.length) return;

    var barre = document.createElement('div');
    barre.className = 'msf-rec-bar';
    barre.id = 'msf-recents';

    var lab = document.createElement('span');
    lab.className = 'msf-rec-lab';
    lab.innerHTML = svg(ICO_HORLOGE, 13);
    lab.appendChild(document.createTextNode("Reprendre où j'en étais"));
    barre.appendChild(lab);

    var liste = document.createElement('div');
    liste.className = 'msf-rec-liste';
    etat.liste.forEach(function (r) { liste.appendChild(chip(r)); });
    barre.appendChild(liste);

    var vider = document.createElement('button');
    vider.type = 'button';
    vider.className = 'msf-rec-vider';
    vider.textContent = 'Effacer';
    vider.title = "Effacer l'historique de reprise";
    vider.addEventListener('click', function () {
      fetch(API, { method: 'DELETE', credentials: 'include' })
        .then(function () { etat.liste = []; retirerBarre(); })
        .catch(function () {});
    });
    barre.appendChild(vider);

    document.body.insertBefore(barre, document.body.firstChild);
    document.body.classList.add('has-msf-recents');
    etat.barre = barre;
  }

  function charger() {
    return fetch(API, { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        etat.liste = (d && Array.isArray(d.recents)) ? d.recents : [];
        dessiner();
        return etat.liste;
      })
      .catch(function () { /* réseau absent : pas de barre, pas d'erreur visible */ });
  }

  function enregistrer(entree) {
    if (!entree || !entree.cle || !entree.url) return Promise.resolve();
    // keepalive : l'appel part alors que la navigation est déjà lancée.
    return fetch(API, {
      method: 'POST',
      credentials: 'include',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cle: entree.cle,
        libelle: entree.libelle || '',
        module: entree.module || '',
        url: entree.url,
      }),
    }).catch(function () {});
  }

  window.MySifaRecents = { enregistrer: enregistrer, recharger: charger };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', charger);
  } else {
    charger();
  }
})();
