# 示範測試案例（真實 vEOS）

此測試套件用於驗證真實設備整合，目標設備為：
- `192.168.56.2`
- `192.168.56.3`
- `192.168.56.4`

帳密：`admin/0000`。

## 準備

Docker：
```bash
docker compose up -d
docker compose exec backend python scripts/bootstrap_real_veos.py
```

本機：
```powershell
cd backend
python scripts/bootstrap_real_veos.py
```

## TC-01：Bootstrap 僅保留目標設備

目標：
- 透過互動式清理僅啟用目標設備。

檢查：
```bash
curl http://localhost:8000/devices
```

預期：
- 僅目標 IP 保持啟用（或你明確選擇保留的非目標設備）。

## TC-02：eAPI 連線測試成功

對每台目標設備執行：
```bash
curl -X POST http://localhost:8000/devices/<id>/test-connection
```

預期：
- `success=true`
- 有回傳 hostname。

## TC-03：輪詢會產生 API 事件

至少等待 2 個輪詢週期（約 20 到 30 秒）後執行：
```bash
curl http://localhost:8000/devices/<id>/events
```

預期：
- 每台目標設備都可看到近期 `poll_success` 事件。

## TC-04：MQTT 狀態與遙測

狀態（retained）：
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -v
```

遙測：
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

預期：
- state 訊息可收到且具 retained 屬性。
- telemetry 包含 `system-clock`、`system-hostname`、`interfaces-status`、`system-version` 等 collector。

## TC-05：可選 poctest 相容原始 Topic

啟用：
```bash
# 在 .env 中設定
MQTT_RAW_COMPAT_ENABLED=true
```

重啟 backend/collector 後訂閱：
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```

預期：
- raw payload 含有 `device`、`collector`、`cmds`、`format`、`raw`、`ts` 欄位。

## TC-06：保留檔案成功寫入

檢查檔案系統：
- `backend/runtime/raw`
- `backend/runtime/raw_ref`

預期：
- 有依 collector 產生的 raw 檔案與中繼參照資訊。
