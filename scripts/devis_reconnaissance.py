"""Reconnaissance du dossier des devis — lecture seule, sans reseau, sans cle API.

POURQUOI CE SCRIPT EXISTE SEPAREMENT. Deux decisions attendent une reponse que
seul le vrai dossier peut donner :

  1. l'agent quotidien ne ramasse que l'annee en cours, en se fiant au NOM des
     sous-dossiers. Si l'arborescence n'est pas rangee par annee, ce filtre
     ecarte tout, ou n'ecarte rien — dans les deux cas silencieusement ;
  2. quand un devis ne porte pas de nom de client lisible, faut-il le deduire
     du dossier qui le contient ? La reponse depend de ce que contiennent ces
     dossiers, et de rien d'autre.

Ce script n'envoie rien, n'ecrit rien dans le dossier, ne demande pas de cle et
n'a pas besoin que le serveur soit a jour. Il se lance AVANT tout deploiement,
et sa sortie repond aux deux questions d'un coup.

    python devis_reconnaissance.py
    python devis_reconnaissance.py --dossier "\\\\serveur\\PSEGARD\\Devis etiquettes"
    python devis_reconnaissance.py --rapport reconnaissance.txt

Le rapport est volontairement court : des compteurs, la forme de l'arbre, et un
echantillon de chemins reels. Lister des milliers de fichiers ne dirait rien de
plus que leur nombre.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

DOSSIER_DEFAUT = r"U:\PSEGARD\Devis étiquettes"

EXTENSIONS = (".xlsx", ".xlsm", ".xls", ".pdf", ".png", ".jpg", ".jpeg")
_PREFIXES_IGNORES = ("~$", ".~")

_ANNEE_RE = re.compile(r"(\d{4})")


def _annee_du_dossier(nom):
    """Meme lecture que l'agent : une annee plausible n'importe ou dans le nom."""
    for m in _ANNEE_RE.finditer(str(nom or "")):
        annee = int(m.group(1))
        if 1990 <= annee <= 2099:
            return annee
    return None


_MOIS = ("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
         "aout", "septembre", "octobre", "novembre", "decembre",
         "jan", "fev", "avr", "juil", "sept", "oct", "nov", "dec")


def _sans_accents(txt):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(txt or ""))
                   if unicodedata.category(c) != "Mn")


def _est_date(nom):
    """« 2026 », « Devis 2025 », « 03 - Mars », « T1 » : une date, pas un client."""
    if nom == "(racine)":
        return False
    brut = _sans_accents(nom).lower().strip()
    if _annee_du_dossier(brut) is not None:
        return True
    if any(m in brut for m in _MOIS):
        return True
    # Un nom purement numerique court (« 01 », « 2 ») est un rang, pas un nom.
    noyau = re.sub(r"[^a-z0-9]", "", brut)
    if noyau.isdigit() and len(noyau) <= 2:
        return True
    if re.fullmatch(r"t[1-4]|s[0-5]?\d", noyau or ""):
        return True
    return False


class Sortie(object):
    """Ecrit a l'ecran et, si demande, dans un fichier.

    La console Windows n'est pas toujours en UTF-8 et les dossiers des
    commerciaux portent des accents : sans repli, le script mourrait sur un
    `print`, ce qui serait un comble pour un outil de diagnostic.
    """

    def __init__(self, chemin=None):
        self.fh = open(chemin, "w", encoding="utf-8") if chemin else None

    def __call__(self, txt=""):
        try:
            print(txt)
        except UnicodeEncodeError:
            enc = sys.stdout.encoding or "ascii"
            print(txt.encode(enc, "replace").decode(enc, "replace"))
        if self.fh:
            self.fh.write(txt + "\n")

    def fermer(self):
        if self.fh:
            self.fh.close()


def analyser(racine):
    """Un seul parcours, tout ce qu'on veut savoir en sortant."""
    racine_abs = os.path.abspath(racine)
    infos = {
        "fichiers": [],          # (relatif, taille, mtime)
        "extensions": Counter(),
        "verrous": 0,            # ~$ d'Excel
        "vides": 0,
        "autres_ext": Counter(),
        "profondeurs": Counter(),
        "dossiers_racine": {},   # nom -> compteurs
        "dossiers_vus": 0,
        "erreurs": [],
    }

    for dossier, sous_dossiers, fichiers in os.walk(racine, onerror=infos["erreurs"].append):
        infos["dossiers_vus"] += 1
        rel_dossier = os.path.relpath(dossier, racine_abs)
        if rel_dossier == ".":
            rel_dossier = ""
        segments = [s for s in rel_dossier.replace("\\", "/").split("/") if s]
        premier = segments[0] if segments else "(racine)"
        infos["dossiers_racine"].setdefault(
            premier, {"devis": 0, "profondeur_max": 0, "sous_dossiers": set()})
        if len(segments) > 1:
            infos["dossiers_racine"][premier]["sous_dossiers"].add(segments[1])

        for nom in fichiers:
            if nom.startswith(_PREFIXES_IGNORES):
                infos["verrous"] += 1
                continue
            ext = os.path.splitext(nom)[1].lower()
            if ext not in EXTENSIONS:
                infos["autres_ext"][ext or "(sans extension)"] += 1
                continue
            chemin = os.path.join(dossier, nom)
            try:
                st = os.stat(chemin)
            except OSError as exc:
                infos["erreurs"].append(exc)
                continue
            if not st.st_size:
                infos["vides"] += 1
                continue
            rel = os.path.relpath(chemin, racine_abs).replace("\\", "/")
            infos["fichiers"].append((rel, st.st_size, st.st_mtime))
            infos["extensions"][ext] += 1
            infos["profondeurs"][len(segments)] += 1
            d = infos["dossiers_racine"][premier]
            d["devis"] += 1
            d["profondeur_max"] = max(d["profondeur_max"], len(segments))

    infos["fichiers"].sort(key=lambda t: t[2], reverse=True)
    return infos


def rapport(racine, infos, ecrire, echantillon=15):
    annee_courante = datetime.now().year
    total = len(infos["fichiers"])

    ecrire("=" * 72)
    ecrire("RECONNAISSANCE — %s" % racine)
    ecrire("%s · lecture seule, rien n'a ete modifie" %
           datetime.now().strftime("%d/%m/%Y %H:%M"))
    ecrire("=" * 72)

    ecrire("")
    ecrire("1. CE QUE CONTIENT LE DOSSIER")
    ecrire("   %d dossier(s) parcouru(s), %d devis exploitables." %
           (infos["dossiers_vus"], total))
    if not total:
        ecrire("   AUCUN fichier lisible. Verifier le chemin, ou les droits du")
        ecrire("   compte qui lance ce script (une tache planifiee ne voit pas")
        ecrire("   les lecteurs mappes d'une session ouverte : preferer le")
        ecrire("   chemin UNC complet).")
    for ext, n in infos["extensions"].most_common():
        ecrire("     %-8s %6d" % (ext, n))
    if infos["autres_ext"]:
        ecrire("   Ignores (extension non lue par le serveur) :")
        for ext, n in infos["autres_ext"].most_common(8):
            ecrire("     %-16s %6d" % (ext, n))
    if infos["verrous"]:
        ecrire("   %d verrou(s) Excel « ~$ » ignore(s) — normal, des classeurs"
               " sont ouverts." % infos["verrous"])
    if infos["vides"]:
        ecrire("   %d fichier(s) de 0 octet ignore(s)." % infos["vides"])

    ecrire("")
    ecrire("2. LA FORME DE L'ARBRE  (repond au filtre « annee en cours »)")
    if not infos["profondeurs"]:
        ecrire("   Rien a mesurer.")
    else:
        for prof in sorted(infos["profondeurs"]):
            libelle = "a la racine" if prof == 0 else "%d niveau(x) sous la racine" % prof
            ecrire("     %-28s %6d devis" % (libelle, infos["profondeurs"][prof]))

    ecrire("")
    ecrire("   Premier niveau, dossier par dossier :")
    lignes = sorted(
        ((nom, d) for nom, d in infos["dossiers_racine"].items() if d["devis"] or nom != "(racine)"),
        key=lambda x: -x[1]["devis"])
    avec_annee = sans_annee = 0
    gardes = ecartes = 0
    for nom, d in lignes[:40]:
        annee = _annee_du_dossier(nom) if nom != "(racine)" else None
        if nom == "(racine)":
            verdict = "toujours pris (fichiers a la racine)"
        elif annee is None:
            verdict = "PAS D'ANNEE LUE -> toujours pris"
            sans_annee += 1
            gardes += d["devis"]
        elif annee < annee_courante:
            verdict = "annee %d -> ECARTE par la passe quotidienne" % annee
            avec_annee += 1
            ecartes += d["devis"]
        else:
            verdict = "annee %d -> pris" % annee
            avec_annee += 1
            gardes += d["devis"]
        ecrire("     %-34s %5d devis  |  %s" % (nom[:34], d["devis"], verdict))
    if len(lignes) > 40:
        ecrire("     ... et %d autre(s) dossier(s)." % (len(lignes) - 40))

    ecrire("")
    ecrire("   VERDICT : %d dossier(s) de premier niveau portent une annee lisible,"
           % avec_annee)
    ecrire("             %d n'en portent pas." % sans_annee)
    if avec_annee == 0 and total:
        ecrire("             >>> L'arborescence n'est PAS rangee par annee. Le filtre")
        ecrire("                 « annee en cours » ne filtrera rien : la passe du soir")
        ecrire("                 relira tout le partage chaque nuit. A remplacer par un")
        ecrire("                 filtre sur la date de modification (--jours), deja en")
        ecrire("                 place, et a lancer avec --annee-min -1.")
    elif avec_annee and sans_annee:
        ecrire("             >>> Arborescence MIXTE. Les dossiers sans annee seront")
        ecrire("                 toujours relus. Verifier la liste ci-dessus avant de")
        ecrire("                 planifier la tache.")
    elif avec_annee:
        ecrire("             >>> Rangement par annee confirme : la passe quotidienne")
        ecrire("                 ne lira que %d devis au lieu de %d." % (gardes, total))

    ecrire("")
    ecrire("3. D'OU POURRAIT VENIR LE NOM DU CLIENT")
    ecrire("   Pour chaque devis, le dossier qui le contient. Si cette colonne")
    ecrire("   ressemble a des noms de clients, on prend le dossier ; si elle")
    ecrire("   ressemble a des annees ou des mois, on laisse le champ vide")
    ecrire("   plutot que d'y mettre une description de produit.")
    ecrire("")
    parents = Counter()
    for rel, _t, _m in infos["fichiers"]:
        seg = rel.split("/")
        parents[seg[-2] if len(seg) > 1 else "(racine)"] += 1
    ecrire("   Les 15 dossiers parents les plus frequents :")
    for nom, n in parents.most_common(15):
        ecrire("     %-40s %5d devis" % (nom[:40], n))
    distincts = len(parents)
    # Un dossier parent qui est une date ne nommera jamais un client. C'est le
    # cas le plus courant d'un partage range par annee, et sans ce test le
    # rapport restait muet sur la question posee.
    devis_sous_date = sum(n for nom, n in parents.items() if _est_date(nom))
    ecrire("")
    ecrire("   %d dossier(s) parent(s) distinct(s) pour %d devis." % (distincts, total))
    if total and devis_sous_date >= total * 0.6:
        ecrire("   >>> %d devis sur %d sont ranges sous un dossier qui est une DATE"
               % (devis_sous_date, total))
        ecrire("       (annee ou mois), pas un client. Le repli par nom de dossier")
        ecrire("       ecrirait « 2026 » dans la colonne Client : laisser vide.")
    elif total and distincts <= 3:
        ecrire("   >>> Trop peu de dossiers parents pour porter des noms de clients :")
        ecrire("       le repli par nom de dossier n'apporterait rien. Laisser vide.")
    elif total and distincts >= max(8, total * 0.05):
        ecrire("   >>> Beaucoup de dossiers parents distincts, et peu ressemblent a")
        ecrire("       des dates : ils portent probablement un client ou une affaire.")
        ecrire("       Le repli a du sens.")
    elif total:
        ecrire("   >>> Cas intermediaire : lire la liste ci-dessus et trancher a l'oeil.")

    ecrire("")
    ecrire("4. ECHANTILLON  (les %d devis modifies le plus recemment)" % echantillon)
    for rel, taille, mtime in infos["fichiers"][:echantillon]:
        ecrire("     %s  ·  %s Ko  ·  %s" % (
            rel[:88], int(taille / 1024),
            datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")))

    ecrire("")
    ecrire("5. VOLUME")
    if total:
        tailles = [t for _r, t, _m in infos["fichiers"]]
        mo = sum(tailles) / (1024.0 * 1024.0)
        ecrire("     %.1f Mo au total, %d Ko en moyenne, %d Ko pour le plus gros."
               % (mo, int(sum(tailles) / len(tailles) / 1024), int(max(tailles) / 1024)))
        recents = [1 for _r, _t, m in infos["fichiers"]
                   if (datetime.now() - datetime.fromtimestamp(m)).days <= 30]
        ecrire("     %d devis modifie(s) dans les 30 derniers jours — c'est l'ordre"
               % len(recents))
        ecrire("     de grandeur de ce que la passe du soir aura a traiter.")

    if infos["erreurs"]:
        ecrire("")
        ecrire("6. CE QUI N'A PAS PU ETRE LU  (%d)" % len(infos["erreurs"]))
        for exc in infos["erreurs"][:10]:
            ecrire("     %s" % exc)
        if len(infos["erreurs"]) > 10:
            ecrire("     ... et %d autre(s)." % (len(infos["erreurs"]) - 10))

    ecrire("")
    ecrire("=" * 72)


def main():
    ap = argparse.ArgumentParser(
        description="Inspecte le dossier des devis sans rien envoyer ni modifier.")
    ap.add_argument("--dossier", default=os.getenv("DEVIS_DIR", DOSSIER_DEFAUT),
                    help="Dossier a inspecter (defaut : %s)" % DOSSIER_DEFAUT)
    ap.add_argument("--rapport", default="",
                    help="Ecrit aussi le rapport dans ce fichier (UTF-8)")
    ap.add_argument("--echantillon", type=int, default=15,
                    help="Nombre de chemins reels a afficher (defaut : 15)")
    args = ap.parse_args()

    if not os.path.isdir(args.dossier):
        print("Dossier introuvable : %s" % args.dossier)
        print("Si c'est un lecteur mappe (U:), essayer le chemin UNC complet.")
        return 2

    sortie = Sortie(args.rapport or None)
    try:
        rapport(args.dossier, analyser(args.dossier), sortie, args.echantillon)
        if args.rapport:
            sortie("Rapport ecrit dans %s" % os.path.abspath(args.rapport))
    finally:
        sortie.fermer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
