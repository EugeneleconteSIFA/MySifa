"""MySifa — MyAO : journal d'engagement fournisseur (multi-canal).

Une seule table, `ao_evenements`, agrège tous les signaux qu'un fournisseur
laisse sur un appel d'offres : envoi de l'invitation, ouverture de l'email,
ouverture du portail, dépôt d'une réponse — et, quand le canal WhatsApp sera
branché, les statuts `envoyé / délivré / lu` remontés par le webhook Meta.
C'est elle qui alimente la timeline unique du panneau fournisseur.

Deux principes structurants :

1. **On conserve tout, on ne compte pas tout.** Une ouverture d'email n'est pas
   une preuve de lecture : Apple Mail Privacy Protection précharge les images
   dès la réception, les passerelles antispam d'entreprise aussi. Ces hits sont
   enregistrés avec `fiable=0` et un `motif`, jamais supprimés — mais exclus des
   compteurs affichés. Voir `classer_ouverture()`.

2. **Le journal ne bloque jamais un envoi.** `log_evenement()` avale ses
   exceptions (convention CLAUDE.md : ne jamais faire échouer une saisie pour
   une écriture annexe). Perdre une ligne de timeline est sans gravité ; perdre
   un appel d'offres ne l'est pas.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_PARIS = ZoneInfo("Europe/Paris")

# ─── Vocabulaire ──────────────────────────────────────────────────

CANAL_EMAIL = "email"
CANAL_WHATSAPP = "whatsapp"
CANAL_PORTAIL = "portail"

EV_EMAIL_ENVOYE = "email_envoye"
EV_EMAIL_ECHEC = "email_echec"
EV_EMAIL_OUVERT = "email_ouvert"
EV_PORTAIL_OUVERT = "portail_ouvert"
EV_REPONSE_DEPOSEE = "reponse_deposee"
EV_MESSAGE_RECU = "message_recu"
EV_EMAIL_MESSAGE = "email_message"
EV_EMAIL_ATTRIBUTION = "email_attribution"
# Réservés au chantier WhatsApp (webhook Meta) — déjà nommés pour que la
# timeline et les libellés n'aient pas à bouger le jour de la bascule.
EV_WA_ENVOYE = "wa_envoye"
EV_WA_DELIVRE = "wa_delivre"
EV_WA_LU = "wa_lu"
EV_WA_ECHEC = "wa_echec"

LIBELLES = {
    EV_EMAIL_ENVOYE: "Invitation envoyée par email",
    EV_EMAIL_ECHEC: "Échec d'envoi de l'email",
    EV_EMAIL_OUVERT: "Email ouvert",
    EV_PORTAIL_OUVERT: "Portail consulté",
    EV_REPONSE_DEPOSEE: "Offre déposée",
    EV_MESSAGE_RECU: "Message reçu du fournisseur",
    EV_EMAIL_MESSAGE: "Message envoyé par email",
    EV_EMAIL_ATTRIBUTION: "Attribution notifiée par email",
    EV_WA_ENVOYE: "Invitation envoyée par WhatsApp",
    EV_WA_DELIVRE: "WhatsApp remis",
    EV_WA_LU: "WhatsApp lu",
    EV_WA_ECHEC: "Échec d'envoi WhatsApp",
}

# Trois emails distincts peuvent partir vers un fournisseur, et chacun porte
# son pixel. Le code de contexte voyage dans l'URL du pixel (?e=…) pour que la
# timeline sache LEQUEL a été ouvert : « email ouvert » sans préciser lequel ne
# se lit pas quand une relance suit l'invitation de trois jours.
CONTEXTES = {
    "inv": "invitation",
    "msg": "message",
    "attr": "attribution",
}

# Evenements correspondant a un email reellement parti vers le fournisseur.
EMAILS_SORTANTS = (EV_EMAIL_ENVOYE, EV_EMAIL_MESSAGE, EV_EMAIL_ATTRIBUTION)

_CONTEXTE_EVENEMENT = {
    "inv": EV_EMAIL_ENVOYE,
    "msg": EV_EMAIL_MESSAGE,
    "attr": EV_EMAIL_ATTRIBUTION,
}


# ─── Fiabilité des ouvertures d'email ─────────────────────────────

# Un hit du pixel qui arrive dans les secondes suivant l'envoi ne vient pas
# d'un humain : c'est un préchargement (Apple MPP, relais de sécurité). Le
# seuil est volontairement large — un fournisseur qui ouvre réellement en
# moins de 20 s est rare, et le classer « préchargement » ne perd rien
# puisque son ouverture suivante, elle, comptera.
PREFETCH_SECONDES = 20

# Deux hits rapprochés = le même affichage (client mail qui recharge l'image,
# volet de prévisualisation). On les enregistre une seule fois.
DEDUP_SECONDES = 90

# Robots connus. Liste volontairement courte : chaque motif est un fetcher
# qui s'annonce, pas une heuristique. Apple MPP, lui, ne s'annonce PAS et
# n'est attrapé que par la fenêtre de préchargement ci-dessus.
# Proxys d'images des webmails. Gmail et Yahoo ne prechargent PAS a la
# livraison : ils passent l'image par leur proxy au moment ou le message est
# affiche. Ce sont donc de vraies ouvertures - simplement depourvues de geo et
# de device, et non repetables (l'image est mise en cache, les ouvertures
# suivantes ne refont pas de hit). Les ecarter reviendrait a etre aveugle sur
# tous les fournisseurs en Gmail / Google Workspace, soit pres d'un tiers des
# ouvertures constatees.
UA_PROXIES = {
    "googleimageproxy": "Gmail",
    "googleusercontent": "Gmail",
    "yahoomailproxy": "Yahoo Mail",
}

UA_ROBOTS = (
    "proofpoint",
    "barracuda",
    "mimecast",
    "symantec",
    "messagelabs",
    "microsoft-webdav",
    "bingpreview",
    "slackbot",
    "whatsapp",
    "facebookexternalhit",
    "python-requests",
    "curl/",
    "wget/",
)


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


def classer_ouverture(
    date_envoi: object,
    user_agent: str | None,
    date_ouverture: str | None = None,
) -> tuple[bool, str | None]:
    """Décide si un hit du pixel compte comme une vraie ouverture.

    Retourne `(fiable, motif)`. `motif` est None quand le hit est retenu sans
    reserve ; il peut etre renseigne sur un hit RETENU (proxy de webmail), la
    fiabilite et le motif etant deux informations distinctes.
    """
    ua = (user_agent or "").strip().lower()
    for robot in UA_ROBOTS:
        if robot in ua:
            return False, f"robot ({robot.rstrip('/')})"

    proxy = None
    for empreinte, nom in UA_PROXIES.items():
        if empreinte in ua:
            proxy = nom
            break

    if not ua:
        # Un vrai client mail envoie toujours un User-Agent en chargeant une
        # image. Son absence n'est pas une preuve de robot pour autant : on
        # ecarte le hit du compteur, mais le motif dit que c'est indecis.
        return False, "sans user-agent — non concluant"

    # Le prechargement prime sur tout le reste, proxy compris : un hit qui
    # arrive dans les secondes suivant l'envoi ne vient pas d'un humain.
    envoi = _parse_iso(date_envoi)
    hit = _parse_iso(date_ouverture) or datetime.now(_PARIS).replace(tzinfo=None)
    if envoi is not None:
        delta = (hit - envoi).total_seconds()
        if 0 <= delta < PREFETCH_SECONDES:
            return False, "préchargement (moins de %ds après l'envoi)" % PREFETCH_SECONDES

    if proxy:
        # Retenu comme ouverture, mais on garde la trace : ni geo ni device, et
        # pas de comptage des ouvertures suivantes (cache du proxy).
        return True, f"proxifié ({proxy})"
    return True, None


def date_email_reference(
    conn,
    ao_fournisseur_id: int,
    contexte: str | None = None,
    date_envoi: object = None,
) -> str | None:
    """Date de l'envoi auquel rattacher un hit du pixel.

    `ao_fournisseurs.date_envoi` ne bouge plus apres l'invitation : s'y fier
    revient a ne detecter les prechargements que sur le premier email, jamais
    sur les relances - or c'est sur la relance qu'on regarde le plus si le
    fournisseur a vu le message. On prend donc la date du dernier email
    reellement parti : celui du contexte vise (`inv` / `msg` / `attr`) quand il
    est connu, sinon le plus recent tous contextes confondus.
    """
    cible = _CONTEXTE_EVENEMENT.get(str(contexte or "").strip().lower())
    tentatives = ([cible] if cible else None, list(EMAILS_SORTANTS))
    for types in tentatives:
        if not types:
            continue
        try:
            trous = ",".join("?" * len(types))
            row = conn.execute(
                f"""SELECT MAX(date) AS d FROM ao_evenements
                    WHERE ao_fournisseur_id=? AND type_evenement IN ({trous})""",
                (int(ao_fournisseur_id), *types),
            ).fetchone()
        except Exception as exc:
            logger.warning("ao_evenements.date_email_reference: %s", exc)
            break
        if row is not None and row["d"]:
            return str(row["d"])
    return str(date_envoi) if date_envoi else None


# ─── Écriture ─────────────────────────────────────────────────────

def token_pixel(conn, ao_fournisseur_id: int) -> str | None:
    """Retourne le token de pixel du fournisseur, en le créant au besoin.

    Token distinct du token portail : le pixel transite par les proxys
    d'images (Gmail, Outlook), qui le mettent en cache et le journalisent.
    Y faire passer le token d'accès au portail reviendrait à le diffuser.
    """
    try:
        row = conn.execute(
            "SELECT token_pixel FROM ao_fournisseurs WHERE id=?",
            (int(ao_fournisseur_id),),
        ).fetchone()
        if row is None:
            return None
        existant = row["token_pixel"] if "token_pixel" in row.keys() else None
        if existant:
            return str(existant)
        nouveau = str(uuid.uuid4())
        conn.execute(
            "UPDATE ao_fournisseurs SET token_pixel=? WHERE id=?",
            (nouveau, int(ao_fournisseur_id)),
        )
        return nouveau
    except Exception as exc:
        logger.warning("ao_evenements.token_pixel: %s", exc)
        return None


def url_pixel(token: str | None, contexte: str = "inv") -> str | None:
    """URL absolue du pixel de suivi, ou None si le suivi est impossible.

    `contexte` (clé de CONTEXTES) part en query string plutôt qu'en second
    token : les proxys d'images transmettent l'URL complète, et cela évite une
    table de tokens par envoi pour un besoin qui tient en trois valeurs.
    """
    if not token:
        return None
    try:
        from config import BASE_URL

        base = str(BASE_URL or "").rstrip("/")
    except Exception:
        base = ""
    if not base:
        return None
    ctx = contexte if contexte in CONTEXTES else "inv"
    return f"{base}/portail/ao/px/{token}.gif?e={ctx}"


def log_evenement(
    conn,
    *,
    ao_fournisseur_id: int,
    ao_id: int | None = None,
    canal: str,
    type_evenement: str,
    date: str | None = None,
    fiable: bool = True,
    motif: str | None = None,
    user_agent: str | None = None,
    meta: dict | None = None,
    dedup_secondes: int = 0,
) -> bool:
    """Enregistre un événement. Ne lève jamais. Retourne True si écrit.

    `dedup_secondes` > 0 ignore un événement identique (même fournisseur, même
    type) déjà enregistré dans la fenêtre — utilisé pour les rechargements
    d'image successifs qui décrivent un seul et même affichage.
    """
    try:
        quand = date or now_paris_iso()
        if dedup_secondes > 0:
            recent = _parse_iso(quand)
            if recent is not None:
                seuil = (recent - timedelta(seconds=dedup_secondes)).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                # La fiabilite fait partie de la cle de dedup : sans elle, un
                # prechargement enregistre a T ferait disparaitre la vraie
                # ouverture arrivee a T+40s - exactement le cas que la
                # classification est censee traiter.
                deja = conn.execute(
                    """SELECT 1 FROM ao_evenements
                       WHERE ao_fournisseur_id=? AND type_evenement=?
                         AND fiable=? AND date>=?
                       LIMIT 1""",
                    (
                        int(ao_fournisseur_id),
                        type_evenement,
                        1 if fiable else 0,
                        seuil,
                    ),
                ).fetchone()
                if deja:
                    return False
        if ao_id is None:
            row = conn.execute(
                "SELECT ao_id FROM ao_fournisseurs WHERE id=?",
                (int(ao_fournisseur_id),),
            ).fetchone()
            ao_id = int(row["ao_id"]) if row else None
        conn.execute(
            """INSERT INTO ao_evenements
               (ao_fournisseur_id, ao_id, canal, type_evenement, date,
                fiable, motif, user_agent, meta)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                int(ao_fournisseur_id),
                int(ao_id) if ao_id is not None else None,
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
        logger.warning("ao_evenements.log_evenement (%s): %s", type_evenement, exc)
        return False


# ─── Lecture ──────────────────────────────────────────────────────

def resume_par_fournisseur(conn, ao_id: int) -> dict[int, dict]:
    """Agrégat d'engagement par fournisseur d'un AO, pour la liste MyAO.

    Ne compte que les événements `fiable=1`. Les hits écartés sont renvoyés
    séparément dans `ouvertures_ecartees` : l'information reste consultable
    dans la timeline, sans polluer le compteur affiché.
    """
    out: dict[int, dict] = {}
    try:
        rows = conn.execute(
            """SELECT ao_fournisseur_id AS fid, type_evenement AS t, fiable,
                      COUNT(*) AS n, MIN(date) AS premier, MAX(date) AS dernier
               FROM ao_evenements
               WHERE ao_id=?
               GROUP BY ao_fournisseur_id, type_evenement, fiable""",
            (int(ao_id),),
        ).fetchall()
    except Exception as exc:
        logger.warning("ao_evenements.resume_par_fournisseur: %s", exc)
        return out

    for r in rows:
        fid = int(r["fid"])
        entry = out.setdefault(
            fid,
            {
                "nb_ouvertures_email": 0,
                "email_ouvert_le": None,
                "email_ouvert_dernier": None,
                "ouvertures_ecartees": 0,
                "motif_ecarte": None,
                "nb_visites_portail": 0,
                "portail_ouvert_le": None,
                "dernier_signal": None,
            },
        )
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
        if fiable and t != EV_EMAIL_ENVOYE:
            dernier = entry.get("dernier_signal")
            if not dernier or str(r["dernier"]) > str(dernier):
                entry["dernier_signal"] = r["dernier"]

    # Motif du dernier hit ecarte : sans lui, « Ouverture non confirmee » ne
    # dit pas SI c'est un prechargement, un robot ou un UA manquant — or c'est
    # exactement ce qu'on veut savoir en regardant la ligne.
    try:
        for r in conn.execute(
            """SELECT ao_fournisseur_id AS fid, motif, MAX(date) AS d
               FROM ao_evenements
               WHERE ao_id=? AND type_evenement=? AND fiable=0
               GROUP BY ao_fournisseur_id""",
            (int(ao_id), EV_EMAIL_OUVERT),
        ).fetchall():
            entry = out.get(int(r["fid"]))
            if entry is not None:
                entry["motif_ecarte"] = r["motif"]
    except Exception as exc:
        logger.warning("ao_evenements.resume_par_fournisseur (motifs): %s", exc)
    return out


def timeline(conn, ao_fournisseur_id: int, limite: int = 200) -> list[dict]:
    """Événements d'un fournisseur, du plus récent au plus ancien."""
    try:
        rows = conn.execute(
            """SELECT id, canal, type_evenement, date, fiable, motif, user_agent, meta
               FROM ao_evenements
               WHERE ao_fournisseur_id=?
               ORDER BY date DESC, id DESC
               LIMIT ?""",
            (int(ao_fournisseur_id), int(limite)),
        ).fetchall()
    except Exception as exc:
        logger.warning("ao_evenements.timeline: %s", exc)
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
