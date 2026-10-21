"""Maintenance › alertes — assistant IA.

Crée ou modifie une alerte (titre, description, déclencheur, machines,
affichage, questionnaire) depuis une consigne en français ou une fiche de
contrôle papier jointe (photo, PDF). Même principe que l'assistant des
formulaires de MyQualité (`qualite_formulaires_ia.py`) :

- Claude rend les paramètres via l'outil `proposer_alerte` ;
- le serveur les repasse par `_validate_alert_params` (settings.py), la même
  validation qu'une saisie dans le formulaire : une valeur hors référentiel est
  refusée, pas devinée ;
- rien n'est enregistré : la proposition remplit le formulaire, l'utilisateur
  la relit et enregistre.

Le questionnaire garde le format des alertes (`choice` / `value`) : c'est le
format que le moteur commun des formulaires reprend tel quel.
"""
from __future__ import annotations

import json
from typing import Optional

from app.services import ia_usage
from app.services.qualite_formulaires_ia import _blocs_pieces, _client
from config import ALERTES_IA_MODELE, alertes_ia_modeles

_MAX_TOKENS = 16000

_JOURS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_EVENEMENTS = {
    "dossier_start": "début de dossier",
    "dossier_end": "fin de dossier",
    "after_calage": "après le calage, au retour en production (delay_minutes = minutes de production avant l'alerte)",
}


class AlerteIaErreur(Exception):
    """Message affichable tel quel à l'utilisateur."""


def _consigne(machines: list[str]) -> str:
    liste = ", ".join(machines) if machines else "(aucune machine déclarée)"
    evts = "\n".join(f"  - {k} : {v}" for k, v in _EVENEMENTS.items())
    return f"""Tu paramètres des alertes de contrôle pour l'atelier de SIFA, fabricant d'étiquettes adhésives, dans l'outil MySifa. Une alerte s'affiche sur l'écran de saisie de production de l'opérateur ; il la valide en répondant à un questionnaire de points de contrôle.

Champs de l'alerte :
- `nom` : titre court affiché à l'opérateur (ex. « Inspection des produits finis »).
- `description` : contexte en une ou deux phrases, facultatif.
- `trigger` : quand l'alerte apparaît.
  - periodic : toutes les `interval_minutes` minutes (1 à 10080), seulement quand la machine produit ; `grace_minutes` (0 à 120, défaut 5) = délai avant la première alerte d'une session de production.
  - calendar : à heure fixe `time` (HH:MM) les jours `days` parmi {", ".join(_JOURS)}, même machine à l'arrêt (contrôle de prise de poste).
  - event : sur un événement métier `event` :
{evts}
- `machines` : machines ciblées, parmi : {liste}. ["*"] = toutes les machines.
- `block_production` : true si l'opérateur ne doit plus pouvoir saisir tant qu'il n'a pas validé (contrôle critique). Par défaut false.
- `dismiss_button` : bouton pour fermer l'alerte sans répondre ({{"enabled": true, "label": "Pas de production"}}). Par défaut désactivé.
- `checklist` : le questionnaire, `enabled` = true et `items` = points de contrôle :
  - choice : `responses` (réponses courtes, ex. ["Conforme", "Non conforme"]), `multi` (plusieurs réponses possibles, défaut true ; false pour un choix unique), `nc_responses` (réponses qui signalent une non-conformité), `allow_other` (ajoute « Autre » avec précision), `other_is_nc`, `comment_responses` (réponses qui exigent un commentaire de l'opérateur).
  - value : valeur mesurée, `unit`, `min` et `max` (tolérance), `target_value` (cible), `points` (libellés fixes quand il faut plusieurs mesures, ex. ["Début de prod", "Milieu de prod", "Fin de prod"]), ou bien `points_libres` = true quand le nombre de mesures varie et que l'opérateur ajoute lui-même ses lignes (ex. un poids par front, selon la laize) avec `libelle_point` (ex. "Front"), `min_points` et `max_points` (1 à 50), `out_of_range_is_nc` (hors tolérance = non-conformité, seulement avec min ou max), `placeholder`.
  - pour tous : `label` (la question), `required` (réponse obligatoire), `help` (méthode de contrôle en une ou deux phrases).

Règles :
- N'invente ni tolérance, ni cible, ni fréquence, ni machine : ne mets que ce que la consigne ou la fiche jointe indique. Sinon, garde la valeur actuelle ou la valeur par défaut, et dis-le dans `remarques`.
- Libellés courts, en français, à l'adresse d'un opérateur.
- Pour modifier une alerte existante : pars des paramètres fournis, garde tel quel ce que la consigne ne vise pas, ne change que ce qui est demandé.
- Depuis une fiche de contrôle jointe : reprends ses points dans l'ordre, avec le type de réponse le plus proche (case à cocher → choice, valeur mesurée → value).

Appelle l'outil `proposer_alerte` une seule fois, avec l'alerte complète. `resume` dit en une ou deux phrases ce que tu as fait ; `remarques` liste ce qu'il faut vérifier ou compléter. Aucun texte en dehors de l'outil."""


_ITEM = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["choice", "value"]},
        "label": {"type": "string"},
        "required": {"type": "boolean"},
        "help": {"type": "string"},
        "responses": {"type": "array", "items": {"type": "string"}},
        "multi": {"type": "boolean"},
        "nc_responses": {"type": "array", "items": {"type": "string"}},
        "allow_other": {"type": "boolean"},
        "other_is_nc": {"type": "boolean"},
        "comment_responses": {"type": "array", "items": {"type": "string"}},
        "other_needs_comment": {"type": "boolean"},
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
        "placeholder": {"type": "string"},
    },
    "required": ["type", "label"],
}

_OUTIL = {
    "name": "proposer_alerte",
    "description": "Rend l'alerte complète : titre, déclencheur, machines, affichage et questionnaire.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nom": {"type": "string"},
            "description": {"type": "string"},
            "trigger": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["periodic", "calendar", "event"]},
                    "interval_minutes": {"type": "integer"},
                    "grace_minutes": {"type": "integer"},
                    "time": {"type": "string"},
                    "days": {"type": "array", "items": {"type": "string", "enum": _JOURS}},
                    "event": {"type": "string", "enum": list(_EVENEMENTS)},
                    "delay_minutes": {"type": "integer"},
                },
                "required": ["type"],
            },
            "machines": {"type": "array", "items": {"type": "string"}},
            "block_production": {"type": "boolean"},
            "dismiss_button": {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}, "label": {"type": "string"}},
            },
            "checklist": {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}, "items": {"type": "array", "items": _ITEM}},
            },
            "resume": {"type": "string"},
            "remarques": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["nom", "trigger", "machines", "checklist", "resume"],
    },
}


def choisir_modele(modele: Optional[str]) -> dict:
    liste = alertes_ia_modeles()
    modeles = {m["id"]: m for m in liste}
    if not modele:
        return modeles.get(ALERTES_IA_MODELE) or liste[0]
    if modele not in modeles:
        raise AlerteIaErreur(f"Modèle « {modele} » non proposé — choisir dans la liste.")
    return modeles[modele]


def proposer(consigne: str, *, nom: str, params: Optional[dict], machines: list[str],
             valider, pieces: Optional[list[dict]] = None, modele: Optional[str] = None) -> dict:
    """Rend {"nom", "params", "resume", "remarques", "modele", …}.

    `params` vide = création ; sinon modification. `valider(params) -> params`
    est la validation des alertes (`_validate_alert_params`) : elle lève une
    exception si la proposition n'est pas acceptable. `machines` = noms des
    machines actives, seules valeurs admises en plus de « * ».
    """
    choix = choisir_modele(modele)
    client = _client()
    if client is None:
        raise AlerteIaErreur("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")

    actuel = params if isinstance(params, dict) else {}
    texte = ""
    if actuel.get("checklist") or actuel.get("description") or (nom or "").strip():
        texte += "Alerte actuelle :\n" + json.dumps({"nom": nom or "", **actuel}, ensure_ascii=False) + "\n\n"
    texte += "Consigne :\n" + ((consigne or "").strip() or "Crée l'alerte d'après la fiche de contrôle jointe.")
    contenu = _blocs_pieces(pieces or []) + [{"type": "text", "text": texte}]

    options = {"extra_body": {"output_config": {"effort": "medium"}}}
    if choix.get("repli"):
        options["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
        options["extra_body"]["fallbacks"] = "default"
    try:
        reponse = client.messages.create(
            model=choix["id"],
            max_tokens=_MAX_TOKENS,
            system=_consigne(machines),
            tools=[_OUTIL],
            # Le choix forcé d'un outil est refusé par les modèles récents :
            # la consigne demande l'outil, la réponse est contrôlée ci-dessous.
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": contenu}],
            **options,
        )
    except Exception as e:
        raise AlerteIaErreur(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "alertes")

    if getattr(reponse, "stop_reason", "") == "refusal":
        raise AlerteIaErreur("L'assistant a refusé cette demande. Reformuler la consigne.")
    if getattr(reponse, "stop_reason", "") == "max_tokens":
        raise AlerteIaErreur("Réponse de l'assistant tronquée — questionnaire trop long pour un seul passage.")

    entree = None
    for bloc in reponse.content:
        if getattr(bloc, "type", "") == "tool_use" and getattr(bloc, "name", "") == "proposer_alerte":
            entree = bloc.input
            if isinstance(entree, str):
                try:
                    entree = json.loads(entree)
                except Exception:
                    entree = None
            break
    if not isinstance(entree, dict):
        raise AlerteIaErreur("L'assistant n'a pas rendu d'alerte. Préciser la consigne et relancer.")

    remarques = [str(r)[:300] for r in (entree.get("remarques") or []) if r][:10]
    # Machines : seulement celles qui existent ; une machine inconnue est
    # retirée et signalée plutôt que créée.
    connues = {m.casefold(): m for m in machines}
    demandees = [str(m).strip() for m in (entree.get("machines") or []) if str(m).strip()]
    retenues, inconnues = [], []
    for m in demandees:
        if m == "*":
            retenues = ["*"]
            break
        if m.casefold() in connues:
            retenues.append(connues[m.casefold()])
        else:
            inconnues.append(m)
    if inconnues:
        remarques.append("Machine(s) inconnue(s) ignorée(s) : " + ", ".join(inconnues) + ".")
    if not retenues:
        retenues = list((actuel.get("target") or {}).get("machines") or ["*"])

    brut = {
        "description": entree.get("description") or "",
        "trigger": entree.get("trigger") or actuel.get("trigger") or {"type": "periodic", "interval_minutes": 120},
        "target": {"machines": retenues},
        "block_production": bool(entree.get("block_production", actuel.get("block_production", False))),
        "dismiss_button": entree.get("dismiss_button") or actuel.get("dismiss_button") or {},
        "checklist": entree.get("checklist") or {},
        # Affichage : réglage de l'écran, jamais proposé par l'assistant.
        "placement": actuel.get("placement") or "top-right",
        "size": actuel.get("size") or "medium",
    }
    try:
        propre = valider(brut)
    except Exception as e:
        detail = getattr(e, "detail", None) or str(e)
        raise AlerteIaErreur(f"Proposition de l'assistant invalide ({detail}). Préciser la consigne et relancer.")
    return {
        "nom": str(entree.get("nom") or nom or "").strip()[:120],
        "params": propre,
        "resume": str(entree.get("resume") or "")[:600],
        "remarques": remarques[:12],
        "modele": choix["id"],
        "modele_libelle": choix.get("libelle", choix["id"]),
        "modele_reel": str(getattr(reponse, "model", "") or choix["id"]),
    }
