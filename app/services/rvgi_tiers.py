"""Les clients et les fournisseurs de MySifa, alignés sur ceux de RVGI.

Ce que ce module fait, dans cet ordre
-------------------------------------
1. **Rapprocher** — poser le lien entre une fiche MySifa et une fiche RVGI.
   Sur SIRET identique d'abord (c'est un identifiant légal, il ne ment pas),
   puis sur code, puis sur nom normalisé. Tout le reste part en
   « à confirmer » : un lien faux ferait écraser une fiche par les données
   d'un autre tiers, ce qui est bien pire que de laisser une fiche non liée.

2. **Importer** — créer dans MySifa les fiches RVGI actives qui n'ont pas
   d'équivalent. « Actif » veut dire `bloq <> 2` (voir la migration : dans
   RVGI, `bloq = 1` est l'état vivant, `2` l'état bloqué).

3. **Appliquer** — réécrire, sur chaque fiche liée, les champs que RVGI
   connaît. C'est le « RVGI prime » : ces champs deviennent lecture seule
   dans MySifa, et la synchro suivante les remettra de toute façon.

Ce que ce module ne fait jamais
-------------------------------
Il ne touche pas `fournisseurs_fsc.nom`, ni `groupe`, ni `actif`. Le nom est
unique et joint en texte par une douzaine de modules ; le groupe pilote un
écran ; `actif` pilote la visibilité dans MyAO et Qualité. Les valeurs RVGI
correspondantes sont rangées dans `rvgi_rs`, `rvgi_groupe`, `rvgi_bloq`,
montrées à côté, et adoptées d'un clic si quelqu'un le décide.

Il ne supprime rien non plus. Une fiche qui disparaît de RVGI garde son lien
et son contenu : c'est à un humain de décider ce qu'on en fait.
"""

from __future__ import annotations

import difflib
import sqlite3
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services import erp_mirror as miroir

PERIMETRES = ("client", "fournisseur")

# Dans RVGI, `bloq = 2` est l'état bloqué. Mesuré : zéro commande en 2026 sur
# les 713 clients concernés, zéro commande d'achat depuis 2025 sur les 1 018
# fournisseurs. Les valeurs 1 et 3 restent vivantes.
BLOQ_INACTIF = 2

# RVGI code ses devises sur une lettre ou trois. MySifa parle ISO.
DEVISES = {"E": "EUR", "EUR": "EUR", "DOL": "USD", "USD": "USD",
           "L": "GBP", "GBP": "GBP", "CHF": "CHF"}


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normaliser(nom: Any) -> str:
    """« JAOUR S.A. » et « Jaour SA » doivent se retrouver.

    Même règle que l'import Excel des fournisseurs et que la migration de
    l'annuaire : accents retirés, ponctuation en espaces, formes juridiques
    et lettres isolées écartées. Deux normalisations différentes sur la même
    donnée produiraient deux rapprochements différents.
    """
    s = unicodedata.normalize("NFKD", str(nom or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = "".join(c if c.isalnum() else " " for c in s)
    stop = ("sa", "sas", "sarl", "sasu", "gmbh", "ltd", "bv", "nv", "spa",
            "srl", "inc", "eurl", "scop", "snc")
    mots = [m for m in s.split() if m not in stop and len(m) > 1]
    return " ".join(mots) or " ".join(s.split())


def _txt(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _siret(v: Any) -> Optional[str]:
    """RVGI écrit « 790 121 784 00082 », MySifa parfois sans espaces."""
    s = "".join(c for c in str(v or "") if c.isdigit())
    return s if len(s) >= 9 else None


# ── Ce que chaque périmètre lit et écrit ─────────────────────────────────────
#
# Une seule table de correspondance par référentiel, et tout le reste du module
# est commun. `champs` : colonne MySifa -> champ RVGI (ou fonction). Ce sont
# EXACTEMENT les champs que la synchro réécrit et que l'interface verrouille.

def _adresse_fou(r: Dict[str, Any]) -> Optional[str]:
    """Les fournisseurs MySifa n'ont qu'une ligne d'adresse, RVGI en a deux."""
    return " ".join(x for x in (_txt(r.get("adr1")), _txt(r.get("adr2"))) if x) or None


def _devise(r: Dict[str, Any]) -> Optional[str]:
    return DEVISES.get(str(r.get("dev") or "").strip().upper())


def _langue(r: Dict[str, Any]) -> Optional[str]:
    return {"F": "fr", "A": "en", "D": "de", "E": "es"}.get(
        str(r.get("lang") or "").strip().upper())


def _etat_client(r: Dict[str, Any]) -> str:
    return "Bloqué" if r.get("bloq") == BLOQ_INACTIF else "Normal"


PLAN = {
    "client": {
        "table": "clients",
        "rvgi": "fic_clt",
        "label": "Clients",
        "cle_nom": "raison_sociale",
        "cle_siret": "siret",
        "cle_code": "code",
        # `raison_sociale` n'est pas unique, et elle ne doit pas l'être : RVGI
        # porte plusieurs sites d'un même groupe sous la même raison sociale
        # (SONELOG LE PONTET, SONELOG…), et ce sont bien des clients distincts.
        "nom_unique": False,
        "champs": {
            "numero": "numero",
            "code": "code",
            "raison_sociale": "rs",
            "adresse1": "adr1",
            "adresse2": "adr2",
            "bp": "bp",
            "cp": "cp",
            "ville": "vil",
            "code_pays": "cpays",
            "pays": "pays",
            "siret": "siret",
            "tva": "ntva",
            "rcs": "rcs",
            "ean": "ean",
            "nif": "nif",
            "telephone": "tel",
            "telecopie": "fax",
            "email": "mail",
            "groupe": "_groupe",
            "representant": "_representant",
            "devise": _devise,
            "etat": _etat_client,
        },
        # Ce que la synchro ne touche pas : ce que RVGI ignore, ou ce dont
        # MySifa a fait autre chose.
        "reserve": ("contact_nom", "contact_fonction", "contact_email",
                    "contact_tel", "notes", "mode_livraison", "mode_reglement",
                    "encours_autorise", "code_comptable", "adv",
                    "categorie1", "categorie2", "categorie3"),
        "defauts": {"raison_sociale": "Sans nom", "etat": "Normal"},
    },
    "fournisseur": {
        "table": "fournisseurs_fsc",
        "rvgi": "fic_fou",
        "label": "Fournisseurs",
        "cle_nom": "nom",
        "cle_siret": "siret",
        "cle_code": None,          # pas de colonne code côté MySifa
        # `fournisseurs_fsc.nom` est UNIQUE — et joint en texte par une
        # douzaine de modules. Deux fiches RVGI de même nom normalisé ne
        # peuvent donc pas devenir deux fiches MySifa homonymes.
        "nom_unique": True,
        "champs": {
            "adresse": _adresse_fou,
            "code_postal": "cp",
            "ville": "vil",
            "pays": "cpays",
            "siret": "siret",
            "tva_intracom": "ntva",
            "rcs": "rcs",
            "telephone": "tel",
            "fax": "fax",
            "email": "mail",
            "delai_expedition_jours": "nbjliv",
            "price_currency": _devise,
            "langue_default": _langue,
            # Rangés à part, jamais imposés — voir l'en-tête du module.
            "rvgi_rs": "rs",
            "rvgi_groupe": "_groupe",
        },
        "reserve": ("nom", "groupe", "branche", "actif", "has_fsc", "licence",
                    "certificat", "fsc_date_expiration", "categories", "tags",
                    "notes", "sous_traitant", "pays_origine", "mode_reglement",
                    "mode_livraison", "regime_tva", "traca_photo_url",
                    "traca_explication", "traca_exemple_code"),
        "defauts": {"nom": None},   # calculé à l'import : c'est `rs`
    },
}

# Les champs verrouillés dans l'interface = ceux que la synchro réécrit, moins
# ceux qu'on range à part (préfixés `rvgi_`), qui ne sont pas des champs MySifa.
def champs_pilotes(perimetre: str) -> List[str]:
    p = PLAN[perimetre]
    return sorted(c for c in p["champs"] if not c.startswith("rvgi_"))


# ── Le côté RVGI ─────────────────────────────────────────────────────────────

def lire_rvgi(perimetre: str) -> Dict[int, Dict[str, Any]]:
    """{numero: fiche RVGI}, avec le groupe et le représentant résolus.

    `groupe` dans RVGI n'est pas un libellé mais le `numero` du tiers tête de
    groupe : on le remplace par sa raison sociale, sinon MySifa afficherait
    « Groupe : 1245 ».
    """
    p = PLAN[perimetre]
    with miroir.get_erp_db() as conn:
        if p["rvgi"] not in miroir.tables_presentes(conn):
            raise FileNotFoundError(
                "La table « %s » n'est pas dans le miroir : lancer la synchro RVGI."
                % p["rvgi"])
        lignes = [dict(r) for r in conn.execute(
            'SELECT * FROM "%s" WHERE corbeille = 0' % p["rvgi"])]
        reps = {}
        if perimetre == "client" and "fic_rep" in miroir.tables_presentes(conn):
            reps = {r["numero"]: _txt(r["nom"]) for r in
                    conn.execute("SELECT numero, nom FROM fic_rep WHERE corbeille = 0")}

    par_num = {}
    for r in lignes:
        num = r.get("numero")
        if num is None:
            continue
        par_num[int(num)] = r

    for r in par_num.values():
        tete = par_num.get(int(r.get("groupe") or 0))
        # Un tiers est son propre groupe dans RVGI : ça n'apprend rien.
        r["_groupe"] = (_txt(tete.get("rs")) if tete
                        and int(tete["numero"]) != int(r["numero"]) else None)
        r["_representant"] = reps.get(r.get("numrep"))
    return par_num


def _actif(r: Dict[str, Any]) -> bool:
    return r.get("bloq") != BLOQ_INACTIF


def valeur_rvgi(champ, r: Dict[str, Any]) -> Any:
    if callable(champ):
        return champ(r)
    v = r.get(champ)
    if isinstance(v, str):
        return _txt(v)
    return v


# ── Le côté MySifa ───────────────────────────────────────────────────────────

def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}


def lire_mysifa(conn: sqlite3.Connection, perimetre: str) -> List[Dict[str, Any]]:
    p = PLAN[perimetre]
    return [dict(r) for r in conn.execute('SELECT * FROM "%s"' % p["table"])]


# ── 1. Rapprocher ────────────────────────────────────────────────────────────

def rapprocher(conn: sqlite3.Connection, perimetre: str,
               rvgi: Dict[int, Dict[str, Any]]) -> Dict[str, int]:
    """Pose le lien là où il est certain, propose là où il est probable.

    Trois clés, par ordre de confiance décroissante :
      siret   identifiant légal — deux tiers qui le partagent sont le même
      code    le code ERP, quand MySifa le porte déjà (cas des clients)
      nom     nom normalisé identique, ET une seule fiche de chaque côté

    Une clé qui désigne plusieurs fiches d'un côté ou de l'autre ne lie rien :
    l'ambiguïté part en « à confirmer » plutôt que de tomber du bon côté une
    fois sur deux.
    """
    p = PLAN[perimetre]
    cols = _colonnes(conn, p["table"])
    if "rvgi_numero" not in cols:
        raise RuntimeError("Migration rvgi_tiers non appliquée sur %s." % p["table"])

    fiches = lire_mysifa(conn, perimetre)
    pris = {int(f["rvgi_numero"]) for f in fiches
            if f.get("rvgi_numero") and f.get("rvgi_etat") == "lie"}

    def index(source, cle):
        """clé -> numero unique, ou None si la clé est ambiguë."""
        out: Dict[str, Any] = {}
        for num, r in source.items():
            k = cle(r)
            if not k:
                continue
            out[k] = None if k in out else num
        return {k: v for k, v in out.items() if v is not None}

    par_siret = index(rvgi, lambda r: _siret(r.get("siret")))
    par_code = index(rvgi, lambda r: (_txt(r.get("code")) or "").upper() or None)
    par_nom = index(rvgi, lambda r: normaliser(r.get("rs")) or None)

    # L'ambiguïté se juge aussi côté MySifa : deux fiches MySifa au même nom
    # ne peuvent pas pointer la même fiche RVGI.
    def compte(cle):
        n: Dict[str, int] = {}
        for f in fiches:
            k = cle(f)
            if k:
                n[k] = n.get(k, 0) + 1
        return n

    n_siret = compte(lambda f: _siret(f.get(p["cle_siret"])))
    n_nom = compte(lambda f: normaliser(f.get(p["cle_nom"])) or None)

    res = {"lie": 0, "a_confirmer": 0, "deja": 0}
    for f in fiches:
        if f.get("rvgi_etat") == "lie" and f.get("rvgi_numero"):
            res["deja"] += 1
            continue

        candidat, motif, score = None, None, None

        s = _siret(f.get(p["cle_siret"]))
        if s and n_siret.get(s) == 1 and s in par_siret:
            candidat, motif, score = par_siret[s], "siret", 1.0

        if candidat is None and p["cle_code"]:
            c = (_txt(f.get(p["cle_code"])) or "").upper()
            if c and c in par_code:
                candidat, motif, score = par_code[c], "code", 0.95

        if candidat is None:
            nm = normaliser(f.get(p["cle_nom"]))
            if nm and n_nom.get(nm) == 1 and nm in par_nom:
                candidat, motif, score = par_nom[nm], "nom", 0.9

        # Le lien proposé par la migration à partir du numéro ERP déjà présent.
        if candidat is None and f.get("rvgi_numero") and int(f["rvgi_numero"]) in rvgi:
            candidat, motif, score = int(f["rvgi_numero"]), f.get("rvgi_motif") or "numero_erp", 0.9

        if candidat is None or candidat in pris:
            continue

        # Un lien posé sur le SIRET est sûr : on l'établit. Les autres sont
        # proposés — c'est un humain qui tranche, parce qu'un lien faux fait
        # écraser une fiche par les données d'un autre tiers.
        etat = "lie" if motif == "siret" else "a_confirmer"
        conn.execute(
            'UPDATE "%s" SET rvgi_numero=?, rvgi_code=?, rvgi_etat=?, rvgi_motif=?, '
            "rvgi_score=?, rvgi_lie_le=? WHERE id=?" % p["table"],
            (candidat, _txt(rvgi[candidat].get("code")), etat, motif, score,
             _maintenant(), f["id"]))
        pris.add(candidat)
        res[etat] += 1
    return res


def confirmer(conn: sqlite3.Connection, perimetre: str, fiche_id: int,
              rvgi_numero: Optional[int]) -> None:
    """Valider (ou poser à la main) le lien d'une fiche.

    `rvgi_numero = None` détache : la fiche redevient purement MySifa, ses
    champs se rouvrent à la saisie et la synchro ne la touchera plus.
    """
    p = PLAN[perimetre]
    if rvgi_numero is None:
        conn.execute(
            'UPDATE "%s" SET rvgi_numero=NULL, rvgi_code=NULL, rvgi_etat=\'manuel\', '
            "rvgi_motif=NULL, rvgi_score=NULL, rvgi_lie_le=NULL WHERE id=?" % p["table"],
            (fiche_id,))
        return
    autre = conn.execute(
        'SELECT id FROM "%s" WHERE rvgi_numero=? AND rvgi_etat=\'lie\' AND id<>?'
        % p["table"], (int(rvgi_numero), fiche_id)).fetchone()
    if autre is not None:
        raise ValueError(
            "La fiche RVGI n° %s est déjà rattachée à une autre fiche MySifa."
            % rvgi_numero)
    conn.execute(
        'UPDATE "%s" SET rvgi_numero=?, rvgi_etat=\'lie\', rvgi_motif=\'manuel\', '
        "rvgi_score=1.0, rvgi_lie_le=? WHERE id=?" % p["table"],
        (int(rvgi_numero), _maintenant(), fiche_id))


# ── 2. Importer ce que MySifa n'a pas ────────────────────────────────────────

def importer_manquants(conn: sqlite3.Connection, perimetre: str,
                       rvgi: Dict[int, Dict[str, Any]],
                       inclure_bloques: bool = False) -> int:
    """Crée les fiches RVGI actives absentes de MySifa.

    Le nom d'un fournisseur est unique dans MySifa, alors que RVGI porte des
    homonymes. Plutôt que d'écarter la fiche en silence — ce qui reviendrait à
    perdre un fournisseur réel — on la crée sous un nom désambiguïsé par son
    code ERP. Ce nom reste modifiable ; c'est un point de départ, pas un verdict.

    Les clients n'ont pas cette contrainte, et ne doivent pas l'avoir : RVGI
    porte plusieurs sites d'un même groupe sous la même raison sociale, et ce
    sont bien des clients distincts.
    """
    p = PLAN[perimetre]
    cols = _colonnes(conn, p["table"])
    connus = {int(r[0]) for r in conn.execute(
        'SELECT rvgi_numero FROM "%s" WHERE rvgi_numero IS NOT NULL' % p["table"])}
    unique = bool(p.get("nom_unique"))
    noms = ({normaliser(r[0]) for r in conn.execute(
        'SELECT "%s" FROM "%s"' % (p["cle_nom"], p["table"]))} if unique else set())

    n = 0
    maintenant = _maintenant()
    for num, r in sorted(rvgi.items()):
        if num in connus:
            continue
        if not inclure_bloques and not _actif(r):
            continue
        nom = _txt(r.get("rs")) or _txt(r.get("code")) or ("RVGI %d" % num)
        if unique and normaliser(nom) in noms:
            code = _txt(r.get("code"))
            nom = "%s (%s)" % (nom, code or ("RVGI %d" % num))
            if normaliser(nom) in noms:
                nom = "%s (RVGI %d)" % (_txt(r.get("rs")) or code or "Fournisseur", num)
            if normaliser(nom) in noms:
                continue        # trois collisions : on renonce plutôt qu'on invente

        valeurs = {p["cle_nom"]: nom}
        for col, champ in p["champs"].items():
            if col in cols and col != p["cle_nom"]:
                valeurs[col] = valeur_rvgi(champ, r)
        valeurs.update({
            "rvgi_numero": num,
            "rvgi_code": _txt(r.get("code")),
            "rvgi_etat": "lie",
            "rvgi_motif": "import",
            "rvgi_score": 1.0,
            "rvgi_bloq": r.get("bloq"),
            "rvgi_lie_le": maintenant,
            "rvgi_maj_le": maintenant,
        })
        for col, defaut in (("created_at", maintenant), ("updated_at", maintenant),
                            ("actif", 1), ("has_fsc", 0), ("etat", "Normal")):
            if col in cols and not valeurs.get(col):
                valeurs[col] = defaut
        valeurs = {k: v for k, v in valeurs.items() if k in cols}

        conn.execute(
            'INSERT INTO "%s" (%s) VALUES (%s)'
            % (p["table"], ",".join('"%s"' % k for k in valeurs),
               ",".join("?" * len(valeurs))),
            list(valeurs.values()))
        noms.add(normaliser(nom))
        n += 1
    return n


# ── 3. Appliquer : RVGI réécrit ce qu'il connaît ─────────────────────────────

def appliquer(conn: sqlite3.Connection, perimetre: str,
              rvgi: Dict[int, Dict[str, Any]]) -> Tuple[int, int]:
    """Réécrit les champs pilotés sur les fiches liées.

    Renvoie (fiches modifiées, champs écrits). On n'écrit que ce qui change :
    une synchro qui ne change rien ne doit pas toucher `updated_at`, sinon
    l'historique de modification perd tout son sens.
    """
    p = PLAN[perimetre]
    cols = _colonnes(conn, p["table"])
    plan = {c: ch for c, ch in p["champs"].items() if c in cols}

    fiches, champs = 0, 0
    maintenant = _maintenant()
    for f in conn.execute(
            'SELECT * FROM "%s" WHERE rvgi_etat=\'lie\' AND rvgi_numero IS NOT NULL'
            % p["table"]).fetchall():
        r = rvgi.get(int(f["rvgi_numero"]))
        if r is None:
            continue          # disparue de RVGI : on garde, on ne vide pas
        maj = {}
        for col, champ in plan.items():
            v = valeur_rvgi(champ, r)
            # Un champ que RVGI ne renseigne pas n'efface pas ce que MySifa
            # sait : l'ERP est prioritaire, pas amnésique.
            if v is None or v == "":
                continue
            if _identique(f[col] if col in f.keys() else None, v):
                continue
            maj[col] = v
        if r.get("bloq") != (f["rvgi_bloq"] if "rvgi_bloq" in f.keys() else None):
            maj["rvgi_bloq"] = r.get("bloq")
        if not maj:
            continue
        maj["rvgi_maj_le"] = maintenant
        if "updated_at" in cols:
            maj["updated_at"] = maintenant
        conn.execute(
            'UPDATE "%s" SET %s WHERE id=?'
            % (p["table"], ",".join('"%s"=?' % k for k in maj)),
            list(maj.values()) + [f["id"]])
        fiches += 1
        champs += len(maj) - 1
    return fiches, champs


def _identique(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    return str(a).strip() == str(b).strip()


# ── La synchro, et sa trace ──────────────────────────────────────────────────

def etat(conn: sqlite3.Connection, perimetre: str) -> Dict[str, Any]:
    """De quoi annoncer ce qu'une synchro ferait, avant de la lancer."""
    p = PLAN[perimetre]
    try:
        rvgi = lire_rvgi(perimetre)
    except FileNotFoundError as e:
        return {"perimetre": perimetre, "disponible": False, "raison": str(e)}
    cols = _colonnes(conn, p["table"])
    if "rvgi_numero" not in cols:
        return {"perimetre": perimetre, "disponible": False,
                "raison": "Migration rvgi_tiers non appliquée."}

    par_etat = {r[0] or "manuel": r[1] for r in conn.execute(
        'SELECT rvgi_etat, COUNT(*) FROM "%s" GROUP BY 1' % p["table"])}
    # « RVGI seul » = aucune fiche MySifa ne pointe dessus, confirmée ou non.
    # Une fiche en attente de confirmation n'est pas une fiche manquante.
    lies = {int(r[0]) for r in conn.execute(
        'SELECT rvgi_numero FROM "%s" WHERE rvgi_numero IS NOT NULL' % p["table"])}
    actifs = [n for n, r in rvgi.items() if _actif(r)]
    dernier = conn.execute(
        "SELECT * FROM rvgi_tiers_synchros WHERE perimetre=? ORDER BY lance_le DESC LIMIT 1",
        (perimetre,)).fetchone()
    return {
        "perimetre": perimetre,
        "label": p["label"],
        "disponible": True,
        "rvgi_total": len(rvgi),
        "rvgi_actifs": len(actifs),
        "mysifa_total": sum(par_etat.values()),
        "lies": par_etat.get("lie", 0),
        "a_confirmer": par_etat.get("a_confirmer", 0),
        "manuels": par_etat.get("manuel", 0),
        "rvgi_seuls": sum(1 for n in actifs if n not in lies),
        "champs_pilotes": champs_pilotes(perimetre),
        "miroir": miroir.meta().get("releve_le"),
        "derniere_synchro": dict(dernier) if dernier is not None else None,
    }


def synchroniser(conn: sqlite3.Connection, perimetre: str, utilisateur: str = "",
                 origine: str = "manuel", importer: bool = True,
                 inclure_bloques: bool = False) -> Dict[str, Any]:
    """Rapprocher, importer, appliquer — dans cet ordre, et une seule fois."""
    if perimetre not in PERIMETRES:
        raise ValueError("Périmètre inconnu : %r" % (perimetre,))
    rvgi = lire_rvgi(perimetre)

    rap = rapprocher(conn, perimetre, rvgi)
    nouveaux = importer_manquants(conn, perimetre, rvgi, inclure_bloques) if importer else 0
    fiches, champs = appliquer(conn, perimetre, rvgi)

    p = PLAN[perimetre]
    a_confirmer = conn.execute(
        'SELECT COUNT(*) FROM "%s" WHERE rvgi_etat=\'a_confirmer\'' % p["table"]
    ).fetchone()[0]
    lies = conn.execute(
        'SELECT COUNT(*) FROM "%s" WHERE rvgi_etat=\'lie\'' % p["table"]).fetchone()[0]

    res = {
        "perimetre": perimetre,
        "rvgi_total": len(rvgi),
        "rvgi_actifs": sum(1 for r in rvgi.values() if _actif(r)),
        "lies": lies,
        "nouveaux_liens": rap["lie"],
        "nouveaux": nouveaux,
        "mis_a_jour": fiches,
        "champs_ecrits": champs,
        "a_confirmer": a_confirmer,
    }
    conn.execute(
        """INSERT INTO rvgi_tiers_synchros
             (perimetre, lance_le, lance_par, origine, miroir_releve_le,
              rvgi_total, rvgi_actifs, lies, nouveaux, mis_a_jour, a_confirmer,
              champs_ecrits)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (perimetre, _maintenant(), utilisateur or None, origine,
         miroir.meta().get("releve_le"), res["rvgi_total"], res["rvgi_actifs"],
         lies, nouveaux, fiches, a_confirmer, champs))
    return res


# ── Ce que RVGI porte et que MySifa n'a pas encore repris ────────────────────

def fiche_rvgi(perimetre: str, numero: int) -> Optional[Dict[str, Any]]:
    """La fiche RVGI brute, pour l'afficher à côté de la fiche MySifa."""
    rvgi = lire_rvgi(perimetre)
    r = rvgi.get(int(numero))
    return dict(r) if r else None


def rvgi_seuls(conn: sqlite3.Connection, perimetre: str, q: str = "",
               limite: int = 200, inclure_bloques: bool = False) -> List[Dict[str, Any]]:
    """Les fiches RVGI qu'aucune fiche MySifa ne porte — l'onglet « à importer »."""
    p = PLAN[perimetre]
    rvgi = lire_rvgi(perimetre)
    lies = {int(r[0]) for r in conn.execute(
        'SELECT rvgi_numero FROM "%s" WHERE rvgi_numero IS NOT NULL' % p["table"])}
    motif = normaliser(q)
    out = []
    for num, r in sorted(rvgi.items(), key=lambda kv: str(kv[1].get("rs") or "")):
        if num in lies:
            continue
        if not inclure_bloques and not _actif(r):
            continue
        if motif and motif not in normaliser(r.get("rs")) and motif not in normaliser(r.get("code")):
            continue
        out.append({"numero": num, "code": _txt(r.get("code")), "rs": _txt(r.get("rs")),
                    "ville": _txt(r.get("vil")), "cp": _txt(r.get("cp")),
                    "pays": _txt(r.get("pays")), "siret": _txt(r.get("siret")),
                    "mail": _txt(r.get("mail")), "tel": _txt(r.get("tel")),
                    "actif": _actif(r), "bloq": r.get("bloq")})
        if len(out) >= limite:
            break
    return out


def candidats(perimetre: str, q: str, limite: int = 20) -> List[Dict[str, Any]]:
    """Le sélecteur « lier à une fiche RVGI »."""
    rvgi = lire_rvgi(perimetre)
    motif = normaliser(q)
    if not motif:
        return []
    out = []
    for num, r in rvgi.items():
        cible = normaliser(r.get("rs")) + " " + normaliser(r.get("code"))
        if motif not in cible:
            continue
        out.append({"numero": num, "code": _txt(r.get("code")), "rs": _txt(r.get("rs")),
                    "ville": _txt(r.get("vil")), "siret": _txt(r.get("siret")),
                    "actif": _actif(r)})
    out.sort(key=lambda x: (not x["actif"], str(x["rs"] or "")))
    return out[:limite]


# ── Le mapping : relier ce qui reste ─────────────────────────────────────────
#
# Le rapprochement automatique ne pose un lien que sur le SIRET, le code ou un
# nom normalisé identique. Ce qui reste — 24 fournisseurs propres à MySifa sur
# 224 au 26/08/2026 — sont soit des fiches qui n'existent pas dans l'ERP, soit
# des doublons écrits autrement. On ne peut pas les distinguer tout seul ; on
# peut en revanche proposer les meilleurs candidats et laisser trancher.
#
# Deux mesures, et elles ne servent pas à la même chose :
#
#   - le RECOUVREMENT DE MOTS voit « SA BRENNTAG » = « BRENNTAG SA », et
#     « ADLEY ADHESIVES » ⊂ « ADLEY ADHESIVES FRANCE ». Partager un mot entier
#     est un signal fort : on l'accepte dès la moitié des mots en commun.
#   - le RATIO DE SÉQUENCE rattrape les fautes de frappe et les abréviations,
#     mais il produit du bruit : « GENERIQUE » et « SERVITIQUE » sont à 63 %
#     l'un de l'autre et n'ont rien à voir. On ne l'accepte donc qu'au-delà
#     de 80 %, où il ne reste plus grand-chose de faux.
#
# Les deux seuils ont été calés sur les vraies données du miroir : à 62 %
# indifférencié, une suggestion sur deux était absurde et l'écran devenait
# une corvée qu'on abandonne.

SEUIL_MOTS = 0.50
SEUIL_SEQUENCE = 0.80


def _similarite(a: str, b: str):
    """Rend (score, mesure) — ou (0, None) si rien ne se ressemble assez."""
    if not a or not b:
        return 0.0, None
    ma, mb = set(a.split()), set(b.split())
    recouvrement = len(ma & mb) / len(ma | mb) if (ma | mb) else 0.0
    if recouvrement >= SEUIL_MOTS:
        return recouvrement, "mots"
    sequence = difflib.SequenceMatcher(None, a, b).ratio()
    if sequence >= SEUIL_SEQUENCE:
        return sequence, "orthographe"
    return 0.0, None


def doublons(conn: sqlite3.Connection, perimetre: str, limite: int = 80,
             par_fiche: int = 3) -> List[Dict[str, Any]]:
    """Les fiches restées propres à MySifa, et la fiche ERP qu'elles doublonnent.

    Le raisonnement compte, parce qu'il n'est pas celui qu'on croit. L'import
    crée une fiche MySifa pour CHAQUE fiche RVGI active. Une fiche MySifa
    ancienne, écrite autrement que dans l'ERP, ne se relie donc pas à une fiche
    RVGI libre : sa fiche RVGI a déjà son propre jumeau MySifa. Ce sont deux
    fiches MySifa qui font double emploi — « ADLEY ADHESIVES » et « ADLEY
    ADHESIVES (ADLEYADHESIVES FRANCE) ».

    On ne les relie donc pas : on les FUSIONNE. La fiche pilotée par l'ERP
    survit, l'ancienne y verse ses contacts, ses certificats FSC, ses tarifs
    et ses catégories — c'est ce que fait `/api/fournisseurs/{src}/merge/{tgt}`.
    """
    p = PLAN[perimetre]
    fiches = [dict(r) for r in conn.execute('SELECT * FROM "%s"' % p["table"])]
    pilotees = [(f, normaliser(f.get(p["cle_nom"])), _siret(f.get(p["cle_siret"])))
                for f in fiches if f.get("rvgi_etat") == "lie"]
    orphelines = [f for f in fiches
                  if f.get("rvgi_etat") != "lie" and not f.get("rvgi_numero")]

    out = []
    for f in orphelines:
        nom = normaliser(f.get(p["cle_nom"]))
        siret = _siret(f.get(p["cle_siret"]))
        if not nom:
            continue
        notes = []
        for g, nom_g, siret_g in pilotees:
            if g["id"] == f["id"]:
                continue
            if siret and siret_g and siret == siret_g:
                notes.append((1.0, "siret", g))
                continue
            score, mesure = _similarite(nom, nom_g)
            if mesure:
                notes.append((score, mesure, g))
        if not notes:
            continue
        notes.sort(key=lambda x: (-x[0], str(x[2].get(p["cle_nom"]) or "")))
        out.append({
            "id": f["id"],
            "origine": "doublon",
            "mysifa": {"nom": f.get(p["cle_nom"]), "siret": siret,
                       "ville": f.get("ville"), "email": f.get("email")},
            "candidats": [{
                "id": g["id"], "numero": g.get("rvgi_numero"),
                "code": g.get("rvgi_code"), "rs": g.get(p["cle_nom"]),
                "siret": g.get(p["cle_siret"]), "ville": g.get("ville"),
                "actif": g.get("rvgi_bloq") != BLOQ_INACTIF,
                "score": round(score, 2), "motif": mesure,
            } for score, mesure, g in notes[:par_fiche]],
        })
    out.sort(key=lambda x: -x["candidats"][0]["score"])
    return out[:limite]


def a_mapper(conn: sqlite3.Connection, perimetre: str,
             limite: int = 120) -> Dict[str, Any]:
    """Tout ce qui attend une décision humaine, dans un seul écran.

    Deux origines, deux gestes différents — et il ne faut pas les confondre :

      `propose`  un rapprochement automatique a trouvé un candidat presque sûr
                 et attend un accord. Le geste est de RELIER : la fiche devient
                 pilotée par l'ERP, rien n'est supprimé.

      `doublon`  une fiche ancienne de MySifa fait double emploi avec une fiche
                 que l'ERP pilote déjà. Le geste est de FUSIONNER : l'ancienne
                 verse son contenu dans l'autre puis disparaît. Irréversible,
                 donc jamais automatique.
    """
    p = PLAN[perimetre]
    rvgi = lire_rvgi(perimetre)
    lignes = []

    for f in conn.execute(
            'SELECT * FROM "%s" WHERE rvgi_etat = \'a_confirmer\' '
            "ORDER BY rvgi_score DESC, id LIMIT ?" % p["table"], (int(limite),)):
        f = dict(f)
        r = rvgi.get(int(f.get("rvgi_numero") or 0)) or {}
        if not r:
            continue
        lignes.append({
            "id": f["id"], "origine": "propose", "motif": f.get("rvgi_motif"),
            "mysifa": {"nom": f.get(p["cle_nom"]), "siret": f.get(p["cle_siret"]),
                       "ville": f.get("ville"), "email": f.get("email")},
            "candidats": [{
                "numero": f.get("rvgi_numero"), "code": _txt(r.get("code")),
                "rs": _txt(r.get("rs")), "siret": _txt(r.get("siret")),
                "ville": _txt(r.get("vil")), "actif": _actif(r),
                "score": f.get("rvgi_score"), "motif": f.get("rvgi_motif"),
            }],
        })

    vus = {l["id"] for l in lignes}
    for d in doublons(conn, perimetre, limite=limite):
        if d["id"] not in vus:
            lignes.append(d)

    return {
        "perimetre": perimetre,
        "total": len(lignes),
        # La fusion n'existe que pour les fournisseurs : c'est la seule table
        # dont toutes les dépendances sont connues et réassignables.
        "fusion_possible": perimetre == "fournisseur",
        "lignes": lignes,
    }


# ── Les contacts RVGI d'un fournisseur ───────────────────────────────────────
#
# `fic_foui` porte 265 interlocuteurs. MySifa a sa propre table de contacts,
# tenue à la main : on ne fusionne pas les deux — on montre ceux de RVGI, et
# on les reprend d'un clic quand quelqu'un le décide.

def contacts_rvgi(numero: int) -> List[Dict[str, Any]]:
    with miroir.get_erp_db() as conn:
        if "fic_foui" not in miroir.tables_presentes(conn):
            return []
        return [{"numint": r["numint"], "nom": _txt(r["nom"]), "prenom": _txt(r["pre"]),
                 "service": _txt(r["service"]), "tel": _txt(r["tel"]),
                 "gsm": _txt(r["gsm"]), "fax": _txt(r["fax"]), "mail": _txt(r["mail"]),
                 "principal": bool(r["def"])}
                for r in conn.execute(
                    "SELECT * FROM fic_foui WHERE corbeille = 0 AND numfou = ? "
                    "ORDER BY def DESC, nom", (int(numero),))]


def adresses_rvgi(numero: int) -> List[Dict[str, Any]]:
    """`fic_clta` : les adresses de livraison d'un client — 6 186 dans le miroir."""
    with miroir.get_erp_db() as conn:
        if "fic_clta" not in miroir.tables_presentes(conn):
            return []
        return [{"numadr": r["numadr"], "rs": _txt(r["rs"]), "adr1": _txt(r["adr1"]),
                 "adr2": _txt(r["adr2"]), "cp": _txt(r["cp"]), "ville": _txt(r["vil"]),
                 "pays": _txt(r["pays"]), "tel": _txt(r["tel"]), "mail": _txt(r["mail"]),
                 "contact": " ".join(x for x in (_txt(r["i_pre"]), _txt(r["i_nom"])) if x) or None,
                 "contact_mail": _txt(r["i_mail"]), "contact_tel": _txt(r["i_tel"])}
                for r in conn.execute(
                    "SELECT * FROM fic_clta WHERE corbeille = 0 AND numclt = ? "
                    "ORDER BY numadr", (int(numero),))]
