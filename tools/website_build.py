"""Site vitrine : synchronise les blocs partagés de toutes les pages.

Les pages vivent dans app/web/website/<chemin>/index.html et restent les
fichiers que l'on édite. Ce script ne réécrit que les blocs balisés :

    <!-- @head -->     ... <!-- /@head -->     métadonnées, canonical, Open Graph, JSON-LD
    <!-- @header -->   ... <!-- /@header -->   en-tête (_partials/header.html)
    <!-- @crumbs -->   ... <!-- /@crumbs -->   fil d'Ariane visible (sous-pages)
    <!-- @footer -->   ... <!-- /@footer -->   pied de page (_partials/footer.html)
    <!-- @scripts -->  ... <!-- /@scripts -->  site.js

Les titres, descriptions et l'ordre des pages sont dans _partials/site.json.
Les liens entre pages sont relatifs ({{root}}) pour que les mêmes fichiers
marchent sous /website/ (aperçu MySifa) et à la racine de www.sifapro.fr.

    python3 tools/website_build.py           # réécrit les blocs
    python3 tools/website_build.py --check   # signale sans écrire (code 1 si écart)
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "app" / "web" / "website"
PARTIALS = SITE / "_partials"
STATIC = ROOT / "static" / "website"

FONTS = ("https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,500..600"
         "&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap")


def charger_registre():
    return json.loads((PARTIALS / "site.json").read_text(encoding="utf-8"))


def racine_relative(chemin):
    profondeur = chemin.count("/")
    return "./" if profondeur == 0 else "../" * profondeur


def empreinte(nom):
    return hashlib.sha1((STATIC / nom).read_bytes()).hexdigest()[:8]


def esc(t):
    return html.escape(t, quote=True)


def json_ld(reg, page):
    base = reg["base_url"]
    org_id = base + "#organization"
    adresse = {
        "@type": "PostalAddress",
        "streetAddress": "45 rue Rollin",
        "postalCode": "59100",
        "addressLocality": "Roubaix",
        "addressCountry": "FR",
    }
    graphe = [
        {
            "@type": "Organization",
            "@id": org_id,
            "name": "SIFA",
            "url": base,
            "logo": {"@type": "ImageObject", "url": base + "static/website/logo-sifa-400.png",
                     "width": 400, "height": 213},
            "foundingDate": "1987",
            "email": "contact@sifa.pro",
            "telephone": "+33 3 20 69 01 01",
            "faxNumber": "+33 3 20 68 33 20",
            "address": adresse,
            "sameAs": ["https://www.linkedin.com/company/sifa-france/"],
        },
        {
            "@type": "LocalBusiness",
            "@id": base + "#roubaix",
            "name": "SIFA",
            "description": "Fabricant et enducteur d'étiquettes adhésives à Roubaix depuis 1987.",
            "url": base,
            "image": base + reg["og_image"].lstrip("/"),
            "telephone": "+33 3 20 69 01 01",
            "email": "contact@sifa.pro",
            "address": adresse,
            "parentOrganization": {"@id": org_id},
        },
        {
            "@type": "WebSite",
            "@id": base + "#website",
            "url": base,
            "name": "SIFA",
            "inLanguage": "fr-FR",
            "publisher": {"@id": org_id},
        },
    ]
    if page["path"]:
        graphe.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": nom, "item": base + chemin}
                for i, (nom, chemin) in enumerate(fil(reg, page))
            ],
        })
    data = {"@context": "https://schema.org", "@graph": graphe}
    return json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")


def fil(reg, page):
    """[(nom, chemin)] de l'accueil à la page."""
    par_chemin = {p["path"]: p for p in reg["pages"]}
    etapes = [("Accueil", "")]
    morceaux = page["path"].strip("/").split("/")
    cumul = ""
    for m in morceaux:
        cumul += m + "/"
        if cumul in par_chemin:
            etapes.append((par_chemin[cumul]["crumb"], cumul))
    return etapes


def bloc_head(reg, page, v_css):
    base = reg["base_url"]
    url = base + page["path"]
    img = base + reg["og_image"].lstrip("/")
    t, d = esc(page["title"]), esc(page["description"])
    return f"""<meta name="robots" content="noindex, nofollow">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="SIFA">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="SIFA, fabricant et enducteur d'étiquettes adhésives à Roubaix">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{img}">
<meta name="theme-color" content="#0A0E17">
<link rel="icon" type="image/png" sizes="32x32" href="/static/website/favicon-32.png">
<link rel="apple-touch-icon" href="/static/website/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="/static/website/site.css?v={v_css}">
<script>try{{var t=localStorage.getItem('sifa-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}}catch(e){{}}</script>
<script type="application/ld+json">
{json_ld(reg, page)}
</script>"""


def bloc_partiel(nom, page):
    s = (PARTIALS / nom).read_text(encoding="utf-8")
    s = s.replace("{{root}}", racine_relative(page["path"]))
    for cle in ("savoir", "produits", "engagements", "entreprise"):
        s = s.replace("{{cur:%s}}" % cle, ' aria-current="page"' if page.get("nav") == cle else "")
    return s.rstrip("\n")


def bloc_crumbs(reg, page):
    etapes = fil(reg, page)
    root = racine_relative(page["path"])
    items = []
    for i, (nom, chemin) in enumerate(etapes):
        if i == len(etapes) - 1:
            items.append(f'<li><span aria-current="page">{esc(nom)}</span></li>')
        else:
            items.append(f'<li><a href="{root}{chemin}">{esc(nom)}</a></li>')
    return '<nav class="crumbs" aria-label="Fil d\'Ariane"><ol>' + "".join(items) + "</ol></nav>"


def remplacer(texte, nom, contenu, obligatoire=True):
    motif = re.compile(r"(<!-- @%s -->)(.*?)(<!-- /@%s -->)" % (nom, nom), re.S)
    if not motif.search(texte):
        if obligatoire:
            raise SystemExit(f"bloc <!-- @{nom} --> absent")
        return texte
    return motif.sub(lambda m: m.group(1) + "\n" + contenu + "\n" + m.group(3), texte, count=1)


def controler(nom, texte):
    alertes = []
    corps = re.sub(r"<script.*?</script>", "", texte, flags=re.S)
    n_h1 = len(re.findall(r"<h1[\s>]", corps))
    if n_h1 != 1:
        alertes.append(f"{n_h1} balises h1")
    for img in re.findall(r"<img\b[^>]*>", corps):
        if 'alt="' not in img:
            alertes.append("image sans alt : " + img[:80])
        if 'width="' not in img or 'height="' not in img:
            alertes.append("image sans width/height : " + img[:80])
    if 'href="#"' in corps.replace('href="#main"', ""):
        pass  # liens légaux en attente : signalés par les placeholders
    return [f"{nom} : {a}" for a in alertes]


def main():
    check = "--check" in sys.argv
    reg = charger_registre()
    v_css, v_js = empreinte("site.css"), empreinte("site.js")
    ecarts, alertes = 0, []
    for page in reg["pages"]:
        f = SITE / page["path"] / "index.html"
        if not f.exists():
            alertes.append(f"{page['path'] or '/'} : fichier absent")
            continue
        avant = f.read_text(encoding="utf-8")
        s = remplacer(avant, "head", bloc_head(reg, page, v_css))
        s = remplacer(s, "header", bloc_partiel("header.html", page))
        s = remplacer(s, "footer", bloc_partiel("footer.html", page))
        s = remplacer(s, "crumbs", bloc_crumbs(reg, page), obligatoire=False)
        s = remplacer(s, "scripts", f'<script src="/static/website/site.js?v={v_js}" defer></script>')
        alertes += controler(page["path"] or "/", s)
        if s != avant:
            ecarts += 1
            if not check:
                f.write_text(s, encoding="utf-8", newline="\n")
    for a in alertes:
        print("ATTENTION", a)
    print(f"{len(reg['pages'])} pages, {ecarts} {'à mettre à jour' if check else 'mises à jour'}"
          f" (site.css?v={v_css}, site.js?v={v_js})")
    if check and (ecarts or alertes):
        sys.exit(1)


if __name__ == "__main__":
    main()
