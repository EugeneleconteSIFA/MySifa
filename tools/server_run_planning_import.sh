#!/usr/bin/env bash
# Import planning Cohésio 1/2 depuis un CSV (grille Google Sheet exportée).
# Usage sur le serveur (root ou sifa) :
#   ./tools/server_run_planning_import.sh /chemin/vers/fichier.csv
#
# Détection automatique : même répertoire code que systemd (WorkingDirectory), ou …/app
# si présent — pour utiliser la *même* production.db que l’UI (ex. …/app/data/production.db).
set -euo pipefail

GIT_ROOT="${MYSIFA_APP_DIR:-/home/sifa/production-saas}"
IMPORTER="$GIT_ROOT/tools/import_planning_cohesio_csv.py"
PY="$GIT_ROOT/venv/bin/python"

resolve_code_root() {
  if [[ -n "${MYSIFA_CODE_ROOT:-}" ]] && [[ -f "${MYSIFA_CODE_ROOT}/config.py" ]]; then
    export MYSIFA_CODE_ROOT
    echo "MYSIFA_CODE_ROOT (déjà défini): $MYSIFA_CODE_ROOT"
    return
  fi
  if command -v systemctl >/dev/null 2>&1; then
    local wd
    wd=$(systemctl show mysifa.service -p WorkingDirectory --value 2>/dev/null | tr -d '\n' || true)
    if [[ -n "$wd" && "$wd" != "-" && -f "$wd/config.py" ]]; then
      export MYSIFA_CODE_ROOT="$wd"
      echo "MYSIFA_CODE_ROOT (WorkingDirectory systemd mysifa): $MYSIFA_CODE_ROOT"
      return
    fi
  fi
  if [[ -f "$GIT_ROOT/app/config.py" ]]; then
    export MYSIFA_CODE_ROOT="$GIT_ROOT/app"
    echo "MYSIFA_CODE_ROOT (sous-dossier app/): $MYSIFA_CODE_ROOT"
    return
  fi
  export MYSIFA_CODE_ROOT="$GIT_ROOT"
  echo "MYSIFA_CODE_ROOT (racine GIT_ROOT): $MYSIFA_CODE_ROOT"
}

# DB_PATH : uniquement si défini dans systemd ; sinon laisser config.py sous MYSIFA_CODE_ROOT choisir data/production.db
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
          echo "DB_PATH (systemd Environment): $DB_PATH"
          return
        fi
      done
    fi
  fi
  unset DB_PATH 2>/dev/null || true
  echo "DB_PATH: (non forcé — défaut = \$MYSIFA_CODE_ROOT/data/production.db via config.py)"
}

if [[ ! -f "$IMPORTER" ]]; then
  echo "Erreur: importer introuvable: $IMPORTER (git pull ?)" >&2
  exit 1
fi
if [[ ! -x "$PY" ]] && ! command -v "$PY" >/dev/null 2>&1; then
  echo "Erreur: Python venv introuvable: $PY" >&2
  exit 1
fi

resolve_code_root
resolve_db_path

CSV_PATH="${1:-}"
if [[ -z "${CSV_PATH:-}" ]]; then
  if [[ -f "$MYSIFA_CODE_ROOT/data/planning_cohesio_import.csv" ]]; then
    CSV_PATH="$MYSIFA_CODE_ROOT/data/planning_cohesio_import.csv"
  elif [[ -f "$GIT_ROOT/data/planning_cohesio_import.csv" ]]; then
    CSV_PATH="$GIT_ROOT/data/planning_cohesio_import.csv"
  else
    echo "Erreur: CSV introuvable. Placez planning_cohesio_import.csv dans data/ ou passez le chemin en argument." >&2
    exit 1
  fi
fi
if [[ ! -f "$CSV_PATH" ]]; then
  echo "Erreur: CSV introuvable: $CSV_PATH" >&2
  exit 1
fi

if [[ "$(id -u)" -eq 0 ]] && id sifa >/dev/null 2>&1; then
  if [[ -n "${DB_PATH:-}" ]]; then
    sudo -u sifa env \
      "MYSIFA_CODE_ROOT=$MYSIFA_CODE_ROOT" \
      "DB_PATH=$DB_PATH" \
      bash -c "cd $(printf '%q' "$MYSIFA_CODE_ROOT") && $(printf '%q' "$PY") $(printf '%q' "$IMPORTER") $(printf '%q' "$CSV_PATH")"
  else
    sudo -u sifa env \
      "MYSIFA_CODE_ROOT=$MYSIFA_CODE_ROOT" \
      bash -c "cd $(printf '%q' "$MYSIFA_CODE_ROOT") && $(printf '%q' "$PY") $(printf '%q' "$IMPORTER") $(printf '%q' "$CSV_PATH")"
  fi
else
  export MYSIFA_CODE_ROOT
  [[ -n "${DB_PATH:-}" ]] && export DB_PATH || unset DB_PATH
  cd "$MYSIFA_CODE_ROOT"
  "$PY" "$IMPORTER" "$CSV_PATH"
fi

if [[ "$(id -u)" -eq 0 ]]; then
  for db in "$MYSIFA_CODE_ROOT/data/production.db" "$GIT_ROOT/data/production.db" "$GIT_ROOT/production.db"; do
    [[ -f "$db" ]] && chown sifa:sifa "$db" 2>/dev/null || true
  done
fi

echo "Import terminé. Redémarrage du service…"
if command -v systemctl >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
  systemctl restart mysifa
  systemctl --no-pager -l status mysifa || true
else
  echo "Relancez: sudo systemctl restart mysifa"
fi
