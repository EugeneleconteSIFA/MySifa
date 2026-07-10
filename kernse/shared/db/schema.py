"""
Kernse — schéma de la DB plateforme (platform.db)

Tables :
    clients             instances clients Kernse actives
    clients_archived    trace minimale des clients purgés (audit + comptable)
    audit_log           journal des actions plateforme (RGPD, comptabilité)
    platform_settings   config plateforme (nom marque, URL landing, catalogue plans, etc.)
    schema_migrations   versions de schéma appliquées (idempotent)

Toutes les dates sont stockées en ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
Les objets structurés (options, before/after audit) sont sérialisés en JSON TEXT.

Migrations : versions numériques monotones. Chaque _migrate_vN vérifie sa
présence dans schema_migrations avant de s'appliquer — idempotent.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def utcnow_iso() -> str:
    """Timestamp UTC ISO 8601 sans microsecondes (`2026-07-10T18:30:00Z`)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _record_migration(conn: sqlite3.Connection, version: int, name: str) -> None:
    conn.execute(
        "INSERT INTO schema_migrations(version, name, applied_at) VALUES(?, ?, ?)",
        (version, name, utcnow_iso()),
    )


def _migration_applied(conn: sqlite3.Connection, version: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version=? LIMIT 1",
        (version,),
    ).fetchone() is not None


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


# ─── Migration 1 — tables initiales ──────────────────────────────────────
def _migrate_v1(conn: sqlite3.Connection) -> None:
    if _migration_applied(conn, 1):
        return

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id              TEXT PRIMARY KEY,           -- UUID v4
            slug            TEXT UNIQUE NOT NULL,       -- ex. 'imprimerie-durand'
            company_name    TEXT NOT NULL,              -- ex. 'Imprimerie Durand SARL'
            subdomain       TEXT UNIQUE NOT NULL,       -- ex. 'durand.kernse.fr'
            port            INTEGER UNIQUE NOT NULL,    -- port FastAPI dédié
            plan            TEXT NOT NULL DEFAULT 'atelier',  -- 'atelier' | 'usine' | 'custom'
            deployed_ref    TEXT NOT NULL DEFAULT '',   -- SHA git court (7 chars) ou ''
            deployed_at     TEXT,                       -- ISO UTC de la dernière promotion
            pinned          INTEGER NOT NULL DEFAULT 0, -- 0/1 — épingle protège des mass-promote
            pinned_at       TEXT,                       -- ISO UTC de la pose d'épingle
            pinned_reason   TEXT,                       -- note libre superadmin
            suspended       INTEGER NOT NULL DEFAULT 0, -- 0/1 — accès bloqué (impayé, litige)
            suspended_at    TEXT,
            suspended_reason TEXT,
            terminated_at   TEXT,                       -- ISO UTC — début rétention 30 jours
            options_json    TEXT NOT NULL DEFAULT '{}', -- feature flags, modules activés, branding
            contact_email   TEXT NOT NULL,              -- superadmin de l'orga
            contact_name    TEXT,
            created_at      TEXT NOT NULL,
            created_by      TEXT NOT NULL               -- email superadmin plateforme
        );

        CREATE INDEX IF NOT EXISTS idx_clients_pinned    ON clients(pinned);
        CREATE INDEX IF NOT EXISTS idx_clients_suspended ON clients(suspended);
        CREATE INDEX IF NOT EXISTS idx_clients_plan      ON clients(plan);

        CREATE TABLE IF NOT EXISTS clients_archived (
            id              TEXT PRIMARY KEY,
            slug            TEXT NOT NULL,
            company_name    TEXT NOT NULL,
            plan            TEXT,
            created_at      TEXT NOT NULL,
            terminated_at   TEXT NOT NULL,
            purged_at       TEXT NOT NULL,
            purged_by       TEXT NOT NULL,
            reason          TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            at           TEXT NOT NULL,                 -- ISO UTC
            actor_email  TEXT NOT NULL,                 -- qui a fait l'action
            actor_ip     TEXT,                          -- IP source
            action       TEXT NOT NULL,                 -- verbe court : 'promote_client', 'pin_client', etc.
            entity_type  TEXT,                          -- 'client', 'setting', 'plan', ...
            entity_id    TEXT,                          -- id métier (client.id, ...)
            before_json  TEXT,                          -- état avant (JSON, nullable)
            after_json   TEXT,                          -- état après (JSON, nullable)
            note         TEXT                           -- commentaire optionnel
        );

        CREATE INDEX IF NOT EXISTS idx_audit_at          ON audit_log(at);
        CREATE INDEX IF NOT EXISTS idx_audit_actor       ON audit_log(actor_email);
        CREATE INDEX IF NOT EXISTS idx_audit_entity      ON audit_log(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_audit_action      ON audit_log(action);

        CREATE TABLE IF NOT EXISTS platform_settings (
            key         TEXT PRIMARY KEY,
            value_json  TEXT NOT NULL,                  -- valeur sérialisée JSON
            updated_at  TEXT NOT NULL,
            updated_by  TEXT NOT NULL
        );
        """
    )

    _record_migration(conn, 1, "initial_platform_schema")


# ─── Migration 2 — auth superadmin plateforme ────────────────────────────
def _migrate_v2(conn: sqlite3.Connection) -> None:
    if _migration_applied(conn, 2):
        return

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS superadmins (
            email          TEXT PRIMARY KEY,       -- lowercased
            password_hash  TEXT NOT NULL,          -- format 'pbkdf2$<iter>$<salt>$<hash>'
            totp_secret    TEXT,                   -- base32, NULL = 2FA désactivée
            created_at     TEXT NOT NULL,
            last_login_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS superadmin_sessions (
            session_id  TEXT PRIMARY KEY,          -- 64 hex chars
            email       TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            ip          TEXT,
            user_agent  TEXT,
            twofa_ok    INTEGER NOT NULL DEFAULT 0 -- 0/1 : 2FA validée pour cette session
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_email    ON superadmin_sessions(email);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires  ON superadmin_sessions(expires_at);
        """
    )
    _record_migration(conn, 2, "superadmin_auth")



def init_platform_db(db_path: str) -> None:
    """Crée / met à jour la DB plateforme.

    Idempotent : peut être appelé au boot de kernse-admin.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        _ensure_migrations_table(conn)
        _migrate_v1(conn)
        _migrate_v2(conn)
        conn.commit()
    finally:
        conn.close()


def seed_platform_defaults(db_path: str, actor_email: str = "system") -> None:
    """Insère les valeurs par défaut de `platform_settings` si absentes.

    Ces valeurs pilotent la landing, les emails plateforme, le catalogue des
    plans. Elles sont éditables ensuite via la console admin.
    """
    import json

    conn = sqlite3.connect(db_path)
    try:
        defaults = {
            "brand_name":      "Kernse",
            "brand_tagline":   "Le pilotage d'atelier sans Excel ni ERP usine à gaz",
            "landing_url":     "https://www.kernse.fr",
            "support_email":   "support@kernse.fr",
            "sla_uptime_pct":  99.5,
            "plans_catalog":   [
                {"key": "atelier", "label": "Kernse Atelier", "audience": "TPE — 2 à 15 pers."},
                {"key": "usine",   "label": "Kernse Usine",   "audience": "PME — 15 à 100 pers."},
            ],
            "starter_kits_available": [
                "imprimerie", "usinage", "plasturgie", "assemblage", "decoupe",
            ],
        }
        now = utcnow_iso()
        for key, value in defaults.items():
            existing = conn.execute(
                "SELECT 1 FROM platform_settings WHERE key=? LIMIT 1", (key,)
            ).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO platform_settings(key, value_json, updated_at, updated_by) VALUES(?, ?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), now, actor_email),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # Bootstrap local pour tests.
    import os
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "kernse/admin/data/platform.db"
    os.makedirs(os.path.dirname(target), exist_ok=True)
    init_platform_db(target)
    seed_platform_defaults(target)
    print(f"OK — platform DB prête : {target}")
