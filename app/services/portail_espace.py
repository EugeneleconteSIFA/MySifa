"""Espace SIFA — le portail unique d'un destinataire externe.

Décision du 20/10/2026 : tout ce qu'un tiers reçoit de SIFA se retrouve au
même endroit. Un Espace par adresse email (seule clé commune aux modules),
ouvert par un lien personnel `/portail/{jeton}` sans code.

Ce que l'Espace réunit :
  - les formulaires de MyQualité (natifs : remplis dans l'Espace) ;
  - les appels d'offres MyAO, les demandes de devis transport et la taxe
    carburant, le questionnaire EUDR : des cartes qui ouvrent les pages
    existantes de chaque module, en attendant leur intégration complète. Les
    liens déjà envoyés par ces modules restent valables.

Chaque module est lu dans son propre `try` : une table absente ou une requête
en échec retire sa carte, jamais l'Espace entier.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from config import public_base_url

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _maintenant() -> str:
    return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")


def normaliser_email(email: str) -> str:
    e = (email or "").strip().lower()
    return e if _EMAIL.match(e) and len(e) <= 254 else ""


def url_espace(token: str) -> str:
    return f"{public_base_url()}/portail/{token}"


def espace_pour(conn, email: str, nom: str = "") -> dict:
    """L'Espace de cette adresse, créé au premier envoi. Lève ValueError si
    l'adresse n'est pas valide."""
    mail = normaliser_email(email)
    if not mail:
        raise ValueError(f"Adresse invalide : {email!r}")
    r = conn.execute("SELECT * FROM portail_espaces WHERE email = ?", (mail,)).fetchone()
    if r:
        if nom and not r["nom"]:
            conn.execute("UPDATE portail_espaces SET nom = ? WHERE id = ?", (nom[:200], r["id"]))
        return dict(r)
    token = secrets.token_urlsafe(24)
    while conn.execute("SELECT 1 FROM portail_espaces WHERE token = ?", (token,)).fetchone():
        token = secrets.token_urlsafe(24)
    cur = conn.execute(
        "INSERT INTO portail_espaces (email, token, nom, actif, cree_le) VALUES (?, ?, ?, 1, ?)",
        (mail, token, (nom or "")[:200], _maintenant()),
    )
    return dict(conn.execute("SELECT * FROM portail_espaces WHERE id = ?", (cur.lastrowid,)).fetchone())


def lire_par_token(conn, token: str) -> dict | None:
    if not token or len(token) > 100:
        return None
    r = conn.execute("SELECT * FROM portail_espaces WHERE token = ? AND actif = 1", (token,)).fetchone()
    return dict(r) if r else None


def noter_acces(conn, espace: dict, ip: str) -> None:
    conn.execute(
        "UPDATE portail_espaces SET dernier_acces_le = ?, dernier_acces_ip = ? WHERE id = ?",
        (_maintenant(), (ip or "")[:64], espace["id"]),
    )


# ── Contenu de l'Espace ─────────────────────────────────────────────────

def _formulaires(conn, email: str) -> list[dict]:
    rows = conn.execute(
        """SELECT d.id, d.statut, d.envoye_le, d.ouvert_le, d.repondu_le,
                  e.titre, e.description, e.echeance, e.cree_par, e.cree_le
             FROM qualite_formulaires_destinataires d
             JOIN qualite_formulaires_envois e ON e.id = d.envoi_id
             JOIN qualite_formulaires f ON f.id = e.formulaire_id
            WHERE d.email = ? AND d.actif = 1 AND f.statut != 'archive'
            ORDER BY e.cree_le DESC
            LIMIT 200""",
        (email,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        out.append({
            "module": "formulaire", "id": d["id"], "titre": d["titre"],
            "detail": d["description"][:240], "echeance": d["echeance"],
            "envoye_le": d["envoye_le"], "de": d["cree_par"],
            "a_traiter": d["statut"] != "repondu", "statut": d["statut"],
            "repondu_le": d["repondu_le"],
        })
    return out


def _appels_offres(conn, email: str) -> list[dict]:
    rows = conn.execute(
        """SELECT f.token, f.statut AS f_statut, f.date_envoi, f.date_reponse,
                  d.reference, d.titre, d.date_limite, d.statut AS ao_statut
             FROM ao_fournisseurs f
             JOIN ao_demandes d ON d.id = f.ao_id
            WHERE LOWER(TRIM(COALESCE(f.email_contact, ''))) = ?
              AND d.deleted_at IS NULL
              AND (d.statut IN ('envoyee', 'cloturee') OR f.date_envoi IS NOT NULL)
            ORDER BY COALESCE(f.date_envoi, d.date_creation) DESC
            LIMIT 100""",
        (email,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        out.append({
            "module": "ao", "titre": d["titre"] or "Appel d'offres",
            "detail": "Référence " + (d["reference"] or ""), "echeance": d["date_limite"],
            "envoye_le": d["date_envoi"],
            "a_traiter": d["ao_statut"] == "envoyee" and d["f_statut"] != "repondu",
            "statut": d["f_statut"], "repondu_le": d["date_reponse"],
            "url": f"{public_base_url()}/portail/ao/{d['token']}",
        })
    return out


def _devis_transport(conn, email: str) -> list[dict]:
    acc = conn.execute(
        "SELECT token FROM expe_portal_transporteurs WHERE LOWER(TRIM(email)) = ? AND actif = 1",
        (email,),
    ).fetchone()
    if not acc:
        return []
    n = conn.execute(
        """SELECT COUNT(DISTINCT d.id) FROM expe_devis_reponses r
             JOIN expe_demandes_devis d ON d.id = r.demande_id
            WHERE d.deleted_at IS NULL AND d.statut = 'ouverte'
              AND LOWER(TRIM(COALESCE(r.destinataire_email, ''))) = ?
              AND r.statut IN ('envoyee', 'ouvert', 'echec')""",
        (email,),
    ).fetchone()[0]
    return [{
        "module": "expe", "titre": "Demandes de devis transport",
        "detail": (f"{n} demande(s) en attente de votre offre" if n else "Aucune demande en attente")
                  + " · taxe carburant",
        "a_traiter": bool(n), "statut": "a_repondre" if n else "a_jour",
        "url": f"{public_base_url()}/portail/expe/{acc['token']}",
    }]


def _eudr(conn, email: str) -> list[dict]:
    rows = conn.execute(
        """SELECT token, statut, envoye_le, repondu_le FROM eudr_demandes
            WHERE LOWER(TRIM(email)) = ? AND actif = 1
            ORDER BY id DESC LIMIT 5""",
        (email,),
    ).fetchall()
    return [{
        "module": "eudr", "titre": "Questionnaire EUDR",
        "detail": "Règlement européen sur la déforestation",
        "envoye_le": r["envoye_le"], "a_traiter": not r["repondu_le"],
        "statut": r["statut"], "repondu_le": r["repondu_le"],
        "url": f"{public_base_url()}/portail/eudr/{r['token']}",
    } for r in rows]


def contenu(conn, email: str) -> dict:
    """Tout ce qui attend cette adresse : formulaires et cartes des autres
    modules, chacun avec `a_traiter`."""
    mail = normaliser_email(email)
    elements: list[dict] = []
    for lecteur in (_formulaires, _appels_offres, _devis_transport, _eudr):
        try:
            elements.extend(lecteur(conn, mail))
        except Exception:
            # Module absent de cette instance ou table en cours de migration :
            # sa carte manque, le reste de l'Espace s'affiche.
            continue
    return {
        "a_traiter": [e for e in elements if e.get("a_traiter")],
        "traites": [e for e in elements if not e.get("a_traiter")],
    }
