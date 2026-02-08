# 協作代理指南

## 目標與範圍
此文件提供人類與 AI 協作者在本倉庫的共同工作規範。

- 目標：以安全、可回溯、可驗證的方式完成任務
- 主要範圍：`AristaConnector/` 的開發、測試與文件維護

## 倉庫真實狀態（Source of Truth）
- 主工作路徑：`AristaConnector/`
- `poctest/` 為歷史 PoC 對照，不是主要交付目標

## 標準作業流程
1. 開發前先閱讀：
   - `AristaConnector/README.md`
   - `AristaConnector/QUICKSTART.md`
2. 在主專案目錄啟動服務：
   ```bash
   cd AristaConnector
   docker compose up -d
   ```
3. 任務完成前至少做一項驗證（API / MQTT / 前端）：
   - API：`http://localhost:8000/docs`
   - MQTT：訂閱 `arista/default/+/state` 或 `arista/default/+/telemetry/+`
   - 前端：`http://localhost:3000`
4. 收尾輸出需包含：
   - 修改檔案清單
   - 驗證命令與結果摘要

## 變更規範
- 優先小步變更，避免一次大改且難以回溯。
- 不修改與本任務無關的檔案。
- 不提交密碼、金鑰、憑證或真實敏感資訊。
- 若變更 API 行為或關鍵流程，必須同步更新對應文件。

## 測試與驗收規範
- Backend 測試：
  ```bash
  cd AristaConnector/backend
  pytest tests -v
  ```
- Frontend 基本驗收：
  ```bash
  cd AristaConnector/frontend
  npm install
  npm run dev
  ```
- Frontend e2e（如任務涉及）：
  ```bash
  cd AristaConnector/frontend
  npx playwright test
  ```
- 文件變更驗收：
  - 檢查連結目標檔案存在
  - 檢查命令可讀且路徑正確

## 文件維護規範
- 根目錄文件（`README.MD`、`AGENT.MD`）只做入口與規範，不複製子專案完整手冊。
- 若命令、路徑、流程改動，需同步更新 `README.MD` 與 `AGENT.MD`。

## 禁止事項
- 不在根文件寫入易過期的硬編碼設定。
- 不把 `poctest/` 流程寫成主流程。
- 不新增與現況不符的部署承諾或測試聲明。
