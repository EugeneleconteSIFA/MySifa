"""
Rapprochement automatique d'un devis et d'une entrée de planning.

POURQUOI CE MODULE EXISTE. Le planning porte plusieurs centaines de dossiers,
les devis arrivent par centaines du partage réseau, et relier les deux à la
main dossier par dossier ne se fera jamais. Sans rapprochement, la comparaison
devis/réel reste une promesse : elle marche sur les cinq dossiers qu'on aura
liés un jour de motivation.

CE QUE LE MOTEUR COMPARE (décision du 15/10/2026) : format, laize, client,
papier, colle et date. Le papier et la colle ne sont dans aucune case du
devis : le classeur maison ne les porte que dans sa feuille de référentiel. Ils
sont en revanche écrits dans le NOM DU FICHIER, que les commerciaux rédigent
tous de la même façon (« 50x60 mm thermique pro permanent M76 B5000 … »). Côté
planning, ils viennent de l'OF (`matiere`, `adhesif_label`).

RIEN N'EST CODÉ EN DUR. Les familles de papier (« thermique », « vélin »,
« couché »…) et les types de colle (« permanent », « enlevable »…) ne sont pas
une liste du code : ce sont les premiers mots des matières et des adhésifs que
les OF ont réellement portés (`vocabulaire()`). Une matière nouvelle entre dans
le vocabulaire le jour où un OF la mentionne.

CE QU'IL NE FAUT PAS FAIRE. Proposer au hasard. Une proposition fausse qu'on
confirme d'un clic par réflexe empoisonne la comparaison sans laisser de trace.
Le moteur se TAIT en cas de doute réel :

- le format est éliminatoire. Sans format des deux côtés, aucune proposition ;
- un papier ou une colle qui se contredisent (vélin contre thermique,
  enlevable contre permanent) interdisent la proposition : c'est un autre
  produit. Le devis reste listé dans la recherche, plus bas ;
- il faut un score minimum ET un écart net avec le deuxième devis candidat.

UNE EXCEPTION À L'ÉCART, ET ELLE EST VOULUE. Un même produit est redevisé
plusieurs fois (« … 05-10-2026.xlsx », puis « … 06-10-2026.xlsx »). Ces devis
sont identiques sur tout sauf la date, et l'écart avec le second n'existe
jamais. Quand les candidats ex aequo décrivent le MÊME produit — même nom de
fichier une fois la date et la quantité retirées — on retient la version la
plus récente antérieure à la production : c'est celle qui était en vigueur.

UN DEVIS PEUT SERVIR PLUSIEURS DOSSIERS. Un produit refabriqué dix fois l'est
sur le même devis : interdire au devis de servir deux entrées laissait neuf
dossiers sur dix sans rattachement.

Les liaisons décidées par quelqu'un ne sont jamais touchées. Un couple rejeté
n'est plus jamais reproposé (`rent_rejets`).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

# ── Barème ────────────────────────────────────────────────────────
# Sur 100. Le format pèse le plus : c'est la seule grandeur physique que les
# deux côtés mesurent de la même façon.
POIDS_FORMAT = 30
POIDS_CLIENT = 20
POIDS_PAPIER = 14
POIDS_LAIZE = 12
POIDS_COLLE = 10
POIDS_DATE = 10
POIDS_MOTS = 4

# En dessous, on ne propose pas. Au-dessus, il faut encore devancer le second
# candidat de MARGE_MINIMALE : un ex aequo n'est pas une réponse (sauf
# versions successives du même devis, cf. en-tête).
SCORE_MINIMAL = 58
MARGE_MINIMALE = 10

# Un devis est chiffré peu avant la production qu'il chiffre. Plein points
# jusqu'à deux mois d'écart, puis décroissance jusqu'à un an et demi. Au-delà,
# le critère ne dit plus rien — il n'élimine pas pour autant : un marché
# annuel se produit longtemps après son devis.
JOURS_PLEIN = 60
JOURS_NEUTRE = 540

# Une famille de papier ou un type de colle n'entre dans le vocabulaire que
# s'il apparaît sur au moins ce nombre d'OF : une faute de frappe isolée ne
# doit pas devenir une famille.
OCCURRENCES_MINIMALES = 2

_SUFFIXES_JURIDIQUES = {
    "sa", "sas", "sasu", "sarl", "eurl", "sci", "snc", "gie", "scop",
    "ste", "societe", "cie", "co", "ltd", "gmbh", "bv", "nv", "spa", "srl",
}

# Mots trop répandus dans les noms de fichiers pour distinguer quoi que ce soit.
_MOTS_VIDES = {
    "mm", "cm", "ex", "coul", "couleurs", "couleur", "devis", "de",
    "la", "le", "les", "du", "des", "et", "en", "sur", "pour", "avec", "xlsx",
    "xls", "pdf", "bob", "bobine", "bobines", "etiquette", "etiquettes",
    "blanc", "blanche", "serie", "series", "copie", "qte", "ref", "adh",
    "sans", "ou", "un", "une",
}


def _sans_accents(txt: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )


def _jetons(valeur) -> list[str]:
    """Mots en minuscules sans accents, lettres et chiffres séparés.

    « PP100 » donne « pp » et « 100 » : la famille du support se lit sans
    qu'on ait à connaître tous les grammages qui la suivent.
    """
    txt = _sans_accents(str(valeur or "")).lower()
    txt = re.sub(r"([a-z])(\d)", r"\1 \2", txt)
    txt = re.sub(r"(\d)([a-z])", r"\1 \2", txt)
    return [m for m in re.sub(r"[^a-z0-9]+", " ", txt).split() if m]


def normaliser_client(valeur) -> str:
    """« EP CONSULT  » et « Ep-Consult SAS » donnent la même chaîne."""
    mots = [m for m in _jetons(valeur) if m not in _SUFFIXES_JURIDIQUES]
    return " ".join(mots)


def _mots_significatifs(valeur) -> set:
    return {m for m in _jetons(valeur)
            if len(m) >= 3 and not m.isdigit() and m not in _MOTS_VIDES}


def _nombre(valeur):
    try:
        n = float(str(valeur).replace(",", ".")) if isinstance(valeur, str) else float(valeur)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _proches(a: float, b: float, tolerance_rel: float = 0.015,
             tolerance_abs: float = 0.5) -> bool:
    """Deux cotes se valent si elles diffèrent de moins de 1,5 % ou de 0,5 mm."""
    return abs(a - b) <= max(tolerance_abs, tolerance_rel * max(a, b))


# ── Vocabulaire papier / colle, tiré des OF ───────────────────────
def vocabulaire(matieres, adhesifs) -> dict:
    """Familles de papier et types de colle, tels que les OF les écrivent.

    `matieres` / `adhesifs` : les libellés bruts des OF, un par OF (les
    doublons comptent : c'est la fréquence qui écarte les fautes de frappe).

    La famille est le premier mot du libellé (« THERMIQUE ECO » → thermique),
    le qualificatif le mot suivant (eco). Les types de colle sont les premiers
    mots des adhésifs (« Permanent 2028Y - 19 » → permanent), et les codes
    d'adhésif les nombres à quatre chiffres qu'ils portent (2028).
    """
    familles: dict[str, int] = {}
    qualifs: dict[str, set] = {}
    for lib in matieres or []:
        mots = [m for m in _jetons(lib) if not m.isdigit()]
        if not mots:
            continue
        familles[mots[0]] = familles.get(mots[0], 0) + 1
        if len(mots) > 1 and len(mots[1]) >= 2:
            qualifs.setdefault(mots[0], set()).add(mots[1])
    types: dict[str, int] = {}
    for lib in adhesifs or []:
        mots = [m for m in _jetons(lib) if not m.isdigit()]
        if mots:
            types[mots[0]] = types.get(mots[0], 0) + 1
    fams = {f for f, n in familles.items() if n >= OCCURRENCES_MINIMALES and len(f) >= 2}
    typs = {t for t, n in types.items() if n >= OCCURRENCES_MINIMALES and len(t) >= 3}
    # Un type de colle ne peut pas être aussi une famille de papier : un OF
    # « Couché Perm » ferait sinon de « couche » un type de colle.
    typs -= fams
    return {
        "familles": fams,
        "qualificatifs": {f: q for f, q in qualifs.items() if f in fams},
        "colles": typs,
    }


def _prefixe_commun(a: str, b: str) -> bool:
    """« pro » et « protege » désignent le même papier : le nom de fichier
    abrège ou développe librement ce que l'OF écrit."""
    if a == b:
        return True
    court, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(court) >= 3 and long_.startswith(court)


def _codes_colle(valeur) -> set:
    return {m for m in _jetons(valeur) if m.isdigit() and len(m) == 4}


def caracteristiques_devis(devis: dict, voc: dict) -> dict:
    """Papier et colle lus dans le nom du fichier d'un devis."""
    mots = _jetons(devis.get("filename"))
    familles = [m for m in mots if m in voc.get("familles", ())]
    famille = familles[0] if familles else ""
    qualifs = voc.get("qualificatifs", {}).get(famille, set())
    qualif = ""
    if famille:
        i = mots.index(famille)
        for m in mots[i + 1:i + 3]:
            if any(_prefixe_commun(m, q) for q in qualifs):
                qualif = m
                break
    colles = []
    for m in mots:
        for t in voc.get("colles", ()):
            if _prefixe_commun(m, t) and t not in colles:
                colles.append(t)
    return {
        "famille": famille,
        "qualificatif": qualif,
        "colles": colles,
        "codes_colle": _codes_colle(devis.get("filename")),
    }


def caracteristiques_entree(entree: dict, voc: dict) -> dict:
    """Papier et colle d'une entrée de planning, lus dans son OF."""
    mat = [m for m in _jetons(entree.get("matiere")) if not m.isdigit()]
    famille = mat[0] if mat and mat[0] in voc.get("familles", ()) else ""
    qualif = mat[1] if famille and len(mat) > 1 else ""
    colle = ""
    adh = [m for m in _jetons(entree.get("adhesif")) if not m.isdigit()]
    for m in adh[:1] + mat:
        trouve = next((t for t in voc.get("colles", ()) if _prefixe_commun(m, t)), "")
        if trouve:
            colle = trouve
            break
    return {
        "famille": famille,
        "qualificatif": qualif,
        "colle": colle,
        "codes_colle": _codes_colle(entree.get("adhesif")),
    }


# ── Critères ──────────────────────────────────────────────────────
def _cotes(a, b) -> list:
    return sorted(x for x in (_nombre(a), _nombre(b)) if x)


def _score_format(d: list, e: list) -> tuple[float, str]:
    """Compare deux couples de cotes SANS tenir compte de l'ordre.

    `d` / `e` : les cotes triées (`_cotes`), préparées une fois par devis et
    par entrée — le moteur évalue des centaines de milliers de couples."""
    if len(d) != 2 or len(e) != 2:
        return 0.0, ""
    if _proches(d[0], e[0]) and _proches(d[1], e[1]):
        return POIDS_FORMAT, "format %g×%g" % (e[0], e[1])
    return 0.0, ""


def _score_laize(devis, entree) -> tuple[float, str]:
    ld, le = _nombre(devis.get("laize")), _nombre(entree.get("laize"))
    if ld is None or le is None:
        return 0.0, ""
    if _proches(ld, le, 0.02, 2.0):
        return POIDS_LAIZE, "laize %g" % le
    return -POIDS_LAIZE, ""


def _score_client(cd: str, ce: str, nom: str) -> tuple[float, str]:
    """Le client du devis est souvent vide : son absence ne pénalise pas.

    `cd` / `ce` : noms normalisés (`normaliser_client`), `nom` : celui du
    planning, tel qu'affiché dans le motif."""
    if not cd or not ce:
        return 0.0, ""
    if cd == ce or cd.replace(" ", "") == ce.replace(" ", ""):
        return POIDS_CLIENT, "client %s" % nom
    court, long_ = (cd, ce) if len(cd) <= len(ce) else (ce, cd)
    if len(court) >= 4 and (court in long_ or court.replace(" ", "") in long_.replace(" ", "")):
        return POIDS_CLIENT * 0.8, "client %s" % nom
    # Premier mot commun d'au moins cinq lettres : « Maitre Coq - Arrivé » et
    # « MAITRE COQ ».
    md, me = cd.split(), ce.split()
    if md and me and md[0] == me[0] and len(md[0]) >= 5:
        return POIDS_CLIENT * 0.6, "client %s" % nom
    return 0.0, ""


def _score_papier(cd: dict, ce: dict) -> tuple[float, str]:
    if not cd["famille"] or not ce["famille"]:
        return 0.0, ""
    if cd["famille"] != ce["famille"]:
        # Thermique contre vélin : ce n'est pas le même produit.
        return -POIDS_PAPIER, ""
    if cd["qualificatif"] and ce["qualificatif"]:
        if _prefixe_commun(cd["qualificatif"], ce["qualificatif"]):
            return POIDS_PAPIER, "papier %s %s" % (ce["famille"], ce["qualificatif"])
        # Thermique éco contre thermique pro : même famille, autre papier.
        return POIDS_PAPIER * 0.2, ""
    return POIDS_PAPIER * 0.7, "papier %s" % ce["famille"]


def _score_colle(cd: dict, ce: dict) -> tuple[float, str]:
    if not cd["colles"] or not ce["colle"]:
        return 0.0, ""
    if ce["colle"] not in cd["colles"]:
        return -POIDS_COLLE, ""
    pts, motif = POIDS_COLLE * 0.8, "colle %s" % ce["colle"]
    communs = cd["codes_colle"] & ce["codes_colle"]
    if communs:
        pts, motif = POIDS_COLLE, motif + " " + sorted(communs)[0]
    return pts, motif


def _jour(valeur) -> datetime | None:
    txt = str(valeur or "").strip()[:10]
    try:
        return datetime.strptime(txt, "%Y-%m-%d")
    except ValueError:
        return None


def _date_entree(entree):
    return _jour(entree.get("planned_start")) or _jour(entree.get("debut_production"))


def _score_date(dd, dp) -> tuple[float, str]:
    """Un devis précède sa production. Ce critère nuance, il n'élimine jamais."""
    if dd is None or dp is None:
        return 0.0, ""
    ecart = (dp - dd).days
    if ecart < -3:
        return -POIDS_DATE * 0.5, ""
    ecart = max(0, ecart)
    if ecart <= JOURS_PLEIN:
        return POIDS_DATE, "devis %d j avant" % ecart
    if ecart >= JOURS_NEUTRE:
        return 0.0, ""
    reste = (JOURS_NEUTRE - ecart) / (JOURS_NEUTRE - JOURS_PLEIN)
    return POIDS_DATE * reste, ""


def _score_mots(mots_devis: set, mots_entree: set, deja: set) -> tuple[float, str]:
    """Les noms de fichiers portent le produit (« tabac », « RONDS »). Un
    appoint qui départage deux formats identiques, jamais une preuve."""
    communs = (mots_devis & mots_entree) - deja
    if not communs:
        return 0.0, ""
    part = min(1.0, len(communs) / 2.0)
    return POIDS_MOTS * part, "mots communs : " + ", ".join(sorted(communs)[:3])


def _prep_devis(devis: dict, voc: dict) -> dict:
    """Ce qui ne dépend que du devis, calculé une fois par passage du moteur.

    Rangé dans le dict lui-même, et rattaché au vocabulaire utilisé : un autre
    vocabulaire recalcule."""
    p = devis.get("_rp")
    if p is None or p["voc"] is not voc:
        p = {"voc": voc,
             "cotes": _cotes(devis.get("format_h"), devis.get("format_v")),
             "car": caracteristiques_devis(devis, voc),
             "client": normaliser_client(devis.get("client")),
             "mots": _mots_significatifs(devis.get("filename")),
             "jour": _jour(devis.get("date_devis"))}
        devis["_rp"] = p
    return p


def _prep_entree(entree: dict, voc: dict) -> dict:
    p = entree.get("_rp")
    if p is None or p["voc"] is not voc:
        p = {"voc": voc,
             "cotes": _cotes(entree.get("format_l"), entree.get("format_h")),
             "car": caracteristiques_entree(entree, voc),
             "client": normaliser_client(entree.get("client")),
             "nom": (entree.get("client") or "").strip(),
             "mots": (_mots_significatifs(entree.get("description"))
                      | _mots_significatifs(entree.get("ref_produit"))),
             "jour": _date_entree(entree)}
        entree["_rp"] = p
    return p


def evaluer(devis: dict, entree: dict, voc: dict | None = None) -> dict:
    """Score d'un couple (devis, entrée de planning) et motif lisible.

    `fond` est le score SANS la date : deux versions d'un même devis ont le
    même fond, c'est ce qui permet de les départager par la date seule.
    """
    voc = voc or {}
    pd, pe = _prep_devis(devis, voc), _prep_entree(entree, voc)
    s_format, m_format = _score_format(pd["cotes"], pe["cotes"])
    if s_format <= 0:
        return {"score": 0.0, "fond": 0.0, "motif": "", "format_ok": False,
                "contradiction": False}

    cd, ce = pd["car"], pe["car"]
    total, motifs = s_format, [m_format]
    s_papier, s_colle = _score_papier(cd, ce), _score_colle(cd, ce)
    for pts, motif in (_score_client(pd["client"], pe["client"], pe["nom"]),
                       _score_laize(devis, entree), s_papier, s_colle):
        total += pts
        if motif:
            motifs.append(motif)
    contradiction = s_papier[0] < 0 or s_colle[0] < 0
    utilises = {cd["famille"], cd["qualificatif"], *cd["colles"]}
    pts, motif = _score_mots(pd["mots"], pe["mots"], utilises)
    total += pts
    if motif:
        motifs.append(motif)
    fond = total
    pts, motif = _score_date(pd["jour"], pe["jour"])
    total += pts
    if motif:
        motifs.append(motif)
    return {
        "score": round(max(0.0, min(100.0, total)), 1),
        "fond": round(fond, 1),
        "motif": " · ".join(m for m in motifs if m),
        "format_ok": True,
        "contradiction": contradiction,
    }


# ── Versions successives d'un même devis ──────────────────────────
_RE_DATE_FICHIER = re.compile(r"\d{1,2}[-_.]\d{1,2}[-_.]\d{2,4}")


def signature_produit(filename) -> str:
    """Le nom du fichier sans sa date, ses quantités ni son extension.

    « 50x60 thermique pro M76 B5000 3.705.000 12-10-2026.xlsx » et la même
    chose datée du 05-10 donnent la même signature : ce sont deux versions du
    même devis, pas deux produits.
    """
    txt = re.sub(r"\.(xlsx|xlsm|xls|pdf|png|jpe?g)$", "", str(filename or ""), flags=re.I)
    txt = _RE_DATE_FICHIER.sub(" ", txt)
    txt = re.sub(r"\d{1,3}(?:[. ]\d{3})+", " ", txt)   # 3.705.000, 1 000 000
    txt = re.sub(r"\b\d{5,}\b", " ", txt)
    return " ".join(m for m in _jetons(txt) if m not in {"ex", "qte"})


def _plus_recente_version(candidats: list[dict], devis_par_id: dict, entree: dict):
    """Parmi des versions d'un même devis, celle en vigueur à la production.

    Rend None si les candidats ne sont pas des versions d'un même produit :
    dans ce cas l'ex aequo est un vrai doute, et le moteur se tait.
    """
    sigs = {signature_produit(devis_par_id[c["devis_id"]].get("filename")) for c in candidats}
    fonds = {c["fond"] for c in candidats}
    if len(sigs) != 1 or max(fonds) - min(fonds) > 0.5:
        return None
    dp = _date_entree(entree)

    def cle(c):
        d = _jour(devis_par_id[c["devis_id"]].get("date_devis"))
        if d is None:
            return (2, 0)
        if dp is None or d <= dp:
            return (0, -d.toordinal())      # antérieure : la plus récente
        return (1, d.toordinal())           # postérieure : la plus proche
    return sorted(candidats, key=cle)[0]


# ── Classement et propositions ────────────────────────────────────
def classer_pour_entree(devis_rows, entree: dict, limite: int = 8,
                        voc: dict | None = None) -> list[dict]:
    """Les devis plausibles pour UN dossier, du plus au moins probable."""
    voc = voc or {}
    e = _prep_entree(entree, voc)["cotes"]
    classes = []
    for dv in devis_rows:
        d = _prep_devis(dv, voc)["cotes"]
        if len(d) != 2 or len(e) != 2 or not _proches(d[0], e[0]):
            continue
        note = evaluer(dv, entree, voc)
        if note["score"] <= 0:
            continue
        classes.append({
            "devis_id": int(dv.get("id")),
            "score": note["score"],
            "fond": note["fond"],
            "motif": note["motif"],
            "contradiction": note["contradiction"],
        })
    classes.sort(key=lambda c: (-c["score"], -c["devis_id"]))
    return classes[:limite]


def meilleur_devis(devis_rows, entree: dict, voc: dict | None = None,
                   exclus: set | None = None) -> dict | None:
    """La proposition pour une entrée, ou None si le doute est réel.

    `exclus` : les devis déjà rejetés pour cette entrée.
    """
    exclus = exclus or set()
    lignes = [d for d in devis_rows if int(d.get("id")) not in exclus]
    classes = [c for c in classer_pour_entree(lignes, entree, limite=50, voc=voc)
               if not c["contradiction"]]
    if not classes or classes[0]["score"] < SCORE_MINIMAL:
        return None
    tete = classes[0]
    serres = [c for c in classes if tete["score"] - c["score"] < MARGE_MINIMALE]
    if len(serres) == 1:
        return tete
    par_id = {int(d.get("id")): d for d in lignes}
    choix = _plus_recente_version(serres, par_id, entree)
    if choix is None:
        return None
    return {**choix, "motif": choix["motif"]
            + " · version la plus récente de %d devis identiques" % len(serres)}


def proposer(devis_rows, entrees_rows, deja_liees, voc: dict | None = None,
             rejets: dict | None = None) -> list[dict]:
    """Les propositions à écrire, pour l'ensemble du planning.

    `deja_liees` : entrées dont la liaison a été décidée par quelqu'un. On n'y
    touche pas.
    `rejets` : {planning_entry_id: {devis_id, …}} — couples refusés à l'écran.
    """
    exclues = {int(x) for x in (deja_liees or [])}
    rejets = rejets or {}
    retenus = []
    for en in entrees_rows:
        eid = int(en.get("id") or 0)
        if not eid or eid in exclues:
            continue
        p = meilleur_devis(devis_rows, en, voc, rejets.get(eid))
        if p:
            retenus.append({
                "devis_id": p["devis_id"],
                "planning_entry_id": eid,
                "score": p["score"],
                "motif": p["motif"],
            })
    return retenus
