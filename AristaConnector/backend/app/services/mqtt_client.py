"""
MQTT client for publishing device state, telemetry, and optional poctest-compatible raw topics.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional, Dict, Any
from uuid import UUID

import paho.mqtt.client as mqtt

from app.services.collector_profile import (
    get_collector_name_for_command,
    get_raw_topic_for_command,
)

_mqtt_client: Optional[mqtt.Client] = None
_connected = False


def get_mqtt_config() -> dict[str, Any]:
    """Get MQTT configuration from environment variables."""
    return {
        "host": os.getenv("MQTT_HOST", os.getenv("MQTT_BROKER", "localhost")),
        "port": int(os.getenv("MQTT_PORT", "1883")),
        "tls": os.getenv("MQTT_TLS", "false").lower() == "true",
        "username": os.getenv("MQTT_USERNAME"),
        "password": os.getenv("MQTT_PASSWORD"),
        "raw_compat_enabled": os.getenv("MQTT_RAW_COMPAT_ENABLED", "false").lower() == "true",
    }


def get_mqtt_client() -> mqtt.Client:
    """Get or create MQTT client."""
    global _mqtt_client, _connected

    if _mqtt_client is None:
        config = get_mqtt_config()
        client_id = f"arista-collector-{os.getpid()}"
        _mqtt_client = mqtt.Client(client_id=client_id)

        if config["username"] and config["password"]:
            _mqtt_client.username_pw_set(config["username"], config["password"])

        if config["tls"]:
            _mqtt_client.tls_set()

        def on_connect(client, userdata, flags, rc):  # noqa: ANN001
            global _connected
            if rc == 0:
                _connected = True
                print(f"MQTT connected to {config['host']}:{config['port']}")
            else:
                _connected = False
                print(f"MQTT connection failed with code {rc}")

        def on_disconnect(client, userdata, rc):  # noqa: ANN001
            global _connected
            _connected = False
            print(f"MQTT disconnected (rc={rc})")

        _mqtt_client.on_connect = on_connect
        _mqtt_client.on_disconnect = on_disconnect

        try:
            _mqtt_client.connect(config["host"], config["port"], 60)
            _mqtt_client.loop_start()
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to connect to MQTT broker: {exc}")
            _connected = False

    return _mqtt_client


def create_envelope(
    device_id: UUID,
    hostname: Optional[str],
    ip: str,
    collector: str,
    command: str,
    duration_ms: Optional[float],
    status: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create normalized MQTT message envelope."""
    return {
        "ts": int(time.time()),
        "tenant": "default",
        "device": {
            "id": str(device_id),
            "hostname": hostname or "",
            "ip": ip,
        },
        "source": {
            "type": "arista_eapi",
            "collector": collector,
            "command": command,
            "duration_ms": duration_ms,
        },
        "status": status,
        "data": data or {},
    }


def publish_state(
    device_id: UUID,
    hostname: Optional[str],
    ip: str,
    status: str,
    data: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """Publish device state (retained=true, QoS=1)."""
    client = get_mqtt_client()
    if not _connected:
        return

    topic = f"arista/default/{device_id}/state"
    envelope = create_envelope(
        device_id=device_id,
        hostname=hostname,
        ip=ip,
        collector="state",
        command="state",
        duration_ms=duration_ms,
        status=status,
        data=data,
    )

    try:
        client.publish(topic, json.dumps(envelope), qos=1, retain=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to publish state to MQTT: {exc}")


def publish_telemetry(
    device_id: UUID,
    hostname: Optional[str],
    ip: str,
    collector: str,
    command: str,
    data: Dict[str, Any],
    duration_ms: Optional[float] = None,
    status: str = "ok",
) -> None:
    """Publish device telemetry (retained=false, QoS=1)."""
    client = get_mqtt_client()
    if not _connected:
        return

    topic = f"arista/default/{device_id}/telemetry/{collector}"
    envelope = create_envelope(
        device_id=device_id,
        hostname=hostname,
        ip=ip,
        collector=collector,
        command=command,
        duration_ms=duration_ms,
        status=status,
        data=data,
    )

    try:
        client.publish(topic, json.dumps(envelope), qos=1, retain=False)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to publish telemetry to MQTT: {exc}")


def publish_raw_compat(
    *,
    device_identifier: str,
    command: str,
    raw_result: Any,
    ts: int | None = None,
) -> None:
    """
    Publish poctest-compatible raw payload to network/arista/raw/* topics when enabled.
    """
    config = get_mqtt_config()
    if not config["raw_compat_enabled"]:
        return

    collector = get_collector_name_for_command(command)
    topic = get_raw_topic_for_command(command)
    payload = {
        "device": device_identifier,
        "collector": collector,
        "cmds": [command],
        "format": "json",
        "raw": [raw_result],
        "ts": ts if ts is not None else int(time.time()),
    }

    client = get_mqtt_client()
    if not _connected:
        return

    try:
        client.publish(topic, json.dumps(payload), qos=1, retain=False)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to publish raw compat payload to MQTT: {exc}")


def get_collector_name(command: str) -> str:
    """Map eAPI command to collector name via shared profile."""
    return get_collector_name_for_command(command)
