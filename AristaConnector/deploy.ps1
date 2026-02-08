# Arista vEOS Connector - Windows Deployment Script

param(
    [string]$RemoteHost = "123.192.126.214",
    [int]$Port = 33333,
    [string]$User = "ubuntu",
    [string]$RemoteDir = "~/aristacollector"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Arista vEOS Connector - Remote Deployment ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: ${User}@${RemoteHost}:${Port}" -ForegroundColor White
Write-Host "Remote Directory: ${RemoteDir}" -ForegroundColor White
Write-Host ""

# Check if SSH is available (Windows 10+ has OpenSSH)
$sshAvailable = $false
if (Get-Command ssh -ErrorAction SilentlyContinue) {
    $sshAvailable = $true
    Write-Host "[1/6] SSH client found" -ForegroundColor Green
} else {
    Write-Host "[1/6] SSH client not found" -ForegroundColor Red
    Write-Host "  Please install OpenSSH or use WSL/Git Bash" -ForegroundColor Yellow
    Write-Host "  Or use deploy.sh in WSL/Git Bash" -ForegroundColor Yellow
    exit 1
}

# Test SSH connection
Write-Host ""
Write-Host "[2/6] Testing SSH connection..." -ForegroundColor Yellow
try {
    $testResult = ssh -p $Port -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${User}@${RemoteHost}" "echo 'Connection successful'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: SSH connection successful" -ForegroundColor Green
    } else {
        throw "Connection failed"
    }
} catch {
    Write-Host "  ERROR: Failed to connect to ${User}@${RemoteHost}" -ForegroundColor Red
    Write-Host "  Please check:" -ForegroundColor Yellow
    Write-Host "    - SSH key is configured" -ForegroundColor Yellow
    Write-Host "    - Host is reachable" -ForegroundColor Yellow
    Write-Host "    - Port ${Port} is open" -ForegroundColor Yellow
    exit 1
}

# Check Docker on remote
Write-Host ""
Write-Host "[3/6] Checking Docker on remote host..." -ForegroundColor Yellow
$dockerCheck = ssh -p $Port "${User}@${RemoteHost}" "command -v docker" 2>&1
if ($LASTEXITCODE -eq 0) {
    $dockerVersion = ssh -p $Port "${User}@${RemoteHost}" "docker --version" 2>&1
    Write-Host "  OK: Docker found - $dockerVersion" -ForegroundColor Green
    
    # Check Docker Compose
    $composeCheck = ssh -p $Port "${User}@${RemoteHost}" "docker compose version" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $composeCmd = "docker compose"
        Write-Host "  OK: Docker Compose (new) available" -ForegroundColor Green
    } else {
        $composeCheck = ssh -p $Port "${User}@${RemoteHost}" "docker-compose version" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $composeCmd = "docker-compose"
            Write-Host "  OK: Docker Compose (old) available" -ForegroundColor Green
        } else {
            Write-Host "  ERROR: Docker Compose not found" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "  ERROR: Docker not found on remote host" -ForegroundColor Red
    Write-Host "  Please install Docker on the remote host first" -ForegroundColor Yellow
    exit 1
}

# Create remote directory
Write-Host ""
Write-Host "[4/6] Setting up remote directory..." -ForegroundColor Yellow
ssh -p $Port "${User}@${RemoteHost}" "mkdir -p ${RemoteDir}" | Out-Null
Write-Host "  OK: Remote directory created" -ForegroundColor Green

# Copy files using scp/rsync
Write-Host ""
Write-Host "[5/6] Copying files to remote host..." -ForegroundColor Yellow
Write-Host "  Note: Using SCP (for rsync, use WSL/Git Bash with deploy.sh)" -ForegroundColor Cyan

# Create a temporary tar archive and copy it
$tempTar = "deploy_temp.tar.gz"
Write-Host "  Creating archive..." -ForegroundColor Cyan

# Use tar if available (Windows 10+)
if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar -czf $tempTar --exclude='.git' --exclude='node_modules' --exclude='__pycache__' --exclude='.next' --exclude='.env' --exclude='*.pyc' --exclude='.DS_Store' .
    scp -P $Port $tempTar "${User}@${RemoteHost}:${RemoteDir}/"
    ssh -p $Port "${User}@${RemoteHost}" "cd ${RemoteDir} && tar -xzf $tempTar && rm $tempTar"
    Remove-Item $tempTar
    Write-Host "  OK: Files copied" -ForegroundColor Green
} else {
    Write-Host "  WARNING: tar not available. Please copy files manually or use WSL/Git Bash" -ForegroundColor Yellow
    Write-Host "  Manual steps:" -ForegroundColor Yellow
    Write-Host "    1. Use WinSCP, FileZilla, or similar tool" -ForegroundColor White
    Write-Host "    2. Or use WSL/Git Bash: ./deploy.sh" -ForegroundColor White
    exit 1
}

# Setup environment
Write-Host ""
Write-Host "[6/6] Setting up environment and deploying..." -ForegroundColor Yellow
ssh -p $Port "${User}@${RemoteHost}" @"
cd ${RemoteDir}
if [ ! -f .env ]; then
    cp .env.example .env
    echo 'Created .env from .env.example'
    echo 'Please edit .env with production settings'
fi
echo 'Building Docker images...'
${composeCmd} build
echo 'Stopping existing services...'
${composeCmd} down
echo 'Starting services...'
${composeCmd} up -d
sleep 10
${composeCmd} ps
"@

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Services are running on:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://${RemoteHost}:3000" -ForegroundColor White
Write-Host "  Backend:   http://${RemoteHost}:8000" -ForegroundColor White
Write-Host "  API Docs:  http://${RemoteHost}:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "To check logs:" -ForegroundColor Yellow
Write-Host "  ssh -p ${Port} ${User}@${RemoteHost} 'cd ${RemoteDir} && ${composeCmd} logs -f'" -ForegroundColor White
Write-Host ""
Write-Host "To stop services:" -ForegroundColor Yellow
Write-Host "  ssh -p ${Port} ${User}@${RemoteHost} 'cd ${RemoteDir} && ${composeCmd} down'" -ForegroundColor White
Write-Host ""
