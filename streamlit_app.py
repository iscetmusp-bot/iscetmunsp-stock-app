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

# FinMind API Token
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

@st.cache_resource
def get_loader():
    """初始化並登入 FinMind 資料庫"""
    api = DataLoader()
    try:
        # 修正：目前版本標準登入語法
        api.login(token=FINMIND_TOKEN)
    except:
        # 相容性回退語法
        api = DataLoader(token=FINMIND_TOKEN)
    return api

dl = get_loader()

# --- 1. 核心資料抓取與處理函數 ---

@st.cache_data(ttl=3600)
def get_tw_stock_map():
    """抓取全台股代碼與名稱對照表"""
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
    """技術面過濾邏輯"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="100d")
        if len(hist) < 65: return None
        
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        prev2_close = hist['Close'].iloc[-3]
        volume_lots = hist['Volume'].iloc[-1] / 1000
        
        if volume_lots < min_vol: return None
        
        # 邏輯 A：強勢連漲股
        if mode == "強勢股":
            if last_close > prev_close and prev_close > prev2_close:
                return {
                    "代號": ticker.split('.')[0], 
                    "名稱": name, 
                    "收盤價": round(last_close, 2), 
                    "漲幅(%)": round(((last_close-prev_close)/prev_close)*100, 2),
                    "成交量(張)": int(volume_lots)
                }
        
        # 邏輯 B：突破季線股
        if mode == "突破季線":
            ma60 = hist['Close'].rolling(window=60).mean()
            if last_close > ma60.iloc[-1] and prev_close <= ma60.iloc[-2]:
                return {
                    "代號": ticker.split('.')[0], 
                    "名稱": name, 
                    "收盤價": round(last_close, 2), 
                    "漲幅(%)": round(((last_close-prev_close)/prev_close)*100, 2),
                    "成交量(張)": int(volume_lots),
                    "季線位置": round(ma60.iloc[-1], 2)
                }
    except: return None
    return None

def get_broker_trading(broker_id):
    """抓取特定券商分點最新交易數據"""
    try:
        # 設定較寬的抓取範圍 (最近 10 天)，確保能抓到最新的交易日
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        df_broker = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_id, 
            start_date=start_date,
            end_date=end_date
        )
        
        if df_broker is None or df_broker.empty:
            return None
        
        # 自動鎖定最新的一個交易日
        latest_date = df_broker['date'].max()
        df_latest = df_broker[df_broker['date'] == latest_date]
        
        # 計算買超張數
        summary = df_latest.groupby("stock_id").agg({"buy": "sum", "sell": "sum"}).reset_index()
        summary["買超張數"] = (summary["buy"] - summary["sell"]) / 1000
        
        # 過濾買超大於 50 張的股票
        result = summary[summary["買超張數"] > 50].sort_values("買超張數", ascending=False)
        return result, latest_date
    except:
        return None, None

# --- 2. 介面佈局 ---

with st.sidebar:
    st.title("🛡️ 參數控制面板")
    min_vol = st.slider("最低成交量門檻 (張)", 500, 5000, 1000, step=100)
    st.divider()
    st.caption("技術指標使用 Yahoo Finance 資料")
    st.caption("籌碼指標使用 FinMind 資料")

tab1, tab2, tab3 = st.tabs(["📈 技術面選股", "💎 籌碼面/券商追蹤", "📋 使用說明"])

with tab1:
    st.subheader("📈 技術分析篩選")
    # 手機版優化：按鈕填滿寬度
    c1, c2 = st.columns(2)
    with c1: btn_s = st.button("🔥 執行：強勢連漲股", use_container_width=True)
    with c2: btn_m = st.button("🚀 執行：突破季線股", use_container_width=True)
    
    if btn_s or btn_m:
        mode = "強勢股" if btn_s else "突破季線"
        stock_map = get_tw_stock_map()
        with st.spinner(f'正在掃描台股 {mode} 標的...'):
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(process_stock, t, n, mode, min_vol) for t, n in stock_map.items()]
                results = [f.result() for f in futures if f.result()]
        
        if results:
            st.success(f"掃描完成，符合條件共 {len(results)} 檔")
            st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)
        else:
            st.warning("查無符合條件之股票，請調整成交量門檻。")

with tab2:
    st.subheader("💎 主力券商分點追蹤")
    # 常用隔日沖與大戶名單
    broker_dict = {
        "9268 凱基-台北": "9268", 
        "9264 凱基-松山": "9264", 
        "1470 摩根斯坦利": "1470", 
        "8440 摩根大通": "8440", 
        "1560 美商高盛": "1560", 
        "9800 元大-總公司": "9800",
        "700E 富邦-建國": "700E", 
        "5850 國票-敦北法人": "5850", 
        "7006 元大-土城永寧": "7006"
    }
    selected_name = st.selectbox("請選擇要追蹤的指標券商：", list(broker_dict.keys()))
    
    if st.button("🔍 開始分析籌碼數據", use_container_width=True):
        broker_id = broker_dict[selected_name]
        with st.spinner(f'正在調閱 {selected_name} 的最新成交明細...'):
            broker_data, latest_date = get_broker_trading(broker_id)
            
            if broker_data is not None and not broker_data.empty:
                sm = get_tw_stock_map()
                broker_data['名稱'] = broker_data['stock_id'].apply(lambda x: sm.get(x+".TW", sm.get(x+".TWO", "未知")))
                
                st.success(f"✅ 成功抓取數據：{selected_name}")
                st.info(f"📅 資料日期：{latest_date} (系統已自動定位至最新交易日)")
                
                # 顯示表格
                display_df = broker_data[['stock_id', '名稱', '買超張數']].rename(columns={'stock_id':'代號'})
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.error("⚠️ 查無數據。原因可能為：1. 該券商今日無大型進出。 2. 交易所尚未產出數據 (通常為 17:30)。")

with tab3:
    st.markdown("""
    ### 📖 功能與邏輯說明
    1. **強勢連漲股**：今日收盤 > 昨日收盤 > 前日收盤，代表短期動能強勁。
    2. **突破季線股**：收盤價「由下往上」穿過 60 日移動平均線 (60MA)，是中長期趨勢轉強的訊號。
    3. **券商分點追蹤**：
        * 數據源自證交所每日買賣日報表。
        * 已自動過濾買超低於 50 張的雜訊。
        * 系統會自動回溯最近一個有開盤的交易日。
    """)