"""
OAuth 2.1 pour le serveur MCP : clients enregistres dynamiquement, codes
d'autorisation a usage unique, jetons d'acces et de rafraichissement.

Pourquoi cette migration existe : les connecteurs Claude ne savent pas
transporter un en-tete `X-Api-Key`. Ils parlent OAuth, et rien d'autre. Sans
ces trois tables, la seule facon de brancher MySifa sur un agent etait de
coller une cle API dans une URL — un secret dans les logs nginx, dans
l'historique du navigateur, et en clair dans les parametres du connecteur.

Aucun secret n'est stocke en clair : seules les empreintes SHA-256 des jetons
et des codes sont conservees, comme pour `api_keys`. Un jeton perdu n'est pas
recuperable, il se revoque.
"""

NOM = "mcp_oauth"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_oauth_clients (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id           TEXT NOT NULL UNIQUE,
            client_secret_hash  TEXT,
            client_name         TEXT NOT NULL DEFAULT '',
            redirect_uris       TEXT NOT NULL DEFAULT '[]',
            scope               TEXT NOT NULL DEFAULT 'mcp:read',
            auth_method         TEXT NOT NULL DEFAULT 'none',
            created_at          TEXT NOT NULL,
            last_used_at        TEXT
        )
        """
    )

    # Le code d'autorisation vit cinq minutes et ne sert qu'une fois. On garde
    # la ligne apres usage (colonne `used_at`) : un code rejoue est une tentative
    # de rejeu, pas une erreur de frappe, et le silence serait le pire accueil.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_oauth_codes (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            code_hash             TEXT NOT NULL UNIQUE,
            client_id             TEXT NOT NULL,
            user_id               INTEGER NOT NULL,
            user_email            TEXT NOT NULL DEFAULT '',
            redirect_uri          TEXT NOT NULL,
            code_challenge        TEXT NOT NULL,
            code_challenge_method TEXT NOT NULL DEFAULT 'S256',
            scope                 TEXT NOT NULL DEFAULT 'mcp:read',
            resource              TEXT,
            created_at            TEXT NOT NULL,
            expires_at            TEXT NOT NULL,
            used_at               TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_oauth_tokens (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            access_hash        TEXT NOT NULL UNIQUE,
            refresh_hash       TEXT UNIQUE,
            client_id          TEXT NOT NULL,
            user_id            INTEGER NOT NULL,
            user_email         TEXT NOT NULL DEFAULT '',
            scope              TEXT NOT NULL DEFAULT 'mcp:read',
            created_at         TEXT NOT NULL,
            expires_at         TEXT NOT NULL,
            refresh_expires_at TEXT,
            revoked_at         TEXT,
            last_used_at       TEXT
        )
        """
    )

    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_mcp_oauth_codes_exp ON mcp_oauth_codes(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_mcp_oauth_tokens_exp ON mcp_oauth_tokens(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_mcp_oauth_tokens_user ON mcp_oauth_tokens(user_id)",
    ):
        conn.execute(sql)

    conn.commit()
    print("[MySifa] migration mcp_oauth : tables OAuth du serveur MCP en place.")
