"""MyExpé — les signaux d'engagement qui viennent de CHEZ NOUS ne comptent pas.

Régression réelle (août 2026) : le créateur d'une demande de tarif est en
copie de l'email envoyé au transporteur. Son client de messagerie charge donc
le même pixel, et sa relecture faisait grimper « Email ouvert ×6 » sur des
transporteurs qui n'avaient rien ouvert. Pire côté portail : cliquer sur le
lien depuis la copie faisait basculer la ligne en « Ouverte », c'est-à-dire
affirmait noir sur blanc que le transporteur avait consulté la demande.

Ce que ce fichier verrouille :

1. Un hit venu d'une IP interne est ENREGISTRÉ mais pas COMPTÉ, sous un motif
   distinct des préchargements Apple/antispam — les deux ne se corrigent pas
   de la même façon.
2. Le reclassement manuel existe et fonctionne dans les deux sens : le filtre
   IP ne voit pas les lectures faites sur Outlook Web ou sur mobile, qui
   arrivent par les serveurs Microsoft.
3. Ce reclassement ne s'applique qu'aux ouvertures d'email — le reste des
   événements est émis par nous et n'a rien à reclasser.
"""
import sqlite3
import sys

sys.path.insert(0, ".")

import config
from app.services import expe_evenements as ev


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE expe_devis_reponses (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               demande_id INTEGER,
               statut TEXT,
               destinataire_email TEXT,
               sent_at TEXT,
               token_pixel TEXT
           )"""
    )
    c.execute(
        """CREATE TABLE expe_devis_evenements (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               reponse_id INTEGER NOT NULL,
               demande_id INTEGER,
               canal TEXT NOT NULL,
               type_evenement TEXT NOT NULL,
               date TEXT NOT NULL,
               fiable INTEGER NOT NULL DEFAULT 1,
               motif TEXT,
               user_agent TEXT,
               ip TEXT,
               meta TEXT
           )"""
    )
    c.execute(
        "INSERT INTO expe_devis_reponses (id, demande_id, statut, destinataire_email, sent_at)"
        " VALUES (1, 7, 'envoyee', 'contact@transporteur.fr', '2026-08-26T09:00:00')"
    )
    c.commit()
    return c


def test_est_ip_interne():
    ancien = config.EXPE_IPS_INTERNES
    try:
        config.EXPE_IPS_INTERNES = "92.154.13., 51.75.20.9"
        assert ev.est_ip_interne("92.154.13.4"), "préfixe terminé par un point"
        assert ev.est_ip_interne("92.154.13.201")
        assert ev.est_ip_interne("51.75.20.9"), "IP exacte"
        assert not ev.est_ip_interne("92.154.130.4"), "le point évite de mordre sur 130"
        assert not ev.est_ip_interne("8.8.8.8")
        assert not ev.est_ip_interne(""), "IP absente n'est pas interne"
        assert not ev.est_ip_interne(None)
        # Liste vide : personne n'est interne. Le défaut ne doit surtout pas
        # écarter des ouvertures transporteur sur une instance non configurée.
        config.EXPE_IPS_INTERNES = ""
        assert not ev.est_ip_interne("92.154.13.4")
    finally:
        config.EXPE_IPS_INTERNES = ancien


def test_ouverture_interne_hors_compteur():
    conn = _conn()
    # Deux vraies ouvertures du transporteur, trois relectures internes.
    for i, quand in enumerate(("2026-08-26T10:00:00", "2026-08-26T14:00:00")):
        ev.log_evenement(
            conn,
            reponse_id=1,
            demande_id=7,
            canal=ev.CANAL_EMAIL,
            type_evenement=ev.EV_EMAIL_OUVERT,
            date=quand,
            ip="8.8.8.%d" % i,
        )
    for i in range(3):
        ev.log_evenement(
            conn,
            reponse_id=1,
            demande_id=7,
            canal=ev.CANAL_EMAIL,
            type_evenement=ev.EV_EMAIL_OUVERT,
            date="2026-08-26T11:0%d:00" % i,
            fiable=False,
            motif=ev.MOTIF_INTERNE,
            ip="92.154.13.4",
        )
    # Et un préchargement, qui doit rester dans SON compteur à lui.
    ev.log_evenement(
        conn,
        reponse_id=1,
        demande_id=7,
        canal=ev.CANAL_EMAIL,
        type_evenement=ev.EV_EMAIL_OUVERT,
        date="2026-08-26T09:00:05",
        fiable=False,
        motif="préchargement",
    )
    conn.commit()

    r = ev.resume_par_reponse(conn, 7)[1]
    assert r["nb_ouvertures_email"] == 2, r
    assert r["ouvertures_internes"] == 3, r
    assert r["ouvertures_ecartees"] == 1, r
    # Le motif affiché est celui d'un vrai doute technique, pas « c'était
    # nous » : sinon la ligne conseille de relancer pour une raison fausse.
    assert r["motif_ecarte"] == "préchargement", r
    # Rien n'est supprimé : les six hits sont toujours en base.
    assert conn.execute("SELECT COUNT(*) FROM expe_devis_evenements").fetchone()[0] == 6


def test_marquer_interne_aller_retour():
    conn = _conn()
    ev.log_evenement(
        conn,
        reponse_id=1,
        demande_id=7,
        canal=ev.CANAL_EMAIL,
        type_evenement=ev.EV_EMAIL_OUVERT,
        date="2026-08-26T10:00:00",
        ip="52.100.0.1",  # Outlook Web : le filtre IP ne peut rien voir
    )
    conn.commit()
    eid = conn.execute("SELECT id FROM expe_devis_evenements").fetchone()["id"]

    assert ev.resume_par_reponse(conn, 7)[1]["nb_ouvertures_email"] == 1

    assert ev.marquer_interne(conn, eid) is True
    conn.commit()
    r = ev.resume_par_reponse(conn, 7)[1]
    assert r["nb_ouvertures_email"] == 0, r
    assert r["ouvertures_internes"] == 1, r

    # Réversible : un clic de trop ne doit pas effacer une vraie ouverture.
    assert ev.marquer_interne(conn, eid, interne=False) is True
    conn.commit()
    assert ev.resume_par_reponse(conn, 7)[1]["nb_ouvertures_email"] == 1

    # Et l'événement reste lisible dans la timeline avec son IP.
    tl = ev.timeline(conn, 1)
    assert len(tl) == 1 and tl[0]["ip"] == "52.100.0.1", tl


def test_marquer_interne_ne_blanchit_pas_un_prechargement():
    """Un hit deja ecarte pour une autre raison n'est pas reclassable.

    Sinon l'aller-retour « C'etait nous » puis « Finalement non » remettait
    `fiable=1, motif=NULL` : un prechargement Apple ressortait en ouverture
    certaine, et le motif d'origine etait perdu au passage.
    """
    conn = _conn()
    ev.log_evenement(
        conn,
        reponse_id=1,
        demande_id=7,
        canal=ev.CANAL_EMAIL,
        type_evenement=ev.EV_EMAIL_OUVERT,
        date="2026-08-26T09:00:03",
        fiable=False,
        motif="préchargement",
    )
    conn.commit()
    eid = conn.execute("SELECT id FROM expe_devis_evenements").fetchone()["id"]
    assert ev.marquer_interne(conn, eid) is False
    row = conn.execute(
        "SELECT fiable, motif FROM expe_devis_evenements WHERE id=?", (eid,)
    ).fetchone()
    assert row["motif"] == "préchargement" and row["fiable"] == 0, dict(row)
    r = ev.resume_par_reponse(conn, 7)[1]
    assert r["nb_ouvertures_email"] == 0 and r["ouvertures_internes"] == 0, r


def test_marquer_interne_refuse_les_autres_evenements():
    conn = _conn()
    ev.log_evenement(
        conn,
        reponse_id=1,
        demande_id=7,
        canal=ev.CANAL_PORTAIL,
        type_evenement=ev.EV_PORTAIL_OUVERT,
        date="2026-08-26T10:00:00",
    )
    conn.commit()
    eid = conn.execute("SELECT id FROM expe_devis_evenements").fetchone()["id"]
    # Une visite du portail se reconnaît toute seule (session MySifa) : elle
    # n'est jamais journalisée quand elle vient de nous, donc rien à annuler.
    assert ev.marquer_interne(conn, eid) is False
    assert ev.marquer_interne(conn, 999999) is False
    assert ev.resume_par_reponse(conn, 7)[1]["nb_visites_portail"] == 1


if __name__ == "__main__":
    test_est_ip_interne()
    test_ouverture_interne_hors_compteur()
    test_marquer_interne_aller_retour()
    test_marquer_interne_ne_blanchit_pas_un_prechargement()
    test_marquer_interne_refuse_les_autres_evenements()
    print("[MySifa] test_expe_devis_engagement : 5 tests OK.")
