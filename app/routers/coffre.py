"""MySifa — Coffre RH côté salarié.

Endpoints pour un utilisateur connecté (tous rôles) : consultation de ses
propres bulletins de paie et gestion de ses notes de frais (dépôt, soumission,
suppression brouillon). L'accès aux fichiers est strictement limité au
propriétaire ou aux rôles compta/superadmin (partagés avec /rh/coffre).

Coffre interne SIFA — pas de valeur légale opposable, le bulletin officiel
reste celui remis en main propre / par email par la comptabilité.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config import BASE_DIR, NDF_TAUX_TVA, ROLE_COMPTABILITE, ROLE_SUPERADMIN
from database import get_db
from services.auth_service import get_current_user


router = APIRouter(tags=["coffre"])

COFFRE_ROOT = Path(BASE_DIR) / "data" / "uploads" / "coffre_rh"
COFFRE_ROOT.mkdir(parents=True, exist_ok=True)

NDF_ROOT = Path(BASE_DIR) / "data" / "uploads" / "ndf_justificatifs"
NDF_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_DOC_TYPES = {"bulletin_paie", "contrat", "attestation", "autre"}
ALLOWED_NDF_STATUTS = {"brouillon", "soumise", "validee", "payee", "refusee"}

MAX_JUSTIFICATIF_MB = 10
MAX_JUSTIFICATIF_BYTES = MAX_JUSTIFICATIF_MB * 1024 * 1024


def _is_compta_or_super(user: dict) -> bool:
    return user.get("role") in {ROLE_COMPTABILITE, ROLE_SUPERADMIN}


def _log_doc_access(conn, doc_id: int, user: dict, action: str, ip: Optional[str]) -> None:
    conn.execute(
        """INSERT INTO documents_rh_access_log
           (document_id,user_id,user_nom,action,ip,created_at)
           VALUES (?,?,?,?,?,?)""",
        (
            doc_id,
            user.get("id"),
            (user.get("nom") or user.get("email") or "")[:120],
            action,
            (ip or "")[:64],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )


def _sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "")
    base = re.sub(r"[^A-Za-z0-9._\-]", "_", base)
    return base[:120] or "fichier"


# ── Documents RH (bulletins, contrats, attestations) — vue salarié ──────

@router.get("/api/coffre/documents")
def list_my_documents(request: Request, annee: Optional[int] = None, type: Optional[str] = None):
    """Liste des documents visibles par le salarié connecté."""
    user = get_current_user(request)
    uid = user.get("id")
    where = ["employe_user_id=?", "deleted_at IS NULL", "visible_salarie=1"]
    params: list = [uid]
    if annee:
        where.append("annee=?")
        params.append(int(annee))
    if type and type in ALLOWED_DOC_TYPES:
        where.append("type=?")
        params.append(type)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT id,type,annee,mois,libelle,fichier_nom,taille_bytes,
                       uploaded_at,distribue_at,consulte_at
                FROM documents_rh
                WHERE {' AND '.join(where)}
                ORDER BY annee DESC, mois DESC, uploaded_at DESC""",
            params,
        ).fetchall()
        # Regroupement par année pour l'affichage
        annees = conn.execute(
            """SELECT DISTINCT annee FROM documents_rh
               WHERE employe_user_id=? AND deleted_at IS NULL AND visible_salarie=1
               AND annee IS NOT NULL
               ORDER BY annee DESC""",
            (uid,),
        ).fetchall()
    return {
        "documents": [dict(r) for r in rows],
        "annees_disponibles": [r["annee"] for r in annees],
    }


@router.get("/api/coffre/documents/{doc_id}/download")
def download_document(doc_id: int, request: Request, inline: bool = False):
    """Télécharge ou prévisualise (?inline=1) un document RH.

    Propriétaire ou compta/superadmin uniquement. En mode inline, sert le
    fichier avec Content-Disposition: inline pour affichage dans iframe/img.
    """
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id,employe_user_id,fichier_path,fichier_nom,deleted_at
               FROM documents_rh WHERE id=?""",
            (doc_id,),
        ).fetchone()
        if not row or row["deleted_at"]:
            raise HTTPException(404, "Document introuvable")
        d = dict(row)
        if d["employe_user_id"] != user.get("id") and not _is_compta_or_super(user):
            raise HTTPException(403, "Accès refusé")
        # Marquage première consultation
        conn.execute(
            "UPDATE documents_rh SET consulte_at=COALESCE(consulte_at,?) WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), doc_id),
        )
        _log_doc_access(
            conn, doc_id, user, "preview" if inline else "download",
            request.client.host if request.client else None,
        )
        conn.commit()
    path = Path(d["fichier_path"])
    if not path.is_file():
        raise HTTPException(410, "Fichier absent du serveur")
    fname = d["fichier_nom"] or path.name
    mime, _ = mimetypes.guess_type(fname)
    if not mime:
        mime = "application/pdf"
    if inline:
        # Content-Disposition: inline → aperçu dans le navigateur (iframe/img)
        return FileResponse(
            str(path),
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{fname}"'},
        )
    return FileResponse(str(path), filename=fname, media_type=mime)


# ── Notes de frais — vue salarié (dépôt + workflow) ──────────────────────

def ndf_categories(conn, toutes: bool = False) -> list:
    """Catégories de notes de frais, actives seulement sauf `toutes`."""
    where = "" if toutes else "WHERE actif=1"
    rows = conn.execute(
        f"""SELECT id,code,libelle,saisie,taux_tva,taux_km,ordre,actif
            FROM ndf_categories {where} ORDER BY ordre, libelle"""
    ).fetchall()
    return [dict(r) for r in rows]


NDF_MAX_LIGNES_TVA = 6


def ndf_lignes_tva(lignes: list) -> dict:
    """Ventilation de la TVA d'une note : une ligne par taux, telle qu'imprimée
    sur le ticket. Chaque ligne donne son TTC et, si elle est connue, sa TVA
    (sinon déduite du taux). Rend les lignes validées et les totaux de la note.
    Même calcul que `ndfLigneCalcul()` de la page."""
    if not isinstance(lignes, list) or not lignes:
        raise HTTPException(400, "Montant manquant — au moins une ligne de TVA.")
    if len(lignes) > NDF_MAX_LIGNES_TVA:
        raise HTTPException(400, f"Au plus {NDF_MAX_LIGNES_TVA} taux de TVA par note.")
    propres, vus = [], set()
    for l in lignes:
        try:
            taux = float(l.get("taux"))
            ttc = round(float(str(l.get("ttc")).replace(",", ".")), 2)
        except (TypeError, ValueError, AttributeError):
            raise HTTPException(400, "Ligne de TVA invalide — taux et montant TTC attendus.")
        if taux not in NDF_TAUX_TVA:
            raise HTTPException(400, "Taux de TVA invalide.")
        if taux in vus:
            raise HTTPException(400, "Deux lignes au même taux de TVA — regroupez-les.")
        vus.add(taux)
        if ttc <= 0:
            raise HTTPException(400, "Montant TTC invalide — valeur supérieure à 0.")
        brut = l.get("tva")
        if brut in (None, ""):
            tva = round(ttc - ttc / (1 + taux / 100), 2)
        else:
            try:
                tva = round(float(str(brut).replace(",", ".")), 2)
            except ValueError:
                raise HTTPException(400, "TVA invalide — nombre attendu.")
        if tva < 0 or (tva >= ttc and ttc > 0) or (taux == 0 and tva != 0):
            raise HTTPException(400, "TVA invalide — doit rester inférieure au montant TTC.")
        propres.append({"taux_tva": taux, "montant_ttc": ttc, "montant_tva": tva,
                        "montant_ht": round(ttc - tva, 2)})
    tot_ttc = round(sum(l["montant_ttc"] for l in propres), 2)
    tot_tva = round(sum(l["montant_tva"] for l in propres), 2)
    return {
        "lignes": propres,
        "montant_ttc": tot_ttc,
        "montant_tva": tot_tva,
        "montant_ht": round(tot_ttc - tot_tva, 2),
        # Un seul taux : il qualifie la note. Plusieurs : ce sont les lignes.
        "taux_tva": propres[0]["taux_tva"] if len(propres) == 1 else None,
    }


def ndf_montants(saisie: str, montant_ttc: Optional[float], taux_tva: float,
                 montant_tva: Optional[float], distance_km: Optional[float],
                 taux_km: Optional[float]) -> dict:
    """TTC, TVA et HT d'une note saisie sur une seule ligne.

    Kilométrique : TTC = distance × taux, sans TVA ni ligne de TVA. Sinon la
    note n'a qu'un taux : c'est une ventilation à une ligne.
    """
    if saisie == "km":
        if not distance_km or distance_km <= 0:
            raise HTTPException(400, "Distance invalide — nombre de km supérieur à 0.")
        if not taux_km or taux_km <= 0:
            raise HTTPException(400, "Taux kilométrique non défini — à régler par la comptabilité dans Coffre RH › Notes de frais › Réglages.")
        ttc = round(distance_km * taux_km, 2)
        return {"montant_ttc": ttc, "montant_tva": 0.0, "montant_ht": ttc, "taux_tva": 0.0, "lignes": []}
    if montant_ttc is None or montant_ttc <= 0:
        raise HTTPException(400, "Montant TTC invalide — valeur supérieure à 0.")
    return ndf_lignes_tva([{"taux": taux_tva, "ttc": montant_ttc, "tva": montant_tva}])


def ndf_joindre_lignes(conn, notes: list) -> list:
    """Ajoute à chaque note (dict) sa ventilation `tva_lignes`."""
    ids = [n["id"] for n in notes]
    par_note: dict = {i: [] for i in ids}
    for i in range(0, len(ids), 500):
        lot = ids[i:i + 500]
        if not lot:
            continue
        for r in conn.execute(
            f"""SELECT note_id,taux_tva,montant_ttc,montant_tva,montant_ht
                FROM notes_de_frais_tva WHERE note_id IN ({','.join('?' * len(lot))})
                ORDER BY note_id, ordre, id""",
            lot,
        ).fetchall():
            par_note[r["note_id"]].append({k: r[k] for k in ("taux_tva", "montant_ttc", "montant_tva", "montant_ht")})
    for n in notes:
        n["tva_lignes"] = par_note.get(n["id"], [])
    return notes


def _ecrire_lignes(conn, note_id: int, lignes: list) -> None:
    conn.execute("DELETE FROM notes_de_frais_tva WHERE note_id=?", (note_id,))
    for i, l in enumerate(lignes):
        conn.execute(
            """INSERT INTO notes_de_frais_tva
               (note_id,ordre,taux_tva,montant_ttc,montant_tva,montant_ht) VALUES (?,?,?,?,?,?)""",
            (note_id, i, l["taux_tva"], l["montant_ttc"], l["montant_tva"], l["montant_ht"]),
        )


def _nombre_ou_none(v: str, quoi: str) -> Optional[float]:
    v = (v or "").strip().replace(",", ".")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        raise HTTPException(400, f"{quoi} invalide — nombre attendu.")


@router.post("/api/coffre/notes-frais/scan")
async def scan_justificatif(request: Request, justificatif: UploadFile = File(...)):
    """Lit un justificatif et propose les champs de la note (rien n'est
    enregistré). Le fichier est renvoyé avec la note à l'enregistrement."""
    from app.services import ia_usage
    from app.services.ndf_scan import lire_justificatif

    user = get_current_user(request)
    contenu = await justificatif.read()
    if not contenu:
        raise HTTPException(400, "Fichier vide.")
    if len(contenu) > MAX_JUSTIFICATIF_BYTES:
        raise HTTPException(400, f"Justificatif > {MAX_JUSTIFICATIF_MB} Mo")
    mime = (justificatif.content_type or "").lower()
    if not mime or mime == "application/octet-stream":
        mime = (mimetypes.guess_type(justificatif.filename or "")[0] or "").lower()
    with get_db() as conn:
        cats = [c for c in ndf_categories(conn) if c["saisie"] == "montant"]
    with ia_usage.suivi(user, "ndf", "coffre"):
        return lire_justificatif(contenu, mime, cats)


@router.get("/api/coffre/ndf-categories")
def list_ndf_categories(request: Request):
    get_current_user(request)
    with get_db() as conn:
        cats = ndf_categories(conn)
    return {"categories": cats, "taux_tva": list(NDF_TAUX_TVA)}


@router.get("/api/coffre/notes-frais")
def list_my_ndf(request: Request, annee: Optional[int] = None):
    user = get_current_user(request)
    uid = user.get("id")
    where = ["employe_user_id=?", "deleted_at IS NULL"]
    params: list = [uid]
    if annee:
        where.append("strftime('%Y', date_frais)=?")
        params.append(str(annee))
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT id,date_frais,categorie,categorie_id,montant_ttc,montant_tva,
                       montant_ht,taux_tva,distance_km,taux_km,ville,description,
                       justificatif_nom,statut,created_at,soumise_at,validee_at,
                       validee_by_nom,payee_at,motif_refus
                FROM notes_de_frais
                WHERE {' AND '.join(where)}
                ORDER BY date_frais DESC, id DESC""",
            params,
        ).fetchall()
        notes = ndf_joindre_lignes(conn, [dict(r) for r in rows])
    return {"notes": notes}


def _ndf_champs(date_frais: str, categorie_id: int, montant_ttc: str, taux_tva: str,
                montant_tva: str, distance_km: str, ville: str, description: str,
                tva_lignes: str = "") -> dict:
    """Valide une saisie de note et rend les colonnes à écrire (création et
    modification d'un brouillon passent par ici). La ventilation par taux
    part sous la clé `_lignes`, à écrire dans notes_de_frais_tva.

    `tva_lignes` (JSON : [{taux, ttc, tva}]) l'emporte sur montant_ttc /
    taux_tva / montant_tva, qui restent acceptés pour une note à un taux."""
    try:
        datetime.fromisoformat(date_frais[:10])
    except ValueError:
        raise HTTPException(400, "Date invalide (format YYYY-MM-DD attendu)")
    with get_db() as conn:
        cat = conn.execute(
            "SELECT id,libelle,saisie,taux_tva,taux_km FROM ndf_categories WHERE id=? AND actif=1",
            (categorie_id,),
        ).fetchone()
    if not cat:
        raise HTTPException(400, "Catégorie inconnue — choisir dans la liste.")
    taux = _nombre_ou_none(taux_tva, "Taux de TVA")
    if taux is None:
        taux = float(cat["taux_tva"])
    if taux not in NDF_TAUX_TVA:
        raise HTTPException(400, "Taux de TVA invalide.")
    if cat["saisie"] == "montant" and (tva_lignes or "").strip():
        try:
            brutes = json.loads(tva_lignes)
        except ValueError:
            raise HTTPException(400, "Lignes de TVA illisibles.")
        m = ndf_lignes_tva(brutes)
    else:
        m = ndf_montants(
            cat["saisie"],
            _nombre_ou_none(montant_ttc, "Montant TTC"),
            taux,
            _nombre_ou_none(montant_tva, "TVA"),
            _nombre_ou_none(distance_km, "Distance"),
            cat["taux_km"],
        )
    lignes = m.pop("lignes")
    est_km = cat["saisie"] == "km"
    return {
        "date_frais": date_frais[:10],
        "categorie": cat["libelle"],
        "categorie_id": cat["id"],
        **m,
        "distance_km": _nombre_ou_none(distance_km, "Distance") if est_km else None,
        "taux_km": cat["taux_km"] if est_km else None,
        "ville": (ville or "").strip()[:80] or None,
        "description": (description or "").strip()[:1000],
        "_lignes": lignes,
    }


async def _ndf_justificatif(uid, justificatif: Optional[UploadFile]) -> Optional[tuple]:
    """Enregistre le justificatif envoyé ; (chemin, nom) ou None sans fichier."""
    if justificatif is None or not justificatif.filename:
        return None
    allowed_ct = {"image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"}
    ct = (justificatif.content_type or "").lower()
    if ct not in allowed_ct:
        raise HTTPException(400, "Format justificatif : PDF, JPG, PNG, WEBP, HEIC uniquement")
    content = await justificatif.read()
    if len(content) > MAX_JUSTIFICATIF_BYTES:
        raise HTTPException(400, f"Justificatif > {MAX_JUSTIFICATIF_MB} Mo")
    user_dir = NDF_ROOT / str(uid)
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(justificatif.filename)
    dest = user_dir / f"{uuid.uuid4().hex[:12]}_{safe_name}"
    with open(dest, "wb") as f:
        f.write(content)
    return str(dest), justificatif.filename[:180]


@router.post("/api/coffre/notes-frais")
async def create_ndf(
    request: Request,
    date_frais: str = Form(...),
    categorie_id: int = Form(...),
    montant_ttc: str = Form(""),
    taux_tva: str = Form(""),
    montant_tva: str = Form(""),
    distance_km: str = Form(""),
    ville: str = Form(""),
    description: str = Form(""),
    tva_lignes: str = Form(""),
    soumettre: str = Form("0"),
    justificatif: Optional[UploadFile] = File(None),
):
    """Créer une note de frais. Si soumettre=1, statut=soumise directement."""
    user = get_current_user(request)
    uid = user.get("id")
    champs = _ndf_champs(date_frais, categorie_id, montant_ttc, taux_tva,
                         montant_tva, distance_km, ville, description, tva_lignes)
    lignes = champs.pop("_lignes")
    just = await _ndf_justificatif(uid, justificatif)
    if just:
        champs["justificatif_path"], champs["justificatif_nom"] = just

    do_soumettre = str(soumettre).strip() in {"1", "true", "yes"}
    now = datetime.now().isoformat(timespec="seconds")
    champs.update({
        "employe_user_id": uid,
        "statut": "soumise" if do_soumettre else "brouillon",
        "created_at": now,
        "soumise_at": now if do_soumettre else None,
    })
    with get_db() as conn:
        cur = conn.execute(
            f"""INSERT INTO notes_de_frais ({','.join(champs)})
                VALUES ({','.join('?' * len(champs))})""",
            list(champs.values()),
        )
        _ecrire_lignes(conn, cur.lastrowid, lignes)
        conn.commit()
    return {"success": True, "id": cur.lastrowid, "statut": champs["statut"]}


@router.put("/api/coffre/notes-frais/{ndf_id}")
async def update_ndf(
    ndf_id: int,
    request: Request,
    date_frais: str = Form(...),
    categorie_id: int = Form(...),
    montant_ttc: str = Form(""),
    taux_tva: str = Form(""),
    montant_tva: str = Form(""),
    distance_km: str = Form(""),
    ville: str = Form(""),
    description: str = Form(""),
    tva_lignes: str = Form(""),
    soumettre: str = Form("0"),
    justificatif: Optional[UploadFile] = File(None),
):
    """Modifier un brouillon (le sien uniquement). Sans nouveau fichier, le
    justificatif déjà joint est conservé. soumettre=1 l'envoie à la compta."""
    user = get_current_user(request)
    uid = user.get("id")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,employe_user_id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Note introuvable")
    if row["employe_user_id"] != uid:
        raise HTTPException(403, "Accès refusé")
    if row["statut"] != "brouillon":
        raise HTTPException(400, "Note déjà soumise — elle n'est plus modifiable.")
    champs = _ndf_champs(date_frais, categorie_id, montant_ttc, taux_tva,
                         montant_tva, distance_km, ville, description, tva_lignes)
    lignes = champs.pop("_lignes")
    just = await _ndf_justificatif(uid, justificatif)
    if just:
        champs["justificatif_path"], champs["justificatif_nom"] = just
    if str(soumettre).strip() in {"1", "true", "yes"}:
        champs["statut"] = "soumise"
        champs["soumise_at"] = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            f"""UPDATE notes_de_frais SET {', '.join(k + '=?' for k in champs)}
                WHERE id=? AND statut='brouillon'""",
            list(champs.values()) + [ndf_id],
        )
        if cur.rowcount:
            _ecrire_lignes(conn, ndf_id, lignes)
        conn.commit()
    return {"success": True, "id": ndf_id, "statut": champs.get("statut", "brouillon")}


@router.post("/api/coffre/notes-frais/{ndf_id}/soumettre")
def submit_ndf(ndf_id: int, request: Request):
    """Soumet un brouillon à la compta. Une fois soumise, non modifiable côté salarié."""
    user = get_current_user(request)
    uid = user.get("id")
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,employe_user_id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        if row["employe_user_id"] != uid:
            raise HTTPException(403, "Accès refusé")
        if row["statut"] != "brouillon":
            raise HTTPException(400, "Seuls les brouillons peuvent être soumis")
        conn.execute(
            "UPDATE notes_de_frais SET statut='soumise', soumise_at=? WHERE id=?",
            (now, ndf_id),
        )
        conn.commit()
    return {"success": True}


@router.delete("/api/coffre/notes-frais/{ndf_id}")
def delete_ndf(ndf_id: int, request: Request):
    """Suppression logique — brouillons uniquement côté salarié."""
    user = get_current_user(request)
    uid = user.get("id")
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,employe_user_id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        if row["employe_user_id"] != uid and not _is_compta_or_super(user):
            raise HTTPException(403, "Accès refusé")
        if row["statut"] != "brouillon" and not _is_compta_or_super(user):
            raise HTTPException(400, "Seuls les brouillons peuvent être supprimés par le salarié")
        conn.execute(
            "UPDATE notes_de_frais SET deleted_at=? WHERE id=?",
            (now, ndf_id),
        )
        conn.commit()
    return {"success": True}


@router.get("/api/coffre/notes-frais/{ndf_id}/justificatif")
def download_ndf_justificatif(ndf_id: int, request: Request, inline: bool = False):
    """Télécharge ou prévisualise (?inline=1) le justificatif d'une note de frais.

    Propriétaire ou compta/superadmin uniquement.
    """
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id,employe_user_id,justificatif_path,justificatif_nom
               FROM notes_de_frais WHERE id=? AND deleted_at IS NULL""",
            (ndf_id,),
        ).fetchone()
        if not row or not row["justificatif_path"]:
            raise HTTPException(404, "Justificatif introuvable")
        if row["employe_user_id"] != user.get("id") and not _is_compta_or_super(user):
            raise HTTPException(403, "Accès refusé")
    path = Path(row["justificatif_path"])
    if not path.is_file():
        raise HTTPException(410, "Fichier absent du serveur")
    fname = row["justificatif_nom"] or path.name
    mime, _ = mimetypes.guess_type(fname)
    if not mime:
        mime = "application/octet-stream"
    if inline:
        return FileResponse(
            str(path),
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{fname}"'},
        )
    return FileResponse(str(path), filename=fname, media_type=mime)
