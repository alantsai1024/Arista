import json
import socket
import paho.mqtt.client as mqtt


def mqtt_connect(cfg):
    socket.getaddrinfo(cfg["host"], None)

    client = mqtt.Client(
        client_id=cfg["client_id"],
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    if cfg.get("username"):
        client.username_pw_set(cfg["username"], cfg.get("password"))

    client.connect(cfg["host"], cfg["port"], keepalive=60)
    client.loop_start()
    return client


def publish_raw(client, topic, payload, qos=1, retain=False):
    client.publish(
        topic,
        json.dumps(payload, ensure_ascii=False),
        qos=qos,
        retain=retain,
    )