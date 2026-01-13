import streamlit as st
from datetime import datetime

# ==========================================
# 核心設定：全面切換至 WantGoo
# ==========================================
st.set_page_config(page_title="分點監控-新源版", layout="wide")

# 2025 強勢分點名單 (WantGoo 專用格式)
BROKERS = {
    "9200 凱基-台北 (隔日沖)": "9200",
    "984E 元大-土城永寧 (隔日沖)": "984E",
    "1520 凱基-松山 (主力)": "1520",
    "1470 台灣美林 (外資)": "1470",
    "1440 摩根大通 (外資)": "1440",
    "1024 合庫-台中": "1024"
}

st.title("📊 分點進出 (WantGoo 數據源)")
st.info("💡 已棄用 MoneyDJ，改用傳輸更穩定的 WantGoo 數據源，防止 IP 封鎖。")

# --- 使用者輸入介面 ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        sel = st.selectbox("選擇追蹤分點", options=list(BROKERS.keys()))
        manual = st.text_input("手動輸入代號 (如有)", placeholder="例如: 9200")
    with col2:
        # WantGoo 支援日期選擇
        target_date = st.date_input("查詢日期", value=datetime(2026, 1, 8))
        # WantGoo 通常預設顯示金額與張數
        st.write("數據模式：完整明細")

final_id = manual if manual else BROKERS[sel]
d_str = target_date.strftime("%Y/%m/%d")

# 構建 WantGoo 合法數據網址
# 網址範例：https://www.wantgoo.com/stock/astock/agentstat?agentid=9200
target_url = f"https://www.wantgoo.com/stock/astock/agentstat?agentid={final_id}"

# --- 顯示邏輯 ---
st.divider()

# 提供手機用戶最直接的保障按鈕
st.link_button(f"🚀 手機直接開啟 {final_id} 完整數據頁", target_url, use_container_width=True)

st.warning(f"正在連線至 WantGoo 獲取 {final_id} 的資料...")

# 使用 Iframe 顯示：這會由您的手機端直接連線，避開雲端 IP 被擋的問題
iframe_code = f'<iframe src="{target_url}" width="100%" height="900" style="border:none; border-radius:10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></iframe>'
st.components.v1.html(iframe_code, height=900, scrolling=True)