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
    jourPropose: null,
    titrePropose: '',
    ouverteId: null,                   // reunion laissee ouverte au demarrage
    notesLocal: null,                  // frappe non encore enregistree
    notesEtat: '',
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
  function poster(path, corps){
    return appel(path, {method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(corps || {})});
  }

  /* Chargement -------------------------------------------------- */

  async function chargerContexte(){
    if(S.contexteCharge) return;
    var c = await appel('/api/reunions/contexte');
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
      + '</div></div>';
  }

  /* Rendu : liste -----------------------------------------------
     Fonctions pures : elles recoivent leurs donnees, ne lisent pas S et ne
     touchent pas au DOM. Exportees pour etre testables. */

  function rendreListe(l){
    if(l === null || l === undefined) return '<div class="reu-vide">Chargement&hellip;</div>';
    if(!l.length){
      return '<div class="reu-vide">Aucune r&eacute;union enregistr&eacute;e.<br>'
           + 'Lancez un point de production : la p&eacute;riode analys&eacute;e sera la '
           + 'derni&egrave;re journ&eacute;e travaill&eacute;e.</div>';
    }
    return '<table class="reu-tbl"><thead><tr><th>R&eacute;union</th>'
      + '<th>P&eacute;riode analys&eacute;e</th><th>Participants</th>'
      + '<th>Actions</th><th>&Eacute;tat</th></tr></thead><tbody>'
      + l.map(function(r){
          var periode = r.date_debut === r.date_fin
            ? dateFr(r.date_debut)
            : dateFr(r.date_debut) + ' → ' + dateFr(r.date_fin);
          var act = r.nb_actions
            ? (r.actions_restantes
                ? '<span class="reu-pastille ouverte">' + r.actions_restantes + ' &agrave; faire</span>'
                : '<span class="reu-pastille close">' + r.nb_actions + ' faites</span>')
            : '<span class="reu-pastille">&mdash;</span>';
          return '<tr data-id="' + escA(r.id) + '">'
            + '<td><div class="reu-nom-cell">' + esc(r.titre) + '</div>'
            + '<div class="reu-sous">' + esc(r.ouverte_par)
            + (r.a_des_notes ? ' · notes' : ' · sans notes') + '</div></td>'
            + '<td>' + esc(periode)
            + (r.machine ? '<div class="reu-sous">' + esc(r.machine) + '</div>' : '') + '</td>'
            + '<td>' + esc((r.participants || []).join(', ') || '—') + '</td>'
            + '<td>' + act + '</td>'
            + '<td>' + (r.ouverte
                ? '<span class="reu-pastille ouverte">en cours</span>'
                : '<span class="reu-pastille close">close</span>') + '</td></tr>';
        }).join('')
      + '</tbody></table>';
  }

  /* Rendu : reunion --------------------------------------------- */

  function rendreReunion(r, prod, notesEtat){
    if(!r) return '<div class="reu-vide">Chargement&hellip;</div>';
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
      +     '<div class="reu-champ"><label for="reu-machine">Machine</label>'
      +       '<select id="reu-machine"><option value="">Toutes les machines</option>'
      +       machines.map(function(m){
                return '<option value="' + escA(m) + '"'
                     + (m === r.machine ? ' selected' : '') + '>' + esc(m) + '</option>';
              }).join('')
      +       '</select></div>'
      +     '<button type="button" class="reu-btn ghost" data-r="imprimer">Imprimer</button>'
      +     '<button type="button" class="reu-btn" data-r="clore">'
      +       (r.ouverte ? 'Clore la r&eacute;union' : 'Rouvrir la r&eacute;union') + '</button>'
      +   '</div>'
      + '</div>'
      + '<div class="reu-split">'
      +   '<div id="reu-prod"><div class="reu-vide">Chargement des donn&eacute;es de production&hellip;</div></div>'
      +   '<aside class="reu-colonne">'
      +     '<h3>Notes</h3>'
      +     '<div class="reu-hint">Ce qui est abord&eacute; pendant le point.</div>'
      +     '<textarea class="reu-notes" id="reu-notes" '
      +       'placeholder="Ce qu\'on se dit, ce qu\'on constate&hellip;"></textarea>'
      +     '<div class="reu-sauve" id="reu-notes-etat">' + esc(notesEtat || '') + '</div>'
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
    var vue = rac.querySelector('#reu-vue');
    if(!vue) return;
    if(S.vue === 'reunion'){
      vue.innerHTML = rendreReunion(S.reunion, S.prod, S.notesEtat);
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
      +       (r.machine ? ' · ' + esc(r.machine) : ' · toutes les machines') + '</div>'
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
      var el = ev.target.closest ? ev.target.closest('[data-r],[data-sup]') : null;
      if(el && rac.contains(el)){
        var act = el.getAttribute('data-r');
        if(act === 'liste'){
          S.vue = 'liste'; S.reunion = null; S.prod = null; S.notesLocal = null;
          peindre();
          try{ await chargerListe(); }catch(e){ S.erreur = e.message; }
          peindre();
          return;
        }
        if(act === 'lancer'){ ouvrirModale(rac); return; }
        if(act === 'annuler'){ fermerModale(rac); return; }
        if(act === 'creer'){ await creer(rac); return; }
        if(act === 'imprimer'){ imprimer(); return; }
        if(act === 'clore'){ await clore(); return; }
        if(act === 'ajout-action'){ await ajouterAction(rac); return; }
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
      if(t.id === 'reu-machine'){ await enregistrer({machine: t.value}, true); await recharger(); return; }
      if(t.hasAttribute && t.hasAttribute('data-coche')){
        await majAction(t.getAttribute('data-coche'), {fait: t.checked});
      }
    });

    rac.addEventListener('input', function(ev){
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

    rac.addEventListener('keydown', function(ev){
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
    if(!S.contexteCharge || S.reunions === null){ amorcer(); }
    else{ peindre(); }
  }

  function reset(){
    S.vue = 'liste'; S.reunion = null; S.prod = null;
    S.reunions = null; S.notesLocal = null; S.notesEtat = ''; S.erreur = null;
    S.contexteCharge = false;
  }

  window.MySifaReunions = {
    monter: monter, reset: reset,
    rendreListe: rendreListe, rendreReunion: rendreReunion,
    rendreActions: rendreActions, rendreDocument: rendreDocument
  };
})();
