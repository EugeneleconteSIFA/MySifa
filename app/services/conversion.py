"""MyTools › Convertir — conversions qui ne peuvent pas se faire dans le navigateur.

Repris du convertisseur de Prismix (music/prismix/server/convertir.mjs), réécrit
pour FastAPI. Le navigateur fait tout ce qu'il sait faire (images, SVG, PDF par
pdf.js / pdf-lib, CSV → JSON, vectorisation couleurs) ; ce module ne traite que
le reste, avec les outils système :

  documents, présentations, tableurs   LibreOffice sans interface (soffice)
  audio, vidéo                          ffmpeg
  images exotiques (TIFF, GIF, HEIC…)   ImageMagick (convert), libheif
  vectorisation noir et blanc           potrace
  PDF compressé (ghostscript), PDF → Word (LibreOffice)

Chaque demande travaille dans un dossier temporaire supprimé dès la réponse
préparée. Un outil absent du serveur n'est pas une panne : `outils_disponibles()`
le dit, l'écran grise la conversion et donne le paquet à installer.

Sécurité : aucun fichier reçu n'est exécuté. LibreOffice tourne avec un profil
jetable par conversion (macros jamais activées en mode --convert-to), ImageMagick
ne reçoit jamais de SVG/MSL (le SVG se convertit dans le navigateur), et les noms
de fichiers ne servent qu'au nom du résultat, nettoyés.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from typing import Optional

from config import CONVERTIR_MAX_MO, CONVERTIR_PARALLELE, CONVERTIR_PAR_HEURE

FAMILLES = {
    "image": ("png", "jpg", "jpeg", "webp", "gif", "bmp", "avif", "ico", "tif", "tiff", "heic", "heif"),
    "pdf": ("pdf",),
    "presentation": ("pptx", "ppt", "odp", "key", "pps", "ppsx"),
    "document": ("docx", "doc", "odt", "rtf", "txt", "md", "html", "htm", "pages"),
    "tableur": ("xlsx", "xls", "ods", "csv", "tsv", "numbers"),
    "audio": ("mp3", "wav", "ogg", "oga", "m4a", "aac", "flac", "opus", "aiff", "aif", "wma"),
    "video": ("mp4", "mov", "webm", "mkv", "avi", "m4v", "3gp", "wmv", "mpg", "mpeg", "flv"),
}

# Ce que le SERVEUR sait produire, par famille d'origine. Le reste (PNG, JPEG,
# WebP, ICO, PDF d'images, SVG couleurs, pages et texte d'un PDF, fusion…) se
# fait dans le navigateur (static/mysifa_tools_convertir.js).
CIBLES = {
    "image": ("png", "jpg", "webp", "avif", "gif", "bmp", "tiff", "svg-nb"),
    "pdf": ("docx", "compresser"),
    "presentation": ("pdf", "pptx", "odp", "png", "jpg"),
    "document": ("pdf", "docx", "odt", "rtf", "txt", "html"),
    "tableur": ("xlsx", "ods", "csv", "pdf"),
    "audio": ("mp3", "wav", "ogg", "flac", "m4a", "opus", "aiff"),
    "video": ("mp4", "webm", "mov", "mkv", "gif", "mp3", "m4a", "wav"),
}

# Outil système → paquet à installer (Debian/Ubuntu), pour le message d'absence.
OUTILS = {
    "soffice": "libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress",
    "ffmpeg": "ffmpeg",
    "convert": "imagemagick",
    "heif-convert": "libheif-examples",
    "potrace": "potrace",
    "gs": "ghostscript",
    "pdftoppm": "poppler-utils",
}


class ConversionRefusee(Exception):
    """Erreur affichable telle quelle, avec un code HTTP."""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def famille(ext: str) -> Optional[str]:
    ext = (ext or "").lower()
    return next((f for f, liste in FAMILLES.items() if ext in liste), None)


_presents: dict[str, bool] = {}
_chemins: dict[str, Optional[str]] = {}

# Le service systemd peut tourner avec un PATH réduit au virtualenv : les
# outils installés par apt (/usr/bin) y sont alors introuvables. On cherche
# aussi dans les dossiers système, et on lance l'outil par son chemin complet.
_DOSSIERS_SYSTEME = ("/usr/local/bin", "/usr/bin", "/bin", "/usr/local/sbin", "/usr/sbin", "/snap/bin",
                     "/opt/homebrew/bin")
# Nom de remplacement d'un outil (ImageMagick 7 n'installe plus que `magick`).
_ALIAS = {"convert": ("magick",)}


def _chemin_recherche() -> str:
    actuel = [d for d in (os.environ.get("PATH") or "").split(os.pathsep) if d]
    return os.pathsep.join(actuel + [d for d in _DOSSIERS_SYSTEME if d not in actuel])


def chemin_outil(o: str) -> Optional[str]:
    """Chemin complet de l'outil, ou None s'il n'est pas installé."""
    if o not in _chemins:
        trouve = None
        for nom in (o,) + _ALIAS.get(o, ()):
            trouve = shutil.which(nom, path=_chemin_recherche())
            if trouve:
                break
        _chemins[o] = trouve
    return _chemins[o]


def outils_disponibles() -> dict:
    for o in OUTILS:
        if o not in _presents:
            _presents[o] = chemin_outil(o) is not None
    return {"outils": dict(_presents), "paquets": dict(OUTILS)}


def outil_requis(fam: str, cible: str) -> str:
    if fam in ("audio", "video"):
        return "ffmpeg"
    if fam in ("presentation", "document", "tableur"):
        return "soffice"
    if fam == "pdf":
        return "gs" if cible == "compresser" else "soffice"
    if fam == "image":
        return "potrace" if cible == "svg-nb" else "convert"
    return ""


# ── Limites : conversions simultanées, quota par utilisateur ───────────
_verrou = threading.Lock()
_en_cours = 0
_historique: dict[str, list[float]] = {}


def reserver(qui: str) -> None:
    global _en_cours
    maintenant = time.time()
    with _verrou:
        h = [t for t in _historique.get(qui, []) if maintenant - t < 3600]
        if len(h) >= CONVERTIR_PAR_HEURE:
            raise ConversionRefusee(f"Limite atteinte : {CONVERTIR_PAR_HEURE} conversions par heure. Réessayer plus tard.", 429)
        if _en_cours >= CONVERTIR_PARALLELE:
            raise ConversionRefusee("Le convertisseur est occupé. Réessayer dans un instant.", 429)
        h.append(maintenant)
        _historique[qui] = h
        _en_cours += 1


def liberer() -> None:
    global _en_cours
    with _verrou:
        _en_cours = max(0, _en_cours - 1)


# ── Exécution ─────────────────────────────────────────────────────────
def _lancer(args: list[str], cwd: str, delai: int = 15 * 60) -> None:
    env = dict(os.environ, HOME=cwd, LANG="fr_FR.UTF-8", PATH=_chemin_recherche())
    complet = chemin_outil(args[0]) if args and os.sep not in args[0] else None
    if complet:
        args = [complet] + list(args[1:])
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=delai)
    except subprocess.TimeoutExpired:
        raise ConversionRefusee("Conversion trop longue, interrompue. Essayer un fichier plus léger.", 504)
    except FileNotFoundError:
        raise ConversionRefusee(f"Outil manquant sur le serveur : {args[0]}.", 503)
    if p.returncode != 0:
        raise RuntimeError(f"{args[0]} a échoué ({p.returncode}) : {p.stderr.decode('utf-8', 'replace')[-500:]}")


def nom_propre(nom: str) -> str:
    base = re.sub(r"\.[^.]+$", "", nom or "")
    base = re.sub(r"[^\w .-]+", "_", base, flags=re.UNICODE).strip(" ._")[:80]
    return base or "fichier"


_CRF = {"haute": 19, "moyenne": 23, "legere": 28}


def _echelle(o: dict) -> list[str]:
    h = {"1080": 1080, "720": 720, "480": 480}.get(str(o.get("resolution") or ""), 0)
    return ["-vf", f"scale=-2:'min(ih,{h})'"] if h else []


def _convertir_un(f: dict, cible: str, o: dict, dossier: str, i: int) -> None:
    sortie = os.path.join(dossier, "out")
    nom_sortie = lambda ext: os.path.join(sortie, f"{f['base']}.{ext}")  # noqa: E731

    def soffice(fmt: str, src: Optional[str] = None, filtre: Optional[str] = None) -> str:
        profil = os.path.join(dossier, f"lo{i}")
        tmp = os.path.join(dossier, f"tmp{i}")
        os.makedirs(tmp, exist_ok=True)
        args = ["soffice", f"-env:UserInstallation=file://{profil}", "--headless", "--norestore",
                "--nolockcheck", "--nodefault"]
        if filtre:
            args.append(f"--infilter={filtre}")
        args += ["--convert-to", fmt, "--outdir", tmp, src or f["chemin"]]
        _lancer(args, dossier, 5 * 60)
        produits = os.listdir(tmp)
        if not produits:
            raise RuntimeError("LibreOffice n'a rien produit.")
        return os.path.join(tmp, produits[0])

    def pages(pdf: str, fmt: str) -> None:
        dpi = str(int(o.get("dpi") or 150))
        _lancer(["pdftoppm", "-r", dpi, "-jpeg" if fmt == "jpg" else "-png", pdf,
                 os.path.join(sortie, f"{f['base']}-page")], dossier)

    fam = f["famille"]
    if fam in ("audio", "video"):
        crf = str(_CRF.get(str(o.get("qualite") or ""), 23))
        h264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf, "-pix_fmt", "yuv420p", *_echelle(o),
                "-c:a", "aac", "-b:a", "160k"]
        recettes = {
            "mp4": h264 + ["-movflags", "+faststart"],
            "mov": h264,
            "mkv": ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf, *_echelle(o), "-c:a", "aac", "-b:a", "160k"],
            "webm": ["-c:v", "libvpx-vp9", "-crf", str(int(crf) + 10), "-b:v", "0", "-row-mt", "1", "-deadline", "good",
                     "-cpu-used", "4", *_echelle(o), "-c:a", "libopus", "-b:a", "128k"],
            "gif": ["-filter_complex", f"fps=12,scale='min(iw,{int(o.get('largeur') or 480)})':-2:flags=lanczos,"
                    "split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4", "-an"],
            "mp3": ["-vn", "-c:a", "libmp3lame", "-q:a", "2"],
            "m4a": ["-vn", "-c:a", "aac", "-b:a", "192k"],
            "wav": ["-vn", "-c:a", "pcm_s16le"],
            "ogg": ["-vn", "-c:a", "libvorbis", "-q:a", "6"],
            "flac": ["-vn", "-c:a", "flac"],
            "opus": ["-vn", "-c:a", "libopus", "-b:a", "128k"],
            "aiff": ["-vn", "-c:a", "pcm_s16be"],
        }
        if cible in recettes:
            _lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f["chemin"], *recettes[cible],
                     nom_sortie(cible)], dossier)
            return
    elif fam in ("presentation", "document", "tableur"):
        if cible in ("png", "jpg"):
            pages(soffice("pdf"), cible)
            return
        fmt = {"txt": "txt:Text (encoded):UTF8", "csv": "csv:Text - txt - csv (StarCalc):44,34,76,1",
               "html": "html"}.get(cible, cible)
        shutil.move(soffice(fmt), nom_sortie(cible))
        return
    elif fam == "pdf":
        if cible == "docx":
            shutil.move(soffice("docx:MS Word 2007 XML", filtre="writer_pdf_import"), nom_sortie("docx"))
            return
        if cible == "compresser":
            niveau = "screen" if o.get("niveau") == "fort" else "ebook"
            _lancer(["gs", "-sDEVICE=pdfwrite", f"-dPDFSETTINGS=/{niveau}", "-dCompatibilityLevel=1.5", "-dNOPAUSE",
                     "-dBATCH", "-dQUIET", "-dSAFER", f"-sOutputFile={os.path.join(sortie, f['base'] + '-compresse.pdf')}",
                     f["chemin"]], dossier)
            return
    elif fam == "image":
        src = f["chemin"]
        if f["ext"] in ("heic", "heif"):
            src = os.path.join(dossier, f"heic{i}.png")
            _lancer(["heif-convert", f["chemin"], src], dossier)
        largeur = int(o.get("largeur") or 0)
        lim = ["-resize", f"{largeur}x{largeur}>"] if largeur > 0 else []
        if cible == "svg-nb":
            bmp = os.path.join(dossier, f"nb{i}.bmp")
            seuil = int(o.get("seuil") or 50)
            _lancer(["convert", f"{src}[0]", *lim, "-background", "white", "-flatten", "-colorspace", "gray",
                     "-threshold", f"{seuil}%", bmp], dossier)
            _lancer(["potrace", "-s", "--turdsize", "4", "--alphamax", "1", "-o", nom_sortie("svg"), bmp], dossier)
            return
        fond = ["-background", "white", "-flatten"] if cible in ("jpg", "bmp") else []
        q = ["-quality", str(round(float(o.get("qualite") or 0.88) * 100))] if cible in ("jpg", "webp", "avif") else []
        _lancer(["convert", f"{src}[0]", *lim, *fond, *q, nom_sortie(cible)], dossier)
        return
    raise ConversionRefusee(f"Conversion {f['ext']} → {cible} non prise en charge.")


def convertir(fichiers: list[tuple[str, bytes]], cible: str, options: dict) -> tuple[str, bytes, str]:
    """[(nom, octets)] → (nom du résultat, octets, type MIME). ZIP s'il y a plusieurs fichiers produits."""
    if not fichiers:
        raise ConversionRefusee("Aucun fichier reçu.")
    total = sum(len(c) for _, c in fichiers)
    if total > CONVERTIR_MAX_MO * 1024 * 1024:
        raise ConversionRefusee(f"Fichiers trop lourds : {CONVERTIR_MAX_MO} Mo au plus.", 413)
    infos = []
    for nom, _ in fichiers:
        ext = (re.search(r"\.([a-z0-9]{1,6})$", nom or "", re.I) or [None, ""])[1].lower()
        fam = famille(ext)
        if not fam:
            raise ConversionRefusee(f"{nom} : type de fichier non pris en charge.")
        infos.append((ext, fam))
    fam = infos[0][1]
    if any(x[1] != fam for x in infos):
        raise ConversionRefusee("Envoyer des fichiers du même type à la fois.")
    if cible not in CIBLES.get(fam, ()):
        raise ConversionRefusee(f"Conversion vers {cible} non prise en charge pour ce type de fichier.")
    requis = outil_requis(fam, cible)
    if requis and not outils_disponibles()["outils"].get(requis):
        raise ConversionRefusee(f"Outil absent du serveur : {requis} (paquet {OUTILS.get(requis, requis)}).", 503)
    if (cible in ("png", "jpg") and fam in ("presentation", "document", "tableur")
            and not outils_disponibles()["outils"].get("pdftoppm")):
        raise ConversionRefusee("Outil absent du serveur : pdftoppm (paquet poppler-utils).", 503)

    dossier = tempfile.mkdtemp(prefix="mysifa_conv_")
    try:
        os.makedirs(os.path.join(dossier, "in"))
        os.makedirs(os.path.join(dossier, "out"))
        liste = []
        for i, ((nom, contenu), (ext, fam_i)) in enumerate(zip(fichiers, infos)):
            chemin = os.path.join(dossier, "in", f"{i}.{ext}")
            with open(chemin, "wb") as fh:
                fh.write(contenu)
            liste.append({"nom": nom, "base": nom_propre(nom), "ext": ext, "chemin": chemin, "famille": fam_i})
        for i, f in enumerate(liste):
            _convertir_un(f, cible, options or {}, dossier, i)
        sortie = os.path.join(dossier, "out")
        produits = sorted(os.listdir(sortie), key=lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)])
        if not produits:
            raise RuntimeError("La conversion n'a rien produit.")
        if len(produits) == 1:
            with open(os.path.join(sortie, produits[0]), "rb") as fh:
                return produits[0], fh.read(), "application/octet-stream"
        nom_zip = f"{liste[0]['base']}-{cible}.zip"
        chemin_zip = os.path.join(dossier, nom_zip)
        with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in produits:
                z.write(os.path.join(sortie, p), p)
        with open(chemin_zip, "rb") as fh:
            return nom_zip, fh.read(), "application/zip"
    finally:
        shutil.rmtree(dossier, ignore_errors=True)
