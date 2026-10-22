"""
MyTools › Étiquettes — impression déclenchée par une saisie de production.

Une règle (`etiq_regles_auto`, éditée dans MyTools › Étiquettes › Impression
automatique, rôles admin imprimantes) dit : sur la machine <id>, quand le code
d'opération <code> est saisi (89 = fin de production, ou tout autre code de
operations.json, par exemple celui de la fin de bobine), imprimer le modèle
<id> — dans sa version APPROUVÉE — sur l'imprimante <id>, en N exemplaires.
Aucun nom de machine dans le code : la machine est un id de la table machines.

Point d'entrée : `apres_saisie(...)`, appelé par POST /api/fabrication/saisie
APRÈS l'enregistrement de la saisie, dans un try/except. Tout le travail
(lecture des règles, rendu, envoi réseau) part dans un fil séparé : la saisie
de l'opérateur ne l'attend jamais et n'échoue jamais à cause de lui.

Un échec est écrit dans le journal d'impression (statut « erreur », source
« auto ») et compté par le détecteur de notification « Impressions
automatiques en échec » (app/services/notifications.py), jusqu'à ce que
l'impression soit relancée depuis le journal.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Optional

log = logging.getLogger("mysifa.etiq_auto")


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def modele_approuve(conn, modele_id: int) -> dict:
    """Le modèle dans sa version approuvée. Lève ValueError (message lisible)
    si le modèle n'existe pas ou n'a aucune version approuvée."""
    # Référence : etiq_validation.modele_production (agent éditeur). Le repli
    # ci-dessous ne sert que si ce module manque (instance en retard).
    try:
        from app.services.etiq_validation import modele_production
    except ImportError:
        modele_production = None
    if modele_production is not None:
        try:
            m = modele_production(conn, modele_id)
        except Exception as e:  # EtiquetteInvalide : message lisible
            raise ValueError(str(e))
        return {k: m[k] for k in ("id", "nom", "largeur_mm", "hauteur_mm", "dpi", "layout", "version") if k in m}
    row = conn.execute("SELECT * FROM etiq_modeles WHERE id=?", (modele_id,)).fetchone()
    if not row or ("archive" in row.keys() and row["archive"]):
        raise ValueError(f"Modèle n°{modele_id} introuvable ou archivé.")
    cols = set(row.keys())
    nom = row["nom"]
    if "statut_validation" not in cols:          # base sans validation : version courante
        layout, l, h, dpi = row["layout_json"], row["largeur_mm"], row["hauteur_mm"], row["dpi"]
    else:
        va = row["version_approuvee"] if "version_approuvee" in cols else None
        if not va:
            raise ValueError(f"« {nom} » n'a aucune version approuvée : rien n'est imprimé en production.")
        if "version" in cols and int(row["version"] or 1) == int(va):
            layout, l, h, dpi = row["layout_json"], row["largeur_mm"], row["hauteur_mm"], row["dpi"]
        else:
            v = conn.execute("SELECT * FROM etiq_modeles_versions WHERE modele_id=? AND version=?",
                             (modele_id, va)).fetchone() if _colonnes(conn, "etiq_modeles_versions") else None
            if not v:
                raise ValueError(f"« {nom} » : version approuvée v{va} introuvable dans l'historique.")
            layout, l, h, dpi = v["layout_json"], v["largeur_mm"], v["hauteur_mm"], v["dpi"]
    try:
        layout = json.loads(layout or "{}")
    except ValueError:
        raise ValueError(f"« {nom} » : mise en page illisible.")
    return {"id": modele_id, "nom": nom, "largeur_mm": l, "hauteur_mm": h, "dpi": dpi, "layout": layout}


def donnees_saisie(conn, modele: dict, saisie: dict) -> dict:
    """Enregistrement de l'étiquette : champs de la saisie, puis variables
    « source » remplies depuis le dossier (etiq_sources)."""
    rec = {k: ("" if v is None else str(v)) for k, v in saisie.items()}
    no_dossier = saisie.get("dossier")
    if not no_dossier:
        return rec
    try:
        from app.services import etiq_sources
        pe = conn.execute("SELECT id FROM planning_entries WHERE reference=? ORDER BY id DESC LIMIT 1",
                          (no_dossier,)).fetchone()
        champs = etiq_sources.lire(conn, "dossier", pe["id"]) if pe else {}
    except Exception:
        champs = {}
    lay = modele.get("layout") or {}
    for v in lay.get("variables") or []:
        if v.get("type") == "source" and v.get("champ") in champs:
            rec[str(v.get("nom")).lower()] = champs[v["champ"]]
    for k, v in champs.items():
        rec.setdefault(k.replace(".", "_"), v)
    return rec


def regles_applicables(conn, machine_id: int, code: str, fin_dossier: bool) -> list:
    if not _colonnes(conn, "etiq_regles_auto"):
        return []
    rows = conn.execute("SELECT * FROM etiq_regles_auto WHERE actif=1 AND machine_id=? AND operation_code=?",
                        (machine_id, code)).fetchall()
    return [dict(r) for r in rows if fin_dossier or not r["fin_dossier_seulement"]]


def _utilisateur(conn, email: Optional[str], nom: str) -> dict:
    u = {"email": email or "", "nom": nom or "Impression automatique", "role": "fabrication"}
    if email:
        r = conn.execute("SELECT id,email,nom,role FROM users WHERE email=?", (email,)).fetchone()
        if r:
            u.update(dict(r))
    return u


def _journaliser_echec(conn, regle: dict, machine_nom: str, saisie: dict, user: dict, message: str,
                       modele_nom: str = "") -> None:
    from app.routers.etiq_impression import TABLE, _now
    if not _colonnes(conn, TABLE):
        return
    imp = conn.execute("SELECT nom FROM imprimantes WHERE id=?", (regle["imprimante_id"],)).fetchone()
    cur = conn.execute(
        f"INSERT INTO {TABLE} (created_at,created_by,created_by_nom,source,modele_id,modele_nom,imprimante_id,"
        "imprimante_nom,mode_envoi,etiquettes,exemplaires,resume,donnees_json,statut,erreur) "
        "VALUES (?,?,?,'auto',?,?,?,?,'auto',1,?,?,?,'erreur',?)",
        (_now(), user.get("email"), user.get("nom"), regle["modele_id"], modele_nom, regle["imprimante_id"],
         imp["nom"] if imp else "", regle.get("exemplaires") or 1, (f"Dossier {saisie.get('dossier') or '—'}")[:240],
         json.dumps({"enregistrements": [saisie], "valeurs": []}, ensure_ascii=False), message[:500]))
    if "origine" in _colonnes(conn, TABLE):
        conn.execute(f"UPDATE {TABLE} SET origine=? WHERE id=?",
                     (f"Saisie {saisie.get('operation_code')} · {machine_nom}"[:300], cur.lastrowid))
    conn.commit()


def executer(machine_id: int, machine_nom: str, code: str, fin_dossier: bool, saisie: dict,
             email: Optional[str], operateur: str) -> list:
    """Applique les règles de la machine pour ce code. Rend la liste des
    résultats (un par règle). Ne lève jamais."""
    from app.core.database import get_db
    from app.routers.etiq_impression import _executer, _lire_profil
    sortie = []
    try:
        with get_db() as conn:
            regles = regles_applicables(conn, machine_id, code, fin_dossier)
            user = _utilisateur(conn, email, operateur)
    except Exception as e:  # noqa: BLE001
        log.warning("Impression automatique : lecture des règles impossible (%s).", type(e).__name__)
        return sortie
    for regle in regles:
        modele_nom = ""
        try:
            with get_db() as conn:
                modele = modele_approuve(conn, regle["modele_id"])
                modele_nom = modele["nom"]
                p = _lire_profil(conn, regle["imprimante_id"])
                rec = donnees_saisie(conn, modele, saisie)
            r = _executer(user, None, p, None, modele=modele, enregistrements=[rec], valeurs=None,
                          copies=max(1, int(regle.get("exemplaires") or 1)), source="auto",
                          modele_id=regle["modele_id"], modele_nom=modele_nom,
                          origine=f"Saisie {code} · {machine_nom} · dossier {saisie.get('dossier') or '—'}")
            if r.get("mode") in ("fichier", "navigateur", "pdf"):
                # Personne n'est là pour récupérer un fichier : c'est un échec.
                with get_db() as conn:
                    conn.execute("UPDATE etiq_journal_impression SET statut='erreur', erreur=? WHERE id=?",
                                 ("Imprimante sans envoi direct (réseau ou agent) : rien n'est sorti.", r["journal_id"]))
                    conn.commit()
                r["statut"] = "erreur"
            sortie.append(r)
        except Exception as e:  # noqa: BLE001
            message = getattr(e, "detail", None) or str(e) or type(e).__name__
            try:
                with get_db() as conn:
                    _journaliser_echec(conn, regle, machine_nom, saisie, user, str(message), modele_nom)
            except Exception:
                pass
            sortie.append({"statut": "erreur", "erreur": str(message), "regle_id": regle["id"]})
    if any(r.get("statut") == "erreur" for r in sortie):
        try:
            from app.services.notifications import invalider_cache
            invalider_cache("tools.impressions_auto")
        except Exception:
            pass
    return sortie


def apres_saisie(*, machine_id, machine_nom: str, code: str, fin_dossier: bool, no_dossier: Optional[str],
                 operateur: str, email: Optional[str], saisie_id=None, quantite=None, metrage=None,
                 client: str = "", designation: str = "", synchrone: bool = False):
    """Crochet de POST /api/fabrication/saisie. Rend tout de suite (fil séparé)."""
    if not machine_id or not code:
        return None
    maintenant = datetime.now()
    saisie = {
        "dossier": no_dossier or "", "machine": machine_nom or "", "operateur": operateur or "",
        "operation_code": code, "saisie_id": saisie_id or "", "quantite": "" if quantite is None else quantite,
        "metrage": "" if metrage is None else metrage, "client": client or "", "designation": designation or "",
        "date": maintenant.strftime("%d/%m/%Y"), "heure": maintenant.strftime("%H:%M"),
    }
    args = (int(machine_id), machine_nom or "", str(code), bool(fin_dossier), saisie, email, operateur or "")
    if synchrone:
        return executer(*args)
    threading.Thread(target=executer, args=args, name="etiq-auto", daemon=True).start()
    return None
