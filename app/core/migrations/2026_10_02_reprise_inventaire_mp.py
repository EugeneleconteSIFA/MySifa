"""
Reprise de l'inventaire physique du 01/10/2026 dans MyStock (matières et consommables).

Données : `donnees/reprise_inventaire_mp_2026_10_01.json`, produit depuis le
tableau de correspondance validé par Eugène le 02/10/2026 (inventaire master
table v7 + fiches articles et achats RVGI). Toute la logique, et ses règles,
vivent dans `app/services/reprise_inventaire_mp.py`.

Ce que la reprise écrit :
- fiches reprises (libellé commercial, ancienne désignation gardée dans
  `mp_fiche_mapping`), fiches créées, doublons ramenés à zéro et désactivés ;
- stock par laize = compté au 01/10 + mouvements enregistrés depuis, tracé
  comme un inventaire MyStock (mouvement + ligne `inventaires_matieres`) ;
- non-conformités hors stock disponible, portées par leurs emplacements ;
- emplacements du terrain ;
- variantes fournisseur et fournisseur principal (partagé avec Coûts matières).

Le rapport complet est gardé dans `stock_config` (clé ci-dessous).
"""

import json
import os

NOM = "reprise_inventaire_mp_2026_10_01"
DEPEND = ["mp_variantes_fournisseur", "mp_emplacements"]
CLE_RAPPORT = "reprise_inventaire_2026_10_01_rapport"


def _fichier() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees",
                        "reprise_inventaire_mp_2026_10_01.json")


def _base_sifa(conn, data) -> bool:
    """La reprise ne vaut que pour la base dont l'inventaire est tiré.

    Une base de test, une instance neuve ou une copie locale vide passent aussi
    par les migrations : y créer les fiches de SIFA serait une donnée métier
    écrite en dur. On reconnaît la base à ses fiches : l'id ET la désignation
    relevée le 02/10/2026 (ou déjà le nouveau libellé) doivent concorder pour
    l'essentiel des fiches reprises.
    """
    attendues = [f for f in data["fiches"] if f.get("id") and f.get("designation_avant")]
    if not attendues:
        return False
    ok = 0
    for f in attendues:
        r = conn.execute("SELECT designation FROM matieres_premieres WHERE id=?", (f["id"],)).fetchone()
        if r and (r[0] or "").strip() in ((f["designation_avant"] or "").strip(), f["designation"]):
            ok += 1
    return ok >= 0.8 * len(attendues)


def appliquer(conn):
    from app.services import reprise_inventaire_mp as reprise

    with open(_fichier(), encoding="utf-8") as fh:
        data = json.load(fh)
    if not _base_sifa(conn, data):
        print(f"[MySifa] migration {NOM} : base sans les fiches de l'inventaire SIFA — reprise ignorée.")
        return
    rapport = reprise.appliquer(conn, data)
    conn.execute(
        """INSERT INTO stock_config (cle, valeur) VALUES (?, ?)
           ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur""",
        (CLE_RAPPORT, json.dumps(rapport, ensure_ascii=False, default=str)),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {reprise.resume(rapport)}")
