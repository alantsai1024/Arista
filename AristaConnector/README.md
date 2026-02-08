# Arista vEOS Connector

Arista vEOS connector with real-device polling via eAPI, Redis health state, PostgreSQL events, and MQTT publishing.

Primary validation flow now targets real vEOS devices:
- `192.168.56.2`
- `192.168.56.3`
- `192.168.56.4`

Default credentials used by bootstrap:
- username: `admin`
- password: `0000`

## Core Features

- Device CRUD APIs (`POST/GET/PATCH/DELETE /devices`)
- eAPI connection test (`POST /devices/{id}/test-connection`)
- Collector polling profile (shared source):
  - `show clock`
  - `show hostname`
  - `show interfaces status`
  - `show version`
- MQTT outputs:
  - `arista/default/<device_id>/state` (retained)
  - `arista/default/<device_id>/telemetry/<collector>` (non-retained)
- Optional poctest-compatible raw MQTT topics:
  - `network/arista/raw/...` when `MQTT_RAW_COMPAT_ENABLED=true`
- Local raw evidence retention:
  - `backend/runtime/raw`
  - `backend/runtime/raw_ref`

## Quick Start

See `QUICKSTART.md`.
For device onboarding details (Chinese), see `ADD_DEVICES_GUIDE_ZH.md`.

## Real vEOS Bootstrap

Use the backend bootstrap script to:
1. Probe the three target vEOS devices by eAPI.
2. Interactively clean up non-target devices (`delete/disable/keep`).
3. Upsert target devices.
4. Run connection tests.

Docker mode:
```bash
docker compose up -d
docker compose exec backend python scripts/bootstrap_real_veos.py
```

Local backend mode:
```bash
cd backend
python scripts/bootstrap_real_veos.py
```

## Configuration

Main environment variables:

- `MQTT_RAW_COMPAT_ENABLED` (default `false`)
- `RETENTION_ENABLED` (default `true`)
- `RETENTION_BASE_DIR` (default `./runtime`)
- `RETENTION_TARGETS` (default `*`)
- `VEOS_TARGETS` (default `192.168.56.2,192.168.56.3,192.168.56.4`)
- `VEOS_USERNAME` (default `admin`)
- `VEOS_PASSWORD` (default `0000`)
- `VEOS_PORT` (default `443`)
- `VEOS_INTERVAL_SEC` (default `10`)

## Validation

- API docs: `http://localhost:8000/docs`
- Fleet health: `GET /health/fleet`
- Device events: `GET /devices/{id}/events`
- MQTT subscribe helper: `scripts/subscribe_topics.sh`

Detailed test flow: `DEMO_TESTCASES.md`.

## Windows Local Setup (No Docker)

See `LOCAL_WINDOWS_SETUP.md` for PostgreSQL + Redis + Mosquitto + backend/collector setup on Windows.
