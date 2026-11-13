"""MyAO — régénère les PJ auto (fiche fournisseur + BAT) des AO ouverts.

Jusqu'ici une PJ auto était générée une fois puis figée, et la duplication
d'un AO recopiait celles de l'original : des AO partaient avec un ancien
modèle de fiche. On retire les PJ auto des AO encore ouverts (brouillon,
envoyée) ; elles sont régénérées au modèle actuel à la prochaine ouverture de
l'onglet Documents, côté MySifa comme côté portail fournisseur.

Les AO clôturés gardent leurs documents : c'est ce qui a été envoyé.
"""

import os

NOM = "ao_pj_auto_regen"

_KINDS = ("auto-fiche-produit", "auto-bat-produit")
_PREFIXES = ("fiche_fournisseur_", "bat_")


def appliquer(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if not {"ao_pieces_jointes", "ao_demandes"} <= tables:
        return
    try:
        from config import UPLOAD_DIR
    except Exception:
        UPLOAD_DIR = None

    rows = conn.execute(
        """SELECT pj.id, pj.ao_id, pj.filename, pj.stored_name, pj.uploaded_by
           FROM ao_pieces_jointes pj
           JOIN ao_demandes d ON d.id = pj.ao_id
           WHERE pj.ao_fournisseur_id IS NULL
             AND d.statut IN ('brouillon', 'envoyee')""").fetchall()
    n = 0
    for r in rows:
        kind = str(r[4] or "")
        name = str(r[2] or "")
        if kind not in _KINDS and not name.startswith(_PREFIXES):
            continue
        if UPLOAD_DIR and r[3]:
            try:
                path = os.path.join(UPLOAD_DIR, "ao", str(r[1]), str(r[3]))
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass
        conn.execute("DELETE FROM ao_pieces_jointes WHERE id=?", (r[0],))
        n += 1
    conn.commit()
    print(f"[MySifa] migration ao_pj_auto_regen : {n} PJ auto retirée(s), régénérées à la prochaine ouverture.")
