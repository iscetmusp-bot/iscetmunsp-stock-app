import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3

# 1. 基本設定與安全性修正
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

# 自定義 CSS 讓表格更好看
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 核心功能函數 ---

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
        # 為了計算季線，抓取 100 天資料
        hist = stock.history(period="100d")
        if len(hist) < 65: return None
        
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        prev2_close = hist['Close'].iloc[-3]
        volume_lots = hist['Volume'].iloc[-1] / 1000
        
        # 基本過濾：成交量
        if volume_lots < min_vol: return None
        
        # 邏輯 A：強勢連漲
        cond_strong = last_close > prev_close and prev_close > prev2_close
        
        # 邏輯 B：突破季線 (MA60)
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        last_ma60 = hist['MA60'].iloc[-1]
        prev_ma60 = hist['MA60'].iloc[-2]
        cond_ma60 = last_close > last_ma60 and prev_close <= prev_ma60
        
        res_data = {
            "代號": ticker.split('.')[0], "名稱": name, 
            "收盤價": round(last_close, 2), "漲幅(%)": round(((last_close-prev_close)/prev_close)*100, 2),
            "成交量(張)": int(volume_lots)
        }

        if mode == "強勢股" and cond_strong: return res_data
        if mode == "突破季線" and cond_ma60: 
            res_data["季線位置"] = round(last_ma60, 2)
            return res_data
    except: return None
    return None

# --- UI 介面設計 ---

# 側邊欄
with st.sidebar:
    st.title("🛡️ 參數控制面板")
    st.divider()
    min_vol = st.slider("最低成交量門檻 (張)", 500, 5000, 1000, step=100)
    st.info("調整上方數值後，再點擊右側分頁中的按鈕執行掃描。")
    st.write("---")
    st.caption("數據來源: Yahoo Finance / TWSE")

# 主畫面分頁
tab1, tab2, tab3 = st.tabs(["📈 技術面選股", "💎 籌碼面/券商追蹤", "📋 使用說明"])

with tab1:
    st.subheader("技術分析條件篩選")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔥 執行：強勢連漲股"):
            stock_map = get_tw_stock_map()
            results = []
            with st.spinner('掃描全台股中...'):
                with ThreadPoolExecutor(max_workers=15) as executor:
                    futures = [executor.submit(process_stock, t, n, "強勢股", min_vol) for t, n in stock_map.items()]
                    results = [f.result() for f in futures if f.result()]
            if results:
                st.dataframe(pd.DataFrame(results).sort_values("漲幅(%)", ascending=False), hide_index=True, use_container_width=True)
            else: st.warning("今日無符合標的")

    with col2:
        if st.button("🚀 執行：突破季線股"):
            stock_map = get_tw_stock_map()
            results = []
            with st.spinner('計算季線位置中...'):
                with ThreadPoolExecutor(max_workers=15) as executor:
                    futures = [executor.submit(process_stock, t, n, "突破季線", min_vol) for t, n in stock_map.items()]
                    results = [f.result() for f in futures if f.result()]
            if results:
                st.dataframe(pd.DataFrame(results).sort_values("漲幅(%)", ascending=False), hide_index=True, use_container_width=True)
            else: st.warning("今日無符合標的")

with tab2:
    st.subheader("主力籌碼與分點追蹤")
    st.info("此功能正在串接資料來源，目前可先行設定參數。")
    
    c1, c2 = st.columns(2)
    with c1:
        broker_name = st.text_input("輸入追蹤券商 (如: 凱基-台北)", "")
    with c2:
        buy_days = st.number_input("連續買超天數", 1, 10, 3)
    
    if st.button("🔍 執行：特定券商進出掃描 (測試中)"):
        if not broker_name:
            st.error("請先輸入券商名稱")
        else:
            st.write(f"正在模擬查詢 {broker_name} 的交易數據...")
            st.warning("提醒：此功能需串接 FinMind API，請確認已在 requirements.txt 加入 FinMind。")

with tab3:
    st.markdown("""
    ### 介面說明
    1. **側邊欄**：統一設定篩選的「基本量能」，避免選到流動性不足的殭屍股。
    2. **技術面分頁**：
        * **強勢連漲**：收盤價連續兩天上升。
        * **突破季線**：當日收盤價由下往上穿過 60MA，代表趨勢轉強。
    3. **籌碼面分頁**：未來將加入特定券商(分點)的買賣超數據對齊。
    """)
