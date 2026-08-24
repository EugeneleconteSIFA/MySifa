#!/usr/bin/env python3
"""MySifa — le carnet de commandes est-il prévisible ?

Pourquoi ce script existe
─────────────────────────
Prévoir la consommation matière à 3-4 mois ne consiste pas à extrapoler une
courbe. Sur cet horizon, une partie du besoin est DÉJÀ CONNUE : les dossiers
au planning dont la livraison tombe dans la fenêtre. MySifa la calcule
exactement (Besoins matières par échéance). Ce qui reste à estimer, c'est le
REMPLISSAGE : combien un mois va encore gagner de dossiers entre aujourd'hui
et sa réalisation.

Ce remplissage se mesure, il ne se devine pas. `planning_entries.created_at`
dit quand un dossier est entré au carnet, `date_livraison` quand il en sort.
Le croisement des deux donne, pour chaque horizon k, la part du volume final
déjà visible k mois à l'avance — appelons-la p(k).

    prévision(M+k) = besoin_connu(M+k) / p(k)

Tout le modèle tient dans cette ligne. Sa validité tient à p(k) : si les deux
colonnes sont mal renseignées, ou si p(k) est trop dispersé d'un mois à
l'autre, l'approche ne tient pas et il faut le savoir AVANT de construire un
écran qui affiche des chiffres.

Ce script ne prédit rien. Il répond à quatre questions :

  1. Les colonnes nécessaires sont-elles renseignées, et sur quelle période ?
  2. Quelle est la courbe de remplissage p(k), et sa dispersion ?
  3. Combien de références matières ont assez d'historique pour qu'une
     prévision par référence veuille dire quelque chose ?
  4. Le métrage des OF, qui porte tout le calcul, est-il présent dans
     l'historique ou seulement sur les dossiers récents ?

Lecture seule. Aucune écriture, aucune table créée.

Usage
─────
    python scripts/diag_previsions_matieres.py
    python scripts/diag_previsions_matieres.py --db app/data/production-v1.db
    python scripts/diag_previsions_matieres.py --horizons 1,2,3,4,6
"""
import argparse
import os
import sqlite3
import statistics
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _defaut_db() -> str:
    try:
        from config import DB_PATH
        return DB_PATH
    except Exception:
        return os.path.join("data", "production.db")


def _titre(t):
    print("\n" + t)
    print("─" * max(len(t), 60))


def _mois(s):
    """'2026-03-14T…' ou '2026-03-14' → (2026, 3). None si illisible."""
    s = str(s or "").strip()
    if len(s) < 7 or s[4] != "-":
        return None
    try:
        return int(s[:4]), int(s[5:7])
    except ValueError:
        return None


def _delta_mois(a, b) -> int:
    """Nombre de mois de a vers b (tous deux (an, mois))."""
    return (b[0] - a[0]) * 12 + (b[1] - a[1])


def _pct(n, d):
    return f"{(100.0 * n / d):5.1f}%" if d else "    —"


# ── 1. Les colonnes sont-elles là ? ───────────────────────────────────

def diag_colonnes(conn):
    _titre("1. Matière première du modèle : les colonnes sont-elles renseignées ?")
    tot = conn.execute("SELECT COUNT(*) c FROM planning_entries").fetchone()["c"]
    if not tot:
        print("  Aucun dossier au planning — rien à mesurer.")
        return False
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)")}
    manquantes = {"created_at", "date_livraison"} - cols
    if manquantes:
        print(f"  Colonnes absentes : {', '.join(sorted(manquantes))} — approche impossible en l'état.")
        return False

    q = conn.execute(
        """SELECT
             COUNT(*) AS tot,
             SUM(CASE WHEN TRIM(COALESCE(created_at,''))     != '' THEN 1 ELSE 0 END) AS a_cree,
             SUM(CASE WHEN TRIM(COALESCE(date_livraison,'')) != '' THEN 1 ELSE 0 END) AS a_livr,
             SUM(CASE WHEN TRIM(COALESCE(created_at,''))     != ''
                       AND TRIM(COALESCE(date_livraison,'')) != '' THEN 1 ELSE 0 END) AS a_deux,
             MIN(date_livraison) AS livr_min, MAX(date_livraison) AS livr_max,
             MIN(created_at)     AS cree_min, MAX(created_at)     AS cree_max
           FROM planning_entries"""
    ).fetchone()
    print(f"  Dossiers au planning              : {q['tot']}")
    print(f"  avec created_at                   : {q['a_cree']:>6}  {_pct(q['a_cree'], q['tot'])}")
    print(f"  avec date_livraison               : {q['a_livr']:>6}  {_pct(q['a_livr'], q['tot'])}")
    print(f"  avec les DEUX (exploitables)      : {q['a_deux']:>6}  {_pct(q['a_deux'], q['tot'])}")
    print(f"  livraisons de {str(q['livr_min'])[:10]} à {str(q['livr_max'])[:10]}")
    print(f"  créations   de {str(q['cree_min'])[:10]} à {str(q['cree_max'])[:10]}")
    if q["a_deux"] < 200:
        print("\n  ⚠ Moins de 200 dossiers exploitables : la courbe de remplissage")
        print("    sera trop bruitée pour calibrer quoi que ce soit.")
    return q["a_deux"] >= 50


# ── 2. La courbe de remplissage p(k) ──────────────────────────────────

def diag_remplissage(conn, horizons):
    _titre("2. Courbe de remplissage du carnet — p(k)")
    print("  Pour chaque mois de livraison M révolu : quelle part du métrage")
    print("  finalement produit était déjà au carnet k mois avant M ?\n")

    rows = conn.execute(
        """SELECT pe.date_livraison AS livr, pe.created_at AS cree,
                  COALESCE(oi.metrage, 0) AS metrage,
                  COALESCE(oi.qte_etiquettes, 0) AS qte
           FROM planning_entries pe
           LEFT JOIN of_imports oi ON oi.id = pe.of_import_id
           WHERE TRIM(COALESCE(pe.date_livraison,'')) != ''
             AND TRIM(COALESCE(pe.created_at,'')) != ''"""
    ).fetchall()

    # Poids : le métrage si on l'a, sinon le dossier compte pour 1. Un carnet
    # dont on ne connaît que le nombre de dossiers reste informatif.
    par_mois_total = defaultdict(float)
    par_mois_avant = defaultdict(lambda: defaultdict(float))
    aujourdhui = (date.today().year, date.today().month)
    sans_metrage = 0

    for r in rows:
        ml, mc = _mois(r["livr"]), _mois(r["cree"])
        if not ml or not mc:
            continue
        if _delta_mois(ml, aujourdhui) < 1:
            continue  # mois non révolu : son volume final n'est pas connu
        poids = float(r["metrage"] or 0)
        if poids <= 0:
            poids = 1.0
            sans_metrage += 1
        par_mois_total[ml] += poids
        avance = _delta_mois(mc, ml)  # mois d'avance à la création
        for k in horizons:
            if avance >= k:
                par_mois_avant[ml][k] += poids

    mois_ok = sorted(m for m, v in par_mois_total.items() if v > 0)
    if len(mois_ok) < 6:
        print(f"  Seulement {len(mois_ok)} mois révolus exploitables — insuffisant.")
        return None
    print(f"  {len(mois_ok)} mois révolus, de {mois_ok[0][0]}-{mois_ok[0][1]:02d} "
          f"à {mois_ok[-1][0]}-{mois_ok[-1][1]:02d}")
    print(f"  ({sans_metrage} dossiers sans métrage OF, comptés à l'unité)\n")

    print("   k   p(k) médian   écart-type   min     max    lecture")
    print("  ─────────────────────────────────────────────────────────────────")
    calib = {}
    for k in horizons:
        parts = [par_mois_avant[m][k] / par_mois_total[m] for m in mois_ok
                 if par_mois_total[m] > 0]
        if len(parts) < 4:
            continue
        med = statistics.median(parts)
        sd = statistics.pstdev(parts) if len(parts) > 1 else 0.0
        calib[k] = {"p": med, "sd": sd, "n": len(parts)}
        if med <= 0.02:
            avis = "carnet vide à cet horizon"
        elif sd > 0.20:
            avis = "trop dispersé — inexploitable seul"
        elif sd > 0.12:
            avis = "utilisable avec une large fourchette"
        else:
            avis = "exploitable"
        print(f"  {k:2}   {med:8.1%}     {sd:7.1%}   {min(parts):5.0%}  {max(parts):5.0%}   {avis}")

    print("\n  Lecture : p(3) = 60 % signifie qu'à 3 mois d'échéance le carnet")
    print("  contient 60 % du volume final. La prévision est alors le besoin")
    print("  connu divisé par 0,60 — et l'écart-type donne la fourchette.")
    return calib


# ── 3. Assez d'historique par référence ? ─────────────────────────────

def diag_references(conn):
    _titre("3. Prévision PAR RÉFÉRENCE : combien tiennent debout ?")
    try:
        rows = conn.execute(
            """SELECT mp.id, mp.reference, mp.designation, mp.categorie,
                      COUNT(DISTINCT SUBSTR(pe.date_livraison, 1, 7)) AS mois,
                      COUNT(*) AS dossiers
               FROM mp_fiche_mapping m
               JOIN matieres_premieres mp ON mp.id = m.matiere_id
               JOIN fiches_techniques ft
                 ON LOWER(TRIM(COALESCE(ft.support,''))) = LOWER(TRIM(m.source_value))
                 OR LOWER(TRIM(COALESCE(ft.glassine,''))) = LOWER(TRIM(m.source_value))
                 OR LOWER(TRIM(COALESCE(ft.adhesif,'')))  = LOWER(TRIM(m.source_value))
               JOIN planning_entries pe
                 ON pe.ref_produit_norm = ft.ref_produit_norm
               WHERE TRIM(COALESCE(pe.date_livraison,'')) != ''
               GROUP BY mp.id
               ORDER BY mois DESC, dossiers DESC"""
        ).fetchall()
    except Exception as exc:
        print(f"  Requête impossible sur cette base : {exc}")
        return

    if not rows:
        print("  Aucune matière rattachée à un dossier — mp_fiche_mapping est-il rempli ?")
        return

    seuils = [(24, "solide"), (12, "indicatif"), (6, "fragile"), (0, "insuffisant")]
    par_niveau = defaultdict(list)
    for r in rows:
        for s, lab in seuils:
            if r["mois"] >= s:
                par_niveau[lab].append(r)
                break

    total_map = conn.execute("SELECT COUNT(DISTINCT matiere_id) c FROM mp_fiche_mapping").fetchone()["c"]
    print(f"  {total_map} matières associées dans mp_fiche_mapping, "
          f"{len(rows)} effectivement vues sur un dossier.\n")
    for _, lab in seuils:
        n = len(par_niveau[lab])
        print(f"  {lab:12} ({n:3} réf.)", end="")
        if n:
            ex = ", ".join((r["reference"] or r["designation"] or "?")[:18]
                           for r in par_niveau[lab][:3])
            print(f"  ex. {ex}")
        else:
            print()
    print("\n  Seules les références « solide » et « indicatif » méritent une")
    print("  prévision chiffrée. Les autres doivent afficher leur incertitude,")
    print("  sinon l'écran invente un chiffre que personne ne pourra contredire.")


# ── 4. Le métrage est-il présent dans l'historique ? ──────────────────

def diag_metrage(conn):
    _titre("4. Métrage des OF — le calcul repose dessus")
    rows = conn.execute(
        """SELECT SUBSTR(pe.date_livraison, 1, 4) AS an,
                  COUNT(*) AS n,
                  SUM(CASE WHEN COALESCE(oi.metrage,0) > 0 THEN 1 ELSE 0 END) AS avec
           FROM planning_entries pe
           LEFT JOIN of_imports oi ON oi.id = pe.of_import_id
           WHERE TRIM(COALESCE(pe.date_livraison,'')) != ''
           GROUP BY an ORDER BY an"""
    ).fetchall()
    print("   année   dossiers   avec métrage")
    for r in rows:
        if not r["an"]:
            continue
        print(f"   {r['an']}    {r['n']:6}       {_pct(r['avec'], r['n'])}")
    print("\n  Un métrage absent sur les années anciennes n'interdit pas le modèle")
    print("  (le remplissage se mesure aussi en nombre de dossiers), mais il")
    print("  restreint la calibration en volume aux années bien renseignées.")


# ── 5. Qui documente les mois passés ? ────────────────────────────────
#
# La vue Tendance affiche douze mois révolus. Deux sources peuvent les
# documenter : les dossiers encore présents au planning, et les OF scannés
# qu'aucun dossier ne porte plus. Quand les deux sont muettes, le mois est
# hachuré — un trou, pas un zéro. Quand elles parlent mais que le besoin
# n'est pas chiffrable, le mois s'affiche à plat, ce qui se lit à tort comme
# une activité nulle. Cette section distingue les deux cas, mois par mois.

def _mois_de(s):
    """'2026-03-14…' ou '14/03/2026' → '2026-03'. None si illisible."""
    s = str(s or "").strip()
    if len(s) >= 7 and s[4] == "-" and s[:4].isdigit() and s[5:7].isdigit():
        return s[:7]
    # Formats français d'Access : JJ/MM/AAAA ou JJ-MM-AAAA.
    for sep in ("/", "-"):
        p = s.split(" ")[0].split(sep)
        if len(p) == 3 and len(p[2]) == 4 and p[2].isdigit() and p[1].isdigit():
            return f"{int(p[2]):04d}-{int(p[1]):02d}"
    return None


def _fenetre_mois(n_passes=12, n_futurs=5):
    auj = date.today()
    an, mo = auj.year, auj.month - n_passes
    an += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    out = []
    for _ in range(n_passes + 1 + n_futurs):
        out.append(f"{an:04d}-{mo:02d}")
        mo += 1
        if mo > 12:
            mo, an = 1, an + 1
    return out


def diag_sources_passe(conn):
    _titre("5. Vue Tendance — qui documente chaque mois de la fenêtre ?")

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None
        print("  (fiche_ref_parser indisponible : le rapprochement OF↔fiche")
        print("   ne sera pas mesuré — lancer le script depuis la racine du projet.)\n")

    # Les clés de fiche technique, telles que `_load_dossiers` les indexe.
    cles_fiches = set()
    for r in conn.execute(
        "SELECT ref_produit_norm, reference FROM fiches_techniques"
    ).fetchall():
        n = (r["ref_produit_norm"] or "").strip()
        cles_fiches.add(n if n else (r["reference"] or "").strip().lower())
    cles_fiches.discard("")

    fenetre = _fenetre_mois()
    courant = f"{date.today().year:04d}-{date.today().month:02d}"

    # ── Source A : le planning, tous statuts ──
    pe_par_mois = defaultdict(lambda: {"n": 0, "chiffrable": 0})
    for r in conn.execute(
        """SELECT pe.date_livraison, pe.planned_end, pe.planned_start,
                  COALESCE(oi.metrage, 0)        AS metrage,
                  COALESCE(oi.qte_etiquettes, 0) AS qte
           FROM planning_entries pe
           LEFT JOIN of_imports oi ON oi.id = pe.of_import_id"""
    ).fetchall():
        m = (_mois_de(r["date_livraison"]) or _mois_de(r["planned_end"])
             or _mois_de(r["planned_start"]))
        if not m:
            continue
        c = pe_par_mois[m]
        c["n"] += 1
        if r["metrage"] > 0 or r["qte"] > 0:
            c["chiffrable"] += 1

    # ── Source B : les OF qu'aucun dossier du planning ne porte ──
    # `propres` : l'OF nomme lui-même sa matière (of_imports.matiere /
    # .glassine / .adhesif_label, recopiées de la fiche Access à sa création).
    # C'est ce que la vue Tendance exploite pour l'archive — comparer cette
    # colonne à `fiche` dit ce que le rapprochement de fiche fait perdre.
    cols_of = {r["name"] for r in conn.execute("PRAGMA table_info(of_imports)")}
    a_mat = "matiere" in cols_of
    sel_mat = ("COALESCE(oi.matiere,'') AS matiere, "
               "COALESCE(oi.glassine,'') AS glassine, "
               "COALESCE(oi.adhesif_label,'') AS adhesif_label, "
               if a_mat else
               "'' AS matiere, '' AS glassine, '' AS adhesif_label, ")

    of_par_mois = defaultdict(
        lambda: {"n": 0, "fiche": 0, "propres": 0, "chiffrable": 0})
    of_total = of_orph = of_sans_date = 0
    for r in conn.execute(
        f"""SELECT oi.id, oi.reference, oi.delai_client, oi.date_creation,
                   {sel_mat}
                   COALESCE(oi.metrage, 0)        AS metrage,
                   COALESCE(oi.qte_etiquettes, 0) AS qte,
                   (SELECT COUNT(*) FROM planning_entries pe
                     WHERE pe.of_import_id = oi.id) AS n_pe
            FROM of_imports oi"""
    ).fetchall():
        of_total += 1
        if r["n_pe"]:
            continue  # porté par le planning : compté en source A, pas ici
        of_orph += 1
        m = _mois_de(r["delai_client"]) or _mois_de(r["date_creation"])
        if not m:
            of_sans_date += 1
            continue
        c = of_par_mois[m]
        c["n"] += 1
        if normalize_ref_produit:
            k = normalize_ref_produit(r["reference"]) \
                or (r["reference"] or "").strip().lower()
            if k in cles_fiches:
                c["fiche"] += 1
        if (r["matiere"].strip() or r["glassine"].strip()
                or r["adhesif_label"].strip()):
            c["propres"] += 1
        if r["metrage"] > 0 or r["qte"] > 0:
            c["chiffrable"] += 1

    print(f"  {of_total} OF scannés au total, dont {of_orph} qu'aucun dossier du")
    print(f"  planning ne porte ({of_sans_date} sans date exploitable).\n")
    if not a_mat:
        print("  ⚠ of_imports n'a pas de colonne `matiere` : la colonne « propres »")
        print("    restera vide et l'archive dépendra du rapprochement de fiche.\n")

    print("   mois      PLANNING             OF ORPHELINS                     verdict")
    print("             dossiers chiffr.    OF  fiche  propres  chiffr.")
    print("  ─────────────────────────────────────────────────────────────────────────")
    trous = plats = 0
    for m in fenetre:
        a = pe_par_mois.get(m, {"n": 0, "chiffrable": 0})
        b = of_par_mois.get(m, {"n": 0, "fiche": 0, "propres": 0, "chiffrable": 0})
        # Un OF pèse s'il nomme sa matière (par lui-même OU via une fiche) ET
        # qu'il porte de quoi la chiffrer.
        nomme = max(b["fiche"], b["propres"])
        chiffrable = a["chiffrable"] + min(nomme, b["chiffrable"])
        if a["n"] + b["n"] == 0:
            verdict = "TROU — hachuré à l'écran"
            trous += 1
        elif chiffrable == 0:
            verdict = "PLAT — des dossiers, aucun chiffre"
            plats += 1
        elif chiffrable < (a["n"] + b["n"]) * 0.5:
            verdict = "partiel — moins de la moitié chiffrée"
        else:
            verdict = "ok"
        marque = " <" if m == courant else "  "
        print(f"  {m}{marque} {a['n']:7} {a['chiffrable']:7}   {b['n']:5} {b['fiche']:6} "
              f"{b['propres']:7}  {b['chiffrable']:7}   {verdict}")

    print()
    if trous:
        print(f"  {trous} mois sans aucune source. Si ce sont des mois anciens, c'est")
        print("  attendu : ni le planning ni les OF ne remontent aussi loin.")
    if plats:
        print(f"  {plats} mois documentés mais non chiffrables — c'est CE cas qui")
        print("  fabrique une courbe à plat qu'on lira comme une activité nulle.")

    tot_of = sum(c["n"] for c in of_par_mois.values())
    tot_fi = sum(c["fiche"] for c in of_par_mois.values())
    tot_pr = sum(c["propres"] for c in of_par_mois.values())
    if normalize_ref_produit:
        print(f"\n  OF orphelins nommant leur matière :")
        print(f"    via une fiche technique   {tot_fi:5}/{tot_of} "
              f"({_pct(tot_fi, tot_of).strip()})")
        print(f"    par leurs propres champs  {tot_pr:5}/{tot_of} "
              f"({_pct(tot_pr, tot_of).strip()})")
        if tot_pr > tot_fi:
            print("\n  L'écart est l'enjeu : `fiches_techniques` ne garde que les produits")
            print("  actifs, alors que l'OF a recopié sa matière à sa création. Lire l'OF")
            print("  plutôt que de lui chercher une fiche récupère la différence.")
        elif tot_pr == 0:
            print("\n  Les OF ne portent pas leurs matières : l'archive dépend entièrement")
            print("  du rapprochement de fiche, et il faudra le réparer là.")


# ── 6. Que contiennent RÉELLEMENT les OF archivés ? ───────────────────
#
# La section 5 dit que les OF anciens ne nomment leur matière ni par une fiche
# technique, ni par leurs propres champs. Reste à savoir ce qu'ils portent : un
# OF qui a son métrage et sa quantité mais aucune matière n'est pas la même
# situation qu'un OF vide, et n'appelle pas la même réparation.
#
# Deux cohortes, séparées par un mois pivot, parce que les OF n'ont pas tous
# été chargés par le même chemin : la synchro Access remplit `matiere` /
# `glassine` / `adhesif_label`, les reprises plus anciennes non.

def diag_contenu_of(conn, pivot="2026-06"):
    _titre(f"6. Contenu réel des OF que le planning ne porte plus (pivot {pivot})")

    cols = [r["name"] for r in conn.execute("PRAGMA table_info(of_imports)")]
    if not cols:
        print("  Table of_imports absente.")
        return

    lignes = conn.execute(
        "SELECT oi.* , (SELECT COUNT(*) FROM planning_entries pe "
        "               WHERE pe.of_import_id = oi.id) AS n_pe "
        "FROM of_imports oi"
    ).fetchall()

    anciens, recents = [], []
    for r in lignes:
        if r["n_pe"]:
            continue
        m = _mois_de(r["delai_client"]) or _mois_de(r["date_creation"])
        if not m:
            continue
        (anciens if m < pivot else recents).append(r)

    print(f"  {len(anciens)} OF orphelins avant {pivot}, {len(recents)} après.\n")
    if not anciens and not recents:
        return

    def _rempli(v):
        if v is None:
            return False
        if isinstance(v, str):
            return bool(v.strip())
        return v != 0

    print("   colonne                    avant pivot   après pivot")
    print("  ──────────────────────────────────────────────────────")
    for c in cols:
        if c in ("id", "n_pe"):
            continue
        a = sum(1 for r in anciens if _rempli(r[c]))
        b = sum(1 for r in recents if _rempli(r[c]))
        if not a and not b:
            continue  # colonne vide partout : ne dit rien, n'encombre pas
        print(f"   {c:26} {_pct(a, len(anciens))}      {_pct(b, len(recents))}")

    # Pourquoi la fiche ne se trouve pas : référence illisible, ou fiche absente ?
    # Les deux se réparent très différemment, et rien d'autre ne les distingue.
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    if normalize_ref_produit and anciens:
        cles = set()
        for r in conn.execute("SELECT ref_produit_norm FROM fiches_techniques"):
            if (r["ref_produit_norm"] or "").strip():
                cles.add(r["ref_produit_norm"].strip())
        sans_ref = illisible = absente = trouvee = 0
        exemples = []
        for r in anciens:
            ref = (r["reference"] or "").strip()
            if not ref:
                sans_ref += 1
                continue
            k = normalize_ref_produit(ref)
            if not k:
                illisible += 1
                if len(exemples) < 6:
                    exemples.append((ref, "référence non normalisable"))
            elif k in cles:
                trouvee += 1
            else:
                absente += 1
                if len(exemples) < 6:
                    exemples.append((ref, f"normalisée en {k}, aucune fiche"))

        print(f"\n  Pourquoi la fiche manque, sur les {len(anciens)} OF anciens :")
        print(f"    référence absente            {sans_ref:5}")
        print(f"    référence non normalisable   {illisible:5}")
        print(f"    normalisée mais fiche absente{absente:6}")
        print(f"    fiche trouvée                {trouvee:5}")
        if exemples:
            print("\n  Exemples :")
            for ref, pourquoi in exemples:
                print(f"    {ref[:40]:42} {pourquoi}")
        print("\n  « fiche absente » se répare en important les fiches anciennes ;")
        print("  « non normalisable » se répare dans le parser. Ce ne sont pas")
        print("  les mêmes travaux, et l'un des deux peut être inutile.")

    # À quoi ressemble un OF ancien, concrètement.
    if anciens:
        print("\n  Trois OF anciens, champs non vides :")
        for r in anciens[:3]:
            dispo = set(r.keys())
            plein = {c: r[c] for c in cols
                     if c != "id" and c in dispo and _rempli(r[c])}
            nom = r["of_numero"] if "of_numero" in dispo else "?"
            print(f"\n    OF {nom} — {len(plein)} champ(s) renseigné(s)")
            for c, v in list(plein.items())[:14]:
                print(f"      {c:22} {str(v)[:44]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=_defaut_db())
    ap.add_argument("--horizons", default="1,2,3,4,5,6")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"Base introuvable : {args.db}")
        return 2
    horizons = [int(x) for x in args.horizons.split(",") if x.strip().isdigit()]

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    print(f"Base : {args.db}  (lecture seule)")

    if diag_colonnes(conn):
        calib = diag_remplissage(conn, horizons)
    else:
        calib = None
    diag_references(conn)
    diag_metrage(conn)
    try:
        diag_sources_passe(conn)
    except Exception as exc:
        print(f"\n5. Sources des mois passés — impossible sur cette base : {exc}")
    try:
        diag_contenu_of(conn)
    except Exception as exc:
        print(f"\n6. Contenu des OF — impossible sur cette base : {exc}")

    _titre("Verdict")
    if not calib:
        print("  La courbe de remplissage n'est pas mesurable sur cette base.")
        print("  Le modèle « besoin connu ÷ p(k) » ne tient pas — il faudra")
        print("  se rabattre sur une moyenne historique par matière, beaucoup")
        print("  moins précise, et le dire clairement dans l'écran.")
    else:
        exploitables = [k for k, v in calib.items() if v["sd"] <= 0.20 and v["p"] > 0.02]
        if exploitables:
            print(f"  Horizons exploitables : M+{', M+'.join(map(str, exploitables))}.")
            print("  Le modèle « besoin connu ÷ p(k) » peut être calibré.")
        else:
            print("  Aucun horizon assez stable. Le carnet se remplit trop")
            print("  irrégulièrement pour qu'un coefficient unique le décrive.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
