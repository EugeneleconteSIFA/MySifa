"""
MyStock — Besoins matières
==========================

Calcule les besoins en matières premières à partir des dossiers de production
au planning (statut 'attente' ou 'en_cours'). S'appuie sur :

- `planning_entries` : les dossiers, avec dates prévues (planned_start/end,
  date_livraison) et lien vers `of_imports` (qte_etiquettes à produire).
- `fiches_techniques` : jointes via `ref_produit_norm` avec tie-breaker
  machine — même logique que `app/routers/planning.py` (l. 3238+).
- `mp_fiche_mapping` (v215) : table de correspondance éditable entre les
  champs texte des fiches (support, adhesif, mandrin_dia, cartons,
  palette_type) et les références de `matieres_premieres`.

Formules :
- support (m²)  : eti_laize * eti_longueur * qte_etiquettes / 1e6
- adhésif (m²)  : qte_au_mille * qte_etiquettes / 1000     (colle au m²/1000 étiq)
- mandrins (u)  : qte_etiquettes / nb_etiq_bobin
- cartons  (u)  : mandrins / nb_bobines_carton
- palettes (u)  : cartons / (palette_nb_cartons_sol * palette_nb_cartons_hauteur)

Fenêtre 7j / 15j : today + N comme borne. Pour un dossier à cheval sur la
borne (planned_start < borne < planned_end), on applique une règle de trois
sur la durée qui tombe dans la fenêtre.

Accès : rôles _STOCK_MATIERES_ADMIN_ROLES (voir stock.py).
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.routers.stock import require_stock_matieres_admin

router = APIRouter(tags=["besoins-matieres"])

_KINDS = ("support", "adhesif", "mandrin", "carton", "palette")

# ── Utilitaires ─────────────────────────────────────────────────────────

def _f(v) -> Optional[float]:
    """Cast robuste en float positif (None si vide/invalide/≤0)."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_iso(s) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19]).date()
    except (TypeError, ValueError):
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None


def _ratio_dans_fenetre(pe: dict, today: date, borne: date) -> float:
    """Ratio du dossier tombant dans la fenêtre [today, borne].

    Règles :
    - Dossier sans dates → ratio 1 (n'est pas encore parvenu, on compte tout).
    - Dossier en retard (fin < today) → ratio 1 (besoin immédiat).
    - Dossier entièrement avant la borne → ratio 1.
    - Dossier entièrement après la borne (start > borne) → ratio 0.
    - Dossier à cheval → proportion des jours dans la fenêtre / durée totale.
    """
    ps = _parse_iso(pe.get("planned_start"))
    pe_end = _parse_iso(pe.get("planned_end"))
    dl = _parse_iso(pe.get("date_livraison"))
    # Fallback : sans planned_end, on prend date_livraison
    if not pe_end:
        pe_end = dl
    if not ps and not pe_end:
        return 1.0  # aucune info temporelle → dossier ouvert, tout compte
    if not ps:
        # Fin connue mais pas de début : on suppose durée d'un jour
        ps = pe_end
    if not pe_end:
        pe_end = ps
    if pe_end < ps:
        pe_end = ps
    # Dossier en retard : besoin immédiat
    if pe_end < today:
        return 1.0
    # Entièrement dans la fenêtre
    if pe_end <= borne:
        return 1.0
    # Entièrement après la borne
    if ps > borne:
        return 0.0
    # À cheval : proportion
    total = (pe_end - ps).days + 1
    debut_effectif = max(ps, today)
    fin_effective = min(pe_end, borne)
    dans = (fin_effective - debut_effectif).days + 1
    return max(0.0, min(1.0, dans / total)) if total > 0 else 1.0


# ── Requête source : dossiers du planning + fiches techniques ──────────

_SQL_DOSSIERS = """
    SELECT pe.id, pe.machine_id, pe.reference, pe.client, pe.description,
           pe.ref_produit, pe.ref_produit_norm, pe.numero_of, pe.statut,
           pe.planned_start, pe.planned_end, pe.date_livraison, pe.duree_heures,
           pe.position,
           m.nom AS machine_nom,
           oi.qte_etiquettes AS qte_etiquettes,
           oi.qte_bobines    AS qte_bobines,
           ft.id                         AS ft_id,
           ft.support                    AS ft_support,
           ft.adhesif                    AS ft_adhesif,
           ft.qte_au_mille               AS ft_qte_au_mille,
           ft.eti_laize                  AS ft_eti_laize,
           ft.eti_longueur               AS ft_eti_longueur,
           ft.mandrin_dia                AS ft_mandrin_dia,
           ft.nb_etiq_bobin              AS ft_nb_etiq_bobin,
           ft.nb_bobines_carton          AS ft_nb_bobines_carton,
           ft.cartons                    AS ft_cartons,
           ft.palette_type               AS ft_palette_type,
           ft.palette_nb_cartons_sol     AS ft_palette_nb_cartons_sol,
           ft.palette_nb_cartons_hauteur AS ft_palette_nb_cartons_hauteur
    FROM planning_entries pe
    LEFT JOIN machines m ON m.id = pe.machine_id
    LEFT JOIN of_imports oi ON oi.id = pe.of_import_id
    LEFT JOIN fiches_techniques ft ON ft.id = (
        SELECT ft2.id FROM fiches_techniques ft2
        WHERE COALESCE(NULLIF(TRIM(ft2.ref_produit_norm), ''), LOWER(TRIM(ft2.reference)))
            = COALESCE(NULLIF(TRIM(pe.ref_produit_norm), ''), LOWER(TRIM(pe.ref_produit)))
        ORDER BY
          CASE
            -- Tie-breaker : préférer la fiche dont la machine correspond au dossier.
            -- SQLite ne résout pas m.nom (alias JOIN outer) depuis cette sous-requête
            -- corrélée : on refait le lookup via pe.machine_id.
            WHEN LOWER(TRIM(COALESCE(ft2.machine,''))) = LOWER(TRIM(COALESCE(
                  (SELECT nom FROM machines WHERE id = pe.machine_id), '')))
                 AND TRIM(COALESCE(ft2.machine,'')) != '' THEN 0
            WHEN TRIM(COALESCE(ft2.machine,'')) = '' THEN 1
            ELSE 2
          END,
          ft2.id
        LIMIT 1
    )
    WHERE pe.statut IN ('attente', 'en_cours')
    ORDER BY COALESCE(pe.planned_start, pe.date_livraison, '9999'), pe.position
"""


def _load_mapping(conn) -> dict:
    """Retourne dict {(kind, source_value_lower): {matiere_id, reference, designation, unite_stock}}."""
    rows = conn.execute("""
        SELECT m.kind, m.source_value, m.matiere_id,
               mp.reference, mp.designation, mp.categorie
        FROM mp_fiche_mapping m
        JOIN matieres_premieres mp ON mp.id = m.matiere_id
    """).fetchall()
    out = {}
    for r in rows:
        out[(r["kind"], (r["source_value"] or "").strip().lower())] = {
            "matiere_id": r["matiere_id"],
            "reference": r["reference"],
            "designation": r["designation"],
            "categorie": r["categorie"],
        }
    return out


def _compute_besoins_dossier(pe: dict, mapping: dict) -> list:
    """Calcule la liste des besoins MP pour un dossier de prod.

    Retourne une liste de dicts :
      { kind, source_value, matiere_id?, matiere_ref?, matiere_designation?,
        quantite, unite, mapped, formule }
    """
    besoins = []
    qte = _f(pe.get("qte_etiquettes")) or 0
    if qte <= 0:
        return besoins

    def _add(kind: str, source_value, quantite: float, unite: str, formule: str):
        sv = (source_value or "").strip() if source_value else ""
        if not sv or quantite <= 0:
            return
        key = (kind, sv.lower())
        m = mapping.get(key)
        besoins.append({
            "kind": kind,
            "source_value": sv,
            "matiere_id": m["matiere_id"] if m else None,
            "matiere_ref": m["reference"] if m else None,
            "matiere_designation": m["designation"] if m else None,
            "quantite": round(quantite, 3),
            "unite": unite,
            "mapped": m is not None,
            "formule": formule,
        })

    # Support (papier / frontal) : surface étiquette × nb
    L = _f(pe.get("ft_eti_laize"))
    H = _f(pe.get("ft_eti_longueur"))
    if pe.get("ft_support") and L and H:
        _add("support", pe["ft_support"], L * H * qte / 1_000_000.0, "m²",
             f"{L:g}×{H:g} mm × {int(qte)} étiq")

    # Adhésif (colle) — qte_au_mille = m² pour 1000 étiquettes produites
    q_mille = _f(pe.get("ft_qte_au_mille"))
    if pe.get("ft_adhesif") and q_mille:
        _add("adhesif", pe["ft_adhesif"], q_mille * qte / 1000.0, "m²",
             f"{q_mille:g} m²/1000 × {int(qte)} étiq")

    # Mandrins : 1 par bobine
    nb_eb = _f(pe.get("ft_nb_etiq_bobin"))
    nb_mandrins = 0.0
    if pe.get("ft_mandrin_dia") and nb_eb:
        nb_mandrins = qte / nb_eb
        _add("mandrin", pe["ft_mandrin_dia"], nb_mandrins, "u",
             f"{int(qte)} étiq ÷ {int(nb_eb)} étiq/bobine")

    # Cartons : nb bobines / bobines par carton
    nb_bc = _f(pe.get("ft_nb_bobines_carton"))
    nb_cartons = 0.0
    if pe.get("ft_cartons") and nb_bc and nb_mandrins > 0:
        nb_cartons = nb_mandrins / nb_bc
        _add("carton", pe["ft_cartons"], nb_cartons, "u",
             f"{nb_mandrins:.1f} bobines ÷ {int(nb_bc)} bobines/carton")

    # Palettes : cartons / (cartons_sol × cartons_hauteur)
    ncs = _f(pe.get("ft_palette_nb_cartons_sol"))
    nch = _f(pe.get("ft_palette_nb_cartons_hauteur"))
    if pe.get("ft_palette_type") and ncs and nch and nb_cartons > 0:
        _add("palette", pe["ft_palette_type"], nb_cartons / (ncs * nch), "u",
             f"{nb_cartons:.1f} cartons ÷ ({int(ncs)}×{int(nch)})")

    return besoins


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/api/stock/besoins-matieres/par-dossier")
def besoins_par_dossier(request: Request):
    """Retourne une ligne par dossier de production (statut attente/en_cours),
    avec le détail des besoins MP calculés."""
    require_stock_matieres_admin(request)
    with get_db() as conn:
        mapping = _load_mapping(conn)
        rows = [dict(r) for r in conn.execute(_SQL_DOSSIERS).fetchall()]
    dossiers = []
    for pe in rows:
        besoins = _compute_besoins_dossier(pe, mapping)
        dossiers.append({
            "id": pe["id"],
            "reference": pe.get("reference"),
            "client": pe.get("client"),
            "description": pe.get("description"),
            "ref_produit": pe.get("ref_produit"),
            "numero_of": pe.get("numero_of"),
            "machine_nom": pe.get("machine_nom"),
            "statut": pe.get("statut"),
            "planned_start": pe.get("planned_start"),
            "planned_end": pe.get("planned_end"),
            "date_livraison": pe.get("date_livraison"),
            "qte_etiquettes": pe.get("qte_etiquettes"),
            "ft_id": pe.get("ft_id"),
            "besoins": besoins,
            "besoins_mapped_count": sum(1 for b in besoins if b["mapped"]),
            "besoins_total_count": len(besoins),
        })
    return {"dossiers": dossiers, "count": len(dossiers)}


@router.get("/api/stock/besoins-matieres/par-echeance")
def besoins_par_echeance(request: Request):
    """Agrège les besoins MP par référence, avec split sous 7j / 15j / total.

    Règle de proportionnalité pour les dossiers à cheval sur la borne
    (durée dans la fenêtre / durée totale du dossier)."""
    require_stock_matieres_admin(request)
    today = date.today()
    borne_7 = today + timedelta(days=7)
    borne_15 = today + timedelta(days=15)

    with get_db() as conn:
        mapping = _load_mapping(conn)
        rows = [dict(r) for r in conn.execute(_SQL_DOSSIERS).fetchall()]
        # Stock actuel pour comparaison (mp_stock non laizé + mp_stock_laize agrégé)
        stock_map: dict = {}
        for r in conn.execute("SELECT matiere_id, SUM(quantite) AS q FROM mp_stock GROUP BY matiere_id").fetchall():
            stock_map[int(r["matiere_id"])] = float(r["q"] or 0)
        for r in conn.execute("SELECT matiere_id, SUM(quantite) AS q FROM mp_stock_laize GROUP BY matiere_id").fetchall():
            mid = int(r["matiere_id"])
            stock_map[mid] = stock_map.get(mid, 0) + float(r["q"] or 0)

    # Agrégation par (kind, source_value)
    agg: dict = {}
    for pe in rows:
        r7 = _ratio_dans_fenetre(pe, today, borne_7)
        r15 = _ratio_dans_fenetre(pe, today, borne_15)
        besoins = _compute_besoins_dossier(pe, mapping)
        for b in besoins:
            key = (b["kind"], (b["source_value"] or "").strip().lower())
            if key not in agg:
                agg[key] = {
                    "kind": b["kind"],
                    "source_value": b["source_value"],
                    "matiere_id": b["matiere_id"],
                    "matiere_ref": b["matiere_ref"],
                    "matiere_designation": b["matiere_designation"],
                    "unite": b["unite"],
                    "besoin_7j": 0.0,
                    "besoin_15j": 0.0,
                    "besoin_total": 0.0,
                    "mapped": b["mapped"],
                    "nb_dossiers": 0,
                }
            agg[key]["besoin_7j"] += b["quantite"] * r7
            agg[key]["besoin_15j"] += b["quantite"] * r15
            agg[key]["besoin_total"] += b["quantite"]
            agg[key]["nb_dossiers"] += 1

    lignes = []
    for a in agg.values():
        for k in ("besoin_7j", "besoin_15j", "besoin_total"):
            a[k] = round(a[k], 3)
        a["stock_actuel"] = round(stock_map.get(a["matiere_id"], 0), 3) if a["matiere_id"] else None
        a["manque_7j"] = None
        if a["matiere_id"]:
            a["manque_7j"] = round(max(0, a["besoin_7j"] - (a["stock_actuel"] or 0)), 3)
        lignes.append(a)
    # Tri : d'abord les non mappés (à corriger), puis manque décroissant, puis besoin 7j
    lignes.sort(key=lambda x: (
        x["mapped"],
        -(x.get("manque_7j") or 0),
        -x["besoin_7j"],
    ))
    return {
        "lignes": lignes,
        "count": len(lignes),
        "today": today.isoformat(),
        "borne_7j": borne_7.isoformat(),
        "borne_15j": borne_15.isoformat(),
    }


@router.get("/api/stock/besoins-matieres/mapping")
def list_mapping(request: Request):
    """Liste toutes les correspondances FT→MP + valeurs FT non mappées détectées
    dans les dossiers actifs (pour aider à peupler la table)."""
    require_stock_matieres_admin(request)
    with get_db() as conn:
        maps = [dict(r) for r in conn.execute("""
            SELECT m.id, m.kind, m.source_value, m.matiere_id, m.notes,
                   m.created_at, m.updated_at,
                   mp.reference AS matiere_ref, mp.designation AS matiere_designation,
                   mp.categorie AS matiere_categorie
            FROM mp_fiche_mapping m
            JOIN matieres_premieres mp ON mp.id = m.matiere_id
            ORDER BY m.kind, LOWER(m.source_value)
        """).fetchall()]
        rows = [dict(r) for r in conn.execute(_SQL_DOSSIERS).fetchall()]

    mapping_keys = {(m["kind"], (m["source_value"] or "").strip().lower()) for m in maps}
    seen: dict = {}
    for pe in rows:
        for kind, col in (("support", "ft_support"), ("adhesif", "ft_adhesif"),
                          ("mandrin", "ft_mandrin_dia"), ("carton", "ft_cartons"),
                          ("palette", "ft_palette_type")):
            v = pe.get(col)
            if not v or not str(v).strip():
                continue
            key = (kind, str(v).strip().lower())
            if key in mapping_keys:
                continue
            if key not in seen:
                seen[key] = {"kind": kind, "source_value": str(v).strip(), "count": 0}
            seen[key]["count"] += 1
    non_mappe = sorted(seen.values(), key=lambda x: (x["kind"], -x["count"]))
    return {"mapping": maps, "non_mappe": non_mappe}


@router.post("/api/stock/besoins-matieres/mapping")
async def upsert_mapping(request: Request):
    """Crée ou met à jour une correspondance FT→MP.
    Body : { kind, source_value, matiere_id, notes? }"""
    require_stock_matieres_admin(request)
    body = await request.json()
    kind = (body.get("kind") or "").strip()
    source_value = (body.get("source_value") or "").strip()
    matiere_id = body.get("matiere_id")
    notes = (body.get("notes") or "").strip() or None
    if kind not in _KINDS:
        raise HTTPException(400, f"kind invalide (attendu : {'|'.join(_KINDS)})")
    if not source_value:
        raise HTTPException(400, "source_value requis")
    try:
        matiere_id = int(matiere_id)
    except (TypeError, ValueError):
        raise HTTPException(400, "matiere_id numérique requis")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        if not conn.execute("SELECT id FROM matieres_premieres WHERE id=?", (matiere_id,)).fetchone():
            raise HTTPException(404, "Matière introuvable")
        existing = conn.execute(
            "SELECT id FROM mp_fiche_mapping WHERE kind=? AND LOWER(TRIM(source_value))=LOWER(TRIM(?)) LIMIT 1",
            (kind, source_value),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE mp_fiche_mapping SET matiere_id=?, notes=?, updated_at=? WHERE id=?",
                (matiere_id, notes, now, existing["id"]),
            )
            new_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO mp_fiche_mapping (kind, source_value, matiere_id, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (kind, source_value, matiere_id, notes, now, now),
            )
            new_id = cur.lastrowid
        conn.commit()
    return {"ok": True, "id": new_id}


@router.delete("/api/stock/besoins-matieres/mapping/{map_id}")
def delete_mapping(request: Request, map_id: int):
    require_stock_matieres_admin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM mp_fiche_mapping WHERE id=?", (map_id,))
        conn.commit()
    return {"ok": True}
