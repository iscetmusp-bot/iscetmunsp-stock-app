import streamlit as st
import pandas as pd
import requests
import re
import io

# ==========================================
# 核心數據提取類別 (GitHub 風格)
# ==========================================
class MoneyDJScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://moneydj.emega.com.tw/"
        }

    def _clean_label(self, text):
        """處理 GenLink2stk 亂碼標籤"""
        match = re.search(r"','(.+?)'\);", str(text))
        return match.group(1) if match else text

    def get_broker_data(self, broker_id, date_obj, mode="金額"):
        d_str = f"{date_obj.year}-{date_obj.month}-{date_obj.day}"
        e_val = "1" if mode == "張數" else "0"
        url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={broker_id}&b={broker_id}&c={d_str}&d={d_str}&e={e_val}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.encoding = 'big5'
            # 提取原始數據
            pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
            matches = re.findall(pattern, resp.text, re.DOTALL)
            
            if not matches: return None
            
            results = []
            for m in matches:
                results.append({
                    "股票名稱": m[0],
                    "買進": float(m[1].replace(',', '')),
                    "賣出": float(m[2].replace(',', '')),
                    "差額": float(m[3].replace(',', ''))
                })
            return pd.DataFrame(results)
        except:
            return None

# ==========================================
# Streamlit 介面層
# ==========================================
st.set_page_config(page_title="MoneyDJ Pro 監控", layout="wide")
st.title("🚀 MoneyDJ 分點進出 (GitHub 專業版)")

# 初始化爬蟲
scraper = MoneyDJScraper()

# 隔日沖與核心清單
BROKER_LIST = {
    "9200 凱基-台北 (隔日沖)": "9200",
    "984e 元大-土城永寧 (隔日沖)": "984e",
    "1520 凱基-松山 (主力)": "1520",
    "1470 台灣美林 (外資)": "1470",
    "1440 摩根大通 (外資)": "1440",
    "1020 合庫-總社": "1020"
}

with st.sidebar:
    st.header("⚙️ 設定參數")
    sel_broker = st.selectbox("選擇分點", options=list(BROKER_LIST.keys()))
    manual_id = st.text_input("手動輸入代號 (選填)", placeholder="例如: 1024")
    target_date = st.date_input("查詢日期", value=pd.to_datetime("2026-01-08"))
    data_mode = st.radio("數據模式", ["金額", "張數"])
    
    final_id = manual_id if manual_id else BROKER_LIST[sel_broker]

if st.button("🔥 啟動數據追蹤", use_container_width=True):
    df = scraper.get_broker_data(final_id, target_date, data_mode)
    
    if df is not None and not df.empty:
        st.success(f"成功解析分點 {final_id} 數據")
        
        # 視覺化摘要
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📈 買超前五名")
            st.dataframe(df.nlargest(5, '差額'), hide_index=True)
        with col2:
            st.subheader("📉 賣超前五名")
            st.dataframe(df.nsmallest(5, '差額'), hide_index=True)
            
        st.divider()
        st.subheader("📋 完整明細")
        st.dataframe(df.sort_values('差額', ascending=False), use_container_width=True)
    else:
        st.error("查無紀錄，請檢查日期或分點代號。")
