import streamlit as st
import pandas as pd
import requests
import re
import time
import random
from datetime import datetime

# ==========================================
# 核心偽裝引擎 (模擬真實瀏覽器行為)
# ==========================================
class UltimateMoneyDJ:
    def __init__(self):
        # 建立 Session 以保持連線狀態，降低被封鎖機率
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,share/png,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm",
            "Connection": "keep-alive"
        }

    def safe_fetch(self, b_id, d_obj, mode):
        # 嚴格日期格式：YYYY-MM-DD
        d_str = d_obj.strftime("%Y-%m-%d")
        e_val = "1" if mode == "張數" else "0"
        url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={b_id}&b={b_id}&c={d_str}&d={d_str}&e={e_val}"
        
        # 隨機延遲 0.5~2 秒，避免被偵測為機器人
        time.sleep(random.uniform(0.5, 2.0))
        
        try:
            # 帶入完整 Session 與偽裝頭部
            resp = self.session.get(url, headers=self.headers, timeout=15)
            resp.encoding = 'big5'
            html = resp.text
            
            # 強力正則表達式，專治 GenLink2stk 標籤
            pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
            matches = re.findall(pattern, html, re.DOTALL)
            
            if not matches:
                return None
                
            data = []
            for m in matches:
                name = m[0].strip()
                if not name: continue
                # 數字清洗
                buy = float(m[1].replace(',', '').strip() or 0)
                sell = float(m[2].replace(',', '').strip() or 0)
                diff = float(m[3].replace(',', '').strip() or 0)
                data.append({"股票名稱": name, "買進": buy, "賣出": sell, "差額": diff})
                
            return pd.DataFrame(data).drop_duplicates()
        except Exception:
            return None

# ==========================================
# 專業介面
# ==========================================
st.set_page_config(page_title="MoneyDJ 深度監控版", layout="wide")
st.title("🛡️ MoneyDJ 分點監控 (絕對防護穩定版)")

engine = UltimateMoneyDJ()

# 常見分點名單
BROKER_LIST = {
    "9200 凱基-台北": "9200",
    "984e 元大-土城永寧": "984e",
    "1520 凱基-松山": "1520",
    "1024 合庫-台中": "1024",
    "1470 台灣美林": "1470",
    "1440 摩根大通": "1440"
}

with st.sidebar:
    st.header("⚙️ 控制台")
    sel_broker = st.selectbox("核心分點", options=list(BROKER_LIST.keys()))
    manual_id = st.text_input("手動輸入代號 (優先)", placeholder="例如: 1024")
    target_date = st.date_input("查詢日期", value=datetime(2026, 1, 8))
    mode = st.radio("模式", ["金額", "張數"], horizontal=True)
    
    final_id = manual_id if manual_id else BROKER_LIST[sel_broker]

if st.button("🔥 啟動防封鎖掃描", use_container_width=True):
    with st.spinner(f"正在模擬真人訪問 {final_id}..."):
        df = engine.safe_fetch(final_id, target_date, mode)
        
        if df is not None and not df.empty:
            st.success(f"✅ 成功獲取 {len(df)} 筆數據")
            
            # 統計看板
            buy_sum = df[df['差額'] > 0]['差額'].sum()
            sell_sum = df[df['差額'] < 0]['差額'].abs().sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("買超總計", f"{buy_sum:,.0f}")
            c2.metric("賣超總計", f"{sell_sum:,.0f}")
            c3.metric("淨流向", f"{(buy_sum - sell_sum):,.0f}")
            
            st.divider()
            st.dataframe(df.sort_values('差額', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.error("⚠️ 抓取失敗。可能原因：非交易日、伺服器拒絕、或該分點當日無交易。")
            st.info(f"官方參考連結：https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={final_id}&b={final_id}&c={target_date.strftime('%Y-%m-%d')}&d={target_date.strftime('%Y-%m-%d')}")