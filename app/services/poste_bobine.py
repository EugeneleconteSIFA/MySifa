"""Sur quel poste de déroulement va une bobine — frontal ou glassine.

Le besoin (10/09/2026)
----------------------
Pour savoir ce qui est monté sur une machine, il faut savoir OÙ se monte chaque
bobine scannée : le poste frontal (frontal ou complexe) ou le poste glassine.
L'opérateur ne doit pas avoir à le dire à chaque scan.

Ce que disent les données, et qui fixe l'ordre de la cascade
-----------------------------------------------------------
- Les catégories de Paramètres › Fournisseurs tranchent la plupart des cas :
  Kanzan ne livre que du frontal, Itasa que de la glassine.
- Elles ne suffisent PAS pour un fournisseur qui livre les deux. Likexin porte
  glassine, frontal ET complexe ; ce qui les sépare est le code lui-même
  (`G1101-…` glassine, `R1101-…` frontal). D'où les règles de préfixe, tenues
  par fournisseur dans `fournisseur_regles_code`.
- Le fournisseur tapé à la main se contredit parfois. On part donc du CODE
  chaque fois qu'on le peut, et le fournisseur n'intervient qu'ensuite.

Cascade, du certain au probable :

    0. montee      la bobine est déjà montée quelque part       → certain
    1. stock       le code est une bobine connue de MyStock     → certain
    2. historique  ce code exact a déjà reçu une nature         → probable
    3. regle       règle de préfixe du fournisseur              → selon le fournisseur
    4. fournisseur ses catégories ne désignent qu'un poste      → selon le fournisseur
    5. signature   la forme du code a déjà été vue sous une nature → probable ou suggéré

Rien de trouvé : la réponse est vide et l'écran pose la question en un geste
(Frontal · Complexe · Glassine). La réponse de l'opérateur est apprise.

La confiance d'un palier 3 ou 4 ne peut pas dépasser celle du fournisseur :
une règle exacte appliquée au mauvais fournisseur donne une nature fausse.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

from config import CATEGORIES_BOBINE, poste_pour_categorie, postes_deroulement
from app.services import origine_bobine

PLACES_MAX = 4

# Sources dont la nature est ARRÊTÉE et peut donc nourrir la mémoire des formes.
# Une nature seulement déduite (signature, fournisseur, historique) n'y entre
# pas : la mémoire apprendrait ses propres suppositions.
SOURCES_APPRISES = ("saisie", "stock", "regle")
SOURCES = ("montee", "stock", "historique", "regle", "fournisseur", "signature", "saisie")
_CONF_RANG = {"aucune": 0, "suggere": 1, "probable": 2, "certain": 3}


# Même horloge que les scans (`fab_matieres_utilisees.scanned_at`, heure de
# Paris sans fuseau) : les montages et les lignes héritées se trient avec eux.
_PARIS = ZoneInfo("Europe/Paris")


def _maintenant() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _norm_categorie(valeur) -> Optional[str]:
    v = str(valeur or "").strip().lower()
    return v if v in CATEGORIES_BOBINE else None


def _plafond(conf: str, plafond: str) -> str:
    """La plus faible des deux confiances."""
    return conf if _CONF_RANG.get(conf, 0) <= _CONF_RANG.get(plafond, 0) else plafond


def _cats_json(raw) -> List[str]:
    try:
        v = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    return [str(x).strip().lower() for x in v if str(x).strip()] if isinstance(v, list) else []


def _label_poste(code: Optional[str]) -> str:
    for p in postes_deroulement():
        if p["code"] == code:
            return p["label"]
    return code or ""


# ══ Référentiel : postes par machine ═════════════════════════════════════════

def postes_machine(conn, machine_id: int, actifs_seulement: bool = True) -> List[Dict[str, Any]]:
    """Les postes de déroulement d'une machine, dans l'ordre du référentiel."""
    lignes = {
        r["poste"]: dict(r)
        for r in conn.execute(
            "SELECT poste, places, actif, updated_at, updated_by "
            "FROM machine_postes_deroulement WHERE machine_id=?",
            (int(machine_id),),
        ).fetchall()
    }
    out = []
    for p in postes_deroulement():
        l = lignes.get(p["code"])
        if l is None:
            if actifs_seulement:
                continue
            l = {"places": 0, "actif": 0, "updated_at": None, "updated_by": None}
        if actifs_seulement and (not l["actif"] or int(l["places"] or 0) <= 0):
            continue
        out.append({
            "poste": p["code"], "label": p["label"], "categories": p["categories"],
            "places": int(l["places"] or 0), "actif": 1 if l["actif"] else 0,
            "updated_at": l["updated_at"], "updated_by": l["updated_by"],
        })
    return out


def enregistrer_postes(conn, machine_id: int, postes: List[Dict[str, Any]], par: str) -> List[Dict[str, Any]]:
    """Remplace la configuration des postes d'une machine. Lève ValueError."""
    connus = {p["code"] for p in postes_deroulement()}
    vus = set()
    propres = []
    for p in postes or []:
        code = str((p or {}).get("poste") or "").strip().lower()
        if code not in connus:
            raise ValueError("Poste inconnu : %s." % (code or "vide"))
        if code in vus:
            raise ValueError("Poste %s déclaré deux fois." % _label_poste(code))
        vus.add(code)
        try:
            places = int(p.get("places"))
        except (TypeError, ValueError):
            raise ValueError("Nombre de places invalide — entier entre 0 et %d." % PLACES_MAX)
        if places < 0 or places > PLACES_MAX:
            raise ValueError("Nombre de places invalide — entier entre 0 et %d." % PLACES_MAX)
        actif = 1 if (p.get("actif", 1) and places > 0) else 0
        propres.append((code, places, actif))
    maintenant = _maintenant()
    for code, places, actif in propres:
        conn.execute(
            """INSERT INTO machine_postes_deroulement
                   (machine_id, poste, places, actif, updated_at, updated_by)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(machine_id, poste) DO UPDATE SET
                   places=excluded.places, actif=excluded.actif,
                   updated_at=excluded.updated_at, updated_by=excluded.updated_by""",
            (int(machine_id), code, places, actif, maintenant, par),
        )
    return postes_machine(conn, machine_id, actifs_seulement=False)


# ══ Référentiel : règles de code par fournisseur ═════════════════════════════

def regles_code(conn, fournisseur_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql = """SELECT r.id, r.fournisseur_id, f.nom AS fournisseur, r.motif, r.categorie,
                    r.note, r.actif, r.created_at, r.updated_at, r.updated_by
               FROM fournisseur_regles_code r
          LEFT JOIN fournisseurs_fsc f ON f.id = r.fournisseur_id"""
    args: tuple = ()
    if fournisseur_id:
        sql += " WHERE r.fournisseur_id=?"
        args = (int(fournisseur_id),)
    sql += " ORDER BY lower(f.nom), length(r.motif) DESC, r.motif"
    out = []
    for r in conn.execute(sql, args).fetchall():
        d = dict(r)
        d["poste"] = poste_pour_categorie(d["categorie"])
        out.append(d)
    return out


def enregistrer_regle(conn, fournisseur_id, motif, categorie, note, par: str,
                      regle_id: Optional[int] = None, actif: int = 1) -> Dict[str, Any]:
    """Crée ou modifie une règle. Lève ValueError sur une saisie invalide."""
    try:
        fid = int(fournisseur_id)
    except (TypeError, ValueError):
        raise ValueError("Fournisseur requis.")
    if not conn.execute("SELECT 1 FROM fournisseurs_fsc WHERE id=?", (fid,)).fetchone():
        raise ValueError("Fournisseur introuvable.")
    cat = _norm_categorie(categorie)
    if not cat:
        raise ValueError("Catégorie invalide — frontal, complexe ou glassine.")
    m = str(motif or "").strip().upper()
    if len(m) > 20:
        raise ValueError("Préfixe trop long — 20 caractères au plus.")
    maintenant = _maintenant()
    doublon = conn.execute(
        "SELECT id FROM fournisseur_regles_code WHERE fournisseur_id=? AND motif=?",
        (fid, m),
    ).fetchone()
    if doublon and (regle_id is None or int(doublon["id"]) != int(regle_id)):
        raise ValueError("Ce préfixe a déjà une règle pour ce fournisseur.")
    if regle_id:
        cur = conn.execute(
            """UPDATE fournisseur_regles_code
                  SET fournisseur_id=?, motif=?, categorie=?, note=?, actif=?,
                      updated_at=?, updated_by=?
                WHERE id=?""",
            (fid, m, cat, (note or "").strip()[:200] or None, 1 if actif else 0,
             maintenant, par, int(regle_id)),
        )
        if not cur.rowcount:
            raise LookupError("Règle introuvable.")
        rid = int(regle_id)
    else:
        rid = conn.execute(
            """INSERT INTO fournisseur_regles_code
                   (fournisseur_id, motif, categorie, note, actif, created_at, updated_at, updated_by)
               VALUES (?,?,?,?,?,?,?,?)""",
            (fid, m, cat, (note or "").strip()[:200] or None, 1 if actif else 0,
             maintenant, maintenant, par),
        ).lastrowid
    return next(r for r in regles_code(conn) if r["id"] == rid)


def supprimer_regle(conn, regle_id: int) -> bool:
    return bool(conn.execute(
        "DELETE FROM fournisseur_regles_code WHERE id=?", (int(regle_id),)
    ).rowcount)


def regle_pour_code(conn, fournisseur_id: int, code: str) -> Optional[Dict[str, Any]]:
    """La règle active dont le préfixe est le plus long à couvrir le code."""
    brut = (code or "").strip().upper()
    meilleure = None
    for r in conn.execute(
        "SELECT id, motif, categorie FROM fournisseur_regles_code "
        "WHERE fournisseur_id=? AND actif=1",
        (int(fournisseur_id),),
    ).fetchall():
        motif = r["motif"] or ""
        if brut.startswith(motif) and (meilleure is None or len(motif) > len(meilleure["motif"] or "")):
            meilleure = dict(r)
    return meilleure


def categories_bobine_fournisseur(conn, fournisseur_id: Optional[int] = None,
                                  nom: Optional[str] = None) -> List[str]:
    """Les catégories de bobine (frontal, complexe, glassine) d'une fiche fournisseur."""
    if fournisseur_id:
        row = conn.execute("SELECT categories FROM fournisseurs_fsc WHERE id=?",
                           (int(fournisseur_id),)).fetchone()
    elif nom:
        row = conn.execute("SELECT categories FROM fournisseurs_fsc WHERE trim(nom)=trim(?) LIMIT 1",
                           (nom,)).fetchone()
    else:
        return []
    if not row:
        return []
    cats = _cats_json(row["categories"])
    return [c for c in CATEGORIES_BOBINE if c in cats]


def diagnostic(conn) -> Dict[str, Any]:
    """Ce qui empêche la reconnaissance d'être automatique, fournisseur par fournisseur.

    - `ambigus` : la fiche désigne les deux postes et aucune règle ne départage.
    - `sans_categorie` : fournisseur déjà vu sur des scans, sans aucune catégorie
      de bobine — la cascade ne peut rien en tirer.
    """
    avec_regle = {int(r["fournisseur_id"]) for r in conn.execute(
        "SELECT DISTINCT fournisseur_id FROM fournisseur_regles_code WHERE actif=1").fetchall()}
    ambigus = []
    for f in conn.execute(
        "SELECT id, nom, categories FROM fournisseurs_fsc WHERE COALESCE(actif,1)=1"
    ).fetchall():
        cats = [c for c in CATEGORIES_BOBINE if c in _cats_json(f["categories"])]
        postes = {poste_pour_categorie(c) for c in cats}
        if len(postes) > 1 and int(f["id"]) not in avec_regle:
            ambigus.append({"id": f["id"], "nom": f["nom"], "categories": cats})

    vus = conn.execute(
        """SELECT COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS nom, COUNT(*) AS scans
             FROM fab_matieres_utilisees fmu
        LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
            WHERE COALESCE(sr.fournisseur, fmu.fournisseur_manual) IS NOT NULL
         GROUP BY 1"""
    ).fetchall()
    sans = []
    for v in vus:
        f = conn.execute(
            "SELECT id, nom, categories FROM fournisseurs_fsc WHERE trim(nom)=trim(?) LIMIT 1",
            (v["nom"],),
        ).fetchone()
        if not f:
            continue
        if not [c for c in CATEGORIES_BOBINE if c in _cats_json(f["categories"])]:
            sans.append({"id": f["id"], "nom": f["nom"], "scans": int(v["scans"])})
    sans.sort(key=lambda x: -x["scans"])
    return {"ambigus": ambigus, "sans_categorie": sans}


# ══ Mémoire des natures par forme de code ════════════════════════════════════

def _obs_categorie(row) -> Dict[str, int]:
    try:
        keys = row.keys()
        raw = row["observations_categorie"] if "observations_categorie" in keys else "{}"
        d = json.loads(raw or "{}")
    except (ValueError, TypeError):
        return {}
    return {str(k): int(v) for k, v in d.items() if _norm_categorie(k)}


def apprendre_categorie(conn, code: str, categorie: str) -> int:
    """Compte une nature arrêtée dans toutes les signatures du code."""
    cat = _norm_categorie(categorie)
    if not cat:
        return 0
    maintenant = _maintenant()
    n = 0
    for typ, valeur, spec in origine_bobine.signatures_candidates(code):
        row = conn.execute(
            "SELECT id, observations_categorie FROM bobine_signatures WHERE type=? AND valeur=?",
            (typ, valeur),
        ).fetchone()
        if row:
            obs = _obs_categorie(row)
            obs[cat] = obs.get(cat, 0) + 1
            conn.execute(
                "UPDATE bobine_signatures SET observations_categorie=?, dernier_vu=? WHERE id=?",
                (json.dumps(obs), maintenant, int(row["id"])),
            )
        else:
            conn.execute(
                """INSERT INTO bobine_signatures
                       (type, valeur, specificite, observations, total,
                        premier_vu, dernier_vu, observations_categorie)
                   VALUES (?,?,?,'{}',0,?,?,?)""",
                (typ, valeur, spec, maintenant, maintenant, json.dumps({cat: 1})),
            )
        n += 1
    return n


# ══ Cascade ══════════════════════════════════════════════════════════════════

def _reponse(source, confiance, categorie, explication, poste=None, candidats=None, **extra):
    cat = _norm_categorie(categorie)
    p = poste or poste_pour_categorie(cat)
    d = {
        "trouve": bool(p),
        "source": source,
        "confiance": confiance if p else "aucune",
        "categorie": cat,
        "poste": p,
        "poste_label": _label_poste(p),
        "explication": explication,
        "candidats": candidats or [],
        "categories": list(CATEGORIES_BOBINE),
    }
    d.update(extra)
    return d


def _vide(candidats=None, explication=None):
    return _reponse(None, "aucune", None,
                    explication or "Rien ne permet de dire sur quel poste se monte cette bobine.",
                    candidats=candidats)


def _depuis_fournisseur(conn, code: str, fourn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    nom = (fourn or {}).get("fournisseur")
    fid = (fourn or {}).get("fournisseur_id")
    conf_f = (fourn or {}).get("confiance") or "aucune"
    if not (nom or fid) or conf_f == "aucune" or conf_f == "ambigu":
        return None
    if not fid and nom:
        r = conn.execute("SELECT id FROM fournisseurs_fsc WHERE trim(nom)=trim(?) LIMIT 1",
                         (nom,)).fetchone()
        fid = int(r["id"]) if r else None
    if not fid:
        return None

    regle = regle_pour_code(conn, fid, code)
    if regle:
        motif = regle["motif"] or ""
        if motif:
            txt = "Chez %s, un code commençant par %s est un %s." % (nom, motif, regle["categorie"])
        else:
            txt = "Chez %s, ce type de code est un %s." % (nom, regle["categorie"])
        return _reponse("regle", _plafond("certain", conf_f), regle["categorie"], txt,
                        fournisseur=nom, regle_id=regle["id"])

    cats = categories_bobine_fournisseur(conn, fournisseur_id=fid)
    postes = {poste_pour_categorie(c) for c in cats}
    if len(postes) == 1:
        poste = postes.pop()
        categorie = cats[0] if len(cats) == 1 else None
        txt = "%s ne livre que %s." % (nom, " et ".join(cats) if cats else "ce poste")
        return _reponse("fournisseur", _plafond("probable", conf_f), categorie, txt,
                        poste=poste, fournisseur=nom)
    return None


def resoudre(conn, code: str, machine_id: Optional[int] = None,
             fournisseur: Optional[Dict[str, Any]] = None,
             no_dossier: Optional[str] = None) -> Dict[str, Any]:
    """La nature et le poste d'une bobine, et ce qui permet de l'affirmer.

    `fournisseur` est la réponse d'`origine_bobine.resoudre` (ou un dict
    {fournisseur, fournisseur_id, confiance}) quand l'appelant l'a déjà ; sinon
    elle est calculée ici.
    """
    brut = (code or "").strip()
    if not brut:
        return _vide()

    # 0 ── Déjà montée : le poste a été arrêté au montage.
    m = conn.execute(
        """SELECT machine_id, poste, categorie FROM bobines_montees
            WHERE trim(code_barre)=trim(?) AND demonte_at IS NULL AND poste IS NOT NULL
         ORDER BY monte_at DESC, id DESC LIMIT 1""",
        (brut,),
    ).fetchone()
    if m:
        ici = machine_id is not None and int(m["machine_id"]) == int(machine_id)
        return _reponse("montee", "certain", m["categorie"],
                        "Cette bobine est déjà montée sur le poste %s%s."
                        % (_label_poste(m["poste"]).lower(), "" if ici else " d'une autre machine"),
                        poste=m["poste"], machine_id=int(m["machine_id"]))

    # 1 ── Le stock : la bobine a une matière, la matière a une catégorie.
    s = conn.execute(
        """SELECT mp.categorie, mp.reference FROM stock_bobines b
             JOIN matieres_premieres mp ON mp.id = b.matiere_id
            WHERE trim(b.code_barre)=trim(?) LIMIT 1""",
        (brut,),
    ).fetchone()
    if not s:
        s = conn.execute(
            """SELECT mp.categorie, mp.reference FROM stock_reception_items i
                 JOIN matieres_premieres mp ON mp.id = i.matiere_id
                WHERE trim(i.code_barre)=trim(?)
             ORDER BY i.scanned_at DESC, i.id DESC LIMIT 1""",
            (brut,),
        ).fetchone()
    if s and _norm_categorie(s["categorie"]):
        return _reponse("stock", "certain", s["categorie"],
                        "Bobine connue du stock (%s)." % (s["reference"] or s["categorie"]))

    # 2 ── Ce code exact a déjà reçu une nature.
    lignes = conn.execute(
        """SELECT categorie_bobine AS c, COUNT(*) n FROM fab_matieres_utilisees
            WHERE trim(code_barre)=trim(?) AND categorie_bobine IS NOT NULL
         GROUP BY 1 ORDER BY 2 DESC""",
        (brut,),
    ).fetchall()
    obs = {r["c"]: int(r["n"]) for r in lignes if _norm_categorie(r["c"])}
    if len(obs) == 1:
        cat = next(iter(obs))
        return _reponse("historique", "probable", cat,
                        "Ce code-barres a déjà été scanné comme %s." % cat)
    candidats_hist = [{"categorie": k, "observations": v}
                      for k, v in sorted(obs.items(), key=lambda kv: -kv[1])]

    # 3-4 ── Le fournisseur : ses règles de préfixe, puis ses catégories.
    if fournisseur is None:
        try:
            fournisseur = origine_bobine.resoudre(conn, brut, no_dossier)
        except Exception:
            fournisseur = None
    rep = _depuis_fournisseur(conn, brut, fournisseur or {})
    if rep:
        return rep

    # 5 ── La forme du code.
    for typ, valeur, _spec in origine_bobine.signatures_candidates(brut):
        row = conn.execute(
            "SELECT observations_categorie FROM bobine_signatures WHERE type=? AND valeur=?",
            (typ, valeur),
        ).fetchone()
        if not row:
            continue
        o = _obs_categorie(row)
        if not o:
            continue
        cat, confiance, cands = origine_bobine._verdict(o)
        candidats = [{"categorie": c["nom"], "observations": c["observations"]} for c in cands]
        if not cat:
            return _vide(candidats, "Cette forme de code a déjà été vue sous plusieurs natures.")
        return _reponse("signature", confiance, cat,
                        "Les codes de cette forme ont été scannés comme %s." % cat,
                        candidats=candidats, signature=valeur)

    return _vide(candidats_hist)


def reconstruire_categories(conn) -> Dict[str, int]:
    """Rejoue les scans passés dont la nature est ARRÊTÉE, pour la mémoire des formes.

    Ne comptent que ce qui ne se déduit pas d'une supposition : la bobine
    connue du stock, une règle de préfixe, et la nature choisie par un
    opérateur. Les catégories d'une fiche fournisseur sont exclues — elles se
    relisent en direct à chaque scan, et une fiche mal renseignée (Burgo noté
    « complexe » alors qu'il livre du frontal) empoisonnerait sinon la mémoire
    pour longtemps. Rejouer la mémoire elle-même ne ferait qu'auto-entretenir
    ses propres suppositions.
    """
    conn.execute("UPDATE bobine_signatures SET observations_categorie='{}'")
    scans = apprises = 0
    for r in conn.execute(
        """SELECT fmu.code_barre AS code,
                  COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS nom,
                  fmu.categorie_bobine AS cat_saisie, fmu.poste_source AS src
             FROM fab_matieres_utilisees fmu
        LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id"""
    ).fetchall():
        scans += 1
        cat = None
        if r["cat_saisie"] and r["src"] in SOURCES_APPRISES:
            cat = r["cat_saisie"]
        else:
            s = conn.execute(
                """SELECT mp.categorie FROM stock_bobines b
                     JOIN matieres_premieres mp ON mp.id=b.matiere_id
                    WHERE trim(b.code_barre)=trim(?) LIMIT 1""",
                (r["code"],),
            ).fetchone()
            if s and _norm_categorie(s["categorie"]):
                cat = s["categorie"]
            elif r["nom"]:
                f = conn.execute("SELECT id FROM fournisseurs_fsc WHERE trim(nom)=trim(?) LIMIT 1",
                                 (r["nom"],)).fetchone()
                regle = regle_pour_code(conn, int(f["id"]), r["code"]) if f else None
                if regle:
                    cat = regle["categorie"]
        if cat and apprendre_categorie(conn, r["code"], cat):
            apprises += 1
    return {"scans": scans, "apprises": apprises}
