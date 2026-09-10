"""Ce qui est monté sur les postes de déroulement de chaque machine.

Règles d'atelier (10/09/2026), et ce que le module en fait
---------------------------------------------------------
- Un poste porte au plus `places` bobines (deux sur une Cohésio : celle qui
  roule et celle qui prendra le relais). Monter une bobine sur un poste plein
  démonte la PLUS ANCIENNE : c'est celle qui a fini de rouler, celle qu'on
  change. Le démontage garde le lien vers la bobine qui l'a remplacée, pour
  pouvoir le défaire si le scan est annulé.
- Rescanner une bobine déjà montée ne change rien à l'état.
- Une bobine scannée sur une autre machine y est démontée : elle a été
  déplacée, elle ne peut pas être à deux endroits.
- Une bobine dont on ignore la nature est montée « en attente de poste » :
  elle n'occupe aucune place tant que personne n'a tranché.
- Rien n'est effacé : un montage se FERME (demonte_at). Le seul cas où l'on
  défait est l'annulation du scan qui l'avait créé.

Une machine sans poste configuré (repiquage) n'a pas d'état : `monter` rend
`sans_poste` et n'écrit rien.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from config import poste_pour_categorie
from app.services.poste_bobine import postes_machine, _norm_categorie, _label_poste


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _ligne(conn, montee_id: int) -> Optional[Dict[str, Any]]:
    r = conn.execute("SELECT * FROM bobines_montees WHERE id=?", (int(montee_id),)).fetchone()
    return dict(r) if r else None


def _fermer(conn, montee_id: int, motif: str, par: str, quand: str,
            remplacee_par: Optional[int] = None) -> None:
    conn.execute(
        """UPDATE bobines_montees
              SET demonte_at=?, demonte_par=?, motif_demontage=?, remplacee_par_id=?
            WHERE id=? AND demonte_at IS NULL""",
        (quand, par, motif, remplacee_par, int(montee_id)),
    )


def _liberer_places(conn, machine_id: int, poste: str, places: int,
                    garder_id: int, par: str, quand: str) -> List[Dict[str, Any]]:
    """Démonte les plus anciennes jusqu'à retomber dans le nombre de places."""
    actives = conn.execute(
        """SELECT * FROM bobines_montees
            WHERE machine_id=? AND poste=? AND demonte_at IS NULL
         ORDER BY monte_at ASC, id ASC""",
        (int(machine_id), poste),
    ).fetchall()
    trop = len(actives) - max(int(places), 0)
    sorties = []
    for r in actives:
        if trop <= 0:
            break
        if int(r["id"]) == int(garder_id):
            continue
        _fermer(conn, r["id"], "remplacee", par, quand, remplacee_par=garder_id)
        sorties.append(dict(r))
        trop -= 1
    return sorties


def monter(conn, machine_id: int, code_barre: str, *, categorie: Optional[str] = None,
           poste: Optional[str] = None, fab_matiere_id: Optional[int] = None,
           no_dossier: Optional[str] = None, par: str = "",
           source: Optional[str] = None, confiance: Optional[str] = None) -> Dict[str, Any]:
    code = (code_barre or "").strip()
    if not code:
        raise ValueError("Code barre manquant.")
    postes = {p["poste"]: p for p in postes_machine(conn, machine_id)}
    if not postes:
        return {"action": "sans_poste", "montee": None, "demontees": []}

    cat = _norm_categorie(categorie)
    p = poste or poste_pour_categorie(cat)
    if p not in postes:
        p = None
    quand = _maintenant()

    actives = conn.execute(
        "SELECT * FROM bobines_montees WHERE trim(code_barre)=trim(?) AND demonte_at IS NULL "
        "ORDER BY monte_at DESC, id DESC",
        (code,),
    ).fetchall()
    for r in actives:
        if int(r["machine_id"]) != int(machine_id):
            _fermer(conn, r["id"], "deplacee", par, quand)
    ici = next((dict(r) for r in actives if int(r["machine_id"]) == int(machine_id)), None)

    if ici:
        meme = (ici["poste"] == p) or (p is None)
        if meme:
            if cat and not ici["categorie"]:
                conn.execute("UPDATE bobines_montees SET categorie=? WHERE id=?", (cat, ici["id"]))
            return {"action": "deja_montee", "montee": _ligne(conn, ici["id"]), "demontees": []}
        conn.execute(
            "UPDATE bobines_montees SET poste=?, categorie=?, poste_source=?, poste_confiance=? WHERE id=?",
            (p, cat or ici["categorie"], source, confiance, ici["id"]),
        )
        sorties = _liberer_places(conn, machine_id, p, postes[p]["places"], ici["id"], par, quand)
        return {"action": "poste_corrige", "montee": _ligne(conn, ici["id"]), "demontees": sorties}

    mid = conn.execute(
        """INSERT INTO bobines_montees
               (machine_id, poste, categorie, code_barre, fab_matiere_id, no_dossier,
                poste_source, poste_confiance, monte_at, monte_par)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (int(machine_id), p, cat, code, fab_matiere_id, no_dossier,
         source, confiance, quand, par),
    ).lastrowid
    sorties = []
    if p:
        sorties = _liberer_places(conn, machine_id, p, postes[p]["places"], mid, par, quand)
    return {"action": "montee", "montee": _ligne(conn, mid), "demontees": sorties}


def fixer_poste(conn, fab_matiere_id: int, categorie: str, par: str = "",
                source: str = "saisie", confiance: str = "certain") -> Dict[str, Any]:
    """L'opérateur (ou une correction) arrête la nature d'une bobine déjà scannée."""
    cat = _norm_categorie(categorie)
    if not cat:
        raise ValueError("Catégorie invalide — frontal, complexe ou glassine.")
    fmu = conn.execute(
        "SELECT id, machine_id, code_barre, no_dossier FROM fab_matieres_utilisees WHERE id=?",
        (int(fab_matiere_id),),
    ).fetchone()
    if not fmu:
        raise LookupError("Scan introuvable.")
    conn.execute(
        """UPDATE fab_matieres_utilisees
              SET categorie_bobine=?, poste=?, poste_source=?, poste_confiance=?
            WHERE id=?""",
        (cat, poste_pour_categorie(cat), source, confiance, int(fab_matiere_id)),
    )
    if fmu["machine_id"] is None:
        return {"action": "sans_poste", "montee": None, "demontees": []}
    return monter(conn, int(fmu["machine_id"]), fmu["code_barre"], categorie=cat,
                  fab_matiere_id=int(fab_matiere_id), no_dossier=fmu["no_dossier"],
                  par=par, source=source, confiance=confiance)


def demonter(conn, montee_id: int, par: str = "", motif: str = "retiree") -> Dict[str, Any]:
    r = _ligne(conn, montee_id)
    if not r:
        raise LookupError("Montage introuvable.")
    if r["demonte_at"]:
        return r
    _fermer(conn, montee_id, motif, par, _maintenant())
    return _ligne(conn, montee_id)


def annuler_scan(conn, fab_matiere_id: int) -> int:
    """Défait le montage créé par un scan supprimé, et rend leur place aux bobines qu'il avait poussées.

    C'est le seul endroit où une ligne disparaît : un scan annulé n'a jamais
    monté de bobine, garder sa trace ferait croire le contraire.
    """
    lignes = conn.execute(
        "SELECT id, machine_id, code_barre FROM bobines_montees WHERE fab_matiere_id=?",
        (int(fab_matiere_id),),
    ).fetchall()
    n = 0
    for r in lignes:
        # La même bobine rescannée ensuite sur ce poste (dossier suivant) : le
        # montage reste vrai, il change seulement de scan de référence.
        autre = conn.execute(
            """SELECT id FROM fab_matieres_utilisees
                WHERE id<>? AND machine_id=? AND trim(code_barre)=trim(?)
             ORDER BY scanned_at ASC, id ASC LIMIT 1""",
            (int(fab_matiere_id), r["machine_id"], r["code_barre"]),
        ).fetchone()
        if autre:
            conn.execute("UPDATE bobines_montees SET fab_matiere_id=? WHERE id=?",
                         (int(autre["id"]), int(r["id"])))
            continue
        n += 1
        conn.execute(
            """UPDATE bobines_montees
                  SET demonte_at=NULL, demonte_par=NULL, motif_demontage=NULL, remplacee_par_id=NULL
                WHERE remplacee_par_id=? AND motif_demontage='remplacee'""",
            (int(r["id"]),),
        )
        conn.execute("DELETE FROM bobines_montees WHERE id=?", (int(r["id"]),))
    return n


def changer_code(conn, fab_matiere_id: int, code_barre: str) -> int:
    """Suit la correction d'un code-barres mal scanné."""
    return conn.execute(
        "UPDATE bobines_montees SET code_barre=? WHERE fab_matiere_id=? AND demonte_at IS NULL",
        ((code_barre or "").strip(), int(fab_matiere_id)),
    ).rowcount


def scan_en_double(conn, machine_id: int, code_barre: str, no_dossier: Optional[str]) -> Optional[int]:
    """Le scan existant quand la bobine est déjà montée ici ET déjà scannée sur ce dossier."""
    if not conn.execute(
        "SELECT 1 FROM bobines_montees WHERE machine_id=? AND trim(code_barre)=trim(?) "
        "AND demonte_at IS NULL LIMIT 1",
        (int(machine_id), code_barre),
    ).fetchone():
        return None
    r = conn.execute(
        """SELECT id FROM fab_matieres_utilisees
            WHERE machine_id=? AND trim(code_barre)=trim(?)
              AND COALESCE(no_dossier,'')=COALESCE(?,'')
         ORDER BY scanned_at DESC, id DESC LIMIT 1""",
        (int(machine_id), code_barre, no_dossier),
    ).fetchone()
    return int(r["id"]) if r else None


def etat_machine(conn, machine_id: int) -> Dict[str, Any]:
    """Les postes d'une machine et les bobines qui y sont montées."""
    actives = [dict(r) for r in conn.execute(
        """SELECT bm.*, COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
                  (SELECT f2.no_dossier FROM fab_matieres_utilisees f2
                    WHERE f2.machine_id = bm.machine_id AND trim(f2.code_barre) = trim(bm.code_barre)
                 ORDER BY f2.scanned_at DESC, f2.id DESC LIMIT 1) AS dernier_dossier
             FROM bobines_montees bm
        LEFT JOIN fab_matieres_utilisees fmu ON fmu.id = bm.fab_matiere_id
        LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
            WHERE bm.machine_id=? AND bm.demonte_at IS NULL
         ORDER BY bm.monte_at ASC, bm.id ASC""",
        (int(machine_id),),
    ).fetchall()]
    postes = []
    for p in postes_machine(conn, machine_id):
        bobines = [b for b in actives if b["poste"] == p["poste"]]
        postes.append(dict(p, bobines=bobines, libres=max(p["places"] - len(bobines), 0)))
    connus = {p["poste"] for p in postes}
    return {
        "machine_id": int(machine_id),
        "postes": postes,
        "en_attente": [b for b in actives if b["poste"] not in connus],
    }


# ══ Lot 4 — reprise des bobines en place au début de production ══════════════

def _copier_scan(conn, source_id: int, machine_id: int, machine_nom: str, no_dossier: str,
                 par: str, quand: str, montee: Dict[str, Any]) -> int:
    """Une ligne de consommation pour le nouveau dossier, héritée d'un scan réel.

    L'origine (réception, fournisseur, certificat) est RECOPIÉE et non
    recalculée : c'est la même bobine, sa preuve d'origine ne change pas
    parce qu'elle passe d'un dossier au suivant.
    """
    src = conn.execute("SELECT * FROM fab_matieres_utilisees WHERE id=?", (int(source_id),)).fetchone()
    src = dict(src) if src else {}
    return conn.execute(
        """INSERT INTO fab_matieres_utilisees
               (machine_id, machine_nom, operateur, no_dossier, code_barre, scanned_at,
                reception_id, liaison_mode, fournisseur_manual, certificat_fsc_manual,
                origine_detection, origine_confiance,
                categorie_bobine, poste, poste_source, poste_confiance, herite_de_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (int(machine_id), machine_nom or src.get("machine_nom"), par, no_dossier,
         montee["code_barre"], quand,
         src.get("reception_id"), src.get("liaison_mode"), src.get("fournisseur_manual"),
         src.get("certificat_fsc_manual"), src.get("origine_detection"), src.get("origine_confiance"),
         montee.get("categorie"), montee.get("poste"), "montee", "certain",
         int(source_id) if source_id else None),
    ).lastrowid


def reprendre(conn, machine_id: int, no_dossier: str, *, retirer: Optional[List[int]] = None,
              par: str = "", machine_nom: str = "") -> Dict[str, Any]:
    """Rattache au dossier qui démarre les bobines restées montées sur la machine.

    - `retirer` : les montages que l'opérateur a DÉCOCHÉS — ils sont démontés
      (motif « retiree ») et ne sont pas rattachés.
    - Tout le reste est rattaché, y compris une bobine de poste inconnu : dans
      le doute, la traçabilité prudente garde la bobine.
    - Exception : quand le poste frontal ne porte QUE des complexes, la
      glassine restée en place ne sert pas (un complexe a déjà son support).
      Elle reste montée — le dossier suivant pourra en hériter — mais n'est
      pas rattachée à celui-ci.
    - Une bobine déjà rattachée au dossier (reprise d'un dossier interrompu,
      scan fait avant le démarrage) n'est pas dupliquée.
    """
    ref = (no_dossier or "").strip()
    if not ref:
        raise ValueError("Référence dossier manquante.")
    quand = _maintenant()
    retirer_ids = {int(x) for x in (retirer or []) if str(x).strip().lstrip("-").isdigit()}

    retirees = []
    for mid_ in retirer_ids:
        r = _ligne(conn, mid_)
        if r and int(r["machine_id"]) == int(machine_id) and not r["demonte_at"]:
            _fermer(conn, mid_, "retiree", par, quand)
            retirees.append(r["code_barre"])

    actives = [dict(r) for r in conn.execute(
        "SELECT * FROM bobines_montees WHERE machine_id=? AND demonte_at IS NULL "
        "ORDER BY monte_at ASC, id ASC",
        (int(machine_id),),
    ).fetchall()]
    frontaux = [b for b in actives if b["poste"] == "frontal"]
    complexe_seul = bool(frontaux) and all(b["categorie"] == "complexe" for b in frontaux)

    rattachees, deja, glassine_gardee = [], [], []
    for b in actives:
        if complexe_seul and b["poste"] == "glassine":
            glassine_gardee.append(b["code_barre"])
            continue
        existe = conn.execute(
            """SELECT id FROM fab_matieres_utilisees
                WHERE machine_id=? AND trim(code_barre)=trim(?) AND trim(COALESCE(no_dossier,''))=?
                LIMIT 1""",
            (int(machine_id), b["code_barre"], ref),
        ).fetchone()
        if existe:
            deja.append(b["code_barre"])
            continue
        # Le dernier dossier qui l'a eue, pas celui du montage : c'est de lui
        # qu'elle est héritée, et la chaîne `herite_de_id` remonte au scan réel.
        prec = conn.execute(
            """SELECT id, no_dossier FROM fab_matieres_utilisees
                WHERE machine_id=? AND trim(code_barre)=trim(?)
             ORDER BY scanned_at DESC, id DESC LIMIT 1""",
            (int(machine_id), b["code_barre"]),
        ).fetchone()
        source_id = int(prec["id"]) if prec else b["fab_matiere_id"]
        nid = _copier_scan(conn, source_id, machine_id, machine_nom, ref, par, quand, b)
        rattachees.append({"id": nid, "code_barre": b["code_barre"], "poste": b["poste"],
                           "categorie": b["categorie"], "montee_id": b["id"],
                           "herite_de_id": source_id,
                           "dossier_origine": prec["no_dossier"] if prec else b["no_dossier"]})
    return {"rattachees": rattachees, "deja_rattachees": deja,
            "retirees": retirees, "glassine_non_rattachee": glassine_gardee}
