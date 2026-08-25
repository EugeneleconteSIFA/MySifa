"""API de rattachement — relier un dossier ou un départ aux pièces de RVGI.

Le sélecteur de commandes du planning et le sélecteur de BL de MyExpé parlent
tous les deux à ces routes. Elles lisent le miroir de RVGI en lecture seule et
écrivent uniquement dans `rvgi_rattachements`, côté MySifa.

Rien ne repart vers l'ERP. Le sens d'écriture reste unique : RVGI est la
source, MySifa rattache ce qu'il fabrique et ce qu'il expédie à ce qu'il y lit.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from database import get_db
from app.services import rvgi_rattachement as ratt
from services.auth_service import require_admin

router = APIRouter(prefix="/api/rvgi", tags=["rvgi"])


# ── Modèles d'entrée ─────────────────────────────────────────────────────────

class LigneChoisie(BaseModel):
    numero: str = Field(..., max_length=40)
    ligne: Optional[int] = Field(None, ge=0, le=99999)
    qte: Optional[float] = None
    confirme: bool = False
    vu_qte: Optional[float] = None
    vu_article: Optional[str] = Field(None, max_length=120)
    vu_client: Optional[str] = Field(None, max_length=160)
    note: Optional[str] = Field(None, max_length=300)


class Rattachement(BaseModel):
    objet: str = Field(..., max_length=12)
    objet_id: int = Field(..., ge=1)
    lignes: List[LigneChoisie] = Field(default_factory=list)
    # « Je ne trouve pas ma commande » et « production sans commande » sont des
    # réponses légitimes, pas des échecs. Elles s'enregistrent explicitement.
    etat: Optional[str] = Field(None, max_length=20)


# Les valeurs autorisées sont vérifiées à la main plutôt qu'avec `pattern=` :
# la syntaxe a changé entre pydantic v1 (`regex`) et v2 (`pattern`), et une
# route qui ne se charge pas est un 500 au démarrage, pas un message clair.
ETATS_FORCABLES = ("a_rattacher", "hors_commande")


def _valeurs(champs: Any) -> Dict[str, Any]:
    """Le dict d'un modèle, que l'on soit en pydantic v1 ou v2."""
    if hasattr(champs, "model_dump"):
        return champs.model_dump()
    return champs.dict()


def _piece_de(objet: str) -> str:
    return "commande" if objet == "dossier" else "livraison"


def _existe(conn, objet: str, objet_id: int) -> None:
    table = "planning_entries" if objet == "dossier" else "expe_departs"
    row = conn.execute('SELECT id FROM "%s" WHERE id=?' % table, (objet_id,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Ce %s n'existe pas." % ("dossier" if objet == "dossier" else "départ"),
        )


# ── Recherche de pièces ──────────────────────────────────────────────────────

@router.get("/commandes")
def rvgi_commandes(
    request: Request,
    q: str = Query("", max_length=120),
    ouvertes: int = Query(1, ge=0, le=1),
    limite: int = Query(ratt.LIMITE_RECHERCHE, ge=1, le=100),
):
    """Commandes candidates pour un dossier, avec ce qui leur est déjà rattaché.

    Cherche sur le numéro, le client, la référence article et la désignation :
    c'est ce qu'un planificateur a sous les yeux quand il ouvre un dossier.
    """
    require_admin(request)
    try:
        groupes = ratt.chercher_commandes(q, limite=limite, ouvertes_seulement=bool(ouvertes))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    with get_db() as conn:
        groupes = ratt.enrichir_avec_rattachements(conn, "commande", groupes)
    return {"pieces": groupes, "miroir": _fraicheur()}


@router.get("/livraisons")
def rvgi_livraisons(
    request: Request,
    q: str = Query("", max_length=120),
    dossier_id: Optional[int] = Query(None, ge=1),
    limite: int = Query(ratt.LIMITE_RECHERCHE, ge=1, le=100),
):
    """Bons de livraison candidats pour un départ.

    `dossier_id` : le dossier expédié. RVGI porte déjà le lien entre une ligne
    de BL et sa ligne de commande, donc les BL des commandes de ce dossier
    remontent en tête — sans que l'expéditionnaire ait à les chercher.
    """
    require_admin(request)
    numeros: List[str] = []
    if dossier_id:
        with get_db() as conn:
            numeros = [r["numero"] for r in conn.execute(
                "SELECT DISTINCT numero FROM rvgi_rattachements "
                "WHERE objet='dossier' AND objet_id=? AND piece='commande'",
                (dossier_id,),
            )]
    try:
        groupes = ratt.chercher_livraisons(q, numeros_commande=numeros, limite=limite)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    with get_db() as conn:
        groupes = ratt.enrichir_avec_rattachements(conn, "livraison", groupes)
    return {"pieces": groupes, "commandes_du_dossier": numeros, "miroir": _fraicheur()}


def _fraicheur() -> Dict[str, Any]:
    """L'heure du miroir, pour que l'écran puisse dire ce qu'il ne sait pas."""
    from app.services import erp_mirror as miroir
    try:
        m = miroir.meta()
        return {"present": m["present"], "releve_le": m.get("releve_le")}
    except Exception:
        return {"present": False, "releve_le": None}


# ── Lecture et écriture d'un rattachement ────────────────────────────────────

@router.get("/rattachements/{objet}/{objet_id}")
def rvgi_lire(objet: str, objet_id: int, request: Request):
    require_admin(request)
    if objet not in ratt.OBJETS:
        raise HTTPException(status_code=400, detail="Objet inconnu.")
    with get_db() as conn:
        _existe(conn, objet, objet_id)
        lignes = ratt.lister(conn, objet, objet_id)
        table = "planning_entries" if objet == "dossier" else "expe_departs"
        row = conn.execute(
            'SELECT rvgi_etat, rvgi_maj_le FROM "%s" WHERE id=?' % table, (objet_id,)
        ).fetchone()
    return {
        "objet": objet, "objet_id": objet_id,
        "etat": (row["rvgi_etat"] if row else None),
        "maj_le": (row["rvgi_maj_le"] if row else None),
        "rattachements": lignes,
    }


@router.post("/rattachements")
def rvgi_enregistrer(corps: Rattachement, request: Request):
    """Remplace les rattachements d'un dossier ou d'un départ.

    Remplacement complet, pas fusion : l'écran envoie l'état voulu. C'est ce
    qui permet de retirer une ligne, et ce qui évite qu'un aller-retour dans
    l'interface laisse des rattachements fantômes.
    """
    user = require_admin(request)
    nom = (user.get("nom") or user.get("email") or "") if isinstance(user, dict) else ""
    if corps.objet not in ratt.OBJETS:
        raise HTTPException(status_code=400, detail="Objet inconnu.")
    if corps.etat and corps.etat not in ETATS_FORCABLES:
        raise HTTPException(status_code=400, detail="État inconnu.")
    piece = _piece_de(corps.objet)
    with get_db() as conn:
        _existe(conn, corps.objet, corps.objet_id)
        try:
            res = ratt.enregistrer(
                conn, corps.objet, corps.objet_id, piece,
                [_valeurs(l) for l in corps.lignes], nom, etat_objet=corps.etat,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
        lignes = ratt.lister(conn, corps.objet, corps.objet_id)
    return {**res, "rattachements": lignes}


@router.get("/reference")
def rvgi_reference(
    request: Request,
    numeros: str = Query("", max_length=400),
    lignes: str = Query("", max_length=800),
    dossier_id: Optional[int] = Query(None, ge=1),
):
    """La référence de dossier proposée pour une sélection.

    `numeros` : « 9932128,9932129 ». `lignes` : « 9932128:1,9932128:2 ».
    Le client n'invente pas la règle de nommage — elle vit au même endroit que
    tout le reste, et changera sans qu'on touche aux écrans.
    """
    require_admin(request)
    choix: List[Dict[str, Any]] = []
    for bout in (lignes or "").split(","):
        bout = bout.strip()
        if not bout:
            continue
        num, _, lg = bout.partition(":")
        try:
            choix.append({"numero": num.strip(), "ligne": int(lg) if lg.strip() else None})
        except ValueError:
            continue
    for num in (numeros or "").split(","):
        num = num.strip()
        if num and not any(c["numero"] == num for c in choix):
            choix.append({"numero": num, "ligne": None})
    if not choix:
        return {"reference": "", "reliquat": False}

    # Combien de lignes chaque commande porte dans RVGI : sans ça, on écrirait
    # « 9932128/L1-6 » là où « 9932128 » suffit.
    totaux: Dict[str, int] = {}
    try:
        from app.services import erp_mirror as miroir
        with miroir.get_erp_db() as c:
            if "cde_ligne" in miroir.tables_presentes(c):
                uniques = sorted({c2["numero"] for c2 in choix})
                for debut in range(0, len(uniques), 400):
                    lot = uniques[debut:debut + 400]
                    for r in c.execute(
                        "SELECT CAST(numero AS TEXT) n, COUNT(*) k FROM cde_ligne "
                        "WHERE corbeille=0 AND CAST(numero AS TEXT) IN (%s) GROUP BY n"
                        % ",".join("?" * len(lot)), lot):
                        totaux[r["n"]] = r["k"]
    except FileNotFoundError:
        pass

    with get_db() as conn:
        reliquat = ratt.deja_couvertes(
            conn, choix, "commande",
            sauf=("dossier", dossier_id) if dossier_id else None,
        )
    return {
        "reference": ratt.proposer_reference(choix, totaux, reliquat=reliquat),
        "reliquat": reliquat,
    }


# ── La liste « à rattacher » ─────────────────────────────────────────────────

@router.get("/a-rattacher")
def rvgi_a_rattacher(
    request: Request,
    objet: str = Query("dossier", max_length=12),
    limite: int = Query(200, ge=1, le=1000),
):
    """Ce qui attend un arbitrage humain.

    Un dossier sans commande, ou dont le numéro n'a jamais été retrouvé dans
    le miroir. Sans cette liste, « je ne trouve pas » deviendrait la réponse
    par défaut et le rattachement ne servirait à rien.
    """
    require_admin(request)
    if objet not in ratt.OBJETS:
        raise HTTPException(status_code=400, detail="Objet inconnu.")
    table, ref = (("planning_entries", "reference") if objet == "dossier"
                  else ("expe_departs", "no_bl"))
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, "%s" AS ref, rvgi_etat, rvgi_maj_le, created_at '
            'FROM "%s" WHERE COALESCE(rvgi_etat, \'a_rattacher\') IN '
            "('a_rattacher','a_verifier') ORDER BY COALESCE(created_at,'') DESC LIMIT ?"
            % (ref, table), (limite,),
        ).fetchall()
    return {"objet": objet, "total": len(rows), "lignes": [dict(r) for r in rows]}


@router.post("/reprendre")
def rvgi_reprendre(request: Request):
    """Confirme les rattachements « à vérifier » que le miroir connaît enfin.

    Appelée après chaque import du miroir. Peut aussi se déclencher à la main
    depuis la liste « à rattacher », quand on vient de synchroniser.
    """
    require_admin(request)
    with get_db() as conn:
        res = ratt.reprendre_apres_synchro(conn)
        conn.commit()
    return res
