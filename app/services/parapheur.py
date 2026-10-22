"""MyTools › Parapheur — circuit de signature d'un PDF.

Une demande part avec ses signataires ordonnés :
  - séquentiel : un signataire à la fois, dans l'ordre ; le suivant est
    prévenu quand le précédent a signé ;
  - parallèle : tous prévenus d'emblée.
Un refus arrête la demande ; l'échéance dépassée l'expire. Quand le dernier a
signé, le document final est scellé (`parapheur_pdf.py`).

Signataire interne (utilisateur MySifa) : tâche dans le gestionnaire, push et
email, il signe dans MyTools. Signataire externe : son Espace SIFA
(`portail_espace.py`, décision du 20/10/2026), avec un lien de signature
propre — jeton aléatoire dont seule l'empreinte est gardée, durée et nombre de
consultations limités, révoqué dès qu'il a répondu. Le jeton voyage dans le
fragment de l'adresse (`#signer=`), jamais dans la query : il ne passe ni dans
les journaux du serveur, ni dans les réponses de l'API.

Droits (revérifiés par l'API, `app/routers/tools_parapheur.py`) :
  voir    auteur, signataire interne, ROLES_PARAPHEUR_SUPERVISION
  gérer   auteur et ROLES_PARAPHEUR_SUPERVISION (relancer, annuler)
  créer   ROLES_PARAPHEUR_CREATION
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import struct
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.services import email_service
from app.services import parapheur_pdf as ppdf
from app.services import portail_espace
from config import (
    APP_ORG_NAME,
    PARAPHEUR_DIR,
    PARAPHEUR_ECHEANCE_JOURS,
    PARAPHEUR_JETON_JOURS,
    PARAPHEUR_JETON_USAGES,
    PARAPHEUR_LIENS_PAR_JOUR,
    PARAPHEUR_NIVEAU,
    PARAPHEUR_RELANCE_JOURS,
    PARAPHEUR_RELANCES_MAX,
    PARAPHEUR_SIGNATAIRES_MAX,
    PARAPHEUR_TAILLE_MAX_MO,
    ROLES_PARAPHEUR_CREATION,
    ROLES_PARAPHEUR_SUPERVISION,
    public_base_url,
)

_PARIS = ZoneInfo("Europe/Paris")
MODES = ("sequentiel", "parallele")
STATUTS = ("en_cours", "signee", "refusee", "expiree", "annulee")
FILTRES = ("a_signer", "en_cours", "signee", "refusee", "expiree", "annulee", "toutes")
EN_ATTENTE_SIG = ("a_signer", "ouvert")
PNG_MAX_OCTETS = 600 * 1024
LIBELLES_EVENEMENT = {
    "creation": "Demande créée", "envoi": "Invitation envoyée", "relance": "Relance envoyée",
    "echec_envoi": "Échec d'envoi", "ouverture": "Document consulté", "signature": "Signé",
    "refus": "Refusé", "annulation": "Demande annulée", "expiration": "Échéance dépassée",
    "scelle": "Document scellé", "telechargement": "Document téléchargé", "lien": "Nouveau lien demandé",
}


class Refus(Exception):
    """Refus métier : `code` HTTP et message affichable."""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def maintenant() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _dt(s: str | None) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(s)[:19]) if s else None
    except ValueError:
        return None


def sha256(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def _empreinte_jeton(jeton: str) -> str:
    return hashlib.sha256(("parapheur:" + (jeton or "")).encode("utf-8")).hexdigest()


# ── Droits ──────────────────────────────────────────────────────────────

def _role(user: dict) -> str:
    try:
        from app.services.auth_service import effective_role
        return effective_role(user) or ""
    except Exception:
        return (user or {}).get("role") or ""


def peut_creer(user: dict) -> bool:
    return _role(user) in ROLES_PARAPHEUR_CREATION


def supervise(user: dict) -> bool:
    return _role(user) in ROLES_PARAPHEUR_SUPERVISION


def peut_gerer(user: dict, d: dict) -> bool:
    return supervise(user) or (d.get("cree_par_id") is not None and int(d["cree_par_id"]) == int(user.get("id") or -1))


def peut_voir(user: dict, d: dict, sigs: list[dict]) -> bool:
    uid = int(user.get("id") or -1)
    return peut_gerer(user, d) or any(s.get("user_id") is not None and int(s["user_id"]) == uid for s in sigs)


# ── Fichiers ────────────────────────────────────────────────────────────

def _chemin(nom: str) -> str:
    base = os.path.basename(nom or "")
    if not base or base != nom or not base.endswith(".pdf"):
        raise Refus("Fichier introuvable.", 404)
    return os.path.join(PARAPHEUR_DIR, base)


def _ecrire(octets: bytes) -> str:
    os.makedirs(PARAPHEUR_DIR, exist_ok=True)
    nom = uuid.uuid4().hex + ".pdf"
    with open(os.path.join(PARAPHEUR_DIR, nom), "wb") as f:
        f.write(octets)
    return nom


def lire_fichier(nom: str) -> bytes:
    p = _chemin(nom)
    if not os.path.isfile(p):
        raise Refus("Fichier introuvable.", 404)
    with open(p, "rb") as f:
        return f.read()


def nom_telechargement(d: dict, final: bool) -> str:
    base = os.path.splitext(d.get("nom_fichier") or "document")[0]
    base = "".join(ch if ch.isalnum() or ch in " -_." else "_" for ch in base).strip() or "document"
    return f"{base[:80]}{' - signé' if final else ''}.pdf"


# ── Lecture ─────────────────────────────────────────────────────────────

def demande(conn, did: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM parapheur_demandes WHERE id = ?", (did,)).fetchone()
    return dict(r) if r else None


def signataires(conn, did: int, *, avec_images: bool = False) -> list[dict]:
    cols = "*" if avec_images else (
        "id, demande_id, ordre, type, user_id, nom, email, organisation, statut, notifie_le, ouvert_le, "
        "signe_le, refuse_le, motif_refus, ip, mode_signature, nom_saisi, nb_relances, relance_le, tache_id")
    return [dict(r) for r in conn.execute(
        f"SELECT {cols} FROM parapheur_signataires WHERE demande_id = ? ORDER BY ordre, id", (did,)).fetchall()]


def signataire(conn, sid: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM parapheur_signataires WHERE id = ?", (sid,)).fetchone()
    return dict(r) if r else None


def zones(conn, did: int, sid: int | None = None) -> list[dict]:
    q = "SELECT id, signataire_id, page, type, x, y, w, h FROM parapheur_zones WHERE demande_id = ?"
    args: list[Any] = [did]
    if sid is not None:
        q += " AND signataire_id = ?"
        args.append(sid)
    return [dict(r) for r in conn.execute(q + " ORDER BY page, y, x", args).fetchall()]


def evenements(conn, did: int) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM parapheur_evenements WHERE demande_id = ? ORDER BY le, id", (did,)).fetchall():
        e = dict(r)
        e["libelle"] = LIBELLES_EVENEMENT.get(e["type"], e["type"])
        out.append(e)
    return out


def evenement(conn, did: int, type_: str, *, sid: int | None = None, acteur: str = "", ip: str = "",
              detail: str = "") -> None:
    conn.execute(
        "INSERT INTO parapheur_evenements (demande_id, signataire_id, le, type, acteur, ip, detail) VALUES (?,?,?,?,?,?,?)",
        (did, sid, maintenant(), type_, (acteur or "")[:200], (ip or "")[:64] or None, (detail or "")[:500]),
    )


def _public_sig(s: dict, *, avec_ip: bool) -> dict:
    out = {k: s.get(k) for k in ("id", "ordre", "type", "user_id", "nom", "email", "organisation", "statut",
                                 "notifie_le", "ouvert_le", "signe_le", "refuse_le", "motif_refus",
                                 "mode_signature", "nb_relances", "relance_le")}
    if avec_ip:
        out["ip"] = s.get("ip")
    return out


def _public_demande(d: dict) -> dict:
    return {k: d.get(k) for k in ("id", "titre", "message", "mode", "statut", "echeance", "relance_jours",
                                  "nom_fichier", "sha256_original", "taille_original", "nb_pages",
                                  "sha256_signe", "sha256_final", "niveau", "cree_par_id", "cree_par_nom",
                                  "cree_par_email", "cree_le", "termine_le", "motif_fin")} | {
        "final_disponible": bool(d.get("fichier_final"))}


def detail(conn, did: int, user: dict) -> dict:
    d = demande(conn, did)
    if not d:
        raise Refus("Demande introuvable.", 404)
    sigs = signataires(conn, did)
    if not peut_voir(user, d, sigs):
        raise Refus("Accès refusé à cette demande.", 403)
    gere = peut_gerer(user, d)
    uid = int(user.get("id") or -1)
    moi = next((s for s in sigs if s.get("user_id") is not None and int(s["user_id"]) == uid
                and s["statut"] in EN_ATTENTE_SIG), None)
    return {
        "demande": _public_demande(d),
        "signataires": [_public_sig(s, avec_ip=gere) for s in sigs],
        "zones": zones(conn, did),
        "evenements": evenements(conn, did) if gere else [],
        "droits": {"gerer": gere and d["statut"] == "en_cours", "telecharger": True},
        "moi": ({"signataire_id": moi["id"], "peut_signer": d["statut"] == "en_cours"} if moi else None),
    }


def liste(conn, user: dict, filtre: str = "en_cours") -> dict:
    uid = int(user.get("id") or -1)
    if supervise(user):
        base, args = "1=1", []
    else:
        base = "(d.cree_par_id = ? OR d.id IN (SELECT demande_id FROM parapheur_signataires WHERE user_id = ?))"
        args = [uid, uid]
    rows = [dict(r) for r in conn.execute(
        f"""SELECT d.id, d.titre, d.nom_fichier, d.mode, d.statut, d.echeance, d.cree_par_id, d.cree_par_nom,
                   d.cree_le, d.termine_le,
                   (SELECT COUNT(*) FROM parapheur_signataires s WHERE s.demande_id = d.id) AS nb,
                   (SELECT COUNT(*) FROM parapheur_signataires s WHERE s.demande_id = d.id AND s.statut = 'signe') AS nb_signes,
                   (SELECT s.statut FROM parapheur_signataires s WHERE s.demande_id = d.id AND s.user_id = ?
                     ORDER BY s.ordre LIMIT 1) AS mon_statut
              FROM parapheur_demandes d WHERE {base}
             ORDER BY d.id DESC LIMIT 500""", [uid] + args).fetchall()]
    attente: dict[int, list[str]] = {}
    ids = [r["id"] for r in rows if r["statut"] == "en_cours"]
    if ids:
        marques = ",".join("?" * len(ids))
        for s in conn.execute(
                f"""SELECT demande_id, nom, email, organisation FROM parapheur_signataires
                     WHERE demande_id IN ({marques}) AND statut IN ('a_signer', 'ouvert') ORDER BY ordre""", ids):
            attente.setdefault(s["demande_id"], []).append(s["nom"] or s["organisation"] or s["email"])
    for r in rows:
        r["en_attente_de"] = attente.get(r["id"], [])
        r["a_signer"] = r["statut"] == "en_cours" and r["mon_statut"] in EN_ATTENTE_SIG
    compteurs = {f: 0 for f in FILTRES}
    for r in rows:
        compteurs["toutes"] += 1
        compteurs[r["statut"]] = compteurs.get(r["statut"], 0) + 1
        if r["a_signer"]:
            compteurs["a_signer"] += 1
    if filtre == "a_signer":
        rows = [r for r in rows if r["a_signer"]]
    elif filtre in STATUTS:
        rows = [r for r in rows if r["statut"] == filtre]
    return {"demandes": rows, "compteurs": compteurs, "filtre": filtre}


def ma_signature(conn, user_id: int) -> Optional[str]:
    r = conn.execute(
        """SELECT signature_png FROM parapheur_signataires
            WHERE user_id = ? AND signature_png IS NOT NULL ORDER BY signe_le DESC LIMIT 1""", (user_id,)).fetchone()
    if not r or not r["signature_png"]:
        return None
    return "data:image/png;base64," + base64.b64encode(r["signature_png"]).decode("ascii")


# ── Création ────────────────────────────────────────────────────────────

def _echeance(v: Any) -> str:
    s = str(v or "").strip()[:10]
    if not s:
        return (date.today() + timedelta(days=PARAPHEUR_ECHEANCE_JOURS)).isoformat()
    try:
        d = date.fromisoformat(s)
    except ValueError:
        raise Refus("Échéance invalide — format AAAA-MM-JJ.")
    if d < date.today():
        raise Refus("Échéance dans le passé.")
    if d > date.today() + timedelta(days=366):
        raise Refus("Échéance trop lointaine — un an au plus.")
    return d.isoformat()


def _signataires_propres(conn, brut: Any) -> list[dict]:
    if not isinstance(brut, list) or not brut:
        raise Refus("Ajouter au moins un signataire.")
    if len(brut) > PARAPHEUR_SIGNATAIRES_MAX:
        raise Refus(f"{PARAPHEUR_SIGNATAIRES_MAX} signataires au plus.")
    out, vus_users, vus_mails = [], set(), set()
    for i, s in enumerate(brut):
        if not isinstance(s, dict):
            raise Refus(f"Signataire {i + 1} invalide.")
        if s.get("type") == "interne":
            try:
                uid = int(s.get("user_id"))
            except (TypeError, ValueError):
                raise Refus(f"Signataire {i + 1} : utilisateur inconnu.")
            u = conn.execute("SELECT id, nom, email FROM users WHERE id = ? AND actif = 1", (uid,)).fetchone()
            if not u:
                raise Refus(f"Signataire {i + 1} : utilisateur inconnu ou désactivé.")
            if uid in vus_users:
                raise Refus(f"{u['nom']} figure deux fois parmi les signataires.")
            vus_users.add(uid)
            mail = portail_espace.normaliser_email(u["email"] or "")
            out.append({"type": "interne", "user_id": uid, "nom": (u["nom"] or "")[:200], "email": mail,
                        "organisation": APP_ORG_NAME})
        else:
            mail = portail_espace.normaliser_email(str(s.get("email") or ""))
            if not mail:
                raise Refus(f"Signataire {i + 1} : adresse email invalide.")
            if mail in vus_mails:
                raise Refus(f"{mail} figure deux fois parmi les signataires.")
            vus_mails.add(mail)
            nom = str(s.get("nom") or "").strip()[:200]
            if not nom:
                raise Refus(f"Signataire {i + 1} : nom obligatoire (il figure sur le certificat).")
            out.append({"type": "externe", "user_id": None, "nom": nom, "email": mail,
                        "organisation": str(s.get("organisation") or "").strip()[:200]})
    return out


def _zones_propres(brut: Any, nb_sig: int, dims: list[dict]) -> list[dict]:
    if not isinstance(brut, list):
        raise Refus("Zones invalides.")
    out = []
    for z in brut[:500]:
        if not isinstance(z, dict):
            continue
        try:
            i = int(z.get("signataire"))
            page = int(z.get("page"))
            x, y, w, h = (float(z.get(k)) for k in ("x", "y", "w", "h"))
        except (TypeError, ValueError):
            raise Refus("Zone invalide.")
        t = z.get("type")
        if t not in ppdf.TYPES_ZONE or not (0 <= i < nb_sig) or not (1 <= page <= len(dims)):
            raise Refus("Zone invalide.")
        if not all(v == v for v in (x, y, w, h)) or w < 0.005 or h < 0.003 or x < -0.001 or y < -0.001 \
                or x + w > 1.001 or y + h > 1.001:
            raise Refus(f"Zone hors de la page {page}.")
        out.append({"signataire": i, "page": page, "type": t, "x": max(0.0, x), "y": max(0.0, y), "w": w, "h": h})
    for i in range(nb_sig):
        if not any(z["signataire"] == i and z["type"] == "signature" for z in out):
            raise Refus(f"Signataire {i + 1} : placer au moins une zone de signature.")
    return out


def creer(conn, *, octets: bytes, nom_fichier: str, donnees: dict, auteur: dict) -> int:
    """Crée la demande (sans notifier). Rend son id ; le commit reste à l'appelant."""
    if not peut_creer(auteur):
        raise Refus("Votre profil ne permet pas d'envoyer un document à signer.", 403)
    if not octets:
        raise Refus("Aucun fichier.")
    if len(octets) > PARAPHEUR_TAILLE_MAX_MO * 1024 * 1024:
        raise Refus(f"Fichier trop lourd — {PARAPHEUR_TAILLE_MAX_MO} Mo au plus.", 413)
    try:
        dims = ppdf.pages(octets)
    except ValueError as e:
        raise Refus(str(e))
    titre = str(donnees.get("titre") or "").strip()[:200]
    if not titre:
        raise Refus("Titre obligatoire.")
    mode = donnees.get("mode") if donnees.get("mode") in MODES else "sequentiel"
    try:
        relance = int(donnees.get("relance_jours") if donnees.get("relance_jours") is not None else PARAPHEUR_RELANCE_JOURS)
    except (TypeError, ValueError):
        raise Refus("Rythme de relance invalide.")
    if not 0 <= relance <= 30:
        raise Refus("Relance : entre 0 (aucune) et 30 jours.")
    sigs = _signataires_propres(conn, donnees.get("signataires"))
    zs = _zones_propres(donnees.get("zones"), len(sigs), dims)
    nom = os.path.basename(str(nom_fichier or "document.pdf"))[:200] or "document.pdf"
    fichier = _ecrire(octets)
    now = maintenant()
    cur = conn.execute(
        """INSERT INTO parapheur_demandes
             (titre, message, mode, statut, echeance, relance_jours, nom_fichier, fichier_original,
              sha256_original, taille_original, nb_pages, niveau, cree_par_id, cree_par_nom, cree_par_email, cree_le)
           VALUES (?, ?, ?, 'en_cours', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (titre, str(donnees.get("message") or "").strip()[:3000], mode, _echeance(donnees.get("echeance")), relance,
         nom, fichier, sha256(octets), len(octets), len(dims), PARAPHEUR_NIVEAU, auteur.get("id"),
         auteur.get("nom") or auteur.get("email"), portail_espace.normaliser_email(auteur.get("email") or "") or None, now),
    )
    did = int(cur.lastrowid)
    ids = []
    for k, s in enumerate(sigs):
        if s["type"] == "externe":
            portail_espace.espace_pour(conn, s["email"], s["nom"] or s["organisation"])
        cur = conn.execute(
            """INSERT INTO parapheur_signataires (demande_id, ordre, type, user_id, nom, email, organisation, statut)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'attente')""",
            (did, k + 1, s["type"], s["user_id"], s["nom"], s["email"], s["organisation"]),
        )
        ids.append(int(cur.lastrowid))
    for z in zs:
        conn.execute(
            "INSERT INTO parapheur_zones (demande_id, signataire_id, page, type, x, y, w, h) VALUES (?,?,?,?,?,?,?,?)",
            (did, ids[z["signataire"]], z["page"], z["type"], z["x"], z["y"], z["w"], z["h"]),
        )
    evenement(conn, did, "creation", acteur=auteur.get("nom") or auteur.get("email") or "",
              detail=f"{len(sigs)} signataire(s), {'séquentiel' if mode == 'sequentiel' else 'parallèle'}")
    return did


def suivants(conn, did: int) -> list[int]:
    """Passe « à signer » ceux dont c'est le tour et rend leurs ids."""
    d = demande(conn, did)
    if not d or d["statut"] != "en_cours":
        return []
    sigs = signataires(conn, did)
    if d["mode"] == "parallele":
        cands = [s for s in sigs if s["statut"] == "attente"]
    else:
        if any(s["statut"] in EN_ATTENTE_SIG for s in sigs):
            return []
        cands = [s for s in sigs if s["statut"] == "attente"][:1]
    for s in cands:
        conn.execute("UPDATE parapheur_signataires SET statut = 'a_signer' WHERE id = ? AND statut = 'attente'", (s["id"],))
    return [s["id"] for s in cands]


# ── Jetons des externes ─────────────────────────────────────────────────

def emettre_jeton(conn, sid: int) -> str:
    s = signataire(conn, sid)
    d = demande(conn, s["demande_id"])
    fin = datetime.now(_PARIS).replace(tzinfo=None) + timedelta(days=PARAPHEUR_JETON_JOURS)
    if d.get("echeance"):
        fin = min(fin, datetime.fromisoformat(d["echeance"] + "T23:59:59"))
    jeton = secrets.token_urlsafe(32)
    conn.execute(
        """INSERT INTO parapheur_jetons (signataire_id, jeton_hash, cree_le, expire_le, usages, usages_max)
           VALUES (?, ?, ?, ?, 0, ?)""",
        (sid, _empreinte_jeton(jeton), maintenant(), fin.strftime("%Y-%m-%dT%H:%M:%S"), PARAPHEUR_JETON_USAGES),
    )
    return jeton


def revoquer(conn, *, sid: int | None = None, did: int | None = None) -> None:
    now = maintenant()
    if sid is not None:
        conn.execute("UPDATE parapheur_jetons SET revoque_le = ? WHERE signataire_id = ? AND revoque_le IS NULL", (now, sid))
    if did is not None:
        conn.execute(
            """UPDATE parapheur_jetons SET revoque_le = ? WHERE revoque_le IS NULL
                AND signataire_id IN (SELECT id FROM parapheur_signataires WHERE demande_id = ?)""", (now, did))


def par_jeton(conn, email_espace: str, jeton: str, *, consommer: bool) -> tuple[Optional[dict], str]:
    """(signataire, '') si le jeton ouvre la signature ; sinon (signataire ou
    None, raison) avec raison parmi inconnu, expire, epuise, traite."""
    if not jeton or len(jeton) > 100:
        return None, "inconnu"
    j = conn.execute("SELECT * FROM parapheur_jetons WHERE jeton_hash = ?", (_empreinte_jeton(jeton),)).fetchone()
    if not j:
        return None, "inconnu"
    s = signataire(conn, j["signataire_id"])
    if not s or s["email"] != portail_espace.normaliser_email(email_espace):
        return None, "inconnu"
    d = demande(conn, s["demande_id"])
    if not d or d["statut"] != "en_cours" or s["statut"] not in EN_ATTENTE_SIG:
        return s, "traite"
    if j["revoque_le"] or (_dt(j["expire_le"]) or datetime.min) < datetime.now(_PARIS).replace(tzinfo=None):
        return s, "expire"
    if j["usages"] >= j["usages_max"]:
        return s, "epuise"
    if consommer:
        conn.execute("UPDATE parapheur_jetons SET usages = usages + 1 WHERE id = ?", (j["id"],))
    return s, ""


def noter_ouverture(conn, s: dict, *, ip: str, acteur: str) -> None:
    if s.get("ouvert_le"):
        return
    conn.execute(
        """UPDATE parapheur_signataires SET ouvert_le = ?,
                  statut = CASE WHEN statut = 'a_signer' THEN 'ouvert' ELSE statut END WHERE id = ?""",
        (maintenant(), s["id"]),
    )
    evenement(conn, s["demande_id"], "ouverture", sid=s["id"], acteur=acteur, ip=ip)


# ── Signature, refus, annulation ────────────────────────────────────────

def png(valeur: Any, *, obligatoire: bool = True) -> Optional[bytes]:
    """Image PNG d'une signature (data URL ou base64), bornée en poids et en taille."""
    if not valeur:
        if obligatoire:
            raise Refus("Signature manquante.")
        return None
    s = str(valeur)
    if s.startswith("data:"):
        if not s.startswith("data:image/png;base64,"):
            raise Refus("Signature : image PNG attendue.")
        s = s.split(",", 1)[1]
    try:
        b = base64.b64decode(s, validate=True)
    except Exception:
        raise Refus("Signature illisible.")
    if len(b) > PNG_MAX_OCTETS:
        raise Refus("Signature trop lourde.")
    if len(b) < 33 or b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        raise Refus("Signature : image PNG attendue.")
    w, h = struct.unpack(">II", b[16:24])
    if not (1 <= w <= 4000 and 1 <= h <= 4000):
        raise Refus("Signature : dimensions invalides.")
    return b


def _fermer_tache(conn, tache_id: Any) -> None:
    if not tache_id:
        return
    try:
        now = maintenant()
        conn.execute(
            """UPDATE taches SET statut = 'termine', done_at = COALESCE(done_at, ?), updated_at = ?
                WHERE id = ? AND deleted_at IS NULL""", (now, now, tache_id))
    except Exception:
        pass


def signer(conn, sid: int, *, signature: Any, paraphe: Any = None, mode: str = "dessin", nom_saisi: str = "",
           ip: str = "", user_agent: str = "", acteur: str = "") -> dict:
    """Enregistre la signature et fait avancer la demande. Rend
    {"termine": bool, "suivants": [ids]}. Le commit reste à l'appelant."""
    s = signataire(conn, sid)
    if not s:
        raise Refus("Signataire introuvable.", 404)
    d = demande(conn, s["demande_id"])
    if not d or d["statut"] != "en_cours":
        raise Refus("Cette demande n'est plus en cours.", 409)
    if s["statut"] not in EN_ATTENTE_SIG:
        raise Refus("Ce n'est pas à vous de signer pour le moment." if s["statut"] == "attente"
                    else "Signature déjà enregistrée.", 409)
    img = png(signature)
    par = png(paraphe, obligatoire=False)
    mode = mode if mode in ("dessin", "texte", "reutilise") else "dessin"
    nom = str(nom_saisi or "").strip()[:200] or s["nom"]
    now = maintenant()
    conn.execute(
        """UPDATE parapheur_signataires
              SET statut = 'signe', signe_le = ?, ouvert_le = COALESCE(ouvert_le, ?), ip = ?, user_agent = ?,
                  mode_signature = ?, nom_saisi = ?, signature_png = ?, paraphe_png = ?
            WHERE id = ?""",
        (now, now, (ip or "")[:64], (user_agent or "")[:300], mode, nom, img, par, sid),
    )
    revoquer(conn, sid=sid)
    _fermer_tache(conn, s.get("tache_id"))
    evenement(conn, d["id"], "signature", sid=sid, acteur=acteur or nom, ip=ip,
              detail={"dessin": "signature tracée", "texte": "signature saisie", "reutilise": "signature réutilisée"}[mode])
    sigs = signataires(conn, d["id"])
    if all(x["statut"] == "signe" for x in sigs):
        sceller(conn, d["id"])
        return {"termine": True, "suivants": []}
    return {"termine": False, "suivants": suivants(conn, d["id"])}


def _clore(conn, did: int, statut: str, *, motif: str, statut_sig: str) -> None:
    now = maintenant()
    conn.execute("UPDATE parapheur_demandes SET statut = ?, termine_le = ?, motif_fin = ? WHERE id = ?",
                 (statut, now, (motif or "")[:500] or None, did))
    for s in signataires(conn, did):
        if s["statut"] in ("attente",) + EN_ATTENTE_SIG:
            conn.execute("UPDATE parapheur_signataires SET statut = ? WHERE id = ?", (statut_sig, s["id"]))
            _fermer_tache(conn, s.get("tache_id"))
    revoquer(conn, did=did)


def refuser(conn, sid: int, *, motif: str, ip: str = "", acteur: str = "") -> dict:
    s = signataire(conn, sid)
    if not s:
        raise Refus("Signataire introuvable.", 404)
    d = demande(conn, s["demande_id"])
    if not d or d["statut"] != "en_cours" or s["statut"] not in EN_ATTENTE_SIG:
        raise Refus("Cette demande n'attend pas votre signature.", 409)
    motif = str(motif or "").strip()
    if len(motif) < 3:
        raise Refus("Motif du refus obligatoire.")
    now = maintenant()
    conn.execute(
        """UPDATE parapheur_signataires SET statut = 'refuse', refuse_le = ?, motif_refus = ?, ip = ?,
                  ouvert_le = COALESCE(ouvert_le, ?) WHERE id = ?""",
        (now, motif[:1000], (ip or "")[:64], now, sid),
    )
    _fermer_tache(conn, s.get("tache_id"))
    _clore(conn, d["id"], "refusee", motif=f"Refus de {s['nom'] or s['email']} : {motif}", statut_sig="annule")
    evenement(conn, d["id"], "refus", sid=sid, acteur=acteur or s["nom"], ip=ip, detail=motif[:300])
    return demande(conn, d["id"])


def annuler(conn, did: int, *, motif: str, acteur: str) -> dict:
    d = demande(conn, did)
    if not d:
        raise Refus("Demande introuvable.", 404)
    if d["statut"] != "en_cours":
        raise Refus("Seule une demande en cours s'annule.", 409)
    _clore(conn, did, "annulee", motif=str(motif or "").strip() or "Annulée par l'émetteur", statut_sig="annule")
    evenement(conn, did, "annulation", acteur=acteur, detail=str(motif or "").strip()[:300])
    return demande(conn, did)


def sceller(conn, did: int) -> dict:
    """Document final : signatures apposées, certificat, niveau de signature."""
    d = demande(conn, did)
    origine = lire_fichier(d["fichier_original"])
    if sha256(origine) != d["sha256_original"]:
        raise Refus("Le document d'origine a été altéré sur le serveur — scellement refusé.", 409)
    sigs_img = {s["id"]: s for s in signataires(conn, did, avec_images=True)}
    signe = ppdf.apposer(origine, zones(conn, did), sigs_img)
    sha_signe = sha256(signe)
    libelle, fn = ppdf.niveau(d.get("niveau") or "simple")
    now = maintenant()
    d_cert = dict(d, termine_le=now)
    evenement(conn, did, "scelle", acteur=APP_ORG_NAME, detail=f"empreinte du document signé {sha_signe[:16]}…")
    cert = ppdf.certificat(d_cert, signataires(conn, did), evenements(conn, did), organisation=APP_ORG_NAME,
                           sha_original=d["sha256_original"], sha_signe=sha_signe, niveau_libelle=libelle)
    final = ppdf.assembler(signe, cert, organisation=APP_ORG_NAME, demande_id=did, titre=d["titre"])
    final = fn(final, {"demande": d_cert, "signataires": list(sigs_img.values())})
    nom = _ecrire(final)
    conn.execute(
        """UPDATE parapheur_demandes SET statut = 'signee', termine_le = ?, fichier_final = ?,
                  sha256_signe = ?, sha256_final = ? WHERE id = ?""",
        (now, nom, sha_signe, sha256(final), did),
    )
    return demande(conn, did)


# ── Notifications ───────────────────────────────────────────────────────

def lien_interne(did: int, *, signer_: bool = False) -> str:
    return f"{public_base_url()}/tools?outil=parapheur&demande={did}" + ("&signer=1" if signer_ else "")


def _email_signature(d: dict, s: dict, *, url: str, relance: bool, externe: bool) -> tuple[str, str]:
    from app.services.email_service import _email_bouton, _email_detail_table, _esc, email_mysifa_layout

    org = APP_ORG_NAME
    de = d.get("cree_par_nom") or org
    intro = f"{_esc(de)} vous demande de signer le document <strong>« {_esc(d['titre'])} »</strong>."
    if relance:
        intro = "Rappel : votre signature est toujours attendue. " + intro
    lignes = [("Document", _esc(d["nom_fichier"])), ("Pages", _esc(d["nb_pages"]))]
    if d.get("echeance"):
        lignes.append(("À signer avant le", _esc(ppdf.date_fr(d["echeance"]))))
    message = ""
    if (d.get("message") or "").strip():
        message = ('<p style="margin:0 0 18px;padding:12px 14px;border-left:3px solid #0891b2;'
                   'background:#f1f5f9;font-size:14px;color:#334155;line-height:1.6;white-space:pre-wrap">'
                   + _esc(d["message"].strip()) + "</p>")
    salut = f"Bonjour {s['nom']}," if s.get("nom") else "Bonjour,"
    fin = (f"Le lien ouvre votre espace {_esc(org)} sur ce document. Il est personnel et valable pour une "
           "durée limitée ; votre espace permet d'en recevoir un nouveau." if externe else
           "Le document se signe dans MyTools, onglet Parapheur.")
    inner = f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">{_esc(salut)}</p>
    <p style="margin:0 0 18px;font-size:14px;color:#475569;line-height:1.65">{intro}</p>
    {message}
    {_email_detail_table(lignes)}
    <p style="margin:18px 0 0;font-size:13px;color:#64748b;line-height:1.65">{fin}</p>
    {_email_bouton(url, "Ouvrir le document à signer", "Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :")}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      Cordialement,<br><strong style="color:#0f172a;font-size:14px">{_esc(de)}</strong><br>{_esc(org)}
    </p>"""
    corps = email_mysifa_layout(
        subtitle="Document à signer", body_html=inner,
        footer_note=(f"Ce lien est personnel : merci de ne pas le transférer." if externe else None),
        marque=org if externe else "MySifa",
    )
    sujet = ("Rappel : " if relance else "") + f"Document à signer — {d['titre']}" + (f" — {org}" if externe else "")
    return sujet[:200], corps


def _tache_interne(conn, d: dict, s: dict) -> None:
    if s.get("tache_id") or not s.get("user_id"):
        return
    try:
        from app.routers.taches import creer_tache_pour
        from config import TACHES_SERVICES_CODES

        u = conn.execute("SELECT role FROM users WHERE id = ?", (s["user_id"],)).fetchone()
        role = (u["role"] if u else "") or ""
        demandeur = {"id": d.get("cree_par_id"), "nom": d.get("cree_par_nom") or APP_ORG_NAME,
                     "email": d.get("cree_par_email") or ""}
        desc = (f"Document à signer : {d['titre']} ({d['nom_fichier']}).\n"
                + (f"À signer avant le {ppdf.date_fr(d['echeance'])}.\n" if d.get("echeance") else "")
                + f"Lien : {lien_interne(d['id'], signer_=True)}")
        tid = creer_tache_pour(conn, demandeur, titre=f"Signature : {d['titre']}"[:200], description=desc,
                               ttype="autre", module="print",
                               service=role if role in TACHES_SERVICES_CODES else "superadmin",
                               assignes=[int(s["user_id"])])
        conn.execute("UPDATE parapheur_signataires SET tache_id = ? WHERE id = ?", (tid, s["id"]))
    except Exception:
        pass


def notifier(conn, sid: int, *, relance: bool = False, acteur: str = "", nouveau_lien: bool = False) -> bool:
    """Prévient un signataire dont c'est le tour (invitation, relance ou
    nouveau lien). Valide l'état en base AVANT l'envoi de l'email ; rend True
    si au moins un canal est parti."""
    s = signataire(conn, sid)
    d = demande(conn, s["demande_id"]) if s else None
    if not s or not d or d["statut"] != "en_cours" or s["statut"] not in EN_ATTENTE_SIG:
        return False
    externe = s["type"] == "externe"
    if externe:
        esp = portail_espace.espace_pour(conn, s["email"], s["nom"] or s["organisation"])
        url = portail_espace.url_espace(esp["token"]) + "#signer=" + emettre_jeton(conn, sid)
    else:
        url = lien_interne(d["id"], signer_=True)
        _tache_interne(conn, d, s)
    now = maintenant()
    if s.get("notifie_le") and (relance or nouveau_lien):
        conn.execute("UPDATE parapheur_signataires SET nb_relances = nb_relances + ?, relance_le = ? WHERE id = ?",
                     (1 if relance else 0, now, sid))
    else:
        conn.execute("UPDATE parapheur_signataires SET notifie_le = COALESCE(notifie_le, ?), relance_le = ? WHERE id = ?",
                     (now, now, sid))
    conn.commit()
    parti = False
    if not externe and s.get("user_id"):
        try:
            from app.routers.push import send_push_safe
            parti = send_push_safe(s["user_id"], title="Document à signer", body=d["titre"][:120],
                                   url=f"/tools?outil=parapheur&demande={d['id']}&signer=1",
                                   tag=f"parapheur-{d['id']}") > 0
        except Exception:
            pass
    if s.get("email"):
        sujet, corps = _email_signature(d, s, url=url, relance=relance, externe=externe)
        expediteur = (d.get("cree_par_email") or "").strip() or None
        if email_service.send_email(to=s["email"], subject=sujet, html_body=corps, reply_to=expediteur):
            parti = True
    type_ = "lien" if nouveau_lien else ("relance" if relance else "envoi")
    evenement(conn, d["id"], type_ if (parti or not externe) else "echec_envoi", sid=sid,
              acteur=acteur or APP_ORG_NAME,
              detail=(s["email"] or s["nom"]) + ("" if parti or not externe else " — email non parti"))
    conn.commit()
    return parti or (not externe and bool(s.get("tache_id") or s.get("user_id")))


def prevenir_fin(conn, did: int) -> None:
    """Fin de circuit : l'émetteur est prévenu (signé, refusé, expiré) ; une
    fois signé, chaque signataire sait où retrouver le document final."""
    d = demande(conn, did)
    if not d:
        return
    from app.services.email_service import _email_detail_table, _esc, email_mysifa_layout

    etat = {"signee": "Signé par tous", "refusee": "Refusé", "expiree": "Échéance dépassée",
            "annulee": "Annulé"}.get(d["statut"], d["statut"])
    if d.get("cree_par_email"):
        lignes = [("Document", _esc(d["nom_fichier"])), ("État", _esc(etat))]
        if d.get("motif_fin"):
            lignes.append(("Motif", _esc(d["motif_fin"])))
        corps = email_mysifa_layout(subtitle="Parapheur", body_html=_email_detail_table(lignes),
                                    cta_href=lien_interne(did), cta_label="Ouvrir la demande")
        email_service.send_email(to=d["cree_par_email"], subject=f"{etat} — {d['titre']}"[:200], html_body=corps)
    if d["statut"] != "signee":
        return
    for s in signataires(conn, did):
        if not s.get("email") or s["email"] == d.get("cree_par_email"):
            continue
        if s["type"] == "externe":
            esp = portail_espace.espace_pour(conn, s["email"], s["nom"])
            href, marque = portail_espace.url_espace(esp["token"]), APP_ORG_NAME
        else:
            href, marque = lien_interne(did), "MySifa"
        corps = email_mysifa_layout(
            subtitle="Document signé",
            body_html=_email_detail_table([("Document", _esc(d["nom_fichier"])), ("État", "Signé par tous")]),
            cta_href=href, cta_label="Télécharger le document signé", marque=marque)
        email_service.send_email(to=s["email"], subject=f"Document signé — {d['titre']}"[:200], html_body=corps)
    conn.commit()


def nouveau_lien(conn, sid: int) -> bool:
    """Depuis l'Espace : renvoie un lien de signature, borné par jour."""
    s = signataire(conn, sid)
    jour = date.today().isoformat()
    nb = int(s.get("liens_nb") or 0) if s.get("liens_jour") == jour else 0
    if nb >= PARAPHEUR_LIENS_PAR_JOUR:
        raise Refus("Trop de liens demandés aujourd'hui — utilisez le dernier email reçu.", 429)
    conn.execute("UPDATE parapheur_signataires SET liens_jour = ?, liens_nb = ? WHERE id = ?", (jour, nb + 1, sid))
    return notifier(conn, sid, nouveau_lien=True, acteur=s["nom"] or s["email"])


# ── Espace SIFA ─────────────────────────────────────────────────────────

def elements_espace(conn, email: str) -> list[dict]:
    """Lecteur de `portail_espace.contenu()` : les documents adressés à cette
    adresse dont l'invitation est partie."""
    rows = conn.execute(
        """SELECT s.id, s.statut, s.notifie_le, s.signe_le, s.refuse_le, d.titre, d.nom_fichier, d.echeance,
                  d.cree_par_nom, d.statut AS d_statut, d.fichier_final
             FROM parapheur_signataires s JOIN parapheur_demandes d ON d.id = s.demande_id
            WHERE s.email = ? AND s.type = 'externe' AND s.notifie_le IS NOT NULL
            ORDER BY s.notifie_le DESC LIMIT 100""", (email,)).fetchall()
    out = []
    for r in rows:
        a_traiter = r["d_statut"] == "en_cours" and r["statut"] in EN_ATTENTE_SIG
        out.append({
            "module": "signature", "id": r["id"], "titre": r["titre"], "detail": ("Document à signer · " if a_traiter else "Document · ") + r["nom_fichier"],
            "echeance": r["echeance"], "envoye_le": r["notifie_le"], "de": r["cree_par_nom"],
            "a_traiter": a_traiter, "statut": r["statut"], "demande_statut": r["d_statut"],
            "signe_le": r["signe_le"], "final": bool(r["fichier_final"]) and r["d_statut"] == "signee",
        })
    return out


def signataire_espace(conn, email: str, sid: int) -> dict:
    s = signataire(conn, sid)
    if not s or s["type"] != "externe" or s["email"] != portail_espace.normaliser_email(email) or not s.get("notifie_le"):
        raise Refus("Document introuvable.", 404)
    return s


# ── Relances automatiques et échéances ──────────────────────────────────

def _heure_ouvree(now: datetime) -> bool:
    return now.weekday() < 5 and 8 <= now.hour < 18


def tour(get_db, *, force: bool = False) -> dict:
    """Une passe de la boucle (main.py, prod seulement) : expire les demandes
    dont l'échéance est passée, relance les signataires qui tardent (jours
    ouvrés, 8 h – 18 h)."""
    res = {"expirees": 0, "relances": 0}
    now = datetime.now(_PARIS).replace(tzinfo=None)
    with get_db() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM parapheur_demandes WHERE statut = 'en_cours'").fetchall()]
        for did in ids:
            d = demande(conn, did)
            if d.get("echeance") and d["echeance"] < date.today().isoformat():
                _clore(conn, did, "expiree", motif="Échéance dépassée", statut_sig="expire")
                evenement(conn, did, "expiration", acteur=APP_ORG_NAME)
                conn.commit()
                res["expirees"] += 1
                try:
                    prevenir_fin(conn, did)
                except Exception:
                    pass
                continue
            if not (force or _heure_ouvree(now)) or int(d.get("relance_jours") or 0) <= 0:
                continue
            for s in signataires(conn, did):
                if s["statut"] not in EN_ATTENTE_SIG or not s.get("notifie_le"):
                    continue
                if int(s.get("nb_relances") or 0) >= PARAPHEUR_RELANCES_MAX:
                    continue
                dernier = _dt(s.get("relance_le") or s["notifie_le"])
                if dernier and now - dernier >= timedelta(days=int(d["relance_jours"])):
                    if notifier(conn, s["id"], relance=True, acteur="Relance automatique"):
                        res["relances"] += 1
    return res
