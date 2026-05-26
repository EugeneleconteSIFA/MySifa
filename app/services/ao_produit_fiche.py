"""MyAO — Fiche produit : structure JSON, désignation, export HTML."""
from __future__ import annotations

import json
from html import escape
from typing import Any


def default_fiche() -> dict[str, Any]:
    return {
        "type_produit": "rouleau",
        "impressions": True,
        "etiquette": {
            "laize": None,
            "longueur": None,
            "rayon": None,
            "perforation": "",
        },
        "echenillage": {"droite": None, "gauche": None, "avance": None},
        "matiere": {
            "frontal_id": None,
            "adhesif_id": None,
            "grammage_adhesif": None,
            "glassine_id": None,
            "couleur_glassine": "",
        },
        "bobines": {
            "diametre_mandrin": None,
            "enroulement": "interieur",
            "diametre_bobine": None,
            "nb_etiquettes": None,
        },
        "impressions_detail": {
            "aplat": False,
            "aplat_pourcent": None,
            "recto": 0,
            "verso": 0,
            "recto_details": [],
            "verso_details": [],
        },
        "conditionnement": {
            "carton": {
                "matiere_id": None,
                "bobines_sol": None,
                "nb_etages": None,
                "bobines_carton": None,
            },
            "palette": {
                "matiere_id": None,
                "cartons_sol": None,
                "nb_etages": None,
                "cartons_palette": None,
            },
        },
        "particularites": "",
    }


def _norm_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_fiche(fiche: dict[str, Any]) -> dict[str, Any]:
    """Convertit les identifiants vides en null pour le stockage JSON."""
    mat = fiche.get("matiere") or {}
    mat["frontal_id"] = _norm_id(mat.get("frontal_id"))
    mat["adhesif_id"] = _norm_id(mat.get("adhesif_id"))
    mat["glassine_id"] = _norm_id(mat.get("glassine_id"))
    fiche["matiere"] = mat
    cond = fiche.get("conditionnement") or {}
    for key in ("carton", "palette"):
        block = cond.get(key) or {}
        block["matiere_id"] = _norm_id(block.get("matiere_id"))
        cond[key] = block
    fiche["conditionnement"] = cond
    return fiche


def parse_fiche(raw: str | None) -> dict[str, Any]:
    base = default_fiche()
    if not raw:
        return base
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return base
    if not isinstance(data, dict):
        return base

    def merge(dst: dict, src: dict) -> dict:
        for k, v in src.items():
            if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
                merge(dst[k], v)
            else:
                dst[k] = v
        return dst

    return merge(base, data)


def format_etiquette(etiquette: dict | None) -> str:
    if not etiquette:
        return ""
    laize = etiquette.get("laize")
    longueur = etiquette.get("longueur")
    if laize is None or longueur is None:
        return ""
    try:
        l1 = int(float(laize))
        l2 = int(float(longueur))
    except (TypeError, ValueError):
        return ""
    return f"{l1}mm X {l2}mm"


def build_designation(ref: str, client_nom: str | None, type_produit: str) -> str:
    ref = (ref or "").strip()
    parts = [ref] if ref else []
    if client_nom:
        parts.append(client_nom.strip())
    tp = (type_produit or "").strip().capitalize()
    if tp and tp not in parts:
        parts.append(tp)
    return " — ".join(parts) if parts else ref or "Produit"


def produit_row_to_api(row: dict, client_nom: str | None = None) -> dict:
    fiche = parse_fiche(row.get("fiche_json"))
    out = dict(row)
    out["fiche"] = fiche
    out["format_etiquette"] = format_etiquette(fiche.get("etiquette"))
    if client_nom:
        out["client_nom"] = client_nom
    return out


def _esc(v: Any) -> str:
    if v is None or v == "":
        return "—"
    return escape(str(v))


def _row_html(label: str, value: Any) -> str:
    return (
        f'<tr><td style="padding:6px 12px;color:var(--muted);font-size:12px;'
        f'font-weight:600;width:40%">{escape(label)}</td>'
        f'<td style="padding:6px 12px;font-size:13px">{_esc(value)}</td></tr>'
    )


def render_fiche_html(
    produit: dict,
    *,
    client_nom: str | None = None,
    matieres_map: dict[int, dict] | None = None,
) -> str:
    """HTML imprimable (thème MySifa via variables CSS)."""
    matieres_map = matieres_map or {}
    fiche = produit.get("fiche") or parse_fiche(produit.get("fiche_json"))
    ref = produit.get("ref") or ""
    titre = escape(ref or "Fiche produit")
    client_nom = client_nom or produit.get("client_nom") or "—"

    def mp_label(mid: Any) -> str:
        if mid is None:
            return "—"
        m = matieres_map.get(int(mid))
        if not m:
            return f"#{mid}"
        return f"{m.get('reference', '')} — {m.get('designation', '')}".strip(" —")

    et = fiche.get("etiquette") or {}
    ech = fiche.get("echenillage") or {}
    mat = fiche.get("matiere") or {}
    bob = fiche.get("bobines") or {}
    imp = fiche.get("impressions_detail") or {}
    cond = fiche.get("conditionnement") or {}
    cart = cond.get("carton") or {}
    pal = cond.get("palette") or {}

    imp_rows = ""
    if fiche.get("impressions"):
        imp_rows += _row_html("Aplat", f"Oui ({imp.get('aplat_pourcent')} %)" if imp.get("aplat") else "Non")
        imp_rows += _row_html("Recto", imp.get("recto"))
        imp_rows += _row_html("Verso", imp.get("verso"))
        for i, d in enumerate(imp.get("recto_details") or [], 1):
            imp_rows += _row_html(
                f"Recto {i}",
                f"{d.get('couleur', '')} — {d.get('printing_area', '')}".strip(" —"),
            )
        for i, d in enumerate(imp.get("verso_details") or [], 1):
            imp_rows += _row_html(
                f"Verso {i}",
                f"{d.get('couleur', '')} — {d.get('printing_area', '')}".strip(" —"),
            )

    sections = [
        ("Infos générales", [
            _row_html("Réf. produit", ref),
            _row_html("Type", fiche.get("type_produit")),
            _row_html("Impressions", "Oui" if fiche.get("impressions") else "Non"),
            _row_html("Client", client_nom),
        ]),
        ("Étiquette", [
            _row_html("Format", format_etiquette(et)),
            _row_html("Laize (mm)", et.get("laize")),
            _row_html("Longueur (mm)", et.get("longueur")),
            _row_html("Rayon (mm)", et.get("rayon")),
            _row_html("Perforation", et.get("perforation")),
        ]),
        ("Échenillage", [
            _row_html("Espace à droite (mm)", ech.get("droite")),
            _row_html("Espace à gauche (mm)", ech.get("gauche")),
            _row_html("En avance (mm)", ech.get("avance")),
        ]),
        ("Matière", [
            _row_html("Frontal", mp_label(mat.get("frontal_id"))),
            _row_html("Adhésif", mp_label(mat.get("adhesif_id"))),
            _row_html("Grammage adhésif (gsm)", mat.get("grammage_adhesif")),
            _row_html("Glassine", mp_label(mat.get("glassine_id"))),
            _row_html("Couleur glassine", mat.get("couleur_glassine")),
        ]),
        ("Bobines", [
            _row_html("Diamètre mandrin (mm)", bob.get("diametre_mandrin")),
            _row_html("Enroulement", bob.get("enroulement")),
            _row_html("Diamètre bobine (mm)", bob.get("diametre_bobine")),
            _row_html("Étiquettes / bobine", bob.get("nb_etiquettes")),
        ]),
    ]
    if fiche.get("impressions"):
        sections.append(("Impressions", [imp_rows]))

    sections.extend([
        ("Conditionnement — Cartons", [
            _row_html("Type carton", mp_label(cart.get("matiere_id"))),
            _row_html("Bobines au sol", cart.get("bobines_sol")),
            _row_html("Nombre d'étages", cart.get("nb_etages")),
            _row_html("Bobines / carton", cart.get("bobines_carton")),
        ]),
        ("Conditionnement — Palettes", [
            _row_html("Type palette", mp_label(pal.get("matiere_id"))),
            _row_html("Cartons au sol", pal.get("cartons_sol")),
            _row_html("Étages de cartons", pal.get("nb_etages")),
            _row_html("Cartons / palette", pal.get("cartons_palette")),
        ]),
        ("Particularités", [
            f'<tr><td colspan="2" style="padding:12px;font-size:13px;line-height:1.6">'
            f'{_esc(fiche.get("particularites"))}</td></tr>',
        ]),
    ])

    blocks = ""
    for title, rows in sections:
        blocks += (
            f'<div style="margin-bottom:20px">'
            f'<div style="font-size:12px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.5px;color:var(--text);margin-bottom:8px">{escape(title)}</div>'
            f'<table style="width:100%;border-collapse:collapse;border:1px solid var(--border)">'
            f"{''.join(rows)}</table></div>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Fiche produit — {titre}</title>
<style>
:root{{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--muted:#64748b;--accent:#0891b2}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:24px}}
.wrap{{max-width:800px;margin:0 auto;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:28px}}
h1{{font-size:20px;font-weight:800;margin:0 0 8px}}
.sub{{font-size:12px;color:var(--muted);margin-bottom:24px}}
@media print{{body{{background:#fff;padding:0}}.wrap{{border:none;box-shadow:none}}}}
</style>
</head>
<body>
<div class="wrap">
<h1>Fiche produit — {titre}</h1>
<div class="sub">MyAO · MySifa</div>
{blocks}
</div>
<script>window.onload=function(){{window.print();}};</script>
</body>
</html>"""
