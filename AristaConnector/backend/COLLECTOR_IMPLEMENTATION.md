# Collector Service Implementation Summary

## ✅ Completed Features

### 1. Collector Service (`backend/collector.py`)

**Core Features:**
- ✅ Loads enabled devices from database
- ✅ Polls each device at configured `interval_sec` (default 10s)
- ✅ Executes eAPI commands: `show clock`, `show hostname`, `show interfaces status`
- ✅ Uses async httpx with concurrency control (semaphore, default 20)
- ✅ Implements exponential backoff: 10s → 20s → 40s → 60s (capped at 60s)
- ✅ Writes events to Postgres (events table)
- ✅ Updates Redis health:
  - `device:<id>:last_seen` = now (TTL 60s)
  - `device:<id>:status` = online/degraded/offline
  - `device:<id>:latency_ms` = response latency
- ✅ Offline rule: if `now - last_seen > 30s` then offline

**Status Logic:**
- `online`: Successful poll, last_seen within 30s
- `degraded`: 1-2 consecutive errors
- `offline`: 3+ consecutive errors or last_seen > 30s

### 2. Events DAO (`backend/app/dao/events.py`)

- ✅ `create_event()` - Create new event
- ✅ `get_recent_events()` - Get recent events for device
- ✅ `get_event_stats()` - Get event statistics

### 3. Collector Client (`backend/app/services/collector_client.py`)

- ✅ `poll_device()` - Poll device with eAPI commands
- ✅ Returns success, error message, data, and latency
- ✅ `calculate_backoff_delay()` - Exponential backoff calculation

### 4. Updated API Endpoints

**GET /health/fleet** (`backend/app/routers/health.py`):
- ✅ Summary counts: online/offline/degraded
- ✅ Top 5 latency devices
- ✅ Device status list

**GET /devices/{id}/status** (`backend/app/routers/devices.py`):
- ✅ Health status
- ✅ Last seen timestamp
- ✅ Recent stats:
  - Total events last hour
  - Events by type
  - Last event timestamp
  - Latency (ms)

### 5. Mock eAPI Server (`backend/tests/mock_eapi_server.py`)

- ✅ FastAPI-based mock server
- ✅ Returns static JSON for eAPI commands
- ✅ Supports multiple instances on different ports
- ✅ Basic auth support (accepts any for testing)

### 6. Tests (`backend/tests/test_collector.py`)

**Load Test:**
- ✅ Creates 30 mock devices
- ✅ Starts 30 mock servers
- ✅ Runs collector for 35 seconds
- ✅ Asserts:
  - Each device has >= 3 events stored
  - Redis status online for all devices

**Failure Test:**
- ✅ Creates device-05 with mock server
- ✅ Verifies online status
- ✅ Stops mock server
- ✅ After polling, device-05 becomes offline
- ✅ Restarts server
- ✅ Device-05 recovers to online

### 7. Configuration

**Environment Variables:**
- `POLLING_TIMEOUT` - Request timeout (default 5.0s)
- `MAX_CONCURRENT_POLLS` - Semaphore limit (default 20)
- `OFFLINE_THRESHOLD_SEC` - Offline threshold (default 30s)

## Architecture

```
collector.py (main loop)
  ├── get_enabled_devices() - Load from DB
  ├── poll_single_device() - Poll with backoff
  │   ├── poll_device() - eAPI client
  │   ├── update_redis_health() - Update Redis
  │   ├── create_event() - Write to Postgres
  │   └── publish_state/telemetry() - MQTT
  └── Concurrency control via semaphore
```

## Backoff Strategy

| Attempt | Delay (seconds) |
|---------|----------------|
| 1      | 10             |
| 2      | 20             |
| 3      | 40             |
| 4+     | 60 (capped)    |

## Status Determination

1. **Online**: Successful poll + last_seen within 30s
2. **Degraded**: 1-2 consecutive errors
3. **Offline**: 3+ consecutive errors OR last_seen > 30s

## Testing

Run collector tests:
```bash
make test-collector
# or
docker compose exec backend pytest tests/test_collector.py -v -s
```

## Next Steps

1. Add metrics/observability (Prometheus)
2. Add retry logic for transient errors
3. Add device-specific timeout configuration
4. Add batch event writing for performance
5. Add health check endpoint for collector itself
