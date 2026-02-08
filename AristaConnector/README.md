# Arista vEOS 連接器

此專案透過 eAPI 對真實設備進行輪詢，並整合 Redis 健康狀態、PostgreSQL 事件紀錄與 MQTT 發布。

目前主要驗證流程以以下 vEOS 真機為目標：
- `192.168.56.2`
- `192.168.56.3`
- `192.168.56.4`

Bootstrap 預設帳密：
- 使用者名稱：`admin`
- 密碼：`0000`

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
設備上線的中文說明請見 `ADD_DEVICES_GUIDE_ZH.md`。

## 真實 vEOS Bootstrap

使用 backend bootstrap 腳本可完成：
1. 以 eAPI 探測三台目標 vEOS。
2. 以互動方式清理非目標設備（`delete/disable/keep`）。
3. 對目標設備執行 upsert。
4. 執行連線測試。

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
- `VEOS_USERNAME`（預設 `admin`）
- `VEOS_PASSWORD`（預設 `0000`）
- `VEOS_PORT`（預設 `443`）
- `VEOS_INTERVAL_SEC`（預設 `10`）

## 驗證

- API 文件：`http://localhost:8000/docs`
- 機群健康：`GET /health/fleet`
- 設備事件：`GET /devices/{id}/events`
- MQTT 訂閱輔助腳本：`scripts/subscribe_topics.sh`

詳細測試流程請見 `DEMO_TESTCASES.md`。

## Windows 本機安裝（無 Docker）

請參考 `LOCAL_WINDOWS_SETUP.md`，內含 Windows 上 PostgreSQL、Redis、Mosquitto 與 backend/collector 的完整設定。
