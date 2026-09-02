"""
MyExpé — note de confiance transporteur.

La note est une moyenne pondérée des avis émis sur les expéditions, exprimée
sur 10, puis traduite en lettre de A (à utiliser en priorité) à F (à éviter).

Tout transporteur part de `NOTE_DEPART` (5/10, soit C), qui entre dans la
moyenne comme un avis de poids 1. Deux conséquences voulues : un transporteur
sur lequel personne n'a rien signalé est affiché comme neutre plutôt que comme
une case vide, et le tout premier avis ne fait pas basculer la note d'un bout à
l'autre de l'échelle — il la déplace de moitié. Cette note de départ s'efface
d'elle-même : son poids reste 1 quand celui des avis s'accumule, donc son
influence tombe à 1/(n+1).

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

En dessous de `SEUIL_FIABILITE` avis, la note est marquée provisoire, et tant
qu'aucun avis n'a été émis elle est marquée `par_defaut` : l'écran doit pouvoir
dire « note de départ » plutôt que laisser croire à un jugement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.services import expe_regions

# Note attribuée à un transporteur sur lequel rien n'a encore été signalé, et
# poids qu'elle garde dans la moyenne (celui d'un avis).
NOTE_DEPART = 5.0
POIDS_NOTE_DEPART = 1.0

# Bornes basses de chaque lettre, sur 10. Lues de haut en bas.
#
# L'échelle est centrée sur NOTE_DEPART : C est la bande neutre et la plus
# large, et 5/10 tombe dedans avec de la marge des deux côtés. Déplacer ces
# bornes sans déplacer NOTE_DEPART ferait démarrer tout le monde à « À
# surveiller » — le contraire de ce qu'une note de départ veut dire.
SEUILS_LETTRE: list[tuple[float, str]] = [
    (8.5, "A"),
    (7.0, "B"),
    (4.5, "C"),
    (3.0, "D"),
    (1.5, "E"),
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

# ── Score de pertinence par zone (écran Zone géographique) ──
#
# Deux moitiés, et rien d'autre : ce que valent les avis, et ce que le
# transporteur a réellement transporté sur la zone. Les deux poids font 1.
POIDS_NOTE = 0.50
POIDS_EXPERIENCE = 0.50

# Récence d'un transport, en jours : 3, 6, 12 puis 24 mois. Premier palier
# atteint = poids retenu. Le premier palier est plus court que celui des avis :
# un transport récent dit que la ligne tourne aujourd'hui, un avis récent dit
# seulement que le jugement est frais.
PALIERS_RECENCE_TRANSPORT: list[tuple[int, float]] = [
    (91, 1.0),
    (183, 0.75),
    (365, 0.5),
    (730, 0.25),
]
POIDS_TRANSPORT_ANCIEN = 0.1


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
    # La note de départ entre dans la moyenne comme un avis, et n'est jamais
    # comptée dans `nb_avis` : elle n'est le jugement de personne.
    somme = NOTE_DEPART * POIDS_NOTE_DEPART
    total_poids = POIDS_NOTE_DEPART
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
        # Aucun avis : la note affichée est la note de départ, pas un jugement.
        "par_defaut": nb_avis == 0,
        "provisoire": 0 < nb_avis < SEUIL_FIABILITE,
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
    """Résout une saisie ville ou code postal en département, puis en région.

    Le référentiel de villes est celui des clients : ce sont exactement les
    destinations vers lesquelles SIFA expédie. Chercher une commune que
    personne n'a jamais livrée n'apporterait rien de plus qu'un code postal
    saisi à la main, qui reste accepté.

    Le département reste calculé — c'est lui qui porte le délai indicatif — mais
    c'est la région qui sert de zone de classement.
    """
    cp_txt = (cp or "").strip()
    ville_txt = (ville or "").strip()

    if not cp_txt and ville_txt and ville_txt[:2].isdigit():
        # L'utilisateur a tapé un code postal dans le champ ville.
        cp_txt, ville_txt = ville_txt, ""

    def _sortie(cp_out: str, ville_out: str, dept: str) -> dict:
        region = expe_regions.region_du_departement(dept)
        return {
            "cp": cp_out,
            "ville": ville_out,
            "departement": dept,
            "region": region,
            "region_nom": expe_regions.nom_region(region),
        }

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
        return _sortie(cp_txt, ville_trouvee, dept)

    if ville_txt:
        cible = _norm_texte(ville_txt)
        rows = conn.execute(
            "SELECT ville, cp FROM clients WHERE ville IS NOT NULL AND ville <> '' "
            "AND cp IS NOT NULL AND cp <> ''"
        ).fetchall()
        for row in rows:
            if _norm_texte(row["ville"]) == cible:
                return _sortie(row["cp"], row["ville"], _norm_dept(row["cp"]))
        for row in rows:
            if cible and cible in _norm_texte(row["ville"]):
                return _sortie(row["cp"], row["ville"], _norm_dept(row["cp"]))

    return _sortie("", ville_txt, "")


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
        dept = _norm_dept(cle[1])
        item = {
            "ville": cle[0],
            "cp": cle[1],
            "departement": dept,
            "region": expe_regions.region_du_departement(dept),
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


def poids_recence_transport(date_depart: Any, maintenant: datetime) -> float:
    """Poids d'un transport selon son âge, par paliers.

    Même logique que l'ancienneté des avis, avec un premier palier plus court :
    un transport d'il y a deux mois prouve que la ligne tourne aujourd'hui, un
    transport d'il y a deux ans prouve seulement qu'elle a tourné. Un transport
    sans date lisible compte pour le palier le plus faible plutôt que d'être
    ignoré : il a bien eu lieu.
    """
    dt = _parse_iso(date_depart)
    if dt is None:
        return POIDS_TRANSPORT_ANCIEN
    jours = max(0, (maintenant - dt).days)
    for limite, poids in PALIERS_RECENCE_TRANSPORT:
        if jours <= limite:
            return poids
    return POIDS_TRANSPORT_ANCIEN


def _usages_par_region(conn) -> dict[str, dict[int, dict]]:
    """Historique des départs, groupé par région puis par transporteur.

    Une seule passe sur `expe_departs` : la carte demande toutes les régions
    d'un coup, et refaire un balayage par région coûterait dix-huit fois le
    même travail.

    L'expérience d'un transporteur sur une région n'est pas son nombre de
    départs mais leur somme pondérée par la récence — dix départs de 2019 ne
    valent pas dix départs du trimestre.
    """
    transporteurs = conn.execute(
        "SELECT id, nom FROM expe_transporteurs"
    ).fetchall()
    par_nom = {_norm_texte(t["nom"]): t["id"] for t in transporteurs}
    maintenant = datetime.now()

    usages: dict[str, dict[int, dict]] = {}
    departs = conn.execute(
        """SELECT transporteur_id, transporteur, code_postal_destination,
                  date_enlevement
             FROM expe_departs
            WHERE code_postal_destination IS NOT NULL
              AND code_postal_destination <> ''"""
    ).fetchall()
    for dep in departs:
        region = expe_regions.region_du_departement(
            _norm_dept(dep["code_postal_destination"])
        )
        if not region:
            continue
        trp_id = dep["transporteur_id"]
        if not trp_id:
            trp_id = par_nom.get(_norm_texte(dep["transporteur"]))
        if not trp_id:
            continue
        entree = usages.setdefault(region, {}).setdefault(
            trp_id, {"nb": 0, "dernier": "", "poids": 0.0}
        )
        entree["nb"] += 1
        date_dep = str(dep["date_enlevement"] or "")[:10]
        entree["poids"] += poids_recence_transport(date_dep, maintenant)
        if date_dep > entree["dernier"]:
            entree["dernier"] = date_dep
    return usages


def _note_de(trp) -> tuple[Optional[float], Optional[str], int]:
    cles = trp.keys()
    valeur = trp["note_valeur"] if "note_valeur" in cles else None
    lettre = trp["note_lettre"] if "note_lettre" in cles else None
    nb = (trp["note_nb_avis"] if "note_nb_avis" in cles else 0) or 0
    return valeur, lettre, nb


def _classer(
    transporteurs: list,
    usages_region: dict[int, dict],
    zone_col: str,
) -> list[dict]:
    """Score de pertinence : note de confiance et expérience sur la région.

    Deux moitiés, et rien d'autre : ce que valent les avis (`POIDS_NOTE`) et ce
    que le transporteur a réellement transporté sur la zone, pondéré par la
    récence de ces transports (`POIDS_EXPERIENCE`). L'expérience est rapportée
    au mieux-disant de la région : c'est un classement relatif, pas une note
    absolue — sur une région où personne n'a beaucoup roulé, celui qui a roulé
    le plus prend quand même les points.

    Un transporteur jamais utilisé sur la zone n'est pas écarté — il descend en
    bas de liste, signalé comme piste non testée. Sinon le classement ne ferait
    que reconduire les habitudes, et un bon transporteur n'aurait jamais sa
    première chance.
    """
    max_poids = max([u.get("poids", 0.0) for u in usages_region.values()], default=0.0)
    resultats: list[dict] = []
    for trp in transporteurs:
        usage = usages_region.get(trp["id"], {"nb": 0, "dernier": "", "poids": 0.0})
        nb = usage["nb"]
        dernier = usage["dernier"]
        poids_exp = float(usage.get("poids", 0.0))
        note_valeur, note_lettre, nb_avis = _note_de(trp)

        # `note_valeur` est nulle seulement si le cache n'a jamais été calculé ;
        # on retombe alors sur la note de départ, comme le calcul lui-même.
        base = NOTE_DEPART if note_valeur is None else float(note_valeur)
        score_note = base / 10.0
        score_exp = (poids_exp / max_poids) if max_poids else 0.0
        points_note = score_note * POIDS_NOTE * 100
        points_exp = score_exp * POIDS_EXPERIENCE * 100
        score = score_note * POIDS_NOTE + score_exp * POIDS_EXPERIENCE

        eligible = bool(trp[zone_col]) if zone_col else True
        if not eligible:
            score *= 0.4

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
                "experience": round(poids_exp, 2),
                "experience_max": round(max_poids, 2),
                # Les deux moitiés du score, AVANT la pénalité hors zone : le
                # détail dépliable de l'écran montre d'où viennent les points,
                # et une somme qui ne retombe pas sur le total afficherait un
                # calcul faux plutôt qu'une pénalité.
                "points_note": round(points_note, 1),
                "points_experience": round(points_exp, 1),
                "derniere_expedition": dernier or "",
                "eligible_zone": eligible,
                "jamais_utilise": nb == 0,
                "score": round(score * 100, 1),
            }
        )
    resultats.sort(key=lambda r: (-r["score"], r["transporteur"]))
    for rang, item in enumerate(resultats, start=1):
        item["rang"] = rang
    return resultats


def recommander_transporteurs(
    conn,
    region: str,
    type_envoi: str = "",
    limite: int = 0,
) -> list[dict]:
    """Classe les transporteurs actifs pour une région."""
    code = expe_regions.normaliser(region)
    if not code:
        return []
    transporteurs = conn.execute(
        "SELECT * FROM expe_transporteurs WHERE actif = 1 ORDER BY nom"
    ).fetchall()
    if not transporteurs:
        return []

    usages = _usages_par_region(conn).get(code, {})
    zone_col = _zone_colonne(type_envoi) if type_envoi else ""
    resultats = _classer(transporteurs, usages, zone_col)

    # Grille tarifaire connue sur la région : information affichée, pas critère
    # de classement — une grille absente ne dit rien de la qualité du service.
    # Une grille sur un seul département de la région suffit à l'afficher : le
    # transporteur y a bien un tarif.
    depts = list(expe_regions.departements_de(code))
    trous = ",".join("?" for _ in depts)
    like = " OR ".join(["zone_valeur LIKE ?"] * len(depts))
    for item in resultats:
        tarif = conn.execute(
            f"""SELECT 1 FROM expe_tarifs
                 WHERE transporteur_id = ? AND actif = 1
                   AND ((zone_type = 'departement' AND zone_valeur IN ({trous}))
                     OR (zone_type = 'code_postal' AND ({like})))
                 LIMIT 1""",
            [item["transporteur_id"]] + depts + [d + "%" for d in depts],
        ).fetchone()
        item["grille_tarifaire"] = bool(tarif)

    return resultats[:limite] if limite else resultats


def carte_zones(conn, type_envoi: str = "") -> dict:
    """Pour chaque région, le transporteur à prioriser et l'historique.

    Alimente la carte de France de l'écran Zone géographique : une région se
    colore de la couleur du transporteur recommandé, et n'est coloriée que si
    elle a une histoire — une région jamais livrée reste neutre plutôt que
    d'afficher une recommandation fabriquée de toutes pièces.
    """
    transporteurs = conn.execute(
        "SELECT * FROM expe_transporteurs WHERE actif = 1 ORDER BY nom"
    ).fetchall()
    if not transporteurs:
        return {}
    zone_col = _zone_colonne(type_envoi) if type_envoi else ""
    usages = _usages_par_region(conn)

    carte: dict[str, dict] = {}
    for region, usages_region in usages.items():
        classement = _classer(transporteurs, usages_region, zone_col)
        if not classement:
            continue
        premier = classement[0]
        carte[region] = {
            "region": region,
            "region_nom": expe_regions.nom_region(region),
            "transporteur_id": premier["transporteur_id"],
            "transporteur": premier["transporteur"],
            "couleur": premier["couleur"],
            "note_lettre": premier["note_lettre"],
            "nb_expeditions": sum(u["nb"] for u in usages_region.values()),
            "nb_transporteurs": len([u for u in usages_region.values() if u["nb"]]),
        }
    return carte
