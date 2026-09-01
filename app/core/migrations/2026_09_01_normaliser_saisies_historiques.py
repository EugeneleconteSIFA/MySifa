"""
Reprise des saisies importees de l'ancien systeme : dates et libelles machine.

Deux formes coexistent dans `production_data`, heritees de la bascule d'avril
2026, et les deux faussent silencieusement toute lecture d'historique.

**Les dates.** 3 991 lignes sont en ISO (`2026-04-01T05:15:10`), 75 sont au
format francais (`31/03/2026 21:24:00`), dont certaines avec un `C` colle a la
fin — un artefact de l'export d'origine. La colonne etant du TEXTE, un
`ORDER BY date_operation` range `31/03/2026` apres `2026-09-01` : les plus
vieilles lignes du fichier remontent en tete de l'historique. Un `BETWEEN` sur
une periode ne les voit jamais. Les routes qui lisent la journee courante
compensent deja par un `OR date_operation LIKE '<jour au format FR>%'` ; ce
rattrapage devient inutile ici, mais il reste en place, sans effet.

**Les libelles machine.** L'ancien systeme ecrivait `1 - COHESIO 1`,
`2 - COHESIO 2`, et une fois `1 - COHESIO !` (faute de frappe sur le 1).
MySifa ecrit `Cohesio 1` et `Cohesio 2`. Tout regroupement par machine sur
l'historique se scinde donc en deux colonnes pour la meme machine.

La resolution ne code aucun nom de machine en dur : elle rapproche le libelle
du referentiel de la table `machines`, apres avoir retire le prefixe `N - ` et
neutralise casse, accents et ponctuation. Le libelle qui ne se rapproche de
rien n'est pas touche — mieux vaut une valeur bizarre et visible qu'une valeur
rangee de force sous la mauvaise machine.

Le libelle vide devient NULL : les codes 86/87 (arrivee et depart du personnel)
n'ont pas de machine, et ils l'expriment deja par NULL partout ailleurs.
"""
import re
import unicodedata

NOM = "normaliser_saisies_historiques"

_DATE_FR = re.compile(r"^(\d{2})/(\d{2})/(\d{4})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?")
_PREFIXE_NUM = re.compile(r"^\s*(\d+)\s*-\s*(.*)$")


def _cle(txt: str) -> str:
    """Casse, accents et ponctuation neutralises : « Cohesio 1 » -> « COHESIO1 »."""
    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", str(txt or ""))
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^A-Za-z0-9]", "", sans_accent).upper()


def _iso(valeur: str):
    """`31/03/2026 21:24:00` -> `2026-03-31T21:24:00`. None si ce n'est pas du FR."""
    m = _DATE_FR.match(str(valeur or ""))
    if not m:
        return None
    jour, mois, annee, heure, minute, seconde = m.groups()
    return f"{annee}-{mois}-{jour}T{int(heure):02d}:{minute}:{seconde or '00'}"


def _resoudre_machine(valeur: str, referentiel: dict):
    """Nom canonique de la machine, ou None si le libelle ne se rapproche de rien."""
    brut = str(valeur or "").strip()
    if not brut:
        return None
    if brut in referentiel.values():
        return None  # deja canonique, rien a faire

    candidats = [_cle(brut)]
    m = _PREFIXE_NUM.match(brut)
    if m:
        numero, reste = m.group(1), m.group(2)
        candidats.append(_cle(reste))
        # « 1 - COHESIO ! » : le 1 du prefixe dit quelle machine c'est, la
        # ponctuation finale a remplace le chiffre. On recompose avec le
        # prefixe plutot que d'ecrire le nom attendu dans le code.
        candidats.append(_cle(re.sub(r"[^A-Za-z]", "", reste)) + numero)

    for c in candidats:
        if c in referentiel:
            return referentiel[c]
    return None


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "production_data" not in tables:
        return  # base de test sans le module production : rien a reprendre

    # ── Dates ───────────────────────────────────────────────────────
    n_dates = 0
    lignes = conn.execute(
        "SELECT id, date_operation FROM production_data "
        "WHERE date_operation IS NOT NULL AND date_operation LIKE '__/__/____%'"
    ).fetchall()
    for r in lignes:
        iso = _iso(r[1])
        if iso:
            conn.execute(
                "UPDATE production_data SET date_operation=? WHERE id=?", (iso, r[0])
            )
            n_dates += 1

    # ── Libelles machine ────────────────────────────────────────────
    n_machines = 0
    n_vides = 0
    if "machines" in tables:
        referentiel = {}
        for r in conn.execute("SELECT nom FROM machines").fetchall():
            nom = str(r[0] or "").strip()
            if nom:
                referentiel[_cle(nom)] = nom
        if referentiel:
            valeurs = [
                r[0] for r in conn.execute(
                    "SELECT DISTINCT machine FROM production_data "
                    "WHERE machine IS NOT NULL AND TRIM(machine) <> ''"
                ).fetchall()
            ]
            for valeur in valeurs:
                canonique = _resoudre_machine(valeur, referentiel)
                if canonique:
                    cur = conn.execute(
                        "UPDATE production_data SET machine=? WHERE machine=?",
                        (canonique, valeur),
                    )
                    n_machines += cur.rowcount

    cur = conn.execute(
        "UPDATE production_data SET machine=NULL "
        "WHERE machine IS NOT NULL AND TRIM(machine) = ''"
    )
    n_vides = cur.rowcount

    conn.commit()
    print(
        f"[MySifa] migration {NOM} : {n_dates} date(s) passee(s) en ISO, "
        f"{n_machines} libelle(s) machine aligne(s), {n_vides} vide(s) mis a NULL."
    )
