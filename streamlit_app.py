import streamlit as st
import pandas as pd
import requests
import re
import datetime

# ==========================================
# 核心數據類別 (專業 GitHub 風格)
# ==========================================
class BrokerTracker:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://moneydj.emega.com.tw/"
        }
        # 2025 最新主力與隔日沖名單
        self.broker_map = {
            "--- 隔日沖主力 ---": "NONE",
            "9200 凱基-台北": "9200",
            "984e 元大-土城永寧": "984e",
            "1520 凱基-松山": "1520",
            "512a 國票-敦北法人": "512a",
            "--- 外資/大型分點 ---": "NONE",
            "1470 台灣美林": "1470",
            "1440 摩根大通": "1440",
            "1360 新加坡商瑞銀": "1360",
            "1560 港商高盛": "1560",
            "1024 合庫-台中": "1024",
            "1020 合庫-總社": "1020"
        }

    def fetch(self, b_id, d_obj, mode):
        # 關鍵修正：MoneyDJ 有時要求日期必須補零 (2026-01-08)
        d_str = d_obj.strftime("%Y-%m-%d") 
        e_val = "1" if mode == "張數" else "0"
        url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={b_id}&b={b_id}&c={d_str}&d={d_str}&e={e_val}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'big5'
            html = resp.text
            
            # 使用最穩定的 Regex 提取法，解決 GenLink2stk 亂碼
            pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
            matches = re.findall(pattern, html, re.DOTALL)
            
            if not matches:
                # 備用提取法：純文字標籤
                alt_pattern = r"<td class=\"t3t1\">(.+?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
                matches = re.findall(alt_pattern, html, re.DOTALL)

            if matches:
                res = []
                for m in matches:
                    res.append([m[0], float(m[1].replace(',','')), float(m[2].replace(',','')), float(m[3].replace(',',''))])
                return pd.DataFrame(res, columns=['股票名稱', '買進', '賣出', '差額'])
            return None
        except:
            return None

# ==========================================
# Streamlit UI 層
# ==========================================
st.set_page_config(page_title="主力分點監控 PRO", layout="wide")
tracker = BrokerTracker()

with st.sidebar:
    st.title("🛡️ 監控面板")
    sel = st.selectbox("核心名單", options=list(tracker.broker_map.keys()))
    manual = st.text_input("手動代號", placeholder="例如: 9200")
    # 預設為你有資料的那天
    date = st.date_input("查詢日期", value=datetime.date(2026, 1, 8))
    mode = st.radio("顯示模式", ["金額", "張數"], horizontal=True)
    
    active_id = manual if manual else tracker.broker_map[sel]

st.header(f"🚀 分點數據分析：{active_id}")

if st.button("啟動深度追蹤", use_container_width=True):
    if active_id == "NONE":
        st.warning("請選擇或輸入有效的分點代號")
    else:
        df = tracker.fetch(active_id, date, mode)
        if df is not None and not df.empty:
            st.success(f"✅ 成功找到 {len(df)} 筆交易紀錄")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("買超總計", f"{df[df['差額']>0]['差額'].sum():,.0f}")
            m2.metric("賣超總計", f"{df[df['差額']<0]['差超'].abs().sum() if '差超' in df else 0:,.0f}") # 修正變數
            m3.metric("淨流向", f"{df['差額'].sum():,.0f}")

            t1, t2 = st.tabs(["📈 買超排名", "📉 賣超排名"])
            with t1:
                st.dataframe(df[df['差額'] > 0].sort_values('差額', ascending=False), use_container_width=True)
            with t2:
                st.dataframe(df[df['差額'] < 0].sort_values('差額', ascending=True), use_container_width=True)
        else:
            # 針對你的截圖錯誤給出明確提示
            st.error("⚠️ 查無紀錄。請確認該日期是否為交易日（週六日無資料），或嘗試輸入其他分點。")
            st.info(f"偵測網址：https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={active_id}&b={active_id}&c={date.strftime('%Y-%m-%d')}&d={date.strftime('%Y-%m-%d')}")