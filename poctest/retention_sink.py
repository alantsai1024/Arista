#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set


def _iso_utc(ts: int) -> str:
    # 把 UNIX 時間戳轉成 UTC 的 ISO 格式字串
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _atomic_write_text(path: Path, text: str) -> None:
    # 原子寫入：先寫到 .tmp 再取代，避免中途斷電導致檔案損壞
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _sha256_bytes(b: bytes) -> str:
    # 計算 SHA256，用來做完整性驗證
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


class RetentionSink:
    """
    將原始證據保存到本地檔案：
      - raw/<collector>_<ts>.json        （只保存 raw 內容）
      - raw_ref/<collector>_<ts>.json    （metadata，指向 raw 檔）
      - raw_ref/collector.log            （JSONL 事件日誌，用於稽核）
    """

    def __init__(
        self,
        base_dir: str = ".",
        enabled: bool = True,
        targets: Optional[Set[str]] = None,
        log_jsonl_path: Optional[str] = None,
    ) -> None:
        # base_dir：保存檔案的根目錄
        self.base_dir = Path(base_dir).resolve()
        self.enabled = enabled
        # targets: 指定要保存哪些 collector，None 代表全部保存
        self.targets = targets

        self.raw_dir = self.base_dir / "raw"
        self.ref_dir = self.base_dir / "raw_ref"

        # Collector log: default -> raw_ref/collector.log
        self.log_path = Path(log_jsonl_path).resolve() if log_jsonl_path else (self.ref_dir / "collector.log")

        # 確保目錄存在
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ref_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _should_persist(self, collector: str) -> bool:
        # 判斷某個 collector 是否需要保存
        if not self.enabled:
            return False
        if not self.targets:
            return True
        return collector in self.targets or "*" in self.targets

    def persist(self, *, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        主要保存流程，回傳結果（成功/失敗與檔案資訊）。
        成功時：
          {ok: True, skipped: bool, raw_file: str, ref_file: str, raw_sha256: str}
        失敗時：
          {ok: False, error: str}
        """
        try:
            collector = str(payload.get("collector", "unknown"))
            ts = int(payload.get("ts") or time.time())

            if not self._should_persist(collector):
                return {"ok": True, "skipped": True}

            # raw 檔：只保存 payload["raw"]，符合「原始證據」的定義
            raw_obj = payload.get("raw", None)
            raw_json = json.dumps(raw_obj, ensure_ascii=False, indent=2)
            raw_bytes = raw_json.encode("utf-8")
            raw_sha256 = _sha256_bytes(raw_bytes)

            raw_file = self.raw_dir / f"{collector}_{ts}.json"
            _atomic_write_text(raw_file, raw_json)

            # raw_ref 檔：保存 metadata，指向 raw 檔
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
            ref_json = json.dumps(ref_obj, ensure_ascii=False, indent=2)
            ref_file = self.ref_dir / f"{collector}_{ts}.json"
            _atomic_write_text(ref_file, ref_json)

            return {
                "ok": True,
                "skipped": False,
                "raw_file": str(raw_file),
                "ref_file": str(ref_file),
                "raw_sha256": raw_sha256,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def log_event(self, event: Dict[str, Any]) -> None:
        """
        追加一行 JSONL 到 collector.log。
        注意：此函式不能拋錯到外層，避免影響輪詢。
        """
        try:
            ts = int(event.get("ts") or time.time())
            event.setdefault("ts", ts)
            event.setdefault("ts_iso", _iso_utc(ts))
            line = json.dumps(event, ensure_ascii=False)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # 吃掉錯誤，避免阻塞主流程
            pass
