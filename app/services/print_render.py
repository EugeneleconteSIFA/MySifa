"""
MySifa — moteur de rendu d'étiquettes pour le module impression cloud.

Prend un template texte (ZPL, EPL ou ESC-POS) contenant des placeholders
`{{clef}}` et un dictionnaire de données, retourne les bytes prêts à être
envoyés à l'imprimante par socket TCP:9100.

Placeholders spéciaux (résolus AVANT les placeholders simples) :
  - {{barcode:champ,format}}     ex. {{barcode:lot_numero,CODE128}}
  - {{qrcode:champ}}             ex. {{qrcode:lot_numero}}
  - {{now:strftime}}             ex. {{now:%d/%m/%Y}}

Les placeholders spéciaux ne sont interprétés qu'en ZPL. En EPL et ESC-POS,
ils sont convertis en équivalent le plus proche (les templates par défaut
livrés dans les migrations sont écrits en ZPL, langage principal).

Un template ZPL doit contenir sa propre commande ^XA ... ^XZ. Le moteur
n'ajoute AUCUN wrap : ce que tu écris est ce qui est envoyé (après
substitution). Cela laisse l'admin totalement libre de la mise en page.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


LANGAGES = ("zpl", "epl", "escpos")

# Placeholder simple : {{ clef }} ou {{ clef.sous_clef }} (support dot notation)
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
# Placeholder spécial : {{barcode:champ}}, {{barcode:champ,CODE128}}, etc.
_SPECIAL_RE = re.compile(r"\{\{\s*(barcode|qrcode|now)\s*:\s*([^}]+?)\s*\}\}")


def _lookup(data: dict, path: str) -> str:
    """Résout `a.b.c` en descendant dans le dict imbriqué. Retourne '' si absent."""
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return ""
        if cur is None:
            return ""
    return "" if cur is None else str(cur)


def _zpl_escape(s: str) -> str:
    """Échappe les caractères spéciaux ZPL. Le caractère `^` ouvre une commande
    et `~` ouvre une commande hôte. On les remplace par leur code ASCII via ^FH."""
    # Ordre important : ` ^ ~ sont les métacaractères ZPL par défaut.
    return (
        str(s)
        .replace("\\", "\\5c")
        .replace("^", "\\5e")
        .replace("~", "\\7e")
        .replace("\r", "")
        .replace("\n", "\\&")
    )


def _resolve_special(match: re.Match, data: dict, langage: str) -> str:
    kind = match.group(1)
    args = match.group(2).strip()

    if kind == "now":
        fmt = args or "%d/%m/%Y %H:%M"
        return datetime.now().strftime(fmt)

    if kind == "barcode":
        # args = "champ" ou "champ,FORMAT" ou "champ,FORMAT,HAUTEUR"
        parts = [p.strip() for p in args.split(",")]
        champ = parts[0]
        fmt = (parts[1] if len(parts) > 1 else "CODE128").upper()
        haut = parts[2] if len(parts) > 2 else "80"
        val = _lookup(data, champ)
        if not val:
            return ""
        val_z = _zpl_escape(val)
        if langage == "zpl":
            # Barcode128 par défaut ; sinon C39 (code39) comme fallback simple.
            if fmt in ("CODE128", "C128", "BARCODE128"):
                # ^BY2 : module width 2 ; ^BCN,haut,Y,N,N : orientation Normal,
                # hauteur, human-readable, above=N, check=N
                return f"^BY2^BCN,{haut},Y,N,N^FD{val_z}^FS"
            if fmt in ("CODE39", "C39"):
                return f"^BY2^B3N,N,{haut},Y,N^FD{val_z}^FS"
            if fmt == "EAN13":
                return f"^BY2^BEN,{haut},Y,N^FD{val_z}^FS"
            # Défaut : CODE128
            return f"^BY2^BCN,{haut},Y,N,N^FD{val_z}^FS"
        # EPL / ESC-POS : on renvoie juste la valeur texte, l'admin doit adapter
        # son template au langage cible.
        return val
    if kind == "qrcode":
        val = _lookup(data, args)
        if not val:
            return ""
        val_z = _zpl_escape(val)
        if langage == "zpl":
            # ^BQN,2,6 : QR normal orientation, model 2, magnification 6
            return f"^BQN,2,6^FDLA,{val_z}^FS"
        return val
    return match.group(0)


def render_template(template: str, data: dict, langage: str = "zpl") -> bytes:
    """Rend un template en bytes prêts à envoyer à l'imprimante.

    Passe deux fois :
      1. Résolution des placeholders spéciaux ({{barcode:...}}, {{qrcode:...}}, {{now:...}})
      2. Résolution des placeholders simples ({{champ}}, {{champ.sous_champ}})

    Les valeurs sont automatiquement échappées pour ZPL (caractères ^, ~, \\,
    retours ligne). Pour les autres langages, on renvoie la valeur telle quelle.
    """
    if langage not in LANGAGES:
        raise ValueError(f"Langage inconnu : {langage!r}. Attendu : {LANGAGES}")
    if template is None:
        template = ""
    if data is None:
        data = {}

    # Étape 1 : placeholders spéciaux
    rendered = _SPECIAL_RE.sub(lambda m: _resolve_special(m, data, langage), template)

    # Étape 2 : placeholders simples
    def _repl(m: re.Match) -> str:
        val = _lookup(data, m.group(1))
        if langage == "zpl":
            return _zpl_escape(val)
        return str(val)

    rendered = _PLACEHOLDER_RE.sub(_repl, rendered)

    # Encodage : ZPL et EPL sont ASCII étendu (CP850), ESC-POS accepte UTF-8 sur
    # imprimantes modernes. On tolère les caractères non-représentables.
    if langage == "zpl":
        return rendered.encode("cp850", errors="replace")
    if langage == "epl":
        return rendered.encode("cp850", errors="replace")
    return rendered.encode("utf-8", errors="replace")


# ── Templates par défaut livrés dans la migration ──────────────────────
#
# Template ZPL 4"×6" (102×152mm) 203 dpi pour la réception matière SIFA.
# Dimensions en points : 812 × 1218 (203 dpi × 4" × 6")
# Placeholders utilisés :
#   {{lot_numero}}         — numéro de lot auto-généré
#   {{fournisseur}}        — nom fournisseur
#   {{fsc_label}}          — libellé statut FSC ("FSC 100%", "Non FSC", …)
#   {{fsc_banner}}         — "MATIERE FSC" ou "MATIERE NON FSC"
#   {{ref_produit}}        — référence produit (optionnel)
#   {{code_barre}}         — code-barres bobine
#   {{operateur_nom}}      — nom de l'opérateur qui a validé
#   {{date_reception}}     — date de réception format "dd/mm/yyyy"
#
DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL = """^XA
^CI28
^PW812
^LL1218
^LH0,0
^FO40,40^GB732,1138,4^FS
^FO60,70^A0N,40,40^FDIDENTIFICATION BOBINE^FS
^FO60,120^GB692,3,3^FS
^FO60,150^A0N,55,55^FD{{fsc_banner}}^FS
^FO60,240^A0N,26,26^FDReference produit^FS
^FO60,280^A0N,45,45^FD{{ref_produit}}^FS
^FO60,360^A0N,26,26^FDFournisseur^FS
^FO60,400^A0N,42,42^FD{{fournisseur}}^FS
^FO60,480^A0N,26,26^FDStatut FSC^FS
^FO60,520^A0N,40,40^FD{{fsc_label}}^FS
^FO60,600^A0N,26,26^FDN de lot^FS
^FO60,640^A0N,40,40^FD{{lot_numero}}^FS
^FO60,730^A0N,26,26^FDCode-barres bobine^FS
^FO60,770^BY3^BCN,140,Y,N,N^FD{{code_barre}}^FS
^FO60,970^A0N,22,22^FDReception le {{date_reception}} par {{operateur_nom}}^FS
^FO60,1010^A0N,22,22^FDSIFA^FS
^XZ
"""


def default_templates_seed() -> list[dict]:
    """Liste des templates par défaut à seeder à la première configuration
    d'une imprimante ZPL. Le seed est appliqué depuis app/routers/print.py
    quand l'admin crée sa première imprimante, pas en migration, car il faut
    connaître l'imprimante_id."""
    return [
        {
            "usage_key": "reception_matiere",
            "nom": "Étiquette réception matière",
            "contenu": DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL,
        },
    ]


# ── Registre des usages métier ─────────────────────────────────────────
# Une clé d'usage = un contexte métier où on peut imprimer une étiquette.
# Les libellés sont utilisés dans l'UI (config imprimantes par défaut et
# éditeur de template).
USAGES = [
    {
        "key": "reception_matiere",
        "label": "Réception matière — identification bobine",
        "module": "stock",
        "placeholders": [
            "lot_numero", "fournisseur", "fsc_label", "fsc_banner",
            "ref_produit", "code_barre", "operateur_nom", "date_reception",
            "{{barcode:code_barre}}", "{{barcode:lot_numero,CODE128,140}}",
            "{{qrcode:lot_numero}}", "{{now:%d/%m/%Y}}",
        ],
    },
    # À venir : etiquette_of (MyProd), etiquette_colis (MyExpé),
    # etiquette_emplacement (MyStock), etc.
]


def usage_label(key: str) -> str:
    for u in USAGES:
        if u["key"] == key:
            return u["label"]
    return key
