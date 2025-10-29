# seed.ps1 - run the seed profile to populate votes
# Usage: .\seed.ps1

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Running seed job (this runs and then exits)..."
# Run in foreground so user sees output; it will exit when complete
docker compose --profile seed up --remove-orphans

Write-Host "Seed job finished."