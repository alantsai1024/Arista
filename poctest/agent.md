# Arista eAPI → MQTT Agent 設計說明

**整體概覽**
此代理以輪詢方式向 Arista EOS eAPI 送出 CLI 指令，取得原始回傳資料後，序列化成 JSON 並發布到 MQTT。

**資料流**
ASCII 流程：

```
config.py (COLLECTORS)
        |
        v
arista_agent.py (排程與輪詢)
        |
        v
collectors.py (eAPI runCmds)
        |
        v
dispatcher_mqtt.py (MQTT publish)
        |
        v
MQTT broker -> subscribers
```

**模組職責**
| 檔案 | 負責事項 |
| --- | --- |
| `arista_agent.py` | 主迴圈、輪詢排程、組 payload、錯誤記錄 |
| `collectors.py` | eAPI `runCmds` RPC 呼叫與回應錯誤處理 |
| `dispatcher_mqtt.py` | MQTT 連線、JSON 序列化與發布 |
| `config.py` | Collector 定義與 topic 配置 |

**Payload Schema**
發布到 MQTT 的 JSON 結構欄位說明：
- `device`：設備識別（通常是 EOS 主機名或 IP）
- `collector`：collector 名稱
- `cmds`：送出的 CLI 指令陣列
- `format`：回傳格式（如 `json` 或 `text`）
- `raw`：eAPI 原始回傳資料
- `ts`：UNIX timestamp（秒）

**Topic 規則**
Topic 由 `config.py` 中 `COLLECTORS` 的 `topic` 欄位定義，內建 topics：
- `network/arista/raw/show-clock`
- `network/arista/raw/show-hostname`
- `network/arista/raw/show-interfaces-status`
- `network/arista/raw/show-version`

**設計決策與限制**
- 使用輪詢與簡單間隔控制，無事件驅動機制。
- 無重試或退避策略，單次失敗只記錄錯誤。
- 以單一執行序輪詢 collector，無併發設計。

**擴充點**
- 新增 collector：修改 `config.py` 的 `COLLECTORS`。
- 新增 dispatcher：可擴充 `dispatcher_mqtt.py` 或新增其他發布模組（例如 Kafka）。
- 強化安全：加入 TLS 驗證、憑證管理或更嚴格的認證流程。
