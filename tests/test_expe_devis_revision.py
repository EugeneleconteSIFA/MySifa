"""MyExpé — modifier une demande de tarif après envoi, sans la clôturer.

Avant : une demande partie chez les transporteurs était figée. Corriger un
poids obligeait à la clôturer puis la dupliquer, ce qui changeait la référence
et dispersait les offres sur deux demandes. Ce fichier verrouille le
remplaçant :

1. Le classement des champs : destination, type d'envoi, poids et palettes
   demandent un nouveau prix ; les contraintes ne sont qu'une information ;
   le client ne sort jamais vers le transporteur.
2. Seule une modification qui demande un nouveau prix monte la révision, et
   rend « à confirmer » les offres reçues avant elle.
3. Une offre redéposée sur la version à jour n'est plus à confirmer.
4. Les destinataires prévenus sont ceux qui ont réellement reçu la demande.
5. L'email de modification montre l'ancienne et la nouvelle valeur, et ne
   laisse jamais passer le client.
"""
import sqlite3
import sys

sys.path.insert(0, ".")

import database  # noqa: F401  (shim d'abord, cf. CLAUDE.md)
from app.services import expe_devis_revision as rev


def _migrer(c):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "m", "app/core/migrations/2026_10_20_expe_devis_revisions.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.appliquer(c)
    m.appliquer(c)  # rejouable


def _base():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        CREATE TABLE expe_demandes_devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT, code_postal_destination TEXT, type_envoi TEXT,
            poids_total_kg REAL, nb_palette REAL, type_palette TEXT,
            contraintes TEXT, statut TEXT DEFAULT 'ouverte', reference TEXT,
            date_limite TEXT, created_at TEXT
        );
        CREATE TABLE expe_devis_reponses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id INTEGER, nom_transporteur TEXT, destinataire_email TEXT,
            prix REAL, delai_jours INTEGER, statut TEXT, sent_at TEXT
        );
        INSERT INTO expe_demandes_devis
          (id, client, code_postal_destination, type_envoi, poids_total_kg, nb_palette,
           type_palette, contraintes, reference, created_at)
          VALUES (1, 'Client X', '69000', 'affretement', 1200, 4, 'europe', NULL,
                  'DT-2026-001', '2026-10-20T09:00:00');
        INSERT INTO expe_devis_reponses
          (demande_id, nom_transporteur, destinataire_email, prix, delai_jours, statut, sent_at)
        VALUES
          (1, 'A', 'a@trp.fr', 450, 2, 'recue', '2026-10-20T09:05:00'),
          (1, 'B', 'b@trp.fr', NULL, NULL, 'envoyee', '2026-10-20T09:05:00'),
          (1, 'C', 'c@trp.fr', NULL, NULL, 'sans_suite', '2026-10-20T09:05:00'),
          (1, 'D', 'd@trp.fr', NULL, NULL, 'echec', NULL),
          (1, 'E', 'e@trp.fr', NULL, NULL, 'envoyee', NULL);
        """
    )
    _migrer(c)
    return c


def _demande(c):
    return dict(c.execute("SELECT * FROM expe_demandes_devis WHERE id=1").fetchone())


def test_classement_des_champs():
    d = {"client": "X", "poids_total_kg": 1200.0, "contraintes": None, "code_postal_destination": "69000"}
    assert rev.classer(rev.changements(d, {"poids_total_kg": "1500"})) == rev.MODE_RECHIFFRAGE
    assert rev.classer(rev.changements(d, {"contraintes": "RDV 8h"})) == rev.MODE_INFORMATION
    assert rev.classer(rev.changements(d, {"client": "Y"})) == rev.MODE_INTERNE
    # Même valeur sous une autre écriture : pas un changement.
    assert rev.changements(d, {"poids_total_kg": "1200", "contraintes": "  ", "client": "X "}) == []
    # Le champ le plus fort l'emporte.
    chg = rev.changements(d, {"client": "Y", "contraintes": "RDV", "code_postal_destination": "75001"})
    assert rev.classer(chg) == rev.MODE_RECHIFFRAGE
    assert [c["champ"] for c in rev.visibles(chg)] == ["code_postal_destination", "contraintes"]


def test_rechiffrage_monte_la_revision_et_rend_les_offres_a_confirmer():
    c = _base()
    d = _demande(c)
    chg = rev.changements(d, {"poids_total_kg": 1500, "client": "Client Y"})
    res = rev.appliquer(c, demande=d, chg=chg, now="2026-10-20T10:00:00", email="x@sifa.pro")
    assert res["mode"] == rev.MODE_RECHIFFRAGE and res["revision"] == 1
    d2 = _demande(c)
    assert d2["poids_total_kg"] == 1500 and d2["client"] == "Client Y" and d2["revision"] == 1
    offre = dict(c.execute("SELECT * FROM expe_devis_reponses WHERE nom_transporteur='A'").fetchone())
    assert rev.offre_a_confirmer(offre, d2)
    # Le client ne figure pas dans ce que le transporteur verra.
    h = rev.historique(c, 1)
    assert len(h) == 1 and h[0]["rechiffrage"] is True
    assert [x["champ"] for x in h[0]["changements"]] == ["poids_total_kg"]
    assert h[0]["changements"][0]["avant"] == 1200.0


def test_information_ne_touche_pas_la_revision():
    c = _base()
    d = _demande(c)
    res = rev.appliquer(
        c, demande=d, chg=rev.changements(d, {"contraintes": "Hayon"}), now="t", email=None
    )
    assert res["mode"] == rev.MODE_INFORMATION and res["revision"] == 0
    d2 = _demande(c)
    offre = dict(c.execute("SELECT * FROM expe_devis_reponses WHERE nom_transporteur='A'").fetchone())
    assert not rev.offre_a_confirmer(offre, d2)
    assert rev.historique(c, 1)[0]["rechiffrage"] is False


def test_interne_ne_laisse_pas_de_trace_transporteur():
    c = _base()
    d = _demande(c)
    res = rev.appliquer(c, demande=d, chg=rev.changements(d, {"client": "Z"}), now="t", email=None)
    assert res["mode"] == rev.MODE_INTERNE and res["revision_id"] is None
    assert rev.historique(c, 1) == []


def test_offre_redeposee_n_est_plus_a_confirmer():
    c = _base()
    d = _demande(c)
    rev.appliquer(c, demande=d, chg=rev.changements(d, {"nb_palette": 6}), now="t", email=None)
    # Ce que font le portail et la saisie interne au dépôt d'un prix.
    c.execute(
        """UPDATE expe_devis_reponses SET prix=470,
             revision_offre=(SELECT COALESCE(revision,0) FROM expe_demandes_devis
                             WHERE id=expe_devis_reponses.demande_id)
           WHERE nom_transporteur='A'"""
    )
    offre = dict(c.execute("SELECT * FROM expe_devis_reponses WHERE nom_transporteur='A'").fetchone())
    assert not rev.offre_a_confirmer(offre, _demande(c))


def test_destinataires_prevenus():
    c = _base()
    noms = [r["nom_transporteur"] for r in rev.destinataires(c, 1)]
    # A a chiffré, B attend, C a décliné sur l'ancienne version : tous
    # prévenus. D (échec) et E (jamais parti) n'ont rien reçu.
    assert noms == ["A", "B", "C"]
    assert rev.deja_envoyee(c, 1)


def test_email_modification():
    from app.services.email_service import email_expe_rfq_transport

    demande = {
        "code_postal_destination": "69000", "type_envoi": "affretement",
        "poids_total_kg": 1500, "nb_palette": 4, "type_palette": "europe",
        "client": "Client confidentiel",
    }
    modif = {
        "mode": rev.MODE_RECHIFFRAGE,
        "changements": [{"champ": "poids_total_kg", "avant": 1200.0, "apres": 1500.0}],
    }
    sujet, corps = email_expe_rfq_transport(
        demande=demande, user={"nom": "Test"}, portail_lien="https://x/portail/expe/t",
        langue="fr", modification=modif,
    )
    assert sujet.startswith("Modification — ")
    # Séparateur de milliers : espace insécable, comme le reste des emails.
    assert "1\xa0200 kg" in corps and "1\xa0500 kg" in corps
    assert "confirmer ou de réviser" in corps
    assert "Client confidentiel" not in corps

    sujet_en, corps_en = email_expe_rfq_transport(
        demande=demande, user={"nom": "Test"}, portail_lien="https://x/portail/expe/t",
        langue="en", modification={"mode": rev.MODE_INFORMATION,
                                   "changements": [{"champ": "contraintes", "avant": None, "apres": "Tail lift"}]},
    )
    assert sujet_en.startswith("Update — ")
    assert "remains valid" in corps_en and "Tail lift" in corps_en

    sujet_bi, _ = email_expe_rfq_transport(
        demande=demande, user={"nom": "Test"}, portail_lien="https://x/portail/expe/t",
        langue=None, modification=modif,
    )
    assert sujet_bi.startswith("Modification / Update — ")


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_") and callable(f):
            f()
            print("ok", nom)
