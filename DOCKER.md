# 使用 Docker 部署

本專案支援使用 Docker 容器化部署，方便在不同環境中執行分析與儀表板。

## 快速開始

### 1. 建置映像檔

```bash
docker build -t stock-analysis .
```

### 2. 執行 CLI 工具

執行單次分析：
```bash
docker run --rm -v $(pwd)/data:/app/data stock-analysis analyze 2330
```

### 3. 啟動 Dashboard (Docker Compose)

推薦使用 Docker Compose 來啟動 Streamlit 儀表板：

```bash
docker-compose up -d
```

啟動後即可在瀏覽器訪問 `http://localhost:8501`。

## 注意事項

- **網路存取**：`docker-compose.yml` 已配置 `stock-network` (bridge 模式)，確保容器能存取外部金融 API (TWSE, FinMind)。
- **資料持久化**：使用 `-v $(pwd)/data:/app/data` 將本地 data 目錄掛載到容器內，以保存 SQLite 快取。
- **環境變數**：如果需要設定 FinMind Token，可以在 `docker-compose.yml` 中加入環境變數，或是在執行 `docker run` 時使用 `-e FINMIND_TOKEN=your_token`。
