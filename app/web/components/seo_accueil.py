"""Balises de référencement de la page d'accueil publique (« / » de la prod).

Canonical, Open Graph et données structurées. Les autres pages et les autres
instances reçoivent « noindex » (voir SEO_INDEXABLE dans config.py et le
middleware noindex_hors_accueil de main.py).
"""
import json
from html import escape

from config import (
    APP_AUTHOR_NAME,
    APP_AUTHOR_URL,
    APP_META_DESCRIPTION,
    APP_NAME,
    APP_OG_IMAGE,
    APP_ORG_NAME,
    APP_PAGE_TITLE,
    public_base_url,
)

NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def seo_head() -> str:
    base = public_base_url()
    img = APP_OG_IMAGE if APP_OG_IMAGE.startswith("http") else base + APP_OG_IMAGE
    ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": APP_NAME, "url": base + "/",
          "description": APP_META_DESCRIPTION, "applicationCategory": "BusinessApplication", "operatingSystem": "Web",
          "inLanguage": "fr", "publisher": {"@type": "Organization", "name": APP_ORG_NAME},
          "author": {"@type": "Person", "name": APP_AUTHOR_NAME, "url": APP_AUTHOR_URL}}
    return "\n".join([
        f'<link rel="canonical" href="{base}/">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{escape(APP_NAME)}">',
        '<meta property="og:locale" content="fr_FR">',
        f'<meta property="og:title" content="{escape(APP_PAGE_TITLE)}">',
        f'<meta property="og:description" content="{escape(APP_META_DESCRIPTION)}">',
        f'<meta property="og:url" content="{base}/">',
        f'<meta property="og:image" content="{escape(img)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>",
    ])
