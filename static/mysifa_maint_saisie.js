/*
 * MySifa — Saisie prod, onglet Qualité › Opérations de maintenance :
 * enregistrer une intervention déjà réalisée, sans quitter la saisie.
 *
 * Même circuit que « Enregistrer une opération » de MyMaintenance
 * (opSubmitNew / adminSubmitRegisterOp de app/web/maintenance_page.py) :
 *   1. « Autre maintenance » : POST /api/maintenance/codes/libres {label}
 *      → code LIB-xxx (réutilisé si le titre existe déjà) ;
 *   2. POST /api/maintenance/events  {machine, date_prevue, source:
 *      'non_planifie', ops:[code]} → créneau non planifié, une opération ;
 *   3. PATCH …/ops/{id} {statut:'termine', duree_reelle_min, observations,
 *      done_at} → l'opération est soldée ; si ce PATCH échoue, le créneau est
 *      supprimé (pas de créneau « non planifié » jamais soldé).
 * L'opération apparaît donc dans MyMaintenance (historique des opérations,
 * statuts machine, interventions non programmées) comme si elle y avait été
 * saisie. Seules les Interventions du catalogue sont proposées
 * (catégorie « remplacements ») ; contrôles et nettoyages restent dans
 * MyMaintenance.
 *
 * Interventions et machines se choisissent en pastilles (écran tactile de
 * l'atelier). Les opérations récentes de la machine sont relues dans
 * GET /api/maintenance/history, la source de l'écran Historique.
 *
 *   MySifaMaintSaisie.vue({machine, machines, role})   élément durable à
 *       poser dans la page ; les appels suivants rendent le même élément
 *       (saisie en cours conservée). Machine : celle de l'opérateur.
 * Tout texte passe par textContent.
 */
(function (global) {
  "use strict";

  var AUTRE = "__autre__";
  var JOURS_HISTO = 30, LIGNES_HISTO = 8;
  var DUREES = [15, 30, 60, 120];
  var SVG = "http://www.w3.org/2000/svg";
  var ICONES = {
    outil: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    fleche: '<path d="M7 17 17 7M8 7h9v9"/>',
  };
  var M = { el: null, codes: null, histo: null, machine: "", machines: [], role: "", refus: false,
            envoi: false, erreur: "", code: "", form: null };

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function icone(nom, taille) {
    var s = document.createElementNS(SVG, "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("width", taille || 16);
    s.setAttribute("height", taille || 16);
    s.setAttribute("fill", "none");
    s.setAttribute("stroke", "currentColor");
    s.setAttribute("stroke-width", "2");
    s.setAttribute("stroke-linecap", "round");
    s.setAttribute("stroke-linejoin", "round");
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = ICONES[nom];  // tracé constant, aucune donnée
    return s;
  }
  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function isoJour(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function jourLisible(iso) {
    var s = String(iso || "");
    if (s.length < 10) return s;
    var auj = isoJour(new Date()), hier = new Date();
    hier.setDate(hier.getDate() - 1);
    var j = s.slice(0, 10);
    var lib = j === auj ? "Aujourd'hui" : j === isoJour(hier) ? "Hier" : s.slice(8, 10) + "/" + s.slice(5, 7);
    return lib + (s.length >= 16 ? " · " + s.slice(11, 16) : "");
  }
  function toast(msg, type) {
    if (typeof global.showToast === "function") global.showToast(msg, type || "success");
  }
  async function appel(url, opt) {
    opt = opt || {};
    var r = await fetch(url, {
      method: opt.method || "GET", credentials: "include", cache: "no-store",
      headers: opt.body ? { "Content-Type": "application/json" } : undefined,
      body: opt.body ? JSON.stringify(opt.body) : undefined,
    });
    var d = await r.json().catch(function () { return {}; });
    if (!r.ok) {
      var e = new Error((d && d.detail) || ("Erreur " + r.status + "."));
      e.status = r.status;
      throw e;
    }
    return d;
  }
  // Date choisie + heure du moment, comme _toDoneAtIso de MyMaintenance.
  function doneAt(jour) {
    var n = new Date();
    return jour + "T" + pad(n.getHours()) + ":" + pad(n.getMinutes()) + ":" + pad(n.getSeconds());
  }

  // ── Données ────────────────────────────────────────────────────────────
  async function chargerCodes() {
    try {
      var d = await appel("/api/maintenance/codes");
      M.codes = (d.items || [])
        .filter(function (c) { return c.categorie === "remplacements" && !c.libre && !c.archived; })
        .sort(function (a, b) { return String(a.label).localeCompare(String(b.label), "fr"); });
    } catch (e) {
      M.codes = [];
      M.erreur = e.message;
    }
    rendre();
  }
  async function chargerHisto() {
    if (!M.machine) { M.histo = []; rendre(); return; }
    var du = new Date();
    du.setDate(du.getDate() - JOURS_HISTO);
    try {
      var d = await appel("/api/maintenance/history?machine=" + encodeURIComponent(M.machine) + "&date_from=" + isoJour(du));
      // Le filtre machine du serveur est un LIKE : « Cohésio 1 » ramènerait
      // « Cohésio 10 ». On garde les opérations qui portent la machine.
      M.histo = (d.history || []).filter(function (h) {
        return (h.machines || []).indexOf(M.machine) >= 0 || h.machine === M.machine;
      });
    } catch (e) {
      if (e.status === 403) M.refus = true;
      M.histo = [];
    }
    rendre();
  }

  // ── Enregistrement ─────────────────────────────────────────────────────
  async function enregistrer() {
    var f = M.form;
    var autre = M.code === AUTRE;
    var titre = f.titre.value.trim(), jour = f.date.value, machine = M.machine;
    var dureeTxt = f.duree.value.trim(), comment = f.comment.value.trim();
    var duree = dureeTxt === "" ? null : Number(dureeTxt.replace(",", "."));
    if (!M.code) return erreur("Choisissez une intervention.");
    if (autre && !titre) return erreur("Décrivez l'intervention.");
    if (!machine) return erreur("Choisissez une machine.");
    if (!jour) return erreur("Date obligatoire.");
    if (jour > isoJour(new Date())) return erreur("Une opération réalisée ne peut pas être datée dans le futur.");
    if (duree != null && (!isFinite(duree) || duree < 0 || Math.round(duree) !== duree)) {
      return erreur("Durée invalide — nombre entier de minutes.");
    }
    M.envoi = true; M.erreur = "";
    rendre();
    var ev = null;
    try {
      var code = M.code;
      if (autre) code = (await appel("/api/maintenance/codes/libres", { method: "POST", body: { label: titre } })).code;
      var d = await appel("/api/maintenance/events", { method: "POST", body: {
        machine: machine, date_prevue: jour, source: "non_planifie", ops: [code], operators: [] } });
      ev = d.event;
      var op = ev && (ev.ops || [])[0];
      if (!op) throw new Error("Opération absente de la réponse.");
      var corps = { statut: "termine", done_at: doneAt(jour) };
      if (duree != null) corps.duree_reelle_min = duree;
      if (comment) corps.observations = comment;
      await appel("/api/maintenance/events/" + ev.id + "/ops/" + op.id, { method: "PATCH", body: corps });
      ev = null;
      M.code = "";
      f.titre.value = ""; f.duree.value = ""; f.comment.value = "";
      f.date.value = isoJour(new Date());
      toast("Opération enregistrée.");
      chargerHisto();
    } catch (e) {
      // Créneau créé mais pas soldé : on le retire, comme MyMaintenance.
      if (ev && ev.id) { try { await appel("/api/maintenance/events/" + ev.id, { method: "DELETE" }); } catch (x) {} }
      M.erreur = e.status === 403 ? "Enregistrement réservé à l'atelier et aux responsables maintenance." : e.message;
      toast(M.erreur, "danger");
    }
    M.envoi = false;
    rendre();
  }
  function erreur(msg) {
    M.erreur = msg;
    rendre();
    toast(msg, "danger");
  }

  // ── Rendu ──────────────────────────────────────────────────────────────
  function pastille(texte, actif, onClick, cls) {
    var b = el("button", "mm-pastille" + (cls ? " " + cls : "") + (actif ? " actif" : ""));
    b.type = "button";
    b.setAttribute("aria-pressed", actif ? "true" : "false");
    if (actif) b.appendChild(icone("check", 14));
    b.appendChild(document.createTextNode(texte));
    b.addEventListener("click", onClick);
    return b;
  }
  function etape(num, titre) {
    var t = el("div", "mm-etape");
    t.appendChild(el("span", "mm-etape-num", String(num)));
    t.appendChild(el("span", null, titre));
    return t;
  }

  // Champs texte construits une fois : la saisie en cours survit aux rendus.
  // Pastilles et liste sont redessinées à chaque rendu.
  function construireForm() {
    var f = {};
    f.titre = el("input", "mm-input");
    f.titre.type = "text";
    f.titre.maxLength = 200;
    f.titre.placeholder = "Décrivez l'intervention — ex. : remplacement joint pompe hydraulique";
    f.date = el("input", "mm-input");
    f.date.type = "date";
    f.date.value = isoJour(new Date());
    f.date.max = isoJour(new Date());
    f.duree = el("input", "mm-input mm-duree");
    f.duree.type = "number";
    f.duree.min = "0";
    f.duree.step = "1";
    f.duree.placeholder = "—";
    f.duree.inputMode = "numeric";
    f.duree.addEventListener("input", rendre);
    f.comment = el("textarea", "mm-input");
    f.comment.rows = 2;
    f.comment.placeholder = "Pièces changées, observations…";
    f.envoyer = el("button", "mm-btn");
    f.envoyer.type = "button";
    f.envoyer.addEventListener("click", enregistrer);
    // Zones redessinées
    f.codes = el("div", "mm-pastilles");
    f.machines = el("div", "mm-pastilles");
    f.durees = el("div", "mm-pastilles mm-pastilles-duree");
    f.etat = el("div", "mm-etat");

    var form = el("div", "mm-carte mm-form");
    form.appendChild(etape(1, "Intervention réalisée"));
    form.appendChild(f.codes);
    f.titreBloc = el("div", "mm-titre-libre");
    f.titreBloc.appendChild(f.titre);
    form.appendChild(f.titreBloc);

    form.appendChild(etape(2, "Machine et date"));
    var ligne = el("div", "mm-ligne");
    ligne.appendChild(f.machines);
    var dateBloc = el("label", "mm-champ");
    dateBloc.appendChild(el("span", "mm-lib", "Date"));
    dateBloc.appendChild(f.date);
    ligne.appendChild(dateBloc);
    form.appendChild(ligne);

    form.appendChild(etape(3, "Détails (facultatif)"));
    var details = el("div", "mm-ligne");
    var dureeBloc = el("div", "mm-champ");
    dureeBloc.appendChild(el("span", "mm-lib", "Durée"));
    var dureeLigne = el("div", "mm-duree-ligne");
    dureeLigne.appendChild(f.durees);
    var unite = el("label", "mm-unite");
    unite.appendChild(f.duree);
    unite.appendChild(el("span", null, "min"));
    dureeLigne.appendChild(unite);
    dureeBloc.appendChild(dureeLigne);
    details.appendChild(dureeBloc);
    form.appendChild(details);
    var comBloc = el("label", "mm-champ");
    comBloc.appendChild(el("span", "mm-lib", "Commentaire"));
    comBloc.appendChild(f.comment);
    form.appendChild(comBloc);

    var pied = el("div", "mm-pied");
    pied.append(f.etat, f.envoyer);
    form.appendChild(pied);
    f.racine = form;
    return f;
  }

  function dessinerForm(f) {
    f.codes.textContent = "";
    if (!M.codes) f.codes.appendChild(el("div", "mm-vide", "Chargement du catalogue…"));
    (M.codes || []).forEach(function (c) {
      var b = pastille(c.label, M.code === c.code, function () { M.code = M.code === c.code ? "" : c.code; rendre(); });
      b.title = c.code;
      f.codes.appendChild(b);
    });
    var autre = pastille("Autre maintenance", M.code === AUTRE, function () {
      M.code = M.code === AUTRE ? "" : AUTRE;
      rendre();
      if (M.code === AUTRE) f.titre.focus();
    }, "mm-pastille-autre");
    if (M.code !== AUTRE) autre.insertBefore(icone("plus", 14), autre.firstChild);
    f.codes.appendChild(autre);
    f.titreBloc.hidden = M.code !== AUTRE;

    var liste = M.machines.slice();
    if (M.machine && liste.indexOf(M.machine) < 0) liste.unshift(M.machine);
    f.machines.textContent = "";
    if (!liste.length) f.machines.appendChild(el("div", "mm-vide", "Aucune machine."));
    liste.forEach(function (m) {
      f.machines.appendChild(pastille(m, m === M.machine, function () {
        if (m === M.machine) return;
        M.machine = m; M.histo = null;
        rendre();
        chargerHisto();
      }, "mm-pastille-machine"));
    });

    var dv = f.duree.value.trim();
    f.durees.textContent = "";
    DUREES.forEach(function (n) {
      f.durees.appendChild(pastille(n < 60 ? n + " min" : (n / 60) + " h", dv === String(n), function () {
        f.duree.value = dv === String(n) ? "" : String(n);
        rendre();
      }, "mm-pastille-petite"));
    });

    f.envoyer.textContent = "";
    f.envoyer.appendChild(icone("check", 16));
    f.envoyer.appendChild(document.createTextNode(M.envoi ? "Enregistrement…" : "Enregistrer l'opération"));
    f.envoyer.disabled = M.envoi || M.refus;
    f.etat.textContent = M.refus ? "Enregistrement réservé à l'atelier et aux responsables maintenance." : M.erreur;
    f.etat.classList.toggle("mm-erreur", !!(M.erreur || M.refus));
  }

  function historique() {
    var b = el("div", "mm-carte mm-histo");
    var t = el("div", "mm-histo-tete");
    t.appendChild(el("div", "mm-histo-titre", "Dernières opérations"));
    t.appendChild(el("div", "mm-histo-sous", (M.machine || "—") + " · " + JOURS_HISTO + " derniers jours"));
    b.appendChild(t);
    if (M.histo == null) { b.appendChild(el("div", "mm-vide", "Chargement…")); return b; }
    if (!M.histo.length) { b.appendChild(el("div", "mm-vide", "Aucune opération enregistrée sur cette machine depuis " + JOURS_HISTO + " jours.")); return b; }
    var ul = el("ul", "mm-liste");
    M.histo.slice(0, LIGNES_HISTO).forEach(function (h) {
      var li = el("li", "mm-op" + (h.libre ? " mm-op-autre" : ""));
      var haut = el("div", "mm-op-haut");
      haut.appendChild(el("span", "mm-op-nom", h.type || h.code || "—"));
      if (h.libre) haut.appendChild(el("span", "mm-tag", "Autre"));
      haut.appendChild(el("span", "mm-op-date", jourLisible(h.date_saisie)));
      li.appendChild(haut);
      var meta = [h.operateur || "", h.duree_reelle_min != null ? h.duree_reelle_min + " min" : ""].filter(Boolean).join(" · ");
      if (meta) li.appendChild(el("div", "mm-op-meta", meta));
      if (h.commentaire) li.appendChild(el("div", "mm-op-com", h.commentaire));
      ul.appendChild(li);
    });
    b.appendChild(ul);
    if (M.histo.length > LIGNES_HISTO) b.appendChild(el("div", "mm-histo-sous", "+ " + (M.histo.length - LIGNES_HISTO) + " dans MyMaintenance"));
    return b;
  }

  function lienMaintenance() {
    // Responsables : historique des opérations filtré sur la machine ;
    // atelier : ses tâches de maintenance (MyMaintenance choisit la vue).
    return M.role === "fabrication" ? "/maintenance?vue=op-tasks"
      : "/maintenance?vue=operations" + (M.machine ? "&machine=" + encodeURIComponent(M.machine) : "");
  }

  // Squelette construit une fois (le formulaire n'est jamais sorti de la
  // page : un champ en cours de frappe garde son focus) ; à chaque rendu,
  // pastilles, lien et historique seulement.
  function rendre() {
    if (!M.el) return;
    if (!M.form) {
      M.form = construireForm();
      var tete = el("div", "mm-tete");
      var ico = el("div", "mm-tete-ico");
      ico.appendChild(icone("outil", 22));
      var tt = el("div", "mm-tete-txt");
      tt.appendChild(el("h3", "mm-titre", "Enregistrer une opération de maintenance"));
      tt.appendChild(el("div", "mm-sous", "Intervention déjà réalisée. Elle rejoint l'historique de MyMaintenance."));
      M.lien = el("a", "mm-lien");
      M.lien.appendChild(document.createTextNode("Ouvrir MyMaintenance"));
      M.lien.appendChild(icone("fleche", 14));
      tete.append(ico, tt, M.lien);
      M.corps = el("div", "mm-corps");
      M.histoEl = el("div");
      M.corps.append(M.form.racine, M.histoEl);
      M.el.append(tete, M.corps);
    }
    dessinerForm(M.form);
    M.lien.href = lienMaintenance();
    var h = historique();
    M.corps.replaceChild(h, M.histoEl);
    M.histoEl = h;
  }

  function vue(opts) {
    opts = opts || {};
    var machines = (opts.machines || []).filter(Boolean);
    M.role = opts.role || M.role;
    if (!M.el) {
      M.el = el("section", "mm-section");
      M.machine = opts.machine || machines[0] || "";
      M.machines = machines;
      rendre();
      chargerCodes();
      chargerHisto();
      return M.el;
    }
    // La liste des machines peut arriver après le premier rendu.
    if (machines.join("|") !== M.machines.join("|")) {
      M.machines = machines;
      if (!M.machine) { M.machine = opts.machine || machines[0] || ""; chargerHisto(); }
      rendre();
    }
    return M.el;
  }

  global.MySifaMaintSaisie = { vue: vue, _doneAt: doneAt };
})(window);
