#!/usr/bin/env python3
"""
MySifa — agent d'impression local

Petit démon Python autonome à faire tourner sur un Raspberry Pi ou un PC de
l'usine. Il poll le VPS MySifa toutes les N secondes, récupère les jobs pending,
les envoie à leur imprimante cible, puis ack.

Deux backends d'envoi selon le `type_connexion` de l'imprimante côté MySifa :

  - tcp_ip        → socket TCP:9100 (stdlib pure). Marche pour toute imprimante
                    Zebra/Brother/TSC/… branchée directement au LAN.

  - windows_local → API Windows (win32print) pour cibler une queue installée
                    sur ce PC hôte. Marche pour USB, LPT et toute imprimante
                    déjà déclarée dans "Périphériques et imprimantes". Nécessite
                    `pip install pywin32` sur le PC hôte.

Compatible Python 3.7+ (via `from __future__ import annotations`).

Configuration : agent_config.yaml dans le même dossier que ce script.
Format minimal :

    server_url: https://www.mysifa.com
    token: xxxxxxxxxxxxxx           # le token affiché à la création de l'agent
    poll_interval: 2                # secondes entre 2 polls
    heartbeat_interval: 30          # secondes entre 2 heartbeats
    printer_timeout: 8              # secondes de timeout socket vers l'imprimante
    log_level: INFO

Déploiement Linux (systemd) : voir mysifa-print-agent.service dans ce dossier.
Déploiement Windows (NSSM)  : voir install_agent_windows.ps1 dans ce dossier.
"""

from __future__ import annotations

import base64
import json
import logging
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ─── Backend Windows local (queue via win32print) ────────────────────
# Import optionnel : l'agent fonctionne sans si aucun `windows_local` n'est
# rattaché. On log l'absence à l'usage seulement (pas au démarrage).
try:
    import win32print  # type: ignore
    _HAS_WIN32PRINT = True
except Exception:
    _HAS_WIN32PRINT = False


DEFAULT_CONFIG = {
    "server_url": "https://www.mysifa.com",
    "token": "",
    "poll_interval": 2,
    "heartbeat_interval": 30,
    "printer_timeout": 8,
    "log_level": "INFO",
}


def load_config(path: Path) -> dict:
    """Charge la config YAML minimaliste (parser maison pour éviter la dépendance
    à PyYAML). Format : `clef: valeur` par ligne, `#` pour commentaire."""
    cfg = dict(DEFAULT_CONFIG)
    if not path.is_file():
        logging.error("Config introuvable : %s", path)
        sys.exit(2)
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if v.isdigit():
                v = int(v)
            elif v.lower() in ("true", "yes", "on"):
                v = True
            elif v.lower() in ("false", "no", "off"):
                v = False
            cfg[k] = v
    if not cfg.get("token"):
        logging.error("Token manquant dans la config. Récupère-le en créant un agent dans /settings > Imprimantes.")
        sys.exit(2)
    cfg["server_url"] = str(cfg["server_url"]).rstrip("/")
    return cfg


def http_request(url: str, method: str, token: str, payload: dict | None = None, timeout: int = 10) -> dict:
    body = None
    headers = {"X-Agent-Token": token, "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return json.loads(data.decode("utf-8")) if data else {}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} — {detail or e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Réseau : {e.reason}")


def send_to_printer_tcp(ip: str, port: int, payload: bytes, timeout: int = 8) -> None:
    """Envoie les octets directement à l'imprimante en TCP:9100 (protocole
    raw standard des Zebra, Brother, TSC, etc.)."""
    with socket.create_connection((ip, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        # Utile pour les paquets < MTU : force l'envoi immédiat
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.sendall(payload)


def send_to_printer_windows(queue_name: str, payload: bytes, doc_name: str = "MySifa print job") -> None:
    """Envoie les octets à une queue Windows en mode RAW (le driver ne réinterprète
    pas). Marche pour USB, LPT et réseau tant qu'une queue Windows existe.

    Nécessite `pywin32` — installé sur les PC hôtes via install_agent_windows.ps1.
    """
    if not _HAS_WIN32PRINT:
        raise RuntimeError(
            "pywin32 non installé sur cet agent — impossible d'atteindre les imprimantes "
            "Windows locales. Installe-le avec : pip install pywin32"
        )
    hprinter = win32print.OpenPrinter(queue_name)
    try:
        # Format ("nom_doc", None, "RAW") = octets bruts, le driver Windows
        # ne rerend pas. C'est exactement ce qu'on veut pour du ZPL/EPL/ESC-POS.
        job_id = win32print.StartDocPrinter(hprinter, 1, (doc_name, None, "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, payload)
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)


# Backward-compat : garde l'ancienne signature pour éviter de casser
# des appels externes qui pourraient exister.
def send_to_printer(ip: str, port: int, payload: bytes, timeout: int = 8) -> None:
    send_to_printer_tcp(ip, port, payload, timeout)


def process_jobs(cfg: dict) -> int:
    """Récupère les jobs pending, les envoie aux imprimantes, ack le résultat.
    Retourne le nombre de jobs traités."""
    url_jobs = f"{cfg['server_url']}/api/print/agent/jobs?limit=20"
    r = http_request(url_jobs, "GET", cfg["token"], timeout=15)
    jobs = r.get("jobs", []) if isinstance(r, dict) else []
    if not jobs:
        return 0
    processed = 0
    for job in jobs:
        jid = job["id"]
        imp = job["imprimante"]
        try:
            payload = base64.b64decode(job["payload_b64"])
        except Exception as e:
            _ack(cfg, jid, ok=False, erreur=f"Payload b64 invalide : {e}")
            continue
        # v1.6 — route selon type_connexion. Défaut 'tcp_ip' pour rétrocompat
        # avec des serveurs pré-v189 qui ne renvoient pas encore ce champ.
        tc = imp.get("type_connexion", "tcp_ip") if isinstance(imp, dict) else "tcp_ip"
        try:
            if tc == "windows_local":
                queue = imp.get("nom_queue_windows")
                if not queue:
                    raise RuntimeError("Imprimante configurée en windows_local mais nom_queue_windows vide côté serveur.")
                send_to_printer_windows(queue, payload, doc_name=f"MySifa job {jid}")
                _ack(cfg, jid, ok=True)
                logging.info("Job %s → %s (win:%s) : OK", jid, imp["nom"], queue)
            else:
                send_to_printer_tcp(imp["ip"], int(imp["port"]), payload, timeout=cfg["printer_timeout"])
                _ack(cfg, jid, ok=True)
                logging.info("Job %s → %s (%s:%s) : OK", jid, imp["nom"], imp["ip"], imp["port"])
            processed += 1
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            logging.warning("Job %s → %s : ÉCHEC (%s)", jid, imp["nom"], msg)
            _ack(cfg, jid, ok=False, erreur=msg)
    return processed


def _ack(cfg: dict, job_id: int, ok: bool, erreur: str | None = None) -> None:
    url = f"{cfg['server_url']}/api/print/agent/jobs/{job_id}/ack"
    try:
        http_request(url, "POST", cfg["token"], {"ok": ok, "erreur": erreur}, timeout=10)
    except Exception as e:
        logging.warning("ACK %s : %s", job_id, e)


def heartbeat(cfg: dict) -> None:
    url = f"{cfg['server_url']}/api/print/agent/heartbeat"
    try:
        r = http_request(url, "POST", cfg["token"], {}, timeout=10)
        n = len(r.get("imprimantes", []))
        logging.info("Heartbeat OK — %d imprimante(s) rattachée(s)", n)
    except Exception as e:
        logging.warning("Heartbeat KO : %s", e)


def main_loop(cfg: dict) -> None:
    logging.info(
        "MySifa print-agent v1.6 démarré — server=%s poll=%ss, backend Windows=%s",
        cfg["server_url"], cfg["poll_interval"],
        "OK" if _HAS_WIN32PRINT else "absent (pip install pywin32 pour les imprimantes USB/LPT)",
    )
    heartbeat(cfg)
    last_hb = time.monotonic()
    while True:
        try:
            n = process_jobs(cfg)
            if n:
                logging.info("Batch traité : %d job(s)", n)
        except Exception as e:
            logging.warning("Poll : %s", e)
        # Heartbeat périodique (indépendant du poll pour rester léger)
        if time.monotonic() - last_hb > cfg["heartbeat_interval"]:
            heartbeat(cfg)
            last_hb = time.monotonic()
        time.sleep(cfg["poll_interval"])


def main() -> None:
    here = Path(__file__).resolve().parent
    cfg_path = here / "agent_config.yaml"
    if len(sys.argv) > 1:
        cfg_path = Path(sys.argv[1]).resolve()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    cfg = load_config(cfg_path)
    logging.getLogger().setLevel(getattr(logging, str(cfg["log_level"]).upper(), logging.INFO))
    try:
        main_loop(cfg)
    except KeyboardInterrupt:
        logging.info("Arrêt demandé — bye.")


if __name__ == "__main__":
    main()
