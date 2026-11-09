"""MyCompta — comparaison des factures RVGI et du grand-livre clients CW.

Deux éditions PDF du même mois :
  - « Analyse des ventes par client » de RVGI, édition détaillée : une ligne
    par facture, montant HORS TAXES ;
  - « Grand-livre des comptes clients » de CW : les lignes du journal des
    ventes (VE) sont les factures et avoirs, montant TOUTES TAXES.

Une facture est identifiée par son numéro ET sa date. Elle est concordante
quand le TTC de CW vaut le HT de RVGI multiplié par (1 + un taux légal), à la
tolérance près. Tout le reste est un écart, accompagné quand c'est possible
d'une piste de correction.

Lecture seule : rien n'est écrit en base, les PDF ne sont pas conservés.
"""

from __future__ import annotations

import io
import re
from typing import Dict, List, Optional, Tuple

from config import (
    COMPTA_CMP_JOURNAL_VENTES,
    COMPTA_CMP_TAUX_TVA,
    COMPTA_CMP_TOLERANCE,
)

# Repères de reconnaissance des deux éditions (titres imprimés par les
# logiciels, pas des données de l'entreprise).
_MARQUE_RVGI = "analyse des ventes"
_MARQUE_CW = "grands-livres"

_RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_RE_RVGI_CLIENT = re.compile(r"^(\d+) - (.+)$")
# No pièce, date, quantité, total HT. Chaque montant porte une seule virgule,
# ce qui sépare sans ambiguïté la quantité du HT malgré les espaces de milliers.
_RE_RVGI_FACTURE = re.compile(
    r"^(\S+) (\d{2}/\d{2}/\d{4}) (-?[\d ]+?,\d{2}-?) (-?[\d ]+?,\d{2}-?)$"
)
_RE_RVGI_TOTAL = re.compile(r"^Total HT Net\s*:\s*(-?[\d ]+,\d{2}-?)")
_RE_PERIODE = re.compile(r"[Dd]u (\d{2}/\d{2}/\d{4}) au (\d{2}/\d{2}/\d{4})")

# Montant CW : « 424,00 », « 744,59DD* » (lettrage collé au débit).
_RE_CW_MONTANT = re.compile(r"^(-?\d{1,3},\d{2})([A-Za-z]*\*?)$")
_RE_CW_GROUPE = re.compile(r"^-?\d{1,3}$")


class DocumentNonReconnu(ValueError):
    pass


# ── Utilitaires ──────────────────────────────────────────────────────────

def _montant(txt: str) -> float:
    s = txt.replace(" ", "").replace(" ", "").replace("\xa0", "")
    neg = s.endswith("-") or s.startswith("-")
    s = s.strip("-").replace(",", ".")
    v = float(s)
    return -v if neg else v


def _iso(d: str) -> str:
    j, m, a = d.split("/")
    return f"{a}-{m}-{j}"


def _texte_pdf(data: bytes) -> List[str]:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return [(p.extract_text() or "") for p in pdf.pages]


def type_document(data: bytes) -> str:
    """'rvgi', 'cw' ou lève DocumentNonReconnu."""
    try:
        pages = _texte_pdf(data)
    except Exception:
        raise DocumentNonReconnu("Fichier illisible — un PDF est attendu.")
    debut = " ".join(pages[:2]).lower()
    if _MARQUE_RVGI in debut:
        return "rvgi"
    if _MARQUE_CW in debut:
        return "cw"
    raise DocumentNonReconnu(
        "Document non reconnu — attendu : analyse des ventes par client (RVGI) "
        "ou grand-livre des comptes clients (CW)."
    )


# ── Lecture RVGI ─────────────────────────────────────────────────────────

def lire_rvgi(data: bytes) -> Dict:
    pages = _texte_pdf(data)
    client = ""
    factures: List[Dict] = []
    total = None
    periode = None
    for txt in pages:
        for ligne in txt.split("\n"):
            ligne = ligne.strip()
            if periode is None:
                mp = _RE_PERIODE.search(ligne)
                if mp:
                    periode = (_iso(mp.group(1)), _iso(mp.group(2)))
            mt = _RE_RVGI_TOTAL.match(ligne)
            if mt:
                total = _montant(mt.group(1))
                continue
            mf = _RE_RVGI_FACTURE.match(ligne)
            if mf:
                factures.append({
                    "numero": mf.group(1),
                    "date": _iso(mf.group(2)),
                    "client": client,
                    "ht": round(_montant(mf.group(4)), 2),
                })
                continue
            mc = _RE_RVGI_CLIENT.match(ligne)
            if mc and not ligne.startswith("Total"):
                client = mc.group(2).strip()
    return {"factures": factures, "total_ht": total, "periode": periode}


# ── Lecture du grand-livre CW ────────────────────────────────────────────

def _rangees(page) -> List[List[dict]]:
    """Mots de la page regroupés par ligne (même hauteur à 3 pt près)."""
    mots = sorted(page.extract_words(), key=lambda w: (round(w["top"]), w["x0"]))
    rangees: List[List[dict]] = []
    for w in mots:
        if rangees and abs(rangees[-1][0]["top"] - w["top"]) <= 3:
            rangees[-1].append(w)
        else:
            rangees.append([w])
    return [sorted(r, key=lambda w: w["x0"]) for r in rangees]


def _colonnes(rangee: List[dict]) -> Optional[Dict[str, float]]:
    """Abscisses des en-têtes Débit / Let. / Solde, si la rangée est l'en-tête."""
    textes = {w["text"]: w["x0"] for w in rangee}
    if "Débit" in textes and "Solde" in textes and "Date" in textes:
        return {
            "debit": textes["Débit"],
            "let": textes.get("Let.", textes["Débit"] + 38),
            "solde": textes["Solde"],
        }
    return None


def _montants_cw(rangee: List[dict], col: Dict[str, float]) -> Tuple[float, float, int]:
    """(débit, crédit, index du premier mot de montant) d'une ligne d'écriture."""
    debit = credit = 0.0
    premier = len(rangee)
    for i, w in enumerate(rangee):
        m = _RE_CW_MONTANT.match(w["text"])
        if not m:
            continue
        # Groupes de milliers à gauche, collés au montant.
        j = i
        parts = [m.group(1)]
        while j - 1 >= 0:
            g = rangee[j - 1]
            if (_RE_CW_GROUPE.match(g["text"])
                    and rangee[j]["x0"] - g["x1"] <= 4
                    and g["x0"] >= col["debit"] - 40):
                parts.insert(0, g["text"])
                j -= 1
            else:
                break
        valeur = _montant(" ".join(parts))
        if w["x0"] < col["let"]:
            debit += valeur
        elif w["x0"] < col["solde"]:
            credit += valeur
        else:
            continue  # solde progressif
        premier = min(premier, j)
    return debit, credit, premier


def lire_cw(data: bytes) -> Dict:
    import pdfplumber

    factures: Dict[Tuple[str, str], Dict] = {}
    compte = client = ""
    periode = None
    col = None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            if periode is None:
                mp = _RE_PERIODE.search(page.extract_text() or "")
                if mp:
                    periode = (_iso(mp.group(1)), _iso(mp.group(2)))
            for r in _rangees(page):
                c = _colonnes(r)
                if c:
                    col = c
                    continue
                if r[0]["text"] == "Compte" and len(r) >= 2:
                    compte = r[1]["text"]
                    client = " ".join(w["text"] for w in r[2:])
                    continue
                if col is None or len(r) < 4 or not _RE_DATE.match(r[0]["text"]):
                    continue
                if r[2]["text"] != COMPTA_CMP_JOURNAL_VENTES:
                    continue
                debit, credit, premier = _montants_cw(r, col)
                if not debit and not credit:
                    continue
                cle = (r[1]["text"], _iso(r[0]["text"]))
                f = factures.setdefault(cle, {
                    "numero": cle[0], "date": cle[1], "compte": compte,
                    "client": client, "ttc": 0.0,
                    "libelle": " ".join(w["text"] for w in r[3:premier]),
                })
                f["ttc"] = round(f["ttc"] + debit - credit, 2)
    return {"factures": list(factures.values()), "periode": periode}


# ── Comparaison ──────────────────────────────────────────────────────────

def _taux_concordant(ht: float, ttc: float) -> Optional[float]:
    for t in COMPTA_CMP_TAUX_TVA:
        if abs(ht * (1 + t / 100) - ttc) <= COMPTA_CMP_TOLERANCE:
            return t
    return None


def _taux_proche(ht: float, ttc: float) -> float:
    return min(COMPTA_CMP_TAUX_TVA, key=lambda t: abs(ht * (1 + t / 100) - ttc))


def _distance(a: str, b: str) -> int:
    """Distance d'édition (numéros de pièce : quelques caractères)."""
    prec = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cour = [i]
        for j, cb in enumerate(b, 1):
            cour.append(min(prec[j] + 1, cour[j - 1] + 1, prec[j - 1] + (ca != cb)))
        prec = cour
    return prec[-1]


def _fr(v: float) -> str:
    s = f"{abs(v):,.2f}".replace(",", " ").replace(".", ",")
    return ("-" if v < 0 else "") + s


def _diagnostic_montant(ht: float, ttc: float) -> Tuple[Optional[float], Optional[str]]:
    """(taux reconnu, piste) pour une facture présente des deux côtés."""
    t = _taux_concordant(ht, ttc)
    if t is not None:
        return t, None
    if _taux_concordant(-ht, ttc) is not None:
        return None, ("Montant de signe opposé : un avoir a été passé comme une "
                      "facture, ou l'inverse. Corriger le sens de l'écriture.")
    tp = _taux_proche(ht, ttc)
    attendu = round(ht * (1 + tp / 100), 2)
    ecart = round(ttc - attendu, 2)
    piste = (f"TTC attendu {_fr(attendu)} € (TVA {_fr(tp).rstrip('0').rstrip(',')} %), "
             f"écart de {_fr(ecart)} €.")
    centimes = round(abs(ecart) * 100)
    remise = (1 - ttc / attendu) * 100 if attendu else 0
    if abs(ttc - ht) <= COMPTA_CMP_TOLERANCE:
        piste += " Le montant CW égale le HT : TVA oubliée dans CW."
    elif 0.4 <= abs(remise) <= 15 and abs(remise * 2 - round(remise * 2)) <= 0.05:
        pct = _fr(round(remise * 2) / 2).rstrip("0").rstrip(",")
        piste += (f" Le TTC CW vaut le TTC attendu {'moins' if remise > 0 else 'plus'} "
                  f"{pct.lstrip('-')} % : remise ou escompte appliqué d'un seul côté.")
    elif centimes and centimes % 100 == 0:
        piste += " Écart d'un montant rond : frais ou ligne présents d'un seul côté."
    elif centimes and centimes % 9 == 0:
        piste += " Écart divisible par 9 : inversion de deux chiffres probable à la saisie."
    return None, piste


def comparer(rvgi: Dict, cw: Dict) -> Dict:
    # Regroupement par clé (numéro, date) : une facture sur plusieurs lignes
    # s'additionne.
    gauche: Dict[Tuple[str, str], Dict] = {}
    for f in rvgi["factures"]:
        k = (f["numero"], f["date"])
        if k in gauche:
            gauche[k]["ht"] = round(gauche[k]["ht"] + f["ht"], 2)
        else:
            gauche[k] = dict(f)
    droite: Dict[Tuple[str, str], Dict] = {(f["numero"], f["date"]): f for f in cw["factures"]}

    lignes: List[Dict] = []

    def ajouter(g: Optional[Dict], d: Optional[Dict], statut: str, piste: Optional[str], taux=None):
        lignes.append({
            "statut": statut,
            "numero": (g or d)["numero"],
            "date": (g or d)["date"],
            "numero_cw": d["numero"] if d else None,
            "date_cw": d["date"] if d else None,
            "client_rvgi": g["client"] if g else None,
            "client_cw": d["client"] if d else None,
            "compte_cw": d["compte"] if d else None,
            "ht": g["ht"] if g else None,
            "ttc": d["ttc"] if d else None,
            "taux": taux,
            "piste": piste,
        })

    # 1. Même numéro, même date.
    for k in list(gauche):
        if k in droite:
            g, d = gauche.pop(k), droite.pop(k)
            t, piste = _diagnostic_montant(g["ht"], d["ttc"])
            ajouter(g, d, "ok" if t is not None else "montant", piste, t)

    # 2. Même numéro, date différente.
    par_numero: Dict[str, List[Tuple[str, str]]] = {}
    for k in droite:
        par_numero.setdefault(k[0], []).append(k)
    for k in list(gauche):
        cands = par_numero.get(k[0]) or []
        cands = [c for c in cands if c in droite]
        if not cands:
            continue
        g, d = gauche.pop(k), droite.pop(cands[0])
        t, piste_m = _diagnostic_montant(g["ht"], d["ttc"])
        piste = (f"Date {d['date'][8:10]}/{d['date'][5:7]}/{d['date'][:4]} dans CW, "
                 f"{g['date'][8:10]}/{g['date'][5:7]}/{g['date'][:4]} dans RVGI : "
                 "corriger la date de l'écriture.")
        if piste_m:
            piste += " " + piste_m
        ajouter(g, d, "date", piste, t)

    # 3. Numéro voisin (faute de frappe), montant concordant : d'abord à la
    #    même date, puis à n'importe quelle date.
    for meme_date in (True, False):
        for k in list(gauche):
            g = gauche[k]
            meilleur = None
            for kd, d in droite.items():
                if meme_date and kd[1] != k[1]:
                    continue
                if _taux_concordant(g["ht"], d["ttc"]) is None:
                    continue
                dist = _distance(k[0], kd[0])
                if dist <= 2 and (meilleur is None or dist < meilleur[0]):
                    meilleur = (dist, kd)
            if meilleur:
                d = droite.pop(meilleur[1])
                gauche.pop(k)
                t = _taux_concordant(g["ht"], d["ttc"])
                piste = (f"Saisi sous le numéro {d['numero']} dans CW : "
                         f"corriger en {g['numero']}.")
                if d["date"] != g["date"]:
                    piste += " La date diffère aussi."
                ajouter(g, d, "numero", piste, t)

    # 4. Restes.
    for g in gauche.values():
        ajouter(g, None, "rvgi_seul",
                "Facture absente du grand-livre : à comptabiliser dans CW.")
    for d in droite.values():
        piste = ("Écriture de ventes sans facture RVGI de ce numéro : "
                 "vérifier une saisie manuelle dans CW ou une facture hors période.")
        if d["ttc"] < 0:
            piste = ("Avoir dans CW sans équivalent RVGI : vérifier qu'il a bien été "
                     "émis dans RVGI sur la période.")
        ajouter(None, d, "cw_seul", piste)

    # 5. Taux de TVA isolé : une facture concordante dont le taux diffère de
    #    celui de toutes les autres factures du même compte client.
    par_compte: Dict[str, List[Dict]] = {}
    for l in lignes:
        if l["taux"] is not None and l["compte_cw"]:
            par_compte.setdefault(l["compte_cw"], []).append(l)
    for groupe in par_compte.values():
        taux = [l["taux"] for l in groupe]
        if len(set(taux)) < 2:
            continue
        majoritaire = max(set(taux), key=taux.count)
        if taux.count(majoritaire) * 2 <= len(taux):
            continue
        for l in groupe:
            if l["taux"] != majoritaire and l["statut"] == "ok":
                l["statut"] = "tva"
                l["piste"] = (f"TVA {_fr(l['taux']).rstrip('0').rstrip(',')} % alors que les "
                              f"autres factures de ce client sont à "
                              f"{_fr(majoritaire).rstrip('0').rstrip(',')} % : vérifier le régime de TVA.")

    ordre = {"montant": 0, "numero": 1, "date": 2, "rvgi_seul": 3, "cw_seul": 4, "tva": 5, "ok": 6}
    lignes.sort(key=lambda l: (ordre[l["statut"]], l["date"], l["numero"]))

    compte = {s: 0 for s in ordre}
    for l in lignes:
        compte[l["statut"]] += 1
    total_ht = round(sum(f["ht"] for f in rvgi["factures"]), 2)
    total_ttc = round(sum(f["ttc"] for f in cw["factures"]), 2)
    return {
        "lignes": lignes,
        "compte": compte,
        "nb_rvgi": len(rvgi["factures"]),
        "nb_cw": len(cw["factures"]),
        "total_ht_rvgi": total_ht,
        "total_ht_rvgi_edition": rvgi.get("total_ht"),
        "total_ttc_cw": total_ttc,
        "periode_rvgi": rvgi.get("periode"),
        "periode_cw": cw.get("periode"),
        "tolerance": COMPTA_CMP_TOLERANCE,
    }


def comparer_pdf(doc_a: bytes, doc_b: bytes) -> Dict:
    """Compare deux PDF, dans n'importe quel ordre : chacun est reconnu."""
    ta, tb = type_document(doc_a), type_document(doc_b)
    if ta == tb:
        nom = "l'analyse des ventes RVGI" if ta == "rvgi" else "le grand-livre CW"
        raise DocumentNonReconnu(
            f"Les deux documents sont {nom} — il faut un document de chaque."
        )
    rvgi_b, cw_b = (doc_a, doc_b) if ta == "rvgi" else (doc_b, doc_a)
    rvgi, cw = lire_rvgi(rvgi_b), lire_cw(cw_b)
    if not rvgi["factures"]:
        raise DocumentNonReconnu("Aucune facture lue dans l'analyse des ventes RVGI — édition détaillée attendue.")
    if not cw["factures"]:
        raise DocumentNonReconnu("Aucune écriture du journal des ventes lue dans le grand-livre CW.")
    res = comparer(rvgi, cw)
    res["types"] = [ta, tb]
    return res
