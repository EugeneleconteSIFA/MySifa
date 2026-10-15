"""Clôture d'inventaire de la valorisation MyStock.

Un inventaire physique se compte le matin du 1er et se saisit dans les jours
qui suivent ; les prix sont revus dans la foulée. La valorisation figée à une
date ne lit que la date de saisie : sans clôture, tout ce travail tombe hors
du stock de fin de mois.

Une clôture porte deux choses, pour une date donnée :

- Une date limite des prix. Le prix retenu est le dernier saisi au plus tard
  ce jour-là, au lieu du dernier saisi au plus tard le jour de clôture.
- Des mouvements rattachés. Saisis après la clôture, ils comptent comme s'ils
  avaient eu lieu le soir de la clôture : leur écart (après − avant) s'ajoute
  à la quantité reconstituée. On rattache l'écart et non la quantité comptée,
  parce qu'un comptage saisi le 14 tient compte des sorties du 1er au 14 :
  l'écart, lui, est l'erreur qui existait déjà le soir de la clôture.

Seule la valorisation à la date de clôture lit tout cela ; les autres dates
restent reconstituées à la date de saisie.
"""

from __future__ import annotations

# Préfixe des notes posées par /convertir-unite : une conversion n'est pas une
# correction d'inventaire, elle ne se propose pas au rattachement. La
# reconstitution PF s'en sert aussi pour retrouver le facteur de conversion.
NOTE_CONVERSION_UNITE = "Changement d'unité de vente"

# Mouvements PF écrits par le code lors d'une activité réelle (production,
# expédition, déplacement, FIFO) : jamais des corrections d'inventaire.
_NOTES_PF_ACTIVITE = ("Production", "Expédition", "Déplacement", "Sortie lot FIFO")


def _fin_de_jour(date_iso: str) -> str:
    return f"{date_iso}T23:59:59"


def lire(conn, date_cloture: str) -> dict | None:
    """Clôture enregistrée pour cette date, ou None."""
    try:
        row = conn.execute(
            "SELECT date_cloture, date_limite_prix, updated_at, updated_by_name "
            "FROM valo_clotures WHERE date_cloture=?",
            (date_cloture,),
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    nb = conn.execute(
        "SELECT source, COUNT(*) AS n FROM valo_cloture_mouvements "
        "WHERE date_cloture=? GROUP BY source",
        (date_cloture,),
    ).fetchall()
    compte = {r["source"]: int(r["n"]) for r in nb}
    return {
        "date_cloture": row["date_cloture"],
        "date_limite_prix": row["date_limite_prix"],
        "updated_at": row["updated_at"],
        "updated_by_name": row["updated_by_name"],
        "nb_mp": compte.get("mp", 0),
        "nb_pf": compte.get("pf", 0),
    }


def date_prix(conn, date_cloture: str) -> str:
    """Date à laquelle lire les prix pour valoriser au soir de date_cloture."""
    c = lire(conn, date_cloture)
    if c and c["date_limite_prix"] and c["date_limite_prix"] > date_cloture:
        return c["date_limite_prix"]
    return date_cloture


def ecarts_mp(conn, date_cloture: str) -> tuple[dict[int, float], dict[tuple[int, int], float]]:
    """Écarts des mouvements MP rattachés : ({matiere_id: δ}, {(matiere_id, laize_id): δ})."""
    non_laize: dict[int, float] = {}
    laize: dict[tuple[int, int], float] = {}
    try:
        rows = conn.execute(
            """SELECT m.matiere_id, m.laize_id,
                      COALESCE(m.quantite_apres, 0) - COALESCE(m.quantite_avant, 0) AS ecart
               FROM valo_cloture_mouvements c
               JOIN mp_mouvements m ON m.id = c.mouvement_id
               WHERE c.source='mp' AND c.date_cloture=? AND m.created_at > ?""",
            (date_cloture, _fin_de_jour(date_cloture)),
        ).fetchall()
    except Exception:
        return non_laize, laize
    for r in rows:
        d = float(r["ecart"] or 0)
        mid = int(r["matiere_id"])
        if r["laize_id"] is None:
            non_laize[mid] = non_laize.get(mid, 0.0) + d
        else:
            k = (mid, int(r["laize_id"]))
            laize[k] = laize.get(k, 0.0) + d
    return non_laize, laize


def ecarts_pf(conn, date_cloture: str) -> dict[int, float]:
    """Écarts des mouvements PF rattachés, par produit, dans l'unité actuelle.

    Un écart saisi avant un changement d'unité est dans l'ancienne unité : on
    lui applique les facteurs des conversions qui l'ont suivi."""
    out: dict[int, float] = {}
    try:
        rows = conn.execute(
            """SELECT m.produit_id, m.created_at,
                      COALESCE(m.quantite_apres, 0) - COALESCE(m.quantite_avant, 0) AS ecart
               FROM valo_cloture_mouvements c
               JOIN mouvements_stock m ON m.id = c.mouvement_id
               WHERE c.source='pf' AND c.date_cloture=? AND m.created_at > ?""",
            (date_cloture, _fin_de_jour(date_cloture)),
        ).fetchall()
    except Exception:
        return out
    if not rows:
        return out
    conversions = conn.execute(
        """SELECT produit_id, created_at,
                  MAX(quantite_apres / quantite_avant) AS facteur
           FROM mouvements_stock
           WHERE created_at > ? AND note LIKE ? AND quantite_avant > 0
           GROUP BY produit_id, created_at""",
        (_fin_de_jour(date_cloture), NOTE_CONVERSION_UNITE + "%"),
    ).fetchall()
    for r in rows:
        pid = int(r["produit_id"])
        d = float(r["ecart"] or 0)
        for cv in conversions:
            if int(cv["produit_id"]) == pid and cv["created_at"] > r["created_at"]:
                f = float(cv["facteur"] or 0)
                if f > 0:
                    d *= f
        out[pid] = out.get(pid, 0.0) + d
    return out


def candidats(conn, date_cloture: str) -> list[dict]:
    """Mouvements saisis après la clôture qui peuvent s'y rattacher.

    MP : ajustements et inventaires. PF : inventaires, et entrées/sorties
    manuelles (hors production, expédition, déplacement, FIFO, conversion)."""
    fin = _fin_de_jour(date_cloture)
    rattaches = {
        (r["source"], int(r["mouvement_id"])): r["date_cloture"]
        for r in conn.execute(
            "SELECT source, mouvement_id, date_cloture FROM valo_cloture_mouvements"
        ).fetchall()
    }
    out: list[dict] = []
    mp = conn.execute(
        """SELECT m.id, m.created_at, m.type_mouvement, m.quantite_avant, m.quantite_apres,
                  m.note, m.created_by_name, m.unite_saisie,
                  mp.reference, mp.designation, mp.categorie, l.label AS laize
           FROM mp_mouvements m
           LEFT JOIN matieres_premieres mp ON mp.id = m.matiere_id
           LEFT JOIN mp_laizes l ON l.id = m.laize_id
           WHERE m.created_at > ? AND m.type_mouvement IN ('ajustement', 'inventaire')
           ORDER BY m.created_at, m.id""",
        (fin,),
    ).fetchall()
    for r in mp:
        out.append(_ligne("mp", r, r["laize"], r["categorie"], rattaches, date_cloture))
    exclues = " AND ".join(["COALESCE(m.note,'') NOT LIKE ?"] * (len(_NOTES_PF_ACTIVITE) + 1))
    pf = conn.execute(
        f"""SELECT m.id, m.created_at, m.type_mouvement, m.quantite_avant, m.quantite_apres,
                   m.note, m.created_by_name, m.emplacement,
                   p.reference, p.designation, p.unite
            FROM mouvements_stock m
            LEFT JOIN produits p ON p.id = m.produit_id
            WHERE m.created_at > ? AND {exclues}
            ORDER BY m.created_at, m.id""",
        (fin, *[n + "%" for n in _NOTES_PF_ACTIVITE], NOTE_CONVERSION_UNITE + "%"),
    ).fetchall()
    for r in pf:
        out.append(_ligne("pf", r, r["emplacement"], r["unite"], rattaches, date_cloture))
    return out


def _ligne(source, r, detail, complement, rattaches, date_cloture) -> dict:
    avant = float(r["quantite_avant"] or 0)
    apres = float(r["quantite_apres"] or 0)
    autre = rattaches.get((source, int(r["id"])))
    return {
        "source": source,
        "id": int(r["id"]),
        "created_at": r["created_at"],
        "type": r["type_mouvement"],
        "reference": r["reference"] or "",
        "designation": r["designation"] or "",
        "detail": detail or "",
        "complement": complement or "",
        "note": r["note"] or "",
        "par": r["created_by_name"] or "",
        "avant": round(avant, 4),
        "apres": round(apres, 4),
        "ecart": round(apres - avant, 4),
        "rattache": autre == date_cloture,
        "rattache_ailleurs": autre if autre and autre != date_cloture else None,
    }


def enregistrer(
    conn, date_cloture: str, date_limite_prix: str | None,
    mp_ids: list[int], pf_ids: list[int], *, now: str, par: str | None,
) -> dict:
    """Remplace la clôture de cette date. Les mouvements rattachés à une autre
    clôture n'en sont pas retirés : ils sont ignorés ici."""
    fin = _fin_de_jour(date_cloture)
    conn.execute(
        """INSERT INTO valo_clotures (date_cloture, date_limite_prix, updated_at, updated_by_name)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(date_cloture) DO UPDATE SET
             date_limite_prix=excluded.date_limite_prix,
             updated_at=excluded.updated_at,
             updated_by_name=excluded.updated_by_name""",
        (date_cloture, date_limite_prix, now, par),
    )
    conn.execute("DELETE FROM valo_cloture_mouvements WHERE date_cloture=?", (date_cloture,))
    n = 0
    for source, table, ids in (("mp", "mp_mouvements", mp_ids), ("pf", "mouvements_stock", pf_ids)):
        for mid in ids:
            ok = conn.execute(
                f"SELECT 1 FROM {table} WHERE id=? AND created_at > ?", (mid, fin)
            ).fetchone()
            if not ok:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO valo_cloture_mouvements "
                "(source, mouvement_id, date_cloture, created_at) VALUES (?, ?, ?, ?)",
                (source, mid, date_cloture, now),
            )
            n += cur.rowcount or 0
    conn.commit()
    return {"nb_rattaches": n}
