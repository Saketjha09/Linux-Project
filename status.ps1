# status.ps1 - quick smoke checks for the example voting app
# Usage: .\status.ps1

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Docker Compose status:" -ForegroundColor Cyan
docker compose ps

function Get-HttpHeaders($url) {
    Write-Host "\nChecking $url" -ForegroundColor Yellow
    try {
        # try curl.exe first (works if curl is on PATH)
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($curl) {
            curl.exe -sS -I $url
        } else {
            # fallback to PowerShell's Invoke-WebRequest
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop
            $resp.Headers
        }
    } catch {
        Write-Warning "Request to $url failed: $($_.Exception.Message)"
    }
}

Get-HttpHeaders "http://localhost:8080/health"
Get-HttpHeaders "http://localhost:8080/ready"
Get-HttpHeaders "http://localhost:8081/health"
Get-HttpHeaders "http://localhost:8081/ready"

Write-Host "\nTo tail logs: docker compose logs -f [service] (example: docker compose logs -f worker)" -ForegroundColor Green
