/* MySifa — Moteur de guide in-app partagé (générique, réutilisable)
 * Auto-suffisant : injecte son CSS, gère sa modale (#mysifa-guide-root),
 * ses appels /api/guides/* et le gating superadmin de l'auto-open.
 * API : configure({role}), register(key,{steps}), registerMany(obj),
 *       boot(), open(key,{autoOpened}), autoOpen(key), isAcked(key).
 */
(function(){
  "use strict";
  if(window.MySifaGuides) return;

  var registry = {};
  var progress = {};
  var ackedKeys = new Set();
  var openedThisSession = new Set();
  var role = "";
  var loaded = false;
  var st = { key:null, idx:0, bitmap:0, startMs:0, lastStepMs:0 };
  var currentKey = null;
  var chain = null;
  var chainIdx = 0;

  function gfetch(path, opts){ opts = opts || {}; opts.credentials = "include"; return fetch(path, opts); }
  function jbody(o){ return { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(o) }; }
  function bitCount(n){ n = n>>>0; var c=0; while(n){ c += n&1; n = n>>>1; } return c; }
  function bitmapFull(total){ return (1<<total) - 1; }
  function deltaMs(){ return st.lastStepMs ? (Date.now() - st.lastStepMs) : 0; }

  function toast(msg, type){
    try{ if(typeof window.showToast === "function"){ window.showToast(msg, type); return; } }catch(e){}
    var d = document.createElement("div");
    d.className = "mguide-toast " + (type||"");
    d.textContent = msg;
    document.body.appendChild(d);
    requestAnimationFrame(function(){ d.classList.add("show"); });
    setTimeout(function(){ d.classList.remove("show"); setTimeout(function(){ d.remove(); }, 300); }, 2600);
  }

  function configure(o){ o = o || {}; if(o.role != null) role = String(o.role || ""); }
  function register(key, g){ if(!key || !g || !Array.isArray(g.steps)) return; registry[key] = g; }
  function registerMany(obj){ Object.keys(obj||{}).forEach(function(k){ register(k, obj[k]); }); }
  function isAcked(key){ return ackedKeys.has(key); }

  function boot(){
    injectCSS();
    return gfetch("/api/guides/progress").then(function(r){ return r.ok ? r.json() : null; }).then(function(rows){
      if(rows){
        progress = {}; ackedKeys = new Set();
        rows.forEach(function(row){ progress[row.guide_key] = row; if(row.acknowledged_at) ackedKeys.add(row.guide_key); });
      }
      loaded = true;
    }).catch(function(){ loaded = true; });
  }

  function postOpen(key, total){ gfetch("/api/guides/open", jbody({guide_key:key, total_steps:total})).catch(function(){}); }
  function postHeartbeat(key, idx, total, dms){ gfetch("/api/guides/heartbeat", jbody({guide_key:key, step_idx:idx, total_steps:total, delta_ms:dms})).catch(function(){}); }
  function postAck(key){
    var g = registry[key]; var total = (g && g.steps) ? g.steps.length : 0;
    return gfetch("/api/guides/ack", jbody({guide_key:key, client_bitmap: st.bitmap|0, client_total_steps: total}))
      .then(function(r){ if(r.ok){ ackedKeys.add(key); return true; } return false; })
      .catch(function(){ return false; });
  }

  function autoOpen(key){
    if(registry[key]){ currentKey = key; updateHelpBtn(); }
    if(role !== "superadmin") return;
    if(!loaded) return;
    if(!registry[key]) return;
    if(ackedKeys.has(key)) return;
    if(openedThisSession.has(key)) return;
    openedThisSession.add(key);
    setTimeout(function(){ open(key, {autoOpened:true}); }, 400);
  }

  function _chainStep(){
    if(!chain) return;
    while(chainIdx < chain.length){
      var k = chain[chainIdx];
      if(role === "superadmin" && loaded && registry[k] && !ackedKeys.has(k) && !openedThisSession.has(k)){
        openedThisSession.add(k);
        (function(kk){ setTimeout(function(){ open(kk, {autoOpened:true}); }, 300); })(k);
        return;
      }
      chainIdx++;
    }
  }
  function autoOpenChain(keys){
    keys = (keys||[]).filter(function(k){ return registry[k]; });
    chain = keys; chainIdx = 0;
    if(keys.length){ currentKey = keys[keys.length-1]; }
    _chainStep();
  }

  function mountEl(){
    var m = document.getElementById("mysifa-guide-root");
    if(!m){ m = document.createElement("div"); m.id = "mysifa-guide-root"; document.body.appendChild(m); }
    return m;
  }
  function closeGuide(){
    var key = st.key;
    if(key){ var g = registry[key]; if(g){ var dms = deltaMs(); if(dms > 0) postHeartbeat(key, st.idx||0, g.steps.length, dms); } }
    st = { key:null, idx:0, bitmap:0, startMs:0, lastStepMs:0 };
    var m = document.getElementById("mysifa-guide-root");
    if(m) m.innerHTML = "";
    document.removeEventListener("keydown", onKey);
    if(chain && chainIdx < chain.length && chain[chainIdx] === key){ chainIdx++; setTimeout(_chainStep, 350); }
  }

  function open(key, opts){
    var g = registry[key];
    if(!g) return;
    injectCSS();
    opts = opts || {};
    var total = g.steps.length;
    var prog = progress[key];
    st = { key:key, idx:0, bitmap: prog ? (prog.steps_seen_bitmap|0) : 0, startMs: Date.now(), lastStepMs: Date.now() };
    st.bitmap |= 1;
    postOpen(key, total);

    var alreadyAcked = ackedKeys.has(key);
    var autoHint = opts.autoOpened && !alreadyAcked
      ? '<div class="mguide-ack-info">Ce guide s\'affiche automatiquement à votre première visite.</div>'
      : (alreadyAcked ? '<div class="mguide-ack-info"><span class="mguide-ack-badge">✓ Validé</span> Vous avez déjà validé ce guide.</div>' : '');

    var stepsHtml = g.steps.map(function(s, i){
      return '<div class="mguide-step ' + (i===0?'active':'') + '" data-idx="'+i+'">'
        + ((s.icon && !s.illu) ? '<div class="mguide-icon">'+s.icon+'</div>' : '')
        + '<h3 class="mguide-tit">'+s.title+'</h3>'
        + '<p class="mguide-body">'+s.body+'</p>'
        + (s.extra || '')
        + (s.illu ? '<div class="mguide-illu">'+s.illu+'</div>' : '')
        + '</div>';
    }).join('');

    var dotsHtml = g.steps.map(function(_, i){
      return '<button type="button" class="mguide-dot '+(i===0?'active':'')+'" data-idx="'+i+'" onclick="MySifaGuides._nav('+i+')" aria-label="Étape '+(i+1)+'"></button>';
    }).join('');

    var m = mountEl();
    m.innerHTML = '<div class="mguide-ov" onclick="if(event.target===this)MySifaGuides._close()">'
      + '<div class="mguide" role="dialog">'
      + '<button type="button" class="mguide-close" aria-label="Fermer" onclick="MySifaGuides._close()">×</button>'
      + '<div class="mguide-progress"><div class="mguide-progress-bar" id="mguide-bar" style="width:'+((1/total)*100).toFixed(1)+'%"></div></div>'
      + '<div class="mguide-viewport" id="mguide-viewport">'+stepsHtml+'</div>'
      + '<div class="mguide-nav">'
      + '<div class="mguide-dots">'+dotsHtml+'</div>'
      + '<div class="mguide-nav-btns">'
      + '<button type="button" class="mguide-nav-btn" id="mguide-prev" onclick="MySifaGuides._nav(MySifaGuides._idx()-1)" disabled>Précédent</button>'
      + '<button type="button" class="mguide-nav-btn primary" id="mguide-next" onclick="MySifaGuides._nav(MySifaGuides._idx()+1)">Suivant →</button>'
      + '</div></div>'
      + '<div class="mguide-ack-row"><button type="button" class="mguide-ack-btn" id="mguide-ack" onclick="MySifaGuides._ack()" disabled></button>'+autoHint+'</div>'
      + '</div></div>';
    updateAckButton();
    document.addEventListener("keydown", onKey);
  }

  function onKey(e){
    if(!document.querySelector(".mguide-ov")){ document.removeEventListener("keydown", onKey); return; }
    if(e.key === "Escape"){ closeGuide(); }
    else if(e.key === "ArrowRight"){ nav(st.idx+1); }
    else if(e.key === "ArrowLeft"){ nav(st.idx-1); }
  }

  function nav(newIdx){
    var g = registry[st.key];
    if(!g) return;
    var total = g.steps.length;
    if(newIdx < 0 || newIdx >= total) return;
    var oldIdx = st.idx;
    if(newIdx === oldIdx) return;
    var dir = newIdx > oldIdx ? 1 : -1;
    var vp = document.getElementById("mguide-viewport");
    if(!vp) return;
    var steps = vp.querySelectorAll(".mguide-step");
    steps.forEach(function(s, i){
      s.classList.remove("active","from-left","from-right","to-left","to-right");
      if(i === newIdx){
        s.classList.add(dir>0 ? "from-right" : "from-left");
        void s.offsetWidth;
        s.classList.remove("from-right","from-left");
        s.classList.add("active");
      } else if(i === oldIdx){
        s.classList.add(dir>0 ? "to-left" : "to-right");
      }
    });
    st.bitmap |= (1 << newIdx);
    postHeartbeat(st.key, newIdx, total, deltaMs());
    st.lastStepMs = Date.now();
    st.idx = newIdx;
    document.querySelectorAll(".mguide-dot").forEach(function(d, i){ d.classList.toggle("active", i===newIdx); });
    var bar = document.getElementById("mguide-bar");
    if(bar) bar.style.width = (((newIdx+1)/total)*100).toFixed(1) + "%";
    var prevBtn = document.getElementById("mguide-prev");
    var nextBtn = document.getElementById("mguide-next");
    if(prevBtn) prevBtn.disabled = (newIdx === 0);
    if(nextBtn){ nextBtn.textContent = (newIdx === total-1) ? "Dernière étape" : "Suivant →"; nextBtn.disabled = (newIdx === total-1); }
    updateAckButton();
  }

  function updateAckButton(){
    var btn = document.getElementById("mguide-ack");
    if(!btn) return;
    var g = registry[st.key];
    if(!g) return;
    var total = g.steps.length;
    var full = bitmapFull(total);
    var complete = (st.bitmap & full) === full;
    var alreadyAcked = ackedKeys.has(st.key);
    btn.disabled = !complete;
    if(alreadyAcked){
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Déjà validé — fermer';
    } else if(complete){
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> J\'ai compris — clôturer';
    } else {
      var seen = bitCount(st.bitmap & full);
      btn.innerHTML = '<span class="mguide-ack-lock"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></span><span>Voyez toutes les étapes pour valider</span><span class="mguide-ack-chip">'+seen+'/'+total+'</span>';
    }
  }

  function ack(){
    var key = st.key;
    if(!key) return;
    if(ackedKeys.has(key)){ closeGuide(); return; }
    postAck(key).then(function(ok){
      if(!ok){ toast("Impossible de valider (voyez toutes les étapes)", "danger"); return; }
      toast("Formation validée ✓", "success");
      closeGuide();
    });
  }

  function injectCSS(){
    if(document.getElementById("mysifa-guide-css")) return;
    var s = document.createElement("style");
    s.id = "mysifa-guide-css";
    s.textContent = MGUIDE_CSS;
    document.head.appendChild(s);
  }

  var MGUIDE_CSS = ""
+ ".mguide-ov{position:fixed;inset:0;background:rgba(0,0,0,.68);z-index:20000;display:flex;align-items:center;justify-content:center;padding:16px;animation:mguideOvIn .2s ease-out}"
+ "@media(min-width:900px){.mguide-ov{left:220px;padding-left:24px}}"
+ "@keyframes mguideOvIn{from{opacity:0}to{opacity:1}}"
+ ".mguide{background:var(--card);border:1px solid var(--border);border-radius:20px;width:100%;max-width:820px;position:relative;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.5);animation:mguideIn .28s cubic-bezier(.34,1.56,.64,1)}"
+ "@keyframes mguideIn{from{opacity:0;transform:scale(.9) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}"
+ ".mguide-close{position:absolute;top:14px;right:14px;background:transparent;border:none;color:var(--muted);cursor:pointer;font-size:22px;line-height:1;padding:6px 10px;border-radius:8px;transition:.15s;z-index:5}"
+ ".mguide-close:hover{color:var(--danger);background:rgba(248,113,113,.1)}"
+ ".mguide-progress{height:3px;background:var(--border);width:100%;overflow:hidden}"
+ ".mguide-progress-bar{height:100%;background:linear-gradient(90deg,var(--accent),var(--ok,#34d399));transition:width .35s cubic-bezier(.4,0,.2,1);border-radius:0 3px 3px 0}"
+ ".mguide-viewport{position:relative;min-height:460px;max-height:65vh;overflow:hidden}"
+ ".mguide-step{position:absolute;inset:0;padding:32px 44px 24px;display:flex;flex-direction:column;align-items:center;text-align:center;opacity:0;transform:translateX(100%);transition:opacity .3s ease,transform .35s cubic-bezier(.4,0,.2,1);overflow-y:auto;pointer-events:none}"
+ ".mguide-step.active{opacity:1;transform:translateX(0);pointer-events:auto}"
+ ".mguide-step.from-right{transform:translateX(100%);opacity:0;transition:none}"
+ ".mguide-step.from-left{transform:translateX(-100%);opacity:0;transition:none}"
+ ".mguide-step.to-right{transform:translateX(100%);opacity:0}"
+ ".mguide-step.to-left{transform:translateX(-100%);opacity:0}"
+ ".mguide-illu{width:100%;max-width:660px;height:330px;border-radius:14px;background:var(--bg);border:1px solid var(--border);margin-top:14px;margin-bottom:4px;padding:14px;box-sizing:border-box;overflow:hidden;position:relative}"
+ ".mguide-illu svg{width:100%;height:100%;display:block}"
+ "body.light .mguide-illu{background:#f8fafc}"
+ ".mguide-icon{width:80px;height:80px;border-radius:20px;background:linear-gradient(135deg,var(--accent-bg),rgba(52,211,153,.12));display:flex;align-items:center;justify-content:center;color:var(--accent);margin-bottom:20px;animation:mguideIconIn .5s cubic-bezier(.34,1.56,.64,1)}"
+ "@keyframes mguideIconIn{0%{opacity:0;transform:scale(.5) rotate(-10deg)}60%{transform:scale(1.15) rotate(4deg)}100%{opacity:1;transform:scale(1) rotate(0)}}"
+ ".mguide-tit{font-size:24px;font-weight:800;color:var(--text);margin:0 0 14px;line-height:1.25;letter-spacing:-.2px}"
+ ".mguide-body{font-size:16px;color:var(--text2);line-height:1.75;max-width:640px;margin:0}"
+ ".mguide-body strong{color:var(--text);font-weight:700}"
+ ".mguide-body .mguide-hl{color:var(--accent);font-weight:700;background:var(--accent-bg);padding:1px 7px;border-radius:6px;font-size:14.5px}"
+ ".mguide-body .mguide-tag{display:inline-flex;align-items:center;gap:4px;background:var(--accent-bg);color:var(--accent);font-weight:600;padding:1px 8px;border-radius:6px;font-size:11px;margin:0 2px}"
+ ".mguide-tasks{width:100%;max-width:600px;text-align:left;margin-top:12px;display:flex;flex-direction:column;gap:12px}"
+ ".mguide-svc{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px}"
+ ".mguide-svc-hd{font-size:13px;font-weight:700;color:var(--accent);margin-bottom:6px;display:flex;align-items:center;gap:7px}"
+ ".mguide-svc-hd svg{width:14px;height:14px;flex-shrink:0}"
+ ".mguide-svc-list{margin:0;padding-left:20px;font-size:13px;color:var(--text2);line-height:1.6}"
+ ".mguide-svc-list li{margin-bottom:3px}"
+ "body.light .mguide-svc{background:#f8fafc}"
+ ".mguide-nav{display:flex;justify-content:space-between;align-items:center;padding:14px 24px 20px;gap:12px;border-top:1px solid var(--border);background:var(--bg);flex-wrap:wrap}"
+ ".mguide-dots{display:flex;gap:6px}"
+ ".mguide-dot{width:8px;height:8px;border-radius:99px;background:var(--border);cursor:pointer;transition:all .2s;border:none;padding:0}"
+ ".mguide-dot.active{background:var(--accent);width:22px}"
+ ".mguide-dot:hover:not(.active){background:var(--muted)}"
+ ".mguide-nav-btns{display:flex;gap:8px}"
+ ".mguide-nav-btn{padding:8px 16px;border-radius:9px;border:1px solid var(--border);background:transparent;color:var(--text2);font-weight:600;font-size:12px;cursor:pointer;transition:all .15s;font-family:inherit}"
+ ".mguide-nav-btn:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}"
+ ".mguide-nav-btn:disabled{opacity:.4;cursor:not-allowed}"
+ ".mguide-nav-btn.primary{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:800;text-shadow:0 1px 2px rgba(0,0,0,.3)}"
+ ".mguide-nav-btn.primary:hover:not(:disabled){filter:brightness(1.08);transform:translateY(-1px);color:#fff}"
+ ".mguide-nav-btn.primary:disabled{color:#fff;opacity:.55;text-shadow:none}"
+ ".mguide-ack-row{display:flex;flex-direction:column;justify-content:center;align-items:center;padding:0 24px 16px;background:var(--bg)}"
+ ".mguide-ack-btn{width:100%;max-width:400px;padding:12px 18px;border-radius:10px;border:1.5px solid var(--ok,#34d399);background:var(--ok,#34d399);color:var(--btn-fg,#04222b);font-weight:800;font-size:13px;cursor:pointer;transition:all .18s;font-family:inherit;display:inline-flex;align-items:center;justify-content:center;gap:8px}"
+ ".mguide-ack-btn:hover:not(:disabled){filter:brightness(1.06);transform:translateY(-1px);box-shadow:0 6px 16px rgba(52,211,153,.28)}"
+ ".mguide-ack-btn:disabled{cursor:not-allowed;background:var(--bg);color:var(--text2);border:1.5px solid var(--border);font-weight:600;gap:10px}"
+ ".mguide-ack-btn:disabled .mguide-ack-lock{color:var(--muted);flex-shrink:0;display:inline-flex;align-items:center}"
+ ".mguide-ack-btn:disabled .mguide-ack-chip{margin-left:auto;background:var(--card);color:var(--muted);font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;border:1px solid var(--border);font-family:ui-monospace,Menlo,monospace}"
+ ".mguide-ack-btn:disabled:hover{transform:none;box-shadow:none;filter:none}"
+ ".mguide-ack-info{font-size:11px;color:var(--muted);margin-top:6px;text-align:center;width:100%;font-style:italic}"
+ ".mguide-ack-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:999px;background:rgba(52,211,153,.15);color:var(--ok,#34d399);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}"
+ ".mguide-toast{position:fixed;bottom:24px;left:50%;transform:translate(-50%,20px);background:var(--card);color:var(--text);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:12px 18px;font-size:13px;font-weight:600;z-index:20001;opacity:0;transition:all .3s;box-shadow:0 8px 24px rgba(0,0,0,.3)}"
+ ".mguide-toast.show{opacity:1;transform:translate(-50%,0)}"
+ ".mguide-toast.success{border-left-color:var(--ok,#34d399)}"
+ ".mguide-toast.danger{border-left-color:var(--danger,#f87171)}"
+ ".mguide-help-fab{position:fixed;bottom:82px;right:18px;width:44px;height:44px;border-radius:50%;background:var(--accent);color:#fff;border:none;cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,.3);z-index:19990;transition:transform .15s,filter .15s}"
+ ".mguide-help-fab:hover{filter:brightness(1.08);transform:translateY(-2px)}"
+ ".mguide-help-fab svg{width:22px;height:22px}"
+ ".mguide-help-inline{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:9px;background:var(--accent-bg);color:var(--accent);border:1px solid transparent;cursor:pointer;transition:all .18s;padding:0;vertical-align:middle}"
+ ".mguide-help-inline:hover{background:var(--accent);color:#fff;transform:translateY(-1px)}"
+ ".mguide-help-inline svg{width:16px;height:16px}"
+ "@media(max-width:640px){.mguide-step{padding:24px 20px 18px}.mguide-illu{height:220px}.mguide-tit{font-size:20px}.mguide-body{font-size:14px}.mguide-help-fab{bottom:74px;right:14px;width:40px;height:40px}}";

  function updateHelpBtn(){
    var b = document.getElementById("mguide-help-fab");
    if(b) b.style.display = "none";
  }
  function bookBtn(key){
    if(role !== "superadmin") return "";
    if(!registry[key]) return "";
    return '<button type="button" class="mguide-help-inline" title="Guide de la page" aria-label="Guide de la page" onclick="MySifaGuides.open(\''+key+'\')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg></button>';
  }

  window.MySifaGuides = {
    configure: configure, register: register, registerMany: registerMany,
    boot: boot, open: open, autoOpen: autoOpen, autoOpenChain: autoOpenChain, bookBtn: bookBtn, isAcked: isAcked,
    _nav: nav, _close: closeGuide, _ack: ack, _idx: function(){ return st.idx; }
  };
})();
