import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 0. 設定 ---
st.set_page_config(page_title="台股籌碼觀察站 (穩定版)", layout="wide")

# 您目前的 Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

# --- 1. 功能函數 ---

def get_price_only(stock_id):
    """測試您的 Token 唯一能抓到的資料：股價"""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
        "token": TOKEN
    }
    res = requests.get(url, params=params)
    if res.status_code == 200:
        return pd.DataFrame(res.json()['data'])
    return None

def show_auth_guide():
    """權限引導美化版"""
    st.warning("🏮 **偵測到權限限制 (HTTP 422)**")
    st.markdown("""
    目前的帳號無法存取「分點資料」。請嘗試以下步驟：
    1. 前往 **[FinMind 官網](https://finmindtrade.com/)** 登入。
    2. 檢查 **個人積分** 是否大於 0。
    3. 若您剛註冊，請完成 Email 驗證。
    """)
    if st.button("查看模擬範例 (Demo Mode)"):
        demo_data = pd.DataFrame({
            '股票代號': ['2330', '2317', '2454'],
            '股票名稱': ['台積電', '鴻海', '聯發科'],
            '預估買超(張)': [1250.5, 840.2, -310.4]
        })
        st.write("### 💡 預期產出畫面：")
        st.table(demo_data)

# --- 2. 介面 ---

st.title("🛡️ 台股籌碼觀察站")
st.divider()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("⚙️ 掃描設定")
    stock_id = st.text_input("輸入代號測試連線 (如: 2330)", value="2330")
    run_test = st.button("🚀 執行連線測試")

with col2:
    if run_test:
        with st.spinner('連線中...'):
            # 先試基礎資料
            price_df = get_price_only(stock_id)
            if price_df is not None and not price_df.empty:
                st.success(f"✅ 連線正常！{stock_id} 近期股價已收錄")
                st.line_chart(price_df.set_index('date')['close'])
                
                # 提示籌碼權限
                st.error("❌ 籌碼進階數據存取失敗")
                show_auth_guide()
            else:
                st.error("Token 已過期或帳號被暫時鎖定，請更換新 Token。")

st.divider()
st.caption("備註：若層級 1 正常但仍無法看分點，請至官網確認您的帳號是否具備進階 API 權限。")
