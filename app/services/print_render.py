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


# v1.7 — ajout de "pdf" pour l'impression de documents bureautiques (OF, fiches
# techniques) vers des imprimantes A4/A3 laser/jet. Le langage "pdf" est un
# passthrough : les bytes du PDF sont stockes tels quels dans print_jobs.payload
# et transmis a l'agent, qui les envoie a SumatraPDF pour impression sur la
# queue Windows cible (avec params copies/duplex/format/bac/N&B via data_json).
LANGAGES = ("zpl", "epl", "escpos", "pdf")

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
    # v1.7 — le langage "pdf" ne rend pas de template : les bytes du PDF sont
    # fournis directement par l'endpoint POST /api/print/pdf. render_template
    # n'est jamais appele pour un job PDF (l'endpoint stocke directement le
    # blob dans print_jobs.payload). Si on arrive ici avec langage=pdf, c'est
    # que quelqu'un a mal cable l'appel — on remonte une erreur explicite.
    if langage == "pdf":
        raise ValueError(
            "Le langage 'pdf' ne s'utilise pas via render_template. "
            "Utilise l'endpoint POST /api/print/pdf pour soumettre un job PDF."
        )
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
^PW1188
^LL1476
^LH24,24
^PR2
~SD22
^FO0,20^FB1140,1,0,C,0^A0N,90,90^FDSIFA^FS
^FO0,140^GB1140,130,130^FS
^FO0,168^FB1140,1,0,C,0^A0N,72,72^FR^FD{{fsc_banner}}^FS
^FO0,320^FB1140,1,0,C,0^A0N,70,70^FD{{lot_numero}}^FS
^BY5,3,320
^FO60,420^BCN,320,N,N,N^FD{{lot_numero}}^FS
^FO0,790^FB1140,1,0,C,0^A0N,44,44^FDReference : {{ref_matiere}}^FS
^FO0,855^FB1140,1,0,C,0^A0N,40,40^FD{{fournisseur}}^FS
^FO0,915^FB1140,1,0,C,0^A0N,40,40^FDFSC : {{certificat_fsc}}^FS
^FO0,975^FB1140,1,0,C,0^A0N,40,40^FDReception : {{date_reception}}^FS
^FO0,1035^FB1140,1,0,C,0^A0N,40,40^FDBobines : {{nb_bobines}}/{{nb_bobines_total}}^FS
^FO70,1120^GB1000,3,3^FS
^FO0,1150^FB1140,1,0,C,0^A0N,50,50^FDCODES BOBINES^FS
^FO60,1230^FB1068,5,4,C,0^A0N,32,32^FD{{codes_bobines}}^FS
^XZ
"""

# Template COMPACT 107x50mm pour reimpression (203dpi = 8dpmm)
# 107mm x 8 = 856 dots, 50mm x 8 = 400 dots
DEFAULT_TEMPLATE_RECEPTION_COMPACT_ZPL = """^XA
^CI28
^PW1284
^LL600
^LH20,16
^PR2
~SD22
^FO0,0^GB1244,72,72^FS
^FO0,14^FB1244,1,0,C,0^A0N,44,44^FR^FDMATIERE {{fsc_banner}}^FS
^FO0,100^A0N,22,22^FDReference^FS
^FO0,132^A0N,32,32^FD{{ref_produit}}^FS
^FO440,100^A0N,22,22^FDLaize^FS
^FO440,132^A0N,32,32^FD{{laize}}^FS
^FO0,190^A0N,22,22^FDFournisseur^FS
^FO0,222^A0N,28,28^FD{{fournisseur}}^FS
^FO0,275^A0N,22,22^FDReception^FS
^FO0,307^A0N,26,26^FD{{date_reception}}^FS
^FO440,275^A0N,22,22^FDOperateur^FS
^FO440,307^A0N,26,26^FD{{operateur_nom}}^FS
^FO900,100^BQN,2,7^FDLA,{{lot_numero}}^FS
^FO0,470^GB1244,3,3^FS
^FO0,490^FB1244,1,0,C,0^A0N,28,28^FDNUMERO LOT^FS
^FO0,528^FB1244,1,0,C,0^A0N,44,44^FD{{lot_numero}}^FS
^XZ
"""


# Templates prédéfinis complémentaires (galerie de départ pour l'admin).
# Format : liste de dicts {key, nom, description, langage, contenu}.
# ── Avertissement FSC à agrafer au dossier physique de production ──────
#
# Format 100 × 50 mm, soit 800 × 400 points à 203 dpi (8 pts/mm — même
# résolution que les gabarits bobine ci-dessus : 57 mm → ^PW456).
#
# Strictement monochrome. Sur une thermique, la couleur n'existe pas : la
# hiérarchie visuelle passe par l'épaisseur du trait, le pavé plein inversé
# (^GB rempli + ^FR) et la taille de police. Rien d'autre ne se voit.
#
# Le contenu est une CONSIGNE, pas une identification : l'opérateur qui prend
# le dossier physique en main doit savoir ce qu'on attend de lui avant d'aller
# chercher sa bobine. C'est le pendant papier du bandeau de la saisie de
# production — et le seul support disponible quand l'écran est mobilisé par
# une autre machine.
#
# Texte sans accents, comme les gabarits existants : les polices bitmap A0
# des thermiques d'entrée de gamme les rendent mal même en ^CI28.
# Hiérarchie assumée : ce que l'opérateur doit FAIRE est plus gros que ce qui
# identifie le dossier. Le n° d'OF et le client servent à retrouver la bonne
# pochette — une fois l'étiquette en main, ils n'apprennent plus rien. Les
# trois consignes, elles, sont relues à chaque changement de bobine.
#
# ^FB (field block) fait le retour à la ligne automatique : les consignes sont
# trop longues pour tenir sur une ligne à cette taille, et un ^FD nu serait
# tronqué au bord droit sans le moindre avertissement. Les hauteurs réservées
# (2 / 3 / 2 lignes) sont calculées pour le pire cas.
#
# Le code-barres a sauté : il servait à rescanner le dossier, ce que personne
# ne fait depuis une étiquette collée sur une pochette. La place gagnée va aux
# consignes, qui elles sont lues.
DEFAULT_TEMPLATE_FSC_AVERTISSEMENT_ZPL = """^XA
^CI28
^PW800
^LL400
^LH0,0
^FO4,4^GB792,392,4^FS
^FO14,8^GB772,48,48^FS
^FO26,14^FR^A0N,36,36^FDDOSSIER FSC^FS
^FO560,22^FR^A0N,18,18^FD{{fsc_type_requis}}^FS
^FO26,62^A0N,24,24^FD{{no_dossier}}^FS
^FO26,90^A0N,18,18^FD{{client}}^FS
^FO14,112^GB772,2,2^FS
^FO26,120^FB748,2,2,L,0^A0N,28,28^FD1. Utiliser de la matiere avec la mention "Matiere FSC" uniquement.^FS
^FO26,182^FB748,3,2,L,0^A0N,28,28^FD2. Pour chaque bobine utilisee (glassines et frontaux) ajouter les numeros de bobine IMPERATIVEMENT dans l'outil de traca^FS
^FO26,274^FB748,2,2,L,0^A0N,28,28^FD3. Effectuer les entrees de produits finis en Z1 avec l'outil stock.^FS
^FO14,338^GB772,2,2^FS
^FO26,348^A0N,20,20^FD{{ref_produit}}  {{machine}}^FS
^FO420,348^A0N,20,20^FD{{now:%d/%m/%Y}}^FS
^FO670,344^A0N,28,28^FDMerci^FS
^XZ
"""

DEFAULT_TEMPLATE_GALLERY = [
    {
        "key": "fsc_avertissement_dossier",
        "variante": "full",
        "nom": "Avertissement FSC — dossier de production (100×50mm, N&B)",
        "description": (
            "Format 100×50mm, strictement noir et blanc. Consigne à coller sur le "
            "dossier physique : matière certifiée obligatoire, scan de chaque bobine, "
            "entrée en Z1. Bandeau inversé, code-barres du n° de dossier."
        ),
        "langage": "zpl",
        "usage_key": "fsc_avertissement_dossier",
        "largeur_mm": 100,
        "hauteur_mm": 50,
        "contenu": DEFAULT_TEMPLATE_FSC_AVERTISSEMENT_ZPL,
    },
    {
        "key": "bobine_full",
        "variante": "full",
        "nom": "Étiquette bobine — complète (FSC + code-barres + QR)",
        "description": "Format A6 (102×152mm). Header SIFA, badge FSC inversé, référence produit gros, fournisseur, lot très visible, code-barres CODE128, QR code + traçabilité.",
        "langage": "zpl",
        "usage_key": "reception_matiere",
        "largeur_mm": 102,
        "hauteur_mm": 152,
        "contenu": DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL,
    },
    {
        "key": "bobine_compact",
        "variante": "compact",
        "nom": "Étiquette bobine — compacte (petit format 57×32mm)",
        "description": "Format ticket (57×32mm). Juste l'essentiel : lot + code-barres + FSC.",
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
        "variante": "full",
        "nom": "Étiquette emplacement stock (grand)",
        "description": "Format A5 (102×74mm). Code emplacement en très gros + code-barres pour scan mobile.",
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
        "variante": "full",
        "nom": "Étiquette colis expédition (100×150mm)",
        "description": "Format standard colis. Client, adresse, numéro de commande, code-barres tracking.",
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
    """Renvoie la galerie de templates prédéfinis pour l'UI (sans le contenu ZPL
    complet dans la liste, juste key + nom + description + dimensions)."""
    return [
        {
            "key": t["key"],
            "nom": t["nom"],
            "description": t["description"],
            "langage": t["langage"],
            "usage_key": t["usage_key"],
            "variante": t.get("variante", "full"),
            "largeur_mm": t["largeur_mm"],
            "hauteur_mm": t["hauteur_mm"],
        }
        for t in DEFAULT_TEMPLATE_GALLERY
    ]


def get_default_template(key: str) -> dict | None:
    """Renvoie le template prédéfini complet (avec contenu) par sa clé."""
    for t in DEFAULT_TEMPLATE_GALLERY:
        if t["key"] == key:
            return t
    return None


# ── Variantes de template ──────────────────────────────────────────────
# Un même usage métier peut avoir deux gabarits distincts sur une imprimante :
#   - "full"    : première impression (bouton « Faire une réception »)
#   - "compact" : réimpression depuis l'historique (bouton « Réimprimer »)
# Le front envoie la variante dans le payload de POST /api/print/label ;
# le serveur résout TOUJOURS le contenu depuis imprimante_templates. Aucun
# ZPL n'est plus figé dans le code sur le chemin d'impression (v2.6.0) :
# les constantes ci-dessus ne servent qu'au seed initial et à la galerie.
VARIANTES = ("full", "compact")

VARIANTE_LABELS = {
    "full": "Impression",
    "compact": "Réimpression",
}


def variante_label(key: str) -> str:
    return VARIANTE_LABELS.get(key, key)


def default_templates_seed() -> list[dict]:
    """Liste des templates par défaut à seeder à la première configuration
    d'une imprimante ZPL. Le seed est appliqué depuis app/routers/print.py
    quand l'admin crée sa première imprimante, pas en migration, car il faut
    connaître l'imprimante_id.

    Une entrée par variante : sans le gabarit `compact`, le bouton
    « Réimprimer étiquettes » renverrait un 409 dès la première utilisation.
    """
    return [
        {
            "usage_key": "reception_matiere",
            "variante": "full",
            "nom": "Étiquette réception matière (complète)",
            "contenu": DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL,
        },
        {
            "usage_key": "reception_matiere",
            "variante": "compact",
            "nom": "Étiquette réception matière (réimpression)",
            "contenu": DEFAULT_TEMPLATE_RECEPTION_COMPACT_ZPL,
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
            "ref_produit", "laize", "code_barre", "operateur_nom", "date_reception",
            "{{barcode:code_barre}}", "{{barcode:lot_numero,CODE128,140}}",
            "{{qrcode:lot_numero}}", "{{now:%d/%m/%Y}}",
        ],
    },
    # v1.7 — usages "PDF passthrough" pour MyProd. Aucun template n'est
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
    {
        "key": "fsc_avertissement_dossier",
        "label": "Avertissement FSC — dossier de production",
        "module": "prod",
        "placeholders": [
            "no_dossier", "numero_of", "client", "ref_produit", "machine",
            "fsc_type_requis", "operateur_nom",
            "{{barcode:no_dossier}}", "{{qrcode:no_dossier}}",
            "{{now:%d/%m/%Y %H:%M}}",
        ],
    },
    # À venir : etiquette_colis (MyExpé), etiquette_emplacement (MyStock), etc.
]


def usage_label(key: str) -> str:
    for u in USAGES:
        if u["key"] == key:
            return u["label"]
    return key
