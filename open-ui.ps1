<#
open-ui.ps1 - Open the Voting and Results UIs in the default browser.

Usage:
  # Just open (assumes services already running)
  .\open-ui.ps1

  # If services are not running, start them first (runs start.ps1)
  .\open-ui.ps1 -StartIfNeeded

Options:
  -StartIfNeeded  : Start the compose stack if endpoints are not reachable.
  -TimeoutSeconds : How many seconds to wait for services to become healthy (default 60).
#>

param(
    [switch]$StartIfNeeded,
    [int]$TimeoutSeconds = 60
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$voteUrl = 'http://localhost:8080'
$resultUrl = 'http://localhost:8081'

function Test-Endpoint {
    param([string]$url)
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -Method Head -TimeoutSec 5 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Wait-For-Endpoints {
    param([string[]]$urls, [int]$timeoutSeconds)
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $allUp = $true
        foreach ($u in $urls) {
            if (-not (Test-Endpoint $u)) { $allUp = $false; break }
        }
        if ($allUp) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host "Checking endpoints: $voteUrl and $resultUrl" -ForegroundColor Cyan
$voteUp = Test-Endpoint $voteUrl
$resultUp = Test-Endpoint $resultUrl

if ($voteUp -and $resultUp) {
    Write-Host "Both endpoints are already responding. Opening browser..." -ForegroundColor Green
} else {
    Write-Warning "One or both endpoints are not responding." 
    if ($StartIfNeeded) {
        Write-Host "Attempting to start compose stack (start.ps1)..." -ForegroundColor Yellow
        if (Test-Path "$RepoRoot\start.ps1") {
            powershell -NoProfile -ExecutionPolicy Bypass -File "$RepoRoot\start.ps1"
        } else {
            Write-Warning "start.ps1 not found in repo root. Running 'docker compose up -d' directly."
            docker compose up -d
        }

        Write-Host "Waiting up to $TimeoutSeconds seconds for endpoints to become healthy..." -ForegroundColor Yellow
        $ok = Wait-For-Endpoints -urls @($voteUrl,$resultUrl) -timeoutSeconds $TimeoutSeconds
        if (-not $ok) {
            Write-Warning "Services did not become healthy in time. You can check logs: docker compose logs -f"
        } else {
            Write-Host "Services are responding." -ForegroundColor Green
        }
    } else {
        Write-Host "Run with -StartIfNeeded to start the stack automatically, or start it yourself and re-run this script." -ForegroundColor Yellow
        if (-not $voteUp) { Write-Host "Vote UI not reachable: $voteUrl" }
        if (-not $resultUp) { Write-Host "Result UI not reachable: $resultUrl" }
        exit 1
    }
}

# Open both URLs in the default browser
try {
    Start-Process $voteUrl
    Start-Process $resultUrl
    Write-Host "Opened $voteUrl and $resultUrl in the default browser." -ForegroundColor Green
} catch {
    Write-Warning "Failed to open browser via Start-Process. You can open the URLs manually: $voteUrl and $resultUrl"
}
