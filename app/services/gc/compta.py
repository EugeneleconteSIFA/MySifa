"""Comptabilité clients / fournisseurs : échéances, règlements, lettrage.

- Un règlement s'affecte à des échéances du même tiers, jamais au-delà de
  leur reste dû, et la somme affectée ne dépasse pas le montant reçu. Le non
  affecté reste disponible sur le règlement (acompte, trop-perçu).
- `regle_cents` d'une échéance = somme de ses affectations, recalculée ici.
- Une facture entièrement réglée passe à l'état « soldé » (affiché « Réglée »),
  et y revient si un règlement est supprimé.
"""
from __future__ import annotations

from datetime import datetime

from app.services.gc.pieces import ErreurPiece

SENS_PAR_TYPE = {"facture": "encaissement", "facture_fournisseur": "decaissement"}


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def echeances(conn, tiers_id: int | None = None, ouvertes: bool = False) -> list[dict]:
    filtres, args = [], []
    if tiers_id:
        filtres.append("p.tiers_id=?")
        args.append(tiers_id)
    if ouvertes:
        filtres.append("e.montant_cents > e.regle_cents")
    where = ("WHERE " + " AND ".join(filtres)) if filtres else ""
    return [dict(r) for r in conn.execute(
        f"""SELECT e.id, e.date_echeance, e.montant_cents, e.regle_cents,
                   e.montant_cents - e.regle_cents AS reste_cents,
                   p.id AS piece_id, p.type, p.numero, p.date_piece, p.mode_paiement,
                   t.id AS tiers_id, t.raison_sociale AS tiers_nom
            FROM gc_echeances e JOIN gc_pieces p ON p.id=e.piece_id JOIN gc_tiers t ON t.id=p.tiers_id
            {where} ORDER BY e.date_echeance, e.id""", args).fetchall()]


def _majs(conn, echeance_ids: set[int]) -> None:
    pieces_touchees = set()
    for eid in echeance_ids:
        s = conn.execute("SELECT COALESCE(SUM(montant_cents),0) s FROM gc_reglements_affectations WHERE echeance_id=?",
                         (eid,)).fetchone()["s"]
        conn.execute("UPDATE gc_echeances SET regle_cents=? WHERE id=?", (int(s), eid))
        pieces_touchees.add(conn.execute("SELECT piece_id FROM gc_echeances WHERE id=?", (eid,)).fetchone()["piece_id"])
    for pid in pieces_touchees:
        r = conn.execute(
            "SELECT SUM(montant_cents) m, SUM(regle_cents) r FROM gc_echeances WHERE piece_id=?", (pid,)).fetchone()
        statut = "solde" if int(r["r"] or 0) >= int(r["m"] or 0) else ("partiel" if int(r["r"] or 0) > 0 else "valide")
        conn.execute("UPDATE gc_pieces SET statut=?, modifie_le=? WHERE id=? AND statut IN ('valide','partiel','solde')",
                     (statut, _maintenant(), pid))


def enregistrer_reglement(conn, data: dict, user: dict | None = None) -> int:
    try:
        tiers_id = int(data.get("tiers_id") or 0)
        montant = int(data.get("montant_cents") or 0)
    except (TypeError, ValueError):
        raise ErreurPiece("Montant ou tiers invalide.") from None
    if montant <= 0:
        raise ErreurPiece("Montant du règlement : supérieur à zéro.")
    if not conn.execute("SELECT 1 FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone():
        raise ErreurPiece("Tiers introuvable.")
    sens = data.get("sens") or "encaissement"
    if sens not in ("encaissement", "decaissement"):
        raise ErreurPiece("Sens : encaissement ou décaissement.")
    if not data.get("date_reglement"):
        raise ErreurPiece("Date du règlement obligatoire.")
    affectations = data.get("affectations") or []
    total = 0
    touchees = set()
    lignes = []
    for a in affectations:
        m = int(a.get("montant_cents") or 0)
        if m == 0:
            continue
        if m < 0:
            raise ErreurPiece("Affectation négative.")
        e = conn.execute(
            """SELECT e.id, e.montant_cents, e.regle_cents, p.tiers_id, p.type, p.numero FROM gc_echeances e
               JOIN gc_pieces p ON p.id=e.piece_id WHERE e.id=?""", (int(a.get("echeance_id") or 0),)).fetchone()
        if not e or e["tiers_id"] != tiers_id:
            raise ErreurPiece("Échéance d'un autre tiers.")
        if SENS_PAR_TYPE.get(e["type"]) != sens:
            raise ErreurPiece(f"{e['numero']} : sens de règlement incohérent.")
        if m > int(e["montant_cents"]) - int(e["regle_cents"]):
            raise ErreurPiece(f"{e['numero']} : l'affectation dépasse le reste dû.")
        total += m
        touchees.add(int(e["id"]))
        lignes.append((int(e["id"]), m))
    if total > montant:
        raise ErreurPiece("Les affectations dépassent le montant du règlement.")
    cur = conn.execute(
        """INSERT INTO gc_reglements (tiers_id, sens, date_reglement, mode_paiement, montant_cents, reference, notes,
               cree_par, cree_le) VALUES (?,?,?,?,?,?,?,?,?)""",
        (tiers_id, sens, data["date_reglement"], data.get("mode_paiement") or None, montant,
         str(data.get("reference") or ""), str(data.get("notes") or ""), str((user or {}).get("nom") or ""), _maintenant()))
    rid = int(cur.lastrowid)
    for eid, m in lignes:
        conn.execute("INSERT INTO gc_reglements_affectations (reglement_id, echeance_id, montant_cents) VALUES (?,?,?)",
                     (rid, eid, m))
    _majs(conn, touchees)
    return rid


def supprimer_reglement(conn, reglement_id: int) -> None:
    if not conn.execute("SELECT 1 FROM gc_reglements WHERE id=?", (reglement_id,)).fetchone():
        raise ErreurPiece("Règlement introuvable.")
    touchees = {r["echeance_id"] for r in conn.execute(
        "SELECT echeance_id FROM gc_reglements_affectations WHERE reglement_id=?", (reglement_id,)).fetchall()}
    conn.execute("DELETE FROM gc_reglements_affectations WHERE reglement_id=?", (reglement_id,))
    conn.execute("DELETE FROM gc_reglements WHERE id=?", (reglement_id,))
    _majs(conn, touchees)


def reglements(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT r.*, t.raison_sociale AS tiers_nom, t.code AS tiers_code,
                  (SELECT COALESCE(SUM(montant_cents),0) FROM gc_reglements_affectations a WHERE a.reglement_id=r.id) AS affecte_cents,
                  (SELECT GROUP_CONCAT(p.numero, ', ') FROM gc_reglements_affectations a JOIN gc_echeances e ON e.id=a.echeance_id
                     JOIN gc_pieces p ON p.id=e.piece_id WHERE a.reglement_id=r.id) AS factures
           FROM gc_reglements r JOIN gc_tiers t ON t.id=r.tiers_id ORDER BY r.date_reglement DESC, r.id DESC""").fetchall()]
