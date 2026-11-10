"""MyAO — fiche produit tirée d'une fiche technique MyProd."""
import sys

sys.path.insert(0, ".")

from app.services.ao_produit_depuis_fiche import (  # noqa: E402
    completer_vides,
    diametre_mandrin,
    enroulement,
    fiche_vers_produit,
    nb_champs,
)
from app.services.ao_produit_fiche import default_fiche  # noqa: E402


FT = {
    "reference": "623/0014",
    "laize": 440, "laize_optimale": 440,          # bobine : jamais l'étiquette
    "eti_laize": 104.5, "eti_longueur": 148.4, "eti_rayons": 6,
    "eti_perforations": "", "lateral_ext": 1.625, "horizontal": 4,
    "support_ref_id": 11, "adhesif_ref_id": 12, "glassine_ref_id": 99,
    "palette_ref_id": 14, "mandrin_dia": "Tube 1500x40", "dia_ext": 0,
    "nb_etiq_bobin": 500, "enroulement": "Exterieur pied en avant",
    "recto": 1, "verso": 0, "nb_bobines_carton": 16, "nb_au_sol": 0,
}
ACTIVES = {11: "frontal", 12: "adhesif", 99: "frontal", 14: "palette"}


def test_mandrin_et_enroulement():
    assert diametre_mandrin("Tube 1500x40") == 40
    assert diametre_mandrin("12 mm") == 12
    assert diametre_mandrin("Bague 69,9x40") == 40
    assert diametre_mandrin("Planches A4") is None
    assert enroulement("Intérieur Tête en avant") == "interieur"
    assert enroulement("Ext. Grand côté en avant") == "exterieur"
    assert enroulement("Voir BAT") is None


def test_traduction():
    a = fiche_vers_produit(FT, ACTIVES)
    assert a["ref_sifa"] == "623/0014"
    assert a["etiquette"] == {"laize": 104.5, "longueur": 148.4, "rayon": 6}
    assert a["echenillage"] == {"droite": 1.625, "gauche": 1.625, "avance": 4}
    # glassine 99 est un frontal : pas reprise
    assert a["matiere"] == {"frontal_id": "11", "adhesif_id": "12"}
    assert a["conditionnement"]["palette"]["matiere_id"] == "14"
    assert a["bobines"]["diametre_mandrin"] == 40
    assert "diametre_bobine" not in a["bobines"]          # zéro Access = vide
    assert a["bobines"]["sens_sortie"] == 1
    assert a["impressions_detail"] == {"recto": 1}
    assert "bobines_sol" not in a["conditionnement"]["carton"]


def test_completer_ne_reecrit_rien():
    f = default_fiche()
    f["etiquette"]["laize"] = 100
    f["bobines"]["sens_sortie"] = 3
    n = completer_vides(f, fiche_vers_produit(FT, ACTIVES))
    assert f["etiquette"]["laize"] == 100            # saisie conservée
    assert f["etiquette"]["longueur"] == 148.4
    assert f["bobines"]["sens_sortie"] == 3          # défaut non écrasé
    assert f["ref_sifa"] == "623/0014"
    assert n > 0 and n <= nb_champs(fiche_vers_produit(FT, ACTIVES))


if __name__ == "__main__":
    test_mandrin_et_enroulement(); test_traduction(); test_completer_ne_reecrit_rien()
    print("OK")
