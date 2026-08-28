"""Database Viewer — requêtes SQL via langage naturel (Anthropic Claude).

Le SQL produit par le modèle est exécuté par `diagnostic_sql.executer()`, donc
sous l'autoriseur SQLite. `validate_select_sql()` reste en amont, mais ce n'est
plus la barrière de sécurité : c'est un contrôle de forme, qui rend une erreur
lisible tout de suite et ajoute la LIMIT manquante. Un filtre par expression
régulière ne sait pas ce qu'une requête va lire ; l'autoriseur, lui, refuse à
la lecture, table par table et colonne par colonne.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from fastapi import HTTPException

from app.services import diagnostic_sql
from config import ANTHROPIC_API_KEY, DB_PATH

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
- Utilise uniquement les tables et colonnes du schéma fourni. Le schéma ne
  contient pas toute la base : ce qui n'y est pas est refusé à la lecture, il
  est donc inutile de le deviner.
- Dates souvent stockées en TEXT ISO ou format français ; adapte les filtres.
- Si la question est ambiguë, choisis l'interprétation la plus utile pour un admin métier.

Réponds UNIQUEMENT avec un objet JSON valide (sans markdown) :
{"sql": "SELECT ...", "explanation": "Courte phrase en français expliquant la requête."}
"""


def build_schema_snapshot() -> str:
    """Résumé compact du schéma pour le prompt Claude.

    Ne décrit que les tables de la liste blanche, et tait les colonnes
    masquées : le modèle ne peut pas proposer de lire ce qu'il ne voit pas,
    et n'écrit pas une requête vouée à revenir NULL.
    """
    lines: list[str] = []
    for name in sorted(diagnostic_sql.TABLES_LISIBLES):
        try:
            cols = diagnostic_sql.colonnes_de_la_table(DB_PATH, name)
        except Exception:
            continue
        parts = []
        for c in cols:
            if c["masquee"]:
                continue
            flags = []
            if c["pk"]:
                flags.append("PK")
            if c["notnull"]:
                flags.append("NOT NULL")
            parts.append(f"{c['name']} {(c['type'] or 'TEXT').upper()}"
                         + (f" ({','.join(flags)})" if flags else ""))
        if not parts:
            continue
        lines.append(f"- {name}: {', '.join(parts)}")
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


def execute_select(sql: str) -> dict[str, Any]:
    """Exécute le SQL produit par le modèle, sous encadrement."""
    sql = validate_select_sql(sql)
    r = diagnostic_sql.executer(DB_PATH, sql, lignes_max=_MAX_ROWS)

    def _safe(v: Any) -> Any:
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8", errors="replace")
            except Exception:
                return f"<BLOB {len(v)} bytes>"
        return v

    return {
        "columns": r["colonnes"],
        "rows": [[_safe(cell) for cell in ligne] for ligne in r["lignes"]],
        "total": r["nb_lignes"],
        "truncated": r["tronque"],
    }


def run_natural_language_query(question: str) -> dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question vide.")
    if len(q) > 2000:
        raise HTTPException(status_code=400, detail="Question trop longue (max 2000 caractères).")
    schema = build_schema_snapshot()
    generated = natural_language_to_sql(q, schema)
    result = execute_select(generated["sql"])
    return {
        "question": q,
        "sql": validate_select_sql(generated["sql"]),
        "explanation": generated["explanation"],
        **result,
    }
