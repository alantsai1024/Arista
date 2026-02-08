# 快速測試（真實 vEOS）

## 1. 啟動服務

```bash
docker compose up -d
docker compose ps
```

## 2. Bootstrap 目標設備

```bash
docker compose exec backend python scripts/bootstrap_real_veos.py
```

此腳本會：
- 探測 `192.168.56.2/3/4`
- 詢問如何處理非目標設備（`delete/disable/keep`）
- 對目標設備執行 upsert
- 逐台執行 test-connection

## 3. 驗證 API

```bash
curl http://localhost:8000/devices
curl http://localhost:8000/health/fleet
```

## 4. 驗證事件

```bash
# 先找 device id
curl http://localhost:8000/devices

# 再查事件
curl http://localhost:8000/devices/<device_id>/events
```

## 5. 驗證 MQTT

```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -v
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

可選原始相容模式：
```bash
# 在 .env 設定
MQTT_RAW_COMPAT_ENABLED=true
docker compose restart backend collector
docker compose exec mqtt mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```
