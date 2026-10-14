"""Envoi d'une pièce par e-mail, PDF en pièce jointe.

Destinataires proposés : les interlocuteurs du tiers cochés pour ce document
sur la fiche client (devis, ARC, BL, facture) ; à défaut, l'e-mail de
facturation (factures) ou l'e-mail du tiers. L'utilisateur confirme ou corrige
avant l'envoi. L'envoi passe par le service e-mail de MySifa
(`email_service.send_email` : Microsoft Graph ou SMTP), qui ne lève jamais.
"""
from __future__ import annotations

import html
import re
from datetime import datetime

from app.services.gc import fichiers, pdf, pieces

# Case de la fiche client qui désigne les destinataires de chaque document.
DRAPEAU = {"devis": "envoi_devis", "marche": "envoi_arc", "commande": "envoi_arc", "bl": "envoi_bl",
           "facture": "envoi_facture", "avoir": "envoi_facture", "aof": "envoi_aof", "cde_fournisseur": "envoi_cde"}
NOM_DOC = {"devis": "notre devis", "marche": "notre marché", "commande": "la confirmation de votre commande",
           "bl": "le bon de livraison", "facture": "notre facture", "avoir": "notre avoir",
           "aof": "notre demande de prix", "cde_fournisseur": "notre bon de commande"}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def preparation(conn, piece_id: int) -> dict:
    from app.web.erp2.impression import donnees
    p = pieces.charger(conn, piece_id)
    if not p["numero"]:
        raise pieces.ErreurPiece("Un brouillon ne s'envoie pas : valider la pièce d'abord.")
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (p["tiers_id"],)).fetchone()
    drapeau = DRAPEAU.get(p["type"])
    contacts = [dict(r) for r in conn.execute(
        "SELECT * FROM gc_tiers_contacts WHERE tiers_id=? AND actif=1 AND email!='' ORDER BY id", (t["id"],)).fetchall()]
    for c in contacts:
        c["propose"] = bool(drapeau and c.get(drapeau))
    proposes = [c["email"] for c in contacts if c["propose"]]
    if not proposes:
        repli = (t["email_facturation"] if p["type"] in ("facture", "avoir") else "") or t["email"]
        if repli:
            proposes = [repli]
    soc = fichiers.lire_societe(conn)
    D = donnees(conn, piece_id)
    objet = f"{D['titre_complet']} — {soc.get('raison_sociale') or ''}".strip(" —")
    message = (f"Madame, Monsieur,\n\nVeuillez trouver ci-joint {NOM_DOC.get(p['type'], 'notre document')} "
               f"n° {p['numero']} du {p['date_piece'][8:10]}/{p['date_piece'][5:7]}/{p['date_piece'][:4]}"
               + (f" (votre référence : {p['ref_tiers']})" if p.get("ref_tiers") else "") + ".\n\n"
               "Nous restons à votre disposition pour toute question.\n\nCordialement,\n"
               + (soc.get("raison_sociale") or ""))
    envois = [dict(r) for r in conn.execute(
        "SELECT envoye_le, destinataires, reussi, envoye_par FROM gc_envois WHERE piece_id=? ORDER BY id DESC",
        (piece_id,)).fetchall()]
    return {"contacts": contacts, "destinataires": proposes, "objet": objet, "message": message,
            "fichier": nom_fichier(D), "envois": envois}


def nom_fichier(D: dict) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", f"{D['titre']} {D['numero']}".encode("ascii", "ignore").decode()).strip("_")
    return (base or "document") + ".pdf"


def envoyer(conn, piece_id: int, destinataires: list[str], copie: list[str], objet: str, message: str,
            user: dict | None = None, envoyeur=None) -> bool:
    """Génère le PDF et l'envoie. `envoyeur` : fonction d'envoi (tests) ; par
    défaut `email_service.send_email`. Trace l'envoi, réussi ou non."""
    from app.web.erp2.impression import donnees
    from app.services.email_service import email_mysifa_layout
    dest = [d.strip() for d in destinataires if d and d.strip()]
    cc = [d.strip() for d in (copie or []) if d and d.strip()]
    if not dest:
        raise pieces.ErreurPiece("Aucun destinataire.")
    mauvais = [d for d in dest + cc if not _EMAIL.match(d)]
    if mauvais:
        raise pieces.ErreurPiece("Adresse e-mail invalide : " + ", ".join(mauvais) + ".")
    p = pieces.charger(conn, piece_id)
    if not p["numero"]:
        raise pieces.ErreurPiece("Un brouillon ne s'envoie pas : valider la pièce d'abord.")
    D = donnees(conn, piece_id)
    contenu = pdf.generer(D)
    fichier = nom_fichier(D)
    soc = fichiers.lire_societe(conn)
    corps = "".join(f"<p style='margin:0 0 10px'>{html.escape(par).replace(chr(10), '<br>')}</p>"
                    for par in (message or "").split("\n\n") if par.strip())
    html_mail = email_mysifa_layout(subtitle=html.escape(D["titre_complet"]), body_html=corps,
                                    marque=soc.get("raison_sociale") or "SIFA")
    if envoyeur is None:
        from app.services.email_service import send_email as envoyeur
    ok = bool(envoyeur(dest, objet or D["titre_complet"], html_mail, cc=cc or None,
                       attachments=[{"filename": fichier, "content": contenu, "mime": "application/pdf"}]))
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        """INSERT INTO gc_envois (piece_id, envoye_le, destinataires, copie, objet, fichier, reussi, envoye_par)
           VALUES (?,?,?,?,?,?,?,?)""",
        (piece_id, now, ", ".join(dest), ", ".join(cc), objet or "", fichier, 1 if ok else 0,
         str((user or {}).get("nom") or "")))
    if ok:
        conn.execute("UPDATE gc_pieces SET envoye_le=COALESCE(envoye_le, ?), imprime_le=COALESCE(imprime_le, ?) WHERE id=?",
                     (now, now, piece_id))
    return ok
