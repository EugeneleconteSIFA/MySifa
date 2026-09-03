"""MySifa — Gestionnaire de tâches (page).

Route : /taches — accès piloté par la matrice (Paramètres → Accès, app
`taches`). Chacun voit ses tâches, et celles de son service à partir du niveau
`write`. Le cloisonnement est appliqué côté API (`app/routers/taches.py`) : la
page ne fait que masquer ce qui n'a pas lieu d'être proposé.

Trois vues : Kanban (glisser-déposer), Liste (filtrable / triable) et un
panneau de détail (description, checklist, sous-tâches, fichiers de contexte,
commentaires, journal d'activité).

Shell MySifa standard : sidebar invariable + topbar mobile + MySifaTheme +
MySifaUserChip + guides in-app partagés (mysifa_guides.js).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, role_label
from services.auth_service import effective_role, get_current_user, user_access_level, user_can

router = APIRouter()


@router.get("/taches", response_class=HTMLResponse)
def taches_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/taches", status_code=302)
        raise
    if not user_can(user, "taches", "_app", "read"):
        from app.web.access_denied import access_denied_response
        return access_denied_response(
            "Gestionnaire de tâches",
            detail=(
                "Cette application n'est pas ouverte à votre service. "
                "Merci de contacter un administrateur en cas de besoin."
            ),
        )
    service = effective_role(user) or ""
    html = (
        TACHES_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__USER_ROLE__", str(user.get("role") or ""))
        .replace("__USER_NIVEAU__", user_access_level(user, "taches"))
        .replace("__USER_SERVICE__", role_label(service))
    )
    return HTMLResponse(content=html)


TACHES_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Gestionnaire de tâches — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_mobile_topbar.css">
<style>
/* tokens : static/mysifa_theme.css — ici, seulement les écarts */
:root{--ok:#34d399;}
body.light{--muted:#64748b;--ok:#059669;}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── Shell ── */
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:24px;border-radius:8px;cursor:pointer;transition:background .15s,color .15s}
.logo:hover{background:var(--accent-bg)}
.logo:hover .logo-brand{color:var(--accent)}
.logo-brand{font-size:15px;font-weight:800;transition:color .15s}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(34,211,238,.25),0 0 18px rgba(34,211,238,.15)}
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
.nav-badge{margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--accent-bg);color:var(--accent);font-size:10px;font-weight:700;line-height:1.5}
.nav-badge.warn{background:rgba(251,191,36,.16);color:var(--warn)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}

.main{flex:1;min-width:0;padding:24px 26px 40px;overflow-x:hidden}
h1{font-size:22px;font-weight:700;margin:0}
.subtitle{font-size:13px;color:var(--muted);margin-top:4px}

/* ── En-tête ── */
.page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.head-title-row{display:flex;align-items:center;gap:10px}
.stats-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.stat{display:flex;align-items:center;gap:8px;padding:8px 13px;background:var(--card);border:1px solid var(--border);border-radius:10px;font-size:12px;color:var(--text2);cursor:pointer;transition:border-color .15s,color .15s}
.stat:hover{border-color:var(--accent);color:var(--accent)}
.stat.active{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.stat b{font-size:15px;font-weight:800;color:var(--text)}
.stat.active b,.stat:hover b{color:var(--accent)}
.stat.alert b{color:var(--danger)}

/* ── Barre d'outils ── */
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px}
.search-wrap{position:relative;flex:1;min-width:220px;max-width:380px}
.search-wrap svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
input.search{width:100%;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 14px 10px 36px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
input.search:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
select.filter{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text2);font-size:12px;font-family:inherit;outline:none;cursor:pointer;transition:border-color .15s}
select.filter:focus,select.filter:hover{border-color:var(--accent)}
select.filter.on{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.seg{display:inline-flex;background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.seg button{padding:9px 14px;border:none;background:var(--card);color:var(--text2);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;display:inline-flex;align-items:center;gap:7px;transition:background .15s,color .15s}
.seg button:hover{background:var(--bg)}
.seg button.active{background:var(--accent-bg);color:var(--accent)}
.btn{padding:10px 16px;border-radius:10px;border:none;background:var(--accent);color:var(--bg);font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:var(--card);border:1px solid var(--border);color:var(--text2)}
.btn.ghost:hover{background:var(--bg);border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:var(--danger);color:#fff}
.btn.small{padding:6px 11px;font-size:11px;border-radius:8px}
.btn:disabled{opacity:.5;cursor:not-allowed;filter:none}
/* Bascule « Mes tâches » : un filtre, pas une vue — il vaut pour le Kanban
   comme pour la Liste et se cumule avec les autres critères. */
.btn.ghost.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.btn.ghost.on:hover{background:var(--accent-bg)}
.btn .cnt{padding:0 6px;border-radius:8px;background:var(--border);color:var(--text2);font-size:10px;font-weight:800;line-height:1.6}
.btn.ghost.on .cnt{background:var(--accent);color:var(--bg)}
.btn .cnt.warn{background:rgba(251,191,36,.22);color:var(--warn)}
.btn.ghost.on .cnt.warn{background:var(--warn);color:#3b2c00}

/* ── Kanban ── */
/* Colonnes bornées : elles ne s'étirent plus pour remplir l'écran. Une carte
   compacte n'a pas besoin de 240 px de large, et le board reste lisible d'un
   seul coup d'œil au lieu de s'étaler. */
.board{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(146px,200px);justify-content:start;
  gap:10px;align-items:start;overflow-x:auto;padding-bottom:14px}
.col{min-width:0;background:var(--card);border:1px solid var(--border);border-radius:14px;display:flex;flex-direction:column;max-height:calc(100vh - 250px)}
.col.drop{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.col-head{display:flex;align-items:center;gap:7px;padding:11px 11px;border-bottom:1px solid var(--border);flex-shrink:0}
.col-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.col-title{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.col-count{margin-left:auto;font-size:10.5px;font-weight:700;color:var(--muted);background:var(--bg);padding:2px 7px;border-radius:8px;flex-shrink:0}
.col-body{padding:8px;display:flex;flex-direction:column;gap:7px;overflow-y:auto;min-height:70px;flex:1}
.col-add{margin:0 8px 8px;padding:8px;border:1px dashed var(--border);border-radius:9px;background:transparent;color:var(--muted);font-size:11.5px;font-family:inherit;cursor:pointer;transition:all .15s;flex-shrink:0}
.col-add:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

.tcard{background:var(--bg);border:1px solid var(--border);border-left:3px solid var(--border);border-radius:9px;padding:8px 9px;cursor:pointer;transition:border-color .15s,transform .1s,box-shadow .15s}
.tcard:hover{border-color:var(--accent);box-shadow:0 4px 14px rgba(0,0,0,.18)}
.tcard.dragging{opacity:.45}
/* Carte active (survol ou navigation J/K) : cible des touches 1 à 5. */
.tcard.actif{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg),0 6px 18px rgba(0,0,0,.18)}

.kbd-foot{margin-top:22px;padding-top:14px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;
  align-items:center;gap:6px 16px;font-size:11.5px;color:var(--muted)}
.kbd-foot b{font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;font-size:10px;margin-right:2px}
.kbd-foot span{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
kbd{display:inline-block;min-width:17px;padding:1px 5px;border-radius:5px;background:var(--card);
  border:1px solid var(--border);border-bottom-width:2px;font-family:'SF Mono','Consolas',monospace;
  font-size:10.5px;font-weight:700;color:var(--text2);text-align:center;line-height:1.5}
.tcard.prio-critique{border-left-color:var(--danger)}
.tcard.prio-haute{border-left-color:var(--warn)}
.tcard.prio-normale{border-left-color:var(--accent)}
.tcard.prio-basse{border-left-color:var(--muted)}
/* Carte compacte : une ligne d'en-tête (assignés à gauche, alerte + chevron à
   droite) puis le titre. Aucune étiquette texte — le type, le module, la
   priorité et l'échéance se lisent dans la fiche ; la priorité reste donnée par
   la couleur du liseré gauche. */
.tcard-hd{display:flex;align-items:center;gap:4px;margin-bottom:5px;min-height:17px}
.tcard-hd .sp{flex:1;min-width:0}
.tcard-hd .avatar{width:17px;height:17px;font-size:7.5px;border-radius:50%}
.tcard-hd .pile .avatar{margin-left:-5px}
.tcard-hd .pile .plus{margin-left:-5px;font-size:7.5px}
.tcard-retard{display:inline-flex;align-items:center;flex-shrink:0;padding:2px}
.tcard-retard i{display:block;width:6px;height:6px;border-radius:50%;background:var(--danger);
  box-shadow:0 0 0 3px rgba(248,113,113,.16)}
.tcard-title{font-size:12px;font-weight:600;color:var(--text);line-height:1.35;word-break:break-word}
.avatar{width:22px;height:22px;border-radius:50%;background:var(--accent-bg);color:var(--accent);font-size:9px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;letter-spacing:-.2px}
.avatar img{width:100%;height:100%;object-fit:cover}
.avatar.none{background:var(--bg);color:var(--muted);border:1px dashed var(--border)}
/* Pile d'avatars : les visages se chevauchent pour tenir sur une carte étroite. */
.pile{display:inline-flex;align-items:center;flex-shrink:0}
.pile .avatar{margin-left:-6px;box-shadow:0 0 0 2px var(--bg)}
.pile .avatar:first-child{margin-left:0}
.pile .plus{margin-left:-6px;background:var(--border);color:var(--text2);box-shadow:0 0 0 2px var(--bg)}
td .pile .avatar,td .pile .plus{box-shadow:0 0 0 2px var(--card)}

/* Sélecteur d'assignés : chips + popover avec recherche et cases à cocher. */
.asg-field{position:relative}
.asg-box{display:flex;flex-wrap:wrap;align-items:center;gap:5px;min-height:38px;width:100%;
  background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:5px 8px;cursor:pointer;transition:border-color .15s}
.asg-box:hover,.asg-box.open{border-color:var(--accent)}
.asg-chip{display:inline-flex;align-items:center;gap:6px;padding:2px 8px 2px 3px;border-radius:999px;
  background:var(--accent-bg);color:var(--accent);font-size:11.5px;font-weight:600;max-width:100%}
.asg-chip .avatar{width:18px;height:18px;font-size:8px}
.asg-chip .x{border:none;background:transparent;color:inherit;cursor:pointer;font-size:13px;line-height:1;padding:0 1px;opacity:.7}
.asg-chip .x:hover{opacity:1}
.asg-vide{font-size:12.5px;color:var(--muted)}
.asg-pop{position:absolute;z-index:40;top:calc(100% + 5px);left:0;right:0;background:var(--card);
  border:1px solid var(--border);border-radius:11px;box-shadow:0 14px 34px rgba(0,0,0,.32);padding:8px;max-height:280px;display:flex;flex-direction:column}
.asg-pop input.asg-q{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:7px 10px;color:var(--text);font-size:12.5px;font-family:inherit;outline:none;margin-bottom:6px;flex-shrink:0}
.asg-pop input.asg-q:focus{border-color:var(--accent)}
.asg-list{overflow-y:auto;flex:1}
/* Sélecteur spécificité : les options sont des <label> posés dans un .field,
   qui les mettrait en majuscules bloc (style des libellés de formulaire). On
   remonte la spécificité avec `.asg-pop` plutôt que d'empiler des !important. */
.asg-pop .asg-opt{display:flex;align-items:center;gap:9px;padding:7px 8px;border-radius:8px;
  cursor:pointer;font-size:12.5px;font-weight:500;color:var(--text2);
  text-transform:none;letter-spacing:0;margin-bottom:0}
.asg-pop .asg-opt:hover,.asg-pop .asg-opt.actif{background:var(--accent-bg)}
.asg-pop .asg-opt.actif{color:var(--accent)}
.asg-pop .asg-opt input{width:14px;height:14px;accent-color:var(--accent);cursor:pointer;flex-shrink:0;margin:0}
.asg-pop .asg-opt .n{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* Service de la personne : la liste couvre tous les services, deux prénoms
   identiques doivent rester distinguables d'un coup d'œil. */
.asg-pop .asg-opt .asg-svc{flex-shrink:0;font-size:10.5px;color:var(--muted);
  background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:1px 6px}
.asg-pop .asg-opt.actif .asg-svc{color:var(--accent);border-color:var(--accent)}
.asg-rien{font-size:12px;color:var(--muted);padding:10px 8px;text-align:center}

/* Corbeille d'archivage : discrète au repos, elle ne s'ouvre que pendant un
   glisser. Posée en bas à gauche de la zone board, hors du flux des colonnes. */
.arch-drop{position:fixed;left:calc(220px + 20px);bottom:20px;z-index:60;
  display:flex;align-items:center;gap:9px;padding:11px 15px;border-radius:12px;
  background:var(--card);border:1.5px dashed var(--border);color:var(--muted);
  font-size:12px;font-weight:600;font-family:inherit;cursor:default;
  opacity:.55;transform:translateY(4px);transition:opacity .18s,transform .18s,border-color .18s,color .18s,background .18s}
.arch-drop svg{width:17px;height:17px;flex-shrink:0}
body.drag-actif .arch-drop{opacity:1;transform:translateY(0);border-color:var(--accent);color:var(--accent)}
.arch-drop.survol{background:var(--accent-bg);border-color:var(--accent);border-style:solid;color:var(--accent);transform:translateY(0) scale(1.04)}
@media (max-width:900px){.arch-drop{left:14px;bottom:14px;padding:10px 12px}.arch-drop .lbl{display:none}}
.tag{display:inline-flex;align-items:center;padding:2px 7px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;background:var(--bg);color:var(--muted);border:1px solid var(--border)}
.tag.accent{background:var(--accent-bg);color:var(--accent);border-color:transparent}
.tag.warn{background:rgba(251,191,36,.15);color:var(--warn);border-color:transparent}
.tag.danger{background:rgba(248,113,113,.15);color:var(--danger);border-color:transparent}
.tag.ok{background:rgba(52,211,153,.15);color:var(--ok);border-color:transparent}
.tag.muted{background:var(--bg);color:var(--muted)}
.due{font-weight:700}
.due.late{color:var(--danger)}
.due.soon{color:var(--warn)}
/* Pile carte + sous-tâches : la carte reste seule à porter le drag, la pile
   dépliée vit en dessous, dans le même bloc. */
.tstack{display:flex;flex-direction:column}
.sous-toggle{display:inline-flex;align-items:center;gap:3px;flex-shrink:0;padding:1px 5px;border-radius:6px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);font-size:9.5px;font-weight:700;
  font-family:inherit;cursor:pointer;transition:background .15s,color .15s,border-color .15s}
.sous-toggle:hover{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.sous-toggle.ouvert{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.sous-toggle svg{width:11px;height:11px;transition:transform .18s}
.sous-toggle.ouvert svg{transform:rotate(90deg)}
.sous-pile{display:flex;flex-direction:column;gap:4px;margin:5px 0 2px 8px;padding-left:8px;border-left:2px solid var(--border)}
.sous-carte{display:flex;align-items:center;gap:6px;padding:5px 7px;border-radius:7px;background:var(--card);
  border:1px solid var(--border);cursor:pointer;transition:border-color .15s,background .15s}
.sous-carte:hover{border-color:var(--accent);background:var(--accent-bg)}
.sous-carte .st{flex:1;min-width:0;font-size:11px;font-weight:600;color:var(--text);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sous-carte.close .st{text-decoration:line-through;color:var(--muted);font-weight:500}
.sous-carte .pastille{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.sous-carte .avatar{width:15px;height:15px;font-size:7px}
.sous-carte .pile .avatar{margin-left:-4px}
.progress{height:3px;border-radius:3px;background:var(--border);overflow:hidden;margin-top:6px}
.progress i{display:block;height:100%;background:var(--accent);border-radius:3px}

/* ── Liste ── */
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:11px 12px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);white-space:nowrap;cursor:pointer;user-select:none}
th:hover{color:var(--accent)}
th .sort{opacity:.4;margin-left:4px}
th.sorted .sort{opacity:1;color:var(--accent)}
td{padding:11px 12px;border-bottom:1px solid var(--border);color:var(--text2);vertical-align:middle}
tbody tr{cursor:pointer;transition:background .12s}
tbody tr:hover td{background:var(--accent-bg)}
td.t-titre{color:var(--text);font-weight:600;max-width:420px}
td.t-titre .sub{display:block;font-size:11px;color:var(--muted);font-weight:400;margin-top:2px}
/* Sous-tache : indentation + liseré gauche, pour lire le groupe d'un coup d'œil. */
td.t-titre.est-sous{padding-left:34px;position:relative;font-weight:500}
td.t-titre.est-sous .arbre{position:absolute;left:16px;color:var(--muted);font-weight:400}
td.t-titre.est-sous .sub{margin-left:0}
tr.row-sous td:first-child{box-shadow:inset 2px 0 0 var(--border)}
tr.row-sous td{background:var(--bg)}
tbody tr.row-sous:hover td{background:var(--accent-bg)}

.empty{text-align:center;padding:44px 20px;color:var(--muted);font-size:13px}
.empty b{display:block;color:var(--text2);font-size:14px;margin-bottom:6px}

/* ── Panneau de détail ── */
.drawer-back{position:fixed;top:var(--msf-top,0px);left:0;right:0;bottom:0;background:rgba(0,0,0,.55);z-index:500;backdrop-filter:blur(3px);animation:fade .15s}
@keyframes fade{from{opacity:0}to{opacity:1}}
.drawer{position:fixed;top:var(--msf-top,0px);right:0;bottom:0;width:min(680px,100vw);background:var(--card);border-left:1px solid var(--border);z-index:501;display:flex;flex-direction:column;box-shadow:-16px 0 48px rgba(0,0,0,.4);animation:slideL .18s ease}
@keyframes slideL{from{transform:translateX(30px);opacity:.4}to{transform:translateX(0);opacity:1}}
.dr-head{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:12px;flex-shrink:0}
.dr-head-main{flex:1;min-width:0}
.dr-title{font-size:16px;font-weight:700;color:var(--text);line-height:1.35;word-break:break-word;border-radius:7px;padding:3px 5px;margin:-3px -5px;cursor:text}
.dr-title:hover{background:var(--bg)}
.dr-meta{font-size:11px;color:var(--muted);margin-top:5px}
.dr-close{width:32px;height:32px;border-radius:9px;border:1px solid var(--border);background:var(--bg);color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px;line-height:1;transition:all .15s}
.dr-close:hover{border-color:var(--danger);color:var(--danger)}
.dr-tabs{display:flex;gap:2px;padding:0 14px;border-bottom:1px solid var(--border);flex-shrink:0;overflow-x:auto}
.dr-tab{padding:11px 13px;border:none;background:transparent;color:var(--muted);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;transition:color .15s,border-color .15s}
.dr-tab:hover{color:var(--text2)}
.dr-tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.dr-tab .n{background:var(--bg);border-radius:8px;padding:0 6px;font-size:10px;font-weight:700}
.dr-body{flex:1;overflow-y:auto;padding:18px 20px 26px}
.dr-pane{display:none}
.dr-pane.active{display:block}

.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:18px}
.field label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:9px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.field textarea{min-height:96px;resize:vertical;line-height:1.55}
.field.full{grid-column:1/-1}
.sec{margin-bottom:20px}
.sec-hd{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}
.sec-hd h3{margin:0;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)}

.chk{display:flex;align-items:center;gap:9px;padding:8px 10px;background:var(--bg);border:1px solid var(--border);border-radius:9px;margin-bottom:6px}
.chk input[type=checkbox]{width:15px;height:15px;accent-color:var(--accent);cursor:pointer;flex-shrink:0}
.chk .lbl{flex:1;font-size:12.5px;color:var(--text2);word-break:break-word}
.chk.done .lbl{text-decoration:line-through;color:var(--muted)}
.chk .x{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:15px;line-height:1;padding:2px 4px;border-radius:5px}
.chk .x:hover{color:var(--danger);background:rgba(248,113,113,.12)}
.inline-add{display:flex;gap:7px;margin-top:8px}
.inline-add input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:8px 11px;color:var(--text);font-size:12.5px;font-family:inherit;outline:none}
.inline-add input:focus{border-color:var(--accent)}

.sub-item{display:flex;align-items:center;gap:9px;padding:9px 11px;background:var(--bg);border:1px solid var(--border);border-radius:9px;margin-bottom:6px;cursor:pointer;transition:border-color .15s}
.sub-item:hover{border-color:var(--accent)}
.sub-item .st{flex:1;font-size:12.5px;color:var(--text2);word-break:break-word}
.sub-item.done .st{text-decoration:line-through;color:var(--muted)}

.file-item{display:flex;align-items:center;gap:11px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:7px}
.file-ico{width:32px;height:32px;border-radius:8px;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.file-info{flex:1;min-width:0}
.file-name{font-size:12.5px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-meta{font-size:10.5px;color:var(--muted);margin-top:2px}
.drop-zone{border:1.5px dashed var(--border);border-radius:11px;padding:22px 16px;text-align:center;font-size:12.5px;color:var(--muted);cursor:pointer;transition:all .15s}
.drop-zone:hover,.drop-zone.over{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

.cmt{display:flex;gap:10px;margin-bottom:14px}
.cmt-body{flex:1;min-width:0}
.cmt-hd{display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.cmt-auteur{font-size:12px;font-weight:700;color:var(--text)}
.cmt-date{font-size:10.5px;color:var(--muted)}
.cmt-msg{font-size:13px;color:var(--text2);line-height:1.6;white-space:pre-wrap;word-break:break-word}
.cmt-del{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:11px;padding:2px 5px;border-radius:5px;margin-left:auto}
.cmt-del:hover{color:var(--danger)}
.cmt-form{position:sticky;bottom:0;background:var(--card);padding-top:10px;border-top:1px solid var(--border);margin-top:6px}
.cmt-form textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;min-height:74px;resize:vertical}
.cmt-form textarea:focus{border-color:var(--accent)}

.act{display:flex;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--text2)}
.act:last-child{border-bottom:none}
.act-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);flex-shrink:0;margin-top:6px}
.act-date{margin-left:auto;font-size:10.5px;color:var(--muted);white-space:nowrap;flex-shrink:0}
.act b{color:var(--text)}

/* ── Modale ── */
.modal-back{position:fixed;top:var(--msf-top,0px);left:0;right:0;bottom:0;background:rgba(0,0,0,.6);z-index:600;display:flex;align-items:center;justify-content:center;padding:18px;backdrop-filter:blur(3px)}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px;max-width:560px;width:100%;max-height:92vh;overflow:auto}
.modal h3{margin:0 0 16px;font-size:16px;font-weight:700}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}

.toast{position:fixed;top:22px;right:22px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:9px;padding:12px 18px;font-size:13px;color:var(--text);z-index:900;box-shadow:0 10px 26px rgba(0,0,0,.32);animation:slideIn .18s}
.toast.err{border-left-color:var(--danger)}
@keyframes slideIn{from{transform:translateX(18px);opacity:0}to{transform:translateX(0);opacity:1}}

@media (max-width:1400px) and (min-width:901px){
  .main{padding-left:16px;padding-right:16px}
  .board{gap:8px}
  .col-body{padding:7px;gap:6px}
  .col-head{padding:10px 9px}
  .col-add{margin:0 7px 7px}
}
@media (max-width:900px){
  body.has-topbar .main{padding-top:74px}
  .main{padding:16px 14px 34px}
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .board{display:flex;overflow-x:auto}
  .col{flex:0 0 208px;width:208px;max-height:none}
  .fgrid{grid-template-columns:1fr}
  .drawer{width:100vw;border-left:none}
  .search-wrap{max-width:none}
}
@media (min-width:901px){.mobile-topbar{display:none}}
</style>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_guides.js"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="closeSidebar()"></div>

<div class="layout">
  <aside class="sidebar">
    <div class="logo" onclick="showView('kanban')" title="Vue Kanban">
      <div class="logo-brand">My<span>Tâches</span></div>
      <div class="logo-sub">Gestionnaire</div>
    </div>

    <button type="button" class="nav-btn active" id="nav-kanban" onclick="showView('kanban')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="6" height="18" rx="1"/><rect x="10" y="3" width="6" height="12" rx="1"/><rect x="17" y="3" width="4" height="8" rx="1"/></svg>
      Kanban
    </button>
    <button type="button" class="nav-btn" id="nav-liste" onclick="showView('liste')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
      Liste
      <span class="nav-badge" id="badge-total">0</span>
    </button>
    <button type="button" class="nav-btn" id="nav-archives" onclick="showView('archives')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5" rx="1"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
      Archives
    </button>

    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" onclick="location.href='/profil'" title="Mon profil">
        <div class="uc-name" id="uc-name">—</div>
        <div class="uc-role" id="uc-role">—</div>
      </div>
      <button type="button" class="theme-btn" id="btn-theme">
        <span class="theme-ico" id="theme-ico"></span>
        <span class="theme-label" id="theme-label">Mode clair</span>
      </button>
      <button type="button" class="logout-btn" id="btn-logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Tâches · __V_LABEL__</div>
    </div>
  </aside>

  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Tâches</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Kanban</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>

    <div class="page-head">
      <div>
        <div class="head-title-row">
          <h1 id="page-title">Kanban</h1>
          <span id="guide-btn-slot"></span>
        </div>
        <div class="subtitle" id="page-sub">Ce que l'équipe doit faire, en cours et terminé.</div>
      </div>
      <button type="button" class="btn" id="btn-nouvelle" onclick="openTacheModal()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouvelle tâche
      </button>
    </div>

    <div class="stats-row" id="stats-row"></div>

    <div class="toolbar" id="toolbar">
      <div class="search-wrap">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.7" y2="16.7"/></svg>
        <input type="text" class="search" id="f-q" placeholder="Rechercher (titre, description…)" autocomplete="off">
      </div>
      <button type="button" class="btn ghost small" id="btn-moi" title="N’afficher que les tâches qui me sont assignées — vaut pour le Kanban comme pour la Liste">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Mes tâches
        <span class="cnt" id="cnt-moi" style="display:none">0</span>
      </button>
      <select class="filter" id="f-assigne"><option value="">Tout le monde</option></select>
      <select class="filter" id="f-priorite"><option value="">Toutes priorités</option></select>
      <select class="filter" id="f-type"><option value="">Tous types</option></select>
      <select class="filter" id="f-module"><option value="">Tous modules</option></select>
      <select class="filter" id="f-service" style="display:none"><option value="">Tous services</option></select>
      <button type="button" class="btn ghost small" id="btn-sous" title="Vue Liste : afficher ou masquer les lignes de sous-tâches. Sur le Kanban elles sont toujours regroupées sous leur tâche mère.">Sous-tâches affichées</button>
      <button type="button" class="btn ghost small" id="btn-reset" onclick="resetFiltres()">Réinitialiser</button>
    </div>

    <div id="view-kanban"><div class="board" id="board"></div></div>
    <div id="view-liste" style="display:none">
      <div class="table-wrap">
        <table>
          <thead><tr id="liste-head"></tr></thead>
          <tbody id="liste-body"></tbody>
        </table>
      </div>
    </div>

    <div class="kbd-foot" id="kbd-foot">
      <b>Raccourcis</b>
      <span><kbd>N</kbd> nouvelle tâche</span>
      <span><kbd>/</kbd> rechercher</span>
      <span><kbd>J</kbd><kbd>K</kbd> naviguer entre les cartes</span>
      <span><kbd>1</kbd>–<kbd>5</kbd> changer le statut de la carte active</span>
      <span><kbd>Échap</kbd> fermer</span>
      <span style="color:var(--text2)"><kbd>⌥</kbd><kbd>T</kbd> créer une tâche depuis n’importe quelle page de MySifa</span>
    </div>
  </main>
</div>

<div class="arch-drop" id="arch-drop" title="Glisser une tâche ici pour l'archiver">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5" rx="1"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
  <span class="lbl">Archiver</span>
</div>

<div id="drawer-root"></div>
<div id="modal-root"></div>

<script>
// ══════════════════════════════════════════════════════════════════
// MyTâches — état central, rendu, API
// Convention api() : retourne le JSON parsé, throw sur HTTP != 2xx.
// ══════════════════════════════════════════════════════════════════
const USER_ROLE = "__USER_ROLE__";
// Niveau d'accès sur l'app : read / write / admin. Sert uniquement à ne pas
// proposer une action que l'API refuserait — la règle, elle, est côté serveur.
const USER_NIVEAU = "__USER_NIVEAU__";
const USER_SERVICE = "__USER_SERVICE__";
const PEUT_ECRIRE = (USER_NIVEAU === 'write' || USER_NIVEAU === 'admin');
const TOUS_SERVICES = (USER_NIVEAU === 'admin');

const S = {
  meta: null,
  taches: [],
  stats: {par_statut:{}, en_retard:0, non_assignees:0},
  view: 'kanban',
  detail: null,          // objet complet de la tâche ouverte
  detailTab: 'detail',
  // `moi` : bascule « Mes tâches ». C'est un filtre, pas une vue — il s'applique
  // au Kanban comme à la Liste et survit au changement d'onglet.
  filtres: {q:'', assigne:'', priorite:'', type:'', module:'', service:'', rapide:'', moi:false},
  sousTaches: true,     // vue Liste : afficher ou non les lignes de sous-tâches
  ouverts: new Set(),   // Kanban : cartes dont la pile de sous-tâches est dépliée
  actif: null,          // carte visée par les touches 1–5 (survol ou J/K)
  tri: {champ:'ordre', sens:'asc'},
  drag: null,
  me: null,
};

const ICO_SUN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICO_MOON = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function toast(msg,type){const t=document.createElement('div');t.className='toast'+(type==='err'?' err':'');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3400);}
async function api(url,opts){
  opts=opts||{};opts.credentials='include';
  const r=await fetch(url,opts);
  if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}
  return r.json();
}
function jpost(url,body,method){
  return api(url,{method:method||'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
}

// ── Référentiels : jamais de valeur en dur, tout vient de /api/taches/meta ──
function statutDef(code){return (S.meta&&S.meta.statuts||[]).find(s=>s.code===code)||{code:code,label:code,couleur:'muted',final:false};}
function prioriteDef(code){return (S.meta&&S.meta.priorites||[]).find(p=>p.code===code)||{code:code,label:code,couleur:'muted'};}
function typeLabel(code){const t=(S.meta&&S.meta.types||[]).find(x=>x.code===code);return t?t.label:(code||'');}
function moduleLabel(code){const m=(S.meta&&S.meta.modules||[]).find(x=>x.code===code);return m?m.label:(code||'');}
function statutsFinaux(){return (S.meta&&S.meta.statuts||[]).filter(s=>s.final).map(s=>s.code);}
function couleurVar(c){return c==='muted'?'var(--muted)':'var('+'--'+c+')';}

// ── Formats ──
const MOIS_COURT=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'];
function fmtDate(s){if(!s)return '';const d=new Date(String(s).substr(0,10));if(isNaN(d))return s;return d.getDate()+' '+MOIS_COURT[d.getMonth()]+' '+d.getFullYear();}
function fmtDateTime(s){
  if(!s)return '';const d=new Date(s);if(isNaN(d))return s;
  return d.getDate()+' '+MOIS_COURT[d.getMonth()]+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
}
function joursRestants(iso){
  if(!iso)return null;
  const d=new Date(String(iso).substr(0,10));if(isNaN(d))return null;
  const auj=new Date();auj.setHours(0,0,0,0);d.setHours(0,0,0,0);
  return Math.round((d-auj)/86400000);
}
function initiales(nom){
  const p=String(nom||'').trim().split(/\s+/).filter(Boolean);
  if(!p.length)return '?';
  if(p.length===1)return p[0].slice(0,2).toUpperCase();
  return (p[0][0]+p[p.length-1][0]).toUpperCase();
}
function avatarHtml(nom,url,titre){
  if(!nom)return '<span class="avatar none" title="Non assigné">—</span>';
  const t=esc(titre||nom);
  if(url)return '<span class="avatar" title="'+t+'"><img src="'+esc(url)+'" alt=""></span>';
  return '<span class="avatar" title="'+t+'">'+esc(initiales(nom))+'</span>';
}
// Pile d'avatars : au-delà de 3 personnes on compte le reste, sinon la carte
// déborde sur les colonnes étroites.
const PILE_MAX=3;
function pileHtml(assignes,max){
  const list=assignes||[];
  if(!list.length)return '<span class="avatar none" title="Non assigné">—</span>';
  const n=max||PILE_MAX;
  const montres=list.slice(0,n),reste=list.length-montres.length;
  return '<span class="pile">'+
    montres.map(u=>avatarHtml(u.nom,u.avatar_url)).join('')+
    (reste>0?'<span class="avatar plus" title="'+esc(list.slice(n).map(u=>u.nom).join(', '))+'">+'+reste+'</span>':'')+
  '</span>';
}
function nomsAssignes(assignes){
  const list=assignes||[];
  if(!list.length)return '';
  if(list.length===1)return list[0].nom||'';
  return (list[0].nom||'')+' +'+(list.length-1);
}

function fmtTaille(o){
  const n=Number(o)||0;
  if(n<1024)return n+' o';
  if(n<1048576)return Math.round(n/1024)+' Ko';
  return (n/1048576).toFixed(1)+' Mo';
}
function fmtH(h){const n=Number(h)||0;return n?(Number.isInteger(n)?n:n.toFixed(1))+' h':'';}

// ── Sélecteur multi-assignés ────────────────────────────────────────────
// Un <select multiple> natif est inutilisable au clavier comme à la souris dès
// qu'il y a plus de trois entrées : on rend des chips + un popover cherchable.
// `onChange(ids)` est appelé à chaque coche/décoche.
function champAssignes(hostId, selection, onChange, connus){
  const host=document.getElementById(hostId);
  if(!host)return;
  let ids=(selection||[]).slice();
  let ouvert=false;
  // `connus` = les assignés réels de la tâche. La liste proposée couvre tous
  // les services, mais une tâche plus ancienne peut porter quelqu'un qui n'y
  // figure plus : on l'affiche quand même pour pouvoir le retirer.
  const horsListe=(connus||[]).filter(u=>!((S.meta&&S.meta.users)||[]).some(x=>x.id===u.id));

  function tousUsers(){
    return ((S.meta&&S.meta.users)||[]).concat(horsListe);
  }

  function rendre(){
    const users=tousUsers();
    const choisis=ids.map(id=>users.find(u=>u.id===id)).filter(Boolean);
    host.innerHTML=
      '<div class="asg-box'+(ouvert?' open':'')+'" tabindex="0" role="button" aria-haspopup="listbox">'+
        (choisis.length
          ? choisis.map(u=>'<span class="asg-chip">'+avatarHtml(u.nom,u.avatar_url)+esc(u.nom||'')+
              '<button type="button" class="x" data-retirer="'+u.id+'" aria-label="Retirer">×</button></span>').join('')
          : '<span class="asg-vide">Personne — cliquer pour assigner</span>')+
      '</div>'+
      (ouvert?popHtml():'');
    brancher();
  }
  function popHtml(){
    return '<div class="asg-pop">'+
      '<input type="text" class="asg-q" placeholder="Rechercher (nom, service…)" autocomplete="off">'+
      '<div class="asg-list"></div>'+
    '</div>';
  }
  function rendreListe(filtre){
    const zone=host.querySelector('.asg-list');
    if(!zone)return;
    const q=(filtre||'').trim().toLowerCase();
    const users=tousUsers().filter(u=>!q
      ||String(u.nom||'').toLowerCase().includes(q)
      ||String(u.service_label||'').toLowerCase().includes(q));
    if(!users.length){
      zone.innerHTML='<div class="asg-rien">Aucun résultat pour « '+esc(filtre)+' »</div>';
      return;
    }
    zone.innerHTML=users.map(u=>{
      const on=ids.indexOf(u.id)!==-1;
      return '<label class="asg-opt'+(on?' actif':'')+'" data-uid="'+u.id+'">'+
        '<input type="checkbox"'+(on?' checked':'')+'>'+
        avatarHtml(u.nom,u.avatar_url)+
        '<span class="n">'+esc(u.nom||'')+'</span>'+
        (u.service_label?'<span class="asg-svc">'+esc(u.service_label)+'</span>':'')+
      '</label>';
    }).join('');
    zone.querySelectorAll('.asg-opt').forEach(el=>{
      el.addEventListener('mousedown',e=>e.preventDefault());
      el.addEventListener('click',e=>{
        e.preventDefault();e.stopPropagation();
        const uid=Number(el.dataset.uid);
        const i=ids.indexOf(uid);
        if(i===-1)ids.push(uid);else ids.splice(i,1);
        const champ=host.querySelector('.asg-q');
        const q2=champ?champ.value:'';
        rendre();
        const c2=host.querySelector('.asg-q');
        if(c2){c2.value=q2;c2.focus();}
        rendreListe(q2);
        onChange(ids.slice());
      });
    });
  }
  function brancher(){
    const box=host.querySelector('.asg-box');
    box.addEventListener('click',e=>{
      if(e.target.closest('[data-retirer]'))return;
      ouvert=!ouvert;rendre();
      if(ouvert){
        rendreListe('');
        requestAnimationFrame(()=>{const q=host.querySelector('.asg-q');if(q)q.focus();});
      }
    });
    box.addEventListener('keydown',e=>{
      if(e.key==='Enter'||e.key===' '){e.preventDefault();box.click();}
    });
    host.querySelectorAll('[data-retirer]').forEach(b=>{
      b.addEventListener('click',e=>{
        e.stopPropagation();
        const uid=Number(b.dataset.retirer);
        ids=ids.filter(x=>x!==uid);
        rendre();
        if(ouvert)rendreListe('');
        onChange(ids.slice());
      });
    });
    const q=host.querySelector('.asg-q');
    if(q){
      q.addEventListener('input',()=>rendreListe(q.value));
      q.addEventListener('keydown',e=>{
        // stopPropagation obligatoire : ce handler retire le popover du DOM,
        // donc si l'événement remonte jusqu'au document, le garde-fou du tiroir
        // ne voit plus de popover et ferme toute la fiche. Échap doit fermer un
        // seul niveau à la fois.
        if(e.key==='Escape'){e.preventDefault();e.stopPropagation();ouvert=false;rendre();}
      });
      rendreListe(q.value);
    }
  }
  // Fermeture au clic extérieur — enregistrée une fois par champ.
  // Garde-fou `isConnected` : le clic qui OUVRE le popover reconstruit le champ,
  // donc au moment où l'événement remonte jusqu'au document, sa cible a été
  // retirée du DOM. `host.contains()` répond alors false et le popover se
  // refermait aussitôt qu'ouvert. On ignore les cibles détachées.
  document.addEventListener('click',e=>{
    if(!ouvert)return;
    if(!e.target||!e.target.isConnected)return;
    if(host.contains(e.target))return;
    ouvert=false;rendre();
  });
  rendre();
  return {valeur:()=>ids.slice()};
}

// ── Shell ──
function getPrefs(){return window.MySifaTheme?MySifaTheme.loadPrefs():{mode:'dark'};}
function syncThemeBtn(){
  const isLight=getPrefs().mode==='light';
  const i=document.getElementById('theme-ico');const l=document.getElementById('theme-label');
  if(i)i.innerHTML=isLight?ICO_SUN:ICO_MOON;
  if(l)l.textContent=isLight?'Mode sombre':'Mode clair';
}
// Hauteur du bandeau staging v1, exposee en variable CSS pour que les elements
// position:fixed (tiroir, modales) s'en decalent. 0 en prod : aucun bandeau.
function syncBandeauOffset(){
  const b=document.querySelector('.staging-bandeau');
  const h=b?Math.round(b.getBoundingClientRect().height||24):0;
  document.documentElement.style.setProperty('--msf-top',h+'px');
}

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const VIEW_META={
  kanban:{titre:'Kanban',sub:"Ce que l'équipe doit faire, en cours et terminé.",guide:'taches-kanban'},
  liste:{titre:'Liste',sub:'Toutes les tâches actives, filtrables et triables.',guide:'taches-liste'},
  archives:{titre:'Archives',sub:'Tâches archivées — conservées pour l’historique.',guide:'taches-liste'},
};
const VALID_VIEWS=['kanban','liste','archives'];
function estBoard(v){return v==='kanban';}
function readView(){
  try{
    const h=(location.hash||'').replace(/^#/,'').trim();
    // Ancien onglet « Mes tâches » : les liens et favoris en #mes atterrissent
    // sur le Kanban avec la bascule déjà armée.
    if(h==='mes'){S.filtres.moi=true;return 'kanban';}
    if(VALID_VIEWS.indexOf(h)!==-1)return h;
  }catch(e){}
  return 'kanban';
}
function showView(v,opts){
  if(VALID_VIEWS.indexOf(v)===-1)v='kanban';
  S.view=v;
  VALID_VIEWS.forEach(id=>{const n=document.getElementById('nav-'+id);if(n)n.classList.toggle('active',id===v);});
  document.getElementById('view-kanban').style.display=estBoard(v)?'':'none';
  document.getElementById('view-liste').style.display=estBoard(v)?'none':'';
  const m=VIEW_META[v];
  document.getElementById('page-title').textContent=m.titre;
  document.getElementById('page-sub').textContent=m.sub;
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=m.titre;
  // Le bouton n'a de sens qu'en Liste : sur le Kanban les sous-tâches sont
  // toujours regroupées sous leur mère, jamais masquables.
  const bs=document.getElementById('btn-sous');
  if(bs)bs.style.display=estBoard(v)?'none':'';
  syncMoi();
  syncGuideBtn();
  closeSidebar();
  if(!(opts&&opts.silent)){try{if(location.hash!=='#'+v)history.replaceState(null,'','#'+v);}catch(e){}}
  chargerTaches();
}

// ══════════════════════════════════════════════════════════════════
// Chargement
// ══════════════════════════════════════════════════════════════════
function remplirFiltres(){
  const fa=document.getElementById('f-assigne');
  fa.innerHTML='<option value="">Tout le monde</option><option value="0">Non assignées</option>'+
    (S.meta.users||[]).map(u=>'<option value="'+u.id+'">'+esc(u.nom||'')+'</option>').join('');
  document.getElementById('f-priorite').innerHTML='<option value="">Toutes priorités</option>'+
    (S.meta.priorites||[]).map(p=>'<option value="'+esc(p.code)+'">'+esc(p.label)+'</option>').join('');
  document.getElementById('f-type').innerHTML='<option value="">Tous types</option>'+
    (S.meta.types||[]).map(t=>'<option value="'+esc(t.code)+'">'+esc(t.label)+'</option>').join('');
  document.getElementById('f-module').innerHTML='<option value="">Tous modules</option>'+
    (S.meta.modules||[]).map(m=>'<option value="'+esc(m.code)+'">'+esc(m.label)+'</option>').join('');
  // Filtrer par service n'a de sens que si on en voit plusieurs : à un seul
  // service visible, la liste n'offrirait qu'un choix déjà appliqué.
  const fs=document.getElementById('f-service');
  const services=S.meta.services||[];
  if(fs){
    fs.innerHTML='<option value="">Tous services</option>'+
      services.map(x=>'<option value="'+esc(x.code)+'">'+esc(x.label)+'</option>').join('');
    fs.style.display=services.length>1?'':'none';
  }
  const bn=document.getElementById('btn-nouvelle');
  if(bn&&!PEUT_ECRIRE)bn.style.display='none';
}

function queryFiltres(){
  const p=new URLSearchParams();
  const f=S.filtres;
  if(f.q)p.set('q',f.q);
  if(f.moi){
    // Bascule « Mes tâches » : filtre posé côté serveur, prioritaire sur la
    // liste déroulante des personnes (masquée tant que la bascule est active).
    if(S.meta&&S.meta.moi)p.set('assigne',String(S.meta.moi.id));
  }
  else if(f.assigne==='0')p.set('non_assignees','1');
  else if(f.assigne)p.set('assigne',f.assigne);
  if(f.priorite)p.set('priorite',f.priorite);
  if(f.type)p.set('type',f.type);
  if(f.module)p.set('module',f.module);
  if(f.service)p.set('service',f.service);
  if(S.view==='archives')p.set('archivees','1');
  return p.toString();
}

async function chargerTaches(){
  try{
    const j=await api('/api/taches?'+queryFiltres());
    S.taches=j.taches||[];
    renderStats();
    // « Non assignées » et les raccourcis de compteur se filtrent côté client :
    // ils ne changent pas la requête, seulement la sélection affichée.
    render();
  }catch(e){
    toast(e.message,'err');
    const b=document.getElementById('board');
    if(b)b.innerHTML='<div class="empty">Erreur de chargement : '+esc(e.message)+'</div>';
  }
}

async function chargerStats(){
  try{S.stats=await api('/api/taches/stats');renderStats();}catch(e){}
}

function tachesVisibles(){
  let list=S.taches.slice();
  const f=S.filtres;
  if(f.rapide==='retard'){
    const finaux=statutsFinaux();
    list=list.filter(t=>t.echeance&&joursRestants(t.echeance)<0&&finaux.indexOf(t.statut)===-1);
  }else if(f.rapide==='non_assignees'){
    list=list.filter(t=>!(t.assignes&&t.assignes.length));
  }else if(f.rapide&&f.rapide.indexOf('statut:')===0){
    const code=f.rapide.slice(7);
    list=list.filter(t=>t.statut===code);
  }
  return list;
}

// ══════════════════════════════════════════════════════════════════
// Rendu
// ══════════════════════════════════════════════════════════════════
function render(){
  // Le badge de la nav « Liste » compte TOUTES les tâches actives, pas le
  // résultat courant : sinon il chutait à 1 dès qu'on ouvrait « Mes tâches ».
  const total=Object.values((S.stats&&S.stats.par_statut)||{}).reduce((a,b)=>a+b,0);
  document.getElementById('badge-total').textContent=String(total||S.taches.length);
  if(estBoard(S.view))renderKanban();
  else renderListe();
}

// Compteur de la bascule « Mes tâches » — mêmes chiffres que la pastille du portail.
async function chargerBadgeMes(){
  try{
    const j=await api('/api/taches/badge');
    const b=document.getElementById('cnt-moi');
    if(!b)return;
    const n=Number(j.count||0),r=Number(j.en_retard||0);
    b.textContent=String(n);
    b.style.display=n?'':'none';
    b.classList.toggle('warn',r>0);
    const btn=document.getElementById('btn-moi');
    if(btn)btn.title=r>0
      ? n+' tâche'+(n>1?'s':'')+' assignée'+(n>1?'s':'')+', dont '+r+' en retard'
      : 'N’afficher que les tâches qui me sont assignées — vaut pour le Kanban comme pour la Liste';
  }catch(e){}
}

function renderStats(){
  if(!S.meta)return;
  const row=document.getElementById('stats-row');
  const parts=[];
  // Bascule « Mes tâches » armée : les compteurs se calculent sur ce qui est
  // chargé — c'est-à-dire mes tâches. Afficher les totaux de l'équipe au-dessus
  // d'un board filtré sur moi n'aurait aucun sens.
  const mesVues=!!S.filtres.moi;
  const finaux=statutsFinaux();
  let parStatut=S.stats.par_statut||{};
  let enRetard=S.stats.en_retard||0;
  if(mesVues){
    parStatut={};
    enRetard=0;
    S.taches.forEach(t=>{
      parStatut[t.statut]=(parStatut[t.statut]||0)+1;
      if(t.echeance&&joursRestants(t.echeance)<0&&finaux.indexOf(t.statut)===-1)enRetard++;
    });
  }
  (S.meta.statuts||[]).forEach(st=>{
    const n=parStatut[st.code]||0;
    const on=S.filtres.rapide==='statut:'+st.code;
    parts.push('<div class="stat'+(on?' active':'')+'" data-rapide="statut:'+esc(st.code)+'">'+
      '<span class="col-dot" style="background:'+couleurVar(st.couleur)+'"></span>'+
      esc(st.label)+' <b>'+n+'</b></div>');
  });
  if(enRetard>0){
    const on=S.filtres.rapide==='retard';
    parts.push('<div class="stat alert'+(on?' active':'')+'" data-rapide="retard">En retard <b>'+enRetard+'</b></div>');
  }
  // « Non assignées » n'a pas de sens dans une vue filtrée sur une personne.
  if(!mesVues&&S.stats.non_assignees>0){
    const on=S.filtres.rapide==='non_assignees';
    parts.push('<div class="stat'+(on?' active':'')+'" data-rapide="non_assignees">Non assignées <b>'+S.stats.non_assignees+'</b></div>');
  }
  row.innerHTML=parts.join('');
  row.querySelectorAll('.stat').forEach(el=>{
    el.onclick=()=>{
      const v=el.getAttribute('data-rapide');
      S.filtres.rapide=(S.filtres.rapide===v)?'':v;
      renderStats();render();
    };
  });
}

const SVG_CHEVRON='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';

function sousCarteHtml(t){
  const st=statutDef(t.statut);
  const clos=statutsFinaux().indexOf(t.statut)!==-1;
  // Pastille de couleur plutôt qu'étiquette texte : le statut se lit sans manger
  // la largeur d'une colonne étroite. Le libellé reste en infobulle.
  return '<div class="sous-carte'+(clos?' close':'')+'" data-sous-id="'+t.id+'" title="'+esc(st.label)+' — '+esc(t.titre)+'">'+
    '<span class="pastille" style="background:'+couleurVar(st.couleur)+'"></span>'+
    '<span class="st">'+esc(t.titre)+'</span>'+
    ((t.assignes&&t.assignes.length)?pileHtml(t.assignes,2):'')+
  '</div>';
}

// Carte compacte. Ce qui reste visible : les assignés (en haut, en petit), le
// titre, l'alerte de retard et la progression de checklist. Ce qui disparaît :
// les étiquettes type / module / priorité et la date d'échéance — elles se
// lisent dans la fiche, la vue Liste ou l'infobulle de la carte. La priorité
// reste portée par la couleur du liseré gauche.
function carteHtml(t,enfants){
  const prio=prioriteDef(t.priorite);
  const jr=joursRestants(t.echeance);
  const finaux=statutsFinaux();
  const clos=finaux.indexOf(t.statut)!==-1;
  const enRetard=(!clos&&jr!==null&&jr<0);

  // Tout ce qu'on retire de la carte reste accessible au survol.
  const infos=[];
  if(t.priorite)infos.push('Priorité : '+prio.label);
  if(t.type)infos.push(typeLabel(t.type));
  if(t.module)infos.push(moduleLabel(t.module));
  if(t.echeance)infos.push('Échéance : '+fmtDate(t.echeance)+(enRetard?' (en retard de '+Math.abs(jr)+' j)':''));
  if(t.estimation_h)infos.push('Estimation : '+fmtH(t.estimation_h));
  if(t.nb_sous_taches)infos.push(t.nb_sous_taches_faites+'/'+t.nb_sous_taches+' sous-tâches');
  if(t.nb_commentaires)infos.push(t.nb_commentaires+' commentaire'+(t.nb_commentaires>1?'s':''));
  if(t.nb_fichiers)infos.push(t.nb_fichiers+' fichier'+(t.nb_fichiers>1?'s':''));
  const bulle=esc(t.titre+(infos.length?'\n'+infos.join(' · '):''));

  const alerte=enRetard
    ? '<span class="tcard-retard" title="En retard de '+Math.abs(jr)+' jour'+(Math.abs(jr)>1?'s':'')+
      ' — échéance '+esc(fmtDate(t.echeance))+'"><i></i></span>'
    : '';

  let prog='';
  if(t.nb_checklist>0){
    const pct=Math.round(100*t.nb_checklist_faits/t.nb_checklist);
    prog='<div class="progress" title="Checklist '+t.nb_checklist_faits+'/'+t.nb_checklist+'"><i style="width:'+pct+'%"></i></div>';
  }

  // Bouton chevron : replie/déplie la pile des sous-tâches sous la carte.
  const kids=enfants||[];
  const ouvert=S.ouverts.has(t.id);
  const chevron=kids.length
    ? '<button type="button" class="sous-toggle'+(ouvert?' ouvert':'')+'" data-toggle="'+t.id+'"'+
      ' title="'+(ouvert?'Masquer':'Afficher')+' les sous-tâches" aria-expanded="'+(ouvert?'true':'false')+'">'+
      SVG_CHEVRON+kids.length+'</button>'
    : '';

  // L'en-tête ne s'affiche que s'il porte quelque chose : une carte sans
  // assigné, sans retard et sans sous-tâche n'a pas à réserver une ligne vide.
  const pile=(t.assignes&&t.assignes.length)?pileHtml(t.assignes,3):'';
  const tete=(pile||alerte||chevron)
    ? '<div class="tcard-hd">'+pile+'<span class="sp"></span>'+alerte+chevron+'</div>'
    : '';

  return '<div class="tstack">'+
    '<div class="tcard prio-'+esc(t.priorite||'normale')+(S.actif===t.id?' actif':'')+'" draggable="true" data-id="'+t.id+'" title="'+bulle+'">'+
      tete+
      '<div class="tcard-title">'+esc(t.titre)+'</div>'+
      (t.parent_titre?'<div style="font-size:10px;color:var(--muted);margin-top:3px">↳ '+esc(t.parent_titre)+'</div>':'')+
      prog+
    '</div>'+
    (kids.length&&ouvert?'<div class="sous-pile">'+kids.map(sousCarteHtml).join('')+'</div>':'')+
  '</div>';
}

function renderKanban(){
  const board=document.getElementById('board');
  if(!S.meta){board.innerHTML='<div class="empty">Chargement…</div>';return;}
  const list=tachesVisibles();

  // Une sous-tâche n'est jamais une carte autonome : elle vit dans la pile de sa
  // tâche mère, dépliable par le chevron. Elle apparaît donc dans la colonne du
  // PARENT, même si son propre statut diffère — c'est le lien qui prime.
  // Exception : si la mère est exclue par un filtre, la sous-tâche redevient une
  // carte à part entière avec son fil d'Ariane, plutôt que de disparaître.
  const visibles=new Set(list.map(t=>t.id));
  const enfantsPar=new Map();
  const cartes=[];
  for(const t of list){
    if(t.parent_id&&visibles.has(t.parent_id)){
      if(!enfantsPar.has(t.parent_id))enfantsPar.set(t.parent_id,[]);
      enfantsPar.get(t.parent_id).push(t);
    }else{
      cartes.push(t);
    }
  }

  board.innerHTML=(S.meta.statuts||[]).map(st=>{
    const items=cartes.filter(t=>t.statut===st.code);
    return '<section class="col" data-statut="'+esc(st.code)+'">'+
      '<div class="col-head">'+
        '<span class="col-dot" style="background:'+couleurVar(st.couleur)+'"></span>'+
        '<span class="col-title">'+esc(st.label)+'</span>'+
        '<span class="col-count">'+items.length+'</span>'+
      '</div>'+
      '<div class="col-body" data-statut="'+esc(st.code)+'">'+
        (items.length?items.map(t=>carteHtml(t,enfantsPar.get(t.id))).join(''):'<div style="font-size:11.5px;color:var(--muted);text-align:center;padding:14px 6px">Aucune tâche</div>')+
      '</div>'+
      '<button type="button" class="col-add" data-add="'+esc(st.code)+'">+ Ajouter une tâche</button>'+
    '</section>';
  }).join('');

  board.querySelectorAll('.sous-toggle').forEach(b=>{
    b.addEventListener('click',e=>{
      e.stopPropagation();   // le clic ne doit pas ouvrir la fiche de la mère
      const id=Number(b.dataset.toggle);
      if(S.ouverts.has(id))S.ouverts.delete(id);else S.ouverts.add(id);
      try{localStorage.setItem('mysifa_taches_ouverts',JSON.stringify([...S.ouverts]));}catch(err){}
      renderKanban();
    });
  });
  board.querySelectorAll('.sous-carte').forEach(el=>{
    el.addEventListener('click',e=>{e.stopPropagation();openDetail(Number(el.dataset.sousId));});
  });

  board.querySelectorAll('.tcard').forEach(c=>{
    // Le survol désigne la carte active : les touches 1–5 s'y appliquent sans
    // qu'on ait à cliquer, ce qui ouvrirait la fiche.
    c.addEventListener('mouseenter',()=>{marquerActif(Number(c.dataset.id),{scroll:false});});
    c.addEventListener('click',e=>{
      if(e.target.closest('.sous-toggle'))return;
      openDetail(Number(c.dataset.id));
    });
    c.addEventListener('dragstart',e=>{
      S.drag=Number(c.dataset.id);
      c.classList.add('dragging');
      document.body.classList.add('drag-actif');
      try{e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',c.dataset.id);}catch(err){}
    });
    c.addEventListener('dragend',()=>{
      c.classList.remove('dragging');S.drag=null;
      document.body.classList.remove('drag-actif');
      const z=document.getElementById('arch-drop');if(z)z.classList.remove('survol');
      board.querySelectorAll('.col').forEach(col=>col.classList.remove('drop'));
    });
  });
  board.querySelectorAll('.col-add').forEach(b=>{
    b.addEventListener('click',()=>openTacheModal(null,{statut:b.dataset.add}));
  });
  board.querySelectorAll('.col-body').forEach(zone=>{
    zone.addEventListener('dragover',e=>{
      e.preventDefault();
      try{e.dataTransfer.dropEffect='move';}catch(err){}
      zone.closest('.col').classList.add('drop');
    });
    zone.addEventListener('dragleave',e=>{
      if(!zone.contains(e.relatedTarget))zone.closest('.col').classList.remove('drop');
    });
    zone.addEventListener('drop',e=>{
      e.preventDefault();
      zone.closest('.col').classList.remove('drop');
      if(!S.drag)return;
      const voisins=[...zone.querySelectorAll('.tcard')].filter(c=>Number(c.dataset.id)!==S.drag);
      let apres=null,avant=null;
      for(const c of voisins){
        const r=c.getBoundingClientRect();
        if(e.clientY>r.top+r.height/2)apres=Number(c.dataset.id);
        else{avant=Number(c.dataset.id);break;}
      }
      deplacer(S.drag,zone.dataset.statut,apres,avant);
    });
  });
}

// Cible d'archivage : branchée une seule fois, elle vit hors du board (qui est
// reconstruit à chaque rendu). Elle archive — elle ne supprime pas : le contenu
// reste consultable dans l'onglet Archives.
function brancherArchivage(){
  const zone=document.getElementById('arch-drop');
  if(!zone)return;
  zone.addEventListener('dragover',e=>{
    if(!S.drag)return;
    e.preventDefault();
    try{e.dataTransfer.dropEffect='move';}catch(err){}
    zone.classList.add('survol');
  });
  zone.addEventListener('dragleave',()=>zone.classList.remove('survol'));
  zone.addEventListener('drop',async e=>{
    e.preventDefault();
    zone.classList.remove('survol');
    document.body.classList.remove('drag-actif');
    const id=S.drag;
    S.drag=null;
    if(!id)return;
    try{
      const j=await jpost('/api/taches/'+id+'/archive',{});
      if(!j.archivee){
        // La tâche était déjà archivée : on la remet dans cet état plutôt que
        // de laisser le geste la désarchiver silencieusement.
        await jpost('/api/taches/'+id+'/archive',{});
      }
      toast('Tâche archivée.');
      if(S.detail&&S.detail.tache&&S.detail.tache.id===id)closeDetail();
      await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
    }catch(err){toast(err.message,'err');}
  });
}

async function deplacer(id,statut,apres_id,avant_id){
  try{
    await jpost('/api/taches/'+id+'/move',{statut:statut,apres_id:apres_id,avant_id:avant_id});
    await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
    if(S.detail&&S.detail.tache&&S.detail.tache.id===id)openDetail(id,{silent:true});
  }catch(e){toast(e.message,'err');chargerTaches();}
}

const COLONNES_LISTE=[
  {champ:'titre',label:'Tâche'},
  {champ:'statut',label:'Statut'},
  {champ:'priorite',label:'Priorité'},
  {champ:'assignes',label:'Assigné'},
  {champ:'module',label:'Module'},
  {champ:'echeance',label:'Échéance'},
  {champ:'temps_passe_h',label:'Temps'},
];

function renderListe(){
  const head=document.getElementById('liste-head');
  head.innerHTML=COLONNES_LISTE.map(c=>{
    const on=S.tri.champ===c.champ;
    return '<th data-champ="'+c.champ+'"'+(on?' class="sorted"':'')+'>'+esc(c.label)+
      '<span class="sort">'+(on?(S.tri.sens==='asc'?'↑':'↓'):'↕')+'</span></th>';
  }).join('');
  head.querySelectorAll('th').forEach(th=>{
    th.onclick=()=>{
      const c=th.dataset.champ;
      if(S.tri.champ===c)S.tri.sens=(S.tri.sens==='asc'?'desc':'asc');
      else{S.tri.champ=c;S.tri.sens='asc';}
      renderListe();
    };
  });

  const base=S.sousTaches?tachesVisibles():tachesVisibles().filter(t=>!t.parent_id);
  const trie=base.slice().sort((a,b)=>{
    const c=S.tri.champ;
    let va=a[c],vb=b[c];
    if(c==='priorite'){
      const poids=o=>{const p=(S.meta.priorites||[]).find(x=>x.code===o);return p?p.poids:0;};
      va=poids(a.priorite);vb=poids(b.priorite);
    }
    if(c==='statut'){
      const rang=o=>(S.meta.statuts||[]).findIndex(x=>x.code===o);
      va=rang(a.statut);vb=rang(b.statut);
    }
    if(c==='assignes'){
      // Tri sur le 1er assigné (ordre alphabétique) ; non assigné en dernier.
      const cle=o=>(o.assignes&&o.assignes.length)?(o.assignes[0].nom||''):'\uffff';
      va=cle(a);vb=cle(b);
    }
    if(va==null)va='';if(vb==null)vb='';
    let r;
    if(typeof va==='number'&&typeof vb==='number')r=va-vb;
    else r=String(va).localeCompare(String(vb),'fr',{numeric:true});
    return S.tri.sens==='asc'?r:-r;
  });

  // Regroupement : une sous-tache s'affiche TOUJOURS immediatement sous sa tache
  // mere, jamais isolee au milieu de la liste. Le tri s'applique aux racines,
  // puis aux enfants a l'interieur de chaque groupe.
  // Cas particulier : une sous-tache dont la mere est exclue par un filtre (ou
  // masquee) n'a plus de groupe -- elle remonte alors au niveau racine plutot
  // que de disparaitre, avec son fil d'Ariane pour rester comprehensible.
  const presentes=new Set(trie.map(t=>t.id));
  const enfantsPar=new Map();
  const racines=[];
  for(const t of trie){
    if(t.parent_id&&presentes.has(t.parent_id)){
      if(!enfantsPar.has(t.parent_id))enfantsPar.set(t.parent_id,[]);
      enfantsPar.get(t.parent_id).push(t);
    }else{
      racines.push(t);
    }
  }
  const list=[];
  for(const r of racines){
    list.push({t:r,enfant:false,orphelin:!!r.parent_id});
    for(const c of (enfantsPar.get(r.id)||[])) list.push({t:c,enfant:true,orphelin:false});
  }

  const body=document.getElementById('liste-body');
  if(!list.length){
    body.innerHTML='<tr><td colspan="'+COLONNES_LISTE.length+'"><div class="empty"><b>Aucune tâche</b>'+
      (S.view==='archives'?'Rien d’archivé pour l’instant.':'Créez la première avec « Nouvelle tâche ».')+'</div></td></tr>';
    return;
  }
  const finaux=statutsFinaux();
  body.innerHTML=list.map(ligne=>{
    const t=ligne.t;
    const st=statutDef(t.statut),prio=prioriteDef(t.priorite);
    const jr=joursRestants(t.echeance);
    const clos=finaux.indexOf(t.statut)!==-1;
    let dueCls='';
    if(!clos&&jr!==null){if(jr<0)dueCls=' late';else if(jr<=2)dueCls=' soon';}
    const sousTitre=[];
    // Sous une tache mere, le nom du parent est redondant : l'indentation le dit.
    // Il n'est rappele que pour une sous-tache orpheline (mere filtree).
    if(ligne.orphelin&&t.parent_titre)sousTitre.push('↳ '+t.parent_titre);
    if(t.type)sousTitre.push(typeLabel(t.type));
    if(t.nb_checklist)sousTitre.push('checklist '+t.nb_checklist_faits+'/'+t.nb_checklist);
    if(!ligne.enfant&&t.nb_sous_taches)sousTitre.push(t.nb_sous_taches+' sous-tâche'+(t.nb_sous_taches>1?'s':''));
    return '<tr data-id="'+t.id+'"'+(ligne.enfant?' class="row-sous"':'')+'>'+
      '<td class="t-titre'+(ligne.enfant?' est-sous':'')+'">'+
        (ligne.enfant?'<span class="arbre">↳</span>':'')+esc(t.titre)+
        (sousTitre.length?'<span class="sub">'+esc(sousTitre.join(' · '))+'</span>':'')+'</td>'+
      '<td><span class="tag '+esc(st.couleur)+'">'+esc(st.label)+'</span></td>'+
      '<td><span class="tag '+esc(prio.couleur)+'">'+esc(prio.label)+'</span></td>'+
      '<td>'+((t.assignes&&t.assignes.length)
        ?('<span style="display:inline-flex;align-items:center;gap:8px" title="'+esc((t.assignes||[]).map(u=>u.nom).join(', '))+'">'+
            pileHtml(t.assignes,2)+esc(nomsAssignes(t.assignes))+'</span>')
        :'<span style="color:var(--muted)">—</span>')+'</td>'+
      '<td>'+esc(t.module?moduleLabel(t.module):'—')+'</td>'+
      '<td class="due'+dueCls+'">'+(t.echeance?esc(fmtDate(t.echeance)):'—')+'</td>'+
      '<td>'+(t.temps_passe_h?esc(fmtH(t.temps_passe_h)):(t.estimation_h?'0 h':'—'))+(t.estimation_h?'<span style="color:var(--muted)"> / '+esc(fmtH(t.estimation_h))+'</span>':'')+'</td>'+
    '</tr>';
  }).join('');
  body.querySelectorAll('tr[data-id]').forEach(tr=>{
    tr.onclick=()=>openDetail(Number(tr.dataset.id));
  });
}

// ══════════════════════════════════════════════════════════════════
// Panneau de détail
// ══════════════════════════════════════════════════════════════════
async function openDetail(id,opts){
  try{
    const j=await api('/api/taches/'+id);
    S.detail=j;
    if(!(opts&&opts.silent))S.detailTab='detail';
    renderDrawer();
  }catch(e){toast(e.message,'err');}
}
function closeDetail(){
  S.detail=null;
  document.getElementById('drawer-root').innerHTML='';
  document.removeEventListener('keydown',onDrawerKey);
}
function onDrawerKey(e){
  if(e.key!=='Escape')return;
  if(document.getElementById('modal-root').firstElementChild)return;
  // Échap ferme d'abord ce qui est ouvert PAR-DESSUS le tiroir (popover
  // d'assignation) : sinon un simple Échap dans la recherche fait perdre toute
  // la fiche. Le champ gère sa propre fermeture, on laisse passer ce tour.
  if(document.querySelector('.asg-pop'))return;
  closeDetail();
}

function renderDrawer(){
  const root=document.getElementById('drawer-root');
  if(!S.detail){root.innerHTML='';return;}
  const d=S.detail,t=d.tache;
  const st=statutDef(t.statut);

  const onglets=[
    {id:'detail',label:'Détail',n:null},
    {id:'commentaires',label:'Commentaires',n:d.commentaires.length},
    {id:'fichiers',label:'Fichiers',n:d.fichiers.length},
    {id:'activite',label:'Activité',n:null},
  ];

  root.innerHTML=
  '<div class="drawer-back" id="dr-back"></div>'+
  '<aside class="drawer" role="dialog" aria-label="Détail de la tâche">'+
    '<div class="dr-head">'+
      '<div class="dr-head-main">'+
        '<div class="dr-title" id="dr-titre" title="Cliquer pour renommer">'+esc(t.titre)+'</div>'+
        '<div class="dr-meta">'+
          '<span class="tag '+esc(st.couleur)+'">'+esc(st.label)+'</span> · '+
          'Créée le '+esc(fmtDateTime(t.created_at))+(t.createur_nom?' par '+esc(t.createur_nom):'')+
          (t.archived_at?' · <span class="tag warn">Archivée</span>':'')+
        '</div>'+
      '</div>'+
      '<button type="button" class="dr-close" id="dr-close" aria-label="Fermer">×</button>'+
    '</div>'+
    '<div class="dr-tabs">'+
      onglets.map(o=>'<button type="button" class="dr-tab'+(S.detailTab===o.id?' active':'')+'" data-tab="'+o.id+'">'+
        esc(o.label)+(o.n?'<span class="n">'+o.n+'</span>':'')+'</button>').join('')+
    '</div>'+
    '<div class="dr-body">'+
      '<div class="dr-pane'+(S.detailTab==='detail'?' active':'')+'" id="pane-detail">'+paneDetail(d)+'</div>'+
      '<div class="dr-pane'+(S.detailTab==='commentaires'?' active':'')+'" id="pane-commentaires">'+paneCommentaires(d)+'</div>'+
      '<div class="dr-pane'+(S.detailTab==='fichiers'?' active':'')+'" id="pane-fichiers">'+paneFichiers(d)+'</div>'+
      '<div class="dr-pane'+(S.detailTab==='activite'?' active':'')+'" id="pane-activite">'+paneActivite(d)+'</div>'+
    '</div>'+
  '</aside>';

  root.querySelector('#dr-back').onclick=closeDetail;
  root.querySelector('#dr-close').onclick=closeDetail;
  root.querySelectorAll('.dr-tab').forEach(b=>{
    b.onclick=()=>{S.detailTab=b.dataset.tab;renderDrawer();};
  });
  document.addEventListener('keydown',onDrawerKey);
  brancherDetail();
}

function paneDetail(d){
  const t=d.tache;
  const opt=(items,val,vide)=>(vide?'<option value="">'+esc(vide)+'</option>':'')+
    items.map(i=>'<option value="'+esc(i.code!=null?i.code:i.id)+'"'+
      (String(val||'')===String(i.code!=null?i.code:i.id)?' selected':'')+'>'+esc(i.label||i.nom)+'</option>').join('');

  const chk=d.checklist;
  const nbFaits=chk.filter(c=>c.fait).length;

  return ''+
  '<div class="fgrid">'+
    '<div class="field"><label>Statut</label><select id="d-statut">'+opt(S.meta.statuts,t.statut)+'</select></div>'+
    '<div class="field"><label>Priorité</label><select id="d-priorite">'+opt(S.meta.priorites,t.priorite)+'</select></div>'+
    '<div class="field"><label>Échéance</label><input type="date" id="d-echeance" value="'+esc(t.echeance||'')+'"></div>'+
    '<div class="field full asg-field"><label>Assigné à</label><div id="d-assignes"></div></div>'+
    '<div class="field"><label>Type</label><select id="d-type">'+opt(S.meta.types,t.type)+'</select></div>'+
    '<div class="field"><label>Module</label><select id="d-module">'+opt(S.meta.modules,t.module,'Aucun')+'</select></div>'+
    (TOUS_SERVICES
      ? '<div class="field"><label>Service</label><select id="d-service">'+opt(S.meta.services,t.service)+'</select></div>'
      : '')+
    '<div class="field"><label>Estimation (h)</label><input type="number" step="0.25" min="0" id="d-estimation" value="'+esc(t.estimation_h!=null?t.estimation_h:'')+'"></div>'+
    '<div class="field"><label>Temps passé</label>'+
      '<div style="display:flex;gap:6px">'+
        '<input type="number" step="0.25" min="0" id="d-temps-ajout" placeholder="+ heures">'+
        '<button type="button" class="btn ghost small" id="d-temps-btn" style="white-space:nowrap">Ajouter</button>'+
      '</div>'+
      '<div style="font-size:11px;color:var(--muted);margin-top:5px">Cumul : <b style="color:var(--text2)">'+esc(fmtH(t.temps_passe_h)||'0 h')+'</b>'+
      (t.estimation_h?' sur '+esc(fmtH(t.estimation_h))+' estimées':'')+'</div>'+
    '</div>'+
    '<div class="field full"><label>Description</label><textarea id="d-description" placeholder="Contexte, attendu, critères d’acceptation…">'+esc(t.description||'')+'</textarea></div>'+
  '</div>'+

  '<div class="sec">'+
    '<div class="sec-hd"><h3>Checklist'+(chk.length?' · '+nbFaits+'/'+chk.length:'')+'</h3></div>'+
    (chk.length?chk.map(c=>
      '<div class="chk'+(c.fait?' done':'')+'" data-chk="'+c.id+'">'+
        '<input type="checkbox"'+(c.fait?' checked':'')+'>'+
        '<span class="lbl">'+esc(c.libelle)+'</span>'+
        (c.fait&&c.fait_par_nom?'<span style="font-size:10px;color:var(--muted)">'+esc(c.fait_par_nom)+'</span>':'')+
        '<button type="button" class="x" title="Supprimer">×</button>'+
      '</div>').join(''):'<div style="font-size:12px;color:var(--muted);padding:2px 0 4px">Aucun point de contrôle.</div>')+
    '<div class="inline-add"><input type="text" id="chk-new" placeholder="Ajouter un point de contrôle…"><button type="button" class="btn ghost small" id="chk-add">Ajouter</button></div>'+
  '</div>'+

  (t.parent_id?'':
  '<div class="sec">'+
    '<div class="sec-hd"><h3>Sous-tâches'+(d.sous_taches.length?' · '+d.sous_taches.length:'')+'</h3></div>'+
    (d.sous_taches.length?d.sous_taches.map(s=>{
      const sst=statutDef(s.statut);
      const clos=statutsFinaux().indexOf(s.statut)!==-1;
      return '<div class="sub-item'+(clos?' done':'')+'" data-sous="'+s.id+'">'+
        '<span class="tag '+esc(sst.couleur)+'">'+esc(sst.label)+'</span>'+
        '<span class="st">'+esc(s.titre)+'</span>'+
        ((s.assignes&&s.assignes.length)?pileHtml(s.assignes,2):'')+
      '</div>';
    }).join(''):'<div style="font-size:12px;color:var(--muted);padding:2px 0 4px">Aucune sous-tâche.</div>')+
    '<div class="inline-add"><input type="text" id="sous-new" placeholder="Ajouter une sous-tâche…"><button type="button" class="btn ghost small" id="sous-add">Ajouter</button></div>'+
  '</div>')+

  '<div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:6px;border-top:1px solid var(--border)">'+
    '<button type="button" class="btn ghost small" id="d-archive">'+(t.archived_at?'Désarchiver':'Archiver')+'</button>'+
    '<button type="button" class="btn danger small" id="d-delete" style="margin-left:auto">Supprimer</button>'+
  '</div>';
}

function paneCommentaires(d){
  return ''+
  '<div id="cmt-list">'+
    (d.commentaires.length?d.commentaires.map(c=>
      '<div class="cmt">'+avatarHtml(c.auteur_nom,c.auteur_avatar)+
        '<div class="cmt-body">'+
          '<div class="cmt-hd"><span class="cmt-auteur">'+esc(c.auteur_nom||'—')+'</span>'+
            '<span class="cmt-date">'+esc(fmtDateTime(c.created_at))+'</span>'+
            '<button type="button" class="cmt-del" data-cmt="'+c.id+'">Supprimer</button></div>'+
          '<div class="cmt-msg">'+esc(c.message)+'</div>'+
        '</div>'+
      '</div>').join(''):'<div class="empty"><b>Aucun commentaire</b>Ouvrez la discussion ci-dessous.</div>')+
  '</div>'+
  '<div class="cmt-form">'+
    '<textarea id="cmt-new" placeholder="Écrire un commentaire… (Ctrl+Entrée pour envoyer)"></textarea>'+
    '<div style="display:flex;justify-content:flex-end;margin-top:8px"><button type="button" class="btn small" id="cmt-send">Commenter</button></div>'+
  '</div>';
}

const IMG_RE=/\.(png|jpe?g|gif|webp|bmp|svg)$/i;
function paneFichiers(d){
  return ''+
  '<div class="drop-zone" id="fic-drop">'+
    '<div style="font-weight:600;margin-bottom:4px">Déposer un fichier de contexte</div>'+
    '<div style="font-size:11px">ou cliquer pour choisir — '+(S.meta.max_file_mb||25)+' Mo maximum</div>'+
    '<input type="file" id="fic-input" style="display:none">'+
  '</div>'+
  '<div style="margin-top:14px">'+
    (d.fichiers.length?d.fichiers.map(f=>
      '<div class="file-item">'+
        '<div class="file-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>'+
        '<div class="file-info"><div class="file-name">'+esc(f.nom)+'</div>'+
          '<div class="file-meta">'+esc(fmtTaille(f.taille_bytes))+' · '+esc(f.uploaded_nom||'')+' · '+esc(fmtDateTime(f.created_at))+'</div></div>'+
        '<button type="button" class="btn ghost small" data-preview="'+f.id+'" data-nom="'+esc(f.nom)+'">Ouvrir</button>'+
        '<button type="button" class="btn ghost small" data-fic-del="'+f.id+'">×</button>'+
      '</div>').join(''):'<div class="empty"><b>Aucun fichier</b>Maquettes, exports, captures : tout ce qui aide à comprendre la demande.</div>')+
  '</div>';
}

function paneActivite(d){
  if(!d.activite.length)return '<div class="empty"><b>Aucune activité</b>Les changements apparaîtront ici.</div>';
  return d.activite.map(a=>{
    let txt;
    if(a.action==='creation')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a créé la tâche';
    else if(a.action==='commentaire')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a commenté';
    else if(a.action==='commentaire_supprime')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a supprimé un commentaire';
    else if(a.action==='fichier')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a ajouté '+esc(a.apres||'un fichier');
    else if(a.action==='fichier_supprime')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a retiré '+esc(a.avant||'un fichier');
    else if(a.action==='archivage')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a archivé la tâche';
    else if(a.action==='desarchivage')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a désarchivé la tâche';
    else if(a.action==='suppression')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a supprimé la tâche';
    else if(a.action==='statut')txt='<b>'+esc(a.auteur_nom||'—')+'</b> : statut '+esc(statutDef(a.avant).label)+' → '+esc(statutDef(a.apres).label);
    else if(a.action==='temps')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a pointé du temps ('+esc(a.apres||'')+' h)';
    else if(a.action==='assignation')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a assigné '+esc(a.apres||'');
    else if(a.action==='desassignation')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a retiré '+esc(a.avant||'');
    else if(a.action&&a.action.indexOf('checklist')===0)txt='<b>'+esc(a.auteur_nom||'—')+'</b> · checklist : '+esc(a.avant||a.apres||'');
    else txt='<b>'+esc(a.auteur_nom||'—')+'</b> a modifié '+esc(a.champ||'')+
      (a.avant?' — <span style="color:var(--muted)">'+esc(a.avant)+'</span> →':' →')+' '+esc(a.apres||'vide');
    return '<div class="act"><span class="act-dot"></span><span>'+txt+'</span><span class="act-date">'+esc(fmtDateTime(a.created_at))+'</span></div>';
  }).join('');
}

// ── Interactions du panneau ──
function brancherDetail(){
  const d=S.detail;if(!d)return;
  const t=d.tache;
  const root=document.getElementById('drawer-root');

  async function patch(champ,valeur){
    try{
      const body={};body[champ]=valeur;
      await api('/api/taches/'+t.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
      await openDetail(t.id,{silent:true});
    }catch(e){toast(e.message,'err');}
  }

  const bind=(id,champ,transform)=>{
    const el=root.querySelector('#'+id);
    if(!el)return;
    el.addEventListener('change',()=>{
      let v=el.value;
      if(transform)v=transform(v);
      patch(champ,v);
    });
  };
  bind('d-statut','statut');
  bind('d-priorite','priorite');
  bind('d-type','type');
  bind('d-module','module',v=>v||null);
  if(TOUS_SERVICES)bind('d-service','service',v=>v||null);
  // Assignés : on enregistre SANS re-rendre le tiroir. `patch()` rappelle
  // renderDrawer(), ce qui reconstruirait le champ et fermerait le popover à
  // chaque case cochée — impossible d'assigner deux personnes d'affilée. Le
  // champ tient son propre affichage ; on se contente de rafraîchir les données
  // sous-jacentes pour le prochain rendu du tiroir.
  async function patchAssignes(ids){
    try{
      await api('/api/taches/'+t.id,{method:'PUT',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({assignes:ids})});
      S.detail=await api('/api/taches/'+t.id);
      await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
    }catch(e){toast(e.message,'err');}
  }
  champAssignes('d-assignes',(t.assignes||[]).map(u=>u.id),patchAssignes,t.assignes||[]);
  bind('d-echeance','echeance',v=>v||null);
  bind('d-estimation','estimation_h',v=>v===''?null:Number(v));

  const desc=root.querySelector('#d-description');
  if(desc){
    desc.addEventListener('blur',()=>{
      if((desc.value||'')===(t.description||''))return;
      patch('description',desc.value);
    });
  }

  // Titre éditable en place
  const titre=root.querySelector('#dr-titre');
  if(titre){
    titre.addEventListener('click',()=>{
      if(titre.querySelector('input'))return;
      const val=t.titre;
      titre.innerHTML='<input type="text" style="width:100%;background:var(--bg);border:1px solid var(--accent);border-radius:8px;padding:6px 9px;color:var(--text);font-size:15px;font-weight:700;font-family:inherit;outline:none">';
      const inp=titre.querySelector('input');
      inp.value=val;inp.focus();inp.select();
      const valider=()=>{
        const nv=(inp.value||'').trim();
        if(!nv||nv===val){renderDrawer();return;}
        patch('titre',nv);
      };
      inp.addEventListener('blur',valider);
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        if(e.key==='Escape'){e.preventDefault();inp.value=val;renderDrawer();}
      });
    });
  }

  // Temps passé
  const tbtn=root.querySelector('#d-temps-btn');
  if(tbtn){
    tbtn.onclick=async()=>{
      const inp=root.querySelector('#d-temps-ajout');
      const h=Number(inp.value);
      if(!h||h<=0){toast('Temps invalide — valeur supérieure à 0 attendue.','err');return;}
      try{
        await jpost('/api/taches/'+t.id+'/temps',{heures:h});
        inp.value='';
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
        toast('Temps ajouté.');
      }catch(e){toast(e.message,'err');}
    };
  }

  // Checklist
  root.querySelectorAll('.chk').forEach(el=>{
    const id=Number(el.dataset.chk);
    const box=el.querySelector('input[type=checkbox]');
    box.onchange=async()=>{
      try{
        await api('/api/taches/checklist/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({fait:box.checked})});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');box.checked=!box.checked;}
    };
    el.querySelector('.x').onclick=async()=>{
      try{
        await api('/api/taches/checklist/'+id,{method:'DELETE'});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
    };
  });
  const chkAdd=root.querySelector('#chk-add'),chkNew=root.querySelector('#chk-new');
  if(chkAdd){
    const envoyer=async()=>{
      const v=(chkNew.value||'').trim();
      if(!v)return;
      try{
        await jpost('/api/taches/'+t.id+'/checklist',{libelle:v});
        chkNew.value='';
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
        requestAnimationFrame(()=>{const n=document.getElementById('chk-new');if(n)n.focus();});
      }catch(e){toast(e.message,'err');}
    };
    chkAdd.onclick=envoyer;
    chkNew.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();envoyer();}});
  }

  // Sous-tâches
  root.querySelectorAll('.sub-item').forEach(el=>{
    el.onclick=()=>openDetail(Number(el.dataset.sous));
  });
  const sousAdd=root.querySelector('#sous-add'),sousNew=root.querySelector('#sous-new');
  if(sousAdd){
    const envoyer=async()=>{
      const v=(sousNew.value||'').trim();
      if(!v)return;
      try{
        await jpost('/api/taches',{titre:v,parent_id:t.id,statut:'a_faire',module:t.module,type:t.type});
        sousNew.value='';
        await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes(),openDetail(t.id,{silent:true})]);
        requestAnimationFrame(()=>{const n=document.getElementById('sous-new');if(n)n.focus();});
      }catch(e){toast(e.message,'err');}
    };
    sousAdd.onclick=envoyer;
    sousNew.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();envoyer();}});
  }

  // Archiver / supprimer
  const arch=root.querySelector('#d-archive');
  if(arch)arch.onclick=async()=>{
    try{
      const j=await jpost('/api/taches/'+t.id+'/archive',{});
      toast(j.archivee?'Tâche archivée.':'Tâche désarchivée.');
      closeDetail();
      await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
    }catch(e){toast(e.message,'err');}
  };
  const del=root.querySelector('#d-delete');
  if(del)del.onclick=()=>{
    confirmer('Supprimer la tâche « '+t.titre+' » ?','Ses sous-tâches, commentaires et fichiers seront également retirés.',async()=>{
      try{
        await api('/api/taches/'+t.id,{method:'DELETE'});
        toast('Tâche supprimée.');
        closeDetail();
        await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
      }catch(e){toast(e.message,'err');}
    });
  };

  // Commentaires
  const send=root.querySelector('#cmt-send'),area=root.querySelector('#cmt-new');
  if(send){
    const envoyer=async()=>{
      const v=(area.value||'').trim();
      if(!v)return;
      send.disabled=true;
      try{
        await jpost('/api/taches/'+t.id+'/commentaires',{message:v});
        area.value='';
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
      finally{send.disabled=false;}
    };
    send.onclick=envoyer;
    area.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();envoyer();}});
  }
  root.querySelectorAll('.cmt-del').forEach(b=>{
    b.onclick=()=>confirmer('Supprimer ce commentaire ?','',async()=>{
      try{
        await api('/api/taches/commentaires/'+b.dataset.cmt,{method:'DELETE'});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
    });
  });

  // Fichiers
  const drop=root.querySelector('#fic-drop'),input=root.querySelector('#fic-input');
  if(drop){
    drop.onclick=()=>input.click();
    input.onchange=()=>{if(input.files&&input.files[0])televerser(input.files[0]);};
    ['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over');}));
    ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over');}));
    drop.addEventListener('drop',e=>{
      const f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];
      if(f)televerser(f);
    });
  }
  async function televerser(file){
    const fd=new FormData();fd.append('fichier',file);
    try{
      const r=await fetch('/api/taches/'+t.id+'/fichiers',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch(e){}throw new Error(m);}
      toast('Fichier ajouté.');
      await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
    }catch(e){toast(e.message,'err');}
  }
  root.querySelectorAll('[data-preview]').forEach(b=>{
    b.onclick=()=>{
      const id=b.dataset.preview,nom=b.dataset.nom||'';
      window.open('/api/taches/fichiers/'+id+'/download?inline=1','_blank','noopener');
    };
  });
  root.querySelectorAll('[data-fic-del]').forEach(b=>{
    b.onclick=()=>confirmer('Retirer ce fichier ?','',async()=>{
      try{
        await api('/api/taches/fichiers/'+b.dataset.ficDel,{method:'DELETE'});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
    });
  });
}

// ══════════════════════════════════════════════════════════════════
// Modales
// ══════════════════════════════════════════════════════════════════
function fermerModal(){document.getElementById('modal-root').innerHTML='';}

function confirmer(titre,detail,onOui){
  const root=document.getElementById('modal-root');
  root.innerHTML='<div class="modal-back"><div class="modal" style="max-width:420px">'+
    '<h3>'+esc(titre)+'</h3>'+
    (detail?'<p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0 0 4px">'+esc(detail)+'</p>':'')+
    '<div class="modal-actions"><button type="button" class="btn ghost" id="cf-non">Annuler</button>'+
    '<button type="button" class="btn danger" id="cf-oui">Confirmer</button></div>'+
  '</div></div>';
  root.querySelector('#cf-non').onclick=fermerModal;
  root.querySelector('#cf-oui').onclick=()=>{fermerModal();onOui();};
  root.querySelector('.modal-back').onclick=e=>{if(e.target===root.querySelector('.modal-back'))fermerModal();};
}

function openTacheModal(_ignored,defauts){
  defauts=defauts||{};
  const root=document.getElementById('modal-root');
  const optList=(items,val,vide)=>(vide?'<option value="">'+esc(vide)+'</option>':'')+
    items.map(i=>'<option value="'+esc(i.code)+'"'+(String(val||'')===String(i.code)?' selected':'')+'>'+esc(i.label)+'</option>').join('');
  const statutDefaut=defauts.statut||(S.meta.statuts[0]&&S.meta.statuts[0].code)||'backlog';

  root.innerHTML='<div class="modal-back"><div class="modal">'+
    '<h3>Nouvelle tâche</h3>'+
    '<form id="tache-form">'+
      '<div class="fgrid">'+
        '<div class="field full"><label>Titre</label><input type="text" id="n-titre" required maxlength="300" placeholder="Ex. Corriger le tri des OF dans le planning"></div>'+
        '<div class="field full"><label>Description</label><textarea id="n-description" placeholder="Contexte, comportement attendu, critères d’acceptation…"></textarea></div>'+
        '<div class="field"><label>Statut</label><select id="n-statut">'+optList(S.meta.statuts,statutDefaut)+'</select></div>'+
        '<div class="field"><label>Priorité</label><select id="n-priorite">'+optList(S.meta.priorites,'normale')+'</select></div>'+
        '<div class="field"><label>Type</label><select id="n-type">'+optList(S.meta.types,'evolution')+'</select></div>'+
        '<div class="field"><label>Module</label><select id="n-module">'+optList(S.meta.modules,'','Aucun')+'</select></div>'+
        (TOUS_SERVICES
          ? '<div class="field"><label>Service</label><select id="n-service">'+optList(S.meta.services,(S.meta.moi&&S.meta.moi.service)||'')+'</select></div>'
          : '')+
        '<div class="field"><label>Échéance</label><input type="date" id="n-echeance"></div>'+
        '<div class="field full asg-field"><label>Assigné à</label><div id="n-assignes"></div></div>'+
        '<div class="field"><label>Estimation (h)</label><input type="number" step="0.25" min="0" id="n-estimation" placeholder="ex. 3"></div>'+
      '</div>'+
      '<div class="modal-actions">'+
        '<button type="button" class="btn ghost" id="n-cancel">Annuler</button>'+
        '<button type="submit" class="btn">Créer la tâche</button>'+
      '</div>'+
    '</form>'+
  '</div></div>';

  let nouvAssignes=[];
  champAssignes('n-assignes',[],ids=>{nouvAssignes=ids;});
  root.querySelector('#n-cancel').onclick=fermerModal;
  root.querySelector('.modal-back').onclick=e=>{if(e.target===root.querySelector('.modal-back'))fermerModal();};
  requestAnimationFrame(()=>{const el=document.getElementById('n-titre');if(el)el.focus();});

  root.querySelector('#tache-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const g=id=>{const el=document.getElementById(id);return el?el.value:'';};
    const titre=(g('n-titre')||'').trim();
    if(!titre){toast('Titre obligatoire.','err');return;}
    const body={
      titre:titre,
      description:(g('n-description')||'').trim()||null,
      statut:g('n-statut'),priorite:g('n-priorite'),type:g('n-type'),
      module:g('n-module')||null,
      // Absent du formulaire hors niveau admin : le serveur retombe alors sur
      // le service de l'auteur.
      service:(TOUS_SERVICES?(g('n-service')||null):null),
      assignes:nouvAssignes.slice(),
      echeance:g('n-echeance')||null,
      estimation_h:g('n-estimation')?Number(g('n-estimation')):null,
    };
    try{
      const j=await jpost('/api/taches',body);
      fermerModal();
      toast('Tâche créée.');
      await Promise.all([chargerTaches(),chargerStats(),chargerBadgeMes()]);
      openDetail(j.id);
    }catch(err){toast(err.message,'err');}
  });
}

// ══════════════════════════════════════════════════════════════════
// Filtres
// ══════════════════════════════════════════════════════════════════
let _debounce=null;
function brancherFiltres(){
  const q=document.getElementById('f-q');
  q.addEventListener('input',()=>{
    S.filtres.q=q.value.trim();
    clearTimeout(_debounce);
    _debounce=setTimeout(chargerTaches,220);
  });
  q.addEventListener('keydown',e=>{
    if(e.key==='Escape'){q.value='';S.filtres.q='';chargerTaches();}
  });
  [['f-assigne','assigne'],['f-priorite','priorite'],['f-type','type'],
   ['f-module','module'],['f-service','service']].forEach(([id,champ])=>{
    const el=document.getElementById(id);
    if(!el)return;
    el.addEventListener('change',()=>{
      S.filtres[champ]=el.value;
      el.classList.toggle('on',!!el.value);
      chargerTaches();
    });
  });
}
// ── Bascule « Mes tâches » ─────────────────────────────────────────────
// Remplace l'ancien onglet du même nom : un filtre qui vaut pour le Kanban, la
// Liste et les Archives, au lieu d'une vue à part.
function syncMoi(){
  const b=document.getElementById('btn-moi');
  if(!b)return;
  b.classList.toggle('on',!!S.filtres.moi);
  b.setAttribute('aria-pressed',S.filtres.moi?'true':'false');
  // La liste déroulante des personnes n'a pas de sens quand on est déjà filtré
  // sur soi : on la masque plutôt que de laisser deux filtres se contredire.
  const fa=document.getElementById('f-assigne');
  if(fa)fa.style.display=S.filtres.moi?'none':'';
}
function brancherMoi(){
  const b=document.getElementById('btn-moi');
  if(!b)return;
  try{if(localStorage.getItem('mysifa_taches_moi')==='1')S.filtres.moi=true;}catch(e){}
  b.onclick=()=>{
    S.filtres.moi=!S.filtres.moi;
    try{localStorage.setItem('mysifa_taches_moi',S.filtres.moi?'1':'0');}catch(e){}
    syncMoi();
    chargerTaches();
  };
  syncMoi();
}

function brancherSousTaches(){
  const b=document.getElementById('btn-sous');
  if(!b)return;
  const sync=()=>{
    b.textContent=S.sousTaches?'Sous-tâches affichées':'Sous-tâches masquées';
    b.classList.toggle('ghost',S.sousTaches);
  };
  b.onclick=()=>{
    S.sousTaches=!S.sousTaches;
    try{localStorage.setItem('mysifa_taches_sous',S.sousTaches?'1':'0');}catch(e){}
    sync();render();
  };
  try{if(localStorage.getItem('mysifa_taches_sous')==='0')S.sousTaches=false;}catch(e){}
  try{
    const brut=localStorage.getItem('mysifa_taches_ouverts');
    if(brut)S.ouverts=new Set(JSON.parse(brut).map(Number));
  }catch(e){}
  sync();
}

function resetFiltres(){
  S.filtres={q:'',assigne:'',priorite:'',type:'',module:'',service:'',rapide:'',moi:false};
  ['f-q','f-assigne','f-priorite','f-type','f-module','f-service'].forEach(id=>{
    const el=document.getElementById(id);if(el){el.value='';el.classList.remove('on');}
  });
  try{localStorage.setItem('mysifa_taches_moi','0');}catch(e){}
  syncMoi();
  renderStats();
  chargerTaches();
}

// ══════════════════════════════════════════════════════════════════
// Raccourcis clavier
// ══════════════════════════════════════════════════════════════════
function cartesVisibles(){
  return [...document.querySelectorAll('#board .tcard')].map(c=>Number(c.dataset.id));
}
function marquerActif(id,opts){
  if(S.actif===id)return;
  S.actif=id;
  document.querySelectorAll('#board .tcard.actif').forEach(c=>c.classList.remove('actif'));
  const el=document.querySelector('#board .tcard[data-id="'+id+'"]');
  if(el){
    el.classList.add('actif');
    if(!opts||opts.scroll!==false)el.scrollIntoView({block:'nearest',behavior:'smooth'});
  }
}
function deplacerActif(pas){
  const ids=cartesVisibles();
  if(!ids.length)return;
  const i=ids.indexOf(S.actif);
  const suivant=(i===-1)?(pas>0?0:ids.length-1):Math.min(ids.length-1,Math.max(0,i+pas));
  marquerActif(ids[suivant]);
}

// Une frappe ne doit jamais agir « dans le dos » de l'utilisateur : on ne prend
// la main ni dans un champ de saisie, ni quand une fiche ou une modale est
// ouverte — le tiroir a ses propres champs et son propre Échap.
function saisieEnCours(e){
  const el=e.target;
  if(!el)return false;
  const tag=(el.tagName||'').toLowerCase();
  return tag==='input'||tag==='textarea'||tag==='select'||el.isContentEditable;
}
function surcoucheOuverte(){
  return !!(document.getElementById('modal-root').firstElementChild
    || document.getElementById('drawer-root').firstElementChild
    || document.querySelector('.mguide-ov')
    || document.getElementById('mtq-root'));
}

document.addEventListener('keydown',e=>{
  if(e.ctrlKey||e.metaKey||e.altKey)return;
  if(saisieEnCours(e)||surcoucheOuverte())return;

  if(e.key==='n'||e.key==='N'){e.preventDefault();openTacheModal();return;}
  if(e.key==='/'){
    e.preventDefault();
    const q=document.getElementById('f-q');
    if(q){q.focus();q.select();}
    return;
  }
  if(e.key==='Escape'){
    if(S.actif!==null){
      S.actif=null;
      document.querySelectorAll('#board .tcard.actif').forEach(c=>c.classList.remove('actif'));
    }
    return;
  }
  if(!estBoard(S.view))return;   // J/K et 1–5 n'ont de sens que sur un board

  if(e.key==='j'||e.key==='J'){e.preventDefault();deplacerActif(1);return;}
  if(e.key==='k'||e.key==='K'){e.preventDefault();deplacerActif(-1);return;}
  if(e.key==='Enter'&&S.actif!==null){e.preventDefault();openDetail(S.actif);return;}

  // 1 à 5 → colonnes du référentiel, dans l'ordre affiché.
  if(/^[1-9]$/.test(e.key)){
    const statuts=(S.meta&&S.meta.statuts)||[];
    const st=statuts[Number(e.key)-1];
    if(!st||S.actif===null)return;
    e.preventDefault();
    const t=S.taches.find(x=>x.id===S.actif);
    if(!t||t.statut===st.code)return;
    deplacer(S.actif,st.code,null,null);
    toast('→ '+st.label);
  }
},true);

// ══════════════════════════════════════════════════════════════════
// Guides in-app (moteur partagé mysifa_guides.js)
// ══════════════════════════════════════════════════════════════════
const TACHES_GUIDES = {
  'taches-kanban': { steps: [
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="6" height="18" rx="1"/><rect x="10" y="3" width="6" height="12" rx="1"/><rect x="17" y="3" width="4" height="8" rx="1"/></svg>',
      title: 'Gestionnaire de tâches',
      body: '<p>Cette application suit <strong>ce que vous demandez à l’équipe de développement</strong> : une tâche par demande, de son arrivée en <span class="mguide-tag">Boîte à idées</span> jusqu’à <span class="mguide-tag">Terminé</span>. Elle est réservée au super administrateur.</p>',
      extra: '<div class="mguide-tasks"><div class="mguide-svc"><div class="mguide-svc-hd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>Ce que vous avez à faire ici</div><ul class="mguide-svc-list"><li>Créer une tâche pour chaque demande, avec le contexte nécessaire.</li><li>Assigner la tâche à un développeur et poser une échéance.</li><li>Suivre l’avancement colonne par colonne, sans réunion.</li><li>Joindre les fichiers de contexte et commenter au fil de l’eau.</li></ul></div></div>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 9l-3 3 3 3"/><path d="M9 5l3-3 3 3"/><path d="M15 19l-3 3-3-3"/><path d="M19 9l3 3-3 3"/></svg>',
      title: 'Déplacer une tâche',
      body: '<p>Chaque colonne est un statut. <strong>Glissez une carte</strong> d’une colonne à l’autre pour la faire avancer — le statut, la date de démarrage et la date de clôture se mettent à jour seuls. À l’intérieur d’une colonne, la position que vous donnez à la carte est conservée.</p><p>Une carte déposée sur la zone <span class="mguide-tag">Archiver</span>, en bas à gauche, sort du board sans rien perdre : elle reste consultable dans l’onglet <span class="mguide-hl">Archives</span> avec son historique.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="8" y="10" width="100" height="140" rx="10" fill="var(--card)" stroke="var(--border)"/><rect x="120" y="10" width="100" height="140" rx="10" fill="var(--card)" stroke="var(--accent)"/><rect x="232" y="10" width="100" height="140" rx="10" fill="var(--card)" stroke="var(--border)"/><text x="20" y="28" font-size="9" fill="var(--muted)" font-weight="700">À FAIRE</text><text x="132" y="28" font-size="9" fill="var(--accent)" font-weight="700">EN COURS</text><text x="244" y="28" font-size="9" fill="var(--muted)" font-weight="700">TERMINÉ</text><rect x="16" y="38" width="84" height="34" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="24" y="52" font-size="8" fill="var(--text2)">Tri des OF</text><rect x="24" y="58" width="30" height="7" rx="3" fill="var(--warn)" opacity=".5"/><rect x="128" y="38" width="84" height="34" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="4 3"/><text x="136" y="52" font-size="8" fill="var(--accent)" font-weight="700">Export PDF</text><rect x="136" y="58" width="42" height="7" rx="3" fill="var(--accent)" opacity=".6"/><path d="M104 55 L124 55" stroke="var(--accent)" stroke-width="2" marker-end="url(#a)"/><defs><marker id="a" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6z" fill="var(--accent)"/></marker></defs><rect x="240" y="38" width="84" height="34" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="248" y="52" font-size="8" fill="var(--muted)">Badge stock</text><rect x="248" y="58" width="26" height="7" rx="3" fill="var(--ok)" opacity=".5"/></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/></svg>',
      title: 'Lire une carte',
      body: '<p>La carte est volontairement <strong>dépouillée</strong> : les assignés en haut, le titre en dessous. Le <strong>liseré de gauche</strong> donne la priorité — rouge critique, orange haute, cyan normale, gris basse — et un <span class="mguide-hl">point rouge</span> en haut à droite signale une échéance dépassée.</p><p>Le type, le module, la date et les compteurs ne sont plus affichés pour garder des colonnes étroites : ils apparaissent <strong>au survol de la carte</strong>, et en entier dans la fiche ou la vue Liste. Une sous-tâche n’est jamais une carte isolée : elle vit sous sa tâche mère, que le bouton <span class="mguide-tag">› N</span> déplie et replie.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="24" y="26" width="136" height="76" rx="9" fill="var(--bg)" stroke="var(--border)"/><rect x="24" y="26" width="4" height="76" rx="2" fill="var(--danger)"/><text x="34" y="20" font-size="8" fill="var(--danger)">priorité</text><circle cx="46" cy="44" r="8" fill="var(--accent-bg)"/><text x="46" y="47" font-size="7" fill="var(--accent)" text-anchor="middle" font-weight="800">EL</text><circle cx="58" cy="44" r="8" fill="var(--accent-bg)" stroke="var(--bg)" stroke-width="1.6"/><text x="58" y="47" font-size="7" fill="var(--accent)" text-anchor="middle" font-weight="800">LG</text><circle cx="146" cy="44" r="3.5" fill="var(--danger)"/><circle cx="146" cy="44" r="7" fill="none" stroke="var(--danger)" stroke-opacity=".25" stroke-width="3"/><text x="166" y="40" font-size="8" fill="var(--danger)">retard</text><text x="38" y="72" font-size="10" fill="var(--text)" font-weight="700">Doublon entrée Z1</text><rect x="38" y="84" width="112" height="4" rx="2" fill="var(--border)"/><rect x="38" y="84" width="70" height="4" rx="2" fill="var(--accent)"/><path d="M162 88 L196 106" stroke="var(--muted)" stroke-width="1.4" stroke-dasharray="3 3"/><rect x="190" y="100" width="140" height="52" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="200" y="118" font-size="8.5" fill="var(--text2)" font-weight="700">Doublon entrée Z1</text><text x="200" y="132" font-size="8" fill="var(--muted)">Critique · Bug · MyStock</text><text x="200" y="145" font-size="8" fill="var(--muted)">Échéance 12 mars · 3 comm.</text><text x="200" y="94" font-size="8" fill="var(--muted)">au survol</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
      title: 'Le panneau de détail',
      body: '<p>Cliquez une carte pour ouvrir son panneau. Tout s’y modifie directement — <strong>chaque changement est enregistré immédiatement</strong>, il n’y a pas de bouton « Enregistrer ». Quatre onglets : <span class="mguide-tag">Détail</span> (champs, checklist, sous-tâches), <span class="mguide-tag">Commentaires</span>, <span class="mguide-tag">Fichiers</span> et <span class="mguide-tag">Activité</span>, qui trace qui a changé quoi.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="0" y="0" width="150" height="160" rx="0" fill="var(--bg)" opacity=".5"/><rect x="150" y="0" width="190" height="160" rx="0" fill="var(--card)" stroke="var(--border)"/><text x="164" y="24" font-size="11" fill="var(--text)" font-weight="700">Doublon à l’entrée Z1</text><rect x="164" y="34" width="42" height="14" rx="5" fill="var(--accent-bg)"/><text x="185" y="44" font-size="8" fill="var(--accent)" text-anchor="middle" font-weight="700">EN COURS</text><line x1="150" y1="58" x2="340" y2="58" stroke="var(--border)"/><text x="164" y="72" font-size="8" fill="var(--accent)" font-weight="700">Détail</text><line x1="162" y1="76" x2="192" y2="76" stroke="var(--accent)" stroke-width="2"/><text x="204" y="72" font-size="8" fill="var(--muted)">Commentaires</text><text x="272" y="72" font-size="8" fill="var(--muted)">Fichiers</text><rect x="164" y="88" width="80" height="20" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="170" y="101" font-size="8" fill="var(--text2)">Assigné</text><rect x="250" y="88" width="76" height="20" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="256" y="101" font-size="8" fill="var(--text2)">Échéance</text><rect x="164" y="116" width="162" height="30" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="170" y="130" font-size="8" fill="var(--muted)">Description, checklist,</text><text x="170" y="141" font-size="8" fill="var(--muted)">sous-tâches…</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M7 9h2M11 9h2M15 9h2M7 13h10"/></svg>',
      title: 'Créer une tâche sans quitter sa page',
      body: '<p>Partout dans MySifa, <span class="mguide-tag">Option</span> + <span class="mguide-tag">T</span> ouvre cette fenêtre : la page où vous êtes est <strong>capturée et jointe</strong> à la tâche, le module est déduit de l’écran courant, le type est réglé sur Évolution et la tâche vous est assignée. Vous n’avez qu’à écrire le titre.</p><p>Depuis la <strong>messagerie</strong>, le menu <span class="mguide-tag">⋮</span> d’un message propose <span class="mguide-hl">Créer une tâche</span> : le message devient la description, sans copier-coller.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="10" y="10" width="86" height="30" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="53" y="29" font-size="11" fill="var(--text2)" text-anchor="middle" font-weight="700">Option + T</text><path d="M100 25 L126 25" stroke="var(--accent)" stroke-width="2" marker-end="url(#fq)"/><defs><marker id="fq" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6z" fill="var(--accent)"/></marker></defs><rect x="132" y="8" width="198" height="144" rx="11" fill="var(--card)" stroke="var(--accent)"/><text x="144" y="28" font-size="11" fill="var(--text)" font-weight="800">Créer une tâche</text><text x="144" y="41" font-size="8" fill="var(--muted)">Depuis MyStock · /stock</text><rect x="144" y="50" width="174" height="18" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="150" y="62" font-size="8" fill="var(--muted)">Titre…</text><rect x="144" y="74" width="84" height="16" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="150" y="85" font-size="7" fill="var(--text2)">Évolution</text><rect x="234" y="74" width="84" height="16" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="240" y="85" font-size="7" fill="var(--text2)">MyStock</text><rect x="144" y="96" width="66" height="16" rx="8" fill="var(--accent-bg)" stroke="var(--accent)"/><circle cx="154" cy="104" r="5" fill="var(--accent)"/><text x="166" y="108" font-size="7" fill="var(--accent)" font-weight="700">moi</text><rect x="144" y="118" width="174" height="26" rx="6" fill="var(--bg)" stroke="var(--border)"/><rect x="150" y="122" width="28" height="18" rx="3" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="186" y="134" font-size="8" fill="var(--text2)">capture de la page jointe</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21.4 11.05 12.25 20.2a5.5 5.5 0 0 1-7.78-7.78l9.19-9.19a3.67 3.67 0 0 1 5.18 5.18l-9.2 9.19a1.83 1.83 0 0 1-2.59-2.59l8.49-8.48"/></svg>',
      title: 'Contexte et suivi du temps',
      body: '<p>Dans l’onglet <strong>Fichiers</strong>, glissez maquettes, exports ou captures : le développeur trouve tout au même endroit. Dans <strong>Détail</strong>, l’<span class="mguide-hl">estimation</span> se saisit une fois et le <span class="mguide-hl">temps passé</span> se cumule au fil des pointages — l’écart entre les deux se lit directement dans la vue Liste.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="20" y="14" width="300" height="52" rx="10" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="5 4"/><text x="170" y="38" font-size="10" fill="var(--accent)" text-anchor="middle" font-weight="700">Déposer un fichier de contexte</text><text x="170" y="54" font-size="8" fill="var(--accent)" text-anchor="middle" opacity=".8">ou cliquer pour choisir</text><rect x="20" y="78" width="300" height="30" rx="8" fill="var(--bg)" stroke="var(--border)"/><rect x="28" y="84" width="18" height="18" rx="5" fill="var(--accent-bg)"/><text x="56" y="96" font-size="9" fill="var(--text)">maquette-planning.png</text><text x="312" y="96" font-size="8" fill="var(--muted)" text-anchor="end">248 Ko</text><rect x="20" y="118" width="145" height="30" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="30" y="131" font-size="8" fill="var(--muted)">ESTIMATION</text><text x="30" y="143" font-size="10" fill="var(--text)" font-weight="700">4 h</text><rect x="175" y="118" width="145" height="30" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="185" y="131" font-size="8" fill="var(--muted)">TEMPS PASSÉ</text><text x="185" y="143" font-size="10" fill="var(--warn)" font-weight="700">6,5 h</text></svg>'
    }
  ]},

  'taches-liste': { steps: [
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
      title: 'Vue Liste',
      body: '<p>La liste montre les mêmes tâches que le Kanban, mais <strong>à plat et triables</strong>. Cliquez un en-tête de colonne pour trier — un second clic inverse le sens. Elle sert à répondre à « qu’est-ce qui traîne ? » plutôt qu’à « où en est-on ? ».</p>',
      extra: '<div class="mguide-tasks"><div class="mguide-svc"><div class="mguide-svc-hd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>Ce que vous avez à faire ici</div><ul class="mguide-svc-list"><li>Trier par échéance pour repérer les retards.</li><li>Comparer temps passé et estimation, tâche par tâche.</li><li>Filtrer sur une personne pour préparer un point d’équipe.</li></ul></div></div>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
      title: 'Filtrer et chercher',
      body: '<p>La barre de recherche filtre sur le <strong>titre et la description</strong>, dès le premier caractère ; <span class="mguide-tag">Échap</span> la vide. Les listes déroulantes cumulent les critères, et les compteurs du haut sont eux aussi cliquables : un clic sur <span class="mguide-hl">En retard</span> ne garde que les tâches en retard.</p><p>Le bouton <span class="mguide-tag">Mes tâches</span> ne garde que ce qui vous est assigné. C’est un filtre, pas un onglet : il vaut aussi bien sur le <strong>Kanban</strong> que sur la <strong>Liste</strong>, il se cumule avec les autres critères et il reste armé d’une visite à l’autre. <span class="mguide-tag">Réinitialiser</span> le relâche.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="14" y="14" width="70" height="26" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="24" y="31" font-size="9" fill="var(--text2)">Idées 4</text><rect x="90" y="14" width="74" height="26" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="100" y="31" font-size="9" fill="var(--text2)">En cours 3</text><rect x="170" y="14" width="80" height="26" rx="8" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="180" y="31" font-size="9" fill="var(--accent)" font-weight="700">En retard 2</text><rect x="14" y="52" width="180" height="28" rx="9" fill="var(--card)" stroke="var(--accent)"/><circle cx="30" cy="66" r="5" fill="none" stroke="var(--muted)" stroke-width="1.6"/><line x1="34" y1="70" x2="38" y2="74" stroke="var(--muted)" stroke-width="1.6"/><text x="46" y="70" font-size="9" fill="var(--text2)">export</text><rect x="202" y="52" width="60" height="28" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="212" y="70" font-size="9" fill="var(--muted)">Priorité</text><rect x="270" y="52" width="56" height="28" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="280" y="70" font-size="9" fill="var(--muted)">Module</text><rect x="14" y="92" width="312" height="22" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="24" y="107" font-size="9" fill="var(--text)">Export PDF des OF</text><text x="316" y="107" font-size="9" fill="var(--danger)" text-anchor="end" font-weight="700">retard 3 j</text><rect x="14" y="118" width="312" height="22" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="24" y="133" font-size="9" fill="var(--text)">Doublon à l’entrée Z1</text><text x="316" y="133" font-size="9" fill="var(--danger)" text-anchor="end" font-weight="700">retard 1 j</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5" rx="1"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
      title: 'Archiver plutôt que supprimer',
      body: '<p>Une tâche terminée qui encombre le board s’<strong>archive</strong> depuis son panneau de détail : elle disparaît du Kanban et de la liste, mais reste consultable dans <span class="mguide-tag">Archives</span> avec tout son historique. La suppression, elle, retire aussi les sous-tâches, commentaires et fichiers — réservez-la aux tâches créées par erreur.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="30" y="24" width="280" height="46" rx="10" fill="var(--bg)" stroke="var(--border)"/><rect x="42" y="38" width="94" height="18" rx="6" fill="var(--card)" stroke="var(--border)"/><text x="89" y="51" font-size="9" fill="var(--text2)" text-anchor="middle">Archiver</text><text x="152" y="51" font-size="9" fill="var(--muted)">conserve tout, masque la tâche</text><rect x="30" y="86" width="280" height="46" rx="10" fill="var(--bg)" stroke="var(--danger)" stroke-opacity=".5"/><rect x="42" y="100" width="94" height="18" rx="6" fill="rgba(248,113,113,.15)"/><text x="89" y="113" font-size="9" fill="var(--danger)" text-anchor="middle" font-weight="700">Supprimer</text><text x="152" y="113" font-size="9" fill="var(--muted)">retire sous-tâches et fichiers</text></svg>'
    }
  ]}
};

function syncGuideBtn(){
  const slot=document.getElementById('guide-btn-slot');
  if(!slot)return;
  const cle=(VIEW_META[S.view]||VIEW_META.kanban).guide;
  slot.innerHTML=(window.MySifaGuides&&typeof MySifaGuides.bookBtn==='function')?MySifaGuides.bookBtn(cle):'';
}

function initGuides(){
  try{
    if(!window.MySifaGuides)return;
    MySifaGuides.configure({role:USER_ROLE});
    MySifaGuides.registerMany(TACHES_GUIDES);
    MySifaGuides.boot().then(function(){
      syncGuideBtn();
      MySifaGuides.autoOpen((VIEW_META[S.view]||VIEW_META.kanban).guide);
    });
  }catch(e){}
}

// ══════════════════════════════════════════════════════════════════
// Boot
// ══════════════════════════════════════════════════════════════════
function updateUserChip(){
  if(!S.me)return;
  const chip=document.querySelector('.user-chip');
  if(chip&&window.MySifaUserChip){MySifaUserChip.fill(chip,S.me,{showProfil:false});return;}
  const n=document.getElementById('uc-name');if(n)n.textContent=S.me.nom||'—';
  const r=document.getElementById('uc-role');if(r)r.textContent=S.me.role||'—';
}

document.getElementById('btn-theme').onclick=()=>{
  if(window.MySifaTheme)MySifaTheme.toggleMode();
  syncThemeBtn();
};
document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

(async function init(){
  syncBandeauOffset();
  window.addEventListener('resize',syncBandeauOffset);
  syncThemeBtn();
  try{
    S.me=await api('/api/auth/me');
    if(S.me&&window.MySifaTheme)MySifaTheme.mergeFromUser(S.me);
    syncThemeBtn();
    updateUserChip();
  }catch(e){}
  try{
    S.meta=await api('/api/taches/meta');
    remplirFiltres();
  }catch(e){toast(e.message,'err');return;}
  brancherFiltres();
  brancherMoi();
  brancherSousTaches();
  brancherArchivage();
  showView(readView(),{silent:true});
  await chargerStats();
  await chargerBadgeMes();
  initGuides();
})();
window.addEventListener('hashchange',function(){try{showView(readView(),{silent:true});}catch(e){}});
</script>
<script src="/static/mysifa_cal_rappel.js?v=5"></script>
</body>
</html>
"""
