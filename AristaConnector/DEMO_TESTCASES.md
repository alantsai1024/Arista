# Demo Test Cases (Real vEOS)

This test suite validates real-device integration against:
- `192.168.56.2`
- `192.168.56.3`
- `192.168.56.4`

Credentials: `admin/0000`.

## Preparation

Docker:
```bash
docker compose up -d
docker compose exec backend python scripts/bootstrap_real_veos.py
```

Local:
```powershell
cd backend
python scripts/bootstrap_real_veos.py
```

## TC-01: Bootstrap Keeps Only Target Devices

Goal:
- Keep only target devices enabled by using interactive cleanup.

Check:
```bash
curl http://localhost:8000/devices
```

Expected:
- Only target IPs remain enabled (or non-targets are explicitly kept by your choice).

## TC-02: eAPI Connection Test Success

For each target device:
```bash
curl -X POST http://localhost:8000/devices/<id>/test-connection
```

Expected:
- `success=true`
- hostname is returned.

## TC-03: Polling Produces API Events

Wait for at least 2 polling cycles (~20-30s), then:
```bash
curl http://localhost:8000/devices/<id>/events
```

Expected:
- Recent `poll_success` events exist for each target device.

## TC-04: MQTT State + Telemetry

State retained:
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -v
```

Telemetry:
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

Expected:
- state messages arrive and are retained.
- telemetry includes collectors like `system-clock`, `system-hostname`, `interfaces-status`, `system-version`.

## TC-05: Optional poctest-Compatible Raw Topics

Enable:
```bash
# in .env
MQTT_RAW_COMPAT_ENABLED=true
```

Restart collector/backend and subscribe:
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```

Expected:
- raw payload contains keys: `device`, `collector`, `cmds`, `format`, `raw`, `ts`.

## TC-06: Retention Files Written

Check filesystem:
- `backend/runtime/raw`
- `backend/runtime/raw_ref`

Expected:
- per-collector raw files and metadata references are generated.
