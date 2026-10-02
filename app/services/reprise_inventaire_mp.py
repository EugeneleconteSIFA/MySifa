"""Reprise de l'inventaire physique des matières dans MyStock.

Entrée : un fichier de données produit depuis le tableau de correspondance validé
(fiches, variantes fournisseur, stock par laize et emplacement). Voir la
migration `reprise_inventaire_mp_2026_10_01`.

Principes, dans l'ordre où ils s'appliquent :

1. Les fiches gardent leur id. Une fiche reprise prend le libellé commercial ;
   son ancienne désignation est ajoutée à `mp_fiche_mapping`, pour que Besoins
   matières retrouve encore les OF et fiches techniques qui la citent. Une fiche
   à créer l'est avec le libellé commercial comme référence.
2. Le stock suit l'inventaire de MyStock, ligne par ligne : mouvement
   `ajustement` toujours tracé, ligne `inventaires_matieres`, zones magasin /
   production. La quantité appliquée est le COMPTÉ du 01/10 plus les mouvements
   enregistrés depuis : la production des jours suivants n'est pas effacée.
3. Les non-conformités restent hors stock disponible : elles ne sont portées
   que par leurs emplacements (NC GH, NC KL).
4. Une laize que la fiche connaissait et que l'inventaire n'a pas trouvée est
   remise à zéro : l'inventaire est exhaustif.
5. Les fiches doublons sont ramenées à zéro puis désactivées, jamais supprimées.
6. Les emplacements de la fiche sont remplacés par ceux du terrain.
7. Les variantes fournisseur sont créées (ou complètent une variante
   provisoire) par `mp_variantes.creer`, et le principal choisi est posé par
   `definir_principal` — donc partagé avec Coûts matières.

`appliquer` ne commite pas : l'appelant décide (migration, ou simulation qui
annule). Le rapport dit tout ce qui a été tranché ou laissé de côté.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

AUTEUR = "Reprise inventaire 01/10/2026"
MARQUE = "Inventaire physique du 01/10/2026"
_LAIZEES = {"frontal", "glassine", "complexe"}
_KIND = {"frontal": "support", "complexe": "support", "glassine": "glassine", "adhesif": "adhesif",
         "carton": "carton", "mandrin": "mandrin", "palette": "palette"}
_UNITE = {"frontal": "bobines", "glassine": "bobines", "complexe": "bobines", "adhesif": "kg",
          "carton": "palettes", "mandrin": "palettes", "palette": "palettes"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _code_emplacement(code: str) -> str:
    """Nom du terrain, en majuscules, 20 caractères au plus (« COHÉSIO 1 (SORTI…) » -> « COHÉSIO 1 »)."""
    c = " ".join(str(code or "").upper().split())
    if len(c) > 20 and " (" in c:
        c = c.split(" (")[0]
    return c[:20]


def _laize_id(conn: sqlite3.Connection, valeur_mm: float, rapport: dict) -> int:
    r = conn.execute(
        "SELECT id FROM mp_laizes WHERE ABS(valeur_mm - ?) <= 0.5 ORDER BY ABS(valeur_mm - ?) LIMIT 1",
        (valeur_mm, valeur_mm),
    ).fetchone()
    if r:
        return int(r["id"])
    rapport["laizes_creees"].append(valeur_mm)
    return int(conn.execute(
        "INSERT INTO mp_laizes (valeur_mm, label, ordre, actif, created_at) VALUES (?,?,?,1,?)",
        (valeur_mm, "%g mm" % valeur_mm, int(valeur_mm), _now()),
    ).lastrowid)


def _resoudre_fiches(conn, data, rapport) -> dict[str, dict]:
    """cle -> {id, categorie, laizee, action}. Crée les fiches neuves, met à jour les reprises."""
    out: dict[str, dict] = {}
    for f in data["fiches"]:
        cle, cat = f["cle"], f["categorie"]
        if f["id"]:
            row = conn.execute("SELECT * FROM matieres_premieres WHERE id=?", (f["id"],)).fetchone()
            if not row:
                rapport["erreurs"].append("Fiche %s introuvable : ignorée." % f["id"])
                continue
            mid = int(row["id"])
            sets, vals = [], []
            if f["action"] in ("Reprendre", "Stock à zéro") and f["designation"] and f["designation"] != row["designation"]:
                ancienne = (row["designation"] or "").strip()
                if ancienne:
                    conn.execute(
                        """INSERT OR IGNORE INTO mp_fiche_mapping (kind, source_value, matiere_id, notes)
                           VALUES (?,?,?,?)""",
                        (_KIND.get(cat, "support"), ancienne, mid, "Ancienne désignation — " + AUTEUR),
                    )
                sets.append("designation=?"); vals.append(f["designation"])
                rapport["fiches_renommees"].append((mid, ancienne, f["designation"]))
            if f["action"] == "Reprendre" and (row["categorie"] != cat or (row["sous_section"] or None) != (f["sous_section"] or None)):
                conflit = conn.execute(
                    "SELECT id FROM matieres_premieres WHERE categorie=? AND reference=? AND id<>?",
                    (cat, row["reference"], mid),
                ).fetchone()
                if conflit:
                    rapport["erreurs"].append("Fiche %d : reclassement en %s impossible (référence en double)." % (mid, cat))
                else:
                    sets += ["categorie=?", "sous_section=?"]; vals += [cat, f["sous_section"]]
            if f["ml_std"] and not (row["metres_lineaires_par_bobine"] or 0):
                sets.append("metres_lineaires_par_bobine=?"); vals.append(f["ml_std"])
            if f["unites_par_palette"] and not (row["unites_par_palette"] or 0):
                sets.append("unites_par_palette=?"); vals.append(f["unites_par_palette"])
            if sets:
                sets.append("updated_at=?"); vals.append(_now())
                conn.execute("UPDATE matieres_premieres SET %s WHERE id=?" % ", ".join(sets), vals + [mid])
        else:
            ref = f["designation"]
            row = conn.execute(
                "SELECT id FROM matieres_premieres WHERE categorie=? AND reference=?", (cat, ref)
            ).fetchone()
            if row:
                mid = int(row["id"])
                conn.execute("UPDATE matieres_premieres SET actif=1 WHERE id=?", (mid,))
            else:
                mid = int(conn.execute(
                    """INSERT INTO matieres_premieres
                           (categorie, reference, designation, sous_section, actif, is_europe, prix_par_laize,
                            suivi_bobine, metres_lineaires_par_bobine, unites_par_palette, created_at, updated_at)
                       VALUES (?,?,?,?,1,0,0,0,?,?,?,?)""",
                    (cat, ref, f["designation"], f["sous_section"], f["ml_std"], f["unites_par_palette"],
                     _now(), _now()),
                ).lastrowid)
                conn.execute("INSERT OR IGNORE INTO mp_stock (matiere_id, quantite) VALUES (?, 0)", (mid,))
                rapport["fiches_creees"].append((mid, cat, ref))
        out[cle] = {"id": mid, "categorie": cat, "laizee": cat in _LAIZEES, "action": f["action"]}
    return out


def _delta_depuis(conn, mid: int, laize_id: Optional[int], depuis: str) -> float:
    """Mouvements enregistrés depuis le jour de l'inventaire (hors cette reprise)."""
    lz = "laize_id = ?" if laize_id is not None else "laize_id IS NULL"
    params: list[Any] = [mid] + ([laize_id] if laize_id is not None else []) + [depuis, MARQUE + "%"]
    r = conn.execute(
        f"""SELECT COALESCE(SUM(CASE
                   WHEN quantite_apres IS NOT NULL AND quantite_avant IS NOT NULL THEN quantite_apres - quantite_avant
                   WHEN type_mouvement = 'entree' THEN quantite
                   WHEN type_mouvement = 'sortie' THEN -quantite
                   ELSE 0 END), 0)
              FROM mp_mouvements
             WHERE matiere_id = ? AND {lz} AND created_at >= ? AND COALESCE(note,'') NOT LIKE ?""",
        params,
    ).fetchone()
    return float(r[0] or 0)


def _ecrire_stock(conn, mid: int, cat: str, laize_id: Optional[int], q_new: float,
                  q_mag: Optional[float], q_prod: Optional[float], commentaire: str) -> tuple[float, float]:
    if laize_id is not None:
        r = conn.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=? AND laize_id=?", (mid, laize_id)).fetchone()
    else:
        r = conn.execute("SELECT quantite FROM mp_stock WHERE matiere_id=?", (mid,)).fetchone()
    q_avant = float(r["quantite"]) if r and r["quantite"] is not None else 0.0
    ecart = q_new - q_avant
    if laize_id is not None:
        conn.execute(
            """INSERT INTO mp_stock_laize (matiere_id, laize_id, quantite, updated_at, updated_by_name,
                                           quantite_magasin, quantite_production)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(matiere_id, laize_id) DO UPDATE SET
                   quantite=excluded.quantite, updated_at=excluded.updated_at,
                   updated_by_name=excluded.updated_by_name,
                   quantite_magasin=excluded.quantite_magasin, quantite_production=excluded.quantite_production""",
            (mid, laize_id, q_new, _now(), AUTEUR, q_mag, q_prod),
        )
        total = conn.execute("SELECT COALESCE(SUM(quantite),0) FROM mp_stock_laize WHERE matiere_id=?", (mid,)).fetchone()[0]
        if conn.execute("SELECT 1 FROM mp_stock WHERE matiere_id=?", (mid,)).fetchone():
            conn.execute("UPDATE mp_stock SET quantite=?, updated_at=?, updated_by_name=? WHERE matiere_id=?",
                         (float(total), _now(), AUTEUR, mid))
        else:
            conn.execute("INSERT INTO mp_stock (matiere_id, quantite, updated_at, updated_by_name) VALUES (?,?,?,?)",
                         (mid, float(total), _now(), AUTEUR))
    else:
        if conn.execute("SELECT 1 FROM mp_stock WHERE matiere_id=?", (mid,)).fetchone():
            conn.execute(
                """UPDATE mp_stock SET quantite=?, updated_at=?, updated_by_name=?,
                       quantite_magasin=?, quantite_production=? WHERE matiere_id=?""",
                (q_new, _now(), AUTEUR, q_mag, q_prod, mid))
        else:
            conn.execute(
                """INSERT INTO mp_stock (matiere_id, quantite, updated_at, updated_by_name,
                                         quantite_magasin, quantite_production) VALUES (?,?,?,?,?,?)""",
                (mid, q_new, _now(), AUTEUR, q_mag, q_prod))
    sign = "+" if ecart > 0 else ""
    note = "%s — reprise — écart : %s%s %s" % (
        MARQUE, sign, ("%g" % round(ecart, 3)), _UNITE.get(cat, ""))
    if commentaire:
        note += " | " + commentaire
    mvt = conn.execute(
        """INSERT INTO mp_mouvements (matiere_id, type_mouvement, quantite, quantite_avant, quantite_apres,
                                      note, created_at, created_by_name, laize_id)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (mid, "ajustement", abs(ecart), q_avant, q_new, note, _now(), AUTEUR, laize_id),
    ).lastrowid
    conn.execute(
        """INSERT INTO inventaires_matieres (matiere_id, laize_id, quantite_avant, quantite_comptee, ecart,
                                             commentaire, operateur_nom, date_validation, mouvement_id,
                                             quantite_magasin, quantite_production)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (mid, laize_id, q_avant, q_new, ecart, commentaire or None, AUTEUR, _now(), mvt, q_mag, q_prod),
    )
    return q_avant, ecart


def appliquer(conn: sqlite3.Connection, data: dict) -> dict:
    from app.services import mp_variantes as mv

    depuis = data.get("date_inventaire", "2026-10-01") + "T00:00:00"
    rapport: dict[str, Any] = defaultdict(list)
    fiches = _resoudre_fiches(conn, data, rapport)

    # --- stock compté par (fiche, laize)
    compte: dict[tuple, dict] = {}
    emplacements: dict[tuple, float] = defaultdict(float)
    for s in data["stock"]:
        fi = fiches.get(s["cle"])
        if not fi:
            continue
        mid, cat = fi["id"], fi["categorie"]
        lid = _laize_id(conn, s["laize_mm"], rapport) if (fi["laizee"] and s["laize_mm"]) else None
        if fi["laizee"] and lid is None:
            rapport["erreurs"].append("Fiche %d : ligne sans laize ignorée (%s)." % (mid, s["emplacement"]))
            continue
        if lid is not None:
            conn.execute("INSERT OR IGNORE INTO mp_matiere_laizes (matiere_id, laize_id) VALUES (?,?)", (mid, lid))
        k = (mid, lid)
        c = compte.setdefault(k, {"cat": cat, "mag": 0.0, "prod": 0.0, "nc": 0.0, "inconnu": 0})
        q = s["quantite"]
        if q is None:
            c["inconnu"] += 1
            continue
        if s["zone"] == "non_conforme":
            c["nc"] += q
        elif s["zone"] == "production":
            c["prod"] += q
        else:
            c["mag"] += q
        if s["emplacement"]:
            emplacements[(mid, lid or 0, _code_emplacement(s["emplacement"]))] += q

    # --- cibles : compté, zéro pour les laizes non trouvées et les fiches à vider
    cibles: dict[tuple, Optional[dict]] = {}
    for cle, fi in fiches.items():
        mid = fi["id"]
        if fi["laizee"]:
            for r in conn.execute("SELECT laize_id FROM mp_stock_laize WHERE matiere_id=?", (mid,)).fetchall():
                cibles[(mid, int(r["laize_id"]))] = None
        else:
            cibles[(mid, None)] = None
    for k, c in compte.items():
        cibles[k] = c
    for (mid, lid), c in sorted(cibles.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
        fi = next(f for f in fiches.values() if f["id"] == mid)
        if c and c["inconnu"] and not (c["mag"] or c["prod"] or c["nc"]):
            rapport["stock_non_applique"].append((mid, lid, "conditionnement inconnu : unités non converties"))
            continue
        if c and c["inconnu"]:
            rapport["stock_partiel"].append((mid, lid, "%d ligne(s) sans conditionnement non comptée(s)" % c["inconnu"]))
        dispo = (c["mag"] + c["prod"]) if c else 0.0
        delta = _delta_depuis(conn, mid, lid, depuis)
        q_new = round(dispo + delta, 6)
        if q_new < 0:
            rapport["stocks_negatifs"].append((mid, lid, q_new))
        comm = []
        if delta:
            comm.append("compté %g + mouvements depuis le 01/10 %+g" % (round(dispo, 3), round(delta, 3)))
        if c and c["nc"]:
            comm.append("hors stock : %g en non-conformité" % round(c["nc"], 3))
        if not c:
            comm.append("non trouvé à l'inventaire")
        q_avant, ecart = _ecrire_stock(conn, mid, fi["categorie"], lid, q_new,
                                       round(c["mag"], 6) if c else 0.0, round(c["prod"], 6) if c else 0.0,
                                       " · ".join(comm))
        rapport["lignes_stock"].append((mid, lid, q_avant, q_new, ecart))

    # --- emplacements : ceux du terrain remplacent les précédents
    for cle, fi in fiches.items():
        conn.execute("DELETE FROM mp_emplacements WHERE matiere_id=?", (fi["id"],))
    for (mid, lid, code), q in emplacements.items():
        if q <= 0:
            continue
        conn.execute(
            """INSERT INTO mp_emplacements (matiere_id, laize_id, emplacement, quantite, updated_at, updated_by_name)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(matiere_id, laize_id, emplacement) DO UPDATE SET quantite=excluded.quantite""",
            (mid, lid, code, round(q, 6), _now(), AUTEUR),
        )
        rapport["emplacements"].append((mid, lid, code))

    # --- fiches à désactiver
    for cle, fi in fiches.items():
        if fi["action"] == "Désactiver":
            conn.execute("UPDATE matieres_premieres SET actif=0, updated_at=? WHERE id=?", (_now(), fi["id"]))
            conn.execute("UPDATE mp_variantes SET actif=0, principal=0 WHERE matiere_id=?", (fi["id"],))
            rapport["fiches_desactivees"].append(fi["id"])

    # --- variantes fournisseur
    principaux = []
    for v in data["variantes"]:
        fi = fiches.get(v["cle"])
        if not fi or fi["action"] == "Désactiver":
            continue
        mid = fi["id"]
        deja = conn.execute(
            """SELECT id FROM mp_variantes WHERE matiere_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)
                  AND libelle_technique=? AND actif=1""",
            (mid, v["fournisseur_id"], v["libelle_technique"]),
        ).fetchone()
        corps = {"fournisseur_id": v["fournisseur_id"], "libelle_technique": v["libelle_technique"],
                 "ref_fournisseur": v["ref_fournisseur"], "ml_bobine": v["ml_bobine"],
                 "note": "Reprise de l'inventaire du 01/10/2026."}
        if v["rvgi_code1"]:
            corps["ref_rvgi"] = "%s/%s" % (v["rvgi_code1"], v["rvgi_code2"])
            corps["rvgi_type_code"] = v["rvgi_type_code"]
        if deja:
            vid = int(deja["id"])
        else:
            # Une variante qui ne passe pas ne doit pas arrêter la reprise :
            # fournisseur absent de la base -> variante sans fournisseur ;
            # article RVGI refusé -> variante sans article ; sinon, consignée.
            if corps["fournisseur_id"] and not conn.execute(
                    "SELECT 1 FROM fournisseurs_fsc WHERE id=?", (corps["fournisseur_id"],)).fetchone():
                rapport["fournisseur_absent"].append((mid, corps["fournisseur_id"]))
                corps["fournisseur_id"] = None
            try:
                vid = mv.creer(conn, mid, corps, AUTEUR)
            except (ValueError, LookupError) as e:
                if "ref_rvgi" not in corps:
                    rapport["erreurs"].append("Fiche %d : variante non créée (%s)." % (mid, e))
                    continue
                rapport["rvgi_non_rattache"].append((mid, corps["ref_rvgi"], str(e)))
                corps.pop("ref_rvgi"); corps.pop("rvgi_type_code")
                try:
                    vid = mv.creer(conn, mid, corps, AUTEUR)
                except (ValueError, LookupError) as e2:
                    rapport["erreurs"].append("Fiche %d : variante non créée (%s)." % (mid, e2))
                    continue
            rapport["variantes_creees"].append(vid)
        if v["principal"]:
            principaux.append((mid, vid))
    for mid, vid in principaux:
        actuel = conn.execute(
            "SELECT id FROM mp_variantes WHERE matiere_id=? AND principal=1 AND actif=1", (mid,)
        ).fetchone()
        if actuel and int(actuel["id"]) == vid:
            continue
        res = mv.definir_principal(conn, vid, user_name=AUTEUR)
        if res.get("declinaisons_suivies"):
            rapport["prix_principal_change"].append((mid, vid, res["declinaisons_suivies"]))
    return dict(rapport)


def resume(rapport: dict) -> str:
    n = lambda k: len(rapport.get(k, []))
    return ("%d fiche(s) créée(s), %d renommée(s), %d désactivée(s) ; %d ligne(s) de stock "
            "(%d négative(s), %d non appliquée(s)) ; %d emplacement(s) ; %d variante(s) ; "
            "%d prix en vigueur déplacé(s) ; %d article(s) RVGI non rattaché(s) ; %d erreur(s)."
            % (n("fiches_creees"), n("fiches_renommees"), n("fiches_desactivees"), n("lignes_stock"),
               n("stocks_negatifs"), n("stock_non_applique"), n("emplacements"), n("variantes_creees"),
               n("prix_principal_change"), n("rvgi_non_rattache"), n("erreurs")))
