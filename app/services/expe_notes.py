"""
MyExpé — note de confiance transporteur.

La note est une moyenne pondérée des avis émis sur les expéditions, exprimée
sur 10, puis traduite en lettre de A (à utiliser en priorité) à F (à éviter).

Trois pondérations, et une seule raison pour chacune :

* **La thématique.** Un colis perdu ne pèse pas comme un retard d'une heure.
  Le poids vit dans `expe_avis_thematiques.poids`, réglable sans toucher au
  code.
* **L'ancienneté.** Un incident d'il y a trois ans ne dit plus rien du
  transporteur d'aujourd'hui. Le poids décroît par paliers, pas en continu :
  un palier se lit dans l'historique (« cet avis compte pour moitié »), une
  exponentielle non.
* **L'ajustement manuel.** Il s'ajoute en points à la moyenne, il ne l'écrase
  pas. Écraser la note ferait de tout le mécanisme d'avis une décoration.

La note n'existe pas tant qu'aucun avis n'a été émis : afficher C par défaut
reviendrait à affirmer quelque chose qu'on ne sait pas. En dessous de
`SEUIL_FIABILITE` avis, elle est marquée provisoire.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

# Bornes basses de chaque lettre, sur 10. Lues de haut en bas.
SEUILS_LETTRE: list[tuple[float, str]] = [
    (9.0, "A"),
    (8.0, "B"),
    (6.5, "C"),
    (5.0, "D"),
    (3.5, "E"),
]

LETTRE_LIBELLE: dict[str, str] = {
    "A": "À utiliser en priorité",
    "B": "Fiable",
    "C": "Correct",
    "D": "À surveiller",
    "E": "Problématique",
    "F": "À éviter",
}

# En dessous de ce nombre d'avis, la note est affichée mais marquée provisoire.
SEUIL_FIABILITE = 3

# Amortissement par ancienneté, en jours. Premier palier atteint = poids retenu.
PALIERS_ANCIENNETE: list[tuple[int, float]] = [
    (183, 1.0),
    (365, 0.75),
    (730, 0.5),
]
POIDS_ANCIEN = 0.25

NOTE_MIN = 0.0
NOTE_MAX = 10.0

# Amplitude maximale d'un ajustement manuel, en points.
AJUSTEMENT_MAX = 3.0


def lettre_pour(valeur: Optional[float]) -> Optional[str]:
    """Traduit une note /10 en lettre. Renvoie None si la note n'existe pas."""
    if valeur is None:
        return None
    for borne, lettre in SEUILS_LETTRE:
        if valeur >= borne:
            return lettre
    return "F"


def libelle_lettre(lettre: Optional[str]) -> str:
    return LETTRE_LIBELLE.get(lettre or "", "Non noté")


def _parse_iso(valeur: Any) -> Optional[datetime]:
    txt = str(valeur or "").strip()
    if not txt:
        return None
    txt = txt.replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def poids_anciennete(created_at: Any, maintenant: Optional[datetime] = None) -> float:
    """Poids d'un avis selon son âge. Un avis sans date est traité comme récent."""
    dt = _parse_iso(created_at)
    if dt is None:
        return 1.0
    ref = maintenant or datetime.now()
    jours = max(0, (ref - dt).days)
    for limite, poids in PALIERS_ANCIENNETE:
        if jours <= limite:
            return poids
    return POIDS_ANCIEN


def _clamp(valeur: float) -> float:
    return max(NOTE_MIN, min(NOTE_MAX, valeur))


def calculer_note(conn, transporteur_id: int) -> dict:
    """Calcule la note d'un transporteur à partir de ses avis et ajustements."""
    lignes = conn.execute(
        """
        SELECT a.id, a.type, a.sens, a.note, a.ajustement, a.created_at,
               COALESCE(t.poids, 1.0) AS poids_them
          FROM expe_transporteur_avis a
          LEFT JOIN expe_avis_thematiques t ON t.id = a.thematique_id
         WHERE a.transporteur_id = ?
        """,
        (transporteur_id,),
    ).fetchall()

    maintenant = datetime.now()
    somme = 0.0
    total_poids = 0.0
    nb_avis = 0
    nb_alertes = 0
    ajustement_total = 0.0

    for ligne in lignes:
        if (ligne["type"] or "avis") == "ajustement":
            ajustement_total += float(ligne["ajustement"] or 0)
            continue
        note = ligne["note"]
        if note is None:
            continue
        poids = float(ligne["poids_them"] or 1.0) * poids_anciennete(
            ligne["created_at"], maintenant
        )
        if poids <= 0:
            continue
        somme += float(note) * poids
        total_poids += poids
        nb_avis += 1
        if (ligne["sens"] or "") == "alerte":
            nb_alertes += 1

    ajustement_total = max(-AJUSTEMENT_MAX, min(AJUSTEMENT_MAX, ajustement_total))

    if nb_avis == 0:
        # Un ajustement seul ne fabrique pas une note : il n'y a rien à ajuster.
        return {
            "valeur": None,
            "lettre": None,
            "libelle": libelle_lettre(None),
            "nb_avis": 0,
            "nb_alertes": 0,
            "ajustement": round(ajustement_total, 2),
            "provisoire": False,
            "moyenne_brute": None,
        }

    moyenne = somme / total_poids
    valeur = _clamp(moyenne + ajustement_total)
    lettre = lettre_pour(valeur)
    return {
        "valeur": round(valeur, 2),
        "lettre": lettre,
        "libelle": libelle_lettre(lettre),
        "nb_avis": nb_avis,
        "nb_alertes": nb_alertes,
        "ajustement": round(ajustement_total, 2),
        "provisoire": nb_avis < SEUIL_FIABILITE,
        "moyenne_brute": round(moyenne, 2),
    }


def recalculer_note(conn, transporteur_id: int) -> dict:
    """Recalcule et met en cache la note d'un transporteur."""
    note = calculer_note(conn, transporteur_id)
    conn.execute(
        """UPDATE expe_transporteurs
              SET note_valeur = ?, note_lettre = ?, note_nb_avis = ?,
                  note_maj_le = datetime('now')
            WHERE id = ?""",
        (note["valeur"], note["lettre"], note["nb_avis"], transporteur_id),
    )
    return note


def recalculer_toutes(conn) -> int:
    rows = conn.execute("SELECT id FROM expe_transporteurs").fetchall()
    for row in rows:
        recalculer_note(conn, row["id"])
    return len(rows)


# ─── Recommandation par zone géographique ──────────────────────────


def _norm_dept(cp: str) -> str:
    """Département depuis un code postal (Corse et DOM compris)."""
    txt = (cp or "").strip().upper()
    if len(txt) < 2:
        return txt
    if txt.startswith("97") and len(txt) >= 3:
        return txt[:3]
    if txt.startswith("20") and len(txt) == 5 and txt.isdigit():
        return "2A" if int(txt) <= 20190 else "2B"
    return txt[:2]


def _norm_texte(valeur: Any) -> str:
    import unicodedata

    txt = str(valeur or "").strip().lower()
    txt = unicodedata.normalize("NFD", txt)
    return "".join(c for c in txt if unicodedata.category(c) != "Mn")


def resoudre_destination(conn, ville: str = "", cp: str = "") -> dict:
    """Résout une saisie ville ou code postal en département.

    Le référentiel de villes est celui des clients : ce sont exactement les
    destinations vers lesquelles SIFA expédie. Chercher une commune que
    personne n'a jamais livrée n'apporterait rien de plus qu'un code postal
    saisi à la main, qui reste accepté.
    """
    cp_txt = (cp or "").strip()
    ville_txt = (ville or "").strip()

    if not cp_txt and ville_txt and ville_txt[:2].isdigit():
        # L'utilisateur a tapé un code postal dans le champ ville.
        cp_txt, ville_txt = ville_txt, ""

    if cp_txt:
        dept = _norm_dept(cp_txt)
        ville_trouvee = ""
        row = conn.execute(
            "SELECT ville FROM clients WHERE cp = ? AND ville IS NOT NULL "
            "AND ville <> '' LIMIT 1",
            (cp_txt,),
        ).fetchone()
        if row:
            ville_trouvee = row["ville"]
        return {"cp": cp_txt, "ville": ville_trouvee, "departement": dept}

    if ville_txt:
        cible = _norm_texte(ville_txt)
        rows = conn.execute(
            "SELECT ville, cp FROM clients WHERE ville IS NOT NULL AND ville <> '' "
            "AND cp IS NOT NULL AND cp <> ''"
        ).fetchall()
        for row in rows:
            if _norm_texte(row["ville"]) == cible:
                return {
                    "cp": row["cp"],
                    "ville": row["ville"],
                    "departement": _norm_dept(row["cp"]),
                }
        for row in rows:
            if cible and cible in _norm_texte(row["ville"]):
                return {
                    "cp": row["cp"],
                    "ville": row["ville"],
                    "departement": _norm_dept(row["cp"]),
                }

    return {"cp": "", "ville": ville_txt, "departement": ""}


def chercher_villes(conn, requete: str, limite: int = 12) -> list[dict]:
    """Suggestions ville/code postal pour l'autocomplétion de l'écran Zones."""
    cible = _norm_texte(requete)
    if len(cible) < 2:
        return []
    rows = conn.execute(
        "SELECT DISTINCT ville, cp FROM clients "
        "WHERE ville IS NOT NULL AND ville <> '' AND cp IS NOT NULL AND cp <> '' "
        "ORDER BY ville"
    ).fetchall()
    vus: set[tuple[str, str]] = set()
    debut: list[dict] = []
    contient: list[dict] = []
    for row in rows:
        cle = (str(row["ville"]).strip(), str(row["cp"]).strip())
        if cle in vus:
            continue
        vus.add(cle)
        nom = _norm_texte(row["ville"])
        item = {
            "ville": cle[0],
            "cp": cle[1],
            "departement": _norm_dept(cle[1]),
        }
        if nom.startswith(cible) or cle[1].startswith(requete.strip()):
            debut.append(item)
        elif cible in nom:
            contient.append(item)
    return (debut + contient)[:limite]


def _zone_colonne(type_envoi: str) -> str:
    return {
        "messagerie": "zone_messagerie",
        "ramasse": "zone_messagerie",
        "affretement": "zone_affretement",
    }.get(type_envoi, "zone_france")


def recommander_transporteurs(
    conn,
    departement: str,
    type_envoi: str = "",
    limite: int = 0,
) -> list[dict]:
    """Classe les transporteurs actifs pour une destination.

    Le score mélange trois choses, dans cet ordre d'importance : la note de
    confiance, l'expérience réelle sur la zone, et la fraîcheur de cette
    expérience. Un transporteur jamais utilisé sur la zone n'est pas écarté —
    il apparaît en bas, signalé comme piste non testée, sinon la liste ne
    ferait que reconduire les habitudes.
    """
    dept = (departement or "").strip().upper()
    if not dept:
        return []

    transporteurs = conn.execute(
        "SELECT * FROM expe_transporteurs WHERE actif = 1 ORDER BY nom"
    ).fetchall()
    if not transporteurs:
        return []

    par_nom = {_norm_texte(t["nom"]): t["id"] for t in transporteurs}

    # Historique : tous les départs vers ce département, validés ou non.
    usages: dict[int, dict] = {}
    departs = conn.execute(
        """SELECT transporteur_id, transporteur, code_postal_destination,
                  date_enlevement
             FROM expe_departs
            WHERE code_postal_destination IS NOT NULL
              AND code_postal_destination <> ''"""
    ).fetchall()
    for dep in departs:
        if _norm_dept(dep["code_postal_destination"]) != dept:
            continue
        trp_id = dep["transporteur_id"]
        if not trp_id:
            trp_id = par_nom.get(_norm_texte(dep["transporteur"]))
        if not trp_id:
            continue
        entree = usages.setdefault(trp_id, {"nb": 0, "dernier": ""})
        entree["nb"] += 1
        date_dep = str(dep["date_enlevement"] or "")[:10]
        if date_dep > entree["dernier"]:
            entree["dernier"] = date_dep

    max_usage = max([u["nb"] for u in usages.values()], default=0)
    maintenant = datetime.now()
    zone_col = _zone_colonne(type_envoi) if type_envoi else ""

    resultats: list[dict] = []
    for trp in transporteurs:
        usage = usages.get(trp["id"], {"nb": 0, "dernier": ""})
        nb = usage["nb"]
        dernier = usage["dernier"]

        note_valeur = trp["note_valeur"] if "note_valeur" in trp.keys() else None
        note_lettre = trp["note_lettre"] if "note_lettre" in trp.keys() else None
        nb_avis = (trp["note_nb_avis"] if "note_nb_avis" in trp.keys() else 0) or 0

        # Sans note, on ne suppose ni bien ni mal : score neutre.
        score_note = 0.5 if note_valeur is None else float(note_valeur) / 10.0
        score_usage = (nb / max_usage) if max_usage else 0.0

        score_recence = 0.0
        dt_dernier = _parse_iso(dernier)
        if dt_dernier is not None:
            jours = max(0, (maintenant - dt_dernier).days)
            if jours <= 90:
                score_recence = 1.0
            elif jours <= 365:
                score_recence = 0.6
            elif jours <= 730:
                score_recence = 0.3

        score = score_note * 0.55 + score_usage * 0.30 + score_recence * 0.15

        eligible = True
        if zone_col:
            eligible = bool(trp[zone_col])
        if not eligible:
            score *= 0.4

        # Grille tarifaire connue sur la zone : information, pas critère.
        tarif = conn.execute(
            """SELECT 1 FROM expe_tarifs
                WHERE transporteur_id = ? AND actif = 1
                  AND ((zone_type = 'departement' AND zone_valeur = ?)
                    OR (zone_type = 'code_postal' AND zone_valeur LIKE ?))
                LIMIT 1""",
            (trp["id"], dept, dept + "%"),
        ).fetchone()

        resultats.append(
            {
                "transporteur_id": trp["id"],
                "transporteur": trp["nom"],
                "couleur": trp["couleur"] or "",
                "note_valeur": note_valeur,
                "note_lettre": note_lettre,
                "note_libelle": libelle_lettre(note_lettre),
                "nb_avis": nb_avis,
                "nb_expeditions": nb,
                "derniere_expedition": dernier or "",
                "grille_tarifaire": bool(tarif),
                "eligible_zone": eligible,
                "jamais_utilise": nb == 0,
                "score": round(score * 100, 1),
            }
        )

    resultats.sort(key=lambda r: (-r["score"], r["transporteur"]))
    for rang, item in enumerate(resultats, start=1):
        item["rang"] = rang
    return resultats[:limite] if limite else resultats
