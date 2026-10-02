"""
Fusion des fiches fournisseur en double.

Revue du 02/10/2026 : six sociétés existaient deux fois dans `fournisseurs_fsc`,
le plus souvent une fiche saisie à la main (prix, certificats, appels d'offres)
et la fiche importée de RVGI (numéro fournisseur, donc articles). La reprise de
l'inventaire rattachant les variantes par le numéro RVGI, une matière Likexin
montrait deux fournisseurs : « Likexin » avec le prix, « SHENZHEN LIKEXIN… »
avec la référence.

Données : `donnees/fusion_fournisseurs_2026_10_03.json`. Logique :
`app/services/fournisseurs_fusion.py`. Une paire ne s'applique que si les deux
fiches portent encore l'id ET le nom relevés : une autre base passe à côté.

Ces paires sont les cas que `scripts/fusion_fournisseurs_doublons.py` avait
laissés « à trancher » le 08/09/2026, plus les tiers RVGI importés depuis
(Likexin, Xinzhu). Le sens est celui du script : la fiche d'usage survit, avec
le lien RVGI de l'autre ; la fusion est la même (`fournisseurs_fusion`). Seule
exception, Torrespapel : la fiche manuelle, au nom mal orthographié, se fond
dans l'entité RVGI qui facture.

La licence FSC de Torraspapel (groupe Lecta) va à l'entité qui facture les
bobines ; les deux entités sont rangées dans le groupe « Torraspapel » et le
certificat passe au niveau groupe, pour couvrir aussi la France.

Les variantes provisoires rendues jumelles par une fusion (prix chez
« Likexin » + article chez l'ex-« SHENZHEN LIKEXIN ») sont fondues par la
fusion elle-même.
"""

import json
import os

NOM = "fournisseurs_fusion_doublons_2026_10"
DEPEND = ["mp_variantes_fusion_provisoires"]


def _fichier() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees",
                        "fusion_fournisseurs_2026_10_03.json")


def _concorde(conn, f) -> bool:
    r = conn.execute("SELECT nom FROM fournisseurs_fsc WHERE id=?", (f["id"],)).fetchone()
    return bool(r) and (r[0] or "").strip() == f["nom"].strip()


def appliquer(conn):
    from app.services import fournisseurs_fusion as fusion

    fusion.assurer_colonne(conn)
    with open(_fichier(), encoding="utf-8") as fh:
        data = json.load(fh)

    faites, ignorees = [], 0
    for p in data["fusions"]:
        s, d = p["survivant"], p["doublon"]
        if not (_concorde(conn, s) and _concorde(conn, d)):
            ignorees += 1
            continue
        if conn.execute("SELECT fusionne_dans FROM fournisseurs_fsc WHERE id=?", (d["id"],)).fetchone()[0]:
            continue
        r = fusion.fusionner(conn, d["id"], s["id"], auteur="Migration " + NOM)
        faites.append("%s ← %s (%s)%s" % (
            r["target"]["nom"], r["source"]["nom"],
            ", ".join("%s %d" % kv for kv in sorted({**r["moved"], **r["renamed"]}.items())) or "rien à déplacer",
            " — gardée pour son lien RVGI" if r["source_conservee"] else ""))

    for g in data.get("groupes", []):
        if not all(_concorde(conn, f) for f in g["fournisseurs"]):
            continue
        for f in g["fournisseurs"]:
            conn.execute(
                "UPDATE fournisseurs_fsc SET groupe=? WHERE id=? AND (groupe IS NULL OR TRIM(groupe)='')",
                (g["groupe"], f["id"]))
        src = g.get("certificats_de")
        if src and _concorde(conn, src):
            conn.execute(
                "UPDATE qualite_fournisseur_certificats SET groupe_ref=? "
                "WHERE fournisseur_id=? AND (groupe_ref IS NULL OR TRIM(groupe_ref)='')",
                (g["groupe"], src["id"]))

    conn.commit()
    print(f"[MySifa] migration {NOM} : {len(faites)} fusion(s), {ignorees} paire(s) absente(s) de cette base.")
    for ligne in faites:
        print(f"[MySifa]   {ligne}")
