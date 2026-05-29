"""MySifa — Portail fournisseur public (HTML)."""
from __future__ import annotations

import html as html_module
import json


def _esc(s: object) -> str:
    return html_module.escape(str(s or ""))


def get_portail_404_html() -> str:
    return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0a0e17">
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
</body>
</html>"""


def get_portail_html(token: str, ao: dict, fournisseur: dict) -> str:
    """Page HTML du portail fournisseur — token injecté pour les appels API publics."""
    token_js = json.dumps(token)
    ref_init = _esc(ao.get("reference"))
    titre_init = _esc(ao.get("titre"))
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0a0e17">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<title>{ref_init} — Portail fournisseur</title>
<style>
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
input:focus,textarea:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}}
input:disabled,textarea:disabled{{opacity:.65;cursor:not-allowed}}
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
    <div class="hdr-brand"><strong>MySifa</strong><br>Portail fournisseur</div>
    <div class="hdr-ref" id="hdr-ref">{ref_init}</div>
  </header>
  <div class="banner">
    <h1 id="banner-titre">{titre_init}</h1>
    <div class="banner-meta" id="banner-meta">Chargement…</div>
  </div>
  <nav class="tabs" id="tabs">
    <button type="button" class="tab active" data-tab="offre">Demande de prix</button>
    <button type="button" class="tab" data-tab="messages">Messagerie</button>
    <button type="button" class="tab" data-tab="documents">Documents</button>
  </nav>
  <div id="panel-offre" class="panel"></div>
  <div id="panel-messages" class="panel hidden"></div>
  <div id="panel-documents" class="panel hidden"></div>
  <p class="foot">Ce lien est personnel et confidentiel. Ne pas transmettre.</p>
</div>
<div id="toast"></div>
<script>
const TOKEN = {token_js};
const S = {{ tab: "offre", data: null, polling: null, messages: [] }};

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
  return d.toLocaleString("fr-FR", {{
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
  return formatDate(iso).split(",")[0] || s;
}}

function escAttr(s) {{
  return escHtml(s).replace(/"/g, "&quot;");
}}

function aoStatutBadge(statut) {{
  const m = {{
    brouillon: ["badge-muted", "Brouillon"],
    envoyee: ["badge-warn", "Envoyée"],
    cloturee: ["badge-success", "Clôturée"]
  }};
  const x = m[statut] || ["badge-muted", statut || ""];
  return '<span class="badge ' + x[0] + '">' + escHtml(x[1]) + '</span>';
}}

function updateBanner() {{
  const d = S.data;
  if (!d || !d.ao) return;
  const ao = d.ao;
  document.getElementById("banner-titre").textContent = ao.titre || "";
  document.getElementById("hdr-ref").textContent = ao.reference || "";
  let meta = aoStatutBadge(ao.statut);
  if (ao.date_limite) meta += '<span>Date limite : <strong>' + escHtml(formatDateShort(ao.date_limite)) + '</strong></span>';
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
    el.innerHTML = '<p class="empty">Chargement…</p>';
    return;
  }}
  const cloture = !!d.cloture;
  const ao = d.ao;
  const fourni = d.fournisseur || {{}};
  const repMap = {{}};
  (d.reponses || []).forEach(r => {{ repMap[r.ligne_id] = r; }});

  let html = "";
  if (cloture) {{
    html += '<p class="notice">Cet appel d\\'offre est clôturé. Les réponses ne sont plus acceptées.</p>';
  }} else if (fourni.statut === "repondu") {{
    html += '<p class="notice notice-warn">Vous avez déjà soumis une offre. Vous pouvez la modifier jusqu\\'à la date limite.</p>';
  }}

  html += '<div class="table-wrap"><table><thead><tr>' +
    '<th>Client</th><th>Réf.</th><th>Frontal</th><th>Adhésif</th>' +
    '<th>Étiq. / bobine</th><th>Qté étiquettes</th>' +
    '<th>Quotation</th><th>Devise</th><th>Unité</th>' +
    '<th>Délai (j)</th><th>Commentaire</th>' +
    '</tr></thead><tbody>';

  const lignes = d.lignes || [];
  if (!lignes.length) {{
    html += '<tr><td colspan="11" class="empty">Aucune ligne dans cette demande.</td></tr>';
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
        "<td>" + escHtml(ln.client_nom || "—") + "</td>" +
        "<td>" + escHtml(ln.ref_produit) + "</td>" +
        '<td class="td-muted">' + escHtml(ln.frontal || "—") + "</td>" +
        '<td class="td-muted">' + escHtml(ln.adhesif || "—") + "</td>" +
        "<td>" + escHtml(ln.etiquettes_par_bobine != null ? ln.etiquettes_par_bobine : "—") + "</td>" +
        "<td>" + escHtml(ln.quantite) + "</td>" +
        '<td><input type="number" step="0.0001" min="0" class="inp-quotation" data-lid="' + ln.id + '" value="' + escHtml(qVal) + '"' + dis + "></td>" +
        '<td><select class="inp-devise" data-lid="' + ln.id + '"' + dis + ">" +
          devSel("EUR", dev) + devSel("USD", dev) +
        "</select></td>" +
        '<td><select class="inp-unite" data-lid="' + ln.id + '"' + dis + ">" +
          uniteSel("mille", "Au mille", unite) +
          uniteSel("bobine", "Par bobine", unite) +
        "</select></td>" +
        '<td><input type="number" step="1" min="0" class="inp-delai" data-lid="' + ln.id + '" value="' + escHtml(delaiVal) + '"' + dis + "></td>" +
        '<td><input type="text" class="inp-com" data-lid="' + ln.id + '" value="' + escAttr(r.commentaire || "") + '"' + dis + "></td>" +
        "</tr>";
    }});
  }}
  html += "</tbody></table></div>";

  html += '<label class="lbl" for="com-global">Commentaire général sur votre offre</label>' +
    '<textarea id="com-global" rows="3"' + (cloture ? " disabled" : "") + ">" +
    escHtml(fourni.commentaire_global || "") + "</textarea>";

  if (!cloture) {{
    html += '<div style="margin-top:20px"><button type="button" class="btn" id="btn-submit">Soumettre mon offre</button></div>';
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
    showToast("Indiquez au moins une quotation.", "danger");
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
    showToast("Offre enregistrée.", "success");
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
    html += '<p class="empty">Aucun message pour le moment.</p>';
  }} else {{
    msgs.forEach(m => {{
      const interne = m.expediteur !== "fournisseur";
      const cls = interne ? "interne" : "fournisseur";
      const who = interne ? "SIFA" : escHtml(m.auteur_nom || "Vous");
      html += '<div class="bubble ' + cls + '">' +
        '<div class="meta">' + who + " · " + escHtml(formatDate(m.date)) + "</div>" +
        escHtml(m.message) + "</div>";
    }});
  }}
  html += "</div>";

  if (!cloture) {{
    html += '<div class="msg-compose">' +
      '<textarea id="msg-text" rows="3" placeholder="Votre message…">' + escHtml(draft) + "</textarea>" +
      '<div style="margin-top:10px"><button type="button" class="btn" id="btn-msg">Envoyer</button></div></div>';
  }} else {{
    html += '<p class="notice">Messagerie fermée — appel d\\'offre clôturé.</p>';
  }}

  el.innerHTML = html;
  const newList = document.getElementById("msg-list-live");
  if (newList) newList.scrollTop = scrollTop;

  document.getElementById("btn-msg")?.addEventListener("click", async () => {{
    const message = (document.getElementById("msg-text")?.value || "").trim();
    if (!message) {{
      showToast("Message vide.", "danger");
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
      showToast("Message envoyé.", "success");
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
    el.innerHTML = '<p class="empty">Chargement…</p>';
    return;
  }}
  const cloture = !!d.cloture;

  let html = '<p class="section-title">Documents fournis par SIFA</p>';
  const pjAo = d.pj_ao || [];
  if (!pjAo.length) {{
    html += '<p class="empty">Aucun document fourni.</p>';
  }} else {{
    pjAo.forEach(pj => {{
      const ko = Math.max(1, Math.round((pj.taille_octets || 0) / 1024));
      html += '<div class="pj-item">' +
        '<div><span class="pj-name">' + escHtml(pj.filename) + '</span> ' +
        '<span class="pj-size">(' + ko + ' Ko)</span></div>' +
        '<a class="btn btn-ghost" href="/api/portail/ao/' + TOKEN + '/pj-ao/' + pj.id + '/download">Télécharger</a>' +
        "</div>";
    }});
  }}

  html += '<p class="section-title">Vos documents joints</p>';
  const pjF = d.pj_fournisseur || [];
  if (!pjF.length) {{
    html += '<p class="empty">Aucun document joint.</p>';
  }} else {{
    pjF.forEach(pj => {{
      const ko = Math.max(1, Math.round((pj.taille_octets || 0) / 1024));
      html += '<div class="pj-item">' +
        '<div><span class="pj-name">' + escHtml(pj.filename) + '</span> ' +
        '<span class="pj-size">(' + ko + ' Ko)</span></div>' +
        '<a class="btn btn-ghost" href="/api/portail/ao/' + TOKEN + '/pieces-jointes/' + pj.id + '/download">Télécharger</a>' +
        "</div>";
    }});
  }}

  if (!cloture) {{
    html += '<div style="margin-top:16px">' +
      '<input type="file" id="pj-file" style="margin-bottom:10px">' +
      '<button type="button" class="btn" id="btn-pj">Joindre un document</button></div>';
  }}

  el.innerHTML = html;
  document.getElementById("btn-pj")?.addEventListener("click", async () => {{
    const input = document.getElementById("pj-file");
    const f = input?.files?.[0];
    if (!f) {{
      showToast("Choisissez un fichier.", "danger");
      return;
    }}
    if (f.size > 15 * 1024 * 1024) {{
      showToast("Fichier trop volumineux (max 15 Mo).", "danger");
      return;
    }}
    const btn = document.getElementById("btn-pj");
    if (btn) btn.disabled = true;
    const fd = new FormData();
    fd.append("file", f);
    try {{
      await api("/api/portail/ao/" + TOKEN + "/pieces-jointes", {{ method: "POST", body: fd }});
      showToast("Document joint.", "success");
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
    render();
  }} catch (e) {{
    document.getElementById("panel-offre").innerHTML =
      '<p class="notice notice-danger">' + escHtml(e.message) + "</p>";
  }}
}}

init();
</script>
</body>
</html>"""
