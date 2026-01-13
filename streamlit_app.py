import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (中繼穩定版)", layout="wide")

# 1. 請確保這是您最新部署的、不帶 /u/0/ 的網址
GAS_URL = "https://script.google.com/macros/s/AKfycbwPDwsQ8VuSF906a9BiNjjTMFA91BBKTDXzIXDQ3TeXqqckCksbbPKamvSEa4MzZKMbPg/exec"

def get_data_via_gas(target_date):
    date_str = target_date.strftime("%Y%m%d")
    api_url = f"{GAS_URL}?date={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        # 在函數內部建立 session
        with requests.Session() as session:
            # allow_redirects=True 非常重要，處理 Google 腳本轉址
            res = session.get(api_url, headers=headers, timeout=30, allow_redirects=True)
            
            # 診斷：若拿到 HTML 代表權限沒開對
            if res.text.strip().startswith("<!DOCTYPE html>"):
                return None, "拿到 Google 登入網頁，請確認 GAS 部署為『所有人』存取。"
            
            data = res.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                return df, data["title"]
            return None, f"證交所訊息：{data.get('stat')}"
            
    except Exception as e:
        return None, f"系統連線失敗: {str(e)}"

# --- UI 介面 ---
st.title("🛡️ 台股籌碼觀察站 (終極穿透版)")

query_date = st.date_input("🗓️ 選擇查詢日期", value=datetime.now() - timedelta(days=1))

if st.button("🚀 執行官方數據抓取", use_container_width=True):
    with st.spinner('正在引導 Google 伺服器穿透連線...'):
        df, msg = get_data_via_gas(query_date)
        
        if df is not None:
            st.success(f"✅ 成功獲取：{msg}")
            # 資料清理：移除逗號轉數字
            for col in df.columns[1:]:
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
        else:
            st.error(f"❌ 抓取失敗")
            st.warning(f"診斷訊息：{msg}")
