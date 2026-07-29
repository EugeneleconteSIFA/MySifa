"""
Pont API — Access → MySifa
Authentification : header X-Api-Key
Scope requis : of:read (lecture) / of:write (écriture)

Endpoints :
  GET  /api/bridge/health      → ping sans auth
  GET  /api/bridge/of          → liste les OF importés (of:read)
  POST /api/bridge/of          → pousse un OF depuis Access (of:write)
  GET  /api/bridge/fiches      → liste les fiches techniques importées (of:read)
"""
import hashlib
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.database import get_db
from app.services.fiche_pdf import generate_fiche_pdf

router = APIRouter(prefix="/api/bridge", tags=["bridge"])

# Numéro racine d'un OF SIFA. Sert UNIQUEMENT de pré-filtre SQL pour ramener
# les quelques lignes candidates ; la comparaison finale est faite sur le
# numéro complet (cf. _of_numero_key) car « 9932056 » et « Reliquat 9932056 »
# sont deux OF bien distincts qui doivent pouvoir coexister.
_OF_RACINE_RE = re.compile(r"\b(99\d{5})\b")


def _of_racine(num: Optional[str]) -> Optional[str]:
    m = _OF_RACINE_RE.search(str(num or ""))
    return m.group(1) if m else None


def _of_numero_key(num: Optional[str]) -> str:
    """Clé de comparaison d'un numéro d'OF : casse et espaces neutralisés.

    « Reliquat 9932056 », « reliquat  9932056 » et « RELIQUAT 9932056 » sont le
    même OF ; « 9932056 » en est un autre.
    """
    return re.sub(r"\s+", " ", str(num or "").strip()).lower()


# ── Auth ──────────────────────────────────────────────────────────────

def _require_scope(raw_key: Optional[str], required_scope: str) -> None:
    if not raw_key:
        raise HTTPException(status_code=401, detail="Clé API manquante (header X-Api-Key).")
    h = hashlib.sha256(raw_key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, scopes, is_active FROM api_keys WHERE key_hash=? LIMIT 1", (h,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Clé API invalide.")
        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="Clé API révoquée.")
        scopes = [s.strip() for s in (row["scopes"] or "").split(",")]
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required_scope}' non autorisé pour cette clé."
            )
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row["id"])
            )
            conn.commit()
        except Exception:
            pass


# ── Modèle ────────────────────────────────────────────────────────────

class OFPushIn(BaseModel):
    # Champs Access → of_imports
    numero_of: str                          # t_of.numero_of  → of_imports.of_numero
    date_creation: Optional[str] = None     # t_of.date_creation
    format: Optional[str] = None            # t_of.format
    qte_etiquettes: Optional[float] = None  # t_of.theorique_quantite
    qte_bobines: Optional[float] = None     # t_of.theorique_quantite_bobine
    # Champs optionnels supplémentaires (extensible)
    reference: Optional[str] = None
    machine: Optional[str] = None
    laize: Optional[float] = None
    matiere: Optional[str] = None
    delai_client: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/health")
def bridge_health():
    return {"status": "ok", "service": "mysifa-bridge"}


@router.get("/of")
def list_of_imports(x_api_key: Optional[str] = Header(default=None)):
    """Liste les OFs importés, du plus récent au plus ancien."""
    _require_scope(x_api_key, "of:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, of_numero, date_creation, format,
                      qte_etiquettes, qte_bobines, statut, date_import
               FROM of_imports
               ORDER BY date_import DESC
               LIMIT 500"""
        ).fetchall()
    return {"of": [dict(r) for r in rows]}


@router.get("/fiches")
def list_fiches_bridge(x_api_key: Optional[str] = Header(default=None)):
    """Liste les références de fiches techniques déjà importées."""
    _require_scope(x_api_key, "of:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, reference, designation, client, source, date_import
               FROM fiches_techniques
               ORDER BY date_import DESC
               LIMIT 500"""
        ).fetchall()
    return {"fiches": [dict(r) for r in rows]}


@router.post("/of")
def push_of(
    body: OFPushIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Pousse un OF depuis Access vers of_imports.

    Idempotent : si un OF portant exactement le même numéro (casse et espaces
    normalisés) existe déjà dans of_imports, retourne
    {"inserted": false, "reason": "already_exists"} sans rien modifier.

    « 9932056 » et « Reliquat 9932056 » sont deux OF distincts : chacun peut
    être créé indépendamment de l'autre.
    """
    _require_scope(x_api_key, "of:write")

    numero = body.numero_of.strip()
    if not numero:
        raise HTTPException(status_code=400, detail="numero_of est obligatoire.")

    racine = _of_racine(numero)
    key = _of_numero_key(numero)

    with get_db() as conn:
        # Dédoublonnage — ne jamais écraser ni doubler un OF existant.
        #
        # Le match porte sur le numéro COMPLET, à la casse et aux espaces près.
        # On ne compare surtout pas sur le numéro racine : « 9932056 » doit
        # pouvoir être créé même si « Reliquat 9932056 » existe déjà (et
        # inversement) — ce sont deux OF différents, avec leurs quantités et
        # leur aperçu propres.
        #
        # L'ancien TRIM(of_numero)=? était sensible à la casse et aux espaces
        # multiples, d'où des doublons qui passaient au travers. Le pré-filtre
        # SQL sur la racine limite la lecture à quelques lignes ; le tri final
        # est fait en Python (SQLite ne sait pas normaliser les espaces).
        if racine:
            rows = conn.execute(
                """SELECT id, of_numero, pdf_filename, date_import FROM of_imports
                   WHERE of_numero LIKE ?
                      OR LOWER(TRIM(of_numero)) = LOWER(TRIM(?))""",
                ("%" + racine + "%", numero),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, of_numero, pdf_filename, date_import FROM of_imports
                   WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))""",
                (numero,),
            ).fetchall()

        matches = [r for r in rows if _of_numero_key(r["of_numero"]) == key]
        # Tri stable : import le plus récent d'abord, puis les OF disposant
        # d'un vrai PDF (aperçu réel) remontent devant ceux générés sur template.
        matches.sort(key=lambda r: str(r["date_import"] or ""), reverse=True)
        matches.sort(key=lambda r: 0 if (r["pdf_filename"] or "").strip() else 1)
        existing = matches[0] if matches else None

        if existing:
            return {
                "inserted": False,
                "reason": "already_exists",
                "id": existing["id"],
                "of_numero": numero,
                "matched_of_numero": existing["of_numero"],
                "has_pdf": bool(existing["pdf_filename"]),
            }

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        cur = conn.execute(
            """INSERT INTO of_imports
               (of_numero, date_creation, format, qte_etiquettes, qte_bobines,
                reference, machine, laize, matiere, delai_client,
                date_import, imported_by, statut)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                numero,
                body.date_creation,
                body.format,
                body.qte_etiquettes,
                body.qte_bobines,
                body.reference,
                body.machine,
                body.laize,
                body.matiere,
                body.delai_client,
                now,
                "access_bridge",
                "en_attente",
            )
        )
        conn.commit()
        new_id = cur.lastrowid

    # Auto-link : relier les dossiers planning dont le numero_of correspond.
    #
    # Garde-fou : on ne repointe JAMAIS un dossier déjà relié à un OF disposant
    # d'un PDF. L'OF poussé par Access n'a pas de pdf_filename — son aperçu est
    # un rendu sur template vierge — et il écrasait sinon l'aperçu réel importé
    # à la main par la production.
    with get_db() as conn2:
        conn2.execute(
            """UPDATE planning_entries
               SET of_import_id = ?
               WHERE LOWER(TRIM(numero_of)) = LOWER(TRIM(?))
                 AND (of_import_id IS NULL OR of_import_id != ?)
                 AND NOT EXISTS (
                       SELECT 1 FROM of_imports o
                       WHERE o.id = planning_entries.of_import_id
                         AND TRIM(COALESCE(o.pdf_filename,'')) != ''
                 )
                 AND NOT EXISTS (
                       SELECT 1 FROM planning_of_links pl
                       JOIN of_imports o2 ON o2.id = pl.of_import_id
                       WHERE pl.planning_entry_id = planning_entries.id
                         AND TRIM(COALESCE(o2.pdf_filename,'')) != ''
                 )""",
            (new_id, numero, new_id),
        )
        conn2.commit()

    return {
        "inserted": True,
        "id": new_id,
        "of_numero": numero,
    }


class FicheTechniqueIn(BaseModel):
    # Identification
    reference:              str
    designation:            Optional[str]   = None
    client:                 Optional[str]   = None
    date_modif:             Optional[str]   = None
    # Format / étiquette
    format:                 Optional[str]   = None
    eti_laize:              Optional[float] = None
    eti_longueur:           Optional[float] = None
    eti_rayons:             Optional[float] = None
    eti_perforations:       Optional[str]   = None
    # Module
    mod_laize:              Optional[float] = None
    mod_longueur:           Optional[float] = None
    mod_nb_front:           Optional[int]   = None
    # Échenillage
    lateral_ext:            Optional[float] = None
    horizontal:             Optional[float] = None
    lateral_int:            Optional[float] = None
    # Outil 1
    outil1_forme:           Optional[str]   = None
    outil1_numero_sifa:     Optional[str]   = None
    outil1_laize:           Optional[float] = None
    machine:                Optional[str]   = None
    outil1_epaisseur:       Optional[float] = None
    outil1_nb_dents:        Optional[int]   = None
    outil1_nb_front:        Optional[int]   = None
    outil1_nb_avance:       Optional[int]   = None
    # Outil 2
    outil2_forme:           Optional[str]   = None
    outil2_numero_sifa:     Optional[str]   = None
    outil2_epaisseur:       Optional[float] = None
    outil2_nb_dents:        Optional[int]   = None
    outil2_nb_front:        Optional[int]   = None
    outil2_nb_avance:       Optional[int]   = None
    # Outil 3
    outil3_forme:           Optional[str]   = None
    outil3_numero_sifa:     Optional[str]   = None
    outil3_epaisseur:       Optional[float] = None
    outil3_nb_dents:        Optional[int]   = None
    outil3_nb_front:        Optional[int]   = None
    outil3_nb_avance:       Optional[int]   = None
    # Matière
    support:                Optional[str]   = None
    matiere:                Optional[str]   = None   # alias support (compatibilité)
    glassine:               Optional[str]   = None
    laize_optimale:         Optional[float] = None
    laize_optionnelle:      Optional[float] = None
    epaisseur:              Optional[float] = None
    adhesif:                Optional[str]   = None
    qte_au_mille:           Optional[float] = None
    # Impression
    nb_couleurs:            Optional[int]   = None
    recto:                  Optional[int]   = None
    verso:                  Optional[int]   = None
    tete1_pantone:          Optional[str]   = None
    tete1_couleur:          Optional[str]   = None
    tete1_anilox:           Optional[str]   = None
    tete1_composition:      Optional[str]   = None
    tete2_pantone:          Optional[str]   = None
    tete2_couleur:          Optional[str]   = None
    tete2_anilox:           Optional[str]   = None
    tete2_composition:      Optional[str]   = None
    tete3_pantone:          Optional[str]   = None
    tete3_couleur:          Optional[str]   = None
    tete3_anilox:           Optional[str]   = None
    tete3_composition:      Optional[str]   = None
    remarque:               Optional[str]   = None
    # Conditionnement
    mandrin_dia:            Optional[str]   = None
    mandrin_longueur:       Optional[float] = None
    enroulement:            Optional[str]   = None
    nb_etiq_bobin:          Optional[int]   = None
    dia_ext:                Optional[float] = None
    poids:                  Optional[float] = None
    conditionnement:        Optional[str]   = None
    cales_sachets:          Optional[str]   = None
    cartons:                Optional[str]   = None
    nb_au_sol:              Optional[int]   = None
    nb_etage:               Optional[int]   = None
    nb_bobines_carton:      Optional[int]   = None
    # Palettisation
    palette_type:               Optional[str]   = None
    palette_nb_cartons_sol:     Optional[int]   = None
    palette_nb_cartons_hauteur: Optional[int]   = None
    palette_hauteur_max:        Optional[float] = None
    particularite:              Optional[str]   = None
    notes:                      Optional[str]   = None


# Colonnes DB gérées manuellement (non mappées depuis le modèle)
_FT_META_COLS = {"source", "date_import", "imported_by"}


@router.post("/fiche-technique")
def push_fiche_technique(
    body: FicheTechniqueIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Crée ou met à jour une fiche technique (upsert par référence).
    Si la référence existe déjà : mise à jour des champs fournis.
    Scope requis : of:write
    """
    _require_scope(x_api_key, "of:write")
    ref = body.reference.strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Le champ 'reference' est obligatoire.")

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Tous les champs non-null sauf référence et méta
    data = {
        k: v for k, v in body.model_dump().items()
        if k != "reference" and v is not None and k not in _FT_META_COLS
    }

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
            (ref,)
        ).fetchone()
        if existing:
            if data:
                conn.execute(
                    f"UPDATE fiches_techniques SET {', '.join(f'{k}=?' for k in data)} WHERE id=?",
                    list(data.values()) + [existing["id"]],
                )
                conn.commit()
            return {"action": "updated", "id": existing["id"], "reference": ref}
        else:
            cols = ["reference", "source", "date_import", "imported_by"] + list(data.keys())
            vals = [ref, "access_bridge", now, "access_bridge"] + list(data.values())
            cur = conn.execute(
                f"INSERT INTO fiches_techniques ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                vals,
            )
            conn.commit()
            return {"action": "created", "id": cur.lastrowid, "reference": ref}


@router.get("/fiche-technique/{reference}/pdf")
def preview_fiche_pdf(
    reference: str,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Génère et retourne le PDF de prévisualisation d'une fiche technique.
    Scope requis : of:read
    """
    _require_scope(x_api_key, "of:read")

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
            (reference,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Fiche '{reference}' introuvable.")

    pdf_bytes = generate_fiche_pdf(dict(row))
    safe_ref = reference.replace("/", "-").replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="fiche_{safe_ref}.pdf"'},
    )
