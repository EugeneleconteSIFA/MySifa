"""
Devis : une quantité de fichier multiple exacte de celle des calculs n'est
plus « à vérifier ».

Le classeur Schisler annonce 4 320 000 ex dans son nom et calcule ses temps
pour 2 160 000 : exactement la moitié, ce qui est voulu (retour d'Eugène du
20/11/2026). La lecture levait pourtant le drapeau « à vérifier » avec la note
« Fichier : 4 320 000 ex · calculs : 2 160 000 ex ». Le contrôle ne le fait
plus pour les nouveaux devis (`multiple_exact`) ; cette migration retire la
même alerte des devis déjà importés, et le drapeau quand c'était sa seule
raison. Les autres raisons de la note restent.
"""
import json
import re

NOM = "devis_quantite_multiple_coherente"
DEPEND = ["devis_import_agent"]

_COURT = re.compile(r"Fichier : ([\d ]+) ex · calculs : ([\d ]+) ex")


def _multiple(a: float, b: float) -> bool:
    if a <= 0 or b <= 0:
        return False
    grand, petit = max(a, b), min(a, b)
    k = round(grand / petit)
    return k >= 2 and abs(grand - k * petit) < 1


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(devis)").fetchall()}
    if not {"a_verifier", "note", "coherence_json"} <= cols:
        return
    repris = 0
    for row in conn.execute(
        "SELECT id, note, coherence_json FROM devis WHERE note LIKE '%Fichier : %calculs : %'"
    ).fetchall():
        note = row[1] or ""
        m = _COURT.search(note)
        if not m:
            continue
        fichier = float(m.group(1).replace(" ", ""))
        calculs = float(m.group(2).replace(" ", ""))
        if not _multiple(fichier, calculs):
            continue
        reste = [p.strip() for p in note.replace(m.group(0), "").split(" · ") if p.strip()]
        try:
            coherence = [c for c in json.loads(row[2] or "[]")
                         if not (isinstance(c, dict) and "qte_etiquettes" in (c.get("champs") or []))]
        except (TypeError, ValueError):
            coherence = []
        conn.execute(
            "UPDATE devis SET note=?, a_verifier=?, coherence_json=? WHERE id=?",
            (" · ".join(reste), 1 if reste else 0, json.dumps(coherence, ensure_ascii=False), row[0]),
        )
        repris += 1
    conn.commit()
    print(f"[MySifa] migration {NOM} : {repris} devis repris.")
