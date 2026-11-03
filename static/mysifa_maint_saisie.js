/*
 * MySifa — Saisie prod, onglet Qualité : enregistrer une opération de
 * maintenance déjà réalisée, sans quitter la saisie.
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
 * Les opérations récentes de la machine sont relues dans
 * GET /api/maintenance/history, la source de l'écran Historique.
 *
 *   MySifaMaintSaisie.vue({machine, machines, role})   élément durable à poser
 *       dans la page ; les appels suivants rendent le même élément (saisie en
 *       cours conservée). Machine : celle de l'opérateur, modifiable.
 * Tout texte passe par textContent.
 */
(function (global) {
  "use strict";

  var AUTRE = "__autre__";
  var JOURS_HISTO = 30, LIGNES_HISTO = 6;
  var M = { el: null, codes: null, histo: null, machine: "", machines: [], role: "", refus: false,
            envoi: false, erreur: "", form: null };

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function isoJour(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function dateCourte(iso) {
    var s = String(iso || "");
    return s.length >= 10 ? s.slice(8, 10) + "/" + s.slice(5, 7) + (s.length >= 16 ? " " + s.slice(11, 16) : "") : s;
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
    var autre = f.code.value === AUTRE;
    var titre = f.titre.value.trim(), jour = f.date.value, machine = f.machine.value;
    var dureeTxt = f.duree.value.trim(), comment = f.comment.value.trim();
    var duree = dureeTxt === "" ? null : Number(dureeTxt.replace(",", "."));
    if (!f.code.value) return erreur("Choisissez une intervention.");
    if (autre && !titre) return erreur("Décrivez l'intervention.");
    if (!machine) return erreur("Machine obligatoire.");
    if (!jour) return erreur("Date obligatoire.");
    if (jour > isoJour(new Date())) return erreur("Une opération réalisée ne peut pas être datée dans le futur.");
    if (duree != null && (!isFinite(duree) || duree < 0 || Math.round(duree) !== duree)) {
      return erreur("Durée invalide — nombre entier de minutes.");
    }
    M.envoi = true; M.erreur = "";
    rendre();
    var ev = null;
    try {
      var code = f.code.value;
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
      f.code.value = ""; f.titre.value = ""; f.duree.value = ""; f.comment.value = "";
      f.date.value = isoJour(new Date());
      toast("Opération enregistrée.");
      M.machine = machine;
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
  // Le formulaire est construit une fois : la saisie en cours survit aux
  // rendus. Seuls la liste des interventions, l'état et l'historique bougent.
  function construireForm() {
    var f = {};
    function champ(lib, input, cls) {
      var c = el("label", "mm-champ" + (cls ? " " + cls : ""));
      c.appendChild(el("span", "mm-lib", lib));
      c.appendChild(input);
      return c;
    }
    f.code = el("select", "mm-input");
    f.titre = el("input", "mm-input");
    f.titre.type = "text";
    f.titre.maxLength = 200;
    f.titre.placeholder = "Ex. : remplacement joint pompe hydraulique";
    f.machine = el("select", "mm-input");
    f.date = el("input", "mm-input");
    f.date.type = "date";
    f.date.value = isoJour(new Date());
    f.date.max = isoJour(new Date());
    f.duree = el("input", "mm-input");
    f.duree.type = "number";
    f.duree.min = "0";
    f.duree.step = "1";
    f.duree.placeholder = "Facultatif";
    f.comment = el("textarea", "mm-input");
    f.comment.rows = 2;
    f.comment.placeholder = "Pièces changées, observations…";
    f.envoyer = el("button", "mm-btn", "Enregistrer");
    f.envoyer.type = "button";
    f.envoyer.addEventListener("click", enregistrer);
    f.machine.addEventListener("change", function () { M.machine = f.machine.value; M.histo = null; rendre(); chargerHisto(); });
    f.code.addEventListener("change", function () {
      f.titreChamp.hidden = f.code.value !== AUTRE;
      if (!f.titreChamp.hidden) f.titre.focus();
    });

    var grille = el("div", "mm-grille");
    grille.appendChild(champ("Intervention", f.code, "mm-large"));
    f.titreChamp = champ("Autre maintenance — description", f.titre, "mm-large");
    f.titreChamp.hidden = true;
    grille.appendChild(f.titreChamp);
    grille.appendChild(champ("Machine", f.machine));
    grille.appendChild(champ("Date", f.date));
    grille.appendChild(champ("Durée (min)", f.duree));
    grille.appendChild(champ("Commentaire", f.comment, "mm-large"));
    f.racine = el("div", "mm-form");
    f.racine.appendChild(grille);
    f.etat = el("div", "mm-etat");
    var pied = el("div", "mm-pied");
    pied.append(f.etat, f.envoyer);
    f.racine.appendChild(pied);
    return f;
  }

  function remplirCodes(f) {
    var avant = f.code.value;
    f.code.textContent = "";
    f.code.appendChild(new Option(M.codes ? "Choisir une intervention…" : "Chargement…", ""));
    (M.codes || []).forEach(function (c) {
      var o = new Option(c.label, c.code);
      o.title = c.code;
      f.code.appendChild(o);
    });
    f.code.appendChild(new Option("Autre maintenance…", AUTRE));
    f.code.value = avant;
    if (f.code.value !== avant) f.code.value = "";
    f.titreChamp.hidden = f.code.value !== AUTRE;
  }
  function remplirMachines(f) {
    var liste = M.machines.slice();
    if (M.machine && liste.indexOf(M.machine) < 0) liste.unshift(M.machine);
    var cle = liste.join("|");
    if (f.machinesCle === cle) { f.machine.value = M.machine; return; }
    f.machinesCle = cle;
    f.machine.textContent = "";
    if (!liste.length) f.machine.appendChild(new Option("Aucune machine", ""));
    liste.forEach(function (m) { f.machine.appendChild(new Option(m, m)); });
    f.machine.value = M.machine;
  }

  function historique() {
    var b = el("div", "mm-histo");
    var t = el("div", "mm-sous-titre", "Dernières opérations" + (M.machine ? " · " + M.machine : "") + " · " + JOURS_HISTO + " jours");
    b.appendChild(t);
    if (M.histo == null) { b.appendChild(el("div", "mm-vide", "Chargement…")); return b; }
    if (!M.histo.length) { b.appendChild(el("div", "mm-vide", "Aucune opération enregistrée sur cette période.")); return b; }
    var tab = el("table", "mm-table"), th = el("tr");
    ["Date", "Opération", "Opérateur", "Durée", "Commentaire"].forEach(function (h, i) {
      th.appendChild(el("th", i === 3 ? "num" : null, h));
    });
    var thead = el("thead");
    thead.appendChild(th);
    tab.appendChild(thead);
    var tb = el("tbody");
    M.histo.slice(0, LIGNES_HISTO).forEach(function (h) {
      var r = el("tr");
      r.appendChild(el("td", "mm-date", dateCourte(h.date_saisie)));
      var type = el("td", null, h.type || h.code || "—");
      if (h.libre) type.appendChild(el("span", "mm-tag", "Autre"));
      r.appendChild(type);
      r.appendChild(el("td", null, h.operateur || "—"));
      r.appendChild(el("td", "num", h.duree_reelle_min != null ? h.duree_reelle_min + " min" : "—"));
      var c = el("td", "mm-com", h.commentaire || "");
      c.title = h.commentaire || "";
      r.appendChild(c);
      tb.appendChild(r);
    });
    tab.appendChild(tb);
    var w = el("div", "mm-table-wrap");
    w.appendChild(tab);
    b.appendChild(w);
    return b;
  }

  function lienMaintenance() {
    // Responsables : historique des opérations filtré sur la machine ;
    // atelier : ses tâches de maintenance (MyMaintenance choisit la vue).
    var href = M.role === "fabrication" ? "/maintenance?vue=op-tasks"
      : "/maintenance?vue=operations" + (M.machine ? "&machine=" + encodeURIComponent(M.machine) : "");
    var a = el("a", "mm-lien", "Ouvrir MyMaintenance →");
    a.href = href;
    return a;
  }

  function rendre() {
    if (!M.el) return;
    if (!M.form) M.form = construireForm();
    var f = M.form;
    remplirCodes(f);
    remplirMachines(f);
    f.envoyer.disabled = M.envoi || M.refus;
    f.envoyer.textContent = M.envoi ? "Enregistrement…" : "Enregistrer";
    f.etat.textContent = M.refus ? "Enregistrement réservé à l'atelier et aux responsables maintenance." : M.erreur;
    f.etat.classList.toggle("mm-erreur", !!(M.erreur || M.refus));

    var tete = el("div", "mm-tete");
    var tt = el("div", null);
    tt.appendChild(el("h3", "mm-titre", "Opérations de maintenance"));
    tt.appendChild(el("div", "mm-sous",
      "Interventions déjà réalisées. Elles sont enregistrées dans MyMaintenance, comme si elles y avaient été saisies."));
    tete.append(tt, lienMaintenance());
    M.el.textContent = "";
    M.el.append(tete, f.racine, historique());
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
