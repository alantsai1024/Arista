# Arista 專案倉庫

## 專案簡介
此倉庫包含 Arista eAPI 到 MQTT 的主系統與早期 PoC。

- 主要開發與部署目標：`AristaConnector/`
- 早期原型與對照參考：`poctest/`

## 倉庫結構
- `AristaConnector/`：主要可部署系統（`backend` / `frontend` / `mqtt`）
- `poctest/`：早期 PoC 與資料流驗證範例

## 快速開始（主專案）
```bash
cd AristaConnector
docker compose up -d
docker compose exec backend python scripts/bootstrap_real_veos.py
```

驗證端點：
- `http://localhost:8000/docs`
- `http://localhost:3000`

## 常用工作流程
### Docker 模式
```bash
cd AristaConnector
docker compose up -d
docker compose logs -f backend collector
```

詳細步驟請見：`AristaConnector/QUICKSTART.md`

### Windows 本機模式（無 Docker）
```powershell
cd AristaConnector\backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

```powershell
cd AristaConnector\backend
python collector.py
```

詳細步驟請見：`AristaConnector/LOCAL_WINDOWS_SETUP.md`

## 文件導覽
- [主專案總覽](AristaConnector/README.md)
- [主專案快速啟動](AristaConnector/QUICKSTART.md)
- [Windows 本機安裝流程](AristaConnector/LOCAL_WINDOWS_SETUP.md)
- [驗收與測試案例](AristaConnector/DEMO_TESTCASES.md)
- [PoC 專案說明](poctest/README.md)
- [PoC Agent 設計說明](poctest/agent.md)

## 開發建議
- 優先以 `AristaConnector/` 的文件與流程為準。
- `poctest/` 僅作參考，不作為主要交付流程。
- 敏感設定請放在 `.env`（由 `.env.example` 複製），避免帳密硬編碼。
