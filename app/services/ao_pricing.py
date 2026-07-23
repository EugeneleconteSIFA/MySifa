"""MyAO — Calculs de prix pour les demandes de prix fournisseurs."""
from __future__ import annotations

from typing import Any

DEVISES = frozenset({"EUR", "USD"})
UNITES_QUOTATION = frozenset({"mille", "bobine"})
_DEFAULT_EUR_USD = 0.92


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _norm_devise(value: str | None) -> str:
    d = (value or "EUR").strip().upper()
    return d if d in DEVISES else "EUR"


def _norm_unite(value: str | None) -> str:
    u = (value or "mille").strip().lower()
    return u if u in UNITES_QUOTATION else "mille"


def get_eur_usd_rate(conn) -> float:
    row = conn.execute(
        "SELECT value_decimal FROM mc_setting WHERE key='eur_usd_rate' LIMIT 1"
    ).fetchone()
    if row and row["value_decimal"] is not None:
        try:
            rate = float(row["value_decimal"])
            if rate > 0:
                return rate
        except (TypeError, ValueError):
            pass
    return _DEFAULT_EUR_USD


def convert_amount(
    amount: float,
    from_devise: str,
    to_devise: str,
    eur_usd_rate: float,
) -> float:
    """Convertit un montant entre EUR et USD (via EUR)."""
    src = _norm_devise(from_devise)
    dst = _norm_devise(to_devise)
    if src == dst:
        return amount
    if src == "USD" and dst == "EUR":
        return amount * eur_usd_rate
    if src == "EUR" and dst == "USD" and eur_usd_rate > 0:
        return amount / eur_usd_rate
    return amount


def calc_prix_au_mille(
    quotation: float | None,
    unite_quotation: str | None,
    nb_etiquettes_bobine: float | None,
) -> float | None:
    if quotation is None:
        return None
    unite = _norm_unite(unite_quotation)
    if unite == "mille":
        return quotation
    nb = _float_or_none(nb_etiquettes_bobine)
    if not nb or nb <= 0:
        return None
    return (quotation / nb) * 1000.0


def calc_prix_calcule(
    quotation: float | None,
    unite_quotation: str | None,
    quantite_etiquettes: float | None,
    nb_etiquettes_bobine: float | None,
) -> float | None:
    """Prix total pour la quantité d'étiquettes de la ligne."""
    if quotation is None:
        return None
    qte = _float_or_none(quantite_etiquettes)
    if not qte or qte <= 0:
        return None
    unite = _norm_unite(unite_quotation)
    if unite == "mille":
        return quotation * (qte / 1000.0)
    nb = _float_or_none(nb_etiquettes_bobine)
    if not nb or nb <= 0:
        return None
    return quotation * (qte / nb)


def _clean_transport_pct(transport_pct: float | None) -> float:
    try:
        pct = float(transport_pct or 0)
    except (TypeError, ValueError):
        pct = 0.0
    return pct if pct > 0 else 0.0


def calc_prix_vente(
    prix_au_mille: float | None,
    devise_fournisseur: str | None,
    coef: float | None,
    devise_prix_devis: str | None,
    eur_usd_rate: float,
    transport_pct: float = 0.0,
) -> float | None:
    """Prix de vente au mille (devise devis).

    Pipeline : prix_au_mille → +transport (devise fournisseur) → ×coef → conversion devise.
    Le transport s'ajoute AVANT coef et AVANT conversion devise.
    """
    if prix_au_mille is None:
        return None
    c = _float_or_none(coef)
    if c is None or c <= 0:
        c = 1.0
    pct = _clean_transport_pct(transport_pct)
    # +transport en devise fournisseur, puis ×coef
    base_fournisseur = prix_au_mille * (1.0 + pct / 100.0) * c
    return convert_amount(
        base_fournisseur,
        _norm_devise(devise_fournisseur),
        _norm_devise(devise_prix_devis),
        eur_usd_rate,
    )


def calc_transport_amount(
    prix_calcule: float | None,
    transport_pct: float = 0.0,
) -> float | None:
    """Montant transport en devise fournisseur (pour affichage colonne dédiée)."""
    if prix_calcule is None:
        return None
    return prix_calcule * (_clean_transport_pct(transport_pct) / 100.0)


def enrich_reponse_pricing(
    reponse: dict[str, Any],
    ligne_ctx: dict[str, Any],
    *,
    eur_usd_rate: float,
    transport_pct: float = 0.0,
) -> dict[str, Any]:
    """Ajoute les champs calculés à une réponse fournisseur."""
    quotation = _float_or_none(reponse.get("quotation"))
    if quotation is None:
        quotation = _float_or_none(reponse.get("prix_unitaire"))

    # unite pour PRICING : toujours celle du fournisseur (unite_quotation_original)
    # unite pour AFFICHAGE (unite_quotation) peut etre override par l'interne (badge "manuel")
    unite_display = reponse.get("unite_quotation")
    unite = _norm_unite(reponse.get("unite_quotation_original") or unite_display)
    devise = _norm_devise(reponse.get("devise"))
    devise_devis = _norm_devise(reponse.get("devise_prix_devis"))
    coef = _float_or_none(reponse.get("coef"))
    if coef is None or coef <= 0:
        coef = 1.0

    nb_bob = ligne_ctx.get("etiquettes_par_bobine")
    qte = ligne_ctx.get("quantite_etiquettes")

    prix_au_mille = calc_prix_au_mille(quotation, unite, nb_bob)
    prix_calcule = calc_prix_calcule(quotation, unite, qte, nb_bob)
    transport_amount = calc_transport_amount(prix_calcule, transport_pct)
    prix_vente = calc_prix_vente(
        prix_au_mille, devise, coef, devise_devis, eur_usd_rate, transport_pct
    )

    out = dict(reponse)
    out["quotation"] = quotation
    out["devise"] = devise
    out["unite_quotation"] = _norm_unite(unite_display) if unite_display else unite
    out["coef"] = coef
    out["devise_prix_devis"] = devise_devis
    out["prix_au_mille"] = prix_au_mille
    out["prix_calcule"] = prix_calcule
    out["transport_amount"] = transport_amount
    out["prix_vente"] = prix_vente
    return out


def ligne_context_from_produit(
    ref_produit: str,
    quantite: float | None,
    produit: dict | None,
    matieres_map: dict[int, dict],
) -> dict[str, Any]:
    """Contexte produit pour une ligne AO (client, matières, bobines)."""
    client_nom = None
    frontal = None
    adhesif = None
    etiquettes_par_bobine = None

    if produit:
        client_nom = produit.get("client_nom")
        fiche = produit.get("fiche") or {}
        mat = fiche.get("matiere") or {}
        bob = fiche.get("bobines") or {}

        def mp_label(mid: Any) -> str | None:
            if mid is None:
                return None
            try:
                m = matieres_map.get(int(mid))
            except (TypeError, ValueError):
                return None
            if not m:
                return None
            ref = (m.get("reference") or "").strip()
            des = (m.get("designation") or "").strip()
            return f"{ref} — {des}".strip(" —") or None

        frontal = mp_label(mat.get("frontal_id"))
        adhesif = mp_label(mat.get("adhesif_id"))
        etiquettes_par_bobine = _float_or_none(bob.get("nb_etiquettes"))

    qte = _float_or_none(quantite)

    return {
        "ref_produit": ref_produit,
        "client_nom": client_nom,
        "frontal": frontal,
        "adhesif": adhesif,
        "etiquettes_par_bobine": etiquettes_par_bobine,
        "quantite_etiquettes": qte,
    }
