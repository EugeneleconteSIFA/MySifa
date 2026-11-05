"""
Réunions — mode écoute : enregistrement, cycle de vie, validation du brief.

Service pur : il prend une connexion sqlite et un dossier de travail, rien
d'autre. La transcription elle-même (faster-whisper) vit dans
`transcription.py`, la proposition de brief (Claude) dans
`reunion_ecoute_ia.py`, l'enchaînement dans `tools/transcription_worker.py`.

Cycle d'une écoute (`statut`) :

    enregistrement → a_transcrire → transcription → a_structurer → proposition → validee
                                                  ↘ (type sans IA) ↗
    et à tout moment : erreur, abandonnee

L'audio arrive en morceaux numérotés (MediaRecorder, 30 s chacun). Un morceau
seul n'est pas lisible — seul le premier porte l'en-tête du conteneur — mais
leur concaténation dans l'ordre l'est : c'est ce que fait `assembler()`.
Un morceau manquant est SIGNALÉ (`morceaux_manquants`), jamais masqué : le
brief dira qu'un passage de la réunion n'a pas été entendu.

L'audio ne va jamais en base, et il est supprimé dès que la transcription est
faite. La transcription est purgée `ECOUTE_RETENTION_JOURS` après validation.

Une écoute n'est visible que de la personne qui l'a lancée (et du
superadmin) tant qu'elle n'est pas validée : la transcription brute d'une
réunion de direction n'a pas à circuler. Une fois validée, c'est la réunion
qu'elle a produite, avec sa propre visibilité, qui fait foi.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services import reunion as rn

ENREGISTREMENT = "enregistrement"
A_TRANSCRIRE = "a_transcrire"
TRANSCRIPTION = "transcription"
A_STRUCTURER = "a_structurer"
PROPOSITION = "proposition"
VALIDEE = "validee"
ERREUR = "erreur"
ABANDONNEE = "abandonnee"

STATUTS = {
    ENREGISTREMENT: "Enregistrement en cours",
    A_TRANSCRIRE: "En attente de transcription",
    TRANSCRIPTION: "Transcription en cours",
    A_STRUCTURER: "Brief en préparation",
    PROPOSITION: "Brief à valider",
    VALIDEE: "Validé",
    ERREUR: "Erreur",
    ABANDONNEE: "Abandonné",
}
# Ce qui attend encore quelque chose du serveur.
EN_TRAITEMENT = (A_TRANSCRIRE, TRANSCRIPTION, A_STRUCTURER)
TENTATIVES_MAX = 3

_MIMES = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
}


def _txt(v: Any) -> str:
    return ("" if v is None else str(v)).strip()


def _now(quand: Optional[datetime] = None) -> str:
    return (quand or datetime.now()).isoformat(timespec="seconds")


def _date(s: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(_txt(s)[:19])
    except ValueError:
        return None


def mime_propre(mime: str) -> str:
    """« audio/webm;codecs=opus » -> « audio/webm » ; inconnu -> ''."""
    base = _txt(mime).split(";", 1)[0].lower()
    return base if base in _MIMES else ""


def extension(mime: str) -> str:
    return _MIMES.get(mime_propre(mime), "webm")


def dossier(base: str, ecoute_id: int) -> str:
    return os.path.join(base, str(int(ecoute_id)))


def _morceaux_presents(base: str, ecoute_id: int) -> List[int]:
    d = dossier(base, ecoute_id)
    if not os.path.isdir(d):
        return []
    nums = []
    for f in os.listdir(d):
        m = re.fullmatch(r"(\d{5})\.part", f)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def _effacer_audio(base: str, ecoute_id: int) -> None:
    shutil.rmtree(dossier(base, ecoute_id), ignore_errors=True)


# ─── Lecture ─────────────────────────────────────────────────────────────────

def _ecoute(conn, row) -> Dict[str, Any]:
    d = dict(row)
    d["statut_libelle"] = STATUTS.get(d.get("statut"), d.get("statut"))
    try:
        d["proposition"] = json.loads(d["proposition"]) if d.get("proposition") else None
    except ValueError:
        d["proposition"] = None
    d["morceaux_manquants"] = [int(x) for x in _txt(d.get("morceaux_manquants")).split(",") if x.strip().isdigit()]
    t = rn.type_reunion(conn, d.get("type_id"))
    d["type"] = {"id": t["id"], "libelle": t["libelle"], "chiffres_prod": t["chiffres_prod"],
                 "structuration_ia": t["structuration_ia"]} if t else None
    return d


def ecoute(conn, ecoute_id: int, avec_texte: bool = True) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM reunion_ecoutes WHERE id=?", (int(ecoute_id),)).fetchone()
    if not row:
        return None
    d = _ecoute(conn, row)
    if not avec_texte:
        d.pop("transcription", None)
    return d


def visible(e: Dict[str, Any], qui: Optional[Dict[str, Any]]) -> bool:
    if qui is None or qui.get("superadmin"):
        return True
    if e.get("demarre_par_id") not in (None, "") and qui.get("id") is not None:
        return str(e["demarre_par_id"]) == str(qui["id"])
    return _txt(e.get("demarre_par")).lower() == _txt(qui.get("nom")).lower() != ""


def liste_de(conn, qui: Dict[str, Any], limite: int = 30) -> List[Dict[str, Any]]:
    """Les écoutes de cette personne qui ne sont pas encore validées ni
    abandonnées, plus les dernières validées : ce qu'elle a en cours."""
    rows = conn.execute(
        """SELECT * FROM reunion_ecoutes
            WHERE statut NOT IN (?, ?) OR valide_le >= ?
            ORDER BY id DESC LIMIT 200""",
        (VALIDEE, ABANDONNEE, _now(datetime.now() - timedelta(days=7))),
    ).fetchall()
    out = []
    for r in rows:
        d = _ecoute(conn, r)
        if not visible(d, qui):
            continue
        d.pop("transcription", None)
        out.append(d)
        if len(out) >= limite:
            break
    return out


def en_cours_de(conn, qui: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """L'écoute encore en enregistrement de cette personne : la page la
    reprend plutôt que d'en ouvrir une seconde."""
    rows = conn.execute(
        "SELECT * FROM reunion_ecoutes WHERE statut=? ORDER BY id DESC", (ENREGISTREMENT,)
    ).fetchall()
    # La sienne seulement, superadmin compris : reprendre l'écoute d'un autre
    # mêlerait deux réunions dans un même enregistrement.
    for r in rows:
        d = _ecoute(conn, r)
        if visible(d, dict(qui, superadmin=False)):
            d.pop("transcription", None)
            return d
    return None


# ─── Enregistrement ──────────────────────────────────────────────────────────

def creer(conn, auteur: str, auteur_id: Optional[int], type_id: Optional[int] = None,
          titre: str = "", reunion_id: Optional[int] = None) -> Dict[str, Any]:
    t = rn.type_reunion(conn, type_id)
    now = _now()
    cur = conn.execute(
        """INSERT INTO reunion_ecoutes (statut, reunion_id, type_id, titre, demarre_le,
               demarre_par, demarre_par_id, maj_le)
           VALUES (?,?,?,?,?,?,?,?)""",
        (ENREGISTREMENT, int(reunion_id) if reunion_id else None, t["id"] if t else None,
         _txt(titre)[:200], now, _txt(auteur), auteur_id, now),
    )
    conn.commit()
    return ecoute(conn, cur.lastrowid)


def ajouter_morceau(conn, base: str, ecoute_id: int, numero: int, donnees: bytes,
                    mime: str = "", max_octets: int = 8 * 1024 * 1024) -> Dict[str, Any]:
    """Range le morceau `numero` (0, 1, 2…). Rejouable : un morceau renvoyé
    après une coupure réseau remplace le précédent du même numéro.

    Lève ValueError (message affichable) si l'écoute n'accepte plus de morceau.
    """
    e = ecoute(conn, ecoute_id, avec_texte=False)
    if not e:
        raise ValueError("Écoute introuvable.")
    if e["statut"] != ENREGISTREMENT:
        raise ValueError("Écoute déjà arrêtée — ce morceau n'est plus attendu.")
    if numero < 0 or numero > 99999:
        raise ValueError("Numéro de morceau invalide.")
    if not donnees:
        raise ValueError("Morceau vide.")
    if len(donnees) > max_octets:
        raise ValueError(f"Morceau trop lourd — {max_octets // (1024 * 1024)} Mo au plus.")
    d = dossier(base, ecoute_id)
    os.makedirs(d, exist_ok=True)
    final = os.path.join(d, f"{int(numero):05d}.part")
    tmp = final + ".tmp"
    with open(tmp, "wb") as f:
        f.write(donnees)
    os.replace(tmp, final)
    presents = _morceaux_presents(base, ecoute_id)
    taille = sum(os.path.getsize(os.path.join(d, f"{n:05d}.part")) for n in presents)
    conn.execute(
        """UPDATE reunion_ecoutes SET nb_morceaux=?, taille_octets=?, dernier_morceau_le=?,
               mime=CASE WHEN mime='' THEN ? ELSE mime END, maj_le=? WHERE id=?""",
        (len(presents), taille, _now(), mime_propre(mime), _now(), int(ecoute_id)),
    )
    conn.commit()
    return {"numero": int(numero), "recus": len(presents), "taille_octets": taille}


def arreter(conn, base: str, ecoute_id: int, nb_annonces: Optional[int] = None,
            duree_s: Optional[float] = None, type_id: Optional[int] = None,
            titre: Optional[str] = None, reunion_id: Optional[int] = None) -> Dict[str, Any]:
    """Fin de l'enregistrement. Ce qui est arrivé part en transcription ; une
    écoute sans aucun morceau est abandonnée. Les trous sont notés."""
    e = ecoute(conn, ecoute_id, avec_texte=False)
    if not e:
        raise ValueError("Écoute introuvable.")
    champs, valeurs = [], []
    if type_id not in (None, "") and rn.type_reunion(conn, type_id):
        champs.append("type_id=?"); valeurs.append(int(type_id))
    if titre is not None:
        champs.append("titre=?"); valeurs.append(_txt(titre)[:200])
    if reunion_id not in (None, ""):
        champs.append("reunion_id=?"); valeurs.append(int(reunion_id))
    if e["statut"] == ENREGISTREMENT:
        presents = _morceaux_presents(base, ecoute_id)
        attendus = int(nb_annonces) if nb_annonces not in (None, "") else (max(presents) + 1 if presents else 0)
        manquants = [n for n in range(attendus) if n not in set(presents)]
        statut = A_TRANSCRIRE if presents else ABANDONNEE
        champs += ["statut=?", "arrete_le=?", "nb_annonces=?", "morceaux_manquants=?"]
        valeurs += [statut, _now(), attendus, ",".join(str(n) for n in manquants)]
        if duree_s not in (None, ""):
            champs.append("duree_s=?"); valeurs.append(float(duree_s))
        if not presents:
            champs.append("erreur=?"); valeurs.append("Aucun son reçu par le serveur.")
    if champs:
        champs.append("maj_le=?"); valeurs.append(_now())
        conn.execute(f"UPDATE reunion_ecoutes SET {', '.join(champs)} WHERE id=?",
                     valeurs + [int(ecoute_id)])
        conn.commit()
    if e["statut"] == ENREGISTREMENT and not _morceaux_presents(base, ecoute_id):
        _effacer_audio(base, ecoute_id)
    return ecoute(conn, ecoute_id, avec_texte=False)


def abandonner(conn, base: str, ecoute_id: int) -> Dict[str, Any]:
    """Abandon volontaire : l'audio et la transcription sont effacés."""
    if not ecoute(conn, ecoute_id, avec_texte=False):
        raise ValueError("Écoute introuvable.")
    _effacer_audio(base, ecoute_id)
    conn.execute(
        """UPDATE reunion_ecoutes SET statut=?, transcription=NULL, proposition=NULL,
               maj_le=? WHERE id=? AND statut<>?""",
        (ABANDONNEE, _now(), int(ecoute_id), VALIDEE),
    )
    conn.commit()
    return ecoute(conn, ecoute_id, avec_texte=False)


def relancer(conn, ecoute_id: int) -> Dict[str, Any]:
    """Après une erreur : repart de l'étape qui a échoué."""
    e = ecoute(conn, ecoute_id, avec_texte=True)
    if not e:
        raise ValueError("Écoute introuvable.")
    if e["statut"] != ERREUR:
        raise ValueError("Seule une écoute en erreur se relance.")
    statut = A_STRUCTURER if e.get("transcription") else A_TRANSCRIRE
    conn.execute(
        "UPDATE reunion_ecoutes SET statut=?, erreur=NULL, tentatives=0, maj_le=? WHERE id=?",
        (statut, _now(), int(ecoute_id)),
    )
    conn.commit()
    return ecoute(conn, ecoute_id, avec_texte=False)


def clore_silencieuses(conn, base: str, silence_min: int,
                       maintenant: Optional[datetime] = None) -> int:
    """Une écoute qui ne reçoit plus rien (onglet fermé, téléphone éteint) est
    arrêtée d'office : ce qui est arrivé part en transcription."""
    limite = (maintenant or datetime.now()) - timedelta(minutes=silence_min)
    rows = conn.execute(
        "SELECT id, dernier_morceau_le, demarre_le FROM reunion_ecoutes WHERE statut=?",
        (ENREGISTREMENT,),
    ).fetchall()
    n = 0
    for r in rows:
        dernier = _date(r["dernier_morceau_le"] or r["demarre_le"])
        if dernier and dernier < limite:
            arreter(conn, base, r["id"])
            n += 1
    return n


# ─── Traitement (appelé par le worker) ──────────────────────────────────────

def travail_en_attente(conn, silence_min: int, maintenant: Optional[datetime] = None) -> bool:
    """Lecture légère pour la boucle de main.py : faut-il lancer le worker ?"""
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='reunion_ecoutes'").fetchone() is None:
        return False
    if conn.execute(
        "SELECT 1 FROM reunion_ecoutes WHERE statut IN (?, ?, ?) LIMIT 1",
        (A_TRANSCRIRE, A_STRUCTURER, TRANSCRIPTION),
    ).fetchone():
        return True
    limite = _now((maintenant or datetime.now()) - timedelta(minutes=silence_min))
    return conn.execute(
        """SELECT 1 FROM reunion_ecoutes
            WHERE statut=? AND COALESCE(dernier_morceau_le, demarre_le) < ? LIMIT 1""",
        (ENREGISTREMENT, limite),
    ).fetchone() is not None


def a_traiter(conn) -> Optional[Dict[str, Any]]:
    """La prochaine écoute qui attend le serveur, la plus ancienne d'abord."""
    row = conn.execute(
        "SELECT id FROM reunion_ecoutes WHERE statut IN (?, ?) ORDER BY id LIMIT 1",
        (A_TRANSCRIRE, A_STRUCTURER),
    ).fetchone()
    return ecoute(conn, row["id"]) if row else None


def reprendre_interrompues(conn) -> int:
    """Appelé verrou pris : une écoute restée « transcription » vient d'un
    traitement tué en route (redémarrage du service). Elle repart, trois fois
    au plus."""
    rows = conn.execute(
        "SELECT id, tentatives FROM reunion_ecoutes WHERE statut=?", (TRANSCRIPTION,)
    ).fetchall()
    for r in rows:
        if int(r["tentatives"] or 0) >= TENTATIVES_MAX:
            echec(conn, r["id"], "Transcription interrompue trois fois — relancer à la main.")
        else:
            conn.execute("UPDATE reunion_ecoutes SET statut=?, maj_le=? WHERE id=?",
                         (A_TRANSCRIRE, _now(), r["id"]))
    conn.commit()
    return len(rows)


def debut_transcription(conn, ecoute_id: int, modele: str) -> None:
    conn.execute(
        """UPDATE reunion_ecoutes SET statut=?, modele=?, transcription_debut=?, progression=0,
               tentatives=tentatives+1, maj_le=? WHERE id=?""",
        (TRANSCRIPTION, _txt(modele), _now(), _now(), int(ecoute_id)),
    )
    conn.commit()


def poser_progression(conn, ecoute_id: int, fraction: float) -> None:
    """Part de l'audio déjà transcrite (0 à 1), écrite par le worker."""
    conn.execute("UPDATE reunion_ecoutes SET progression=? WHERE id=? AND statut=?",
                 (round(max(0.0, min(1.0, float(fraction))), 3), int(ecoute_id), TRANSCRIPTION))
    conn.commit()


def assembler(base: str, ecoute_id: int, mime: str = "") -> Optional[str]:
    """Concatène les morceaux reçus, dans l'ordre, en un fichier lisible."""
    presents = _morceaux_presents(base, ecoute_id)
    if not presents:
        return None
    d = dossier(base, ecoute_id)
    sortie = os.path.join(d, "reunion." + extension(mime))
    with open(sortie, "wb") as out:
        for n in presents:
            with open(os.path.join(d, f"{n:05d}.part"), "rb") as f:
                shutil.copyfileobj(f, out)
    return sortie


def poser_transcription(conn, base: str, ecoute_id: int, texte: str,
                        duree_traitement_s: float, duree_audio_s: Optional[float] = None) -> Dict[str, Any]:
    """La transcription est faite : l'audio disparaît. L'écoute passe à la
    structuration, ou directement à la proposition si son type s'en passe."""
    e = ecoute(conn, ecoute_id, avec_texte=False)
    if not e:
        raise ValueError("Écoute introuvable.")
    avec_ia = bool(e.get("type") and e["type"]["structuration_ia"]) if e.get("type") else True
    statut = A_STRUCTURER if avec_ia and _txt(texte) else PROPOSITION
    conn.execute(
        """UPDATE reunion_ecoutes SET statut=?, transcription=?, transcrit_le=?, progression=1,
               duree_traitement_s=?, duree_s=COALESCE(?, duree_s), erreur=NULL,
               tentatives=0, maj_le=? WHERE id=?""",
        (statut, texte or "", _now(), round(float(duree_traitement_s or 0), 1),
         duree_audio_s, _now(), int(ecoute_id)),
    )
    conn.commit()
    _effacer_audio(base, ecoute_id)
    return ecoute(conn, ecoute_id, avec_texte=False)


def poser_proposition(conn, ecoute_id: int, proposition: Dict[str, Any]) -> Dict[str, Any]:
    conn.execute(
        """UPDATE reunion_ecoutes SET statut=?, proposition=?, structure_le=?, erreur=NULL,
               tentatives=0, maj_le=? WHERE id=?""",
        (PROPOSITION, json.dumps(proposition, ensure_ascii=False), _now(), _now(), int(ecoute_id)),
    )
    conn.commit()
    return ecoute(conn, ecoute_id, avec_texte=False)


def echec(conn, ecoute_id: int, message: str) -> None:
    conn.execute(
        "UPDATE reunion_ecoutes SET statut=?, erreur=?, maj_le=? WHERE id=?",
        (ERREUR, _txt(message)[:500], _now(), int(ecoute_id)),
    )
    conn.commit()


def purger(conn, base: str, retention_jours: int,
           maintenant: Optional[datetime] = None) -> Dict[str, int]:
    """Transcriptions échues effacées ; audio d'une écoute en erreur depuis
    24 h ou abandonnée effacé. Rien d'autre."""
    now = maintenant or datetime.now()
    cur = conn.execute(
        """UPDATE reunion_ecoutes SET transcription=NULL, maj_le=?
            WHERE purge_le IS NOT NULL AND purge_le <= ? AND transcription IS NOT NULL""",
        (_now(now), _now(now)),
    )
    textes = cur.rowcount
    audios = 0
    rows = conn.execute(
        "SELECT id, statut, maj_le FROM reunion_ecoutes WHERE statut IN (?, ?, ?)",
        (ERREUR, ABANDONNEE, VALIDEE),
    ).fetchall()
    for r in rows:
        maj = _date(r["maj_le"])
        if r["statut"] == ERREUR and maj and maj > now - timedelta(hours=24):
            continue
        if os.path.isdir(dossier(base, r["id"])):
            _effacer_audio(base, r["id"])
            audios += 1
    conn.commit()
    return {"transcriptions": textes, "audios": audios}


# ─── Validation du brief ─────────────────────────────────────────────────────

def _lignes(v: Any) -> List[str]:
    if isinstance(v, (list, tuple)):
        brut = [str(x) for x in v]
    else:
        brut = _txt(v).splitlines()
    out = []
    for l in brut:
        l = re.sub(r"^\s*[-•·*]\s*", "", l).strip()
        if l:
            out.append(l)
    return out


def _puces(lignes: List[str]) -> str:
    return "\n".join("- " + l for l in lignes)


def valider(conn, ecoute_id: int, brief: Dict[str, Any], auteur: str,
            auteur_id: Optional[int], retention_jours: int,
            jour: Optional[str] = None) -> Dict[str, Any]:
    """Écrit le brief relu dans les réunions. Rend {ecoute, reunion}.

    `brief` : titre, type_id, notes (texte), decisions (liste ou texte),
    participants (noms), actions [{texte, responsable, echeance}],
    visibilite, roles_visibles, reunion_id (rattacher à une réunion
    existante au lieu d'en créer une).

    Rattachée, la réunion garde ses notes et décisions : celles du brief s'y
    ajoutent à la suite. Une action sans texte est ignorée.
    """
    e = ecoute(conn, ecoute_id, avec_texte=False)
    if not e:
        raise ValueError("Écoute introuvable.")
    if e["statut"] == VALIDEE:
        raise ValueError("Ce brief est déjà validé.")
    if e["statut"] != PROPOSITION:
        raise ValueError("Le brief n'est pas encore prêt.")

    notes = str(brief.get("notes") or "").strip()
    decisions = _puces(_lignes(brief.get("decisions")))
    noms = [p for p in _lignes(brief.get("participants"))]
    actions = [a for a in (brief.get("actions") or []) if isinstance(a, dict) and _txt(a.get("texte"))]
    reunion_id = brief.get("reunion_id") or e.get("reunion_id")
    jour = _txt(jour)[:10] or _txt(e.get("demarre_le"))[:10]

    if reunion_id:
        r = rn.reunion(conn, int(reunion_id))
        if not r:
            raise ValueError("Réunion de rattachement introuvable.")
        existants = [p["nom"] for p in r.get("participants") or []]
        rn.enregistrer(
            conn, r["id"], auteur,
            notes=(_txt(r.get("notes")) + ("\n\n" if _txt(r.get("notes")) and notes else "") + notes),
            decisions=(_txt(r.get("decisions")) + ("\n" if _txt(r.get("decisions")) and decisions else "") + decisions),
            noms_participants=existants + [n for n in noms if n.lower() not in {x.lower() for x in existants}],
        )
        rid = r["id"]
    else:
        r = rn.lancer(
            conn, auteur, jour, jour, titre=_txt(brief.get("titre")) or _txt(e.get("titre")),
            noms_participants=noms, type_id=brief.get("type_id") or e.get("type_id"),
            visibilite=brief.get("visibilite"),
            roles_visibles=brief.get("roles_visibles"),
            auteur_id=auteur_id, reprendre=False, notes=notes, decisions=decisions,
            statut=rn.STATUT_CLOSE,
        )
        if not r:
            raise ValueError("Réunion non créée.")
        rid = r["id"]
    for a in actions:
        rn.ajouter_action(conn, rid, _txt(a.get("texte")), _txt(a.get("responsable")),
                          _txt(a.get("echeance")))
    purge = _now(datetime.now() + timedelta(days=max(0, int(retention_jours))))
    conn.execute(
        """UPDATE reunion_ecoutes SET statut=?, reunion_id=?, valide_le=?, valide_par=?,
               purge_le=?, maj_le=? WHERE id=?""",
        (VALIDEE, rid, _now(), _txt(auteur), purge, _now(), int(ecoute_id)),
    )
    conn.commit()
    return {"ecoute": ecoute(conn, ecoute_id, avec_texte=False), "reunion": rn.reunion(conn, rid)}


def brief_vide(e: Dict[str, Any]) -> Dict[str, Any]:
    """Le brief proposé quand Claude n'intervient pas (type sans IA) : la
    transcription brute, à mettre en forme à la main."""
    return {"titre": _txt(e.get("titre")), "resume": "", "notes": "", "decisions": [],
            "actions": [], "participants": [], "points_ouverts": []}
