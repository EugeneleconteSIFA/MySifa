"""
Qui a le dernier mot sur un OF ou une fiche technique, et ce que ça coûte.

Le déstockage de production lit ces deux documents pour décider ce qui sort du
stock. Deux règles, énoncées par Eugène, gouvernent leur mise à jour :

  1. Le document le plus récent fait foi.
  2. Sauf sur ce qu'un humain a saisi : un import manuel est plus sûr qu'un
     import Access.

Prises au niveau du document, ces deux règles se contredisent — c'est ce qui
donnait deux comportements opposés selon la table. Un OF portant un PDF était
gelé en entier, y compris ses colonnes vides, et une quantité corrigée dans
Access n'arrivait jamais. Une fiche technique, elle, était intégralement
écrasée à chaque sync, correction atelier comprise.

Prises au niveau du CHAMP, elles tiennent ensemble : Access met à jour tout ce
qu'aucun humain n'a touché, et bute sur le reste. C'est ce que fait ce module.

Le second rôle du module est de périmer la validation. Le verrou documentaire
n'a de valeur que si la case se décoche quand le chiffre bouge : sinon il
atteste d'une relecture qui a bien eu lieu, mais pas sur les valeurs qui
serviront au calcul. Toute écriture sur un champ de calcul remet donc
`valide` à 0 et écrit pourquoi.

Rien n'est committé ici : l'appelant maîtrise sa transaction, et le journal
doit tomber ou survivre avec l'écriture qu'il décrit.
"""
import json
from datetime import datetime
from typing import Any, Optional

# ── Champs qui alimentent le calcul de déstockage ─────────────────────
#
# Un changement sur l'un d'eux périme la validation. La liste est volontairement
# large : `reference` et `machine` ne sont pas des quantités, mais ce sont elles
# qui décident QUELLE fiche technique est rapprochée du dossier — les changer
# change le calcul aussi sûrement qu'un métrage.

CHAMPS_CALCUL_OF = frozenset({
    "reference", "machine", "format", "laize", "matiere", "glassine",
    "adhesif_label", "ref_adhesif", "qte_adhesif_g", "qte_adhesif_kg",
    "qte_au_mille", "qte_etiquettes", "qte_bobines", "metrage",
    "conditionnement", "nb_cartons", "nb_mandrins", "nb_tubes",
    "mandrins_dia", "mandrin_longueur", "cartons_type",
})

CHAMPS_CALCUL_FT = frozenset({
    "reference", "ref_produit_norm", "machine",
    "support", "matiere", "glassine", "adhesif", "qte_au_mille",
    "eti_laize", "eti_longueur", "mod_laize", "mod_longueur", "mod_nb_front",
    "laize", "laize_optimale", "mandrin_dia", "nb_etiq_bobin",
    "nb_bobines_carton", "cartons", "conditionnement",
    "palette_type", "palette_nb_cartons_sol", "palette_nb_cartons_hauteur",
})

CHAMPS_CALCUL = {
    "of_imports": CHAMPS_CALCUL_OF,
    "fiches_techniques": CHAMPS_CALCUL_FT,
}

# Colonnes de service : jamais écrites par ce chemin, quelle que soit l'origine.
# `valide` en fait partie — on ne valide pas un document en le mettant à jour.
_INTOUCHABLES = frozenset({
    "id", "valide", "valide_par", "valide_at", "champs_manuels",
    "invalide_at", "invalide_motif", "date_import", "imported_by",
    "pdf_filename", "source", "statut",
})

# Libellés pour le message d'invalidation. Une pastille qui repasse au rouge
# sans dire pourquoi sera recochée sans être relue.
_LIBELLES = {
    "qte_etiquettes": "quantité d'étiquettes",
    "qte_bobines": "nombre de bobines",
    "metrage": "métrage",
    "laize": "laize",
    "matiere": "matière",
    "support": "support",
    "glassine": "glassine",
    "adhesif": "adhésif",
    "adhesif_label": "adhésif",
    "ref_adhesif": "référence adhésif",
    "qte_adhesif_g": "grammage adhésif",
    "qte_adhesif_kg": "quantité d'adhésif",
    "qte_au_mille": "quantité au mille",
    "nb_cartons": "nombre de cartons",
    "nb_mandrins": "nombre de mandrins",
    "nb_tubes": "nombre de tubes",
    "mandrins_dia": "diamètre mandrin",
    "mandrin_dia": "diamètre mandrin",
    "mandrin_longueur": "longueur mandrin",
    "cartons_type": "type de carton",
    "cartons": "cartons",
    "conditionnement": "conditionnement",
    "reference": "référence",
    "ref_produit_norm": "clé produit",
    "machine": "machine",
    "format": "format",
    "eti_laize": "laize étiquette",
    "eti_longueur": "longueur étiquette",
    "mod_laize": "laize module",
    "mod_longueur": "longueur module",
    "mod_nb_front": "nombre de fronts",
    "laize_optimale": "laize optimale",
    "nb_etiq_bobin": "étiquettes par bobine",
    "nb_bobines_carton": "bobines par carton",
    "palette_type": "type de palette",
    "palette_nb_cartons_sol": "cartons au sol",
    "palette_nb_cartons_hauteur": "cartons en hauteur",
}

_ORIGINES_LISIBLES = {
    "access_bridge": "Access",
    "manuel": "une saisie manuelle",
    "import_pdf": "l'import d'un PDF",
}


def libelle_champ(champ: str) -> str:
    return _LIBELLES.get(champ, champ)


def _motif_invalidation(champs, origine: str, auteur: Optional[str]) -> str:
    """Phrase affichée sur la pastille et dans le blocage du déstockage.

    L'accord porte sur « valeur », toujours féminin, et jamais sur le nom du
    champ : « le métrage » et « la laize » n'ont pas le même genre, et une
    formulation qui dépend du champ finit fausse une fois sur deux.
    """
    n = len(champs)
    qui = _ORIGINES_LISIBLES.get(origine, origine)
    if auteur:
        qui += f" ({auteur})"
    quoi = ", ".join(libelle_champ(c) for c in champs)
    tete = "valeur modifiée" if n <= 1 else f"{n} valeurs modifiées"
    return f"Validation retirée — {tete} par {qui} : {quoi}."


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def valeur_differente(ancien: Any, nouveau: Any) -> bool:
    """Comparaison tolérante : évite de réécrire 7124.0 sur 7124.0398 arrondi.

    Reprise telle quelle de api_bridge._valeur_differente, qui vivait là-bas et
    n'y avait pas sa place : les deux appelants en ont besoin.
    """
    if ancien is None and nouveau is None:
        return False
    if ancien is None or nouveau is None:
        return True
    try:
        return abs(float(ancien) - float(nouveau)) > 1e-6
    except (TypeError, ValueError):
        return str(ancien).strip() != str(nouveau).strip()


def est_vide(val: Any) -> bool:
    """Vrai si la colonne est considérée comme non renseignée."""
    return val is None or (isinstance(val, str) and not val.strip())


def champs_manuels(row) -> set:
    """Colonnes du document dont la valeur vient d'un humain.

    Tolérant à une base ancienne (colonne absente) et à un JSON abîmé : dans le
    doute on ne protège rien plutôt que de faire échouer un import.
    """
    try:
        brut = row["champs_manuels"]
    except (IndexError, KeyError):
        return set()
    if not brut:
        return set()
    try:
        val = json.loads(brut)
    except (ValueError, TypeError):
        return set()
    return {str(c) for c in val} if isinstance(val, list) else set()


def _journaliser(conn, table, doc_id, champ, avant, apres, origine, auteur,
                 etait_valide, refuse=0) -> None:
    try:
        conn.execute(
            """INSERT INTO documents_valeurs_historique
               (table_nom, doc_id, champ, avant, apres, origine, auteur, at,
                etait_valide, refuse)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (table, doc_id, champ,
             None if avant is None else str(avant),
             None if apres is None else str(apres),
             origine, auteur, _now(), 1 if etait_valide else 0, refuse),
        )
    except Exception:
        # Base non migrée : l'écriture métier ne doit pas échouer pour autant.
        # Le journal est une garantie, pas une dépendance.
        pass


def appliquer_maj(
    conn,
    table: str,
    doc_id: int,
    valeurs: dict,
    *,
    origine: str,
    auteur: Optional[str] = None,
    proteger_manuels: bool = True,
    marquer_manuels: bool = False,
    seulement_vides: bool = False,
    autoriser_effacement: bool = False,
) -> dict:
    """Écrit une mise à jour de document en arbitrant les sources.

    - `proteger_manuels` : refuse d'écraser un champ saisi par un humain. Le
      refus est journalisé (`refuse=1`) — c'est un conflit à trancher, pas un
      non-événement, et le silence était précisément le défaut d'avant.
    - `marquer_manuels` : les champs écrits deviennent protégés à leur tour.
      Vrai pour une saisie dans MySifa et pour la lecture d'un vrai PDF d'OF.
    - `seulement_vides` : ne remplit que les colonnes non renseignées
      (comportement `enrich_if_exists` du pont).
    - `autoriser_effacement` : un `None` vide la colonne au lieu d'être ignoré.
      Réservé aux saisies humaines — quand quelqu'un efface un champ dans une
      modale, c'est une décision. Un `None` venant d'Access n'en est pas une :
      c'est le plus souvent une jointure qui n'a rien donné, et l'effacer
      supprimerait une valeur juste.

    Retourne le détail de ce qui s'est passé, pour que l'appelant puisse le
    remonter à son client au lieu de répondre « ok ».
    """
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (doc_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table}#{doc_id} introuvable.")

    colonnes = set(row.keys())
    calcul = CHAMPS_CALCUL.get(table, frozenset())
    etait_valide = bool(int(row["valide"] or 0)) if "valide" in colonnes else False
    proteges_avant = champs_manuels(row) if proteger_manuels else set()

    a_ecrire: dict = {}
    conflits: list = []
    ignores: list = []
    # Un trou comblé et une valeur corrigée ne se racontent pas pareil : le
    # premier complète, le second contredit. Les scripts de sync distinguent
    # les deux dans leur bilan, et l'appelant en a besoin pour sa réponse.
    remplis: list = []
    corriges: list = []

    for champ, valeur in (valeurs or {}).items():
        if champ not in colonnes or champ in _INTOUCHABLES:
            ignores.append(champ)
            continue
        if valeur is None and not autoriser_effacement:
            continue  # une absence n'efface pas une valeur connue
        if seulement_vides and not est_vide(row[champ]):
            continue
        if not valeur_differente(row[champ], valeur):
            continue
        if champ in proteges_avant:
            conflits.append({
                "champ": champ,
                "libelle": libelle_champ(champ),
                "actuel": row[champ],
                "propose": valeur,
            })
            _journaliser(conn, table, doc_id, champ, row[champ], valeur,
                         origine, auteur, etait_valide, refuse=1)
            continue
        a_ecrire[champ] = valeur
        (remplis if est_vide(row[champ]) else corriges).append(champ)

    if not a_ecrire:
        return {
            "ecrits": [], "remplis": [], "corriges": [],
            "conflits": conflits, "ignores": sorted(set(ignores)),
            "invalide": False, "champs_invalidants": [], "motif": None,
        }

    for champ, valeur in a_ecrire.items():
        _journaliser(conn, table, doc_id, champ, row[champ], valeur,
                     origine, auteur, etait_valide)

    sets = dict(a_ecrire)

    # ── Péremption de la validation ───────────────────────────────────
    invalidants = sorted(c for c in a_ecrire if c in calcul)
    motif = None
    if invalidants and etait_valide:
        motif = _motif_invalidation(invalidants, origine,
                                    auteur if origine != "access_bridge" else None)
        sets["valide"] = 0
        sets["valide_par"] = None
        sets["valide_at"] = None
        if "invalide_at" in colonnes:
            sets["invalide_at"] = _now()
        if "invalide_motif" in colonnes:
            sets["invalide_motif"] = motif

    # ── Marquage des champs saisis par un humain ──────────────────────
    if marquer_manuels and "champs_manuels" in colonnes:
        sets["champs_manuels"] = json.dumps(
            sorted(champs_manuels(row) | set(a_ecrire))
        )

    conn.execute(
        f"UPDATE {table} SET {', '.join(f'{c}=?' for c in sets)} WHERE id=?",
        list(sets.values()) + [doc_id],
    )

    return {
        "ecrits": sorted(a_ecrire),
        "remplis": sorted(remplis),
        "corriges": sorted(corriges),
        "conflits": conflits,
        "ignores": sorted(set(ignores)),
        "invalide": motif is not None,
        "champs_invalidants": invalidants,
        "motif": motif,
    }


def marquer_champs_manuels(conn, table: str, doc_id: int, champs) -> None:
    """Ajoute des colonnes à la liste protégée sans rien écrire d'autre.

    Sert à l'import d'un PDF d'OF, qui écrit la ligne entière d'un bloc : les
    valeurs lues sur le papier sont celles d'un humain et Access ne doit plus
    les toucher.
    """
    champs = {c for c in (champs or []) if c}
    if not champs:
        return
    try:
        row = conn.execute(
            f"SELECT champs_manuels FROM {table} WHERE id=?", (doc_id,)
        ).fetchone()
    except Exception:
        return  # colonne absente : base non migrée
    if row is None:
        return
    conn.execute(
        f"UPDATE {table} SET champs_manuels=? WHERE id=?",
        (json.dumps(sorted(champs_manuels(row) | champs)), doc_id),
    )


def historique_document(conn, table: str, doc_id: int, limite: int = 50) -> list:
    """Derniers changements de valeur d'un document, du plus récent au plus ancien."""
    try:
        rows = conn.execute(
            """SELECT champ, avant, apres, origine, auteur, at, etait_valide, refuse
               FROM documents_valeurs_historique
               WHERE table_nom=? AND doc_id=?
               ORDER BY at DESC, id DESC LIMIT ?""",
            (table, doc_id, limite),
        ).fetchall()
    except Exception:
        return []
    return [{**dict(r), "libelle": libelle_champ(r["champ"])} for r in rows]


def constater_remplacement(
    conn,
    table: str,
    doc_id: int,
    avant: dict,
    *,
    origine: str,
    auteur: Optional[str] = None,
    marquer_manuels: bool = True,
) -> dict:
    """Arbitre APRÈS une réécriture complète de la ligne.

    L'import d'un PDF d'OF ne se prête pas à `appliquer_maj` : il remplace la
    ligne d'un bloc, volontairement, y compris en effaçant ce que le nouveau
    papier ne dit plus. C'est le geste le plus fiable dont on dispose et il n'y
    a pas à l'arbitrer. Reste à en tirer les mêmes conséquences que partout
    ailleurs : journaliser ce qui a bougé, périmer la validation si un chiffre
    de calcul a changé, et marquer comme humaines les colonnes renseignées.

    `avant` est le `dict(row)` pris juste avant l'écriture.
    """
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (doc_id,)).fetchone()
    if row is None:
        return {"changes": [], "invalide": False, "motif": None}

    colonnes = set(row.keys())
    calcul = CHAMPS_CALCUL.get(table, frozenset())
    etait_valide = bool(int(avant.get("valide") or 0))

    changes = []
    for champ in sorted(colonnes - _INTOUCHABLES):
        ancien, nouveau = avant.get(champ), row[champ]
        if not valeur_differente(ancien, nouveau):
            continue
        changes.append(champ)
        _journaliser(conn, table, doc_id, champ, ancien, nouveau,
                     origine, auteur, etait_valide)

    sets: dict = {}
    invalidants = sorted(c for c in changes if c in calcul)
    motif = None
    if invalidants and etait_valide:
        motif = _motif_invalidation(invalidants, origine, auteur)
        sets.update({"valide": 0, "valide_par": None, "valide_at": None})
        if "invalide_at" in colonnes:
            sets["invalide_at"] = _now()
        if "invalide_motif" in colonnes:
            sets["invalide_motif"] = motif

    if marquer_manuels and "champs_manuels" in colonnes:
        renseignes = {c for c in colonnes - _INTOUCHABLES if not est_vide(row[c])}
        if renseignes:
            sets["champs_manuels"] = json.dumps(
                sorted(champs_manuels(row) | renseignes)
            )

    if sets:
        conn.execute(
            f"UPDATE {table} SET {', '.join(f'{c}=?' for c in sets)} WHERE id=?",
            list(sets.values()) + [doc_id],
        )

    return {"changes": changes, "invalide": motif is not None, "motif": motif}
