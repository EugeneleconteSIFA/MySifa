"""
Le tarif quitte la déclinaison pour rejoindre le fournisseur.

Le problème
-----------
Devise, base de prix, transport et taxes étaient portés par la DÉCLINAISON
(`mp_matiere_declinaison`), donc partagés par tous ses fournisseurs. Deux
fournisseurs sur le même 17 g/m² héritaient du même mode de transport — alors
que Meltavis livre par conteneur depuis l'Asie et Bostik par forfait local.
Conséquence directe : ajouter un deuxième fournisseur pour comparer ne servait
à rien, les deux sortaient le même coût au m² à un rapport de prix près.

Le bon niveau
-------------
Un tarif ne dépend ni de la laize ni du grammage : il dépend de chez qui on
achète, et de ce qu'on lui achète.

  fournisseur            → devise d'achat (Meltavis facture en USD, Coquelle
                           en EUR). Vrai pour tout ce qu'on lui prend.
  fournisseur × matière  → base de prix, transport, taxes. Le conteneur de
                           18 000 kg décrit comment on achète CET adhésif chez
                           CE fournisseur ; le frontal du même fournisseur peut
                           arriver autrement.
  déclinaison            → grammage et perte. Physique de la matière, pas du
                           vendeur. C'est ce qui fait que 17 et 22 g/m² au même
                           prix au kilo ne coûtent pas pareil au m².
  déclinaison × fournisseur → le prix d'achat lui-même (déjà en place dans
                           `mp_matiere_prix`).

Ce que fait cette migration
---------------------------
1. Ajoute `price_currency` sur `fournisseurs_fsc`.
2. Crée `mc_tarif_fournisseur`, une ligne par couple (fournisseur, matière).
3. Reprend l'existant : chaque couple (fournisseur, matière) déjà présent dans
   `mp_matiere_prix` reçoit un tarif recopié des réglages de sa déclinaison.
   Aucun coût ne bouge le jour du déploiement.

Ce qu'elle ne fait PAS
----------------------
Elle ne supprime aucune colonne de `mp_matiere_declinaison`. Elles restent le
repli quand une ligne de prix n'a pas de fournisseur — et il en existe : une
déclinaison créée vierge porte une ligne sans fournisseur. Les effacer aurait
aussi rendu la migration irréversible pour rien.

Ce que la reprise ne peut pas deviner
-------------------------------------
Les réglages d'un fournisseur SECONDAIRE n'ont jamais existé : sa ligne héritait
de ceux de la déclinaison, posés pour le principal. La reprise les lui recopie
donc — c'est le seul choix qui ne fasse bouger aucun coût au déploiement, mais
c'est une hypothèse, pas une donnée. Un fournisseur secondaire qui livre
autrement est à corriger à la main, une fois, dans sa fiche tarif.

Le conflit de reprise
---------------------
Un même fournisseur peut vendre plusieurs déclinaisons de la même matière (17,
19, 22 g/m²) avec, aujourd'hui, des réglages différents sur chacune. Le tarif
étant unique par couple, il faut trancher : on retient les réglages de la
déclinaison dont ce fournisseur est le principal ; à défaut, la plus anciennes
des siennes. Les cas où les réglages divergeaient sont comptés et affichés au
démarrage — ce sont les seuls endroits où un coût peut bouger, et il vaut mieux
les connaître que les découvrir.
"""

from __future__ import annotations

import sqlite3

NOM = "mc_tarif_fournisseur"
DEPEND = ["mp_transport_methodes"]

# Les réglages qui descendent au niveau (fournisseur, matière). `price_currency`
# n'y est pas : il monte au fournisseur seul.
_CHAMPS_TARIF = (
    "price_basis",
    "taxe_pct",
    "is_imported",
    "transport_mode",
    "transport_unit_price",
    "transport_pct",
    "transport_cout",
    "transport_quantite",
)


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    # ── 1. La devise monte au fournisseur ───────────────────────────────────
    cols_f = _colonnes(conn, "fournisseurs_fsc")
    if cols_f and "price_currency" not in cols_f:
        conn.execute(
            "ALTER TABLE fournisseurs_fsc ADD COLUMN price_currency "
            "TEXT NOT NULL DEFAULT 'EUR'"
        )

    # ── 2. Le tarif par couple (fournisseur, matière) ───────────────────────
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mc_tarif_fournisseur (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id       INTEGER NOT NULL
                                 REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
            matiere_id           INTEGER NOT NULL
                                 REFERENCES matieres_premieres(id) ON DELETE CASCADE,
            price_basis          TEXT    NOT NULL DEFAULT 'PER_KG',
            taxe_pct             REAL    NOT NULL DEFAULT 0,
            is_imported          INTEGER NOT NULL DEFAULT 0,
            transport_mode       TEXT    NOT NULL DEFAULT 'AMOUNT',
            transport_unit_price REAL    NOT NULL DEFAULT 0,
            transport_pct        REAL    NOT NULL DEFAULT 0,
            transport_cout       REAL    NOT NULL DEFAULT 0,
            transport_quantite   REAL    NOT NULL DEFAULT 0,
            updated_at           TEXT    NOT NULL
                                 DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            updated_by_name      TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mctf_unique
            ON mc_tarif_fournisseur(fournisseur_id, matiere_id);
        CREATE INDEX IF NOT EXISTS idx_mctf_matiere
            ON mc_tarif_fournisseur(matiere_id);
        """
    )

    # Rien à reprendre si le socle des déclinaisons n'est pas encore là (base
    # fraîche : les tables se créent dans l'ordre, celle-ci peut passer avant).
    cols_d = _colonnes(conn, "mp_matiere_declinaison")
    cols_p = _colonnes(conn, "mp_matiere_prix")
    if not cols_d or not cols_p:
        print(f"[MySifa] migration {NOM} : tables créées, rien à reprendre.")
        return
    if not set(_CHAMPS_TARIF) <= cols_d:
        print(f"[MySifa] migration {NOM} : réglages absents de la déclinaison, "
              "reprise sautée.")
        return

    # ── 3. Reprise ──────────────────────────────────────────────────────────
    # Une ligne par couple (fournisseur, matière). L'ordre du SELECT décide qui
    # gagne : la déclinaison dont ce fournisseur est le principal d'abord, puis
    # la plus ancienne. `INSERT OR IGNORE` garde le premier venu.
    champs = ", ".join(_CHAMPS_TARIF)
    source = ", ".join(f"d.{c}" for c in _CHAMPS_TARIF)
    lignes = conn.execute(
        f"""SELECT p.fournisseur_id, d.matiere_id, {source}, p.principal
              FROM mp_matiere_prix p
              JOIN mp_matiere_declinaison d ON d.id = p.declinaison_id
             WHERE p.fournisseur_id IS NOT NULL
             ORDER BY p.fournisseur_id, d.matiere_id, p.principal DESC, d.id ASC"""
    ).fetchall()

    repris = 0
    vus: dict[tuple[int, int], tuple] = {}
    divergents: set[tuple[int, int]] = set()
    for r in lignes:
        cle = (int(r["fournisseur_id"]), int(r["matiere_id"]))
        reglages = tuple(r[c] for c in _CHAMPS_TARIF)
        if cle in vus:
            # Deux déclinaisons du même couple ne disaient pas la même chose :
            # le tarif retenu est celui du principal, l'autre est signalé.
            if vus[cle] != reglages:
                divergents.add(cle)
            continue
        vus[cle] = reglages
        conn.execute(
            f"""INSERT OR IGNORE INTO mc_tarif_fournisseur
                (fournisseur_id, matiere_id, {champs})
                VALUES (?, ?{", ?" * len(_CHAMPS_TARIF)})""",
            (cle[0], cle[1], *reglages),
        )
        repris += 1

    # ── 4. La devise du fournisseur ─────────────────────────────────────────
    # Piège de la reprise : la devise vivait sur la déclinaison, donc un
    # fournisseur SECONDAIRE porte la devise choisie pour le principal. Compter
    # toutes ses lignes ferait passer Bostik en USD au seul motif qu'il propose
    # un prix sur un adhésif importé par Meltavis.
    #
    # On ne retient donc que les lignes où le fournisseur est PRINCIPAL : ce
    # sont les seules dont la devise ait jamais servi à calculer quoi que ce
    # soit. Un fournisseur principal nulle part garde EUR, le défaut.
    devises = 0
    ambigus = 0
    if "price_currency" in _colonnes(conn, "fournisseurs_fsc"):
        par_fournisseur: dict[int, dict[str, int]] = {}
        for r in conn.execute(
            """SELECT p.fournisseur_id AS fid, d.price_currency AS devise
                 FROM mp_matiere_prix p
                 JOIN mp_matiere_declinaison d ON d.id = p.declinaison_id
                WHERE p.fournisseur_id IS NOT NULL AND p.principal = 1
                  AND d.price_currency IS NOT NULL AND d.price_currency <> ''"""
        ).fetchall():
            par_fournisseur.setdefault(int(r["fid"]), {})
            par_fournisseur[int(r["fid"])][r["devise"]] = (
                par_fournisseur[int(r["fid"])].get(r["devise"], 0) + 1
            )
        for fid, comptes in par_fournisseur.items():
            classement = sorted(comptes.items(), key=lambda kv: -kv[1])
            gagnante, n = classement[0]
            # Égalité parfaite : rien ne permet de trancher, on laisse le défaut
            # plutôt que de tirer à pile ou face sur un prix.
            if len(classement) > 1 and classement[1][1] == n:
                ambigus += 1
                continue
            if gagnante != "EUR":
                devises += conn.execute(
                    "UPDATE fournisseurs_fsc SET price_currency=? WHERE id=?",
                    (gagnante, fid),
                ).rowcount

    message = (
        f"[MySifa] migration {NOM} : {repris} tarif(s) fournisseur × matière repris, "
        f"{devises} devise(s) remontée(s) au fournisseur."
    )
    if divergents:
        message += (
            f" ATTENTION — {len(divergents)} couple(s) avaient des réglages "
            "différents selon la déclinaison : le tarif du fournisseur principal "
            "a été retenu, à vérifier."
        )
    if ambigus:
        message += (
            f" {ambigus} fournisseur(s) sans devise majoritaire : laissés en EUR."
        )
    print(message)
