"""Reception RVGI -> stock MyStock : lire, apparier, convertir.

Une ligne de reception de l'ERP doit devenir un mouvement de stock. Entre les
deux il y a trois traductions, et chacune s'est deja revelee piegeuse.

## L'article : un TRIPLET, pas un couple

`mat_mat` porte plusieurs lignes pour un meme `(code1, code2)`, une par type :
`1183/0001` est une glassine en type 2 et un velin en type 3. Le type de la
LIGNE D'ACHAT dit laquelle est la bonne. Tout ce module raisonne donc sur
`(code1, code2, type)`.

Les types au-dessus de 100 (802, 807, 817...) sont des variantes de fiche : ils
ne decrivent pas ce qu'on achete et n'entrent jamais dans la cle.

## La quantite : des METRES LINEAIRES, quoi que dise `cua`

Sur les bobines, `cdf_ligne.cua` vaut `10` ou `M²`, tous deux « metre carre »
dans `fic_ua`. C'est faux pour la quantite : `cua` decrit l'unite de PRIX.
Verifie en croisant `lif_ligne.qte` avec `stm_hist`, qui ecrit la meme valeur :
`552/0007` recoit 20 000 pour des bobines que `mat_mat.libt2` annonce a
« 10.000 ml », soit deux bobines ; `552/0005` recoit 64 009 pour des bobines de
« 16.000 ml », soit quatre. Diviser par la laize -- le reflexe naturel devant un
`cua` en metres carres -- donnerait un metrage faux d'un facteur deux.

## L'unite de gestion : celle du magasin, pas celle du fournisseur

MyStock tient les bobines en BOBINES, les adhesifs en KILOS, les cartons et les
mandrins en PALETTES. Le meme raisonnement que le destockage de fin de dossier
(`besoins_matieres._quantite_a_destocker`), en sens inverse. Une quantite qu'on
ne sait pas convertir n'est pas approximee : la ligne reste a integrer et dit ce
qui lui manque.

## Deux regimes d'entree

Personne ne scanne un carton : il entre directement. Une bobine, si -- et c'est
ce scan qui relie plus tard la bobine consommee en production a son certificat
FSC, par `stock_reception_items.code_barre`. Une bobine cree donc une reception
EN ATTENTE que le magasin valide au scan, et le stock ne bouge qu'a ce
moment-la. Arbitrage d'Eugene du 04/09/2026.
"""

import re
import unicodedata

# ── Ce que MyStock sait recevoir ────────────────────────────────────────────
#
# type RVGI -> (categorie MyStock, sous-section si elle discrimine, regime)
#
# Le regime « attente » est celui des bobines : elles passent par le scan du
# magasin. « direct » entre en stock des l'integration.
PERIMETRE = {
    3:  ("complexe", None,           "attente"),
    4:  ("glassine", None,           "attente"),
    5:  ("frontal",  "Velin",        "attente"),
    6:  ("frontal",  "Couché",       "attente"),
    7:  ("frontal",  "Thermiques",   "attente"),
    8:  ("frontal",  "Synthétique",  "attente"),
    9:  ("adhesif",  None,           "direct"),
    15: ("mandrin",  None,           "direct"),
    19: ("carton",   None,           "direct"),
    20: ("palette",  None,           "direct"),
}

# Unite de gestion du stock, par categorie. Doit rester aligne sur
# `stock._mp_unite_gestion` : deux reponses differentes pour la meme matiere
# rendraient le stock incomparable a lui-meme.
UNITE_GESTION = {
    "complexe": "bobine", "glassine": "bobine", "frontal": "bobine",
    "adhesif": "kg", "carton": "palette", "mandrin": "palette",
    "palette": "palette",
}


# ── Rapprochement par mots metier ───────────────────────────────────────────
#
# RVGI et MyStock parlent la meme langue -- « Couche Adhesif enlevable » d'un
# cote, « Couché adhésif enlevable » de l'autre -- mais pas toujours avec les
# memes mots : le fournisseur ecrit « vellum » ou « thermal », l'atelier ecrit
# « velin » et « thermique ». Une similarite de chaine brute se fait piéger par
# les accents et par les suffixes fournisseur (`H400`, `S692N-BG40WH`). On
# compare donc des ENSEMBLES de mots ramenes a une forme canonique.
SYNONYMES = {
    "vellum": "velin", "velins": "velin",
    "thermal": "thermique", "thermiques": "thermique", "therm": "thermique",
    "coated": "couche", "couches": "couche", "couché": "couche",
    "glassines": "glassine", "siliconne": "silicone", "siliconee": "silicone",
    "siliconnee": "silicone", "siliconees": "silicone", "siliconnees": "silicone",
    "silicone": "silicone", "silicones": "silicone", "release": "silicone",
    "adhesifs": "adhesif", "adh": "adhesif", "adhesive": "adhesif",
    "permanents": "permanent", "perm": "permanent",
    "removable": "enlevable", "enlevables": "enlevable",
    "freezer": "congelation", "congelation": "congelation",
    "tyre": "pneu", "tire": "pneu",
    "white": "blanc", "blanche": "blanc", "yellow": "jaune",
    "silver": "argente", "matt": "mat", "mate": "mat",
    "transparent": "transparent", "clear": "transparent",
    "acrylic": "acrylique", "hotmelt": "hotmelt",
    "core": "mandrin", "tube": "mandrin", "tubes": "mandrin",
    "roll": "bobine", "bobines": "bobine",
    "carton": "carton", "cartons": "carton", "boite": "boite",
    "pallet": "palette", "palettes": "palette",
}

# Mots qui ne discriminent rien : presents partout, ils gonflent le score sans
# rien dire. « adhesif » est dans quinze references sur dix-sept.
VIDES = frozenset({
    "de", "du", "des", "la", "le", "les", "et", "en", "pour", "par", "a", "au",
    "aux", "avec", "sur", "mm", "gsm", "g", "gr", "um", "micron", "microns",
    "ml", "m", "kg", "the", "of", "and", "for", "with", "bobine", "adhesif",
})

# Un grammage ou une epaisseur separe deux references que tout le reste
# rapproche : « PP blanc mat 120 » et « PP blanc mat 200 ». Il vaut donc autant
# qu'un mot, et son absence ne punit que lorsque les deux cotes chiffrent --
# voir `score`, ou cette dissymetrie est expliquee.
POIDS_NOMBRE = 1.0

# Les natures de support ne se confondent pas. Un PP n'est pas un PET, un PE
# n'est pas un couche -- et pourtant « PP blanc mat adhesif permanent » et
# « PET blanc adhesif permanent » partagent tout le reste. Sans cette regle, le
# rapprochement sortait le PET en tete avec 0,67 et l'aurait fait valider d'un
# clic. Quand les deux libelles declarent une nature et qu'elles ne se
# recoupent pas, le candidat est ecarte, pas seulement mal note.
NATURES = {
    "pp": "pp", "bopp": "pp", "opp": "pp",
    "pet": "pet",
    "pe": "pe", "pead": "pe", "pebd": "pe",
    "pvc": "pvc",
    "velin": "velin", "couche": "couche", "thermique": "thermique",
    "glassine": "glassine",
}


def _sans_accent(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()


def _decouper(texte):
    """Normalise un libelle avant tout decoupage.

    Deux details qui font echouer un rapprochement juste : les grammages colles
    a leur unite (« 60g », « 60gsm », « 95µ ») ne se ressemblent pas alors
    qu'ils disent le meme nombre, et les cotes ecrites « 385x385x208 » ne se
    separent pas toutes seules.
    """
    t = _sans_accent(texte).lower()
    t = re.sub(r"(\d)\s*[x×]\s*(\d)", r"\1 x \2", t)
    t = re.sub(r"(\d)\s*(?:gsm|g/m2|gm2|g|gr|um|u|mic|microns?|mm)\b", r"\1 ", t)
    return re.sub(r"[^a-z0-9]+", " ", t)


def mots(texte):
    """Les mots significatifs d'un libelle, ramenes a leur forme canonique."""
    out = set()
    for m in _decouper(texte).split():
        if m in VIDES or len(m) < 2 or m.isdigit():
            continue
        out.add(SYNONYMES.get(m, m))
    return out


def _nombres(texte):
    """Grammages, epaisseurs, cotes -- ce qui separe deux voisines."""
    return set(re.findall(r"\b\d{2,4}\b", _decouper(texte)))


def natures(texte):
    """Les natures de support declarees par un libelle."""
    return {NATURES[m] for m in mots(texte) if m in NATURES}


def score(texte_rvgi, texte_mysifa):
    """Proximite de deux libelles, entre 0 et 1.

    Rapportee aux mots de la reference MyStock, pas a l'union : le libelle RVGI
    porte des references fournisseur (`S692N-BG40WH`) qui n'ont pas d'equivalent
    et qui, dans une union, ecraseraient un rapprochement pourtant juste.

    Zero des que les deux libelles annoncent des natures de support qui ne se
    recoupent pas : ce n'est pas une nuance de score, c'est une autre matiere.
    """
    a, b = mots(texte_rvgi), mots(texte_mysifa)
    if not b:
        return 0.0
    na_sup, nb_sup = natures(texte_rvgi), natures(texte_mysifa)
    if na_sup and nb_sup and not (na_sup & nb_sup):
        return 0.0
    na, nb = _nombres(texte_rvgi), _nombres(texte_mysifa)
    # Les nombres de la reference MyStock ne comptent au denominateur QUE si le
    # libelle RVGI en porte lui-meme. Sans cette condition, `2030` -- une
    # reference d'adhesif qui EST un nombre -- serait puni face a « Adhesif
    # congelation », qui n'a aucune raison de le citer. Avec, une reference
    # pauvre comme « 62gsm Vellum » cesse de matcher n'importe quel velin a
    # 100 % : son grammage compte contre elle quand il ne se retrouve pas.
    denom = len(b) + (len(nb) if na else 0)
    communs = len(a & b) + POIDS_NOMBRE * len(na & nb)
    return communs / denom if denom else 0.0


def proposer(libelle_rvgi, matieres, limite=4):
    """Les meilleures matieres candidates, la plus proche en tete.

    `matieres` est deja restreint a la categorie du type RVGI : on ne propose
    jamais un carton pour une bobine. Rien n'est jamais enregistre ici --
    l'appariement se decide d'un clic, parce qu'un appariement faux ne se voit
    qu'a l'inventaire suivant.
    """
    notes = []
    for m in matieres:
        s = score(libelle_rvgi, "%s %s" % (m.get("reference") or "", m.get("designation") or ""))
        if s > 0:
            notes.append((s, m))
    notes.sort(key=lambda t: (-t[0], (t[1].get("reference") or "")))
    return [{"matiere_id": m["id"], "reference": m.get("reference"),
             "designation": m.get("designation"), "score": round(s, 3)}
            for s, m in notes[:limite]]


# ── Longueur de bobine annoncee par l'ERP ───────────────────────────────────

_RE_ML = re.compile(
    r"(?:bobine|roll|rouleau|r)\D{0,12}?(\d{1,3}(?:[ .]\d{3})+|\d{3,6})\s*(?:ml|m\b|meters?|metres?)",
    re.I)


def metrage_bobine_erp(libt2):
    """Metres par bobine, lus dans `mat_mat.libt2`.

    L'ERP l'ecrit en clair et de facon remarquablement reguliere : « Ø 76 mm,
    Bobine 16.000 ml, CSO », « Roll 18 000 ml », « Roll lenght 2.000 meters ».
    Sert de repli quand MyStock ne renseigne pas son propre metrage -- cinq
    references portent encore 0 -- et de controle quand les deux existent.
    """
    if not libt2:
        return None
    m = _RE_ML.search(str(libt2))
    if not m:
        return None
    try:
        v = float(m.group(1).replace(" ", "").replace(".", ""))
    except ValueError:
        return None
    return v if v > 0 else None


# ── Conversion vers l'unite de gestion ──────────────────────────────────────

def convertir(type_rvgi, qte_rvgi, matiere, libt2=None):
    """Traduit une quantite de reception dans l'unite du magasin.

    Renvoie { quantite, unite, detail, manque[] }. Une quantite non convertible
    rend `quantite = None` et dit pourquoi : on prefere une ligne qui reste a
    integrer a un stock faux que personne ne remet en cause.
    """
    cat = (matiere.get("categorie") or "").strip().lower()
    unite = UNITE_GESTION.get(cat, "palette")
    q = None
    try:
        q = float(qte_rvgi)
    except (TypeError, ValueError):
        q = None
    if q is None or q <= 0:
        return {"quantite": None, "unite": unite, "detail": None, "alerte": None,
                "manque": ["Quantité absente ou nulle sur la ligne de réception"]}

    if unite == "kg":
        # L'adhesif s'achete et se stocke au kilo : rien a traduire.
        return {"quantite": round(q, 4), "unite": "kg", "detail": None,
                "alerte": None, "manque": []}

    if unite == "bobine":
        # `qte` est en METRES LINEAIRES malgre un `cua` en metres carres.
        #
        # C'est le conditionnement de l'ARTICLE qui fait foi, pas la fiche
        # matiere : une meme reference MyStock est achetee chez plusieurs
        # fournisseurs, qui ne livrent pas la meme longueur de bobine.
        # `70g Eco Thermal` porte 12 000 m dans MyStock ; l'article `574/0001`
        # arrive en bobines de 8 150 m et l'article `1183/0004` en 12 000.
        # Verifie sur `stm_hist` le 04/09/2026 : sur 1183/0004, les receptions
        # de 143 900, 168 180, 120 300 et 72 180 m tombent exactement sur 12,
        # 14, 10 et 6 bobines de 12 000. Le metrage MyStock, lui, ne peut pas
        # etre juste pour les deux fournisseurs a la fois.
        ml_ms = _f(matiere.get("metres_lineaires_par_bobine"))
        ml_erp = metrage_bobine_erp(libt2)
        ml, origine = (ml_erp, "conditionnement ERP") if ml_erp else (ml_ms, "MyStock")
        if not ml:
            return {"quantite": None, "unite": "bobine", "detail": None, "alerte": None,
                    "manque": ["Mètres linéaires par bobine inconnus — "
                               "ni sur la matière MyStock, ni dans le libellé RVGI"]}

        # Les deux sources se contredisent : on retient l'ERP et on le dit.
        # Sur `552/0005`, MyStock annonce 18 100 m quand l'ERP ecrit « Bobine
        # 16.000 ml », et c'est l'ERP qui tombe juste -- 64 009 m font
        # exactement 4 bobines. Entrer 3,54 bobines la ou il y en a 4 ne se
        # rattrape qu'a l'inventaire. Le message n'est donc pas une hesitation,
        # c'est une invitation a corriger la fiche matiere.
        alerte = None
        if ml_ms and ml_erp and abs(ml_ms - ml_erp) / max(ml_ms, ml_erp) > 0.02:
            alerte = ("Conditionnement retenu : %s m/bobine (ERP). "
                      "La fiche MyStock dit %s m — %s bobines au lieu de %s."
                      % (_n(ml_erp), _n(ml_ms), round(q / ml_erp, 2), round(q / ml_ms, 2)))
        return {"quantite": round(q / ml, 4), "unite": "bobine",
                "detail": "%s m ÷ %s m/bobine (%s)" % (_n(q), _n(ml), origine),
                "alerte": alerte, "manque": []}

    if unite == "palette":
        if cat == "palette":
            # Une palette reste une palette : la quantite EST deja l'unite.
            return {"quantite": round(q, 4), "unite": "palette", "detail": None,
                    "alerte": None, "manque": []}
        upp = _f(matiere.get("unites_par_palette"))
        if not upp:
            return {"quantite": None, "unite": "palette", "detail": None, "alerte": None,
                    "manque": ["Unités par palette non renseignées sur la matière"]}
        return {"quantite": round(q / upp, 4), "unite": "palette",
                "detail": "%s ÷ %s par palette" % (_n(q), _n(upp)),
                "alerte": None, "manque": []}

    return {"quantite": round(q, 4), "unite": unite, "detail": None,
            "alerte": None, "manque": []}


def _f(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f else None


def _n(v):
    """Un nombre lisible : « 18 100 », pas « 18100 » ni « 18,100 »."""
    if v is None:
        return "?"
    f = float(v)
    if abs(f) >= 1000:
        return f"{f:,.0f}".replace(",", "\u202f")
    return "%g" % f


# ── Lecture : ce qu'il y a a integrer ───────────────────────────────────────

CLE_DEPUIS = "reception_rvgi_depuis"

# Les lignes de reception, jointes a leur ligne de commande (l'article n'est pas
# sur `lif_ligne`) et a la fiche matiere de l'ERP (le metrage de bobine). La
# jointure vers `mat_mat` porte le TYPE : sans lui elle ramene une fiche au
# hasard parmi celles qui partagent le couple.
_SQL_LIGNES = """
    SELECT l.id AS lif_id, l.numero, l.ligne, l.amjl, l.qte, l.ref AS ref_br,
           e.rs AS fournisseur, e.numfou,
           c.code1, c.code2, c.code3 AS laize_mm, c.type AS type_code,
           c.des1, c.cua,
           m.libc1 AS lib_erp, m.libt2 AS cond_erp
    FROM lif_ligne l
    JOIN cdf_ligne c
      ON c.numero = l.numero AND c.ligne = l.ligne AND c.corbeille = 0
    LEFT JOIN cdf_entete e
      ON e.numero = l.numero AND e.corbeille = 0
    LEFT JOIN mat_mat m
      ON m.code1 = c.code1 AND m.code2 = c.code2
     AND m.type = c.type - 2 AND m.corbeille = 0
    WHERE l.corbeille = 0
      AND c.type IN (%s)
      AND substr(l.amjl, 1, 10) >= ?
    ORDER BY l.amjl DESC, l.numero DESC, l.ligne
"""


def date_de_mise_en_service(conn):
    """Le jour a partir duquel les receptions entrent en stock, ou None.

    Vide par defaut, et c'est voulu : rien ne doit entrer avant que quelqu'un
    ait choisi le jour de bascule. Le stock actuel de MyStock est la reference.
    """
    try:
        r = conn.execute(
            "SELECT valeur FROM stock_config WHERE cle = ?", (CLE_DEPUIS,)
        ).fetchone()
    except Exception:
        return None
    v = (r["valeur"] if r else "") or ""
    return v.strip()[:10] or None


def _appariements(conn):
    return {
        (r["code1"], r["code2"], int(r["type_code"])): int(r["matiere_id"])
        for r in conn.execute(
            "SELECT code1, code2, type_code, matiere_id FROM erp_article_matiere"
        ).fetchall()
    }


def _matieres(conn):
    return [dict(r) for r in conn.execute(
        "SELECT id, categorie, sous_section, reference, designation,"
        "       metres_lineaires_par_bobine, unites_par_palette"
        " FROM matieres_premieres WHERE COALESCE(actif, 1) = 1"
    ).fetchall()]


def _deja_integrees(conn):
    return {int(r["lif_id"]) for r in conn.execute(
        "SELECT lif_id FROM erp_reception_integree").fetchall()}


def _candidates(matieres, type_code):
    """Les matieres qu'un type RVGI peut designer, et elles seules."""
    cat, sous, _ = PERIMETRE[type_code]
    return [m for m in matieres
            if (m.get("categorie") or "").strip().lower() == cat
            and (sous is None or (m.get("sous_section") or "").strip() == sous)]


def lignes_a_integrer(conn, conn_erp, limite=300):
    """Les receptions RVGI qui n'ont pas encore rejoint le stock.

    Chaque ligne dit tout ce qu'il faut pour decider : la matiere appariee s'il
    y en a une, les candidates proposees sinon, la quantite traduite dans
    l'unite du magasin, le regime d'entree et ce qui manque encore.

    Ne prend RIEN tant que la date de mise en service n'est pas posee.
    """
    depuis = date_de_mise_en_service(conn)
    if not depuis:
        return {"depuis": None, "lignes": [], "total": 0,
                "message": "Aucune date de mise en service : l'intégration est à l'arrêt."}

    types = ",".join(str(t) for t in sorted(PERIMETRE))
    brut = conn_erp.execute(_SQL_LIGNES % types, (depuis,)).fetchall()

    appar = _appariements(conn)
    matieres = _matieres(conn)
    par_id = {m["id"]: m for m in matieres}
    faites = _deja_integrees(conn)

    lignes = []
    for r in brut:
        if int(r["lif_id"]) in faites:
            continue
        type_code = int(r["type_code"])
        cle = (r["code1"], r["code2"], type_code)
        mid = appar.get(cle)
        matiere = par_id.get(mid) if mid else None
        libelle = ((r["lib_erp"] or r["des1"] or "") + " " + (r["cond_erp"] or "")).strip()

        conv = (convertir(type_code, r["qte"], matiere, r["cond_erp"])
                if matiere else
                {"quantite": None, "unite": None, "detail": None,
                 "alerte": None, "manque": []})
        manque = list(conv.get("manque") or [])
        if not matiere:
            manque.insert(0, "Article RVGI non apparié à une référence MySifa")

        lignes.append({
            "lif_id": int(r["lif_id"]),
            "numero": r["numero"], "ligne": r["ligne"],
            "amjl": (r["amjl"] or "")[:10],
            "ref_br": r["ref_br"], "fournisseur": r["fournisseur"],
            "article": "%s/%s" % (r["code1"], r["code2"]),
            "code1": r["code1"], "code2": r["code2"], "type_code": type_code,
            "libelle": libelle or None,
            "laize_mm": _f(r["laize_mm"]),
            "qte_rvgi": _f(r["qte"]),
            "matiere_id": mid,
            "matiere_ref": (matiere or {}).get("reference"),
            "matiere_designation": (matiere or {}).get("designation"),
            "propositions": ([] if matiere else
                             proposer(libelle, _candidates(matieres, type_code))),
            "quantite": conv.get("quantite"),
            "unite": conv.get("unite"),
            "detail": conv.get("detail"),
            "alerte": conv.get("alerte"),
            "regime": PERIMETRE[type_code][2],
            "manque": manque,
            "integrable": bool(matiere) and conv.get("quantite") is not None,
        })
        if len(lignes) >= limite:
            break

    return {"depuis": depuis, "lignes": lignes, "total": len(lignes), "message": None}


# ── Ecriture : apparier, puis integrer ──────────────────────────────────────

def apparier(conn, code1, code2, type_code, matiere_id, auteur=None, origine="manuel"):
    """Lie un article RVGI a une matiere MyStock. `matiere_id` vide delie.

    La cle est le triplet. Rien n'est verifie sur la categorie de la matiere :
    l'utilisateur voit deja des candidates restreintes a ce que le type peut
    designer, et lui interdire un choix hors liste l'empecherait de corriger un
    cas que le perimetre n'a pas prevu.
    """
    from datetime import datetime

    code1 = str(code1 or "").strip()
    code2 = str(code2 or "").strip()
    if not code1 or not code2:
        raise ValueError("Article RVGI incomplet.")
    try:
        type_code = int(type_code)
    except (TypeError, ValueError):
        raise ValueError("Type d'article invalide.")

    if matiere_id in (None, "", 0):
        conn.execute(
            "DELETE FROM erp_article_matiere WHERE code1=? AND code2=? AND type_code=?",
            (code1, code2, type_code))
        return {"code1": code1, "code2": code2, "type_code": type_code, "matiere_id": None}

    mid = int(matiere_id)
    if conn.execute("SELECT 1 FROM matieres_premieres WHERE id=?", (mid,)).fetchone() is None:
        raise ValueError("Matière MySifa inconnue.")
    conn.execute(
        "INSERT INTO erp_article_matiere "
        "(code1, code2, type_code, matiere_id, origine, created_at, created_by_name) "
        "VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(code1, code2, type_code) DO UPDATE SET "
        "  matiere_id = excluded.matiere_id, origine = excluded.origine, "
        "  created_at = excluded.created_at, created_by_name = excluded.created_by_name",
        (code1, code2, type_code, mid, origine,
         datetime.now().isoformat(timespec="seconds"), auteur or ""))
    return {"code1": code1, "code2": code2, "type_code": type_code, "matiere_id": mid}


def _laize_id(conn, valeur_mm):
    """L'identifiant de la laize, creee a la volee si l'ERP en annonce une neuve.

    Une laize inconnue n'est pas une anomalie : c'est une bobine que SIFA
    commande pour la premiere fois. Refuser l'entree pour cette raison bloquerait
    une reception parfaitement normale.
    """
    from datetime import datetime

    try:
        v = float(valeur_mm)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    r = conn.execute(
        "SELECT id FROM mp_laizes WHERE ABS(valeur_mm - ?) < 0.5 ORDER BY id LIMIT 1", (v,)
    ).fetchone()
    if r:
        return int(r["id"])
    cur = conn.execute(
        "INSERT INTO mp_laizes (valeur_mm, label, actif, created_at) VALUES (?,?,1,?)",
        (v, "%g mm" % v, datetime.now().isoformat(timespec="seconds")))
    return int(cur.lastrowid)


def integrer(conn, ligne, user, appliquer_mouvement):
    """Fait entrer une ligne de reception dans MyStock, une fois et une seule.

    `appliquer_mouvement` est `stock.appliquer_mouvement_mp`, passe en argument
    plutot qu'importe : ce module ne doit pas dependre du routeur, et surtout
    l'ecriture du stock reste le chemin CANONIQUE de MyStock. En ouvrir un
    sixieme ferait diverger la mise a jour de `mp_stock` le jour ou l'un des
    deux changerait.

    Deux regimes, decides par `PERIMETRE` :

    - **direct** -- cartons, palettes, mandrins, adhesifs. Personne ne les
      scanne : le mouvement d'entree part tout de suite.
    - **attente** -- les bobines. On cree une reception MyStock SANS bobine,
      portant la quantite attendue ; le stock ne bougera qu'au scan du magasin.
      C'est ce scan qui relie plus tard la bobine consommee en production a son
      certificat FSC, par `stock_reception_items.code_barre`. Entrer les bobines
      directement ferait un stock juste et une tracabilite muette.

    Ne committe pas : l'appelant maitrise sa transaction.
    """
    from datetime import datetime

    lif_id = int(ligne["lif_id"])
    if conn.execute("SELECT 1 FROM erp_reception_integree WHERE lif_id=?",
                    (lif_id,)).fetchone():
        raise ValueError("Cette réception a déjà été intégrée.")
    if not ligne.get("integrable"):
        raise ValueError("; ".join(ligne.get("manque") or ["Ligne non intégrable."]))

    matiere_id = int(ligne["matiere_id"])
    quantite = float(ligne["quantite"])
    regime = ligne.get("regime") or PERIMETRE[int(ligne["type_code"])][2]
    laize_id = _laize_id(conn, ligne.get("laize_mm")) if regime == "attente" else None
    maintenant = datetime.now().isoformat(timespec="seconds")
    auteur = (user or {}).get("nom") or (user or {}).get("email") or ""
    origine = "Réception RVGI %s/%s du %s" % (
        ligne.get("numero"), ligne.get("ligne"), ligne.get("amjl") or "?")

    mouvement_id = reception_id = None

    if regime == "direct":
        res = appliquer_mouvement(
            conn, user, matiere_id, "entree", quantite,
            laize_id=None, note=origine)
        mouvement_id = res.get("mouvement_id")
    else:
        if laize_id is None:
            raise ValueError("Laize absente de la ligne de réception — bobine non intégrable.")
        cur = conn.execute(
            "INSERT INTO stock_receptions "
            "(created_at, created_by, created_by_name, note, nb_bobines, fournisseur, "
            " fsc_type_claim, lot_numero, rvgi_cde, rvgi_bl, rvgi_qte_attendue, "
            " rvgi_lif_id, rvgi_matiere_id, rvgi_laize_id) "
            "VALUES (?,?,?,?,0,?,?,?,?,?,?,?,?,?)",
            (maintenant, (user or {}).get("email"), auteur, origine,
             ligne.get("fournisseur"), "non_fsc",
             "RVGI-%s-%s" % (ligne.get("numero"), ligne.get("ligne")),
             str(ligne.get("numero") or "")[:30], str(ligne.get("ref_br") or "")[:60],
             quantite, lif_id, matiere_id, laize_id))
        reception_id = int(cur.lastrowid)

    conn.execute(
        "INSERT INTO erp_reception_integree "
        "(lif_id, numero, ligne, amjl, qte_rvgi, matiere_id, laize_id, quantite, "
        " unite, regime, mouvement_id, reception_id, integre_at, integre_par) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (lif_id, ligne.get("numero"), ligne.get("ligne"), ligne.get("amjl"),
         ligne.get("qte_rvgi"), matiere_id, laize_id, quantite, ligne.get("unite"),
         regime, mouvement_id, reception_id, maintenant, auteur))

    return {"lif_id": lif_id, "regime": regime, "quantite": quantite,
            "unite": ligne.get("unite"), "mouvement_id": mouvement_id,
            "reception_id": reception_id,
            "message": ("Entrée en stock." if regime == "direct"
                        else "Réception créée — en attente du scan des bobines.")}
