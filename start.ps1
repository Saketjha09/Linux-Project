# start.ps1 - start the example-voting-app using Docker Compose
# Usage: Open PowerShell, run: .\start.ps1

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Checking Docker daemon..."
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) { throw "docker" }
} catch {
    Write-Error "Docker daemon not available. Please start Docker Desktop (or the Docker Engine) and try again.";
    exit 1
}

Write-Host "Starting services with Docker Compose (detached)..."
docker compose up -d

Write-Host "Showing compose status:"
docker compose ps
Write-Host "Done. Open http://localhost:8080 (vote) and http://localhost:8081 (result)."