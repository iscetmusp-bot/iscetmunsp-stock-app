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
    api = DataLoader()
    api.login(token=FINMIND_TOKEN)
    return api

dl = get_loader()

# --- 1. 核心邏輯：自動追蹤有效資料 ---

def get_broker_data_debug(broker_id):
    """
    終極診斷模式：不設限抓取，並檢查 API 回傳結構
    """
    try:
        # 抓取範圍：今天往回推 14 天
        today = datetime.now()
        start_date = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        # 使用最原始的請求方式以確保穩定性
        df = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            return None, "API 回傳空白 (可能是 Token 權限或該時段 API 維護)"
        
        # 強制轉型確保運算正確
        df['date'] = pd.to_datetime(df['date'])
        df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
        df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
        
        # 找出這 14 天內最新的交易日期
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 計算買超張數 (股轉張)
        df_latest['買超張數'] = (df_latest['buy'] - df_latest['sell']) / 1000
        
        # 只要有交易就顯示，不設 50 張門檻
        result = df_latest[df_latest['買超張數'] != 0].sort_values("買超張數", ascending=False)
        
        return result, latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        return None, f"程式執行錯誤: {str(e)}"

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
    st.header("💎 知名分點進出掃描")
    
    broker_dict = {
        "9268 凱基-台北": "9268",
        "9264 凱基-松山": "9264",
        "1470 摩根斯坦利": "1470",
        "8440 摩根大通": "8440",
        "1560 美商高盛": "1560",
        "9800 元大-總公司": "9800",
        "700E 富邦-建國": "700E"
    }
    
    target_broker = st.selectbox("選擇券商分點", list(broker_dict.keys()))
    
    if st.button("🚀 開始分析", use_container_width=True):
        bid = broker_dict[target_broker]
        with st.spinner('正在與 FinMind 伺服器同步數據...'):
            data, status = get_broker_data_debug(bid)
            
            if data is not None:
                st.success(f"✅ 成功對接數據！交易日期：{status}")
                
                # 取得股票名稱映射
                sm = get_tw_stock_map()
                data['股票名稱'] = data['stock_id'].apply(lambda x: sm.get(x+".TW", sm.get(x+".TWO", "未知")))
                
                # 顯示表格
                final_df = data[['stock_id', '股票名稱', '買超張數']].rename(columns={'stock_id':'代號'})
                st.dataframe(final_df, hide_index=True, use_container_width=True)
                
                # 下載功能
                csv = final_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載此報表", csv, f"{target_broker}_{status}.csv", "text/csv")
            else:
                st.error(f"❌ 無法讀取資料")
                st.warning(f"診斷訊息：{status}")
                st.info("💡 提示：若持續出現 API 回傳空白，請確認 FinMind 官網個人面板中的 API 呼叫次數是否已達上限。")

with tab1:
    st.subheader("技術面掃描")
    st.write("請從左側調整參數後點擊按鈕。")
