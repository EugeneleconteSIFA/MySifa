"""Agent local — depot des OF termines scannes dans MySifa.

Le copieur de l'atelier depose ses scans dans un dossier reseau. Cet agent
surveille ce dossier, envoie chaque nouveau PDF a MySifa, puis DEPLACE le
fichier dans un sous-dossier `_envoyes/`. Il ne supprime jamais rien : en cas
de doute, l'original reste sur le partage.

Le serveur decide de tout — lecture du numero d'OF, rattachement a la
reference produit, mise en file de rattachement manuel. L'agent n'a aucune
connaissance metier ; c'est ce qui permet de faire evoluer la regle sans
retoucher le poste.

Meme authentification que le pont Access : une cle API (header X-Api-Key)
portant le scope `scan:write`.

Usage :
    python agent_scan_of.py --dossier "\\\\serveur\\scans\\OF" \\
                            --url https://www.mysifa.com \\
                            --cle CLE_API

Options utiles :
    --intervalle 60     secondes entre deux balayages (defaut 60)
    --une-passe         un seul balayage puis sortie (pour le planificateur
                        de taches Windows plutot qu'un service resident)
    --age-min 15        n'envoie un fichier que s'il n'a pas bouge depuis N
                        secondes — evite d'attraper un PDF encore en cours
                        d'ecriture par le copieur (defaut 15)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover - message d'installation
    print("Le module 'requests' est requis : pip install requests")
    sys.exit(2)


ENVOYES = "_envoyes"
ECHECS = "_echecs"


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def candidats(dossier: str, age_min: int) -> list:
    """PDF stables du dossier, hors sous-dossiers de service."""
    out = []
    maintenant = time.time()
    try:
        noms = os.listdir(dossier)
    except OSError as exc:
        log(f"Dossier illisible : {exc}")
        return out
    for nom in sorted(noms):
        chemin = os.path.join(dossier, nom)
        if not os.path.isfile(chemin):
            continue
        if not nom.lower().endswith(".pdf"):
            continue
        try:
            # Un fichier encore en cours d'ecriture par le copieur serait
            # envoye tronque : on attend qu'il ne bouge plus.
            if maintenant - os.path.getmtime(chemin) < age_min:
                continue
        except OSError:
            continue
        out.append(chemin)
    return out


def envoyer(chemin: str, url: str, cle: str, timeout: int = 120) -> dict:
    with open(chemin, "rb") as fh:
        contenu = fh.read()
    if not contenu:
        raise ValueError("fichier vide")
    reponse = requests.post(
        url.rstrip("/") + "/api/bridge/of-scan",
        headers={"X-Api-Key": cle},
        files={"file": (os.path.basename(chemin), contenu, "application/pdf")},
        data={"fichier_origine": os.path.basename(chemin)},
        timeout=timeout,
    )
    if reponse.status_code >= 400:
        detail = ""
        try:
            detail = reponse.json().get("detail") or reponse.text[:200]
        except Exception:
            detail = reponse.text[:200]
        raise RuntimeError(f"HTTP {reponse.status_code} — {detail}")
    return reponse.json()


def deplacer(chemin: str, sous_dossier: str) -> None:
    """Deplace sans jamais ecraser : un homonyme recoit un suffixe horodate."""
    cible_dir = os.path.join(os.path.dirname(chemin), sous_dossier)
    os.makedirs(cible_dir, exist_ok=True)
    base = os.path.basename(chemin)
    cible = os.path.join(cible_dir, base)
    if os.path.exists(cible):
        racine, ext = os.path.splitext(base)
        cible = os.path.join(cible_dir, f"{racine}_{datetime.now():%Y%m%d_%H%M%S}{ext}")
    shutil.move(chemin, cible)


def passe(dossier: str, url: str, cle: str, age_min: int) -> tuple:
    fichiers = candidats(dossier, age_min)
    if not fichiers:
        return 0, 0
    ok, ko = 0, 0
    for chemin in fichiers:
        nom = os.path.basename(chemin)
        try:
            res = envoyer(chemin, url, cle)
        except Exception as exc:
            ko += 1
            log(f"ECHEC {nom} : {exc}")
            # Un echec reseau ne doit pas bloquer le dossier a la passe
            # suivante ; on isole le fichier pour qu'un humain le regarde.
            try:
                deplacer(chemin, ECHECS)
            except OSError as move_exc:
                log(f"  (fichier laisse en place : {move_exc})")
            continue
        ok += 1
        log(f"OK {nom} — {res.get('message') or res.get('statut')}")
        try:
            deplacer(chemin, ENVOYES)
        except OSError as exc:
            log(f"  ATTENTION {nom} envoye mais non deplace ({exc}) : "
                f"il repartira a la prochaine passe.")
    return ok, ko


def main() -> int:
    ap = argparse.ArgumentParser(description="Depose les OF scannes dans MySifa.")
    ap.add_argument("--dossier", required=True, help="Dossier reseau surveille")
    ap.add_argument("--url", default=os.getenv("MYSIFA_URL", "https://www.mysifa.com"))
    ap.add_argument("--cle", default=os.getenv("MYSIFA_API_KEY", ""))
    ap.add_argument("--intervalle", type=int, default=60)
    ap.add_argument("--age-min", type=int, default=15)
    ap.add_argument("--une-passe", action="store_true")
    args = ap.parse_args()

    if not args.cle:
        log("Cle API manquante (--cle ou variable MYSIFA_API_KEY).")
        return 2
    if not os.path.isdir(args.dossier):
        log(f"Dossier introuvable : {args.dossier}")
        return 2

    log(f"Surveillance de {args.dossier} vers {args.url}")
    if args.une_passe:
        ok, ko = passe(args.dossier, args.url, args.cle, args.age_min)
        log(f"Passe terminee : {ok} envoye(s), {ko} echec(s).")
        return 1 if ko else 0

    while True:
        try:
            passe(args.dossier, args.url, args.cle, args.age_min)
        except KeyboardInterrupt:
            log("Arret demande.")
            return 0
        except Exception as exc:
            log(f"Erreur inattendue (on continue) : {exc}")
        time.sleep(max(10, args.intervalle))


if __name__ == "__main__":
    sys.exit(main())
