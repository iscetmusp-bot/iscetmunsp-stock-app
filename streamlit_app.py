import streamlit as st
import pandas as pd
import requests
import re

# 設定頁面
st.set_page_config(page_title="MoneyDJ 終極版", layout="wide")
st.title("📊 MoneyDJ 分點進出 (終極救贖版)")

# 2025 隔日沖與核心名單
BROKERS = {
    "9200 凱基-台北 (隔日沖)": "9200",
    "984e 元大-土城永寧 (隔日沖)": "984e",
    "1520 凱基-松山 (主力)": "1520",
    "1470 台灣美林 (外資)": "1470",
    "1440 摩根大通 (外資)": "1440",
    "1024 合庫-台中": "1024",
    "1020 合庫-總社": "1020"
}

with st.sidebar:
    st.header("⚙️ 設定中心")
    sel_name = st.selectbox("選擇分點", options=list(BROKERS.keys()))
    manual_id = st.text_input("或輸入 4 位代號", placeholder="例如: 1024")
    target_date = st.date_input("查詢日期", value=pd.to_datetime("2026-01-08"))
    mode = st.radio("數據模式", ["金額", "張數"], horizontal=True)
    
    b_id = manual_id if manual_id else BROKERS[sel_name]

def fetch_data_hardcore(broker_id, date_obj, mode_str):
    # 格式化日期與模式
    d_str = f"{date_obj.year}-{date_obj.month}-{date_obj.day}"
    e_val = "1" if mode_str == "張數" else "0"
    url = f"https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={broker_id}&b={broker_id}&c={d_str}&d={d_str}&e={e_val}"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'big5'
        html = resp.text
        
        # 關鍵：直接用 Regex 挖取 GenLink2stk 裡面的名稱和後面的數字
        # 這是應對你截圖中亂碼標籤的最強手段
        pattern = r"GenLink2stk\('.+?','(.+?)'\);.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>.*?<td.*?>(.*?)</td>"
        matches = re.findall(pattern, html, re.DOTALL)
        
        if not matches: return None
        
        data = []
        for m in matches:
            data.append({
                "股票名稱": m[0],
                "買進": float(m[1].replace(',', '') or 0),
                "賣出": float(m[2].replace(',', '') or 0),
                "差額": float(m[3].replace(',', '') or 0)
            })
        return pd.DataFrame(data)
    except:
        return None

if st.button("🚀 執行強力數據掃描", use_container_width=True):
    with st.spinner("正在擊破 MoneyDJ 標籤阻礙..."):
        df = fetch_data_hardcore(b_id, target_date, mode)
        
        if df is not None and not df.empty:
            st.success(f"✅ 成功還原 {b_id} 的數據！")
            
            # 顯示統計
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📈 買超前 10")
                st.dataframe(df.nlargest(10, '差額'), hide_index=True, use_container_width=True)
            with col2:
                st.subheader("📉 賣超前 10")
                st.dataframe(df.nsmallest(10, '差額'), hide_index=True, use_container_width=True)
                
            st.divider()
            st.subheader("📋 完整交易明細")
            st.dataframe(df.sort_values('差額', ascending=False), use_container_width=True)
        else:
            st.error(f"❌ 還是抓不到。請確認此連結在瀏覽器中是否有資料：\n https://moneydj.emega.com.tw/z/zg/zgb/zgb0.djhtm?a={b_id}&b={b_id}&c={target_date.year}-{target_date.month}-{target_date.day}&d={target_date.year}-{target_date.month}-{target_date.day}&e={'1' if mode=='張數' else '0'}")
