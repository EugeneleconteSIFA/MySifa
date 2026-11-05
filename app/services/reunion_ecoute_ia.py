"""
Réunions — mode écoute : proposition du brief par Claude.

Seul le TEXTE de la transcription part chez Anthropic, jamais l'audio
(décision du 2026-11-05). Même patron que app/services/pdf_ia.py, qui envoie
déjà des documents à Claude depuis l'Éditeur PDF : clé ANTHROPIC_API_KEY,
sortie structurée au schéma du brief, repli serveur sur refus, contrôle de
`stop_reason`, consommation notée par ia_usage (fonction « reunion »).

Le brief est une PROPOSITION : la transcription ne sait pas qui parle, les
responsables sont déduits des noms prononcés. Quelqu'un relit toujours avant
que rien ne soit écrit dans les réunions.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from app.services import ia_usage
from config import REUNION_IA_MODELE

_MAX_TOKENS = 8000


class ReunionIaErreur(Exception):
    """Message destiné à l'utilisateur."""


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "titre": {"type": "string"},
        "resume": {"type": "string"},
        "notes": {"type": "string"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "texte": {"type": "string"},
                    "responsable": {"type": "string"},
                    "echeance": {"type": "string"},
                },
                "required": ["texte", "responsable", "echeance"],
            },
        },
        "participants": {"type": "array", "items": {"type": "string"}},
        "points_ouverts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["titre", "resume", "notes", "decisions", "actions", "participants", "points_ouverts"],
}

_SYSTEME = (
    "Tu rédiges le compte-rendu d'une réunion interne d'une entreprise industrielle, à partir de sa "
    "transcription automatique. Tu écris en français, de façon factuelle et directe, sans formule de "
    "politesse ni emoji. La transcription est imparfaite : des mots peuvent être mal reconnus, et elle "
    "ne dit pas qui parle. Tu ne retiens que ce qui y est dit ; tu n'inventes ni chiffre, ni nom, ni "
    "décision. Quand un passage est incompréhensible, tu le laisses de côté plutôt que de le deviner.\n\n"
    "Le compte-rendu est lu en quelques secondes par des gens qui étaient dans la salle : il est COURT. "
    "Style télégraphique, sans phrase d'introduction ni de conclusion. Tu parles de la réunion, jamais "
    "de la transcription ni de l'enregistrement (pas de « la transcription indique », « il est dit que »). "
    "Une rubrique sans contenu reste vide : ne la remplis pas pour la remplir."
)


def _client():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    try:
        import anthropic
    except Exception:
        return None
    return anthropic.Anthropic(api_key=cle)


def consigne(contexte: Dict[str, Any]) -> str:
    """Le contexte donné avec la transcription : date, type, annuaire, termes."""
    lignes = [
        f"Date de la réunion : {contexte.get('date') or 'inconnue'}.",
        f"Type de réunion : {contexte.get('type') or 'non précisé'}.",
    ]
    if contexte.get("titre"):
        lignes.append(f"Titre donné : {contexte['titre']}.")
    personnes: List[str] = contexte.get("personnes") or []
    if personnes:
        lignes.append("Personnes de l'entreprise (pour écrire correctement un nom prononcé) : "
                      + ", ".join(personnes) + ".")
    termes: List[str] = contexte.get("termes") or []
    if termes:
        lignes.append("Termes de l'atelier : " + ", ".join(termes) + ".")
    if contexte.get("manquants"):
        lignes.append("Des passages de l'enregistrement n'ont pas été reçus : le signaler en une "
                      "ligne dans « points_ouverts ».")
    lignes += [
        "",
        "Rends :",
        "- titre : 3 à 6 mots, le sujet principal (sans la date) ;",
        "- resume : une phrase de 25 mots au plus ;",
        "- notes : les faits utiles, une ligne par point commençant par « - », 12 mots au plus par "
        "ligne, 6 lignes au plus. Chiffres, références et noms de machines gardés tels quels. "
        "Ce qui est déjà dans les décisions ou les actions n'y est pas répété ;",
        "- decisions : ce qui a été décidé, une entrée courte par décision (10 mots au plus) ;",
        "- actions : ce que quelqu'un doit faire. « responsable » = la personne nommée pour le faire, "
        "écrite comme dans la liste des personnes si elle y figure, vide si personne n'est nommé. "
        "« echeance » = date AAAA-MM-JJ si une échéance est dite (« vendredi prochain » se calcule "
        "depuis la date de la réunion), vide sinon ;",
        "- participants : les personnes qui parlent ou sont interpellées, seulement si leur nom est dit ;",
        "- points_ouverts : questions de la réunion restées sans réponse (3 au plus). Pas de remarque "
        "sur la qualité de l'enregistrement, sauf passages manquants signalés plus haut.",
        "",
        "Si la réunion n'a pas de contenu de fond (essai, échange très bref), le résumé le dit en une "
        "phrase et les autres rubriques restent vides.",
    ]
    return "\n".join(lignes)


def structurer(transcription: str, contexte: Dict[str, Any]) -> Dict[str, Any]:
    texte = (transcription or "").strip()
    if not texte:
        raise ReunionIaErreur("Transcription vide — rien à résumer.")
    client = _client()
    if client is None:
        raise ReunionIaErreur("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")
    try:
        reponse = client.messages.create(
            model=REUNION_IA_MODELE,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEME,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "<transcription>\n" + texte + "\n</transcription>"},
                {"type": "text", "text": consigne(contexte)},
            ]}],
            # Repli serveur sur refus (catégorie de refus → modèle recommandé).
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"output_config": {"effort": "medium",
                                          "format": {"type": "json_schema", "schema": SCHEMA}},
                        "fallbacks": "default"},
        )
    except Exception as e:
        raise ReunionIaErreur(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "reunion")
    ia_usage.preciser(modele_demande=REUNION_IA_MODELE)
    raison = getattr(reponse, "stop_reason", "")
    if raison == "refusal":
        raise ReunionIaErreur("L'assistant a refusé de résumer cette réunion.")
    if raison == "max_tokens":
        raise ReunionIaErreur("Brief tronqué — réunion trop longue pour un seul passage.")
    brut = "".join(getattr(b, "text", "") for b in reponse.content
                   if getattr(b, "type", "") == "text").strip()
    try:
        d = json.loads(brut)
    except ValueError:
        raise ReunionIaErreur("Réponse illisible de l'assistant — relancer.")
    return nettoyer(d)


def nettoyer(d: Any) -> Dict[str, Any]:
    """Rend un brief de forme sûre, quoi que contienne la réponse."""
    d = d if isinstance(d, dict) else {}

    def s(v: Any, n: int) -> str:
        return ("" if v is None else str(v)).strip()[:n]

    def liste(v: Any) -> List[str]:
        return [s(x, 500) for x in (v if isinstance(v, list) else []) if s(x, 500)][:60]

    actions = []
    for a in (d.get("actions") if isinstance(d.get("actions"), list) else [])[:60]:
        if isinstance(a, dict) and s(a.get("texte"), 500):
            ech = s(a.get("echeance"), 10)
            actions.append({"texte": s(a.get("texte"), 500), "responsable": s(a.get("responsable"), 120),
                            "echeance": ech if len(ech) == 10 and ech[4] == "-" else ""})
    return {
        "titre": s(d.get("titre"), 200),
        "resume": s(d.get("resume"), 2000),
        "notes": s(d.get("notes"), 20000),
        "decisions": liste(d.get("decisions")),
        "actions": actions,
        "participants": liste(d.get("participants")),
        "points_ouverts": liste(d.get("points_ouverts")),
    }
