#!/usr/bin/env bash
# Import planning Cohésio 1/2 depuis un CSV (grille Google Sheet exportée).
# Usage sur le serveur (root ou sifa) :
#   ./tools/server_run_planning_import.sh /chemin/vers/fichier.csv
#
# Défaut CSV si argument omis : /home/sifa/production-saas/data/planning_cohesio_import.csv
set -euo pipefail

APP_DIR="${MYSIFA_APP_DIR:-/home/sifa/production-saas}"
CSV_PATH="${1:-$APP_DIR/data/planning_cohesio_import.csv}"
PY="$APP_DIR/venv/bin/python"
IMPORTER="$APP_DIR/tools/import_planning_cohesio_csv.py"

if [[ ! -f "$IMPORTER" ]]; then
  echo "Erreur: importer introuvable: $IMPORTER (git pull ?)" >&2
  exit 1
fi
if [[ ! -f "$CSV_PATH" ]]; then
  echo "Erreur: CSV introuvable: $CSV_PATH" >&2
  echo "Placez le fichier puis relancez, ou: $0 /chemin/vers/votre.csv" >&2
  exit 1
fi
if [[ ! -x "$PY" ]] && ! command -v "$PY" >/dev/null 2>&1; then
  echo "Erreur: Python venv introuvable: $PY" >&2
  exit 1
fi

run_import() {
  cd "$APP_DIR"
  "$PY" "$IMPORTER" "$CSV_PATH"
}

if [[ "$(id -u)" -eq 0 ]] && id sifa >/dev/null 2>&1; then
  # Exécuter en tant que sifa (même UID que l’app / production.db)
  sudo -u sifa bash -c "cd $(printf '%q' "$APP_DIR") && $(printf '%q' "$PY") $(printf '%q' "$IMPORTER") $(printf '%q' "$CSV_PATH")"
else
  run_import
fi

if [[ "$(id -u)" -eq 0 ]] && [[ -f "$APP_DIR/data/production.db" ]]; then
  chown sifa:sifa "$APP_DIR/data/production.db" 2>/dev/null || true
fi

echo "Import terminé. Redémarrage du service (optionnel mais recommandé si locks SQLite)…"
if command -v systemctl >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
  systemctl restart mysifa
  systemctl --no-pager -l status mysifa || true
else
  echo "Relancez le service avec: sudo systemctl restart mysifa"
fi
