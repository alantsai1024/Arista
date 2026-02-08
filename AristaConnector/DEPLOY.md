# 部署指南

## 遠端伺服器部署

### 前置需求

1. **遠端伺服器要求：**
   - Ubuntu 18.04+ (或其他 Linux 發行版)
   - Docker 和 Docker Compose 已安裝
   - SSH 訪問權限
   - 開放端口：3000 (前端), 8000 (後端), 5432 (PostgreSQL), 6379 (Redis), 1883 (MQTT)

2. **本地要求：**
   - SSH 客戶端
   - 對遠端伺服器的 SSH 訪問權限

### 快速部署

#### 方法 1: 使用部署腳本 (推薦)

**Linux/Mac/WSL:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows PowerShell:**
```powershell
.\deploy.ps1
```

**Windows (Git Bash/WSL):**
```bash
./deploy.sh
```

#### 方法 2: 手動部署

1. **連接到遠端伺服器：**
```bash
ssh -p 33333 ubuntu@123.192.126.214
```

2. **安裝 Docker (如果尚未安裝):**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
# 登出並重新登入以應用群組變更
```

3. **建立專案目錄：**
```bash
mkdir -p ~/aristacollector
cd ~/aristacollector
```

4. **上傳專案檔案：**
   - 使用 SCP:
   ```bash
   # 從本地執行
   scp -P 33333 -r . ubuntu@123.192.126.214:~/aristacollector/
   ```
   
   - 或使用 rsync (推薦):
   ```bash
   rsync -avz -e "ssh -p 33333" \
     --exclude '.git' \
     --exclude 'node_modules' \
     --exclude '__pycache__' \
     --exclude '.next' \
     --exclude '.env' \
     ./ ubuntu@123.192.126.214:~/aristacollector/
   ```

5. **在遠端伺服器上配置環境：**
```bash
cd ~/aristacollector
cp .env.example .env
nano .env  # 編輯生產環境配置
```

6. **啟動服務：**
```bash
docker compose build
docker compose up -d
```

7. **檢查服務狀態：**
```bash
docker compose ps
docker compose logs -f
```

### 生產環境配置

#### 1. 編輯 `.env` 檔案

在遠端伺服器上編輯 `.env` 檔案，設定生產環境變數：

```bash
ssh -p 33333 ubuntu@123.192.126.214
cd ~/aristacollector
nano .env
```

重要設定：
- `POSTGRES_PASSWORD`: 設定強密碼
- `MQTT_USERNAME` 和 `MQTT_PASSWORD`: 設定 MQTT 認證
- `NEXT_PUBLIC_API_URL`: 設定為實際的 API URL

#### 2. 使用生產配置

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 3. 設定防火牆

```bash
# Ubuntu UFW
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend API
sudo ufw allow 1883/tcp  # MQTT (如果需要外部訪問)
```

#### 4. 設定反向代理 (可選，推薦)

使用 Nginx 作為反向代理：

```nginx
# /etc/nginx/sites-available/arista
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

啟用配置：
```bash
sudo ln -s /etc/nginx/sites-available/arista /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 常用命令

#### 查看日誌
```bash
# 所有服務
docker compose logs -f

# 特定服務
docker compose logs -f backend
docker compose logs -f collector
docker compose logs -f frontend
```

#### 重啟服務
```bash
docker compose restart
# 或重啟特定服務
docker compose restart backend
```

#### 停止服務
```bash
docker compose down
```

#### 更新部署
```bash
# 1. 拉取最新代碼
cd ~/aristacollector
git pull  # 如果使用 git

# 2. 重新構建並啟動
docker compose build
docker compose up -d
```

#### 備份資料庫
```bash
docker compose exec postgres pg_dump -U arista arista > backup_$(date +%Y%m%d).sql
```

#### 還原資料庫
```bash
docker compose exec -T postgres psql -U arista arista < backup_20240101.sql
```

### 監控和維護

#### 檢查服務健康狀態
```bash
# 檢查容器狀態
docker compose ps

# 檢查資源使用
docker stats

# 檢查磁碟使用
docker system df
```

#### 清理未使用的資源
```bash
# 清理未使用的映像和容器
docker system prune -a

# 清理卷（謹慎使用）
docker volume prune
```

### 故障排除

#### 服務無法啟動
```bash
# 查看詳細日誌
docker compose logs <service_name>

# 檢查端口是否被佔用
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :3000

# 檢查 Docker 狀態
sudo systemctl status docker
```

#### 資料庫連接問題
```bash
# 測試資料庫連接
docker compose exec backend python -c "from app.database import engine; print('DB OK')"

# 檢查資料庫日誌
docker compose logs postgres
```

#### 前端無法連接到後端
- 檢查 `.env` 中的 `NEXT_PUBLIC_API_URL` 設定
- 確認後端服務正在運行
- 檢查防火牆規則

### 安全建議

1. **更改預設密碼**: 確保所有服務使用強密碼
2. **使用 HTTPS**: 設定 SSL/TLS 憑證
3. **限制端口訪問**: 只開放必要的端口
4. **定期備份**: 設定自動備份資料庫
5. **更新系統**: 定期更新 Docker 和系統套件
6. **監控日誌**: 設定日誌監控和告警

### 支援

如有問題，請檢查：
- 服務日誌: `docker compose logs`
- 系統日誌: `journalctl -u docker`
- GitHub Issues (如果適用)
