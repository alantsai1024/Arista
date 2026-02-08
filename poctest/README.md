# Arista eAPI → MQTT 原始資料代理

此專案透過 Arista EOS eAPI 取得設備資訊，並以 MQTT 發布原始 JSON 資料，供其他系統訂閱與處理。

**架構**
![架構圖](notes/架構圖.png)

**依賴與安裝**
- Python 3.8+（建議 3.10+）
- 依賴套件：`requests`, `paho-mqtt`

```bash
pip install requests paho-mqtt
```

**事前條件**
- Arista eAPI 已啟用，且可透過 HTTP/HTTPS 存取。
- MQTT broker 已可連線（本專案只負責發布，不負責啟動 broker）。

**快速開始**
1. 設定環境變數（以下為示例，請自行替換為實際值）。

```bash
set EOS_HOST=192.168.x.x
set EOS_USER=<username>
set EOS_PASS=<password>
set MQTT_HOST=127.0.0.1
```

2. 啟動代理程式。

```bash
python arista_agent.py
```

3. 驗證 MQTT 訊息（示例）。

```bash
mosquitto_sub -h 127.0.0.1 -t "network/arista/raw/#" -v
```

**環境變數**
預設值在 `arista_agent.py` 中定義。建議以環境變數覆寫避免硬編碼。

| 變數 | 說明 | 預設值來源 |
| --- | --- | --- |
| `EOS_HOST` | Arista EOS 管理介面 IP/主機名 | `arista_agent.py` |
| `EOS_HTTPS` | 是否使用 HTTPS | `arista_agent.py` |
| `EOS_USER` | eAPI 使用者 | `arista_agent.py` |
| `EOS_PASS` | eAPI 密碼 | `arista_agent.py` |
| `EOS_VERIFY_TLS` | HTTPS 憑證驗證 | `arista_agent.py` |
| `EOS_TIMEOUT` | eAPI 請求逾時秒數 | `arista_agent.py` |
| `MQTT_HOST` | MQTT broker 位址 | `arista_agent.py` |
| `MQTT_PORT` | MQTT broker 連接埠 | `arista_agent.py` |
| `MQTT_USERNAME` | MQTT 使用者 | `arista_agent.py` |
| `MQTT_PASSWORD` | MQTT 密碼 | `arista_agent.py` |
| `MQTT_QOS` | MQTT QoS | `arista_agent.py` |
| `MQTT_RETAIN` | MQTT retain | `arista_agent.py` |

**Collector 設定**
Collector 定義集中在 `config.py` 的 `COLLECTORS`。

每個 collector 欄位說明：
- `name`：collector 名稱
- `cmds`：Arista CLI 指令陣列
- `format`：回傳格式（如 `json` 或 `text`）
- `interval`：輪詢間隔（秒）
- `topic`：MQTT topic

新增 collector 範例：

```python
COLLECTORS.append({
    "name": "interfaces-brief",
    "cmds": ["show interfaces brief"],
    "format": "json",
    "interval": 30,
    "topic": "network/arista/raw/show-interfaces-brief",
})
```

**輸出格式**
MQTT payload 為 JSON，結構如下（示意）：

```json
{
  "device": "<EOS_HOST>",
  "collector": "<collector-name>",
  "cmds": ["show ..."],
  "format": "json",
  "raw": [ ... ],
  "ts": 1700000000
}
```

**驗證**
1. 設定環境變數並執行 `python arista_agent.py`。
2. 使用 `mosquitto_sub` 訂閱 `network/arista/raw/#`。
3. 嘗試錯誤帳密，確認日誌會輸出錯誤訊息。
