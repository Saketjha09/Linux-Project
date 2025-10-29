# stop.ps1 - stop and remove the example-voting-app compose stack
# Usage: .\stop.ps1

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Stopping and removing compose stack (including volumes)..."
docker compose down --volumes --remove-orphans

Write-Host "Done."