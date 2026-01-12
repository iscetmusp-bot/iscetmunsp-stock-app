import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3
from FinMind.data import DataLoader

# 1. 基本設定與 Token 配置
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全能選股助手", layout="wide")

# 正確寫法：Token 是一整行長字串，前後引號對齊
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMiAxODowNTozOSIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjEwMS44LjI1LjIyOCJ9.Y507vFfYtj4EJnz6Qc8N2w47HiDDsoA_5ArA_HqPGU4"

# 緊接著這行
dl = DataLoader(token=FINMIND_TOKEN)

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

# 新增：抓取特定券商買超邏輯
def get_broker_trading(broker_name, days=3):
    try:
        # 確保日期格式正確
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        
        df_broker = dl.taiwan_stock_broker_pivots(
            broker_ids=broker_name, 
            start_date=start_date
        )
        
        # 檢查資料是否為空或包含錯誤訊息
        if df_broker is None or df_broker.empty:
            return None
        
        # 加總期間內的買賣超
        summary = df_broker.groupby("stock_id").agg({
            "buy": "sum",
            "sell": "sum"
        }).reset_index()
        
        # 計算買超張數（FinMind 單位通常是股，所以除以 1000）
        summary["買超張數"] = (summary["buy"] - summary["sell"]) / 1000
        # 只顯示買超大於 0 的標的
        return summary[summary["買超張數"] > 0].sort_values("買超張數", ascending=False)
    except Exception as e:
        st.error(f"FinMind API 呼叫失敗: {e}")
        return None

# ... (其餘原本的 process_stock 函數保持不變) ...

# --- UI 介面設計 ---

with st.sidebar:
    st.title("🛡️ 參數控制面板")
    min_vol = st.slider("最低成交量門檻 (張)", 500, 5000, 1000, step=100)

tab1, tab2, tab3 = st.tabs(["📈 技術面選股", "💎 籌碼面/券商追蹤", "📋 使用說明"])

with tab1:
    # (此處保留原本的技術面按鈕邏輯...)
    st.info("請點擊下方按鈕執行技術掃描")

with tab2:
    st.subheader("主力券商分點追蹤")
    c1, c2 = st.columns([2, 1])
    with c1:
        broker_input = st.text_input("輸入完整券商名稱 (例如: 9268 凱基-台北)", "9268 凱基-台北")
    with c2:
        lookback = st.number_input("追蹤天數", 1, 5, 1)
    
    if st.button("🔍 執行：特定券商買超掃描"):
        with st.spinner(f'正在向 FinMind 調閱 {broker_input} 的資料...'):
            # 取得券商 ID (假設格式為 "9268 凱基-台北")
            bid = broker_input.split(' ')[0]
            broker_data = get_broker_trading(bid, days=lookback)
            
            if broker_data is not None:
                stock_map = get_tw_stock_map()
                # 合併股票名稱
                broker_data['名稱'] = broker_data['stock_id'].apply(lambda x: stock_map.get(x+".TW", stock_map.get(x+".TWO", "未知")))
                st.success(f"找到 {broker_input} 近 {lookback} 天買超標的：")
                st.dataframe(broker_data[['stock_id', '名稱', '買超張數']], hide_index=True, use_container_width=True)
            else:
                st.warning("查無該券商資料，請確認券商代碼是否正確。")

with tab3:
    st.markdown("### 說明：券商代碼查詢可至證交所官網查詢（如 9268 為凱基台北）。")