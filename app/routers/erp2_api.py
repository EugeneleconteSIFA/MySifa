"""API du nouvel ERP (erp.mysifa.com) — `/api/erp2`.

Réservée à `ROLES_ERP2`. Le router ne porte que l'accès, la transaction et la
traduction des refus en 400 : la logique vit dans `app/services/gc/`. Chaque
écriture est une transaction : un refus en cours de route n'écrit rien.
"""
from __future__ import annotations

from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, Request

from config import ROLES_ERP2
from app.core.database import get_db
from app.services.auth_service import get_current_user
from app.services.audit_service import log_action
from app.services.gc import demo, fichiers, pieces
from app.services.gc.pieces import ErreurPiece

router = APIRouter(prefix="/api/erp2", tags=["erp2"])


def _user(request: Request) -> dict:
    u = get_current_user(request)
    if u.get("role") not in ROLES_ERP2:
        raise HTTPException(403, "Accès réservé.")
    return u


@contextmanager
def _ecriture():
    """Connexion transactionnelle : commit en sortie, rollback sur refus."""
    with get_db() as conn:
        try:
            yield conn
            conn.commit()
        except ErreurPiece as e:
            conn.rollback()
            raise HTTPException(400, str(e)) from None
        except Exception:
            conn.rollback()
            raise


def _lecture(fn, *a):
    with get_db() as conn:
        try:
            return fn(conn, *a)
        except ErreurPiece as e:
            raise HTTPException(404 if "introuvable" in str(e) else 400, str(e)) from None


def _trace(request, user, action, objet, detail=None):
    log_action(user=user, action=action, module="erp2", objet=objet, detail=detail, request=request)


# ── Méta : tout ce qu'un écran doit savoir pour s'afficher ────────────

@router.get("/meta")
def meta(request: Request):
    _user(request)
    with get_db() as conn:
        return {
            "referentiels": {k: fichiers.lister_referentiel(conn, k) for k in fichiers.REFERENTIELS},
            "referentiels_libelles": {k: v["libelle"] for k, v in fichiers.REFERENTIELS.items()},
            "societe": fichiers.lire_societe(conn),
            "types": pieces.TYPES,
            "natures": fichiers.NATURES,
        }


@router.put("/referentiels/{nom}")
async def maj_referentiel(nom: str, request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        for ligne in body.get("lignes") or []:
            fichiers.enregistrer_referentiel(conn, nom, ligne)
    _trace(request, u, "UPDATE", f"Référentiel {nom}")
    return {"ok": True}


@router.put("/societe")
async def maj_societe(request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        fichiers.enregistrer_societe(conn, body)
    _trace(request, u, "UPDATE", "Société")
    return {"ok": True}


# ── Tiers ─────────────────────────────────────────────────────────────

@router.get("/tiers")
def tiers_liste(request: Request, role: str = ""):
    _user(request)
    return _lecture(fichiers.lister_tiers, role or None)


@router.get("/tiers/{tiers_id}")
def tiers_fiche(tiers_id: int, request: Request):
    _user(request)
    return _lecture(fichiers.charger_tiers, tiers_id)


@router.post("/tiers")
@router.put("/tiers/{tiers_id}")
async def tiers_enregistrer(request: Request, tiers_id: int | None = None):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        tid = fichiers.enregistrer_tiers(conn, tiers_id, body.get("tiers") or {},
                                         body.get("adresses"), body.get("contacts"))
    _trace(request, u, "CREATE" if tiers_id is None else "UPDATE", f"Tiers #{tid}")
    return {"id": tid}


# ── Articles ──────────────────────────────────────────────────────────

@router.get("/articles")
def articles_liste(request: Request, nature: str = ""):
    _user(request)
    return _lecture(fichiers.lister_articles, nature or None)


@router.get("/articles/{article_id}")
def article_fiche(article_id: int, request: Request):
    _user(request)
    return _lecture(fichiers.charger_article, article_id)


@router.post("/articles")
@router.put("/articles/{article_id}")
async def article_enregistrer(request: Request, article_id: int | None = None):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        aid = fichiers.enregistrer_article(conn, article_id, body.get("article") or {}, body.get("tarifs"))
    _trace(request, u, "CREATE" if article_id is None else "UPDATE", f"Article #{aid}")
    return {"id": aid}


@router.get("/prix")
def prix(request: Request, article_id: int, tiers_id: int | None = None, quantite_milli: int = 0, sens: str = "vente"):
    _user(request)
    with get_db() as conn:
        try:
            p = pieces.prix(conn, article_id, tiers_id, quantite_milli, sens)
            a = conn.execute("SELECT * FROM gc_articles WHERE id=?", (article_id,)).fetchone()
            t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone() if tiers_id else None
            code = pieces.code_tva_ligne(conn, t, a)
            p["tva_code"] = code
            p["taux_tva_bp"] = pieces.taux_tva(conn, code)
            return p
        except ErreurPiece as e:
            raise HTTPException(400, str(e)) from None


# ── Pièces ────────────────────────────────────────────────────────────

@router.get("/pieces")
def pieces_liste(request: Request, types: str):
    _user(request)
    liste = [t for t in types.split(",") if t in pieces.TYPES]
    if not liste:
        raise HTTPException(400, "Type de pièce inconnu.")
    return _lecture(pieces.lister, liste)


@router.get("/pieces/{piece_id}")
def piece(piece_id: int, request: Request):
    _user(request)
    return _lecture(pieces.charger, piece_id)


@router.post("/pieces")
async def piece_creer(request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        pid = pieces.creer(conn, body.get("type"), int(body.get("tiers_id") or 0), u)
        if body.get("entete") or body.get("lignes"):
            pieces.enregistrer(conn, pid, body.get("entete"), body.get("lignes"))
    _trace(request, u, "CREATE", f"Pièce #{pid}")
    return {"id": pid}


@router.put("/pieces/{piece_id}")
async def piece_enregistrer(piece_id: int, request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        pieces.enregistrer(conn, piece_id, body.get("entete"), body.get("lignes"))
    _trace(request, u, "UPDATE", f"Pièce #{piece_id}")
    return {"ok": True}


@router.post("/pieces/{piece_id}/valider")
def piece_valider(piece_id: int, request: Request):
    u = _user(request)
    with _ecriture() as conn:
        numero = pieces.valider(conn, piece_id, u)
    _trace(request, u, "VALIDATE", f"Pièce {numero}")
    return {"numero": numero}


@router.post("/pieces/transformer")
async def piece_transformer(request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        pid = pieces.transformer(conn, [int(i) for i in body.get("sources") or []], body.get("cible"), u)
    _trace(request, u, "CREATE", f"Pièce #{pid} ({body.get('cible')})", {"sources": body.get("sources")})
    return {"id": pid}


@router.post("/pieces/{piece_id}/annuler")
def piece_annuler(piece_id: int, request: Request):
    u = _user(request)
    with _ecriture() as conn:
        pieces.annuler(conn, piece_id, u)
    _trace(request, u, "CANCEL", f"Pièce #{piece_id}")
    return {"ok": True}


@router.delete("/pieces/{piece_id}")
def piece_supprimer(piece_id: int, request: Request):
    u = _user(request)
    with _ecriture() as conn:
        pieces.supprimer(conn, piece_id)
    _trace(request, u, "DELETE", f"Brouillon #{piece_id}")
    return {"ok": True}


@router.post("/lignes/{ligne_id}/solde")
async def ligne_solde(ligne_id: int, request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        pid = pieces.solder_ligne(conn, ligne_id, bool(body.get("solde")))
    _trace(request, u, "UPDATE", f"Ligne #{ligne_id} soldée" if body.get("solde") else f"Ligne #{ligne_id} rouverte")
    return {"piece_id": pid}


# ── Stock ─────────────────────────────────────────────────────────────

@router.get("/stock")
def stock(request: Request):
    _user(request)
    return _lecture(fichiers.stock)


@router.get("/mouvements")
def mouvements(request: Request, article_id: int | None = None):
    _user(request)
    return _lecture(fichiers.mouvements, article_id)


@router.post("/mouvements")
async def mouvement_creer(request: Request):
    u = _user(request)
    body = await request.json()
    with _ecriture() as conn:
        mid = fichiers.mouvement_manuel(conn, body, u)
    _trace(request, u, "CREATE", f"Mouvement de stock #{mid}")
    return {"id": mid}


# ── Comptabilité ──────────────────────────────────────────────────────

@router.get("/echeances")
def echeances(request: Request):
    _user(request)
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT e.id, e.date_echeance, e.montant_cents, e.regle_cents,
                      e.montant_cents - e.regle_cents AS reste_cents,
                      p.id AS piece_id, p.type, p.numero, p.date_piece, p.mode_paiement,
                      t.id AS tiers_id, t.raison_sociale AS tiers_nom
               FROM gc_echeances e JOIN gc_pieces p ON p.id=e.piece_id JOIN gc_tiers t ON t.id=p.tiers_id
               ORDER BY e.date_echeance""").fetchall()]


# ── Recherche globale ─────────────────────────────────────────────────

@router.get("/recherche")
def recherche(request: Request, q: str = ""):
    _user(request)
    q = q.strip()
    if len(q) < 2:
        return []
    m = f"%{q}%"
    with get_db() as conn:
        res = [{"genre": "tiers", "id": r["id"], "titre": r["raison_sociale"], "sous": r["code"],
                "client": r["est_client"]}
               for r in conn.execute(
                   "SELECT id, code, raison_sociale, est_client FROM gc_tiers WHERE code LIKE ? OR raison_sociale LIKE ? LIMIT 8",
                   (m, m)).fetchall()]
        res += [{"genre": "article", "id": r["id"], "titre": r["libelle"], "sous": r["code"]}
                for r in conn.execute(
                    "SELECT id, code, libelle FROM gc_articles WHERE code LIKE ? OR libelle LIKE ? LIMIT 8",
                    (m, m)).fetchall()]
        res += [{"genre": "piece", "id": r["id"], "titre": r["numero"], "sous": r["raison_sociale"], "type": r["type"]}
                for r in conn.execute(
                    """SELECT p.id, p.numero, p.type, t.raison_sociale FROM gc_pieces p JOIN gc_tiers t ON t.id=p.tiers_id
                       WHERE p.numero LIKE ? OR p.ref_tiers LIKE ? LIMIT 8""", (m, m)).fetchall()]
    return res


# ── Démonstration ─────────────────────────────────────────────────────

@router.post("/demo/reinitialiser")
def demo_reinitialiser(request: Request):
    u = _user(request)
    with _ecriture() as conn:
        res = demo.reinitialiser(conn, u)
    _trace(request, u, "RESET", "Démonstration ERP", res)
    return res
