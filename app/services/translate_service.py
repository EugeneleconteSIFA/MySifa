"""MyTraduction — service DeepL avec cache SQLite.

Encapsule les appels à l'API DeepL (Free ou Pro selon la clé) et met en
cache les traductions dans la table `translations_cache` pour éviter de
consommer inutilement le quota mensuel.

Utilisation typique :
    from app.services.translate_service import translate, get_usage
    result = translate("Bonjour", target_lang="EN", source_lang="FR")
    # → {"translated": "Hello", "source_detected": "FR", "cached": False}
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import HTTPException

from config import DEEPL_API_KEY, DEEPL_API_URL


# Langues supportées par DeepL — codes ISO utilisés par l'API.
# Ordre = celui affiché dans le sélecteur UI.
SUPPORTED_LANGS = [
    ("FR", "Français"),
    ("EN", "Anglais"),
    ("DE", "Allemand"),
    ("ES", "Espagnol"),
    ("IT", "Italien"),
    ("NL", "Néerlandais"),
    ("PT", "Portugais"),
    ("PL", "Polonais"),
]

# Codes source acceptés par DeepL (subset de SUPPORTED_LANGS + "auto").
_VALID_SOURCE = {code for code, _ in SUPPORTED_LANGS}
# Codes cible acceptés par DeepL. Note : DeepL distingue EN-GB / EN-US et
# PT-BR / PT-PT en target, mais on garde le mapping simple ici.
_VALID_TARGET = {code for code, _ in SUPPORTED_LANGS}

# Limite de sécurité — un texte > 100k caractères sera refusé côté service
# pour éviter de consommer 20% du quota mensuel en un seul appel.
MAX_CHARS_PER_REQUEST = 100_000

_FORMALITY_VALUES = {"default", "more", "less", "prefer_more", "prefer_less"}


def _cache_key(text: str, source_lang: str, target_lang: str, formality: str) -> str:
    """Hash SHA-256 utilisé comme clé de cache."""
    payload = f"{source_lang or 'auto'}|{target_lang}|{formality}|{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lookup_cache(conn: sqlite3.Connection, key: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT source_lang, target_lang, translated FROM translations_cache WHERE hash=?",
        (key,),
    ).fetchone()
    if not row:
        return None
    # Incrémente le compteur — utile pour identifier les traductions à
    # promouvoir en dictionnaire i18n statique si elles reviennent souvent.
    try:
        conn.execute(
            "UPDATE translations_cache SET hit_count = hit_count + 1 WHERE hash=?",
            (key,),
        )
        conn.commit()
    except Exception:
        pass
    return {
        "source_lang": row[0],
        "target_lang": row[1],
        "translated": row[2],
    }


def _store_cache(
    conn: sqlite3.Connection,
    key: str,
    source_lang: Optional[str],
    target_lang: str,
    formality: str,
    translated: str,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO translations_cache
           (hash, source_lang, target_lang, formality, translated, created_at, hit_count)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (key, source_lang, target_lang, formality, translated, _now_iso()),
    )
    conn.commit()


def _log_usage(
    conn: sqlite3.Connection,
    user_id: Optional[int],
    chars: int,
    cached: bool,
    source_lang: Optional[str],
    target_lang: str,
) -> None:
    try:
        conn.execute(
            """INSERT INTO translations_usage
               (user_id, chars_count, cached, source_lang, target_lang, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, chars, 1 if cached else 0, source_lang, target_lang, _now_iso()),
        )
        conn.commit()
    except Exception:
        # Le log ne doit jamais bloquer une traduction utilisateur.
        pass


def _ensure_cache_tables(conn: sqlite3.Connection) -> None:
    """Filet de sécurité : crée les tables si la migration 161 n'a pas tourné.

    Utile en dev local quand MIGRATIONS_DISABLED=1 : le service crée ses
    propres tables à la première utilisation. En prod, la migration 161
    aura déjà tourné et les CREATE IF NOT EXISTS sont no-ops.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS translations_cache (
            hash         TEXT PRIMARY KEY,
            source_lang  TEXT,
            target_lang  TEXT NOT NULL,
            formality    TEXT,
            translated   TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            hit_count    INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS translations_usage (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            chars_count  INTEGER NOT NULL,
            cached       INTEGER NOT NULL DEFAULT 0,
            source_lang  TEXT,
            target_lang  TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );
    """)
    conn.commit()



def _call_deepl(
    text: str,
    target_lang: str,
    source_lang: Optional[str],
    formality: str,
) -> dict:
    """Appel bas-niveau à l'API DeepL. Renvoie {"translated": ..., "source_detected": ...}."""
    if not DEEPL_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Clé DeepL non configurée — ajouter DEEPL_API_KEY dans .env",
        )

    endpoint = DEEPL_API_URL.rstrip("/") + "/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "text": text,
        "target_lang": target_lang,
    }
    if source_lang and source_lang != "auto":
        data["source_lang"] = source_lang
    if formality and formality != "default":
        data["formality"] = formality

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(endpoint, headers=headers, data=data)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"DeepL injoignable : {e}")

    if resp.status_code == 456:
        # Quota mensuel dépassé (DeepL renvoie 456 spécifiquement).
        raise HTTPException(
            status_code=429,
            detail="Quota DeepL mensuel atteint. Réessayer le mois prochain ou passer en Pro.",
        )
    if resp.status_code == 403:
        raise HTTPException(
            status_code=502,
            detail="Clé DeepL invalide ou expirée — vérifier DEEPL_API_KEY.",
        )
    if resp.status_code >= 400:
        detail = resp.text[:500]
        raise HTTPException(status_code=502, detail=f"DeepL erreur {resp.status_code} : {detail}")

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="DeepL — réponse non-JSON.")

    translations = payload.get("translations") or []
    if not translations:
        raise HTTPException(status_code=502, detail="DeepL — pas de traduction retournée.")

    return {
        "translated": translations[0].get("text", ""),
        "source_detected": translations[0].get("detected_source_language"),
    }


def translate(
    conn: sqlite3.Connection,
    text: str,
    target_lang: str,
    source_lang: Optional[str] = None,
    formality: str = "default",
    user_id: Optional[int] = None,
) -> dict:
    """Traduit un texte via DeepL, avec cache.

    Retourne : {"translated": str, "source_detected": str|None, "cached": bool}
    Lève HTTPException en cas d'erreur (clé manquante, quota, réseau).
    """
    _ensure_cache_tables(conn)
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texte vide.")
    if len(text) > MAX_CHARS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Texte trop long ({len(text)} caractères). Maximum : {MAX_CHARS_PER_REQUEST}.",
        )

    target_lang = (target_lang or "").upper().strip()
    if target_lang not in _VALID_TARGET:
        raise HTTPException(
            status_code=400,
            detail=f"Langue cible invalide : {target_lang}. Valides : {sorted(_VALID_TARGET)}",
        )

    if source_lang:
        source_lang = source_lang.upper().strip()
        if source_lang != "AUTO" and source_lang not in _VALID_SOURCE:
            raise HTTPException(
                status_code=400,
                detail=f"Langue source invalide : {source_lang}.",
            )
        if source_lang == "AUTO":
            source_lang = None
    formality = formality if formality in _FORMALITY_VALUES else "default"

    # Cache hit ?
    key = _cache_key(text, source_lang or "", target_lang, formality)
    cached = _lookup_cache(conn, key)
    if cached:
        _log_usage(conn, user_id, len(text), True, cached["source_lang"], target_lang)
        return {
            "translated": cached["translated"],
            "source_detected": cached["source_lang"],
            "cached": True,
        }

    # Appel DeepL
    result = _call_deepl(text, target_lang, source_lang, formality)
    src_final = source_lang or result.get("source_detected")

    _store_cache(conn, key, src_final, target_lang, formality, result["translated"])
    _log_usage(conn, user_id, len(text), False, src_final, target_lang)

    return {
        "translated": result["translated"],
        "source_detected": src_final,
        "cached": False,
    }


def get_usage(conn: sqlite3.Connection, user_id: Optional[int] = None) -> dict:
    """Retourne les stats d'usage du mois en cours + le quota DeepL restant.

    Retour :
    {
        "month_chars_billed": int,   # caractères réellement facturés (non-cachés)
        "month_chars_total":  int,   # tous appels (avec cache)
        "cache_hits":         int,
        "deepl_limit":        int|None,  # quota mensuel DeepL
        "deepl_used":         int|None,  # caractères déjà utilisés côté DeepL
    }
    """
    _ensure_cache_tables(conn)
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()

    row = conn.execute(
        """SELECT
             COALESCE(SUM(chars_count),0),
             COALESCE(SUM(CASE WHEN cached=0 THEN chars_count ELSE 0 END),0),
             COALESCE(SUM(cached),0)
           FROM translations_usage
           WHERE created_at >= ?""",
        (month_start,),
    ).fetchone()
    total, billed, hits = row if row else (0, 0, 0)

    deepl_limit = None
    deepl_used = None
    if DEEPL_API_KEY:
        try:
            endpoint = DEEPL_API_URL.rstrip("/") + "/usage"
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    endpoint,
                    headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                )
            if resp.status_code == 200:
                data = resp.json()
                deepl_limit = data.get("character_limit")
                deepl_used = data.get("character_count")
        except Exception:
            pass

    return {
        "month_chars_total": int(total),
        "month_chars_billed": int(billed),
        "cache_hits": int(hits),
        "deepl_limit": deepl_limit,
        "deepl_used": deepl_used,
    }
