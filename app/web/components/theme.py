# -*- coding: utf-8 -*-
"""
Source de verite unique du theme MySifa.

Avant ce module, le bloc `:root{...}` / `body.light{...}` etait redeclare dans
25 fichiers de app/web/. Chaque nouvelle page en recopiait une variante, et les
variantes divergeaient. Ici, il est ecrit une fois.

Deux usages :

    from app.web.components import bloc_tokens, T

    # 1. injecter les variables CSS en tete de page
    html = "<style>%s ...</style>" % bloc_tokens()

    # 2. referencer une couleur dans du CSS genere, sans jamais ecrire de hex
    css = "background:%s;color:%s;border:1px solid %s" % (T.CARD, T.TEXT, T.BORDER)

Le hook .claude/hooks/apres_edition.py refuse toute NOUVELLE couleur
hexadecimale ajoutee dans app/web/ ou static/*.css. Ce fichier-ci est la seule
exception legitime : c'est la definition. Ses lignes portent le marqueur
`hex-ok`, qui desamorce le controle.
"""


# --- Definition canonique -------------------------------------------------
# Reprise a l'identique de app/web/html.py (la coquille du portail), qui fait
# reference. Toute evolution du theme se fait ICI et nulle part ailleurs.

_SOMBRE = """:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --filter-input-bg:#1c2838;
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --pf-entree:#059669;--pf-sortie:#dc2626;
  --c1:#22d3ee;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171
}"""  # hex-ok : definition du theme sombre

_CLAIR = """body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --filter-input-bg:#ffffff;
  --success:#059669;--warn:#d24b00;--danger:#dc2626;
  --pf-entree:#047857;--pf-sortie:#b91c1c;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626
}"""  # hex-ok : definition du theme clair

TOKENS_CSS = _SOMBRE + "\n" + _CLAIR


def bloc_tokens(indent=""):
    """Retourne le bloc CSS des variables, pret a injecter dans un <style>."""
    if not indent:
        return TOKENS_CSS
    return "\n".join(indent + l for l in TOKENS_CSS.split("\n"))


# --- Reference semantique -------------------------------------------------
# Ecrire T.CARD plutot que "#111827" : la valeur suit le theme de
# l'utilisateur, et le passage en theme clair n'a plus besoin d'etre teste
# a la main a chaque ecran.

class T(object):
    """Variables CSS du theme, sous forme de chaines `var(--x)`."""

    BG = "var(--bg)"
    CARD = "var(--card)"
    BORDER = "var(--border)"
    TEXT = "var(--text)"
    TEXT2 = "var(--text2)"
    MUTED = "var(--muted)"

    ACCENT = "var(--accent)"
    ACCENT_BG = "var(--accent-bg)"
    FILTER_INPUT_BG = "var(--filter-input-bg)"

    SUCCESS = "var(--success)"
    OK = "var(--success)"
    WARN = "var(--warn)"
    DANGER = "var(--danger)"

    PF_ENTREE = "var(--pf-entree)"
    PF_SORTIE = "var(--pf-sortie)"

    # Serie categorielle, pour les graphes et les badges de categorie.
    SERIE = ("var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)")

    # Texte pose SUR un fond colore. `var(--bg)` bascule avec le theme, donc
    # il produit automatiquement un texte contraste dans les deux sens.
    # Ne JAMAIS utiliser T.TEXT ou T.TEXT2 sur un bouton a fond colore :
    # ils suivent le theme et deviennent invisibles dans l'un des deux.
    SUR_ACCENT = "var(--bg)"


def serie(i):
    """Couleur categorielle n(i), en boucle sur les 5 teintes de la serie."""
    return T.SERIE[i % len(T.SERIE)]
