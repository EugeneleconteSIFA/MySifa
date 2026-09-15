"""Rattacher un dossier de fabrication — ou un départ — à des pièces de RVGI.

Ce module est le seul endroit qui met les deux bases en regard : le miroir de
RVGI (lecture seule, `erp_mirror`) et la base de production de MySifa. Il ne
fusionne rien. Il propose des pièces, enregistre un choix, et calcule un état.

Trois règles qui expliquent tout le reste
-----------------------------------------
1. **On pointe un id, jamais une référence texte.** `planning_entries.reference`
   est joint en texte par un millier de lignes de code sous le nom
   `no_dossier` : un dossier renommé perdrait ses rattachements si on s'appuyait
   dessus. La table de liaison porte `objet_id`.

2. **Le miroir a jusqu'à douze heures de retard.** Le sélecteur ne bloque donc
   jamais : un numéro que le miroir ne connaît pas encore s'enregistre en
   `a_verifier`, et `reprendre_apres_synchro()` le confirme dès qu'il apparaît.

3. **On ne devine pas une quantité.** Une ligne rattachée sans quantité couvre
   toute la ligne. Une quantité explicite en couvre une partie — et c'est cette
   distinction, pas un drapeau « partiel », qui permet de dire ce qu'il reste.

4. **Produire et expédier ne sont pas la même question.** Un départ rattache
   ses bons de livraison, et depuis le 15/09/2026 les lignes de commande qu'il
   emporte. Cette seconde liaison ne dit PAS que la ligne est produite : elle
   dit qu'elle est partie. Tout ce qui compte la couverture de production —
   la tuile « lignes sans dossier », le badge « déjà pris » du planning, le
   « Reliquat » d'une référence — ne regarde donc que `OBJETS_PRODUCTION`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services import erp_mirror as miroir

# Un dossier ne peut pas rattacher la terre entière : au-delà, la référence
# devient intapable au terminal et le rattachement n'aide plus personne.
MAX_LIGNES = 40
LIMITE_RECHERCHE = 40

OBJETS = ("dossier", "depart", "of")
PIECES = ("commande", "livraison")

# Où chaque objet range son état, et quelle nature de pièce le porte.
# `champ_texte` est la vitrine dénormalisée des numéros : tenue à jour,
# jamais lue comme source. La pièce nommée ici est la pièce NATIVE de l'objet :
# celle, et la seule, dont l'état remonte dans `rvgi_etat`.
ACCUEIL = {
    "dossier": ("planning_entries", "dos_rvgi", "commande"),
    "depart":  ("expe_departs",     "no_bl",    "livraison"),
    "of":      ("of_imports",       "cmd_rvgi", "commande"),
}

# Chaque couple objet × pièce autorisé, et la colonne texte qui l'affiche.
# Un départ en a deux : ses BL, et les lignes de commande qu'il emporte —
# lesquelles s'écrivent dans `arc`, exactement là où l'expéditeur les tapait
# à la main. Un couple absent d'ici n'existe pas : c'est ce qui empêche
# d'inventer un rattachement dossier → livraison sans y avoir réfléchi.
VITRINES = {
    ("dossier", "commande"):  "dos_rvgi",
    ("depart",  "livraison"): "no_bl",
    ("depart",  "commande"):  "arc",
    ("of",      "commande"):  "cmd_rvgi",
}

# Qui répond à « cette ligne de commande est-elle produite ? » — et qui répond
# à « est-elle partie ? ». Les deux questions vivent dans la même table et ne
# se confondent jamais : une ligne expédiée depuis du stock ancien n'a aucun
# dossier derrière elle, et un dossier lancé ce matin n'a rien expédié.
OBJETS_PRODUCTION = ("dossier", "of")
OBJETS_EXPEDITION = ("depart",)


def piece_native(objet: str) -> str:
    """La pièce dont l'état pilote `rvgi_etat` pour cet objet."""
    if objet not in ACCUEIL:
        raise ValueError("Objet inconnu : %r" % (objet,))
    return ACCUEIL[objet][2]


def pieces_de(objet: str) -> Tuple[str, ...]:
    """Les natures de pièce que cet objet a le droit de rattacher."""
    if objet not in ACCUEIL:
        raise ValueError("Objet inconnu : %r" % (objet,))
    native = piece_native(objet)
    autres = [p for (o, p) in VITRINES if o == objet and p != native]
    return tuple([native] + sorted(autres))


def vitrine_de(objet: str, piece: str) -> Optional[str]:
    """La colonne texte qui affiche ce couple, ou None s'il n'en a pas."""
    return VITRINES.get((objet, piece))


def _clause_objets(objets: Optional[Iterable[str]]) -> Tuple[str, List[Any]]:
    """Fragment SQL restreignant les rattachements à certains objets."""
    liste = [o for o in (objets or ()) if o in OBJETS]
    if not liste:
        return "", []
    return " AND r.objet IN (%s)" % ",".join("?" * len(liste)), list(liste)


# ─── Références de dossier ───────────────────────────────────────────────────
#
# La référence est PROPOSÉE, jamais imposée : c'est l'opérateur qui la tape au
# terminal, et c'est la clé que le reste de MySifa joint en texte. On la génère
# à la création, on ne la réécrit pas ensuite.

def _compacter_numeros(nums: List[str]) -> str:
    """« 9932128 » + « 9932129 » → « 9932128+129 ».

    Le préfixe n'est raccourci que si les numéros le partagent vraiment et ont
    la même longueur. Sinon on les écrit en entier : mieux vaut une référence
    longue qu'un numéro de commande faux.
    """
    tetes = sorted({str(n).strip() for n in nums if str(n).strip()})
    if not tetes:
        return ""
    if len(tetes) == 1:
        return tetes[0]
    prefixe = tetes[0][:4]
    meme_forme = all(len(t) == len(tetes[0]) and t.startswith(prefixe) for t in tetes)
    if not meme_forme:
        return "+".join(tetes)
    return "+".join([tetes[0]] + [t[4:] for t in tetes[1:]])


def _compacter_lignes(lignes: List[int]) -> str:
    """[1, 2, 3, 5] → « L1-3+5 »."""
    vals = sorted({int(x) for x in lignes if x is not None})
    if not vals:
        return ""
    bouts: List[Tuple[int, int]] = []
    debut = prec = vals[0]
    for n in vals[1:]:
        if n == prec + 1:
            prec = n
            continue
        bouts.append((debut, prec))
        debut = prec = n
    bouts.append((debut, prec))
    return "L" + "+".join(str(a) if a == b else "%d-%d" % (a, b) for a, b in bouts)


def proposer_reference(lignes: List[Dict[str, Any]],
                       lignes_par_commande: Optional[Dict[str, int]] = None,
                       reliquat: bool = False) -> str:
    """Référence proposée pour un dossier couvrant `lignes`.

    `lignes` : [{numero, ligne, qte, qte_ligne}, …] — `qte` absente = ligne
    entière. `lignes_par_commande` : {numero: nb de lignes dans RVGI}, pour
    écrire « 9932128 » tout court quand la commande est couverte en entier.

    Une couverture partielle ne se voit PAS dans la référence : l'opérateur la
    tape au terminal, et « (part.) » lui coûterait sept caractères pour une
    information qu'il ne peut de toute façon pas chiffrer de mémoire. Le
    « 450 000 sur 900 000 » vit dans la fiche du dossier et dans la colonne de
    MyERP, là où il est exact. En revanche « Reliquat » reste dans le numéro :
    c'est déjà la convention des scans d'OF, et c'est ce qui distingue deux
    dossiers posés sur la même ligne de commande.
    """
    if not lignes:
        return ""
    lignes_par_commande = lignes_par_commande or {}

    par_cde: Dict[str, List[Dict[str, Any]]] = {}
    for r in lignes:
        num = str(r.get("numero") or "").strip()
        if not num:
            continue
        par_cde.setdefault(num, []).append(r)
    if not par_cde:
        return ""

    if len(par_cde) == 1:
        num, rs = next(iter(par_cde.items()))
        nums_lignes = [r.get("ligne") for r in rs if r.get("ligne") is not None]
        base = num
        total = lignes_par_commande.get(num)
        # « 9932128/L1-6 » quand la commande a exactement six lignes n'apprend
        # rien à personne : dans ce cas on écrit « 9932128 ».
        if nums_lignes and not (total and len({int(x) for x in nums_lignes}) >= total):
            base += "/" + _compacter_lignes(nums_lignes)
    else:
        # Plusieurs commandes : le détail des lignes rendrait la référence
        # impossible à taper. On ne garde que les numéros.
        base = _compacter_numeros(list(par_cde.keys()))

    return ("Reliquat " + base) if reliquat else base


def deja_couvertes(conn: sqlite3.Connection, lignes: List[Dict[str, Any]],
                   piece: str = "commande",
                   sauf: Optional[Tuple[str, int]] = None) -> bool:
    """Une des lignes choisies est-elle déjà portée par un autre dossier ?

    C'est ce qui fait basculer la référence proposée en « Reliquat … » : un
    deuxième passage sur la même ligne de commande ne peut pas porter le même
    numéro de dossier que le premier.
    """
    # Un départ posé sur la même ligne ne fait pas reliquat : il dit que la
    # marchandise est partie, pas qu'elle a déjà été produite une fois.
    etats = etat_des_lignes(conn, piece, lignes, objets=OBJETS_PRODUCTION)
    for e in etats.values():
        for o in e.get("objets", []):
            # Un OF pointe la même ligne que le dossier qui en sort : le compter
            # ferait naître en « Reliquat » le premier dossier issu de cet OF.
            # Ce qui fait reliquat, c'est une production déjà passée dessus.
            if o["objet"] == "of":
                continue
            if sauf and (o["objet"], int(o["objet_id"])) == (sauf[0], int(sauf[1])):
                continue
            return True
    return False


# ─── Lecture des rattachements ───────────────────────────────────────────────

def lister(conn: sqlite3.Connection, objet: str, objet_id: int,
           piece: Optional[str] = None) -> List[Dict[str, Any]]:
    """Les rattachements d'un dossier ou d'un départ, dans l'ordre des pièces.

    `piece` restreint à une nature : un départ porte ses BL et ses lignes de
    commande, et les deux résumés de l'écran n'ont pas à se mélanger.
    """
    if objet not in OBJETS:
        raise ValueError("Objet inconnu : %r" % (objet,))
    sql = "SELECT * FROM rvgi_rattachements WHERE objet = ? AND objet_id = ?"
    params: List[Any] = [objet, int(objet_id)]
    if piece:
        sql += " AND piece = ?"
        params.append(piece)
    sql += " ORDER BY piece, CAST(numero AS INTEGER), COALESCE(ligne, 0)"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def rattachements_par_ligne(conn: sqlite3.Connection, piece: str,
                            cles: Iterable[Tuple[str, Optional[int]]],
                            objets: Optional[Iterable[str]] = None) -> Dict[Tuple[str, Optional[int]], List[Dict[str, Any]]]:
    """Ce qui est rattaché à des lignes RVGI données, pour la colonne de MyERP.

    `cles` : [(numero, ligne), …] — au plus une page d'écran. On interroge la
    base de production avec ces seules clés : le moteur du miroir reste étanche.
    Un rattachement posé sur la pièce entière (`ligne IS NULL`) répond pour
    toutes ses lignes.

    `objets` restreint la réponse — `OBJETS_PRODUCTION` pour « cette ligne
    est-elle produite », `OBJETS_EXPEDITION` pour « est-elle partie ». Sans
    filtre, tout remonte.
    """
    cles = list(cles)
    if not cles:
        return {}
    numeros = sorted({str(n).strip() for n, _ in cles if str(n or "").strip()})
    if not numeros:
        return {}

    out: Dict[Tuple[str, Optional[int]], List[Dict[str, Any]]] = {}
    # SQLite plafonne le nombre de paramètres liés : on découpe.
    for debut in range(0, len(numeros), 400):
        lot = numeros[debut:debut + 400]
        clause, p_obj = _clause_objets(objets)
        rows = conn.execute(
            "SELECT r.* FROM rvgi_rattachements r WHERE r.piece = ? "
            "AND r.numero IN (%s)%s" % (",".join("?" * len(lot)), clause),
            [piece] + lot + p_obj,
        ).fetchall()
        for r in rows:
            d = dict(r)
            if d["ligne"] is None:
                for num, lig in cles:
                    if str(num).strip() == d["numero"]:
                        out.setdefault((str(num).strip(), lig), []).append(d)
            else:
                out.setdefault((d["numero"], d["ligne"]), []).append(d)
    return out


def _libelles_objets(conn: sqlite3.Connection,
                     rattachements: List[Dict[str, Any]]) -> Dict[Tuple[str, int], str]:
    """Référence lisible de chaque dossier / départ cité, pour l'affichage."""
    ids_d = sorted({int(r["objet_id"]) for r in rattachements if r["objet"] == "dossier"})
    ids_p = sorted({int(r["objet_id"]) for r in rattachements if r["objet"] == "depart"})
    out: Dict[Tuple[str, int], str] = {}
    if ids_d:
        for r in conn.execute(
            "SELECT id, COALESCE(NULLIF(TRIM(reference),''), TRIM(COALESCE(numero_of,''))) AS ref "
            "FROM planning_entries WHERE id IN (%s)" % ",".join("?" * len(ids_d)), ids_d
        ):
            out[("dossier", r["id"])] = r["ref"] or ("#%d" % r["id"])
    if ids_p:
        for r in conn.execute(
            "SELECT id, COALESCE(NULLIF(TRIM(COALESCE(no_bl,'')),''), 'départ #'||id) AS ref "
            "FROM expe_departs WHERE id IN (%s)" % ",".join("?" * len(ids_p)), ids_p
        ):
            out[("depart", r["id"])] = r["ref"]
    ids_o = sorted({int(r["objet_id"]) for r in rattachements if r["objet"] == "of"})
    if ids_o:
        for r in conn.execute(
            "SELECT id, COALESCE(NULLIF(TRIM(COALESCE(of_numero,'')),''), 'OF #'||id) AS ref "
            "FROM of_imports WHERE id IN (%s)" % ",".join("?" * len(ids_o)), ids_o
        ):
            out[("of", r["id"])] = r["ref"]
    return out


def etat_des_lignes(conn: sqlite3.Connection, piece: str,
                    lignes: List[Dict[str, Any]],
                    objets: Optional[Iterable[str]] = None) -> Dict[Tuple[str, Optional[int]], Dict[str, Any]]:
    """Pour chaque ligne RVGI : rattachée, partiellement, ou pas du tout.

    `lignes` : [{numero, ligne, qte}, …] telles que lues dans le miroir. La
    quantité sert à distinguer « couverte » de « couverte en partie » — sans
    elle, on ne peut dire que « rattachée ».
    """
    cles = [(str(l.get("numero") or "").strip(),
             None if l.get("ligne") is None else int(l["ligne"])) for l in lignes]
    ratt = rattachements_par_ligne(conn, piece, cles, objets=objets)
    tous = [r for lot in ratt.values() for r in lot]
    libelles = _libelles_objets(conn, tous)

    out: Dict[Tuple[str, Optional[int]], Dict[str, Any]] = {}
    for l in lignes:
        cle = (str(l.get("numero") or "").strip(),
               None if l.get("ligne") is None else int(l["ligne"]))
        posés = ratt.get(cle, [])
        if not posés:
            out[cle] = {"etat": "non_rattache", "objets": [], "qte_rattachee": None,
                        "qte_ligne": l.get("qte")}
            continue

        qte_ligne = l.get("qte")
        somme = 0.0
        quantifie = False
        for r in posés:
            if r["qte"] is None:
                somme = None
                break
            quantifie = True
            somme += float(r["qte"])

        if somme is None or not quantifie:
            etat = "rattache"          # au moins un rattachement couvre tout
        elif qte_ligne in (None, 0):
            etat = "rattache"          # pas de quantité en face : on ne juge pas
        elif somme + 1e-6 < float(qte_ligne):
            etat = "partiel"
        else:
            etat = "rattache"

        if any(r["etat"] == "a_verifier" for r in posés):
            etat = etat if etat == "partiel" else "a_verifier"

        out[cle] = {
            "etat": etat,
            "objets": [
                {"objet": r["objet"], "objet_id": r["objet_id"],
                 "ref": libelles.get((r["objet"], r["objet_id"])) or "",
                 "qte": r["qte"], "etat": r["etat"]}
                for r in posés
            ],
            "qte_rattachee": None if somme is None else somme,
            "qte_ligne": qte_ligne,
        }
    return out


# ─── Écriture ────────────────────────────────────────────────────────────────

def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def enregistrer(conn: sqlite3.Connection, objet: str, objet_id: int, piece: str,
                lignes: List[Dict[str, Any]], utilisateur: str = "",
                etat_objet: Optional[str] = None) -> Dict[str, Any]:
    """Remplace les rattachements d'un objet pour une nature de pièce.

    `lignes` : [{numero, ligne?, qte?, vu_qte?, vu_article?, vu_client?,
    confirme?}, …]. `confirme` dit que la ligne a été choisie dans une liste
    issue du miroir ; sinon elle est enregistrée en `a_verifier`.

    Remplacement complet et non fusion : l'écran envoie l'état voulu, pas un
    delta. C'est ce qui rend le retrait d'une ligne possible. Le remplacement
    ne porte QUE sur la nature de pièce visée : enregistrer les lignes de
    commande d'un départ ne touche pas à ses bons de livraison.
    """
    if objet not in OBJETS:
        raise ValueError("Objet inconnu : %r" % (objet,))
    if piece not in PIECES:
        raise ValueError("Nature de pièce inconnue : %r" % (piece,))
    if (objet, piece) not in VITRINES:
        raise ValueError(
            "Un %s ne rattache pas de %s." % (objet, piece)
        )
    if len(lignes) > MAX_LIGNES:
        raise ValueError(
            "Un %s ne peut pas rattacher plus de %d lignes — au-delà, la "
            "référence devient intapable." % (objet, MAX_LIGNES)
        )

    maintenant = _maintenant()
    conn.execute(
        "DELETE FROM rvgi_rattachements WHERE objet=? AND objet_id=? AND piece=?",
        (objet, int(objet_id), piece),
    )
    vus = set()
    for l in lignes:
        numero = str(l.get("numero") or "").strip()
        if not numero:
            continue
        ligne = l.get("ligne")
        ligne = None if ligne in (None, "", 0) else int(ligne)
        if (numero, ligne) in vus:
            continue
        vus.add((numero, ligne))
        conn.execute(
            """INSERT INTO rvgi_rattachements
                 (objet, objet_id, piece, numero, ligne, qte, etat,
                  vu_qte, vu_article, vu_client, cree_le, cree_par, confirme_le, note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (objet, int(objet_id), piece, numero, ligne,
             _nombre(l.get("qte")),
             "confirme" if l.get("confirme") else "a_verifier",
             _nombre(l.get("vu_qte")),
             (l.get("vu_article") or None), (l.get("vu_client") or None),
             maintenant, utilisateur or None,
             maintenant if l.get("confirme") else None,
             (l.get("note") or None)),
        )
    return recalculer_etat(conn, objet, objet_id, piece=piece, force=etat_objet)


def _nombre(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def etat_de_rattachements(rows: List[Dict[str, Any]],
                          force: Optional[str] = None) -> str:
    """L'état que décrit un lot de rattachements d'une même nature de pièce.

    « Je ne trouve pas » et « hors commande » ne se posent que sur un lot VIDE :
    sinon l'état contredirait ce que la table contient, et c'est la table qui
    a raison.
    """
    if force in ("hors_commande", "a_rattacher") and not rows:
        return force
    if not rows:
        return "a_rattacher"
    if any(r["etat"] == "a_verifier" for r in rows):
        return "a_verifier"
    if any(r["qte"] is not None and r["vu_qte"] is not None
           and float(r["qte"]) + 1e-6 < float(r["vu_qte"]) for r in rows):
        return "partiel"
    return "lie"


def recalculer_etat(conn: sqlite3.Connection, objet: str, objet_id: int,
                    piece: Optional[str] = None,
                    force: Optional[str] = None) -> Dict[str, Any]:
    """Recalcule le champ texte dénormalisé, et `rvgi_etat` si la pièce le porte.

    `force` permet de poser « hors_commande » (production sans commande, assumée)
    ou « a_rattacher » (« je ne trouve pas ») sans rattachement à l'appui.

    `rvgi_etat` est une colonne unique par objet : elle ne peut parler que
    d'UNE nature de pièce, la native. Les lignes de commande d'un départ ont
    donc leur état rendu à l'appelant, mais ne réécrivent pas la colonne —
    sinon un départ dont les BL manquent passerait « rattaché » parce que son
    ARC est renseigné.
    """
    if objet not in ACCUEIL:
        raise ValueError("Objet inconnu : %r" % (objet,))
    table = ACCUEIL[objet][0]
    native = piece_native(objet)
    piece = piece or native
    champ_texte = vitrine_de(objet, piece)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM rvgi_rattachements WHERE objet=? AND objet_id=? AND piece=?",
        (objet, int(objet_id), piece),
    )]

    etat = etat_de_rattachements(rows, force=force)

    # Le champ texte reste la vitrine : les numéros, sans les lignes. Il est
    # tenu à jour, jamais lu comme source — même choix que expe_departs.no_dossier.
    texte = _compacter_numeros([r["numero"] for r in rows]) or None
    maintenant = _maintenant()
    cols = {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    sets, params = [], []
    if piece == native:
        if "rvgi_etat" in cols:
            sets.append("rvgi_etat=?"); params.append(etat)
        if "rvgi_maj_le" in cols:
            sets.append("rvgi_maj_le=?"); params.append(maintenant)
    if champ_texte and champ_texte in cols and texte:
        sets.append("%s=?" % champ_texte); params.append(texte)
    if sets:
        params.append(int(objet_id))
        conn.execute("UPDATE %s SET %s WHERE id=?" % (table, ", ".join(sets)), params)

    return {"etat": etat, "texte": texte, "rattachements": len(rows),
            "piece": piece, "native": piece == native}


# ─── Reprise après une synchro ───────────────────────────────────────────────

def reprendre_apres_synchro(conn: sqlite3.Connection, limite: int = 5000) -> Dict[str, int]:
    """Confirme les rattachements « à vérifier » que le miroir connaît désormais.

    Sans cette reprise, « je ne trouve pas ma commande » deviendrait la porte
    principale : un numéro tapé pendant que le miroir était en retard resterait
    marqué douteux pour toujours.
    """
    en_attente = [dict(r) for r in conn.execute(
        "SELECT * FROM rvgi_rattachements WHERE etat='a_verifier' "
        "ORDER BY cree_le LIMIT ?", (int(limite),))]
    if not en_attente:
        return {"vus": 0, "confirmes": 0, "objets": 0}

    trouves = _numeros_connus_du_miroir(en_attente)
    maintenant = _maintenant()
    confirmes, objets = 0, set()
    for r in en_attente:
        if (r["piece"], r["numero"]) not in trouves:
            continue
        conn.execute(
            "UPDATE rvgi_rattachements SET etat='confirme', confirme_le=? WHERE id=?",
            (maintenant, r["id"]),
        )
        confirmes += 1
        objets.add((r["objet"], r["objet_id"], r["piece"]))
    for objet, objet_id, piece in objets:
        recalculer_etat(conn, objet, objet_id, piece=piece)
    return {"vus": len(en_attente), "confirmes": confirmes,
            "objets": len({(o, i) for o, i, _ in objets})}


def _numeros_connus_du_miroir(rattachements: List[Dict[str, Any]]) -> set:
    """Parmi des (piece, numero), ceux que le miroir connaît."""
    par_piece: Dict[str, List[str]] = {}
    for r in rattachements:
        par_piece.setdefault(r["piece"], []).append(str(r["numero"]).strip())

    trouves = set()
    try:
        with miroir.get_erp_db() as c:
            presentes = miroir.tables_presentes(c)
            for piece, numeros in par_piece.items():
                table = "cde_ligne" if piece == "commande" else "liv_ligne"
                if table not in presentes:
                    continue
                uniques = sorted(set(numeros))
                for debut in range(0, len(uniques), 400):
                    lot = uniques[debut:debut + 400]
                    sql = ('SELECT DISTINCT CAST(numero AS TEXT) FROM "%s" '
                           "WHERE corbeille=0 AND CAST(numero AS TEXT) IN (%s)"
                           % (table, ",".join("?" * len(lot))))
                    for row in c.execute(sql, lot):
                        trouves.add((piece, row[0]))
    except FileNotFoundError:
        return set()   # miroir absent : on ne confirme rien, on ne casse rien
    return trouves


# ─── Recherche de pièces dans le miroir ──────────────────────────────────────
#
# Le sélecteur ne montre jamais 20 000 commandes : il cherche. Trois entrées
# possibles — un numéro, un nom de client, une référence article ou une
# désignation — parce que c'est ce qu'un planificateur a sous les yeux.

_SQL_COMMANDES = """
    SELECT l.numero          AS numero,
           l.ligne           AS ligne,
           l.lpos            AS lpos,
           l.code1           AS code1,
           l.code2           AS code2,
           l.des1            AS des1,
           l.qte             AS qte,
           l.qtep            AS qtep,
           l.amje            AS amje,
           e.rs              AS client,
           e.amjc            AS date_cde,
           l.vref            AS vref
      FROM cde_ligne l
      LEFT JOIN cde_entete e ON e.numero = l.numero
     WHERE l.corbeille = 0
"""

_SQL_LIVRAISONS = """
    SELECT l.numero          AS numero,
           l.rang            AS ligne,
           l.numcde          AS numcde,
           l.lignecde        AS lignecde,
           l.qte             AS qte,
           l.qtefac          AS qtefac,
           l.amjl            AS amjl,
           l.fac_no          AS fac_no,
           e.lrs             AS client,
           e.amje            AS date_bl
      FROM liv_ligne l
      LEFT JOIN liv_entete e ON e.numero = l.numero
     WHERE l.corbeille = 0
"""


def _filtre_texte(q: str, colonnes: List[str]) -> Tuple[str, List[Any]]:
    """Un OU sur les colonnes utiles. Un numéro tapé en entier passe d'abord."""
    motif = "%" + str(q or "").strip().replace("%", "") + "%"
    bouts = " OR ".join("CAST(%s AS TEXT) LIKE ?" % c for c in colonnes)
    return "(" + bouts + ")", [motif] * len(colonnes)


def chercher_commandes(q: str, limite: int = LIMITE_RECHERCHE,
                       ouvertes_seulement: bool = True,
                       numeros_suggeres: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Commandes candidates, groupées, avec leurs lignes.

    `ouvertes_seulement` écarte les commandes soldées : on lance rarement une
    production sur une commande déjà livrée. Le sélecteur permet de rouvrir la
    recherche à tout, pour les reliquats et les rattrapages.

    `numeros_suggeres` : les commandes que l'écran connaît déjà — pour un
    départ, celles de ses dossiers de fabrication. Elles remontent en tête et
    s'affichent même sans recherche, mais rien n'est coché à la place de
    l'expéditeur : ce qui part réellement, c'est lui qui le sait.
    """
    q = str(q or "").strip()
    suggeres = [str(n).strip() for n in (numeros_suggeres or []) if str(n).strip()]
    if len(q) < 2 and not suggeres:
        return []
    ou, params = _filtre_texte(q, ["l.numero", "e.rs", "l.des1", "l.code1", "l.code2", "l.vref"])
    if len(q) < 2:
        # Pas de recherche : seules les commandes suggérées sont candidates.
        ou, params = "1=0", []
    sql = _SQL_COMMANDES + " AND " + ou
    if ouvertes_seulement:
        # lpos : 2 = soldée dans RVGI. On garde tout le reste, y compris les
        # positions inconnues — une position qu'on ne sait pas lire ne doit pas
        # faire disparaître une commande.
        sql += " AND COALESCE(l.lpos, 0) <> 2"
    sql += " ORDER BY l.numero DESC, l.ligne LIMIT ?"
    params = params + [int(limite) * 12]

    with miroir.get_erp_db() as c:
        if "cde_ligne" not in miroir.tables_presentes(c):
            return []
        # Deux temps, et c'est important. La recherche ne trouve QUE les lignes
        # qui correspondent au texte tapé — « SONELOG » ne remonte pas la ligne
        # 3 d'une commande SONELOG si sa désignation ne contient pas le mot.
        # Or on coche des lignes : en montrer une partie sans le dire ferait
        # rattacher une commande incomplète. On retient donc les NUMÉROS
        # trouvés, puis on relit toutes leurs lignes.
        # Les suggérées d'abord : une commande soldée reste visible si un
        # dossier du départ la porte — c'est le cas courant d'un reliquat.
        numeros = list(dict.fromkeys(suggeres))[:limite]
        for r in c.execute(sql, params):
            num = str(r["numero"] or "").strip()
            if num and num not in numeros:
                numeros.append(num)
            if len(numeros) >= limite:
                break
        if not numeros:
            return []
        lignes = _lire_lignes_commandes(c, numeros)
    vus = set(suggeres)
    for l in lignes:
        l["suggere"] = str(l.get("numero") or "").strip() in vus
    groupes = _grouper_par_numero(lignes, limite)
    if suggeres:
        groupes.sort(key=lambda g: (not any(l.get("suggere") for l in g["lignes"]),
                                    -_entier(g["numero"])))
    return groupes


def _lire_lignes_commandes(c, numeros: List[str]) -> List[Dict[str, Any]]:
    """Toutes les lignes des commandes retenues, dans l'ordre de RVGI."""
    lignes: List[Dict[str, Any]] = []
    for debut in range(0, len(numeros), 400):
        lot = numeros[debut:debut + 400]
        sql = (_SQL_COMMANDES + " AND CAST(l.numero AS TEXT) IN (%s)"
               % ",".join("?" * len(lot)) + " ORDER BY l.numero DESC, l.ligne")
        for r in c.execute(sql, lot):
            d = dict(r)
            # On garde les deux codes bruts : ils formeront la clé de jointure
            # vers la fiche produit, que `article` ne permet plus une fois les
            # deux colonnes fondues en « 986/0005 ».
            c1, c2 = d.pop("code1", None), d.pop("code2", None)
            d["code1_brut"], d["code2_brut"] = c1, c2
            d["article"] = _article(c1, c2)
            d["qte"] = miroir.nettoyer(d.get("qte"), "qte")
            d["qtep"] = miroir.nettoyer(d.get("qtep"), "qte")
            d["amje"] = miroir.nettoyer(d.get("amje"), "date")
            d["date_cde"] = miroir.nettoyer(d.get("date_cde"), "date")
            lignes.append(d)
        _ajouter_fiche_produit(c, lignes)
    return lignes


# ─── La fiche produit ────────────────────────────────────────────────────────
#
# Ce que le planificateur regarde d'abord, avant même le client : QUEL produit,
# et sur QUELLE machine il est censé tourner. RVGI le sait, dans deux tables
# différentes — la fiche article pour le format, la fiche de fabrication pour
# la machine et la laize. On les rassemble ici plutôt que de les faire chercher.
#
#   fic_art   ftl / fth   largeur et hauteur de l'étiquette (2 734 / 7 679)
#             cltc2       la référence du client pour cet article (5 379)
#             libc1       la désignation
#   gpr_ff    nmac1       la machine de production (584 fiches, une par article)
#             laimat      la laize matière (548 / 584)
#   mac_pro   nom         le nom de la machine — type 1 = machines de production
#
# Toutes les commandes n'ont pas de fiche de fabrication : 579 articles sur les
# 4 007 commandés. C'est normal — un article jamais produit chez SIFA n'en a
# pas. Le sélecteur affiche alors l'article seul, sans machine, et n'invente rien.

_SEP = "\x1f"


def _cle_art(code1, code2) -> str:
    return "%s%s%s" % (str(code1 or "").strip(), _SEP, str(code2 or "").strip())


def _nombre(v) -> Optional[float]:
    """Un format à zéro n'est pas un format : RVGI y écrit l'absence de saisie."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f else None


def fiche_produit(c, codes: Iterable[Tuple[Any, Any]]) -> Dict[str, Dict[str, Any]]:
    """{clé article: {libelle, ref_client, largeur, hauteur, laize, machine}}.

    Les trois tables sont interrogées par lots de 400 couples de codes : sous
    SQLite, un `IN` de plusieurs milliers de paramètres coûte plus cher que
    quelques allers-retours.
    """
    cles: List[Tuple[str, str]] = []
    vus = set()
    for c1, c2 in codes:
        a, b = str(c1 or "").strip(), str(c2 or "").strip()
        if not a or (a, b) in vus:
            continue
        vus.add((a, b))
        cles.append((a, b))
    if not cles:
        return {}

    presentes = miroir.tables_presentes(c)
    out: Dict[str, Dict[str, Any]] = {}

    def _par_lots(table: str, colonnes: str, sur):
        if table not in presentes:
            return
        for debut in range(0, len(cles), 400):
            lot = cles[debut:debut + 400]
            sql = ('SELECT %s FROM "%s" WHERE corbeille = 0 AND (%s)'
                   % (colonnes, table,
                      " OR ".join(["(code1 = ? AND code2 = ?)"] * len(lot))))
            params = [v for paire in lot for v in paire]
            for r in c.execute(sql, params):
                sur(out.setdefault(_cle_art(r["code1"], r["code2"]), {}), r)

    _par_lots("fic_art", "code1, code2, libc1, ftl, fth, cltc2", lambda d, r: d.update({
        "libelle": (r["libc1"] or None),
        "ref_client": (str(r["cltc2"]).strip() or None) if r["cltc2"] else None,
        "largeur": _nombre(r["ftl"]),
        "hauteur": _nombre(r["fth"]),
    }))

    machines: Dict[Any, str] = {}
    if "mac_pro" in presentes:
        for r in c.execute("SELECT code, nom FROM mac_pro WHERE corbeille = 0 AND type = 1"):
            if r["nom"]:
                machines[r["code"]] = str(r["nom"]).strip()

    def _ff(d: Dict[str, Any], r) -> None:
        d["laize"] = _nombre(r["laimat"])
        d["machine_code"] = r["nmac1"]
        # Une machine que `mac_pro` ne connaît pas ne devient pas « machine 4 » :
        # on préfère ne rien afficher plutôt qu'un numéro qui ne parle à personne.
        d["machine"] = machines.get(r["nmac1"])

    _par_lots("gpr_ff", "code1, code2, nmac1, laimat", _ff)
    return out


def _ajouter_fiche_produit(c, lignes: List[Dict[str, Any]]) -> None:
    """Colle la fiche produit sur chaque ligne de commande proposée."""
    if not lignes:
        return
    try:
        fiches = fiche_produit(c, [(l.get("code1_brut"), l.get("code2_brut"))
                                   for l in lignes])
    except sqlite3.Error:
        return  # une fiche manquante ne doit pas empêcher de rattacher
    for l in lignes:
        f = fiches.get(_cle_art(l.get("code1_brut"), l.get("code2_brut"))) or {}
        l["produit"] = {
            "article": l.get("article"),
            "libelle": f.get("libelle") or l.get("des1"),
            "ref_client": f.get("ref_client"),
            "largeur": f.get("largeur"),
            "hauteur": f.get("hauteur"),
            "laize": f.get("laize"),
            "machine": f.get("machine"),
            "machine_code": f.get("machine_code"),
        }
        # Remontés à plat aussi : le sélecteur les affiche sur chaque ligne, et
        # une indirection de plus dans le gabarit ne servirait à rien.
        l["machine"] = f.get("machine")
        l["laize"] = f.get("laize")


def chercher_livraisons(q: str = "", numeros_commande: Optional[List[str]] = None,
                        limite: int = LIMITE_RECHERCHE) -> List[Dict[str, Any]]:
    """Bons de livraison candidats, groupés par BL.

    `numeros_commande` : les commandes du dossier expédié. RVGI porte déjà le
    lien (`liv_ligne.numcde`), donc les BL de ces commandes sont proposés en
    premier, sans que personne ait à les chercher.
    """
    q = str(q or "").strip()
    numeros_commande = [str(n).strip() for n in (numeros_commande or []) if str(n).strip()]
    if len(q) < 2 and not numeros_commande:
        return []

    conditions, params = [], []
    if numeros_commande:
        lot = numeros_commande[:400]
        conditions.append("CAST(l.numcde AS TEXT) IN (%s)" % ",".join("?" * len(lot)))
        params += lot
    if len(q) >= 2:
        ou, p = _filtre_texte(q, ["l.numero", "l.numcde", "e.lrs", "l.note"])
        conditions.append(ou)
        params += p

    sql = _SQL_LIVRAISONS + " AND (" + " OR ".join(conditions) + ")"
    sql += " ORDER BY l.numero DESC, COALESCE(l.rang, 0) LIMIT ?"
    params.append(int(limite) * 12)

    lignes: List[Dict[str, Any]] = []
    with miroir.get_erp_db() as c:
        if "liv_ligne" not in miroir.tables_presentes(c):
            return []
        for r in c.execute(sql, params):
            d = dict(r)
            d["qte"] = miroir.nettoyer(d.get("qte"), "qte")
            d["amjl"] = miroir.nettoyer(d.get("amjl"), "date")
            d["date_bl"] = miroir.nettoyer(d.get("date_bl"), "date")
            # Ce BL vient-il d'une commande du dossier ? C'est ce qui le fait
            # remonter en tête plutôt que de le noyer dans la liste.
            d["suggere"] = bool(numeros_commande) and str(d.get("numcde") or "") in set(numeros_commande)
            lignes.append(d)
    groupes = _grouper_par_numero(lignes, limite)
    groupes.sort(key=lambda g: (not any(l.get("suggere") for l in g["lignes"]),
                                -_entier(g["numero"])))
    return groupes


def _article(code1, code2) -> Optional[str]:
    a = str(code1 or "").strip()
    b = str(code2 or "").strip()
    if not a and not b:
        return None
    return ("%s/%s" % (a, b)) if b else a


def _entier(v) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return 0


def _grouper_par_numero(lignes: List[Dict[str, Any]], limite: int) -> List[Dict[str, Any]]:
    """Les lignes remontent à plat ; le sélecteur, lui, raisonne par pièce."""
    groupes: Dict[str, Dict[str, Any]] = {}
    for l in lignes:
        num = str(l.get("numero") or "").strip()
        if not num:
            continue
        g = groupes.setdefault(num, {
            "numero": num, "client": l.get("client"),
            "date": l.get("date_cde") or l.get("date_bl"),
            "lignes": [],
        })
        if not g.get("client"):
            g["client"] = l.get("client")
        g["lignes"].append(l)
    ordre = sorted(groupes.values(), key=lambda g: -_entier(g["numero"]))
    for g in ordre:
        g["nb_lignes"] = len(g["lignes"])
    return ordre[:limite]


def enrichir_avec_rattachements(conn: sqlite3.Connection, piece: str,
                                groupes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ajoute à chaque ligne proposée ce qui lui est déjà rattaché.

    C'est ce qui empêche de rattacher deux fois la même ligne sans le savoir —
    et ce qui permet de proposer, par défaut, le RESTE d'une ligne déjà
    partiellement couverte plutôt que sa quantité totale.

    Sur une commande, deux lectures cohabitent sans se mélanger :
    `rattachement` dit ce que la PRODUCTION a pris — c'est lui qui pilote le
    reste à produire et le badge « déjà pris » — et `expedition` dit ce qui est
    DÉJÀ PARTI. Un départ ne réduit jamais le reste à produire : il ne produit
    rien.
    """
    plates = [l for g in groupes for l in g["lignes"]]
    objets = OBJETS_PRODUCTION if piece == "commande" else None
    etats = etat_des_lignes(conn, piece, plates, objets=objets)
    exped = (etat_des_lignes(conn, piece, plates, objets=OBJETS_EXPEDITION)
             if piece == "commande" else {})
    for g in groupes:
        for l in g["lignes"]:
            cle = (str(l.get("numero") or "").strip(),
                   None if l.get("ligne") is None else int(l["ligne"]))
            e = etats.get(cle) or {}
            l["rattachement"] = e
            if piece == "commande":
                x = exped.get(cle) or {}
                l["expedition"] = x if x.get("objets") else None
            deja = e.get("qte_rattachee")
            qte = l.get("qte")
            if qte is not None and deja is not None:
                l["reste"] = max(0.0, float(qte) - float(deja))
            else:
                l["reste"] = qte
        g["etat"] = _etat_du_groupe(g["lignes"])
        if piece == "commande":
            g["expediee"] = any(l.get("expedition") for l in g["lignes"])
    return groupes


def _etat_du_groupe(lignes: List[Dict[str, Any]]) -> str:
    etats = {(l.get("rattachement") or {}).get("etat", "non_rattache") for l in lignes}
    if etats <= {"non_rattache"}:
        return "non_rattache"
    if "non_rattache" in etats or "partiel" in etats:
        return "partiel"
    if "a_verifier" in etats:
        return "a_verifier"
    return "rattache"


# ── Entête d'une commande, pour le préremplissage d'un départ ────────────────
#
# MyExpé demande ceci quand on saisit un numéro d'ARC : la commande sait déjà
# chez qui la marchandise part et quand elle est attendue. Le retaper à la main
# est une source d'erreur, et une erreur de code postal se paie en livraison.


def _jour(valeur: Any) -> str:
    """Les dates du miroir portent une heure : on ne garde que le jour."""
    return str(valeur or "").strip()[:10]


def entete_commande(numero: str) -> Optional[Dict[str, Any]]:
    """L'entête d'une commande RVGI, réduite à ce qu'un départ sait utiliser.

    L'adresse retenue est celle de LIVRAISON (`lrs`/`lcp`/`lville`) et non
    celle de facturation : un départ va chez le destinataire. On retombe sur
    l'adresse de facturation seulement si la commande n'en porte pas d'autre,
    ce qui est le cas courant quand les deux sont confondues.
    """
    num = str(numero or "").strip()
    if not num or not num.isdigit():
        return None
    with miroir.get_erp_db() as c:
        if "cde_entete" not in miroir.tables_presentes(c):
            return None
        # Comparaison sur l'ENTIER : `numero` est un integer dans le miroir et
        # porte un index. Un CAST en texte le rend inutilisable — 24 ms de
        # balayage au lieu de 1 ms, sur une requete tapee a chaque frappe.
        row = c.execute(
            """SELECT * FROM cde_entete
                WHERE corbeille = 0 AND numero = ?
                LIMIT 1""",
            (int(num),),
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        nb_lignes = 0
        soldee = False
        if "cde_ligne" in miroir.tables_presentes(c):
            lignes = c.execute(
                """SELECT COUNT(*) AS n,
                          SUM(CASE WHEN COALESCE(lpos,0) = 2 THEN 1 ELSE 0 END) AS soldees
                     FROM cde_ligne
                    WHERE corbeille = 0 AND numero = ?""",
                (int(num),),
            ).fetchone()
            nb_lignes = int(lignes["n"] or 0)
            # lpos = 2 : ligne soldée dans RVGI. Toutes soldées = commande livrée.
            soldee = nb_lignes > 0 and int(lignes["soldees"] or 0) >= nb_lignes

    livre = str(d.get("lrs") or "").strip()
    facture = str(d.get("rs") or "").strip()
    cp = str(d.get("lcp") or "").strip() or str(d.get("cp") or "").strip()
    ville = str(d.get("lville") or "").strip() or str(d.get("ville") or "").strip()
    return {
        "numero": num,
        "client": livre or facture,
        "client_facture": facture,
        "adresse_de_livraison": bool(livre),
        "code_postal": cp,
        "ville": ville,
        "pays": str(d.get("lpays") or d.get("pays") or "").strip(),
        "date_commande": _jour(d.get("amjc")),
        "date_livraison": _jour(d.get("amjl")) or _jour(d.get("amje")),
        "ref_client": str(d.get("vref") or "").strip(),
        "interlocuteur": str(d.get("interlocuteur") or "").strip(),
        "nb_lignes": nb_lignes,
        "soldee": soldee,
    }


# ─── Articles ────────────────────────────────────────────────────────────────
#
# La référence d'une fiche technique MySifa (« 1026/0020 », parfois suivie de
# « - COHESIO 1 ») est exactement le couple code1/code2 d'un article de RVGI.
# C'est ce qui permet de relier les deux sans demander une saisie de plus —
# mais le lien est STOCKÉ (article_code1/article_code2 sur la fiche) et non
# redevine à chaque lecture : une référence corrigée ne doit pas déplacer
# silencieusement une fiche d'un article à un autre.

def couper_reference(reference: str) -> Optional[Tuple[str, str]]:
    """« 1026/0020 - COHESIO 1 » → ('1026', '0020'). None si ce n'en est pas une.

    Le suffixe machine est un ajout d'affichage côté SIFA ; RVGI ne connaît que
    les deux codes. On ne normalise pas les zéros de tête : « 0020 » et « 20 »
    sont deux articles différents dans l'ERP.
    """
    brut = str(reference or "").split(" - ")[0].strip()
    if "/" not in brut:
        return None
    gauche, _, droite = brut.partition("/")
    gauche, droite = gauche.strip(), droite.strip()
    if not gauche or not droite:
        return None
    if not (gauche.isdigit() and droite.isdigit()):
        return None
    return gauche, droite


def _article_ligne(r) -> Dict[str, Any]:
    largeur, hauteur = _nombre(r["ftl"]), _nombre(r["fth"])
    return {
        "code1": str(r["code1"] or "").strip(),
        "code2": str(r["code2"] or "").strip(),
        "reference": "%s/%s" % (str(r["code1"] or "").strip(),
                                str(r["code2"] or "").strip()),
        "libelle": (r["libc1"] or None),
        "ref_client": (str(r["cltc2"]).strip() or None) if r["cltc2"] else None,
        "largeur": largeur,
        "hauteur": hauteur,
        "format": ("%s x %s mm" % (_texte_nombre(largeur), _texte_nombre(hauteur))
                   if largeur and hauteur else None),
    }


def _texte_nombre(v: Optional[float]) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v) == int(v) else str(v)


def chercher_articles(q: str, limite: int = LIMITE_RECHERCHE) -> List[Dict[str, Any]]:
    """Articles candidats pour une fiche technique.

    Cherche sur les deux codes, le libellé et la référence client : c'est ce
    que l'ADV a sous les yeux quand elle ouvre une fiche.
    """
    q = str(q or "").strip()
    if len(q) < 2:
        return []
    # « 1026/0020 » tapé en entier doit tomber sur l'article exact, pas sur les
    # cent articles dont le libellé contient « 1026 ».
    exact = couper_reference(q)
    with miroir.get_erp_db() as c:
        if "fic_art" not in miroir.tables_presentes(c):
            return []
        if exact:
            rows = c.execute(
                "SELECT code1, code2, libc1, cltc2, ftl, fth FROM fic_art "
                "WHERE corbeille = 0 AND code1 = ? AND code2 = ? LIMIT 1", exact,
            ).fetchall()
            if rows:
                return [_article_ligne(r) for r in rows]
        ou, params = _filtre_texte(q, ["code1", "code2", "libc1", "cltc2"])
        rows = c.execute(
            "SELECT code1, code2, libc1, cltc2, ftl, fth FROM fic_art "
            "WHERE corbeille = 0 AND " + ou +
            " ORDER BY CAST(code1 AS INTEGER), code2 LIMIT ?",
            params + [int(limite)],
        ).fetchall()
    return [_article_ligne(r) for r in rows]


def article(code1: str, code2: str) -> Optional[Dict[str, Any]]:
    """L'article et ce que RVGI sait de sa fabrication.

    `gpr_ff` est la fiche de fabrication de l'ERP. SIFA a cessé de l'alimenter
    en avril 2026 — c'est précisément ce qui a donné naissance à MySifa. On la
    lit donc comme une aide au pré-remplissage, jamais comme une vérité : le
    bloc `fabrication` est renvoyé à part pour que l'écran puisse dire d'où
    vient chaque valeur proposée.
    """
    a, b = str(code1 or "").strip(), str(code2 or "").strip()
    if not a or not b:
        return None
    with miroir.get_erp_db() as c:
        presentes = miroir.tables_presentes(c)
        if "fic_art" not in presentes:
            return None
        r = c.execute(
            "SELECT code1, code2, libc1, cltc2, ftl, fth FROM fic_art "
            "WHERE corbeille = 0 AND code1 = ? AND code2 = ? LIMIT 1", (a, b),
        ).fetchone()
        if not r:
            return None
        out = _article_ligne(r)
        out["fabrication"] = None
        if "gpr_ff" in presentes:
            f = c.execute(
                "SELECT laimat, laiout, nbcoul, cliche, nmac1, amj FROM gpr_ff "
                "WHERE corbeille = 0 AND code1 = ? AND code2 = ? "
                "ORDER BY COALESCE(amj,'') DESC LIMIT 1", (a, b),
            ).fetchone()
            if f:
                machines = {}
                if "mac_pro" in presentes:
                    for m in c.execute(
                        "SELECT code, nom FROM mac_pro WHERE corbeille = 0 AND type = 1"
                    ):
                        if m["nom"]:
                            machines[m["code"]] = str(m["nom"]).strip()
                out["fabrication"] = {
                    "laize_matiere": _nombre(f["laimat"]),
                    "laize_outil": _nombre(f["laiout"]),
                    "nb_couleurs": _nombre(f["nbcoul"]),
                    "cliche": (f["cliche"] or None),
                    "machine": machines.get(f["nmac1"]),
                    "maj_le": (f["amj"] or None),
                }
    return out
