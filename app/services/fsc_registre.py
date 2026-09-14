"""
MySifa — registre FSC des approvisionnements : import RVGI et éligibilité.

Ce module fait trois choses, et rien d'autre : il lit les réceptions du miroir
RVGI, il les fige dans `fsc_reception`, et il dit d'une ligne si elle est
éligible FSC. Les écrans et les routes vivent ailleurs.

Ce qu'« éligible » veut dire
---------------------------
Une matière n'est FSC éligible que si les quatre conditions sont réunies :
le certificat du fournisseur était valide **à la date du BL**, le BL porte une
allégation, la facture porte **la même**, et le code de certificat figure sur
ces documents. Trois valeurs de sortie disent l'état réel plutôt que de trancher
trop tôt :

- `oui` — les quatre conditions sont vérifiées ;
- `non` — une condition est démentie (certificat expiré, pas d'allégation
  facturée, code absent) ;
- `a_verifier` — une information manque encore, y compris quand la date
  d'expiration du certificat est inconnue ;
- `ecart_bl_facture` — le BL et la facture ne disent pas la même chose. C'est le
  cas le plus intéressant pour un auditeur : il ne se range ni dans oui ni dans
  non, il appelle une réclamation au fournisseur.

Une date d'expiration absente n'est PAS un certificat invalide. `fsc_certificat`
tient déjà cette distinction (« un contrôle qui ne sait pas doit le dire ») et ce
module la reprend telle quelle.

Ce qui est figé, et pourquoi
----------------------------
Fournisseur, désignation, quantité, laize, verdict du certificat : tout est
recopié à l'import et ne se relit plus. Un article renommé dans l'ERP en
novembre ne doit pas réécrire une réception de mars. Une resynchro n'ajoute que
les lignes nouvelles (`lif_id` est unique).
"""

from __future__ import annotations

import sqlite3
import unicodedata
from datetime import datetime
from typing import Any, Optional

from app.services.fsc_certificat import evaluer_certificat
from app.services.reception_rvgi import PERIMETRE
from config import (
    FSC_ALLEGATIONS,
    FSC_ETIQUETTES,
    FSC_SEUIL_LABEL_PCT,
    FSC_TYPES_NON_FORESTIERS,
    FSC_TYPES_REGISTRE,
)

TABLE = "fsc_reception"
CLE_DEPUIS = "registre_depuis"

# Les champs que l'opérateur saisit. Tout le reste vient de RVGI et ne s'édite
# pas : corriger une désignation dans le registre la ferait diverger de la
# pièce d'origine, qui est ce que l'auditeur regarde.
CHAMPS_SAISIS = (
    "num_facture_fournisseur",
    "allegation_bl",
    "allegation_facture",
    "pourcentage",
    "code_certificat_present",
    "etiquette_posee",
    "observations",
)
# Ceux que « appliquer à tout le BL » recopie : une facture couvre trois à cinq
# lignes du même bon, et personne ne saisit cinq fois le même numéro.
CHAMPS_BL = (
    "num_facture_fournisseur",
    "allegation_bl",
    "allegation_facture",
    "pourcentage",
    "code_certificat_present",
    "etiquette_posee",
)


# ══════════════════════════════════════════════════════════════════
# Lecture du miroir RVGI
# ══════════════════════════════════════════════════════════════════

# Le filtre de période porte sur `l.id`, PAS sur `amjl`. Le magasin saisit
# souvent plusieurs jours après la livraison — relevé du 10/09/2026, la
# réception 28566 a été saisie le 07/09 pour une livraison du 21/07. Filtrer sur
# la date du bon écarterait POUR TOUJOURS une réception livrée avant la bascule
# mais saisie après. `l.id` suit l'ordre de création des lignes ; `dtem` bouge à
# chaque modification, il ne sert qu'à situer la borne. Même motif que
# `reception_rvgi._SQL_LIGNES`, et pour la même raison.
_SQL_IMPORT = """
    SELECT l.id                  AS lif_id,
           l.numero              AS cde_numero,
           l.ligne               AS cde_ligne,
           substr(l.amjl, 1, 10) AS date_reception,
           substr(l.dtem, 1, 10) AS date_saisie_rvgi,
           l.qte                 AS quantite_ml,
           l.ref                 AS num_bl,
           l.fac_no              AS piece_facture_rvgi,
           l.fac_lg              AS ligne_facture_rvgi,
           e.numfou              AS numfou,
           e.rs                  AS fournisseur_rvgi,
           c.code1               AS code1,
           c.code2               AS code2,
           c.code3               AS laize_mm,
           c.type                AS type_code,
           c.des1                AS designation,
           m.libc1               AS libelle_matiere,
           m.ref                 AS ref_fournisseur
      FROM lif_ligne l
      JOIN cdf_ligne c  ON c.numero = l.numero AND c.ligne = l.ligne AND c.corbeille = 0
      LEFT JOIN cdf_entete e ON e.numero = l.numero AND e.corbeille = 0
      -- La fiche matière se joint sur le TRIPLET : `cdf_ligne.type` réserve ses
      -- deux premiers rangs à ce qui n'est pas une matière, d'où le décalage.
      -- Sans le type, `1183/0001` ramène sa fiche glassine ou sa fiche vélin au
      -- hasard.
      LEFT JOIN mat_mat m ON m.code1 = c.code1 AND m.code2 = c.code2
                         AND m.type = c.type - 2 AND m.corbeille = 0
     WHERE l.corbeille = 0
       AND c.type IN (%s)
       AND l.id > (SELECT COALESCE(MAX(x.id), 0) FROM lif_ligne x
                    WHERE substr(x.dtem, 1, 10) < ?)
       AND substr(l.amjl, 1, 10) >= ?
     ORDER BY l.amjl, l.numero, l.ligne
"""


def _f(v) -> Optional[float]:
    try:
        return float(str(v).replace(",", ".")) if v is not None and str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _txt(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def normaliser_nom(nom: str) -> str:
    """« SHENZHEN LIKEXIN INDUSTRIAL Co. » → « shenzhen likexin industrial ».

    Les formes juridiques et les initiales isolées sautent : RVGI écrit la
    raison sociale complète là où MySifa porte le nom d'usage.
    """
    s = unicodedata.normalize("NFKD", str(nom or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = "".join(c if c.isalnum() else " " for c in s)
    stop = ("sa", "sas", "sarl", "sasu", "gmbh", "ltd", "co", "bv", "nv", "spa",
            "srl", "inc", "ag", "kg", "plc", "llc", "cie")
    mots = [m for m in s.split() if m not in stop and len(m) > 1]
    return " ".join(mots) or " ".join(s.split())


def date_entree(conn) -> Optional[str]:
    """Le jour à partir duquel les réceptions entrent au registre, ou None."""
    try:
        r = conn.execute(
            "SELECT valeur FROM fsc_parametre WHERE cle = ?", (CLE_DEPUIS,)
        ).fetchone()
    except sqlite3.Error:
        return None
    valeur = (r["valeur"] if r and "valeur" in r.keys() else None) or ""
    return valeur.strip()[:10] or None


def definir_date_entree(conn, jour: str, utilisateur: Optional[str] = None) -> str:
    jour = (jour or "").strip()[:10]
    datetime.strptime(jour, "%Y-%m-%d")  # lève si le format est faux
    conn.execute(
        "INSERT INTO fsc_parametre (cle, valeur, modifie_le, modifie_par) VALUES (?,?,?,?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur, "
        "modifie_le=excluded.modifie_le, modifie_par=excluded.modifie_par",
        (CLE_DEPUIS, jour, _now(), utilisateur),
    )
    conn.commit()
    return jour


# ══════════════════════════════════════════════════════════════════
# Rapprochement fournisseur
# ══════════════════════════════════════════════════════════════════

def index_fournisseurs(conn) -> tuple[dict, dict]:
    """({numfou: fiche}, {nom normalisé: fiche}) des fournisseurs de l'annuaire.

    Le numéro RVGI fait foi quand il est renseigné. Le nom ne sert qu'à défaut :
    « ARCONVERT S.A » côté ERP et « Fedrigoni Manter » côté MySifa désignent le
    même fournisseur et aucune comparaison de chaînes ne le devinera. Une ligne
    non rapprochée entre quand même au registre, signalée — la faire disparaître
    serait le pire des deux maux devant un auditeur.
    """
    par_numero: dict[int, dict] = {}
    par_nom: dict[str, dict] = {}
    # `rvgi_numero` est arrivé avec le rapprochement des tiers : une instance qui
    # ne l'a pas encore se rabat sur le nom au lieu de tomber.
    colonnes = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
    voulues = [c for c in ("id", "nom", "licence", "certificat", "has_fsc", "actif",
                           "rvgi_numero", "fsc_date_expiration") if c in colonnes]
    for r in conn.execute("SELECT %s FROM fournisseurs_fsc" % ", ".join(voulues)).fetchall():
        f = dict(r)
        if f.get("rvgi_numero"):
            par_numero[int(f["rvgi_numero"])] = f
        cle = normaliser_nom(f["nom"])
        if cle:
            par_nom.setdefault(cle, f)
    return par_numero, par_nom


def trouver_fournisseur(numfou, nom_rvgi, par_numero, par_nom) -> Optional[dict]:
    if numfou is not None:
        try:
            hit = par_numero.get(int(numfou))
        except (TypeError, ValueError):
            hit = None
        if hit:
            return hit
    cle = normaliser_nom(nom_rvgi or "")
    if not cle:
        return None
    if cle in par_nom:
        return par_nom[cle]
    # Inclusion dans un sens ou dans l'autre : « likexin » tient dans
    # « shenzhen likexin industrial », et « mosaico » est le nom d'usage de
    # « Burgo / Mosaico ». Deux candidats = pas de réponse : « FRIMPEKS LTD »
    # peut être Italy, UK ou Turkey, et seul un humain sait laquelle.
    mots = set(cle.split())
    candidats = [f for k, f in par_nom.items()
                 if (set(k.split()) and mots)
                 and (set(k.split()) <= mots or mots <= set(k.split()))]
    uniques = {f["id"]: f for f in candidats}
    return next(iter(uniques.values())) if len(uniques) == 1 else None


def rattacher_fournisseur(conn, numfou: int, fournisseur_id: int,
                          nom_rvgi: Optional[str] = None,
                          utilisateur: Optional[str] = None) -> int:
    """Lie un numéro de tiers RVGI à une fiche de l'annuaire, et reprend les
    lignes déjà importées qui portent ce numéro. Rend le nombre de lignes reprises."""
    fiche = conn.execute(
        "SELECT id, nom, licence, certificat, has_fsc, fsc_date_expiration "
        "FROM fournisseurs_fsc WHERE id = ?", (fournisseur_id,)
    ).fetchone()
    if not fiche:
        raise ValueError("Fournisseur introuvable.")
    fiche = dict(fiche)
    colonnes = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
    if "rvgi_numero" in colonnes:
        sets, vals = ["rvgi_numero = ?"], [int(numfou)]
        if "rvgi_rs" in colonnes:
            sets.append("rvgi_rs = COALESCE(rvgi_rs, ?)"); vals.append(_txt(nom_rvgi))
        if "rvgi_lie_le" in colonnes:
            sets.append("rvgi_lie_le = ?"); vals.append(_now())
        if "updated_at" in colonnes:
            sets.append("updated_at = ?"); vals.append(_now())
        conn.execute("UPDATE fournisseurs_fsc SET %s WHERE id = ?" % ", ".join(sets),
                     [*vals, fournisseur_id])
    reprises = 0
    for r in conn.execute(
        "SELECT * FROM fsc_reception WHERE numfou = ? AND fournisseur_id IS NULL",
        (int(numfou),),
    ).fetchall():
        ligne = dict(r)
        verdict = evaluer_certificat(fiche, ligne["date_reception"])
        conn.execute(
            "UPDATE fsc_reception SET fournisseur_id=?, code_certificat_attendu=?, "
            "licence_attendue=?, certificat_expiration=?, certificat_statut=?, "
            "eligible=?, modifie_le=? WHERE id=?",
            (
                fournisseur_id, fiche.get("certificat"), fiche.get("licence"),
                verdict.get("expiration"), verdict["statut"],
                evaluer_eligibilite({**ligne, "certificat_statut": verdict["statut"]}),
                _now(), ligne["id"],
            ),
        )
        journaliser(conn, ligne["id"], "fournisseur_id", None, fournisseur_id, utilisateur)
        reprises += 1
    conn.commit()
    return reprises


# ══════════════════════════════════════════════════════════════════
# Éligibilité
# ══════════════════════════════════════════════════════════════════

def evaluer_eligibilite(ligne: dict) -> str:
    """oui | non | a_verifier | ecart_bl_facture. Voir l'en-tête du module."""
    statut = (ligne.get("certificat_statut") or "").strip()
    bl = (ligne.get("allegation_bl") or "").strip()
    facture = (ligne.get("allegation_facture") or "").strip()
    code = ligne.get("code_certificat_present")
    pct = ligne.get("pourcentage")

    if statut == "non_certifie":
        return "non"
    if statut == "expire":
        return "non"
    if not statut or statut == "inconnu":
        # Fournisseur non rattaché, ou fiche sans date d'expiration : on ne sait
        # pas, et on le dit.
        return "a_verifier"
    if not bl or not facture or code is None:
        return "a_verifier"
    if bl != facture:
        return "ecart_bl_facture"
    if facture in ("aucune", "fsc_controlled_wood"):
        return "non"
    if not int(code):
        return "non"
    if FSC_ALLEGATIONS.get(facture, {}).get("pct") and _f(pct) is None:
        return "a_verifier"
    return "oui"


def label_autorise(allegation: Optional[str], pourcentage=None) -> bool:
    """Le label FSC est-il autorisé pour cette allégation ? (FSC-STD-50-001 V2-1)

    Sert au registre des ventes ; ici il ne juge que ce qui entre.
    """
    regle = FSC_ALLEGATIONS.get((allegation or "").strip())
    if not regle:
        return False
    if regle["label"] is None:
        p = _f(pourcentage)
        return p is not None and p >= FSC_SEUIL_LABEL_PCT
    return bool(regle["label"])


# ══════════════════════════════════════════════════════════════════
# Import
# ══════════════════════════════════════════════════════════════════

def _type_matiere(type_code: int) -> str:
    cat = PERIMETRE.get(int(type_code), (None, None, None))[0]
    return cat or "matiere"


def lignes_rvgi(conn_erp, depuis: str) -> list[dict]:
    """Les lignes de réception du miroir, à partir de la date d'entrée."""
    sql = _SQL_IMPORT % ",".join(str(t) for t in FSC_TYPES_REGISTRE)
    return [dict(r) for r in conn_erp.execute(sql, (depuis, depuis)).fetchall()]


def importer(conn, conn_erp, utilisateur: Optional[str] = None) -> dict:
    """Ajoute au registre les réceptions RVGI qui n'y sont pas encore.

    N'écrit jamais sur une ligne existante : `lif_id` est unique et l'insertion
    est un `INSERT OR IGNORE`. Rend un bilan chiffré.
    """
    depuis = date_entree(conn)
    if not depuis:
        return {"ajoutees": 0, "deja_presentes": 0, "sans_fournisseur": 0,
                "erreur": "Date d'entrée dans la chaîne de contrôle non renseignée."}

    par_numero, par_nom = index_fournisseurs(conn)
    connues = {int(r["lif_id"]) for r in conn.execute(
        "SELECT lif_id FROM fsc_reception").fetchall()}
    # Ce que MyStock a déjà intégré : la réception rattachée, et le claim déjà
    # saisi au magasin. Autant ne pas le redemander.
    deja_stock: dict[int, dict] = {}
    try:
        for r in conn.execute(
            """SELECT i.lif_id, i.reception_id, s.fsc_type_claim, s.certificat_fsc
                 FROM erp_reception_integree i
                 LEFT JOIN stock_receptions s ON s.id = i.reception_id"""
        ).fetchall():
            deja_stock[int(r["lif_id"])] = dict(r)
    except sqlite3.Error:
        pass

    ajoutees = sans_fournisseur = deja = 0
    maintenant = _now()
    for r in lignes_rvgi(conn_erp, depuis):
        lif_id = int(r["lif_id"])
        if lif_id in connues:
            deja += 1
            continue
        fiche = trouver_fournisseur(r.get("numfou"), r.get("fournisseur_rvgi"),
                                    par_numero, par_nom)
        if fiche is None:
            sans_fournisseur += 1
        verdict = (evaluer_certificat(fiche, r["date_reception"]) if fiche
                   else {"statut": None, "expiration": None})
        laize = _f(r.get("laize_mm"))
        ml = _f(r.get("quantite_ml"))
        type_code = int(r.get("type_code") or 0)
        stock = deja_stock.get(lif_id) or {}
        ligne = {
            "lif_id": lif_id,
            "cde_numero": r.get("cde_numero"),
            "cde_ligne": r.get("cde_ligne"),
            "date_reception": r["date_reception"],
            "date_saisie_rvgi": r.get("date_saisie_rvgi"),
            "num_bl": _txt(r.get("num_bl")),
            "numfou": r.get("numfou"),
            "fournisseur_rvgi": _txt(r.get("fournisseur_rvgi")),
            "fournisseur_id": fiche["id"] if fiche else None,
            "code1": _txt(r.get("code1")),
            "code2": _txt(r.get("code2")),
            "code_matiere": "/".join(x for x in (_txt(r.get("code1")), _txt(r.get("code2"))) if x),
            "type_code": type_code,
            "type_matiere": _type_matiere(type_code),
            "origine_forestiere": 0 if type_code in FSC_TYPES_NON_FORESTIERS else 1,
            "designation": _txt(r.get("designation")),
            "libelle_matiere": _txt(r.get("libelle_matiere")),
            "ref_fournisseur": _txt(r.get("ref_fournisseur")),
            "laize_mm": laize,
            "quantite_ml": ml,
            # `qte` est en mètres LINÉAIRES malgré un `cua` en mètres carrés.
            "quantite_m2": round(ml * laize / 1000.0, 2) if (ml and laize) else None,
            "piece_facture_rvgi": r.get("piece_facture_rvgi"),
            "ligne_facture_rvgi": r.get("ligne_facture_rvgi"),
            "reception_id": stock.get("reception_id"),
            "code_certificat_attendu": (fiche or {}).get("certificat"),
            "licence_attendue": (fiche or {}).get("licence"),
            "certificat_expiration": verdict.get("expiration"),
            "certificat_statut": verdict.get("statut"),
            "num_facture_fournisseur": None,
            "allegation_bl": None,
            "allegation_facture": None,
            "pourcentage": None,
            "code_certificat_present": None,
            "etiquette_posee": None,
            "observations": "",
            "importe_le": maintenant,
            "importe_par": utilisateur,
        }
        ligne["eligible"] = evaluer_eligibilite(ligne)
        colonnes = list(ligne.keys())
        conn.execute(
            "INSERT OR IGNORE INTO fsc_reception (%s) VALUES (%s)"
            % (", ".join(colonnes), ", ".join(["?"] * len(colonnes))),
            [ligne[c] for c in colonnes],
        )
        ajoutees += 1
    conn.commit()
    return {"ajoutees": ajoutees, "deja_presentes": deja,
            "sans_fournisseur": sans_fournisseur, "depuis": depuis}


# ══════════════════════════════════════════════════════════════════
# Saisie, journal
# ══════════════════════════════════════════════════════════════════

def journaliser(conn, ligne_id: int, champ: str, avant, apres,
                utilisateur: Optional[str] = None) -> None:
    conn.execute(
        "INSERT INTO fsc_journal (table_cible, ligne_id, champ, ancienne_valeur, "
        "nouvelle_valeur, utilisateur, horodatage) VALUES (?,?,?,?,?,?,?)",
        (TABLE, ligne_id, champ,
         None if avant is None else str(avant),
         None if apres is None else str(apres),
         utilisateur, _now()),
    )


def _valider(champs: dict) -> dict:
    """Normalise et refuse ce qui n'est pas dans les listes fermées."""
    propre: dict[str, Any] = {}
    for cle, valeur in champs.items():
        if cle not in CHAMPS_SAISIS:
            continue
        if cle in ("allegation_bl", "allegation_facture"):
            v = (valeur or "").strip()
            if v and v not in FSC_ALLEGATIONS:
                raise ValueError("Allégation inconnue : %s." % v)
            propre[cle] = v or None
        elif cle == "pourcentage":
            v = _f(valeur)
            if v is not None and not (0 <= v <= 100):
                raise ValueError("Pourcentage hors plage (0 à 100).")
            propre[cle] = v
        elif cle == "code_certificat_present":
            propre[cle] = None if valeur in (None, "") else int(bool(int(valeur)))
        elif cle == "etiquette_posee":
            v = (valeur or "").strip()
            if v and v not in FSC_ETIQUETTES:
                raise ValueError("Étiquette inconnue : %s." % v)
            propre[cle] = v or None
        else:
            propre[cle] = (valeur or "").strip() or ("" if cle == "observations" else None)
    return propre


def mettre_a_jour(conn, ligne_id: int, champs: dict,
                  utilisateur: Optional[str] = None) -> dict:
    """Écrit les champs saisis, journalise chaque changement, recalcule le verdict."""
    avant = conn.execute("SELECT * FROM fsc_reception WHERE id = ?", (ligne_id,)).fetchone()
    if not avant:
        raise ValueError("Ligne de registre introuvable.")
    avant = dict(avant)
    propre = _valider(champs)
    if not propre:
        return avant

    changes = {c: v for c, v in propre.items() if (avant.get(c) or None) != (v or None)}
    if not changes:
        return avant
    apres = {**avant, **changes}
    apres["eligible"] = evaluer_eligibilite(apres)
    if apres["eligible"] != avant["eligible"]:
        changes["eligible"] = apres["eligible"]
    changes["controle_par"] = utilisateur
    changes["controle_le"] = _now()
    changes["modifie_le"] = _now()

    conn.execute(
        "UPDATE fsc_reception SET %s WHERE id = ?" % ", ".join("%s = ?" % c for c in changes),
        [*changes.values(), ligne_id],
    )
    for champ, valeur in changes.items():
        if champ in ("modifie_le", "controle_le", "controle_par"):
            continue
        journaliser(conn, ligne_id, champ, avant.get(champ), valeur, utilisateur)
    conn.commit()
    return dict(conn.execute("SELECT * FROM fsc_reception WHERE id = ?", (ligne_id,)).fetchone())


def appliquer_au_bl(conn, ligne_id: int, utilisateur: Optional[str] = None) -> int:
    """Recopie la saisie de cette ligne sur toutes celles du même BL.

    Même fournisseur et même numéro de bon : une facture couvre souvent trois à
    cinq lignes du même bon, et les ressaisir à l'identique est la meilleure
    façon d'en rater une. Les lignes déjà saisies sont écrasées — c'est le sens
    du geste — mais chaque écrasement passe par le journal.
    """
    source = conn.execute("SELECT * FROM fsc_reception WHERE id = ?", (ligne_id,)).fetchone()
    if not source:
        raise ValueError("Ligne de registre introuvable.")
    source = dict(source)
    if not source.get("num_bl"):
        raise ValueError("Cette ligne n'a pas de numéro de BL : rien à propager.")
    valeurs = {c: source.get(c) for c in CHAMPS_BL}
    cibles = conn.execute(
        "SELECT id FROM fsc_reception WHERE num_bl = ? AND COALESCE(numfou,-1) = COALESCE(?,-1) "
        "AND id <> ?",
        (source["num_bl"], source.get("numfou"), ligne_id),
    ).fetchall()
    n = 0
    for c in cibles:
        mettre_a_jour(conn, int(c["id"]), valeurs, utilisateur)
        n += 1
    return n


# ══════════════════════════════════════════════════════════════════
# Lecture pour l'écran
# ══════════════════════════════════════════════════════════════════

def lister(conn, debut=None, fin=None, fournisseur_id=None, eligible=None,
           certifies_seuls=False, recherche=None, limite=1000) -> list[dict]:
    where, params = ["1=1"], []
    if debut:
        where.append("r.date_reception >= ?"); params.append(str(debut)[:10])
    if fin:
        where.append("r.date_reception <= ?"); params.append(str(fin)[:10])
    if fournisseur_id:
        where.append("r.fournisseur_id = ?"); params.append(int(fournisseur_id))
    if eligible:
        where.append("r.eligible = ?"); params.append(eligible)
    if certifies_seuls:
        where.append("f.id IS NOT NULL AND COALESCE(f.has_fsc,1) = 1")
    if recherche:
        motif = "%%%s%%" % str(recherche).strip().lower()
        where.append("(LOWER(COALESCE(r.num_bl,'')) LIKE ? OR LOWER(COALESCE(r.fournisseur_rvgi,'')) LIKE ?"
                     " OR LOWER(COALESCE(r.designation,'')) LIKE ? OR LOWER(COALESCE(r.code_matiere,'')) LIKE ?"
                     " OR LOWER(COALESCE(r.num_facture_fournisseur,'')) LIKE ?)")
        params.extend([motif] * 5)
    rows = conn.execute(
        """SELECT r.*, f.nom AS fournisseur_nom, f.has_fsc AS fournisseur_certifie
             FROM fsc_reception r
             LEFT JOIN fournisseurs_fsc f ON f.id = r.fournisseur_id
            WHERE %s
            ORDER BY r.date_reception DESC, r.num_bl, r.cde_ligne
            LIMIT ?""" % " AND ".join(where),
        [*params, int(limite)],
    ).fetchall()
    return [dict(r) for r in rows]


def stats(lignes: list[dict]) -> dict:
    return {
        "lignes": len(lignes),
        "oui": sum(1 for l in lignes if l["eligible"] == "oui"),
        "non": sum(1 for l in lignes if l["eligible"] == "non"),
        "a_verifier": sum(1 for l in lignes if l["eligible"] == "a_verifier"),
        "ecart": sum(1 for l in lignes if l["eligible"] == "ecart_bl_facture"),
        "sans_fournisseur": sum(1 for l in lignes if not l.get("fournisseur_id")),
        "m2_eligibles": round(sum((l.get("quantite_m2") or 0) for l in lignes
                                  if l["eligible"] == "oui"), 2),
    }


def volumes_par_allegation(lignes: list[dict]) -> list[dict]:
    """Entrées éligibles par allégation — ce que l'organisme certificateur demande."""
    agg: dict[str, dict] = {}
    for l in lignes:
        if l["eligible"] != "oui":
            continue
        cle = l.get("allegation_facture") or "aucune"
        e = agg.setdefault(cle, {"code": cle,
                                 "libelle": FSC_ALLEGATIONS.get(cle, {}).get("libelle", cle),
                                 "lignes": 0, "ml": 0.0, "m2": 0.0})
        e["lignes"] += 1
        e["ml"] += l.get("quantite_ml") or 0
        e["m2"] += l.get("quantite_m2") or 0
    for e in agg.values():
        e["ml"] = round(e["ml"], 1)
        e["m2"] = round(e["m2"], 2)
    return [agg[k] for k in FSC_ALLEGATIONS if k in agg]


def journal(conn, ligne_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT champ, ancienne_valeur, nouvelle_valeur, utilisateur, horodatage "
        "FROM fsc_journal WHERE table_cible = ? AND ligne_id = ? "
        "ORDER BY horodatage DESC, id DESC", (TABLE, ligne_id)).fetchall()]


# ══════════════════════════════════════════════════════════════════
# Export
# ══════════════════════════════════════════════════════════════════

_COLONNES_EXPORT = [
    ("date_reception", "Date de réception"),
    ("num_bl", "N° de BL"),
    ("fournisseur_nom", "Fournisseur"),
    ("licence_attendue", "Licence FSC"),
    ("code_certificat_attendu", "Code de certificat"),
    ("certificat_statut", "Certificat à la date du BL"),
    ("code_matiere", "Référence"),
    ("designation", "Désignation"),
    ("type_matiere", "Type"),
    ("laize_mm", "Laize (mm)"),
    ("quantite_ml", "Quantité (ml)"),
    ("quantite_m2", "Quantité (m²)"),
    ("num_facture_fournisseur", "N° de facture fournisseur"),
    ("allegation_bl", "Allégation sur le BL"),
    ("allegation_facture", "Allégation sur la facture"),
    ("pourcentage", "Pourcentage"),
    ("code_certificat_present", "Code de certificat présent"),
    ("eligible", "Éligible FSC"),
    ("etiquette_posee", "Étiquette"),
    ("controle_par", "Contrôlé par"),
    ("controle_le", "Contrôlé le"),
    ("observations", "Observations"),
]

_LIB_ELIGIBLE = {"oui": "Oui", "non": "Non", "a_verifier": "À vérifier",
                 "ecart_bl_facture": "Écart BL / facture"}
_LIB_CERTIF = {"valide": "Valide", "expire": "Expiré", "inconnu": "Inconnu",
               "non_certifie": "Non certifié"}


def export_xlsx(lignes: list[dict], debut: Optional[str], fin: Optional[str],
                titre: str = "Registre des approvisionnements FSC") -> bytes:
    """Le registre d'une période, figé dans un classeur.

    L'auditeur demande une période précise et veut la figer : deux feuilles, le
    registre et le récapitulatif par allégation, plus les critères en tête.
    """
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Approvisionnements"
    ws["A1"] = titre
    ws["A1"].font = Font(bold=True, size=13)
    periode = "Période : %s → %s" % (debut or "origine", fin or "aujourd'hui")
    ws["A2"] = "%s · %d ligne(s) · édité le %s" % (
        periode, len(lignes), datetime.now().strftime("%d/%m/%Y %H:%M"))
    ws["A2"].font = Font(italic=True, color="475569")  # hex-ok (feuille Excel)

    entete = 4
    for i, (_, libelle) in enumerate(_COLONNES_EXPORT, start=1):
        c = ws.cell(row=entete, column=i, value=libelle)
        c.font = Font(bold=True, color="FFFFFF")  # hex-ok (feuille Excel)
        c.fill = PatternFill("solid", fgColor="0F172A")  # hex-ok (feuille Excel)
        c.alignment = Alignment(vertical="center", wrap_text=True)

    for n, ligne in enumerate(lignes, start=entete + 1):
        for i, (cle, _) in enumerate(_COLONNES_EXPORT, start=1):
            v = ligne.get(cle)
            if cle in ("allegation_bl", "allegation_facture"):
                v = FSC_ALLEGATIONS.get(v or "", {}).get("libelle", v)
            elif cle == "eligible":
                v = _LIB_ELIGIBLE.get(v, v)
            elif cle == "certificat_statut":
                v = _LIB_CERTIF.get(v, v or "—")
            elif cle == "code_certificat_present":
                v = "" if v is None else ("Oui" if int(v) else "Non")
            elif cle == "etiquette_posee" and v:
                v = v.capitalize()
            ws.cell(row=n, column=i, value=v)

    largeurs = {"date_reception": 14, "num_bl": 18, "fournisseur_nom": 24, "designation": 34,
                "observations": 34, "num_facture_fournisseur": 20, "allegation_bl": 18,
                "allegation_facture": 18, "eligible": 16, "certificat_statut": 20}
    for i, (cle, libelle) in enumerate(_COLONNES_EXPORT, start=1):
        ws.column_dimensions[get_column_letter(i)].width = largeurs.get(cle, max(12, len(libelle) + 2))
    ws.freeze_panes = ws.cell(row=entete + 1, column=1)

    ws2 = wb.create_sheet("Volumes par allégation")
    ws2.append(["Allégation", "Lignes", "Mètres linéaires", "Mètres carrés"])
    for c in ws2[1]:
        c.font = Font(bold=True)
    for v in volumes_par_allegation(lignes):
        ws2.append([v["libelle"], v["lignes"], v["ml"], v["m2"]])
    ws2.append([])
    ws2.append([periode])
    for i, w in enumerate((28, 10, 18, 16), start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
