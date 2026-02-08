# Quick Start

## Mode A: Docker Compose

1. Start services:
```bash
docker compose up -d
```

2. Confirm services:
```bash
docker compose ps
docker compose logs -f backend collector
```

3. Bootstrap real vEOS devices (interactive cleanup included):
```bash
docker compose exec backend python scripts/bootstrap_real_veos.py
```

4. Validate:
```bash
curl http://localhost:8000/devices
curl http://localhost:8000/health/fleet
```

5. Validate MQTT:
```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/state" -v
docker compose exec mqtt mosquitto_sub -h localhost -t "arista/default/+/telemetry/+" -v
```

## Mode B: Local Windows (No Docker)

Use `LOCAL_WINDOWS_SETUP.md` to install:
- PostgreSQL
- Redis
- Mosquitto

Then run:
```powershell
cd backend
pip install -r requirements.txt
$env:DATABASE_URL="postgresql://arista:arista123@localhost:5432/arista"
$env:REDIS_URL="redis://localhost:6379/0"
$env:MQTT_HOST="localhost"
$env:MQTT_PORT="1883"
uvicorn main:app --host 0.0.0.0 --port 8000
```

In another terminal:
```powershell
cd backend
python collector.py
```

Bootstrap real devices:
```powershell
cd backend
python scripts/bootstrap_real_veos.py
```

## Notes

- `scripts/seed_30_devices.py` is deprecated.
- Main acceptance is based on real vEOS polling and API+MQTT verification.
