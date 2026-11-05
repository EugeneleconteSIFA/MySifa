"""MyQualité › Formulaires — assistant IA.

Deux usages, un seul appel (même principe que l'assistant des étiquettes
spécifiques, `etiq_specifiques_ia.py`) :
  - créer un formulaire depuis une consigne (« enquête satisfaction client,
    10 questions ») ou depuis un formulaire existant joint (photo, PDF scanné
    d'une fiche papier) ;
  - modifier le formulaire ouvert (« ajoute une section sécurité »).

Claude rend la structure via l'outil `proposer_formulaire`, que le serveur
repasse par `normaliser_schema()` : un champ inventé ou une liste trop longue
sont retirés comme pour une saisie manuelle. Rien n'est enregistré ici.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

from app.services import ia_usage
from app.services.qualite_formulaires import MAX_QUESTIONS, MAX_SECTIONS, normaliser_schema
from config import FORMULAIRES_IA_MODELE, formulaires_ia_modeles

_MAX_TOKENS = 16000


class FormulaireIaErreur(Exception):
    """Message affichable tel quel à l'utilisateur."""


_CONSIGNE = f"""Tu construis des formulaires dans MySifa, l'outil de gestion de SIFA, fabricant d'étiquettes adhésives. Les formulaires sont remplis par des fournisseurs, des clients ou le personnel : enquêtes de satisfaction, autoévaluations fournisseurs, contrôles qualité en production, audits internes, recueils d'information.

Un formulaire est une suite de sections ; chaque section a un `titre` (court), une `description` (facultative) et des `questions`. Chaque question a un `label` (la question telle que le destinataire la lit), un `type`, `required` (réponse obligatoire) et `help` (facultatif : précision ou méthode de mesure, une ou deux phrases).

Types :
- text : réponse libre. `long` = true pour un commentaire de plusieurs lignes ; `placeholder` = exemple de réponse.
- value : nombre. `unit` (g, mm, °C, %…), `min` et `max` (tolérance), `target_value` (valeur cible). `points` = libellés fixes quand il faut plusieurs mesures du même point (ex. ["Début de prod", "Milieu de prod", "Fin de prod"]) ; ou `points_libres` = true quand le nombre de mesures varie et que le destinataire ajoute lui-même ses lignes, avec `libelle_point` (ex. "Front"), `min_points` et `max_points` (1 à 50). `out_of_range_is_nc` = true si une valeur hors tolérance est une non-conformité (seulement avec min ou max).
- choice : `responses` (liste de réponses proposées, courtes), `multi` (plusieurs réponses possibles), `display` = "select" pour une longue liste à réponse unique, `allow_other` (ajoute « Autre » avec précision libre), `nc_responses` (sous-ensemble de `responses` qui signale une non-conformité, ex. ["Non conforme"]). Une question oui/non est un choice ["Oui", "Non"].
- date : une date.
- scale : note de `min` (0 ou 1) à `max` (2 à 10), avec `label_min` et `label_max` (ex. « Pas du tout satisfait », « Très satisfait »).

Règles :
- Une question = une seule chose demandée. Libellés courts, en français, vouvoiement pour un destinataire externe.
- N'invente ni seuil, ni tolérance, ni cible : ne les mets que s'ils figurent dans la consigne ou le document. Signale dans `remarques` ce qu'il faudra compléter.
- Au plus {MAX_SECTIONS} sections et {MAX_QUESTIONS} questions.
- Depuis un document joint (fiche papier, PDF, photo) : reproduis ses rubriques et ses questions dans l'ordre, avec le type de réponse le plus proche de ce que la fiche attend (case à cocher → choice, valeur mesurée → value, zone libre → text). Mentionne dans `remarques` ce qui était illisible.
- Pour modifier un formulaire existant : pars du formulaire fourni, garde les sections et questions que la consigne ne vise pas avec leur `id`, et ne change que ce qui est demandé. Les nouvelles questions n'ont pas d'`id`.

Appelle l'outil `proposer_formulaire` une seule fois, avec le formulaire complet. `resume` dit en une ou deux phrases ce que tu as fait ; `remarques` liste ce qu'il faut vérifier ou compléter. Aucun texte en dehors de l'outil."""


_QUESTION = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["text", "value", "choice", "date", "scale"]},
        "label": {"type": "string"},
        "required": {"type": "boolean"},
        "help": {"type": "string"},
        "long": {"type": "boolean"},
        "placeholder": {"type": "string"},
        "unit": {"type": "string"},
        "min": {"type": "number"},
        "max": {"type": "number"},
        "target_value": {"type": "number"},
        "points": {"type": "array", "items": {"type": "string"}},
        "points_libres": {"type": "boolean"},
        "libelle_point": {"type": "string"},
        "min_points": {"type": "integer"},
        "max_points": {"type": "integer"},
        "out_of_range_is_nc": {"type": "boolean"},
        "responses": {"type": "array", "items": {"type": "string"}},
        "multi": {"type": "boolean"},
        "display": {"type": "string", "enum": ["chips", "select"]},
        "allow_other": {"type": "boolean"},
        "nc_responses": {"type": "array", "items": {"type": "string"}},
        "label_min": {"type": "string"},
        "label_max": {"type": "string"},
    },
    "required": ["type", "label"],
}

_OUTIL = {
    "name": "proposer_formulaire",
    "description": "Rend le formulaire complet : titre, description, sections et questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "titre": {"type": "string"},
            "description": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "titre": {"type": "string"},
                        "description": {"type": "string"},
                        "questions": {"type": "array", "items": _QUESTION},
                    },
                    "required": ["titre", "questions"],
                },
            },
            "resume": {"type": "string"},
            "remarques": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["titre", "sections", "resume"],
    },
}

IMAGES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
PIECES_ACCEPTEES = IMAGES | {"application/pdf"}
PIECE_MAX_OCTETS = 15 * 1024 * 1024
PIECES_MAX = 5


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
            blocs.append({"type": "document", "source": {"type": "base64", "media_type": mime, "data": data}})
        elif mime in IMAGES:
            blocs.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}})
        else:
            continue
        blocs.append({"type": "text", "text": f"Document joint ci-dessus : {p.get('nom', '')}"})
    return blocs


def choisir_modele(modele: Optional[str]) -> dict:
    """Le modèle demandé s'il est dans la liste de config.py, sinon le défaut.
    Un identifiant inconnu est refusé plutôt que remplacé en silence."""
    liste = formulaires_ia_modeles()
    modeles = {m["id"]: m for m in liste}
    if not modele:
        return modeles.get(FORMULAIRES_IA_MODELE) or liste[0]
    if modele not in modeles:
        raise FormulaireIaErreur(f"Modèle « {modele} » non proposé — choisir dans la liste.")
    return modeles[modele]


def proposer(consigne: str, *, titre: str = "", description: str = "", schema: Optional[dict] = None,
             pieces: Optional[list[dict]] = None, modele: Optional[str] = None) -> dict:
    """Rend {"titre","description","schema","resume","remarques","modele",…}.

    `schema` vide (ou sans question) = création ; sinon modification du
    formulaire fourni. Lève FormulaireIaErreur avec un message affichable.
    """
    choix = choisir_modele(modele)
    client = _client()
    if client is None:
        raise FormulaireIaErreur("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")

    actuel = normaliser_schema(schema or {})
    a_des_questions = any(s["questions"] for s in actuel["sections"])
    texte = ""
    if a_des_questions:
        texte += "Formulaire actuel :\n" + json.dumps(
            {"titre": titre, "description": description, "sections": actuel["sections"]}, ensure_ascii=False) + "\n\n"
    elif titre and titre != "Formulaire sans titre":
        texte += f"Titre prévu : {titre}\n\n"
    texte += "Consigne :\n" + ((consigne or "").strip() or "Reproduis le formulaire du document joint.")
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
            # Le choix forcé d'un outil est refusé par les modèles récents :
            # la consigne demande l'outil, la réponse est contrôlée ci-dessous.
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": contenu}],
            **options,
        )
    except Exception as e:
        raise FormulaireIaErreur(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "formulaires")
    ia_usage.preciser(modele_demande=choix["id"], fichiers=len(pieces or []))

    if getattr(reponse, "stop_reason", "") == "refusal":
        raise FormulaireIaErreur("L'assistant a refusé cette demande. Reformuler la consigne.")
    if getattr(reponse, "stop_reason", "") == "max_tokens":
        raise FormulaireIaErreur("Réponse de l'assistant tronquée — formulaire trop long pour un seul passage. Le découper en plusieurs demandes.")

    entree = None
    for bloc in reponse.content:
        if getattr(bloc, "type", "") == "tool_use" and getattr(bloc, "name", "") == "proposer_formulaire":
            entree = bloc.input
            if isinstance(entree, str):
                try:
                    entree = json.loads(entree)
                except Exception:
                    entree = None
            break
    if not isinstance(entree, dict):
        raise FormulaireIaErreur("L'assistant n'a pas rendu de formulaire. Préciser la consigne et relancer.")

    nouveau = normaliser_schema({"sections": entree.get("sections") or []})
    if not any(s["questions"] for s in nouveau["sections"]):
        raise FormulaireIaErreur("L'assistant a rendu un formulaire vide. Préciser la consigne et relancer.")
    remarques = [str(r)[:300] for r in (entree.get("remarques") or []) if r][:10]
    return {
        "titre": str(entree.get("titre") or titre or "Formulaire sans titre").strip()[:200],
        "description": str(entree.get("description") or "").strip()[:2000],
        "schema": nouveau,
        "resume": str(entree.get("resume") or "")[:600],
        "remarques": remarques,
        "modele": choix["id"],
        "modele_libelle": choix.get("libelle", choix["id"]),
        # Le modèle qui a réellement répondu (différent si le repli a joué)
        "modele_reel": str(getattr(reponse, "model", "") or choix["id"]),
    }
