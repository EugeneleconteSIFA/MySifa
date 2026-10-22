"""
MyTools › Étiquettes — envoi d'un flux à une imprimante réseau (port 9100,
socket brute, comme l'agent local) et lecture de l'état d'une Zebra (~HS).

Aucune base ici : le routeur (app/routers/etiq_impression.py) choisit l'hôte
et le port dans le profil, contrôle le port contre ETIQ_PORTS_RESEAU, et
journalise. Testé contre un faux serveur local (tests/test_etiq_zpl.py).
"""

from __future__ import annotations

import re
import socket

from app.services.etiq_zpl import ImpressionImpossible


def envoyer_reseau(hote: str, port: int, donnees: bytes, timeout: float = 4.0) -> int:
    """Envoie le flux tel quel, rend le nombre d'octets écrits. Lève
    ImpressionImpossible avec un message que l'opérateur peut suivre."""
    try:
        with socket.create_connection((hote, int(port)), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(donnees)
            try:
                s.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        return len(donnees)
    except socket.timeout:
        raise ImpressionImpossible(f"Imprimante {hote}:{port} injoignable — délai dépassé ({timeout:g} s).")
    except ConnectionRefusedError:
        raise ImpressionImpossible(f"Imprimante {hote}:{port} : connexion refusée (port fermé ou imprimante occupée).")
    except OSError as e:
        raise ImpressionImpossible(f"Imprimante {hote}:{port} injoignable — {e.strerror or type(e).__name__}.")


def etat_zpl(hote: str, port: int, timeout: float = 3.0) -> dict:
    """Interroge une Zebra (~HS) : papier, pause, tête, ruban."""
    with socket.create_connection((hote, int(port)), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(b"~HS\r\n")
        brut = b""
        try:
            while brut.count(b"\x03") < 2 and len(brut) < 4096:
                morceau = s.recv(1024)
                if not morceau:
                    break
                brut += morceau
        except socket.timeout:
            pass
    return lire_etat_zpl(brut.decode("ascii", "replace"))


def lire_etat_zpl(texte: str) -> dict:
    blocs = [b.strip("\x02\x03\r\n ") for b in re.split(r"\x03", texte) if b.strip("\x02\x03\r\n ")]
    if len(blocs) < 2:
        return {"repond": bool(texte.strip()), "lisible": False}
    l1, l2 = blocs[0].split(","), blocs[1].split(",")

    def drapeau(champs, i):
        return len(champs) > i and champs[i].strip() == "1"
    return {"repond": True, "lisible": True, "papier_epuise": drapeau(l1, 1), "en_pause": drapeau(l1, 2),
            "tete_ouverte": drapeau(l2, 2), "ruban_epuise": drapeau(l2, 3)}


# ─── Parc : interrogation détaillée d'une Zebra ─────────────────────────

_ERREURS_HQES = {0x1: "papier épuisé", 0x2: "ruban épuisé", 0x4: "tête ouverte", 0x8: "défaut massicot",
                 0x10: "tête en surchauffe", 0x20: "moteur en surchauffe", 0x40: "élément de tête défectueux",
                 0x80: "tête non détectée"}
_ALERTES_HQES = {0x1: "calibrer le support", 0x2: "nettoyer la tête", 0x4: "tête usée : à remplacer",
                 0x8: "fin de papier proche"}


def interroger(hote: str, port: int, commande: bytes, timeout: float = 2.0, attente_fin: bytes = b"") -> str:
    """Envoie une commande d'interrogation et lit la réponse jusqu'au silence
    (ou jusqu'au motif `attente_fin`)."""
    with socket.create_connection((hote, int(port)), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(commande)
        brut = b""
        try:
            while len(brut) < 16384:
                morceau = s.recv(2048)
                if not morceau:
                    break
                brut += morceau
                if attente_fin and attente_fin in brut:
                    break
                s.settimeout(0.4)          # la suite arrive d'un bloc : on attend peu
        except socket.timeout:
            pass
    return brut.decode("ascii", "replace")


def lire_hqes(texte: str) -> dict:
    """~HQES : erreurs et alertes (dont « tête usée »)."""
    def drapeaux(motif, table):
        m = re.search(motif + r"\s*:?\s*(\d)\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})", texte or "")
        if not m:
            return None
        val = int(m.group(3), 16)
        return [lib for bit, lib in table.items() if val & bit]
    err = drapeaux(r"ERRORS", _ERREURS_HQES)
    ale = drapeaux(r"WARNINGS", _ALERTES_HQES)
    return {"lisible": err is not None or ale is not None, "erreurs": err or [], "alertes": ale or [],
            "tete_usee": "tête usée : à remplacer" in (ale or [])}


def lire_hqod(texte: str) -> dict:
    """~HQOD : compteurs de longueur imprimée (non remis à zéro, puis utilisateur)."""
    out = {}
    m = re.search(r"NONRESETTABLE\s*:\s*([\d.,]+)\s*(\S*)", texte or "", re.I)
    if m:
        out["total"] = m.group(1)
        out["unite"] = m.group(2).replace('"', "po") or ""
    m = re.search(r"RESETTABLE CNTR1\s*:\s*([\d.,]+)", texte or "", re.I)
    if m:
        out["compteur1"] = m.group(1)
    return out


def etat_complet(hote: str, port: int, timeout: float = 2.0) -> dict:
    """État d'une Zebra pour la vue du parc : ~HS, ~HQES, ~HQOD."""
    try:
        etat = lire_etat_zpl(interroger(hote, port, b"~HS\r\n", timeout, b"\x03\r\n\x02"))
    except OSError as e:
        return {"en_ligne": False, "message": f"Injoignable — {e.strerror or type(e).__name__}."}
    etat["en_ligne"] = bool(etat.get("repond"))
    try:
        etat.update(lire_hqes(interroger(hote, port, b"~HQES\r\n", timeout, b"WARNINGS")))
    except OSError:
        pass
    try:
        etat["compteurs"] = lire_hqod(interroger(hote, port, b"~HQOD\r\n", timeout))
    except OSError:
        pass
    return etat
