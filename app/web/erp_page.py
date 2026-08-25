"""MySifa — ERP (page).

Route : /erp — direction, services administration et super administrateur
(`ROLES_ADMIN`).

Lecture du miroir RVGI (`data/erp_mirror.db`) dans les codes de MySifa :
sidebar invariable, filtres persistants à gauche, grille dense, et une modale
de détail qui porte les « pièces liées » — de la commande vers ses BL, ses
factures, ses mouvements — pour explorer comme dans l'ERP. Aucune action
d'écriture : l'ERP reste la source, cet écran regarde.

Le catalogue d'écrans vit dans `app/services/erp_catalogue.py` : ajouter un
écran ne demande pas de toucher à cette page.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLES_ADMIN
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/erp", response_class=HTMLResponse)
def erp_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/erp", status_code=302)
        raise
    if user.get("role") not in ROLES_ADMIN:
        from app.web.access_denied import access_denied_response
        return access_denied_response(
            "ERP",
            detail=(
                "Cette application est réservée à la direction, aux services "
                "administration et au super administrateur."
            ),
        )
    html = (
        ERP_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__USER_ROLE__", str(user.get("role") or ""))
    )
    return HTMLResponse(content=html)


ERP_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>ERP — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_mobile_topbar.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--success:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--success:#059669;--danger:#dc2626;--warn:#d97706}
*{box-sizing:border-box}
/* La page ne défile pas : elle occupe l'écran, et c'est la grille qui roule
   sous son en-tête. Le bandeau de v1 ajoute 24 px de padding en haut du body —
   `height:100vh` avec `border-box` en tient compte tout seul. */
html{height:100%}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column}

/* ── Shell ── */
.layout{display:flex;flex:1;min-height:0}
/* Tiroir : la sidebar ne mange plus 230 px en permanence. Elle s'ouvre par le
   bouton Menu, se referme dès qu'on choisit un écran. La grille récupère la
   largeur, c'est elle qui en a besoin. */
.sidebar{width:min(1080px,94vw);background:var(--card);border-right:1px solid var(--border);padding:17px 21px 0;display:flex;flex-direction:column;flex-shrink:0;position:fixed;top:0;bottom:0;left:0;z-index:70;overflow-y:auto;scrollbar-width:none;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 0 48px rgba(0,0,0,.4)}
/* Le tiroir montre le menu general en entier : on va de n'importe quel ecran
   a n'importe quel autre sans repasser par l'accueil. */
.nav-colonnes{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:4px 24px;align-items:start;margin-top:6px}
.nav-bloc{min-width:0;break-inside:avoid}
.nav-bloc.parametres{grid-column:1/-1;margin-top:6px;padding-top:10px;border-top:1px solid var(--border)}
.nav-bloc.parametres .nav-domaine{border-left:none;margin:0 0 6px;padding-left:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:2px 10px}
.nav-bloc.parametres .nav-btn{border-radius:8px;padding-left:11px}
.nav-bloc.parametres .nav-btn:hover{padding-left:13px}
.nav-bloc.parametres .nav-btn.active::before{display:none}
body.sb-open .sidebar{transform:translateX(0)}
.sidebar::-webkit-scrollbar{width:0}
/* L'en-tete du tiroir se cale sur celui de la page : la croix occupe la place
   exacte du bouton « Menu », donc ouvrir puis refermer se fait sans deplacer
   la souris. Meme hauteur de bouton, meme retrait a gauche. */
.sb-entete{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.logo{display:flex;align-items:center;gap:11px;padding:5px 9px;border-radius:9px;cursor:pointer;transition:background .15s,color .15s}
.logo:hover{background:var(--accent-bg)}
.logo:hover .logo-brand{color:var(--accent)}
.logo-brand{font-size:15px;font-weight:800;transition:color .15s}.logo-brand span{color:var(--accent)}

/* Ouvrir le tiroir par erreur ne doit pas couter un detour : la croix est la
   ou l'oeil arrive, a gauche de la marque. */
.sb-fermer{flex-shrink:0;width:36px;height:36px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text2);display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:background .15s,color .15s,border-color .15s}
.sb-fermer:hover{background:var(--danger);border-color:var(--danger);color:#fff}
.rvgi-mark{display:inline-flex;align-items:center;flex-shrink:0}
.rvgi-mark img{width:46px;height:auto;display:block}
.rvgi-mark .rvgi-clair{display:none}
body.light .rvgi-mark .rvgi-sombre{display:none}
body.light .rvgi-mark .rvgi-clair{display:block}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
/* Le tiroir reprend la lecture verticale du menu : chaque domaine est une
   colonne, tenue par un filet, et l'écran courant marque ce filet d'un trait
   plein. On suit la colonne des yeux au lieu de lire une liste plate. */
.nav-groupe{font-size:13px;font-weight:800;letter-spacing:.2px;color:var(--text);padding:14px 4px 8px;display:flex;align-items:center;gap:8px}
.nav-groupe::before{content:'';width:3px;height:14px;border-radius:2px;background:var(--accent);flex-shrink:0}
.nav-domaine{display:flex;flex-direction:column;margin:0 0 10px 9px;padding-left:12px;border-left:1px solid var(--border)}
.nav-btn{position:relative;display:flex;align-items:center;gap:9px;width:100%;text-align:left;padding:7px 11px;border-radius:0 8px 8px 0;border:none;background:transparent;color:var(--text2);font-size:12.5px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,padding-left .12s;margin-bottom:1px}
.nav-btn:hover{background:var(--accent-bg);color:var(--accent);padding-left:14px}
.nav-btn.active{background:var(--accent-bg);color:var(--accent);font-weight:600}
/* Le trait vient se poser exactement sur le filet de la colonne. */
.nav-btn.active::before{content:'';position:absolute;left:-13px;top:5px;bottom:5px;width:2px;border-radius:2px;background:var(--accent)}
/* « Menu » n'appartient à aucun domaine : il garde la forme pleine. */
#nav-menu{border-radius:8px;padding:9px 12px;font-weight:600}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
/* Pied identique a celui de MyStock et MyProd : meme ordre, memes classes,
   meme chip utilisateur partage (mysifa_user_chip.js). Un pied qui differe
   d'une app a l'autre oblige a rechercher la deconnexion a chaque fois. */
.sidebar-bottom{margin-top:auto;margin-left:-20px;margin-right:-20px;padding:12px 16px;border-top:1px solid var(--border);background:var(--card);display:flex;flex-direction:column;gap:6px;flex-shrink:0;position:sticky;bottom:0}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip:hover{background:rgba(34,211,238,.18)}
.user-chip .uc-top{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.user-chip .uc-avatar{width:36px;height:36px;min-width:36px;border-radius:50%;object-fit:cover;border:1px solid var(--border);flex-shrink:0;display:block}
.user-chip .uc-info{flex:1;min-width:0}
.user-chip .uc-name,.uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role,.uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.user-chip .uc-profil{font-size:10px;color:var(--accent);margin-top:3px;display:flex;align-items:center;gap:4px}
.support-btn,.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;width:100%;transition:background .15s,color .15s,border-color .15s}
.support-btn:hover,.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.support-ico{display:inline-flex;align-items:center}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;color:var(--muted);padding:4px 12px}

.main{flex:1;min-width:0;min-height:0;display:flex;flex-direction:column}
.page-head{flex-shrink:0;padding:18px 22px 12px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:14px;flex-wrap:wrap;background:var(--bg)}
.btn-menu{flex-shrink:0;display:inline-flex;align-items:center;gap:8px;border:1px solid var(--border);background:var(--card);color:var(--text2);border-radius:10px;padding:9px 13px;font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;transition:background .15s,color .15s,border-color .15s}
.btn-menu:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
@media (max-width:900px){.btn-menu{display:none}}
.page-head h1{margin:0;font-size:19px;font-weight:700}
.head-titre-ligne{display:flex;align-items:center;gap:10px}
.page-head .sous{font-size:12px;color:var(--muted);margin-top:4px;max-width:640px}
.head-droite{margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.head-mark{display:inline-flex;align-items:center;flex-shrink:0}
.head-mark img{width:46px;height:auto;display:block}
/* Les mêmes actions que dans le tiroir, mais toujours sous la main : le tiroir
   sert à naviguer entre les écrans, pas à se déconnecter. */
.head-actions{display:flex;align-items:center;gap:6px;padding-left:10px;margin-left:4px;border-left:1px solid var(--border)}
.head-btn{width:34px;height:34px;border-radius:9px;border:1px solid var(--border);background:var(--card);color:var(--text2);display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:background .15s,color .15s,border-color .15s;flex-shrink:0}
.head-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.head-btn.danger:hover{background:var(--danger);border-color:var(--danger);color:#fff}
@media (max-width:900px){.head-actions{display:none}}
.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;font-size:11px;font-weight:600;background:var(--bg);border:1px solid var(--border);color:var(--text2)}
.pill.lecture{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.pill.vieux{background:rgba(251,191,36,.14);border-color:var(--warn);color:var(--warn)}

/* ── Menu (accueil du module) ── */
.menu-wrap{padding:22px 26px 40px;overflow:auto}
/* Un domaine = une colonne. L'écran est large, la lecture est verticale :
   on compare des natures d'objet côte à côte au lieu de dérouler cinq bandes. */
.colonnes{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;align-items:start}
.colonne{min-width:0}
/* Les paramètres ne sont pas une étape du process : ils passent sous les
   colonnes, sur toute la largeur, en lignes qui se replient. */
.colonne.parametres{grid-column:1/-1;margin-top:10px;padding-top:16px;border-top:1px solid var(--border)}
.colonne.parametres .cartes{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.domaine-titre{font-size:14px;font-weight:800;letter-spacing:.3px;color:var(--text);margin:0 0 12px;padding-bottom:9px;border-bottom:2px solid var(--accent)}
.cartes{display:flex;flex-direction:column;gap:10px}
.carte{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;cursor:pointer;transition:border-color .15s,transform .12s;display:flex;align-items:center;gap:12px}
.carte:hover{border-color:var(--accent);transform:translateY(-1px)}
.carte-ico{width:36px;height:36px;border-radius:10px;background:var(--accent-bg);color:var(--accent);display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
.carte-titre{font-size:13.5px;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}


/* ── Écran : rail + grille ── */
.ecran{display:flex;flex:1;min-height:0;overflow:hidden}
.rail{width:236px;flex-shrink:0;border-right:1px solid var(--border);padding:16px 14px;overflow-y:auto;background:var(--card);height:100%}
.rail-titre{font-size:11px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;color:var(--text);margin:0 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.champ{margin-bottom:12px}
.champ label{display:block;font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:var(--text2);margin-bottom:5px}
.champ input,.champ select{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;transition:border-color .15s}
.champ input::placeholder{color:var(--muted);opacity:.75}
.champ input:focus,.champ select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.btn{border-radius:10px;padding:9px 14px;font-weight:700;font-size:12px;font-family:inherit;cursor:pointer;border:1px solid var(--border);background:var(--bg);color:var(--text2);transition:filter .15s,background .15s,color .15s}
.btn:hover{background:var(--card);color:var(--text)}
.btn-accent{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.btn-accent:hover{filter:brightness(1.05)}
.rail-info{font-size:11px;color:var(--muted);line-height:1.6;border-top:1px solid var(--border);margin-top:14px;padding-top:12px}

.grille-zone{flex:1;min-width:0;min-height:0;display:flex;flex-direction:column}
.grille-scroll{flex:1;overflow:auto;cursor:grab}
.grille-scroll.attrape{cursor:grabbing;user-select:none}
table.grille{border-collapse:separate;border-spacing:0;width:100%;font-size:12.5px}
table.grille th{position:sticky;top:0;z-index:2;background:var(--card);border-bottom:1px solid var(--border);padding:9px 10px;text-align:left;font-size:10.5px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:var(--muted);white-space:nowrap;cursor:pointer;user-select:none}
table.grille th:hover{color:var(--accent)}
table.grille th .fleche{color:var(--accent);margin-left:4px}
table.grille th.attrapee{opacity:.4}
table.grille th.cible{box-shadow:inset 3px 0 0 var(--accent)}
.th-boite{display:flex;align-items:center;gap:6px}
.th-poignee{cursor:grab;color:var(--muted);opacity:.45;flex-shrink:0}
.th-poignee:hover{opacity:1;color:var(--accent)}
.th-cadenas{border:none;background:transparent;padding:0;margin-left:auto;color:var(--muted);opacity:.35;cursor:pointer;display:inline-flex;flex-shrink:0}
.th-cadenas:hover{opacity:1;color:var(--accent)}
.th-cadenas.on{opacity:1;color:var(--accent)}
/* Colonnes épinglées : elles restent à gauche au défilement horizontal.
   Le décalage `left` est calculé après rendu, à la largeur réelle. */
table.grille th.epingle{z-index:4}
table.grille th.epingle,table.grille td.epingle{position:sticky;background:var(--card)}
table.grille td.epingle{z-index:1;background:var(--bg)}
table.grille tbody tr:hover td.epingle,table.grille tbody tr.sel td.epingle{background:var(--accent-bg)}
table.grille th.bord-epingle,table.grille td.bord-epingle{border-right:1px solid var(--accent)}
table.grille td{padding:7px 10px;border-bottom:1px solid var(--border);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:340px}
table.grille tbody tr{cursor:pointer}
table.grille tbody tr:hover td{background:var(--accent-bg)}
table.grille tbody tr.sel td{background:var(--accent-bg)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
td.of{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:var(--accent);font-weight:600}
td.vide{color:var(--muted)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:700;background:var(--accent-bg);color:var(--accent)}
.badge.n0{background:rgba(148,163,184,.16);color:var(--muted)}
.badge.n1{background:rgba(251,191,36,.16);color:var(--warn)}
.badge.n2{background:rgba(52,211,153,.16);color:var(--ok)}
.badge.n3{background:rgba(34,211,238,.14);color:var(--accent)}
.neg{color:var(--danger);font-weight:600}
.pied{display:flex;align-items:center;gap:12px;padding:10px 16px;border-top:1px solid var(--border);background:var(--card);font-size:12px;color:var(--muted)}
.pied .compte{font-variant-numeric:tabular-nums}
.pied .pager{margin-left:auto;display:flex;align-items:center;gap:6px}
.vide-msg{padding:40px 26px;color:var(--muted);font-size:13px}

/* ── Détail : une modale par-dessus la grille ── */
.detail-fond{position:fixed;inset:0;z-index:70;display:none;align-items:center;justify-content:center;padding:22px;
  background:rgba(2,6,23,.66)}
body.light .detail-fond{background:rgba(15,23,42,.5)}
.detail-fond.ouvert{display:flex}
.detail{width:min(1100px,94vw);max-height:88vh;display:flex;flex-direction:column;
  background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden;
  box-shadow:0 28px 80px rgba(0,0,0,.5);animation:mo .16s ease-out}
@keyframes mo{from{opacity:0;transform:translateY(10px) scale(.985)}to{opacity:1;transform:none}}
.detail-head{flex-shrink:0;background:var(--card);border-bottom:1px solid var(--border);padding:13px 16px;display:flex;align-items:center;gap:12px}
.detail-head .tt{min-width:0}
.detail-head h2{margin:0;font-size:16px;font-weight:800;letter-spacing:-.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.detail-head .st{margin:2px 0 0;font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.detail-retour{border:1px solid var(--border);background:var(--bg);color:var(--text2);border-radius:9px;
  padding:6px 11px;cursor:pointer;font-size:12px;font-weight:600;display:none;align-items:center;gap:6px;flex-shrink:0}
.detail-retour.on{display:inline-flex}
.detail-retour:hover{border-color:var(--accent);color:var(--accent)}
.detail-fermer{margin-left:auto;border:1px solid var(--border);background:var(--bg);color:var(--text2);border-radius:9px;
  width:30px;height:30px;cursor:pointer;font-size:17px;line-height:1;flex-shrink:0}
.detail-fermer:hover{background:var(--danger);border-color:var(--danger);color:#fff}
.detail-corps{overflow-y:auto;padding:15px 16px 20px;background:var(--bg);flex:1}
.sections{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;align-items:start}
.groupe{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.groupe.pleine{grid-column:1/-1}
.groupe-titre{padding:10px 14px;font-size:10.5px;font-weight:800;letter-spacing:.7px;text-transform:uppercase;color:var(--muted);
  cursor:pointer;display:flex;align-items:center;gap:8px;background:var(--bg)}
.groupe-titre:hover{color:var(--accent)}
.groupe-titre .chev{margin-left:auto;transition:transform .15s}
.groupe.replie .groupe-titre .chev{transform:rotate(-90deg)}
.groupe-corps{padding:6px 14px 10px}
/* Un entête de pièce porte trop de champs pour une colonne : on les étale. */
.groupe.champs-cols .groupe-corps{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:0 22px}
.groupe.replie .groupe-corps{display:none}
.ligne-champ{display:flex;gap:12px;padding:6px 0;font-size:12.5px;border-bottom:1px solid var(--border)}
.ligne-champ:last-child{border-bottom:none}
.ligne-champ .lab{color:var(--muted);flex:0 0 44%}
.ligne-champ .val{color:var(--text);word-break:break-word;font-weight:600;text-align:right;margin-left:auto}
.ligne-champ .val.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
.ligne-champ .val.num{font-variant-numeric:tabular-nums}
.ligne-champ .val.vide{color:var(--muted);font-weight:400}
.ligne-champ .val.of{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:var(--accent)}
.lien-row .c.of{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent);font-weight:600}
.lien-row .c.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px}

/* Pièces liées */
.liens{grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px;align-items:start}
.lien{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.lien-tete{display:flex;align-items:center;gap:8px;padding:9px 13px;background:var(--bg);border-bottom:1px solid var(--border)}
.lien-tete .nom{font-size:12px;font-weight:800;color:var(--text)}
.lien-tete .cle{font-size:10.5px;color:var(--muted);font-family:ui-monospace,Menlo,Consolas,monospace}
.lien-tete .cpt{margin-left:auto;display:inline-block;padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:800;background:var(--accent-bg);color:var(--accent)}
.lien-rows{display:flex;flex-direction:column}
.lien-row{display:flex;gap:10px;align-items:center;padding:7px 13px;font-size:12px;cursor:pointer;border-bottom:1px solid var(--border);color:var(--text2)}
.lien-row:last-child{border-bottom:none}
.lien-row:hover{background:var(--accent-bg);color:var(--text)}
.lien-row .c{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1 1 0;min-width:0}
.lien-row .c.num{text-align:right;font-variant-numeric:tabular-nums;flex:0 0 auto}
.lien-row .fl{flex:0 0 auto;color:var(--muted)}
.lien-plus{padding:8px 13px;font-size:11.5px;font-weight:700;color:var(--accent);cursor:pointer;background:var(--bg);text-align:center}
.lien-plus:hover{background:var(--accent-bg)}
.lien-err{padding:10px 13px;font-size:11.5px;color:var(--danger)}
.liens-vide{grid-column:1/-1;padding:14px;border:1px dashed var(--border);border-radius:12px;color:var(--muted);font-size:12px;text-align:center}
.titre-bloc{display:flex;align-items:center;gap:10px;margin:14px 0 8px;font-size:11px;font-weight:800;
  letter-spacing:.8px;text-transform:uppercase;color:var(--text2)}
.titre-bloc:first-child{margin-top:0}
.titre-bloc:after{content:"";flex:1;height:1px;background:var(--border);order:1}
.titre-bloc .tb-num{order:2;font-variant-numeric:tabular-nums;letter-spacing:0;
  background:var(--accent-bg);color:var(--accent);border-radius:999px;padding:2px 9px;font-size:11px}

/* Les lignes de la pièce : la même grille, en petit, dans la fiche. */
.pl-boite{border:1px solid var(--border);border-radius:12px;overflow:auto;background:var(--card);max-height:290px}
table.pl{width:100%;border-collapse:collapse;font-size:12px}
table.pl th{position:sticky;top:0;z-index:1;background:var(--bg);color:var(--muted);text-align:left;
  font-size:10px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;
  padding:8px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
table.pl th.num,table.pl td.num{text-align:right;font-variant-numeric:tabular-nums}
table.pl td{padding:7px 10px;border-bottom:1px solid var(--border);color:var(--text2);
  white-space:nowrap;max-width:280px;overflow:hidden;text-overflow:ellipsis}
table.pl tr:last-child td{border-bottom:none}
table.pl tbody tr{cursor:pointer}
table.pl tbody tr:hover td{background:var(--accent-bg);color:var(--text)}
table.pl tbody tr.ici td{background:var(--accent-bg);color:var(--text);font-weight:600;cursor:default}
table.pl tbody tr.ici td:first-child{box-shadow:inset 3px 0 0 var(--accent)}
table.pl td.vide{color:var(--muted)}
table.pl td.of{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent);font-weight:600}
table.pl td.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px}
.pl-note{margin:6px 2px 0;font-size:11.5px;color:var(--muted)}

/* Résumé de la ligne : l'article et les chiffres, lisibles de loin. */
.resume{display:flex;flex-wrap:wrap;align-items:center;gap:16px 26px;margin-bottom:12px;
  padding:14px 16px;border:1px solid var(--border);border-radius:12px;background:var(--card);
  border-left:3px solid var(--accent)}
.resume-quoi{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1 1 240px}
.resume-ref{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:19px;font-weight:700;
  color:var(--accent);letter-spacing:-.2px}
.resume-des{font-size:13px;color:var(--text2);line-height:1.35}
.resume-chiffres{display:flex;flex-wrap:wrap;gap:10px 28px;margin-left:auto}
.tuile{display:flex;flex-direction:column;gap:2px;text-align:right;min-width:88px}
.tuile .tl{font-size:10px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:var(--muted)}
.tuile .tv{font-size:19px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums;line-height:1.1}
.tuile .tv.neg{color:var(--danger)}
.tuile .tv.vide{color:var(--muted);font-weight:400}
@media (max-width:700px){
  .resume-chiffres{margin-left:0}
  .tuile{text-align:left}
}

/* Bandeau de provenance au-dessus de la grille */
.bandeau{display:none;align-items:center;gap:10px;padding:9px 14px;background:var(--accent-bg);
  border-bottom:1px solid var(--border);font-size:12px;color:var(--text2)}
.bandeau.on{display:flex}
.bandeau b{color:var(--accent)}
.bandeau .x{margin-left:auto;border:1px solid var(--border);background:var(--card);color:var(--text2);
  border-radius:8px;padding:3px 10px;font-size:11.5px;cursor:pointer;font-weight:600}
.bandeau .x:hover{border-color:var(--danger);color:var(--danger)}

/* ── Recherche globale ── */
.rg{position:relative;display:flex;align-items:center;gap:8px;margin-left:22px;
  background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:0 10px;
  height:36px;min-width:260px;max-width:420px;flex:1 1 300px}
.rg:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.rg-ico{color:var(--muted);flex-shrink:0}
.rg input{flex:1;min-width:0;background:none;border:none;outline:none;color:var(--text);
  font:inherit;font-size:13px;padding:0}
.rg input::placeholder{color:var(--muted)}
.rg input::-webkit-search-cancel-button{filter:grayscale(1) opacity(.6)}
.rg-kbd{flex-shrink:0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;
  color:var(--muted);border:1px solid var(--border);border-radius:5px;padding:2px 5px;background:var(--card)}
.rg:focus-within .rg-kbd{display:none}

.rg-fond{position:fixed;inset:0;z-index:75;display:none;background:rgba(2,6,23,.5);
  padding:76px 22px 22px;justify-content:center;align-items:flex-start}
body.light .rg-fond{background:rgba(15,23,42,.4)}
.rg-fond.ouvert{display:flex}
.rg-panneau{width:min(1000px,96vw);max-height:calc(100vh - 110px);overflow-y:auto;
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  box-shadow:0 24px 70px rgba(0,0,0,.5);padding:8px 0 10px}
.rg-tete{display:flex;align-items:baseline;gap:10px;padding:8px 16px 10px;
  border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--card);z-index:1}
.rg-tete b{font-family:inherit;font-size:13px}
.rg-tete .cpt{margin-left:auto;font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.rg-groupe{padding:4px 0 2px}
.rg-groupe-tete{display:flex;align-items:center;gap:8px;padding:9px 16px 6px;
  font-family:Archivo,inherit;font-size:10.5px;font-weight:800;letter-spacing:.7px;
  text-transform:uppercase;color:var(--muted)}
.rg-groupe-tete .n{margin-left:auto;background:var(--accent-bg);color:var(--accent);
  border-radius:999px;padding:1px 8px;font-size:10.5px;text-transform:none;letter-spacing:0}
.rg-ligne{display:flex;gap:12px;align-items:center;padding:7px 16px;font-size:12.5px;
  color:var(--text2);cursor:pointer;border-left:2px solid transparent}
.rg-ligne:hover,.rg-ligne.vise{background:var(--accent-bg);color:var(--text);border-left-color:var(--accent)}
.rg-ligne .c{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1 1 0;min-width:0}
.rg-ligne .c.num{text-align:right;flex:0 0 auto;font-variant-numeric:tabular-nums}
.rg-ligne .c.of{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent);font-weight:600}
.rg-ligne .c.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
.rg-ligne mark{background:var(--accent-bg);color:var(--accent);border-radius:3px;padding:0 2px}
.rg-plus{padding:5px 16px 8px;font-size:11.5px;color:var(--accent);cursor:pointer;font-weight:600}
.rg-plus:hover{text-decoration:underline}
.rg-msg{padding:26px 18px;text-align:center;color:var(--muted);font-size:13px}
.rg-note{padding:8px 16px 2px;font-size:11.5px;color:var(--warn)}
@media (max-width:900px){.rg{display:none}}

/* ── Divers ── */
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:11px 18px;font-size:13px;z-index:80;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.toast.err{border-left-color:var(--danger)}
.skel{height:12px;border-radius:6px;background:linear-gradient(90deg,var(--border),var(--card),var(--border));background-size:200% 100%;animation:sk 1.2s linear infinite}
@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:40}
body.sb-open .sidebar-overlay{display:block}
@media (max-width:900px){
  .ecran{flex-direction:column}
  .rail{width:auto;border-right:none;border-bottom:1px solid var(--border)}
  .detail-fond{padding:0}
  .detail{width:100%;max-height:100vh;height:100vh;border-radius:0;border:none}
  .sections{grid-template-columns:1fr}
  .liens{grid-template-columns:1fr}
}
@media (min-width:901px){.mobile-topbar{display:none}}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_guides.js"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="fermerSidebar()"></div>

<!-- Détail d'une ligne : modale par-dessus la grille, jamais une page à part. -->
<div class="rg-fond" id="rg-fond"><div class="rg-panneau" id="rg-panneau" role="dialog" aria-label="Résultats de la recherche"></div></div>

<div class="detail-fond" id="detail-fond">
  <section class="detail" id="detail" role="dialog" aria-modal="true" aria-labelledby="detail-titre"></section>
</div>

<div class="layout">
  <aside class="sidebar">
    <div class="sb-entete">
      <button type="button" class="sb-fermer" onclick="fermerSidebar()" title="Fermer le menu" aria-label="Fermer le menu">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <div class="logo" onclick="allerAuMenu()" title="Menu ERP">
        <span class="rvgi-mark">
          <img class="rvgi-sombre" src="/static/rvgi_mark_clair.png?v=3" alt="">
          <img class="rvgi-clair" src="/static/rvgi_mark.png?v=3" alt="">
        </span>
        <div>
          <div class="logo-brand">My<span>ERP</span></div>
          <div class="logo-sub">RVGI · lecture seule</div>
        </div>
      </div>
    </div>
    <button type="button" class="nav-btn" id="nav-menu" onclick="allerAuMenu()">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
      Menu
    </button>
    <div id="nav-ecrans"></div>

    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="uc" onclick="location.href='/profil'" title="Modifier mon profil">
        <div class="uc-name" id="uc-name">—</div>
        <div class="uc-role" id="uc-role">—</div>
      </div>
      <button type="button" class="support-btn" id="btn-support">
        <span class="support-ico" id="support-ico"></span>
        Contacter le support
      </button>
      <button type="button" class="theme-btn" id="btn-theme">
        <span class="theme-ico" id="theme-ico"></span>
        <span class="theme-label" id="theme-label">Mode clair</span>
      </button>
      <button type="button" class="logout-btn" id="btn-logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">MyERP · __V_LABEL__</div>
    </div>
  </aside>

  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="basculerSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">ERP</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Menu</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>

    <div class="page-head">
      <button type="button" class="btn-menu" onclick="basculerSidebar()" aria-label="Ouvrir le menu ERP">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        Menu
      </button>
      <span class="head-mark rvgi-mark">
        <img class="rvgi-sombre" src="/static/rvgi_mark_clair.png?v=3" alt="RVGI">
        <img class="rvgi-clair" src="/static/rvgi_mark.png?v=3" alt="RVGI">
      </span>
      <div>
        <div class="head-titre-ligne"><h1 id="titre">ERP</h1><span id="guide-btn-slot"></span></div>
        <div class="sous" id="sous">Lecture du miroir de RVGI.</div>
      </div>
      <div class="rg">
        <svg class="rg-ico" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg>
        <input type="search" id="rg-q" autocomplete="off" spellcheck="false"
               placeholder="Chercher partout : n° de pièce, client, article…"
               aria-label="Chercher dans tous les écrans">
        <kbd class="rg-kbd">Ctrl K</kbd>
      </div>
      <div class="head-droite" id="head-droite"></div>
      <div class="head-actions">
        <button type="button" class="head-btn" id="hd-profil" title="Mon profil" aria-label="Mon profil">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        </button>
        <button type="button" class="head-btn" id="hd-retour" title="Retour à MySifa" aria-label="Retour à MySifa">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/></svg>
        </button>
        <button type="button" class="head-btn" id="hd-theme" title="Changer de thème" aria-label="Changer de thème"></button>
        <button type="button" class="head-btn danger" id="hd-logout" title="Déconnexion" aria-label="Déconnexion">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        </button>
      </div>
    </div>

    <div id="corps" style="flex:1;min-height:0;display:flex;flex-direction:column"></div>
  </main>
</div>

<script>
// ══════════════════════════════════════════════════════════════════
// MyERP — lecture du miroir RVGI.
// Convention api() : retourne le JSON parsé, throw sur HTTP != 2xx.
// Le rail de filtres n'est JAMAIS reconstruit par un rafraîchissement de
// liste : seuls le corps de la grille et le pied changent. C'est ce qui
// garantit que la recherche ne perd pas le focus en cours de frappe.
// ══════════════════════════════════════════════════════════════════
const USER_ROLE = "__USER_ROLE__";

const S = {
  meta: null,
  ecran: null,        // clé de l'écran courant
  def: null,          // sa définition (colonnes, filtres) telle que renvoyée par meta
  colonnes: [],
  lignes: [],
  total: 0,
  page: 1,
  taille: 100,
  tri: null,
  sens: 'asc',
  q: '',
  filtres: {},
  selection: null,
  epingles: [],       // colonnes figées à gauche, dans l'ordre d'épinglage
  colDrag: null,      // colonne en cours de déplacement
  glisse: false,      // un défilement à la souris vient d'avoir lieu
  jeton: 0,           // anti-course : seule la dernière requête lancée s'affiche
  pile: [],           // fil d'Ariane de la modale : {ecran, id}
  jetonD: 0,          // anti-course pour la modale
  contexte: null,     // grille ouverte depuis une pièce liée
  ctxAttente: null,   // contexte à consommer au prochain ouvrirEcran()
  apresEcran: null,   // à jouer une fois l'écran monté (recherche globale)
};

const ICO_SUN='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICO_MOON='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function toast(msg,type){const t=document.createElement('div');t.className='toast'+(type==='err'?' err':'');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3400);}
async function api(url){
  const r=await fetch(url,{credentials:'include'});
  if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}
  return r.json();
}

// ── Formats ──────────────────────────────────────────────────────
function fmtNb(v,dec){
  const n=Number(v);
  if(!isFinite(n))return esc(v);
  return n.toLocaleString('fr-FR',{minimumFractionDigits:dec||0,maximumFractionDigits:dec==null?2:dec});
}
function fmtDate(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(!m)return esc(s);
  return m[3]+'/'+m[2]+'/'+m[1];
}
function fmtDateHeure(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
  if(!m)return fmtDate(s);
  return m[3]+'/'+m[2]+'/'+m[1]+' '+m[4]+':'+m[5];
}
function libelleEnum(nom,code){
  const t=(S.meta&&S.meta.enums&&S.meta.enums[nom])||null;
  const c=String(code==null?'':code);
  if(t&&t[c]!=null)return t[c];
  if(c==='255')return '—';   // sentinelle WinDev : octet non renseigné
  return c;   // un code inconnu s'affiche brut : on ne cache jamais une valeur
}

// Rendu d'une cellule : classe CSS + HTML. Une valeur absente est un tiret
// discret, jamais un vide — sinon on ne distingue pas « rien » de « pas chargé ».
function cellule(col,v){
  if(v==null||v==='')return{cls:'vide',html:'—'};
  const t=col.type||'texte';
  if(t==='date')     return {cls:'',     html:fmtDate(v)};
  if(t==='datetime') return {cls:'mono', html:fmtDateHeure(v)};
  if(t==='of')       return {cls:'of',   html:esc(v)};
  if(t==='ref'||t==='code') return {cls:'mono',html:esc(v)};
  if(t==='bool')     return {cls:'',     html:(String(v)==='1'||v===true)?'Oui':'—'};
  if(t==='enum'){
    const code=String(v);
    const cl=('n'+code).length<=3?('n'+code):'';
    return {cls:'',html:'<span class="badge '+cl+'">'+esc(libelleEnum(col.enum,code))+'</span>'};
  }
  if(t==='qte'||t==='nombre'){
    const n=Number(v);
    const neg=isFinite(n)&&n<0;
    return {cls:'num'+(neg?' neg':''),html:fmtNb(v,0)};
  }
  if(t==='prix')     return {cls:'num',  html:fmtNb(v,4)};
  if(t==='montant')  return {cls:'num',  html:fmtNb(v,2)};
  return {cls:'',html:esc(v)};
}

// ── Disposition des colonnes ─────────────────────────────────────
// Ordre et épinglages sont mémorisés par écran, dans le navigateur. C'est un
// confort d'affichage, pas une donnée : il n'a pas à voyager jusqu'au serveur,
// et il ne suit pas l'utilisateur d'un poste à l'autre — dit une fois ici pour
// que ce ne soit pas une surprise.
function cleLayout(){return 'mysifa_erp_cols_'+(S.ecran||'');}
function layoutCharger(){
  try{const b=localStorage.getItem(cleLayout());if(b)return JSON.parse(b)||{};}catch(e){}
  return {ordre:[],epingles:[]};
}
function layoutSauver(){
  try{
    localStorage.setItem(cleLayout(),JSON.stringify({
      ordre:S.colonnes.map(c=>c.nom), epingles:S.epingles
    }));
  }catch(e){}
}
function layoutOublier(){
  try{localStorage.removeItem(cleLayout());}catch(e){}
  S.epingles=[];
  charger();
  toast('Disposition des colonnes réinitialisée.');
}
// Les épinglées passent devant, dans l'ordre où elles ont été épinglées.
function reordonner(){
  const ep=[],reste=[];
  S.colonnes.forEach(c=>{(S.epingles.indexOf(c.nom)>=0?ep:reste).push(c);});
  ep.sort((a,b)=>S.epingles.indexOf(a.nom)-S.epingles.indexOf(b.nom));
  S.colonnes=ep.concat(reste);
}
function appliquerLayout(colonnes){
  const l=layoutCharger();
  const parNom={};colonnes.forEach(c=>{parNom[c.nom]=c;});
  const ordonnees=[];
  (l.ordre||[]).forEach(n=>{if(parNom[n]){ordonnees.push(parNom[n]);delete parNom[n];}});
  colonnes.forEach(c=>{if(parNom[c.nom])ordonnees.push(c);});   // colonnes nouvelles : à la fin
  S.colonnes=ordonnees;
  S.epingles=(l.epingles||[]).filter(n=>ordonnees.some(c=>c.nom===n));
  reordonner();
}
function basculerEpingle(nom){
  const i=S.epingles.indexOf(nom);
  if(i>=0)S.epingles.splice(i,1);else S.epingles.push(nom);
  reordonner();layoutSauver();renderTete();renderGrille();
}
function deplacerColonne(depuis,vers){
  if(depuis===vers)return;
  const i=S.colonnes.findIndex(c=>c.nom===depuis);
  const j=S.colonnes.findIndex(c=>c.nom===vers);
  if(i<0||j<0)return;
  const [c]=S.colonnes.splice(i,1);
  S.colonnes.splice(j,0,c);
  reordonner();layoutSauver();renderTete();renderGrille();
}
// Décalage `left` des colonnes épinglées : mesuré après rendu, parce que la
// largeur réelle dépend du contenu, pas de la largeur déclarée au catalogue.
function appliquerEpingles(){
  const table=document.querySelector('table.grille');
  if(!table)return;
  const ths=table.querySelectorAll('thead th');
  let x=0;
  S.colonnes.forEach((c,i)=>{
    const th=ths[i];
    if(!th)return;
    const cellules=table.querySelectorAll('tbody tr > td:nth-child('+(i+1)+')');
    const epingle=S.epingles.indexOf(c.nom)>=0;
    const suivante=S.colonnes[i+1];
    const dernier=epingle&&(!suivante||S.epingles.indexOf(suivante.nom)<0);
    if(epingle){
      th.style.left=x+'px';th.classList.add('epingle');
      th.classList.toggle('bord-epingle',dernier);
      cellules.forEach(td=>{
        td.style.left=x+'px';td.classList.add('epingle');
        td.classList.toggle('bord-epingle',dernier);
      });
      x+=th.offsetWidth;
    }else{
      th.style.left='';th.classList.remove('epingle','bord-epingle');
      cellules.forEach(td=>{td.style.left='';td.classList.remove('epingle','bord-epingle');});
    }
  });
}
// Défilement à la souris : la barre horizontale est en bas d'une grille haute,
// donc presque toujours hors de vue. On attrape la grille et on la tire.
function activerGlisserDefiler(){
  const z=document.querySelector('.grille-scroll');
  if(!z||z.dataset.glisse)return;
  z.dataset.glisse='1';
  let actif=false,bouge=false,x0=0,y0=0,g0=0,h0=0;
  z.addEventListener('mousedown',e=>{
    if(e.button!==0)return;
    if(e.target.closest('button, a, input, select, .th-poignee'))return;
    actif=true;bouge=false;x0=e.pageX;y0=e.pageY;g0=z.scrollLeft;h0=z.scrollTop;
  });
  z.addEventListener('mousemove',e=>{
    if(!actif)return;
    const dx=e.pageX-x0,dy=e.pageY-y0;
    if(!bouge){
      if(Math.abs(dx)<5&&Math.abs(dy)<5)return;
      bouge=true;z.classList.add('attrape');
    }
    e.preventDefault();
    z.scrollLeft=g0-dx;z.scrollTop=h0-dy;
  });
  function fin(){
    if(bouge)S.glisse=true;   // avale le clic qui suit, sinon on ouvre une ligne
    actif=false;bouge=false;z.classList.remove('attrape');
  }
  z.addEventListener('mouseleave',fin);
  window.addEventListener('mouseup',fin);
}

// ── Icônes des écrans ────────────────────────────────────────────
// Un pictogramme par nature d'objet, réutilisé quand deux écrans montrent la
// même chose vue d'un autre bout (un prix reste un prix, un mouvement reste un
// mouvement). Un écran sans icône déclarée tombe sur celle par défaut.
function _svg(d){
  return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '+
         'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'+d+'</svg>';
}
const ICO_ECRAN = {
  devis:_svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>'),
  commandes:_svg('<rect x="4" y="4" width="16" height="17" rx="2"/><path d="M9 2h6v4H9z"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="13" y2="16"/>'),
  livraisons:_svg('<rect x="1" y="6" width="13" height="10" rx="1"/><path d="M14 9h4l3 3v4h-7z"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>'),
  factures:_svg('<path d="M6 2h12v20l-3-2-3 2-3-2-3 2z"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="9" y1="12" x2="15" y2="12"/>'),
  echeances:_svg('<rect x="3" y="4" width="18" height="17" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M12 14v3h3"/>'),
  marches:_svg('<rect x="2" y="7" width="20" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><line x1="2" y1="12" x2="22" y2="12"/>'),
  achats:_svg('<circle cx="9" cy="20" r="1.6"/><circle cx="18" cy="20" r="1.6"/><path d="M2 3h3l2.5 12h11L21 7H6"/>'),
  receptions:_svg('<path d="M3 8l9-5 9 5v9l-9 5-9-5z"/><path d="M3 8l9 5 9-5"/><line x1="12" y1="13" x2="12" y2="22"/>'),
  appels:_svg('<path d="M3 10v4h4l6 5V5L7 10z"/><path d="M17 8a5 5 0 0 1 0 8"/>'),
  stock:_svg('<path d="M12 2l9 5-9 5-9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 17l9 5 9-5"/>'),
  mouvements:_svg('<polyline points="17 2 21 6 17 10"/><path d="M3 6h18"/><polyline points="7 14 3 18 7 22"/><path d="M21 18H3"/>'),
  matiere:_svg('<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/>'),
  articles:_svg('<path d="M20.6 13.4L12 22l-9-9V4a1 1 0 0 1 1-1h9z"/><circle cx="7.5" cy="7.5" r="1.4"/>'),
  clients:_svg('<path d="M17 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9.5" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/>'),
  fournisseurs:_svg('<path d="M3 21V8l7-5 7 5v13"/><path d="M17 12h4v9"/><line x1="7" y1="12" x2="10" y2="12"/><line x1="7" y1="16" x2="10" y2="16"/>'),
  outils:_svg('<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.1" y2="15.9"/><line x1="14.5" y1="14.5" x2="20" y2="20"/><line x1="8.1" y1="8.1" x2="12" y2="12"/>'),
  machines:_svg('<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M8 8V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v3"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="12" y2="17"/>'),
  prix:_svg('<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5A4.5 4.5 0 0 0 9 12a4.5 4.5 0 0 0 6.5 3.5"/><line x1="7.5" y1="11" x2="13" y2="11"/><line x1="7.5" y1="13.5" x2="13" y2="13.5"/>'),
  fiches:_svg('<rect x="4" y="3" width="16" height="18" rx="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="12" x2="16" y2="12"/><circle cx="16" cy="17" r="2"/>'),
  dossiers:_svg('<path d="M3 7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
  declarations:_svg('<path d="M9 11l3 3 8-8"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'),
  sorties:_svg('<path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5"/><polyline points="8 17 3 12 8 7"/><line x1="3" y1="12" x2="15" y2="12"/>'),
  colisage:_svg('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M3 11h18"/><path d="M8 7V4h8v3"/>'),
  defaut:_svg('<rect x="3" y="4" width="18" height="16" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="9" x2="9" y2="20"/>'),
};
const ICO_PAR_ECRAN = {
  devis:'devis', commandes:'commandes', livraisons:'livraisons', factures:'factures',
  echeances:'echeances', marches:'marches',
  commandes_fournisseur:'achats', receptions:'receptions',
  factures_fournisseur:'factures', appels_offres:'appels',
  stock_pf:'stock', mouvements_pf:'mouvements',
  stock_matiere:'matiere', mouvements_matiere:'mouvements',
  articles:'articles', clients:'clients', fournisseurs:'fournisseurs',
  outils:'outils', machines:'machines',
  prix_vente:'prix', prix_achat:'prix', prix_client:'prix',
  fiches_fabrication:'fiches', dossiers:'dossiers', declarations:'declarations',
  sorties_matiere:'sorties', colisage:'colisage',
};
function iconeEcran(cle){
  return ICO_ECRAN[ICO_PAR_ECRAN[cle]] || ICO_ECRAN.defaut;
}

// ══════════════════════════════════════════════════════════════════
// Guide in-app (moteur partagé mysifa_guides.js)
// ══════════════════════════════════════════════════════════════════
const ERP_TACHES_PAR_SERVICE = {
  direction: [
    'Retrouver un carnet, un chiffre d\'affaires ou un encours sans ouvrir RVGI.',
    'Croiser une commande avec sa livraison, sa facture et son échéance.',
    'Consulter les prix de vente, d\'achat et les prix négociés par client.'
  ],
  administration: [
    'Retrouver une commande, un BL ou une facture à partir d\'un numéro ou d\'un nom.',
    'Vérifier une réception : référence du BR, quantité, numéro de lot.',
    'Contrôler un stock produit fini ou matière avant de répondre à un client.'
  ]
};

function _erpBullets(role){
  const bloc=(titre,items)=>'<div class="mguide-svc"><div class="mguide-svc-hd">'+
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'+
    titre+'</div><ul class="mguide-svc-list">'+items.map(x=>'<li>'+x+'</li>').join('')+'</ul></div>';
  let h='<div class="mguide-tasks">';
  if(role==='superadmin'||role==='direction'){
    h+=bloc('Direction',ERP_TACHES_PAR_SERVICE.direction);
    h+=bloc('Administration',ERP_TACHES_PAR_SERVICE.administration);
  }else{
    h+=bloc('Ce que vous avez à faire ici',ERP_TACHES_PAR_SERVICE.administration);
  }
  return h+'</div>';
}

const ERP_GUIDES = {
  'erp-overview': { steps: [

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8l9-5 9 5v9l-9 5-9-5z"/><path d="M3 8l9 5 9-5"/><line x1="12" y1="13" x2="12" y2="22"/></svg>',
      title: 'ERP',
      body: '<p>Cet écran donne à lire les données de <strong>RVGI</strong>, l\'ERP de Sifa, dans l\'habillage de MySifa : commandes, livraisons, factures, stocks, référentiels. Vingt-sept écrans, une seule façon de chercher.</p><p>Tout y est en <span class="mguide-tag">lecture seule</span>. Rien de ce qui est fait ici ne remonte vers RVGI — l\'ERP reste la source, MySifa se contente de regarder.</p>',
      extra: '__BULLETS__'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
      title: 'Trouver le bon écran',
      body: '<p>Les écrans suivent les menus de RVGI : <span class="mguide-tag">Ventes</span>, <span class="mguide-tag">Stocks</span>, <span class="mguide-tag">Production</span>, <span class="mguide-tag">Achats</span>, <span class="mguide-tag">Comptabilités</span>. Les <strong>Fichiers</strong> — articles, clients, fournisseurs, outils, prix — sont rangés à part, en bas : ce sont des référentiels, pas des étapes du process.</p><p>Le bouton <span class="mguide-hl">Menu</span>, en haut à gauche, ouvre le même sommaire par-dessus n\'importe quel écran. On passe donc d\'une liste à l\'autre sans revenir en arrière.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="10" y="10" width="70" height="22" rx="7" fill="var(--card)" stroke="var(--accent)"/><text x="45" y="25" font-size="9" fill="var(--accent)" text-anchor="middle" font-weight="700">Menu</text><rect x="10" y="44" width="150" height="1" fill="var(--accent)"/><text x="10" y="58" font-size="9" fill="var(--text)" font-weight="800">Ventes</text><text x="20" y="74" font-size="8.5" fill="var(--text2)">Devis</text><text x="20" y="88" font-size="8.5" fill="var(--accent)" font-weight="700">Commandes</text><text x="20" y="102" font-size="8.5" fill="var(--text2)">Bons de livraison</text><line x1="14" y1="64" x2="14" y2="106" stroke="var(--border)"/><rect x="180" y="44" width="150" height="1" fill="var(--accent)"/><text x="180" y="58" font-size="9" fill="var(--text)" font-weight="800">Achats</text><text x="190" y="74" font-size="8.5" fill="var(--text2)">Commandes fourn.</text><text x="190" y="88" font-size="8.5" fill="var(--text2)">Réceptions</text><line x1="184" y1="64" x2="184" y2="92" stroke="var(--border)"/><line x1="10" y1="118" x2="330" y2="118" stroke="var(--border)"/><text x="10" y="134" font-size="9" fill="var(--muted)" font-weight="800">Fichiers</text><text x="80" y="134" font-size="8.5" fill="var(--text2)">Articles</text><text x="140" y="134" font-size="8.5" fill="var(--text2)">Clients</text><text x="200" y="134" font-size="8.5" fill="var(--text2)">Fournisseurs</text><text x="278" y="134" font-size="8.5" fill="var(--text2)">Prix</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg>',
      title: 'Chercher et filtrer',
      body: '<p>La colonne de gauche ne bouge jamais. La <strong>recherche</strong> porte sur les colonnes qui comptent pour l\'écran — un nom de client, une désignation, un numéro — et se vide avec <span class="mguide-tag">Échap</span>. Les filtres en dessous se cumulent avec elle.</p><p>Sur les commandes, <span class="mguide-hl">Position</span> est réglé d\'entrée sur <strong>En cours</strong> : on ouvre sur le carnet vivant, pas sur dix ans d\'archives. Le bouton <span class="mguide-tag">Réinitialiser les filtres</span> remet ce réglage, il ne vide pas tout.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="8" y="8" width="112" height="144" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="20" y="26" font-size="8" fill="var(--text)" font-weight="800">RECHERCHE</text><rect x="20" y="34" width="88" height="20" rx="7" fill="var(--bg)" stroke="var(--accent)"/><text x="28" y="48" font-size="8" fill="var(--muted)">LIDL</text><text x="20" y="72" font-size="8" fill="var(--text)" font-weight="800">FILTRES</text><text x="20" y="88" font-size="7.5" fill="var(--text2)">POSITION</text><rect x="20" y="93" width="88" height="18" rx="6" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="28" y="106" font-size="8" fill="var(--accent)" font-weight="700">En cours</text><text x="20" y="126" font-size="7.5" fill="var(--text2)">ORIGINE</text><rect x="20" y="131" width="88" height="18" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="28" y="144" font-size="8" fill="var(--muted)">Tous</text><rect x="132" y="8" width="200" height="144" rx="9" fill="var(--bg)" stroke="var(--border)"/><rect x="132" y="8" width="200" height="22" rx="9" fill="var(--card)"/><text x="144" y="23" font-size="7.5" fill="var(--muted)" font-weight="700">N° / OF</text><text x="200" y="23" font-size="7.5" fill="var(--muted)" font-weight="700">CLIENT</text><text x="278" y="23" font-size="7.5" fill="var(--muted)" font-weight="700">QUANTITÉ</text><line x1="132" y1="30" x2="332" y2="30" stroke="var(--border)"/><text x="144" y="46" font-size="8" fill="var(--accent)" font-weight="700">9932399</text><text x="200" y="46" font-size="8" fill="var(--text)">LIDL</text><text x="324" y="46" font-size="8" fill="var(--text)" text-anchor="end">500 000</text><line x1="132" y1="54" x2="332" y2="54" stroke="var(--border)"/><text x="144" y="70" font-size="8" fill="var(--accent)" font-weight="700">9932401</text><text x="200" y="70" font-size="8" fill="var(--text)">LIDL</text><text x="324" y="70" font-size="8" fill="var(--text)" text-anchor="end">120 000</text><line x1="132" y1="78" x2="332" y2="78" stroke="var(--border)"/><text x="144" y="140" font-size="8" fill="var(--muted)">1–100 sur 880</text></svg>'
    }
    ,{
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="9" x2="9" y2="20"/></svg>',
      title: 'Ranger la grille à sa main',
      body: '<p>Un écran ERP est large. Trois gestes le rendent praticable : <strong>glisser une en-tête</strong> par sa poignée pour déplacer la colonne, cliquer le <strong>cadenas</strong> pour la figer à gauche, et <strong>tirer la grille à la souris</strong> pour la faire défiler sans chercher la barre du bas.</p><p>L\'ordre et les colonnes figées sont mémorisés <strong>écran par écran, sur ce poste</strong>. Ils ne vous suivent pas d\'un ordinateur à l\'autre. Un clic sur une en-tête trie ; un second inverse le sens.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="8" y="20" width="324" height="24" rx="6" fill="var(--card)" stroke="var(--border)"/><circle cx="20" cy="29" r="1.3" fill="var(--muted)"/><circle cx="25" cy="29" r="1.3" fill="var(--muted)"/><circle cx="20" cy="35" r="1.3" fill="var(--muted)"/><circle cx="25" cy="35" r="1.3" fill="var(--muted)"/><text x="34" y="36" font-size="8" fill="var(--accent)" font-weight="700">N° / OF</text><rect x="76" y="26" width="12" height="12" rx="3" fill="var(--accent-bg)"/><path d="M79 33h6v4h-6z" fill="none" stroke="var(--accent)" stroke-width="1.2"/><path d="M80.5 33v-2a1.5 1.5 0 0 1 3 0v2" fill="none" stroke="var(--accent)" stroke-width="1.2"/><text x="106" y="36" font-size="8" fill="var(--muted)" font-weight="700">CLIENT</text><text x="176" y="36" font-size="8" fill="var(--muted)" font-weight="700">DÉSIGNATION</text><text x="276" y="36" font-size="8" fill="var(--muted)" font-weight="700">QUANTITÉ</text><line x1="96" y1="20" x2="96" y2="150" stroke="var(--accent)"/><rect x="8" y="48" width="88" height="22" rx="4" fill="var(--bg)"/><text x="34" y="63" font-size="8" fill="var(--accent)">9932399</text><rect x="100" y="48" width="232" height="22" rx="4" fill="var(--bg)" opacity=".45"/><text x="106" y="63" font-size="8" fill="var(--text2)">LIDL</text><rect x="8" y="76" width="88" height="22" rx="4" fill="var(--bg)"/><text x="34" y="91" font-size="8" fill="var(--accent)">9932401</text><rect x="100" y="76" width="232" height="22" rx="4" fill="var(--bg)" opacity=".45"/><text x="106" y="91" font-size="8" fill="var(--text2)">SCAPARTOIS</text><text x="150" y="126" font-size="8" fill="var(--muted)">colonnes figées</text><path d="M96 130 L60 130" stroke="var(--accent)" stroke-width="1.4" marker-end="url(#gf)"/><defs><marker id="gf" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6z" fill="var(--accent)"/></marker></defs><path d="M240 130 L300 130" stroke="var(--muted)" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#gf)"/><text x="250" y="146" font-size="8" fill="var(--muted)">tirer pour défiler</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="14" y1="3" x2="14" y2="21"/><line x1="17" y1="9" x2="21" y2="9"/><line x1="17" y1="14" x2="21" y2="14"/></svg>',
      title: 'Ouvrir une ligne, suivre la pièce',
      body: '<p>Un clic sur une ligne ouvre une <strong>fiche en grand</strong> par-dessus la grille : la ligne y est dépliée en blocs — la pièce, l\'article, les quantités et prix, la livraison. Ce que l\'écran ne montre pas est regroupé sous <span class="mguide-tag">Autres champs</span>, replié. Rien n\'est masqué : si RVGI porte l\'information, elle est là.</p><p>En bas, <span class="mguide-hl">Pièces liées</span> suit les clés de RVGI : d\'une commande vers ses bons de livraison, ses factures, ses mouvements de stock. Un clic sur une pièce l\'ouvre dans la même fiche — <span class="mguide-tag">Retour</span> revient d\'un cran, <span class="mguide-tag">Voir les N</span> bascule sur l\'écran complet. <span class="mguide-tag">Échap</span> referme.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><g opacity=".28"><rect x="4" y="6" width="332" height="148" rx="8" fill="var(--bg)" stroke="var(--border)"/><line x1="4" y1="26" x2="336" y2="26" stroke="var(--border)"/><line x1="4" y1="46" x2="336" y2="46" stroke="var(--border)"/><line x1="4" y1="66" x2="336" y2="66" stroke="var(--border)"/><line x1="4" y1="86" x2="336" y2="86" stroke="var(--border)"/><line x1="4" y1="106" x2="336" y2="106" stroke="var(--border)"/><line x1="4" y1="126" x2="336" y2="126" stroke="var(--border)"/></g><rect x="26" y="12" width="288" height="136" rx="10" fill="var(--card)" stroke="var(--accent)"/><rect x="26" y="12" width="288" height="26" rx="10" fill="var(--bg)"/><text x="38" y="24" font-size="9" fill="var(--text)" font-weight="800">Commande 9932399</text><text x="38" y="34" font-size="7" fill="var(--muted)">LIDL · 890/0112 · 500 000</text><text x="302" y="29" font-size="10" fill="var(--muted)" text-anchor="end">×</text><line x1="26" y1="38" x2="314" y2="38" stroke="var(--border)"/><rect x="34" y="46" width="132" height="52" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="42" y="58" font-size="6.5" fill="var(--muted)" font-weight="800">LA PIÈCE</text><text x="42" y="72" font-size="7.5" fill="var(--text2)">N°</text><text x="158" y="72" font-size="7.5" fill="var(--text)" text-anchor="end" font-weight="700">9932399</text><line x1="42" y1="77" x2="158" y2="77" stroke="var(--border)"/><text x="42" y="90" font-size="7.5" fill="var(--text2)">Client</text><text x="158" y="90" font-size="7.5" fill="var(--text)" text-anchor="end" font-weight="700">LIDL</text><rect x="174" y="46" width="132" height="52" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="182" y="58" font-size="6.5" fill="var(--muted)" font-weight="800">QUANTITÉS ET PRIX</text><text x="182" y="72" font-size="7.5" fill="var(--text2)">Quantité</text><text x="298" y="72" font-size="7.5" fill="var(--text)" text-anchor="end" font-weight="700">500 000</text><line x1="182" y1="77" x2="298" y2="77" stroke="var(--border)"/><text x="182" y="90" font-size="7.5" fill="var(--text2)">Prix</text><text x="298" y="90" font-size="7.5" fill="var(--text)" text-anchor="end" font-weight="700">0,0142</text><text x="34" y="112" font-size="6.5" fill="var(--text2)" font-weight="800">PIÈCES LIÉES</text><line x1="92" y1="110" x2="306" y2="110" stroke="var(--border)"/><rect x="34" y="118" width="88" height="24" rx="7" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="42" y="128" font-size="7" fill="var(--accent)" font-weight="800">Bons de livraison</text><text x="42" y="138" font-size="6.5" fill="var(--accent)" opacity=".85">numcde 9932399</text><text x="114" y="133" font-size="7.5" fill="var(--accent)" text-anchor="end" font-weight="800">3</text><rect x="128" y="118" width="88" height="24" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="136" y="128" font-size="7" fill="var(--text)" font-weight="800">Factures</text><text x="136" y="138" font-size="6.5" fill="var(--muted)">livno 9932399</text><text x="208" y="133" font-size="7.5" fill="var(--text2)" text-anchor="end" font-weight="800">1</text><rect x="222" y="118" width="88" height="24" rx="7" fill="var(--card)" stroke="var(--border)"/><text x="230" y="128" font-size="7" fill="var(--text)" font-weight="800">Mouvements</text><text x="230" y="138" font-size="6.5" fill="var(--muted)">Voir les 12 →</text><text x="302" y="133" font-size="7.5" fill="var(--text2)" text-anchor="end" font-weight="800">12</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
      title: 'Lecture seule, et données d\'il y a quelques heures',
      body: '<p>Les données ne sont pas lues dans RVGI en direct : le serveur de MySifa ne voit pas le réseau de l\'atelier. Une synchronisation en rapporte une copie <strong>deux fois par jour</strong>, à 5 h et 12 h 30.</p><p>La pastille <span class="mguide-tag">Miroir du …</span>, en haut à droite, dit l\'heure de cette copie — et passe à l\'<span class="mguide-hl">orange</span> au-delà de deux jours. Pour une commande saisie il y a dix minutes, c\'est encore RVGI qu\'il faut ouvrir.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="12" y="46" width="92" height="46" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="58" y="66" font-size="9" fill="var(--text)" text-anchor="middle" font-weight="800">RVGI</text><text x="58" y="80" font-size="7.5" fill="var(--muted)" text-anchor="middle">réseau Sifa</text><path d="M108 69 L152 69" stroke="var(--accent)" stroke-width="1.8" marker-end="url(#fl)"/><defs><marker id="fl" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6z" fill="var(--accent)"/></marker></defs><text x="130" y="60" font-size="7.5" fill="var(--accent)" text-anchor="middle">5 h · 12 h 30</text><rect x="156" y="46" width="92" height="46" rx="9" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="202" y="66" font-size="9" fill="var(--accent)" text-anchor="middle" font-weight="800">Miroir</text><text x="202" y="80" font-size="7.5" fill="var(--accent)" text-anchor="middle" opacity=".8">copie du jour</text><path d="M252 69 L292 69" stroke="var(--muted)" stroke-width="1.8" marker-end="url(#fl)"/><rect x="296" y="46" width="32" height="46" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="312" y="73" font-size="8" fill="var(--text2)" text-anchor="middle">vous</text><rect x="96" y="112" width="148" height="22" rx="11" fill="var(--card)" stroke="var(--border)"/><text x="170" y="127" font-size="8.5" fill="var(--text2)" text-anchor="middle">Miroir du 25/08/2026 05:00</text><rect x="12" y="112" width="76" height="22" rx="11" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="50" y="127" font-size="8.5" fill="var(--accent)" text-anchor="middle" font-weight="700">Lecture seule</text></svg>'
    }
  ]}
};


function initGuides(){
  try{
    if(!window.MySifaGuides)return;
    MySifaGuides.configure({role:USER_ROLE});
    // Les bullets de la 1re etape dependent du role : on les injecte ici,
    // une fois le role connu, plutot que de figer le texte au chargement.
    const g=JSON.parse(JSON.stringify(ERP_GUIDES));
    g['erp-overview'].steps[0].extra=_erpBullets(USER_ROLE);
    MySifaGuides.registerMany(g);
    MySifaGuides.boot().then(function(){
      const slot=document.getElementById('guide-btn-slot');
      if(slot&&typeof MySifaGuides.bookBtn==='function')slot.innerHTML=MySifaGuides.bookBtn('erp-overview');
      MySifaGuides.autoOpen('erp-overview');
    });
  }catch(e){}
}

// ── Navigation ───────────────────────────────────────────────────
// Les domaines de paramétrage passent après ceux du process, quelle que soit
// leur place dans le catalogue.
function domainesOrdonnes(){
  const d=(S.meta&&S.meta.domaines)||[];
  return d.filter(x=>x.type!=='parametres').concat(d.filter(x=>x.type==='parametres'));
}

function renderNav(){
  const hote=document.getElementById('nav-ecrans');
  if(!S.meta||!S.meta.present){hote.innerHTML='';return;}
  let h='<div class="nav-colonnes">';
  domainesOrdonnes().forEach(d=>{
    const ecrans=(S.meta.ecrans||[]).filter(e=>e.domaine===d.cle);
    if(!ecrans.length)return;
    const kl=(d.type==='parametres')?' parametres':'';
    h+='<div class="nav-bloc'+kl+'"><div class="nav-groupe">'+esc(d.label)+'</div><div class="nav-domaine">';
    ecrans.forEach(e=>{
      h+='<button type="button" class="nav-btn'+(S.ecran===e.cle?' active':'')+'" data-ecran="'+esc(e.cle)+'">'+esc(e.label)+'</button>';
    });
    h+='</div></div>';
  });
  hote.innerHTML=h+'</div>';
  hote.querySelectorAll('[data-ecran]').forEach(b=>{
    b.addEventListener('click',()=>{location.hash='#/'+b.getAttribute('data-ecran');});
  });
  const nm=document.getElementById('nav-menu');
  if(nm)nm.classList.toggle('active',!S.ecran);
}

function renderFraicheur(){
  const hote=document.getElementById('head-droite');
  if(!S.meta){hote.innerHTML='';return;}
  if(!S.meta.present){hote.innerHTML='<span class="pill vieux">Miroir absent</span>';return;}
  const d=String(S.meta.importe_le||'');
  const j=(new Date()-new Date(d.replace(' ','T')))/86400000;
  const vieux=isFinite(j)&&j>2;
  hote.innerHTML='<span class="pill lecture">Lecture seule</span>'+
    '<span class="pill'+(vieux?' vieux':'')+'">Miroir du '+esc(fmtDateHeure(d))+'</span>';
}

// ── Vue menu ─────────────────────────────────────────────────────
function ouvrirMenu(){
  fermerSidebar();   // on a choisi sa destination : le tiroir n'a plus lieu d'etre
  S.ecran=null;S.def=null;S.selection=null;S.colonnes=[];
  document.getElementById('titre').textContent='ERP';
  document.getElementById('sous').textContent=
    (S.meta&&S.meta.present)
      ? 'Lecture de l\'ERP RVGI.'
      : 'Le miroir de l\'ERP n\'a pas encore été construit.';
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent='Menu';
  renderNav();
  const corps=document.getElementById('corps');
  if(!S.meta||!S.meta.present){
    corps.innerHTML='<div class="vide-msg">'+esc((S.meta&&S.meta.message)||'Miroir indisponible.')+'</div>';
    return;
  }
  let h='<div class="menu-wrap"><div class="colonnes">';
  domainesOrdonnes().forEach(d=>{
    const ecrans=(S.meta.ecrans||[]).filter(e=>e.domaine===d.cle);
    if(!ecrans.length)return;
    const kl=(d.type==='parametres')?' parametres':'';
    h+='<div class="colonne'+kl+'"><div class="domaine-titre">'+esc(d.label)+'</div><div class="cartes">';
    ecrans.forEach(e=>{
      h+='<div class="carte" data-ecran="'+esc(e.cle)+'" title="'+esc(e.resume||'')+'">'+
           '<span class="carte-ico">'+iconeEcran(e.cle)+'</span>'+
           '<span class="carte-titre">'+esc(e.label)+'</span>'+
         '</div>';
    });
    h+='</div></div>';
  });
  corps.innerHTML=h+'</div></div>';
  corps.querySelectorAll('[data-ecran]').forEach(c=>{
    c.addEventListener('click',()=>{location.hash='#/'+c.getAttribute('data-ecran');});
  });
}

// ── Vue écran : rail + grille ────────────────────────────────────
function ouvrirEcran(cle){
  const def=((S.meta&&S.meta.ecrans)||[]).find(e=>e.cle===cle);
  if(!def){toast('Écran inconnu.','err');ouvrirMenu();return;}
  S.ecran=cle;S.def=def;S.page=1;S.tri=null;S.sens='asc';S.q='';S.filtres={};S.selection=null;S.colonnes=[];S.epingles=[];
  // Un contexte de pièce liée n'est valable que pour l'écran qu'il vise, et
  // pour une seule ouverture : on le consomme ici.
  S.contexte=(S.ctxAttente&&S.ctxAttente.cible===cle)?S.ctxAttente:null;
  S.ctxAttente=null;
  // Un écran s'ouvre sur ce qui est vivant : le filtre qui porte un défaut
  // (Position = En cours) est appliqué d'entrée, et reste effaçable. Venant
  // d'une pièce liée, non : on veut la pièce, même soldée.
  if(!S.contexte){
    (def.filtres||[]).forEach(f=>{
      if(f.defaut!=null&&f.defaut!=='')S.filtres[f.nom]=String(f.defaut);
    });
  }
  document.getElementById('titre').textContent=def.label;
  document.getElementById('sous').textContent=def.resume||'';
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=def.label;
  renderNav();

  // Rail construit UNE fois par écran. Les rafraîchissements de liste ne le
  // touchent pas : le champ de recherche garde son focus et son curseur.
  let rail='<div class="rail"><div class="rail-titre">Recherche</div>'+
    '<div class="champ"><input type="text" id="q" placeholder="Rechercher..." autocomplete="off"></div>';
  if((def.filtres||[]).length){
    rail+='<div class="rail-titre">Filtres</div>';
    (def.filtres||[]).forEach(f=>{
      const id='f-'+f.nom;
      const lab='<label for="'+id+'">'+esc(f.label)+'</label>';
      const val=S.filtres[f.nom]!=null?String(S.filtres[f.nom]):'';
      if(f.type==='enum'&&S.meta.enums&&S.meta.enums[f.enum]){
        let o='<option value=""'+(val===''?' selected':'')+'>Tous</option>';
        Object.keys(S.meta.enums[f.enum]).forEach(k=>{
          o+='<option value="'+esc(k)+'"'+(val===String(k)?' selected':'')+'>'+esc(S.meta.enums[f.enum][k])+'</option>';
        });
        rail+='<div class="champ">'+lab+'<select id="'+id+'" data-filtre="'+esc(f.nom)+'">'+o+'</select></div>';
      }else if(f.type==='date_min'||f.type==='date_max'){
        rail+='<div class="champ">'+lab+'<input type="date" id="'+id+'" data-filtre="'+esc(f.nom)+'" value="'+esc(val)+'"></div>';
      }else{
        const ph=f.exemple?('ex. '+f.exemple):(f.type==='contient'?'Contient…':'Valeur exacte');
        rail+='<div class="champ">'+lab+'<input type="text" id="'+id+'" data-filtre="'+esc(f.nom)+'" '+
              'value="'+esc(val)+'" placeholder="'+esc(ph)+'" autocomplete="off"></div>';
      }
    });
  }
  rail+='<button type="button" class="btn" id="btn-reset" style="width:100%">Réinitialiser les filtres</button>'+
    '<button type="button" class="btn" id="btn-reset-cols" style="width:100%;margin-top:6px">Réinitialiser les colonnes</button>'+
    '<div class="rail-info">Glisser une en-tête pour déplacer sa colonne, le cadenas pour la figer à gauche. '+
    'Tirer la grille à la souris pour la faire défiler.</div></div>';

  document.getElementById('corps').innerHTML='<div class="ecran">'+rail+
    '<div class="grille-zone">'+
      '<div class="bandeau" id="bandeau"></div>'+
      '<div class="grille-scroll"><table class="grille"><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>'+
      '<div class="pied" id="pied"></div></div></div>';
  renderBandeau();

  const q=document.getElementById('q');
  let minuteur=null;
  q.addEventListener('input',()=>{
    S.q=q.value;clearTimeout(minuteur);
    minuteur=setTimeout(()=>{S.page=1;charger();},220);
  });
  q.addEventListener('keydown',ev=>{
    if(ev.key==='Escape'){q.value='';S.q='';S.page=1;charger();}
  });
  document.querySelectorAll('[data-filtre]').forEach(el=>{
    const ev=(el.tagName==='SELECT'||el.type==='date')?'change':'input';
    let m=null;
    el.addEventListener(ev,()=>{
      S.filtres[el.getAttribute('data-filtre')]=el.value;
      clearTimeout(m);
      m=setTimeout(()=>{S.page=1;charger();},ev==='change'?0:220);
    });
  });
  document.getElementById('btn-reset').addEventListener('click',()=>{
    S.q='';S.filtres={};S.page=1;
    (def.filtres||[]).forEach(f=>{
      if(f.defaut!=null&&f.defaut!=='')S.filtres[f.nom]=String(f.defaut);
    });
    const c=document.getElementById('q');if(c)c.value='';
    document.querySelectorAll('[data-filtre]').forEach(el=>{
      const nom=el.getAttribute('data-filtre');
      el.value=S.filtres[nom]!=null?String(S.filtres[nom]):'';
    });
    charger();if(c)c.focus();
  });
  const bc=document.getElementById('btn-reset-cols');
  if(bc)bc.addEventListener('click',layoutOublier);
  // La recherche globale ouvre un écran PUIS une fiche : la grille doit être
  // montée avant, sinon la modale s'ouvrirait sur un écran vide.
  const suite=S.apresEcran;S.apresEcran=null;
  if(suite){try{suite();}catch(e){charger();}}
  else charger();
}

const ICO_POIGNEE='<svg class="th-poignee" width="10" height="14" viewBox="0 0 10 14" fill="currentColor" aria-hidden="true"><circle cx="2" cy="3" r="1.2"/><circle cx="8" cy="3" r="1.2"/><circle cx="2" cy="7" r="1.2"/><circle cx="8" cy="7" r="1.2"/><circle cx="2" cy="11" r="1.2"/><circle cx="8" cy="11" r="1.2"/></svg>';
const ICO_CADENAS_OUVERT='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.5-2"/></svg>';
const ICO_CADENAS_FERME='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';

function renderTete(){
  const t=document.getElementById('thead');
  if(!t)return;
  let h='<tr>';
  S.colonnes.forEach(c=>{
    const actif=S.tri===c.nom;
    const fl=actif?('<span class="fleche">'+(S.sens==='desc'?'▾':'▴')+'</span>'):'';
    const ep=S.epingles.indexOf(c.nom)>=0;
    h+='<th data-col="'+esc(c.nom)+'" draggable="true" style="'+(c.largeur?('min-width:'+c.largeur+'px'):'')+'">'+
         '<span class="th-boite">'+ICO_POIGNEE+
           '<span class="th-libelle">'+esc(c.label)+fl+'</span>'+
           '<button type="button" class="th-cadenas'+(ep?' on':'')+'" data-epingle="'+esc(c.nom)+'" '+
             'title="'+(ep?'Libérer la colonne':'Figer la colonne à gauche')+'" '+
             'aria-label="'+(ep?'Libérer la colonne':'Figer la colonne à gauche')+'">'+
             (ep?ICO_CADENAS_FERME:ICO_CADENAS_OUVERT)+
           '</button>'+
         '</span>'+
       '</th>';
  });
  t.innerHTML=h+'</tr>';

  t.querySelectorAll('[data-epingle]').forEach(b=>{
    b.addEventListener('click',ev=>{ev.stopPropagation();basculerEpingle(b.getAttribute('data-epingle'));});
  });

  t.querySelectorAll('[data-col]').forEach(th=>{
    const nom=th.getAttribute('data-col');
    th.addEventListener('click',ev=>{
      if(ev.target.closest('.th-cadenas'))return;
      if(S.tri===nom){S.sens=(S.sens==='asc')?'desc':'asc';}else{S.tri=nom;S.sens='asc';}
      S.page=1;charger();
    });
    th.addEventListener('dragstart',ev=>{
      S.colDrag=nom;th.classList.add('attrapee');
      try{ev.dataTransfer.effectAllowed='move';ev.dataTransfer.setData('text/plain',nom);}catch(e){}
    });
    th.addEventListener('dragend',()=>{
      S.colDrag=null;
      t.querySelectorAll('th').forEach(x=>x.classList.remove('attrapee','cible'));
    });
    th.addEventListener('dragover',ev=>{
      if(!S.colDrag||S.colDrag===nom)return;
      ev.preventDefault();th.classList.add('cible');
    });
    th.addEventListener('dragleave',()=>th.classList.remove('cible'));
    th.addEventListener('drop',ev=>{
      ev.preventDefault();th.classList.remove('cible');
      if(S.colDrag&&S.colDrag!==nom)deplacerColonne(S.colDrag,nom);
      S.colDrag=null;
    });
  });
  appliquerEpingles();
}

function urlListe(){
  const p=new URLSearchParams();
  if(S.q)p.set('q',S.q);
  if(S.tri){p.set('tri',S.tri);p.set('sens',S.sens);}
  p.set('page',String(S.page));
  p.set('taille',String(S.taille));
  Object.keys(S.filtres).forEach(k=>{if(S.filtres[k])p.set('f_'+k,S.filtres[k]);});
  // Ouverture depuis une pièce liée : on transmet l'origine, jamais un nom de
  // colonne — c'est le serveur qui reconstruit la jointure depuis le catalogue.
  if(S.contexte){
    p.set('depuis',S.contexte.depuis);
    p.set('depuis_id',S.contexte.depuis_id);
    p.set('lien',String(S.contexte.lien));
  }
  return '/api/erp/'+encodeURIComponent(S.ecran)+'/lignes?'+p.toString();
}

// Bandeau de provenance : dire d'où vient une grille restreinte, et permettre
// d'en sortir. Sans lui, une liste filtrée passe pour la liste complète.
function renderBandeau(){
  const b=document.getElementById('bandeau');
  if(!b)return;
  if(!S.contexte){b.classList.remove('on');b.innerHTML='';return;}
  const c=S.contexte;
  b.classList.add('on');
  b.innerHTML='<span>'+ICO_LIEN+'</span><span>Depuis <b>'+esc(c.depuis_label||c.depuis)+'</b>'+
    (c.cle_lue?(' · '+esc(c.cle_lue)):'')+'</span>'+
    '<button type="button" class="x" id="ctx-x">Voir tout l\'écran</button>';
  const x=document.getElementById('ctx-x');
  if(x)x.addEventListener('click',()=>{S.contexte=null;S.page=1;renderBandeau();charger();});
}

async function charger(){
  const tb=document.getElementById('tbody');
  if(!tb)return;
  const jeton=++S.jeton;
  const nbCol=Math.max(S.colonnes.length,1);
  tb.innerHTML='<tr><td colspan="'+nbCol+'"><div class="skel"></div></td></tr>';
  let r;
  try{ r=await api(urlListe()); }
  catch(e){
    if(jeton!==S.jeton)return;
    tb.innerHTML='<tr><td colspan="'+nbCol+'" class="vide">'+esc(e.message)+'</td></tr>';
    return;
  }
  if(jeton!==S.jeton)return;   // une frappe plus récente a déjà relancé
  if(S.contexte&&r.contexte){
    S.contexte.depuis_label=r.contexte.depuis_label;
    S.contexte.lien_label=r.contexte.lien;
    S.contexte.cle_lue=Object.keys(r.contexte.valeurs||{})
      .map(k=>k+' '+r.contexte.valeurs[k]).join(' · ');
    renderBandeau();
  }
  S.lignes=r.lignes;S.total=r.total;
  appliquerLayout(r.colonnes);
  renderTete();renderGrille();renderPied();
  activerGlisserDefiler();
}

function renderGrille(){
  const tb=document.getElementById('tbody');
  if(!tb)return;
  if(!S.lignes.length){
    const msg=S.q?('Aucun résultat pour « '+esc(S.q)+' »'):'Aucune ligne.';
    tb.innerHTML='<tr><td colspan="'+Math.max(S.colonnes.length,1)+'" class="vide">'+msg+'</td></tr>';
    return;
  }
  let h='';
  S.lignes.forEach(l=>{
    h+='<tr data-id="'+esc(l._id)+'"'+(String(S.selection)===String(l._id)?' class="sel"':'')+'>';
    S.colonnes.forEach(c=>{
      const r=cellule(c,l[c.nom]);
      h+='<td class="'+r.cls+'">'+r.html+'</td>';
    });
    h+='</tr>';
  });
  tb.innerHTML=h;
  tb.querySelectorAll('[data-id]').forEach(tr=>{
    tr.addEventListener('click',()=>{
      if(S.glisse){S.glisse=false;return;}   // c'était un défilement, pas un clic
      ouvrirDetail(tr.getAttribute('data-id'));
    });
  });
  appliquerEpingles();
}

function renderPied(){
  const p=document.getElementById('pied');
  if(!p)return;
  const debut=S.total?((S.page-1)*S.taille+1):0;
  const fin=Math.min(S.page*S.taille,S.total);
  const pages=Math.max(1,Math.ceil(S.total/S.taille));
  p.innerHTML='<span class="compte">'+fmtNb(debut,0)+'–'+fmtNb(fin,0)+' sur '+fmtNb(S.total,0)+'</span>'+
    '<span class="pager">'+
      '<button type="button" class="btn" id="prec"'+(S.page<=1?' disabled':'')+'>Précédent</button>'+
      '<span>page '+fmtNb(S.page,0)+' / '+fmtNb(pages,0)+'</span>'+
      '<button type="button" class="btn" id="suiv"'+(S.page>=pages?' disabled':'')+'>Suivant</button></span>';
  const a=document.getElementById('prec'),b=document.getElementById('suiv');
  if(a)a.addEventListener('click',()=>{if(S.page>1){S.page--;charger();}});
  if(b)b.addEventListener('click',()=>{if(S.page<pages){S.page++;charger();}});
}

// ── Détail : modale sectionnée + pièces liées ────────────────────
// La modale garde une pile : ouvrir une pièce liée empile, « Retour » dépile.
// On explore ainsi commande → BL → facture sans jamais perdre son point de
// départ, et sans quitter l'écran de travail derrière.
const ICO_LIEN='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>';
const ICO_CHEV='<svg class="chev" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
const ICO_FLECHE='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>';
const ICO_RETOUR='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="11 18 5 12 11 6"/></svg>';
const ICO_PIECE='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><polyline points="14 3 14 8 19 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>';
const ICO_FICHE='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/></svg>';

function defEcran(cle){return ((S.meta&&S.meta.ecrans)||[]).find(e=>e.cle===cle)||null;}

function enteteDetail(titre,sous){
  const retour=S.pile.length>1;
  const p=S.pile.length>1?S.pile[S.pile.length-2]:null;
  const dp=p?defEcran(p.ecran):null;
  return '<div class="detail-head">'+
    '<button type="button" class="detail-retour'+(retour?' on':'')+'" id="d-retour" title="Revenir">'+
      ICO_RETOUR+'<span>'+esc(dp?dp.label:'Retour')+'</span></button>'+
    '<div class="tt"><h2 id="detail-titre">'+esc(titre)+'</h2>'+
      (sous?('<p class="st">'+esc(sous)+'</p>'):'')+'</div>'+
    '<button type="button" class="detail-fermer" id="d-fermer" title="Fermer (Échap)">×</button></div>';
}

// Le sous-titre : ce qui identifie la pièce ouverte. Quand il y a un entête,
// c'est lui qui parle — numéro, client, date — plutôt que le premier groupe
// du détail, qui peut commencer par un identifiant technique.
function sousTitreDetail(groupes,piece){
  const source=piece?(piece.entete||[]).filter(c=>c.principal):((groupes||[])[0]||{}).champs;
  const bouts=[];
  (source||[]).forEach(c=>{
    if(bouts.length>=3)return;
    if(c.valeur==null||c.valeur==='')return;
    const v=cellule(c,c.valeur);
    const txt=String(v.html).replace(/<[^>]*>/g,'').trim();
    if(txt&&txt!=='—')bouts.push(txt);
  });
  return bouts.join(' · ');
}

function ouvrirDetail(id){
  S.pile=[{ecran:S.ecran,id:id}];
  S.selection=id;renderGrille();
  rendreDetail();
}
function empilerDetail(cle,id){S.pile.push({ecran:cle,id:id});rendreDetail();}
function depilerDetail(){if(S.pile.length>1){S.pile.pop();rendreDetail();}}

async function rendreDetail(){
  const f=document.getElementById('detail-fond'),d=document.getElementById('detail');
  if(!f||!d||!S.pile.length)return;
  const cur=S.pile[S.pile.length-1];
  const def=defEcran(cur.ecran);
  const jeton=++S.jetonD;
  f.classList.add('ouvert');
  d.innerHTML=enteteDetail(def?def.label:'Détail','')+
    '<div class="detail-corps"><div class="sections"><div class="groupe pleine" style="padding:18px"><div class="skel"></div></div></div></div>';
  brancherEnteteDetail();

  let r;
  try{ r=await api('/api/erp/'+encodeURIComponent(cur.ecran)+'/detail/'+encodeURIComponent(cur.id)); }
  catch(e){
    if(jeton!==S.jetonD)return;
    d.innerHTML=enteteDetail(def?def.label:'Détail','')+'<div class="detail-corps"><div class="vide-msg">'+esc(e.message)+'</div></div>';
    brancherEnteteDetail();return;
  }
  if(jeton!==S.jetonD)return;

  // Une commande, un marché, un BL sont des DOCUMENTS : l'entête d'abord,
  // puis toutes leurs lignes, puis la ligne ouverte, puis ce qui s'y rattache.
  const p=r.piece||null;
  h=enteteDetail(def?def.label:'Détail',sousTitreDetail(r.groupes,p));
  h+='<div class="detail-corps">';
  if(p)h+=blocPiece(p,cur.id);
  h+='<div class="titre-bloc">'+ICO_FICHE+'<span>'+(p?'Détail de la ligne':'Détail')+'</span></div>';
  const res=resumeLigne(r.groupes);
  h+=res.html;
  h+='<div class="sections" id="sec-detail">'+blocGroupes(r.groupes,res.pris)+'</div>';
  h+='<div class="titre-bloc" id="t-liens">'+ICO_LIEN+'<span>Pièces liées</span></div>'+
     '<div class="liens" id="liens"><div class="liens-vide">Recherche des pièces rattachées…</div></div>';
  h+='</div>';
  d.innerHTML=h;
  brancherEnteteDetail();
  d.querySelectorAll('.groupe-titre').forEach(t=>{
    t.addEventListener('click',()=>t.parentNode.classList.toggle('replie'));
  });
  // Changer de ligne sans quitter la pièce : on remplace la ligne courante
  // dans la pile plutôt que d'empiler — sinon « Retour » remonterait ligne
  // par ligne au lieu de revenir d'où l'on vient.
  d.querySelectorAll('.pl-ligne[data-id]').forEach(tr=>{
    tr.addEventListener('click',()=>{
      const id=tr.getAttribute('data-id');
      if(String(id)===String(cur.id))return;
      S.pile[S.pile.length-1]={ecran:cur.ecran,id:id};
      rendreDetail();
    });
  });
  d.querySelector('.detail-corps').scrollTop=0;
  chargerLiens(cur,jeton);
}

function blocGroupes(groupes,pris){
  pris=pris||{};
  // Ce qui reste vraiment à afficher, une fois le résumé servi. Un bloc seul
  // dans une grille à trois colonnes laisse deux tiers de vide : dans ce cas
  // il prend la largeur et étale ses champs.
  const restants=(groupes||[]).map((g,i)=>({g:g,i:i,champs:(g.champs||[]).filter(c=>!pris[c.nom])}))
                              .filter(x=>x.champs.length);
  const seul=restants.filter(x=>!x.g.replie).length<=1;
  let h='';
  restants.forEach(({g,i,champs})=>{
    h+='<div class="groupe'+(g.replie?' replie':'')+
       ((champs.length>14||(seul&&!g.replie))?' pleine champs-cols':'')+'" data-g="'+i+'">'+
       '<div class="groupe-titre"><span>'+esc(g.titre)+'</span>'+ICO_CHEV+'</div><div class="groupe-corps">';
    champs.forEach(c=>{
      const v=cellule(c,c.valeur);
      h+='<div class="ligne-champ"><span class="lab">'+esc(c.label)+'</span>'+
         '<span class="val '+esc(v.cls)+'">'+v.html+'</span></div>';
    });
    h+='</div></div>';
  });
  return h;
}

// Ce qu'on veut savoir d'une ligne en une seconde : de quel article il s'agit,
// et les chiffres qui comptent. Le reste des champs suit, mais ces quatre-là
// méritent d'être lus de loin plutôt que d'être une ligne parmi trente.
const TUILES_MAX=4;
function resumeLigne(groupes){
  const tous=[];
  (groupes||[]).forEach(g=>{ if(!g.replie)(g.champs||[]).forEach(c=>tous.push(c)); });
  const pris={};
  const rempli=c=>c&&c.valeur!=null&&c.valeur!=='';

  const article=tous.find(c=>c.type==='ref'&&rempli(c));
  const titres=tous.filter(c=>c.type==='texte'&&rempli(c)&&/désignation|designation|libell/i.test(c.label)).slice(0,2);
  const chiffres=tous.filter(c=>rempli(c)&&['qte','prix','montant','pct'].indexOf(c.type)>=0).slice(0,TUILES_MAX);
  if(!article&&!chiffres.length)return {html:'',pris:pris};

  let h='<div class="resume">';
  if(article||titres.length){
    h+='<div class="resume-quoi">';
    if(article){pris[article.nom]=1;h+='<span class="resume-ref">'+esc(article.valeur)+'</span>';}
    if(titres.length){
      h+='<span class="resume-des">'+titres.map(t=>{pris[t.nom]=1;return esc(t.valeur);}).join(' · ')+'</span>';
    }
    h+='</div>';
  }
  if(chiffres.length){
    h+='<div class="resume-chiffres">';
    chiffres.forEach(c=>{
      pris[c.nom]=1;
      const v=cellule(c,c.valeur);
      h+='<div class="tuile"><span class="tl">'+esc(c.label)+'</span>'+
         '<span class="tv '+esc(v.cls)+'">'+v.html+'</span></div>';
    });
    h+='</div>';
  }
  h+='</div>';
  return {html:h,pris:pris};
}

// L'entête de la pièce, puis ses lignes. Les champs que RVGI ne nomme pas
// partent dans un bloc replié : on ne masque rien, on hiérarchise.
function blocPiece(p,idCourant){
  const princ=(p.entete||[]).filter(c=>c.principal);
  const reste=(p.entete||[]).filter(c=>!c.principal);
  let h='<div class="titre-bloc">'+ICO_PIECE+'<span>'+esc(p.label)+'</span>'+
        '<span class="tb-num">'+esc(p.numero)+'</span></div>';

  h+='<div class="sections" id="sec-piece">';
  // Une ligne peut exister sans son entête : RVGI a mis la pièce à la
  // corbeille, ou l'export ne l'a pas ramenée. On le dit, au lieu d'afficher
  // une carte vide qui passerait pour un document sans informations.
  if(!(p.entete||[]).length){
    h+='<div class="liens-vide">L\'entête de cette pièce n\'est pas dans le miroir — '+
       'seules ses lignes le sont.</div></div>';
  }else{
  h+='<div class="groupe pleine champs-cols">'+
     '<div class="groupe-titre"><span>Informations communes</span>'+ICO_CHEV+'</div>'+
     '<div class="groupe-corps">';
  (princ.length?princ:(p.entete||[])).forEach(c=>{
    const v=cellule(c,c.valeur);
    h+='<div class="ligne-champ"><span class="lab">'+esc(c.label)+'</span>'+
       '<span class="val '+esc(v.cls)+'">'+v.html+'</span></div>';
  });
  h+='</div></div>';
  if(princ.length&&reste.length){
    h+='<div class="groupe replie pleine champs-cols">'+
       '<div class="groupe-titre"><span>Autres champs de l\'entête ('+reste.length+')</span>'+ICO_CHEV+'</div>'+
       '<div class="groupe-corps">';
    reste.forEach(c=>{
      const v=cellule(c,c.valeur);
      h+='<div class="ligne-champ"><span class="lab">'+esc(c.label)+'</span>'+
         '<span class="val '+esc(v.cls)+'">'+v.html+'</span></div>';
    });
    h+='</div></div>';
    }
    h+='</div>';
  }

  // Les lignes de la pièce, avec les colonnes de la grille — mais remises
  // dans l'ordre où on lit une pièce : de quoi il s'agit d'abord (numéro,
  // ligne, article), le reste ensuite. Sur la grille, l'ordre est celui que
  // l'utilisateur s'est fabriqué ; ici, c'est le document qui commande.
  const cols=ordonnerColonnesPiece(p.colonnes||[]).slice(0,9);
  h+='<div class="titre-bloc"><span>Lignes de la pièce</span>'+
     '<span class="tb-num">'+fmtNb(p.total,0)+'</span></div>';
  h+='<div class="pl-boite"><table class="pl"><thead><tr>';
  cols.forEach(c=>{h+='<th class="'+(estNum(c)?'num':'')+'">'+esc(c.label)+'</th>';});
  h+='</tr></thead><tbody>';
  (p.lignes||[]).forEach(l=>{
    const ici=String(l._id)===String(idCourant);
    h+='<tr class="pl-ligne'+(ici?' ici':'')+'" data-id="'+esc(l._id)+'"'+
       (ici?' title="La ligne ouverte"':' title="Ouvrir cette ligne"')+'>';
    cols.forEach(c=>{
      const v=cellule(c,l[c.nom]);
      h+='<td class="'+esc(v.cls)+'">'+v.html+'</td>';
    });
    h+='</tr>';
  });
  h+='</tbody></table></div>';
  if(p.tronque){
    h+='<p class="pl-note">'+fmtNb((p.lignes||[]).length,0)+' premières lignes sur '+
       fmtNb(p.total,0)+' — la pièce est plus longue que ce que la fiche affiche.</p>';
  }
  return h;
}

// L'identité d'une ligne passe devant tout le reste : son numéro, son rang
// dans la pièce, et l'article dont il est question.
const TETE_PIECE=['numero','ligne','rang','lignecde','article','code','ref','reference'];
function ordonnerColonnesPiece(cols){
  const rang=c=>{
    const i=TETE_PIECE.indexOf(c.nom);
    if(i>=0)return i;
    // Une colonne composite d'article ne s'appelle pas toujours « article ».
    if(c.type==='ref')return TETE_PIECE.indexOf('article');
    return TETE_PIECE.length+1;
  };
  return cols.map((c,i)=>({c:c,i:i})).sort((a,b)=>(rang(a.c)-rang(b.c))||(a.i-b.i)).map(x=>x.c);
}

function estNum(col){
  const t=col.type||'';
  return t==='qte'||t==='nombre'||t==='prix'||t==='montant'||t==='pct';
}

function brancherEnteteDetail(){
  const r=document.getElementById('d-retour'),x=document.getElementById('d-fermer');
  if(r)r.addEventListener('click',depilerDetail);
  if(x)x.addEventListener('click',fermerDetail);
}

async function chargerLiens(cur,jeton){
  const z=document.getElementById('liens');
  if(!z)return;
  let r;
  try{ r=await api('/api/erp/'+encodeURIComponent(cur.ecran)+'/liens/'+encodeURIComponent(cur.id)); }
  catch(e){
    if(jeton!==S.jetonD)return;
    z.innerHTML='<div class="liens-vide">'+esc(e.message)+'</div>';return;
  }
  if(jeton!==S.jetonD)return;
  const liens=(r.liens||[]).filter(l=>l.erreur||l.total>0);
  if(!liens.length){
    const t=document.getElementById('t-liens');if(t)t.remove();
    z.innerHTML='<div class="liens-vide">Aucune pièce rattachée à cette ligne dans le miroir.</div>';
    return;
  }
  let h='';
  liens.forEach((l,i)=>{
    const cle=Object.keys(l.valeurs||{}).map(k=>k+' '+l.valeurs[k]).join(' · ');
    h+='<div class="lien">'+
       '<div class="lien-tete"><span class="nom">'+esc(l.label)+'</span>'+
         (cle?('<span class="cle">'+esc(cle)+'</span>'):'')+
         '<span class="cpt">'+fmtNb(l.total,0)+'</span></div>';
    if(l.erreur){
      h+='<div class="lien-err">Lien indisponible : '+esc(l.erreur)+'</div></div>';
      return;
    }
    h+='<div class="lien-rows">';
    (l.lignes||[]).forEach(ln=>{
      h+='<div class="lien-row" data-ecran="'+esc(l.ecran)+'" data-id="'+esc(ln._id)+'">';
      (l.colonnes||[]).slice(0,4).forEach(c=>{
        const v=cellule(c,ln[c.nom]);
        h+='<span class="c '+esc(v.cls)+'">'+v.html+'</span>';
      });
      h+='<span class="fl">'+ICO_FLECHE+'</span></div>';
    });
    h+='</div>';
    if(l.total>(l.lignes||[]).length){
      h+='<div class="lien-plus" data-plus="'+i+'" data-ecran="'+esc(l.ecran)+'" data-rang="'+
         esc(String(l.rang))+'">Voir les '+fmtNb(l.total,0)+' →</div>';
    }
    h+='</div>';
  });
  z.innerHTML=h;
  z.querySelectorAll('.lien-row').forEach(el=>{
    el.addEventListener('click',()=>empilerDetail(el.getAttribute('data-ecran'),el.getAttribute('data-id')));
  });
  z.querySelectorAll('[data-plus]').forEach(el=>{
    el.addEventListener('click',()=>{
      const cible=el.getAttribute('data-ecran');
      S.ctxAttente={cible:cible,depuis:cur.ecran,depuis_id:cur.id,lien:Number(el.getAttribute('data-rang'))};
      fermerDetail();
      if(location.hash==='#/'+cible)appliquerHash();else location.hash='#/'+cible;
    });
  });
}

function fermerDetail(){
  const f=document.getElementById('detail-fond'),d=document.getElementById('detail');
  if(f)f.classList.remove('ouvert');
  if(d)d.innerHTML='';
  S.pile=[];S.jetonD++;
  S.selection=null;renderGrille();
}

// ── Recherche globale ────────────────────────────────────────────────────────
// Une seule chaîne, les vingt-sept écrans. Chaque écran déclare déjà sur quoi
// il se cherche ; on ne réinvente pas une seconde règle côté serveur, et le
// résultat trouve donc exactement ce que la recherche de l'écran trouverait.
const RG={ouvert:false,jeton:0,q:'',lignes:[],vise:-1};

function rgOuvrir(){
  const f=document.getElementById('rg-fond');
  if(f){f.classList.add('ouvert');RG.ouvert=true;}
}
function rgFermer(){
  const f=document.getElementById('rg-fond');
  if(f){f.classList.remove('ouvert');}
  RG.ouvert=false;RG.vise=-1;
}
function rgPanneau(html){
  const p=document.getElementById('rg-panneau');
  if(p)p.innerHTML=html;
}

function rgSurligner(txt,q){
  const s=String(txt==null?'':txt);
  const i=s.toLowerCase().indexOf(String(q||'').toLowerCase());
  if(i<0||!q)return esc(s);
  return esc(s.slice(0,i))+'<mark>'+esc(s.slice(i,i+q.length))+'</mark>'+esc(s.slice(i+q.length));
}

async function rgChercher(q){
  RG.q=q;
  const jeton=++RG.jeton;
  if(String(q||'').trim().length<2){
    if(String(q||'').trim().length===0){rgFermer();return;}
    rgOuvrir();rgPanneau('<div class="rg-msg">Au moins deux caractères.</div>');return;
  }
  rgOuvrir();
  rgPanneau('<div class="rg-msg">Recherche dans les écrans…</div>');
  let r;
  try{ r=await api('/api/erp/recherche?q='+encodeURIComponent(q)); }
  catch(e){
    if(jeton!==RG.jeton)return;
    rgPanneau('<div class="rg-msg">'+esc(e.message)+'</div>');return;
  }
  if(jeton!==RG.jeton)return;   // une frappe plus récente a déjà relancé
  rgRendre(r);
}

function rgRendre(r){
  const groupes=r.resultats||[];
  const nb=groupes.reduce((n,g)=>n+(g.lignes||[]).length,0);
  RG.lignes=[];
  let h='<div class="rg-tete"><b>'+esc(r.q)+'</b>'+
        '<span class="cpt">'+(nb?fmtNb(nb,0)+' résultat'+(nb>1?'s':'')+' dans '+
        fmtNb(groupes.length,0)+' écran'+(groupes.length>1?'s':''):'aucun résultat')+'</span></div>';
  if(r.tronque){
    h+='<div class="rg-note">Recherche interrompue avant d\'avoir vu tous les écrans — '+
       'affine la chaîne pour aller au bout.</div>';
  }
  if(!groupes.length){
    h+='<div class="rg-msg">Rien qui contienne « '+esc(r.q)+' » dans le miroir.<br>'+
       '<span class="mini">Le miroir a jusqu\'à douze heures de retard : une pièce saisie ce matin peut ne pas y être.</span></div>';
    rgPanneau(h);return;
  }
  groupes.forEach(g=>{
    h+='<div class="rg-groupe"><div class="rg-groupe-tete">'+iconeEcran(g.cle)+
       '<span>'+esc(g.label)+'</span>'+
       '<span class="n">'+fmtNb((g.lignes||[]).length,0)+(g.encore?'+':'')+'</span></div>';
    (g.lignes||[]).forEach(l=>{
      const i=RG.lignes.length;
      RG.lignes.push({ecran:g.cle,id:l._id});
      h+='<div class="rg-ligne" data-i="'+i+'">';
      (g.colonnes||[]).forEach(c=>{
        const v=cellule(c,l[c.nom]);
        // On surligne ce qui a été tapé, mais seulement sur du texte simple :
        // une date formatée ou un badge d'énumération ne se découpent pas.
        const html=(c.type==='texte'||c.type==='client'||c.type==='ref'||c.type==='of')
          ? rgSurligner(l[c.nom],RG.q) : v.html;
        h+='<span class="c '+esc(v.cls)+'">'+html+'</span>';
      });
      h+='</div>';
    });
    if(g.encore){
      h+='<div class="rg-plus" data-ecran="'+esc(g.cle)+'">Ouvrir '+esc(g.label)+
         ' avec cette recherche →</div>';
    }
    h+='</div>';
  });
  rgPanneau(h);
  const p=document.getElementById('rg-panneau');
  p.querySelectorAll('.rg-ligne').forEach(el=>{
    el.addEventListener('click',()=>rgAller(Number(el.getAttribute('data-i'))));
  });
  p.querySelectorAll('[data-ecran]').forEach(el=>{
    el.addEventListener('click',()=>rgOuvrirEcran(el.getAttribute('data-ecran')));
  });
}

// Ouvrir un résultat, c'est ouvrir sa fiche — pas seulement son écran. On passe
// donc par l'écran (la grille doit exister derrière la modale), puis on
// déplie la ligne trouvée.
function rgAller(i){
  const cible=RG.lignes[i];
  if(!cible)return;
  rgFermer();
  const suite=()=>{
    charger();      // la grille doit exister derrière la fiche
    S.pile=[{ecran:cible.ecran,id:cible.id}];S.selection=cible.id;rendreDetail();
  };
  if(S.ecran===cible.ecran){suite();return;}
  S.apresEcran=suite;
  location.hash='#/'+cible.ecran;
}

function rgOuvrirEcran(cle){
  const q=RG.q;
  rgFermer();
  S.apresEcran=()=>{
    S.q=q;const c=document.getElementById('q');
    if(c)c.value=q;
    S.page=1;charger();
  };
  if(location.hash==='#/'+cle)appliquerHash();else location.hash='#/'+cle;
}

function initRecherche(){
  const i=document.getElementById('rg-q'),f=document.getElementById('rg-fond');
  if(!i)return;
  let m=null;
  i.addEventListener('input',()=>{clearTimeout(m);m=setTimeout(()=>rgChercher(i.value),260);});
  i.addEventListener('keydown',e=>{
    if(e.key==='Escape'){i.value='';rgFermer();i.blur();return;}
    if(e.key==='Enter'&&RG.vise>=0){e.preventDefault();rgAller(RG.vise);return;}
    if(e.key!=='ArrowDown'&&e.key!=='ArrowUp')return;
    e.preventDefault();
    if(!RG.lignes.length)return;
    RG.vise=(e.key==='ArrowDown')
      ? Math.min(RG.lignes.length-1,RG.vise+1)
      : Math.max(0,RG.vise-1);
    const p=document.getElementById('rg-panneau');
    p.querySelectorAll('.rg-ligne').forEach(el=>el.classList.remove('vise'));
    const el=p.querySelector('.rg-ligne[data-i="'+RG.vise+'"]');
    if(el){el.classList.add('vise');el.scrollIntoView({block:'nearest'});}
  });
  i.addEventListener('focus',()=>{if(RG.lignes.length&&i.value.trim().length>=2)rgOuvrir();});
  if(f)f.addEventListener('click',ev=>{if(ev.target===f)rgFermer();});
  document.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&(e.key==='k'||e.key==='K')){e.preventDefault();i.focus();i.select();}
  });
}

// ── Shell ────────────────────────────────────────────────────────
function basculerSidebar(){document.body.classList.toggle('sb-open');}
function fermerSidebar(){document.body.classList.remove('sb-open');}
function majTheme(){
  const clair=document.body.classList.contains('light');
  const i=document.getElementById('theme-ico'),l=document.getElementById('theme-label');
  if(i)i.innerHTML=clair?ICO_MOON:ICO_SUN;
  if(l)l.textContent=clair?'Mode sombre':'Mode clair';
  // Le bouton de l'en-tête montre la même chose que celui du tiroir.
  const h=document.getElementById('hd-theme');
  if(h)h.innerHTML=clair?ICO_MOON:ICO_SUN;
}
function basculerTheme(){
  document.body.classList.toggle('light');
  try{localStorage.setItem('mysifa_theme',document.body.classList.contains('light')?'light':'dark');}catch(e){}
  majTheme();
}
async function deconnexion(){
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
}
function allerAuMenu(){
  fermerSidebar();
  if(location.hash&&location.hash!=='#/'){location.hash='';}   // hashchange fera le reste
  else{ouvrirMenu();}
}

function appliquerHash(){
  fermerDetail();   // on ne garde jamais une modale ouverte sur un autre écran
  const m=String(location.hash||'').match(/^#\/([a-z_]+)$/);
  if(m&&S.meta&&S.meta.present){ouvrirEcran(m[1]);}else{ouvrirMenu();}
  fermerSidebar();
}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    if(RG.ouvert){rgFermer();return;}
    if(document.body.classList.contains('sb-open')){fermerSidebar();return;}
    const f=document.getElementById('detail-fond');
    if(f&&f.classList.contains('ouvert')){
      // Échap remonte d'un cran dans le fil, puis referme.
      if(S.pile.length>1)depilerDetail();else fermerDetail();
    }
  }
});

async function boot(){
  try{if(localStorage.getItem('mysifa_theme')==='light')document.body.classList.add('light');}catch(e){}
  majTheme();
  const brancher=(id,fn)=>{const el=document.getElementById(id);if(el)el.addEventListener('click',fn);};
  brancher('btn-theme',basculerTheme);
  brancher('hd-theme',basculerTheme);
  brancher('btn-logout',deconnexion);
  brancher('hd-logout',deconnexion);
  brancher('hd-profil',()=>{location.href='/profil';});
  // Cliquer le fond referme : le geste attendu d'une modale.
  const fond=document.getElementById('detail-fond');
  if(fond)fond.addEventListener('click',ev=>{if(ev.target===fond)fermerDetail();});
  brancher('hd-retour',()=>{location.href='/';});
  try{
    const me=await api('/api/auth/me');
    const chip=document.getElementById('uc');
    // Le meme composant que MyStock et MyProd : avatar, nom, role, « Mon profil ».
    if(chip&&window.MySifaUserChip&&MySifaUserChip.fill){
      MySifaUserChip.fill(chip,me,{});
    }else{
      const n=document.getElementById('uc-name'),ro=document.getElementById('uc-role');
      if(n)n.textContent=me.nom||me.email||'—';
      if(ro)ro.textContent=me.role||'—';
    }
  }catch(e){}

  const bs=document.getElementById('btn-support');
  if(bs){
    const ico=document.getElementById('support-ico');
    if(ico&&window.MySifaSupport&&MySifaSupport.iconSvg)ico.innerHTML=MySifaSupport.iconSvg();
    if(window.MySifaSupport&&MySifaSupport.open){
      bs.addEventListener('click',()=>MySifaSupport.open());
    }else{
      bs.style.display='none';   // pas de widget chargé : pas de bouton mort
    }
  }
  try{ S.meta=await api('/api/erp/meta'); }
  catch(e){
    document.getElementById('corps').innerHTML='<div class="vide-msg">'+esc(e.message)+'</div>';
    return;
  }
  renderFraicheur();renderNav();initRecherche();appliquerHash();
  window.addEventListener('hashchange',appliquerHash);
  initGuides();
}
boot();
</script>

</body>
</html>
"""
