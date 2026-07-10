"""
Kernse — hachage des mots de passe superadmin plateforme.

Utilise PBKDF2-HMAC-SHA256 (stdlib, aucun paquet externe) avec un salt
aléatoire de 16 octets et 240_000 itérations (OWASP 2023 baseline).

Format stocké en DB : `pbkdf2$<iterations>$<salt_hex>$<hash_hex>`.

Comparaison en temps constant via `hmac.compare_digest`.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets


PBKDF2_ITERATIONS = 240_000
SALT_BYTES = 16
HASH_BYTES = 32


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Mot de passe superadmin : minimum 12 caractères.")
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=HASH_BYTES
    )
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not password or not stored:
        return False
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2":
        return False
    try:
        iters = int(iters)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iters, dklen=len(expected)
    )
    return hmac.compare_digest(computed, expected)
