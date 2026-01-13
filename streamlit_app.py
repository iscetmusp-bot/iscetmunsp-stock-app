import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (終極穿透版)", layout="wide")

# ⚠️ 請在此處替換為您在「步驟一」獲得的全新網址 (確認不含 /u/0/)
GAS_URL = "https://script.google.com/macros/s/AKfycbyrA6vV0Tpfal6dO8djllNkv-m60d_UgAs2O88U_pJMgFepacESS90LbLmLiuC7cPmE6w/exec"

def get_data_via_gas(target_date):
    date_str = target_date.strftime("%Y%m%d")
    api_url = f"{GAS_URL}?date={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        # 在函數內建立 session，避免 NameError
        with requests.Session() as session:
            # allow_redirects=True 確保能正確處理 Google 的身分跳轉
            res = session.get(api_url, headers=headers, timeout=30, allow_redirects=True)
            
            # 診斷：若拿到 HTML 代表 GAS 部署設定仍不對
            if res.text.strip().startswith("<!DOCTYPE html>"):
                return None, "拿到 Google 登入網頁，請確認 GAS 部署為『所有人』存取。"
            
            data = res.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                return df, data["title"]
            return None, f"證交所訊息：{data.get('stat')}"
            
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- UI 介面 ---
st.title("🛡️ 台股籌碼觀察站 (終極穿透版)")
st.caption("透過 Google Cloud 代理請求，完美解決證交所封鎖雲端 IP 的問題。")

query_date = st.date_input("🗓️ 選擇查詢日期", value=datetime.now() - timedelta(days=1))

if st.button("🚀 執行官方數據抓取", use_container_width=True):
    with st.spinner('正在同步數據...'):
        df, msg = get_data_via_gas(query_date)
        
        if df is not None:
            st.success(f"✅ 成功獲取：{msg}")
            # 資料清洗
            for col in df.columns[1:]:
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
        else:
            st.error(f"❌ 抓取失敗")
            st.warning(f"診斷訊息：{msg}")

st.info("提示：台股收盤資料通常在 15:00 後更新，週六日不開盤。")
