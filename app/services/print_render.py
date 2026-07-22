"""
MySifa â€” moteur de rendu d'Ã©tiquettes pour le module impression cloud.

Prend un template texte (ZPL, EPL ou ESC-POS) contenant des placeholders
`{{clef}}` et un dictionnaire de donnÃ©es, retourne les bytes prÃªts Ã  Ãªtre
envoyÃ©s Ã  l'imprimante par socket TCP:9100.

Placeholders spÃ©ciaux (rÃ©solus AVANT les placeholders simples) :
  - {{barcode:champ,format}}     ex. {{barcode:lot_numero,CODE128}}
  - {{qrcode:champ}}             ex. {{qrcode:lot_numero}}
  - {{now:strftime}}             ex. {{now:%d/%m/%Y}}

Les placeholders spÃ©ciaux ne sont interprÃ©tÃ©s qu'en ZPL. En EPL et ESC-POS,
ils sont convertis en Ã©quivalent le plus proche (les templates par dÃ©faut
livrÃ©s dans les migrations sont Ã©crits en ZPL, langage principal).

Un template ZPL doit contenir sa propre commande ^XA ... ^XZ. Le moteur
n'ajoute AUCUN wrap : ce que tu Ã©cris est ce qui est envoyÃ© (aprÃ¨s
substitution). Cela laisse l'admin totalement libre de la mise en page.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


# v1.7 â€” ajout de "pdf" pour l'impression de documents bureautiques (OF, fiches
# techniques) vers des imprimantes A4/A3 laser/jet. Le langage "pdf" est un
# passthrough : les bytes du PDF sont stockes tels quels dans print_jobs.payload
# et transmis a l'agent, qui les envoie a SumatraPDF pour impression sur la
# queue Windows cible (avec params copies/duplex/format/bac/N&B via data_json).
LANGAGES = ("zpl", "epl", "escpos", "pdf")

# Placeholder simple : {{ clef }} ou {{ clef.sous_clef }} (support dot notation)
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
# Placeholder spÃ©cial : {{barcode:champ}}, {{barcode:champ,CODE128}}, etc.
_SPECIAL_RE = re.compile(r"\{\{\s*(barcode|qrcode|now)\s*:\s*([^}]+?)\s*\}\}")


def _lookup(data: dict, path: str) -> str:
    """RÃ©sout `a.b.c` en descendant dans le dict imbriquÃ©. Retourne '' si absent."""
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
    """Ã‰chappe les caractÃ¨res spÃ©ciaux ZPL. Le caractÃ¨re `^` ouvre une commande
    et `~` ouvre une commande hÃ´te. On les remplace par leur code ASCII via ^FH."""
    # Ordre important : ` ^ ~ sont les mÃ©tacaractÃ¨res ZPL par dÃ©faut.
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
            # Barcode128 par dÃ©faut ; sinon C39 (code39) comme fallback simple.
            if fmt in ("CODE128", "C128", "BARCODE128"):
                # ^BY2 : module width 2 ; ^BCN,haut,Y,N,N : orientation Normal,
                # hauteur, human-readable, above=N, check=N
                return f"^BY2^BCN,{haut},Y,N,N^FD{val_z}^FS"
            if fmt in ("CODE39", "C39"):
                return f"^BY2^B3N,N,{haut},Y,N^FD{val_z}^FS"
            if fmt == "EAN13":
                return f"^BY2^BEN,{haut},Y,N^FD{val_z}^FS"
            # DÃ©faut : CODE128
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
    """Rend un template en bytes prÃªts Ã  envoyer Ã  l'imprimante.

    Passe deux fois :
      1. RÃ©solution des placeholders spÃ©ciaux ({{barcode:...}}, {{qrcode:...}}, {{now:...}})
      2. RÃ©solution des placeholders simples ({{champ}}, {{champ.sous_champ}})

    Les valeurs sont automatiquement Ã©chappÃ©es pour ZPL (caractÃ¨res ^, ~, \\,
    retours ligne). Pour les autres langages, on renvoie la valeur telle quelle.
    """
    if langage not in LANGAGES:
        raise ValueError(f"Langage inconnu : {langage!r}. Attendu : {LANGAGES}")
    # v1.7 â€” le langage "pdf" ne rend pas de template : les bytes du PDF sont
    # fournis directement par l'endpoint POST /api/print/pdf. render_template
    # n'est jamais appele pour un job PDF (l'endpoint stocke directement le
    # blob dans print_jobs.payload). Si on arrive ici avec langage=pdf, c'est
    # que quelqu'un a mal cable l'appel â€” on remonte une erreur explicite.
    if langage == "pdf":
        raise ValueError(
            "Le langage 'pdf' ne s'utilise pas via render_template. "
            "Utilise l'endpoint POST /api/print/pdf pour soumettre un job PDF."
        )
    if template is None:
        template = ""
    if data is None:
        data = {}

    # Ã‰tape 1 : placeholders spÃ©ciaux
    rendered = _SPECIAL_RE.sub(lambda m: _resolve_special(m, data, langage), template)

    # Ã‰tape 2 : placeholders simples
    def _repl(m: re.Match) -> str:
        val = _lookup(data, m.group(1))
        if langage == "zpl":
            return _zpl_escape(val)
        return str(val)

    rendered = _PLACEHOLDER_RE.sub(_repl, rendered)

    # Encodage : ZPL et EPL sont ASCII Ã©tendu (CP850), ESC-POS accepte UTF-8 sur
    # imprimantes modernes. On tolÃ¨re les caractÃ¨res non-reprÃ©sentables.
    if langage == "zpl":
        return rendered.encode("cp850", errors="replace")
    if langage == "epl":
        return rendered.encode("cp850", errors="replace")
    return rendered.encode("utf-8", errors="replace")


# â”€â”€ Templates par dÃ©faut livrÃ©s dans la migration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# Template ZPL 4"Ã—6" (102Ã—152mm) 203 dpi pour la rÃ©ception matiÃ¨re SIFA.
# Dimensions en points : 812 Ã— 1218 (203 dpi Ã— 4" Ã— 6")
# Placeholders utilisÃ©s :
#   {{lot_numero}}         â€” numÃ©ro de lot auto-gÃ©nÃ©rÃ©
#   {{fournisseur}}        â€” nom fournisseur
#   {{fsc_label}}          â€” libellÃ© statut FSC ("FSC 100%", "Non FSC", â€¦)
#   {{fsc_banner}}         â€” "MATIERE FSC" ou "MATIERE NON FSC"
#   {{ref_produit}}        â€” rÃ©fÃ©rence produit (optionnel)
#   {{code_barre}}         â€” code-barres bobine
#   {{operateur_nom}}      â€” nom de l'opÃ©rateur qui a validÃ©
#   {{date_reception}}     â€” date de rÃ©ception format "dd/mm/yyyy"
#
DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL = """^XA
^CI28
^PW1188
^LL1476
^LH96,96
^FO0,0^A0N,68,68^FDSIFA^FS
^FO660,0^GB336,108,108^FS
^FO690,30^A0N,48,48^FR^FD{{fsc_banner}}^FS
^FO0,140^A0N,60,60^FD{{lot_numero}}^FS
^BY4,3,240
^FO0,220^BCN,240,N,N,N^FD{{lot_numero}}^FS
^FO0,500^A0N,42,42^FDReference : {{ref_matiere}}^FS
^FO0,560^A0N,38,38^FDFournisseur : {{fournisseur}}^FS
^FO0,615^A0N,38,38^FDCertificat FSC : {{certificat_fsc}}^FS
^FO0,670^A0N,38,38^FDReception : {{date_reception}}^FS
^FO0,725^A0N,38,38^FDBobines : {{nb_bobines}} / {{nb_bobines_total}}^FS
^FO0,800^GB1000,3,3^FS
^FO0,820^A0N,42,42^FDCODES BOBINES^FS
^FO0,880^A0N,32,32^FD{{codes_bobines}}^FS
^XZ
"""

# Template COMPACT 107x50mm pour reimpression (203dpi = 8dpmm)
# 107mm x 8 = 856 dots, 50mm x 8 = 400 dots
DEFAULT_TEMPLATE_RECEPTION_COMPACT_ZPL = """^XA
^CI28
^PW1284
^LL600
^LH24,24
^FO0,0^A0N,68,68^FD{{lot_numero}}^FS
^FO0,82^GB180,44,44^FS
^FO8,90^A0N,32,32^FR^FD{{fsc_banner}}^FS
^FO200,88^A0N,32,32^FD{{date_reception}}^FS
^BY3,2.5,180
^FO0,145^BCN,180,N,N,N^FD{{lot_numero}}^FS
^FO0,345^A0N,32,32^FDMATIERE : {{ref_matiere}}^FS
^FO0,390^A0N,28,28^FD{{fournisseur}} — {{site}}^FS
^XZ
"""


# Templates prÃ©dÃ©finis complÃ©mentaires (galerie de dÃ©part pour l'admin).
# Format : liste de dicts {key, nom, description, langage, contenu}.
DEFAULT_TEMPLATE_GALLERY = [
    {
        "key": "bobine_full",
        "nom": "Ã‰tiquette bobine â€” complÃ¨te (FSC + code-barres + QR)",
        "description": "Format A6 (102Ã—152mm). Header SIFA, badge FSC inversÃ©, rÃ©fÃ©rence produit gros, fournisseur, lot trÃ¨s visible, code-barres CODE128, QR code + traÃ§abilitÃ©.",
        "langage": "zpl",
        "usage_key": "reception_matiere",
        "largeur_mm": 102,
        "hauteur_mm": 152,
        "contenu": DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL,
    },
    {
        "key": "bobine_compact",
        "nom": "Ã‰tiquette bobine â€” compacte (petit format 57Ã—32mm)",
        "description": "Format ticket (57Ã—32mm). Juste l'essentiel : lot + code-barres + FSC.",
        "langage": "zpl",
        "usage_key": "reception_matiere",
        "largeur_mm": 57,
        "hauteur_mm": 32,
        "contenu": """^XA
^CI28
^PW456
^LL256
^LH0,0
^FO10,10^A0N,22,22^FD{{fsc_banner}}^FS
^FO10,40^A0N,26,26^FD{{lot_numero}}^FS
^FO10,80^BY2,3,80^BCN,80,N,N,N^FD{{lot_numero}}^FS
^FO10,180^A0N,16,16^FD{{ref_produit}}^FS
^FO10,205^A0N,14,14^FD{{fournisseur}} - {{date_reception}}^FS
^XZ
""",
    },
    {
        "key": "emplacement_stock",
        "nom": "Ã‰tiquette emplacement stock (grand)",
        "description": "Format A5 (102Ã—74mm). Code emplacement en trÃ¨s gros + code-barres pour scan mobile.",
        "langage": "zpl",
        "usage_key": "reception_matiere",
        "largeur_mm": 102,
        "hauteur_mm": 74,
        "contenu": """^XA
^CI28
^PW812
^LL592
^LH0,0
^FO30,30^A0N,26,26^FDEMPLACEMENT^FS
^FO30,70^A0N,130,130^FD{{ref_produit}}^FS
^FO30,240^BY5,3,180^BCN,180,Y,N,N^FD{{ref_produit}}^FS
^FO30,530^A0N,20,20^FDSIFA - Loos^FS
^XZ
""",
    },
    {
        "key": "colis_expedition",
        "nom": "Ã‰tiquette colis expÃ©dition (100Ã—150mm)",
        "description": "Format standard colis. Client, adresse, numÃ©ro de commande, code-barres tracking.",
        "langage": "zpl",
        "usage_key": "reception_matiere",
        "largeur_mm": 100,
        "hauteur_mm": 150,
        "contenu": """^XA
^CI28
^PW800
^LL1200
^LH0,0
^FO30,30^A0N,32,32^FDEXPEDITION^FS
^FO30,80^GB740,3,3^FS
^FO30,110^A0N,22,22^FDDestinataire :^FS
^FO30,150^A0N,42,42^FD{{fournisseur}}^FS
^FO30,220^A0N,26,26^FD{{ref_produit}}^FS
^FO30,290^GB740,2,2^FS
^FO30,320^A0N,22,22^FDNumero de commande :^FS
^FO30,360^A0N,55,55^FD{{lot_numero}}^FS
^FO30,470^BY4,3,150^BCN,150,Y,N,N^FD{{code_barre}}^FS
^FO30,700^BQN,2,8^FDLA,{{code_barre}}^FS
^FO320,720^A0N,22,22^FDExpedie le :^FS
^FO320,750^A0N,32,32^FD{{date_reception}}^FS
^FO320,810^A0N,22,22^FDPar :^FS
^FO320,840^A0N,28,28^FD{{operateur_nom}}^FS
^FO30,1150^A0N,18,18^FDSIFA Loos - Support: contact@sifa.pro^FS
^XZ
""",
    },
]


def list_default_templates() -> list[dict]:
    """Renvoie la galerie de templates prÃ©dÃ©finis pour l'UI (sans le contenu ZPL
    complet dans la liste, juste key + nom + description + dimensions)."""
    return [
        {
            "key": t["key"],
            "nom": t["nom"],
            "description": t["description"],
            "langage": t["langage"],
            "usage_key": t["usage_key"],
            "largeur_mm": t["largeur_mm"],
            "hauteur_mm": t["hauteur_mm"],
        }
        for t in DEFAULT_TEMPLATE_GALLERY
    ]


def get_default_template(key: str) -> dict | None:
    """Renvoie le template prÃ©dÃ©fini complet (avec contenu) par sa clÃ©."""
    for t in DEFAULT_TEMPLATE_GALLERY:
        if t["key"] == key:
            return t
    return None


def default_templates_seed() -> list[dict]:
    """Liste des templates par dÃ©faut Ã  seeder Ã  la premiÃ¨re configuration
    d'une imprimante ZPL. Le seed est appliquÃ© depuis app/routers/print.py
    quand l'admin crÃ©e sa premiÃ¨re imprimante, pas en migration, car il faut
    connaÃ®tre l'imprimante_id."""
    return [
        {
            "usage_key": "reception_matiere",
            "nom": "Ã‰tiquette rÃ©ception matiÃ¨re (complÃ¨te)",
            "contenu": DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL,
        },
    ]


# â”€â”€ Registre des usages mÃ©tier â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Une clÃ© d'usage = un contexte mÃ©tier oÃ¹ on peut imprimer une Ã©tiquette.
# Les libellÃ©s sont utilisÃ©s dans l'UI (config imprimantes par dÃ©faut et
# Ã©diteur de template).
USAGES = [
    {
        "key": "reception_matiere",
        "label": "RÃ©ception matiÃ¨re â€” identification bobine",
        "module": "stock",
        "placeholders": [
            "lot_numero", "fournisseur", "fsc_label", "fsc_banner",
            "ref_produit", "code_barre", "operateur_nom", "date_reception",
            "{{barcode:code_barre}}", "{{barcode:lot_numero,CODE128,140}}",
            "{{qrcode:lot_numero}}", "{{now:%d/%m/%Y}}",
        ],
    },
    # v1.7 â€” usages "PDF passthrough" pour MyProd. Aucun template n'est
    # applique : c'est le PDF genere/importe qui sert de payload direct
    # (endpoint POST /api/print/pdf). Ces usages doivent etre associes a
    # une imprimante de langage="pdf" (imprimante bureautique via
    # SumatraPDF sur agent Windows).
    {
        "key": "of_document",
        "label": "Ordre de fabrication (PDF)",
        "module": "prod",
        "placeholders": [],
    },
    {
        "key": "fiche_technique",
        "label": "Fiche technique (PDF)",
        "module": "prod",
        "placeholders": [],
    },
    # Ã€ venir : etiquette_colis (MyExpÃ©), etiquette_emplacement (MyStock), etc.
]


def usage_label(key: str) -> str:
    for u in USAGES:
        if u["key"] == key:
            return u["label"]
    return key
