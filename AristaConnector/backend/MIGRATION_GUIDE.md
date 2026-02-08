# 資料庫遷移指南

## 建立初始遷移

更新模型後，建立新的 migration：

```bash
# 在 backend 目錄執行
alembic revision --autogenerate -m "Initial migration with UUID and encrypted passwords"
```

執行後會在 `alembic/versions/` 產生 migration 檔案。

## 檢查遷移

套用前務必先檢視自動產生的 migration 內容：

```bash
# 檢視 migration 檔案
cat alembic/versions/<migration_file>.py
```

## 套用遷移

```bash
# 套用所有待執行 migration
alembic upgrade head

# 或使用 Docker
docker compose exec backend alembic upgrade head
```

## 回滾遷移

```bash
# 回滾一步
alembic downgrade -1

# 回滾到指定版本
alembic downgrade <revision_id>
```

## 手動遷移步驟

若要搬移既有資料，建議流程：

1. **先備份目前資料庫**
2. **撰寫含資料轉換的 migration 腳本**
3. **先在 staging 測試**
4. **再套用到 production**

## 遷移檢查清單

- [ ] 檢查自動產生的 migration 內容
- [ ] 在開發資料庫測試 migration
- [ ] 備份正式資料庫
- [ ] 在維護時段套用 migration
- [ ] 套用後確認資料完整性
- [ ] 如有需要同步更新應用程式程式碼

