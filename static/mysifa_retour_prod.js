/*
 * MySifa — Retour de production : rendu partage.
 *
 * Deux ecrans affichent la meme matiere : la page /rapports-prod et l'onglet
 * « Retour de prod » de MyProd. Ils consomment les memes endpoints
 * /api/rapports-prod, et ils partagent CE fichier pour le rendu — sinon les
 * deux vues divergent, et un dossier finit par afficher deux chiffres selon
 * l'endroit ou on le regarde.
 *
 * Le module ne connait ni la page ni l'onglet : il rend des chaines HTML et
 * recoit ses effets de bord (toast, rafraichissement) en parametres.
 *
 *   MySifaRetourProd.renderFeuille(data)      -> feuille atelier
 *   MySifaRetourProd.renderListe(lignes)      -> tableau des comptes-rendus
 *   MySifaRetourProd.renderCR(cr)             -> compte-rendu complet
 *   MySifaRetourProd.brancher(racine, no, o)  -> active les editions
 *
 * Toute donnee utilisateur passe par escHtml / escAttr, sans exception.
 */
(function (global) {
  "use strict";

  function escHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
                    .replace(/'/g, "&#39;");
  }
  function escAttr(s) { return escHtml(s).replace(/"/g, "&quot;"); }

  function fnum(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return Number(v).toFixed(digits || 0)
      .replace(/\B(?=(\d{3})+(?!\d))/g, " ").replace(".", ",");
  }
  function minutesTxt(m) {
    if (m === null || m === undefined || isNaN(m)) return "—";
    var t = Math.round(Number(m));
    if (t < 60) return t + " min";
    var h = Math.floor(t / 60), r = t % 60;
    return r === 0 ? h + " h" : h + " h " + String(r).padStart(2, "0");
  }
  function ecartHtml(pct) {
    if (pct === null || pct === undefined || isNaN(pct))
      return '<span class="rp-ecart none">pas de repère</span>';
    var v = Number(pct);
    return '<span class="rp-ecart ' + (v >= 0 ? "up" : "down") + '">'
         + (v >= 0 ? "+" : "") + v.toFixed(0).replace(".", ",") + ' %</span>';
  }
  function dateFr(iso) {
    if (!iso) return "";
    var d = String(iso).slice(0, 10).split("-");
    return d.length === 3 ? d[2] + "/" + d[1] + "/" + d[0] : String(iso);
  }

  var LIB_VIGILANCE = {
    info_prod_absente:       "dossier clôturé sans info prod",
    seuils_sans_explication: "dossier avec un seuil d'arrêt non expliqué",
    saisie_ouverte:          "dossier avec une saisie restée ouverte d'un jour à l'autre",
    metrage_non_fiable:      "dossier sans métrage exploitable",
    arrets_eleves:           "dossier passé à plus de 30 % d'arrêts"
  };
  var LIB_ORIGINE = {
    info_prod:   "Info prod",
    arret:       "Arrêt expliqué",
    commentaire: "Commentaire de saisie",
    annulation:  "Motif d'annulation"
  };

  function kpi(val, lbl, sub) {
    return '<div class="rp-kpi"><div class="k-lbl">' + escHtml(lbl) + '</div>'
         + '<div class="k-val">' + val + '</div>'
         + (sub ? '<div class="k-sub">' + escHtml(sub) + '</div>' : '') + '</div>';
  }

  /* ── Feuille atelier ────────────────────────────────────────── */

  function renderFeuille(d) {
    var p = d.production || {}, per = d.periode || {};

    if (!d.dossiers) {
      return '<div class="rp-feuille"><div class="rp-tete"><div>'
           + '<div class="rp-machine">' + escHtml(d.machine) + '</div>'
           + '<div class="rp-periode">' + escHtml(per.label) + '</div></div></div>'
           + '<div class="rp-vide">Aucun dossier clôturé sur cette machine sur cette période.</div></div>';
    }

    var h = '<div class="rp-feuille"><div class="rp-tete"><div>'
          + '<div class="rp-machine">' + escHtml(d.machine) + '</div>'
          + '<div class="rp-periode">' + escHtml(per.label)
          + (per.mode === "semaine" ? ' — du ' + escHtml(per.du) + ' au ' + escHtml(per.au) : '')
          + '</div></div>';
    if ((d.conducteurs || []).length) {
      h += '<div class="rp-equipe"><b>Aux commandes'
         + (per.mode === "semaine" ? " cette semaine" : " ce jour-là") + '</b><br>'
         + d.conducteurs.map(escHtml).join(" · ") + '</div>';
    }
    h += '</div>';

    h += '<div class="rp-bloc"><div class="rp-titre">Ce qui est sorti de la machine</div><div class="rp-kpis">'
       + kpi(fnum(p.metrage) + ' m', "Métrage produit",
             d.dossiers + (d.dossiers > 1 ? " dossiers" : " dossier"))
       + kpi(minutesTxt(p.minutes_production), "Temps de production",
             p.vitesse_m_h ? fnum(p.vitesse_m_h) + " m/h" : "")
       + kpi(minutesTxt(p.minutes_calage), "Calage et changements", "")
       + kpi(minutesTxt(p.minutes_arret), "Arrêts et attentes",
             p.part_arret_pct ? fnum(p.part_arret_pct, 1) + " % du temps passé" : "")
       + '</div></div>';

    if ((d.references || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Cadence, comparée aux fois précédentes</div>'
         + '<div class="rp-note">Cadence = métrage rapporté au temps de production et d\'arrêt, '
         + 'arrêts compris — même calcul des deux côtés, pour que la comparaison ait un sens.</div>'
         + '<table class="rp-grille"><thead><tr><th>Dossier</th><th>Référence</th>'
         + '<th class="num">Métrage</th><th class="num">Cette fois</th>'
         + '<th class="num">D\'habitude</th><th class="num">Écart</th></tr></thead><tbody>';
      d.references.forEach(function (r) {
        var hab = r.cadence_reference_m_h
          ? fnum(r.cadence_reference_m_h) + ' m/h<div class="rp-sous">sur ' + r.series_passees
            + (r.series_passees > 1 ? ' productions' : ' production') + '</div>'
          : '<span class="rp-mut">1re production</span>';
        h += '<tr><td><b>' + escHtml(r.no_dossier) + '</b></td>'
           + '<td>' + escHtml(r.ref_produit_norm || r.designation || "—") + '</td>'
           + '<td class="num">' + fnum(r.metrage) + ' m</td>'
           + '<td class="num">' + fnum(r.cadence_m_h) + ' m/h'
           + '<div class="rp-sous">' + fnum(r.vitesse_m_h) + ' m/h hors arrêts</div></td>'
           + '<td class="num">' + hab + '</td>'
           + '<td class="num">' + ecartHtml(r.ecart_pct) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    if ((d.arrets_couteux || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Ce qui a coûté le plus de temps</div>'
         + '<table class="rp-grille"><thead><tr><th>Code</th><th>Opération</th>'
         + '<th class="num">Occurrences</th><th class="num">Temps</th></tr></thead><tbody>';
      d.arrets_couteux.forEach(function (a) {
        h += '<tr><td><b>' + escHtml(a.code) + '</b></td>'
           + '<td>' + escHtml(a.operation || "—") + '</td>'
           + '<td class="num">' + a.occurrences + '</td>'
           + '<td class="num">' + escHtml(a.minutes_txt) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    if ((d.ecrits || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Ce que vous avez écrit</div>';
      d.ecrits.forEach(function (e) {
        h += '<div class="rp-mot"><div class="m-txt">' + escHtml(e.texte) + '</div>'
           + '<div class="m-meta"><span class="m-tag">'
           + escHtml(LIB_ORIGINE[e.origine] || e.origine) + '</span>'
           + 'dossier ' + escHtml(e.no_dossier)
           + (e.operation ? ' · ' + escHtml(e.operation) : '')
           + (e.auteur ? ' · ' + escHtml(e.auteur) : '')
           + (e.date ? ' · ' + escHtml(dateFr(e.date)) : '')
           + '</div></div>';
      });
      h += '</div>';
    }

    var vig = d.vigilance || {};
    var cles = Object.keys(vig).filter(function (k) { return vig[k] > 0; });
    if (cles.length) {
      h += '<div class="rp-bloc"><div class="rp-titre">À reprendre au point de production</div>';
      cles.forEach(function (k) {
        h += '<div class="rp-vig"><div class="v-nb">' + vig[k] + '</div><div>'
           + escHtml(LIB_VIGILANCE[k] || k) + (vig[k] > 1 ? " (×" + vig[k] + ")" : "")
           + '</div></div>';
      });
      h += '</div>';
    }

    if (d.nb_nc) {
      h += '<div class="rp-bloc"><div class="rp-titre">Qualité</div><div class="rp-txt">'
         + d.nb_nc + (d.nb_nc > 1 ? ' non-conformités rattachées' : ' non-conformité rattachée')
         + ' aux dossiers de la période.</div></div>';
    }

    return h + '<div class="rp-pied">MySifa · Retour de production · établi le '
             + escHtml(new Date().toLocaleDateString("fr-FR")) + '</div></div>';
  }

  /* ── Liste des comptes-rendus ───────────────────────────────── */

  function renderListe(rows) {
    if (!rows.length) {
      return '<div class="rp-vide">Aucun dossier clôturé sur cette période.<br>'
           + 'La liste se remplit à partir des saisies de fin de production.</div>';
    }
    var h = '<table class="rp-cr"><thead><tr><th>Dossier</th><th>Client</th><th>Machine</th>'
          + '<th class="num">Métrage</th><th class="num">Cadence</th><th class="num">Écart</th>'
          + '<th>Info prod</th><th class="num">Écrits</th><th>Seuils</th><th class="num">NC</th>'
          + '</tr></thead><tbody>';
    rows.forEach(function (r) {
      var info = r.info_prod_substantielle
        ? '<span class="rp-pastille on">renseignée</span>'
        : (r.info_prod ? '<span class="rp-pastille">R.A.S.</span>'
                       : '<span class="rp-pastille att">absente</span>');
      var seuils = r.nb_seuils
        ? (r.nb_seuils_sans_explication
            ? '<span class="rp-pastille att">' + r.nb_seuils_sans_explication + ' sans mot</span>'
            : '<span class="rp-pastille on">' + r.nb_seuils + ' expliqué'
              + (r.nb_seuils > 1 ? 's' : '') + '</span>')
        : '<span class="rp-pastille">—</span>';
      h += '<tr data-dossier="' + escAttr(r.no_dossier) + '">'
         + '<td><b>' + escHtml(r.no_dossier) + '</b>'
         + '<div class="rp-sous">' + escHtml(dateFr(r.date_fin)) + '</div></td>'
         + '<td>' + escHtml(r.client || "—") + '</td>'
         + '<td>' + escHtml(r.machine || "—") + '</td>'
         + '<td class="num">' + fnum(r.metrage_reel) + ' m</td>'
         + '<td class="num">' + (r.cadence_m_h ? fnum(r.cadence_m_h) + ' m/h' : '—') + '</td>'
         + '<td class="num">' + ecartHtml(r.ecart_cadence_pct) + '</td>'
         + '<td>' + info + '</td>'
         + '<td class="num">' + (r.nb_commentaires || 0) + '</td>'
         + '<td>' + seuils + '</td>'
         + '<td class="num">' + (r.nb_nc || 0) + '</td></tr>';
    });
    return h + '</tbody></table>';
  }

  /* ── Résultats de recherche ─────────────────────────────────── */

  function renderRecherche(lignes, terme) {
    if (!lignes.length) {
      return '<div class="rp-note" style="margin-top:10px">Aucun dossier ne porte de saisie '
           + 'correspondant à « ' + escHtml(terme) + ' ».</div>';
    }
    return lignes.map(function (l) {
      return '<div class="rp-rech-item" data-dossier="' + escAttr(l.no_dossier) + '">'
           + '<div><div class="r-id">' + escHtml(l.no_dossier) + '</div>'
           + '<div class="r-meta">' + escHtml(l.client || "—")
           + (l.designation ? ' · ' + escHtml(l.designation) : '')
           + (l.machine ? ' · ' + escHtml(l.machine) : '')
           + ' · ' + l.nb_saisies + (l.nb_saisies > 1 ? ' saisies' : ' saisie')
           + ' · dernière le ' + escHtml(dateFr(l.derniere_saisie)) + '</div></div>'
           + (l.cloture ? '<span class="rp-pastille on">clôturé</span>'
                        : '<span class="rp-pastille att">en cours</span>')
           + '</div>';
    }).join("");
  }


  /* ── Compte-rendu complet d'un dossier ──────────────────────── */

  function renderCR(cr, opts) {
    opts = opts || {};
    var id = cr.identite || {}, t = cr.temps || {}, m = cr.metrage || {};
    var info = (cr.ecrits || {}).info_prod;

    var h = (opts.fermer !== false
              ? '<button class="rp-btn-mini" id="rp-close" style="float:right">Fermer</button>'
              : '')
          + '<h3 class="rp-cr-titre">' + escHtml(cr.no_dossier) + '</h3>'
          + '<div class="rp-cr-sous">' + escHtml(id.client || "—") + ' · '
          + escHtml(id.designation || "—") + ' · ' + escHtml(id.machine || "—")
          + (id.ref_produit_norm ? ' · réf ' + escHtml(id.ref_produit_norm) : '')
          + (id.cloture ? '' : ' · <span class="rp-pastille att">en cours</span>')
          + '</div>';

    h += '<div class="rp-bloc"><div class="rp-kpis">'
       + kpi(fnum(m.reel) + ' m', "Métrage",
             m.prevu ? "prévu " + fnum(m.prevu) + " m" : (m.fiable ? "" : "non exploitable"))
       + kpi(cr.vitesse_m_h ? fnum(cr.vitesse_m_h) + ' m/h' : '—', "Vitesse de production", "hors arrêts")
       + kpi(cr.cadence_m_h ? fnum(cr.cadence_m_h) + ' m/h' : '—', "Cadence", "arrêts compris")
       + kpi(minutesTxt(t.total_minutes), "Temps passé", (id.nb_saisies || 0) + " saisies")
       + kpi(escHtml((id.conducteurs || []).join(", ") || "—"), "Conducteurs", "")
       + '</div></div>';

    if ((t.categories || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Répartition du temps</div>'
         + '<table class="rp-grille"><thead><tr><th>Poste</th><th class="num">Temps</th>'
         + '<th class="num">Part</th><th class="num">Occurrences</th></tr></thead><tbody>';
      t.categories.forEach(function (c) {
        h += '<tr><td>' + escHtml(c.label) + '</td>'
           + '<td class="num">' + minutesTxt(c.minutes) + '</td>'
           + '<td class="num">' + fnum(c.part_pct, 1) + ' %</td>'
           + '<td class="num">' + c.occurrences + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    /* Info prod — toujours affichee, meme absente : c'est le manque qui compte. */
    h += '<div class="rp-bloc"><div class="rp-titre">Info prod de clôture</div>'
       + '<div id="rp-ip-vue">'
       + (info
           ? '<div class="rp-mot"><div class="m-txt">' + escHtml(info.texte) + '</div>'
             + '<div class="m-meta">' + escHtml(info.auteur || "")
             + (info.updated_par && info.updated_par !== info.auteur
                 ? ' · corrigée par ' + escHtml(info.updated_par) : '')
             + ' · ' + escHtml(dateFr(info.updated_at || info.created_at)) + '</div></div>'
           : '<div class="rp-manque">Aucune info prod enregistrée pour ce dossier.'
             + (id.cloture ? ' Elle est pourtant due à la clôture.'
                           : ' Le dossier n\'est pas encore clôturé.') + '</div>')
       + '<div class="rp-edit-actions"><button type="button" class="rp-btn-mini" id="rp-ip-edit">'
       + (info ? 'Modifier' : 'Renseigner') + '</button></div></div>'
       + '<div id="rp-ip-form" style="display:none"><div class="rp-edit">'
       + '<textarea id="rp-ip-txt" placeholder="Ce qu\'il faut savoir pour la prochaine production de cette référence">'
       + escHtml(info ? info.texte : "") + '</textarea>'
       + '<div class="rp-edit-actions">'
       + '<button type="button" class="rp-btn-mini" id="rp-ip-annul">Annuler</button>'
       + '<button type="button" class="rp-btn-mini primaire" id="rp-ip-ok">Enregistrer</button>'
       + '</div></div></div></div>';

    if ((cr.seuils || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Seuils d\'arrêt franchis</div>';
      cr.seuils.forEach(function (s) {
        var sid = s.saisie_id;
        h += '<div class="rp-mot"><div class="m-txt" id="rp-sx-vue-' + sid + '">'
           + (s.explication_texte
               ? escHtml(s.explication_texte)
               : '<span class="rp-attente">Sans explication — à poser au point de production</span>')
           + '</div><div class="m-meta"><span class="m-tag">' + escHtml(s.operation_code) + '</span>'
           + escHtml(s.operation || "") + ' · ' + escHtml(s.duree_saisie_txt || "")
           + (s.operateur ? ' · ' + escHtml(s.operateur) : '') + '</div>'
           + '<div class="rp-edit-actions"><button type="button" class="rp-btn-mini" data-seuil="'
           + sid + '">' + (s.explication_texte ? 'Compléter' : 'Expliquer') + '</button></div>'
           + '<div class="rp-edit" id="rp-sx-form-' + sid + '" style="display:none">'
           + '<textarea id="rp-sx-txt-' + sid + '" placeholder="Ce qui s\'est passé, et ce qui a été fait">'
           + escHtml(s.explication_texte || "") + '</textarea>'
           + '<div class="rp-edit-actions">'
           + '<button type="button" class="rp-btn-mini" data-seuil-annul="' + sid + '">Annuler</button>'
           + '<button type="button" class="rp-btn-mini primaire" data-seuil-ok="' + sid + '">Enregistrer</button>'
           + '</div></div></div>';
      });
      h += '</div>';
    }

    var coms = (cr.ecrits || {}).commentaires || [];
    if (coms.length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Commentaires de saisie</div>';
      coms.forEach(function (c) {
        h += '<div class="rp-mot"><div class="m-txt">' + escHtml(c.texte) + '</div>'
           + '<div class="m-meta"><span class="m-tag">'
           + escHtml(LIB_ORIGINE[c.origine] || c.origine) + '</span>'
           + escHtml(c.operateur || "") + ' · ' + escHtml(dateFr(c.date)) + '</div></div>';
      });
      h += '</div>';
    }

    if ((cr.non_conformites || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Non-conformités</div>'
         + '<table class="rp-grille"><thead><tr><th>Numéro</th><th>Titre</th>'
         + '<th>Gravité</th><th>Statut</th></tr></thead><tbody>';
      cr.non_conformites.forEach(function (n) {
        h += '<tr><td><b>' + escHtml(n.numero) + '</b></td><td>' + escHtml(n.titre) + '</td>'
           + '<td>' + escHtml(n.gravite || "—") + '</td>'
           + '<td>' + escHtml(n.statut || "—") + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    if ((cr.vigilance || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">À reprendre</div>';
      cr.vigilance.forEach(function (v) {
        h += '<div class="rp-vig"><div class="v-nb">·</div><div>' + escHtml(v.texte) + '</div></div>';
      });
      h += '</div>';
    }
    return h;
  }

  /* ── Editions : info prod et explications d'arret ───────────── */

  function poster(url, corps) {
    return fetch(url, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps)
    }).then(function (r) {
      if (r.ok) return r.json();
      return r.json().catch(function () { return {}; }).then(function (j) {
        throw new Error((j && j.detail) || ("Erreur " + r.status));
      });
    });
  }

  function ouvrirForm(R, idVue, idForm, idTxt) {
    var v = R.querySelector("#" + idVue), f = R.querySelector("#" + idForm),
        t = R.querySelector("#" + idTxt);
    if (!v || !f || !t) return;
    v.style.display = "none";
    f.style.display = "";
    t.focus();
    t.setSelectionRange(t.value.length, t.value.length);
  }
  function fermerForm(R, idVue, idForm) {
    var v = R.querySelector("#" + idVue), f = R.querySelector("#" + idForm);
    if (f) f.style.display = "none";
    if (v) v.style.display = "";
  }

  /*
   * Active les editions rendues par renderCR.
   *   no           : numero de dossier
   *   opts.racine  : noeud contenant le rendu — un noeud DETACHE convient, ce
   *                  qui permet a MyProd de brancher avant insertion dans le
   *                  DOM (son `render()` remplace l'arbre a chaque passe).
   *                  Defaut : document.
   *   opts.onSaved : rappel apres ecriture reussie (rafraichir la vue)
   *   opts.toast   : (message, type) — retour visuel, optionnel
   */
  function brancher(no, opts) {
    opts = opts || {};
    var R = opts.racine || document;
    var dire = opts.toast || function () {};

    var edit = R.querySelector("#rp-ip-edit");
    if (edit) {
      edit.onclick = function () { ouvrirForm(R, "rp-ip-vue", "rp-ip-form", "rp-ip-txt"); };
      R.querySelector("#rp-ip-annul").onclick = function () {
        fermerForm(R, "rp-ip-vue", "rp-ip-form");
      };
      R.querySelector("#rp-ip-ok").onclick = function (e) {
        var b = e.target; b.disabled = true;
        poster("/api/rapports-prod/dossier/" + encodeURIComponent(no) + "/info-prod",
               { texte: R.querySelector("#rp-ip-txt").value })
          .then(function () {
            dire("Info prod enregistrée.", "info");
            if (opts.onSaved) opts.onSaved();
          })
          .catch(function (err) { dire(err.message, "danger"); b.disabled = false; });
      };
    }

    Array.prototype.forEach.call(R.querySelectorAll("[data-seuil]"), function (b) {
      var sid = b.getAttribute("data-seuil");
      b.onclick = function () {
        ouvrirForm(R, "rp-sx-vue-" + sid, "rp-sx-form-" + sid, "rp-sx-txt-" + sid);
      };
    });
    Array.prototype.forEach.call(R.querySelectorAll("[data-seuil-annul]"), function (b) {
      var sid = b.getAttribute("data-seuil-annul");
      b.onclick = function () { fermerForm(R, "rp-sx-vue-" + sid, "rp-sx-form-" + sid); };
    });
    Array.prototype.forEach.call(R.querySelectorAll("[data-seuil-ok]"), function (b) {
      var sid = b.getAttribute("data-seuil-ok");
      b.onclick = function (e) {
        var txt = (R.querySelector("#rp-sx-txt-" + sid).value || "").trim();
        if (!txt) { dire("Explication vide.", "danger"); return; }
        var btn = e.target; btn.disabled = true;
        poster("/api/rapports-prod/seuil/" + encodeURIComponent(sid) + "/explication",
               { texte: txt })
          .then(function () {
            dire("Explication enregistrée.", "info");
            if (opts.onSaved) opts.onSaved();
          })
          .catch(function (err) { dire(err.message, "danger"); btn.disabled = false; });
      };
    });
  }

  global.MySifaRetourProd = {
    escHtml: escHtml, escAttr: escAttr,
    fnum: fnum, minutesTxt: minutesTxt, ecartHtml: ecartHtml, dateFr: dateFr,
    kpi: kpi, LIB_ORIGINE: LIB_ORIGINE, LIB_VIGILANCE: LIB_VIGILANCE,
    renderFeuille: renderFeuille,
    renderListe: renderListe,
    renderRecherche: renderRecherche,
    renderCR: renderCR,
    brancher: brancher
  };
})(window);
