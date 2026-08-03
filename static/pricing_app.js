/**
 * MySifa — Coûts matières (SPA client-side routing)
 */
(function () {
  "use strict";

  const INIT = window.__PRICING__ || { canWrite: false, user: {} };
  const ADMIN_ROLES = new Set(["direction", "superadmin"]);

  const S = {
    canWrite: !!INIT.canWrite,
    user: INIT.user || {},
    route: { name: "dashboard", id: null },
    loading: true,
    dashboard: null,
    categories: [],
    suppliers: [],
    supplierMap: {},
    materials: [],
    materialsAll: [],
    products: [],
    settings: null,
    filters: {
      matQ: "",
      matCats: [],
      matSupplier: "",
      matActive: "1",
      prodQ: "",
    },
    formMaterial: null,
    formProduct: null,
    matPreview: null,
    prodPreview: null,
    drawerMaterial: null,
    debounceMat: null,
    debounceProd: null,
    selectedProductIds: new Set(),
  };

  const CAT_CLASS = {
    FRONTAL: "badge-frontal",
    ADHESIF: "badge-adhesif",
    SILICONE: "badge-silicone",
    GLASSINE: "badge-glassine",
    AUTRE: "badge-autre",
  };

  const CAT_BAR_COLOR = {
    frontal: "var(--cat-frontal)",
    adhesif: "var(--cat-adhesif)",
    silicone: "var(--cat-silicone)",
    glassine: "var(--cat-glassine)",
    extra_1: "var(--cat-autre)",
    extra_2: "var(--cat-autre)",
  };

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escAttr(s) {
    return escHtml(s).replace(/'/g, "&#39;");
  }

  const ROLE_LABELS = {
    direction: "Direction",
    administration: "Administration",
    fabrication: "Fabrication",
    logistique: "Logistique",
    comptabilite: "Comptabilité",
    expedition: "Expédition",
    commercial: "Commercial",
    superadmin: "Super admin",
  };

  function icon(name, size) {
    size = size || 16;
    const a =
      'width="' +
      size +
      '" height="' +
      size +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"';
    const p = {
      grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
      package:
        '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
      layers:
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
      settings:
        '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
      menu: '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
      home: '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/>',
      sun: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
      moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
      "log-out":
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
      edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    };
    return "<svg " + a + ">" + (p[name] || p.grid) + "</svg>";
  }

  /** Format nombre fr-FR (espace milliers, virgule décimale). */
  function fmtNum(n, minDec, maxDec) {
    const x = parseFloat(n);
    if (Number.isNaN(x)) return "—";
    return new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: minDec ?? 2,
      maximumFractionDigits: maxDec ?? 4,
    }).format(x);
  }

  function fmt4(n) {
    return fmtNum(n, 4, 4);
  }

  function fmt2(n) {
    return fmtNum(n, 2, 2);
  }

  function fmtEur(n, decimals) {
    const s = fmtNum(n, decimals ?? 4, decimals ?? 4);
    return s === "—" ? s : s + "\u00a0€";
  }

  function fmtEurM2(n) {
    const s = fmtNum(n, 4, 4);
    return s === "—" ? s : s + "\u00a0€/m²";
  }

  function fmtPct(n) {
    const s = fmtNum(n, 2, 2);
    return s === "—" ? s : s + "\u00a0%";
  }

  const CUR_SYM = { EUR: "€", USD: "$" };

  /** Montant dans une devise donnée : 4,0183 $ */
  function fmtCur(n, cur) {
    const s = fmtNum(n, 4, 4);
    return s === "—" ? s : s + "\u00a0" + (CUR_SYM[(cur || "EUR").toUpperCase()] || "€");
  }

  /** Unité d'achat lisible : $/kg, €/m²… */
  function unitLabel(cur, basis) {
    const sym = CUR_SYM[(cur || "EUR").toUpperCase()] || "€";
    return sym + "/" + (basis === "PER_M2" ? "m²" : "kg");
  }

  const BASIS_LABEL = {
    PER_KG: "Au kilo — le prix est saisi par kg, converti au m² via le poids",
    PER_M2: "Au mètre carré — le prix est déjà exprimé au m²",
  };

  /** Le poids au m² n'est utile que si le prix est au kilo ou pour la calculette import. */
  function needsWeight(form) {
    return form.price_basis === "PER_KG" || !!form.is_imported;
  }

  function isFxStale(updatedAt) {
    if (!updatedAt) return true;
    const raw = String(updatedAt).replace(" ", "T");
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return true;
    return (Date.now() - d.getTime()) / 86400000 > 7;
  }

  function fxStaleBadgeHtml() {
    return '<span class="badge badge-fx-stale">À rafraîchir</span>';
  }

  function confirmDelete(message) {
    return new Promise((resolve) => {
      const root = document.getElementById("modal-root");
      root.innerHTML = `
        <div class="modal-backdrop" id="cfm-back">
          <div class="modal" style="max-width:400px">
            <h2>Confirmation</h2>
            <p style="font-size:13px;color:var(--text2);line-height:1.6;margin:0 0 16px">${escHtml(message)}</p>
            <div style="display:flex;gap:10px;justify-content:flex-end">
              <button type="button" class="btn btn-soft" id="cfm-no">Annuler</button>
              <button type="button" class="btn btn-danger" id="cfm-yes">Supprimer</button>
            </div>
          </div>
        </div>`;
      const close = (ok) => {
        root.innerHTML = "";
        resolve(ok);
      };
      document.getElementById("cfm-no").onclick = () => close(false);
      document.getElementById("cfm-yes").onclick = () => close(true);
      document.getElementById("cfm-back").onclick = (e) => {
        if (e.target.id === "cfm-back") close(false);
      };
    });
  }

  function showToast(msg, type) {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const el = document.createElement("div");
    el.className = "toast " + (type || "info");
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(() => el.remove(), 3200);
  }

  async function api(path, opts) {
    const o = opts || {};
    const res = await fetch(path, {
      credentials: "include",
      headers: o.body ? { "Content-Type": "application/json", ...(o.headers || {}) } : o.headers,
      method: o.method || (o.body ? "POST" : "GET"),
      body: o.body ? JSON.stringify(o.body) : undefined,
    });
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      try {
        data = await res.json();
      } catch (e) {
        data = null;
      }
    }
    if (!res.ok) {
      const detail = data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join(", ")
            : "Erreur " + res.status;
      const err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function parseRoute() {
    const p = window.location.pathname.replace(/\/+$/, "") || "/pricing";
    const parts = p.split("/").filter(Boolean);
    if (parts.length <= 1 || parts[0] !== "pricing") {
      return { name: "dashboard", id: null };
    }
    const seg = parts[1];
    if (seg === "materials") {
      if (parts[2] === "new") return { name: "material-new", id: null };
      if (parts[2] && /^\d+$/.test(parts[2])) return { name: "material-edit", id: parts[2] };
      return { name: "materials", id: null };
    }
    if (seg === "products") {
      if (parts[2] === "new") return { name: "product-new", id: null };
      if (parts[2] && /^\d+$/.test(parts[2])) return { name: "product-edit", id: parts[2] };
      return { name: "products", id: null };
    }
    if (seg === "settings") return { name: "settings", id: null };
    return { name: "dashboard", id: null };
  }

  function navigate(path) {
    document.body.classList.remove("sb-open");
    if (window.location.pathname !== path) {
      history.pushState(null, "", path);
    }
    S.route = parseRoute();
    bootRoute();
  }

  function currencyBadge(cur) {
    const c = (cur || "EUR").toUpperCase();
    return `<span class="currency-badge${c === "USD" ? " usd" : ""}">${escHtml(c)}</span>`;
  }

  function categoryBadge(code) {
    const c = (code || "AUTRE").toUpperCase();
    return `<span class="badge ${CAT_CLASS[c] || "badge-autre"}">${escHtml(c)}</span>`;
  }

  /** @param {{components:Array, total?:number}} opts */
  function priceBreakdownHtml(opts) {
    const comps = opts.components || [];
    const total =
      opts.total != null
        ? parseFloat(opts.total)
        : comps.reduce((s, c) => s + parseFloat(c.price_eur_per_m2 || 0), 0);
    if (!comps.length || total <= 0) {
      return '<div class="empty">Aucun composant</div>';
    }
    const segs = comps
      .map((c) => {
        const v = parseFloat(c.price_eur_per_m2 || 0);
        const pct = total > 0 ? (v / total) * 100 : 0;
        const col = CAT_BAR_COLOR[c.role] || "var(--accent)";
        return `<div class="breakdown-seg" style="width:${pct.toFixed(1)}%;background:${col}" title="${escAttr(c.name)}"></div>`;
      })
      .join("");
    const legend = comps
      .map((c) => {
        const v = parseFloat(c.price_eur_per_m2 || 0);
        const pct = total > 0 ? ((v / total) * 100).toFixed(1) : "0";
        return `<div><span>${escHtml(c.name || c.role)}</span><span>${fmtEurM2(v)} · ${pct}%</span></div>`;
      })
      .join("");
    return `<div class="breakdown-stack"><div class="breakdown-bar">${segs}</div><div class="breakdown-legend">${legend}</div></div>`;
  }

  function updateChromeControls() {
    const isLight = document.body.classList.contains("light");
    const themeIco = document.getElementById("theme-ico");
    const themeLabel = document.getElementById("theme-label");
    if (themeIco) themeIco.innerHTML = icon(isLight ? "sun" : "moon", 16);
    if (themeLabel) themeLabel.textContent = isLight ? "Mode clair" : "Mode sombre";
    const logoutIco = document.getElementById("logout-ico");
    if (logoutIco) logoutIco.innerHTML = icon("log-out", 14);
    const menuBtn = document.getElementById("mobile-menu-btn");
    if (menuBtn) menuBtn.innerHTML = icon("menu", 20);
    const homeBtn = document.getElementById("mobile-home-btn");
    if (homeBtn) homeBtn.innerHTML = icon("home", 20);
    const chip = document.getElementById("user-chip");
    if (chip && S.user) {
      if (window.MySifaUserChip) {
        MySifaUserChip.fill(chip, S.user, {
          roleLabels: ROLE_LABELS,
          editIconHtml: icon("edit", 10),
        });
        chip.onclick = () => {
          window.location.href = "/profil";
        };
      } else {
        chip.innerHTML =
          '<div class="uc-name">' +
          escHtml(S.user.nom || "—") +
          '</div><div class="uc-role">' +
          escHtml(ROLE_LABELS[S.user.role] || S.user.role || "") +
          "</div>";
      }
    }
  }

  function renderSidebar() {
    const nav = document.getElementById("sidebar-nav");
    const items = [
      { path: "/pricing", label: "Tableau de bord", route: "dashboard", icon: "grid" },
      { path: "/pricing/materials", label: "Matières", route: "materials", icon: "package" },
      { path: "/pricing/products", label: "Produits", route: "products", icon: "layers" },
    ];
    if (S.canWrite) {
      items.push({ path: "/pricing/settings", label: "Paramètres", route: "settings", icon: "settings" });
    }
    const active = S.route.name;
    nav.innerHTML = items
      .map((it) => {
        const on =
          active === it.route ||
          (it.route === "materials" && active.startsWith("material")) ||
          (it.route === "products" && active.startsWith("product"));
        return (
          `<button type="button" class="nav-btn${on ? " active" : ""}" data-nav="${escAttr(it.path)}">` +
          icon(it.icon, 16) +
          `<span>${escHtml(it.label)}</span></button>`
        );
      })
      .join("");
    nav.querySelectorAll("[data-nav]").forEach((btn) => {
      btn.onclick = () => navigate(btn.getAttribute("data-nav"));
    });

    updateChromeControls();

    const titles = {
      dashboard: ["Coûts matières", "Tableau de bord"],
      materials: ["Matières", "Liste"],
      "material-new": ["Matière", "Nouvelle"],
      "material-edit": ["Matière", "Édition"],
      products: ["Produits", "Liste"],
      "product-new": ["Produit", "Nouveau"],
      "product-edit": ["Produit", "Édition"],
      settings: ["Paramètres", "Coûts matières"],
    };
    const t = titles[active] || titles.dashboard;
    document.getElementById("mobile-title").textContent = t[0];
    document.getElementById("mobile-sub").textContent = t[1];
  }

  /**
   * En-tête de page commun. `sub` et `actions` acceptent du HTML.
   * L'engrenage Paramètres est présent sur toutes les pages (droits en écriture).
   */
  function pageHead(title, sub, actions) {
    const gear = S.canWrite
      ? `<button type="button" class="icon-btn" id="btn-open-settings" title="Paramètres">${icon("settings", 16)}</button>`
      : "";
    return `<div class="page-head">
        <div><h1>${escHtml(title)}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div>
        <div class="page-head-actions">${actions || ""}${gear}</div>
      </div>`;
  }

  function setContent(html) {
    document.getElementById("content").innerHTML = html;
    const gear = document.getElementById("btn-open-settings");
    if (gear) gear.onclick = () => openSettingsModal();
  }

  function showLoading() {
    setContent(
      '<div class="loading-state"><div class="spinner"></div><span>Chargement…</span></div>'
    );
  }

  async function loadBaseData() {
    const [cats, sups, settings] = await Promise.all([
      api("/api/pricing/categories"),
      api("/api/pricing/suppliers?active_only=false"),
      api("/api/pricing/settings"),
    ]);
    S.categories = cats.categories || [];
    S.suppliers = sups.suppliers || [];
    S.supplierMap = {};
    S.suppliers.forEach((s) => {
      S.supplierMap[s.id] = s.name;
    });
    S.settings = settings;
  }

  async function renderDashboard() {
    S.dashboard = await api("/api/pricing/dashboard");
    const d = S.dashboard;
    const fxDate = d.eur_usd_rate_updated_at
      ? String(d.eur_usd_rate_updated_at).replace("T", " ").slice(0, 16)
      : "—";
    const fxSrc = d.eur_usd_rate_source || "—";
    const fxStale = isFxStale(d.eur_usd_rate_updated_at);
    setContent(`
      <div class="pr-narrow">
        ${pageHead("Tableau de bord", "Calcul des coûts matières")}
        <div class="kpi-grid kpi-grid-3">
          <div class="kpi-card"><div class="kpi-label">Matières actives</div><div class="kpi-value">${d.materials_active}</div></div>
          <div class="kpi-card"><div class="kpi-label">Produits actifs</div><div class="kpi-value">${d.products_active}</div></div>
          <div class="kpi-card">
            <div class="kpi-label">Taux USD / EUR ${fxStale ? fxStaleBadgeHtml() : ""}</div>
            <div class="kpi-value">${fmtNum(d.eur_usd_rate, 4, 4)}</div>
            <div class="kpi-meta">1 USD = ${fmtNum(d.eur_usd_rate, 4, 4)} € · MAJ : ${escHtml(fxDate)} · ${escHtml(fxSrc)}</div>
            ${S.canWrite ? '<button type="button" class="btn btn-soft btn-sm" id="dash-fx-btn" style="margin-top:10px">Rafraîchir</button>' : ""}
          </div>
        </div>
      </div>
    `);
    const fxBtn = document.getElementById("dash-fx-btn");
    if (fxBtn) {
      fxBtn.onclick = async () => {
        try {
          await api("/api/pricing/settings/refresh-fx", { method: "POST" });
          showToast("Taux USD/EUR mis à jour.", "success");
          S.settings = await api("/api/pricing/settings");
          await renderDashboard();
        } catch (e) {
          showToast(e.message, "danger");
        }
      };
    }
  }

  async function loadMaterialsList() {
    const params = new URLSearchParams();
    // L'API ne connaît que « actifs uniquement » ou « tout » : pour afficher les
    // inactifs seuls, on charge tout et on tranche côté client.
    params.set("active_only", S.filters.matActive === "1" ? "true" : "false");
    params.set("with_computed", "true");
    if (S.filters.matQ) params.set("q", S.filters.matQ);
    if (S.filters.matSupplier) params.set("supplier_id", S.filters.matSupplier);
    const data = await api("/api/pricing/materials?" + params.toString());
    // On conserve la liste brute : les filtres client sont rejouables sans
    // rappeler l'API (décocher une catégorie doit restituer les lignes).
    S.materialsAll = data.materials || [];
    applyMaterialFilters();
  }

  /** Filtres appliqués côté client : catégories cochées et statut actif/inactif. */
  function applyMaterialFilters() {
    let list = S.materialsAll || [];
    if (S.filters.matCats.length) {
      const set = new Set(S.filters.matCats);
      list = list.filter((m) => set.has(m.category_code));
    }
    if (S.filters.matActive === "1") list = list.filter((m) => m.is_active);
    else if (S.filters.matActive === "0") list = list.filter((m) => !m.is_active);
    S.materials = list;
  }

  function renderMaterialsList() {
    const catOpts = S.categories
      .map(
        (c) =>
          `<label class="cat-cb${S.filters.matCats.includes(c.code) ? " on" : ""}"><input type="checkbox" class="mat-cat-cb" value="${escAttr(c.code)}" ${S.filters.matCats.includes(c.code) ? "checked" : ""}/>${escHtml(c.label)}</label>`
      )
      .join("");
    const supOpts =
      '<option value="">Tous fournisseurs</option>' +
      S.suppliers
        .filter((s) => s.is_active)
        .map(
          (s) =>
            `<option value="${s.id}" ${String(S.filters.matSupplier) === String(s.id) ? "selected" : ""}>${escHtml(s.name)}</option>`
        )
        .join("");

    const rows = S.materials
      .map((m) => {
        const sup = m.supplier_id ? S.supplierMap[m.supplier_id] || "—" : "—";
        const live = m.computed ? fmtEurM2(m.computed.price_eur_per_m2) : "—";
        const unit = `${fmtNum(m.unit_price, 4, 4)}\u00a0${m.price_currency}/${m.price_basis === "PER_M2" ? "m²" : "kg"}`;
        return `<tr data-mid="${m.id}">
          <td>${categoryBadge(m.category_code)}</td>
          <td><button type="button" class="cell-link" data-edit-m="${m.id}" title="Éditer cette matière">${escHtml(m.name)}</button></td>
          <td>${escHtml(m.appellation_code)}</td>
          <td>${escHtml(sup)}</td>
          <td>${unit}</td>
          <td><strong>${live}</strong></td>
          <td>${m.is_active ? '<span class="badge badge-glassine">Actif</span>' : '<span class="badge badge-inactive">Inactif</span>'}</td>
          <td class="row-actions" onclick="event.stopPropagation()">
            <button type="button" class="btn btn-soft btn-sm" data-hist="${m.id}">Historique</button>
            ${S.canWrite ? `<button type="button" class="btn btn-soft btn-sm" data-edit-m="${m.id}">Éditer</button>` : ""}
          </td>
        </tr>`;
      })
      .join("");

    const emptyBlock =
      !S.materials.length && !S.filters.matQ && !S.filters.matSupplier && !S.filters.matCats.length
        ? `<div class="empty-state">
            <p>Aucune matière enregistrée.</p>
            ${S.canWrite ? '<button type="button" class="btn btn-accent" id="empty-new-mat">Créer la première matière</button>' : ""}
          </div>`
        : "";

    setContent(`
      <div class="pr-narrow">
        ${pageHead(
          "Matières",
          `${S.materials.length} ligne(s)`,
          S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-new-mat">+ Nouvelle matière</button>' : ""
        )}
        <div class="filters">
          <input type="search" class="search-input" id="mat-q" placeholder="Rechercher (nom, appellation…)" value="${escAttr(S.filters.matQ)}"/>
          <select id="mat-sup">${supOpts}</select>
          <select id="mat-active"><option value="1" ${S.filters.matActive==="1"?"selected":""}>Actifs</option><option value="0" ${S.filters.matActive==="0"?"selected":""}>Inactifs</option><option value="all" ${S.filters.matActive==="all"?"selected":""}>Tous</option></select>
        </div>
        <div class="cat-filters">${catOpts}</div>
        ${emptyBlock}
        <div class="table-wrap" ${emptyBlock ? 'style="display:none"' : ""}>
          <table class="pr-table">
            <thead><tr><th>Cat.</th><th>Nom</th><th>Appellation</th><th>Fournisseur</th><th>Prix unit.</th><th>€/m²</th><th>Statut</th><th></th></tr></thead>
            <tbody>${rows || '<tr><td colspan="8" class="empty">Aucun résultat pour ce filtre</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `);

    const qEl = document.getElementById("mat-q");
    let qTimer;
    qEl.oninput = () => {
      clearTimeout(qTimer);
      qTimer = setTimeout(async () => {
        S.filters.matQ = qEl.value;
        await loadMaterialsList();
        renderMaterialsList();
      }, 300);
    };
    document.getElementById("mat-sup").onchange = async (e) => {
      S.filters.matSupplier = e.target.value;
      await loadMaterialsList();
      renderMaterialsList();
    };
    document.getElementById("mat-active").onchange = async (e) => {
      S.filters.matActive = e.target.value;
      await loadMaterialsList();
      renderMaterialsList();
    };
    document.querySelectorAll(".mat-cat-cb").forEach((cb) => {
      cb.onchange = () => {
        S.filters.matCats = Array.from(
          document.querySelectorAll(".mat-cat-cb:checked")
        ).map((x) => x.value);
        applyMaterialFilters();
        renderMaterialsList();
      };
    });
    document.querySelectorAll("tbody tr[data-mid]").forEach((tr) => {
      tr.onclick = () => openMaterialDrawer(tr.getAttribute("data-mid"));
    });
    document.querySelectorAll("[data-hist]").forEach((b) => {
      b.onclick = () => openPriceHistoryModal(b.getAttribute("data-hist"));
    });
    document.querySelectorAll("[data-edit-m]").forEach((b) => {
      b.onclick = (e) => {
        e.stopPropagation();
        navigate("/pricing/materials/" + b.getAttribute("data-edit-m"));
      };
    });
    const btnNew = document.getElementById("btn-new-mat");
    if (btnNew) btnNew.onclick = () => navigate("/pricing/materials/new");
    const emptyNew = document.getElementById("empty-new-mat");
    if (emptyNew) emptyNew.onclick = () => navigate("/pricing/materials/new");
  }

  function defaultMaterialForm() {
    const cat = S.categories[0];
    return {
      name: "",
      appellation_code: "",
      category_id: cat ? cat.id : 1,
      supplier_id: "",
      weight_per_m2: "0",
      weight_gsm: "",
      price_currency: "EUR",
      unit_price: "0",
      price_basis: "PER_KG",
      tax_incidence: "1",
      is_imported: false,
      transport_mode: "AMOUNT",
      transport_unit_price: "0",
      transport_pct: "0",
    };
  }

  async function loadMaterialForm(id) {
    if (!id) {
      S.formMaterial = defaultMaterialForm();
      S.matPreview = null;
      return;
    }
    const m = await api("/api/pricing/materials/" + id);
    S.formMaterial = {
      name: m.name,
      appellation_code: m.appellation_code,
      category_id: m.category_id,
      supplier_id: m.supplier_id || "",
      weight_per_m2: String(m.weight_per_m2),
      weight_gsm: m.weight_gsm != null ? String(m.weight_gsm) : "",
      price_currency: m.price_currency,
      unit_price: String(m.unit_price),
      price_basis: m.price_basis,
      tax_incidence: String(m.tax_incidence),
      is_imported: !!m.is_imported,
      transport_mode: m.transport_mode || "AMOUNT",
      transport_unit_price:
        m.transport_unit_price != null ? String(m.transport_unit_price) : "0",
      transport_pct: m.transport_pct != null ? String(m.transport_pct) : "0",
      _history: [],
    };
    try {
      const h = await api("/api/pricing/materials/" + id + "/history");
      S.formMaterial._history = (h.history || []).slice(0, 10);
    } catch (e) {
      S.formMaterial._history = [];
    }
    S.matPreview = m.computed || null;
  }

  function materialPreviewPayload() {
    const f = S.formMaterial;
    return {
      unit_price: parseFloat(f.unit_price) || 0,
      weight_per_m2: parseFloat(f.weight_per_m2) || 0,
      price_currency: f.price_currency,
      price_basis: f.price_basis,
      tax_incidence: parseFloat(f.tax_incidence) || 1,
      is_imported: !!f.is_imported,
      transport_mode: f.transport_mode || "AMOUNT",
      transport_unit_price: parseFloat(f.transport_unit_price) || 0,
      transport_pct: parseFloat(f.transport_pct) || 0,
    };
  }

  async function refreshMaterialPreview() {
    if (!S.formMaterial) return;
    try {
      S.matPreview = await api("/api/pricing/materials/preview", {
        method: "POST",
        body: materialPreviewPayload(),
      });
      const el = document.getElementById("mat-recap");
      if (el) el.innerHTML = recapTableHtml(S.matPreview);
      const sum = document.getElementById("mat-summary");
      if (sum) sum.innerHTML = matSummaryHtml(S.matPreview);
      updateTransportEquivalent();
    } catch (e) {
      const el = document.getElementById("mat-recap");
      if (el) el.innerHTML = `<div class="empty" style="color:var(--danger)">${escHtml(e.message)}</div>`;
    }
  }

  /**
   * Tableau récapitulatif horizontal du calcul :
   * (prix d'achat + transport) x taux de change x incidence taxes, puis marge.
   */
  function recapTableHtml(computed) {
    if (!computed) return '<div class="empty">—</div>';
    const b = computed.breakdown || {};
    const cur = (b.currency || "EUR").toUpperCase();
    const basis = b.price_basis || "PER_KG";
    const unit = unitLabel(cur, basis);
    const perM2 = basis === "PER_M2";
    const rate = parseFloat(b.fx_rate || 1);
    const taxRatio =
      parseFloat(b.subtotal_eur || 0) !== 0
        ? parseFloat(computed.price_eur_per_m2) / parseFloat(b.subtotal_eur)
        : 1;
    const w = parseFloat(b.weight_per_m2 || 0);
    const hasTransport = parseFloat(b.transport_src || 0) > 0;

    const cells = [
      { label: "Prix d'achat", value: fmtCur(b.unit_price_src, cur), unit: unit },
      {
        label: "Transport",
        value: hasTransport ? fmtCur(b.transport_src, cur) : "—",
        unit: hasTransport
          ? `${unit} · ${fmtPct(b.transport_pct_effective || 0)} du prix`
          : "non imputé",
        muted: !hasTransport,
      },
      {
        label: "Sous-total achat",
        value: fmtCur(parseFloat(b.unit_price_src || 0) + parseFloat(b.transport_src || 0), cur),
        unit: unit,
      },
    ];
    if (!perM2) {
      // Prix au kilo : on montre explicitement le passage au m² via le poids.
      cells.push({
        label: "Ramené au m²",
        value: fmtCur(parseFloat(b.raw || 0) + parseFloat(b.transport || 0), cur),
        unit: `${CUR_SYM[cur] || "€"}/m² · × ${fmtNum(w, 4, 4)} kg/m²`,
      });
    }
    cells.push(
      {
        label: "Change",
        value: cur === "USD" ? "× " + fmtNum(rate, 4, 4) : "—",
        unit: cur === "USD" ? "USD → EUR" : "achat en €",
        muted: cur !== "USD",
      },
      {
        label: "Achat converti",
        value: fmtNum(parseFloat(b.raw || 0) + parseFloat(b.transport || 0) + parseFloat(b.fx || 0), 4, 4),
        unit: "€/m²",
      },
      {
        label: "Incidence taxes",
        value: "× " + fmtNum(taxRatio, 4, 4),
        unit: parseFloat(b.tax_uplift || 0) >= 0 ? "majoration" : "minoration",
      },
      {
        label: "Prix de revient",
        value: fmtNum(computed.price_eur_per_m2, 4, 4),
        unit: "€/m²",
        strong: true,
      },
      {
        label: `Marge (${fmtNum(computed.margin_pct || 0, 2, 2)} %)`,
        value: fmtNum(computed.margin_eur_m2 || 0, 4, 4),
        unit: "€/m²",
      },
      {
        label: "Prix de vente",
        value: fmtNum(computed.sell_price_eur_m2 || 0, 4, 4),
        unit: "€/m²",
        strong: true,
      }
    );

    const head = cells.map((c) => `<th>${escHtml(c.label)}</th>`).join("");
    const body = cells
      .map(
        (c) =>
          `<td class="${c.strong ? "recap-strong" : ""}${c.muted ? " recap-muted" : ""}">` +
          `<div class="recap-value">${escHtml(c.value)}</div>` +
          (c.unit ? `<div class="recap-unit">${escHtml(c.unit)}</div>` : "") +
          "</td>"
      )
      .join("");

    const notes = [];
    if (!perM2) {
      notes.push(
        w > 0
          ? `Prix au kilo ramené au m² via le poids : × ${fmtNum(w, 4, 4)} kg/m².`
          : `Poids au m² non renseigné : le prix au kilo ne peut pas être ramené au m².`
      );
    }
    if (hasTransport) {
      notes.push(`Transport ramené en euros : ${fmtEurM2(b.transport_eur_m2 || 0)}.`);
    }

    return `
      <div class="recap-card">
        <div class="recap-head">
          <div>
            <div class="recap-title">Détail du calcul</div>
            <div class="recap-formula">(prix d'achat + transport) × change × incidence taxes</div>
          </div>
        </div>
        <div class="recap-scroll">
          <table class="recap-table"><thead><tr>${head}</tr></thead><tbody><tr>${body}</tr></tbody></table>
        </div>
        ${notes.length ? `<div class="recap-notes">${notes.join(" · ")}</div>` : ""}
      </div>`;
  }

  /**
   * Paramètres globaux éditables en place, posés à droite de l'identification.
   * Ils s'appliquent à toutes les matières — d'où l'avertissement et le bouton
   * d'application explicite (pas d'enregistrement silencieux à la frappe).
   */
  function inlineSettingsHtml() {
    const s = S.settings;
    if (!s || !S.canWrite) return "";
    const fxDate = s.eur_usd_rate_updated_at
      ? String(s.eur_usd_rate_updated_at).replace("T", " ").slice(0, 16)
      : "—";
    const stale = isFxStale(s.eur_usd_rate_updated_at);
    return `
      <div class="settings-inline">
        <div class="si-head">Paramètres globaux <span>appliqués à toutes les matières</span></div>
        <div class="field-row">
          <div class="field f-num"><label>Taux USD → EUR ${stale ? fxStaleBadgeHtml() : ""}</label>
            <input type="number" step="0.0001" id="si-rate" value="${escAttr(s.eur_usd_rate)}"/>
          </div>
          <div class="field f-num"><label>Marge par défaut <span class="lbl-unit">%</span></label>
            <input type="number" step="0.01" id="si-margin" value="${escAttr(s.default_margin_pct)}"/>
          </div>
        </div>
        <div class="si-actions">
          <button type="button" class="btn btn-soft btn-sm" id="si-save">Appliquer</button>
          <button type="button" class="btn btn-soft btn-sm" id="si-fx">Rafraîchir le taux</button>
          <span class="si-meta">MAJ ${escHtml(fxDate)} · ${escHtml(s.eur_usd_rate_source || "—")}</span>
        </div>
      </div>`;
  }

  function bindInlineSettings(isNew) {
    const save = document.getElementById("si-save");
    if (save) {
      save.onclick = async () => {
        try {
          S.settings = await api("/api/pricing/settings", {
            method: "PATCH",
            body: {
              eur_usd_rate: parseFloat(document.getElementById("si-rate").value),
              default_margin_pct: parseFloat(document.getElementById("si-margin").value),
            },
          });
          showToast("Paramètres globaux enregistrés.", "success");
          renderMaterialForm(isNew);
          refreshMaterialPreview();
        } catch (e) {
          showToast(e.message, "danger");
        }
      };
    }
    const fx = document.getElementById("si-fx");
    if (fx) {
      fx.onclick = async () => {
        try {
          const r = await api("/api/pricing/settings/refresh-fx", { method: "POST" });
          showToast("Taux mis à jour : " + fmtNum(r.eur_usd_rate, 4, 4), "success");
          S.settings = await api("/api/pricing/settings");
          renderMaterialForm(isNew);
          refreshMaterialPreview();
        } catch (e) {
          showToast(e.message, "danger");
        }
      };
    }
  }

  /** Bandeau résumé en haut de la fiche matière : revient, marge, vente. */
  function matSummaryHtml(computed) {
    if (!computed) {
      return `<div class="ms-item ms-main"><div class="ms-label">Prix de revient</div>
        <div class="ms-value">—</div></div>`;
    }
    return `
      <div class="ms-item ms-main">
        <div class="ms-label">Prix de revient</div>
        <div class="ms-value">${fmtEurM2(computed.price_eur_per_m2)}</div>
      </div>
      <div class="ms-item">
        <div class="ms-label">Marge ${fmtPct(computed.margin_pct || 0)}</div>
        <div class="ms-value">${fmtEurM2(computed.margin_eur_m2 || 0)}</div>
      </div>
      <div class="ms-item">
        <div class="ms-label">Prix de vente</div>
        <div class="ms-value">${fmtEurM2(computed.sell_price_eur_m2 || 0)}</div>
      </div>`;
  }

  /** Texte d'équivalence sous le champ transport : montant €/m² et % du prix. */
  function transportEqText(computed) {
    if (!computed || !computed.breakdown) {
      return "Le transport s'ajoute au prix d'achat avant conversion.";
    }
    const b = computed.breakdown;
    const eur = parseFloat(b.transport_eur_m2 || 0);
    const pct = parseFloat(b.transport_pct_effective || 0);
    if (!eur && !pct) return "Aucun transport imputé pour l'instant.";
    return `Soit ${fmtEurM2(eur)} · ${fmtPct(pct)} du prix d'achat`;
  }

  function updateTransportEquivalent() {
    const el = document.getElementById("transport-eq");
    if (el) el.textContent = transportEqText(S.matPreview);
  }

  function renderMaterialForm(isNew) {
    const f = S.formMaterial;
    const catOpts = S.categories
      .map((c) => `<option value="${c.id}" ${f.category_id === c.id ? "selected" : ""}>${escHtml(c.label)}</option>`)
      .join("");
    const supOpts =
      '<option value="">—</option>' +
      S.suppliers
        .map((s) => `<option value="${s.id}" ${String(f.supplier_id) === String(s.id) ? "selected" : ""}>${escHtml(s.name)}</option>`)
        .join("");
    const hist = (f._history || [])
      .map(
        (h) =>
          `<tr><td>${escHtml(h.effective_date)}</td><td>${fmt4(h.unit_price)} ${escHtml(h.price_currency)}</td><td>${escHtml(h.source || "—")}</td></tr>`
      )
      .join("");
    const unit = unitLabel(f.price_currency, f.price_basis);
    const isPct = f.transport_mode === "PCT";

    setContent(`
      <div class="pr-narrow">
        ${pageHead(
          isNew ? "Nouvelle matière" : "Éditer matière",
          isNew ? "" : escHtml(f.name),
          '<button type="button" class="btn btn-accent" id="btn-back-mat">Retour liste</button>'
        )}
        <div class="mat-summary" id="mat-summary">${matSummaryHtml(S.matPreview)}</div>
        <div class="form-card form-compact">
          <div class="form-section"><h3>Identification</h3>
            <div class="field"><label>Nom</label><input id="f-name" value="${escAttr(f.name)}"/></div>
            <div class="field-row">
              <div class="field f-mid"><label>Appellation</label><input id="f-app" value="${escAttr(f.appellation_code)}"/></div>
              <div class="field f-mid"><label>Catégorie</label><select id="f-cat">${catOpts}</select></div>
            </div>
            <div class="field-row ident-row">
              <div class="field f-mid"><label>Fournisseur</label><select id="f-sup">${supOpts}</select></div>
              ${inlineSettingsHtml()}
            </div>
          </div>

          <div class="form-section"><h3>Prix d'achat</h3>
            <div class="field-row">
              <div class="field f-mid"><label>Devise achat</label><select id="f-cur">
                <option value="EUR" ${f.price_currency==="EUR"?"selected":""}>EUR — euro (€)</option>
                <option value="USD" ${f.price_currency==="USD"?"selected":""}>USD — dollar américain ($)</option>
              </select></div>
              <div class="field"><label>Base de prix</label><select id="f-basis">
                <option value="PER_KG" ${f.price_basis==="PER_KG"?"selected":""}>${escHtml(BASIS_LABEL.PER_KG)}</option>
                <option value="PER_M2" ${f.price_basis==="PER_M2"?"selected":""}>${escHtml(BASIS_LABEL.PER_M2)}</option>
              </select></div>
            </div>
            <div class="field-row">
              <div class="field f-num"><label>Prix unitaire <span class="lbl-unit">${escHtml(unit)}</span></label><input type="number" step="0.0001" id="f-unit" value="${escAttr(f.unit_price)}"/></div>
              <div class="field f-num"><label>Incidence taxes <span class="lbl-unit">multiplicateur</span></label><input type="number" step="0.0001" id="f-tax" value="${escAttr(f.tax_incidence)}"/>
                <div class="field-hint">1 = neutre · 1,05 = +5 % · 0,95 = −5 %</div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="import-block${f.is_imported ? " on" : ""}" id="import-block">
              <label class="check-row">
                <input type="checkbox" id="f-imp" ${f.is_imported?"checked":""}/>
                <span>
                  <span class="check-title">Matière importée</span>
                  <span class="check-sub">Un coût de transport s'ajoute au prix d'achat avant conversion.</span>
                </span>
              </label>
              <div id="import-fields" class="import-fields" style="${f.is_imported?"":"display:none"}">
                <div class="field-row">
                  <div class="field f-mid"><label>Mode de transport</label><select id="f-tmode">
                    <option value="AMOUNT" ${isPct?"":"selected"}>Montant — saisi en ${escHtml(unit)}</option>
                    <option value="PCT" ${isPct?"selected":""}>Pourcentage du prix d'achat</option>
                  </select></div>
                  <div class="field f-num"><label>Transport <span class="lbl-unit">${isPct ? "% du prix d'achat" : escHtml(unit)}</span></label>
                    <input type="number" step="0.0001" id="f-transport" value="${escAttr(isPct ? f.transport_pct : f.transport_unit_price)}"/>
                    <div class="field-hint" id="transport-eq">${transportEqText(S.matPreview)}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="form-section" id="carac-section" style="${needsWeight(f)?"":"display:none"}"><h3>Caractéristiques</h3>
            <div class="field-row">
              <div class="field f-num"><label>Poids <span class="lbl-unit">kg/m²</span></label><input type="number" step="0.0001" id="f-wm2" value="${escAttr(f.weight_per_m2)}"/></div>
              <div class="field f-num"><label>Grammage <span class="lbl-unit">g/m²</span></label><input type="number" id="f-gsm" value="${escAttr(f.weight_gsm)}"/>
                <div class="field-hint">Renseigné seul, il remplit le poids (g/m² ÷ 1000).</div>
              </div>
            </div>
          </div>

          ${S.canWrite ? `<div class="form-actions">
            <button type="button" class="btn btn-accent" id="btn-save-mat">Enregistrer</button>
            ${!isNew ? '<button type="button" class="btn btn-danger" id="btn-del-mat">Supprimer</button>' : ""}
          </div>` : ""}
        </div>

        <div id="mat-recap">${recapTableHtml(S.matPreview)}</div>

        ${!isNew && hist ? `<div class="form-card" style="margin-top:16px"><div class="form-section" style="margin:0"><h3>Historique prix (10 derniers)</h3><div class="table-wrap"><table class="pr-table"><thead><tr><th>Date</th><th>Prix</th><th>Source</th></tr></thead><tbody>${hist}</tbody></table></div></div></div>` : ""}
      </div>
    `);

    document.getElementById("btn-back-mat").onclick = () => navigate("/pricing/materials");
    bindInlineSettings(isNew);

    const bindPreview = () => {
      clearTimeout(S.debounceMat);
      S.debounceMat = setTimeout(refreshMaterialPreview, 300);
    };
    ["f-unit", "f-wm2", "f-tax", "f-transport"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.oninput = () => {
        syncMaterialFormFromDom();
        bindPreview();
      };
    });
    const gsm = document.getElementById("f-gsm");
    if (gsm) {
      gsm.oninput = () => {
        const g = parseFloat(gsm.value);
        const wEl = document.getElementById("f-wm2");
        if (wEl && !Number.isNaN(g) && (!parseFloat(wEl.value) || wEl.dataset.auto === "1")) {
          wEl.value = String(Math.round((g / 1000) * 10000) / 10000);
          wEl.dataset.auto = "1";
        }
        syncMaterialFormFromDom();
        bindPreview();
      };
    }
    ["f-cur", "f-basis", "f-imp", "f-tmode"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.onchange = () => {
        syncMaterialFormFromDom();
        renderMaterialForm(isNew);
        refreshMaterialPreview();
      };
    });

    if (S.canWrite) {
      document.getElementById("btn-save-mat").onclick = () => saveMaterialForm(isNew);
      const delBtn = document.getElementById("btn-del-mat");
      if (delBtn) {
        delBtn.onclick = async () => {
          const ok = await confirmDelete("Désactiver cette matière ? Elle ne sera plus utilisée dans les calculs.");
          if (!ok) return;
          try {
            await api("/api/pricing/materials/" + S.route.id, { method: "DELETE" });
            showToast("Matière désactivée.", "success");
            navigate("/pricing/materials");
          } catch (e) {
            showToast(e.message, "danger");
          }
        };
      }
    }
    if (!S.matPreview) refreshMaterialPreview();
  }

  function syncMaterialFormFromDom() {
    const f = S.formMaterial;
    const val = (id) => {
      const el = document.getElementById(id);
      return el ? el.value : null;
    };
    f.name = val("f-name") ?? f.name;
    f.appellation_code = val("f-app") ?? f.appellation_code;
    const cat = val("f-cat");
    if (cat != null) f.category_id = parseInt(cat, 10);
    f.supplier_id = val("f-sup") ?? f.supplier_id;
    f.price_currency = val("f-cur") ?? f.price_currency;
    f.price_basis = val("f-basis") ?? f.price_basis;
    f.unit_price = val("f-unit") ?? f.unit_price;
    f.tax_incidence = val("f-tax") ?? f.tax_incidence;
    const imp = document.getElementById("f-imp");
    if (imp) f.is_imported = imp.checked;
    const mode = val("f-tmode");
    if (mode) f.transport_mode = mode;
    const tv = val("f-transport");
    if (tv != null) {
      if (f.transport_mode === "PCT") f.transport_pct = tv;
      else f.transport_unit_price = tv;
    }
    f.weight_per_m2 = val("f-wm2") ?? f.weight_per_m2;
    f.weight_gsm = val("f-gsm") ?? f.weight_gsm;
  }

  async function saveMaterialForm(isNew) {
    syncMaterialFormFromDom();
    const f = S.formMaterial;
    const body = {
      name: f.name.trim(),
      appellation_code: f.appellation_code.trim(),
      category_id: f.category_id,
      supplier_id: f.supplier_id ? parseInt(f.supplier_id, 10) : null,
      weight_per_m2: parseFloat(f.weight_per_m2) || 0,
      weight_gsm: f.weight_gsm ? parseInt(f.weight_gsm, 10) : null,
      price_currency: f.price_currency,
      unit_price: parseFloat(f.unit_price) || 0,
      price_basis: f.price_basis,
      tax_incidence: parseFloat(f.tax_incidence) || 1,
      is_imported: !!f.is_imported,
      transport_mode: f.transport_mode || "AMOUNT",
      transport_unit_price: parseFloat(f.transport_unit_price) || 0,
      transport_pct: parseFloat(f.transport_pct) || 0,
      price_history_source: "Saisie interface",
    };
    if (!body.name) {
      showToast("Nom requis.", "danger");
      return;
    }
    if (body.price_basis === "PER_KG" && !(body.weight_per_m2 > 0)) {
      showToast("Poids kg/m² requis : le prix est saisi au kilo.", "danger");
      return;
    }
    try {
      if (isNew) {
        const r = await api("/api/pricing/materials", { method: "POST", body });
        showToast("Matière créée.", "success");
        navigate("/pricing/materials/" + r.id);
      } else {
        await api("/api/pricing/materials/" + S.route.id, { method: "PATCH", body });
        showToast("Matière enregistrée.", "success");
        await loadMaterialForm(S.route.id);
        renderMaterialForm(false);
      }
    } catch (e) {
      showToast(e.message, "danger");
    }
  }

  async function openMaterialDrawer(id) {
    const m = await api("/api/pricing/materials/" + id);
    const root = document.getElementById("modal-root");
    root.innerHTML = `
      <div class="drawer-backdrop" id="dw-back"></div>
      <div class="drawer">
        <h2 style="margin:0 0 12px">${escHtml(m.name)}</h2>
        <p style="color:var(--muted);font-size:13px">${categoryBadge(m.category_code)} · ${escHtml(m.appellation_code)}</p>
        <p style="margin:16px 0"><strong>${m.computed ? fmtEurM2(m.computed.price_eur_per_m2) : "—"}</strong></p>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn btn-soft btn-sm" id="dw-hist">Historique</button>
          ${S.canWrite ? `<button type="button" class="btn btn-accent btn-sm" id="dw-edit">Éditer</button>` : ""}
        </div>
      </div>`;
    document.getElementById("dw-back").onclick = () => (root.innerHTML = "");
    document.getElementById("dw-hist").onclick = () => {
      root.innerHTML = "";
      openPriceHistoryModal(id);
    };
    const ed = document.getElementById("dw-edit");
    if (ed) ed.onclick = () => navigate("/pricing/materials/" + id);
  }

  function drawHistoryChart(canvas, history) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const pts = history.slice().reverse();
    if (pts.length < 2) {
      ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--muted") || "#94a3b8";
      ctx.font = "13px sans-serif";
      ctx.fillText("Historique insuffisant", 20, h / 2);
      return;
    }
    const vals = pts.map((p) => parseFloat(p.unit_price));
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = 24;
    const range = max - min || 1;
    ctx.strokeStyle = getComputedStyle(document.body).getPropertyValue("--accent") || "#22d3ee";
    ctx.lineWidth = 2;
    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = pad + (i / (pts.length - 1)) * (w - pad * 2);
      const y = h - pad - ((parseFloat(p.unit_price) - min) / range) * (h - pad * 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  async function openPriceHistoryModal(materialId) {
    const h = await api("/api/pricing/materials/" + materialId + "/history");
    const history = h.history || [];
    const rows = history
      .map(
        (x) =>
          `<tr><td>${escHtml(x.effective_date)}</td><td>${fmt4(x.unit_price)} ${currencyBadge(x.price_currency)}</td><td>${fmt4(x.tax_incidence)}</td><td>${escHtml(x.source || "—")}</td></tr>`
      )
      .join("");
    const root = document.getElementById("modal-root");
    root.innerHTML = `
      <div class="modal-backdrop" id="modal-back">
        <div class="modal">
          <h2>Historique des prix</h2>
          <canvas class="history-chart" id="hist-canvas" width="560" height="200"></canvas>
          <table class="pr-table"><thead><tr><th>Date</th><th>Prix</th><th>Taxe</th><th>Source</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" class="empty">Aucun historique</td></tr>'}</tbody></table>
          <button type="button" class="btn btn-soft" style="margin-top:12px" id="modal-close">Fermer</button>
        </div>
      </div>`;
    document.getElementById("modal-back").onclick = (e) => {
      if (e.target.id === "modal-back") root.innerHTML = "";
    };
    document.getElementById("modal-close").onclick = () => (root.innerHTML = "");
    const canvas = document.getElementById("hist-canvas");
    if (canvas) drawHistoryChart(canvas, history);
  }

  async function loadProductsList() {
    const params = new URLSearchParams();
    params.set("with_cost", "true");
    params.set("active_only", "true");
    if (S.filters.prodQ) params.set("q", S.filters.prodQ);
    const data = await api("/api/pricing/products?" + params.toString());
    S.products = data.products || [];
  }

  function matLabel(id, matMap) {
    if (!id) return '<span style="color:var(--muted)">—</span>';
    const m = matMap[id];
    if (m) return escHtml(m.appellation_code || m.name);
    return "#" + id;
  }

  async function loadAllMaterialsLookup() {
    const data = await api("/api/pricing/materials?active_only=false&with_computed=true");
    const map = {};
    (data.materials || []).forEach((m) => {
      map[m.id] = m;
    });
    return map;
  }

  async function renderProductsList() {
    const matMap = await loadAllMaterialsLookup();
    const rows = S.products
      .map((p) => {
        const c = p.cost;
        const total = c ? fmtEurM2(c.total_eur_per_m2) : "—";
        const sell = c ? fmtEurM2(c.sell_price_eur_m2) : "—";
        const margin = c ? fmtEurM2(c.margin_eur_m2) : "—";
        const checked = S.selectedProductIds.has(p.id) ? " checked" : "";
        return `<tr data-pid="${p.id}">
          <td onclick="event.stopPropagation()"><input type="checkbox" class="prod-sel" data-pid="${p.id}"${checked} aria-label="Sélectionner"/></td>
          <td><strong>${escHtml(p.code)}</strong></td>
          <td>${escHtml(p.name)}</td>
          <td>${matLabel(p.frontal_id, matMap)}</td>
          <td>${matLabel(p.adhesif_id, matMap)}</td>
          <td>${matLabel(p.silicone_id, matMap)}</td>
          <td>${matLabel(p.glassine_id, matMap)}</td>
          <td>${total}</td>
          <td>${sell}</td>
          <td>${margin}</td>
          <td class="row-actions" onclick="event.stopPropagation()">
            <button type="button" class="btn btn-soft btn-sm" data-dup="${p.id}">Dupliquer</button>
            <button type="button" class="btn btn-soft btn-sm" data-xls="${p.id}">Excel</button>
            <button type="button" class="btn btn-soft btn-sm" data-pdf="${p.id}">PDF</button>
            ${S.canWrite ? `<button type="button" class="btn btn-soft btn-sm" data-edit-p="${p.id}">Éditer</button>` : ""}
          </td>
        </tr>`;
      })
      .join("");

    const prodEmpty =
      !S.products.length && !S.filters.prodQ
        ? `<div class="empty-state">
            <p>Aucun produit enregistré.</p>
            ${S.canWrite ? '<button type="button" class="btn btn-accent" id="empty-new-prod">Créer le premier produit</button>' : ""}
          </div>`
        : "";

    setContent(`
      ${pageHead(
        "Produits",
        `${S.products.length} produit(s)`,
        S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-new-prod">+ Nouveau produit</button>' : ""
      )}
      <div class="filters">
        <input type="search" class="search-input" id="prod-q" placeholder="Rechercher (code, nom…)" value="${escAttr(S.filters.prodQ)}"/>
        <button type="button" class="btn btn-accent" id="prod-export-sel">Exporter sélection (Excel)</button>
        <button type="button" class="btn btn-soft" id="prod-export-all">Exporter liste CSV</button>
      </div>
      ${prodEmpty}
      <div class="table-wrap" ${prodEmpty ? 'style="display:none"' : ""}>
        <table class="pr-table">
          <thead><tr><th style="width:36px"><input type="checkbox" id="prod-sel-all" title="Tout sélectionner"/></th><th>Code</th><th>Nom</th><th>Frontal</th><th>Adh.</th><th>Sil.</th><th>Glass.</th><th>Coût</th><th>Vente</th><th>Marge</th><th></th></tr></thead>
          <tbody>${rows || '<tr><td colspan="11" class="empty">Aucun résultat pour ce filtre</td></tr>'}</tbody>
        </table>
      </div>
    `);

    document.getElementById("prod-q").oninput = (e) => {
      clearTimeout(S.debounceProd);
      S.debounceProd = setTimeout(async () => {
        S.filters.prodQ = e.target.value;
        await loadProductsList();
        renderProductsList();
      }, 300);
    };
    document.querySelectorAll("[data-edit-p]").forEach((b) => {
      b.onclick = () => navigate("/pricing/products/" + b.getAttribute("data-edit-p"));
    });
    document.querySelectorAll("tbody tr[data-pid]").forEach((tr) => {
      tr.onclick = () => navigate("/pricing/products/" + tr.getAttribute("data-pid"));
    });
    document.querySelectorAll("[data-dup]").forEach((b) => {
      b.onclick = async (ev) => {
        ev.stopPropagation();
        const p = S.products.find((x) => String(x.id) === b.getAttribute("data-dup"));
        if (!p) return;
        S.formProduct = {
          code: p.code + "-copie",
          name: p.name + " (copie)",
          frontal_id: p.frontal_id,
          adhesif_id: p.adhesif_id,
          silicone_id: p.silicone_id,
          glassine_id: p.glassine_id,
          extra_material_ids: [...(p.extra_material_ids || [])],
          custom_margin_pct: p.custom_margin_pct != null ? String(p.custom_margin_pct) : "",
        };
        navigate("/pricing/products/new");
        await bootRoute();
      };
    });
    document.querySelectorAll(".prod-sel").forEach((cb) => {
      cb.onchange = () => {
        const id = parseInt(cb.getAttribute("data-pid"), 10);
        if (cb.checked) S.selectedProductIds.add(id);
        else S.selectedProductIds.delete(id);
      };
    });
    const selAll = document.getElementById("prod-sel-all");
    if (selAll) {
      selAll.onchange = () => {
        const on = selAll.checked;
        document.querySelectorAll(".prod-sel").forEach((cb) => {
          cb.checked = on;
          const id = parseInt(cb.getAttribute("data-pid"), 10);
          if (on) S.selectedProductIds.add(id);
          else S.selectedProductIds.delete(id);
        });
      };
    }
    document.getElementById("prod-export-sel").onclick = () => exportProductsExcel();
    document.querySelectorAll("[data-xls]").forEach((b) => {
      b.onclick = (ev) => {
        ev.stopPropagation();
        exportProductsExcel([parseInt(b.getAttribute("data-xls"), 10)]);
      };
    });
    document.querySelectorAll("[data-pdf]").forEach((b) => {
      b.onclick = (ev) => {
        ev.stopPropagation();
        downloadProductPdf(b.getAttribute("data-pdf"));
      };
    });
    document.getElementById("prod-export-all").onclick = exportAllProductsCsv;
    const btnNew = document.getElementById("btn-new-prod");
    if (btnNew) btnNew.onclick = () => navigate("/pricing/products/new");
    const emptyProd = document.getElementById("empty-new-prod");
    if (emptyProd) emptyProd.onclick = () => navigate("/pricing/products/new");
  }

  function exportAllProductsCsv() {
    const header = ["code", "nom", "cout_eur_m2", "vente_eur_m2", "marge"];
    const lines = S.products.map((p) => {
      const c = p.cost || {};
      return [p.code, p.name, c.total_eur_per_m2, c.sell_price_eur_m2, c.margin_eur_m2]
        .map((x) => `"${String(x ?? "").replace(/"/g, '""')}"`)
        .join(";");
    });
    downloadCsv("produits-couts.csv", [header.join(";"), ...lines].join("\n"));
    showToast("Export CSV téléchargé.", "success");
  }

  function exportProductCsv(id) {
    const p = S.products.find((x) => String(x.id) === String(id));
    if (!p || !p.cost) return;
    const c = p.cost;
    const lines = [
      "code;nom;role;prix_eur_m2;part_pct",
      ...c.components.map((x) =>
        [p.code, p.name, x.role, x.price_eur_per_m2, x.share_pct].join(";")
      ),
      `;;total;${c.total_eur_per_m2};`,
      `;;marge;${c.margin_eur_m2};`,
      `;;vente;${c.sell_price_eur_m2};`,
    ];
    downloadCsv(`produit-${p.code}.csv`, lines.join("\n"));
    showToast("Export CSV produit.", "success");
  }

  function downloadCsv(filename, content) {
    const blob = new Blob(["\ufeff" + content], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function _filenameFromDisposition(res, fallback) {
    const cd = res.headers.get("Content-Disposition") || "";
    const m = /filename="?([^";\n]+)"?/i.exec(cd);
    return m ? m[1].trim() : fallback;
  }

  async function downloadBlobResponse(res, fallbackName) {
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = _filenameFromDisposition(res, fallbackName);
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function downloadProductPdf(productId) {
    try {
      const res = await fetch("/api/pricing/products/" + productId + "/export/pdf", {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        let msg = "Export PDF impossible.";
        try {
          const j = await res.json();
          msg = j.detail || msg;
        } catch (e) {}
        throw new Error(typeof msg === "string" ? msg : "Export PDF impossible.");
      }
      await downloadBlobResponse(res, "fiche-produit.pdf");
      showToast("PDF téléchargé.", "success");
    } catch (e) {
      showToast(e.message, "danger");
    }
  }

  async function exportProductsExcel(ids) {
    const list = ids && ids.length ? ids : Array.from(S.selectedProductIds);
    if (!list.length) {
      showToast("Sélectionnez au moins un produit.", "info");
      return;
    }
    try {
      const res = await fetch(
        "/api/pricing/products/export.xlsx?ids=" + encodeURIComponent(list.join(",")),
        { credentials: "include" }
      );
      if (!res.ok) {
        let msg = "Export Excel impossible.";
        try {
          const j = await res.json();
          msg = j.detail || msg;
        } catch (e) {}
        throw new Error(typeof msg === "string" ? msg : "Export Excel impossible.");
      }
      await downloadBlobResponse(res, "produits-couts.xlsx");
      showToast("Export Excel téléchargé.", "success");
    } catch (e) {
      showToast(e.message, "danger");
    }
  }

  function defaultProductForm() {
    return (
      S.formProduct || {
        code: "",
        name: "",
        frontal_id: "",
        adhesif_id: "",
        silicone_id: "",
        glassine_id: "",
        extra_material_ids: [],
        custom_margin_pct: "",
      }
    );
  }

  async function loadProductForm(id) {
    if (!id) {
      S.formProduct = defaultProductForm();
      S.prodPreview = null;
      return;
    }
    const p = await api("/api/pricing/products/" + id);
    S.formProduct = {
      code: p.code,
      name: p.name,
      frontal_id: p.frontal_id || "",
      adhesif_id: p.adhesif_id || "",
      silicone_id: p.silicone_id || "",
      glassine_id: p.glassine_id || "",
      extra_material_ids: p.extra_material_ids || [],
      custom_margin_pct: p.custom_margin_pct != null ? String(p.custom_margin_pct) : "",
    };
    S.prodPreview = p.cost || null;
  }

  async function loadMaterialsForCombos() {
    const data = await api("/api/pricing/materials?active_only=true&with_computed=true");
    S.materials = data.materials || [];
  }

  function materialsForCategory(code) {
    return S.materials.filter((m) => m.category_code === code && m.is_active);
  }

  function materialComboboxHtml(fieldId, categoryCode, selectedId) {
    const mats = materialsForCategory(categoryCode);
    const sel = mats.find((m) => String(m.id) === String(selectedId));
    const label = sel
      ? `${sel.appellation_code} — ${fmtEurM2(sel.computed?.price_eur_per_m2 || "?")}`
      : "— Choisir —";
    return `
      <div class="field combobox-wrap" data-mcb="${escAttr(fieldId)}" data-cat="${escAttr(categoryCode)}">
        <label>${escHtml(categoryCode.charAt(0) + categoryCode.slice(1).toLowerCase())}</label>
        <input type="hidden" id="${fieldId}" value="${escAttr(selectedId || "")}"/>
        <input type="text" class="mcb-search" placeholder="Rechercher…" autocomplete="off" value="${sel ? escAttr(sel.appellation_code) : ""}"/>
        <div class="combobox-list" style="display:none"></div>
        <div class="sub" style="font-size:11px;color:var(--muted);margin-top:4px">${escHtml(label)}</div>
      </div>`;
  }

  function bindMaterialComboboxes() {
    document.querySelectorAll("[data-mcb]").forEach((wrap) => {
      const fieldId = wrap.getAttribute("data-mcb");
      const cat = wrap.getAttribute("data-cat");
      const hidden = document.getElementById(fieldId);
      const search = wrap.querySelector(".mcb-search");
      const list = wrap.querySelector(".combobox-list");
      const mats = materialsForCategory(cat);

      function renderList(q) {
        const t = (q || "").toLowerCase();
        const filtered = mats.filter((m) => {
          const blob = (m.name + " " + m.appellation_code).toLowerCase();
          return !t || blob.includes(t);
        });
        list.innerHTML = filtered
          .slice(0, 40)
          .map((m) => {
            const price = m.computed ? fmtEurM2(m.computed.price_eur_per_m2) : "?";
            return `<div class="combobox-item" data-id="${m.id}"><div>${escHtml(m.appellation_code)} · ${escHtml(m.name)}</div><div class="sub">${price}</div></div>`;
          })
          .join("");
        list.style.display = filtered.length ? "block" : "none";
        list.querySelectorAll(".combobox-item").forEach((item) => {
          item.onclick = () => {
            hidden.value = item.getAttribute("data-id");
            search.value = mats.find((x) => String(x.id) === hidden.value)?.appellation_code || "";
            list.style.display = "none";
            syncProductFormFromDom();
            refreshProductPreview();
          };
        });
      }

      search.onfocus = () => renderList(search.value);
      search.oninput = () => renderList(search.value);
      document.addEventListener("click", (e) => {
        if (!wrap.contains(e.target)) list.style.display = "none";
      });
    });
  }

  function productPreviewBody() {
    const f = S.formProduct;
    return {
      frontal_id: f.frontal_id ? parseInt(f.frontal_id, 10) : null,
      adhesif_id: f.adhesif_id ? parseInt(f.adhesif_id, 10) : null,
      silicone_id: f.silicone_id ? parseInt(f.silicone_id, 10) : null,
      glassine_id: f.glassine_id ? parseInt(f.glassine_id, 10) : null,
      extra_material_ids: f.extra_material_ids || [],
      custom_margin_pct: f.custom_margin_pct !== "" && f.custom_margin_pct != null
        ? parseFloat(f.custom_margin_pct)
        : null,
    };
  }

  async function refreshProductPreview() {
    const f = S.formProduct;
    if (!f) return;
    try {
      S.prodPreview = await api("/api/pricing/products/preview", {
        method: "POST",
        body: productPreviewBody(),
      });
      const el = document.getElementById("prod-recap");
      if (el) el.innerHTML = productRecapHtml(S.prodPreview);
    } catch (e) {
      const el = document.getElementById("prod-recap");
      if (el) el.innerHTML = `<div class="empty" style="color:var(--danger)">${escHtml(e.message)}</div>`;
    }
  }

  function productRecapHtml(cost) {
    if (!cost) return '<div class="empty">Sélectionnez les composants</div>';
    const comps = cost.components.map((c) => ({ ...c, price_eur_per_m2: c.price_eur_per_m2 }));
    return `
      <div class="big-label">Coût total</div>
      <div class="big-price">${fmtEurM2(cost.total_eur_per_m2)}</div>
      ${priceBreakdownHtml({ components: comps, total: cost.total_eur_per_m2 })}
      <div class="breakdown-legend" style="margin-top:14px">
        <div><span>Marge (${fmtNum(cost.margin_pct || 0, 2, 2)} %)</span><span>${fmtEurM2(cost.margin_eur_m2)}</span></div>
        <div><span>Prix de vente</span><span><strong>${fmtEurM2(cost.sell_price_eur_m2)}</strong></span></div>
      </div>`;
  }

  function renderProductForm(isNew) {
    const f = S.formProduct;
    const defMargin = S.settings ? fmtNum(S.settings.default_margin_pct, 2, 2) : "—";

    setContent(`
      ${pageHead(
        isNew ? "Nouveau produit" : "Éditer produit",
        "",
        '<button type="button" class="btn btn-accent" id="btn-back-prod">Retour liste</button>'
      )}
      <div class="form-grid">
        <div class="form-card">
          <div class="field-row">
            <div class="field"><label>Code</label><input id="p-code" value="${escAttr(f.code)}"/></div>
            <div class="field"><label>Nom</label><input id="p-name" value="${escAttr(f.name)}"/></div>
          </div>
          ${materialComboboxHtml("p-frontal", "FRONTAL", f.frontal_id)}
          ${materialComboboxHtml("p-adhesif", "ADHESIF", f.adhesif_id)}
          ${materialComboboxHtml("p-silicone", "SILICONE", f.silicone_id)}
          ${materialComboboxHtml("p-glassine", "GLASSINE", f.glassine_id)}
          <div class="field"><label>Marge personnalisée <span class="lbl-unit">% du prix de revient</span></label>
            <input type="number" step="0.01" id="p-margin" value="${escAttr(f.custom_margin_pct)}" placeholder="Défaut : ${escAttr(defMargin)} %"/>
            <div class="field-hint">Laisser vide pour appliquer la marge par défaut des paramètres.</div>
          </div>
          ${S.canWrite ? `<div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap">
            <button type="button" class="btn btn-accent" id="btn-save-prod">Enregistrer</button>
            <button type="button" class="btn btn-soft" id="btn-print-prod">Exporter PDF</button>
            ${!isNew ? '<button type="button" class="btn btn-danger" id="btn-del-prod">Supprimer</button>' : ""}
          </div>` : ""}
        </div>
        <div class="side-panel" id="prod-recap">${productRecapHtml(S.prodPreview)}</div>
      </div>
    `);

    document.getElementById("btn-back-prod").onclick = () => navigate("/pricing/products");
    bindMaterialComboboxes();
    document.getElementById("p-code").oninput =
      document.getElementById("p-name").oninput =
      document.getElementById("p-margin").oninput =
        () => {
          syncProductFormFromDom();
          clearTimeout(S.debounceProd);
          S.debounceProd = setTimeout(refreshProductPreview, 300);
        };

    if (S.canWrite) {
      document.getElementById("btn-save-prod").onclick = () => saveProductForm(isNew);
      document.getElementById("btn-print-prod").onclick = () => {
        if (!isNew && S.route.id) downloadProductPdf(S.route.id);
        else showToast("Enregistrez le produit avant export PDF.", "info");
      };
      const delProd = document.getElementById("btn-del-prod");
      if (delProd) {
        delProd.onclick = async () => {
          const ok = await confirmDelete("Désactiver ce produit ?");
          if (!ok) return;
          try {
            await api("/api/pricing/products/" + S.route.id, { method: "DELETE" });
            showToast("Produit désactivé.", "success");
            navigate("/pricing/products");
          } catch (e) {
            showToast(e.message, "danger");
          }
        };
      }
    }
    refreshProductPreview();
  }

  function syncProductFormFromDom() {
    const f = S.formProduct;
    f.code = document.getElementById("p-code").value;
    f.name = document.getElementById("p-name").value;
    f.frontal_id = document.getElementById("p-frontal").value;
    f.adhesif_id = document.getElementById("p-adhesif").value;
    f.silicone_id = document.getElementById("p-silicone").value;
    f.glassine_id = document.getElementById("p-glassine").value;
    f.custom_margin_pct = document.getElementById("p-margin").value;
  }

  async function saveProductForm(isNew) {
    syncProductFormFromDom();
    const f = S.formProduct;
    const body = {
      code: f.code.trim(),
      name: f.name.trim(),
      frontal_id: f.frontal_id ? parseInt(f.frontal_id, 10) : null,
      adhesif_id: f.adhesif_id ? parseInt(f.adhesif_id, 10) : null,
      silicone_id: f.silicone_id ? parseInt(f.silicone_id, 10) : null,
      glassine_id: f.glassine_id ? parseInt(f.glassine_id, 10) : null,
      extra_material_ids: f.extra_material_ids || [],
      custom_margin_pct: f.custom_margin_pct !== "" && f.custom_margin_pct != null
        ? parseFloat(f.custom_margin_pct)
        : null,
    };
    try {
      if (isNew) {
        const r = await api("/api/pricing/products", { method: "POST", body });
        showToast("Produit créé.", "success");
        navigate("/pricing/products/" + r.id);
      } else {
        await api("/api/pricing/products/" + S.route.id, { method: "PATCH", body });
        showToast("Produit enregistré.", "success");
        await loadProductForm(S.route.id);
        renderProductForm(false);
      }
    } catch (e) {
      showToast(e.message, e.status === 422 ? "danger" : "danger");
    }
  }

  function openSettingsModal() {
    if (!S.canWrite) return;
    const s = S.settings || {};
    const fxDate = s.eur_usd_rate_updated_at
      ? String(s.eur_usd_rate_updated_at).replace("T", " ").slice(0, 16)
      : "—";
    const fxStale = isFxStale(s.eur_usd_rate_updated_at);
    const root = document.getElementById("modal-root");
    root.innerHTML = `
      <div class="modal-backdrop" id="set-back">
        <div class="modal" id="set-modal" style="max-width:520px">
          <div class="modal-head">
            <h2>Paramètres</h2>
            <button type="button" class="icon-btn" id="set-close" aria-label="Fermer">×</button>
          </div>
          <div class="field"><label>Taux USD → EUR ${fxStale ? fxStaleBadgeHtml() : ""}</label>
            <input type="number" step="0.0001" id="s-rate" value="${escAttr(s.eur_usd_rate)}"/>
            <div class="field-hint">1 USD = ce montant en euros · Source : ${escHtml(s.eur_usd_rate_source || "—")} · MAJ : ${escHtml(fxDate)}</div>
          </div>
          <div class="field"><label>Marge par défaut <span class="lbl-unit">% du prix de revient</span></label>
            <input type="number" step="0.01" id="s-margin" value="${escAttr(s.default_margin_pct)}"/>
            <div class="field-hint">Appliquée à tous les produits sans marge personnalisée.</div>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-accent" id="s-save">Enregistrer</button>
            <button type="button" class="btn btn-soft" id="s-fx">Rafraîchir le taux</button>
            <button type="button" class="btn btn-soft" id="s-cancel">Annuler</button>
          </div>
        </div>
      </div>`;

    const close = () => {
      root.innerHTML = "";
    };
    document.getElementById("set-back").onclick = (e) => {
      if (e.target.id === "set-back") close();
    };
    document.getElementById("set-close").onclick = close;
    document.getElementById("s-cancel").onclick = close;
    document.getElementById("s-save").onclick = async () => {
      try {
        S.settings = await api("/api/pricing/settings", {
          method: "PATCH",
          body: {
            eur_usd_rate: parseFloat(document.getElementById("s-rate").value),
            default_margin_pct: parseFloat(document.getElementById("s-margin").value),
          },
        });
        showToast("Paramètres enregistrés.", "success");
        close();
        await bootRoute();
      } catch (e) {
        showToast(e.message, "danger");
      }
    };
    document.getElementById("s-fx").onclick = async () => {
      try {
        const r = await api("/api/pricing/settings/refresh-fx", { method: "POST" });
        showToast("Taux mis à jour : " + fmtNum(r.eur_usd_rate, 4, 4), "success");
        S.settings = await api("/api/pricing/settings");
        openSettingsModal();
      } catch (e) {
        showToast(e.message, "danger");
      }
    };
  }

  async function bootRoute() {
    S.route = parseRoute();
    renderSidebar();
    showLoading();
    try {
      if (!S.categories.length) await loadBaseData();

      const r = S.route.name;
      if (r === "dashboard") await renderDashboard();
      else if (r === "materials") {
        await loadMaterialsList();
        renderMaterialsList();
      } else if (r === "material-new") {
        if (!S.canWrite) {
          navigate("/pricing/materials");
          return;
        }
        await loadMaterialForm(null);
        renderMaterialForm(true);
      } else if (r === "material-edit") {
        await loadMaterialForm(S.route.id);
        renderMaterialForm(false);
      } else if (r === "products") {
        await loadProductsList();
        await renderProductsList();
      } else if (r === "product-new") {
        if (!S.canWrite) {
          navigate("/pricing/products");
          return;
        }
        await loadMaterialsForCombos();
        if (!S.formProduct) await loadProductForm(null);
        renderProductForm(true);
      } else if (r === "product-edit") {
        await loadMaterialsForCombos();
        await loadProductForm(S.route.id);
        renderProductForm(false);
      } else if (r === "settings") {
        if (!S.canWrite) {
          navigate("/pricing");
          return;
        }
        await renderDashboard();
        openSettingsModal();
      } else await renderDashboard();
    } catch (e) {
      setContent(`<div class="empty" style="color:var(--danger);padding:24px">${escHtml(e.message)}</div>`);
      if (e.status === 401) window.location.href = "/?next=" + encodeURIComponent(window.location.pathname);
    }
  }

  function initChrome() {
    document.getElementById("btn-portal").onclick = () => {
      window.location.href = "/";
    };
    document.getElementById("theme-btn").onclick = () => {
      if (window.MySifaTheme) MySifaTheme.toggleMode();
      else document.body.classList.toggle("light");
      updateChromeControls();
    };
    document.getElementById("logout-btn").onclick = async () => {
      try {
        await api("/api/auth/logout", { method: "POST" });
      } catch (e) {}
      window.location.href = "/";
    };
    document.getElementById("mobile-menu-btn").onclick = () => document.body.classList.toggle("sb-open");
    document.getElementById("sidebar-overlay").onclick = () => document.body.classList.remove("sb-open");
    updateChromeControls();
  }

  async function initApp() {
    initChrome();
    try {
      const me = await api("/api/auth/me");
      if (me && me.id) {
        S.user = {
          id: me.id,
          nom: me.nom || "",
          role: me.role || "",
          avatar_url: me.avatar_url || "",
        };
        if (window.MySifaTheme) MySifaTheme.mergeFromUser(me);
      }
    } catch (e) {
      if (e.status === 401) {
        window.location.href = "/?next=" + encodeURIComponent(window.location.pathname);
        return;
      }
    }
    updateChromeControls();
    S.route = parseRoute();
    await bootRoute();
  }

  window.addEventListener("popstate", bootRoute);
  document.addEventListener("DOMContentLoaded", () => {
    initApp();
  });
})();
