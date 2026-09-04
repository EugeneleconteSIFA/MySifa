"""
MyExpé — pilotage amont des expéditions.

Le problème que cette migration ouvre la voie à corriger : aujourd'hui une
ligne `expe_departs` n'existe qu'une fois le bon de livraison édité. Tant que
la production tourne, l'expédition n'existe nulle part — donc on attend la fin
de prod pour réserver un transport, et l'affrètement se fait dans l'urgence.

Le départ devient un objet à cycle de vie long, créé dès que le dossier est au
planning :

    prevu  →  en_attente  →  valide
    (rien n'est commandé)  (transport commandé, départ programmé)  (parti, historisé)

`statut = 'prevu'` est une valeur NEUVE. Les écrans existants filtrent sur
`'en_attente'` et `'valide'` : un départ prévisionnel n'apparaît donc dans
aucun d'eux tant qu'il n'a pas basculé. C'est volontaire — aucune régression
sur « Départs programmés » ni sur l'historique.

Les jalons sont stockés en DATES, pas en booléens : « transport commandé »
sans « quand » ne permet ni de relancer ni de mesurer l'anticipation gagnée.
Le troisième jalon d'Eugène — le BL — n'est pas stocké : il se lit dans RVGI
(`liv_entete` via `liv_ligne.numcde`) et dans `no_bl`. Une donnée qui a déjà
une source ne se recopie pas.

`nb_palette` reste la quantité saisie, qui fait foi. `nb_palette_estime` porte
l'estimation calculée depuis la fiche technique — les deux cohabitent pour que
l'on puisse voir, après coup, à quel point l'estimation était juste.
"""

NOM = "expe_pilotage_amont"


COLONNES = [
    # Estimation de palettes calculée depuis la fiche technique (le calcul vit
    # dans app/services/palettes_estimation.py). Ne remplace jamais nb_palette.
    ("nb_palette_estime", "REAL"),
    ("nb_palette_estime_maj_le", "TEXT"),
    # Jalons du cycle amont.
    ("transport_commande_le", "TEXT"),
    ("transport_commande_par", "TEXT"),
    ("parti_le", "TEXT"),
    ("parti_par", "TEXT"),
    # 'prevue' = date déduite du planning, 'confirmee' = date arrêtée avec le
    # transporteur. Sans ça, une date d'enlèvement calculée et une date
    # négociée se ressemblent, et on ne sait plus laquelle est un engagement.
    ("date_enlevement_source", "TEXT"),
    # 'manuel' = saisi dans MyExpé, 'pilotage' = né du tableau de bord.
    ("origine", "TEXT"),
    # Clé de regroupement de l'envoi (client + destination + date), pour
    # retrouver le prévisionnel d'un même camion d'un rafraîchissement à
    # l'autre sans recréer de doublon.
    ("cle_envoi", "TEXT"),
]


def _colonnes(conn, table):
    return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}


def appliquer(conn):
    presentes = _colonnes(conn, "expe_departs")
    if not presentes:
        # Table absente : les migrations historiques ne sont pas passées.
        return

    ajoutees = 0
    for nom, type_sql in COLONNES:
        if nom not in presentes:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN %s %s" % (nom, type_sql)
            )
            ajoutees += 1

    # Réglages du pilotage. Même mécanique que `transport_planning_params` :
    # une table clé/valeur, des défauts dans le code, aucune valeur SIFA en dur.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS expe_pilotage_params ("
        " cle TEXT PRIMARY KEY NOT NULL, valeur TEXT NOT NULL)"
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_departs_statut_date "
        "ON expe_departs(statut, date_enlevement)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_expe_departs_cle_envoi "
        "ON expe_departs(cle_envoi) WHERE cle_envoi IS NOT NULL"
    )

    # Reprise : tout ce qui existe avant cette migration a été saisi à la main,
    # et sa date d'enlèvement est une date arrêtée, pas une prévision.
    repris = conn.execute(
        "UPDATE expe_departs SET origine='manuel' WHERE origine IS NULL"
    ).rowcount
    conn.execute(
        "UPDATE expe_departs SET date_enlevement_source='confirmee' "
        " WHERE date_enlevement_source IS NULL"
    )
    # Un départ déjà validé est forcément parti : on date le jalon avec la
    # validation plutôt que de laisser un historique entier sans jalon.
    conn.execute(
        "UPDATE expe_departs SET parti_le = COALESCE(validated_at, date_enlevement) "
        " WHERE parti_le IS NULL AND statut = 'valide'"
    )
    # Idem pour la commande de transport : un numéro de commande transporteur
    # renseigné vaut jalon, à la date de création du départ.
    conn.execute(
        "UPDATE expe_departs SET transport_commande_le = created_at "
        " WHERE transport_commande_le IS NULL "
        "   AND TRIM(COALESCE(no_cde_transport, '')) != ''"
    )

    conn.commit()
    print(
        "[MySifa] migration %s : %d colonne(s) ajoutee(s), %d depart(s) repris."
        % (NOM, ajoutees, repris)
    )
