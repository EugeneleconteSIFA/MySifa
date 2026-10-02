"""Variantes fournisseur d'une matière MyStock.

La matière porte le libellé COMMERCIAL (aucune référence). Chaque variante est
une façon de l'acheter : un fournisseur, un article, avec son libellé TECHNIQUE
(les références de colle, de glassine, d'article), sa référence RVGI et sa
longueur de bobine.

Un seul fournisseur principal par matière, et c'est le même que celui de
Coûts matières :

- `definir_principal` (page matière) pose le principal sur la variante puis le
  répercute sur chaque déclinaison qui a un prix chez ce fournisseur, via
  `mystock_prix.set_principal` — donc avec le miroir de valorisation et
  l'historique de prix habituels ;
- `suivre_principal_prix`, appelé par `mystock_prix.set_principal`, fait le
  chemin inverse quand le principal change dans Coûts matières. Il ne fait rien
  si la variante principale a déjà ce fournisseur, ce qui coupe la boucle.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

_CHAMPS_TEXTE = ("libelle_technique", "ref_fournisseur", "note")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _norm_txt(v: Any) -> Optional[str]:
    s = str(v or "").strip()
    return s or None


def _norm_float(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        f = float(str(v).replace(",", ".").replace(" ", "").replace(" ", ""))
    except (TypeError, ValueError):
        raise ValueError("Longueur de bobine invalide — nombre de mètres attendu.")
    if f < 0:
        raise ValueError("Longueur de bobine invalide — valeur positive attendue.")
    return f or None


def _parse_ref_rvgi(ref: Any) -> tuple[Optional[str], Optional[str]]:
    """« 1183/0004 » -> ("1183", "0004"). Vide -> (None, None)."""
    s = str(ref or "").strip()
    if not s:
        return None, None
    if "/" not in s:
        raise ValueError("Référence RVGI invalide — format attendu 1183/0004.")
    a, b = (x.strip() for x in s.split("/", 1))
    if not a or not b:
        raise ValueError("Référence RVGI invalide — format attendu 1183/0004.")
    return a, b


def types_rvgi(conn: sqlite3.Connection) -> list[dict]:
    """Types d'article RVGI proposés pour une variante (référentiel erp_type_famille)."""
    return [
        {"type_code": r["type_code"], "libelle": r["libelle_secours"] or ("Type %d" % r["type_code"]),
         "famille": r["famille"]}
        for r in conn.execute(
            """SELECT type_code, famille, libelle_secours FROM erp_type_famille
                WHERE famille IN ('matiere','consommable') ORDER BY type_code"""
        ).fetchall()
    ]


def _fournisseur_par_numero_rvgi(conn: sqlite3.Connection, code1: Optional[str]) -> Optional[int]:
    """Le code1 d'un article RVGI est le numéro du fournisseur (1 = article générique)."""
    if not code1 or not str(code1).isdigit() or str(code1) == "1":
        return None
    from app.services.fournisseurs_fusion import par_numero_rvgi
    return par_numero_rvgi(conn, code1)


def _dernier_achat(refs: list[tuple[str, str, int]]) -> dict:
    """Date et nombre de commandes RVGI par article, lus dans le miroir. Vide si absent."""
    if not refs:
        return {}
    try:
        from app.services import erp_mirror as miroir
        if not miroir.miroir_present():
            return {}
        out = {}
        with miroir.get_erp_db() as erp:
            for c1, c2, t in refs:
                r = erp.execute(
                    """SELECT MAX(substr(e.amjc,1,10)) AS d, COUNT(DISTINCT e.numero) AS n
                         FROM cdf_ligne l
                         JOIN cdf_entete e ON e.numero = l.numero AND e.corbeille = 0
                        WHERE l.corbeille = 0 AND l.code1 = ? AND l.code2 = ? AND l.type = ?
                          AND substr(e.amjc,1,10) <= date('now')""",
                    (c1, c2, t),
                ).fetchone()
                if r and r["n"]:
                    out[(c1, c2, t)] = {"date": r["d"], "commandes": r["n"]}
        return out
    except Exception:
        # Miroir illisible ou schéma inattendu : la page perd la colonne, pas plus.
        return {}


def lister(conn: sqlite3.Connection, matiere_id: int, avec_inactives: bool = False) -> dict:
    mp = conn.execute(
        "SELECT id, reference, designation, categorie FROM matieres_premieres WHERE id=?",
        (matiere_id,),
    ).fetchone()
    if not mp:
        raise LookupError("Matière non trouvée.")
    rows = conn.execute(
        f"""SELECT v.*, f.nom AS fournisseur_nom
              FROM mp_variantes v
              LEFT JOIN fournisseurs_fsc f ON f.id = v.fournisseur_id
             WHERE v.matiere_id = ? {'' if avec_inactives else 'AND v.actif = 1'}
             ORDER BY v.actif DESC, v.principal DESC, f.nom COLLATE NOCASE, v.id""",
        (matiere_id,),
    ).fetchall()

    # Laizes livrées par fournisseur, et laizes où ce fournisseur a un prix.
    laizes_fou: dict[Optional[int], list[str]] = {}
    for r in conn.execute(
        """SELECT mlf.fournisseur_id, l.valeur_mm, l.label
             FROM matiere_laize_fournisseurs mlf JOIN mp_laizes l ON l.id = mlf.laize_id
            WHERE mlf.matiere_id = ? ORDER BY l.valeur_mm""",
        (matiere_id,),
    ).fetchall():
        laizes_fou.setdefault(r["fournisseur_id"], []).append(r["label"] or "%g mm" % r["valeur_mm"])
    decls = conn.execute(
        """SELECT d.id, d.laize_id, d.grammage_id, l.valeur_mm, l.label AS laize_label,
                  g.valeur_gsm, g.label AS grammage_label
             FROM mp_matiere_declinaison d
             LEFT JOIN mp_laizes l ON l.id = d.laize_id
             LEFT JOIN mp_grammages g ON g.id = d.grammage_id
            WHERE d.matiere_id = ?""",
        (matiere_id,),
    ).fetchall()
    prix = conn.execute(
        """SELECT p.declinaison_id, p.fournisseur_id, p.principal FROM mp_matiere_prix p
            WHERE p.matiere_id = ?""",
        (matiere_id,),
    ).fetchall()
    prix_fou: dict[Optional[int], set] = {}
    principal_decl: dict[int, Optional[int]] = {}
    for p in prix:
        prix_fou.setdefault(p["fournisseur_id"], set()).add(p["declinaison_id"])
        if p["principal"]:
            principal_decl[p["declinaison_id"]] = p["fournisseur_id"]

    achats = _dernier_achat([
        (r["rvgi_code1"], r["rvgi_code2"], int(r["rvgi_type_code"]))
        for r in rows if r["rvgi_code1"] and r["rvgi_type_code"] is not None
    ])

    variantes = []
    for r in rows:
        key = (r["rvgi_code1"], r["rvgi_code2"], int(r["rvgi_type_code"])) if r["rvgi_code1"] and r["rvgi_type_code"] is not None else None
        variantes.append({
            "id": r["id"],
            "fournisseur_id": r["fournisseur_id"],
            "fournisseur_nom": r["fournisseur_nom"] or "",
            "libelle_technique": r["libelle_technique"],
            "ref_fournisseur": r["ref_fournisseur"] or "",
            "ref_rvgi": f"{r['rvgi_code1']}/{r['rvgi_code2']}" if r["rvgi_code1"] else "",
            "rvgi_type_code": r["rvgi_type_code"],
            "ml_bobine": r["ml_bobine"],
            "principal": bool(r["principal"]),
            "actif": bool(r["actif"]),
            "note": r["note"] or "",
            "laizes": laizes_fou.get(r["fournisseur_id"], []) if r["fournisseur_id"] else [],
            "declinaisons_avec_prix": len(prix_fou.get(r["fournisseur_id"], set())) if r["fournisseur_id"] else 0,
            "dernier_achat": (achats.get(key) or {}).get("date") if key else None,
            "commandes_rvgi": (achats.get(key) or {}).get("commandes") if key else None,
            "updated_at": r["updated_at"] or r["created_at"],
            "updated_by_name": r["updated_by_name"] or r["created_by_name"] or "",
        })

    # Déclinaisons dont le prix en vigueur n'est pas chez le fournisseur principal.
    princ = next((v for v in variantes if v["principal"] and v["actif"]), None)
    ecarts = []
    if princ and princ["fournisseur_id"]:
        for d in decls:
            fp = principal_decl.get(d["id"])
            if d["id"] not in prix_fou.get(princ["fournisseur_id"], set()):
                etat = "sans_prix"
            elif fp != princ["fournisseur_id"]:
                etat = "autre_principal"
            else:
                continue
            ecarts.append({
                "declinaison_id": d["id"],
                "libelle": d["laize_label"] or (("%g mm" % d["valeur_mm"]) if d["valeur_mm"] else None)
                           or d["grammage_label"] or (("%g g/m²" % d["valeur_gsm"]) if d["valeur_gsm"] else "Sans déclinaison"),
                "etat": etat,
            })
    return {
        "matiere": {"id": mp["id"], "reference": mp["reference"], "designation": mp["designation"],
                    "categorie": mp["categorie"]},
        "variantes": variantes,
        "ecarts_prix": ecarts,
    }


def _valider(conn: sqlite3.Connection, data: dict, existante: Optional[sqlite3.Row] = None) -> dict:
    out: dict[str, Any] = {}
    if "libelle_technique" in data or existante is None:
        lib = _norm_txt(data.get("libelle_technique"))
        if not lib:
            raise ValueError("Libellé technique obligatoire.")
        out["libelle_technique"] = lib
    for c in ("ref_fournisseur", "note"):
        if c in data:
            out[c] = _norm_txt(data.get(c))
    if "fournisseur_id" in data:
        fid = data.get("fournisseur_id")
        if fid in (None, "", 0, "0"):
            out["fournisseur_id"] = None
        else:
            try:
                fid = int(fid)
            except (TypeError, ValueError):
                raise ValueError("Fournisseur invalide.") from None
            if not conn.execute("SELECT 1 FROM fournisseurs_fsc WHERE id=?", (fid,)).fetchone():
                raise ValueError("Fournisseur inconnu.")
            out["fournisseur_id"] = fid
    if "ml_bobine" in data:
        out["ml_bobine"] = _norm_float(data.get("ml_bobine"))
    if "ref_rvgi" in data:
        c1, c2 = _parse_ref_rvgi(data.get("ref_rvgi"))
        out["rvgi_code1"], out["rvgi_code2"] = c1, c2
        if c1:
            try:
                t = int(data.get("rvgi_type_code"))
            except (TypeError, ValueError):
                raise ValueError("Type d'article RVGI obligatoire avec une référence RVGI.") from None
            out["rvgi_type_code"] = t
        else:
            out["rvgi_type_code"] = None
    return out


def _rvgi_libre(conn, c1, c2, t, sauf_id=None, matiere_id=None) -> None:
    if not c1:
        return
    r = conn.execute(
        """SELECT v.id, v.matiere_id, m.reference FROM mp_variantes v
             JOIN matieres_premieres m ON m.id = v.matiere_id
            WHERE v.rvgi_code1=? AND v.rvgi_code2=? AND v.rvgi_type_code=? AND v.actif=1
              AND v.id <> COALESCE(?, 0)""",
        (c1, c2, t, sauf_id),
    ).fetchone()
    if r:
        if matiere_id is not None and r["matiere_id"] == matiere_id:
            raise ValueError("L'article RVGI %s/%s est déjà rattaché à un fournisseur de cette matière." % (c1, c2))
        raise ValueError("L'article RVGI %s/%s est déjà rattaché à une autre matière (%s)."
                         % (c1, c2, r["reference"]))


def _sync_erp(conn, variante_id: int, matiere_id: int, c1, c2, t, auteur) -> None:
    """L'article RVGI d'une variante est apparié à sa matière, et pointe la variante."""
    conn.execute("UPDATE erp_article_matiere SET variante_id=NULL WHERE variante_id=?", (variante_id,))
    if not c1:
        return
    conn.execute(
        """INSERT INTO erp_article_matiere
               (code1, code2, type_code, matiere_id, variante_id, origine, created_at, created_by_name)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(code1, code2, type_code) DO UPDATE SET
               matiere_id = excluded.matiere_id, variante_id = excluded.variante_id""",
        (c1, c2, t, matiere_id, variante_id, "variante", _now(), auteur or ""),
    )


def creer(conn: sqlite3.Connection, matiere_id: int, data: dict, auteur: Optional[str]) -> int:
    if not conn.execute("SELECT 1 FROM matieres_premieres WHERE id=? AND actif=1", (matiere_id,)).fetchone():
        raise LookupError("Matière non trouvée.")
    v = _valider(conn, data)
    if not v.get("fournisseur_id") and "fournisseur_id" not in v:
        v["fournisseur_id"] = _fournisseur_par_numero_rvgi(conn, v.get("rvgi_code1"))
    _rvgi_libre(conn, v.get("rvgi_code1"), v.get("rvgi_code2"), v.get("rvgi_type_code"), matiere_id=matiere_id)
    # Une variante provisoire de ce fournisseur (créée depuis un prix ou par la
    # reprise, sans référence) se complète au lieu d'être doublée. Reconnue à
    # sa note d'origine : son libellé est l'ancienne désignation, qui ne
    # correspond plus une fois la fiche renommée.
    if v.get("fournisseur_id"):
        prov = conn.execute(
            """SELECT v.id FROM mp_variantes v JOIN matieres_premieres m ON m.id = v.matiere_id
                WHERE v.matiere_id=? AND v.fournisseur_id=? AND v.actif=1
                  AND v.rvgi_code1 IS NULL AND v.ref_fournisseur IS NULL
                  AND (v.libelle_technique IN (COALESCE(m.designation,''), COALESCE(m.reference,''), 'À compléter')
                       OR v.note LIKE 'Reprise des prix fournisseur%'
                       OR v.note LIKE 'Créée depuis un prix%'
                       OR v.note LIKE 'Créée au choix%')
                ORDER BY v.principal DESC, v.id LIMIT 1""",
            (matiere_id, v["fournisseur_id"]),
        ).fetchone()
        if prov:
            data = dict(data)
            data.setdefault("note", None)
            modifier(conn, prov["id"], data, auteur)
            return int(prov["id"])
    premiere = not conn.execute(
        "SELECT 1 FROM mp_variantes WHERE matiere_id=? AND actif=1", (matiere_id,)
    ).fetchone()
    if premiere:
        # Première variante : principale, sauf si Coûts matières a déjà un
        # principal chez un autre fournisseur (on ne crée pas deux vérités).
        fps = {r[0] for r in conn.execute(
            "SELECT DISTINCT fournisseur_id FROM mp_matiere_prix WHERE matiere_id=? AND principal=1",
            (matiere_id,),
        ).fetchall()} - {None}
        premiere = not fps or v.get("fournisseur_id") in fps
    cols = ["matiere_id", "principal", "actif", "created_at", "created_by_name"] + list(v)
    vals = [matiere_id, 1 if premiere else 0, 1, _now(), auteur] + list(v.values())
    vid = conn.execute(
        "INSERT INTO mp_variantes (%s) VALUES (%s)" % (",".join(cols), ",".join("?" * len(cols))), vals
    ).lastrowid
    _sync_erp(conn, vid, matiere_id, v.get("rvgi_code1"), v.get("rvgi_code2"), v.get("rvgi_type_code"), auteur)
    return int(vid)


def _get(conn, variante_id: int) -> sqlite3.Row:
    r = conn.execute("SELECT * FROM mp_variantes WHERE id=?", (variante_id,)).fetchone()
    if not r:
        raise LookupError("Variante introuvable.")
    return r


def modifier(conn: sqlite3.Connection, variante_id: int, data: dict, auteur: Optional[str]) -> sqlite3.Row:
    r = _get(conn, variante_id)
    v = _valider(conn, data, r)
    if "rvgi_code1" in v:
        _rvgi_libre(conn, v["rvgi_code1"], v["rvgi_code2"], v["rvgi_type_code"], sauf_id=variante_id,
                    matiere_id=r["matiere_id"])
    if v.get("fournisseur_id") != r["fournisseur_id"] and "fournisseur_id" in v and r["principal"]:
        raise ValueError("Changer le fournisseur de la variante principale déplacerait le prix en vigueur. "
                         "Choisir d'abord un autre fournisseur principal.")
    if v:
        v["updated_at"], v["updated_by_name"] = _now(), auteur
        conn.execute(
            "UPDATE mp_variantes SET %s WHERE id=?" % ", ".join(f"{k}=?" for k in v),
            list(v.values()) + [variante_id],
        )
        if "rvgi_code1" in v:
            _sync_erp(conn, variante_id, r["matiere_id"], v["rvgi_code1"], v["rvgi_code2"],
                      v["rvgi_type_code"], auteur)
    return _get(conn, variante_id)


def desactiver(conn: sqlite3.Connection, variante_id: int, auteur: Optional[str]) -> sqlite3.Row:
    r = _get(conn, variante_id)
    if r["principal"] and r["actif"]:
        autres = conn.execute(
            "SELECT COUNT(*) FROM mp_variantes WHERE matiere_id=? AND actif=1 AND id<>?",
            (r["matiere_id"], variante_id),
        ).fetchone()[0]
        if autres:
            raise ValueError("Variante principale : choisir d'abord un autre fournisseur principal.")
    conn.execute(
        "UPDATE mp_variantes SET actif=0, principal=0, updated_at=?, updated_by_name=? WHERE id=?",
        (_now(), auteur, variante_id),
    )
    conn.execute("UPDATE erp_article_matiere SET variante_id=NULL WHERE variante_id=?", (variante_id,))
    return _get(conn, variante_id)


def reactiver(conn: sqlite3.Connection, variante_id: int, auteur: Optional[str]) -> sqlite3.Row:
    r = _get(conn, variante_id)
    _rvgi_libre(conn, r["rvgi_code1"], r["rvgi_code2"], r["rvgi_type_code"], sauf_id=variante_id,
                matiere_id=r["matiere_id"])
    conn.execute(
        "UPDATE mp_variantes SET actif=1, updated_at=?, updated_by_name=? WHERE id=?",
        (_now(), auteur, variante_id),
    )
    _sync_erp(conn, variante_id, r["matiere_id"], r["rvgi_code1"], r["rvgi_code2"], r["rvgi_type_code"], auteur)
    return _get(conn, variante_id)


def _poser_principal(conn, matiere_id: int, variante_id: int, auteur: Optional[str]) -> None:
    conn.execute("UPDATE mp_variantes SET principal=0 WHERE matiere_id=? AND principal=1", (matiere_id,))
    conn.execute(
        "UPDATE mp_variantes SET principal=1, updated_at=?, updated_by_name=? WHERE id=?",
        (_now(), auteur, variante_id),
    )


def definir_principal(
    conn: sqlite3.Connection, variante_id: int, *, user_id: Optional[int] = None,
    user_name: Optional[str] = None,
) -> dict:
    """Pose le principal sur la variante, et le prix en vigueur suit dans Coûts matières."""
    from app.services import mystock_prix

    r = _get(conn, variante_id)
    if not r["actif"]:
        raise ValueError("Variante désactivée : la réactiver avant d'en faire le fournisseur principal.")
    _poser_principal(conn, r["matiere_id"], variante_id, user_name)
    suivies, sans_prix = [], []
    fid = r["fournisseur_id"]
    for d in conn.execute(
        """SELECT d.id, l.label, l.valeur_mm, g.label AS g_label, g.valeur_gsm
             FROM mp_matiere_declinaison d
             LEFT JOIN mp_laizes l ON l.id = d.laize_id
             LEFT JOIN mp_grammages g ON g.id = d.grammage_id
            WHERE d.matiere_id = ?""",
        (r["matiere_id"],),
    ).fetchall():
        lib = d["label"] or (("%g mm" % d["valeur_mm"]) if d["valeur_mm"] else None) \
            or d["g_label"] or (("%g g/m²" % d["valeur_gsm"]) if d["valeur_gsm"] else "sans déclinaison")
        # Un prix à 0 veut dire « non renseigné » : il ne devient pas le prix
        # en vigueur (il pousserait 0 dans la valorisation).
        a_prix = fid is not None and conn.execute(
            "SELECT 1 FROM mp_matiere_prix WHERE declinaison_id=? AND fournisseur_id=? AND prix > 0",
            (d["id"], fid),
        ).fetchone()
        if not a_prix:
            sans_prix.append(lib)
            continue
        res = mystock_prix.set_principal(
            conn, declinaison_id=d["id"], fournisseur_id=fid, user_id=user_id, user_name=user_name,
            origine="MyStock — fiche matière",
        )
        if res.get("ok"):
            suivies.append(lib)
    return {"ok": True, "declinaisons_suivies": suivies, "declinaisons_sans_prix": sans_prix}


def _assurer_variante(conn: sqlite3.Connection, matiere_id: int, fournisseur_id: int,
                      auteur: Optional[str]) -> int:
    """La variante active de ce fournisseur pour cette matière, créée au besoin."""
    v = conn.execute(
        """SELECT id FROM mp_variantes WHERE matiere_id=? AND fournisseur_id=? AND actif=1
            ORDER BY principal DESC, (rvgi_code1 IS NULL), id LIMIT 1""",
        (matiere_id, fournisseur_id),
    ).fetchone()
    if v:
        return int(v["id"])
    m = conn.execute("SELECT designation, reference FROM matieres_premieres WHERE id=?", (matiere_id,)).fetchone()
    return int(conn.execute(
        """INSERT INTO mp_variantes (matiere_id, fournisseur_id, libelle_technique, principal, actif,
                                     created_at, created_by_name, note)
           VALUES (?,?,?,0,1,?,?,?)""",
        (matiere_id, fournisseur_id, (m["designation"] or m["reference"] or "").strip() or "À compléter",
         _now(), auteur or "Coûts matières",
         "Créée depuis un prix fournisseur de Coûts matières : libellé technique à compléter."),
    ).lastrowid)


def suivre_prix_declinaison(conn: sqlite3.Connection, declinaison_id: int, auteur: Optional[str] = None,
                            *, principal_explicite: bool = False) -> None:
    """Coûts matières a écrit sur une déclinaison.

    Tout fournisseur qui y a un prix a sa variante sur la page matière. La
    variante principale ne suit le principal de la déclinaison que sur un choix
    EXPLICITE (`set_principal`), ou si la matière n'en a encore aucune : saisir
    un prix sur une laize que le fournisseur principal ne livre pas ne doit pas
    faire basculer toute la matière.
    """
    d = conn.execute("SELECT matiere_id FROM mp_matiere_declinaison WHERE id=?", (declinaison_id,)).fetchone()
    if not d:
        return
    mid = d["matiere_id"]
    fp = None
    for r in conn.execute(
        """SELECT fournisseur_id, principal FROM mp_matiere_prix
            WHERE declinaison_id=? AND fournisseur_id IS NOT NULL""",
        (declinaison_id,),
    ).fetchall():
        vid = _assurer_variante(conn, mid, r["fournisseur_id"], auteur)
        if r["principal"]:
            fp = (r["fournisseur_id"], vid)
    if not fp:
        return
    princ = conn.execute(
        "SELECT id, fournisseur_id FROM mp_variantes WHERE matiere_id=? AND principal=1 AND actif=1", (mid,)
    ).fetchone()
    if princ and (princ["fournisseur_id"] == fp[0] or not principal_explicite):
        return
    _poser_principal(conn, mid, fp[1], auteur or "Coûts matières")


def suivre_principal_prix(conn: sqlite3.Connection, declinaison_id: int,
                          fournisseur_id: Optional[int], auteur: Optional[str] = None) -> None:
    """Compatibilité : choix explicite du principal sur une déclinaison."""
    suivre_prix_declinaison(conn, declinaison_id, auteur, principal_explicite=True)


def rattacher_article(conn: sqlite3.Connection, code1: str, code2: str, type_code: int,
                      matiere_id: Optional[int], auteur: Optional[str] = None,
                      libelle: Optional[str] = None) -> Optional[int]:
    """Appariement RVGI -> matière : l'article devient (ou retrouve) une variante de la matière."""
    ancienne = conn.execute(
        "SELECT id FROM mp_variantes WHERE rvgi_code1=? AND rvgi_code2=? AND rvgi_type_code=? AND actif=1",
        (code1, code2, type_code),
    ).fetchone()
    if matiere_id in (None, "", 0):
        if ancienne:
            a = _get(conn, ancienne["id"])
            vide = a["fournisseur_id"] is None and not a["principal"]
            conn.execute(
                "UPDATE mp_variantes SET rvgi_code1=NULL, rvgi_code2=NULL, rvgi_type_code=NULL, "
                "actif=?, updated_at=?, updated_by_name=? WHERE id=?",
                (0 if vide else a["actif"], _now(), auteur, a["id"]),
            )
        return None
    mid = int(matiere_id)
    if ancienne:
        a = _get(conn, ancienne["id"])
        if a["matiere_id"] == mid:
            vid = a["id"]
        else:
            conn.execute(
                "UPDATE mp_variantes SET rvgi_code1=NULL, rvgi_code2=NULL, rvgi_type_code=NULL, "
                "updated_at=?, updated_by_name=? WHERE id=?",
                (_now(), auteur, a["id"]),
            )
            vid = None
    else:
        vid = None
    if vid is None:
        fid = _fournisseur_par_numero_rvgi(conn, code1)
        # Variante de ce fournisseur déjà présente sans article (provisoire,
        # créée depuis un prix) : elle reçoit l'article au lieu d'être doublée.
        if fid is not None:
            prov = conn.execute(
                """SELECT id FROM mp_variantes WHERE matiere_id=? AND fournisseur_id=? AND actif=1
                      AND rvgi_code1 IS NULL ORDER BY principal DESC, id LIMIT 1""",
                (mid, fid),
            ).fetchone()
            if prov:
                vid = int(prov["id"])
                conn.execute(
                    "UPDATE mp_variantes SET rvgi_code1=?, rvgi_code2=?, rvgi_type_code=?, updated_at=?, "
                    "updated_by_name=? WHERE id=?",
                    (code1, code2, int(type_code), _now(), auteur, vid),
                )
    if vid is None:
        fid = _fournisseur_par_numero_rvgi(conn, code1)
        m = conn.execute("SELECT designation, reference FROM matieres_premieres WHERE id=?", (mid,)).fetchone()
        premiere = not conn.execute(
            "SELECT 1 FROM mp_variantes WHERE matiere_id=? AND actif=1", (mid,)
        ).fetchone()
        vid = conn.execute(
            """INSERT INTO mp_variantes (matiere_id, fournisseur_id, libelle_technique, rvgi_code1,
                                         rvgi_code2, rvgi_type_code, principal, actif, created_at,
                                         created_by_name, note)
               VALUES (?,?,?,?,?,?,?,1,?,?,?)""",
            (mid, fid, (libelle or m["designation"] or m["reference"] or "").strip() or "À compléter",
             code1, code2, int(type_code), 1 if premiere else 0, _now(), auteur,
             "Créée à l'appariement RVGI : libellé technique à vérifier."),
        ).lastrowid
    conn.execute(
        "UPDATE erp_article_matiere SET variante_id=? WHERE code1=? AND code2=? AND type_code=?",
        (vid, code1, code2, int(type_code)),
    )
    return int(vid)


def fermer_matiere(conn: sqlite3.Connection, matiere_id: int) -> int:
    """Une matière désactivée ne garde aucune variante active : ses articles RVGI
    sont libérés (une autre matière peut les reprendre) et les appariements ne
    pointent plus sa variante. Renvoie le nombre d'appariements RVGI qui restent
    sur la matière, à signaler : la file de réception les montre « à apparier »."""
    conn.execute(
        "UPDATE mp_variantes SET actif=0, principal=0, updated_at=? WHERE matiere_id=? AND actif=1",
        (_now(), matiere_id),
    )
    conn.execute(
        "UPDATE erp_article_matiere SET variante_id=NULL WHERE matiere_id=?", (matiere_id,)
    )
    return int(conn.execute(
        "SELECT COUNT(*) FROM erp_article_matiere WHERE matiere_id=?", (matiere_id,)
    ).fetchone()[0])


# Une variante provisoire : créée depuis un prix ou par la reprise, sans
# article ni référence, reconnue à sa note d'origine.
_PROVISOIRE = """(v.rvgi_code1 IS NULL AND v.ref_fournisseur IS NULL
                  AND (v.note LIKE 'Reprise des prix fournisseur%'
                       OR v.note LIKE 'Créée depuis un prix%'
                       OR v.note LIKE 'Créée au choix%'))"""


def fusionner_provisoires(conn: sqlite3.Connection, matiere_ids=None) -> int:
    """Fond chaque variante provisoire dans la variante complète du même fournisseur.

    Une provisoire qui a une sœur complète chez le même fournisseur lui passe
    son statut principal s'il le porte, puis est désactivée. Le fournisseur ne
    change pas, donc le prix en vigueur non plus. Ne committe pas.

    Les jumelles naissent de deux façons : la reprise d'inventaire qui renomme
    la fiche avant de créer les variantes (la provisoire n'est plus reconnue
    par son libellé), et la fusion de deux fiches fournisseur (le prix de l'une,
    l'article de l'autre).
    """
    sql = f"""SELECT v.id, v.matiere_id, v.fournisseur_id, v.principal FROM mp_variantes v
               WHERE v.actif = 1 AND v.fournisseur_id IS NOT NULL AND {_PROVISOIRE}"""
    params: list = []
    if matiere_ids is not None:
        ids = [int(m) for m in matiere_ids]
        if not ids:
            return 0
        sql += " AND v.matiere_id IN (%s)" % ",".join("?" * len(ids))
        params = ids
    n = 0
    for pid, mid, fid, principal in conn.execute(sql, params).fetchall():
        soeur = conn.execute(
            f"""SELECT v.id FROM mp_variantes v
                 WHERE v.matiere_id = ? AND v.fournisseur_id = ? AND v.actif = 1 AND v.id <> ?
                   AND NOT {_PROVISOIRE}
                 ORDER BY (v.rvgi_code1 IS NULL), v.id LIMIT 1""",
            (mid, fid, pid),
        ).fetchone()
        if not soeur:
            continue
        if principal:
            conn.execute("UPDATE mp_variantes SET principal = 0 WHERE id = ?", (pid,))
            conn.execute("UPDATE mp_variantes SET principal = 1 WHERE id = ?", (soeur[0],))
        conn.execute(
            """UPDATE mp_variantes SET actif = 0, note = COALESCE(note,'') || ' Fusionnée dans la variante ' || ?
                WHERE id = ?""",
            (soeur[0], pid),
        )
        n += 1
    return n
