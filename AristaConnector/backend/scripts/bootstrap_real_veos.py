#!/usr/bin/env python3
"""
Bootstrap script for real vEOS devices.

Flow:
1) Probe target devices via eAPI show hostname.
2) Fetch existing devices from API.
3) Interactively cleanup non-target devices (delete/disable/keep).
4) Upsert target devices.
5) Test connection for each target device.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_targets(raw: str) -> list[str]:
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap real vEOS devices into AristaConnector")
    parser.add_argument(
        "--api-url",
        default=os.getenv("ARISTA_API_URL", "http://localhost:8000"),
        help="Backend API base URL",
    )
    parser.add_argument(
        "--targets",
        default=os.getenv("VEOS_TARGETS", "192.168.56.2,192.168.56.3,192.168.56.4"),
        help="Comma separated list of target device IPs",
    )
    parser.add_argument("--username", default=os.getenv("VEOS_USERNAME", "admin"), help="eAPI username")
    parser.add_argument("--password", default=os.getenv("VEOS_PASSWORD", "0000"), help="eAPI password")
    parser.add_argument("--port", type=int, default=int(os.getenv("VEOS_PORT", "443")), help="eAPI port")
    parser.add_argument(
        "--interval-sec",
        type=int,
        default=int(os.getenv("VEOS_INTERVAL_SEC", "10")),
        help="Polling interval",
    )
    parser.add_argument(
        "--non-interactive-action",
        choices=["keep", "disable", "delete"],
        default=None,
        help="When set, cleanup is non-interactive for non-target devices",
    )
    return parser.parse_args()


def eapi_probe(ip: str, port: int, username: str, password: str, timeout: float = 10.0) -> tuple[bool, str | None, str]:
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {"version": 1, "cmds": ["show hostname"], "format": "json"},
        "id": "1",
    }

    try:
        resp = requests.post(
            f"https://{ip}:{port}/command-api",
            json=payload,
            auth=(username, password),
            verify=False,
            timeout=timeout,
        )
        if resp.status_code != 200:
            return False, None, f"HTTP {resp.status_code}: {resp.text}"

        data = resp.json()
        if "error" in data:
            return False, None, str(data["error"])

        results = data.get("result", [])
        if not results:
            return False, None, "empty result"

        hostname = results[0].get("hostname")
        return True, hostname, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def api_get_devices(api_url: str) -> list[dict[str, Any]]:
    resp = requests.get(f"{api_url}/devices", timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_create_device(api_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(f"{api_url}/devices", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_patch_device(api_url: str, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = requests.patch(f"{api_url}/devices/{device_id}", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_delete_device(api_url: str, device_id: str) -> None:
    resp = requests.delete(f"{api_url}/devices/{device_id}", timeout=10)
    resp.raise_for_status()


def api_test_connection(api_url: str, device_id: str) -> dict[str, Any]:
    resp = requests.post(f"{api_url}/devices/{device_id}/test-connection", timeout=10)
    resp.raise_for_status()
    return resp.json()


def cleanup_action(device: dict[str, Any], non_interactive_action: str | None) -> str:
    if non_interactive_action:
        return non_interactive_action

    if not sys.stdin.isatty():
        return "keep"

    prompt = (
        f"Device {device.get('hostname') or '-'} ({device['ip']}, id={device['id']}) "
        "[d]elete/[s]disable/[k]eep (default k): "
    )
    choice = input(prompt).strip().lower()
    if choice in ("d", "delete"):
        return "delete"
    if choice in ("s", "disable"):
        return "disable"
    return "keep"


def upsert_targets(
    api_url: str,
    existing_by_ip: dict[str, dict[str, Any]],
    hostnames_by_ip: dict[str, str],
    *,
    targets: list[str],
    username: str,
    password: str,
    port: int,
    interval_sec: int,
) -> list[dict[str, Any]]:
    upserted: list[dict[str, Any]] = []
    for ip in targets:
        hostname = hostnames_by_ip.get(ip, ip)
        payload = {
            "hostname": hostname,
            "ip": ip,
            "port": port,
            "username": username,
            "password": password,
            "interval_sec": interval_sec,
            "enabled": True,
        }

        existing = existing_by_ip.get(ip)
        if existing:
            updated = api_patch_device(api_url, existing["id"], payload)
            print(f"Updated target device: {hostname} ({ip}) id={updated['id']}")
            upserted.append(updated)
        else:
            created = api_create_device(api_url, payload)
            print(f"Created target device: {hostname} ({ip}) id={created['id']}")
            upserted.append(created)
    return upserted


def main() -> int:
    args = build_args()
    targets = parse_targets(args.targets)
    if not targets:
        print("No target IPs configured.")
        return 1

    print("=== Real vEOS Bootstrap ===")
    print(f"API URL: {args.api_url}")
    print(f"Targets: {', '.join(targets)}")
    print(f"Credentials: {args.username}/{'*' * len(args.password)}")
    print("")

    hostnames_by_ip: dict[str, str] = {}
    probe_failed = False
    for ip in targets:
        ok, hostname, message = eapi_probe(ip, args.port, args.username, args.password)
        if ok:
            hostnames_by_ip[ip] = hostname or ip
            print(f"[OK] eAPI probe {ip} -> hostname={hostnames_by_ip[ip]}")
        else:
            probe_failed = True
            print(f"[FAIL] eAPI probe {ip} -> {message}")

    if probe_failed:
        print("Abort: one or more target devices failed eAPI probe.")
        return 1

    try:
        devices = api_get_devices(args.api_url)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to fetch existing devices: {exc}")
        return 1

    target_set = set(targets)
    for device in devices:
        if device["ip"] in target_set:
            continue
        action = cleanup_action(device, args.non_interactive_action)
        try:
            if action == "delete":
                api_delete_device(args.api_url, device["id"])
                print(f"Deleted non-target device {device['id']} ({device['ip']})")
            elif action == "disable":
                api_patch_device(args.api_url, device["id"], {"enabled": False})
                print(f"Disabled non-target device {device['id']} ({device['ip']})")
            else:
                print(f"Kept non-target device {device['id']} ({device['ip']})")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed cleanup action for {device['id']} ({device['ip']}): {exc}")

    devices_after_cleanup = api_get_devices(args.api_url)
    existing_by_ip = {d["ip"]: d for d in devices_after_cleanup}

    upserted = upsert_targets(
        args.api_url,
        existing_by_ip,
        hostnames_by_ip,
        targets=targets,
        username=args.username,
        password=args.password,
        port=args.port,
        interval_sec=args.interval_sec,
    )

    print("")
    print("Connection test results:")
    for device in upserted:
        try:
            result = api_test_connection(args.api_url, device["id"])
            print(
                f"- {device.get('hostname') or '-'} ({device['ip']}): "
                f"success={result.get('success')} message={result.get('message')}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"- {device.get('hostname') or '-'} ({device['ip']}): FAILED to test ({exc})")

    print("")
    print("Final devices:")
    final_devices = api_get_devices(args.api_url)
    for d in final_devices:
        print(f"- {d.get('hostname') or '-'} {d['ip']} enabled={d['enabled']} id={d['id']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
