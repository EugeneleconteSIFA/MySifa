/* MySifa - Points de production : rendu et pilotage de l'onglet Reunions.
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
    plein: false,                      // reunion affichee seule, sans la coquille
    aSupprimer: null,                  // reunion dont la suppression est demandee
    erreur: null,
    contexteCharge: false
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

  async function chargerReunion(id){
    var d = await appel('/api/reunions/' + encodeURIComponent(id));
    S.reunion = d.reunion;
    S.prod = d.prod;
    S.notesLocal = null;
    S.notesEtat = '';
  }

  /* Premier montage : contexte + liste, et reprise de la reunion laissee
     ouverte -- une reunion non close n'est pas une erreur, c'est une reunion
     qu'on n'a pas fini de tenir. */
  async function amorcer(){
    try{
      S.erreur = null;
      await chargerContexte();
      await chargerListe();
      if(S.ouverteId && !S.reunion){
        await chargerReunion(S.ouverteId);
        S.vue = 'reunion';
      }
    }catch(e){
      S.erreur = e.message;
    }
    peindre();
  }

  /* Squelette --------------------------------------------------- */

  var ICONE_CORBEILLE =
      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<polyline points="3 6 5 6 21 6"/>'
    + '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
    + '<path d="M10 11v6"/><path d="M14 11v6"/>'
    + '<path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>';

  function squelette(){
    return ''
      + '<div class="reu-barre">'
      +   '<button type="button" class="reu-btn ghost" data-r="liste" style="display:none">'
      +     '&larr; Toutes les r&eacute;unions</button>'
      +   '<span id="reu-etat"></span>'
      +   '<div class="reu-sep"></div>'
      +   '<button type="button" class="reu-btn" data-r="lancer">+ Lancer une r&eacute;union</button>'
      + '</div>'
      + '<div id="reu-erreur"></div>'
      + '<div id="reu-vue"></div>'
      + '<div class="reu-modal-ov" id="reu-mov"><div class="reu-modal">'
      +   '<h3>Lancer une r&eacute;union</h3>'
      +   '<div class="reu-champ"><label for="reu-n-titre">Titre</label>'
      +     '<input id="reu-n-titre"></div>'
      +   '<div class="reu-champ"><label for="reu-n-du">P&eacute;riode analys&eacute;e &mdash; du</label>'
      +     '<input type="date" id="reu-n-du"></div>'
      +   '<div class="reu-champ"><label for="reu-n-au">au</label>'
      +     '<input type="date" id="reu-n-au"></div>'
      +   '<div class="reu-fin">'
      +     '<button type="button" class="reu-btn ghost" data-r="annuler">Annuler</button>'
      +     '<button type="button" class="reu-btn" data-r="creer">Lancer</button>'
      +   '</div>'
      + '</div></div>'
      + '<div class="reu-modal-ov" id="reu-mov-sup"><div class="reu-modal">'
      +   '<h3>Supprimer cette r&eacute;union ?</h3>'
      +   '<div class="reu-confirme" id="reu-sup-quoi"></div>'
      +   '<div class="reu-fin">'
      +     '<button type="button" class="reu-btn ghost" data-r="suppr-non">Annuler</button>'
      +     '<button type="button" class="reu-btn danger" data-r="suppr-oui">Supprimer</button>'
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
      +       '<h3>Notes</h3>'
      +       '<div class="reu-hint">Ce qui est abord&eacute; pendant le point.</div>'
      +       '<textarea class="reu-notes" id="reu-notes" '
      +         'placeholder="Ce qu\'on se dit, ce qu\'on constate&hellip;"></textarea>'
      +       '<div class="reu-sauve" id="reu-notes-etat">' + esc(etat.notes || '') + '</div>'
      +     '</div>'
      +     '<div class="reu-bloc">'
      +       '<h3>Actions</h3>'
      +       '<div class="reu-hint">Ce qui a &eacute;t&eacute; d&eacute;cid&eacute;, et par qui.</div>'
      +       '<div id="reu-actions">' + rendreActions(r.actions || []) + '</div>'
      +       '<div class="reu-actform">'
      +         '<input id="reu-a-txt" placeholder="Action &agrave; faire">'
      +         '<div class="reu-duo"><input id="reu-a-qui" placeholder="Qui">'
      +           '<input type="date" id="reu-a-quand" title="Pour quand"></div>'
      +         '<button type="button" class="reu-btn" data-r="ajout-action">Ajouter l\'action</button>'
      +       '</div>'
      +     '</div>'
      +   '</aside>'
      + '</div>';
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
      return '<div class="reu-act' + (a.fait ? ' fait' : '') + '">'
        + '<input type="checkbox" data-coche="' + escA(a.id) + '"' + (a.fait ? ' checked' : '') + '>'
        + '<div class="reu-a-txt">' + esc(a.texte) + meta + '</div>'
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
        plein: S.plein,
        horsProd: (S.prod && S.prod.machines_hors_production) || []
      });
      var ta = vue.querySelector('#reu-notes');
      if(ta) ta.value = (S.notesLocal !== null ? S.notesLocal
                                               : ((S.reunion && S.reunion.notes) || ''));
      peindreProd(vue);
    }else{
      vue.innerHTML = rendreListe(S.reunions);
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

  async function majAction(id, corps){
    try{
      await poster('/api/reunions/actions/' + encodeURIComponent(id), corps);
      await recharger();
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
      return '<div class="reu-doc-act' + (a.fait ? ' fait' : '') + '">'
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
                            + '[data-mach],[data-mach-tout]') : null;
      if(el && rac.contains(el)){
        var act = el.getAttribute('data-r');
        if(act === 'liste'){
          S.vue = 'liste'; S.reunion = null; S.prod = null; S.notesLocal = null;
          S.plein = false; appliquerPlein();
          peindre();
          try{ await chargerListe(); }catch(e){ S.erreur = e.message; }
          peindre();
          return;
        }
        if(act === 'lancer'){ ouvrirModale(rac); return; }
        if(act === 'annuler'){ fermerModale(rac); return; }
        if(act === 'creer'){ await creer(rac); return; }
        if(act === 'plein'){ basculerPlein(); return; }
        if(act === 'imprimer'){ imprimer(); return; }
        if(act === 'clore'){ await clore(); return; }
        if(act === 'ajout-action'){ await ajouterAction(rac); return; }
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
      if(t.hasAttribute && t.hasAttribute('data-coche')){
        await majAction(t.getAttribute('data-coche'), {fait: t.checked});
      }
    });

    rac.addEventListener('input', function(ev){
      if(ev.target.id === 'reu-p-q'){
        S.rechercheP = ev.target.value;
        peindreParticipants(rac, true);
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

  function ouvrirModale(rac){
    var t = rac.querySelector('#reu-n-titre');
    var du = rac.querySelector('#reu-n-du');
    var au = rac.querySelector('#reu-n-au');
    if(t) t.value = S.titrePropose || '';
    if(du) du.value = S.jourPropose || '';
    if(au) au.value = S.jourPropose || '';
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

  /* Montage ----------------------------------------------------- */

  function monter(racine, o){
    if(!racine) return;
    opts = o || {};
    racineCourante = racine;
    racine.innerHTML = squelette();
    brancher(racine);
    poserEchap();
    appliquerPlein();
    if(!S.contexteCharge || S.reunions === null){ amorcer(); }
    else{ peindre(); }
  }

  function reset(){
    S.plein = false; appliquerPlein();
    S.vue = 'liste'; S.reunion = null; S.prod = null;
    S.reunions = null; S.notesLocal = null; S.notesEtat = ''; S.erreur = null;
    S.personnes = []; S.rechercheP = '';
    S.contexteCharge = false;
  }

  window.MySifaReunions = {
    monter: monter, reset: reset,
    rendreListe: rendreListe, rendreReunion: rendreReunion,
    rendreActions: rendreActions, rendreParticipants: rendreParticipants,
    rendreMachines: rendreMachines,
    rendreDocument: rendreDocument
  };
})();
