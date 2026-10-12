"""MyQualité — EUDR : questionnaire fournisseurs.

Même mécanique que la taxe carburant de MyExpé : on envoie au fournisseur un
email avec un lien personnel, il répond dans un formulaire MySifa sans compte,
la réponse arrive en base et la personne qui a envoyé la demande est prévenue.

- `eudr_demandes` : une ligne par (fournisseur, adresse). Une relance réutilise
  la ligne et son jeton — le lien d'un premier email reste valable.
- `eudr_reponses` : une ligne par réponse, jamais écrasée. La dernière fait foi.

Les libellés des choix vivent dans `config.EUDR_CHOIX`.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from config import APP_ORG_NAME, EUDR_CHOIX, EUDR_REPONSE_AVANT, eudr_libelle

_PARIS = ZoneInfo("Europe/Paris")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ST_ENVOYEE = "envoyee"
ST_OUVERTE = "ouverte"
ST_REPONDUE = "repondue"

# Champs texte libres du formulaire et leur longueur maximale.
CHAMPS_TEXTE = {
    "repondant_nom": 200,
    "repondant_fonction": 200,
    "repondant_email": 200,
    "codes_nc": 500,
    "date_debut_dds": 10,
    "transmission_detail": 1000,
    "amont": 1000,
    "essences": 500,
    "pays_recolte": 500,
    "contact_nom": 200,
    "contact_email": 200,
    "commentaire": 4000,
}
# Champs à choix : la valeur doit être une clé de EUDR_CHOIX[champ].
CHAMPS_CHOIX = tuple(EUDR_CHOIX.keys())
COLONNES_REPONSE = tuple(CHAMPS_TEXTE) + CHAMPS_CHOIX


def now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def email_valide(email: str | None) -> bool:
    return bool(email and _EMAIL_RE.match(email.strip()))


# ── Fournisseurs et contacts ─────────────────────────────────────────────


def _emails_contact(brut) -> list[str]:
    """`fournisseur_contacts.emails` est une liste JSON ; tolère le texte brut."""
    if not brut:
        return []
    try:
        val = json.loads(brut)
        items = val if isinstance(val, list) else [val]
    except (TypeError, ValueError):
        items = re.split(r"[,;\s]+", str(brut))
    return [str(e).strip() for e in items if email_valide(str(e))]


def emails_fournisseur(conn, fournisseur_id: int, email_fiche: str | None = None) -> list[str]:
    """Adresses connues d'un fournisseur : contact principal d'abord, fiche ensuite."""
    rows = conn.execute(
        """SELECT emails FROM fournisseur_contacts
           WHERE fournisseur_id=? AND actif=1
           ORDER BY is_principal DESC, id""",
        (int(fournisseur_id),),
    ).fetchall()
    vus: list[str] = []
    for r in rows:
        for e in _emails_contact(r["emails"]):
            if e.lower() not in [v.lower() for v in vus]:
                vus.append(e)
    if email_valide(email_fiche) and email_fiche.strip().lower() not in [v.lower() for v in vus]:
        vus.append(email_fiche.strip())
    return vus


def liste(conn) -> list[dict]:
    """Fournisseurs actifs, avec leur dernière demande et leur dernière réponse."""
    fours = conn.execute(
        """SELECT id, nom, pays, groupe, has_fsc, licence, email
           FROM fournisseurs_fsc
           WHERE actif=1 AND COALESCE(fusionne_dans,0)=0
           ORDER BY nom COLLATE NOCASE"""
    ).fetchall()
    demandes: dict[int, list[dict]] = {}
    for d in conn.execute(
        """SELECT id, fournisseur_id, email, statut, nb_envois, envoye_le, envoye_par,
                  ouvert_le, repondu_le
           FROM eudr_demandes WHERE actif=1 ORDER BY id"""
    ).fetchall():
        demandes.setdefault(int(d["fournisseur_id"]), []).append(dict(d))
    reponses: dict[int, dict] = {}
    for r in conn.execute(
        """SELECT * FROM eudr_reponses r
           WHERE id = (SELECT MAX(id) FROM eudr_reponses WHERE fournisseur_id=r.fournisseur_id)"""
    ).fetchall():
        reponses[int(r["fournisseur_id"])] = dict(r)
    nb_rep = {
        int(r["fournisseur_id"]): int(r["n"])
        for r in conn.execute(
            "SELECT fournisseur_id, COUNT(*) n FROM eudr_reponses GROUP BY fournisseur_id"
        ).fetchall()
    }
    out = []
    for f in fours:
        fid = int(f["id"])
        ds = demandes.get(fid, [])
        rep = reponses.get(fid)
        if rep:
            statut = ST_REPONDUE
        elif any(d["statut"] == ST_OUVERTE for d in ds):
            statut = ST_OUVERTE
        elif ds:
            statut = ST_ENVOYEE
        else:
            statut = "jamais"
        out.append({
            "id": fid,
            "nom": f["nom"],
            "pays": f["pays"],
            "groupe": f["groupe"],
            "has_fsc": bool(f["has_fsc"]),
            "licence": f["licence"],
            "emails": emails_fournisseur(conn, fid, f["email"]),
            "statut": statut,
            "demandes": ds,
            "derniere_demande": max((d["envoye_le"] or "" for d in ds), default=None) or None,
            "reponse": _reponse_lisible(rep) if rep else None,
            "nb_reponses": nb_rep.get(fid, 0),
        })
    return out


def _reponse_lisible(rep: dict) -> dict:
    """La réponse brute, plus le libellé français de chaque choix."""
    d = dict(rep)
    d.pop("ip", None)
    d["libelles"] = {c: eudr_libelle(c, d.get(c), "fr") for c in CHAMPS_CHOIX}
    return d


def historique(conn, fournisseur_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM eudr_reponses WHERE fournisseur_id=? ORDER BY id DESC""",
        (int(fournisseur_id),),
    ).fetchall()
    return [_reponse_lisible(dict(r)) for r in rows]


# ── Demandes et jetons ───────────────────────────────────────────────────


def demande_pour(conn, *, fournisseur_id: int, email: str) -> dict:
    """Demande active pour cette adresse, créée si besoin (jeton neuf)."""
    email_norm = email.strip().lower()
    row = conn.execute(
        """SELECT * FROM eudr_demandes
           WHERE fournisseur_id=? AND LOWER(email)=? AND actif=1 LIMIT 1""",
        (int(fournisseur_id), email_norm),
    ).fetchone()
    if row:
        return dict(row)
    now = now_paris_iso()
    cur = conn.execute(
        """INSERT INTO eudr_demandes (fournisseur_id, email, token, statut, created_at)
           VALUES (?,?,?,?,?)""",
        (int(fournisseur_id), email_norm, str(uuid.uuid4()), ST_ENVOYEE, now),
    )
    return dict(conn.execute("SELECT * FROM eudr_demandes WHERE id=?", (cur.lastrowid,)).fetchone())


def noter_envoi(conn, *, demande_id: int, auteur: str | None) -> None:
    conn.execute(
        """UPDATE eudr_demandes
           SET envoye_le=?, envoye_par=?, nb_envois=nb_envois+1,
               statut=CASE WHEN statut=? THEN statut ELSE ? END
           WHERE id=?""",
        (now_paris_iso(), auteur, ST_REPONDUE, ST_ENVOYEE, int(demande_id)),
    )


def demande_par_token(conn, token: str) -> dict | None:
    row = conn.execute(
        """SELECT d.*, f.nom AS fournisseur_nom, f.pays AS fournisseur_pays
           FROM eudr_demandes d JOIN fournisseurs_fsc f ON f.id=d.fournisseur_id
           WHERE d.token=? AND d.actif=1""",
        (token,),
    ).fetchone()
    return dict(row) if row else None


def noter_ouverture(conn, demande: dict) -> None:
    conn.execute(
        """UPDATE eudr_demandes
           SET ouvert_le=COALESCE(ouvert_le, ?),
               statut=CASE WHEN statut=? THEN ? ELSE statut END
           WHERE id=?""",
        (now_paris_iso(), ST_ENVOYEE, ST_OUVERTE, int(demande["id"])),
    )


def derniere_reponse(conn, fournisseur_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM eudr_reponses WHERE fournisseur_id=? ORDER BY id DESC LIMIT 1",
        (int(fournisseur_id),),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d.pop("ip", None)
    return d


def valider_reponse(body: dict) -> dict:
    """Nettoie la saisie du formulaire. Lève ValueError avec un message anglais."""
    propre: dict = {}
    for champ, longueur in CHAMPS_TEXTE.items():
        v = body.get(champ)
        v = str(v).strip()[:longueur] if v is not None else ""
        propre[champ] = v or None
    for champ in CHAMPS_CHOIX:
        v = str(body.get(champ) or "").strip()
        if v and v not in EUDR_CHOIX[champ]:
            raise ValueError(f"Invalid value for {champ}.")
        propre[champ] = v or None
    if not propre["repondant_nom"]:
        raise ValueError("Please enter your name.")
    if not email_valide(propre["repondant_email"]):
        raise ValueError("Please enter a valid email address.")
    if propre["contact_email"] and not email_valide(propre["contact_email"]):
        raise ValueError("The EUDR contact email address is not valid.")
    if propre["date_debut_dds"] and not re.match(r"^\d{4}-\d{2}-\d{2}$", propre["date_debut_dds"]):
        raise ValueError("Invalid date.")
    if not propre["role"]:
        raise ValueError("Please indicate your role under the EUDR.")
    return propre


def enregistrer_reponse(conn, *, demande: dict, reponse: dict, ip: str | None) -> int:
    now = now_paris_iso()
    cols = ("demande_id", "fournisseur_id") + COLONNES_REPONSE + ("ip", "created_at")
    vals = (int(demande["id"]), int(demande["fournisseur_id"])) + tuple(
        reponse.get(c) for c in COLONNES_REPONSE
    ) + (ip, now)
    cur = conn.execute(
        f"INSERT INTO eudr_reponses ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        vals,
    )
    conn.execute(
        "UPDATE eudr_demandes SET statut=?, repondu_le=? WHERE id=?",
        (ST_REPONDUE, now, int(demande["id"])),
    )
    return int(cur.lastrowid)


# ── Emails ───────────────────────────────────────────────────────────────


def _date_en(iso: str | None) -> str:
    try:
        return datetime.strptime((iso or "")[:10], "%Y-%m-%d").strftime("%d %B %Y")
    except ValueError:
        return iso or ""


def email_demande(*, nom_fournisseur: str, lien: str, user_nom: str, relance: bool) -> tuple[str, str]:
    """Sujet et corps HTML de la demande envoyée au fournisseur (anglais)."""
    from app.services.email_service import (
        _email_bouton,
        _email_detail_table,
        _esc,
        email_mysifa_layout,
    )

    org = APP_ORG_NAME
    intro = (
        f'<strong style="color:#0f172a">{_esc(org)}</strong> is preparing for the EU Deforestation '
        "Regulation (EU) 2023/1115 (EUDR), which applies to the paper products we buy from you. "
        "To set up the traceability of our supplies, we need a few answers from you: whether your "
        "products are in scope, your role under the regulation, and how you will send us the "
        "reference numbers of the due diligence statements."
    )
    if relance:
        intro = "This is a reminder of our request below. " + intro
    detail = _email_detail_table([
        ("Supplier", _esc(nom_fournisseur)),
        ("Reply requested by", _esc(_date_en(EUDR_REPONSE_AVANT))),
        ("Time needed", "About 5 minutes"),
    ])
    cta = _email_bouton(lien, "Answer the EUDR questionnaire",
                        "If the button does not work, copy this link into your browser:")
    inner = f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">Dear Sir or Madam,</p>
    <p style="margin:0 0 22px;font-size:14px;color:#475569;line-height:1.65">{intro}</p>
    {detail}
    <p style="margin:18px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      The link opens a short form — no account or password required. You can answer again
      later with the same link if your position changes.
    </p>
    {cta}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      Best regards,<br>
      <strong style="color:#0f172a;font-size:14px">{_esc(user_nom)}</strong><br>
      {_esc(org)} — Quality department
    </p>"""
    body = email_mysifa_layout(
        subtitle="EUDR — supplier questionnaire",
        body_html=inner,
        footer_note=f"{org} supplier portal — personal link, do not share.",
        footer_contact=True,
        marque=org,
        lang="en",
    )
    sujet = f"{'Reminder — ' if relance else ''}EUDR — information requested by {org}"
    return sujet, body


def email_reponse_recue(*, nom_fournisseur: str, reponse: dict, lien_mysifa: str) -> tuple[str, str]:
    """Notification interne : un fournisseur a répondu."""
    from app.services.email_service import _email_detail_table, _esc, email_mysifa_layout

    lignes = [
        ("Fournisseur", _esc(nom_fournisseur)),
        ("Répondant", _esc(f"{reponse.get('repondant_nom') or ''} — {reponse.get('repondant_email') or ''}")),
        ("Rôle", _esc(eudr_libelle("role", reponse.get("role")))),
        ("Produits dans le périmètre", _esc(eudr_libelle("perimetre", reponse.get("perimetre")))),
        ("Transmission des références", _esc(eudr_libelle("transmission", reponse.get("transmission")))),
    ]
    inner = f"""
    <p style="margin:0 0 18px;font-size:14px;color:#475569;line-height:1.65">
      Réponse au questionnaire EUDR reçue.
    </p>
    {_email_detail_table(lignes)}
    <p style="margin:18px 0 0;font-size:13px;color:#64748b">
      Détail complet : <a href="{_esc(lien_mysifa)}">MyQualité › Certifications SIFA › EUDR</a>
    </p>"""
    body = email_mysifa_layout(
        subtitle="EUDR — réponse fournisseur",
        body_html=inner,
        marque=APP_ORG_NAME,
    )
    return f"EUDR — réponse de {nom_fournisseur}", body
