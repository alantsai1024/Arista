# 後端修改指南（新手版）

這份文件專門給「第一次要改後端」的人。  
你會看到每個檔案的角色、它們如何配合、流程長什麼樣，以及「要改 Arista 路由器整合」時該改哪些檔案、怎麼改。  
內容包含程式碼、圖表、流程、文字說明與表格統整。

---

## 讀這份文件的最佳順序
1. 系統結構圖
2. 檔案協作流程圖
3. 檔案角色一覽表
4. 主要流程（API / Collector）
5. Arista 整合修改步驟與範例

---

## 系統結構圖（ASCII）
```
[Frontend / User]
        |
        v
    [FastAPI] -----> [PostgreSQL]
        |                |
        |                v
        |             [events]
        |
        +-----> [Redis] (status/last_seen/latency)

[Collector] -> [Arista eAPI Device] -> [MQTT Broker]
```

---

## 檔案協作流程圖（ASCII）
```
devices.py (API 路由)
   -> schemas.py (輸入/輸出驗證)
   -> models.py (資料表)
   -> database.py (DB 連線)
   -> dao/events.py (事件寫入/查詢)

collector.py (輪詢主程式)
   -> collector_client.py (eAPI 輪詢)
   -> eapi_client.py (單次測試)
   -> mqtt_client.py (MQTT 發佈)
   -> redis_client.py (Redis 狀態)
```

---

## 檔案角色一覽（表格）

| 檔案 | 角色 | 常見修改情境 |
|---|---|---|
| `backend/main.py` | FastAPI 入口、路由註冊 | 新增 middleware 或全域設定 |
| `backend/app/routers/devices.py` | 設備 CRUD 與狀態 API | 新增欄位或新 API |
| `backend/app/routers/health.py` | 機群健康 API | 調整健康統計輸出 |
| `backend/app/models.py` | 資料表模型 | 新增資料欄位 |
| `backend/app/schemas.py` | API schema 驗證 | API 請求/回應欄位 |
| `backend/app/dao/events.py` | events 存取 | 事件寫入/統計 |
| `backend/app/services/eapi_client.py` | 單次 eAPI 測試 | 改測試指令 |
| `backend/app/services/collector_client.py` | eAPI 輪詢與退避 | 新增輪詢指令 |
| `backend/app/services/mqtt_client.py` | MQTT 發佈格式 | 新增 topic / mapping |
| `backend/app/services/redis_client.py` | Redis 連線 | 改 Redis 行為 |
| `backend/collector.py` | 輪詢主流程 | 改輪詢策略 |

---

## 資料流向與儲存位置（表格）

| 資料 | 寫入位置 | 說明 |
|---|---|---|
| 設備資料 | PostgreSQL `devices` | API 建立/更新 |
| 輪詢事件 | PostgreSQL `events` | Collector 成功/失敗 |
| 最後看到時間 | Redis `device:<id>:last_seen` | Collector 更新 |
| 設備狀態 | Redis `device:<id>:status` | online / degraded / offline |
| 輪詢延遲 | Redis `device:<id>:latency_ms` | API 查狀態會讀 |
| MQTT 狀態 | topic `.../state` | retain=true |
| MQTT 遙測 | topic `.../telemetry/<collector>` | retain=false |

---

## 主要流程（文字 + 流程圖）

### 1. API 建立設備流程
```
Client -> POST /devices
        -> 驗證 IP/interval
        -> 密碼加密 (base64)
        -> 寫入 Postgres
        -> 回傳 Device
```

### 2. 查設備狀態流程
```
Client -> GET /devices/{id}/status
        -> Redis 取 last_seen/status/latency
        -> events 統計
        -> 回傳狀態
```

### 3. Collector 輪詢流程
```
Collector -> 取 enabled devices
          -> 判斷 interval 是否該輪詢
          -> eAPI 呼叫
          -> 成功: Redis + Event + MQTT
          -> 失敗: 退避 + Event + Redis
```

---

## 與 Arista 路由器整合：完整操作指南

### 一、設備端準備清單
- 啟用 eAPI 並可用 HTTPS 存取 `/command-api`
- 確保管理網路可連到設備的 IP/port
- 建立具備 `show` 權限的帳號

### 二、專案端設定步驟
1. 使用 API 建立設備資料
2. 執行 `POST /devices/{id}/test-connection` 測試連線
3. 啟動 Collector，開始輪詢
4. 透過 API 或 MQTT 檢查是否有資料

### 三、若要「改整合內容」要改哪些檔案
| 修改目的 | 主要檔案 |
|---|---|
| 新增/修改輪詢指令 | `backend/app/services/collector_client.py` |
| 調整 MQTT collector 名稱 | `backend/app/services/mqtt_client.py` |
| 測試 eAPI 指令 | `backend/app/services/eapi_client.py` |
| 改輪詢策略 | `backend/collector.py` |
| 新增 API 回傳欄位 | `backend/app/routers/*.py`, `backend/app/schemas.py` |

---

## 修改範例：新增一個 eAPI 指令

### 步驟 1：修改輪詢指令清單
檔案：`backend/app/services/collector_client.py`
```python
EAPI_COMMANDS = [
    "show clock",
    "show hostname",
    "show interfaces status",
    "show version"
]
```

### 步驟 2：加上 MQTT 對應名稱
檔案：`backend/app/services/mqtt_client.py`
```python
mapping = {
    "show clock": "system-clock",
    "show hostname": "system-hostname",
    "show interfaces status": "interfaces-status",
    "show version": "system-version"
}
```

### 步驟 3：需要進 DB 才改 Model/Schema
只有在你要把資料存成欄位時才需要改：
- `backend/app/models.py`
- `backend/app/schemas.py`

---

## 修改範例：新增 API 欄位

### 目標：在 Device 新增 `location`
1. 修改 `backend/app/models.py` 新增欄位
2. 修改 `backend/app/schemas.py` 加入欄位
3. 修改 `backend/app/routers/devices.py` 讓 API 接受/回傳

範例片段（示意）：
```python
# models.py
location = Column(String(255), nullable=True)
```
```python
# schemas.py
location: Optional[str] = None
```

---

## 常見修改情境（快速指引）

### 想改輪詢頻率
修改資料庫中 `devices.interval_sec`。  
Collector 會依每台設備的 interval 控制頻率。

### 想改 online/offline 判斷邏輯
修改 `backend/collector.py` 的 `OFFLINE_THRESHOLD_SEC` 或 `get_device_status()`。

### 想改 MQTT 資料格式
修改 `backend/app/services/mqtt_client.py` 的 `create_envelope()`。

---

## 常見錯誤排查（表格）

| 問題 | 可能原因 | 建議處理 |
|---|---|---|
| 連線逾時 | 管理 IP 不通、ACL 擋、port 未開 | 檢查網路與 firewall |
| 驗證失敗 | 帳密錯誤或權限不足 | 確認帳號可跑 `show` |
| 無 MQTT 資料 | MQTT 連線失敗 | 檢查 broker 設定 |
| API 查不到狀態 | Redis 沒更新 | 確認 Collector 是否有跑 |

---

## 小結
如果你是第一次改後端，建議先從：
1. `collector_client.py` 改指令
2. `mqtt_client.py` 改 mapping
3. `collector.py` 看流程
開始就能理解全系統如何配合。
