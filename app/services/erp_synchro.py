"""Mise à jour du miroir RVGI à la demande.

Le serveur ne peut pas joindre RVGI (le VPS ne voit pas 192.168.100.x) : la
synchro est TOUJOURS un envoi du poste du réseau SIFA vers MySifa. Le bouton
« Mettre à jour maintenant » dépose donc une demande ; le poste la relève
(tâche planifiée toutes les deux minutes, `sync_rvgi.ps1 -SiDemande`), lance
une synchro complète, et la fin de l'import du miroir clôt la demande.

    en_attente  déposée, pas encore relevée par le poste
    prise       relevée : export et envoi en cours
    terminee    le miroir vient d'être reconstruit
    echec       l'import a échoué (le message dit pourquoi)

Une demande relevée qui n'aboutit pas (poste éteint en cours de route, envoi
refusé) ne bloque rien : passé `DELAI_SANS_REPONSE`, elle est dite « sans
réponse » et une nouvelle demande peut être déposée.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")
# Une synchro complète (export ~61 tables, zip, envoi, import) tient largement
# dans ce délai ; au-delà, le poste n'a pas fini et ne finira plus.
DELAI_SANS_REPONSE = timedelta(minutes=45)
# Une demande en attente que personne ne relève : le poste est éteint, ou la
# tâche de relève n'est pas installée. On le dit au lieu d'attendre en silence.
DELAI_NON_RELEVEE = timedelta(minutes=10)


def maintenant() -> datetime:
    return datetime.now(_PARIS).replace(tzinfo=None, microsecond=0)


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def _lire(v) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(v)[:19]) if v else None
    except ValueError:
        return None


def _table(conn) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='erp_synchro_demandes'").fetchone() is not None


def _ouverte(conn) -> Optional[Dict[str, Any]]:
    """La demande encore vivante (en attente, ou prise depuis moins du délai)."""
    r = conn.execute("""SELECT * FROM erp_synchro_demandes
                         WHERE statut IN ('en_attente','prise') ORDER BY id DESC LIMIT 1""").fetchone()
    if not r:
        return None
    d = dict(r)
    if d["statut"] == "prise" and (_lire(d["prise_le"]) or maintenant()) < maintenant() - DELAI_SANS_REPONSE:
        return None
    return d


def demander(conn, par: str) -> Dict[str, Any]:
    """Dépose une demande, ou rend celle déjà ouverte (deux clics = une synchro)."""
    ouverte = _ouverte(conn)
    if ouverte:
        return {"demande": ouverte, "nouvelle": False}
    # Les demandes abandonnées par le poste sont closes, pour que l'historique
    # dise ce qui s'est passé.
    conn.execute("""UPDATE erp_synchro_demandes SET statut='echec', fin_le=?,
                           message='Sans réponse du poste SIFA'
                     WHERE statut='prise'""", (_iso(maintenant()),))
    cur = conn.execute("INSERT INTO erp_synchro_demandes (demande_le, demande_par, statut) VALUES (?, ?, 'en_attente')",
                       (_iso(maintenant()), par))
    conn.commit()
    d = dict(conn.execute("SELECT * FROM erp_synchro_demandes WHERE id=?", (cur.lastrowid,)).fetchone())
    return {"demande": d, "nouvelle": True}


def prendre(conn) -> Optional[Dict[str, Any]]:
    """Le poste relève la demande en attente (et la marque prise), s'il y en a une."""
    if not _table(conn):
        return None
    r = conn.execute("SELECT * FROM erp_synchro_demandes WHERE statut='en_attente' ORDER BY id LIMIT 1").fetchone()
    if not r:
        return None
    prise_le = _iso(maintenant())
    conn.execute("UPDATE erp_synchro_demandes SET statut='prise', prise_le=? WHERE statut='en_attente'",
                 (prise_le,))
    conn.commit()
    return {**dict(r), "statut": "prise", "prise_le": prise_le}


def terminer(conn, ok: bool, message: str = "") -> int:
    """Fin de l'import du miroir : toute demande en cours est close.

    Un import qui arrive sans demande (passage horaire) clôt aussi une demande
    en attente : le miroir est à jour, le poste n'a plus rien à faire.
    """
    if not _table(conn):
        return 0
    n = conn.execute("""UPDATE erp_synchro_demandes SET statut=?, fin_le=?, message=?
                         WHERE statut IN ('en_attente','prise')""",
                     ("terminee" if ok else "echec", _iso(maintenant()), (message or "")[:300])).rowcount
    conn.commit()
    return n


def etat(conn, miroir_meta: Dict[str, Any], import_etat: Dict[str, Any]) -> Dict[str, Any]:
    """Ce que l'écran affiche : date des données, et où en est la dernière demande."""
    derniere = None
    if _table(conn):
        r = conn.execute("SELECT * FROM erp_synchro_demandes ORDER BY id DESC LIMIT 1").fetchone()
        derniere = dict(r) if r else None
    if derniere:
        now = maintenant()
        if derniere["statut"] == "en_attente" and (_lire(derniere["demande_le"]) or now) < now - DELAI_NON_RELEVEE:
            derniere["alerte"] = "Le poste SIFA n'a pas relevé la demande : il est peut-être éteint."
        if derniere["statut"] == "prise" and (_lire(derniere["prise_le"]) or now) < now - DELAI_SANS_REPONSE:
            derniere["statut"] = "echec"
            derniere["message"] = "Sans réponse du poste SIFA"
    return {
        "present": bool(miroir_meta.get("present")),
        "importe_le": miroir_meta.get("importe_le"),
        "releve_le": miroir_meta.get("releve_le"),
        "import": {k: import_etat.get(k) for k in ("statut", "debut", "fin") if k in import_etat},
        "demande": derniere,
    }
