#!/bin/bash
# Arista vEOS Connector - Deployment Script

set -e

# Configuration
REMOTE_HOST="123.192.126.214"
REMOTE_PORT="33333"
REMOTE_USER="ubuntu"
REMOTE_DIR="~/aristacollector"
DEPLOY_USER="${REMOTE_USER}@${REMOTE_HOST}"

echo "=== Arista vEOS Connector - Remote Deployment ==="
echo ""
echo "Target: ${DEPLOY_USER}:${REMOTE_PORT}"
echo "Remote Directory: ${REMOTE_DIR}"
echo ""

# Check if SSH key is available
if [ -z "$SSH_AUTH_SOCK" ] && [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Warning: No SSH key found. You may need to enter password multiple times."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Test SSH connection
echo "[1/6] Testing SSH connection..."
if ssh -p ${REMOTE_PORT} -o ConnectTimeout=10 ${DEPLOY_USER} "echo 'Connection successful'" 2>/dev/null; then
    echo "  ✓ SSH connection successful"
else
    echo "  ✗ Failed to connect to ${DEPLOY_USER}"
    echo "  Please check:"
    echo "    - SSH key is added: ssh-add ~/.ssh/your_key"
    echo "    - Host is reachable: ping ${REMOTE_HOST}"
    echo "    - Port ${REMOTE_PORT} is open"
    exit 1
fi

# Check Docker on remote host
echo ""
echo "[2/6] Checking Docker on remote host..."
if ssh -p ${REMOTE_PORT} ${DEPLOY_USER} "command -v docker >/dev/null 2>&1"; then
    DOCKER_VERSION=$(ssh -p ${REMOTE_PORT} ${DEPLOY_USER} "docker --version")
    echo "  ✓ Docker found: ${DOCKER_VERSION}"
    
    # Check Docker Compose
    if ssh -p ${REMOTE_PORT} ${DEPLOY_USER} "docker compose version >/dev/null 2>&1"; then
        echo "  ✓ Docker Compose (new) available"
        COMPOSE_CMD="docker compose"
    elif ssh -p ${REMOTE_PORT} ${DEPLOY_USER} "docker-compose version >/dev/null 2>&1"; then
        echo "  ✓ Docker Compose (old) available"
        COMPOSE_CMD="docker-compose"
    else
        echo "  ✗ Docker Compose not found"
        exit 1
    fi
else
    echo "  ✗ Docker not found on remote host"
    echo "  Installing Docker..."
    ssh -p ${REMOTE_PORT} ${DEPLOY_USER} << 'ENDSSH'
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose
        sudo usermod -aG docker $USER
        echo "Docker installed. You may need to log out and back in."
ENDSSH
    exit 1
fi

# Create remote directory
echo ""
echo "[3/6] Setting up remote directory..."
ssh -p ${REMOTE_PORT} ${DEPLOY_USER} "mkdir -p ${REMOTE_DIR}"
echo "  ✓ Remote directory created"

# Copy files to remote host
echo ""
echo "[4/6] Copying files to remote host..."
rsync -avz -e "ssh -p ${REMOTE_PORT}" \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '.next' \
    --exclude '.env' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    ./ ${DEPLOY_USER}:${REMOTE_DIR}/

echo "  ✓ Files copied"

# Create .env file on remote if it doesn't exist
echo ""
echo "[5/6] Setting up environment..."
ssh -p ${REMOTE_PORT} ${DEPLOY_USER} << ENDSSH
    cd ${REMOTE_DIR}
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "  ✓ Created .env from .env.example"
        echo "  ⚠ Please edit .env file with production settings:"
        echo "    ssh -p ${REMOTE_PORT} ${DEPLOY_USER}"
        echo "    cd ${REMOTE_DIR}"
        echo "    nano .env"
    else
        echo "  ✓ .env file already exists"
    fi
ENDSSH

# Deploy services
echo ""
echo "[6/6] Deploying services..."
ssh -p ${REMOTE_PORT} ${DEPLOY_USER} << ENDSSH
    cd ${REMOTE_DIR}
    echo "Building Docker images..."
    ${COMPOSE_CMD} build
    echo "Stopping existing services..."
    ${COMPOSE_CMD} down
    echo "Starting services..."
    ${COMPOSE_CMD} up -d
    echo "Waiting for services to be ready..."
    sleep 10
    ${COMPOSE_CMD} ps
ENDSSH

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services are running on:"
echo "  Frontend:  http://${REMOTE_HOST}:3000"
echo "  Backend:   http://${REMOTE_HOST}:8000"
echo "  API Docs:  http://${REMOTE_HOST}:8000/docs"
echo ""
echo "To check logs:"
echo "  ssh -p ${REMOTE_PORT} ${DEPLOY_USER} 'cd ${REMOTE_DIR} && ${COMPOSE_CMD} logs -f'"
echo ""
echo "To stop services:"
echo "  ssh -p ${REMOTE_PORT} ${DEPLOY_USER} 'cd ${REMOTE_DIR} && ${COMPOSE_CMD} down'"
echo ""
