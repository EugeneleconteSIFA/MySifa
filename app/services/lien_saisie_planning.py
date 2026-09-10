"""
Lien explicite entre une saisie de production et SON créneau du planning.

Pourquoi (10/09/2026). Une saisie ne connaissait son dossier que par le texte
`no_dossier`, recherché à chaque lecture dans `planning_entries` par référence.
Tant qu'un dossier n'a qu'un créneau, ça tient. Dès qu'il en a plusieurs — un
reliquat, un dossier dupliqué, un second créneau recréé après une annulation —
personne ne sait plus quelle saisie appartient à quel passage : l'annulation
modifiait le mauvais créneau, et remettre un dossier « non annulé » obligeait
à dupliquer et supprimer des saisies à la main.

`production_data.planning_entry_id` fixe le lien au moment de la saisie.
Les lectures qui ont besoin du créneau le lisent d'abord ; la référence texte
reste le repli pour les saisies non rattachées (import, créneau supprimé).

Règles de rattachement, dans l'ordre :
1. une seule entrée du planning porte cette référence sur la machine → elle ;
2. la saisie précédente du même dossier sur la machine est rattachée, et rien
   n'a clos ce passage depuis (fin « Dossier terminé » ou annulation) → même
   créneau ;
3. saisie du jour (≤ 48 h) : le créneau en cours, sinon le premier en attente ;
4. saisie ancienne : le créneau dont les dates encadrent la saisie, sinon le
   plus proche dans le temps.
"""
from datetime import datetime, timedelta
from typing import Optional

CODES_CLOTURE = ("89", "90")


def _dt(v) -> Optional[datetime]:
    s = str(v or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if "T" in s or " " in s else s[:10], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s[:26])
    except ValueError:
        return None


def colonne_presente(conn) -> bool:
    return "planning_entry_id" in {r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}


def candidats(conn, no_dossier: str, machine: str) -> list:
    ref = (no_dossier or "").strip()
    mac = (machine or "").strip()
    if not ref or not mac:
        return []
    return [dict(r) for r in conn.execute(
        """SELECT pe.id, pe.statut, pe.position, pe.planned_start, pe.planned_end
             FROM planning_entries pe
             JOIN machines m ON m.id = pe.machine_id
            WHERE (trim(m.nom) = ? OR (trim(COALESCE(m.code,'')) <> '' AND trim(m.code) = ?))
              AND (trim(pe.reference) = ? OR trim(COALESCE(pe.numero_of,'')) = ?)""",
        (mac, mac, ref, ref),
    ).fetchall()]


def resoudre(conn, saisie: dict, maintenant: Optional[datetime] = None) -> Optional[int]:
    """Créneau du planning auquel appartient cette saisie (sans écrire)."""
    cands = candidats(conn, saisie.get("no_dossier"), saisie.get("machine"))
    if not cands:
        return None
    if len(cands) == 1:
        return int(cands[0]["id"])
    ids = {int(c["id"]) for c in cands}
    date_s = str(saisie.get("date_operation") or "")
    sid = saisie.get("id") or 0

    prev = conn.execute(
        """SELECT id, date_operation, operation_code, planning_entry_id,
                  COALESCE(fin_dossier, -1) AS fin_dossier
             FROM production_data
            WHERE trim(no_dossier) = trim(?) AND trim(machine) = trim(?)
              AND id <> ? AND planning_entry_id IS NOT NULL
              AND (date_operation < ? OR (date_operation = ? AND id < ?))
            ORDER BY date_operation DESC, id DESC LIMIT 1""",
        (saisie.get("no_dossier") or "", saisie.get("machine") or "", sid, date_s, date_s, sid),
    ).fetchone() if _a_fin_dossier(conn) else conn.execute(
        """SELECT id, date_operation, operation_code, planning_entry_id, -1 AS fin_dossier
             FROM production_data
            WHERE trim(no_dossier) = trim(?) AND trim(machine) = trim(?)
              AND id <> ? AND planning_entry_id IS NOT NULL
              AND (date_operation < ? OR (date_operation = ? AND id < ?))
            ORDER BY date_operation DESC, id DESC LIMIT 1""",
        (saisie.get("no_dossier") or "", saisie.get("machine") or "", sid, date_s, date_s, sid),
    ).fetchone()
    if prev and int(prev["planning_entry_id"]) in ids:
        code = str(prev["operation_code"] or "").strip()
        clos = code == "90" or (code == "89" and int(prev["fin_dossier"]) == 1)
        if not clos:
            return int(prev["planning_entry_id"])

    maintenant = maintenant or datetime.now()
    d = _dt(date_s) or maintenant
    if d >= maintenant - timedelta(hours=48):
        en_cours = [c for c in cands if c["statut"] == "en_cours"]
        if en_cours:
            return int(en_cours[0]["id"])
        attente = sorted((c for c in cands if c["statut"] == "attente"), key=lambda c: c["position"] or 0)
        if attente:
            return int(attente[0]["id"])

    def distance(c):
        s, e = _dt(c["planned_start"]), _dt(c["planned_end"])
        if not s and not e:
            return None
        s = s or e
        e = e or s
        if s <= d <= e:
            return 0.0
        return min(abs((d - s).total_seconds()), abs((d - e).total_seconds()))

    dated = [(distance(c), c) for c in cands]
    dated = [(x, c) for x, c in dated if x is not None]
    if dated:
        dated.sort(key=lambda t: (t[0], 0 if t[1]["statut"] == "termine" else 1))
        return int(dated[0][1]["id"])
    attente = sorted(cands, key=lambda c: c["position"] or 0)
    return int(attente[0]["id"])


_CACHE_FIN = {}


def _a_fin_dossier(conn) -> bool:
    key = id(conn)
    if key not in _CACHE_FIN:
        _CACHE_FIN.clear()
        _CACHE_FIN[key] = "fin_dossier" in {
            r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()
        }
    return _CACHE_FIN[key]


def rattacher(conn, saisie_id: int, forcer: bool = False) -> Optional[int]:
    """Pose `planning_entry_id` sur la saisie. Best effort : ne lève jamais."""
    try:
        if not colonne_presente(conn):
            return None
        row = conn.execute("SELECT * FROM production_data WHERE id = ?", (saisie_id,)).fetchone()
        if not row:
            return None
        row = dict(row)
        if row.get("planning_entry_id") and not forcer:
            return int(row["planning_entry_id"])
        pe_id = resoudre(conn, row)
        conn.execute("UPDATE production_data SET planning_entry_id = ? WHERE id = ?", (pe_id, saisie_id))
        return pe_id
    except Exception:
        return None


def saisies_du_creneau(conn, entry_id: int, reference: str, machine_nom: str) -> list:
    """Ids des saisies d'un créneau : rattachées, ou non rattachées de même référence."""
    return [int(r["id"]) for r in conn.execute(
        """SELECT id FROM production_data
            WHERE planning_entry_id = ?
               OR (planning_entry_id IS NULL AND trim(no_dossier) = trim(?) AND trim(machine) = trim(?))""",
        (entry_id, reference or "", machine_nom or ""),
    ).fetchall()]
