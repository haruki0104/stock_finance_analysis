import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from src.data.free_data_client import FreeDataClient
from src.data.cache_manager import init_db
from src.model.multi_factor import MultiFactorModel
from src.model.signal import generate_signals
from src.config import BACKTEST_START, BACKTEST_END

st.set_page_config(page_title="台股多因子分析系統", layout="wide")
st.title("台股多因子分析系統")

init_db()

if "client" not in st.session_state:
    st.session_state.client = FreeDataClient()
if "model" not in st.session_state:
    st.session_state.model = MultiFactorModel(st.session_state.client)

client = st.session_state.client
model = st.session_state.model

st.sidebar.header("參數設定")
start_date = st.sidebar.date_input("開始日期", pd.to_datetime(BACKTEST_START))
end_date = st.sidebar.date_input("結束日期", pd.to_datetime(BACKTEST_END))
top_n = st.sidebar.slider("選取標的數", 5, 50, 10)
run_btn = st.sidebar.button("執行分析")

if run_btn:
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    with st.spinner("正在獲取上市櫃股票清單..."):
        stock_info = client.all_stock_info()
        if "stock_id" not in stock_info.columns:
            stock_info = stock_info.rename(columns={"code": "stock_id"})
        stock_ids = stock_info["stock_id"].astype(str).tolist()[:50]

    with st.spinner(f"正在評分 {len(stock_ids)} 檔個股 (多執行緒)..."):
        scores = model.score_universe(stock_ids, start_str, end_str, max_workers=10)

    if scores.empty:
        st.error("無法取得評分結果，請檢查網路連線")
    else:
        name_map = stock_info[["stock_id", "stock_name"]].drop_duplicates()
        name_map["stock_id"] = name_map["stock_id"].astype(str)
        signals = generate_signals(scores)
        signals["signal"] = signals.apply(
            lambda r: "BUY" if r["rank"] <= top_n else "HOLD", axis=1
        )
        signals = signals.merge(name_map, on="stock_id", how="left")
        signals["stock_name"] = signals["stock_name"].fillna("")

        col1, col2, col3, col4, col5 = st.columns(5)
        avg_score = signals["total_score"].mean()
        buy_count = len(signals[signals["signal"] == "BUY"])
        top_row = signals.iloc[0]
        top_stock = f"{top_row['stock_id']} {top_row['stock_name']}" if not signals.empty else "N/A"
        top_score = top_row["total_score"] if not signals.empty else 0

        col1.metric("評分母數", len(signals))
        col2.metric("平均分數", f"{avg_score:.3f}")
        col3.metric("買進訊號", buy_count)
        col4.metric("最佳股票", top_stock)
        col5.metric("最高分數", f"{top_score:.3f}")

        st.subheader("評分排名表")
        display = signals[["rank", "stock_id", "stock_name", "total_score",
                           "fundamental", "institutional", "technical",
                           "warrant", "sentiment", "close_price", "signal"]].head(30)
        st.dataframe(display, use_container_width=True, hide_index=True)

        st.subheader("雷達圖 - 前 5 名")
        top5 = signals.head(5)
        fig = go.Figure()
        for _, row in top5.iterrows():
            categories = ["基本面", "籌碼面", "技術面", "權證", "市場情緒"]
            values = [row["fundamental"], row["institutional"],
                      row["technical"], row["warrant"], row["sentiment"]]
            values += values[:1]
            angles = [i * 360 / 5 for i in range(5)] + [0]
            label = f"{row['stock_id']} {row['stock_name']} ({row['total_score']:.2f})"
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                name=label,
                fill="toself",
                opacity=0.6
            ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True,
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("分數分佈")
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(x=signals["total_score"], nbinsx=30,
                                     marker_color="royalblue"))
        fig2.update_layout(
            title="Total Score Distribution",
            xaxis_title="Score",
            yaxis_title="Count",
            height=400,
        )
        st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("請在左側設定參數後，點擊「執行分析」按鈕")
    st.markdown("""
    ### 使用說明
    1. 設定分析的開始與結束日期
    2. 選擇想要選取的標的數量
    3. 點擊「執行分析」
    4. 系統將自動從 TWSE OpenAPI / FinMind 取得資料並進行多因子評分

    ### 評分維度
    - **基本面 (30%)**: 營收成長率、本益比區間、股利政策
    - **籌碼面 (25%)**: 三大法人買賣超趨勢、外資動向
    - **技術面 (20%)**: 均線排列、RSI、MACD、成交量
    - **權證情緒 (10%)**: 權證成交量變化
    - **市場情緒 (15%)**: 融資融券變化、股權集中度
    """)
