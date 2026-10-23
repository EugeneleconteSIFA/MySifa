"""
MySifa — lecture d'un justificatif de note de frais (ticket, facture).

Le salarié photographie ou dépose son justificatif dans Mon coffre ; Claude en
lit la date, le commerce, la ville, le montant TTC et la TVA par taux, et
propose une catégorie. Le formulaire se pré-remplit, le salarié vérifie et
corrige avant d'envoyer.

Ce module LIT et PROPOSE. Il n'écrit rien en base : la note n'existe que quand
le salarié l'enregistre, avec les montants recalculés par `ndf_lignes_tva()`.

Ticket à plusieurs taux (restaurant : 10 % sur la nourriture, 20 % sur
l'alcool) : une ligne par taux, avec son TTC et sa TVA, comme sur le ticket.
Si la somme des lignes ne retombe pas sur le total du ticket, la remarque le
dit au salarié au lieu de corriger en silence.

Ticket étranger : sa TVA ne se récupère pas sur la déclaration française. La
note est proposée « Sans TVA » et la remarque le dit. Si le total n'est pas en
euros, il n'est pas reporté : le salarié saisit le montant converti.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import date
from typing import Optional

from app.services import ia_usage
from config import NDF_SCAN_IA_ACTIVE, NDF_SCAN_IA_MODELE, NDF_TAUX_TVA

# Pays dont la TVA est la TVA française : Monaco, et les DOM qui ont leur
# propre code ISO.
_PAYS_TVA_FRANCAISE = {"FR", "MC", "GP", "MQ", "RE", "GF", "YT"}

# Au-delà, l'image est réduite avant l'envoi : l'API refuse les images de plus
# de 5 Mo, et un ticket se lit très bien à 2 000 px de long.
log = logging.getLogger(__name__)

_IMAGE_MAX_OCTETS = 3_500_000
_IMAGE_MAX_COTE = 2000

_MIMES_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _nombre_ou_nul(description: str) -> dict:
    return {"anyOf": [{"type": "number"}, {"type": "null"}], "description": description}


def _texte_ou_nul(description: str) -> dict:
    return {"anyOf": [{"type": "string"}, {"type": "null"}], "description": description}


def _schema(codes: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "lisible": {"type": "boolean", "description": "Le document est-il un ticket ou une facture lisible ?"},
            "date": _texte_ou_nul("Date de la dépense, AAAA-MM-JJ."),
            "commerce": _texte_ou_nul("Nom du commerce ou du fournisseur."),
            "ville": _texte_ou_nul("Ville du commerce."),
            "pays": _texte_ou_nul("Pays du commerce, code ISO à 2 lettres (FR, DE, BE…)."),
            "devise": _texte_ou_nul("Devise du total, code ISO à 3 lettres (EUR, CHF, GBP…)."),
            "montant_ttc": _nombre_ou_nul("Total payé TTC, dans la devise du ticket."),
            "tva": {
                "type": "array",
                "description": "Une ligne par taux de TVA imprimé sur le ticket.",
                "items": {
                    "type": "object",
                    "properties": {
                        "taux": {"type": "number", "description": "Taux en %, ex. 10 ou 5.5."},
                        "montant": {"type": "number", "description": "Montant de TVA à ce taux, dans la devise du ticket."},
                        "base_ht": _nombre_ou_nul("Montant HT à ce taux, s'il est imprimé."),
                        "ttc": _nombre_ou_nul("Montant TTC à ce taux, s'il est imprimé."),
                    },
                    "required": ["taux", "montant", "base_ht", "ttc"],
                    "additionalProperties": False,
                },
            },
            "categorie": {"type": "string", "enum": codes + ["inconnue"]},
            "remarque": _texte_ou_nul("Ce qui est illisible ou douteux, en une phrase."),
        },
        "required": ["lisible", "date", "commerce", "ville", "pays", "devise", "montant_ttc", "tva", "categorie", "remarque"],
        "additionalProperties": False,
    }


def _consigne(categories: list[dict]) -> str:
    liste = "\n".join(f"- {c['code']} : {c['libelle']}" for c in categories)
    return f"""Tu lis le justificatif d'une note de frais d'un salarié français : ticket de caisse, facture, reçu de péage ou de parking.

Relève uniquement ce qui est imprimé sur le document :
- la date de la dépense ;
- le nom du commerce et sa ville ;
- le pays du commerce (d'après l'adresse, la langue, le numéro de TVA) et la devise du total ;
- le total payé TTC ;
- la TVA, une ligne par taux imprimé : le taux en %, le montant de TVA, et le montant HT (base) et TTC à ce taux s'ils sont imprimés. Un restaurant a souvent deux taux (10 % et 20 %) : relève les deux lignes séparément.

Choisis la catégorie dans cette liste, d'après la nature de la dépense :
{liste}
Réponds « inconnue » si aucune ne convient clairement.

Règles :
1. N'invente rien. Une valeur absente ou illisible vaut null ; une TVA non imprimée donne une liste vide.
2. Les montants sont relevés tels qu'imprimés, dans la devise du ticket, avec un point décimal.
3. Si le document n'est pas un justificatif de dépense, mets lisible à false."""


def _client():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    try:
        import anthropic
    except Exception:
        return None
    return anthropic.Anthropic(api_key=cle)


def _bloc(file_bytes: bytes, mime: str) -> Optional[dict]:
    """Bloc de contenu pour l'API, image réduite si besoin. None si format non lu."""
    if mime == "application/pdf":
        data = base64.standard_b64encode(file_bytes).decode()
        return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    if mime not in _MIMES_IMAGE:
        return None
    if len(file_bytes) > _IMAGE_MAX_OCTETS:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            img = img.convert("RGB")
            img.thumbnail((_IMAGE_MAX_COTE, _IMAGE_MAX_COTE))
            sortie = io.BytesIO()
            img.save(sortie, format="JPEG", quality=85)
            file_bytes, mime = sortie.getvalue(), "image/jpeg"
        except Exception:
            return None
    data = base64.standard_b64encode(file_bytes).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}


def _date(valeur) -> Optional[str]:
    v = (valeur or "").strip()[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return None
    try:
        d = date.fromisoformat(v)
    except ValueError:
        return None
    # Une date dans le futur ou de plus de deux ans est une erreur de lecture.
    if d > date.today() or (date.today() - d).days > 730:
        return None
    return v


def _montant(valeur) -> Optional[float]:
    try:
        v = round(float(valeur), 2)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def interpreter(brut: dict, categories: list[dict]) -> dict:
    """Ramène la lecture du modèle aux champs du formulaire. Séparé de l'appel
    pour être testé sans réseau."""
    if not brut.get("lisible"):
        return {"ok": False, "erreur": (brut.get("remarque") or "Justificatif illisible — saisissez la note à la main.")}

    ttc = _montant(brut.get("montant_ttc"))
    pays = (brut.get("pays") or "").strip().upper()[:2]
    devise = (brut.get("devise") or "").strip().upper()[:3]
    etranger = bool(pays) and pays not in _PAYS_TVA_FRANCAISE
    autre_devise = bool(devise) and devise != "EUR"
    remarques = []
    if autre_devise:
        # Un montant en francs suisses posé comme des euros fausserait le
        # remboursement : on le montre, on ne le reporte pas.
        if ttc is not None:
            remarques.append(f"Total de {ttc:.2f} {devise} : saisissez le montant converti en euros.".replace(".", ",", 1))
        else:
            remarques.append(f"Ticket en {devise} : saisissez le montant converti en euros.")
        ttc = None
    if etranger:
        remarques.append(f"Ticket étranger ({pays}) : TVA non récupérable en France, note proposée sans TVA.")

    # Lignes de TVA : une par taux légal, au centime près.
    par_taux: dict = {}
    for l in ([] if etranger or autre_devise else brut.get("tva") or []):
        try:
            taux = float(l.get("taux"))
            tva_l = round(float(l.get("montant")), 2)
        except (TypeError, ValueError, AttributeError):
            continue
        if taux not in NDF_TAUX_TVA or tva_l < 0:
            continue
        ttc_l = _montant(l.get("ttc"))
        if ttc_l is None:
            base = _montant(l.get("base_ht"))
            if base is not None:
                ttc_l = round(base + tva_l, 2)
            elif taux > 0 and tva_l > 0:
                ttc_l = round(tva_l * (100 + taux) / taux, 2)
        d = par_taux.setdefault(taux, {"taux": taux, "ttc": 0.0, "tva": 0.0, "complet": True})
        d["tva"] = round(d["tva"] + tva_l, 2)
        if ttc_l is None:
            d["complet"] = False
        else:
            d["ttc"] = round(d["ttc"] + ttc_l, 2)
    lignes = sorted(par_taux.values(), key=lambda d: -d["taux"])
    if etranger and ttc is not None:
        lignes = [{"taux": 0.0, "ttc": ttc, "tva": 0.0, "complet": True}]
    if len(lignes) == 1 and ttc is not None:
        # Un seul taux : le total du ticket fait foi pour le TTC de la ligne.
        lignes[0]["ttc"], lignes[0]["complet"] = ttc, True
    lignes = [l for l in lignes if l["complet"] and l["ttc"] > 0 and l["tva"] < l["ttc"]]
    if lignes:
        somme = round(sum(l["ttc"] for l in lignes), 2)
        if ttc is None:
            ttc = somme
        elif abs(somme - ttc) > 0.02:
            remarques.append(
                f"Écart de {abs(somme - ttc):.2f} € entre les lignes de TVA et le total du ticket — vérifiez.".replace(".", ",", 1))
    if len(lignes) > 1:
        remarques.append("Ticket à " + " et ".join(
            f"{l['taux']:g} %".replace(".", ",") for l in lignes) + " : une ligne par taux.")
    if brut.get("remarque"):
        remarques.append(str(brut["remarque"]).strip())
    tva_lignes = [{"taux": l["taux"], "ttc": l["ttc"], "tva": l["tva"]} for l in lignes] or None

    cat = next((c for c in categories if c["code"] == brut.get("categorie")), None)
    commerce = (brut.get("commerce") or "").strip()[:80] or None
    ville = (brut.get("ville") or "").strip()[:80] or None

    champs = {
        "date_frais": _date(brut.get("date")),
        "montant_ttc": ttc,
        "tva_lignes": tva_lignes,
        "taux_tva": tva_lignes[0]["taux"] if tva_lignes and len(tva_lignes) == 1 else None,
        "montant_tva": round(sum(l["tva"] for l in tva_lignes), 2) if tva_lignes else None,
        "ville": ville,
        "categorie_id": cat["id"] if cat else None,
        "description": commerce,
    }
    lus = [k for k, v in champs.items() if v is not None]
    if not lus:
        # Ticket en devise sans autre champ lisible : la remarque dit quoi faire.
        return {"ok": False, "erreur": " ".join(remarques) or "Rien de lisible sur le justificatif — saisissez la note à la main."}
    return {"ok": True, "champs": champs, "lus": lus, "remarque": " ".join(remarques) or None}


def lire_justificatif(file_bytes: bytes, mime: str, categories: list[dict]) -> dict:
    """Lit un justificatif. `categories` : catégories actives saisies en
    montant ({id, code, libelle}). Rend {ok, champs, lus, remarque} ou
    {ok: False, erreur}."""
    if not NDF_SCAN_IA_ACTIVE:
        return {"ok": False, "erreur": "Lecture automatique désactivée — saisissez la note à la main."}
    bloc = _bloc(file_bytes, (mime or "").lower())
    if bloc is None:
        return {"ok": False, "erreur": "Format non lu automatiquement (PDF, JPG ou PNG attendus) — complétez à la main."}
    client = _client()
    if client is None:
        return {"ok": False, "erreur": "Lecture automatique indisponible — saisissez la note à la main."}

    codes = [c["code"] for c in categories]
    try:
        # Paramètres récents passés par extra_body / extra_headers : ils
        # fonctionnent quelle que soit la version du SDK installée sur le VPS.
        reponse = client.messages.create(
            model=NDF_SCAN_IA_MODELE,
            max_tokens=4000,
            system=_consigne(categories),
            messages=[{"role": "user", "content": [bloc, {"type": "text", "text": "Lis ce justificatif."}]}],
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={
                "output_config": {
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": _schema(codes)},
                },
                "fallbacks": "default",
            },
        )
    except Exception as e:
        # Le détail (statut, message de l'API) va au journal du serveur, pas au salarié.
        log.warning("ndf_scan : appel au modèle en échec : %s", e)
        return {"ok": False, "erreur": f"Lecture automatique en échec ({type(e).__name__}) — complétez à la main."}
    ia_usage.noter(reponse, "ndf")

    if getattr(reponse, "stop_reason", "") in ("refusal", "max_tokens"):
        return {"ok": False, "erreur": "Justificatif non lu — saisissez la note à la main."}
    texte = next((b.text for b in reponse.content if getattr(b, "type", "") == "text"), "")
    try:
        brut = json.loads(texte)
    except Exception:
        return {"ok": False, "erreur": "Lecture illisible — saisissez la note à la main."}
    resultat = interpreter(brut, categories)
    resultat["modele"] = NDF_SCAN_IA_MODELE
    return resultat
