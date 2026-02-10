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
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
import urllib3

# Ensure `/app` (project root) is importable when executing this file directly.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.device_identity import (
    compute_identity_fingerprint,
    normalize_serial_number,
    normalize_system_mac,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_TARGETS = "192.168.56.2,192.168.56.3,192.168.56.4"
LEGACY_ENV_VARS = ("VEOS_USERNAME", "VEOS_PASSWORD")
LEGACY_CLI_FLAGS = ("--username", "--password")
CredentialsByIP = dict[str, dict[str, str]]


class ConfigError(ValueError):
    """Raised when bootstrap configuration is invalid."""


def parse_targets(raw: str) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for token in raw.split(","):
        ip = token.strip()
        if not ip or ip in seen:
            continue
        seen.add(ip)
        targets.append(ip)
    return targets


def has_legacy_cli_args(argv: list[str]) -> bool:
    for arg in argv:
        for flag in LEGACY_CLI_FLAGS:
            if arg == flag or arg.startswith(f"{flag}="):
                return True
    return False


def ensure_legacy_env_vars_not_set() -> None:
    blocked = [name for name in LEGACY_ENV_VARS if name in os.environ]
    if blocked:
        blocked_str = ", ".join(blocked)
        raise ConfigError(
            f"Legacy env vars are not supported: {blocked_str}. "
            "Use VEOS_CREDENTIALS_FILE with per-target credentials JSON."
        )


def load_credentials_file(path: str) -> CredentialsByIP:
    if not path:
        raise ConfigError("Missing credentials file. Set VEOS_CREDENTIALS_FILE or pass --credentials-file.")

    credentials_path = Path(path)
    try:
        raw = credentials_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"Credentials file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"Failed to read credentials file {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Invalid credentials JSON in {path}: {exc.msg} (line {exc.lineno}, col {exc.colno})"
        ) from exc

    if not isinstance(data, dict):
        raise ConfigError("Credentials JSON root must be an object: {\"<ip>\": {\"username\": \"...\", \"password\": \"...\"}}")

    credentials: CredentialsByIP = {}
    for raw_ip, raw_cred in data.items():
        if not isinstance(raw_ip, str) or not raw_ip.strip():
            raise ConfigError("Credentials JSON keys must be non-empty IP strings.")
        ip = raw_ip.strip()

        if not isinstance(raw_cred, dict):
            raise ConfigError(f"Credential entry for {ip} must be an object.")

        username = raw_cred.get("username")
        password = raw_cred.get("password")

        if not isinstance(username, str) or not username.strip():
            raise ConfigError(f"Credential entry for {ip} must include non-empty string 'username'.")
        if not isinstance(password, str) or password == "":
            raise ConfigError(f"Credential entry for {ip} must include non-empty string 'password'.")

        credentials[ip] = {"username": username.strip(), "password": password}

    return credentials


def validate_credentials_targets(targets: list[str], credentials_map: CredentialsByIP) -> None:
    target_set = set(targets)
    credentials_set = set(credentials_map.keys())

    missing = sorted(target_set - credentials_set)
    extra = sorted(credentials_set - target_set)

    errors: list[str] = []
    if missing:
        errors.append(f"Missing credentials for targets: {', '.join(missing)}")
    if extra:
        errors.append(f"Credentials file has extra entries not in VEOS_TARGETS: {', '.join(extra)}")

    if errors:
        raise ConfigError("; ".join(errors))


def get_credentials_for_target(ip: str, credentials_map: CredentialsByIP) -> tuple[str, str]:
    cred = credentials_map.get(ip)
    if cred is None:
        raise ConfigError(f"No credentials found for target {ip}")
    return cred["username"], cred["password"]


def build_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Bootstrap real vEOS devices into AristaConnector")

    parser.add_argument(
        "--api-url",
        default=os.getenv("ARISTA_API_URL", "http://localhost:8000"),
        help="Backend API base URL",
    )
    parser.add_argument(
        "--targets",
        default=os.getenv("VEOS_TARGETS", DEFAULT_TARGETS),
        help="Comma separated list of target device IPs",
    )
    parser.add_argument(
        "--credentials-file",
        default=os.getenv("VEOS_CREDENTIALS_FILE", ""),
        help="Path to credentials JSON file: {\"<ip>\": {\"username\": \"...\", \"password\": \"...\"}}",
    )
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
    parser.add_argument(
        "--probe-failure-policy",
        choices=["continue", "abort"],
        default="continue",
        help="Behavior when one or more target probes fail",
    )
    if has_legacy_cli_args(argv):
        parser.error(
            "Legacy CLI args --username/--password are not supported. "
            "Use --credentials-file with per-target credentials JSON."
        )
    return parser.parse_args(argv)


def _extract_show_version_identity(show_version: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    serial = show_version.get("serialNumber") or show_version.get("serial_number") or show_version.get("serial")
    system_mac = (
        show_version.get("systemMacAddress")
        or show_version.get("system_mac_address")
        or show_version.get("systemMac")
        or show_version.get("macAddress")
        or show_version.get("mac")
    )
    normalized_serial = normalize_serial_number(serial) if isinstance(serial, str) else None
    normalized_mac = normalize_system_mac(system_mac) if isinstance(system_mac, str) else None
    fingerprint = compute_identity_fingerprint(normalized_serial, normalized_mac)
    return normalized_serial, normalized_mac, fingerprint


def eapi_probe(
    ip: str,
    port: int,
    username: str,
    password: str,
    timeout: float = 10.0,
) -> tuple[bool, str | None, str | None, dict[str, str | None], str]:
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {"version": 1, "cmds": ["show hostname", "show version"], "format": "json"},
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
            return False, None, None, {"serial_number": None, "system_mac": None}, f"HTTP {resp.status_code}: {resp.text}"

        data = resp.json()
        if "error" in data:
            return False, None, None, {"serial_number": None, "system_mac": None}, str(data["error"])

        results = data.get("result", [])
        if len(results) < 2:
            return False, None, None, {"serial_number": None, "system_mac": None}, "empty result"

        hostname = results[0].get("hostname")
        show_version = results[1] if isinstance(results[1], dict) else {}
        serial_number, system_mac, fingerprint = _extract_show_version_identity(show_version)
        return True, hostname, fingerprint, {"serial_number": serial_number, "system_mac": system_mac}, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, None, None, {"serial_number": None, "system_mac": None}, str(exc)


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
    fingerprints_by_ip: dict[str, str],
    *,
    targets: list[str],
    credentials_by_ip: CredentialsByIP,
    port: int,
    interval_sec: int,
) -> list[dict[str, Any]]:
    upserted: list[dict[str, Any]] = []
    for ip in targets:
        username, password = get_credentials_for_target(ip, credentials_by_ip)
        hostname = hostnames_by_ip.get(ip, ip)
        payload = {
            "hostname": hostname,
            "ip": ip,
            "port": port,
            "username": username,
            "password": password,
            "interval_sec": interval_sec,
            "enabled": True,
            "identity_mode": "auto",
            "expected_identity_fingerprint": fingerprints_by_ip.get(ip),
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


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        ensure_legacy_env_vars_not_set()
        targets = parse_targets(args.targets)
        if not targets:
            raise ConfigError("No target IPs configured. Set VEOS_TARGETS.")

        credentials_by_ip = load_credentials_file(args.credentials_file)
        validate_credentials_targets(targets, credentials_by_ip)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print("=== Real vEOS Bootstrap ===")
    print(f"API URL: {args.api_url}")
    print(f"Targets: {', '.join(targets)}")
    print(f"Target count: {len(targets)}")
    print(f"Credentials file: {args.credentials_file}")
    print("")

    hostnames_by_ip: dict[str, str] = {}
    fingerprints_by_ip: dict[str, str] = {}
    probe_successes: list[tuple[str, str]] = []
    probe_failures: list[tuple[str, str]] = []
    for ip in targets:
        username, password = get_credentials_for_target(ip, credentials_by_ip)
        ok, hostname, fingerprint, identity_meta, message = eapi_probe(ip, args.port, username, password)
        if ok:
            resolved_hostname = hostname or ip
            hostnames_by_ip[ip] = resolved_hostname
            if fingerprint:
                fingerprints_by_ip[ip] = fingerprint
            probe_successes.append((ip, resolved_hostname))
            print(
                f"[OK] eAPI probe {ip} -> hostname={resolved_hostname} "
                f"fingerprint={'set' if fingerprint else 'missing'} "
                f"serial={identity_meta.get('serial_number') or '-'} "
                f"mac={identity_meta.get('system_mac') or '-'}"
            )
        else:
            hostnames_by_ip[ip] = ip
            probe_failures.append((ip, message))
            print(f"[FAIL] eAPI probe {ip} -> {message}")

    if probe_failures:
        failed_ips = ", ".join(ip for ip, _ in probe_failures)
        print(f"Probe failures ({len(probe_failures)}): {failed_ips}")
        if args.probe_failure_policy == "abort":
            print("Abort: one or more target devices failed eAPI probe (policy=abort).")
            return 1
        print("Continue: failed probes will still be upserted using IP as hostname fallback.")

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
        fingerprints_by_ip,
        targets=targets,
        credentials_by_ip=credentials_by_ip,
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

    print("")
    print("Probe summary:")
    print(f"- Success: {len(probe_successes)}")
    if probe_successes:
        for ip, hostname in probe_successes:
            print(f"  * {ip} -> {hostname}")
    print(f"- Failed: {len(probe_failures)}")
    if probe_failures:
        for ip, reason in probe_failures:
            print(f"  * {ip} -> {reason}")
        print("WARNING: Some targets were unreachable, but bootstrap continued (policy=continue).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
