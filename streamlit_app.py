import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# --- 0. 基本環境設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股籌碼觀察站", layout="wide")

# 使用您最新的 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

# --- 1. 核心智能抓取函數 ---

def get_broker_data_smart_search(broker_id):
    """
    智能搜尋：若當日無資料，自動往回追溯至有資料為止
    """
    api_url = "https://api.finmindtrade.com/api/v4/data"
    
    # 搜尋最近 30 天
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    params = {
        "dataset": "TaiwanStockBrokerPivots",
        "data_id": broker_id,
        "start_date": start_date,
        "end_date": end_date,
        "token": FINMIND_TOKEN
    }

    try:
        res = requests.get(api_url, params=params, timeout=15)
        data_json = res.json()
        
        if data_json.get("msg") != "success":
            return None, f"API 拒絕請求: {data_json.get('msg')}"
        
        df = pd.DataFrame(data_json.get("data", []))
        
        if df.empty:
            return None, "資料庫搜尋區間內查無數據。"

        # 核心邏輯：找出這份資料中「最新」的日期
        df['date'] = pd.to_datetime(df['date'])
        actual_latest_date = df['date'].max()
        
        # 僅取出最後一天的資料
        df_final = df[df['date'] == actual_latest_date].copy()
        
        # 數值轉型與計算
        df_final['buy'] = pd.to_numeric(df_final['buy'], errors='coerce').fillna(0)
        df_final['sell'] = pd.to_numeric(df_final['sell'], errors='coerce').fillna(0)
        df_final['買超(張)'] = (df_final['buy'] - df_final['sell']) / 1000
        
        # 排序
        result = df_final[df_final['買超(張)'] != 0].sort_values("買超(張)", ascending=False)
        return result, actual_latest_date.strftime('%Y-%m-%d')

    except Exception as e:
        return None, f"連線失敗: {str(e)}"

@st.cache_data(ttl=3600)
def get_name_map():
    try:
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", timeout=10)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        return {str(val).split('　')[0]: str(val).split('　')[1] for val in df['有價證券代號及名稱'] if '　' in str(val)}
    except:
        return {}

# --- 2. 介面設計 ---

st.title("🛡️ 台股籌碼觀察站 (智能修復版)")
st.info("系統會自動抓取交易所最新產出的分點資料（若今日尚未更新，則顯示昨日數據）。")

broker_dict = {
    "9268 凱基-台北": "9268", "9264 凱基-松山": "9264", 
    "1470 摩根斯坦利": "1470", "8440 摩根大通": "8440"
}

target = st.selectbox("🎯 選擇分點：", list(broker_dict.keys()))

if st.button("🚀 執行智能掃描", use_container_width=True):
    with st.spinner('正在分析資料庫庫存...'):
        data, date_info = get_broker_data_smart_search(broker_dict[target])
        
        if data is not None:
            st.success(f"✅ 成功找到資料！實際日期：{date_info}")
            
            names = get_name_map()
            data['股票名稱'] = data['stock_id'].apply(lambda x: names.get(str(x), "未知"))
            
            # 美化表格
            show_df = data[['stock_id', '股票名稱', '買超(張)']].rename(columns={'stock_id':'代號'})
            st.dataframe(show_df.style.format({"買超(張)": "{:.1f}"}), hide_index=True, use_container_width=True)
        else:
            st.error(f"❌ 無法讀取資料: {date_info}")

st.divider()
st.caption("提示：若多次出現 None，代表 FinMind 伺服器暫時繁忙，請間隔 1 分鐘再按一次。")
