# Windows 本機安裝（無 Docker）

本指南說明如何在 Windows 直接安裝並啟動所有必要服務：
- PostgreSQL
- Redis
- Mosquitto
- FastAPI backend
- Collector

## 1) 安裝 PostgreSQL

1. 從官方安裝程式安裝 PostgreSQL 15 以上版本。
2. 建立資料庫與使用者：
```sql
CREATE USER arista WITH PASSWORD 'arista123';
CREATE DATABASE arista OWNER arista;
```
3. 驗證連線：
```powershell
psql -h localhost -U arista -d arista -c "SELECT 1;"
```

## 2) 安裝 Redis

可選方案：
- 使用 Windows 版本 Redis
- 或透過 WSL 安裝 Redis（若環境允許）

驗證：
```powershell
redis-cli ping
```
預期回應：`PONG`。

## 3) 安裝 Mosquitto

1. 安裝 Eclipse Mosquitto（Windows 版）。
2. 啟動 broker（預設 1883）：
```powershell
mosquitto -v
```
3. 在另一個終端機驗證：
```powershell
mosquitto_pub -h localhost -t test -m hello
mosquitto_sub -h localhost -t test -C 1
```

## 4) 設定 Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

設定環境變數：
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

啟動 API：
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 5) 設定 Collector

開新終端機：
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://arista:arista123@localhost:5432/arista"
$env:REDIS_URL="redis://localhost:6379/0"
$env:MQTT_HOST="localhost"
$env:MQTT_PORT="1883"
python collector.py
```

## 6) 真實 vEOS Bootstrap

先在專案根目錄建立逐機帳密檔（請填入真實帳密）：
```powershell
Copy-Item .\secrets\veos_credentials.example.json .\secrets\veos_credentials.json
```

建議限制檔案權限：
```powershell
icacls .\secrets\veos_credentials.json /inheritance:r /grant:r "$env:USERNAME:(R)"
```

開新終端機：
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:VEOS_TARGETS="192.168.56.2,192.168.56.3,192.168.56.4"
$env:VEOS_CREDENTIALS_FILE="..\secrets\veos_credentials.json"
$env:VEOS_PORT="443"
$env:VEOS_INTERVAL_SEC="10"
python scripts/bootstrap_real_veos.py
```

## 7) 驗收檢查

```powershell
curl http://localhost:8000/devices
curl http://localhost:8000/health/fleet
curl http://localhost:8000/devices/<device_id>/events
```

MQTT 檢查：
```powershell
mosquitto_sub -h localhost -t "arista/default/+/state" -v
mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

可選原始相容模式：
```powershell
$env:MQTT_RAW_COMPAT_ENABLED="true"
# 重新啟動 backend 與 collector
mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```
