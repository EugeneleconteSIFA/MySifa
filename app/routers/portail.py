"""Portail — volets de navigation et reprise de navigation.

Trois entrées, toutes portées par l'utilisateur connecté :

  GET    /api/portail/volets    le catalogue des sous-menus, déjà filtré par le
                                rôle. Le front n'en connaît rien d'autre.
  GET    /api/portail/recents   les derniers écrans ouverts (« Reprendre où j'en
                                étais »), du plus récent au plus ancien.
  POST   /api/portail/recents   enregistre une ouverture d'écran.
  DELETE /api/portail/recents   vide l'historique de reprise.

L'historique vit en base et non dans le navigateur : dans l'atelier on change de
poste, et un `localStorage` ne suit pas l'opérateur. Douze lignes au maximum par
utilisateur, la plus ancienne saute — c'est un raccourci, pas un journal ; le
journal d'audit existe ailleurs et n'a pas les mêmes règles de rétention.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.services.auth_service import get_current_user
from app.services import portail_volets

router = APIRouter(tags=["portail"])

# Au-delà, ce n'est plus « reprendre où j'en étais » mais un historique que
# personne ne lit. Le front en affiche moins encore (la barre est étroite).
MAX_RECENTS = 12


def _role_effectif(user: dict) -> str:
    """Le rôle simulé quand le superadmin est en impersonation, sinon le sien.

    Même choix que `/api/auth/me` : ce que voit le front doit correspondre à ce
    que verrait vraiment l'utilisateur simulé, volets compris.
    """
    return str(user.get("effective_role") or user.get("role") or "")


@router.get("/api/portail/volets")
def volets(request: Request):
    user = get_current_user(request)
    return {"volets": portail_volets.volets_pour(_role_effectif(user))}


@router.get("/api/portail/recents")
def recents(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT cle,libelle,module,url,vu_le FROM portail_recents "
            "WHERE user_id=? ORDER BY vu_le DESC LIMIT ?",
            (user["id"], MAX_RECENTS),
        ).fetchall()
    return {"recents": [dict(r) for r in rows]}


@router.post("/api/portail/recents")
async def enregistrer_recent(request: Request):
    """Le front signale l'ouverture d'un écran.

    Il envoie ce que le catalogue lui a donné : une clé, un libellé, une URL
    interne. L'URL est vérifiée ici — une entrée qui commencerait par `http` ou
    `//` transformerait la barre de reprise en tremplin vers l'extérieur.
    """
    user = get_current_user(request)
    body = await request.json()

    cle = str(body.get("cle") or "").strip()[:64]
    libelle = str(body.get("libelle") or "").strip()[:80]
    module = str(body.get("module") or "").strip()[:40] or None
    url = str(body.get("url") or "").strip()[:300]

    if not cle or not libelle or not url:
        raise HTTPException(status_code=400, detail="cle, libelle et url sont requis")
    if not url.startswith("/") or url.startswith("//"):
        raise HTTPException(status_code=400, detail="URL interne attendue")

    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_db() as conn:
        # Une deuxième visite déplace la date : l'écran remonte en tête sans
        # créer de doublon (index unique sur user_id + cle).
        conn.execute(
            "INSERT INTO portail_recents (user_id,cle,libelle,module,url,vu_le) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(user_id,cle) DO UPDATE SET "
            "libelle=excluded.libelle, module=excluded.module, "
            "url=excluded.url, vu_le=excluded.vu_le",
            (user["id"], cle, libelle, module, url, maintenant),
        )
        conn.execute(
            "DELETE FROM portail_recents WHERE user_id=? AND id NOT IN ("
            "  SELECT id FROM portail_recents WHERE user_id=? "
            "  ORDER BY vu_le DESC LIMIT ?)",
            (user["id"], user["id"], MAX_RECENTS),
        )
        conn.commit()
    return {"success": True}


@router.delete("/api/portail/recents")
def vider_recents(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        conn.execute("DELETE FROM portail_recents WHERE user_id=?", (user["id"],))
        conn.commit()
    return {"success": True}
