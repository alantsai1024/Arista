# MQTT 發布實作摘要

## ✅ 已完成功能

### 1. MQTT Client 模組（`backend/app/services/mqtt_client.py`）

**設定：**
- ✅ 環境變數：`MQTT_HOST`、`MQTT_PORT`、`MQTT_TLS`、`MQTT_USERNAME`、`MQTT_PASSWORD`
- ✅ 支援 TLS 連線
- ✅ 自動重連處理

**發布：**
- ✅ `publish_state()`：狀態訊息（QoS=1，retained=true）
- ✅ `publish_telemetry()`：遙測訊息（QoS=1，retained=false）
- ✅ 所有訊息使用一致 envelope 格式

**Topic 結構：**
- 狀態：`arista/default/<device_id>/state`
- 遙測：`arista/default/<device_id>/telemetry/<collector>`
  - Collectors：`system-clock`、`system-hostname`、`interfaces-status`

**Envelope 格式：**
```json
{
  "ts": <unix_timestamp>,
  "tenant": "default",
  "device": {
    "id": "<uuid>",
    "hostname": "<hostname>",
    "ip": "<ip_address>"
  },
  "source": {
    "type": "arista_eapi",
    "collector": "<collector_name>",
    "command": "<eapi_command>",
    "duration_ms": <latency>
  },
  "status": "ok" | "error",
  "data": { ... }
}
```

### 2. Collector 整合（`backend/collector.py`）

- ✅ 輪詢成功時發布狀態訊息
- ✅ 每個 eAPI 指令都發布遙測訊息
- ✅ envelope 內含 latency
- ✅ 有處理 MQTT 發布失敗情況

### 3. Docker Compose

- ✅ 已配置 Mosquitto 容器
- ✅ 已配置 MQTT 相關環境變數
- ✅ 已啟用健康檢查

### 4. 整合測試（`backend/tests/test_mqtt.py`）

**測試涵蓋：**
- ✅ `test_state_retained`：晚訂閱者可收到 retained state
- ✅ `test_telemetry_not_retained`：晚訂閱者不會收到舊 telemetry
- ✅ `test_qos1_publish_no_error`：QoS=1 發布可正常完成
- ✅ `test_envelope_structure`：驗證 envelope 格式
- ✅ `test_collector_name_mapping`：驗證 command 到 collector 名稱映射

### 5. Makefile

- ✅ 已新增 `make test-mqtt`

## 環境變數

```bash
MQTT_HOST=mqtt          # MQTT broker 主機名稱
MQTT_PORT=1883         # MQTT broker 埠號
MQTT_TLS=false         # 是否啟用 TLS（true/false）
MQTT_USERNAME=         # 可選：帳號
MQTT_PASSWORD=         # 可選：密碼
```

## 主題範例

**State Topic：**
```
arista/default/550e8400-e29b-41d4-a716-446655440000/state
```

**Telemetry Topics：**
```
arista/default/550e8400-e29b-41d4-a716-446655440000/telemetry/system-clock
arista/default/550e8400-e29b-41d4-a716-446655440000/telemetry/system-hostname
arista/default/550e8400-e29b-41d4-a716-446655440000/telemetry/interfaces-status
```

## 訊息流程

1. Collector 輪詢設備成功
2. 發布 state 訊息（retained=true）
3. 針對每個命令發布 telemetry（retained=false）
4. 晚訂閱者會立刻收到 state（retained）
5. 晚訂閱者不會收到舊 telemetry（非 retained）

## 測試

執行 MQTT 測試：
```bash
make test-mqtt
# 或
docker compose exec backend pytest tests/test_mqtt.py -v -s
```

## 採集器名稱映射

| eAPI 指令 | Collector 名稱 |
|-----------|----------------|
| `show clock` | `system-clock` |
| `show hostname` | `system-hostname` |
| `show interfaces status` | `interfaces-status` |

## 下一步

1. 增加 MQTT 訊息驗證
2. 新增 MQTT 發布成功/失敗指標
3. 支援依租戶自訂 topics
4. 大訊息 payload 壓縮
5. 高吞吐場景的 MQTT 連線池化

