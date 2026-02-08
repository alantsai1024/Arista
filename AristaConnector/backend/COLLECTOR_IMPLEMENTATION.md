# 採集器服務實作摘要

## ✅ 已完成功能

### 1. Collector 服務（`backend/collector.py`）

**核心功能：**
- ✅ 從資料庫載入已啟用設備
- ✅ 依每台設備設定的 `interval_sec` 輪詢（預設 10 秒）
- ✅ 執行 eAPI 指令：`show clock`、`show hostname`、`show interfaces status`
- ✅ 使用 async httpx + 併發控制（semaphore，預設 20）
- ✅ 指數退避：10s → 20s → 40s → 60s（上限 60s）
- ✅ 將事件寫入 Postgres（events 資料表）
- ✅ 更新 Redis 健康資訊：
  - `device:<id>:last_seen` = 現在時間（TTL 60 秒）
  - `device:<id>:status` = online/degraded/offline
  - `device:<id>:latency_ms` = 回應延遲
- ✅ 離線規則：若 `now - last_seen > 30s` 則視為 offline

**狀態邏輯：**
- `online`：輪詢成功，且 last_seen 在 30 秒內
- `degraded`：連續 1 到 2 次失敗
- `offline`：連續 3 次以上失敗，或 last_seen 超過 30 秒

### 2. Events DAO（`backend/app/dao/events.py`）

- ✅ `create_event()`：建立事件
- ✅ `get_recent_events()`：取得設備近期事件
- ✅ `get_event_stats()`：取得事件統計

### 3. 採集器客戶端（`backend/app/services/collector_client.py`）

- ✅ `poll_device()`：執行 eAPI 輪詢
- ✅ 回傳 success、錯誤訊息、資料與延遲
- ✅ `calculate_backoff_delay()`：計算指數退避延遲

### 4. 已更新 API 端點

**GET /health/fleet**（`backend/app/routers/health.py`）：
- ✅ 總覽計數：online/offline/degraded
- ✅ 延遲最高前 5 台設備
- ✅ 設備狀態清單

**GET /devices/{id}/status**（`backend/app/routers/devices.py`）：
- ✅ 健康狀態
- ✅ 最後上線時間
- ✅ 近期統計：
  - 最近 1 小時總事件數
  - 依事件類型分組
  - 最新事件時間
  - 延遲（ms）

### 5. Mock eAPI Server（`backend/tests/mock_eapi_server.py`）

- ✅ 以 FastAPI 實作 mock server
- ✅ 回傳固定 eAPI JSON
- ✅ 支援不同 port 啟動多個實例
- ✅ 支援 basic auth（測試時接受任意帳密）

### 6. 測試（`backend/tests/test_collector.py`）

**負載測試：**
- ✅ 建立 30 台 mock 設備
- ✅ 啟動 30 個 mock server
- ✅ 執行 collector 35 秒
- ✅ 驗證：
  - 每台設備至少有 3 筆事件
  - Redis 狀態皆為 online

**故障測試：**
- ✅ 建立 device-05 並先確認 online
- ✅ 停止 mock server
- ✅ 經輪詢後 device-05 轉為 offline
- ✅ 重啟 server 後恢復 online

### 7. 設定

**環境變數：**
- `POLLING_TIMEOUT`：請求逾時（預設 5.0 秒）
- `MAX_CONCURRENT_POLLS`：semaphore 上限（預設 20）
- `OFFLINE_THRESHOLD_SEC`：離線門檻（預設 30 秒）

## 架構

```
collector.py（主迴圈）
  ├── get_enabled_devices() - 從 DB 載入設備
  ├── poll_single_device() - 帶退避的輪詢
  │   ├── poll_device() - eAPI client
  │   ├── update_redis_health() - 更新 Redis
  │   ├── create_event() - 寫入 Postgres
  │   └── publish_state/telemetry() - 發布 MQTT
  └── 透過 semaphore 做併發控制
```

## 退避策略

| 嘗試次數 | 延遲（秒） |
|---------|-----------|
| 1       | 10        |
| 2       | 20        |
| 3       | 40        |
| 4+      | 60（上限） |

## 狀態判定

1. **Online**：輪詢成功且 last_seen 在 30 秒內
2. **Degraded**：連續 1 到 2 次錯誤
3. **Offline**：連續 3 次以上錯誤，或 last_seen 超過 30 秒

## 測試執行

執行 collector 測試：
```bash
make test-collector
# 或
docker compose exec backend pytest tests/test_collector.py -v -s
```

## 下一步

1. 新增指標與可觀測性（Prometheus）
2. 針對暫時性錯誤增加重試策略
3. 增加每設備自訂 timeout 設定
4. 以批次方式寫入事件提升效能
5. 增加 collector 自身健康檢查端點

