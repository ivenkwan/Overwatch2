param (
    [switch]$Start,
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"

# Ensure we are in the correct directory (where docker-compose.yml lives)
$scriptPath = $MyInvocation.MyCommand.Path
$composeDir = Split-Path $scriptPath
Set-Location $composeDir

Function Teardown-And-Rebuild {
    Write-Host "`n[!] Tearing down services and deleting volumes (Clean Slate)..." -ForegroundColor Yellow
    docker-compose down -v
    Write-Host "[!] Rebuilding and starting services from original init..." -ForegroundColor Yellow
    docker-compose up -d --build
}

Function Wait-For-Http {
    param([string]$Url, [string]$ServiceName, [int]$TimeoutSeconds = 60)
    
    Write-Host "Waiting for $ServiceName at $Url to become available..." -NoNewline
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 401 -or $response.StatusCode -eq 403 -or $response.StatusCode -eq 404) {
                # Considering 401/403/404 as responses which mean the server is technically up and responding.
                Write-Host " [OK] ($($response.StatusCode))" -ForegroundColor Green
                return $true
            }
        } catch {
            # Ignored, wait and retry
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 3
    }
    Write-Host " [FAILED] (Timeout)" -ForegroundColor Red
    return $false
}

Function Check-Services {
    Write-Host "`nDatabase is managed within platform's docker-compose.yml..." -ForegroundColor Green

    # Check Backend
    # Fast API default docs are at /docs, or root / might return 404 but server is up. 
    $backendUp = Wait-For-Http -Url "http://localhost:8000/docs" -ServiceName "Backend API" -TimeoutSeconds 60
    if (-not $backendUp) {
        return $false
    }

    # Check Frontend
    $frontendUp = Wait-For-Http -Url "http://localhost:3000/" -ServiceName "Frontend Node" -TimeoutSeconds 60
    if (-not $frontendUp) {
        return $false
    }

    return $true
}

# --- Main Logic ---

if ($Stop) {
    Write-Host "Stopping AML Platform Services..." -ForegroundColor Cyan
    docker-compose stop
    exit 0
}

if (-not $Start -and -not $Restart -and -not $Rebuild) {
    Write-Host "Usage: .\manage_aml_services.ps1 [-Start | -Stop | -Restart | -Rebuild]"
    Write-Host "Example: .\manage_aml_services.ps1 -Start"
    exit 1
}

if ($Rebuild) {
    Write-Host "Rebuilding AML Platform Services..." -ForegroundColor Cyan
    docker-compose down
    docker-compose up -d --build
} elseif ($Restart) {
    Write-Host "Restarting AML Platform Services..." -ForegroundColor Cyan
    docker-compose down
    docker-compose up -d
} else {
    Write-Host "Starting AML Platform Services (Normal Startup)..." -ForegroundColor Cyan
    docker-compose up -d
}
# Initialize Keycloak database in the ETL container if it isn't already created
Write-Host "`nEnsuring Keycloak internal database exists..." -ForegroundColor Cyan
try {
    .\init_keycloak.ps1
} catch {
    Write-Host "[WARNING] Failed to run init_keycloak.ps1." -ForegroundColor Yellow
}

# Check if everything came up properly
$allHealthy = Check-Services

if (-not $allHealthy) {
    Write-Host "`n>>> Failure detected. Initiating clean rebuild from original init... <<<" -ForegroundColor Red
    Teardown-And-Rebuild
    
    Write-Host "`nRe-checking services after clean rebuild..." -ForegroundColor Cyan
    $secondTryHealthy = Check-Services
    
    if (-not $secondTryHealthy) {
        Write-Host "`n[ERROR] Services are still unavailable after a complete rebuild. Please check docker logs manually." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n>>> All AML Platform services are running and available! <<<" -ForegroundColor Green
exit 0
