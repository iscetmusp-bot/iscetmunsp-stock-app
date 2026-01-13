import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="台股籌碼分析 (校準版)", layout="wide")

# 驗證過的 Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

def fetch_finmind(dataset, data_id):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "data_id": data_id, "token": TOKEN}
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.status_code, res.json()
    except:
        return 999, None

st.title("🏹 台股數據深度校準")
stock_id = st.sidebar.text_input("股票代號", "2330")

if st.sidebar.button("🚀 執行多維度掃描"):
    
    # 測試 A: 分點明細 (最高權限)
    st.write("### 🔍 測試一：分點明細 (BrokerPivots)")
    s1, d1 = fetch_finmind("TaiwanStockBrokerPivots", stock_id)
    if s1 == 200:
        st.success("✅ 成功！這是最詳細的分點數據。")
        st.write(pd.DataFrame(d1['data']).head())
    else:
        st.error(f"❌ 失敗 (錯誤碼: {s1})。通常為積分不足。")

    # 測試 B: 個股日報 (中等權限)
    st.write("### 🔍 測試二：個股日報 (DailyReport)")
    s2, d2 = fetch_finmind("TaiwanStockTradingDailyReport", stock_id)
    if s2 == 200:
        st.success("✅ 成功！這是您截圖中提到的日報表。")
        st.write(pd.DataFrame(d2['data']).head())
    else:
        st.warning(f"⚠️ 失敗 (錯誤碼: {s2})。請檢查官網權限。")

st.divider()
st.info("💡 **結論**：若測試一與二皆為 422，代表問題不在資料集名稱，而是您的 Token 點數歸零。請到 FinMind 官網簽到領點數。")
