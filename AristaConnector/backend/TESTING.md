# 後端測試指南

## 執行測試

Docker：
```bash
docker compose exec backend pytest tests/ -v
```

本機：
```bash
cd backend
pytest tests/ -v
```

## 主要測試檔案

- `tests/test_devices_api.py`
  - 設備 CRUD
  - 含 `DELETE /devices/{id}` 測試
- `tests/test_connection.py`
  - `test-connection` 端點行為
- `tests/test_collector_client.py`
  - collector 指令設定含 `show version`
- `tests/test_retention_sink.py`
  - retention 寫入失敗不應阻斷主流程
- `tests/test_collector.py`
  - 小規模 mock collector 流程（3 台設備）
- `tests/test_mqtt.py`
  - MQTT envelope 與 collector 名稱映射

## 備註

- 目前主要驗收基準是「真實 vEOS 整合」，而非舊的 30 台假設備播種流程。
- 若要用真實設備驗證，請使用 `scripts/bootstrap_real_veos.py`，並搭配根目錄 `DEMO_TESTCASES.md`。

