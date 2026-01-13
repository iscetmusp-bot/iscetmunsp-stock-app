import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 0. 基礎設定 ---
st.set_page_config(page_title="台股籌碼觀察站 (穩定法人版)", layout="wide")

# 您提供的有效 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

def get_institutional_data(stock_id):
    """
    抓取三大法人買賣超，避開分點資料的 422 權限限制
    """
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # 搜尋最近 10 天
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    params = {
        "dataset": "InstitutionalInvestorsBuySell",
        "data_id": str(stock_id),
        "start_date": start_date,
        "end_date": end_date,
        "token": FINMIND_TOKEN
    }

    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code != 200:
            return None, f"連線錯誤: {res.status_code}"
            
        data = res.json().get("data", [])
        if not data:
            return None, "查無此標的近期法人資料。"
            
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 整理數據：將不同法人的買賣超彙整
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        return df_latest, latest_date.strftime('%Y-%m-%d')
        
    except Exception as e:
        return None, f"異常: {str(e)}"

# --- 1. 使用者介面 ---

st.title("🛡️ 台股籌碼觀察站 (法人動態版)")
st.info("由於分點資料權限受限 (422)，本版改由追蹤『三大法人』資金流向。")

# 提供熱門標的供測試
test_stocks = {
    "2330 台積電": "2330",
    "2317 鴻海": "2317",
    "2454 聯發科": "2454",
    "2603 長榮": "2603"
}

target_stock = st.selectbox("🎯 選擇追蹤標的：", list(test_stocks.keys()))

if st.button("🚀 開始掃描籌碼", use_container_width=True):
    with st.spinner('連線伺服器中...'):
        result, info = get_institutional_data(test_stocks[target_stock])
        
        if result is not None:
            st.success(f"✅ 讀取成功！資料日期：{info}")
            
            # 整理輸出表格
            final_df = result[['name', 'buy', 'sell']].copy()
            final_df['買超(張)'] = (pd.to_numeric(final_df['buy']) - pd.to_numeric(final_df['sell'])) / 1000
            
            st.table(final_df[['name', '買超(張)']].rename(columns={'name':'法人名稱'}))
        else:
            st.error("❌ 讀取失敗")
            st.warning(f"診斷訊息：{info}")
            st.info("💡 建議：若仍出現錯誤，代表您的 Token 在此時段呼叫頻率已達上限。")
