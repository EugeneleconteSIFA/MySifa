"""
Types d'article RVGI : le décodage de `fic_para` et le regroupement en familles.

Ce que ce test protège, dans l'ordre où ça casse :

1. **La lecture des libellés.** RVGI range ses paramètres sous des numéros
   `15 TT PP` et porte ses propres coquilles de recopie — `150705` annonce
   « Encres » au milieu du bloc des adhésifs. Prendre le premier suffixe venu
   renommerait un type entier. C'est le suffixe majoritaire qui tranche.
2. **La jointure des réceptions.** `lif_ligne` ne porte aucun article : il vient
   de `cdf_ligne`, sur le couple (numéro, ligne). Sur le seul numéro, chaque
   réception ramènerait toutes les lignes de sa commande et l'écran
   multiplierait ses lignes sans le dire.
3. **Le classement.** Une famille inconnue ou un code illisible sont refusés,
   pas enregistrés en silence.

Les deux derniers blocs ne tournent que si le miroir est présent.
"""
import sqlite3
import sys

sys.path.insert(0, ".")
from app.services import erp_types                     # noqa: E402
from app.services import erp_catalogue as cat          # noqa: E402
from app.services import erp_mirror as miroir          # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def vrai(libelle, condition, detail=""):
    global ko
    if not condition:
        ko += 1
    print(f"  {'OK ' if condition else 'KO '} {libelle}")
    if not condition and detail:
        print(f"       {detail}")


# ── 1. Le suffixe d'un paramètre ────────────────────────────────────────────
print("\nSuffixe de `des1`")
check("libellé simple", erp_types._suffixe("Ua par défaut : Cartons"), "Cartons")
check("deux-points dans le préfixe",
      erp_types._suffixe("Cpt transfert achats s/Tva : Adhésifs"), "Adhésifs")
check("sans deux-points", erp_types._suffixe("Licence RVGI Software"), "")
check("vide", erp_types._suffixe(None), "")


# ── 2. Le décodage d'un bloc, coquilles comprises ───────────────────────────
print("\nDécodage de `fic_para` — le bloc des adhésifs porte une coquille")
faux = sqlite3.connect(":memory:")
faux.row_factory = sqlite3.Row
faux.execute("CREATE TABLE fic_para (numero INTEGER, des1 TEXT, corbeille INTEGER)")
faux.executemany(
    "INSERT INTO fic_para (numero, des1, corbeille) VALUES (?,?,0)",
    [
        # Bloc 07 → type 9. Trois « Adhésifs », une coquille « Encres » :
        # c'est exactement la forme relevée en production le 02/09/2026.
        (150702, "Avec gestion par fournisseur : Adhésifs"),
        (150715, "Matière générique : Adhésifs"),
        (150765, "Ua par défaut : Adhésifs"),
        (150705, "Gestion nomenclatures : Encres"),
        # Bloc 17 → type 19.
        (151702, "Avec gestion par fournisseur : Cartons"),
        (151765, "Ua par défaut : Cartons"),
        # Bloc sans nom : un suffixe purement numérique n'est pas un libellé.
        (150065, "Ua par défaut : 2"),
        # Ligne à la corbeille : jamais lue.
    ],
)
faux.execute("INSERT INTO fic_para (numero, des1, corbeille) VALUES (?,?,1)",
             (150702, "Avec gestion par fournisseur : Supprimé"))
lus = erp_types._libelles_depuis_miroir(faux)
check("la majorité l'emporte sur la coquille", lus.get(9), "Adhésifs")
check("décalage de deux : bloc 17 → type 19", lus.get(19), "Cartons")
check("bloc sans nom ignoré", lus.get(2), None)
faux.close()


# ── 3. Le classement ────────────────────────────────────────────────────────
print("\nClassement d'un type")
base = sqlite3.connect(":memory:")
base.row_factory = sqlite3.Row
base.execute(
    "CREATE TABLE erp_type_famille (type_code INTEGER PRIMARY KEY, famille TEXT NOT NULL,"
    " libelle_secours TEXT, updated_at TEXT, updated_by_name TEXT)"
)
erp_types.enregistrer_famille(base, 7, "matiere", auteur="test")
check("classé", erp_types.familles_par_type(base).get(7), "matiere")
erp_types.enregistrer_famille(base, 7, "consommable", auteur="test")
check("reclassé", erp_types.familles_par_type(base).get(7), "consommable")
erp_types.enregistrer_famille(base, 7, "", auteur="test")
check("déclassé", erp_types.familles_par_type(base).get(7), None)

for mauvaise in ("matieres", "MATIERE", "outil"):
    try:
        erp_types.enregistrer_famille(base, 7, mauvaise)
        vrai(f"famille « {mauvaise} » refusée", False, "elle a été enregistrée")
    except ValueError:
        vrai(f"famille « {mauvaise} » refusée", True)
try:
    erp_types.enregistrer_famille(base, "sept", "matiere")
    vrai("code non entier refusé", False, "il a été enregistré")
except ValueError:
    vrai("code non entier refusé", True)
base.close()


# ── 4. Les clés du filtre de famille ────────────────────────────────────────
print("\nFiltre de famille — des listes de codes, développées en IN (...)")
base = sqlite3.connect(":memory:")
base.row_factory = sqlite3.Row
base.execute(
    "CREATE TABLE erp_type_famille (type_code INTEGER PRIMARY KEY, famille TEXT NOT NULL,"
    " libelle_secours TEXT, updated_at TEXT, updated_by_name TEXT)"
)
for code, fam in [(3, "matiere"), (4, "matiere"), (1, "sous_traitance"), (11, "outillage")]:
    erp_types.enregistrer_famille(base, code, fam)
familles = erp_types.familles_par_type(base)
cles = {}
for cle, libelle in erp_types.FAMILLES:
    codes = sorted(c for c, f in familles.items() if f == cle)
    if codes:
        cles["|".join(str(c) for c in codes)] = libelle
check("les codes d'une famille sont joints par « | »", cles.get("3|4"), "Matière première")
check("une famille d'un seul code n'a pas de séparateur",
      cles.get("1"), "Sous-traitance")
vrai("une famille sans aucun code ne produit pas de clé vide", "" not in cles)
base.close()


# ── 5. Sur le miroir réel, s'il est là ──────────────────────────────────────
if not miroir.miroir_present():
    print("\nMiroir absent — contrôles sur données réelles ignorés.")
else:
    print("\nÉcran Réceptions sur le miroir réel")
    with miroir.get_erp_db() as conn:
        colonnes = {
            t: {r[1] for r in conn.execute('PRAGMA table_info("%s")' % t)}
            for t in miroir.tables_presentes(conn)
        }
        brut = conn.execute(
            "SELECT COUNT(*) FROM lif_ligne WHERE corbeille = 0"
        ).fetchone()[0]

    ec = cat.adapter_ecran(cat.PAR_CLE["receptions"], colonnes)
    vrai("l'écran survit à l'adaptation", ec is not None)
    if ec:
        noms = [c["nom"] for c in ec["colonnes"]]
        for attendu in ("article", "des1", "famille", "type_article", "laize",
                        "qte_cde", "lpos"):
            vrai(f"colonne « {attendu} » présente", attendu in noms)
        vrai("la famille refuse le filtre d'en-tête",
             any(c["nom"] == "famille" and c.get("sans_filtre") for c in ec["colonnes"]))

        # LE contrôle qui compte : la jointure ne doit pas multiplier les lignes.
        total = miroir.lister(ec, taille=1)["total"]
        check("la jointure ne duplique aucune ligne", total, brut)

        # Chaque ligne doit tomber dans une famille et une seule.
        e = cat.enums()
        somme = 0
        for cle in e.get("famille_article_filtre", {}):
            somme += miroir.lister(ec, filtres={"famille": cle}, taille=1)["total"]
        check("les familles partitionnent les réceptions", somme, total)

        # La laize n'existe que sur les matières laizées : c'est ce qui permet
        # d'entrer une bobine dans la bonne laize de MyStock.
        laizees = miroir.lister(ec, filtres={"famille": "3|4|5|6|7|8|9"},
                                taille=200)["lignes"]
        avec = [l for l in laizees if (l.get("laize") or "").strip()]
        vrai("les matières portent leur laize",
             len(avec) >= 0.5 * len(laizees) if laizees else True,
             f"{len(avec)} sur {len(laizees)}")

    # ── 6. Le lien vers la ligne de commande, et non vers la commande ────────
    #
    # Depuis la ligne 3 d'une commande de six lignes, le lien portait sur le
    # seul `numero` : il ramenait les six réceptions, sans dire laquelle
    # répondait à la ligne ouverte. Ces deux liens doivent donc rendre des
    # nombres DIFFÉRENTS sur une commande à plusieurs lignes — sinon le lien
    # précis est retombé sur la pièce entière.
    print("\nLien réception → ligne de commande")
    with miroir.get_erp_db() as conn:
        piece = conn.execute(
            "SELECT numero FROM lif_ligne WHERE corbeille = 0 "
            "GROUP BY numero HAVING COUNT(*) >= 5 ORDER BY numero DESC LIMIT 1"
        ).fetchone()
        ligne = conn.execute(
            "SELECT id FROM lif_ligne WHERE numero = ? AND corbeille = 0 "
            "ORDER BY ligne LIMIT 1", (piece["numero"],)
        ).fetchone() if piece else None

    if ligne is None:
        print("  -- aucune commande à cinq lignes dans ce miroir, contrôle ignoré.")
    else:
        def resoudre(cle):
            e = cat.ecran(cle)
            return cat.adapter_ecran(e, colonnes) if e else None

        par_label = {l.get("label"): l for l in miroir.liens(ec, ligne["id"], resoudre)}
        precis = par_label.get("La ligne de commande")
        entier = par_label.get("La commande fournisseur")
        vrai("le lien de ligne est proposé", precis is not None)
        vrai("le lien de pièce est proposé", entier is not None)
        if precis and entier:
            check("le lien de ligne ne ramène qu'une ligne de commande",
                  precis.get("total"), 1)
            vrai("le lien de pièce en ramène davantage",
                 (entier.get("total") or 0) > 1,
                 f"pièce : {entier.get('total')}")
        # Ces trois-là ne pouvaient pas exister avant la jointure vers
        # `cdf_ligne` : leurs clés vivent sur la commande, pas sur la réception.
        for label in ("L'article", "La matière", "Le fournisseur"):
            vrai(f"lien « {label} » proposé depuis une réception",
                 label in par_label)

print("\n%s" % ("Tout est vert." if not ko else f"{ko} contrôle(s) en échec."))
sys.exit(1 if ko else 0)
