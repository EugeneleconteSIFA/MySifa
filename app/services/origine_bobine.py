"""Retrouver le fournisseur d'une bobine à partir de son seul code-barres.

Le problème, mesuré avant d'écrire une ligne
--------------------------------------------
Sur les 90 scans matière de la saisie de production, AUCUN n'était rattaché à
une réception : 57 portaient un fournisseur tapé à la main, 33 rien du tout.
Le rattachement automatique existait pourtant déjà — il cherche le code scanné
dans `stock_reception_items` — mais il ne trouvait jamais rien, faute de
réceptions saisies au code-barres (25 bobines en tout, la dernière le
29/06/2026).

Et la saisie manuelle se contredit : `R1001-26050458-440-*` a été déclaré
Frimpeks UK sur une bobine et Likexin sur l'autre ; `R1101-SGD26020324-*` a été
déclaré Sato, Shine ET Likexin. Une origine matière qui repose sur ce que
l'opérateur se rappelle n'est pas une traçabilité.

Ce que ce module ajoute
-----------------------
Une cascade, du certain au probable, qui rend TOUJOURS son niveau de confiance :

    1. réception    le code est dans une réception scannée   → certain, DÉMONTRÉ
    2. historique   ce code exact a déjà été identifié        → probable
    3. signature    la FORME du code désigne un fournisseur   → probable ou suggéré
    4. dossier      les autres bobines du dossier en cours    → suggéré

Le palier 3 est le seul qui demande une explication. Un code-barres de bobine
n'est pas quelconque : il porte la marque de qui l'a imprimé. Kanzan livre des
codes de 11 chiffres commençant par 60 ; UPM Raflatac émet des GTIN et des SSCC
qui partagent tous le préfixe GS1 `641578`. On n'a donc pas besoin d'écrire ces
règles à la main : il suffit de les APPRENDRE de chaque identification confirmée,
et de ne s'en servir que là où l'historique est unanime.

Ce que le module ne fait PAS, et c'est délibéré
----------------------------------------------
Un fournisseur détecté n'apporte JAMAIS de certificat FSC. Seule la réception
démontre l'origine d'une bobine ; une signature, si régulière soit-elle, ne fait
que la déclarer. La cascade sert à ne plus faire taper l'opérateur, pas à
fabriquer une preuve d'audit. C'est `liaison_mode` qui garde cette distinction
('reception' = démontré, 'manual' = déclaré) et ce module n'y touche pas.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Longueurs de préfixe apprises sur un code numérique, de la plus discriminante
# à la plus large. Au-delà de 8 on décrirait la bobine et non le fournisseur ;
# en deçà de 2 on ne décrirait plus rien.
LONGUEURS_PREFIXE = (8, 7, 6, 5, 4, 3, 2)

# Nombre d'identifications concordantes à partir duquel une signature cesse
# d'être une coïncidence. Trois, parce que deux bobines consécutives d'une même
# palette ne prouvent rien de plus qu'une seule.
SEUIL_PROBABLE = 3

# Part que doit tenir le fournisseur majoritaire d'une signature. En dessous de
# 0,6 la signature ne désigne plus personne : on rend la liste des candidats et
# on laisse l'opérateur trancher — ce qui reste plus rapide que l'annuaire entier.
PART_PROBABLE = 0.8
PART_SUGGERE = 0.6

_SEPARATEURS = re.compile(r"[-._/ ]+")


# ── Normalisation GS1 ────────────────────────────────────────────────────────

def variantes(code: str) -> List[str]:
    """Formes d'un même code numérique, enveloppe GS1 retirée.

    Un fabricant émet ses identifiants sous plusieurs habillages : UPM Raflatac
    apparaît chez SIFA en EAN-13 (`6415788160497`) et en SSCC préfixé de son AI
    (`00364157811504575495`). Bruts, ces deux codes n'ont rien en commun —
    l'un commence par `641578`, l'autre par `003641`. Débarrassés de leur
    enveloppe, ils partagent le préfixe entreprise `641578`, qui est justement
    ce que GS1 attribue au fabricant et ne change jamais.

    On ne cherche pas à décoder complètement le GS1 (les AI concaténés, les
    séparateurs FNC1) : on retire ce qui précède le préfixe entreprise, et on
    laisse l'apprentissage faire le reste.
    """
    brut = (code or "").strip()
    if not brut or not brut.isdigit():
        return []
    out = [brut]

    def _ajouter(v: str) -> None:
        if len(v) >= 8 and v not in out:
            out.append(v)

    n = len(brut)
    if n == 20 and brut.startswith("00"):
        # AI (00) + SSCC 18 : on retire l'AI, puis le chiffre d'extension qui
        # appartient à l'expéditeur et non au fabricant.
        _ajouter(brut[2:])
        _ajouter(brut[3:])
    elif n == 18:
        _ajouter(brut[1:])
    elif n == 14:
        # GTIN-14 : le premier chiffre est l'indicateur de niveau
        # d'emballage, pas une donnée d'identité.
        _ajouter(brut[1:])
    return out


# ── Signatures ───────────────────────────────────────────────────────────────

def signatures_candidates(code: str) -> List[Tuple[str, str, int]]:
    """Signatures que porte un code, de la plus spécifique à la plus large.

    Deux familles, parce que les codes-barres de bobines se rangent en deux :

    - `num` — le code est numérique. La signature est sa LONGUEUR et son
      préfixe : `11|602` se lit « onze chiffres commençant par 602 ». La
      longueur compte autant que le préfixe, un fournisseur gardant son format.
    - `seg` — le code est structuré par des séparateurs (`R1101-26050459-440-16`).
      La signature est son premier segment et son nombre de segments :
      `R1101|4`. Ni le lot ni le numéro de bobine n'y entrent : ils changent à
      chaque bobine, et une signature qui change à chaque bobine n'apprend rien.
    """
    brut = (code or "").strip().upper()
    if not brut:
        return []

    out: List[Tuple[str, str, int]] = []
    vus = set()

    def _poser(typ: str, valeur: str, spec: int) -> None:
        cle = (typ, valeur)
        if cle in vus:
            return
        vus.add(cle)
        out.append((typ, valeur, spec))

    formes = variantes(brut)
    if formes:
        # Signature de FORMAT : longueur du code entière + préfixe. C'est ce qui
        # décrit un code maison — Kanzan émet des codes de 11 chiffres, Burgo
        # de 12, et cette longueur fait partie de leur identité.
        for k in LONGUEURS_PREFIXE:
            if k < len(brut):
                _poser("num", "%d|%s" % (len(brut), brut[:k]), k)

        # Signature GS1 : préfixe entreprise, sans la longueur. Un fabricant
        # émet le MÊME préfixe sous des habillages de tailles différentes —
        # UPM Raflatac apparaît en EAN-13 `6415788160497` et en SSCC
        # `00364157811504575495`, qui n'ont en commun que `641578` une fois
        # l'enveloppe retirée. Contraindre la longueur ici casserait justement
        # le seul rapprochement que GS1 permet de faire.
        if len(brut) >= 12:
            for v in formes:
                for k in LONGUEURS_PREFIXE:
                    if k < 5 or k >= len(v):
                        continue
                    _poser("gs1", v[:k], k + 1)

    segments = [s for s in _SEPARATEURS.split(brut) if s]
    if len(segments) >= 2 and not brut.isdigit():
        # Une signature de segment est aussi discriminante qu'un préfixe long :
        # elle porte un identifiant émetteur entier, pas une tranche.
        _poser("seg", "%s|%d" % (segments[0], len(segments)), 10)

    out.sort(key=lambda t: -t[2])
    return out


def _charger_observations(row) -> Dict[str, int]:
    try:
        d = json.loads(row["observations"] or "{}")
    except (ValueError, TypeError):
        return {}
    return {str(k): int(v) for k, v in d.items() if str(k).strip()}


def apprendre(conn, code: str, fournisseur_nom: str) -> int:
    """Enregistre une identification confirmée dans toutes ses signatures.

    Appelé à chaque fois qu'un fournisseur est ARRÊTÉ sur un code — que ce soit
    par une réception ou par un opérateur. C'est la seule façon d'obtenir des
    règles qui collent aux fournisseurs réels de SIFA plutôt qu'à des motifs
    devinés : l'application apprend ce qu'on lui montre, et la détection
    s'améliore d'elle-même à mesure qu'on scanne.

    Rien n'est écrasé : chaque signature garde le COMPTE par fournisseur. Une
    signature vue sous deux noms n'est pas supprimée, elle devient ambiguë —
    et c'est cette ambiguïté qui empêchera de proposer un fournisseur faux.
    """
    nom = (fournisseur_nom or "").strip()
    if not nom:
        return 0
    from datetime import datetime
    maintenant = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    n = 0
    for typ, valeur, spec in signatures_candidates(code):
        row = conn.execute(
            "SELECT id, observations, total FROM bobine_signatures WHERE type=? AND valeur=?",
            (typ, valeur),
        ).fetchone()
        if row:
            obs = _charger_observations(row)
            obs[nom] = obs.get(nom, 0) + 1
            conn.execute(
                """UPDATE bobine_signatures
                      SET observations=?, total=?, dernier_vu=?
                    WHERE id=?""",
                (json.dumps(obs, ensure_ascii=False), sum(obs.values()),
                 maintenant, int(row["id"])),
            )
        else:
            conn.execute(
                """INSERT INTO bobine_signatures
                   (type, valeur, specificite, observations, total, premier_vu, dernier_vu)
                   VALUES (?,?,?,?,?,?,?)""",
                (typ, valeur, spec,
                 json.dumps({nom: 1}, ensure_ascii=False), 1,
                 maintenant, maintenant),
            )
        n += 1
    return n


def _verdict(obs: Dict[str, int]) -> Tuple[Optional[str], str, List[Dict[str, Any]]]:
    """Ce qu'une signature permet d'affirmer, et à quel titre."""
    total = sum(obs.values())
    if total <= 0:
        return None, "aucune", []
    classes = sorted(obs.items(), key=lambda kv: -kv[1])
    candidats = [{"nom": k, "observations": v} for k, v in classes]
    tete_nom, tete_n = classes[0]
    part = tete_n / float(total)
    if part >= PART_PROBABLE and tete_n >= SEUIL_PROBABLE:
        return tete_nom, "probable", candidats
    if part >= PART_SUGGERE:
        return tete_nom, "suggere", candidats
    # Plusieurs fournisseurs se partagent la forme : on ne désigne personne,
    # mais la liste courte vaut mieux que l'annuaire complet.
    return None, "ambigu", candidats


# ── Cascade ──────────────────────────────────────────────────────────────────

def _fiche_fournisseur(conn, nom: str) -> Optional[dict]:
    if not nom:
        return None
    row = conn.execute(
        "SELECT id, nom, licence FROM fournisseurs_fsc WHERE trim(nom)=trim(?) LIMIT 1",
        (nom,),
    ).fetchone()
    return dict(row) if row else None


def _resultat(source: str, confiance: str, nom: Optional[str],
              explication: str, conn, candidats=None, **extra) -> Dict[str, Any]:
    fiche = _fiche_fournisseur(conn, nom or "")
    d: Dict[str, Any] = {
        "trouve": bool(nom) or bool(candidats),
        "source": source,
        "confiance": confiance,
        "fournisseur": nom,
        "fournisseur_id": (fiche or {}).get("id"),
        "licence": (fiche or {}).get("licence") or "",
        "hors_annuaire": bool(nom) and fiche is None,
        "explication": explication,
        "candidats": candidats or [],
        # Seule la réception démontre. Tout le reste est déclaratif, et l'écran
        # doit pouvoir le dire à l'opérateur au moment où il valide.
        "demontre": source == "reception",
    }
    d.update(extra)
    return d


def _vide() -> Dict[str, Any]:
    return {
        "trouve": False, "source": None, "confiance": "aucune",
        "fournisseur": None, "fournisseur_id": None, "licence": "",
        "hors_annuaire": False, "candidats": [], "demontre": False,
        "explication": "Aucun élément ne permet de rattacher ce code à un fournisseur.",
    }


def resoudre(conn, code: str, no_dossier: Optional[str] = None) -> Dict[str, Any]:
    """Le fournisseur d'un code-barres, et ce qui permet de l'affirmer."""
    brut = (code or "").strip()
    if not brut:
        return _vide()

    # 1 ── La réception. Le seul palier qui DÉMONTRE : la bobine a été scannée
    # à l'arrivée, sous le bon de livraison d'un fournisseur, avec son certificat.
    rec = conn.execute(
        """SELECT r.id AS reception_id, r.fournisseur, r.certificat_fsc,
                  r.fsc_type_claim, ff.licence AS licence
             FROM stock_reception_items i
             JOIN stock_receptions r ON r.id = i.reception_id
        LEFT JOIN fournisseurs_fsc ff ON trim(ff.nom) = trim(r.fournisseur)
            WHERE trim(i.code_barre) = trim(?)
         ORDER BY i.scanned_at DESC, i.id DESC
            LIMIT 1""",
        (brut,),
    ).fetchone()
    if rec and rec["reception_id"]:
        return _resultat(
            "reception", "certain", rec["fournisseur"],
            "Cette bobine a été scannée en réception.",
            conn,
            reception_id=int(rec["reception_id"]),
            certificat_fsc=rec["certificat_fsc"],
            fsc_type_claim=rec["fsc_type_claim"] or "non_fsc",
        )

    # 2 ── Ce code exact, déjà identifié en production. Une bobine sert souvent
    # sur plusieurs dossiers : le deuxième scan n'a pas à reposer la question.
    lignes = conn.execute(
        """SELECT COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS nom, COUNT(*) n
             FROM fab_matieres_utilisees fmu
        LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
            WHERE trim(fmu.code_barre) = trim(?)
              AND COALESCE(sr.fournisseur, fmu.fournisseur_manual) IS NOT NULL
         GROUP BY nom
         ORDER BY n DESC""",
        (brut,),
    ).fetchall()
    if lignes:
        obs = {r["nom"]: int(r["n"]) for r in lignes if (r["nom"] or "").strip()}
        if obs:
            nom, confiance, candidats = _verdict(obs)
            if len(obs) == 1:
                seul = candidats[0]
                return _resultat(
                    "historique", "probable", seul["nom"],
                    "Ce code-barres a déjà été identifié %s en production."
                    % ("une fois" if seul["observations"] == 1
                       else "%d fois" % seul["observations"]),
                    conn, candidats=candidats,
                )
            return _resultat(
                "historique", confiance, nom,
                "Ce code-barres a déjà été identifié en production, sous "
                "%d fournisseurs différents." % len(obs),
                conn, candidats=candidats,
            )

    # 3 ── La forme du code. Ce que le fournisseur imprime lui ressemble.
    for typ, valeur, _spec in signatures_candidates(brut):
        row = conn.execute(
            "SELECT observations FROM bobine_signatures WHERE type=? AND valeur=?",
            (typ, valeur),
        ).fetchone()
        if not row:
            continue
        obs = _charger_observations(row)
        if not obs:
            continue
        nom, confiance, candidats = _verdict(obs)
        return _resultat(
            "signature", confiance, nom,
            _dire_signature(typ, valeur, candidats),
            conn, candidats=candidats, signature=valeur,
        )

    # 4 ── Le dossier en cours. Une série consomme en général les bobines d'une
    # même livraison : ce que les autres bobines du dossier ont déclaré est le
    # meilleur pari qui reste.
    if no_dossier:
        lignes = conn.execute(
            """SELECT COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS nom, COUNT(*) n
                 FROM fab_matieres_utilisees fmu
            LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
                WHERE fmu.no_dossier = ?
                  AND COALESCE(sr.fournisseur, fmu.fournisseur_manual) IS NOT NULL
             GROUP BY nom
             ORDER BY n DESC""",
            (no_dossier,),
        ).fetchall()
        obs = {r["nom"]: int(r["n"]) for r in lignes if (r["nom"] or "").strip()}
        if obs:
            nom, _c, candidats = _verdict(obs)
            return _resultat(
                "dossier", "suggere", nom or candidats[0]["nom"],
                "Les autres bobines de ce dossier viennent de ce fournisseur.",
                conn, candidats=candidats,
            )

    return _vide()


def _dire_signature(typ: str, valeur: str, candidats: List[Dict[str, Any]]) -> str:
    """La règle apprise, en français, pour que l'opérateur puisse la contredire.

    Une détection qu'on ne peut pas contester est une détection qu'on subit.
    L'écran affiche donc sur quoi elle repose, et l'opérateur reste libre de
    choisir autre chose.
    """
    total = sum(c["observations"] for c in candidats)
    if typ == "num":
        longueur, _, prefixe = valeur.partition("|")
        forme = "un code de %s chiffres commençant par %s" % (longueur, prefixe)
    elif typ == "gs1":
        forme = "un code GS1 de préfixe entreprise %s" % valeur
    else:
        premier, _, nb = valeur.partition("|")
        forme = "un code en %s parties commençant par %s" % (nb, premier)
    if len(candidats) == 1:
        return "%d bobine(s) %s portaient %s." % (
            total, candidats[0]["nom"], forme)
    liste = ", ".join("%s (%d)" % (c["nom"], c["observations"]) for c in candidats[:4])
    return "%s a déjà désigné plusieurs fournisseurs : %s." % (forme.capitalize(), liste)


# ── Reconstruction ───────────────────────────────────────────────────────────

def reconstruire(conn) -> Dict[str, int]:
    """Rejoue tout l'historique confirmé pour (re)constituer les signatures.

    Utilisée par la migration d'installation, et disponible ensuite pour repartir
    d'une table propre si les règles apprises devaient être remises à plat. Les
    réceptions passent AVANT la production : ce sont les seules identifications
    démontrées, et elles doivent peser en premier dans ce qu'on apprend.
    """
    conn.execute("DELETE FROM bobine_signatures")
    n_rec = n_prod = 0

    for r in conn.execute(
        """SELECT i.code_barre AS code, rc.fournisseur AS nom
             FROM stock_reception_items i
             JOIN stock_receptions rc ON rc.id = i.reception_id
            WHERE rc.fournisseur IS NOT NULL AND trim(rc.fournisseur) <> ''"""
    ).fetchall():
        if apprendre(conn, r["code"], r["nom"]):
            n_rec += 1

    for r in conn.execute(
        """SELECT fmu.code_barre AS code,
                  COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS nom
             FROM fab_matieres_utilisees fmu
        LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
            WHERE COALESCE(sr.fournisseur, fmu.fournisseur_manual) IS NOT NULL"""
    ).fetchall():
        if apprendre(conn, r["code"], r["nom"]):
            n_prod += 1

    total = conn.execute("SELECT COUNT(*) c FROM bobine_signatures").fetchone()["c"]
    return {"receptions": n_rec, "production": n_prod, "signatures": int(total)}
