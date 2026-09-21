"""Socle commun aux deux imports de devis commerciaux.

Le dossier source (U:\\PSEGARD\\Devis etiquettes) appartient aux commerciaux.
**Rien n'y est jamais deplace, renomme ni supprime** : on lit, on envoie, on
note ce qui est parti. L'idempotence ne vient pas d'un rangement des fichiers
mais de deux garde-fous independants :

- **cote serveur**, une empreinte sha-256 du contenu, en index unique. Un
  devis renomme, ou recopie dans le dossier de l'annee suivante, reste le meme
  document et n'entre pas deux fois ;
- **cote poste**, un index local (JSON) qui evite de relire et de renvoyer des
  centaines de classeurs a chaque passage. Perdre cet index ne cree aucun
  doublon — il ne fait gagner que du temps.

L'agent n'a AUCUNE connaissance metier : il ne sait pas lire un devis, ne sait
pas ce qu'est une vitesse devisee, ne decide d'aucun rattachement. Il envoie le
fichier, le serveur lit et decide. Corriger la lecture d'un devis ne demande
donc jamais de redeployer quoi que ce soit sur les postes.

Deux points d'entree l'utilisent :
    devis_import_initial.py    — la reprise complete, une fois
    devis_import_quotidien.py  — la passe du soir, tous les jours
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover
    print("Le module 'requests' est requis : pip install requests")
    sys.exit(2)


DOSSIER_DEFAUT = r"U:\PSEGARD\Devis étiquettes"
URL_DEFAUT = "https://www.mysifa.com"
INDEX_DEFAUT = os.path.join(
    os.getenv("PROGRAMDATA") or os.path.expanduser("~"),
    "MySifa", "devis_index.json",
)

# Ce que le serveur sait lire. Les .xlsm sont acceptes : le modele maison est
# un classeur a macros chez certains commerciaux.
EXTENSIONS = (".xlsx", ".xlsm", ".xls", ".pdf", ".png", ".jpg", ".jpeg")

# Dossiers du partage qui ne contiennent pas de devis client : modeles vierges,
# referentiels de prix matiere, et la base de travail « marge brute » qui
# reprend en seconde copie des devis deja ranges par client. Laisses entrer,
# ils peupleraient la vue Rentabilite de lignes qui ne sont pas des affaires.
# La comparaison porte sur le nom d'un segment de chemin, casse et espaces
# indifferents ; `--exclure` remplace cette liste.
DOSSIERS_IGNORES = ("_modele", "2 parametres devis", "1111 - base marge brute")


def _pliable(nom: str) -> str:
    """Nom de dossier comparable : sans accent, sans casse, espaces reduits."""
    sans_accent = unicodedata.normalize("NFKD", str(nom or ""))
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    return " ".join(sans_accent.casefold().split())


# Date du devis lue dans le nom du fichier. Surtout pas « quatre chiffres
# quelque part » : les noms sont pleins de references matiere qui y
# ressembleraient (« 1408-22 », « 2021-40 », « 2288-50g », « 2030-28 »). Seule
# une date complete jj-mm-aaaa compte, et elle ne doit pas etre collee a
# d'autres chiffres.
_DATE_NOM_RE = re.compile(r"(?<!\d)(\d{2})[-. _](\d{2})[-. _](\d{4}|\d{2})(?!\d)")


def annee_du_nom(nom: str):
    """Annee de la derniere date complete lisible dans le nom, sinon None."""
    annee = None
    for m in _DATE_NOM_RE.finditer(str(nom or "")):
        jour, mois, an = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (1 <= jour <= 31 and 1 <= mois <= 12):
            continue
        if an < 100:
            an += 2000
        if 2000 <= an <= 2099:
            annee = an
    return annee


# Fichiers de travail d'Excel : « ~$devis.xlsx » est un verrou de 165 octets
# ecrit pendant qu'un classeur est ouvert, pas un devis.
_PREFIXES_IGNORES = ("~$", ".~")


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

_ANNEE_DOSSIER_RE = re.compile(r"(\d{4})")


def _annee_du_dossier(nom: str):
    """Annee lue dans un nom de sous-dossier (« Devis 2026 » -> 2026).

    Le motif n'est pas ancre en tete, contrairement aux scans d'OF : les
    commerciaux nomment « Devis 2026 » aussi bien que « 2026 ». Une annee
    trouvee n'importe ou dans le nom vaut mieux qu'un dossier ecarte a tort —
    et un nom sans annee n'est jamais ecarte.
    """
    for m in _ANNEE_DOSSIER_RE.finditer(str(nom or "")):
        annee = int(m.group(1))
        if 1990 <= annee <= 2099:
            return annee
    return None


def parcourir(racine: str, age_min: int = 0, modifie_depuis: float = 0.0,
              annee_min: int = 0, exclure=DOSSIERS_IGNORES,
              annee_devis_min: int = 0) -> list:
    """Devis du dossier et de ses sous-dossiers, tries du plus ancien au plus recent.

    `age_min` ecarte les fichiers encore en cours d'ecriture — un classeur
    copie sur le reseau et envoye a mi-copie arrive tronque, et un classeur
    tronque produit une lecture fausse plutot qu'une erreur franche.
    `modifie_depuis` limite la passe quotidienne aux fichiers recents.
    `annee_min` ecarte les sous-dossiers d'annee anterieurs : on se fie au NOM
    du dossier, pas a la date des fichiers, parce qu'une archive recopiee porte
    la date de la copie et non celle du devis. Les fichiers poses a la racine
    sont toujours pris.
    `exclure` ecarte des dossiers par leur nom, a n'importe quelle profondeur.
    `annee_devis_min` ecarte les devis anterieurs a cette annee. Le partage
    n'est pas range par millesime mais par client : l'annee se lit donc dans le
    nom du fichier, ou l'usage maison est de terminer par la date du devis. A
    defaut de date lisible, on se rabat sur la date du fichier.
    """
    trouves = []
    maintenant = time.time()
    racine_abs = os.path.abspath(racine)
    exclus = {_pliable(x) for x in (exclure or ())}
    # Seuil de repli : le 1er janvier de l'annee demandee.
    seuil_mtime = (time.mktime((annee_devis_min, 1, 1, 0, 0, 0, 0, 1, -1))
                   if annee_devis_min else 0.0)
    for dossier, sous_dossiers, fichiers in os.walk(racine):
        if exclus:
            # Elaguer avant de descendre : os.walk ne visitera pas ce qui sort
            # de `sous_dossiers`, donc un dossier ecarte ne coute meme pas la
            # lecture de son contenu sur le reseau.
            sous_dossiers[:] = [d for d in sous_dossiers if _pliable(d) not in exclus]
            if _pliable(os.path.basename(dossier)) in exclus:
                continue
        if annee_min and os.path.abspath(dossier) == racine_abs:
            gardes = []
            for d in sous_dossiers:
                annee = _annee_du_dossier(d)
                if annee is not None and annee < annee_min:
                    continue
                gardes.append(d)
            sous_dossiers[:] = gardes
        for nom in fichiers:
            if nom.startswith(_PREFIXES_IGNORES):
                continue
            if not nom.lower().endswith(EXTENSIONS):
                continue
            chemin = os.path.join(dossier, nom)
            try:
                st = os.stat(chemin)
            except OSError:
                continue
            if not st.st_size:
                continue
            if age_min and (maintenant - st.st_mtime) < age_min:
                continue
            if modifie_depuis and st.st_mtime < modifie_depuis:
                continue
            if annee_devis_min:
                annee = annee_du_nom(nom)
                if annee is not None:
                    if annee < annee_devis_min:
                        continue
                elif st.st_mtime < seuil_mtime:
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

_MIMES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def envoyer(chemin: str, racine: str, url: str, cle: str, timeout: int = 180) -> dict:
    with open(chemin, "rb") as fh:
        contenu = fh.read()
    if not contenu:
        raise ValueError("fichier vide")
    relatif = cle_index(racine, chemin)
    ext = os.path.splitext(chemin)[1].lower()
    try:
        date_fichier = datetime.fromtimestamp(
            os.path.getmtime(chemin)).strftime("%Y-%m-%dT%H:%M:%S")
    except OSError:
        date_fichier = ""
    reponse = requests.post(
        url.rstrip("/") + "/api/bridge/devis",
        headers={"X-Api-Key": cle},
        files={"file": (os.path.basename(chemin), contenu,
                        _MIMES.get(ext, "application/octet-stream"))},
        data={"fichier_origine": os.path.basename(chemin),
              "chemin_origine": relatif, "date_fichier": date_fichier},
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
             age_min: int = 0, modifie_depuis: float = 0.0, annee_min: int = 0,
             simulation: bool = False, pause: float = 0.0,
             max_fichiers: int = 0, exclure=DOSSIERS_IGNORES,
             annee_devis_min: int = 0) -> dict:
    """Balaie `racine` et envoie ce qui n'est pas deja parti."""
    if not os.path.isdir(racine):
        raise SystemExit("Dossier introuvable : %s" % racine)

    index = charger_index(index_path)
    fichiers = parcourir(racine, age_min=age_min, modifie_depuis=modifie_depuis,
                         annee_min=annee_min, exclure=exclure,
                         annee_devis_min=annee_devis_min)
    log("%d devis vus dans %s" % (len(fichiers), racine))

    bilan = {"vus": len(fichiers), "envoyes": 0, "doublons": 0,
             "deja_indexes": 0, "a_verifier": 0, "sans_reserve": 0, "echecs": 0}
    echecs = []
    a_verifier = []
    traites = 0

    for chemin, mtime, taille in fichiers:
        cle_fic = cle_index(racine, chemin)
        vu = index.get(cle_fic)
        # L'index local ne fait que raccourcir le travail : si le fichier n'a
        # ni change de taille ni de date, inutile de relire 2 Mo sur le reseau.
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
            if res.get("a_verifier"):
                bilan["a_verifier"] += 1
                a_verifier.append((cle_fic, res.get("message") or ""))
            else:
                bilan["sans_reserve"] += 1
        log("OK  %s -> %s" % (cle_fic, res.get("message") or res.get("statut")))

        index[cle_fic] = {"taille": taille, "mtime": mtime,
                          "empreinte": res.get("empreinte"),
                          "envoye_le": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
        if traites % 25 == 0:
            ecrire_index(index_path, index)
        if pause:
            time.sleep(pause)

    if not simulation:
        ecrire_index(index_path, index)

    log("Bilan : %d envoye(s) dont %d sans reserve et %d a verifier, "
        "%d doublon(s), %d deja vu(s), %d echec(s)."
        % (bilan["envoyes"], bilan["sans_reserve"], bilan["a_verifier"],
           bilan["doublons"], bilan["deja_indexes"], bilan["echecs"]))
    if a_verifier:
        log("Devis a verifier dans MyProd > Rentabilite > Devis :")
        for nom, motif in a_verifier[:20]:
            log("   - %s : %s" % (nom, motif))
        if len(a_verifier) > 20:
            log("   ... et %d autre(s)." % (len(a_verifier) - 20))
    if echecs:
        log("Fichiers en echec (a relancer) :")
        for nom, err in echecs[:20]:
            log("   - %s : %s" % (nom, err))
        if len(echecs) > 20:
            log("   ... et %d autre(s)." % (len(echecs) - 20))
    bilan["detail_echecs"] = echecs
    bilan["detail_a_verifier"] = a_verifier
    return bilan


def arguments_communs(parser):
    parser.add_argument("--dossier", default=os.getenv("DEVIS_DIR", DOSSIER_DEFAUT),
                        help="Dossier des devis (defaut : %s)" % DOSSIER_DEFAUT)
    parser.add_argument("--url", default=os.getenv("MYSIFA_URL", URL_DEFAUT))
    parser.add_argument("--cle", default=os.getenv("MYSIFA_API_KEY", ""),
                        help="Cle API portant le scope devis:write")
    parser.add_argument("--index", default=os.getenv("DEVIS_INDEX", INDEX_DEFAUT),
                        help="Index local des fichiers deja envoyes")
    parser.add_argument("--simulation", action="store_true",
                        help="Liste ce qui serait envoye, sans rien envoyer")
    parser.add_argument("--exclure", default=",".join(DOSSIERS_IGNORES),
                        help="Dossiers a ne pas lire, separes par des virgules "
                             "(defaut : %s). « aucun » pour tout lire — "
                             "PowerShell n'accepte pas une chaine vide en "
                             "argument." % ", ".join(DOSSIERS_IGNORES))
    parser.add_argument("--depuis-annee", type=int, default=0, dest="depuis_annee",
                        help="Ignorer les devis anterieurs a cette annee "
                             "(0 = tout). L'annee est lue dans le nom du "
                             "fichier, a defaut dans sa date.")
    return parser


def dossiers_exclus(valeur: str) -> tuple:
    """Liste passee en ligne de commande -> tuple de noms de dossiers.

    « aucun » vide la liste : PowerShell avale les chaines vides passees en
    argument (`--exclure ""` fait echouer argparse), il faut donc un mot.
    """
    texte = str(valeur or "").strip()
    if _pliable(texte) in ("", "aucun", "rien"):
        return ()
    return tuple(x.strip() for x in texte.split(",") if x.strip())


def verifier_cle(cle: str) -> None:
    if not cle:
        raise SystemExit("Cle API manquante : --cle ou variable MYSIFA_API_KEY.")
