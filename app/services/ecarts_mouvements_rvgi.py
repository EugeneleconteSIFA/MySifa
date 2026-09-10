"""Entrées et sorties de matières : ce que dit MySifa, ce que dit RVGI.

Pourquoi un outil de plus
-------------------------
`stock_compare` compare des STOCKS : une photo par synchro. Un écart y dit
« il manque 12 bobines », jamais « depuis quand » ni « à cause de quel
mouvement ». Depuis le 10/09/2026 les entrées (réceptions RVGI) et les sorties
(déstockage des dossiers) de MySifa sont automatiques : l'endroit où elles
peuvent diverger de l'ERP, c'est le MOUVEMENT. Cet outil pose donc les deux
journaux côte à côte sur une fenêtre courte — 48 h par défaut — pendant que
les faits sont encore frais.

Ce que RVGI écrit, relevé sur `stm_hist` le 10/09/2026
------------------------------------------------------
- `mvt = 3` : réception fournisseur. `numcde`/`ligne` pointent la commande,
  `des1` vaut « Réception du 08/09/2026 ».
- `mvt = 2` : sortie de production. `numcde = 0`, et le DOSSIER est écrit à la
  main dans `des1` : « 9932366 ligne 1 », « Reliquat 9932232 », « 993266
  Ligne 3 » (six chiffres : faute de frappe, introuvable par construction).
- `mvt = 1`, `4`, `99` : créations de laize, inventaires, reprises. Hors
  comparaison, comptés à part.
- `type` est celui de `mat_mat`, soit le type de la LIGNE D'ACHAT moins 2 :
  l'adhésif 1055/0005 est en type 9 sur `cdf_ligne` et 7 dans `stm_hist`.
  Les types au-delà de 100 (1107, 1113…) sont les doublons de variante de
  fiche que RVGI écrit à chaque réception : les compter doublerait tout.
- `qte1` est la quantité mouvementée dans l'unité RVGI (mètres linéaires pour
  les bobines, kilos pour l'adhésif), `qte2` le stock résultant.

La clé
------
Un mouvement RVGI rejoint une matière MySifa par `erp_article_matiere`, la
table d'appariement des réceptions : (code1, code2, type d'achat). La même
table sert aux deux outils, donc apparier un article ici le fait aussi entrer
en stock à la prochaine réception. La quantité est traduite dans l'unité du
magasin par `reception_rvgi.convertir`, le même code que l'entrée en stock :
deux conversions différentes produiraient un écart qui n'existe pas.
"""

import re
from datetime import datetime, timedelta

from app.services import reception_rvgi as rr

MVT_RECEPTION = 3
MVT_SORTIE = 2
# stm_hist.type = cdf_ligne.type - DECALAGE_TYPE
DECALAGE_TYPE = 2

# Un numéro de dossier SIFA : sept chiffres. On en accepte six pour que la
# faute de frappe se voie dans l'écran au lieu de disparaître.
_RE_DOSSIER = re.compile(r"(?<!\d)(\d{6,7})(?!\d)")

# Sous ces écarts, la différence vient d'un arrondi (conversion ml → bobines,
# kg saisis au carton), pas d'un mouvement manquant.
TOLERANCE_ABSOLUE = {"bobine": 0.05, "kg": 0.5, "palette": 0.05}
TOLERANCE_RELATIVE = 0.02


def fenetre(heures=None, debut=None, fin=None, maintenant=None):
    """(début, fin) au format « AAAA-MM-JJ HH:MM:SS ».

    `debut`/`fin` explicites priment ; sinon les `heures` qui précèdent
    maintenant (48 par défaut, bornées à 31 jours).
    """
    maintenant = maintenant or datetime.now()

    def _lire(v):
        if not v:
            return None
        txt = str(v).strip().replace("T", " ")
        for n, fmt in ((19, "%Y-%m-%d %H:%M:%S"), (16, "%Y-%m-%d %H:%M"), (10, "%Y-%m-%d")):
            if len(txt) < n:
                continue
            try:
                return datetime.strptime(txt[:n], fmt)
            except ValueError:
                continue
        raise ValueError("Date invalide : %r" % (v,))

    d, f = _lire(debut), _lire(fin)
    if d is None:
        try:
            h = float(heures) if heures not in (None, "") else 48.0
        except (TypeError, ValueError):
            raise ValueError("Durée invalide.")
        h = max(1.0, min(h, 24.0 * 31))
        f = f or maintenant
        d = f - timedelta(hours=h)
    else:
        if f is None:
            f = maintenant
        elif len(str(fin).strip()) <= 10:
            f = f + timedelta(days=1)  # « jusqu'au 09/09 » inclut le 09/09
    if f <= d:
        raise ValueError("La fin de la période doit suivre son début.")
    if f - d > timedelta(days=31):
        raise ValueError("Période limitée à 31 jours.")
    fmt = "%Y-%m-%d %H:%M:%S"
    return d.strftime(fmt), f.strftime(fmt)


_RE_SUITE = re.compile(r"(?<!\d)(\d{7})((?:\s*\+\s*\d{1,3}(?!\d))+)")


def dossiers_cites(texte):
    """Numéros de dossier écrits dans un libellé RVGI.

    « 9932376+377 » désigne deux dossiers, 9932376 et 9932377 : la sortie a
    été saisie une fois pour deux OF consécutifs. Le suffixe remplace la fin
    du numéro.
    """
    txt = str(texte or "")
    out = []
    for m in _RE_SUITE.finditer(txt):
        base = m.group(1)
        for suite in re.findall(r"\d{1,3}", m.group(2)):
            out.append(base[:len(base) - len(suite)] + suite)
    for num in _RE_DOSSIER.findall(txt):
        if num not in out:
            out.append(num)
    # Ordre de lecture : le numéro écrit en entier d'abord, ses suites ensuite.
    return sorted(set(out), key=lambda n: (txt.find(n) if n in txt else len(txt), n))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _tolerance(unite, a, b):
    base = TOLERANCE_ABSOLUE.get(unite, 0.05)
    return max(base, TOLERANCE_RELATIVE * max(abs(a or 0), abs(b or 0)))


def _statut(unite, rvgi, mysifa):
    if not rvgi and not mysifa:
        return "vide"
    if not rvgi:
        return "mysifa_seul"
    if not mysifa:
        return "rvgi_seul"
    return "ok" if abs(mysifa - rvgi) <= _tolerance(unite, rvgi, mysifa) else "ecart"


_SQL_RVGI = """
    SELECT h.id, h.amjh, h.mvt, h.type, h.code1, h.code2, h.code3, h.numcde,
           h.ligne, h.qte1, h.des1, h.refbl,
           MAX(m.libc1) AS lib_erp, MAX(m.libt2) AS cond_erp
      FROM stm_hist h
      LEFT JOIN mat_mat m
        ON m.code1 = h.code1 AND m.code2 = h.code2 AND m.type = h.type
       AND m.corbeille = 0
     WHERE h.amjh >= ? AND h.amjh < ?
       AND h.type < 100
     GROUP BY h.id
     ORDER BY h.amjh
"""

_SQL_MYSIFA = """
    SELECT m.id, m.created_at, m.matiere_id, m.laize_id, m.type_mouvement,
           m.quantite, m.planning_entry_id, m.no_dossier, m.note,
           m.created_by_name,
           mp.reference, mp.designation, mp.categorie
      FROM mp_mouvements m
      JOIN matieres_premieres mp ON mp.id = m.matiere_id
     WHERE replace(m.created_at, 'T', ' ') >= ?
       AND replace(m.created_at, 'T', ' ') < ?
     ORDER BY m.created_at
"""


def _matieres(conn):
    return {int(r["id"]): dict(r) for r in conn.execute(
        "SELECT id, categorie, sous_section, reference, designation,"
        "       metres_lineaires_par_bobine, unites_par_palette"
        "  FROM matieres_premieres").fetchall()}


def comparer(conn, conn_erp, debut, fin):
    """Les deux journaux de mouvements, rapprochés par matière et par dossier."""
    matieres = _matieres(conn)
    actives = [m for m in matieres.values()]
    appar = rr._appariements(conn)

    par_matiere: dict = {}

    def _ligne_matiere(mid):
        m = matieres.get(mid) or {}
        cat = (m.get("categorie") or "").strip().lower()
        if mid not in par_matiere:
            par_matiere[mid] = {
                "matiere_id": mid, "reference": m.get("reference"),
                "designation": m.get("designation"), "categorie": m.get("categorie"),
                "unite": rr.UNITE_GESTION.get(cat, "palette"),
                "entrees_rvgi": 0.0, "entrees_mysifa": 0.0,
                "sorties_rvgi": 0.0, "sorties_mysifa": 0.0,
                "mouvements_rvgi": [], "mouvements_mysifa": [],
                "non_convertibles": 0,
            }
        return par_matiere[mid]

    non_apparies: dict = {}
    par_dossier: dict = {}
    autres_rvgi = 0
    hors_perimetre = 0

    def _dossier(num):
        if num not in par_dossier:
            par_dossier[num] = {"dossier": num, "rvgi": [], "mysifa": [],
                                "planning_id": None, "client": None}
        return par_dossier[num]

    # ── RVGI ──────────────────────────────────────────────────────────
    for r in conn_erp.execute(_SQL_RVGI, (debut, fin)).fetchall():
        mvt = int(r["mvt"] or 0)
        if mvt not in (MVT_RECEPTION, MVT_SORTIE):
            autres_rvgi += 1
            continue
        type_achat = int(r["type"] or 0) + DECALAGE_TYPE
        if type_achat not in rr.PERIMETRE:
            hors_perimetre += 1
            continue
        sens = "entree" if mvt == MVT_RECEPTION else "sortie"
        qte = _f(r["qte1"]) or 0.0
        libelle = ((r["lib_erp"] or "") + " " + (r["cond_erp"] or "")).strip()
        article = "%s/%s" % (r["code1"], r["code2"])
        dossiers = dossiers_cites(r["des1"]) if sens == "sortie" else []
        base = {
            "id": int(r["id"]), "date": (r["amjh"] or "")[:16], "sens": sens,
            "article": article, "laize_mm": _f(r["code3"]), "qte_rvgi": qte,
            "libelle_mvt": r["des1"], "bl": r["refbl"],
            "commande": r["numcde"] or None, "dossiers": dossiers,
        }
        mid = appar.get((str(r["code1"]), str(r["code2"]), type_achat))
        if not mid or mid not in matieres:
            cle = (str(r["code1"]), str(r["code2"]), type_achat)
            na = non_apparies.get(cle)
            if na is None:
                na = non_apparies[cle] = {
                    "code1": str(r["code1"]), "code2": str(r["code2"]),
                    "type_code": type_achat, "article": article,
                    "famille": rr.PERIMETRE[type_achat][0],
                    "libelle": libelle or None,
                    "nb_mouvements": 0, "entrees_rvgi": 0.0, "sorties_rvgi": 0.0,
                    "propositions": rr.proposer(
                        libelle, rr._candidates(actives, type_achat)),
                }
            na["nb_mouvements"] += 1
            na["entrees_rvgi" if sens == "entree" else "sorties_rvgi"] += qte
            for num in dossiers:
                _dossier(num)["rvgi"].append({**base, "matiere_id": None,
                                              "quantite": None, "unite": None})
            continue

        lm = _ligne_matiere(mid)
        conv = rr.convertir(type_achat, qte, matieres[mid], r["cond_erp"])
        q = conv.get("quantite")
        mv = {**base, "matiere_id": mid, "quantite": q, "unite": conv.get("unite"),
              "detail": conv.get("detail"),
              "manque": conv.get("manque") or []}
        lm["mouvements_rvgi"].append(mv)
        if q is None:
            lm["non_convertibles"] += 1
        else:
            lm["entrees_rvgi" if sens == "entree" else "sorties_rvgi"] += q
        for num in dossiers:
            _dossier(num)["rvgi"].append(mv)

    # ── MySifa ────────────────────────────────────────────────────────
    ajustements = 0
    for r in conn.execute(_SQL_MYSIFA, (debut, fin)).fetchall():
        t = (r["type_mouvement"] or "").strip().lower()
        if t not in ("entree", "sortie"):
            ajustements += 1
            continue
        mid = int(r["matiere_id"])
        lm = _ligne_matiere(mid)
        q = _f(r["quantite"]) or 0.0
        de_production = r["planning_entry_id"] is not None
        # Un retour sur un dossier (annulation, ajustement à la baisse) est
        # une sortie qui recule, pas une réception : il se compte en moins
        # dans les sorties, sinon il gonflerait les entrées d'un faux arrivage.
        if de_production:
            signe = 1.0 if t == "sortie" else -1.0
            lm["sorties_mysifa"] += signe * q
            sens = "sortie"
        else:
            lm["entrees_mysifa" if t == "entree" else "sorties_mysifa"] += q
            sens = t
        mv = {"id": int(r["id"]), "date": (r["created_at"] or "")[:16].replace("T", " "),
              "sens": sens, "type_mouvement": t,
              "quantite": q if (not de_production or t == "sortie") else -q,
              "unite": lm["unite"], "laize_id": r["laize_id"],
              "dossier": (r["no_dossier"] or "").strip() or None,
              "planning_id": r["planning_entry_id"], "note": r["note"],
              "par": r["created_by_name"]}
        lm["mouvements_mysifa"].append(mv)
        if de_production and mv["dossier"]:
            d = _dossier(mv["dossier"])
            d["planning_id"] = d["planning_id"] or r["planning_entry_id"]
            d["mysifa"].append({**mv, "matiere_id": mid,
                                "reference": r["reference"]})

    # ── Verdicts ──────────────────────────────────────────────────────
    lignes = []
    for lm in par_matiere.values():
        for k in ("entrees_rvgi", "entrees_mysifa", "sorties_rvgi", "sorties_mysifa"):
            lm[k] = round(lm[k], 4)
        lm["statut_entrees"] = _statut(lm["unite"], lm["entrees_rvgi"], lm["entrees_mysifa"])
        lm["statut_sorties"] = _statut(lm["unite"], lm["sorties_rvgi"], lm["sorties_mysifa"])
        lm["ecart_entrees"] = round(lm["entrees_mysifa"] - lm["entrees_rvgi"], 4)
        lm["ecart_sorties"] = round(lm["sorties_mysifa"] - lm["sorties_rvgi"], 4)
        lm["a_regarder"] = (lm["statut_entrees"] not in ("ok", "vide")
                            or lm["statut_sorties"] not in ("ok", "vide")
                            or lm["non_convertibles"] > 0)
        lignes.append(lm)
    lignes.sort(key=lambda x: (not x["a_regarder"], (x["reference"] or "").lower()))

    dossiers = []
    for d in par_dossier.values():
        # Par matière dans le dossier : les deux côtés se comparent dans
        # l'unité du magasin, quand l'article RVGI est apparié.
        cote: dict = {}
        for mv in d["rvgi"]:
            if mv.get("matiere_id") and mv.get("quantite") is not None:
                c = cote.setdefault(mv["matiere_id"], [0.0, 0.0, mv.get("unite")])
                c[0] += mv["quantite"]
        for mv in d["mysifa"]:
            c = cote.setdefault(mv["matiere_id"], [0.0, 0.0, mv.get("unite")])
            c[1] += mv["quantite"]
        ecarts = []
        for mid, (qr, qm, unite) in cote.items():
            st = _statut(unite, round(qr, 4), round(qm, 4))
            ecarts.append({"matiere_id": mid,
                           "reference": (matieres.get(mid) or {}).get("reference"),
                           "rvgi": round(qr, 4), "mysifa": round(qm, 4),
                           "unite": unite, "statut": st})
        non_rattaches = sum(1 for mv in d["rvgi"] if not mv.get("matiere_id"))
        if not d["mysifa"]:
            statut = "absent_mysifa"
        elif not d["rvgi"]:
            statut = "absent_rvgi"
        elif non_rattaches or any(e["statut"] != "ok" for e in ecarts):
            statut = "ecart"
        else:
            statut = "ok"
        dossiers.append({**d, "matieres": ecarts, "statut": statut,
                         "rvgi_non_apparies": non_rattaches})
    dossiers.sort(key=lambda x: (x["statut"] == "ok", x["dossier"]))

    return {
        "debut": debut, "fin": fin,
        "matieres": lignes,
        "dossiers": dossiers,
        "non_apparies": sorted(non_apparies.values(),
                               key=lambda x: -x["nb_mouvements"]),
        "resume": {
            "matieres": len(lignes),
            "a_regarder": sum(1 for x in lignes if x["a_regarder"]),
            "dossiers": len(dossiers),
            "dossiers_en_ecart": sum(1 for x in dossiers if x["statut"] != "ok"),
            "non_apparies": len(non_apparies),
            "mouvements_rvgi_ignores": autres_rvgi,
            "mouvements_rvgi_hors_perimetre": hors_perimetre,
            "ajustements_mysifa": ajustements,
        },
    }
