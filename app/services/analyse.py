from datetime import datetime, timedelta
from collections import defaultdict
from database import parse_datetime
from config import CODE_ARRIVEE, CODE_DEPART, CODE_DEBUT_DOS, CODE_FIN_DOS


# ─── Regroupement par "shift" (équipe / journée opérateur) ────────────
#
# Une journée d'opérateur n'est pas toujours calée sur le calendrier :
# l'équipe de nuit commence en soirée et termine le lendemain matin. Si on
# groupe par date civile, l'arrivée (86) et le départ (87) tombent sur deux
# dates différentes et déclenchent de faux positifs ("arrivée manquante",
# "départ manquant", "dossier sans fin", "arrivée→départ < 5h", etc.).
#
# Règle de regroupement (par opérateur, lignes triées chronologiquement) :
#  - Chaque ``CODE_ARRIVEE`` (86) ouvre un nouveau shift dont la clé est la
#    date civile du 86.
#  - Toutes les lignes suivantes — y compris celles qui passent minuit —
#    appartiennent à ce shift jusqu'au prochain ``CODE_DEPART`` (87) inclus,
#    ou jusqu'au prochain 86 (qui implicitement clôt le précédent), ou
#    jusqu'à un trou ≥ 12 h entre deux lignes (forfait pour ne pas étirer
#    indéfiniment un shift en cas d'oubli de 87).
#  - Les lignes orphelines (avant tout 86) retombent sur leur date civile.
#  - La "date" affichée pour un shift est toujours la date du 86 (ou de la
#    première ligne quand le shift est ouvert par défaut).

_SHIFT_GAP_MAX = timedelta(hours=12)


def assign_shift_keys(rows):
    """Annote chaque ligne d'une clé ``_shift_key`` (= date de début du
    shift, ISO ``YYYY-MM-DD``) et renvoie un cache ``{id(row): dt}``.

    Mute en place : ajoute ``_shift_key`` sur chaque ligne.
    """
    dt_cache = {}
    by_op = defaultdict(list)
    for r in rows:
        op = str(r.get("operateur") or "?")
        dt = parse_datetime(r.get("date_operation"))
        dt_cache[id(r)] = dt
        by_op[op].append(r)

    for op, lignes in by_op.items():
        lignes.sort(key=lambda x: dt_cache.get(id(x)) or datetime.min)

        current_key = None         # clé du shift en cours (ISO date) ou None
        last_dt = None             # dt de la ligne précédente
        shift_closed = False       # True après un 87, jusqu'au prochain 86

        for r in lignes:
            dt = dt_cache.get(id(r))
            code = str(r.get("operation_code") or "")

            # Trou > _SHIFT_GAP_MAX => on coupe le shift en cours
            if current_key and dt and last_dt and (dt - last_dt) > _SHIFT_GAP_MAX:
                current_key = None
                shift_closed = False

            if code == CODE_ARRIVEE:
                # Nouveau shift : la clé est la date du 86 (sinon fallback)
                if dt:
                    current_key = dt.date().isoformat()
                else:
                    current_key = (r.get("date_operation") or "")[:10]
                shift_closed = False
            elif shift_closed:
                # Un 87 a déjà fermé le shift précédent : la ligne suivante
                # qui n'est pas un 86 retombe sur sa date civile.
                current_key = None
                shift_closed = False

            if current_key:
                r["_shift_key"] = current_key
            else:
                # Aucun shift ouvert : fallback date civile
                if dt:
                    r["_shift_key"] = dt.date().isoformat()
                else:
                    r["_shift_key"] = (r.get("date_operation") or "")[:10]

            if code == CODE_DEPART and current_key:
                # Le 87 fait partie du shift ; on le ferme APRÈS l'avoir
                # rattaché. Les lignes suivantes (sans nouveau 86) sortiront
                # du shift.
                shift_closed = True

            if dt:
                last_dt = dt

    return dt_cache


# ─── Analyse erreurs de saisie ────────────────────────────────────
def analyse_saisie_errors(rows):
    """
    Détecte les erreurs de saisie structurelles :
    - Absence d'arrivée personnel en début de journée
    - Absence de départ personnel en fin de journée
    - Dossier sans début ou sans fin
    Retourne une liste d'erreurs enrichies.

    Regroupement par "shift opérateur" (86 → 87) plutôt que par date civile,
    pour ne pas casser les équipes de nuit qui traversent minuit.
    """
    errors = []
    dt_cache = assign_shift_keys(rows)

    # Grouper par opérateur + shift_key
    by_op_shift = defaultdict(list)
    for r in rows:
        op = r["operateur"] or "?"
        shift_key = r.get("_shift_key") or ((r.get("date_operation") or "")[:10])
        by_op_shift[(op, shift_key)].append(r)

    for (operateur, jour), lignes in by_op_shift.items():
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
