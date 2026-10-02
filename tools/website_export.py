"""Export statique du site vitrine pour l'hébergement web Hostinger (public_html).

Produit un dossier et un zip prêts à déposer à la racine de www.sifapro.fr :
  - les pages de app/web/website/ sans la balise meta robots noindex ;
  - static/website/ réduit aux fichiers que les pages utilisent ;
  - sitemap.xml, robots.txt, .htaccess, 404.html.

Ne touche pas à la base : n'importe ni `database` ni `app.*`.

    python3 tools/website_build.py --check      # blocs partagés à jour ?
    python3 tools/website_export.py <dossier_de_sortie>
"""
import datetime as dt
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "app" / "web" / "website"
STATIC = ROOT / "static" / "website"

HTACCESS = """# SIFA · www.sifapro.fr · généré par tools/website_export.py
Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html
AddDefaultCharset UTF-8

<IfModule mod_rewrite.c>
RewriteEngine On

# HTTPS et www forcés (une seule adresse canonique)
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} !^www\\. [NC]
RewriteRule ^ https://www.sifapro.fr%{REQUEST_URI} [L,R=301]

# Anciennes adresses du site Hostinger Website Builder (sans barre finale)
RewriteRule ^contact$ /contact/ [L,R=301]
RewriteRule ^notre-histoire$ /notre-histoire/ [L,R=301]
</IfModule>

# Compression
<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript text/javascript application/json image/svg+xml text/xml application/xml text/plain
</IfModule>

# Cache : longue durée pour les images (noms stables) et pour CSS/JS (versionnés par ?v=),
# court pour le HTML afin qu'une mise à jour soit vue tout de suite.
<IfModule mod_expires.c>
ExpiresActive On
ExpiresDefault "access plus 1 hour"
ExpiresByType text/html "access plus 0 seconds"
ExpiresByType text/css "access plus 1 year"
ExpiresByType application/javascript "access plus 1 year"
ExpiresByType text/javascript "access plus 1 year"
ExpiresByType image/jpeg "access plus 1 year"
ExpiresByType image/png "access plus 1 year"
ExpiresByType image/svg+xml "access plus 1 year"
ExpiresByType font/woff2 "access plus 1 year"
ExpiresByType application/xml "access plus 1 day"
ExpiresByType text/xml "access plus 1 day"
</IfModule>
<IfModule mod_headers.c>
<FilesMatch "\\.(jpe?g|png|svg|woff2|css|js)$">
Header set Cache-Control "public, max-age=31536000, immutable"
</FilesMatch>
<FilesMatch "\\.html$">
Header set Cache-Control "no-cache"
</FilesMatch>
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
"""


def pages(reg):
    for p in reg["pages"]:
        yield p, SITE / p["path"] / "index.html"


def page_404(accueil_html):
    """404 à partir de l'accueil : même tête et même en-tête, contenu minimal."""
    s = accueil_html
    s = re.sub(r"<title>.*?</title>", "<title>Page introuvable | SIFA</title>", s, count=1, flags=re.S)
    s = re.sub(r'<link rel="canonical"[^>]*>\n?', "", s, count=1)
    s = s.replace('<meta name="description"', '<meta name="robots" content="noindex">\n<meta name="description"', 1)
    corps = ('<main id="main"><section class="sec page-hero"><div class="wrap" style="display:block">'
             '<span class="eyebrow">Erreur 404</span><h1>Cette page n\'existe pas ou a été déplacée.</h1>'
             '<p class="lead">Le site de SIFA a été refondu en 2026. Les pages produits ont changé d\'adresse.</p>'
             '<div class="hero-cta"><a class="btn btn-primary" href="/">Accueil</a>'
             '<a class="btn btn-second" href="/produits/">Nos produits</a>'
             '<a class="btn btn-second" href="/contact/">Contact</a></div></div></section></main>')
    s = re.sub(r'<main id="main">.*?</main>', corps, s, count=1, flags=re.S)
    # Servie à n'importe quelle profondeur : liens absolus depuis la racine.
    s = s.replace('href="./', 'href="/')
    return s


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit("Le dossier de sortie doit être hors du dépôt.")
    reg = json.loads((SITE / "_partials" / "site.json").read_text(encoding="utf-8"))
    base = reg["base_url"]
    site_dir = out / "public_html"
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)

    utilises, erreurs = set(), []
    accueil = None
    for p, f in pages(reg):
        if not f.exists():
            erreurs.append(f"page absente : {p['path'] or '/'}")
            continue
        s = f.read_text(encoding="utf-8")
        s2 = re.sub(r'<meta name="robots" content="noindex, nofollow">\n?', "", s)
        if s2 == s:
            erreurs.append(f"{p['path'] or '/'} : meta noindex introuvable (blocs à jour ?)")
        attendu = f'<link rel="canonical" href="{base}{p["path"]}">'
        if attendu not in s2:
            erreurs.append(f"{p['path'] or '/'} : canonical attendu {attendu}")
        utilises |= set(re.findall(r"/static/website/([\w.\-]+)", s2))
        cible = site_dir / p["path"] / "index.html"
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(s2, encoding="utf-8", newline="\n")
        if p["path"] == "":
            accueil = s2

    # Fichiers référencés depuis la feuille de style et le JSON-LD
    css = (STATIC / "site.css").read_text(encoding="utf-8")
    utilises |= set(re.findall(r"/static/website/([\w.\-]+)", css))
    utilises |= {"logo-sifa-400.png", Path(reg["og_image"]).name}
    (site_dir / "static" / "website").mkdir(parents=True)
    for nom in sorted(utilises):
        src = STATIC / nom
        if not src.exists():
            erreurs.append(f"fichier statique absent : {nom}")
            continue
        shutil.copy2(src, site_dir / "static" / "website" / nom)

    if accueil:
        (site_dir / "404.html").write_text(page_404(accueil), encoding="utf-8", newline="\n")

    jour = dt.date.today().isoformat()
    urls = "".join(
        f"  <url><loc>{base}{p['path']}</loc><lastmod>{jour}</lastmod><priority>{p['priority']}</priority></url>\n"
        for p in reg["pages"])
    (site_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
        encoding="utf-8", newline="\n")
    (site_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n", encoding="utf-8", newline="\n")
    (site_dir / ".htaccess").write_text(HTACCESS, encoding="utf-8", newline="\n")

    zip_path = out / "sifapro-public_html.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(site_dir.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(site_dir).as_posix())

    taille = sum(f.stat().st_size for f in site_dir.rglob("*") if f.is_file())
    print(f"{len(reg['pages'])} pages, {len(utilises)} fichiers statiques, {taille // 1024} Ko")
    print(f"dossier : {site_dir}")
    print(f"zip     : {zip_path} ({zip_path.stat().st_size // 1024} Ko)")
    for e in erreurs:
        print("ERREUR", e)
    if erreurs:
        sys.exit(1)


if __name__ == "__main__":
    main()
