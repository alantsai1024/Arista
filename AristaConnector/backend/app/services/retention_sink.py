"""
Retention sink for persisting raw eAPI evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _sha256_bytes(raw: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(raw)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class RetentionSink:
    """
    Persist raw collector output and metadata reference files.
    """

    def __init__(
        self,
        base_dir: str = "./runtime",
        enabled: bool = True,
        targets: set[str] | None = None,
        log_jsonl_path: str | None = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.enabled = enabled
        self.targets = targets

        self.raw_dir = self.base_dir / "raw"
        self.ref_dir = self.base_dir / "raw_ref"
        self.log_path = Path(log_jsonl_path).resolve() if log_jsonl_path else (self.ref_dir / "collector.log")

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ref_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _should_persist(self, collector: str) -> bool:
        if not self.enabled:
            return False
        if not self.targets:
            return True
        return collector in self.targets or "*" in self.targets

    def persist(self, *, topic: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Persist a raw payload and matching metadata reference.

        Returns:
          - success: {"ok": True, "skipped": bool, ...}
          - error: {"ok": False, "error": "..."}
        """
        try:
            collector = str(payload.get("collector", "unknown"))
            ts = int(payload.get("ts") or time.time())

            if not self._should_persist(collector):
                return {"ok": True, "skipped": True}

            raw_obj = payload.get("raw")
            raw_json = json.dumps(raw_obj, ensure_ascii=False, indent=2)
            raw_bytes = raw_json.encode("utf-8")
            raw_sha256 = _sha256_bytes(raw_bytes)

            raw_file = self.raw_dir / f"{collector}_{ts}.json"
            _atomic_write_text(raw_file, raw_json)

            ref_obj = {
                "device": payload.get("device"),
                "collector": collector,
                "cmds": payload.get("cmds"),
                "format": payload.get("format"),
                "ts": ts,
                "ts_iso": _iso_utc(ts),
                "topic": topic,
                "raw_file": str(raw_file.relative_to(self.base_dir)),
                "raw_sha256": raw_sha256,
            }
            ref_file = self.ref_dir / f"{collector}_{ts}.json"
            _atomic_write_text(ref_file, json.dumps(ref_obj, ensure_ascii=False, indent=2))

            return {
                "ok": True,
                "skipped": False,
                "raw_file": str(raw_file),
                "ref_file": str(ref_file),
                "raw_sha256": raw_sha256,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def log_event(self, event: dict[str, Any]) -> None:
        """
        Append one JSONL line. Errors are swallowed by design.
        """
        try:
            ts = int(event.get("ts") or time.time())
            event.setdefault("ts", ts)
            event.setdefault("ts_iso", _iso_utc(ts))
            line = json.dumps(event, ensure_ascii=False)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:  # noqa: BLE001
            # Intentionally non-blocking.
            pass
