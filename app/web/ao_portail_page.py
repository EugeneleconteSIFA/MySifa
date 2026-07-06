"""MySifa — Portail fournisseur public (HTML)."""
from __future__ import annotations

import html as html_module
import json

from app.web.ao_portail_i18n import PORTAIL_I18N


def _esc(s: object) -> str:
    return html_module.escape(str(s or ""))


def _normalize_lang(lang: str | None) -> str:
    return "en" if (lang or "").strip().lower() == "en" else "fr"


def _i18n_pack(lang: str) -> tuple[str, str]:
    lang_js = json.dumps(_normalize_lang(lang))
    i18n_js = json.dumps(PORTAIL_I18N, ensure_ascii=False)
    return lang_js, i18n_js


def _inject_i18n(html: str, *, token_js: str, lang_js: str, i18n_js: str) -> str:
    return (
        html.replace("__TOKEN_JS__", token_js)
        .replace("__INIT_LANG_JS__", lang_js)
        .replace("__I18N_JS__", i18n_js)
    )


_LANG_BTN_CSS = """
.hdr-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.lang-btn{
  padding:6px 8px;border-radius:10px;border:1px solid var(--border);background:var(--card);
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;line-height:0;
}
.lang-btn:hover{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.lang-btn svg{display:block;border-radius:2px}
.theme-btn{
  padding:6px 8px;border-radius:10px;border:1px solid var(--border);background:var(--card);
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;line-height:0;
  color:var(--text2);
}
.theme-btn:hover{border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.theme-btn svg{display:block}
"""

_PORTAIL_THEME_JS = """
const ICON_SUN = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
const ICON_MOON = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
function syncThemeColor() {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = document.body.classList.contains('light') ? '#f1f5f9' : '#0a0e17';
}
function initTheme() {
  try {
    if (localStorage.getItem('mysifa_theme') === 'light') document.body.classList.add('light');
  } catch (e) {}
  syncThemeColor();
}
function toggleTheme() {
  document.body.classList.toggle('light');
  try {
    localStorage.setItem('mysifa_theme', document.body.classList.contains('light') ? 'light' : 'dark');
  } catch (e) {}
  syncThemeColor();
  updateThemeBtn();
}
function updateThemeBtn() {
  const btn = document.getElementById('themeBtn');
  if (!btn) return;
  btn.innerHTML = document.body.classList.contains('light') ? ICON_MOON : ICON_SUN;
  if (typeof t === 'function') {
    btn.title = t('themeTitle');
    btn.setAttribute('aria-label', t('themeTitle'));
  }
}
"""


def get_portail_404_html() -> str:
    return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0a0e17">
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<title>Lien invalide — MySifa</title>
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--danger:#f87171}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:40px 32px;max-width:420px;text-align:center}
h1{font-size:18px;font-weight:700;margin-bottom:12px}
p{font-size:14px;color:var(--muted);line-height:1.6}
</style>
</head>
<body>
<div class="card">
<h1>Lien invalide ou expiré</h1>
<p>Ce lien de demande de prix n'est pas reconnu. Contactez votre interlocuteur SIFA pour obtenir un nouveau lien.</p>
</div>
<script src="/static/mysifa_impersonate.js"></script>
</body>
</html>"""


def get_portail_html(
    token: str, ao: dict, fournisseur: dict, *, lang: str = "fr"
) -> str:
    """Page HTML du portail fournisseur — token injecté pour les appels API publics."""
    token_js = json.dumps(token)
    lang_js, i18n_js = _i18n_pack(lang)
    ref_init = _esc(ao.get("reference"))
    titre_init = _esc(ao.get("titre"))
    html = f"""<!DOCTYPE html>
<html lang="{_normalize_lang(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0a0e17">
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<title>{ref_init}</title>
<style>
{_LANG_BTN_CSS}
:root{{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
}}
body.light{{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.1);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);
  min-height:100vh;line-height:1.5;
}}
.wrap{{max-width:860px;margin:0 auto;padding:20px 16px 48px}}
.hdr{{
  display:flex;justify-content:space-between;align-items:flex-start;gap:16px;
  margin-bottom:20px;flex-wrap:wrap;
}}
.hdr-brand{{font-size:13px;color:var(--muted);line-height:1.5}}
.hdr-brand strong{{color:var(--accent);font-size:16px;font-weight:800;letter-spacing:-.3px}}
.hdr-ref{{font-size:12px;color:var(--muted);font-family:ui-monospace,monospace;padding:6px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card)}}
.banner{{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:20px 22px;margin-bottom:16px;
}}
.banner h1{{font-size:18px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.banner-meta{{font-size:13px;color:var(--text2);display:flex;flex-wrap:wrap;gap:12px;align-items:center}}
.badge{{
  display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:.3px;
}}
.badge-muted{{background:rgba(148,163,184,.15);color:var(--muted)}}
.badge-warn{{background:rgba(251,191,36,.15);color:var(--warn)}}
.badge-success{{background:rgba(52,211,153,.15);color:var(--success)}}
.tabs{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.tab{{
  padding:10px 16px;border-radius:10px;border:1px solid var(--border);
  background:transparent;color:var(--text2);font-size:13px;font-weight:600;
  cursor:pointer;font-family:inherit;transition:background .15s,color .15s,border-color .15s;
}}
.tab:hover{{border-color:var(--accent);color:var(--accent)}}
.tab.active{{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}}
.panel{{
  background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;
}}
.panel.hidden{{display:none}}
.notice{{
  font-size:13px;color:var(--text2);margin-bottom:16px;padding:12px 14px;
  border-radius:10px;border:1px solid var(--border);background:var(--bg);
}}
.notice-warn{{border-color:var(--warn);color:var(--warn);background:rgba(251,191,36,.08)}}
.table-wrap{{overflow-x:auto;margin:0 -4px}}
table{{width:100%;border-collapse:collapse;font-size:13px;min-width:640px}}
th,td{{padding:10px 8px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}}
th{{
  font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  font-weight:600;background:var(--bg);
}}
.td-muted{{color:var(--muted);font-size:12px}}
.notice-danger{{border-color:var(--danger);color:var(--danger)}}
td input[type="number"],td input[type="text"]{{min-width:88px}}
input,textarea,select{{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;color:var(--text);font-size:14px;font-family:inherit;
  transition:border-color .15s,box-shadow .15s;
}}
input:focus,textarea:focus,select:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}}
body.light input:focus,body.light textarea:focus,body.light select:focus{{box-shadow:0 0 0 3px rgba(8,145,178,.12)}}
input:disabled,textarea:disabled{{opacity:.65;cursor:not-allowed}}
body.light .btn{{color:#fff}}
label.lbl{{
  display:block;font-size:12px;font-weight:600;color:var(--muted);
  margin:16px 0 8px;text-transform:uppercase;letter-spacing:.5px;
}}
.btn{{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:10px 18px;border-radius:10px;font-weight:700;font-size:14px;border:none;
  cursor:pointer;font-family:inherit;background:var(--accent);color:var(--bg);
  transition:filter .15s;
}}
.btn:hover{{filter:brightness(1.05)}}
.btn:disabled{{opacity:.5;cursor:not-allowed;filter:none}}
.btn-ghost{{
  background:transparent;border:1px solid var(--border);color:var(--text2);
  font-weight:600;font-size:13px;padding:8px 14px;
}}
.btn-ghost:hover{{border-color:var(--accent);color:var(--accent);filter:none}}
.section-title{{
  font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin:0 0 12px;
}}
.section-title:not(:first-child){{margin-top:24px}}
.pj-item{{
  display:flex;justify-content:space-between;align-items:center;gap:12px;
  padding:12px 0;border-bottom:1px solid var(--border);font-size:13px;flex-wrap:wrap;
}}
.pj-item:last-child{{border-bottom:none}}
.pj-name{{color:var(--text);font-weight:500}}
.pj-size{{color:var(--muted);font-size:12px}}
.msg-list{{
  display:flex;flex-direction:column;gap:10px;max-height:360px;overflow-y:auto;
  margin-bottom:16px;padding:4px 2px;
}}
.bubble{{
  max-width:88%;padding:12px 14px;border-radius:12px;font-size:13px;line-height:1.55;
  word-break:break-word;
}}
.bubble.interne{{align-self:flex-start;background:var(--card);border:1px solid var(--border)}}
.bubble.fournisseur{{align-self:flex-end;margin-left:auto;background:var(--accent-bg);border:1px solid var(--accent)}}
.bubble .meta{{font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600}}
.msg-compose{{margin-top:8px}}
.foot{{
  margin-top:28px;font-size:11px;color:var(--muted);text-align:center;line-height:1.6;
  padding-top:16px;border-top:1px solid var(--border);
}}
#toast{{
  position:fixed;bottom:20px;right:20px;left:20px;max-width:360px;margin-left:auto;
  padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;z-index:200;
  display:none;box-shadow:0 8px 24px rgba(0,0,0,.25);
}}
#toast.show{{display:block}}
#toast.success{{background:var(--success);color:var(--bg)}}
#toast.danger{{background:var(--danger);color:#fff}}
#toast.info{{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent)}}
#toast.warn{{background:rgba(251,191,36,.2);color:var(--warn);border:1px solid var(--warn)}}
.empty{{font-size:13px;color:var(--muted);padding:12px 0}}
@media(max-width:600px){{
  .hdr-ref{{width:100%;text-align:center}}
  th,td{{font-size:12px;padding:8px 6px}}
}}
</style>
</head>
<body>
<div class="wrap" id="app">
  <header class="hdr">
    <div class="hdr-brand"><strong>MySifa</strong><br><span id="i18n-subtitle">Portail fournisseur</span></div>
    <div class="hdr-actions" style="flex-direction:column;align-items:flex-end">
      <div class="hdr-actions">
        <a class="btn btn-ghost" id="link-mes-demandes" href="/portail/ao/{_esc(token)}/mes-demandes" style="font-size:12px;padding:8px 12px">Toutes mes demandes</a>
        <button type="button" class="lang-btn" id="langBtn" title="English" aria-label="English"></button>
        <button type="button" class="theme-btn" id="themeBtn" title="Thème clair / sombre" aria-label="Thème clair / sombre"></button>
      </div>
      <div class="hdr-ref" id="hdr-ref">{ref_init}</div>
    </div>
  </header>
  <div class="banner">
    <h1 id="banner-titre">{titre_init}</h1>
    <div class="banner-meta" id="banner-meta">Chargement…</div>
  </div>
  <nav class="tabs" id="tabs">
    <button type="button" class="tab active" data-tab="offre" id="tab-offre">Demande de prix</button>
    <button type="button" class="tab" data-tab="messages" id="tab-messages">Messagerie</button>
    <button type="button" class="tab" data-tab="documents" id="tab-documents">Documents</button>
  </nav>
  <div id="panel-offre" class="panel"></div>
  <div id="panel-messages" class="panel hidden"></div>
  <div id="panel-documents" class="panel hidden"></div>
  <p class="foot" id="i18n-foot">Ce lien est personnel et confidentiel. Ne pas transmettre.</p>
</div>
<div id="toast"></div>
<script>
const TOKEN = __TOKEN_JS__;
const INIT_LANG = __INIT_LANG_JS__;
const I18N = __I18N_JS__;
__PORTAIL_THEME_JS__
const S = {{ tab: "offre", data: null, polling: null, messages: [], lang: INIT_LANG }};

const FLAG_FR = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 3 2" aria-hidden="true"><rect width="1" height="2" fill="#002395"/><rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#ED2939"/></svg>';
const FLAG_GB = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 60 30" aria-hidden="true"><rect width="60" height="30" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="3"/><path d="M30,0 V30 M0,15 H60" stroke="#fff" stroke-width="10"/><path d="M30,0 V30 M0,15 H60" stroke="#C8102E" stroke-width="6"/></svg>';

function t(k) {{ return (I18N[S.lang] && I18N[S.lang][k]) || k; }}
function readLang() {{
  try {{
    const q = new URLSearchParams(location.search).get("lang");
    if (q === "en" || q === "fr") return q;
    const s = localStorage.getItem("mysifa_portail_lang");
    if (s === "en" || s === "fr") return s;
  }} catch (e) {{}}
  return INIT_LANG === "en" ? "en" : "fr";
}}
function pathWithLang(path) {{
  if (S.lang === "en") return path + "?lang=en";
  return path;
}}
function localeTag() {{ return S.lang === "en" ? "en-GB" : "fr-FR"; }}
function updateLangBtn() {{
  const btn = document.getElementById("langBtn");
  if (!btn) return;
  if (S.lang === "fr") {{
    btn.innerHTML = FLAG_GB;
    btn.title = t("langToEn");
    btn.setAttribute("aria-label", t("langToEn"));
  }} else {{
    btn.innerHTML = FLAG_FR;
    btn.title = t("langToFr");
    btn.setAttribute("aria-label", t("langToFr"));
  }}
}}
function applyI18n() {{
  document.documentElement.lang = S.lang;
  const ref = (S.data && S.data.ao && S.data.ao.reference) ? S.data.ao.reference + " — " : "";
  document.title = ref + t("pageTitleSuffix");
  const sub = document.getElementById("i18n-subtitle"); if (sub) sub.textContent = t("subtitle");
  const lnk = document.getElementById("link-mes-demandes");
  if (lnk) {{
    lnk.textContent = t("myRequests");
    lnk.href = pathWithLang("/portail/ao/" + encodeURIComponent(TOKEN) + "/mes-demandes");
  }}
  const fo = document.getElementById("i18n-foot"); if (fo) fo.textContent = t("footConfidential");
  const t1 = document.getElementById("tab-offre"); if (t1) t1.textContent = t("tabOffer");
  const t2 = document.getElementById("tab-messages"); if (t2) t2.textContent = t("tabMessages");
  const t3 = document.getElementById("tab-documents"); if (t3) t3.textContent = t("tabDocuments");
  updateThemeBtn();
  updateLangBtn();
}}
function setLang(lang) {{
  S.lang = lang === "en" ? "en" : "fr";
  try {{ localStorage.setItem("mysifa_portail_lang", S.lang); }} catch (e) {{}}
  applyI18n();
  render();
}}

function escHtml(s) {{
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}}

function showToast(msg, type) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "show " + (type || "info");
  clearTimeout(showToast._tm);
  showToast._tm = setTimeout(() => {{ t.className = ""; }}, 4000);
}}

async function api(path, options) {{
  const r = await fetch(path, {{ credentials: "omit", ...options }});
  if (!r.ok) {{
    let detail = "Erreur " + r.status;
    try {{
      const j = await r.json();
      detail = typeof j.detail === "string" ? j.detail : detail;
    }} catch (e) {{}}
    throw new Error(detail);
  }}
  if (r.status === 204) return null;
  return r.json();
}}

function formatDate(iso) {{
  if (!iso) return "";
  const s = String(iso).trim();
  const d = new Date(s.includes("T") ? s : s.replace(" ", "T"));
  if (isNaN(d.getTime())) return s;
  return d.toLocaleString(localeTag(), {{
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  }});
}}

function formatDateShort(iso) {{
  if (!iso) return "";
  const s = String(iso).trim();
  if (/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(s)) {{
    const p = s.split("-");
    return p[2] + "/" + p[1] + "/" + p[0];
  }}
  const d = new Date(s.includes("T") ? s : s.replace(" ", "T"));
  if (isNaN(d.getTime())) return s;
  return d.toLocaleDateString(localeTag(), {{ day: "2-digit", month: "2-digit", year: "numeric" }});
}}

function escAttr(s) {{
  return escHtml(s).replace(/"/g, "&quot;");
}}

function aoStatutBadge(statut) {{
  const m = {{
    brouillon: ["badge-muted", "ao_brouillon"],
    envoyee: ["badge-warn", "ao_envoyee"],
    cloturee: ["badge-success", "ao_cloturee"]
  }};
  const x = m[statut] || ["badge-muted", null];
  const label = x[1] ? t(x[1]) : (statut || "");
  return '<span class="badge ' + x[0] + '">' + escHtml(label) + '</span>';
}}

function updateBanner() {{
  const d = S.data;
  if (!d || !d.ao) return;
  const ao = d.ao;
  document.getElementById("banner-titre").textContent = ao.titre || "";
  document.getElementById("hdr-ref").textContent = ao.reference || "";
  let meta = aoStatutBadge(ao.statut);
  if (ao.date_limite) meta += '<span>' + escHtml(t("dateLimit")) + ' <strong>' + escHtml(formatDateShort(ao.date_limite)) + '</strong></span>';
  if (d.fournisseur && d.fournisseur.nom_fournisseur) {{
    meta += '<span>' + escHtml(d.fournisseur.nom_fournisseur) + '</span>';
  }}
  document.getElementById("banner-meta").innerHTML = meta;
}}

function setTab(tab) {{
  S.tab = tab;
  document.querySelectorAll(".tab").forEach(b => {{
    b.classList.toggle("active", b.dataset.tab === tab);
  }});
  ["offre", "messages", "documents"].forEach(t => {{
    document.getElementById("panel-" + t).classList.toggle("hidden", t !== tab);
  }});
  if (tab === "messages") {{
    loadMessages();
    startMsgPolling();
  }} else {{
    stopMsgPolling();
  }}
  render();
}}

function startMsgPolling() {{
  stopMsgPolling();
  S.polling = setInterval(() => {{
    if (S.tab === "messages") loadMessages(true);
  }}, 30000);
}}

function stopMsgPolling() {{
  if (S.polling) {{
    clearInterval(S.polling);
    S.polling = null;
  }}
}}

document.getElementById("tabs").addEventListener("click", e => {{
  const btn = e.target.closest(".tab");
  if (btn && btn.dataset.tab) setTab(btn.dataset.tab);
}});

function renderOffre() {{
  const el = document.getElementById("panel-offre");
  const d = S.data;
  if (!d) {{
    el.innerHTML = '<p class="empty">' + escHtml(t("loading")) + '</p>';
    return;
  }}
  const cloture = !!d.cloture;
  const ao = d.ao;
  const fourni = d.fournisseur || {{}};
  const repMap = {{}};
  (d.reponses || []).forEach(r => {{ repMap[r.ligne_id] = r; }});

  let html = "";
  if (cloture) {{
    html += '<p class="notice">' + escHtml(t("noticeClosed")) + '</p>';
  }} else if (fourni.statut === "repondu") {{
    html += '<p class="notice notice-warn">' + escHtml(t("noticeAlreadyReplied")) + '</p>';
  }}

  html += '<div class="table-wrap"><table><thead><tr>' +
    '<th>' + escHtml(t("thClient")) + '</th><th>' + escHtml(t("thRef")) + '</th>' +
    '<th>' + escHtml(t("thFrontal")) + '</th><th>' + escHtml(t("thAdhesive")) + '</th>' +
    '<th>' + escHtml(t("thLabelsBobine")) + '</th><th>' + escHtml(t("thQty")) + '</th>' +
    '<th>' + escHtml(t("thQuotation")) + '</th><th>' + escHtml(t("thCurrency")) + '</th>' +
    '<th>' + escHtml(t("thUnit")) + '</th><th>' + escHtml(t("thDelay")) + '</th>' +
    '<th>' + escHtml(t("thComment")) + '</th>' +
    '</tr></thead><tbody>';

  const lignes = d.lignes || [];
  if (!lignes.length) {{
    html += '<tr><td colspan="11" class="empty">' + escHtml(t("noLines")) + '</td></tr>';
  }} else {{
    lignes.forEach(ln => {{
      const r = repMap[ln.id] || {{}};
      const dis = cloture ? " disabled" : "";
      const qVal = r.quotation != null && r.quotation !== "" ? r.quotation
        : (r.prix_unitaire != null && r.prix_unitaire !== "" ? r.prix_unitaire : "");
      const delaiVal = r.delai_jours != null && r.delai_jours !== "" ? r.delai_jours : "";
      const dev = (r.devise || "EUR").toUpperCase();
      const unite = (r.unite_quotation || "mille").toLowerCase();
      const devSel = (code, sel) =>
        '<option value="' + code + '"' + (sel === code ? " selected" : "") + ">" + code + "</option>";
      const uniteSel = (code, label, sel) =>
        '<option value="' + code + '"' + (sel === code ? " selected" : "") + ">" + label + "</option>";
      html += "<tr>" +
        "<td>" + escHtml(ln.client_nom || t("dash")) + "</td>" +
        "<td>" + escHtml(ln.ref_produit) + "</td>" +
        '<td class="td-muted">' + escHtml(ln.frontal || t("dash")) + "</td>" +
        '<td class="td-muted">' + escHtml(ln.adhesif || t("dash")) + "</td>" +
        "<td>" + escHtml(ln.etiquettes_par_bobine != null ? ln.etiquettes_par_bobine : t("dash")) + "</td>" +
        "<td>" + escHtml(ln.quantite) + "</td>" +
        '<td><input type="number" step="0.0001" min="0" class="inp-quotation" data-lid="' + ln.id + '" value="' + escHtml(qVal) + '"' + dis + "></td>" +
        '<td><select class="inp-devise" data-lid="' + ln.id + '"' + dis + ">" +
          devSel("EUR", dev) + devSel("USD", dev) +
        "</select></td>" +
        '<td><select class="inp-unite" data-lid="' + ln.id + '"' + dis + ">" +
          uniteSel("mille", t("unitMille"), unite) +
          uniteSel("bobine", t("unitBobine"), unite) +
        "</select></td>" +
        '<td><input type="number" step="1" min="0" class="inp-delai" data-lid="' + ln.id + '" value="' + escHtml(delaiVal) + '"' + dis + "></td>" +
        '<td><input type="text" class="inp-com" data-lid="' + ln.id + '" value="' + escAttr(r.commentaire || "") + '"' + dis + "></td>" +
        "</tr>";
    }});
  }}
  html += "</tbody></table></div>";

  html += '<label class="lbl" for="com-global">' + escHtml(t("labelGlobalComment")) + '</label>' +
    '<textarea id="com-global" rows="3"' + (cloture ? " disabled" : "") + ">" +
    escHtml(fourni.commentaire_global || "") + "</textarea>";

  if (!cloture) {{
    html += '<div style="margin-top:20px"><button type="button" class="btn" id="btn-submit">' + escHtml(t("submitOffer")) + '</button></div>';
  }}

  el.innerHTML = html;
  document.getElementById("btn-submit")?.addEventListener("click", submitOffre);
}}

async function submitOffre() {{
  const lignes = [];
  let hasQuotation = false;
  document.querySelectorAll(".inp-quotation").forEach(inp => {{
    const lid = parseInt(inp.dataset.lid, 10);
    const qRaw = inp.value.trim();
    const quotation = qRaw === "" ? null : parseFloat(qRaw);
    const delaiEl = document.querySelector('.inp-delai[data-lid="' + lid + '"]');
    const comEl = document.querySelector('.inp-com[data-lid="' + lid + '"]');
    const devEl = document.querySelector('.inp-devise[data-lid="' + lid + '"]');
    const uniteEl = document.querySelector('.inp-unite[data-lid="' + lid + '"]');
    if (quotation != null && !isNaN(quotation)) hasQuotation = true;
    let delai = null;
    if (delaiEl && delaiEl.value.trim() !== "") {{
      delai = parseInt(delaiEl.value, 10);
      if (isNaN(delai)) delai = null;
    }}
    lignes.push({{
      ligne_id: lid,
      quotation: quotation,
      devise: devEl ? devEl.value : "EUR",
      unite_quotation: uniteEl ? uniteEl.value : "mille",
      delai_jours: delai,
      commentaire: comEl ? (comEl.value.trim() || null) : null
    }});
  }});
  if (!hasQuotation) {{
    showToast(t("toastQuotationRequired"), "danger");
    return;
  }}
  const btn = document.getElementById("btn-submit");
  if (btn) btn.disabled = true;
  try {{
    await api("/api/portail/ao/" + TOKEN + "/repondre", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lignes,
        commentaire_global: (document.getElementById("com-global")?.value || "").trim() || null
      }})
    }});
    showToast(t("toastOfferSaved"), "success");
    S.data = await api("/api/portail/ao/" + TOKEN);
    render();
  }} catch (e) {{
    showToast(e.message, "danger");
  }} finally {{
    if (btn) btn.disabled = false;
  }}
}}

async function loadMessages(silent) {{
  try {{
    const msgs = await api("/api/portail/ao/" + TOKEN + "/messages");
    S.messages = msgs || [];
    if (S.tab === "messages") renderMessagerie(silent);
  }} catch (e) {{
    if (!silent) showToast(e.message, "danger");
  }}
}}

function renderMessagerie(silent) {{
  const el = document.getElementById("panel-messages");
  const d = S.data;
  const cloture = d && d.cloture;
  const msgs = S.messages || [];
  const list = document.getElementById("msg-list-live");
  const scrollTop = list ? list.scrollTop : 0;
  const draft = document.getElementById("msg-text")?.value || "";

  let html = '<div class="msg-list" id="msg-list-live">';
  if (!msgs.length) {{
    html += '<p class="empty">' + escHtml(t("noMessages")) + '</p>';
  }} else {{
    msgs.forEach(m => {{
      const interne = m.expediteur !== "fournisseur";
      const cls = interne ? "interne" : "fournisseur";
      const who = interne ? "SIFA" : escHtml(m.auteur_nom || t("you"));
      html += '<div class="bubble ' + cls + '">' +
        '<div class="meta">' + who + " · " + escHtml(formatDate(m.date)) + "</div>" +
        escHtml(m.message) + "</div>";
    }});
  }}
  html += "</div>";

  if (!cloture) {{
    html += '<div class="msg-compose">' +
      '<textarea id="msg-text" rows="3" placeholder="' + escAttr(t("msgPlaceholder")) + '">' + escHtml(draft) + "</textarea>" +
      '<div style="margin-top:10px"><button type="button" class="btn" id="btn-msg">' + escHtml(t("send")) + '</button></div></div>';
  }} else {{
    html += '<p class="notice">' + escHtml(t("msgClosed")) + '</p>';
  }}

  el.innerHTML = html;
  const newList = document.getElementById("msg-list-live");
  if (newList) newList.scrollTop = scrollTop;

  document.getElementById("btn-msg")?.addEventListener("click", async () => {{
    const message = (document.getElementById("msg-text")?.value || "").trim();
    if (!message) {{
      showToast(t("toastEmptyMessage"), "danger");
      return;
    }}
    const btn = document.getElementById("btn-msg");
    if (btn) btn.disabled = true;
    try {{
      await api("/api/portail/ao/" + TOKEN + "/messages", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ message }})
      }});
      showToast(t("toastMessageSent"), "success");
      await loadMessages(true);
    }} catch (e) {{
      showToast(e.message, "danger");
    }} finally {{
      if (btn) btn.disabled = false;
    }}
  }});
}}

function renderDocuments() {{
  const el = document.getElementById("panel-documents");
  const d = S.data;
  if (!d) {{
    el.innerHTML = '<p class="empty">' + escHtml(t("loading")) + '</p>';
    return;
  }}
  const cloture = !!d.cloture;

  let html = '<p class="section-title">' + escHtml(t("docSifa")) + '</p>';
  const pjAo = d.pj_ao || [];
  if (!pjAo.length) {{
    html += '<p class="empty">' + escHtml(t("noDocSifa")) + '</p>';
  }} else {{
    pjAo.forEach(pj => {{
      const ko = Math.max(1, Math.round((pj.taille_octets || 0) / 1024));
      html += '<div class="pj-item">' +
        '<div><span class="pj-name">' + escHtml(pj.filename) + '</span> ' +
        '<span class="pj-size">(' + ko + ' Ko)</span></div>' +
        '<a class="btn btn-ghost" href="/api/portail/ao/' + TOKEN + '/pj-ao/' + pj.id + '/download">' + escHtml(t("download")) + '</a>' +
        "</div>";
    }});
  }}

  html += '<p class="section-title">' + escHtml(t("docYours")) + '</p>';
  const pjF = d.pj_fournisseur || [];
  if (!pjF.length) {{
    html += '<p class="empty">' + escHtml(t("noDocYours")) + '</p>';
  }} else {{
    pjF.forEach(pj => {{
      const ko = Math.max(1, Math.round((pj.taille_octets || 0) / 1024));
      html += '<div class="pj-item">' +
        '<div><span class="pj-name">' + escHtml(pj.filename) + '</span> ' +
        '<span class="pj-size">(' + ko + ' Ko)</span></div>' +
        '<a class="btn btn-ghost" href="/api/portail/ao/' + TOKEN + '/pieces-jointes/' + pj.id + '/download">' + escHtml(t("download")) + '</a>' +
        "</div>";
    }});
  }}

  if (!cloture) {{
    html += '<div style="margin-top:16px">' +
      '<input type="file" id="pj-file" style="margin-bottom:10px">' +
      '<button type="button" class="btn" id="btn-pj">' + escHtml(t("attachDoc")) + '</button></div>';
  }}

  el.innerHTML = html;
  document.getElementById("btn-pj")?.addEventListener("click", async () => {{
    const input = document.getElementById("pj-file");
    const f = input?.files?.[0];
    if (!f) {{
      showToast(t("toastChooseFile"), "danger");
      return;
    }}
    if (f.size > 15 * 1024 * 1024) {{
      showToast(t("toastFileTooBig"), "danger");
      return;
    }}
    const btn = document.getElementById("btn-pj");
    if (btn) btn.disabled = true;
    const fd = new FormData();
    fd.append("file", f);
    try {{
      await api("/api/portail/ao/" + TOKEN + "/pieces-jointes", {{ method: "POST", body: fd }});
      showToast(t("toastDocAttached"), "success");
      S.data = await api("/api/portail/ao/" + TOKEN);
      renderDocuments();
      if (input) input.value = "";
    }} catch (e) {{
      showToast(e.message, "danger");
    }} finally {{
      if (btn) btn.disabled = false;
    }}
  }});
}}

function render() {{
  updateBanner();
  if (S.tab === "offre") renderOffre();
  else if (S.tab === "messages") renderMessagerie();
  else if (S.tab === "documents") renderDocuments();
}}

async function init() {{
  try {{
    S.data = await api("/api/portail/ao/" + TOKEN);
    applyI18n();
    render();
  }} catch (e) {{
    document.getElementById("panel-offre").innerHTML =
      '<p class="notice notice-danger">' + escHtml(e.message) + "</p>";
  }}
}}

document.getElementById("langBtn").addEventListener("click", () => {{
  setLang(S.lang === "fr" ? "en" : "fr");
}});
document.getElementById("themeBtn").addEventListener("click", toggleTheme);
initTheme();
S.lang = readLang();
applyI18n();
init();
</script>
</body>
</html>"""
    return (
        _inject_i18n(html, token_js=token_js, lang_js=lang_js, i18n_js=i18n_js)
        .replace("__PORTAIL_THEME_JS__", _PORTAIL_THEME_JS)
    )


def get_mes_demandes_html(
    token: str,
    *,
    email: str,
    nom_fournisseur: str | None = None,
    lang: str = "fr",
) -> str:
    """Liste des demandes de prix pour l'email du fournisseur (lien personnel)."""
    token_js = json.dumps(token)
    lang_js, i18n_js = _i18n_pack(lang)
    email_esc = _esc(email)
    nom_esc = _esc(nom_fournisseur or "")
    html = f"""<!DOCTYPE html>
<html lang="{_normalize_lang(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0a0e17">
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<title>Mes demandes</title>
<style>
{_LANG_BTN_CSS}
:root{{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
}}
body.light{{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.1);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);
  min-height:100vh;line-height:1.5;
}}
.wrap{{max-width:860px;margin:0 auto;padding:20px 16px 48px}}
.hdr{{
  display:flex;justify-content:space-between;align-items:flex-start;gap:16px;
  margin-bottom:20px;flex-wrap:wrap;
}}
.hdr-brand{{font-size:13px;color:var(--muted);line-height:1.5}}
.hdr-brand strong{{color:var(--accent);font-size:16px;font-weight:800;letter-spacing:-.3px}}
.chip{{
  font-size:12px;color:var(--muted);font-family:ui-monospace,monospace;
  padding:6px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card);
  max-width:100%;word-break:break-all;
}}
.banner{{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:20px 22px;margin-bottom:16px;
}}
.banner h1{{font-size:18px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.banner p{{font-size:13px;color:var(--text2);line-height:1.65}}
.list{{display:flex;flex-direction:column;gap:12px}}
.d-item{{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:16px 18px;display:flex;flex-direction:column;gap:10px;
}}
.d-item.current{{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent-bg)}}
.d-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
.d-ref{{font-family:ui-monospace,monospace;font-size:12px;color:var(--muted);font-weight:600}}
.d-title{{font-size:15px;font-weight:700;color:var(--text);margin-top:4px}}
.d-meta{{font-size:12px;color:var(--text2);display:flex;flex-wrap:wrap;gap:10px 14px;line-height:1.6}}
.badge{{
  display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:.3px;
}}
.badge-muted{{background:rgba(148,163,184,.15);color:var(--muted)}}
.badge-warn{{background:rgba(251,191,36,.15);color:var(--warn)}}
.badge-success{{background:rgba(52,211,153,.15);color:var(--success)}}
.btn{{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:10px 18px;border-radius:10px;font-weight:700;font-size:14px;border:none;
  cursor:pointer;font-family:inherit;background:var(--accent);color:var(--bg);
  text-decoration:none;transition:filter .15s;
}}
.btn:hover{{filter:brightness(1.05)}}
body.light .btn{{color:#fff}}
.btn-ghost{{
  background:transparent;border:1px solid var(--border);color:var(--text2);
  font-weight:600;font-size:13px;padding:8px 14px;
}}
.btn-ghost:hover{{border-color:var(--accent);color:var(--accent);filter:none}}
.btn-sm{{font-size:13px;padding:8px 14px}}
.empty{{
  font-size:13px;color:var(--muted);padding:24px;text-align:center;
  background:var(--card);border:1px solid var(--border);border-radius:12px;
}}
.foot{{
  margin-top:28px;font-size:11px;color:var(--muted);text-align:center;line-height:1.6;
  padding-top:16px;border-top:1px solid var(--border);
}}
#toast{{
  position:fixed;bottom:20px;right:20px;left:20px;max-width:360px;margin-left:auto;
  padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;z-index:200;
  display:none;box-shadow:0 8px 24px rgba(0,0,0,.25);
}}
#toast.show{{display:block}}
#toast.danger{{background:var(--danger);color:#fff}}
</style>
</head>
<body>
<div class="wrap">
  <header class="hdr">
    <div class="hdr-brand"><strong>MySifa</strong><br><span id="i18n-subtitle">Portail fournisseur</span></div>
    <div class="hdr-actions">
      <div class="chip" id="who">{nom_esc or email_esc}</div>
      <button type="button" class="lang-btn" id="langBtn" title="English" aria-label="English"></button>
      <button type="button" class="theme-btn" id="themeBtn" title="Thème clair / sombre" aria-label="Thème clair / sombre"></button>
    </div>
  </header>
  <div class="banner">
    <h1 id="i18n-banner-title">Mes demandes de prix</h1>
    <p id="i18n-banner-text" data-email="{email_esc}">Chargement…</p>
  </div>
  <div class="list" id="list"><p class="empty">Chargement…</p></div>
  <p class="foot" id="i18n-foot">Ce lien est personnel et confidentiel. Ne pas transmettre.</p>
</div>
<div id="toast"></div>
<script>
const TOKEN = __TOKEN_JS__;
const INIT_LANG = __INIT_LANG_JS__;
const I18N = __I18N_JS__;
__PORTAIL_THEME_JS__
const LIST_EMAIL = {json.dumps(email)};
const S = {{ lang: INIT_LANG }};

const FLAG_FR = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 3 2" aria-hidden="true"><rect width="1" height="2" fill="#002395"/><rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#ED2939"/></svg>';
const FLAG_GB = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="18" viewBox="0 0 60 30" aria-hidden="true"><rect width="60" height="30" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="3"/><path d="M30,0 V30 M0,15 H60" stroke="#fff" stroke-width="10"/><path d="M30,0 V30 M0,15 H60" stroke="#C8102E" stroke-width="6"/></svg>';

function t(k) {{ return (I18N[S.lang] && I18N[S.lang][k]) || k; }}
function readLang() {{
  try {{
    const q = new URLSearchParams(location.search).get("lang");
    if (q === "en" || q === "fr") return q;
    const s = localStorage.getItem("mysifa_portail_lang");
    if (s === "en" || s === "fr") return s;
  }} catch (e) {{}}
  return INIT_LANG === "en" ? "en" : "fr";
}}
function pathWithLang(path) {{
  if (S.lang === "en") return path + "?lang=en";
  return path;
}}
function localeTag() {{ return S.lang === "en" ? "en-GB" : "fr-FR"; }}
function updateLangBtn() {{
  const btn = document.getElementById("langBtn");
  if (!btn) return;
  if (S.lang === "fr") {{
    btn.innerHTML = FLAG_GB;
    btn.title = t("langToEn");
    btn.setAttribute("aria-label", t("langToEn"));
  }} else {{
    btn.innerHTML = FLAG_FR;
    btn.title = t("langToFr");
    btn.setAttribute("aria-label", t("langToFr"));
  }}
}}
function applyI18n() {{
  document.documentElement.lang = S.lang;
  document.title = t("pageTitleList");
  const sub = document.getElementById("i18n-subtitle"); if (sub) sub.textContent = t("subtitle");
  const bt = document.getElementById("i18n-banner-title"); if (bt) bt.textContent = t("listBannerTitle");
  const bx = document.getElementById("i18n-banner-text");
  if (bx) {{
    const em = bx.dataset.email || LIST_EMAIL || "";
    bx.innerHTML = t("listBannerText").replace("__EMAIL__", escHtml(em));
  }}
  const fo = document.getElementById("i18n-foot"); if (fo) fo.textContent = t("footConfidential");
  updateThemeBtn();
  updateLangBtn();
}}
function setLang(lang) {{
  S.lang = lang === "en" ? "en" : "fr";
  try {{ localStorage.setItem("mysifa_portail_lang", S.lang); }} catch (e) {{}}
  applyI18n();
  if (window._listData) renderList(window._listData);
}}

function escHtml(s) {{
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}}

function showToast(msg, type) {{
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "show " + (type || "");
  clearTimeout(showToast._tm);
  showToast._tm = setTimeout(() => {{ el.className = ""; }}, 4000);
}}

async function api(path) {{
  const r = await fetch(path, {{ credentials: "omit" }});
  if (!r.ok) {{
    let detail = "Erreur " + r.status;
    try {{
      const j = await r.json();
      detail = typeof j.detail === "string" ? j.detail : detail;
    }} catch (e) {{}}
    throw new Error(detail);
  }}
  return r.json();
}}

function formatDateShort(iso) {{
  if (!iso) return "";
  const s = String(iso).trim();
  if (/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(s)) {{
    const p = s.split("-");
    return p[2] + "/" + p[1] + "/" + p[0];
  }}
  const d = new Date(s.includes("T") ? s : s.replace(" ", "T"));
  if (isNaN(d.getTime())) return s;
  return d.toLocaleDateString(localeTag(), {{ day: "2-digit", month: "2-digit", year: "numeric" }});
}}

function aoStatutBadge(statut) {{
  const m = {{
    brouillon: ["badge-muted", "ao_brouillon"],
    envoyee: ["badge-warn", "ao_envoyee_list"],
    cloturee: ["badge-success", "ao_cloturee_list"]
  }};
  const x = m[statut] || ["badge-muted", null];
  const label = x[1] ? t(x[1]) : (statut || "");
  return '<span class="badge ' + x[0] + '">' + escHtml(label) + "</span>";
}}

function fourniStatutBadge(statut) {{
  const m = {{
    invite: ["badge-muted", "fourni_invite"],
    ouvert: ["badge-warn", "fourni_ouvert"],
    repondu: ["badge-success", "fourni_repondu"],
    decline: ["badge-muted", "fourni_decline"]
  }};
  const x = m[statut] || ["badge-muted", null];
  const label = x[1] ? t(x[1]) : (statut || "");
  return '<span class="badge ' + x[0] + '">' + escHtml(label) + "</span>";
}}

function renderList(data) {{
  const el = document.getElementById("list");
  const items = data.demandes || [];
  if (!items.length) {{
    el.innerHTML = '<p class="empty">' + escHtml(t("noRequestsList")) + '</p>';
    return;
  }}
  el.innerHTML = items.map(d => {{
    const cur = d.is_current ? " current" : "";
    const href = pathWithLang("/portail/ao/" + encodeURIComponent(d.token));
    let meta = aoStatutBadge(d.ao_statut) + fourniStatutBadge(d.fournisseur_statut);
    if (d.date_limite) {{
      meta += "<span>" + escHtml(t("dateLimit")) + " <strong>" + escHtml(formatDateShort(d.date_limite)) + "</strong></span>";
    }}
    if (d.date_envoi) {{
      meta += "<span>" + escHtml(t("sentOn")) + " " + escHtml(formatDateShort(d.date_envoi)) + "</span>";
    }}
    if (d.date_reponse) {{
      meta += "<span>" + escHtml(t("repliedOn")) + " " + escHtml(formatDateShort(d.date_reponse)) + "</span>";
    }}
    const btnLabel = d.fournisseur_statut === "repondu" ? t("viewEdit") : t("reply");
    return '<article class="d-item' + cur + '">' +
      '<div class="d-top">' +
        '<div><div class="d-ref">' + escHtml(d.reference || "") + "</div>" +
        '<div class="d-title">' + escHtml(d.titre || t("defaultRequestTitle")) + "</div></div>" +
        '<a class="btn btn-sm" href="' + href + '">' + escHtml(btnLabel) + "</a>" +
      "</div>" +
      '<div class="d-meta">' + meta + "</div>" +
      "</article>";
  }}).join("");
}}

async function init() {{
  try {{
    const data = await api("/api/portail/ao/" + TOKEN + "/demandes");
    window._listData = data;
    if (data.nom_fournisseur) {{
      document.getElementById("who").textContent = data.nom_fournisseur;
    }}
    renderList(data);
  }} catch (e) {{
    document.getElementById("list").innerHTML =
      '<p class="empty">' + escHtml(e.message) + "</p>";
    showToast(e.message, "danger");
  }}
}}

document.getElementById("langBtn").addEventListener("click", () => {{
  setLang(S.lang === "fr" ? "en" : "fr");
}});
document.getElementById("themeBtn").addEventListener("click", toggleTheme);
initTheme();
S.lang = readLang();
applyI18n();
init();
</script>
</body>
</html>"""
    return (
        _inject_i18n(html, token_js=token_js, lang_js=lang_js, i18n_js=i18n_js)
        .replace("__PORTAIL_THEME_JS__", _PORTAIL_THEME_JS)
    )
