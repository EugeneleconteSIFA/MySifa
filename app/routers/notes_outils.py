"""MySifa — Mes notes : historique, modèles, favoris et récentes, commentaires,
liens vers MySifa (« @ »), export PDF / Word.

Complète app/routers/postit.py (notes, partage, rédaction à plusieurs). Inclus
AVANT lui dans main.py : `/api/postits/modeles` serait sinon lu comme
`/api/postits/{postit_id}`. Les droits sur une note passent toujours par
`exiger_droit` (app/services/notes.py).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from database import get_db
from services.auth_service import (
    can_access_settings,
    can_access_settings_contacts,
    get_current_user,
    user_has_app_access,
)
from app.services.notes import (
    droit_sur,
    exiger_droit,
    extrait_de,
    lire_blocs,
    maintenant,
    marquer_reset,
    photographier,
    titre_propre,
)
from app.services import notes_export

router = APIRouter(tags=["postits"])

COMMENTAIRE_MAX = 4000
RECENTES_GARDEES = 30


def _user(request: Request) -> dict:
    return get_current_user(request)


def _signaler_commentaires(conn, note_id: int, user_id: int) -> None:
    """Les éditeurs ouverts sur la note rechargent ses commentaires (flux)."""
    rev = int(conn.execute("SELECT revision FROM postits WHERE id=?", (note_id,)).fetchone()[0] or 0) + 1
    conn.execute("UPDATE postits SET revision=? WHERE id=?", (rev, note_id))
    conn.execute(
        "INSERT INTO note_ops (note_id, revision, user_id, client, op, cree_le) VALUES (?,?,?,?,?,?)",
        (note_id, rev, user_id, "commentaires", json.dumps({"t": "com"}), maintenant()),
    )


# ── Historique des versions ──────────────────────────────────────────────

@router.get("/api/postits/{postit_id}/versions")
def lister_versions(postit_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        exiger_droit(conn, int(user["id"]), postit_id, "lire")
        noms = {r[0]: r[1] for r in conn.execute("SELECT id, nom FROM users").fetchall()}
        out = []
        for r in conn.execute(
            "SELECT id, titre, contenu, auteurs, raison, cree_le FROM note_versions WHERE note_id=? ORDER BY id DESC",
            (postit_id,),
        ).fetchall():
            blocs = lire_blocs(r["contenu"])
            auteurs = [noms.get(int(a), "") for a in (r["auteurs"] or "").split(",") if a.strip().isdigit()]
            out.append({"id": r["id"], "titre": r["titre"], "cree_le": r["cree_le"], "raison": r["raison"],
                        "auteurs": [a for a in auteurs if a], "nb_blocs": len(blocs), "extrait": extrait_de(blocs)})
    return {"versions": out}


@router.get("/api/postits/{postit_id}/versions/{version_id}")
def lire_version(postit_id: int, version_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        exiger_droit(conn, int(user["id"]), postit_id, "lire")
        r = conn.execute("SELECT * FROM note_versions WHERE id=? AND note_id=?", (version_id, postit_id)).fetchone()
        if not r:
            raise HTTPException(404, "Version introuvable")
    return {"id": r["id"], "titre": r["titre"], "cree_le": r["cree_le"], "blocs": lire_blocs(r["contenu"])}


@router.post("/api/postits/{postit_id}/versions/{version_id}/restaurer")
def restaurer_version(postit_id: int, version_id: int, request: Request):
    """Remet la note dans l'état de cette version ; l'état actuel est gardé en version."""
    user = _user(request)
    uid = int(user["id"])
    with get_db() as conn:
        exiger_droit(conn, uid, postit_id, "ecrire")
        r = conn.execute("SELECT titre, contenu FROM note_versions WHERE id=? AND note_id=?",
                         (version_id, postit_id)).fetchone()
        if not r:
            raise HTTPException(404, "Version introuvable")
        photographier(conn, postit_id, "avant restauration", forcer=True)
        conn.execute("UPDATE postits SET contenu=?, title=?, modifie_le=? WHERE id=?",
                     (r["contenu"], r["titre"] or "Sans titre", maintenant(), postit_id))
        marquer_reset(conn, postit_id, uid)
        conn.commit()
    return {"ok": True}


# ── Modèles ──────────────────────────────────────────────────────────────

@router.get("/api/postits/modeles")
def lister_modeles(request: Request):
    user = _user(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, user_id, nom, description, contenu FROM note_modeles
                WHERE user_id IS NULL OR user_id=? ORDER BY user_id IS NOT NULL, nom COLLATE NOCASE""",
            (int(user["id"]),),
        ).fetchall()
    return [{"id": r["id"], "nom": r["nom"], "description": r["description"] or "",
             "commun": r["user_id"] is None, "blocs": lire_blocs(r["contenu"])} for r in rows]


@router.post("/api/postits/modeles")
async def creer_modele(request: Request):
    """Enregistre une note comme modèle personnel : {note_id, nom, description}."""
    user = _user(request)
    body = await request.json()
    nom = titre_propre(body.get("nom"))
    with get_db() as conn:
        _, note = exiger_droit(conn, int(user["id"]), int(body.get("note_id") or 0), "lire")
        blocs = lire_blocs(note.get("contenu"))
        if not blocs:
            raise HTTPException(400, "La note est vide : rien à enregistrer comme modèle.")
        cur = conn.execute(
            "INSERT INTO note_modeles (user_id, nom, description, contenu, cree_le) VALUES (?,?,?,?,?)",
            (int(user["id"]), nom, str(body.get("description") or "")[:200],
             json.dumps(blocs, ensure_ascii=False), maintenant()),
        )
        conn.commit()
    return {"id": cur.lastrowid, "nom": nom}


@router.delete("/api/postits/modeles/{modele_id}")
def supprimer_modele(modele_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        r = conn.execute("SELECT user_id FROM note_modeles WHERE id=?", (modele_id,)).fetchone()
        if not r or r[0] != int(user["id"]):
            raise HTTPException(404, "Modèle introuvable (les modèles communs ne se suppriment pas ici).")
        conn.execute("DELETE FROM note_modeles WHERE id=?", (modele_id,))
        conn.commit()
    return {"ok": True}


# ── Favoris et récentes ──────────────────────────────────────────────────

@router.put("/api/postits/{postit_id}/favori")
async def basculer_favori(postit_id: int, request: Request):
    user = _user(request)
    uid = int(user["id"])
    body = await request.json()
    with get_db() as conn:
        exiger_droit(conn, uid, postit_id, "lire")
        if body.get("favori"):
            ordre = conn.execute("SELECT COALESCE(MAX(ordre), -1) + 1 FROM note_favoris WHERE user_id=?", (uid,)).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO note_favoris (user_id, note_id, ordre, cree_le) VALUES (?,?,?,?)",
                         (uid, postit_id, ordre, maintenant()))
        else:
            conn.execute("DELETE FROM note_favoris WHERE user_id=? AND note_id=?", (uid, postit_id))
        conn.commit()
    return {"ok": True, "favori": bool(body.get("favori"))}


@router.post("/api/postits/{postit_id}/consultee")
def marquer_consultee(postit_id: int, request: Request):
    """Note ouverte dans /note : elle remonte dans « Récentes »."""
    user = _user(request)
    uid = int(user["id"])
    with get_db() as conn:
        exiger_droit(conn, uid, postit_id, "lire")
        conn.execute(
            """INSERT INTO note_recents (user_id, note_id, vu_le) VALUES (?,?,?)
               ON CONFLICT(user_id, note_id) DO UPDATE SET vu_le=excluded.vu_le""",
            (uid, postit_id, maintenant()),
        )
        conn.execute(
            """DELETE FROM note_recents WHERE user_id=? AND note_id NOT IN
               (SELECT note_id FROM note_recents WHERE user_id=? ORDER BY vu_le DESC LIMIT ?)""",
            (uid, uid, RECENTES_GARDEES),
        )
        conn.commit()
    return {"ok": True}


@router.get("/api/postits/raccourcis")
def raccourcis(request: Request):
    """Favoris (dans leur ordre) et récentes de l'utilisateur, parmi les notes qu'il peut lire."""
    user = _user(request)
    uid = int(user["id"])
    with get_db() as conn:
        def lisibles(rows):
            out = []
            for r in rows:
                d, note = droit_sur(conn, uid, r[0])
                if d and note and not note.get("supprime_le"):
                    out.append({"id": r[0], "title": note.get("title") or "Sans titre", "quand": r[1]})
            return out
        favoris = lisibles(conn.execute(
            "SELECT note_id, cree_le FROM note_favoris WHERE user_id=? ORDER BY ordre, cree_le", (uid,)).fetchall())
        recentes = lisibles(conn.execute(
            "SELECT note_id, vu_le FROM note_recents WHERE user_id=? ORDER BY vu_le DESC LIMIT 12", (uid,)).fetchall())
        mentions = conn.execute(
            """SELECT m.id, m.note_id, m.commentaire_id, m.cree_le, p.title, u.nom AS par, c.texte
                 FROM note_mentions m
                 JOIN postits p ON p.id = m.note_id AND p.supprime_le IS NULL
                 LEFT JOIN users u ON u.id = m.par_user_id
                 LEFT JOIN note_commentaires c ON c.id = m.commentaire_id
                WHERE m.user_id=? AND m.lu_le IS NULL ORDER BY m.id DESC LIMIT 30""",
            (uid,),
        ).fetchall()
    return {"favoris": favoris, "recentes": recentes,
            "mentions": [{"id": m["id"], "note_id": m["note_id"], "commentaire_id": m["commentaire_id"],
                          "titre": m["title"] or "Sans titre", "par": m["par"] or "", "cree_le": m["cree_le"],
                          "extrait": (m["texte"] or "")[:140]} for m in mentions]}


# ── Commentaires ─────────────────────────────────────────────────────────

def _commentaire(r, uid: int, droit: str, noms: dict) -> dict:
    return {
        "id": r["id"], "bloc_uid": r["bloc_uid"], "citation": r["citation"] or "", "texte": r["texte"],
        "user_id": r["user_id"], "nom": noms.get(r["user_id"], "Utilisateur"), "parent_id": r["parent_id"],
        "resolu": bool(r["resolu"]), "resolu_par": noms.get(r["resolu_par"], "") if r["resolu_par"] else "",
        "cree_le": r["cree_le"], "modifie_le": r["modifie_le"],
        "peut_modifier": r["user_id"] == uid,
        "peut_supprimer": r["user_id"] == uid or droit == "proprio",
    }


@router.get("/api/postits/{postit_id}/commentaires")
def lister_commentaires(postit_id: int, request: Request):
    user = _user(request)
    uid = int(user["id"])
    with get_db() as conn:
        droit, _ = exiger_droit(conn, uid, postit_id, "lire")
        noms = {r[0]: r[1] for r in conn.execute("SELECT id, nom FROM users").fetchall()}
        rows = conn.execute("SELECT * FROM note_commentaires WHERE note_id=? ORDER BY id", (postit_id,)).fetchall()
        conn.execute("UPDATE note_mentions SET lu_le=? WHERE note_id=? AND user_id=? AND lu_le IS NULL",
                     (maintenant(), postit_id, uid))
        conn.commit()
    return {"commentaires": [_commentaire(r, uid, droit, noms) for r in rows]}


@router.post("/api/postits/{postit_id}/commentaires")
async def commenter(postit_id: int, request: Request):
    """{texte, bloc_uid, citation, parent_id, mentions:[user_id]} — lecture suffit pour commenter."""
    user = _user(request)
    uid = int(user["id"])
    body = await request.json()
    texte = str(body.get("texte") or "").strip()
    if not texte:
        raise HTTPException(400, "Commentaire vide.")
    if len(texte) > COMMENTAIRE_MAX:
        raise HTTPException(400, f"Commentaire trop long — {COMMENTAIRE_MAX} caractères au plus.")
    parent_id = body.get("parent_id")
    sans_acces, notifies = [], []
    with get_db() as conn:
        droit, note = exiger_droit(conn, uid, postit_id, "lire")
        if parent_id:
            p = conn.execute("SELECT id, bloc_uid, citation FROM note_commentaires WHERE id=? AND note_id=? AND parent_id IS NULL",
                             (int(parent_id), postit_id)).fetchone()
            if not p:
                raise HTTPException(400, "Fil de commentaires introuvable.")
            bloc_uid, citation = p["bloc_uid"], p["citation"]
            parent_id = p["id"]
        else:
            bloc_uid = str(body.get("bloc_uid") or "")[:32] or None
            citation = " ".join(str(body.get("citation") or "").split())[:300] or None
            parent_id = None
        now = maintenant()
        cur = conn.execute(
            """INSERT INTO note_commentaires (note_id, bloc_uid, citation, texte, user_id, parent_id, cree_le)
               VALUES (?,?,?,?,?,?,?)""",
            (postit_id, bloc_uid, citation, texte, uid, parent_id, now),
        )
        cid = cur.lastrowid
        mentionnes = {int(m) for m in (body.get("mentions") or []) if str(m).isdigit()} - {uid}
        for m in sorted(mentionnes)[:20]:
            d, _ = droit_sur(conn, m, postit_id)
            nom = conn.execute("SELECT nom FROM users WHERE id=? AND COALESCE(actif,1)=1", (m,)).fetchone()
            if not nom:
                continue
            if not d:
                sans_acces.append(nom[0])
                continue
            conn.execute("INSERT INTO note_mentions (commentaire_id, note_id, user_id, par_user_id, cree_le) VALUES (?,?,?,?,?)",
                         (cid, postit_id, m, uid, now))
            notifies.append(m)
        _signaler_commentaires(conn, postit_id, uid)
        conn.commit()
        noms = {r[0]: r[1] for r in conn.execute("SELECT id, nom FROM users").fetchall()}
        row = conn.execute("SELECT * FROM note_commentaires WHERE id=?", (cid,)).fetchone()
    if notifies:
        try:
            from app.routers.push import send_push_safe
            titre = f"{user.get('nom') or 'Un collègue'} vous mentionne"
            for m in notifies:
                send_push_safe(m, title=titre, body=f"« {note.get('title') or 'Note'} » : {texte[:120]}",
                               url=f"/note?note={postit_id}&commentaires=1", tag=f"note-{postit_id}")
        except Exception:
            pass
    out = _commentaire(row, uid, droit, noms)
    out["sans_acces"] = sans_acces
    return out


@router.patch("/api/postits/{postit_id}/commentaires/{commentaire_id}")
async def modifier_commentaire(postit_id: int, commentaire_id: int, request: Request):
    """{texte} (son auteur) ou {resolu} (son auteur, ou qui peut écrire dans la note)."""
    user = _user(request)
    uid = int(user["id"])
    body = await request.json()
    with get_db() as conn:
        droit, _ = exiger_droit(conn, uid, postit_id, "lire")
        r = conn.execute("SELECT * FROM note_commentaires WHERE id=? AND note_id=?", (commentaire_id, postit_id)).fetchone()
        if not r:
            raise HTTPException(404, "Commentaire introuvable")
        if "texte" in body:
            if r["user_id"] != uid:
                raise HTTPException(403, "Seul son auteur modifie un commentaire.")
            texte = str(body.get("texte") or "").strip()
            if not texte or len(texte) > COMMENTAIRE_MAX:
                raise HTTPException(400, "Commentaire vide ou trop long.")
            conn.execute("UPDATE note_commentaires SET texte=?, modifie_le=? WHERE id=?", (texte, maintenant(), commentaire_id))
        if "resolu" in body:
            if r["user_id"] != uid and droit not in ("ecrire", "proprio"):
                raise HTTPException(403, "Note en lecture seule pour vous.")
            if body.get("resolu"):
                conn.execute("UPDATE note_commentaires SET resolu=1, resolu_par=?, resolu_le=? WHERE id=?",
                             (uid, maintenant(), commentaire_id))
            else:
                conn.execute("UPDATE note_commentaires SET resolu=0, resolu_par=NULL, resolu_le=NULL WHERE id=?", (commentaire_id,))
        _signaler_commentaires(conn, postit_id, uid)
        conn.commit()
    return {"ok": True}


@router.delete("/api/postits/{postit_id}/commentaires/{commentaire_id}")
def supprimer_commentaire(postit_id: int, commentaire_id: int, request: Request):
    user = _user(request)
    uid = int(user["id"])
    with get_db() as conn:
        droit, _ = exiger_droit(conn, uid, postit_id, "lire")
        r = conn.execute("SELECT user_id FROM note_commentaires WHERE id=? AND note_id=?", (commentaire_id, postit_id)).fetchone()
        if not r:
            raise HTTPException(404, "Commentaire introuvable")
        if r[0] != uid and droit != "proprio":
            raise HTTPException(403, "Seuls son auteur et l'auteur de la note suppriment un commentaire.")
        conn.execute("DELETE FROM note_mentions WHERE commentaire_id IN (SELECT id FROM note_commentaires WHERE id=? OR parent_id=?)",
                     (commentaire_id, commentaire_id))
        conn.execute("DELETE FROM note_commentaires WHERE id=? OR parent_id=?", (commentaire_id, commentaire_id))
        _signaler_commentaires(conn, postit_id, uid)
        conn.commit()
    return {"ok": True}


@router.get("/api/postits/{postit_id}/personnes")
def personnes_mentionnables(postit_id: int, request: Request):
    """Qui peut être mentionné : les collègues actifs, avec leur accès à la note."""
    user = _user(request)
    uid = int(user["id"])
    with get_db() as conn:
        exiger_droit(conn, uid, postit_id, "lire")
        rows = conn.execute("SELECT id, nom FROM users WHERE COALESCE(actif,1)=1 AND id>0 AND id<>? ORDER BY nom COLLATE NOCASE",
                            (uid,)).fetchall()
        return [{"id": r[0], "nom": r[1], "acces": bool(droit_sur(conn, r[0], postit_id)[0])} for r in rows]


# ── Liens vers MySifa (« @ » dans le texte) ─────────────────────────────

@router.get("/api/postits/references")
def references(request: Request, q: str = ""):
    """Objets MySifa à lier depuis une note : notes, dossiers, machines, clients.

    Chaque lien mène à la page où l'utilisateur peut voir l'objet ; une page
    qui lui est fermée n'est pas proposée."""
    user = _user(request)
    uid = int(user["id"])
    q = " ".join((q or "").split())[:60]
    like = f"%{q}%"
    out = []
    with get_db() as conn:
        # Notes (les siennes et celles partagées avec lui)
        for r in conn.execute(
            """SELECT p.id, p.title FROM postits p
                WHERE p.supprime_le IS NULL AND p.title LIKE ? AND
                      (p.user_id=? OR EXISTS (SELECT 1 FROM note_partages s WHERE s.note_id=p.id AND s.user_id=?))
                ORDER BY p.modifie_le DESC LIMIT 6""", (like, uid, uid)).fetchall():
            out.append({"type": "note", "libelle": r["title"] or "Sans titre", "detail": "Note", "url": f"/note?note={r['id']}"})
        prod = user_has_app_access(user, "prod")
        planning = user_has_app_access(user, "planning")
        if q and (prod or planning):
            vus = set()
            for r in conn.execute(
                """SELECT pe.id, pe.reference, pe.client, pe.description, pe.machine_id, m.nom AS machine
                     FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id
                    WHERE pe.reference LIKE ? OR pe.client LIKE ? OR pe.description LIKE ?
                    ORDER BY (pe.reference LIKE ?) DESC, pe.id DESC LIMIT 20""", (like, like, like, q + "%")).fetchall():
                ref = (r["reference"] or "").strip()
                if not ref or ref in vus:
                    continue
                vus.add(ref)
                url = (f"/prod?page=traceabilite&dossier={ref}" if prod
                       else f"/planning?machine={r['machine_id']}&dossier={r['id']}")
                detail = " · ".join(x for x in (r["client"], r["machine"]) if x)
                out.append({"type": "dossier", "libelle": ref, "detail": detail or "Dossier", "url": url})
                if len(vus) >= 6:
                    break
        if planning:
            for r in conn.execute(
                "SELECT id, nom FROM machines WHERE COALESCE(actif,1)=1 AND nom LIKE ? ORDER BY nom LIMIT 6", (like,)).fetchall():
                out.append({"type": "machine", "libelle": r["nom"], "detail": "Machine", "url": f"/planning?machine={r['id']}"})
        if q and can_access_settings(user) and can_access_settings_contacts(user):
            try:
                for r in conn.execute(
                    """SELECT id, raison_sociale, ville FROM clients
                        WHERE raison_sociale LIKE ? OR code LIKE ? ORDER BY raison_sociale LIMIT 6""", (like, like)).fetchall():
                    out.append({"type": "client", "libelle": r["raison_sociale"], "detail": " · ".join(x for x in ("Client", r["ville"]) if x),
                                "url": f"/settings?onglet=clients&client={r['id']}"})
            except Exception:
                pass
    return {"resultats": out}


# ── Export ───────────────────────────────────────────────────────────────

def _disposition(nom: str) -> str:
    """En-tête de téléchargement sûr pour tout titre : repli ASCII + nom UTF-8 (RFC 5987)."""
    import unicodedata
    from urllib.parse import quote
    ascii_ = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode() or "note"
    return f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nom)}"


def _note_export(conn, uid: int, postit_id: int):
    _, note = exiger_droit(conn, uid, postit_id, "lire")
    auteur = conn.execute("SELECT nom FROM users WHERE id=?", (note["user_id"],)).fetchone()
    quand = (note.get("modifie_le") or note.get("created_at") or "")[:10]
    date = "/".join(reversed(quand.split("-"))) if quand else ""
    return note, lire_blocs(note.get("contenu")), (auteur[0] if auteur else ""), date


@router.get("/api/postits/{postit_id}/export.pdf")
def export_pdf(postit_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        note, blocs, auteur, date = _note_export(conn, int(user["id"]), postit_id)
        pdf = notes_export.pdf_note(conn, note.get("title"), blocs, auteur, date)
    nom = notes_export.nom_fichier(note.get("title"), "pdf")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": _disposition(nom)})


@router.get("/api/postits/{postit_id}/export.docx")
def export_docx(postit_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        note, blocs, auteur, date = _note_export(conn, int(user["id"]), postit_id)
        doc = notes_export.docx_note(conn, note.get("title"), blocs, auteur, date)
    nom = notes_export.nom_fichier(note.get("title"), "docx")
    return Response(doc, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": _disposition(nom)})


def pdf_pour_impression(user: dict, postit_id: int) -> tuple[bytes, str]:
    """PDF d'une note pour l'impression réseau (app/routers/print.py, entity_type « note »)."""
    with get_db() as conn:
        note, blocs, auteur, date = _note_export(conn, int(user["id"]), postit_id)
        pdf = notes_export.pdf_note(conn, note.get("title"), blocs, auteur, date)
    return pdf, notes_export.nom_fichier(note.get("title"), "pdf")
