import streamlit as st
from datetime import datetime

# ==========================================
# 核心設定：確保手機點擊 100% 觸發
# ==========================================
st.set_page_config(page_title="分點監控-連結版", layout="centered")

st.title("🛡️ 分點進出 (文字直連版)")
st.info("💡 由於部分手機會攔截按鈕跳窗，請直接點擊下方的「藍色連結」。")

# 2025 強勢分點名單
BROKERS = {
    "9200 凱基-台北": "9200",
    "984e 元大-土城永寧": "984e",
    "1520 凱基-松山": "1520",
    "1024 合庫-台中": "1024",
    "1470 台灣美林": "1470"
}

with st.container():
    sel = st.selectbox("核心分點", options=list(BROKERS.keys()))
    manual = st.text_input("手動代號 (4位)", placeholder="例如: 9200")
    target_date = st.date_input("查詢日期", value=datetime(2026, 1, 8))

final_id = manual if manual else BROKERS[sel]
d_moneydj = target_date.strftime("%Y-%m-%d")

# --- 生成穩定連結 ---
st.divider()
st.subheader(f"📍 {final_id} 數據入口")

# 構建網址
url_wantgoo = f"https://www.wantgoo.com/stock/astock/agentstat?agentid={final_id}"
url_moneydj = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={final_id}&b={final_id}&c={d_moneydj}&d={d_moneydj}&e=1"

# 使用 Markdown 語法生成最原始的連結，這在手機上是不會失效的
st.markdown(f"### [👉 點我開啟：玩股網數據 (推薦)]({url_wantgoo})")
st.write("適合手機閱讀，介面最清楚。")

st.markdown(f"### [👉 點我開啟：MoneyDJ 官方數據]({url_moneydj})")
st.write("官方原始資料，最精確。")

st.divider()
st.caption("註：點擊連結後若無反應，請長按連結並選擇「在瀏覽器開啟」。")