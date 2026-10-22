"""
Étiquettes spécifiques — validation des modèles et version de production.

  brouillon     jamais approuvé, ou modifié depuis la dernière approbation
  a_approuver   modification soumise, en attente d'un rôle qualité
  approuve      la version courante est celle de la production

La production imprime TOUJOURS `version_approuvee` : une modification en
cours ne part pas à l'atelier tant qu'elle n'est pas approuvée. Un modèle
jamais approuvé ne s'imprime pas.

Point d'entrée pour l'impression (static/mysifa_etiq_impression.js,
app/routers/etiq_impression.py) : `modele_production(conn, modele_id)`.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from app.services import etiq_specifiques as es
from app.services.etiq_specifiques import EtiquetteInvalide

STATUTS = {"brouillon": "Brouillon", "a_approuver": "À approuver", "approuve": "Approuvée"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _cle(row, k, defaut=None):
    return row[k] if k in row.keys() else defaut


def modele_production(conn, modele_id: int) -> dict:
    """Le modèle tel que la production doit l'imprimer : format et mise en
    page de la version approuvée. Lève EtiquetteInvalide sinon."""
    row = conn.execute("SELECT * FROM etiq_modeles WHERE id=? AND archive=0", (modele_id,)).fetchone()
    if not row:
        raise EtiquetteInvalide("Étiquette introuvable.")
    va = _cle(row, "version_approuvee")
    if not va:
        raise EtiquetteInvalide(f"« {row['nom']} » n'a jamais été approuvée — à faire valider par la qualité avant impression.")
    if int(va) == int(_cle(row, "version", 1) or 1):
        src = row
    else:
        src = conn.execute("SELECT * FROM etiq_modeles_versions WHERE modele_id=? AND version=?",
                           (modele_id, va)).fetchone()
        if not src:
            raise EtiquetteInvalide(f"Version approuvée {va} de « {row['nom']} » introuvable.")
    return {"id": row["id"], "nom": row["nom"], "dossier_id": row["dossier_id"],
            "usage": _cle(row, "usage", ""), "client": _cle(row, "client", ""),
            "version": int(va), "version_courante": int(_cle(row, "version", 1) or 1),
            "largeur_mm": src["largeur_mm"], "hauteur_mm": src["hauteur_mm"], "dpi": src["dpi"],
            "layout": es.normaliser_layout(src["layout_json"]), "layout_json": src["layout_json"]}


def apres_enregistrement(statut: str, version_changee: bool) -> str:
    """Statut après un enregistrement : toute modification du dessin repasse
    en brouillon (la production garde la version approuvée)."""
    return "brouillon" if version_changee else statut


def journaliser(conn, modele_id: int, version: int, action: str, email: str, commentaire: str = "") -> None:
    conn.execute("INSERT INTO etiq_approbations (modele_id,version,action,commentaire,par,le) VALUES (?,?,?,?,?,?)",
                 (modele_id, version, action, (commentaire or "")[:1000], email, _now()))


def historique(conn, modele_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT version,action,commentaire,par,le FROM etiq_approbations WHERE modele_id=? ORDER BY le DESC, id DESC LIMIT 200",
        (modele_id,)).fetchall()]


def pour_dossier(conn, no_dossier: str, usage: str = "") -> list[dict]:
    """Modèles approuvés applicables à un dossier : même client que le
    dossier (raison sociale ou client du modèle), usage demandé d'abord."""
    pe = conn.execute("SELECT client FROM planning_entries WHERE reference=? ORDER BY id DESC LIMIT 1",
                      (no_dossier,)).fetchone()
    client = (pe["client"] if pe else "") or ""
    rows = conn.execute(
        "SELECT m.id, m.nom, m.usage, m.client, m.version_approuvee, d.nom AS dossier_nom FROM etiq_modeles m"
        " LEFT JOIN etiq_dossiers d ON d.id=m.dossier_id"
        " WHERE m.archive=0 AND m.version_approuvee IS NOT NULL"
        " AND (LOWER(TRIM(m.client))=LOWER(TRIM(?)) OR LOWER(TRIM(d.nom))=LOWER(TRIM(?)))",
        (client, client)).fetchall() if client else []
    out = [dict(r) for r in rows]
    out.sort(key=lambda r: (0 if usage and r["usage"] == usage else 1, r["nom"].lower()))
    return out


def rendu(conn, modele_id: int, enregistrement: Optional[dict] = None, index: int = 0,
          production: bool = True) -> dict:
    """Valeurs et objets visibles d'une étiquette remplie (aperçu, kiosque,
    impression en fin de bobine). Les compteurs montrent le prochain numéro
    sans le réserver."""
    if production:
        m = modele_production(conn, modele_id)
    else:
        row = conn.execute("SELECT * FROM etiq_modeles WHERE id=? AND archive=0", (modele_id,)).fetchone()
        if not row:
            raise EtiquetteInvalide("Étiquette introuvable.")
        m = {"id": row["id"], "nom": row["nom"], "largeur_mm": row["largeur_mm"], "hauteur_mm": row["hauteur_mm"],
             "dpi": row["dpi"], "layout": es.normaliser_layout(row["layout_json"]), "version": _cle(row, "version", 1)}
    plan = es.plan_serie(conn, modele_id, m["layout"], index + 1)
    vals = es.valeurs_etiquette(m["layout"], plan, index, {k: str(v) for k, v in (enregistrement or {}).items()})
    visibles = es.elements_visibles(m["layout"], vals)
    langue = vals.get("_langue", "")
    elements = [dict(e, valeur=es.substituer(es.texte_element(e, langue), vals)) if e["type"] in ("texte", "code_barre")
                else dict(e) for e in visibles]
    m.pop("layout_json", None)
    return {"modele": m, "valeurs": vals, "elements": elements,
            "zpl": es.rendre_zpl(m["layout"], m["largeur_mm"], m["hauteur_mm"], m["dpi"], vals)}


def etat(row) -> dict:
    return {"statut_validation": _cle(row, "statut_validation", "brouillon") or "brouillon",
            "statut_libelle": STATUTS.get(_cle(row, "statut_validation", "brouillon") or "brouillon", ""),
            "version_approuvee": _cle(row, "version_approuvee"),
            "approuve_par": _cle(row, "approuve_par"), "approuve_le": _cle(row, "approuve_le")}


def layout_json_production(conn, modele_id: int) -> tuple:
    """(layout_json, largeur, hauteur, dpi, version) de la production."""
    m = modele_production(conn, modele_id)
    return json.dumps(m["layout"], ensure_ascii=False), m["largeur_mm"], m["hauteur_mm"], m["dpi"], m["version"]
