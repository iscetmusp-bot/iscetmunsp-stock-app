import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (終極穿透版)", layout="wide")

# ⚠️ 請將下方引號內的網址，更換為您在「第一步」獲得的全新 URL
# 注意：網址內不應該包含 /u/0/
GAS_URL = "https://script.google.com/macros/s/AKfycbxed-SP4n7bixPvst04u4QJqQF-fmFOCNsq3W5fmslA8cr2OweIZSc6BytD8BWW6b2rMQ/exec"

def get_data_via_gas(target_date):
    date_str = target_date.strftime("%Y%m%d")
    api_url = f"{GAS_URL}?date={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        # 在函數內建立 Session，確保連線獨立且正確
        with requests.Session() as session:
            # allow_redirects=True 確保能正確穿透 Google 的轉址層
            res = session.get(api_url, headers=headers, timeout=30, allow_redirects=True)
            
            # 診斷：若拿到 HTML 代表 GAS 部署網址 ID 仍有權限問題
            if res.text.strip().startswith("<!DOCTYPE html>"):
                return None, "拿到 Google 登入網頁，請重新執行『新增部署』獲取新的 ID 網址。"
            
            data = res.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                return df, data["title"]
            return None, f"證交所訊息：{data.get('stat')}"
            
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- 介面設計 ---
st.title("🛡️ 台股籌碼觀察站 (終極穿透版)")
st.caption("解決證交所封鎖雲端 IP 的終極方案。")

query_date = st.date_input("🗓️ 選擇查詢日期", value=datetime.now() - timedelta(days=1))

if st.button("🚀 執行官方數據抓取", use_container_width=True):
    with st.spinner('正在與 Google 伺服器同步數據...'):
        df, msg = get_data_via_gas(query_date)
        
        if df is not None:
            st.success(f"✅ 成功獲取：{msg}")
            # 數據清洗：處理金額中的逗號並轉為數字
            for col in df.columns[1:]:
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
        else:
            st.error(f"❌ 抓取失敗")
            st.warning(f"診斷訊息：{msg}")

st.info("提示：台股收盤資料通常在 15:00 後更新，週六日不開盤。")
