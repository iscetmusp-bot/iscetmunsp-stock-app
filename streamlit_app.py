import streamlit as st
import pandas as pd
import requests
import urllib3
import time
from datetime import datetime, timedelta

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股籌碼觀察站 (穩定強化版)", layout="wide")

def get_twse_data_final(target_date):
    """
    強化的證交所資料抓取函數
    """
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/zh/api/trading/fund/BFI82U?date={date_str}&response=json"
    
    # 更完整的瀏覽器偽裝 Headers，避免被當作爬蟲阻擋
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.twse.com.tw/zh/page/trading/fund/BFI82U.html",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        # 加入 timeout 與 verify=False
        res = requests.get(url, headers=headers, timeout=15, verify=False)
        
        # 檢查是否為 200 OK
        if res.status_code != 200:
            return None, f"證交所伺服器忙碌 (HTTP {res.status_code})"
            
        # 嘗試解析 JSON
        data = res.json()
        
        if data.get("stat") == "OK":
            df = pd.DataFrame(data["data"], columns=data["fields"])
            return df, data["title"]
        else:
            return None, f"該日期查無資料 ({data.get('stat')})"
            
    except Exception as e:
        return None, f"連線異常：{str(e)}"

# --- UI 介面 ---
st.title("🛡️ 台股籌碼觀察站 (終極穩定版)")
st.markdown("數據來源：臺灣證券交易所官方 API (直連免 Token)")

# 預設為前一個工作日 (避免今日尚未收盤的問題)
default_date = datetime.now() - timedelta(days=1)
if default_date.weekday() == 5: # 週六
    default_date -= timedelta(days=1)
elif default_date.weekday() == 6: # 週日
    default_date -= timedelta(days=2)

query_date = st.date_input("🗓️ 選擇查詢日期", value=default_date)

if st.button("🚀 執行官方數據抓取", use_container_width=True):
    with st.spinner(f'正在安全連線至證交所 ({query_date.strftime("%Y-%m-%d")})...'):
        # 增加一個微小的延遲，避免請求過快
        time.sleep(1)
        df, msg = get_twse_data_final(query_date)
        
        if df is not None:
            st.success(f"✅ 讀取成功！{msg}")
            
            # 數據美化
            for col in df.columns[1:]:
                df[col] = df[col].str.replace(',', '').astype(float)
            
            # 顯示主要表格
            st.subheader("📋 三大法人買賣超彙總")
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
            
            # 重點看板
            st.divider()
            cols = st.columns(3)
            # 依據台灣證交所格式，第 4 欄通常是買賣差額
            foreign_buy = df.iloc[3, 4] / 100000000 # 外資
            itrust_buy = df.iloc[2, 4] / 100000000 # 投信
            total_net = df.iloc[-1, 4] / 100000000 # 合計
            
            cols[0].metric("外資買賣超", f"{foreign_buy:.2f} 億元")
            cols[1].metric("投信買賣超", f"{itrust_buy:.2f} 億元")
            cols[2].metric("全市場總計", f"{total_net:.2f} 億元")
            
        else:
            st.error("❌ 讀取失敗")
            st.warning(f"診斷訊息：{msg}")
            st.info("💡 提示：若出現『非交易日』，請選取最近一個週一至週五。")
