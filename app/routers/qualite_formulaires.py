"""MyQualité › Formulaires — création et publication de formulaires.

Lot 1 : éditeur et versions publiées. L'envoi aux fournisseurs, au personnel
et aux clients (lien personnel, suivi, relances) suit le modèle d'EUDR
(`qualite_eudr.py`) et viendra s'appuyer sur `qualite_formulaires_versions`.

Lecture : rôles qualité en lecture (`_require_qualite_view`).
Écriture : rôles qualité (`_require_qualite_access`).
Structure et règles : `app/services/qualite_formulaires.py`.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.core.database import get_db
from app.routers.qualite import _require_qualite_access, _require_qualite_view
from app.services import ia_usage
from app.services import qualite_formulaires as formulaires
from app.services import qualite_formulaires_envois as envois
from app.services import qualite_formulaires_exports as exports
from app.services import qualite_formulaires_ia as formulaires_ia
from app.services.email_service import send_email
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/qualite/formulaires", tags=["qualite_formulaires"])


def _auteur(user: dict) -> str | None:
    return (user.get("nom") or user.get("email") or user.get("identifiant") or None)


def _objet(fid: int, titre: str | None) -> str:
    return f"Formulaire #{fid}" + (f" · {titre}" if titre else "")


def _lire_ou_404(conn, fid: int) -> dict:
    d = formulaires.lire(conn, fid)
    if d is None:
        raise HTTPException(status_code=404, detail="Formulaire introuvable.")
    return d


@router.get("")
def liste(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return {"formulaires": formulaires.liste(conn)}


@router.post("")
def creer(request: Request, body: dict = Body(default={})):
    user = _require_qualite_access(request)
    with get_db() as conn:
        try:
            fid = formulaires.creer(conn, titre=body.get("titre") or "", description=body.get("description") or "",
                                    schema=body.get("schema"), auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        d = formulaires.lire(conn, fid)
    log_action(user=user, action="CREATE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return d


# ── Assistant IA ─────────────────────────────────────────────────────────
# Déclarées avant /{fid} : « ia » ne doit pas être lu comme un identifiant.


@router.get("/ia/modeles")
def ia_modeles(request: Request):
    _require_qualite_access(request)
    choix = formulaires_ia.choisir_modele(None)
    return {"modeles": formulaires_ia.formulaires_ia_modeles(), "defaut": choix["id"]}


@router.post("/ia/proposer")
async def ia_proposer(
    request: Request,
    consigne: str = Form(""),
    etat: str = Form(""),
    modele: Optional[str] = Form(None),
    fichiers: list[UploadFile] = File(default=[]),
):
    """Propose un formulaire. `etat` (JSON {titre, description, schema}) = le
    formulaire ouvert dans l'éditeur, enregistré ou non ; vide = création.
    Rien n'est enregistré : la proposition revient à l'écran."""
    user = _require_qualite_access(request)
    consigne = (consigne or "").strip()[:6000]
    fichiers = [f for f in (fichiers or []) if f and f.filename]
    if not consigne and not fichiers:
        raise HTTPException(status_code=400, detail="Décrire le formulaire souhaité ou joindre un document.")
    if len(fichiers) > formulaires_ia.PIECES_MAX:
        raise HTTPException(status_code=400, detail=f"{formulaires_ia.PIECES_MAX} documents au plus.")
    pieces = []
    for f in fichiers:
        mime = (f.content_type or "").lower()
        if mime not in formulaires_ia.PIECES_ACCEPTEES:
            raise HTTPException(status_code=400, detail=f"« {f.filename} » : seuls les PDF et les images (PNG, JPG, WEBP, GIF) sont lus.")
        contenu = await f.read(formulaires_ia.PIECE_MAX_OCTETS + 1)
        if len(contenu) > formulaires_ia.PIECE_MAX_OCTETS:
            raise HTTPException(status_code=400, detail=f"« {f.filename} » dépasse 15 Mo.")
        pieces.append({"mime": mime, "contenu": contenu, "nom": f.filename[:120]})
    try:
        e = json.loads(etat) if etat else {}
    except ValueError:
        e = {}
    if not isinstance(e, dict):
        e = {}
    try:
        with ia_usage.suivi(user, "formulaires", "qualite"):
            return formulaires_ia.proposer(
                consigne, titre=str(e.get("titre") or ""), description=str(e.get("description") or ""),
                schema=e.get("schema") if isinstance(e.get("schema"), dict) else None,
                pieces=pieces, modele=modele)
    except formulaires_ia.FormulaireIaErreur as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Envoi aux destinataires ──────────────────────────────────────────────
# Le lien de chaque email ouvre l'Espace SIFA du destinataire
# (app/routers/portail_espace.py), là où se trouve tout ce que SIFA lui adresse.


@router.get("/destinataires")
def destinataires_possibles(request: Request, type: str = "fournisseur", q: str = ""):
    _require_qualite_access(request)
    if type not in ("fournisseur", "client", "personnel"):
        raise HTTPException(status_code=400, detail="Type de destinataire inconnu.")
    with get_db() as conn:
        return {"destinataires": envois.candidats(conn, type, q)}


def _envoyer(conn, dest_ids: list[int], *, user: dict, relance: bool) -> dict:
    """Envoie l'invitation (ou la relance) à chaque destinataire. Commit après
    chaque envoi réussi : un échec au milieu ne fait pas oublier les envois
    déjà partis."""
    expediteur = (user.get("email") or "").strip() or None
    envoyes, echecs = [], []
    for did in dest_ids:
        dest = envois.destinataire(conn, did)
        if not dest or not dest["actif"]:
            continue
        sujet, corps = envois.email_invitation(dest, url=envois.url_destinataire(conn, dest), relance=relance)
        conn.commit()
        if send_email(to=dest["email"], subject=sujet, html_body=corps, reply_to=expediteur, from_upn=expediteur):
            envois.noter_envoi(conn, did)
            conn.commit()
            envoyes.append(dest["email"])
        else:
            echecs.append(dest["email"])
    return {"envoyes": envoyes, "echecs": echecs}


def _taches_personnel(conn, user: dict, envoi_id: int) -> None:
    """Destinataire du personnel : une tâche « formulaire à remplir » dans
    MySifa, terminée automatiquement à la réponse. Ne bloque jamais l'envoi."""
    try:
        from app.routers.taches import creer_tache_pour
        from config import TACHES_SERVICES_CODES
    except Exception:
        return
    rows = conn.execute(
        """SELECT d.id, d.user_id, d.email, e.titre, e.echeance, u.role
             FROM qualite_formulaires_destinataires d
             JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
             LEFT JOIN users u ON u.id = d.user_id
            WHERE d.envoi_id = ? AND d.type = 'personnel' AND d.user_id IS NOT NULL""",
        (envoi_id,),
    ).fetchall()
    for r in rows:
        try:
            dest = envois.destinataire(conn, r["id"])
            lien = envois.url_destinataire(conn, dest)
            description = (f"Formulaire à compléter : {r['titre']}.\n"
                           + (f"Réponse attendue avant le {r['echeance']}.\n" if r["echeance"] else "")
                           + f"Lien : {lien}")
            service = r["role"] if r["role"] in TACHES_SERVICES_CODES else "superadmin"
            tid = creer_tache_pour(conn, user, titre=f"Formulaire à remplir : {r['titre']}"[:200],
                                   description=description, ttype="autre", module="qualite",
                                   service=service, assignes=[int(r["user_id"])])
            conn.execute("UPDATE qualite_formulaires_destinataires SET tache_id = ? WHERE id = ?", (tid, r["id"]))
        except Exception:
            continue


@router.get("/{fid}/envois")
def suivi_envois(fid: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        _lire_ou_404(conn, fid)
        return {"envois": envois.suivi(conn, fid)}


@router.post("/{fid}/envois")
def envoyer(fid: int, request: Request, body: dict = Body(...)):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        try:
            cree = envois.creer_envoi(conn, fid, body.get("destinataires") or [], message=body.get("message") or "",
                                      echeance=body.get("echeance"), auteur=_auteur(user),
                                      auteur_email=(user.get("email") or None))
        except (ValueError, LookupError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        _taches_personnel(conn, user, cree["envoi_id"])
        conn.commit()
        res = _envoyer(conn, cree["destinataires"], user=user, relance=False)
    log_action(user=user, action="SEND", module="qualite", objet=_objet(fid, d["titre"]),
               detail={"envoi": cree["envoi_id"], "envoyes": len(res["envoyes"]), "echecs": res["echecs"][:20]},
               request=request)
    return {"envoi_id": cree["envoi_id"], **res}


@router.post("/destinataires/{did}/relancer")
def relancer_un(did: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        dest = envois.destinataire(conn, did)
        if not dest or not dest["actif"]:
            raise HTTPException(status_code=404, detail="Destinataire introuvable.")
        if dest["statut"] == "repondu":
            raise HTTPException(status_code=409, detail="Ce destinataire a déjà répondu.")
        res = _envoyer(conn, [did], user=user, relance=True)
    log_action(user=user, action="SEND", module="qualite",
               objet=_objet(dest["formulaire_id"], dest["titre"]) + f" · relance {dest['email']}", request=request)
    return res


@router.post("/envois/{eid}/relancer")
def relancer_envoi(eid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        e = conn.execute("SELECT formulaire_id, titre FROM qualite_formulaires_envois WHERE id = ?", (eid,)).fetchone()
        if not e:
            raise HTTPException(status_code=404, detail="Envoi introuvable.")
        ids = [r["id"] for r in conn.execute(
            """SELECT id FROM qualite_formulaires_destinataires
                WHERE envoi_id = ? AND actif = 1 AND statut != 'repondu'""", (eid,)).fetchall()]
        if not ids:
            raise HTTPException(status_code=409, detail="Tous les destinataires ont répondu.")
        res = _envoyer(conn, ids, user=user, relance=True)
    log_action(user=user, action="SEND", module="qualite",
               objet=_objet(e["formulaire_id"], e["titre"]) + f" · relance de {len(ids)} destinataire(s)", request=request)
    return res


@router.post("/destinataires/{did}/retirer")
def retirer(did: int, request: Request):
    """Le destinataire ne voit plus ce formulaire dans son Espace. Sa réponse
    éventuelle reste consultable ici."""
    user = _require_qualite_access(request)
    with get_db() as conn:
        dest = envois.destinataire(conn, did)
        if not dest:
            raise HTTPException(status_code=404, detail="Destinataire introuvable.")
        conn.execute("UPDATE qualite_formulaires_destinataires SET actif = 0 WHERE id = ?", (did,))
        conn.commit()
    log_action(user=user, action="DELETE", module="qualite",
               objet=_objet(dest["formulaire_id"], dest["titre"]) + f" · destinataire {dest['email']} retiré", request=request)
    return {"ok": True}


@router.get("/destinataires/{did}/reponse")
def voir_reponse(did: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        dest = envois.destinataire(conn, did)
        if not dest:
            raise HTTPException(status_code=404, detail="Destinataire introuvable.")
        rep = envois.derniere_reponse(conn, did)
        if not rep:
            raise HTTPException(status_code=404, detail="Pas encore de réponse.")
        schema = envois.schema_envoi(conn, dest)
        return {
            "destinataire": {k: dest[k] for k in ("id", "nom", "organisation", "email", "type", "statut", "repondu_le")},
            "titre": dest["titre"], "version": dest["version"], "schema": schema,
            "reponse": rep, "nc": envois.non_conformites(schema, rep["reponses"]),
        }


# ── Exports des réponses ─────────────────────────────────────────────────
# Lecture (rôles qualité, commercial compris). Chaque export est journalisé :
# il sort de MySifa des réponses de tiers (journal-audit.md : une lecture
# n'est pas tracée d'office, une extraction de données l'est explicitement).


def _telecharger(contenu, nom: str, media_type: str) -> Response:
    return Response(content=contenu, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{nom}"', "Cache-Control": "no-store"})


@router.get("/{fid}/reponses.csv")
def export_csv(fid: int, request: Request, envoi: Optional[int] = None, tous: int = 0):
    """Toutes les réponses (dernière version par destinataire). `envoi` limite
    à un envoi ; `tous=1` ajoute les destinataires sans réponse."""
    user = _require_qualite_view(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        entrees = exports.lignes(conn, fid, envoi_id=envoi, avec_sans_reponse=bool(tous))
    nom, texte = exports.csv_reponses(entrees, d["titre"])
    log_action(user=user, action="EXPORT", module="qualite", objet=_objet(fid, d["titre"]) + f" · CSV ({len(entrees)} ligne(s))",
               request=request)
    return _telecharger(texte, nom, "text/csv; charset=utf-8")


@router.get("/{fid}/reponses.pdf")
def export_pdf(fid: int, request: Request, envoi: Optional[int] = None):
    """Synthèse par question, liste des destinataires, puis chaque réponse."""
    user = _require_qualite_view(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        entrees = exports.lignes(conn, fid, envoi_id=envoi, avec_sans_reponse=True)
    if not any(e["reponse"] for e in entrees):
        raise HTTPException(status_code=404, detail="Aucune réponse à exporter.")
    nom, contenu = exports.pdf_ensemble(entrees, d["titre"], nb_destinataires=len(entrees))
    log_action(user=user, action="EXPORT", module="qualite", objet=_objet(fid, d["titre"]) + " · PDF des réponses",
               request=request)
    return _telecharger(contenu, nom, "application/pdf")


@router.get("/destinataires/{did}/reponse.pdf")
def export_reponse_pdf(did: int, request: Request):
    user = _require_qualite_view(request)
    with get_db() as conn:
        dest = envois.destinataire(conn, did)
        if not dest:
            raise HTTPException(status_code=404, detail="Destinataire introuvable.")
        rep = envois.derniere_reponse(conn, did)
        if not rep:
            raise HTTPException(status_code=404, detail="Pas encore de réponse.")
        schema = envois.schema_envoi(conn, dest)
        e = {"dest": dest, "schema": schema, "reponse": rep, "nc": envois.non_conformites(schema, rep["reponses"])}
    nom, contenu = exports.pdf_reponse(e, dest["titre"])
    log_action(user=user, action="EXPORT", module="qualite",
               objet=_objet(dest["formulaire_id"], dest["titre"]) + f" · PDF de la réponse de {dest['email']}", request=request)
    return _telecharger(contenu, nom, "application/pdf")


@router.get("/{fid}")
def detail(fid: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return _lire_ou_404(conn, fid)


@router.put("/{fid}")
def enregistrer(fid: int, request: Request, body: dict = Body(...)):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        if d["statut"] == "archive":
            raise HTTPException(status_code=409, detail="Formulaire archivé — le restaurer pour le modifier.")
        try:
            formulaires.enregistrer(conn, fid, titre=body.get("titre"), description=body.get("description"),
                                    schema=body.get("schema"), auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        d = formulaires.lire(conn, fid)
    # Appelé par l'enregistrement automatique de l'éditeur (après 2 s sans
    # frappe) : une ligne de journal par pause de saisie, pas par touche.
    log_action(user=user, action="UPDATE", module="qualite", objet=_objet(fid, d["titre"]),
               detail={"nb_questions": d["nb_questions"]}, request=request)
    return d


@router.post("/{fid}/publier")
def publier(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        _lire_ou_404(conn, fid)
        try:
            numero = formulaires.publier(conn, fid, auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        d = formulaires.lire(conn, fid)
    log_action(user=user, action="PUBLISH", module="qualite", objet=_objet(fid, d["titre"]),
               detail={"version": numero}, request=request)
    return d


@router.post("/{fid}/dupliquer")
def dupliquer(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        _lire_ou_404(conn, fid)
        nouveau = formulaires.dupliquer(conn, fid, auteur=_auteur(user))
        conn.commit()
        d = formulaires.lire(conn, nouveau)
    log_action(user=user, action="DUPLICATE", module="qualite", objet=_objet(nouveau, d["titre"]),
               detail={"source": fid}, request=request)
    return d


@router.post("/{fid}/archiver")
def archiver(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        formulaires.changer_statut(conn, fid, "archive", auteur=_auteur(user))
        conn.commit()
    log_action(user=user, action="ARCHIVE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return {"ok": True}


@router.post("/{fid}/restaurer")
def restaurer(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        statut = "publie" if d["version_courante"] else "brouillon"
        formulaires.changer_statut(conn, fid, statut, auteur=_auteur(user))
        conn.commit()
    log_action(user=user, action="RESTORE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return {"ok": True}


@router.delete("/{fid}")
def supprimer(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        try:
            formulaires.supprimer(conn, fid)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        conn.commit()
    log_action(user=user, action="DELETE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return {"ok": True}
