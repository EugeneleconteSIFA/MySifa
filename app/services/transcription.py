"""
Transcription locale d'un enregistrement (faster-whisper, sur le serveur).

L'audio ne quitte pas la machine : c'est la décision du 2026-11-05 (spec
docs/reunions-mode-ecoute.md). faster-whisper est une dépendance À PART
(tools/requirements-transcription.txt) : sans elle, l'application tourne
normalement et une écoute passe en erreur avec un message qui dit quoi
installer.

Réglages (config.py) : TRANSCRIPTION_MODELE, TRANSCRIPTION_THREADS. Le modèle
est téléchargé au premier usage (environ 1,6 Go pour large-v3-turbo) dans le
cache Hugging Face de l'utilisateur du service, ou TRANSCRIPTION_CACHE.

Appelé uniquement par tools/transcription_worker.py, dans un processus à part
en nice 19 : jamais depuis un worker FastAPI.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional


def indisponible() -> Optional[str]:
    """None si faster-whisper s'importe, sinon le message à afficher."""
    try:
        import faster_whisper  # noqa: F401
    except Exception as e:
        return (f"Transcription indisponible sur ce serveur — installer "
                f"tools/requirements-transcription.txt ({type(e).__name__}: {e}).")
    return None


def horodatage(secondes: float) -> str:
    s = int(secondes)
    h, reste = divmod(s, 3600)
    m, s = divmod(reste, 60)
    return f"[{h}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"


def transcrire(chemin: str, modele: str, threads: int = 1, vocabulaire: str = "") -> Dict[str, Any]:
    """Rend {texte, duree_audio, duree_traitement, segments}.

    `vocabulaire` : termes métier lus en base (noms de machines…), passés en
    amorce au modèle pour qu'il les écrive correctement.
    """
    from faster_whisper import WhisperModel

    t0 = time.perf_counter()
    m = WhisperModel(modele, device="cpu", compute_type="int8", cpu_threads=max(1, int(threads)),
                     download_root=os.getenv("TRANSCRIPTION_CACHE") or None)
    segments, info = m.transcribe(
        chemin, language="fr", beam_size=5, vad_filter=True,
        initial_prompt=vocabulaire or None,
    )
    lignes = []
    for s in segments:  # générateur paresseux : le calcul a lieu ici
        t = (s.text or "").strip()
        if t:
            lignes.append(f"{horodatage(s.start)} {t}")
    return {
        "texte": "\n".join(lignes),
        "duree_audio": float(getattr(info, "duration", 0) or 0),
        "duree_traitement": time.perf_counter() - t0,
        "segments": len(lignes),
    }
