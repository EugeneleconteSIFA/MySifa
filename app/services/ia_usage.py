"""Usage de l'IA — enregistrement des appels à Claude et synthèse pour la direction.

Chaque fonction qui appelle Claude passe sa réponse à `noter()`. Si la route
a ouvert un `suivi(user, fonction)`, les appels s'additionnent sur une seule
ligne attribuée à l'utilisateur, écrite à la sortie du bloc. Sans suivi actif
(pont API, script), `noter()` écrit une ligne anonyme sur-le-champ.

Un échec d'enregistrement ne bloque jamais l'action de l'utilisateur.

D'où vient l'appel (application, écran, page, API) est lu sur la requête en
cours (`app/core/requete_courante.py`) : aucune route n'a à le transmettre.
Hors requête (boucle de fond), l'application vaut « Automatique ». Un service
qui connaît le modèle demandé ou les pièces jointes le précise avec
`preciser(modele_demande=…, fichiers=…)`.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from urllib.parse import parse_qs, urlsplit

from config import IA_CACHE_ECRITURE_FACTEUR, IA_CACHE_LECTURE_FACTEUR, ia_tarifs_modeles

_PARIS = ZoneInfo("Europe/Paris")

FONCTIONS = {
    "agent": "Assistant IA",
    "devis": "Lecture de devis",
    "fsc": "Lecture de certificat FSC",
    "tarif_transport": "Grille transporteur",
    "sql": "Requête DB Viewer",
    "memo_expe": "Mémo expédition",
    "emails_commandes": "Tri des e-mails commandes",
    "etiquettes": "Étiquettes spécifiques",
    "formulaires": "Création de formulaires",
    "alertes": "Alertes maintenance",
}

_suivi_courant: ContextVar[Optional["Suivi"]] = ContextVar("ia_suivi_courant", default=None)

# ─── Origine d'un appel ────────────────────────────────────────────

# Application d'une API appelée sans page connue (pont API, appel direct).
_APPLI_PAR_API = (
    ("/api/print", "MyTools"), ("/api/translate", "MyTools"),
    ("/api/qualite", "MyQualité"), ("/api/maintenance", "Maintenance"),
    ("/api/expe", "MyExpé"), ("/api/rentabilite", "MyProd"),
    ("/api/db", "Base de données"), ("/api/ai", "Assistant IA"),
)
# Paramètre d'adresse qui désigne l'écran, par page (url-etat.md : chaque appli
# garde le nom de clé déjà en usage dans ses liens).
_CLE_ECRAN = {"/tools": "outil", "/stock": "tab", "/prod": "page", "/qualite": "vue",
              "/expe": "onglet", "/planning": "vue", "/fabrication": "onglet", "/ao": "section"}
_SOUS_ECRAN = ("poste", "sous", "section")
_LIBELLES_ECRAN = {
    "etiquettes": "Étiquettes", "formulaires": "Formulaires", "pdf": "Éditeur PDF",
    "image": "Image", "calculs": "Calculs bobine", "traduction": "Traducteur",
    "specifiques": "Étiquettes spécifiques", "fsc": "FSC", "eudr": "EUDR",
    "rentabilite": "Rentabilité", "retour": "Retour de prod",
}


def _joli(v: str) -> str:
    v = (v or "").strip()
    return _LIBELLES_ECRAN.get(v) or (v.replace("-", " ").replace("_", " ")[:1].upper() + v.replace("-", " ").replace("_", " ")[1:])


def origine(page: str = "", api: str = "") -> tuple[str, str]:
    """(application, écran) lisibles d'un appel, d'après la page et l'API."""
    application, ecran = "", ""
    if page:
        u = urlsplit(page)
        chemin = u.path or "/"
        try:
            from app.services.boutons_flottants import APPLIS, appli_de_chemin
            code = appli_de_chemin(chemin)
            application = next((a.libelle for a in APPLIS if a.code == code), "") if code else ""
        except Exception:
            application = ""
        if chemin == "/tools":
            application = "MyTools"
        q = parse_qs(u.query)
        cle = _CLE_ECRAN.get(chemin)
        morceaux = []
        if cle and q.get(cle):
            morceaux.append(_joli(q[cle][0]))
        for k in _SOUS_ECRAN:
            if k != cle and q.get(k):
                morceaux.append(_joli(q[k][0]))
                break
        ecran = " › ".join(morceaux)
    if not application and api:
        application = next((lib for pref, lib in _APPLI_PAR_API if api.startswith(pref)), "")
    return application, ecran


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
        self.modele_demande = ""
        self.nb_fichiers = 0
        self.fin_raison = ""
        self.erreur = ""
        self._debut = time.monotonic()
        self._jeton = None
        try:
            from app.core.requete_courante import courante
            r = courante() or {}
        except Exception:
            r = {}
        self.page = r.get("page", "")
        self.api = r.get("api", "")
        self.application, self.ecran = origine(self.page, self.api)
        if not r:
            self.application = "Automatique"

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
            self.fin_raison = str(getattr(reponse, "stop_reason", "") or "")[:40]
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
                           cache_ecriture_tokens, cout_usd, duree_ms, statut,
                           application, ecran, page, api, modele_demande, nb_fichiers,
                           fin_raison, erreur)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S"),
                        u.get("id"), nom, u.get("role") or "",
                        self.fonction, self.module, self.modele, self.nb_appels,
                        self.entree, self.sortie, self.cache_lecture, self.cache_ecriture,
                        round(self.cout, 6), int((time.monotonic() - self._debut) * 1000),
                        self.statut,
                        self.application or None, self.ecran or None, self.page or None,
                        self.api or None, self.modele_demande or None, int(self.nb_fichiers or 0),
                        self.fin_raison or None, self.erreur or None,
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
            # Message lisible : le `detail` d'une HTTPException, sinon le texte.
            detail = getattr(exc, "detail", None)
            self.erreur = str(detail if detail is not None else exc)[:300]
        if self._jeton is not None:
            _suivi_courant.reset(self._jeton)
        self.enregistrer()


def suivi(user: Optional[dict], fonction: str, module: str = "") -> Suivi:
    return Suivi(user, fonction, module)


def preciser(modele_demande: Optional[str] = None, fichiers: Optional[int] = None) -> None:
    """Complète le suivi en cours : modèle choisi, nombre de pièces envoyées."""
    s = _suivi_courant.get()
    if s is None:
        return
    if modele_demande:
        s.modele_demande = str(modele_demande)[:80]
    if fichiers is not None:
        s.nb_fichiers = int(fichiers or 0)


def noter(reponse: Any, fonction: str) -> None:
    """À appeler juste après chaque `messages.create`."""
    s = _suivi_courant.get()
    if s is not None:
        s.noter(reponse)
        return
    seul = Suivi({"nom": "Automatique"}, fonction)
    seul.noter(reponse)
    seul.enregistrer()


# ─── Synthèse ──────────────────────────────────────────────────────

FILTRES = ("utilisateur", "fonction", "application", "modele", "statut")


def taux_usd_eur(conn) -> float:
    """Le taux du réglage Coûts matières (mc_setting.eur_usd_rate : 1 $ = x €)."""
    try:
        r = conn.execute("SELECT value_decimal FROM mc_setting WHERE key='eur_usd_rate'").fetchone()
        v = float(r[0]) if r and r[0] else 0.0
        return v if 0 < v < 10 else 0.85
    except Exception:
        return 0.85


def _ou(jours: int, filtres: Optional[dict]) -> tuple[str, list]:
    debut = (datetime.now(_PARIS) - timedelta(days=jours - 1)).strftime("%Y-%m-%dT00:00:00")
    clauses, params = ["cree_le >= ?"], [debut]
    f = filtres or {}
    if f.get("utilisateur") not in (None, ""):
        v = str(f["utilisateur"])
        if v == "auto":
            clauses.append("user_id IS NULL")
        elif v.isdigit():
            clauses.append("user_id = ?"); params.append(int(v))
    if f.get("fonction"):
        clauses.append("fonction = ?"); params.append(str(f["fonction"]))
    if "application" in f and f["application"] is not None:
        clauses.append("COALESCE(application, '') = ?"); params.append(str(f["application"]))
    if f.get("modele"):
        clauses.append("modele = ?"); params.append(str(f["modele"]))
    if f.get("statut") in ("ok", "err"):
        clauses.append("COALESCE(statut, 'ok') = ?"); params.append(f["statut"])
    return "WHERE " + " AND ".join(clauses), params


def synthese(conn, jours: int = 30, filtres: Optional[dict] = None) -> dict:
    jours = max(1, min(int(jours or 30), 366))
    filtre, p = _ou(jours, filtres)
    p = tuple(p)

    def _lignes(sql: str, params=p) -> list[dict]:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]

    agregats = """COUNT(*) AS actions, SUM(nb_appels) AS appels,
                  SUM(input_tokens + cache_lecture_tokens + cache_ecriture_tokens) AS tokens_entree,
                  SUM(output_tokens) AS tokens_sortie, SUM(cout_usd) AS cout_usd,
                  SUM(CASE WHEN statut = 'err' THEN 1 ELSE 0 END) AS echecs,
                  AVG(duree_ms) AS duree_moyenne"""

    total = dict(conn.execute(f"SELECT {agregats}, COUNT(DISTINCT user_id) AS utilisateurs FROM ia_usage {filtre}", p).fetchone())
    par_utilisateur = _lignes(
        f"""SELECT user_id, MAX(utilisateur) AS utilisateur, MAX(role) AS role, {agregats},
                   MAX(cree_le) AS dernier
            FROM ia_usage {filtre}
            GROUP BY COALESCE(user_id, -1) ORDER BY cout_usd DESC"""
    )
    par_application = _lignes(
        f"""SELECT COALESCE(application, '') AS application, {agregats}
            FROM ia_usage {filtre} GROUP BY COALESCE(application, '') ORDER BY cout_usd DESC"""
    )
    par_ecran = _lignes(
        f"""SELECT COALESCE(application, '') AS application, COALESCE(ecran, '') AS ecran, {agregats}
            FROM ia_usage {filtre} GROUP BY 1, 2 ORDER BY cout_usd DESC LIMIT 30"""
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
    recents = _lignes(
        f"""SELECT id, cree_le, user_id, utilisateur, role, fonction, module, modele, modele_demande,
                   nb_appels, input_tokens + cache_lecture_tokens + cache_ecriture_tokens AS tokens_entree,
                   output_tokens AS tokens_sortie, cout_usd, duree_ms, statut,
                   application, ecran, nb_fichiers, fin_raison, erreur
            FROM ia_usage {filtre} ORDER BY cree_le DESC, id DESC LIMIT 200"""
    )
    for ligne in par_fonction + recents:
        ligne["fonction_libelle"] = FONCTIONS.get(ligne.get("fonction"), ligne.get("fonction"))

    # Valeurs proposées dans les filtres : toute la période, filtres ignorés,
    # pour qu'un filtre posé n'efface pas les autres choix.
    f0, p0 = _ou(jours, None)
    p0 = tuple(p0)
    options = {
        "utilisateurs": _lignes(
            f"""SELECT COALESCE(CAST(user_id AS TEXT), 'auto') AS valeur, MAX(utilisateur) AS libelle
                FROM ia_usage {f0} GROUP BY COALESCE(user_id, -1) ORDER BY libelle""", p0),
        "fonctions": [{"valeur": r["fonction"], "libelle": FONCTIONS.get(r["fonction"], r["fonction"])}
                      for r in _lignes(f"SELECT DISTINCT fonction FROM ia_usage {f0} ORDER BY fonction", p0)],
        "applications": [{"valeur": r["application"], "libelle": r["application"] or "Non renseignée"}
                         for r in _lignes(f"SELECT DISTINCT COALESCE(application, '') AS application FROM ia_usage {f0} ORDER BY 1", p0)],
        "modeles": [{"valeur": r["modele"], "libelle": r["modele"]}
                    for r in _lignes(f"SELECT DISTINCT modele FROM ia_usage {f0} AND modele IS NOT NULL AND modele <> '' ORDER BY modele", p0)],
    }
    return {
        "jours": jours,
        "depuis": p[0][:10],
        "taux_usd_eur": taux_usd_eur(conn),
        "filtres": {k: (filtres or {}).get(k) or "" for k in FILTRES},
        "total": total,
        "par_utilisateur": par_utilisateur,
        "par_application": par_application,
        "par_ecran": par_ecran,
        "par_fonction": par_fonction,
        "par_modele": par_modele,
        "par_jour": par_jour,
        "recents": recents,
        "options": options,
    }


def detail(conn, appel_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM ia_usage WHERE id = ?", (int(appel_id),)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["fonction_libelle"] = FONCTIONS.get(d.get("fonction"), d.get("fonction"))
    d["taux_usd_eur"] = taux_usd_eur(conn)
    # Coût décomposé, mêmes tarifs que l'enregistrement.
    p_in, p_out = _tarif(d.get("modele") or "")
    d["cout_detail"] = {
        "entree": (d.get("input_tokens") or 0) * p_in / 1_000_000,
        "sortie": (d.get("output_tokens") or 0) * p_out / 1_000_000,
        "cache_lecture": (d.get("cache_lecture_tokens") or 0) * p_in * IA_CACHE_LECTURE_FACTEUR / 1_000_000,
        "cache_ecriture": (d.get("cache_ecriture_tokens") or 0) * p_in * IA_CACHE_ECRITURE_FACTEUR / 1_000_000,
    }
    d["repli"] = bool(d.get("modele_demande") and d.get("modele") and not str(d["modele"]).startswith(str(d["modele_demande"])))
    return d
