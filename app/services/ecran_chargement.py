"""Écran de chargement sur téléphone : logo et barre sur un dégradé du thème.

Le code de la page pèse lourd et le portail reste vide jusqu'à la réponse de
`/api/auth/me` : sans cet écran, l'ouverture de l'app est une page blanche. Il tient
donc entièrement dans le <head>, avant toute feuille de style et tout script, et se
retire de lui-même dès que la page a quelque chose à montrer. Rien à faire page par
page : `main.py` le pose partout.

Quand il s'affiche, sous 900 px seulement :

- à l'ouverture de l'app ou à un rechargement : tout de suite ;
- en passant d'une appli à l'autre : dès le toucher (tuile, bouton Accueil, lien),
  sur la page qu'on quitte, puis tout de suite sur la suivante. Sinon, rien ne bouge
  entre le toucher et la réponse du serveur, et l'app paraît ne pas avoir réagi ;
- pour une navigation qu'on n'a pas vu partir : après 250 ms, pour ne pas clignoter
  quand la page est rapide. En attendant, le fond a déjà la couleur du thème.

Les changements d'onglet et les actualisations ne rechargent pas la page : ils ne
passent pas par ici. Au bout de 10 s, il propose de réessayer ; au bout de 20 s, il
s'efface, pour ne jamais bloquer une page qu'il n'aurait pas su reconnaître.

Les couleurs sont lues dans `static/mysifa_theme.css` : un thème modifié ou ajouté
s'y retrouve sans toucher à ce fichier. Le mode et la palette viennent du
localStorage, comme pour `mysifa_theme.js`, qui n'est pas encore chargé à ce moment.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from config import APP_NAME_PREFIX, APP_NAME_SUFFIX, BASE_DIR

_BLOC_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_VARIABLE_RE = re.compile(r"--(bg|text|accent|border)\s*:\s*([^;]+)")
_PALETTE_RE = re.compile(r"^body\.palette-([a-z]+)(\.light)?$")
_DEFAUT_COULEURS = {
    "s": {"bg": "#0a0e17", "text": "#f1f5f9", "accent": "#22d3ee", "border": "#1e293b"},
    "c": {"bg": "#f1f5f9", "text": "#0f172a", "accent": "#0891b2", "border": "#e2e8f0"},
}


def couleurs_des_themes(css: str) -> dict:
    """{ "<palette>_<c|s>": {bg, text, accent, border} } lus dans la feuille des thèmes.

    `mysifa` est le thème sans classe de palette : `:root` et `body.light`.
    """
    sans_commentaires = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    themes = {
        "mysifa_s": dict(_DEFAUT_COULEURS["s"]),
        "mysifa_c": dict(_DEFAUT_COULEURS["c"]),
    }
    for selecteurs, corps in _BLOC_RE.findall(sans_commentaires):
        valeurs = {k: v.strip() for k, v in _VARIABLE_RE.findall(corps)}
        if not valeurs:
            continue
        for brut in selecteurs.split(","):
            sel = brut.strip()
            cle = None
            if sel == ":root":
                cle = "mysifa_s"
            elif sel == "body.light":
                cle = "mysifa_c"
            else:
                m = _PALETTE_RE.match(sel)
                if m:
                    cle = m.group(1) + ("_c" if m.group(2) else "_s")
            if cle:
                # Une palette ne redéfinit que ce qui change : le reste vient du mode.
                base = themes.setdefault(cle, dict(_DEFAUT_COULEURS[cle[-1]]))
                base.update({k: v for k, v in valeurs.items() if k in base})
    return themes


_STYLE = (
    "#msf-charge{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;"
    "align-items:center;justify-content:center;gap:28px;background-color:var(--c-bg);"
    "background-image:linear-gradient(180deg,color-mix(in srgb,var(--c-a) 17%,transparent) 0,transparent 62%);"
    "font-family:'Segoe UI',system-ui,-apple-system,sans-serif;transition:opacity .15s ease-out}"
    "#msf-charge.fin{opacity:0;pointer-events:none}"
    "#msf-charge .w{font-size:min(11vw,44px);font-weight:800;letter-spacing:-.037em;line-height:1;color:var(--c-x)}"
    "#msf-charge .w span{color:var(--c-a)}"
    "#msf-charge .tr{position:relative;width:min(30vw,120px);height:4px;border-radius:2px;background:var(--c-l);overflow:hidden}"
    # transform et pas left : l'animation tourne hors du fil principal, elle reste fluide
    # pendant que la page lit son code, ce qui est justement le moment où on la voit.
    "#msf-charge .tr i{position:absolute;top:0;bottom:0;left:0;width:36%;border-radius:2px;background:var(--c-a);"
    "transform:translateX(-100%);will-change:transform;animation:msf-charge-barre 1.25s ease-in-out infinite}"
    "@keyframes msf-charge-barre{from{transform:translateX(-100%)}to{transform:translateX(278%)}}"
    "html.perf-eco #msf-charge .tr i,html.reduce-anim #msf-charge .tr i{animation:none;transform:translateX(90%)}"
    "@media (prefers-reduced-motion:reduce){#msf-charge .tr i{animation:none;transform:translateX(90%)}}"
    "#msf-charge .lent{position:absolute;left:24px;right:24px;bottom:max(64px,env(safe-area-inset-bottom,0px));"
    "display:flex;flex-direction:column;align-items:center;gap:12px;font-size:14px;text-align:center;color:var(--c-x)}"
    "#msf-charge .lent[hidden]{display:none}"
    "#msf-charge .lent button{min-height:44px;padding:0 20px;border-radius:10px;border:1px solid var(--c-a);"
    "background:transparent;color:var(--c-a);font:inherit;font-weight:700}"
)

_SCRIPT = r"""(function(){
// screen et pas matchMedia : la balise viewport n'est pas encore lue, un téléphone se
// présente ici avec une largeur de bureau (980 px).
if(window.top!==window||screen.width>900)return;
var q=new URLSearchParams(location.search);if(q.has('widget')||q.get('embed')==='1')return;
var T=__THEMES__,mode='c',pal='mysifa';
try{if(localStorage.getItem('theme')==='dark')mode='s';var p=localStorage.getItem('mysifa_palette');
if(p==='forge')p='ambre';if(p==='cocon')p='pivoine';if(p&&T[p+'_'+mode])pal=p;}catch(e){}
var c=T[pal+'_'+mode],h=document.documentElement,fini=false,el=null,charge=false;
h.style.backgroundColor=c.bg;
function pret(){if(document.readyState==='loading'||!document.body)return false;
var r=document.getElementById('root');if(r&&!r.firstElementChild)return false;
if(document.querySelector('.portal-page,.mobile-topbar'))return true;
return charge&&(document.body.innerText||'').trim().length>4;}
function montrer(){if(fini||el)return;el=document.createElement('div');el.id='msf-charge';el.setAttribute('role','status');el.setAttribute('aria-label','Chargement');
el.style.cssText='--c-bg:'+c.bg+';--c-x:'+c.text+';--c-a:'+c.accent+';--c-l:'+c.border;
el.innerHTML='<div class="w">__PREFIXE__<span>__SUFFIXE__</span></div><div class="tr"><i></i></div><div class="lent" hidden>Connexion lente.<button type="button">Réessayer</button></div>';
el.querySelector('button').onclick=function(){location.reload();};
h.appendChild(el);}
function masquer(){if(fini)return;fini=true;clearInterval(v);clearTimeout(a);h.style.backgroundColor='';
if(el){el.classList.add('fin');var e=el;setTimeout(function(){e.remove();},200);}}
var nav=performance.getEntriesByType&&performance.getEntriesByType('navigation')[0];
var interne=false;try{interne=!!document.referrer&&new URL(document.referrer).origin===location.origin&&(!nav||nav.type==='navigate');
var t=sessionStorage.getItem('msf_charge_nav');if(t&&Date.now()-t<6000)interne=false;sessionStorage.removeItem('msf_charge_nav');}catch(e){}
var a=setTimeout(montrer,interne?250:0);if(!interne)montrer();
addEventListener('load',function(){charge=true;});
var v=setInterval(function(){if(pret())masquer();},50);
setTimeout(function(){if(!fini&&el)el.querySelector('.lent').hidden=false;},10000);
setTimeout(masquer,20000);
addEventListener('pageshow',function(e){if(e.persisted)masquer();});
// Toucher qui va changer de page : l'écran part de la page qu'on quitte.
function quitte(n){if(n.closest('.portal-app--busy,.portal-app--disabled,.portal-app--placeholder'))return false;
try{if(typeof _portalDragSuppressClick!=='undefined'&&_portalDragSuppressClick)return false;}catch(e){}
if(n.matches('a[href]')){if(n.hasAttribute('download')||(n.target&&n.target!=='_self'))return false;
var u=new URL(n.href,location.href);return u.origin===location.origin&&(u.protocol==='http:'||u.protocol==='https:')&&(u.pathname!==location.pathname)&&u.pathname.indexOf('/api/')!==0;}
if(n.matches('.mobile-home-btn'))return location.pathname!=='/';
return true;}
// Après les gestionnaires de la page : un lien repris par son routeur (MyCoûts, ERP)
// a annulé le clic, et ne change pas de page.
document.addEventListener('click',function(e){if(e.defaultPrevented&&!(e.target.closest&&e.target.closest('.portal-app,.mobile-home-btn')))return;
var n=e.target.closest&&e.target.closest('a[href],.mobile-home-btn,.portal-app[data-portal-id],.portal-vol-item,.portal-atraiter .msf-row,.portal-mach,[onclick*="location.href"]');
if(!n||!quitte(n))return;if(n.closest('.portal-apps-block--glisse'))return;
try{sessionStorage.setItem('msf_charge_nav',String(Date.now()));}catch(err){}
fini=false;el=null;h.style.backgroundColor=c.bg;montrer();
// La page n'a finalement pas changé : l'écran ne reste pas.
setTimeout(masquer,8000);});
})();"""


# Écrans d'iPhone : (largeur, hauteur, densité). iOS ne prend l'image que si la taille
# correspond exactement ; les images sont dans static/demarrage/, en clair et en sombre.
# iOS ne connaît pas la palette à ce stade : elles sont neutres (logo d'une seule teinte,
# sans dégradé), pour ne pas annoncer un thème qui n'est pas forcément celui de la personne.
_IPHONES = (
    (320, 568, 2), (375, 667, 2), (414, 736, 3), (375, 812, 3), (414, 896, 2), (414, 896, 3),
    (360, 780, 3), (390, 844, 3), (393, 852, 3), (428, 926, 3), (430, 932, 3), (402, 874, 3),
    (440, 956, 3),
)


@lru_cache(maxsize=1)
def images_demarrage() -> bytes:
    """Ce qu'iOS affiche avant même de charger la page, pour l'app installée."""
    balises = []
    for w, h, r in _IPHONES:
        ecran = (
            f"(device-width:{w}px) and (device-height:{h}px) and "
            f"(-webkit-device-pixel-ratio:{r}) and (orientation:portrait)"
        )
        for nom, mode in (("clair", "light"), ("sombre", "dark")):
            balises.append(
                f'<link rel="apple-touch-startup-image" media="{ecran} and (prefers-color-scheme:{mode})" '
                f'href="/static/demarrage/{w * r}x{h * r}_{nom}.png?v=2">'
            )
    return "".join(balises).encode("utf-8")


@lru_cache(maxsize=1)
def tete_de_page() -> bytes:
    """Ce que main.py pose en tête du <head>. Rien d'utilisateur n'y est interpolé."""
    try:
        with open(os.path.join(BASE_DIR, "static", "mysifa_theme.css"), encoding="utf-8") as f:
            themes = couleurs_des_themes(f.read())
    except OSError:
        themes = {"mysifa_s": _DEFAUT_COULEURS["s"], "mysifa_c": _DEFAUT_COULEURS["c"]}
    script = (
        _SCRIPT.replace("__THEMES__", json.dumps(themes, separators=(",", ":")))
        .replace("__PREFIXE__", APP_NAME_PREFIX)
        .replace("__SUFFIXE__", APP_NAME_SUFFIX)
    )
    return ("<style>%s</style><script>%s</script>" % (_STYLE, script)).encode("utf-8")
