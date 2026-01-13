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

# 固定使用你的 Token
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

@st.cache_resource
def get_loader():
    """修正：2026 年 DataLoader 初始化標準方式，不呼叫 .login()"""
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

def get_broker_data_safe(broker_id):
    """
    修正：使用通用 data_id 請求方式，解決函數不存在的問題
    """
    try:
        # 設定回溯 10 天確保抓到數據
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        # 修正：目前最穩定的請求方式是透過通用介面抓取台灣分點數據
        df = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            return None, "API 未回傳數據，請確認 Token 額度或日期"
        
        # 數據清理與格式轉換
        df['date'] = pd.to_datetime(df['date'])
        df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
        df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
        
        # 定位最新交易日
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 計算買超張數
        df_latest['買超張數'] = (df_latest['buy'] - df_latest['sell']) / 1000
        result = df_latest[df_latest['買超張數'] > 1].sort_values("買超張數", ascending=False)
        
        return result, latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        return None, f"發生錯誤：{str(e)}"

# --- 2. 介面設計 ---

tab1, tab2, tab3 = st.tabs(["📈 技術分析", "💎 籌碼追蹤", "📋 說明"])

with tab2:
    st.header("💎 知名分點進出掃描")
    
    broker_dict = {
        "9268 凱基-台北": "9268",
        "9264 凱基-松山": "9264",
        "1470 摩根斯坦利": "1470",
        "8440 摩根大通": "8440",
        "1560 美商高盛": "1560",
        "9800 元大-總公司": "9800"
    }
    
    selected_name = st.selectbox("請選擇指標券商：", list(broker_dict.keys()))
    
    if st.button("🚀 開始掃描籌碼", use_container_width=True):
        bid = broker_dict[selected_name]
        with st.spinner(f'正在調閱 {selected_name} 的成交明細...'):
            data, info = get_broker_data_safe(bid)
            
            if data is not None and not data.empty:
                sm = get_tw_stock_map()
                data['股票名稱'] = data['stock_id'].apply(lambda x: sm.get(x+".TW", sm.get(x+".TWO", "未知")))
                
                st.success(f"✅ 成功抓取！資料日期：{info}")
                display_df = data[['stock_id', '股票名稱', '買超張數']].rename(columns={'stock_id':'代號'})
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.error(f"❌ 無法讀取資料")
                st.info(f"詳細診斷：{info}")

with tab1:
    st.info("請點擊側邊欄調整參數或按鈕執行掃描")
