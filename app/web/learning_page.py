"""MySifa — Pages MyLearning (routes /learning et /learning/admin).

Deux pages standalone :
  - /learning         : écran apprenant (liste formations → modules → vidéos + quiz)
  - /learning/admin   : édition de contenu (superadmin uniquement)

Vanilla HTML/CSS/JS injecté en chaîne Python, cohérent avec le reste de MySifa.
Player YouTube via l'API IFrame officielle (youtube-nocookie.com).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/learning", response_class=HTMLResponse)
def learning_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/learning", status_code=302)
        raise
    html = LEARNING_HTML
    html = html.replace("__V_LABEL__", f"v{APP_VERSION}")
    html = html.replace("__USER_NOM__", user.get("nom", ""))
    html = html.replace("__USER_ROLE__", user.get("role", ""))
    html = html.replace("__IS_SUPERADMIN__", "true" if user.get("role") == "superadmin" else "false")
    return HTMLResponse(content=html)


@router.get("/learning/admin", response_class=HTMLResponse)
def learning_admin_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/learning/admin", status_code=302)
        raise
    if user.get("role") != "superadmin":
        return RedirectResponse(url="/learning", status_code=302)
    html = LEARNING_ADMIN_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    html = html.replace("__USER_NOM__", user.get("nom", ""))
    return HTMLResponse(content=html)


# ═════════════════════════════════════════════════════════════════════════
# ─── ÉCRAN APPRENANT ─────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════
LEARNING_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>MyLearning — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<style>
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;
  --accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--muted:#64748b;
  --accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 80px}
.topbar{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand{font-size:24px;font-weight:800;letter-spacing:.3px}
.brand span{color:var(--accent)}
.spacer{flex:1}
.link{color:var(--text2);text-decoration:none;font-size:13px;padding:8px 14px;border-radius:8px;transition:all .15s;border:1px solid transparent}
.link:hover{background:var(--accent-bg);color:var(--accent)}
.link-admin{border-color:var(--warn);color:var(--warn)}
.link-admin:hover{background:rgba(251,191,36,.12)}

h1{font-size:22px;margin:0 0 8px;font-weight:700}
.sub{color:var(--muted);font-size:13px;margin:0 0 24px}

/* Liste des formations */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;cursor:pointer;transition:all .15s;position:relative}
.card:hover{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 8px 24px rgba(34,211,238,.08)}
.card-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:6px}
.card-titre{font-size:16px;font-weight:700;margin-bottom:8px}
.card-desc{font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:16px;min-height:36px}
.card-progress{display:flex;align-items:center;gap:10px;font-size:11px;color:var(--muted)}
.bar{flex:1;height:6px;background:var(--border);border-radius:4px;overflow:hidden}
.bar-fill{height:100%;background:var(--accent);transition:width .3s}
.bar-fill.ok{background:var(--ok)}
.badge{position:absolute;top:14px;right:14px;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase}
.badge-ok{background:rgba(52,211,153,.16);color:var(--ok)}

.empty{padding:40px;text-align:center;color:var(--muted);font-size:13px;border:1px dashed var(--border);border-radius:12px}

/* Vue module */
.back-btn{display:inline-flex;align-items:center;gap:6px;color:var(--text2);text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;margin-bottom:20px}
.back-btn:hover{color:var(--accent);background:var(--accent-bg)}
.module-nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:10px}
.module-nav button{flex:0 0 auto;padding:8px 12px;border-radius:6px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-family:inherit;cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:6px}
.module-nav button:hover{border-color:var(--accent);color:var(--accent)}
.module-nav button.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);font-weight:700}
.module-nav button.done{color:var(--ok);border-color:rgba(52,211,153,.3)}
.module-nav button.done.active{background:rgba(52,211,153,.16);border-color:var(--ok)}
.mn-check{font-weight:900}

.video-container{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:20px}
.video-titre{font-size:15px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between}
.video-pct{font-size:11px;color:var(--muted);font-weight:400}
.video-pct.ok{color:var(--ok)}
.player-frame{position:relative;padding-bottom:56.25%;background:#000;border-radius:8px;overflow:hidden}
.player-frame iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.video-nav{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.video-nav button{padding:8px 14px;border-radius:6px;border:1px solid var(--border);background:transparent;color:var(--text2);font-family:inherit;font-size:12px;cursor:pointer;transition:all .15s}
.video-nav button:hover{border-color:var(--accent);color:var(--accent)}
.video-nav button.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}

/* Quiz */
.quiz-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:20px}
.quiz-title{font-size:16px;font-weight:700;margin-bottom:6px}
.quiz-sub{font-size:12px;color:var(--muted);margin-bottom:20px}
.quiz-locked{padding:20px;background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.3);border-radius:8px;color:var(--warn);font-size:13px}
.q-block{padding:16px;border:1px solid var(--border);border-radius:10px;margin-bottom:12px}
.q-num{font-size:11px;color:var(--muted);font-weight:700;letter-spacing:.5px;text-transform:uppercase;margin-bottom:6px}
.q-text{font-size:14px;font-weight:600;margin-bottom:14px;line-height:1.5}
.q-choice{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;cursor:pointer;margin-bottom:6px;transition:all .15s;font-size:13px}
.q-choice:hover{border-color:var(--accent);background:var(--accent-bg)}
.q-choice input{margin:0;accent-color:var(--accent)}
.q-choice.selected{border-color:var(--accent);background:var(--accent-bg)}
.q-choice.correct{border-color:var(--ok);background:rgba(52,211,153,.12);color:var(--ok);font-weight:600}
.q-choice.incorrect{border-color:var(--danger);background:rgba(248,113,113,.12);color:var(--danger)}
.q-explain{font-size:12px;color:var(--muted);margin-top:8px;padding-left:22px;font-style:italic}

.quiz-submit{margin-top:16px;padding:12px 24px;border-radius:8px;border:none;background:var(--accent);color:#0a0e17;font-weight:700;cursor:pointer;font-family:inherit;font-size:14px;transition:filter .15s}
.quiz-submit:hover{filter:brightness(1.1)}
.quiz-submit:disabled{opacity:.4;cursor:not-allowed}
.quiz-result{margin-top:16px;padding:14px;border-radius:8px;font-size:13px;font-weight:600}
.quiz-result.ok{background:rgba(52,211,153,.12);color:var(--ok);border:1px solid rgba(52,211,153,.3)}
.quiz-result.ko{background:rgba(248,113,113,.12);color:var(--danger);border:1px solid rgba(248,113,113,.3)}

.toast-zone{position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{padding:12px 16px;border-radius:8px;font-size:13px;font-weight:600;color:#0a0e17;animation:toastIn .2s}
.toast.success{background:var(--ok)}
.toast.info{background:var(--accent)}
.toast.danger{background:var(--danger)}
@keyframes toastIn{from{transform:translateX(20px);opacity:0}to{transform:none;opacity:1}}

.loading{color:var(--muted);text-align:center;padding:40px;font-size:13px}
</style>
</head>
<body>
<div id="toast-zone" class="toast-zone"></div>

<div class="wrap">
  <div class="topbar">
    <div class="brand">My<span>Learning</span></div>
    <div class="spacer"></div>
    <a href="/" class="link">← Portail</a>
    <a href="/learning/admin" class="link link-admin" id="admin-link" style="display:none">Admin</a>
  </div>

  <div id="app">
    <div class="loading">Chargement…</div>
  </div>
</div>

<script>
const IS_SUPERADMIN = __IS_SUPERADMIN__;
if (IS_SUPERADMIN) document.getElementById("admin-link").style.display = "";

const S = {
  formations: [],
  current_formation: null,   // {formation, modules, permissions, progression}
  current_module_idx: 0,
  current_video_idx: 0,
  player: null,
  ytApiReady: false,
  pctReportTimer: null,
  lastReportedPct: {},
};

// ─── API helpers ────────────────────────────────────────────────────────
async function api(path, opts) {
  const r = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
  if (r.status === 401) { window.location.href = "/?next=/learning"; return null; }
  if (!r.ok) {
    let msg = "Erreur " + r.status;
    try { const j = await r.json(); msg = j.detail?.message || j.detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.json();
}
function escHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function toast(msg, type) {
  const div = document.createElement("div");
  div.className = "toast " + (type || "info");
  div.textContent = msg;
  document.getElementById("toast-zone").appendChild(div);
  setTimeout(() => div.remove(), 3500);
}
function readQuery() {
  const q = new URLSearchParams(location.search);
  return { f: parseInt(q.get("f") || "0"), m: parseInt(q.get("m") || "0") };
}
function updateQuery(f, m) {
  const p = new URLSearchParams();
  if (f) p.set("f", f);
  if (m) p.set("m", m);
  history.replaceState(null, "", "?" + p.toString());
}

// ─── Router principal ───────────────────────────────────────────────────
async function route() {
  const q = readQuery();
  if (q.f) {
    await renderFormation(q.f, q.m);
  } else {
    await renderPortail();
  }
}

// ─── Vue portail : liste des formations ─────────────────────────────────
async function renderPortail() {
  const data = await api("/api/learning/formations");
  if (!data) return;
  S.formations = data.formations;
  const el = document.getElementById("app");
  if (!S.formations.length) {
    el.innerHTML = `
      <h1>Bonjour __USER_NOM__</h1>
      <p class="sub">Aucun parcours de formation n'est publié pour le moment.</p>
      <div class="empty">
        Le catalogue de parcours arrive prochainement. Vous serez notifié dès la publication du premier parcours.
      </div>`;
    return;
  }
  el.innerHTML = `
    <h1>Bonjour __USER_NOM__</h1>
    <p class="sub">Sélectionnez un parcours pour commencer votre formation. Chaque parcours débloque un ensemble de gestes métier.</p>
    <div class="grid">
      ${S.formations.map(f => {
        const pct = f.modules_total ? Math.round(100 * f.modules_valides / f.modules_total) : 0;
        return `
        <div class="card" onclick="location.href='?f=${f.id}'">
          ${f.complete ? '<span class="badge badge-ok">Terminé</span>' : ''}
          ${f.role_cible ? `<div class="card-role">${escHtml(f.role_cible)}</div>` : ''}
          <div class="card-titre">${escHtml(f.titre)}</div>
          <div class="card-desc">${escHtml(f.description)}</div>
          <div class="card-progress">
            <div class="bar"><div class="bar-fill ${pct === 100 ? 'ok' : ''}" style="width:${pct}%"></div></div>
            <span>${f.modules_valides}/${f.modules_total} module${f.modules_total > 1 ? 's' : ''}</span>
          </div>
        </div>`;
      }).join("")}
    </div>`;
}

// ─── Vue formation : modules + player + quiz ────────────────────────────
async function renderFormation(fid, mid) {
  const data = await api("/api/learning/formations/" + fid);
  if (!data) return;
  S.current_formation = data;
  const modules = data.modules.filter(m => m.actif);
  if (!modules.length) {
    document.getElementById("app").innerHTML = `
      <a href="/learning" class="back-btn">← Retour aux parcours</a>
      <h1>${escHtml(data.formation.titre)}</h1>
      <div class="empty">Ce parcours ne contient encore aucun module.</div>`;
    return;
  }
  S.current_module_idx = Math.max(0, modules.findIndex(m => m.id === mid));
  if (S.current_module_idx < 0) S.current_module_idx = 0;
  S.current_video_idx = 0;
  renderCurrentModule();
}

function renderCurrentModule() {
  const data = S.current_formation;
  const modules = data.modules.filter(m => m.actif);
  const mod = modules[S.current_module_idx];
  updateQuery(data.formation.id, mod.id);

  // Nav modules
  const navHtml = modules.map((m, i) => {
    const valide = data.progression.modules[m.id]?.valide_le;
    return `<button class="${i === S.current_module_idx ? 'active' : ''} ${valide ? 'done' : ''}"
                    onclick="jumpToModule(${i})">
              ${valide ? '<span class="mn-check">✓</span>' : ''} ${escHtml(m.titre)}
            </button>`;
  }).join("");

  // Vidéos
  const videos = mod.videos;
  const videosHtml = videos.length ? renderVideosSection(mod) : `<div class="empty">Ce module ne contient pas encore de vidéos.</div>`;

  // Quiz
  const quizHtml = renderQuizSection(mod);

  document.getElementById("app").innerHTML = `
    <a href="/learning" class="back-btn">← Retour aux parcours</a>
    <h1>${escHtml(data.formation.titre)}</h1>
    <p class="sub">${escHtml(mod.titre)}${mod.description ? ' — ' + escHtml(mod.description) : ''}</p>
    <div class="module-nav">${navHtml}</div>
    ${videosHtml}
    ${quizHtml}
  `;

  if (videos.length) mountVideo(videos[S.current_video_idx]);
}

function renderVideosSection(mod) {
  const videos = mod.videos;
  const v = videos[S.current_video_idx];
  const prog = S.current_formation.progression.videos[v.id] || 0;
  const done = prog >= 90;
  const navHtml = videos.length > 1
    ? `<div class="video-nav">${videos.map((vv, i) => {
         const p = S.current_formation.progression.videos[vv.id] || 0;
         const d = p >= 90 ? '✓ ' : '';
         return `<button class="${i === S.current_video_idx ? 'active' : ''}"
                         onclick="jumpToVideo(${i})">${d}${escHtml(vv.titre)}</button>`;
       }).join("")}</div>`
    : "";
  return `
    <div class="video-container">
      <div class="video-titre">
        <span>${escHtml(v.titre)}</span>
        <span class="video-pct ${done ? 'ok' : ''}">${done ? '✓ vue à ' : ''}${prog}%</span>
      </div>
      <div class="player-frame"><div id="yt-player"></div></div>
      ${navHtml}
    </div>`;
}

function renderQuizSection(mod) {
  if (!mod.quiz.length) return "";
  const videos = mod.videos;
  const videosOk = videos.length && videos.every(v => (S.current_formation.progression.videos[v.id] || 0) >= 90);
  const valid = S.current_formation.progression.modules[mod.id];
  if (!videosOk) {
    return `<div class="quiz-wrap">
      <div class="quiz-title">Quiz de validation</div>
      <div class="quiz-locked">Terminez d'abord toutes les vidéos du module (≥ 90 % de chacune) pour débloquer le quiz.</div>
    </div>`;
  }
  const questionsHtml = mod.quiz.map((q, i) => `
    <div class="q-block" data-qid="${q.id}">
      <div class="q-num">Question ${i + 1}</div>
      <div class="q-text">${escHtml(q.question)}</div>
      ${q.choix.map((c, ci) => `
        <label class="q-choice">
          <input type="radio" name="q_${q.id}" value="${ci}">
          <span>${escHtml(c)}</span>
        </label>`).join("")}
    </div>`).join("");
  const info = valid && valid.quiz_score != null
    ? `<div class="quiz-sub">Meilleur score : <b>${valid.quiz_score}%</b>${valid.valide_le ? ' — module validé ✓' : ' — validation à 80%'}</div>`
    : `<div class="quiz-sub">Répondez à toutes les questions puis validez. Seuil requis : 80% de bonnes réponses.</div>`;
  return `
    <div class="quiz-wrap">
      <div class="quiz-title">Quiz — ${mod.quiz.length} question${mod.quiz.length > 1 ? 's' : ''}</div>
      ${info}
      <div id="quiz-questions">${questionsHtml}</div>
      <button class="quiz-submit" onclick="submitQuiz(${mod.id})">Valider mes réponses</button>
      <div id="quiz-result"></div>
    </div>`;
}

// ─── Navigation ─────────────────────────────────────────────────────────
window.jumpToModule = function(idx) {
  destroyPlayer();
  S.current_module_idx = idx;
  S.current_video_idx = 0;
  renderCurrentModule();
};
window.jumpToVideo = function(idx) {
  destroyPlayer();
  S.current_video_idx = idx;
  renderCurrentModule();
};

// ─── Player YouTube ─────────────────────────────────────────────────────
function loadYtApi() {
  if (window.YT && window.YT.Player) { S.ytApiReady = true; return; }
  const tag = document.createElement("script");
  tag.src = "https://www.youtube.com/iframe_api";
  document.head.appendChild(tag);
  window.onYouTubeIframeAPIReady = () => { S.ytApiReady = true; };
}
function destroyPlayer() {
  if (S.pctReportTimer) { clearInterval(S.pctReportTimer); S.pctReportTimer = null; }
  if (S.player && S.player.destroy) { try { S.player.destroy(); } catch (e) {} }
  S.player = null;
}
function mountVideo(v) {
  destroyPlayer();
  const tryMount = () => {
    if (!S.ytApiReady) { setTimeout(tryMount, 200); return; }
    S.player = new YT.Player("yt-player", {
      host: "https://www.youtube-nocookie.com",
      videoId: v.youtube_id,
      playerVars: { modestbranding: 1, rel: 0, playsinline: 1 },
      events: {
        onReady: () => startPctReport(v),
        onStateChange: (e) => {
          if (e.data === YT.PlayerState.ENDED) reportPct(v, 100);
        }
      }
    });
  };
  tryMount();
}
function startPctReport(v) {
  if (S.pctReportTimer) clearInterval(S.pctReportTimer);
  S.pctReportTimer = setInterval(() => {
    try {
      const t = S.player.getCurrentTime();
      const d = S.player.getDuration();
      if (d > 0) {
        const pct = Math.min(100, Math.round(100 * t / d));
        reportPct(v, pct);
      }
    } catch (e) {}
  }, 5000);
}
async function reportPct(v, pct) {
  const last = S.lastReportedPct[v.id] || 0;
  // Ne report qu'aux paliers de 10% pour éviter de spammer le serveur.
  if (pct < last + 10 && pct < 100) return;
  S.lastReportedPct[v.id] = pct;
  try {
    await api("/api/learning/videos/" + v.id + "/progression",
      { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pct_vu: pct }) });
    // Update local progression
    S.current_formation.progression.videos[v.id] = Math.max(pct, S.current_formation.progression.videos[v.id] || 0);
    // Refresh pct display
    const el = document.querySelector(".video-pct");
    if (el) {
      const done = pct >= 90;
      el.textContent = (done ? "✓ vue à " : "") + pct + "%";
      el.className = "video-pct" + (done ? " ok" : "");
    }
    // Si toutes les vidéos du module viennent d'être terminées, on refresh l'écran pour dévoiler le quiz
    const mod = S.current_formation.modules.filter(m => m.actif)[S.current_module_idx];
    const allOk = mod.videos.every(vv => (S.current_formation.progression.videos[vv.id] || 0) >= 90);
    if (allOk && document.querySelector(".quiz-locked")) {
      renderCurrentModule();
    }
  } catch (e) {}
}

// ─── Quiz submission ────────────────────────────────────────────────────
window.submitQuiz = async function(module_id) {
  const reponses = {};
  document.querySelectorAll(".q-block").forEach(block => {
    const qid = block.dataset.qid;
    const sel = block.querySelector('input[type=radio]:checked');
    if (sel) reponses[qid] = parseInt(sel.value);
  });
  const totalQ = document.querySelectorAll(".q-block").length;
  if (Object.keys(reponses).length < totalQ) {
    toast("Répondez à toutes les questions avant de valider", "danger");
    return;
  }
  try {
    const r = await api("/api/learning/modules/" + module_id + "/quiz",
      { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reponses: reponses }) });
    const resEl = document.getElementById("quiz-result");
    if (r.score >= r.seuil) {
      resEl.className = "quiz-result ok";
      resEl.textContent = `Score : ${r.score}% — Module validé.`;
      if (r.valide_le) toast("Module validé !", "success");
    } else {
      resEl.className = "quiz-result ko";
      resEl.textContent = `Score : ${r.score}% (seuil ${r.seuil}%). Ré-essayez.`;
    }
    // Refresh la progression + le quiz visuel
    const data = await api("/api/learning/formations/" + S.current_formation.formation.id);
    S.current_formation = data;
    setTimeout(() => renderCurrentModule(), 1500);
  } catch (e) {
    toast(e.message, "danger");
  }
};

// ─── Thème persistant ───────────────────────────────────────────────────
(function initTheme() {
  const saved = localStorage.getItem("mysifa_theme");
  if (saved === "light") document.body.classList.add("light");
})();

// ─── Boot ───────────────────────────────────────────────────────────────
loadYtApi();
route();
</script>
</body>
</html>
"""


# ═════════════════════════════════════════════════════════════════════════
# ─── ÉCRAN ADMIN (superadmin uniquement) ─────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════
LEARNING_ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>MyLearning Admin — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--warn:#fbbf24;--danger:#f87171}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--warn:#d97706;--danger:#dc2626}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.wrap{max-width:1200px;margin:0 auto;padding:24px 20px 80px}
.topbar{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.brand{font-size:22px;font-weight:800}
.brand span{color:var(--accent)}
.admin-tag{padding:3px 10px;border-radius:6px;background:rgba(251,191,36,.16);color:var(--warn);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.spacer{flex:1}
.link{color:var(--text2);text-decoration:none;font-size:13px;padding:8px 14px;border-radius:8px;border:1px solid transparent}
.link:hover{background:var(--accent-bg);color:var(--accent)}

.layout{display:grid;grid-template-columns:280px 1fr;gap:20px}
@media (max-width:900px){.layout{grid-template-columns:1fr}}
.sidebar{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;height:fit-content}
.sidebar h3{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin:0 0 12px}
.f-list{display:flex;flex-direction:column;gap:4px;margin-bottom:12px}
.f-btn{display:block;text-align:left;padding:10px 12px;border-radius:8px;border:1px solid transparent;background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px;transition:all .15s}
.f-btn:hover{background:var(--accent-bg);color:var(--accent)}
.f-btn.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);font-weight:700}
.f-btn small{display:block;color:var(--muted);font-weight:400;font-size:10px;margin-top:2px}
.btn{padding:9px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px;transition:all .15s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn-accent{background:var(--accent);color:#0a0e17;border-color:var(--accent);font-weight:700}
.btn-accent:hover{color:#0a0e17;filter:brightness(1.1)}
.btn-danger:hover{border-color:var(--danger);color:var(--danger)}
.btn-full{width:100%}

.content{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;min-height:400px}
.content h2{margin:0 0 4px;font-size:20px}
.content .role-sub{color:var(--muted);font-size:12px;margin-bottom:20px}
.section{margin-top:32px}
.section-title{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:12px;display:flex;align-items:center;justify-content:space-between}
.section-title .btn{padding:4px 10px;font-size:11px}

.form-row{display:grid;grid-template-columns:180px 1fr;gap:12px;margin-bottom:12px;align-items:center}
.form-row label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.form-row input, .form-row textarea, .form-row select{width:100%;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:inherit;font-size:13px}
.form-row input:focus,.form-row textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.form-row textarea{min-height:60px;resize:vertical}
.form-actions{display:flex;gap:8px;margin-top:16px}

.mod-block{padding:14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:12px}
.mod-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.mod-head b{font-size:14px}
.mod-actions{display:flex;gap:6px}
.mod-sub{font-size:11px;color:var(--muted);margin-bottom:10px}
.chip{display:inline-block;padding:2px 8px;background:var(--accent-bg);color:var(--accent);border-radius:4px;font-size:10px;font-weight:600;margin-right:4px}
.chip-warn{background:rgba(251,191,36,.16);color:var(--warn)}
.item-list{margin-left:12px}
.item{padding:8px 10px;background:var(--card);border:1px solid var(--border);border-radius:6px;margin-bottom:4px;display:flex;align-items:center;gap:8px;font-size:12px}
.item .yid{font-family:'JetBrains Mono',ui-monospace,monospace;color:var(--muted);font-size:10px}
.item .name{flex:1}
.perm-list{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.perm-chip{padding:5px 10px;border-radius:6px;background:var(--bg);border:1px solid var(--border);font-size:11px;cursor:pointer;transition:all .1s;user-select:none}
.perm-chip:hover{border-color:var(--accent)}
.perm-chip.selected{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);font-weight:700}
.perm-tranche{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-top:8px;margin-bottom:4px}

.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;max-width:560px;width:100%;max-height:90vh;overflow-y:auto}
.modal h3{margin:0 0 16px;font-size:16px}
.toast-zone{position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{padding:12px 16px;border-radius:8px;font-size:13px;font-weight:600;color:#0a0e17}
.toast.success{background:var(--ok)}
.toast.info{background:var(--accent)}
.toast.danger{background:var(--danger)}
.empty{padding:24px;text-align:center;color:var(--muted);font-size:13px;border:1px dashed var(--border);border-radius:8px}
</style>
</head>
<body>
<div id="toast-zone" class="toast-zone"></div>
<div id="mroot"></div>
<div class="wrap">
  <div class="topbar">
    <div class="brand">My<span>Learning</span></div>
    <span class="admin-tag">Admin</span>
    <div class="spacer"></div>
    <a href="/learning" class="link">← Vue apprenant</a>
    <a href="/" class="link">Portail</a>
  </div>

  <div class="layout">
    <aside class="sidebar">
      <h3>Parcours</h3>
      <div id="formations-list" class="f-list"><div style="color:var(--muted);font-size:12px">Chargement…</div></div>
      <button class="btn btn-accent btn-full" onclick="openNewFormation()">+ Nouveau parcours</button>
    </aside>
    <main class="content" id="content">
      <div class="empty">Sélectionnez un parcours à gauche, ou créez-en un nouveau.</div>
    </main>
  </div>
</div>

<script>
const A = {
  formations: [],
  current: null,
  permCatalog: null,
};

// ─── API + helpers ──────────────────────────────────────────────────────
async function api(path, opts) {
  const r = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
  if (r.status === 401) { location.href = "/?next=/learning/admin"; return null; }
  if (!r.ok) {
    let msg = "Erreur " + r.status;
    try { const j = await r.json(); msg = j.detail?.message || j.detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.json();
}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function toast(msg,type){const d=document.createElement("div");d.className="toast "+(type||"info");d.textContent=msg;document.getElementById("toast-zone").appendChild(d);setTimeout(()=>d.remove(),3500);}
function openModal(html){document.getElementById("mroot").innerHTML=`<div class="modal-back" onclick="if(event.target===this)closeModal()"><div class="modal">${html}</div></div>`;}
window.closeModal=function(){document.getElementById("mroot").innerHTML="";};

// ─── Formations list ────────────────────────────────────────────────────
async function loadFormations() {
  const data = await api("/api/learning/admin/formations");
  if (!data) return;
  A.formations = data.formations;
  const el = document.getElementById("formations-list");
  if (!A.formations.length) { el.innerHTML = '<div style="color:var(--muted);font-size:12px">Aucun parcours créé</div>'; return; }
  el.innerHTML = A.formations.map(f => `
    <button class="f-btn ${A.current && A.current.id === f.id ? 'active' : ''}"
            onclick="selectFormation(${f.id})">
      ${esc(f.titre)}
      <small>${f.nb_modules} module${f.nb_modules>1?'s':''} · ${f.nb_permissions} perm${f.nb_permissions>1?'s':''}${f.actif?'':' · inactif'}</small>
    </button>
  `).join("");
}

window.selectFormation = async function(fid) {
  const [full, cat] = await Promise.all([
    api("/api/learning/admin/formations/" + fid),
    A.permCatalog ? Promise.resolve(A.permCatalog) : api("/api/learning/permissions/catalog")
  ]);
  if (!full) return;
  A.current = full.formation;
  A.current.modules = full.modules;
  A.current.permissions = full.permissions;
  A.permCatalog = cat;
  loadFormations();
  renderFormationEdit();
};

// ─── Formation edit ─────────────────────────────────────────────────────
function renderFormationEdit() {
  const f = A.current;
  const el = document.getElementById("content");
  el.innerHTML = `
    <h2>${esc(f.titre)}</h2>
    <div class="role-sub">Code : <code style="background:var(--bg);padding:2px 6px;border-radius:4px;font-size:11px">${esc(f.code)}</code>${f.role_cible ? ' · Rôle cible : ' + esc(f.role_cible) : ''}</div>

    <div class="section">
      <div class="section-title">Informations</div>
      <div class="form-row"><label>Titre</label><input id="f-titre" value="${esc(f.titre)}"></div>
      <div class="form-row"><label>Description</label><textarea id="f-desc">${esc(f.description)}</textarea></div>
      <div class="form-row"><label>Rôle cible</label><input id="f-role" value="${esc(f.role_cible)}" placeholder="ex : Opérateur Cohésio"></div>
      <div class="form-row"><label>Ordre d'affichage</label><input id="f-ordre" type="number" value="${f.ordre}"></div>
      <div class="form-row"><label>Actif</label><select id="f-actif"><option value="1" ${f.actif?'selected':''}>Actif</option><option value="0" ${!f.actif?'selected':''}>Inactif</option></select></div>
      <div class="form-actions">
        <button class="btn btn-accent" onclick="saveFormation()">Enregistrer</button>
        <button class="btn btn-danger" onclick="deleteFormation()">Supprimer</button>
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        <span>Modules (${f.modules.length})</span>
        <button class="btn btn-accent" onclick="openNewModule()">+ Ajouter</button>
      </div>
      ${renderModules()}
    </div>

    <div class="section">
      <div class="section-title">Permissions débloquées (${f.permissions.length})</div>
      ${renderPermissions()}
      <div class="form-actions"><button class="btn btn-accent" onclick="savePermissions()">Enregistrer les permissions</button></div>
    </div>
  `;
}

function renderModules() {
  const mods = A.current.modules;
  if (!mods.length) return '<div class="empty">Aucun module créé. Ajoutez le premier chapitre du parcours.</div>';
  return mods.map(m => `
    <div class="mod-block">
      <div class="mod-head">
        <div>
          <b>${esc(m.titre)}</b>
          <span class="chip">${m.videos.length} vidéo${m.videos.length>1?'s':''}</span>
          <span class="chip ${m.quiz.length===0?'chip-warn':''}">${m.quiz.length} question${m.quiz.length>1?'s':''}</span>
          ${m.actif ? '' : '<span class="chip chip-warn">Inactif</span>'}
        </div>
        <div class="mod-actions">
          <button class="btn" onclick="openEditModule(${m.id})">Éditer</button>
          <button class="btn btn-danger" onclick="deleteModule(${m.id})">Suppr</button>
        </div>
      </div>
      ${m.description ? `<div class="mod-sub">${esc(m.description)}</div>` : ''}
      <div class="item-list">
        ${m.videos.map(v => `
          <div class="item">
            <span class="name">${esc(v.titre)}</span>
            <span class="yid">${esc(v.youtube_id)}${v.duree_sec?` · ${Math.round(v.duree_sec/60)}min`:''}</span>
            <button class="btn" onclick="openEditVideo(${m.id},${v.id})">✎</button>
            <button class="btn btn-danger" onclick="deleteVideo(${v.id})">×</button>
          </div>`).join("")}
        <div class="item" style="border-style:dashed">
          <button class="btn" onclick="openNewVideo(${m.id})">+ Ajouter une vidéo</button>
          <span style="flex:1"></span>
        </div>
        ${m.quiz.map((q, i) => `
          <div class="item">
            <span class="name">Q${i+1}. ${esc(q.question)}</span>
            <span class="yid">Bonne : ${esc(q.choix[q.bonne_reponse] || '?')}</span>
            <button class="btn" onclick="openEditQuestion(${m.id},${q.id})">✎</button>
            <button class="btn btn-danger" onclick="deleteQuestion(${q.id})">×</button>
          </div>`).join("")}
        <div class="item" style="border-style:dashed">
          <button class="btn" onclick="openNewQuestion(${m.id})">+ Ajouter une question</button>
          <span style="flex:1"></span>
        </div>
      </div>
    </div>
  `).join("");
}

function renderPermissions() {
  const selected = new Set(A.current.permissions);
  const cat = A.permCatalog;
  const chip = c => `<span class="perm-chip ${selected.has(c.code)?'selected':''}" data-code="${c.code}" onclick="togglePerm(this)">${esc(c.label)}</span>`;
  return `
    <div class="perm-tranche">Tranche 1 (MVP)</div>
    <div class="perm-list">${cat.tranche_1.map(chip).join("")}</div>
    <div class="perm-tranche">Tranche 2</div>
    <div class="perm-list">${cat.tranche_2.map(chip).join("")}</div>
    <div class="perm-tranche">Tranche 3</div>
    <div class="perm-list">${cat.tranche_3.map(chip).join("")}</div>
  `;
}

window.togglePerm = function(el) { el.classList.toggle("selected"); };

async function savePermissions() {
  const codes = Array.from(document.querySelectorAll(".perm-chip.selected")).map(x => x.dataset.code);
  try {
    await api("/api/learning/admin/formations/" + A.current.id + "/permissions",
      { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify({permissions: codes})});
    A.current.permissions = codes;
    toast("Permissions enregistrées", "success");
    loadFormations();
  } catch (e) { toast(e.message, "danger"); }
}

async function saveFormation() {
  const payload = {
    titre: document.getElementById("f-titre").value.trim(),
    description: document.getElementById("f-desc").value.trim(),
    role_cible: document.getElementById("f-role").value.trim(),
    ordre: parseInt(document.getElementById("f-ordre").value || "100"),
    actif: document.getElementById("f-actif").value === "1",
  };
  try {
    await api("/api/learning/admin/formations/" + A.current.id,
      { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    Object.assign(A.current, payload);
    toast("Parcours enregistré", "success");
    loadFormations();
    renderFormationEdit();
  } catch (e) { toast(e.message, "danger"); }
}

async function deleteFormation() {
  if (!confirm("Supprimer ce parcours ? Toutes les données (modules, quiz, progression) seront perdues.")) return;
  try {
    await api("/api/learning/admin/formations/" + A.current.id, {method:"DELETE"});
    A.current = null;
    toast("Parcours supprimé", "success");
    document.getElementById("content").innerHTML = '<div class="empty">Sélectionnez un parcours à gauche.</div>';
    loadFormations();
  } catch (e) { toast(e.message, "danger"); }
}

// ─── Modales : nouveau parcours ─────────────────────────────────────────
window.openNewFormation = function() {
  openModal(`
    <h3>Nouveau parcours</h3>
    <div class="form-row"><label>Code technique</label><input id="n-code" placeholder="operateur_cohesio"></div>
    <div class="form-row"><label>Titre</label><input id="n-titre" placeholder="Opérateur Cohésio"></div>
    <div class="form-row"><label>Description</label><textarea id="n-desc"></textarea></div>
    <div class="form-row"><label>Rôle cible</label><input id="n-role" placeholder="Opérateur Cohésio"></div>
    <div class="form-row"><label>Ordre</label><input id="n-ordre" type="number" value="100"></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="createFormation()">Créer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.createFormation = async function() {
  const payload = {
    code: document.getElementById("n-code").value.trim().toLowerCase(),
    titre: document.getElementById("n-titre").value.trim(),
    description: document.getElementById("n-desc").value.trim(),
    role_cible: document.getElementById("n-role").value.trim(),
    ordre: parseInt(document.getElementById("n-ordre").value || "100"),
    actif: true,
  };
  if (!payload.code || !payload.titre) { toast("Code et titre requis", "danger"); return; }
  try {
    const r = await api("/api/learning/admin/formations",
      { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Parcours créé", "success");
    await loadFormations();
    selectFormation(r.id);
  } catch (e) { toast(e.message, "danger"); }
};

// ─── Modales : module ───────────────────────────────────────────────────
window.openNewModule = function() {
  openModal(`
    <h3>Nouveau module</h3>
    <div class="form-row"><label>Titre</label><input id="nm-titre" placeholder="Chapitre 1 - Connexion"></div>
    <div class="form-row"><label>Description</label><textarea id="nm-desc"></textarea></div>
    <div class="form-row"><label>Ordre</label><input id="nm-ordre" type="number" value="100"></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="createModule()">Créer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.createModule = async function() {
  const payload = {
    titre: document.getElementById("nm-titre").value.trim(),
    description: document.getElementById("nm-desc").value.trim(),
    ordre: parseInt(document.getElementById("nm-ordre").value || "100"),
  };
  if (!payload.titre) { toast("Titre requis", "danger"); return; }
  try {
    await api("/api/learning/admin/formations/" + A.current.id + "/modules",
      { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Module créé", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};

window.openEditModule = function(mid) {
  const m = A.current.modules.find(x => x.id === mid);
  openModal(`
    <h3>Éditer le module</h3>
    <div class="form-row"><label>Titre</label><input id="em-titre" value="${esc(m.titre)}"></div>
    <div class="form-row"><label>Description</label><textarea id="em-desc">${esc(m.description)}</textarea></div>
    <div class="form-row"><label>Ordre</label><input id="em-ordre" type="number" value="${m.ordre}"></div>
    <div class="form-row"><label>Actif</label><select id="em-actif"><option value="1" ${m.actif?'selected':''}>Actif</option><option value="0" ${!m.actif?'selected':''}>Inactif</option></select></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="saveModule(${mid})">Enregistrer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.saveModule = async function(mid) {
  const payload = {
    titre: document.getElementById("em-titre").value.trim(),
    description: document.getElementById("em-desc").value.trim(),
    ordre: parseInt(document.getElementById("em-ordre").value || "100"),
    actif: document.getElementById("em-actif").value === "1",
  };
  try {
    await api("/api/learning/admin/modules/" + mid,
      { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Module enregistré", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};
window.deleteModule = async function(mid) {
  if (!confirm("Supprimer ce module et tout son contenu ?")) return;
  try {
    await api("/api/learning/admin/modules/" + mid, {method:"DELETE"});
    toast("Module supprimé", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};

// ─── Modales : vidéo ────────────────────────────────────────────────────
window.openNewVideo = function(mid) {
  openModal(`
    <h3>Nouvelle vidéo</h3>
    <div class="form-row"><label>Titre</label><input id="nv-titre" placeholder="Vidéo 1 - Se connecter"></div>
    <div class="form-row"><label>URL YouTube</label><input id="nv-url" placeholder="https://youtu.be/... ou ID 11 caractères"></div>
    <div class="form-row"><label>Durée (secondes)</label><input id="nv-duree" type="number" value="0" placeholder="Optionnel — pour affichage"></div>
    <div class="form-row"><label>Ordre</label><input id="nv-ordre" type="number" value="100"></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="createVideo(${mid})">Créer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.createVideo = async function(mid) {
  const payload = {
    titre: document.getElementById("nv-titre").value.trim(),
    youtube_url: document.getElementById("nv-url").value.trim(),
    duree_sec: parseInt(document.getElementById("nv-duree").value || "0"),
    ordre: parseInt(document.getElementById("nv-ordre").value || "100"),
  };
  if (!payload.titre || !payload.youtube_url) { toast("Titre et URL requis", "danger"); return; }
  try {
    await api("/api/learning/admin/modules/" + mid + "/videos",
      { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Vidéo ajoutée", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};

window.openEditVideo = function(mid, vid) {
  const v = A.current.modules.find(m=>m.id===mid).videos.find(x => x.id === vid);
  openModal(`
    <h3>Éditer la vidéo</h3>
    <div class="form-row"><label>Titre</label><input id="ev-titre" value="${esc(v.titre)}"></div>
    <div class="form-row"><label>URL YouTube</label><input id="ev-url" value="${esc(v.youtube_id)}"></div>
    <div class="form-row"><label>Durée (secondes)</label><input id="ev-duree" type="number" value="${v.duree_sec}"></div>
    <div class="form-row"><label>Ordre</label><input id="ev-ordre" type="number" value="${v.ordre}"></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="saveVideo(${vid})">Enregistrer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.saveVideo = async function(vid) {
  const payload = {
    titre: document.getElementById("ev-titre").value.trim(),
    youtube_url: document.getElementById("ev-url").value.trim(),
    duree_sec: parseInt(document.getElementById("ev-duree").value || "0"),
    ordre: parseInt(document.getElementById("ev-ordre").value || "100"),
  };
  try {
    await api("/api/learning/admin/videos/" + vid,
      { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Vidéo enregistrée", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};
window.deleteVideo = async function(vid) {
  if (!confirm("Supprimer cette vidéo ?")) return;
  try {
    await api("/api/learning/admin/videos/" + vid, {method:"DELETE"});
    toast("Vidéo supprimée", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};

// ─── Modales : question de quiz ─────────────────────────────────────────
function renderChoixInputs(prefix, choix, bonne) {
  return choix.map((c, i) => `
    <div class="form-row">
      <label>${i === bonne ? '<span style="color:var(--ok)">✓</span>' : ''} Choix ${i+1}</label>
      <div style="display:flex;gap:6px">
        <input id="${prefix}-choix-${i}" value="${esc(c)}" style="flex:1">
        <button class="btn" onclick="document.getElementById('${prefix}-bonne').value=${i};document.getElementById('${prefix}-bonne-lbl').textContent=${i+1}">Bonne</button>
      </div>
    </div>
  `).join("");
}
window.openNewQuestion = function(mid) {
  openModal(`
    <h3>Nouvelle question</h3>
    <div class="form-row"><label>Question</label><textarea id="nq-question" placeholder="Comment démarrer une machine ?"></textarea></div>
    ${renderChoixInputs('nq', ['','','',''], 0)}
    <input type="hidden" id="nq-bonne" value="0">
    <div class="form-row"><label>Bonne réponse</label><span id="nq-bonne-lbl">1</span> (cliquer sur "Bonne" à côté du bon choix)</div>
    <div class="form-row"><label>Explication (optionnel)</label><textarea id="nq-explain" placeholder="Affichée après validation"></textarea></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="createQuestion(${mid})">Créer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.createQuestion = async function(mid) {
  const choix = [0,1,2,3].map(i => document.getElementById("nq-choix-"+i).value.trim());
  if (choix.some(c => !c)) { toast("Les 4 choix doivent être remplis", "danger"); return; }
  const payload = {
    question: document.getElementById("nq-question").value.trim(),
    choix: choix,
    bonne_reponse: parseInt(document.getElementById("nq-bonne").value),
    explication: document.getElementById("nq-explain").value.trim(),
    ordre: 100,
  };
  if (!payload.question) { toast("Question requise", "danger"); return; }
  try {
    await api("/api/learning/admin/modules/" + mid + "/quiz",
      { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Question ajoutée", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};

window.openEditQuestion = function(mid, qid) {
  const q = A.current.modules.find(m=>m.id===mid).quiz.find(x => x.id === qid);
  // Pad choix à 4 minimum pour l'affichage.
  const choixPadded = [...q.choix];
  while (choixPadded.length < 4) choixPadded.push("");
  openModal(`
    <h3>Éditer la question</h3>
    <div class="form-row"><label>Question</label><textarea id="eq-question">${esc(q.question)}</textarea></div>
    ${renderChoixInputs('eq', choixPadded, q.bonne_reponse)}
    <input type="hidden" id="eq-bonne" value="${q.bonne_reponse}">
    <div class="form-row"><label>Bonne réponse</label><span id="eq-bonne-lbl">${q.bonne_reponse+1}</span></div>
    <div class="form-row"><label>Explication</label><textarea id="eq-explain">${esc(q.explication)}</textarea></div>
    <div class="form-row"><label>Ordre</label><input id="eq-ordre" type="number" value="${q.ordre}"></div>
    <div class="form-actions">
      <button class="btn btn-accent" onclick="saveQuestion(${qid})">Enregistrer</button>
      <button class="btn" onclick="closeModal()">Annuler</button>
    </div>
  `);
};
window.saveQuestion = async function(qid) {
  const choix = [0,1,2,3].map(i => document.getElementById("eq-choix-"+i).value.trim());
  if (choix.some(c => !c)) { toast("Les 4 choix doivent être remplis", "danger"); return; }
  const payload = {
    question: document.getElementById("eq-question").value.trim(),
    choix: choix,
    bonne_reponse: parseInt(document.getElementById("eq-bonne").value),
    explication: document.getElementById("eq-explain").value.trim(),
    ordre: parseInt(document.getElementById("eq-ordre").value || "100"),
  };
  try {
    await api("/api/learning/admin/quiz/" + qid,
      { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    closeModal();
    toast("Question enregistrée", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};
window.deleteQuestion = async function(qid) {
  if (!confirm("Supprimer cette question ?")) return;
  try {
    await api("/api/learning/admin/quiz/" + qid, {method:"DELETE"});
    toast("Question supprimée", "success");
    selectFormation(A.current.id);
  } catch (e) { toast(e.message, "danger"); }
};

// ─── Thème ──────────────────────────────────────────────────────────────
(function initTheme() {
  const saved = localStorage.getItem("mysifa_theme");
  if (saved === "light") document.body.classList.add("light");
})();

loadFormations();
</script>
</body>
</html>
"""
