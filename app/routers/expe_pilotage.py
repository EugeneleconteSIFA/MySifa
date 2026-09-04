"""
MyExpé — API du tableau de bord expédition (pilotage amont).

Monté sous `/api/expe/pilotage`. La construction de la vue vit dans
`app/services/expe_pilotage.py` ; ce fichier ne fait que l'exposer et écrire
les jalons.

Un point de conception qui explique tout le reste : les actions ne prennent
JAMAIS le contenu de l'envoi depuis le corps de la requête. Elles reçoivent une
clé d'envoi, le serveur reconstruit le tableau et retrouve l'envoi par cette
clé. Un client ne peut donc pas créer un départ portant un client, une
destination ou un nombre de palettes qui ne correspondent à aucun dossier réel
— et les chiffres écrits en base sont exactement ceux qui étaient affichés.

Ce que l'utilisateur peut y faire :
  - déclarer le transport commandé (crée le départ s'il n'existe pas encore,
    en statut `en_attente` : il rejoint alors « Départs programmés ») ;
  - déclarer l'envoi parti ;
  - corriger le nombre de palettes estimé ;
  - régler l'horizon et les préavis de réservation.
"""

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, HTTPException, Request

from app.services import expe_pilotage as pil
from app.services.audit_service import log_action
from config import ROLES_EXPE_PILOTAGE
from database import get_db
from services.auth_service import (
    effective_role,
    get_current_user,
    user_can_write_expe,
    user_has_app_access,
)

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")


def _require_expe(request: Request) -> dict:
    """Accès au pilotage : MyExpé, plus un rôle habilité.

    L'écran est restreint pendant son rodage (`ROLES_EXPE_PILOTAGE` dans
    `config.py`, direction et super administrateur). Le filtre est ici, côté
    serveur : masquer l'entrée de menu ne protège rien, l'URL de l'API reste
    appelable.
    """
    user = get_current_user(request)
    if not user_has_app_access(user, "expe"):
        raise HTTPException(status_code=403, detail="Accès MyExpé requis")
    if effective_role(user) not in ROLES_EXPE_PILOTAGE:
        raise HTTPException(
            status_code=403,
            detail="Pilotage des expéditions — accès réservé pendant le rodage.",
        )
    return user


def _require_expe_write(request: Request) -> dict:
    user = _require_expe(request)
    if not user_can_write_expe(user):
        raise HTTPException(status_code=403, detail="Accès MyExpé en lecture seule")
    return user


def _maintenant() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).isoformat(timespec="seconds")


def _email(user: dict) -> Optional[str]:
    return (user.get("email") or user.get("identifiant") or "").strip() or None


def _envoi_ou_404(conn, cle: str) -> dict:
    for e in pil.construire_tableau(conn)["envois"]:
        if e["cle_envoi"] == cle:
            return e
    raise HTTPException(
        status_code=404,
        detail="Envoi introuvable — le tableau a changé depuis son affichage. "
               "Rafraîchir la page.",
    )


def _depart_de_lenvoi(conn, envoi: dict, user: dict, date_enlevement: str) -> int:
    """Le départ de cet envoi, créé s'il n'existe pas encore.

    C'est ici que le prévisionnel devient une ligne d'expédition : le départ
    naît avec le client, la destination, les palettes et les dossiers déjà
    connus du tableau, en statut `prevu`. Ce statut est invisible des écrans
    existants : le départ ne rejoint « Départs programmés » qu'au moment où le
    transport est commandé, et sans ressaisie.
    """
    dep = envoi.get("depart")
    if dep and dep.get("id"):
        return int(dep["id"])

    now = _maintenant()
    email = _email(user)
    cur = conn.execute(
        """INSERT INTO expe_departs
             (date_enlevement, client, code_postal_destination, arc,
              nb_palette_estime, nb_palette_estime_maj_le,
              statut, created_at, created_by_email,
              date_enlevement_source, origine, cle_envoi,
              palette_europe, palette_europe_statut,
              fsc_sans_transit, sans_dossier)
           VALUES (?,?,?,?,?,?,'prevu',?,?,'prevue','pilotage',?,0,'en_attente',0,0)""",
        (
            date_enlevement,
            envoi.get("client") or None,
            envoi.get("code_postal") or None,
            "+".join(envoi.get("commandes_rvgi") or []) or None,
            # `nb_palette` reste vide : c'est la quantité SAISIE, et personne
            # ne l'a encore saisie. L'estimation vit dans sa propre colonne,
            # sinon un chiffre calculé se ferait passer pour un chiffre validé.
            envoi.get("nb_palette_estime"),
            now,
            now,
            email,
            envoi["cle_envoi"],
        ),
    )
    depart_id = int(cur.lastrowid)

    # Rattachement des dossiers : c'est ce lien qui évite qu'un rafraîchissement
    # du tableau recrée un second départ pour le même camion.
    for d in envoi.get("dossiers", []):
        conn.execute(
            "INSERT OR IGNORE INTO expe_depart_dossiers "
            "(depart_id, planning_entry_id, no_dossier, created_at, created_by) "
            "VALUES (?,?,?,?,?)",
            (depart_id, d["id"], d.get("reference"), now, email),
        )
    premier = (envoi.get("dossiers") or [{}])[0]
    if premier.get("id"):
        conn.execute(
            "UPDATE expe_departs SET planning_entry_id=?, no_dossier=?, "
            "no_dossier_source='saisi' WHERE id=?",
            (premier["id"], premier.get("reference"), depart_id),
        )
    return depart_id


# ─── Lecture ─────────────────────────────────────────────────────────────────

@router.get("/pilotage")
def tableau_pilotage(request: Request):
    """Le tableau de bord complet : envois à venir, jalons, alertes."""
    _require_expe(request)
    with get_db() as conn:
        return pil.construire_tableau(conn)


@router.get("/pilotage/params")
def lire_params(request: Request):
    _require_expe(request)
    with get_db() as conn:
        return {"params": pil.charger_params(conn), "defauts": pil.DEFAUTS,
                "bornes": pil.BORNES}


@router.put("/pilotage/params")
def ecrire_params(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    with get_db() as conn:
        try:
            params = pil.enregistrer_params(conn, body or {})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="expe",
               objet="Pilotage expéditions · réglages",
               ip=request.client.host if request.client else None)
    return {"params": params}


# ─── Jalons ──────────────────────────────────────────────────────────────────

@router.post("/pilotage/envois/{cle}/transport")
def marquer_transport_commande(request: Request, cle: str, body: dict = Body(default={})):
    """Transport commandé : crée le départ au besoin et pose le jalon.

    Body : { transporteur?, no_cde_transport?, date_enlevement?, nb_palette? }
    `date_enlevement` par défaut : la date d'expédition visée par le tableau.
    """
    user = _require_expe_write(request)
    body = body or {}
    with get_db() as conn:
        envoi = _envoi_ou_404(conn, cle)
        date_enl = str(body.get("date_enlevement") or "").strip()[:10] \
            or envoi.get("date_cible") \
            or datetime.now(_PARIS).date().isoformat()
        depart_id = _depart_de_lenvoi(conn, envoi, user, date_enl)

        maj = ["transport_commande_le=COALESCE(transport_commande_le, ?)",
               "transport_commande_par=COALESCE(transport_commande_par, ?)",
               "date_enlevement=?", "statut='en_attente'"]
        args: list[Any] = [_maintenant(), _email(user), date_enl]
        if str(body.get("transporteur") or "").strip():
            maj.append("transporteur=?")
            args.append(str(body["transporteur"]).strip())
        if str(body.get("no_cde_transport") or "").strip():
            maj.append("no_cde_transport=?")
            args.append(str(body["no_cde_transport"]).strip())
        if body.get("nb_palette") not in (None, ""):
            maj.append("nb_palette=?")
            args.append(_nombre(body["nb_palette"], "Nombre de palettes"))
        # Une date d'enlèvement fournie explicitement est une date négociée.
        maj.append("date_enlevement_source=?")
        args.append("confirmee" if body.get("date_enlevement") else "prevue")
        args.append(depart_id)
        conn.execute("UPDATE expe_departs SET " + ", ".join(maj) + " WHERE id=?", args)
        conn.commit()

    log_action(user=user, action="UPDATE", module="expe",
               objet=f"Transport commandé · {envoi.get('client') or ''} · {date_enl}",
               ip=request.client.host if request.client else None)
    with get_db() as conn:
        return pil.construire_tableau(conn)


@router.get("/pilotage/envois/{cle}/departs-candidats")
def departs_candidats(request: Request, cle: str):
    """Départs déjà saisis auxquels cet envoi pourrait se rattacher.

    Le cas réel : le transport a été programmé dans « Départs programmés »
    avant que le tableau de pilotage n'existe, ou par quelqu'un qui est passé
    par l'écran habituel. Créer un second départ dupliquerait le camion. On
    propose donc de rattacher plutôt que de créer.

    Le tri place en tête ce qui a des chances d'être le bon : même client,
    puis même destination, puis date d'enlèvement la plus proche de la date
    visée. Chaque ligne dit POURQUOI elle remonte — l'expéditionnaire choisit,
    l'écran ne décide pas à sa place.
    """
    _require_expe(request)
    with get_db() as conn:
        envoi = _envoi_ou_404(conn, cle)
        rows = conn.execute(
            """SELECT d.id, d.date_enlevement, d.transporteur, d.client,
                      d.code_postal_destination, d.nb_palette, d.no_bl,
                      d.no_cde_transport, d.arc, d.ref_sifa, d.statut,
                      d.cle_envoi,
                      (SELECT COUNT(*) FROM expe_depart_dossiers dd
                        WHERE dd.depart_id = d.id) AS nb_dossiers
                 FROM expe_departs d
                WHERE d.statut IN ('prevu', 'en_attente')
                  AND (d.cle_envoi IS NULL OR d.cle_envoi = ?)
                ORDER BY d.date_enlevement DESC, d.id DESC
                LIMIT 400""",
            (cle,),
        ).fetchall()

    client = pil._norm(envoi.get("client"))
    dept = pil._dept(envoi.get("code_postal"))
    cible = envoi.get("date_cible") or ""

    sortie = []
    for r in rows:
        d = dict(r)
        raisons = []
        if client and pil._norm(d.get("client")) == client:
            raisons.append("même client")
        if dept and pil._dept(d.get("code_postal_destination")) == dept:
            raisons.append("même destination")
        if cible and (d.get("date_enlevement") or "")[:10] == cible:
            raisons.append("même date")
        d["raisons"] = raisons
        d["pertinent"] = bool(raisons)
        d["ecart_jours"] = _ecart_jours(cible, d.get("date_enlevement"))
        sortie.append(d)

    sortie.sort(key=lambda d: (-len(d["raisons"]),
                               abs(d["ecart_jours"]) if d["ecart_jours"] is not None else 9999,
                               -int(d["id"])))
    return {"envoi": {"client": envoi.get("client"),
                      "code_postal": envoi.get("code_postal"),
                      "ville": envoi.get("ville"),
                      "date_cible": envoi.get("date_cible")},
            "departs": sortie[:60]}


def _ecart_jours(cible: Optional[str], autre: Optional[str]) -> Optional[int]:
    from datetime import date as _date
    def _d(v):
        v = str(v or "")[:10]
        try:
            return _date(int(v[0:4]), int(v[5:7]), int(v[8:10]))
        except (ValueError, TypeError):
            return None
    a, b = _d(cible), _d(autre)
    return (b - a).days if (a and b) else None


@router.post("/pilotage/envois/{cle}/associer")
def associer_depart(request: Request, cle: str, body: dict = Body(...)):
    """Rattache l'envoi à un départ déjà saisi, au lieu d'en créer un second.

    Concrètement : les dossiers de l'envoi rejoignent ce départ, et la clé
    d'envoi s'y inscrit pour que le tableau le retrouve aux rafraîchissements
    suivants. Rien n'est écrasé sur le départ existant — ni son transporteur,
    ni sa date, ni ses palettes : il a été saisi par quelqu'un qui savait ce
    qu'il faisait.
    """
    user = _require_expe_write(request)
    try:
        depart_id = int((body or {}).get("depart_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Départ à associer obligatoire.")

    with get_db() as conn:
        envoi = _envoi_ou_404(conn, cle)
        if (envoi.get("depart") or {}).get("id"):
            raise HTTPException(
                status_code=409,
                detail="Cet envoi porte déjà un départ. Le détacher avant d'en associer un autre.",
            )
        ex = conn.execute(
            "SELECT id, statut, cle_envoi, client FROM expe_departs WHERE id=?",
            (depart_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Départ introuvable.")
        if ex["statut"] not in ("prevu", "en_attente"):
            raise HTTPException(
                status_code=409,
                detail="Ce départ est déjà validé — il ne peut plus recevoir de dossier.",
            )
        if ex["cle_envoi"] and ex["cle_envoi"] != cle:
            raise HTTPException(
                status_code=409,
                detail="Ce départ est déjà rattaché à un autre envoi.",
            )

        now = _maintenant()
        email = _email(user)
        for d in envoi.get("dossiers", []):
            conn.execute(
                "INSERT OR IGNORE INTO expe_depart_dossiers "
                "(depart_id, planning_entry_id, no_dossier, created_at, created_by) "
                "VALUES (?,?,?,?,?)",
                (depart_id, d["id"], d.get("reference"), now, email),
            )
        conn.execute(
            "UPDATE expe_departs SET cle_envoi=COALESCE(cle_envoi, ?) WHERE id=?",
            (cle, depart_id),
        )
        # Un départ déjà porteur d'un numéro de commande transport a bien été
        # commandé : on date le jalon plutôt que de le laisser vide.
        conn.execute(
            "UPDATE expe_departs SET transport_commande_le=COALESCE(transport_commande_le, ?),"
            " transport_commande_par=COALESCE(transport_commande_par, ?)"
            " WHERE id=? AND TRIM(COALESCE(no_cde_transport,'')) != ''",
            (now, email, depart_id),
        )
        conn.commit()

    log_action(user=user, action="UPDATE", module="expe",
               objet=f"Envoi rattaché au départ #{depart_id} · {envoi.get('client') or ''}",
               ip=request.client.host if request.client else None)
    with get_db() as conn:
        return pil.construire_tableau(conn)


@router.post("/pilotage/envois/{cle}/parti")
def marquer_parti(request: Request, cle: str, body: dict = Body(default={})):
    """Envoi parti. Le départ existe forcément — sinon rien n'a été commandé."""
    user = _require_expe_write(request)
    body = body or {}
    with get_db() as conn:
        envoi = _envoi_ou_404(conn, cle)
        dep = envoi.get("depart") or {}
        if not dep.get("id"):
            raise HTTPException(
                status_code=400,
                detail="Aucun transport commandé pour cet envoi — "
                       "commander le transport avant de le déclarer parti.",
            )
        quand = str(body.get("le") or "").strip()[:10] or \
            datetime.now(_PARIS).date().isoformat()
        conn.execute(
            "UPDATE expe_departs SET parti_le=?, parti_par=? WHERE id=?",
            (quand, _email(user), int(dep["id"])),
        )
        conn.commit()
    log_action(user=user, action="UPDATE", module="expe",
               objet=f"Départ parti · {envoi.get('client') or ''} · {quand}",
               ip=request.client.host if request.client else None)
    with get_db() as conn:
        return pil.construire_tableau(conn)


@router.post("/pilotage/envois/{cle}/palettes")
def corriger_palettes(request: Request, cle: str, body: dict = Body(...)):
    """Corrige le nombre de palettes d'un envoi.

    L'estimation calculée reste en base à côté (`nb_palette_estime`) : c'est ce
    qui permettra plus tard de mesurer si les fiches techniques disent vrai.
    """
    user = _require_expe_write(request)
    valeur = _nombre((body or {}).get("nb_palette"), "Nombre de palettes")
    if valeur is None:
        raise HTTPException(status_code=400, detail="Nombre de palettes obligatoire.")
    with get_db() as conn:
        envoi = _envoi_ou_404(conn, cle)
        date_enl = envoi.get("date_cible") or datetime.now(_PARIS).date().isoformat()
        depart_id = _depart_de_lenvoi(conn, envoi, user, date_enl)
        conn.execute(
            "UPDATE expe_departs SET nb_palette=?, nb_palette_estime=?, "
            "nb_palette_estime_maj_le=? WHERE id=?",
            (valeur, envoi.get("nb_palette_estime"), _maintenant(), depart_id),
        )
        conn.commit()
    log_action(user=user, action="UPDATE", module="expe",
               objet=f"Palettes corrigées · {envoi.get('client') or ''} · {valeur:g}",
               ip=request.client.host if request.client else None)
    with get_db() as conn:
        return pil.construire_tableau(conn)


def _nombre(v: Any, champ: str) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        val = float(str(v).replace(",", ".").replace(" ", "").replace(" ", ""))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{champ} invalide.")
    if val < 0 or val > 999:
        raise HTTPException(status_code=400, detail=f"{champ} — valeur entre 0 et 999.")
    return val
