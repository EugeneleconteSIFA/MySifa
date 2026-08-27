"""
Fragments HTML/CSS partages entre les pages MySifa.

Regle : une page de app/web/ n'ecrit plus de HTML ni de CSS qui existe deja
ici. Quand un fragment est utilise par deux pages, il descend dans ce paquet
et les deux pages l'importent.

Voir app/web/components/README.md.
"""

from app.web.components.theme import T, TOKENS_CSS, bloc_tokens  # noqa: F401
