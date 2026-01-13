import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (穩定版)", layout="wide")

# ⚠️ 請確保此網址是在 GAS「管理部署」中，由「最新版本」生成的 URL
# 且網址內絕對不可包含 /u/0/
GAS_URL = "https://script.google.com/macros/s/AKfycbwP58H9_tNzYX2SgIPgj1SqFUu1iQzRraHaq0Hta3XZg5s59fVTA-srruNkX8ZBhrlGpA/exec"

def get_data(target_date):
    date_str = target_date.strftime("%Y%m%d")
    # 手動加上一個隨機參數，強制 Google 不要使用快取網頁
    api_url = f"{GAS_URL}?date={date_str}&nocache={datetime.now().timestamp()}"
    
    try:
        # 改用最直接的 requests.get，並強制 allow_redirects
        res = requests.get(api_url, timeout=30, allow_redirects=True)
        
        # 這是您目前卡關的地方，我們印出前 100 字來診斷
        if res.text.strip().startswith("<!DOCTYPE html>"):
            return None, "診斷訊息：GAS 仍回傳 HTML 登入網頁。請嘗試在 GAS『管理部署』中刪除舊部署，重新建立一個全新的部署。"
        
        data = res.json()
        if data.get("stat") == "OK":
            df = pd.DataFrame(data["data"], columns=data["fields"])
            return df, data["title"]
        return None, f"證交所訊息：{data.get('stat')}"
    except Exception as e:
        return None, f"發生錯誤：{str(e)}"

# --- 介面設計 ---
st.title("🛡️ 台股籌碼觀察站")
query_date = st.date_input("🗓️ 選擇查詢日期", value=datetime(2026, 1, 12))

if st.button("🚀 執行抓取"):
    df, msg = get_data(query_date)
    if df is not None:
        st.success(msg)
        # 資料清洗
        for col in df.columns[1:]:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
        st.dataframe(df, use_container_width=True)
    else:
        st.error(msg)
