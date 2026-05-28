"""MyExpé — textes email RFQ transporteur (FR / EN)."""

from __future__ import annotations

_EXPE_TYPE_FR = {
    "messagerie": "Messagerie",
    "ramasse": "Ramasse",
    "affretement": "Affrètement",
}
_EXPE_TYPE_EN = {
    "messagerie": "Groupage / parcel service",
    "ramasse": "Collection",
    "affretement": "Full truckload",
}


def expe_type_envoi_label(type_raw: str, lang: str) -> str:
    raw = (type_raw or "messagerie").strip()
    labels = _EXPE_TYPE_EN if lang == "en" else _EXPE_TYPE_FR
    return labels.get(raw, raw)


def expe_rfq_email_strings(lang: str, *, cp: str, user_nom: str) -> dict[str, str]:
    if lang == "en":
        return {
            "subtitle": "Transport quote request",
            "hello": "Hello,",
            "intro": (
                "<strong style=\"color:#0f172a\">SIFA</strong> (Roubaix, France) is requesting "
                "a transport quote for the shipment below."
            ),
            "cp_label": "Destination postcode",
            "type_label": "Shipment type",
            "weight_label": "Total weight",
            "pallets_label": "Pallets",
            "constraints_label": "Constraints",
            "cta": "Reply on the portal",
            "ask": (
                "Please submit your <strong style=\"color:#0f172a\">best net price (excl. tax)</strong> "
                "and <strong style=\"color:#0f172a\">estimated delivery time</strong> via our secure portal."
            ),
            "hint": "It takes less than a minute: price and lead time only.",
            "regards": "Kind regards,",
            "service": "SIFA — Shipping department",
            "footer": "MySifa carrier portal — personal link, do not share.",
            "subject": f"Transport quote request — SIFA Roubaix — {cp}",
            "switch_hint": "Language / Langue",
        }
    return {
        "subtitle": "Demande de tarif transport",
        "hello": "Bonjour,",
        "intro": (
            "<strong style=\"color:#0f172a\">SIFA</strong> (Roubaix) vous sollicite pour établir "
            "un tarif de transport pour l'envoi ci-dessous."
        ),
        "cp_label": "Code postal destination",
        "type_label": "Type d'envoi",
        "weight_label": "Poids total",
        "pallets_label": "Palettes",
        "constraints_label": "Contraintes",
        "cta": "Répondre sur le portail",
        "ask": (
            "Merci de nous transmettre votre <strong style=\"color:#0f172a\">meilleur tarif HT</strong> "
            "et le <strong style=\"color:#0f172a\">délai de livraison estimé</strong> via le portail sécurisé."
        ),
        "hint": "La saisie prend moins d'une minute : prix et délai uniquement.",
        "regards": "Cordialement,",
        "service": "SIFA — Service expéditions",
        "footer": "Portail transporteur MySifa — lien personnel, ne pas partager.",
        "subject": f"Demande de tarif transport — SIFA Roubaix — {cp}",
        "switch_hint": "Langue / Language",
    }
