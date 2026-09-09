"""La bobine comme objet de stock — creation, consommation, controle.

Ce module tient `stock_bobines`. Il ne touche JAMAIS a `mp_stock_laize` ni a
`mp_mouvements` : le compteur a deja son chemin canonique
(`stock.appliquer_mouvement_mp`) et deux chemins d'ecriture vers le meme stock
finissent toujours par diverger. Ici on tient l'inventaire des objets ; ailleurs
on tient le compteur ; et `coherence()` dit quand les deux ne se racontent plus
la meme histoire.

Trois regles qui viennent des donnees, pas d'un principe
-------------------------------------------------------
1. **Un scan qui arrive apres coup RATTACHE, il n'ajoute jamais.** Arbitrage du
   04/09/2026. Une bobine entree par packing list puis scannee au magasin est la
   MEME bobine : `creer()` la reconnait a son code-barres et complete ce qui
   manquait, sans creer de seconde ligne et sans toucher au compteur.

2. **Un metrage inconnu vaut NULL, jamais zero.** Une somme qui traite l'inconnu
   comme du vide sort un stock reel sous-estime sans rien signaler. Toutes les
   fonctions de ce module rendent le nombre de bobines sans metrage a cote de la
   somme, pour que l'ecran puisse dire « 214 000 m + 3 bobines de metrage
   inconnu » plutot qu'un chiffre faux.

3. **Le metrage de la packing list prime sur le standard matiere.** Releve sur
   la liste PZH260486 (49 bobines, une seule reference) : les longueurs vont de
   17 700 a 18 200 m. Le standard `metres_lineaires_par_bobine` aurait efface
   2,5 % d'ecart -- exactement ce qu'un stock reel sert a montrer. D'ou
   `metrage_origine`, qui dit toujours d'ou vient le chiffre affiche.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# Etats possibles d'une bobine. Volontairement trois, pas huit : chaque etat
# supplementaire est un etat que quelqu'un devra poser a la main.
ETAT_STOCK = "stock"
ETAT_CONSOMMEE = "consommee"
ETAT_REBUT = "rebut"
ETATS = (ETAT_STOCK, ETAT_CONSOMMEE, ETAT_REBUT)

# D'ou vient le metrage porte par la bobine, du plus sur au moins sur.
ORIGINE_LISTE = "packing_list"   # la liste du fournisseur, bobine par bobine
ORIGINE_SAISIE = "saisie"        # un humain l'a mesure ou corrige
ORIGINE_STANDARD = "standard"    # matieres_premieres.metres_lineaires_par_bobine
ORIGINES = (ORIGINE_LISTE, ORIGINE_SAISIE, ORIGINE_STANDARD)

# Sources de creation — repond a « comment cette bobine est-elle entree ».
SOURCE_SCAN = "scan"
SOURCE_LISTE = "liste"
SOURCE_ERP = "erp"
SOURCE_SAISIE = "saisie"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _f(v) -> Optional[float]:
    try:
        f = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def normaliser_code(code) -> str:
    """Forme retenue d'un code-barres : sans espaces de bord, en majuscules.

    Les douchettes ajoutent parfois un espace ou un retour ligne, et le meme
    code tape a la main revient en minuscules. Sans normalisation, la meme
    bobine entre deux fois et le stock double.
    """
    return str(code or "").strip().upper()


# ── Metrage ──────────────────────────────────────────────────────────────────

def metrage_standard(conn: sqlite3.Connection, matiere_id: Optional[int]) -> Optional[float]:
    """Metrage de reference d'une bobine de cette matiere, ou None."""
    if not matiere_id:
        return None
    row = conn.execute(
        "SELECT metres_lineaires_par_bobine FROM matieres_premieres WHERE id=?",
        (matiere_id,),
    ).fetchone()
    return _f(row["metres_lineaires_par_bobine"]) if row else None


def _resoudre_metrage(conn, matiere_id, metrage, origine) -> tuple:
    """(metrage, origine) apres repli sur le standard matiere."""
    m = _f(metrage)
    if m is not None:
        return m, (origine if origine in ORIGINES else ORIGINE_SAISIE)
    std = metrage_standard(conn, matiere_id)
    if std is not None:
        return std, ORIGINE_STANDARD
    return None, None


# ── Creation et rattachement ─────────────────────────────────────────────────

def lire(conn: sqlite3.Connection, code_barre: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM stock_bobines WHERE code_barre=?", (normaliser_code(code_barre),)
    ).fetchone()


def creer(
    conn: sqlite3.Connection,
    *,
    code_barre: str,
    matiere_id: Optional[int] = None,
    laize_id: Optional[int] = None,
    reception_id: Optional[int] = None,
    lot_fournisseur: Optional[str] = None,
    metrage: Optional[float] = None,
    metrage_origine: Optional[str] = None,
    source: str = SOURCE_SCAN,
    auteur: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Cree la bobine, ou COMPLETE celle qui porte deja ce code-barres.

    Ne commit pas : l'appelant maitrise sa transaction, comme partout ailleurs
    dans MyStock.

    Rend `{"id", "cree", "rattachee", "code_barre", "note"}`. `rattachee` a
    True veut dire que le code existait deja : l'appelant NE DOIT PAS compter
    une entree de stock de plus. C'est la regle du 04/09 — un scan tardif
    rattache, il n'ajoute pas.
    """
    code = normaliser_code(code_barre)
    if not code:
        raise ValueError("Code-barres vide.")
    if source not in (SOURCE_SCAN, SOURCE_LISTE, SOURCE_ERP, SOURCE_SAISIE):
        raise ValueError("Source de creation inconnue : %r" % source)

    metrage, origine = _resoudre_metrage(conn, matiere_id, metrage, metrage_origine)
    now = _now()
    existante = lire(conn, code)

    if existante is not None:
        # On complete ce qui manque, on n'ecrase rien. Un metrage de packing
        # list peut en revanche remplacer un metrage standard : il est plus sur,
        # et c'est la seule remontee en qualite qu'on s'autorise ici.
        maj: List[str] = []
        args: List[Any] = []

        def _completer(colonne, valeur):
            if valeur is not None and existante[colonne] is None:
                maj.append("%s=?" % colonne)
                args.append(valeur)

        _completer("matiere_id", matiere_id)
        _completer("laize_id", laize_id)
        _completer("reception_id", reception_id)
        _completer("lot_fournisseur", lot_fournisseur)

        remplace_metrage = (
            metrage is not None
            and origine == ORIGINE_LISTE
            and existante["metrage_origine"] != ORIGINE_LISTE
        )
        if existante["metrage_initial"] is None or remplace_metrage:
            if metrage is not None:
                maj += ["metrage_initial=?", "metrage_origine=?"]
                args += [metrage, origine]
                # Le restant ne se recale que sur une bobine intacte : sur une
                # bobine deja entamee, remonter le restant inventerait de la
                # matiere qui n'existe pas.
                if existante["metrage_restant"] is None or (
                    existante["metrage_initial"] is not None
                    and float(existante["metrage_restant"] or 0)
                    >= float(existante["metrage_initial"])
                ):
                    maj.append("metrage_restant=?")
                    args.append(metrage)

        note_rattachement = "Code deja connu — bobine rattachee, aucune entree de stock."
        if maj:
            maj.append("updated_at=?")
            args.append(now)
            args.append(existante["id"])
            conn.execute(
                "UPDATE stock_bobines SET %s WHERE id=?" % ", ".join(maj), args
            )
            note_rattachement = "Bobine deja connue — informations completees, aucune entree de stock."

        if matiere_id:
            _marquer_suivi(conn, matiere_id)
        return {"id": int(existante["id"]), "cree": False, "rattachee": True,
                "code_barre": code, "note": note_rattachement}

    cur = conn.execute(
        """INSERT INTO stock_bobines
           (code_barre, matiere_id, laize_id, reception_id, lot_fournisseur,
            metrage_initial, metrage_restant, metrage_origine, etat,
            source, note, created_at, created_by_name, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (code, matiere_id, laize_id, reception_id,
         (lot_fournisseur or None), metrage, metrage, origine, ETAT_STOCK,
         source, (note or None), now, auteur, now),
    )
    if matiere_id:
        _marquer_suivi(conn, matiere_id)
    return {"id": int(cur.lastrowid), "cree": True, "rattachee": False,
            "code_barre": code, "note": None}


def _marquer_suivi(conn: sqlite3.Connection, matiere_id: int) -> None:
    """La matiere est desormais tenue a la bobine — le drapeau enregistre un
    fait accompli, il n'exprime pas une intention (cf. la migration)."""
    conn.execute(
        "UPDATE matieres_premieres SET suivi_bobine=1 WHERE id=? AND suivi_bobine=0",
        (matiere_id,),
    )


def supprimer_de_la_reception(conn: sqlite3.Connection, reception_id: int,
                              codes: Optional[List[str]] = None) -> int:
    """Retire les bobines creees par une reception qu'on annule.

    Seules les bobines ENCORE EN STOCK partent : une bobine deja consommee a
    servi en production, et effacer sa ligne effacerait la seule trace de ce qui
    est parti chez un client. Elle reste, avec sa reception detachee.
    """
    if codes is not None:
        codes_norm = [normaliser_code(c) for c in codes if normaliser_code(c)]
        if not codes_norm:
            return 0
        marques = ",".join("?" for _ in codes_norm)
        cur = conn.execute(
            "DELETE FROM stock_bobines WHERE reception_id=? AND etat=? "
            "AND code_barre IN (%s)" % marques,
            [reception_id, ETAT_STOCK] + codes_norm,
        )
        n = cur.rowcount or 0
        conn.execute(
            "UPDATE stock_bobines SET reception_id=NULL, updated_at=? "
            "WHERE reception_id=? AND etat<>? AND code_barre IN (%s)" % marques,
            [_now(), reception_id, ETAT_STOCK] + codes_norm,
        )
        return n

    cur = conn.execute(
        "DELETE FROM stock_bobines WHERE reception_id=? AND etat=?",
        (reception_id, ETAT_STOCK),
    )
    n = cur.rowcount or 0
    conn.execute(
        "UPDATE stock_bobines SET reception_id=NULL, updated_at=? "
        "WHERE reception_id=? AND etat<>?",
        (_now(), reception_id, ETAT_STOCK),
    )
    return n


# ── Consommation ─────────────────────────────────────────────────────────────

def consommer(
    conn: sqlite3.Connection,
    bobine_id: int,
    *,
    metres: Optional[float] = None,
    terminee: bool = False,
    planning_entry_id: Optional[int] = None,
    no_dossier: Optional[str] = None,
    auteur: Optional[str] = None,
) -> Dict[str, Any]:
    """Retire du metrage d'une bobine, et la sort du stock si elle est finie.

    `terminee=True` la passe a l'etat consomme quel que soit le restant : c'est
    le geste normal en fin de dossier, ou l'operateur constate que la bobine est
    vide sans en mesurer le reliquat au metre pres.

    Le restant ne descend jamais sous zero. Un depassement n'est pas efface
    pour autant : il ressort dans `depassement`, parce qu'une bobine qui a rendu
    plus que son metrage annonce est un metrage faux a corriger, pas un incident
    a taire.
    """
    b = conn.execute("SELECT * FROM stock_bobines WHERE id=?", (bobine_id,)).fetchone()
    if b is None:
        raise ValueError("Bobine %s introuvable." % bobine_id)

    restant_avant = b["metrage_restant"]
    depassement = 0.0
    restant = restant_avant

    m = _f(metres)
    if m is not None and restant_avant is not None:
        restant = float(restant_avant) - m
        if restant < 0:
            depassement = -restant
            restant = 0.0
    elif m is not None:
        # Metrage inconnu au depart : on ne peut pas soustraire de rien. La
        # bobine reste sans metrage plutot que d'en acquerir un negatif.
        restant = None

    etat = b["etat"]
    if terminee or (restant is not None and restant <= 0):
        etat = ETAT_CONSOMMEE

    conn.execute(
        """UPDATE stock_bobines
              SET metrage_restant=?, etat=?, updated_at=?,
                  planning_entry_id=COALESCE(?, planning_entry_id),
                  no_dossier=COALESCE(?, no_dossier),
                  consomme_at=CASE WHEN ?='consommee' THEN COALESCE(consomme_at, ?) ELSE consomme_at END
            WHERE id=?""",
        (restant, etat, _now(), planning_entry_id, (no_dossier or None),
         etat, _now(), bobine_id),
    )
    return {
        "id": bobine_id,
        "etat": etat,
        "metrage_restant": restant,
        "metrage_avant": restant_avant,
        "depassement": depassement or None,
        "sortie_du_stock": etat == ETAT_CONSOMMEE and b["etat"] == ETAT_STOCK,
    }


def remettre_en_stock(conn: sqlite3.Connection, bobine_id: int,
                      metres_restant: Optional[float] = None) -> Dict[str, Any]:
    """Rend une bobine au stock — reliquat rapporte au magasin, ou correction.

    Le pendant de `consommer`. Sans lui, une erreur de designation en fin de
    dossier ne se rattraperait qu'en base.

    Sans `metres_restant`, le restant deja enregistre est conserve TEL QUEL,
    y compris zero. Remonter la bobine a son metrage initial « puisqu'elle
    revient » inventerait de la matiere que personne n'a vue.
    """
    b = conn.execute("SELECT * FROM stock_bobines WHERE id=?", (bobine_id,)).fetchone()
    if b is None:
        raise ValueError("Bobine %s introuvable." % bobine_id)
    restant = _f(metres_restant)
    if restant is None:
        restant = b["metrage_restant"]
    conn.execute(
        """UPDATE stock_bobines
              SET etat=?, metrage_restant=?, consomme_at=NULL, updated_at=?
            WHERE id=?""",
        (ETAT_STOCK, restant, _now(), bobine_id),
    )
    return {"id": bobine_id, "etat": ETAT_STOCK, "metrage_restant": restant}


# ── Lecture ──────────────────────────────────────────────────────────────────

_SELECT_BOBINE = """
    SELECT b.id, b.code_barre, b.matiere_id, b.laize_id, b.reception_id,
           b.lot_fournisseur, b.metrage_initial, b.metrage_restant,
           b.metrage_origine, b.etat, b.planning_entry_id, b.no_dossier,
           b.source, b.note, b.created_at, b.created_by_name, b.consomme_at,
           mp.reference    AS matiere_ref,
           mp.designation  AS matiere_designation,
           mp.categorie    AS matiere_categorie,
           lz.valeur_mm    AS laize_mm,
           sr.lot_numero   AS reception_lot,
           sr.fournisseur  AS fournisseur,
           sr.fsc_type_claim AS fsc_type_claim,
           sr.certificat_fsc AS certificat_fsc
      FROM stock_bobines b
      LEFT JOIN matieres_premieres mp ON mp.id = b.matiere_id
      LEFT JOIN mp_laizes         lz ON lz.id = b.laize_id
      LEFT JOIN stock_receptions  sr ON sr.id = b.reception_id
"""


def lister(
    conn: sqlite3.Connection,
    *,
    matiere_id: Optional[int] = None,
    laize_id: Optional[int] = None,
    etat: Optional[str] = None,
    q: Optional[str] = None,
    reception_id: Optional[int] = None,
    no_dossier: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    """Bobines filtrees, plus le total et le metrage de la selection ENTIERE.

    Le total est calcule sur le filtre et non sur la page : un magasinier qui
    voit « 200 bobines » alors qu'il en a 340 ne s'en apercoit jamais.
    """
    where, args = ["1=1"], []
    if matiere_id:
        where.append("b.matiere_id = ?")
        args.append(int(matiere_id))
    if laize_id:
        where.append("b.laize_id = ?")
        args.append(int(laize_id))
    if etat:
        if etat not in ETATS:
            raise ValueError("Etat inconnu : %r" % etat)
        where.append("b.etat = ?")
        args.append(etat)
    if reception_id:
        where.append("b.reception_id = ?")
        args.append(int(reception_id))
    if no_dossier:
        where.append("b.no_dossier = ?")
        args.append(str(no_dossier).strip())
    if q:
        motif = "%%%s%%" % str(q).strip().upper()
        where.append(
            "(UPPER(b.code_barre) LIKE ? OR UPPER(IFNULL(b.lot_fournisseur,'')) LIKE ? "
            " OR UPPER(IFNULL(mp.reference,'')) LIKE ? "
            " OR UPPER(IFNULL(mp.designation,'')) LIKE ?)"
        )
        args += [motif, motif, motif, motif]
    clause = " AND ".join(where)

    total = conn.execute(
        "SELECT COUNT(*) AS n, "
        "       COALESCE(SUM(b.metrage_restant), 0) AS metrage, "
        "       SUM(CASE WHEN b.metrage_restant IS NULL THEN 1 ELSE 0 END) AS sans_metrage "
        "  FROM stock_bobines b "
        "  LEFT JOIN matieres_premieres mp ON mp.id = b.matiere_id "
        " WHERE " + clause,
        args,
    ).fetchone()

    rows = conn.execute(
        _SELECT_BOBINE + " WHERE " + clause
        + " ORDER BY b.etat='stock' DESC, b.created_at DESC, b.id DESC LIMIT ? OFFSET ?",
        args + [int(limit), int(offset)],
    ).fetchall()

    return {
        "items": [dict(r) for r in rows],
        "total": int(total["n"] or 0),
        "metrage_total": round(float(total["metrage"] or 0), 1),
        "sans_metrage": int(total["sans_metrage"] or 0),
    }


def etat_stock(conn: sqlite3.Connection, matiere_id: int,
               laize_id: Optional[int] = None) -> Dict[str, Any]:
    """Ce que les bobines disent du stock d'une matiere (x laize).

    `sans_metrage` n'est pas de la decoration : c'est ce qui permet a l'ecran
    d'ecrire « 214 000 m + 3 bobines de metrage inconnu » plutot qu'un chiffre
    qui se donne pour complet.
    """
    where = ["matiere_id = ?", "etat = ?"]
    args: List[Any] = [int(matiere_id), ETAT_STOCK]
    if laize_id is not None:
        where.append("laize_id = ?")
        args.append(int(laize_id))
    row = conn.execute(
        "SELECT COUNT(*) AS nb, COALESCE(SUM(metrage_restant),0) AS metrage, "
        "       SUM(CASE WHEN metrage_restant IS NULL THEN 1 ELSE 0 END) AS sans "
        "  FROM stock_bobines WHERE " + " AND ".join(where),
        args,
    ).fetchone()
    nb = int(row["nb"] or 0)
    sans = int(row["sans"] or 0)
    return {
        "nb_bobines": nb,
        "metrage": round(float(row["metrage"] or 0), 1),
        "sans_metrage": sans,
        "metrage_complet": nb > 0 and sans == 0,
    }


# ── Controle de coherence ────────────────────────────────────────────────────

def coherence(conn: sqlite3.Connection, matiere_id: Optional[int] = None) -> Dict[str, Any]:
    """Compare le nombre de bobines en stock au compteur `mp_stock_laize`.

    Le controle ne porte QUE sur les matieres marquees `suivi_bobine` : ailleurs
    l'absence de bobine n'est pas un ecart, c'est une reference que le magasin
    n'a pas encore commence a scanner.

    Ce module ne corrige rien. Un ecart peut vouloir dire trois choses -- une
    bobine sortie sans etre designee, une entree comptee deux fois, ou un stock
    ajuste a la main -- et seul le magasin sait laquelle. Corriger d'office
    ferait disparaitre la question avec le chiffre.
    """
    args: List[Any] = []
    filtre = ""
    if matiere_id:
        filtre = " AND mp.id = ?"
        args.append(int(matiere_id))

    rows = conn.execute(
        """
        SELECT mp.id            AS matiere_id,
               mp.reference     AS matiere_ref,
               mp.designation   AS matiere_designation,
               sl.laize_id      AS laize_id,
               lz.valeur_mm     AS laize_mm,
               COALESCE(sl.quantite, 0) AS compteur
          FROM matieres_premieres mp
          JOIN mp_stock_laize sl ON sl.matiere_id = mp.id
          LEFT JOIN mp_laizes lz ON lz.id = sl.laize_id
         WHERE mp.suivi_bobine = 1 AND mp.actif = 1
        """ + filtre,
        args,
    ).fetchall()

    ecarts, controlees = [], 0
    for r in rows:
        b = conn.execute(
            "SELECT COUNT(*) AS nb, COALESCE(SUM(metrage_restant),0) AS metrage, "
            "       SUM(CASE WHEN metrage_restant IS NULL THEN 1 ELSE 0 END) AS sans "
            "  FROM stock_bobines "
            " WHERE matiere_id=? AND laize_id IS ? AND etat=?",
            (r["matiere_id"], r["laize_id"], ETAT_STOCK),
        ).fetchone()
        controlees += 1
        nb = int(b["nb"] or 0)
        compteur = float(r["compteur"] or 0)
        if abs(compteur - nb) < 1e-9:
            continue
        ecarts.append({
            "matiere_id": r["matiere_id"],
            "matiere_ref": r["matiere_ref"],
            "matiere_designation": r["matiere_designation"],
            "laize_id": r["laize_id"],
            "laize_mm": r["laize_mm"],
            "compteur": compteur,
            "bobines": nb,
            "ecart": round(compteur - nb, 4),
            "metrage": round(float(b["metrage"] or 0), 1),
            "sans_metrage": int(b["sans"] or 0),
        })

    # Bobines orphelines : en stock mais sans matiere. Elles ne peuvent etre
    # confrontees a aucun compteur et resteront invisibles a l'inventaire tant
    # que personne ne les rattache.
    orphelines = conn.execute(
        "SELECT COUNT(*) FROM stock_bobines WHERE etat=? AND matiere_id IS NULL",
        (ETAT_STOCK,),
    ).fetchone()[0]

    return {
        "lignes_controlees": controlees,
        "ecarts": sorted(ecarts, key=lambda e: -abs(e["ecart"])),
        "bobines_sans_matiere": int(orphelines or 0),
    }
