# Local Windows Setup (No Docker)

This guide installs and runs all required services directly on Windows:
- PostgreSQL
- Redis
- Mosquitto
- FastAPI backend
- Collector

## 1) Install PostgreSQL

1. Install PostgreSQL 15+ from official installer.
2. Create database and user:
```sql
CREATE USER arista WITH PASSWORD 'arista123';
CREATE DATABASE arista OWNER arista;
```
3. Verify:
```powershell
psql -h localhost -U arista -d arista -c "SELECT 1;"
```

## 2) Install Redis

Options:
- Redis on Windows build, or
- Redis via WSL (if allowed in your environment).

Verify:
```powershell
redis-cli ping
```
Expected: `PONG`.

## 3) Install Mosquitto

1. Install Eclipse Mosquitto for Windows.
2. Start broker (default 1883):
```powershell
mosquitto -v
```
3. Verify in another terminal:
```powershell
mosquitto_pub -h localhost -t test -m hello
mosquitto_sub -h localhost -t test -C 1
```

## 4) Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set env vars:
```powershell
$env:DATABASE_URL="postgresql://arista:arista123@localhost:5432/arista"
$env:REDIS_URL="redis://localhost:6379/0"
$env:MQTT_HOST="localhost"
$env:MQTT_PORT="1883"
$env:MQTT_RAW_COMPAT_ENABLED="false"
$env:RETENTION_ENABLED="true"
$env:RETENTION_BASE_DIR="./runtime"
$env:RETENTION_TARGETS="*"
```

Start API:
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 5) Collector Setup

New terminal:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://arista:arista123@localhost:5432/arista"
$env:REDIS_URL="redis://localhost:6379/0"
$env:MQTT_HOST="localhost"
$env:MQTT_PORT="1883"
python collector.py
```

## 6) Real vEOS Bootstrap

New terminal:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:VEOS_TARGETS="192.168.56.2,192.168.56.3,192.168.56.4"
$env:VEOS_USERNAME="admin"
$env:VEOS_PASSWORD="0000"
$env:VEOS_PORT="443"
$env:VEOS_INTERVAL_SEC="10"
python scripts/bootstrap_real_veos.py
```

## 7) Acceptance Checks

```powershell
curl http://localhost:8000/devices
curl http://localhost:8000/health/fleet
curl http://localhost:8000/devices/<device_id>/events
```

MQTT checks:
```powershell
mosquitto_sub -h localhost -t "arista/default/+/state" -v
mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

Optional raw compatibility:
```powershell
$env:MQTT_RAW_COMPAT_ENABLED="true"
# restart backend + collector processes
mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```
