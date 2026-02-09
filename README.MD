# Arista 專案倉庫

## 專案簡介
此倉庫包含 Arista eAPI 到 MQTT 的主系統與相關文件。

- 主要開發與部署目標：`AristaConnector/`

## 倉庫結構
- `AristaConnector/`：主要可部署系統（`backend` / `frontend` / `mqtt`）

## 快速開始（主專案）
```bash
cd AristaConnector
cp .env.example .env
cp secrets/veos_credentials.example.json secrets/veos_credentials.json
cd frontend
npm install
cd ..
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

詳細步驟請見：`AristaConnector/docs/setup/local-windows-setup.md`

## 文件導覽
- [主專案總覽](AristaConnector/README.md)
- [主專案快速啟動](AristaConnector/QUICKSTART.md)
- [Windows 本機安裝流程](AristaConnector/docs/setup/local-windows-setup.md)
- [驗收與測試案例](AristaConnector/docs/testing/demo-testcases.md)

## 開發建議
- 優先以 `AristaConnector/` 的文件與流程為準。
- 一般設定放在 `.env`（由 `.env.example` 複製）；vEOS 帳密請放在 `AristaConnector/secrets/veos_credentials.json`，避免帳密硬編碼與誤提交。
