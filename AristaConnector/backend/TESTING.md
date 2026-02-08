# Backend Testing Guide

## Run Tests

Docker:
```bash
docker compose exec backend pytest tests/ -v
```

Local:
```bash
cd backend
pytest tests/ -v
```

## Key Test Files

- `tests/test_devices_api.py`
  - device CRUD
  - includes `DELETE /devices/{id}` tests
- `tests/test_connection.py`
  - `test-connection` endpoint behavior
- `tests/test_collector_client.py`
  - collector command profile contains `show version`
- `tests/test_retention_sink.py`
  - retention failures are non-blocking
- `tests/test_collector.py`
  - small-scale mock collector flow (3 devices)
- `tests/test_mqtt.py`
  - MQTT envelope and collector-name mapping

## Notes

- Main acceptance is now real vEOS integration (not fake 30-device seeding).
- To validate against real devices, use `scripts/bootstrap_real_veos.py` and follow root-level `DEMO_TESTCASES.md`.
