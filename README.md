# 台股多因子分析系統

Taiwan Stock Multi-Factor Analysis System

## 功能

- **多因子評分**：對台股上市櫃股票進行五大維度評分（基本面 30%、籌碼面 25%、技術面 20%、權證 10%、市場情緒 15%）
- **個股分析**：輸入股票代號取得完整多因子評估報告（評分、訊號、價格趨勢、建議）
- **回測引擎**：支援多因子輪動、買入持有、等權重等多種策略，含手續費/稅/滑價模型
- **排程更新**：每日自動更新資料（排程器）
- **即時儀表板**：Streamlit 互動式視覺化介面
- **免 API Token**：資料來自 TWSE OpenAPI + FinMind 匿名模式，無需註冊即可使用

## 系統架構

```
src/
├── main.py              # CLI 入口 (analyze/score/backtest/schedule/dashboard)
├── config.py            # 全域設定（權重、回測參數、排程）
├── data/
│   ├── free_data_client.py   # 免 Token 資料客戶端（TWSE OpenAPI + FinMind 匿名）
│   ├── finmind_client.py     # FinMind 包裝層（Token 選用）
│   ├── cache_manager.py      # SQLite 快取層
│   ├── scheduler.py          # 每日排程更新
│   └── stock_universe.py     # 股票清單管理
├── features/
│   ├── fundamental.py    # 基本面評分
│   ├── institutional.py  # 籌碼面評分
│   ├── technical.py      # 技術面評分
│   ├── warrant.py        # 權證評分
│   └── sentiment.py      # 市場情緒評分
├── model/
│   ├── multi_factor.py   # 多因子模型
│   └── signal.py         # 訊號生成
├── backtest/
│   ├── engine.py         # backtrader 引擎
│   ├── strategies.py     # 交易策略
│   └── report.py         # 回測報告（圖表 + JSON）
├── analysis/
│   └── stock_report.py   # 個股分析報告
└── dashboard/
    └── app.py            # Streamlit 儀表板
```

## 安裝

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 使用方式

### CLI

```bash
# 檢查 API 連線
python3 src/main.py check-api

# 分析單一個股
python3 src/main.py analyze 2330
python3 src/main.py analyze 2317 --years 2 --json

# 多因子評分（批次）
python3 src/main.py score --max-stocks 50

# 回測
python3 src/main.py backtest --start 2023-01-01 --end 2026-01-01

# 執行每日更新
python3 src/main.py schedule

# 啟動儀表板
python3 src/main.py dashboard

# 清除快取
python3 src/main.py clear

# 查看權重
python3 src/main.py weights
```

### Dashboard

```bash
python3 src/main.py dashboard
```

瀏覽器開啟 `http://localhost:8501`

## 資料來源

- **TWSE OpenAPI** (`openapi.twse.com.tw`)：本益比、股價淨值比、現金殖利率 — 免 Token
- **FinMind**（匿名模式）：股價、營收、三大法人、融資融券、股利 — 每小時 300 次
- **twstock**：備用股價資料源

## 環境變數

| 變數 | 必要 | 說明 |
|------|------|------|
| `FINMIND_TOKEN` | 否 | FinMind Token（未設定則匿名模式，每小時 300 次） |

## License

MIT
