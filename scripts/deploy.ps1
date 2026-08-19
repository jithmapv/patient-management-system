$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"
Write-Host " Patient Management System"
Write-Host " Full Stack Deployment"
Write-Host "========================================"
Write-Host ""

# Check Docker installation
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker is not installed."
    exit 1
}

Write-Host "Checking Docker..."

docker info *> $null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker Desktop is not running."
    exit 1
}

# Move to project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

Write-Host "Project root:"
Write-Host $ProjectRoot
Write-Host ""

Write-Host "Stopping previous containers..."

docker compose down --remove-orphans

Write-Host ""
Write-Host "Building and starting services..."

docker compose up --build -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker Compose failed."
    exit 1
}

Write-Host ""
Write-Host "Waiting for backend..."

$BackendReady = $false

for ($i = 1; $i -le 30; $i++) {

    try {

        $response = Invoke-WebRequest `
            -Uri "http://localhost:8000/health" `
            -UseBasicParsing `
            -TimeoutSec 2

        if ($response.StatusCode -eq 200) {
            $BackendReady = $true
            break
        }

    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $BackendReady) {

    Write-Host ""
    Write-Host "Backend did not become ready."
    Write-Host ""
    Write-Host "Showing logs..."

    docker compose logs backend

    exit 1
}

Write-Host ""
Write-Host "Container status:"

docker compose ps

Write-Host ""
Write-Host "========================================"
Write-Host " Application started successfully"
Write-Host "========================================"
Write-Host ""

Write-Host "Frontend : http://localhost:5173"
Write-Host "Backend  : http://localhost:8000"
Write-Host "Swagger  : http://localhost:8000/docs"
Write-Host "Health   : http://localhost:8000/health"

Write-Host ""