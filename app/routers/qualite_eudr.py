"""MyQualité › Certifications SIFA › EUDR — questionnaire fournisseurs.

Deux faces, comme la taxe carburant de MyExpé :

- `router` (prefix /api/qualite/eudr) : l'écran interne — liste des
  fournisseurs avec l'état de leur réponse, envoi des demandes, historique.
  Lecture : ROLES_QUALITE_VIEW. Envoi : ROLES_QUALITE.
- `router_html` + `router_api` : le formulaire public ouvert par le lien de
  l'email, sans compte. Le jeton est la seule clé ; un jeton inconnu compte
  dans la même limite par IP que le portail transporteur.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.database import get_db
from app.routers.expe_portail import (
    _check_rate_limit,
    _client_ip,
    _record_invalid_attempt,
    _visiteur_interne,
)
from app.routers.qualite import _require_qualite_access, _require_qualite_view
from app.services import qualite_eudr as eudr
from app.services.audit_service import log_action
from app.services.email_service import send_email
from app.web.eudr_portail_page import get_eudr_404_html, get_eudr_portail_html
from config import EUDR_CHOIX, EUDR_LANGUES, eudr_langue, public_base_url

router = APIRouter(prefix="/api/qualite/eudr", tags=["qualite_eudr"])
router_html = APIRouter(tags=["eudr_portail"])
router_api = APIRouter(prefix="/api/portail/eudr", tags=["eudr_portail_api"])


def _auteur(user: dict) -> str | None:
    addr = str(user.get("email") or user.get("identifiant") or "").strip()
    return addr or None


# ── Écran interne ────────────────────────────────────────────────────────


@router.get("/fournisseurs")
def liste_fournisseurs(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return {"fournisseurs": eudr.liste(conn), "choix": EUDR_CHOIX}


@router.get("/fournisseurs/{fournisseur_id}/reponses")
def reponses_fournisseur(request: Request, fournisseur_id: int):
    _require_qualite_view(request)
    with get_db() as conn:
        return {"reponses": eudr.historique(conn, fournisseur_id)}


@router_html.get("/qualite/eudr/apercu", response_class=HTMLResponse)
def apercu_questionnaire(request: Request):
    """Le formulaire tel que le voit le fournisseur, sur des données factices.
    Rien n'est enregistré : la page ne contacte aucune API (`apercu`)."""
    _require_qualite_view(request)
    donnees = _donnees_formulaire(
        fournisseur="Exemple fournisseur",
        email="contact@fournisseur.example",
        langue=request.query_params.get("lang"),
        precedente=None,
    )
    return HTMLResponse(get_eudr_portail_html("apercu", apercu=donnees))


def _donnees_formulaire(*, fournisseur: str, email: str, langue, precedente) -> dict:
    return {
        "fournisseur": fournisseur,
        "email": email,
        "langue": eudr_langue(langue),
        "precedente": precedente,
        # Les trois langues d'un coup : changer de langue sur la page ne
        # recharge rien et ne perd pas ce qui est déjà saisi.
        "choix": {
            lang: {c: {k: v[lang] for k, v in opts.items()} for c, opts in EUDR_CHOIX.items()}
            for lang in EUDR_LANGUES
        },
    }


@router.post("/demander")
def demander(request: Request, body: dict = Body(...)):
    """Envoie le lien du questionnaire.

    `envois` : [{fournisseur_id, emails: [..], langue: en|fr|es}]. L'expéditeur est la personne
    qui clique, comme pour les appels d'offres : le fournisseur lui répond
    directement. Commit par fournisseur — un envoi parti reste noté même si
    le suivant plante.
    """
    user = _require_qualite_access(request)
    envois = body.get("envois") or []
    if not isinstance(envois, list) or not envois:
        raise HTTPException(status_code=400, detail="Aucun fournisseur sélectionné.")

    auteur = _auteur(user)
    expediteur = auteur if auteur and "@" in auteur else None
    user_nom = user.get("nom") or auteur or ""
    envoyes: list[str] = []
    echecs: list[str] = []
    sans_email: list[str] = []
    with get_db() as conn:
        for e in envois:
            try:
                fid = int(e.get("fournisseur_id"))
            except (TypeError, ValueError, AttributeError):
                continue
            four = conn.execute(
                "SELECT id, nom FROM fournisseurs_fsc WHERE id=? AND actif=1", (fid,)
            ).fetchone()
            if not four:
                continue
            adresses = [a.strip() for a in (e.get("emails") or []) if eudr.email_valide(a)]
            if not adresses:
                sans_email.append(four["nom"])
                continue
            langue = eudr_langue(e.get("langue"))
            ok_un = False
            for email in adresses:
                dem = eudr.demande_pour(conn, fournisseur_id=fid, email=email, langue=langue)
                sujet, corps = eudr.email_demande(
                    nom_fournisseur=four["nom"],
                    lien=f"{public_base_url()}/portail/eudr/{dem['token']}",
                    user_nom=user_nom,
                    relance=int(dem.get("nb_envois") or 0) > 0,
                    langue=langue,
                )
                if send_email(to=email, subject=sujet, html_body=corps,
                              reply_to=expediteur, from_upn=expediteur):
                    eudr.noter_envoi(conn, demande_id=int(dem["id"]), auteur=auteur, langue=langue)
                    ok_un = True
            (envoyes if ok_un else echecs).append(four["nom"])
            conn.commit()
        fournisseurs = eudr.liste(conn)

    log_action(
        user=user,
        action="SEND",
        module="qualite",
        objet=f"EUDR — questionnaire envoyé à {len(envoyes)} fournisseur(s)",
        ip=request.client.host if request.client else None,
    )
    return {"envoyes": envoyes, "echecs": echecs, "sans_email": sans_email,
            "fournisseurs": fournisseurs}


# ── Formulaire public ────────────────────────────────────────────────────


def _demande_ou_none(conn, token: str, ip: str) -> dict | None:
    _check_rate_limit(ip)
    dem = eudr.demande_par_token(conn, token)
    if not dem:
        _record_invalid_attempt(ip)
    return dem


@router_html.get("/portail/eudr/{token}", response_class=HTMLResponse)
def page_portail(request: Request, token: str):
    ip = _client_ip(request)
    try:
        with get_db() as conn:
            dem = _demande_ou_none(conn, token, ip)
            if not dem:
                return HTMLResponse(get_eudr_404_html(), status_code=404)
            if not _visiteur_interne(request):
                eudr.noter_ouverture(conn, dem)
                conn.commit()
    except HTTPException as exc:
        if exc.status_code == 429:
            return HTMLResponse(get_eudr_404_html(), status_code=429)
        raise
    return HTMLResponse(get_eudr_portail_html(token))


@router_api.get("/{token}")
def donnees_portail(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        dem = _demande_ou_none(conn, token, ip)
        if not dem:
            raise HTTPException(status_code=404, detail="Invalid or expired link.")
        precedente = eudr.derniere_reponse(conn, int(dem["fournisseur_id"]))
    return _donnees_formulaire(
        fournisseur=dem["fournisseur_nom"],
        email=dem["email"],
        langue=dem.get("langue"),
        precedente=precedente,
    )


@router_api.post("/{token}/langue")
def changer_langue(request: Request, token: str, body: dict = Body(...)):
    """Le fournisseur change de langue : les relances suivront ce choix."""
    ip = _client_ip(request)
    with get_db() as conn:
        dem = _demande_ou_none(conn, token, ip)
        if not dem:
            raise HTTPException(status_code=404, detail="Invalid or expired link.")
        eudr.noter_langue(conn, dem, (body or {}).get("langue"))
        conn.commit()
    return {"ok": True}


@router_api.post("/{token}")
def repondre(request: Request, token: str, body: dict = Body(...)):
    ip = _client_ip(request)
    with get_db() as conn:
        dem = _demande_ou_none(conn, token, ip)
        if not dem:
            raise HTTPException(status_code=404, detail="Invalid or expired link.")
        try:
            reponse = eudr.valider_reponse(body or {})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        eudr.enregistrer_reponse(conn, demande=dem, reponse=reponse, ip=ip)
        if (body or {}).get("langue"):
            eudr.noter_langue(conn, dem, body["langue"])
        conn.commit()

    # La notification ne doit jamais faire échouer la réponse du fournisseur.
    destinataire = (dem.get("envoye_par") or "").strip()
    if "@" in destinataire:
        try:
            sujet, corps = eudr.email_reponse_recue(
                nom_fournisseur=dem["fournisseur_nom"],
                reponse=reponse,
                lien_mysifa=f"{public_base_url()}/qualite",
            )
            send_email(to=destinataire, subject=sujet, html_body=corps)
        except Exception:
            pass
    log_action(
        user=None,
        action="SEND",
        module="qualite",
        objet=f"EUDR — réponse de {dem['fournisseur_nom']}",
        ip=ip,
    )
    return {"ok": True}
