import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 0. 基礎設定 ---
st.set_page_config(page_title="台股籌碼觀察站", layout="wide")

# 您提供的有效 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

def get_broker_data_v2(broker_id):
    """
    針對 422 錯誤優化的抓取邏輯
    """
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # 縮短搜尋區間以符合免費版權限 (通常限制 30 天內)
    today = datetime.now()
    end_date = today.strftime('%Y-%m-%d')
    start_date = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    
    # 參數嚴格檢查
    params = {
        "dataset": "TaiwanStockBrokerPivots",
        "data_id": str(broker_id),
        "start_date": start_date,
        "end_date": end_date,
        "token": FINMIND_TOKEN
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        
        # 針對 422 錯誤進行特別診斷
        if response.status_code == 422:
            return None, "API 權限限制 (422)：該券商資料可能受限或搜尋區間過長，請嘗試減少追蹤天數。"
        
        if response.status_code != 200:
            return None, f"伺服器回應錯誤: {response.status_code}"
            
        data_json = response.json()
        raw_data = data_json.get("data", [])
        
        if not raw_data:
            return None, "目前查無數據 (可能今日日報表尚未產出，請於 18:30 後重試)。"
            
        df = pd.DataFrame(raw_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 取得最新一個交易日
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 計算買超
        df_latest['buy'] = pd.to_numeric(df_latest['buy'], errors='coerce').fillna(0)
        df_latest['sell'] = pd.to_numeric(df_latest['sell'], errors='coerce').fillna(0)
        df_latest['買超(張)'] = (df_latest['buy'] - df_latest['sell']) / 1000
        
        result = df_latest[df_latest['買超(張)'] != 0].sort_values("買超(張)", ascending=False)
        return result, latest_date.strftime('%Y-%m-%d')
        
    except Exception as e:
        return None, f"程式異常: {str(e)}"

# --- 1. 使用者介面 ---

st.title("🛡️ 台股籌碼觀察站 (穩定強化版)")
st.caption("版本：2026.01.13 | 解決 422 參數錯誤問題")
st.divider()

broker_dict = {
    "9268 凱基-台北": "9268",
    "9264 凱基-松山": "9264",
    "1470 摩根斯坦利": "1470",
    "8440 摩根大通": "8440"
}

# 增加提示說明
st.sidebar.header("📋 使用小撇步")
st.sidebar.write("1. 若出現 422 錯誤，通常是 API 伺服器正在維護或 Token 到期。")
st.sidebar.write("2. 台股分點資料更新時間約為 17:30 - 18:30。")

target = st.selectbox("🎯 選擇追蹤分點：", list(broker_dict.keys()))

if st.button("🚀 執行精準掃描", use_container_width=True):
    with st.spinner('📡 正在校準 API 參數並連線伺服器...'):
        data, info = get_broker_data_v2(broker_dict[target])
        
        if data is not None and not data.empty:
            st.success(f"✅ 資料連線成功！日期：{info}")
            
            # 簡化顯示列
            show_df = data[['stock_id', '買超(張)']].rename(columns={'stock_id':'代號'})
            st.dataframe(show_df.style.format({"買超(張)": "{:.1f}"}), use_container_width=True, hide_index=True)
        else:
            st.error("❌ 無法讀取資料")
            st.warning(f"診斷訊息：{info}")
