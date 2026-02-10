# 專案能力與現況說明

本文件用「高層功能」與「目前可達成」兩段，讓你快速了解這個專案能做什麼、現在做到哪裡。

## 專案能做什麼
- 管理 Arista vEOS 設備清單，包含新增、查詢、更新與狀態查看。
- 以固定間隔輪詢設備 eAPI，取得系統時間、主機名稱、介面狀態等資訊。
- 以 `show version` 身份指紋（serial/mac）驗證設備身份，避免同 IP/同 hostname 誤判。
- 追蹤設備健康狀態與延遲，並提供機群健康概覽。
- 將輪詢結果保存為事件紀錄，方便查詢與統計。
- 透過 MQTT 發布設備狀態與遙測資料，提供即時訂閱來源。
- 搭配前端儀表板，提供基本的監控與可視化入口。
- 透過 Docker Compose 一鍵啟動後端、資料庫、Redis、MQTT、Collector 與前端。

## 目前可達成什麼
- 可透過 API 建立、列出、取得、更新設備資料。
- 可設定設備身份模式（`identity_mode=auto|manual`）與預期指紋（`expected_identity_fingerprint`）。
- 可對單一設備進行 eAPI 連線測試。
- Collector 可依設備 `interval_sec` 進行輪詢，並支援並發與退避。
- 當輪詢成功但身份比對失敗時，會標記 `ip_conflict` 並停止 telemetry/raw 發布。
- Redis 會保存 `last_seen`、`status`、`latency_ms` 等健康資訊。
- 系統會將輪詢成功/失敗寫入 `events`，可查最近事件或統計。
- MQTT 可發佈 state 與 telemetry 主題，符合既定 envelope 格式。
- `GET /health/fleet` 可回傳機群健康摘要與高延遲設備。
- 本地與部署腳本可啟動完整服務組合（PostgreSQL/Redis/MQTT/Backend/Collector/Frontend）。

## 已知不包含 / 非重點範圍
- 目前未提供身份驗證與權限控管。
- 密碼僅以 base64 儲存，尚未做正式加密。
- eAPI 在開發環境預設忽略 SSL 驗證。
- 尚未提供告警通知、報表匯出或多租戶管理功能。

## 與 Arista 路由器整合（實際步驟）
以下是「真的要接到 Arista 路由器」時的實際流程重點，盡量用最簡單的語言說明。

1. 確認設備已開啟 eAPI，且可用 HTTPS 呼叫 `/command-api`。
2. 確保後端/Collector 可以連到設備的管理 IP 與 port（預設 443）。
3. 準備一組可用的帳號密碼（需有執行 `show` 指令的權限）。
4. 在專案中新增設備（可用 API 或前端介面）。
5. 先測試連線，確保 eAPI 可回 `show hostname` 的結果。
6. 啟動 Collector，開始依 `interval_sec` 自動輪詢設備。
7. 在 API 查狀態/事件，或在 MQTT 訂閱 topic 檢查資料是否進來。

### 你會用到的 API（最常見）
建立設備（HTTP JSON 範例）：
```json
POST /devices
{
  "hostname": "leaf-01",
  "ip": "10.0.0.10",
  "port": 443,
  "username": "admin",
  "password": "your_password",
  "identity_mode": "auto",
  "expected_identity_fingerprint": "<optional sha256 hex>",
  "interval_sec": 10,
  "enabled": true
}
```

測試連線：
```json
POST /devices/{device_id}/test-connection
```

查設備狀態：
```json
GET /devices/{device_id}/status
```

### 目前輪詢的指令
Collector 目前固定輪詢以下 eAPI 指令：
- `show clock`
- `show hostname`
- `show interfaces status`
- `show version`

如需新增指令，可修改：
- `backend/app/services/collector_client.py` 的 `EAPI_COMMANDS`
- `backend/app/services/mqtt_client.py` 的 `get_collector_name()` 對應名稱

### 常見整合問題（快速排查）
1. 連線逾時或拒絕：檢查設備管理網路、ACL、防火牆與 port 是否開放。
2. 驗證失敗：確認帳號密碼正確，且權限足以執行 `show` 指令。
3. SSL 憑證問題：目前後端會忽略驗證（`verify=False`），正式環境請改用有效憑證或調整驗證策略。
4. 顯示 `ip_conflict`：代表連線可達但身份指紋不一致，常見於重複 IP 或克隆設備未重設 serial/mac。
