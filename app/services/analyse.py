from datetime import datetime
from collections import defaultdict
from database import parse_datetime
from config import CODE_ARRIVEE, CODE_DEPART, CODE_DEBUT_DOS, CODE_FIN_DOS

# ─── Analyse erreurs de saisie ────────────────────────────────────
def analyse_saisie_errors(rows):
    """
    Détecte les erreurs de saisie structurelles :
    - Absence d'arrivée personnel en début de journée
    - Absence de départ personnel en fin de journée
    - Dossier sans début ou sans fin
    Retourne une liste d'erreurs enrichies.
    """
    errors = []

    # Grouper par opérateur + jour
    # (on met en cache parse_datetime pour éviter de le recalculer plusieurs fois)
    dt_cache = {}
    by_op_day = defaultdict(list)
    for r in rows:
        op = r["operateur"] or "?"
        dt = parse_datetime(r["date_operation"])
        dt_cache[id(r)] = dt
        if dt:
            day_key = dt.date().isoformat()
        else:
            day_key = (r["date_operation"] or "")[:10]
        by_op_day[(op, day_key)].append(r)

    for (operateur, jour), lignes in by_op_day.items():
        # Trier par heure
        lignes_sorted = sorted(
            lignes,
            key=lambda r: dt_cache.get(id(r)) or datetime.min
        )

        codes = [r["operation_code"] for r in lignes_sorted]
        first_op = lignes_sorted[0]
        last_op  = lignes_sorted[-1]

        # ── Erreur 1 : Pas d'arrivée personnel ──────────────────────
        if CODE_ARRIVEE not in codes:
            errors.append({
                "type": "absence_arrivee",
                "severity": "critique",
                "operateur": operateur,
                "jour": jour,
                "message": f"Arrivée personnel (86) manquante",
                "detail": f"Première saisie à {(dt_cache.get(id(first_op)) or '?')}",
                "date_operation": first_op["date_operation"],
                "machine": first_op.get("machine", ""),
                "no_dossier": first_op.get("no_dossier", ""),
            })

        # ── Erreur 2 : Pas de départ personnel ──────────────────────
        if CODE_DEPART not in codes:
            errors.append({
                "type": "absence_depart",
                "severity": "critique",
                "operateur": operateur,
                "jour": jour,
                "message": f"Départ personnel (87) manquant",
                "detail": f"Dernière saisie à {(dt_cache.get(id(last_op)) or '?')}",
                "date_operation": last_op["date_operation"],
                "machine": last_op.get("machine", ""),
                "no_dossier": last_op.get("no_dossier", ""),
            })

        # ── Erreur 3 : Dossiers sans début ou sans fin ───────────────
        # Grouper les lignes par no_dossier (hors dossier "0" ou vide)
        dossiers_du_jour = defaultdict(list)
        for r in lignes_sorted:
            dos = r.get("no_dossier", "") or ""
            if dos and dos not in ("0", ""):
                dossiers_du_jour[dos].append(r["operation_code"])

        for dos, dos_codes in dossiers_du_jour.items():
            has_debut = CODE_DEBUT_DOS in dos_codes
            has_fin   = CODE_FIN_DOS   in dos_codes

            if not has_debut and not has_fin:
                errors.append({
                    "type": "dossier_sans_debut_fin",
                    "severity": "critique",
                    "operateur": operateur,
                    "jour": jour,
                    "message": f"Dossier {dos} : Début (01) ET Fin (89) manquants",
                    "detail": f"Codes saisis : {', '.join(sorted(set(dos_codes)))}",
                    "date_operation": lignes_sorted[0]["date_operation"],
                    "machine": next((r.get("machine","") for r in lignes_sorted if r.get("no_dossier")==dos), ""),
                    "no_dossier": dos,
                })
            elif not has_debut:
                errors.append({
                    "type": "dossier_sans_debut",
                    "severity": "critique",
                    "operateur": operateur,
                    "jour": jour,
                    "message": f"Dossier {dos} : Début dossier (01) manquant",
                    "detail": f"Codes saisis : {', '.join(sorted(set(dos_codes)))}",
                    "date_operation": lignes_sorted[0]["date_operation"],
                    "machine": next((r.get("machine","") for r in lignes_sorted if r.get("no_dossier")==dos), ""),
                    "no_dossier": dos,
                })
            elif not has_fin:
                errors.append({
                    "type": "dossier_sans_fin",
                    "severity": "critique",
                    "operateur": operateur,
                    "jour": jour,
                    "message": f"Dossier {dos} : Fin dossier (89) manquante",
                    "detail": f"Codes saisis : {', '.join(sorted(set(dos_codes)))}",
                    "date_operation": lignes_sorted[0]["date_operation"],
                    "machine": next((r.get("machine","") for r in lignes_sorted if r.get("no_dossier")==dos), ""),
                    "no_dossier": dos,
                })

    return errors
