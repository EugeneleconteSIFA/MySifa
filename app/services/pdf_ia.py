"""MyTools › Éditeur PDF — fonctions IA (Claude) sur un PDF.

Le navigateur envoie le PDF qu'il vient de produire (annotations comprises).
Quatre usages, un appel chacun :

  resumer(pdf)                      → {"texte"}
  question(pdf, question)           → {"reponse"}
  extraire(pdf, nature, consigne)   → {"colonnes", "lignes", "remarques"}
  champs(pdf)                       → {"champs": [{page, nom, type, x, y, l, h, options}]}
                                      coordonnées normalisées 0–1000, origine en haut à gauche

Chaque appel passe par ia_usage.noter() (fonction « pdf ») : la route ouvre le
suivi au nom de l'utilisateur. Les erreurs remontent en PdfIaErreur avec un
message affichable.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Optional

from app.services import ia_usage
from config import PDF_IA_MODELE

_MAX_TOKENS = 16000


class PdfIaErreur(Exception):
    """Message destiné à l'utilisateur."""


def _client():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    try:
        import anthropic
    except Exception:
        return None
    return anthropic.Anthropic(api_key=cle)


def _document(pdf: bytes) -> dict:
    return {"type": "document",
            "source": {"type": "base64", "media_type": "application/pdf",
                       "data": base64.standard_b64encode(pdf).decode()}}


def _appel(pdf: bytes, consigne: str, systeme: str, effort: str = "medium",
           schema: Optional[dict] = None) -> str:
    """Un appel à Claude avec le PDF ; rend le texte de la réponse."""
    client = _client()
    if client is None:
        raise PdfIaErreur("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")
    sortie: dict[str, Any] = {"effort": effort}
    if schema is not None:
        sortie["format"] = {"type": "json_schema", "schema": schema}
    try:
        reponse = client.messages.create(
            model=PDF_IA_MODELE,
            max_tokens=_MAX_TOKENS,
            system=systeme,
            messages=[{"role": "user", "content": [_document(pdf), {"type": "text", "text": consigne}]}],
            # Repli serveur sur refus (catégorie de refus → modèle recommandé).
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"output_config": sortie, "fallbacks": "default"},
        )
    except Exception as e:
        raise PdfIaErreur(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "pdf")
    ia_usage.preciser(modele_demande=PDF_IA_MODELE, fichiers=1)
    raison = getattr(reponse, "stop_reason", "")
    if raison == "refusal":
        raise PdfIaErreur("L'assistant a refusé cette demande sur ce document.")
    if raison == "max_tokens":
        raise PdfIaErreur("Réponse tronquée — document trop long pour un seul passage.")
    texte = "".join(getattr(b, "text", "") for b in reponse.content if getattr(b, "type", "") == "text").strip()
    if not texte:
        raise PdfIaErreur("Réponse vide de l'assistant.")
    return texte


def _json(texte: str) -> dict:
    try:
        return json.loads(texte)
    except ValueError:
        raise PdfIaErreur("Réponse illisible de l'assistant — recommencer.")


_SYSTEME = ("Tu travailles sur un document PDF fourni par un utilisateur d'un outil interne d'entreprise. "
            "Tu réponds en français, de façon factuelle et directe, sans formule de politesse ni emoji. "
            "Tu ne t'appuies que sur le contenu du document ; si une information n'y est pas, tu le dis.")


def resumer(pdf: bytes) -> dict:
    texte = _appel(pdf, (
        "Résume ce document : d'abord une phrase qui dit de quoi il s'agit, puis les points clés "
        "en liste (montants, dates, parties, engagements, échéances), puis ce qui demande une action. "
        "Texte brut, listes en « - », 250 mots au plus."), _SYSTEME, effort="medium")
    return {"texte": texte}


def question(pdf: bytes, q: str) -> dict:
    q = (q or "").strip()
    if not q:
        raise PdfIaErreur("Question vide.")
    texte = _appel(pdf, (
        f"Question : {q}\n\nRéponds à partir du document seulement. Cite la page (« p. 3 ») "
        "des passages sur lesquels tu t'appuies. Texte brut."), _SYSTEME, effort="medium")
    return {"reponse": texte}


NATURES = {
    "facture": "une facture : fournisseur, numéro, date, échéance, puis une ligne par article "
               "(référence, désignation, quantité, unité, prix unitaire HT, montant HT, TVA)",
    "bl": "un bon de livraison : expéditeur, destinataire, numéro, date, puis une ligne par article "
          "(référence, désignation, quantité livrée, unité, lot)",
    "fiche": "une fiche technique : une ligne par caractéristique (caractéristique, valeur, unité, norme ou méthode)",
    "libre": "le tableau demandé par l'utilisateur",
}

_SCHEMA_TABLEAU = {
    "type": "object",
    "properties": {
        "colonnes": {"type": "array", "items": {"type": "string"}},
        "lignes": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
        "remarques": {"type": "string"},
    },
    "required": ["colonnes", "lignes", "remarques"],
    "additionalProperties": False,
}


def extraire(pdf: bytes, nature: str, consigne: str = "") -> dict:
    if nature not in NATURES:
        raise PdfIaErreur("Type de document inconnu.")
    texte = _appel(pdf, (
        f"Ce document est {NATURES[nature]}. Extrais les données en un tableau : "
        "« colonnes » = en-têtes, « lignes » = une liste de cellules par ligne, dans l'ordre des colonnes, "
        "valeurs recopiées telles qu'écrites (nombres au format du document). Les informations d'en-tête "
        "(fournisseur, numéro, date…) vont dans des colonnes répétées sur chaque ligne. "
        "« remarques » : ce qui est illisible ou ambigu, vide sinon."
        + (f"\n\nConsigne de l'utilisateur : {consigne.strip()}" if consigne and consigne.strip() else "")),
        _SYSTEME, effort="high", schema=_SCHEMA_TABLEAU)
    d = _json(texte)
    n = len(d.get("colonnes") or [])
    lignes = [[str(c) for c in (l or [])][:n] + [""] * max(0, n - len(l or [])) for l in (d.get("lignes") or [])]
    return {"colonnes": [str(c) for c in d.get("colonnes") or []], "lignes": lignes, "remarques": str(d.get("remarques") or "")}


_TYPES_CHAMP = ["texte", "multi", "case", "date", "signature", "liste"]
_SCHEMA_CHAMPS = {
    "type": "object",
    "properties": {
        "champs": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "page": {"type": "integer"},
                "nom": {"type": "string"},
                "type": {"type": "string", "enum": _TYPES_CHAMP},
                "x": {"type": "number"}, "y": {"type": "number"},
                "l": {"type": "number"}, "h": {"type": "number"},
                "options": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["page", "nom", "type", "x", "y", "l", "h", "options"],
            "additionalProperties": False,
        }},
    },
    "required": ["champs"],
    "additionalProperties": False,
}


def champs(pdf: bytes) -> dict:
    texte = _appel(pdf, (
        "Ce PDF est un formulaire à plat (non remplissable). Repère chaque zone à remplir : ligne "
        "pointillée ou soulignée après un libellé, case à cocher, cadre vide, zone « Signature », "
        "date (« / / »), liste de choix. Pour chacune : « page » (1 = première), « nom » court tiré du "
        "libellé (sans point), « type » parmi texte, multi (zone de plusieurs lignes), case, date, "
        "signature, liste (alors « options »), et la zone de saisie elle-même (pas le libellé) en "
        "coordonnées normalisées 0–1000 de la page : « x », « y » = coin haut-gauche, « l », « h » = "
        "largeur et hauteur. « options » vide sauf pour une liste."), _SYSTEME, effort="high", schema=_SCHEMA_CHAMPS)
    d = _json(texte)
    sortie = []
    for c in d.get("champs") or []:
        try:
            x, y, l, h = (max(0.0, min(1000.0, float(c[k]))) for k in ("x", "y", "l", "h"))
        except (KeyError, TypeError, ValueError):
            continue
        if l < 3 or h < 3:
            continue
        sortie.append({"page": int(c.get("page") or 1), "nom": str(c.get("nom") or "Champ").replace(".", " ")[:60],
                       "type": c.get("type") if c.get("type") in _TYPES_CHAMP else "texte",
                       "x": x, "y": y, "l": l, "h": h, "options": [str(o) for o in (c.get("options") or [])][:30]})
    return {"champs": sortie}


# ─── Lot 4 : sélection, contrats, BAT, génération ─────────────────

def _appel_texte(contenu: list, consigne_sys: str, effort: str = "medium", schema: Optional[dict] = None) -> str:
    """Comme _appel, avec un contenu déjà composé (plusieurs documents, texte seul)."""
    client = _client()
    if client is None:
        raise PdfIaErreur("Assistant IA indisponible — clé ANTHROPIC_API_KEY absente du serveur.")
    sortie: dict[str, Any] = {"effort": effort}
    if schema is not None:
        sortie["format"] = {"type": "json_schema", "schema": schema}
    try:
        reponse = client.messages.create(
            model=PDF_IA_MODELE, max_tokens=_MAX_TOKENS, system=consigne_sys,
            messages=[{"role": "user", "content": contenu}],
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"output_config": sortie, "fallbacks": "default"},
        )
    except Exception as e:
        raise PdfIaErreur(f"Appel à l'assistant en échec : {e}")
    ia_usage.noter(reponse, "pdf")
    ia_usage.preciser(modele_demande=PDF_IA_MODELE,
                      fichiers=sum(1 for b in contenu if isinstance(b, dict) and b.get("type") == "document"))
    raison = getattr(reponse, "stop_reason", "")
    if raison == "refusal":
        raise PdfIaErreur("L'assistant a refusé cette demande.")
    if raison == "max_tokens":
        raise PdfIaErreur("Réponse tronquée — documents trop longs pour un seul passage.")
    texte = "".join(getattr(b, "text", "") for b in reponse.content if getattr(b, "type", "") == "text").strip()
    if not texte:
        raise PdfIaErreur("Réponse vide de l'assistant.")
    return texte


MODES_SELECTION = {
    "expliquer": "Explique ce passage en termes simples (5 phrases au plus), en disant ce qu'il implique concrètement.",
    "reformuler": "Reformule ce passage en français clair et direct, même sens, même niveau de formalité. Rends seulement le texte reformulé.",
    "resumer": "Résume ce passage en 2 phrases.",
}


def selection(texte: str, mode: str) -> dict:
    texte = (texte or "").strip()
    if not texte:
        raise PdfIaErreur("Aucun texte sélectionné.")
    if mode not in MODES_SELECTION:
        raise PdfIaErreur("Demande inconnue.")
    r = _appel_texte([{"type": "text", "text": f"{MODES_SELECTION[mode]}\n\nPassage :\n{texte[:20000]}"}], _SYSTEME, effort="low")
    return {"texte": r}


def contrats(pdf_a: bytes, pdf_b: bytes) -> dict:
    contenu = [_document(pdf_a), {"type": "text", "text": "Document A (version de référence) ci-dessus."},
               _document(pdf_b), {"type": "text", "text": "Document B (nouvelle version) ci-dessus.\n\n"
               "Compare ces deux versions d'un contrat ou de conditions. Liste les clauses qui changent : pour chacune, "
               "l'article ou la section, ce que disait A, ce que dit B, et l'effet concret (qui y gagne, quel risque). "
               "Puis les clauses ajoutées et retirées. Termine par les 3 points à négocier en priorité. "
               "Texte brut, titres en majuscules, listes en « - ». N'invente rien : seulement ce qui diffère réellement."}]
    return {"texte": _appel_texte(contenu, _SYSTEME, effort="high")}


_SCHEMA_BAT = {
    "type": "object",
    "properties": {
        "points": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "sujet": {"type": "string"},
                "attendu": {"type": "string"},
                "constate": {"type": "string"},
                "statut": {"type": "string", "enum": ["conforme", "ecart", "a_verifier"]},
                "page": {"type": "integer"},
            },
            "required": ["sujet", "attendu", "constate", "statut", "page"],
            "additionalProperties": False,
        }},
        "synthese": {"type": "string"},
    },
    "required": ["points", "synthese"],
    "additionalProperties": False,
}


def bat(pdf: bytes, fiche: dict) -> dict:
    utile = {k: v for k, v in (fiche or {}).items() if v not in (None, "") and not str(k).endswith("_id")
             and k not in ("champs_manuels", "date_import", "imported_by", "source", "pdf_path")}
    r = _appel_texte([_document(pdf), {"type": "text", "text": (
        "Ce PDF est un BAT (bon à tirer) d'étiquette. Vérifie-le contre la fiche technique ci-dessous : "
        "dimensions et format, forme et rayons, nombre de couleurs et teintes (Pantone), sens d'enroulement, "
        "mentions obligatoires, références, codes (EAN, lot), textes. Un point par vérification, "
        "« statut » = conforme, ecart ou a_verifier (si le BAT ne permet pas de conclure), « page » = page du BAT "
        "concernée (1 si global). « synthese » : 2 phrases.\n\nFiche technique :\n"
        + json.dumps(utile, ensure_ascii=False, default=str)[:15000])}], _SYSTEME, effort="high", schema=_SCHEMA_BAT)
    d = _json(r)
    return {"points": d.get("points") or [], "synthese": str(d.get("synthese") or "")}


def remplir(pdf: bytes, champs_: list, donnees: str) -> dict:
    noms = [str(c.get("nom")) for c in (champs_ or []) if isinstance(c, dict) and c.get("nom")][:300]
    if not noms:
        raise PdfIaErreur("Ce modèle n'a pas de champ à remplir.")
    if not (donnees or "").strip():
        raise PdfIaErreur("Données vides.")
    schema = {"type": "object", "properties": {"valeurs": {"type": "array", "items": {
        "type": "object", "properties": {"nom": {"type": "string"}, "valeur": {"type": "string"}},
        "required": ["nom", "valeur"], "additionalProperties": False}}},
        "required": ["valeurs"], "additionalProperties": False}
    r = _appel_texte([_document(pdf), {"type": "text", "text": (
        "Ce PDF est un modèle avec des champs à remplir. Remplis chaque champ à partir des données fournies, "
        "au format attendu par son libellé (date JJ/MM/AAAA, montants avec virgule). Laisse vide (« ») un champ "
        "dont la donnée manque — n'invente rien.\n\nChamps : " + json.dumps(champs_, ensure_ascii=False)[:8000]
        + "\n\nDonnées :\n" + donnees[:20000])}], _SYSTEME, effort="medium", schema=schema)
    d = _json(r)
    ok = set(noms)
    return {"valeurs": {str(v.get("nom")): str(v.get("valeur") or "") for v in d.get("valeurs") or [] if str(v.get("nom")) in ok}}
