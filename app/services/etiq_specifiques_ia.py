"""
MyPrint — étiquettes spécifiques : assistant IA.

Deux usages, un seul appel :
  - modifier une étiquette existante à partir d'une consigne en français
    (« ajoute le SSCC en GS1-128 sous la référence ») ;
  - construire un premier jet depuis une demande de nouveau format, pièces
    jointes comprises (photo ou PDF d'une étiquette existante, cahier des
    charges client) ;
  - créer une étiquette directement depuis une photo et une explication
    (`format_libre=True` quand l'utilisateur ne donne pas le format : Claude
    le déduit de la photo parmi les formats standard de config.py).

Claude ne produit jamais de ZPL : il rend la même mise en page JSON que
l'éditeur manuel, qui repasse par `normaliser_layout()`. Rien n'est
enregistré ici : la proposition revient à l'écran, l'utilisateur la regarde
et l'applique ou non.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

from app.services import ia_usage
from config import ETIQ_FORMATS_STANDARD, ETIQ_IA_MODELE, etiq_ia_modeles
from app.services.etiq_specifiques import (
    EtiquetteInvalide, SYMBOLOGIES, TYPES_VARIABLE, normaliser_format, normaliser_layout,
)

_MAX_TOKENS = 16000

_CONSIGNE = """Tu paramètres des étiquettes industrielles pour imprimantes thermiques (ZPL), dans l'outil MySifa. Tu ne produis jamais de ZPL : tu rends une mise en page structurée via l'outil `proposer_etiquette`, qui sera convertie en ZPL par le logiciel.

Repère : millimètres, origine en haut à gauche, x vers la droite, y vers le bas. Tout élément doit tenir dans le format (largeur × hauteur). Garde 2 à 3 mm de marge sur les bords.

Éléments (`elements`) — chacun a un `id` court unique (e1, e2…), un `nom` lisible, `x`, `y` :
- texte : `valeur` (texte, peut contenir des {{variables}}), `taille` = hauteur des caractères en mm (2 à 4 pour du courant, 6 à 15 pour un titre), `gras`, `largeur` en mm (0 = pas de bloc ; sinon bloc de texte avec retour à la ligne), `lignes` (nombre max de lignes du bloc), `align` (gauche|centre|droite, n'agit que si largeur > 0), `rotation` (0, 90, 180, 270), `inverse` (texte blanc sur fond noir, à poser sur un cadre plein).
- code_barre : `symbologie` (code128, gs1_128, ean13, datamatrix, qrcode), `valeur`, `hauteur` en mm (codes linéaires), `module` = largeur du plus petit barreau en mm (0,25 à 0,5 pour les linéaires ; 0,5 à 1 pour datamatrix/QR), `lisible` (texte en clair sous le code), `rotation`. Largeur approximative d'un Code 128 : (11 × nb_caractères + 35) × module mm — vérifie qu'il tient.
- cadre : `largeur`, `hauteur`, `epaisseur` en mm, `arrondi` (0 à 8), `plein` (rectangle noir).
- ligne : `orientation` (h|v), `longueur`, `epaisseur` en mm.
- picto : pictogramme réglementaire `picto` (recyclage, fsc, deroulage, fragile, haut, humidite), `largeur`, `hauteur` en mm, `legende` (texte sous le dessin ; pour fsc, mets {{fsc_licence}}).
Symbologies supplémentaires : gs1_datamatrix (données GS1 avec AI entre parenthèses), pdf417. code128 choisit seul le jeu de caractères.

Champs communs à tous les éléments : `calque` (« fond » pour ce qui est identique sur toutes les étiquettes : logo, intitulés, mentions légales, filets ; « donnees » pour ce qui change), `verrou` (vrai pour un logo ou une mention imposée que l'opérateur ne doit pas toucher), `condition` (expression : l'objet ne s'imprime que si elle est vraie, ex. NON(VIDE(lot))), `masquer_si_vide` (vrai : l'objet disparaît quand sa valeur est vide — utile pour une ligne facultative).

Variables (`variables`) — `nom` en minuscules (a-z, 0-9, _), `libelle` lisible, `type` :
- fixe : `valeur`
- saisie : demandée à l'opérateur à chaque impression, `valeur` = valeur par défaut, `obligatoire`
- compteur : numéro qui avance à chaque étiquette — `debut`, `pas`, `longueur` (zéros de tête), `prefixe`, `suffixe`
- sscc : SSCC GS1 de 18 chiffres calculé (extension + préfixe GS1 + série + clé) — `extension` (1 chiffre), `prefixe_gs1` (7 à 10 chiffres). Si le préfixe n'est pas connu, laisse-le vide et signale-le dans `remarques`.
- date : date calculée — `base` (« impression » ou le nom d'une autre variable, ex. date de fabrication saisie), `decalage_jours`, `decalage_mois` (DLUO, DDM), `format` (%d/%m/%Y, %y%m%d pour GS1, S%V-%G semaine ISO, %y%j lot daté AAJJJ)
- source : donnée lue dans MySifa à l'impression — `champ` parmi la liste fournie (ex. dossier.reference, produit.designation, client.raison_sociale, lot.lot_fournisseur), `valeur` = valeur lue sur la photo (aperçu). Préfère une source à une saisie quand la donnée existe dans MySifa : référence dossier, OF, désignation produit, client, lot matière.
- formule : `expression` sur les autres variables, sans {{}} : concaténation avec &, MAJUSCULE(t), GAUCHE(t;n), SI(cond;a;b), ARRONDI(x;n), TEXTE(x;n), ZEROS(x;n), NUM(t), VIDE(t), CLE_GS1(t)… Ex. MAJUSCULE(client) & " - " & lot.
Une variable s'utilise dans la `valeur` d'un élément avec {{nom}}. {{fsc_licence}} et {{gs1_prefixe}} sont fournis par MySifa sans déclaration.

Règles GS1 : en GS1-128, chaque identifiant d'application s'écrit entre parenthèses, suivi de sa donnée, sans espace — par exemple (00){{sscc}} ou (02){{gtin}}(37){{quantite}}. Le SSCC s'imprime sous l'AI (00). Si la consigne demande un SSCC « sous le code-barre produit », place le GS1-128 SSCC sous le code existant, aligné à gauche sur lui.

Quand tu modifies une étiquette existante : pars de la mise en page fournie, garde les éléments et leurs id que la consigne ne vise pas, et ne déplace que ce qui doit l'être.

Quand tu crées depuis une photo ou un PDF d'étiquette :
- Reproduis fidèlement la disposition visible : mêmes zones, même ordre, mêmes alignements, mêmes cadres et filets, mêmes tailles relatives de texte. Ne réinvente pas la mise en page et n'ajoute rien qui n'y figure pas, sauf si l'explication le demande.
- Mesure les proportions : situe chaque élément en fraction de la largeur et de la hauteur de l'étiquette sur l'image, puis convertis en mm dans le format retenu. Corrige la perspective et la rotation de la prise de vue : raisonne sur l'étiquette à plat, pas sur le cadre de la photo.
- Format : s'il est imposé, garde-le. S'il est « à déduire », pars du rapport largeur / hauteur de l'étiquette sur la photo et d'un repère de taille connue (un EAN-13 en module 0,33 mm fait environ 37 mm de large, un SSCC en GS1-128 module 0,5 environ 80 mm), puis retiens le format standard le plus proche de la liste fournie ; indique dans `remarques` le format retenu et sur quoi tu t'es fondé.
- Codes-barres : identifie la symbologie (EAN-13, GS1-128 avec ses AI entre parenthèses, Code 128, DataMatrix, QR) et reprends sa taille et sa position.
- Données variables : tout ce qui change d'une étiquette à l'autre (référence, lot, date, quantité, poids, numéro de colis, SSCC, adresse de livraison…) devient une variable, du type qui convient (source si la donnée est dans MySifa, sinon saisie, compteur, sscc, date, formule). Ce qui est identique sur toutes les étiquettes (logo texte, intitulés de champs, nom du fournisseur) reste du texte fixe, sur le calque « fond ». L'explication de l'utilisateur fait foi sur ce point. Liste chaque champ variable détecté dans `champs_detectes` (nom de la variable, ce que tu as lu sur l'original, pourquoi ce type).
- Pictogrammes : un pictogramme de manutention ou de recyclage visible devient un élément picto de même emprise.
- Valeurs par défaut : reprends les valeurs lues sur la photo comme `valeur` par défaut des variables de saisie, pour que l'aperçu ressemble à l'original.
- Un logo ou une image ne se reproduit pas : remplace-le par un cadre de même emprise nommé « Logo … » et signale-le dans `remarques`.
- Signale dans `remarques` tout ce qui est illisible, coupé ou incertain sur la photo, plutôt que de l'inventer.

Appelle l'outil `proposer_etiquette` une seule fois, avec la mise en page complète. `resume` dit en une ou deux phrases ce que tu as fait ; `remarques` liste ce qu'il faut vérifier ou compléter (préfixe GS1 manquant, donnée illisible sur la photo…). Aucun texte en dehors de l'outil."""


_ELEMENT = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["texte", "code_barre", "cadre", "ligne", "picto"]},
        "nom": {"type": "string"},
        "x": {"type": "number"},
        "y": {"type": "number"},
        "valeur": {"type": "string"},
        "taille": {"type": "number"},
        "gras": {"type": "boolean"},
        "largeur": {"type": "number"},
        "hauteur": {"type": "number"},
        "lignes": {"type": "integer"},
        "align": {"type": "string", "enum": ["gauche", "centre", "droite"]},
        "rotation": {"type": "integer", "enum": [0, 90, 180, 270]},
        "inverse": {"type": "boolean"},
        "symbologie": {"type": "string", "enum": list(SYMBOLOGIES)},
        "module": {"type": "number"},
        "lisible": {"type": "boolean"},
        "epaisseur": {"type": "number"},
        "arrondi": {"type": "integer"},
        "plein": {"type": "boolean"},
        "orientation": {"type": "string", "enum": ["h", "v"]},
        "longueur": {"type": "number"},
        "picto": {"type": "string", "enum": ["recyclage", "fsc", "deroulage", "fragile", "haut", "humidite"]},
        "legende": {"type": "string"},
        "calque": {"type": "string", "enum": ["fond", "donnees"]},
        "verrou": {"type": "boolean"},
        "condition": {"type": "string"},
        "masquer_si_vide": {"type": "boolean"},
    },
    "required": ["id", "type", "x", "y"],
}

_VARIABLE = {
    "type": "object",
    "properties": {
        "nom": {"type": "string"},
        "libelle": {"type": "string"},
        "type": {"type": "string", "enum": list(TYPES_VARIABLE)},
        "valeur": {"type": "string"},
        "obligatoire": {"type": "boolean"},
        "debut": {"type": "integer"},
        "pas": {"type": "integer"},
        "longueur": {"type": "integer"},
        "prefixe": {"type": "string"},
        "suffixe": {"type": "string"},
        "extension": {"type": "string"},
        "prefixe_gs1": {"type": "string"},
        "format": {"type": "string"},
        "decalage_jours": {"type": "integer"},
        "decalage_mois": {"type": "integer"},
        "base": {"type": "string"},
        "champ": {"type": "string"},
        "expression": {"type": "string"},
        "reprise": {"type": "boolean"},
    },
    "required": ["nom", "libelle", "type"],
}

_OUTIL = {
    "name": "proposer_etiquette",
    "description": "Rend la mise en page complète de l'étiquette (format, éléments, variables).",
    "input_schema": {
        "type": "object",
        "properties": {
            "largeur_mm": {"type": "number"},
            "hauteur_mm": {"type": "number"},
            "elements": {"type": "array", "items": _ELEMENT},
            "variables": {"type": "array", "items": _VARIABLE},
            "resume": {"type": "string"},
            "remarques": {"type": "array", "items": {"type": "string"}},
            "champs_detectes": {"type": "array", "items": {"type": "object", "properties": {
                "variable": {"type": "string"}, "lu": {"type": "string"}, "raison": {"type": "string"}},
                "required": ["variable"]}},
        },
        "required": ["largeur_mm", "hauteur_mm", "elements", "variables", "resume"],
    },
}

_IMAGES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def _client():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    try:
        import anthropic
    except Exception:
        return None
    return anthropic.Anthropic(api_key=cle)


def _blocs_pieces(pieces: list[dict]) -> list[dict]:
    """pieces : [{"mime", "contenu" (bytes), "nom"}] — images et PDF seulement."""
    blocs = []
    for p in pieces or []:
        mime = (p.get("mime") or "").lower()
        data = base64.standard_b64encode(p["contenu"]).decode()
        if mime == "application/pdf":
            blocs.append({"type": "document",
                          "source": {"type": "base64", "media_type": mime, "data": data}})
        elif mime in _IMAGES:
            blocs.append({"type": "image",
                          "source": {"type": "base64", "media_type": mime, "data": data}})
        else:
            continue
        blocs.append({"type": "text", "text": f"Pièce jointe ci-dessus : {p.get('nom', '')}"})
    return blocs


def choisir_modele(modele: Optional[str]) -> dict:
    """Le modèle demandé s'il est dans la liste de config.py, sinon le défaut.
    Un identifiant inconnu est refusé plutôt que remplacé en silence."""
    liste = etiq_ia_modeles()
    modeles = {m["id"]: m for m in liste}
    if not modele:
        # Un défaut (.env) qui n'est plus dans la liste retombe sur le premier
        # modèle proposé, plutôt que d'appeler un modèle retiré.
        return modeles.get(ETIQ_IA_MODELE) or liste[0]
    if modele not in modeles:
        raise EtiquetteInvalide(f"Modèle « {modele} » non proposé — choisir dans la liste.")
    return modeles[modele]


def contexte_photo(largeur_mm: Optional[float], hauteur_mm: Optional[float]) -> str:
    """Ce que l'assistant doit savoir du format pour une création depuis photo."""
    if largeur_mm and hauteur_mm:
        return (f"Création depuis une photo. Format imposé par l'utilisateur : "
                f"{largeur_mm:g} × {hauteur_mm:g} mm (largeur × hauteur) — garde-le.")
    formats = ", ".join(f"{l}×{h}" for l, h in ETIQ_FORMATS_STANDARD)
    return ("Création depuis une photo. Format à déduire de la photo (largeur × hauteur en mm). "
            f"Formats standard du site : {formats}. Une étiquette nettement hors de ces formats "
            "garde ses dimensions mesurées, arrondies au mm.")


def proposer(consigne: str, largeur_mm: float, hauteur_mm: float, dpi: int,
             layout: dict, pieces: Optional[list[dict]] = None, contexte: str = "",
             modele: Optional[str] = None, format_libre: bool = False) -> dict:
    """Rend {"largeur_mm","hauteur_mm","layout","resume","remarques","modele"}.

    `format_libre` : le format n'est pas connu, l'état envoyé le dit « à
    déduire » au lieu de proposer largeur_mm / hauteur_mm (qui restent le
    repli si la réponse n'en donne pas).

    Lève EtiquetteInvalide avec un message affichable si l'appel échoue.
    """
    choix = choisir_modele(modele)
    client = _client()
    if client is None:
        raise EtiquetteInvalide("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")

    etat = {
        "largeur_mm": "à déduire" if format_libre else largeur_mm,
        "hauteur_mm": "à déduire" if format_libre else hauteur_mm,
        "dpi": dpi,
        "elements": layout.get("elements", []), "variables": layout.get("variables", []),
    }
    texte = ""
    if contexte:
        texte += contexte.strip() + "\n\n"
    from app.services.etiq_sources import CHAMPS
    texte += ("Champs MySifa disponibles pour les variables de type source : "
              + ", ".join(f"{t}.{c}" for t, lst in CHAMPS.items() for c, _l, _ in lst) + "\n\n")
    texte += "Étiquette actuelle :\n" + json.dumps(etat, ensure_ascii=False) + "\n\n"
    texte += "Consigne :\n" + (consigne or "").strip()
    contenu = _blocs_pieces(pieces or []) + [{"type": "text", "text": texte}]

    options = {"extra_body": {"output_config": {"effort": "medium"}}}
    if choix.get("repli"):
        options["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
        options["extra_body"]["fallbacks"] = "default"
    try:
        reponse = client.messages.create(
            model=choix["id"],
            max_tokens=_MAX_TOKENS,
            system=_CONSIGNE,
            tools=[_OUTIL],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": contenu}],
            **options,
        )
    except Exception as e:
        raise EtiquetteInvalide(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "etiquettes")
    ia_usage.preciser(modele_demande=choix["id"], fichiers=len(pieces or []))

    if getattr(reponse, "stop_reason", "") == "refusal":
        raise EtiquetteInvalide("L'assistant a refusé cette demande. Reformuler la consigne.")
    if getattr(reponse, "stop_reason", "") == "max_tokens":
        raise EtiquetteInvalide("Réponse de l'assistant tronquée — étiquette trop complexe pour un seul passage.")

    entree = None
    for bloc in reponse.content:
        if getattr(bloc, "type", "") == "tool_use" and getattr(bloc, "name", "") == "proposer_etiquette":
            entree = bloc.input
            if isinstance(entree, str):
                try:
                    entree = json.loads(entree)
                except Exception:
                    entree = None
            break
    if not isinstance(entree, dict):
        raise EtiquetteInvalide("L'assistant n'a pas rendu de mise en page. Préciser la consigne et relancer.")

    l, h, _ = normaliser_format(entree.get("largeur_mm", largeur_mm), entree.get("hauteur_mm", hauteur_mm), dpi)
    nouveau = normaliser_layout({"elements": entree.get("elements"), "variables": entree.get("variables")})
    remarques = [str(r)[:300] for r in (entree.get("remarques") or []) if r][:10]
    noms = {v["nom"]: v for v in nouveau["variables"]}
    champs = []
    for c in (entree.get("champs_detectes") or [])[:40]:
        if isinstance(c, dict) and str(c.get("variable") or "").lower() in noms:
            v = noms[str(c["variable"]).lower()]
            champs.append({"variable": v["nom"], "libelle": v["libelle"], "type": v["type"],
                           "champ": v.get("champ", ""), "lu": str(c.get("lu") or "")[:120],
                           "raison": str(c.get("raison") or "")[:200]})
    return {
        "largeur_mm": l, "hauteur_mm": h, "layout": nouveau,
        "resume": str(entree.get("resume") or "")[:600],
        "remarques": remarques,
        "champs_detectes": champs,
        "modele": choix["id"],
        "modele_libelle": choix.get("libelle", choix["id"]),
        # Le modèle qui a réellement répondu (différent si le repli a joué)
        "modele_reel": str(getattr(reponse, "model", "") or choix["id"]),
    }
