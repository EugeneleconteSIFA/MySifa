"""
MyExpé — mémo expédition du matin.

Chaque jour ouvré, à l'heure réglée dans MyExpé › Pilotage, un mémo part vers
le service expédition : ce qui part aujourd'hui, les affrètements et
messageries à réserver, les retards, et les affrètements des jours suivants
pour anticiper.

Partage des rôles, et il ne doit pas bouger :
  - les listes et les chiffres viennent de `expe_pilotage.construire_tableau`,
    le même calcul que l'écran de pilotage ;
  - le modèle ne rédige que le paragraphe « À retenir ». Il reçoit les listes
    déjà calculées et n'a le droit que de les hiérarchiser. Sans clé API ou en
    cas d'échec, le mémo part sans ce paragraphe — jamais bloqué pour ça.
"""

import json
import re
from datetime import date, datetime, timedelta
from html import escape
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.services import expe_pilotage as pil
from app.services import ia_usage

PARIS = ZoneInfo("Europe/Paris")

TABLE_REGLAGES = "expe_memo_reglages"
TABLE_MEMOS = "expe_memos"

# Combien de jours ouvrés à l'avance on montre les affrètements à venir.
JOURS_ANTICIPATION = 7
# Une fois l'heure passée, combien de temps on accepte encore d'envoyer le
# mémo automatique (redémarrage du serveur, panne réseau). Au-delà, un mémo
# « du matin » qui arrive l'après-midi trompe plus qu'il n'aide.
FENETRE_RATTRAPAGE_H = 3
# Tentatives automatiques par jour avant d'abandonner (échec d'envoi).
MAX_TENTATIVES = 3

_RE_HEURE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_RE_EMAIL = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"]


def maintenant() -> datetime:
    return datetime.now(PARIS).replace(tzinfo=None)


# ─── Réglages ────────────────────────────────────────────────────────────────

def decouper_emails(texte: Any) -> List[str]:
    if isinstance(texte, list):
        morceaux = [str(x) for x in texte]
    else:
        morceaux = re.split(r"[\s,;]+", str(texte or ""))
    out: List[str] = []
    for m in morceaux:
        m = m.strip().lower()
        if m and m not in out:
            out.append(m)
    return out


def charger_reglages(conn) -> Dict[str, Any]:
    vals = {"actif": "0", "heure": "06:00", "destinataires": ""}
    try:
        for r in conn.execute(f"SELECT cle, valeur FROM {TABLE_REGLAGES}").fetchall():
            vals[r["cle"]] = r["valeur"]
    except Exception:
        pass
    heure = vals["heure"] if _RE_HEURE.match(str(vals["heure"])) else "06:00"
    return {
        "actif": str(vals["actif"]) == "1",
        "heure": heure,
        "destinataires": decouper_emails(vals["destinataires"]),
    }


def _ecrire(conn, cle: str, valeur: str) -> None:
    conn.execute(
        f"INSERT INTO {TABLE_REGLAGES} (cle, valeur) VALUES (?,?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (cle, valeur),
    )


def enregistrer_reglages(conn, valeurs: Dict[str, Any]) -> Dict[str, Any]:
    """Écrit les réglages fournis, valide le tout, et relit."""
    actuels = charger_reglages(conn)
    heure = actuels["heure"]
    if "heure" in valeurs:
        heure = str(valeurs["heure"] or "").strip()
        if not _RE_HEURE.match(heure):
            raise ValueError("Heure invalide — format attendu HH:MM.")
    emails = actuels["destinataires"]
    if "destinataires" in valeurs:
        emails = decouper_emails(valeurs["destinataires"])
        mauvais = [e for e in emails if not _RE_EMAIL.match(e)]
        if mauvais:
            raise ValueError("Adresse invalide : " + ", ".join(mauvais) + ".")
    actif = actuels["actif"]
    if "actif" in valeurs:
        actif = valeurs["actif"] in (True, 1, "1", "true")
    if actif and not emails:
        raise ValueError("Ajouter au moins un destinataire avant d'activer l'envoi.")
    _ecrire(conn, "heure", heure)
    _ecrire(conn, "destinataires", ", ".join(emails))
    _ecrire(conn, "actif", "1" if actif else "0")
    conn.commit()
    return charger_reglages(conn)


# ─── Sélection ───────────────────────────────────────────────────────────────

def _jour_ouvre_suivant(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def selectionner(tableau: dict, today: date) -> Dict[str, List[dict]]:
    """Range les envois du tableau de pilotage dans les rubriques du mémo.

    Un envoi n'apparaît que dans une rubrique, la plus urgente.
    """
    iso = today.isoformat()
    limite = _jour_ouvre_suivant(today, JOURS_ANTICIPATION).isoformat()
    # Le vendredi, le « jour même » couvre aussi le week-end : un enlèvement
    # du samedi se prépare la veille.
    fin_jour = (today + timedelta(days=2)).isoformat() if today.weekday() == 4 else iso

    rub: Dict[str, List[dict]] = {
        "retard": [], "aujourdhui": [], "affretement_a_reserver": [],
        "messagerie_a_reserver": [], "affretement_a_venir": [],
    }
    for e in tableau.get("envois", []):
        if e["alerte"] == "parti":
            continue
        transport_fait = e["jalons"]["transport"]["fait"]
        dc = e.get("date_cible") or ""
        if e["alerte"] == "retard":
            rub["retard"].append(e)
        elif dc and iso <= dc <= fin_jour:
            rub["aujourdhui"].append(e)
        elif not transport_fait and e["alerte"] in ("urgent", "a_commander"):
            cle = ("affretement_a_reserver" if e["type_envoi"] == "affretement"
                   else "messagerie_a_reserver")
            rub[cle].append(e)
        elif e["type_envoi"] == "affretement" and dc and dc <= limite:
            rub["affretement_a_venir"].append(e)
    return rub


# ─── Rédaction ───────────────────────────────────────────────────────────────

def _jour_fr(iso: Optional[str], avec_annee: bool = False) -> str:
    if not iso:
        return "sans date"
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    s = f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]}"
    return s + f" {d.year}" if avec_annee else s


def _palettes(e: dict) -> str:
    n = e.get("nb_palette")
    if n is None:
        return "pal. ?"
    txt = f"{n:g} pal."
    return txt + " (est.)" if e.get("nb_palette_source") == "estime" else txt


def _ligne(e: dict) -> Dict[str, Any]:
    """Version compacte d'un envoi, pour le modèle comme pour le HTML."""
    t = e["jalons"]["transport"]
    return {
        "date": e.get("date_cible"),
        "client": e.get("client") or "",
        "destination": " ".join(x for x in [e.get("code_postal") or "", e.get("ville") or ""] if x),
        "palettes": _palettes(e),
        "type": e.get("type_envoi"),
        "transport": (t.get("transporteur") or "commandé") if t["fait"] else "à réserver",
        "a_reserver_le": e.get("a_commander_le"),
        "prod_prete": bool(e.get("prod_prete")),
        "prod_apres_expedition": bool(e.get("prod_apres_expedition")),
        "dossiers": [d.get("reference") or "" for d in e.get("dossiers", []) if d.get("reference")],
    }


_RUBRIQUES = [
    ("retard", "En retard", "Date d'expédition dépassée, envoi non parti."),
    ("aujourdhui", "Départs du jour", None),
    ("affretement_a_reserver", "Affrètements à réserver", "Préavis atteint, aucun transport commandé."),
    ("messagerie_a_reserver", "Messageries à programmer", None),
    ("affretement_a_venir", "Affrètements à venir", f"Sur les {JOURS_ANTICIPATION} prochains jours ouvrés."),
]

_TD = "padding:7px 8px;border-bottom:1px solid #e2e8f0;font-size:13px;vertical-align:top;color:#0f172a"
_TH = ("padding:6px 8px;border-bottom:1px solid #cbd5e1;font-size:10px;text-transform:uppercase;"
       "letter-spacing:.4px;color:#64748b;text-align:left")
_PETIT = "font-size:11px;color:#64748b"


def _table_html(envois: List[dict]) -> str:
    lignes = []
    for e in envois:
        l = _ligne(e)
        if l["prod_prete"]:
            prod = ""
        elif l["prod_apres_expedition"]:
            prod = '<div style="font-size:11px;color:#b45309">Production après la date visée</div>'
        else:
            prod = f'<div style="{_PETIT}">Production en cours</div>'
        sous = escape(l["destination"])
        if l["dossiers"]:
            sous += " · " + escape(", ".join(l["dossiers"]))
        lignes.append(
            "<tr>"
            f'<td style="{_TD};white-space:nowrap">{escape(_jour_fr(l["date"]))}</td>'
            f'<td style="{_TD}"><strong>{escape(l["client"])}</strong>'
            f'<div style="{_PETIT}">{sous}</div>{prod}</td>'
            f'<td style="{_TD};white-space:nowrap">{escape(l["palettes"])}'
            f'<div style="{_PETIT}">{escape(l["type"] or "")}</div></td>'
            f'<td style="{_TD}">{escape(l["transport"])}</td>'
            "</tr>"
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        'style="border-collapse:collapse;margin:0 0 6px">'
        f'<tr><th style="{_TH}">Départ</th><th style="{_TH}">Envoi</th>'
        f'<th style="{_TH}">Palettes</th><th style="{_TH}">Transport</th></tr>'
        + "".join(lignes) + "</table>"
    )


def points_a_retenir(rub: Dict[str, List[dict]], today: date) -> List[str]:
    """Trois à cinq points rédigés par le modèle. Liste vide si indisponible."""
    if not any(rub.values()):
        return []
    try:
        from config import EXPE_MEMO_MODELE
        from app.services.devis_extraction import _client_anthropic

        client = _client_anthropic()
        if client is None:
            return []
        donnees = {k: [_ligne(e) for e in v] for k, v in rub.items()}
        consigne = (
            "Tu prépares le mémo du matin du service expédition d'un fabricant "
            "d'étiquettes. Voici les envois déjà triés par rubrique (JSON). "
            f"Nous sommes le {_jour_fr(today.isoformat(), True)}.\n\n"
            "Rédige 3 à 5 points d'attention, du plus urgent au moins urgent : "
            "transports à réserver aujourd'hui, regroupements possibles vers une "
            "même destination, départs dont la production n'est pas prête, "
            "palettes non estimées. Une phrase courte par point, ton factuel et "
            "direct, en français, sans emoji ni formule de politesse. "
            "N'invente aucun chiffre, client ou date absent des données. "
            "Réponds uniquement par les points, un par ligne, sans puce.\n\n"
            + json.dumps(donnees, ensure_ascii=False)
        )
        rep = client.messages.create(
            model=EXPE_MEMO_MODELE,
            max_tokens=600,
            messages=[{"role": "user", "content": consigne}],
        )
        ia_usage.noter(rep, "memo_expe")
        texte = "".join(b.text for b in rep.content if getattr(b, "type", "") == "text")
    except Exception as e:
        print(f"[MySifa] mémo expé : points d'attention indisponibles ({e})")
        return []
    points = [re.sub(r"^[\s\-•·*\d.)]+", "", l).strip() for l in texte.splitlines()]
    return [p for p in points if p][:5]


def construire_memo(conn, today: Optional[date] = None, avec_ia: bool = True) -> Dict[str, Any]:
    """Sujet + HTML du mémo. Ne fait que lire."""
    from app.services.email_service import email_mysifa_layout, public_base_url

    today = today or maintenant().date()
    tableau = pil.construire_tableau(conn, today)
    rub = selectionner(tableau, today)
    points = points_a_retenir(rub, today) if avec_ia else []

    n_resa = len(rub["affretement_a_reserver"]) + len(rub["messagerie_a_reserver"])
    sujet = (f"Mémo expédition · {_jour_fr(today.isoformat())} · "
             f"{len(rub['aujourdhui'])} départ(s), {n_resa} à réserver")
    if rub["retard"]:
        sujet += f", {len(rub['retard'])} en retard"

    corps = [f'<p style="margin:0 0 18px;font-size:15px;color:#0f172a"><strong>'
             f'{escape(_jour_fr(today.isoformat(), True).capitalize())}</strong></p>']
    if points:
        corps.append(
            '<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;'
            'padding:12px 16px;margin:0 0 22px"><div style="font-size:11px;font-weight:700;'
            'text-transform:uppercase;letter-spacing:.5px;color:#0369a1;margin-bottom:6px">'
            'À retenir</div><ul style="margin:0;padding-left:18px">'
            + "".join(f'<li style="margin:3px 0">{escape(p)}</li>' for p in points)
            + "</ul></div>")
    for cle, titre, aide in _RUBRIQUES:
        envois = rub[cle]
        if not envois and cle in ("retard", "affretement_a_venir"):
            continue
        corps.append(f'<h3 style="margin:22px 0 4px;font-size:14px;color:#0f172a">{escape(titre)} '
                     f'<span style="color:#64748b;font-weight:400">· {len(envois)}</span></h3>')
        if aide:
            corps.append(f'<div style="font-size:12px;color:#64748b;margin-bottom:6px">{escape(aide)}</div>')
        corps.append(_table_html(envois) if envois
                     else '<div style="font-size:13px;color:#64748b">Rien.</div>')
    r = tableau.get("resume", {})
    notes = []
    if r.get("sans_estimation"):
        notes.append(f"{r['sans_estimation']} envoi(s) sans estimation de palettes.")
    if not tableau.get("rvgi", {}).get("present", True):
        notes.append("Miroir RVGI indisponible : dates et adresses incomplètes.")
    if notes:
        corps.append('<p style="margin:18px 0 0;font-size:12px;color:#64748b">'
                     + " ".join(escape(n) for n in notes) + "</p>")

    html = email_mysifa_layout(
        subtitle="Mémo expédition du matin",
        body_html="".join(corps),
        cta_href=public_base_url().rstrip("/") + "/expe",
        cta_label="Ouvrir le pilotage",
    )
    return {"sujet": sujet, "html": html, "points": points,
            "rubriques": {k: len(v) for k, v in rub.items()}}


# ─── Envoi ───────────────────────────────────────────────────────────────────

def envoyer(conn, destinataires: List[str], declencheur: str) -> Dict[str, Any]:
    """Construit, envoie et archive le mémo. `declencheur` : auto | manuel."""
    from config import EXPE_MEMO_FROM
    from app.services.email_service import send_email

    if not destinataires:
        raise ValueError("Aucun destinataire.")
    now = maintenant()
    memo = construire_memo(conn, now.date())
    ok = send_email(destinataires, memo["sujet"], memo["html"], from_upn=EXPE_MEMO_FROM)
    conn.execute(
        f"INSERT INTO {TABLE_MEMOS} "
        "(jour, cree_le, declencheur, destinataires, sujet, html, envoye, erreur) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (now.date().isoformat(), now.isoformat(timespec="seconds"), declencheur,
         ", ".join(destinataires), memo["sujet"], memo["html"], 1 if ok else 0,
         None if ok else "Envoi refusé par le serveur de messagerie."),
    )
    conn.commit()
    return {"envoye": ok, "sujet": memo["sujet"], "rubriques": memo["rubriques"]}


def doit_partir(conn, now: datetime) -> bool:
    """Le mémo automatique est-il dû maintenant ?"""
    reg = charger_reglages(conn)
    if not reg["actif"] or not reg["destinataires"] or now.weekday() >= 5:
        return False
    h, m = (int(x) for x in reg["heure"].split(":"))
    debut = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if not (debut <= now < debut + timedelta(hours=FENETRE_RATTRAPAGE_H)):
        return False
    rows = conn.execute(
        f"SELECT envoye FROM {TABLE_MEMOS} WHERE jour = ? AND declencheur = 'auto'",
        (now.date().isoformat(),),
    ).fetchall()
    if any(r["envoye"] for r in rows):
        return False
    return len(rows) < MAX_TENTATIVES


def tour_automatique(get_db) -> Optional[Dict[str, Any]]:
    """Appelé chaque minute par la boucle de `main.py`."""
    with get_db() as conn:
        if not doit_partir(conn, maintenant()):
            return None
        return envoyer(conn, charger_reglages(conn)["destinataires"], "auto")


def historique(conn, limite: int = 10) -> List[Dict[str, Any]]:
    try:
        rows = conn.execute(
            "SELECT id, jour, cree_le, declencheur, destinataires, sujet, envoye, erreur "
            f"FROM {TABLE_MEMOS} ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def html_archive(conn, memo_id: int) -> Optional[str]:
    row = conn.execute(f"SELECT html FROM {TABLE_MEMOS} WHERE id = ?", (memo_id,)).fetchone()
    return row["html"] if row else None
