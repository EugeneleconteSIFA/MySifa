"""
SIFA — Rentabilité v1.0
Import devis, liaison dossiers, comparaison théorique/réel.
Accès : direction + administration uniquement.

Lecture d'un devis : `app/services/devis_extraction.py`. Le parser à motifs
traite le modèle maison, l'IA prend le relais dès qu'un champ clé manque ou
que le fichier n'est pas un classeur. Rien n'entre en base sans passer par
l'écran de validation de MyProd : ces routes proposent, elles n'enregistrent
que ce qu'un humain a confirmé.
"""
import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Request, UploadFile, File, HTTPException

from database import get_db
from services.auth_service import get_current_user
from app.services.devis_extraction import extraire_devis
from app.services.dossier_stats import build_dossier_production_stats
from config import (
    DEVIS_EXTENSIONS_ACCEPTEES,
    DEVIS_MAX_FILE_MB,
    DEVIS_UPLOAD_DIR,
    ROLES_ADMIN,
)

router = APIRouter()


def require_rentabilite(request: Request) -> dict:
    """Direction et Administration uniquement."""
    user = get_current_user(request)
    if user["role"] not in ROLES_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à la Direction et l'Administration"
        )
    return user


def _reel_depuis_saisies(conn, no_dossiers: list[str]) -> dict:
    """Le réel d'un devis, calculé par `build_dossier_production_stats`.

    Pourquoi ne pas refaire le SQL ici. Ce module additionnait `metrage_reel`,
    qui n'est pas un métrage produit mais un RELEVÉ DE COMPTEUR machine : sur
    le dossier 9932259, la somme sortait 561 152 286 m là où le dossier en a
    produit 154 701. Le métrage se lit en écart de compteur entre le 01 et le
    89 d'un même cycle — c'est ce que fait `dossier_stats`, et c'est ce que
    lisent les opérateurs dans MyProd.

    La règle produit est qu'un dossier n'a qu'un chiffre : Rentabilité ne
    recalcule donc plus rien, elle appelle le code de l'écran de référence.
    Les temps suivent le même chemin, pour la même raison.
    """
    vide = {"metrage_ml": 0.0, "qte_etiquettes": 0.0, "temps_calage_mn": 0.0,
            "temps_production_mn": 0.0, "temps_arret_mn": 0.0}
    if not no_dossiers:
        return dict(vide)

    placeholders = ",".join("?" * len(no_dossiers))
    lignes = [
        dict(r) for r in conn.execute(
            f"""SELECT * FROM production_data
                WHERE no_dossier IN ({placeholders})
                  AND COALESCE(est_annule, 0) = 0""",
            no_dossiers,
        ).fetchall()
    ]

    total = dict(vide)
    for dos in no_dossiers:
        st = build_dossier_production_stats(lignes, dos)
        q, t = st["quantites"], st["temps_totaux"]
        total["metrage_ml"] += float(q.get("metrage_m") or 0)
        total["qte_etiquettes"] += float(q.get("etiquettes") or 0)
        total["temps_calage_mn"] += float(t.get("calage_min") or 0)
        total["temps_production_mn"] += float(t.get("production_min") or 0)
        total["temps_arret_mn"] += float(t.get("arret_min") or 0)
    return total


def _colonne(row, nom: str, defaut: float = 0.0) -> float:
    """Lit une colonne qui peut ne pas exister encore.

    `sqlite3.Row` n'a pas de `.get()` et lève `IndexError` sur une colonne
    absente : une base où la migration n'est pas encore passée casserait la
    comparaison au lieu de la rendre approximative.
    """
    try:
        v = row[nom]
    except (IndexError, KeyError):
        return defaut
    try:
        return float(v) if v is not None else defaut
    except (TypeError, ValueError):
        return defaut


def _calage_theorique(devis_row) -> float:
    """Le calage devisé, tous postes confondus — outil + impression."""
    return (_colonne(devis_row, "temps_calage_mn")
            + _colonne(devis_row, "temps_calage_impression_mn"))


def _comparaison_from_no_dossiers(conn, devis_row, no_dossiers: list[str]) -> dict:
    """Calcule la comparaison devis vs réel pour une liste de no_dossier (production_data)."""
    d = devis_row
    no_dossiers = [str(x).strip() for x in (no_dossiers or []) if str(x or "").strip()]
    if not no_dossiers:
        return {"devis": dict(d), "reel": None, "message": "Aucun dossier lié"}

    reel_saisies = _reel_depuis_saisies(conn, no_dossiers)
    qte_reel = reel_saisies["qte_etiquettes"]
    metrage_reel = reel_saisies["metrage_ml"]
    tps_calage_reel = reel_saisies["temps_calage_mn"]
    tps_prod_reel = reel_saisies["temps_production_mn"]
    tps_arret_reel = reel_saisies["temps_arret_mn"]

    # Vitesse sur production + arret, comme MyProd : une machine arretee au
    # milieu d'un dossier a bien produit ce metrage dans ce temps-la.
    denom_vitesse = tps_prod_reel + tps_arret_reel
    vitesse_reel = (metrage_reel / denom_vitesse) if denom_vitesse > 0 else 0
    tps_total_reel = tps_calage_reel + denom_vitesse
    vitesse_avec_calage = (metrage_reel / tps_total_reel) if tps_total_reel > 0 else 0

    # LE CALAGE DEVISÉ EST LA SOMME DE DEUX POSTES.
    # Le devis sépare le calage outil (montage de l'outil de découpe) du calage
    # impression (mises en route couleurs et clichés). MyProd, lui, ne les
    # sépare pas : `dossier_stats` range dans la catégorie « calage » aussi
    # bien l'opération 02 que les 12 (changement de couleur) et 75 (changement
    # de cliché), qui SONT le calage impression. Comparer le calage relevé au
    # seul poste outil opposait donc deux périmètres différents — sur un devis
    # à 150 mn d'outil et 450 mn d'impression, l'écart affiché était faux d'un
    # facteur 4, sans qu'aucun chiffre soit inexact.
    tps_calage_theo = _calage_theorique(d)
    metrage_calage_theo = _colonne(d, "metrage_calage_ml") + _colonne(d, "metrage_calage_impression_ml")

    tps_total_theo = tps_calage_theo + (d["temps_production_mn"] or 0)
    vitesse_theo_avec_calage = ((d["metrage_production_ml"] or 0) / tps_total_theo) if tps_total_theo > 0 else 0

    def pct_diff(reel, theo):
        if theo and theo != 0:
            return round((reel - theo) / theo * 100, 1)
        return None

    def fmt_pct(v):
        if v is None:
            return None
        return f"+{v}%" if v > 0 else f"{v}%"

    reel = {
        "temps_calage_mn":      round(tps_calage_reel, 1),
        "temps_production_mn":  round(tps_prod_reel, 1),
        "temps_arret_mn":       round(tps_arret_reel, 1),
        "metrage_ml":           round(metrage_reel, 1),
        "qte_etiquettes":       round(qte_reel, 0),
        "vitesse":              round(vitesse_reel, 2),
        "vitesse_avec_calage":  round(vitesse_avec_calage, 2),
    }

    theo = {
        "temps_calage_mn":      round(tps_calage_theo, 1),
        # Le détail des deux postes reste exposé : l'écran doit pouvoir dire
        # d'où vient le total, sans quoi un utilisateur qui ouvre le classeur
        # ne retrouve pas le chiffre affiché.
        "temps_calage_outil_mn":      _colonne(d, "temps_calage_mn"),
        "temps_calage_impression_mn": _colonne(d, "temps_calage_impression_mn"),
        "metrage_calage_ml":    round(metrage_calage_theo, 1),
        "temps_production_mn":  d["temps_production_mn"],
        "metrage_ml":           d["metrage_production_ml"],
        "qte_etiquettes":       d["qte_etiquettes"],
        "vitesse":              d["vitesse_theorique"],
        "vitesse_avec_calage":  round(vitesse_theo_avec_calage, 2),
    }

    ecarts = {
        "temps_calage_mn":      fmt_pct(pct_diff(reel["temps_calage_mn"],     theo["temps_calage_mn"])),
        "temps_production_mn":  fmt_pct(pct_diff(reel["temps_production_mn"], theo["temps_production_mn"])),
        "metrage_ml":           fmt_pct(pct_diff(reel["metrage_ml"],           theo["metrage_ml"])),
        "qte_etiquettes":       fmt_pct(pct_diff(reel["qte_etiquettes"],       theo["qte_etiquettes"])),
        "vitesse":              fmt_pct(pct_diff(reel["vitesse"],              theo["vitesse"])),
        "vitesse_avec_calage":  fmt_pct(pct_diff(reel["vitesse_avec_calage"],  theo["vitesse_avec_calage"])),
    }

    score = 0
    if reel["vitesse"] > (theo["vitesse"] or 0):
        score += 1
    if reel["temps_calage_mn"] < (theo["temps_calage_mn"] or 999):
        score += 1
    if reel["qte_etiquettes"] >= (theo["qte_etiquettes"] or 0):
        score += 1

    if score == 3:
        conclusion = {"label": "Excellent", "color": "success"}
    elif score == 2:
        conclusion = {"label": "Bon",        "color": "success"}
    elif score == 1:
        conclusion = {"label": "Mitigé",     "color": "warn"}
    else:
        conclusion = {"label": "À améliorer", "color": "danger"}

    return {
        "devis":      dict(d),
        "dossiers":   no_dossiers,
        "theorique":  theo,
        "reel":       reel,
        "ecarts":     ecarts,
        "conclusion": conclusion,
        "avertissements": _avertissements_comparaison(theo, reel),
    }


# Au-delà de cet écart entre la quantité produite et la quantité devisée, les
# deux ne décrivent plus la même affaire et la comparaison perd son sens.
ECART_QUANTITE_ALERTE = 0.10


def _milliers(n) -> str:
    """14400000 → « 14 400 000 ».

    Formater d'abord PUIS remplacer sur toute la phrase supprimait aussi les
    virgules de ponctuation : « 29 000 000 étiquettes  le devis en chiffrait ».
    Le remplacement doit rester enfermé dans le nombre.
    """
    try:
        return f"{float(n):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def _avertissements_comparaison(theo: dict, reel: dict) -> list[dict]:
    """Ce qui rend la comparaison trompeuse, dit avant qu'on la lise.

    Un devis chiffre plusieurs quantités mais ne calcule les temps que pour
    une seule. Si le dossier lié a produit une quantité très différente, les
    écarts affichés ne mesurent pas une performance d'atelier : ils mesurent
    l'écart entre deux commandes. Mieux vaut le dire que laisser conclure.
    """
    avertissements: list[dict] = []
    qte_theo = float(theo.get("qte_etiquettes") or 0)
    qte_reel = float(reel.get("qte_etiquettes") or 0)
    if qte_theo > 0 and qte_reel > 0:
        ecart = abs(qte_reel - qte_theo) / qte_theo
        if ecart > ECART_QUANTITE_ALERTE:
            avertissements.append({
                "niveau": "avertissement",
                "message": (
                    f"Le dossier a produit {_milliers(qte_reel)} étiquettes, le devis "
                    f"en chiffrait {_milliers(qte_theo)} — {ecart * 100:.0f} % d'écart. "
                    "Les temps devisés valent pour la quantité du devis : les "
                    "écarts ci-dessous comparent deux volumes différents."
                ),
            })

    impr = float(theo.get("temps_calage_impression_mn") or 0)
    if impr > 0:
        outil = float(theo.get("temps_calage_outil_mn") or 0)
        avertissements.append({
            "niveau": "info",
            "message": (
                f"Calage devisé = {_milliers(outil)} mn d'outil + {_milliers(impr)} mn "
                "d'impression. Le calage relevé en atelier couvre les deux "
                "(changements de couleur et de cliché compris)."
            ),
        })
    return avertissements


# ── Rentabilité v2 (Planning-based) ───────────────────────────────
@router.get("/api/rentabilite/planning-entries")
def list_planning_entries(request: Request):
    """Liste toutes les entrées planning (toutes machines) pour la vue Rentabilité."""
    require_rentabilite(request)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
              e.*,
              m.nom AS machine_nom,
              m.code AS machine_code
            FROM planning_entries e
            JOIN machines m ON m.id = e.machine_id
            WHERE m.actif = 1
            ORDER BY m.nom ASC, e.position ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/rentabilite/links/{planning_entry_id}")
def get_links(planning_entry_id: int, request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_entry_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée planning introuvable")
        link = conn.execute(
            "SELECT devis_id, updated_at FROM rent_links WHERE planning_entry_id=?",
            (planning_entry_id,),
        ).fetchone()
        prod = conn.execute(
            "SELECT no_dossier FROM rent_prod_links WHERE planning_entry_id=? ORDER BY no_dossier",
            (planning_entry_id,),
        ).fetchall()
    return {
        "planning_entry_id": planning_entry_id,
        "devis_id": (link["devis_id"] if link else None),
        "updated_at": (link["updated_at"] if link else None),
        "no_dossiers": [r["no_dossier"] for r in prod],
    }


@router.put("/api/rentabilite/links/{planning_entry_id}")
async def put_links(planning_entry_id: int, request: Request):
    require_rentabilite(request)
    body = await request.json()
    devis_id = body.get("devis_id")
    no_dossiers = body.get("no_dossiers") or []
    no_dossiers = [str(x).strip() for x in no_dossiers if str(x or "").strip()]

    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_entry_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée planning introuvable")
        if devis_id is not None:
            dv = conn.execute("SELECT id FROM devis WHERE id=?", (int(devis_id),)).fetchone()
            if not dv:
                raise HTTPException(404, "Devis introuvable")

        conn.execute(
            """INSERT INTO rent_links (planning_entry_id, devis_id, updated_at)
               VALUES (?,?,?)
               ON CONFLICT(planning_entry_id) DO UPDATE
                 SET devis_id=excluded.devis_id, updated_at=excluded.updated_at""",
            (planning_entry_id, int(devis_id) if devis_id is not None else None, now),
        )
        conn.execute("DELETE FROM rent_prod_links WHERE planning_entry_id=?", (planning_entry_id,))
        for dos in no_dossiers:
            conn.execute(
                "INSERT OR IGNORE INTO rent_prod_links (planning_entry_id, no_dossier) VALUES (?,?)",
                (planning_entry_id, dos),
            )
        conn.commit()
    return {"success": True}


@router.get("/api/rentabilite/planning/{planning_entry_id}/comparaison")
def comparaison_for_planning(planning_entry_id: int, request: Request):
    """Comparaison basée sur le devis lié + les no_dossier liés à une entrée planning."""
    require_rentabilite(request)
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_entry_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée planning introuvable")
        link = conn.execute(
            "SELECT devis_id FROM rent_links WHERE planning_entry_id=?",
            (planning_entry_id,),
        ).fetchone()
        if not link or not link["devis_id"]:
            return {"devis": None, "reel": None, "message": "Aucun devis lié"}
        d = conn.execute("SELECT * FROM devis WHERE id=?", (int(link["devis_id"]),)).fetchone()
        if not d:
            raise HTTPException(404, "Devis introuvable")
        prod = conn.execute(
            "SELECT no_dossier FROM rent_prod_links WHERE planning_entry_id=?",
            (planning_entry_id,),
        ).fetchall()
        no_dossiers = [r["no_dossier"] for r in prod]
        return _comparaison_from_no_dossiers(conn, d, no_dossiers)


@router.get("/api/rentabilite/no-dossiers")
def suggest_no_dossiers(request: Request, q: str = "", limit: int = 12):
    """Suggestions no_dossier depuis production_data (pour autocomplétion)."""
    require_rentabilite(request)
    qn = str(q or "").strip()
    try:
        lim = max(1, min(int(limit), 50))
    except Exception:
        lim = 12
    with get_db() as conn:
        if qn:
            rows = conn.execute(
                """
                SELECT DISTINCT no_dossier
                FROM production_data
                WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                  AND LOWER(no_dossier) LIKE LOWER(?)
                ORDER BY no_dossier
                LIMIT ?
                """,
                (f"%{qn}%", lim),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT no_dossier
                FROM production_data
                WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                ORDER BY no_dossier
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
    return [r["no_dossier"] for r in rows]

# ── Import d'un devis ─────────────────────────────────────────────
def _extension(filename: str) -> str:
    return (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""


def _conserver_fichier(contents: bytes, filename: str) -> str:
    """Range le devis d'origine et rend son chemin relatif.

    Le nom est généré ici : rien de ce que l'utilisateur envoie n'entre dans
    le chemin, sauf l'extension, déjà validée contre une liste blanche.
    """
    try:
        os.makedirs(DEVIS_UPLOAD_DIR, exist_ok=True)
        ext = _extension(filename) or "bin"
        nom = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        with open(os.path.join(DEVIS_UPLOAD_DIR, nom), "wb") as f:
            f.write(contents)
        return nom
    except Exception:
        # Conserver le fichier est un confort d'audit, pas une condition de
        # l'import : un disque plein ne doit pas bloquer une lecture de devis.
        return ""


@router.post("/api/rentabilite/devis/import")
async def import_devis(request: Request, file: UploadFile = File(...),
                       forcer_ia: int = 0):
    """Lit un devis et rend une PROPOSITION — aucun enregistrement ici.

    `forcer_ia=1` redemande une lecture au modèle alors même que le parser a
    trouvé les champs clés : c'est le bouton « Relire avec l'IA » de l'écran
    de validation, quand il manque un indicateur secondaire.
    """
    require_rentabilite(request)
    contents = await file.read()
    filename = file.filename or "devis.xlsx"

    ext = _extension(filename)
    if ext not in DEVIS_EXTENSIONS_ACCEPTEES:
        raise HTTPException(
            400,
            "Format non accepté — formats lus : "
            + ", ".join(DEVIS_EXTENSIONS_ACCEPTEES) + ".",
        )
    if len(contents) > DEVIS_MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(
            400, f"Fichier trop volumineux — {DEVIS_MAX_FILE_MB} Mo maximum."
        )

    resultat = extraire_devis(
        contents, filename,
        content_type=(file.content_type or ""),
        forcer_ia=bool(forcer_ia),
    )
    resultat["fichier_chemin"] = _conserver_fichier(contents, filename)
    resultat["fichier_mime"] = file.content_type or ""
    return resultat


# ── Valider et sauvegarder un devis ──────────────────────────────
@router.post("/api/rentabilite/devis")
async def create_devis(request: Request):
    user = require_rentabilite(request)
    body = await request.json()

    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO devis
               (filename, client, date_devis, format_h, format_v, laize, nb_couleurs,
                temps_calage_mn, metrage_calage_ml, temps_production_mn,
                metrage_production_ml, vitesse_theorique, qte_etiquettes, gache,
                statut, note, imported_at, imported_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                body.get("filename", ""),
                body.get("client", ""),
                body.get("date_devis", ""),
                body.get("format_h", 0),
                body.get("format_v", 0),
                body.get("laize", 0),
                body.get("nb_couleurs", 0),
                body.get("temps_calage_mn", 0),
                body.get("metrage_calage_ml", 0),
                body.get("temps_production_mn", 0),
                body.get("metrage_production_ml", 0),
                body.get("vitesse_theorique", 0),
                body.get("qte_etiquettes", 0),
                body.get("gache", 0),
                "en_attente",
                body.get("note", ""),
                now,
                user["email"],
            )
        )
        devis_id = cursor.lastrowid

        # Le calage impression vit dans des colonnes ajoutées par migration :
        # écriture séparée, pour qu'une base pas encore migrée enregistre
        # quand même le devis au lieu de refuser l'import.
        cols_avant = {r[1] for r in conn.execute("PRAGMA table_info(devis)").fetchall()}
        if "temps_calage_impression_mn" in cols_avant:
            conn.execute(
                """UPDATE devis SET temps_calage_impression_mn=?,
                          metrage_calage_impression_ml=? WHERE id=?""",
                (
                    body.get("temps_calage_impression_mn", 0) or 0,
                    body.get("metrage_calage_impression_ml", 0) or 0,
                    devis_id,
                ),
            )

        # Traçabilité de la lecture. `extraction_json` garde, champ par champ,
        # la source et la confiance affichées au moment de la validation :
        # c'est ce qui permet, des mois après, de rouvrir la bonne cellule
        # plutôt que de rejouer une extraction avec un modèle qui a changé.
        cols_devis = {r[1] for r in conn.execute("PRAGMA table_info(devis)").fetchall()}
        if "extraction_methode" in cols_devis:
            conn.execute(
                """UPDATE devis SET extraction_methode=?, extraction_modele=?,
                          extraction_json=?, coherence_json=?,
                          fichier_chemin=?, fichier_mime=?,
                          valide_par=?, valide_at=?
                   WHERE id=?""",
                (
                    body.get("extraction_methode") or "manuel",
                    body.get("extraction_modele") or "",
                    json.dumps(body.get("champs") or {}, ensure_ascii=False),
                    json.dumps(body.get("coherence") or [], ensure_ascii=False),
                    body.get("fichier_chemin") or "",
                    body.get("fichier_mime") or "",
                    user["email"],
                    now,
                    devis_id,
                ),
            )

        _remplacer_indicateurs(conn, devis_id, body.get("indicateurs") or [], now)
        conn.commit()
    return {"success": True, "devis_id": devis_id}


def _remplacer_indicateurs(conn, devis_id: int, indicateurs: list, now: str) -> int:
    """Pose les indicateurs hors socle validés pour ce devis.

    Remplacement complet plutôt qu'ajout : rejouer un import corrige les
    valeurs au lieu d'empiler deux versions du même libellé.
    """
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "devis_indicateurs" not in tables:
        return 0

    conn.execute("DELETE FROM devis_indicateurs WHERE devis_id=?", (devis_id,))
    poses = 0
    for ind in indicateurs:
        libelle = str((ind or {}).get("libelle") or "").strip()
        if not libelle:
            continue
        valeur_nombre = ind.get("valeur_nombre")
        try:
            valeur_nombre = float(valeur_nombre) if valeur_nombre is not None else None
        except (TypeError, ValueError):
            valeur_nombre = None
        conn.execute(
            """INSERT OR REPLACE INTO devis_indicateurs
               (devis_id, libelle, valeur_nombre, valeur_texte, unite,
                source, confiance, origine, cree_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                devis_id, libelle, valeur_nombre,
                str(ind.get("valeur_texte") or ""),
                str(ind.get("unite") or ""),
                str(ind.get("source") or ""),
                str(ind.get("confiance") or ""),
                str(ind.get("origine") or "ia"),
                now,
            ),
        )
        poses += 1
    return poses


# ── Indicateurs hors socle d'un devis ─────────────────────────────
@router.get("/api/rentabilite/devis/{devis_id}/indicateurs")
def get_indicateurs(devis_id: int, request: Request):
    """Les indicateurs du devis que le socle comparable ne prévoit pas."""
    require_rentabilite(request)
    with get_db() as conn:
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "devis_indicateurs" not in tables:
            return []
        rows = conn.execute(
            "SELECT * FROM devis_indicateurs WHERE devis_id=? ORDER BY libelle",
            (devis_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Liste des devis ───────────────────────────────────────────────
@router.get("/api/rentabilite/devis")
def list_devis(request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.*,
                      COUNT(dd.id) as nb_dossiers_lies
               FROM devis d
               LEFT JOIN devis_dossiers dd ON dd.devis_id=d.id
               GROUP BY d.id
               ORDER BY d.imported_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


# ── Détail d'un devis ─────────────────────────────────────────────
@router.get("/api/rentabilite/devis/{devis_id}")
def get_devis(devis_id: int, request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        d = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Devis non trouvé")
        dossiers = conn.execute(
            "SELECT no_dossier FROM devis_dossiers WHERE devis_id=?", (devis_id,)
        ).fetchall()
    return {**dict(d), "dossiers_lies": [r["no_dossier"] for r in dossiers]}


# ── Modifier un devis ─────────────────────────────────────────────
@router.put("/api/rentabilite/devis/{devis_id}")
async def update_devis(devis_id: int, request: Request):
    require_rentabilite(request)
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Devis non trouvé")
        conn.execute(
            """UPDATE devis SET client=?,date_devis=?,format_h=?,format_v=?,laize=?,
               nb_couleurs=?,temps_calage_mn=?,metrage_calage_ml=?,temps_production_mn=?,
               metrage_production_ml=?,vitesse_theorique=?,qte_etiquettes=?,gache=?,note=?
               WHERE id=?""",
            (
                body.get("client", ex["client"]),
                body.get("date_devis", ex["date_devis"]),
                body.get("format_h", ex["format_h"]),
                body.get("format_v", ex["format_v"]),
                body.get("laize", ex["laize"]),
                body.get("nb_couleurs", ex["nb_couleurs"]),
                body.get("temps_calage_mn", ex["temps_calage_mn"]),
                body.get("metrage_calage_ml", ex["metrage_calage_ml"]),
                body.get("temps_production_mn", ex["temps_production_mn"]),
                body.get("metrage_production_ml", ex["metrage_production_ml"]),
                body.get("vitesse_theorique", ex["vitesse_theorique"]),
                body.get("qte_etiquettes", ex["qte_etiquettes"]),
                body.get("gache", ex["gache"]),
                body.get("note", ex["note"]),
                devis_id,
            )
        )
        # Colonnes ajoutées par migration : modifiées à part, pour ne pas faire
        # échouer l'édition sur une base qui ne les a pas encore.
        cols_devis = {r[1] for r in conn.execute("PRAGMA table_info(devis)").fetchall()}
        if "temps_calage_impression_mn" in cols_devis:
            conn.execute(
                """UPDATE devis SET temps_calage_impression_mn=?,
                          metrage_calage_impression_ml=? WHERE id=?""",
                (
                    body.get("temps_calage_impression_mn",
                             _colonne(ex, "temps_calage_impression_mn")),
                    body.get("metrage_calage_impression_ml",
                             _colonne(ex, "metrage_calage_impression_ml")),
                    devis_id,
                ),
            )
        conn.commit()
    return {"success": True}


# ── Supprimer un devis ────────────────────────────────────────────
@router.delete("/api/rentabilite/devis/{devis_id}")
def delete_devis(devis_id: int, request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        conn.execute("DELETE FROM devis_dossiers WHERE devis_id=?", (devis_id,))
        conn.execute("DELETE FROM devis WHERE id=?", (devis_id,))
        conn.commit()
    return {"success": True}


# ── Lier des dossiers à un devis ──────────────────────────────────
@router.put("/api/rentabilite/devis/{devis_id}/dossiers")
async def link_dossiers(devis_id: int, request: Request):
    require_rentabilite(request)
    body = await request.json()
    no_dossiers = body.get("dossiers", [])

    with get_db() as conn:
        ex = conn.execute("SELECT id FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Devis non trouvé")
        conn.execute("DELETE FROM devis_dossiers WHERE devis_id=?", (devis_id,))
        for dos in no_dossiers:
            if dos:
                conn.execute(
                    "INSERT INTO devis_dossiers (devis_id, no_dossier) VALUES (?,?)",
                    (devis_id, str(dos).strip()),
                )
        statut = "lie" if no_dossiers else "en_attente"
        conn.execute("UPDATE devis SET statut=? WHERE id=?", (statut, devis_id))
        conn.commit()
    return {"success": True}


# ── Calcul rentabilité devis vs réel ─────────────────────────────
@router.get("/api/rentabilite/devis/{devis_id}/comparaison")
def comparaison(devis_id: int, request: Request):
    """Comparaison devis vs réel.

    Le corps de cette route était une copie mot pour mot de
    `_comparaison_from_no_dossiers` : deux copies, c'est deux corrections à
    faire et une à oublier. C'est précisément ce qui est arrivé au métrage.
    """
    require_rentabilite(request)

    with get_db() as conn:
        d = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Devis non trouvé")

        no_dossiers = [
            r["no_dossier"] for r in conn.execute(
                "SELECT no_dossier FROM devis_dossiers WHERE devis_id=?", (devis_id,)
            ).fetchall()
        ]
        if not no_dossiers:
            return {"devis": dict(d), "reel": None,
                    "message": "Aucun dossier lié à ce devis"}

        return _comparaison_from_no_dossiers(conn, d, no_dossiers)
