# 腳本說明

## `subscribe_topics.sh`

MQTT topic 訂閱輔助腳本。

用法：
```bash
./scripts/subscribe_topics.sh state
./scripts/subscribe_topics.sh telemetry
./scripts/subscribe_topics.sh all
./scripts/subscribe_topics.sh <device_id>
```

## `seed_30_devices.py`（已淘汰）

此腳本已刻意淘汰，不再建議使用。

目前專案改用真實 vEOS 上線流程：
```bash
docker compose exec backend python scripts/bootstrap_real_veos.py
# 或
cd backend && python scripts/bootstrap_real_veos.py
```

快速驗證流程請見 `../docs/testing/quick-test.md`。
