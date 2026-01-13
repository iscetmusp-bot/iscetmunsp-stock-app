import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (免 Token 版)", layout="wide")

def get_twse_institutional_investors(target_date):
    """直接從證交所官網抓取三大法人買賣超彙總"""
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/zh/api/trading/fund/BFI82U?date={date_str}&response=json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        
        if data.get("stat") == "OK":
            # 整理成 DataFrame
            df = pd.DataFrame(data["data"], columns=data["fields"])
            return df, data["title"]
        else:
            return None, "當日非交易日或資料尚未更新"
    except Exception as e:
        return None, f"連線失敗: {str(e)}"

# --- 介面設計 ---
st.title("🛡️ 台股籌碼觀察站 (官方直接連線)")
st.info("本頁面數據直接連線『台灣證券交易所』，不需 FinMind Token，無積分限制。")

# 選擇日期 (預設昨天，因為今天可能還沒收盤)
query_date = st.date_input("選擇查詢日期", datetime.now() - timedelta(days=1))

if st.button("🚀 抓取官方法人數據", use_container_width=True):
    with st.spinner('正在從證交所下載資料...'):
        df, msg = get_twse_institutional_investors(query_date)
        
        if df is not None:
            st.success(f"✅ {msg}")
            
            # 美化表格
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 簡單分析
            st.write("### 💡 快速解讀")
            # 假設最後一欄是買賣差額
            total_diff = df.iloc[-1, -1]
            st.metric("市場總買賣超差額", total_diff)
        else:
            st.error(f"❌ 無法讀取：{msg}")
            st.warning("提示：台股收盤資料通常在 15:00 後更新，週六日不開盤。")

st.divider()
st.caption("數據來源：臺灣證券交易所 (TWSE) 公開資料查詢系統")
