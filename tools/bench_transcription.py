"""Bench de transcription locale — lot 0 du mode écoute (docs/reunions-mode-ecoute.md).

Mesure, sur la machine qui l'exécute (le VPS), ce que coûte la transcription
d'un enregistrement de réunion avec faster-whisper, pour plusieurs modèles :
durée de traitement, cœurs occupés, RAM pic, et projection pour 1 h de réunion.
Écrit la transcription de chaque modèle pour juger la qualité à la lecture.

Avec --sonde, interroge /healthz de MySifa pendant tout le bench : c'est ce qui
dit si une transcription en cours ralentit l'application.

Autonome : n'importe rien de MySifa, tourne dans un venv à part (jamais celui
de l'application). Chaque modèle passe dans un sous-processus, pour que la RAM
pic mesurée soit la sienne et pas celle du modèle précédent. Tout tourne en
nice 19 : le bench cède la main à MySifa.

    python3 bench_transcription.py reunion.m4a --sonde http://127.0.0.1:8000/healthz
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

MODELES_DEFAUT = "small,medium,large-v3-turbo"
OBJECTIF_1H_MIN = 90  # critère d'acceptation de la spec : 1 h de réunion en moins d'1 h 30


# ── Enfant : un modèle, une transcription ─────────────────────────────────────

def _enfant(args) -> None:
    from faster_whisper import WhisperModel

    t0 = time.perf_counter()
    modele = WhisperModel(args.modele, device="cpu", compute_type="int8",
                          cpu_threads=args.threads)
    chargement = time.perf_counter() - t0

    t1 = time.perf_counter()
    segments, info = modele.transcribe(
        args.audio, language="fr", beam_size=args.beam, vad_filter=True,
        initial_prompt=args.vocabulaire or None,
    )
    lignes = []
    for s in segments:  # générateur paresseux : c'est ici que le calcul a lieu
        m, sec = divmod(int(s.start), 60)
        lignes.append(f"[{m:02d}:{sec:02d}] {s.text.strip()}")
    transcription = time.perf_counter() - t1

    Path(args.sortie, f"{args.modele}.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    u = resource.getrusage(resource.RUSAGE_SELF)
    print(json.dumps({
        "modele": args.modele,
        "duree_audio": info.duration,
        "chargement": chargement,
        "transcription": transcription,
        "cpu": u.ru_utime + u.ru_stime,
        "ram_pic_mo": u.ru_maxrss / 1024,  # Linux : ru_maxrss en Ko
        "segments": len(lignes),
    }))


# ── Parent : contexte machine, sonde, tableau ─────────────────────────────────

def _meminfo() -> dict:
    infos = {}
    try:
        for ligne in Path("/proc/meminfo").read_text().splitlines():
            cle, val = ligne.split(":", 1)
            infos[cle] = int(val.split()[0]) / 1024 / 1024  # Ko → Go
    except Exception:
        pass
    return infos


class Sonde(threading.Thread):
    """Interroge une URL toutes les 2 s et garde les latences par phase."""

    def __init__(self, url: str):
        super().__init__(daemon=True)
        self.url = url
        self.phase = "repos"
        self.mesures: dict[str, list] = {}
        self.echecs: dict[str, int] = {}
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            phase, t0 = self.phase, time.perf_counter()
            try:
                with urllib.request.urlopen(self.url, timeout=5) as r:
                    r.read()
                self.mesures.setdefault(phase, []).append((time.perf_counter() - t0) * 1000)
            except Exception:
                self.echecs[phase] = self.echecs.get(phase, 0) + 1
            self._stop.wait(2)

    def arreter(self):
        self._stop.set()

    def resume(self, phase: str) -> str:
        m, e = self.mesures.get(phase, []), self.echecs.get(phase, 0)
        if not m:
            return f"aucune réponse ({e} échec(s))" if e else "—"
        txt = f"{statistics.median(m):.0f} / {max(m):.0f} ms"
        return txt + (f", {e} échec(s)" if e else "")


def _duree(s: float) -> str:
    m, sec = divmod(int(round(s)), 60)
    h, m = divmod(m, 60)
    return f"{h} h {m:02d}" if h else f"{m} min {sec:02d}"


def _parent(args) -> int:
    try:
        os.nice(19)
    except Exception:
        pass
    if not Path(args.audio).is_file():
        print(f"Fichier audio introuvable : {args.audio}")
        return 1
    try:
        import faster_whisper  # noqa: F401
    except Exception as e:  # une dépendance cassée lève autre chose qu'un module absent
        print(f"faster-whisper ne s'importe pas ({sys.executable}) : {type(e).__name__}: {e}")
        return 1
    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)

    mem = _meminfo()
    entete = [
        "# Bench transcription",
        "",
        f"- Machine : {os.cpu_count()} cœur(s), RAM {mem.get('MemTotal', 0):.1f} Go "
        f"(disponible {mem.get('MemAvailable', 0):.1f} Go), charge {os.getloadavg()[0]:.2f}",
        f"- Audio : {args.audio}",
        f"- Threads : {args.threads} · beam {args.beam} · int8 · VAD",
    ]
    print("\n".join(entete), flush=True)

    sonde = None
    if args.sonde:
        sonde = Sonde(args.sonde)
        sonde.start()
        print(f"Sonde {args.sonde} : 20 s de mesure au repos…", flush=True)
        time.sleep(20)

    resultats = []
    for nom in [m.strip() for m in args.modeles.split(",") if m.strip()]:
        print(f"→ {nom}…", flush=True)
        if sonde:
            sonde.phase = nom
        cmd = [sys.executable, __file__, args.audio, "--enfant", "--modele", nom,
               "--threads", str(args.threads), "--beam", str(args.beam),
               "--sortie", str(sortie)]
        if args.vocabulaire:
            cmd += ["--vocabulaire", args.vocabulaire]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            err = (p.stderr.strip().splitlines() or ["erreur inconnue"])[-1]
            print(f"  échec : {err}", flush=True)
            resultats.append({"modele": nom, "erreur": err})
            continue
        r = json.loads(p.stdout.strip().splitlines()[-1])
        resultats.append(r)
        print(f"  {_duree(r['transcription'])} pour {_duree(r['duree_audio'])} d'audio", flush=True)
    if sonde:
        sonde.phase = "fin"
        sonde.arreter()

    lignes = entete + [
        "",
        "| Modèle | Chargement | Transcription | Facteur | 1 h de réunion | Cœurs occupés | RAM pic | Sonde méd. / max | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resultats:
        if "erreur" in r:
            lignes.append(f"| {r['modele']} | — | échec : {r['erreur']} | | | | | | |")
            continue
        facteur = r["transcription"] / r["duree_audio"] if r["duree_audio"] else 0
        proj = facteur * 3600
        coeurs = r["cpu"] / (r["chargement"] + r["transcription"])
        verdict = "OK" if proj <= OBJECTIF_1H_MIN * 60 else "trop lent"
        lignes.append(
            f"| {r['modele']} | {r['chargement']:.0f} s | {_duree(r['transcription'])} | "
            f"{facteur:.2f} | {_duree(proj)} | {coeurs:.1f} | {r['ram_pic_mo']:.0f} Mo | "
            f"{sonde.resume(r['modele']) if sonde else '—'} | {verdict} |"
        )
    lignes += [
        "",
        f"Facteur = temps de transcription / durée de l'audio. Objectif : 1 h de réunion en moins de {OBJECTIF_1H_MIN} min.",
        "Le premier passage d'un modèle inclut son téléchargement dans « Chargement ».",
    ]
    if sonde:
        lignes.append(f"Sonde au repos (référence) : {sonde.resume('repos')}.")
    lignes.append(f"Transcriptions à relire : {sortie}/<modèle>.txt")

    rapport = "\n".join(lignes) + "\n"
    (sortie / "resultats.md").write_text(rapport, encoding="utf-8")
    print("\n" + rapport)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Bench de transcription locale (faster-whisper).")
    ap.add_argument("audio", help="Enregistrement de réunion (m4a, mp3, wav, webm…), 10 min conseillées")
    ap.add_argument("--modeles", default=MODELES_DEFAUT, help=f"Liste séparée par des virgules (défaut : {MODELES_DEFAUT})")
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                    help="Threads de calcul (défaut : la moitié des cœurs, le reste pour MySifa)")
    ap.add_argument("--beam", type=int, default=5, help="Largeur de faisceau : 1 = plus rapide, 5 = plus précis")
    ap.add_argument("--vocabulaire", default="", help="Termes métier à favoriser (noms de machines, clients…)")
    ap.add_argument("--sonde", default="", help="URL interrogée pendant le bench, ex. http://127.0.0.1:8000/healthz")
    ap.add_argument("--sortie", default="bench_transcription_resultats", help="Dossier des résultats")
    ap.add_argument("--enfant", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--modele", default="", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.enfant:
        _enfant(args)
        return 0
    return _parent(args)


if __name__ == "__main__":
    sys.exit(main())
