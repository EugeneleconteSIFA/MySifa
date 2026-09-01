"""
Recale la categorie et la severite des saisies sur le referentiel des codes.

`production_data.operation_category` et `operation_severity` sont ecrites au
moment de la saisie, en copiant le referentiel de l'epoque. Elles ne bougeaient
plus ensuite : reclasser un code dans Parametres ne touchait pas l'historique,
et l'ecran promettait donc un reclassement qu'il ne faisait pas.

Constat en production le 01/09/2026 : le code 58 « Changement bobines » portait
trois categories selon le mois de saisie — `appro` en avril, `calage` depuis
mai, `arret` dans le referentiel depuis aujourd'hui. Le code 73 « Probleme
Turret » etait pour moitie en `arret`, pour moitie en `technique`. Consequence
directe : les minutes de changement de bobines et de probleme Turret ne
comptaient pas dans les arrets, donc la cadence (metrage / (production +
arret)) valait la vitesse de production nue sur plus d'un dossier sur deux.

A partir d'ici, le referentiel fait foi : cette migration realigne l'existant,
et `PUT /api/settings/operation-codes/{code}` propage chaque changement futur.

Le LIBELLE n'est pas recale : renommer un code ne doit avoir aucune
consequence sur l'historique. C'est une identite, pas une classification.

Les codes presents dans les saisies mais absents du referentiel (supprimes
depuis) gardent ce qu'ils ont : on n'invente pas une categorie pour eux.
"""

NOM = "recaler_categories_saisies"


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if not {"production_data", "operation_codes"} <= tables:
        return  # base de test sans ces tables : rien a recaler

    codes = conn.execute(
        "SELECT code, category, severity FROM operation_codes "
        "WHERE code IS NOT NULL AND TRIM(code) <> ''"
    ).fetchall()

    total = 0
    detail = []
    for ligne in codes:
        code = str(ligne[0]).strip()
        categorie = ligne[1]
        severite = ligne[2]
        if categorie is None and severite is None:
            continue
        cur = conn.execute(
            """UPDATE production_data
                  SET operation_category = COALESCE(?, operation_category),
                      operation_severity = COALESCE(?, operation_severity)
                WHERE operation_code = ?
                  AND (COALESCE(operation_category,'') <> COALESCE(?, operation_category, '')
                       OR COALESCE(operation_severity,'') <> COALESCE(?, operation_severity, ''))""",
            (categorie, severite, code, categorie, severite),
        )
        if cur.rowcount:
            total += cur.rowcount
            detail.append(f"{code}->{categorie or '?'} ({cur.rowcount})")

    conn.commit()
    resume = ", ".join(detail[:8]) + (" …" if len(detail) > 8 else "")
    print(f"[MySifa] migration {NOM} : {total} saisie(s) recalee(s)"
          + (f" — {resume}" if detail else "."))
