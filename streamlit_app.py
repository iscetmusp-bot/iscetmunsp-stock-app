import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# 禁用安全警示（因為我們使用了 verify=False）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股籌碼觀察站 (官方直連版)", layout="wide")

def get_twse_data(target_date):
    """直接從證交所抓取法人彙總，加入 SSL 忽略設定"""
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/zh/api/trading/fund/BFI82U?date={date_str}&response=json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # 重點：verify=False 解決 image_10c56e.png 遇到的 SSL 錯誤
        res = requests.get(url, headers=headers, timeout=15, verify=False)
        data = res.json()
        
        if data.get("stat") == "OK":
            df = pd.DataFrame(data["data"], columns=data["fields"])
            return df, data["title"]
        else:
            return None, f"證交所回應：{data.get('stat', '無資料')}"
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- UI 介面 ---
st.title("🛡️ 台股籌碼觀察站 (官方直連穩定版)")

# 選擇日期：台股資料通常下午三點後才齊全
query_date = st.date_input("選擇查詢日期", datetime.now() - timedelta(days=1))

if st.button("🚀 抓取官方法人數據", use_container_width=True):
    with st.spinner('正在排除 SSL 障礙並下載資料...'):
        df, msg = get_twse_data(query_date)
        
        if df is not None:
            st.success(f"✅ 獲取成功！{msg}")
            
            # 數值清理：移除逗號並轉為數字
            for col in df.columns[1:]:
                df[col] = df[col].str.replace(',', '').astype(float)
            
            st.dataframe(df.style.format(precision=0), use_container_width=True)
            
            # 視覺化看板
            st.subheader("📊 市場資金流向總結")
            net_value = df.iloc[-1, -1] / 100000000 # 轉為億元
            st.metric("市場總買賣超 (億元)", f"{net_value:.2f}")
        else:
            st.error(f"❌ 讀取失敗")
            st.warning(f"診斷訊息：{msg}")
            st.info("💡 建議：若查詢今日無資料，請嘗試前一個工作日。")
