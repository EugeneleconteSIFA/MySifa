"""MyQualité › Formulaires — envoi aux destinataires et réponses.

Modèle : le questionnaire EUDR (lien personnel, suivi envoyé / ouvert /
répondu, relances, réponses jamais écrasées), mais le lien mène à l'Espace
SIFA du destinataire (`portail_espace.py`), pas à une page propre au
formulaire.

Trois sources de destinataires, plus l'adresse libre :
  fournisseur  fournisseurs_fsc + fournisseur_contacts (emails JSON)
  client       gc_tiers (est_client) + gc_tiers_contacts — décision du
               20/10/2026 : les contacts de l'ERP font foi pour les clients
  personnel    users actifs ; reçoivent aussi une tâche dans MySifa
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.services import portail_espace
from app.services.qualite_formulaires import normaliser_schema
from config import APP_ORG_NAME

TYPES_DESTINATAIRE = ("fournisseur", "client", "personnel", "libre")
STATUTS = ("envoye", "ouvert", "repondu")
MAX_DESTINATAIRES = 300


def _maintenant() -> str:
    return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")


def _emails_json(v: Any) -> list[str]:
    if isinstance(v, list):
        brut = v
    else:
        try:
            brut = json.loads(v or "[]")
        except ValueError:
            brut = [x for x in str(v or "").replace(";", ",").split(",")]
    if not isinstance(brut, list):
        brut = [brut]
    out = []
    for x in brut:
        e = portail_espace.normaliser_email(str(x or ""))
        if e and e not in out:
            out.append(e)
    return out


# ── Candidats ───────────────────────────────────────────────────────────

def candidats(conn, type_: str, q: str = "") -> list[dict]:
    """Destinataires possibles d'un type, une ligne par adresse."""
    q = (q or "").strip().lower()
    out: list[dict] = []

    def garder(*textes) -> bool:
        return not q or q in " ".join(t or "" for t in textes).lower()

    if type_ == "fournisseur":
        fours = conn.execute(
            """SELECT id, nom, email FROM fournisseurs_fsc
                WHERE COALESCE(actif, 1) = 1 AND fusionne_dans IS NULL
                ORDER BY nom COLLATE NOCASE"""
        ).fetchall()
        contacts: dict[int, list] = {}
        for c in conn.execute(
            """SELECT fournisseur_id, nom, emails, is_principal FROM fournisseur_contacts
                WHERE COALESCE(actif, 1) = 1 ORDER BY is_principal DESC, id"""
        ).fetchall():
            contacts.setdefault(int(c["fournisseur_id"]), []).append(c)
        for f in fours:
            vus = set()
            for c in contacts.get(int(f["id"]), []):
                for e in _emails_json(c["emails"]):
                    if e not in vus and garder(f["nom"], c["nom"], e):
                        vus.add(e)
                        out.append({"type": "fournisseur", "ref_id": f["id"], "organisation": f["nom"],
                                    "nom": c["nom"] or "", "email": e})
            for e in _emails_json(f["email"]):
                if e not in vus and garder(f["nom"], e):
                    vus.add(e)
                    out.append({"type": "fournisseur", "ref_id": f["id"], "organisation": f["nom"],
                                "nom": "", "email": e})
    elif type_ == "client":
        tiers = conn.execute(
            """SELECT id, raison_sociale, nom_court, email FROM gc_tiers
                WHERE est_client = 1 AND COALESCE(actif, 1) = 1
                ORDER BY raison_sociale COLLATE NOCASE"""
        ).fetchall()
        contacts = {}
        for c in conn.execute(
            """SELECT tiers_id, nom, email FROM gc_tiers_contacts
                WHERE COALESCE(actif, 1) = 1 AND COALESCE(email, '') != '' ORDER BY id"""
        ).fetchall():
            contacts.setdefault(int(c["tiers_id"]), []).append(c)
        for t in tiers:
            org = t["raison_sociale"] or t["nom_court"] or ""
            vus = set()
            for c in contacts.get(int(t["id"]), []):
                e = portail_espace.normaliser_email(c["email"])
                if e and e not in vus and garder(org, c["nom"], e):
                    vus.add(e)
                    out.append({"type": "client", "ref_id": t["id"], "organisation": org,
                                "nom": c["nom"] or "", "email": e})
            e = portail_espace.normaliser_email(t["email"] or "")
            if e and e not in vus and garder(org, e):
                out.append({"type": "client", "ref_id": t["id"], "organisation": org, "nom": "", "email": e})
    elif type_ == "personnel":
        for u in conn.execute(
            "SELECT id, nom, email, role FROM users WHERE actif = 1 ORDER BY nom COLLATE NOCASE"
        ).fetchall():
            e = portail_espace.normaliser_email(u["email"] or "")
            if e and garder(u["nom"], e):
                out.append({"type": "personnel", "ref_id": u["id"], "organisation": APP_ORG_NAME,
                            "nom": u["nom"] or "", "email": e})
    return out[:500]


# ── Envoi ───────────────────────────────────────────────────────────────

def _echeance(v: Any) -> Optional[str]:
    s = str(v or "").strip()[:10]
    if not s:
        return None
    try:
        d = date.fromisoformat(s)
    except ValueError:
        raise ValueError("Échéance invalide — format AAAA-MM-JJ.")
    if d < date.today():
        raise ValueError("Échéance dans le passé.")
    return d.isoformat()


def creer_envoi(conn, formulaire_id: int, destinataires: list[dict], *, message: str = "",
                echeance: Any = None, auteur: str | None, auteur_email: str | None) -> dict:
    """Crée l'envoi et ses destinataires (sans envoyer d'email). Rend
    {"envoi_id", "destinataires": [ids], "ignores": [emails déjà destinataires]}."""
    f = conn.execute("SELECT * FROM qualite_formulaires WHERE id = ?", (formulaire_id,)).fetchone()
    if not f:
        raise LookupError("Formulaire introuvable.")
    if f["statut"] == "archive":
        raise ValueError("Formulaire archivé — le restaurer avant de l'envoyer.")
    if not int(f["version_courante"] or 0):
        raise ValueError("Formulaire jamais publié — le publier avant de l'envoyer.")
    v = conn.execute(
        "SELECT titre FROM qualite_formulaires_versions WHERE formulaire_id = ? AND numero = ?",
        (formulaire_id, f["version_courante"]),
    ).fetchone()
    propres: list[dict] = []
    vus = set()
    for d in destinataires or []:
        if not isinstance(d, dict):
            continue
        e = portail_espace.normaliser_email(str(d.get("email") or ""))
        t = d.get("type") if d.get("type") in TYPES_DESTINATAIRE else "libre"
        if not e or e in vus:
            continue
        vus.add(e)
        ref = d.get("ref_id")
        propres.append({"type": t, "ref_id": int(ref) if str(ref or "").isdigit() else None,
                        "nom": str(d.get("nom") or "")[:200], "organisation": str(d.get("organisation") or "")[:200],
                        "email": e})
    if not propres:
        raise ValueError("Aucun destinataire valide.")
    if len(propres) > MAX_DESTINATAIRES:
        raise ValueError(f"{MAX_DESTINATAIRES} destinataires au plus par envoi.")
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO qualite_formulaires_envois
             (formulaire_id, version, titre, description, message, echeance, cree_par, cree_par_email, cree_le)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (formulaire_id, f["version_courante"], (v["titre"] if v else f["titre"]), f["description"] or "",
         (message or "").strip()[:2000], _echeance(echeance), auteur, auteur_email, now),
    )
    envoi_id = int(cur.lastrowid)
    ids = []
    for d in propres:
        portail_espace.espace_pour(conn, d["email"], d["nom"] or d["organisation"])
        user_id = d["ref_id"] if d["type"] == "personnel" else None
        cur = conn.execute(
            """INSERT INTO qualite_formulaires_destinataires
                 (envoi_id, type, ref_id, nom, organisation, email, user_id, statut)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'envoye')""",
            (envoi_id, d["type"], d["ref_id"], d["nom"], d["organisation"], d["email"], user_id),
        )
        ids.append(int(cur.lastrowid))
    return {"envoi_id": envoi_id, "destinataires": ids}


def destinataire(conn, dest_id: int) -> dict | None:
    r = conn.execute(
        """SELECT d.*, e.formulaire_id, e.version, e.titre, e.description, e.message, e.echeance,
                  e.cree_par, e.cree_par_email, e.cree_le AS envoi_cree_le, f.statut AS formulaire_statut
             FROM qualite_formulaires_destinataires d
             JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
             JOIN qualite_formulaires f ON f.id = e.formulaire_id
            WHERE d.id = ?""",
        (dest_id,),
    ).fetchone()
    return dict(r) if r else None


def _date_fr(iso: str | None) -> str:
    if not iso:
        return ""
    p = str(iso)[:10].split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else str(iso)


def email_invitation(dest: dict, *, url: str, relance: bool) -> tuple[str, str]:
    """Sujet et corps HTML de l'invitation (ou de la relance), marque SIFA."""
    from app.services.email_service import _email_bouton, _email_detail_table, _esc, email_mysifa_layout

    org = APP_ORG_NAME
    salut = f"Bonjour {dest['nom']}," if dest.get("nom") else "Bonjour,"
    intro = (f"{_esc(dest.get('cree_par') or org)} vous invite à compléter le formulaire "
             f"<strong style=\"color:#0f172a\">« {_esc(dest['titre'])} »</strong>.")
    if relance:
        intro = "Rappel : votre réponse est toujours attendue. " + intro
    lignes = [("Formulaire", _esc(dest["titre"]))]
    if dest.get("echeance"):
        lignes.append(("Réponse attendue avant le", _esc(_date_fr(dest["echeance"]))))
    message = ""
    if (dest.get("message") or "").strip():
        message = ('<p style="margin:0 0 18px;padding:12px 14px;border-left:3px solid #0891b2;'
                   'background:#f1f5f9;font-size:14px;color:#334155;line-height:1.6;white-space:pre-wrap">'
                   + _esc(dest["message"].strip()) + "</p>")
    inner = f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">{_esc(salut)}</p>
    <p style="margin:0 0 18px;font-size:14px;color:#475569;line-height:1.65">{intro}</p>
    {message}
    {_email_detail_table(lignes)}
    <p style="margin:18px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      Toutes les demandes que {_esc(org)} vous adresse sont réunies dans votre espace personnel.
    </p>
    {_email_bouton(url, "Ouvrir mon espace " + org, "Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :")}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      Cordialement,<br>
      <strong style="color:#0f172a;font-size:14px">{_esc(dest.get('cree_par') or org)}</strong><br>{_esc(org)}
    </p>"""
    corps = email_mysifa_layout(
        subtitle=dest["titre"][:120],
        body_html=inner,
        footer_note=f"Ce lien est personnel : il ouvre votre espace {org}. Merci de ne pas le transférer.",
        footer_contact=True,
        marque=org,
    )
    sujet = ("Rappel : " if relance else "") + f"{dest['titre']} — {org}"
    return sujet[:200], corps


def url_destinataire(conn, dest: dict) -> str:
    esp = portail_espace.espace_pour(conn, dest["email"], dest.get("nom") or "")
    return f"{portail_espace.url_espace(esp['token'])}?formulaire={dest['id']}"


def noter_envoi(conn, dest_id: int) -> None:
    conn.execute(
        """UPDATE qualite_formulaires_destinataires
              SET nb_envois = nb_envois + 1, envoye_le = ?
            WHERE id = ?""",
        (_maintenant(), dest_id),
    )


def noter_ouverture(conn, dest_id: int) -> None:
    conn.execute(
        """UPDATE qualite_formulaires_destinataires
              SET ouvert_le = COALESCE(ouvert_le, ?),
                  statut = CASE WHEN statut = 'envoye' THEN 'ouvert' ELSE statut END
            WHERE id = ?""",
        (_maintenant(), dest_id),
    )


# ── Réponses ────────────────────────────────────────────────────────────

def schema_envoi(conn, dest: dict) -> dict:
    v = conn.execute(
        "SELECT schema_json FROM qualite_formulaires_versions WHERE formulaire_id = ? AND numero = ?",
        (dest["formulaire_id"], dest["version"]),
    ).fetchone()
    return normaliser_schema(v["schema_json"] if v else "{}")


def _num(x: Any) -> Optional[float]:
    try:
        f = float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def nettoyer_reponses(schema: dict, brutes: Any) -> tuple[dict, list[str]]:
    """Garde les réponses aux questions du formulaire, au bon format.
    Rend (réponses, libellés des questions obligatoires sans réponse)."""
    brutes = brutes if isinstance(brutes, dict) else {}
    out: dict[str, Any] = {}
    manquantes: list[str] = []
    for s in schema["sections"]:
        for q in s["questions"]:
            qid, t, r = q["id"], q["type"], brutes.get(q["id"])
            val: Any = None
            if t == "value" and q.get("points_libres"):
                # Nombre libre : les lignes laissées vides sont ignorées.
                vals = [v for v in (_num(x) for x in (r if isinstance(r, list) else [r])) if v is not None]
                vals = vals[: int(q.get("max_points") or 50)]
                if q.get("required") and len(vals) < max(1, int(q.get("min_points") or 1)):
                    manquantes.append(q["label"])
                    continue
                val = vals or None
            elif t == "value":
                if isinstance(r, list) and len(q.get("points") or []) > 1:
                    vals = [_num(x) for x in r[: len(q["points"])]]
                    vals += [None] * (len(q["points"]) - len(vals))
                    val = vals if any(v is not None for v in vals) else None
                    if q.get("required") and (val is None or any(v is None for v in vals)):
                        manquantes.append(q["label"])
                        continue
                else:
                    val = _num(r)
            elif t == "choice":
                permis = list(q.get("responses") or []) + (["Autre"] if q.get("allow_other") else [])
                choix = [str(x) for x in (r if isinstance(r, list) else [r]) if str(x or "") in permis]
                if not q.get("multi"):
                    choix = choix[:1]
                val = choix or None
                autre = brutes.get(qid + "_other")
                if val and "Autre" in val and isinstance(autre, str) and autre.strip():
                    out[qid + "_other"] = autre.strip()[:500]
            elif t == "scale":
                n = _num(r)
                if n is not None and q.get("min", 1) <= n <= q.get("max", 5) and n == int(n):
                    val = int(n)
            elif t == "date":
                try:
                    val = date.fromisoformat(str(r or "")[:10]).isoformat()
                except ValueError:
                    val = None
            else:
                val = str(r).strip()[: (5000 if q.get("long") else 1000)] if isinstance(r, str) and r.strip() else None
            if val is None:
                if q.get("required"):
                    manquantes.append(q["label"])
                continue
            out[qid] = val
    return out, manquantes


def non_conformites(schema: dict, reponses: dict) -> list[str]:
    """Identifiants des questions dont la réponse signale une non-conformité :
    réponse marquée NC, « Autre » marqué NC, ou mesure hors tolérance quand la
    question le demande."""
    nc = []
    for s in schema["sections"]:
        for q in s["questions"]:
            r = reponses.get(q["id"])
            if r is None:
                continue
            if q["type"] == "choice":
                sel = r if isinstance(r, list) else [r]
                if any(x in (q.get("nc_responses") or []) for x in sel) or (q.get("other_is_nc") and "Autre" in sel):
                    nc.append(q["id"])
            elif q["type"] == "value" and q.get("out_of_range_is_nc"):
                for x in (r if isinstance(r, list) else [r]):
                    n = _num(x)
                    if n is None:
                        continue
                    if (q.get("min") is not None and n < q["min"]) or (q.get("max") is not None and n > q["max"]):
                        nc.append(q["id"])
                        break
    return nc


def enregistrer_reponse(conn, dest: dict, reponses: dict, *, repondant_nom: str, ip: str) -> int:
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO qualite_formulaires_reponses
             (destinataire_id, reponses_json, repondant_nom, soumis_le, ip)
           VALUES (?, ?, ?, ?, ?)""",
        (dest["id"], json.dumps(reponses, ensure_ascii=False), (repondant_nom or "").strip()[:200], now, (ip or "")[:64]),
    )
    conn.execute(
        """UPDATE qualite_formulaires_destinataires
              SET statut = 'repondu', repondu_le = ?, ouvert_le = COALESCE(ouvert_le, ?)
            WHERE id = ?""",
        (now, now, dest["id"]),
    )
    # Destinataire du personnel : sa tâche « formulaire à remplir » est faite.
    if dest.get("tache_id"):
        try:
            conn.execute(
                """UPDATE taches SET statut = 'termine', done_at = COALESCE(done_at, ?), updated_at = ?
                    WHERE id = ? AND deleted_at IS NULL""",
                (now, now, dest["tache_id"]),
            )
        except Exception:
            pass
    return int(cur.lastrowid)


def derniere_reponse(conn, dest_id: int) -> dict | None:
    r = conn.execute(
        """SELECT * FROM qualite_formulaires_reponses WHERE destinataire_id = ?
            ORDER BY id DESC LIMIT 1""",
        (dest_id,),
    ).fetchone()
    if not r:
        return None
    d = dict(r)
    try:
        d["reponses"] = json.loads(d.pop("reponses_json") or "{}")
    except ValueError:
        d["reponses"] = {}
    d["nb_versions"] = conn.execute(
        "SELECT COUNT(*) FROM qualite_formulaires_reponses WHERE destinataire_id = ?", (dest_id,)
    ).fetchone()[0]
    return d


# ── Suivi interne ───────────────────────────────────────────────────────

def suivi(conn, formulaire_id: int) -> list[dict]:
    envois = [dict(r) for r in conn.execute(
        "SELECT * FROM qualite_formulaires_envois WHERE formulaire_id = ? ORDER BY id DESC",
        (formulaire_id,),
    ).fetchall()]
    for e in envois:
        dests = [dict(r) for r in conn.execute(
            """SELECT id, type, ref_id, nom, organisation, email, statut, nb_envois,
                      envoye_le, ouvert_le, repondu_le, actif
                 FROM qualite_formulaires_destinataires WHERE envoi_id = ?
                ORDER BY organisation COLLATE NOCASE, nom COLLATE NOCASE, email""",
            (e["id"],),
        ).fetchall()]
        schema = None
        for d in dests:
            d["nb_nc"] = 0
            if d["statut"] == "repondu":
                rep = derniere_reponse(conn, d["id"])
                if rep:
                    if schema is None:
                        schema = schema_envoi(conn, {"formulaire_id": formulaire_id, "version": e["version"]})
                    d["nb_nc"] = len(non_conformites(schema, rep["reponses"]))
        e["destinataires"] = dests
        actifs = [d for d in dests if d["actif"]]
        e["nb"] = len(actifs)
        e["nb_repondus"] = sum(1 for d in actifs if d["statut"] == "repondu")
        e["nb_ouverts"] = sum(1 for d in actifs if d["statut"] in ("ouvert", "repondu"))
    return envois
