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

# Même base que le service mysifa. Par défaut, config.py utilise data/production.db
# (pas la racine). Privilégier data/ évite d’importer dans un second fichier SQLite
# que l’UI ne lit pas.
resolve_db_path() {
  if [[ -n "${DB_PATH:-}" ]]; then
    echo "DB_PATH (déjà défini): $DB_PATH"
    return
  fi
  if command -v systemctl >/dev/null 2>&1; then
    local env_val tok
    env_val=$(systemctl show mysifa.service -p Environment --value 2>/dev/null || true)
    if [[ -n "$env_val" ]]; then
      for tok in $env_val; do
        if [[ "$tok" == DB_PATH=* ]]; then
          export DB_PATH="${tok#DB_PATH=}"
          echo "DB_PATH (extrait de systemd mysifa): $DB_PATH"
          return
        fi
      done
    fi
  fi
  if [[ -f "$APP_DIR/data/production.db" ]]; then
    export DB_PATH="$APP_DIR/data/production.db"
    echo "DB_PATH (défaut MySifa — data/production.db): $DB_PATH"
    return
  fi
  if [[ -f "$APP_DIR/production.db" ]]; then
    export DB_PATH="$APP_DIR/production.db"
    echo "DB_PATH (legacy — production.db à la racine, data/ absent): $DB_PATH"
    return
  fi
  export DB_PATH="$APP_DIR/data/production.db"
  echo "DB_PATH (standard — data/production.db, sera créé si besoin): $DB_PATH"
}

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

resolve_db_path

run_import() {
  cd "$APP_DIR"
  if [[ -n "${DB_PATH:-}" ]]; then
    export DB_PATH
  fi
  "$PY" "$IMPORTER" "$CSV_PATH"
}

if [[ "$(id -u)" -eq 0 ]] && id sifa >/dev/null 2>&1; then
  # Exécuter en tant que sifa ; transmettre DB_PATH explicitement (sudo n’hérite pas toujours des exports)
  if [[ -n "${DB_PATH:-}" ]]; then
    sudo -u sifa env "DB_PATH=$DB_PATH" bash -c "cd $(printf '%q' "$APP_DIR") && $(printf '%q' "$PY") $(printf '%q' "$IMPORTER") $(printf '%q' "$CSV_PATH")"
  else
    sudo -u sifa bash -c "cd $(printf '%q' "$APP_DIR") && $(printf '%q' "$PY") $(printf '%q' "$IMPORTER") $(printf '%q' "$CSV_PATH")"
  fi
else
  run_import
fi

if [[ "$(id -u)" -eq 0 ]]; then
  for db in "$APP_DIR/production.db" "$APP_DIR/data/production.db"; do
    [[ -f "$db" ]] && chown sifa:sifa "$db" 2>/dev/null || true
  done
fi

echo "Import terminé. Redémarrage du service (optionnel mais recommandé si locks SQLite)…"
if command -v systemctl >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
  systemctl restart mysifa
  systemctl --no-pager -l status mysifa || true
else
  echo "Relancez le service avec: sudo systemctl restart mysifa"
fi
