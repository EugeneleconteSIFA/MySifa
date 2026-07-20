"""
MySifa — Modal d'impression PDF partage (v1.7).

Lit les fichiers static `mysifa_print_modal.css` et `mysifa_print_modal.js`
(source unique de verite, aussi charges par prod_page.py via <link>/<script>)
et les expose en constantes pour les pages qui integrent le modal en INLINE
(fabrication_page.py).

Cote frontend, appeler :

    openPrintModal({
        entityType: 'of' | 'fiche',
        entityId: 42,
        title: 'Imprimer OF-2026-042',           // affiche dans l'entete
        subtitle: 'Client Machin — Ref XYZ',     // optionnel
    });

Le popup se charge du reste : liste des imprimantes (langage=pdf uniquement),
defauts utilisateur, params (copies/duplex/format/bac/N&B), soumission a
POST /api/print/pdf, toasts de succes/erreur.

Le popup depend de :
  - api(path, opts)  OU  apiFetch(path, opts)  — helpers HTTP MySifa
  - toast(msg, type) OU  showToast(msg, type)  — snifes par _mysifaPrintToast
"""

from __future__ import annotations

from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════
# Chargement depuis static/ (source unique de verite)
# ═══════════════════════════════════════════════════════════════════════
# Chemin : app/web/print_modal.py → ../../static/mysifa_print_modal.{css,js}

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
_CSS_PATH = _STATIC_DIR / "mysifa_print_modal.css"
_JS_PATH = _STATIC_DIR / "mysifa_print_modal.js"


def _read_or_empty(path: Path, kind: str) -> str:
    """Lit un fichier static et le renvoie en str. En cas d'echec, log un
    warning et renvoie un commentaire d'erreur — evite un crash du serveur
    si un fichier est absent (dev mode ou install partielle)."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return (
            f"/* MySifa print modal — {kind} indisponible : {e} */"
            if kind == "CSS"
            else
            f"// MySifa print modal — {kind} indisponible : {e}"
        )


PRINT_MODAL_CSS = _read_or_empty(_CSS_PATH, "CSS")
PRINT_MODAL_JS = _read_or_empty(_JS_PATH, "JS")


def print_modal_bundle() -> tuple[str, str]:
    """Renvoie le tuple (css, js) a injecter dans une page qui veut le modal
    en INLINE (patterns anciens comme fabrication_page.py qui compose un
    template geant).

    Les pages modernes (prod_page.py) chargent directement les fichiers
    static via <link rel="stylesheet"> et <script src=""> — pas besoin
    d'appeler cette fonction.
    """
    return PRINT_MODAL_CSS, PRINT_MODAL_JS
