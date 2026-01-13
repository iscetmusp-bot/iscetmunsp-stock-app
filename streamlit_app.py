import streamlit as st
import pandas as pd
import io
import requests
from datetime import datetime

st.set_page_config(page_title="台股籌碼觀測站 (直接連線版)", layout="wide")

def get_data_direct(target_date):
    date_str = target_date.strftime("%Y%m%d")
    # 改用 CSV 下載網址，這與 JSON 接口的路徑不同，有機會繞過阻擋
    url = f"https://www.twse.com.tw/zh/trading/fund/BFI82U/download?queryDate={date_str}&type=csv"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        
        # 如果還是被擋（回傳 HTML），這行會抓到
        if "<html>" in response.text:
            return None, "連線被證交所拒絕 (IP 封鎖)。"

        # 使用 io.StringIO 將字串轉為檔案格式供 pandas 讀取
        # 證交所 CSV 通常從第 2 行開始才是資料
        df = pd.read_csv(io.StringIO(response.text), skiprows=1)
        
        # 清理資料：移除全空的欄位或合計列
        df = df.dropna(subset=['單位名稱'])
        return df, f"{date_str} 三大法人買賣超"
        
    except Exception as e:
        return None, f"抓取失敗: {str(e)}"

# --- UI 介面 ---
st.title("📈 台股籌碼觀察站 (CSV 直接連線)")

# 測試時請手動選取 2026/01/12
query_date = st.date_input("選擇查詢日期", value=datetime(2026, 1, 12))

if st.button("執行抓取", use_container_width=True):
    with st.spinner('嘗試直接連線證交所 CSV 伺服器...'):
        df, msg = get_data_direct(query_date)
        
        if df is not None:
            st.success(msg)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.error(msg)
            st.info("目前的雲端 IP 可能已被證交所暫時列入黑名單。")
