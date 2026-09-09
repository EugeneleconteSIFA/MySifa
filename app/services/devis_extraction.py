"""
SIFA — Extraction des indicateurs d'un devis, quel qu'en soit l'auteur.

Le problème. Chaque commercial devise à sa façon : le modèle maison a une
feuille « Calculs » et une feuille « Prix » aux libellés connus, mais les
autres classeurs déplacent les libellés, les renomment, changent d'unité, ou
n'existent qu'en PDF ou en photo d'un tirage papier. Un parser à motifs ne
peut pas suivre : il rend des zéros, et un zéro entre en base sans bruit.

La réponse, en deux temps :

1. **Le parser à motifs d'abord** (`devis_parser.parse_devis`). Il est gratuit,
   instantané et suffit pour le modèle maison. On le laisse faire.
2. **L'IA quand il échoue.** Dès qu'un champ clé ressort vide — ou que le
   fichier n'est pas un classeur — le contenu part au modèle, qui rend les
   mêmes champs, PLUS les indicateurs que le socle ne prévoit pas, chacun
   accompagné de sa source (« Calculs!I2 », « page 2 ») et d'un niveau de
   confiance.

Rien n'entre en base sans validation humaine : ce module ne fait que proposer.
L'écran de validation de MyProd affiche valeur, provenance et confiance, et
c'est Eugène qui tranche. C'est le seul moyen honnête de faire lire un devis
par une machine : on montre d'où vient chaque chiffre.

CE MODULE NE DEVINE JAMAIS. Un champ absent du fichier reste absent — il ne
prend ni zéro, ni valeur « raisonnable ». Un zéro inventé dans un devis, c'est
un écart de rentabilité fantôme trois mois plus tard.
"""
import base64
import io
import json
import os
import re
from typing import Any, Optional

from config import (
    DEVIS_IA_ACTIVE,
    DEVIS_IA_MAX_CARACTERES,
    DEVIS_IA_MAX_TOKENS,
    DEVIS_IA_MODELE,
    DEVIS_EXTENSIONS_EXCEL,
    DEVIS_EXTENSIONS_IMAGE,
    DEVIS_FEUILLES_PRIORITAIRES,
    DEVIS_TOLERANCE_COHERENCE,
)
from services.devis_parser import (
    CHAMPS_NUMERIQUES,
    champ_vide,
    champs_cles_manquants,
    charger_feuilles,
    gabarit_devis,
    parse_devis,
)

# Libellés affichés dans l'écran de validation. Ils servent aussi de
# vocabulaire au modèle : c'est cette liste, et elle seule, qui définit le
# socle comparable devis/réel.
CHAMPS_SOCLE = {
    "client":                ("Client",                  "texte", ""),
    "date_devis":            ("Date du devis",           "texte", "AAAA-MM-JJ"),
    "format_h":              ("Format hauteur",          "nombre", "mm"),
    "format_v":              ("Format laize",            "nombre", "mm"),
    "laize":                 ("Laize production",        "nombre", "mm"),
    "nb_couleurs":           ("Nombre de couleurs",      "nombre", ""),
    "temps_calage_mn":       ("Temps de calage outil",   "nombre", "mn"),
    "metrage_calage_ml":     ("Métrage de calage outil", "nombre", "ml"),
    "temps_calage_impression_mn":   ("Temps de calage impression",   "nombre", "mn"),
    "metrage_calage_impression_ml": ("Métrage de calage impression", "nombre", "ml"),
    "temps_production_mn":   ("Temps de production",     "nombre", "mn"),
    "metrage_production_ml": ("Métrage de production",   "nombre", "ml"),
    "vitesse_theorique":     ("Vitesse devisée",         "nombre", "m/mn"),
    "qte_etiquettes":        ("Quantité d'étiquettes",   "nombre", "ex"),
    "gache":                 ("Gâche",                   "nombre", "fraction (0,05 = 5 %)"),
}


# ══════════════════════════════════════════════════════════════════
# Mise en forme du fichier pour le modèle
# ══════════════════════════════════════════════════════════════════

def _lettre_colonne(idx: int) -> str:
    lettre = ""
    idx += 1
    while idx:
        idx, reste = divmod(idx - 1, 26)
        lettre = chr(65 + reste) + lettre
    return lettre


def _rang_feuille(nom: str) -> int:
    """0 = feuille utile, 1 = le reste.

    Un classeur de devis embarque ses référentiels : la feuille « Matière »
    fait 1 488 lignes, « Base_matières » 401. Les envoyer noierait les vingt
    cellules qui portent le devis, et coûterait cher pour rien.
    """
    bas = (nom or "").lower()
    return 0 if any(mot in bas for mot in DEVIS_FEUILLES_PRIORITAIRES) else 1


def texte_classeur(file_bytes: bytes, filename: str,
                   budget: Optional[int] = None) -> tuple[str, list[str]]:
    """Aplatit un classeur en « Feuille!Cellule: valeur », feuilles utiles d'abord.

    La coordonnée est indispensable : sans elle le modèle ne peut pas citer sa
    source, et une valeur sans source n'est pas vérifiable.
    """
    budget = budget or DEVIS_IA_MAX_CARACTERES
    feuilles, erreurs = charger_feuilles(file_bytes, filename)
    if not feuilles:
        return "", erreurs

    noms = sorted(feuilles.keys(), key=lambda n: (_rang_feuille(n), n))
    morceaux: list[str] = []
    total = 0
    for nom in noms:
        df = feuilles[nom]
        plafond = 1500 if _rang_feuille(nom) == 0 else 80
        lignes: list[str] = []
        for r in range(len(df)):
            for c in range(len(df.columns)):
                val = df.iloc[r, c]
                try:
                    vide = val is None or (val != val)  # NaN != NaN
                except Exception:
                    vide = val is None
                if vide:
                    continue
                txt = str(val).strip()
                if not txt:
                    continue
                lignes.append(f"{_lettre_colonne(c)}{r + 1}: {txt}")
                if len(lignes) >= plafond:
                    break
            if len(lignes) >= plafond:
                break
        if not lignes:
            continue
        bloc = f"### Feuille « {nom} »\n" + "\n".join(lignes)
        if total + len(bloc) > budget:
            morceaux.append(f"### Feuille « {nom} » — non transmise (budget atteint)")
            break
        morceaux.append(bloc)
        total += len(bloc)
    return "\n\n".join(morceaux), erreurs


def _texte_pdf(file_bytes: bytes, budget: int) -> str:
    """Texte d'un PDF natif. Rend une chaîne vide si le PDF est un scan."""
    try:
        import pdfplumber
    except Exception:
        return ""
    morceaux: list[str] = []
    total = 0
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                txt = (page.extract_text() or "").strip()
                if not txt:
                    continue
                bloc = f"### Page {i}\n{txt}"
                if total + len(bloc) > budget:
                    break
                morceaux.append(bloc)
                total += len(bloc)
    except Exception:
        return ""
    return "\n\n".join(morceaux)


def _type_fichier(filename: str, content_type: str = "") -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""
    if ext in DEVIS_EXTENSIONS_EXCEL:
        return "excel"
    if ext == "pdf" or "pdf" in (content_type or ""):
        return "pdf"
    if ext in DEVIS_EXTENSIONS_IMAGE or (content_type or "").startswith("image/"):
        return "image"
    return "inconnu"


def _mime_image(filename: str, content_type: str = "") -> str:
    if (content_type or "").startswith("image/"):
        return content_type
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")


# ══════════════════════════════════════════════════════════════════
# Appel du modèle
# ══════════════════════════════════════════════════════════════════

_OUTIL = {
    "name": "enregistrer_devis",
    "description": "Enregistre les indicateurs lus dans le devis, avec leur source.",
    "input_schema": {
        "type": "object",
        "properties": {
            "champs": {
                "type": "array",
                "description": "Un élément par indicateur du socle EFFECTIVEMENT trouvé. Ne rien émettre pour un indicateur absent.",
                "items": {
                    "type": "object",
                    "properties": {
                        "cle": {"type": "string", "enum": list(CHAMPS_SOCLE.keys())},
                        "valeur_nombre": {"type": "number"},
                        "valeur_texte": {"type": "string"},
                        "source": {"type": "string", "description": "Feuille!Cellule (ex. Calculs!I2) ou « page 2 »."},
                        "confiance": {"type": "string", "enum": ["haute", "moyenne", "basse"]},
                        "commentaire": {"type": "string", "description": "Pourquoi cette cellule et pas une autre, si le fichier en propose plusieurs."},
                    },
                    "required": ["cle", "source", "confiance"],
                },
            },
            "indicateurs": {
                "type": "array",
                "description": "Les autres indicateurs chiffrés du devis, hors socle : nombre de fronts, poses, métrage total, prix au mille, nombre de bobines, temps de conditionnement, etc.",
                "items": {
                    "type": "object",
                    "properties": {
                        "libelle": {"type": "string", "description": "Le libellé tel qu'il est écrit dans le fichier."},
                        "valeur_nombre": {"type": "number"},
                        "valeur_texte": {"type": "string"},
                        "unite": {"type": "string"},
                        "source": {"type": "string"},
                        "confiance": {"type": "string", "enum": ["haute", "moyenne", "basse"]},
                    },
                    "required": ["libelle", "source", "confiance"],
                },
            },
            "remarques": {
                "type": "string",
                "description": "Ce qui a demandé un arbitrage, ou ce qui reste douteux. Une ou deux phrases.",
            },
        },
        "required": ["champs"],
    },
}

_CONSIGNE = """Tu lis un devis de fabrication d'étiquettes adhésives et tu en extrais les indicateurs de production.

Chaque commercial devise à sa manière : libellés différents, feuilles différentes, unités différentes. Tu lis ce qui est écrit, tu ne transposes pas un modèle appris.

Règles, sans exception :

1. N'INVENTE RIEN. Un indicateur absent du fichier n'est pas émis. Ne le remplace ni par zéro, ni par une valeur plausible, ni par un calcul de ton cru. Un chiffre inventé fausse une comparaison de rentabilité des mois plus tard.
2. CITE TA SOURCE pour chaque valeur. Classeur : « Feuille!Cellule », exactement comme dans les données fournies (ex. « Calculs!I2 »). PDF ou image : « page 2 », et le libellé lu.
3. LA VITESSE DEVISÉE est la vitesse de production retenue POUR CE DEVIS, en m/mn. Un fichier en contient souvent plusieurs (théorique, réelle, de conditionnement, de la machine). Retiens celle qui vérifie « métrage de production ≈ vitesse × temps de production », et explique ton choix dans `commentaire`. Si aucune ne le vérifie, prends la plus explicite et baisse la confiance à « moyenne » ou « basse ».
4. UNITÉS. Temps en minutes (une valeur en heures est convertie, et tu le dis dans `commentaire`). Métrages en mètres linéaires. Vitesse en m/mn. Gâche en fraction : 5 % s'écrit 0.05.
5. CONFIANCE. « haute » = le libellé est explicite et la valeur cohérente avec le reste. « moyenne » = déduit d'un libellé approchant, ou plusieurs candidats. « basse » = lecture incertaine, notamment sur photo ou scan.
6. LE CALAGE SE DÉCOMPOSE EN DEUX POSTES, à ne jamais additionner entre eux ni avec la production. « temps_calage_mn » est le calage OUTIL (montage de l'outil de découpe). « temps_calage_impression_mn » est le calage IMPRESSION (mises en route couleurs et clichés, changements de couleur). Si le devis ne distingue pas les deux, mets tout dans le calage outil et dis-le dans `commentaire` — ne répartis pas au jugé.
7. Dans `indicateurs`, mets tout le reste de chiffré et d'utile — nombre de fronts, poses, métrage total, prix au mille, nombre de bobines, quantité par rouleau, temps de conditionnement. Garde le libellé du fichier, pas une traduction.

Appelle l'outil `enregistrer_devis`. Aucun texte libre en dehors de l'outil."""


def _client_anthropic():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        return None
    try:
        import anthropic
    except Exception:
        return None
    return anthropic.Anthropic(api_key=cle)


def _rappel_deja_lu(indicateurs: list) -> str:
    """Ce que la lecture directe a déjà relevé, pour ne pas le faire redire.

    Sans ce rappel, le modèle réémet « NOMBRE FRONT » là où le motif a déjà
    posé « Nombre de fronts » : même chiffre, deux libellés, et un écran de
    validation qui donne l'impression que la machine hésite.
    """
    libelles = [i.get("libelle") for i in (indicateurs or []) if i.get("libelle")]
    if not libelles:
        return ""
    return ("\n\nIndicateurs DÉJÀ relevés par la lecture directe — ne les remets "
            "pas dans `indicateurs`, cherche ce qui manque :\n- "
            + "\n- ".join(libelles))


def _blocs_contenu(file_bytes: bytes, filename: str, content_type: str,
                   type_fichier: str, deja_lu: str = "") -> tuple[list[dict], list[str]]:
    """Construit les blocs de message envoyés au modèle."""
    avertissements: list[str] = []
    budget = DEVIS_IA_MAX_CARACTERES

    if type_fichier == "excel":
        texte, erreurs = texte_classeur(file_bytes, filename, budget)
        avertissements.extend(erreurs)
        if not texte:
            return [], avertissements
        return [{"type": "text",
                 "text": f"Fichier : {filename}\n\n{texte}{deja_lu}"}], avertissements

    if type_fichier == "pdf":
        texte = _texte_pdf(file_bytes, budget)
        if texte:
            return [{"type": "text",
                     "text": f"Fichier : {filename}\n\n{texte}{deja_lu}"}], avertissements
        # PDF sans couche texte : c'est un scan, il part tel quel au modèle,
        # qui en lit les pages comme des images.
        avertissements.append("PDF sans texte : lu comme un document numérisé.")
        return [{
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf",
                       "data": base64.standard_b64encode(file_bytes).decode()},
        }, {"type": "text", "text": f"Fichier : {filename}{deja_lu}"}], avertissements

    if type_fichier == "image":
        return [{
            "type": "image",
            "source": {"type": "base64",
                       "media_type": _mime_image(filename, content_type),
                       "data": base64.standard_b64encode(file_bytes).decode()},
        }, {"type": "text", "text": f"Fichier : {filename}{deja_lu}"}], avertissements

    return [], ["Format de fichier non reconnu."]


def _appel_modele(blocs: list[dict]) -> tuple[Optional[dict], Optional[str], str]:
    """Rend `(resultat, erreur, modele)`."""
    client = _client_anthropic()
    if client is None:
        return None, "Clé ANTHROPIC_API_KEY absente : extraction IA indisponible.", ""
    modele = DEVIS_IA_MODELE
    try:
        reponse = client.messages.create(
            model=modele,
            max_tokens=DEVIS_IA_MAX_TOKENS,
            system=_CONSIGNE,
            tools=[_OUTIL],
            tool_choice={"type": "tool", "name": "enregistrer_devis"},
            messages=[{"role": "user", "content": blocs}],
        )
    except Exception as e:
        return None, f"Appel au modèle en échec : {e}", modele

    for bloc in reponse.content:
        if getattr(bloc, "type", "") == "tool_use":
            entree = bloc.input
            if isinstance(entree, str):
                try:
                    entree = json.loads(entree)
                except Exception:
                    return None, "Réponse du modèle illisible.", modele
            return entree, None, modele
    return None, "Le modèle n'a pas rendu d'extraction.", modele


# ══════════════════════════════════════════════════════════════════
# Normalisation et cohérence
# ══════════════════════════════════════════════════════════════════

def _valeur_champ(item: dict, cle: str):
    nature = CHAMPS_SOCLE.get(cle, ("", "texte", ""))[1]
    if nature == "nombre":
        v = item.get("valeur_nombre")
        if v is None and item.get("valeur_texte") not in (None, ""):
            try:
                v = float(str(item["valeur_texte"]).replace(",", ".").strip())
            except ValueError:
                v = None
        return v
    v = item.get("valeur_texte")
    if v in (None, "") and item.get("valeur_nombre") is not None:
        v = str(item["valeur_nombre"])
    return v


def _normaliser_gache(valeur):
    """5 devient 0,05. Le socle stocke une fraction ; un commercial écrit « 5 % »."""
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return valeur
    return v / 100.0 if v > 1 else v


def _fmt(n) -> str:
    """12345.6 → « 12 346 ». Espace fine insécable exclue : le HTML la mange."""
    try:
        return f"{float(n):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def _indicateur(indicateurs: list, libelle: str):
    for i in (indicateurs or []):
        if (i.get("libelle") or "").strip().lower() == libelle.lower():
            return i.get("valeur_nombre")
    return None


# « 29.000.000 », « 984.000 » : la quantité que le commercial met dans le nom
# du fichier. Groupes de trois chiffres séparés par des points, uniquement —
# une date compacte (16062025) ou un format (148x210) ne peut pas correspondre.
# Pas de `\b` : le souligné EST un caractère de mot, donc `\b` ne se déclenche
# pas dans « ..._29.000.000_16062025.xlsx » — exactement les noms de fichiers
# que les commerciaux écrivent. On borne sur « pas un chiffre » à la place.
_RE_QTE_NOM_FICHIER = re.compile(r"(?<!\d)\d{1,3}(?:\.\d{3}){1,4}(?!\d)")


def _controles_paliers(donnees: dict, paliers: list) -> list[dict]:
    """Vérifie sur QUELLE quantité les temps du devis ont été calculés.

    Un devis chiffre plusieurs quantités, mais n'en calcule le temps et le
    métrage que pour une seule. Si le dossier produit correspond à une autre,
    la comparaison devis/réel compare deux affaires différentes — et rien dans
    le classeur ne le signale. Ces contrôles ne choisissent pas : ils posent
    la question avec les chiffres sous les yeux.
    """
    if not paliers:
        return []
    alertes: list[dict] = []
    qte_calc = float(donnees.get("qte_etiquettes") or 0)
    quantites = [float(p.get("quantite") or 0) for p in paliers]

    if len(paliers) > 1:
        detail = " ; ".join(
            f"{_fmt(p['quantite'])} ex"
            + (" à " + f"{p['prix_mille']:.2f}".replace(".", ",") + " €/mille"
               if p.get("prix_mille") else "")
            for p in paliers
        )
        alertes.append({
            "niveau": "info",
            "champs": ["qte_etiquettes"],
            "message": (
                f"Le devis chiffre {len(paliers)} quantités ({detail}). Les temps et "
                f"métrages ci-dessous sont calculés pour {_fmt(qte_calc)} ex. "
                "Vérifier que c'est bien la quantité du dossier."
            ),
        })

    if qte_calc > 0 and not any(abs(q - qte_calc) < 1 for q in quantites):
        alertes.append({
            "niveau": "info",
            "champs": ["qte_etiquettes"],
            "message": (
                f"La quantité des calculs ({_fmt(qte_calc)} ex) ne figure dans aucun "
                f"palier proposé ({', '.join(_fmt(q) for q in quantites)}). "
                "Le devis a pu être recalculé après la proposition de prix."
            ),
        })

    # Le nom du fichier porte souvent la quantité commandée. Quand ce nombre
    # correspond à un palier AUTRE que celui des calculs, ce n'est pas une
    # coïncidence : le devis a été calculé pour une quantité différente.
    nom = str(donnees.get("filename") or "")
    for brut in _RE_QTE_NOM_FICHIER.findall(nom):
        val = float(brut.replace(".", ""))
        if qte_calc > 0 and abs(val - qte_calc) < 1:
            continue
        if any(abs(q - val) < 1 for q in quantites):
            alertes.append({
                "niveau": "avertissement",
                "champs": ["qte_etiquettes"],
                "message": (
                    f"Le nom du fichier annonce {_fmt(val)} ex, qui est bien un palier "
                    f"du devis — mais les temps sont calculés pour {_fmt(qte_calc)} ex. "
                    "Comparer la production réelle à ces temps fausserait l'écart."
                ),
            })
            break
    return alertes


def controles_coherence(donnees: dict, indicateurs: Optional[list] = None,
                        paliers: Optional[list] = None) -> list[dict]:
    """Les vérifications qu'un chef de production ferait de tête.

    Elles ne corrigent rien : elles montrent ce qui ne tient pas debout, pour
    que la valeur soit revue AVANT d'entrer en base.
    """
    # La quantité de référence passe en premier : si elle est en cause, tout
    # le reste de la comparaison porte sur la mauvaise affaire.
    alertes: list[dict] = _controles_paliers(donnees, paliers or [])
    tol = DEVIS_TOLERANCE_COHERENCE

    v = donnees.get("vitesse_theorique") or 0
    t = donnees.get("temps_production_mn") or 0
    m = donnees.get("metrage_production_ml") or 0
    if v > 0 and t > 0 and m > 0:
        attendu = v * t
        ecart = abs(attendu - m) / m
        if ecart > tol:
            alertes.append({
                "niveau": "avertissement",
                "champs": ["vitesse_theorique", "temps_production_mn", "metrage_production_ml"],
                "message": (
                    f"Vitesse × temps = {_fmt(attendu)} ml, mais le métrage devisé est "
                    f"{_fmt(m)} ml — {ecart * 100:.0f} % d'écart. L'un des trois est mal lu."
                ),
            })
    elif v > 0 and t > 0 and m == 0:
        alertes.append({
            "niveau": "info",
            "champs": ["metrage_production_ml"],
            "message": f"Métrage de production absent. Vitesse × temps donnerait {_fmt(v * t)} ml.",
        })

    # Le calage devisé se paie en DEUX postes dans le modèle maison : le
    # calage outil (« temps_calage_mn ») et le calage impression, porté à part.
    # Sur le devis RIFO : 180 mn d'outil + 67,5 mn d'impression. Comparer un
    # calage réel d'atelier — qui couvre tout le réglage — au seul poste outil
    # fait perdre 37 % à la comparaison sans qu'aucun chiffre soit faux.
    calage_impr = float(donnees.get("temps_calage_impression_mn") or 0)
    calage_outil = donnees.get("temps_calage_mn") or 0
    if calage_impr > 0 and calage_outil > 0:
        alertes.append({
            "niveau": "info",
            "champs": ["temps_calage_mn", "temps_calage_impression_mn"],
            "message": (
                f"Calage devisé : {_fmt(calage_outil)} mn d'outil + "
                f"{_fmt(calage_impr)} mn d'impression = "
                f"{_fmt(calage_outil + calage_impr)} mn. C'est ce total que la "
                "comparaison oppose au calage relevé en atelier, qui couvre lui "
                "aussi les changements de couleur et de cliché."
            ),
        })

    if (donnees.get("temps_calage_mn") or 0) > (donnees.get("temps_production_mn") or 0) > 0:
        alertes.append({
            "niveau": "info",
            "champs": ["temps_calage_mn"],
            "message": "Le calage devisé dépasse la production : possible sur une petite série, à confirmer.",
        })

    g = donnees.get("gache")
    if g is not None and g > 0.5:
        alertes.append({
            "niveau": "avertissement",
            "champs": ["gache"],
            "message": f"Gâche à {g:.2f} — la valeur attendue est une fraction (0,05 pour 5 %).",
        })

    for cle in ("temps_production_mn", "metrage_production_ml", "qte_etiquettes",
                "vitesse_theorique", "temps_calage_mn"):
        if champ_vide(donnees.get(cle)):
            alertes.append({
                "niveau": "manquant",
                "champs": [cle],
                "message": f"{CHAMPS_SOCLE[cle][0]} : non trouvé dans le fichier.",
            })
    return alertes


# ══════════════════════════════════════════════════════════════════
# Point d'entrée
# ══════════════════════════════════════════════════════════════════

def extraire_devis(file_bytes: bytes, filename: str, content_type: str = "",
                   forcer_ia: bool = False) -> dict:
    """Lit un devis et rend une proposition à valider.

    Sortie :
      preview      — le socle, mêmes clés que l'ancien parser (compatibilité)
      champs       — {cle: {valeur, libelle, unite, source, confiance, origine, commentaire}}
      indicateurs  — les indicateurs hors socle relevés par l'IA
      coherence    — les alertes à lever avant enregistrement
      methode      — regex | ia | mixte | echec
      modele       — le modèle appelé, s'il l'a été
    """
    type_fichier = _type_fichier(filename, content_type)
    socle = gabarit_devis(filename)
    champs: dict[str, dict] = {}
    indicateurs: list[dict] = []
    paliers: list[dict] = []
    avertissements: list[str] = []
    methode = "regex"

    # ── 1. Le chemin rapide, sur les classeurs uniquement ─────────
    if type_fichier == "excel":
        socle = parse_devis(file_bytes, filename)
        avertissements.extend(socle.get("parse_errors") or [])
        indicateurs.extend(socle.get("indicateurs") or [])
        paliers = socle.get("paliers") or []
        # Les paliers rejoignent les indicateurs pour être conservés en base :
        # savoir, six mois plus tard, que le devis proposait aussi 29 millions
        # à 0,74 € vaut autant que le chiffre retenu.
        for rang, p in enumerate(paliers, start=1):
            indicateurs.append({
                "libelle": f"Quantité proposée (palier {rang})",
                "valeur_nombre": p.get("quantite"),
                "valeur_texte": p.get("note") or "",
                "unite": "ex", "source": p.get("source") or "",
                "confiance": "haute", "origine": "regex",
            })
            if p.get("prix_mille") is not None:
                indicateurs.append({
                    "libelle": f"Prix au mille (palier {rang})",
                    "valeur_nombre": p.get("prix_mille"),
                    "valeur_texte": "", "unite": "€",
                    "source": p.get("source_prix") or p.get("source") or "",
                    "confiance": "haute", "origine": "regex",
                })
        # Un champ LU vaut zéro aussi bien qu'autre chose. Le devis « tabac »
        # porte « NBRE COULEURS : 0 » — c'est la réalité de l'affaire, pas une
        # lecture ratée. Ce qui compte ici est qu'une cellule ait été trouvée
        # (`sources`), jamais la valeur qu'elle contient : afficher « non
        # trouvé » sur un zéro légitime pousserait à corriger une valeur juste.
        confiances = socle.get("confiances") or {}
        for cle, coord in (socle.get("sources") or {}).items():
            libelle, _nature, unite = CHAMPS_SOCLE.get(cle, (cle, "texte", ""))
            conf = confiances.get(cle, "haute")
            champs[cle] = {
                "valeur": socle.get(cle), "libelle": libelle, "unite": unite,
                "source": coord, "confiance": conf, "origine": "regex",
                "commentaire": ("Libellé absent de la feuille : valeur déduite de sa "
                                "position, à contrôler." if conf != "haute" else ""),
            }

    manquants = champs_cles_manquants(socle)
    besoin_ia = forcer_ia or type_fichier != "excel" or bool(manquants)

    # ── 2. L'IA, quand le chemin rapide ne suffit pas ─────────────
    resultat_ia = None
    modele = ""
    if besoin_ia and DEVIS_IA_ACTIVE:
        blocs, avert_blocs = _blocs_contenu(file_bytes, filename, content_type,
                                            type_fichier, _rappel_deja_lu(indicateurs))
        avertissements.extend(avert_blocs)
        if blocs:
            resultat_ia, erreur, modele = _appel_modele(blocs)
            if erreur:
                avertissements.append(erreur)
    elif besoin_ia and not DEVIS_IA_ACTIVE:
        avertissements.append("Extraction IA désactivée (DEVIS_IA_ACTIVE).")

    remarques = ""
    if resultat_ia:
        remarques = (resultat_ia.get("remarques") or "").strip()
        for item in (resultat_ia.get("champs") or []):
            cle = item.get("cle")
            if cle not in CHAMPS_SOCLE:
                continue
            valeur = _valeur_champ(item, cle)
            if valeur is None or valeur == "":
                continue
            if cle == "gache":
                valeur = _normaliser_gache(valeur)
            # Le parser à motifs garde la main quand il a trouvé : il lit la
            # cellule, il ne l'interprète pas. L'IA complète, elle n'écrase pas.
            if cle in champs:
                champs[cle]["confirme_ia"] = True
                if champs[cle].get("source") != item.get("source"):
                    champs[cle]["source_ia"] = item.get("source") or ""
                continue
            libelle, _nature, unite = CHAMPS_SOCLE[cle]
            champs[cle] = {
                "valeur": valeur, "libelle": libelle, "unite": unite,
                "source": item.get("source") or "", "confiance": item.get("confiance") or "moyenne",
                "origine": "ia", "commentaire": item.get("commentaire") or "",
            }
            socle[cle] = valeur

        # Le modèle relit souvent des indicateurs que le motif a déjà relevés :
        # on ne les pose qu'une fois, la lecture directe faisant foi.
        deja = {(i.get("libelle") or "").strip().lower() for i in indicateurs}
        for item in (resultat_ia.get("indicateurs") or []):
            libelle = (item.get("libelle") or "").strip()
            if not libelle or libelle.lower() in deja:
                continue
            deja.add(libelle.lower())
            indicateurs.append({
                "libelle": libelle,
                "valeur_nombre": item.get("valeur_nombre"),
                "valeur_texte": (item.get("valeur_texte") or "").strip(),
                "unite": (item.get("unite") or "").strip(),
                "source": (item.get("source") or "").strip(),
                "confiance": item.get("confiance") or "moyenne",
                "origine": "ia",
            })

        # La méthode décrit ce qui a réellement produit la fiche. Le modèle
        # peut n'avoir rien ajouté au socle et avoir tout de même trouvé des
        # indicateurs : c'est « mixte », pas « regex ».
        origines = {c["origine"] for c in champs.values()}
        origines |= {i.get("origine") for i in indicateurs if i.get("origine")}
        if origines == {"ia"}:
            methode = "ia"
        elif "ia" in origines:
            methode = "mixte"
        else:
            methode = "regex"
    elif besoin_ia:
        methode = "echec" if not champs else "regex"

    # Le socle reste au format historique : les champs numériques non trouvés
    # valent 0 en base, mais `champs` dit lesquels n'ont jamais été lus.
    for cle in CHAMPS_NUMERIQUES:
        if socle.get(cle) is None:
            socle[cle] = 0.0
    socle["filename"] = filename
    # Le socle repart au format historique : la provenance vit dans `champs`,
    # les indicateurs dans leur propre liste.
    socle.pop("sources", None)
    socle.pop("confiances", None)
    socle.pop("indicateurs", None)
    socle.pop("paliers", None)
    socle["parse_errors"] = avertissements

    return {
        "preview": socle,
        "champs": champs,
        "indicateurs": indicateurs,
        "coherence": controles_coherence(socle, indicateurs, paliers),
        "paliers": paliers,
        "methode": methode,
        "modele": modele,
        "remarques": remarques,
        "type_fichier": type_fichier,
        "champs_cles_manquants": champs_cles_manquants(socle),
        "parse_errors": avertissements,
    }
