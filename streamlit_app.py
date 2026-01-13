import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 0. 基礎設定 ---
st.set_page_config(page_title="台股籌碼觀察站", layout="wide")

# 您提供的有效 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

def get_data_direct(broker_id):
    """
    極簡連線邏輯，針對 422 錯誤進行區間壓縮
    """
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # 策略：將搜尋區間壓縮至極短的 7 天，以避開 422 權限限制
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    params = {
        "dataset": "TaiwanStockBrokerPivots",
        "data_id": str(broker_id),
        "start_date": start_date,
        "end_date": end_date,
        "token": FINMIND_TOKEN
    }

    try:
        # 加入擬人化 Headers
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        # 深度診斷 422 錯誤
        if response.status_code == 422:
            return None, "權限/參數限制 (422)。建議：1. 稍後再試 2. 登入 FinMind 確認 Token 權限是否包含分點數據。"
        
        if response.status_code != 200:
            return None, f"連線異常: {response.status_code}"
            
        data = response.json().get("data", [])
        if not data:
            return None, "區間內無交易數據 (請確認今日是否已收盤或交易所已公布資料)。"
            
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 只取最後一天的資料
        last_date = df['date'].max()
        df_last = df[df['date'] == last_date].copy()
        
        # 數值校正
        df_last['buy'] = pd.to_numeric(df_last['buy'], errors='coerce').fillna(0)
        df_last['sell'] = pd.to_numeric(df_last['sell'], errors='coerce').fillna(0)
        df_last['買超(張)'] = (df_last['buy'] - df_last['sell']) / 1000
        
        return df_last[df_last['買超(張)'] != 0].sort_values("買超(張)", ascending=False), last_date.strftime('%Y-%m-%d')
        
    except Exception as e:
        return None, f"系統報錯: {str(e)}"

# --- 1. 使用者介面 ---

st.title("🛡️ 台股籌碼觀察站 (穩定連線版)")
st.info("系統已針對 422 錯誤優化搜尋路徑。")

broker_dict = {
    "9268 凱基-台北": "9268",
    "9264 凱基-松山": "9264",
    "1470 摩根斯坦利": "1470",
    "8440 摩根大通": "8440"
}

target = st.selectbox("🎯 選擇追蹤分點：", list(broker_dict.keys()))

if st.button("🚀 開始掃描", use_container_width=True):
    with st.spinner('連線中...'):
        result, info = get_data_direct(broker_dict[target])
        
        if result is not None:
            st.success(f"✅ 讀取成功！日期：{info}")
            st.dataframe(result[['stock_id', '買超(張)']].rename(columns={'stock_id':'股票代號'}), use_container_width=True, hide_index=True)
        else:
            st.error("❌ 讀取失敗")
            st.warning(f"診斷訊息：{info}")
