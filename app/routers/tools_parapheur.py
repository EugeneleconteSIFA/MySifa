"""MyTools › Parapheur — API.

`router` (prefix /api/tools/parapheur, session MySifa) :
  GET  ""                          demandes visibles, filtre `statut`
  GET  /candidats                  signataires possibles (interne, fournisseur, client)
  GET  /ma-signature               dernière signature de l'utilisateur (réutilisation)
  POST ""                          création (multipart : fichier + données JSON), envoi
  GET  /{id}                       détail, signataires, zones, historique
  GET  /{id}/document              PDF d'origine (pièce jointe)
  GET  /{id}/final                 PDF scellé (pièce jointe)
  POST /{id}/signer                signature de l'utilisateur connecté
  POST /{id}/refuser               refus motivé
  POST /{id}/signataires/{sid}/relancer
  POST /{id}/annuler

`router_espace` (prefix /api/portail/espace, sans compte) : la signature d'un
externe dans son Espace SIFA. Le jeton de l'Espace est dans le chemin (règle
commune des portails) ; le jeton de SIGNATURE voyage dans l'en-tête
`X-Parapheur-Jeton`, jamais dans l'adresse : il n'entre dans aucun journal.

Droits revérifiés à chaque appel (app/services/parapheur.py). Toute écriture
journalise explicitement (log_action) : le middleware d'audit se tait alors.
"""
from __future__ import annotations

import json
import unicodedata
from urllib.parse import quote

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.core.database import get_db
from app.routers.expe_portail import _check_rate_limit, _record_invalid_attempt, _visiteur_interne
from app.services import parapheur as svc
from app.services import portail_espace as espace_svc
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from config import PARAPHEUR_TAILLE_MAX_MO

router = APIRouter(prefix="/api/tools/parapheur", tags=["tools_parapheur"])
router_espace = APIRouter(prefix="/api/portail/espace", tags=["tools_parapheur_espace"])

ENTETE_JETON = "x-parapheur-jeton"


def _ip(request: Request) -> str:
    ip = request.client.host if request.client and request.client.host else ""
    fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if fwd and ip in ("127.0.0.1", "::1", ""):
        ip = fwd
    return (ip or "inconnue")[:64]


def _ua(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:300]


def _acteur(user: dict) -> str:
    return user.get("nom") or user.get("email") or f"utilisateur {user.get('id')}"


def _objet(d: dict) -> str:
    return f"Parapheur · demande n° {d['id']} · {d.get('titre') or ''}"[:300]


def _http(e: svc.Refus) -> HTTPException:
    return HTTPException(status_code=e.code, detail=str(e))


def _pdf(octets: bytes, nom: str) -> Response:
    ascii_ = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii").replace('"', "") or "document.pdf"
    return Response(content=octets, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nom)}",
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


def _demande_visible(conn, did: int, user: dict) -> tuple[dict, list[dict]]:
    d = svc.demande(conn, did)
    if not d:
        raise HTTPException(status_code=404, detail="Demande introuvable.")
    sigs = svc.signataires(conn, did)
    if not svc.peut_voir(user, d, sigs):
        raise HTTPException(status_code=403, detail="Accès refusé à cette demande.")
    return d, sigs


def _notifier_tous(conn, ids: list[int], *, acteur: str) -> list[int]:
    echecs = []
    for sid in ids:
        try:
            if not svc.notifier(conn, sid, acteur=acteur):
                echecs.append(sid)
        except Exception:
            echecs.append(sid)
    return echecs


def _apres_signature(conn, did: int, res: dict, *, acteur: str) -> None:
    conn.commit()
    _notifier_tous(conn, res.get("suivants") or [], acteur=acteur)
    if res.get("termine"):
        try:
            svc.prevenir_fin(conn, did)
        except Exception:
            pass


# ── Session MySifa ──────────────────────────────────────────────────────

@router.get("")
def liste(request: Request, statut: str = "en_cours"):
    user = get_current_user(request)
    filtre = statut if statut in svc.FILTRES else "en_cours"
    with get_db() as conn:
        res = svc.liste(conn, user, filtre)
    res["peut_creer"] = svc.peut_creer(user)
    return res


@router.get("/candidats")
def candidats(request: Request, type: str = "interne", q: str = ""):
    user = get_current_user(request)
    if not svc.peut_creer(user):
        raise HTTPException(status_code=403, detail="Votre profil ne permet pas d'envoyer un document à signer.")
    q = (q or "").strip()[:80]
    with get_db() as conn:
        if type == "interne":
            ql = q.lower()
            rows = conn.execute("SELECT id, nom, email, role FROM users WHERE actif = 1 ORDER BY nom COLLATE NOCASE").fetchall()
            out = [{"type": "interne", "user_id": r["id"], "nom": r["nom"] or "", "email": r["email"] or "",
                    "organisation": ""} for r in rows
                   if not ql or ql in f"{r['nom'] or ''} {r['email'] or ''}".lower()]
            return {"candidats": out[:200]}
        if type not in ("fournisseur", "client"):
            raise HTTPException(status_code=400, detail="Type de signataire inconnu.")
        from app.services import qualite_formulaires_envois as envois
        try:
            brut = envois.candidats(conn, type, q)
        except Exception:
            brut = []
    return {"candidats": [{"type": "externe", "nom": c.get("nom") or "", "email": c["email"],
                           "organisation": c.get("organisation") or ""} for c in brut[:200]]}


@router.get("/ma-signature")
def ma_signature(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        return {"signature": svc.ma_signature(conn, int(user.get("id") or 0))}


@router.post("")
async def creer(request: Request, fichier: UploadFile = File(...), donnees: str = Form(...)):
    user = get_current_user(request)
    if not svc.peut_creer(user):
        raise HTTPException(status_code=403, detail="Votre profil ne permet pas d'envoyer un document à signer.")
    octets = await fichier.read(PARAPHEUR_TAILLE_MAX_MO * 1024 * 1024 + 1)
    try:
        d_json = json.loads(donnees or "{}")
        if not isinstance(d_json, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="Données de la demande illisibles.")
    with get_db() as conn:
        try:
            did = svc.creer(conn, octets=octets, nom_fichier=fichier.filename or "document.pdf", donnees=d_json, auteur=user)
            ids = svc.suivants(conn, did)
        except svc.Refus as e:
            raise _http(e)
        conn.commit()
        echecs = _notifier_tous(conn, ids, acteur=_acteur(user))
        d = svc.demande(conn, did)
        nb = len(svc.signataires(conn, did))
    log_action(user=user, action="CREATE", module="tools", objet=_objet(d),
               detail={"signataires": nb, "mode": d["mode"], "echeance": d["echeance"], "notifies": len(ids),
                       "echecs_envoi": len(echecs), "sha256": d["sha256_original"]}, request=request)
    return {"id": did, "notifies": len(ids) - len(echecs), "echecs": len(echecs)}


@router.get("/{did}")
def detail(did: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        try:
            return svc.detail(conn, did, user)
        except svc.Refus as e:
            raise _http(e)


@router.get("/{did}/document")
def document(did: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        d, _ = _demande_visible(conn, did, user)
        try:
            octets = svc.lire_fichier(d["fichier_original"])
        except svc.Refus as e:
            raise _http(e)
    return _pdf(octets, svc.nom_telechargement(d, final=False))


@router.get("/{did}/final")
def final(did: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        d, _ = _demande_visible(conn, did, user)
        if not d.get("fichier_final"):
            raise HTTPException(status_code=404, detail="Document final pas encore scellé.")
        try:
            octets = svc.lire_fichier(d["fichier_final"])
        except svc.Refus as e:
            raise _http(e)
        svc.evenement(conn, did, "telechargement", acteur=_acteur(user), ip=_ip(request))
        conn.commit()
    log_action(user=user, action="EXPORT", module="tools", objet=_objet(d) + " · document signé", request=request)
    return _pdf(octets, svc.nom_telechargement(d, final=True))


def _mon_signataire(conn, did: int, user: dict) -> tuple[dict, dict]:
    d, sigs = _demande_visible(conn, did, user)
    uid = int(user.get("id") or -1)
    s = next((x for x in sigs if x.get("user_id") is not None and int(x["user_id"]) == uid
              and x["statut"] in svc.EN_ATTENTE_SIG), None)
    if not s:
        raise HTTPException(status_code=409, detail="Aucune signature ne vous est demandée sur ce document.")
    return d, s


@router.post("/{did}/ouvrir")
def ouvrir(did: int, request: Request):
    """L'utilisateur ouvre le document à signer : consultation notée."""
    user = get_current_user(request)
    with get_db() as conn:
        d, s = _mon_signataire(conn, did, user)
        svc.noter_ouverture(conn, s, ip=_ip(request), acteur=_acteur(user))
        conn.commit()
    log_action(user=user, action="UPDATE", module="tools", objet=_objet(d) + " · document consulté", request=request)
    return {"ok": True}


@router.post("/{did}/signer")
def signer(did: int, request: Request, body: dict = Body(...)):
    user = get_current_user(request)
    with get_db() as conn:
        d, s = _mon_signataire(conn, did, user)
        try:
            res = svc.signer(conn, s["id"], signature=body.get("signature"), paraphe=body.get("paraphe"),
                             mode=str(body.get("mode") or ""), nom_saisi=str(body.get("nom") or user.get("nom") or ""),
                             ip=_ip(request), user_agent=_ua(request), acteur=_acteur(user))
        except svc.Refus as e:
            raise _http(e)
        _apres_signature(conn, did, res, acteur=_acteur(user))
    log_action(user=user, action="VALIDATE", module="tools", objet=_objet(d) + " · signature",
               detail={"termine": res["termine"]}, request=request)
    return {"ok": True, "termine": res["termine"]}


@router.post("/{did}/refuser")
def refuser(did: int, request: Request, body: dict = Body(...)):
    user = get_current_user(request)
    with get_db() as conn:
        d, s = _mon_signataire(conn, did, user)
        try:
            svc.refuser(conn, s["id"], motif=str(body.get("motif") or ""), ip=_ip(request), acteur=_acteur(user))
        except svc.Refus as e:
            raise _http(e)
        conn.commit()
        svc.prevenir_fin(conn, did)
    log_action(user=user, action="UPDATE", module="tools", objet=_objet(d) + " · refus de signer",
               detail={"motif": str(body.get("motif") or "")[:300]}, request=request)
    return {"ok": True}


@router.post("/{did}/signataires/{sid}/relancer")
def relancer(did: int, sid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        d, sigs = _demande_visible(conn, did, user)
        if not svc.peut_gerer(user, d):
            raise HTTPException(status_code=403, detail="Seul l'émetteur relance.")
        s = next((x for x in sigs if x["id"] == sid), None)
        if not s or d["statut"] != "en_cours" or s["statut"] not in svc.EN_ATTENTE_SIG:
            raise HTTPException(status_code=409, detail="Ce signataire n'attend pas de relance.")
        parti = svc.notifier(conn, sid, relance=True, acteur=_acteur(user))
    log_action(user=user, action="SEND", module="tools", objet=_objet(d) + f" · relance {s['nom'] or s['email']}",
               detail={"parti": parti}, request=request)
    if not parti:
        raise HTTPException(status_code=502, detail="Relance non partie — vérifier l'adresse du signataire.")
    return {"ok": True}


@router.post("/{did}/annuler")
def annuler(did: int, request: Request, body: dict = Body(default={})):
    user = get_current_user(request)
    with get_db() as conn:
        d, _ = _demande_visible(conn, did, user)
        if not svc.peut_gerer(user, d):
            raise HTTPException(status_code=403, detail="Seul l'émetteur annule.")
        try:
            svc.annuler(conn, did, motif=str(body.get("motif") or ""), acteur=_acteur(user))
        except svc.Refus as e:
            raise _http(e)
        conn.commit()
    log_action(user=user, action="CANCEL", module="tools", objet=_objet(d),
               detail={"motif": str(body.get("motif") or "")[:300]}, request=request)
    return {"ok": True}


# ── Espace SIFA (externes, sans compte) ─────────────────────────────────

def _espace(conn, token: str, ip: str) -> dict:
    _check_rate_limit(ip)
    esp = espace_svc.lire_par_token(conn, token)
    if not esp:
        _record_invalid_attempt(ip)
        raise HTTPException(status_code=404, detail="Lien invalide ou désactivé.")
    return esp


_RAISONS = {
    "inconnu": "Lien de signature invalide.",
    "expire": "Ce lien de signature a expiré. Demandez-en un nouveau depuis votre espace.",
    "epuise": "Ce lien de signature a été trop souvent utilisé. Demandez-en un nouveau depuis votre espace.",
    "traite": "Ce document n'attend plus votre signature.",
}


def _par_jeton(conn, request: Request, token: str, *, consommer: bool) -> tuple[dict, dict, dict]:
    ip = _ip(request)
    esp = _espace(conn, token, ip)
    s, raison = svc.par_jeton(conn, esp["email"], request.headers.get(ENTETE_JETON) or "", consommer=consommer)
    if raison:
        if raison == "inconnu":
            _record_invalid_attempt(ip)
        raise HTTPException(status_code=404 if raison == "inconnu" else 410,
                            detail={"message": _RAISONS[raison], "raison": raison,
                                    "signataire_id": s["id"] if s else None})
    return esp, s, svc.demande(conn, s["demande_id"])


@router_espace.get("/{token}/signature")
def espace_signature(token: str, request: Request):
    with get_db() as conn:
        esp, s, d = _par_jeton(conn, request, token, consommer=True)
        if not _visiteur_interne(request):
            svc.noter_ouverture(conn, s, ip=_ip(request), acteur=s["nom"] or s["email"])
        conn.commit()
        sigs = svc.signataires(conn, d["id"])
        return {
            "signataire": {"id": s["id"], "nom": s["nom"], "email": s["email"], "organisation": s["organisation"]},
            "demande": {k: d[k] for k in ("id", "titre", "message", "nom_fichier", "nb_pages", "echeance",
                                           "cree_par_nom", "mode", "sha256_original")},
            "zones": svc.zones(conn, d["id"], s["id"]),
            "circuit": [{"ordre": x["ordre"], "nom": x["nom"] or x["organisation"] or "", "statut": x["statut"],
                         "moi": x["id"] == s["id"]} for x in sigs],
        }


@router_espace.get("/{token}/signature/document")
def espace_document(token: str, request: Request):
    with get_db() as conn:
        _, _, d = _par_jeton(conn, request, token, consommer=False)
        try:
            octets = svc.lire_fichier(d["fichier_original"])
        except svc.Refus as e:
            raise _http(e)
    return _pdf(octets, svc.nom_telechargement(d, final=False))


@router_espace.post("/{token}/signature/signer")
def espace_signer(token: str, request: Request, body: dict = Body(...)):
    ip = _ip(request)
    with get_db() as conn:
        _, s, d = _par_jeton(conn, request, token, consommer=False)
        if not body.get("consentement"):
            raise HTTPException(status_code=400, detail="Cochez la case de consentement pour signer.")
        try:
            res = svc.signer(conn, s["id"], signature=body.get("signature"), paraphe=body.get("paraphe"),
                             mode=str(body.get("mode") or ""), nom_saisi=str(body.get("nom") or ""), ip=ip,
                             user_agent=_ua(request), acteur=str(body.get("nom") or s["nom"] or s["email"]))
        except svc.Refus as e:
            raise _http(e)
        _apres_signature(conn, d["id"], res, acteur=s["nom"] or s["email"])
    log_action(user=None, action="VALIDATE", module="tools",
               objet=_objet(d) + f" · signature de {s['organisation'] or s['nom'] or s['email']}", ip=ip)
    return {"ok": True, "termine": res["termine"]}


@router_espace.post("/{token}/signature/refuser")
def espace_refuser(token: str, request: Request, body: dict = Body(...)):
    ip = _ip(request)
    with get_db() as conn:
        _, s, d = _par_jeton(conn, request, token, consommer=False)
        try:
            svc.refuser(conn, s["id"], motif=str(body.get("motif") or ""), ip=ip, acteur=s["nom"] or s["email"])
        except svc.Refus as e:
            raise _http(e)
        conn.commit()
        svc.prevenir_fin(conn, d["id"])
    log_action(user=None, action="UPDATE", module="tools",
               objet=_objet(d) + f" · refus de {s['organisation'] or s['nom'] or s['email']}",
               detail={"motif": str(body.get("motif") or "")[:300]}, ip=ip)
    return {"ok": True}


@router_espace.post("/{token}/signatures/{sid}/lien")
def espace_nouveau_lien(token: str, sid: int, request: Request):
    ip = _ip(request)
    with get_db() as conn:
        esp = _espace(conn, token, ip)
        try:
            s = svc.signataire_espace(conn, esp["email"], sid)
            d = svc.demande(conn, s["demande_id"])
            if d["statut"] != "en_cours" or s["statut"] not in svc.EN_ATTENTE_SIG:
                raise svc.Refus("Ce document n'attend plus votre signature.", 409)
            parti = svc.nouveau_lien(conn, sid)
        except svc.Refus as e:
            raise _http(e)
    log_action(user=None, action="SEND", module="tools", objet=_objet(d) + f" · nouveau lien demandé par {s['email']}",
               detail={"parti": parti}, ip=ip)
    if not parti:
        raise HTTPException(status_code=502, detail="Email non parti — réessayez plus tard.")
    return {"ok": True}


@router_espace.get("/{token}/signatures/{sid}/final")
def espace_final(token: str, sid: int, request: Request):
    ip = _ip(request)
    with get_db() as conn:
        esp = _espace(conn, token, ip)
        try:
            s = svc.signataire_espace(conn, esp["email"], sid)
            d = svc.demande(conn, s["demande_id"])
            if d["statut"] != "signee" or not d.get("fichier_final"):
                raise svc.Refus("Document signé indisponible.", 404)
            octets = svc.lire_fichier(d["fichier_final"])
        except svc.Refus as e:
            raise _http(e)
        if not _visiteur_interne(request):
            svc.evenement(conn, d["id"], "telechargement", sid=sid, acteur=s["nom"] or s["email"], ip=ip)
            conn.commit()
    return _pdf(octets, svc.nom_telechargement(d, final=True))
