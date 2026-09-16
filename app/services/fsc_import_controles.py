"""MySifa — import d'un lot de contrôles FSC.

Un contrôle sur la base publique FSC produit deux choses : le « FSC Certification
Record » signé numériquement par FSC, et ce qu'on y lit. Les déposer un par un
sur dix-huit fiches est une corvée qui invite à la faute de frappe — et une
faute de frappe sur une date d'expiration se paie en réception.

Ce module avale le lot entier et rend une proposition, fichier par fichier.

Deux principes :

1. **Le dossier fait foi.** Tout est lu dans le PDF, y compris la date du
   contrôle, qui est l'horodatage UTC de la signature FSC — pas la date du jour,
   pas une saisie. Le CSV qui accompagne le lot n'apporte que le libellé du
   fournisseur et la décision de le garder ou non dans la liste ; il ne corrige
   jamais une valeur lue.
2. **Ce module LIT et PROPOSE.** Il n'écrit rien en base. La route appelante
   montre la proposition, et seul un humain déclenche l'écriture.

Le rapprochement avec `fournisseurs_fsc` se fait par code de certificat, puis
par licence, puis par nom. Cet ordre n'est pas cosmétique : une fiche dont le
code de certificat est faux — cas Itasa, qui portait ceux de la filiale
mexicaine — ne se rattrape que par la licence, et c'est précisément le genre
d'erreur que l'import est là pour corriger.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Optional

from app.services.fsc_classification import nettoyer_liste
from config import FSC_CLAIMS_PORTEE

# Un Certification Record fait 3 à 17 pages ; au-delà on ne lit pas un dossier.
_MAX_CARACTERES = 400_000

MARQUEUR = "FSC CERTIFICATION RECORD"

_MOIS_EN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Le dossier est toujours tiré en anglais (culture=en) : « Aug 09, 2027 ».
_RE_DATE_EN = re.compile(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b")

# Horodatage PDF : « D:20260916083625+00'00' ».
_RE_HORODATAGE = re.compile(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})")

_RE_CODE_PORTEE = re.compile(r"\bP\d{1,2}(?:\.\d{1,2}){0,2}\b")

# L'ordre compte : « Credit » avant la forme courte, sinon « FSC Mix Credit »
# serait compté comme « FSC Mix ».
_CLAIMS = [
    ("fsc_mix_credit", re.compile(r"FSC\s*Mix\s*Credit", re.I)),
    ("fsc_recycled_credit", re.compile(r"FSC\s*Recycled\s*Credit", re.I)),
    ("fsc_100", re.compile(r"FSC\s*100\s*%", re.I)),
    ("fsc_mix", re.compile(r"FSC\s*Mix(?!\s*Credit)", re.I)),
    ("fsc_recycled", re.compile(r"FSC\s*Recycled(?!\s*Credit)", re.I)),
    ("fsc_controlled_wood", re.compile(r"FSC\s*Controlled\s*Wood", re.I)),
]

_STATUTS = {
    "valid": "valide",
    "suspended": "suspendu",
    "withdrawn": "retire",
    "expired": "expire",
    "terminated": "retire",
}

# Le pied de page se glisse dans le dernier champ d'un bloc quand l'extraction
# perd la mise en page. Toute valeur qui le contient est du bruit.
_RE_PIED = re.compile(r"FSC Certification File|Page\s+\d+\s+about\s+\d+", re.I)


# ══════════════════════════════════════════════════════════════════
# Texte
# ══════════════════════════════════════════════════════════════════

def texte_record(file_bytes: bytes) -> str:
    """Texte brut du PDF. Chaîne vide si ce n'est pas lisible."""
    try:
        import pdfplumber
    except Exception:
        return ""
    morceaux: list[str] = []
    total = 0
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # x_tolerance=1 : les polices embarquées de ces dossiers
                # déclarent des largeurs fausses. Au réglage par défaut (3),
                # pdfplumber n'insère aucune espace et rend « LicenseCode: ».
                txt = page.extract_text(x_tolerance=1) or ""
                if not txt:
                    continue
                if total + len(txt) > _MAX_CARACTERES:
                    break
                morceaux.append(txt)
                total += len(txt)
    except Exception:
        return ""
    return "\n".join(morceaux)


# ══════════════════════════════════════════════════════════════════
# Petits lecteurs
# ══════════════════════════════════════════════════════════════════

# Une ligne du dossier qui ouvre un nouveau champ : « Expiry date: », « Website ».
_RE_LABEL = re.compile(r"^[A-Za-z][A-Za-z ./'-]{2,44}:")


def _champ(texte: str, label: str, largeur: int = 200, suite: bool = False) -> str:
    """Valeur qui suit `label:`.

    `suite=True` recolle les lignes de débordement — une raison sociale ou une
    adresse longue passe à la ligne dans le dossier, et s'arrêter à la première
    ligne amputerait « INDUSTRIAS … S.A. (ITASA) » de son sigle.
    """
    i = texte.find(label)
    if i < 0:
        return ""
    reste = texte[i + len(label):i + len(label) + largeur].lstrip(": \t")
    morceaux: list[str] = []
    for ligne in reste.split("\n"):
        ligne = ligne.strip()
        if _RE_PIED.search(ligne):
            break
        if not ligne:
            if morceaux:
                break
            continue
        if morceaux and _RE_LABEL.match(ligne):
            break
        morceaux.append(ligne)
        if not suite:
            break
    return " ".join(morceaux).strip()


def _date_iso(valeur: str) -> Optional[str]:
    m = _RE_DATE_EN.search(valeur or "")
    if not m:
        return None
    mois = _MOIS_EN.get(m.group(1).lower()[:3])
    if not mois:
        return None
    jour, annee = int(m.group(2)), int(m.group(3))
    if not (1 <= jour <= 31 and 1990 <= annee <= 2100):
        return None
    return "%04d-%02d-%02d" % (annee, mois, jour)


def _statut(valeur: str) -> str:
    v = (valeur or "").strip().lower()
    for cle, code in _STATUTS.items():
        if cle in v:
            return code
    return "introuvable"


# Fin d'un bloc : le libellé en capitales qui ouvre le champ suivant.
_RE_LABEL_BLOC = re.compile(r"^[A-Z][A-Z0-9 \-/,.']{3,}:\s*$")


def _valeurs_apres(texte: str, entete: str) -> list[str]:
    """Contenu de chaque champ `entete`, jusqu'au libellé suivant.

    Découper sur l'en-tête plutôt que lire une fenêtre de taille fixe : sur un
    dossier dont les blocs produit sont courts — Avery Dennison, trois lignes —
    une fenêtre avale le bloc suivant et le fait disparaître du résultat.
    """
    out: list[str] = []
    for part in texte.split(entete)[1:]:
        lignes: list[str] = []
        for ligne in part.split("\n")[:40]:
            nue = ligne.strip()
            if not nue or _RE_PIED.search(nue):
                continue
            if lignes and _RE_LABEL_BLOC.match(nue):
                break
            if _RE_LABEL_BLOC.match(nue):
                break
            lignes.append(nue)
        out.append("\n".join(lignes))
    return out


def _claims(texte: str) -> list[str]:
    """Allégations de sortie, union de tous les blocs produit du dossier."""
    trouves: set[str] = set()
    for segment in _valeurs_apres(texte, "MAIN OUTPUT CATEGORY:"):
        reste = segment
        for code, motif in _CLAIMS:
            if motif.search(reste):
                trouves.add(code)
            reste = motif.sub(" ", reste)
    # Ordre du référentiel, pas ordre d'apparition : deux dossiers du même
    # fournisseur doivent produire la même liste.
    return [c for c in FSC_CLAIMS_PORTEE if c in trouves]


def _portees(texte: str) -> list[str]:
    """Codes FSC-STD-40-004a couverts, union de tous les blocs produit."""
    codes: list[str] = []
    for segment in _valeurs_apres(texte, "PRODUCT CATEGORY:"):
        m = _RE_CODE_PORTEE.search(segment)
        if m:
            codes.append(m.group(0))
    return nettoyer_liste(codes)


def signature_fsc(file_bytes: bytes) -> tuple[Optional[str], Optional[str]]:
    """Date et heure de la signature numérique FSC, en UTC.

    C'est l'horodatage qui fait preuve, et il ne se lit PAS dans le texte du
    PDF : l'apparence de la signature est un flux à part, que l'extraction de
    texte ne traverse pas. On va le chercher dans le dictionnaire de signature
    du formulaire (`/M`), à défaut dans la date de création du document.

    Rend (jour ISO, horodatage complet) — (None, None) si le dossier n'est pas
    signé, ce qui doit se voir plutôt que se combler.
    """
    def _iso(brut: str) -> Optional[str]:
        m = _RE_HORODATAGE.search(brut or "")
        if not m:
            return None
        return "%s-%s-%s %s:%s:%s" % m.groups()

    try:
        import pypdf
    except Exception:
        return None, None
    try:
        lecteur = pypdf.PdfReader(io.BytesIO(file_bytes))
        formulaire = lecteur.trailer["/Root"].get("/AcroForm")
        if formulaire:
            for champ in formulaire.get("/Fields", []) or []:
                valeur = champ.get_object().get("/V")
                if valeur is None:
                    continue
                horo = _iso(str(valeur.get_object().get("/M") or ""))
                if horo:
                    return horo[:10], horo
        horo = _iso(str((lecteur.metadata or {}).get("/CreationDate") or ""))
        if horo:
            return horo[:10], horo
    except Exception:
        return None, None
    return None, None


def _sites_expires(texte: str) -> int:
    return len(re.findall(r"Expired\s*\n?\s*site", texte, re.I))


# ══════════════════════════════════════════════════════════════════
# Lecture d'un dossier
# ══════════════════════════════════════════════════════════════════

def lire_record(file_bytes: bytes) -> dict:
    """Lit un FSC Certification Record.

    Rend `{"ok": False, "erreur": ...}` sur tout ce qui n'est pas un dossier de
    certification FSC : mieux vaut refuser un fichier que d'en inventer le
    contenu. Un champ absent du dossier reste absent — il n'est jamais deviné.
    """
    texte = texte_record(file_bytes)
    if not texte:
        return {"ok": False, "erreur": "PDF illisible ou sans texte — un dossier FSC n'est jamais un scan."}
    if MARQUEUR not in texte.upper():
        return {"ok": False, "erreur": "Ce PDF n'est pas un FSC Certification Record téléchargé sur la base FSC."}

    certificat = _champ(texte, "Certificate Code")
    licence = _champ(texte, "License Code")
    # « Old certificate code: » vide fait remonter le titre du bloc suivant.
    ancien = _champ(texte, "Old certificate code")
    if ancien and not re.match(r"^[A-Z]{2,8}-(?:COC|CW|FM/COC|PC)-\d{4,7}$", ancien):
        ancien = ""

    signe_le, signe_horodatage = signature_fsc(file_bytes)
    donnees = {
        "ok": True,
        "licence": licence or None,
        "certificat": certificat or None,
        "ancien_certificat": ancien or None,
        "titulaire": _champ(texte, "Company Name", 260, suite=True) or None,
        "adresse": _champ(texte, "Address", 260, suite=True) or None,
        "statut_base": _statut(_champ(texte, "Certification status")),
        "statut_texte": _champ(texte, "Certification status") or None,
        "date_premiere_emission": _date_iso(_champ(texte, "Date of first issue")),
        "derniere_mise_a_jour": _date_iso(_champ(texte, "Last status update")),
        "date_expiration_lue": _date_iso(_champ(texte, "Expiry date")),
        "standards": _champ(texte, "Standards assessed") or None,
        "claims": _claims(texte),
        "portees": _portees(texte),
        "signe_le": signe_le,
        "signe_horodatage": signe_horodatage,
        "sites_expires": _sites_expires(texte),
    }
    if not donnees["certificat"]:
        return {"ok": False, "erreur": "Code de certificat introuvable dans le dossier."}
    if not signe_le:
        donnees["avertissements"] = ["Signature FSC absente du dossier — la date du contrôle sera à saisir."]
    return donnees


# ══════════════════════════════════════════════════════════════════
# CSV d'accompagnement
# ══════════════════════════════════════════════════════════════════

def lire_csv(file_bytes: bytes) -> dict[str, dict]:
    """Le CSV du lot, indexé par code de certificat.

    Facultatif, et volontairement pauvre : il ne sert qu'à nommer le
    fournisseur et à porter la décision « reste dans la liste ou non ». Aucune
    valeur du CSV ne remplace une valeur lue dans le dossier.
    """
    try:
        texte = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texte = file_bytes.decode("cp1252")
        except Exception:
            return {}
    try:
        dialecte = csv.Sniffer().sniff(texte[:2000], delimiters=";,\t")
        delim = dialecte.delimiter
    except Exception:
        delim = ";"
    out: dict[str, dict] = {}
    for ligne in csv.DictReader(io.StringIO(texte), delimiter=delim):
        cert = (ligne.get("certificat") or "").strip().upper()
        if not cert:
            continue
        garde = (ligne.get("liste_fournisseurs_fsc") or "").strip().lower()
        out[cert] = {
            "fournisseur": (ligne.get("fournisseur") or "").strip() or None,
            "dans_liste": None if not garde else garde.startswith("o"),
            "motif": (ligne.get("motif") or "").strip() or None,
        }
    return out


# ══════════════════════════════════════════════════════════════════
# Rapprochement
# ══════════════════════════════════════════════════════════════════

def _norm(v) -> str:
    return re.sub(r"[^a-z0-9]", "", (v or "").lower())


def rapprocher(fournisseurs: list[dict], lu: dict, libelle_csv: Optional[str]) -> tuple[Optional[dict], str]:
    """Retrouve la fiche fournisseur. Rend (fiche, méthode)."""
    cert = _norm(lu.get("certificat"))
    if cert:
        for f in fournisseurs:
            if _norm(f.get("certificat")) == cert:
                return f, "certificat"
    lic = _norm(lu.get("licence"))
    if lic:
        for f in fournisseurs:
            if _norm(f.get("licence")) == lic:
                return f, "licence"
    for candidat in (libelle_csv, lu.get("titulaire")):
        n = _norm(candidat)
        if not n:
            continue
        for f in fournisseurs:
            fn = _norm(f.get("nom"))
            if fn and (fn == n or (len(fn) >= 4 and fn in n)):
                return f, "nom"
    return None, "aucun"


def couvre_portee(portees_lues: list[str], code: str) -> bool:
    """La portée est hiérarchique : P7.8 est couvert par P7.8 comme par P7."""
    return any(code == l or code.startswith(l + ".") for l in portees_lues or [])


def ecarts(fiche: Optional[dict], lu: dict) -> list[dict]:
    """Ce que l'import changerait sur la fiche fournisseur."""
    if not fiche:
        return []
    out = []
    for champ, en_base, lue in (
        ("licence", fiche.get("licence"), lu.get("licence")),
        ("certificat", fiche.get("certificat"), lu.get("certificat")),
        ("fsc_date_expiration", (fiche.get("fsc_date_expiration") or "")[:10] or None,
         lu.get("date_expiration_lue")),
    ):
        if lue and (en_base or None) != lue:
            out.append({"champ": champ, "avant": en_base or None, "apres": lue})
    return out
