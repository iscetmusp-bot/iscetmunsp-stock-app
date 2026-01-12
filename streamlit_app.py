import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3
from FinMind.data import DataLoader

# --- 0. 基本設定與 Token 配置 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

# 請確保此 Token 有效
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

try:
    dl = DataLoader()
    dl.login_token(FINMIND_TOKEN)
except:
    # 備用登入語法
    dl = DataLoader(token=FINMIND_TOKEN)

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
        prev2_close = hist['Close'].iloc[-3]
        volume_lots = hist['Volume'].iloc[-1] / 1000
        
        if volume_lots < min_vol: return None
        
        # 邏輯 A：強勢連漲
        cond_strong = last_close > prev_close and prev_close > prev2_close
        
        # 邏輯 B：突破季線
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        last_ma60 = hist['MA60'].iloc[-1]
        prev_ma60 = hist['MA60'].iloc[-2]
        cond_ma60 = last_close > last_ma60 and prev_close <= prev_ma60
        
        res_data = {
            "代號": ticker.split('.')[0], "名稱": name, 
            "收盤價": round(last_close, 2), 
            "漲幅(%)": round(((last_close-prev_close)/prev_close)*100, 2),
            "成交量(張)": int(volume_lots)
        }

        if mode == "強勢股" and cond_strong: return res_data
        if mode == "突破季線" and cond_ma60: 
            res_data["季線位置"] = round(last_ma60, 2)
            return res_data
    except: return None
    return None

def get_broker_trading(broker_id, days=1):
    try:
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        df_broker = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_id, 
            start_date=start_date
        )
        if df_broker is None or df_broker.empty: return None
        
        summary = df_broker.groupby("stock_id").agg({"buy": "sum", "sell": "sum"}).reset_index()
        summary["買超張數"] = (summary["buy"] - summary["sell"]) / 1000
        return summary[summary["買超張數"] > 0].sort_values("買超張數", ascending=False)
    except: return None

# --- 2. UI 介面設計 ---

with st.sidebar:
    st.title("🛡️ 參數控制面板")
    min_vol = st.slider("最低成交量門檻 (張)", 500, 5000, 1000, step=100)
    st.divider()
    st.caption("建議收盤後 (17:30) 再執行籌碼掃描")

tab1, tab2, tab3 = st.tabs(["📈 技術面選股", "💎 籌碼面/券商追蹤", "📋 使用說明"])

with tab1:
    st.subheader("📈 技術分析條件篩選")
    # 垂直排列按鈕，方便手機操作
    if st.button("🔥 執行：強勢連漲股", use_container_width=True):
        stock_map = get_tw_stock_map()
        results = []
        with st.spinner('掃描全台股中...'):
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = [executor.submit(process_stock, t, n, "強勢股", min_vol) for t, n in stock_map.items()]
                results = [f.result() for f in futures if f.result()]
        if results:
            st.dataframe(pd.DataFrame(results).sort_values("漲幅(%)", ascending=False), hide_index=True, use_container_width=True)
        else: st.warning("今日無符合標的")

    if st.button("🚀 執行：突破季線股", use_container_width=True):
        stock_map = get_tw_stock_map()
        results = []
        with st.spinner('正在計算突破季線標的...'):
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = [executor.submit(process_stock, t, n, "突破季線", min_vol) for t, n in stock_map.items()]
                results = [f.result() for f in futures if f.result()]
        if results:
            st.dataframe(pd.DataFrame(results).sort_values("漲幅(%)", ascending=False), hide_index=True, use_container_width=True)
        else: st.warning("今日無符合標的")

with tab2:
    st.subheader("💎 主力券商分點追蹤")
    
    # 2025 隔日沖與大戶名單
    broker_dict = {
        "9268 凱基-台北": "9268",
        "9264 凱基-松山": "9264",
        "1470 摩根斯坦利": "1470",
        "8440 摩根大通": "8440",
        "1560 美商高盛": "1560",
        "9800 元大-總公司": "9800",
        "700E 富邦-建國": "700E",
        "5850 國票-敦北法人": "5850",
        "7006 元大-土城永寧": "7006",
        "其他 (手動輸入代碼)": "custom"
    }
    
    selected_name = st.selectbox("請選擇追蹤券商：", list(broker_dict.keys()))
    
    if selected_name == "其他 (手動輸入代碼)":
        broker_id = st.text_input("請輸入 4 位數券商代碼", "")
    else:
        broker_id = broker_dict[selected_name]
    
    lookback = st.slider("追蹤天數", 1, 5, 1)
    
    if st.button("🔍 執行：特定券商買超掃描", use_container_width=True):
        if not broker_id:
            st.error("請提供券商代碼")
        else:
            with st.spinner(f'正在向 FinMind 查詢 {selected_name} 的數據...'):
                broker_data = get_broker_trading(broker_id, days=lookback)
                
                if broker_data is not None and not broker_data.empty:
                    stock_map = get_tw_stock_map()
                    broker_data['名稱'] = broker_data['stock_id'].apply(lambda x: stock_map.get(x+".TW", stock_map.get(x+".TWO", "未知")))
                    
                    st.success(f"✅ 找到 {selected_name} 近期的買超標的：")
                    st.dataframe(
                        broker_data[['stock_id', '名稱', '買超張數']].rename(columns={'stock_id': '代號'}),
                        hide_index=True, 
                        use_container_width=True
                    )
                else:
                    st.warning("⚠️ 該券商近期無買超資料。請確認是否為開盤日，或增加追蹤天數。")

with tab3:
    st.markdown("""
    ### 📖 快速功能說明
    1. **強勢連漲股**：篩選成交量 > 設定值，且股價連二漲。
    2. **突破季線股**：找出今天收盤價剛站上 60MA 的轉強標的。
    3. **籌碼面追蹤**：直接點選知名「隔日沖」券商（如 9268 凱基台北），觀察其近期買超動向。
    """)