"""MySifa — Outil RH (onglet de MyCompta).

Liste partagée des employés suivis dans l'onglet « Outil RH ». On y ajoute un
employé choisi parmi tous les comptes (actifs ou non), on peut le retirer.
Chaque employé suivi porte une checklist :
- des cases fixes, une colonne de rh_outil_membres chacune (CHECKLIST) ;
- des listes qui varient d'un employé à l'autre (LISTES : formations,
  documents), piochées chacune dans un catalogue commun géré depuis l'onglet.
Les formations se rangent par catégorie (rh_outil_formation_categories,
modifiable) et peuvent entraîner des documents : attribuer une formation à un
employé lui attribue aussi ses documents liés (rh_outil_formation_documents).
Chaque employé a le service de son compte (users.role, jamais modifié ici).
Un élément du catalogue est « exigé pour » personne, tous les employés
(colonne obligatoire) ou certains services (tables *_services) — jamais les
deux à la fois. Il est alors attribué d'office aux employés concernés.
Les documents d'un employé peuvent porter des pièces jointes (rh_outil_pieces),
rangées hors de /static sous data/uploads/rh_outil/.
Le contrat (type, début, fin) vit dans la fiche Paie (paie_employes) : l'Outil
RH le crée avec le compte et le modifie (app/routers/rh_outil_contrat.py), sans
jamais toucher aux éléments de salaire.
L'onglet sert au suivi des nouveaux employés : « Nouvel employé » crée le compte
MySifa (mêmes règles que Paramètres › Comptes, fonctions partagées avec
app/routers/auth.py) et l'inscrit au suivi avec sa date d'arrivée.
Accès : quiconque a accès à MyCompta (rôle ou exception réglée dans Paramètres).
Créer un compte demande en plus le droit de gérer les comptes (Paramètres).
"""

import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import (
    ASSIGNABLE_ROLES,
    BASE_DIR,
    CONTRATS_DUREE_INDETERMINEE,
    CONTRATS_TYPES,
    RH_OUTIL_ALERTE_FIN_CONTRAT_JOURS,
    RH_OUTIL_MAX_FILE_MB,
    SUPERADMIN_EMAIL,
    role_label,
    taches_services,
)
from database import get_db
from services.auth_service import (
    can_access_settings_contacts,
    get_current_user,
    hash_password,
    is_real_superadmin,
    user_has_app_access,
)
from services.audit_service import log_action

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])

LIBELLE_MAX = 120

PIECES_ROOT = Path(BASE_DIR) / "data" / "uploads" / "rh_outil"
PIECE_MAX_OCTETS = RH_OUTIL_MAX_FILE_MB * 1024 * 1024
PIECE_NOM_MAX = 180


def _type_fichier(debut: bytes) -> Optional[tuple]:
    """(mime, extension) d'après les premiers octets du fichier, jamais d'après
    son nom ni le Content-Type annoncé par le navigateur. None si refusé."""
    if debut.startswith(b"%PDF-"):
        return ("application/pdf", "pdf")
    if debut.startswith(b"\xff\xd8\xff"):
        return ("image/jpeg", "jpg")
    if debut.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("image/png", "png")
    if debut[:4] == b"RIFF" and debut[8:12] == b"WEBP":
        return ("image/webp", "webp")
    if debut[4:8] == b"ftyp" and debut[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"hevc"):
        return ("image/heic", "heic")
    return None


def _supprimer_fichiers(chemins: list) -> None:
    """Efface les fichiers après le commit ; un fichier déjà absent n'est pas une erreur."""
    for c in chemins:
        try:
            (PIECES_ROOT / c).unlink(missing_ok=True)
        except OSError:
            pass


def _retirer_pieces(conn, where: str, params: tuple) -> list:
    """Supprime les lignes rh_outil_pieces des attributions de documents qui
    vérifient `where` (sur l'alias a = rh_outil_membre_documents). Renvoie les
    fichiers à effacer une fois la transaction validée."""
    rows = conn.execute(
        f"""SELECT p.id, p.fichier FROM rh_outil_pieces p
              JOIN rh_outil_membre_documents a ON a.id = p.attribution_id
             WHERE {where}""",
        params,
    ).fetchall()
    if rows:
        conn.execute(
            f"DELETE FROM rh_outil_pieces WHERE id IN ({','.join('?' * len(rows))})",
            [r["id"] for r in rows],
        )
    return [r["fichier"] for r in rows]


class MembreIn(BaseModel):
    user_id: int


class MembrePatch(BaseModel):
    reglement_signe: Optional[bool] = None
    date_arrivee: Optional[str] = None


class NouvelEmployeIn(BaseModel):
    prenom: str
    nom: str
    email: str
    service: str
    password: str
    date_arrivee: str
    contrat_type: str
    contrat_fin: Optional[str] = None


class LibelleIn(BaseModel):
    libelle: str
    categorie_id: Optional[int] = None   # formations seulement, à la création


class CategorieRef(BaseModel):
    categorie_id: Optional[int] = None


class DocumentsLies(BaseModel):
    documents: list[int]


class AttributionIn(BaseModel):
    element_id: int


class ExigeIn(BaseModel):
    """« Exigé pour » : tous les employés, ou la liste de services (vide =
    personne). Les deux sont exclusifs : `tous` l'emporte et vide les services."""
    tous: bool = False
    services: list[str] = []


class AttributionPatch(BaseModel):
    fait: bool


# Listes par employé. Chaque liste = un catalogue + une table de liaison
# employé ↔ élément avec une case « fait ». Les noms de tables et de colonnes
# viennent d'ici, jamais de la requête : les f-strings SQL sont sûres.
LISTES = {
    "formations": {
        "catalogue": "rh_outil_formations",
        "liaison": "rh_outil_membre_formations",
        "fk": "formation_id",
        "exigences": "rh_outil_formation_services",
        "categories": True,
        "nom": "formation",
        "catalogue_nom": "catalogue des formations",
        "doublon": "Cette formation existe déjà au catalogue.",
        "introuvable": "Formation introuvable.",
        "deja": "Cet employé a déjà cette formation.",
        "fait": ("faite", "à faire"),
    },
    "documents": {
        "catalogue": "rh_outil_documents",
        "liaison": "rh_outil_membre_documents",
        "fk": "document_id",
        "exigences": "rh_outil_document_services",
        "nom": "document",
        "catalogue_nom": "catalogue des documents",
        "doublon": "Ce document existe déjà au catalogue.",
        "introuvable": "Document introuvable.",
        "deja": "Cet employé a déjà ce document.",
        "fait": ("vérifié", "à vérifier"),
    },
}


def _liste(liste: str) -> dict:
    cfg = LISTES.get(liste)
    if not cfg:
        raise HTTPException(404, "Liste inconnue.")
    return cfg


# Points fixes de la checklist : champ de MembrePatch → libellé du journal.
# Chaque point est une colonne de rh_outil_membres (migration fichier).
CHECKLIST = {"reglement_signe": "Règlement signé"}


def _piece_json(pc) -> dict:
    return {"id": pc["id"], "nom": pc["nom"], "mime": pc["mime"], "taille": pc["taille"],
            "ajoute_le": pc["ajoute_le"], "ajoute_par": pc["ajoute_par"]}


def _require(request: Request) -> dict:
    u = get_current_user(request)
    if not user_has_app_access(u, "compta"):
        raise HTTPException(status_code=403, detail="Accès réservé à MyCompta")
    return u


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _libelle(brut: str) -> str:
    libelle = " ".join((brut or "").split())
    if not libelle:
        raise HTTPException(400, "Intitulé vide.")
    if len(libelle) > LIBELLE_MAX:
        raise HTTPException(400, f"Intitulé trop long — {LIBELLE_MAX} caractères maximum.")
    return libelle


def _membre(conn, membre_id: int):
    row = conn.execute(
        """SELECT m.id, u.nom FROM rh_outil_membres m
             JOIN users u ON u.id = m.user_id WHERE m.id=?""",
        (membre_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Employé introuvable dans la liste.")
    return row


def _attribuer_obligatoires(conn, membre_id: Optional[int] = None,
                            liste: Optional[str] = None, element_id: Optional[int] = None) -> int:
    """Attribue les éléments obligatoires qui manquent (case « fait » décochée).

    Filtrable par employé, par liste et par élément ; sans filtre, rattrape
    tout. Ne retire jamais rien. Renvoie le nombre d'attributions créées.
    """
    n = 0
    for cle, cfg in LISTES.items():
        if liste and cle != liste:
            continue
        where, params = ["e.obligatoire = 1"], [_now()]
        if membre_id is not None:
            where.append("m.id = ?"); params.append(membre_id)
        if element_id is not None:
            where.append("e.id = ?"); params.append(element_id)
        n += conn.execute(
            f"""INSERT OR IGNORE INTO {cfg['liaison']} (membre_id, {cfg['fk']}, fait, ajoute_le)
                SELECT m.id, e.id, 0, ?
                  FROM rh_outil_membres m CROSS JOIN {cfg['catalogue']} e
                 WHERE {' AND '.join(where)}""",
            params,
        ).rowcount
    return n


def _attribuer_par_service(conn, membre_id: Optional[int] = None, liste: Optional[str] = None,
                          element_id: Optional[int] = None, service: Optional[str] = None) -> int:
    """Attribue les éléments exigés pour un service aux employés de ce service
    (service = rôle du compte) qui ne les ont pas encore. Filtrable par
    employé, liste, élément et service. Ne retire jamais rien. Renvoie le
    nombre d'attributions créées."""
    n = 0
    for cle, cfg in LISTES.items():
        if liste and cle != liste:
            continue
        where, params = ["1=1"], [_now()]
        if membre_id is not None:
            where.append("m.id = ?"); params.append(membre_id)
        # La colonne de l'élément est renommée `element_id` dans la sous-requête :
        # chaque morceau de la clause reste une chaîne littérale (garde-fou
        # tests/test_sql_where_dynamique.py).
        if element_id is not None:
            where.append("x.element_id = ?"); params.append(element_id)
        if service is not None:
            where.append("x.service = ?"); params.append(service)
        n += conn.execute(
            f"""INSERT OR IGNORE INTO {cfg['liaison']} (membre_id, {cfg['fk']}, fait, ajoute_le)
                SELECT DISTINCT m.id, x.element_id, 0, ?
                  FROM (SELECT {cfg['fk']} AS element_id, service FROM {cfg['exigences']}) x
                  JOIN users u ON u.role = x.service
                  JOIN rh_outil_membres m ON m.user_id = u.id
                 WHERE {' AND '.join(where)}""",
            params,
        ).rowcount
    return n


def _documents_lies(conn, paires) -> int:
    """Attribue les documents liés aux formations pour chaque paire
    (membre_id, formation_id) donnée. On ne passe que des attributions de
    formation qui viennent d'être créées : une exception posée à la main sur
    un document n'est jamais annulée par un rattrapage global."""
    n = 0
    for membre_id, formation_id in paires:
        n += conn.execute(
            """INSERT OR IGNORE INTO rh_outil_membre_documents (membre_id, document_id, fait, ajoute_le)
               SELECT ?, fd.document_id, 0, ? FROM rh_outil_formation_documents fd
                WHERE fd.formation_id = ?""",
            (membre_id, _now(), formation_id),
        ).rowcount
    return n


def _formations_du_membre(conn, membre_id: int) -> list:
    return [(membre_id, r["formation_id"]) for r in conn.execute(
        "SELECT formation_id FROM rh_outil_membre_formations WHERE membre_id=?", (membre_id,)).fetchall()]


def _membres_de_formation(conn, formation_id: int) -> set:
    return {r["membre_id"] for r in conn.execute(
        "SELECT membre_id FROM rh_outil_membre_formations WHERE formation_id=?", (formation_id,)).fetchall()}


def _categorie(conn, categorie_id: Optional[int]):
    if categorie_id is None:
        return None
    row = conn.execute("SELECT id, libelle FROM rh_outil_formation_categories WHERE id=?",
                       (categorie_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Catégorie introuvable.")
    return row


def _services() -> list:
    """Services existants : ceux de MySifa (un service est un rôle, cf.
    config.taches_services), libellés compris. Rien n'est créé ici."""
    return taches_services()


def _date(brut: Optional[str]) -> Optional[str]:
    """AAAA-MM-JJ valide, ou None si vide. Erreur 400 sinon."""
    brut = (brut or "").strip()
    if not brut:
        return None
    try:
        return date.fromisoformat(brut).isoformat()
    except ValueError:
        raise HTTPException(400, "Date d'arrivée invalide — format AAAA-MM-JJ.")


def _jour_fr(iso: Optional[str]) -> str:
    """« 2026-10-06 » → « 06/10/2026 » pour le Journal."""
    return date.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "non renseignée"


def _services_creables(user: dict) -> list:
    """Services qu'un compte créé ici peut recevoir : les rôles attribuables,
    moins Direction si l'auteur n'est pas le vrai super admin (même garde que
    Paramètres › Comptes)."""
    from app.routers.auth import _ROLES_COMPTES_PROTEGES
    return [s for s in _services()
            if s["code"] in ASSIGNABLE_ROLES
            and (is_real_superadmin(user) or s["code"] not in _ROLES_COMPTES_PROTEGES)]


def _doublon(conn, cfg: dict, libelle: str, sauf_id: Optional[int] = None) -> bool:
    row = conn.execute(
        f"SELECT id FROM {cfg['catalogue']} WHERE libelle = ? COLLATE NOCASE AND id != ?",
        (libelle, sauf_id or 0),
    ).fetchone()
    return row is not None


# ─── Employés ─────────────────────────────────────────────────────────────

@router.get("/employes")
def list_employes(request: Request):
    """Tous les comptes, actifs ou non, pour le sélecteur d'ajout."""
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id, u.nom, u.email, u.role, u.actif,
                      (m.id IS NOT NULL) AS deja_ajoute
                 FROM users u
                 LEFT JOIN rh_outil_membres m ON m.user_id = u.id
                WHERE LOWER(COALESCE(u.nom,'')) != 'administrateur'
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
    return {"employes": [
        {"user_id": r["id"], "nom": r["nom"], "email": r["email"], "role": r["role"],
         "actif": bool(r["actif"]), "deja_ajoute": bool(r["deja_ajoute"])}
        for r in rows
    ]}


@router.post("/employes")
def create_employe(payload: NouvelEmployeIn, request: Request):
    """Crée le compte MySifa d'un nouvel employé et l'inscrit au suivi.

    Mêmes règles que Paramètres › Comptes (POST /api/users) : email obligatoire
    et unique, mot de passe de 8 caractères minimum saisi par l'auteur, rôle
    attribuable, Direction réservée au vrai super admin, identifiant généré et
    dédoublonné. Le mot de passe n'est ni journalisé ni renvoyé."""
    from app.routers.auth import (
        _default_identifiant_from_nom, _ensure_unique_identifiant,
        _guard_role_attribuable, _norm_email,
    )
    user = _require(request)
    if not can_access_settings_contacts(user):
        raise HTTPException(403, "Créer un compte demande le droit de gérer les comptes (Paramètres).")
    prenom = " ".join((payload.prenom or "").split())
    nom_famille = " ".join((payload.nom or "").split())
    if not prenom or not nom_famille:
        raise HTTPException(400, "Prénom et nom obligatoires.")
    nom = f"{prenom} {nom_famille}"[:120]
    email = _norm_email(payload.email)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Email invalide.")
    if email == _norm_email(SUPERADMIN_EMAIL):
        raise HTTPException(400, "Cet email est réservé au compte super administrateur.")
    if payload.service not in ASSIGNABLE_ROLES:
        raise HTTPException(400, "Service invalide.")
    _guard_role_attribuable(user, payload.service)
    if len(payload.password or "") < 8:
        raise HTTPException(400, "Mot de passe trop court — 8 caractères minimum.")
    arrivee = _date(payload.date_arrivee)
    if not arrivee:
        raise HTTPException(400, "Date d'arrivée obligatoire.")
    if payload.contrat_type not in CONTRATS_TYPES:
        raise HTTPException(400, "Type de contrat invalide.")
    fin = None if payload.contrat_type in CONTRATS_DUREE_INDETERMINEE else _date(payload.contrat_fin)
    if fin and fin < arrivee:
        raise HTTPException(400, "La fin de contrat précède la date d'arrivée.")
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email)=?", (email,)).fetchone():
            raise HTTPException(409, "Un compte existe déjà avec cet email.")
        ident = _ensure_unique_identifiant(conn, _default_identifiant_from_nom(nom)) or None
        cur = conn.execute(
            """INSERT INTO users (email, identifiant, nom, password_hash, role, actif, created_at)
               VALUES (?,?,?,?,?,1,?)""",
            (email, ident, nom, hash_password(payload.password), payload.service,
             datetime.now().isoformat()),
        )
        user_id = cur.lastrowid
        cur = conn.execute(
            """INSERT INTO rh_outil_membres (user_id, ajoute_le, ajoute_par, date_arrivee)
               VALUES (?,?,?,?)""",
            (user_id, _now(), user.get("nom"), arrivee),
        )
        membre_id = cur.lastrowid
        # Fiche Paie : seulement le contrat. Salaire, taux, primes restent à
        # la comptabilité, dans la Paie.
        conn.execute(
            """INSERT INTO paie_employes (user_id, contrat_type, date_debut, date_fin, updated_at, updated_by)
               VALUES (?,?,?,?,?,?)""",
            (user_id, payload.contrat_type, arrivee, fin, datetime.now().isoformat(), user.get("email")),
        )
        n = _attribuer_obligatoires(conn, membre_id=membre_id)
        n += _attribuer_par_service(conn, membre_id=membre_id)
        n += _documents_lies(conn, _formations_du_membre(conn, membre_id))
        conn.commit()
    # Même trace que Paramètres pour la création du compte, puis celle du suivi.
    log_action(user=user, action="CREATE", module="settings",
               objet=f"Utilisateur {nom} [{payload.service}]", detail={"email": email},
               request=request)
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · nouvel employé {nom} ({role_label(payload.service)}, "
                     f"{payload.contrat_type}), arrivée le {_jour_fr(arrivee)}" + (f" · {n} élément(s) attribué(s)" if n else ""),
               request=request)
    return {"success": True, "membre_id": membre_id, "identifiant": ident, "attribues": n}


@router.get("/membres")
def list_membres(request: Request):
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT m.id, m.user_id, m.ajoute_le, m.ajoute_par, m.reglement_signe, m.date_arrivee,
                      u.nom, u.email, u.role, u.actif,
                      pe.contrat_type, pe.date_debut AS contrat_debut, pe.date_fin AS contrat_fin
                 FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id
                 LEFT JOIN paie_employes pe ON pe.user_id = u.id
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
        # {liste: {membre_id: [éléments]}}
        par_liste: dict = {}
        for liste, cfg in LISTES.items():
            par_membre = par_liste.setdefault(liste, {})
            for a in conn.execute(
                f"""SELECT a.id, a.membre_id, a.{cfg['fk']} AS element_id, a.fait, e.libelle, e.obligatoire,
                           {'e.categorie_id' if cfg.get('categories') else 'NULL'} AS categorie_id
                      FROM {cfg['liaison']} a
                      JOIN {cfg['catalogue']} e ON e.id = a.{cfg['fk']}
                     ORDER BY e.libelle COLLATE NOCASE"""
            ).fetchall():
                par_membre.setdefault(a["membre_id"], []).append(
                    {"id": a["id"], "element_id": a["element_id"],
                     "libelle": a["libelle"], "fait": bool(a["fait"]),
                     "obligatoire": bool(a["obligatoire"]), "categorie_id": a["categorie_id"]}
                )
        pieces: dict = {}
        for pc in conn.execute(
            """SELECT id, attribution_id, nom, mime, taille, ajoute_le, ajoute_par
                 FROM rh_outil_pieces ORDER BY ajoute_le, id"""
        ).fetchall():
            pieces.setdefault(pc["attribution_id"], []).append(_piece_json(pc))
    for x in par_liste.get("documents", {}).values():
        for el in x:
            el["pieces"] = pieces.get(el["id"], [])
    membres = []
    for r in rows:
        m = {"id": r["id"], "user_id": r["user_id"], "nom": r["nom"], "email": r["email"],
             "role": r["role"], "actif": bool(r["actif"]),
             "service": r["role"] or "", "service_label": role_label(r["role"] or ""),
             "ajoute_le": r["ajoute_le"], "ajoute_par": r["ajoute_par"],
             "reglement_signe": bool(r["reglement_signe"]),
             "date_arrivee": r["date_arrivee"],
             # Pas de fiche Paie ou type vide : « à renseigner », jamais « CDI » supposé.
             "contrat_type": r["contrat_type"] or None,
             "contrat_debut": r["contrat_debut"], "contrat_fin": r["contrat_fin"]}
        for liste in LISTES:
            m[liste] = par_liste[liste].get(r["id"], [])
        membres.append(m)
    return {"membres": membres}


@router.post("/membres")
def add_membre(payload: MembreIn, request: Request):
    user = _require(request)
    with get_db() as conn:
        emp = conn.execute("SELECT id, nom FROM users WHERE id=?", (payload.user_id,)).fetchone()
        if not emp:
            raise HTTPException(404, "Employé introuvable.")
        cur = conn.execute(
            "INSERT OR IGNORE INTO rh_outil_membres (user_id, ajoute_le, ajoute_par) VALUES (?,?,?)",
            (emp["id"], _now(), user.get("nom")),
        )
        if not cur.rowcount:
            raise HTTPException(409, "Employé déjà dans la liste.")
        _attribuer_obligatoires(conn, membre_id=cur.lastrowid)
        _attribuer_par_service(conn, membre_id=cur.lastrowid)
        _documents_lies(conn, _formations_du_membre(conn, cur.lastrowid))
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · ajout de {emp['nom']}", request=request)
    return {"success": True}


@router.patch("/membres/{membre_id}")
def update_membre(membre_id: int, payload: MembrePatch, request: Request):
    user = _require(request)
    brut = payload.model_dump(exclude_unset=True)
    data = {k: v for k, v in brut.items() if k in CHECKLIST}
    if "date_arrivee" in brut:
        arrivee = _date(brut["date_arrivee"])
        with get_db() as conn:
            row = _membre(conn, membre_id)
            conn.execute("UPDATE rh_outil_membres SET date_arrivee=? WHERE id=?", (arrivee, membre_id))
            conn.commit()
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · {row['nom']} · date d'arrivée : {_jour_fr(arrivee)}",
                   request=request)
    if not data:
        return {"success": True}
    with get_db() as conn:
        row = _membre(conn, membre_id)
        # Les clés viennent de CHECKLIST, jamais de la requête : pas d'injection.
        sets = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE rh_outil_membres SET {sets} WHERE id=?",
                     [1 if v else 0 for v in data.values()] + [membre_id])
        conn.commit()
    for k, v in data.items():
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · {row['nom']} · {CHECKLIST[k]} : {'oui' if v else 'non'}",
                   request=request)
    return {"success": True}


@router.delete("/membres/{membre_id}")
def delete_membre(membre_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = _membre(conn, membre_id)
        fichiers = _retirer_pieces(conn, "a.membre_id = ?", (membre_id,))
        for cfg in LISTES.values():
            conn.execute(f"DELETE FROM {cfg['liaison']} WHERE membre_id=?", (membre_id,))
        conn.execute("DELETE FROM rh_outil_membres WHERE id=?", (membre_id,))
        conn.commit()
    _supprimer_fichiers(fichiers)
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · retrait de {row['nom']}", request=request)
    return {"success": True}


# ─── Services (lecture) et exigences par service ──────────────────────────
# Déclarées avant les routes génériques « /{liste}/catalogue/... » : FastAPI
# prend la première route qui correspond.

@router.get("/services")
def list_services(request: Request):
    """Services existants de MySifa (un service est un rôle). Lecture seule.
    Indique aussi si l'utilisateur peut créer un compte, et avec quels services."""
    user = _require(request)
    peut = can_access_settings_contacts(user)
    return {"services": _services(), "peut_creer": peut,
            "services_creables": _services_creables(user) if peut else [],
            "contrats": list(CONTRATS_TYPES),
            "contrats_sans_fin": sorted(CONTRATS_DUREE_INDETERMINEE),
            "alerte_fin_contrat_jours": RH_OUTIL_ALERTE_FIN_CONTRAT_JOURS}


# ─── Catégories de formations et documents liés ──────────────────────────

@router.get("/formations/categories")
def list_categories(request: Request):
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.id, c.libelle, c.ordre,
                      (SELECT COUNT(*) FROM rh_outil_formations f WHERE f.categorie_id = c.id) AS nb
                 FROM rh_outil_formation_categories c
                ORDER BY c.ordre, c.libelle COLLATE NOCASE"""
        ).fetchall()
    return {"categories": [{"id": r["id"], "libelle": r["libelle"], "nb_formations": r["nb"]} for r in rows]}


@router.post("/formations/categories")
def add_categorie(payload: LibelleIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM rh_outil_formation_categories WHERE libelle=? COLLATE NOCASE",
                        (libelle,)).fetchone():
            raise HTTPException(409, "Cette catégorie existe déjà.")
        ordre = conn.execute("SELECT COALESCE(MAX(ordre),0)+10 FROM rh_outil_formation_categories").fetchone()[0]
        cur = conn.execute(
            "INSERT INTO rh_outil_formation_categories (libelle, ordre, cree_le) VALUES (?,?,?)",
            (libelle, ordre, _now()))
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · catégories de formations · ajout de « {libelle} »", request=request)
    return {"success": True, "id": cur.lastrowid}


@router.put("/formations/categories/{categorie_id}")
def rename_categorie(categorie_id: int, payload: LibelleIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        row = _categorie(conn, categorie_id)
        if row["libelle"] == libelle:
            return {"success": True}
        if conn.execute("SELECT 1 FROM rh_outil_formation_categories WHERE libelle=? COLLATE NOCASE AND id!=?",
                        (libelle, categorie_id)).fetchone():
            raise HTTPException(409, "Cette catégorie existe déjà.")
        conn.execute("UPDATE rh_outil_formation_categories SET libelle=? WHERE id=?", (libelle, categorie_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · catégories de formations · « {row['libelle']} » → « {libelle} »",
               request=request)
    return {"success": True}


@router.delete("/formations/categories/{categorie_id}")
def delete_categorie(categorie_id: int, request: Request):
    """Supprime la catégorie ; ses formations restent, sans catégorie."""
    user = _require(request)
    with get_db() as conn:
        row = _categorie(conn, categorie_id)
        n = conn.execute("UPDATE rh_outil_formations SET categorie_id=NULL WHERE categorie_id=?",
                         (categorie_id,)).rowcount
        conn.execute("DELETE FROM rh_outil_formation_categories WHERE id=?", (categorie_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · catégories de formations · suppression de « {row['libelle']} » "
                     f"({n} formation(s) sans catégorie)", request=request)
    return {"success": True}


@router.put("/formations/catalogue/{element_id}/categorie")
def set_categorie(element_id: int, payload: CategorieRef, request: Request):
    user = _require(request)
    with get_db() as conn:
        f = conn.execute("SELECT libelle, categorie_id FROM rh_outil_formations WHERE id=?",
                         (element_id,)).fetchone()
        if not f:
            raise HTTPException(404, "Formation introuvable.")
        cat = _categorie(conn, payload.categorie_id)
        if f["categorie_id"] == payload.categorie_id:
            return {"success": True}
        conn.execute("UPDATE rh_outil_formations SET categorie_id=? WHERE id=?",
                     (payload.categorie_id, element_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · catalogue des formations · « {f['libelle']} » → catégorie "
                     f"« {cat['libelle'] if cat else 'Sans catégorie'} »", request=request)
    return {"success": True}


@router.put("/formations/catalogue/{element_id}/documents")
def set_documents_lies(element_id: int, payload: DocumentsLies, request: Request):
    """Remplace les documents liés à la formation. Un document nouvellement lié
    est attribué tout de suite aux employés qui ont la formation ; délier ne
    retire rien."""
    user = _require(request)
    voulus = set(payload.documents)
    with get_db() as conn:
        f = conn.execute("SELECT libelle FROM rh_outil_formations WHERE id=?", (element_id,)).fetchone()
        if not f:
            raise HTTPException(404, "Formation introuvable.")
        if voulus:
            connus = {r["id"] for r in conn.execute(
                f"SELECT id FROM rh_outil_documents WHERE id IN ({','.join('?' * len(voulus))})",
                list(voulus)).fetchall()}
            if connus != voulus:
                raise HTTPException(404, "Document introuvable.")
        avant = {r["document_id"] for r in conn.execute(
            "SELECT document_id FROM rh_outil_formation_documents WHERE formation_id=?",
            (element_id,)).fetchall()}
        for d in avant - voulus:
            conn.execute("DELETE FROM rh_outil_formation_documents WHERE formation_id=? AND document_id=?",
                         (element_id, d))
        n = 0
        for d in voulus - avant:
            conn.execute("INSERT OR IGNORE INTO rh_outil_formation_documents (formation_id, document_id) VALUES (?,?)",
                         (element_id, d))
            n += conn.execute(
                """INSERT OR IGNORE INTO rh_outil_membre_documents (membre_id, document_id, fait, ajoute_le)
                   SELECT a.membre_id, ?, 0, ? FROM rh_outil_membre_formations a WHERE a.formation_id = ?""",
                (d, _now(), element_id)).rowcount
        conn.commit()
    if avant != voulus:
        suite = f" · {n} attribution(s)" if n else ""
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · catalogue des formations · « {f['libelle']} » : "
                         f"{len(voulus)} document(s) lié(s){suite}", request=request)
    return {"success": True, "attribues": n}


@router.put("/{liste}/catalogue/{element_id}/exige")
def set_exige(liste: str, element_id: int, payload: ExigeIn, request: Request):
    """Règle « Exigé pour ». Ce qui devient exigé est attribué tout de suite
    aux employés concernés qui ne l'ont pas ; ce qui cesse de l'être ne retire
    rien."""
    user = _require(request)
    cfg = _liste(liste)
    voulus = set() if payload.tous else set(payload.services)
    if not voulus <= {s["code"] for s in _services()}:
        raise HTTPException(400, "Service inconnu.")
    with get_db() as conn:
        row = conn.execute(f"SELECT libelle, obligatoire FROM {cfg['catalogue']} WHERE id=?",
                           (element_id,)).fetchone()
        if not row:
            raise HTTPException(404, cfg["introuvable"])
        tous_avant = bool(row["obligatoire"])
        deja = _membres_de_formation(conn, element_id) if liste == "formations" else set()
        avant = {r["service"] for r in conn.execute(
            f"SELECT service FROM {cfg['exigences']} WHERE {cfg['fk']}=?", (element_id,)).fetchall()}
        conn.execute(f"UPDATE {cfg['catalogue']} SET obligatoire=? WHERE id=?",
                     (1 if payload.tous else 0, element_id))
        for sv in avant - voulus:
            conn.execute(f"DELETE FROM {cfg['exigences']} WHERE {cfg['fk']}=? AND service=?",
                         (element_id, sv))
        n = 0
        for sv in voulus - avant:
            conn.execute(f"INSERT OR IGNORE INTO {cfg['exigences']} ({cfg['fk']}, service) VALUES (?,?)",
                         (element_id, sv))
            n += _attribuer_par_service(conn, liste=liste, element_id=element_id, service=sv)
        if payload.tous and not tous_avant:
            n += _attribuer_obligatoires(conn, liste=liste, element_id=element_id)
        if liste == "formations":
            nouveaux = _membres_de_formation(conn, element_id) - deja
            _documents_lies(conn, [(mid, element_id) for mid in nouveaux])
        conn.commit()
    if payload.tous != tous_avant or voulus != avant:
        cible = ("tous les employés" if payload.tous
                 else ", ".join(sorted(role_label(v) for v in voulus)) or "personne")
        suite = f" · attribué à {n} employé(s)" if n else ""
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · {cfg['catalogue_nom']} · « {row['libelle']} » exigé pour : {cible}{suite}",
                   request=request)
    return {"success": True, "attribues": n}


# ─── Catalogues (formations, documents) ───────────────────────────────────

@router.get("/{liste}/catalogue")
def list_catalogue(liste: str, request: Request):
    _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT e.id, e.libelle, e.obligatoire,
                       (SELECT COUNT(*) FROM {cfg['liaison']} a
                         WHERE a.{cfg['fk']} = e.id) AS nb_employes
                  FROM {cfg['catalogue']} e
                 ORDER BY e.libelle COLLATE NOCASE"""
        ).fetchall()
        exiges: dict = {}
        for x in conn.execute(f"SELECT {cfg['fk']} AS el, service FROM {cfg['exigences']}").fetchall():
            exiges.setdefault(x["el"], []).append(x["service"])
        lies: dict = {}
        cats: dict = {}
        if cfg.get("categories"):
            for x in conn.execute("SELECT formation_id, document_id FROM rh_outil_formation_documents").fetchall():
                lies.setdefault(x["formation_id"], []).append(x["document_id"])
            cats = {x["id"]: x["categorie_id"] for x in conn.execute(
                "SELECT id, categorie_id FROM rh_outil_formations").fetchall()}
    return {"elements": [
        {"id": r["id"], "libelle": r["libelle"], "nb_employes": r["nb_employes"],
         "obligatoire": bool(r["obligatoire"]), "services": exiges.get(r["id"], []),
         "categorie_id": cats.get(r["id"]), "documents": lies.get(r["id"], [])}
        for r in rows
    ]}


@router.post("/{liste}/catalogue")
def add_catalogue(liste: str, payload: LibelleIn, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        if _doublon(conn, cfg, libelle):
            raise HTTPException(409, cfg["doublon"])
        cur = conn.execute(
            f"INSERT INTO {cfg['catalogue']} (libelle, cree_le, cree_par) VALUES (?,?,?)",
            (libelle, _now(), user.get("nom")),
        )
        if cfg.get("categories") and payload.categorie_id is not None:
            _categorie(conn, payload.categorie_id)
            conn.execute("UPDATE rh_outil_formations SET categorie_id=? WHERE id=?",
                         (payload.categorie_id, cur.lastrowid))
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · {cfg['catalogue_nom']} · ajout de « {libelle} »", request=request)
    return {"success": True, "id": cur.lastrowid}


@router.put("/{liste}/catalogue/{element_id}")
def rename_catalogue(liste: str, element_id: int, payload: LibelleIn, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        row = conn.execute(f"SELECT libelle FROM {cfg['catalogue']} WHERE id=?",
                           (element_id,)).fetchone()
        if not row:
            raise HTTPException(404, cfg["introuvable"])
        if row["libelle"] == libelle:
            return {"success": True}
        if _doublon(conn, cfg, libelle, element_id):
            raise HTTPException(409, cfg["doublon"])
        conn.execute(f"UPDATE {cfg['catalogue']} SET libelle=? WHERE id=?", (libelle, element_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {cfg['catalogue_nom']} · « {row['libelle']} » → « {libelle} »",
               request=request)
    return {"success": True}


@router.delete("/{liste}/catalogue/{element_id}")
def delete_catalogue(liste: str, element_id: int, request: Request):
    """Supprime l'élément du catalogue ET de tous les employés qui l'ont."""
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        row = conn.execute(f"SELECT libelle FROM {cfg['catalogue']} WHERE id=?",
                           (element_id,)).fetchone()
        if not row:
            raise HTTPException(404, cfg["introuvable"])
        fichiers = (_retirer_pieces(conn, "a.document_id = ?", (element_id,))
                    if liste == "documents" else [])
        n = conn.execute(f"DELETE FROM {cfg['liaison']} WHERE {cfg['fk']}=?",
                         (element_id,)).rowcount
        conn.execute(f"DELETE FROM {cfg['exigences']} WHERE {cfg['fk']}=?", (element_id,))
        # Liens formation ↔ document : la colonne vaut formation_id ou document_id.
        conn.execute(f"DELETE FROM rh_outil_formation_documents WHERE {cfg['fk']}=?", (element_id,))
        conn.execute(f"DELETE FROM {cfg['catalogue']} WHERE id=?", (element_id,))
        conn.commit()
    _supprimer_fichiers(fichiers)
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {cfg['catalogue_nom']} · suppression de « {row['libelle']} » ({n} employé(s))",
               request=request)
    return {"success": True}


# ─── Listes d'un employé ──────────────────────────────────────────────────

@router.post("/membres/{membre_id}/{liste}")
def add_attribution(membre_id: int, liste: str, payload: AttributionIn, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        m = _membre(conn, membre_id)
        e = conn.execute(f"SELECT libelle FROM {cfg['catalogue']} WHERE id=?",
                         (payload.element_id,)).fetchone()
        if not e:
            raise HTTPException(404, cfg["introuvable"])
        cur = conn.execute(
            f"""INSERT OR IGNORE INTO {cfg['liaison']}
                    (membre_id, {cfg['fk']}, fait, ajoute_le) VALUES (?,?,0,?)""",
            (membre_id, payload.element_id, _now()),
        )
        if not cur.rowcount:
            raise HTTPException(409, cfg["deja"])
        docs = _documents_lies(conn, [(membre_id, payload.element_id)]) if liste == "formations" else 0
        conn.commit()
    suite = f" · {docs} document(s) lié(s) attribué(s)" if docs else ""
    log_action(user=user, action="ASSIGN", module="rh_outil",
               objet=f"Outil RH · {m['nom']} · {cfg['nom']} « {e['libelle']} » : attribution{suite}",
               request=request)
    return {"success": True, "documents_lies": docs}


def _attribution(conn, cfg: dict, attribution_id: int):
    row = conn.execute(
        f"""SELECT a.id, e.libelle, u.nom
              FROM {cfg['liaison']} a
              JOIN {cfg['catalogue']} e ON e.id = a.{cfg['fk']}
              JOIN rh_outil_membres m ON m.id = a.membre_id
              JOIN users u ON u.id = m.user_id
             WHERE a.id=?""",
        (attribution_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, cfg["introuvable"])
    return row


@router.patch("/{liste}/attributions/{attribution_id}")
def update_attribution(liste: str, attribution_id: int, payload: AttributionPatch,
                       request: Request):
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        row = _attribution(conn, cfg, attribution_id)
        conn.execute(f"UPDATE {cfg['liaison']} SET fait=? WHERE id=?",
                     (1 if payload.fait else 0, attribution_id))
        conn.commit()
    etat = cfg["fait"][0] if payload.fait else cfg["fait"][1]
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · {cfg['nom']} « {row['libelle']} » : {etat}",
               request=request)
    return {"success": True}


@router.delete("/{liste}/attributions/{attribution_id}")
def delete_attribution(liste: str, attribution_id: int, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        row = _attribution(conn, cfg, attribution_id)
        fichiers = (_retirer_pieces(conn, "a.id = ?", (attribution_id,))
                    if liste == "documents" else [])
        conn.execute(f"DELETE FROM {cfg['liaison']} WHERE id=?", (attribution_id,))
        conn.commit()
    _supprimer_fichiers(fichiers)
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · {cfg['nom']} « {row['libelle']} » : retrait",
               request=request)
    return {"success": True}


# ─── Pièces jointes des documents ─────────────────────────────────────────

def _piece(conn, piece_id: int):
    row = conn.execute(
        """SELECT p.id, p.attribution_id, p.nom, p.fichier, p.mime, e.libelle, u.nom AS employe
             FROM rh_outil_pieces p
             JOIN rh_outil_membre_documents a ON a.id = p.attribution_id
             JOIN rh_outil_documents e ON e.id = a.document_id
             JOIN rh_outil_membres m ON m.id = a.membre_id
             JOIN users u ON u.id = m.user_id
            WHERE p.id=?""",
        (piece_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Pièce jointe introuvable.")
    return row


@router.get("/documents/attributions/{attribution_id}/pieces")
def list_pieces(attribution_id: int, request: Request):
    _require(request)
    with get_db() as conn:
        _attribution(conn, LISTES["documents"], attribution_id)
        rows = conn.execute(
            """SELECT id, attribution_id, nom, mime, taille, ajoute_le, ajoute_par
                 FROM rh_outil_pieces WHERE attribution_id=? ORDER BY ajoute_le, id""",
            (attribution_id,),
        ).fetchall()
    return {"pieces": [_piece_json(r) for r in rows]}


@router.post("/documents/attributions/{attribution_id}/pieces")
async def add_piece(attribution_id: int, request: Request, fichier: UploadFile = File(...)):
    user = _require(request)
    # Lecture bornée : on ne charge jamais plus que la taille autorisée + 1 octet.
    contenu = await fichier.read(PIECE_MAX_OCTETS + 1)
    if not contenu:
        raise HTTPException(400, "Fichier vide.")
    if len(contenu) > PIECE_MAX_OCTETS:
        raise HTTPException(400, f"Fichier trop lourd — {RH_OUTIL_MAX_FILE_MB} Mo maximum.")
    detecte = _type_fichier(contenu[:16])
    if not detecte:
        raise HTTPException(400, "Format refusé — PDF, JPG, PNG, WEBP ou HEIC uniquement.")
    mime, ext = detecte
    nom = " ".join(Path(fichier.filename or "").name.split())[:PIECE_NOM_MAX] or f"piece.{ext}"
    with get_db() as conn:
        row = _attribution(conn, LISTES["documents"], attribution_id)
        dossier = PIECES_ROOT / str(attribution_id)
        dossier.mkdir(parents=True, exist_ok=True)
        # Nom sur disque généré : rien du nom fourni par le navigateur n'y entre.
        relatif = f"{attribution_id}/{uuid.uuid4().hex}.{ext}"
        (PIECES_ROOT / relatif).write_bytes(contenu)
        try:
            cur = conn.execute(
                """INSERT INTO rh_outil_pieces
                       (attribution_id, nom, fichier, mime, taille, ajoute_le, ajoute_par)
                   VALUES (?,?,?,?,?,?,?)""",
                (attribution_id, nom, relatif, mime, len(contenu), _now(), user.get("nom")),
            )
            conn.commit()
        except Exception:
            _supprimer_fichiers([relatif])
            raise
    log_action(user=user, action="UPLOAD", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · document « {row['libelle']} » : pièce jointe ajoutée",
               request=request)
    return {"success": True, "id": cur.lastrowid}


@router.get("/pieces/{piece_id}")
def get_piece(piece_id: int, request: Request, apercu: bool = False):
    """Téléchargement (par défaut) ou aperçu dans le navigateur (?apercu=1).

    Seuls des PDF et des images vérifiés au dépôt sont servis. L'aperçu est
    isolé (CSP sandbox) et nosniff : le navigateur n'exécute rien et ne
    réinterprète pas le type."""
    user = _require(request)
    with get_db() as conn:
        row = _piece(conn, piece_id)
    chemin = PIECES_ROOT / row["fichier"]
    if not chemin.is_file():
        raise HTTPException(410, "Fichier absent du serveur.")
    log_action(user=user, action="EXPORT", module="rh_outil",
               objet=f"Outil RH · {row['employe']} · document « {row['libelle']} » : pièce jointe consultée",
               request=request)
    return FileResponse(
        str(chemin), media_type=row["mime"], filename=row["nom"],
        content_disposition_type="inline" if apercu else "attachment",
        headers={"X-Content-Type-Options": "nosniff",
                 "Content-Security-Policy": "sandbox",
                 "Cache-Control": "private, no-store"},
    )


@router.delete("/pieces/{piece_id}")
def delete_piece(piece_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = _piece(conn, piece_id)
        conn.execute("DELETE FROM rh_outil_pieces WHERE id=?", (piece_id,))
        conn.commit()
    _supprimer_fichiers([row["fichier"]])
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {row['employe']} · document « {row['libelle']} » : pièce jointe supprimée",
               request=request)
    return {"success": True}
