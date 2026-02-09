# Arista vEOS 連接器

此專案透過 eAPI 對真實設備進行輪詢，並整合 Redis 健康狀態、PostgreSQL 事件紀錄與 MQTT 發布。

目前主要驗證流程以以下 vEOS 真機為目標：
- `192.168.56.2`
- `192.168.56.3`
- `192.168.56.4`

Bootstrap 逐機帳密改由 secrets JSON 檔提供（IP -> username/password 對應），
請使用 `secrets/veos_credentials.example.json` 建立本機 `secrets/veos_credentials.json`。

## 核心功能

- 設備 CRUD API（`POST/GET/PATCH/DELETE /devices`）
- eAPI 連線測試（`POST /devices/{id}/test-connection`）
- Collector 輪詢設定（共享來源）：
  - `show clock`
  - `show hostname`
  - `show interfaces status`
  - `show version`
- MQTT 輸出：
  - `arista/default/<device_id>/state`（保留訊息 retained）
  - `arista/default/<device_id>/telemetry/<collector>`（非保留訊息）
- 可選 poctest 相容原始 MQTT topic：
  - 當 `MQTT_RAW_COMPAT_ENABLED=true` 時輸出 `network/arista/raw/...`
- 本地原始證據保存：
  - `backend/runtime/raw`
  - `backend/runtime/raw_ref`

## 快速開始

請先閱讀 `QUICKSTART.md`。
設備上線的中文說明請見 `docs/setup/add-devices-zh.md`。

## 真實 vEOS Bootstrap

使用 backend bootstrap 腳本可完成：
1. 以 eAPI 探測三台目標 vEOS。
2. 以互動方式清理非目標設備（`delete/disable/keep`）。
3. 對目標設備執行 upsert。
4. 執行連線測試。

先準備逐機帳密（勿提交真實密碼）：

```bash
cp .env.example .env
cp secrets/veos_credentials.example.json secrets/veos_credentials.json
```

Windows PowerShell：
```powershell
Copy-Item .\.env.example .\.env
Copy-Item .\secrets\veos_credentials.example.json .\secrets\veos_credentials.json
```

Docker 模式：
```bash
docker compose up -d
docker compose exec backend python scripts/bootstrap_real_veos.py
```

本機 backend 模式：
```bash
cd backend
python scripts/bootstrap_real_veos.py
```

## 設定

主要環境變數：

- `MQTT_RAW_COMPAT_ENABLED`（預設 `false`）
- `RETENTION_ENABLED`（預設 `true`）
- `RETENTION_BASE_DIR`（預設 `./runtime`）
- `RETENTION_TARGETS`（預設 `*`）
- `VEOS_TARGETS`（預設 `192.168.56.2,192.168.56.3,192.168.56.4`）
- `VEOS_CREDENTIALS_FILE`（預設 `/run/secrets/veos_credentials.json`）
- `VEOS_PORT`（預設 `443`）
- `VEOS_INTERVAL_SEC`（預設 `10`）

安全建議：
- Linux/macOS：`chmod 600 secrets/veos_credentials.json`
- Windows：`icacls .\secrets\veos_credentials.json /inheritance:r /grant:r "$env:USERNAME:(R)"`
- 請勿將 `secrets/veos_credentials.json` 提交到 git（已在 `.gitignore` 排除）

## 驗證

- API 文件：`http://localhost:8000/docs`
- 機群健康：`GET /health/fleet`
- 設備事件：`GET /devices/{id}/events`
- MQTT 訂閱輔助腳本：`scripts/subscribe_topics.sh`

詳細測試流程請見 `docs/testing/demo-testcases.md`。
完整文件索引請見 `docs/README.md`。

## Windows 本機安裝（無 Docker）

請參考 `docs/setup/local-windows-setup.md`，內含 Windows 上 PostgreSQL、Redis、Mosquitto 與 backend/collector 的完整設定。
