"""MyExpé — onglet Taxe carburant (API interne).

Monté sous `/api/expe`. La saisie côté transporteur passe par le portail
public (`app/routers/expe_portail.py`, route `/{token}/carburant`) ; ce
fichier ne sert que l'écran interne : la liste, l'historique d'un
transporteur, et l'envoi des demandes de mise à jour.
"""

from fastapi import APIRouter, Body, HTTPException, Request

from app.routers.expe_departs import _require_expe, _require_expe_write
from app.services import expe_carburant as carb
from app.services.audit_service import log_action
from app.services.email_service import send_email
from config import EXPE_DEVIS_FROM, public_base_url
from database import get_db

router = APIRouter()


@router.get("/carburant")
def liste_taxes(request: Request):
    _require_expe(request)
    with get_db() as conn:
        return {"transporteurs": carb.liste(conn)}


@router.get("/carburant/{transporteur_id}/historique")
def historique_taxe(request: Request, transporteur_id: int):
    _require_expe(request)
    with get_db() as conn:
        return {"historique": carb.historique(conn, transporteur_id)}


@router.post("/carburant/demander")
def demander_mise_a_jour(request: Request, body: dict = Body(...)):
    """Envoie à chaque transporteur choisi l'email qui ouvre son espace.

    L'expéditeur est la boîte du service, comme pour les demandes de tarif.
    Pas de copie au demandeur : sur un envoi à quinze transporteurs, quinze
    copies identiques n'apprennent rien — c'est la confirmation de saisie qui
    lui revient, transporteur par transporteur.
    """
    user = _require_expe_write(request)
    ids = []
    for x in body.get("transporteur_ids") or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    if not ids:
        raise HTTPException(status_code=400, detail="Aucun transporteur sélectionné.")

    auteur = (user.get("email") or user.get("identifiant") or "").strip() or None
    user_nom = user.get("nom") or auteur or ""
    reply_to = (EXPE_DEVIS_FROM or "").strip() or None

    envoyes: list[str] = []
    echecs: list[str] = []
    sans_email: list[str] = []
    with get_db() as conn:
        ph = ",".join("?" * len(ids))
        trps = conn.execute(
            f"""SELECT * FROM expe_transporteurs WHERE id IN ({ph}) AND actif=1
                ORDER BY nom COLLATE NOCASE""",
            ids,
        ).fetchall()
        for t in trps:
            d = dict(t)
            adresses = carb.emails_transporteur(d)
            if not adresses:
                sans_email.append(d["nom"])
                continue
            ok_un = False
            for email in adresses:
                token = carb.token_portail(conn, email=email, transporteur_id=int(d["id"]))
                sujet, corps = carb.email_demande_taxe(
                    nom_transporteur=d["nom"],
                    portail_lien=f"{public_base_url()}/portail/expe/{token}",
                    langue=d.get("langue"),
                    pct_actuel=float(d.get("taxe_carburant_pct") or 0),
                    maj_le=d.get("taxe_carburant_maj_le"),
                    user_nom=user_nom,
                )
                if send_email(
                    to=email,
                    subject=sujet,
                    html_body=corps,
                    reply_to=reply_to,
                    from_upn=EXPE_DEVIS_FROM,
                ):
                    ok_un = True
            if ok_un:
                carb.noter_demande(conn, transporteur_id=int(d["id"]), auteur=auteur)
                envoyes.append(d["nom"])
            else:
                echecs.append(d["nom"])
            # Commit par transporteur : un envoi parti doit rester noté même si
            # le suivant plante.
            conn.commit()
        transporteurs = carb.liste(conn)

    log_action(
        user=user,
        action="SEND",
        module="expe",
        objet=f"Taxe carburant — demande à {len(envoyes)} transporteur(s)",
        ip=request.client.host if request.client else None,
    )
    return {
        "envoyes": envoyes,
        "echecs": echecs,
        "sans_email": sans_email,
        "transporteurs": transporteurs,
    }
