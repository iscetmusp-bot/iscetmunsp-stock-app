import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# --- 0. 基礎環境設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

# 固定使用你的 Token
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

# --- 1. 核心數據處理函數 (使用 API URL 直接請求) ---

def get_broker_data_via_api(broker_id):
    """
    不使用 DataLoader 函數，直接透過 HTTP 請求 FinMind API 伺服器
    """
    try:
        # 設定回溯 14 天
        end_date = (datetime.now()).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
        
        # 直接呼叫 API 網址
        api_url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockBrokerPivots",
            "data_id": broker_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": FINMIND_TOKEN
        }
        
        res = requests.get(api_url, params=params)
        data_json = res.json()
        
        if data_json.get("msg") != "success" or not data_json.get("data"):
            return None, f"API 請求失敗: {data_json.get('msg', '無數據')}"
        
        df = pd.DataFrame(data_json["data"])
        
        # 格式轉換
        df['date'] = pd.to_datetime(df['date'])
        df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
        df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
        
        # 抓取最新一個日期
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 計算買超張數
        df_latest['買超張數'] = (df_latest['buy'] - df_latest['sell']) / 1000
        result = df_latest[df_latest['買超張數'] > 0].sort_values("買超張數", ascending=False)
        
        return result, latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        return None, f"連線異常: {str(e)}"

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

# --- 2. 介面設計 ---

tab1, tab2, tab3 = st.tabs(["📈 技術選股", "💎 籌碼追蹤", "📋 說明"])

with tab2:
    st.header("💎 知名分點進出掃描 (API 直接連線版)")
    
    broker_dict = {
        "9268 凱基-台北": "9268", "9264 凱基-松山": "9264", "1470 摩根斯坦利": "1470", 
        "8440 摩根大通": "8440", "1560 美商高盛": "1560", "9800 元大-總公司": "9800"
    }
    
    selected_name = st.selectbox("請選擇券商分點：", list(broker_dict.keys()))
    
    if st.button("🚀 執行籌碼分析", use_container_width=True):
        bid = broker_dict[selected_name]
        with st.spinner('連線中...'):
            data, info = get_broker_data_via_api(bid)
            
            if data is not None and not data.empty:
                sm = get_tw_stock_map()
                data['股票名稱'] = data['stock_id'].apply(lambda x: sm.get(x+".TW", sm.get(x+".TWO", "未知")))
                st.success(f"✅ 抓取成功！交易日期：{info}")
                display_df = data[['stock_id', '股票名稱', '買超張數']].rename(columns={'stock_id':'代號'})
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.error(f"❌ 無法讀取資料: {info}")

with tab1:
    st.write("技術掃描功能開發中...")
