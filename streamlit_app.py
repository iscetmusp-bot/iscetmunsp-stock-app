import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# --- 0. 基礎環境設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

# 更新 Token (請確保這串字元完整且無空格)
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

# --- 1. 核心數據處理函數 ---

def get_broker_data_final(broker_id):
    """
    使用 HTTP 直接請求，解決 Token 異常與套件報錯問題
    """
    try:
        # 自動搜尋過去 10 天內最新的資料
        api_url = "https://api.finmindtrade.com/api/v4/data"
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        params = {
            "dataset": "TaiwanStockBrokerPivots",
            "data_id": broker_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": FINMIND_TOKEN
        }
        
        res = requests.get(api_url, params=params, timeout=10)
        data_json = res.json()
        
        if data_json.get("msg") != "success":
            return None, f"API 錯誤: {data_json.get('msg')}"
        
        raw_data = data_json.get("data", [])
        if not raw_data:
            return None, "此券商在過去 10 天內無買賣紀錄。"
            
        df = pd.DataFrame(raw_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 取得最後一個有資料的日期
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 轉換數值並計算買超 (張)
        df_latest['buy'] = pd.to_numeric(df_latest['buy'], errors='coerce').fillna(0)
        df_latest['sell'] = pd.to_numeric(df_latest['sell'], errors='coerce').fillna(0)
        df_latest['買超張數'] = (df_latest['buy'] - df_latest['sell']) / 1000
        
        # 只要有買就顯示 (買超 > 0)
        result = df_latest[df_latest['買超張數'] > 0].sort_values("買超張數", ascending=False)
        return result, latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        return None, f"連線異常: {str(e)}"

@st.cache_data(ttl=3600)
def get_stock_name_map():
    """抓取證交所代碼對照表"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", headers=headers, verify=False)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        name_map = {}
        for val in df['有價證券代號及名稱']:
            if '　' in str(val):
                code, name = str(val).split('　')
                if len(code) == 4: name_map[code] = name
        return name_map
    except:
        return {}

# --- 2. 介面呈現 ---

st.title("🛡️ 台股籌碼觀察站")

tab1, tab2 = st.tabs(["💎 知名分點追蹤", "📋 使用說明"])

with tab1:
    broker_dict = {
        "9268 凱基-台北": "9268",
        "9264 凱基-松山": "9264",
        "1470 摩根斯坦利": "1470",
        "8440 摩根大通": "8440",
        "1560 美商高盛": "1560",
        "9800 元大-總公司": "9800"
    }
    
    target = st.selectbox("請選擇券商分點：", list(broker_dict.keys()))
    
    if st.button("🔍 執行數據掃描", use_container_width=True):
        bid = broker_dict[target]
        with st.spinner('連線資料庫中...'):
            data, info = get_broker_data_final(bid)
            
            if data is not None and not data.empty:
                st.success(f"✅ 成功！資料日期：{info}")
                
                # 匹配名稱
                names = get_stock_name_map()
                data['股票名稱'] = data['stock_id'].apply(lambda x: names.get(x, "未知"))
                
                # 顯示結果
                st.dataframe(
                    data[['stock_id', '股票名稱', '買超張數']].rename(columns={'stock_id':'代號'}),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.error(f"❌ 掃描失敗")
                st.info(f"詳細訊息：{info}")

with tab2:
    st.markdown("""
    ### 📌 功能說明
    * **即時連線**：直接對接 FinMind API，獲取交易所每日買賣日報。
    * **自動回溯**：若今日數據尚未產出，系統會自動搜尋最近一個交易日。
    * **數據定義**：買超張數 = (總買入股數 - 總賣出股數) / 1000。
    """)
