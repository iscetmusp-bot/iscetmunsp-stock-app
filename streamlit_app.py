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
    try:
        api.login(token=FINMIND_TOKEN) # 使用最新建議語法
    except:
        api = DataLoader(token=FINMIND_TOKEN)
    return api

dl = get_loader()

# --- 1. 核心資料處理 ---

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

def get_broker_trading_final(broker_id):
    """
    終極修復：強制轉型並確保日期正確抓取
    """
    try:
        # 抓取最近 10 天
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        df_broker = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_id, 
            start_date=start_date,
            end_date=end_date
        )
        
        if df_broker is None or df_broker.empty:
            return None, "API 未回傳任何數據"
        
        # 強制將日期欄位轉為 Datetime 格式，避免比對失敗
        df_broker['date'] = pd.to_datetime(df_broker['date'])
        
        # 取得最新交易日
        latest_date = df_broker['date'].max()
        df_latest = df_broker[df_broker['date'] == latest_date].copy()
        
        # 確保 buy 和 sell 是數字格式
        df_latest['buy'] = pd.to_numeric(df_latest['buy'], errors='coerce').fillna(0)
        df_latest['sell'] = pd.to_numeric(df_latest['sell'], errors='coerce').fillna(0)
        
        # 統計買超 (買入股數 - 賣出股數)
        summary = df_latest.groupby("stock_id").agg({"buy": "sum", "sell": "sum"}).reset_index()
        summary["買超張數"] = (summary["buy"] - summary["sell"]) / 1000
        
        # 過濾買超 > 0 的股票
        result = summary[summary["買超張數"] > 1].sort_values("買超張數", ascending=False)
        
        if result.empty:
            return None, f"日期 {latest_date.date()} 有資料，但該券商當日無買超紀錄(僅賣出)。"
            
        return result, latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        return None, f"發生錯誤: {str(e)}"

# --- 2. 介面設計 ---

tab1, tab2, tab3 = st.tabs(["📈 技術面選股", "💎 籌碼面/券商追蹤", "📋 使用說明"])

with tab2:
    st.subheader("💎 主力券商分點追蹤")
    broker_dict = {
        "9268 凱基-台北": "9268", "9264 凱基-松山": "9264", "1470 摩根斯坦利": "1470", 
        "8440 摩根大通": "8440", "1560 美商高盛": "1560", "9800 元大-總公司": "9800",
        "700E 富邦-建國": "700E", "5850 國票-敦北法人": "5850"
    }
    selected_name = st.selectbox("請選擇指標券商：", list(broker_dict.keys()))
    
    if st.button("🔍 開始分析籌碼數據", use_container_width=True):
        bid = broker_dict[selected_name]
        with st.spinner('數據計算中...'):
            data, info = get_broker_trading_final(bid)
            
            if data is not None:
                sm = get_tw_stock_map()
                data['名稱'] = data['stock_id'].apply(lambda x: sm.get(x+".TW", sm.get(x+".TWO", "未知")))
                st.success(f"✅ 成功找到數據！日期：{info}")
                st.dataframe(data[['stock_id', '名稱', '買超張數']].rename(columns={'stock_id':'代號'}), hide_index=True, use_container_width=True)
            else:
                st.error(f"⚠️ 無法顯示資料：{info}")

with tab1:
    # (此處放你原本的技術分析代碼即可)
    st.write("請執行技術分析...")
