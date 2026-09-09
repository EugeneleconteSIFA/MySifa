"""Lire la packing list d'un fournisseur — sans jamais supposer son format.

Le probleme, pose par Eugene le 09/09/2026 : « chaque fournisseur aura sa
maniere de gerer cela ». Ecrire un lecteur par fournisseur, c'est un lecteur de
plus a chaque nouveau fournisseur et une regression silencieuse le jour ou l'un
d'eux ajoute une colonne. Ecrire un lecteur qui DEVINE, c'est pire : il se
trompe sans le dire, et une bobine entre en stock avec la laize d'une autre.

D'ou le compromis retenu, le meme que pour les grilles tarifaires transporteur :
le module PROPOSE une correspondance de colonnes, un humain la valide, et le
profil est memorise par fournisseur. La deuxieme livraison du meme fournisseur
ne redemande rien ; un fournisseur inconnu coute un clic.

Ce que le module lit, releve sur la premiere liste reelle (PZH260486, 49 bobines
d'une seule reference, 5 laizes) :

    ligne 1   (vide)
    ligne 2   roll batch number | width(MM) | length(M)
    ligne 3   Y2606000506       | 440       | 17980
    ...
    ligne 51  (vide)

Trois lecons tirees de ce seul fichier, et codees ici :

1. **L'entete n'est pas la premiere ligne.** Une ligne vide en tete suffit a
   faire nommer les colonnes « Unnamed: 0 » par pandas et a promouvoir la vraie
   entete en donnee. On cherche donc la ligne d'entete au lieu de la supposer.

2. **L'unite est dans le titre de la colonne, pas ailleurs.** `width(MM)` et
   `length(M)` disent tout. Un fournisseur qui ecrit `length(KM)` sortirait un
   metrage mille fois trop petit si on ne lisait pas la parenthese.

3. **« roll batch number » est un identifiant de bobine, pas un numero de lot.**
   Un entete qui contient « roll » designe la bobine, meme s'il contient aussi
   « batch ». Confondre les deux ferait entrer 49 bobines portant toutes le
   meme code — donc UNE bobine, les 48 autres rattachees.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence

# Nombre de lignes rendues en apercu. Huit suffit a reconnaitre un format et
# tient dans un ecran sans defilement.
APERCU = 8

# Une laize hors de cette plage n'est pas une laize : c'est une autre colonne
# lue par erreur. Bornes larges a dessein — 50 mm couvre les rubans etroits,
# 2 000 mm depasse la plus large machine de SIFA.
LAIZE_MIN_MM, LAIZE_MAX_MM = 20.0, 2500.0

_ACCENTS = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")


def _norm(s: Any) -> str:
    """Entete normalise : minuscules, sans accents, sans ponctuation."""
    t = unicodedata.normalize("NFC", str(s or "")).strip().lower().translate(_ACCENTS)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _txt(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def _nombre(v: Any) -> Optional[float]:
    """Nombre d'une cellule, virgule decimale et separateurs de milliers admis.

    « 17 980 », « 17.980 » et « 17980 » sont le meme metrage chez trois
    fournisseurs differents. On ne peut pas distinguer un point de milliers d'un
    point decimal dans l'absolu : la regle retenue est qu'un point ou une
    virgule suivi d'exactement trois chiffres, avec d'autres chiffres devant,
    est un separateur de milliers. C'est ce que produit Excel en francais et en
    anglais, et cela n'a jamais d'autre sens sur un metrage ou une laize.
    """
    s = _txt(v).replace(" ", "").replace(" ", "")
    if not s:
        return None
    s = re.sub(r"[^0-9,.\-]", "", s)
    if not s or s in ("-", ".", ","):
        return None
    if re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    else:
        s = s.replace(",", ".")
        if s.count(".") > 1:
            entier, _, dec = s.rpartition(".")
            s = entier.replace(".", "") + "." + dec
    try:
        return float(s)
    except ValueError:
        return None


# ── Grille ───────────────────────────────────────────────────────────────────

def normaliser_grille(lignes: Sequence[Sequence[Any]]):
    """Grille en texte, lignes et colonnes entierement vides retirees.

    Rend AUSSI le numero de chaque ligne dans le fichier d'origine. Sans lui,
    un refus signale « ligne 12 » alors que l'utilisateur en voit 14 dans son
    Excel — et il cherche l'erreur au mauvais endroit. Les lignes vides d'en
    tete decalent tout.
    """
    brut = [[_txt(c) for c in (ligne or [])] for ligne in (lignes or [])]
    largeur = max((len(l) for l in brut), default=0)
    brut = [l + [""] * (largeur - len(l)) for l in brut]
    paires = [(i + 1, l) for i, l in enumerate(brut) if any(c for c in l)]
    if not paires:
        return [], []
    gardees = [i for i in range(largeur) if any(l[i] for _, l in paires)]
    return ([[l[i] for i in gardees] for _, l in paires], [n for n, _ in paires])


def detecter_entete(grille: List[List[str]]) -> int:
    """Index de la ligne d'entete dans une grille normalisee.

    Une ligne d'entete se reconnait a ceci : ses cellules non vides sont du
    TEXTE, et la ligne suivante contient au moins un nombre. Un fichier sans
    entete du tout (des codes des la premiere ligne) rend -1 plutot que de
    sacrifier sa premiere bobine.
    """
    for i, ligne in enumerate(grille[: min(len(grille), 10)]):
        pleines = [c for c in ligne if c]
        if len(pleines) < 2:
            continue
        if any(_nombre(c) is not None for c in pleines):
            continue
        suivante = grille[i + 1] if i + 1 < len(grille) else []
        if any(_nombre(c) is not None for c in suivante if c):
            return i
    return -1


# ── Proposition de correspondance ────────────────────────────────────────────

# Mots qui designent chaque role, du plus specifique au plus vague. L'ordre
# compte : « roll » avant « batch » parce que « roll batch number » est un
# identifiant de bobine, et que l'inverse ferait entrer 49 bobines sous un
# seul code.
_MOTS = {
    "code": ["roll number", "roll no", "roll id", "roll batch", "roll",
             "code barre", "codebarre", "barcode", "bobine", "reel",
             "serial", "code", "numero bobine", "no bobine"],
    "laize": ["width", "laize", "largeur", "breite", "larghezza"],
    "metrage": ["length", "longueur", "metrage", "metres", "meter", "metre",
                "running", "ml", "lm", "lfm"],
    "lot": ["lot number", "lot no", "batch number", "batch no", "lot",
            "batch", "charge"],
}

# Unites lues dans le titre de la colonne — `width(MM)`, `length(M)`.
_UNITES_LAIZE = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "inch": 25.4, "in": 25.4}
_UNITES_METRAGE = {"m": 1.0, "km": 1000.0, "ml": 1.0, "lm": 1.0, "yd": 0.9144}


def _unite_dans_entete(entete: str, table: Dict[str, float]) -> Optional[str]:
    m = re.search(r"[\(\[]\s*([a-zA-Z]{1,4})\s*[\)\]]", str(entete or ""))
    if m:
        u = m.group(1).lower()
        if u in table:
            return u
    mots = _norm(entete).split()
    for u in table:
        if u in mots:
            return u
    return None


def _score_entete(entete: str, role: str) -> int:
    """Plus le mot trouve est specifique, plus le score est haut. 0 = aucun."""
    n = _norm(entete)
    if not n:
        return 0
    for rang, mot in enumerate(_MOTS[role]):
        if mot in n:
            return len(_MOTS[role]) - rang
    return 0


def _profil_colonne(valeurs: List[str]) -> Dict[str, Any]:
    nombres = [_nombre(v) for v in valeurs if v]
    nombres = [n for n in nombres if n is not None]
    remplies = [v for v in valeurs if v]
    return {
        "nb": len(remplies),
        "distinctes": len(set(remplies)),
        "part_numerique": (len(nombres) / len(remplies)) if remplies else 0.0,
        "median": sorted(nombres)[len(nombres) // 2] if nombres else None,
    }


def proposer_mapping(entetes: List[str], colonnes: List[List[str]]) -> Dict[str, Any]:
    """Correspondance proposee — jamais imposee, toujours revue par un humain.

    L'entete decide en premier. Quand il ne dit rien (fichier sans titres, ou
    titres dans une langue non prevue), la FORME des valeurs tranche : une
    colonne de nombres entre 20 et 2 500 tous identiques a quelques valeurs
    pres est une laize ; une colonne de nombres bien plus grands est un
    metrage ; une colonne dont presque toutes les valeurs sont distinctes est
    un identifiant de bobine.
    """
    profils = [_profil_colonne(c) for c in colonnes]
    prop: Dict[str, Any] = {"code": None, "laize": None, "metrage": None, "lot": None,
                            "unite_laize": None, "unite_metrage": None,
                            "confiance": {}}
    pris = set()

    for role in ("code", "laize", "metrage", "lot"):
        meilleur, meilleur_score = None, 0
        for i, e in enumerate(entetes):
            if i in pris:
                continue
            s = _score_entete(e, role)
            if s > meilleur_score:
                meilleur, meilleur_score = i, s
        if meilleur is not None:
            prop[role] = entetes[meilleur]
            prop["confiance"][role] = "entete"
            pris.add(meilleur)

    # Repli sur la forme des valeurs, uniquement pour ce que l'entete n'a pas dit.
    if prop["laize"] is None:
        for i, p in enumerate(profils):
            if i in pris or p["part_numerique"] < 0.9 or p["median"] is None:
                continue
            if LAIZE_MIN_MM <= p["median"] <= LAIZE_MAX_MM and p["distinctes"] <= max(12, p["nb"] // 3):
                prop["laize"] = entetes[i]
                prop["confiance"]["laize"] = "valeurs"
                pris.add(i)
                break
    if prop["metrage"] is None:
        candidats = [(i, p) for i, p in enumerate(profils)
                     if i not in pris and p["part_numerique"] >= 0.9 and p["median"]
                     and p["median"] > LAIZE_MAX_MM]
        if candidats:
            i = max(candidats, key=lambda c: c[1]["median"])[0]
            prop["metrage"] = entetes[i]
            prop["confiance"]["metrage"] = "valeurs"
            pris.add(i)
    if prop["code"] is None:
        candidats = [(i, p) for i, p in enumerate(profils)
                     if i not in pris and p["nb"] and p["distinctes"] >= 0.9 * p["nb"]]
        if candidats:
            i = max(candidats, key=lambda c: c[1]["distinctes"])[0]
            prop["code"] = entetes[i]
            prop["confiance"]["code"] = "valeurs"
            pris.add(i)

    if prop["laize"]:
        prop["unite_laize"] = _unite_dans_entete(prop["laize"], _UNITES_LAIZE) or "mm"
    if prop["metrage"]:
        prop["unite_metrage"] = _unite_dans_entete(prop["metrage"], _UNITES_METRAGE) or "m"
    return prop


# ── Analyse et extraction ────────────────────────────────────────────────────

def analyser(lignes: Sequence[Sequence[Any]]) -> Dict[str, Any]:
    """Ce qu'on peut dire d'un fichier avant que quiconque ait rien valide."""
    grille, numeros = normaliser_grille(lignes)
    if not grille:
        raise ValueError("Fichier vide.")
    i_entete = detecter_entete(grille)
    if i_entete < 0:
        entetes = ["Colonne %d" % (i + 1) for i in range(len(grille[0]))]
        donnees = grille
    else:
        entetes = [c or ("Colonne %d" % (i + 1)) for i, c in enumerate(grille[i_entete])]
        donnees = grille[i_entete + 1:]
    if not donnees:
        raise ValueError("Aucune ligne de donnees sous l'entete.")

    colonnes = [[l[i] if i < len(l) else "" for l in donnees] for i in range(len(entetes))]
    return {
        "entetes": entetes,
        # Le numero dans le FICHIER, pas dans la grille compactee : les lignes
        # vides d'en tete decalent les deux, et c'est le fichier que l'humain a
        # sous les yeux.
        "entete_ligne": numeros[i_entete] if i_entete >= 0 else 0,
        "nb_lignes": len(donnees),
        "apercu": [dict(zip(entetes, l)) for l in donnees[:APERCU]],
        "proposition": proposer_mapping(entetes, colonnes),
    }


def extraire(lignes: Sequence[Sequence[Any]], mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Bobines lues dans le fichier, selon la correspondance validee.

    Rend TOUJOURS les deux : les lignes retenues et celles refusees, avec leur
    numero dans le fichier et le motif. Une ligne perdue en silence, c'est une
    bobine qui manquera a l'inventaire dans six mois sans que personne puisse
    remonter a la cause.
    """
    col_code = (mapping or {}).get("code")
    if not col_code:
        raise ValueError("La colonne du code-barres est obligatoire.")
    col_laize = (mapping or {}).get("laize")
    col_metrage = (mapping or {}).get("metrage")
    col_lot = (mapping or {}).get("lot")
    f_laize = _UNITES_LAIZE.get((mapping.get("unite_laize") or "mm").lower(), 1.0)
    f_metrage = _UNITES_METRAGE.get((mapping.get("unite_metrage") or "m").lower(), 1.0)

    grille, numeros = normaliser_grille(lignes)
    if not grille:
        raise ValueError("Fichier vide.")
    i_entete = detecter_entete(grille)
    entetes = ([c or ("Colonne %d" % (i + 1)) for i, c in enumerate(grille[i_entete])]
               if i_entete >= 0 else ["Colonne %d" % (i + 1) for i in range(len(grille[0]))])
    depart_idx = i_entete + 1 if i_entete >= 0 else 0
    donnees = grille[depart_idx:]
    numeros_donnees = numeros[depart_idx:]

    def _idx(nom):
        return entetes.index(nom) if nom in entetes else None

    i_code, i_laize = _idx(col_code), _idx(col_laize)
    i_metrage, i_lot = _idx(col_metrage), _idx(col_lot)
    if i_code is None:
        raise ValueError("Colonne « %s » absente du fichier." % col_code)

    retenues: List[Dict[str, Any]] = []
    refusees: List[Dict[str, Any]] = []
    vus: Dict[str, int] = {}

    for n, ligne in zip(numeros_donnees, donnees):
        code = (ligne[i_code] if i_code < len(ligne) else "").strip().upper()
        if not code:
            refusees.append({"ligne": n, "motif": "code-barres vide"})
            continue
        if code in vus:
            refusees.append({"ligne": n, "code_barre": code,
                             "motif": "code deja present ligne %d du fichier" % vus[code]})
            continue

        laize = metrage = None
        if i_laize is not None and i_laize < len(ligne):
            v = _nombre(ligne[i_laize])
            if v is not None:
                laize = round(v * f_laize, 2)
                if not (LAIZE_MIN_MM <= laize <= LAIZE_MAX_MM):
                    refusees.append({"ligne": n, "code_barre": code,
                                     "motif": "laize hors plage : %g mm" % laize})
                    continue
        if i_metrage is not None and i_metrage < len(ligne):
            v = _nombre(ligne[i_metrage])
            if v is not None and v > 0:
                metrage = round(v * f_metrage, 2)

        vus[code] = n
        retenues.append({
            "ligne": n,
            "code_barre": code,
            "laize_mm": laize,
            "metrage_m": metrage,
            "lot_fournisseur": ((ligne[i_lot] if i_lot is not None and i_lot < len(ligne) else "") or None),
        })

    laizes: Dict[Any, int] = {}
    for r in retenues:
        laizes[r["laize_mm"]] = laizes.get(r["laize_mm"], 0) + 1
    return {
        "lignes": retenues,
        "refusees": refusees,
        "nb": len(retenues),
        "sans_metrage": sum(1 for r in retenues if r["metrage_m"] is None),
        "sans_laize": sum(1 for r in retenues if r["laize_mm"] is None),
        "metrage_total": round(sum(r["metrage_m"] or 0 for r in retenues), 1),
        "par_laize": sorted(
            ({"laize_mm": k, "nb": v} for k, v in laizes.items()),
            key=lambda d: (d["laize_mm"] is None, d["laize_mm"] or 0),
        ),
    }


# ── Profils par fournisseur ──────────────────────────────────────────────────

_CHAMPS_PROFIL = ("colonne_code", "colonne_laize", "colonne_metrage",
                  "colonne_lot", "unite_laize", "unite_metrage")


def profil(conn, fournisseur_id: Optional[int],
           fournisseur_nom: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Correspondance deja validee pour ce fournisseur, si elle existe.

    L'id prime sur le nom : renommer un fournisseur dans l'annuaire ne doit pas
    lui faire perdre son profil. Le nom reste le repli pour les receptions
    saisies avant que l'annuaire ne soit branche.
    """
    row = None
    if fournisseur_id:
        row = conn.execute(
            "SELECT * FROM stock_packing_profils WHERE fournisseur_id=?",
            (int(fournisseur_id),),
        ).fetchone()
    if row is None and fournisseur_nom:
        row = conn.execute(
            "SELECT * FROM stock_packing_profils "
            " WHERE fournisseur_id IS NULL AND UPPER(IFNULL(fournisseur_nom,''))=? ",
            (fournisseur_nom.strip().upper(),),
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return {
        "code": d.get("colonne_code"),
        "laize": d.get("colonne_laize"),
        "metrage": d.get("colonne_metrage"),
        "lot": d.get("colonne_lot"),
        "unite_laize": d.get("unite_laize"),
        "unite_metrage": d.get("unite_metrage"),
        "fournisseur_nom": d.get("fournisseur_nom"),
        "updated_at": d.get("updated_at"),
    }


def enregistrer_profil(conn, *, fournisseur_id: Optional[int],
                       fournisseur_nom: Optional[str],
                       mapping: Dict[str, Any], fichier: Optional[str] = None,
                       auteur: Optional[str] = None) -> None:
    """Memorise la correspondance validee. Ne commit pas."""
    if not (fournisseur_id or (fournisseur_nom or "").strip()):
        return
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    valeurs = {
        "colonne_code": mapping.get("code"),
        "colonne_laize": mapping.get("laize"),
        "colonne_metrage": mapping.get("metrage"),
        "colonne_lot": mapping.get("lot"),
        "unite_laize": mapping.get("unite_laize"),
        "unite_metrage": mapping.get("unite_metrage"),
    }
    existant = None
    if fournisseur_id:
        existant = conn.execute(
            "SELECT id FROM stock_packing_profils WHERE fournisseur_id=?",
            (int(fournisseur_id),)).fetchone()
    elif fournisseur_nom:
        existant = conn.execute(
            "SELECT id FROM stock_packing_profils "
            " WHERE fournisseur_id IS NULL AND UPPER(IFNULL(fournisseur_nom,''))=?",
            (fournisseur_nom.strip().upper(),)).fetchone()

    if existant:
        conn.execute(
            "UPDATE stock_packing_profils SET %s, exemple_fichier=?, updated_at=?, "
            "updated_by_name=? WHERE id=?" % ", ".join("%s=?" % c for c in _CHAMPS_PROFIL),
            [valeurs[c] for c in _CHAMPS_PROFIL] + [fichier, now, auteur, existant["id"]],
        )
    else:
        conn.execute(
            "INSERT INTO stock_packing_profils "
            "(fournisseur_id, fournisseur_nom, %s, exemple_fichier, created_at, "
            " updated_at, updated_by_name) VALUES (?,?,%s,?,?,?,?)"
            % (", ".join(_CHAMPS_PROFIL), ",".join("?" for _ in _CHAMPS_PROFIL)),
            [fournisseur_id, (fournisseur_nom or "").strip() or None]
            + [valeurs[c] for c in _CHAMPS_PROFIL] + [fichier, now, now, auteur],
        )


# ── Lecture du fichier ───────────────────────────────────────────────────────

def lire_fichier(contenu: bytes, nom: str) -> List[List[Any]]:
    """Grille brute d'un .xlsx / .xls / .csv — SANS supposer que la premiere
    ligne est l'entete.

    C'est toute la difference avec `database.parse_file`, qui lit avec
    `header=0`. Sur la premiere liste reelle, la ligne 1 est vide : pandas
    nommait donc les colonnes « Unnamed: 0 » et promouvait « roll batch number »
    en donnee. On lit tout en brut, et `detecter_entete` tranche ensuite.
    """
    import io as _io

    import pandas as pd

    ext = (nom or "").lower().rsplit(".", 1)[-1] if "." in (nom or "") else ""
    if ext in ("xls", "xlsx", "xlsm"):
        df = pd.read_excel(_io.BytesIO(contenu), header=None, dtype=str)
    elif ext in ("csv", "txt", "tsv"):
        meilleur = None
        for encodage in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            for sep in (";", ",", "\t"):
                try:
                    essai = pd.read_csv(_io.BytesIO(contenu), header=None, dtype=str,
                                        sep=sep, encoding=encodage,
                                        engine="python", on_bad_lines="skip")
                except Exception:
                    continue
                if meilleur is None or essai.shape[1] > meilleur.shape[1]:
                    meilleur = essai
            if meilleur is not None and meilleur.shape[1] > 1:
                break
        if meilleur is None:
            raise ValueError("Fichier CSV illisible.")
        df = meilleur
    else:
        raise ValueError("Format non supporte : .%s — attendu .xlsx, .xls ou .csv." % ext)
    return df.values.tolist()
