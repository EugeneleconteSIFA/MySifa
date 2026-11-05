"""
Étiquettes spécifiques — contrôle avant impression par l'IA.

L'éditeur envoie l'étiquette telle qu'elle va sortir : mise en page, valeurs
de la première étiquette, rendu PNG de l'aperçu et alertes déjà levées par
les contrôles locaux (lisibilité des codes, texte qui dépasse, bords —
static/mysifa_etiq_moteur.js). Claude relit l'ensemble et signale ce qu'un
contrôle mécanique ne voit pas : mention obligatoire manquante pour l'usage
(SSCC sur une palette, licence FSC sous un logo FSC, lot et date sur un
produit daté), texte coupé ou illisible sur le rendu, contraste insuffisant,
incohérence entre texte en clair et code-barres.

Rien n'est modifié : la réponse est une liste de points à corriger.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Optional

from app.services import ia_usage
from app.services.etiq_specifiques import EtiquetteInvalide
from app.services.etiq_specifiques_ia import _client, choisir_modele

_MAX_TOKENS = 4000
PNG_MAX_OCTETS = 3 * 1024 * 1024

_CONSIGNE = """Tu contrôles une étiquette industrielle juste avant son impression sur une imprimante thermique, dans l'outil MySifa. Tu reçois le rendu de l'étiquette (image), sa mise en page JSON (millimètres, origine en haut à gauche), les valeurs de la première étiquette de la série, son usage (bobine, palette, carton, échantillon, expédition) et les alertes déjà levées par les contrôles automatiques.

Signale uniquement ce qui empêcherait l'étiquette de servir ou d'être conforme :
- mention obligatoire manquante pour l'usage : une étiquette palette logistique porte un SSCC (AI 00) en GS1-128 et son texte en clair ; un logo ou une mention FSC porte le numéro de licence ; un produit daté porte son lot et sa date ; une étiquette d'expédition porte le destinataire ;
- texte coupé, tronqué, qui déborde de son cadre ou de l'étiquette, ou trop petit pour être lu (moins de 1,5 mm de hauteur de caractère) ;
- code-barres illisible : trop petit, collé à un bord ou à un autre objet (zone de silence), tronqué, données incohérentes avec le texte en clair ;
- contraste insuffisant : texte blanc hors d'un aplat noir, objets superposés ;
- valeur manifestement fausse (variable vide, {{nom}} resté visible, date incohérente).

Ne répète pas une alerte automatique déjà fournie, sauf pour la préciser. Ne propose pas d'amélioration esthétique. Si tout est bon, rends verdict « ok » et aucun point.

Appelle l'outil `rendre_controle` une seule fois. Aucun texte en dehors de l'outil."""

_OUTIL = {
    "name": "rendre_controle",
    "description": "Rend le résultat du contrôle avant impression.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["ok", "a_corriger", "bloquant"]},
            "resume": {"type": "string"},
            "points": {"type": "array", "items": {"type": "object", "properties": {
                "gravite": {"type": "string", "enum": ["bloquant", "attention", "info"]},
                "element_id": {"type": "string"},
                "message": {"type": "string"},
            }, "required": ["gravite", "message"]}},
        },
        "required": ["verdict", "points"],
    },
}


def controler(largeur_mm: float, hauteur_mm: float, dpi: int, layout: dict, valeurs: dict,
              usage: str = "", alertes: Optional[list] = None, png_base64: str = "",
              modele: Optional[str] = None) -> dict:
    choix = choisir_modele(modele)
    client = _client()
    if client is None:
        raise EtiquetteInvalide("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")
    contenu = []
    if png_base64:
        brut = png_base64.split(",", 1)[-1]
        try:
            octets = base64.b64decode(brut, validate=True)
        except (binascii.Error, ValueError):
            raise EtiquetteInvalide("Rendu de l'étiquette illisible.")
        if len(octets) > PNG_MAX_OCTETS:
            raise EtiquetteInvalide("Rendu de l'étiquette trop lourd.")
        if octets[:8] == b"\x89PNG\r\n\x1a\n":
            contenu.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": brut}})
    etat = {"format_mm": [largeur_mm, hauteur_mm], "dpi": dpi, "usage": usage or "non précisé",
            "elements": layout.get("elements", []), "variables": layout.get("variables", []),
            "valeurs_premiere_etiquette": valeurs, "alertes_automatiques": (alertes or [])[:40]}
    contenu.append({"type": "text", "text": "Étiquette à contrôler :\n" + json.dumps(etat, ensure_ascii=False)})
    options = {"extra_body": {"output_config": {"effort": "low"}}}
    if choix.get("repli"):
        options["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
        options["extra_body"]["fallbacks"] = "default"
    try:
        reponse = client.messages.create(
            model=choix["id"], max_tokens=_MAX_TOKENS, system=_CONSIGNE, tools=[_OUTIL],
            tool_choice={"type": "auto"}, messages=[{"role": "user", "content": contenu}], **options)
    except Exception as e:
        raise EtiquetteInvalide(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "etiquettes")
    ia_usage.preciser(modele_demande=choix["id"], fichiers=1 if png_base64 else 0)
    entree = None
    for bloc in reponse.content:
        if getattr(bloc, "type", "") == "tool_use" and getattr(bloc, "name", "") == "rendre_controle":
            entree = bloc.input if isinstance(bloc.input, dict) else None
            break
    if not entree:
        raise EtiquetteInvalide("L'assistant n'a pas rendu de contrôle. Relancer.")
    ids = {e.get("id") for e in layout.get("elements", [])}
    points = []
    for p in (entree.get("points") or [])[:20]:
        if not isinstance(p, dict) or not p.get("message"):
            continue
        g = p.get("gravite") if p.get("gravite") in ("bloquant", "attention", "info") else "attention"
        points.append({"gravite": g, "message": str(p["message"])[:300],
                       "element_id": p.get("element_id") if p.get("element_id") in ids else None})
    verdict = entree.get("verdict") if entree.get("verdict") in ("ok", "a_corriger", "bloquant") else "a_corriger"
    if verdict == "ok" and any(p["gravite"] == "bloquant" for p in points):
        verdict = "bloquant"
    return {"verdict": verdict, "resume": str(entree.get("resume") or "")[:500], "points": points,
            "modele": choix["id"], "modele_libelle": choix.get("libelle", choix["id"])}
