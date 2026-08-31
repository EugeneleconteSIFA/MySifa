"""MySifa — Traceur de traçabilité FSC (MyProd → Traçabilité → Traceur).

Objet : reconstituer, dans les DEUX SENS, la chaîne complète d'un produit —
de la bobine reçue du fournisseur jusqu'au bon de livraison client.

    réception fournisseur → bobine scannée → dossier de fabrication
      → saisies de production → lot de produit fini (entrée Z1)
      → déplacements en stock → sortie → expédition

Pourquoi les deux sens. Une chaîne de contrôle FSC se vérifie de l'amont vers
l'aval (« ce dossier a-t-il consommé de la matière certifiée ? ») mais s'audite
surtout de l'aval vers l'amont : en cas de doute sur un certificat fournisseur,
la question qui tombe est « ce lot de bobines est parti chez qui ? ». Ne servir
qu'un sens obligeait à ouvrir dossier par dossier jusqu'à retrouver le bon.

Le point d'entrée est un champ unique : l'utilisateur colle ce qu'il a sous la
main — un numéro d'OF, un code-barre de bobine, un numéro de lot LOT-…, une
référence produit, un numéro de BL — et `resolve` détermine la nature de la
clé. Demander à l'opérateur de choisir d'abord le type de recherche, c'est lui
demander de connaître le modèle de données.

HONNÊTETÉ DES LIENS. Certains rattachements sont issus du backfill des
migrations 220-222 (rapprochements par horodatage, ou `ref_sifa` reconnu comme
une référence de dossier) et non d'une saisie. Ils sortent marqués
`reconstitue: true`, et l'interface les affiche en dégradé. Un auditeur ne doit
jamais prendre une déduction pour une donnée d'origine.

Accès : config.ROLES_TRACA_VIEWER — plus fermé que le rapport FSC par dossier
déjà disponible en atelier, parce que la vue transversale expose fournisseurs
et volumes clients bien au-delà du besoin d'un poste de production.
"""
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from config import EXPE_MOTIFS_SANS_DOSSIER, FSC_CLAIM_LABELS, ROLES_TRACA_VIEWER
from database import get_db
from services.auth_service import get_current_user

router = APIRouter()

# Limite de fan-out par niveau. Une bobine consommée sur 400 dossiers rendrait
# le graphe illisible et la requête coûteuse ; on tronque et on le DIT
# (`tronque: true`), plutôt que de laisser croire à une chaîne complète.
_MAX_NOEUDS = 50


def _require_traca(request: Request) -> dict:
    user = get_current_user(request)
    if (user.get("role") or "") not in ROLES_TRACA_VIEWER:
        raise HTTPException(403, "Accès au traceur de traçabilité non autorisé.")
    return user


def _claim_label(claim: Optional[str]) -> str:
    c = (claim or "non_fsc").strip()
    return FSC_CLAIM_LABELS.get(c, c)


# ══════════════════════════════════════════════════════════════════
# Résolution : quelle est la nature de la clé saisie ?
# ══════════════════════════════════════════════════════════════════

# Numéro de lot matière généré à la réception : LOT-AAAAMMJJ-HHMM-FOURN-CLAIM
# (cf. _build_lot_numero dans app/routers/stock.py).
_RE_LOT_MATIERE = re.compile(r"^LOT-\d{6,8}-", re.I)


def _resolve_candidats(conn, q: str) -> list[dict]:
    """Retourne les entités correspondant à `q`, la plus probable d'abord.

    On ne devine pas : on interroge chaque table et on renvoie ce qui existe
    RÉELLEMENT. Une saisie ambiguë (une référence produit qui ressemble à un
    numéro d'OF) remonte donc deux candidats et l'utilisateur tranche, plutôt
    que de recevoir silencieusement la mauvaise chaîne.
    """
    out: list[dict] = []
    ql = q.strip()
    if not ql:
        return out

    # 1. Dossier de fabrication (reference ou numero_of)
    for r in conn.execute(
        """SELECT reference, numero_of, client, description,
                  COALESCE(fsc_requis,0) AS fsc_requis, COALESCE(fsc_type_requis,'') AS fsc_type_requis
             FROM planning_entries
            WHERE TRIM(COALESCE(reference,''))=? OR TRIM(COALESCE(numero_of,''))=?
            LIMIT 5""",
        (ql, ql),
    ).fetchall():
        out.append({
            "type": "dossier",
            "id": r["reference"] or r["numero_of"],
            "libelle": (r["reference"] or r["numero_of"] or ""),
            "detail": " · ".join(x for x in [r["client"], r["description"]] if x),
            "fsc": int(r["fsc_requis"] or 0),
            "fsc_type": r["fsc_type_requis"] or "",
        })

    # 2. Bobine matière (code-barre scanné en production ou en réception)
    row = conn.execute(
        """SELECT COUNT(*) AS n FROM fab_matieres_utilisees
            WHERE TRIM(code_barre)=?""",
        (ql,),
    ).fetchone()
    row2 = conn.execute(
        "SELECT COUNT(*) AS n FROM stock_reception_items WHERE TRIM(code_barre)=?",
        (ql,),
    ).fetchone()
    if (row and row["n"]) or (row2 and row2["n"]):
        out.append({
            "type": "bobine",
            "id": ql,
            "libelle": ql,
            "detail": f"{(row['n'] if row else 0)} utilisation(s) en production",
        })

    # 3. Lot matière (numéro de réception)
    if _RE_LOT_MATIERE.match(ql):
        r = conn.execute(
            "SELECT id, lot_numero, fournisseur, fsc_type_claim FROM stock_receptions WHERE lot_numero=? LIMIT 1",
            (ql,),
        ).fetchone()
        if r:
            out.append({
                "type": "reception",
                "id": str(r["id"]),
                "libelle": r["lot_numero"] or ql,
                "detail": " · ".join(x for x in [r["fournisseur"], _claim_label(r["fsc_type_claim"])] if x),
            })

    # 4. Expédition (numéro de BL)
    for r in conn.execute(
        """SELECT id, no_bl, client, transporteur, date_enlevement
             FROM expe_departs WHERE TRIM(COALESCE(no_bl,''))=? LIMIT 5""",
        (ql,),
    ).fetchall():
        out.append({
            "type": "expedition",
            "id": str(r["id"]),
            "libelle": r["no_bl"] or f"BL #{r['id']}",
            "detail": " · ".join(x for x in [r["client"], r["transporteur"], r["date_enlevement"]] if x),
        })

    # 5. Référence produit fini
    for r in conn.execute(
        "SELECT id, reference, designation FROM produits WHERE UPPER(TRIM(reference))=UPPER(?) LIMIT 5",
        (ql,),
    ).fetchall():
        out.append({
            "type": "produit",
            "id": str(r["id"]),
            "libelle": r["reference"] or "",
            "detail": r["designation"] or "",
        })

    return out


@router.get("/api/traca/resolve")
def traca_resolve(request: Request, q: str = ""):
    """Identifie ce que désigne la saisie de l'utilisateur.

    Retourne 0, 1 ou plusieurs candidats. Le front enchaîne automatiquement
    sur /api/traca/chaine quand il n'y en a qu'un, et propose un choix sinon.
    """
    _require_traca(request)
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(400, "Saisir au moins 2 caractères.")
    with get_db() as conn:
        candidats = _resolve_candidats(conn, q)
    return {"q": q, "candidats": candidats, "nb": len(candidats)}


# ══════════════════════════════════════════════════════════════════
# Construction de la chaîne
# ══════════════════════════════════════════════════════════════════


def _dossier_row(conn, ref: str) -> Optional[dict]:
    r = conn.execute(
        """SELECT pe.reference, pe.numero_of, pe.client, pe.description, pe.statut,
                  pe.date_livraison, COALESCE(pe.fsc_requis,0) AS fsc_requis,
                  COALESCE(pe.fsc_type_requis,'') AS fsc_type_requis,
                  m.nom AS machine_nom
             FROM planning_entries pe
             LEFT JOIN machines m ON m.id = pe.machine_id
            WHERE TRIM(COALESCE(pe.reference,''))=? OR TRIM(COALESCE(pe.numero_of,''))=?
            LIMIT 1""",
        (ref, ref),
    ).fetchone()
    return dict(r) if r else None


def _matieres_du_dossier(conn, ref: str) -> list[dict]:
    """Bobines consommées par un dossier, avec leur origine fournisseur."""
    rows = conn.execute(
        """SELECT fmu.code_barre, fmu.scanned_at, fmu.operateur, fmu.machine_nom,
                  COALESCE(fmu.fsc_warning,0) AS fsc_warning, fmu.fsc_warning_note,
                  sr.id AS reception_id, sr.lot_numero, sr.created_at AS reception_date,
                  COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
                  COALESCE(sr.certificat_fsc, fmu.certificat_fsc_manual) AS certificat_fsc,
                  COALESCE(sr.fsc_type_claim,'non_fsc') AS fsc_type_claim,
                  ff.licence AS fournisseur_licence,
                  (SELECT COUNT(DISTINCT i2.reception_id)
                     FROM stock_reception_items i2
                    WHERE TRIM(i2.code_barre) = TRIM(fmu.code_barre)) AS nb_receptions_candidates
             FROM fab_matieres_utilisees fmu
             LEFT JOIN stock_receptions sr ON sr.id = (
                   SELECT i.reception_id FROM stock_reception_items i
                    WHERE TRIM(i.code_barre) = TRIM(fmu.code_barre)
                    ORDER BY i.scanned_at DESC, i.id DESC LIMIT 1)
             LEFT JOIN fournisseurs_fsc ff
                    ON ff.id = sr.fournisseur_id
                    OR (sr.fournisseur_id IS NULL
                        AND ff.nom = COALESCE(sr.fournisseur, fmu.fournisseur_manual))
            WHERE TRIM(COALESCE(fmu.no_dossier,''))=?
            ORDER BY fmu.scanned_at ASC
            LIMIT ?""",
        (ref, _MAX_NOEUDS),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["fsc_claim_label"] = _claim_label(d.get("fsc_type_claim"))
        # Le rattachement bobine → réception passe par le code-barre : c'est
        # une saisie réelle (l'opérateur a scanné), pas une déduction.
        d["reconstitue"] = False
        # …sauf si le code existe dans plusieurs réceptions. La requête
        # ci-dessus retient alors la plus récente : c'est un choix arbitraire,
        # et il doit être annoncé. Un fournisseur affiché avec certitude alors
        # qu'il y avait deux candidats est pire qu'une case vide.
        d["reception_ambigue"] = int(d.pop("nb_receptions_candidates", 1) or 1) > 1
        out.append(d)
    return out


def _saisies_du_dossier(conn, ref: str) -> list[dict]:
    rows = conn.execute(
        """SELECT date_operation, operation, operateur, machine,
                  quantite_traitee, quantite_a_traiter
             FROM production_data
            WHERE TRIM(COALESCE(no_dossier,''))=?
            ORDER BY date_operation ASC
            LIMIT ?""",
        (ref, _MAX_NOEUDS),
    ).fetchall()
    return [dict(r) for r in rows]


def motifs_absence_matiere(conn, ref: str) -> list[dict]:
    """Ce que l'operateur a repondu en cloturant sans avoir scanne un code.

    Definition unique, partagee par le traceur et par le rapport FSC par
    dossier (app/routers/fabrication.py) : une chaine vide expliquee et une
    chaine vide par oubli ont exactement la meme allure dans la base, et les
    deux vues doivent trancher de la meme facon.

    Renvoie une liste vide -- jamais une erreur -- si la base n'a pas encore
    recu la migration `matiere_absente_motif` : une vue de tracabilite doit
    rester lisible sur une base en retard.
    """
    try:
        rows = conn.execute(
            """SELECT matiere_absente_motif AS motif, operateur, date_operation,
                      machine
                 FROM production_data
                WHERE TRIM(COALESCE(no_dossier,''))=?
                  AND operation_code='89'
                  AND COALESCE(TRIM(matiere_absente_motif),'') <> ''
                ORDER BY date_operation DESC
                LIMIT ?""",
            (ref, _MAX_NOEUDS),
        ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def _lots_du_dossier(conn, ref: str) -> list[dict]:
    """Lots de produit fini issus d'un dossier, avec leur emplacement actuel."""
    rows = conn.execute(
        """SELECT l.id, l.emplacement, l.quantite_initiale, l.quantite_restante,
                  l.date_entree, l.created_at, l.created_by,
                  COALESCE(l.fsc,0) AS fsc, COALESCE(l.fsc_ecart,0) AS fsc_ecart,
                  COALESCE(l.fsc_link_reconstitue,0) AS reconstitue,
                  p.id AS produit_id, p.reference AS produit_ref, p.designation, p.unite
             FROM lots_stock l
             JOIN produits p ON p.id = l.produit_id
            WHERE TRIM(COALESCE(l.no_dossier,''))=?
            ORDER BY l.created_at ASC
            LIMIT ?""",
        (ref, _MAX_NOEUDS),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reconstitue"] = bool(d.pop("reconstitue", 0))
        # Où ce lot est-il parti ? Le sens aval, celui qu'un auditeur suit
        # quand il doute d'un certificat fournisseur.
        d["departs"] = _departs_du_lot(conn, d["id"])
        out.append(d)
    return out


def _mouvements_des_lots(conn, lot_ids: list[int], ref: str) -> list[dict]:
    """Parcours physique : entrées, déplacements et sorties.

    Deux sources complémentaires — les mouvements rattachés explicitement à un
    lot (`lot_id`, renseigné depuis la migration 221) et ceux rattachés au
    dossier (`no_dossier`). Les premiers sont fiables, les seconds couvrent
    l'historique antérieur : on les marque `reconstitue` pour que la
    différence reste lisible.
    """
    vus: set[int] = set()
    out: list[dict] = []

    if lot_ids:
        ph = ",".join("?" * len(lot_ids))
        for r in conn.execute(
            f"""SELECT m.id, m.emplacement, m.type_mouvement, m.quantite,
                       m.created_at, m.created_by_name, m.created_by, m.note,
                       m.lot_id, COALESCE(m.fsc,0) AS fsc,
                       COALESCE(m.fsc_ecart,0) AS fsc_ecart, m.fsc_ecart_note,
                       p.reference AS produit_ref
                  FROM mouvements_stock m
                  JOIN produits p ON p.id = m.produit_id
                 WHERE m.lot_id IN ({ph})
                 ORDER BY m.created_at ASC""",
            lot_ids,
        ).fetchall():
            d = dict(r)
            d["reconstitue"] = False
            vus.add(d["id"])
            out.append(d)

    for r in conn.execute(
        """SELECT m.id, m.emplacement, m.type_mouvement, m.quantite,
                  m.created_at, m.created_by_name, m.created_by, m.note,
                  m.lot_id, COALESCE(m.fsc,0) AS fsc,
                  COALESCE(m.fsc_ecart,0) AS fsc_ecart, m.fsc_ecart_note,
                  p.reference AS produit_ref
             FROM mouvements_stock m
             JOIN produits p ON p.id = m.produit_id
            WHERE TRIM(COALESCE(m.no_dossier,''))=?
            ORDER BY m.created_at ASC
            LIMIT ?""",
        (ref, _MAX_NOEUDS * 2),
    ).fetchall():
        if r["id"] in vus:
            continue
        d = dict(r)
        d["reconstitue"] = True
        out.append(d)

    out.sort(key=lambda x: (x.get("created_at") or ""))
    return out[: _MAX_NOEUDS * 2]


def _expeditions_du_dossier(conn, ref: str) -> list[dict]:
    """Départs rattachés à un dossier.

    Deux chemins, parce que le lien a deux âges. `expe_departs.no_dossier` est
    la copie textuelle tenue à jour à l'écriture par `_sync_no_dossier()` ;
    `planning_entry_id` est la clé étrangère que le formulaire d'expédition
    remplit depuis toujours. On interroge les deux : sans le second, tout
    départ créé entre la migration 222 et le rétablissement du lien resterait
    invisible ici alors que son dossier est parfaitement connu en base.
    """
    rows = conn.execute(
        """SELECT d.id, d.no_bl, d.client, d.transporteur, d.affreteurs,
                  d.date_enlevement, d.date_livraison, d.code_postal_destination,
                  d.nb_palette, d.poids_total_kg, d.statut, d.ref_sifa,
                  COALESCE(NULLIF(TRIM(COALESCE(d.no_dossier,'')),''),
                           NULLIF(TRIM(COALESCE(pe.reference,'')),''),
                           TRIM(COALESCE(pe.numero_of,''))) AS no_dossier,
                  CASE
                    WHEN TRIM(COALESCE(d.no_dossier,'')) <> ''
                      THEN COALESCE(d.no_dossier_source,'')
                    WHEN d.planning_entry_id IS NOT NULL THEN 'saisi'
                    ELSE ''
                  END AS no_dossier_source
             FROM expe_departs d
             LEFT JOIN planning_entries pe ON pe.id = d.planning_entry_id
            WHERE TRIM(COALESCE(d.no_dossier,''))=?
               OR TRIM(COALESCE(pe.reference,''))=?
               OR TRIM(COALESCE(pe.numero_of,''))=?
               -- Un départ peut couvrir plusieurs dossiers : le lien direct
               -- ne désigne que le premier, la liaison les porte tous.
               OR EXISTS (SELECT 1 FROM expe_depart_dossiers dd
                            LEFT JOIN planning_entries pe3 ON pe3.id = dd.planning_entry_id
                           WHERE dd.depart_id = d.id
                             AND (TRIM(COALESCE(dd.no_dossier,''))=?
                               OR TRIM(COALESCE(pe3.reference,''))=?
                               OR TRIM(COALESCE(pe3.numero_of,''))=?))
            ORDER BY d.date_enlevement ASC
            LIMIT ?""",
        (ref, ref, ref, ref, ref, ref, _MAX_NOEUDS),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reconstitue"] = (d.pop("no_dossier_source", "") == "reconstitue")
        out.append(d)
    return out


def _lots_expedies(conn, depart_id: int) -> list[dict]:
    """Lots de produit fini physiquement sortis pour un départ donné.

    C'est la preuve directe, celle qu'un auditeur préfère : non pas « ce
    dossier a produit ces lots et cette expédition vient de ce dossier », mais
    « ces lots-là sont sortis du stock sur ce BL ». La déduction par le dossier
    reste juste tant qu'un dossier ne produit qu'un lot ; elle cesse de l'être
    dès qu'il en produit plusieurs.

    Renvoie une liste vide pour les sorties antérieures à la migration
    `fsc_sortie_lots_et_depart` : elles n'ont jamais enregistré le détail des
    lots consommés, et le reconstituer a posteriori serait une invention.
    """
    try:
        rows = conn.execute(
            """SELECT msl.lot_id, msl.quantite, msl.fsc, msl.no_dossier,
                      m.id AS mouvement_id, m.created_at, m.created_by_name,
                      m.emplacement, m.note,
                      l.date_entree, l.quantite_initiale,
                      COALESCE(l.fsc_link_reconstitue,0) AS lot_reconstitue,
                      p.reference AS produit_ref, p.designation, p.unite
                 FROM mouvements_stock m
                 JOIN mouvements_stock_lots msl ON msl.mouvement_id = m.id
                 JOIN lots_stock l ON l.id = msl.lot_id
                 JOIN produits p ON p.id = m.produit_id
                WHERE m.expe_depart_id = ?
                ORDER BY m.created_at ASC, msl.id ASC
                LIMIT ?""",
            (depart_id, _MAX_NOEUDS),
        ).fetchall()
    except Exception:
        # Base antérieure à la migration : absence de trace, pas erreur.
        return []
    out = []
    for r in rows:
        d = dict(r)
        d["lot_reconstitue"] = bool(d.pop("lot_reconstitue", 0))
        out.append(d)
    return out


def _departs_du_lot(conn, lot_id: int) -> list[dict]:
    """Sens inverse : sur quels bons de livraison ce lot est-il parti ?"""
    try:
        rows = conn.execute(
            """SELECT DISTINCT d.id, d.no_bl, d.client, d.date_enlevement,
                      d.transporteur, msl.quantite
                 FROM mouvements_stock_lots msl
                 JOIN mouvements_stock m ON m.id = msl.mouvement_id
                 JOIN expe_departs d ON d.id = m.expe_depart_id
                WHERE msl.lot_id = ?
                ORDER BY d.date_enlevement ASC
                LIMIT ?""",
            (lot_id, _MAX_NOEUDS),
        ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def _dossiers_de_la_bobine(conn, code_barre: str) -> list[str]:
    """Sens inverse : tous les dossiers ayant consommé cette bobine."""
    rows = conn.execute(
        """SELECT DISTINCT TRIM(COALESCE(no_dossier,'')) AS ref
             FROM fab_matieres_utilisees
            WHERE TRIM(code_barre)=? AND TRIM(COALESCE(no_dossier,''))<>''
            LIMIT ?""",
        (code_barre, _MAX_NOEUDS),
    ).fetchall()
    return [r["ref"] for r in rows]


def _reception_de_la_bobine(conn, code_barre: str) -> Optional[dict]:
    r = conn.execute(
        """SELECT sr.id, sr.lot_numero, sr.fournisseur, sr.certificat_fsc,
                  COALESCE(sr.fsc_type_claim,'non_fsc') AS fsc_type_claim,
                  sr.created_at, sr.created_by_name, sr.nb_bobines,
                  ff.licence AS fournisseur_licence, ff.certificat AS fournisseur_certificat,
                  ff.pays_origine
             FROM stock_reception_items i
             JOIN stock_receptions sr ON sr.id = i.reception_id
             LEFT JOIN fournisseurs_fsc ff
                    ON ff.id = sr.fournisseur_id
                    OR (sr.fournisseur_id IS NULL AND ff.nom = sr.fournisseur)
            WHERE TRIM(i.code_barre)=?
            ORDER BY i.scanned_at DESC, i.id DESC
            LIMIT 1""",
        (code_barre,),
    ).fetchone()
    if not r:
        return None
    d = dict(r)
    d["fsc_claim_label"] = _claim_label(d.get("fsc_type_claim"))
    nb = conn.execute(
        """SELECT COUNT(DISTINCT reception_id) AS n
             FROM stock_reception_items WHERE TRIM(code_barre)=?""",
        (code_barre,),
    ).fetchone()
    d["reception_ambigue"] = int((nb["n"] if nb else 1) or 1) > 1
    return d


def _negoce_du_produit(conn, produit_id: int) -> list[dict]:
    """Réceptions de négoce (produit fini acheté) portant sur ce produit.

    Un produit acheté fini n'a ni bobine ni dossier de fabrication : sa chaîne
    s'arrête au BL du partenaire, et c'est normal. Sans cette requête, le
    traceur conclurait « aucun lot rattaché à un dossier » — une phrase exacte
    mais qui se lit comme un trou de traçabilité alors que la chaîne est
    complète, simplement plus courte.
    """
    try:
        rows = conn.execute(
            """SELECT r.id, r.lot_numero, r.date_reception, r.bon_livraison,
                      COALESCE(r.fsc_type_claim,'non_fsc') AS fsc_type_claim,
                      r.licence_fournisseur, r.certificat_valide, r.certificat_note,
                      f.nom AS fournisseur_nom,
                      i.id AS item_id, i.quantite, i.unite, i.emplacement,
                      i.lot_fournisseur, i.lot_stock_id
                 FROM pf_reception_items i
                 JOIN pf_receptions r ON r.id = i.reception_id
                 LEFT JOIN fournisseurs_fsc f ON f.id = r.fournisseur_id
                WHERE i.produit_id=?
                ORDER BY r.date_reception DESC, r.id DESC
                LIMIT ?""",
            (produit_id, _MAX_NOEUDS),
        ).fetchall()
    except Exception:
        # Base antérieure à la migration négoce : absence de trace, pas erreur.
        return []
    out = []
    for r in rows:
        d = dict(r)
        d["fsc_claim_label"] = _claim_label(d.get("fsc_type_claim"))
        out.append(d)
    return out


def _bobines_de_la_reception(conn, reception_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT code_barre FROM stock_reception_items WHERE reception_id=? LIMIT ?",
        (reception_id, _MAX_NOEUDS),
    ).fetchall()
    return [r["code_barre"] for r in rows]


def _chaine_dossier(conn, ref: str) -> dict:
    """Chaîne complète autour d'un dossier — le cœur du traceur.

    Amont (matières) et aval (lots, mouvements, expéditions) sont renvoyés
    ensemble : c'est un seul dossier, l'utilisateur n'a pas à demander deux
    fois pour voir les deux côtés.
    """
    dossier = _dossier_row(conn, ref)
    ref_canon = (dossier or {}).get("reference") or ref

    matieres = _matieres_du_dossier(conn, ref_canon)
    motifs_absence = motifs_absence_matiere(conn, ref_canon)
    saisies = _saisies_du_dossier(conn, ref_canon)
    lots = _lots_du_dossier(conn, ref_canon)
    mouvements = _mouvements_des_lots(conn, [l["id"] for l in lots], ref_canon)
    expeditions = _expeditions_du_dossier(conn, ref_canon)

    fsc_requis = int((dossier or {}).get("fsc_requis") or 0)
    try:
        from app.routers.fabrication import FSC_CLAIM_HIERARCHY
        autorises = FSC_CLAIM_HIERARCHY.get((dossier or {}).get("fsc_type_requis") or "", set())
    except Exception:
        autorises = set()
    nb_conformes = sum(
        1 for m in matieres if (m.get("fsc_type_claim") or "non_fsc") in autorises
    )

    # Rupture de chaîne : ce que le traceur ne peut PAS démontrer. Une chaîne
    # incomplète affichée sans le dire vaut moins que pas de chaîne du tout.
    ruptures = []
    if not matieres:
        # Une chaine matiere vide ne dit pas la meme chose selon qu'elle est
        # expliquee ou muette. L'explication de l'operateur, si elle existe,
        # remonte ICI : c'est la premiere chose qu'un auditeur cherche quand
        # il ouvre un dossier sans bobine.
        if motifs_absence:
            m0 = motifs_absence[0]
            ruptures.append(
                "Aucune bobine scannée sur ce dossier. Réponse de l'opérateur "
                + (("« " + str(m0.get("motif") or "").strip() + " »") if m0.get("motif") else "—")
                + (" (" + m0["operateur"] + ")" if m0.get("operateur") else "")
                + " — déclaratif, non vérifiable par la chaîne."
            )
        elif fsc_requis:
            ruptures.append(
                "Aucune bobine tracée sur ce dossier certifié, et aucune "
                "explication saisie à la clôture."
            )
    if fsc_requis and matieres and nb_conformes < len(matieres):
        ruptures.append(
            f"{len(matieres) - nb_conformes} bobine(s) ne satisfont pas le claim exigé."
        )
    nb_ambigues = sum(1 for m in matieres if m.get("reception_ambigue"))
    if nb_ambigues:
        ruptures.append(
            f"{nb_ambigues} bobine(s) portent un code-barre présent dans plusieurs "
            f"réceptions : leur origine fournisseur n'est pas démontrable."
        )
    if not lots:
        ruptures.append("Aucun lot de produit fini rattaché — entrée en stock non faite ou antérieure au suivi.")
    if lots and not expeditions:
        ruptures.append("Aucune expédition rattachée à ce dossier.")

    return {
        "racine": {"type": "dossier", "id": ref_canon},
        "dossier": dossier,
        "matieres": matieres,
        "motifs_absence": motifs_absence,
        "saisies": saisies,
        "lots": lots,
        "mouvements": mouvements,
        "expeditions": expeditions,
        "synthese": {
            "fsc_requis": fsc_requis,
            "fsc_type_requis": (dossier or {}).get("fsc_type_requis") or "",
            "nb_bobines": len(matieres),
            "matiere_absente_expliquee": bool(motifs_absence),
            "nb_bobines_conformes": nb_conformes if fsc_requis else None,
            "nb_lots": len(lots),
            "nb_lots_fsc": sum(1 for l in lots if int(l.get("fsc") or 0) == 1),
            "nb_expeditions": len(expeditions),
            "quantite_produite": sum(float(l.get("quantite_initiale") or 0) for l in lots),
            "quantite_en_stock": sum(float(l.get("quantite_restante") or 0) for l in lots),
            "ruptures": ruptures,
            "tronque": any(
                len(x) >= _MAX_NOEUDS for x in (matieres, saisies, lots, expeditions)
            ),
        },
    }


@router.get("/api/traca/chaine")
def traca_chaine(request: Request, type: str = "", id: str = ""):
    """Chaîne de traçabilité complète à partir d'un point d'entrée.

    `type` : dossier | bobine | reception | expedition | produit
    `id`   : identifiant renvoyé par /api/traca/resolve
    """
    _require_traca(request)
    t = (type or "").strip().lower()
    key = (id or "").strip()
    if not t or not key:
        raise HTTPException(400, "Paramètres `type` et `id` obligatoires.")

    with get_db() as conn:
        if t == "dossier":
            return _chaine_dossier(conn, key)

        if t == "bobine":
            # Sens aval → amont : la bobine, sa réception, et TOUS les dossiers
            # qui l'ont consommée avec leur propre chaîne aval.
            reception = _reception_de_la_bobine(conn, key)
            refs = _dossiers_de_la_bobine(conn, key)
            branches = [_chaine_dossier(conn, r) for r in refs]
            return {
                "racine": {"type": "bobine", "id": key},
                "reception": reception,
                "dossiers": branches,
                "synthese": {
                    "nb_dossiers": len(refs),
                    "nb_expeditions": sum(len(b["expeditions"]) for b in branches),
                    "claim_matiere": (reception or {}).get("fsc_type_claim"),
                    "claim_matiere_label": _claim_label((reception or {}).get("fsc_type_claim")),
                    "ruptures": (
                        ["Bobine inconnue en réception — origine fournisseur non démontrable."]
                        if not reception else []
                    ) + ([] if refs else ["Bobine jamais consommée en production."]),
                    "tronque": len(refs) >= _MAX_NOEUDS,
                },
            }

        if t == "reception":
            try:
                rid = int(key)
            except ValueError:
                raise HTTPException(400, "Identifiant de réception invalide.")
            rec = conn.execute(
                """SELECT sr.*, ff.licence AS fournisseur_licence,
                          ff.certificat AS fournisseur_certificat, ff.pays_origine
                     FROM stock_receptions sr
                     LEFT JOIN fournisseurs_fsc ff
                            ON ff.id = sr.fournisseur_id
                            OR (sr.fournisseur_id IS NULL AND ff.nom = sr.fournisseur)
                    WHERE sr.id=?""",
                (rid,),
            ).fetchone()
            if not rec:
                raise HTTPException(404, "Réception introuvable.")
            codes = _bobines_de_la_reception(conn, rid)
            refs: list[str] = []
            for cb in codes:
                for r in _dossiers_de_la_bobine(conn, cb):
                    if r not in refs:
                        refs.append(r)
            branches = [_chaine_dossier(conn, r) for r in refs[:_MAX_NOEUDS]]
            d_rec = dict(rec)
            d_rec["fsc_claim_label"] = _claim_label(d_rec.get("fsc_type_claim"))
            return {
                "racine": {"type": "reception", "id": key},
                "reception": d_rec,
                "bobines": codes,
                "dossiers": branches,
                "synthese": {
                    "nb_bobines": len(codes),
                    "nb_dossiers": len(refs),
                    "nb_expeditions": sum(len(b["expeditions"]) for b in branches),
                    "ruptures": [] if refs else ["Aucune bobine de cette réception n'a encore été consommée."],
                    "tronque": len(refs) > _MAX_NOEUDS,
                },
            }

        if t == "expedition":
            try:
                eid = int(key)
            except ValueError:
                raise HTTPException(400, "Identifiant d'expédition invalide.")
            # Même double lecture que `_expeditions_du_dossier` : la copie
            # textuelle si elle existe, sinon le dossier pointé par la clé
            # étrangère du formulaire d'expédition.
            exp = conn.execute(
                """SELECT d.*,
                          COALESCE(NULLIF(TRIM(COALESCE(d.no_dossier,'')),''),
                                   NULLIF(TRIM(COALESCE(pe.reference,'')),''),
                                   TRIM(COALESCE(pe.numero_of,''))) AS dossier_ref,
                          CASE
                            WHEN TRIM(COALESCE(d.no_dossier,'')) <> ''
                              THEN COALESCE(d.no_dossier_source,'')
                            WHEN d.planning_entry_id IS NOT NULL THEN 'saisi'
                            ELSE ''
                          END AS dossier_source
                     FROM expe_departs d
                     LEFT JOIN planning_entries pe ON pe.id = d.planning_entry_id
                    WHERE d.id=?""",
                (eid,),
            ).fetchone()
            if not exp:
                raise HTTPException(404, "Expédition introuvable.")
            d_exp = dict(exp)
            refs_dossiers = [
                r["ref"]
                for r in conn.execute(
                    """SELECT COALESCE(
                                NULLIF(TRIM(COALESCE(dd.no_dossier,'')), ''),
                                NULLIF(TRIM(COALESCE(pe.reference,'')), ''),
                                TRIM(COALESCE(pe.numero_of,''))) AS ref
                         FROM expe_depart_dossiers dd
                         LEFT JOIN planning_entries pe ON pe.id = dd.planning_entry_id
                        WHERE dd.depart_id = ?
                        ORDER BY dd.id ASC LIMIT ?""",
                    (eid, _MAX_NOEUDS),
                ).fetchall()
                if (r["ref"] or "").strip()
            ]
            # Repli sur la copie textuelle pour les départs antérieurs à la
            # table de liaison, ou saisis par un client non mis à jour.
            if not refs_dossiers:
                r0 = (d_exp.get("dossier_ref") or "").strip()
                refs_dossiers = [r0] if r0 else []
            ref = refs_dossiers[0] if refs_dossiers else ""
            branches = [_chaine_dossier(conn, r) for r in refs_dossiers]

            # Livraison directe (régime A2) : rien n'a transité par SIFA, donc
            # l'absence de dossier et de lot est la situation NORMALE. La
            # preuve du claim est le BL du partenaire, et c'est lui qu'il faut
            # exiger — pas un dossier de fabrication qui n'existera jamais.
            negoce_direct = None
            if int(d_exp.get("fsc_sans_transit") or 0) == 1:
                fourn = None
                if d_exp.get("fsc_fournisseur_id"):
                    fourn = conn.execute(
                        "SELECT id, nom, licence, certificat FROM fournisseurs_fsc WHERE id=?",
                        (d_exp.get("fsc_fournisseur_id"),),
                    ).fetchone()
                negoce_direct = {
                    "fournisseur": dict(fourn) if fourn else None,
                    "bl_fournisseur": (d_exp.get("fsc_bl_fournisseur") or "").strip() or None,
                    "claim_entrant": d_exp.get("fsc_claim_entrant"),
                    "claim_sortant": d_exp.get("fsc_claim_sortant"),
                    "claim_label": _claim_label(d_exp.get("fsc_claim_sortant")),
                }

            # Preuve directe : les lots physiquement sortis pour ce départ.
            lots_expedies = _lots_expedies(conn, eid)

            if negoce_direct:
                ruptures_e = (
                    []
                    if negoce_direct["bl_fournisseur"]
                    else [
                        "Livraison directe sans n° de BL partenaire : le claim facturé "
                        "au client n'est adossé à aucun document."
                    ]
                )
            elif ref:
                ruptures_e = []
            elif int(d_exp.get("sans_dossier") or 0) == 1:
                # Déclaré hors production : chaîne courte mais COMPLÈTE. Le
                # motif tient lieu de preuve, comme le BL partenaire tient lieu
                # de preuve pour une livraison directe. Signaler une rupture
                # ici reviendrait à reprocher à une expédition de palettes
                # vides de ne pas avoir consommé de bobines.
                ruptures_e = []
            else:
                ruptures_e = [
                    "Cette expédition n'est rattachée à aucun dossier et ne déclare "
                    "aucun motif : la chaîne ne peut pas remonter jusqu'à la matière, "
                    "et rien ne dit si c'est normal."
                ]

            hors_production = (
                None if int(d_exp.get("sans_dossier") or 0) != 1
                else {
                    "motif": d_exp.get("sans_dossier_motif"),
                    "motif_label": EXPE_MOTIFS_SANS_DOSSIER.get(
                        (d_exp.get("sans_dossier_motif") or ""),
                        d_exp.get("sans_dossier_motif") or "",
                    ),
                    "note": d_exp.get("sans_dossier_note"),
                    "declare_par": d_exp.get("sans_dossier_par"),
                    "declare_le": d_exp.get("sans_dossier_le"),
                }
            )

            # Une expédition de marchandise fabriquée sans lot rattaché n'est
            # pas fausse — c'est le cas de toutes celles antérieures au suivi.
            # Mais l'auditeur doit savoir qu'il lit une déduction par le
            # dossier et non la sortie physique elle-même.
            if not negoce_direct and not hors_production and not lots_expedies:
                ruptures_e = ruptures_e + [
                    "Aucun lot rattaché à cette sortie : le lien entre les palettes "
                    "parties et le dossier repose sur une déduction, pas sur "
                    "l'enregistrement de la sortie."
                ]

            return {
                "racine": {"type": "expedition", "id": key},
                "expedition": d_exp,
                "reconstitue": (d_exp.get("dossier_source") or "") == "reconstitue",
                "negoce_direct": negoce_direct,
                "hors_production": hors_production,
                "lots_expedies": lots_expedies,
                "dossiers": branches,
                "synthese": {
                    "nb_dossiers": len(branches),
                    # Vente mixte : le claim ne peut pas être porté globalement
                    # sur le document, il doit l'être ligne par ligne.
                    "fsc_mixte": len({
                        (b.get("dossier") or {}).get("fsc_type_requis") or ""
                        if int((b.get("dossier") or {}).get("fsc_requis") or 0) else "non_fsc"
                        for b in branches
                    }) > 1,
                    "nb_lots_expedies": len(lots_expedies),
                    "quantite_expediee": sum(
                        float(l.get("quantite") or 0) for l in lots_expedies
                    ),
                    "preuve_sortie": "directe" if lots_expedies else "deduite",
                    "origine": (
                        "negoce_direct" if negoce_direct
                        else "fabrication" if ref
                        else "hors_production" if hors_production
                        else "inconnue"
                    ),
                    "ruptures": ruptures_e,
                    "tronque": False,
                },
            }

        if t == "produit":
            try:
                pid = int(key)
            except ValueError:
                raise HTTPException(400, "Identifiant produit invalide.")
            prod = conn.execute("SELECT * FROM produits WHERE id=?", (pid,)).fetchone()
            if not prod:
                raise HTTPException(404, "Produit introuvable.")
            refs = [
                r["ref"]
                for r in conn.execute(
                    # GROUP BY + MAX() plutôt que DISTINCT + ORDER BY MAX() :
                    # SQLite refuse un agrégat dans le ORDER BY d'une requête
                    # non groupée (« misuse of aggregate »). Les dossiers les
                    # plus récents remontent en premier.
                    """SELECT TRIM(COALESCE(no_dossier,'')) AS ref,
                              MAX(created_at) AS dernier_lot
                         FROM lots_stock
                        WHERE produit_id=? AND TRIM(COALESCE(no_dossier,''))<>''
                        GROUP BY ref
                        ORDER BY dernier_lot DESC
                        LIMIT ?""",
                    (pid, _MAX_NOEUDS),
                ).fetchall()
            ]
            branches = [_chaine_dossier(conn, r) for r in refs]
            negoce = _negoce_du_produit(conn, pid)

            # Un produit acheté fini a une chaîne courte mais complète. On ne
            # signale une rupture que s'il n'a NI dossier de fabrication NI
            # réception de négoce — c'est-à-dire si son origine est vraiment
            # inconnue.
            if refs:
                ruptures_p: list[str] = []
            elif negoce:
                ruptures_p = []
            else:
                ruptures_p = [
                    "Aucune origine connue pour ce produit : ni dossier de fabrication, "
                    "ni réception de négoce."
                ]
            return {
                "racine": {"type": "produit", "id": key},
                "produit": dict(prod),
                "dossiers": branches,
                "negoce": negoce,
                "synthese": {
                    "nb_dossiers": len(refs),
                    "nb_expeditions": sum(len(b["expeditions"]) for b in branches),
                    "nb_receptions_negoce": len(negoce),
                    "origine": (
                        "fabrication" if refs and not negoce
                        else "negoce" if negoce and not refs
                        else "mixte" if refs and negoce
                        else "inconnue"
                    ),
                    "ruptures": ruptures_p,
                    "tronque": len(refs) >= _MAX_NOEUDS,
                },
            }

    raise HTTPException(400, f"Type de point d'entrée inconnu : {type}")
