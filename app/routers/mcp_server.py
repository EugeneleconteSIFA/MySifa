"""Serveur MCP MySifa — expose les données de MySifa et du miroir RVGI à Claude.

Transport : Streamable HTTP, forme la plus simple du protocole — un POST
JSON-RPC 2.0 sur `/mcp`, une réponse JSON. Pas de flux SSE, pas de session :
chaque appel se suffit à lui-même, ce qui évite tout état partagé côté serveur
et survit à un redémarrage de l'app.

Authentification : clé API existante (table `api_keys`), portée `mcp:read`,
envoyée en `X-Api-Key` ou `Authorization: Bearer <clé>`.

Lecture seule de bout en bout : les connexions SQLite sont ouvertes en `mode=ro`
(cf. `app/services/mcp_data.py`), aucun outil n'écrit quoi que ce soit.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from config import APP_VERSION
from app.core.database import get_db
from app.services.audit_service import log_action
from app.services import mcp_data

router = APIRouter(tags=["mcp"])
logger = logging.getLogger("mysifa.mcp")

SCOPE_MCP = "mcp:read"
VERSIONS_SUPPORTEES = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
VERSION_DEFAUT = "2025-06-18"

# ── Instructions du serveur ──────────────────────────────────────────────────
# Envoyées au client à l'`initialize`. Elles portent les règles de lecture qui
# ont coûté le plus cher à établir : sans elles, un agent refait les mêmes
# erreurs d'interprétation sur RVGI à chaque session.

INSTRUCTIONS = """Accès en lecture seule aux données de production de MySifa (SIFA, fabricant d'étiquettes).

Deux bases :
- `mysifa` : la base applicative — dossiers de production, saisies opérateurs, arrêts,
  planning machine, stock et matières, expéditions, qualité, maintenance.
- `rvgi` : miroir en lecture seule de l'ERP RVGI — commandes, factures, livraisons,
  articles, tiers. Le sens d'écriture est unique : RVGI est la source, MySifa lit.

Méthode : commence par `mysifa_schema` sur la base et le sujet visés, puis écris
le SQL. Ne devine jamais un nom de colonne — la structure est irrégulière,
surtout côté RVGI.

Règles de lecture RVGI, établies à l'usage et non négociables :
- Ne prendre que les lignes `corbeille = 0` : RVGI ne supprime pas, il marque.
- Le montant d'une ligne se LIT dans sa colonne de total HT (`htn`), il ne se
  reconstruit pas. `net` vaut 1,00 partout (drapeau, pas montant). `pun` ne se
  rapporte pas à la même unité d'une table à l'autre.
- Sur un écran de lignes de document, la jointure vers l'entête est OBLIGATOIRE
  (INNER JOIN) : l'export filtre table par table, donc une pièce mise à la
  corbeille laisse ses lignes orphelines dans le miroir.
- Les dates portent une heure (« 2026-08-26 09:12 ») : tout regroupement ou toute
  comparaison par jour doit tronquer à 10 caractères (`substr(date,1,10)`).
- `code1`, `code2`, `code3` sont stockées en TEXTE dans toutes les tables :
  `code1 > 0` est toujours vrai en SQLite. Tester sur la chaîne.
- Ordre de grandeur de contrôle : le chiffre d'affaires annuel de SIFA se situe
  entre 2 et 20 M€. Un total hors de cette plage est un bug de calcul, pas une
  découverte.

Règle de lecture MySifa :
- La saisie des opérateurs est le repère numéro 1. Tout chiffre de temps ou de
  quantité de production doit s'y aligner ; deux écrans ne donnent jamais deux
  chiffres pour le même dossier.

Hors périmètre, et les outils le refuseront : messagerie interne, calendrier
personnel, RH et paie, mots de passe, jetons et clés. Ce n'est pas un oubli."""


# ── Authentification ─────────────────────────────────────────────────────────

def _cle_brute(request: Request) -> Optional[str]:
    cle = request.headers.get("x-api-key")
    if cle:
        return cle.strip()
    autorisation = request.headers.get("authorization") or ""
    if autorisation.lower().startswith("bearer "):
        return autorisation[7:].strip()
    return None


def _verifier_cle(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Renvoie (motif de refus, nom de la clé). Le motif est None si l'accès passe."""
    brute = _cle_brute(request)
    if not brute:
        return "Clé API manquante (en-tête X-Api-Key ou Authorization: Bearer).", None
    empreinte = hashlib.sha256(brute.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, scopes, is_active FROM api_keys WHERE key_hash=? LIMIT 1",
            (empreinte,),
        ).fetchone()
        if not row or not row["is_active"]:
            return "Clé API invalide ou révoquée.", None
        portees = [s.strip() for s in (row["scopes"] or "").split(",")]
        if SCOPE_MCP not in portees:
            return f"Cette clé n'a pas la portée « {SCOPE_MCP} ».", None
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row["id"]),
            )
            conn.commit()
        except Exception:
            pass
        nom_cle = row["name"]
    return None, nom_cle


# ── Catalogue d'outils ───────────────────────────────────────────────────────

_BASES = list(mcp_data.BASES.keys())

OUTILS: list[dict[str, Any]] = [
    {
        "name": "mysifa_bases",
        "title": "Bases disponibles",
        "description": "Liste les bases interrogeables (mysifa, rvgi) avec leur taille, "
                       "leur nombre de tables et ce qu'elles contiennent. À appeler en "
                       "premier si tu ne sais pas encore où chercher.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "mysifa_schema",
        "title": "Schéma des tables",
        "description": "Tables d'une base avec leur nombre de lignes et leurs colonnes. "
                       "Utilise `filtre` pour ne ramener que les tables dont le nom "
                       "contient un mot (« dossier », « stock », « expe », « vte »…) : "
                       "sans filtre, la réponse est très longue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string", "enum": _BASES, "description": "Base à inspecter."},
                "filtre": {"type": "string", "description": "Sous-chaîne du nom de table."},
                "avec_colonnes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Mettre à false pour n'obtenir que la liste des tables.",
                },
            },
            "required": ["base"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mysifa_sql",
        "title": "Requête SQL (lecture seule)",
        "description": "Exécute une requête SELECT (ou WITH … SELECT) sur une base. "
                       "SQLite. Une seule requête, sans point-virgule. Le résultat est "
                       "borné : au-delà de la limite, la réponse indique `tronque: true` "
                       "— affine le filtre plutôt que de remonter la limite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string", "enum": _BASES},
                "sql": {"type": "string", "description": "Requête SELECT SQLite."},
                "limite": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": mcp_data.LIMITE_MAX,
                    "default": mcp_data.LIMITE_DEFAUT,
                },
            },
            "required": ["base", "sql"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mysifa_apercu_table",
        "title": "Aperçu d'une table",
        "description": "Premières lignes d'une table, pour voir à quoi ressemblent "
                       "réellement les valeurs avant d'écrire une requête.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string", "enum": _BASES},
                "table": {"type": "string"},
                "limite": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
            "required": ["base", "table"],
            "additionalProperties": False,
        },
    },
]


def _executer_outil(nom: str, args: dict[str, Any]) -> Any:
    if nom == "mysifa_bases":
        return {"bases": mcp_data.inventaire_bases()}
    if nom == "mysifa_schema":
        return mcp_data.schema(
            args.get("base", ""),
            args.get("filtre"),
            bool(args.get("avec_colonnes", True)),
        )
    if nom == "mysifa_sql":
        return mcp_data.executer_select(
            args.get("base", ""),
            args.get("sql", ""),
            int(args.get("limite") or mcp_data.LIMITE_DEFAUT),
        )
    if nom == "mysifa_apercu_table":
        return mcp_data.apercu_table(
            args.get("base", ""),
            args.get("table", ""),
            int(args.get("limite") or 20),
        )
    raise mcp_data.ErreurMCP(f"Outil inconnu : « {nom} ».")


# ── JSON-RPC ─────────────────────────────────────────────────────────────────

# PowerShell 5.1 (et quelques autres clients) decodent en Latin-1 quand le
# charset n'est pas annonce : les accents partent en charabia. On l'annonce.
JSON_UTF8 = "application/json; charset=utf-8"


def _json(contenu: Any, status_code: int = 200, headers: Optional[dict] = None) -> JSONResponse:
    return JSONResponse(contenu, status_code=status_code, headers=headers, media_type=JSON_UTF8)


def _resultat(rid: Any, valeur: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "result": valeur}


def _erreur(rid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def _texte(valeur: Any) -> dict[str, Any]:
    return {
        "content": [
            {"type": "text", "text": json.dumps(valeur, ensure_ascii=False, indent=1, default=str)}
        ],
        "isError": False,
    }


def _journaliser(nom_cle: Optional[str], outil: str, args: dict[str, Any],
                 echec: bool, request: Any = None) -> None:
    """Trace un appel d'outil dans le journal des actions.

    Le transport lui-meme est dans SKIP_PREFIXES : sans cet appel, une lecture
    de la base de production par un agent externe ne laisserait aucune trace.
    On ecrit ce qui a du sens — quel outil, sur quelle base, quelle requete —
    et rien du resultat.
    """
    detail: dict[str, Any] = {"outil": outil}
    for cle in ("base", "table", "filtre", "limite"):
        if args.get(cle) is not None:
            detail[cle] = args[cle]
    sql = args.get("sql")
    if sql:
        detail["sql"] = str(sql)[:1000]
    if echec:
        detail["echec"] = True
    log_action(
        user={"nom": f"Clé MCP · {nom_cle or 'inconnue'}", "role": "mcp"},
        action="SEARCH",
        module="mcp",
        objet=f"{outil} · {args.get('base') or '—'}",
        detail=detail,
        request=request,
    )


def _traiter(message: dict[str, Any], nom_cle: Optional[str] = None,
             request: Any = None) -> Optional[dict[str, Any]]:
    """Traite un message JSON-RPC. Renvoie None pour une notification."""
    methode = message.get("method") or ""
    rid = message.get("id")
    params = message.get("params") or {}
    notification = "id" not in message

    if methode == "initialize":
        demandee = (params.get("protocolVersion") or "").strip()
        version = demandee if demandee in VERSIONS_SUPPORTEES else VERSION_DEFAUT
        return _resultat(rid, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "mysifa", "title": "MySifa", "version": str(APP_VERSION)},
            "instructions": INSTRUCTIONS,
        })

    if methode.startswith("notifications/"):
        return None

    if methode == "ping":
        return _resultat(rid, {})

    if methode == "tools/list":
        return _resultat(rid, {"tools": OUTILS})

    if methode == "tools/call":
        nom = params.get("name") or ""
        args = params.get("arguments") or {}
        try:
            valeur = _executer_outil(nom, args)
        except mcp_data.ErreurMCP as e:
            # Erreur métier : elle remonte comme resultat d'outil en erreur, pas
            # comme erreur de protocole — le modele doit pouvoir la lire et corriger.
            _journaliser(nom_cle, nom, args, True, request)
            return _resultat(rid, {
                "content": [{"type": "text", "text": str(e)}],
                "isError": True,
            })
        except Exception:
            logger.exception("MCP — echec de l'outil %s", nom)
            _journaliser(nom_cle, nom, args, True, request)
            return _resultat(rid, {
                "content": [{"type": "text", "text": "Erreur interne pendant l'exécution de l'outil."}],
                "isError": True,
            })
        _journaliser(nom_cle, nom, args, False, request)
        return _resultat(rid, _texte(valeur))

    if notification:
        return None
    return _erreur(rid, -32601, f"Méthode inconnue : {methode}")


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/mcp")
async def mcp_endpoint(request: Request):
    refus, nom_cle = _verifier_cle(request)
    if refus:
        return _json({"error": refus}, 401)

    try:
        corps = await request.json()
    except Exception:
        return _json(_erreur(None, -32700, "JSON invalide."), 400)

    if isinstance(corps, list):
        reponses = [
            r for r in (_traiter(m, nom_cle, request) for m in corps if isinstance(m, dict)) if r
        ]
        if not reponses:
            return Response(status_code=202)
        return _json(reponses)

    if not isinstance(corps, dict):
        return _json(_erreur(None, -32600, "Requête JSON-RPC invalide."), 400)

    reponse = _traiter(corps, nom_cle, request)
    if reponse is None:
        return Response(status_code=202)
    return _json(reponse)


@router.get("/mcp")
async def mcp_sse_non_supporte():
    """Le serveur ne tient pas de flux SSE : chaque échange est un POST autonome."""
    return _json(
        {"error": "Ce serveur MCP ne gère que le POST (Streamable HTTP sans flux SSE)."},
        405,
        {"Allow": "POST, DELETE"},
    )


@router.delete("/mcp")
async def mcp_fin_session():
    """Pas de session à fermer : le serveur est sans état."""
    return Response(status_code=204)
