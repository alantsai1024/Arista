# 快速開始

## 模式 A：Docker Compose

1. 準備設定與逐機帳密檔：
```bash
cp .env.example .env
cp secrets/veos_credentials.example.json secrets/veos_credentials.json
```

2. 啟動服務：
```bash
docker compose up -d
```

3. 確認服務狀態：
```bash
docker compose ps
docker compose logs -f backend collector
```

4. Bootstrap 真實 vEOS 設備（含互動式清理）：
```bash
docker compose exec backend python scripts/bootstrap_real_veos.py
```

說明：
- 預設 `--probe-failure-policy continue`，若有離線設備會繼續 upsert 其餘設備，並在輸出摘要標示失敗目標。
- 若需舊有 fail-fast 行為，請改用：
```bash
docker compose exec backend python scripts/bootstrap_real_veos.py --probe-failure-policy abort
```

5. 驗證 API：
```bash
curl http://localhost:8000/devices
curl http://localhost:8000/health/fleet
```

6. 驗證 MQTT：
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -v
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

## 模式 B：Windows 本機（無 Docker）

先依 `docs/setup/local-windows-setup.md` 安裝：
- PostgreSQL
- Redis
- Mosquitto

接著執行：
```powershell
cd backend
pip install -r requirements.txt
$env:DATABASE_URL="postgresql://arista:arista123@localhost:5432/arista"
$env:REDIS_URL="redis://localhost:6379/0"
$env:MQTT_HOST="localhost"
$env:MQTT_PORT="1883"
$env:VEOS_TARGETS="192.168.56.2,192.168.56.3,192.168.56.4"
$env:VEOS_CREDENTIALS_FILE="..\secrets\veos_credentials.json"
uvicorn main:app --host 0.0.0.0 --port 8000
```

在另一個終端機：
```powershell
cd backend
python collector.py
```

Bootstrap 真實設備：
```powershell
cd backend
python scripts/bootstrap_real_veos.py
```

說明：
- 預設 `continue` 策略可讓離線設備不影響其他設備建立。
- 需要 fail-fast 可加 `--probe-failure-policy abort`。

## 備註

- `scripts/seed_30_devices.py` 已淘汰。
- 主要驗收依據為真實 vEOS 輪詢與 API + MQTT 驗證。
- Fleet 頁面若遇單一設備或單一路徑 API 異常，仍可顯示其餘設備，並以告警區呈現異常清單與資料來源警告。
