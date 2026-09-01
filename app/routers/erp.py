"""API ERP — lecture seule du miroir RVGI.

Ouvert à la direction, aux services administration et à l'expédition, en plus
du super administrateur — c'est `ROLES_ERP`. L'expédition y a été ajoutée le
31/08/2026 : sans lecture du miroir, un expéditeur ne peut ni retrouver le BL
qu'il expédie, ni faire compléter un départ par son numéro de commande. La
page `/erp` et les sélecteurs de rattachement de MyExpé en sont les
consommateurs.

Endpoints
---------
  GET /api/erp/meta                    → fraîcheur du miroir, écrans disponibles
  GET /api/erp/tdb/{cle}               → un tableau de bord (adv | direction)
  GET /api/erp/{ecran}/lignes          → liste paginée, filtrée, triée
  GET /api/erp/{ecran}/export          → la vue courante en classeur xlsx
  GET /api/erp/{ecran}/detail/{id}     → toutes les colonnes d'une ligne

Aucun POST, aucun PUT, aucun DELETE — et ce n'est pas une omission : le miroir
est ouvert en `mode=ro` par `app/services/erp_mirror.py`. RVGI est la source,
MySifa lit. Le jour où l'on voudra écrire, ce sera un autre chantier, avec
l'accord de l'éditeur de l'ERP.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.services import erp_catalogue as catalogue
from app.services import erp_export as export
from app.services import erp_mirror as miroir
from app.services import erp_tdb
from app.services.auth_service import get_current_user
from config import ROLES_ERP

router = APIRouter(prefix="/api/erp", tags=["erp"])


def _exiger_acces(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in ROLES_ERP:
        raise HTTPException(
            status_code=403,
            detail=(
                "Accès réservé à la direction, aux services administration, "
                "au service expédition et au super administrateur."
            ),
        )
    return user


def _colonnes_par_table():
    """Ce que le miroir contient réellement, table par table.

    Miroir absent = 503 (« le service n'est pas disponible »), pas 500 : ce
    n'est pas un bug de MySifa, c'est un import qui n'a pas encore eu lieu, et
    le message le dit.
    """
    try:
        with miroir.get_erp_db() as conn:
            tables = miroir.tables_presentes(conn)
            return {
                t: {r[1] for r in conn.execute("SELECT * FROM pragma_table_info(?)", (t,))}
                for t in tables
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


def _ecran(cle):
    ec = catalogue.ecran(cle)
    if not ec:
        raise HTTPException(status_code=404, detail="Écran inconnu.")
    adapte = catalogue.adapter_ecran(ec, _colonnes_par_table())
    if not adapte:
        raise HTTPException(
            status_code=404,
            detail="Écran indisponible : la table « %s » n'est pas dans le miroir." % ec["table"],
        )
    return adapte


@router.get("/meta")
def erp_meta(request: Request):
    user = _exiger_acces(request)
    infos = miroir.meta()
    if not infos["present"]:
        return {
            "present": False,
            "menu": catalogue.menu_du_role(user.get("role"), set()),
            "domaines": catalogue.DOMAINES,
            "ecrans": [],
            "enums": catalogue.ENUMS,
            "filtres_colonne": miroir.operateurs_disponibles(),
            "export_max": miroir.TAILLE_EXPORT_MAX,
            "message": (
                "Le miroir de l'ERP n'a pas encore été construit. "
                "Lancer l'export depuis un poste du réseau SIFA, puis l'import."
            ),
        }

    cols = _colonnes_par_table()
    lignes_par_table = {t["nom"]: t["lignes"] for t in infos["tables"]}
    ecrans = []
    for ec in catalogue.ECRANS:
        adapte = catalogue.adapter_ecran(ec, cols)
        if not adapte:
            continue
        ecrans.append({
            "cle": ec["cle"],
            "label": ec["label"],
            "domaine": ec["domaine"],
            "resume": ec.get("resume", ""),
            "table": ec["table"],
            "lignes": lignes_par_table.get(ec["table"]),
            "colonnes": len(adapte["colonnes"]),
            "filtres": [
                {k: v for k, v in f.items() if k != "col"} for f in adapte["filtres"]
            ],
            "rattachable": bool(adapte.get("rattachable")),
            "groupable": bool(catalogue.groupable(adapte)),
            "piece_label": (catalogue.PIECE_LABELS.get(ec["cle"], "La pièce")
                            if catalogue.groupable(adapte) else None),
        })

    # Les écrans sortent dans l'ordre d'affichage, pas dans celui du catalogue.
    ecrans.sort(key=lambda e: catalogue.rang(e["cle"]))

    return {
        "present": True,
        "menu": catalogue.menu_du_role(user.get("role"), {e["cle"] for e in ecrans}),
        "importe_le": infos["importe_le"],
        "releve_le": infos["releve_le"],
        "lignes": infos["lignes"],
        "tables": len(infos["tables"]),
        "domaines": catalogue.DOMAINES,
        "ecrans": ecrans,
        "enums": catalogue.ENUMS,
        # Quels opérateurs de filtre pour quelle famille de colonne, et
        # comment les nommer. La page n'en redéfinit aucun de son côté :
        # ajouter un opérateur ici suffit à le faire apparaître dans toutes
        # les en-têtes.
        "filtres_colonne": miroir.operateurs_disponibles(),
        "export_max": miroir.TAILLE_EXPORT_MAX,
    }


@router.get("/recherche")
def erp_recherche(
    request: Request,
    q: str = Query("", max_length=120),
    par_ecran: int = Query(miroir.RESULTATS_PAR_ECRAN, ge=1, le=20),
):
    """Cherche la même chaîne dans les vingt-sept écrans à la fois.

    Déclarée AVANT `/{cle}/...` : sinon FastAPI lirait « recherche » comme une
    clé d'écran et rendrait un 404.
    """
    _exiger_acces(request)
    cols = _colonnes_par_table()
    ecrans = []
    for ec in catalogue.ECRANS:
        adapte = catalogue.adapter_ecran(ec, cols)
        if adapte:
            ecrans.append(adapte)
    ecrans.sort(key=lambda e: catalogue.rang(e["cle"]))
    try:
        return miroir.recherche_globale(ecrans, q, par_ecran=par_ecran)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/menu")
def erp_menu(request: Request):
    """Le menu de service, seul — sans le catalogue des vingt-sept écrans.

    Le portail d'accueil l'appelle au survol de la marque RVGI. `/meta` ferait
    l'affaire mais coûte le relevé complet du miroir pour trois entrées de
    menu ; ici on ne lit le miroir que pour savoir quels écrans existent, et
    s'il est absent le menu sort quand même avec ses tableaux de bord.

    Déclarée AVANT `/{cle}/...`, comme `/recherche` et `/tdb`.
    """
    user = _exiger_acces(request)
    try:
        cols = _colonnes_par_table()
    except HTTPException:
        return {"present": False,
                "menu": catalogue.menu_du_role(user.get("role"), set())}
    dispo = {ec["cle"] for ec in catalogue.ECRANS
             if catalogue.adapter_ecran(ec, cols)}
    return {"present": True, "menu": catalogue.menu_du_role(user.get("role"), dispo)}


@router.get("/tdb/{cle}")
def erp_tableau_de_bord(cle: str, request: Request):
    """Un tableau de bord monté sur le miroir.

    Déclarée AVANT `/{cle}/...`, comme `/recherche` : sinon FastAPI lirait
    « tdb » comme une clé d'écran.

    Les compteurs qui vivent dans MySifa — OF, fiches techniques, mappings,
    scans — ne passent PAS par ici. Le navigateur va les chercher à leur
    propre route, celle-là même que le lien de la tuile ouvre : un compteur
    et l'écran qu'il ouvre ne peuvent alors jamais diverger.
    """
    _exiger_acces(request)
    if cle not in ("adv", "direction"):
        raise HTTPException(status_code=404, detail="Tableau de bord inconnu.")
    try:
        return erp_tdb.adv() if cle == "adv" else erp_tdb.direction()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{cle}/lignes")
def erp_lignes(
    cle: str,
    request: Request,
    q: str = Query("", max_length=120),
    tri: str = Query("", max_length=60),
    sens: str = Query("asc", max_length=4),
    page: int = Query(1, ge=1, le=100000),
    taille: int = Query(miroir.TAILLE_PAGE_DEFAUT, ge=1, le=miroir.TAILLE_PAGE_MAX),
    depuis: str = Query("", max_length=40),
    depuis_id: str = Query("", max_length=40),
    lien: int = Query(-1, ge=-1, le=99),
    ratt: str = Query("", max_length=10),
    vue: str = Query("ligne", max_length=6),
):
    _exiger_acces(request)
    ec = _ecran(cle)
    if ratt and ratt not in ("oui", "non", "partiel", "douteux"):
        raise HTTPException(status_code=400, detail="Filtre de rattachement inconnu.")

    # Ouverture depuis une pièce liée : le client donne l'écran d'origine, la
    # ligne et le rang du lien — jamais un nom de colonne. La condition est
    # reconstruite ici, à partir du catalogue.
    extra = None
    contexte = None
    if depuis and depuis_id and lien >= 0:
        extra, contexte = _condition_de_lien(depuis, depuis_id, lien, cle)

    # Les filtres du rail arrivent en `f_<nom>` — seuls ceux que l'écran
    # déclare sont retenus — et ceux des en-têtes en `c_<colonne>`, sous la
    # forme `operateur:valeur`. Les autres paramètres sont ignorés sans bruit.
    filtres, filtres_col = _parametres_vue(request)

    if vue not in ("ligne", "piece"):
        raise HTTPException(status_code=400, detail="Vue inconnue.")

    try:
        # Les filtres d'en-tête valent dans les deux vues : regrouper par
        # pièce ne doit pas rendre un filtre posé silencieusement inopérant.
        if vue == "piece":
            groupe = catalogue.colonnes_groupees(ec)
            if not groupe:
                raise HTTPException(
                    status_code=400,
                    detail="Cet écran n'a pas de pièce sur laquelle regrouper.")
            res = miroir.lister_groupe(
                ec, groupe, q=q, filtres=filtres, filtres_col=filtres_col,
                tri=tri or None, sens=sens,
                page=page, taille=taille, extra=extra,
            )
        else:
            res = miroir.lister(
                ec, q=q, filtres=filtres, filtres_col=filtres_col,
                tri=tri or None, sens=sens,
                page=page, taille=taille, extra=extra,
                rattachement=bool(ec.get("rattachable")), filtre_ratt=ratt,
            )
            res["vue"] = "ligne"
        if contexte:
            res["contexte"] = contexte
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _condition_de_lien(cle_source, ident, rang, cle_cible):
    """Reconstruit la condition d'un lien déclaré au catalogue."""
    ec_source = catalogue.ecran(cle_source)
    if not ec_source:
        raise HTTPException(status_code=400, detail="Écran d'origine inconnu.")
    liens = catalogue.LIENS.get(cle_source, [])
    if rang >= len(liens):
        raise HTTPException(status_code=400, detail="Lien inconnu.")
    lien = liens[rang]
    if lien["ecran"] != cle_cible:
        raise HTTPException(status_code=400, detail="Ce lien ne mène pas à cet écran.")

    adapte = catalogue.adapter_ecran(ec_source, _colonnes_par_table())
    if not adapte:
        raise HTTPException(status_code=404, detail="Écran d'origine indisponible.")

    source = miroir.ligne_brute(adapte, ident)
    if source is None:
        raise HTTPException(status_code=404, detail="Ligne d'origine introuvable.")

    extra = []
    valeurs = {}
    for ref, champ in lien["sur"].items():
        v = source.get(champ)
        if v is None or str(v).strip() == "":
            raise HTTPException(status_code=400, detail="La ligne d'origine ne porte pas cette clé.")
        extra.append(("CAST(%s AS TEXT) = ?" % miroir.valider_ref(ref), str(v).strip()))
        valeurs[ref.split(".")[-1]] = v

    return extra, {
        "depuis": cle_source,
        "depuis_label": ec_source["label"],
        "lien": lien["label"],
        "valeurs": valeurs,
    }


@router.get("/{cle}/liens/{ident}")
def erp_liens(cle: str, ident: str, request: Request):
    """Les pièces rattachées à une ligne : BL d'une commande, facture d'un BL…"""
    _exiger_acces(request)
    ec = _ecran(cle)
    cols = _colonnes_par_table()

    def resoudre(cle_cible):
        cible = catalogue.ecran(cle_cible)
        if not cible:
            return None
        return catalogue.adapter_ecran(cible, cols)

    try:
        return {"liens": miroir.liens(ec, ident, resoudre)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{cle}/detail/{ident}")
def erp_detail(cle: str, ident: str, request: Request):
    """La ligne ouverte, et la pièce qui la porte.

    Sur un écran de lignes de document — commande, marché, BL, facture — on
    renvoie d'un seul coup l'entête de la pièce et TOUTES ses lignes. Ouvrir la
    ligne 2 d'un marché sans montrer qu'il en compte quatre oblige à retourner
    à la grille : c'est justement le geste que cet écran doit supprimer.
    """
    _exiger_acces(request)
    ec = _ecran(cle)
    try:
        piece = miroir.piece(ec, ident)
        # Ce que l'entête porte déjà n'est pas répété dans le détail de la
        # ligne. Uniquement ce qui lui est PROPRE : `amje` existe des deux
        # côtés — date d'échéance de la pièce et de la ligne — et l'écarter du
        # détail ferait disparaître une information qui n'est pas la même.
        exclure = set()
        entete = None
        if piece:
            cols_ligne = _colonnes_par_table().get(ec["table"], set())
            exclure = set(piece["colonnes_entete"]) - set(cols_ligne) - {"numero"}
            entete = piece.get("brut_entete")
        res = miroir.detail(ec, ident, exclure=exclure, entete=entete)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if res is None:
        raise HTTPException(status_code=404, detail="Ligne introuvable dans le miroir.")
    if piece:
        piece.pop("colonnes_entete", None)
        piece.pop("brut_entete", None)
        res["piece"] = piece
    return res


# ── Export xlsx ──────────────────────────────────────────────────────────────

# Les paramètres d'une vue sont lus au même endroit pour la grille et pour
# l'export : c'est la seule façon de garantir que le fichier contient
# exactement ce que l'écran montrait. Deux lectures séparées finiraient par
# diverger, et personne ne s'en apercevrait avant de compter deux totaux
# différents.
def _parametres_vue(request: Request):
    filtres, filtres_col = {}, {}
    for nom, valeur in request.query_params.items():
        if nom.startswith("f_"):
            filtres[nom[2:]] = valeur
        elif nom.startswith("c_"):
            filtres_col[nom[2:]] = valeur
    return filtres, filtres_col


def _libelle_filtre_colonne(ec, nom, expr, enums):
    """« Quantité — Compris entre 1 000 et 5 000 », pour la feuille Critères."""
    col = next((c for c in ec["colonnes"] if c["nom"] == nom), None)
    if not col:
        return None
    op, _, reste = str(expr or "").partition(":")
    op = op.strip()
    fam = miroir.famille_de(col.get("type"))
    libs = dict(miroir.LABELS_OPS)
    if fam == "date":
        libs.update(miroir.LABELS_OPS_DATE)
    elif fam in ("enum", "bool"):
        libs.update(miroir.LABELS_OPS_LISTE)
    if op not in libs:
        return None
    attendu = miroir.NB_VALEURS.get(op, 1)
    vals = [v.strip() for v in str(reste).split("|")][:attendu] if attendu else []
    if len(vals) < attendu or any(v == "" for v in vals):
        return None
    if fam == "enum":
        table = enums.get(col.get("enum")) or {}
        vals = [table.get(v, v) for v in vals]
    elif fam == "date":
        vals = ["%s/%s/%s" % (v[8:10], v[5:7], v[0:4]) if len(v) >= 10 else v for v in vals]
    return "%s — %s%s" % (
        col.get("label") or nom, libs[op],
        (" " + " et ".join(vals)) if vals else "")


def _criteres(ec, meta_miroir, q, filtres, filtres_col, ratt, tri, sens,
              contexte, total, vue="ligne"):
    """Ce qui a produit ce fichier, en français, pour la seconde feuille."""
    enums = catalogue.ENUMS
    # La maille est dite explicitement : « 312 exportées » sur un écran qui en
    # comptait 845 se lit comme un export tronqué, alors que c'est un
    # regroupement. Le mot « pièce » lève l'ambiguïté à lui seul.
    par_piece = (vue == "piece")
    p = catalogue.piece_de(ec) if par_piece else None
    lignes = [
        ("Écran", "%s — %s" % (ec["label"], ec.get("resume", ""))),
        ("Table RVGI", ec["table"]),
        ("Lu par", ((p or {}).get("label") or "pièce") if par_piece else "ligne"),
        ("Exporté le", datetime.now().strftime("%d/%m/%Y à %H:%M")),
        ("Miroir importé le", _jolie_date(meta_miroir.get("importe_le"))),
        ("Relevé RVGI du", _jolie_date(meta_miroir.get("releve_le"))),
        (("Pièces exportées" if par_piece else "Lignes exportées"), total),
    ]
    if q:
        lignes.append(("Recherche", q))
    par_nom = {f["nom"]: f for f in ec.get("filtres", [])}
    for nom, valeur in filtres.items():
        f = par_nom.get(nom)
        if not f or not str(valeur).strip():
            continue
        v = str(valeur).strip()
        if f.get("type") == "enum":
            # Un choix composé (« 0|1 ») porte son propre libellé ; sinon on
            # traduit le code par l'énumération. Écrire « 0|1 » dans la feuille
            # des critères ne dirait rien à personne.
            compose = next((c["label"] for c in (f.get("choix") or [])
                            if str(c.get("v")) == v), None)
            v = compose or (enums.get(f.get("enum")) or {}).get(v, v)
        elif f.get("type", "").startswith("date") and len(v) >= 10:
            v = "%s/%s/%s" % (v[8:10], v[5:7], v[0:4])
        lignes.append(("Filtre — " + f["label"], v))
    for nom, expr in filtres_col.items():
        lib = _libelle_filtre_colonne(ec, nom, expr, enums)
        if lib:
            lignes.append(("Filtre de colonne", lib))
    if ratt:
        lignes.append(("Rattachement MySifa", {
            "oui": "Rattaché", "non": "Non rattaché",
            "partiel": "Partiellement", "douteux": "À vérifier"}.get(ratt, ratt)))
    if contexte:
        lignes.append(("Ouvert depuis", "%s · %s" % (
            contexte.get("depuis_label", ""), contexte.get("lien", ""))))
    if tri:
        lignes.append(("Tri", "%s, %s" % (
            tri, "décroissant" if sens == "desc" else "croissant")))
    lignes.append(("Source", "Miroir de RVGI, lecture seule. MySifa n'écrit "
                             "jamais dans l'ERP."))
    return lignes


def _jolie_date(s):
    s = str(s or "").strip()
    if len(s) >= 10:
        return "%s/%s/%s%s" % (s[8:10], s[5:7], s[0:4], (" " + s[11:16]) if len(s) >= 16 else "")
    return s or "—"


@router.get("/{cle}/export")
def erp_export(
    cle: str,
    request: Request,
    q: str = Query("", max_length=120),
    tri: str = Query("", max_length=60),
    sens: str = Query("asc", max_length=4),
    cols: str = Query("", max_length=2000),
    depuis: str = Query("", max_length=40),
    depuis_id: str = Query("", max_length=40),
    lien: int = Query(-1, ge=-1, le=99),
    ratt: str = Query("", max_length=10),
    vue: str = Query("ligne", max_length=6),
):
    """La vue courante, en classeur — pas la table, la VUE.

    Mêmes filtres, même tri, mêmes colonnes dans le même ordre que l'écran au
    moment du clic. `cols` porte l'ordre d'affichage tel que l'utilisateur l'a
    arrangé : c'est la seule chose que le serveur ne peut pas deviner, puisque
    déplacer une colonne est un réglage de navigateur.

    L'export ne pagine pas : il ramène tout le résultat du filtre, plafonné à
    `TAILLE_EXPORT_MAX`. Au-delà, le fichier est rendu quand même — tronqué au
    plafond — et la feuille « Critères » le dit en toutes lettres. Un fichier
    silencieusement incomplet serait pire qu'une erreur.

    La maille suit, elle aussi : lu par pièce, l'écran s'exporte par pièce.
    Rendre les lignes d'un écran qui affiche des commandes donnerait un
    classeur que personne ne rapprocherait de ce qu'il avait sous les yeux.
    """
    _exiger_acces(request)
    ec = _ecran(cle)
    if ratt and ratt not in ("oui", "non", "partiel", "douteux"):
        raise HTTPException(status_code=400, detail="Filtre de rattachement inconnu.")
    if vue not in ("ligne", "piece"):
        raise HTTPException(status_code=400, detail="Vue inconnue.")

    extra = contexte = None
    if depuis and depuis_id and lien >= 0:
        extra, contexte = _condition_de_lien(depuis, depuis_id, lien, cle)

    filtres, filtres_col = _parametres_vue(request)

    try:
        if vue == "piece":
            groupe = catalogue.colonnes_groupees(ec)
            if not groupe:
                raise HTTPException(
                    status_code=400,
                    detail="Cet écran n'a pas de pièce sur laquelle regrouper.")
            res = miroir.lister_groupe(
                ec, groupe, q=q, filtres=filtres, filtres_col=filtres_col,
                tri=tri or None, sens=sens, page=1,
                taille=miroir.TAILLE_EXPORT_MAX, plafond=miroir.TAILLE_EXPORT_MAX,
                extra=extra,
            )
        else:
            res = miroir.lister(
                ec, q=q, filtres=filtres, filtres_col=filtres_col,
                tri=tri or None, sens=sens, page=1,
                taille=miroir.TAILLE_EXPORT_MAX, plafond=miroir.TAILLE_EXPORT_MAX,
                extra=extra, rattachement=bool(ec.get("rattachable")), filtre_ratt=ratt,
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Ordre des colonnes : celui de l'écran. Un nom que l'écran ne connaît pas
    # est ignoré ; si rien ne reste, on retombe sur l'ordre du catalogue plutôt
    # que de rendre un classeur vide.
    dispo = {c["nom"]: c for c in res["colonnes"]}
    if ec.get("rattachable") and vue != "piece":
        dispo["_ratt"] = {
            "nom": "_ratt", "type": "ratt", "largeur": 150,
            "label": "Départ MyExpé" if cle == "livraisons" else "Dossier de fab",
        }
    demandees = [n.strip() for n in cols.split(",") if n.strip()]
    colonnes = [dispo[n] for n in demandees if n in dispo] or res["colonnes"]

    lignes = res["lignes"]
    total = res["total"] or 0
    tronque = total > len(lignes)
    note = None
    if tronque:
        mot = "pièces" if vue == "piece" else "lignes"
        note = (
            "Le filtre retourne %s %s ; l'export s'arrête à %s. "
            "Resserrer le filtre — une date de début, un client — pour obtenir "
            "le fichier complet." % (f"{total:,}".replace(",", " "), mot,
                                     f"{len(lignes):,}".replace(",", " "))
        )

    criteres = _criteres(ec, miroir.meta(), q, filtres, filtres_col, ratt,
                         res.get("tri"), res.get("sens"), contexte, len(lignes),
                         vue=vue)

    buf = export.construire(
        ec["label"], colonnes, lignes, enums=catalogue.ENUMS,
        criteres=criteres, note=note, tronque=tronque,
    )
    nom = "myerp_%s_%s.xlsx" % (cle, datetime.now().strftime("%Y%m%d-%H%M"))
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="%s"' % nom,
            # Le nombre de lignes remonte au client, qui l'annonce dans un
            # toast : sans lui, un export de 3 lignes et un de 3 000 se
            # ressemblent.
            "X-Erp-Lignes": str(len(lignes)),
            "X-Erp-Tronque": "1" if tronque else "0",
            "Access-Control-Expose-Headers": "X-Erp-Lignes, X-Erp-Tronque",
        },
    )
