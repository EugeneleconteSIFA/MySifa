"""Database Viewer — requêtes SQL via langage naturel (Anthropic Claude)."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from typing import Any

from fastapi import HTTPException

from config import ANTHROPIC_API_KEY

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
_MAX_ROWS = 200
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|"
    r"PRAGMA|VACUUM|REINDEX|TRIGGER|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = """Tu es un assistant SQL pour MySifa (SQLite en production).
L'utilisateur pose une question en français ; tu produis UNE SEULE requête SELECT valide.

Règles strictes :
- Uniquement SELECT (pas de modification, pas de PRAGMA, pas de plusieurs requêtes).
- SQLite : guillemets doubles pour les identifiants si besoin, pas de backticks MySQL.
- Limite les résultats : ajoute LIMIT 200 si absent (max 200 lignes).
- Utilise uniquement les tables et colonnes du schéma fourni.
- Dates souvent stockées en TEXT ISO ou format français ; adapte les filtres.
- Si la question est ambiguë, choisis l'interprétation la plus utile pour un admin métier.

Réponds UNIQUEMENT avec un objet JSON valide (sans markdown) :
{"sql": "SELECT ...", "explanation": "Courte phrase en français expliquant la requête."}
"""


def build_schema_snapshot(conn: sqlite3.Connection) -> str:
    """Résumé compact du schéma pour le prompt Claude."""
    tables = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    lines: list[str] = []
    for t in tables:
        name = t[0]
        cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
        parts = []
        for c in cols:
            col = c[1]
            typ = (c[2] or "TEXT").upper()
            flags = []
            if c[5]:
                flags.append("PK")
            if c[3]:
                flags.append("NOT NULL")
            parts.append(f"{col} {typ}" + (f" ({','.join(flags)})" if flags else ""))
        try:
            n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        except Exception:
            n = "?"
        lines.append(f"- {name} (~{n} lignes): {', '.join(parts)}")
    return "\n".join(lines)


def _parse_ai_json(raw: str) -> dict[str, str]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Réponse IA invalide (JSON attendu).",
        ) from e
    sql = (data.get("sql") or "").strip()
    explanation = (data.get("explanation") or "").strip()
    if not sql:
        raise HTTPException(status_code=502, detail="L'IA n'a pas produit de requête SQL.")
    return {"sql": sql, "explanation": explanation}


def validate_select_sql(sql: str) -> str:
    """Valide et normalise une requête SELECT uniquement."""
    s = sql.strip().rstrip(";").strip()
    if not s:
        raise HTTPException(status_code=400, detail="Requête SQL vide.")
    if ";" in s:
        raise HTTPException(status_code=400, detail="Une seule requête autorisée.")
    if not re.match(r"^\s*SELECT\b", s, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Seules les requêtes SELECT sont autorisées.")
    if _FORBIDDEN_SQL.search(s):
        raise HTTPException(status_code=400, detail="Mot-clé SQL interdit dans la requête.")
    if not re.search(r"\bLIMIT\b", s, re.IGNORECASE):
        s = f"{s} LIMIT {_MAX_ROWS}"
    return s


def natural_language_to_sql(question: str, schema: str) -> dict[str, str]:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Clé Anthropic non configurée — ajouter ANTHROPIC_API_KEY dans .env",
        )
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = (
        f"Schéma de la base :\n{schema}\n\n"
        f"Question : {question.strip()}\n\n"
        "Génère le JSON demandé."
    )
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            raw += block.text
    return _parse_ai_json(raw)


def execute_select(conn: sqlite3.Connection, sql: str) -> dict[str, Any]:
    sql = validate_select_sql(sql)
    cur = conn.execute(sql)
    if cur.description is None:
        return {
            "columns": [],
            "rows": [],
            "total": 0,
            "truncated": False,
        }
    columns = [d[0] for d in cur.description]
    rows_raw = cur.fetchmany(_MAX_ROWS + 1)
    truncated = len(rows_raw) > _MAX_ROWS
    rows_raw = rows_raw[:_MAX_ROWS]

    def _safe(v: Any) -> Any:
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8", errors="replace")
            except Exception:
                return f"<BLOB {len(v)} bytes>"
        return v

    rows = [[_safe(cell) for cell in r] for r in rows_raw]
    return {
        "columns": columns,
        "rows": rows,
        "total": len(rows),
        "truncated": truncated,
    }


def run_natural_language_query(
    conn: sqlite3.Connection, question: str
) -> dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question vide.")
    if len(q) > 2000:
        raise HTTPException(status_code=400, detail="Question trop longue (max 2000 caractères).")
    schema = build_schema_snapshot(conn)
    generated = natural_language_to_sql(q, schema)
    result = execute_select(conn, generated["sql"])
    return {
        "question": q,
        "sql": validate_select_sql(generated["sql"]),
        "explanation": generated["explanation"],
        **result,
    }
