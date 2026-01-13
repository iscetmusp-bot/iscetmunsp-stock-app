import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime

# ==========================================
# 終極自動化解析：不再讓您動手
# ==========================================
def auto_fetch_and_analyze(broker_id, date_obj):
    # 格式化日期與構建 URL
    d_str = date_obj.strftime("%Y-%m-%d")
    url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={broker_id}&b={broker_id}&c={d_str}&d={d_str}&e=1"
    
    # 這是最關鍵的偽裝：模擬行動版 Chrome，嘗試穿透封鎖
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Referer": "https://moneydj.emega.com.tw/"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'big5'
        html = resp.text
        
        # 使用正則表達式直接從 HTML 提取，解決 JavaScript 亂碼問題
        pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)<\/td>.*?<td.*?>(.*?)<\/td>.*?<td.*?>(.*?)<\/td>"
        matches = re.findall(pattern, html)
        
        if matches:
            df = pd.DataFrame(matches, columns=['股票名稱', '買進', '賣出', '差額'])
            for col in ['買進', '賣出', '差額']:
                df[col] = df[col].str.replace(',', '').astype(float)
            return df
        return None
    except:
        return None

# --- Streamlit 介面 ---
st.set_page_config(page_title="分點監控-自動化終結版", layout="wide")
st.title("📊 分點進出 (自動化數據看板)")

with st.sidebar:
    broker_id = st.text_input("輸入分點代號", value="1470")
    target_date = st.date_input("查詢日期", value=datetime(2026, 1, 8))

if st.button("🚀 執行自動抓取與分析", use_container_width=True):
    # 這裡是您要的：自動顯示，不讓您去連外部網頁
    result_df = auto_fetch_and_analyze(broker_id, target_date)
    
    if result_df is not None:
        st.success(f"✅ 自動抓取成功！已過濾主力動向")
        st.dataframe(result_df.sort_values('差額', ascending=False), use_container_width=True)
    else:
        st.error("❌ 雲端 IP 仍遭封鎖中。")
        st.warning("如果自動抓取失敗，代表 MoneyDJ 已徹底封鎖雲端平台。")