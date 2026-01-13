import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="API 權限終極診斷", layout="wide")

# 您最新的 Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

st.title("🧪 API 權限深度診斷工具")
st.write("本工具將測試您的 Token 實際可存取的資料層級。")

def test_api_permission(dataset, data_id):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": dataset,
        "data_id": data_id,
        "start_date": (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
        "token": TOKEN
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.status_code, res.json()
    except Exception as e:
        return 999, str(e)

if st.button("🔍 開始權限檢測 (測試三種資料層級)"):
    
    # 層級 1: 基礎資料 (門檻最低)
    st.subheader("層級 1：基礎股價 (TaiwanStockPrice)")
    code1, res1 = test_api_permission("TaiwanStockPrice", "2330")
    if code1 == 200 and res1.get("data"):
        st.success("✅ 基礎權限：正常")
    else:
        st.error(f"❌ 基礎權限失敗：HTTP {code1}")
        st.json(res1)

    # 層級 2: 法人籌碼 (中等門檻)
    st.subheader("層級 2：法人動態 (InstitutionalInvestorsBuySell)")
    code2, res2 = test_api_permission("InstitutionalInvestorsBuySell", "2330")
    if code2 == 200 and res2.get("data"):
        st.success("✅ 法人權限：正常")
    else:
        st.warning(f"⚠️ 法人權限受限：HTTP {code2}")
        st.write("原因：您的帳號積分可能不足，或 Token 需重新產生。")

    # 層級 3: 分點資料 (最高門檻)
    st.subheader("層級 3：分點明細 (TaiwanStockBrokerPivots)")
    code3, res3 = test_api_permission("TaiwanStockBrokerPivots", "9268")
    if code3 == 200 and res3.get("data"):
        st.success("✅ 分點權限：正常")
    else:
        st.error(f"🚫 分點權限拒絕：HTTP {code3}")
        st.write("這就是導致您先前 422 錯誤的主因。")

st.divider()
st.write("💡 **後續行動建議**：")
st.write("1. 如果連『層級 1』都失敗，代表該 Token 已被伺服器封鎖，請去 FinMind 官網登出再登入，重新產生一個。")
st.write("2. 如果只有『層級 3』失敗，代表您的帳號等級目前無法存取分點資料。")
