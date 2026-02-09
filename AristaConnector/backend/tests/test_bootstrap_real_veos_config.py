import json

import pytest

from scripts import bootstrap_real_veos as bootstrap


def write_credentials_file(tmp_path, payload: dict) -> str:
    path = tmp_path / "veos_credentials.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_parse_targets_handles_blank_and_duplicates():
    targets = bootstrap.parse_targets(" 192.168.56.2, ,192.168.56.3,192.168.56.2 ")
    assert targets == ["192.168.56.2", "192.168.56.3"]


def test_parse_targets_empty():
    assert bootstrap.parse_targets(" , , ") == []


def test_load_credentials_file_success(tmp_path):
    path = write_credentials_file(
        tmp_path,
        {
            "192.168.56.2": {"username": "admin", "password": "pw1"},
            "192.168.56.3": {"username": "ops", "password": "pw2"},
        },
    )

    loaded = bootstrap.load_credentials_file(path)
    assert loaded["192.168.56.2"]["username"] == "admin"
    assert loaded["192.168.56.3"]["password"] == "pw2"


def test_load_credentials_file_not_found():
    with pytest.raises(bootstrap.ConfigError, match="not found"):
        bootstrap.load_credentials_file("C:/missing/veos_credentials.json")


def test_load_credentials_file_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(bootstrap.ConfigError, match="Invalid credentials JSON"):
        bootstrap.load_credentials_file(str(bad_file))


def test_load_credentials_file_missing_schema_key(tmp_path):
    path = write_credentials_file(
        tmp_path,
        {
            "192.168.56.2": {"password": "pw1"},
        },
    )

    with pytest.raises(bootstrap.ConfigError, match="username"):
        bootstrap.load_credentials_file(path)


def test_validate_credentials_targets_missing_target():
    targets = ["192.168.56.2", "192.168.56.3"]
    creds = {"192.168.56.2": {"username": "admin", "password": "pw1"}}

    with pytest.raises(bootstrap.ConfigError, match="Missing credentials"):
        bootstrap.validate_credentials_targets(targets, creds)


def test_validate_credentials_targets_extra_target():
    targets = ["192.168.56.2"]
    creds = {
        "192.168.56.2": {"username": "admin", "password": "pw1"},
        "192.168.56.3": {"username": "ops", "password": "pw2"},
    }

    with pytest.raises(bootstrap.ConfigError, match="extra entries"):
        bootstrap.validate_credentials_targets(targets, creds)


def test_validate_credentials_targets_all_matched():
    targets = ["192.168.56.2", "192.168.56.3"]
    creds = {
        "192.168.56.2": {"username": "admin", "password": "pw1"},
        "192.168.56.3": {"username": "ops", "password": "pw2"},
    }

    bootstrap.validate_credentials_targets(targets, creds)


def test_main_rejects_legacy_env_vars(monkeypatch, tmp_path):
    path = write_credentials_file(
        tmp_path,
        {"192.168.56.2": {"username": "admin", "password": "pw1"}},
    )
    monkeypatch.setenv("VEOS_TARGETS", "192.168.56.2")
    monkeypatch.setenv("VEOS_CREDENTIALS_FILE", path)
    monkeypatch.setenv("VEOS_USERNAME", "legacy-user")

    rc = bootstrap.main([])
    assert rc == 2


def test_main_rejects_legacy_cli_args():
    rc = bootstrap.main(["--username", "admin"])
    assert rc == 2


def test_main_uses_per_target_credentials_for_probe_and_upsert(monkeypatch, tmp_path):
    creds_payload = {
        "192.168.56.2": {"username": "admin", "password": "pw1"},
        "192.168.56.3": {"username": "ops", "password": "pw2"},
    }
    path = write_credentials_file(tmp_path, creds_payload)

    probe_calls: list[tuple[str, str, str]] = []
    upsert_seen: dict = {}

    def fake_probe(ip, port, username, password, timeout=10.0):
        probe_calls.append((ip, username, password))
        return True, f"host-{ip}", "ok"

    def fake_api_get_devices(_api_url):
        return []

    def fake_upsert_targets(_api_url, _existing_by_ip, _hostnames_by_ip, **kwargs):
        upsert_seen["credentials_by_ip"] = kwargs["credentials_by_ip"]
        return []

    monkeypatch.setattr(bootstrap, "eapi_probe", fake_probe)
    monkeypatch.setattr(bootstrap, "api_get_devices", fake_api_get_devices)
    monkeypatch.setattr(bootstrap, "upsert_targets", fake_upsert_targets)

    rc = bootstrap.main(
        [
            "--api-url",
            "http://localhost:8000",
            "--targets",
            "192.168.56.2,192.168.56.3",
            "--credentials-file",
            path,
            "--non-interactive-action",
            "keep",
        ]
    )

    assert rc == 0
    assert probe_calls == [
        ("192.168.56.2", "admin", "pw1"),
        ("192.168.56.3", "ops", "pw2"),
    ]
    assert upsert_seen["credentials_by_ip"] == creds_payload


def test_main_probe_failure_aborts_before_upsert(monkeypatch, tmp_path):
    path = write_credentials_file(
        tmp_path,
        {
            "192.168.56.2": {"username": "admin", "password": "pw1"},
            "192.168.56.3": {"username": "ops", "password": "pw2"},
        },
    )

    def fake_probe(ip, port, username, password, timeout=10.0):
        if ip == "192.168.56.3":
            return False, None, "auth failed"
        return True, f"host-{ip}", "ok"

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Should not call API cleanup/upsert when probe fails")

    upsert_called = {"value": False}

    def fake_upsert(*_args, **_kwargs):
        upsert_called["value"] = True
        return []

    monkeypatch.setattr(bootstrap, "eapi_probe", fake_probe)
    monkeypatch.setattr(bootstrap, "api_get_devices", fail_if_called)
    monkeypatch.setattr(bootstrap, "upsert_targets", fake_upsert)

    rc = bootstrap.main(
        [
            "--targets",
            "192.168.56.2,192.168.56.3",
            "--credentials-file",
            path,
        ]
    )

    assert rc == 1
    assert upsert_called["value"] is False
