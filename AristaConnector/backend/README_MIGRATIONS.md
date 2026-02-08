# 資料庫遷移

## 快速開始

### 首次設定

1. **建立初始遷移：**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Initial migration"
   ```

2. **檢查產生的遷移檔案**（位於 `alembic/versions/`）

3. **套用遷移：**
   ```bash
   alembic upgrade head
   ```

### Docker 用法

```bash
# 建立遷移
docker compose exec backend alembic revision --autogenerate -m "Description"

# 套用遷移
docker compose exec backend alembic upgrade head

# 或使用 Makefile
make migrate
```

## 目前 Schema

### Devices 資料表
- `id`（UUID，主鍵）
- `hostname`（string，可為空）
- `ip`（string，必填，已建立索引）
- `port`（integer，預設 443）
- `username`（string，必填）
- `password_enc`（text，加密密碼）
- `interval_sec`（integer，預設 10）
- `enabled`（boolean，預設 true，已建立索引）
- `created_at`（timestamp）
- `updated_at`（timestamp，可為空）

### Events 資料表
- `id`（UUID，主鍵）
- `device_id`（UUID，外鍵到 devices.id）
- `event_type`（string，已建立索引）
- `message`（text，可為空）
- `metadata`（text，以文字儲存 JSON）
- `created_at`（timestamp，已建立索引）

## 從舊 Schema 遷移

若目前資料仍使用整數 ID，需撰寫客製 migration 來：
1. 新增 UUID 欄位
2. 為既有資料產生 UUID
3. 更新外鍵關聯
4. 移除舊的整數欄位

詳細說明請見 `MIGRATION_GUIDE.md`。

