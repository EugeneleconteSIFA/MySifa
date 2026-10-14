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

from config import (
    APP_ORG_NAME,
    EUDR_CATEGORIES_BOBINES,
    EUDR_CHOIX,
    EUDR_REPONSE_AVANT,
    eudr_langue,
    eudr_libelle,
)

_PARIS = ZoneInfo("Europe/Paris")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ST_ENVOYEE = "envoyee"
ST_OUVERTE = "ouverte"
ST_REPONDUE = "repondue"

# Champs texte libres du formulaire et leur longueur maximale.
CHAMPS_TEXTE = {
    "repondant_societe": 200,
    "repondant_nom": 200,
    "repondant_tel": 50,
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
        """SELECT id, nom, pays, groupe, has_fsc, licence, email, categories, langue_default
           FROM fournisseurs_fsc
           WHERE actif=1 AND COALESCE(fusionne_dans,0)=0
           ORDER BY nom COLLATE NOCASE"""
    ).fetchall()
    demandes: dict[int, list[dict]] = {}
    for d in conn.execute(
        """SELECT id, fournisseur_id, email, statut, nb_envois, envoye_le, envoye_par,
                  ouvert_le, repondu_le, langue
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
        cats = _categories(f["categories"])
        out.append({
            "id": fid,
            "categories": cats,
            "langue": _langue_suggeree(conn, fid, ds, f["langue_default"]),
            "bobines": any(c in EUDR_CATEGORIES_BOBINES for c in cats),
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


def _langue_suggeree(conn, fournisseur_id: int, demandes: list[dict], langue_fiche) -> str:
    """Langue proposée à l'envoi : celle de la dernière demande (le fournisseur
    a pu la changer sur le formulaire), sinon celle du contact principal, sinon
    celle de la fiche, sinon l'anglais."""
    if demandes:
        return eudr_langue(demandes[-1].get("langue"))
    row = conn.execute(
        """SELECT langue FROM fournisseur_contacts
           WHERE fournisseur_id=? AND actif=1 ORDER BY is_principal DESC, id LIMIT 1""",
        (int(fournisseur_id),),
    ).fetchone()
    return eudr_langue((row["langue"] if row else None) or langue_fiche)


def _categories(brut) -> list[str]:
    """`fournisseurs_fsc.categories` est une liste JSON ; vide si illisible."""
    try:
        val = json.loads(brut or "[]")
    except (TypeError, ValueError):
        return []
    return [str(c) for c in val] if isinstance(val, list) else []


def _reponse_lisible(rep: dict) -> dict:
    """La réponse brute, plus le libellé français de chaque choix."""
    d = dict(rep)
    d.pop("ip", None)
    d["libelles"] = {c: eudr_libelle(c, d.get(c)) for c in CHAMPS_CHOIX}
    return d


def historique(conn, fournisseur_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM eudr_reponses WHERE fournisseur_id=? ORDER BY id DESC""",
        (int(fournisseur_id),),
    ).fetchall()
    return [_reponse_lisible(dict(r)) for r in rows]


# ── Demandes et jetons ───────────────────────────────────────────────────


def demande_pour(conn, *, fournisseur_id: int, email: str, langue: str = "en") -> dict:
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
        """INSERT INTO eudr_demandes (fournisseur_id, email, token, statut, langue, created_at)
           VALUES (?,?,?,?,?,?)""",
        (int(fournisseur_id), email_norm, str(uuid.uuid4()), ST_ENVOYEE, eudr_langue(langue), now),
    )
    return dict(conn.execute("SELECT * FROM eudr_demandes WHERE id=?", (cur.lastrowid,)).fetchone())


def noter_envoi(conn, *, demande_id: int, auteur: str | None, langue: str = "en") -> None:
    conn.execute(
        """UPDATE eudr_demandes
           SET envoye_le=?, envoye_par=?, nb_envois=nb_envois+1, langue=?,
               statut=CASE WHEN statut=? THEN statut ELSE ? END
           WHERE id=?""",
        (now_paris_iso(), auteur, eudr_langue(langue), ST_REPONDUE, ST_ENVOYEE, int(demande_id)),
    )


# Pièces jointes d'une saisie manuelle : extension → type servi. Liste fermée,
# rien d'exécutable. PDF et images s'ouvrent dans le navigateur, le reste se
# télécharge.
PIECE_TYPES = {
    "pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "msg": "application/vnd.ms-outlook", "eml": "message/rfc822",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
PIECE_EN_LIGNE = {"pdf", "png", "jpg", "jpeg", "webp"}
PIECE_MAX_OCTETS = 15 * 1024 * 1024


def enregistrer_manuel(conn, *, fournisseur_id: int, body: dict, auteur: str | None,
                       piece: tuple[str, str, str] | None) -> int:
    """Réponse saisie dans MyQualité (courrier, email, appel). Lève ValueError.

    `piece` = (nom sur disque, nom d'origine, type MIME), fichier déjà écrit.
    """
    champs: dict = {}
    for champ in ("role", "perimetre", "transmission"):
        v = str(body.get(champ) or "").strip()
        if v and v not in EUDR_CHOIX[champ]:
            raise ValueError("Choix invalide.")
        champs[champ] = v or None
    commentaire = str(body.get("commentaire") or "").strip()[:4000]
    if not commentaire:
        raise ValueError("Commentaire obligatoire — résumez ce que le fournisseur a répondu.")
    now = now_paris_iso()
    # Demande inactive : la réponse garde un demande_id, aucun lien n'existe.
    cur = conn.execute(
        """INSERT INTO eudr_demandes (fournisseur_id, email, token, statut, envoye_par,
                                      repondu_le, actif, created_at)
           VALUES (?, '', ?, ?, ?, ?, 0, ?)""",
        (int(fournisseur_id), str(uuid.uuid4()), ST_REPONDUE, auteur, now, now),
    )
    p = piece or (None, None, None)
    cur = conn.execute(
        """INSERT INTO eudr_reponses (demande_id, fournisseur_id, role, perimetre, transmission,
               commentaire, source, saisi_par, piece_filename, piece_original, piece_mime, created_at)
           VALUES (?,?,?,?,?,?, 'manuel', ?,?,?,?,?)""",
        (cur.lastrowid, int(fournisseur_id), champs["role"], champs["perimetre"],
         champs["transmission"], commentaire, auteur, p[0], p[1], p[2], now),
    )
    return int(cur.lastrowid)


def annuler_demande(conn, demande_id: int) -> dict | None:
    """Désactive un lien envoyé à la mauvaise adresse : le formulaire répond
    alors « lien invalide ». Les réponses déjà reçues par ce lien restent."""
    row = conn.execute(
        """SELECT d.id, d.email, f.nom AS fournisseur_nom FROM eudr_demandes d
           JOIN fournisseurs_fsc f ON f.id=d.fournisseur_id
           WHERE d.id=? AND d.actif=1""",
        (int(demande_id),),
    ).fetchone()
    if not row:
        return None
    conn.execute("UPDATE eudr_demandes SET actif=0 WHERE id=?", (int(demande_id),))
    return dict(row)


def noter_langue(conn, demande: dict, langue: str) -> None:
    """Le fournisseur a changé de langue sur le formulaire : la relance suivante
    partira dans celle-ci."""
    conn.execute("UPDATE eudr_demandes SET langue=? WHERE id=?",
                 (eudr_langue(langue), int(demande["id"])))


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
    """Dernière réponse du fournisseur lui-même, pour préremplir son formulaire.
    Une saisie manuelle n'en fait pas partie : son commentaire est interne."""
    row = conn.execute(
        """SELECT * FROM eudr_reponses WHERE fournisseur_id=? AND COALESCE(source,'portail')<>'manuel'
           ORDER BY id DESC LIMIT 1""",
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
    if not propre["repondant_societe"]:
        raise ValueError("Please enter your company name.")
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


_MOIS = {
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"),
}


def date_longue(iso: str | None, langue: str = "en") -> str:
    """« 15 November 2026 », « 15 novembre 2026 », « 15 de noviembre de 2026 »."""
    try:
        d = datetime.strptime((iso or "")[:10], "%Y-%m-%d")
    except ValueError:
        return iso or ""
    if langue == "fr":
        return f"{d.day} {_MOIS['fr'][d.month - 1]} {d.year}"
    if langue == "es":
        return f"{d.day} de {_MOIS['es'][d.month - 1]} de {d.year}"
    return d.strftime("%d %B %Y").lstrip("0")


# Textes de l'email de demande. {org} est remplacé par le nom de l'entreprise
# (déjà mis en forme), le reste est du texte brut échappé à l'insertion.
_TEXTES_DEMANDE = {
    "en": {
        "hello": "Dear Sir or Madam,",
        "reminder": "This is a reminder of our request below.",
        "intro": ("{org} is preparing for the EU Deforestation Regulation (EU) 2023/1115 (EUDR), "
                  "which applies to the paper products we buy from you. To set up the traceability "
                  "of our supplies, we need a few answers from you: whether your products are in "
                  "scope, your role under the regulation, and how you will send us the reference "
                  "numbers of the due diligence statements."),
        "supplier": "Supplier", "by": "Reply requested by", "time": "Time needed",
        "time_val": "About 5 minutes",
        "how": ("The link opens a short form — no account or password required. You can answer "
                "again later with the same link if your position changes."),
        "cta": "Answer the EUDR questionnaire",
        "copy": "If the button does not work, copy this link into your browser:",
        "regards": "Best regards,", "service": "Quality department",
        "subtitle": "EUDR — supplier questionnaire",
        "footer": "supplier portal — personal link, do not share.",
        "subject": "EUDR — information requested by {org}", "subject_re": "Reminder — ",
    },
    "fr": {
        "hello": "Madame, Monsieur,",
        "reminder": "Nous nous permettons de vous relancer au sujet de la demande ci-dessous.",
        "intro": ("{org} prépare l'application du règlement (UE) 2023/1115 relatif aux produits "
                  "zéro déforestation (EUDR), qui s'applique au papier que nous vous achetons. Pour "
                  "mettre en place la traçabilité de nos approvisionnements, nous avons besoin de "
                  "quelques réponses : vos produits entrent-ils dans le périmètre, quel est votre "
                  "rôle au sens du règlement, et comment nous transmettrez-vous les numéros de "
                  "référence des déclarations de diligence raisonnée."),
        "supplier": "Fournisseur", "by": "Réponse souhaitée avant le", "time": "Durée",
        "time_val": "Environ 5 minutes",
        "how": ("Le lien ouvre un court formulaire, sans compte ni mot de passe. Vous pourrez "
                "répondre à nouveau avec le même lien si votre position évolue."),
        "cta": "Répondre au questionnaire EUDR",
        "copy": "Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :",
        "regards": "Cordialement,", "service": "Service qualité",
        "subtitle": "EUDR — questionnaire fournisseur",
        "footer": "portail fournisseur — lien personnel, ne pas partager.",
        "subject": "EUDR — informations demandées par {org}", "subject_re": "Relance — ",
    },
    "es": {
        "hello": "Estimados señores:",
        "reminder": "Les recordamos nuestra solicitud a continuación.",
        "intro": ("{org} se prepara para la aplicación del Reglamento (UE) 2023/1115 relativo a "
                  "los productos libres de deforestación (EUDR), que se aplica al papel que les "
                  "compramos. Para organizar la trazabilidad de nuestros suministros necesitamos "
                  "algunas respuestas: si sus productos están incluidos en el ámbito del reglamento, "
                  "cuál es su papel según el mismo y cómo nos enviarán los números de referencia "
                  "de las declaraciones de diligencia debida."),
        "supplier": "Proveedor", "by": "Respuesta solicitada antes del", "time": "Duración",
        "time_val": "Unos 5 minutos",
        "how": ("El enlace abre un breve formulario, sin cuenta ni contraseña. Podrán responder "
                "de nuevo con el mismo enlace si su posición cambia."),
        "cta": "Responder al cuestionario EUDR",
        "copy": "Si el botón no funciona, copien este enlace en su navegador:",
        "regards": "Atentamente,", "service": "Departamento de calidad",
        "subtitle": "EUDR — cuestionario para proveedores",
        "footer": "portal de proveedores — enlace personal, no compartir.",
        "subject": "EUDR — información solicitada por {org}", "subject_re": "Recordatorio — ",
    },
}


def email_demande(*, nom_fournisseur: str, lien: str, user_nom: str, relance: bool,
                  langue: str = "en") -> tuple[str, str]:
    """Sujet et corps HTML de la demande envoyée au fournisseur, dans sa langue."""
    from app.services.email_service import (
        _email_bouton,
        _email_detail_table,
        _esc,
        email_mysifa_layout,
    )

    lang = eudr_langue(langue)
    t = _TEXTES_DEMANDE[lang]
    org = APP_ORG_NAME
    org_html = f'<strong style="color:#0f172a">{_esc(org)}</strong>'
    intro = _esc(t["intro"]).replace("{org}", org_html)
    if relance:
        intro = _esc(t["reminder"]) + " " + intro
    detail = _email_detail_table([
        (t["supplier"], _esc(nom_fournisseur)),
        (t["by"], _esc(date_longue(EUDR_REPONSE_AVANT, lang))),
        (t["time"], _esc(t["time_val"])),
    ])
    cta = _email_bouton(f"{lien}?lang={lang}", t["cta"], t["copy"])
    inner = f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">{_esc(t["hello"])}</p>
    <p style="margin:0 0 22px;font-size:14px;color:#475569;line-height:1.65">{intro}</p>
    {detail}
    <p style="margin:18px 0 0;font-size:13px;color:#64748b;line-height:1.65">{_esc(t["how"])}</p>
    {cta}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      {_esc(t["regards"])}<br>
      <strong style="color:#0f172a;font-size:14px">{_esc(user_nom)}</strong><br>
      {_esc(org)} — {_esc(t["service"])}
    </p>"""
    body = email_mysifa_layout(
        subtitle=t["subtitle"],
        body_html=inner,
        footer_note=f"{org} {t['footer']}",
        footer_contact=True,
        marque=org,
        lang="en" if lang == "en" else "fr",
    )
    sujet = (t["subject_re"] if relance else "") + t["subject"].replace("{org}", org)
    return sujet, body


def email_reponse_recue(*, nom_fournisseur: str, reponse: dict, lien_mysifa: str) -> tuple[str, str]:
    """Notification interne : un fournisseur a répondu."""
    from app.services.email_service import _email_detail_table, _esc, email_mysifa_layout

    lignes = [
        ("Fournisseur", _esc(nom_fournisseur)),
        ("Société", _esc(reponse.get("repondant_societe") or "")),
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
