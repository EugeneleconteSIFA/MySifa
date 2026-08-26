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

OBJETS = ("dossier", "depart")
PIECES = ("commande", "livraison")


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
    etats = etat_des_lignes(conn, piece, lignes)
    for e in etats.values():
        for o in e.get("objets", []):
            if sauf and (o["objet"], int(o["objet_id"])) == (sauf[0], int(sauf[1])):
                continue
            return True
    return False


# ─── Lecture des rattachements ───────────────────────────────────────────────

def lister(conn: sqlite3.Connection, objet: str, objet_id: int) -> List[Dict[str, Any]]:
    """Les rattachements d'un dossier ou d'un départ, dans l'ordre des pièces."""
    if objet not in OBJETS:
        raise ValueError("Objet inconnu : %r" % (objet,))
    rows = conn.execute(
        """SELECT * FROM rvgi_rattachements
            WHERE objet = ? AND objet_id = ?
            ORDER BY piece, CAST(numero AS INTEGER), COALESCE(ligne, 0)""",
        (objet, int(objet_id)),
    ).fetchall()
    return [dict(r) for r in rows]


def rattachements_par_ligne(conn: sqlite3.Connection, piece: str,
                            cles: Iterable[Tuple[str, Optional[int]]]) -> Dict[Tuple[str, Optional[int]], List[Dict[str, Any]]]:
    """Ce qui est rattaché à des lignes RVGI données, pour la colonne de MyERP.

    `cles` : [(numero, ligne), …] — au plus une page d'écran. On interroge la
    base de production avec ces seules clés : le moteur du miroir reste étanche.
    Un rattachement posé sur la pièce entière (`ligne IS NULL`) répond pour
    toutes ses lignes.
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
        rows = conn.execute(
            "SELECT * FROM rvgi_rattachements WHERE piece = ? AND numero IN (%s)"
            % ",".join("?" * len(lot)),
            [piece] + lot,
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
    return out


def etat_des_lignes(conn: sqlite3.Connection, piece: str,
                    lignes: List[Dict[str, Any]]) -> Dict[Tuple[str, Optional[int]], Dict[str, Any]]:
    """Pour chaque ligne RVGI : rattachée, partiellement, ou pas du tout.

    `lignes` : [{numero, ligne, qte}, …] telles que lues dans le miroir. La
    quantité sert à distinguer « couverte » de « couverte en partie » — sans
    elle, on ne peut dire que « rattachée ».
    """
    cles = [(str(l.get("numero") or "").strip(),
             None if l.get("ligne") is None else int(l["ligne"])) for l in lignes]
    ratt = rattachements_par_ligne(conn, piece, cles)
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
    delta. C'est ce qui rend le retrait d'une ligne possible.
    """
    if objet not in OBJETS:
        raise ValueError("Objet inconnu : %r" % (objet,))
    if piece not in PIECES:
        raise ValueError("Nature de pièce inconnue : %r" % (piece,))
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
    return recalculer_etat(conn, objet, objet_id, force=etat_objet)


def _nombre(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def recalculer_etat(conn: sqlite3.Connection, objet: str, objet_id: int,
                    force: Optional[str] = None) -> Dict[str, Any]:
    """Recalcule `rvgi_etat` et le champ texte dénormalisé de l'objet.

    `force` permet de poser « hors_commande » (production sans commande, assumée)
    ou « a_rattacher » (« je ne trouve pas ») sans rattachement à l'appui.
    """
    table, champ_texte = (("planning_entries", "dos_rvgi") if objet == "dossier"
                          else ("expe_departs", "no_bl"))
    piece = "commande" if objet == "dossier" else "livraison"
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM rvgi_rattachements WHERE objet=? AND objet_id=? AND piece=?",
        (objet, int(objet_id), piece),
    )]

    # « Je ne trouve pas » et « hors commande » ne se posent que sur un objet
    # SANS rattachement : sinon l'état contredirait ce que la table contient,
    # et c'est la table qui a raison.
    if force in ("hors_commande", "a_rattacher") and not rows:
        etat = force
    elif not rows:
        etat = "a_rattacher"
    elif any(r["etat"] == "a_verifier" for r in rows):
        etat = "a_verifier"
    elif any(r["qte"] is not None and r["vu_qte"] is not None
             and float(r["qte"]) + 1e-6 < float(r["vu_qte"]) for r in rows):
        etat = "partiel"
    else:
        etat = "lie"

    # Le champ texte reste la vitrine : les numéros, sans les lignes. Il est
    # tenu à jour, jamais lu comme source — même choix que expe_departs.no_dossier.
    texte = _compacter_numeros([r["numero"] for r in rows]) or None
    maintenant = _maintenant()
    cols = {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    sets, params = [], []
    if "rvgi_etat" in cols:
        sets.append("rvgi_etat=?"); params.append(etat)
    if "rvgi_maj_le" in cols:
        sets.append("rvgi_maj_le=?"); params.append(maintenant)
    if champ_texte in cols and texte:
        sets.append("%s=?" % champ_texte); params.append(texte)
    if sets:
        params.append(int(objet_id))
        conn.execute("UPDATE %s SET %s WHERE id=?" % (table, ", ".join(sets)), params)

    return {"etat": etat, "texte": texte, "rattachements": len(rows)}


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
        objets.add((r["objet"], r["objet_id"]))
    for objet, objet_id in objets:
        recalculer_etat(conn, objet, objet_id)
    return {"vus": len(en_attente), "confirmes": confirmes, "objets": len(objets)}


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
                       ouvertes_seulement: bool = True) -> List[Dict[str, Any]]:
    """Commandes candidates, groupées, avec leurs lignes.

    `ouvertes_seulement` écarte les commandes soldées : on lance rarement une
    production sur une commande déjà livrée. Le sélecteur permet de rouvrir la
    recherche à tout, pour les reliquats et les rattrapages.
    """
    q = str(q or "").strip()
    if len(q) < 2:
        return []
    ou, params = _filtre_texte(q, ["l.numero", "e.rs", "l.des1", "l.code1", "l.code2", "l.vref"])
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
        numeros = []
        for r in c.execute(sql, params):
            num = str(r["numero"] or "").strip()
            if num and num not in numeros:
                numeros.append(num)
            if len(numeros) >= limite:
                break
        if not numeros:
            return []
        lignes = _lire_lignes_commandes(c, numeros)
    return _grouper_par_numero(lignes, limite)


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
    """
    plates = [l for g in groupes for l in g["lignes"]]
    etats = etat_des_lignes(conn, piece, plates)
    for g in groupes:
        for l in g["lignes"]:
            cle = (str(l.get("numero") or "").strip(),
                   None if l.get("ligne") is None else int(l["ligne"]))
            e = etats.get(cle) or {}
            l["rattachement"] = e
            deja = e.get("qte_rattachee")
            qte = l.get("qte")
            if qte is not None and deja is not None:
                l["reste"] = max(0.0, float(qte) - float(deja))
            else:
                l["reste"] = qte
        g["etat"] = _etat_du_groupe(g["lignes"])
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
