"""MySifa — Coffre RH côté comptabilité.

Endpoints réservés aux rôles comptabilité et superadmin :
- Dashboard mensuel bulletins × salariés
- Upload en masse (ZIP mensuel avec matching Bulletin_YYYY_MM_NOM_Prenom.pdf)
- Upload individuel (pour un cas ponctuel)
- Impression PDF concaténé de tous les bulletins d'un mois
- Validation / refus / marquage payée des notes de frais
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import unicodedata
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from config import BASE_DIR, NDF_TAUX_TVA, ROLE_COMPTABILITE, ROLE_SUPERADMIN
from database import get_db
from services.auth_service import get_current_user
from app.routers.coffre import (
    COFFRE_ROOT,
    ALLOWED_DOC_TYPES,
    ALLOWED_NDF_STATUTS,
    _log_doc_access,
    _sanitize_filename,
    ndf_categories,
    ndf_joindre_lignes,
)

router = APIRouter(tags=["rh_coffre"])


def _require_rh(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in {ROLE_COMPTABILITE, ROLE_SUPERADMIN}:
        raise HTTPException(403, "Accès réservé à la comptabilité")
    return user


def _norm(s: str) -> str:
    """Normalise un nom : sans accents, minuscules, alpha seulement."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _split_bulletin_name(fname: str) -> Optional[dict]:
    """Parse Bulletin_YYYY_MM_NOM_Prenom.pdf → dict ou None."""
    base = os.path.basename(fname)
    m = re.match(
        r"^Bulletin_(\d{4})_(\d{1,2})_(.+?)_(.+?)\.pdf$",
        base,
        re.IGNORECASE,
    )
    if not m:
        return None
    annee, mois, nom, prenom = m.groups()
    return {
        "annee": int(annee),
        "mois": int(mois),
        "nom": nom,
        "prenom": prenom,
        "match_key": _norm(nom + prenom),
    }


def _find_user_for_bulletin(conn, info: dict) -> Optional[dict]:
    """Cherche un user par matricule (dans le nom) ou par nom+prenom."""
    rows = conn.execute(
        "SELECT id,nom,email,matricule FROM users WHERE actif=1"
    ).fetchall()
    # 1) Matching par matricule si présent dans le fichier
    #    (le nom du fichier n'a pas de matricule dans le format demandé,
    #    mais si on trouve un chiffre uniquement dans nom ou prenom, on tente)
    for r in rows:
        if r["matricule"] and (
            info["nom"] == r["matricule"] or info["prenom"] == r["matricule"]
        ):
            return dict(r)
    # 2) Matching par concaténation nom + prénom normalisée
    for r in rows:
        target = _norm(r["nom"] or "")
        if target and (target == info["match_key"] or info["match_key"] in target
                       or target in info["match_key"]):
            return dict(r)
    return None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Compteurs portail (badge tuile) ─────────────────────────────────────

@router.get("/api/rh-coffre/badges")
def rh_coffre_badges(request: Request):
    """Compteur leger de NDF a traiter (statut=soumise).

    Utilise par la tuile portail Coffre RH pour afficher un badge.
    Reserve compta + superadmin.
    """
    _require_rh(request)
    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM notes_de_frais "
            "WHERE statut='soumise' AND deleted_at IS NULL"
        ).fetchone()[0]
    return {"ndf_soumises": int(count)}


# ── Documents RH — Dashboard ────────────────────────────────────────────

@router.get("/api/rh-coffre/employes")
def list_employes(request: Request):
    _require_rh(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id,nom,email,matricule,role,actif
               FROM users WHERE actif=1
               ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
    return {"employes": [dict(r) for r in rows]}


@router.get("/api/rh-coffre/dashboard")
def dashboard(request: Request, annee: int, mois: int):
    """Matrice users × statut pour un mois donné."""
    _require_rh(request)
    with get_db() as conn:
        users = conn.execute(
            """SELECT id,nom,email,matricule FROM users
               WHERE actif=1 ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
        docs = conn.execute(
            """SELECT id,employe_user_id,fichier_nom,taille_bytes,uploaded_at,
                      distribue_at,consulte_at
               FROM documents_rh
               WHERE type='bulletin_paie' AND annee=? AND mois=?
                 AND deleted_at IS NULL""",
            (annee, mois),
        ).fetchall()
    by_user: dict = {}
    for d in docs:
        by_user.setdefault(d["employe_user_id"], dict(d))
    lignes = []
    for u in users:
        ud = dict(u)
        d = by_user.get(u["id"])
        lignes.append({
            **ud,
            "document": d,
            "statut": (
                "consulté" if d and d.get("consulte_at")
                else "distribué" if d and d.get("distribue_at")
                else "déposé" if d
                else "manquant"
            ),
        })
    return {"annee": annee, "mois": mois, "lignes": lignes}


# ── Upload ─────────────────────────────────────────────────────────────

@router.post("/api/rh-coffre/upload-zip")
async def upload_zip_bulletins(request: Request, file: UploadFile = File(...)):
    """Upload d'un ZIP mensuel de bulletins avec matching auto par nom fichier."""
    user = _require_rh(request)
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Fichier ZIP attendu (.zip)")
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(400, "ZIP trop volumineux (max 100 Mo)")

    now = datetime.now().isoformat(timespec="seconds")
    matched: list = []
    unmatched: list = []
    skipped: list = []

    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Fichier ZIP invalide ou corrompu")

    with get_db() as conn:
        for member in zf.namelist():
            if member.endswith("/") or member.startswith("__MACOSX/"):
                continue
            name = os.path.basename(member)
            if not name.lower().endswith(".pdf"):
                skipped.append({"fichier": member, "raison": "non PDF"})
                continue
            info = _split_bulletin_name(name)
            if not info:
                unmatched.append({"fichier": name, "raison": "format nom fichier non reconnu"})
                continue
            emp = _find_user_for_bulletin(conn, info)
            if not emp:
                unmatched.append({"fichier": name, "raison": f"aucun user trouvé pour {info['nom']} {info['prenom']}"})
                continue
            with zf.open(member) as f:
                data = f.read()
            hash_ = _sha256_bytes(data)
            # Doublon exact déjà présent ?
            dup = conn.execute(
                """SELECT id FROM documents_rh
                   WHERE employe_user_id=? AND type='bulletin_paie'
                     AND annee=? AND mois=? AND hash_sha256=? AND deleted_at IS NULL""",
                (emp["id"], info["annee"], info["mois"], hash_),
            ).fetchone()
            if dup:
                skipped.append({"fichier": name, "raison": "déjà présent (hash identique)"})
                continue
            # Ecriture disque
            user_dir = COFFRE_ROOT / str(emp["id"])
            user_dir.mkdir(parents=True, exist_ok=True)
            safe = _sanitize_filename(name)
            fpath = user_dir / f"{uuid.uuid4().hex[:12]}_{safe}"
            with open(fpath, "wb") as out:
                out.write(data)
            cur = conn.execute(
                """INSERT INTO documents_rh
                   (employe_user_id,type,annee,mois,libelle,fichier_path,fichier_nom,
                    taille_bytes,hash_sha256,uploaded_by_user_id,uploaded_by_nom,uploaded_at,visible_salarie)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (
                    emp["id"], "bulletin_paie", info["annee"], info["mois"],
                    f"Bulletin {info['mois']:02d}/{info['annee']}",
                    str(fpath), name, len(data), hash_,
                    user.get("id"), (user.get("nom") or user.get("email") or "")[:120],
                    now,
                ),
            )
            matched.append({
                "fichier": name,
                "employe": emp["nom"],
                "id": cur.lastrowid,
            })
        conn.commit()

    return {
        "matched": matched,
        "unmatched": unmatched,
        "skipped": skipped,
        "total_matched": len(matched),
        "total_unmatched": len(unmatched),
    }


@router.post("/api/rh-coffre/upload-single")
async def upload_single_document(
    request: Request,
    employe_user_id: int = Form(...),
    type: str = Form(...),
    annee: str = Form(""),
    mois: str = Form(""),
    libelle: str = Form(""),
    fichier: UploadFile = File(...),
):
    """Upload individuel d'un document (bulletin, contrat, attestation, autre)."""
    user = _require_rh(request)
    if type not in ALLOWED_DOC_TYPES:
        raise HTTPException(400, f"Type invalide (attendu : {sorted(ALLOWED_DOC_TYPES)})")
    with get_db() as conn:
        emp = conn.execute(
            "SELECT id,nom FROM users WHERE id=?", (employe_user_id,)
        ).fetchone()
        if not emp:
            raise HTTPException(404, "Salarié introuvable")
    data = await fichier.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "Fichier > 25 Mo")
    annee_i = int(annee) if annee.strip() else None
    mois_i = int(mois) if mois.strip() else None
    user_dir = COFFRE_ROOT / str(employe_user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    safe = _sanitize_filename(fichier.filename or "document.pdf")
    fpath = user_dir / f"{uuid.uuid4().hex[:12]}_{safe}"
    with open(fpath, "wb") as out:
        out.write(data)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO documents_rh
               (employe_user_id,type,annee,mois,libelle,fichier_path,fichier_nom,
                taille_bytes,hash_sha256,uploaded_by_user_id,uploaded_by_nom,uploaded_at,visible_salarie)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                employe_user_id, type, annee_i, mois_i,
                (libelle or "").strip()[:180] or None,
                str(fpath), fichier.filename or safe, len(data), _sha256_bytes(data),
                user.get("id"), (user.get("nom") or user.get("email") or "")[:120],
                now,
            ),
        )
        conn.commit()
    return {"success": True, "id": cur.lastrowid}


# ── Impression concaténée ──────────────────────────────────────────────

@router.get("/api/rh-coffre/print")
def print_all_bulletins(
    request: Request, annee: int, mois: int, mark_distribue: str = "0"
):
    """Retourne un PDF unique concaténé de tous les bulletins du mois.
    Si mark_distribue=1, marque tous les docs concernés comme distribués.
    """
    user = _require_rh(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.id,d.fichier_path,d.fichier_nom,u.nom
               FROM documents_rh d
               JOIN users u ON u.id = d.employe_user_id
               WHERE d.type='bulletin_paie' AND d.annee=? AND d.mois=?
                 AND d.deleted_at IS NULL
               ORDER BY u.nom COLLATE NOCASE ASC""",
            (annee, mois),
        ).fetchall()
    if not rows:
        raise HTTPException(404, "Aucun bulletin pour ce mois")
    try:
        from pypdf import PdfWriter  # type: ignore
    except ImportError:
        raise HTTPException(500, "pypdf non installé sur le serveur")
    writer = PdfWriter()
    total_ok = 0
    for r in rows:
        path = Path(r["fichier_path"])
        if not path.is_file():
            continue
        try:
            writer.append(str(path))
            total_ok += 1
        except Exception:
            continue
    if total_ok == 0:
        raise HTTPException(500, "Aucun bulletin lisible")
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    do_mark = str(mark_distribue).strip() in {"1", "true", "yes"}
    if do_mark:
        now = datetime.now().isoformat(timespec="seconds")
        with get_db() as conn:
            conn.execute(
                """UPDATE documents_rh SET distribue_at=?
                   WHERE type='bulletin_paie' AND annee=? AND mois=?
                     AND deleted_at IS NULL AND distribue_at IS NULL""",
                (now, annee, mois),
            )
            for r in rows:
                _log_doc_access(
                    conn, r["id"], user, "print",
                    request.client.host if request.client else None,
                )
            conn.commit()

    filename = f"bulletins_{annee}_{mois:02d}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/rh-coffre/mark-distributed")
async def mark_distributed(request: Request):
    """Marque les bulletins d'un mois comme distribués (sans impression)."""
    _require_rh(request)
    body = await request.json()
    annee = int(body.get("annee") or 0)
    mois = int(body.get("mois") or 0)
    if not (annee and 1 <= mois <= 12):
        raise HTTPException(400, "Année/mois requis")
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE documents_rh SET distribue_at=?
               WHERE type='bulletin_paie' AND annee=? AND mois=?
                 AND deleted_at IS NULL AND distribue_at IS NULL""",
            (now, annee, mois),
        )
        conn.commit()
    return {"success": True, "marked": cur.rowcount}


@router.delete("/api/rh-coffre/documents/{doc_id}")
def delete_document(doc_id: int, request: Request):
    user = _require_rh(request)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM documents_rh WHERE id=? AND deleted_at IS NULL",
            (doc_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Document introuvable")
        conn.execute(
            "UPDATE documents_rh SET deleted_at=?, deleted_by_nom=? WHERE id=?",
            (now, (user.get("nom") or user.get("email") or "")[:120], doc_id),
        )
        conn.commit()
    return {"success": True}


# ── Notes de frais côté compta ─────────────────────────────────────────

@router.get("/api/rh-coffre/ndf")
def list_all_ndf(request: Request, statut: str = "", annee: str = ""):
    _require_rh(request)
    where = ["n.deleted_at IS NULL"]
    params: list = []
    if statut and statut in ALLOWED_NDF_STATUTS:
        where.append("n.statut=?")
        params.append(statut)
    if annee.strip():
        where.append("strftime('%Y', n.date_frais)=?")
        params.append(annee.strip())
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT n.*, u.nom AS employe_nom, u.email AS employe_email
                FROM notes_de_frais n
                JOIN users u ON u.id = n.employe_user_id
                WHERE {' AND '.join(where)}
                ORDER BY
                  CASE n.statut
                    WHEN 'soumise' THEN 0
                    WHEN 'validee' THEN 1
                    WHEN 'brouillon' THEN 2
                    WHEN 'payee' THEN 3
                    WHEN 'refusee' THEN 4
                    ELSE 5 END,
                  n.date_frais DESC, n.id DESC""",
            params,
        ).fetchall()
        notes = ndf_joindre_lignes(conn, [dict(r) for r in rows])
    return {"notes": notes}


@router.post("/api/rh-coffre/ndf/{ndf_id}/valider")
def valider_ndf(ndf_id: int, request: Request):
    user = _require_rh(request)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        if row["statut"] not in {"soumise", "refusee"}:
            raise HTTPException(400, "Note non validable dans son statut actuel")
        conn.execute(
            """UPDATE notes_de_frais
               SET statut='validee', validee_at=?, validee_by_user_id=?, validee_by_nom=?,
                   motif_refus=NULL
               WHERE id=?""",
            (
                now, user.get("id"),
                (user.get("nom") or user.get("email") or "")[:120],
                ndf_id,
            ),
        )
        conn.commit()
    return {"success": True}


@router.post("/api/rh-coffre/ndf/{ndf_id}/refuser")
async def refuser_ndf(ndf_id: int, request: Request):
    user = _require_rh(request)
    body = await request.json()
    motif = (body.get("motif") or "").strip()
    if not motif:
        raise HTTPException(400, "Motif de refus requis")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        conn.execute(
            "UPDATE notes_de_frais SET statut='refusee', motif_refus=? WHERE id=?",
            (motif[:400], ndf_id),
        )
        conn.commit()
    return {"success": True}


@router.post("/api/rh-coffre/ndf/{ndf_id}/marquer-payee")
def marquer_payee(ndf_id: int, request: Request):
    user = _require_rh(request)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        if row["statut"] != "validee":
            raise HTTPException(400, "Note doit être au statut 'validée' avant marquage payée")
        conn.execute(
            """UPDATE notes_de_frais SET statut='payee', payee_at=?,
                                          payee_by_user_id=?, payee_by_nom=?
               WHERE id=?""",
            (
                now, user.get("id"),
                (user.get("nom") or user.get("email") or "")[:120],
                ndf_id,
            ),
        )
        conn.commit()
    return {"success": True}


# ── Catégories de notes de frais (référentiel de la compta) ────────────
# Réglages > Catégories enregistre la liste entière d'un coup (PUT). Une
# catégorie retirée de la liste est désactivée, pas effacée : les notes qui la
# portent gardent leur libellé et leurs montants, et l'export reste juste.

def _categorie_valide(item: dict, saisie: str) -> dict:
    """Champs d'une catégorie de la liste, validés. `saisie` est figée pour
    une catégorie existante : on ne transforme pas des notes en euros en km."""
    libelle = str(item.get("libelle") or "").strip()[:60]
    if not libelle:
        raise HTTPException(400, "Libellé requis pour chaque catégorie.")
    if saisie not in {"montant", "km"}:
        raise HTTPException(400, f"{libelle} : saisie invalide — montant ou km.")
    if saisie == "km":
        v = item.get("taux_km")
        try:
            taux_km = float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            raise HTTPException(400, f"{libelle} : taux kilométrique requis.")
        if taux_km <= 0 or taux_km > 5:
            raise HTTPException(400, f"{libelle} : taux kilométrique entre 0 et 5 € par km.")
        return {"libelle": libelle, "saisie": "km", "taux_tva": 0.0, "taux_km": taux_km}
    try:
        taux = float(item.get("taux_tva"))
    except (TypeError, ValueError):
        raise HTTPException(400, f"{libelle} : taux de TVA invalide.")
    if taux not in NDF_TAUX_TVA:
        raise HTTPException(400, f"{libelle} : taux de TVA invalide.")
    return {"libelle": libelle, "saisie": "montant", "taux_tva": taux, "taux_km": None}


@router.get("/api/rh-coffre/ndf-categories")
def list_ndf_categories_rh(request: Request):
    _require_rh(request)
    with get_db() as conn:
        cats = ndf_categories(conn)
        usages = dict(conn.execute(
            """SELECT categorie_id, COUNT(*) FROM notes_de_frais
               WHERE categorie_id IS NOT NULL AND deleted_at IS NULL
               GROUP BY categorie_id"""
        ).fetchall())
    for c in cats:
        c["nb_notes"] = usages.get(c["id"], 0)
    return {"categories": cats, "taux_tva": list(NDF_TAUX_TVA)}


@router.put("/api/rh-coffre/ndf-categories")
async def save_ndf_categories(request: Request):
    """Enregistre la liste complète, dans l'ordre affiché. Tout est validé
    avant la première écriture : une erreur ne laisse rien à moitié fait."""
    _require_rh(request)
    body = await request.json()
    items = body.get("categories")
    if not isinstance(items, list) or not items:
        raise HTTPException(400, "Au moins une catégorie est requise.")
    with get_db() as conn:
        existantes = {r["id"]: dict(r) for r in conn.execute(
            "SELECT id,saisie FROM ndf_categories WHERE actif=1"
        ).fetchall()}
        lignes, vus = [], set()
        for item in items:
            cid = item.get("id")
            if cid is not None:
                if cid not in existantes:
                    raise HTTPException(400, "Catégorie inconnue — rechargez les réglages.")
                champs = _categorie_valide(item, existantes[cid]["saisie"])
            else:
                champs = _categorie_valide(item, item.get("saisie") or "montant")
            cle = champs["libelle"].casefold()
            if cle in vus:
                raise HTTPException(400, f"Deux catégories s'appellent « {champs['libelle']} ».")
            vus.add(cle)
            lignes.append((cid, champs))

        gardees = {cid for cid, _ in lignes if cid is not None}
        for cid in existantes:
            if cid not in gardees:
                conn.execute("UPDATE ndf_categories SET actif=0 WHERE id=?", (cid,))
        for i, (cid, champs) in enumerate(lignes):
            ordre = (i + 1) * 10
            if cid is not None:
                conn.execute(
                    """UPDATE ndf_categories SET libelle=?, taux_tva=?, taux_km=?, ordre=?
                       WHERE id=?""",
                    (champs["libelle"], champs["taux_tva"], champs["taux_km"], ordre, cid),
                )
            else:
                conn.execute(
                    """INSERT INTO ndf_categories (code,libelle,saisie,taux_tva,taux_km,ordre)
                       VALUES (?,?,?,?,?,?)""",
                    ("cat_" + uuid.uuid4().hex[:8], champs["libelle"], champs["saisie"],
                     champs["taux_tva"], champs["taux_km"], ordre),
                )
        conn.commit()
    return {"success": True}


def _rubrique_feuille(categorie: str, taux, km: bool) -> str:
    """Colonne de la feuille de frais Excel : « Repas à 10% », « KM »…"""
    if km:
        return "KM"
    libelle = categorie or ""
    if taux is None:
        return libelle
    if not taux:
        return f"{libelle} sans TVA"
    return f"{libelle} à {taux:g}%".replace(".", ",")


@router.get("/api/rh-coffre/ndf/export")
def export_ndf_csv(request: Request, annee: str = "", statut: str = ""):
    """Export CSV des notes de frais (filtrable). Pour intégration compta.

    Une ligne par taux de TVA : un ticket de restaurant à 10 % et 20 % donne
    deux lignes, chacune avec ses propres HT, TVA et TTC, et le même id de
    note. `ligne` les numérote (« 1/2 ») et `montant_ttc_note` rappelle le
    total du ticket. Une indemnité kilométrique tient sur une ligne.
    """
    _require_rh(request)
    where = ["n.deleted_at IS NULL"]
    params: list = []
    if statut and statut in ALLOWED_NDF_STATUTS:
        where.append("n.statut=?")
        params.append(statut)
    if annee.strip():
        where.append("strftime('%Y', n.date_frais)=?")
        params.append(annee.strip())
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT n.id,u.nom AS employe,u.matricule,n.date_frais,n.categorie,
                       n.ville,n.distance_km,n.taux_km,n.taux_tva,
                       n.montant_ht,n.montant_tva,n.montant_ttc,n.description,n.statut,
                       n.soumise_at,n.validee_at,n.validee_by_nom,
                       n.payee_at,n.payee_by_nom,n.motif_refus
                FROM notes_de_frais n
                JOIN users u ON u.id = n.employe_user_id
                WHERE {' AND '.join(where)}
                ORDER BY n.date_frais DESC, n.id DESC""",
            params,
        ).fetchall()
        notes = ndf_joindre_lignes(conn, [dict(r) for r in rows])

    def txt(v):
        return "" if v is None else str(v)

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([
        "id", "ligne", "salarie", "matricule", "date_frais", "categorie", "rubrique_feuille",
        "ville", "distance_km", "taux_km", "taux_tva",
        "montant_ht", "montant_tva", "montant_ttc", "montant_ttc_note", "description", "statut",
        "soumise_at", "validee_at", "validee_par", "payee_at", "payee_par", "motif_refus",
    ])
    for n in notes:
        km = n["distance_km"] is not None
        lignes = n["tva_lignes"] or [{
            "taux_tva": n["taux_tva"], "montant_ht": n["montant_ht"],
            "montant_tva": n["montant_tva"], "montant_ttc": n["montant_ttc"],
        }]
        for i, l in enumerate(lignes, start=1):
            w.writerow([txt(v) for v in (
                n["id"], f"{i}/{len(lignes)}", n["employe"], n["matricule"], n["date_frais"],
                n["categorie"], _rubrique_feuille(n["categorie"], l["taux_tva"], km),
                n["ville"], n["distance_km"], n["taux_km"], l["taux_tva"],
                l["montant_ht"], l["montant_tva"], l["montant_ttc"], n["montant_ttc"],
                n["description"], n["statut"], n["soumise_at"], n["validee_at"],
                n["validee_by_nom"], n["payee_at"], n["payee_by_nom"], n["motif_refus"],
            )])
    buf.seek(0)
    filename = f"notes_de_frais_{annee or 'toutes'}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
