import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 0. 基本設定與 Token 配置 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

@st.cache_resource
def get_loader():
    api = DataLoader()
    api.login_token(FINMIND_TOKEN)
    return api

dl = get_loader()

# --- 1. 核心資料抓取函數 ---

@st.cache_data(ttl=3600)
def get_tw_stock_map():
    headers = {'User-Agent': 'Mozilla/5.0'}
    urls = [("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", ".TW"), 
            ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", ".TWO")]
    stock_map = {}
    for url, suffix in urls:
        try:
            res = requests.get(url, headers=headers, verify=False)
            df = pd.read_html(res.text)[0]
            df.columns = df.iloc[0]
            df = df.iloc[2:]
            for val in df['有價證券代號及名稱']:
                if '　' in str(val):
                    code, name = str(val).split('　')
                    if len(code) == 4: stock_map[code + suffix] = name
        except: pass
    return stock_map

def process_stock(ticker, name, mode, min_vol):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="100d")
        if len(hist) < 65: return None
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        volume_lots = hist['Volume'].iloc[-1] / 1000
        if volume_lots < min_vol: return None
        
        # 邏輯判斷
        if mode == "強勢股" and last_close > prev_close and prev_close > hist['Close'].iloc[-3]:
            return {"代號": ticker.split('.')[0], "名稱": name, "收盤價": round(last_close, 2), "漲幅(%)": round(((last_close-prev_close)/prev_close)*100, 2), "成交量(張)": int(volume_lots)}
        
        if mode == "突破季線":
            ma60 = hist['Close'].rolling(window=60).mean()
            if last_close > ma60.iloc[-1] and prev_close <= ma60.iloc[-2]:
                return {"代號": ticker.split('.')[0], "名稱": name, "收盤價": round(last_close, 2), "漲幅(%)": round(((last_close-prev_close)/prev_close)*100, 2), "成交量(張)": int(volume_lots)}
    except: return None
    return None

def get_broker_trading(broker_id, lookback_days=1):
    try:
        # 自動向前追溯，確保抓到有開盤的日期
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=lookback_days + 3)).strftime('%Y-%m-%d')
        
        df_broker = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_id, 
            start_date=start_date,
            end_date=end_date
        )
        
        if df_broker is None or df_broker.empty:
            return None
        
        # 依照日期排序，取最後一筆有效日期
        latest_date = df_broker['date'].max()
        df_latest = df_broker[df_broker['date'] == latest_date]
        
        summary = df_latest.groupby("stock_id").agg({"buy": "sum", "sell": "sum"}).reset_index()
        summary["買超張數"] = (summary["buy"] - summary["sell"]) / 1000
        return summary[summary["買超張數"] > 50].sort_values("買超張數", ascending=False) # 過濾小量買超
    except: return None

# --- 2. UI 介面設計 ---

with st.sidebar:
    st.title("🛡️ 參數控制面板")
    min_vol = st.slider("最低成交量門檻 (張)", 500, 5000, 1000, step=100)

tab1, tab2, tab3 = st.tabs(["📈 技術面選股", "💎 籌碼面/券商追蹤", "📋 使用說明"])

with tab1:
    st.subheader("📈 技術分析條件篩選")
    c1, c2 = st.columns(2)
    with c1: btn_s = st.button("🔥 執行：強勢連漲股", use_container_width=True)
    with c2: btn_m = st.button("🚀 執行：突破季線股", use_container_width=True)
    
    if btn_s or btn_m:
        mode = "強勢股" if btn_s else "突破季線"
        stock_map = get_tw_stock_map()
        with st.spinner(f'正在分析台股 {mode}...'):
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(process_stock, t, n, mode, min_vol) for t, n in stock_map.items()]
                results = [f.result() for f in futures if f.result()]
        if results: st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)
        else: st.warning("今日無符合標的")

with tab2:
    st.subheader("💎 主力券商分點追蹤")
    broker_dict = {
        "9268 凱基-台北": "9268", "9264 凱基-松山": "9264", "1470 摩根斯坦利": "1470", 
        "8440 摩根大通": "8440", "1560 美商高盛": "1560", "9800 元大-