# Arista vEOS Connector - Startup Script

Write-Host "Arista vEOS Connector - Starting Services" -ForegroundColor Green
Write-Host ""

# Check if Docker is available
$dockerCmd = $null
if (Get-Command docker -ErrorAction SilentlyContinue) {
    # Check for docker compose (new version)
    $composeTest = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerCmd = "docker compose"
        Write-Host "Detected Docker Compose (new version)" -ForegroundColor Green
    } else {
        # Check for docker-compose (old version)
        $composeTest = docker-compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerCmd = "docker-compose"
            Write-Host "Detected Docker Compose (old version)" -ForegroundColor Green
        }
    }
}

if (-not $dockerCmd) {
    Write-Host "Error: Docker or Docker Compose not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Docker Desktop first:" -ForegroundColor Yellow
    Write-Host "  https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After installation, ensure Docker Desktop is running and rerun this script." -ForegroundColor Yellow
    exit 1
}

# Check .env file
if (-not (Test-Path .env)) {
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "Created .env file from .env.example" -ForegroundColor Green
    } else {
        Write-Host "Warning: .env file not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""

# Start services
Invoke-Expression "$dockerCmd up -d"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URLs:" -ForegroundColor Cyan
    Write-Host "  Frontend Dashboard: http://localhost:3000" -ForegroundColor White
    Write-Host "  Backend API:        http://localhost:8000" -ForegroundColor White
    Write-Host "  API Docs:           http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "View logs: $dockerCmd logs -f" -ForegroundColor Yellow
    Write-Host "Stop services: $dockerCmd down" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Failed to start services. Check error messages above." -ForegroundColor Red
    Write-Host "View logs: $dockerCmd logs" -ForegroundColor Yellow
    exit 1
}
