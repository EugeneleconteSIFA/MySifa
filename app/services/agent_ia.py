"""
MySifa — agent IA du widget (présent sur tout le site).

Lecture : les mêmes outils que le connecteur MCP (`app/routers/mcp_server.py`),
appelés directement en Python — base MySifa en lecture seule, miroir RVGI,
chiffres de prod calculés par le code des écrans. Les garde-fous du MCP
s'appliquent tels quels (connexion `mode=ro`, SELECT seul, tables RH / paie /
messagerie et colonnes sensibles refusées).

Écriture : l'agent n'écrit jamais. Il appelle `proposer_action`, qui vérifie
la demande contre le catalogue fermé de `agent_actions.py` et l'enregistre
dans `ai_actions`. L'utilisateur voit une carte et confirme ; c'est alors
l'écran existant qui exécute, avec ses propres droits et son journal.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from config import (
    AGENT_IA_MAX_TOURS, AGENT_IA_MODELE, ROLES_AGENT_RVGI, agent_ia_modeles,
)
from app.services import agent_actions as aa
from app.services import ia_usage

PARIS = ZoneInfo("Europe/Paris")
MAX_TOKENS = 8000
MAX_RESULTAT = 30000   # caractères renvoyés au modèle par appel d'outil


class ErreurAgent(Exception):
    """Message factuel, affiché tel quel."""


def choisir_modele(modele: Optional[str]) -> dict:
    liste = agent_ia_modeles()
    par_id = {m["id"]: m for m in liste}
    if not modele:
        return par_id.get(AGENT_IA_MODELE) or liste[0]
    if modele not in par_id:
        raise ErreurAgent(f"Modèle « {modele} » non proposé.")
    return par_id[modele]


# ── Outils ──────────────────────────────────────────────────────────────

def _bases_autorisees(role: str) -> list[str]:
    from app.services import mcp_data
    bases = list(mcp_data.BASES.keys())
    if role not in ROLES_AGENT_RVGI and role != "superadmin":
        bases = [b for b in bases if b != "rvgi"]
    return bases


def outils_pour(user: dict) -> list[dict]:
    """Outils MCP (schémas repris tels quels) + proposer_action."""
    from app.routers.mcp_server import OUTILS
    bases = _bases_autorisees(user.get("role", ""))
    out = []
    for o in OUTILS:
        schema = json.loads(json.dumps(o["inputSchema"]))
        base = schema.get("properties", {}).get("base")
        if base and "enum" in base:
            base["enum"] = bases
        out.append({"name": o["name"], "description": o["description"], "input_schema": schema})
    out.append({
        "name": "lire_ecran",
        "description": (
            "Lit un écran MySifa tel que l'utilisateur le voit, avec ses droits. À PRÉFÉRER au SQL dès "
            "qu'on demande ce qu'un écran affiche : stock d'un emplacement ou d'un produit, stock "
            "matière, file du planning, saisies. Le stock n'est jamais la somme des mouvements ni des "
            "lots : c'est ce que calcule l'écran.\n\nÉcrans :\n" + aa.description_lectures()),
        "input_schema": {
            "type": "object",
            "properties": {
                "ecran": {"type": "string", "enum": [l["cle"] for l in aa.LECTURES]},
                "parametres": {"type": "object"},
            },
            "required": ["ecran"],
        },
    })
    actions = aa.catalogue_pour(user)
    if actions:
        out.append({
            "name": "proposer_action",
            "description": (
                "Propose une écriture dans MySifa. RIEN n'est écrit : l'utilisateur voit une "
                "carte récapitulative et doit cliquer « Confirmer ». Une action par appel ; "
                "plusieurs appels possibles dans une réponse. Résous d'abord les identifiants "
                "(machine, emplacement, article, saisie…) avec les outils de lecture : n'invente "
                "jamais un id.\n\nActions disponibles :\n" + aa.description_catalogue(actions)
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": [a["cle"] for a in actions]},
                    "parametres": {"type": "object", "description": "Paramètres de l'action, voir la liste."},
                    "resume": {"type": "string", "description": "Une phrase en français : ce qui sera fait, sur quoi."},
                },
                "required": ["action", "parametres", "resume"],
            },
        })
    return out


def _texte(valeur: Any) -> str:
    t = json.dumps(valeur, ensure_ascii=False, default=str)
    if len(t) > MAX_RESULTAT:
        t = t[:MAX_RESULTAT] + "… [tronqué : affiner la requête]"
    return t


def _sync(fn, *args):
    """Lance une coroutine depuis le fil de travail de la requête (route
    synchrone sous anyio), ou depuis un script / test sans boucle."""
    import anyio
    try:
        return anyio.from_thread.run(fn, *args)
    except RuntimeError:
        import asyncio
        return asyncio.run(fn(*args))


def lire_ecran(contexte: Optional[dict], args: dict) -> str:
    if not contexte or not contexte.get("app"):
        return _texte({"erreur": "Lecture d'écran indisponible dans ce contexte."})
    try:
        data = _sync(aa.lire, contexte["app"], contexte.get("cookies") or {},
                     args.get("ecran", ""), args.get("parametres") or {})
        return _texte(data)
    except aa.ActionInvalide as e:
        return _texte({"erreur": str(e)})
    except Exception as e:
        return _texte({"erreur": f"{type(e).__name__} : {e}"})


def executer_lecture(user: dict, nom: str, args: dict) -> str:
    from app.routers.mcp_server import _executer_outil
    from app.services.mcp_data import ErreurMCP
    base = (args or {}).get("base")
    if base and base not in _bases_autorisees(user.get("role", "")):
        return _texte({"erreur": f"Base « {base} » non accessible pour ce rôle."})
    try:
        return _texte(_executer_outil(nom, args or {}))
    except ErreurMCP as e:
        return _texte({"erreur": str(e)})
    except Exception as e:  # une erreur d'outil ne casse pas la conversation
        return _texte({"erreur": f"{type(e).__name__} : {e}"})


# ── Actions proposées ───────────────────────────────────────────────────

def enregistrer_proposition(conn, user: dict, args: dict, modele: str) -> dict:
    """Valide contre le catalogue et enregistre. Lève aa.ActionInvalide."""
    prep = aa.preparer(user, args.get("action", ""), args.get("parametres") or {})
    jeton = secrets.token_urlsafe(16)
    resume = str(args.get("resume") or prep["libelle"])[:400]
    now = datetime.now(PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        "INSERT INTO ai_actions (jeton,user_email,cle,libelle,resume,methode,chemin,corps_json,details_json,"
        "statut,modele,created_at) VALUES (?,?,?,?,?,?,?,?,?,'proposee',?,?)",
        (jeton, user.get("email") or "", prep["cle"], prep["libelle"], resume, prep["methode"],
         prep["chemin"], json.dumps(prep["corps"], ensure_ascii=False),
         json.dumps(prep["details"], ensure_ascii=False), modele, now))
    conn.commit()
    return {"jeton": jeton, "cle": prep["cle"], "libelle": prep["libelle"], "resume": resume,
            "details": prep["details"], "module": prep.get("module", "")}


# ── Prompt ──────────────────────────────────────────────────────────────

_REGLES = """Tu es l'agent intégré de MySifa, l'outil de gestion de production de SIFA (fabricant d'étiquettes).
Tu réponds en français, de façon directe et factuelle, sans formule commerciale ni emoji.

Ce qu'un écran affiche se lit avec `lire_ecran` (stock d'un emplacement, d'un produit, d'une
matière ; file du planning ; saisies) : c'est le chiffre que l'utilisateur voit. N'en reconstitue
jamais un en SQL à partir des mouvements ou des lots, et ne liste pas les lignes à zéro.

Lecture transversale : tu disposes des outils du connecteur MySifa (bases `mysifa` et `rvgi`). Applique
strictement les règles de lecture ci-dessous. Ne devine jamais un nom de colonne : consulte
`mysifa_schema` (avec un `filtre`) avant d'écrire du SQL. Un chiffre de temps ou de métrage
vient de `mysifa_metric`, jamais d'un calcul SQL. Un identifiant donné par l'utilisateur passe
par `mysifa_resolve`.

Écriture : tu n'écris jamais directement. Pour créer ou modifier quelque chose, appelle
`proposer_action` — l'utilisateur confirme sur une carte. Avant de proposer :
- résous chaque identifiant avec les outils de lecture (machine, emplacement, article,
  saisie, tâche, réunion) ; s'il reste une ambiguïté, pose une question courte ;
- vérifie la valeur actuelle quand tu modifies (prix, quantité, saisie) et cite-la ;
- n'annonce jamais une action comme faite : dis qu'elle attend la confirmation.
Si l'utilisateur demande une écriture absente du catalogue, dis-le simplement.

Forme — court avant tout :
- Commence directement par la réponse, en une phrase. Pas d'introduction, pas de reformulation
  de la question, pas de récit de ce que tu as consulté, pas de conclusion qui répète.
- Ensuite 5 lignes au plus, ou un tableau de 8 lignes au plus avec 3 ou 4 colonnes courtes. S'il
  y a davantage, donne les plus importantes et le nombre restant (« et 6 autres »), puis propose
  le détail en une ligne.
- Chiffres arrondis à ce qui sert (« 1,2 million », « 18 h ») ; montants en euros HT, dates en JJ/MM.
- Mets en **gras** les références dossier et le mot qui porte le problème (« **sans info prod** »),
  jamais une phrase entière. Un titre `### ` seulement pour séparer deux sujets distincts. Une ligne
  commençant par `> ` pour l'action à faire, s'il y en a une.

Vocabulaire — celui de l'atelier et du bureau, jamais celui de la base :
- Aucun nom de table, de colonne, d'outil ou de code technique (pas de « planning_entries »,
  « production_data », « fin_dossier », « corbeille », « miroir », « mysifa_sql », « id 4512 »).
- Dis « dossier », « saisie », « OF », « fiche technique », « BL », « départ », « sortie de stock »,
  « emplacement », « machine ». Les statuts : « En attente », « En cours », « Terminé »,
  « Dossier clôturé » ; les opérations : « Début de production », « Fin de production ».
- Pas d'anglicisme ni de sigle que l'atelier n'emploie pas. Phrases courtes, sujet-verbe-complément.
Ne colle jamais de SQL dans la réponse sauf si on te le demande. Si une donnée n'existe pas,
dis-le — n'invente rien."""


def prompt_systeme(user: dict, page: Optional[dict]) -> list[dict]:
    """Deux blocs : le stable (mis en cache) puis le contexte de la requête."""
    from app.routers.mcp_server import INSTRUCTIONS
    try:
        from app.services.ai_context import _load_sifa_context
        contexte_sifa = _load_sifa_context()
    except Exception:
        contexte_sifa = ""
    stable = f"{_REGLES}\n\n--- Règles du connecteur ---\n{INSTRUCTIONS}\n\n--- SIFA ---\n{contexte_sifa}"
    maintenant = datetime.now(PARIS)
    page = page or {}
    variable = (
        f"Utilisateur : {user.get('nom') or user.get('email')} — rôle : {user.get('role')}\n"
        f"Date et heure (Paris) : {maintenant.strftime('%A %d/%m/%Y %H:%M')}\n"
        f"Page ouverte : {str(page.get('titre') or '')[:120]} — {str(page.get('url') or '')[:200]}\n"
        f"Bases lisibles : {', '.join(_bases_autorisees(user.get('role', '')))}"
    )
    from app.services.agent_actions_erp import consigne_page
    variable += consigne_page(page)
    return [
        {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": variable},
    ]


# ── Boucle ──────────────────────────────────────────────────────────────

def _client():
    import os
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=cle)


def converser(conn, user: dict, historique: list[dict], page: Optional[dict] = None,
              modele: Optional[str] = None, contexte: Optional[dict] = None) -> dict:
    """`contexte` : {app, cookies} de la requête, pour lire_ecran."""
    """Rend {reponse, actions, outils, modele}. `historique` : [{role, content(str)}]."""
    client = _client()
    if client is None:
        raise ErreurAgent("Agent indisponible — clé ANTHROPIC_API_KEY absente du serveur.")
    choix = choisir_modele(modele)
    outils = outils_pour(user)
    systeme = prompt_systeme(user, page)
    messages: list[dict] = [{"role": m["role"], "content": m["content"]} for m in historique]
    options: dict[str, Any] = {"extra_body": {"output_config": {"effort": "medium"}}}
    if choix.get("repli"):
        options["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
        options["extra_body"]["fallbacks"] = "default"

    actions: list[dict] = []
    utilises: list[str] = []
    texte = ""
    for _ in range(AGENT_IA_MAX_TOURS):
        try:
            rep = client.messages.create(
                model=choix["id"], max_tokens=MAX_TOKENS, system=systeme,
                tools=outils, messages=messages, **options)
        except Exception as e:
            raise ErreurAgent(f"Appel au modèle en échec : {e}")
        ia_usage.noter(rep, "agent")
        texte = "".join(b.text for b in rep.content if getattr(b, "type", "") == "text")
        if rep.stop_reason == "refusal":
            texte = texte or "Je ne peux pas traiter cette demande."
            break
        if rep.stop_reason != "tool_use":
            if rep.stop_reason == "max_tokens":
                texte += "\n\n[Réponse coupée : demande trop large, la préciser.]"
            break
        # Le contenu complet (réflexion comprise) repart tel quel au tour suivant.
        messages.append({"role": "assistant", "content": rep.content})
        resultats = []
        for b in rep.content:
            if getattr(b, "type", "") != "tool_use":
                continue
            utilises.append(b.name)
            args = b.input if isinstance(b.input, dict) else {}
            if b.name == "proposer_action":
                try:
                    act = enregistrer_proposition(conn, user, args, choix["id"])
                    actions.append(act)
                    contenu = (f"Action enregistrée, en attente de confirmation par l'utilisateur "
                               f"(carte affichée). Elle N'EST PAS faite. Détails : {_texte(act['details'])}")
                    erreur = False
                except aa.ActionInvalide as e:
                    contenu, erreur = f"Action refusée : {e}", True
            elif b.name == "lire_ecran":
                contenu, erreur = lire_ecran(contexte, args), False
            else:
                contenu, erreur = executer_lecture(user, b.name, args), False
            resultats.append({"type": "tool_result", "tool_use_id": b.id, "content": contenu,
                              **({"is_error": True} if erreur else {})})
        messages.append({"role": "user", "content": resultats})
    else:
        texte = (texte + "\n\n" if texte else "") + "[Arrêt : trop d'étapes pour une seule demande. Préciser la question.]"

    return {"reponse": texte.strip() or ("Action proposée — à confirmer ci-dessous." if actions else "Pas de réponse."),
            "actions": actions, "outils": utilises, "modele": choix["id"]}
