"""
Kernse — 2FA TOTP (RFC 6238) pour les superadmins plateforme.

Implémentation manuelle (stdlib uniquement, aucune dépendance externe)
pour éviter d'introduire `pyotp` juste pour deux fonctions. Le format
est standard : compatible Google Authenticator, Authy, 1Password.

Paramètres RFC 6238 :
    - HMAC-SHA1
    - 30 secondes par pas
    - 6 chiffres
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


TOTP_DIGITS = 6
TOTP_STEP_SECONDS = 30
TOTP_SECRET_BYTES = 20  # 160 bits — recommandation RFC


def generate_secret() -> str:
    """Génère un nouveau secret TOTP en base32 (sans padding)."""
    raw = secrets.token_bytes(TOTP_SECRET_BYTES)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _hotp(secret_b32: str, counter: int) -> str:
    """HOTP RFC 4226 — bloc de base."""
    padded = secret_b32 + "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = struct.pack(">Q", counter)
    hs = hmac.new(key, msg, hashlib.sha1).digest()
    offset = hs[-1] & 0x0F
    bin_code = struct.unpack(">I", hs[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(bin_code % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_code(secret_b32: str, code: str, *, window: int = 1) -> bool:
    """Vérifie un code TOTP en autorisant une fenêtre de +/- `window` pas
    (tolérance à la dérive d'horloge et au temps de saisie).

    Comparaison en temps constant.
    """
    if not secret_b32 or not code:
        return False
    code = code.replace(" ", "").strip()
    if not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    counter = int(time.time() // TOTP_STEP_SECONDS)
    for offset in range(-window, window + 1):
        candidate = _hotp(secret_b32, counter + offset)
        if hmac.compare_digest(candidate, code):
            return True
    return False


def otpauth_uri(*, secret_b32: str, email: str, issuer: str = "Kernse") -> str:
    """Retourne l'URI otpauth:// à encoder en QR code pour l'ajout dans
    Google Authenticator / Authy / etc."""
    label = quote(f"{issuer}:{email}")
    params = (
        f"secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&algorithm=SHA1"
        f"&digits={TOTP_DIGITS}"
        f"&period={TOTP_STEP_SECONDS}"
    )
    return f"otpauth://totp/{label}?{params}"
