"""
L'OF et la fiche technique d'un dossier disent-ils la même chose ?

Le cas qui a fait naître ce module (18/11/2026)
----------------------------------------------
Dossier 9932921, produit 1341/0012, Cohésio 1. L'OF du 18/11 dit 110 x 150 mm,
PP 95µ blanc mat. La fiche technique, créée dans Access le 11/09 en dupliquant
la 1341/0008, dit 100 x 99,6 mm, machine DSI, Vélin H400 — un autre produit.
Le contrôle de cohérence ne comparait que des ids de matière (vides sur les
documents venus d'Access) et la quantité au mille : il n'a signalé qu'un
« 38,10 contre 33,87 », que personne n'a lu comme « mauvaise fiche ».

Ce que fait le module
---------------------
- `comparer(of, fiche)` : les écarts champ par champ — machine, format,
  matière (par famille, sur le texte quand les ids manquent), laize, quantité
  au mille. Un champ vide d'un côté ne prouve rien : il n'est pas comparé.
- `verdict(of, fiche, ...)` : les écarts, plus QUI fait foi. Règle d'Eugène :
  le document le plus récent est le plus réel. À date égale, l'OF l'emporte —
  il décrit la commande en cours, la fiche décrit le produit en général.
- `fiche_affichee(fiche, verdict)` : la fiche telle qu'on l'affiche et
  l'imprime. Quand l'OF fait foi, ses valeurs remplacent celles de la fiche
  sur les seuls champs en désaccord, et `_substitutions` dit lesquels.

Ce que le module ne fait PAS
----------------------------
Il n'écrit rien. La fiche en base reste fausse tant que quelqu'un ne la
corrige pas (dans Access, ou dans MySifa — le pont respecte les champs saisis
à la main). Le déstockage et les besoins matières lisent toujours la fiche
réelle : la substitution est un affichage, signalé comme tel, jamais un
calcul. Décision du 18/11/2026 : « alerte + le plus récent fait foi à
l'écran ».
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from config import (
    ACCORD_FORMAT_TOLERANCE_MM,
    ACCORD_QAM_TOLERANCE,
    FAMILLES_MATIERE,
)
from app.services.fiche_choix import cle_machine

# Champs dont le désaccord désigne une fiche d'un autre produit, pas un
# réglage à reprendre. Deux sur trois et l'alerte change de ton.
CHAMPS_IDENTITE = ("machine", "format", "matiere")


# ── Lecture des valeurs ─────────────────────────────────────────────

def _sans_accent(txt: Any) -> str:
    t = unicodedata.normalize("NFKD", str(txt or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def _nombre(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        f = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


_RE_FORMAT = re.compile(r"(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)", re.I)


def format_mm(texte: Any) -> Optional[Tuple[float, float]]:
    """« 110 x 150 mm » → (110.0, 150.0). None si rien d'exploitable."""
    m = _RE_FORMAT.search(str(texte or ""))
    if not m:
        return None
    a, b = _nombre(m.group(1)), _nombre(m.group(2))
    return (a, b) if a and b else None


def format_fiche(ft: dict) -> Optional[Tuple[float, float]]:
    """Le format de la fiche : son libellé, sinon la laize × longueur étiquette."""
    f = format_mm(ft.get("format"))
    if f:
        return f
    a, b = _nombre(ft.get("eti_laize")), _nombre(ft.get("eti_longueur"))
    return (a, b) if a and b else None


def _meme_format(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
    tol = ACCORD_FORMAT_TOLERANCE_MM
    droit = abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol
    tourne = abs(a[0] - b[1]) <= tol and abs(a[1] - b[0]) <= tol
    return droit or tourne


def famille_matiere(texte: Any) -> Optional[str]:
    """« PP 95µ BLANC MAT » → « pp ». None si aucune famille, ou plusieurs."""
    mots = set(re.findall(r"[a-z]+", _sans_accent(texte)))
    if not mots:
        return None
    trouvees = {fam for fam, cles in FAMILLES_MATIERE.items()
                if any(c in mots for c in cles)}
    return trouvees.pop() if len(trouvees) == 1 else None


def _fmt_mm(f: Tuple[float, float]) -> str:
    def n(x: float) -> str:
        return (f"{x:.1f}".rstrip("0").rstrip(".")).replace(".", ",")
    return f"{n(f[0])} x {n(f[1])} mm"


def _fmt_nombre(v: float, dec: int = 2) -> str:
    return f"{v:.{dec}f}".replace(".", ",")


# ── Comparaison ─────────────────────────────────────────────────────

def comparer(of: dict, ft: dict) -> List[Dict[str, Any]]:
    """Les champs sur lesquels l'OF et la fiche se contredisent."""
    of, ft = dict(of or {}), dict(ft or {})
    ecarts: List[Dict[str, Any]] = []

    def ecart(champ: str, libelle: str, v_of: str, v_ft: str) -> None:
        ecarts.append({"champ": champ, "libelle": libelle, "of": v_of, "fiche": v_ft,
                       "identite": champ in CHAMPS_IDENTITE})

    # Machine — « COHESIO » sans numéro vaut pour les deux Cohésio.
    m_of, m_ft = cle_machine(of.get("machine")), cle_machine(ft.get("machine"))
    if m_of and m_ft and m_of != m_ft and not (
            m_of.startswith(m_ft) or m_ft.startswith(m_of)):
        ecart("machine", "Machine", str(of.get("machine")), str(ft.get("machine")))

    # Format
    f_of, f_ft = format_mm(of.get("format")), format_fiche(ft)
    if f_of and f_ft and not _meme_format(f_of, f_ft):
        ecart("format", "Format", _fmt_mm(f_of), _fmt_mm(f_ft))

    # Matière — l'id quand les deux en ont un, sinon la famille du libellé.
    id_of, id_ft = of.get("matiere_ref_id"), ft.get("support_ref_id")
    t_of, t_ft = of.get("matiere"), ft.get("support") or ft.get("matiere")
    if id_of and id_ft:
        if int(id_of) != int(id_ft):
            ecart("matiere", "Matière", str(t_of or f"#{id_of}"), str(t_ft or f"#{id_ft}"))
    else:
        fa_of, fa_ft = famille_matiere(t_of), famille_matiere(t_ft)
        if fa_of and fa_ft and fa_of != fa_ft:
            ecart("matiere", "Matière", str(t_of), str(t_ft))

    # Laize bobine — seulement contre la laize de la fiche, pas l'optimale.
    l_of, l_ft = _nombre(of.get("laize")), _nombre(ft.get("laize"))
    if l_of and l_ft and abs(l_of - l_ft) > 0.5:
        ecart("laize", "Laize", _fmt_nombre(l_of, 0), _fmt_nombre(l_ft, 0))

    # Quantité au mille
    q_of, q_ft = _nombre(of.get("qte_au_mille")), _nombre(ft.get("qte_au_mille"))
    if q_of and q_ft and abs(q_of - q_ft) / q_ft > ACCORD_QAM_TOLERANCE:
        ecart("qte_au_mille", "Quantité au mille", _fmt_nombre(q_of), _fmt_nombre(q_ft))

    return ecarts


# ── Qui fait foi ────────────────────────────────────────────────────

def _jour(v: Any) -> Optional[date]:
    """« 2026-11-18T09:40:59 », « 2026-09-11 » ou « 18/11/2026 » → date."""
    s = str(v or "").strip()
    if not s:
        return None
    for fmt, n in (("%Y-%m-%d", 10), ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(s[:n], fmt).date()
        except ValueError:
            continue
    return None


def date_of(of: dict) -> Optional[date]:
    """Le jour où l'OF a été établi ou réimporté — le plus tardif des deux."""
    jours = [d for d in (_jour(of.get("date_creation")), _jour(of.get("date_import"))) if d]
    return max(jours) if jours else None


def date_fiche(ft: dict, derniere_correction: Any = None) -> Optional[date]:
    """Le jour de la dernière modification connue de la fiche.

    `date_modif` vient d'Access. Une correction faite dans MySifa ne la touche
    pas : l'appelant passe la date de la dernière écriture humaine journalisée
    (`derniere_correction_fiche`).
    """
    jours = [d for d in (_jour(ft.get("date_modif")), _jour(derniere_correction)) if d]
    if not jours:
        jours = [d for d in (_jour(ft.get("date_import")),) if d]
    return max(jours) if jours else None


def derniere_correction_fiche(conn, fiche_id: Any) -> Optional[str]:
    """Dernière valeur écrite à la main sur la fiche, d'après le journal."""
    try:
        r = conn.execute(
            "SELECT MAX(at) FROM documents_valeurs_historique "
            "WHERE table_nom = 'fiches_techniques' AND doc_id = ? "
            "AND refuse = 0 AND origine = 'manuel'",
            (fiche_id,),
        ).fetchone()
    except Exception:
        return None
    return r[0] if r and r[0] else None


def verdict(of: dict, ft: dict, derniere_correction: Any = None) -> Dict[str, Any]:
    """Écarts, document qui fait foi, et le message à afficher."""
    ecarts = comparer(of, ft)
    d_of, d_ft = date_of(of), date_fiche(ft, derniere_correction)
    # À date égale (ou inconnue des deux côtés), l'OF : il décrit la commande.
    if d_ft and (not d_of or d_ft > d_of):
        source = "fiche"
    else:
        source = "of"
    nb_identite = sum(1 for e in ecarts if e["identite"])
    autre_produit = nb_identite >= 2
    return {
        "accord": not ecarts,
        "ecarts": ecarts,
        "source": source,
        "date_of": d_of.isoformat() if d_of else None,
        "date_fiche": d_ft.isoformat() if d_ft else None,
        "autre_produit": autre_produit,
        "of_numero": of.get("of_numero"),
        "fiche_id": ft.get("id"),
        "fiche_reference": ft.get("reference"),
        "message": message(ecarts, source, d_of, d_ft, of.get("of_numero"), autre_produit),
    }


def _jour_fr(d: Optional[date]) -> str:
    return d.strftime("%d/%m/%Y") if d else "date inconnue"


def message(ecarts: List[dict], source: str, d_of: Optional[date], d_ft: Optional[date],
            of_numero: Any, autre_produit: bool) -> str:
    if not ecarts:
        return ""
    champs = ", ".join(e["libelle"].lower() for e in ecarts)
    tete = ("La fiche technique semble être celle d'un autre produit"
            if autre_produit else "L'OF et la fiche technique se contredisent")
    of_txt = f"l'OF {of_numero}" if of_numero else "l'OF"
    if source == "of":
        return (f"{tete} ({champs}). {of_txt[0].upper() + of_txt[1:]} du {_jour_fr(d_of)} "
                f"est plus récent que la fiche "
                f"({_jour_fr(d_ft)}) : ses valeurs sont reprises. "
                "Outillage et conditionnement de la fiche à vérifier.")
    return (f"{tete} ({champs}). La fiche du {_jour_fr(d_ft)} est plus récente que "
            f"{of_txt} ({_jour_fr(d_of)}) : vérifier l'OF.")


# ── La fiche telle qu'on l'affiche ──────────────────────────────────

def fiche_affichee(ft: dict, of: dict, v: Dict[str, Any]) -> Dict[str, Any]:
    """La fiche à afficher : celle de la base, ou corrigée par l'OF s'il fait foi.

    Seuls les champs en désaccord sont remplacés. Le reste de la fiche — outils,
    module, conditionnement — est laissé tel quel : on ne sait pas le déduire
    de l'OF, et le message dit qu'il est à vérifier.
    """
    out = dict(ft or {})
    out["_substitutions"] = []
    if v.get("accord") or v.get("source") != "of":
        return out
    of = dict(of or {})
    for e in v.get("ecarts") or []:
        champ = e["champ"]
        if champ == "machine":
            out["machine"] = of.get("machine")
        elif champ == "format":
            f = format_mm(of.get("format"))
            out["format"] = of.get("format")
            if f:
                out["eti_laize"], out["eti_longueur"] = f
        elif champ == "matiere":
            out["support"] = of.get("matiere")
        elif champ == "laize":
            out["laize"] = of.get("laize")
        elif champ == "qte_au_mille":
            out["qte_au_mille"] = of.get("qte_au_mille")
        else:
            continue
        out["_substitutions"].append(champ)
    return out


# ── Accès base ──────────────────────────────────────────────────────

def charger(conn, of_id: Any, fiche_id: Any) -> Optional[Dict[str, Any]]:
    """OF, fiche et verdict pour un couple d'ids. None si l'un manque."""
    if not of_id or not fiche_id:
        return None
    of = conn.execute("SELECT * FROM of_imports WHERE id = ?", (of_id,)).fetchone()
    ft = conn.execute("SELECT * FROM fiches_techniques WHERE id = ?", (fiche_id,)).fetchone()
    if not of or not ft:
        return None
    of, ft = dict(of), dict(ft)
    return {"of": of, "fiche": ft,
            "verdict": verdict(of, ft, derniere_correction_fiche(conn, ft["id"]))}
