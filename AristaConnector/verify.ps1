# Verification Script for Arista vEOS Connector

Write-Host "=== Arista vEOS Connector - Project Verification ===" -ForegroundColor Cyan
Write-Host ""

$errors = 0
$warnings = 0

# Check Docker
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
$dockerAvailable = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerVersion = docker --version 2>&1
    Write-Host "  OK: Docker found - $dockerVersion" -ForegroundColor Green
    $dockerAvailable = $true
    
    # Check Docker Compose
    $null = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: Docker Compose (new) available" -ForegroundColor Green
    } else {
        $null = docker-compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK: Docker Compose (old) available" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Docker Compose not found" -ForegroundColor Yellow
            $warnings++
        }
    }
} else {
    Write-Host "  ERROR: Docker not found in PATH" -ForegroundColor Red
    Write-Host "    Please install Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    $errors++
}

# Check project structure
Write-Host ""
Write-Host "[2/6] Checking project structure..." -ForegroundColor Yellow
$requiredDirs = @("backend", "frontend", "mqtt")
$requiredFiles = @(
    "docker-compose.yml",
    "Makefile",
    ".env.example",
    "README.md",
    "backend/main.py",
    "backend/collector.py",
    "backend/requirements.txt",
    "backend/Dockerfile",
    "frontend/package.json",
    "frontend/Dockerfile",
    "mqtt/mosquitto.conf"
)

foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Host "  OK: Directory '$dir' exists" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Directory '$dir' missing" -ForegroundColor Red
        $errors++
    }
}

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  OK: File '$file' exists" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: File '$file' missing" -ForegroundColor Red
        $errors++
    }
}

# Check .env file
Write-Host ""
Write-Host "[3/6] Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path .env) {
    Write-Host "  OK: .env file exists" -ForegroundColor Green
} else {
    if (Test-Path .env.example) {
        Write-Host "  INFO: .env not found, will be created from .env.example on startup" -ForegroundColor Cyan
    } else {
        Write-Host "  ERROR: .env.example missing" -ForegroundColor Red
        $errors++
    }
}

# Check backend Python files
Write-Host ""
Write-Host "[4/6] Checking backend code..." -ForegroundColor Yellow
$backendFiles = @(
    "backend/app/models.py",
    "backend/app/schemas.py",
    "backend/app/database.py",
    "backend/app/routers/devices.py",
    "backend/app/routers/health.py",
    "backend/app/services/redis_client.py",
    "backend/app/services/mqtt_client.py"
)

foreach ($file in $backendFiles) {
    if (Test-Path $file) {
        Write-Host "  OK: $file" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: $file missing" -ForegroundColor Red
        $errors++
    }
}

# Check frontend files
Write-Host ""
Write-Host "[5/6] Checking frontend code..." -ForegroundColor Yellow
$frontendFiles = @(
    "frontend/app/page.tsx",
    "frontend/app/layout.tsx",
    "frontend/app/components/DeviceList.tsx",
    "frontend/app/components/FleetHealth.tsx"
)

foreach ($file in $frontendFiles) {
    if (Test-Path $file) {
        Write-Host "  OK: $file" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: $file missing" -ForegroundColor Red
        $errors++
    }
}

# Check Python (for local development)
Write-Host ""
Write-Host "[6/6] Checking Python (optional, for local dev)..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK: Python found - $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  INFO: Python not found (optional, only needed for local dev)" -ForegroundColor Cyan
}

# Summary
Write-Host ""
Write-Host "=== Verification Summary ===" -ForegroundColor Cyan
if ($errors -eq 0) {
    Write-Host "Status: READY TO START" -ForegroundColor Green
    if ($warnings -gt 0) {
        Write-Host "Warnings: $warnings (non-critical)" -ForegroundColor Yellow
    }
    Write-Host ""
    if ($dockerAvailable) {
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Ensure Docker Desktop is running" -ForegroundColor White
        Write-Host "  2. Run: .\start.ps1" -ForegroundColor White
        Write-Host "     Or: docker compose up -d" -ForegroundColor White
    } else {
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Install Docker Desktop" -ForegroundColor White
        Write-Host "  2. Start Docker Desktop" -ForegroundColor White
        Write-Host "  3. Run: .\start.ps1" -ForegroundColor White
    }
} else {
    Write-Host "Status: ERRORS FOUND ($errors errors)" -ForegroundColor Red
    Write-Host "Please fix the errors above before starting services." -ForegroundColor Yellow
}

Write-Host ""
