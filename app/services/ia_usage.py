"""Usage de l'IA — enregistrement des appels à Claude et synthèse pour la direction.

Chaque fonction qui appelle Claude passe sa réponse à `noter()`. Si la route
a ouvert un `suivi(user, fonction)`, les appels s'additionnent sur une seule
ligne attribuée à l'utilisateur, écrite à la sortie du bloc. Sans suivi actif
(pont API, script), `noter()` écrit une ligne anonyme sur-le-champ.

Un échec d'enregistrement ne bloque jamais l'action de l'utilisateur.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from config import IA_CACHE_ECRITURE_FACTEUR, IA_CACHE_LECTURE_FACTEUR, ia_tarifs_modeles

_PARIS = ZoneInfo("Europe/Paris")

FONCTIONS = {
    "agent": "Assistant IA",
    "devis": "Lecture de devis",
    "fsc": "Lecture de certificat FSC",
    "tarif_transport": "Grille transporteur",
    "sql": "Requête DB Viewer",
}

_suivi_courant: ContextVar[Optional["Suivi"]] = ContextVar("ia_suivi_courant", default=None)


def _tarif(modele: str) -> tuple[float, float]:
    tarifs = ia_tarifs_modeles()
    meilleur = ""
    for prefixe in tarifs:
        if (modele or "").startswith(prefixe) and len(prefixe) > len(meilleur):
            meilleur = prefixe
    return tarifs.get(meilleur, (0.0, 0.0))


def cout_usd(modele: str, entree: int, sortie: int, cache_lecture: int = 0, cache_ecriture: int = 0) -> float:
    p_in, p_out = _tarif(modele)
    return (
        entree * p_in
        + sortie * p_out
        + cache_lecture * p_in * IA_CACHE_LECTURE_FACTEUR
        + cache_ecriture * p_in * IA_CACHE_ECRITURE_FACTEUR
    ) / 1_000_000


class Suivi:
    """Cumule les appels d'une action et l'enregistre à la sortie du bloc `with`."""

    def __init__(self, user: Optional[dict], fonction: str, module: str = ""):
        self.user = user or {}
        self.fonction = fonction
        self.module = module or ""
        self.modele = ""
        self.nb_appels = 0
        self.entree = self.sortie = self.cache_lecture = self.cache_ecriture = 0
        self.cout = 0.0
        self.statut = "ok"
        self._debut = time.monotonic()
        self._jeton = None

    def noter(self, reponse: Any) -> None:
        try:
            u = getattr(reponse, "usage", None)
            if u is None:
                return
            modele = getattr(reponse, "model", "") or self.modele
            e = int(getattr(u, "input_tokens", 0) or 0)
            s = int(getattr(u, "output_tokens", 0) or 0)
            cl = int(getattr(u, "cache_read_input_tokens", 0) or 0)
            ce = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
            self.modele = modele
            self.nb_appels += 1
            self.entree += e
            self.sortie += s
            self.cache_lecture += cl
            self.cache_ecriture += ce
            self.cout += cout_usd(modele, e, s, cl, ce)
        except Exception:
            pass

    def enregistrer(self) -> None:
        if not self.nb_appels:
            return
        try:
            from database import get_db

            u = self.user
            nom = u.get("nom") or u.get("email") or u.get("identifiant") or ""
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO ia_usage (cree_le, user_id, utilisateur, role, fonction, module,
                           modele, nb_appels, input_tokens, output_tokens, cache_lecture_tokens,
                           cache_ecriture_tokens, cout_usd, duree_ms, statut)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S"),
                        u.get("id"), nom, u.get("role") or "",
                        self.fonction, self.module, self.modele, self.nb_appels,
                        self.entree, self.sortie, self.cache_lecture, self.cache_ecriture,
                        round(self.cout, 6), int((time.monotonic() - self._debut) * 1000),
                        self.statut,
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def __enter__(self) -> "Suivi":
        self._jeton = _suivi_courant.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.statut = "err"
        if self._jeton is not None:
            _suivi_courant.reset(self._jeton)
        self.enregistrer()


def suivi(user: Optional[dict], fonction: str, module: str = "") -> Suivi:
    return Suivi(user, fonction, module)


def noter(reponse: Any, fonction: str) -> None:
    """À appeler juste après chaque `messages.create`."""
    s = _suivi_courant.get()
    if s is not None:
        s.noter(reponse)
        return
    seul = Suivi(None, fonction)
    seul.noter(reponse)
    seul.enregistrer()


# ─── Synthèse ──────────────────────────────────────────────────────

def synthese(conn, jours: int = 30) -> dict:
    jours = max(1, min(int(jours or 30), 366))
    debut = (datetime.now(_PARIS) - timedelta(days=jours - 1)).strftime("%Y-%m-%dT00:00:00")
    filtre = "WHERE cree_le >= ?"
    p = (debut,)

    def _lignes(sql: str) -> list[dict]:
        return [dict(r) for r in conn.execute(sql, p).fetchall()]

    agregats = """COUNT(*) AS actions, SUM(nb_appels) AS appels,
                  SUM(input_tokens + cache_lecture_tokens + cache_ecriture_tokens) AS tokens_entree,
                  SUM(output_tokens) AS tokens_sortie, SUM(cout_usd) AS cout_usd"""

    total = dict(conn.execute(f"SELECT {agregats}, COUNT(DISTINCT user_id) AS utilisateurs FROM ia_usage {filtre}", p).fetchone())
    par_utilisateur = _lignes(
        f"""SELECT user_id, MAX(utilisateur) AS utilisateur, MAX(role) AS role, {agregats},
                   MAX(cree_le) AS dernier
            FROM ia_usage {filtre}
            GROUP BY COALESCE(user_id, -1) ORDER BY cout_usd DESC"""
    )
    par_fonction = _lignes(
        f"SELECT fonction, {agregats} FROM ia_usage {filtre} GROUP BY fonction ORDER BY cout_usd DESC"
    )
    par_modele = _lignes(
        f"SELECT modele, {agregats} FROM ia_usage {filtre} GROUP BY modele ORDER BY cout_usd DESC"
    )
    par_jour = _lignes(
        f"""SELECT substr(cree_le, 1, 10) AS jour, {agregats}
            FROM ia_usage {filtre} GROUP BY jour ORDER BY jour"""
    )
    recents = [
        dict(r) for r in conn.execute(
            f"""SELECT cree_le, utilisateur, role, fonction, module, modele, nb_appels,
                       input_tokens + cache_lecture_tokens + cache_ecriture_tokens AS tokens_entree,
                       output_tokens AS tokens_sortie, cout_usd, duree_ms, statut
                FROM ia_usage {filtre} ORDER BY cree_le DESC, id DESC LIMIT 100""",
            p,
        ).fetchall()
    ]
    for ligne in par_fonction + recents:
        ligne["fonction_libelle"] = FONCTIONS.get(ligne.get("fonction"), ligne.get("fonction"))
    return {
        "jours": jours,
        "depuis": debut[:10],
        "total": total,
        "par_utilisateur": par_utilisateur,
        "par_fonction": par_fonction,
        "par_modele": par_modele,
        "par_jour": par_jour,
        "recents": recents,
    }
