# 示範測試案例（真實 vEOS）

此測試套件用於驗證真實設備整合，目標設備為：
- `192.168.56.2`
- `192.168.56.3`
- `192.168.56.4`

## 準備

Docker：
```bash
cp .env.example .env
cp secrets/veos_credentials.example.json secrets/veos_credentials.json
docker compose up -d
docker compose exec backend python scripts/bootstrap_real_veos.py
```

本機：
```powershell
Copy-Item .\.env.example .\.env
Copy-Item .\secrets\veos_credentials.example.json .\secrets\veos_credentials.json
cd backend
$env:VEOS_TARGETS="192.168.56.2,192.168.56.3,192.168.56.4"
$env:VEOS_CREDENTIALS_FILE="..\secrets\veos_credentials.json"
python scripts/bootstrap_real_veos.py
```

注意：
- credentials 檔需使用 IP -> `{username,password}` 的 JSON 對應。
- `VEOS_TARGETS` 必須和 JSON key 完全一致。
- bootstrap 預設 `--probe-failure-policy continue`，當部分設備離線時仍會繼續 upsert 其餘設備並輸出失敗摘要。

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

Docker 內檢查：
```bash
docker compose exec collector sh -lc "ls -lah /app/runtime/raw /app/runtime/raw_ref"
docker compose exec collector sh -lc "find /app/runtime/raw -type f | head -n 10"
docker compose exec collector sh -lc "cat $(find /app/runtime/raw -type f | head -n 1)"
```

主機端檢查（開發 compose 有 `./backend:/app` 掛載）：
```bash
ls -lah backend/runtime/raw backend/runtime/raw_ref
```

預期：
- 有依 collector 產生的 raw 檔案與中繼參照資訊。

## TC-07：單一 vEOS 離線時仍可顯示其他設備

步驟：
1. 關閉其中一台 vEOS（例如 `192.168.56.4`）。
2. 執行：
```bash
docker compose exec backend python scripts/bootstrap_real_veos.py --probe-failure-policy continue
```
3. 開啟 `http://localhost:3000/fleet`。

預期：
- bootstrap 不會因單台失敗而整批中止，並會輸出 probe 失敗摘要。
- Fleet 頁面仍可顯示其他正常設備，不會整頁卡住。
- Fleet 顯示「管理者告警」，包含離線/降級/未知設備統計與異常清單。
- `curl http://localhost:8000/health/fleet` 的每台 `devices[]` 都包含 `recent_stats` 欄位。
