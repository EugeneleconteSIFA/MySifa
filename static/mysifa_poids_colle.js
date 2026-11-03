/*
 * MySifa — Saisie prod : widget « Poids de colle » (bouton du dock).
 *
 * Grammage d'adhésif à partir d'une pesée d'étiquettes décollées, comme le
 * classeur « application excel calcul de poids adhésif » de l'atelier :
 *
 *   surface (mm²)  = laize × hauteur − 4 × (r² − π r² / 4)    rectangle
 *                  = π × (Ø / 2)²                             ronde
 *   théorique (g)  = surface × n × (frontal + encre × couverture) / 10⁶
 *   adhésif (g/m²) = (pesé − théorique) / (surface × n) × 10⁶
 *
 * Le format, le rayon des coins, le papier et l'anilox viennent du dossier en
 * cours et de sa fiche technique (GET /api/fabrication/poids-colle,
 * app/services/poids_colle.py) ; tout reste modifiable. Les grammages sont le
 * référentiel des épaisseurs matière, éditable ici par les administrateurs
 * matières (PUT /api/stock/metrage-epaisseurs, perimetre « grammage »).
 *
 * La page hôte dit quel dossier est en cours :
 *   window.mysifaPoidsColleContexte = () => ({no_dossier, machine})
 * Monté par MySifaPoidsColle.monter(). Tout texte passe par textContent.
 */
(function (global) {
  "use strict";

  // Un poids de balance : le widget part d'une pesée.
  var ICO = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="5" r="3"/><path d="M6.5 8a2 2 0 0 0-1.9 1.46L2.1 18.5A2 2 0 0 0 4 21h16a2 2 0 0 0 1.92-2.54L19.4 9.5A2 2 0 0 0 17.5 8z"/></svg>';
  var LS = "mysifa_poids_colle_v1";
  var W = { open: false, data: null, charge: false, edit: false, erreur: "", saisie: null };

  // ── Calcul ─────────────────────────────────────────────────────────────
  function nb(v) {
    var x = parseFloat(String(v == null ? "" : v).replace(",", "."));
    return isFinite(x) ? x : NaN;
  }
  function surface(s) {
    if (s.forme === "ronde") {
      var d = nb(s.diametre);
      return d > 0 ? Math.PI * (d / 2) * (d / 2) : NaN;
    }
    var l = nb(s.laize), h = nb(s.hauteur), r = nb(s.rayon);
    if (!(l > 0) || !(h > 0)) return NaN;
    if (!(r > 0)) r = 0;
    if (2 * r > Math.min(l, h)) return NaN;
    return l * h - 4 * (r * r - Math.PI * r * r / 4);
  }
  function calcul(s) {
    var S2 = surface(s), n = nb(s.nombre), p = nb(s.pese), f = nb(s.frontal);
    var enc = nb(s.encre), cov = nb(s.couverture);
    var encre = (enc > 0 && cov > 0) ? enc * cov / 100 : 0;
    if (!(S2 > 0)) return { manque: "Format incomplet ou rayon trop grand pour le format." };
    if (!(n >= 1)) return { manque: "Nombre d'étiquettes pesées." };
    if (!(f > 0)) return { manque: "Grammage du papier." };
    var theorique = S2 * n * (f + encre) / 1e6;
    if (!(p > 0)) return { surface: S2, theorique: theorique, manque: "Poids pesé." };
    return { surface: S2, theorique: theorique, adhesif: (p - theorique) / (S2 * n) * 1e6 };
  }

  // ── Outils DOM ─────────────────────────────────────────────────────────
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function fmt(v, d) {
    return isFinite(v) ? Number(v).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }) : "—";
  }
  function champ(lib, input, unite) {
    var c = el("label", "pc-champ");
    c.appendChild(el("span", "pc-lib", lib + (unite ? " (" + unite + ")" : "")));
    c.appendChild(input);
    return c;
  }
  function nombre(val, ph, onInput) {
    var i = el("input");
    i.type = "text";
    i.inputMode = "decimal";
    i.placeholder = ph || "";
    i.value = val == null ? "" : String(val);
    i.addEventListener("input", function () { onInput(i.value); });
    return i;
  }
  function lireLS() { try { return JSON.parse(localStorage.getItem(LS) || "null"); } catch (e) { return null; } }
  function ecrireLS() { try { localStorage.setItem(LS, JSON.stringify(W.saisie)); } catch (e) {} }
  function contexte() {
    try { return (global.mysifaPoidsColleContexte && global.mysifaPoidsColleContexte()) || {}; } catch (e) { return {}; }
  }
  function ref() { return (W.data && W.data.referentiel) || []; }
  function ligne(id) { return ref().filter(function (l) { return String(l.id) === String(id); })[0] || null; }
  function famille(code) { return ref().filter(function (l) { return l.famille === code; }); }

  // ── Saisie initiale : dossier en cours, sinon la dernière saisie ──────
  function depuisDossier(d) {
    var s = { dossier: d.no_dossier || "", forme: "rectangle", laize: "", hauteur: "", rayon: "", diametre: "",
              papier: "", frontal: "", anilox: "", encre: "", couverture: "0", nombre: "1", pese: "" };
    var f = d.format;
    if (f) {
      s.forme = f.forme;
      s.laize = f.laize != null ? f.laize : "";
      s.hauteur = f.hauteur != null ? f.hauteur : "";
      s.rayon = f.rayon != null ? f.rayon : "";
      s.diametre = f.diametre != null ? f.diametre : "";
    }
    var pc = d.papier && d.papier.choix ? ligne(d.papier.choix) : null;
    if (pc) { s.papier = String(pc.id); s.frontal = pc.grammage_gsm; }
    var an = (d.anilox || []).filter(function (a) { return a.choix; })[0];
    var al = an ? ligne(an.choix) : null;
    if (al) { s.anilox = String(al.id); s.encre = al.grammage_gsm; }
    return s;
  }

  async function charger(force) {
    var c = contexte();
    W.charge = true; W.erreur = "";
    rendre();
    try {
      var r = await fetch("/api/fabrication/poids-colle?no_dossier=" + encodeURIComponent(c.no_dossier || ""),
                          { credentials: "include", cache: "no-store" });
      if (!r.ok) throw new Error("Lecture impossible (" + r.status + ").");
      W.data = await r.json();
    } catch (e) {
      W.erreur = e.message || "Lecture impossible.";
      W.data = W.data || { referentiel: [], familles: [], dossier: {}, peut_modifier: false };
    }
    W.charge = false;
    var d = W.data.dossier || {};
    var mem = lireLS();
    if (force || !mem || (d.no_dossier || "") !== (mem.dossier || "")) {
      // Nouveau dossier : ses valeurs. Le nombre d'étiquettes pesées suit
      // l'habitude du poste, pas le dossier.
      W.saisie = depuisDossier(d);
      if (mem && mem.nombre) W.saisie.nombre = mem.nombre;
      ecrireLS();
    } else {
      W.saisie = mem;
    }
    rendre();
  }

  // ── Rendu ──────────────────────────────────────────────────────────────
  function selectMatiere(code, valeur, proposes, onChange) {
    var sel = el("select");
    sel.appendChild(new Option("Saisie libre", ""));
    var lignes = famille(code);
    var prop = lignes.filter(function (l) { return proposes.indexOf(l.id) >= 0; });
    var autres = lignes.filter(function (l) { return proposes.indexOf(l.id) < 0; });
    function opt(l) { return new Option(l.libelle + " — " + fmt(l.grammage_gsm, 1) + " g/m²", String(l.id)); }
    if (prop.length) {
      var g1 = document.createElement("optgroup");
      g1.label = "Proposé par la fiche";
      prop.forEach(function (l) { g1.appendChild(opt(l)); });
      sel.appendChild(g1);
      var g2 = document.createElement("optgroup");
      g2.label = "Autres";
      autres.forEach(function (l) { g2.appendChild(opt(l)); });
      sel.appendChild(g2);
    } else {
      autres.forEach(function (l) { sel.appendChild(opt(l)); });
    }
    sel.value = valeur || "";
    sel.addEventListener("change", function () { onChange(sel.value); });
    return sel;
  }

  function rendreCalcul(body) {
    var s = W.saisie, d = (W.data && W.data.dossier) || {}, ctx = contexte();
    var maj = function () { ecrireLS(); afficherResultat(); };

    var tete = el("div", "pc-dossier");
    if (d.no_dossier) {
      tete.appendChild(el("strong", null, "Dossier " + d.no_dossier));
      tete.appendChild(el("span", null, d.fiche ? " · fiche " + d.fiche.reference : " · pas de fiche technique"));
    } else {
      tete.appendChild(el("span", null, ctx.no_dossier ? "Dossier " + ctx.no_dossier + " introuvable au planning" : "Aucun dossier en cours — saisie libre"));
    }
    var recharger = el("button", "pc-lien", "Reprendre le dossier");
    recharger.type = "button";
    recharger.title = "Remettre le format et les matières du dossier en cours";
    recharger.addEventListener("click", function () { charger(true); });
    tete.appendChild(recharger);
    body.appendChild(tete);

    // Forme
    var formes = el("div", "pc-seg");
    [["rectangle", "Rectangle"], ["ronde", "Ronde"]].forEach(function (f) {
      var b = el("button", s.forme === f[0] ? "on" : "", f[1]);
      b.type = "button";
      b.addEventListener("click", function () { s.forme = f[0]; ecrireLS(); rendre(); });
      formes.appendChild(b);
    });
    body.appendChild(formes);
    var dims = el("div", "pc-ligne");
    if (s.forme === "ronde") {
      dims.appendChild(champ("Diamètre", nombre(s.diametre, "50", function (v) { s.diametre = v; maj(); }), "mm"));
    } else {
      dims.appendChild(champ("Laize", nombre(s.laize, "148", function (v) { s.laize = v; maj(); }), "mm"));
      dims.appendChild(champ("Hauteur", nombre(s.hauteur, "210", function (v) { s.hauteur = v; maj(); }), "mm"));
      dims.appendChild(champ("Rayon", nombre(s.rayon, "6", function (v) { s.rayon = v; maj(); }), "mm"));
    }
    body.appendChild(dims);
    if (d.format && d.format.texte) body.appendChild(el("div", "pc-aide", "Fiche : " + d.format.texte + (d.format.source === "dossier" ? " · dimensions du dossier" : "")));

    // Papier
    var inpF = nombre(s.frontal, "70", function (v) {
      s.frontal = v;
      var l = ligne(s.papier);
      if (l && nb(v) !== l.grammage_gsm) { s.papier = ""; selP.value = ""; }
      maj();
    });
    var selP = selectMatiere("frontal", s.papier, (d.papier && d.papier.candidats) || [], function (v) {
      s.papier = v;
      var l = ligne(v);
      if (l) { s.frontal = l.grammage_gsm; inpF.value = String(l.grammage_gsm); }
      maj();
    });
    var pap = el("div", "pc-ligne pc-matiere");
    pap.appendChild(champ("Papier", selP));
    pap.appendChild(champ("Grammage", inpF, "g/m²"));
    body.appendChild(pap);
    if (d.papier) {
      var txt = "Fiche : " + d.papier.texte;
      if (!d.papier.choix) txt += (d.papier.candidats || []).length > 1 ? " — plusieurs papiers possibles, à choisir" : " — absent du référentiel, saisir le grammage";
      body.appendChild(el("div", "pc-aide", txt));
    }
    if (d.glassine) body.appendChild(el("div", "pc-aide", "Glassine : " + d.glassine.texte + " — non comptée, l'étiquette se pèse décollée."));

    // Encre
    var inpE = nombre(s.encre, "2", function (v) {
      s.encre = v;
      var l = ligne(s.anilox);
      if (l && nb(v) !== l.grammage_gsm) { s.anilox = ""; selA.value = ""; }
      maj();
    });
    var selA = el("select");
    selA.appendChild(new Option("Sans encre / libre", ""));
    famille("anilox").forEach(function (l) { selA.appendChild(new Option(l.libelle + " — " + fmt(l.grammage_gsm, 1) + " g/m²", String(l.id))); });
    selA.value = s.anilox || "";
    selA.addEventListener("change", function () {
      s.anilox = selA.value;
      var l = ligne(selA.value);
      s.encre = l ? l.grammage_gsm : "";
      inpE.value = String(s.encre);
      maj();
    });
    var enc = el("div", "pc-ligne pc-matiere");
    enc.appendChild(champ("Anilox", selA));
    enc.appendChild(champ("Encre", inpE, "g/m²"));
    enc.appendChild(champ("Couverture", nombre(s.couverture, "0", function (v) { s.couverture = v; maj(); }), "%"));
    body.appendChild(enc);
    if ((d.anilox || []).length) {
      body.appendChild(el("div", "pc-aide", "Fiche : " + d.anilox.map(function (a) { return "tête " + a.tete + " " + a.texte; }).join(" · ")));
    }

    // Pesée
    var pes = el("div", "pc-ligne");
    pes.appendChild(champ("Étiquettes pesées", nombre(s.nombre, "1", function (v) { s.nombre = v; maj(); })));
    var inpP = nombre(s.pese, "3,043", function (v) { s.pese = v; maj(); });
    pes.appendChild(champ("Poids pesé", inpP, "g"));
    body.appendChild(pes);

    var res = el("div", "pc-res pc-vide");
    var val = el("div", "pc-res-val", "—");
    var lib = el("div", "pc-res-lbl", "g/m² d'adhésif");
    var det = el("div", "pc-res-det");
    res.append(val, lib, det);
    body.appendChild(res);
    function afficherResultat() {
      var r = calcul(s);
      det.textContent = r.surface ? "Surface " + fmt(r.surface, 0) + " mm² · sans colle " + fmt(r.theorique, 3) + " g" : "";
      if (r.adhesif != null) {
        val.textContent = fmt(r.adhesif, 1);
        lib.textContent = "g/m² d'adhésif";
        res.classList.remove("pc-vide");
        res.classList.toggle("pc-neg", r.adhesif < 0);
        if (r.adhesif < 0) lib.textContent = "négatif : poids pesé ou grammage du papier à revoir";
      } else {
        val.textContent = "—";
        lib.textContent = "Manque : " + r.manque;
        res.classList.add("pc-vide");
        res.classList.remove("pc-neg");
      }
    }
    afficherResultat();

    body.appendChild(el("div", "pc-aide", "Valeurs de grammage indicatives : le poids du frontal se prend sur chaque bobine et s'annote dessus."));
    var liens = el("div", "pc-liens");
    if (global.MySifaPesees) {
      var h = el("button", "pc-lien", "Historique des pesées par front");
      h.type = "button";
      h.addEventListener("click", function () {
        global.MySifaPesees.ouvrir({ machine: ctx.machine || "", no_dossier: "" });
      });
      liens.appendChild(h);
    }
    if (W.data && W.data.peut_modifier) {
      var g = el("button", "pc-lien", "Gérer les grammages");
      g.type = "button";
      g.addEventListener("click", function () { W.edit = true; rendre(); });
      liens.appendChild(g);
    }
    body.appendChild(liens);
  }

  function rendreEdition(body) {
    var familles = (W.data && W.data.familles || []).filter(function (f) { return f.code !== "complexe"; });
    var lignes = ref().map(function (l) { return { id: l.id, libelle: l.libelle, famille: l.famille || "frontal", grammage_gsm: l.grammage_gsm }; });
    var liste = el("div", "pc-edit");
    var err = el("div", "pc-err");
    function dessiner() {
      liste.textContent = "";
      lignes.forEach(function (l, i) {
        var r = el("div", "pc-edit-ligne");
        var lib = el("input", "pc-edit-lib");
        lib.maxLength = 80;
        lib.placeholder = "Matière";
        lib.value = l.libelle;
        lib.addEventListener("input", function () { l.libelle = lib.value; });
        var fam = el("select", "pc-edit-fam");
        familles.forEach(function (f) { fam.appendChild(new Option(f.libelle, f.code)); });
        fam.value = l.famille;
        fam.addEventListener("change", function () { l.famille = fam.value; });
        var g = nombre(l.grammage_gsm, "g/m²", function (v) { l.grammage_gsm = v; });
        g.className = "pc-edit-g";
        var x = el("button", "pc-edit-x", "×");
        x.type = "button";
        x.title = "Retirer";
        x.addEventListener("click", function () { lignes.splice(i, 1); dessiner(); });
        r.append(lib, fam, g, x);
        liste.appendChild(r);
      });
    }
    dessiner();
    var ajout = el("button", "pc-lien", "+ Ajouter une matière");
    ajout.type = "button";
    ajout.addEventListener("click", function () { lignes.push({ libelle: "", famille: "frontal", grammage_gsm: "" }); dessiner(); });
    var annuler = el("button", "pc-btn", "Annuler");
    annuler.type = "button";
    annuler.addEventListener("click", function () { W.edit = false; rendre(); });
    var ok = el("button", "pc-btn pc-btn-accent", "Enregistrer");
    ok.type = "button";
    ok.addEventListener("click", async function () {
      err.textContent = "";
      var items = lignes.map(function (l) {
        return { id: l.id, libelle: String(l.libelle || "").trim(), famille: l.famille,
                 grammage_gsm: String(l.grammage_gsm == null ? "" : l.grammage_gsm).replace(",", ".") };
      }).filter(function (l) { return l.libelle || l.grammage_gsm; });
      ok.disabled = true;
      try {
        var r = await fetch("/api/stock/metrage-epaisseurs", {
          method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ perimetre: "grammage", items: items }),
        });
        var d = await r.json().catch(function () { return {}; });
        if (!r.ok) throw new Error((d && d.detail) || "Enregistrement impossible.");
        W.data.referentiel = (Array.isArray(d) ? d : []).filter(function (l) { return l.grammage_gsm != null; });
        W.edit = false;
        if (typeof global.showToast === "function") global.showToast("Grammages enregistrés.", "success");
        rendre();
      } catch (e) {
        err.textContent = e.message || "Enregistrement impossible.";
        ok.disabled = false;
      }
    });
    var actions = el("div", "pc-edit-actions");
    actions.append(annuler, ok);
    body.append(el("div", "pc-aide", "Grammages types en g/m². Anilox : dépôt d'encre d'un aplat à 100 %. Les épaisseurs (Métrage bobine) ne sont pas touchées."),
                liste, ajout, err, actions);
  }

  function rendre() {
    var panel = document.getElementById("pc-panel");
    if (!panel) return;
    panel.textContent = "";
    var head = el("div", "mysifa-dock-panel-head");
    head.appendChild(el("span", "mysifa-dock-panel-title", W.edit ? "Grammages matière" : "Poids de colle"));
    var x = el("button", "mysifa-dock-panel-close", "×");
    x.type = "button";
    x.setAttribute("aria-label", "Fermer");
    x.addEventListener("click", function () { ouvrir(false); });
    head.appendChild(x);
    panel.appendChild(head);
    var body = el("div", "pc-body");
    panel.appendChild(body);
    if (W.erreur) body.appendChild(el("div", "pc-err", W.erreur));
    if (!W.saisie) { body.appendChild(el("div", "pc-aide", "Chargement…")); return; }
    if (W.edit) rendreEdition(body); else rendreCalcul(body);
  }

  function ouvrir(v) {
    W.open = !!v;
    var panel = document.getElementById("pc-panel");
    if (panel) panel.style.display = W.open ? "" : "none";
    if (W.open) { W.edit = false; charger(false); }
    if (global.MySifaDock && typeof global.MySifaDock.layout === "function") global.MySifaDock.layout();
  }

  function monter() {
    if (document.getElementById("pc-fab")) return;
    var fab = el("button", "mysifa-dock-fab mysifa-dock-extra");
    fab.id = "pc-fab";
    fab.type = "button";
    fab.setAttribute("data-dock-panel", "pc-panel");
    fab.title = "Poids de colle";
    fab.setAttribute("aria-label", "Poids de colle");
    fab.innerHTML = ICO;  // SVG constant, aucune donnée
    fab.addEventListener("click", function () { ouvrir(!W.open); });
    document.body.appendChild(fab);
    var panel = el("div", "mysifa-dock-panel pc-panel");
    panel.id = "pc-panel";
    panel.style.display = "none";
    document.body.appendChild(panel);
    document.addEventListener("keydown", function (e) {
      if (W.open && e.key === "Escape" && !document.getElementById("pf-overlay")) ouvrir(false);
    });
    if (global.MySifaDock && typeof global.MySifaDock.layout === "function") global.MySifaDock.layout();
  }

  global.MySifaPoidsColle = { monter: monter, ouvrir: ouvrir, _calcul: calcul, _surface: surface };
})(window);
