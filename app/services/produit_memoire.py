"""Memoire produit — agregation de la production par reference produit.

Le pivot est `ref_produit_norm` ("XXX/NNNN"), deja maintenu par triggers sur
`planning_entries` et `fiches_techniques` (cf. fiche_ref_parser). Ce module ne
cree aucune notion metier : il materialise la chaine qui existe deja

    production_data.no_dossier -> planning_entries.reference
                               -> planning_entries.ref_produit_norm

et l'expose sous une forme lisible : une serie par production passee.

Regle de conception : une serie est un SNAPSHOT FIGE. On ne la recalcule pas a
chaque lecture. Un changement de regle de calcul cree une colonne, il ne
reecrit pas l'histoire — sinon l'atelier voit les chiffres du passe bouger sans
qu'aucune production n'ait eu lieu.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.services.dossier_stats import build_dossier_production_stats

_PARIS = ZoneInfo("Europe/Paris")

# Types de savoir proposes a la saisie. Volontairement courts : une liste de
# quinze categories ne se remplit jamais correctement.
TYPES_SAVOIR = ("reglage", "piege", "defaut", "matiere", "outillage", "controle", "autre")

LABELS_TYPE_SAVOIR = {
    "reglage":   "Reglage",
    "piege":     "Piege",
    "defaut":    "Defaut recurrent",
    "matiere":   "Matiere",
    "outillage": "Outillage",
    "controle":  "Controle qualite",
    "autre":     "Autre",
}


def now_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _cols(conn, table: str) -> set:
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _norm(value) -> Optional[str]:
    """Cle produit normalisee, sans dependance dure au parser."""
    if not value:
        return None
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        return None
    try:
        return normalize_ref_produit(str(value))
    except Exception:
        return None


def mediane(valeurs: List[float]) -> Optional[float]:
    vals = sorted(float(v) for v in valeurs if v is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    if n % 2:
        return round(vals[mid], 2)
    return round((vals[mid - 1] + vals[mid]) / 2.0, 2)


# ─── Resolution dossier -> reference produit ──────────────────────────────────

def contexte_dossier(conn, no_dossier: str) -> Dict[str, Any]:
    """Contexte planning d'un dossier : reference produit, machine, OF, fiche.

    Retourne toujours un dict ; `ref_produit_norm` vaut None quand le dossier
    n'est rattachable a aucun produit — c'est ce cas-la qui fait le taux de
    rattachement, et il doit rester visible plutot que d'etre devine.
    """
    ref = (no_dossier or "").strip()
    out: Dict[str, Any] = {
        "no_dossier": ref, "ref_produit_norm": None, "ref_produit": None,
        "planning_entry_id": None, "of_import_id": None, "fiche_id": None,
        "machine": None, "client": None, "designation": None,
        "laize_mm": None, "format": None, "conditionnement_norm": None,
    }
    if not ref:
        return out

    pe_cols = _cols(conn, "planning_entries")
    if not pe_cols:
        return out

    sel = ["pe.id AS pe_id", "pe.reference", "pe.client", "pe.description"]
    for c in ("ref_produit", "ref_produit_norm", "of_import_id", "numero_of",
              "laize", "format_l", "format_h"):
        if c in pe_cols:
            sel.append(f"pe.{c}")
    sql = (
        "SELECT " + ", ".join(sel) + ", m.nom AS machine_nom "
        "FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id "
        "WHERE trim(pe.reference) = trim(?)"
    )
    if "numero_of" in pe_cols:
        sql += " OR trim(COALESCE(pe.numero_of,'')) = trim(?)"
        row = conn.execute(sql + " ORDER BY pe.id DESC LIMIT 1", (ref, ref)).fetchone()
    else:
        row = conn.execute(sql + " ORDER BY pe.id DESC LIMIT 1", (ref,)).fetchone()

    if row:
        r = dict(row)
        out["planning_entry_id"] = r.get("pe_id")
        out["client"] = r.get("client")
        out["designation"] = r.get("description")
        out["machine"] = r.get("machine_nom")
        out["of_import_id"] = r.get("of_import_id")
        out["ref_produit"] = r.get("ref_produit")
        out["ref_produit_norm"] = (r.get("ref_produit_norm") or "").strip() or None
        if r.get("laize") is not None:
            try:
                out["laize_mm"] = int(round(float(r["laize"])))
            except (TypeError, ValueError):
                pass
        if r.get("format_l") and r.get("format_h"):
            out["format"] = f"{r['format_l']} x {r['format_h']} mm"

    # Repli 1 : la colonne normalisee est vide mais le libelle est la.
    if not out["ref_produit_norm"]:
        out["ref_produit_norm"] = _norm(out.get("ref_produit"))

    # Repli 2 : l'OF rattache porte deja la reference normalisee (option B de
    # l'import OF : `of_imports.reference` EST la cle produit).
    if not out["ref_produit_norm"] and out["of_import_id"]:
        of_row = conn.execute(
            "SELECT reference FROM of_imports WHERE id=?", (out["of_import_id"],)
        ).fetchone()
        if of_row:
            out["ref_produit_norm"] = _norm(of_row["reference"])

    # Repli 3 : le numero de dossier lui-meme porte parfois la reference.
    if not out["ref_produit_norm"]:
        out["ref_produit_norm"] = _norm(ref)

    # Fiche technique : meme regle de choix que /api/of/planning/{id} —
    # la fiche dont la machine correspond au dossier passe en premier.
    if out["ref_produit_norm"] and "ref_produit_norm" in _cols(conn, "fiches_techniques"):
        fiche = conn.execute(
            """SELECT id, laize, format, conditionnement_norm
               FROM fiches_techniques
               WHERE ref_produit_norm = ?
               ORDER BY CASE
                   WHEN LOWER(TRIM(COALESCE(machine,''))) = LOWER(TRIM(COALESCE(?,'')))
                        AND TRIM(COALESCE(machine,'')) != '' THEN 0
                   WHEN TRIM(COALESCE(machine,'')) = '' THEN 1
                   ELSE 2 END, id
               LIMIT 1""",
            (out["ref_produit_norm"], out.get("machine") or ""),
        ).fetchone()
        if fiche:
            f = dict(fiche)
            out["fiche_id"] = f.get("id")
            out["conditionnement_norm"] = f.get("conditionnement_norm")
            if out["format"] is None:
                out["format"] = f.get("format")
            if out["laize_mm"] is None and f.get("laize") is not None:
                try:
                    out["laize_mm"] = int(round(float(f["laize"])))
                except (TypeError, ValueError):
                    pass
    return out


# ─── Materialisation d'une serie ──────────────────────────────────────────────

def _saisies_dossier(conn, no_dossier: str) -> List[dict]:
    pd_cols = _cols(conn, "production_data")
    where = "no_dossier = ?"
    if "est_annule" in pd_cols:
        where += " AND COALESCE(est_annule,0) = 0"
    rows = conn.execute(
        f"SELECT * FROM production_data WHERE {where} ORDER BY date_operation ASC, id ASC",
        (no_dossier,),
    ).fetchall()
    return [dict(r) for r in rows]


def _outillage_of(conn, of_import_id: Optional[int]) -> Optional[dict]:
    if not of_import_id:
        return None
    row = conn.execute("SELECT * FROM of_imports WHERE id=?", (of_import_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    out = {k: v for k, v in d.items() if k.startswith("outil") and v not in (None, "")}
    return out or None


def _matieres_dossier(conn, no_dossier: str) -> List[dict]:
    if not _cols(conn, "fab_matieres_utilisees"):
        return []
    rows = conn.execute(
        """SELECT code_barre, scanned_at, operateur, machine_nom
           FROM fab_matieres_utilisees WHERE no_dossier = ?
           ORDER BY scanned_at ASC, id ASC""",
        (no_dossier,),
    ).fetchall()
    return [dict(r) for r in rows]


def _commentaires_dossier(conn, saisies: List[dict]) -> List[dict]:
    out = []
    for s in saisies:
        txt = (s.get("commentaire") or "").strip()
        if txt:
            out.append({
                "saisie_id": s.get("id"), "date": s.get("date_operation"),
                "operateur": s.get("operateur"), "operation": s.get("operation"),
                "texte": txt, "origine": "commentaire",
            })
        motif = (s.get("annule_motif") or "").strip() if "annule_motif" in s else ""
        if motif:
            out.append({
                "saisie_id": s.get("id"), "date": s.get("annule_le") or s.get("date_operation"),
                "operateur": s.get("annule_par") or s.get("operateur"),
                "operation": s.get("operation"),
                "texte": motif, "origine": "annulation",
            })
    return out


def _nb_nc(conn, no_dossier: str) -> int:
    if "no_dossier" not in _cols(conn, "nc_dossiers"):
        return 0
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM nc_dossiers WHERE trim(COALESCE(no_dossier,'')) = trim(?)",
        (no_dossier,),
    ).fetchone()
    return int(row["n"] or 0) if row else 0


def materialiser_serie(conn, no_dossier: str, cloture_par: Optional[str] = None) -> Optional[dict]:
    """Ecrit (ou reecrit) la serie d'un dossier. Retourne le snapshot, ou None.

    None signifie « pas rattachable » : aucune reference produit, ou aucune
    saisie. On n'invente rien — un dossier non rattachable doit rester compte
    comme tel dans le taux de rattachement.
    """
    ref = (no_dossier or "").strip()
    if not ref:
        return None

    ctx = contexte_dossier(conn, ref)
    if not ctx.get("ref_produit_norm"):
        return None

    saisies = _saisies_dossier(conn, ref)
    if not saisies:
        return None

    stats = build_dossier_production_stats(saisies, ref)
    temps = stats.get("temps_totaux") or {}
    qtes = stats.get("quantites") or {}

    arrets = {}
    for op in stats.get("by_operation") or []:
        if str(op.get("category") or "").lower() == "arret" and float(op.get("minutes") or 0) > 0:
            arrets[str(op.get("code"))] = {
                "label": op.get("label"), "minutes": round(float(op["minutes"]), 1),
                "count": op.get("count"),
            }

    dates = [str(s.get("date_operation") or "") for s in saisies if s.get("date_operation")]
    dates = sorted(d for d in dates if d)
    operateurs = [o.get("operateur") for o in (stats.get("operateurs") or []) if o.get("operateur")]

    payload = {
        "ref_produit_norm": ctx["ref_produit_norm"],
        "no_dossier": ref,
        "planning_entry_id": ctx.get("planning_entry_id"),
        "of_import_id": ctx.get("of_import_id"),
        "fiche_id": ctx.get("fiche_id"),
        "machine": ctx.get("machine"),
        "laize_mm": ctx.get("laize_mm"),
        "conditionnement_norm": ctx.get("conditionnement_norm"),
        "format": ctx.get("format"),
        "matiere": None,
        "ref_adhesif": None,
        "client": ctx.get("client"),
        "designation": ctx.get("designation"),
        "operateurs": json.dumps(operateurs, ensure_ascii=False),
        "date_debut": dates[0] if dates else None,
        "date_fin": dates[-1] if dates else None,
        "nb_saisies": stats.get("nb_saisies") or 0,
        "temps_calage_min": temps.get("calage_min"),
        "temps_prod_min": temps.get("production_min"),
        "temps_arret_min": temps.get("arret_min"),
        "duree_totale_min": temps.get("duree_totale_min"),
        "metrage_m": qtes.get("metrage_m"),
        "etiquettes": qtes.get("etiquettes"),
        "vitesse_m_min": stats.get("vitesse_m_min"),
        "arrets_par_code": json.dumps(arrets, ensure_ascii=False),
        "outillage": json.dumps(_outillage_of(conn, ctx.get("of_import_id")) or {}, ensure_ascii=False),
        "matieres_consommees": json.dumps(_matieres_dossier(conn, ref), ensure_ascii=False),
        "commentaires": json.dumps(_commentaires_dossier(conn, saisies), ensure_ascii=False),
        "nb_nc": _nb_nc(conn, ref),
        "cloture_le": now_iso(),
        "cloture_par": cloture_par,
    }

    if ctx.get("of_import_id"):
        of_row = conn.execute(
            "SELECT matiere, ref_adhesif FROM of_imports WHERE id=?", (ctx["of_import_id"],)
        ).fetchone()
        if of_row:
            payload["matiere"] = of_row["matiere"]
            payload["ref_adhesif"] = of_row["ref_adhesif"]

    champs = list(payload.keys())
    maj = [c for c in champs if c != "no_dossier"]
    conn.execute(
        "INSERT INTO produit_series (" + ", ".join(champs) + ") "
        "VALUES (" + ", ".join("?" * len(champs)) + ") "
        "ON CONFLICT(no_dossier) DO UPDATE SET "
        + ", ".join(f"{c}=excluded.{c}" for c in maj),
        [payload[c] for c in champs],
    )
    conn.commit()

    # Un scan d'OF depose avant la cloture attend d'etre rattache a sa serie.
    try:
        conn.execute(
            "UPDATE produit_documents SET ref_produit_norm=? "
            "WHERE no_dossier=? AND (ref_produit_norm IS NULL OR ref_produit_norm='')",
            (payload["ref_produit_norm"], ref),
        )
        conn.commit()
    except Exception:
        pass

    return payload


def rattraper_series(conn, limit: Optional[int] = None, refaire: bool = False,
                     offset: int = 0) -> dict:
    """Materialise les series manquantes sur l'historique.

    Idempotent : sans `refaire`, ne touche pas aux dossiers deja materialises.
    """
    pd_cols = _cols(conn, "production_data")
    where = "operation_code = '89'"
    if "est_annule" in pd_cols:
        where += " AND COALESCE(est_annule,0) = 0"
    sql = (
        "SELECT DISTINCT trim(no_dossier) AS ref FROM production_data "
        f"WHERE {where} AND trim(COALESCE(no_dossier,'')) NOT IN ('', '0')"
    )
    if not refaire:
        sql += " AND trim(no_dossier) NOT IN (SELECT no_dossier FROM produit_series)"
    sql += " ORDER BY ref"
    if limit:
        # `offset` sert a avancer par-dessus les dossiers non rattachables : ils
        # restent candidats a chaque passe (rien ne les retire du lot), et sans
        # ce decalage un rattrapage par lots boucle indefiniment sur eux.
        sql += f" LIMIT {int(limit)} OFFSET {max(0, int(offset))}"

    refs = [r["ref"] for r in conn.execute(sql).fetchall()]
    faits, sans_produit = 0, []
    for ref in refs:
        try:
            if materialiser_serie(conn, ref, cloture_par="rattrapage"):
                faits += 1
            else:
                sans_produit.append(ref)
        except Exception:
            sans_produit.append(ref)
    return {
        "candidats": len(refs), "materialisees": faits,
        "non_rattachables": len(sans_produit),
        "exemples_non_rattachables": sans_produit[:25],
    }


# ─── Lectures ─────────────────────────────────────────────────────────────────

def _serie_dict(row) -> dict:
    d = dict(row)
    for k in ("operateurs", "arrets_par_code", "outillage", "matieres_consommees", "commentaires"):
        raw = d.get(k)
        if raw:
            try:
                d[k] = json.loads(raw)
            except (ValueError, TypeError):
                d[k] = None
    return d


def series_produit(conn, ref_produit_norm: str, limit: Optional[int] = None,
                   exclure_dossier: Optional[str] = None) -> List[dict]:
    sql = "SELECT * FROM produit_series WHERE ref_produit_norm = ?"
    params: list = [ref_produit_norm]
    if exclure_dossier:
        sql += " AND no_dossier != ?"
        params.append(exclure_dossier)
    sql += " ORDER BY COALESCE(date_fin, date_debut) DESC, id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return [_serie_dict(r) for r in conn.execute(sql, params).fetchall()]


def savoirs_produit(conn, ref_produit_norm: str, inclure_obsoletes: bool = False,
                    user_login: Optional[str] = None) -> List[dict]:
    sql = "SELECT * FROM produit_savoirs WHERE ref_produit_norm = ?"
    if not inclure_obsoletes:
        sql += " AND obsolete = 0"
    sql += " ORDER BY epingle DESC, utile_count DESC, datetime(created_at) DESC, id DESC"
    rows = [dict(r) for r in conn.execute(sql, (ref_produit_norm,)).fetchall()]
    votes = set()
    if user_login and rows:
        ids = [r["id"] for r in rows]
        marks = ",".join("?" * len(ids))
        votes = {
            r["savoir_id"] for r in conn.execute(
                f"SELECT savoir_id FROM produit_savoirs_utile "
                f"WHERE user_login = ? AND savoir_id IN ({marks})",
                [user_login] + ids,
            ).fetchall()
        }
    for r in rows:
        r["type_label"] = LABELS_TYPE_SAVOIR.get(r.get("type") or "autre", "Autre")
        r["vote_utilisateur"] = r["id"] in votes
    return rows


def documents_produit(conn, ref_produit_norm: str) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM produit_documents WHERE ref_produit_norm = ? AND statut != 'ecarte' "
        "ORDER BY datetime(importe_le) DESC, id DESC",
        (ref_produit_norm,),
    ).fetchall()
    return [dict(r) for r in rows]


def identite_produit(conn, ref_produit_norm: str) -> dict:
    """Identite lue sur la fiche technique la plus complete de la reference."""
    out = {"ref_produit_norm": ref_produit_norm, "designation": None, "format": None,
           "laize": None, "support": None, "nb_couleurs": None, "fiches": []}
    ft_cols = _cols(conn, "fiches_techniques")
    if "ref_produit_norm" not in ft_cols:
        return out
    champs = [c for c in ("id", "reference", "designation", "format", "laize", "support",
                          "matiere", "machine", "nb_couleurs", "conditionnement")
              if c in ft_cols]
    rows = conn.execute(
        "SELECT " + ", ".join(champs) + " FROM fiches_techniques "
        "WHERE ref_produit_norm = ? ORDER BY id",
        (ref_produit_norm,),
    ).fetchall()
    fiches = [dict(r) for r in rows]
    out["fiches"] = fiches
    for f in fiches:
        for k_src, k_dst in (("designation", "designation"), ("format", "format"),
                             ("laize", "laize"), ("support", "support"),
                             ("matiere", "support"), ("nb_couleurs", "nb_couleurs")):
            if out.get(k_dst) in (None, "") and f.get(k_src) not in (None, ""):
                out[k_dst] = f[k_src]
    return out


def resume_produit(conn, ref_produit_norm: str, user_login: Optional[str] = None,
                   exclure_dossier: Optional[str] = None) -> dict:
    """Vue complete d'une reference : identite, series, medianes, savoirs, scans."""
    series = series_produit(conn, ref_produit_norm, exclure_dossier=exclure_dossier)
    savoirs = savoirs_produit(conn, ref_produit_norm, user_login=user_login)
    documents = documents_produit(conn, ref_produit_norm)

    machines = sorted({s["machine"] for s in series if s.get("machine")})
    clients = sorted({s["client"] for s in series if s.get("client")})
    recentes = series[:5]
    medianes = {
        "calage_min": mediane([s.get("temps_calage_min") for s in recentes]),
        "prod_min": mediane([s.get("temps_prod_min") for s in recentes]),
        "arret_min": mediane([s.get("temps_arret_min") for s in recentes]),
        "vitesse_m_min": mediane([s.get("vitesse_m_min") for s in recentes]),
        "metrage_m": mediane([s.get("metrage_m") for s in recentes]),
        "base_series": len(recentes),
    }

    arrets: Dict[str, dict] = {}
    for s in series:
        for code, info in (s.get("arrets_par_code") or {}).items():
            acc = arrets.setdefault(code, {
                "code": code, "label": (info or {}).get("label"),
                "minutes": 0.0, "series": 0,
            })
            acc["minutes"] += float((info or {}).get("minutes") or 0)
            acc["series"] += 1
    arrets_list = sorted(arrets.values(), key=lambda a: (-a["series"], -a["minutes"]))
    for a in arrets_list:
        a["minutes"] = round(a["minutes"], 1)
        a["part_series"] = round(a["series"] / len(series), 2) if series else 0

    return {
        "ref_produit_norm": ref_produit_norm,
        "identite": identite_produit(conn, ref_produit_norm),
        "nb_series": len(series),
        "machines": machines,
        "clients": clients,
        "derniere_production": series[0]["date_fin"] if series else None,
        "medianes": medianes,
        "arrets_recurrents": arrets_list[:8],
        "series": series,
        "savoirs": savoirs,
        "documents": documents,
    }


def apercu_pour_dossier(conn, no_dossier: str, user_login: Optional[str] = None) -> dict:
    """Ce que Saisieprod affiche : y a-t-il un historique sur ce dossier ?

    `disponible` est faux des qu'il n'y a ni serie anterieure, ni savoir, ni
    scan. Le bouton ne doit alors pas exister du tout : un bouton toujours
    present qui ouvre « aucune donnee » perd sa credibilite en trois clics.
    """
    ctx = contexte_dossier(conn, no_dossier)
    ref = ctx.get("ref_produit_norm")
    vide = {
        "disponible": False, "no_dossier": (no_dossier or "").strip(),
        "ref_produit_norm": ref, "nb_series": 0, "nb_savoirs": 0, "nb_documents": 0,
    }
    if not ref:
        return vide
    n_series = conn.execute(
        "SELECT COUNT(*) AS n FROM produit_series WHERE ref_produit_norm=? AND no_dossier != ?",
        (ref, (no_dossier or "").strip()),
    ).fetchone()["n"]
    n_savoirs = conn.execute(
        "SELECT COUNT(*) AS n FROM produit_savoirs WHERE ref_produit_norm=? AND obsolete=0",
        (ref,),
    ).fetchone()["n"]
    n_docs = conn.execute(
        "SELECT COUNT(*) AS n FROM produit_documents WHERE ref_produit_norm=? AND statut!='ecarte'",
        (ref,),
    ).fetchone()["n"]
    return {
        "disponible": bool(n_series or n_savoirs or n_docs),
        "no_dossier": (no_dossier or "").strip(),
        "ref_produit_norm": ref,
        "nb_series": int(n_series or 0),
        "nb_savoirs": int(n_savoirs or 0),
        "nb_documents": int(n_docs or 0),
    }


def dossiers_non_materialises(conn, ref_produit_norm: str) -> List[str]:
    """Dossiers de cette reference qui ont tourne mais n'ont pas encore de serie.

    Sert a distinguer deux situations que l'utilisateur ne doit surtout pas
    confondre : « cette reference n'a jamais tourne » et « elle a tourne, mais
    le rattrapage n'a pas encore ete lance ». Repondre « aucune donnee » dans
    le second cas revient a mentir a quelqu'un qui sait qu'il a produit ce
    produit — et a lui faire douter de l'outil plutot que d'agir.
    """
    ref = (ref_produit_norm or "").strip()
    if not ref:
        return []
    pe_cols = _cols(conn, "planning_entries")
    if "ref_produit_norm" not in pe_cols:
        return []
    pd_cols = _cols(conn, "production_data")
    where_pd = "pd.no_dossier = pe.reference AND pd.operation_code = '89'"
    if "est_annule" in pd_cols:
        where_pd += " AND COALESCE(pd.est_annule,0) = 0"
    base = f"""SELECT DISTINCT pe.reference AS no_dossier
               FROM planning_entries pe
               WHERE {{cle}}
                 AND EXISTS (SELECT 1 FROM production_data pd WHERE {where_pd})
                 AND pe.reference NOT IN (SELECT no_dossier FROM produit_series)
               ORDER BY pe.reference"""
    try:
        # `norm_ref_produit` est enregistree sur chaque connexion (elle alimente
        # les triggers). L'inclure rattrape les dossiers dont la colonne
        # normalisee est restee vide — sinon un backfill jamais lance donne le
        # meme resultat qu'une reference qui n'a jamais tourne.
        rows = conn.execute(
            base.format(cle="(pe.ref_produit_norm = ? OR norm_ref_produit(pe.ref_produit) = ?)"),
            (ref, ref),
        ).fetchall()
    except Exception:
        rows = conn.execute(base.format(cle="pe.ref_produit_norm = ?"), (ref,)).fetchall()
    return [r["no_dossier"] for r in rows]


def taux_rattachement(conn) -> dict:
    """Part des dossiers termines rattachables a une reference produit.

    C'est l'indicateur qui dit si la memoire produit dit la verite. Une
    memoire alimentee par 60 % des dossiers est une memoire qui ment, et
    cette derive doit se voir sans ouvrir la base.
    """
    pd_cols = _cols(conn, "production_data")
    where = "operation_code='89' AND trim(COALESCE(no_dossier,'')) NOT IN ('','0')"
    if "est_annule" in pd_cols:
        where += " AND COALESCE(est_annule,0)=0"
    total = conn.execute(
        f"SELECT COUNT(DISTINCT trim(no_dossier)) AS n FROM production_data WHERE {where}"
    ).fetchone()["n"] or 0
    rattaches = conn.execute("SELECT COUNT(*) AS n FROM produit_series").fetchone()["n"] or 0

    par_mois = [dict(r) for r in conn.execute(
        f"""SELECT substr(date_operation,1,7) AS mois,
                   COUNT(DISTINCT trim(no_dossier)) AS dossiers
            FROM production_data WHERE {where}
            GROUP BY mois ORDER BY mois DESC LIMIT 18"""
    ).fetchall()]
    for m in par_mois:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM produit_series WHERE substr(COALESCE(date_fin,date_debut),1,7)=?",
            (m["mois"],),
        ).fetchone()
        m["series"] = int(row["n"] or 0)

    multi = conn.execute(
        """SELECT COUNT(*) AS n FROM (
               SELECT ref_produit_norm FROM produit_series
               GROUP BY ref_produit_norm HAVING COUNT(*) >= 2)"""
    ).fetchone()["n"] or 0
    refs = conn.execute(
        "SELECT COUNT(DISTINCT ref_produit_norm) AS n FROM produit_series"
    ).fetchone()["n"] or 0

    return {
        "dossiers_termines": int(total),
        "series_materialisees": int(rattaches),
        "taux": round(rattaches / total, 3) if total else 0.0,
        "references": int(refs),
        "references_multi_series": int(multi),
        "par_mois": par_mois,
    }
