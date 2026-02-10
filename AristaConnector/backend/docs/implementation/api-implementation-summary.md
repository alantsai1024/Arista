# 機群管理 API 實作摘要

## ✅ 已完成功能

### 1. 資料庫模型（SQLAlchemy 2.0 Async）

**檔案**：`backend/app/models.py`

- ✅ 設備與事件採用 UUID 主鍵
- ✅ 設備 schema 新增/更新欄位：
  - `id`（UUID，主鍵）
  - `hostname`（可為空字串）
  - `ip`（必填字串，已建立索引）
  - `port`（整數，預設 443）
  - `username`（必填字串）
  - `password_enc`（加密後密碼，text）
  - `interval_sec`（整數，預設 10）
  - `enabled`（布林，預設 true，已建立索引）
  - `identity_mode`（`auto|manual`）
  - `expected_identity_fingerprint`（可選 64-char sha256）
  - `identity_status`（`unbound|verified|conflict|insufficient_identity`）
  - `created_at`、`updated_at`（時間戳）
- ✅ events 資料表使用 UUID 外鍵
- ✅ 完成關聯設定（Device -> Events）

### 2. 資料庫 Migration（Alembic）

**檔案**：
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`

- ✅ 已完成 async SQLAlchemy 的 Alembic 設定
- ✅ 完成 migration 環境設定
- ✅ 可直接產生初始 migration

**建立初始 migration：**
```bash
cd backend
alembic revision --autogenerate -m "Initial migration with UUID and encrypted passwords"
alembic upgrade head
```

### 3. 密碼加密

**檔案**：`backend/app/utils/encryption.py`

- ✅ MVP 階段使用 Base64 編碼（簡易加密）
- ✅ `encrypt_password()`
- ✅ `decrypt_password()`
- ✅ 已加上正式環境 TODO（Vault、Fernet 等）

### 4. 驗證工具

**檔案**：`backend/app/utils/validation.py`

- ✅ IP 驗證（IPv4 與 IPv6）
- ✅ 輪詢間隔驗證（5 到 300 秒）

### 5. Pydantic Schemas

**檔案**：`backend/app/schemas.py`

- ✅ `DeviceBase`（含欄位驗證）
- ✅ `DeviceCreate`
- ✅ `DeviceUpdate`（支援部分更新）
- ✅ `DeviceResponse`（不回傳密碼）
- ✅ `ConnectionTestResponse`
- ✅ IP 格式驗證
- ✅ interval 範圍驗證（5 到 300 秒）

### 6. API 端點

**檔案**：`backend/app/routers/devices.py`

- ✅ `POST /devices`：建立設備
  - 驗證 IP 格式
  - 驗證 interval（5 到 300 秒）
  - 寫入前加密密碼
  - 防止重複 IP
  - 防止重複 `expected_identity_fingerprint`（HTTP 409）
- ✅ `GET /devices`：列出所有設備
  - 依建立時間排序回傳
- ✅ `GET /devices/{id}`：取得單一設備
  - 找不到回傳 404
- ✅ `PATCH /devices/{id}`：更新設備
  - 支援部分欄位更新
  - 可更新 interval、enabled、帳密、IP 等
  - 若提供 IP/interval 會做驗證
  - 密碼更新時會重新加密
  - 支援更新 identity mode 與 expected fingerprint
- ✅ `POST /devices/{id}/test-connection`：測試 eAPI 連線
  - 呼叫 Arista eAPI 的 `show hostname`
  - 成功時回傳 hostname，失敗回傳錯誤
- ✅ `GET /devices/{id}/status`：由 Redis 取得設備狀態
  - 回傳 online/offline
  - 回傳 last_seen
  - 支援 `ip_conflict` 狀態，且僅 `status=online` 才會 `online=true`

### 7. eAPI Client

**檔案**：`backend/app/services/eapi_client.py`

- ✅ `test_connection()`
- ✅ Arista eAPI 整合
- ✅ 認證處理
- ✅ 錯誤處理（timeout、連線錯誤）
- ✅ 成功時回傳 hostname

### 8. 單元測試

**檔案**：
- `backend/tests/conftest.py`：測試 fixtures
- `backend/tests/test_devices_api.py`：設備 API 測試
- `backend/tests/test_connection.py`：連線測試

**測試涵蓋：**
- ✅ 建立設備（成功與驗證失敗）
- ✅ 列出設備
- ✅ 取得設備（存在與不存在）
- ✅ 更新設備（interval、enabled、credentials）
- ✅ 停用設備
- ✅ 非法 IP 驗證
- ✅ 非法 interval 驗證
- ✅ 重複 IP 防護
- ✅ 連線測試端點（成功與失敗）
- ✅ 不存在設備的連線測試

**測試設定：**
- ✅ 使用 in-memory SQLite 以提升測試速度
- ✅ 使用 pytest-asyncio 支援非同步測試
- ✅ 已建立資料庫 session fixtures
- ✅ 已建立 API client fixtures

### 9. 建置設定

**更新檔案：**
- `backend/requirements.txt`：新增 pytest、pytest-asyncio、aiosqlite
- `Makefile`：新增 `test-backend` 指令
- `backend/pytest.ini`：pytest 設定

## 📋 API 端點總覽

| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| POST | `/devices` | 建立新設備 | ✅ |
| GET | `/devices` | 列出所有設備 | ✅ |
| GET | `/devices/{id}` | 取得單一設備 | ✅ |
| PATCH | `/devices/{id}` | 更新設備 | ✅ |
| POST | `/devices/{id}/test-connection` | 測試 eAPI 連線 | ✅ |
| GET | `/devices/{id}/status` | 取得設備狀態 | ✅ |

## 🔒 安全性說明

- **密碼加密**：目前使用 base64（僅限 MVP）
  - TODO：正式環境需改為真正加密（Fernet、Vault 等）
- **輸入驗證**：已驗證 IP 格式與 interval 範圍
- **回應不含密碼**：API 不回傳密碼欄位

## 🧪 測試

執行測試：
```bash
make test-backend
# 或
docker compose exec backend pytest tests/ -v
```

## 📝 下一步

1. **建立初始 migration：**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```
2. **更新 `collector.py`** 以完整使用 UUID 版設備模型
3. **更新 frontend** 以對應 UUID device ID
4. **導入正式加密方案**（取代 base64）
5. **新增整合測試**（以 mock 設備驗證 eAPI 連線）

## 📚 相關文件

- `../migrations/migration-guide.md`：資料庫 migration 詳細說明
- `../migrations/readme-migrations.md`：migration 快速參考
- `../testing/testing.md`：測試指南與範例
