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
:root{--serie2:#a78bfa;--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--accent-bord:rgba(34,211,238,.45);--ok:#34d399;--success:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--serie2:#6d4ddb;--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--accent-bord:rgba(8,145,178,.42);--ok:#059669;--success:#059669;--danger:#dc2626;--warn:#d24b00}
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
.badge.r-oui{background:rgba(52,211,153,.16);color:var(--ok)}
.badge.r-partiel{background:rgba(251,191,36,.16);color:var(--warn)}
.badge.r-douteux{background:rgba(248,113,113,.16);color:var(--danger)}
.pied{display:flex;align-items:center;gap:12px;padding:10px 16px;border-top:1px solid var(--border);background:var(--card);font-size:12px;color:var(--muted)}
.pied .compte{font-variant-numeric:tabular-nums}
.pied .pager{margin-left:auto;display:flex;align-items:center;gap:6px}
.vide-msg{padding:40px 26px;color:var(--muted);font-size:13px}

/* ── Détail : une modale par-dessus la grille ── */
.detail-fond{position:fixed;inset:0;z-index:70;display:none;align-items:center;justify-content:center;padding:22px;
  background:rgba(2,6,23,.66)}
body.light .detail-fond{background:rgba(15,23,42,.5)}
.detail-fond.ouvert{display:flex}
.detail{width:min(1520px,96vw);max-height:90vh;display:flex;flex-direction:column;
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
/* Deux colonnes : la pièce à gauche, ce qui s'y rattache à droite.
   Les pièces liées étaient au bas d'une modale qu'il fallait dérouler pour
   les voir — donc, en pratique, jamais vues. Elles tiennent maintenant leur
   propre colonne, visible dès l'ouverture, et le rail reste collé en haut
   pendant qu'on descend dans les champs de la ligne. */
.detail-corps.deux-col{display:grid;grid-template-columns:minmax(0,1fr) 380px;
  gap:0 18px;align-items:start}
.detail-principal{min-width:0}
.detail-rail{min-width:0;position:sticky;top:0;max-height:calc(90vh - 96px);
  overflow-y:auto;padding-bottom:6px}
.detail-rail::-webkit-scrollbar{width:6px}
.detail-rail::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
/* Dans le rail, les cartes de liens s'empilent : 380 px n'en tiennent qu'une. */
.detail-rail .liens{grid-template-columns:1fr}
@media (max-width:1180px){
  .detail-corps.deux-col{display:block}
  .detail-rail{position:static;max-height:none;overflow:visible}
}
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
/* Le tableau porte tout le détail de la ligne : il défile horizontalement, et
   les deux colonnes d'identité restent visibles pendant qu'on défile. Sans
   elles, à la dixième colonne on ne sait plus quelle ligne on lit. */
.pl-boite.pl-large{max-height:340px}
table.pl th.fx,table.pl td.fx{position:sticky;z-index:2;background:var(--card)}
table.pl th.fx{z-index:3;background:var(--bg)}
table.pl th.fx0,table.pl td.fx0{left:0}
/* Le décalage de la 2e colonne figée est mesuré après le rendu : la largeur de
   la 1re dépend du contenu, et une valeur en dur la faisait chevaucher. */
table.pl th.fx1,table.pl td.fx1{left:var(--fx1,96px)}
table.pl td.fx1{box-shadow:1px 0 0 var(--border)}
table.pl th.fx1{box-shadow:1px 0 0 var(--border)}
table.pl tbody tr:hover td.fx,table.pl tbody tr.ici td.fx{background:var(--accent-bg)}
table.pl td{max-width:210px}
.pl-astuce{order:3;font-size:10.5px;font-weight:600;letter-spacing:0;text-transform:none;
  color:var(--muted);white-space:nowrap}

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
  background:var(--card);border:1.5px solid var(--accent-bord);border-radius:10px;padding:0 11px;
  height:38px;min-width:260px;max-width:440px;flex:1 1 320px;
  box-shadow:inset 0 1px 2px rgba(0,0,0,.14)}
body.light .rg{background:#fff;box-shadow:inset 0 1px 2px rgba(15,23,42,.06)}
.rg:hover{border-color:var(--accent)}
.rg:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.rg-ico{color:var(--accent);flex-shrink:0;opacity:.85}
.rg input{flex:1;min-width:0;background:none;border:none;outline:none;color:var(--text);
  font:inherit;font-size:13.5px;padding:0}
.rg input::placeholder{color:var(--muted)}
.rg input::-webkit-search-cancel-button{filter:grayscale(1) opacity(.6)}
.rg-kbd{flex-shrink:0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;
  color:var(--muted);border:1px solid var(--border);border-radius:5px;padding:2px 5px;background:var(--card)}
.rg:focus-within .rg-kbd{display:none}

.rg-fond{position:fixed;inset:0;z-index:75;display:none;background:rgba(2,6,23,.5);
  padding:76px 22px 22px;justify-content:center;align-items:flex-start}
body.light .rg-fond{background:rgba(15,23,42,.4)}
.rg-fond.ouvert{display:flex}
.rg-panneau{width:min(940px,96vw);max-height:calc(100vh - 110px);overflow-y:auto;
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  box-shadow:0 24px 70px rgba(0,0,0,.5);padding:8px 0 10px}
.rg-tete{display:flex;align-items:baseline;gap:10px;padding:8px 16px 10px;
  border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--card);z-index:1}
.rg-tete b{font-family:inherit;font-size:13px}
.rg-tete .cpt{margin-left:auto;font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.rg-groupe{padding:0}
.rg-groupe-tete{display:flex;align-items:center;gap:8px;padding:11px 16px 7px;background:var(--bg);
  border-top:1px solid var(--border);border-bottom:1px solid var(--border);
  font-family:Archivo,inherit;font-size:10.5px;font-weight:800;letter-spacing:.7px;
  text-transform:uppercase;color:var(--muted)}
.rg-groupe-tete .n{margin-left:auto;background:var(--accent-bg);color:var(--accent);
  border-radius:999px;padding:1px 8px;font-size:10.5px;text-transform:none;letter-spacing:0}
.rg-ligne{display:grid;grid-template-columns:140px minmax(0,1fr) auto;gap:4px 16px;align-items:baseline;
  padding:9px 16px 9px 14px;font-size:12.5px;color:var(--text2);cursor:pointer;
  border-left:3px solid transparent;border-top:1px solid var(--border)}
.rg-groupe .rg-ligne:first-of-type{border-top:none}
.rg-ligne:hover,.rg-ligne.vise{background:var(--accent-bg);color:var(--text);border-left-color:var(--accent)}
/* La 1re colonne identifie (numéro, référence), la 2e décrit, la 3e chiffre.
   Sans cette grille, cinq colonnes de largeurs libres s'alignaient au hasard
   d'un écran à l'autre et la liste devenait illisible. */
.rg-ligne .c{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rg-ligne .c1{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;font-size:13px;color:var(--accent)}
.rg-ligne .c2{color:var(--text);font-weight:600}
.rg-ligne .c3{grid-column:2;font-size:11.5px;color:var(--muted);font-weight:400}
.rg-ligne .cn{grid-column:3;grid-row:1;text-align:right;font-variant-numeric:tabular-nums;
  color:var(--text2);white-space:nowrap}
.rg-ligne .cd{grid-column:3;grid-row:2;text-align:right;font-size:11.5px;color:var(--muted);white-space:nowrap}
.rg-ligne mark{background:rgba(251,191,36,.28);color:inherit;border-radius:3px;padding:0 2px;font-weight:700}
body.light .rg-ligne mark{background:rgba(217,119,6,.22)}
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
/* ── Menu de service : au survol de la marque RVGI ────────────────────────
   Le tiroir montre les 27 écrans ; ce menu-ci montre les cinq qu'on ouvre
   vraiment, plus les tableaux de bord. Il tient au survol ET au clic : la
   souris pour l'habitude, le clic pour le tactile et le clavier. */
.mk-svc{position:relative;flex-shrink:0;display:flex}
.mk-btn{display:inline-flex;align-items:center;gap:5px;background:none;border:1px solid transparent;border-radius:10px;padding:3px 7px 3px 5px;cursor:pointer;color:var(--muted);font:inherit;transition:background .15s,border-color .15s}
.mk-btn:hover,.mk-svc.ouvert .mk-btn{background:var(--accent-bg);border-color:var(--accent-bord)}
.mk-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.mk-chev{font-size:9px;line-height:1;opacity:.75;transition:transform .15s}
.mk-svc:hover .mk-chev,.mk-svc.ouvert .mk-chev{transform:translateY(1px);opacity:1;color:var(--accent)}
.mk-pop{position:absolute;top:100%;left:0;margin-top:7px;min-width:300px;max-width:350px;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:0 18px 46px rgba(0,0,0,.45);padding:6px;z-index:90;display:none}
.mk-svc:hover .mk-pop,.mk-svc:focus-within .mk-pop,.mk-svc.ouvert .mk-pop{display:block}
/* Pont invisible : descendre la souris vers le menu ne doit pas le refermer. */
.mk-pop::before{content:'';position:absolute;top:-9px;left:0;right:0;height:9px}
.mk-groupe{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:9px 10px 5px}
.mk-item{display:flex;align-items:flex-start;gap:10px;width:100%;text-align:left;background:none;border:none;border-radius:9px;padding:8px 10px;cursor:pointer;color:var(--text2);font:inherit;transition:background .12s,color .12s}
.mk-item:hover{background:var(--accent-bg)}
.mk-item .mk-ico{flex-shrink:0;margin-top:2px;opacity:.8;color:var(--muted)}
.mk-item:hover .mk-ico{color:var(--accent);opacity:1}
.mk-item b{display:block;font-size:12.5px;font-weight:600;color:var(--text)}
.mk-item:hover b{color:var(--accent)}
.mk-item em{display:block;font-style:normal;font-size:11px;color:var(--muted);line-height:1.42;margin-top:2px}
.mk-item.tdb b{font-size:13.5px}
.mk-item.active b{color:var(--accent)}
.mk-sep{height:1px;background:var(--border);margin:6px 8px}

/* ── Tableaux de bord ─────────────────────────────────────────────────────
   Une vue de plus dans `#corps`, à côté du menu et de la grille. Le body ne
   défile pas : c'est cette enveloppe qui roule. */
.tdb-wrap{flex:1;min-height:0;overflow-y:auto;padding:15px 17px 30px}
.tdb-charge{padding:40px;text-align:center;color:var(--muted);font-size:13px}
.tdb-alerte{display:flex;align-items:flex-start;gap:9px;padding:10px 13px;border-radius:10px;border:1px solid rgba(251,191,36,.32);background:rgba(251,191,36,.08);color:var(--text2);font-size:12px;line-height:1.5;margin-bottom:12px}
.tdb-alerte b{color:var(--text)}

.tdb-bande{display:flex;flex-wrap:wrap;align-items:center;gap:10px 22px;padding:14px 16px;border-radius:12px;border:1px solid var(--accent-bord);background:var(--accent-bg);margin-bottom:13px}
.tdb-bande .lab{display:block;font-size:10.5px;font-weight:700;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);margin-bottom:7px}
.tdb-bande .big{display:block;font-size:29px;font-weight:800;letter-spacing:-.02em;line-height:1;font-variant-numeric:tabular-nums;color:var(--text)}
.tdb-bande .txt{font-size:12.5px;color:var(--text2);line-height:1.45}
.tdb-bande .txt b{color:var(--text)}
.tdb-bande .droite{margin-left:auto;text-align:right;font-size:11.5px;color:var(--muted);line-height:1.5}
.tdb-bande .droite b{display:block;font-size:12.5px;font-weight:700}

.tdb-tuiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(186px,1fr));gap:11px;margin-bottom:13px}
.tdb-tuile{position:relative;overflow:hidden;text-align:left;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:13px 14px 14px;color:var(--text2);font:inherit;cursor:pointer;transition:border-color .15s,transform .12s}
.tdb-tuile[data-inerte]{cursor:default}
.tdb-tuile:not([data-inerte]):hover{border-color:var(--accent-bord);transform:translateY(-1px)}
.tdb-tuile:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tdb-tuile::after{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:var(--accent);opacity:.5}
.tdb-tuile.ok::after{background:var(--ok);opacity:.8}
.tdb-tuile.warn::after{background:var(--warn);opacity:.9}
.tdb-tuile.dg::after{background:var(--danger);opacity:.9}
.tdb-tuile.neu::after{background:var(--border);opacity:1}
.tdb-tuile .k{display:block;font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;line-height:1.3}
.tdb-tuile .v{display:block;font-size:25px;font-weight:800;letter-spacing:-.02em;line-height:1;font-variant-numeric:tabular-nums;color:var(--text)}
.tdb-tuile .v small{font-size:13px;font-weight:600;color:var(--text2);margin-left:2px}
.tdb-tuile .s{display:block;margin-top:7px;font-size:11px;color:var(--muted);line-height:1.4}
.tdb-tuile .s.ok{color:var(--ok)}
.tdb-tuile .s.warn{color:var(--warn)}
.tdb-tuile .s.dg{color:var(--danger)}

.tdb-cols{display:grid;grid-template-columns:2fr 1fr;gap:11px;align-items:start}
@media(max-width:1150px){.tdb-cols{grid-template-columns:1fr}}
.tdb-pile{display:flex;flex-direction:column;gap:11px;min-width:0}
.tdb-pan{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.tdb-pan-h{display:flex;align-items:center;gap:9px;padding:10px 13px;border-bottom:1px solid var(--border)}
.tdb-pan-h h3{margin:0;font-size:12.5px;font-weight:700;color:var(--text)}
.tdb-pan-h .cpt{font-size:11px;color:var(--muted)}
.tdb-pan-h .plus{margin-left:auto;font-size:11.5px;color:var(--accent);background:none;border:none;cursor:pointer;font:inherit;padding:2px 4px;border-radius:6px;white-space:nowrap}
.tdb-pan-h .plus:hover{background:var(--accent-bg)}
.tdb-note{padding:9px 13px;border-top:1px solid var(--border);font-size:10.5px;color:var(--muted);line-height:1.5}
.tdb-vide{padding:20px 13px;text-align:center;color:var(--muted);font-size:12px}

table.tdb-t{width:100%;border-collapse:collapse;font-size:12px}
table.tdb-t th{text-align:left;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding:7px 11px;border-bottom:1px solid var(--border);white-space:nowrap}
table.tdb-t td{padding:8px 11px;border-bottom:1px solid var(--border);color:var(--text2);white-space:nowrap}
table.tdb-t tr:last-child td{border-bottom:none}
table.tdb-t tr[data-ouvre]{cursor:pointer}
table.tdb-t tr[data-ouvre]:hover td{background:var(--accent-bg);color:var(--accent)}
table.tdb-t td.n,table.tdb-t th.n{text-align:right;font-variant-numeric:tabular-nums}
table.tdb-t td.ref{color:var(--accent);font-weight:600}
table.tdb-t td.fort{color:var(--text);font-weight:500}
table.tdb-t td.coupe{max-width:170px;overflow:hidden;text-overflow:ellipsis}

.tdb-etiq{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;white-space:nowrap;background:var(--border);color:var(--text2)}
.tdb-etiq.ok{background:rgba(52,211,153,.14);color:var(--ok)}
.tdb-etiq.warn{background:rgba(251,191,36,.15);color:var(--warn)}
.tdb-etiq.dg{background:rgba(248,113,113,.15);color:var(--danger)}
.tdb-etiq i{width:5px;height:5px;border-radius:50%;background:currentColor;display:block}

/* Contrôles MySifa : chaque ligne est un compteur ET la porte de l'écran qui
   le corrige. Les deux viennent de la même route — ils ne peuvent pas mentir
   l'un sur l'autre. */
.tdb-ctrl{display:flex;align-items:center;gap:11px;width:100%;text-align:left;padding:10px 13px;background:none;border:none;border-bottom:1px solid var(--border);color:var(--text2);font:inherit;cursor:pointer;transition:background .12s}
.tdb-ctrl:last-child{border-bottom:none}
.tdb-ctrl:hover{background:var(--accent-bg)}
.tdb-ctrl .tt{min-width:0;flex:1}
.tdb-ctrl b{display:block;font-size:12px;font-weight:600;color:var(--text)}
.tdb-ctrl:hover b{color:var(--accent)}
.tdb-ctrl em{display:block;font-style:normal;font-size:10.5px;color:var(--muted);line-height:1.4;margin-top:2px;white-space:normal}
.tdb-ctrl .n{flex-shrink:0;font-size:17px;font-weight:800;font-variant-numeric:tabular-nums;color:var(--text);min-width:34px;text-align:right}
.tdb-ctrl .n.ok{color:var(--ok)}
.tdb-ctrl .n.warn{color:var(--warn)}
.tdb-ctrl .n.dg{color:var(--danger)}
.tdb-ctrl .n.vide{color:var(--muted);font-size:14px;font-weight:600}
.tdb-ctrl .ext{flex-shrink:0;opacity:.5}
.tdb-ctrl:hover .ext{opacity:1;color:var(--accent)}

/* Graphiques : deux séries, une seule échelle. Jamais deux axes. */
.tdb-graph{padding:13px}
.tdb-leg{display:flex;flex-wrap:wrap;gap:7px 17px;padding-bottom:11px;font-size:11px;color:var(--text2)}
.tdb-leg span{display:inline-flex;align-items:center;gap:6px}
.tdb-leg i{width:10px;height:10px;border-radius:2px;display:block}
.tdb-barres{display:flex;align-items:flex-end;gap:8px;height:130px;padding-bottom:5px;border-bottom:1px solid var(--border)}
.tdb-barres .grp{flex:1;display:flex;align-items:flex-end;justify-content:center;gap:2px;height:100%;position:relative;min-width:0}
.tdb-barres .grp i{display:block;width:46%;border-radius:3px 3px 0 0;min-height:2px}
.tdb-barres .grp i.a{background:var(--serie2)}
.tdb-barres .grp i.b{background:var(--accent)}
.tdb-axe{display:flex;gap:8px;padding-top:6px}
.tdb-axe span{flex:1;text-align:center;font-size:9.5px;color:var(--muted);overflow:hidden}
.tdb-jours{display:flex;align-items:flex-end;gap:2px;height:64px;border-bottom:1px solid var(--border);padding:0 13px 4px}
.tdb-jours i{flex:1;display:block;border-radius:2px 2px 0 0;background:var(--accent);opacity:.55;min-height:2px}
.tdb-jours i.dernier{opacity:1;background:var(--serie2)}
.tdb-jours-pied{display:flex;justify-content:space-between;padding:6px 13px 0;font-size:10px;color:var(--muted)}

.tdb-hb{display:flex;flex-direction:column;gap:10px;padding:12px 13px 14px}
.tdb-hb .l{display:grid;grid-template-columns:1fr auto;gap:3px 10px;align-items:center}
.tdb-hb .nom{font-size:11.5px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tdb-hb .val{font-size:11.5px;color:var(--text);font-variant-numeric:tabular-nums}
.tdb-hb .piste{grid-column:1/-1;height:7px;border-radius:4px;background:var(--border);overflow:hidden}
.tdb-hb .piste i{display:block;height:100%;border-radius:4px;background:var(--accent);min-width:2px}

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
      <div class="mk-svc" id="mk-svc">
        <button type="button" class="head-mark rvgi-mark mk-btn" id="mk-btn"
                aria-haspopup="true" aria-expanded="false"
                title="Les écrans de mon service" aria-label="Les écrans de mon service">
          <img class="rvgi-sombre" src="/static/rvgi_mark_clair.png?v=3" alt="RVGI">
          <img class="rvgi-clair" src="/static/rvgi_mark.png?v=3" alt="RVGI">
          <span class="mk-chev" aria-hidden="true">&#9662;</span>
        </button>
        <div class="mk-pop" id="mk-pop" role="menu"></div>
      </div>
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
  ratt: '',           // filtre sur l'état de rattachement MySifa
};

const ICO_SUN='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICO_MOON='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function toast(msg,type){const t=document.createElement('div');t.className='toast'+(type==='err'?' err':'');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3400);}
async function api(url,opts){
  const r=await fetch(url,Object.assign({credentials:'include'},opts||{}));
  if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}
  return r.json();
}

// ── Formats ──────────────────────────────────────────────────────
function fmtNb(v,dec){
  const n=Number(v);
  if(!isFinite(n))return esc(v);
  return n.toLocaleString('fr-FR',{minimumFractionDigits:dec||0,maximumFractionDigits:dec==null?2:dec});
}
// Un numéro de pièce, écrit comme RVGI l'écrit : sans séparateur de milliers,
// et sans décimale parasite quand la colonne SQL est un réel (9938471.0).
function fmtId(v){
  const n=Number(v);
  if(!isFinite(n))return String(v==null?'':v);
  return String(Number.isInteger(n)?n:v);
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
  if((col.type||'')==='ratt')return celluleRatt(v);
  if(v==null||v==='')return{cls:'vide',html:'—'};
  const t=col.type||'texte';
  if(t==='date')     return {cls:'',     html:fmtDate(v)};
  if(t==='datetime') return {cls:'mono', html:fmtDateHeure(v)};
  if(t==='of')       return {cls:'of',   html:esc(v)};
  // Un numéro de pièce s'écrit tel qu'il est tapé et recopié : « 26060187 »,
  // jamais « 26 060 187 ». Il s'aligne à droite comme un nombre — deux numéros
  // l'un sous l'autre se comparent alors chiffre à chiffre.
  if(t==='id')       return {cls:'mono num', html:esc(fmtId(v))};
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

// L'état de rattachement : « rattaché » ne veut pas dire « couvert ». Une
// ligne prise à moitié doit se lire comme telle, avec le chiffre — sinon la
// colonne ne dit que « quelqu'un s'en est occupé », ce qui n'aide personne.
const RATT_LIB={oui:'Rattaché',partiel:'Partiel',douteux:'À vérifier',non:'—'};
function celluleRatt(v){
  const e=(v&&v.etat)||'non';
  if(e==='non')return {cls:'vide',html:'—'};
  let txt=RATT_LIB[e]||e;
  if(e==='partiel'&&v.total){
    txt+=' '+fmtNb(v.pris,0)+' / '+fmtNb(v.total,0);
  }else if(v.n>1){
    txt+=' ×'+v.n;
  }
  return {cls:'',html:'<span class="badge r-'+esc(e)+'">'+esc(txt)+'</span>'};
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
  const d=((S.meta&&S.meta.domaines)||[]).slice();
  return d.filter(x=>x.type!=='parametres').concat(d.filter(x=>x.type==='parametres'));
}

// MyERP ne montre QUE ce que le miroir contient. Les domaines viennent du
// catalogue, qui vient de RVGI — aucun écran n'est ajouté ici. Voir CLAUDE.md,
// « MyERP est un miroir ».
function ecransDuDomaine(cle){
  return (S.meta.ecrans||[]).filter(e=>e.domaine===cle);
}

function renderNav(){
  const hote=document.getElementById('nav-ecrans');
  if(!S.meta||!S.meta.present){hote.innerHTML='';return;}
  let h='<div class="nav-colonnes">';
  domainesOrdonnes().forEach(d=>{
    const ecrans=ecransDuDomaine(d.cle);
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
  renderNav();renderMenuService();
  const corps=document.getElementById('corps');
  if(!S.meta||!S.meta.present){
    corps.innerHTML='<div class="vide-msg">'+esc((S.meta&&S.meta.message)||'Miroir indisponible.')+'</div>';
    return;
  }
  let h='<div class="menu-wrap">';
  const tdb=((S.meta&&S.meta.menu)||{}).tdb||[];
  if(tdb.length){
    h+='<div class="colonnes" style="margin-bottom:4px"><div class="colonne parametres">'+
       '<div class="domaine-titre">Tableaux de bord</div><div class="cartes">';
    tdb.forEach(t=>{
      h+='<div class="carte" data-ecran="'+esc(t.cle)+'" title="'+esc(t.resume||'')+'">'+
         '<span class="carte-ico">'+ICO_TDB.replace(' class="mk-ico"','')+'</span>'+
         '<span class="carte-titre">'+esc(t.label)+'</span></div>';
    });
    h+='</div></div></div>';
  }
  h+='<div class="colonnes">';
  domainesOrdonnes().forEach(d=>{
    const ecrans=ecransDuDomaine(d.cle);
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
function ouvrirEcran(cle,prefiltres){
  const def=((S.meta&&S.meta.ecrans)||[]).find(e=>e.cle===cle);
  if(!def){toast('Écran inconnu.','err');ouvrirMenu();return;}
  S.ecran=cle;S.def=def;S.page=1;S.tri=null;S.sens='asc';S.q='';S.filtres={};S.selection=null;S.colonnes=[];S.epingles=[];
  // Un contexte de pièce liée n'est valable que pour l'écran qu'il vise, et
  // pour une seule ouverture : on le consomme ici.
  S.contexte=(S.ctxAttente&&S.ctxAttente.cible===cle)?S.ctxAttente:null;
  S.ctxAttente=null;
  S.ratt='';
  // Un écran s'ouvre sur ce qui est vivant : le filtre qui porte un défaut
  // (Position = En cours) est appliqué d'entrée, et reste effaçable. Venant
  // d'une pièce liée, non : on veut la pièce, même soldée.
  if(!S.contexte){
    (def.filtres||[]).forEach(f=>{
      if(f.defaut!=null&&f.defaut!=='')S.filtres[f.nom]=String(f.defaut);
    });
  }
  // Les filtres venus du hash passent APRÈS les défauts du catalogue : une
  // tuile qui vise « position = toutes » doit pouvoir effacer le défaut
  // « En cours », pas s'y ajouter. `q` et `ratt` ne sont pas des filtres de
  // colonne, ils ont leur propre état.
  if(prefiltres){
    Object.keys(prefiltres).forEach(k=>{
      const v=prefiltres[k];
      if(k==='q'){S.q=String(v||'');}
      else if(k==='ratt'){S.ratt=String(v||'');}
      else{S.filtres[k]=String(v==null?'':v);}
    });
  }
  document.getElementById('titre').textContent=def.label;
  document.getElementById('sous').textContent=def.resume||'';
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=def.label;
  renderNav();renderMenuService();

  // Rail construit UNE fois par écran. Les rafraîchissements de liste ne le
  // touchent pas : le champ de recherche garde son focus et son curseur.
  let rail='<div class="rail"><div class="rail-titre">Recherche</div>'+
    '<div class="champ"><input type="text" id="q" placeholder="Rechercher..." autocomplete="off" value="'+esc(S.q||'')+'"></div>';
  if(def.rattachable){
    rail+='<div class="rail-titre">Rattachement MySifa</div>'+
      '<div class="champ"><label for="f-ratt">'+
      (cle==='livraisons'?'Départ MyExpé':'Dossier de fabrication')+'</label>'+
      '<select id="f-ratt">'+
        ['','non','partiel','oui','douteux'].map((v,i)=>
          '<option value="'+v+'"'+((S.ratt||'')===v?' selected':'')+'>'+
          ['Tous','Non rattaché','Partiellement','Rattaché','À vérifier'][i]+'</option>').join('')+
      '</select></div>';
  }
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
  const fr=document.getElementById('f-ratt');
  if(fr)fr.addEventListener('change',()=>{S.ratt=fr.value;S.page=1;charger();});
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
    S.q='';S.filtres={};S.page=1;S.ratt='';
    const r=document.getElementById('f-ratt');if(r)r.value='';
    (def.filtres||[]).forEach(f=>{
      if(f.defaut!=null&&f.defaut!=='')S.filtres[f.nom]=String(f.defaut);
    });
    const c=document.getElementById('q');if(c)c.value='';
    const fr=document.getElementById('f-ratt');
  if(fr)fr.addEventListener('change',()=>{S.ratt=fr.value;S.page=1;charger();});
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
  if(S.ratt)p.set('ratt',S.ratt);
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
  // La colonne de rattachement n'est pas une colonne de RVGI : c'est ce que
  // MySifa a accroché à cette ligne. Elle s'ajoute ici, et se déplace ou se
  // fige comme les autres.
  let cols=r.colonnes;
  if(S.def&&S.def.rattachable){
    cols=cols.concat([{nom:'_ratt',label:(S.ecran==='livraisons'?'Départ MyExpé':'Dossier de fab'),
                       type:'ratt',largeur:150}]);
  }
  appliquerLayout(cols);
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
  h+='<div class="detail-corps deux-col"><div class="detail-principal">';
  if(p)h+=blocPiece(p,cur.id);
  h+='<div class="titre-bloc">'+ICO_FICHE+'<span>'+(p?'Détail de la ligne':'Détail')+'</span>'+
     (p?'<span class="tb-num">'+esc(numeroDeLigne(r.groupes,p,cur.id))+'</span>':'')+'</div>';
  const res=resumeLigne(r.groupes);
  h+=res.html;
  // Dans une PIÈCE, le détail de la ligne est déjà le tableau au-dessus,
  // ligne par ligne et colonne par colonne. Le répéter en blocs obligeait à
  // faire la correspondance de tête et empêchait de comparer deux lignes.
  // Hors pièce — un article, un client, un mouvement — il n'y a pas de
  // tableau, donc les blocs restent : c'est la seule vue de l'objet.
  h+=p?'':('<div class="sections" id="sec-detail">'+blocGroupes(r.groupes,res.pris)+'</div>');
  h+='</div><div class="detail-rail">';
  h+='<div class="titre-bloc" id="t-liens">'+ICO_LIEN+'<span>Pièces liées</span></div>'+
     '<div class="liens" id="liens"><div class="liens-vide">Recherche des pièces rattachées…</div></div>';
  h+='</div></div>';
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
  calerColonnesFigees(d);
  d.querySelector('.detail-corps').scrollTop=0;
  chargerLiens(cur,jeton);
}

// La 2e colonne figée se colle juste après la 1re — dont la largeur dépend du
// contenu et ne se connaît qu'une fois le tableau posé. Sans cette mesure, la
// colonne « Lg » recouvrait la référence article au premier défilement.
function calerColonnesFigees(racine){
  (racine||document).querySelectorAll('table.pl').forEach(t=>{
    const p=t.querySelector('thead th.fx0');
    if(p)t.style.setProperty('--fx1',Math.round(p.getBoundingClientRect().width)+'px');
  });
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
  // TOUTES les colonnes de la ligne, pas les neuf premières. Le détail de la
  // ligne se lisait auparavant en blocs sous le tableau, ce qui obligeait à
  // faire la correspondance de tête entre « ligne 3 » et le bloc du bas — et
  // interdisait de comparer deux lignes. Ici, une ligne du document est une
  // ligne du tableau, point. Le prix : ça défile horizontalement, d'où les
  // deux premières colonnes figées et les cellules tronquées à 20 caractères.
  const cols=ordonnerColonnesPiece(p.colonnes||[]);
  h+='<div class="titre-bloc"><span>Lignes de la pièce</span>'+
     '<span class="tb-num">'+fmtNb(p.total,0)+'</span>'+
     (cols.length>9?'<span class="pl-astuce">'+fmtNb(cols.length,0)+
      ' colonnes — faire défiler vers la droite</span>':'')+'</div>';
  h+='<div class="pl-boite pl-large"><table class="pl"><thead><tr>';
  cols.forEach((c,i)=>{
    h+='<th class="'+(estNum(c)?'num ':'')+fige(i)+'" title="'+esc(c.label)+'">'+
       esc(c.label)+'</th>';
  });
  h+='</tr></thead><tbody>';
  (p.lignes||[]).forEach(l=>{
    const ici=String(l._id)===String(idCourant);
    h+='<tr class="pl-ligne'+(ici?' ici':'')+'" data-id="'+esc(l._id)+'"'+
       (ici?' title="La ligne ouverte"':' title="Ouvrir cette ligne"')+'>';
    cols.forEach((c,i)=>{
      h+='<td class="'+esc(celluleCourte(c,l[c.nom]).cls)+' '+fige(i)+'"'+
         celluleCourte(c,l[c.nom]).titre+'>'+celluleCourte(c,l[c.nom]).html+'</td>';
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

// Les deux premières colonnes (numéro, ligne) restent visibles quand on
// défile : sans elles on ne sait plus quelle ligne on lit dès la dixième
// colonne, et le tableau devient inutilisable.
function fige(i){return i===0?'fx fx0':(i===1?'fx fx1':'');}

// Vingt caractères, et la valeur entière au survol. Une désignation RVGI fait
// parfois cent caractères : elle écraserait à elle seule les vingt autres
// colonnes. On coupe l'affichage, jamais la donnée.
const PL_MAX=20;
function celluleCourte(col,v){
  const r=cellule(col,v);
  const brut=(v==null||v==='')?'':String(v);
  // Seul le texte simple se coupe : une date formatée, un badge d'énumération
  // ou un montant n'ont pas de longueur à réduire, et les tronquer les
  // rendrait faux.
  const t=col.type||'texte';
  const coupable=(t==='texte'||t==='client'||t==='ref'||t==='code'||t==='of');
  if(!coupable||brut.length<=PL_MAX){
    return {cls:r.cls,html:r.html,titre:brut&&brut.length>PL_MAX?' title="'+esc(brut)+'"':''};
  }
  return {cls:r.cls,html:esc(brut.slice(0,PL_MAX-1))+'…',titre:' title="'+esc(brut)+'"'};
}

// Quelle ligne du document est ouverte — « L3 sur 4 ». Le tableau la surligne
// déjà, mais un document de quarante lignes se déroule : le titre le rappelle
// sans qu'on ait à remonter.
function numeroDeLigne(groupes,p,idCourant){
  const rang=(p.lignes||[]).findIndex(l=>String(l._id)===String(idCourant));
  const l=rang>=0?p.lignes[rang]:null;
  let n=null;
  if(l)for(const k of ['ligne','rang','lignecde']){ if(l[k]!=null&&l[k]!==''){n=l[k];break;} }
  if(n==null&&rang>=0)n=rang+1;
  const tot=p.total||(p.lignes||[]).length;
  if(n==null)return tot>1?tot+' lignes':'';
  return tot>1?('L'+n+' sur '+fmtNb(tot,0)):('L'+n);
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
  return t==='qte'||t==='nombre'||t==='prix'||t==='montant'||t==='pct'||t==='id';
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
  // Le titre du rail reste en place même à vide : une colonne qui disparaît
  // déplace tout le reste, et « aucune pièce rattachée » est une réponse, pas
  // une absence de réponse.
  const t=document.getElementById('t-liens');
  if(t){
    const total=liens.reduce((s,l)=>s+(l.total||0),0);
    const n=t.querySelector('.tb-num');if(n)n.remove();
    if(total)t.insertAdjacentHTML('beforeend','<span class="tb-num">'+fmtNb(total,0)+'</span>');
  }
  if(!liens.length){
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

// Chaque écran a ses propres colonnes ; le panneau, lui, n'a que quatre
// emplacements — ce qui identifie, ce qui décrit, le chiffre, la date. On
// range les colonnes dedans par TYPE, pas par position : sinon la même liste
// s'alignerait différemment d'un écran à l'autre.
function rgCasesLigne(colonnes,l){
  const cases={c1:null,c2:null,c3:null,cn:null,cd:null};
  colonnes.forEach(c=>{
    const t=c.type||'texte';
    // Un numéro de pièce identifie : il tient la première case, comme un n° d'OF
    // ou une référence article — pas la case du chiffre, où on le lirait comme
    // une quantité.
    if(!cases.c1&&(t==='of'||t==='ref'||t==='code'||t==='id'))cases.c1=c;
    else if(!cases.cd&&(t==='date'||t==='datetime'))cases.cd=c;
    else if(!cases.cn&&(t==='qte'||t==='nombre'||t==='prix'||t==='montant'))cases.cn=c;
    else if(!cases.c2)cases.c2=c;
    else if(!cases.c3)cases.c3=c;
  });
  // Aucune colonne d'identité : le premier venu tient ce rôle, sinon la ligne
  // commencerait par du vide.
  if(!cases.c1){for(const k of ['c2','c3']){if(cases[k]){cases.c1=cases[k];cases[k]=null;break;}}}
  let h='';
  ['c1','c2','c3','cn','cd'].forEach(k=>{
    const c=cases[k];
    if(!c){ if(k==='c1'||k==='c2')h+='<span class="c '+k+'"></span>'; return; }
    const v=cellule(c,l[c.nom]);
    // On surligne ce qui a été tapé, mais seulement sur du texte simple :
    // une date formatée ou un badge d'énumération ne se découpent pas.
    const brut=l[c.nom];
    const t=c.type||'texte';
    const html=(t==='texte'||t==='client'||t==='ref'||t==='of'||t==='code')
      ? rgSurligner(brut,RG.q)
      : (t==='id' ? rgSurligner(fmtId(brut),RG.q) : v.html);
    h+='<span class="c '+k+'" title="'+esc(c.label)+' : '+esc(brut==null?'—':brut)+'">'+html+'</span>';
  });
  return h;
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
      h+='<div class="rg-ligne" data-i="'+i+'">'+rgCasesLigne(g.colonnes||[],l)+'</div>';
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


// ── Menu de service ──────────────────────────────────────────────
// Servi par /api/erp/meta selon le rôle. Ce n'est pas un droit d'accès —
// tout le monde ouvre les mêmes 27 écrans par le tiroir — c'est une
// habitude rangée : deux tableaux de bord, puis les écrans du service.
const ICO_TDB='<svg class="mk-ico" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="8" height="10" rx="1"/><rect x="13" y="3" width="8" height="6" rx="1"/><rect x="13" y="11" width="8" height="10" rx="1"/><rect x="3" y="15" width="8" height="6" rx="1"/></svg>';
const ICO_EXT='<svg class="ext" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>';
const ICO_GRILLE='<svg class="mk-ico" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/></svg>';

function fermerMkPop(){
  const w=document.getElementById('mk-svc');if(!w)return;
  w.classList.remove('ouvert');
  const b=document.getElementById('mk-btn');if(b)b.setAttribute('aria-expanded','false');
  if(b&&document.activeElement===b)b.blur();   // sinon :focus-within le rouvre
}

function renderMenuService(){
  const pop=document.getElementById('mk-pop');if(!pop)return;
  const menu=(S.meta&&S.meta.menu)||{tdb:[],ecrans:[]};
  const courant=S.ecran||'';
  let h='';
  if((menu.tdb||[]).length){
    h+='<div class="mk-groupe">Tableaux de bord</div>';
    (menu.tdb||[]).forEach(t=>{
      h+='<button type="button" role="menuitem" class="mk-item tdb'+(courant===t.cle?' active':'')+'" data-va="#/'+esc(t.cle)+'">'+
         ICO_TDB+'<span><b>'+esc(t.label)+'</b><em>'+esc(t.resume||'')+'</em></span></button>';
    });
  }
  if((menu.ecrans||[]).length){
    h+='<div class="mk-groupe">Mes écrans RVGI</div>';
    (menu.ecrans||[]).forEach(e=>{
      h+='<button type="button" role="menuitem" class="mk-item'+(courant===e.cle?' active':'')+'" data-va="#/'+esc(e.cle)+'">'+
         (iconeEcran(e.cle)||ICO_GRILLE).replace('<svg','<svg class="mk-ico"')+
         '<span><b>'+esc(e.label)+'</b><em>'+esc(e.resume||'')+'</em></span></button>';
    });
  }
  h+='<div class="mk-sep"></div><button type="button" role="menuitem" class="mk-item" data-va="#/">'+
     ICO_GRILLE+'<span><b>Tous les écrans</b><em>Les 27 écrans de RVGI, par domaine.</em></span></button>';
  pop.innerHTML=h;
  pop.querySelectorAll('[data-va]').forEach(b=>{
    b.addEventListener('click',()=>{
      const va=b.getAttribute('data-va');
      fermerMkPop();
      if(va==='#/')allerAuMenu();else location.hash=va;
    });
  });
}

// ── Tableaux de bord ─────────────────────────────────────────────
const TDB_DEFS={
  tdb_adv:{api:'adv',titre:'TDB ADV',
    sous:'Le fil commande → dossier de production → BL, et ce qui attend une vérification.'},
  tdb_direction:{api:'direction',titre:'TDB Direction',
    sous:'Rentré, facturable, facturé — et le rentré de la veille.'}
};
function estTdb(cle){return Object.prototype.hasOwnProperty.call(TDB_DEFS,cle);}

// Les contrôles qui vivent dans MySifa, pas dans RVGI. Chaque ligne lit le
// compteur à la MÊME route que l'écran qu'elle ouvre : le chiffre et la page
// ne peuvent pas diverger. Un accès refusé n'efface pas la ligne, il le dit.
const TDB_CONTROLES=[
  {cle:'pending',titre:'Mappings à valider',
   quoi:'Un OF que plusieurs commandes peuvent réclamer : personne ne tranche à la place de l\'ADV.',
   url:'/api/admin/of-link-pending/count',lire:d=>d.count,va:'/prod?page=of#pending',seuil:1},
  {cle:'sansof',titre:'Dossiers sans OF',
   quoi:'Un dossier en cours qu\'aucun ordre de fabrication ne couvre.',
   url:'/api/admin/dossiers-sans-of/count',lire:d=>d.count,va:'/prod?page=of#sansof',seuil:1},
  {cle:'incoh',titre:'Fiches techniques incohérentes',
   quoi:'Nombre de fronts en désaccord avec la géométrie : le besoin matière part faux.',
   url:'/api/stock/besoins-matieres/fiches-incoherentes',lire:d=>d.incoherentes,
   va:'/stock?tab=besoins-matieres',seuil:1,grave:true},
  {cle:'orph',titre:'Fiches non reliées',
   quoi:'Référence illisible, ou produit jamais fabriqué — les deux n\'appellent pas la même action.',
   url:'/api/produits/fiches-non-reliees?limit=1',lire:d=>d.total,va:'/prod?page=fiches'},
  {cle:'scans',titre:'Scans d\'OF à rattacher',
   quoi:'OF scannés que rien ne relie encore à un produit.',
   url:'/api/produits/documents/a-rattacher',lire:d=>d.total,va:'/prod?page=scans'}
];

function tdbNav(va){
  if(!va)return;
  if(va.charAt(0)==='#'){location.hash=va;return;}
  // Un écran d'une autre app s'ouvre à côté : l'ADV revient au tableau de
  // bord sans avoir perdu sa place ni son filtre.
  window.open(va,'_blank','noopener');
}

function tdbTuile(o){
  const inerte=o.va?'':' data-inerte="1"';
  const val=(o.v==null)?'<span class="v" style="color:var(--muted)">—</span>'
    :('<span class="v">'+o.v+(o.unite?('<small>'+esc(o.unite)+'</small>'):'')+'</span>');
  return '<button type="button" class="tdb-tuile '+(o.ton||'')+'"'+inerte+
    (o.va?(' data-va="'+esc(o.va)+'"'):'')+(o.titre?(' title="'+esc(o.titre)+'"'):'')+'>'+
    '<span class="k">'+esc(o.k)+'</span>'+val+
    (o.s?('<span class="s '+(o.sTon||'')+'">'+esc(o.s)+'</span>'):'')+'</button>';
}

function tdbPan(o){
  return '<section class="tdb-pan"><div class="tdb-pan-h"><h3>'+esc(o.titre)+'</h3>'+
    (o.cpt?('<span class="cpt">'+esc(o.cpt)+'</span>'):'')+
    (o.plus?('<button type="button" class="plus" data-va="'+esc(o.plusVa||'')+'">'+esc(o.plus)+' →</button>'):'')+
    '</div>'+(o.corps||'')+(o.note?('<div class="tdb-note">'+o.note+'</div>'):'')+'</section>';
}

function tdbVide(txt){return '<div class="tdb-vide">'+esc(txt)+'</div>';}

// Un montant se lit d'un coup d'œil ou ne se lit pas : au-delà du millier on
// abrège, et le titre porte la valeur exacte.
function tdbEurParts(v){
  const n=Number(v);
  if(!isFinite(n))return null;
  const a=Math.abs(n);
  if(a>=1e6)return [fmtNb(n/1e6,2),'M€'];
  // Une décimale tant qu'on est sous 100 k€ : sans elle, quatre tranches de
  // 1,9 · 1,7 · 4,6 · 6,3 s'affichent 2 · 2 · 5 · 6 et ne font plus le total.
  if(a>=1000)return [fmtNb(n/1000,a<1e5?1:0),'k€'];
  return [fmtNb(n,0),'€'];
}
function tdbEur(v){
  const p=tdbEurParts(v);
  return p?(p[0]+'<small> '+p[1]+'</small>'):null;
}
function tdbEurTxt(v){
  const p=tdbEurParts(v);
  return p?(p[0]+' '+p[1]):'—';
}
function tdbEurExact(v){const n=Number(v);return isFinite(n)?(fmtNb(n,2)+' €'):'—';}
function tdbJourCourt(iso){
  const m=String(iso||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m?(m[3]+'/'+m[2]):'—';
}
function tdbLibelleJour(iso){
  const m=String(iso||'').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(!m)return '';
  const d=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]));
  try{return d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'});}
  catch(e){return fmtDate(iso);}
}

function tdbBrancher(racine){
  racine.querySelectorAll('[data-va]').forEach(el=>{
    el.addEventListener('click',ev=>{ev.stopPropagation();tdbNav(el.getAttribute('data-va'));});
  });
  // Une ligne ouvre la modale du miroir, sans quitter le tableau de bord.
  racine.querySelectorAll('[data-ouvre]').forEach(el=>{
    el.addEventListener('click',()=>{
      ouvrirDetailTdb(el.getAttribute('data-ouvre'),el.getAttribute('data-id'));
    });
  });
}

// Ouvrir le détail depuis une vue qui n'a pas de grille : même modale, même
// fil de pièces liées, sans passer par l'écran.
function ouvrirDetailTdb(cle,id){
  if(!cle||id==null||id==='')return;
  S.pile=[{ecran:cle,id:id}];
  rendreDetail();
}

async function ouvrirTdb(cle){
  const conf=TDB_DEFS[cle];
  if(!conf){ouvrirMenu();return;}
  fermerSidebar();
  S.ecran=cle;S.def=null;S.selection=null;S.colonnes=[];S.filtres={};S.q='';S.ratt='';
  document.getElementById('titre').textContent=conf.titre;
  document.getElementById('sous').textContent=conf.sous;
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=conf.titre;
  renderNav();renderMenuService();
  const corps=document.getElementById('corps');
  corps.innerHTML='<div class="tdb-wrap"><div class="tdb-charge">Chargement du tableau de bord…</div></div>';
  if(!S.meta||!S.meta.present){
    corps.innerHTML='<div class="vide-msg">'+esc((S.meta&&S.meta.message)||'Miroir indisponible.')+'</div>';
    return;
  }
  let d;
  try{d=await api('/api/erp/tdb/'+conf.api);}
  catch(e){corps.innerHTML='<div class="vide-msg">'+esc(e.message)+'</div>';return;}
  if(S.ecran!==cle)return;   // l'utilisateur est déjà parti ailleurs
  const hote=corps.querySelector('.tdb-wrap');
  if(!hote)return;
  hote.innerHTML=(cle==='tdb_adv')?htmlTdbAdv(d):htmlTdbDirection(d);
  tdbBrancher(hote);
  if(cle==='tdb_adv')chargerControlesMySifa(hote);
}

function tdbIndispo(d){
  if(!d.indispo||!d.indispo.length)return '';
  return '<div class="tdb-alerte"><span>⚠</span><span><b>Certains blocs sont muets.</b> '+
    esc(d.indispo.join(' · '))+'</span></div>';
}

// ── ADV ──────────────────────────────────────────────────────────
function htmlTdbAdv(d){
  const c=d.carnet||{},aujourdhui=(d.bornes||{}).aujourdhui||'';
  const dos=d.dossiers||{},hp=d.hors_prod||{},af=d.a_facturer||{};
  let h=tdbIndispo(d);

  h+='<div class="tdb-tuiles">'+
    tdbTuile({k:'Carnet ouvert',v:c.lignes==null?null:fmtNb(c.lignes,0),s:'lignes à traiter',
      va:'#/commandes?position=0',titre:d.formules.carnet})+
    tdbTuile({k:'À expédier sous 7 jours',v:c.semaine==null?null:fmtNb(c.semaine,0),
      s:'date d\'expédition dans la semaine',va:'#/commandes?position=0&jusqua='+encodeURIComponent(d.bornes.fin_semaine),
      titre:d.formules.semaine})+
    tdbTuile({k:'En retard',v:c.retard==null?null:fmtNb(c.retard,0),ton:c.retard?'dg':'ok',
      s:c.retard?'date d\'expédition dépassée':'rien en retard',sTon:c.retard?'dg':'ok',
      va:'#/commandes?position=0&jusqua='+encodeURIComponent(aujourdhui),titre:d.formules.retard})+
    tdbTuile({k:'BL à facturer',v:af.bl==null?null:fmtNb(af.bl,0),ton:af.bl?'warn':'',
      s:'livrés, pas encore facturés',sTon:af.bl?'warn':'',va:'#/livraisons',titre:d.formules.a_facturer})+
    tdbTuile({k:'Sans dossier de prod',v:d.sans_dossier==null?null:fmtNb(d.sans_dossier,0),
      ton:'neu',s:'lignes en fabrication, non rattachées',
      va:'#/commandes?position=0&ratt=non',titre:d.formules.sans_dossier})+
    '</div>';

  // ── En retard : la liste d'action ──
  let corps;
  const rt=d.retards||[];
  if(!rt.length){corps=tdbVide('Rien en retard. Le carnet est tenu.');}
  else{
    corps='<table class="tdb-t"><thead><tr><th>Commande</th><th>Client</th><th>Désignation</th>'+
      '<th class="n">Reste</th><th class="n">Expédition</th><th>Retard</th></tr></thead><tbody>';
    rt.forEach(l=>{
      const j=joursEcoules(l.expedition,aujourdhui);
      const ton=j>=5?'dg':(j>=2?'warn':'');
      corps+='<tr data-ouvre="commandes" data-id="'+esc(l.id)+'" title="Ouvrir la commande">'+
        '<td class="ref">'+esc(fmtId(l.numero))+(l.ligne!=null?(' · '+esc(fmtId(l.ligne))):'')+'</td>'+
        '<td class="fort coupe">'+esc(l.client||'—')+'</td>'+
        '<td class="coupe">'+esc(l.designation||'—')+'</td>'+
        '<td class="n">'+fmtNb(l.reste,0)+'</td>'+
        '<td class="n">'+esc(tdbJourCourt(l.expedition))+'</td>'+
        '<td><span class="tdb-etiq '+ton+'"><i></i>'+esc(j==null?'—':(j+' j'))+'</span></td></tr>';
    });
    corps+='</tbody></table>';
  }
  const gauche=tdbPan({titre:'En retard de livraison',cpt:(c.retard||0)+' lignes',
    plus:'Ouvrir le carnet filtré',plusVa:'#/commandes?position=0&jusqua='+encodeURIComponent(aujourdhui),
    corps:corps,
    note:'Cliquer une ligne ouvre sa modale et ses pièces liées — BL, colisage, facture — '+
         'sans quitter ce tableau de bord.'});

  // ── Livré, pas encore facturé ──
  let cf;
  const items=d.a_facturer_items||[];
  if(!items.length){cf=tdbVide('Tout ce qui est livré est facturé.');}
  else{
    cf='<table class="tdb-t"><thead><tr><th>BL</th><th class="n">Expédié</th><th>Client</th>'+
       '<th class="n">Lignes</th><th class="n">Reste</th></tr></thead><tbody>';
    items.forEach(l=>{
      cf+='<tr data-ouvre="livraisons" data-id="'+esc(l.id)+'" title="Ouvrir le bon de livraison">'+
        '<td class="ref">'+esc(fmtId(l.bl))+'</td>'+
        '<td class="n">'+esc(tdbJourCourt(l.expedition))+'</td>'+
        '<td class="fort coupe">'+esc(l.client||'—')+'</td>'+
        '<td class="n">'+fmtNb(l.lignes,0)+'</td>'+
        '<td class="n">'+fmtNb(l.reste,0)+'</td></tr>';
    });
    cf+='</tbody></table>';
  }
  const gauche2=tdbPan({titre:'Livré, pas encore facturé',cpt:(af.bl||0)+' BL',
    plus:'Ouvrir les BL',plusVa:'#/livraisons',corps:cf,
    note:'Reste = quantité livrée moins quantité déjà facturée, ligne par ligne ('+
         '<code>qte − qtefac</code>).'});

  // ── Les contrôles MySifa, remplis après coup ──
  let ctrl='';
  TDB_CONTROLES.forEach(k=>{
    ctrl+='<button type="button" class="tdb-ctrl" data-va="'+esc(k.va)+'" data-ctrl="'+esc(k.cle)+'">'+
      '<span class="n vide" data-n="'+esc(k.cle)+'">…</span>'+
      '<span class="tt"><b>'+esc(k.titre)+'</b><em>'+esc(k.quoi)+'</em></span>'+ICO_EXT+'</button>';
  });
  const droite=tdbPan({titre:'OF et fiches techniques à vérifier',cpt:'MySifa',corps:ctrl,
    note:'Ces chiffres viennent de MySifa, pas de RVGI, et chaque ligne lit le compteur à la '+
         'même route que l\'écran qu\'elle ouvre — ils ne peuvent pas diverger. L\'écran s\'ouvre '+
         'dans un onglet à côté.'});

  // ── Dossiers vis-à-vis de RVGI ──
  let dr;
  if(!d.dossiers){dr=tdbVide('Base MySifa non attachée au miroir.');}
  else{
    const etats=[
      ['lie','Rattachés','ok'],['partiel','Partiellement','warn'],
      ['a_verifier','À vérifier','warn'],['a_rattacher','À rattacher','dg'],
      ['hors_commande','Hors commande','']
    ];
    dr='<table class="tdb-t"><tbody>';
    etats.forEach(e=>{
      const n=dos[e[0]]||0;
      if(!n&&e[0]==='hors_commande')return;
      dr+='<tr><td class="fort">'+esc(e[1])+'</td>'+
          '<td class="n"><span class="tdb-etiq '+e[2]+'"><i></i>'+fmtNb(n,0)+'</span></td></tr>';
    });
    dr+='</tbody></table>';
  }
  const droite2=tdbPan({titre:'Dossiers de production ↔ RVGI',cpt:'dossiers non terminés',corps:dr,
    note:'Un numéro tapé au terminal avant la synchro reste « à vérifier » et se confirme tout '+
         'seul au prochain import. Ce qui reste « à rattacher » demande un humain.'});

  // ── Ce qui n'attend aucun dossier, et c'est normal ──
  let hpc;
  if(!d.hors_prod){hpc=tdbVide('Origine des lignes indisponible.');}
  else{
    hpc='<table class="tdb-t"><tbody>'+
      '<tr data-va="#/commandes?position=0&origine=2"><td class="fort">Sur stock</td><td class="n">'+fmtNb(hp.stock,0)+'</td></tr>'+
      '<tr data-va="#/commandes?position=0&origine=3"><td class="fort">Sous-traitance</td><td class="n">'+fmtNb(hp.sous_traitance,0)+'</td></tr>'+
      '</tbody></table>';
  }
  const droite3=tdbPan({titre:'Sans dossier, et c\'est normal',corps:hpc,
    note:'Seules les lignes en fabrication attendent un dossier. Compter les autres avec elles '+
         'ferait apparaître des retards de production qui n\'existent pas.'});

  h+='<div class="tdb-cols"><div class="tdb-pile">'+gauche+gauche2+'</div>'+
     '<div class="tdb-pile">'+droite+droite2+droite3+'</div></div>';
  return h;
}

function joursEcoules(depuis,jusqua){
  const a=String(depuis||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  const b=String(jusqua||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(!a||!b)return null;
  const da=Date.UTC(+a[1],+a[2]-1,+a[3]),db=Date.UTC(+b[1],+b[2]-1,+b[3]);
  return Math.round((db-da)/86400000);
}

// Les compteurs MySifa, chacun pour soi : une route en échec (droits, écran
// en panne) laisse « — » sur SA ligne au lieu de vider le panneau.
async function chargerControlesMySifa(hote){
  TDB_CONTROLES.forEach(async k=>{
    const cible=hote.querySelector('[data-n="'+k.cle+'"]');
    if(!cible)return;
    try{
      const d=await api(k.url);
      const n=Number(k.lire(d)||0);
      cible.textContent=isFinite(n)?fmtNb(n,0):'—';
      cible.className='n'+(n>=(k.seuil||1)?(k.grave?' dg':' warn'):' ok');
      cible.title=n?(n+' à traiter'):'Rien à traiter';
    }catch(e){
      cible.textContent='—';cible.className='n vide';
      cible.title='Indisponible : '+e.message;
    }
  });
}

// ── Direction ────────────────────────────────────────────────────
// Le CA de tout l'écran repose sur une seule hypothèse : `net` est le
// montant net de la ligne. Le service la vérifie sur les données ; si elle
// ne tient pas, l'écran le dit AVANT d'afficher des millions d'euros faux.
function tdbControleMontant(d){
  const c=d.controle_montant||{};
  const suspects=[];
  Object.keys(c).forEach(k=>{
    const v=c[k];
    if(v&&v.verdict==='prix_unitaire')suspects.push(k);
  });
  if(!suspects.length)return '';
  return '<div class="tdb-alerte"><span>⚠</span><span><b>Chiffres à ne pas utiliser tels quels.</b> '+
    'Sur '+esc(suspects.join(' et '))+', la colonne <code>net</code> se comporte comme un prix '+
    'unitaire, pas comme un montant de ligne : le chiffre d\'affaires affiché serait divisé par '+
    'les quantités. À reprendre dans <code>erp_tdb._expr_montant</code> avant de s\'y fier.</span></div>';
}

function htmlTdbDirection(d){
  const hier=d.hier||{},re=d.rentre||{},fa=d.facture||{},fb=d.facturable||{},ca=d.carnet||{};
  let h=tdbControleMontant(d)+tdbIndispo(d);

  // Le bandeau : la question qu'on se pose en ouvrant l'écran.
  if(hier&&hier.date){
    const ecart=(hier.moyenne_30j&&hier.montant!=null)
      ? Math.round((hier.montant/hier.moyenne_30j-1)*100):null;
    h+='<div class="tdb-bande">'+
      '<div><span class="lab">Rentré hier · '+esc(tdbLibelleJour(hier.date))+'</span>'+
        '<span class="big" title="'+esc(tdbEurExact(hier.montant))+'">'+
        (tdbEur(hier.montant)||'—')+'</span></div>'+
      '<div class="txt"><b>'+fmtNb(hier.commandes,0)+' commandes</b> · '+fmtNb(hier.lignes,0)+' lignes<br>'+
        fmtNb(hier.clients,0)+' clients</div>'+
      '<div class="droite">'+
        (ecart==null?'':('<b style="color:var(--'+(ecart>=0?'ok':'danger')+')">'+
          (ecart>=0?'+':'')+ecart+' % vs la moyenne 30 j</b>'))+
        'moyenne quotidienne '+tdbEurTxt(hier.moyenne_30j)+
      '</div></div>';
  }

  h+='<div class="tdb-tuiles">'+
    tdbTuile({k:'Rentré — ce mois',v:tdbEur(re.mois),
      s:pourcent(re.mois,re.mois_n1,'vs même mois l\'an dernier'),
      sTon:ton(re.mois,re.mois_n1),va:'#/commandes',titre:d.formules.rentre})+
    tdbTuile({k:'Facturable',v:tdbEur(fb.montant),ton:'warn',
      s:fb.bl!=null?(fmtNb(fb.bl,0)+' BL livrés non facturés'):'',sTon:'warn',
      va:'#/livraisons',titre:d.formules.facturable})+
    tdbTuile({k:'Facturé — ce mois',v:tdbEur(fa.mois),
      s:pourcent(fa.mois,fa.mois_n1,'vs même mois l\'an dernier'),
      sTon:ton(fa.mois,fa.mois_n1),va:'#/factures',titre:d.formules.facture})+
    tdbTuile({k:'Carnet restant',v:tdbEur(ca.montant),ton:'neu',
      s:ca.lignes!=null?(fmtNb(ca.lignes,0)+' lignes à livrer'):'',
      va:'#/commandes?position=0',titre:d.formules.encours})+
    '</div>';

  // ── La série 12 mois : deux séries, une seule échelle ──
  const serie=d.serie||[];
  let g;
  if(!serie.length){g=tdbVide('Série indisponible.');}
  else{
    const maxi=Math.max(1,...serie.map(m=>Math.max(m.rentre||0,m.facture||0)));
    g='<div class="tdb-graph"><div class="tdb-leg">'+
      '<span><i style="background:var(--serie2)"></i>Rentré (prise de commande)</span>'+
      '<span><i style="background:var(--accent)"></i>Facturé</span></div><div class="tdb-barres">';
    serie.forEach(m=>{
      const a=Math.round(((m.rentre||0)/maxi)*100),b=Math.round(((m.facture||0)/maxi)*100);
      g+='<div class="grp" title="'+esc(m.mois+' — rentré '+tdbEurExact(m.rentre)+
          ', facturé '+tdbEurExact(m.facture))+'">'+
         '<i class="a" style="height:'+a+'%"></i><i class="b" style="height:'+b+'%"></i></div>';
    });
    g+='</div><div class="tdb-axe">'+serie.map(m=>'<span>'+esc(m.label||'')+'</span>').join('')+
       '</div></div>';
  }
  const gauche=tdbPan({titre:'Rentré et facturé — 12 mois',cpt:'même échelle',
    plus:'Ouvrir les factures',plusVa:'#/factures',corps:g,
    note:'Le mois courant est toujours partiel côté facturé : la facturation suit la livraison, '+
         'elle ne la précède pas.'});

  // ── Le détail de la veille ──
  let t;
  const it=hier.items||[];
  if(!it.length){t=tdbVide('Aucune commande enregistrée ce jour-là.');}
  else{
    t='<table class="tdb-t"><thead><tr><th>Commande</th><th>Client</th><th class="n">Lignes</th>'+
      '<th class="n">Montant</th><th class="n">Expédition</th></tr></thead><tbody>';
    it.forEach(l=>{
      t+='<tr data-ouvre="commandes" data-id="'+esc(l.id)+'" title="Ouvrir la commande">'+
        '<td class="ref">'+esc(fmtId(l.numero))+'</td>'+
        '<td class="fort coupe">'+esc(l.client||'—')+'</td>'+
        '<td class="n">'+fmtNb(l.lignes,0)+'</td>'+
        '<td class="n" title="'+esc(tdbEurExact(l.montant))+'">'+fmtNb(l.montant,0)+' €</td>'+
        '<td class="n">'+esc(tdbJourCourt(l.expedition))+'</td></tr>';
    });
    t+='<tr><td class="fort">'+fmtNb(hier.commandes,0)+' commandes</td><td></td>'+
       '<td class="n fort">'+fmtNb(hier.lignes,0)+'</td>'+
       '<td class="n fort">'+fmtNb(hier.montant,0)+' €</td><td></td></tr>';
    t+='</tbody></table>';
  }
  const gauche2=tdbPan({titre:'Hier — commandes rentrées',cpt:esc(tdbJourCourt(hier.date)),
    plus:'Ouvrir les commandes',plusVa:'#/commandes',corps:t,
    note:'Une commande modifiée après coup fait bouger ce total : c\'est la photo de l\'ERP à '+
         'la dernière synchro, pas un chiffre figé.'});

  // ── 30 jours de prise de commande ──
  const jours=d.jours||[];
  let j;
  if(!jours.length){j=tdbVide('Série quotidienne indisponible.');}
  else{
    const maxj=Math.max(1,...jours.map(x=>Number(x.montant)||0));
    j='<div class="tdb-jours">'+jours.map((x,i)=>{
      const ha=Math.max(2,Math.round(((Number(x.montant)||0)/maxj)*100));
      return '<i class="'+(i===jours.length-1?'dernier':'')+'" style="height:'+ha+'%" title="'+
        esc(fmtDate(x.jour)+' — '+tdbEurExact(x.montant))+'"></i>';
    }).join('')+'</div><div class="tdb-jours-pied"><span>'+esc(tdbJourCourt(jours[0].jour))+
      '</span><span>'+esc(tdbJourCourt(jours[jours.length-1].jour))+'</span></div>';
  }
  const droite=tdbPan({titre:'Prise de commande',cpt:'30 jours',corps:j,
    note:'Les jours creux — week-ends, fériés — restent à leur place : les masquer ferait croire '+
         'à une activité continue.'});

  // ── Facturable par ancienneté ──
  let fbc;
  if(!fb||!fb.ages){fbc=tdbVide('Facturable indisponible.');}
  else{
    const maxa=Math.max(1,...fb.ages.map(a=>Number(a.montant)||0));
    fbc='<div class="tdb-hb">'+fb.ages.map(a=>{
      const w=Math.max(2,Math.round(((Number(a.montant)||0)/maxa)*100));
      return '<div class="l"><span class="nom">'+esc(a.label)+'</span>'+
        '<span class="val">'+tdbEurTxt(a.montant)+'</span>'+
        '<span class="piste"><i style="width:'+w+'%"></i></span></div>';
    }).join('')+'</div>';
  }
  const droite2=tdbPan({titre:'Facturable par ancienneté',
    cpt:tdbEurTxt(fb.montant),corps:fbc,
    note:'Valorisé au prix unitaire de la commande d\'origine : le BL ne porte pas de prix. '+
         'L\'écart avec la facture réelle — remises de pied, port — est normal.'});

  // ── Top clients ──
  const tc=d.top_clients||[];
  let tcc;
  if(!tc.length){tcc=tdbVide('Aucune facture ce mois-ci.');}
  else{
    const maxc=Math.max(1,...tc.map(x=>Number(x.montant)||0));
    tcc='<div class="tdb-hb">'+tc.map(x=>{
      const w=Math.max(2,Math.round(((Number(x.montant)||0)/maxc)*100));
      return '<div class="l"><span class="nom">'+esc(x.client)+'</span>'+
        '<span class="val">'+tdbEurTxt(x.montant)+'</span>'+
        '<span class="piste"><i style="width:'+w+'%"></i></span></div>';
    }).join('')+'</div>';
  }
  const droite3=tdbPan({titre:'Top clients — ce mois',cpt:'facturé',
    plus:'Ouvrir les clients',plusVa:'#/clients',corps:tcc});

  h+='<div class="tdb-cols"><div class="tdb-pile">'+gauche+gauche2+'</div>'+
     '<div class="tdb-pile">'+droite+droite2+droite3+'</div></div>';
  return h;
}

function pourcent(a,b,suffixe){
  const x=Number(a),y=Number(b);
  if(!isFinite(x)||!isFinite(y)||!y)return '';
  const p=Math.round((x/y-1)*100);
  return (p>=0?'+':'')+p+' % '+suffixe;
}
function ton(a,b){
  const x=Number(a),y=Number(b);
  if(!isFinite(x)||!isFinite(y)||!y)return '';
  return x>=y?'ok':'warn';
}

// Le hash porte désormais la destination ET son filtre :
//   #/commandes                        l'écran, filtres par défaut
//   #/commandes?position=0&ratt=non    l'écran, déjà filtré
//   #/tdb_adv                          un tableau de bord
// C'est ce qui rend une tuile cliquable utile : elle n'ouvre pas « l'écran
// des commandes », elle ouvre les lignes qui composent son chiffre.
function lireParamsHash(qs){
  const out={};
  String(qs||'').split('&').forEach(bout=>{
    if(!bout)return;
    const i=bout.indexOf('=');
    const k=decodeURIComponent(i<0?bout:bout.slice(0,i));
    const v=i<0?'':decodeURIComponent(bout.slice(i+1).replace(/\+/g,' '));
    if(k)out[k]=v;
  });
  return out;
}

// Le survol suffit à la souris ; le clic est là pour le tactile et le
// clavier, où « survoler » ne veut rien dire.
function initMenuService(){
  const w=document.getElementById('mk-svc'),b=document.getElementById('mk-btn');
  if(!w||!b)return;
  b.addEventListener('click',ev=>{
    ev.stopPropagation();
    const ouvert=w.classList.toggle('ouvert');
    b.setAttribute('aria-expanded',ouvert?'true':'false');
  });
  document.addEventListener('click',ev=>{if(!w.contains(ev.target))fermerMkPop();});
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape')fermerMkPop();});
}

function appliquerHash(){
  fermerDetail();   // on ne garde jamais une modale ouverte sur un autre écran
  fermerMkPop();
  const m=String(location.hash||'').match(/^#\/([a-z_]+)(?:\?(.*))?$/);
  if(m&&estTdb(m[1])){ouvrirTdb(m[1]);return;}
  if(m&&S.meta&&S.meta.present){
    ouvrirEcran(m[1],m[2]?lireParamsHash(m[2]):null);
  }else{ouvrirMenu();}
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
  renderFraicheur();renderNav();renderMenuService();initRecherche();initMenuService();appliquerHash();
  window.addEventListener('hashchange',appliquerHash);
  initGuides();
}
boot();
</script>

</body>
</html>
"""
