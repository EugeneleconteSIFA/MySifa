"""MySifa — Import OF PDF pour MyProd."""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from contextlib import nullcontext
from datetime import datetime
from io import BytesIO
from typing import Any, Optional
from zoneinfo import ZoneInfo

import pdfplumber
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from config import UPLOAD_DIR
from database import get_db
from services.auth_service import get_current_user, require_superadmin
from app.services.documents_verite import (
    appliquer_maj, constater_remplacement, marquer_champs_manuels,
)

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")
OF_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "of")
OF_ALLOWED_ROLES = frozenset({"superadmin", "direction", "administration", "administration_ventes", "administration_technique"})

OF_REAL_FIELDS = frozenset({
    "laize", "qte_adhesif_g", "qte_adhesif_kg", "qte_au_mille",
    "qte_bobines", "mandrin_longueur", "outil_1_hauteur", "outil_2_hauteur",
})
OF_INT_FIELDS = frozenset({
    "nb_levees", "qte_etiquettes", "metrage", "nb_cartons",
    "nb_mandrins", "nb_tubes", "nb_palettes",
    "matiere_ref_id", "glassine_ref_id", "adhesif_ref_id",
    "carton_ref_id", "mandrin_ref_id", "palette_ref_id",
})

def _coerce_of_value(field: str, value):
    """Applique a une valeur saisie la meme conversion que le parsing PDF.

    Sans ca une laize tapee « 332,5 » arrivait telle quelle, en texte, dans une
    colonne REAL. Defini apres OF_REAL_FIELDS / OF_INT_FIELDS, utilise par le
    PATCH.
    """
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if field in OF_REAL_FIELDS:
        return _clean_num(value)
    if field in OF_INT_FIELDS:
        return _clean_int(value)
    return value.strip() if isinstance(value, str) else value


OF_DATA_FIELDS = [
    "of_numero", "date_creation", "delai_client", "reference", "machine",
    "laize", "format", "matiere", "ref_matiere", "glassine", "ref_adhesif",
    "qte_adhesif_g", "qte_adhesif_kg", "adhesif_label", "qte_au_mille", "nb_levees",
    "qte_etiquettes", "qte_bobines", "metrage", "conditionnement", "tolerance",
    "cartons_type", "nb_cartons", "mandrins_dia", "mandrin_longueur", "nb_mandrins",
    "nb_tubes", "bobinettes_completes", "outil_1_forme", "outil_1_numero",
    "outil_1_angle", "outil_1_mag", "outil_1_cp", "outil_1_hauteur", "outil_1_fournisseur",
    "outil_2_forme", "outil_2_numero", "outil_2_angle", "outil_2_cp",
    "outil_alt_forme", "outil_alt_numero", "outil_alt_angle", "outil_alt_fournisseur",
    # Le reste du papier atelier — saisissable dans MySifa, absent du parseur PDF.
    "particularites", "cales_sachets", "observations", "ref_matiere_fournisseur",
    "outil_2_mag", "outil_2_hauteur", "outil_2_fournisseur",
    "plieuse_pignon", "nb_pouces", "texte_bobinettes",
    # Type de palette : UN champ, pas deux compteurs Europe/perdues.
    "palette_type", "nb_palettes",
    # Références MyStock. C'est l'id qui fait foi ; la colonne texte en
    # découle (voir _appliquer_references).
    "matiere_ref_id", "glassine_ref_id", "adhesif_ref_id",
    "carton_ref_id", "mandrin_ref_id", "palette_ref_id",
]

# (colonne d'id, colonne texte imprimée sur le document)
REFERENCES_OF = [
    ("matiere_ref_id",  "matiere"),
    ("glassine_ref_id", "glassine"),
    ("adhesif_ref_id",  "adhesif_label"),
    ("carton_ref_id",   "cartons_type"),
    ("mandrin_ref_id",  "mandrins_dia"),
    ("palette_ref_id",  "palette_type"),
]

REFERENCES_FT = [
    ("support_ref_id",  "support"),
    ("glassine_ref_id", "glassine"),
    ("adhesif_ref_id",  "adhesif"),
    ("carton_ref_id",   "cartons"),
    ("mandrin_ref_id",  "mandrin_dia"),
    ("palette_ref_id",  "palette_type"),
]

_PATTERNS = {
    # "OF n° 123456" ou "OF : 123456 + Stock" (un mot après +)
    "of_numero": r"OF\s*(?:n[°o]|n°|:)\s*(\d+(?:\s*\+\s*[\w]+)?)",
    "date_creation": r"Date cr[eé]a\.\s*([\d/]+)",
    "delai_client": r"D[eé]lai client\s*([\d/]+)",
    "reference": r"R[eé]f\s*:\s*([\w/]+)",
    "machine": r"Machine\s*:\s*(.+?)(?:\n|$)",
    # ([\d,\.]+) et non (\d+) : une laize "332,5" etait tronquee a 332,
    # et l'erreur se propageait dans le calcul adhesif de MyStock.
    "laize": r"Laize\s+([\d,\.]+)",
    "format": r"Format\s*:\s*([\d x]+mm)",
    "matiere": r"Mati[eè]re\s+(.+?)(?:\n|$)",
    "ref_adhesif": r"R[eé]f,?\s*Adh[eé]sif\s+(\d+)",
    "qte_adhesif_g": r"Qt[eé]\s*:\s*([\d,\.]+)\s*g",
    "qte_adhesif_kg": r"Qt[eé] totale\s+([\d,\.]+)\s*kg",
    "qte_au_mille": r"Quantit[eé] au mille\s+([\d,\.]+)",
    "nb_levees": r"Nb de lev[eé]es\s+(\d+)",
    "qte_etiquettes": r"Quantit[eé] [eé]tiq\.\s+([\d\s]+)",
    "qte_bobines": r"Quantit[eé] bobines\s+([\d,\.]+)",
    "metrage": r"M[eé]trage\s+([\d\s]+)",
    "conditionnement": r"Conditionnement\s+(.+?)(?:\n|$)",
    "tolerance": r"Tol[eé]rance\s+(.+?)(?:\n|$)",
    "cartons_type": r"Cartons\s+(Carton.+?)(?:\n|$)",
    "mandrins_dia": r"Mandrins dia\.\s+(.+?)(?:Long\.|$)",
    "mandrin_longueur": r"Long\.\s+([\d,\.]+)",
    "nb_cartons": r"Cartons\s+(\d+)(?!\s*x)",
    "nb_mandrins": r"Mandrins\s+(\d+)",
    "nb_tubes": r"Tubes\s+(\d+)",
    "bobinettes_completes": r"Bobinettes compl[eè]tes\s+(\w+)",
}


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _require_of_access(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in OF_ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")
    return user


def _clean_num(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip().replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_int(raw: Optional[str]) -> Optional[int]:
    f = _clean_num(raw)
    if f is None:
        return None
    return int(round(f))


def _normalize_field(key: str, value: Optional[str]) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if key in OF_REAL_FIELDS:
        return _clean_num(text)
    if key in OF_INT_FIELDS:
        return _clean_int(text)
    return text


def _extract_pdf_text(content: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def parse_of_pdf(content: bytes) -> dict[str, Any]:
    text = _extract_pdf_text(content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF illisible ou vide.")

    result: dict[str, Any] = {k: None for k in OF_DATA_FIELDS}
    for key, pattern in _PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            result[key] = _normalize_field(key, m.group(1))
    return result


def _coerce_payload(data: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in OF_DATA_FIELDS:
        raw = data.get(key)
        if raw is None or raw == "":
            out[key] = None
            continue
        if key in OF_REAL_FIELDS:
            out[key] = _clean_num(str(raw))
        elif key in OF_INT_FIELDS:
            out[key] = _clean_int(str(raw))
        else:
            out[key] = str(raw).strip()
    return out


def _appliquer_references(conn, valeurs: dict, liens) -> list:
    """Réécrit la colonne texte à partir de la référence MyStock choisie.

    C'est ici que se joue « la référence fait foi ». Laisser le client poster
    les deux, c'est accepter qu'ils divergent : un jour la désignation change
    dans MyStock, le document garde l'ancienne, et le rapprochement qu'on
    voulait supprimer revient par la fenêtre. Le serveur écrit donc lui-même
    le texte, depuis l'id.

    Un id à `None` explicite détache la référence sans effacer le texte : un
    OF venu d'Access porte un libellé qu'aucune référence ne recouvre encore,
    et le perdre serait perdre la seule chose qu'on sache de sa matière.
    """
    ecrits = []
    for col_id, col_txt in liens:
        if col_id not in valeurs:
            continue
        ref_id = valeurs.get(col_id)
        if ref_id in (None, "", 0):
            valeurs[col_id] = None
            continue
        row = conn.execute(
            "SELECT designation FROM matieres_premieres WHERE id=?", (int(ref_id),)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=400,
                detail="Référence matière %s introuvable." % ref_id,
            )
        valeurs[col_id] = int(ref_id)
        valeurs[col_txt] = row["designation"]
        ecrits.append(col_txt)
    return ecrits


def _row_dict(row) -> dict:
    return dict(row) if row else {}


@router.post("/api/of/parse")
async def parse_of(request: Request, file: UploadFile = File(...)):
    _require_of_access(request)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    return parse_of_pdf(content)


# ─────────────────────────────────────────────────────────────────────────────
# Dédoublonnage & rattachement des OF au planning
#
# Deux sources de vérité coexistent pour « quel OF est affiché sur un dossier » :
#   - planning_entries.of_import_id → lu par le slot du planning (quantité,
#     pastille OF, traçabilité) ;
#   - planning_of_links (ORDER BY position) → lu par le panneau OF du dossier,
#     dont l'iframe d'aperçu.
# L'import PDF ne mettait à jour que la première : un ré-import affichait donc
# la bonne quantité dans le slot tout en laissant l'aperçu figé sur le PDF
# d'origine. Les helpers ci-dessous alignent systématiquement les deux.
# ─────────────────────────────────────────────────────────────────────────────


def _of_numero_racine(num: Optional[str]) -> Optional[str]:
    """Numéro racine 99XXXXX d'un of_numero ("Reliquat 9932056" → "9932056").

    Sert de pré-filtre SQL uniquement : deux OF partageant la même racine ne
    sont PAS le même OF (« 9932056 » vs « Reliquat 9932056 »).
    """
    m = _OF_RACINE_RE.search(str(num or ""))
    return m.group(1) if m else None


def _of_numero_key(num: Optional[str]) -> str:
    """Clé de comparaison d'un numéro d'OF : casse et espaces neutralisés."""
    return re.sub(r"\s+", " ", str(num or "").strip()).lower()


def _archive_of_pdf(pdf_filename: Optional[str]) -> None:
    """Déplace le PDF d'un OF remplacé dans of/_archive/.

    On ne supprime jamais : en cas de ré-import erroné, l'ancien aperçu reste
    récupérable à la main sur le serveur.
    """
    if not pdf_filename:
        return
    src = os.path.join(OF_UPLOAD_DIR, pdf_filename)
    if not os.path.isfile(src):
        return
    try:
        archive_dir = os.path.join(OF_UPLOAD_DIR, "_archive")
        os.makedirs(archive_dir, exist_ok=True)
        stamp = datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S")
        os.replace(src, os.path.join(archive_dir, f"{stamp}__{pdf_filename}"))
    except OSError:
        pass


def _promote_of_link(conn, entry_id: int, of_id: int, created_by: str) -> None:
    """Fait de `of_id` l'OF actif du dossier planning `entry_id`.

    Les autres liens sont décalés d'un cran (ils restent accessibles dans les
    sous-onglets du panneau OF), celui-ci passe en position 0. Le trigger
    trg_planning_of_links_after_insert resynchronise of_import_id sur un
    INSERT ; sur un simple repositionnement il ne se déclenche pas, on aligne
    donc la colonne explicitement.
    """
    conn.execute(
        "UPDATE planning_of_links SET position = position + 1 "
        "WHERE planning_entry_id = ? AND of_import_id != ?",
        (entry_id, of_id),
    )
    cur = conn.execute(
        "UPDATE planning_of_links SET position = 0 "
        "WHERE planning_entry_id = ? AND of_import_id = ?",
        (entry_id, of_id),
    )
    if cur.rowcount == 0:
        conn.execute(
            "INSERT INTO planning_of_links "
            "(planning_entry_id, of_import_id, position, created_by, created_at) "
            "VALUES (?, ?, 0, ?, ?)",
            (entry_id, of_id, created_by, _now_paris_iso()),
        )
    else:
        conn.execute(
            "UPDATE planning_entries SET of_import_id = ? WHERE id = ?",
            (of_id, entry_id),
        )


def _autolink_of_to_planning(of_id: int, of_numero: Optional[str],
                             created_by: str = "of_import") -> int:
    """Relie l'OF `of_id` aux dossiers planning dont le numero_of correspond.

    Retourne le nombre de dossiers rattachés. Idempotent.
    """
    num = (of_numero or "").strip()
    if not num:
        return 0
    linked = 0
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id FROM planning_entries "
                "WHERE LOWER(TRIM(numero_of)) = LOWER(TRIM(?))",
                (num,),
            ).fetchall()
            targets = {int(r["id"]) for r in rows}

            # Élargissement : un dossier nommé "9932163 Reliquat 2" ou
            # "9932376-377" ne matche pas l'égalité stricte. On rattrape par
            # token numérique, en se limitant aux dossiers encore non liés et
            # non arbitrés manuellement — on ne vole jamais un lien existant.
            try:
                tokens = _of_tokens(num)
                if tokens:
                    like_sql = " OR ".join(["numero_of LIKE ?"] * len(tokens))
                    extra = conn.execute(
                        "SELECT id, numero_of FROM planning_entries "
                        "WHERE (" + like_sql + ") "
                        "AND of_import_id IS NULL "
                        "AND COALESCE(of_link_user_managed, 0) = 0",
                        tuple("%" + t + "%" for t in tokens),
                    ).fetchall()
                    for r in extra:
                        if int(r["id"]) in targets:
                            continue
                        if any(_of_token_present(t, r["numero_of"]) for t in tokens):
                            targets.add(int(r["id"]))
            except Exception:
                pass  # colonne absente / base ancienne : on garde l'exact

            for entry_id in sorted(targets):
                _promote_of_link(conn, entry_id, of_id, created_by)
                linked += 1
            conn.commit()
    except Exception:
        # Base sans planning_of_links (migration v108 non appliquée) :
        # on retombe sur le comportement historique.
        try:
            with get_db() as conn_fb:
                conn_fb.execute(
                    """UPDATE planning_entries SET of_import_id = ?
                       WHERE LOWER(TRIM(numero_of)) = LOWER(TRIM(?))
                         AND (of_import_id IS NULL OR of_import_id != ?)""",
                    (of_id, num, of_id),
                )
                conn_fb.commit()
        except Exception:
            pass
    return linked


@router.post("/api/of/validate")
async def validate_of(
    request: Request,
    file: UploadFile = File(...),
    data: str = Form(...),
):
    user = _require_of_access(request)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis.")
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Données JSON invalides.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Données JSON invalides.")

    fields = _coerce_payload(payload)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    os.makedirs(OF_UPLOAD_DIR, exist_ok=True)
    of_num = (fields.get("of_numero") or "inconnu").strip()
    safe_of = re.sub(r"[^\w\-]+", "_", str(of_num))
    ts = datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"{safe_of}_{ts}.pdf"
    dest_path = os.path.join(OF_UPLOAD_DIR, pdf_filename)
    with open(dest_path, "wb") as f:
        f.write(content)

    now = _now_paris_iso()
    imported_by = user.get("nom") or user.get("email") or str(user.get("id", ""))
    of_num_clean = (fields.get("of_numero") or "").strip()
    tail_cols = ["pdf_filename", "date_import", "imported_by", "statut"]
    tail_vals = [pdf_filename, now, imported_by, "valide"]

    # Ré-import d'un numéro d'OF déjà présent → on remplace la ligne existante
    # au lieu d'empiler un doublon. Avant, chaque ré-import créait une ligne de
    # plus et l'aperçu continuait de pointer sur la toute première version.
    # Le match est volontairement strict (of_numero exact, à la casse près) :
    # « 9932056 » et « Reliquat 9932056 » restent deux OF distincts.
    replaced_id = None
    replaced_pdf = None
    with get_db() as conn:
        if of_num_clean:
            # Comparaison sur le numéro COMPLET normalisé (casse + espaces).
            # « Reliquat 9932056 » ne doit jamais être confondu avec
            # « 9932056 » : ce sont deux OF distincts, chacun avec sa quantité
            # et son aperçu. Le pré-filtre SQL sur la racine ne sert qu'à
            # limiter la lecture à quelques lignes.
            key = _of_numero_key(of_num_clean)
            racine = _of_numero_racine(of_num_clean)
            if racine:
                cand = conn.execute(
                    """SELECT id, of_numero, pdf_filename, date_import
                       FROM of_imports
                       WHERE of_numero LIKE ?
                          OR LOWER(TRIM(of_numero)) = LOWER(TRIM(?))""",
                    ("%" + racine + "%", of_num_clean),
                ).fetchall()
            else:
                cand = conn.execute(
                    """SELECT id, of_numero, pdf_filename, date_import
                       FROM of_imports
                       WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))""",
                    (of_num_clean,),
                ).fetchall()
            matches = [r for r in cand if _of_numero_key(r["of_numero"]) == key]
            # Tri stable : on remplace en priorité la ligne qui porte déjà un
            # PDF, sinon la plus ancienne (celle poussée par access_bridge).
            matches.sort(key=lambda r: int(r["id"]))
            matches.sort(key=lambda r: 0 if (r["pdf_filename"] or "").strip() else 1)
            if matches:
                replaced_id = int(matches[0]["id"])
                replaced_pdf = matches[0]["pdf_filename"]

        if replaced_id is not None:
            # Photo de la ligne AVANT réécriture. Le remplacement est un geste
            # délibéré et le papier fait foi — on ne l'arbitre pas. Mais si un
            # chiffre de calcul change sous une validation déjà acquise, cette
            # validation ne vaut plus rien : `constater_remplacement` la retire
            # et journalise ce qui a bougé.
            avant = dict(conn.execute(
                "SELECT * FROM of_imports WHERE id = ?", (replaced_id,)
            ).fetchone())
            set_cols = list(OF_DATA_FIELDS) + tail_cols
            set_sql = ", ".join(f"{c} = ?" for c in set_cols)
            vals = [fields.get(c) for c in OF_DATA_FIELDS] + tail_vals + [replaced_id]
            conn.execute(f"UPDATE of_imports SET {set_sql} WHERE id = ?", vals)
            constater_remplacement(
                conn, "of_imports", replaced_id, avant,
                origine="import_pdf", auteur=imported_by,
            )
            conn.commit()
            new_id = replaced_id
        else:
            cols = list(OF_DATA_FIELDS) + tail_cols
            placeholders = ", ".join("?" * len(cols))
            values = [fields.get(c) for c in OF_DATA_FIELDS] + tail_vals
            cur = conn.execute(
                f"INSERT INTO of_imports ({', '.join(cols)}) VALUES ({placeholders})",
                values,
            )
            new_id = cur.lastrowid
            # Ce que le PDF a rempli vient d'un humain : Access ne l'écrase pas.
            marquer_champs_manuels(
                conn, "of_imports", new_id,
                [c for c in OF_DATA_FIELDS
                 if fields.get(c) is not None
                 and str(fields.get(c)).strip() != ""],
            )
            conn.commit()

    if replaced_pdf and replaced_pdf != pdf_filename:
        _archive_of_pdf(replaced_pdf)

    # Auto-link : relier les dossiers planning dont le numero_of correspond,
    # en plaçant cet OF en position 0 (slot ET aperçu pointent sur la même ligne).
    linked = _autolink_of_to_planning(new_id, of_num_clean, created_by="of_import")
    _invalidate_pending_count_cache()

    return {
        "id": new_id,
        "pdf_filename": pdf_filename,
        "replaced": replaced_id is not None,
        "linked_entries": linked,
    }


@router.get("/api/of/list")
def list_of_imports(request: Request):
    _require_of_access(request)
    q      = (request.query_params.get("q")      or "").strip()
    offset = int(request.query_params.get("offset") or 0)
    limit  = int(request.query_params.get("limit")  or 50)
    limit  = min(limit, 200)   # plafond de sécurité

    like = f"%{q}%"
    search_filter = ""
    params_count: list = []
    params_rows:  list = []

    if q:
        search_filter = """AND (
            LOWER(COALESCE(o.of_numero,''))    LIKE LOWER(?)
         OR LOWER(COALESCE(o.reference,''))   LIKE LOWER(?)
         OR LOWER(COALESCE(o.machine,''))     LIKE LOWER(?)
         OR LOWER(COALESCE(o.delai_client,'')) LIKE LOWER(?)
        )"""
        params_count = [like, like, like, like]
        params_rows  = [like, like, like, like, limit, offset]
    else:
        params_rows = [limit, offset]

    with get_db() as conn:
        total = conn.execute(
            f"""SELECT COUNT(DISTINCT o.id)
                FROM of_imports o
                LEFT JOIN planning_entries pe ON pe.of_import_id = o.id
                WHERE 1=1 {search_filter}""",
            params_count,
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT
                    o.id, o.of_numero, o.reference, o.machine, o.delai_client,
                    o.format, o.date_creation, o.qte_etiquettes, o.qte_bobines,
                    o.metrage, o.matiere, o.conditionnement, o.outil_1_numero,
                    o.nb_mandrins, o.nb_cartons, o.nb_tubes,
                    o.date_import, o.statut, o.pdf_filename, o.imported_by,
                    CASE WHEN pe.of_import_id IS NOT NULL THEN 1 ELSE 0 END AS lie
                FROM of_imports o
                LEFT JOIN planning_entries pe ON pe.of_import_id = o.id
                WHERE 1=1 {search_filter}
                GROUP BY o.id
                ORDER BY COALESCE(o.date_creation, o.date_import) DESC
                LIMIT ? OFFSET ?""",
            params_rows,
        ).fetchall()

    return {
        "total":  total,
        "offset": offset,
        "limit":  limit,
        "rows":   [{**_row_dict(r), "lie": bool(r["lie"])} for r in rows],
    }


@router.patch("/api/of/{of_id}")
async def update_of_import(of_id: int, request: Request):
    """Modifier les champs éditables d'un OF importé."""
    user = _require_of_access(request)
    body = await request.json()

    # Tous les champs metier de l'OF sont corrigeables. L'ancienne liste de 15
    # champs filtrait les 27 autres EN SILENCE : la modale postait 42 cles,
    # l'interface affichait « OF mis a jour » et la valeur ne bougeait pas.
    # `laize` en faisait partie, alors qu'elle alimente le calcul adhesif MyStock.
    EDITABLE = frozenset(OF_DATA_FIELDS)
    # Cles techniques que la modale peut renvoyer sans qu'il faille les ecrire.
    IGNORABLES = frozenset({"id", "statut", "pdf_filename", "date_import", "imported_by"})

    updates = {k: _coerce_of_value(k, v) for k, v in body.items() if k in EDITABLE}
    ignores = sorted(k for k in body if k not in EDITABLE and k not in IGNORABLES)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Aucun champ modifiable fourni."
                   + (" Champs inconnus : " + ", ".join(ignores) if ignores else ""),
        )

    qui = (user.get("nom") or user.get("email") or "").strip() or None
    with get_db() as conn:
        row = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        _appliquer_references(conn, updates, REFERENCES_OF)
        # Une correction humaine a le dernier mot (`proteger_manuels=False`) et
        # devient protegee a son tour (`marquer_manuels=True`) : le prochain
        # sync Access ne la reecrira pas. Elle perime aussi la validation si
        # elle touche un chiffre de calcul — c'est le meme risque qu'une
        # modification venue d'Access, et corriger n'est pas relire.
        maj = appliquer_maj(
            conn, "of_imports", of_id, updates,
            origine="manuel", auteur=qui,
            proteger_manuels=False,
            marquer_manuels=True,
            autoriser_effacement=True,
        )
        conn.commit()
    # `ignored` non vide = des champs postes n'ont pas ete ecrits. On le remonte
    # plutot que de laisser croire a une mise a jour complete.
    return {"updated": True, "id": of_id,
            "updated_fields": maj["ecrits"], "ignored": ignores,
            "validation_retiree": maj["invalide"],
            "motif_validation": maj["motif"]}


@router.get("/api/of/planning/{entry_id}")
def get_of_for_planning_entry(entry_id: int, request: Request):
    get_current_user(request)  # authentification simple, pas de rôle requis
    with get_db() as conn:
        entry = conn.execute(
            """SELECT pe.of_import_id, pe.numero_of, pe.ref_produit,
                      pe.machine_id, m.nom AS machine_nom
               FROM planning_entries pe
               LEFT JOIN machines m ON m.id = pe.machine_id
               WHERE pe.id = ?""",
            (entry_id,),
        ).fetchone()
    if not entry:
        return {"linked": False, "entry_numero_of": None, "ref_produit": None, "fiche_id": None}

    of_import_id = entry["of_import_id"]
    numero_of    = entry["numero_of"]
    ref_produit  = entry["ref_produit"]
    machine_nom  = entry["machine_nom"]

    # Pré-calculer ref_produit_norm pour aider à désambiguïser la lookup OF
    # (cf. _lookup_of_by_numero en bas de ce module — phase 2 du cascade).
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit as _norm_rp
        _ref_produit_norm_for_of_lookup = _norm_rp(ref_produit) if ref_produit else None
    except Exception:
        _ref_produit_norm_for_of_lookup = None

    row = None

    # 1. Lien direct par of_import_id
    if of_import_id:
        with get_db() as c:
            row = c.execute(
                """SELECT id, of_numero, reference, machine, pdf_filename,
                          date_import, imported_by, delai_client, qte_etiquettes, metrage
                   FROM of_imports WHERE id=?""",
                (of_import_id,),
            ).fetchone()

    # 2. Fallback : of_import_id absent ou lien mort → chercher par numero_of
    # Skippe si l'utilisateur a déjà géré manuellement (flag of_link_user_managed=1)
    if not row and numero_of:
        _skip_auto = False
        try:
            with get_db() as _c_check:
                _pe_cols = {r["name"] for r in _c_check.execute("PRAGMA table_info(planning_entries)").fetchall()}
                if "of_link_user_managed" in _pe_cols:
                    _flag = _c_check.execute(
                        "SELECT COALESCE(of_link_user_managed,0) FROM planning_entries WHERE id=?",
                        (entry_id,),
                    ).fetchone()
                    _skip_auto = bool(_flag and int(_flag[0] or 0) == 1)
        except Exception:
            _skip_auto = False

        if not _skip_auto:
            row = _lookup_of_by_numero(numero_of, _ref_produit_norm_for_of_lookup)
            if row:
                # Persister le lien via planning_of_links (trigger sync of_import_id)
                try:
                    with get_db() as c2:
                        c2.execute(
                            "INSERT OR IGNORE INTO planning_of_links "
                            "(planning_entry_id, of_import_id, position, created_by, created_at) "
                            "VALUES (?, ?, 0, 'auto_lookup', ?)",
                            (entry_id, row["id"], _now_paris_iso()),
                        )
                        c2.commit()
                except Exception:
                    pass

    # Chercher la fiche technique par ref_produit.
    # On matche en priorité sur la clé produit normalisée (ref_produit_norm,
    # XXX/NNNN) — insensible à la variante machine/laize présente dans le
    # libellé de la fiche, et tolère "1315-0004" côté dossier vs "1315/0004
    # - COHESIO 1" côté fiche. Si plusieurs fiches partagent la même clé
    # produit (cas fréquent : une variante par machine), on privilégie celle
    # dont la machine correspond à la machine du planning. Fallback sur la
    # référence textuelle complète pour les fiches non encore re-parsées.
    fiche_id = None
    if ref_produit:
        try:
            from app.services.fiche_ref_parser import normalize_ref_produit
            norm = normalize_ref_produit(ref_produit)
        except Exception:
            norm = None
        with get_db() as conn3:
            if norm:
                # ORDER BY : la fiche dont la machine matche la machine du
                # dossier au planning passe en premier ; en cas d'absence
                # de machine sur la fiche, on garde quand même un candidat ;
                # en dernier recours, fiche dont la machine ne matche pas.
                fiche = conn3.execute(
                    """SELECT id FROM fiches_techniques
                       WHERE ref_produit_norm = ?
                       ORDER BY
                         CASE
                           WHEN LOWER(TRIM(COALESCE(machine,''))) = LOWER(TRIM(COALESCE(?,''))) AND TRIM(COALESCE(machine,'')) != '' THEN 0
                           WHEN TRIM(COALESCE(machine,'')) = '' THEN 1
                           ELSE 2
                         END,
                         id
                       LIMIT 1""",
                    (norm, machine_nom or ""),
                ).fetchone()
                if fiche:
                    fiche_id = fiche["id"]
            if fiche_id is None:
                fiche = conn3.execute(
                    "SELECT id FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
                    (ref_produit,),
                ).fetchone()
                if fiche:
                    fiche_id = fiche["id"]

    # Récupère la liste complète des OF liés (multi via planning_of_links).
    # `of` (singular) reste = premier lien (rétrocompat panneau planning).
    ofs_list: list = []
    try:
        with get_db() as c3:
            ofs_rows = c3.execute(
                """SELECT o.id, o.of_numero, o.reference, o.machine, o.pdf_filename,
                          o.date_import, o.imported_by, o.delai_client, o.qte_etiquettes, o.metrage
                    FROM planning_of_links pl
                    JOIN of_imports o ON o.id = pl.of_import_id
                    WHERE pl.planning_entry_id = ?
                    ORDER BY pl.position ASC, pl.id ASC""",
                (entry_id,),
            ).fetchall()
            ofs_list = [_row_dict(r) for r in ofs_rows]
    except Exception:
        ofs_list = []

    base = {"entry_numero_of": numero_of, "ref_produit": ref_produit,
            "fiche_id": fiche_id, "ofs": ofs_list}

    if not row:
        return {"linked": False, **base}
    return {"linked": True, "of": _row_dict(row), **base}


def _enrich_of_row_from_fiche(of_row: dict) -> dict:
    """Enrichit un OF row (dict) à partir de la fiche technique liée.

    Politique :
      - `reference` est TOUJOURS remplacée par le ref_produit_norm (option B),
        extrait via le parser. Si l'extraction échoue, on garde la valeur
        d'origine.
      - Les autres champs (matiere, adhesif_label, ref_adhesif, glassine,
        qte_au_mille) ne sont remplis QUE s'ils sont vides côté OF (option α).
      - Désambiguïsation par machine : si plusieurs fiches partagent le
        même ref_produit_norm, on prend celle dont la machine correspond à
        l'OF (ou la première sans machine, sinon la première par id).

    Lecture seule. Retourne un nouveau dict, ne modifie pas l'original.
    """
    enriched = dict(of_row) if of_row else {}

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        return enriched

    # 1. Extraire ref_produit_norm depuis reference originale
    ref_norm = normalize_ref_produit(enriched.get("reference") or "")
    if ref_norm:
        enriched["reference"] = ref_norm

    if not ref_norm:
        # Pas de ref normalisée → on ne peut pas chercher la fiche
        return enriched

    # 2. Chercher la fiche technique correspondante
    machine_of = (enriched.get("machine") or "").strip()
    try:
        with get_db() as conn:
            fiche = conn.execute(
                """SELECT support, matiere, adhesif, glassine, qte_au_mille
                   FROM fiches_techniques
                   WHERE ref_produit_norm = ?
                   ORDER BY
                     CASE
                       WHEN LOWER(TRIM(COALESCE(machine,''))) = LOWER(TRIM(?))
                            AND TRIM(COALESCE(machine,'')) != '' THEN 0
                       WHEN TRIM(COALESCE(machine,'')) = '' THEN 1
                       ELSE 2
                     END,
                     id
                   LIMIT 1""",
                (ref_norm, machine_of),
            ).fetchone()
    except Exception:
        fiche = None

    if not fiche:
        return enriched

    f = dict(fiche)

    def _empty(v):
        return v is None or (isinstance(v, str) and not v.strip())

    # 3. Mapping fiche → OF (uniquement si OF vide)
    if _empty(enriched.get("matiere")):
        ft_mat = (f.get("support") or "").strip() or (f.get("matiere") or "").strip()
        if ft_mat:
            enriched["matiere"] = ft_mat

    ft_adh = (f.get("adhesif") or "").strip()
    if _empty(enriched.get("adhesif_label")) and ft_adh:
        enriched["adhesif_label"] = ft_adh
    if _empty(enriched.get("ref_adhesif")) and ft_adh:
        # Tente d'extraire un numéro propre (ex: "Permanent 2028Y - 19" → "2028")
        m_ref = re.search(r"\b(\d{3,5})\b", ft_adh)
        if m_ref:
            enriched["ref_adhesif"] = m_ref.group(1)

    if _empty(enriched.get("glassine")):
        ft_gl = (f.get("glassine") or "").strip()
        if ft_gl:
            enriched["glassine"] = ft_gl

    if enriched.get("qte_au_mille") in (None, "", 0, 0.0):
        ft_qam = f.get("qte_au_mille")
        if ft_qam is not None:
            enriched["qte_au_mille"] = ft_qam

    return enriched


@router.get("/api/of/{of_id}/pdf-preview")
def preview_of_pdf(of_id: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        # SELECT * volontaire : la liste explicite d'origine oubliait toute
        # colonne ajoutée ensuite, et l'oubli ne se voyait pas — le PDF sortait
        # simplement sans le champ.
        row = conn.execute(
            "SELECT * FROM of_imports WHERE id=?", (of_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="OF introuvable.")

    # OF importé via PDF → servir le fichier original
    if row["pdf_filename"]:
        path = os.path.join(OF_UPLOAD_DIR, row["pdf_filename"])
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Fichier PDF introuvable.")
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=row["pdf_filename"],
            headers={
                "Content-Disposition": f'inline; filename="{row["pdf_filename"]}"',
                # Le contenu d'un même of_id change désormais lors d'un
                # ré-import (upsert) : on interdit le cache navigateur, sinon
                # l'iframe ressert l'ancien aperçu.
                "Cache-Control": "no-store, must-revalidate",
            },
        )

    # OF importé via API (pas de PDF) → générer depuis le template vierge
    # Enrichissement à la volée depuis la fiche technique liée
    # (reference, matiere, adhesif, glassine, qte_au_mille).
    try:
        from app.services.of_pdf_generator import generate_of_pdf
        enriched = _enrich_of_row_from_fiche(dict(row))
        pdf_bytes = generate_of_pdf(enriched)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {exc}") from exc

    safe_num = re.sub(r"[^\w\-]+", "_", str(row["of_numero"] or of_id))
    filename = f"OF_{safe_num}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store, must-revalidate",
        },
    )


@router.get("/api/of/{of_id}/pdf")
def download_of_pdf(request: Request, of_id: int):
    _require_of_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT pdf_filename FROM of_imports WHERE id=?",
            (of_id,),
        ).fetchone()
    if not row or not row["pdf_filename"]:
        raise HTTPException(status_code=404, detail="OF introuvable.")
    path = os.path.join(OF_UPLOAD_DIR, row["pdf_filename"])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier PDF introuvable.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=row["pdf_filename"],
        headers={"Content-Disposition": f'attachment; filename="{row["pdf_filename"]}"'},
    )


@router.delete("/api/of/bulk")
async def bulk_delete_of(request: Request):
    """Suppression en masse d'OFs. Body JSON : {"ids": [1, 2, 3]}"""
    require_superadmin(request)
    body = await request.json()
    ids  = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Liste d'ids vide.")
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(f"DELETE FROM of_imports WHERE id IN ({placeholders})", ids)
        conn.commit()
    _invalidate_pending_count_cache()
    return {"deleted": len(ids), "ids": ids}


@router.delete("/api/of/{of_id}")
def delete_of_import(request: Request, of_id: int):
    require_superadmin(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        conn.execute("DELETE FROM of_imports WHERE id=?", (of_id,))
        conn.commit()
    _invalidate_pending_count_cache()
    return {"ok": True}


# ══════════════════════════════════════════════════
# Fiches techniques
# ══════════════════════════════════════════════════

@router.get("/api/fiches-techniques/list")
def list_fiches(request: Request):
    _require_of_access(request)
    q      = (request.query_params.get("q")      or "").strip()
    offset = int(request.query_params.get("offset") or 0)
    limit  = min(int(request.query_params.get("limit") or 50), 200)

    like = f"%{q}%"
    where = "WHERE 1=1"
    params_c: list = []
    params_r: list = []
    if q:
        where += " AND (LOWER(COALESCE(reference,'')) LIKE LOWER(?) OR LOWER(COALESCE(format,'')) LIKE LOWER(?) OR LOWER(COALESCE(support,'')) LIKE LOWER(?) OR LOWER(COALESCE(machine,'')) LIKE LOWER(?))"
        params_c = [like, like, like, like]
        params_r = [like, like, like, like, limit, offset]
    else:
        params_r = [limit, offset]

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM fiches_techniques {where}", params_c).fetchone()[0]
        rows  = conn.execute(
            f"SELECT * FROM fiches_techniques {where} ORDER BY date_import DESC LIMIT ? OFFSET ?",
            params_r,
        ).fetchall()
    return {"total": total, "offset": offset, "limit": limit, "rows": [_row_dict(r) for r in rows]}


@router.patch("/api/fiches-techniques/{fiche_id}")
async def update_fiche(fiche_id: int, request: Request):
    user = _require_of_access(request)
    body = await request.json()
    EDITABLE = {
        "reference","designation","client","format",
        "eti_laize","eti_longueur","eti_rayons","eti_perforations",
        "mod_laize","mod_longueur","mod_nb_front",
        "support","matiere","glassine","laize_optimale","laize_optionnelle",
        "epaisseur","adhesif","qte_au_mille",
        "machine","nb_couleurs","recto","verso",
        "tete1_pantone","tete1_couleur","tete1_anilox","tete1_composition",
        "tete2_pantone","tete2_couleur","tete2_anilox","tete2_composition",
        "tete3_pantone","tete3_couleur","tete3_anilox","tete3_composition",
        "remarque","mandrin_dia","mandrin_longueur","enroulement","nb_etiq_bobin",
        "dia_ext","poids","conditionnement","cales_sachets","cartons",
        "nb_au_sol","nb_etage","nb_bobines_carton",
        "palette_type","palette_nb_cartons_sol","palette_nb_cartons_hauteur","palette_hauteur_max",
        "particularite","notes",
        # Lien vers l'article de l'ERP. Stocké, pas redeviné : voir
        # rvgi_rattachement.couper_reference.
        "article_code1","article_code2","article_libelle",
        "support_ref_id","glassine_ref_id","adhesif_ref_id",
        "carton_ref_id","mandrin_ref_id","palette_ref_id",
        "palette_type","grammage",
    }
    updates = {k: v for k, v in body.items() if k in EDITABLE}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ modifiable.")
    qui = (user.get("nom") or user.get("email") or "").strip() or None
    with get_db() as conn:
        if not conn.execute("SELECT id FROM fiches_techniques WHERE id=?", (fiche_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fiche introuvable.")
        _appliquer_references(conn, updates, REFERENCES_FT)
        # Meme contrat que sur l'OF. C'est ici que se jouait la perte la plus
        # brutale : une correction atelier saisie dans MySifa etait ecrasee au
        # sync Access suivant, sans trace. Elle est desormais protegee.
        maj = appliquer_maj(
            conn, "fiches_techniques", fiche_id, updates,
            origine="manuel", auteur=qui,
            proteger_manuels=False,
            marquer_manuels=True,
            autoriser_effacement=True,
        )
        conn.commit()
    return {"updated": True, "id": fiche_id,
            "updated_fields": maj["ecrits"],
            "validation_retiree": maj["invalide"],
            "motif_validation": maj["motif"]}


@router.get("/api/fiches-techniques/{fiche_id}/pdf-preview")
def preview_fiche_pdf(fiche_id: int, request: Request):
    """Génère et retourne le PDF d'une fiche technique (auth session)."""
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE id=?", (fiche_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fiche introuvable.")
    try:
        from app.services.fiche_pdf import generate_fiche_pdf
        pdf_bytes = generate_fiche_pdf(dict(row))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {exc}") from exc
    ref = re.sub(r"[^\w\-]+", "_", str(row["reference"] or fiche_id))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="fiche_{ref}.pdf"'},
    )


@router.get("/api/fiches-techniques/{fiche_id}/pdf-client")
def preview_fiche_pdf_client(fiche_id: int, request: Request):
    """
    Génère la fiche technique CLIENT (bilingue FR/EN) d'une fiche technique.

    Version simplifiée à destination des clients : ne contient que les
    caractéristiques essentielles (format, frontal, adhésif, grammage,
    nombre d'impressions, conditionnement) avec libellés bilingues,
    en-tête SIFA + coordonnées et pied de page daté/versionné.
    """
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE id=?", (fiche_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fiche introuvable.")
    try:
        from app.services.fiche_pdf_client import (
            generate_fiche_client_pdf, _clean_reference,
        )
        pdf_bytes = generate_fiche_client_pdf(dict(row))
        # Nom de fichier basé sur la référence tronquée (ex. "748/0016 - COHESIO 1"
        # → "748_0016") pour rester cohérent avec l'affichage.
        ref_clean = _clean_reference(row["reference"] or fiche_id)
        ref = re.sub(r"[^\w\-]+", "_", ref_clean)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF client : {exc}") from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="fiche_client_{ref}.pdf"'},
    )


@router.delete("/api/fiches-techniques/bulk")
async def bulk_delete_fiches(request: Request):
    """Suppression en masse de fiches techniques. Body JSON : {"ids": [1, 2, 3]}"""
    require_superadmin(request)
    body = await request.json()
    ids  = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Liste d'ids vide.")
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(f"DELETE FROM fiches_techniques WHERE id IN ({placeholders})", ids)
        conn.commit()
    return {"deleted": len(ids), "ids": ids}


@router.delete("/api/fiches-techniques/{fiche_id}")
def delete_fiche(fiche_id: int, request: Request):
    require_superadmin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM fiches_techniques WHERE id=?", (fiche_id,))
        conn.commit()
    return {"deleted": True, "id": fiche_id}


# ─────────────────────────────────────────────────────────────────────────────
# Backfill ref_produit_norm (admin)
#
# Re-parse toutes les fiches_techniques et planning_entries pour remplir
# ref_produit_norm, machine, laize_mm, conditionnement_norm. Idempotent :
# ne touche que les colonnes vides ou désynchronisées. Ne modifie jamais
# une machine/conditionnement déjà saisi à la main.
#
# Usage :
#   POST /api/admin/backfill-ref-produit-norm            → applique
#   POST /api/admin/backfill-ref-produit-norm?dry_run=1  → simulation (lecture seule)
#
# Réservé au superadmin (le backfill modifie potentiellement plusieurs centaines
# de lignes en une fois — pas une action quotidienne).
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/api/admin/backfill-ref-produit-norm")
def admin_backfill_ref_produit_norm(request: Request):
    require_superadmin(request)

    dry_run = (request.query_params.get("dry_run") or "").lower() in ("1", "true", "yes", "on")

    try:
        from app.services.fiche_ref_parser import (
            parse_fiche_reference,
            normalize_ref_produit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parser indisponible : {exc}")

    fiches_total = 0
    fiches_updated = 0
    fiches_unchanged = 0
    fiches_no_match = 0
    fiches_preview: list = []

    pe_total = 0
    pe_updated = 0
    pe_unchanged = 0
    pe_no_match = 0
    pe_preview: list = []

    with get_db() as conn:
        ft_cols = {r["name"] for r in conn.execute("PRAGMA table_info(fiches_techniques)").fetchall()}
        if "ref_produit_norm" not in ft_cols:
            raise HTTPException(
                status_code=500,
                detail="Migration 101 non appliquée (colonne ref_produit_norm absente). Redémarre le service pour déclencher la migration.",
            )

        rows = conn.execute(
            "SELECT id, reference, ref_produit_norm, machine, laize_mm, "
            "       conditionnement, conditionnement_norm "
            "FROM fiches_techniques"
        ).fetchall()
        fiches_total = len(rows)

        for row in rows:
            parsed = parse_fiche_reference(row["reference"])
            updates: dict = {}

            new_norm = parsed.get("ref_produit_norm")
            cur_norm = (row["ref_produit_norm"] or "").strip()
            if new_norm and new_norm != cur_norm:
                updates["ref_produit_norm"] = new_norm

            # Ne pas écraser une machine saisie à la main.
            new_machine = parsed.get("machine")
            cur_machine = (row["machine"] or "").strip()
            if new_machine and not cur_machine:
                updates["machine"] = new_machine

            new_laize = parsed.get("laize_mm")
            if new_laize and not row["laize_mm"]:
                updates["laize_mm"] = new_laize

            new_cond = parsed.get("conditionnement_norm")
            cur_cond_norm = (row["conditionnement_norm"] or "").strip()
            cur_cond_raw = (row["conditionnement"] or "").strip()
            if new_cond and not cur_cond_norm and not cur_cond_raw:
                updates["conditionnement_norm"] = new_cond

            if not updates:
                if new_norm:
                    fiches_unchanged += 1
                else:
                    fiches_no_match += 1
                continue

            fiches_updated += 1
            if len(fiches_preview) < 25:
                fiches_preview.append({
                    "id": row["id"],
                    "reference": row["reference"],
                    "updates": updates,
                })
            if not dry_run:
                set_clause = ", ".join(f"{k}=?" for k in updates)
                conn.execute(
                    f"UPDATE fiches_techniques SET {set_clause} WHERE id=?",
                    list(updates.values()) + [row["id"]],
                )

        pe_rows = conn.execute(
            "SELECT id, ref_produit, ref_produit_norm "
            "FROM planning_entries "
            "WHERE ref_produit IS NOT NULL AND TRIM(ref_produit) != ''"
        ).fetchall()
        pe_total = len(pe_rows)

        for row in pe_rows:
            norm = normalize_ref_produit(row["ref_produit"])
            if not norm:
                pe_no_match += 1
                continue
            cur = (row["ref_produit_norm"] or "").strip()
            if norm == cur:
                pe_unchanged += 1
                continue
            pe_updated += 1
            if len(pe_preview) < 25:
                pe_preview.append({
                    "id": row["id"],
                    "ref_produit": row["ref_produit"],
                    "ref_produit_norm": norm,
                })
            if not dry_run:
                conn.execute(
                    "UPDATE planning_entries SET ref_produit_norm=? WHERE id=?",
                    (norm, row["id"]),
                )

        if not dry_run:
            conn.commit()

    return {
        "dry_run": dry_run,
        "fiches_techniques": {
            "total": fiches_total,
            "updated": fiches_updated,
            "unchanged": fiches_unchanged,
            "no_match": fiches_no_match,
            "preview": fiches_preview,
        },
        "planning_entries": {
            "total": pe_total,
            "updated": pe_updated,
            "unchanged": pe_unchanged,
            "no_match": pe_no_match,
            "preview": pe_preview,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lookup OF par numero, en cascade.
#
# Ordre des passes :
#   1. Match exact (LOWER/TRIM, + normalisation numérique 9931861.0 → 9931861)
#   2. Match exact après retrait du préfixe "OF "
#   3. Extraction du numéro racine 99XXXXX dans le numero, puis recherche
#      d'OF dont l'of_numero contient ce numéro. Désambiguïsation par
#      ref_produit_norm si fourni (l'OF dont la référence matche le produit
#      du planning passe en premier), puis par date_import desc.
#
# Lecture seule (SELECT). Retourne None si rien ne matche.
# ─────────────────────────────────────────────────────────────────────────────

# Normalisation commune aux deux sens du rapprochement (dossier ↔ OF).
_OF_TOKEN_RE  = re.compile(r"\d{5,}")
_OF_RACINE_RE = re.compile(r"\b(99\d{5})\b")   # conservé : dédoublonnage à l'import
_OF_PREFIX_RE = re.compile(r"^\s*OF\s+(.+?)\s*$", re.IGNORECASE)

_OF_SELECT_COLS = (
    "id, of_numero, reference, machine, pdf_filename, "
    "date_import, imported_by, delai_client, qte_etiquettes, metrage"
)


def _of_norm_key(value) -> str:
    """Clé de comparaison d'un numéro d'OF : majuscules, sans accents, sans
    préfixe « OF », ponctuation réduite à un espace.

        "OF 9932376-377"     → "9932376 377"
        "9932163 Reliquat 2" → "9932163 RELIQUAT 2"
    """
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = _OF_PREFIX_RE.sub(r"\1", s.strip()).upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _of_tokens(value) -> list:
    """Tokens numériques de 5 chiffres et plus, dans l'ordre, dédoublonnés.

    C'est ce qui permet de rapprocher "9932376-377" ou "9932163 Reliquat 2"
    de l'OF 9932376 / 9932163 — l'égalité stricte, elle, échoue.
    """
    return list(dict.fromkeys(_OF_TOKEN_RE.findall(str(value or ""))))


def _of_token_present(token: str, haystack) -> bool:
    """Vrai si `token` apparaît dans `haystack` sans être collé à d'autres
    chiffres — garde-fou pour que 9932163 ne matche pas 19932163."""
    if not token or not haystack:
        return False
    return re.search(r"(?<!\d)" + re.escape(token) + r"(?!\d)", str(haystack)) is not None


def _lookup_of_candidates(num: Optional[str], ref_produit_norm: Optional[str] = None,
                          conn=None, machine: Optional[str] = None):
    """Lookup OF en cascade — distingue match certain vs ambigu.

    Retourne un tuple (certain_row_or_None, candidates_list).

    Cascade de collecte :
      1. égalité stricte sur `of_numero` (cas nominal, le moins coûteux)
      2. inclusion par token numérique de 5+ chiffres — couvre les deux sens :
         le numéro du dossier contient celui de l'OF ("9932376-377" → 9932376)
         comme l'inverse ("9932376" → OF "9932376-377")
      3. à défaut de tout token numérique, rapprochement par référence produit
         (dossiers nommés "1068/0001 - Reliquat 2 - Marché 745")

    Désambiguïsation quand plusieurs candidats subsistent, dans cet ordre :
      a. clé normalisée identique   b. référence produit identique
      c. même jeu de tokens          d. machine identique
    Un seul survivant → match certain. Sinon → liste triée pour arbitrage
    humain (onglet « Mappings à valider »).

    Lecture seule.
    """
    if not num:
        return (None, [])
    s = str(num).strip()
    if not s:
        return (None, [])

    key = _of_norm_key(s)
    tokens = _of_tokens(s)

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    # conn fourni par l'appelant (boucles) : on le réutilise au lieu d'ouvrir
    # une connexion SQLite par appel — c'était la cause des ~600 ms du badge
    # of-link-pending (une connexion + cascade de requêtes PAR dossier).
    with (nullcontext(conn) if conn is not None else get_db()) as c:
        # ── Étape 1 : égalité stricte, avec ou sans préfixe "OF " ────────────
        candidates_exact: list = [s]
        try:
            candidates_exact.append(str(int(float(s))))
        except (ValueError, OverflowError):
            pass

        m_prefix = _OF_PREFIX_RE.match(s)
        if m_prefix:
            inner = m_prefix.group(1).strip()
            candidates_exact.append(inner)
            try:
                candidates_exact.append(str(int(float(inner))))
            except (ValueError, OverflowError):
                pass

        for cand in dict.fromkeys(candidates_exact):
            # ORDER BY explicite : sans lui SQLite renvoyait le plus petit
            # rowid, c'est-à-dire le doublon le PLUS ANCIEN. On privilégie
            # désormais un OF disposant d'un vrai PDF, puis le plus récent.
            r = c.execute(
                f"""SELECT {_OF_SELECT_COLS}
                    FROM of_imports
                    WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))
                    ORDER BY (TRIM(COALESCE(pdf_filename,'')) != '') DESC,
                             date_import DESC,
                             id DESC
                    LIMIT 1""",
                (cand,),
            ).fetchone()
            if r:
                return (r, [])

        # ── Étape 2 : inclusion par token numérique ──────────────────────────
        rows: list = []
        if tokens:
            like_sql = " OR ".join(["of_numero LIKE ?"] * len(tokens))
            found = c.execute(
                f"SELECT {_OF_SELECT_COLS} FROM of_imports WHERE {like_sql}",
                tuple("%" + t + "%" for t in tokens),
            ).fetchall()
            # garde-fou : le token doit être isolé, pas noyé dans un plus long
            rows = [r for r in found
                    if any(_of_token_present(t, r["of_numero"]) for t in tokens)]

        # ── Étape 3 : aucun token → rapprochement par référence produit ──────
        if not rows and not tokens and ref_produit_norm and normalize_ref_produit is not None:
            by_ref = c.execute(
                f"""SELECT {_OF_SELECT_COLS} FROM of_imports
                    WHERE TRIM(COALESCE(reference,'')) != ''"""
            ).fetchall()
            rows = [r for r in by_ref
                    if normalize_ref_produit(r["reference"]) == ref_produit_norm]

        if not rows:
            return (None, [])
        if len(rows) == 1:
            return (rows[0], [])

        # ── Désambiguïsation ─────────────────────────────────────────────────
        def _unique(subset):
            return subset[0] if len(subset) == 1 else None

        win = _unique([r for r in rows if _of_norm_key(r["of_numero"]) == key])

        if win is None and ref_produit_norm and normalize_ref_produit is not None:
            win = _unique([r for r in rows
                           if r["reference"]
                           and normalize_ref_produit(r["reference"]) == ref_produit_norm])

        if win is None and tokens:
            tset = set(tokens)
            win = _unique([r for r in rows if set(_of_tokens(r["of_numero"])) == tset])

        if win is None and machine:
            mk = _of_norm_key(machine)
            win = _unique([r for r in rows
                           if r["machine"] and _of_norm_key(r["machine"]) == mk])

        if win is not None:
            return (win, [])

        # Pas de désambiguïsation possible → ambigu (human-in-the-loop).
        # Tri : OF avec PDF d'abord, puis le plus récent.
        rows = sorted(rows, key=lambda r: (
            0 if (r["pdf_filename"] or "").strip() else 1,
            -(int(r["id"]) if r["id"] is not None else 0),
        ))
        return (None, [dict(r) for r in rows])

def _lookup_of_by_numero(num: Optional[str], ref_produit_norm: Optional[str] = None):
    """Variante "match certain uniquement" pour les appels qui ne gèrent pas
    l'ambiguïté (ex. lookup à la volée depuis /api/of/planning/{id}).

    Retourne la row si match certain, None sinon. Voir _lookup_of_candidates
    pour le détail de la cascade.
    """
    certain, _ = _lookup_of_candidates(num, ref_produit_norm)
    return certain


# ─────────────────────────────────────────────────────────────────────────────
# Relink OF en batch (admin)
#
# Parcourt les planning_entries qui ont un numero_of mais pas de of_import_id
# (ou un lien mort), tente une lookup via _lookup_of_by_numero, et persiste
# le lien si trouvé. Idempotent.
#
# Usage :
#   POST /api/admin/relink-of            → applique
#   POST /api/admin/relink-of?dry_run=1  → simulation (lecture seule)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/api/admin/relink-of")
def admin_relink_of(request: Request):
    # Ouvert aux admins OF (et non plus au seul superadmin) : c'est l'action
    # « Relancer le mapping automatique » du bouton de l'onglet Dossiers sans OF.
    _require_of_access(request)

    dry_run = (request.query_params.get("dry_run") or "").lower() in ("1", "true", "yes", "on")

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    total = 0
    relinked = 0
    already_linked = 0
    unmatched = 0
    pending_for_review = 0
    repaired_links = 0
    preview: list = []
    pending_preview: list = []

    with get_db() as conn:
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        has_norm = "ref_produit_norm" in pe_cols

        sql = (
            "SELECT pe.id, pe.numero_of, pe.ref_produit, "
            + ("pe.ref_produit_norm, " if has_norm else "")
            + "pe.of_import_id, m.nom AS machine_nom "
            "FROM planning_entries pe "
            "LEFT JOIN machines m ON m.id = pe.machine_id "
            "WHERE pe.numero_of IS NOT NULL AND TRIM(pe.numero_of) != ''"
        )
        rows = conn.execute(sql).fetchall()
        total = len(rows)

        # Réparation préalable : le pont Access n'écrit que
        # planning_entries.of_import_id, jamais planning_of_links. Ces dossiers
        # sont pourtant liés — sans cette reprise ils comptent « sans OF ».
        try:
            orphans = conn.execute(
                "SELECT pe.id, pe.of_import_id FROM planning_entries pe "
                "JOIN of_imports oi ON oi.id = pe.of_import_id "
                "WHERE pe.of_import_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM planning_of_links pl "
                "                WHERE pl.planning_entry_id = pe.id)"
            ).fetchall()
            for o in orphans:
                if not dry_run:
                    conn.execute(
                        "INSERT OR IGNORE INTO planning_of_links "
                        "(planning_entry_id, of_import_id, position, created_by, created_at) "
                        "VALUES (?, ?, 0, 'access_bridge_repair', ?)",
                        (o["id"], o["of_import_id"], _now_paris_iso()),
                    )
                repaired_links += 1
        except Exception:
            repaired_links = 0

        for row in rows:
            # Si lien déjà en place et OF existe, on saute
            if row["of_import_id"]:
                check = conn.execute(
                    "SELECT 1 FROM of_imports WHERE id=?",
                    (row["of_import_id"],),
                ).fetchone()
                if check:
                    already_linked += 1
                    continue
                # lien mort, on retente

            ref_norm = None
            if has_norm:
                ref_norm = (row["ref_produit_norm"] or "").strip() or None
            if not ref_norm and normalize_ref_produit is not None:
                ref_norm = normalize_ref_produit(row["ref_produit"])

            certain, candidates = _lookup_of_candidates(
                row["numero_of"], ref_norm, conn=conn, machine=row["machine_nom"])

            if certain:
                relinked += 1
                if len(preview) < 30:
                    preview.append({
                        "planning_id": row["id"],
                        "planning_numero_of": row["numero_of"],
                        "planning_ref_produit": row["ref_produit"],
                        "of_id": certain["id"],
                        "of_numero": certain["of_numero"],
                        "of_reference": certain["reference"],
                    })
                if not dry_run:
                    conn.execute(
                        "INSERT OR IGNORE INTO planning_of_links "
                        "(planning_entry_id, of_import_id, position, created_by, created_at) "
                        "VALUES (?, ?, 0, 'admin_relink', ?)",
                        (row["id"], certain["id"], _now_paris_iso()),
                    )
                continue

            if candidates:
                # Ambigu : on n'auto-link pas, le service admin choisira via l'UI
                pending_for_review += 1
                if len(pending_preview) < 15:
                    pending_preview.append({
                        "planning_id": row["id"],
                        "planning_numero_of": row["numero_of"],
                        "planning_ref_produit": row["ref_produit"],
                        "candidates_count": len(candidates),
                        "candidates_sample": [
                            {"of_id": c["id"], "of_numero": c["of_numero"]}
                            for c in candidates[:3]
                        ],
                    })
                continue

            unmatched += 1

        if not dry_run:
            conn.commit()

    if not dry_run:
        # Sans ça, le badge « Dossiers sans OF » gardait sa valeur d'avant le
        # rapprochement pendant toute la durée du cache : liste à 7, badge à 16.
        _invalidate_pending_count_cache()

    return {
        "dry_run": dry_run,
        "total_with_numero_of": total,
        "already_linked": already_linked,
        "repaired_links": repaired_links,
        "relinked": relinked,
        "pending_for_review": pending_for_review,
        "pending_preview": pending_preview,
        "unmatched": unmatched,
        "preview": preview,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mappings OF "à valider" — human-in-the-loop
#
# Quand la lookup automatique trouve PLUSIEURS OF candidats pour un même
# planning_entry (extraction racine 99XXXXX avec multiples matchs et sans
# désambiguïsation possible), on ne lie pas automatiquement : le service
# administration choisit le bon OF via une UI dédiée dans la page Fiches+OF.
#
# Endpoints :
#   GET  /api/admin/of-link-pending/count  → juste le nombre (pour le badge)
#   GET  /api/admin/of-link-pending        → liste détaillée avec candidats
#   POST /api/admin/link-planning-of       → enregistre un choix manuel
# ─────────────────────────────────────────────────────────────────────────────


def _iter_pending_planning_rows(conn):
    """Itère sur les planning_entries sans of_import_id mais avec un numero_of.
    Yield un tuple (row, ref_produit_norm, candidates) UNIQUEMENT pour les cas
    ambigus (2+ candidats sans désambiguïsation possible).
    """
    pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
    has_norm = "ref_produit_norm" in pe_cols

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    sql = (
        "SELECT pe.id, pe.numero_of, pe.ref_produit, "
        + ("pe.ref_produit_norm, " if has_norm else "")
        + "pe.machine_id, m.nom AS machine_nom "
        "FROM planning_entries pe "
        "LEFT JOIN machines m ON m.id = pe.machine_id "
        "WHERE pe.numero_of IS NOT NULL AND TRIM(pe.numero_of) != '' "
        "AND pe.of_import_id IS NULL"
    )
    for row in conn.execute(sql).fetchall():
        ref_norm = None
        if has_norm:
            ref_norm = (row["ref_produit_norm"] or "").strip() or None
        if not ref_norm and normalize_ref_produit is not None:
            ref_norm = normalize_ref_produit(row["ref_produit"])

        certain, candidates = _lookup_of_candidates(
            row["numero_of"], ref_norm, conn=conn, machine=row["machine_nom"])
        if certain:
            continue
        if not candidates or len(candidates) < 2:
            continue
        yield row, ref_norm, candidates


_PENDING_COUNT_TTL = 60  # secondes — le badge tolère un léger retard
_pending_count_cache: dict = {"at": 0.0, "data": None}


def _invalidate_pending_count_cache() -> None:
    """À appeler après TOUTE écriture qui change le nombre de dossiers sans OF.

    Le cache est un cache de process, pas de requête : le vider avant l'écriture
    ne sert à rien — un autre admin peut le repeupler avec l'ancienne valeur
    pendant la transaction. Il se vide donc APRÈS le commit, systématiquement.

    Endpoints concernés : import d'un PDF d'OF (auto-link), suppression d'un OF
    (unitaire ou en masse), relance du mapping automatique, ajout et retrait de
    liens planning↔OF, rattachement depuis Besoins matières, push Access.
    """
    _pending_count_cache["at"] = 0.0
    _pending_count_cache["data"] = None


@router.get("/api/admin/of-link-pending/count")
def admin_of_link_pending_count(request: Request):
    """Badge unifié : ambigus (à arbitrer) + dossiers sans aucun OF (à associer).

    Résultat global (pas par utilisateur) → cache process 60 s : le calcul des
    ambigus reste coûteux (cascade de lookups par dossier non lié) et le badge
    est rechargé à chaque affichage du portail par chaque admin.
    """
    _require_of_access(request)
    now = time.monotonic()
    if _pending_count_cache["data"] is not None and now - _pending_count_cache["at"] < _PENDING_COUNT_TTL:
        return _pending_count_cache["data"]
    ambigus = 0
    sans_of = 0
    with get_db() as conn:
        for _ in _iter_pending_planning_rows(conn):
            ambigus += 1
        sans_of = conn.execute(_DOSSIERS_SANS_OF_COUNT_SQL).fetchone()[0]
    data = {"count": ambigus + sans_of, "ambigus": ambigus, "sans_of": sans_of}
    _pending_count_cache["data"] = data
    _pending_count_cache["at"] = now
    return data


@router.get("/api/admin/of-link-pending")
def admin_of_link_pending(request: Request):
    _require_of_access(request)
    items: list = []
    with get_db() as conn:
        for row, ref_norm, candidates in _iter_pending_planning_rows(conn):
            items.append({
                "planning_id": row["id"],
                "numero_of": row["numero_of"],
                "ref_produit": row["ref_produit"],
                "ref_produit_norm": ref_norm,
                "machine": row["machine_nom"],
                "candidates": candidates,
            })
    return {"total": len(items), "items": items}


@router.post("/api/admin/link-planning-of")
async def admin_link_planning_of(request: Request):
    _require_of_access(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON requis.")

    planning_id = body.get("planning_id")
    of_id = body.get("of_id")  # null = délier

    if not isinstance(planning_id, int):
        raise HTTPException(status_code=400, detail="planning_id (int) requis.")
    if of_id is not None and not isinstance(of_id, int):
        raise HTTPException(status_code=400, detail="of_id doit etre int ou null.")

    with get_db() as conn:
        pe = conn.execute(
            "SELECT id FROM planning_entries WHERE id=?", (planning_id,)
        ).fetchone()
        if not pe:
            raise HTTPException(status_code=404, detail="Planning introuvable.")

        if of_id is not None:
            oi = conn.execute(
                "SELECT id FROM of_imports WHERE id=?", (of_id,)
            ).fetchone()
            if not oi:
                raise HTTPException(status_code=404, detail="OF introuvable.")

        if of_id is None:
            # "délier" = retirer TOUS les liens pour ce planning
            conn.execute(
                "DELETE FROM planning_of_links WHERE planning_entry_id=?",
                (planning_id,),
            )
        else:
            user = get_current_user(request)
            who = (user.get("nom") or user.get("email") or str(user.get("id", ""))) if user else ""
            conn.execute(
                "INSERT OR IGNORE INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, 0, ?, ?)",
                (planning_id, of_id, who, _now_paris_iso()),
            )
        # Action manuelle : désactive l'auto-link futur pour ce planning
        try:
            conn.execute("UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?", (planning_id,))
        except Exception:
            pass
        conn.commit()

    _invalidate_pending_count_cache()
    return {"linked": True, "planning_id": planning_id, "of_id": of_id}


# ─────────────────────────────────────────────────────────────────────────────
# Dossiers sans aucun OF lié (planning_of_links vide)
# ─────────────────────────────────────────────────────────────────────────────

# Un dossier n'est « sans OF » que s'il n'a NI ligne dans planning_of_links,
# NI of_import_id pointant sur un OF réel : le pont Access ne renseigne que la
# seconde colonne, ses dossiers étaient donc comptés à tort.
_DOSSIERS_SANS_OF_WHERE = (
    "WHERE NOT EXISTS (SELECT 1 FROM planning_of_links pl "
    "                  WHERE pl.planning_entry_id = pe.id) "
    "AND NOT EXISTS (SELECT 1 FROM of_imports oi "
    "                WHERE oi.id = pe.of_import_id) "
    "AND COALESCE(pe.statut, '') != 'termine'"
)

_DOSSIERS_SANS_OF_COUNT_SQL = (
    "SELECT COUNT(*) FROM planning_entries pe " + _DOSSIERS_SANS_OF_WHERE
)


@router.get("/api/admin/dossiers-sans-of/count")
def admin_dossiers_sans_of_count(request: Request):
    _require_of_access(request)
    with get_db() as conn:
        n = conn.execute(_DOSSIERS_SANS_OF_COUNT_SQL).fetchone()[0]
    return {"count": int(n)}


@router.get("/api/admin/dossiers-sans-of")
def admin_dossiers_sans_of(request: Request):
    _require_of_access(request)
    rows = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT pe.id, pe.numero_of, pe.ref_produit, pe.ref_produit_norm, "
            "       pe.machine_id, m.nom AS machine_nom, "
            "       pe.created_at AS planning_created_at, "
            "       pe.statut, pe.duree_heures, pe.format_l, pe.format_h "
            "FROM planning_entries pe "
            "LEFT JOIN machines m ON m.id = pe.machine_id "
            + _DOSSIERS_SANS_OF_WHERE
            + " ORDER BY pe.created_at DESC, pe.id DESC"
        ).fetchall()
    items = []
    for r in rows:
        # « rapprochable » = il y a de quoi tenter un mapping automatique.
        # "Marché 761" n'a ni token numérique ni référence produit : aucun
        # algorithme ne le retrouvera, il faut l'attacher à la main.
        has_token = bool(_of_tokens(r["numero_of"]))
        has_ref = bool((r["ref_produit_norm"] or "").strip())
        items.append({
            "planning_id": r["id"],
            "numero_of": r["numero_of"],
            "ref_produit": r["ref_produit"],
            "ref_produit_norm": r["ref_produit_norm"],
            "machine": r["machine_nom"],
            "statut": r["statut"],
            "duree_heures": r["duree_heures"],
            "created_at": r["planning_created_at"],
            "rapprochable": has_token or has_ref,
        })
    return {
        "total": len(items),
        "rapprochables": sum(1 for i in items if i["rapprochable"]),
        "items": items,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Liens multi-OF par planning_entry (POST = ajoute, DELETE = retire)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/api/admin/planning-of-links")
async def admin_add_planning_of_links(request: Request):
    user = _require_of_access(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON requis.")

    planning_id = body.get("planning_id")
    of_ids = body.get("of_ids")
    if not isinstance(planning_id, int):
        raise HTTPException(status_code=400, detail="planning_id (int) requis.")
    if not isinstance(of_ids, list) or not of_ids:
        raise HTTPException(status_code=400, detail="of_ids (liste non vide) requis.")
    of_ids = [int(x) for x in of_ids if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
    of_ids = list(dict.fromkeys(of_ids))  # dedup, garde ordre
    if not of_ids:
        raise HTTPException(status_code=400, detail="of_ids invalides.")

    who = (user.get("nom") or user.get("email") or str(user.get("id", ""))) if user else ""
    now = _now_paris_iso()
    added = 0
    skipped_existing = 0
    not_found: list = []
    with get_db() as conn:
        pe = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_id,)).fetchone()
        if not pe:
            raise HTTPException(status_code=404, detail="Planning introuvable.")
        # Récupère la position max actuelle pour append à la fin
        cur_max = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM planning_of_links WHERE planning_entry_id=?",
            (planning_id,),
        ).fetchone()[0]
        next_pos = int(cur_max) + 1
        for of_id in of_ids:
            oi = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
            if not oi:
                not_found.append(of_id)
                continue
            cur = conn.execute(
                "SELECT id FROM planning_of_links WHERE planning_entry_id=? AND of_import_id=?",
                (planning_id, of_id),
            ).fetchone()
            if cur:
                skipped_existing += 1
                continue
            conn.execute(
                "INSERT INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (planning_id, of_id, next_pos, who, now),
            )
            next_pos += 1
            added += 1
        # Action manuelle : désactive l'auto-link futur pour ce planning
        try:
            conn.execute("UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?", (planning_id,))
        except Exception:
            pass
        conn.commit()
    _invalidate_pending_count_cache()
    return {
        "planning_id": planning_id,
        "added": added,
        "skipped_existing": skipped_existing,
        "not_found": not_found,
    }


@router.delete("/api/admin/planning-of-links")
async def admin_remove_planning_of_link(request: Request):
    _require_of_access(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON requis.")
    planning_id = body.get("planning_id")
    of_id = body.get("of_id")
    if not isinstance(planning_id, int) or not isinstance(of_id, int):
        raise HTTPException(status_code=400, detail="planning_id et of_id (int) requis.")
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM planning_of_links WHERE planning_entry_id=? AND of_import_id=?",
            (planning_id, of_id),
        )
        # Action manuelle : désactive l'auto-link futur pour ce planning
        try:
            conn.execute("UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?", (planning_id,))
        except Exception:
            pass
        conn.commit()
        deleted = cur.rowcount or 0
    _invalidate_pending_count_cache()
    return {"deleted": int(deleted), "planning_id": planning_id, "of_id": of_id}


# ─────────────────────────────────────────────────────────────────────────────
# Recherche d'OF (picker dans l'UI "Dossiers sans OF" et panneau planning)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/api/of/search")
def of_search(request: Request):
    _require_of_access(request)
    q = (request.query_params.get("q") or "").strip()
    try:
        limit = int(request.query_params.get("limit") or 20)
    except Exception:
        limit = 20
    limit = max(1, min(limit, 50))
    rows = []
    with get_db() as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                f"""SELECT {_OF_SELECT_COLS}
                    FROM of_imports
                    WHERE LOWER(COALESCE(of_numero,''))    LIKE LOWER(?)
                       OR LOWER(COALESCE(reference,''))   LIKE LOWER(?)
                       OR LOWER(COALESCE(machine,''))     LIKE LOWER(?)
                    ORDER BY date_import DESC, id DESC
                    LIMIT ?""",
                (like, like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {_OF_SELECT_COLS}
                    FROM of_imports
                    ORDER BY date_import DESC, id DESC
                    LIMIT ?""",
                (limit,),
            ).fetchall()
    return {"items": [_row_dict(r) for r in rows]}


# ═══════════════════════════════════════════════════════════════════════════
# Création dans MySifa
# ═══════════════════════════════════════════════════════════════════════════
#
# Jusqu'ici un OF et une fiche technique ne pouvaient qu'ARRIVER : du pont
# Access ou de la lecture d'un PDF. L'ADV qui prépare une production devait
# donc passer par Access pour créer le document, puis attendre la synchro pour
# le voir dans MySifa. Ces deux routes ferment la boucle.
#
# Trois choses les distinguent d'un import, et expliquent le reste du code :
#
# 1. `source = 'mysifa'` — sans quoi un OF saisi ici est indiscernable d'un OF
#    venu d'Access, et le prochain sync croirait devoir le compléter.
# 2. Tout ce qui est saisi est marqué manuel. C'est le contrat de
#    `documents_verite` : Access ne réécrit pas une valeur posée par un humain.
# 3. `valide = 0`. Créer n'est pas relire — la validation reste un second geste,
#    fait par quelqu'un qui contrôle, comme pour un document importé.

from app.services import rvgi_rattachement as ratt  # noqa: E402  (bas de module)
from app.services.audit_service import log_action  # noqa: E402


def _valeurs_non_vides(champs: dict) -> list:
    return [k for k, v in champs.items()
            if v is not None and str(v).strip() != ""]


def _lignes_commandes(brut) -> list:
    """Normalise les lignes de commande postées par le sélecteur RVGI."""
    lignes = []
    for l in (brut or []):
        if not isinstance(l, dict):
            continue
        numero = str(l.get("numero") or "").strip()
        if not numero:
            continue
        lignes.append({
            "numero": numero,
            "ligne": l.get("ligne"),
            "qte": l.get("qte"),
            "vu_qte": l.get("vu_qte"),
            "vu_article": l.get("vu_article"),
            "vu_client": l.get("vu_client"),
            "confirme": bool(l.get("confirme")),
        })
    return lignes


@router.post("/api/of")
async def create_of(request: Request):
    """Crée un OF dans MySifa, éventuellement rattaché à des commandes RVGI.

    Le numéro suit la règle des dossiers de fabrication : il se PROPOSE depuis
    les numéros de commande rattachés (« 9932128+129 », « 9932128/L1-3 ») et
    reste modifiable. Un OF peut couvrir une commande entière, quelques-unes de
    ses lignes, ou plusieurs commandes — c'est l'ADV qui arbitre, parce qu'elle
    seule sait ce qui part sur la même bobine.
    """
    user = _require_of_access(request)
    body = await request.json()

    champs = {k: _coerce_of_value(k, v) for k, v in body.items() if k in OF_DATA_FIELDS}
    commandes = _lignes_commandes(body.get("commandes"))

    numero = (champs.get("of_numero") or "").strip() if champs.get("of_numero") else ""
    if not numero and commandes:
        numero = ratt.proposer_reference(commandes)
    if not numero:
        raise HTTPException(
            status_code=400,
            detail="Numéro d'OF absent. Renseignez-le, ou rattachez au moins "
                   "une commande pour qu'il soit proposé.",
        )
    champs["of_numero"] = numero

    if not (champs.get("reference") or "").strip():
        raise HTTPException(status_code=400, detail="Référence produit obligatoire.")

    maintenant = _now_paris_iso()
    qui = (user.get("nom") or user.get("email") or "").strip() or None

    with get_db() as conn:
        # La désignation de la référence devient le texte imprimé, AVANT
        # l'insertion : sinon le document naîtrait avec un texte que personne
        # n'a choisi.
        _appliquer_references(conn, champs, REFERENCES_OF)
        double = conn.execute(
            "SELECT id FROM of_imports WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))",
            (numero,),
        ).fetchone()
        if double:
            # On refuse plutôt que de créer un homonyme : deux OF du même numéro
            # rendraient le rapprochement dossier↔OF indécidable, et c'est
            # exactement ce que l'onglet « Mappings à valider » sert à éviter.
            raise HTTPException(
                status_code=409,
                detail="L'OF %s existe déjà (#%d)." % (numero, double["id"]),
            )

        colonnes = list(champs.keys()) + [
            "source", "statut", "valide", "cree_par", "cree_le",
            "date_import", "imported_by",
        ]
        valeurs = list(champs.values()) + [
            "mysifa", "cree", 0, qui, maintenant, maintenant, qui,
        ]
        cur = conn.execute(
            "INSERT INTO of_imports (%s) VALUES (%s)"
            % (", ".join(colonnes), ", ".join("?" * len(colonnes))),
            valeurs,
        )
        of_id = cur.lastrowid

        marquer_champs_manuels(conn, "of_imports", of_id, _valeurs_non_vides(champs))

        rattachement = None
        if commandes:
            try:
                rattachement = ratt.enregistrer(
                    conn, "of", of_id, "commande", commandes, qui or "",
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()

    linked = _autolink_of_to_planning(of_id, numero, created_by="of_mysifa")
    _invalidate_pending_count_cache()

    # Ligne explicite plutôt que la ligne générique du middleware : le journal
    # doit dire QUEL OF a été créé et sur quelles commandes, sans quoi il faut
    # rouvrir la base pour comprendre une entrée.
    log_action(
        user=user, action="CREATE", module="of",
        objet="OF %s · %s" % (numero, champs.get("reference") or ""),
        detail={"source": "mysifa",
                "commandes": [l["numero"] for l in commandes],
                "dossiers_relies": linked},
        request=request,
    )

    return {
        "created": True, "id": of_id, "of_numero": numero,
        "rattachement": rattachement, "linked_entries": linked,
    }


@router.post("/api/fiches-techniques")
async def create_fiche(request: Request):
    """Crée une fiche technique dans MySifa.

    La référence porte le lien vers l'ERP : « 1026/0020 » est le couple
    code1/code2 d'un article de RVGI. On le résout à la création et on le
    STOCKE — le redeviner à chaque lecture ferait glisser une fiche d'un
    article à l'autre au premier renommage.
    """
    user = _require_of_access(request)
    body = await request.json()

    reference = str(body.get("reference") or "").strip()
    if not reference:
        raise HTTPException(status_code=400, detail="Référence obligatoire.")

    EDITABLES = {
        "reference", "designation", "client", "format",
        "eti_laize", "eti_longueur", "eti_rayons", "eti_perforations",
        "mod_laize", "mod_longueur", "mod_nb_front",
        "lateral_ext", "horizontal", "lateral_int",
        "support", "matiere", "glassine", "laize_optimale", "laize_optionnelle",
        "epaisseur", "adhesif", "qte_au_mille",
        "machine", "nb_couleurs", "recto", "verso",
        "outil1_forme", "outil1_numero_sifa", "outil1_laize", "outil1_epaisseur",
        "outil1_nb_dents", "outil1_nb_front", "outil1_nb_avance",
        "outil2_forme", "outil2_numero_sifa", "outil2_epaisseur",
        "outil2_nb_dents", "outil2_nb_front", "outil2_nb_avance",
        "outil3_forme", "outil3_numero_sifa", "outil3_epaisseur",
        "outil3_nb_dents", "outil3_nb_front", "outil3_nb_avance",
        "tete1_pantone", "tete1_couleur", "tete1_anilox", "tete1_composition",
        "tete2_pantone", "tete2_couleur", "tete2_anilox", "tete2_composition",
        "tete3_pantone", "tete3_couleur", "tete3_anilox", "tete3_composition",
        "remarque", "mandrin_dia", "mandrin_longueur", "enroulement",
        "nb_etiq_bobin", "dia_ext", "poids", "conditionnement", "cales_sachets",
        "cartons", "nb_au_sol", "nb_etage", "nb_bobines_carton",
        "palette_type", "palette_nb_cartons_sol", "palette_nb_cartons_hauteur",
        "palette_hauteur_max", "particularite", "notes", "grammage",
        "article_code1", "article_code2", "article_libelle",
        "support_ref_id", "glassine_ref_id", "adhesif_ref_id",
        "carton_ref_id", "mandrin_ref_id", "palette_ref_id",
    }
    champs = {k: v for k, v in body.items() if k in EDITABLES}
    champs["reference"] = reference

    # Résolution de l'article : ce que l'écran a explicitement choisi prime,
    # sinon la référence elle-même le désigne.
    if not champs.get("article_code1"):
        couple = ratt.couper_reference(reference)
        if couple:
            champs["article_code1"], champs["article_code2"] = couple

    maintenant = _now_paris_iso()
    qui = (user.get("nom") or user.get("email") or "").strip() or None

    with get_db() as conn:
        _appliquer_references(conn, champs, REFERENCES_FT)
        double = conn.execute(
            "SELECT id FROM fiches_techniques "
            "WHERE LOWER(TRIM(reference)) = LOWER(TRIM(?))",
            (reference,),
        ).fetchone()
        if double:
            raise HTTPException(
                status_code=409,
                detail="Une fiche technique existe déjà pour %s (#%d). "
                       "Modifiez-la plutôt que d'en créer une seconde."
                       % (reference, double["id"]),
            )

        colonnes = list(champs.keys()) + [
            "source", "valide", "cree_par", "cree_le", "date_import", "imported_by",
        ]
        valeurs = list(champs.values()) + [
            "mysifa", 0, qui, maintenant, maintenant, qui,
        ]
        cur = conn.execute(
            "INSERT INTO fiches_techniques (%s) VALUES (%s)"
            % (", ".join(colonnes), ", ".join("?" * len(colonnes))),
            valeurs,
        )
        fiche_id = cur.lastrowid
        marquer_champs_manuels(
            conn, "fiches_techniques", fiche_id, _valeurs_non_vides(champs),
        )
        conn.commit()

    log_action(
        user=user, action="CREATE", module="of",
        objet="Fiche technique %s" % reference,
        detail={"source": "mysifa",
                "article": ("%s/%s" % (champs.get("article_code1"),
                                       champs.get("article_code2"))
                            if champs.get("article_code1") else None)},
        request=request,
    )

    return {"created": True, "id": fiche_id, "reference": reference,
            "article_code1": champs.get("article_code1"),
            "article_code2": champs.get("article_code2")}


def _date_iso(valeur) -> Optional[str]:
    """« 08/06/2026 » → « 2026-06-08 ». Rend None sur tout le reste.

    Le planning stocke des dates ISO ; l'OF les porte au format français.
    Convertir ici évite qu'une date de livraison arrive au planning sous une
    forme qu'il trie comme du texte.
    """
    brut = str(valeur or "").strip()
    if not brut:
        return None
    for sep in ("/", "-", "."):
        morceaux = brut.split(sep)
        if len(morceaux) == 3 and len(morceaux[0]) <= 2:
            j, m, a = (x.strip() for x in morceaux)
            if j.isdigit() and m.isdigit() and a.isdigit():
                if len(a) == 2:
                    a = "20" + a
                return "%s-%02d-%02d" % (a, int(m), int(j))
    if len(brut) >= 10 and brut[4] == "-" and brut[7] == "-":
        return brut[:10]
    return None


def _format_lh(valeur) -> tuple:
    """« 85 x 51 mm » → (85.0, 51.0)."""
    brut = str(valeur or "").lower().replace("mm", "").strip()
    for sep in ("x", "×", "*"):
        if sep in brut:
            g, _, d = brut.partition(sep)
            try:
                return (float(g.strip().replace(",", ".")),
                        float(d.strip().replace(",", ".")))
            except ValueError:
                return (None, None)
    return (None, None)


@router.get("/api/of/{of_id}/dossier-prefill")
def of_dossier_prefill(of_id: int, request: Request):
    """Ce qu'il faut pour ouvrir la modale « nouveau dossier » déjà remplie.

    Le bouton « Créer directement un dossier de prod » n'écrit rien : il ouvre
    la modale du planning avec ces valeurs. C'est un choix, pas une limitation
    — la machine, la place dans la file et la durée sont des arbitrages de
    planification que l'OF ne porte pas, et un dossier posé en silence au
    mauvais endroit coûte plus cher que deux clics.

    La référence du dossier suit la même règle que partout : elle se propose
    depuis les commandes rattachées, et devient « Reliquat … » si l'une de ces
    lignes a déjà porté une production.
    """
    _require_of_access(request)
    with get_db() as conn:
        of = conn.execute("SELECT * FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not of:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        of = dict(of)

        lignes = [l for l in ratt.lister(conn, "of", of_id) if l["piece"] == "commande"]
        reference = ""
        if lignes:
            reference = ratt.proposer_reference(
                lignes, reliquat=ratt.deja_couvertes(conn, lignes, "commande"),
            )
        reference = reference or (of.get("of_numero") or "")

        fiche = None
        ref_produit = str(of.get("reference") or "").split(" - ")[0].strip()
        if ref_produit:
            fiche = conn.execute(
                "SELECT * FROM fiches_techniques "
                "WHERE LOWER(TRIM(reference)) = LOWER(TRIM(?)) "
                "   OR LOWER(TRIM(reference)) LIKE LOWER(TRIM(?) || ' - %') "
                "ORDER BY id LIMIT 1",
                (of.get("reference") or "", ref_produit),
            ).fetchone()
            fiche = dict(fiche) if fiche else None

        machine_id = None
        nom_machine = (of.get("machine") or "").strip()
        if nom_machine:
            m = conn.execute(
                "SELECT id FROM machines WHERE LOWER(TRIM(nom)) = LOWER(TRIM(?))",
                (nom_machine,),
            ).fetchone()
            machine_id = m["id"] if m else None

    largeur, hauteur = _format_lh(of.get("format"))
    client = next((l["vu_client"] for l in lignes if l.get("vu_client")), None)
    if not client and fiche:
        client = fiche.get("client")

    # Étiquettes par carton : le produit de deux valeurs de la fiche. On ne la
    # propose que si les DEUX sont là — un carton « de 1 000 » déduit d'une
    # moitié de fiche serait pris pour un chiffre vérifié.
    etiq_carton = None
    if fiche and fiche.get("nb_etiq_bobin") and fiche.get("nb_bobines_carton"):
        try:
            etiq_carton = int(fiche["nb_etiq_bobin"]) * int(fiche["nb_bobines_carton"])
        except (TypeError, ValueError):
            etiq_carton = None

    return {
        "of_id": of_id,
        "machine_id": machine_id,
        "machine": nom_machine or None,
        "fiche_id": (fiche.get("id") if fiche else None),
        "dossier": {
            "reference": reference,
            "numero_of": of.get("of_numero"),
            "ref_produit": ref_produit or None,
            "client": client or "",
            "description": (fiche.get("designation") if fiche else None) or "",
            "format_l": largeur,
            "format_h": hauteur,
            "laize": of.get("laize"),
            "date_livraison": _date_iso(of.get("delai_client")),
            "commentaire": of.get("particularites") or "",
            "etiquettes_par_carton": etiq_carton,
            "a_placer": 1,
        },
        # Les mêmes lignes seront rattachées au dossier créé : c'est ce qui
        # fait tenir la chaîne commande → OF → dossier sans ressaisie.
        "commandes": [
            {"numero": l["numero"], "ligne": l["ligne"], "qte": l["qte"],
             "vu_qte": l["vu_qte"], "vu_article": l["vu_article"],
             "vu_client": l["vu_client"],
             "confirme": (l["etat"] == "confirme")}
            for l in lignes
        ],
    }


@router.get("/api/of/{of_id}")
def get_of_import(of_id: int, request: Request):
    """La ligne COMPLÈTE d'un OF, pour ouvrir la modale de modification.

    Pourquoi cette route existe. `/api/of/list` ne renvoie que la vingtaine de
    colonnes du tableau — la modale, elle, poste les quarante-deux champs de
    l'OF. Ouverte sur une ligne de liste, elle affichait donc vides les vingt
    autres (laize, glassine, réf. adhésif, outillage, tolérance…), et
    « Enregistrer » les écrivait à NULL : `autoriser_effacement=True` traite un
    champ vidé comme une décision humaine, ce qu'il est — quand le champ a
    réellement été montré à un humain.

    La modale charge donc l'OF entier avant de s'ouvrir. Ne pas la faire
    revenir sur la ligne de liste.
    """
    _require_of_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        of = _row_dict(row)
        of["commandes"] = [
            l for l in ratt.lister(conn, "of", of_id) if l["piece"] == "commande"
        ]
    return of
