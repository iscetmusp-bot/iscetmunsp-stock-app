import streamlit as st
import pandas as pd
import requests
import re
import io

# ==========================================
# 核心數據提取類別 (穩定增強版)
# ==========================================
class MoneyDJScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://moneydj.emega.com.tw/"
        }

    def get_broker_data(self, broker_id, date_obj, mode="金額"):
        """地毯式掃描網頁原始碼，還原所有交易紀錄"""
        d_str = f"{date_obj.year}-{date_obj.month}-{date_obj.day}"
        e_val = "1" if mode == "張數" else "0"
        url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={broker_id}&b={broker_id}&c={d_str}&d={d_str}&e={e_val}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.encoding = 'big5'
            html = resp.text

            # 強大正則：同時相容 GenLink2stk 標籤與純文字名稱
            # 模式 1: 帶有 JavaScript 連結的名稱
            p1 = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
            # 模式 2: 純文字名稱
            p2 = r"<td class=\"t3t1\">(.+?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
            
            matches = re.findall(p1, html, re.DOTALL) + re.findall(p2, html, re.DOTALL)
            
            if not matches:
                return None
            
            results = []
            for m in matches:
                name = m[0].strip()
                if not name or "券商名稱" in name: continue
                
                # 清洗數值資料
                buy = float(m[1].replace(',', '').strip() or 0)
                sell = float(m[2].replace(',', '').strip() or 0)
                diff = float(m[3].replace(',', '').strip() or 0)
                
                results.append({"股票名稱": name, "買進": buy, "賣出": sell, "差額": diff})
            
            return pd.DataFrame(results).drop_duplicates()
        except Exception as e:
            return None

# ==========================================
# Streamlit 專業介面
# ==========================================
st.set_page_config(page_title="MoneyDJ Pro 監控系統", layout="wide")

# 2025 隔日沖與核心分點清單
BROKER_LIST = {
    "9200 凱基-台北 (隔日沖)": "9200",
    "984e 元大-土城永寧 (隔日沖)": "984e",
    "1520 凱基-松山 (主力)": "1520",
    "512a 國票-敦北法人": "512a",
    "1470 台灣美林 (外資)": "1470",
    "1440 摩根大通 (外資)": "1440",
    "1024 合庫-台中": "1024",
    "1020 合庫-總社": "1020"
}

with st.sidebar:
    st.title("⚙️ 控制面板")
    sel_broker = st.selectbox("核心分點追蹤", options=list(BROKER_LIST.keys()))
    manual_id = st.text_input("手動輸入代號 (4位)", placeholder="例如: 1024")
    target_date = st.date_input("查詢日期", value=pd.to_datetime("2026-01-08"))
    data_mode = st.radio("顯示模式", ["金額", "張數"], horizontal=True)
    
    final_id = manual_id if manual_id else BROKER_LIST[sel_broker]
    st.divider()
    st.info("💡 提示：若出現查無紀錄，建議更換日期後再試。")

st.title("📈 MoneyDJ 分點進出 (GitHub 專業穩定版)")

scraper = MoneyDJScraper()

if st.button("🚀 啟動深度數據掃描", use_container_width=True):
    with st.spinner(f"正在分析 {final_id} 的原始網頁結構..."):
        df = scraper.get_broker_data(final_id, target_date, data_mode)
        
        if df is not None and not df.empty:
            st.success(f"✅ 成功還原分點 {final_id} 的交易明細")
            
            # 頂部儀表板
            net_buy = df[df['差額'] > 0]['差額'].sum()
            net_sell = df[df['差額'] < 0]['差額'].abs().sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("今日買進總額", f"{net_buy:,.0f}")
            c2.metric("今日賣出總額", f"{net_sell:,.0f}")
            c3.metric("淨部位", f"{(net_buy - net_sell):,.0f}", delta=float(net_buy - net_sell))
            
            # 分頁展示
            t1, t2, t3 = st.tabs(["🔥 買超熱點", "❄️ 賣超清單", "📊 完整數據"])
            with t1:
                st.dataframe(df[df['差額'] > 0].sort_values('差額', ascending=False), use_container_width=True, hide_index=True)
            with t2:
                st.dataframe(df[df['差額'] < 0].sort_values('差額', ascending=True), use_container_width=True, hide_index=True)
            with t3:
                st.dataframe(df.sort_values('差額', ascending=False), use_container_width=True, hide_index=True)
                
            # 下載功能
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 匯出 CSV 報表", csv, f"{final_id}_{target_date}.csv", "text/csv")
        else:
            st.warning("⚠️ 查無紀錄。可能原因：網站回應過慢、非交易日、或該分點當日無進出。")
