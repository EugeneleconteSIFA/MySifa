"""MyExpé — taxe carburant des transporteurs.

Le pourcentage vit sur la fiche transporteur (`taxe_carburant_pct`) et le
comparateur l'ajoute au prix de grille, sauf si la grille porte déjà sa propre
ligne gasoil. Ce module s'occupe de ce qui l'entoure :

- savoir de quand date la valeur et qui l'a saisie (colonnes
  `taxe_carburant_maj_*`, historique `expe_taxe_carburant_historique`) ;
- demander aux transporteurs de la mettre à jour eux-mêmes, par un email qui
  ouvre leur espace sur le portail transporteur ;
- prévenir le service expéditions quand une saisie arrive.

Une saisie du transporteur qui reprend la même valeur est enregistrée comme
une saisie : « il a confirmé 12,8 % ce mois-ci » est une information, et c'est
elle qui fait passer la ligne de « en attente » à « à jour ».
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from config import APP_ORG_NAME, EXPE_DEVIS_FROM, public_base_url

_PARIS = ZoneInfo("Europe/Paris")

PCT_MIN = 0.0
PCT_MAX = 100.0

SOURCE_PORTAIL = "portail"
SOURCE_MANUEL = "manuel"

EV_SAISIE = "saisie"
EV_DEMANDE = "demande"


def now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def valider_pct(valeur) -> float:
    """Pourcentage arrondi au centième. Lève ValueError hors [0, 100]."""
    if isinstance(valeur, str):
        valeur = valeur.strip().replace(",", ".").rstrip("%").strip()
    pct = float(valeur)
    if pct != pct or pct < PCT_MIN or pct > PCT_MAX:
        raise ValueError("hors bornes")
    return round(pct, 2)


def emails_transporteur(row) -> list[str]:
    """Adresses de contact d'une fiche transporteur, dédupliquées."""
    d = dict(row)
    brut = d.get("contact_emails")
    items: list[str] = []
    if isinstance(brut, str) and brut.strip():
        s = brut.strip()
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    items = [str(x).strip() for x in arr if x]
            except ValueError:
                items = []
        if not items:
            items = [x.strip() for x in re.split(r"[,;\n\r\t]+", s) if x.strip()]
    if not items:
        legacy = (d.get("contact_email") or "").strip()
        if legacy:
            items = [legacy]
    vus: set[str] = set()
    out: list[str] = []
    for e in items:
        low = e.lower()
        if "@" in low and low not in vus:
            vus.add(low)
            out.append(low)
    return out


# ── Lecture ──────────────────────────────────────────────────────────────


def _statut(d: dict) -> str:
    """'a_jour', 'en_attente' (demande sans saisie depuis) ou 'jamais'."""
    maj = d.get("taxe_carburant_maj_le") or ""
    dem = d.get("taxe_carburant_demande_le") or ""
    if dem and (not maj or maj < dem):
        return "en_attente"
    if maj:
        return "a_jour"
    return "jamais"


def liste(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT id, nom, actif, langue, contact_email, contact_emails,
                  taxe_carburant_pct, taxe_carburant_maj_le, taxe_carburant_maj_source,
                  taxe_carburant_maj_par, taxe_carburant_demande_le,
                  taxe_carburant_demande_par
           FROM expe_transporteurs
           WHERE actif=1
           ORDER BY nom COLLATE NOCASE"""
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        out.append(
            {
                "id": int(d["id"]),
                "nom": d["nom"],
                "langue": d.get("langue") or "fr",
                "emails": emails_transporteur(d),
                "pct": float(d["taxe_carburant_pct"] or 0),
                "maj_le": d.get("taxe_carburant_maj_le"),
                "maj_source": d.get("taxe_carburant_maj_source"),
                "maj_par": d.get("taxe_carburant_maj_par"),
                "demande_le": d.get("taxe_carburant_demande_le"),
                "demande_par": d.get("taxe_carburant_demande_par"),
                "statut": _statut(d),
            }
        )
    return out


def historique(conn, transporteur_id: int, limite: int = 50) -> list[dict]:
    rows = conn.execute(
        """SELECT id, evenement, source, pct_avant, pct, auteur, created_at
           FROM expe_taxe_carburant_historique
           WHERE transporteur_id=?
           ORDER BY created_at DESC, id DESC
           LIMIT ?""",
        (int(transporteur_id), int(limite)),
    ).fetchall()
    return [dict(r) for r in rows]


def etat_portail(conn, transporteur_id: int) -> dict | None:
    """Ce que le bloc « Taxe carburant » du portail affiche."""
    r = conn.execute(
        """SELECT nom, taxe_carburant_pct, taxe_carburant_maj_le,
                  taxe_carburant_demande_le
           FROM expe_transporteurs WHERE id=? AND actif=1""",
        (int(transporteur_id),),
    ).fetchone()
    if not r:
        return None
    d = dict(r)
    return {
        "transporteur": d["nom"],
        "pct": float(d["taxe_carburant_pct"] or 0),
        "maj_le": d.get("taxe_carburant_maj_le"),
        "demande_le": d.get("taxe_carburant_demande_le"),
        "en_attente": _statut(d) == "en_attente",
    }


# ── Écriture ─────────────────────────────────────────────────────────────


def enregistrer_saisie(
    conn,
    *,
    transporteur_id: int,
    pct: float,
    source: str,
    auteur: str | None,
    pct_avant: float | None = None,
    maj_valeur: bool = True,
) -> dict:
    """Écrit la taxe, la date de mise à jour et une ligne d'historique.

    `maj_valeur=False` quand l'appelant a déjà écrit `taxe_carburant_pct`
    (la fiche transporteur l'enregistre avec les autres champs) : il fournit
    alors `pct_avant` lu avant son UPDATE. Ne commite pas.
    """
    now = now_paris_iso()
    if pct_avant is None:
        r = conn.execute(
            "SELECT taxe_carburant_pct FROM expe_transporteurs WHERE id=?",
            (int(transporteur_id),),
        ).fetchone()
        pct_avant = float(r["taxe_carburant_pct"] or 0) if r else None
    sets = "taxe_carburant_maj_le=?, taxe_carburant_maj_source=?, taxe_carburant_maj_par=?"
    args: list = [now, source, auteur]
    if maj_valeur:
        sets = "taxe_carburant_pct=?, " + sets
        args.insert(0, pct)
    conn.execute(
        f"UPDATE expe_transporteurs SET {sets}, updated_at=? WHERE id=?",
        (*args, now, int(transporteur_id)),
    )
    conn.execute(
        """INSERT INTO expe_taxe_carburant_historique
           (transporteur_id, evenement, source, pct_avant, pct, auteur, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (int(transporteur_id), EV_SAISIE, source, pct_avant, pct, auteur, now),
    )
    return {"pct_avant": pct_avant, "pct": pct, "maj_le": now}


def noter_demande(conn, *, transporteur_id: int, auteur: str | None) -> str:
    now = now_paris_iso()
    conn.execute(
        """UPDATE expe_transporteurs
           SET taxe_carburant_demande_le=?, taxe_carburant_demande_par=?
           WHERE id=?""",
        (now, auteur, int(transporteur_id)),
    )
    conn.execute(
        """INSERT INTO expe_taxe_carburant_historique
           (transporteur_id, evenement, source, auteur, created_at)
           VALUES (?,?,?,?,?)""",
        (int(transporteur_id), EV_DEMANDE, None, auteur, now),
    )
    return now


def token_portail(conn, *, email: str, transporteur_id: int) -> str:
    """Jeton portail de cette adresse, créé s'il n'existe pas.

    Un compte portail créé depuis un destinataire saisi à la main n'a pas de
    `transporteur_id` : on le rattache ici, sans quoi le bloc taxe carburant
    ne saurait pas à quelle fiche écrire.
    """
    email_norm = (email or "").strip().lower()
    row = conn.execute(
        """SELECT id, token, transporteur_id FROM expe_portal_transporteurs
           WHERE LOWER(email)=? AND actif=1 LIMIT 1""",
        (email_norm,),
    ).fetchone()
    if row and row["token"]:
        if row["transporteur_id"] is None:
            conn.execute(
                "UPDATE expe_portal_transporteurs SET transporteur_id=? WHERE id=?",
                (int(transporteur_id), int(row["id"])),
            )
        return str(row["token"])
    token = str(uuid.uuid4())
    conn.execute(
        """INSERT OR IGNORE INTO expe_portal_transporteurs
           (email, token, transporteur_id, prospect_id, created_at, actif)
           VALUES (?,?,?,NULL,?,1)""",
        (email_norm, token, int(transporteur_id), now_paris_iso()),
    )
    row2 = conn.execute(
        """SELECT token FROM expe_portal_transporteurs
           WHERE LOWER(email)=? AND actif=1 LIMIT 1""",
        (email_norm,),
    ).fetchone()
    return str(row2["token"]) if row2 and row2["token"] else token


def destinataires_confirmation(demande_par: str | None) -> tuple[str, list[str]]:
    """(to, cc) de l'email interne : l'auteur de la demande, la boîte du
    service en copie. Sans demande en cours, la boîte du service seule."""
    service = (EXPE_DEVIS_FROM or "").strip()
    auteur = (demande_par or "").strip()
    if auteur and "@" in auteur:
        cc = [service] if service and service.lower() != auteur.lower() else []
        return auteur, cc
    return service, []


# ── Emails ───────────────────────────────────────────────────────────────


def _date_courte(iso: str | None, lang: str = "fr") -> str:
    s = (iso or "")[:10]
    if lang == "fr" and len(s) == 10 and s[4] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def fmt_pct(pct, lang: str = "fr") -> str:
    if pct is None:
        return "—"
    txt = f"{float(pct):.2f}".rstrip("0").rstrip(".")
    return (txt if lang == "en" else txt.replace(".", ",")) + " %"


def _textes_demande(lang: str) -> dict[str, str]:
    org = APP_ORG_NAME
    b = '<strong style="color:#0f172a">'
    if lang == "en":
        return {
            "subtitle": "Fuel surcharge update",
            "hello": "Hello,",
            "intro": (
                f"{b}{org}</strong> is updating the fuel surcharge applied to your "
                "transport rates. Please enter your current rate on your carrier page."
            ),
            "carrier": "Carrier",
            "current": "Rate on file",
            "current_none": "No rate on file",
            "updated": "last updated",
            "how_title": "How to update it",
            "step1": "Click the button below — it opens your personal page, no account or password required.",
            "step2": f"Enter your {b}fuel surcharge (%)</strong> in the block at the top of the page.",
            "step3": "Submit. Our shipping department is notified immediately.",
            "hint": "Enter 0 if the fuel surcharge is already included in your prices.",
            "cta": "Enter my fuel surcharge",
            "copy_link": "If the button does not work, copy this link into your browser:",
            "regards": "Kind regards,",
            "service": f"{org} — Shipping department",
            "footer": f"{org} carrier portal — personal link, do not share.",
            "subject": f"Fuel surcharge — update requested — {org}",
        }
    return {
        "subtitle": "Mise à jour taxe carburant",
        "hello": "Bonjour,",
        "intro": (
            f"{b}{org}</strong> met à jour la taxe carburant appliquée à vos tarifs "
            "de transport. Merci de renseigner votre taux en vigueur sur votre espace transporteur."
        ),
        "carrier": "Transporteur",
        "current": "Taux enregistré",
        "current_none": "Aucun taux enregistré",
        "updated": "mis à jour le",
        "how_title": "Comment la renseigner",
        "step1": "Cliquez sur le bouton ci-dessous — il ouvre votre page personnelle, sans compte ni mot de passe.",
        "step2": f"Saisissez votre {b}taxe carburant (%)</strong> dans le bloc en haut de la page.",
        "step3": "Validez. Le service expéditions est prévenu immédiatement.",
        "hint": "Saisissez 0 si la taxe carburant est déjà incluse dans vos prix.",
        "cta": "Renseigner ma taxe carburant",
        "copy_link": "Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :",
        "regards": "Cordialement,",
        "service": f"{org} — Service expéditions",
        "footer": f"Portail transporteur {org} — lien personnel, ne pas partager.",
        "subject": f"Taxe carburant — mise à jour demandée — {org}",
    }


def email_demande_taxe(
    *,
    nom_transporteur: str,
    portail_lien: str,
    langue: str | None,
    pct_actuel: float | None,
    maj_le: str | None,
    user_nom: str,
) -> tuple[str, str]:
    """Sujet et corps HTML — demande de mise à jour au transporteur.

    Même enveloppe et même construction que la demande de tarif (marque de
    l'entreprise en tête, trois étapes, bouton vers le portail) : le
    transporteur reconnaît le canal qu'il utilise déjà pour les devis.
    """
    from app.services.email_service import (
        _email_bouton,
        _email_detail_table,
        _esc,
        email_mysifa_layout,
    )

    lang = "en" if str(langue or "").lower().startswith("en") else "fr"
    s = _textes_demande(lang)

    if maj_le:
        actuel = (
            f"{_esc(fmt_pct(pct_actuel, lang))} "
            f'<span style="color:#64748b;font-weight:400">— {_esc(s["updated"])} '
            f"{_esc(_date_courte(maj_le, lang))}</span>"
        )
    elif pct_actuel:
        actuel = _esc(fmt_pct(pct_actuel, lang))
    else:
        actuel = f'<span style="color:#64748b;font-weight:400">{_esc(s["current_none"])}</span>'
    detail = _email_detail_table(
        [(s["carrier"], _esc(nom_transporteur)), (s["current"], actuel)]
    )

    # Même tableau d'étapes que la demande de tarif : Outlook rend une <ol>
    # avec ses propres marges, une table tient partout.
    def _etape(num: str, texte: str) -> str:
        return (
            "<tr>"
            "<td style=\"padding:0 10px 10px 0;vertical-align:top;width:22px;font-size:15px;"
            f"font-weight:800;color:#0891b2;line-height:1.5\">{num}.</td>"
            "<td style=\"padding:0 0 10px;vertical-align:top;font-size:14px;color:#475569;"
            f"line-height:1.6\">{texte}</td>"
            "</tr>"
        )

    how = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="width:100%;margin:0 0 4px">
      <tr>
        <td bgcolor="#f8fafc" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#0891b2;font-weight:800;margin-bottom:12px">
            {_esc(s["how_title"])}
          </div>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="width:100%;border-collapse:collapse">
            {_etape("1", s["step1"])}
            {_etape("2", s["step2"])}
            {_etape("3", s["step3"])}
          </table>
          <div style="font-size:12px;color:#94a3b8;line-height:1.6">{_esc(s["hint"])}</div>
        </td>
      </tr>
    </table>"""

    lien = (portail_lien or "").strip()
    cta = ""
    if lien:
        cta = _email_bouton(f"{lien}?lang={lang}#carburant", s["cta"], s["copy_link"])

    inner = f"""
    <p style="margin:0 0 14px;font-size:15px;color:#0f172a;font-weight:600">{_esc(s["hello"])}</p>
    <p style="margin:0 0 22px;font-size:14px;color:#475569;line-height:1.65">{s["intro"]}</p>
    {detail}
    {how}
    {cta}
    <p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.65">
      {_esc(s["regards"])}<br>
      <strong style="color:#0f172a;font-size:14px">{_esc(user_nom)}</strong><br>
      {_esc(s["service"])}
    </p>"""

    body = email_mysifa_layout(
        subtitle=s["subtitle"],
        body_html=inner,
        footer_note=s["footer"],
        footer_contact=True,
        marque=APP_ORG_NAME,
        lang=lang,
    )
    return s["subject"], body


def email_taxe_recue(
    *,
    nom_transporteur: str,
    email_saisie: str | None,
    pct_avant: float | None,
    pct: float,
) -> tuple[str, str]:
    """Sujet et corps HTML — notification interne « taxe carburant reçue »."""
    from app.services.email_service import _esc, email_mysifa_layout

    if pct_avant is None:
        evolution = "—"
    elif abs(float(pct_avant) - float(pct)) < 0.005:
        evolution = "Inchangée"
    else:
        ecart = float(pct) - float(pct_avant)
        evolution = ("+" if ecart > 0 else "−") + fmt_pct(abs(ecart)).replace(" %", " pt")

    subject = f"[MySifa] Taxe carburant — {nom_transporteur} — {fmt_pct(pct)}"
    qui = f" ({_esc(email_saisie)})" if email_saisie else ""

    # Couleurs pleines et non rgba() : Outlook bureau ignore rgba.
    def _tuile(lbl: str, val: str, fond: str, bord: str, couleur: str) -> str:
        return (
            f'<td bgcolor="{fond}" style="background:{fond};border:1px solid {bord};'
            'border-radius:10px;padding:10px 14px">'
            f'<div style="font-size:11px;color:{couleur};text-transform:uppercase;'
            f'letter-spacing:.5px;font-weight:800">{_esc(lbl)}</div>'
            f'<div style="font-size:16px;color:#0f172a;font-weight:900">{_esc(val)}</div></td>'
        )

    inner = f"""
    <p style="margin:0 0 14px;color:#0f172a">
      <strong>{_esc(nom_transporteur)}</strong>{qui} a renseigné sa taxe carburant sur le portail transporteur.
    </p>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px">
      <tr>
        {_tuile("Nouveau taux", fmt_pct(pct), "#ecfeff", "#a5f3fc", "#0891b2")}
        <td width="12"></td>
        {_tuile("Précédent", fmt_pct(pct_avant), "#f8fafc", "#e2e8f0", "#64748b")}
        <td width="12"></td>
        {_tuile("Évolution", evolution, "#f8fafc", "#e2e8f0", "#64748b")}
      </tr>
    </table>
    <p style="margin:0;color:#475569;font-size:13px">
      Le comparateur de tarifs applique ce taux dès maintenant.
    </p>"""
    body = email_mysifa_layout(
        subtitle="Taxe carburant reçue",
        body_html=inner,
        cta_href=f"{public_base_url()}/expe#carburant",
        cta_label="Ouvrir MyExpé",
    )
    return subject, body
