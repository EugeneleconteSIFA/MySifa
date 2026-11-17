"""
MyExpé — grilles tarifaires transporteur, versionnées.

Une grille (`expe_tarif_grilles`) regroupe les lignes de `expe_tarifs` d'un
même import pour un type d'envoi et une base de calcul. Elle vit en trois
états :

- **brouillon** : lignes à `actif=0`, ignorées par le comparateur ;
- **active** : ses lignes à `actif=1` sont celles que lit la recherche de
  tarif (`_trouver_ligne_tarif`, inchangée) ;
- **archivée** : plus aucune ligne active.

Activer une grille retire les lignes actives qu'elle remplace : même type
d'envoi, même base, même zone, tranche qui chevauche. Elles passent à
`actif=0` avec `remplacee_par_grille_id`, sans être supprimées. Archiver la
grille ensuite les rétablit : c'est le retour arrière. Une zone absente de la
nouvelle grille (l'international d'une grille France) garde ses tarifs.

L'écran ne charge jamais toutes les lignes : il lit le résumé des grilles
(`lister`), puis une page de zones à la fois (`matrice`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")

TYPES_ENVOI = ("messagerie", "ramasse", "affretement", "express_intl")
BASES_CALCUL = ("poids", "palette", "metre_plancher")
UNITES = ("forfait", "au_100kg", "au_kg")
ZONE_TYPES = ("departement", "code_postal", "zone_intl", "pays")

LIBELLE_TYPE = {
    "messagerie": "Messagerie",
    "ramasse": "Ramasse",
    "affretement": "Affrètement",
    "express_intl": "Express international",
}
LIBELLE_BASE = {"poids": "au poids", "palette": "à la palette", "metre_plancher": "au mètre plancher"}


class GrilleErreur(Exception):
    """Message destiné à l'utilisateur."""


def _maintenant() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def libelle_defaut(type_envoi: str, base_calcul: str) -> str:
    return f"{LIBELLE_TYPE.get(type_envoi, type_envoi)} {LIBELLE_BASE.get(base_calcul, base_calcul)}"


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except ValueError:
        return None


def normaliser_ligne(lg: dict) -> Optional[dict]:
    """Ramène une ligne lue au schéma de `expe_tarifs`, ou None si inutilisable."""
    te = str(lg.get("type_envoi") or "messagerie").strip().lower()
    bc = str(lg.get("base_calcul") or "poids").strip().lower()
    zt = str(lg.get("zone_type") or "departement").strip().lower()
    zv = str(lg.get("zone_valeur") or "").strip()
    un = str(lg.get("unite") or "forfait").strip().lower()
    prix = _num(lg.get("prix"))
    tmin = _num(lg.get("tranche_min"))
    tmax = _num(lg.get("tranche_max"))
    if te not in TYPES_ENVOI or bc not in BASES_CALCUL or zt not in ZONE_TYPES:
        return None
    if un not in UNITES or not zv or prix is None or prix < 0:
        return None
    if tmin is None:
        tmin = 0.0
    if tmax is not None and tmax < tmin:
        return None
    if zt == "departement" and zv.isdigit() and len(zv) == 1:
        zv = zv.zfill(2)
    return {
        "type_envoi": te,
        "base_calcul": bc,
        "zone_type": zt,
        "zone_valeur": zv,
        "tranche_min": tmin,
        "tranche_max": tmax,
        "prix": round(prix, 4),
        "unite": un,
        "mini_perception": _num(lg.get("mini_perception")),
    }


# ─── Création ────────────────────────────────────────────────────────


def creer_brouillons(
    conn,
    transporteur_id: int,
    lignes: Iterable[dict],
    *,
    source_filename: Optional[str],
    methode: str,
    email: Optional[str],
    date_effet: Optional[str] = None,
    frais: Iterable[dict] = (),
) -> list[int]:
    """Range les lignes lues en grilles brouillon, une par type d'envoi et base.

    Une même cellule lue deux fois (tableau répété sur deux pages) ne crée
    qu'une ligne : la dernière lue l'emporte.
    """
    groupes: dict[tuple, dict] = {}
    for brute in lignes:
        lg = normaliser_ligne(brute)
        if lg is None:
            continue
        cle_g = (lg["type_envoi"], lg["base_calcul"])
        cle_l = (lg["zone_type"], lg["zone_valeur"], lg["tranche_min"], lg["tranche_max"], lg["unite"])
        groupes.setdefault(cle_g, {})[cle_l] = lg
    if not groupes:
        raise GrilleErreur("Aucune ligne tarifaire exploitable dans ce fichier.")

    now = _maintenant()
    ids = []
    for (te, bc), lignes_g in sorted(groupes.items()):
        gid = conn.execute(
            """INSERT INTO expe_tarif_grilles
                   (transporteur_id, libelle, type_envoi, base_calcul, statut,
                    date_effet, source_filename, methode_lecture,
                    created_at, created_by_email)
               VALUES (?,?,?,?,'brouillon',?,?,?,?,?)""",
            (transporteur_id, libelle_defaut(te, bc), te, bc, date_effet,
             source_filename, methode, now, email),
        ).lastrowid
        conn.executemany(
            """INSERT INTO expe_tarifs
                   (transporteur_id, grille_id, type_envoi, base_calcul, zone_type,
                    zone_valeur, tranche_min, tranche_max, prix, unite,
                    mini_perception, valid_from, actif, source_filename,
                    created_at, created_by_email)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
            [
                (transporteur_id, gid, lg["type_envoi"], lg["base_calcul"],
                 lg["zone_type"], lg["zone_valeur"], lg["tranche_min"],
                 lg["tranche_max"], lg["prix"], lg["unite"], lg["mini_perception"],
                 date_effet, source_filename, now, email)
                for lg in lignes_g.values()
            ],
        )
        ids.append(gid)

    for fr in frais or ():
        lib = str(fr.get("libelle") or "").strip()
        val = _num(fr.get("valeur"))
        if not lib or val is None:
            continue
        if conn.execute(
            "SELECT 1 FROM expe_tarifs_frais WHERE transporteur_id=? AND libelle=?",
            (transporteur_id, lib),
        ).fetchone():
            continue
        conn.execute(
            """INSERT INTO expe_tarifs_frais
                   (transporteur_id, libelle, mode, valeur, mini, applique_defaut)
               VALUES (?,?,?,?,?,?)""",
            (transporteur_id, lib, fr.get("mode") or "forfait_expedition", val,
             _num(fr.get("mini")), 1 if fr.get("applique_defaut", 1) else 0),
        )
    return ids


# ─── Lecture ─────────────────────────────────────────────────────────


def _grille(conn, transporteur_id: int, grille_id: int):
    g = conn.execute(
        "SELECT * FROM expe_tarif_grilles WHERE id=? AND transporteur_id=?",
        (grille_id, transporteur_id),
    ).fetchone()
    if not g:
        raise GrilleErreur("Grille introuvable.")
    return g


def libelle_tranche(tmin: Optional[float], tmax: Optional[float], base: str) -> str:
    def f(v):
        return str(int(v)) if v is not None and float(v).is_integer() else str(v)

    if base == "palette":
        if tmax is not None and tmin == tmax:
            return f"{f(tmin)} pal."
        return f"{f(tmin)} à {f(tmax)} pal." if tmax is not None else f"{f(tmin)} pal. et +"
    unite = "m" if base == "metre_plancher" else "kg"
    if tmax is None:
        return f"{f(tmin)} {unite} et +"
    return f"{f(tmin)} – {f(tmax)} {unite}"


def comparaison(conn, grille_id: int) -> dict:
    """Écart entre une grille et les lignes actives d'autres grilles qu'elle recouvre.

    Pour un brouillon : ce que l'activation changerait. Pour une grille
    active : rien à comparer (ses lignes sont celles en place).
    """
    r = conn.execute(
        """SELECT COUNT(*) AS n,
                  AVG(n.prix / a.prix) AS moy,
                  MIN(n.prix / a.prix) AS mini,
                  MAX(n.prix / a.prix) AS maxi
             FROM expe_tarifs n
             JOIN expe_tarifs a
               ON a.transporteur_id = n.transporteur_id AND a.actif = 1
              AND a.grille_id IS NOT n.grille_id
              AND a.type_envoi = n.type_envoi AND a.base_calcul = n.base_calcul
              AND a.zone_type = n.zone_type AND a.zone_valeur = n.zone_valeur
              AND a.tranche_min = n.tranche_min
              AND a.tranche_max IS n.tranche_max AND a.unite = n.unite
            WHERE n.grille_id = ? AND a.prix > 0""",
        (grille_id,),
    ).fetchone()
    zones = conn.execute(
        """SELECT COUNT(DISTINCT n.zone_type || ' ' || n.zone_valeur) AS total,
                  COUNT(DISTINCT CASE WHEN EXISTS (
                      SELECT 1 FROM expe_tarifs a
                       WHERE a.transporteur_id = n.transporteur_id AND a.actif = 1
                         AND a.grille_id IS NOT n.grille_id
                         AND a.type_envoi = n.type_envoi AND a.base_calcul = n.base_calcul
                         AND a.zone_type = n.zone_type AND a.zone_valeur = n.zone_valeur)
                    THEN NULL ELSE n.zone_type || ' ' || n.zone_valeur END) AS nouvelles
             FROM expe_tarifs n WHERE n.grille_id = ?""",
        (grille_id,),
    ).fetchone()

    def pct(v):
        return None if v is None else round((float(v) - 1) * 100, 1)

    return {
        "cellules_comparees": int(r["n"] or 0),
        "ecart_moyen_pct": pct(r["moy"]),
        "ecart_min_pct": pct(r["mini"]),
        "ecart_max_pct": pct(r["maxi"]),
        "zones": int(zones["total"] or 0),
        "zones_nouvelles": int(zones["nouvelles"] or 0),
    }


def lister(conn, transporteur_id: int) -> list[dict]:
    """Résumé des grilles d'un transporteur, sans aucune ligne de prix."""
    grilles = conn.execute(
        """SELECT g.*,
                  COUNT(t.id) AS nb_lignes,
                  SUM(CASE WHEN t.actif = 1 THEN 1 ELSE 0 END) AS nb_actives,
                  SUM(CASE WHEN t.remplacee_par_grille_id IS NOT NULL THEN 1 ELSE 0 END) AS nb_remplacees,
                  COUNT(DISTINCT t.zone_type || ' ' || t.zone_valeur) AS nb_zones,
                  COUNT(DISTINCT COALESCE(t.tranche_min, '') || '|' || COALESCE(t.tranche_max, '') || '|' || t.unite) AS nb_tranches
             FROM expe_tarif_grilles g
             LEFT JOIN expe_tarifs t ON t.grille_id = g.id
            WHERE g.transporteur_id = ?
            GROUP BY g.id
            ORDER BY CASE g.statut WHEN 'brouillon' THEN 0 WHEN 'active' THEN 1 ELSE 2 END,
                     g.type_envoi, g.base_calcul, g.id DESC""",
        (transporteur_id,),
    ).fetchall()
    out = []
    for g in grilles:
        d = dict(g)
        d["nb_actives"] = int(d["nb_actives"] or 0)
        d["nb_remplacees"] = int(d["nb_remplacees"] or 0)
        if d["statut"] == "brouillon":
            d["comparaison"] = comparaison(conn, d["id"])
        out.append(d)
    return out


def matrice(
    conn,
    transporteur_id: int,
    grille_id: int,
    recherche: str = "",
    offset: int = 0,
    limite: int = 60,
) -> dict:
    """Une page de la grille en tableau : zones en lignes, tranches en colonnes.

    Pour un brouillon, chaque cellule porte aussi le prix actif qu'elle
    remplacerait, pour que l'écart se lise case par case.
    """
    g = _grille(conn, transporteur_id, grille_id)
    tranches = [
        dict(r)
        for r in conn.execute(
            """SELECT DISTINCT tranche_min, tranche_max, unite FROM expe_tarifs
                WHERE grille_id = ? ORDER BY tranche_min, tranche_max""",
            (grille_id,),
        ).fetchall()
    ]
    for t in tranches:
        t["libelle"] = libelle_tranche(t["tranche_min"], t["tranche_max"], g["base_calcul"])
    index = {(t["tranche_min"], t["tranche_max"], t["unite"]): i for i, t in enumerate(tranches)}

    q = (recherche or "").strip()
    filtre, params = "", [grille_id]
    if q:
        filtre = " AND (zone_valeur LIKE ? OR zone_type || ' ' || zone_valeur LIKE ?)"
        params += [q + "%", "%" + q + "%"]
    total = conn.execute(
        f"""SELECT COUNT(*) FROM (SELECT DISTINCT zone_type, zone_valeur
              FROM expe_tarifs WHERE grille_id = ?{filtre})""",
        params,
    ).fetchone()[0]
    zones = conn.execute(
        f"""SELECT DISTINCT zone_type, zone_valeur FROM expe_tarifs
             WHERE grille_id = ?{filtre}
             ORDER BY zone_type, length(zone_valeur), zone_valeur
             LIMIT ? OFFSET ?""",
        params + [max(1, min(int(limite), 200)), max(0, int(offset))],
    ).fetchall()

    lignes = []
    if zones:
        cles = [(z["zone_type"], z["zone_valeur"]) for z in zones]
        trous = ",".join("(?,?)" for _ in cles)
        plat = [v for c in cles for v in c]
        par_zone: dict[tuple, dict] = {c: {"prix": [None] * len(tranches), "ancien": [None] * len(tranches)} for c in cles}
        for r in conn.execute(
            f"""SELECT zone_type, zone_valeur, tranche_min, tranche_max, unite, prix, actif
                  FROM expe_tarifs WHERE grille_id = ?
                   AND (zone_type, zone_valeur) IN (VALUES {trous})""",
            [grille_id] + plat,
        ):
            i = index.get((r["tranche_min"], r["tranche_max"], r["unite"]))
            if i is not None:
                par_zone[(r["zone_type"], r["zone_valeur"])]["prix"][i] = r["prix"]
        if g["statut"] == "brouillon":
            for r in conn.execute(
                f"""SELECT zone_type, zone_valeur, tranche_min, tranche_max, unite, prix
                      FROM expe_tarifs
                     WHERE transporteur_id = ? AND actif = 1 AND grille_id IS NOT ?
                       AND type_envoi = ? AND base_calcul = ?
                       AND (zone_type, zone_valeur) IN (VALUES {trous})""",
                [transporteur_id, grille_id, g["type_envoi"], g["base_calcul"]] + plat,
            ):
                i = index.get((r["tranche_min"], r["tranche_max"], r["unite"]))
                if i is not None:
                    par_zone[(r["zone_type"], r["zone_valeur"])]["ancien"][i] = r["prix"]
        for c in cles:
            lignes.append({"zone_type": c[0], "zone_valeur": c[1], **par_zone[c]})

    return {"grille": dict(g), "tranches": tranches, "zones": lignes, "total": total,
            "offset": int(offset)}


# ─── Changements d'état ──────────────────────────────────────────────


def activer(conn, transporteur_id: int, grille_id: int, email: Optional[str]) -> dict:
    """Active une grille brouillon ou archivée et retire ce qu'elle remplace."""
    g = _grille(conn, transporteur_id, grille_id)
    if g["statut"] == "active":
        raise GrilleErreur("Cette grille est déjà active.")
    remplacees = conn.execute(
        """UPDATE expe_tarifs SET actif = 0, remplacee_par_grille_id = ?
            WHERE transporteur_id = ? AND actif = 1 AND grille_id IS NOT ?
              AND EXISTS (
                SELECT 1 FROM expe_tarifs n
                 WHERE n.grille_id = ?
                   AND n.type_envoi = expe_tarifs.type_envoi
                   AND n.base_calcul = expe_tarifs.base_calcul
                   AND n.zone_type = expe_tarifs.zone_type
                   AND n.zone_valeur = expe_tarifs.zone_valeur
                   AND (n.tranche_max IS NULL OR expe_tarifs.tranche_min <= n.tranche_max)
                   AND (expe_tarifs.tranche_max IS NULL OR n.tranche_min <= expe_tarifs.tranche_max))""",
        (grille_id, transporteur_id, grille_id, grille_id),
    ).rowcount or 0
    activees = conn.execute(
        "UPDATE expe_tarifs SET actif = 1, remplacee_par_grille_id = NULL WHERE grille_id = ?",
        (grille_id,),
    ).rowcount or 0
    now = _maintenant()
    conn.execute(
        """UPDATE expe_tarif_grilles
              SET statut = 'active', activee_le = ?, activee_par = ?, archivee_le = NULL
            WHERE id = ?""",
        (now, email, grille_id),
    )
    archivees = _archiver_grilles_vides(conn, transporteur_id, now)
    return {"activees": activees, "remplacees": remplacees, "grilles_archivees": archivees}


def _archiver_grilles_vides(conn, transporteur_id: int, now: str) -> int:
    """Une grille active dont toutes les lignes ont été remplacées passe archivée."""
    return conn.execute(
        """UPDATE expe_tarif_grilles SET statut = 'archivee', archivee_le = ?
            WHERE transporteur_id = ? AND statut = 'active'
              AND NOT EXISTS (SELECT 1 FROM expe_tarifs t
                               WHERE t.grille_id = expe_tarif_grilles.id AND t.actif = 1)""",
        (now, transporteur_id),
    ).rowcount or 0


def archiver(conn, transporteur_id: int, grille_id: int) -> dict:
    """Retire une grille active et rétablit les lignes qu'elle avait remplacées."""
    g = _grille(conn, transporteur_id, grille_id)
    if g["statut"] != "active":
        raise GrilleErreur("Seule une grille active peut être archivée.")
    retirees = conn.execute(
        "UPDATE expe_tarifs SET actif = 0 WHERE grille_id = ? AND actif = 1", (grille_id,)
    ).rowcount or 0
    # Ses lignes déjà remplacées par une grille plus récente ne doivent pas
    # revenir le jour où celle-ci sera archivée : la grille est retirée
    # volontairement, en entier.
    conn.execute(
        "UPDATE expe_tarifs SET remplacee_par_grille_id = NULL WHERE grille_id = ?",
        (grille_id,),
    )
    rendues = conn.execute(
        "SELECT DISTINCT grille_id FROM expe_tarifs WHERE remplacee_par_grille_id = ?",
        (grille_id,),
    ).fetchall()
    retablies = conn.execute(
        """UPDATE expe_tarifs SET actif = 1, remplacee_par_grille_id = NULL
            WHERE remplacee_par_grille_id = ?""",
        (grille_id,),
    ).rowcount or 0
    for r in rendues:
        conn.execute(
            """UPDATE expe_tarif_grilles SET statut = 'active', archivee_le = NULL
                WHERE id = ? AND statut = 'archivee'""",
            (r["grille_id"],),
        )
    conn.execute(
        "UPDATE expe_tarif_grilles SET statut = 'archivee', archivee_le = ? WHERE id = ?",
        (_maintenant(), grille_id),
    )
    return {"retirees": retirees, "retablies": retablies}


def supprimer(conn, transporteur_id: int, grille_id: int) -> int:
    """Supprime une grille brouillon ou archivée et ses lignes."""
    g = _grille(conn, transporteur_id, grille_id)
    if g["statut"] == "active":
        raise GrilleErreur("Archiver la grille avant de la supprimer.")
    # Des lignes encore remplacées par cette grille (cas d'une base reprise
    # à la main) redeviennent simplement inactives et sans lien.
    conn.execute(
        "UPDATE expe_tarifs SET remplacee_par_grille_id = NULL WHERE remplacee_par_grille_id = ?",
        (grille_id,),
    )
    n = conn.execute("DELETE FROM expe_tarifs WHERE grille_id = ?", (grille_id,)).rowcount or 0
    conn.execute("DELETE FROM expe_tarif_grilles WHERE id = ?", (grille_id,))
    return n


def modifier(conn, transporteur_id: int, grille_id: int, champs: dict) -> dict:
    """Libellé et date d'effet toujours ; type d'envoi seulement en brouillon."""
    g = _grille(conn, transporteur_id, grille_id)
    maj: dict[str, Any] = {}
    if "libelle" in champs:
        lib = str(champs.get("libelle") or "").strip()[:120]
        if not lib:
            raise GrilleErreur("Libellé obligatoire.")
        maj["libelle"] = lib
    if "date_effet" in champs:
        d = str(champs.get("date_effet") or "").strip()
        if d:
            try:
                datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                raise GrilleErreur("Date d'effet invalide — format AAAA-MM-JJ.")
        maj["date_effet"] = d or None
    if "type_envoi" in champs:
        te = str(champs.get("type_envoi") or "").strip()
        if te not in TYPES_ENVOI:
            raise GrilleErreur("Type d'envoi inconnu.")
        if te != g["type_envoi"]:
            if g["statut"] != "brouillon":
                raise GrilleErreur("Le type d'envoi ne se change que sur un brouillon.")
            maj["type_envoi"] = te
            conn.execute("UPDATE expe_tarifs SET type_envoi = ? WHERE grille_id = ?", (te, grille_id))
    if maj:
        sets = ", ".join(f"{k} = ?" for k in maj)
        conn.execute(f"UPDATE expe_tarif_grilles SET {sets} WHERE id = ?", (*maj.values(), grille_id))
    if "date_effet" in maj:
        conn.execute("UPDATE expe_tarifs SET valid_from = ? WHERE grille_id = ?", (maj["date_effet"], grille_id))
    return dict(_grille(conn, transporteur_id, grille_id))


def vider(conn, transporteur_id: int) -> dict:
    n_l = conn.execute("DELETE FROM expe_tarifs WHERE transporteur_id = ?", (transporteur_id,)).rowcount or 0
    n_f = conn.execute("DELETE FROM expe_tarifs_frais WHERE transporteur_id = ?", (transporteur_id,)).rowcount or 0
    n_g = conn.execute("DELETE FROM expe_tarif_grilles WHERE transporteur_id = ?", (transporteur_id,)).rowcount or 0
    return {"deleted_lignes": n_l, "deleted_frais": n_f, "deleted_grilles": n_g}
