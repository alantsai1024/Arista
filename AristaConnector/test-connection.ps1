# Test SSH Connection to Remote Server

$RemoteHost = "123.192.126.214"
$Port = 33333
$User = "ubuntu"

Write-Host "Testing SSH connection to ${User}@${RemoteHost}:${Port}..." -ForegroundColor Cyan
Write-Host ""

# Test basic connection
try {
    $result = ssh -p $Port -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${User}@${RemoteHost}" "echo 'Connection successful'; uname -a" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ SSH Connection: SUCCESS" -ForegroundColor Green
        Write-Host $result -ForegroundColor White
        Write-Host ""
        
        # Check Docker
        Write-Host "Checking Docker..." -ForegroundColor Yellow
        $dockerCheck = ssh -p $Port "${User}@${RemoteHost}" "command -v docker && docker --version" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Docker: INSTALLED" -ForegroundColor Green
            Write-Host $dockerCheck -ForegroundColor White
            
            # Check Docker Compose
            $composeCheck = ssh -p $Port "${User}@${RemoteHost}" "docker compose version 2>&1 || docker-compose version 2>&1" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Docker Compose: AVAILABLE" -ForegroundColor Green
                Write-Host $composeCheck -ForegroundColor White
            } else {
                Write-Host "✗ Docker Compose: NOT FOUND" -ForegroundColor Red
            }
        } else {
            Write-Host "✗ Docker: NOT INSTALLED" -ForegroundColor Red
            Write-Host "  Install with: sudo apt-get install -y docker.io docker-compose" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "✓ Ready to deploy!" -ForegroundColor Green
        Write-Host "  Run: .\deploy.ps1" -ForegroundColor Cyan
    } else {
        throw "Connection failed"
    }
} catch {
    Write-Host "✗ SSH Connection: FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "  1. SSH key not configured" -ForegroundColor White
    Write-Host "  2. Firewall blocking port $Port" -ForegroundColor White
    Write-Host "  3. Server not accessible" -ForegroundColor White
    Write-Host ""
    Write-Host "Try manually:" -ForegroundColor Yellow
    Write-Host "  ssh -p $Port ${User}@${RemoteHost}" -ForegroundColor White
}

Write-Host ""
