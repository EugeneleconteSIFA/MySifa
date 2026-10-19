/* MySifa - Suivi des actions : rendu et pilotage de l'onglet Actions de MyProd.
 *
 * L'onglet s'appelait Reunions. Il ne sert plus qu'a suivre les actions ; le
 * rendu d'une reunion reste dans ce fichier (et ses tests) mais n'est plus
 * atteint depuis l'ecran.
 *
 * Ce fichier ne connait pas MyProd : il recoit un contenant et s'y installe.
 * C'est ce qui permet a l'onglet Reunions d'etre une page de MyProd comme
 * Vue d'ensemble ou Retour de prod, sans dupliquer la coquille.
 *
 * Le rendu des chiffres vient de `mysifa_retour_prod.js` (window.MySifaRetourProd),
 * partage avec l'onglet Retour de prod : une reunion ne doit pas montrer un
 * atelier different de celui qu'on regarde le reste du temps.
 *
 * API publique :
 *   MySifaReunions.monter(racine, opts)  -> installe l'ecran dans `racine`.
 *   MySifaReunions.reset()               -> oublie l'etat (changement d'onglet).
 * opts : { toast(msg,type) }
 */
(function(){
  'use strict';

  // Resolu a chaque appel, pas une fois au montage : les fonctions de rendu
  // pur s'en servent aussi, et elles s'appellent sans passer par monter().
  function rp(){ return window.MySifaRetourProd || null; }
  // Preference de confort, par navigateur : jamais un etat qui doit survivre.
  function lirePref(k){ try{ return window.localStorage.getItem(k); }catch(e){ return null; } }
  function ecrirePref(k, v){ try{ window.localStorage.setItem(k, v); }catch(e){} }
  var S = {
    vue: 'liste',                      // 'liste' | 'reunion'
    reunions: null,                    // liste chargee
    reunion: null,                     // reunion ouverte
    prod: null,                        // chiffres de la periode analysee
    personnes: [],                     // annuaire, charge une fois au contexte
    rechercheP: '',                    // frappe dans la recherche de participants
    jourPropose: null,
    titrePropose: '',
    ouverteId: null,                   // reunion laissee ouverte au demarrage
    notesLocal: null,                  // frappe non encore enregistree
    notesEtat: '',
    veille: null,                      // notes du point precedent, si demandees
    veilleOuverte: false,
    veilleChargee: false,
    plein: false,                      // reunion affichee seule, sans la coquille
    aSupprimer: null,                  // reunion dont la suppression est demandee
    erreur: null,
    contexteCharge: false,
    suivi: null,                       // toutes les actions, toutes reunions
    filtreResp: '',                    // '' = tous, '~' = non attribuees
    toutTermine: false,                // colonne Termine depliee en entier
    voirTermine: lirePref('reu.voirTermine') === '1',
    rechercheA: ''                     // recherche dans le suivi
  };
  var racineCourante = null;
  var notesTimer = null;
  var opts = {};

  function toast(msg, type){
    try{ if(opts.toast) opts.toast(msg, type); }catch(e){}
  }
  // Repli si mysifa_retour_prod.js n'a pas ete charge : il doit echapper lui
  // aussi. Un `String(x)` de secours laisserait passer la prose utilisateur.
  function _esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  function esc(s){ var R = rp(); return R ? R.escHtml(s) : _esc(s); }
  function escA(s){ var R = rp(); return R ? R.escAttr(s) : _esc(s); }
  function dateFr(s){
    var R = rp();
    if(R) return R.dateFr(s);
    // Meme regle que mysifa_retour_prod.js : AAAA-MM-JJ -> JJ/MM/AAAA.
    if(!s) return '';
    var d = String(s).slice(0, 10).split('-');
    return d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0] : String(s);
  }

  /* Reseau ------------------------------------------------------ */

  async function appel(path, init){
    var r = await fetch(path, Object.assign({credentials: 'include'}, init || {}));
    if(!r.ok){
      var msg = 'Erreur ' + r.status;
      try{ var j = await r.json(); if(j && j.detail) msg = j.detail; }catch(e){}
      throw new Error(msg);
    }
    return r.status === 204 ? null : r.json();
  }
  function supprimerA(path){
    return appel(path, {method: 'DELETE'});
  }
  function poster(path, corps){
    return appel(path, {method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(corps || {})});
  }

  /* Chargement -------------------------------------------------- */

  async function chargerContexte(){
    if(S.contexteCharge) return;
    var c = await appel('/api/reunions/contexte');
    S.personnes = c.personnes || [];
    S.jourPropose = c.jour_propose;
    S.titrePropose = c.titre_propose || '';
    S.ouverteId = c.ouverte ? c.ouverte.id : null;
    S.contexteCharge = true;
  }

  async function chargerListe(){
    var d = await appel('/api/reunions');
    S.reunions = d.reunions || [];
  }

  async function chargerSuivi(){
    var d = await appel('/api/reunions/actions');
    S.suivi = d.actions || [];
  }

  async function chargerReunion(id){
    var d = await appel('/api/reunions/' + encodeURIComponent(id));
    S.reunion = d.reunion;
    S.prod = d.prod;
    S.notesLocal = null;
    S.notesEtat = '';
    // Le point precedent est celui de la reunion qu'on vient d'ouvrir : garder
    // celui de la precedente afficherait les notes d'un autre jour.
    S.veille = null; S.veilleOuverte = false; S.veilleChargee = false;
  }

  async function chargerVeille(){
    if(!S.reunion) return;
    var d = await appel('/api/reunions/' + encodeURIComponent(S.reunion.id) + '/precedente');
    S.veille = d.precedente || null;
    S.veilleChargee = true;
  }

  /* Premier montage : contexte + liste, et reprise de la reunion laissee
     ouverte -- une reunion non close n'est pas une erreur, c'est une reunion
     qu'on n'a pas fini de tenir. */
  async function amorcer(){
    try{
      S.erreur = null;
      await chargerContexte();
      await chargerSuivi();
      if(S.allerApres){
        var a = S.allerApres; S.allerApres = null;
        await appliquerAller(a);
      }
    }catch(e){
      S.erreur = e.message;
    }
    peindre();
    if(S.allerFin){ var fin = S.allerFin; S.allerFin = null; fin(); }
  }

  /* Squelette --------------------------------------------------- */

  var ICONE_CORBEILLE =
      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<polyline points="3 6 5 6 21 6"/>'
    + '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
    + '<path d="M10 11v6"/><path d="M14 11v6"/>'
    + '<path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>';

  /* L'onglet ne sert qu'a suivre les actions : la barre porte la creation,
     la modale sert a creer comme a corriger une action. Les reunions et leur
     API restent en base, mais l'ecran ne les montre plus. */
  function squelette(){
    return ''
      + '<div class="reu-barre">'
      +   '<div class="reu-sep"></div>'
      +   '<button type="button" class="reu-btn" data-r="nouvelle">+ Nouvelle action</button>'
      + '</div>'
      + '<div id="reu-erreur"></div>'
      + '<div id="reu-vue"></div>'
      + '<div class="reu-modal-ov" id="reu-mov"><div class="reu-modal">'
      +   '<h3 id="reu-n-h">Nouvelle action</h3>'
      +   '<div class="reu-champ"><label for="reu-n-texte">Action</label>'
      +     '<input id="reu-n-texte" autocomplete="off"></div>'
      +   '<div class="reu-champ"><label for="reu-n-qui">Responsable</label>'
      +     '<select id="reu-n-qui"></select></div>'
      +   '<div class="reu-champ"><label for="reu-n-quand">&Eacute;ch&eacute;ance</label>'
      +     '<input type="date" id="reu-n-quand"></div>'
      +   '<div class="reu-fin">'
      +     '<button type="button" class="reu-btn danger" data-r="suppr-action" id="reu-n-sup" '
      +       'style="margin-right:auto">Supprimer</button>'
      +     '<button type="button" class="reu-btn ghost" data-r="annuler">Annuler</button>'
      +     '<button type="button" class="reu-btn" data-r="enreg-action">Enregistrer</button>'
      +   '</div>'
      + '</div></div>';
  }

  function pli(t){
    return String(t == null ? '' : t)
      .normalize ? String(t == null ? '' : t).normalize('NFD')
                     .replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
                 : String(t == null ? '' : t).toLowerCase().trim();
  }

  /* Rendu : liste -----------------------------------------------
     Fonctions pures : elles recoivent leurs donnees, ne lisent pas S et ne
     touchent pas au DOM. Exportees pour etre testables. */

  /* La colonne « Actions a mener » : ce qui a ete decide, pas son compteur.
     Un point de production se relit pour retrouver l'action, et « 2 a faire »
     obligeait a ouvrir la reunion pour savoir lesquelles. Ce qui reste a faire
     passe devant, ce qui est fait suit, barre. Au-dela de trois lignes la
     cellule dirait un paragraphe : le reste est compte, et la reunion s'ouvre.
     Repli sur le compteur si la liste ne porte pas encore le detail (API plus
     ancienne servie a un onglet deja ouvert). */
  var ACTIONS_VUES = 3;

  function rendreAMener(r){
    var l = (r && r.actions) || null;
    if(!l || !l.length){
      if(r && r.nb_actions){
        return r.actions_restantes
          ? '<span class="reu-pastille ouverte">' + r.actions_restantes + ' &agrave; faire</span>'
          : '<span class="reu-pastille close">' + r.nb_actions + ' faites</span>';
      }
      return '<span class="reu-pastille">&mdash;</span>';
    }
    var restent = [], faites = [];
    l.forEach(function(a){ (a.fait ? faites : restent).push(a); });
    var vues = restent.concat(faites).slice(0, ACTIONS_VUES);
    var reste = l.length - vues.length;
    return '<div class="reu-todos">'
      + vues.map(function(a){
          var meta = (a.responsable || a.echeance)
            ? '<em>' + esc(a.responsable || '')
              + (a.echeance ? (a.responsable ? ' · ' : '') + dateFr(a.echeance) : '')
              + '</em>'
            : '';
          return '<div class="reu-todo' + (a.fait ? ' fait' : '') + '">'
               + '<span class="reu-todo-p" aria-hidden="true"></span>'
               + '<span class="reu-todo-t"><span class="reu-todo-l">' + esc(a.texte)
               + '</span>' + meta + '</span></div>';
        }).join('')
      + (reste > 0
          ? '<div class="reu-todo-plus">+ ' + reste + ' autre' + (reste > 1 ? 's' : '') + '</div>'
          : '')
      + '</div>';
  }

  /* Rendu : suivi des actions ----------------------------------
     L'ecran d'accueil de l'onglet. Une reunion sert a decider ; ce qu'on vient
     y chercher ensuite, c'est ce qui reste a faire et qui le porte. Quatre
     colonnes par statut, toutes reunions confondues, filtrables par
     responsable. Le statut se change sur la carte, sans ouvrir la reunion. */

  var STATUTS = [
    {code: 'a_faire', libelle: '\u00c0 faire'},
    {code: 'en_cours', libelle: 'En cours'},
    {code: 'en_attente', libelle: 'En attente'},
    {code: 'termine', libelle: 'Termin\u00e9'}
  ];
  var TERMINE_VUES = 8;
  var NON_ATTRIBUE = '~';

  function statutDe(a){
    if(a && STATUTS.some(function(s){ return s.code === a.statut; })) return a.statut;
    return (a && a.fait) ? 'termine' : 'a_faire';
  }

  function selectStatut(a){
    var st = statutDe(a);
    return '<select class="reu-statut st-' + st + '" data-statut="' + escA(a.id) + '" '
      + 'aria-label="Statut de l\'action">'
      + STATUTS.map(function(s){
          return '<option value="' + s.code + '"' + (s.code === st ? ' selected' : '') + '>'
               + esc(s.libelle) + '</option>';
        }).join('')
      + '</select>';
  }

  function enRetard(a, aujourdhui){
    return !!(a.echeance && statutDe(a) !== 'termine'
              && String(a.echeance).slice(0, 10) < aujourdhui);
  }

  function responsables(l){
    var vus = {};
    (l || []).forEach(function(a){
      var n = String(a.responsable || '').trim();
      if(n) vus[n] = (vus[n] || 0) + (statutDe(a) === 'termine' ? 0 : 1);
    });
    return Object.keys(vus).sort(function(x, y){ return x.localeCompare(y, 'fr'); })
      .map(function(n){ return {nom: n, ouvertes: vus[n]}; });
  }

  /* Une tuile de kanban : l'action d'abord, en gros ; qui la porte et pour
     quand, en pastilles au-dessus ; la reunion d'origine en pied. La tuile se
     glisse d'une colonne a l'autre ; le selecteur reste pour le clavier et
     les ecrans tactiles, ou le glisser-deposer HTML5 ne fonctionne pas. */
  function initiales(nom){
    var m = String(nom || '').trim().split(/\s+/).filter(Boolean);
    if(!m.length) return '?';
    return (m[0][0] + (m.length > 1 ? m[m.length - 1][0] : '')).toUpperCase();
  }

  var ICONE_CAL =
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>';

  function rendreCarte(a, aujourdhui){
    var retard = enRetard(a, aujourdhui);
    var qui = String(a.responsable || '').trim();
    var st = statutDe(a);
    return '<article class="reu-carte st-' + st + (retard ? ' retard' : '') + '" '
      + 'draggable="true" data-carte="' + escA(a.id) + '">'
      + '<div class="reu-carte-haut">'
      +   '<span class="reu-carte-qui' + (qui ? '' : ' vide') + '">'
      +     '<span class="reu-avatar" aria-hidden="true">' + esc(initiales(qui)) + '</span>'
      +     esc(qui || 'Non attribuée') + '</span>'
      +   (a.echeance
            ? '<span class="reu-carte-quand" title="Échéance">' + ICONE_CAL
              + (retard ? 'En retard · ' : '') + esc(dateFr(a.echeance)) + '</span>'
            : '')
      + '</div>'
      + '<div class="reu-carte-t" data-editer="' + escA(a.id) + '" role="button" tabindex="0" '
      +   'title="Modifier l\'action">' + esc(a.texte) + '</div>'
      + '<div class="reu-carte-pied">'
      +   '<span></span>'
      +   selectStatut(a)
      + '</div>'
      + '</article>';
  }

  /* Le tableau ne donne pas la meme place a chaque colonne. « A faire » est
     toujours la plus longue : elle prend la moitie de la largeur et range ses
     tuiles sur plusieurs rangs, plutot que de descendre sur trois ecrans.
     « En cours » et « En attente » sont courtes par nature. « Termine » est de
     l'historique : repliee par defaut en une bande etroite, qui reste une
     cible de depot — on y glisse une tuile pour la clore sans deplier. */
  function filtrer(l, etat){
    var filtre = etat.filtreResp || '';
    var q = pli(etat.recherche || '');
    return l.filter(function(a){
      var n = String(a.responsable || '').trim();
      if(filtre === NON_ATTRIBUE && n) return false;
      if(filtre && filtre !== NON_ATTRIBUE && n !== filtre) return false;
      if(q && pli([a.texte, n].join(' ')).indexOf(q) === -1) return false;
      return true;
    });
  }

  function rendreBoard(l, etat){
    var aujourdhui = etat.aujourdhui || jourLocalIso(new Date());
    var vues = filtrer(l, etat);
    var voir = !!etat.voirTermine;
    var colonnes = STATUTS.map(function(s){
      var cartes = vues.filter(function(a){ return statutDe(a) === s.code; });
      var total = cartes.length;
      if(s.code === 'termine'){
        if(!voir){
          return '<section class="reu-col reu-rail st-termine" data-col="termine" '
            + 'data-r="voir-termine" title="Afficher les actions terminées">'
            + '<span class="reu-col-p" aria-hidden="true"></span>'
            + '<span class="reu-rail-t">Terminé · ' + total + '</span>'
            + '<span class="reu-rail-h">Déposer ici pour terminer</span>'
            + '</section>';
        }
        // Les plus recemment terminees d'abord : le reste est de l'historique.
        cartes.sort(function(x, y){
          return String(y.fait_le || '').localeCompare(String(x.fait_le || ''));
        });
      }
      var masquees = 0;
      if(s.code === 'termine' && !etat.toutTermine && total > TERMINE_VUES){
        masquees = total - TERMINE_VUES;
        cartes = cartes.slice(0, TERMINE_VUES);
      }
      var retards = cartes.filter(function(a){ return enRetard(a, aujourdhui); }).length;
      return '<section class="reu-col st-' + s.code + '" data-col="' + s.code + '">'
        + '<h3><span class="reu-col-p" aria-hidden="true"></span>' + esc(s.libelle)
        + (retards ? ' <span class="reu-col-retard">' + retards + ' en retard</span>' : '')
        + ' <span class="reu-col-n">' + total + '</span>'
        + (s.code === 'termine'
            ? '<button type="button" class="reu-col-replier" data-r="voir-termine" '
              + 'title="Replier" aria-label="Replier la colonne Terminé">×</button>'
            : '')
        + '</h3>'
        + '<div class="reu-col-cartes">'
        + (cartes.length
            ? cartes.map(function(a){ return rendreCarte(a, aujourdhui); }).join('')
            : '<div class="reu-col-vide">' + (s.code === 'a_faire' ? 'Rien à faire.' : 'Déposez une action ici.') + '</div>')
        + '</div>'
        + (masquees
            ? '<button type="button" class="reu-col-plus" data-r="tout-termine">'
              + 'Voir les ' + masquees + ' plus anciennes</button>'
            : '')
        + '</section>';
    }).join('');
    return '<div class="reu-board' + (voir ? ' avec-termine' : '') + '">' + colonnes + '</div>';
  }

  function rendreSuivi(l, etat){
    if(l === null || l === undefined) return '<div class="reu-vide">Chargement&hellip;</div>';
    etat = etat || {};
    if(!l.length){
      return '<div class="reu-vide">Aucune action pour l\'instant.<br>'
           + 'Ajoutez-en une avec « + Nouvelle action ».</div>';
    }
    var filtre = etat.filtreResp || '';
    var gens = responsables(l);
    var sansResp = l.filter(function(a){
      return !String(a.responsable || '').trim() && statutDe(a) !== 'termine';
    }).length;
    var barre = '<div class="reu-suivi-barre">'
      + '<div class="reu-filtres" role="group" aria-label="Filtrer par responsable">'
      + '<button type="button" class="reu-filtre' + (!filtre ? ' on' : '') + '" data-resp="">Tous</button>'
      + gens.map(function(g){
          return '<button type="button" class="reu-filtre' + (filtre === g.nom ? ' on' : '') + '" '
               + 'data-resp="' + escA(g.nom) + '">'
               + '<span class="reu-avatar" aria-hidden="true">' + esc(initiales(g.nom)) + '</span>'
               + esc(g.nom) + (g.ouvertes ? ' <b>' + g.ouvertes + '</b>' : '') + '</button>';
        }).join('')
      + (sansResp
          ? '<button type="button" class="reu-filtre' + (filtre === NON_ATTRIBUE ? ' on' : '') + '" '
            + 'data-resp="' + NON_ATTRIBUE + '">Non attribuées <b>' + sansResp + '</b></button>'
          : '')
      + '</div>'
      + '<input type="search" id="reu-suivi-q" class="reu-suivi-q" placeholder="Rechercher une action" '
      +   'aria-label="Rechercher une action" value="' + escA(etat.recherche || '') + '">'
      + '<button type="button" class="reu-filtre' + (etat.voirTermine ? ' on' : '') + '" '
      +   'data-r="voir-termine" aria-pressed="' + (etat.voirTermine ? 'true' : 'false') + '">'
      +   (etat.voirTermine ? 'Masquer les terminées' : 'Afficher les terminées') + '</button>'
      + '</div>';
    return barre + '<div id="reu-board-zone">' + rendreBoard(l, etat) + '</div>';
  }

  function rendreAccueil(reunions, suivi, etat){
    return rendreSuivi(suivi, etat);
  }

  function rendreListe(l){
    if(l === null || l === undefined) return '<div class="reu-vide">Chargement&hellip;</div>';
    if(!l.length){
      return '<div class="reu-vide">Aucune r&eacute;union enregistr&eacute;e.<br>'
           + 'Lancez un point de production : la p&eacute;riode analys&eacute;e sera la '
           + 'derni&egrave;re journ&eacute;e travaill&eacute;e.</div>';
    }
    return '<table class="reu-tbl"><thead><tr><th>R&eacute;union</th>'
      + '<th>P&eacute;riode</th><th>Participants</th>'
      + '<th>Actions &agrave; mener</th><th></th></tr></thead><tbody>'
      + l.map(function(r){
          var periode = r.date_debut === r.date_fin
            ? dateFr(r.date_debut)
            : dateFr(r.date_debut) + ' → ' + dateFr(r.date_fin);
          // Sans machine retenue, la reunion regarde tout l'atelier : le dire
          // vaut mieux qu'une cellule vide, qu'on lirait comme une donnee
          // manquante.
          var perimetre = (r.machines && r.machines.length)
            ? r.machines.join(' · ')
            : (r.machine || 'Toutes les machines');
          return '<tr data-id="' + escA(r.id) + '">'
            + '<td><div class="reu-nom-cell">' + esc(r.titre)
            + (r.ouverte ? ' <span class="reu-pastille ouverte">en cours</span>' : '')
            + '</div>'
            + '<div class="reu-sous">' + esc(r.ouverte_par)
            + (r.a_des_notes ? ' · notes' : ' · sans notes') + '</div></td>'
            + '<td>' + esc(periode)
            + (perimetre ? '<div class="reu-sous">' + esc(perimetre) + '</div>' : '') + '</td>'
            + '<td><div class="reu-part-liste">'
            + esc((r.participants || []).join(', ') || '—') + '</div></td>'
            + '<td class="reu-td-act">' + rendreAMener(r) + '</td>'
            + '<td class="reu-td-sup"><button type="button" class="reu-sup" '
            + 'data-suppr-reunion="' + escA(r.id) + '" '
            + 'data-suppr-titre="' + escA(r.titre || '') + '" '
            + 'title="Supprimer la r&eacute;union" '
            + 'aria-label="Supprimer la r&eacute;union">' + ICONE_CORBEILLE + '</button></td>'
            + '</tr>';
        }).join('')
      + '</tbody></table>';
  }

  /* Rendu : reunion --------------------------------------------- */

  function rendreReunion(r, prod, etat){
    if(!r) return '<div class="reu-vide">Chargement&hellip;</div>';
    etat = etat || {};
    var machines = (prod && prod.machines) || [];
    var sous = 'Ouverte par ' + esc(r.ouverte_par || '—') + ' le ' + esc(dateFr(r.ouverte_le))
             + (r.statut === 'close' ? ' · close le ' + esc(dateFr(r.close_le)) : '');
    return ''
      + '<div class="reu-hdr">'
      +   '<div><input class="reu-nom" id="reu-titre" placeholder="Titre de la r&eacute;union" '
      +     'value="' + escA(r.titre || '') + '">'
      +     '<div class="reu-sous">' + sous + '</div></div>'
      +   '<div class="reu-sep" style="flex:1"></div>'
      +   '<div class="reu-meta">'
      +     '<div class="reu-champ"><label for="reu-du">Du</label>'
      +       '<input type="date" id="reu-du" value="' + escA(r.date_debut || '') + '"></div>'
      +     '<div class="reu-champ"><label for="reu-au">Au</label>'
      +       '<input type="date" id="reu-au" value="' + escA(r.date_fin || '') + '"></div>'
      +     '<div class="reu-champ reu-machines"><label>Machines</label>'
      +       rendreMachines(machines, r.machines, etat.horsProd) + '</div>'
      +     '<button type="button" class="reu-btn ghost" data-r="plein" '
      +       'title="' + (etat.plein ? '&Eacute;chap pour revenir' : 'La r&eacute;union seule, sans la barre lat&eacute;rale ni l\'en-t&ecirc;te') + '">'
      +       (etat.plein ? 'Quitter le plein &eacute;cran' : 'Plein &eacute;cran') + '</button>'
      +     '<button type="button" class="reu-btn ghost" data-r="imprimer">Imprimer</button>'
      +     '<button type="button" class="reu-btn" data-r="clore">'
      +       (r.ouverte ? 'Clore la r&eacute;union' : 'Rouvrir la r&eacute;union') + '</button>'
      +   '</div>'
      + '</div>'
      + '<div class="reu-split">'
      +   '<div id="reu-prod"><div class="reu-vide">Chargement des donn&eacute;es de production&hellip;</div></div>'
      +   '<aside class="reu-colonne">'
      +     '<h3>Participants</h3>'
      +     '<div class="reu-hint">Qui est autour de la table.</div>'
      +     '<div id="reu-participants">'
      +       rendreParticipants(r.participants, etat.personnes, etat.recherche)
      +     '</div>'
      +     '<div class="reu-bloc">'
      +       '<div class="reu-bloc-hdr"><h3>Notes</h3>'
      +         '<button type="button" class="reu-veille-btn'
      +           (etat.veilleOuverte ? ' actif' : '') + '" data-r="veille" id="reu-veille-btn" '
      +           'aria-pressed="' + (etat.veilleOuverte ? 'true' : 'false') + '" '
      +           'aria-controls="reu-notes-zone">'
      +           libelleVeille(etat.veilleOuverte) + '</button>'
      +       '</div>'
      +       '<div id="reu-notes-zone">' + rendreZoneNotes(etat.notes, etat.veilleOuverte) + '</div>'
      +     '</div>'
      +     '<div class="reu-bloc">'
      +       '<h3>Actions</h3>'
      +       '<div class="reu-hint">Ce qui a &eacute;t&eacute; d&eacute;cid&eacute;, et par qui.</div>'
      +       '<div id="reu-actions">' + rendreActions(r.actions || []) + '</div>'
      +       '<datalist id="reu-personnes">'
      +         (etat.personnes || []).map(function(p){
                  return '<option value="' + escA(p.nom) + '">';
                }).join('')
      +       '</datalist>'
      +       '<div class="reu-actform">'
      +         '<input id="reu-a-txt" placeholder="Action &agrave; faire">'
      +         '<div class="reu-duo"><input id="reu-a-qui" placeholder="Qui" list="reu-personnes">'
      +           '<input type="date" id="reu-a-quand" title="Pour quand"></div>'
      +         '<button type="button" class="reu-btn" data-r="ajout-action">Ajouter l\'action</button>'
      +       '</div>'
      +     '</div>'
      +   '</aside>'
      + '</div>';
  }

  function libelleVeille(ouverte){
    return ouverte ? 'Notes du jour' : 'Point pr&eacute;c&eacute;dent';
  }

  /* Un seul encadre, deux contenus. Les notes du point precedent se lisent a
     l'endroit meme des notes du jour, dans le meme cadre : cote a cote, la
     colonne doublait de hauteur et il fallait comparer de haut en bas.
     Le contenu precedent est en lecture seule et sans enregistrement — un
     point deja tenu ne se corrige pas depuis celui d'aujourd'hui, et une
     frappe distraite ne doit surtout pas partir dans les notes du jour. */
  function rendreZoneNotes(etatNotes, ouverte){
    if(!ouverte){
      return '<div class="reu-hint">Ce qui est abord&eacute; pendant le point.</div>'
        + '<textarea class="reu-notes" id="reu-notes" '
        + 'placeholder="Ce qu\'on se dit, ce qu\'on constate&hellip;"></textarea>'
        + '<div class="reu-sauve" id="reu-notes-etat">' + esc(etatNotes || '') + '</div>';
    }
    if(!S.veilleChargee){
      return '<div class="reu-hint">Point pr&eacute;c&eacute;dent.</div>'
        + '<div class="reu-sauve">Chargement&hellip;</div>';
    }
    var v = S.veille;
    if(!v){
      return '<div class="reu-hint">Point pr&eacute;c&eacute;dent.</div>'
        + '<div class="reu-sauve">Aucun point de production avant celui-ci.</div>';
    }
    var quand = dateFr(v.date_debut);
    if(v.date_fin && v.date_fin !== v.date_debut) quand += ' au ' + dateFr(v.date_fin);
    return '<div class="reu-hint">Point du ' + esc(quand)
      + (v.titre && v.titre !== v.date_debut ? ' &middot; ' + esc(v.titre) : '')
      + ' &mdash; lecture seule.</div>'
      + '<textarea class="reu-notes lecture" readonly '
      + 'aria-label="Notes du point pr&eacute;c&eacute;dent" '
      + 'placeholder="Ce point n\'a pas de notes.">' + esc(v.notes || '') + '</textarea>'
      + '<div class="reu-sauve">Notes fig&eacute;es &mdash; repasse aux notes du jour pour &eacute;crire.</div>';
  }

  /* Comme les participants : seule la zone se repeint. Repeindre la colonne
     entiere ferait perdre le curseur dans les notes en cours de frappe. */
  function peindreNotes(rac){
    var zone = rac.querySelector('#reu-notes-zone');
    if(zone){
      zone.innerHTML = rendreZoneNotes(S.notesEtat, S.veilleOuverte);
      var ta = zone.querySelector('#reu-notes');
      if(ta){
        ta.value = (S.notesLocal !== null ? S.notesLocal
                                          : ((S.reunion && S.reunion.notes) || ''));
        ta.focus();
      }
    }
    var btn = rac.querySelector('#reu-veille-btn');
    if(btn){
      btn.innerHTML = libelleVeille(S.veilleOuverte);
      btn.setAttribute('aria-pressed', S.veilleOuverte ? 'true' : 'false');
      btn.classList.toggle('actif', !!S.veilleOuverte);
    }
  }

  async function basculerVeille(rac){
    S.veilleOuverte = !S.veilleOuverte;
    peindreNotes(rac);
    if(!S.veilleOuverte || S.veilleChargee) return;
    try{ await chargerVeille(); }
    catch(e){ S.veilleChargee = true; S.veille = null; toast(e.message, 'danger'); }
    peindreNotes(rac);
  }

  /* Participants : les presents en pastilles, et une recherche pour en ajouter.
     L'annuaire est deja en memoire (charge avec le contexte) — la recherche ne
     part donc pas au serveur a chaque touche. Un nom absent de l'annuaire reste
     acceptable : un point de production reunit parfois quelqu'un qui n'a pas de
     compte. */
  function rendreParticipants(presents, personnes, recherche){
    presents = presents || [];
    personnes = personnes || [];
    var q = String(recherche == null ? '' : recherche);
    var deja = {};
    presents.forEach(function(p){ deja[pli(p.nom)] = true; });

    var pastilles = presents.length
      ? presents.map(function(p){
          return '<span class="reu-part">' + esc(p.nom)
               + '<button type="button" class="reu-part-x" '
               + 'data-part-sup="' + escA(p.nom) + '" '
               + 'title="Retirer" aria-label="Retirer ' + escA(p.nom) + '">×</button></span>';
        }).join('')
      : '<div class="reu-sauve">Personne pour l\'instant.</div>';

    var qp = pli(q);
    // On cherche partout dans le nom — « lesaf » doit trouver « Lesaffre »
    // meme si c'est le nom de famille. Mais un nom qui COMMENCE par la frappe
    // passe devant : taper « ma » doit proposer Manuel et Marc avant
    // Desreumaux, ou le « ma » est au milieu.
    var trouves = [];
    if(qp){
      var debut = [], milieu = [];
      personnes.forEach(function(pe){
        var n = pli(pe.nom);
        if(deja[n] || n.indexOf(qp) === -1) return;
        var mots = n.split(/[\s-]+/);
        var enTete = mots.some(function(m){ return m.indexOf(qp) === 0; });
        (enTete ? debut : milieu).push(pe);
      });
      trouves = debut.concat(milieu).slice(0, 8);
    }
    // Le nom libre n'est propose que si l'annuaire ne repond rien : tant qu'il
    // reste des noms a choisir, offrir « ajouter tel quel » n'ajoute que du
    // bruit sous la liste.
    var libre = qp && !trouves.length && !deja[qp];

    var suggestions = '';
    if(qp){
      suggestions = trouves.map(function(pe){
        return '<button type="button" class="reu-sugg" data-part-add="' + escA(pe.nom) + '">'
             + esc(pe.nom) + '</button>';
      }).join('');
      if(libre){
        suggestions += '<button type="button" class="reu-sugg hors" data-part-add="' + escA(q.trim()) + '">'
                     + 'Ajouter &laquo; ' + esc(q.trim()) + ' &raquo;'
                     + '<em>hors annuaire</em></button>';
      }
      if(!suggestions){
        suggestions = '<div class="reu-sauve">D&eacute;j&agrave; dans la r&eacute;union.</div>';
      }
    }

    return '<div class="reu-parts">' + pastilles + '</div>'
      + '<div class="reu-cherche">'
      +   '<input type="search" id="reu-p-q" autocomplete="off" '
      +     'placeholder="Chercher un nom&hellip;" aria-label="Chercher un participant" '
      +     'value="' + escA(q) + '">'
      +   '<div class="reu-suggs">' + suggestions + '</div>'
      + '</div>';
  }

  /* Le perimetre d'une reunion : une machine, plusieurs, ou tout l'atelier.
     « Toutes » n'est pas une machine de plus dans la liste — c'est l'absence de
     choix, et cocher tout revient au meme. On l'affiche donc comme l'etat par
     defaut, actif tant que rien n'est coche. */
  function rendreMachines(disponibles, retenues, horsProd){
    disponibles = disponibles || [];
    retenues = retenues || [];
    var prises = {}, hors = {};
    retenues.forEach(function(m){ prises[pli(m)] = true; });
    (horsProd || []).forEach(function(m){ hors[pli(m)] = true; });
    var toutes = !retenues.length;
    return '<div class="reu-mach">'
      + '<button type="button" class="reu-mach-p' + (toutes ? ' actif' : '') + '" '
      + 'data-mach-tout="1" aria-pressed="' + (toutes ? 'true' : 'false') + '" '
      + 'title="Toutes les machines de production">Toutes</button>'
      + disponibles.map(function(m){
          var actif = !!prises[pli(m)];
          // Un poste hors production n'entre pas dans « Toutes » : sa pastille
          // reste la, en retrait, et un clic le ramene.
          var dehors = !!hors[pli(m)];
          return '<button type="button" class="reu-mach-p'
               + (actif ? ' actif' : '') + (dehors ? ' hors' : '') + '" '
               + 'data-mach="' + escA(m) + '" '
               + (dehors ? 'title="Poste hors production : non compt&eacute; par d&eacute;faut" ' : '')
               + 'aria-pressed="' + (actif ? 'true' : 'false') + '">' + esc(m)
               + (dehors ? '<em>hors prod</em>' : '') + '</button>';
        }).join('')
      + '</div>';
  }

  function rendreActions(l){
    l = l || [];
    if(!l.length) return '<div class="reu-sauve">Aucune action pour l\'instant.</div>';
    return l.map(function(a){
      var meta = (a.responsable || a.echeance)
        ? '<div class="reu-a-meta">' + esc(a.responsable || '')
          + (a.echeance ? (a.responsable ? ' · ' : '') + 'pour le ' + esc(dateFr(a.echeance)) : '')
          + '</div>'
        : '';
      return '<div class="reu-act' + (statutDe(a) === 'termine' ? ' fait' : '') + '">'
        + '<div class="reu-a-txt">' + esc(a.texte) + meta + '</div>'
        + selectStatut(a)
        + '<button type="button" class="reu-a-sup" data-sup="' + escA(a.id) + '" '
        + 'title="Supprimer">×</button></div>';
    }).join('');
  }

  /* Plein ecran -------------------------------------------------
     Un point de production se tient a plusieurs devant un ecran : la barre
     laterale, le titre de page et les sous-onglets ne servent a personne
     pendant la reunion. On ne change pas de page pour autant — la classe est
     posee sur <body> et la feuille de style masque la coquille, donc l'etat de
     MyProd, la reunion ouverte et la frappe en cours sont intacts au retour. */

  function appliquerPlein(){
    try{
      var actif = !!(S.plein && S.vue === 'reunion');
      document.body.classList.toggle('reu-plein', actif);
    }catch(e){}
  }

  function basculerPlein(valeur){
    S.plein = (valeur === undefined) ? !S.plein : !!valeur;
    appliquerPlein();
    peindre();
    if(S.plein){ try{ window.scrollTo(0, 0); }catch(e){} }
  }

  // Echap rend la coquille : c'est le geste attendu d'un plein ecran, et il
  // faut pouvoir sortir meme si le bouton est passe sous le pli. Pose une
  // seule fois, sur le document — la racine du module est repeinte en boucle.
  var echapPose = false;
  function poserEchap(){
    if(echapPose) return;
    echapPose = true;
    document.addEventListener('keydown', function(ev){
      if(ev.key !== 'Escape' || !S.plein) return;
      // La recherche de participants a deja son Echap : vider le champ passe
      // avant de quitter l'ecran.
      if(ev.target && ev.target.id === 'reu-p-q') return;
      basculerPlein(false);
    });
  }

  /* Peinture ---------------------------------------------------- */

  function peindre(){
    var rac = racineCourante;
    if(!rac || !rac.isConnected) return;
    // La page hôte (MyProd) met la réunion ouverte et le filtre du suivi dans
    // son adresse (url-etat.md).
    try{ if(opts.surChange) opts.surChange(etatAdresse()); }catch(e){}
    var boiteErr = rac.querySelector('#reu-erreur');
    if(boiteErr){
      boiteErr.innerHTML = S.erreur
        ? '<div class="card" style="padding:14px 16px;margin-bottom:14px;'
          + 'border-color:var(--warn);color:var(--text2);font-size:13px">' + esc(S.erreur) + '</div>'
        : '';
    }
    var btnListe = rac.querySelector('[data-r="liste"]');
    if(btnListe) btnListe.style.display = S.vue === 'reunion' ? '' : 'none';
    var etat = rac.querySelector('#reu-etat');
    if(etat){
      etat.innerHTML = (S.vue === 'reunion' && S.reunion)
        ? (S.reunion.ouverte
            ? '<span class="reu-pastille ouverte">r&eacute;union en cours</span>'
            : '<span class="reu-pastille close">close</span>')
        : '';
    }
    // Filet : le plein ecran masque la coquille de MyProd. Il ne doit exister
    // que tant qu'une reunion est a l'ecran — sinon la barre laterale
    // resterait cachee sur une page qui n'a rien demande.
    if(S.vue !== 'reunion' && S.plein){ S.plein = false; }
    appliquerPlein();
    var vue = rac.querySelector('#reu-vue');
    if(!vue) return;
    if(S.vue === 'reunion'){
      vue.innerHTML = rendreReunion(S.reunion, S.prod, {
        notes: S.notesEtat, personnes: S.personnes, recherche: S.rechercheP,
        plein: S.plein, veilleOuverte: S.veilleOuverte,
        horsProd: (S.prod && S.prod.machines_hors_production) || []
      });
      var ta = vue.querySelector('#reu-notes');
      if(ta) ta.value = (S.notesLocal !== null ? S.notesLocal
                                               : ((S.reunion && S.reunion.notes) || ''));
      peindreProd(vue);
    }else{
      var hist = vue.querySelector('details.reu-hist');
      vue.innerHTML = rendreAccueil(S.reunions, S.suivi, {
        filtreResp: S.filtreResp, toutTermine: S.toutTermine,
        voirTermine: S.voirTermine, recherche: S.rechercheA,
        histOuvert: hist ? hist.open : false
      });
    }
  }

  function peindreProd(vue){
    var box = vue.querySelector('#reu-prod');
    var R = rp();
    if(!box) return;
    if(!R){ box.innerHTML = '<div class="reu-vide">Module de rendu non charg&eacute; '
                          + '(mysifa_retour_prod.js).</div>'; return; }
    if(!S.prod){ box.innerHTML = '<div class="reu-vide">Aucune donn&eacute;e.</div>'; return; }
    box.innerHTML = R.renderFeuille(S.prod.atelier, S.prod.frise)
      + '<div class="rp-bloc"><div class="rp-titre">Dossiers de la p&eacute;riode</div>'
      + R.renderListe(S.prod.comptes_rendus || []) + '</div>';
    R.brancherFrise(box, {onClic: function(){}});
    R.brancher(null, {racine: box, toast: toast, onSaved: function(){ recharger(); }});
  }

  /* Perimetre : cocher une machine change les chiffres, donc on relit la
     reunion entiere. Decocher la derniere revient a « toutes » — sans ca on
     resterait sur un perimetre vide, qui ne montre rien. */
  async function basculerMachine(nom){
    if(!S.reunion) return;
    var actuelles = (S.reunion.machines || []).slice();
    var idx = -1;
    actuelles.forEach(function(m, i){ if(pli(m) === pli(nom)) idx = i; });
    if(idx >= 0) actuelles.splice(idx, 1);
    else actuelles.push(nom);
    await majMachines(actuelles);
  }

  async function majMachines(noms){
    if(!S.reunion) return;
    try{
      await enregistrer({machines: noms}, true);
      await recharger();
    }catch(e){ toast(e.message, 'danger'); }
  }

  /* Le bloc se repeint seul : la colonne entiere se reconstruirait sinon, et
     le champ de recherche perdrait le curseur a chaque lettre. */
  function peindreParticipants(rac, garderFocus){
    var box = rac.querySelector('#reu-participants');
    if(!box) return;
    var champ = box.querySelector('#reu-p-q');
    var pos = champ ? champ.selectionStart : null;
    box.innerHTML = rendreParticipants(
      S.reunion && S.reunion.participants, S.personnes, S.rechercheP);
    if(garderFocus){
      var neuf = box.querySelector('#reu-p-q');
      if(neuf){
        neuf.focus();
        try{ if(pos !== null) neuf.setSelectionRange(pos, pos); }catch(e){}
      }
    }
  }

  /* Ajouter ou retirer : le serveur remplace la liste entiere, on lui envoie
     donc celle d'apres. Les chiffres de production ne dependent pas des
     presents — inutile de recharger la reunion complete. */
  async function majParticipants(rac, ajout, retrait){
    if(!S.reunion) return;
    var noms = ((S.reunion.participants || []).map(function(p){ return p.nom; }));
    if(retrait !== null && retrait !== undefined){
      noms = noms.filter(function(n){ return pli(n) !== pli(retrait); });
    }
    if(ajout){
      var nom = String(ajout).trim();
      if(nom && !noms.some(function(n){ return pli(n) === pli(nom); })) noms.push(nom);
    }
    try{
      S.reunion = await poster('/api/reunions/' + encodeURIComponent(S.reunion.id),
                               {participants: noms});
      S.rechercheP = '';
      peindreParticipants(rac, !!ajout);
      try{ await chargerListe(); }catch(e){}
    }catch(e){ toast(e.message, 'danger'); }
  }

  /* Enregistrement ---------------------------------------------- */

  async function enregistrer(corps, silencieux){
    if(!S.reunion) return;
    try{
      S.reunion = await poster('/api/reunions/' + encodeURIComponent(S.reunion.id), corps);
      if(!silencieux) toast('Enregistre.', 'info');
    }catch(e){ toast(e.message, 'danger'); }
  }

  async function recharger(){
    if(!S.reunion) return;
    try{
      await chargerReunion(S.reunion.id);
      peindre();
    }catch(e){ toast(e.message, 'danger'); }
  }

  async function deplacer(id, statut){
    var a = (S.suivi || []).filter(function(x){ return String(x.id) === String(id); })[0];
    if(!a || statutDe(a) === statut) return;
    var avant = {statut: a.statut, fait: a.fait, fait_le: a.fait_le};
    a.statut = statut; a.fait = statut === 'termine';
    if(a.fait) a.fait_le = new Date().toISOString();
    peindre();
    try{
      await poster('/api/reunions/actions/' + encodeURIComponent(id), {statut: statut});
      await chargerSuivi();
    }catch(e){
      Object.assign(a, avant);
      toast(e.message, 'danger');
    }
    peindre();
  }

  async function majAction(id, corps){
    try{
      await poster('/api/reunions/actions/' + encodeURIComponent(id), corps);
      if(S.vue === 'reunion'){ await recharger(); }
      else{ await chargerSuivi(); peindre(); }
    }catch(e){ toast(e.message, 'danger'); }
  }

  /* Impression --------------------------------------------------
     Un onglet s'imprime avec toute l'application autour : on construit donc un
     document a part, hors de la coquille, et la feuille de style masque le
     reste. Les notes sortent en texte -- un <textarea> imprime se coupe a sa
     hauteur visible. */

  function boiteImpression(){
    var d = document.getElementById('reu-doc');
    if(!d){
      d = document.createElement('div');
      d.id = 'reu-doc';
      document.body.appendChild(d);
    }
    return d;
  }

  function rendreDocument(r, prod, notes){
    if(!r) return '';
    var periode = r.date_debut === r.date_fin
      ? dateFr(r.date_debut)
      : dateFr(r.date_debut) + ' → ' + dateFr(r.date_fin);
    var noms = (r.participants || []).map(function(p){ return p.nom; });
    var actions = (r.actions || []).map(function(a){
      var meta = (a.responsable || a.echeance)
        ? '<span class="reu-doc-act-meta">' + esc(a.responsable || '')
          + (a.echeance ? (a.responsable ? ' · ' : '') + 'pour le ' + esc(dateFr(a.echeance)) : '')
          + '</span>'
        : '';
      var st = STATUTS.filter(function(s){ return s.code === statutDe(a); })[0];
      return '<div class="reu-doc-act' + (a.fait ? ' fait' : '') + '">'
           + '<span class="reu-doc-act-st">' + esc(st ? st.libelle : '') + '</span> '
           + esc(a.texte) + meta + '</div>';
    }).join('');
    var chiffres = '';
    var R = rp();
    if(R && prod){
      chiffres = R.renderFeuille(prod.atelier, prod.frise)
           + '<div class="rp-bloc"><div class="rp-titre">Dossiers de la p&eacute;riode</div>'
           + R.renderListe(prod.comptes_rendus || []) + '</div>';
    }
    return ''
      + '<div class="reu-doc-hdr">'
      +   '<div class="reu-doc-marque">MySifa &mdash; Point de production</div>'
      +   '<h2>' + esc(r.titre || '') + '</h2>'
      +   '<div class="reu-doc-meta">'
      +     '<div><b>P&eacute;riode analys&eacute;e</b> : ' + esc(periode)
      +       ' · ' + esc((r.machines && r.machines.length)
                          ? r.machines.join(' · ')
                          : (r.machine || 'toutes les machines')) + '</div>'
      +     '<div><b>Participants</b> : ' + esc(noms.join(', ') || 'non renseignés') + '</div>'
      +     '<div><b>Ouverte par</b> ' + esc(r.ouverte_par || '—')
      +       ' le ' + esc(dateFr(r.ouverte_le))
      +       (r.statut === 'close'
                ? ' · <b>close</b> le ' + esc(dateFr(r.close_le))
                : ' · <b>en cours</b>') + '</div>'
      +   '</div>'
      + '</div>'
      + '<div class="reu-doc-bloc"><h3>Notes</h3>'
      +   '<div class="reu-doc-notes">' + esc(notes || '') + '</div></div>'
      + (actions
          ? '<div class="reu-doc-bloc"><h3>Actions</h3>' + actions + '</div>'
          : '')
      + (chiffres ? '<div class="reu-doc-bloc">' + chiffres + '</div>' : '');
  }

  function peindreImpression(){
    if(!S.reunion) return;
    var notes = S.notesLocal !== null ? S.notesLocal : (S.reunion.notes || '');
    boiteImpression().innerHTML = rendreDocument(S.reunion, S.prod, notes);
  }

  /* Le navigateur nomme le PDF d'apres <title> : sans ca le fichier s'appelle
     « MyProd - MySifa » pour toutes les reunions. */
  function nomDocument(){
    var r = S.reunion || {};
    var j = String(r.date_debut || '').split('-');
    var d = j.length === 3 ? j[2] + '-' + j[1] + '-' + j[0] : '';
    return 'MySifa - Point de production ' + (d || r.titre || '');
  }

  function imprimer(){
    peindreImpression();
    var avant = document.title;
    document.title = nomDocument();
    document.body.classList.add('reu-impression');
    var fin = function(){
      document.body.classList.remove('reu-impression');
      document.title = avant;
      window.removeEventListener('afterprint', fin);
    };
    window.addEventListener('afterprint', fin);
    setTimeout(function(){ window.print(); setTimeout(fin, 1500); }, 60);
  }

  /* Branchements ------------------------------------------------
     Delegation : le contenu est repeint en innerHTML a chaque passe, un
     binding pose sur un noeud ne survivrait pas. */

  function brancher(rac){
    rac.addEventListener('click', async function(ev){
      var corb = ev.target.closest ? ev.target.closest('[data-suppr-reunion]') : null;
      if(corb && rac.contains(corb)){
        ev.stopPropagation();
        demanderSuppression(rac, corb.getAttribute('data-suppr-reunion'),
                                 corb.getAttribute('data-suppr-titre'));
        return;
      }
      var el = ev.target.closest
        ? ev.target.closest('[data-r],[data-sup],[data-part-add],[data-part-sup],'
                            + '[data-mach],[data-mach-tout],[data-resp],[data-ouvrir],'
                            + '[data-editer]') : null;
      if(el && rac.contains(el)){
        var act = el.getAttribute('data-r');
        if(act === 'liste'){
          S.vue = 'liste'; S.reunion = null; S.prod = null; S.notesLocal = null;
          S.plein = false; appliquerPlein();
          peindre();
          try{ await Promise.all([chargerListe(), chargerSuivi()]); }
          catch(e){ S.erreur = e.message; }
          peindre();
          return;
        }
        if(act === 'nouvelle'){ ouvrirAction(rac, null); return; }
        if(act === 'enreg-action'){ await enregistrerAction(rac); return; }
        if(act === 'suppr-action'){ await supprimerAction(rac); return; }
        if(act === 'tout-termine'){ S.toutTermine = true; peindre(); return; }
        if(act === 'voir-termine'){
          S.voirTermine = !S.voirTermine;
          ecrirePref('reu.voirTermine', S.voirTermine ? '1' : '0');
          peindre(); return;
        }
        if(el.hasAttribute('data-resp')){
          S.filtreResp = el.getAttribute('data-resp') || ''; peindre(); return;
        }
        if(el.hasAttribute('data-editer')){ ouvrirAction(rac, el.getAttribute('data-editer')); return; }
        if(el.hasAttribute('data-ouvrir')){ await ouvrir(el.getAttribute('data-ouvrir')); return; }
        if(act === 'moment'){ choisirMoment(rac, el.getAttribute('data-moment')); return; }
        if(act === 'annuler'){ fermerModale(rac); return; }
        if(act === 'creer'){ await creer(rac); return; }
        if(act === 'plein'){ basculerPlein(); return; }
        if(act === 'imprimer'){ imprimer(); return; }
        if(act === 'clore'){ await clore(); return; }
        if(act === 'ajout-action'){ await ajouterAction(rac); return; }
        if(act === 'veille'){ await basculerVeille(rac); return; }
        if(act === 'suppr-non'){ fermerSuppression(rac); return; }
        if(el.getAttribute('data-mach-tout') !== null){
          await majMachines([]);
          return;
        }
        var mach = el.getAttribute('data-mach');
        if(mach !== null){ await basculerMachine(mach); return; }
        var ajout = el.getAttribute('data-part-add');
        if(ajout !== null){ await majParticipants(rac, ajout, null); return; }
        var retrait = el.getAttribute('data-part-sup');
        if(retrait !== null){ await majParticipants(rac, null, retrait); return; }
        if(act === 'suppr-oui'){ await confirmerSuppression(rac); return; }
        var sup = el.getAttribute('data-sup');
        if(sup){ await majAction(sup, {texte: ''}); return; }
      }
      var tr = ev.target.closest ? ev.target.closest('tr[data-id]') : null;
      if(tr && rac.contains(tr)){ await ouvrir(tr.getAttribute('data-id')); }
    });

    rac.addEventListener('change', async function(ev){
      var t = ev.target;
      if(t.id === 'reu-titre'){ await enregistrer({titre: t.value}); peindre(); return; }
      if(t.id === 'reu-du'){ await enregistrer({date_debut: t.value}, true); await recharger(); return; }
      if(t.id === 'reu-au'){ await enregistrer({date_fin: t.value}, true); await recharger(); return; }
      if(t.hasAttribute && t.hasAttribute('data-statut')){
        await majAction(t.getAttribute('data-statut'), {statut: t.value});
      }
    });

    rac.addEventListener('input', function(ev){
      if(ev.target.id === 'reu-p-q'){
        S.rechercheP = ev.target.value;
        peindreParticipants(rac, true);
        return;
      }
      if(ev.target.id === 'reu-suivi-q'){
        S.rechercheA = ev.target.value;
        var zone = rac.querySelector('#reu-board-zone');
        if(zone && S.suivi) zone.innerHTML = rendreBoard(S.suivi, {
          filtreResp: S.filtreResp, toutTermine: S.toutTermine,
          voirTermine: S.voirTermine, recherche: S.rechercheA
        });
        return;
      }
      if(ev.target.id !== 'reu-notes') return;
      S.notesLocal = ev.target.value;
      S.notesEtat = 'Modifications non enregistrees…';
      var etat = rac.querySelector('#reu-notes-etat');
      if(etat) etat.textContent = S.notesEtat;
      clearTimeout(notesTimer);
      notesTimer = setTimeout(async function(){
        var valeur = S.notesLocal;
        await enregistrer({notes: valeur}, true);
        // La frappe a pu continuer pendant l'aller-retour : on ne declare
        // enregistre que ce qui l'est vraiment.
        if(S.notesLocal === valeur) S.notesLocal = null;
        S.notesEtat = 'Enregistre a ' + new Date().toLocaleTimeString('fr-FR').slice(0, 5);
        var e2 = rac.querySelector('#reu-notes-etat');
        if(e2) e2.textContent = S.notesEtat;
      }, 900);
    });

    /* Glisser-deposer du kanban. Delegue sur la racine, comme le reste : le
       tableau est repeint a chaque changement. */
    var glisse = null;
    rac.addEventListener('dragstart', function(ev){
      var c = ev.target.closest ? ev.target.closest('[data-carte]') : null;
      if(!c) return;
      glisse = c.getAttribute('data-carte');
      try{ ev.dataTransfer.setData('text/plain', glisse); ev.dataTransfer.effectAllowed = 'move'; }catch(e){}
      setTimeout(function(){ c.classList.add('glisse'); }, 0);
    });
    rac.addEventListener('dragend', function(){
      glisse = null;
      rac.querySelectorAll('.glisse,.survol').forEach(function(n){
        n.classList.remove('glisse'); n.classList.remove('survol');
      });
    });
    rac.addEventListener('dragover', function(ev){
      if(!glisse) return;
      var col = ev.target.closest ? ev.target.closest('[data-col]') : null;
      if(!col) return;
      ev.preventDefault();
      try{ ev.dataTransfer.dropEffect = 'move'; }catch(e){}
      rac.querySelectorAll('.reu-col.survol').forEach(function(n){
        if(n !== col) n.classList.remove('survol');
      });
      col.classList.add('survol');
    });
    rac.addEventListener('drop', async function(ev){
      var col = ev.target.closest ? ev.target.closest('[data-col]') : null;
      if(!col || !glisse) return;
      ev.preventDefault();
      var id = glisse;
      glisse = null;
      await deplacer(id, col.getAttribute('data-col'));
    });

    rac.addEventListener('keydown', async function(ev){
      // Entree valide la premiere suggestion : on tape trois lettres, on entre.
      if(ev.target.id === 'reu-p-q' && ev.key === 'Enter'){
        ev.preventDefault();
        var premiere = rac.querySelector('[data-part-add]');
        if(premiere) await majParticipants(rac, premiere.getAttribute('data-part-add'), null);
        return;
      }
      if(ev.target.id === 'reu-p-q' && ev.key === 'Escape'){
        S.rechercheP = '';
        peindreParticipants(rac, true);
        return;
      }
      if(ev.target.hasAttribute && ev.target.hasAttribute('data-editer')
         && (ev.key === 'Enter' || ev.key === ' ')){
        ev.preventDefault();
        ouvrirAction(rac, ev.target.getAttribute('data-editer'));
        return;
      }
      if(ev.target.id === 'reu-n-texte' && ev.key === 'Enter'){
        ev.preventDefault();
        await enregistrerAction(rac);
        return;
      }
      if(ev.target.id === 'reu-a-txt' && ev.key === 'Enter'){
        ev.preventDefault();
        var b = rac.querySelector('[data-r="ajout-action"]');
        if(b) b.click();
      }
    });

    var mov = rac.querySelector('#reu-mov');
    if(mov) mov.addEventListener('click', function(ev){
      if(ev.target === mov) fermerModale(rac);
    });
    var movSup = rac.querySelector('#reu-mov-sup');
    if(movSup) movSup.addEventListener('click', function(ev){
      if(ev.target === movSup) fermerSuppression(rac);
    });
  }

  /* Suppression -------------------------------------------------
     Une reunion emporte ses notes et ses actions : la confirmation nomme ce
     qu'on efface, et la fenetre reste dans la page (pas de confirm() natif,
     qui n'a ni le theme ni la langue du reste). */

  function demanderSuppression(rac, id, titre){
    S.aSupprimer = {id: id, titre: titre || ''};
    var quoi = rac.querySelector('#reu-sup-quoi');
    if(quoi){
      quoi.innerHTML = '<b>' + esc(S.aSupprimer.titre || 'Sans titre') + '</b><br>'
        + 'Ses notes et ses actions sont supprim&eacute;es avec elle. '
        + 'Les remont&eacute;es de production ne sont pas touch&eacute;es.';
    }
    var movSup = rac.querySelector('#reu-mov-sup');
    if(movSup) movSup.classList.add('open');
  }

  function fermerSuppression(rac){
    S.aSupprimer = null;
    var movSup = rac.querySelector('#reu-mov-sup');
    if(movSup) movSup.classList.remove('open');
  }

  async function confirmerSuppression(rac){
    var cible = S.aSupprimer;
    if(!cible) return;
    try{
      await supprimerA('/api/reunions/' + encodeURIComponent(cible.id));
      fermerSuppression(rac);
      // La reunion ouverte peut etre celle qu'on vient d'effacer : on ne la
      // laisse pas a l'ecran avec un identifiant qui n'existe plus.
      if(S.reunion && String(S.reunion.id) === String(cible.id)){
        S.reunion = null; S.prod = null; S.notesLocal = null; S.vue = 'liste';
      }
      if(String(S.ouverteId) === String(cible.id)) S.ouverteId = null;
      await chargerListe();
      peindre();
      toast('Reunion supprimee.', 'info');
    }catch(e){
      fermerSuppression(rac);
      toast(e.message, 'danger');
    }
  }

  async function ouvrir(id){
    try{
      S.vue = 'reunion';
      await chargerReunion(id);
      peindre();
    }catch(e){
      toast(e.message, 'danger');
      S.vue = 'liste';
      peindre();
    }
  }

  /* Moment de la reunion : matin ou apres-midi, repris dans le titre. On se
     reunit deux fois par jour sur la meme date : sans le moment, les deux
     points portent le meme nom dans la liste. */
  var MOMENTS = {'matin': 'Matin', 'apres-midi': 'Apr\u00e8s-midi'};
  var SEP_MOMENT = ' \u00b7 ';
  function momentParDefaut(){
    return (new Date().getHours() < 13) ? 'matin' : 'apres-midi';
  }
  function jourLocalIso(d){
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0')
         + '-' + String(d.getDate()).padStart(2, '0');
  }
  // Retire un suffixe de moment deja pose, pour ne jamais en empiler deux.
  function titreSansMoment(titre){
    var s = String(titre || '');
    Object.keys(MOMENTS).forEach(function(k){
      var suf = SEP_MOMENT + MOMENTS[k];
      if(s.slice(-suf.length) === suf) s = s.slice(0, -suf.length);
    });
    return s;
  }
  function choisirMoment(rac, moment){
    if(!MOMENTS[moment]) return;
    rac.querySelectorAll('.reu-moment-btn').forEach(function(b){
      var on = b.getAttribute('data-moment') === moment;
      b.classList.toggle('on', on);
      b.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    var t = rac.querySelector('#reu-n-titre');
    if(t){
      var base = titreSansMoment(t.value).trim() || S.titrePropose || '';
      t.value = base + SEP_MOMENT + MOMENTS[moment];
    }
  }

  function ouvrirModale(rac){
    var t = rac.querySelector('#reu-n-titre');
    var du = rac.querySelector('#reu-n-du');
    var au = rac.querySelector('#reu-n-au');
    if(t) t.value = S.titrePropose || '';
    // Periode par defaut : de la veille (le dernier jour saisi, qui saute le
    // week-end un lundi) jusqu'a aujourd'hui, pour voir aussi la nuit et le
    // debut de poste en cours.
    if(du) du.value = S.jourPropose || '';
    if(au) au.value = jourLocalIso(new Date());
    choisirMoment(rac, momentParDefaut());
    // Les participants s'ajoutent pendant la reunion, pas avant : au moment de
    // lancer, on ne sait pas encore qui sera la.
    var mov = rac.querySelector('#reu-mov');
    if(mov) mov.classList.add('open');
  }
  function fermerModale(rac){
    var mov = rac.querySelector('#reu-mov');
    if(mov) mov.classList.remove('open');
  }

  async function creer(rac){
    try{
      var r = await poster('/api/reunions', {
        titre: (rac.querySelector('#reu-n-titre') || {}).value || '',
        date_debut: (rac.querySelector('#reu-n-du') || {}).value || '',
        date_fin: (rac.querySelector('#reu-n-au') || {}).value || ''
      });
      fermerModale(rac);
      await ouvrir(r.id);
      try{ await chargerListe(); }catch(e){}
    }catch(e){ toast(e.message, 'danger'); }
  }

  async function clore(){
    if(!S.reunion) return;
    try{
      var r = await poster('/api/reunions/' + encodeURIComponent(S.reunion.id) + '/clore',
                           {rouvrir: !S.reunion.ouverte});
      S.reunion = r;
      S.ouverteId = r.ouverte ? r.id : null;
      peindre();
      toast(r.ouverte ? 'Reunion rouverte.' : 'Reunion close.', 'info');
      try{ await chargerListe(); }catch(e){}
    }catch(e){ toast(e.message, 'danger'); }
  }

  async function ajouterAction(rac){
    if(!S.reunion) return;
    var champ = rac.querySelector('#reu-a-txt');
    var texte = ((champ || {}).value || '').trim();
    if(!texte){ toast('Action vide.', 'danger'); return; }
    try{
      await poster('/api/reunions/' + encodeURIComponent(S.reunion.id) + '/actions', {
        texte: texte,
        responsable: (rac.querySelector('#reu-a-qui') || {}).value || '',
        echeance: (rac.querySelector('#reu-a-quand') || {}).value || ''
      });
      await recharger();
    }catch(e){ toast(e.message, 'danger'); }
  }

  /* Action : creation et correction ----------------------------
     Meme modale pour les deux. Le responsable se choisit dans l'annuaire ;
     un nom qui n'y est plus (compte desactive) reste propose pour ne pas
     etre efface a la premiere correction. */

  function ouvrirAction(rac, id){
    var a = id ? (S.suivi || []).filter(function(x){ return String(x.id) === String(id); })[0] : null;
    if(id && !a) return;
    S.actionEditee = a ? a.id : null;
    var qui = String((a && a.responsable) || '').trim();
    var noms = (S.personnes || []).map(function(p){ return String(p.nom || '').trim(); })
                                  .filter(Boolean);
    if(qui && noms.indexOf(qui) === -1) noms.push(qui);
    var sel = rac.querySelector('#reu-n-qui');
    if(sel){
      sel.innerHTML = '<option value="">Non attribuée</option>'
        + noms.map(function(n){
            return '<option value="' + escA(n) + '"' + (n === qui ? ' selected' : '') + '>'
                 + esc(n) + '</option>';
          }).join('');
    }
    var t = rac.querySelector('#reu-n-texte');
    if(t) t.value = a ? (a.texte || '') : '';
    var q = rac.querySelector('#reu-n-quand');
    if(q) q.value = a && a.echeance ? String(a.echeance).slice(0, 10) : '';
    var h = rac.querySelector('#reu-n-h');
    if(h) h.textContent = a ? 'Modifier l\'action' : 'Nouvelle action';
    var sup = rac.querySelector('#reu-n-sup');
    if(sup) sup.style.display = a ? '' : 'none';
    var mov = rac.querySelector('#reu-mov');
    if(mov) mov.classList.add('open');
    if(t) setTimeout(function(){ try{ t.focus(); }catch(e){} }, 0);
  }

  async function enregistrerAction(rac){
    var texte = ((rac.querySelector('#reu-n-texte') || {}).value || '').trim();
    if(!texte){ toast('Action vide — décrivez ce qu\'il faut faire.', 'danger'); return; }
    var corps = {
      texte: texte,
      responsable: (rac.querySelector('#reu-n-qui') || {}).value || '',
      echeance: (rac.querySelector('#reu-n-quand') || {}).value || ''
    };
    var modif = !!S.actionEditee;
    try{
      if(modif){
        await poster('/api/reunions/actions/' + encodeURIComponent(S.actionEditee), corps);
      }else{
        await poster('/api/reunions/actions', corps);
      }
      fermerModale(rac);
      S.actionEditee = null;
      toast(modif ? 'Action modifiée.' : 'Action ajoutée.', 'info');
      await chargerSuivi();
      peindre();
    }catch(e){ toast(e.message, 'danger'); }
  }

  async function supprimerAction(rac){
    if(!S.actionEditee) return;
    var id = S.actionEditee;
    S.actionEditee = null;
    fermerModale(rac);
    await majAction(id, {texte: ''});
    toast('Action supprimée.', 'info');
  }

  /* Adresse de la page hôte ------------------------------------ */

  // Ce que l'adresse doit porter : la réunion ouverte, le filtre du suivi
  // ('' = tous, '~' = non attribuées, sinon un responsable).
  function etatAdresse(){
    return {
      reunion: (S.vue === 'reunion' && S.reunion) ? S.reunion.id : null,
      resp: S.filtreResp || ''
    };
  }
  // Une ancienne adresse peut encore nommer une reunion : l'ecran n'en
  // affiche plus, on retombe sur le suivi.
  async function appliquerAller(a){
    S.filtreResp = a.resp || '';
    S.vue = 'liste'; S.reunion = null; S.prod = null; S.notesLocal = null;
  }
  // Va à l'endroit décrit par l'adresse. Avant le premier chargement, la
  // demande attend la fin d'amorcer().
  async function aller(a){
    a = a || {};
    if(!S.contexteCharge || S.suivi === null){
      // Résolue par amorcer(), une fois l'endroit affiché.
      return new Promise(function(fin){ S.allerApres = a; S.allerFin = fin; });
    }
    if(S.vue !== 'reunion' && (S.filtreResp || '') === (a.resp || '')) return;
    await appliquerAller(a);
    peindre();
  }

  /* Montage ----------------------------------------------------- */

  function monter(racine, o){
    if(!racine) return;
    opts = o || {};
    racineCourante = racine;
    racine.innerHTML = squelette();
    brancher(racine);
    poserEchap();
    appliquerPlein();
    if(!S.contexteCharge || S.suivi === null){ amorcer(); }
    else{ peindre(); }
  }

  function reset(){
    S.plein = false; appliquerPlein();
    S.vue = 'liste'; S.reunion = null; S.prod = null;
    S.reunions = null; S.notesLocal = null; S.notesEtat = ''; S.erreur = null;
    S.veille = null; S.veilleOuverte = false; S.veilleChargee = false;
    S.personnes = []; S.rechercheP = '';
    S.contexteCharge = false;
    S.suivi = null; S.filtreResp = ''; S.toutTermine = false; S.rechercheA = '';
  }

  window.MySifaReunions = {
    monter: monter, reset: reset,
    aller: aller, etatAdresse: etatAdresse,
    rendreListe: rendreListe, rendreReunion: rendreReunion,
    rendreSuivi: rendreSuivi, rendreAccueil: rendreAccueil,
    rendreActions: rendreActions, rendreParticipants: rendreParticipants,
    rendreMachines: rendreMachines,
    rendreDocument: rendreDocument
  };
})();
