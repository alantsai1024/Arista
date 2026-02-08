# Scripts

## `subscribe_topics.sh`

MQTT topic subscribe helper.

Usage:
```bash
./scripts/subscribe_topics.sh state
./scripts/subscribe_topics.sh telemetry
./scripts/subscribe_topics.sh all
./scripts/subscribe_topics.sh <device_id>
```

## `seed_30_devices.py` (Deprecated)

This script is intentionally deprecated.

The project now uses real vEOS onboarding:
```bash
docker compose exec backend python scripts/bootstrap_real_veos.py
# or
cd backend && python scripts/bootstrap_real_veos.py
```
