# 文件目的與讀者

本文件為 `AristaConnector` 技術交接說明，針對：
- 舊版：`originarista/AristaConnector/`
- 新版：`AristaConnector/`

提供「功能作用介紹 + 新版優化解釋 + 導入建議 + 驗收方式」。  
適用讀者：
- 後端/前端工程師
- DevOps / 維運人員
- 專案交接與審查人員

> 注意：本文件以可交付差異為主，不將 `__pycache__`、`.pytest_cache`、`backend/runtime/raw*` 等執行產物視為功能變更。

---

# 系統整體作用（舊版與新版共通能力）

## 架構與資料流

```text
Arista eAPI Device
      |
      v
Collector (backend/collector.py)
      |------------------------------|
      v                              v
Redis (health/last_seen/latency)   PostgreSQL (devices/events)
      |
      v
MQTT broker
  ├─ arista/default/<device_id>/state
  ├─ arista/default/<device_id>/telemetry/<collector>
  └─ network/arista/raw/* (poctest 相容，開關控制)
      |
      v
Frontend (fleet / device detail)
```

## 主要模組職責

| 模組 | 主要職責 |
|---|---|
| `backend/` | API、資料模型、DAO、健康統計、eAPI 連線測試 |
| `backend/collector.py` | 輪詢設備、更新 Redis、寫入事件、發布 MQTT |
| `frontend/` | 機群視圖、設備詳情、狀態可視化 |
| `mqtt/` | Mosquitto 設定與 broker 服務 |
| `scripts/` | 快速驗證、topic 訂閱、bootstrap 協助 |

## 共通核心功能
- 設備 CRUD（`POST/GET/PATCH/DELETE /devices`）
- 單設備 eAPI 測試（`POST /devices/{id}/test-connection`）
- 週期輪詢與退避策略
- 事件寫入與查詢（`events`）
- Redis 健康狀態追蹤（`last_seen/status/latency_ms`）
- MQTT state/telemetry 發布
- poctest 相容 raw topic（`network/arista/raw/*`，由 `MQTT_RAW_COMPAT_ENABLED` 控制）

---

# 舊版詳細功能介紹

## 舊版定位
舊版（`originarista/AristaConnector`）可完成完整 Arista eAPI 採集鏈路，適合作為功能基準與回歸對照。

## 舊版運作重點

### 1) Collector 事件寫入方式
- `poll_single_device(...)` 直接使用主流程 session 寫入事件（`create_event(db=...)`）。
- 在並發輪詢場景下，事件寫入與輪詢流程共享 session，邏輯簡單但對 session 競用較敏感。

### 2) Fleet 畫面資料依賴
- `frontend/app/fleet/page.tsx` 主要依賴 `/health/fleet` 回傳的 `recent_stats`。
- 若後端 payload 欄位不完整，前端顯示可能退化（例如 events/latency 呈現依賴欄位存在）。

### 3) Compose 行為特性
- MQTT healthcheck 為較簡化測法。
- collector service 未設 `restart: unless-stopped`，故障恢復彈性較弱。

## 舊版可用能力與限制（工程觀點）

| 面向 | 舊版可用能力 | 可能限制 |
|---|---|---|
| 採集鏈路 | eAPI -> Redis/Postgres/MQTT 可運作 | 並發事件寫入穩定性較依賴單一 session 行為 |
| 前端可視化 | fleet 排行、狀態、延遲可展示 | 對 `/health/fleet` payload 完整性依賴較高 |
| 部署韌性 | 可 docker compose 啟動整套服務 | collector 非自動重啟策略 |
| 文件與上線 | 既有 README/QuickStart/Deploy 文檔 | 缺少獨立設備上線手冊與新版 device detail 路由對應說明 |

---

# 新版詳細功能介紹

## 新版定位
新版（`AristaConnector`）在保留舊版核心能力基礎上，補強「穩定性、相容性、可觀測性、導入可操作性」。

## 新版新增能力

### 1) 設備詳情頁（drill-down）
- 新增路由：`frontend/app/devices/[id]/page.tsx`
- 提供：
  - 設備基本資訊
  - 即時狀態與近期統計
  - 最近事件列表與 JSON 展開
  - 自動刷新（10 秒）

### 2) 設備上線操作文檔
- 新增：`ADD_DEVICES_GUIDE_ZH.md`
- 包含：
  - 單台/批次上線流程
  - Bootstrap 命令
  - API 與 MQTT 驗證
  - 常見故障排查與建議順序

## 新版維持能力（與舊版一致）
- poctest 相容 raw 發布邏輯保持可用
  - `backend/app/services/mqtt_client.py` 的 `publish_raw_compat()`
  - `backend/app/services/collector_profile.py` 的 topic mapping
  - `.env` 開關 `MQTT_RAW_COMPAT_ENABLED=true/false`
- retention 能力保持可用
  - `RETENTION_ENABLED`
  - `RETENTION_BASE_DIR`
  - `RETENTION_TARGETS`

---

# 新版優化總覽（摘要表）

## 版本證據摘要

| 指標 | 數值 | 說明 |
|---|---:|---|
| 新版追蹤檔案數 | 89 | 以 `git ls-files` 計算 `AristaConnector/*` |
| 舊版缺失檔案 | 2 | `ADD_DEVICES_GUIDE_ZH.md`、`frontend/app/devices/[id]/page.tsx` |
| 同路徑內容差異檔 | 5 | `collector.py`、`events.py`、`test_collector.py`、`docker-compose.yml`、`fleet/page.tsx` |
| 共同 Markdown 差異 | 0 | 同路徑 Markdown hash 無差異 |
| 僅新版新增 Markdown | 1 | `ADD_DEVICES_GUIDE_ZH.md` |

## 新版優化清單（摘要）

| 優化項 | 對應檔案 | 核心價值 |
|---|---|---|
| 併發事件寫入穩定性 | `backend/collector.py` | 降低 session 競用風險 |
| 併發回歸保障 | `backend/tests/test_collector.py` | 減少回歸時漏測併發場景 |
| 事件查詢簡化 | `backend/app/dao/events.py` | 降低不必要查詢開銷 |
| 部署韌性 | `docker-compose.yml` | collector 異常可自動重啟 |
| 前端容錯相容 | `frontend/app/fleet/page.tsx` | 舊 payload 下仍可穩定顯示 |
| 可觀測 drill-down | `frontend/app/devices/[id]/page.tsx` | 提升排障與追查效率 |
| 導入文檔化 | `ADD_DEVICES_GUIDE_ZH.md` | 降低上線操作門檻 |

---

# 新版優化明細（逐項前後對照）

## 改善原因（遇到的實際狀況）

1. 多設備並發輪詢時，事件寫入與輪詢共用同一 DB session，容易出現競用風險與事件漏寫疑慮。
2. 併發問題在單設備測試不明顯，先前缺少專門回歸案例，後續重構容易把問題帶回來。
3. 事件統計查詢在高事件量下有不必要的查詢成本，且程式可讀性偏低。
4. collector 進程異常退出時若未自動重啟，會造成輪詢中斷且不易第一時間察覺。
5. 舊版或過渡期 `/health/fleet` payload 可能缺 `recent_stats`，前端表格會出現欄位退化或顯示不一致。
6. 僅有 fleet 總覽時，排障要反覆切 API/日誌，缺少單設備 drill-down 入口。
7. 設備上線流程若靠零散命令，常發生操作順序錯誤、漏做驗證、交接不一致。

| 優化項 | 遇到的狀況（改善原因） | 舊版行為 | 新版行為 | 技術影響 | 業務/維運價值 | 注意事項 |
|---|---|---|---|---|---|---|
| Collector 事件寫入穩定性 | 多設備並發輪詢時，事件寫入與輪詢共用 session，存在競用與事件漏寫風險。 | `poll_single_device` 直接用主 session 寫事件 | 透過 `record_event` 使用隔離 session 寫入 | 併發輪詢下事件寫入更穩定，降低 session 競用 | 減少事件漏寫與觀測盲點 | 若回退舊行為，需重新評估併發下寫入可靠性 |
| 併發測試補強 | 併發 bug 在單機/單設備測試不易被捕捉，回歸時容易漏測。 | 缺少獨立併發事件寫入保障情境 | 新增/調整 `test_collector` 併發寫入驗證 | 測試能覆蓋隔離 session 設計 | 回歸風險更低 | CI 需保留此測試場景 |
| DAO 查詢簡化 | 事件量增加時，統計查詢存在不必要操作，影響查詢效率與維護可讀性。 | 事件統計查詢含不必要排序與多餘匯入 | 移除冗餘排序、清理匯入 | 查詢更聚焦、可讀性更高 | 維護成本降低 | 若未來改統計需求，需再定義排序語義 |
| Compose 韌性 | collector 異常退出後若未重啟，輪詢會中斷，維運需手動介入。 | collector 無 `restart` 策略；MQTT healthcheck 較簡化 | collector 增加 `restart: unless-stopped` 並調整 healthcheck | 容器恢復能力提升 | 線上穩定性與自癒性改善 | 仍需搭配監控告警避免靜默失敗 |
| Fleet payload 相容 | `/health/fleet` 在舊版或過渡期可能缺 `recent_stats`，導致前端欄位顯示退化。 | 主要依賴 `/health/fleet` 內含完整 `recent_stats` | 新增 `/devices/{id}/status` fallback 合併策略 | 前端對舊/不完整 payload 容錯提升 | 避免儀表板欄位退化 | 後端 payload 統一後可評估收斂 fallback |
| Device drill-down | 僅看 fleet 總覽時，無法快速定位單設備事件與異常脈絡。 | 無設備詳情頁 | 新增 `/devices/[id]` 詳情頁（事件、狀態、JSON） | 觀測路徑更完整（fleet -> detail） | 排障效率提升 | 需確保 `GET /devices/{id}/events`、`/status` 穩定 |
| 設備導入文檔 | 上線流程若靠口頭與零散命令，易發生漏步驟與交接品質不一致。 | 缺少專門上線流程文檔 | 新增 `ADD_DEVICES_GUIDE_ZH.md` | 導入流程標準化 | 新人上手與交接更快 | 文件需與 API/腳本變更同步更新 |

---

# 對外介面影響（API / 路由 / 相容性）

## API 影響
- 本次對照範圍內，未新增後端對外 REST endpoint。
- 主要變動為內部行為優化（collector 寫入策略、前端資料補償邏輯），非破壞性 API contract 變更。

## 路由影響
- 新版新增前端路由：`/devices/[id]`（設備詳情頁）。

## 相容性影響
- 新版 fleet 前端新增 fallback，能兼容較舊或不完整的 `/health/fleet` payload。
- poctest raw 相容輸出機制保持一致，透過 `MQTT_RAW_COMPAT_ENABLED` 啟用。

---

# 導入與遷移建議

## 建議採用策略
1. 以新版 `AristaConnector/` 作為主線版本。
2. 保留 `collector.py` 隔離 session 設計與對應測試。
3. 保留 fleet fallback，待後端 payload 完全穩定後再評估是否收斂。
4. 將 `ADD_DEVICES_GUIDE_ZH.md` 納入正式 onboarding 文件流程。

## poctest 相容導入步驟
1. 設定 `.env`：
   - `MQTT_RAW_COMPAT_ENABLED=true`
   - `RETENTION_ENABLED=true`
   - `RETENTION_BASE_DIR=./runtime`
   - `RETENTION_TARGETS=*`
2. 啟動：
   ```bash
   cd AristaConnector
   docker compose up -d
   ```
3. 訂閱驗證：
   ```bash
   docker compose exec mqtt mosquitto_sub -h localhost -t "network/arista/raw/#" -v
   ```
4. 檢查 payload 欄位：
   - `device`、`collector`、`cmds`、`format`、`raw`、`ts`

---

# 驗證與驗收清單

## A. 差異重現驗證
使用以下命令重現 5 個差異檔：

```bash
git diff --no-index -- AristaConnector/backend/collector.py originarista/AristaConnector/backend/collector.py
git diff --no-index -- AristaConnector/backend/tests/test_collector.py originarista/AristaConnector/backend/tests/test_collector.py
git diff --no-index -- AristaConnector/backend/app/dao/events.py originarista/AristaConnector/backend/app/dao/events.py
git diff --no-index -- AristaConnector/docker-compose.yml originarista/AristaConnector/docker-compose.yml
git diff --no-index -- AristaConnector/frontend/app/fleet/page.tsx originarista/AristaConnector/frontend/app/fleet/page.tsx
```

## B. 功能敘述可追溯
- 每個優化點都可對應到至少一個檔案：
  - `backend/collector.py`
  - `backend/tests/test_collector.py`
  - `backend/app/dao/events.py`
  - `docker-compose.yml`
  - `frontend/app/fleet/page.tsx`
  - `frontend/app/devices/[id]/page.tsx`
  - `ADD_DEVICES_GUIDE_ZH.md`

## C. 相容性驗證
- 啟用 `MQTT_RAW_COMPAT_ENABLED=true` 後可訂閱到 `network/arista/raw/#`。
- payload 必含 `device`、`collector`、`cmds`、`format`、`raw`、`ts`。

## D. 可讀性驗收
- 本文件至少包含兩張摘要表：
  - 版本證據摘要表
  - 新版優化清單表
- 章節順序完整，具可操作命令與落地驗收項目。

---

# 附錄：證據檔案與比對命令

## 證據檔案（本次結論依據）
- `AristaConnector/backend/collector.py`
- `originarista/AristaConnector/backend/collector.py`
- `AristaConnector/backend/tests/test_collector.py`
- `originarista/AristaConnector/backend/tests/test_collector.py`
- `AristaConnector/backend/app/dao/events.py`
- `originarista/AristaConnector/backend/app/dao/events.py`
- `AristaConnector/docker-compose.yml`
- `originarista/AristaConnector/docker-compose.yml`
- `AristaConnector/frontend/app/fleet/page.tsx`
- `originarista/AristaConnector/frontend/app/fleet/page.tsx`
- `AristaConnector/frontend/app/devices/[id]/page.tsx`
- `AristaConnector/ADD_DEVICES_GUIDE_ZH.md`

## 比對命令（PowerShell）

### 1) 追蹤檔基準與差異統計
```powershell
$tracked = git ls-files | Where-Object { $_ -like 'AristaConnector/*' }
$missing=@(); $diff=@()
foreach($p in $tracked){
  $rel=$p.Substring('AristaConnector/'.Length)
  $q=Join-Path 'originarista/AristaConnector' $rel
  if(-not (Test-Path $q)){ $missing += $rel; continue }
  $h1=(Get-FileHash -Algorithm SHA256 $p).Hash
  $h2=(Get-FileHash -Algorithm SHA256 $q).Hash
  if($h1 -ne $h2){ $diff += $rel }
}
'TRACKED=' + $tracked.Count
'MISSING=' + $missing.Count
$missing
'DIFF=' + $diff.Count
$diff
```

### 2) Markdown 專項比對
```powershell
$a=(Get-ChildItem AristaConnector -Recurse -File -Include *.md,*.MD | % { $_.FullName.Substring((Resolve-Path 'AristaConnector').Path.Length+1) })
$b=(Get-ChildItem originarista/AristaConnector -Recurse -File -Include *.md,*.MD | % { $_.FullName.Substring((Resolve-Path 'originarista/AristaConnector').Path.Length+1) })
$common = $a | ? { $_ -in $b }
$diff=@()
foreach($rel in $common){
  $h1=(Get-FileHash -Algorithm SHA256 (Join-Path 'AristaConnector' $rel)).Hash
  $h2=(Get-FileHash -Algorithm SHA256 (Join-Path 'originarista/AristaConnector' $rel)).Hash
  if($h1 -ne $h2){ $diff += $rel }
}
'MD_IN_ARISTA=' + $a.Count
'MD_IN_ORIGIN=' + $b.Count
'MD_ONLY_IN_ARISTA=' + (($a | ? { $_ -notin $b }).Count)
($a | ? { $_ -notin $b })
'MD_DIFF=' + $diff.Count
$diff
```
