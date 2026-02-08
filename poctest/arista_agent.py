#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

from collectors import run_cmds_raw
from dispatcher_mqtt import mqtt_connect, publish_raw
from config import COLLECTORS
from retention_sink import RetentionSink


# 透過環境變數讀取 Arista EOS eAPI 的連線資訊（沒設定就用預設值）
EOS_HOST = os.getenv("EOS_HOST", "192.168.xx.xx")
EOS_HTTPS = os.getenv("EOS_HTTPS", "true").lower() in ("1", "true", "yes")
EOS_USER = os.getenv("EOS_USER", "admin")
EOS_PASS = os.getenv("EOS_PASS", "arista")
EOS_VERIFY_TLS = os.getenv("EOS_VERIFY_TLS", "false").lower() in ("1", "true", "yes")
EOS_TIMEOUT = int(os.getenv("EOS_TIMEOUT", "10"))

# MQTT broker 連線設定
MQTT_CFG = {
    "host": os.getenv("MQTT_HOST", "127.0.0.1"),
    "port": int(os.getenv("MQTT_PORT", "1883")),
    "username": os.getenv("MQTT_USERNAME", ""),
    "password": os.getenv("MQTT_PASSWORD", ""),
    "client_id": f"arista-agent-{EOS_HOST}",
}

# QoS/retain 會影響訊息投遞方式（初學者可先維持預設）
QOS = int(os.getenv("MQTT_QOS", "1"))
RETAIN = os.getenv("MQTT_RETAIN", "false").lower() in ("1", "true", "yes")

# --- Retention settings ---
# 本地保存原始證據（raw/raw_ref）的設定
RETENTION_ENABLED = os.getenv("RETENTION_ENABLED", "true").lower() in ("1", "true", "yes")
RETENTION_BASE_DIR = os.getenv("RETENTION_BASE_DIR", ".")
# default: only keep IF_STATUS evidence unless you set "*" or add more collectors
RETENTION_TARGETS = os.getenv("RETENTION_TARGETS", "interfaces-status")
RETENTION_TARGET_SET = {x.strip() for x in RETENTION_TARGETS.split(",") if x.strip()}
RETENTION_LOG_PATH = os.getenv("RETENTION_LOG_PATH", "")  # optional override


def main():
    # 建立 MQTT 連線（程式會常駐）
    mqtt_client = mqtt_connect(MQTT_CFG)

    # 建立本地保存器（寫 raw/raw_ref 及 log）
    sink = RetentionSink(
        base_dir=RETENTION_BASE_DIR,
        enabled=RETENTION_ENABLED,
        targets=RETENTION_TARGET_SET if RETENTION_TARGET_SET else None,
        log_jsonl_path=RETENTION_LOG_PATH or None,
    )

    # last_run：記錄每個 collector 上次執行時間，用來控制輪詢頻率
    last_run = {c["name"]: 0.0 for c in COLLECTORS}

    print("[INFO] Arista raw eAPI agent started")
    print(f"[INFO] Retention enabled={RETENTION_ENABLED}, targets={sorted(list(RETENTION_TARGET_SET))}")

    while True:
        now = time.time()

        for c in COLLECTORS:
            name = c["name"]
            interval = float(c["interval"])

            # 還沒到輪詢時間就跳過
            if now - last_run[name] < interval:
                continue

            # Reserve this run slot immediately -> keeps fixed periodic schedule even when failure happens
            # 先把「本輪已執行」記下來，避免失敗時造成輪詢節奏亂掉
            last_run[name] = now

            cmd_list = c.get("cmds", [])
            topic = c.get("topic", "")
            ts = int(now)

            # defaults for logging
            eapi_ok = False
            mqtt_ok = False
            retention_ok = False
            raw_file = None
            ref_file = None
            err_stage = None
            err_msg = None

            try:
                # 1) 呼叫 eAPI 執行 CLI 指令
                result = run_cmds_raw(
                    host=EOS_HOST,
                    https=EOS_HTTPS,
                    user=EOS_USER,
                    password=EOS_PASS,
                    cmds=cmd_list,
                    fmt=c["format"],
                    verify_tls=EOS_VERIFY_TLS,
                    timeout=EOS_TIMEOUT,
                )
                eapi_ok = True

                # 2) 組成要送到 MQTT 的 payload
                payload = {
                    "device": EOS_HOST,
                    "collector": name,
                    "cmds": cmd_list,
                    "format": c["format"],
                    "raw": result,
                    "ts": ts,
                }

                # 1) Persist raw evidence (must not block)
                # 先把 raw 保存到本地（失敗也不能阻塞主流程）
                pr = sink.persist(topic=topic, payload=payload)
                if pr.get("ok") and not pr.get("skipped"):
                    retention_ok = True
                    raw_file = pr.get("raw_file")
                    ref_file = pr.get("ref_file")
                elif pr.get("ok") and pr.get("skipped"):
                    # skipped is not a failure; just not in target set
                    retention_ok = True
                else:
                    retention_ok = False
                    err_stage = "retention"
                    err_msg = pr.get("error", "unknown retention error")

                # 2) Publish MQTT (must not block next rounds)
                # 再發布到 MQTT（錯誤只記錄，不中斷）
                try:
                    publish_raw(
                        mqtt_client,
                        topic,
                        payload,
                        qos=QOS,
                        retain=RETAIN,
                    )
                    mqtt_ok = True
                except Exception as e:
                    mqtt_ok = False
                    err_stage = "mqtt"
                    err_msg = str(e)

                print(f"[INFO] Run {name}: eapi_ok={eapi_ok} retention_ok={retention_ok} mqtt_ok={mqtt_ok}")

            except Exception as e:
                # eAPI failure: record but do not stop future polling
                # eAPI 本身失敗：記錄錯誤，不影響下一輪
                eapi_ok = False
                err_stage = "eapi"
                err_msg = str(e)
                print(f"[ERROR] {name}: {err_msg}")

            # 3) Collector log (10-min evidence)
            # 3) 寫一筆 JSONL 事件紀錄（供後續稽核/查證）
            sink.log_event(
                {
                    "device": EOS_HOST,
                    "collector": name,
                    "cmds": cmd_list,
                    "topic": topic,
                    "ts": ts,
                    "eapi_ok": eapi_ok,
                    "retention_ok": retention_ok,
                    "mqtt_ok": mqtt_ok,
                    "raw_file": raw_file,
                    "ref_file": ref_file,
                    "error_stage": err_stage,
                    "error": err_msg,
                }
            )

        # 簡單節流，避免 CPU 100%
        time.sleep(1)


if __name__ == "__main__":
    main()
