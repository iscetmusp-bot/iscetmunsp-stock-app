import streamlit as st
import pandas as pd
import requests
import re
import time
from datetime import datetime

# ==========================================
# 核心數據類別 (內建重試與多重解析機制)
# ==========================================
class MoneyDJEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm"
        }
        # 完整分點名單
        self.broker_list = {
            "9200 凱基-台北 (隔日沖)": "9200",
            "984e 元大-土城永寧 (隔日沖)": "984e",
            "1520 凱基-松山 (主力)": "1520",
            "512a 國票-敦北法人": "512a",
            "1470 台灣美林 (外資)": "1470",
            "1440 摩根大通 (外資)": "1440",
            "1560 港商高盛 (外資)": "1560",
            "1024 合庫-台中": "1024",
            "1020 合庫-總社": "1020"
        }

    def fetch_with_retry(self, b_id, date_obj, mode, retries=3):
        """帶有自動重試功能的抓取邏輯"""
        d_str = date_obj.strftime("%Y-%m-%d")
        e_val = "1" if mode == "張數" else "0"
        url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={b_id}&b={b_id}&c={d_str}&d={d_str}&e={e_val}"
        
        for i in range(retries):
            try:
                resp = requests.get(url, headers=self.headers, timeout=10)
                resp.encoding = 'big5'
                html = resp.text
                
                # 同時使用兩種 Regex 模式確保不漏抓
                p1 = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
                p2 = r"<td class=\"t3t1\">(.+?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
                
                matches = re.findall(p1, html, re.DOTALL) + re.findall(p2, html, re.DOTALL)
                
                if matches:
                    df = pd.DataFrame([[m[0], float(m[1].replace(',','')), float(m[2].replace(',','')), float(m[3].replace(',',''))] for m in matches], 
                                     columns=['股票名稱', '買進', '賣出', '差額'])
                    return df.drop_duplicates(subset=['股票名稱'])
                
                # 若沒抓到，稍等一下再重試
                time.sleep(1) 
            except:
                time.sleep(2)
        return None

# ==========================================
# Streamlit UI 
# ==========================================
st.set_page_config(page_title="MoneyDJ 主力追蹤 Pro", layout="wide")
engine = MoneyDJEngine()

with st.sidebar:
    st.title("🏦 監控中心")
    sel_broker = st.selectbox("核心分點追蹤", options=list(engine.broker_list.keys()))
    manual_id = st.text_input("手動輸入代號 (選填)", placeholder="例如: 1024")
    target_date = st.date_input("查詢日期", value=datetime(2026, 1, 8))
    data_mode = st.radio("顯示數據", ["金額", "張數"], horizontal=True)
    
    final_id = manual_id if manual_id else engine.broker_list[sel_broker]
    st.divider()
    st.warning("若持續出現查無紀錄，請嘗試切換『金額/張數』或更換日期。")

st.title("🚀 MoneyDJ 分點進出 (GitHub 專業穩定版)")

if st.button("🔥 啟動深度數據掃描", use_container_width=True):
    with st.spinner(f"正在對分點 {final_id} 執行多重掃描..."):
        df = engine.fetch_with_retry(final_id, target_date, data_mode)
        
        if df is not None and not df.empty:
            st.success(f"✅ 數據擷取成功！日期：{target_date}")
            
            # 統計摘要
            m1, m2, m3 = st.columns(3)
            m1.metric("買超合計", f"{df[df['差額']>0]['差額'].sum():,.0f}")
            m2.metric("賣超合計", f"{df[df['差額']<0]['差額'].abs().sum():,.0f}")
            m3.metric("淨流向", f"{df['差額'].sum():,.0f}")

            t1, t2, t3 = st.tabs(["📈 買超排名", "📉 賣超排名", "📊 完整清單"])
            with t1:
                st.dataframe(df[df['差額'] > 0].sort_values('差額', ascending=False), use_container_width=True, hide_index=True)
            with t2:
                st.dataframe(df[df['差額'] < 0].sort_values('差額', ascending=True), use_container_width=True, hide_index=True)
            with t3:
                st.dataframe(df.sort_values('差額', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.error("❌ 掃描失敗。伺服器目前可能拒絕連線或該分點無交易。")
            st.info(f"建議手動檢查：https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={final_id}&b={final_id}&c={target_date.strftime('%Y-%m-%d')}&d={target_date.strftime('%Y-%m-%d')}")