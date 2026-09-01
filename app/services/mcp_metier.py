"""Outils MCP metier — les chiffres et les objets de MySifa, pas du SQL brut.

Regle de construction, et elle n'a pas d'exception : **ces outils ne calculent
rien**. Ils appellent le code des ecrans (`rapport_dossier`, `dossier_stats`) et
mettent en forme ce qu'il renvoie.

Pourquoi c'est ecrit en gras. Le 01/09/2026, MyRentabilite additionnait
`metrage_reel` — un releve de compteur machine — la ou MyProd calculait un
ecart de compteur : 561 152 286 m contre 154 701 sur le meme dossier. Deux
ecrans, deux chiffres, et personne ne l'avait vu pendant des mois. Un MCP qui
refait ses propres jointures serait simplement le troisieme.

Consequence pratique : quand un chiffre est faux ici, il est faux dans MySifa
aussi. C'est voulu. On corrige a la source, jamais dans cette couche.
"""
from __future__ import annotations

import unicodedata
from datetime import date, datetime
from typing import Any, Optional

from config import CODE_ANNUL_DOS, CODE_DEBUT_DOS, CODE_FIN_DOS
from app.core.database import get_db
from app.services import rapport_dossier as rd
from app.services.mcp_data import ErreurMCP

# Ecrans vers lesquels renvoyer. Un chiffre sans son ecran oblige a chercher a
# la main ce qu'on vient de lire.
ECRAN_RETOUR_PROD = "/prod#retour"
ECRAN_REUNIONS = "/reunions"


# ── Periode ──────────────────────────────────────────────────────────────────

def _jour(valeur: Any, champ: str) -> date:
    try:
        return datetime.strptime(str(valeur).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ErreurMCP(f"{champ} invalide : attendu AAAA-MM-JJ, recu « {valeur} ».")


def _bornes(conn, du: Optional[str], au: Optional[str]) -> dict[str, Any]:
    """Bornes de periode. Sans dates, la derniere journee REELLEMENT travaillee.

    Pas la veille calendaire : un lundi, « hier » est le vendredi ou le samedi.
    C'est la meme regle que le raccourci « Hier » de MyProd, et `rapport_dossier`
    sait deja la resoudre.
    """
    if not du and not au:
        dernier = rd.dernier_jour_saisi(conn)
        if not dernier:
            raise ErreurMCP("Aucune saisie de production en base.")
        d = f = _jour(dernier, "jour")
        defaut = True
    else:
        d = _jour(du or au, "du")
        f = _jour(au or du, "au")
        defaut = False
    if f < d:
        d, f = f, d
    return {
        "debut": f"{d.isoformat()}T00:00:00",
        "fin": f"{f.isoformat()}T23:59:59",
        "du": d.isoformat(),
        "au": f.isoformat(),
        "par_defaut": defaut,
    }


def _cr(conn, no_dossier: str, debut: str = "", fin: str = "") -> dict[str, Any]:
    return rd.compte_rendu(
        conn, no_dossier, code_fin=CODE_FIN_DOS, code_debut=CODE_DEBUT_DOS,
        code_annul=CODE_ANNUL_DOS, debut=debut, fin=fin,
    )


# ── mysifa_metric ────────────────────────────────────────────────────────────

_AVERTISSEMENT_VITESSE = (
    "Deux chiffres, deux denominateurs, et ils ne disent pas la meme chose : "
    "`vitesse_m_min` = metrage / temps de production seul ; `cadence_m_min` = "
    "metrage / (production + arret). La cadence est la seule comparable a "
    "l'historique d'une reference. Aucune des deux ne retire du numerateur la "
    "matiere defilee pendant le calage : le compteur est releve au demarrage du "
    "dossier, pas a la mise en production, donc les deux sont surestimees quand "
    "le calage est long."
)


def metric(dossier: Optional[str] = None, du: Optional[str] = None,
           au: Optional[str] = None, machine: Optional[str] = None) -> dict[str, Any]:
    """Les chiffres de production qui font foi — un dossier, ou une periode."""
    with get_db() as conn:
        if dossier and str(dossier).strip():
            cr = _cr(conn, str(dossier).strip())
            if not cr.get("existe"):
                raise ErreurMCP(f"Aucune saisie pour le dossier « {dossier} ».")
            return {
                "portee": "dossier",
                "dossier": cr["no_dossier"],
                "identite": cr["identite"],
                "metrage": cr["metrage"],
                "temps": cr["temps"],
                "vitesse_m_min": cr["vitesse_m_min"],
                "cadence_m_min": cr["cadence_m_min"],
                "reperes_reference": cr["reperes"],
                "ecarts": cr["ecarts"],
                "vigilance": cr["vigilance"],
                "avertissement": _AVERTISSEMENT_VITESSE,
                "ecran": ECRAN_RETOUR_PROD,
            }

        b = _bornes(conn, du, au)
        atelier = rd.retour_atelier(conn, (machine or "").strip(), b["debut"], b["fin"],
                                    code_fin=CODE_FIN_DOS)
        lignes = rd.comptes_rendus_periode(conn, b["debut"], b["fin"],
                                           machine=(machine or "").strip(),
                                           code_fin=CODE_FIN_DOS, limite=200)
    return {
        "portee": "periode",
        "periode": b,
        "machine": (machine or "") or "toutes",
        "atelier": atelier,
        "dossiers": lignes,
        "avertissement": _AVERTISSEMENT_VITESSE,
        "ecran": ECRAN_RETOUR_PROD,
    }


# ── mysifa_dossier ───────────────────────────────────────────────────────────

def dossier(no_dossier: str) -> dict[str, Any]:
    """Un dossier d'un bloc : saisies, arrets, seuils, ecrits, metrage, reperes."""
    ref = str(no_dossier or "").strip()
    if not ref:
        raise ErreurMCP("Numero de dossier vide.")
    with get_db() as conn:
        cr = _cr(conn, ref)
        if not cr.get("existe"):
            proches = rd.rechercher_dossiers(conn, ref, limite=8, code_fin=CODE_FIN_DOS)
            noms = [p.get("no_dossier") for p in proches if p.get("no_dossier")]
            raise ErreurMCP(
                f"Aucune saisie pour le dossier « {ref} »."
                + (f" Dossiers proches : {', '.join(noms)}." if noms else "")
            )
    cr["ecran"] = ECRAN_RETOUR_PROD
    return cr


# ── mysifa_resolve ───────────────────────────────────────────────────────────

def _sans_accent(txt: Any) -> str:
    """Comparaison a l'aveugle des accents et de la casse.

    Un agent ecrit « cohesio » ; la machine s'appelle « Cohésio 1 ». Le LIKE de
    SQLite ignore la casse mais pas les accents, donc la recherche ne rendait
    rien — et l'agent en concluait que la machine n'existe pas.
    """
    base = unicodedata.normalize("NFD", str(txt or ""))
    return "".join(c for c in base if unicodedata.category(c) != "Mn").lower()


def resolve(terme: str, genre: str = "auto") -> dict[str, Any]:
    """Identifiant canonique d'une entite, a partir d'un terme approximatif.

    Un numero de dossier chez SIFA n'est pas un identifiant propre : il vaut
    « 9932236 (marche 747) », « Reliquat 9932250 + Stock » ou « 9932219 a
    9932290 ». Deviner la forme exacte fait echouer une requete sur deux.
    """
    t = str(terme or "").strip()
    if len(t) < 2:
        raise ErreurMCP("Terme trop court (2 caracteres minimum).")
    g = (genre or "auto").strip().lower()
    out: dict[str, Any] = {"terme": t, "genre": g}

    with get_db() as conn:
        if g in ("auto", "dossier"):
            out["dossiers"] = rd.rechercher_dossiers(conn, t, limite=15,
                                                     code_fin=CODE_FIN_DOS)
        cle = _sans_accent(t)
        if g in ("auto", "machine"):
            # Quatre lignes : le filtre se fait en Python, ou les accents ne
            # comptent pas.
            out["machines"] = [
                dict(r) for r in conn.execute(
                    "SELECT id, nom, code, actif FROM machines ORDER BY nom"
                ).fetchall()
                if cle in _sans_accent(r["nom"]) or cle in _sans_accent(r["code"])
            ]
        if g in ("auto", "produit", "reference"):
            candidats = conn.execute(
                """SELECT DISTINCT no_dossier, client, designation
                     FROM production_data
                    WHERE COALESCE(est_annule,0)=0 AND no_dossier NOT IN ('','0')"""
            ).fetchall()
            out["references"] = [
                dict(r) for r in candidats
                if cle in _sans_accent(r["client"]) or cle in _sans_accent(r["designation"])
            ][:15]
    trouve = sum(len(v) for k, v in out.items() if isinstance(v, list))
    out["total"] = trouve
    if not trouve:
        out["message"] = (f"Rien ne correspond a « {t} ». Essaie un fragment plus "
                          "court, ou le nom du client plutot que le numero.")
    return out


# ── anomalies ────────────────────────────────────────────────────────────────

def anomalies(du: Optional[str] = None, au: Optional[str] = None,
              machine: Optional[str] = None, limite: int = 50) -> dict[str, Any]:
    """Les trous de la periode : ce qui est incomplet, pas ce qui est mauvais.

    La source est `_vigilance` de `rapport_dossier` — la meme liste que l'ecran
    Retour de prod affiche par dossier. On l'agrege sur une periode pour en
    faire une file de travail, sans ecrire une seconde definition de ce qui
    est anormal.
    """
    n = max(1, min(int(limite or 50), 200))
    with get_db() as conn:
        b = _bornes(conn, du, au)
        numeros = rd.dossiers_clotures(conn, b["debut"], b["fin"],
                                       (machine or "").strip(), CODE_FIN_DOS)[:n]
        points: list[dict[str, Any]] = []
        complets = 0
        for no_d in numeros:
            cr = _cr(conn, no_d, debut=b["debut"], fin=b["fin"])
            if not cr.get("existe"):
                continue
            vig = cr.get("vigilance") or []
            if not vig:
                complets += 1
                continue
            for v in vig:
                points.append({
                    "dossier": cr["no_dossier"],
                    "machine": cr["identite"].get("machine"),
                    "client": cr["identite"].get("client"),
                    "date_fin": cr["identite"].get("date_fin"),
                    "cle": v.get("cle"),
                    "constat": v.get("texte"),
                })

    par_type: dict[str, int] = {}
    for p in points:
        par_type[p["cle"]] = par_type.get(p["cle"], 0) + 1
    return {
        "periode": b,
        "machine": (machine or "") or "toutes",
        "dossiers_examines": len(numeros),
        "dossiers_complets": complets,
        "nb_points": len(points),
        "par_type": par_type,
        "points": points,
        "ecran": ECRAN_RETOUR_PROD,
    }
