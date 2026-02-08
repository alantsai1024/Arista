# Quick Test (Real vEOS)

## 1. Start Services

```bash
docker compose up -d
docker compose ps
```

## 2. Bootstrap Target Devices

```bash
docker compose exec backend python scripts/bootstrap_real_veos.py
```

This script will:
- probe `192.168.56.2/3/4`
- ask how to handle non-target devices (`delete/disable/keep`)
- upsert target devices
- run test-connection per target device

## 3. Validate API

```bash
curl http://localhost:8000/devices
curl http://localhost:8000/health/fleet
```

## 4. Validate Events

```bash
# find device id first
curl http://localhost:8000/devices

# then query events
curl http://localhost:8000/devices/<device_id>/events
```

## 5. Validate MQTT

```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -v
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

Optional raw compatibility:
```bash
# set in .env
MQTT_RAW_COMPAT_ENABLED=true
docker compose restart backend collector
docker compose exec mqtt mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```
