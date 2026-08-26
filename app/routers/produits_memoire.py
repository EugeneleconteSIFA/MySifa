"""MySifa — Memoire produit.

Routes /api/produits/* : la fiche d'une reference produit (series passees,
scans d'OF termines, savoirs d'atelier) et les points d'entree qui l'ouvrent
depuis Saisieprod et depuis MyProd.

Trois principes tenus par ce module :

1. **Rien ne bloque une saisie de production.** Les appels declenches par la
   fabrication sont best-effort cote appelant ; ici on se contente de ne
   jamais lever pour une raison qui ne concerne pas la lecture demandee.
2. **Un savoir ne se supprime pas, il se perime.** `obsolete=1` garde la trace
   d'un reglage qui ne vaut plus — l'effacer laisserait quelqu'un le
   redecouvrir.
3. **Un scan ne se supprime pas non plus.** `statut='ecarte'` pour un document
   illisible ou hors sujet.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Header, Request, UploadFile
from fastapi.responses import FileResponse

from config import UPLOAD_DIR
from database import get_db
from app.services.audit_service import log_action
from app.services.auth_service import (
    get_current_user, is_admin, is_superadmin, require_superadmin,
)
from app.services import produit_memoire as pm

router = APIRouter()

SCAN_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "of_scans")

# Numero d'OF SIFA : meme pre-filtre que le pont Access et que l'import PDF.
_OF_RACINE_RE = re.compile(r"\b(99\d{5})\b")
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _user_login(user: dict) -> str:
    return str(user.get("email") or user.get("nom") or user.get("id") or "?")


def _auteur(user: dict) -> str:
    return str(user.get("nom") or user.get("email") or "?")


def _ref_ou_404(ref: str) -> str:
    r = (ref or "").strip()
    if not r:
        raise HTTPException(status_code=400, detail="Reference produit requise.")
    return r


# ─── Fiche produit ────────────────────────────────────────────────────────────

@router.get("/api/produits")
def liste_produits(request: Request, q: str = "", machine: str = "",
                   min_series: int = 1, limit: int = 200):
    """Liste des references ayant au moins une serie materialisee."""
    user = get_current_user(request)
    params: list = []
    where = ["1=1"]
    if q.strip():
        where.append("(ps.ref_produit_norm LIKE ? OR LOWER(COALESCE(ps.designation,'')) LIKE LOWER(?)"
                     " OR LOWER(COALESCE(ps.client,'')) LIKE LOWER(?))")
        like = f"%{q.strip()}%"
        params += [like, like, like]
    if machine.strip():
        where.append("LOWER(TRIM(COALESCE(ps.machine,''))) = LOWER(TRIM(?))")
        params.append(machine.strip())

    sql = f"""
        SELECT ps.ref_produit_norm,
               COUNT(*)                                   AS nb_series,
               MAX(COALESCE(ps.date_fin, ps.date_debut))  AS derniere_production,
               GROUP_CONCAT(DISTINCT ps.machine)          AS machines,
               GROUP_CONCAT(DISTINCT ps.client)           AS clients
        FROM produit_series ps
        WHERE {' AND '.join(where)}
        GROUP BY ps.ref_produit_norm
        HAVING COUNT(*) >= ?
        ORDER BY derniere_production DESC
        LIMIT ?
    """
    params += [max(1, int(min_series)), max(1, min(int(limit), 1000))]

    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            r["machines"] = [m for m in (r.get("machines") or "").split(",") if m]
            r["clients"] = [c for c in (r.get("clients") or "").split(",") if c]
            ident = pm.identite_produit(conn, r["ref_produit_norm"])
            r["designation"] = ident.get("designation")
            r["nb_savoirs"] = conn.execute(
                "SELECT COUNT(*) AS n FROM produit_savoirs "
                "WHERE ref_produit_norm=? AND obsolete=0", (r["ref_produit_norm"],)
            ).fetchone()["n"]
            r["nb_documents"] = conn.execute(
                "SELECT COUNT(*) AS n FROM produit_documents "
                "WHERE ref_produit_norm=? AND statut!='ecarte'", (r["ref_produit_norm"],)
            ).fetchone()["n"]
    with get_db() as conn:
        couverture = pm.taux_rattachement(conn)
    return {"produits": rows, "total": len(rows), "peut_ecrire": True,
            "est_admin": is_admin(user), "est_superadmin": is_superadmin(user),
            "couverture": couverture}


@router.get("/api/produits/rattachement")
def couverture_rattachement(request: Request):
    """Taux de rattachement dossier -> produit. L'indicateur de verite du module."""
    get_current_user(request)
    with get_db() as conn:
        return pm.taux_rattachement(conn)


@router.post("/api/produits/rattrapage")
def lancer_rattrapage(request: Request, limit: int = 0, refaire: bool = False,
                      offset: int = 0):
    """Materialise les series manquantes. Reserve au superadmin (long).

    Appelable par lots (`limit` + `offset`) : sur plusieurs annees d'historique
    une passe unique depasserait le timeout de la passerelle, et chaque lot
    etant commite, une interruption ne perd rien de ce qui est deja fait.
    """
    require_superadmin(request)
    with get_db() as conn:
        return pm.rattraper_series(conn, limit=limit or None, refaire=refaire,
                                   offset=offset)


@router.get("/api/produits/documents")
def liste_documents_scannes(request: Request, q: str = "", limit: int = 300):
    """Tous les OF scannes, rattaches ou non — la vue « ce qu'on a deja ».

    La file de rattachement ne montre que les echecs. Elle ne dit rien de ce
    qui est arrive, et c'est pourtant la question la plus frequente : « ce
    dossier a-t-il ete scanne ? ».
    """
    get_current_user(request)
    params: list = []
    where = ["d.statut != 'ecarte'"]
    if q.strip():
        like = f"%{q.strip()}%"
        where.append(
            "(d.of_numero LIKE ? OR d.ref_produit_norm LIKE ? OR d.no_dossier LIKE ?"
            " OR LOWER(COALESCE(d.fichier_origine,'')) LIKE LOWER(?)"
            " OR LOWER(COALESCE(s.client,'')) LIKE LOWER(?))"
        )
        params += [like, like, like, like, like]
    params.append(max(1, min(int(limit), 2000)))

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT d.id, d.of_numero, d.no_dossier, d.ref_produit_norm, d.statut,
                       d.nb_pages, d.fichier_origine, d.chemin_origine,
                       d.date_document, d.importe_le, d.importe_par,
                       o.machine AS of_machine, o.laize AS of_laize, o.format AS of_format,
                       o.qte_etiquettes AS of_qte_etiquettes,
                       s.machine AS serie_machine, s.client AS serie_client,
                       s.etiquettes AS serie_etiquettes, s.metrage_m AS serie_metrage_m
                  FROM produit_documents d
                  LEFT JOIN of_imports    o ON o.id = d.of_import_id
                  LEFT JOIN produit_series s ON s.no_dossier = d.no_dossier
                 WHERE {' AND '.join(where)}
                 ORDER BY COALESCE(d.date_document, d.importe_le) DESC, d.id DESC
                 LIMIT ?""",
            params,
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM produit_documents WHERE statut != 'ecarte'"
        ).fetchone()["n"]
        a_rattacher = conn.execute(
            "SELECT COUNT(*) AS n FROM produit_documents WHERE statut = 'a_rattacher'"
        ).fetchone()["n"]

    docs = []
    for r in rows:
        d = dict(r)
        d["machine"] = d.get("serie_machine") or d.get("of_machine")
        d["client"] = d.get("serie_client")
        d["etiquettes"] = d.get("serie_etiquettes") or d.get("of_qte_etiquettes")
        docs.append(d)
    return {"documents": docs, "total": int(total or 0),
            "a_rattacher": int(a_rattacher or 0), "affiches": len(docs)}


@router.get("/api/produits/fiches-non-reliees")
def fiches_non_reliees(request: Request, q: str = "", limit: int = 500):
    """Fiches techniques qu'aucun OF et aucune production ne rejoint.

    Deux causes, qui n'appellent pas la meme action et sont donc distinguees :
    une reference illisible dans le libelle de la fiche (le rapprochement ne
    peut pas fonctionner), ou une fiche parfaitement lisible mais jamais
    produite (rien a corriger — c'est peut-etre juste un produit dormant).
    """
    get_current_user(request)
    with get_db() as conn:
        ft_cols = {r["name"] for r in conn.execute(
            "PRAGMA table_info(fiches_techniques)").fetchall()}
        if "ref_produit_norm" not in ft_cols:
            return {"fiches": [], "total": 0}
        champs = [c for c in ("id", "reference", "ref_produit_norm", "designation",
                              "client", "format", "laize", "support", "matiere",
                              "machine", "nb_couleurs", "source", "date_import")
                  if c in ft_cols]
        params: list = []
        where = ["""(ft.ref_produit_norm IS NULL OR TRIM(ft.ref_produit_norm) = ''
                     OR (NOT EXISTS (SELECT 1 FROM of_imports o
                                      WHERE TRIM(COALESCE(o.reference,'')) = ft.ref_produit_norm)
                         AND NOT EXISTS (SELECT 1 FROM produit_series s
                                          WHERE s.ref_produit_norm = ft.ref_produit_norm)))"""]
        if q.strip():
            like = f"%{q.strip()}%"
            where.append("(LOWER(COALESCE(ft.reference,'')) LIKE LOWER(?)"
                         " OR LOWER(COALESCE(ft.designation,'')) LIKE LOWER(?))")
            params += [like, like]
        params.append(max(1, min(int(limit), 2000)))
        rows = conn.execute(
            "SELECT " + ", ".join("ft." + c for c in champs) +
            " FROM fiches_techniques ft WHERE " + " AND ".join(where) +
            " ORDER BY ft.reference LIMIT ?",
            params,
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["motif"] = ("ref_illisible" if not (d.get("ref_produit_norm") or "").strip()
                      else "jamais_produite")
        out.append(d)
    return {"fiches": out, "total": len(out)}


@router.get("/api/produits/documents/a-rattacher")
def documents_a_rattacher(request: Request, limit: int = 200):
    """File des scans dont le numero d'OF n'a pas pu etre lu automatiquement."""
    get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM produit_documents WHERE statut='a_rattacher' "
            "ORDER BY datetime(importe_le) DESC, id DESC LIMIT ?",
            (max(1, min(int(limit), 500)),),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM produit_documents WHERE statut='a_rattacher'"
        ).fetchone()["n"]
    return {"documents": [dict(r) for r in rows], "total": int(total or 0)}


@router.get("/api/produits/dossiers/recherche")
def rechercher_dossiers(request: Request, q: str = "", limit: int = 12):
    """Candidats de rattachement pour un scan, cherches au fil de la frappe.

    Le champ de rattachement demandait jusqu'ici un numero de dossier connu
    par coeur : sur un scan dont l'OF n'a pas ete lu, personne ne l'a. On
    cherche donc sur tout ce que le document peut porter — numero de dossier,
    numero d'OF, reference produit, client — et on renvoie pour chaque
    candidat la reference produit que le rattachement produira REELLEMENT
    (via `contexte_dossier`, la meme fonction que le POST). Afficher autre
    chose que ce qui sera ecrit serait une promesse que l'ecran ne tient pas.
    """
    get_current_user(request)
    terme = (q or "").strip()
    if len(terme) < 2:
        return {"dossiers": [], "total": 0}

    n = max(1, min(int(limit), 50))
    like = f"%{terme}%"
    prefixe = f"{terme}%"

    with get_db() as conn:
        pe_cols = pm._cols(conn, "planning_entries")
        if not pe_cols:
            return {"dossiers": [], "total": 0}

        champs = ["pe.id AS pe_id", "pe.reference", "pe.client", "pe.description"]
        for c in ("numero_of", "ref_produit", "ref_produit_norm", "planned_start",
                  "date_livraison", "statut"):
            if c in pe_cols:
                champs.append("pe." + c)

        cherchables = ["pe.reference", "pe.client", "pe.description"]
        for c in ("numero_of", "ref_produit", "ref_produit_norm"):
            if c in pe_cols:
                cherchables.append("pe." + c)
        ou = " OR ".join(
            f"LOWER(COALESCE({c},'')) LIKE LOWER(?)" for c in cherchables
        )
        params = [like] * len(cherchables)

        # Un dossier tape en entier doit sortir en tete, avant les dossiers
        # dont le libelle contient la meme suite de chiffres par hasard.
        rang = ("CASE WHEN LOWER(pe.reference) LIKE LOWER(?) THEN 0 "
                "WHEN LOWER(COALESCE(pe.numero_of,'')) LIKE LOWER(?) THEN 1 "
                "ELSE 2 END" if "numero_of" in pe_cols
                else "CASE WHEN LOWER(pe.reference) LIKE LOWER(?) THEN 0 ELSE 2 END")
        params += [prefixe, prefixe] if "numero_of" in pe_cols else [prefixe]

        sql = (
            "SELECT " + ", ".join(champs) + ", m.nom AS machine_nom, " + rang + " AS rang "
            "FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id "
            f"WHERE {ou} ORDER BY rang, pe.id DESC LIMIT ?"
        )
        rows = conn.execute(sql, params + [n]).fetchall()

        vus = set()
        out = []
        for r in rows:
            d = dict(r)
            dossier = (d.get("reference") or "").strip()
            if not dossier or dossier in vus:
                continue
            vus.add(dossier)
            ctx = pm.contexte_dossier(conn, dossier)
            out.append({
                "no_dossier": dossier,
                "numero_of": d.get("numero_of"),
                "client": ctx.get("client") or d.get("client"),
                "designation": ctx.get("designation") or d.get("description"),
                "machine": ctx.get("machine") or d.get("machine_nom"),
                "statut": d.get("statut"),
                "date": d.get("planned_start") or d.get("date_livraison"),
                "ref_produit_norm": ctx.get("ref_produit_norm"),
            })

    return {"dossiers": out, "total": len(out)}


@router.get("/api/produits/documents/{doc_id}/pdf")
def document_pdf(doc_id: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT fichier, fichier_origine FROM produit_documents WHERE id=?", (doc_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    path = os.path.join(SCAN_UPLOAD_DIR, row["fichier"])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur.")
    # Pas de `filename=` : FileResponse poserait alors un Content-Disposition
    # « attachment » et le scan se telechargerait au lieu de s'ouvrir dans
    # l'apercu cote a cote de la file de rattachement.
    return FileResponse(path, media_type="application/pdf")


@router.post("/api/produits/documents/{doc_id}/rattacher")
async def rattacher_document(doc_id: int, request: Request):
    """Rattachement manuel d'un scan a un dossier (ou mise a l'ecart)."""
    user = get_current_user(request)
    body = await request.json()
    no_dossier = (body.get("no_dossier") or "").strip()
    ecarter = bool(body.get("ecarter"))
    note = (body.get("note") or "").strip() or None

    with get_db() as conn:
        doc = conn.execute("SELECT * FROM produit_documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document introuvable.")

        if ecarter:
            conn.execute(
                "UPDATE produit_documents SET statut='ecarte', note=?, "
                "rattache_par=?, rattache_le=? WHERE id=?",
                (note, _auteur(user), pm.now_iso(), doc_id),
            )
            conn.commit()
            return {"success": True, "statut": "ecarte"}

        if not no_dossier:
            raise HTTPException(status_code=400, detail="Numero de dossier requis.")
        ctx = pm.contexte_dossier(conn, no_dossier)
        if not ctx.get("ref_produit_norm"):
            raise HTTPException(
                status_code=400,
                detail=f"Dossier {no_dossier} rattachable a aucune reference produit.",
            )
        conn.execute(
            "UPDATE produit_documents SET no_dossier=?, ref_produit_norm=?, of_import_id=?, "
            "statut='rattache', note=?, rattache_par=?, rattache_le=? WHERE id=?",
            (no_dossier, ctx["ref_produit_norm"], ctx.get("of_import_id"), note,
             _auteur(user), pm.now_iso(), doc_id),
        )
        conn.commit()
    log_action(user=user, action="UPDATE", module="produits",
               objet=f"Scan OF #{doc_id} rattache a {no_dossier}", detail=None,
               ip=request.client.host if request.client else None)
    return {"success": True, "statut": "rattache", "ref_produit_norm": ctx["ref_produit_norm"]}


@router.post("/api/produits/documents")
async def deposer_document(request: Request, file: UploadFile = File(...),
                           no_dossier: str = Form(""), of_numero: str = Form(""),
                           chemin_origine: str = Form(""), date_fichier: str = Form("")):
    """Depot manuel d'un scan depuis l'interface (secours de l'agent local)."""
    user = get_current_user(request)
    content = await file.read()
    return _enregistrer_scan(content, file.filename or "scan.pdf",
                             importe_par=_auteur(user),
                             no_dossier=no_dossier, of_numero=of_numero,
                             chemin_origine=chemin_origine, date_fichier=date_fichier)


# ─── Depot par l'agent local (dossier reseau surveille) ──────────────────────

@router.post("/api/bridge/of-scan")
async def bridge_of_scan(file: UploadFile = File(...),
                         fichier_origine: str = Form(""),
                         of_numero: str = Form(""),
                         chemin_origine: str = Form(""),
                         date_fichier: str = Form(""),
                         x_api_key: Optional[str] = Header(None, alias="X-Api-Key")):
    """Depot d'un OF termine scanne par l'agent qui surveille le dossier reseau.

    Meme authentification que le pont Access (cle API + scope). L'agent
    n'a aucune connaissance metier : il envoie le PDF, le serveur decide.
    """
    from app.routers.api_bridge import _require_scope
    _require_scope(x_api_key, "scan:write")
    content = await file.read()
    return _enregistrer_scan(content, fichier_origine or file.filename or "scan.pdf",
                             importe_par="agent:scan", of_numero=of_numero,
                             chemin_origine=chemin_origine, date_fichier=date_fichier)


def _lire_of_numero(content: bytes) -> tuple[Optional[str], bool]:
    """Numero d'OF lu dans le PDF, et si le PDF portait du texte.

    Reutilise exactement la chaine d'extraction de l'import OF
    (`pdfplumber` + le motif `of_numero`). Un scan sans OCR ne rend aucun
    texte : ce n'est pas une erreur, c'est le cas nominal tant que l'option
    « PDF consultable » du copieur n'est pas activee — le document part alors
    dans la file de rattachement manuel.
    """
    try:
        from app.routers.of_import import _extract_pdf_text, _PATTERNS
        texte = _extract_pdf_text(content) or ""
    except Exception:
        return None, False
    if not texte.strip():
        return None, False
    m = re.search(_PATTERNS["of_numero"], texte, re.IGNORECASE | re.MULTILINE)
    if m:
        return str(m.group(1)).strip(), True
    m = _OF_RACINE_RE.search(texte)
    return (m.group(1) if m else None), True


def _nom_fichier_sur(nom: str, of_numero: Optional[str]) -> str:
    base = _SAFE_NAME_RE.sub("_", os.path.basename(nom or "scan.pdf")) or "scan.pdf"
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    prefixe = _SAFE_NAME_RE.sub("_", of_numero) if of_numero else "scan"
    stamp = pm.now_iso().replace(":", "").replace("-", "")
    return f"{prefixe}_{stamp}_{base}"[:180]


def _enregistrer_scan(content: bytes, nom_origine: str, importe_par: str,
                      no_dossier: str = "", of_numero: str = "",
                      chemin_origine: str = "", date_fichier: str = "") -> dict:
    """Enregistre un scan d'OF termine et le rattache au mieux.

    Ordre de resolution, du plus fiable au moins fiable :

    1. **Le nom du fichier.** Les scans de l'atelier sont nommes a la main et
       ce nom porte le numero d'OF et la reference produit
       (« 9932140 (marche 748) 420-0018 »). C'est du texte, pas une image :
       aucune OCR ne peut faire mieux.
    2. **Le numero d'OF** ainsi lu, qui donne le dossier via `of_imports` puis
       `planning_entries`, donc la serie exacte.
    3. **La reference produit** du nom, quand aucun OF ne correspond : le
       document se rattache au produit sans se rattacher a une production
       precise. C'est deja utile.
    4. **Le texte du PDF**, en dernier recours, si le copieur a fait de l'OCR.

    La deduplication se fait sur le CONTENU (sha-256) : un fichier renomme ou
    deplace d'un dossier d'annee a l'autre reste le meme document.
    """
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if not (nom_origine or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis.")

    empreinte = hashlib.sha256(content).hexdigest()
    with get_db() as conn:
        deja = conn.execute(
            "SELECT id, statut, ref_produit_norm, no_dossier, of_numero "
            "FROM produit_documents WHERE empreinte = ?", (empreinte,)
        ).fetchone()
    if deja:
        d = dict(deja)
        d.update({"success": True, "doublon": True,
                  "message": "Deja enregistre (contenu identique)."})
        return d

    infos = pm.analyser_nom_scan(nom_origine)
    numero = (of_numero or "").strip() or infos.get("of_numero") or None
    ref_nom = infos.get("ref_produit_norm")

    # Le texte du PDF ne sert que si le nom n'a rien donne : sur un scan sans
    # OCR il est vide, ce qui est le cas nominal et non une erreur.
    avait_texte = False
    if not numero:
        lu, avait_texte = _lire_of_numero(content)
        numero = numero or lu
    else:
        try:
            _, avait_texte = _lire_of_numero(content)
        except Exception:
            avait_texte = False

    os.makedirs(SCAN_UPLOAD_DIR, exist_ok=True)
    fichier = _nom_fichier_sur(nom_origine, numero)
    with open(os.path.join(SCAN_UPLOAD_DIR, fichier), "wb") as fh:
        fh.write(content)

    nb_pages = None
    try:
        import pdfplumber
        from io import BytesIO
        with pdfplumber.open(BytesIO(content)) as pdf:
            nb_pages = len(pdf.pages)
    except Exception:
        pass

    with get_db() as conn:
        dossier = (no_dossier or "").strip() or None
        ref_norm = None
        of_import_id = None

        if not dossier and numero:
            row = conn.execute(
                "SELECT id, reference FROM of_imports "
                "WHERE trim(lower(COALESCE(of_numero,''))) = trim(lower(?)) "
                "ORDER BY id DESC LIMIT 1",
                (numero,),
            ).fetchone()
            if row:
                of_import_id = row["id"]
                pe = conn.execute(
                    "SELECT reference FROM planning_entries WHERE of_import_id=? "
                    "ORDER BY id DESC LIMIT 1", (of_import_id,)
                ).fetchone()
                if pe:
                    dossier = pe["reference"]

        if dossier:
            ctx = pm.contexte_dossier(conn, dossier)
            ref_norm = ctx.get("ref_produit_norm")
            of_import_id = of_import_id or ctx.get("of_import_id")

        # Aucun dossier retrouve, mais le nom porte la reference : on rattache
        # au produit. Le document n'appartient a aucune serie, il appartient
        # quand meme au produit — et c'est ce que quelqu'un vient y chercher.
        origine_ref = "dossier" if ref_norm else None
        if not ref_norm and ref_nom:
            ref_norm = ref_nom
            origine_ref = "nom_fichier"

        statut = "rattache" if ref_norm else "a_rattacher"
        maintenant = pm.now_iso()
        d_fichier = (date_fichier or "").strip() or None
        # La date qui sert au tri est celle de la PRODUCTION, pas celle du
        # depot : sept scans deposes le meme apres-midi couvrent plusieurs
        # mois d'atelier, et une liste triee sur la date d'import n'ordonne
        # rien du tout.
        d_document = pm.date_document(conn, dossier, of_import_id, d_fichier, maintenant)
        cur = conn.execute(
            """INSERT INTO produit_documents
               (ref_produit_norm, no_dossier, of_numero, of_import_id, type, fichier,
                fichier_origine, chemin_origine, nb_pages, taille_octets, texte_extrait,
                empreinte, statut, date_fichier, date_document, importe_le, importe_par)
               VALUES (?,?,?,?,'of_termine',?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref_norm, dossier, numero, of_import_id, fichier,
             os.path.basename(nom_origine or ""), (chemin_origine or "").strip() or None,
             nb_pages, len(content), 1 if avait_texte else 0, empreinte,
             statut, d_fichier, d_document, maintenant, importe_par),
        )
        conn.commit()
        doc_id = cur.lastrowid

    if ref_norm:
        message = "Rattache a " + str(ref_norm)
        if origine_ref == "nom_fichier":
            message += " (reference lue dans le nom du fichier, sans dossier)"
    else:
        message = "Ni numero d'OF ni reference dans le nom — file de rattachement."

    return {
        "success": True, "doublon": False, "id": doc_id, "statut": statut,
        "of_numero": numero, "no_dossier": dossier, "ref_produit_norm": ref_norm,
        "origine_ref": origine_ref, "texte_extrait": avait_texte,
        "date_document": d_document,
        "message": message,
    }


# ─── Savoirs ─────────────────────────────────────────────────────────────────

@router.get("/api/produits/savoirs/types")
def types_savoir(request: Request):
    get_current_user(request)
    return {"types": [{"cle": t, "label": pm.LABELS_TYPE_SAVOIR[t]} for t in pm.TYPES_SAVOIR]}


@router.put("/api/produits/savoirs/{savoir_id}")
async def modifier_savoir(savoir_id: int, request: Request):
    user = get_current_user(request)
    body = await request.json()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM produit_savoirs WHERE id=?", (savoir_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Savoir introuvable.")
        if row["auteur"] != _auteur(user) and not is_admin(user):
            raise HTTPException(status_code=403, detail="Modification reservee a l'auteur.")

        champs, vals = [], []
        if "texte" in body:
            txt = (body.get("texte") or "").strip()
            if not txt:
                raise HTTPException(status_code=400, detail="Texte vide.")
            champs.append("texte=?"); vals.append(txt)
        if "type" in body:
            t = (body.get("type") or "autre").strip()
            champs.append("type=?"); vals.append(t if t in pm.TYPES_SAVOIR else "autre")
        if "machine" in body:
            champs.append("machine=?"); vals.append((body.get("machine") or "").strip() or None)
        if "epingle" in body:
            if not is_admin(user):
                raise HTTPException(status_code=403, detail="Epinglage reserve a l'administration.")
            champs.append("epingle=?"); vals.append(1 if body.get("epingle") else 0)
        if not champs:
            return {"success": True, "inchange": True}

        champs += ["updated_at=?", "updated_par=?"]
        vals += [pm.now_iso(), _auteur(user), savoir_id]
        conn.execute(f"UPDATE produit_savoirs SET {', '.join(champs)} WHERE id=?", vals)
        conn.commit()
    return {"success": True}


@router.post("/api/produits/savoirs/{savoir_id}/obsolete")
async def perimer_savoir(savoir_id: int, request: Request):
    """Un savoir perime se marque, il ne s'efface pas : le lire evite de le redecouvrir."""
    user = get_current_user(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    motif = (body.get("motif") or "").strip() or None
    remettre = bool(body.get("remettre"))
    with get_db() as conn:
        row = conn.execute("SELECT * FROM produit_savoirs WHERE id=?", (savoir_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Savoir introuvable.")
        if row["auteur"] != _auteur(user) and not is_admin(user):
            raise HTTPException(status_code=403, detail="Action reservee a l'auteur.")
        conn.execute(
            "UPDATE produit_savoirs SET obsolete=?, obsolete_motif=?, updated_at=?, updated_par=? "
            "WHERE id=?",
            (0 if remettre else 1, None if remettre else motif,
             pm.now_iso(), _auteur(user), savoir_id),
        )
        conn.commit()
    return {"success": True, "obsolete": 0 if remettre else 1}


@router.post("/api/produits/savoirs/{savoir_id}/utile")
def voter_utile(savoir_id: int, request: Request):
    """Vote « ca m'a servi ». Sans validation hierarchique, c'est l'usage qui trie."""
    user = get_current_user(request)
    login = _user_login(user)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM produit_savoirs WHERE id=?", (savoir_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Savoir introuvable.")
        deja = conn.execute(
            "SELECT 1 FROM produit_savoirs_utile WHERE savoir_id=? AND user_login=?",
            (savoir_id, login),
        ).fetchone()
        if deja:
            conn.execute(
                "DELETE FROM produit_savoirs_utile WHERE savoir_id=? AND user_login=?",
                (savoir_id, login),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO produit_savoirs_utile (savoir_id, user_login, created_at) "
                "VALUES (?,?,?)", (savoir_id, login, pm.now_iso()),
            )
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM produit_savoirs_utile WHERE savoir_id=?", (savoir_id,)
        ).fetchone()["n"]
        conn.execute("UPDATE produit_savoirs SET utile_count=? WHERE id=?", (n, savoir_id))
        conn.commit()
    return {"success": True, "utile_count": int(n or 0), "vote_utilisateur": not bool(deja)}


# ─── Commentaires a promouvoir ───────────────────────────────────────────────

@router.get("/api/produits/commentaires-a-promouvoir")
def commentaires_a_promouvoir(request: Request, limit: int = 100):
    """Les commentaires d'operateurs jamais transformes en savoir.

    C'est la matiere premiere la moins chere du module : elle est deja saisie,
    elle n'attend qu'un geste de relecture.
    """
    get_current_user(request)
    with get_db() as conn:
        pd_cols = {r["name"] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}
        where = ["trim(COALESCE(pd.commentaire,'')) != ''"]
        if "est_annule" in pd_cols:
            where.append("COALESCE(pd.est_annule,0)=0")
        where.append("pd.id NOT IN (SELECT saisie_source_id FROM produit_savoirs "
                     "WHERE saisie_source_id IS NOT NULL)")
        rows = conn.execute(
            f"""SELECT pd.id, pd.date_operation, pd.operateur, pd.machine, pd.no_dossier,
                       pd.operation, pd.operation_code, pd.commentaire
                FROM production_data pd
                WHERE {' AND '.join(where)}
                ORDER BY pd.date_operation DESC, pd.id DESC LIMIT ?""",
            (max(1, min(int(limit), 500)),),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            ctx = pm.contexte_dossier(conn, d.get("no_dossier") or "")
            d["ref_produit_norm"] = ctx.get("ref_produit_norm")
            out.append(d)
    return {"commentaires": out, "total": len(out)}


@router.post("/api/produits/commentaires/{saisie_id}/promouvoir")
async def promouvoir_commentaire(saisie_id: int, request: Request):
    user = get_current_user(request)
    body = await request.json()
    texte = (body.get("texte") or "").strip()
    type_savoir = (body.get("type") or "autre").strip()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, no_dossier, machine, operateur, commentaire FROM production_data WHERE id=?",
            (saisie_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Saisie introuvable.")
        texte = texte or (row["commentaire"] or "").strip()
        if not texte:
            raise HTTPException(status_code=400, detail="Texte vide.")
        ctx = pm.contexte_dossier(conn, row["no_dossier"] or "")
        ref = ctx.get("ref_produit_norm")
        if not ref:
            raise HTTPException(
                status_code=400,
                detail="Dossier rattachable a aucune reference produit.",
            )
        conn.execute(
            """INSERT INTO produit_savoirs
               (ref_produit_norm, type, texte, machine, no_dossier_source, saisie_source_id,
                auteur, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (ref, type_savoir if type_savoir in pm.TYPES_SAVOIR else "autre", texte,
             row["machine"], row["no_dossier"], saisie_id,
             (row["operateur"] or _auteur(user)), pm.now_iso()),
        )
        conn.commit()
    return {"success": True, "ref_produit_norm": ref}


# ─── Historique vu depuis un dossier (Saisieprod) ────────────────────────────

@router.get("/api/produits/dossier/{no_dossier}/apercu")
def apercu_dossier(no_dossier: str, request: Request):
    """Le bouton « Historique » existe-t-il pour ce dossier ?"""
    user = get_current_user(request)
    with get_db() as conn:
        return pm.apercu_pour_dossier(conn, no_dossier, user_login=_user_login(user))


@router.get("/api/produits/dossier/{no_dossier}/historique")
def historique_dossier(no_dossier: str, request: Request):
    """Le panneau ouvert par le bouton : les series des AUTRES dossiers."""
    user = get_current_user(request)
    with get_db() as conn:
        ctx = pm.contexte_dossier(conn, no_dossier)
        ref = ctx.get("ref_produit_norm")
        # L'info prod du dossier ouvert se lit en tete du panneau : c'est la
        # consigne qui concerne la production en cours, pas l'historique.
        info = pm.info_prod_dossier(conn, no_dossier)
        if not ref:
            if not info:
                return {"disponible": False, "ref_produit_norm": None}
            return {
                "disponible": True, "ref_produit_norm": None,
                "no_dossier": (no_dossier or "").strip(),
                "info_prod": info, "series": [], "savoirs": [], "documents": [],
                "contexte": ctx, "est_admin": is_admin(user),
                "est_superadmin": is_superadmin(user), "moi": _auteur(user),
            }
        data = pm.resume_produit(conn, ref, user_login=_user_login(user),
                                 exclure_dossier=(no_dossier or "").strip())
        data["info_prod"] = info
    data["disponible"] = True
    data["no_dossier"] = (no_dossier or "").strip()
    data["contexte"] = ctx
    data["est_admin"] = is_admin(user)
    data["est_superadmin"] = is_superadmin(user)
    data["moi"] = _auteur(user)
    return data


# ─── Fiche produit (routes parametrees en dernier) ───────────────────────────

@router.get("/api/produits/{ref:path}/series")
def series_produit(ref: str, request: Request, limit: int = 0):
    get_current_user(request)
    r = _ref_ou_404(ref)
    with get_db() as conn:
        return {"ref_produit_norm": r,
                "series": pm.series_produit(conn, r, limit=limit or None)}


@router.get("/api/produits/{ref:path}/savoirs")
def liste_savoirs(ref: str, request: Request, obsoletes: bool = False):
    user = get_current_user(request)
    r = _ref_ou_404(ref)
    with get_db() as conn:
        return {"ref_produit_norm": r,
                "savoirs": pm.savoirs_produit(conn, r, inclure_obsoletes=obsoletes,
                                              user_login=_user_login(user))}


@router.post("/api/produits/{ref:path}/savoirs")
async def creer_savoir(ref: str, request: Request):
    """Creation d'un savoir. Publie immediatement, sans validation.

    Le garde-fou n'est pas un circuit d'approbation mais la tracabilite :
    auteur et date sont toujours affiches, et l'auteur peut corriger.
    """
    user = get_current_user(request)
    r = _ref_ou_404(ref)
    body = await request.json()
    texte = (body.get("texte") or "").strip()
    if not texte:
        raise HTTPException(status_code=400, detail="Texte requis.")
    type_savoir = (body.get("type") or "autre").strip()
    machine = (body.get("machine") or "").strip() or None
    no_dossier = (body.get("no_dossier") or "").strip() or None

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO produit_savoirs
               (ref_produit_norm, type, texte, machine, no_dossier_source, auteur, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (r, type_savoir if type_savoir in pm.TYPES_SAVOIR else "autre", texte,
             machine, no_dossier, _auteur(user), pm.now_iso()),
        )
        conn.commit()
        savoir_id = cur.lastrowid
        savoirs = pm.savoirs_produit(conn, r, user_login=_user_login(user))
    return {"success": True, "id": savoir_id, "savoirs": savoirs}


@router.get("/api/produits/{ref:path}/documents")
def liste_documents(ref: str, request: Request):
    get_current_user(request)
    r = _ref_ou_404(ref)
    with get_db() as conn:
        return {"ref_produit_norm": r, "documents": pm.documents_produit(conn, r)}


@router.get("/api/produits/{ref:path}")
def fiche_produit(ref: str, request: Request):
    user = get_current_user(request)
    r = _ref_ou_404(ref)
    with get_db() as conn:
        # Ouvrir la fiche vaut demande explicite : on materialise d'abord les
        # productions passees de cette reference, plafond large. La fiche n'a
        # plus a s'excuser d'etre vide en renvoyant vers un rattrapage global.
        pm.assurer_series_reference(conn, r, plafond=300)
        data = pm.resume_produit(conn, r, user_login=_user_login(user))
        # Une fiche vide a deux causes tres differentes : la reference n'a
        # jamais tourne, ou elle a tourne mais le rattrapage n'a pas encore ete
        # lance. Repondre « aucune donnee » dans le second cas fait douter de
        # l'outil quelqu'un qui sait qu'il a produit ce produit.
        data["a_materialiser"] = pm.dossiers_non_materialises(conn, r)
    vide = (not data["nb_series"] and not data["savoirs"]
            and not data["documents"] and not data["a_materialiser"])
    if vide:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun dossier de production rattache a la reference {r}.",
        )
    data["est_admin"] = is_admin(user)
    data["est_superadmin"] = is_superadmin(user)
    data["moi"] = _auteur(user)
    return data
