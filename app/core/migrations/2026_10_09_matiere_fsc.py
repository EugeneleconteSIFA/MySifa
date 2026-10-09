"""
Fiche matière : drapeau « Matière FSC » (vélin, couché, thermique, et les
complexes de ces papiers).

La catégorie ne suffit pas : un complexe peut être papier (couché, thermique,
vélin) ou synthétique (PP, PE, PET, PLA), et rien d'autre en base ne les
distingue — les complexes n'ont pas de sous-section. Le drapeau se règle dans
la fiche matière ; la reprise ci-dessous n'initialise que les fiches encore
vides, à partir de la sous-section (frontaux) ou du début de la référence
(complexes). Les cas douteux (« A identifier », références internes) restent
à 0 et se corrigent à la main.
"""
import unicodedata

NOM = "matiere_fsc_drapeau"

_SOUS_SECTIONS_FSC = ("velin", "couche", "thermiques", "thermique")
_PREFIXES_COMPLEXE_FSC = ("velin", "couche", "thermique", "papier")


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return s.strip().lower()


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)")}
    if "matiere_fsc" not in cols:
        conn.execute("ALTER TABLE matieres_premieres ADD COLUMN matiere_fsc INTEGER")
    rows = conn.execute(
        "SELECT id, categorie, sous_section, reference FROM matieres_premieres "
        "WHERE matiere_fsc IS NULL").fetchall()
    n = 0
    for mid, cat, sous, ref in rows:
        cat = _norm(cat)
        if cat == "frontal":
            fsc = 1 if _norm(sous) in _SOUS_SECTIONS_FSC else 0
        elif cat == "complexe":
            fsc = 1 if _norm(ref).startswith(_PREFIXES_COMPLEXE_FSC) else 0
        else:
            fsc = 0
        conn.execute("UPDATE matieres_premieres SET matiere_fsc=? WHERE id=?", (fsc, mid))
        n += fsc
    conn.commit()
    print(f"[MySifa] migration matiere_fsc : {n} matière(s) FSC.")
