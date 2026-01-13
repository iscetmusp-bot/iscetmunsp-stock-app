import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="台股籌碼分析工具 (權限解鎖版)", layout="wide")

# 您驗證成功的 Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

def safe_api_call(dataset, data_id):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "data_id": data_id, "token": TOKEN}
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.status_code, res.json()
    except:
        return 999, None

st.title("🏹 台股籌碼數據掃描器")
st.sidebar.header("📊 參數設定")
stock_id = st.sidebar.text_input("股票代號", value="2330")

if st.sidebar.button("🔍 執行深度分析"):
    with st.spinner('連線中...'):
        # 1. 抓取股價 (基礎權限測試)
        p_code, p_data = safe_api_call("TaiwanStockPrice", stock_id)
        
        if p_code == 200:
            st.success(f"📈 {stock_id} 基礎連線正常")
            df_price = pd.DataFrame(p_data['data'])
            st.line_chart(df_price.set_index('date')['close'])
            
            # 2. 抓取分點 (高階權限測試)
            b_code, b_data = safe_api_call("TaiwanStockBrokerPivots", "9268") # 凱基-台北
            
            if b_code == 200:
                st.subheader("🎯 知名分點買賣明細")
                st.dataframe(pd.DataFrame(b_data['data']), use_container_width=True)
            elif b_code == 422:
                st.error("🏮 籌碼權限受限 (HTTP 422)")
                st.info("💡 **解決方案**：請至 FinMind 官網「簽到」領取點數，或完成 Email 驗證即可解鎖分點數據。")
            else:
                st.warning(f"分點資料暫時無法讀取 (錯誤碼: {b_code})")
        else:
            st.error("Token 目前無法使用，請至 FinMind 重新產生。")

st.divider()
st.caption("備註：若股價圖有出來但分點失敗，即代表您的 Token 配置正確，僅需充值帳號點數。")
