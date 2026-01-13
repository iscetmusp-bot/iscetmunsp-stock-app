import streamlit as st
import pandas as pd
import requests
import re
import random

# ==========================================
# 核心偽裝抓取函數
# ==========================================
def fetch_data_mobile(b_id, d_obj, mode):
    # 隨機更換 User-Agent 避開偵測
    ua_list = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    
    headers = {
        "User-Agent": random.choice(ua_list),
        "Referer": "https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm",
        "Accept-Language": "zh-TW,zh;q=0.9"
    }

    d_str = d_obj.strftime("%Y-%m-%d")
    e_val = "1" if mode == "張數" else "0"
    # 建立 URL
    url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={b_id}&b={b_id}&c={d_str}&d={d_str}&e={e_val}"
    
    try:
        # 強制使用 Session 並縮短 timeout 避免死等
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=10)
        resp.encoding = 'big5'
        html = resp.text

        # 針對 GenLink2stk 進行硬解
        pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
        matches = re.findall(pattern, html, re.DOTALL)
        
        if not matches:
            return None
            
        res = []
        for m in matches:
            res.append({
                "股票名稱": m[0],
                "買進": float(m[1].replace(',', '') or 0),
                "賣出": float(m[2].replace(',', '') or 0),
                "差額": float(m[3].replace(',', '') or 0)
            })
        return pd.DataFrame(res)
    except:
        return None

# ==========================================
# Streamlit 手機介面優化
# ==========================================
st.set_page_config(page_title="MoneyDJ 行動版", layout="centered")
st.title("📱 分點進出 (手機優化版)")

# 2025 主力分點名單
BROKERS = {
    "9200 凱基-台北": "9200",
    "984e 元大-土城永寧": "984e",
    "1520 凱基-松山": "1520",
    "1024 合庫-台中": "1024",
    "1470 台灣美林": "1470"
}

# 手機版建議把控制項放在上方，不要放 sidebar
sel = st.selectbox("選擇分點", options=list(BROKERS.keys()))
manual = st.text_input("或輸入 4 位代號", placeholder="例如: 1024")
date = st.date_input("日期", value=pd.to_datetime("2026-01-08"))
mode = st.radio("模式", ["金額", "張數"], horizontal=True)

final_id = manual if manual else BROKERS[sel]

if st.button("🚀 點擊抓取數據", use_container_width=True):
    with st.spinner("連線中..."):
        df = fetch_data_mobile(final_id, date, mode)
        
        if df is not None and not df.empty:
            st.success(f"✅ 成功找到 {len(df)} 筆資料")
            # 手機版顯示簡化表格
            st.dataframe(df.sort_values('差額', ascending=False), use_container_width=True)
        else:
            st.error("❌ 抓取失敗")
            st.info("💡 提示：Streamlit 伺服器可能已被 MoneyDJ 暫時封鎖，請等 5 分鐘後再試，或更換查詢日期。")