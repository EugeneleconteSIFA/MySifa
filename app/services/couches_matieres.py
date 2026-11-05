"""MyTools › Calculs bobine › Métrage — épaisseur des couches d'une matière.

Une matière enduite empile un frontal, un adhésif et une glassine
(`COUCHES_MATIERE` de config.py) : son épaisseur est la somme des leurs, comme
l'épaisseur totale d'une fiche produit (`fiche_technique.donnees_produit`).

L'épaisseur d'une matière se lit au même endroit que pour les fiches
techniques, dans le même ordre : la fiche saisie, puis MyStock
(`matieres_premieres.epaisseur_um`), puis RVGI (`mat_mat.m1_epais` de l'article
relié). Aucune règle de MySifa ne déduit une épaisseur du grammage (il y
faudrait une densité par matière) : une matière sans épaisseur est rendue avec
`epaisseur_um = None` et son grammage, l'écran la fait saisir.
"""
from __future__ import annotations

import json

from config import COUCHES_MATIERE
from app.services.pricing import fiche_technique


def _pos(v):
    return fiche_technique._pos(v)


def liste(conn) -> dict:
    cats = [c for c, _ in COUCHES_MATIERE]
    if not cats:
        return {"couches": []}
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
    ep_col = "epaisseur_um" if "epaisseur_um" in cols else "NULL AS epaisseur_um"
    gsm_col = "weight_gsm" if "weight_gsm" in cols else "NULL AS weight_gsm"
    brouillon = "AND COALESCE(brouillon, 0) = 0" if "brouillon" in cols else ""
    marques = ",".join("?" * len(cats))
    rows = conn.execute(
        f"""SELECT id, lower(categorie) AS categorie, reference, designation, {ep_col}, {gsm_col}
              FROM matieres_premieres
             WHERE lower(categorie) IN ({marques}) AND COALESCE(actif, 1) = 1 {brouillon}
             ORDER BY designation COLLATE NOCASE, reference COLLATE NOCASE""",
        cats,
    ).fetchall()

    fiches: dict[int, dict] = {}
    try:
        for f in conn.execute("SELECT objet_id, data FROM mp_fiche_technique WHERE objet='matiere'"):
            try:
                fiches[int(f["objet_id"])] = json.loads(f["data"] or "{}") or {}
            except ValueError:
                pass
    except Exception:
        pass

    par_cat: dict[str, list] = {c: [] for c in cats}
    for r in rows:
        fiche = fiches.get(int(r["id"]), {})
        ep, source = _pos(fiche.get("epaisseur_um")), "Fiche technique"
        if not ep:
            ep, source = _pos(r["epaisseur_um"]), "MyStock"
        if not ep:
            rv = fiche_technique._rvgi_matiere(conn, int(r["id"]), r["categorie"])
            ep, source = _pos(rv.get("epaisseur_um")), "RVGI"
        gsm = _pos(fiche.get("grammage_gsm")) or _pos(r["weight_gsm"])
        par_cat[r["categorie"]].append({
            "id": int(r["id"]),
            "libelle": (r["designation"] or r["reference"] or "").strip(),
            "reference": r["reference"] or "",
            "epaisseur_um": ep,
            "source": source if ep else None,
            "grammage_gsm": gsm,
        })
    return {"couches": [{"categorie": c, "libelle": l, "matieres": par_cat.get(c, [])} for c, l in COUCHES_MATIERE]}
