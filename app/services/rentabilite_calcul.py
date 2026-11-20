"""
SIFA — Moteur de rentabilité : un seul calcul, devisé ou réel.

LE CALCUL EST CELUI DU CLASSEUR DE DEVIS (feuille Prix), pas une invention :

    marge brute  = prix de vente − (matière + encre + cliché + outil
                                     + emballage + transport)
    MB %         = marge brute ÷ prix de vente
    coût horaire = marge brute ÷ heures machine       (cellule « Cout Horaire »)

Le coût machine (heures × taux KDO) n'entre PAS dans la marge brute : il sert
au classeur à fabriquer le prix de vente. Un dossier lent garde donc sa marge
brute et perd du coût horaire ; un dossier qui change de laize perd de la
marge brute. Les deux indicateurs se complètent, ils ne se répètent pas.

LE RÉEL EST UNE FOURCHETTE. Les temps sont saisis à la main, la matière se
déstocke au jugé : chaque entrée réelle porte un bas, un probable et un haut,
et le moteur calcule la marge en pire et en meilleur cas. Le verdict ne tombe
que quand TOUTE la fourchette est du même côté du seuil ; sinon le dossier est
« à la limite », ce qui veut dire « la précision des saisies ne permet pas de
trancher », pas « presque réussi ».

Ce module ne lit pas la base : il reçoit des nombres et rend des nombres.
C'est ce qui permet de le contrôler sur les devis (il doit retrouver la marge
et le coût horaire de chaque classeur) et de le tester sans fixture.
"""
from dataclasses import dataclass, field
from typing import Optional

from app.services.devis_chiffrage import POSTES_DIRECTS, prix_m2_retenu

# ══════════════════════════════════════════════════════════════════
# Fourchettes
# ══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Fourchette:
    """Une valeur incertaine : bas ≤ probable ≤ haut."""
    bas: float
    probable: float
    haut: float

    @classmethod
    def exacte(cls, v: float) -> "Fourchette":
        v = float(v or 0)
        return cls(v, v, v)

    @classmethod
    def relative(cls, v: float, pct: float) -> "Fourchette":
        """± pct % autour de v (pct = 1 pour 1 %)."""
        v = float(v or 0)
        d = abs(v) * float(pct or 0) / 100.0
        return cls(v - d, v, v + d)

    @classmethod
    def absolue(cls, v: float, delta: float) -> "Fourchette":
        v = float(v or 0)
        d = abs(float(delta or 0))
        return cls(v - d, v, v + d)

    def __add__(self, autre):
        o = autre if isinstance(autre, Fourchette) else Fourchette.exacte(autre)
        return Fourchette(self.bas + o.bas, self.probable + o.probable, self.haut + o.haut)

    __radd__ = __add__

    def __sub__(self, autre):
        # Soustraire une incertitude l'élargit : le bas retire le haut.
        o = autre if isinstance(autre, Fourchette) else Fourchette.exacte(autre)
        return Fourchette(self.bas - o.haut, self.probable - o.probable, self.haut - o.bas)

    def __rsub__(self, autre):
        return Fourchette.exacte(autre) - self

    def fois(self, k: float) -> "Fourchette":
        k = float(k)
        a, b = self.bas * k, self.haut * k
        return Fourchette(min(a, b), self.probable * k, max(a, b))

    def divise_par(self, d: "Fourchette") -> "Fourchette":
        """self ÷ d, d strictement positif. Pire et meilleur cas sur les 4 bornes."""
        if d.bas <= 0:
            raise ValueError("Diviseur nul ou négatif : fourchette non calculable.")
        bornes = [self.bas / d.bas, self.bas / d.haut, self.haut / d.bas, self.haut / d.haut]
        return Fourchette(min(bornes), self.probable / d.probable, max(bornes))

    def en_pct_de(self, total: float) -> "Fourchette":
        """En % d'un total exact (le prix de vente facturé)."""
        if not total:
            raise ValueError("Total nul : pourcentage non calculable.")
        return self.fois(100.0 / total)

    def largeur(self) -> float:
        return self.haut - self.bas

    def dict(self, arrondi: int = 2) -> dict:
        return {"bas": round(self.bas, arrondi), "probable": round(self.probable, arrondi),
                "haut": round(self.haut, arrondi)}


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


# ══════════════════════════════════════════════════════════════════
# Côté devis
# ══════════════════════════════════════════════════════════════════

def calcul_devis(valeurs: dict) -> dict:
    """MB, MB % et coût horaire d'un devis, recalculés depuis ses postes.

    `valeurs` : le dictionnaire de `devis_chiffrage` (postes lus du classeur).
    """
    pv = _f(valeurs.get("prix_vente"))
    directs = sum(_f(valeurs.get(p)) for p in POSTES_DIRECTS)
    mb = pv - directs
    heures = _f(valeurs.get("temps_total_mn")) / 60.0
    return {
        "prix_vente": pv,
        "couts_directs": directs,
        "marge_brute": mb,
        "mb_pct": (mb / pv * 100.0) if pv else None,
        "heures": heures,
        "cout_horaire": (mb / heures) if heures else None,
    }


def controler_devis(valeurs: dict, laize_mm: Optional[float],
                    tolerance_pct: float) -> list[dict]:
    """Refait le calcul du classeur et le compare aux montants lus.

    Chaque contrôle rend `{controle, lu, recalcule, ecart_pct, ok}`. Un
    contrôle dont une entrée manque est omis, pas compté faux : un devis
    d'un autre modèle n'a pas à échouer sur un poste qu'il ne porte pas.
    """
    v = valeurs
    controles: list[dict] = []

    def ajouter(nom: str, lu, recalcule):
        if lu is None or recalcule is None:
            return
        lu, recalcule = float(lu), float(recalcule)
        base = max(abs(lu), abs(recalcule))
        ecart = 0.0 if base == 0 else abs(lu - recalcule) / base * 100.0
        controles.append({"controle": nom, "lu": round(lu, 2),
                          "recalcule": round(recalcule, 2),
                          "ecart_pct": round(ecart, 3), "ok": ecart <= tolerance_pct})

    prix = prix_m2_retenu(v)
    if v.get("metrage_total_ml") and laize_mm and prix:
        ajouter("Coût matière = ml × laize × €/m²", v.get("cout_matiere"),
                _f(v["metrage_total_ml"]) * float(laize_mm) / 1000.0 * prix)

    if v.get("prix_vente") is not None:
        calc = calcul_devis(v)
        ajouter("Marge brute = PV − coûts directs", v.get("marge_brute"), calc["marge_brute"])
        if calc["cout_horaire"] is not None:
            ajouter("Coût horaire = MB ÷ heures", v.get("cout_horaire"), calc["cout_horaire"])

    couts = [k for k in v if k.startswith("cout_") and k != "cout_horaire"]
    if v.get("prix_revient") is not None and any(v.get(k) is not None for k in couts):
        ajouter("Prix de revient = somme des postes", v.get("prix_revient"),
                sum(_f(v.get(k)) for k in couts))

    if v.get("prix_revient") is not None and v.get("surmarge") is not None:
        ajouter("PV = revient − remise + surmarge", v.get("prix_vente"),
                _f(v["prix_revient"]) - _f(v.get("remise")) + _f(v["surmarge"]))

    if v.get("temps_total_mn") and v.get("taux_horaire"):
        ajouter("Coût production = heures × taux machine", v.get("cout_production"),
                _f(v["temps_total_mn"]) / 60.0 * _f(v["taux_horaire"]))
    return controles


def redevise_laize(valeurs: dict, laize_devis: float, laize_reelle: float) -> Optional[float]:
    """Le prix de vente qu'aurait sorti le classeur avec la laize réelle.

    Seul le coût matière dépend de la laize ; le prix de revient bouge
    d'autant, et le PV suit la surmarge. Sert à chiffrer ce qu'un changement
    de laize décidé en production a coûté sans être refacturé.
    """
    if not (laize_devis and laize_reelle and valeurs.get("prix_revient") is not None):
        return None
    delta_matiere = _f(valeurs.get("cout_matiere")) * (laize_reelle / laize_devis - 1.0)
    revient = _f(valeurs["prix_revient"]) + delta_matiere
    taux = _f(valeurs.get("surmarge_taux"))
    return revient - _f(valeurs.get("remise")) + revient * taux


# ══════════════════════════════════════════════════════════════════
# Côté réel
# ══════════════════════════════════════════════════════════════════

def croiser_surfaces(compteur: Optional[Fourchette], mystock: Optional[Fourchette],
                     ecart_max_pct: float) -> tuple[Optional[Fourchette], str, Optional[float]]:
    """Retient la surface consommée à partir de ses deux mesures.

    Compteur × laize d'un côté, sorties − retours MyStock de l'autre. Si elles
    s'accordent, on garde leur recouvrement (plus étroit que chacune) ; si
    l'écart dépasse le seuil, c'est une erreur de saisie : on garde l'union,
    plus large, et on le dit.

    Rend `(fourchette, statut, ecart_pct)`, statut parmi `coherent`,
    `incoherent`, `compteur_seul`, `mystock_seul`, `absent`.
    """
    if compteur is None and mystock is None:
        return None, "absent", None
    if mystock is None:
        return compteur, "compteur_seul", None
    if compteur is None:
        return mystock, "mystock_seul", None
    base = max(compteur.probable, mystock.probable)
    ecart = abs(compteur.probable - mystock.probable) / base * 100.0 if base else 0.0
    probable = (compteur.probable + mystock.probable) / 2.0
    if ecart <= ecart_max_pct:
        bas, haut = max(compteur.bas, mystock.bas), min(compteur.haut, mystock.haut)
        if bas > haut:  # fourchettes disjointes mais proches : on encadre les deux probables
            bas = min(compteur.probable, mystock.probable)
            haut = max(compteur.probable, mystock.probable)
        probable = min(max(probable, bas), haut)
        return Fourchette(bas, probable, haut), "coherent", round(ecart, 2)
    return (Fourchette(min(compteur.bas, mystock.bas), probable, max(compteur.haut, mystock.haut)),
            "incoherent", round(ecart, 2))


@dataclass
class EntreesReelles:
    """Ce qu'un dossier complet a réellement coûté et rapporté.

    `prix_vente` est le montant FACTURÉ (RVGI). `prorata` vaut qté facturée ÷
    qté produite pour un marché facturé en plusieurs appels, 1 sinon — hors
    marché, l'excédent produit est de la gâche et reste à la charge du dossier.
    """
    prix_vente: float
    surface_m2: Fourchette
    prix_m2: float
    couts_annexes: dict = field(default_factory=dict)   # nom → Fourchette (outil, emballage, transport…)
    duree_mn: Fourchette = field(default_factory=lambda: Fourchette.exacte(0))
    calage_mn: float = 0.0
    production_mn: float = 0.0
    arret_mn: float = 0.0
    frontiere_mn: float = 0.0
    prorata: float = 1.0


def calcul_reel(e: EntreesReelles) -> dict:
    """MB, MB % et coût horaire réels, en fourchettes.

    Avec un prorata < 1, coûts et heures sont ramenés à la part facturée. Le
    MB % et le coût horaire n'en dépendent pas (ils sont des rapports) ; la
    marge en euros, si : `marge_brute` est celle de la part facturée,
    `marge_brute_pleine` celle ramenée à toute la production, qui se compare
    au devis.
    """
    k = min(max(float(e.prorata or 1.0), 0.0), 1.0) or 1.0
    matiere = e.surface_m2.fois(e.prix_m2)
    annexes = Fourchette.exacte(0)
    for f in (e.couts_annexes or {}).values():
        annexes = annexes + (f if isinstance(f, Fourchette) else Fourchette.exacte(f))
    directs = (matiere + annexes).fois(k)
    mb = Fourchette.exacte(e.prix_vente) - directs
    heures = e.duree_mn.fois(k / 60.0)
    res = {
        "prorata": round(k, 4),
        "prix_vente": round(e.prix_vente, 2),
        "cout_matiere": matiere.fois(k).dict(),
        "couts_annexes": annexes.fois(k).dict(),
        "couts_directs": directs.dict(),
        "marge_brute": mb.dict(),
        "marge_brute_pleine": mb.fois(1.0 / k).dict(),
        "mb_pct": mb.en_pct_de(e.prix_vente).dict() if e.prix_vente else None,
        "heures": heures.dict(3),
        "cout_horaire": mb.divise_par(heures).dict() if heures.bas > 0 else None,
    }
    return res


# ══════════════════════════════════════════════════════════════════
# Verdict
# ══════════════════════════════════════════════════════════════════

REUSSI, LIMITE, SOUS_SEUIL = "reussi", "limite", "sous_seuil"


def position(f: Optional[dict], seuil: float) -> Optional[str]:
    """Où se trouve une fourchette par rapport à un seuil."""
    if not f:
        return None
    if f["bas"] >= seuil:
        return REUSSI
    if f["haut"] < seuil:
        return SOUS_SEUIL
    return LIMITE


def verdict(mb_pct: Optional[dict], cout_horaire: Optional[dict],
            seuil_mb_pct: float, seuil_cout_horaire: float) -> dict:
    """Réussi si les deux fourchettes passent leur seuil, sous le seuil si
    l'une est entièrement en dessous, à la limite sinon."""
    p_mb = position(mb_pct, seuil_mb_pct)
    p_eh = position(cout_horaire, seuil_cout_horaire)
    if p_mb is None or p_eh is None:
        global_ = None
    elif SOUS_SEUIL in (p_mb, p_eh):
        global_ = SOUS_SEUIL
    elif p_mb == REUSSI and p_eh == REUSSI:
        global_ = REUSSI
    else:
        global_ = LIMITE
    return {"global": global_, "marge": p_mb, "cout_horaire": p_eh}


# ══════════════════════════════════════════════════════════════════
# Cascades d'écarts
# ══════════════════════════════════════════════════════════════════

def cascade_marge(devis: dict, laize_devis: float, reel: EntreesReelles,
                  laize_reelle: float) -> list[dict]:
    """De la marge devisée à la marge réelle, une cause à la fois.

    Substitution dans un ordre fixe : on remplace une entrée devisée par sa
    valeur réelle, on mesure ce que la marge a bougé, on passe à la suivante.
    L'ordre décide de qui porte les effets croisés ; il va de la décision
    (laize, prix) vers l'atelier (métrage, gâche) puis la logistique et la
    facture. La dernière marche absorbe le reste (prix, quantité facturée),
    si bien que la cascade tombe toujours exactement sur la marge réelle.

    Tout est en valeur probable, ramené à toute la production (prorata).
    """
    pv_d = _f(devis.get("prix_vente"))
    mat_d = _f(devis.get("cout_matiere"))
    annexes_d = sum(_f(devis.get(p)) for p in POSTES_DIRECTS if p != "cout_matiere")
    prix_d = prix_m2_retenu(devis) or 0.0

    mb_reel = calcul_reel(reel)["marge_brute_pleine"]["probable"]

    etapes = [{"cause": "Devisé", "nature": "total", "valeur": round(pv_d - mat_d - annexes_d, 2)}]
    courant_mat = mat_d

    def pas(cause: str, nature: str, nouvelle_mat: float):
        nonlocal courant_mat
        etapes.append({"cause": cause, "nature": nature,
                       "valeur": round(-(nouvelle_mat - courant_mat), 2)})
        courant_mat = nouvelle_mat

    if laize_devis and laize_reelle and abs(laize_reelle - laize_devis) > 0.01:
        pas("Laize", "decision", courant_mat * laize_reelle / laize_devis)
    if prix_d and reel.prix_m2 and abs(reel.prix_m2 - prix_d) > 1e-6:
        pas("Prix matière", "decision", courant_mat * reel.prix_m2 / prix_d)
    pas("Métrage et gâche", "atelier", reel.surface_m2.probable * reel.prix_m2)

    annexes_r = sum((f.probable if isinstance(f, Fourchette) else _f(f))
                    for f in (reel.couts_annexes or {}).values())
    etapes.append({"cause": "Emballage, transport", "nature": "logistique",
                   "valeur": round(-(annexes_r - annexes_d), 2)})

    avant_facture = pv_d - courant_mat - annexes_r
    reste = mb_reel - avant_facture
    if abs(reste) >= 0.5:
        etapes.append({"cause": "Prix facturé", "nature": "commercial",
                       "valeur": round(reste, 2)})
    etapes.append({"cause": "Réalisé", "nature": "total", "valeur": round(mb_reel, 2)})
    return [e for e in etapes if e["nature"] == "total" or abs(e["valeur"]) >= 0.5]


def cascade_cout_horaire(devis: dict, calage_devis_mn: float,
                         reel: EntreesReelles) -> list[dict]:
    """Du coût horaire devisé au réel : effet marge, puis calage, vitesse, arrêts.

    Le partage entre calage et production dépend du moment où la saisie 03 est
    faite, qui est la principale source d'erreur de temps. Les marches
    « calage » et « vitesse » portent donc une fourchette (`fourchette`) :
    déplacer la frontière de ± `frontiere_mn` fait passer du temps de l'une à
    l'autre. Leur somme, elle, ne bouge pas.

    `calage_devis_mn` : calage outil + calage impression du devis (le socle) ;
    les heures devisées totales viennent du chiffrage (`temps_total_mn`).
    """
    calc_d = calcul_devis(devis)
    h_d = calc_d["heures"]
    if not h_d or calc_d["cout_horaire"] is None:
        return []
    mb = calcul_reel(reel)["marge_brute_pleine"]["probable"]
    h_calage_d = _f(calage_devis_mn) / 60.0
    h_prod_d = h_d - h_calage_d

    def eh(h):
        return mb / h if h > 0 else 0.0

    e0 = calc_d["cout_horaire"]
    e1 = mb / h_d

    def deux_pas(calage_mn: float):
        h_cal = calage_mn / 60.0
        prod_mn = reel.calage_mn + reel.production_mn - calage_mn
        a = eh(h_cal + h_prod_d)
        b = eh(h_cal + prod_mn / 60.0)
        return a - e1, b - a

    cal_p, vit_p = deux_pas(reel.calage_mn)
    variantes = [deux_pas(max(0.0, reel.calage_mn + s * reel.frontiere_mn)) for s in (-1, 1)]
    cal_f = sorted(v[0] for v in variantes + [(cal_p, vit_p)])
    vit_f = sorted(v[1] for v in variantes + [(cal_p, vit_p)])
    e3 = eh((reel.calage_mn + reel.production_mn) / 60.0)
    e4 = eh((reel.calage_mn + reel.production_mn + reel.arret_mn) / 60.0)

    return [
        {"cause": "Devisé", "nature": "total", "valeur": round(e0, 1)},
        {"cause": "Baisse de marge", "nature": "marge", "valeur": round(e1 - e0, 1)},
        {"cause": "Calage", "nature": "atelier", "valeur": round(cal_p, 1),
         "fourchette": [round(cal_f[0], 1), round(cal_f[-1], 1)]},
        {"cause": "Vitesse", "nature": "atelier", "valeur": round(vit_p, 1),
         "fourchette": [round(vit_f[0], 1), round(vit_f[-1], 1)]},
        {"cause": "Arrêts, nettoyage", "nature": "atelier", "valeur": round(e4 - e3, 1)},
        {"cause": "Réalisé", "nature": "total", "valeur": round(e4, 1)},
    ]


# ══════════════════════════════════════════════════════════════════
# Sensibilité d'un devis — avant la production
# ══════════════════════════════════════════════════════════════════

def sensibilite(valeurs: dict, socle: dict, seuil_mb_pct: float,
                seuil_cout_horaire: float) -> list[dict]:
    """Ce que deviennent MB % et coût horaire si un paramètre bouge en production.

    Quatre écarts courants, chacun seul, à prix de vente constant (le devis est
    signé) : laize +20 mm, prix matière +5 %, gâche +3 points, vitesse
    −10 m/mn. Sert au planning AVANT de lancer : un devis à 40,1 % sait qu'il
    ne supporte pas un changement de laize.

    `socle` : les colonnes du devis (laize, gache, vitesse_theorique,
    metrage_production_ml, temps_production_mn).
    """
    calc = calcul_devis(valeurs)
    pv, h, mb = calc["prix_vente"], calc["heures"], calc["marge_brute"]
    mat = _f(valeurs.get("cout_matiere"))
    if not pv or not h or not mat:
        return []
    laize = _f(socle.get("laize"))
    gache = _f(socle.get("gache"))
    vitesse = _f(socle.get("vitesse_theorique"))
    ml_prod = _f(socle.get("metrage_production_ml"))
    t_prod = _f(socle.get("temps_production_mn")) or (ml_prod / vitesse if vitesse else 0)

    def ligne(cle, libelle, detail, delta_mat=0.0, heures=None):
        mb2 = mb - delta_mat
        h2 = heures if heures else h
        pct, eh = mb2 / pv * 100.0, mb2 / h2
        return {"cle": cle, "libelle": libelle, "detail": detail,
                "mb_pct": round(pct, 2), "cout_horaire": round(eh, 1),
                "delta_mb": round(-delta_mat, 2),
                "sous_seuil_mb": pct < seuil_mb_pct,
                "sous_seuil_cout_horaire": eh < seuil_cout_horaire}

    lignes = []
    if laize:
        lignes.append(ligne("laize", "Laize +20 mm", f"{laize + 20:g} au lieu de {laize:g} mm",
                            delta_mat=mat * 20.0 / laize))
    lignes.append(ligne("prix", "Prix matière +5 %", "", delta_mat=mat * 0.05))
    if gache > 0:  # gâche absente du socle : on ne fabrique pas un « 0 % »
        lignes.append(ligne("gache", "Gâche +3 points",
                            f"{(gache + 0.03) * 100:g} % au lieu de {gache * 100:g} %",
                            delta_mat=mat * (0.03 / (1.0 + gache))))
    if vitesse > 10 and ml_prod and t_prod:
        h2 = h - t_prod / 60.0 + ml_prod / (vitesse - 10.0) / 60.0
        lignes.append(ligne("vitesse", "Vitesse −10 m/mn", f"{vitesse - 10:g} au lieu de {vitesse:g} m/mn",
                            heures=h2))
    return lignes
