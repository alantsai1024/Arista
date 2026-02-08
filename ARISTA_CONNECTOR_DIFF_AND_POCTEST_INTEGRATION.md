# AristaConnector 比較與 poctest 整合說明

## 比較範圍與方法

### 比較對象
- 主要版本：`AristaConnector/`
- 對照快照：`originarista/AristaConnector/`

### 比較原則
- 以「可交付差異」為主（功能、設定、正式文檔、路由行為）。
- 執行產物（例如 `__pycache__`、`.pytest_cache`、`backend/runtime/raw*`）僅列為附註，不視為功能改動。

### 比較方法
1. 以 `git ls-files` 的 `AristaConnector/*` 追蹤檔作為主基準。
2. 針對同路徑檔案比對 SHA256 hash 判定內容差異。
3. 針對 Markdown（`.md/.MD`）額外做獨立 hash 比對。
4. 針對功能關鍵檔執行 `git diff --no-index` 驗證實際改動內容。

## 差異總覽（一頁摘要）

| 類別 | 結果 | 說明 |
|---|---:|---|
| 追蹤檔案總數（AristaConnector） | 89 | 以 `git ls-files` 統計 |
| `originarista` 缺失檔 | 2 | `ADD_DEVICES_GUIDE_ZH.md`、`frontend/app/devices/[id]/page.tsx` |
| 同路徑內容差異檔 | 5 | 主要為 backend 事件寫入、collector、compose 與 fleet 前端容錯 |
| Markdown 同路徑內容差異 | 0 | 共同存在的 Markdown 內容一致（hash 無差異） |
| 僅新版新增 Markdown | 1 | `ADD_DEVICES_GUIDE_ZH.md` |

### 缺失檔（只在 `AristaConnector/`）
- `AristaConnector/ADD_DEVICES_GUIDE_ZH.md`
- `AristaConnector/frontend/app/devices/[id]/page.tsx`

### 同路徑內容差異檔（5）
- `AristaConnector/backend/app/dao/events.py`
- `AristaConnector/backend/collector.py`
- `AristaConnector/backend/tests/test_collector.py`
- `AristaConnector/docker-compose.yml`
- `AristaConnector/frontend/app/fleet/page.tsx`

## 功能改動明細（逐檔）

| 檔案 | 變更類型 | 改動重點 | 實際影響 | 整合建議 |
|---|---|---|---|---|
| `backend/collector.py` | 行為與穩定性 | 新版以 `record_event` 使用隔離 session 寫入事件；對照版直接共用主 session | 併發輪詢時可降低 DB session 競用風險，事件寫入更穩定 | 建議保留新版寫法，作為 collector 併發寫入標準模式 |
| `backend/tests/test_collector.py` | 測試策略 | 新版新增「併發事件寫入」情境測試，並調整 `poll_single_device` 呼叫型態驗證 | 可驗證隔離 session 設計在併發情境下的正確性 | 建議沿用新版測試，避免未來回歸時忽略併發寫入問題 |
| `backend/app/dao/events.py` | 查詢細節 | 事件統計查詢移除不必要排序，並清理匯入內容 | 降低多餘查詢排序成本，程式碼更聚焦 | 建議保留新版簡化查詢邏輯 |
| `docker-compose.yml` | 部署設定 | MQTT healthcheck 調整；collector 新增 `restart: unless-stopped` | collector 在異常退出後可自動拉起，運維韌性較佳 | 建議採用新版 compose 設定 |
| `frontend/app/fleet/page.tsx` | 前端相容性 | 新增 `/devices/{id}/status` fallback，補齊舊版 `/health/fleet` 缺少 `recent_stats` 的情況 | 舊後端 payload 下，fleet 表格仍可顯示關鍵統計與狀態 | 建議保留 fallback，直到後端 payload 完全一致 |
| `frontend/app/devices/[id]/page.tsx` | 新增功能（僅新版存在） | 新增設備詳情頁（狀態、事件、JSON 展開、10 秒自動更新） | 提升排障與觀測效率，補齊 fleet → device drill-down | 建議在導覽與文件中明確納入此頁面 |
| `ADD_DEVICES_GUIDE_ZH.md` | 新增文件（僅新版存在） | 補上設備新增、批量 bootstrap、MQTT/API 驗證與常見故障排查 | 降低上線門檻，操作流程更標準化 | 建議保留並在 README 文件導覽中顯性鏈接 |

## 文檔改動明細

### 正式文件差異
1. 共同存在的 Markdown 檔案內容一致（hash 差異為 `0`）。
2. 僅 `AristaConnector/` 新增 `ADD_DEVICES_GUIDE_ZH.md`。

### 非功能性差異（執行產物）
`originarista/AristaConnector/` 額外包含多數執行產物，主要類型：
- Python 快取：`__pycache__/*.pyc`
- pytest 快取：`.pytest_cache/*`
- 執行輸出：`backend/runtime/raw/*`、`backend/runtime/raw_ref/*`

上述檔案不建議納入功能比較或合併決策。

## poctest 整合指南（可操作）

### 1) 前置設定
在 `AristaConnector/.env` 啟用 poctest 相容輸出：

```env
MQTT_RAW_COMPAT_ENABLED=true
RETENTION_ENABLED=true
RETENTION_BASE_DIR=./runtime
RETENTION_TARGETS=*
```

若尚未建立 `.env`，可先：

```bash
cd AristaConnector
cp .env.example .env
```

### 2) 啟動服務

```bash
cd AristaConnector
docker compose up -d
```

### 3) 驗證 poctest 相容 raw topic

```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "network/arista/raw/#" -v
```

### 4) 驗證 payload 形狀
在訂閱輸出中確認每筆 JSON 至少含下列欄位：
- `device`
- `collector`
- `cmds`
- `format`
- `raw`
- `ts`

### 5) 整合觸點對照
- `AristaConnector/backend/app/services/mqtt_client.py`
  - `publish_raw_compat()` 產生 poctest 相容 payload 與 topic 發布。
- `AristaConnector/backend/app/services/collector_profile.py`
  - 定義 command 與 `network/arista/raw/*` 的 topic 映射。
- `AristaConnector/backend/collector.py`
  - 輪詢成功後呼叫 `publish_raw_compat()`。
- `AristaConnector/docker-compose.yml`
  - 注入 `MQTT_RAW_COMPAT_ENABLED` 至 backend/collector。
- `AristaConnector/.env.example`
  - 提供預設值與設定入口。

### 6) 兼容結論
目前兩個 `AristaConnector` 版本在 poctest 相容層核心邏輯一致；整合以「環境設定 + topic 驗證」為主，不需要額外改碼。

## 驗證清單

### A. 差異重現驗證
針對 5 個內容差異檔逐一執行：

```bash
git diff --no-index -- AristaConnector/backend/collector.py originarista/AristaConnector/backend/collector.py
git diff --no-index -- AristaConnector/backend/tests/test_collector.py originarista/AristaConnector/backend/tests/test_collector.py
git diff --no-index -- AristaConnector/backend/app/dao/events.py originarista/AristaConnector/backend/app/dao/events.py
git diff --no-index -- AristaConnector/docker-compose.yml originarista/AristaConnector/docker-compose.yml
git diff --no-index -- AristaConnector/frontend/app/fleet/page.tsx originarista/AristaConnector/frontend/app/fleet/page.tsx
```

### B. 檔案存在驗證
確認 `originarista` 缺失檔：
- `AristaConnector/ADD_DEVICES_GUIDE_ZH.md`
- `AristaConnector/frontend/app/devices/[id]/page.tsx`

### C. poctest 整合驗證
1. 啟用 `MQTT_RAW_COMPAT_ENABLED=true`
2. 啟動服務並訂閱 `network/arista/raw/#`
3. 檢查 payload 欄位形狀是否符合規範

### D. 可讀性驗收
本文件需滿足：
- 有摘要表
- 有逐檔差異表
- 有整合步驟清單
- 有風險提示與合併建議

## 合併建議與風險提示

### 合併建議
1. 以 `AristaConnector/` 作為主線，吸收其穩定性與可觀測性改動。
2. 保留 `collector.py` 的隔離 session 事件寫入設計與對應測試。
3. 保留 `fleet/page.tsx` fallback，維持舊後端相容期的前端穩定顯示。
4. 正式將 `ADD_DEVICES_GUIDE_ZH.md` 與 `devices/[id]` 納入文件導覽與驗收流程。

### 風險提示
1. 若回退 `collector.py` 至共用 session 寫法，併發情境下事件寫入失敗風險上升。
2. 若移除 fleet fallback，舊版後端 payload 可能造成前端統計欄位顯示退化。
3. `originarista` 的執行產物不得誤判為功能差異或誤納入版本基線。

## 附錄：比對命令

### 1) 追蹤檔比對（數量、缺失、內容差異）
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
'MISSING_IN_ORIGIN=' + $missing.Count
$missing
'HASH_DIFF=' + $diff.Count
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
'MD_HASH_DIFF=' + $diff.Count
$diff
```

## Public APIs / Interfaces / Types 影響
- 無新增對外 REST API 端點。
- 主要差異為內部行為強化（collector 事件寫入）與前端容錯邏輯。
- 前端新增路由能力：`/devices/[id]`（設備詳情頁）。
