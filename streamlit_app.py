import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 核心設定
# ==========================================
st.set_page_config(page_title="分點監控-安全版", layout="wide")

# 2025 強勢分點名單
BROKERS = {
    "9200 凱基-台北 (隔日沖)": "9200",
    "984e 元大-土城永寧 (隔日沖)": "984e",
    "1520 凱基-松山 (主力)": "1520",
    "512a 國票-敦北法人": "512a",
    "1470 台灣美林 (外資)": "1470",
    "1440 摩根大通 (外資)": "1440",
    "1024 合庫-台中": "1024"
}

st.title("🛡️ 分點進出 (安全不封鎖版)")
st.caption("本版本採用「瀏覽器直連」技術，避免 IP 遭封鎖")

# --- 使用者輸入介面 ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        sel = st.selectbox("核心分點追蹤", options=list(BROKERS.keys()))
        manual = st.text_input("手動代號 (選填)", placeholder="例如: 1024")
    with col2:
        target_date = st.date_input("查詢日期", value=datetime(2026, 1, 8))
        mode = st.radio("數據模式", ["金額", "張數"], horizontal=True)

final_id = manual if manual else BROKERS[sel]
d_str = target_date.strftime("%Y-%m-%d")
e_val = "1" if mode == "張數" else "0"

# 構建官方合法網址
target_url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={final_id}&b={final_id}&c={d_str}&d={d_str}&e={e_val}"

# --- 顯示邏輯 ---
st.divider()

# 提供手機用戶一個快速按鈕，萬一鑲嵌失敗可以直達
st.link_button(f"🚀 用手機瀏覽器直接開啟 {final_id} 資料", target_url, use_container_width=True)

st.info(f"正在同步 {d_str} 的官方數據...")

# 使用 Iframe 鑲嵌：這會讓您的手機瀏覽器去載入網頁，而不是雲端主機去抓
# 這是最不容易被封鎖的方法
iframe_code = f'<iframe src="{target_url}" width="100%" height="800" style="border:none;"></iframe>'
st.components.v1.html(iframe_code, height=800, scrolling=True)