"""Cahiers des charges : notes d'un tiers ou d'un article pour une étape de la
chaîne de valeur (RVGI « Cahiers des charges »).

Chaque pièce correspond à une étape ; elle affiche les notes de son tiers et
des articles de ses lignes pour cette étape. Une note « imprimée » sort sur le
document du client ou du fournisseur ; les autres restent internes, sauf sur
les documents internes (ordre d'expédition) qui les reprennent toutes.
"""
from __future__ import annotations

from datetime import datetime

from app.services.gc.pieces import ErreurPiece

ETAPES = {"devis": "Devis", "commande": "Commande", "fabrication": "Fabrication", "livraison": "Livraison",
          "facturation": "Facturation", "achat": "Achat", "reception": "Réception"}
ETAPE_DE_PIECE = {"devis": "devis", "marche": "commande", "commande": "commande", "of": "fabrication",
                  "bl": "livraison", "facture": "facturation", "avoir": "facturation",
                  "aof": "achat", "cde_fournisseur": "achat", "reception": "reception",
                  "facture_fournisseur": "facturation"}
OBJETS = ("tiers", "article")
# Instructions de la fiche client (onglets RVGI) : étape → colonne de gc_tiers.
# Fournisseur (onglets Réception, Stockage, Facturation) : mêmes colonnes,
# l'étape réception lit les instructions « livraison », l'étape achat le stockage.
INSTRUCTIONS = {"livraison": "livraison", "commande": "stockage", "facturation": "facturation",
                "reception": "livraison", "achat": "stockage"}
LIBELLES_INSTRUCTIONS = {"livraison": "Livraison", "stockage": "Stockage", "facturation": "Facturation"}


def lister(conn, objet: str, objet_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, etape, texte, imprime, rang FROM gc_cahiers WHERE objet=? AND objet_id=? ORDER BY rang, id",
        (objet, int(objet_id))).fetchall()]


def enregistrer(conn, objet: str, objet_id: int, lignes: list, user: dict | None = None) -> None:
    """Remplace les notes de l'objet par `lignes` ([{etape, texte, imprime}])."""
    if objet not in OBJETS:
        raise ErreurPiece("Objet de cahier des charges inconnu.")
    table = "gc_tiers" if objet == "tiers" else "gc_articles"
    if not conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (int(objet_id),)).fetchone():
        raise ErreurPiece("Fiche introuvable.")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute("DELETE FROM gc_cahiers WHERE objet=? AND objet_id=?", (objet, int(objet_id)))
    for i, l in enumerate(lignes or [], start=1):
        texte = str(l.get("texte") or "").strip()
        if not texte:
            continue
        if l.get("etape") not in ETAPES:
            raise ErreurPiece(f"Ligne {i} : étape invalide.")
        conn.execute(
            """INSERT INTO gc_cahiers (objet, objet_id, etape, texte, imprime, rang, cree_par, cree_le, modifie_le)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (objet, int(objet_id), l["etape"], texte, 1 if l.get("imprime") in (True, 1, "1") else 0, i,
             str((user or {}).get("nom") or ""), now, now))


def pour_piece(conn, piece_id: int, etape: str | None = None) -> list[dict]:
    """Notes applicables à la pièce : son tiers puis les articles de ses lignes."""
    p = conn.execute("SELECT type, tiers_id FROM gc_pieces WHERE id=?", (piece_id,)).fetchone()
    if not p:
        return []
    etape = etape or ETAPE_DE_PIECE.get(p["type"])
    if not etape:
        return []
    out = []
    if etape in INSTRUCTIONS:
        col = INSTRUCTIONS[etape]
        t = conn.execute(f"SELECT raison_sociale, instr_{col}_interne AS i, instr_{col}_externe AS x FROM gc_tiers WHERE id=?",
                         (p["tiers_id"],)).fetchone()
        src = f"{t['raison_sociale']} (instructions de {LIBELLES_INSTRUCTIONS[col].lower()})" if t else ""
        for texte, imprime in ((t["i"] if t else None, 0), (t["x"] if t else None, 1)):
            if texte and texte.strip():
                out.append({"texte": texte.strip(), "imprime": imprime, "etape": etape, "source": src})
    out += [dict(r, source=r["src"]) for r in conn.execute(
        """SELECT c.texte, c.imprime, c.etape, t.raison_sociale AS src FROM gc_cahiers c JOIN gc_tiers t ON t.id=c.objet_id
           WHERE c.objet='tiers' AND c.objet_id=? AND c.etape=? ORDER BY c.rang""", (p["tiers_id"], etape)).fetchall()]
    out += [dict(r, source=r["src"]) for r in conn.execute(
        """SELECT c.texte, c.imprime, c.etape, a.code AS src FROM gc_cahiers c JOIN gc_articles a ON a.id=c.objet_id
           WHERE c.objet='article' AND c.etape=?
             AND c.objet_id IN (SELECT DISTINCT article_id FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL)
           ORDER BY a.code, c.rang""", (etape, piece_id)).fetchall()]
    for d in out:
        d.pop("src", None)
    return out
