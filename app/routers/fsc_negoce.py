"""MySifa — négoce de produit fini certifié FSC (régimes A1 et A2).

SIFA achète du produit fini à des partenaires certifiés et le revend. Le
partenaire fournit toujours la matière : c'est du négoce en **système de
transfert**, pas de la sous-traitance au sens FSC-STD-40-004. Le claim entrant
ressort à l'identique, jamais modifié ni amélioré.

    A1 · transit   partenaire → stock SIFA → client
                   preuve = réception → lot → expédition
    A2 · direct    partenaire → client (rien ne passe chez SIFA)
                   preuve = lien BL partenaire ↔ départ client, et rien d'autre

Ce module fournit :
  - POST /api/fsc/receptions-pf        réception A1, crée le lot certifié
  - GET  /api/fsc/receptions-pf        historique des réceptions
  - PUT  /api/fsc/departs/{id}/negoce  rattache un départ A2 à son BL partenaire
  - GET  /api/fsc/controles            les écarts qu'un audit relèverait

Le contrôle de certificat est délégué à app/services/fsc_certificat.py, qui
juge à la DATE DU BL et non à la date du jour.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request

from app.services.audit_service import log_action
from app.services.fsc_certificat import (
    certificats_a_renouveler,
    evaluer_certificat,
    fournisseurs_sans_date,
)
from config import (
    FSC_CLAIM_DEFAUT,
    FSC_CLAIM_LABELS,
    FSC_LICENCE_SIFA,
    ROLES_FSC_NEGOCE_WRITE,
    ROLES_TRACA_VIEWER,
)
from database import get_db
from services.auth_service import effective_role, get_current_user

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")

# Claims acceptés en ENTRÉE de négoce. `non_fsc` en fait partie : on achète
# aussi du produit non certifié, et le refuser obligerait à saisir ces
# réceptions ailleurs — donc à les perdre de vue.
_CLAIMS = tuple(FSC_CLAIM_LABELS.keys())


def _now() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).isoformat()


def _require_ecriture(request: Request) -> dict:
    """Saisie d'une réception ou d'un rattachement de vente.

    `effective_role` et non `role` : un superadmin qui simule un opérateur doit
    se voir refuser ce que l'opérateur ne peut pas faire, sans quoi le test
    d'habilitation par impersonation ne prouve rien.
    """
    user = get_current_user(request)
    if effective_role(user) not in ROLES_FSC_NEGOCE_WRITE:
        raise HTTPException(403, "Accès négoce FSC non autorisé.")
    return user


def _require_lecture(request: Request) -> dict:
    """Consultation des contrôles — même périmètre que le traceur."""
    user = get_current_user(request)
    if effective_role(user) not in ROLES_TRACA_VIEWER:
        raise HTTPException(403, "Accès aux contrôles FSC non autorisé.")
    return user


def _claim(valeur: Any, defaut: str = "non_fsc") -> str:
    c = (str(valeur or "").strip() or defaut)
    if c not in _CLAIMS:
        raise HTTPException(
            400, f"Claim FSC inconnu : {c}. Valeurs : {', '.join(_CLAIMS)}."
        )
    return c


def _fournisseur(conn, fournisseur_id: int) -> dict:
    row = conn.execute(
        """SELECT id, nom, licence, certificat, COALESCE(has_fsc,1) AS has_fsc,
                  fsc_date_expiration
             FROM fournisseurs_fsc WHERE id=?""",
        (fournisseur_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Fournisseur introuvable.")
    return dict(row)


# ══════════════════════════════════════════════════════════════════
# A1 — réception de produit fini certifié
# ══════════════════════════════════════════════════════════════════


@router.post("/api/fsc/receptions-pf")
async def creer_reception_pf(request: Request):
    """Réception A1 : le produit fini entre en stock avec son claim.

    Crée une ligne `pf_receptions`, une ligne `pf_reception_items` par produit,
    et le `lots_stock` correspondant porteur du claim. Le lot est marqué
    `fsc=1` dès que le claim entrant n'est pas `non_fsc` — c'est ce marquage
    qui alimente ensuite la ségrégation en stock et le FIFO par segment.

    Le verdict de validité du certificat est FIGÉ ici, à la date du BL. Le
    renouvellement ou l'expiration ultérieurs du certificat ne doivent pas
    réécrire l'histoire de cette livraison.
    """
    user = _require_ecriture(request)
    body = await request.json()

    try:
        fournisseur_id = int(body.get("fournisseur_id") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "fournisseur_id invalide.")
    if not fournisseur_id:
        raise HTTPException(400, "fournisseur_id obligatoire.")

    date_reception = (body.get("date_reception") or "").strip()
    if not date_reception:
        raise HTTPException(400, "date_reception obligatoire (date du BL).")
    bon_livraison = (body.get("bon_livraison") or "").strip() or None
    claim = _claim(body.get("fsc_type_claim"))
    note = (body.get("note") or "").strip() or None

    lignes = body.get("lignes") or []
    if not isinstance(lignes, list) or not lignes:
        raise HTTPException(400, "Au moins une ligne de réception est requise.")

    # Le claim doit figurer sur le document du fournisseur : sans BL, il n'y a
    # rien à opposer à un auditeur. On l'exige dès qu'un claim est revendiqué.
    if claim != "non_fsc" and not bon_livraison:
        raise HTTPException(
            400,
            "Le n° de BL fournisseur est obligatoire pour une réception certifiée : "
            "c'est lui qui porte le claim.",
        )

    with get_db() as conn:
        fourn = _fournisseur(conn, fournisseur_id)

        # Contrôle du certificat À LA DATE DU BL.
        verdict = evaluer_certificat(fourn, date_reception)
        if claim != "non_fsc" and verdict["bloquant"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "certificat_invalide",
                    "statut": verdict["statut"],
                    "message": (
                        f"{fourn['nom']} — {verdict['libelle']}"
                        + (f" (expiré le {verdict['expiration']})" if verdict["expiration"] else "")
                        + ". Une réception certifiée ne peut pas être adossée à ce certificat."
                    ),
                    "expiration": verdict["expiration"],
                },
            )

        now = _now()
        lot_numero = (body.get("lot_numero") or "").strip() or (
            "PF-" + datetime.now(_PARIS).strftime("%Y%m%d-%H%M")
        )
        cur = conn.execute(
            """INSERT INTO pf_receptions
                 (lot_numero, fournisseur_id, date_reception, bon_livraison,
                  certificat_fsc, fsc_type_claim, note, created_at, created_by,
                  created_by_name, licence_fournisseur, certificat_valide,
                  certificat_expiration, certificat_note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lot_numero, fournisseur_id, date_reception, bon_livraison,
                fourn.get("certificat"), claim, note, now, user.get("email"),
                (user.get("nom") or "").strip() or None,
                fourn.get("licence"),
                1 if verdict["statut"] == "valide" else 0,
                verdict["expiration"],
                verdict["libelle"],
            ),
        )
        reception_id = cur.lastrowid

        # Un lot certifié doit être identifiable en stock : c'est ce marquage
        # qui rend la ségrégation possible, pas l'emplacement.
        lot_fsc = 1 if claim != "non_fsc" else 0
        creees = []
        for i, ligne in enumerate(lignes, 1):
            if not isinstance(ligne, dict):
                raise HTTPException(400, f"Ligne {i} invalide.")
            try:
                produit_id = int(ligne.get("produit_id") or 0)
                quantite = float(ligne.get("quantite") or 0)
            except (TypeError, ValueError):
                raise HTTPException(400, f"Ligne {i} : produit_id et quantite numériques requis.")
            emplacement = (ligne.get("emplacement") or "").strip().upper()
            if not produit_id or quantite <= 0 or not emplacement:
                raise HTTPException(
                    400, f"Ligne {i} : produit_id, quantite > 0 et emplacement requis."
                )
            prod = conn.execute(
                "SELECT id, reference, unite FROM produits WHERE id=?", (produit_id,)
            ).fetchone()
            if not prod:
                raise HTTPException(404, f"Ligne {i} : produit {produit_id} introuvable.")

            lot = conn.execute(
                """INSERT INTO lots_stock
                     (produit_id, emplacement, quantite_initiale, quantite_restante,
                      date_entree, note, created_by, created_at, fsc, no_dossier, fsc_ecart)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
                (
                    produit_id, emplacement, quantite, quantite, date_reception,
                    f"Négoce {fourn['nom']}"
                    + (f" · BL {bon_livraison}" if bon_livraison else ""),
                    user.get("email"), now, lot_fsc, None,
                ),
            )
            lot_id = lot.lastrowid

            item = conn.execute(
                """INSERT INTO pf_reception_items
                     (reception_id, produit_id, quantite, unite, emplacement,
                      lot_fournisseur, dluo, lot_stock_id, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    reception_id, produit_id, quantite,
                    (ligne.get("unite") or prod["unite"] or None),
                    emplacement,
                    (ligne.get("lot_fournisseur") or "").strip() or None,
                    (ligne.get("dluo") or "").strip() or None,
                    lot_id, now,
                ),
            )

            # Lien retour lot → réception. Sans lui, un lot FSC acheté serait
            # indiscernable d'un lot FSC sans origine : le contrôle
            # « lots_fsc_sans_origine » le signalerait à tort, et le traceur
            # afficherait « aucune bobine tracée » au lieu de nommer le
            # partenaire chez qui le produit a été acheté certifié.
            conn.execute(
                "UPDATE lots_stock SET pf_reception_item_id=? WHERE id=?",
                (item.lastrowid, lot_id),
            )

            # Agrégat par emplacement, aligné sur ce que fait MyStock.
            ex = conn.execute(
                "SELECT quantite FROM stock_emplacements WHERE produit_id=? AND emplacement=?",
                (produit_id, emplacement),
            ).fetchone()
            if ex:
                conn.execute(
                    """UPDATE stock_emplacements SET quantite=?, updated_at=?, updated_by=?
                        WHERE produit_id=? AND emplacement=?""",
                    (float(ex["quantite"] or 0) + quantite, now, user.get("email"),
                     produit_id, emplacement),
                )
                qte_avant = float(ex["quantite"] or 0)
            else:
                conn.execute(
                    """INSERT INTO stock_emplacements
                         (produit_id, emplacement, quantite, updated_at, updated_by)
                       VALUES (?,?,?,?,?)""",
                    (produit_id, emplacement, quantite, now, user.get("email")),
                )
                qte_avant = 0.0

            conn.execute(
                """INSERT INTO mouvements_stock
                     (produit_id, emplacement, type_mouvement, quantite, quantite_avant,
                      quantite_apres, note, created_at, created_by, created_by_name,
                      fsc, lot_id)
                   VALUES (?,?,'entree',?,?,?,?,?,?,?,?,?)""",
                (
                    produit_id, emplacement, quantite, qte_avant, qte_avant + quantite,
                    f"Réception négoce {fourn['nom']}", now, user.get("email"),
                    (user.get("nom") or "").strip() or None, lot_fsc, lot_id,
                ),
            )
            creees.append({"produit_id": produit_id, "reference": prod["reference"],
                           "lot_id": lot_id, "quantite": quantite})

        conn.commit()

    log_action(
        user=user, action="CREATE", module="stock",
        objet=f"Réception négoce PF {lot_numero} · {fourn['nom']} · {claim}",
        detail={"reception_id": reception_id, "claim": claim,
                "certificat": verdict["statut"], "lignes": len(creees)},
        ip=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "reception_id": reception_id,
        "lot_numero": lot_numero,
        "certificat": verdict,
        "lignes": creees,
    }


@router.get("/api/fsc/receptions-pf")
def lister_receptions_pf(request: Request, limit: int = 50):
    """Historique des réceptions de produit fini certifié."""
    _require_ecriture(request)
    limit = max(1, min(500, int(limit or 50)))
    with get_db() as conn:
        rows = conn.execute(
            """SELECT r.*, f.nom AS fournisseur_nom,
                      (SELECT COUNT(*) FROM pf_reception_items i
                        WHERE i.reception_id = r.id) AS nb_lignes,
                      (SELECT COALESCE(SUM(i.quantite),0) FROM pf_reception_items i
                        WHERE i.reception_id = r.id) AS quantite_totale
                 FROM pf_receptions r
                 LEFT JOIN fournisseurs_fsc f ON f.id = r.fournisseur_id
                ORDER BY r.date_reception DESC, r.id DESC
                LIMIT ?""",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["fsc_claim_label"] = FSC_CLAIM_LABELS.get(d.get("fsc_type_claim") or "non_fsc",
                                                    d.get("fsc_type_claim"))
        out.append(d)
    return {"receptions": out, "nb": len(out)}


# ══════════════════════════════════════════════════════════════════
# A2 — vente sans transit
# ══════════════════════════════════════════════════════════════════


@router.put("/api/fsc/departs/{depart_id}/negoce")
async def rattacher_depart_negoce(depart_id: int, request: Request):
    """Rattache un départ au BL du partenaire qui a livré directement.

    En A2, ce lien est la SEULE preuve du claim facturé au client : aucun lot,
    aucun mouvement de stock n'existe. Sans lui, la vente est indémontrable.

    Le claim sortant doit être identique au claim entrant (système de
    transfert). On refuse une « montée en grade » — vendre du FSC Mix acheté
    comme du FSC 100% — parce que c'est la non-conformité la plus grave et la
    plus facile à commettre par simple erreur de saisie.
    """
    user = _require_ecriture(request)
    body = await request.json()

    with get_db() as conn:
        dep = conn.execute("SELECT * FROM expe_departs WHERE id=?", (depart_id,)).fetchone()
        if not dep:
            raise HTTPException(404, "Départ introuvable.")
        d = dict(dep)

        fournisseur_id = body.get("fsc_fournisseur_id")
        if fournisseur_id in (None, "", 0):
            # Détachement : on remet tout à zéro plutôt que de laisser des
            # miettes qui feraient croire à un rattachement partiel.
            conn.execute(
                """UPDATE expe_departs SET fsc_fournisseur_id=NULL, fsc_bl_fournisseur=NULL,
                       fsc_claim_entrant=NULL, fsc_claim_sortant=NULL, fsc_sans_transit=0
                    WHERE id=?""",
                (depart_id,),
            )
            conn.commit()
            log_action(user=user, action="UPDATE", module="expe",
                       objet=f"Départ #{depart_id} — rattachement négoce FSC retiré",
                       ip=request.client.host if request.client else None)
            return {"success": True, "detache": True}

        try:
            fournisseur_id = int(fournisseur_id)
        except (TypeError, ValueError):
            raise HTTPException(400, "fsc_fournisseur_id invalide.")
        fourn = _fournisseur(conn, fournisseur_id)

        bl = (body.get("fsc_bl_fournisseur") or "").strip() or None
        claim_entrant = _claim(body.get("fsc_claim_entrant"))
        claim_sortant = _claim(body.get("fsc_claim_sortant"), claim_entrant)
        sans_transit = 1 if bool(body.get("fsc_sans_transit", True)) else 0

        if claim_entrant != "non_fsc" and not bl:
            raise HTTPException(
                400,
                "Le n° de BL du partenaire est obligatoire : en livraison directe, "
                "c'est la seule preuve du claim facturé au client.",
            )

        if claim_sortant != claim_entrant:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Système de transfert : le claim sortant doit être identique à "
                    f"l'entrant. Reçu « {FSC_CLAIM_LABELS.get(claim_entrant, claim_entrant)} », "
                    f"vendu « {FSC_CLAIM_LABELS.get(claim_sortant, claim_sortant)} » — "
                    f"un claim ne peut jamais être amélioré au passage."
                ),
            )

        # Validité du certificat à la date d'enlèvement, faute de mieux : c'est
        # la date connue la plus proche de celle du BL partenaire.
        date_ref = (body.get("date_bl") or d.get("date_enlevement") or "").strip() or None
        verdict = evaluer_certificat(fourn, date_ref)
        if claim_entrant != "non_fsc" and verdict["bloquant"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "certificat_invalide",
                    "statut": verdict["statut"],
                    "message": f"{fourn['nom']} — {verdict['libelle']}.",
                    "expiration": verdict["expiration"],
                },
            )

        conn.execute(
            """UPDATE expe_departs
                  SET fsc_fournisseur_id=?, fsc_bl_fournisseur=?, fsc_claim_entrant=?,
                      fsc_claim_sortant=?, fsc_sans_transit=?
                WHERE id=?""",
            (fournisseur_id, bl, claim_entrant, claim_sortant, sans_transit, depart_id),
        )
        conn.commit()

    log_action(
        user=user, action="UPDATE", module="expe",
        objet=f"Départ #{depart_id} — négoce FSC {fourn['nom']} · {claim_sortant}",
        detail={"bl_fournisseur": bl, "claim": claim_sortant,
                "sans_transit": bool(sans_transit), "certificat": verdict["statut"]},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "certificat": verdict}


# ══════════════════════════════════════════════════════════════════
# Mention à porter sur le document de vente
# ══════════════════════════════════════════════════════════════════


@router.get("/api/fsc/departs/{depart_id}/mention")
def mention_document_vente(depart_id: int, request: Request):
    """Texte exact à recopier sur la facture / le BL client.

    Un claim n'existe pour l'auditeur que s'il est ÉCRIT sur le document de
    vente, avec le code de licence du vendeur et le type de claim. MySifa
    n'édite pas les factures : il donne donc la mention à porter, et dit
    clairement quand il manque de quoi la construire plutôt que d'en produire
    une approximative.
    """
    _require_ecriture(request)

    with get_db() as conn:
        dep = conn.execute("SELECT * FROM expe_departs WHERE id=?", (depart_id,)).fetchone()
        if not dep:
            raise HTTPException(404, "Départ introuvable.")
        d = dict(dep)

        sans_transit = int(d.get("fsc_sans_transit") or 0) == 1
        claim = (d.get("fsc_claim_sortant") or "").strip()
        source = "negoce_direct" if sans_transit else None

        # Régime A1 / fabrication : le claim vient du dossier rattaché.
        #
        # Deux façons d'atteindre ce dossier. `planning_entry_id` est une clé
        # étrangère : elle désigne UNE ligne, sans ambiguïté. `no_dossier` est
        # une référence textuelle : deux dossiers peuvent la partager, d'où le
        # `ORDER BY id DESC LIMIT 1` qui suit — un pis-aller. On privilégie
        # donc la clé, et on ne retombe sur le texte que faute de mieux.
        if not claim:
            row = None
            pe_id = d.get("planning_entry_id")
            if pe_id:
                row = conn.execute(
                    """SELECT COALESCE(fsc_requis,0) AS fsc_requis,
                              COALESCE(fsc_type_requis,'') AS fsc_type_requis
                         FROM planning_entries WHERE id=?""",
                    (pe_id,),
                ).fetchone()
            if row is None:
                ref = (d.get("no_dossier") or "").strip()
                if ref:
                    row = conn.execute(
                        """SELECT COALESCE(fsc_requis,0) AS fsc_requis,
                                  COALESCE(fsc_type_requis,'') AS fsc_type_requis
                             FROM planning_entries
                            WHERE TRIM(COALESCE(reference,''))=? OR TRIM(COALESCE(numero_of,''))=?
                            ORDER BY id DESC LIMIT 1""",
                        (ref, ref),
                    ).fetchone()
            if row and int(row["fsc_requis"] or 0) == 1:
                claim = (row["fsc_type_requis"] or FSC_CLAIM_DEFAUT).strip()
                source = "dossier"

    claim = claim or "non_fsc"
    manques: list[str] = []
    if claim == "non_fsc":
        return {
            "depart_id": depart_id,
            "claim": "non_fsc",
            "mention": None,
            "source": source,
            "manques": [],
            "commentaire": "Vente non certifiée : aucune mention FSC ne doit figurer "
                           "sur le document. Porter un claim ici serait une non-conformité.",
        }

    if not FSC_LICENCE_SIFA:
        manques.append(
            "Code de licence FSC de SIFA non renseigné (variable d'environnement "
            "FSC_LICENCE_SIFA). Sans lui, la mention est incomplète et le claim "
            "inopposable."
        )
    if sans_transit and not (d.get("fsc_bl_fournisseur") or "").strip():
        manques.append(
            "Livraison directe sans BL partenaire enregistré : le claim vendu ne "
            "repose sur aucun document entrant."
        )

    libelle = FSC_CLAIM_LABELS.get(claim, claim)
    mention = f"{FSC_LICENCE_SIFA or '«licence FSC SIFA à renseigner»'} — {libelle}"

    return {
        "depart_id": depart_id,
        "claim": claim,
        "claim_label": libelle,
        "licence_sifa": FSC_LICENCE_SIFA or None,
        "mention": mention,
        "source": source,
        "bl_fournisseur": (d.get("fsc_bl_fournisseur") or "").strip() or None,
        "manques": manques,
        "commentaire": "À porter sur la facture ET sur le bon de livraison, "
                       "au niveau de la ligne concernée si la vente est mixte.",
    }


# ══════════════════════════════════════════════════════════════════
# Contrôles — ce qu'un audit relèverait
# ══════════════════════════════════════════════════════════════════


@router.get("/api/fsc/controles")
def controles_fsc(request: Request, jours: int = 60):
    """Écarts détectables automatiquement, regroupés par nature.

    L'objet n'est pas de tout signaler, mais de signaler ce qui casserait un
    claim si un auditeur tirait le fil aujourd'hui.
    """
    _require_lecture(request)
    jours = max(0, min(365, int(jours or 60)))

    with get_db() as conn:
        certifs = certificats_a_renouveler(conn, jours)
        sans_date = fournisseurs_sans_date(conn)

        # Départs livrés directement sans BL partenaire : le claim facturé
        # n'est adossé à rien.
        try:
            directs_orphelins = [
                dict(r)
                for r in conn.execute(
                    """SELECT id, no_bl, client, date_enlevement, fsc_claim_sortant
                         FROM expe_departs
                        WHERE COALESCE(fsc_sans_transit,0) = 1
                          AND TRIM(COALESCE(fsc_bl_fournisseur,'')) = ''
                        ORDER BY date_enlevement DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            directs_orphelins = []

        # Réceptions certifiées adossées à un certificat non valide au moment
        # du BL. Le verdict a été figé à la réception : on le relit tel quel.
        try:
            recep_douteuses = [
                dict(r)
                for r in conn.execute(
                    """SELECT r.id, r.lot_numero, r.date_reception, r.bon_livraison,
                              r.fsc_type_claim, r.certificat_note, f.nom AS fournisseur_nom
                         FROM pf_receptions r
                         LEFT JOIN fournisseurs_fsc f ON f.id = r.fournisseur_id
                        WHERE COALESCE(r.fsc_type_claim,'non_fsc') <> 'non_fsc'
                          AND COALESCE(r.certificat_valide,0) = 0
                        ORDER BY r.date_reception DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            recep_douteuses = []

        # Lots FSC sans origine : ni dossier de fabrication, ni réception de
        # négoce. On ne sait pas d'où vient le claim.
        try:
            lots_orphelins = [
                dict(r)
                for r in conn.execute(
                    """SELECT l.id, l.emplacement, l.quantite_restante, l.date_entree,
                              p.reference
                         FROM lots_stock l
                         JOIN produits p ON p.id = l.produit_id
                        WHERE COALESCE(l.fsc,0) = 1
                          AND l.quantite_restante > 0
                          AND TRIM(COALESCE(l.no_dossier,'')) = ''
                          AND l.pf_reception_item_id IS NULL
                        ORDER BY l.date_entree DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            lots_orphelins = []

        # Numéros de BL portés par plusieurs départs. Premier maillon d'un
        # audit : l'auditeur présente un document, deux lignes répondent, et
        # rien ne dit laquelle est la bonne.
        try:
            bl_doublons = [
                dict(r)
                for r in conn.execute(
                    """SELECT UPPER(REPLACE(REPLACE(REPLACE(TRIM(no_bl),' ',''),'-',''),'.','')) AS cle,
                              COUNT(*) AS nb,
                              GROUP_CONCAT(id) AS depart_ids,
                              GROUP_CONCAT(DISTINCT client) AS clients
                         FROM expe_departs
                        WHERE TRIM(COALESCE(no_bl,'')) <> ''
                        GROUP BY cle
                       HAVING COUNT(*) > 1
                        ORDER BY nb DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            bl_doublons = []

        # Codes-barres présents dans plusieurs réceptions : l'origine
        # fournisseur de ces bobines n'est pas décidable.
        try:
            codes_ambigus = [
                dict(r)
                for r in conn.execute(
                    """SELECT TRIM(i.code_barre) AS code_barre,
                              COUNT(DISTINCT i.reception_id) AS nb_receptions,
                              GROUP_CONCAT(DISTINCT r.fournisseur) AS fournisseurs
                         FROM stock_reception_items i
                         JOIN stock_receptions r ON r.id = i.reception_id
                        WHERE TRIM(COALESCE(i.code_barre,'')) <> ''
                        GROUP BY TRIM(i.code_barre)
                       HAVING COUNT(DISTINCT i.reception_id) > 1
                        ORDER BY nb_receptions DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            codes_ambigus = []

        # Réceptions de matière dont le fournisseur n'est pas dans l'annuaire
        # FSC : ni licence ni certificat opposables.
        try:
            recep_sans_fournisseur = [
                dict(r)
                for r in conn.execute(
                    """SELECT id, lot_numero, created_at, fournisseur, fsc_type_claim,
                              nb_bobines
                         FROM stock_receptions
                        WHERE fournisseur_id IS NULL
                          AND TRIM(COALESCE(fournisseur,'')) <> ''
                        ORDER BY created_at DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            recep_sans_fournisseur = []

        # LE compteur à faire descendre. Un départ ni rattaché ni déclaré est
        # une expédition dont personne ne peut dire si elle aurait dû remonter
        # à un dossier. C'est le seul de ces contrôles qui se répare par
        # l'usage et non par du code.
        try:
            r = conn.execute(
                """SELECT COUNT(*) AS n,
                          SUM(CASE WHEN date_enlevement >= date('now','-90 days')
                                   THEN 1 ELSE 0 END) AS n_90j
                     FROM expe_departs
                    WHERE TRIM(COALESCE(no_dossier,'')) = ''
                      AND planning_entry_id IS NULL
                      AND COALESCE(sans_dossier,0) = 0"""
            ).fetchone()
            departs_muets = {"total": int(r["n"] or 0), "derniers_90j": int(r["n_90j"] or 0)}
            departs_muets_recents = [
                dict(x)
                for x in conn.execute(
                    """SELECT id, no_bl, client, date_enlevement, arc, ref_sifa
                         FROM expe_departs
                        WHERE TRIM(COALESCE(no_dossier,'')) = ''
                          AND planning_entry_id IS NULL
                          AND COALESCE(sans_dossier,0) = 0
                        ORDER BY date_enlevement DESC LIMIT 200"""
                ).fetchall()
            ]
        except Exception:
            departs_muets = {"total": 0, "derniers_90j": 0}
            departs_muets_recents = []

    return {
        "certificats_a_renouveler": certifs,
        "fournisseurs_sans_date_certificat": sans_date,
        "departs_directs_sans_bl": directs_orphelins,
        "receptions_certificat_invalide": recep_douteuses,
        "lots_fsc_sans_origine": lots_orphelins,
        "bl_doublons": bl_doublons,
        "codes_barres_ambigus": codes_ambigus,
        "receptions_fournisseur_hors_annuaire": recep_sans_fournisseur,
        "departs_sans_rattachement_ni_motif": departs_muets_recents,
        "synthese": {
            "nb_certificats_a_renouveler": len(certifs),
            "nb_expires": sum(1 for c in certifs if c["expire"]),
            "nb_sans_date": len(sans_date),
            "nb_departs_directs_sans_bl": len(directs_orphelins),
            "nb_receptions_douteuses": len(recep_douteuses),
            "nb_lots_sans_origine": len(lots_orphelins),
            "nb_bl_doublons": len(bl_doublons),
            "nb_codes_barres_ambigus": len(codes_ambigus),
            "nb_receptions_fournisseur_hors_annuaire": len(recep_sans_fournisseur),
            "nb_departs_sans_rattachement_ni_motif": departs_muets["total"],
            "nb_departs_sans_rattachement_90j": departs_muets["derniers_90j"],
            "genere_a": _now(),
        },
    }
