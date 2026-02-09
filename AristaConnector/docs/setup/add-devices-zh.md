# 新增設備指南（Arista vEOS Connector）

本文件說明此專案如何把「真實設備」加入輪詢，並驗證 eAPI、狀態與 MQTT 是否正常。

適用情境：
- Docker Compose（Ubuntu/Linux）
- Backend Local 模式（手動啟動 API 與 collector）

## 1. 先確認服務已啟動

```bash
cd /home/alan/newArista/AristaConnector
docker compose up -d
docker compose ps
```

建議先確認 API 可用：

```bash
curl -s http://localhost:8000/health/fleet | jq .
```

## 2. 方法 A：新增單一設備（最快）

### 2.1 建立設備

```bash
curl -X POST http://localhost:8000/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "hostname":"vEOS-SW10",
    "ip":"192.168.56.10",
    "port":443,
    "username":"admin",
    "password":"0000",
    "interval_sec":10,
    "enabled":true
  }'
```

### 2.2 取得 device_id

```bash
curl -s http://localhost:8000/devices | jq .
```

### 2.3 測試該設備 eAPI 連線

```bash
curl -X POST http://localhost:8000/devices/<device_id>/test-connection
```

### 2.4 查詢輪詢狀態

```bash
curl -s http://localhost:8000/devices/<device_id>/status | jq .
```

## 3. 方法 B：批次新增設備（推薦）

此方法會先對目標 IP 做 eAPI probe，再 upsert 到 `/devices`。

```bash
cd /home/alan/newArista/AristaConnector
docker compose exec backend python scripts/bootstrap_real_veos.py \
  --targets "192.168.56.2,192.168.56.3,192.168.56.4,192.168.56.10" \
  --username admin \
  --password 0000 \
  --port 443 \
  --interval-sec 10
```

不想互動式詢問時可加上：

```bash
--non-interactive-action keep
```

可選值：`keep`、`disable`、`delete`。

## 4. 調整既有設備（IP/帳密/輪詢間隔/啟用狀態）

```bash
curl -X PATCH http://localhost:8000/devices/<device_id> \
  -H 'Content-Type: application/json' \
  -d '{
    "ip":"192.168.56.10",
    "username":"admin",
    "password":"0000",
    "interval_sec":10,
    "enabled":true
  }'
```

## 5. 驗證輪詢與 MQTT

### 5.1 觀察 collector 輪詢

```bash
docker compose logs -f collector
```

你應該看到類似：
- `✓ Device ... - online`
- 若失敗則會有 `poll_error` 訊息

### 5.2 訂閱 MQTT topic

```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -t "arista/default/+/telemetry/+" -v
```

topic 說明：
- `arista/default/<device_id>/state`：保留訊息（retained）
- `arista/default/<device_id>/telemetry/<collector>`：非保留訊息（non-retained）

### 5.3 API 驗證

```bash
curl -s http://localhost:8000/health/fleet | jq .
curl -s http://localhost:8000/devices/<device_id>/events | jq .
```

## 6. 常見問題與排查

| 問題 | 常見原因 | 建議處理 |
|---|---|---|
| 新增成功但顯示 `offline` | collector 沒跑、設備不可達、帳密錯誤 | `docker compose logs -f collector`，再測 `POST /devices/{id}/test-connection` |
| 看不到 MQTT 訊息 | MQTT 未連線或訂閱 topic 不對 | 檢查 `arista-mqtt` 狀態，訂閱 `arista/default/+/state` 與 `arista/default/+/telemetry/+` |
| `Device with this IP address already exists` | 同 IP 已存在 | 用 `PATCH /devices/{id}` 更新，或刪除舊設備後重建 |
| 設備常被判斷離線 | `interval_sec` 設太長 | 建議先用 `10~30` 秒；若要更長，需同步調整健康判斷策略 |

## 7. 推薦操作順序

1. 先跑 `test-connection` 確認 eAPI 通。
2. 再觀察 `collector` log 是否持續 `poll_success`。
3. 最後用 MQTT 訂閱驗證資料流完整。

---

如需大量設備上線，建議優先使用 `bootstrap_real_veos.py`，比手動逐台 `POST /devices` 更一致、可重複執行且容易追蹤結果。
