"""Accès aux données exposées par le serveur MCP — lecture seule et filtrée.

Deux bases sont exposées :

    mysifa → DB_PATH        base applicative MySifa
    rvgi   → ERP_MIRROR_DB  miroir en lecture seule de l'ERP RVGI

Rien ne peut être écrit : les connexions sont ouvertes en `mode=ro`, donc c'est
SQLite lui-même qui refuse l'écriture — pas seulement le validateur de requête.
Le validateur reste en place pour rendre l'erreur lisible et pour bloquer ce que
`mode=ro` autorise pourtant (lecture d'une table de secrets, ATTACH d'un autre
fichier, requête cartésienne sans fin).

Trois filtres se cumulent :
  1. tables interdites   — messagerie, RH/paie, calendrier personnel, secrets
  2. colonnes interdites — un mot de passe ne se lit ni ne se filtre
  3. bornes d'exécution  — LIMIT forcé et garde-temps sur la requête
"""
from __future__ import annotations

import contextlib
import os
import re
import sqlite3
import time
from typing import Any, Optional

from config import DB_PATH, ERP_MIRROR_DB

# ── Bases ────────────────────────────────────────────────────────────────────

BASES: dict[str, dict[str, str]] = {
    "mysifa": {
        "chemin": DB_PATH,
        "description": "Base applicative MySifa : production, saisies opérateurs, "
                       "stock et matières, expéditions, planning, qualité, maintenance.",
    },
    "rvgi": {
        "chemin": ERP_MIRROR_DB,
        "description": "Miroir en lecture seule de l'ERP RVGI : commandes, factures, "
                       "livraisons, articles, tiers, stock ERP. Rafraîchi par export CSV.",
    },
}

# ── Tables interdites ────────────────────────────────────────────────────────
# Messagerie interne, données personnelles des utilisateurs, RH/paie, secrets.
# Une table absente de ces listes est lisible : la liste noire est volontairement
# nominative pour qu'ajouter une table métier ne demande aucune modification ici.

_INTERDIT_EXACT: dict[str, set[str]] = {
    "mysifa": {
        # messagerie et discussions
        "messages", "ao_messages", "nc_messages", "nc_message_reads",
        "audit_messages", "audit_message_reads", "repiquage_discussion",
        # secrets et sessions
        "sessions", "api_keys", "push_subscriptions",
        # RH / paie / personnel
        "notes_de_frais", "documents_rh", "documents_rh_access_log",
        "formation_quiz",
        # notes personnelles
        "postits", "postit_tasks",
    },
    "rvgi": {
        "gen_sala",   # salariés
    },
}

_INTERDIT_PREFIXE: dict[str, tuple[str, ...]] = {
    "mysifa": (
        "chat_",        # messagerie temps réel
        "cal_",         # calendrier personnel, délégations, jetons de flux
        "paie_",        # paie
        "rh_conges",    # congés et soldes
        "user_video",   # progression individuelle
        "user_guide",
    ),
    "rvgi": (),
}

# ── Colonnes interdites ──────────────────────────────────────────────────────
# Ni lisibles, ni utilisables dans un WHERE (sinon un filtre devient un oracle).
# L'e-mail n'y figure pas : c'est l'identifiant fonctionnel d'un utilisateur dans
# tout MySifa (created_by, audit_logs, saisies), le masquer casserait la lecture
# sans rien protéger — il apparaît en clair partout ailleurs.

_COLONNES_INTERDITES = re.compile(
    r"(password|passwd|mot_de_passe|\bmdp\b|\bpwd\b|key_hash|password_hash|"
    r"\bsalt\b|\botp\b|totp|secret|\btoken\b|api_key|refresh_|"
    r"\biban\b|\bbic\b|num_secu|\bnir\b|salaire|date_naissance)",
    re.IGNORECASE,
)

_MASQUE = "«masqué»"

# ── SQL interdit ─────────────────────────────────────────────────────────────

_SQL_INTERDIT = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|"
    r"PRAGMA|VACUUM|REINDEX|TRIGGER|GRANT|REVOKE|LOAD_EXTENSION)\b",
    re.IGNORECASE,
)

LIMITE_DEFAUT = 200
LIMITE_MAX = 1000
DUREE_MAX_S = 20.0


class ErreurMCP(Exception):
    """Erreur fonctionnelle destinée à être renvoyée telle quelle au client MCP."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def chemin_base(base: str) -> str:
    b = (base or "").strip().lower()
    if b not in BASES:
        raise ErreurMCP(
            f"Base inconnue : « {base} ». Bases disponibles : {', '.join(BASES)}."
        )
    chemin = BASES[b]["chemin"]
    if not os.path.exists(chemin):
        raise ErreurMCP(f"Le fichier de la base « {b} » est introuvable sur ce serveur.")
    return chemin


def table_interdite(base: str, nom: str) -> bool:
    b = (base or "").strip().lower()
    n = (nom or "").strip().lower()
    if n.startswith("sqlite_"):
        return True
    if n in _INTERDIT_EXACT.get(b, set()):
        return True
    return any(n.startswith(p) for p in _INTERDIT_PREFIXE.get(b, ()))


@contextlib.contextmanager
def _connexion(base: str):
    """Connexion en lecture seule, systematiquement refermee.

    `with sqlite3.connect(...)` ne ferme pas la connexion — c'est un
    context manager de transaction. Sur un serveur qui vit des mois, l'oublier
    fuit un descripteur par requete.
    """
    chemin = chemin_base(base)
    uri = "file:" + chemin.replace("?", "%3f").replace("#", "%23") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _garde_temps(conn: sqlite3.Connection, duree_max: float) -> None:
    """Interrompt une requête qui dépasse le temps imparti (jointure cartésienne)."""
    fin = time.monotonic() + duree_max

    def _tick() -> int:
        return 1 if time.monotonic() > fin else 0

    conn.set_progress_handler(_tick, 20000)


def _valeur_json(v: Any) -> Any:
    if isinstance(v, (bytes, bytearray, memoryview)):
        return f"<binaire {len(bytes(v))} octets>"
    return v


# ── Inventaire ───────────────────────────────────────────────────────────────

def inventaire_bases() -> list[dict[str, Any]]:
    out = []
    for nom, meta in BASES.items():
        present = os.path.exists(meta["chemin"])
        entree: dict[str, Any] = {
            "base": nom,
            "description": meta["description"],
            "disponible": present,
        }
        if present:
            entree["taille_mo"] = round(os.path.getsize(meta["chemin"]) / 1_048_576, 1)
            try:
                with _connexion(nom) as conn:
                    entree["nb_tables"] = len(_noms_tables(conn, nom))
            except Exception:
                entree["nb_tables"] = None
        out.append(entree)
    return out


def _noms_tables(conn: sqlite3.Connection, base: str) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows if not table_interdite(base, r[0])]


def schema(base: str, filtre: Optional[str] = None, avec_colonnes: bool = True) -> dict[str, Any]:
    f = (filtre or "").strip().lower()
    with _connexion(base) as conn:
        noms = [n for n in _noms_tables(conn, base) if not f or f in n.lower()]
        tables = []
        for nom in noms:
            entree: dict[str, Any] = {"table": nom}
            try:
                entree["lignes"] = conn.execute(f'SELECT COUNT(*) FROM "{nom}"').fetchone()[0]
            except Exception:
                entree["lignes"] = None
            if avec_colonnes:
                cols = []
                for c in conn.execute(f'PRAGMA table_info("{nom}")').fetchall():
                    col = c[1]
                    if _COLONNES_INTERDITES.search(col):
                        cols.append(f"{col} (masquée)")
                        continue
                    marques = []
                    if c[5]:
                        marques.append("PK")
                    if c[3]:
                        marques.append("NOT NULL")
                    cols.append(
                        f"{col} {(c[2] or 'TEXT').upper()}"
                        + (f" [{','.join(marques)}]" if marques else "")
                    )
                entree["colonnes"] = cols
            tables.append(entree)
    return {
        "base": base,
        "filtre": filtre or None,
        "nb_tables": len(tables),
        "tables": tables,
    }


# ── Requête ──────────────────────────────────────────────────────────────────

def _tables_interdites_presentes(base: str) -> set[str]:
    """Noms interdits reellement presents dans la base, en minuscules.

    Comparer le texte de la requete a la liste de prefixes produirait des faux
    positifs (une colonne `chat_id` n'est pas la table `chat_messages`).
    """
    with _connexion(base) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall()
    return {r[0].lower() for r in rows if table_interdite(base, r[0])}


def _valider(base: str, sql: str, noms_interdits: Optional[set[str]] = None) -> str:
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise ErreurMCP("Requête SQL vide.")
    if ";" in s:
        raise ErreurMCP("Une seule requête à la fois : le point-virgule est interdit.")
    if not re.match(r"^\s*(SELECT|WITH)\b", s, re.IGNORECASE):
        raise ErreurMCP("Seules les requêtes SELECT (ou WITH … SELECT) sont acceptées.")
    interdit = _SQL_INTERDIT.search(s)
    if interdit:
        raise ErreurMCP(
            f"Mot-clé interdit dans une requête de lecture : « {interdit.group(1)} »."
        )
    colonne = _COLONNES_INTERDITES.search(s)
    if colonne:
        raise ErreurMCP(
            f"La colonne « {colonne.group(1)} » ne peut être ni lue ni filtrée "
            "(secret ou donnée personnelle)."
        )
    interdites = noms_interdits if noms_interdits is not None else _tables_interdites_presentes(base)
    for mot in {m.lower() for m in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s)}:
        if mot in interdites or mot.startswith("sqlite_"):
            raise ErreurMCP(
                f"La table « {mot} » n'est pas exposée : messagerie, RH/paie, "
                "calendrier personnel et secrets sont hors périmètre du MCP."
            )
    return s


def executer_select(base: str, sql: str, limite: int = LIMITE_DEFAUT) -> dict[str, Any]:
    s = _valider(base, sql)
    n = max(1, min(int(limite or LIMITE_DEFAUT), LIMITE_MAX))
    enveloppe = f"SELECT * FROM (\n{s}\n) LIMIT {n + 1}"

    debut = time.monotonic()
    with _connexion(base) as conn:
        _garde_temps(conn, DUREE_MAX_S)
        try:
            cur = conn.execute(enveloppe)
            colonnes = [d[0] for d in (cur.description or [])]
            brutes = cur.fetchall()
        except sqlite3.OperationalError as e:
            msg = str(e)
            if "interrupted" in msg.lower():
                raise ErreurMCP(
                    f"Requête interrompue : plus de {int(DUREE_MAX_S)} s d'exécution. "
                    "Ajoute un filtre ou réduis la jointure."
                ) from e
            raise ErreurMCP(f"SQL invalide : {msg}") from e
        except sqlite3.DatabaseError as e:
            raise ErreurMCP(f"Erreur SQLite : {e}") from e
    duree = round(time.monotonic() - debut, 3)

    tronque = len(brutes) > n
    brutes = brutes[:n]
    masquees = [c for c in colonnes if _COLONNES_INTERDITES.search(c)]
    lignes = []
    for r in brutes:
        lignes.append({
            c: (_MASQUE if c in masquees else _valeur_json(r[i]))
            for i, c in enumerate(colonnes)
        })

    return {
        "base": base,
        "sql": s,
        "colonnes": colonnes,
        "nb_lignes": len(lignes),
        "tronque": tronque,
        "limite": n,
        "duree_s": duree,
        "colonnes_masquees": masquees or None,
        "lignes": lignes,
    }


def apercu_table(base: str, table: str, limite: int = 20) -> dict[str, Any]:
    nom = (table or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nom):
        raise ErreurMCP("Nom de table invalide.")
    if table_interdite(base, nom):
        raise ErreurMCP(f"La table « {nom} » n'est pas exposée par le MCP.")
    with _connexion(base) as conn:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=? LIMIT 1",
            (nom,),
        ).fetchone()
    if not existe:
        raise ErreurMCP(f"La table « {nom} » n'existe pas dans la base « {base} ».")
    return executer_select(base, f'SELECT * FROM "{nom}"', limite)
