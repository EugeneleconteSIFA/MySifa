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
    route: { name: "materials", id: null },
    loading: true,
    categories: [],
    suppliers: [],
    supplierMap: {},
    fournisseurs: [],
    fournisseurMap: {},
    materials: [],
    materialsAll: [],
    mystock: [],
    mystockAll: [],
    mystockCats: [],
    laizes: [],
    grammages: [],
    expanded: {},
    // Fiche de paramétrage d'une déclinaison MyStock (route /pricing/mystock/:id).
    declForm: null,
    declPreview: null,
    declDirty: false,
    products: [],
    settings: null,
    filters: {
      matQ: "",
      matCats: [],
      matSupplier: "",
      matActive: "1",
      // MyStock est la source des prix : c'est la vue qu'on veut par défaut.
      matTab: "mystock",
      msQ: "",
      msCat: "",
      msActive: "1",
      prodQ: "",
      // Onglet actif de la page Produits : base Coûts matières ou MyStock.
      prodTab: "mystock",
      msProdQ: "",
    },
    msDecls: [],
    msProducts: [],
    expandedProd: {},
    formMsProduct: null,
    msProdPreview: null,
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
      trash:
        '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
      copy:
        '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
      plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
      link:
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
      unlink:
        '<path d="M18.84 12.25l1.72-1.71a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M5.17 11.75l-1.71 1.71a5 5 0 0 0 7.07 7.07l1.71-1.71"/><line x1="8" y1="2" x2="8" y2="5"/><line x1="2" y1="8" x2="5" y2="8"/><line x1="16" y1="19" x2="16" y2="22"/><line x1="19" y1="16" x2="22" y2="16"/>',
      "arrow-left":
        '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
      star:
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
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

  /**
   * Contrepartie du prix d'achat dans l'AUTRE devise.
   * Le taux stocké est un USD → EUR (1 USD = taux €) : on multiplie pour aller
   * du dollar vers l'euro, on divise dans l'autre sens.
   */
  function otherCurrencyPrice(value, currency, basis) {
    const rate = parseFloat((S.settings && S.settings.eur_usd_rate) || 0);
    const v = parseFloat(value);
    if (!rate || rate <= 0 || Number.isNaN(v)) return null;
    const cur = (currency || "EUR").toUpperCase();
    const other = cur === "USD" ? "EUR" : "USD";
    const converted = cur === "USD" ? v * rate : v / rate;
    return { value: converted, currency: other, label: fmtCur(converted, other) + "/" + (basis === "PER_M2" ? "m²" : "kg") };
  }

  function otherPriceHtml(value, currency, basis) {
    const o = otherCurrencyPrice(value, currency, basis);
    if (!o) return '<div class="price-alt muted">taux non renseigné</div>';
    return `<div class="price-alt">${escHtml(o.label)}</div>`;
  }

  /** Le poids au m² n'est utile que si le prix est au kilo ou pour la calculette import. */
  // Perte matière par défaut, alignée sur mystock_prix.PERTE_DEFAUT.
  const PERTE_DEFAUT = 9;

  /**
   * Poids au m² (kg) réellement consommé : le grammage majoré de la perte.
   * On produit rarement au gramme près — chute et calage font qu'un frontal de
   * 70 g/m² en consomme davantage. C'est ce poids qui entre dans le calcul.
   */
  function poidsRetenu(grammageGsm, pertePct) {
    const g = parseFloat(grammageGsm) || 0;
    const p = parseFloat(pertePct) || 0;
    return Math.round(g * (1 + p / 100) * 1000) / 1e6;
  }

  function grammageRetenu(grammageGsm, pertePct) {
    const g = parseFloat(grammageGsm) || 0;
    const p = parseFloat(pertePct) || 0;
    return Math.round(g * (1 + p / 100) * 100) / 100;
  }

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
    // Plus de tableau de bord : /pricing ouvre directement les matières.
    if (parts.length <= 1 || parts[0] !== "pricing") {
      return { name: "materials", id: null };
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
    if (seg === "mystock") {
      if (parts[2] === "produit") {
        if (parts[3] === "new") return { name: "msproduct-new", id: null };
        if (parts[3] && /^\d+$/.test(parts[3])) return { name: "msproduct-edit", id: parts[3] };
        return { name: "products", id: null };
      }
      if (parts[2] && /^\d+$/.test(parts[2])) return { name: "mystock-edit", id: parts[2] };
    }
    if (seg === "settings") return { name: "settings", id: null };
    return { name: "materials", id: null };
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
      materials: ["Matières", "Liste"],
      "material-new": ["Matière", "Nouvelle"],
      "material-edit": ["Matière", "Édition"],
      products: ["Produits", "Liste"],
      "product-new": ["Produit", "Nouveau"],
      "product-edit": ["Produit", "Édition"],
      settings: ["Paramètres", "Coûts matières"],
    };
    const t = titles[active] || titles.materials;
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
    const [cats, sups, fourn, settings] = await Promise.all([
      api("/api/pricing/categories"),
      api("/api/pricing/suppliers?active_only=false"),
      api("/api/pricing/fournisseurs"),
      api("/api/pricing/settings"),
    ]);
    S.fournisseurs = fourn.fournisseurs || [];
    S.fournisseurMap = {};
    S.fournisseurs.forEach((f) => {
      S.fournisseurMap[f.id] = f.nom;
    });
    S.categories = cats.categories || [];
    S.suppliers = sups.suppliers || [];
    S.supplierMap = {};
    S.suppliers.forEach((s) => {
      S.supplierMap[s.id] = s.name;
    });
    S.settings = settings;
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
      S.fournisseurs
        .map(
          (s) =>
            `<option value="${s.id}" ${String(S.filters.matSupplier) === String(s.id) ? "selected" : ""}>${escHtml(s.nom)}</option>`
        )
        .join("");

    const rows = S.materials
      .map((m) => {
        const sup =
          m.fournisseur_nom ||
          (m.fournisseur_fsc_id ? S.fournisseurMap[m.fournisseur_fsc_id] : null) ||
          (m.supplier_id ? S.supplierMap[m.supplier_id] : null) ||
          "—";
        const live = m.computed ? fmtEurM2(m.computed.price_eur_per_m2) : "—";
        const ms = m.mystock || null;
        const unit = ms
          ? `${fmtNum(ms.unit_price, 4, 4)}\u00a0${ms.price_currency}/${ms.price_basis === "PER_M2" ? "m²" : "kg"}` +
            ' <span class="badge badge-frontal" title="Prix piloté par MyStock">MyStock</span>'
          : `${fmtNum(m.unit_price, 4, 4)}\u00a0${m.price_currency}/${m.price_basis === "PER_M2" ? "m²" : "kg"}`;
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
          materialsTabsHtml() +
            (S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-new-mat">+ Nouvelle matière</button>' : "")
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

    bindMaterialsTabs();

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

  // ───────────────────────────────────────────────────────────────────────
  // Onglet « Matières MyStock ».
  //
  // Une matière se décline par laize (frontal, glassine, complexe) ou par
  // grammage (adhésif). C'est la déclinaison qui s'appaire à une matière de la
  // base Coûts matières, et qui porte les prix par fournisseur.
  // Les supports logistiques (mandrins, cartons, palettes) ne sont pas exposés.
  // ───────────────────────────────────────────────────────────────────────

  async function loadMystockList() {
    const params = new URLSearchParams();
    params.set("active_only", S.filters.msActive === "1" ? "true" : "false");
    if (S.filters.msQ) params.set("q", S.filters.msQ);
    if (S.filters.msCat) params.set("categorie", S.filters.msCat);
    const data = await api("/api/pricing/mystock/materials?" + params.toString());
    S.mystockAll = data.materials || [];
    S.mystockCats = data.categories || [];
    S.laizes = data.laizes || [];
    S.grammages = data.grammages || [];
    applyMystockFilters();
  }

  function applyMystockFilters() {
    let list = S.mystockAll || [];
    if (S.filters.msActive === "0") list = list.filter((m) => !m.actif);
    S.mystock = list;
  }

  /** Prix en vigueur : 3 décimales à l'affichage, la saisie garde sa précision. */
  function fmtPrixUnite(v, unite) {
    if (v == null) return "—";
    const s = fmtNum(v, 3, 3);
    return s === "—" ? s : s + " " + (unite || "€");
  }

  function mystockPrixResume(m) {
    if (m.prix_min == null) return '<span class="muted">à compléter</span>';
    if (Math.abs((m.prix_max || 0) - (m.prix_min || 0)) < 1e-9) {
      return fmtPrixUnite(m.prix_min, m.unite);
    }
    return `${fmtPrixUnite(m.prix_min, m.unite)} <span class="muted">à</span> ${fmtPrixUnite(m.prix_max, m.unite)}`;
  }

  function fournisseurOptions(selectedId) {
    return (
      '<option value="">— Sans fournisseur —</option>' +
      S.fournisseurs
        .map(
          (f) =>
            `<option value="${f.id}" ${String(selectedId) === String(f.id) ? "selected" : ""}>${escHtml(f.nom)}</option>`
        )
        .join("")
    );
  }

  const DECL_LABEL = { LAIZE: "laize", GRAMMAGE: "grammage" };

  /** Bouton d'action en icône seule, avec bulle d'aide au survol. */
  function actionBtn(attr, valeur, nom, titre, danger) {
    return `<button type="button" class="ico-btn${danger ? " danger" : ""}" ${attr}="${escAttr(valeur)}" title="${escAttr(titre)}" aria-label="${escAttr(titre)}">${icon(nom, 15)}</button>`;
  }

  /** Cellule de déclinaison : liste de laizes, ou grammage à saisir. */
  function declinaisonCell(m, d) {
    if (!S.canWrite) return escHtml(d.libelle);
    if (m.type_declinaison === "LAIZE") {
      const opts =
        '<option value="">— à choisir —</option>' +
        S.laizes
          .map(
            (l) =>
              `<option value="${l.id}" ${String(d.laize_id) === String(l.id) ? "selected" : ""}>${escHtml(l.label)}</option>`
          )
          .join("");
      return `<select class="ms-inline ms-decl-input" data-ms-decl-laize="${d.id}">${opts}</select>`;
    }
    if (m.type_declinaison === "GRAMMAGE") {
      const v = d.grammage_id ? String(d.libelle).replace(/[^\d.,]/g, "").replace(",", ".") : "";
      return `<input type="number" step="0.1" min="0" class="ms-inline ms-decl-input ms-gsm"
                data-ms-decl-gsm="${d.id}" value="${escAttr(v)}" placeholder="g/m²"/>`;
    }
    return '<span class="muted">—</span>';
  }

  /**
   * Zone dépliée : une seule table à plat. Chaque ligne porte sa déclinaison,
   * son fournisseur, son prix, sa fiche appairée et ses actions.
   */
  function mystockDetailHtml(m) {
    const decls = m.declinaisons || [];
    const colonnes = m.type_declinaison
      ? `<th style="width:34px"></th><th>${escHtml(DECL_LABEL[m.type_declinaison])}</th>`
      : '<th style="width:34px"></th><th>Déclinaison</th>';
    const lignes = [];
    decls.forEach((d) => {
      (d.lignes || []).forEach((l, i) => {
        const fid = l.fournisseur_id == null ? "" : l.fournisseur_id;
        const key = `${d.id}|${fid}`;
        // Le coût au m² est le vrai résultat attendu : il ouvre la fiche de
        // paramétrage de la déclinaison.
        const cout = d.cout_eur_m2 != null && d.cout_eur_m2 > 0
          ? `<button type="button" class="link-btn" data-ms-open="${d.id}" title="Ouvrir le paramétrage de cette déclinaison">${escHtml(fmtEurM2(d.cout_eur_m2))}</button>`
          : `<button type="button" class="link-btn muted" data-ms-open="${d.id}" title="Renseigner poids, devise, taxes et transport">à paramétrer</button>`;
        lignes.push(`<tr class="${l.principal ? "ms-principal" : ""}">
          <td class="ms-statut">${l.principal
              ? `<span class="badge badge-glassine" title="Ce prix fait foi">Principal</span>`
              : (S.canWrite ? actionBtn("data-ms-principal", key, "star", "Faire de ce prix celui qui fait foi") : "")}</td>
          <td class="ms-decl-cell">${i === 0 ? declinaisonCell(m, d) : '<span class="ms-decl-rappel">↳</span>'}</td>
          <td>${S.canWrite
              ? `<select class="ms-inline" data-ms-fourn="${escAttr(key)}">${fournisseurOptions(l.fournisseur_id)}</select>`
              : escHtml(l.fournisseur_nom || "— Sans fournisseur —")}</td>
          <td>${S.canWrite
              ? `<input type="number" step="0.0001" class="ms-inline ms-prix" data-ms-prix="${escAttr(key)}" value="${escAttr(l.prix)}"/>`
              : fmtPrixUnite(l.prix, m.unite)}</td>
          <td class="ms-unite">${escHtml(m.unite)}</td>
          <td class="ms-fiche">${i === 0 ? cout : ""}</td>
          <td class="ms-meta">${escHtml(l.updated_at ? String(l.updated_at).replace("T", " ").slice(0, 16) : "—")}${l.updated_by_name ? " · " + escHtml(l.updated_by_name) : ""}</td>
          <td class="ms-actions">${S.canWrite
              ? actionBtn("data-ms-open", d.id, "edit", "Ouvrir le paramétrage de cette déclinaison") +
                actionBtn("data-ms-dup", key, "copy", "Dupliquer cette ligne pour un autre fournisseur") +
                (m.type_declinaison ? actionBtn("data-ms-new", m.id, "plus", `Créer un nouveau ${DECL_LABEL[m.type_declinaison]}`) : "") +
                actionBtn("data-ms-del", key, "trash", "Supprimer cette ligne", true)
              : ""}</td>
        </tr>`);
      });
    });
    if (!lignes.length) {
      return `<div class="ms-detail">
        <table class="pr-table ms-table">
          <thead><tr>${colonnes}<th>Fournisseur</th><th>Prix</th><th>Unité</th><th>Coût €/m²</th><th>Modifié</th><th class="ms-actions"></th></tr></thead>
          <tbody><tr><td colspan="8" class="empty" style="padding:18px">Aucune déclinaison.
            ${S.canWrite && m.type_declinaison
              ? `<button type="button" class="btn btn-soft btn-sm" data-ms-new="${m.id}" style="margin-left:8px">Créer ${escHtml(DECL_LABEL[m.type_declinaison] === "laize" ? "une laize" : "un grammage")}</button>`
              : ""}</td></tr></tbody>
        </table></div>`;
    }
    return `<div class="ms-detail">
      <table class="pr-table ms-table">
        <thead><tr>${colonnes}<th>Fournisseur</th><th>Prix</th><th>Unité</th><th>Coût €/m²</th><th>Modifié</th><th class="ms-actions"></th></tr></thead>
        <tbody>${lignes.join("")}</tbody>
      </table>
    </div>`;
  }

  function renderMystockList() {
    const catOpts =
      '<option value="">Toutes catégories</option>' +
      S.mystockCats
        .map(
          (c) =>
            `<option value="${escAttr(c)}" ${S.filters.msCat === c ? "selected" : ""}>${escHtml(c)}</option>`
        )
        .join("");

    const rows = S.mystock
      .map((m) => {
        const open = !!S.expanded[m.id];
        const nb = m.nb_declinaisons || 0;
        const prets = m.nb_parametrees || 0;
        const lien = nb
          ? (prets === nb
              ? `<span class="badge badge-frontal">${prets}/${nb} réglée${nb > 1 ? "s" : ""}</span>`
              : `<span class="badge ${prets ? "badge-silicone" : "badge-autre"}">${prets}/${nb} réglée${nb > 1 ? "s" : ""}</span>`)
          : '<span class="muted">—</span>';
        return `<tr class="ms-row${open ? " open" : ""}" data-ms-row="${m.id}">
            <td class="ms-caret">${open ? "▾" : "▸"}</td>
            <td>${categorieBadge(m.categorie)}</td>
            <td><strong>${escHtml(m.reference)}</strong></td>
            <td>${escHtml(m.designation)}</td>
            <td class="ms-mode">${m.type_declinaison
                ? `<span class="badge badge-silicone">${escHtml(DECL_LABEL[m.type_declinaison])} · ${nb}</span>`
                : '<span class="badge badge-autre">sans déclinaison</span>'}</td>
            <td class="ms-prix-cell">${mystockPrixResume(m)}</td>
            <td>${m.nb_fournisseurs || 0}</td>
            <td>${lien}</td>
            <td class="row-actions" onclick="event.stopPropagation()">
              <a class="btn btn-soft btn-sm" href="/stock?tab=matieres&matiere=${m.id}" target="_blank" rel="noopener" title="Ouvrir la fiche dans MyStock">MyStock ↗</a>
            </td>
          </tr>
          ${open ? `<tr class="ms-detail-row"><td colspan="9">${mystockDetailHtml(m)}</td></tr>` : ""}`;
      })
      .join("");

    setContent(`
      <div class="pr-narrow">
        ${pageHead("Matières", `${S.mystock.length} matière(s) MyStock`, materialsTabsHtml())}
        <div class="filters">
          <input type="search" class="search-input" id="ms-q" placeholder="Rechercher (référence, désignation…)" value="${escAttr(S.filters.msQ)}"/>
          <select id="ms-cat">${catOpts}</select>
          <select id="ms-active">
            <option value="1" ${S.filters.msActive==="1"?"selected":""}>Actives</option>
            <option value="0" ${S.filters.msActive==="0"?"selected":""}>Inactives</option>
            <option value="all" ${S.filters.msActive==="all"?"selected":""}>Toutes</option>
          </select>
        </div>
        <div class="ms-hint">Le prix saisi ici est <strong>celui de MyStock</strong> : il est écrit directement dans la valorisation et historisé.
          C'est le prix du <strong>fournisseur principal</strong> qui fait foi. Chaque <strong>déclinaison</strong> — une laize, un grammage —
          a sa propre fiche : clique sur son coût pour régler poids, devise, taxes et transport d'import.</div>
        <div class="table-wrap">
          <table class="pr-table">
            <thead><tr><th style="width:28px"></th><th>Cat.</th><th>Référence</th><th>Désignation</th><th>Déclinaisons</th><th>Prix en vigueur</th><th>Fourn.</th><th>Réglées</th><th></th></tr></thead>
            <tbody>${rows || '<tr><td colspan="9" class="empty">Aucune matière pour ce filtre</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `);

    bindMaterialsTabs();

    const qEl = document.getElementById("ms-q");
    let t;
    qEl.oninput = () => {
      clearTimeout(t);
      t = setTimeout(async () => {
        S.filters.msQ = qEl.value;
        await loadMystockList();
        renderMystockList();
      }, 300);
    };
    document.getElementById("ms-cat").onchange = async (e) => {
      S.filters.msCat = e.target.value;
      await loadMystockList();
      renderMystockList();
    };
    document.getElementById("ms-active").onchange = async (e) => {
      S.filters.msActive = e.target.value;
      await loadMystockList();
      renderMystockList();
    };
    document.querySelectorAll("[data-ms-row]").forEach((tr) => {
      tr.onclick = (e) => {
        if (e.target.closest("input,select,button,a")) return;
        const id = tr.getAttribute("data-ms-row");
        S.expanded[id] = !S.expanded[id];
        renderMystockList();
      };
    });
    bindMystockActions();
  }

  function parseMsKey(key) {
    const [decl, fid] = String(key).split("|");
    return {
      declinaison_id: parseInt(decl, 10),
      fournisseur_id: fid === "" || fid === undefined ? null : parseInt(fid, 10),
    };
  }

  async function msCall(path, body, method) {
    try {
      await api(path, { method: method || "POST", body });
      await loadMystockList();
      renderMystockList();
      return true;
    } catch (e) {
      showToast(e.message, "danger");
      return false;
    }
  }

  function bindMystockActions() {
    document.querySelectorAll("[data-ms-prix]").forEach((inp) => {
      inp.onchange = async () => {
        const k = parseMsKey(inp.getAttribute("data-ms-prix"));
        const prix = parseFloat(inp.value);
        if (Number.isNaN(prix)) {
          showToast("Prix invalide.", "danger");
          return;
        }
        if (await msCall("/api/pricing/mystock/prix", { ...k, prix })) {
          showToast("Prix enregistré dans MyStock.", "success");
        }
      };
    });
    document.querySelectorAll("[data-ms-fourn]").forEach((sel) => {
      sel.onchange = async () => {
        const k = parseMsKey(sel.getAttribute("data-ms-fourn"));
        const nouveau = sel.value === "" ? null : parseInt(sel.value, 10);
        // On renomme le fournisseur de la ligne existante : la recréer lui ferait
        // perdre son statut de principal.
        if (
          await msCall("/api/pricing/mystock/fournisseur", {
            ...k,
            nouveau_fournisseur_id: nouveau,
          })
        ) {
          showToast("Fournisseur enregistré dans MyStock.", "success");
        }
      };
    });
    document.querySelectorAll("[data-ms-principal]").forEach((btn) => {
      btn.onclick = async () => {
        const k = parseMsKey(btn.getAttribute("data-ms-principal"));
        if (await msCall("/api/pricing/mystock/principal", k)) {
          showToast("Fournisseur principal mis à jour — prix poussé dans MyStock.", "success");
        }
      };
    });
    document.querySelectorAll("[data-ms-del]").forEach((btn) => {
      btn.onclick = async () => {
        const k = parseMsKey(btn.getAttribute("data-ms-del"));
        const ok = await confirmDelete(
          "Supprimer cette ligne ? Si c'est la dernière de la déclinaison, la déclinaison part avec."
        );
        if (!ok) return;
        if (await msCall("/api/pricing/mystock/prix", k, "DELETE")) {
          showToast("Ligne supprimée.", "success");
        }
      };
    });
    document.querySelectorAll("[data-ms-dup]").forEach((btn) => {
      btn.onclick = async () => {
        const k = parseMsKey(btn.getAttribute("data-ms-dup"));
        if (await msCall("/api/pricing/mystock/prix/dupliquer", k)) {
          showToast("Ligne dupliquée — choisissez l'autre fournisseur.", "success");
        }
      };
    });
    document.querySelectorAll("[data-ms-new]").forEach((btn) => {
      btn.onclick = async () => {
        const id = parseInt(btn.getAttribute("data-ms-new"), 10);
        if (await msCall("/api/pricing/mystock/declinaisons", { matiere_id: id })) {
          showToast("Déclinaison créée — renseignez sa valeur dans la ligne.", "info");
        }
      };
    });
    document.querySelectorAll("[data-ms-decl-gsm]").forEach((inp) => {
      inp.onchange = async () => {
        const v = parseFloat(inp.value);
        if (!v || v <= 0) {
          showToast("Grammage invalide.", "danger");
          return;
        }
        if (
          await msCall("/api/pricing/mystock/declinaisons/valeur", {
            declinaison_id: parseInt(inp.getAttribute("data-ms-decl-gsm"), 10),
            valeur_gsm: v,
          })
        ) {
          showToast("Grammage enregistré.", "success");
        }
      };
    });
    document.querySelectorAll("[data-ms-decl-laize]").forEach((sel) => {
      sel.onchange = async () => {
        if (!sel.value) return;
        if (
          await msCall("/api/pricing/mystock/declinaisons/valeur", {
            declinaison_id: parseInt(sel.getAttribute("data-ms-decl-laize"), 10),
            laize_id: parseInt(sel.value, 10),
          })
        ) {
          showToast("Laize enregistrée.", "success");
        }
      };
    });
    // Ouverture de la fiche de paramétrage de la déclinaison.
    document.querySelectorAll("[data-ms-open]").forEach((btn) => {
      btn.onclick = () => navigate("/pricing/mystock/" + btn.getAttribute("data-ms-open"));
    });
  }


  function categorieBadge(cat) {
    const c = String(cat || "").toUpperCase();
    const map = {
      FRONTAL: "badge-frontal",
      GLASSINE: "badge-glassine",
      COMPLEXE: "badge-silicone",
      ADHESIF: "badge-adhesif",
    };
    return `<span class="badge ${map[c] || "badge-autre"}">${escHtml(cat || "—")}</span>`;
  }

  /** Bascule entre la base Coûts matières et les matières MyStock. */
  function materialsTabsHtml() {
    const t = S.filters.matTab;
    return `<div class="tabs">
      <button type="button" class="tab${t === "couts" ? " on" : ""}" data-tab="couts">Base Coûts matières</button>
      <button type="button" class="tab${t === "mystock" ? " on" : ""}" data-tab="mystock">Matières MyStock</button>
    </div>`;
  }

  function bindMaterialsTabs() {
    document.querySelectorAll("[data-tab]").forEach((b) => {
      b.onclick = async () => {
        const tab = b.getAttribute("data-tab");
        if (tab === S.filters.matTab) return;
        S.filters.matTab = tab;
        showLoading();
        try {
          if (tab === "mystock") {
            await loadMystockList();
            renderMystockList();
          } else {
            await loadMaterialsList();
            renderMaterialsList();
          }
        } catch (e) {
          setContent(`<div class="empty" style="color:var(--danger);padding:24px">${escHtml(e.message)}</div>`);
        }
      };
    });
  }

  function defaultMaterialForm() {
    const cat = S.categories[0];
    return {
      name: "",
      appellation_code: "",
      category_id: cat ? cat.id : 1,
      supplier_id: "",
      fournisseur_fsc_id: "",
      grammage_gsm: "0",
      perte_pct: String(PERTE_DEFAUT),
      price_currency: "EUR",
      unit_price: "0",
      price_basis: "PER_KG",
      taxe_pct: "0",
      is_imported: false,
      applique_marge: true,
      transport_mode: "AMOUNT",
      transport_unit_price: "0",
      transport_pct: "0",
    };
  }

  async function loadMaterialForm(id) {
    S.matDirty = false;
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
      fournisseur_fsc_id: m.fournisseur_fsc_id || "",
      grammage_gsm: String(m.grammage_gsm != null ? m.grammage_gsm : 0),
      perte_pct: String(m.perte_pct != null ? m.perte_pct : 0),
      price_currency: m.price_currency,
      unit_price: String(m.unit_price),
      price_basis: m.price_basis,
      taxe_pct: String(m.taxe_pct != null ? m.taxe_pct : 0),
      applique_marge: m.applique_marge !== false,
      is_imported: !!m.is_imported,
      transport_mode: m.transport_mode || "AMOUNT",
      transport_unit_price:
        m.transport_unit_price != null ? String(m.transport_unit_price) : "0",
      transport_pct: m.transport_pct != null ? String(m.transport_pct) : "0",
      _mystock: m.mystock || null,
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
      weight_per_m2: poidsRetenu(f.grammage_gsm, f.perte_pct),
      price_currency: f.price_currency,
      price_basis: f.price_basis,
      taxe_pct: parseFloat(f.taxe_pct) || 0,
      is_imported: !!f.is_imported,
      applique_marge: f.applique_marge !== false,
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
   * (prix d'achat + transport + taxes) x taux de change, puis marge.
   */
  function recapTableHtml(computed) {
    if (!computed) return '<div class="empty">—</div>';
    const b = computed.breakdown || {};
    const cur = (b.currency || "EUR").toUpperCase();
    const basis = b.price_basis || "PER_KG";
    const unit = unitLabel(cur, basis);
    const perM2 = basis === "PER_M2";
    const rate = parseFloat(b.fx_rate || 1);
    const w = parseFloat(b.weight_per_m2 || 0);
    const hasTransport = parseFloat(b.transport_src || 0) > 0;
    const taxePct = parseFloat(b.taxe_pct || 0);
    const taxesSrc = parseFloat(b.taxes_src || 0);

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
        label: "Taxes",
        value: taxePct ? fmtCur(taxesSrc, cur) : "—",
        unit: taxePct ? `${unit} · ${fmtPct(taxePct)} du sous-total` : "non imputées",
        muted: !taxePct,
      },
      {
        label: "Sous-total achat",
        value: fmtCur(
          parseFloat(b.unit_price_src || 0) + parseFloat(b.transport_src || 0) + taxesSrc,
          cur
        ),
        unit: unit,
      },
    ];
    if (!perM2) {
      // Prix au kilo : on montre explicitement le passage au m² via le poids.
      cells.push({
        label: "Ramené au m²",
        value: fmtCur(
          parseFloat(b.raw || 0) + parseFloat(b.transport || 0) + taxesSrc * w,
          cur
        ),
        unit: `${CUR_SYM[cur] || "€"}/m² · × ${fmtNum(w * 1000, 1, 1)} g/m²`,
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
            <div class="recap-formula">(prix d'achat + transport + taxes) × change</div>
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
      <aside class="settings-side">
        <div class="si-head">Paramètres globaux <span>appliqués à toutes les matières</span></div>
        <div class="field"><label>Taux USD → EUR ${stale ? fxStaleBadgeHtml() : ""}</label>
          <input type="number" step="0.0001" id="si-rate" value="${escAttr(s.eur_usd_rate)}"/>
          <div class="si-meta">MAJ ${escHtml(fxDate)} · ${escHtml(s.eur_usd_rate_source || "—")}</div>
        </div>
        <div class="field"><label>Marge par défaut <span class="lbl-unit">%</span></label>
          <input type="number" step="0.01" id="si-margin" value="${escAttr(s.default_margin_pct)}"/>
        </div>
        <div class="si-actions">
          <button type="button" class="btn btn-accent btn-sm" id="si-save">Appliquer</button>
          <button type="button" class="btn btn-soft btn-sm" id="si-fx">Rafraîchir le taux</button>
        </div>
      </aside>`;
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

  /**
   * Bandeau d'actions collé en haut de la fiche matière (même principe que la
   * fiche produit MyAO) : sur un formulaire long, le bouton Enregistrer ne doit
   * pas obliger à redescendre en bas de page.
   */
  function matSaveBarHtml(isNew) {
    const dirty = S.matDirty ? "" : " hidden";
    return `<div class="pr-savebar">
        <button type="button" class="btn btn-soft btn-sm" id="btn-back-mat">${icon("arrow-left", 14)} Retour liste</button>
        <div class="savebar-state" id="mat-dirty"${dirty}><span class="dot"></span>Modifications non enregistrées</div>
        <div class="savebar-actions">
          ${!isNew && S.canWrite ? '<button type="button" class="btn btn-danger btn-sm" id="btn-del-mat">Supprimer</button>' : ""}
          ${S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-save-mat">Enregistrer</button>' : ""}
        </div>
      </div>`;
  }

  function renderMaterialForm(isNew) {
    const f = S.formMaterial;
    const catOpts = S.categories
      .map((c) => `<option value="${c.id}" ${f.category_id === c.id ? "selected" : ""}>${escHtml(c.label)}</option>`)
      .join("");
    const supOpts =
      '<option value="">—</option>' +
      S.fournisseurs
        .map(
          (s) =>
            `<option value="${s.id}" ${String(f.fournisseur_fsc_id) === String(s.id) ? "selected" : ""}>${escHtml(s.nom)}</option>`
        )
        .join("");
    // Ancien fournisseur non rapproché : on le signale plutôt que de le perdre.
    const supLegacy =
      !f.fournisseur_fsc_id && f.supplier_id
        ? `<div class="field-hint">Ancien fournisseur : ${escHtml(S.supplierMap[f.supplier_id] || "?")} — non rapproché à l'annuaire de l'entreprise.</div>`
        : "";
    const hist = (f._history || [])
      .map(
        (h) =>
          `<tr><td>${escHtml(h.effective_date)}</td><td>${fmt4(h.unit_price)} ${escHtml(h.price_currency)}</td><td>${escHtml(h.source || "—")}</td></tr>`
      )
      .join("");
    const ms = f._mystock || null;
    const unit = ms
      ? unitLabel(ms.price_currency, ms.price_basis)
      : unitLabel(f.price_currency, f.price_basis);
    const lockAttr = ms ? "disabled" : "";
    const isPct = f.transport_mode === "PCT";

    setContent(`
      <div class="pr-narrow">
        ${pageHead(
          isNew ? "Nouvelle matière" : "Éditer matière",
          isNew ? "" : escHtml(f.name)
        )}
        ${matSaveBarHtml(isNew)}
        <div class="mat-summary" id="mat-summary">${matSummaryHtml(S.matPreview)}</div>
        <div class="form-layout">
        <div class="form-card">
          <div class="form-section"><h3>Identification</h3>
            <div class="field"><label>Nom</label><input id="f-name" value="${escAttr(f.name)}"/></div>
            <div class="field-row">
              <div class="field f-mid"><label>Appellation</label><input id="f-app" value="${escAttr(f.appellation_code)}"/></div>
              <div class="field f-mid"><label>Catégorie</label><select id="f-cat">${catOpts}</select></div>
            </div>
            <div class="field f-mid"><label>Fournisseur</label><select id="f-sup">${supOpts}</select>${supLegacy}</div>
          </div>

          <div class="form-section" id="carac-section" style="${needsWeight(f)?"":"display:none"}"><h3>Caractéristiques</h3>
            <div class="gram-row">
              <div class="field f-num"><label>Grammage <span class="lbl-unit">g/m²</span></label>
                <input type="number" step="0.01" id="f-gsm" value="${escAttr(f.grammage_gsm)}"/></div>
              <div class="gram-arrow" aria-hidden="true">→</div>
              <div class="field f-num"><label>Perte <span class="lbl-unit">%</span></label>
                <input type="number" step="0.1" id="f-perte" value="${escAttr(f.perte_pct)}"/></div>
              <div class="gram-arrow" aria-hidden="true">→</div>
              <div class="field f-num"><label>Grammage dont perte <span class="lbl-unit">g/m²</span></label>
                <div class="gram-out" id="f-gram-out">${escHtml(fmtNum(grammageRetenu(f.grammage_gsm, f.perte_pct), 2, 2))}</div>
                <div class="field-hint">C'est lui qui entre dans le calcul.</div>
              </div>
            </div>
          </div>

          <div class="form-section"><h3>Prix d'achat</h3>
            ${ms ? `<div class="ms-locked">
              <strong>Prix piloté par MyStock</strong> — cette matière est appairée à
              <strong>${escHtml(ms.reference || "?")}</strong> (${escHtml(ms.categorie || "")}).
              Le prix utilisé pour le calcul est celui de MyStock :
              <strong>${escHtml(fmtNum(ms.unit_price, 4, 4))} ${escHtml(ms.price_currency === "USD" ? "$" : "€")}/${ms.price_basis === "PER_M2" ? "m²" : "kg"}</strong>${ms.detail ? ` (${escHtml(ms.detail)})` : ""}.
              <button type="button" class="link-btn" id="btn-goto-mystock">modifier dans l'onglet MyStock</button>
            </div>` : ""}
            <div class="field-row">
              <div class="field f-mid"><label>Devise achat</label><select id="f-cur" ${lockAttr}>
                <option value="EUR" ${f.price_currency==="EUR"?"selected":""}>EUR — euro (€)</option>
                <option value="USD" ${f.price_currency==="USD"?"selected":""}>USD — dollar américain ($)</option>
              </select></div>
              <div class="field"><label>Base de prix</label><select id="f-basis" ${lockAttr}>
                <option value="PER_KG" ${f.price_basis==="PER_KG"?"selected":""}>${escHtml(BASIS_LABEL.PER_KG)}</option>
                <option value="PER_M2" ${f.price_basis==="PER_M2"?"selected":""}>${escHtml(BASIS_LABEL.PER_M2)}</option>
              </select></div>
            </div>
            <div class="field-row">
              <div class="field f-price"><label>Prix unitaire <span class="lbl-unit">${escHtml(unit)}</span></label>
                <div class="price-pair">
                  <input type="number" step="0.0001" id="f-unit" class="price-main" value="${escAttr(ms ? ms.unit_price : f.unit_price)}" ${lockAttr}/>
                  <span class="price-arrow" aria-hidden="true">→</span>
                  <span id="f-unit-alt">${otherPriceHtml(ms ? ms.unit_price : f.unit_price, ms ? ms.price_currency : f.price_currency, ms ? ms.price_basis : f.price_basis)}</span>
                </div>
                <div class="field-hint">Contrepartie au taux ${escHtml(fmtNum((S.settings && S.settings.eur_usd_rate) || 0, 4, 4))} USD → EUR — indicatif, non enregistré.</div>
              </div>
              <div class="field f-num">
                <label class="check-row check-inline">
                  <input type="checkbox" id="f-marge" ${f.applique_marge !== false ? "checked" : ""}/>
                  <span>
                    <span class="check-title">Appliquer la marge</span>
                    <span class="check-sub">Décoché, la matière entre dans le prix de revient mais on ne marge pas dessus.</span>
                  </span>
                </label>
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
                  <div class="field f-num"><label>Taxes <span class="lbl-unit">% du sous-total</span></label>
                    <input type="number" step="0.01" id="f-tax" value="${escAttr(f.taxe_pct)}"/>
                    <div class="field-hint">6 = +6 % · 0 = neutre · −5 = remise de 5 %</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>

        ${inlineSettingsHtml()}
        </div>

        <div id="mat-recap">${recapTableHtml(S.matPreview)}</div>

        ${!isNew && hist ? `<div class="form-card" style="margin-top:16px"><div class="form-section" style="margin:0"><h3>Historique prix (10 derniers)</h3><div class="table-wrap"><table class="pr-table"><thead><tr><th>Date</th><th>Prix</th><th>Source</th></tr></thead><tbody>${hist}</tbody></table></div></div></div>` : ""}
      </div>
    `);

    document.getElementById("btn-back-mat").onclick = () => navigate("/pricing/materials");
    const goMs = document.getElementById("btn-goto-mystock");
    if (goMs) {
      goMs.onclick = () => {
        S.filters.matTab = "mystock";
        S.filters.msQ = ms && ms.reference ? ms.reference : "";
        navigate("/pricing/materials");
      };
    }
    bindInlineSettings(isNew);

    const bindPreview = () => {
      clearTimeout(S.debounceMat);
      S.debounceMat = setTimeout(refreshMaterialPreview, 300);
    };
    const refreshAltPrice = () => {
      const alt = document.getElementById("f-unit-alt");
      if (!alt) return;
      const cur = ms ? ms.price_currency : S.formMaterial.price_currency;
      const bas = ms ? ms.price_basis : S.formMaterial.price_basis;
      alt.innerHTML = otherPriceHtml(S.formMaterial.unit_price, cur, bas);
    };
    // Le grammage retenu n'est pas saisi : il se recalcule sous les yeux.
    const majGrammage = () => {
      const out = document.getElementById("f-gram-out");
      if (out) out.textContent = fmtNum(grammageRetenu(f.grammage_gsm, f.perte_pct), 2, 2);
    };
    ["f-unit", "f-tax", "f-transport", "f-gsm", "f-perte"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.oninput = () => {
        syncMaterialFormFromDom();
        refreshAltPrice();
        majGrammage();
        bindPreview();
      };
    });
    const chkMarge = document.getElementById("f-marge");
    if (chkMarge) chkMarge.onchange = () => {
      syncMaterialFormFromDom();
      bindPreview();
    };
    ["f-cur", "f-basis", "f-imp", "f-tmode"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.onchange = () => {
        syncMaterialFormFromDom();
        renderMaterialForm(isNew);
        refreshMaterialPreview();
      };
    });

    // Le bandeau signale qu'une saisie attend d'être enregistrée. Le drapeau
    // vit dans S : le formulaire se re-rend tout seul quand la devise ou la base
    // de prix change, un état local serait perdu à chaque fois.
    const carte = document.querySelector(".form-layout > .form-card");
    if (carte) {
      const marquer = () => {
        if (S.matDirty) return;
        S.matDirty = true;
        const t = document.getElementById("mat-dirty");
        if (t) t.hidden = false;
      };
      carte.addEventListener("input", marquer);
      carte.addEventListener("change", marquer);
    }

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
    f.fournisseur_fsc_id = val("f-sup") ?? f.fournisseur_fsc_id;
    if (!f._mystock) {
      f.price_currency = val("f-cur") ?? f.price_currency;
      f.price_basis = val("f-basis") ?? f.price_basis;
      f.unit_price = val("f-unit") ?? f.unit_price;
    }
    f.taxe_pct = val("f-tax") ?? f.taxe_pct;
    f.grammage_gsm = val("f-gsm") ?? f.grammage_gsm;
    f.perte_pct = val("f-perte") ?? f.perte_pct;
    const imp = document.getElementById("f-imp");
    if (imp) f.is_imported = imp.checked;
    const marge = document.getElementById("f-marge");
    if (marge) f.applique_marge = marge.checked;
    const mode = val("f-tmode");
    if (mode) f.transport_mode = mode;
    const tv = val("f-transport");
    if (tv != null) {
      if (f.transport_mode === "PCT") f.transport_pct = tv;
      else f.transport_unit_price = tv;
    }
  }

  async function saveMaterialForm(isNew) {
    syncMaterialFormFromDom();
    const f = S.formMaterial;
    const body = {
      name: f.name.trim(),
      appellation_code: f.appellation_code.trim(),
      category_id: f.category_id,
      fournisseur_fsc_id: f.fournisseur_fsc_id ? parseInt(f.fournisseur_fsc_id, 10) : null,
      grammage_gsm: parseFloat(f.grammage_gsm) || 0,
      perte_pct: parseFloat(f.perte_pct) || 0,
      price_currency: f.price_currency,
      unit_price: parseFloat(f.unit_price) || 0,
      price_basis: f.price_basis,
      taxe_pct: parseFloat(f.taxe_pct) || 0,
      is_imported: !!f.is_imported,
      applique_marge: f.applique_marge !== false,
      transport_mode: f.transport_mode || "AMOUNT",
      transport_unit_price: parseFloat(f.transport_unit_price) || 0,
      transport_pct: parseFloat(f.transport_pct) || 0,
      price_history_source: "Saisie interface",
    };
    if (!body.name) {
      showToast("Nom requis.", "danger");
      return;
    }
    if (body.price_basis === "PER_KG" && !(body.grammage_gsm > 0)) {
      showToast("Grammage requis : le prix est saisi au kilo.", "danger");
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
        S.matDirty = false;
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
          `<tr><td>${escHtml(x.effective_date)}</td><td>${fmt4(x.unit_price)} ${currencyBadge(x.price_currency)}</td><td>${fmt4(x.taxe_pct)} %</td><td>${escHtml(x.source || "—")}</td></tr>`
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
        productsTabsHtml() +
          (S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-new-prod">+ Nouveau produit</button>' : "")
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

    bindProductsTabs();
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

  // ─── Fiche d'une déclinaison MyStock ────────────────────────────────────
  // L'équivalent d'une fiche de la base Coûts matières, mais pour une matière
  // MyStock : le prix vient du fournisseur principal, les réglages qui en font
  // un coût au m² (poids, devise, base, taxes, import) vivent sur la
  // déclinaison. Aucune fiche de la base historique n'est nécessaire.

  async function loadDeclinaisonForm(id) {
    S.declDirty = false;
    S.declForm = await api("/api/pricing/mystock/declinaisons/" + id + "/parametrage");
    S.declPreview = S.declForm.computed || null;
  }

  /** Recopie l'état des champs de la page dans S.declForm. */
  function syncDeclFormFromDom() {
    const f = S.declForm;
    const g = (id) => document.getElementById(id);
    if (g("d-cur")) f.price_currency = g("d-cur").value;
    if (g("d-basis")) f.price_basis = g("d-basis").value;
    if (g("d-tax")) f.taxe_pct = g("d-tax").value;
    if (g("d-imp")) f.is_imported = g("d-imp").checked;
    if (g("d-marge")) f.applique_marge = g("d-marge").checked;
    if (g("d-tmode")) f.transport_mode = g("d-tmode").value;
    if (g("d-transport")) {
      const v = g("d-transport").value;
      if (f.transport_mode === "PCT") f.transport_pct = v;
      else f.transport_unit_price = v;
    }
    if (g("d-gsm")) f.grammage_gsm = g("d-gsm").value;
    if (g("d-perte")) f.perte_pct = g("d-perte").value;
  }

  /** Recalcule le coût sans rien enregistrer — même endpoint que la base CM. */
  async function refreshDeclPreview() {
    const f = S.declForm;
    try {
      S.declPreview = await api("/api/pricing/materials/preview", {
        method: "POST",
        body: {
          unit_price: parseFloat(f.unit_price) || 0,
          weight_per_m2: poidsRetenu(f.grammage_gsm, f.perte_pct),
          price_currency: f.price_currency,
          price_basis: f.price_basis,
          taxe_pct: parseFloat(f.taxe_pct) || 0,
          is_imported: !!f.is_imported,
          applique_marge: f.applique_marge !== false,
          transport_mode: f.transport_mode || "AMOUNT",
          transport_unit_price: parseFloat(f.transport_unit_price) || 0,
          transport_pct: parseFloat(f.transport_pct) || 0,
        },
      });
    } catch (e) {
      return;
    }
    const sum = document.getElementById("decl-summary");
    if (sum) sum.innerHTML = matSummaryHtml(S.declPreview);
    const rec = document.getElementById("decl-recap");
    if (rec) rec.innerHTML = recapTableHtml(S.declPreview);
    const eq = document.getElementById("d-transport-eq");
    if (eq) eq.innerHTML = transportEqText(S.declPreview);
  }

  /**
   * Historique des prix d'une déclinaison.
   *
   * Deux applications écrivent le même prix — la valorisation MyStock et cette
   * fiche. Sans la colonne « Depuis », un écart se constate sans jamais
   * s'expliquer.
   */
  function declHistoriqueHtml(lignes) {
    if (!lignes || !lignes.length) {
      return `<div class="form-card" style="margin-top:16px"><div class="form-section" style="margin:0">
        <h3>Historique des prix</h3>
        <div class="empty" style="padding:14px 0">Aucun mouvement enregistré pour l'instant.</div>
      </div></div>`;
    }
    const corps = lignes
      .map((h) => {
        const dp = h.prix_apres != null && h.prix_avant != null
          ? h.prix_apres - h.prix_avant : 0;
        const sens = Math.abs(dp) < 1e-9 ? "" : (dp > 0 ? " hist-hausse" : " hist-baisse");
        const fleche = Math.abs(dp) < 1e-9 ? "" : (dp > 0 ? "▲ " : "▼ ");
        return `<tr>
          <td class="hist-date">${escHtml(fmtDateHeure(h.date))}</td>
          <td>${escHtml(h.origine || "—")}</td>
          <td>${escHtml(h.auteur || "—")}${h.fournisseur_nom ? ` <span class="muted">· ${escHtml(h.fournisseur_nom)}</span>` : ""}</td>
          <td class="msp-num">${h.prix_avant != null ? escHtml(fmt4(h.prix_avant)) : "—"}</td>
          <td class="msp-num${sens}">${fleche}${h.prix_apres != null ? escHtml(fmt4(h.prix_apres)) : "—"}</td>
          <td class="msp-num">${h.sous_total_apres != null ? escHtml(fmt4(h.sous_total_apres)) : "—"}</td>
          <td class="hist-note">${escHtml(h.note || "")}</td>
        </tr>`;
      })
      .join("");
    return `<div class="form-card" style="margin-top:16px"><div class="form-section" style="margin:0">
      <h3>Historique des prix</h3>
      <div class="field-hint" style="margin:-6px 0 10px">Le sous-total d'achat est la valeur affichée par la valorisation MyStock.</div>
      <div class="table-wrap"><table class="pr-table hist-table">
        <thead><tr><th>Date</th><th>Depuis</th><th>Par</th>
          <th class="msp-num">Prix avant</th><th class="msp-num">Prix après</th>
          <th class="msp-num">Sous-total</th><th>Note</th></tr></thead>
        <tbody>${corps}</tbody>
      </table></div>
    </div></div>`;
  }

  /** « 2026-08-05T07:42:11 » → « 05/08/2026 · 07:42 ». */
  function fmtDateHeure(raw) {
    const m = String(raw || "").match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]} · ${m[4]}:${m[5]}` : String(raw || "");
  }

  function declSaveBarHtml() {
    const dirty = S.declDirty ? "" : " hidden";
    return `<div class="pr-savebar">
        <button type="button" class="btn btn-soft btn-sm" id="btn-back-decl">${icon("arrow-left", 14)} Retour liste</button>
        <div class="savebar-state" id="decl-dirty"${dirty}><span class="dot"></span>Modifications non enregistrées</div>
        <div class="savebar-actions">
          <a class="btn btn-soft btn-sm" href="/stock?tab=matieres&matiere=${S.declForm.matiere_id}" target="_blank" rel="noopener" title="Ouvrir la matière dans MyStock">MyStock ↗</a>
          ${S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-save-decl">Enregistrer</button>' : ""}
        </div>
      </div>`;
  }

  function renderDeclinaisonForm() {
    const f = S.declForm;
    const unit = unitLabel(f.price_currency, f.price_basis);
    const isPct = f.transport_mode === "PCT";
    const prixTxt = `${fmtNum(f.unit_price, 4, 4)} ${unit}`;

    setContent(`
      <div class="pr-narrow">
        ${pageHead(
          "Matière MyStock",
          `${escHtml(f.reference)} — ${escHtml(f.libelle)}`
        )}
        ${declSaveBarHtml()}
        <div class="mat-summary" id="decl-summary">${matSummaryHtml(S.declPreview)}</div>
        <div class="form-layout">
        <div class="form-card">

          <div class="form-section"><h3>Identification</h3>
            <div class="ms-locked">
              <strong>${escHtml(f.reference)}</strong> — ${escHtml(f.designation || "")}
              · ${escHtml(f.libelle)} · ${escHtml(f.categorie || "")}
              <br>Prix en vigueur : <strong>${escHtml(prixTxt)}</strong>${
                f.fournisseur_nom ? ` chez <strong>${escHtml(f.fournisseur_nom)}</strong>` : " (aucun fournisseur principal)"
              }.
              Sous-total d'achat : <strong>${escHtml(fmtNum(f.sous_total_achat, 4, 4))} ${escHtml(unit)}</strong>
              — c'est cette valeur que la valorisation MyStock affiche.
              <br>Le prix se modifie dans l'onglet Matières MyStock, où vivent les fournisseurs.
            </div>
          </div>

          <div class="form-section" id="d-carac" style="${needsWeight(f)?"":"display:none"}"><h3>Caractéristiques</h3>
            <div class="gram-row">
              <div class="field f-num"><label>Grammage <span class="lbl-unit">g/m²</span></label>
                <input type="number" step="0.01" id="d-gsm" value="${escAttr(f.grammage_gsm)}"/></div>
              <div class="gram-arrow" aria-hidden="true">→</div>
              <div class="field f-num"><label>Perte <span class="lbl-unit">%</span></label>
                <input type="number" step="0.1" id="d-perte" value="${escAttr(f.perte_pct)}"/></div>
              <div class="gram-arrow" aria-hidden="true">→</div>
              <div class="field f-num"><label>Grammage dont perte <span class="lbl-unit">g/m²</span></label>
                <div class="gram-out" id="d-gram-out">${escHtml(fmtNum(grammageRetenu(f.grammage_gsm, f.perte_pct), 2, 2))}</div>
                <div class="field-hint">C'est lui qui entre dans le calcul.</div>
              </div>
            </div>
          </div>

          <div class="form-section"><h3>Prix d'achat</h3>
            <div class="field-row">
              <div class="field f-mid"><label>Devise achat</label><select id="d-cur">
                <option value="EUR" ${f.price_currency==="EUR"?"selected":""}>EUR — euro (€)</option>
                <option value="USD" ${f.price_currency==="USD"?"selected":""}>USD — dollar américain ($)</option>
              </select></div>
              <div class="field"><label>Base de prix</label><select id="d-basis">
                <option value="PER_KG" ${f.price_basis==="PER_KG"?"selected":""}>${escHtml(BASIS_LABEL.PER_KG)}</option>
                <option value="PER_M2" ${f.price_basis==="PER_M2"?"selected":""}>${escHtml(BASIS_LABEL.PER_M2)}</option>
              </select></div>
            </div>
            <label class="check-row check-inline">
              <input type="checkbox" id="d-marge" ${f.applique_marge !== false ? "checked" : ""}/>
              <span>
                <span class="check-title">Appliquer la marge</span>
                <span class="check-sub">Décoché, la matière entre dans le prix de revient mais on ne marge pas dessus.</span>
              </span>
            </label>
          </div>

          <div class="form-section">
            <div class="import-block${f.is_imported ? " on" : ""}" id="d-import-block">
              <label class="check-row">
                <input type="checkbox" id="d-imp" ${f.is_imported?"checked":""}/>
                <span>
                  <span class="check-title">Matière importée</span>
                  <span class="check-sub">Un coût de transport s'ajoute au prix d'achat avant conversion.</span>
                </span>
              </label>
              <div id="d-import-fields" class="import-fields" style="${f.is_imported?"":"display:none"}">
                <div class="field-row">
                  <div class="field f-mid"><label>Mode de transport</label><select id="d-tmode">
                    <option value="AMOUNT" ${isPct?"":"selected"}>Montant — saisi en ${escHtml(unit)}</option>
                    <option value="PCT" ${isPct?"selected":""}>Pourcentage du prix d'achat</option>
                  </select></div>
                  <div class="field f-num"><label>Transport <span class="lbl-unit">${isPct ? "% du prix d'achat" : escHtml(unit)}</span></label>
                    <input type="number" step="0.0001" id="d-transport" value="${escAttr(isPct ? f.transport_pct : f.transport_unit_price)}"/>
                    <div class="field-hint" id="d-transport-eq">${transportEqText(S.declPreview)}</div>
                  </div>
                  <div class="field f-num"><label>Taxes <span class="lbl-unit">% du sous-total</span></label>
                    <input type="number" step="0.01" id="d-tax" value="${escAttr(f.taxe_pct)}"/>
                    <div class="field-hint">6 = +6 % · 0 = neutre · −5 = remise de 5 %</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>

        ${inlineSettingsHtml()}
        </div>

        <div id="decl-recap">${recapTableHtml(S.declPreview)}</div>
        ${declHistoriqueHtml(f.historique)}
      </div>
    `);

    document.getElementById("btn-back-decl").onclick = () => navigate("/pricing/materials");
    bindInlineSettings();

    const marquer = () => {
      if (S.declDirty) return;
      S.declDirty = true;
      const t = document.getElementById("decl-dirty");
      if (t) t.hidden = false;
    };

    // Saisie libre : on recalcule à la volée, sans re-render (le curseur reste
    // dans le champ).
    const majGrammage = () => {
      const out = document.getElementById("d-gram-out");
      if (out) out.textContent = fmtNum(grammageRetenu(f.grammage_gsm, f.perte_pct), 2, 2);
    };
    ["d-tax", "d-transport", "d-gsm", "d-perte"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.oninput = () => {
        marquer();
        syncDeclFormFromDom();
        majGrammage();
        clearTimeout(S.debounceDecl);
        S.debounceDecl = setTimeout(refreshDeclPreview, 300);
      };
    });
    const chkMarge = document.getElementById("d-marge");
    if (chkMarge) chkMarge.onchange = () => {
      marquer();
      syncDeclFormFromDom();
      refreshDeclPreview();
    };
    // Ces champs changent les unités affichées partout : on re-rend.
    ["d-cur", "d-basis", "d-imp", "d-tmode"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.onchange = () => {
        marquer();
        syncDeclFormFromDom();
        renderDeclinaisonForm();
        refreshDeclPreview();
      };
    });

    const save = document.getElementById("btn-save-decl");
    if (save) save.onclick = () => saveDeclinaisonForm();
  }

  async function saveDeclinaisonForm() {
    syncDeclFormFromDom();
    const f = S.declForm;
    try {
      const maj = await api(
        "/api/pricing/mystock/declinaisons/" + f.declinaison_id + "/parametrage",
        {
          method: "PATCH",
          body: {
            price_currency: f.price_currency,
            price_basis: f.price_basis,
            taxe_pct: parseFloat(f.taxe_pct) || 0,
            is_imported: !!f.is_imported,
            applique_marge: f.applique_marge !== false,
            transport_mode: f.transport_mode || "AMOUNT",
            transport_unit_price: parseFloat(f.transport_unit_price) || 0,
            transport_pct: parseFloat(f.transport_pct) || 0,
            grammage_gsm: parseFloat(f.grammage_gsm) || 0,
            perte_pct: parseFloat(f.perte_pct) || 0,
          },
        }
      );
      S.declForm = maj;
      S.declPreview = maj.computed || null;
      S.declDirty = false;
      showToast("Réglages enregistrés.", "success");
      renderDeclinaisonForm();
    } catch (e) {
      showToast(e.message, "danger");
    }
  }

  // ─── Produits devisés à partir des matières MyStock ─────────────────────
  // Même idée que les produits de la base Coûts matières, mais composés de
  // DÉCLINAISONS : une laize précise d'un frontal, un grammage précis d'un
  // adhésif. MyStock ne connaît pas de catégorie « silicone » : les trois
  // emplacements nommés sont frontal, adhésif et glassine, le reste s'ajoute
  // librement (complexe, autre…).

  const MSP_ROLES = [
    { role: "FRONTAL", label: "Frontal", categorie: "frontal" },
    { role: "ADHESIF", label: "Adhésif", categorie: "adhesif" },
    { role: "GLASSINE", label: "Glassine", categorie: "glassine" },
  ];

  /** Bascule entre les produits de la base CM et ceux composés depuis MyStock. */
  function productsTabsHtml() {
    const t = S.filters.prodTab;
    return `<div class="tabs">
      <button type="button" class="tab${t === "couts" ? " on" : ""}" data-ptab="couts">Base Coûts matières</button>
      <button type="button" class="tab${t === "mystock" ? " on" : ""}" data-ptab="mystock">Produits MyStock</button>
    </div>`;
  }

  function bindProductsTabs() {
    document.querySelectorAll("[data-ptab]").forEach((b) => {
      b.onclick = async () => {
        const t = b.getAttribute("data-ptab");
        if (t === S.filters.prodTab) return;
        S.filters.prodTab = t;
        await bootRoute();
      };
    });
  }

  function defaultMsProductForm() {
    return { code: "", designation: "", roles: {}, autres: [], custom_margin_pct: "" };
  }

  async function loadMsDeclinaisons() {
    const data = await api("/api/pricing/mystock/declinaisons");
    S.msDecls = data.declinaisons || [];
  }

  async function loadMsProductsList() {
    const params = new URLSearchParams();
    params.set("with_cost", "true");
    if (S.filters.msProdQ) params.set("q", S.filters.msProdQ);
    const data = await api("/api/pricing/mystock/produits?" + params.toString());
    S.msProducts = data.produits || [];
  }

  async function loadMsProductForm(id) {
    await loadMsDeclinaisons();
    if (!id) {
      if (!S.formMsProduct) S.formMsProduct = defaultMsProductForm();
      S.msProdPreview = null;
      return;
    }
    const p = await api("/api/pricing/mystock/produits/" + id);
    const roles = {};
    const autres = [];
    (p.composants || []).forEach((c) => {
      if (MSP_ROLES.some((r) => r.role === c.role)) roles[c.role] = c.declinaison_id;
      else autres.push(c.declinaison_id);
    });
    S.formMsProduct = {
      code: p.code,
      designation: p.designation,
      roles,
      autres,
      custom_margin_pct: p.custom_margin_pct != null ? String(p.custom_margin_pct) : "",
    };
    S.msProdPreview = p.cost || null;
  }

  function msDeclLabel(d) {
    const cout = d.cout_eur_m2 != null ? ` — ${fmtEurM2(d.cout_eur_m2)}` : " — à paramétrer";
    return `${d.reference} · ${d.libelle}${cout}`;
  }

  function msDeclOptions(categorie, selectedId) {
    const list = categorie
      ? S.msDecls.filter((d) => (d.categorie || "").toLowerCase() === categorie)
      : S.msDecls;
    const opts = list
      .map(
        (d) =>
          `<option value="${d.id}" ${String(d.id) === String(selectedId) ? "selected" : ""}>${escHtml(msDeclLabel(d))}</option>`
      )
      .join("");
    return `<option value="">— Aucun —</option>${opts}`;
  }

  function msProductFormHtml(isNew) {
    const f = S.formMsProduct;
    const defMargin = S.settings ? fmtNum(S.settings.default_margin_pct, 2, 2) : "—";
    const slots = MSP_ROLES.map(
      (r) => `<div class="field"><label>${escHtml(r.label)}</label>
        <select id="msp-${r.role.toLowerCase()}" data-msp-role="${r.role}">${msDeclOptions(r.categorie, f.roles[r.role])}</select>
      </div>`
    ).join("");
    const autres = f.autres
      .map(
        (id, i) => `<div class="field-row msp-autre" data-msp-idx="${i}">
          <div class="field" style="flex:1"><select data-msp-autre="${i}">${msDeclOptions(null, id)}</select></div>
          <button type="button" class="icon-btn" data-msp-del="${i}" title="Retirer cette matière">${icon("trash", 15)}</button>
        </div>`
      )
      .join("");
    return `
      ${pageHead(isNew ? "Nouveau produit MyStock" : "Éditer produit MyStock",
                 isNew ? "" : escHtml(f.code))}
      <div class="pr-savebar">
        <button type="button" class="btn btn-soft btn-sm" id="btn-back-msprod">${icon("arrow-left", 14)} Retour liste</button>
        <div class="savebar-actions">
          ${!isNew && S.canWrite ? '<button type="button" class="btn btn-danger btn-sm" id="btn-del-msprod">Supprimer</button>' : ""}
          ${S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-save-msprod">Enregistrer</button>' : ""}
        </div>
      </div>
      <div class="form-grid">
        <div class="form-card">
          <div class="field-row">
            <div class="field"><label>Code</label><input id="msp-code" value="${escAttr(f.code)}"/></div>
            <div class="field"><label>Désignation</label><input id="msp-designation" value="${escAttr(f.designation)}"/></div>
          </div>
          ${slots}
          <div class="form-section" style="margin-top:14px"><h3>Autres matières</h3>
            <div id="msp-autres">${autres || '<div class="empty" style="padding:8px 0">Aucune autre matière.</div>'}</div>
            ${S.canWrite ? `<button type="button" class="btn btn-soft btn-sm" id="msp-add-autre">${icon("plus", 14)} Ajouter une matière</button>` : ""}
          </div>
          <div class="field"><label>Marge personnalisée <span class="lbl-unit">% du prix de revient</span></label>
            <input type="number" step="0.01" id="msp-margin" value="${escAttr(f.custom_margin_pct)}" placeholder="Défaut : ${escAttr(defMargin)} %"/>
            <div class="field-hint">Laisser vide pour appliquer la marge par défaut des paramètres.</div>
          </div>
        </div>
        <div class="side-panel" id="msp-recap">${productRecapHtml(S.msProdPreview)}</div>
      </div>`;
  }

  function syncMsProductFromDom() {
    const f = S.formMsProduct;
    f.code = document.getElementById("msp-code").value;
    f.designation = document.getElementById("msp-designation").value;
    f.custom_margin_pct = document.getElementById("msp-margin").value;
    f.roles = {};
    MSP_ROLES.forEach((r) => {
      const el = document.getElementById("msp-" + r.role.toLowerCase());
      if (el && el.value) f.roles[r.role] = parseInt(el.value, 10);
    });
    f.autres = [];
    document.querySelectorAll("[data-msp-autre]").forEach((sel) => {
      if (sel.value) f.autres.push(parseInt(sel.value, 10));
    });
  }

  /** Composition envoyée à l'API : un tableau {declinaison_id, role}. */
  function msProductComposants() {
    const f = S.formMsProduct;
    const out = [];
    MSP_ROLES.forEach((r) => {
      if (f.roles[r.role]) out.push({ declinaison_id: f.roles[r.role], role: r.role });
    });
    f.autres.forEach((id) => {
      if (id) out.push({ declinaison_id: id, role: "AUTRE" });
    });
    return out;
  }

  /**
   * Aperçu du coût sans enregistrer : on additionne les coûts déjà calculés par
   * l'API pour chaque déclinaison. Pas d'aller-retour serveur à chaque clic, et
   * la formule reste celle du moteur (somme des composants + marge en %).
   */
  function refreshMsProductPreview() {
    const f = S.formMsProduct;
    const comps = msProductComposants();
    if (!comps.length) {
      S.msProdPreview = null;
    } else {
      let total = 0;
      let complet = true;
      const components = comps.map((c) => {
        const d = S.msDecls.find((x) => x.id === c.declinaison_id);
        const prix = d && d.cout_eur_m2 != null ? d.cout_eur_m2 : null;
        if (prix == null) complet = false;
        total += prix || 0;
        return {
          material_id: c.declinaison_id,
          name: d ? `${d.reference} · ${d.libelle}` : "#" + c.declinaison_id,
          role: c.role.toLowerCase(),
          price_eur_per_m2: prix || 0,
          share_pct: 0,
        };
      });
      components.forEach((c) => {
        c.share_pct = total ? Math.round((c.price_eur_per_m2 / total) * 10000) / 100 : 0;
      });
      const saisie = parseFloat(f.custom_margin_pct);
      const marge = Number.isNaN(saisie)
        ? parseFloat((S.settings && S.settings.default_margin_pct) || 0)
        : saisie;
      S.msProdPreview = {
        total_eur_per_m2: total,
        margin_pct: marge,
        margin_eur_m2: (total * marge) / 100,
        sell_price_eur_m2: total * (1 + marge / 100),
        components,
        incomplet: !complet,
      };
    }
    const rec = document.getElementById("msp-recap");
    if (rec) {
      rec.innerHTML =
        productRecapHtml(S.msProdPreview) +
        (S.msProdPreview && S.msProdPreview.incomplet
          ? '<div class="field-hint" style="color:var(--warn);margin-top:10px">Une matière n\'a pas encore de coût : ouvre sa fiche pour la paramétrer.</div>'
          : "");
    }
  }

  function renderMsProductForm(isNew) {
    setContent(msProductFormHtml(isNew));

    document.getElementById("btn-back-msprod").onclick = () => navigate("/pricing/products");

    const majAperçu = () => {
      syncMsProductFromDom();
      refreshMsProductPreview();
    };
    ["msp-code", "msp-designation", "msp-margin"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.oninput = majAperçu;
    });
    document.querySelectorAll("[data-msp-role], [data-msp-autre]").forEach((sel) => {
      sel.onchange = majAperçu;
    });
    const add = document.getElementById("msp-add-autre");
    if (add) {
      add.onclick = () => {
        syncMsProductFromDom();
        S.formMsProduct.autres.push("");
        renderMsProductForm(isNew);
      };
    }
    document.querySelectorAll("[data-msp-del]").forEach((btn) => {
      btn.onclick = () => {
        syncMsProductFromDom();
        S.formMsProduct.autres.splice(parseInt(btn.getAttribute("data-msp-del"), 10), 1);
        renderMsProductForm(isNew);
      };
    });

    const save = document.getElementById("btn-save-msprod");
    if (save) save.onclick = () => saveMsProductForm(isNew);
    const del = document.getElementById("btn-del-msprod");
    if (del) {
      del.onclick = async () => {
        if (!(await confirmDelete("Désactiver ce produit ?"))) return;
        try {
          await api("/api/pricing/mystock/produits/" + S.route.id, { method: "DELETE" });
          showToast("Produit désactivé.", "success");
          navigate("/pricing/products");
        } catch (e) {
          showToast(e.message, "danger");
        }
      };
    }
    refreshMsProductPreview();
  }

  async function saveMsProductForm(isNew) {
    syncMsProductFromDom();
    const f = S.formMsProduct;
    const body = {
      code: (f.code || "").trim(),
      designation: (f.designation || "").trim(),
      composants: msProductComposants(),
      custom_margin_pct: f.custom_margin_pct === "" ? null : parseFloat(f.custom_margin_pct),
    };
    try {
      if (isNew) {
        const p = await api("/api/pricing/mystock/produits", { method: "POST", body });
        S.formMsProduct = null;
        showToast("Produit créé.", "success");
        navigate("/pricing/mystock/produit/" + p.id);
      } else {
        await api("/api/pricing/mystock/produits/" + S.route.id, { method: "PATCH", body });
        showToast("Produit enregistré.", "success");
        await loadMsProductForm(S.route.id);
        renderMsProductForm(false);
      }
    } catch (e) {
      showToast(e.message, "danger");
    }
  }

  const MSP_ROLE_LABEL = {
    frontal: "Frontal",
    adhesif: "Adhésif",
    silicone: "Silicone",
    glassine: "Glassine",
  };

  /**
   * Étiquette courte d'un composant dans la liste.
   *
   * « Toutes déclinaisons » n'apprend rien : quand la déclinaison n'a pas de
   * valeur, on n'affiche que la référence de la matière.
   */
  function msProductCompLabel(produit, role) {
    const c = (produit.composants || []).find((x) => x.role === role);
    if (!c) return '<span style="color:var(--muted)">—</span>';
    const val = c.libelle && c.libelle !== "Toutes déclinaisons"
      ? ` <span class="msp-decl">${escHtml(c.libelle)}</span>`
      : "";
    return escHtml(c.reference) + val;
  }

  /**
   * Résumé déplié d'un produit : d'où vient chaque euro de son prix de revient.
   * C'est la fiche produit ramenée à l'essentiel — on veut comprendre sans
   * quitter la liste.
   */
  function msProductDetailHtml(p) {
    const c = p.cost;
    if (!c || !c.components || !c.components.length) {
      return `<div class="ms-detail"><div class="empty" style="padding:16px 22px">
        Aucun coût calculable : les matières de ce produit n'ont pas encore de prix.
      </div></div>`;
    }
    const lignes = c.components
      .map((x) => {
        const prix = parseFloat(x.price_eur_per_m2 || 0);
        const part = parseFloat(x.share_pct || 0);
        return `<tr>
          <td class="msp-role">${escHtml(MSP_ROLE_LABEL[x.role] || x.role)}</td>
          <td><button type="button" class="msp-lien" data-msp-mat="${x.material_id}"
                title="Ouvrir le paramétrage de cette matière">${escHtml(x.name)}</button></td>
          <td class="msp-num">${prix > 0 ? escHtml(fmtEurM2(prix)) : '<span class="muted">sans prix</span>'}</td>
          <td class="msp-part">
            <span class="msp-jauge"><i style="width:${Math.max(0, Math.min(100, part))}%"></i></span>
            <span class="msp-part-val">${escHtml(fmtPct(part))}</span>
          </td>
        </tr>`;
      })
      .join("");
    const manquants = c.components.filter((x) => !(parseFloat(x.price_eur_per_m2) > 0)).length;
    return `<div class="ms-detail">
      <table class="pr-table ms-table msp-detail">
        <thead><tr><th>Rôle</th><th>Matière MyStock</th><th class="msp-num">Coût €/m²</th><th class="msp-part">Part</th></tr></thead>
        <tbody>${lignes}</tbody>
      </table>
      <div class="msp-totaux">
        <span>Prix de revient <strong>${escHtml(fmtEurM2(c.total_eur_per_m2))}</strong></span>
        <span>Marge ${escHtml(fmtPct(c.margin_pct))} <strong>${escHtml(fmtEurM2(c.margin_eur_m2))}</strong></span>
        <span>Prix de vente <strong>${escHtml(fmtEurM2(c.sell_price_eur_m2))}</strong></span>
        ${manquants ? `<span class="msp-alerte">${manquants} matière(s) sans prix — le coût est sous-évalué</span>` : ""}
      </div>
    </div>`;
  }

  function renderMsProductsList() {
    const rows = S.msProducts
      .map((p) => {
        const c = p.cost;
        const open = !!S.expandedProd[p.id];
        const autres = (p.composants || []).filter((x) => x.role === "AUTRE").length;
        return `<tr class="ms-row${open ? " open" : ""}" data-msp-row="${p.id}">
            <td class="ms-caret">${open ? "▾" : "▸"}</td>
            <td><strong>${escHtml(p.code)}</strong></td>
            <td>${escHtml(p.designation)}</td>
            <td>${msProductCompLabel(p, "FRONTAL")}</td>
            <td>${msProductCompLabel(p, "ADHESIF")}</td>
            <td>${msProductCompLabel(p, "GLASSINE")}</td>
            <td>${autres || '<span style="color:var(--muted)">—</span>'}</td>
            <td class="ms-prix-cell">${c ? fmtEurM2(c.total_eur_per_m2) : '<span style="color:var(--muted)">—</span>'}</td>
            <td class="ms-prix-cell">${c ? fmtEurM2(c.sell_price_eur_m2) : "—"}</td>
            <td class="ms-meta">${c ? fmtPct(c.margin_pct) : "—"}</td>
            <td class="row-actions" onclick="event.stopPropagation()">
              <button type="button" class="btn btn-soft btn-sm" data-msp-edit="${p.id}">Éditer</button>
            </td>
          </tr>
          ${open ? `<tr class="ms-detail-row msp-detail-row"><td colspan="11">${msProductDetailHtml(p)}</td></tr>` : ""}`;
      })
      .join("");

    setContent(`
      <div class="pr-narrow">
        ${pageHead("Produits", `${S.msProducts.length} produit(s) MyStock`, productsTabsHtml())}
        <div class="filters">
          <input type="search" class="search-input" id="msp-q" placeholder="Rechercher (code, désignation…)" value="${escAttr(S.filters.msProdQ)}"/>
          ${S.canWrite ? '<button type="button" class="btn btn-accent" id="btn-new-msprod">+ Nouveau produit</button>' : ""}
        </div>
        <div class="ms-hint">Ces produits sont composés de <strong>déclinaisons MyStock</strong> : une laize précise d'un frontal,
          un grammage précis d'un adhésif. Leur coût suit automatiquement le prix du fournisseur principal de chaque matière.
          Clique sur une ligne pour voir d'où vient son prix de revient.</div>
        <div class="table-wrap">
          <table class="pr-table msp-table">
            <thead><tr><th style="width:28px"></th><th>Code</th><th>Désignation</th><th>Frontal</th><th>Adhésif</th><th>Glassine</th><th>Autres</th><th>Coût</th><th>Vente</th><th>Marge</th><th></th></tr></thead>
            <tbody>${rows || '<tr><td colspan="11" class="empty">Aucun produit MyStock. Crée le premier avec le bouton ci-dessus.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `);

    bindProductsTabs();
    const q = document.getElementById("msp-q");
    if (q) {
      q.oninput = (e) => {
        clearTimeout(S.debounceMsProd);
        S.debounceMsProd = setTimeout(async () => {
          S.filters.msProdQ = e.target.value;
          await loadMsProductsList();
          renderMsProductsList();
        }, 300);
      };
    }
    const nouveau = document.getElementById("btn-new-msprod");
    if (nouveau) {
      nouveau.onclick = () => {
        S.formMsProduct = defaultMsProductForm();
        navigate("/pricing/mystock/produit/new");
      };
    }
    // La ligne déplie le détail ; l'édition passe par son bouton. Comme dans
    // la liste des matières MyStock, pour ne pas avoir deux gestes différents
    // d'un onglet à l'autre.
    document.querySelectorAll("tr[data-msp-row]").forEach((tr) => {
      tr.onclick = () => {
        const id = tr.getAttribute("data-msp-row");
        S.expandedProd[id] = !S.expandedProd[id];
        renderMsProductsList();
      };
    });
    document.querySelectorAll("[data-msp-edit]").forEach((b) => {
      b.onclick = () => navigate("/pricing/mystock/produit/" + b.getAttribute("data-msp-edit"));
    });
    // Depuis le détail, on saute directement au paramétrage de la matière.
    document.querySelectorAll("[data-msp-mat]").forEach((b) => {
      b.onclick = (ev) => {
        ev.stopPropagation();
        navigate("/pricing/mystock/" + b.getAttribute("data-msp-mat"));
      };
    });
  }

  async function bootRoute() {
    S.route = parseRoute();
    renderSidebar();
    showLoading();
    try {
      if (!S.categories.length) await loadBaseData();

      const r = S.route.name;
      if (r === "materials") {
        if (S.filters.matTab === "mystock") {
          await loadMystockList();
          renderMystockList();
        } else {
          await loadMaterialsList();
          renderMaterialsList();
        }
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
      } else if (r === "mystock-edit") {
        await loadDeclinaisonForm(S.route.id);
        renderDeclinaisonForm();
      } else if (r === "products") {
        if (S.filters.prodTab === "mystock") {
          await loadMsProductsList();
          renderMsProductsList();
        } else {
          await loadProductsList();
          await renderProductsList();
        }
      } else if (r === "msproduct-new") {
        if (!S.canWrite) {
          navigate("/pricing/products");
          return;
        }
        S.filters.prodTab = "mystock";
        await loadMsProductForm(null);
        renderMsProductForm(true);
      } else if (r === "msproduct-edit") {
        S.filters.prodTab = "mystock";
        await loadMsProductForm(S.route.id);
        renderMsProductForm(false);
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
        // Les paramètres sont une modale : elle s'ouvre par-dessus la liste.
        await loadMaterialsList();
        renderMaterialsList();
        openSettingsModal();
      } else {
        await loadMaterialsList();
        renderMaterialsList();
      }
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
