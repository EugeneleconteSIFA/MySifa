"""Socle commun aux deux imports de scans d'OF termines.

Le dossier source (U:\\Requia\\Scan\\OF SCANNES) appartient a quelqu'un d'autre.
**Rien n'y est jamais deplace, renomme ni supprime** : on lit, on envoie, on
note ce qui est parti. L'idempotence ne vient pas d'un rangement des fichiers
mais de deux garde-fous independants :

- **cote serveur**, une empreinte sha-256 du contenu, en index unique. Un
  fichier renomme ou passe du dossier 2025 au dossier 2026 reste le meme
  document et n'entre pas deux fois ;
- **cote poste**, un index local (JSON) qui evite de relire et de renvoyer des
  milliers de fichiers a chaque passage. Perdre cet index ne cree aucun
  doublon — il ne fait gagner que du temps.

Deux points d'entree l'utilisent :
    of_scans_import_initial.py    — la reprise complete, une fois
    of_scans_import_quotidien.py  — la passe du soir, tous les jours
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover
    print("Le module 'requests' est requis : pip install requests")
    sys.exit(2)


DOSSIER_DEFAUT = r"U:\Réquia\Scan\OF SCANNES"
URL_DEFAUT = "https://www.mysifa.com"
INDEX_DEFAUT = os.path.join(
    os.getenv("PROGRAMDATA") or os.path.expanduser("~"),
    "MySifa", "of_scans_index.json",
)


def log(msg: str) -> None:
    print("[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)


# ─── Index local ──────────────────────────────────────────────────────────────

def charger_index(chemin: str) -> dict:
    try:
        with open(chemin, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def ecrire_index(chemin: str, index: dict) -> None:
    """Ecriture atomique : une coupure ne doit pas laisser un index illisible."""
    try:
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        tmp = chemin + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False)
        os.replace(tmp, chemin)
    except OSError as exc:
        log("index local non ecrit (%s) — sans consequence sur les doublons." % exc)


def cle_index(racine: str, chemin: str) -> str:
    try:
        return os.path.relpath(chemin, racine).replace("\\", "/")
    except ValueError:
        return chemin.replace("\\", "/")


# ─── Parcours ─────────────────────────────────────────────────────────────────

def parcourir(racine: str, age_min: int = 0, modifie_depuis: float = 0.0) -> list:
    """PDF du dossier et de ses sous-dossiers (un par annee), tries.

    `age_min` ecarte les fichiers encore en cours d'ecriture par le copieur.
    `modifie_depuis` (timestamp) limite la passe quotidienne aux fichiers
    recents — le controle de doublon reste, lui, cote serveur.
    """
    trouves = []
    maintenant = time.time()
    for dossier, sous_dossiers, fichiers in os.walk(racine):
        # Les dossiers de service de l'ancien agent ne sont pas des sources.
        sous_dossiers[:] = [d for d in sous_dossiers if d not in ("_envoyes", "_echecs")]
        for nom in fichiers:
            if not nom.lower().endswith(".pdf"):
                continue
            chemin = os.path.join(dossier, nom)
            try:
                st = os.stat(chemin)
            except OSError:
                continue
            if age_min and (maintenant - st.st_mtime) < age_min:
                continue
            if modifie_depuis and st.st_mtime < modifie_depuis:
                continue
            trouves.append((chemin, st.st_mtime, st.st_size))
    trouves.sort(key=lambda t: (t[1], t[0]))
    return trouves


def empreinte_fichier(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as fh:
        for bloc in iter(lambda: fh.read(1024 * 256), b""):
            h.update(bloc)
    return h.hexdigest()


# ─── Envoi ────────────────────────────────────────────────────────────────────

def envoyer(chemin: str, racine: str, url: str, cle: str, timeout: int = 180) -> dict:
    with open(chemin, "rb") as fh:
        contenu = fh.read()
    if not contenu:
        raise ValueError("fichier vide")
    relatif = cle_index(racine, chemin)
    reponse = requests.post(
        url.rstrip("/") + "/api/bridge/of-scan",
        headers={"X-Api-Key": cle},
        files={"file": (os.path.basename(chemin), contenu, "application/pdf")},
        data={"fichier_origine": os.path.basename(chemin), "chemin_origine": relatif},
        timeout=timeout,
    )
    if reponse.status_code >= 400:
        try:
            detail = reponse.json().get("detail") or reponse.text[:200]
        except Exception:
            detail = reponse.text[:200]
        raise RuntimeError("HTTP %s — %s" % (reponse.status_code, detail))
    return reponse.json()


def importer(racine: str, url: str, cle: str, index_path: str, *,
             age_min: int = 0, modifie_depuis: float = 0.0,
             simulation: bool = False, pause: float = 0.0,
             max_fichiers: int = 0) -> dict:
    """Balaie `racine` et envoie ce qui n'est pas deja parti."""
    if not os.path.isdir(racine):
        raise SystemExit("Dossier introuvable : %s" % racine)

    index = charger_index(index_path)
    fichiers = parcourir(racine, age_min=age_min, modifie_depuis=modifie_depuis)
    log("%d PDF vus dans %s" % (len(fichiers), racine))

    bilan = {"vus": len(fichiers), "envoyes": 0, "doublons": 0,
             "deja_indexes": 0, "rattaches": 0, "a_rattacher": 0, "echecs": 0}
    echecs = []
    traites = 0

    for chemin, mtime, taille in fichiers:
        cle_fic = cle_index(racine, chemin)
        vu = index.get(cle_fic)
        # L'index local ne fait que raccourcir le travail : si le fichier n'a
        # ni change de taille ni de date, inutile de relire 300 Ko sur le reseau.
        if vu and vu.get("taille") == taille and abs((vu.get("mtime") or 0) - mtime) < 2:
            bilan["deja_indexes"] += 1
            continue

        if max_fichiers and traites >= max_fichiers:
            log("Limite de %d fichiers atteinte — relancer pour continuer." % max_fichiers)
            break

        if simulation:
            log("SIMULATION  %s" % cle_fic)
            traites += 1
            continue

        try:
            res = envoyer(chemin, racine, url, cle)
        except Exception as exc:
            bilan["echecs"] += 1
            echecs.append((cle_fic, str(exc)))
            log("ECHEC  %s : %s" % (cle_fic, exc))
            continue

        traites += 1
        if res.get("doublon"):
            bilan["doublons"] += 1
        else:
            bilan["envoyes"] += 1
            if res.get("statut") == "rattache":
                bilan["rattaches"] += 1
            else:
                bilan["a_rattacher"] += 1
        log("OK  %s -> %s" % (cle_fic, res.get("message") or res.get("statut")))

        index[cle_fic] = {"taille": taille, "mtime": mtime,
                          "empreinte": res.get("empreinte"),
                          "envoye_le": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
        # Sauvegarde reguliere : une reprise complete peut durer, et une
        # coupure ne doit pas faire tout recommencer.
        if traites % 25 == 0:
            ecrire_index(index_path, index)
        if pause:
            time.sleep(pause)

    if not simulation:
        ecrire_index(index_path, index)

    log("Bilan : %d envoye(s) dont %d rattache(s) et %d en file, "
        "%d doublon(s), %d deja vu(s), %d echec(s)."
        % (bilan["envoyes"], bilan["rattaches"], bilan["a_rattacher"],
           bilan["doublons"], bilan["deja_indexes"], bilan["echecs"]))
    if echecs:
        log("Fichiers en echec (a relancer) :")
        for nom, err in echecs[:20]:
            log("   - %s : %s" % (nom, err))
        if len(echecs) > 20:
            log("   ... et %d autre(s)." % (len(echecs) - 20))
    bilan["detail_echecs"] = echecs
    return bilan


def arguments_communs(parser):
    parser.add_argument("--dossier", default=os.getenv("OF_SCANS_DIR", DOSSIER_DEFAUT),
                        help="Dossier des scans (defaut : %s)" % DOSSIER_DEFAUT)
    parser.add_argument("--url", default=os.getenv("MYSIFA_URL", URL_DEFAUT))
    parser.add_argument("--cle", default=os.getenv("MYSIFA_API_KEY", ""),
                        help="Cle API portant le scope scan:write")
    parser.add_argument("--index", default=os.getenv("OF_SCANS_INDEX", INDEX_DEFAUT),
                        help="Index local des fichiers deja envoyes")
    parser.add_argument("--simulation", action="store_true",
                        help="Liste ce qui serait envoye, sans rien envoyer")
    return parser


def verifier_cle(cle: str) -> None:
    if not cle:
        raise SystemExit("Cle API manquante : --cle ou variable MYSIFA_API_KEY.")
