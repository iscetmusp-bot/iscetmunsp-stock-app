import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (中繼穩定版)", layout="wide")

# 1. 第 9 行使用不帶 /u/0/ 的新網址
GAS_URL = "https://script.google.com/macros/s/AKfycbyqOzrATutY66IyMesDkqGPWnGOGwdxSlE_gJnZBXSvLp-GI50UNk_kMJhkICxDp4J19w/exec" 

# 2. 修改 requests 連線那一行 (第 15 行左右)
# 加入 allow_redirects=True 並使用 Session
session = requests.Session()
res = session.get(api_url, headers=headers, timeout=30, allow_redirects=True)

def get_data_via_gas(target_date):
    date_str = target_date.strftime("%Y%m%d")
    # 確保網址結尾沒有斜線
    api_url = f"{GAS_URL}?date={date_str}"
    
    # 使用完全模擬一般瀏覽器的 Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/json,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache"
    }
    
    try:
        # 使用 Session 來自動處理 Google 的轉址與 Cookie
        session = requests.Session()
        res = session.get(api_url, headers=headers, timeout=30, allow_redirects=True)
        
        # 診斷：如果還是拿到 HTML，顯示前 100 字幫助判斷是哪種網頁
        if res.text.lstrip().startswith("<!DOCTYPE html>"):
            return None, f"解析失敗：拿到 Google 登入或錯誤網頁。前100字：{res.text[:100]}"
            
        data = res.json()
        
        if data.get("stat") == "OK":
            df = pd.DataFrame(data["data"], columns=data["fields"])
            return df, data["title"]
        else:
            return None, f"證交所訊息：{data.get('stat')}"
            
    except Exception as e:
        return None, f"系統連線異常: {str(e)}"

st.title("🛡️ 台股籌碼觀察站 (Google 中繼強化版)")
st.info("透過 Google Cloud 代理請求，解決證交所阻擋雲端 IP 的問題。")

query_date = st.date_input("🗓️ 選擇查詢日期", value=datetime.now() - timedelta(days=1))

if st.button("🚀 執行穿透式數據抓取", use_container_width=True):
    with st.spinner('正在引導 Google 伺服器進行穿透連線...'):
        df, msg = get_data_via_gas(query_date)
        
        if df is not None:
            st.success(f"✅ 成功獲取：{msg}")
            for col in df.columns[1:]:
                df[col] = df[col].str.replace(',', '').astype(float)
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
            
            # 關鍵指標
            net_total = df.iloc[-1, 4] / 100000000
            st.metric("當日法人總買賣超", f"{net_total:.2f} 億元")
        else:
            st.error(f"❌ 抓取失敗：{msg}")
            st.warning("提示：請確認您的 GAS 部署設定為『所有人』皆可存取。")

st.divider()
st.caption("數據中繼：Google Apps Script | 原始來源：臺灣證券交易所")
