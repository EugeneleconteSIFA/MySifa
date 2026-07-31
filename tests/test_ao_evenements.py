"""Tests du journal d'engagement MyAO (tracking d'ouverture email).

Trois regressions couvertes, toutes rencontrees en conditions reelles :

1. Un proxy de webmail (Gmail) est une VRAIE ouverture, pas un robot.
2. Un prechargement enregistre juste avant ne doit pas faire disparaitre
   l'ouverture humaine qui suit (la dedup porte aussi sur `fiable`).
3. La fenetre de prechargement se mesure sur le DERNIER email parti, pas sur
   `date_envoi` qui reste figee sur l'invitation.
"""
import sqlite3

from app.services.ao_evenements import (
    DEDUP_SECONDES,
    EV_EMAIL_ATTRIBUTION,
    EV_EMAIL_ENVOYE,
    EV_EMAIL_MESSAGE,
    EV_EMAIL_OUVERT,
    CANAL_EMAIL,
    classer_ouverture,
    date_email_reference,
    log_evenement,
)

UA_GMAIL = "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0 (via ggpht.com GoogleImageProxy)"
UA_OUTLOOK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/18"
UA_SCANNER = "Mozilla/5.0 (compatible; proofpoint-urldefense)"


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE ao_evenements (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               ao_fournisseur_id INTEGER NOT NULL,
               ao_id INTEGER,
               canal TEXT NOT NULL,
               type_evenement TEXT NOT NULL,
               date TEXT NOT NULL,
               fiable INTEGER DEFAULT 1,
               motif TEXT,
               user_agent TEXT,
               meta TEXT)"""
    )
    return c


# ─── classer_ouverture ────────────────────────────────────────────

def test_proxy_gmail_est_une_vraie_ouverture():
    fiable, motif = classer_ouverture(
        "2026-07-30T09:00:00", UA_GMAIL, "2026-07-30T11:30:00"
    )
    assert fiable is True
    assert "Gmail" in (motif or "")


def test_prechargement_prime_sur_le_proxy():
    fiable, motif = classer_ouverture(
        "2026-07-30T09:00:00", UA_GMAIL, "2026-07-30T09:00:05"
    )
    assert fiable is False
    assert "chargement" in (motif or "")


def test_scanner_antispam_ecarte():
    fiable, motif = classer_ouverture(
        "2026-07-30T09:00:00", UA_SCANNER, "2026-07-30T11:30:00"
    )
    assert fiable is False
    assert "robot" in (motif or "")


def test_ouverture_humaine_retenue_sans_motif():
    fiable, motif = classer_ouverture(
        "2026-07-30T09:00:00", UA_OUTLOOK, "2026-07-30T11:30:00"
    )
    assert (fiable, motif) == (True, None)


def test_sans_user_agent_ecarte_mais_non_concluant():
    fiable, motif = classer_ouverture("2026-07-30T09:00:00", "", "2026-07-30T11:30:00")
    assert fiable is False
    assert "non concluant" in (motif or "")


# ─── dedup ────────────────────────────────────────────────────────

def _ouverture(conn, date, fiable):
    return log_evenement(
        conn,
        ao_fournisseur_id=1,
        ao_id=7,
        canal=CANAL_EMAIL,
        type_evenement=EV_EMAIL_OUVERT,
        date=date,
        fiable=fiable,
        dedup_secondes=DEDUP_SECONDES,
    )


def test_prechargement_n_avale_pas_la_vraie_ouverture():
    c = _conn()
    assert _ouverture(c, "2026-07-30T09:00:02", False) is True
    # 40 s plus tard, le fournisseur ouvre reellement : dans la fenetre de
    # dedup, mais avec une fiabilite differente -> doit etre enregistre.
    assert _ouverture(c, "2026-07-30T09:00:42", True) is True
    n = c.execute(
        "SELECT COUNT(*) FROM ao_evenements WHERE fiable=1"
    ).fetchone()[0]
    assert n == 1


def test_deux_hits_identiques_rapproches_dedupliques():
    c = _conn()
    assert _ouverture(c, "2026-07-30T09:00:00", True) is True
    assert _ouverture(c, "2026-07-30T09:00:30", True) is False
    assert c.execute("SELECT COUNT(*) FROM ao_evenements").fetchone()[0] == 1


def test_hits_espaces_comptes_separement():
    c = _conn()
    assert _ouverture(c, "2026-07-30T09:00:00", True) is True
    assert _ouverture(c, "2026-07-30T09:05:00", True) is True
    assert c.execute("SELECT COUNT(*) FROM ao_evenements").fetchone()[0] == 2


# ─── date_email_reference ─────────────────────────────────────────

def _envoi(conn, type_ev, date):
    log_evenement(
        conn,
        ao_fournisseur_id=1,
        ao_id=7,
        canal=CANAL_EMAIL,
        type_evenement=type_ev,
        date=date,
    )


def test_reference_suit_le_contexte_demande():
    c = _conn()
    _envoi(c, EV_EMAIL_ENVOYE, "2026-07-01T08:00:00")
    _envoi(c, EV_EMAIL_MESSAGE, "2026-07-28T14:00:00")
    _envoi(c, EV_EMAIL_ATTRIBUTION, "2026-07-29T09:00:00")
    assert date_email_reference(c, 1, "msg") == "2026-07-28T14:00:00"
    assert date_email_reference(c, 1, "inv") == "2026-07-01T08:00:00"
    assert date_email_reference(c, 1, "attr") == "2026-07-29T09:00:00"


def test_reference_prend_le_plus_recent_si_contexte_inconnu():
    c = _conn()
    _envoi(c, EV_EMAIL_ENVOYE, "2026-07-01T08:00:00")
    _envoi(c, EV_EMAIL_MESSAGE, "2026-07-28T14:00:00")
    assert date_email_reference(c, 1, None) == "2026-07-28T14:00:00"


def test_reference_retombe_sur_date_envoi_si_aucun_evenement():
    c = _conn()
    assert date_email_reference(c, 1, "msg", "2026-07-01T08:00:00") == "2026-07-01T08:00:00"
    assert date_email_reference(c, 1, "msg", None) is None


def test_relance_protegee_du_prechargement():
    """Bout en bout : la relance beneficie enfin de la fenetre de 20 s."""
    c = _conn()
    _envoi(c, EV_EMAIL_ENVOYE, "2026-07-01T08:00:00")
    _envoi(c, EV_EMAIL_MESSAGE, "2026-07-28T14:00:00")
    ref = date_email_reference(c, 1, "msg", "2026-07-01T08:00:00")
    fiable, motif = classer_ouverture(ref, UA_OUTLOOK, "2026-07-28T14:00:04")
    assert fiable is False
    assert "chargement" in (motif or "")
