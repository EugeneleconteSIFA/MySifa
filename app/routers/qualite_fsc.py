"""MySifa — MyQualité › Certifications SIFA › FSC.

Une page, trois questions d'audit CoC :

1. « Liste des fournisseurs certifiés » : licence, certificat, expiration, et le
   certificat lui-même — un seul PDF fusionné, page de garde comprise.
2. « Preuves de contrôle des certificats fournisseurs sur la base FSC » : chaque
   contrôle est une ligne de `qualite_fsc_controles`, datée, signée, avec son
   justificatif. Jamais écrasée.
3. « Quelles catégories FSC ? » : ce que chaque fournisseur a le droit de livrer
   (FSC 100%, Mix, Mix Credit, Recycled…), lu sur son certificat puis validé au
   contrôle ; rapproché de ce que SIFA exige sur ses dossiers et de ce qu'elle a
   réellement reçu.

Les données de base ne sont PAS dupliquées : fournisseurs dans
`fournisseurs_fsc`, certificats déposés dans `qualite_fournisseur_certificats`
(Ressources fournisseurs), claims reçus dans `stock_receptions` /
`pf_receptions`, exigences dans `planning_entries`.

Route prefix : /api/qualite/fsc
Lecture : ROLES_QUALITE_VIEW (dont commercial). Écriture : ROLES_QUALITE.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.database import get_db
from app.routers.qualite import (
    RESSOURCES_UPLOAD_DIR,
    _require_qualite_access,
    _require_qualite_view,
    _sanitize_filename,
)
from app.services.audit_service import log_action
from app.services.fsc_dossier import (
    choisir_document,
    construire_dossier_pdf,
    statut_expiration,
)
from app.services.fsc_lecture_certificat import lire_certificat
from config import (
    APP_ORG_NAME,
    FSC_ALERTE_JOURS,
    FSC_BASE_RECHERCHE_URL,
    FSC_CLAIM_LABELS,
    FSC_CLAIMS_PORTEE,
    FSC_CONTROLE_VALIDITE_JOURS,
    FSC_FICHE_SLUG,
    FSC_LICENCE_SIFA,
    FSC_STATUTS_BASE,
    UPLOAD_DIR,
)

router = APIRouter()

FSC_CONTROLES_DIR = os.path.join(UPLOAD_DIR, "qualite", "fsc-controles")
os.makedirs(FSC_CONTROLES_DIR, exist_ok=True)

# Justificatif d'un contrôle : capture ou export de la page de la base FSC.
# Liste fermée : ces fichiers sont servis en ligne, rien d'exécutable ne passe.
_JUSTIF_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
_JUSTIF_MAX_OCTETS = 15 * 1024 * 1024



def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _iso(valeur: Optional[str]) -> Optional[str]:
    v = (valeur or "").strip()[:10]
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Date invalide : {valeur} — format AAAA-MM-JJ attendu.")


def _json_list(raw) -> list:
    if not raw:
        return []
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    return v if isinstance(v, list) else []


def _claims_labels(codes: list[str]) -> list[str]:
    return [FSC_CLAIMS_PORTEE[c]["label"] for c in FSC_CLAIMS_PORTEE if c in codes]


def _colonnes(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


# ══════════════════════════════════════════════════════════════════
# Assemblage de la synthèse
# ══════════════════════════════════════════════════════════════════

def _documents_fsc(conn) -> list[dict]:
    """Tous les certificats déposés qui concernent FSC : tagués sur la fiche RSE
    FSC, ou dont le titre ou le nom de fichier le dit."""
    fiche = conn.execute(
        "SELECT id FROM qualite_ref_fiches WHERE slug=?", (FSC_FICHE_SLUG,)
    ).fetchone()
    fiche_id = fiche["id"] if fiche else -1
    rows = conn.execute(
        """SELECT c.*
             FROM qualite_fournisseur_certificats c
            WHERE c.id IN (SELECT certificat_id FROM qualite_fournisseur_certificat_fiches WHERE fiche_id=?)
               OR UPPER(COALESCE(c.titre,'')) LIKE '%FSC%'
               OR UPPER(COALESCE(c.original_name,'')) LIKE '%FSC%'""",
        (fiche_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _lecture_publique(d: Optional[dict]) -> Optional[dict]:
    if not d or not d.get("fsc_lecture_le"):
        return None
    claims = _json_list(d.get("fsc_claims_lus"))
    for c in claims:
        c["label"] = FSC_CLAIMS_PORTEE.get(c.get("code"), {}).get("label", c.get("code"))
    return {
        "le": d.get("fsc_lecture_le"),
        "methode": d.get("fsc_lecture_methode"),
        "licence": d.get("fsc_licence_lue"),
        "certificat": d.get("fsc_certificat_lu"),
        "expiration": d.get("fsc_expiration_lue"),
        "claims": claims,
        "note": d.get("fsc_lecture_note") or "",
    }


def _derniers_controles(conn) -> dict[int, dict]:
    rows = conn.execute(
        """SELECT c.* FROM qualite_fsc_controles c
            WHERE c.id = (SELECT c2.id FROM qualite_fsc_controles c2
                           WHERE c2.fournisseur_id = c.fournisseur_id
                           ORDER BY c2.date_controle DESC, c2.id DESC LIMIT 1)"""
    ).fetchall()
    out = {}
    aujourdhui = date.today()
    for r in rows:
        d = dict(r)
        try:
            age = (aujourdhui - datetime.strptime(d["date_controle"][:10], "%Y-%m-%d").date()).days
        except ValueError:
            age = None
        out[d["fournisseur_id"]] = {
            "id": d["id"],
            "date_controle": d["date_controle"],
            "statut_base": d["statut_base"],
            "statut_label": FSC_STATUTS_BASE.get(d["statut_base"], d["statut_base"]),
            "date_expiration_lue": d.get("date_expiration_lue"),
            "claims": _json_list(d.get("claims")),
            "note": d.get("note") or "",
            "justificatif": bool(d.get("justificatif_filename")),
            "created_by_nom": d.get("created_by_nom"),
            "age_jours": age,
            "a_refaire": age is None or age > FSC_CONTROLE_VALIDITE_JOURS,
        }
    return out


def _claims_recus(conn) -> dict[int, list[dict]]:
    """Claims réellement reçus, par fournisseur (réceptions matière et négoce)."""
    agg: dict[int, dict[str, dict]] = {}
    sources = []
    if "fournisseur_id" in _colonnes(conn, "stock_receptions"):
        sources.append("SELECT fournisseur_id, fsc_type_claim AS claim, created_at AS le FROM stock_receptions")
    if _colonnes(conn, "pf_receptions"):
        sources.append("SELECT fournisseur_id, fsc_type_claim AS claim, date_reception AS le FROM pf_receptions")
    if not sources:
        return {}
    rows = conn.execute(
        f"""SELECT fournisseur_id, claim, COUNT(*) AS n, MAX(substr(le,1,10)) AS dernier
              FROM ({' UNION ALL '.join(sources)})
             WHERE fournisseur_id IS NOT NULL
               AND COALESCE(claim,'') NOT IN ('', 'non_fsc')
             GROUP BY fournisseur_id, claim"""
    ).fetchall()
    for r in rows:
        agg.setdefault(r["fournisseur_id"], {})[r["claim"]] = {
            "code": r["claim"],
            "label": FSC_CLAIM_LABELS.get(r["claim"], r["claim"]),
            "n": r["n"],
            "dernier": r["dernier"],
        }
    return {fid: list(v.values()) for fid, v in agg.items()}


def _famille(code: str) -> str:
    return FSC_CLAIMS_PORTEE.get(code, {}).get("famille", code)


def _synthese(conn, ids: Optional[set[int]] = None) -> dict:
    fours = [dict(r) for r in conn.execute(
        """SELECT id, nom, licence, certificat, groupe, branche, fsc_date_expiration
             FROM fournisseurs_fsc
            WHERE COALESCE(has_fsc,1)=1 AND COALESCE(actif,1)=1
            ORDER BY nom COLLATE NOCASE"""
    ).fetchall()]
    if ids:
        fours = [f for f in fours if f["id"] in ids]

    docs = _documents_fsc(conn)
    controles = _derniers_controles(conn)
    recus = _claims_recus(conn)

    lignes = []
    for f in fours:
        doc = choisir_document(f, docs)
        ctrl = controles.get(f["id"])
        lecture = _lecture_publique(doc)
        exp_fiche = (f.get("fsc_date_expiration") or "")[:10] or None
        exp_doc = ((doc or {}).get("date_expiration") or (lecture or {}).get("expiration") or "")[:10] or None
        exp_ctrl = ((ctrl or {}).get("date_expiration_lue") or "")[:10] or None
        # Référence affichée : ce qui a été vérifié, sinon ce que dit le document,
        # sinon la fiche. La fiche reste montrée à côté quand elle diverge : c'est
        # elle qui valide les réceptions (services/fsc_certificat.py).
        expiration = exp_ctrl or exp_doc or exp_fiche
        source_exp = "controle" if exp_ctrl else ("document" if exp_doc else ("fiche" if exp_fiche else None))
        st = statut_expiration(expiration, FSC_ALERTE_JOURS)

        if ctrl:
            claims, claims_source = ctrl["claims"], "controle"
        else:
            claims, claims_source = [], None
        proposes = [c["code"] for c in (lecture or {}).get("claims", []) if c["code"] not in claims]

        alertes = []
        if not f.get("licence"):
            alertes.append("Licence FSC non renseignée")
        if not doc:
            alertes.append("Aucun certificat FSC déposé")
        if exp_fiche and expiration and exp_fiche != expiration:
            alertes.append("Date de la fiche fournisseur différente")
        # L'absence de contrôle a sa propre colonne : elle n'est pas répétée ici.
        if ctrl and not ctrl["a_refaire"] and ctrl["statut_base"] != "valide":
            alertes.append(f"Base FSC : {ctrl['statut_label']}")

        lignes.append({
            "id": f["id"],
            "nom": f["nom"],
            "groupe": f.get("groupe"),
            "branche": f.get("branche"),
            "licence": f.get("licence"),
            "certificat": f.get("certificat"),
            "expiration": expiration,
            "expiration_source": source_exp,
            "expiration_fiche": exp_fiche,
            "expiration_document": exp_doc,
            "statut": st["statut"],
            "jours": st["jours"],
            "document": ({
                "id": doc["id"],
                "fournisseur_id": doc["fournisseur_id"],
                "titre": doc.get("titre") or "",
                "original_name": doc.get("original_name"),
                "mime_type": doc.get("mime_type"),
                "filename": doc.get("filename"),
                "date_expiration": doc.get("date_expiration"),
                "lecture": lecture,
            } if doc else None),
            "claims": [c for c in FSC_CLAIMS_PORTEE if c in claims],
            "claims_labels": _claims_labels(claims),
            "claims_source": claims_source,
            "claims_proposes": [c for c in FSC_CLAIMS_PORTEE if c in proposes],
            "dernier_controle": ctrl,
            "recus": recus.get(f["id"], []),
            "alertes": alertes,
        })

    # Couverture : pour chaque catégorie dont SIFA a besoin — exigée sur un
    # dossier ou déjà reçue — combien de fournisseurs peuvent la livrer.
    besoins: dict[str, dict] = {}
    if "fsc_type_requis" in _colonnes(conn, "planning_entries"):
        for r in conn.execute(
            """SELECT fsc_type_requis AS code, COUNT(*) AS n FROM planning_entries
                WHERE COALESCE(fsc_requis,0)=1 AND COALESCE(fsc_type_requis,'')<>''
                GROUP BY fsc_type_requis"""
        ).fetchall():
            besoins.setdefault(r["code"], {"n_dossiers": 0, "n_receptions": 0})["n_dossiers"] = r["n"]
    for l in lignes:
        for rc in l["recus"]:
            besoins.setdefault(rc["code"], {"n_dossiers": 0, "n_receptions": 0})["n_receptions"] += rc["n"]

    couverture = []
    ordre = list(FSC_CLAIM_LABELS.keys())
    for code in sorted(besoins, key=lambda c: ordre.index(c) if c in ordre else 99):
        fam = _famille(code)
        valides = [l for l in lignes if l["statut"] in ("valide", "a_renouveler")]
        confirmes = [l["nom"] for l in valides if any(_famille(c) == fam for c in l["claims"])]
        proposes = [l["nom"] for l in valides
                    if l["nom"] not in confirmes and any(_famille(c) == fam for c in l["claims_proposes"])]
        couverture.append({
            "code": code,
            "label": FSC_CLAIM_LABELS.get(code) or FSC_CLAIMS_PORTEE.get(code, {}).get("label", code),
            **besoins[code],
            "fournisseurs_confirmes": confirmes,
            "fournisseurs_proposes": proposes,
        })

    stats = {
        "fournisseurs": len(lignes),
        "expires": sum(1 for l in lignes if l["statut"] == "expire"),
        "a_renouveler": sum(1 for l in lignes if l["statut"] == "a_renouveler"),
        "sans_document": sum(1 for l in lignes if not l["document"]),
        "non_controles": sum(1 for l in lignes if not l["dernier_controle"] or l["dernier_controle"]["a_refaire"]),
        "sans_categorie": sum(1 for l in lignes if not l["claims"]),
    }
    a_lire = sorted({l["document"]["id"] for l in lignes
                     if l["document"] and not l["document"]["lecture"]})
    return {
        "fournisseurs": lignes,
        "couverture": couverture,
        "stats": stats,
        "documents_a_lire": a_lire,
    }


# ══════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════

@router.get("/api/qualite/fsc/synthese")
def fsc_synthese(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        data = _synthese(conn)
    for l in data["fournisseurs"]:
        if l["document"]:
            l["document"].pop("filename", None)
    data.update({
        "claims_catalogue": [{"code": k, "label": v["label"]} for k, v in FSC_CLAIMS_PORTEE.items()],
        "statuts_base": [{"code": k, "label": v} for k, v in FSC_STATUTS_BASE.items()],
        "base_recherche_url": FSC_BASE_RECHERCHE_URL,
        "licence_sifa": FSC_LICENCE_SIFA,
        "alerte_jours": FSC_ALERTE_JOURS,
        "controle_validite_jours": FSC_CONTROLE_VALIDITE_JOURS,
    })
    return data


@router.get("/api/qualite/fsc/dossier.pdf")
def fsc_dossier_pdf(request: Request, ids: str = "", inline: int = 1):
    """Le dossier FSC fournisseurs : page de garde + certificats, un seul PDF."""
    user = _require_qualite_view(request)
    wanted = {int(t) for t in (ids or "").split(",") if t.strip().isdigit()}
    with get_db() as conn:
        data = _synthese(conn, wanted or None)
    lignes = data["fournisseurs"]
    if not lignes:
        raise HTTPException(status_code=404, detail="Aucun fournisseur certifié FSC à inclure.")
    aujourdhui = date.today()
    sous_titre = " · ".join(x for x in [
        APP_ORG_NAME,
        f"licence {FSC_LICENCE_SIFA}" if FSC_LICENCE_SIFA else "",
        f"édité le {aujourdhui.strftime('%d/%m/%Y')}",
        f"par {user.get('nom')}" if user.get("nom") else "",
        f"{len(lignes)} fournisseur(s)",
    ] if x)
    try:
        pdf = construire_dossier_pdf(
            lignes, RESSOURCES_UPLOAD_DIR,
            titre="Fournisseurs certifiés FSC", sous_titre=sous_titre,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fusion des certificats impossible : {e}")
    nom = f"Dossier_FSC_fournisseurs_{aujourdhui.isoformat()}.pdf"
    dispo = "inline" if inline else "attachment"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{dispo}; filename="{nom}"', "Cache-Control": "no-store"},
    )


@router.post("/api/qualite/fsc/certificats/{cert_id}/lecture")
def fsc_lire_certificat(cert_id: int, request: Request):
    """Lit un certificat déposé et range la PROPOSITION sur sa ligne."""
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT c.*, f.nom AS fournisseur_nom
                 FROM qualite_fournisseur_certificats c
                 JOIN fournisseurs_fsc f ON f.id = c.fournisseur_id
                WHERE c.id=?""",
            (cert_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Certificat introuvable.")
        d = dict(row)
    chemin = os.path.join(RESSOURCES_UPLOAD_DIR, d["filename"])
    if not os.path.isfile(chemin):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur — redéposer le certificat.")
    with open(chemin, "rb") as fh:
        contenu = fh.read()

    lecture = lire_certificat(contenu, d.get("original_name") or d["filename"], d.get("mime_type") or "")

    with get_db() as conn:
        conn.execute(
            """UPDATE qualite_fournisseur_certificats
                  SET fsc_lecture_le=?, fsc_lecture_methode=?, fsc_lecture_modele=?,
                      fsc_licence_lue=?, fsc_certificat_lu=?, fsc_expiration_lue=?,
                      fsc_claims_lus=?, fsc_lecture_note=?
                WHERE id=?""",
            (
                _now(), lecture["methode"], lecture.get("modele"),
                ", ".join(lecture.get("licences") or []) or None,
                lecture.get("certificat"), lecture.get("expiration"),
                json.dumps(lecture.get("claims") or [], ensure_ascii=False),
                lecture.get("note") or "",
                cert_id,
            ),
        )
        conn.commit()
    log_action(
        user=user, action="UPDATE", module="qualite", request=request,
        objet=f"Lecture certificat FSC · {d['fournisseur_nom']} · {d.get('original_name') or ''}",
        detail={"certificat_id": cert_id, "methode": lecture["methode"],
                "claims": [c["code"] for c in lecture.get("claims") or []]},
    )
    for c in lecture.get("claims") or []:
        c["label"] = FSC_CLAIMS_PORTEE[c["code"]]["label"]
    return lecture


@router.get("/api/qualite/fsc/fournisseurs/{four_id}/controles")
def fsc_liste_controles(four_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, date_controle, statut_base, licence, date_expiration_lue, claims, source,
                      certificat_id, note, justificatif_original, fiche_maj, ancienne_expiration,
                      created_at, created_by_nom
                 FROM qualite_fsc_controles
                WHERE fournisseur_id=?
                ORDER BY date_controle DESC, id DESC""",
            (four_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["claims"] = _json_list(d.get("claims"))
        d["claims_labels"] = _claims_labels(d["claims"])
        d["statut_label"] = FSC_STATUTS_BASE.get(d["statut_base"], d["statut_base"])
        d["justificatif"] = bool(d.pop("justificatif_original", None))
        out.append(d)
    return {"controles": out}


@router.post("/api/qualite/fsc/fournisseurs/{four_id}/controles")
async def fsc_enregistrer_controle(
    four_id: int,
    request: Request,
    date_controle: str = Form(""),
    statut_base: str = Form(...),
    date_expiration: str = Form(""),
    claims: str = Form(""),
    note: str = Form(""),
    certificat_id: str = Form(""),
    maj_fiche: str = Form("0"),
    justificatif: Optional[UploadFile] = File(None),
):
    """Enregistre un contrôle du certificat sur la base FSC.

    C'est la seule écriture qui fixe les catégories d'un fournisseur. Le contrôle
    n'écrase jamais le précédent. `maj_fiche=1` reporte la date d'expiration lue
    sur la fiche fournisseur, celle qui valide les réceptions.
    """
    user = _require_qualite_access(request)

    statut = (statut_base or "").strip()
    if statut not in FSC_STATUTS_BASE:
        raise HTTPException(status_code=400, detail="Statut sur la base FSC invalide.")
    jour = _iso(date_controle) or date.today().isoformat()
    if jour > date.today().isoformat():
        raise HTTPException(status_code=400, detail="Date de contrôle dans le futur.")
    expiration = _iso(date_expiration)
    codes = []
    for tok in (claims or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok not in FSC_CLAIMS_PORTEE:
            raise HTTPException(status_code=400, detail=f"Catégorie FSC inconnue : {tok}.")
        if tok not in codes:
            codes.append(tok)
    cert_id = int(certificat_id) if (certificat_id or "").strip().isdigit() else None

    fichier = None
    if justificatif is not None and justificatif.filename:
        original = _sanitize_filename(justificatif.filename)
        ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if ext not in _JUSTIF_TYPES:
            raise HTTPException(status_code=400, detail="Justificatif : PDF, PNG, JPG ou WEBP uniquement.")
        contenu = await justificatif.read()
        if len(contenu) > _JUSTIF_MAX_OCTETS:
            raise HTTPException(status_code=400, detail="Justificatif trop lourd — 15 Mo maximum.")
        nom_disque = f"fsc_ctrl_{four_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
        with open(os.path.join(FSC_CONTROLES_DIR, nom_disque), "wb") as fh:
            fh.write(contenu)
        fichier = (nom_disque, original, _JUSTIF_TYPES[ext])

    with get_db() as conn:
        four = conn.execute(
            "SELECT id, nom, licence, fsc_date_expiration FROM fournisseurs_fsc WHERE id=?",
            (four_id,),
        ).fetchone()
        if not four:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        if cert_id is not None and not conn.execute(
            "SELECT 1 FROM qualite_fournisseur_certificats WHERE id=?", (cert_id,)
        ).fetchone():
            cert_id = None

        ancienne = (four["fsc_date_expiration"] or "")[:10] or None
        fiche_maj = 1 if (maj_fiche == "1" and expiration and expiration != ancienne) else 0

        conn.execute(
            """INSERT INTO qualite_fsc_controles
                 (fournisseur_id, date_controle, statut_base, licence, date_expiration_lue, claims,
                  source, certificat_id, note, justificatif_filename, justificatif_original,
                  justificatif_mime, fiche_maj, ancienne_expiration, created_at, created_by, created_by_nom)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                four_id, jour, statut, four["licence"], expiration,
                json.dumps(codes), "base_fsc", cert_id, (note or "").strip(),
                fichier[0] if fichier else None, fichier[1] if fichier else None,
                fichier[2] if fichier else None,
                fiche_maj, ancienne if fiche_maj else None,
                _now(), user.get("id"), user.get("nom"),
            ),
        )
        ctrl_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        if fiche_maj:
            conn.execute(
                "UPDATE fournisseurs_fsc SET fsc_date_expiration=?, updated_at=? WHERE id=?",
                (expiration, _now(), four_id),
            )
        conn.commit()

    log_action(
        user=user, action="VALIDATE", module="qualite", request=request,
        objet=f"Contrôle FSC · {four['nom']} · {four['licence'] or 'sans licence'} · {FSC_STATUTS_BASE[statut]}",
        detail={
            "controle_id": ctrl_id, "date_controle": jour, "claims": codes,
            "date_expiration_lue": expiration,
            "fiche_expiration": {"avant": ancienne, "apres": expiration} if fiche_maj else None,
        },
    )
    return {"ok": True, "controle_id": ctrl_id, "fiche_maj": bool(fiche_maj)}


@router.get("/api/qualite/fsc/controles/{ctrl_id}/justificatif")
def fsc_justificatif(ctrl_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT justificatif_filename, justificatif_original FROM qualite_fsc_controles WHERE id=?",
            (ctrl_id,),
        ).fetchone()
    if not row or not row["justificatif_filename"]:
        raise HTTPException(status_code=404, detail="Aucun justificatif pour ce contrôle.")
    chemin = os.path.join(FSC_CONTROLES_DIR, row["justificatif_filename"])
    if not os.path.isfile(chemin):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur.")
    ext = row["justificatif_filename"].rsplit(".", 1)[-1].lower()
    # Type déduit de l'extension, jamais du type annoncé par le navigateur :
    # la liste fermée garantit que rien d'exécutable n'est servi en ligne.
    media = _JUSTIF_TYPES.get(ext)
    if not media:
        raise HTTPException(status_code=404, detail="Type de fichier non servi.")
    nom = _sanitize_filename(row["justificatif_original"] or row["justificatif_filename"])
    return FileResponse(chemin, media_type=media,
                        headers={"Content-Disposition": f'inline; filename="{nom}"'})
