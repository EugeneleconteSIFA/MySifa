"""
Import unique Access -> MySifa : fiches techniques + OF depuis une date
=======================================================================

Reprise ponctuelle de l'historique. A lancer UNE fois par instance visee.
Les syncs recurrents restent access_sync_fiches.py et access_sync_of.py :
ce script ne remplace ni l'un ni l'autre et ne touche pas a leur fichier
last_sync.

Ce qu'il fait, dans cet ordre
-----------------------------
1. Fiches techniques. Deux ensembles reunis :
     - les fiches referencees par les OF crees depuis la date, QUELLE QUE
       SOIT leur date de modification. C'est le point important : un OF de
       2026 pointe tres souvent vers une fiche creee en 2019 et jamais
       retouchee. Un filtre sur `modif` seul la laisserait de cote et l'OF
       arriverait dans MySifa sans sa fiche.
     - les fiches dont `modif` est posterieure a la date.
2. OF. t_of.date_creation posterieure a la date, fiche technique et
   grammage adhesif joints (meme requete que access_sync_of.py).

Les fiches passent avant les OF pour qu'un OF trouve toujours sa reference.

Ce qu'il ne fait jamais
-----------------------
Ecraser une valeur deja renseignee dans MySifa. Les deux endpoints sont
appeles avec enrich_if_exists=True et refresh_access_fields=False : une
fiche corrigee a la main, un OF portant un vrai PDF ou une saisie atelier
gardent leurs valeurs. Seules les colonnes restees vides sont completees.

Prerequis
---------
    pip install pyodbc requests

    Python 64 bits ET pilote « Microsoft Access Driver (*.mdb, *.accdb) »
    64 bits (Access Database Engine). Un Python 32 bits ne verra pas un
    pilote 64 bits, et inversement — c'est la cause n°1 d'echec ici.

    setx MYSIFA_API_KEY "msk_..."   puis rouvrir le terminal.
    La cle doit porter le scope of:write.

    Acces au partage \\\\IDEFIX\\sifa_pub — donc depuis un poste du reseau
    SIFA, pas depuis le VPS.

Utilisation
-----------
    # 1. repetition a blanc, rien n'est ecrit
    python scripts/import_access_2026.py --dry-run

    # 2. pour de vrai sur le staging (DB isolee)
    python scripts/import_access_2026.py

    # 3. une fois les volumes verifies sur v1, la prod
    python scripts/import_access_2026.py --base-url https://mysifa.com

Options : --depuis AAAA-MM-JJ (defaut 2026-01-01), --fiches-seules,
--of-seuls, --limite N (essai sur les N premieres lignes).
"""

import argparse
import os
import re
import sys
from datetime import datetime

try:
    import pyodbc
except ImportError:
    sys.exit("pyodbc manquant. Installer avec : pip install pyodbc requests")

try:
    import requests
except ImportError:
    sys.exit("requests manquant. Installer avec : pip install pyodbc requests")


# ── Configuration ────────────────────────────────────────────────────
BASE_DIR   = r"\\IDEFIX\sifa_pub\Fiches techniques Access"
DB_FICHES  = BASE_DIR + r"\sifa_fiches_techniques.mdb"
DB_OF      = BASE_DIR + r"\of.mdb"
TABLE_FICHES = "fiches_techniques"

URL_STAGING = "https://v1.mysifa.com"
URL_PROD    = "https://mysifa.com"

API_KEY = os.environ.get("MYSIFA_API_KEY", "")

# Taille des paquets de references passees en IN (...) a Jet. Au-dela d'a peu
# pres 500 termes le moteur refuse la requete ; 150 laisse de la marge.
LOT_REFERENCES = 150


def conn_str(chemin: str) -> str:
    return (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={chemin};"
    )


# ── Conversions ──────────────────────────────────────────────────────

def to_float(val):
    """Tolere « 470mm », « 10,794 », « 1 234 »."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    txt = re.sub(r"[^0-9,.\-]", "", str(val)).replace(",", ".")
    if txt in ("", "-", "."):
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def to_int(val):
    v = to_float(val)
    return int(round(v)) if v is not None else None


def to_str(val):
    if val is None:
        return None
    return str(val).strip() or None


def format_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    brut = str(val).strip()[:10]
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(brut, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return brut


def litteral_date(iso: str) -> str:
    """« 2026-01-01 » -> « #01/01/2026# ».

    Un litteral date Jet s'ecrit en MM/JJ/AAAA entre dieses, quelle que soit
    la locale du poste. On evite ainsi le typage des parametres par le pilote
    ODBC, qui compare parfois une Date a une chaine et ne ramene rien sans
    lever la moindre erreur.
    """
    d = datetime.strptime(iso, "%Y-%m-%d")
    return d.strftime("#%m/%d/%Y#")


def cle(ref) -> str:
    """Cle de comparaison d'une reference : casse et espaces neutralises."""
    return re.sub(r"\s+", " ", str(ref or "").strip()).lower()


def echappe(val: str) -> str:
    """Echappe une valeur texte pour un litteral SQL Jet."""
    return str(val).replace("'", "''")


# ── Colonnes fiches techniques ───────────────────────────────────────
# Liste reprise telle quelle de access_sync_fiches.py — deja eprouvee.
COLONNES_FICHES = """
    [reference], [date_creation], [modif],
    [format],
    [etilaize], [etilong], [etirayon], [etiperfo],
    [modlaize], [modlong], [nbfront],
    [lateral_ext], [horizontal], [lateral_int],
    [outil], [outilnumerosifa], [laizecoupant], [machine],
    [outil_epaisseur], [nbdents], [outilnbfront], [outilnbavance],
    [outil2], [outilnumerosifa2], [outil_epaisseur2],
    [nbdents2], [outilnbfront2], [outilnbavance2],
    [outil3], [outilnumerosifa3], [outil_epaisseur3],
    [nbdents3], [outilnbfront3], [outilnbavance3],
    [matsupport], [matglassine], [matlaizestandard], [matlaize],
    [protect_epaisseur], [matadhesif], [matquantite],
    [nbcouleurs], [recto], [verso],
    [pant1], [anilox1], [composition1],
    [pant2], [anilox2], [composition2],
    [pant3], [anilox3], [composition3],
    [remarques],
    [mandrin_diametre], [mandrin_longueur], [enroulement],
    [nbetiquette], [diametreext], [poids],
    [miseboite], [cales_sachets], [dimensions_carton],
    [nb_au_sol], [nb_etag], [bob_carton],
    [palettisation_type], [palettisation_nb_sol],
    [palettisation_nb_hauteur], [palettisation_hauteur_max],
    [particularites]
"""


def payload_fiche(row) -> dict:
    f, i, s = to_float, to_int, to_str
    return {
        "reference":              s(row.reference),
        "date_modif":             format_date(row.modif),
        "format":                 s(row.format),
        # Etiquette
        "eti_laize":              f(row.etilaize),
        "eti_longueur":           f(row.etilong),
        "eti_rayons":             f(row.etirayon),
        "eti_perforations":       s(row.etiperfo),
        # Module
        "mod_laize":              f(row.modlaize),
        "mod_longueur":           f(row.modlong),
        "mod_nb_front":           i(row.nbfront),
        # Echenillage
        "lateral_ext":            f(row.lateral_ext),
        "horizontal":             f(row.horizontal),
        "lateral_int":            f(row.lateral_int),
        # Outil 1
        "outil1_forme":           s(row.outil),
        "outil1_numero_sifa":     s(row.outilnumerosifa),
        "outil1_laize":           f(row.laizecoupant),
        "machine":                s(row.machine),
        "outil1_epaisseur":       f(row.outil_epaisseur),
        "outil1_nb_dents":        i(row.nbdents),
        "outil1_nb_front":        i(row.outilnbfront),
        "outil1_nb_avance":       i(row.outilnbavance),
        # Outil 2
        "outil2_forme":           s(row.outil2),
        "outil2_numero_sifa":     s(row.outilnumerosifa2),
        "outil2_epaisseur":       f(row.outil_epaisseur2),
        "outil2_nb_dents":        i(row.nbdents2),
        "outil2_nb_front":        i(row.outilnbfront2),
        "outil2_nb_avance":       i(row.outilnbavance2),
        # Outil 3
        "outil3_forme":           s(row.outil3),
        "outil3_numero_sifa":     s(row.outilnumerosifa3),
        "outil3_epaisseur":       f(row.outil_epaisseur3),
        "outil3_nb_dents":        i(row.nbdents3),
        "outil3_nb_front":        i(row.outilnbfront3),
        "outil3_nb_avance":       i(row.outilnbavance3),
        # Matiere
        "support":                s(row.matsupport),
        "glassine":               s(row.matglassine),
        "laize_optimale":         f(row.matlaizestandard),
        "laize_optionnelle":      f(row.matlaize),
        "epaisseur":              f(row.protect_epaisseur),
        "adhesif":                s(row.matadhesif),
        "qte_au_mille":           f(row.matquantite),
        # Impression
        "nb_couleurs":            i(row.nbcouleurs),
        "recto":                  i(row.recto),
        "verso":                  i(row.verso),
        "tete1_pantone":          s(row.pant1),
        "tete1_anilox":           s(row.anilox1),
        "tete1_composition":      s(row.composition1),
        "tete2_pantone":          s(row.pant2),
        "tete2_anilox":           s(row.anilox2),
        "tete2_composition":      s(row.composition2),
        "tete3_pantone":          s(row.pant3),
        "tete3_anilox":           s(row.anilox3),
        "tete3_composition":      s(row.composition3),
        "remarque":               s(row.remarques),
        # Conditionnement
        "mandrin_dia":            s(row.mandrin_diametre),
        "mandrin_longueur":       f(row.mandrin_longueur),
        "enroulement":            s(row.enroulement),
        "nb_etiq_bobin":          i(row.nbetiquette),
        "dia_ext":                f(row.diametreext),
        "poids":                  f(row.poids),
        "conditionnement":        s(row.miseboite),
        "cales_sachets":          s(row.cales_sachets),
        "cartons":                s(row.dimensions_carton),
        "nb_au_sol":              i(row.nb_au_sol),
        "nb_etage":               i(row.nb_etag),
        "nb_bobines_carton":      i(row.bob_carton),
        # Palettisation
        "palette_type":               s(row.palettisation_type),
        "palette_nb_cartons_sol":     i(row.palettisation_nb_sol),
        "palette_nb_cartons_hauteur": i(row.palettisation_nb_hauteur),
        "palette_hauteur_max":        f(row.palettisation_hauteur_max),
        "particularite":              s(row.particularites),
        # Ne completer que les colonnes vides d'une fiche deja presente.
        "enrich_if_exists":           True,
    }


# ── Requete OF ───────────────────────────────────────────────────────
# t_fiches_techniques est une table liee vers sifa_fiches_techniques.mdb,
# Adhesif est locale a of.mdb : une seule connexion suffit.
SQL_OF = """
    SELECT t_of.numero_of                     AS numero_of,
           t_of.date_creation                 AS date_creation,
           t_of.date_delai                    AS date_delai,
           t_of.format                        AS format,
           t_of.theorique_quantite            AS qte,
           t_of.theorique_quantite_bobines    AS bobines,
           t_of.theorique_metrage_necessaire  AS metrage,
           t_of.theorique_mandrins            AS mandrins,
           t_of.theorique_cartons             AS cartons,
           t_of.theorique_tubes               AS tubes,
           f.matsupport                       AS matiere,
           f.matglassine                      AS glassine,
           f.matlaizestandard                 AS laize,
           f.matquantite                      AS qte_mille,
           f.matquantite_type                 AS qte_mille_type,
           f.matadhesif                       AS adhesif_label,
           f.machine                          AS machine,
           a.reference                        AS adhesif_ref,
           a.grammage                         AS adhesif_grammage
    FROM   (t_of LEFT JOIN t_fiches_techniques AS f
                 ON t_of.format = f.reference)
           LEFT JOIN Adhesif AS a
                 ON f.matadhesif = a.type
    WHERE  t_of.date_creation >= {DATE}
    ORDER  BY t_of.date_creation ASC
"""


def qte_adhesif_kg(grammage, metrage, laize_mm):
    """Formule de la vue Access [adhesif_necessaire_sans_date_prev].

    grammage g/m² x metrage m x laize mm / 1e6 -> kg. La laize est
    matlaizestandard, PAS matlaize (cf. en-tete de access_sync_of.py).
    None des qu'un ingredient manque : mieux vaut une case vide qu'un
    tonnage faux dans les besoins matieres.
    """
    if grammage is None or metrage is None or laize_mm is None:
        return None
    return round(grammage * metrage * laize_mm / 1_000_000, 3)


def payload_of(row) -> dict:
    metrage  = to_float(row.metrage)
    laize    = to_float(row.laize)
    grammage = to_float(row.adhesif_grammage)

    # matquantite ne vaut « quantite au mille » que si matquantite_type le dit.
    qte_mille = None
    if (row.qte_mille_type or "").strip().lower().startswith("au mille"):
        qte_mille = to_float(row.qte_mille)

    return {
        "numero_of":        str(row.numero_of).strip(),
        "date_creation":    format_date(row.date_creation),
        "delai_client":     format_date(row.date_delai),
        "format":           to_str(row.format),
        "reference":        to_str(row.format),   # t_of.format = fiches.reference
        "machine":          to_str(row.machine),
        "matiere":          to_str(row.matiere),
        "glassine":         to_str(row.glassine),
        "laize":            laize,
        "qte_etiquettes":   to_float(row.qte),
        "qte_bobines":      to_float(row.bobines),
        "metrage":          metrage,
        "qte_au_mille":     qte_mille,
        "adhesif_label":    to_str(row.adhesif_label),
        "ref_adhesif":      to_str(row.adhesif_ref),
        "qte_adhesif_g":    grammage,
        "qte_adhesif_kg":   qte_adhesif_kg(grammage, metrage, laize),
        "nb_mandrins":      to_int(row.mandrins),
        "nb_cartons":       to_int(row.cartons),
        "nb_tubes":         to_int(row.tubes),
        "enrich_if_exists":      True,
        "refresh_access_fields": False,
    }


# ── Lecture Access ───────────────────────────────────────────────────

def references_des_of(date_iso: str) -> list:
    """Formats distincts portes par les OF crees depuis la date."""
    with pyodbc.connect(conn_str(DB_OF)) as conn:
        rows = conn.cursor().execute(
            "SELECT DISTINCT [format] FROM t_of "
            f"WHERE date_creation >= {litteral_date(date_iso)} "
            "AND [format] IS NOT NULL"
        ).fetchall()
    vues, refs = set(), []
    for r in rows:
        ref = to_str(r[0])
        if ref and cle(ref) not in vues:
            vues.add(cle(ref))
            refs.append(ref)
    return refs


def fiches_a_importer(date_iso: str, refs_of: list) -> list:
    """Fiches modifiees depuis la date + fiches referencees par les OF."""
    conn = pyodbc.connect(conn_str(DB_FICHES))
    cur  = conn.cursor()

    lignes, vues = [], set()

    def ajoute(rows):
        for row in rows:
            k = cle(row.reference)
            if k and k not in vues:
                vues.add(k)
                lignes.append(row)

    # 1. modifiees depuis la date
    ajoute(cur.execute(
        f"SELECT {COLONNES_FICHES} FROM [{TABLE_FICHES}] "
        f"WHERE [modif] >= {litteral_date(date_iso)} ORDER BY [modif] ASC"
    ).fetchall())
    deja_modif = len(lignes)

    # 2. referencees par les OF, quelle que soit leur date de modification.
    #    Par paquets : Jet plafonne le nombre de termes d'un IN (...).
    manquantes = [r for r in refs_of if cle(r) not in vues]
    for i in range(0, len(manquantes), LOT_REFERENCES):
        lot = manquantes[i:i + LOT_REFERENCES]
        liste = ", ".join("'" + echappe(r) + "'" for r in lot)
        ajoute(cur.execute(
            f"SELECT {COLONNES_FICHES} FROM [{TABLE_FICHES}] "
            f"WHERE [reference] IN ({liste})"
        ).fetchall())

    conn.close()
    print(f"    {deja_modif} fiche(s) modifiee(s) depuis la date, "
          f"+ {len(lignes) - deja_modif} rattrapee(s) via les OF")

    orphelines = [r for r in manquantes if cle(r) not in vues]
    if orphelines:
        apercu = ", ".join(orphelines[:10])
        suite  = " ..." if len(orphelines) > 10 else ""
        print(f"    ATTENTION — {len(orphelines)} format(s) d'OF sans fiche "
              f"dans Access : {apercu}{suite}")
    return lignes


def lit_of(date_iso: str) -> list:
    with pyodbc.connect(conn_str(DB_OF)) as conn:
        return conn.cursor().execute(
            SQL_OF.replace("{DATE}", litteral_date(date_iso))
        ).fetchall()


# ── Envoi ────────────────────────────────────────────────────────────

class Pont:
    def __init__(self, base_url: str, dry_run: bool):
        self.base_url = base_url.rstrip("/")
        self.dry_run  = dry_run
        self.session  = requests.Session()
        self.session.headers.update({
            "X-Api-Key":    API_KEY,
            "Content-Type": "application/json",
        })

    def verifie(self):
        """Refuse de partir si l'instance ne connait pas enrich_if_exists.

        Pydantic ignore silencieusement un champ inconnu : sans ce controle,
        le script croirait completer des colonnes vides alors que le serveur
        ecraserait tout le contenu de la fiche.
        """
        r = self.session.get(f"{self.base_url}/api/bridge/health", timeout=15)
        r.raise_for_status()
        features = r.json().get("features") or []
        if "fiche.enrich_if_exists" not in features:
            sys.exit(
                f"\n{self.base_url} ne connait pas encore l'option "
                "fiche.enrich_if_exists.\n"
                "Le patch de app/routers/api_bridge.py doit etre deploye sur "
                "cette instance avant l'import,\n"
                "sinon les fiches deja presentes seraient ecrasees par Access.\n"
            )

    def post(self, chemin: str, payload: dict) -> dict:
        if self.dry_run:
            return {"dry_run": True}
        r = self.session.post(f"{self.base_url}{chemin}", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()


def journal(fichier, texte, ecran=True):
    """Ecrit dans le journal, et a l'ecran sauf pour le detail ligne a ligne."""
    if ecran:
        print(texte)
    fichier.write(texte + "\n")
    fichier.flush()


# ── Passes ───────────────────────────────────────────────────────────

def passe_fiches(pont, log, date_iso, limite):
    journal(log, "\n=== Passe 1 — Fiches techniques ===")
    refs = references_des_of(date_iso)
    journal(log, f"    {len(refs)} format(s) distinct(s) sur les OF depuis {date_iso}")
    lignes = fiches_a_importer(date_iso, refs)
    if limite:
        lignes = lignes[:limite]
    journal(log, f"    {len(lignes)} fiche(s) a traiter\n")

    creees = enrichies = inchangees = erreurs = 0
    for row in lignes:
        ref = to_str(row.reference) or "???"
        try:
            payload = payload_fiche(row)
            if not payload.get("reference"):
                journal(log, "  [IGNORE]    fiche sans reference")
                continue
            res = pont.post("/api/bridge/fiche-technique", payload)
            action = res.get("action", "dry_run")
            if action == "created":
                journal(log, f"  [CREEE]     {ref}", ecran=False)
                creees += 1
            elif action == "enriched":
                champs = ", ".join(res.get("fields") or [])
                journal(log, f"  [COMPLETEE] {ref} -> {champs}", ecran=False)
                enrichies += 1
            else:
                journal(log, f"  [INCHANGEE] {ref}", ecran=False)
                inchangees += 1
        except requests.HTTPError as e:
            journal(log, f"  [ERREUR]    {ref} -> HTTP {e.response.status_code} : "
                         f"{e.response.text[:150]}")
            erreurs += 1
        except Exception as e:
            journal(log, f"  [ERREUR]    {ref} -> {e}")
            erreurs += 1

    journal(log, f"\n  Fiches — creees : {creees}  |  completees : {enrichies}"
                 f"  |  inchangees : {inchangees}  |  erreurs : {erreurs}")
    return erreurs


def passe_of(pont, log, date_iso, limite):
    journal(log, "\n=== Passe 2 — Ordres de fabrication ===")
    lignes = lit_of(date_iso)
    if limite:
        lignes = lignes[:limite]
    journal(log, f"    {len(lignes)} OF cree(s) depuis le {date_iso}\n")

    importes = completes = inchanges = erreurs = 0
    sans_metrage = sans_adhesif = sans_fiche = 0

    for row in lignes:
        numero = str(row.numero_of).strip()
        if to_float(row.metrage) is None:
            sans_metrage += 1
        if to_float(row.adhesif_grammage) is None:
            sans_adhesif += 1
        if row.matiere is None and row.machine is None:
            sans_fiche += 1
        try:
            res = pont.post("/api/bridge/of", payload_of(row))
            if res.get("dry_run"):
                inchanges += 1
                continue
            if res.get("inserted"):
                journal(log, f"  [IMPORTE]   OF {numero}", ecran=False)
                importes += 1
            elif res.get("reason") in ("enriched", "refreshed"):
                champs = ", ".join(sorted(set((res.get("enriched_fields") or [])
                                              + (res.get("refreshed_fields") or []))))
                journal(log, f"  [COMPLETE]  OF {numero} -> {champs}", ecran=False)
                completes += 1
            else:
                journal(log, f"  [INCHANGE]  OF {numero}", ecran=False)
                inchanges += 1
        except requests.HTTPError as e:
            journal(log, f"  [ERREUR]    OF {numero} -> HTTP {e.response.status_code} : "
                         f"{e.response.text[:150]}")
            erreurs += 1
        except Exception as e:
            journal(log, f"  [ERREUR]    OF {numero} -> {e}")
            erreurs += 1

    journal(log, f"\n  OF — importes : {importes}  |  completes : {completes}"
                 f"  |  inchanges : {inchanges}  |  erreurs : {erreurs}")
    journal(log, f"  Sans metrage en base : {sans_metrage}  |  "
                 f"sans grammage adhesif : {sans_adhesif} "
                 f"(normal quand matadhesif = « Permanent » sans reference)")
    if sans_fiche:
        journal(log, f"  Sans fiche technique jointe : {sans_fiche} "
                     f"— verifier les formats signales en passe 1")
    return erreurs


# ── Main ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Import unique Access -> MySifa (fiches techniques + OF).")
    ap.add_argument("--base-url", default=URL_STAGING,
                    help=f"Instance visee (defaut {URL_STAGING})")
    ap.add_argument("--depuis", default="2026-01-01",
                    help="Date de depart AAAA-MM-JJ (defaut 2026-01-01)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Lit Access et affiche les volumes sans rien ecrire")
    ap.add_argument("--fiches-seules", action="store_true",
                    help="Passe 1 uniquement")
    ap.add_argument("--of-seuls", action="store_true",
                    help="Passe 2 uniquement — suppose les fiches deja presentes")
    ap.add_argument("--limite", type=int, default=0,
                    help="Ne traiter que les N premieres lignes de chaque passe")
    args = ap.parse_args()

    try:
        datetime.strptime(args.depuis, "%Y-%m-%d")
    except ValueError:
        sys.exit("--depuis attend une date au format AAAA-MM-JJ, ex. 2026-01-01")

    if not args.dry_run and not API_KEY:
        sys.exit('Cle API absente. setx MYSIFA_API_KEY "msk_..." puis rouvrir '
                 'le terminal.')

    pont = Pont(args.base_url, args.dry_run)

    print(f"Instance  : {pont.base_url}" + ("   [DRY-RUN — aucune ecriture]"
                                            if args.dry_run else ""))
    print(f"Depuis    : {args.depuis}")
    print(f"Fiches    : {DB_FICHES}")
    print(f"OF        : {DB_OF}")

    if not args.dry_run:
        pont.verifie()
        if pont.base_url.rstrip("/") == URL_PROD:
            rep = input("\nEcriture sur la PRODUCTION. Taper « oui » pour "
                        "confirmer : ").strip().lower()
            if rep != "oui":
                sys.exit("Annule.")

    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_log = f"import_access_{args.depuis.replace('-', '')}_{horodatage}.log"
    erreurs = 0
    with open(nom_log, "w", encoding="utf-8") as log:
        journal(log, f"Import Access -> {pont.base_url}, depuis {args.depuis}, "
                     f"lance le {datetime.now():%d/%m/%Y %H:%M}", ecran=False)
        if not args.of_seuls:
            erreurs += passe_fiches(pont, log, args.depuis, args.limite)
        if not args.fiches_seules:
            erreurs += passe_of(pont, log, args.depuis, args.limite)

    print(f"\nDetail ligne a ligne : {nom_log}")
    if erreurs:
        print(f"{erreurs} erreur(s) — relancer le script apres correction, "
              f"il est rejouable sans doublon.")
    sys.exit(1 if erreurs else 0)


if __name__ == "__main__":
    try:
        main()
    except pyodbc.Error as e:
        sys.exit(f"\nErreur Access : {e}\n"
                 "Verifier que Python et le pilote « Microsoft Access Driver "
                 "(*.mdb, *.accdb) » sont dans la meme architecture (64 bits),\n"
                 f"et que le partage {BASE_DIR} est accessible depuis ce poste.")
    except KeyboardInterrupt:
        sys.exit("\nInterrompu.")
