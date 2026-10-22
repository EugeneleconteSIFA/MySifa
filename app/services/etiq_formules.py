"""
Étiquettes spécifiques — formules, conditions et dates calculées.

Miroir exact de `static/mysifa_etiq_moteur.js` : l'aperçu de l'éditeur (JS)
et l'impression (ZPL / PDF, ici) doivent sortir la même valeur. Les deux
implémentations rejouent les mêmes cas : `tests/etiq_formules_cas.json`
(tests/test_etiq_avance.py et tests/test_etiq_moteur.js).

Évaluateur sûr : un analyseur à descente récursive sur une grammaire fermée.
Jamais d'eval, jamais d'accès à un attribut ni à un module : une formule ne
peut lire que les variables de l'étiquette et appeler les fonctions listées
dans FONCTIONS.

    expression := comparaison
    comparaison := concat ((= | <> | != | < | > | <= | >=) concat)*
    concat      := somme (& somme)*
    somme       := produit ((+ | -) produit)*
    produit     := unaire ((* | /) unaire)*
    unaire      := - unaire | primaire
    primaire    := nombre | "texte" | 'texte' | VRAI | FAUX | nom | {{nom}}
                 | FONCTION(arg ; arg …) | (expression)

Les arguments se séparent par « ; » ou « , ». Un nombre littéral s'écrit avec
un point (12.5) ; une valeur de variable « 12,5 » est lue comme 12,5.
Un résultat numérique s'affiche avec une virgule (2,5).
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

LONGUEUR_MAX = 1000
SORTIE_MAX = 2000
PROFONDEUR_MAX = 60


class ErreurFormule(ValueError):
    """Message affichable tel quel dans l'éditeur."""


# ─── Valeurs ────────────────────────────────────────────────────────────

_NOMBRE_RE = re.compile(r"^-?\d+(\.\d+)?$")


def nombre(v: Any) -> float:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").replace(" ", "").replace(" ", "").replace(",", ".")
    if not _NOMBRE_RE.match(s):
        raise ErreurFormule(f"« {str(v)[:30]} » n'est pas un nombre.")
    return float(s)


def _est_nombre(v: Any) -> bool:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return True
    if isinstance(v, str) and v.strip():
        try:
            nombre(v)
            return True
        except ErreurFormule:
            return False
    return False


def texte(v: Any) -> str:
    if isinstance(v, bool):
        return "VRAI" if v else "FAUX"
    if isinstance(v, (int, float)):
        if not math.isfinite(v):
            raise ErreurFormule("Résultat numérique invalide.")
        if float(v).is_integer() and abs(v) < 1e15:
            return str(int(v))
        s = f"{v:.10f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    return "" if v is None else str(v)


def vrai(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v or "").strip()
    return bool(s) and s != "0" and s.upper() != "FAUX"


def arrondi(x: float, n: int = 0) -> float:
    n = int(n)
    q = Decimal(1).scaleb(-n)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


# ─── Analyse lexicale ───────────────────────────────────────────────────

_JETONS = re.compile(r"""
    (?P<espace>\s+)
  | (?P<var>\{\{\s*[A-Za-z_][A-Za-z0-9_]*\s*\}\})
  | (?P<nombre>\d+(?:\.\d+)?)
  | (?P<chaine>"(?:[^"]|"")*"|'(?:[^']|'')*')
  | (?P<nom>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><=|>=|<>|!=|[=<>+\-*/&(),;])
""", re.X)


def _jetons(expr: str) -> list:
    out, i = [], 0
    while i < len(expr):
        m = _JETONS.match(expr, i)
        if not m:
            raise ErreurFormule(f"Caractère inattendu « {expr[i]} » (position {i + 1}).")
        i = m.end()
        typ = m.lastgroup
        val = m.group(typ)
        if typ == "espace":
            continue
        if typ == "var":
            out.append(("nom", val.strip("{} \t").lower(), True))
        elif typ == "nombre":
            out.append(("nombre", float(val), False))
        elif typ == "chaine":
            q = val[0]
            out.append(("chaine", val[1:-1].replace(q + q, q), False))
        elif typ == "nom":
            out.append(("nom", val, False))
        else:
            out.append(("op", ";" if val == "," else val, False))
    out.append(("fin", None, False))
    return out


# ─── Fonctions ──────────────────────────────────────────────────────────

def _f_stxt(t, debut, n):
    d = max(1, int(nombre(debut)))
    return texte(t)[d - 1: d - 1 + max(0, int(nombre(n)))]


def _f_zeros(x, n):
    s = texte(x)
    signe = "-" if s.startswith("-") else ""
    return signe + s.lstrip("-").rjust(int(nombre(n)), "0")


def _f_texte(x, n=0):
    n = max(0, min(10, int(nombre(n))))
    return f"{arrondi(nombre(x), n):.{n}f}".replace(".", ",")


def _f_cle_gs1(t):
    ch = re.sub(r"\D", "", texte(t))
    if not ch:
        raise ErreurFormule("CLE_GS1 : chiffres attendus.")
    tot = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(ch)))
    return str((10 - tot % 10) % 10)


def _div(a, b):
    b = nombre(b)
    if b == 0:
        raise ErreurFormule("Division par zéro.")
    return nombre(a) / b


# nom → (arguments mini, maxi (None = illimité), fonction)
FONCTIONS = {
    "MAJUSCULE": (1, 1, lambda t: texte(t).upper()),
    "MAJ": (1, 1, lambda t: texte(t).upper()),
    "MINUSCULE": (1, 1, lambda t: texte(t).lower()),
    "CONCAT": (1, None, lambda *a: "".join(texte(x) for x in a)),
    "GAUCHE": (1, 2, lambda t, n=1: texte(t)[: max(0, int(nombre(n)))]),
    "DROITE": (1, 2, lambda t, n=1: (texte(t)[-int(nombre(n)):] if int(nombre(n)) > 0 else "")),
    "STXT": (3, 3, _f_stxt),
    "LONGUEUR": (1, 1, lambda t: float(len(texte(t)))),
    "SUPPRESPACE": (1, 1, lambda t: " ".join(texte(t).split())),
    "REMPLACER": (3, 3, lambda t, a, b: texte(t).replace(texte(a), texte(b)) if texte(a) else texte(t)),
    "SI": (2, 3, lambda c, a, b="": a if vrai(c) else b),
    "VIDE": (1, 1, lambda t: not texte(t).strip()),
    "ET": (1, None, lambda *a: all(vrai(x) for x in a)),
    "OU": (1, None, lambda *a: any(vrai(x) for x in a)),
    "NON": (1, 1, lambda x: not vrai(x)),
    "ARRONDI": (1, 2, lambda x, n=0: arrondi(nombre(x), int(nombre(n)))),
    "ENT": (1, 1, lambda x: float(math.floor(nombre(x)))),
    "ABS": (1, 1, lambda x: abs(nombre(x))),
    "MIN": (1, None, lambda *a: min(nombre(x) for x in a)),
    "MAX": (1, None, lambda *a: max(nombre(x) for x in a)),
    "TEXTE": (1, 2, _f_texte),
    "ZEROS": (2, 2, _f_zeros),
    "NUM": (1, 1, lambda t: nombre(t)),
    "CLE_GS1": (1, 1, _f_cle_gs1),
}


# ─── Analyse syntaxique + évaluation ────────────────────────────────────

class _Analyseur:
    def __init__(self, expr: str, valeurs: dict):
        self.j = _jetons(expr)
        self.i = 0
        self.v = valeurs
        self.prof = 0

    def voir(self):
        return self.j[self.i]

    def prendre(self, op=None):
        t = self.j[self.i]
        if op is not None and not (t[0] == "op" and t[1] == op):
            attendu = "« " + op + " »"
            trouve = "la fin" if t[0] == "fin" else f"« {t[1]} »"
            raise ErreurFormule(f"{attendu} attendu, {trouve} trouvé.")
        self.i += 1
        return t

    def est_op(self, *ops):
        t = self.voir()
        return t[0] == "op" and t[1] in ops

    def descendre(self):
        self.prof += 1
        if self.prof > PROFONDEUR_MAX:
            raise ErreurFormule("Formule trop imbriquée.")

    def expression(self):
        self.descendre()
        g = self.concat()
        while self.est_op("=", "<>", "!=", "<", ">", "<=", ">="):
            op = self.prendre()[1]
            d = self.concat()
            g = _comparer(g, op, d)
        self.prof -= 1
        return g

    def concat(self):
        g = self.somme()
        while self.est_op("&"):
            self.prendre()
            g = texte(g) + texte(self.somme())
        return g

    def somme(self):
        g = self.produit()
        while self.est_op("+", "-"):
            op = self.prendre()[1]
            d = self.produit()
            g = nombre(g) + nombre(d) if op == "+" else nombre(g) - nombre(d)
        return g

    def produit(self):
        g = self.unaire()
        while self.est_op("*", "/"):
            op = self.prendre()[1]
            d = self.unaire()
            g = nombre(g) * nombre(d) if op == "*" else _div(g, d)
        return g

    def unaire(self):
        if self.est_op("-"):
            self.prendre()
            self.descendre()
            r = -nombre(self.unaire())
            self.prof -= 1
            return r
        return self.primaire()

    def primaire(self):
        t = self.prendre()
        typ, val, accolades = t
        if typ == "nombre" or typ == "chaine":
            return val
        if typ == "op" and val == "(":
            r = self.expression()
            self.prendre(")")
            return r
        if typ == "nom":
            if not accolades and self.est_op("("):
                return self.appel(val.upper())
            if not accolades and val.upper() == "VRAI":
                return True
            if not accolades and val.upper() == "FAUX":
                return False
            return self.v.get(val.lower(), "")
        if typ == "fin":
            raise ErreurFormule("Formule incomplète.")
        raise ErreurFormule(f"« {val} » inattendu.")

    def appel(self, nom):
        if nom not in FONCTIONS:
            raise ErreurFormule(f"Fonction inconnue : {nom}.")
        mini, maxi, fn = FONCTIONS[nom]
        self.prendre("(")
        args = []
        if not self.est_op(")"):
            args.append(self.expression())
            while self.est_op(";"):
                self.prendre()
                args.append(self.expression())
        self.prendre(")")
        if len(args) < mini or (maxi is not None and len(args) > maxi):
            borne = str(mini) if mini == maxi else (f"{mini} à {maxi}" if maxi else f"{mini} ou plus")
            raise ErreurFormule(f"{nom} : {borne} argument(s) attendu(s).")
        return fn(*args)


def _comparer(a, op, b):
    if _est_nombre(a) and _est_nombre(b):
        x, y = nombre(a), nombre(b)
    else:
        x, y = texte(a).lower(), texte(b).lower()
    return {"=": x == y, "<>": x != y, "!=": x != y, "<": x < y,
            ">": x > y, "<=": x <= y, ">=": x >= y}[op]


def evaluer_brut(expr: str, valeurs: dict):
    expr = (expr or "").strip()
    if not expr:
        return ""
    if len(expr) > LONGUEUR_MAX:
        raise ErreurFormule(f"Formule trop longue — {LONGUEUR_MAX} caractères au plus.")
    a = _Analyseur(expr, {str(k).lower(): v for k, v in (valeurs or {}).items()})
    r = a.expression()
    if a.voir()[0] != "fin":
        raise ErreurFormule(f"« {a.voir()[1]} » inattendu après la formule.")
    return r


def evaluer(expr: str, valeurs: dict) -> dict:
    """{"valeur": texte, "erreur": message ou ""} — jamais d'exception."""
    try:
        return {"valeur": texte(evaluer_brut(expr, valeurs))[:SORTIE_MAX], "erreur": ""}
    except ErreurFormule as e:
        return {"valeur": "", "erreur": str(e)}
    except (RecursionError, OverflowError, ValueError, TypeError):
        return {"valeur": "", "erreur": "Formule invalide."}


def condition_vraie(expr: str, valeurs: dict) -> bool:
    """Une condition vide est vraie ; une condition en erreur est fausse."""
    if not (expr or "").strip():
        return True
    try:
        return vrai(evaluer_brut(expr, valeurs))
    except Exception:
        return False


# ─── Dates calculées ────────────────────────────────────────────────────

MOIS_COURTS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
               "sept.", "oct.", "nov.", "déc.")
MOIS_LONGS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
              "septembre", "octobre", "novembre", "décembre")

# Formats proposés dans l'éditeur (le champ reste libre).
FORMATS_DATE = (
    ("%d/%m/%Y", "JJ/MM/AAAA"),
    ("%d/%m/%y", "JJ/MM/AA"),
    ("%d.%m.%Y", "JJ.MM.AAAA"),
    ("%Y-%m-%d", "AAAA-MM-JJ"),
    ("%m/%Y", "MM/AAAA (DLUO au mois)"),
    ("%d %b %Y", "JJ mois AAAA"),
    ("S%V-%G", "Semaine ISO (S43-2026)"),
    ("%G%V", "AAAASS"),
    ("%y%j", "Lot daté AAJJJ"),
    ("%y%m%d", "AAMMJJ (GS1)"),
)


def semaine_iso(d) -> tuple[int, int, int]:
    """(année ISO, semaine ISO, jour ISO 1=lundi)."""
    y, w, j = d.isocalendar()[:3]
    return y, w, j


def formater_date(d, fmt: str) -> str:
    """strftime limité aux codes listés, identique côté JS et sans locale."""
    if not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    iy, iw, ij = semaine_iso(d)
    codes = {
        "d": f"{d.day:02d}", "m": f"{d.month:02d}", "Y": f"{d.year:04d}", "y": f"{d.year % 100:02d}",
        "H": f"{d.hour:02d}", "M": f"{d.minute:02d}", "S": f"{d.second:02d}",
        "j": f"{d.timetuple().tm_yday:03d}", "V": f"{iw:02d}", "G": f"{iy:04d}", "g": f"{iy % 100:02d}",
        "u": str(ij), "b": MOIS_COURTS[d.month - 1], "B": MOIS_LONGS[d.month - 1], "%": "%",
    }
    out, i = [], 0
    fmt = fmt or "%d/%m/%Y"
    while i < len(fmt):
        c = fmt[i]
        if c == "%" and i + 1 < len(fmt) and fmt[i + 1] in codes:
            out.append(codes[fmt[i + 1]])
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


_DATE_FR = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})$")
_DATE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
_DATE_COMPACTE = re.compile(r"^(\d{2}|\d{4})(\d{2})(\d{2})$")   # AAMMJJ (GS1), AAAAMMJJ


def lire_date(s: Any) -> Optional[date]:
    """JJ/MM/AAAA, JJ/MM/AA, JJ.MM.AAAA, AAAA-MM-JJ, AAMMJJ, AAAAMMJJ (heure ignorée)."""
    s = str(s or "").strip()
    try:
        m = _DATE_ISO.match(s)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = _DATE_COMPACTE.match(s)
        if m:
            a = int(m.group(1))
            return date(a + 2000 if a < 100 else a, int(m.group(2)), int(m.group(3)))
        m = _DATE_FR.match(s)
        if m:
            a = int(m.group(3))
            if a < 100:
                a += 2000
            return date(a, int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    return None


def ajouter_mois(d: date, n: int) -> date:
    m = d.month - 1 + int(n)
    a = d.year + m // 12
    m = m % 12 + 1
    jours = [31, 29 if (a % 4 == 0 and (a % 100 or a % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(a, m, min(d.day, jours[m - 1]))


def calculer_date(var: dict, valeurs: dict, maintenant: Optional[datetime] = None) -> str:
    """Valeur d'une variable de type date.

    base       « impression » (jour de l'impression) ou le nom d'une autre
               variable (date de fabrication saisie, date d'un OF…)
    decalage_mois, decalage_jours   DLUO, DDM : base + N mois + N jours
    format     voir formater_date
    """
    maintenant = maintenant or datetime.now()
    base = (var.get("base") or "impression").strip().lower()
    if base == "impression":
        d = maintenant
    else:
        lu = lire_date(valeurs.get(base, ""))
        if lu is None:
            return ""
        d = datetime(lu.year, lu.month, lu.day, maintenant.hour, maintenant.minute)
    if var.get("decalage_mois"):
        dd = ajouter_mois(d.date(), int(var["decalage_mois"]))
        d = d.replace(year=dd.year, month=dd.month, day=dd.day)
    d = d + timedelta(days=int(var.get("decalage_jours") or 0))
    return formater_date(d, var.get("format") or "%d/%m/%Y")
