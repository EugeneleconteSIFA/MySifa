/* MySifa — visite guidée du nouveau portail.
 *
 * Quatre étapes, jouées une seule fois par personne et par poste, qui montrent
 * ce qui a changé : les menus de la barre d'icônes, le menu d'une application,
 * l'épinglage en favori, la barre de reprise. Chaque étape éclaire un vrai
 * élément de la page — pas une capture d'écran qui se périmerait au premier
 * changement de libellé.
 *
 * Une étape dont la cible est absente est sautée : un opérateur qui n'a ni ERP
 * ni historique de navigation ne voit que ce qui le concerne.
 *
 * Rejouable à tout moment : window.MySifaPortailTour.ouvrir().
 */
(function () {
  'use strict';

  // Le numéro fait partie de la clé : une prochaine visite guidée se rejouera
  // pour tout le monde sans qu'on ait à deviner qui avait vu la précédente.
  var CLE = 'mysifa_portail_tour_v1';

  var ETAPES = [
    {
      cible: '.portal-corner-stack',
      titre: 'Vos outils ont désormais un menu',
      texte: 'Profil, paramètres, calendrier, ERP : passez la souris sur une icône, ' +
             'son menu s\'ouvre et vous emmène directement au bon écran.',
    },
    {
      cible: '.portal-apps .portal-app',
      titre: 'Chaque application aussi',
      texte: 'Survolez une tuile, ou cliquez le chevron en haut à droite : ' +
             'les écrans du module s\'affichent sans passer par sa page d\'accueil.',
    },
    {
      cible: '.portal-apps .portal-app-star',
      titre: 'Épinglez ce que vous ouvrez tous les jours',
      texte: 'L\'étoile met une application en favori : elle remonte en première ' +
             'rangée, et vous pouvez masquer toutes les autres.',
    },
    {
      cible: '.msf-rec-bar',
      titre: 'Reprenez où vous en étiez',
      texte: 'Les derniers écrans que vous avez ouverts restent à portée, ' +
             'même depuis un autre poste.',
    },
  ];

  var etat = { i: 0, etapes: [], voile: null, trou: null, carte: null };

  function vu() {
    try { return localStorage.getItem(CLE) === '1'; } catch (e) { return true; }
  }
  function marquerVu() {
    try { localStorage.setItem(CLE, '1'); } catch (e) {}
  }

  function fermer() {
    document.body.classList.remove('mpt-actif');
    [etat.voile, etat.trou, etat.carte].forEach(function (n) {
      if (n && n.parentNode) n.parentNode.removeChild(n);
    });
    etat.voile = etat.trou = etat.carte = null;
    window.removeEventListener('resize', placer);
    window.removeEventListener('scroll', placer, true);
    document.removeEventListener('keydown', auClavier, true);
    marquerVu();
  }

  function auClavier(ev) {
    if (ev.key === 'Escape') { ev.preventDefault(); fermer(); }
    else if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); suivant(); }
  }

  function suivant() {
    if (etat.i >= etat.etapes.length - 1) { fermer(); return; }
    etat.i += 1;
    dessiner();
  }

  function cibleDe(etape) {
    var n = document.querySelector(etape.cible);
    return (n && n.getBoundingClientRect().width) ? n : null;
  }

  function placer() {
    var etape = etat.etapes[etat.i];
    if (!etape || !etat.trou) return;
    var n = cibleDe(etape);
    if (!n) return;
    var r = n.getBoundingClientRect();
    var m = 8;
    etat.trou.style.top = (r.top - m) + 'px';
    etat.trou.style.left = (r.left - m) + 'px';
    etat.trou.style.width = (r.width + 2 * m) + 'px';
    etat.trou.style.height = (r.height + 2 * m) + 'px';

    // La carte se pose là où il reste de la place : à gauche si la cible est
    // collée au bord droit (c'est le cas de la barre d'icônes), sinon dessous,
    // et au-dessus en dernier recours.
    var c = etat.carte.getBoundingClientRect();
    var vw = window.innerWidth, vh = window.innerHeight;
    var top, left;
    if (r.right > vw - 360) {
      left = Math.max(16, r.left - c.width - 20);
      top = Math.min(Math.max(16, r.top), vh - c.height - 16);
    } else if (r.bottom + c.height + 24 < vh) {
      top = r.bottom + 18;
      left = Math.min(Math.max(16, r.left + r.width / 2 - c.width / 2), vw - c.width - 16);
    } else {
      top = Math.max(16, r.top - c.height - 18);
      left = Math.min(Math.max(16, r.left + r.width / 2 - c.width / 2), vw - c.width - 16);
    }
    etat.carte.style.top = Math.round(top) + 'px';
    etat.carte.style.left = Math.round(left) + 'px';
  }

  function dessiner() {
    var etape = etat.etapes[etat.i];
    etat.carte.textContent = '';

    var eti = document.createElement('span');
    eti.className = 'mpt-etiquette';
    eti.textContent = 'Nouveau portail';
    etat.carte.appendChild(eti);

    var t = document.createElement('h3');
    t.className = 'mpt-titre';
    t.textContent = etape.titre;
    etat.carte.appendChild(t);

    var p = document.createElement('p');
    p.className = 'mpt-texte';
    p.textContent = etape.texte;
    etat.carte.appendChild(p);

    var pied = document.createElement('div');
    pied.className = 'mpt-pied';
    var points = document.createElement('div');
    points.className = 'mpt-points';
    etat.etapes.forEach(function (_e, i) {
      var d = document.createElement('span');
      d.className = 'mpt-point' + (i === etat.i ? ' actif' : '');
      points.appendChild(d);
    });
    pied.appendChild(points);

    var passer = document.createElement('button');
    passer.type = 'button';
    passer.className = 'mpt-passer';
    passer.textContent = 'Passer';
    passer.addEventListener('click', fermer);
    pied.appendChild(passer);

    var suiv = document.createElement('button');
    suiv.type = 'button';
    suiv.className = 'mpt-suivant';
    suiv.textContent = (etat.i === etat.etapes.length - 1) ? "J'ai compris" : 'Suivant';
    suiv.addEventListener('click', suivant);
    pied.appendChild(suiv);

    etat.carte.appendChild(pied);
    placer();
    suiv.focus();
  }

  function ouvrir() {
    if (etat.voile) return;
    document.body.classList.add('mpt-actif');
    // Les cibles absentes sont retirées maintenant : les points de progression
    // doivent compter les étapes réellement jouées.
    etat.etapes = ETAPES.filter(cibleDe);
    if (!etat.etapes.length) { document.body.classList.remove('mpt-actif'); return; }
    etat.i = 0;

    etat.voile = document.createElement('div');
    etat.voile.className = 'mpt-voile';
    etat.voile.addEventListener('click', fermer);
    etat.trou = document.createElement('div');
    etat.trou.className = 'mpt-trou';
    etat.carte = document.createElement('div');
    etat.carte.className = 'mpt-carte';
    etat.carte.setAttribute('role', 'dialog');
    etat.carte.setAttribute('aria-label', 'Présentation du nouveau portail');
    document.body.appendChild(etat.voile);
    document.body.appendChild(etat.trou);
    document.body.appendChild(etat.carte);

    window.addEventListener('resize', placer);
    window.addEventListener('scroll', placer, true);
    document.addEventListener('keydown', auClavier, true);
    dessiner();
  }

  window.MySifaPortailTour = { ouvrir: ouvrir, dejaVu: vu };

  // Démarrage automatique : le portail est rendu par JS après l'appel à
  // /api/auth/me, donc on attend qu'il existe — quelques secondes au plus, et
  // on renonce si la page visitée n'est pas le portail.
  function guetter() {
    if (vu()) return;
    var reste = 40;
    var t = setInterval(function () {
      reste -= 1;
      var pret = document.querySelector('.portal-apps .portal-app');
      if (pret) {
        clearInterval(t);
        setTimeout(ouvrir, 550);
      } else if (reste <= 0) {
        clearInterval(t);
      }
    }, 250);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', guetter);
  } else {
    guetter();
  }
})();
