/*
 * MySifa — Retour de production : rendu partage.
 *
 * Rendu de l'onglet « Retour de prod » de MyProd (/prod#retour), qui consomme
 * les endpoints /api/rapports-prod.
 *
 * Le rendu vit ici, et pas dans l'onglet, pour deux raisons. D'abord parce
 * qu'un rendu ecrit dans un ecran finit toujours par etre recopie dans le
 * suivant, et les deux divergent : un dossier affiche alors deux chiffres
 * selon l'endroit ou on le regarde. Ensuite parce que le module ne connait
 * rien de son hote — il rend des chaines HTML et recoit ses effets de bord
 * (toast, rafraichissement, racine DOM) en parametres, donc un second ecran
 * s'en sert sans rien reecrire.
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
  // La machine se regle en m/min : c'est l'unite du conducteur, celle de
  // `produit_series.vitesse_m_min` et celle qu'affiche tout MySifa. Pas de m/h.
  function vitesse(v) {
    return (v === null || v === undefined || isNaN(v)) ? "—" : fnum(v, 1) + " m/min";
  }

  // « 66 » affiche a cote de « 66 - Attente matiere » : on ne repete pas le code.
  function sansCode(operation, code) {
    var op = String(operation || ""), c = String(code || "");
    if (!c) return op;
    var re = new RegExp("^\\s*" + c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*[-–]\\s*");
    return op.replace(re, "");
  }

  function dateFr(iso) {
    if (!iso) return "";
    var d = String(iso).slice(0, 10).split("-");
    return d.length === 3 ? d[2] + "/" + d[1] + "/" + d[0] : String(iso);
  }

  var LIB_VIGILANCE = {
    info_prod_absente:       "clôturé sans info prod",
    seuils_sans_explication: "seuil d'arrêt non expliqué",
    saisie_ouverte:          "saisie restée ouverte",
    metrage_non_fiable:      "métrage inexploitable",
    arrets_eleves:           "plus de 30 % d'arrêts"
  };
  var LIB_ORIGINE = {
    info_prod:   "Info prod",
    arret:       "Arrêt",
    commentaire: "Saisie",
    annulation:  "Annulation"
  };

  function kpi(val, lbl, sub) {
    return '<div class="rp-kpi"><div class="k-lbl">' + escHtml(lbl) + '</div>'
         + '<div class="k-val">' + val + '</div>'
         + (sub ? '<div class="k-sub">' + escHtml(sub) + '</div>' : '') + '</div>';
  }



  /* ── Frise de production ────────────────────────────────────── */

  // Meme allure que le planning, mais posee sur de vraies dates. Les positions
  // arrivent en pourcentage, calculees et testees cote serveur : l'ecran ne
  // fait que poser des rectangles.
  function renderFrise(f, opts) {
    opts = opts || {};
    if (!f || f.vide || !(f.lignes || []).length) return "";

    // Les separations de journees traversent toutes les pistes : sans elles, on
    // ne sait plus ou finit un jour et ou commence le suivant.
    var separateurs = (f.axe || []).slice(1).map(function (a) {
      return '<div class="rp-fr-sep' + (a.coupure_avant ? ' coupe' : '') + '"'
           + ' style="left:' + a.x + '%"></div>';
    }).join("");

    var entetes = (f.axe || []).map(function (a) {
      return '<div class="rp-fr-jour" style="left:' + a.x + '%;width:' + a.largeur + '%">'
           + '<span>' + escHtml(a.label) + '</span>'
           + '<em>' + escHtml(a.heures) + ' h</em></div>';
    }).join("");

    var lignes = f.lignes.map(function (l) {
      var slots = (l.slots || []).map(function (sl) {
        var segs = (sl.segments || []).map(function (g) {
          return '<div class="rp-fr-seg mst-' + escAttr(g.statut || "autre") + '"'
               + ' style="left:' + g.x + '%;width:' + g.largeur + '%"></div>';
        }).join("");
        var fmt = sl.format || (sl.laize_mm ? sl.laize_mm + " mm" : "");
        // Densite du libelle. Quatre lignes dans un slot etroit, ce sont quatre
        // « … » : on en retire plutot que de tout tronquer. Le seuil est en
        // pourcentage de la piste, comme la geometrie qui arrive du serveur.
        var large = Number(sl.largeur) || 0;
        var densite = large >= 16 ? '' : (large >= 9 ? ' moyen' : ' etroit');
        return '<div class="rp-fr-slot' + densite
             + (sl.deborde_avant ? ' deborde-avant' : '')
             + (sl.deborde_apres ? ' deborde-apres' : '')
             + '" data-dossier="' + escAttr(sl.no_dossier) + '"'
             + ' data-tip="' + escAttr(JSON.stringify(sl)) + '"'
             + ' style="left:' + sl.x + '%;width:' + sl.largeur + '%">'
             + '<div class="rp-fr-fond">' + segs + '</div>'
             + '<div class="rp-fr-lbl">'
             + '<b>' + escHtml(sl.no_dossier) + '</b>'
             + (sl.client ? '<span>' + escHtml(sl.client) + '</span>' : '')
             + (sl.ref_produit_norm || fmt
                 ? '<i>' + escHtml([sl.ref_produit_norm, fmt].filter(Boolean).join(" · ")) + '</i>'
                 : '')
             + (sl.quantite ? '<u>' + fnum(sl.quantite) + ' ét.</u>' : '')
             + '</div></div>';
      }).join("");
      return '<div class="rp-fr-ligne"><div class="rp-fr-machine">' + escHtml(l.machine) + '</div>'
           + '<div class="rp-fr-piste">' + separateurs + slots + '</div></div>';
    }).join("");

    // Meme legende que Saisieprod, memes couleurs : l'atelier n'a pas a
    // apprendre un second code.
    var legende = [["production", "Production"], ["calage", "Calage"],
                   ["arret", "Arrêt"], ["nettoyage", "Nettoyage"], ["autre", "Autre"]]
      .map(function (c) {
        return '<span class="rp-fr-leg"><i class="mst-' + c[0] + '"></i>' + c[1] + '</span>';
      }).join("");

    return '<div class="rp-bloc rp-frise">'
      + (opts.titre === false ? '' : '<div class="rp-titre">Frise de production</div>')
      + '<div class="rp-fr-cadre">'
      + '<div class="rp-fr-axe"><div class="rp-fr-machine"></div>'
      + '<div class="rp-fr-piste">' + entetes + '</div></div>'
      + lignes + '</div>'
      + '<div class="rp-fr-legende">' + legende
      + '<span class="rp-fr-note">Journées sans saisie repliées (trait pointillé). '
      + 'Un dossier commencé avant ou non terminé déborde de la frise.</span></div>'
      + '</div>';
  }

  /* ── Infobulle de la frise ──────────────────────────────────── */

  // Meme forme que l'infobulle du planning. Posee sur <body> et non dans la
  // frise : celle-ci defile horizontalement, une infobulle a l'interieur
  // serait rognee par son propre conteneur.
  var LIB_STATUT = { production: "Production", calage: "Calage", arret: "Arrêt",
                     nettoyage: "Nettoyage", autre: "Autre" };

  function _tipHtml(sl) {
    var fmt = sl.format || (sl.laize_mm ? sl.laize_mm + " mm" : "");
    var lignes = [
      ["Client", sl.client],
      ["Référence", sl.ref_produit_norm],
      ["Format", fmt],
      ["Quantité", sl.quantite ? fnum(sl.quantite) + " étiquettes" : ""],
      ["Conducteurs", (sl.operateurs || []).join(", ")],
      ["Début", sl.debut ? dateFr(sl.debut) + " " + String(sl.debut).slice(11, 16) : ""],
      ["Fin", sl.fin ? dateFr(sl.fin) + " " + String(sl.fin).slice(11, 16) : ""],
      ["Temps passé", minutesTxt(sl.minutes)]
    ].filter(function (l) { return l[1]; })
     .map(function (l) {
       return '<div class="rp-tip-l"><span>' + escHtml(l[0]) + '</span><b>'
            + escHtml(l[1]) + '</b></div>';
     }).join("");

    var phases = {};
    (sl.segments || []).forEach(function (g) {
      var k = g.statut || "autre";
      phases[k] = (phases[k] || 0) + (g.minutes || 0);
    });
    var detail = Object.keys(phases).map(function (k) {
      return '<div class="rp-tip-ph"><i class="mst-' + escAttr(k) + '"></i>'
           + '<span>' + escHtml(LIB_STATUT[k] || k) + '</span>'
           + '<b>' + escHtml(minutesTxt(phases[k])) + '</b></div>';
    }).join("");

    return '<div class="rp-tip-hdr"><div class="rp-tip-bar"></div>'
      + '<div><div class="rp-tip-ref">' + escHtml(sl.no_dossier) + '</div>'
      + (sl.deborde_avant || sl.deborde_apres
          ? '<div class="rp-tip-sub">déborde de la période affichée</div>' : '')
      + '</div></div>'
      + lignes + (detail ? '<div class="rp-tip-sep"></div>' + detail : '');
  }

  function brancherFrise(racine, opts) {
    opts = opts || {};
    var R = racine || document;
    var tip = null;
    function fermer() { if (tip && tip.parentNode) tip.parentNode.removeChild(tip); tip = null; }

    Array.prototype.forEach.call(R.querySelectorAll(".rp-fr-slot[data-tip]"), function (el) {
      el.addEventListener("mouseenter", function () {
        var sl;
        try { sl = JSON.parse(el.getAttribute("data-tip")); } catch (e) { return; }
        fermer();
        tip = document.createElement("div");
        tip.className = "rp-tip";
        tip.innerHTML = _tipHtml(sl);
        document.body.appendChild(tip);
        placer(el);
      });
      el.addEventListener("mousemove", function () { if (tip) placer(el); });
      el.addEventListener("mouseleave", fermer);
      if (opts.onClic) {
        el.addEventListener("click", function () {
          fermer();
          opts.onClic(el.getAttribute("data-dossier"));
        });
      }
    });

    function placer(el) {
      if (!tip) return;
      var r = el.getBoundingClientRect();
      var largeur = tip.offsetWidth, hauteur = tip.offsetHeight;
      var x = Math.min(Math.max(8, r.left + r.width / 2 - largeur / 2),
                       window.innerWidth - largeur - 8);
      var y = r.top - hauteur - 10;
      if (y < 8) y = r.bottom + 10;          // pas de place au-dessus : on passe dessous
      tip.style.left = (x + window.scrollX) + "px";
      tip.style.top = (y + window.scrollY) + "px";
    }
  }

  /* ── Une remontee, avec ses gestes ────────────────────── */

  // Un id DOM ne peut pas porter les deux-points de la cle : on l'aplatit.
  function slug(cle) { return String(cle || "").replace(/[^A-Za-z0-9_-]/g, "_"); }

  /*
   * Rend une remontee : le texte, sa provenance, son etat, et les trois gestes
   * qu'on peut poser dessus — valider (c'est traite), modifier (le texte est
   * faux ou incomplet), commenter (on repond). Valider n'efface pas : ce qui
   * disparait de l'ecran n'est jamais relu.
   */
  function renderEcrit(e, opts) {
    opts = opts || {};
    var id = slug(e.cle), actions = [];

    if (e.cle) {
      actions.push('<button type="button" class="rp-btn-mini" data-valider="' + escAttr(e.cle)
        + '" data-dossier="' + escAttr(e.no_dossier || opts.no_dossier || "") + '"'
        + ' data-etat="' + (e.valide ? "1" : "0") + '">'
        + (e.valide ? "Dévalider" : "Valider") + '</button>');
      if (e.modifiable) {
        actions.push('<button type="button" class="rp-btn-mini" data-modif="' + escAttr(e.cle)
          + '" data-origine="' + escAttr(e.origine || "") + '"'
          + ' data-ref="' + escAttr(e.reference == null ? "" : e.reference) + '"'
          + ' data-dossier="' + escAttr(e.no_dossier || opts.no_dossier || "") + '">Modifier</button>');
      }
      actions.push('<button type="button" class="rp-btn-mini" data-commenter="' + escAttr(e.cle)
        + '" data-dossier="' + escAttr(e.no_dossier || opts.no_dossier || "") + '">Commenter</button>');
      actions.push('<button type="button" class="rp-btn-mini" data-masquer="' + escAttr(e.cle)
        + '" data-dossier="' + escAttr(e.no_dossier || opts.no_dossier || "") + '"'
        + ' data-etat="' + (e.masque ? "1" : "0") + '">'
        + (e.masque ? "Réafficher" : "Masquer") + '</button>');
    }

    // Les reponses vivent DANS la remontee, en citation : ajoutees a la file,
    // elles la noyaient.
    var reponses = (e.reponses || []).map(function (r) {
      return '<div class="rp-citation"><div class="c-txt">' + escHtml(r.texte) + '</div>'
           + '<div class="c-meta">' + escHtml(r.auteur || "")
           + (r.created_at ? ' · ' + escHtml(dateFr(r.updated_at || r.created_at)) : '')
           + '</div></div>';
    }).join("");

    return '<div class="rp-mot' + (e.valide ? ' est-valide' : '')
      + (e.masque ? ' est-masque' : '') + '">'
      + '<div class="m-txt" id="rp-e-vue-' + id + '">' + escHtml(e.texte) + '</div>'
      + '<div class="m-meta">'
      + (e.origine ? '<span class="m-tag">' + escHtml(LIB_ORIGINE[e.origine] || e.origine) + '</span>' : '')
      + (opts.avecDossier && e.no_dossier ? escHtml(e.no_dossier) + ' · ' : '')
      + (e.operation ? escHtml(sansCode(e.operation, e.operation_code)) + ' · ' : '')
      + escHtml(e.auteur || "")
      + (e.date ? ' · ' + escHtml(dateFr(e.date)) : '')
      + (e.valide ? '<span class="rp-vu">traité' + (e.valide_par ? ' par ' + escHtml(e.valide_par) : '')
                    + (e.valide_le ? ' le ' + escHtml(dateFr(e.valide_le)) : '') + '</span>' : '')
      + '</div>'
      + reponses
      + (actions.length ? '<div class="rp-edit-actions">' + actions.join("") + '</div>' : '')
      + '<div class="rp-edit" id="rp-e-form-' + id + '" style="display:none">'
      + '<textarea id="rp-e-txt-' + id + '">' + escHtml(e.texte || "") + '</textarea>'
      + '<div class="rp-edit-actions">'
      + '<button type="button" class="rp-btn-mini" data-annul="' + id + '" data-quoi="form">Annuler</button>'
      + '<button type="button" class="rp-btn-mini primaire" data-modif-ok="' + escAttr(e.cle) + '"'
      + ' data-origine="' + escAttr(e.origine || "") + '"'
      + ' data-ref="' + escAttr(e.reference == null ? "" : e.reference) + '"'
      + ' data-dossier="' + escAttr(e.no_dossier || opts.no_dossier || "") + '">Enregistrer</button>'
      + '</div></div>'
      + '<div class="rp-edit" id="rp-e-com-' + id + '" style="display:none">'
      + '<textarea id="rp-e-comtxt-' + id + '" placeholder="Votre réponse"></textarea>'
      + '<div class="rp-edit-actions">'
      + '<button type="button" class="rp-btn-mini" data-annul="' + id + '" data-quoi="com">Annuler</button>'
      + '<button type="button" class="rp-btn-mini primaire" data-com-ok="' + escAttr(e.cle) + '"'
      + ' data-dossier="' + escAttr(e.no_dossier || opts.no_dossier || "") + '">Envoyer</button>'
      + '</div></div>'
      + '</div>';
  }

  /* ── Feuille atelier ────────────────────────────────────────── */

  function renderFeuille(d, frise) {
    var p = d.production || {}, per = d.periode || {};

    if (!d.dossiers) {
      return '<div class="rp-feuille"><div class="rp-tete"><div>'
           + '<div class="rp-machine">'
           + escHtml(d.toutes_machines ? "Toutes les machines" : d.machine) + '</div>'
           + '<div class="rp-periode">' + escHtml(per.label) + '</div></div></div>'
           + '<div class="rp-vide">Aucun dossier clôturé.</div></div>';
    }

    var h = '<div class="rp-feuille"><div class="rp-tete"><div>'
          + '<div class="rp-machine">'
          + escHtml(d.toutes_machines ? "Toutes les machines" : d.machine) + '</div>'
          + (d.toutes_machines && (d.machines_couvertes || []).length
              ? '<div class="rp-sous">' + d.machines_couvertes.map(escHtml).join(" · ") + '</div>'
              : '')
          + '<div class="rp-periode">' + escHtml(per.label)
          + (per.mode === "semaine" ? ' — du ' + escHtml(per.du) + ' au ' + escHtml(per.au) : '')
          + '</div></div>';
    if ((d.conducteurs || []).length) {
      h += '<div class="rp-equipe"><b>Aux commandes</b><br>'
         + d.conducteurs.map(escHtml).join(" · ") + '</div>';
    }
    h += '</div>';

    h += '<div class="rp-bloc"><div class="rp-titre">Production</div><div class="rp-kpis">'
       + kpi(fnum(p.metrage) + ' m', "Métrage",
             d.dossiers + (d.dossiers > 1 ? " dossiers" : " dossier"))
       + kpi(minutesTxt(p.minutes_production), "Production",
             p.vitesse_m_min ? vitesse(p.vitesse_m_min) : "")
       + kpi(minutesTxt(p.minutes_calage), "Calage", "")
       + kpi(minutesTxt(p.minutes_arret), "Arrêts",
             p.part_arret_pct ? fnum(p.part_arret_pct, 1) + " % du temps" : "")
       + '</div></div>';

    h += renderFrise(frise);

    if ((d.references || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre" title="Cadence = m\u00e8tres par minute, '
         + 'arr\u00eats compris. M\u00eame calcul des deux c\u00f4t\u00e9s.">Cadence</div>'
         + '<table class="rp-grille"><thead><tr><th>Dossier</th><th>Client</th><th>Référence</th>'
         + '<th class="num">Métrage</th><th class="num">Cette fois</th>'
         + '<th class="num">D\'habitude</th><th class="num">Écart</th></tr></thead><tbody>';
      d.references.forEach(function (r) {
        var hab = r.cadence_reference_m_min
          ? vitesse(r.cadence_reference_m_min) + '<div class="rp-sous">'
            + r.series_passees + (r.series_passees > 1 ? ' prod.' : ' prod.') + '</div>'
          : '<span class="rp-mut">1re fois</span>';
        h += '<tr><td><b>' + escHtml(r.no_dossier) + '</b></td>'
           + '<td>' + escHtml(r.client || "—") + '</td>'
           + '<td>' + escHtml(r.ref_produit_norm || r.designation || "—") + '</td>'
           + '<td class="num">' + fnum(r.metrage) + ' m</td>'
           + '<td class="num">' + vitesse(r.cadence_m_min)
           + '<div class="rp-sous">' + vitesse(r.vitesse_m_min) + ' hors arrêts</div></td>'
           + '<td class="num">' + hab + '</td>'
           + '<td class="num">' + ecartHtml(r.ecart_pct) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    h += renderSaisies(d.saisies);

    if ((d.ecrits || []).length) {
      var restants = d.ecrits.filter(function (e) { return !e.valide; }).length;
      var masques = d.ecrits_masques || [];
      h += '<div class="rp-bloc"><div class="rp-titre rp-titre-ligne"><span>Vos écrits'
         + (restants ? ' <span class="rp-compte">' + restants + ' à traiter</span>' : '')
         + '</span>'
         + (masques.length
             ? '<button type="button" class="rp-btn-mini" id="rp-masques-btn">'
               + 'Commentaires masqués (' + masques.length + ')</button>'
             : '')
         + '</div>';
      d.ecrits.forEach(function (e) { h += renderEcrit(e, { avecDossier: true }); });
      if (masques.length) {
        h += '<div id="rp-masques" style="display:none">'
           + '<div class="rp-note">Remontées jugées hors sujet — elles ne parlent pas de la '
           + 'qualité de la production. Rien n\'est effacé.</div>';
        masques.forEach(function (e) { h += renderEcrit(e, { avecDossier: true }); });
        h += '</div>';
      }
      h += '</div>';
    }

    var vig = d.vigilance || {};
    var cles = Object.keys(vig).filter(function (k) { return vig[k] > 0; });
    if (cles.length) {
      h += '<div class="rp-bloc"><div class="rp-titre">À reprendre</div>';
      cles.forEach(function (k) {
        h += '<div class="rp-vig"><div class="v-nb">' + vig[k] + '</div><div>'
           + escHtml(LIB_VIGILANCE[k] || k) + (vig[k] > 1 ? " (×" + vig[k] + ")" : "")
           + '</div></div>';
      });
      h += '</div>';
    }

    if (d.nb_nc) {
      h += '<div class="rp-bloc"><div class="rp-titre">Qualité</div><div class="rp-txt">'
         + d.nb_nc + (d.nb_nc > 1 ? ' non-conformités' : ' non-conformité')
         + '</div></div>';
    }

    return h + '<div class="rp-pied">MySifa · ' + escHtml(new Date().toLocaleDateString("fr-FR"))
             + '</div></div>';
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
         + '<td class="num">' + (r.cadence_m_min ? vitesse(r.cadence_m_min) : '—') + '</td>'
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

  /* Le deroule des saisies de la periode. Uniquement les saisies de production :
     ni les mouvements de stock ni les validations d'alerte, que l'onglet
     Saisies fusionne dans sa liste mais qui n'apprennent rien sur la machine.

     La liste est haute par nature — une journee fait vite trente lignes. Elle
     defile donc dans sa propre fenetre, et le bouton d'entete l'ouvre en grand
     pour ceux qui veulent tout voir d'un coup. */
  /* Filtre et tri du deroule. Tout se joue dans le navigateur : la liste est
     deja entiere dans la page, un aller-retour serveur n'apporterait qu'une
     attente. La fonction est PURE — elle ne lit pas l'etat du module — pour
     etre appelable dans un test sans DOM. */
  var SA_CHAMPS = {
    heure: function (r) { return _t(r.date_operation) || _t(r.heure); },
    operation: function (r) { return _pli(sansCode(r.operation, r.code) || r.code); },
    dossier: function (r) { return _pli(r.no_dossier); },
    operateur: function (r) { return _pli(r.operateur); },
    duree: function (r) { return typeof r.minutes === "number" ? r.minutes : -1; }
  };

  function _t(v) { return v == null ? "" : String(v); }
  function _pli(v) {
    v = _t(v);
    return v.normalize
      ? v.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
      : v.toLowerCase();
  }

  function filtrerTrier(liste, opts) {
    liste = liste || [];
    opts = opts || {};
    var q = _pli(opts.q).trim();
    var exclus = opts.exclus || {};
    var champ = SA_CHAMPS[opts.champ] ? opts.champ : "heure";
    var sens = opts.sens === -1 ? -1 : 1;

    var gardees = liste.filter(function (r) {
      if (exclus[r.statut || "autre"]) return false;
      if (!q) return true;
      // La recherche porte sur tout ce que la ligne montre — y compris le
      // commentaire, qui est souvent la seule chose qu'on cherche.
      return _pli([r.operation, r.code, r.no_dossier, r.client,
                   r.ref_produit_norm, r.operateur, r.commentaire, r.heure]
                  .filter(Boolean).join(" ")).indexOf(q) !== -1;
    });

    // Tri stable : a valeur egale, l'ordre chronologique reprend la main.
    var lu = SA_CHAMPS[champ];
    return gardees.map(function (r, i) { return { r: r, i: i }; })
      .sort(function (a, b) {
        var va = lu(a.r), vb = lu(b.r);
        if (va < vb) return -1 * sens;
        if (va > vb) return 1 * sens;
        return a.i - b.i;
      })
      .map(function (x) { return x.r; });
  }

  var SA_STATUTS = [["production", "Production"], ["calage", "Calage"],
                    ["arret", "Arrêt"], ["nettoyage", "Nettoyage"], ["autre", "Autre"]];
  var SA_COLONNES = [["heure", "Heure", ""], ["operation", "Opération", ""],
                     ["dossier", "Dossier", ""], ["operateur", "Opérateur", ""],
                     ["duree", "Durée", "num"]];

  // Etat du filtre, garde entre deux rendus : MyProd reconstruit son DOM a
  // chaque passe, une selection perdue a chaque toast serait inutilisable.
  var _sa = { q: "", exclus: {}, champ: "heure", sens: 1, liste: [] };

  function _saLignes(liste) {
    return liste.map(function (r) {
      // Le dossier a sa propre colonne : porte sous l'operation, son numero
      // etait tronque a mi-mot alors que la moitie de la ligne restait vide.
      var repere = [r.ref_produit_norm, r.client].filter(Boolean).map(escHtml).join(" · ");
      return '<tr class="rp-sa-l">'
        + '<td class="rp-sa-h">' + escHtml(r.heure) + '</td>'
        + '<td class="rp-sa-op"><div class="rp-sa-opin">'
        + '<i class="rp-sa-pt mst-' + escAttr(r.statut || "autre") + '"'
        + ' title="' + escAttr(r.label || "") + '"></i>'
        + '<span><b title="' + escAttr(sansCode(r.operation, r.code) || r.code || "") + '">'
        + escHtml(sansCode(r.operation, r.code) || r.code || "—") + '</b>'
        + (r.commentaire ? '<span class="rp-sa-com">' + escHtml(r.commentaire) + '</span>' : '')
        + '</span></div></td>'
        + '<td class="rp-sa-dos">'
        + (r.no_dossier
            ? '<b title="' + escAttr(r.no_dossier) + '">' + escHtml(r.no_dossier) + '</b>'
              + (repere ? '<span class="rp-sous">' + repere + '</span>' : '')
            : '<span class="rp-mut">—</span>')
        + '</td>'
        + '<td class="rp-sa-qui">' + escHtml(r.operateur || "—") + '</td>'
        + '<td class="num rp-sa-d">' + escHtml(r.minutes_txt || "—") + '</td>'
        + '</tr>';
    }).join("")
      || '<tr><td colspan="5" class="rp-sa-rien">Aucune saisie ne correspond '
         + 'au filtre.</td></tr>';
  }

  function _saEntetes() {
    return SA_COLONNES.map(function (c) {
      var actif = _sa.champ === c[0];
      return '<th class="rp-sa-tri' + (actif ? " actif" : "")
        + (c[2] ? " " + c[2] : '') + '" data-sa-tri="' + c[0] + '" '
        + 'aria-sort="' + (actif ? (_sa.sens === 1 ? "ascending" : "descending") : "none")
        + '" title="Trier par ' + escAttr(c[1].toLowerCase()) + '">'
        + escHtml(c[1]) + '<span class="rp-sa-fl">'
        + (actif ? (_sa.sens === 1 ? "↑" : "↓") : "") + '</span></th>';
    }).join("");
  }

  function _saCompte(total, vues) {
    return vues === total ? String(total) : vues + " / " + total;
  }

  function renderSaisies(liste) {
    liste = liste || [];
    if (!liste.length) return "";
    _sa.liste = liste;
    var vues = filtrerTrier(liste, _sa);
    return '<div class="rp-bloc rp-saisies" id="rp-saisies">'
      + '<div class="rp-titre rp-titre-ligne"><span>Saisies '
      + '<span class="rp-compte" id="rp-sa-nb">' + _saCompte(liste.length, vues.length)
      + '</span></span>'
      + '<button type="button" class="rp-sa-plus" id="rp-sa-plus" '
      + 'aria-expanded="false" title="Afficher plus de lignes" '
      + 'aria-label="Afficher plus de lignes">' + ICONE_ETENDRE + '</button></div>'
      + '<div class="rp-sa-barre">'
      + '<input type="search" id="rp-sa-q" autocomplete="off" '
      + 'placeholder="Filtrer : op&eacute;ration, dossier, client, conducteur, commentaire&hellip;" '
      + 'aria-label="Filtrer les saisies" value="' + escAttr(_sa.q) + '">'
      + '<div class="rp-sa-st">'
      + SA_STATUTS.map(function (c) {
          var on = !_sa.exclus[c[0]];
          return '<button type="button" class="rp-sa-stp' + (on ? " actif" : "") + '" '
            + 'data-sa-st="' + c[0] + '" aria-pressed="' + (on ? "true" : "false") + '">'
            + '<i class="rp-sa-pt mst-' + c[0] + '"></i>' + escHtml(c[1]) + '</button>';
        }).join("")
      + '</div></div>'
      + '<div class="rp-sa-cadre" id="rp-sa-cadre">'
      + '<table class="rp-grille rp-sa-tbl">'
      + '<colgroup><col class="c-h"><col class="c-op"><col class="c-dos">'
      + '<col class="c-qui"><col class="c-d"></colgroup>'
      + '<thead><tr>' + _saEntetes() + '</tr></thead>'
      + '<tbody id="rp-sa-corps">' + _saLignes(vues) + '</tbody></table></div></div>';
  }

  var ICONE_ETENDRE =
      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<polyline points="7 13 12 18 17 13"/><polyline points="7 6 12 11 17 6"/></svg>';

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
          + '</div>'
          // Ce que couvrent les chiffres. Les listes d'une periode montrent la
          // part de cette periode ; la fiche montre le dossier entier. Sans
          // cette ligne, ouvrir un dossier depuis la liste donne deux metrages
          // differents sans qu'on sache lequel repond a quelle question.
          + '<div class="rp-cr-portee">'
          + (cr.periode
              ? 'Chiffres du ' + escHtml(dateFr(cr.periode.debut))
                + (dateFr(cr.periode.fin) !== dateFr(cr.periode.debut)
                    ? ' au ' + escHtml(dateFr(cr.periode.fin)) : '')
              : 'Chiffres sur toute la vie du dossier')
          + '</div>';

    h += '<div class="rp-bloc"><div class="rp-kpis">'
       + kpi(fnum(m.reel) + ' m', "Métrage",
             m.prevu ? "prévu " + fnum(m.prevu) + " m" : (m.fiable ? "" : "non exploitable"))
       + kpi(vitesse(cr.vitesse_m_min), "Vitesse", "hors arrêts")
       + kpi(vitesse(cr.cadence_m_min), "Cadence", "arrêts compris")
       + kpi(minutesTxt(t.total_minutes), "Temps", (id.nb_saisies || 0) + " saisies")
       + kpi(escHtml((id.conducteurs || []).join(", ") || "—"), "Conducteurs", "")
       + '</div></div>';

    if ((t.categories || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Temps</div>'
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
    h += '<div class="rp-bloc"><div class="rp-titre">Info prod</div><div id="rp-ip-vue">'
       + (info
           ? renderEcrit(info, { no_dossier: cr.no_dossier })
           : '<div class="rp-manque">Aucune info prod enregistrée pour ce dossier.'
             + (id.cloture ? ' Elle est pourtant due à la clôture.'
                           : ' Le dossier n\'est pas encore clôturé.') + '</div>'
             + '<div class="rp-edit-actions"><button type="button" class="rp-btn-mini"'
             + ' id="rp-ip-edit">Renseigner</button></div>')
       + '</div>'
       + '<div id="rp-ip-form" style="display:none"><div class="rp-edit">'
       + '<textarea id="rp-ip-txt" placeholder="Ce qu\'il faut savoir pour la prochaine production de cette référence">'
       + escHtml(info ? info.texte : "") + '</textarea>'
       + '<div class="rp-edit-actions">'
       + '<button type="button" class="rp-btn-mini" id="rp-ip-annul">Annuler</button>'
       + '<button type="button" class="rp-btn-mini primaire" id="rp-ip-ok">Enregistrer</button>'
       + '</div></div></div></div>';

    if ((cr.seuils || []).length) {
      h += '<div class="rp-bloc"><div class="rp-titre">Seuils franchis</div>';
      cr.seuils.forEach(function (sx) {
        if (sx.explication_texte) {
          h += renderEcrit(sx, { no_dossier: cr.no_dossier });
          return;
        }
        var sid = sx.saisie_id;
        h += '<div class="rp-mot"><div class="m-txt" id="rp-sx-vue-' + sid + '">'
           + '<span class="rp-attente">Sans explication — à poser au point de production</span>'
           + '</div><div class="m-meta"><span class="m-tag">' + escHtml(sx.operation_code) + '</span>'
           + escHtml(sansCode(sx.operation, sx.operation_code)) + ' · '
           + escHtml(sx.duree_saisie_txt || "")
           + (sx.operateur ? ' · ' + escHtml(sx.operateur) : '') + '</div>'
           + '<div class="rp-edit-actions"><button type="button" class="rp-btn-mini" data-seuil="'
           + sid + '">Expliquer</button></div>'
           + '<div class="rp-edit" id="rp-sx-form-' + sid + '" style="display:none">'
           + '<textarea id="rp-sx-txt-' + sid + '" placeholder="Ce qui s\'est passé, et ce qui a été fait"></textarea>'
           + '<div class="rp-edit-actions">'
           + '<button type="button" class="rp-btn-mini" data-seuil-annul="' + sid + '">Annuler</button>'
           + '<button type="button" class="rp-btn-mini primaire" data-seuil-ok="' + sid + '">Enregistrer</button>'
           + '</div></div></div>';
      });
      h += '</div>';
    }

    var coms = (cr.ecrits || {}).commentaires || [];
    var notes = (cr.ecrits || {}).notes || [];
    h += '<div class="rp-bloc"><div class="rp-titre">Commentaires</div>';
    if (!coms.length && !notes.length) {
      h += '<div class="rp-manque">Aucun commentaire sur ce dossier.</div>';
    }
    coms.forEach(function (c) { h += renderEcrit(c, { no_dossier: cr.no_dossier }); });
    notes.forEach(function (n) { h += renderEcrit(n, { no_dossier: cr.no_dossier }); });
    h += '<div class="rp-edit-actions"><button type="button" class="rp-btn-mini"'
       + ' id="rp-note-add">Ajouter un commentaire</button></div>'
       + '<div class="rp-edit" id="rp-note-form" style="display:none">'
       + '<textarea id="rp-note-txt" placeholder="Votre commentaire sur ce dossier"></textarea>'
       + '<div class="rp-edit-actions">'
       + '<button type="button" class="rp-btn-mini" id="rp-note-annul">Annuler</button>'
       + '<button type="button" class="rp-btn-mini primaire" id="rp-note-ok">Enregistrer</button>'
       + '</div></div></div>';

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
    var fini = opts.onSaved || function () {};

    function agir(bouton, url, corps, silence) {
      bouton.disabled = true;
      return poster(url, corps)
        .then(function () { if (!silence) dire(silence || "Enregistré.", "info"); fini(); })
        .catch(function (err) { dire(err.message, "danger"); bouton.disabled = false; });
    }

    // ── Saisies : ouvrir la liste en grand, et la refermer.
    var plus = R.querySelector("#rp-sa-plus");
    var cadre = R.querySelector("#rp-sa-cadre");
    if (plus && cadre) {
      plus.onclick = function () {
        var ouvert = cadre.classList.toggle("ouvert");
        plus.classList.toggle("ouvert", ouvert);
        plus.setAttribute("aria-expanded", ouvert ? "true" : "false");
        plus.title = ouvert ? "Réduire la liste" : "Afficher plus de lignes";
        plus.setAttribute("aria-label", plus.title);
      };
    }

    // ── Saisies : filtre et tri.
    // On ne repeint QUE le corps du tableau, les entetes et le compteur : le
    // champ de recherche garde son curseur, ce qu'un rendu complet lui
    // retirerait a chaque lettre.
    var bloc = R.querySelector("#rp-saisies");
    if (bloc) {
      var repeindre = function () {
        var vues = filtrerTrier(_sa.liste, _sa);
        var corps = bloc.querySelector("#rp-sa-corps");
        if (corps) corps.innerHTML = _saLignes(vues);
        var nb = bloc.querySelector("#rp-sa-nb");
        if (nb) nb.textContent = _saCompte(_sa.liste.length, vues.length);
        var tete = bloc.querySelector("thead tr");
        if (tete) tete.innerHTML = _saEntetes();
        bloc.querySelectorAll("[data-sa-st]").forEach(function (b) {
          var on = !_sa.exclus[b.getAttribute("data-sa-st")];
          b.classList.toggle("actif", on);
          b.setAttribute("aria-pressed", on ? "true" : "false");
        });
      };
      bloc.addEventListener("input", function (ev) {
        if (ev.target.id !== "rp-sa-q") return;
        _sa.q = ev.target.value;
        repeindre();
      });
      bloc.addEventListener("click", function (ev) {
        var st = ev.target.closest ? ev.target.closest("[data-sa-st]") : null;
        if (st && bloc.contains(st)) {
          var cle = st.getAttribute("data-sa-st");
          if (_sa.exclus[cle]) delete _sa.exclus[cle]; else _sa.exclus[cle] = true;
          repeindre();
          return;
        }
        var tri = ev.target.closest ? ev.target.closest("[data-sa-tri]") : null;
        if (tri && bloc.contains(tri)) {
          var champ = tri.getAttribute("data-sa-tri");
          // Recliquer la meme colonne inverse le sens ; changer de colonne
          // repart du sens naturel de lecture.
          if (_sa.champ === champ) _sa.sens = _sa.sens === 1 ? -1 : 1;
          else { _sa.champ = champ; _sa.sens = 1; }
          repeindre();
        }
      });
    }

    // ── Info prod : saisie ou correction depuis le compte-rendu
    var edit = R.querySelector("#rp-ip-edit");
    if (edit) {
      edit.onclick = function () { ouvrirForm(R, "rp-ip-vue", "rp-ip-form", "rp-ip-txt"); };
      R.querySelector("#rp-ip-annul").onclick = function () {
        fermerForm(R, "rp-ip-vue", "rp-ip-form");
      };
      R.querySelector("#rp-ip-ok").onclick = function (e) {
        agir(e.target, "/api/rapports-prod/dossier/" + encodeURIComponent(no) + "/info-prod",
             { texte: R.querySelector("#rp-ip-txt").value }, "Info prod enregistrée.");
      };
    }

    // ── Seuils encore sans explication
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
        agir(e.target, "/api/rapports-prod/seuil/" + encodeURIComponent(sid) + "/explication",
             { texte: txt }, "Explication enregistrée.");
      };
    });

    // ── Les trois gestes sur une remontee ────────────────────────
    // Chaque bouton porte son dossier : la feuille atelier melange plusieurs
    // dossiers, il n'y a pas de « dossier courant » sur lequel se rabattre.
    Array.prototype.forEach.call(R.querySelectorAll("[data-valider]"), function (b) {
      b.onclick = function (e) {
        agir(e.target, "/api/rapports-prod/ecrit/valider", {
          cle: b.getAttribute("data-valider"),
          no_dossier: b.getAttribute("data-dossier") || no || "",
          valide: b.getAttribute("data-etat") !== "1"
        }, b.getAttribute("data-etat") === "1" ? "Remis à traiter." : "Marqué comme traité.");
      };
    });

    Array.prototype.forEach.call(R.querySelectorAll("[data-masquer]"), function (b) {
      b.onclick = function (e) {
        agir(e.target, "/api/rapports-prod/ecrit/masquer", {
          cle: b.getAttribute("data-masquer"),
          no_dossier: b.getAttribute("data-dossier") || no || "",
          masque: b.getAttribute("data-etat") !== "1"
        }, b.getAttribute("data-etat") === "1" ? "Remis dans la liste." : "Masqué.");
      };
    });

    // Bascule de la liste des remontees masquees. Purement local : rien a
    // enregistrer, c'est un geste de consultation.
    var btnMasques = R.querySelector("#rp-masques-btn");
    if (btnMasques) {
      btnMasques.onclick = function () {
        var boite = R.querySelector("#rp-masques");
        if (!boite) return;
        var ouvert = boite.style.display !== "none";
        boite.style.display = ouvert ? "none" : "";
        btnMasques.classList.toggle("primaire", !ouvert);
      };
    }

    Array.prototype.forEach.call(R.querySelectorAll("[data-modif]"), function (b) {
      var id = slug(b.getAttribute("data-modif"));
      b.onclick = function () { ouvrirForm(R, "rp-e-vue-" + id, "rp-e-form-" + id, "rp-e-txt-" + id); };
    });
    Array.prototype.forEach.call(R.querySelectorAll("[data-commenter]"), function (b) {
      var id = slug(b.getAttribute("data-commenter"));
      b.onclick = function () { ouvrirForm(R, "rp-e-vue-" + id, "rp-e-com-" + id, "rp-e-comtxt-" + id); };
    });
    Array.prototype.forEach.call(R.querySelectorAll("[data-annul]"), function (b) {
      var id = b.getAttribute("data-annul"), quoi = b.getAttribute("data-quoi");
      b.onclick = function () {
        fermerForm(R, "rp-e-vue-" + id, "rp-e-" + (quoi === "com" ? "com-" : "form-") + id);
      };
    });

    // Corriger le texte : la destination depend de la source de la remontee.
    Array.prototype.forEach.call(R.querySelectorAll("[data-modif-ok]"), function (b) {
      b.onclick = function (e) {
        var id = slug(b.getAttribute("data-modif-ok"));
        var origine = b.getAttribute("data-origine");
        var ref = b.getAttribute("data-ref");
        var dossier = b.getAttribute("data-dossier") || no || "";
        var txt = R.querySelector("#rp-e-txt-" + id).value;
        var url = null;
        if (origine === "commentaire") {
          url = "/api/rapports-prod/saisie/" + encodeURIComponent(ref) + "/commentaire";
        } else if (origine === "info_prod") {
          url = "/api/rapports-prod/dossier/" + encodeURIComponent(dossier) + "/info-prod";
        } else if (origine === "arret") {
          url = "/api/rapports-prod/seuil/" + encodeURIComponent(ref) + "/explication";
          if (!txt.trim()) { dire("Explication vide.", "danger"); return; }
        } else if (origine === "note") {
          url = "/api/rapports-prod/note/" + encodeURIComponent(ref);
        }
        if (!url) { dire("Cette remontée ne se corrige pas ici.", "danger"); return; }
        agir(e.target, url, { texte: txt }, "Enregistré.");
      };
    });

    // Repondre a une remontee : une note rattachee a sa cle.
    Array.prototype.forEach.call(R.querySelectorAll("[data-com-ok]"), function (b) {
      b.onclick = function (e) {
        var id = slug(b.getAttribute("data-com-ok"));
        var dossier = b.getAttribute("data-dossier") || no || "";
        var txt = (R.querySelector("#rp-e-comtxt-" + id).value || "").trim();
        if (!txt) { dire("Commentaire vide.", "danger"); return; }
        agir(e.target, "/api/rapports-prod/dossier/" + encodeURIComponent(dossier) + "/note",
             { texte: txt, cle_reponse: b.getAttribute("data-com-ok") }, "Commentaire ajouté.");
      };
    });

    // ── Commentaire libre sur le dossier
    var ajout = R.querySelector("#rp-note-add");
    if (ajout) {
      ajout.onclick = function () {
        ouvrirForm(R, "rp-note-add", "rp-note-form", "rp-note-txt");
        ajout.style.display = "none";
      };
      R.querySelector("#rp-note-annul").onclick = function () {
        R.querySelector("#rp-note-form").style.display = "none";
        ajout.style.display = "";
      };
      R.querySelector("#rp-note-ok").onclick = function (e) {
        var txt = (R.querySelector("#rp-note-txt").value || "").trim();
        if (!txt) { dire("Commentaire vide.", "danger"); return; }
        agir(e.target, "/api/rapports-prod/dossier/" + encodeURIComponent(no) + "/note",
             { texte: txt }, "Commentaire ajouté.");
      };
    }
  }

  global.MySifaRetourProd = {
    escHtml: escHtml, escAttr: escAttr,
    fnum: fnum, minutesTxt: minutesTxt, ecartHtml: ecartHtml, dateFr: dateFr,
    kpi: kpi, vitesse: vitesse, sansCode: sansCode,
    LIB_ORIGINE: LIB_ORIGINE, LIB_VIGILANCE: LIB_VIGILANCE,
    renderFeuille: renderFeuille, filtrerTrier: filtrerTrier,
    renderListe: renderListe,
    renderRecherche: renderRecherche,
    renderFrise: renderFrise,
    brancherFrise: brancherFrise,
    renderCR: renderCR,
    renderEcrit: renderEcrit,
    slug: slug,
    brancher: brancher
  };
})(window);
