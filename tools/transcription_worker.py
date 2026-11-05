"""Réunions — mode écoute : traite les écoutes en attente (transcription, brief).

Lancé par main.py (`_boucle_ecoutes`), dans un processus séparé en nice 19 :
une transcription occupe un cœur pendant l'équivalent de la durée de la
réunion, elle ne doit jamais tourner dans un worker FastAPI ni ralentir une
saisie opérateur. Se lance aussi à la main pour diagnostiquer :

    cd /home/sifa/production-saas-v1 && venv/bin/python tools/transcription_worker.py

Un seul traitement à la fois sur la machine : prod et v1 partagent le CPU, donc
le verrou TRANSCRIPTION_VERROU (flock, libéré par le système si le processus
meurt). Verrou déjà pris : sortie immédiate, code 75 — la boucle réessaiera.

Un passage : arrête les écoutes muettes, reprend celles qu'un redémarrage a
coupées, purge ce qui a fait son temps, puis traite toute la file.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402  — d'abord, toujours (CLAUDE.md)
from database import get_db  # noqa: E402

from config import (ECOUTE_DIR, ECOUTE_RETENTION_JOURS, ECOUTE_SILENCE_MIN,  # noqa: E402
                    TRANSCRIPTION_MODELE, TRANSCRIPTION_THREADS, TRANSCRIPTION_VERROU)
from app.services import ia_usage  # noqa: E402
from app.services import reunion_ecoute as ec  # noqa: E402
from app.services import reunion_ecoute_ia as eia  # noqa: E402
from app.services import transcription as tr  # noqa: E402

VERROU_PRIS = 75


def _log(msg: str) -> None:
    print(f"[MySifa] écoute : {msg}", flush=True)


def _verrou():
    import fcntl
    f = open(TRANSCRIPTION_VERROU, "a+")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def _vocabulaire(conn) -> str:
    """Noms des machines actives : écrits correctement par le modèle."""
    try:
        rows = conn.execute("SELECT nom FROM machines WHERE actif=1 ORDER BY nom").fetchall()
        return ", ".join(str(r[0]) for r in rows if r[0])
    except Exception:
        return ""


def _contexte(conn, e: dict) -> dict:
    try:
        personnes = [r[0] for r in conn.execute(
            "SELECT nom FROM users WHERE actif=1 AND TRIM(COALESCE(nom,''))<>'' ORDER BY nom").fetchall()]
    except Exception:
        personnes = []
    voc = _vocabulaire(conn)
    return {
        "date": (e.get("demarre_le") or "")[:10],
        "type": (e.get("type") or {}).get("libelle") or "",
        "titre": e.get("titre") or "",
        "personnes": personnes[:300],
        "termes": [t.strip() for t in voc.split(",") if t.strip()],
        "manquants": bool(e.get("morceaux_manquants")),
    }


def _auteur(conn, e: dict) -> dict:
    if e.get("demarre_par_id"):
        r = conn.execute("SELECT id, nom, email, role FROM users WHERE id=?",
                         (e["demarre_par_id"],)).fetchone()
        if r:
            return dict(r)
    return {"nom": e.get("demarre_par") or "Automatique"}


def _prevenir(e: dict, titre: str, corps: str) -> None:
    """Push à la personne qui a lancé l'écoute ; sans effet si rien n'est réglé."""
    if not e.get("demarre_par_id"):
        return
    try:
        from app.routers.push import send_push_safe
        send_push_safe(e["demarre_par_id"], title=titre, body=corps[:120],
                       url=f"/reunions?ecoute={e['id']}", tag=f"ecoute-{e['id']}")
    except Exception:
        pass


def _transcrire(conn, e: dict) -> bool:
    manque = tr.indisponible()
    if manque:
        ec.echec(conn, e["id"], manque)
        return False
    chemin = ec.assembler(ECOUTE_DIR, e["id"], e.get("mime") or "")
    if not chemin:
        ec.echec(conn, e["id"], "Audio introuvable sur le serveur.")
        return False
    ec.debut_transcription(conn, e["id"], TRANSCRIPTION_MODELE)
    _log(f"n° {e['id']} : transcription ({TRANSCRIPTION_MODELE}, {TRANSCRIPTION_THREADS} thread(s))")
    try:
        r = tr.transcrire(chemin, TRANSCRIPTION_MODELE, TRANSCRIPTION_THREADS, _vocabulaire(conn))
    except Exception as exc:
        ec.echec(conn, e["id"], f"Transcription en échec : {type(exc).__name__}: {exc}")
        return False
    ec.poser_transcription(conn, ECOUTE_DIR, e["id"], r["texte"], r["duree_traitement"], r["duree_audio"])
    _log(f"n° {e['id']} : {r['segments']} segment(s), {r['duree_audio']:.0f} s d'audio "
         f"en {r['duree_traitement']:.0f} s")
    return True


def _structurer(conn, e: dict) -> None:
    complet = ec.ecoute(conn, e["id"])
    with ia_usage.Suivi(_auteur(conn, complet), "reunion", module="reunions") as suivi:
        suivi.application = "Réunions"
        try:
            brief = eia.structurer(complet.get("transcription") or "", _contexte(conn, complet))
        except eia.ReunionIaErreur as exc:
            suivi.statut, suivi.erreur = "err", str(exc)[:300]
            ec.echec(conn, e["id"], str(exc))
            return
    ec.poser_proposition(conn, e["id"], brief)
    _log(f"n° {e['id']} : brief proposé ({len(brief['actions'])} action(s))")


def passage() -> int:
    """Traite toute la file. Rend le nombre d'écoutes traitées."""
    with get_db() as conn:
        n = ec.clore_silencieuses(conn, ECOUTE_DIR, ECOUTE_SILENCE_MIN)
        if n:
            _log(f"{n} écoute(s) sans nouvel audio arrêtée(s) d'office")
        ec.reprendre_interrompues(conn)
        p = ec.purger(conn, ECOUTE_DIR, ECOUTE_RETENTION_JOURS)
        if p["transcriptions"] or p["audios"]:
            _log(f"purge : {p['transcriptions']} transcription(s), {p['audios']} audio(s)")
        traitees = 0
        while True:
            e = ec.a_traiter(conn)
            if not e:
                break
            if e["statut"] == ec.A_TRANSCRIRE and not _transcrire(conn, e):
                _prevenir(e, "Écoute en erreur", "La transcription n'a pas abouti.")
                traitees += 1
                continue
            e = ec.ecoute(conn, e["id"], avec_texte=False)
            if e["statut"] == ec.A_STRUCTURER:
                _structurer(conn, e)
                e = ec.ecoute(conn, e["id"], avec_texte=False)
            if e["statut"] == ec.PROPOSITION:
                _prevenir(e, "Brief de réunion prêt", e.get("titre") or "À relire et valider.")
            elif e["statut"] == ec.ERREUR:
                _prevenir(e, "Écoute en erreur", e.get("erreur") or "")
            traitees += 1
        return traitees


def main() -> int:
    verrou = _verrou()
    if verrou is None:
        return VERROU_PRIS
    try:
        t0 = time.monotonic()
        n = passage()
        if n:
            _log(f"{n} écoute(s) traitée(s) en {time.monotonic() - t0:.0f} s")
        return 0
    finally:
        verrou.close()


if __name__ == "__main__":
    sys.exit(main())
