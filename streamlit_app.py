import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 0. 基礎環境設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

@st.cache_resource
def get_loader():
    # 2026 最新版初始化方式：直接傳入 Token
    return DataLoader(token=FINMIND_TOKEN)

dl = get_loader()

# --- 1. 核心數據處理函數 ---

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

def get_broker_data_final_fix(broker_id):
    """
    終極解決方案：直接存取底層資料表名，避開函數遺失錯誤
    """
    try:
        # 設定回溯天數，確保抓到最新的資料
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
        
        # 核心修正：使用通用 data 請求方法請求 'TaiwanStockBrokerPivots'
        # 這是 FinMind 套件最底層、最不會變更的方法
        df = dl.fetch_data(
            dataset='TaiwanStockBrokerPivots',
            data_id=broker_id, # 這裡傳入券商代碼
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            return None, "API 回傳空白。可能該券商近期無交易，或 API Token 限制。"
        
        # 格式強制轉化
        df['date'] = pd.to_datetime(df['date'])
        df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
        df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
        
        # 抓取最新一個日期
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 計算買超張數
        df_latest['買超張數'] = (df_latest['buy'] - df_latest['sell']) / 1000
        result = df_latest[df_latest['買超張數'] > 1].sort_values("買超張數", ascending=False)
        
        return result, latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        return None, f"發生異常錯誤：{str(e)}"

# --- 2. 介面設計 ---

tab1, tab2, tab3 = st.tabs(["📈 技術分析", "💎 籌碼追蹤", "📋 說明"])

with tab2:
    st.header("💎 指標分點進出掃描")
    
    broker_dict = {
        "9268 凱基-台北": "9268",
        "9264 凱基-松山": "9264",
        "1470 摩根斯坦利": "1470",
        "8440 摩根大通": "8440",
        "1560 美商高盛": "1560",
        "9800 元大-總公司": "9800"
    }
    
    selected_name = st.selectbox("請選擇券商分點：", list(broker_dict.keys()))
    
    if st.button("🚀 執行籌碼數據分析", use_container_width=True):
        bid = broker_dict[selected_name]
        with st.spinner(f'正在讀取 {selected_name} 的數據源...'):
            data, info = get_broker_data_final_fix(bid)
            
            if data is not None and not data.empty:
                sm = get_tw_stock_map()
                data['股票名稱'] = data['stock_id'].apply(lambda x: sm.get(x+".TW", sm.get(x+".TWO", "未知")))
                
                st.success(f"✅ 抓取成功！資料日期：{info}")
                display_df = data[['stock_id', '股票名稱', '買超張數']].rename(columns={'stock_id':'代號'})
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.error("❌ 無法載入數據")
                st.warning(f"診斷報告：{info}")

with tab1:
    st.subheader("📊 技術指標掃描")
    st.write("請使用側邊欄調整參數。")
