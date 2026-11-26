"""Site vitrine : synchronise les blocs partagés de toutes les pages.

Les pages vivent dans app/web/website/<chemin>/index.html et restent les
fichiers que l'on édite. Ce script ne réécrit que les blocs balisés :

    <!-- @head -->     ... <!-- /@head -->     métadonnées, canonical, Open Graph, JSON-LD
    <!-- @header -->   ... <!-- /@header -->   en-tête (_partials/header.html)
    <!-- @crumbs -->   ... <!-- /@crumbs -->   fil d'Ariane visible (sous-pages)
    <!-- @footer -->   ... <!-- /@footer -->   pied de page (_partials/footer.html)
    <!-- @scripts -->  ... <!-- /@scripts -->  site.js

Les titres, descriptions et l'ordre des pages sont dans _partials/site.json.
Chaque page existe en français et en anglais : la clé « en » du registre donne
le chemin, le titre et la description de la version anglaise (sous en/), qui
utilise _partials/header.en.html et footer.en.html. Les deux versions se
répondent par des liens hreflang et par le sélecteur FR | EN de l'en-tête.
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


LANGUES = ("fr", "en")
TXT = {
    "fr": {"accueil": "Accueil", "ariane": "Fil d'Ariane", "langue": "Langue",
           "og_locale": "fr_FR", "in_lang": "fr-FR",
           "og_alt": "SIFA, fabricant et enducteur d'étiquettes adhésives à Roubaix",
           "desc_lb": "Fabricant et enducteur d'étiquettes adhésives à Roubaix depuis 1987."},
    "en": {"accueil": "Home", "ariane": "Breadcrumb", "langue": "Language",
           "og_locale": "en_GB", "in_lang": "en-GB",
           "og_alt": "SIFA, self-adhesive label manufacturer and coater in Roubaix, France",
           "desc_lb": "Self-adhesive label manufacturer and coater in Roubaix, France, since 1987."},
}


def vue(page, lang):
    """La page dans une langue : path, crumb, title, description, nav, lang, fr, en."""
    v = dict(page) if lang == "fr" else {**page["en"], "nav": page["nav"], "priority": page["priority"]}
    v["lang"] = lang
    v["fr"], v["en"] = page["path"], page["en"]["path"]
    return v


def vues(reg, lang):
    return [vue(p, lang) for p in reg["pages"]]


def racine_relative(chemin):
    profondeur = chemin.count("/")
    return "./" if profondeur == 0 else "../" * profondeur


def empreinte(nom):
    return hashlib.sha1((STATIC / nom).read_bytes()).hexdigest()[:8]


def esc(t):
    return html.escape(t, quote=True)


def json_ld(reg, page):
    base = reg["base_url"]
    t = TXT[page["lang"]]
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
            "address": adresse,
            "sameAs": ["https://www.linkedin.com/company/sifa-france/"],
        },
        {
            "@type": "LocalBusiness",
            "@id": base + "#roubaix",
            "name": "SIFA",
            "description": t["desc_lb"],
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
            "inLanguage": t["in_lang"],
            "publisher": {"@id": org_id},
        },
    ]
    if page["path"] not in ("", "en/"):
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
    """[(nom, chemin)] de l'accueil à la page, dans la langue de la page."""
    lang = page["lang"]
    par_chemin = {v["path"]: v for v in vues(reg, lang)}
    accueil = "" if lang == "fr" else "en/"
    etapes = [(TXT[lang]["accueil"], accueil)]
    cumul = ""
    for m in page["path"].strip("/").split("/"):
        cumul += m + "/"
        if cumul in par_chemin and cumul != accueil:
            etapes.append((par_chemin[cumul]["crumb"], cumul))
    return etapes


def bloc_head(reg, page, v_css):
    base = reg["base_url"]
    url = base + page["path"]
    img = base + reg["og_image"].lstrip("/")
    t, d = esc(page["title"]), esc(page["description"])
    tx = TXT[page["lang"]]
    autre = "en_GB" if page["lang"] == "fr" else "fr_FR"
    return f"""<meta name="robots" content="noindex, nofollow">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{base}{page["fr"]}">
<link rel="alternate" hreflang="en" href="{base}{page["en"]}">
<link rel="alternate" hreflang="x-default" href="{base}{page["fr"]}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{tx["og_locale"]}">
<meta property="og:locale:alternate" content="{autre}">
<meta property="og:site_name" content="SIFA">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(tx["og_alt"])}">
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


def bloc_langues(page):
    """Sélecteur FR | EN : lien vers la même page dans chaque langue."""
    root = racine_relative(page["path"])
    liens = []
    for lang, nom, titre in (("fr", "FR", "Version française"), ("en", "EN", "English version")):
        cur = ' aria-current="true"' if lang == page["lang"] else ""
        liens.append(f'<a href="{root}{page[lang]}" hreflang="{lang}" lang="{lang}" title="{titre}"{cur}>{nom}</a>')
    return f'<nav class="lang-sw" aria-label="{TXT[page["lang"]]["langue"]}">' + "".join(liens) + "</nav>"


def bloc_partiel(nom, page):
    if page["lang"] != "fr":
        nom = nom.replace(".html", f".{page['lang']}.html")
    s = (PARTIALS / nom).read_text(encoding="utf-8")
    s = s.replace("{{langswitch}}", bloc_langues(page))
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
    return f'<nav class="crumbs" aria-label="{esc(TXT[page["lang"]]["ariane"])}"><ol>' + "".join(items) + "</ol></nav>"


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
    lang = re.search(r'<html lang="(\w+)"', texte)
    if not lang:
        alertes.append("attribut lang absent")
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
    toutes = [v for lang in LANGUES for v in vues(reg, lang)]
    for page in toutes:
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
        if f'<html lang="{page["lang"]}"' not in s:
            alertes.append(f"{page['path'] or '/'} : <html lang=\"{page['lang']}\"> attendu")
        if s != avant:
            ecarts += 1
            if not check:
                f.write_text(s, encoding="utf-8", newline="\n")
    for a in alertes:
        print("ATTENTION", a)
    print(f"{len(toutes)} pages, {ecarts} {'à mettre à jour' if check else 'mises à jour'}"
          f" (site.css?v={v_css}, site.js?v={v_js})")
    if check and (ecarts or alertes):
        sys.exit(1)


if __name__ == "__main__":
    main()
