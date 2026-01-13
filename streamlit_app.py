import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime

# ==========================================
# 核心：深度模擬真實手機瀏覽器 (非簡單爬蟲)
# ==========================================
def auto_monitor_engine(broker_id, date_obj):
    d_str = date_obj.strftime("%Y-%m-%d")
    url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={broker_id}&b={broker_id}&c={d_str}&d={d_str}&e=1"
    
    # 這裡的 Headers 必須完全模擬手機端真實環境
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-tw",
        "Referer": "https://www.google.com/" # 偽裝成從 Google 搜尋過來的流量
    }
    
    try:
        # 使用 Session 保持狀態
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=15)
        resp.encoding = 'big5'
        html = resp.text
        
        # 針對 MoneyDJ 亂碼標籤的專用提取器
        pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)<\/td>.*?<td.*?>(.*?)<\/td>.*?<td.*?>(.*?)<\/td>"
        matches = re.findall(pattern, html)
        
        if matches:
            df = pd.DataFrame(matches, columns=['股票名稱', '買進', '賣出', '差額'])
            # 自動清理數字數據
            for col in ['買進', '賣出', '差額']:
                df[col] = df[col].str.replace(',', '').astype(float)
            return df
        return None
    except:
        return None

# --- 您要的自動化介面 ---
st.set_page_config(page_title="主力自動監控站", layout="wide")
st.title("🚀 分點進出 (全自動監控面板)")

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        bid = st.text_input("分點代號", value="1470")
    with col2:
        dt = st.date_input("日期", value=datetime(2026, 1, 8))

# 這裡點擊後，應該直接在下方出現表格，而不是跳走
if st.button("🔥 開始自動同步數據", use_container_width=True):
    with st.spinner("正在穿透封鎖，同步官方數據..."):
        df_result = auto_monitor_engine(bid, dt)
        
        if df_result is not None:
            st.success("✅ 自動同步完成")
            # 呈現您要的自動化結果
            st.dataframe(df_result.sort_values('差額', ascending=False), use_container_width=True)
        else:
            # 這是最慘的狀況：雲端 IP 徹底死亡
            st.error("❌ 雲端伺服器遭 MoneyDJ 封鎖。")
            st.info("💡 解決建議：請嘗試將 Streamlit App 的網址更換後重新部署，這會更換伺服器 IP。")