# 快速部署指南

## 一鍵部署到遠端伺服器

### 伺服器資訊
- **主機**: 123.192.126.214
- **端口**: 33333
- **用戶**: ubuntu
- **目錄**: ~/aristacollector

### 部署步驟

#### Windows PowerShell

```powershell
# 執行部署腳本
.\deploy.ps1
```

#### Linux/Mac/WSL/Git Bash

```bash
# 賦予執行權限
chmod +x deploy.sh

# 執行部署
./deploy.sh
```

### 部署腳本會自動執行：

1. ✅ 測試 SSH 連接
2. ✅ 檢查遠端 Docker 安裝
3. ✅ 建立遠端目錄
4. ✅ 上傳專案檔案
5. ✅ 設定環境變數
6. ✅ 構建並啟動所有服務

### 部署後存取

服務啟動後（約 1-2 分鐘），可以通過以下網址存取：

- **前端儀表板**: http://123.192.126.214:3000
- **後端 API**: http://123.192.126.214:8000
- **API 文件**: http://123.192.126.214:8000/docs

### 手動部署（如果腳本失敗）

```bash
# 1. 連接到伺服器
ssh -p 33333 ubuntu@123.192.126.214

# 2. 安裝 Docker (如果尚未安裝)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
# 登出並重新登入

# 3. 建立目錄
mkdir -p ~/aristacollector
cd ~/aristacollector

# 4. 從本地複製檔案 (在本地執行)
# 使用 rsync (推薦)
rsync -avz -e "ssh -p 33333" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.next' \
  --exclude '.env' \
  ./ ubuntu@123.192.126.214:~/aristacollector/

# 或使用 scp
scp -P 33333 -r . ubuntu@123.192.126.214:~/aristacollector/

# 5. 在遠端伺服器上配置
ssh -p 33333 ubuntu@123.192.126.214
cd ~/aristacollector
cp .env.example .env
nano .env  # 編輯配置

# 6. 啟動服務
docker compose build
docker compose up -d

# 7. 查看狀態
docker compose ps
docker compose logs -f
```

### 常用管理命令

```bash
# 連接到伺服器
ssh -p 33333 ubuntu@123.192.126.214

# 查看日誌
cd ~/aristacollector
docker compose logs -f

# 重啟服務
docker compose restart

# 停止服務
docker compose down

# 更新代碼後重新部署
docker compose build
docker compose up -d
```

### 故障排除

#### SSH 連接失敗
- 確認 SSH 金鑰已配置
- 檢查防火牆是否開放端口 33333
- 確認伺服器 IP 正確

#### Docker 未安裝
腳本會提示安裝 Docker，或手動執行：
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

#### 端口被佔用
檢查並釋放端口：
```bash
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :3000
```

#### 服務無法啟動
查看詳細日誌：
```bash
docker compose logs <service_name>
```

### 安全建議

1. **更改預設密碼**: 編輯 `.env` 檔案，設定強密碼
2. **設定防火牆**: 只開放必要端口
3. **使用 HTTPS**: 建議設定反向代理和 SSL 憑證
4. **定期備份**: 設定資料庫自動備份

### 下一步

部署完成後：
1. 透過前端儀表板新增設備
2. 檢查 Collector 日誌確認輪詢正常
3. 設定監控和告警
4. 配置自動備份

詳細部署文檔請參考 `DEPLOY.md`
