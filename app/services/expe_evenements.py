"""MySifa — MyExpé : journal d'engagement transporteur sur les demandes de tarif.

Transposition stricte de `ao_evenements` au module devis transporteurs. Une
seule table, `expe_devis_evenements`, agrège tous les signaux qu'un
transporteur laisse sur une demande de prix : envoi de la demande, ouverture
de l'email, consultation du portail, dépôt d'une offre, notification
d'attribution.

L'unité de suivi est la LIGNE DE RÉPONSE (`expe_devis_reponses`), pas le
transporteur : un même transporteur sollicité sur deux demandes doit pouvoir
avoir ouvert l'une et ignoré l'autre. C'est la différence avec le token
portail, qui lui est par email et transverse à toutes les demandes.

Les deux principes de `ao_evenements` sont repris tels quels :

1. **On conserve tout, on ne compte pas tout.** Une ouverture d'email n'est
   pas une preuve de lecture. Les hits de préchargement (Apple MPP,
   passerelles antispam) sont enregistrés avec `fiable=0` et un `motif`,
   jamais supprimés, mais exclus des compteurs affichés.

2. **Le journal ne bloque jamais un envoi.** `log_evenement()` avale ses
   exceptions : perdre une ligne de timeline est sans gravité, perdre une
   demande de tarif ne l'est pas.

L'heuristique de fiabilité (`classer_ouverture`, listes de robots et de
proxys) n'est pas dupliquée : elle est importée de `ao_evenements`. Un
faux positif Gmail se corrige à un seul endroit pour les deux modules.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Source unique de vérité pour « ce hit est-il un humain ? ». Voir le module
# MyAO : les listes de robots et de proxys de webmail y sont commentées une
# par une, les dupliquer ici garantirait qu'elles divergent.
from app.services.ao_evenements import (  # noqa: F401
    DEDUP_SECONDES,
    PREFETCH_SECONDES,
    classer_ouverture,
)

logger = logging.getLogger(__name__)

_PARIS = ZoneInfo("Europe/Paris")

# ─── Vocabulaire ──────────────────────────────────────────────────

CANAL_EMAIL = "email"
CANAL_PORTAIL = "portail"
CANAL_INTERNE = "interne"

EV_EMAIL_ENVOYE = "email_envoye"
EV_EMAIL_ECHEC = "email_echec"
EV_EMAIL_OUVERT = "email_ouvert"
EV_EMAIL_ATTRIBUTION = "email_attribution"
EV_PORTAIL_OUVERT = "portail_ouvert"
EV_REPONSE_DEPOSEE = "reponse_deposee"
EV_REPONSE_SAISIE = "reponse_saisie"
EV_OFFRE_RETENUE = "offre_retenue"

LIBELLES = {
    EV_EMAIL_ENVOYE: "Demande de tarif envoyée par email",
    EV_EMAIL_ECHEC: "Échec d'envoi de l'email",
    EV_EMAIL_OUVERT: "Email ouvert",
    EV_EMAIL_ATTRIBUTION: "Confirmation d'attribution envoyée",
    EV_PORTAIL_OUVERT: "Portail consulté",
    EV_REPONSE_DEPOSEE: "Offre déposée sur le portail",
    EV_REPONSE_SAISIE: "Offre saisie en interne",
    EV_OFFRE_RETENUE: "Offre retenue",
}

# Deux emails seulement partent vers un transporteur, contre trois en MyAO :
# la demande de tarif, et la confirmation d'attribution. Le jour où une
# relance sera ajoutée, elle prendra le code `rel` et rien d'autre ne bouge.
CONTEXTES = {
    "rfq": "demande de tarif",
    "attr": "attribution",
    "rel": "relance",
}

EMAILS_SORTANTS = (EV_EMAIL_ENVOYE, EV_EMAIL_ATTRIBUTION)

_CONTEXTE_EVENEMENT = {
    "rfq": EV_EMAIL_ENVOYE,
    "attr": EV_EMAIL_ATTRIBUTION,
    "rel": EV_EMAIL_ENVOYE,
}


def now_paris_iso() -> str:
    """Horodatage maison : `%Y-%m-%dT%H:%M:%S` heure Paris, sans timezone."""
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _parse_iso(value: object) -> datetime | None:
    txt = str(value or "").strip()
    if not txt:
        return None
    try:
        return datetime.fromisoformat(txt[:19])
    except Exception:
        return None


def date_email_reference(
    conn,
    reponse_id: int,
    contexte: str | None = None,
    sent_at: object = None,
) -> str | None:
    """Date de l'envoi auquel rattacher un hit du pixel.

    `expe_devis_reponses.sent_at` est réécrit à chaque renvoi, donc plus fiable
    que son équivalent MyAO — mais on garde la même mécanique : on prend la
    date du dernier email réellement parti pour ce contexte, sinon le plus
    récent tous contextes confondus, sinon `sent_at`. Sans cela, la fenêtre
    anti-préchargement ne protégerait que le premier envoi.
    """
    cible = _CONTEXTE_EVENEMENT.get(str(contexte or "").strip().lower())
    for types in ([cible] if cible else None, list(EMAILS_SORTANTS)):
        if not types:
            continue
        try:
            trous = ",".join("?" * len(types))
            row = conn.execute(
                f"""SELECT MAX(date) AS d FROM expe_devis_evenements
                    WHERE reponse_id=? AND type_evenement IN ({trous})""",
                (int(reponse_id), *types),
            ).fetchone()
        except Exception as exc:
            logger.warning("expe_evenements.date_email_reference: %s", exc)
            break
        if row is not None and row["d"]:
            return str(row["d"])
    return str(sent_at) if sent_at else None


# ─── Écriture ─────────────────────────────────────────────────────

def token_pixel(conn, reponse_id: int) -> str | None:
    """Token de pixel de la ligne de réponse, créé au besoin.

    Distinct du token portail (`expe_portal_transporteurs.token`) pour la même
    raison qu'en MyAO : le pixel transite par les proxys d'images, qui le
    mettent en cache et le journalisent. Y faire passer le token d'accès au
    portail reviendrait à diffuser un accès en clair.
    """
    try:
        row = conn.execute(
            "SELECT token_pixel FROM expe_devis_reponses WHERE id=?",
            (int(reponse_id),),
        ).fetchone()
        if row is None:
            return None
        existant = row["token_pixel"] if "token_pixel" in row.keys() else None
        if existant:
            return str(existant)
        nouveau = str(uuid.uuid4())
        conn.execute(
            "UPDATE expe_devis_reponses SET token_pixel=? WHERE id=?",
            (nouveau, int(reponse_id)),
        )
        return nouveau
    except Exception as exc:
        logger.warning("expe_evenements.token_pixel: %s", exc)
        return None


def url_pixel(token: str | None, contexte: str = "rfq") -> str | None:
    """URL absolue du pixel de suivi, ou None si le suivi est impossible."""
    if not token:
        return None
    try:
        from config import public_base_url

        base = str(public_base_url() or "").rstrip("/")
    except Exception:
        base = ""
    if not base:
        return None
    ctx = contexte if contexte in CONTEXTES else "rfq"
    return f"{base}/portail/expe/px/{token}.gif?e={ctx}"


def log_evenement(
    conn,
    *,
    reponse_id: int,
    demande_id: int | None = None,
    canal: str,
    type_evenement: str,
    date: str | None = None,
    fiable: bool = True,
    motif: str | None = None,
    user_agent: str | None = None,
    meta: dict | None = None,
    dedup_secondes: int = 0,
) -> bool:
    """Enregistre un événement. Ne lève jamais. Retourne True si écrit."""
    try:
        quand = date or now_paris_iso()
        if dedup_secondes > 0:
            recent = _parse_iso(quand)
            if recent is not None:
                seuil = (recent - timedelta(seconds=dedup_secondes)).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                # La fiabilité fait partie de la clé de dédup : sans elle, un
                # préchargement enregistré à T ferait disparaître la vraie
                # ouverture arrivée à T+40s.
                deja = conn.execute(
                    """SELECT 1 FROM expe_devis_evenements
                       WHERE reponse_id=? AND type_evenement=?
                         AND fiable=? AND date>=?
                       LIMIT 1""",
                    (int(reponse_id), type_evenement, 1 if fiable else 0, seuil),
                ).fetchone()
                if deja:
                    return False
        if demande_id is None:
            row = conn.execute(
                "SELECT demande_id FROM expe_devis_reponses WHERE id=?",
                (int(reponse_id),),
            ).fetchone()
            demande_id = int(row["demande_id"]) if row else None
        conn.execute(
            """INSERT INTO expe_devis_evenements
               (reponse_id, demande_id, canal, type_evenement, date,
                fiable, motif, user_agent, meta)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                int(reponse_id),
                int(demande_id) if demande_id is not None else None,
                canal,
                type_evenement,
                quand,
                1 if fiable else 0,
                motif,
                (user_agent or "")[:300] or None,
                json.dumps(meta, ensure_ascii=False) if meta else None,
            ),
        )
        return True
    except Exception as exc:
        # Convention CLAUDE.md : une écriture annexe ne fait jamais échouer
        # l'action métier qui l'a déclenchée.
        logger.warning("expe_evenements.log_evenement (%s): %s", type_evenement, exc)
        return False


def log_par_email(
    conn,
    *,
    email: str | None,
    canal: str,
    type_evenement: str,
    date: str | None = None,
    demande_id: int | None = None,
    user_agent: str | None = None,
    dedup_secondes: int = 0,
) -> int:
    """Journalise un événement sur toutes les lignes ouvertes d'un email.

    Le portail transporteur est indexé par email, pas par demande : une visite
    ne dit pas laquelle des demandes en attente a été regardée. Plutôt que
    d'inventer un rattachement, on marque toutes les lignes encore sans
    réponse — c'est exactement le périmètre que la visite peut concerner.
    Retourne le nombre de lignes touchées.
    """
    mail = (email or "").strip().lower()
    if not mail:
        return 0
    try:
        params: list = [mail]
        filtre_demande = ""
        if demande_id is not None:
            filtre_demande = " AND demande_id=?"
            params.append(int(demande_id))
        rows = conn.execute(
            f"""SELECT id, demande_id FROM expe_devis_reponses
                WHERE LOWER(TRIM(COALESCE(destinataire_email,''))) = ?
                  AND statut IN ('envoyee','ouvert','echec'){filtre_demande}""",
            params,
        ).fetchall()
    except Exception as exc:
        logger.warning("expe_evenements.log_par_email: %s", exc)
        return 0
    n = 0
    for r in rows:
        if log_evenement(
            conn,
            reponse_id=int(r["id"]),
            demande_id=int(r["demande_id"]) if r["demande_id"] is not None else None,
            canal=canal,
            type_evenement=type_evenement,
            date=date,
            user_agent=user_agent,
            dedup_secondes=dedup_secondes,
        ):
            n += 1
    return n


# ─── Lecture ──────────────────────────────────────────────────────

_VIDE = {
    "nb_ouvertures_email": 0,
    "email_ouvert_le": None,
    "email_ouvert_dernier": None,
    "ouvertures_ecartees": 0,
    "motif_ecarte": None,
    "nb_visites_portail": 0,
    "portail_ouvert_le": None,
    "dernier_signal": None,
}


def resume_par_reponse(conn, demande_id: int) -> dict[int, dict]:
    """Agrégat d'engagement par destinataire d'une demande de tarif.

    Ne compte que les événements `fiable=1`. Les hits écartés sont renvoyés
    séparément dans `ouvertures_ecartees` : l'information reste consultable
    dans la timeline, sans polluer le compteur affiché.
    """
    out: dict[int, dict] = {}
    try:
        rows = conn.execute(
            """SELECT reponse_id AS rid, type_evenement AS t, fiable,
                      COUNT(*) AS n, MIN(date) AS premier, MAX(date) AS dernier
               FROM expe_devis_evenements
               WHERE demande_id=?
               GROUP BY reponse_id, type_evenement, fiable""",
            (int(demande_id),),
        ).fetchall()
    except Exception as exc:
        logger.warning("expe_evenements.resume_par_reponse: %s", exc)
        return out

    for r in rows:
        rid = int(r["rid"])
        entry = out.setdefault(rid, dict(_VIDE))
        t = str(r["t"])
        fiable = int(r["fiable"] or 0) == 1
        if t == EV_EMAIL_OUVERT:
            if fiable:
                entry["nb_ouvertures_email"] = int(r["n"])
                entry["email_ouvert_le"] = r["premier"]
                entry["email_ouvert_dernier"] = r["dernier"]
            else:
                entry["ouvertures_ecartees"] = int(r["n"])
        elif t == EV_PORTAIL_OUVERT and fiable:
            entry["nb_visites_portail"] = int(r["n"])
            entry["portail_ouvert_le"] = r["premier"]
        if fiable and t not in (EV_EMAIL_ENVOYE, EV_EMAIL_ATTRIBUTION):
            dernier = entry.get("dernier_signal")
            if not dernier or str(r["dernier"]) > str(dernier):
                entry["dernier_signal"] = r["dernier"]

    # Motif du dernier hit écarté : sans lui, « Ouverture non confirmée » ne
    # dit pas SI c'est un préchargement, un robot ou un UA manquant — or c'est
    # exactement ce qu'on veut savoir en regardant la ligne.
    try:
        for r in conn.execute(
            """SELECT reponse_id AS rid, motif, MAX(date) AS d
               FROM expe_devis_evenements
               WHERE demande_id=? AND type_evenement=? AND fiable=0
               GROUP BY reponse_id""",
            (int(demande_id), EV_EMAIL_OUVERT),
        ).fetchall():
            entry = out.get(int(r["rid"]))
            if entry is not None:
                entry["motif_ecarte"] = r["motif"]
    except Exception as exc:
        logger.warning("expe_evenements.resume_par_reponse (motifs): %s", exc)
    return out


def timeline(conn, reponse_id: int, limite: int = 200) -> list[dict]:
    """Événements d'un destinataire, du plus récent au plus ancien."""
    try:
        rows = conn.execute(
            """SELECT id, canal, type_evenement, date, fiable, motif, user_agent, meta
               FROM expe_devis_evenements
               WHERE reponse_id=?
               ORDER BY date DESC, id DESC
               LIMIT ?""",
            (int(reponse_id), int(limite)),
        ).fetchall()
    except Exception as exc:
        logger.warning("expe_evenements.timeline: %s", exc)
        return []

    out: list[dict] = []
    for r in rows:
        meta = None
        if r["meta"]:
            try:
                meta = json.loads(r["meta"])
            except Exception:
                meta = None
        libelle = LIBELLES.get(str(r["type_evenement"]), str(r["type_evenement"]))
        if str(r["type_evenement"]) == EV_EMAIL_OUVERT and isinstance(meta, dict):
            ctx = CONTEXTES.get(str(meta.get("email") or ""))
            if ctx:
                libelle = f"{libelle} ({ctx})"
        out.append(
            {
                "id": int(r["id"]),
                "canal": r["canal"],
                "type": r["type_evenement"],
                "libelle": libelle,
                "date": r["date"],
                "fiable": int(r["fiable"] or 0) == 1,
                "motif": r["motif"],
                "user_agent": r["user_agent"],
                "meta": meta,
            }
        )
    return out
