import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基礎設定 ---
st.set_page_config(page_title="台股籌碼穿透版", layout="wide")

# ⚠️ 請在此處貼上您剛剛產生的「全新 ID」網址
# 網址範例：https://script.google.com/macros/s/ABCDEFG.../exec
GAS_URL = "https://script.google.com/macros/s/AKfycbxxpquBQIW4Zd_C-Mtw3C7F0OXRMGF2zasOzqBw9mDyrUzSwDVxSsA18zMklRMsbaLdbg/exec"

def fetch_twse_data(target_date):
    date_str = target_date.strftime("%Y%m%d")
    # 網址加上隨機數參數，強迫 Google 重新抓取而不使用快取
    api_url = f"{GAS_URL}?date={date_str}&t={datetime.now().timestamp()}"
    
    try:
        # allow_redirects=True 處理 Google 腳本轉址
        # 使用 requests.get 最直接的方式，避免 Session 作用域問題
        response = requests.get(api_url, timeout=30, allow_redirects=True)
        
        # 診斷：若回傳內容以 HTML 標籤開頭
        if response.text.strip().startswith("<!DOCTYPE html>"):
            return None, "錯誤：Google 仍攔截此連線。請確認 GAS 部署時『誰可以存取』已確實設為『所有人』並重新取得網址。"
        
        json_data = response.json()
        if json_data.get("stat") == "OK":
            df = pd.DataFrame(json_data["data"], columns=json_data["fields"])
            return df, json_data["title"]
        else:
            return None, f"證交所訊息：{json_data.get('stat')}"
            
    except Exception as e:
        return None, f"系統異常：{str(e)}"

# --- 使用者介面 ---
st.title("📊 三大法人買賣超彙總 (官方同步版)")

# 預設查詢 2026/01/12
default_date = datetime(2026, 1, 12)
query_date = st.date_input("🗓️ 選擇查詢日期", value=default_date)

if st.button("🚀 取得數據", use_container_width=True):
    with st.spinner('連線中...'):
        df, msg = fetch_twse_data(query_date)
        
        if df is not None:
            st.success(f"✅ {msg}")
            # 資料清理：處理金額字串中的逗號
            for col in df.columns[1:]:
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
        else:
            st.error(msg)
            st.warning("提示：若為假日或今日下午三點前，官方將不會提供數據。")
