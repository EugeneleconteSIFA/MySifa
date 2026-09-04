"""Types d'article RVGI et familles MySifa — le referentiel des receptions.

Deux questions differentes sur une meme ligne d'achat :

- **De quoi s'agit-il ?** RVGI le sait : `cdf_ligne.type` porte 18 valeurs
  (Thermiques, Glassines, Adhesifs, Cliches, Outil de decoupe...). Les libelles
  ne sont pas codes dans WinDev comme on l'a longtemps cru : ils se lisent dans
  `fic_para`, la table de parametrage de l'ERP.
- **Quelle nature d'achat ?** RVGI ne le dit pas. Matiere, sous-traitance,
  outillage, consommable : c'est un regroupement MySifa, stocke dans
  `erp_type_famille` et editable depuis Parametres.

Le premier se lit dans le miroir, le second dans la base de production. Aucun
des deux n'est ecrit en dur ici — sauf les deux exceptions documentees plus
bas, qui ne sont pas des matieres et n'ont donc aucun bloc dans `fic_para`.

## Comment `fic_para` nomme les types

Un parametre porte un `numero` de la forme `15 TT PP`, ou `TT` est le type de
matiere sur deux chiffres et `PP` le rang du parametre. Le libelle du type est
le suffixe de `des1` apres « : » :

    150702  « Avec gestion par fournisseur : Adhesifs »   -> type matiere 07
    151765  « Ua par defaut : Cartons »                   -> type matiere 17

On prend le suffixe MAJORITAIRE du bloc, pas le premier venu : RVGI porte ses
propres coquilles de recopie (`150705` annonce « Encres » au milieu du bloc
des adhesifs, `150805` annonce « Cliches » au milieu de celui des encres).
Sur un bloc d'une vingtaine de parametres, la majorite tranche seule.

## Le decalage de deux

`cdf_ligne.type` n'est pas `mat_mat.type` : la ligne d'achat reserve ses deux
premiers rangs a ce qui n'est pas une matiere — 1 pour l'article achete
(la sous-traitance), 2 pour l'outil de decoupe. Le reste suit avec deux de
decalage.

    cdf_ligne.type = mat_mat.type + 2

Verifie sur les donnees le 02/09/2026, sur les types purs : adhesifs 9 -> 7
(169 lignes sur 169), encres 10 -> 8 (462 sur 462), cliches 11 -> 9 (702 sur
703). Quand les deux divergent sur une ligne, c'est une erreur de saisie RVGI,
pas un defaut de correspondance — et **c'est le type de la ligne d'achat qui
fait foi**, puisque c'est lui qui decrit ce qui a ete commande.
"""

import os

# Les quatre familles, dans l'ordre d'affichage. La cle vit en base, le libelle
# est ici : renommer « Matiere premiere » ne doit pas obliger a reecrire les
# lignes de `erp_type_famille`.
FAMILLES = [
    ("matiere",        "Matière première"),
    ("sous_traitance", "Sous-traitance"),
    ("outillage",      "Outillage et clichés"),
    ("consommable",    "Consommables et emballage"),
]
LIBELLE_FAMILLE = dict(FAMILLES)

# Les deux types qui ne sont pas des matieres, donc sans bloc dans `fic_para`.
# Leur nature est structurelle et se verifie sur les donnees : le type 1 pointe
# `fic_art`, le type 2 pointe `out_dec`. Ce sont les seuls libelles en dur.
TYPES_HORS_MATIERE = {
    1: "Article (sous-traitance)",
    2: "Outil de découpe",
}

_cache = {"cle": None, "libelles": {}}


def _suffixe(des1):
    """« Ua par defaut : Cartons » -> « Cartons ». Rien sans « : »."""
    if not des1 or ":" not in str(des1):
        return ""
    return str(des1).rsplit(":", 1)[1].strip()


def _libelles_depuis_miroir(conn):
    """{code cdf_ligne.type -> libelle}, lu dans `fic_para`.

    Un bloc dont aucun parametre ne porte de suffixe exploitable ne donne
    rien : le type s'affichera brut plutot que sous un libelle invente.
    """
    try:
        rows = conn.execute(
            "SELECT numero, des1 FROM fic_para "
            "WHERE corbeille = 0 AND numero BETWEEN 150100 AND 159999"
        ).fetchall()
    except Exception:
        return {}

    comptes = {}
    for r in rows:
        try:
            numero = int(r["numero"])
        except (TypeError, ValueError):
            continue
        type_matiere = (numero - 150000) // 100
        if type_matiere < 1 or type_matiere > 97:
            continue
        suffixe = _suffixe(r["des1"])
        # Un suffixe purement numerique (« Ua par defaut : 2 ») est un bloc
        # sans nom, pas un type appele « 2 ».
        if not suffixe or suffixe.isdigit():
            continue
        comptes.setdefault(type_matiere + 2, {})
        comptes[type_matiere + 2][suffixe] = comptes[type_matiere + 2].get(suffixe, 0) + 1

    return {
        code: max(paires.items(), key=lambda kv: (kv[1], kv[0]))[0]
        for code, paires in comptes.items() if paires
    }


def libelles_types():
    """{code -> libelle} pour tous les types d'article de RVGI.

    Mis en cache sur la date du miroir : le fichier ne bouge qu'a la synchro,
    et relire `fic_para` a chaque ligne de chaque page serait absurde.
    """
    from app.services import erp_mirror as miroir

    if not miroir.miroir_present():
        return dict(TYPES_HORS_MATIERE)
    try:
        cle = os.path.getmtime(miroir.ERP_MIRROR_DB)
    except OSError:
        cle = None
    if cle is not None and _cache["cle"] == cle:
        return dict(_cache["libelles"])

    libelles = dict(TYPES_HORS_MATIERE)
    try:
        with miroir.get_erp_db() as conn:
            libelles.update(_libelles_depuis_miroir(conn))
    except Exception:
        # Miroir illisible : on rend ce qu'on sait, l'ecran affichera les
        # autres codes bruts. Une page sans libelle vaut mieux qu'une erreur.
        pass

    _cache["cle"] = cle
    _cache["libelles"] = libelles
    return dict(libelles)


def familles_par_type(conn=None):
    """{code -> cle de famille}, tel que Parametres l'a arrete."""
    def _lire(c):
        return {
            int(r["type_code"]): (r["famille"] or "").strip()
            for r in c.execute(
                "SELECT type_code, famille FROM erp_type_famille"
            ).fetchall()
        }

    try:
        if conn is not None:
            return _lire(conn)
        from database import get_db
        with get_db() as c:
            return _lire(c)
    except Exception:
        return {}


def libelles_secours(conn=None):
    """{code -> libelle de secours} pose par la migration.

    Sert quand `fic_para` n'est pas dans le miroir : l'ecran garde des noms
    lisibles au lieu d'une colonne de nombres.
    """
    def _lire(c):
        return {
            int(r["type_code"]): (r["libelle_secours"] or "").strip()
            for r in c.execute(
                "SELECT type_code, libelle_secours FROM erp_type_famille"
            ).fetchall()
            if (r["libelle_secours"] or "").strip()
        }

    try:
        if conn is not None:
            return _lire(conn)
        from database import get_db
        with get_db() as c:
            return _lire(c)
    except Exception:
        return {}


def types_vus_en_achat():
    """{code -> nombre de lignes de reception}, pour Parametres.

    L'ecran de reglage part de ce que l'ERP contient VRAIMENT, pas de la liste
    deja classee : un type qui apparait dans une nouvelle reception doit se
    presenter tout seul a l'arbitrage.
    """
    from app.services import erp_mirror as miroir

    if not miroir.miroir_present():
        return {}
    sql = (
        "SELECT c.type AS t, COUNT(*) AS n "
        "FROM lif_ligne l "
        "JOIN cdf_ligne c ON c.numero = l.numero AND c.ligne = l.ligne "
        "                AND c.corbeille = 0 "
        "WHERE l.corbeille = 0 AND c.type IS NOT NULL "
        "GROUP BY c.type"
    )
    try:
        with miroir.get_erp_db() as conn:
            return {int(r["t"]): int(r["n"]) for r in conn.execute(sql).fetchall()}
    except Exception:
        return {}


def enums():
    """Les trois enumerations que l'ecran Receptions consomme.

    - `type_article`   : le code -> son libelle RVGI, pour la colonne detaillee.
    - `famille_article`: le meme code -> le libelle de sa famille, pour la
      colonne de regroupement. Deux colonnes sur la meme valeur SQL, deux
      lectures differentes.
    - `famille_article_filtre` : les cles sont des LISTES de codes jointes par
      « | ». Le moteur sait deja developper un filtre d'enumeration multi-codes
      en `IN (...)` — c'est ce qui permet de filtrer « Matiere premiere » d'un
      geste sans joindre la base de production a la requete.
    """
    libelles = libelles_types()
    familles = familles_par_type()
    secours = libelles_secours()

    type_article = {}
    for code in set(libelles) | set(familles) | set(secours):
        nom = libelles.get(code) or secours.get(code)
        if nom:
            type_article[str(code)] = nom

    famille_article = {
        str(code): LIBELLE_FAMILLE[cle]
        for code, cle in familles.items() if cle in LIBELLE_FAMILLE
    }

    famille_filtre = {}
    for cle, libelle in FAMILLES:
        codes = sorted(c for c, f in familles.items() if f == cle)
        if codes:
            famille_filtre["|".join(str(c) for c in codes)] = libelle

    return {
        "type_article": type_article,
        "famille_article": famille_article,
        "famille_article_filtre": famille_filtre,
    }


# ── Écran de réglage ─────────────────────────────────────────────────────────

def etat_parametres(conn=None):
    """Ce que Paramètres affiche : un type par ligne, classé ou non.

    La liste part de ce que l'ERP contient VRAIMENT — les types vus sur les
    lignes de réception — et non de la table de classement. Un type qui
    apparaît dans une nouvelle réception se présente donc tout seul à
    l'arbitrage, avec son nombre de lignes, au lieu d'attendre que quelqu'un
    remarque une colonne Famille vide sur l'écran des réceptions.
    """
    libelles = libelles_types()
    familles = familles_par_type(conn)
    secours = libelles_secours(conn)
    vus = types_vus_en_achat()

    codes = set(libelles) | set(familles) | set(vus)
    lignes = []
    for code in sorted(codes):
        lignes.append({
            "type_code": code,
            "libelle": libelles.get(code) or secours.get(code) or "",
            "famille": familles.get(code) or "",
            "receptions": vus.get(code, 0),
        })
    return {
        "familles": [{"cle": c, "label": l} for c, l in FAMILLES],
        "types": lignes,
        "non_classes": sum(1 for l in lignes if not l["famille"] and l["receptions"]),
    }


def enregistrer_famille(conn, type_code, famille, auteur=None):
    """Range un type dans une famille. `famille` vide retire le classement.

    Un type déclassé n'est pas une erreur : il redevient sans famille, donc
    visible comme tel sur l'écran des réceptions et remonté à l'arbitrage.
    """
    from datetime import datetime

    try:
        code = int(type_code)
    except (TypeError, ValueError):
        raise ValueError("Code de type invalide.")
    cle = (famille or "").strip()
    if cle and cle not in LIBELLE_FAMILLE:
        raise ValueError("Famille inconnue : %s" % cle)

    if not cle:
        conn.execute("DELETE FROM erp_type_famille WHERE type_code = ?", (code,))
        conn.commit()
        return {"type_code": code, "famille": ""}

    maintenant = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO erp_type_famille (type_code, famille, updated_at, updated_by_name) "
        "VALUES (?,?,?,?) "
        "ON CONFLICT(type_code) DO UPDATE SET "
        "  famille = excluded.famille, "
        "  updated_at = excluded.updated_at, "
        "  updated_by_name = excluded.updated_by_name",
        (code, cle, maintenant, auteur or ""),
    )
    conn.commit()
    return {"type_code": code, "famille": cle}
