"""MyQualité › Formulaires — exports des réponses (CSV et PDF).

- CSV : une ligne par destinataire (sa dernière réponse), une colonne par
  question — et par mesure quand une question en demande plusieurs. Séparateur
  « ; », BOM UTF-8 et décimales à virgule : s'ouvre tel quel dans Excel en
  français (même convention que l'export fournisseurs de settings.py).
- PDF d'une réponse : la fiche telle que le destinataire l'a remplie, non-
  conformités signalées.
- PDF d'ensemble : une synthèse par question (répartition des choix, min /
  moyenne / max des mesures, moyenne des notes), puis chaque réponse.

Les envois d'un même formulaire peuvent porter sur des versions différentes :
les colonnes suivent la version la plus récente, puis les questions qui
n'existent que dans les anciennes. Une réponse se lit toujours avec les
questions de SA version.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import datetime
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from app.services import qualite_formulaires_envois as envois
from app.services.mesures_libres import libelle as libelle_mesure
from config import APP_ORG_NAME

TYPES_DEST = {"fournisseur": "Fournisseur", "client": "Client", "personnel": "Personnel", "libre": "Adresse libre"}
STATUTS = {"envoye": "Envoyé", "ouvert": "Ouvert", "repondu": "Répondu"}


# ── Lecture ─────────────────────────────────────────────────────────────

def lignes(conn, formulaire_id: int, *, envoi_id: int | None = None, avec_sans_reponse: bool = False) -> list[dict]:
    """Une entrée par destinataire actif : envoi, destinataire, schéma de la
    version envoyée, dernière réponse (ou None) et non-conformités."""
    sql = """SELECT d.id FROM qualite_formulaires_destinataires d
               JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
              WHERE e.formulaire_id = ? AND d.actif = 1"""
    args: list = [formulaire_id]
    if envoi_id:
        sql += " AND e.id = ?"
        args.append(envoi_id)
    if not avec_sans_reponse:
        sql += " AND d.statut = 'repondu'"
    sql += " ORDER BY e.id DESC, d.organisation COLLATE NOCASE, d.nom COLLATE NOCASE, d.email"
    schemas: dict[int, dict] = {}
    out = []
    for (did,) in conn.execute(sql, args).fetchall():
        dest = envois.destinataire(conn, did)
        if not dest:
            continue
        v = int(dest["version"])
        if v not in schemas:
            schemas[v] = envois.schema_envoi(conn, dest)
        rep = envois.derniere_reponse(conn, did)
        out.append({
            "dest": dest, "schema": schemas[v], "reponse": rep,
            "nc": envois.non_conformites(schemas[v], rep["reponses"]) if rep else [],
        })
    return out


def _questions(schema: dict) -> list[dict]:
    return [q for s in schema.get("sections", []) for q in s.get("questions", [])]


def colonnes(entrees: list[dict]) -> list[dict]:
    """Colonnes des questions : version la plus récente d'abord, puis les
    questions propres aux versions plus anciennes."""
    vues: dict[str, dict] = {}
    ordre: list[str] = []
    for e in sorted(entrees, key=lambda x: -int(x["dest"]["version"])):
        for q in _questions(e["schema"]):
            if q["id"] not in vues:
                vues[q["id"]] = q
                ordre.append(q["id"])
    # Nombre libre : autant de colonnes que la plus longue réponse reçue.
    longueurs: dict[str, int] = {}
    for e in entrees:
        for qid, r in ((e["reponse"] or {}).get("reponses") or {}).items():
            if isinstance(r, list):
                longueurs[qid] = max(longueurs.get(qid, 0), len(r))
    cols = []
    for qid in ordre:
        q = vues[qid]
        unite = f" ({q['unit']})" if q.get("unit") else ""
        pts = q.get("points") or []
        if q["type"] == "value" and q.get("points_libres"):
            n = max(longueurs.get(qid, 0), int(q.get("min_points") or 1))
            for k in range(n):
                cols.append({"q": q, "k": k, "titre": f"{q['label']} — {libelle_mesure(q, k)}{unite}"})
        elif q["type"] == "value" and len(pts) > 1:
            for k, p in enumerate(pts):
                cols.append({"q": q, "k": k, "titre": f"{q['label']} — {p}{unite}"})
        else:
            cols.append({"q": q, "k": None, "titre": q["label"] + unite})
    return cols


# ── Mise en forme des valeurs ───────────────────────────────────────────

def nombre(x) -> str:
    if x is None or x == "":
        return ""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    s = str(int(f)) if f == int(f) else f"{f:.6f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def date_fr(iso) -> str:
    if not iso:
        return ""
    s = str(iso)
    p = s[:10].split("-")
    if len(p) != 3:
        return s
    return f"{p[2]}/{p[1]}/{p[0]}" + (f" {s[11:16]}" if len(s) >= 16 else "")


def valeur(q: dict, reponses: dict, k: int | None = None) -> str:
    """Réponse à une question, en texte (une mesure si k est donné)."""
    r = reponses.get(q["id"])
    if r is None:
        return ""
    t = q["type"]
    if t == "value":
        if isinstance(r, list):
            if k is not None:
                return nombre(r[k]) if k < len(r) else ""
            return " / ".join(nombre(x) if x is not None else "—" for x in r)
        return nombre(r) if k in (None, 0) else ""
    if t == "choice":
        sel = r if isinstance(r, list) else [r]
        txt = ", ".join(str(x) for x in sel)
        autre = reponses.get(q["id"] + "_other")
        return txt + (f" — {autre}" if autre else "")
    if t == "scale":
        return f"{r} / {q.get('max', 5)}"
    if t == "date":
        return date_fr(r)[:10]
    return str(r)


def _nom_fichier(titre: str, suffixe: str, ext: str) -> str:
    base = unicodedata.normalize("NFKD", titre or "formulaire").encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower()[:60] or "formulaire"
    jour = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    return f"{base}-{suffixe}-{jour}.{ext}"


# ── CSV ─────────────────────────────────────────────────────────────────

def csv_reponses(entrees: list[dict], titre: str) -> tuple[str, str]:
    cols = colonnes(entrees)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    w.writerow(["Envoi du", "Version", "Organisation", "Contact", "Email", "Type", "Statut", "Répondu le",
                "Répondant", "Non-conformités", "Questions non conformes"] + [c["titre"] for c in cols])
    for e in entrees:
        d, rep = e["dest"], e["reponse"]
        reps = rep["reponses"] if rep else {}
        labels = {q["id"]: q["label"] for q in _questions(e["schema"])}
        mes_q = {q["id"] for q in _questions(e["schema"])}
        w.writerow([
            date_fr(d["envoi_cree_le"])[:10], f"v{d['version']}", d["organisation"] or "", d["nom"] or "", d["email"],
            TYPES_DEST.get(d["type"], d["type"]), STATUTS.get(d["statut"], d["statut"]),
            date_fr(d["repondu_le"]), (rep or {}).get("repondant_nom") or "",
            len(e["nc"]) if rep else "", " · ".join(labels.get(x, x) for x in e["nc"]),
        ] + [(valeur(c["q"], reps, c["k"]).replace("\r", " ").replace("\n", " ") if c["q"]["id"] in mes_q else "")
             for c in cols])
    return _nom_fichier(titre, "reponses", "csv"), "﻿" + buf.getvalue()


# ── Synthèse ────────────────────────────────────────────────────────────

def synthese(entrees: list[dict]) -> list[dict]:
    """Par question : nombre de réponses et résumé lisible. Ne compte que les
    réponses données avec une version qui contient la question."""
    out = []
    for c in colonnes(entrees):
        q, k = c["q"], c["k"]
        valeurs = []
        hors = 0
        for e in entrees:
            if not e["reponse"] or q["id"] not in {x["id"] for x in _questions(e["schema"])}:
                continue
            r = e["reponse"]["reponses"].get(q["id"])
            if r is None:
                continue
            if q["type"] == "value":
                x = r[k] if (isinstance(r, list) and k is not None and k < len(r)) else (r if not isinstance(r, list) else None)
                if x is None:
                    continue
                valeurs.append(float(x))
                if (q.get("min") is not None and x < q["min"]) or (q.get("max") is not None and x > q["max"]):
                    hors += 1
            else:
                valeurs.append(r)
        n = len(valeurs)
        resume = ""
        if n and q["type"] == "value":
            moy = sum(valeurs) / n
            unite = f" {q['unit']}" if q.get("unit") else ""
            resume = f"min {nombre(min(valeurs))} · moyenne {nombre(round(moy, 3))} · max {nombre(max(valeurs))}{unite}"
            if q.get("min") is not None or q.get("max") is not None:
                resume += f" · {hors} hors tolérance"
        elif n and q["type"] == "choice":
            comptes: dict[str, int] = {}
            for r in valeurs:
                for x in (r if isinstance(r, list) else [r]):
                    comptes[str(x)] = comptes.get(str(x), 0) + 1
            nc = set(q.get("nc_responses") or [])
            resume = " · ".join(f"{x} {comptes[x]}" + (" (NC)" if x in nc else "")
                                for x in sorted(comptes, key=lambda y: -comptes[y]))
        elif n and q["type"] == "scale":
            moy = sum(int(x) for x in valeurs) / n
            resume = f"moyenne {nombre(round(moy, 2))} / {q.get('max', 5)}"
        elif n:
            resume = f"{n} réponse{'s' if n > 1 else ''}"
        out.append({"titre": c["titre"], "n": n, "resume": resume or "Aucune réponse"})
    return out


# ── PDF ─────────────────────────────────────────────────────────────────

def _pdf(titre_doc: str, construire) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    accent = colors.HexColor("#0891b2")  # hex-ok : PDF reportlab
    gris = colors.HexColor("#64748b")    # hex-ok : PDF reportlab
    rouge = colors.HexColor("#dc2626")   # hex-ok : PDF reportlab
    trait = colors.HexColor("#cbd5e1")   # hex-ok : PDF reportlab
    st = {
        "brand": ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=8, textColor=accent, leading=10),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=gris, leading=12),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10, textColor=accent, leading=13,
                             spaceBefore=8, spaceAfter=5, keepWithNext=1),
        "q": ParagraphStyle("q", fontName="Helvetica-Bold", fontSize=9, leading=12),
        "r": ParagraphStyle("r", fontName="Helvetica", fontSize=9, leading=12),
        "nc": ParagraphStyle("nc", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=rouge),
        "petit": ParagraphStyle("petit", fontName="Helvetica", fontSize=8, textColor=gris, leading=10),
    }
    ctx = {"st": st, "accent": accent, "gris": gris, "rouge": rouge, "trait": trait, "mm": mm,
           "P": lambda t, s="r": Paragraph(escape(str(t or "")).replace("\n", "<br/>"), st[s])}

    def pied(canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 7)
        canv.setFillColor(gris)
        canv.drawString(18 * mm, 10 * mm, f"{APP_ORG_NAME} · {titre_doc}"[:110])
        canv.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
        canv.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title=titre_doc, author=APP_ORG_NAME)
    doc.build(construire(ctx), onFirstPage=pied, onLaterPages=pied)
    return buf.getvalue()


def _fiche(ctx, e: dict, titre: str) -> list:
    """Flowables d'une réponse : en-tête puis questions et réponses."""
    from reportlab.platypus import KeepTogether, Spacer, Table, TableStyle

    st, P, mm = ctx["st"], ctx["P"], ctx["mm"]
    d, rep = e["dest"], e["reponse"]
    reps = rep["reponses"] if rep else {}
    nc = set(e["nc"])
    qui = (d["nom"] if d["type"] == "personnel" else d["organisation"]) or d["nom"] or d["email"]
    meta = [f"Destinataire : {qui}" + (f" ({d['nom']})" if d["type"] != "personnel" and d["organisation"] and d["nom"] else ""),
            f"Email : {d['email']}",
            f"Version v{d['version']} · envoyée le {date_fr(d['envoi_cree_le'])[:10]}"]
    if rep:
        meta.append(f"Réponse du {date_fr(rep['soumis_le'])}" + (f" par {rep['repondant_nom']}" if rep.get("repondant_nom") else ""))
    else:
        meta.append(f"Pas de réponse — statut : {STATUTS.get(d['statut'], d['statut'])}")
    out = [P(APP_ORG_NAME, "brand"), Spacer(1, 2 * mm), P(titre, "h1")]
    out += [P(m, "sub") for m in meta]
    if nc:
        out += [Spacer(1, 2 * mm), P(f"{len(nc)} réponse(s) non conforme(s).", "nc")]
    for s in e["schema"].get("sections", []):
        if not s.get("questions"):
            continue
        if s.get("titre"):
            out.append(P(s["titre"], "h2"))
        else:
            out.append(Spacer(1, 3 * mm))
        for q in s["questions"]:
            est_nc = q["id"] in nc
            lib = q["label"] + (" — non conforme" if est_nc else "")
            bornes = []
            if q["type"] == "value":
                if q.get("min") is not None or q.get("max") is not None:
                    bornes.append(f"tolérance {nombre(q.get('min')) or '−∞'} à {nombre(q.get('max')) or '+∞'}")
                if q.get("target_value") is not None:
                    bornes.append(f"cible {nombre(q['target_value'])}")
            if q["type"] == "value" and (q.get("points_libres") or len(q.get("points") or []) > 1):
                unite = f" {q['unit']}" if q.get("unit") else ""
                brut = reps.get(q["id"]) if isinstance(reps.get(q["id"]), list) else []
                lignes_m = []
                libelles = ([libelle_mesure(q, k) for k in range(max(len(brut), 1))]
                            if q.get("points_libres") else q["points"])
                for k, p in enumerate(libelles):
                    txt = f"{escape(p)} : {escape(valeur(q, reps, k) or '—')}{escape(unite)}"
                    x = brut[k] if k < len(brut) else None
                    # Seule la mesure hors tolérance passe en rouge.
                    if x is not None and ((q.get("min") is not None and x < q["min"]) or (q.get("max") is not None and x > q["max"])):
                        txt = f'<font color="#{ctx["rouge"].hexval()[2:]}"><b>{txt}</b></font>'
                    lignes_m.append(txt)
                from reportlab.platypus import Paragraph
                cellule = Paragraph("<br/>".join(lignes_m), st["r"])
            else:
                v = valeur(q, reps)
                if v and q["type"] == "value" and q.get("unit"):
                    v += f" {q['unit']}"
                cellule = P(v or "—", "nc" if est_nc else "r")
            bloc = [P(lib, "nc" if est_nc else "q")]
            if bornes:
                bloc.append(P(" · ".join(bornes) + (f" {q['unit']}" if q.get("unit") else ""), "petit"))
            tb = Table([[bloc, cellule]], colWidths=[80 * mm, 94 * mm], hAlign="LEFT")
            tb.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, ctx["trait"]),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
            ] + ([("LINEBEFORE", (0, 0), (0, -1), 2, ctx["rouge"]), ("LEFTPADDING", (0, 0), (0, -1), 5)] if est_nc else [])))
            out.append(KeepTogether([tb]))
    return out


def pdf_reponse(e: dict, titre: str) -> tuple[str, bytes]:
    d = e["dest"]
    qui = (d["nom"] if d["type"] == "personnel" else d["organisation"]) or d["nom"] or d["email"]
    contenu = _pdf(f"{titre} — {qui}", lambda ctx: _fiche(ctx, e, titre))
    return _nom_fichier(f"{titre} {qui}", "reponse", "pdf"), contenu


def pdf_ensemble(entrees: list[dict], titre: str, *, nb_destinataires: int) -> tuple[str, bytes]:
    def construire(ctx):
        from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

        P, mm = ctx["P"], ctx["mm"]
        repondus = [e for e in entrees if e["reponse"]]
        nb_nc = sum(1 for e in repondus if e["nc"])
        out = [P(APP_ORG_NAME, "brand"), Spacer(1, 2 * mm), P(titre, "h1"),
               P(f"Synthèse au {date_fr(datetime.now(ZoneInfo('Europe/Paris')).isoformat())[:10]} · "
                 f"{len(repondus)} réponse(s) sur {nb_destinataires} destinataire(s)"
                 + (f" · {nb_nc} avec non-conformité" if nb_nc else ""), "sub"),
               P("Réponses par question", "h2")]
        lignes_s = [[P("Question", "q"), P("Réponses", "q"), P("Résumé", "q")]]
        for s in synthese(entrees):
            lignes_s.append([P(s["titre"]), P(str(s["n"])), P(s["resume"])])
        tb = Table(lignes_s, colWidths=[70 * mm, 20 * mm, 84 * mm], repeatRows=1, hAlign="LEFT")
        tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, ctx["trait"]),
                                ("LINEBELOW", (0, 0), (-1, 0), 0.8, ctx["accent"]), ("LEFTPADDING", (0, 0), (0, -1), 0)]))
        out.append(tb)
        out.append(P("Destinataires", "h2"))
        lignes_d = [[P("Destinataire", "q"), P("Statut", "q"), P("Répondu le", "q"), P("NC", "q")]]
        for e in entrees:
            d = e["dest"]
            qui = (d["nom"] if d["type"] == "personnel" else d["organisation"]) or d["nom"] or d["email"]
            lignes_d.append([P(f"{qui}\n{d['email']}"), P(STATUTS.get(d["statut"], d["statut"])),
                             P(date_fr(d["repondu_le"])), P(str(len(e["nc"])) if e["reponse"] else "", "nc" if e["nc"] else "r")])
        tb = Table(lignes_d, colWidths=[90 * mm, 28 * mm, 40 * mm, 16 * mm], repeatRows=1, hAlign="LEFT")
        tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, ctx["trait"]),
                                ("LINEBELOW", (0, 0), (-1, 0), 0.8, ctx["accent"]), ("LEFTPADDING", (0, 0), (0, -1), 0)]))
        out.append(tb)
        for e in repondus:
            out.append(PageBreak())
            out += _fiche(ctx, e, titre)
        return out

    return _nom_fichier(titre, "reponses", "pdf"), _pdf(f"{titre} — réponses", construire)
