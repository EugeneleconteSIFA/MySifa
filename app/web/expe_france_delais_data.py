"""Données par défaut — délais livraison par département (MyExpé carte France)."""
import json
from pathlib import Path

_DEPT_LABELS: dict[str, str] = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
    "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
    "18": "Cher", "19": "Corrèze", "21": "Côte-d'Or", "22": "Côtes-d'Armor",
    "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure",
    "28": "Eure-et-Loir", "29": "Finistère", "30": "Gard", "31": "Haute-Garonne",
    "32": "Gers", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine",
    "36": "Indre", "37": "Indre-et-Loire", "38": "Isère", "39": "Jura",
    "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
    "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne",
    "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
    "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse",
    "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise",
    "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin",
    "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire",
    "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris",
    "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres",
    "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse",
    "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges",
    "89": "Yonne", "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis", "94": "Val-de-Marne", "95": "Val-d'Oise",
    "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Réunion", "976": "Mayotte",
}

_IDF = {"75", "77", "78", "91", "92", "93", "94", "95"}
_J1 = {"59", "62", "80", "02", "08", "51", "54", "57", "67", "68", "25", "39"}
_CORSICA = {"2A", "2B"}
_DOM = {"971", "972", "973", "974", "976"}
_REMOTE = {"29", "56", "22", "64", "65", "48", "04", "05", "06", "66", "2A", "2B"}


def _default_entry(dept: str) -> dict[str, str]:
    label = _DEPT_LABELS.get(dept, f"Département {dept}")
    if dept in _DOM:
        return {"label": label, "delai": "J+5", "zone": "affretement"}
    if dept in _IDF:
        zone = "france_hors_paris"
        delai = "J+2" if dept == "75" else "J+1"
        return {"label": label, "delai": delai, "zone": zone}
    if dept in _CORSICA or dept in _REMOTE:
        return {"label": label, "delai": "J+3", "zone": "france"}
    if dept in _J1:
        return {"label": label, "delai": "J+1", "zone": "france"}
    if dept in {"13", "31", "33", "34", "69", "38", "44", "35"}:
        return {"label": label, "delai": "J+1", "zone": "messagerie"}
    if dept in {"76", "14", "50", "37", "45", "28"}:
        return {"label": label, "delai": "J+2", "zone": "france"}
    return {"label": label, "delai": "J+2", "zone": "france"}


def build_delais_france_default() -> dict[str, dict[str, str]]:
    svg_path = Path(__file__).resolve().parent / "expe_france_departments.svg"
    ids: list[str] = []
    if svg_path.is_file():
        import re

        ids = re.findall(r'\bid="([^"]+)"', svg_path.read_text(encoding="utf-8"))
    ids.extend(_DOM)
    out: dict[str, dict[str, str]] = {}
    for dept in ids:
        if dept not in out:
            out[dept] = _default_entry(dept)
    for dept in _DEPT_LABELS:
        if dept not in out:
            out[dept] = _default_entry(dept)
    return out


DELAIS_FRANCE_DEFAULT = build_delais_france_default()
DELAIS_FRANCE_JSON = json.dumps(DELAIS_FRANCE_DEFAULT, ensure_ascii=False)
