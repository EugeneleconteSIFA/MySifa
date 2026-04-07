# Envoie le CSV sur le VPS et lance l’import planning (Cohésio 1 & 2).
# Usage (PowerShell, depuis la racine du repo) :
#   .\tools\deploy_planning_csv_to_server.ps1
#   .\tools\deploy_planning_csv_to_server.ps1 -CsvPath "D:\fichier.csv"
param(
    [string]$Server = "root@168.231.85.64",
    [string]$CsvPath = "$env:USERPROFILE\Downloads\Untitled spreadsheet - Sheet2.csv",
    # VPS avec code sous app/ : même répertoire que db_path …/app/data/production.db
    [string]$RemoteCsv = "/home/sifa/production-saas/app/data/planning_cohesio_import.csv"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $CsvPath)) {
    Write-Error "CSV introuvable: $CsvPath"
}

Write-Host "SCP -> ${Server}:${RemoteCsv}"
scp $CsvPath "${Server}:${RemoteCsv}"

$pullAndImport = "set -euo pipefail; cd /home/sifa/production-saas; git pull origin main; chown -R sifa:sifa /home/sifa/production-saas; chmod +x tools/server_run_planning_import.sh || true; bash tools/server_run_planning_import.sh `"$RemoteCsv`""
Write-Host "SSH: git pull + import + restart mysifa"
ssh $Server $pullAndImport

Write-Host "Terminé."
