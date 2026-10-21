"""MyQualité › Formulaires — structure d'un formulaire et stockage.

Un formulaire est une suite de sections, chacune avec ses questions. Le format
des questions est celui du questionnaire des alertes maintenance
(`static/mysifa_alert_form.js`), étendu : les types « value » et « choice » y
gardent exactement les mêmes champs, pour qu'une alerte puisse un jour pointer
vers un formulaire de MyQualité sans conversion.

    {"sections": [{"id", "titre", "description", "questions": [
        {"id", "type", "label", "required", "help", ...champs du type}
    ]}]}

Types :
  text    long (bool), placeholder
  value   unit, min, max, target_value, points, placeholder, out_of_range_is_nc
  choice  responses, multi, display (chips | select), allow_other,
          other_is_nc, nc_responses
  date    —
  scale   min (0 ou 1), max (2 à 10), label_min, label_max

Les identifiants de question sont stables : une réponse se range sous l'id de
sa question, jamais sous sa position, pour survivre à un réordonnancement.

Le serveur nettoie au lieu de refuser : un champ inconnu est retiré, un texte
trop long est coupé, une liste trop longue est tronquée. Seule une structure
illisible (pas un objet) est refusée.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TYPES = ("text", "value", "choice", "date", "scale")
STATUTS = ("brouillon", "publie", "archive")

MAX_SECTIONS = 30
MAX_QUESTIONS = 200
MAX_REPONSES = 30


def _maintenant() -> str:
    return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")


def _txt(v: Any, n: int) -> str:
    return v.strip()[:n] if isinstance(v, str) else ""


def _num(v: Any) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _id(v: Any, prefixe: str, pris: set[str]) -> str:
    s = v.strip()[:40] if isinstance(v, str) else ""
    if not s or s in pris or not all(c.isalnum() or c in "_-" for c in s):
        s = prefixe + secrets.token_hex(4)
        while s in pris:
            s = prefixe + secrets.token_hex(4)
    pris.add(s)
    return s


def _liste_txt(v: Any, n_max: int, longueur: int) -> list[str]:
    out: list[str] = []
    if not isinstance(v, list):
        return out
    for x in v:
        s = _txt(x, longueur)
        if s and s not in out:
            out.append(s)
        if len(out) >= n_max:
            break
    return out


def normaliser_question(q: dict, pris: set[str]) -> dict | None:
    if not isinstance(q, dict):
        return None
    t = q.get("type") if q.get("type") in TYPES else "text"
    out: dict[str, Any] = {
        "id": _id(q.get("id"), "q_", pris),
        "type": t,
        "label": _txt(q.get("label"), 300),
    }
    if bool(q.get("required")):
        out["required"] = True
    aide = _txt(q.get("help"), 600)
    if aide:
        out["help"] = aide

    if t == "text":
        if bool(q.get("long")):
            out["long"] = True
        ph = _txt(q.get("placeholder"), 80)
        if ph:
            out["placeholder"] = ph
    elif t == "value":
        unit = _txt(q.get("unit"), 20)
        if unit:
            out["unit"] = unit
        vmin, vmax = _num(q.get("min")), _num(q.get("max"))
        if vmin is not None and vmax is not None and vmin > vmax:
            vmin, vmax = vmax, vmin
        if vmin is not None:
            out["min"] = vmin
        if vmax is not None:
            out["max"] = vmax
        cible = _num(q.get("target_value"))
        if cible is not None:
            out["target_value"] = cible
        from app.services.mesures_libres import normaliser as _mesures_libres
        libres = _mesures_libres(q)
        points = _liste_txt(q.get("points"), 10, 40)
        if libres:
            out.update(libres)
        elif len(points) > 1:
            out["points"] = points
        ph = _txt(q.get("placeholder"), 60)
        if ph:
            out["placeholder"] = ph
        if bool(q.get("out_of_range_is_nc")) and (vmin is not None or vmax is not None):
            out["out_of_range_is_nc"] = True
    elif t == "choice":
        reponses = _liste_txt(q.get("responses"), MAX_REPONSES, 150) or ["Oui", "Non"]
        out["responses"] = reponses
        out["multi"] = bool(q.get("multi", False))
        if q.get("display") == "select" and not out["multi"]:
            out["display"] = "select"
        if bool(q.get("allow_other")):
            out["allow_other"] = True
            if bool(q.get("other_is_nc")):
                out["other_is_nc"] = True
        nc = [r for r in _liste_txt(q.get("nc_responses"), MAX_REPONSES, 150) if r in reponses]
        if nc:
            out["nc_responses"] = nc
    elif t == "scale":
        bas = 0 if _num(q.get("min")) == 0 else 1
        haut = _num(q.get("max"))
        haut = int(haut) if haut is not None else 5
        out["min"] = bas
        out["max"] = max(2, min(10, haut))
        for k in ("label_min", "label_max"):
            s = _txt(q.get(k), 40)
            if s:
                out[k] = s
    return out


def normaliser_schema(raw: Any) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except ValueError:
            raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Structure du formulaire illisible.")
    pris: set[str] = set()
    sections: list[dict] = []
    nb_q = 0
    for s in (raw.get("sections") or [])[:MAX_SECTIONS]:
        if not isinstance(s, dict):
            continue
        questions = []
        for q in s.get("questions") or []:
            if nb_q >= MAX_QUESTIONS:
                break
            nq = normaliser_question(q, pris)
            if nq is not None:
                questions.append(nq)
                nb_q += 1
        sections.append({
            "id": _id(s.get("id"), "s_", pris),
            "titre": _txt(s.get("titre"), 200),
            "description": _txt(s.get("description"), 1000),
            "questions": questions,
        })
    if not sections:
        sections.append({"id": _id(None, "s_", pris), "titre": "", "description": "", "questions": []})
    return {"sections": sections}


def nb_questions(schema: dict) -> int:
    return sum(len(s.get("questions") or []) for s in schema.get("sections") or [])


# ── Stockage ─────────────────────────────────────────────────────────────

def _ligne(r) -> dict:
    d = dict(r)
    try:
        schema = json.loads(d.pop("schema_json") or "{}")
    except ValueError:
        schema = {}
    d["schema"] = normaliser_schema(schema)
    d["nb_questions"] = nb_questions(d["schema"])
    return d


def liste(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT f.*,
                  (SELECT v.schema_json FROM qualite_formulaires_versions v
                    WHERE v.formulaire_id = f.id AND v.numero = f.version_courante) AS publie_json,
                  (SELECT v.titre FROM qualite_formulaires_versions v
                    WHERE v.formulaire_id = f.id AND v.numero = f.version_courante) AS publie_titre,
                  (SELECT COUNT(*) FROM qualite_formulaires_destinataires d
                     JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
                    WHERE e.formulaire_id = f.id AND d.actif = 1) AS nb_destinataires,
                  (SELECT COUNT(*) FROM qualite_formulaires_destinataires d
                     JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
                    WHERE e.formulaire_id = f.id AND d.actif = 1 AND d.statut = 'repondu') AS nb_reponses
             FROM qualite_formulaires f
            ORDER BY f.modifie_le DESC"""
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        publie_json, publie_titre = d.pop("publie_json"), d.pop("publie_titre")
        d = _ligne(d)
        d["a_publier"] = _a_publier(d, publie_json, publie_titre)
        d.pop("schema")
        out.append(d)
    return out


def _a_publier(d: dict, publie_json: str | None, publie_titre: str | None) -> bool:
    """Le brouillon diffère-t-il de la dernière version publiée ?"""
    if not d.get("version_courante"):
        return False
    try:
        publie = normaliser_schema(publie_json or "{}")
    except ValueError:
        return True
    return publie != d["schema"] or (publie_titre or "") != d["titre"]


def lire(conn, fid: int) -> dict | None:
    r = conn.execute("SELECT * FROM qualite_formulaires WHERE id = ?", (fid,)).fetchone()
    if not r:
        return None
    d = _ligne(r)
    versions = conn.execute(
        """SELECT numero, titre, schema_json, publie_par, publie_le
             FROM qualite_formulaires_versions WHERE formulaire_id = ?
            ORDER BY numero DESC""",
        (fid,),
    ).fetchall()
    courante = next((v for v in versions if v["numero"] == d["version_courante"]), None)
    d["a_publier"] = _a_publier(d, courante["schema_json"] if courante else None,
                                courante["titre"] if courante else None)
    d["versions"] = [{"numero": v["numero"], "titre": v["titre"], "publie_par": v["publie_par"],
                      "publie_le": v["publie_le"]} for v in versions]
    try:
        c = conn.execute(
            """SELECT COUNT(*) AS n, SUM(CASE WHEN d.statut = 'repondu' THEN 1 ELSE 0 END) AS r
                 FROM qualite_formulaires_destinataires d
                 JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
                WHERE e.formulaire_id = ? AND d.actif = 1""",
            (fid,),
        ).fetchone()
        d["nb_destinataires"], d["nb_reponses"] = int(c["n"] or 0), int(c["r"] or 0)
    except Exception:
        # Tables d'envoi pas encore créées (migration en attente)
        d["nb_destinataires"] = d["nb_reponses"] = 0
    return d


def creer(conn, *, titre: str, description: str = "", schema: Any = None, auteur: str | None) -> int:
    titre = _txt(titre, 200) or "Formulaire sans titre"
    sch = normaliser_schema(schema if schema is not None else {})
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO qualite_formulaires
             (titre, description, statut, schema_json, cree_par, cree_le, modifie_par, modifie_le)
           VALUES (?, ?, 'brouillon', ?, ?, ?, ?, ?)""",
        (titre, _txt(description, 2000), json.dumps(sch, ensure_ascii=False), auteur, now, auteur, now),
    )
    return int(cur.lastrowid)


def enregistrer(conn, fid: int, *, titre: Any, description: Any, schema: Any, auteur: str | None) -> None:
    sch = normaliser_schema(schema)
    conn.execute(
        """UPDATE qualite_formulaires
              SET titre = ?, description = ?, schema_json = ?, modifie_par = ?, modifie_le = ?
            WHERE id = ?""",
        (_txt(titre, 200) or "Formulaire sans titre", _txt(description, 2000),
         json.dumps(sch, ensure_ascii=False), auteur, _maintenant(), fid),
    )


def publier(conn, fid: int, *, auteur: str | None) -> int:
    d = lire(conn, fid)
    if d is None:
        raise LookupError("Formulaire introuvable.")
    if d["statut"] == "archive":
        raise ValueError("Formulaire archivé — restaurer avant de publier.")
    if d["nb_questions"] == 0:
        raise ValueError("Formulaire vide — ajouter au moins une question.")
    sans_libelle = [q for s in d["schema"]["sections"] for q in s["questions"] if not q["label"]]
    if sans_libelle:
        raise ValueError(f"{len(sans_libelle)} question(s) sans libellé.")
    numero = int(d["version_courante"] or 0) + 1
    now = _maintenant()
    conn.execute(
        """INSERT INTO qualite_formulaires_versions
             (formulaire_id, numero, titre, schema_json, publie_par, publie_le)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (fid, numero, d["titre"], json.dumps(d["schema"], ensure_ascii=False), auteur, now),
    )
    conn.execute(
        """UPDATE qualite_formulaires SET statut = 'publie', version_courante = ?,
                  modifie_par = ?, modifie_le = ? WHERE id = ?""",
        (numero, auteur, now, fid),
    )
    return numero


def dupliquer(conn, fid: int, *, auteur: str | None) -> int:
    d = lire(conn, fid)
    if d is None:
        raise LookupError("Formulaire introuvable.")
    # Nouveaux identifiants : la copie est un autre formulaire, ses réponses
    # ne doivent jamais pouvoir se confondre avec celles de l'original.
    sch = json.loads(json.dumps(d["schema"]))
    for s in sch["sections"]:
        s.pop("id", None)
        for q in s["questions"]:
            q.pop("id", None)
    return creer(conn, titre=(d["titre"] + " (copie)")[:200], description=d["description"],
                 schema=sch, auteur=auteur)


def changer_statut(conn, fid: int, statut: str, *, auteur: str | None) -> None:
    if statut not in STATUTS:
        raise ValueError("Statut inconnu.")
    conn.execute(
        "UPDATE qualite_formulaires SET statut = ?, modifie_par = ?, modifie_le = ? WHERE id = ?",
        (statut, auteur, _maintenant(), fid),
    )


def supprimer(conn, fid: int) -> None:
    """Seul un brouillon jamais publié se supprime : une version publiée a pu
    être envoyée, ses réponses doivent rester lisibles. Le reste s'archive."""
    r = conn.execute("SELECT version_courante FROM qualite_formulaires WHERE id = ?", (fid,)).fetchone()
    if not r:
        raise LookupError("Formulaire introuvable.")
    if int(r["version_courante"] or 0) > 0:
        raise ValueError("Formulaire déjà publié — l'archiver plutôt que le supprimer.")
    conn.execute("DELETE FROM qualite_formulaires WHERE id = ?", (fid,))
