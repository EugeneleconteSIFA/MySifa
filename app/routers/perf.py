"""MySifa — fluidité des postes.

Ce module répond à une question qu'on ne pouvait poser qu'au doigt mouillé :
« sur quels ordinateurs MySifa rame vraiment ? »

Deux entrées :

  POST /api/perf/releve   le navigateur envoie ce qu'il a mesuré (un relevé
                          par session, via sendBeacon). Tolérant : un relevé
                          reçu sans session valide est gardé sans email — on
                          préfère une mesure anonyme à pas de mesure.
  GET  /perf-postes       la vue superadmin / direction : un poste par ligne,
                          trié du plus lent au plus fluide.

Ce qui compte dans la lecture : le FPS médian d'un poste, pas son dernier
relevé. Une session à 20 images par seconde peut être une visioconférence
lancée à côté ; six sessions à 20, c'est le poste.

Attention à un piège de lecture : un poste déjà passé en mode éco mesure avec
les effets coupés. Son FPS remonte forcément. La colonne « mode » est donc à
lire avec le FPS : « eco / 55 fps » veut dire « allégé, et du coup fluide »,
pas « pourquoi est-il allégé ? ».
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.database import get_db
from app.services.auth_service import get_current_user
from config import ROLE_DIRECTION, ROLE_SUPERADMIN

router = APIRouter(tags=["perf"])

_ROLES_VUE = {ROLE_SUPERADMIN, ROLE_DIRECTION}
# Un relevé par session côté client ; ce garde-fou côté serveur couvre le cas
# d'un navigateur qui rejoue le beacon (retour arrière, restauration d'onglets).
_ANTI_REBOND_S = 60


# ── petits convertisseurs tolérants ──────────────────────────────────────────
# Le corps vient d'un sendBeacon : on ne rejette rien, on borne.

def _f(v: Any, maxi: float = 1_000_000.0) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or x < 0:  # NaN ou négatif : la mesure n'a pas de sens
        return None
    return round(min(x, maxi), 2)


def _i(v: Any, maxi: int = 100_000) -> Optional[int]:
    f = _f(v, float(maxi))
    return int(f) if f is not None else None


def _s(v: Any, maxi: int = 240) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s[:maxi] if s else None


# ── réception ────────────────────────────────────────────────────────────────

@router.post("/api/perf/releve")
async def enregistrer_releve(request: Request):
    try:
        data = json.loads(await request.body() or b"{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Corps illisible.")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Corps invalide.")

    poste = _s(data.get("poste"), 40)
    if not poste:
        raise HTTPException(status_code=400, detail="Poste manquant.")

    email = None
    try:
        email = (get_current_user(request) or {}).get("email")
    except Exception:
        email = None  # relevé anonyme : mieux que rien

    niveau = "eco" if _s(data.get("niveau"), 10) == "eco" else "normal"
    maintenant = datetime.now().isoformat(timespec="seconds")

    with get_db() as conn:
        recent = conn.execute(
            "SELECT cree_le FROM perf_releves WHERE poste = ? ORDER BY cree_le DESC LIMIT 1",
            (poste,),
        ).fetchone()
        if recent:
            try:
                ecart = (datetime.now() - datetime.fromisoformat(recent[0])).total_seconds()
                if ecart < _ANTI_REBOND_S:
                    return JSONResponse({"ok": True, "ignore": "doublon"})
            except Exception:
                pass

        conn.execute(
            """INSERT INTO perf_releves
               (cree_le, email, poste, niveau, force_main, score,
                fps, fps_bas, blocage_ms, cores, memoire_go, dpr, ecran,
                t_reponse_ms, t_rendu_ms, t_charge_ms, page, navigateur)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                maintenant, email, poste, niveau,
                1 if data.get("force_main") else 0, _i(data.get("score"), 50) or 0,
                _f(data.get("fps"), 300), _f(data.get("fps_bas"), 300), _f(data.get("blocage_ms"), 600000),
                _i(data.get("cores"), 512), _f(data.get("memoire_go"), 1024), _f(data.get("dpr"), 10),
                _s(data.get("ecran"), 24),
                _f(data.get("t_reponse_ms"), 600000), _f(data.get("t_rendu_ms"), 600000),
                _f(data.get("t_charge_ms"), 600000),
                _s(data.get("page"), 120), _s(data.get("navigateur"), 240),
            ),
        )
        # Purge opportuniste : la série au-delà de 120 jours n'apprend plus rien.
        if random.random() < 0.02:
            conn.execute("DELETE FROM perf_releves WHERE cree_le < datetime('now','-120 days')")
        conn.commit()

    return JSONResponse({"ok": True})


# ── lecture ──────────────────────────────────────────────────────────────────

def _exiger_vue(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in _ROLES_VUE:
        raise HTTPException(status_code=403, detail="Accès réservé à la direction et au super administrateur.")
    return user


def _mediane(valeurs: list) -> Optional[float]:
    v = sorted(x for x in valeurs if x is not None)
    if not v:
        return None
    n = len(v)
    return round(v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2, 1)


def _navigateur_court(ua: str) -> str:
    """Assez pour reconnaître un poste, pas assez pour en faire une empreinte."""
    ua = ua or ""
    os_ = "Windows" if "Windows" in ua else "macOS" if "Mac OS" in ua else "Linux" if "Linux" in ua else "?"
    nav = ("Edge" if "Edg/" in ua else "Chrome" if "Chrome" in ua else
           "Firefox" if "Firefox" in ua else "Safari" if "Safari" in ua else "?")
    return f"{nav} / {os_}"


@router.get("/api/perf/postes")
def liste_postes(request: Request, jours: int = 30):
    _exiger_vue(request)
    jours = max(1, min(int(jours or 30), 120))

    with get_db() as conn:
        lignes = conn.execute(
            f"""SELECT * FROM perf_releves
                WHERE cree_le >= datetime('now','-{jours} days')
                ORDER BY cree_le DESC""",
        ).fetchall()

    par_poste: dict = {}
    par_page: dict = {}
    for r in lignes:
        d = dict(r)
        p = par_poste.setdefault(d["poste"], {
            "poste": d["poste"], "sessions": 0, "fps": [], "rendu": [],
            "dernier": d["cree_le"], "niveau": d["niveau"], "force_main": d["force_main"],
            "cores": d["cores"], "memoire_go": d["memoire_go"], "ecran": d["ecran"],
            "navigateur": _navigateur_court(d["navigateur"] or ""), "emails": set(),
        })
        p["sessions"] += 1
        if d["fps"] is not None:
            p["fps"].append(d["fps"])
        if d["t_rendu_ms"] is not None:
            p["rendu"].append(d["t_rendu_ms"])
        if d["email"]:
            p["emails"].add(d["email"])

        if d["page"] and d["fps"] is not None and d["niveau"] != "eco":
            # Les sessions éco mesurent effets coupés : les inclure dans le
            # classement des pages lentes fausserait le classement.
            par_page.setdefault(d["page"], []).append(d["fps"])

    postes = []
    for p in par_poste.values():
        postes.append({
            "poste": p["poste"],
            "sessions": p["sessions"],
            "fps_median": _mediane(p["fps"]),
            "fps_pire": round(min(p["fps"]), 1) if p["fps"] else None,
            "rendu_median": _mediane(p["rendu"]),
            "dernier": p["dernier"],
            "niveau": p["niveau"],
            "force_main": p["force_main"],
            "cores": p["cores"],
            "memoire_go": p["memoire_go"],
            "ecran": p["ecran"],
            "navigateur": p["navigateur"],
            "utilisateurs": sorted(p["emails"]),
        })
    postes.sort(key=lambda x: (x["fps_median"] is None, x["fps_median"] if x["fps_median"] is not None else 999))

    pages = sorted(
        ({"page": k, "fps_median": _mediane(v), "mesures": len(v)} for k, v in par_page.items()),
        key=lambda x: (x["fps_median"] is None, x["fps_median"] if x["fps_median"] is not None else 999),
    )

    return {"jours": jours, "postes": postes, "pages": pages[:20], "total_releves": len(lignes)}


_PAGE = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fluidité des postes — MySifa</title>
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--muted:#94a3b8;
      --accent:#22d3ee;--danger:#f87171;--warn:#fbbf24;--ok:#34d399}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--muted:#64748b;--accent:#0891b2}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font:14px/1.5 'Segoe UI',system-ui,sans-serif;padding:24px}
.wrap{max-width:1180px;margin:0 auto}
h1{font-size:21px;margin-bottom:4px}
.sub{color:var(--muted);font-size:13px;margin-bottom:18px}
.bar{display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
select,a.btn{background:var(--card);color:var(--text);border:1px solid var(--border);
      border-radius:8px;padding:6px 10px;font-size:13px;text-decoration:none}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:18px}
h2{font-size:15px;margin-bottom:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--muted);font-weight:600;padding:7px 8px;border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:8px;border-bottom:1px solid var(--border);vertical-align:top}
tr:last-child td{border-bottom:none}
.fps{font-weight:700}
.f-bas{color:var(--danger)}.f-moy{color:var(--warn)}.f-ok{color:var(--ok)}
.tag{display:inline-block;font-size:11px;padding:2px 7px;border-radius:99px;border:1px solid var(--border);color:var(--muted)}
.tag.eco{border-color:var(--warn);color:var(--warn)}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:var(--muted)}
.vide{color:var(--muted);padding:14px 0}
.note{color:var(--muted);font-size:12px;margin-top:10px}
</style></head><body>
<div class="wrap">
  <h1>Fluidité des postes</h1>
  <div class="sub">Images par seconde réellement obtenues sur chaque ordinateur, mesurées dans MySifa.
  Un poste sous 30 fps passe automatiquement en affichage allégé.</div>
  <div class="bar">
    <select id="jours" onchange="charger()">
      <option value="7">7 derniers jours</option>
      <option value="30" selected>30 derniers jours</option>
      <option value="90">90 derniers jours</option>
    </select>
    <span class="mono" id="total"></span>
    <a class="btn" href="/settings">← Paramètres</a>
    <a class="btn" href="/">MySifa</a>
  </div>
  <div class="card"><h2>Postes</h2><div id="postes" class="vide">Chargement…</div>
    <div class="note">« Mode éco » signifie que le poste affiche déjà une version allégée :
    son FPS est alors mesuré effets coupés, il est normalement bon. C'est le passage en éco
    qui est le signal, pas le chiffre.</div>
  </div>
  <div class="card"><h2>Pages les plus lourdes</h2><div id="pages" class="vide">Chargement…</div>
    <div class="note">Médiane calculée sur les seules sessions en affichage complet.</div>
  </div>
</div>
<script>
try{ if((localStorage.getItem('theme')||'light')!=='dark') document.body.classList.add('light'); }catch(e){}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function cls(f){ if(f==null) return ''; return f<30?'f-bas':f<50?'f-moy':'f-ok'; }
function dt(s){ if(!s) return ''; return s.replace('T',' ').slice(0,16); }
async function charger(){
  const j=document.getElementById('jours').value;
  const r=await fetch('/api/perf/postes?jours='+j,{credentials:'same-origin'});
  if(!r.ok){ document.getElementById('postes').textContent='Accès refusé.'; return; }
  const d=await r.json();
  document.getElementById('total').textContent=d.total_releves+' relevés';
  document.getElementById('postes').innerHTML = d.postes.length ? (
    '<table><tr><th>Poste</th><th>FPS médian</th><th>Pire</th><th>Rendu page</th>'+
    '<th>Mode</th><th>Machine</th><th>Utilisateurs</th><th>Sessions</th><th>Dernier relevé</th></tr>'+
    d.postes.map(p=>'<tr>'+
      '<td class="mono">'+esc(p.poste)+'</td>'+
      '<td class="fps '+cls(p.fps_median)+'">'+(p.fps_median==null?'—':p.fps_median)+'</td>'+
      '<td class="'+cls(p.fps_pire)+'">'+(p.fps_pire==null?'—':p.fps_pire)+'</td>'+
      '<td>'+(p.rendu_median==null?'—':Math.round(p.rendu_median)+' ms')+'</td>'+
      '<td>'+(p.niveau==='eco'?'<span class="tag eco">éco'+(p.force_main?' (manuel)':'')+'</span>':'<span class="tag">complet</span>')+'</td>'+
      '<td>'+esc(p.navigateur)+'<div class="mono">'+(p.cores?p.cores+' cœurs':'')+
        (p.memoire_go?' · '+p.memoire_go+' Go':'')+(p.ecran?' · '+esc(p.ecran):'')+'</div></td>'+
      '<td class="mono">'+esc((p.utilisateurs||[]).join(', '))+'</td>'+
      '<td>'+p.sessions+'</td>'+
      '<td class="mono">'+dt(p.dernier)+'</td></tr>').join('')+'</table>'
  ) : '<div class="vide">Aucun relevé sur la période.</div>';
  document.getElementById('pages').innerHTML = d.pages.length ? (
    '<table><tr><th>Page</th><th>FPS médian</th><th>Mesures</th></tr>'+
    d.pages.map(p=>'<tr><td class="mono">'+esc(p.page)+'</td>'+
      '<td class="fps '+cls(p.fps_median)+'">'+(p.fps_median==null?'—':p.fps_median)+'</td>'+
      '<td>'+p.mesures+'</td></tr>').join('')+'</table>'
  ) : '<div class="vide">Aucune mesure en affichage complet.</div>';
}
charger();
</script></body></html>"""


@router.get("/perf-postes", response_class=HTMLResponse)
def page_postes(request: Request):
    try:
        _exiger_vue(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/perf-postes", status_code=302)
        raise
    return HTMLResponse(content=_PAGE)
