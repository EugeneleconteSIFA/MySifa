"""
MySifa — lecture d'un certificat FSC fournisseur.

Ce qu'on cherche dans le document :
- la licence (FSC-C123456) et le code du certificat (SGSCH-COC-002122) ;
- la date d'expiration ;
- les catégories (claims) que le fournisseur a le droit de livrer :
  FSC 100%, FSC Mix, FSC Mix Credit, FSC Recycled, FSC Recycled Credit,
  FSC Controlled Wood.

Où c'est écrit. La plupart des organismes certificateurs (SGS, Control Union,
FCBA, Intertek, TÜV…) joignent au certificat une annexe « Scope » ou
« Product groups » qui liste, groupe de produits par groupe de produits, les
claims couverts. Certains ne le font PAS et renvoient simplement à la base
publique FSC : sur ces certificats-là, aucune lecture ne trouvera de catégorie,
et le module le dit au lieu d'inventer.

Méthode, dans cet ordre :
1. Les MOTIFS sur le texte du PDF (pdfplumber). Gratuit, instantané, et chaque
   claim trouvé est rendu avec la phrase qui le porte — l'humain qui valide voit
   d'où il vient.
2. L'IA uniquement quand il n'y a PAS de texte : PDF scanné ou photo. Un PDF
   natif dont l'annexe ne liste aucun claim ne part pas au modèle — il ne
   trouverait rien de plus, et le payer pour le confirmer n'a pas de sens.

Ce module LIT et PROPOSE. Il n'écrit jamais en base : la route appelante range
la proposition sur la ligne du certificat, et seul un contrôle validé par un
humain fixe les catégories d'un fournisseur.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from datetime import date
from typing import Optional

from config import FSC_CLAIMS_PORTEE, FSC_LECTURE_IA_ACTIVE, FSC_LECTURE_IA_MODELE

# Budget de caractères envoyés au modèle ou analysés : un certificat fait une à
# cinq pages, une annexe de groupe peut en faire trente.
_MAX_CARACTERES = 60_000


# ══════════════════════════════════════════════════════════════════
# Extraction du texte
# ══════════════════════════════════════════════════════════════════

def texte_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    """[(numéro de page, texte)] d'un PDF natif. Liste vide pour un scan."""
    try:
        import pdfplumber
    except Exception:
        return []
    pages: list[tuple[int, str]] = []
    total = 0
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                txt = (page.extract_text() or "").strip()
                if not txt:
                    continue
                if total + len(txt) > _MAX_CARACTERES:
                    break
                pages.append((i, txt))
                total += len(txt)
    except Exception:
        return []
    return pages


def type_fichier(filename: str, mime: str = "") -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""
    if ext == "pdf" or "pdf" in (mime or ""):
        return "pdf"
    if ext in ("png", "jpg", "jpeg", "webp", "gif") or (mime or "").startswith("image/"):
        return "image"
    return "inconnu"


# ══════════════════════════════════════════════════════════════════
# Motifs
# ══════════════════════════════════════════════════════════════════

# « FSC-C004451 », « FSC® C004451 », « FSC™-C004451 », « License code: C004451 ».
_RE_LICENCE = re.compile(
    r"(?:\bFSC\s*[®™©]?\s*[-–—]?\s*|licen[cs]e\s*(?:code|number|n°|no\.?)?\s*[:#]?\s*)"
    r"C\s*[-–—]?\s*(\d{6})\b",
    re.I,
)
_RE_CERTIFICAT = re.compile(r"\b([A-Z]{2,8}-(?:COC|CW|FM/COC|PC)-\d{4,7})\b")

# L'ordre compte : les formes « Credit » passent avant la forme courte, et un
# claim déjà reconnu sur un segment n'est pas relu par le motif plus court.
_MOTIFS_CLAIMS = [
    ("fsc_mix_credit",      re.compile(r"\bFSC\s*Mix\s*Credit\b", re.I)),
    ("fsc_recycled_credit", re.compile(r"\bFSC\s*Recycled\s*Credit\b", re.I)),
    ("fsc_100",             re.compile(r"\bFSC\s*100\s*%", re.I)),
    ("fsc_mix",             re.compile(r"\bFSC\s*Mix\b(?!\s*Credit)", re.I)),
    ("fsc_recycled",        re.compile(r"\bFSC\s*Recycled\b(?!\s*Credit)", re.I)),
    ("fsc_controlled_wood", re.compile(r"\bFSC\s*Controlled\s*Wood\b", re.I)),
]

# « FSC Controlled Wood » apparaît aussi dans le TITRE des normes citées
# (« FSC-STD-40-005 Requirements for Sourcing FSC Controlled Wood ») : ce n'est
# pas un claim. Une ligne qui cite une norme est ignorée pour ce motif.
_RE_LIGNE_NORME = re.compile(r"STD|Requirements\s+for|Standard\s+for|exigences", re.I)

_MOIS = {
    "january": 1, "jan": 1, "janvier": 1, "janv": 1, "enero": 1, "gennaio": 1, "januar": 1,
    "february": 2, "feb": 2, "fevrier": 2, "février": 2, "fev": 2, "févr": 2, "febrero": 2, "febbraio": 2, "februar": 2,
    "march": 3, "mar": 3, "mars": 3, "marzo": 3, "märz": 3, "marz": 3,
    "april": 4, "apr": 4, "avril": 4, "avr": 4, "abril": 4, "aprile": 4,
    "may": 5, "mai": 5, "mayo": 5, "maggio": 5,
    "june": 6, "jun": 6, "juin": 6, "junio": 6, "giugno": 6, "juni": 6,
    "july": 7, "jul": 7, "juillet": 7, "juil": 7, "julio": 7, "luglio": 7, "juli": 7,
    "august": 8, "aug": 8, "aout": 8, "août": 8, "agosto": 8,
    "september": 9, "sep": 9, "sept": 9, "septembre": 9, "septiembre": 9, "settembre": 9,
    "october": 10, "oct": 10, "octobre": 10, "octubre": 10, "ottobre": 10, "oktober": 10,
    "november": 11, "nov": 11, "novembre": 11, "noviembre": 11,
    "december": 12, "dec": 12, "decembre": 12, "décembre": 12, "diciembre": 12, "dicembre": 12, "dezember": 12,
}
_RE_DATE_ISO = re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b")
_RE_DATE_EU = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b")
_RE_DATE_TEXTE_JMA = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th|er)?\s+([A-Za-zéûä]{3,10})\.?,?\s+(20\d{2})\b")
_RE_DATE_TEXTE_MJA = re.compile(r"\b([A-Za-zéûä]{3,10})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b")

# Mots qui annoncent la date de fin de validité, en plusieurs langues.
_RE_ANNONCE_EXPIRATION = re.compile(
    r"valid\s*(?:until|to|thru|through)|expir\w*|date\s+of\s+expiry|"
    r"valable\s+jusqu|date\s+d.expiration|fin\s+de\s+validit|"
    r"g[üu]ltig\s+bis|v[áa]lido\s+hasta|valido\s+fino|scadenza|fecha\s+de\s+(?:caducidad|vencimiento)",
    re.I,
)


def _date_valide(a: int, m: int, j: int) -> Optional[str]:
    try:
        return date(a, m, j).isoformat()
    except ValueError:
        return None


def _dates_dans(segment: str) -> list[tuple[int, str]]:
    """[(position, AAAA-MM-JJ)] des dates reconnues dans un segment."""
    out: list[tuple[int, str]] = []
    for m in _RE_DATE_ISO.finditer(segment):
        d = _date_valide(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            out.append((m.start(), d))
    for m in _RE_DATE_EU.finditer(segment):
        # Les certificats européens écrivent JJ/MM/AAAA. Un 07/13/2027 ne
        # passe pas en JJ/MM : on le relit alors en MM/JJ (format US).
        j, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        d = _date_valide(a, mo, j) or _date_valide(a, j, mo)
        if d:
            out.append((m.start(), d))
    for m in _RE_DATE_TEXTE_JMA.finditer(segment):
        mo = _MOIS.get(m.group(2).lower())
        if mo:
            d = _date_valide(int(m.group(3)), mo, int(m.group(1)))
            if d:
                out.append((m.start(), d))
    for m in _RE_DATE_TEXTE_MJA.finditer(segment):
        mo = _MOIS.get(m.group(1).lower())
        if mo:
            d = _date_valide(int(m.group(3)), mo, int(m.group(2)))
            if d:
                out.append((m.start(), d))
    return sorted(out)


def _expiration(texte: str) -> Optional[str]:
    """Date qui suit une annonce d'expiration. À défaut : la plus tardive du
    document, qui est presque toujours la fin de validité (émission, audit et
    décision la précèdent)."""
    for m in _RE_ANNONCE_EXPIRATION.finditer(texte):
        suite = texte[m.end(): m.end() + 80]
        dates = _dates_dans(suite)
        if dates:
            return dates[0][1]
    toutes = [d for _, d in _dates_dans(texte)]
    return max(toutes) if toutes else None


def _extrait(ligne: str, debut: int, fin: int, largeur: int = 70) -> str:
    a = max(0, debut - largeur)
    b = min(len(ligne), fin + largeur)
    s = ligne[a:b].strip()
    return ("…" if a > 0 else "") + s + ("…" if b < len(ligne) else "")


def lire_motifs(pages: list[tuple[int, str]]) -> dict:
    """Licence, certificat, expiration et claims trouvés dans le texte."""
    texte = "\n".join(t for _, t in pages)

    licences = []
    for m in _RE_LICENCE.finditer(texte):
        code = f"FSC-C{m.group(1)}"
        if code not in licences:
            licences.append(code)
    certificats = []
    for m in _RE_CERTIFICAT.finditer(texte):
        if m.group(1) not in certificats:
            certificats.append(m.group(1))

    claims: dict[str, dict] = {}
    for num_page, txt in pages:
        for ligne in txt.splitlines():
            couverts: list[tuple[int, int]] = []
            for code, motif in _MOTIFS_CLAIMS:
                if code == "fsc_controlled_wood" and _RE_LIGNE_NORME.search(ligne):
                    continue
                for m in motif.finditer(ligne):
                    if any(a <= m.start() < b for a, b in couverts):
                        continue
                    couverts.append((m.start(), m.end()))
                    if code not in claims:
                        claims[code] = {
                            "code": code,
                            "extrait": _extrait(ligne, m.start(), m.end()),
                            "page": num_page,
                        }

    return {
        # Un certificat de groupe liste plusieurs licences : on les rend
        # toutes, la route choisit celle du fournisseur.
        "licences": licences,
        "licence": licences[0] if licences else None,
        "certificat": certificats[0] if certificats else None,
        "expiration": _expiration(texte),
        "claims": [claims[c] for c in FSC_CLAIMS_PORTEE if c in claims],
    }


# ══════════════════════════════════════════════════════════════════
# IA — scans et photos uniquement
# ══════════════════════════════════════════════════════════════════

_OUTIL = {
    "name": "enregistrer_certificat_fsc",
    "description": "Enregistre ce qui est lu sur un certificat FSC fournisseur.",
    "input_schema": {
        "type": "object",
        "properties": {
            "licence": {"type": "string", "description": "Code licence FSC, format FSC-C123456. Vide si illisible."},
            "certificat": {"type": "string", "description": "Code du certificat, ex. SGSCH-COC-002122. Vide si absent."},
            "date_expiration": {"type": "string", "description": "Fin de validité au format AAAA-MM-JJ. Vide si absente."},
            "claims": {
                "type": "array",
                "description": "Catégories FSC EXPLICITEMENT écrites dans le document. Rien d'autre.",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "enum": list(FSC_CLAIMS_PORTEE.keys())},
                        "extrait": {"type": "string", "description": "Le passage exact qui porte ce claim."},
                        "page": {"type": "integer"},
                    },
                    "required": ["code", "extrait"],
                },
            },
            "remarques": {"type": "string", "description": "Ce qui reste illisible ou douteux, en une phrase."},
        },
        "required": ["claims"],
    },
}

_CONSIGNE = """Tu lis un certificat FSC de chaîne de contrôle (CoC) d'un fournisseur de papier ou d'adhésif.

Relève, uniquement s'ils sont écrits dans le document :
- la licence FSC (FSC-C suivi de six chiffres) ;
- le code du certificat (ex. SGSCH-COC-002122, CU-COC-807907) ;
- la date de fin de validité, au format AAAA-MM-JJ ;
- les catégories (claims) FSC que le certificat couvre, en général listées dans l'annexe « Scope » ou « Product groups » : FSC 100%, FSC Mix (ou FSC Mix x%), FSC Mix Credit, FSC Recycled (ou FSC Recycled x%), FSC Recycled Credit, FSC Controlled Wood.

Règles, sans exception :
1. N'INVENTE RIEN. Un claim qui n'est pas écrit n'est pas émis. Un certificat qui renvoie à la base FSC sans lister ses claims n'en a aucun à relever : dis-le dans `remarques`.
2. « FSC Controlled Wood » cité dans le titre d'une norme (FSC-STD-40-005…) n'est pas un claim.
3. « FSC Mix 70% » se range en fsc_mix ; « FSC Recycled 85% » en fsc_recycled.
4. Pour chaque claim, recopie le passage exact dans `extrait`.

Appelle l'outil `enregistrer_certificat_fsc`. Aucun texte libre en dehors de l'outil."""


def _client_anthropic():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    try:
        import anthropic
    except Exception:
        return None
    return anthropic.Anthropic(api_key=cle)


def _mime_image(filename: str, mime: str = "") -> str:
    if (mime or "").startswith("image/"):
        return mime
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/jpeg")


def lire_ia(file_bytes: bytes, filename: str, mime: str, kind: str) -> tuple[Optional[dict], Optional[str]]:
    """Rend `(lecture, erreur)`. Lecture au même format que `lire_motifs`."""
    client = _client_anthropic()
    if client is None:
        return None, "Clé ANTHROPIC_API_KEY absente : lecture IA indisponible."
    data = base64.standard_b64encode(file_bytes).decode()
    if kind == "pdf":
        bloc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    else:
        bloc = {"type": "image", "source": {"type": "base64", "media_type": _mime_image(filename, mime), "data": data}}
    try:
        reponse = client.messages.create(
            model=FSC_LECTURE_IA_MODELE,
            max_tokens=1500,
            system=_CONSIGNE,
            tools=[_OUTIL],
            tool_choice={"type": "tool", "name": "enregistrer_certificat_fsc"},
            messages=[{"role": "user", "content": [bloc, {"type": "text", "text": f"Fichier : {filename}"}]}],
        )
    except Exception as e:
        return None, f"Appel au modèle en échec : {e}"

    for b in reponse.content:
        if getattr(b, "type", "") != "tool_use":
            continue
        entree = b.input
        if isinstance(entree, str):
            try:
                entree = json.loads(entree)
            except Exception:
                return None, "Réponse du modèle illisible."
        licence = (entree.get("licence") or "").strip().upper() or None
        if licence:
            m = _RE_LICENCE.search(licence)
            licence = f"FSC-C{m.group(1)}" if m else None
        expiration = (entree.get("date_expiration") or "").strip()[:10] or None
        if expiration and not re.match(r"^\d{4}-\d{2}-\d{2}$", expiration):
            expiration = None
        vus = set()
        claims = []
        for c in entree.get("claims") or []:
            code = (c.get("code") or "").strip()
            if code in FSC_CLAIMS_PORTEE and code not in vus:
                vus.add(code)
                claims.append({"code": code, "extrait": (c.get("extrait") or "")[:300], "page": c.get("page")})
        return {
            "licences": [licence] if licence else [],
            "licence": licence,
            "certificat": (entree.get("certificat") or "").strip() or None,
            "expiration": expiration,
            "claims": [c for k in FSC_CLAIMS_PORTEE for c in claims if c["code"] == k],
            "remarques": (entree.get("remarques") or "").strip(),
        }, None
    return None, "Le modèle n'a pas rendu de lecture."


# ══════════════════════════════════════════════════════════════════
# Point d'entrée
# ══════════════════════════════════════════════════════════════════

def lire_certificat(file_bytes: bytes, filename: str, mime: str = "") -> dict:
    """Lecture complète d'un certificat.

    Rend {methode, modele, licences, licence, certificat, expiration, claims, note}.
    `methode` vaut « motifs », « ia » ou « aucune ». `note` dit ce qui empêche
    de conclure — c'est elle qu'on affiche quand `claims` est vide.
    """
    kind = type_fichier(filename, mime)
    vide = {"licences": [], "licence": None, "certificat": None, "expiration": None, "claims": []}

    if kind == "pdf":
        pages = texte_pdf(file_bytes)
        if pages:
            lecture = lire_motifs(pages)
            note = ""
            if not lecture["claims"]:
                note = ("Aucune catégorie écrite sur le certificat : il renvoie "
                        "probablement à la base publique FSC. Contrôle sur la base nécessaire.")
            return {"methode": "motifs", "modele": None, **lecture, "note": note}

    if kind in ("pdf", "image"):
        if not FSC_LECTURE_IA_ACTIVE:
            return {"methode": "aucune", "modele": None, **vide,
                    "note": "Document numérisé et lecture IA désactivée : contrôle sur la base FSC nécessaire."}
        lecture, erreur = lire_ia(file_bytes, filename, mime, kind)
        if erreur:
            return {"methode": "aucune", "modele": None, **vide, "note": erreur}
        note = lecture.pop("remarques", "") or ""
        if not lecture["claims"] and not note:
            note = "Aucune catégorie lisible sur le document : contrôle sur la base FSC nécessaire."
        return {"methode": "ia", "modele": FSC_LECTURE_IA_MODELE, **lecture, "note": note}

    return {"methode": "aucune", "modele": None, **vide,
            "note": "Format de fichier non lu (PDF ou image attendus)."}
