import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="台股籌碼觀察站 (中繼穩定版)", layout="wide")

# 請替換為您在第一步獲得的 Google GAS 網址
GAS_URL = "https://script.google.com/macros/s/AKfycbw-qSK9CP2znSKYLU-6CbsCBM_FjyUFaEIKkoJe1tYyuEN8nJs2WQR5VRkvnpGxK9x71exec" 

def get_data_via_gas(target_date):
    date_str = target_date.strftime("%Y%m%d")
    try:
        # 透過 Google 伺服器請求，繞過 TWSE 對雲端 IP 的限制
        res = requests.get(f"{GAS_URL}?date={date_str}", timeout=20)
        data = res.json()
        
        if data.get("stat") == "OK":
            df = pd.DataFrame(data["data"], columns=data["fields"])
            return df, data["title"]
        return None, f"查無資料 ({data.get('stat')})"
    except Exception as e:
        return None, f"中繼站連線失敗: {str(e)}"

st.title("🛡️ 台股籌碼觀察站 (Google 中繼強化版)")
st.info("透過 Google Cloud 代理請求，解決證交所阻擋雲端 IP 的問題。")

query_date = st.date_input("🗓️ 選擇查詢日期", value=datetime.now() - timedelta(days=1))

if st.button("🚀 執行穿透式數據抓取", use_container_width=True):
    with st.spinner('正在引導 Google 伺服器進行穿透連線...'):
        df, msg = get_data_via_gas(query_date)
        
        if df is not None:
            st.success(f"✅ 成功獲取：{msg}")
            for col in df.columns[1:]:
                df[col] = df[col].str.replace(',', '').astype(float)
            st.dataframe(df.style.format(precision=0), use_container_width=True, hide_index=True)
            
            # 關鍵指標
            net_total = df.iloc[-1, 4] / 100000000
            st.metric("當日法人總買賣超", f"{net_total:.2f} 億元")
        else:
            st.error(f"❌ 抓取失敗：{msg}")
            st.warning("提示：請確認您的 GAS 部署設定為『所有人』皆可存取。")

st.divider()
st.caption("數據中繼：Google Apps Script | 原始來源：臺灣證券交易所")
