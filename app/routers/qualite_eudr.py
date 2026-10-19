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

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.core.database import get_db
from app.routers.expe_portail import (
    _check_rate_limit,
    _client_ip,
    _record_invalid_attempt,
    _visiteur_interne,
)
from app.routers.qualite import _require_qualite_access, _require_qualite_view, _sanitize_filename
from app.services import qualite_eudr as eudr
from app.services.audit_service import log_action
from app.services.email_service import send_email
from app.web.eudr_portail_page import get_eudr_404_html, get_eudr_portail_html
from config import EUDR_CHOIX, EUDR_LANGUES, UPLOAD_DIR, eudr_langue, public_base_url

router = APIRouter(prefix="/api/qualite/eudr", tags=["qualite_eudr"])
router_html = APIRouter(tags=["eudr_portail"])
router_api = APIRouter(prefix="/api/portail/eudr", tags=["eudr_portail_api"])

EUDR_PIECES_DIR = os.path.join(UPLOAD_DIR, "qualite", "eudr")


def _auteur(user: dict) -> str | None:
    addr = str(user.get("email") or user.get("identifiant") or "").strip()
    return addr or None


# ── Écran interne ────────────────────────────────────────────────────────


@router.get("/fournisseurs")
def liste_fournisseurs(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return {
            "fournisseurs": eudr.liste(conn),
            "choix": EUDR_CHOIX,
            "liens_communs": _liens_avec_url(eudr.liens_communs(conn)),
            "a_rattacher": eudr.a_rattacher(conn),
        }


def _liens_avec_url(liens: list[dict]) -> list[dict]:
    for l in liens:
        l["url"] = f"{public_base_url()}/portail/eudr/commun/{l['token']}?lang={l['langue']}"
    return liens


# ── Lien commun : gestion ────────────────────────────────────────────────


@router.post("/liens-communs")
def creer_lien_commun(request: Request, body: dict = Body(...)):
    user = _require_qualite_access(request)
    with get_db() as conn:
        try:
            lien = eudr.creer_lien_commun(conn, libelle=body.get("libelle"),
                                          langue=body.get("langue"), auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        liens = _liens_avec_url(eudr.liens_communs(conn))
    log_action(user=user, action="CREATE", module="qualite",
               objet=f"EUDR — lien commun « {lien['libelle']} » créé",
               ip=request.client.host if request.client else None)
    return {"liens_communs": liens}


@router.post("/liens-communs/{lien_id}/desactiver")
def desactiver_lien_commun(request: Request, lien_id: int):
    user = _require_qualite_access(request)
    with get_db() as conn:
        lien = eudr.desactiver_lien_commun(conn, lien_id)
        if not lien:
            raise HTTPException(status_code=404, detail="Lien introuvable ou déjà désactivé.")
        conn.commit()
        liens = _liens_avec_url(eudr.liens_communs(conn))
    log_action(user=user, action="DELETE", module="qualite",
               objet=f"EUDR — lien commun « {lien['libelle']} » désactivé",
               ip=request.client.host if request.client else None)
    return {"liens_communs": liens}


@router.post("/a-rattacher/{reponse_commune_id}")
def rattacher_reponse(request: Request, reponse_commune_id: int, body: dict = Body(...)):
    """Range une réponse reçue par lien commun sous la fiche fournisseur choisie."""
    user = _require_qualite_access(request)
    try:
        fid = int(body.get("fournisseur_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Choisissez le fournisseur.")
    with get_db() as conn:
        try:
            res = eudr.rattacher(conn, reponse_commune_id=reponse_commune_id,
                                 fournisseur_id=fid, auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        out = {"fournisseurs": eudr.liste(conn), "a_rattacher": eudr.a_rattacher(conn)}
    log_action(user=user, action="UPDATE", module="qualite",
               objet=f"EUDR — réponse par lien commun rattachée à {res['fournisseur']}",
               ip=request.client.host if request.client else None)
    return out


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


@router.post("/fournisseurs/{fournisseur_id}/saisie")
async def saisie_manuelle(
    request: Request,
    fournisseur_id: int,
    role: str = Form(""),
    perimetre: str = Form(""),
    transmission: str = Form(""),
    commentaire: str = Form(""),
    piece: Optional[UploadFile] = File(None),
):
    """Réponse reçue hors formulaire (courrier, email, appel) : saisie par la
    qualité, avec le courrier en pièce jointe. Le fournisseur passe en
    « Répondu » ; ses demandes en cours restent valables."""
    user = _require_qualite_access(request)
    fichier = None
    if piece is not None and piece.filename:
        original = _sanitize_filename(piece.filename)
        ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if ext not in eudr.PIECE_TYPES:
            raise HTTPException(status_code=400, detail="Pièce jointe : PDF, image, email (.msg, .eml) ou Word uniquement.")
        contenu = await piece.read()
        if len(contenu) > eudr.PIECE_MAX_OCTETS:
            raise HTTPException(status_code=400, detail="Pièce jointe trop lourde — 15 Mo maximum.")
        os.makedirs(EUDR_PIECES_DIR, exist_ok=True)
        nom_disque = f"eudr_{fournisseur_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
        with open(os.path.join(EUDR_PIECES_DIR, nom_disque), "wb") as fh:
            fh.write(contenu)
        fichier = (nom_disque, original, eudr.PIECE_TYPES[ext])
    with get_db() as conn:
        four = conn.execute("SELECT id, nom FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not four:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        try:
            eudr.enregistrer_manuel(
                conn, fournisseur_id=fournisseur_id, auteur=_auteur(user), piece=fichier,
                body={"role": role, "perimetre": perimetre, "transmission": transmission,
                      "commentaire": commentaire},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        fournisseurs = eudr.liste(conn)
    log_action(
        user=user,
        action="CREATE",
        module="qualite",
        objet=f"EUDR — réponse saisie à la main pour {four['nom']}",
        ip=request.client.host if request.client else None,
    )
    return {"fournisseurs": fournisseurs}


@router.get("/reponses/{reponse_id}/piece")
def piece_jointe(request: Request, reponse_id: int):
    _require_qualite_view(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT piece_filename, piece_original FROM eudr_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
    if not row or not row["piece_filename"]:
        raise HTTPException(status_code=404, detail="Aucune pièce jointe pour cette réponse.")
    chemin = os.path.join(EUDR_PIECES_DIR, row["piece_filename"])
    if not os.path.isfile(chemin):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur.")
    ext = row["piece_filename"].rsplit(".", 1)[-1].lower()
    # Type déduit de l'extension, jamais du type annoncé par le navigateur.
    media = eudr.PIECE_TYPES.get(ext)
    if not media:
        raise HTTPException(status_code=404, detail="Type de fichier non servi.")
    nom = _sanitize_filename(row["piece_original"] or row["piece_filename"])
    mode = "inline" if ext in eudr.PIECE_EN_LIGNE else "attachment"
    return FileResponse(chemin, media_type=media,
                        headers={"Content-Disposition": f'{mode}; filename="{nom}"'})


@router.get("/questionnaire.pdf")
def questionnaire_pdf(request: Request):
    """Le questionnaire à remplir à la main, dans la langue demandée (?lang=).
    `?fournisseur_id=` pré-inscrit le nom du fournisseur ; l'adresse de retour
    est celle de l'utilisateur qui télécharge."""
    from fastapi.responses import Response
    from app.services.eudr_questionnaire_pdf import construire_pdf

    user = _require_qualite_view(request)
    lang = eudr_langue(request.query_params.get("lang"))
    nom = ""
    fid = (request.query_params.get("fournisseur_id") or "").strip()
    if fid.isdigit():
        with get_db() as conn:
            row = conn.execute("SELECT nom FROM fournisseurs_fsc WHERE id=?", (int(fid),)).fetchone()
            nom = row["nom"] if row else ""
    retour = _auteur(user) or ""
    pdf = construire_pdf(lang, fournisseur=nom, retour=retour if "@" in retour else "")
    fichier = _sanitize_filename(f"EUDR_questionnaire_{lang.upper()}{'_' + nom if nom else ''}.pdf")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fichier}"'})


@router.post("/demandes/{demande_id}/annuler")
def annuler_demande(request: Request, demande_id: int):
    """Retire un destinataire : son lien cesse de fonctionner."""
    user = _require_qualite_access(request)
    with get_db() as conn:
        dem = eudr.annuler_demande(conn, demande_id)
        if not dem:
            raise HTTPException(status_code=404, detail="Envoi introuvable ou déjà retiré.")
        conn.commit()
        fournisseurs = eudr.liste(conn)
    log_action(
        user=user,
        action="DELETE",
        module="qualite",
        objet=f"EUDR — lien de {dem['fournisseur_nom']} désactivé ({dem['email']})",
        ip=request.client.host if request.client else None,
    )
    return {"fournisseurs": fournisseurs}


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


@router_html.get("/portail/eudr/commun/{token}", response_class=HTMLResponse)
def page_portail_commun(request: Request, token: str):
    ip = _client_ip(request)
    try:
        with get_db() as conn:
            _check_rate_limit(ip)
            lien = eudr.lien_commun_par_token(conn, token)
            if not lien:
                _record_invalid_attempt(ip)
                return HTMLResponse(get_eudr_404_html(), status_code=404)
    except HTTPException as exc:
        if exc.status_code == 429:
            return HTMLResponse(get_eudr_404_html(), status_code=429)
        raise
    return HTMLResponse(get_eudr_portail_html(token, commun=True))


def _lien_ou_404(conn, token: str, ip: str) -> dict:
    _check_rate_limit(ip)
    lien = eudr.lien_commun_par_token(conn, token)
    if not lien:
        _record_invalid_attempt(ip)
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    return lien


@router_api.get("/commun/{token}")
def donnees_portail_commun(request: Request, token: str):
    with get_db() as conn:
        lien = _lien_ou_404(conn, token, _client_ip(request))
    return _donnees_formulaire(fournisseur="", email="", langue=lien["langue"], precedente=None)


@router_api.post("/commun/{token}")
def repondre_commun(request: Request, token: str, body: dict = Body(...)):
    ip = _client_ip(request)
    with get_db() as conn:
        lien = _lien_ou_404(conn, token, ip)
        try:
            reponse = eudr.valider_reponse(body or {})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        eudr.enregistrer_reponse_commune(conn, lien=lien, reponse=reponse, ip=ip)
        conn.commit()
    destinataire = (lien.get("cree_par") or "").strip()
    if "@" in destinataire:
        try:
            sujet, corps = eudr.email_reponse_recue(
                nom_fournisseur=f"{reponse.get('repondant_societe')} (lien commun, à rattacher)",
                reponse=reponse,
                lien_mysifa=f"{public_base_url()}/qualite",
            )
            send_email(to=destinataire, subject=sujet, html_body=corps)
        except Exception:
            pass
    log_action(user=None, action="SEND", module="qualite",
               objet=f"EUDR — réponse par lien commun de {reponse.get('repondant_societe')}", ip=ip)
    return {"ok": True}


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
