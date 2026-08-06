"""
Coûts matières : bascule sur l'annuaire fournisseurs de l'entreprise.

Extraite de app/core/database.py (ancienne v226) : une migration par fichier,
identifiée par son NOM, pour que deux chantiers parallèles ne se marchent pas dessus.
"""

NOM = "mc_fournisseurs_annuaire_entreprise"


def appliquer(conn):
    _sup_cols = {r["name"] for r in conn.execute("PRAGMA table_info(mc_supplier)").fetchall()}
    _mat226_cols = {r["name"] for r in conn.execute("PRAGMA table_info(mc_material)").fetchall()}
    if _sup_cols and "fournisseur_fsc_id" not in _sup_cols:
        conn.execute("ALTER TABLE mc_supplier ADD COLUMN fournisseur_fsc_id INTEGER")
    if _mat226_cols and "fournisseur_fsc_id" not in _mat226_cols:
        conn.execute("ALTER TABLE mc_material ADD COLUMN fournisseur_fsc_id INTEGER")

    def _norm226(s):
        import unicodedata

        s = unicodedata.normalize("NFKD", str(s or ""))
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        out = []
        for ch in s:
            out.append(ch if ch.isalnum() else " ")
        # Formes juridiques et initiales isolées ignorées : « JAOUR S.A. »
        # doit retrouver « Jaour ».
        _stop = ("sa", "sas", "sarl", "sasu", "gmbh", "ltd", "bv", "nv", "spa", "srl", "inc")
        mots = [m for m in "".join(out).split() if m not in _stop and len(m) > 1]
        return " ".join(mots) or " ".join("".join(out).split())

    _matched226 = 0
    if _sup_cols and _mat226_cols:
        _fsc = {}
        for _r in conn.execute("SELECT id, nom FROM fournisseurs_fsc").fetchall():
            _fsc.setdefault(_norm226(_r["nom"]), int(_r["id"]))
        for _r in conn.execute(
            "SELECT id, name FROM mc_supplier WHERE fournisseur_fsc_id IS NULL"
        ).fetchall():
            _fid = _fsc.get(_norm226(_r["name"]))
            if _fid:
                conn.execute(
                    "UPDATE mc_supplier SET fournisseur_fsc_id=? WHERE id=?", (_fid, _r["id"])
                )
                _matched226 += 1
        # Report du fournisseur rapproché sur les matières déjà rattachées.
        conn.execute(
            """UPDATE mc_material
                  SET fournisseur_fsc_id = (
                        SELECT s.fournisseur_fsc_id FROM mc_supplier s
                         WHERE s.id = mc_material.supplier_id)
                WHERE fournisseur_fsc_id IS NULL AND supplier_id IS NOT NULL"""
        )
    _unmatched226 = 0
    if _sup_cols:
        _row = conn.execute(
            "SELECT COUNT(*) AS n FROM mc_supplier WHERE fournisseur_fsc_id IS NULL"
        ).fetchone()
        _unmatched226 = int(_row["n"] or 0) if _row else 0
    conn.commit()
