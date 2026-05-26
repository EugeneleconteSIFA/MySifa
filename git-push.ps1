# Push GitHub uniquement (sync Google Drive -> miroir git + git push)
# Usage :
#   .\git-push.ps1
#   .\git-push.ps1 -SkipSync
#   .\git-push.ps1 -m "Mon message de commit"

param(
    [switch]$SkipSync,
    [Alias("m")]
    [string]$Message
)

$deployPs1 = Join-Path $PSScriptRoot "deploy.ps1"
if (-not (Test-Path $deployPs1)) {
    throw "deploy.ps1 introuvable : $deployPs1"
}

& $deployPs1 -GitHubOnly -SkipSync:$SkipSync -m $Message @args
