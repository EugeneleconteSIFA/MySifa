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
import logging
import os
import re
import shutil
import uuid
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
from app.services import fsc_registre as registre
from app.services.erp_mirror import get_erp_db, miroir_present
from app.services.fsc_classification import (
    catalogue_portees,
    # Aliasée : `couverture` est déjà le nom de la liste de couverture par
    # catégorie dans _synthese(), et une variable locale du même nom rendrait la
    # fonction inappelable dans toute la portée de _synthese (UnboundLocalError).
    couverture as calcul_couverture,
    libelle_portee,
    nettoyer_liste,
)
from app.services.fsc_lecture_certificat import lire_certificat
from app.services import fsc_import_controles as importlot
from config import (
    APP_ORG_NAME,
    FSC_ALERTE_JOURS,
    FSC_ALLEGATIONS,
    FSC_BASE_RECHERCHE_URL,
    FSC_CLAIM_LABELS,
    FSC_CLAIMS_PORTEE,
    FSC_CONTROLE_VALIDITE_JOURS,
    FSC_ETIQUETTES,
    FSC_FICHE_SLUG,
    FSC_LICENCE_SIFA,
    FSC_STATUTS_BASE,
    UPLOAD_DIR,
)

logger = logging.getLogger(__name__)

router = APIRouter()

FSC_CONTROLES_DIR = os.path.join(UPLOAD_DIR, "qualite", "fsc-controles")
os.makedirs(FSC_CONTROLES_DIR, exist_ok=True)

# Lot déposé en attente de validation. Rien n'est écrit en base tant que
# quelqu'un n'a pas relu la proposition ; les fichiers patientent ici.
FSC_IMPORTS_DIR = os.path.join(UPLOAD_DIR, "qualite", "fsc-imports")
os.makedirs(FSC_IMPORTS_DIR, exist_ok=True)
_IMPORT_MAX_FICHIERS = 60
_IMPORT_MAX_OCTETS = 20 * 1024 * 1024
_IMPORT_RETENTION_H = 24

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


def _portees_labels(codes: list[str]) -> list[str]:
    return [libelle_portee(c) for c in codes]


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
    # La portée lue suit la même règle que les claims : proposition, jamais
    # validation. Elle ne pré-remplit le contrôle que pour épargner une saisie.
    portees = []
    for p in _json_list(d.get("fsc_portees_lues")):
        code = p.get("code") if isinstance(p, dict) else p
        entree = dict(p) if isinstance(p, dict) else {"code": code}
        entree["code"] = code
        entree["label"] = libelle_portee(code)
        portees.append(entree)
    return {
        "le": d.get("fsc_lecture_le"),
        "methode": d.get("fsc_lecture_methode"),
        "licence": d.get("fsc_licence_lue"),
        "certificat": d.get("fsc_certificat_lu"),
        "expiration": d.get("fsc_expiration_lue"),
        "claims": claims,
        "portees": portees,
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
            "portees": _json_list(d.get("portees")),
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


def _sorties(conn) -> list[dict]:
    """Fournisseurs retirés de la liste FSC, avec la raison et sa date.

    « Ne pas supprimer, désactiver » ne suffit pas pour un audit : une fiche qui
    disparaît de l'écran ne prouve rien. L'auditeur demande pourquoi tel
    fournisseur n'est plus dans la liste, et la réponse est le dernier contrôle
    enregistré avant la sortie — sa date, ce que la base FSC affichait ce
    jour-là, et la note qui dit ce qu'on en a conclu.

    Une fiche jamais certifiée et jamais contrôlée n'a rien à faire ici : elle
    n'est pas sortie de la liste, elle n'y est jamais entrée.
    """
    controles = _derniers_controles(conn)
    out = []
    for r in conn.execute(
        """SELECT id, nom, licence, certificat, fsc_date_expiration
             FROM fournisseurs_fsc
            WHERE COALESCE(has_fsc,1)=0 AND COALESCE(actif,1)=1
            ORDER BY nom COLLATE NOCASE"""
    ).fetchall():
        f = dict(r)
        ctrl = controles.get(f["id"])
        if not ctrl and not f.get("licence"):
            continue
        out.append({
            "id": f["id"],
            "nom": f["nom"],
            "licence": f.get("licence"),
            "certificat": f.get("certificat"),
            "expiration": (f.get("fsc_date_expiration") or "")[:10] or None,
            "dernier_controle": ctrl,
            "motif": (ctrl or {}).get("note") or "",
        })
    return out


def _synthese(conn, ids: Optional[set[int]] = None) -> dict:
    fours = [dict(r) for r in conn.execute(
        """SELECT id, nom, licence, certificat, groupe, branche, fsc_date_expiration,
                  fsc_portees_achetees
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
            portees, portees_source = ctrl.get("portees") or [], "controle"
        else:
            claims, claims_source = [], None
            portees, portees_source = [], None
        proposes = [c["code"] for c in (lecture or {}).get("claims", []) if c["code"] not in claims]
        portees_proposees = [p["code"] for p in (lecture or {}).get("portees", [])
                             if p.get("code") and p["code"] not in portees]
        # Ce que SIFA achète à ce fournisseur, confronté à ce que le certificat
        # couvre. Seul le contrôle compte comme portée : une portée seulement
        # « lue » sur le certificat ne doit ni rassurer ni alerter.
        achats = nettoyer_liste(_json_list(f.get("fsc_portees_achetees")))
        couv = calcul_couverture(portees, achats)

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
        # La portée qui ne couvre pas ce qu'on achète est une alerte : la
        # matière livrée ne peut pas porter d'allégation FSC. Une portée pas
        # encore saisie n'en est pas une — l'écran a sa propre colonne pour ça.
        if couv["alerte"]:
            alertes.append("Portée du certificat : %s non couvert%s"
                           % (", ".join(_portees_labels(couv["manquants"])),
                              "s" if len(couv["manquants"]) > 1 else ""))
        elif couv["partielle"]:
            alertes.append("Portée partielle : %s non couvert%s"
                           % (", ".join(_portees_labels(couv["manquants"])),
                              "s" if len(couv["manquants"]) > 1 else ""))

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
            "portees": nettoyer_liste(portees),
            "portees_labels": _portees_labels(nettoyer_liste(portees)),
            "portees_source": portees_source,
            "portees_proposees": nettoyer_liste(portees_proposees),
            "portees_achetees": achats,
            "portees_achetees_labels": _portees_labels(achats),
            "couverture": couv,
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
        "sans_portee": sum(1 for l in lignes if not l["portees"]),
        "portee_non_couvrante": sum(1 for l in lignes if l["couverture"]["alerte"]),
    }
    a_lire = sorted({l["document"]["id"] for l in lignes
                     if l["document"] and not l["document"]["lecture"]})
    return {
        "fournisseurs": lignes,
        "couverture": couverture,
        "sorties": _sorties(conn),
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
        "portees_catalogue": catalogue_portees(),
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
            """SELECT id, date_controle, statut_base, licence, date_expiration_lue, claims, portees, source,
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
        d["portees"] = _json_list(d.get("portees"))
        d["portees_labels"] = _portees_labels(d["portees"])
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
    portees: str = Form(""),
    note: str = Form(""),
    certificat_id: str = Form(""),
    maj_fiche: str = Form("0"),
    justificatif: Optional[UploadFile] = File(None),
):
    """Enregistre un contrôle du certificat sur la base FSC.

    C'est la seule écriture qui fixe les allégations ET la portée produit d'un
    fournisseur. Le contrôle n'écrase jamais le précédent. `maj_fiche=1` reporte
    la date d'expiration lue sur la fiche fournisseur, celle qui valide les
    réceptions.

    Deux listes, deux questions : `claims` dit sous quelle allégation le
    fournisseur peut livrer, `portees` dit ce que son certificat couvre. Un
    certificat FSC Mix valide qui ne couvre pas P7.8 reste un certificat valide
    — il ne couvre simplement pas les étiquettes adhésives.
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
    # La portée est normalisée, jamais refusée : un code d'une version du
    # standard que le référentiel ne connaît pas encore doit pouvoir être saisi,
    # c'est ce qui est écrit sur le dossier de certification qui fait foi.
    codes_portee = nettoyer_liste((portees or "").split(","))
    refuses = [t.strip() for t in (portees or "").split(",")
               if t.strip() and not nettoyer_liste([t])]
    if refuses:
        raise HTTPException(
            status_code=400,
            detail="Code de portée invalide : %s — format attendu P7.8." % ", ".join(refuses))

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
                  portees, source, certificat_id, note, justificatif_filename, justificatif_original,
                  justificatif_mime, fiche_maj, ancienne_expiration, created_at, created_by, created_by_nom)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                four_id, jour, statut, four["licence"], expiration,
                json.dumps(codes), json.dumps(codes_portee),
                "base_fsc", cert_id, (note or "").strip(),
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
        # Les lignes de registre importées avant ce contrôle n'avaient aucune
        # portée à opposer et sortaient en « à vérifier ». Le premier contrôle
        # d'un fournisseur vient les chercher — sans quoi elles y resteraient.
        # Ne touche que celles dont la portée est encore nulle : une portée déjà
        # figée ne se réécrit pas.
        try:
            lignes_reprises = registre.reprendre_portee(conn, four_id, user.get("nom"))
        except Exception:
            # Le contrôle est enregistré ; une reprise qui échoue ne doit pas le
            # faire perdre. Les lignes restent « à vérifier », ce qui se voit.
            logger.warning("Reprise de portée du registre FSC échouée", exc_info=True)
            lignes_reprises = 0

    log_action(
        user=user, action="VALIDATE", module="qualite", request=request,
        objet=f"Contrôle FSC · {four['nom']} · {four['licence'] or 'sans licence'} · {FSC_STATUTS_BASE[statut]}",
        detail={
            "controle_id": ctrl_id, "date_controle": jour, "claims": codes,
            "portees": codes_portee, "registre_lignes_reprises": lignes_reprises,
            "date_expiration_lue": expiration,
            "fiche_expiration": {"avant": ancienne, "apres": expiration} if fiche_maj else None,
        },
    )
    return {"ok": True, "controle_id": ctrl_id, "fiche_maj": bool(fiche_maj),
            "registre_lignes_reprises": lignes_reprises}


@router.put("/api/qualite/fsc/fournisseurs/{four_id}/portees-achetees")
def fsc_portees_achetees(four_id: int, body: dict, request: Request):
    """Ce que SIFA achète à ce fournisseur, en codes de FSC-STD-40-004a.

    L'autre moitié de la question « ce certificat couvre-t-il ce que nous
    achetons ? ». La portée du certificat vient du contrôle et se fige ; ce
    champ-ci décrit nos achats, il vit avec eux et s'édite librement.

    Amorcé par migration depuis les catégories matière internes (complexe,
    frontal, glassine…), il reste éditable parce que la correspondance est une
    approximation : c'est le seul endroit où quelqu'un qui connaît le
    fournisseur peut trancher.
    """
    user = _require_qualite_access(request)
    brut = (body or {}).get("portees")
    if isinstance(brut, str):
        brut = brut.split(",")
    if not isinstance(brut, list):
        raise HTTPException(status_code=400, detail="Portées attendues sous forme de liste.")

    codes = nettoyer_liste(brut)
    refuses = [str(t).strip() for t in brut if str(t).strip() and not nettoyer_liste([t])]
    if refuses:
        raise HTTPException(
            status_code=400,
            detail="Code de portée invalide : %s — format attendu P7.8." % ", ".join(refuses))

    with get_db() as conn:
        four = conn.execute(
            "SELECT id, nom, fsc_portees_achetees FROM fournisseurs_fsc WHERE id=?", (four_id,)
        ).fetchone()
        if not four:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        avant = nettoyer_liste(_json_list(four["fsc_portees_achetees"]))
        conn.execute(
            "UPDATE fournisseurs_fsc SET fsc_portees_achetees=?, updated_at=? WHERE id=?",
            (json.dumps(codes), _now(), four_id),
        )
        conn.commit()

    if avant != codes:
        log_action(
            user=user, action="UPDATE", module="qualite", request=request,
            objet="Portées achetées FSC · %s" % four["nom"],
            detail={"fournisseur_id": four_id, "avant": avant, "apres": codes},
        )
    return {"portees_achetees": codes, "portees_achetees_labels": _portees_labels(codes)}


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


# ══════════════════════════════════════════════════════════════════
# Registre des approvisionnements (FSC-STD-40-004 V3-1)
#
# Les lignes viennent du miroir RVGI et se figent à l'import ; quatre champs se
# saisissent ici (n° de facture fournisseur, allégation du BL, allégation de la
# facture, présence du code de certificat) et le verdict d'éligibilité se
# recalcule à chaque saisie. Rien ne se supprime : on corrige, et `fsc_journal`
# garde l'avant et l'après.
# ══════════════════════════════════════════════════════════════════

@router.get("/api/qualite/fsc/appro")
def fsc_appro_liste(
    request: Request,
    debut: str = "", fin: str = "", eligible: str = "",
    fournisseur_id: str = "", certifies: int = 0, q: str = "",
):
    _require_qualite_view(request)
    with get_db() as conn:
        lignes = registre.lister(
            conn,
            debut=_iso(debut), fin=_iso(fin),
            fournisseur_id=int(fournisseur_id) if str(fournisseur_id).isdigit() else None,
            eligible=(eligible or "").strip() or None,
            certifies_seuls=bool(certifies),
            recherche=(q or "").strip() or None,
        )
        depuis = registre.date_entree(conn)
        fours = [dict(r) for r in conn.execute(
            "SELECT id, nom, licence, rvgi_numero FROM fournisseurs_fsc "
            "WHERE COALESCE(has_fsc,1)=1 AND COALESCE(actif,1)=1 ORDER BY nom COLLATE NOCASE"
        ).fetchall()]
    return {
        "lignes": lignes,
        "stats": registre.stats(lignes),
        "volumes": registre.volumes_par_allegation(lignes),
        "date_entree": depuis,
        "miroir_present": miroir_present(),
        "allegations": [{"code": k, "libelle": v["libelle"], "pct": v["pct"]}
                        for k, v in FSC_ALLEGATIONS.items()],
        "etiquettes": [{"code": k, "libelle": v} for k, v in FSC_ETIQUETTES.items()],
        "fournisseurs": fours,
    }


@router.put("/api/qualite/fsc/appro/parametres")
def fsc_appro_parametres(body: dict, request: Request):
    """La date d'entrée dans la chaîne de contrôle. Tant qu'elle est vide, rien
    ne s'importe — c'est elle qui borne tout le registre."""
    user = _require_qualite_access(request)
    jour = (body or {}).get("date_entree") or ""
    with get_db() as conn:
        avant = registre.date_entree(conn)
        try:
            jour = registre.definir_date_entree(conn, jour, user.get("nom"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Date invalide — format AAAA-MM-JJ attendu.")
    log_action(user=user, action="UPDATE", module="qualite", request=request,
               objet="Registre FSC · date d'entrée dans la chaîne de contrôle",
               detail={"avant": avant, "apres": jour})
    return {"date_entree": jour}


@router.get("/api/qualite/fsc/appro/export.xlsx")
def fsc_appro_export(request: Request, debut: str = "", fin: str = "",
                     eligible: str = "", certifies: int = 0, q: str = ""):
    _require_qualite_view(request)
    with get_db() as conn:
        lignes = registre.lister(
            conn, debut=_iso(debut), fin=_iso(fin),
            eligible=(eligible or "").strip() or None,
            certifies_seuls=bool(certifies),
            recherche=(q or "").strip() or None,
        )
    contenu = registre.export_xlsx(lignes, _iso(debut), _iso(fin))
    nom = "Registre_FSC_approvisionnements_%s.xlsx" % date.today().isoformat()
    return Response(
        content=contenu,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nom}"',
                 "Cache-Control": "no-store"},
    )


@router.post("/api/qualite/fsc/appro/import")
def fsc_appro_import(request: Request):
    """Ajoute les réceptions RVGI postérieures à la date d'entrée. N'écrase rien."""
    user = _require_qualite_access(request)
    if not miroir_present():
        raise HTTPException(status_code=503, detail="Miroir RVGI absent — la synchro n'a pas encore tourné.")
    with get_db() as conn:
        if not registre.date_entree(conn):
            raise HTTPException(
                status_code=400,
                detail="Renseigner d'abord la date d'entrée dans la chaîne de contrôle.")
        with get_erp_db() as conn_erp:
            bilan = registre.importer(conn, conn_erp, user.get("nom"))
    if bilan.get("erreur"):
        raise HTTPException(status_code=400, detail=bilan["erreur"])
    log_action(user=user, action="CREATE", module="qualite", request=request,
               objet="Import registre FSC · %d réception(s)" % bilan["ajoutees"],
               detail=bilan)
    return bilan


@router.patch("/api/qualite/fsc/appro/{ligne_id}")
def fsc_appro_saisie(ligne_id: int, body: dict, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        try:
            ligne = registre.mettre_a_jour(conn, ligne_id, body or {}, user.get("nom"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="qualite", request=request,
               objet="Registre FSC · %s · BL %s" % (ligne.get("fournisseur_rvgi") or "?",
                                                    ligne.get("num_bl") or "?"),
               detail={"ligne_id": ligne_id, "eligible": ligne.get("eligible"),
                       "champs": sorted((body or {}).keys())})
    return ligne


@router.post("/api/qualite/fsc/appro/{ligne_id}/appliquer-bl")
def fsc_appro_appliquer_bl(ligne_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        try:
            n = registre.appliquer_au_bl(conn, ligne_id, user.get("nom"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="qualite", request=request,
               objet="Registre FSC · saisie appliquée à %d ligne(s) du même BL" % n,
               detail={"ligne_id": ligne_id, "lignes": n})
    return {"appliquees": n}


@router.post("/api/qualite/fsc/appro/{ligne_id}/rattacher")
def fsc_appro_rattacher(ligne_id: int, body: dict, request: Request):
    """Rattache le tiers RVGI de cette ligne à une fiche de l'annuaire.

    « ARCONVERT S.A » côté ERP et « Fedrigoni Manter » côté MySifa sont le même
    fournisseur : aucune comparaison de noms ne le devine, seul un humain le sait.
    Le numéro est mémorisé sur la fiche, et toutes les lignes du même tiers
    suivent.
    """
    user = _require_qualite_access(request)
    fid = (body or {}).get("fournisseur_id")
    if not str(fid or "").isdigit():
        raise HTTPException(status_code=400, detail="Fournisseur à rattacher manquant.")
    with get_db() as conn:
        ligne = conn.execute(
            "SELECT numfou, fournisseur_rvgi FROM fsc_reception WHERE id = ?", (ligne_id,)
        ).fetchone()
        if not ligne:
            raise HTTPException(status_code=404, detail="Ligne de registre introuvable.")
        if ligne["numfou"] is None:
            raise HTTPException(status_code=400, detail="Cette ligne n'a pas de tiers RVGI.")
        try:
            n = registre.rattacher_fournisseur(
                conn, int(ligne["numfou"]), int(fid), ligne["fournisseur_rvgi"], user.get("nom"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="qualite", request=request,
               objet="Registre FSC · tiers RVGI %s rattaché" % ligne["fournisseur_rvgi"],
               detail={"numfou": ligne["numfou"], "fournisseur_id": int(fid), "lignes": n})
    return {"lignes_reprises": n}


@router.get("/api/qualite/fsc/appro/{ligne_id}/journal")
def fsc_appro_journal(ligne_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return {"journal": registre.journal(conn, ligne_id)}


# ══════════════════════════════════════════════════════════════════
# Import d'un lot de contrôles
# ══════════════════════════════════════════════════════════════════
#
# Le contrôle unitaire au-dessus reste la référence : une fiche, un humain, une
# décision. Mais une campagne semestrielle, c'est dix-huit dossiers relevés le
# même jour sur la base FSC, et les redéposer un par un revient à recopier
# dix-huit dates d'expiration à la main. On sait ce que ça donne : sept fiches
# sur dix-sept portaient une date fausse avant le premier import.
#
# Deux temps, jamais un seul : `analyse` lit le lot et propose, `appliquer`
# écrit ce qu'un humain a validé. Entre les deux, les fichiers patientent dans
# FSC_IMPORTS_DIR sous un jeton, avec le propriétaire du lot.


def _import_purge() -> None:
    """Oublie les lots qu'on n'a jamais validés. Best effort."""
    limite = datetime.now().timestamp() - _IMPORT_RETENTION_H * 3600
    try:
        for nom in os.listdir(FSC_IMPORTS_DIR):
            chemin = os.path.join(FSC_IMPORTS_DIR, nom)
            if os.path.isdir(chemin) and os.path.getmtime(chemin) < limite:
                shutil.rmtree(chemin, ignore_errors=True)
    except OSError:
        pass


def _import_dossier(jeton: str) -> str:
    """Dossier du lot. Le jeton est validé — il vient de l'URL."""
    if not re.fullmatch(r"[0-9a-f]{32}", jeton or ""):
        raise HTTPException(status_code=404, detail="Lot introuvable.")
    chemin = os.path.join(FSC_IMPORTS_DIR, jeton)
    if not os.path.isdir(chemin):
        raise HTTPException(status_code=404, detail="Lot expiré ou déjà appliqué.")
    return chemin


def _import_lot(jeton: str, user: dict) -> tuple[str, dict]:
    chemin = _import_dossier(jeton)
    try:
        with open(os.path.join(chemin, "_lot.json"), encoding="utf-8") as fh:
            lot = json.load(fh)
    except OSError:
        raise HTTPException(status_code=404, detail="Lot illisible — le redéposer.")
    if lot.get("user_id") and user.get("id") and lot["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Ce lot a été déposé par quelqu'un d'autre.")
    # Le nettoyage du dossier ne suffit pas à fermer un lot : sur un poste de
    # développement monté depuis Windows, `unlink` est refusé et le dossier
    # survit à la purge. C'est le marqueur en JSON qui fait foi, pas le disque.
    if lot.get("applique_le"):
        raise HTTPException(status_code=409,
                            detail="Ce lot a déjà été importé le %s." % lot["applique_le"])
    return chemin, lot


def _avertissements(lu: dict, fiche: Optional[dict]) -> list[str]:
    out: list[str] = []
    statut = lu.get("statut_base")
    if statut != "valide":
        out.append("Certificat %s sur la base FSC." % FSC_STATUTS_BASE.get(statut, statut))
    exp = lu.get("date_expiration_lue")
    if exp:
        try:
            reste = (datetime.strptime(exp, "%Y-%m-%d").date() - date.today()).days
            if reste < 0:
                out.append("Certificat expiré depuis le %s." % exp)
            elif reste <= FSC_ALERTE_JOURS:
                out.append("Expire dans %s jours (%s)." % (reste, exp))
        except ValueError:
            pass
    if "fsc_controlled_wood" in (lu.get("claims") or []):
        out.append("FSC Controlled Wood autorisé — aucune allégation possible sur le produit fini.")
    if fiche:
        achetees = _json_list(fiche.get("fsc_portees_achetees"))
        manquantes = [c for c in achetees if not importlot.couvre_portee(lu.get("portees") or [], c)]
        if achetees and manquantes:
            out.append("Portée non couverte pour ce que SIFA achète : %s." % ", ".join(manquantes))
        nom = (fiche.get("nom") or "").strip().lower()
        titulaire = (lu.get("titulaire") or "").strip().lower()
        if nom and titulaire and nom not in titulaire:
            out.append("Titulaire du certificat : %s" % (lu.get("titulaire") or "").rstrip("."))
    if lu.get("sites_expires"):
        out.append("%s site(s) expiré(s) au certificat — vérifier l'entité qui facture SIFA."
                   % lu["sites_expires"])
    for a in lu.get("avertissements") or []:
        out.append(a)
    return out


@router.post("/api/qualite/fsc/controles/import")
async def fsc_import_analyser(request: Request, fichiers: list[UploadFile] = File(...)):
    """Dépose un lot de dossiers FSC et rend la proposition, sans rien écrire.

    Les PDF sont les FSC Certification Records signés ; le CSV qui les
    accompagne est facultatif et n'apporte que le libellé du fournisseur et la
    décision de le garder ou non dans la liste. Aucune valeur du CSV ne
    remplace une valeur lue dans un dossier.
    """
    user = _require_qualite_access(request)
    _import_purge()
    if len(fichiers) > _IMPORT_MAX_FICHIERS:
        raise HTTPException(status_code=400,
                            detail="Lot trop gros — %s fichiers maximum." % _IMPORT_MAX_FICHIERS)

    jeton = uuid.uuid4().hex
    chemin = os.path.join(FSC_IMPORTS_DIR, jeton)
    os.makedirs(chemin, exist_ok=True)

    meta_csv: dict[str, dict] = {}
    pdfs: list[tuple[str, str]] = []  # (nom d'origine, nom sur disque)
    for i, f in enumerate(fichiers):
        if not f or not f.filename:
            continue
        original = _sanitize_filename(f.filename)
        contenu = await f.read()
        if len(contenu) > _IMPORT_MAX_OCTETS:
            shutil.rmtree(chemin, ignore_errors=True)
            raise HTTPException(status_code=400, detail="%s dépasse 20 Mo." % original)
        ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if ext == "csv":
            meta_csv.update(importlot.lire_csv(contenu))
            continue
        if ext != "pdf":
            continue
        disque = "%03d.pdf" % i
        with open(os.path.join(chemin, disque), "wb") as fh:
            fh.write(contenu)
        pdfs.append((original, disque))

    if not pdfs:
        shutil.rmtree(chemin, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Aucun dossier PDF dans le lot.")

    with get_db() as conn:
        fiches = [dict(r) for r in conn.execute(
            """SELECT id, nom, licence, certificat, fsc_date_expiration, fsc_portees_achetees, has_fsc
                 FROM fournisseurs_fsc WHERE actif=1 ORDER BY has_fsc DESC, nom"""
        ).fetchall()]
        deja = {(r["fournisseur_id"], r["date_controle"][:10])
                for r in conn.execute(
                    "SELECT fournisseur_id, date_controle FROM qualite_fsc_controles").fetchall()}

    lignes = []
    for original, disque in pdfs:
        with open(os.path.join(chemin, disque), "rb") as fh:
            lu = importlot.lire_record(fh.read())
        if not lu.get("ok"):
            lignes.append({"fichier": original, "disque": disque, "ok": False,
                           "erreur": lu.get("erreur"), "avertissements": []})
            continue
        info = meta_csv.get((lu.get("certificat") or "").upper(), {})
        fiche, methode = importlot.rapprocher(fiches, lu, info.get("fournisseur"))
        lignes.append({
            "fichier": original,
            "disque": disque,
            "ok": True,
            "erreur": None,
            "lu": lu,
            "claims_labels": _claims_labels(lu.get("claims") or []),
            "portees_labels": _portees_labels(lu.get("portees") or []),
            "fournisseur_id": fiche["id"] if fiche else None,
            "fournisseur_nom": fiche["nom"] if fiche else None,
            "rapprochement": methode,
            "csv": info or None,
            "ecarts": importlot.ecarts(fiche, lu),
            "avertissements": _avertissements(lu, fiche),
            "deja_importe": bool(fiche and (fiche["id"], lu.get("signe_le")) in deja),
        })

    lot = {"user_id": user.get("id"), "cree_le": _now(), "lignes": lignes}
    with open(os.path.join(chemin, "_lot.json"), "w", encoding="utf-8") as fh:
        json.dump(lot, fh, ensure_ascii=False)

    return {
        "jeton": jeton,
        "lignes": lignes,
        "fournisseurs": [{"id": f["id"], "nom": f["nom"], "certificat": f["certificat"]}
                         for f in fiches],
        "csv_lu": bool(meta_csv),
    }


@router.post("/api/qualite/fsc/controles/import/{jeton}/appliquer")
def fsc_import_appliquer(jeton: str, body: dict, request: Request):
    """Écrit les contrôles validés du lot.

    Une ligne validée produit trois choses : le dossier déposé en pièce sur la
    fiche fournisseur, un contrôle daté de la signature FSC et jamais écrasé,
    et — si on le demande — la correction de la fiche elle-même.

    La correction des codes est le seul ajout par rapport au contrôle unitaire,
    et c'est la raison d'être de l'écran : une fiche dont le code de certificat
    est faux ne se répare pas en relisant son certificat, puisque c'est par ce
    code qu'on croit l'avoir contrôlée.
    """
    user = _require_qualite_access(request)
    chemin, lot = _import_lot(jeton, user)
    par_fichier = {l["disque"]: l for l in lot.get("lignes") or []}

    demandes = (body or {}).get("lignes")
    if not isinstance(demandes, list) or not demandes:
        raise HTTPException(status_code=400, detail="Aucune ligne à importer.")

    fiche_fsc = None
    resultats, ecrits = [], 0
    with get_db() as conn:
        row = conn.execute("SELECT id FROM qualite_ref_fiches WHERE slug=?", (FSC_FICHE_SLUG,)).fetchone()
        fiche_fsc = row["id"] if row else None

        for d in demandes:
            disque = (d or {}).get("disque")
            ligne = par_fichier.get(disque)
            if not ligne or not ligne.get("ok"):
                resultats.append({"disque": disque, "ok": False, "erreur": "Ligne inconnue dans ce lot."})
                continue
            four_id = d.get("fournisseur_id") or ligne.get("fournisseur_id")
            if not four_id:
                resultats.append({"disque": disque, "ok": False,
                                  "erreur": "Aucune fiche fournisseur rapprochée."})
                continue
            four = conn.execute(
                "SELECT id, nom, licence, certificat, fsc_date_expiration FROM fournisseurs_fsc WHERE id=?",
                (int(four_id),),
            ).fetchone()
            if not four:
                resultats.append({"disque": disque, "ok": False, "erreur": "Fournisseur introuvable."})
                continue

            lu = ligne["lu"]
            jour = lu.get("signe_le") or _iso(d.get("date_controle")) or date.today().isoformat()
            if not d.get("forcer") and conn.execute(
                """SELECT 1 FROM qualite_fsc_controles
                    WHERE fournisseur_id=? AND date_controle=? AND COALESCE(licence,'')=?""",
                (four["id"], jour, lu.get("licence") or four["licence"] or ""),
            ).fetchone():
                resultats.append({"disque": disque, "ok": False, "fournisseur_nom": four["nom"],
                                  "erreur": "Un contrôle du %s existe déjà pour ce certificat." % jour})
                continue
            if jour > date.today().isoformat():
                resultats.append({"disque": disque, "ok": False,
                                  "erreur": "Date de contrôle dans le futur."})
                continue
            source = os.path.join(chemin, disque)
            if not os.path.isfile(source):
                resultats.append({"disque": disque, "ok": False, "erreur": "Fichier absent du lot."})
                continue
            with open(source, "rb") as fh:
                contenu = fh.read()

            claims = [c for c in (lu.get("claims") or []) if c in FSC_CLAIMS_PORTEE]
            portees = nettoyer_liste(lu.get("portees") or [])
            horo = datetime.now().strftime("%Y%m%d%H%M%S%f")

            # 1. Le dossier entre en pièce sur la fiche, avec sa lecture.
            cert_id = None
            if d.get("deposer_certificat", True):
                nom_disque = "fsc_record_%s_%s.pdf" % (four["id"], horo)
                with open(os.path.join(RESSOURCES_UPLOAD_DIR, nom_disque), "wb") as fh:
                    fh.write(contenu)
                conn.execute(
                    """INSERT INTO qualite_fournisseur_certificats
                         (fournisseur_id, filename, original_name, mime_type, size_bytes,
                          titre, date_emission, date_expiration, commentaire, uploaded_at, uploaded_by,
                          fsc_lecture_le, fsc_lecture_methode, fsc_licence_lue, fsc_certificat_lu,
                          fsc_expiration_lue, fsc_claims_lus, fsc_portees_lues, fsc_lecture_note)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        four["id"], nom_disque, ligne["fichier"], "application/pdf", len(contenu),
                        "FSC Certification Record · %s" % (lu.get("certificat") or ""),
                        lu.get("date_premiere_emission"), lu.get("date_expiration_lue"),
                        "Dossier officiel téléchargé sur la base publique FSC le %s." % jour,
                        _now(), user.get("id"),
                        _now(), "dossier_fsc", lu.get("licence"), lu.get("certificat"),
                        lu.get("date_expiration_lue"),
                        json.dumps([{"code": c} for c in claims], ensure_ascii=False),
                        json.dumps([{"code": p} for p in portees], ensure_ascii=False),
                        "Lu dans le FSC Certification Record signé le %s." % (lu.get("signe_horodatage") or jour),
                    ),
                )
                cert_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                if fiche_fsc:
                    conn.execute(
                        "INSERT OR IGNORE INTO qualite_fournisseur_certificat_fiches (certificat_id, fiche_id) VALUES (?,?)",
                        (cert_id, fiche_fsc),
                    )

            # 2. Le même dossier sert de justificatif au contrôle : la preuve
            #    doit rester attachée même si la pièce est retirée un jour.
            justif = "fsc_ctrl_%s_%s.pdf" % (four["id"], horo)
            with open(os.path.join(FSC_CONTROLES_DIR, justif), "wb") as fh:
                fh.write(contenu)

            ancienne = (four["fsc_date_expiration"] or "")[:10] or None
            expiration = lu.get("date_expiration_lue")
            maj = bool(d.get("maj_fiche", True))
            fiche_maj = 1 if (maj and expiration and expiration != ancienne) else 0

            conn.execute(
                """INSERT INTO qualite_fsc_controles
                     (fournisseur_id, date_controle, statut_base, licence, date_expiration_lue, claims,
                      portees, source, certificat_id, note, justificatif_filename, justificatif_original,
                      justificatif_mime, fiche_maj, ancienne_expiration, created_at, created_by, created_by_nom)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    four["id"], jour, lu.get("statut_base") or "introuvable",
                    lu.get("licence") or four["licence"], expiration,
                    json.dumps(claims), json.dumps(portees),
                    "base_fsc", cert_id,
                    (d.get("note") or "").strip()
                    or "Import de lot · dossier signé FSC le %s." % (lu.get("signe_horodatage") or jour),
                    justif, ligne["fichier"], "application/pdf",
                    fiche_maj, ancienne if fiche_maj else None,
                    _now(), user.get("id"), user.get("nom"),
                ),
            )
            ctrl_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

            # 3. La fiche. L'expiration suit le contrôle unitaire ; les codes ne
            #    bougent que si on l'a demandé, et l'avant/après part au journal.
            champs, valeurs, codes_avant = [], [], {}
            if fiche_maj:
                champs.append("fsc_date_expiration=?")
                valeurs.append(expiration)
            if d.get("maj_codes") and lu.get("licence") and lu["licence"] != (four["licence"] or None):
                codes_avant["licence"] = four["licence"]
                champs.append("licence=?")
                valeurs.append(lu["licence"])
            if d.get("maj_codes") and lu.get("certificat") and lu["certificat"] != (four["certificat"] or None):
                codes_avant["certificat"] = four["certificat"]
                champs.append("certificat=?")
                valeurs.append(lu["certificat"])
            if champs:
                champs.append("updated_at=?")
                valeurs.append(_now())
                valeurs.append(four["id"])
                conn.execute("UPDATE fournisseurs_fsc SET %s WHERE id=?" % ", ".join(champs), valeurs)
            conn.commit()

            try:
                reprises = registre.reprendre_portee(conn, four["id"], user.get("nom"))
            except Exception:
                logger.warning("Reprise de portée du registre FSC échouée", exc_info=True)
                reprises = 0

            log_action(
                user=user, action="VALIDATE", module="qualite", request=request,
                objet="Contrôle FSC importé · %s · %s" % (four["nom"], lu.get("certificat") or ""),
                detail={
                    "controle_id": ctrl_id, "certificat_id": cert_id, "lot": jeton,
                    "fichier": ligne["fichier"], "date_controle": jour,
                    "signature_fsc": lu.get("signe_horodatage"),
                    "statut_base": lu.get("statut_base"),
                    "claims": claims, "portees": portees,
                    "fiche_expiration": {"avant": ancienne, "apres": expiration} if fiche_maj else None,
                    "fiche_codes": codes_avant or None,
                    "registre_lignes_reprises": reprises,
                },
            )
            ecrits += 1
            resultats.append({
                "disque": disque, "ok": True, "controle_id": ctrl_id, "certificat_id": cert_id,
                "fournisseur_id": four["id"], "fournisseur_nom": four["nom"],
                "fiche_maj": bool(fiche_maj), "codes_corriges": codes_avant or None,
                "registre_lignes_reprises": reprises,
            })

    if ecrits:
        lot["applique_le"] = _now()
        lot["resultats"] = resultats
        try:
            with open(os.path.join(chemin, "_lot.json"), "w", encoding="utf-8") as fh:
                json.dump(lot, fh, ensure_ascii=False)
        except OSError:
            logger.warning("Marquage du lot FSC %s impossible", jeton, exc_info=True)
    if ecrits and all(r.get("ok") for r in resultats):
        shutil.rmtree(chemin, ignore_errors=True)
    return {"importes": ecrits, "resultats": resultats}
