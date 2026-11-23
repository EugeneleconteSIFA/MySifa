"""
Répartir un cycle de production sur plusieurs dossiers d'une même commande.

Cas réel (20/11/2026, Cohésio 1) : l'opérateur du matin reprend « 9932856 - L8 »
à 6 h 39 et enchaîne L8, L5 et L7 — même format, même outil, changement de
cliché — sans jamais changer de dossier dans MyProd. Le cycle porte alors
19 162 m et toute la matinée sur L8, et L5 / L7 restent sans aucune saisie.

`appliquer()` découpe ce cycle en cycles successifs, un par dossier, comme si
l'opérateur avait fait ses changements de dossier :

    01 L8 … 03 L8 ─────────────────────────────────── 89 L8 (cycle saisi)
    01 L8 … 03 L8 ──── 89 L8 · 01 L5 · 03 L5 ──── 89 L5 · 01 L7 · 03 L7 ── 89 L7

Les heures et les relevés compteur des coupures sont calculés au prorata des
quantités déclarées, entre le début de production et la fin du cycle. Ce ne
sont pas des relevés : les lignes créées sont marquées « Manuel » et portent
la répartition dans `data.repartition`. Le reste de l'application (planning,
temps, métrage, rentabilité, retour de prod) lit ces saisies comme les autres :
c'est tout l'intérêt de découper plutôt que d'inventer une saisie à plusieurs
dossiers.

Règles :
- la saisie de départ est une fin de production (89) non annulée ;
- le premier dossier de la répartition est celui du cycle (il a le démarrage
  et le calage) ; les suivants sont d'autres dossiers de la MÊME commande
  (même référence sans le suffixe de ligne « - L5 ») sur la même machine ;
- les saisies faites pendant le cycle (arrêts, reprises) suivent le dossier
  dans lequel elles tombent ;
- chaque dossier intermédiaire est clôturé ; le dernier garde le choix de la
  fin de production d'origine (terminé / à reprendre).
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional

FMT = "%Y-%m-%dT%H:%M:%S"
_SUFFIXE_LIGNE = re.compile(r"\s*[-–]?\s*L\s*\d+\s*$", re.IGNORECASE)


def cle_commande(reference: str) -> str:
    """« 9932856 - L8 » → « 9932856 ». Une référence sans ligne reste telle quelle."""
    ref = str(reference or "").strip()
    return _SUFFIXE_LIGNE.sub("", ref).strip() or ref


def _dt(v) -> Optional[datetime]:
    s = str(v or "").strip()[:19]
    for f in (FMT, "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def _code(r) -> str:
    return str(r["operation_code"] or "").strip()


def _num(v) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _lire_fin(conn, fin_id: int) -> dict:
    r = conn.execute("SELECT * FROM production_data WHERE id = ?", (int(fin_id),)).fetchone()
    if not r:
        raise ValueError("Saisie introuvable.")
    fin = dict(r)
    if _code(fin) != "89":
        raise ValueError("Seule une fin de production se répartit sur plusieurs dossiers.")
    if int(fin.get("est_annule") or 0):
        raise ValueError("Saisie annulée avec le dossier — répartition impossible.")
    if not str(fin.get("no_dossier") or "").strip() or not str(fin.get("machine") or "").strip():
        raise ValueError("Fin de production sans dossier ou sans machine.")
    return fin


def cycle(conn, fin_id: int) -> dict:
    """Le cycle que ferme la fin de production : démarrage, début de production, saisies."""
    fin = _lire_fin(conn, fin_id)
    ref = fin["no_dossier"].strip()
    machine = fin["machine"].strip()
    avant = conn.execute(
        """SELECT * FROM production_data
            WHERE trim(no_dossier) = ? AND trim(machine) = ?
              AND COALESCE(est_annule, 0) = 0
              AND (date_operation < ? OR (date_operation = ? AND id < ?))
            ORDER BY date_operation DESC, id DESC""",
        (ref, machine, fin["date_operation"], fin["date_operation"], fin["id"]),
    ).fetchall()
    lignes, demarrage = [], None
    for r in avant:
        r = dict(r)
        if _code(r) in ("89", "90"):
            break
        lignes.append(r)
        if _code(r) == "01":
            demarrage = r
            break
    lignes.reverse()
    prod = next((r for r in lignes if (r.get("operation_category") or "") == "production"), None)
    if prod is None:
        raise ValueError("Aucune saisie « Production » dans ce cycle : rien à répartir.")
    t0, t1 = _dt(prod["date_operation"]), _dt(fin["date_operation"])
    if not t0 or not t1 or t1 <= t0:
        raise ValueError("Dates du cycle illisibles.")

    c0 = _num(prod.get("metrage_compteur"))
    if c0 is None and demarrage:
        c0 = _num(demarrage.get("metrage_total_debut"))
        if c0 is None:
            c0 = _num(demarrage.get("metrage_prevu"))
    c1 = _num(fin.get("metrage_total_fin"))
    if c1 is None:
        c1 = _num(fin.get("metrage_reel"))
    if c0 is None or c1 is None or c1 <= c0:
        c0 = c1 = None

    return {
        "fin": fin, "demarrage": demarrage, "production": prod, "lignes": lignes,
        "no_dossier": ref, "machine": machine,
        "debut": t0, "fin_dt": t1, "compteur_debut": c0, "compteur_fin": c1,
    }


def candidats(conn, fin: dict) -> list:
    """Les autres dossiers de la même commande au planning de la même machine."""
    ref = fin["no_dossier"].strip()
    cle = cle_commande(ref)
    pe_cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
    of_join = "LEFT JOIN of_imports o ON o.id = pe.of_import_id" if "of_import_id" in pe_cols else ""
    of_qte = "o.qte_etiquettes" if of_join else "NULL"
    ref_prod = "pe.ref_produit" if "ref_produit" in pe_cols else "NULL"
    lignes = conn.execute(
        f"""SELECT pe.id, trim(pe.reference) AS reference, pe.client, pe.statut,
                   {ref_prod} AS ref_produit, {of_qte} AS qte_of
              FROM planning_entries pe
              JOIN machines m ON m.id = pe.machine_id
              {of_join}
             WHERE (trim(m.nom) = ? OR (trim(COALESCE(m.code,'')) <> '' AND trim(m.code) = ?))
               AND trim(pe.reference) LIKE ?""",
        (fin["machine"].strip(), fin["machine"].strip(), cle + "%"),
    ).fetchall()
    out, vus = [], set()
    for r in lignes:
        r = dict(r)
        nd = r["reference"]
        if nd == ref or nd in vus or cle_commande(nd) != cle:
            continue
        vus.add(nd)
        nb = conn.execute(
            """SELECT COUNT(*) FROM production_data
                WHERE trim(no_dossier) = ? AND COALESCE(est_annule, 0) = 0""",
            (nd,),
        ).fetchone()[0]
        out.append({"no_dossier": nd, "client": r["client"], "statut": r["statut"],
                    "ref_produit": r["ref_produit"], "qte_of": r["qte_of"], "nb_saisies": nb})
    out.sort(key=lambda d: d["no_dossier"])
    return out


def _lire_parts(parts, cy: dict, autorises: set) -> list:
    if not isinstance(parts, list) or len(parts) < 2:
        raise ValueError("Ajouter au moins un autre dossier de la commande.")
    propres, vus = [], set()
    for p in parts:
        nd = str((p or {}).get("no_dossier") or "").strip()
        q = _num(str((p or {}).get("quantite") or "").replace(" ", "").replace(" ", "").replace(",", "."))
        if not nd:
            raise ValueError("Dossier manquant dans la répartition.")
        if nd in vus:
            raise ValueError(f"{nd} figure deux fois dans la répartition.")
        if q is None or q <= 0:
            raise ValueError(f"Quantité invalide pour {nd} — nombre d'étiquettes supérieur à 0.")
        vus.add(nd)
        propres.append({"no_dossier": nd, "quantite": q})
    if propres[0]["no_dossier"] != cy["no_dossier"]:
        raise ValueError(f"Le premier dossier doit être celui du cycle : {cy['no_dossier']}.")
    for p in propres[1:]:
        if p["no_dossier"] not in autorises:
            raise ValueError(f"{p['no_dossier']} n'est pas un dossier de la commande "
                             f"{cle_commande(cy['no_dossier'])} au planning de {cy['machine']}.")
    return propres


def plan(conn, fin_id: int, parts) -> dict:
    """Calcule la répartition sans rien écrire."""
    cy = cycle(conn, fin_id)
    cands = candidats(conn, cy["fin"])
    parts = _lire_parts(parts, cy, {c["no_dossier"] for c in cands})
    total = sum(p["quantite"] for p in parts)
    duree = (cy["fin_dt"] - cy["debut"]).total_seconds()
    c0, c1 = cy["compteur_debut"], cy["compteur_fin"]

    segments, cumul, debut, ctr = [], 0.0, cy["debut"], c0
    for i, p in enumerate(parts):
        cumul += p["quantite"]
        dernier = i == len(parts) - 1
        fin = cy["fin_dt"] if dernier else cy["debut"] + timedelta(seconds=round(duree * cumul / total))
        ctr_fin = c1 if dernier or c0 is None else round(c0 + (c1 - c0) * cumul / total)
        # Les lignes créées à la coupure (fin, démarrage, production) prennent
        # trois secondes : un segment plus court les mélangerait au suivant.
        if (fin - debut).total_seconds() < (3 if i == 0 else 6):
            raise ValueError("Cycle trop court pour cette répartition.")
        segments.append({
            "no_dossier": p["no_dossier"], "quantite": p["quantite"],
            "debut": debut.strftime(FMT), "fin": fin.strftime(FMT),
            "minutes": round((fin - debut).total_seconds() / 60, 1),
            "compteur_debut": ctr, "compteur_fin": ctr_fin,
            "metres": (ctr_fin - ctr) if ctr is not None and ctr_fin is not None else None,
        })
        debut, ctr = fin, ctr_fin
    return {
        "no_dossier": cy["no_dossier"], "machine": cy["machine"],
        "debut": cy["debut"].strftime(FMT), "fin": cy["fin_dt"].strftime(FMT),
        "minutes": round(duree / 60, 1),
        "compteur_debut": c0, "compteur_fin": c1,
        "metres": (c1 - c0) if c0 is not None else None,
        "quantite_saisie": _num(cy["fin"].get("quantite_traitee")),
        "segments": segments,
    }


def apercu(conn, fin_id: int) -> dict:
    """Ce que la fenêtre affiche à l'ouverture : le cycle et les dossiers ajoutables."""
    cy = cycle(conn, fin_id)
    duree = (cy["fin_dt"] - cy["debut"]).total_seconds()
    c0, c1 = cy["compteur_debut"], cy["compteur_fin"]
    return {
        "no_dossier": cy["no_dossier"], "machine": cy["machine"],
        "commande": cle_commande(cy["no_dossier"]),
        "debut": cy["debut"].strftime(FMT), "fin": cy["fin_dt"].strftime(FMT),
        "minutes": round(duree / 60, 1),
        "metres": (c1 - c0) if c0 is not None else None,
        "quantite_saisie": _num(cy["fin"].get("quantite_traitee")),
        "candidats": candidats(conn, cy["fin"]),
    }


def _operateur_a(lignes: list, quand: datetime, defaut: str) -> str:
    op = defaut
    for r in lignes:
        d = _dt(r["date_operation"])
        if d and d <= quand and str(r.get("operateur") or "").strip():
            op = r["operateur"]
    return op


def appliquer(conn, fin_id: int, parts, auteur_email: str, auteur_nom: str) -> dict:
    """Découpe le cycle. Écrit les saisies, puis rejoue la clôture de chaque dossier."""
    p = plan(conn, fin_id, parts)
    cy = cycle(conn, fin_id)
    fin = cy["fin"]
    segs = p["segments"]
    maintenant = datetime.now().isoformat()
    noms = ", ".join(s["no_dossier"] for s in segs)
    note = f"Répartition du cycle {cy['no_dossier']} : {noms} (prorata des quantités)"
    trace = {"fin_id": int(fin_id), "par": auteur_email, "le": maintenant,
             "dossiers": [{"no_dossier": s["no_dossier"], "quantite": s["quantite"]} for s in segs]}

    clients = {}
    for s in segs:
        r = conn.execute(
            "SELECT client FROM planning_entries WHERE trim(reference) = ? AND COALESCE(client,'') <> '' LIMIT 1",
            (s["no_dossier"],),
        ).fetchone()
        clients[s["no_dossier"]] = (r[0] if r else None) or fin.get("client")

    op_demarrer = (cy["demarrage"] or {}).get("operation") or "01 - Démarrer un dossier"
    op_production = cy["production"].get("operation") or "03 - Production"
    op_fin = fin.get("operation") or "89 - Fin de production"
    from config import classify_operation

    def inserer(operation, quand, dossier, operateur, **champs):
        cl = classify_operation(operation)
        data = {"operateur": operateur, "date_operation": quand, "operation": operation,
                "no_dossier": dossier, "machine": cy["machine"], "repartition": trace}
        data.update({k: v for k, v in champs.items() if v is not None})
        cur = conn.execute(
            """INSERT INTO production_data
               (import_id, operateur, date_operation, operation, operation_code,
                operation_severity, operation_category, service, machine, no_dossier,
                client, designation, quantite_a_traiter, quantite_traitee,
                metrage_reel, metrage_total_debut, metrage_total_fin,
                data, est_manuel, modifie_par, modifie_le, modifie_note)
               VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
            (operateur, quand, operation, cl["code"], cl["severity"], cl["category"],
             fin.get("service"), cy["machine"], dossier, clients.get(dossier),
             fin.get("designation"), fin.get("quantite_a_traiter"),
             champs.get("quantite_traitee") or 0,
             champs.get("metrage_reel"), champs.get("metrage_total_debut"),
             champs.get("metrage_total_fin"),
             json.dumps(data, default=str), auteur_email, maintenant, note),
        )
        return cur.lastrowid

    crees = []
    for i, s in enumerate(segs[:-1]):
        suivant = segs[i + 1]["no_dossier"]
        coupure = _dt(s["fin"])
        op = _operateur_a(cy["lignes"], coupure, fin["operateur"])
        crees.append(("fin", s["no_dossier"], inserer(
            op_fin, coupure.strftime(FMT), s["no_dossier"], op,
            quantite_traitee=s["quantite"],
            metrage_reel=s["compteur_fin"], metrage_total_fin=s["compteur_fin"])))
        crees.append(("demarrage", suivant, inserer(
            op_demarrer, (coupure + timedelta(seconds=1)).strftime(FMT), suivant, op,
            metrage_total_debut=s["compteur_fin"])))
        crees.append(("production", suivant, inserer(
            op_production, (coupure + timedelta(seconds=2)).strftime(FMT), suivant, op)))

    # Les saisies faites pendant le cycle suivent le dossier où elles tombent.
    bornes = [(_dt(s["debut"]), s["no_dossier"]) for s in segs]
    deplacees = []
    for r in cy["lignes"]:
        d = _dt(r["date_operation"])
        if not d or d <= cy["debut"]:
            continue
        cible = segs[0]["no_dossier"]
        for debut, nd in bornes:
            if d >= debut:
                cible = nd
        if cible != cy["no_dossier"]:
            conn.execute("UPDATE production_data SET no_dossier = ?, client = ? WHERE id = ?",
                         (cible, clients.get(cible), r["id"]))
            deplacees.append(r["id"])

    dernier = segs[-1]
    data_fin = json.loads(fin["data"]) if fin.get("data") else {}
    data_fin["repartition"] = trace
    data_fin["no_dossier"] = dernier["no_dossier"]
    data_fin["quantite_traitee"] = dernier["quantite"]
    choix_origine = fin.get("fin_dossier")
    conn.execute(
        """UPDATE production_data
              SET no_dossier = ?, client = ?, quantite_traitee = ?, fin_dossier = NULL,
                  modifie_par = ?, modifie_le = ?, modifie_note = ?, data = ?
            WHERE id = ?""",
        (dernier["no_dossier"], clients.get(dernier["no_dossier"]), dernier["quantite"],
         auteur_email, maintenant, note, json.dumps(data_fin, default=str), fin["id"]),
    )

    from app.services.lien_saisie_planning import rattacher
    for _, _, sid in crees:
        rattacher(conn, sid, forcer=True)
    for sid in deplacees:
        rattacher(conn, sid, forcer=True)
    rattacher(conn, fin["id"], forcer=True)
    conn.commit()

    # Clôtures : comme si chaque fin avait été saisie.
    from app.services.cloture_saisie import changer
    clotures = []
    for genre, nd, sid in crees:
        if genre == "fin":
            try:
                clotures.append(changer(conn, sid, True, auteur_nom))
            except ValueError:
                pass
    try:
        garder = True if choix_origine is None else bool(int(choix_origine))
        clotures.append(changer(conn, fin["id"], garder, auteur_nom))
    except ValueError:
        pass

    return {"plan": p, "crees": [sid for _, _, sid in crees],
            "deplacees": deplacees, "clotures": clotures}
