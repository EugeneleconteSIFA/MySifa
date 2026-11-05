"""Espace SIFA — portail unique des destinataires externes (public, sans compte).

- `router_html` : `GET /portail/{jeton}` — la page de l'Espace.
- `router_api` (prefix /api/portail/espace) : contenu de l'Espace, lecture et
  réponse d'un formulaire.

Le jeton est la seule clé. Un jeton inconnu compte dans la même limite par IP
que le portail transporteur et EUDR. Une visite d'un utilisateur MySifa
connecté (cookie de session) ne marque ni l'accès ni l'ouverture.

Services : app/services/portail_espace.py, qualite_formulaires_envois.py.
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
from app.services import portail_espace as espace_svc
from app.services import qualite_formulaires_envois as envois
from app.services.audit_service import log_action
from app.services.email_service import send_email
from app.web.portail_espace_page import get_espace_404_html, get_espace_html
from config import public_base_url

router_html = APIRouter(tags=["portail_espace"])
router_api = APIRouter(prefix="/api/portail/espace", tags=["portail_espace_api"])

_SANS_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"}


def _espace_ou_404(conn, token: str, ip: str) -> dict:
    _check_rate_limit(ip)
    esp = espace_svc.lire_par_token(conn, token)
    if not esp:
        _record_invalid_attempt(ip)
        raise HTTPException(status_code=404, detail="Lien invalide ou désactivé.")
    return esp


def _destinataire_ou_404(conn, esp: dict, did: int) -> dict:
    dest = envois.destinataire(conn, did)
    if (not dest or dest["email"] != esp["email"] or not dest["actif"]
            or dest["formulaire_statut"] == "archive"):
        raise HTTPException(status_code=404, detail="Ce formulaire n'est plus disponible.")
    return dest


@router_html.get("/portail/{token}", response_class=HTMLResponse)
def page_espace(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        try:
            _espace_ou_404(conn, token, ip)
        except HTTPException as e:
            if e.status_code == 429:
                raise
            return HTMLResponse(get_espace_404_html(), status_code=404, headers=_SANS_CACHE)
    return HTMLResponse(get_espace_html(token), headers=_SANS_CACHE)


@router_api.get("/{token}")
def contenu(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        esp = _espace_ou_404(conn, token, ip)
        if not _visiteur_interne(request):
            espace_svc.noter_acces(conn, esp, ip)
            conn.commit()
        c = espace_svc.contenu(conn, esp["email"])
    return {"email": esp["email"], "nom": esp["nom"], **c}


@router_api.get("/{token}/formulaires/{did}")
def lire_formulaire(request: Request, token: str, did: int):
    ip = _client_ip(request)
    with get_db() as conn:
        esp = _espace_ou_404(conn, token, ip)
        dest = _destinataire_ou_404(conn, esp, did)
        if not _visiteur_interne(request):
            envois.noter_ouverture(conn, did)
            conn.commit()
        rep = envois.derniere_reponse(conn, did)
        return {
            "id": dest["id"], "titre": dest["titre"], "description": dest["description"],
            "message": dest["message"], "echeance": dest["echeance"], "de": dest["cree_par"],
            "envoye_le": dest["envoye_le"], "statut": dest["statut"],
            "schema": envois.schema_envoi(conn, dest),
            "reponse": ({"reponses": rep["reponses"], "repondant_nom": rep["repondant_nom"],
                         "soumis_le": rep["soumis_le"]} if rep else None),
        }


@router_api.post("/{token}/formulaires/{did}")
def repondre(request: Request, token: str, did: int, body: dict = Body(...)):
    ip = _client_ip(request)
    with get_db() as conn:
        esp = _espace_ou_404(conn, token, ip)
        dest = _destinataire_ou_404(conn, esp, did)
        schema = envois.schema_envoi(conn, dest)
        reponses, manquantes = envois.nettoyer_reponses(schema, body.get("reponses"))
        if manquantes:
            raise HTTPException(status_code=400, detail=manquantes[:20])
        envois.enregistrer_reponse(conn, dest, reponses, repondant_nom=str(body.get("repondant_nom") or ""), ip=ip)
        nc = envois.non_conformites(schema, reponses)
        conn.commit()
    _prevenir_auteur(dest, nb_nc=len(nc))
    log_action(user=None, action="SEND", module="qualite",
               objet=f"Formulaire « {dest['titre']} » — réponse de {dest['organisation'] or dest['nom'] or dest['email']}",
               ip=ip)
    return {"ok": True}


def _prevenir_auteur(dest: dict, *, nb_nc: int) -> None:
    """Email interne à l'auteur de l'envoi. Ne bloque jamais la réponse."""
    a = (dest.get("cree_par_email") or "").strip()
    if not a:
        return
    try:
        from app.services.email_service import _email_detail_table, _esc, email_mysifa_layout

        qui = dest.get("organisation") or dest.get("nom") or dest["email"]
        lignes = [("Formulaire", _esc(dest["titre"])), ("Destinataire", _esc(f"{qui} — {dest['email']}"))]
        if nb_nc:
            lignes.append(("Non-conformités", _esc(f"{nb_nc} réponse(s) signalée(s) non conforme(s)")))
        corps = email_mysifa_layout(
            subtitle="Réponse à un formulaire",
            body_html=('<p style="margin:0 0 18px;font-size:14px;color:#475569;line-height:1.65">'
                       "Réponse reçue.</p>" + _email_detail_table(lignes)),
            cta_href=f"{public_base_url()}/tools?outil=formulaires&formulaire={dest['formulaire_id']}&onglet=suivi",
            cta_label="Voir les réponses",
        )
        sujet = ("Non-conformité · " if nb_nc else "") + f"Réponse — {dest['titre']} — {qui}"
        send_email(to=a, subject=sujet[:200], html_body=corps)
    except Exception:
        pass
