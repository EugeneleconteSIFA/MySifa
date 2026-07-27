"""MyAO — Calculs de prix pour les demandes de prix fournisseurs."""
from __future__ import annotations

from typing import Any

DEVISES = frozenset({"EUR", "USD"})
UNITES_QUOTATION = frozenset({"mille", "bobine"})
# Unités de vente possibles (définies dans la fiche produit). "mille" = au
# mille d'étiquettes (défaut historique). Les autres dépendent du
# conditionnement renseigné dans la fiche.
UNITES_VENTE = frozenset({"mille", "etiquette", "bobine", "carton", "palette"})
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


def _norm_unite_vente(value: str | None) -> str:
    u = (value or "mille").strip().lower()
    return u if u in UNITES_VENTE else "mille"


def etiquettes_par_unite_vente(
    unite_type: str | None,
    unite_qte: Any,
    nb_etiquettes_bobine: float | None,
    bobines_carton: float | None,
    cartons_palette: float | None,
) -> float | None:
    """Nombre d'étiquettes contenues dans 1 unité de vente.

    Ex. « par carton » avec 2000 étiq/bobine et 8 bobines/carton → 16 000.
    « par 100 bobines » (type=bobine, qté=100) → 100 × nb étiq/bobine.
    Retourne None si une donnée de conditionnement nécessaire manque dans la
    fiche (le tableau affiche alors « Compléter fiche »).
    """
    t = _norm_unite_vente(unite_type)
    q = _float_or_none(unite_qte)
    if q is None or q <= 0:
        q = 1.0
    nb_bob = _float_or_none(nb_etiquettes_bobine)
    bc = _float_or_none(bobines_carton)
    cp = _float_or_none(cartons_palette)
    if t == "etiquette":
        base: float | None = 1.0
    elif t == "mille":
        base = 1000.0
    elif t == "bobine":
        base = nb_bob
    elif t == "carton":
        base = (nb_bob * bc) if (nb_bob and bc) else None
    elif t == "palette":
        base = (nb_bob * bc * cp) if (nb_bob and bc and cp) else None
    else:
        base = None
    if base is None:
        return None
    return base * q


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

    # Deux unités :
    #  - unite_original : ce que le fournisseur a réellement saisi (base du prix_calculé
    #    qu'il facturera). Ne change jamais après ré-interprétation manuelle.
    #  - unite_display : ce que l'interne a corrigé si erreur de saisie fournisseur
    #    (ex. il a coché « bobine » mais voulait dire « mille »). Sert de référence
    #    pour prix_au_mille et prix_vente (notre logique interne).
    unite_display = _norm_unite(reponse.get("unite_quotation"))
    unite_original = _norm_unite(reponse.get("unite_quotation_original") or unite_display)
    devise = _norm_devise(reponse.get("devise"))
    devise_devis = _norm_devise(reponse.get("devise_prix_devis"))
    coef = _float_or_none(reponse.get("coef"))
    if coef is None or coef <= 0:
        coef = 1.0

    nb_bob = ligne_ctx.get("etiquettes_par_bobine")
    qte = ligne_ctx.get("quantite_etiquettes")

    # prix_calcule : basé sur l'unité ORIGINALE (facturation réelle fournisseur)
    prix_calcule = calc_prix_calcule(quotation, unite_original, qte, nb_bob)
    # prix_au_mille : basé sur l'unité AFFICHÉE (celle qu'on considère être la vraie)
    prix_au_mille = calc_prix_au_mille(quotation, unite_display, nb_bob)
    transport_amount = calc_transport_amount(prix_calcule, transport_pct)
    prix_vente = calc_prix_vente(
        prix_au_mille, devise, coef, devise_devis, eur_usd_rate, transport_pct
    )

    out = dict(reponse)
    out["quotation"] = quotation
    out["devise"] = devise
    out["unite_quotation"] = unite_display
    out["coef"] = coef
    out["devise_prix_devis"] = devise_devis
    out["prix_au_mille"] = prix_au_mille
    out["prix_calcule"] = prix_calcule
    out["transport_amount"] = transport_amount
    # Prix d'achat au mille (devise fournisseur, transport inclus, sans coef).
    # Sert de base pour calculer le prix de vente à la condi côté frontend.
    if prix_au_mille is not None:
        out["prix_achat_mille"] = prix_au_mille * (1.0 + _clean_transport_pct(transport_pct) / 100.0)
    else:
        out["prix_achat_mille"] = None
    out["prix_vente"] = prix_vente

    # ── Nouveau pipeline conditionnement (v217) ─────────────────────────────
    # Marge commerciale : 2e multiplicateur, distinct du coef.
    marge = _float_or_none(reponse.get("marge"))
    if marge is None or marge <= 0:
        marge = 1.0
    out["marge"] = marge

    # Prix d'achat au mille exprimé dans la DEVISE DEVIS (demande #2 : la
    # conversion de devise se fait au prix d'achat, pas au prix de vente).
    # Transport inclus, sans coef ni marge.
    if out["prix_achat_mille"] is not None:
        prix_achat_mille_dd = convert_amount(
            out["prix_achat_mille"], devise, devise_devis, eur_usd_rate
        )
    else:
        prix_achat_mille_dd = None
    out["prix_achat_mille_dd"] = prix_achat_mille_dd

    # Unité de vente : vient de la fiche produit (lecture seule côté tableau).
    uv_type = _norm_unite_vente(ligne_ctx.get("unite_vente_type"))
    uv_qte = _float_or_none(ligne_ctx.get("unite_vente_qte")) or 1.0
    etiq_par_condi = etiquettes_par_unite_vente(
        uv_type, uv_qte,
        ligne_ctx.get("etiquettes_par_bobine"),
        ligne_ctx.get("bobines_carton"),
        ligne_ctx.get("cartons_palette"),
    )
    out["unite_vente_type"] = uv_type
    out["unite_vente_qte"] = uv_qte
    out["etiq_par_condi"] = etiq_par_condi

    # Prix d'achat conditionné = prix d'achat au mille (devise devis) ramené à
    # l'unité de vente. Ex. au mille (1000 étiq) → identique au prix au mille.
    if prix_achat_mille_dd is not None and etiq_par_condi:
        prix_achat_conditionne = prix_achat_mille_dd * etiq_par_condi / 1000.0
    else:
        prix_achat_conditionne = None
    out["prix_achat_conditionne"] = prix_achat_conditionne

    # Prix de vente final = prix d'achat conditionné × coef × marge.
    # (Choix produit : coef conserve son rôle, marge s'ajoute en cascade.)
    if prix_achat_conditionne is not None:
        out["prix_vente_final"] = prix_achat_conditionne * coef * marge
    else:
        out["prix_vente_final"] = None

    # ── Marge brute vs dernier prix de vente (fiche produit) ────────────────
    # dernier_prix_vente est saisi PAR UNITÉ DE VENTE (même base que le prix
    # d'achat conditionné) → comparaison directe.
    # Taux de marque = (PV−PA)/PV (marge rapportée au prix de VENTE).
    out["has_produit"] = bool(ligne_ctx.get("has_produit"))
    dpv = _float_or_none(ligne_ctx.get("dernier_prix_vente"))
    out["dernier_prix_vente"] = dpv
    if dpv is not None and dpv > 0 and prix_achat_conditionne is not None:
        out["marge_brute_pct"] = (dpv - prix_achat_conditionne) / dpv * 100.0
    else:
        out["marge_brute_pct"] = None

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
    unite_vente_type = "mille"
    unite_vente_qte = 1.0
    dernier_prix_vente = None

    if produit:
        client_nom = produit.get("client_nom")
        fiche = produit.get("fiche") or {}
        mat = fiche.get("matiere") or {}
        bob = fiche.get("bobines") or {}
        uv = fiche.get("unite_vente") or {}
        unite_vente_type = _norm_unite_vente(uv.get("type"))
        unite_vente_qte = _float_or_none(uv.get("quantite")) or 1.0
        dernier_prix_vente = _float_or_none(fiche.get("dernier_prix_vente"))

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
        cond = fiche.get("conditionnement") or {}
        cart = cond.get("carton") or {}
        pal = cond.get("palette") or {}
        bobines_carton = _float_or_none(cart.get("bobines_carton"))
        cartons_palette = _float_or_none(pal.get("cartons_palette"))
    else:
        bobines_carton = None
        cartons_palette = None

    qte = _float_or_none(quantite)

    return {
        "ref_produit": ref_produit,
        "client_nom": client_nom,
        "frontal": frontal,
        "adhesif": adhesif,
        "etiquettes_par_bobine": etiquettes_par_bobine,
        "bobines_carton": bobines_carton,
        "cartons_palette": cartons_palette,
        "unite_vente_type": unite_vente_type,
        "unite_vente_qte": unite_vente_qte,
        "dernier_prix_vente": dernier_prix_vente,
        "has_produit": produit is not None,
        "quantite_etiquettes": qte,
    }
