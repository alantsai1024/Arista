# 部署步驟指南

## 快速部署到 123.192.126.214

### 步驟 1: 測試 SSH 連接

在 PowerShell 中執行：
```powershell
ssh -p 33333 ubuntu@123.192.126.214
```

如果首次連接，會提示確認主機密鑰，輸入 `yes`。

### 步驟 2: 確認 Docker 已安裝

連接到伺服器後，執行：
```bash
docker --version
docker compose version
```

如果未安裝，執行：
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
# 登出並重新登入以應用群組變更
exit
ssh -p 33333 ubuntu@123.192.126.214
```

### 步驟 3: 上傳專案檔案

**選項 A: 使用 SCP (Windows PowerShell)**
```powershell
# 建立壓縮檔並上傳
tar -czf deploy.tar.gz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' --exclude='.next' --exclude='.env' .
scp -P 33333 deploy.tar.gz ubuntu@123.192.126.214:~/

# 在遠端解壓
ssh -p 33333 ubuntu@123.192.126.214 "cd ~ && tar -xzf deploy.tar.gz -C aristacollector && rm deploy.tar.gz"
```

**選項 B: 使用 WinSCP 或 FileZilla**
- 主機: 123.192.126.214
- 端口: 33333
- 用戶: ubuntu
- 上傳整個專案目錄到 ~/aristacollector

**選項 C: 使用 Git (如果遠端有 Git)**
```bash
ssh -p 33333 ubuntu@123.192.126.214
cd ~
git clone <your-repo-url> aristacollector
cd aristacollector
```

### 步驟 4: 在遠端伺服器上配置

```bash
ssh -p 33333 ubuntu@123.192.126.214
cd ~/aristacollector

# 建立 .env 檔案
cp .env.example .env

# 編輯配置（使用 nano 或 vi）
nano .env
```

重要設定：
- `POSTGRES_PASSWORD`: 設定強密碼
- `MQTT_USERNAME` 和 `MQTT_PASSWORD`: 可選，設定 MQTT 認證
- 其他保持預設值即可

### 步驟 5: 構建並啟動服務

```bash
cd ~/aristacollector

# 構建 Docker 映像
docker compose build

# 啟動所有服務
docker compose up -d

# 查看服務狀態
docker compose ps

# 查看日誌
docker compose logs -f
```

### 步驟 6: 驗證部署

服務啟動後（約 1-2 分鐘），訪問：
- 前端: http://123.192.126.214:3000
- 後端 API: http://123.192.126.214:8000
- API 文件: http://123.192.126.214:8000/docs

### 常用管理命令

```bash
# 查看日誌
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
- 確認 SSH 金鑰已配置，或準備好密碼
- 檢查防火牆是否開放端口 33333

#### Docker 權限問題
```bash
sudo usermod -aG docker $USER
# 登出並重新登入
```

#### 端口被佔用
```bash
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :3000
```

#### 服務無法啟動
```bash
docker compose logs <service_name>
```
