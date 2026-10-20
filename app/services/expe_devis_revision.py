"""Révision d'une demande de tarif transport après envoi (MyExpé).

Une demande partie chez les transporteurs se modifie désormais sans être
clôturée ni dupliquée : elle garde sa référence et ses offres. Ce qui change
dépend du champ touché, parce que tous ne pèsent pas pareil sur un prix :

- **rechiffrage** — destination, type d'envoi, poids, palettes, type de
  palette. Le prix déjà donné ne correspond plus à la demande : la révision
  monte d'un cran, chaque offre reçue devient « à confirmer », et chaque
  transporteur sollicité reçoit les données à jour ;
- **information** — contraintes. Les transporteurs en sont informés, mais
  leurs offres restent valables : une précision sur le créneau de livraison ne
  rend pas un prix caduc ;
- **interne** — client. Le transporteur ne le voit pas, personne n'est prévenu.

Le module ne fait ni email ni HTTP : il compare, classe et écrit. L'envoi reste
dans le router, à côté des trois autres emails transporteur.
"""
from __future__ import annotations

import json
from typing import Any, Optional

CHAMPS_RECHIFFRAGE = (
    "code_postal_destination",
    "type_envoi",
    "poids_total_kg",
    "nb_palette",
    "type_palette",
)
CHAMPS_INFORMATION = ("contraintes",)
CHAMPS_INTERNES = ("client",)
CHAMPS = CHAMPS_RECHIFFRAGE + CHAMPS_INFORMATION + CHAMPS_INTERNES

MODE_RECHIFFRAGE = "rechiffrage"
MODE_INFORMATION = "information"
MODE_INTERNE = "interne"

# Statuts qui ne reçoivent pas l'email de modification. `echec` : l'adresse
# n'a jamais reçu la demande, lui écrire « elle a changé » n'aurait pas de
# sens. `refusee` / `retenue` n'existent que sur une demande clôturée, déjà
# refusée en amont ; les exclure ici évite qu'un futur statut les réintroduise.
STATUTS_NON_PREVENUS = ("echec", "refusee", "retenue")

_NUMERIQUES = ("poids_total_kg", "nb_palette")


def normaliser(champ: str, val: Any) -> Any:
    """Forme comparable d'une valeur : `""`, `None` et `"  "` sont un même vide,
    `1200`, `1200.0` et `"1200"` un même poids."""
    if champ in _NUMERIQUES:
        if val is None or (isinstance(val, str) and not val.strip()):
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            raise ValueError(f"{champ} invalide.")
    txt = str(val or "").strip()
    return txt or None


def changements(demande: dict, body: dict) -> list[dict]:
    """Champs de `body` dont la valeur diffère de la demande, dans l'ordre de
    `CHAMPS`. Un champ absent de `body` n'est pas un changement."""
    out = []
    for champ in CHAMPS:
        if champ not in body:
            continue
        avant = normaliser(champ, demande.get(champ))
        apres = normaliser(champ, body.get(champ))
        if avant != apres:
            out.append({"champ": champ, "avant": avant, "apres": apres})
    return out


def classer(chg: list[dict]) -> Optional[str]:
    """Le mode le plus fort parmi les champs touchés, ou None sans changement."""
    champs = {c["champ"] for c in chg}
    if champs & set(CHAMPS_RECHIFFRAGE):
        return MODE_RECHIFFRAGE
    if champs & set(CHAMPS_INFORMATION):
        return MODE_INFORMATION
    if champs:
        return MODE_INTERNE
    return None


def visibles(chg: list[dict]) -> list[dict]:
    """Les changements que le transporteur a le droit de voir."""
    return [c for c in chg if c["champ"] not in CHAMPS_INTERNES]


def offre_a_confirmer(reponse: dict, demande: dict) -> bool:
    """Une offre chiffrée sur une révision antérieure à celle de la demande."""
    if reponse.get("prix") is None:
        return False
    return int(reponse.get("revision_offre") or 0) < int(demande.get("revision") or 0)


def deja_envoyee(conn, demande_id: int) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM expe_devis_reponses WHERE demande_id=? AND sent_at IS NOT NULL LIMIT 1",
            (demande_id,),
        ).fetchone()
    )


def destinataires(conn, demande_id: int) -> list[dict]:
    """Lignes de réponse à prévenir d'une modification : celles dont la demande
    est réellement partie, hors statuts de `STATUTS_NON_PREVENUS`.

    `sans_suite` est prévenu : « je ne prends pas » a été dit sur l'ancienne
    version, et un poids divisé par deux peut faire changer d'avis."""
    ph = ",".join("?" * len(STATUTS_NON_PREVENUS))
    rows = conn.execute(
        f"""SELECT * FROM expe_devis_reponses
            WHERE demande_id=? AND sent_at IS NOT NULL
              AND COALESCE(statut,'') NOT IN ({ph})
              AND TRIM(COALESCE(destinataire_email,'')) LIKE '%@%'
            ORDER BY id""",
        (demande_id, *STATUTS_NON_PREVENUS),
    ).fetchall()
    return [dict(r) for r in rows]


def appliquer(
    conn,
    *,
    demande: dict,
    chg: list[dict],
    now: str,
    email: Optional[str],
    message: Optional[str] = None,
) -> dict:
    """Écrit les nouvelles valeurs, monte la révision si besoin et journalise.

    Ne commite pas : le router envoie ensuite les emails dans la même
    transaction, puis complète la ligne de révision avec le bilan d'envoi.
    Renvoie `{mode, revision, revision_id}` — `revision_id` vaut None pour une
    modification interne, qui ne laisse pas de trace côté transporteur.
    """
    mode = classer(chg)
    if mode is None:
        return {"mode": None, "revision": int(demande.get("revision") or 0), "revision_id": None}
    sets = [f"{c['champ']}=?" for c in chg]
    args: list[Any] = [c["apres"] for c in chg]
    revision = int(demande.get("revision") or 0)
    if mode == MODE_RECHIFFRAGE:
        revision += 1
        sets += ["revision=?", "revise_le=?"]
        args += [revision, now]
    args.append(int(demande["id"]))
    conn.execute(f"UPDATE expe_demandes_devis SET {', '.join(sets)} WHERE id=?", args)

    revision_id = None
    if mode != MODE_INTERNE:
        cur = conn.execute(
            """INSERT INTO expe_devis_revisions
               (demande_id, revision, rechiffrage, changements, message,
                created_at, created_by_email)
               VALUES (?,?,?,?,?,?,?)""",
            (
                int(demande["id"]),
                revision,
                1 if mode == MODE_RECHIFFRAGE else 0,
                json.dumps(visibles(chg), ensure_ascii=False),
                (message or "").strip() or None,
                now,
                email,
            ),
        )
        revision_id = int(cur.lastrowid)
    return {"mode": mode, "revision": revision, "revision_id": revision_id}


def bilan_envoi(conn, revision_id: Optional[int], ok: int, ko: int) -> None:
    if revision_id:
        conn.execute(
            "UPDATE expe_devis_revisions SET nb_envoyes=?, nb_echecs=? WHERE id=?",
            (ok, ko, revision_id),
        )


def historique(conn, demande_id: int) -> list[dict]:
    """Modifications après envoi, la plus récente d'abord."""
    out = []
    for r in conn.execute(
        """SELECT * FROM expe_devis_revisions WHERE demande_id=?
           ORDER BY created_at DESC, id DESC""",
        (demande_id,),
    ).fetchall():
        d = dict(r)
        try:
            d["changements"] = json.loads(d.get("changements") or "[]")
        except (TypeError, ValueError):
            d["changements"] = []
        d["rechiffrage"] = bool(d.get("rechiffrage"))
        out.append(d)
    return out


def derniere(conn, demande_id: int) -> Optional[dict]:
    h = historique(conn, demande_id)
    return h[0] if h else None
