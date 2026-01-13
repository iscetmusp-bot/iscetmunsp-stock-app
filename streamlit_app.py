import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- 0. 基本配置與擬人化 ---
st.set_page_config(page_title="台股籌碼觀察站 (最終穩定版)", layout="wide")

# 您最新的有效 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

def get_real_data(broker_id):
    """
    從多重維度確保抓到資料，加入 Headers 擬人化
    """
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # 加入擬人化 Headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    # 增加搜尋彈性：拉長至 45 天，確保避開任何長假或維護期
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    
    params = {
        "dataset": "TaiwanStockBrokerPivots",
        "data_id": broker_id,
        "start_date": start_date,
        "end_date": end_date,
        "token": FINMIND_TOKEN
    }

    try:
        # 增加 retry 機制
        for attempt in range(2):
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                result_json = response.json()
                if result_json.get("msg") == "success" and result_json.get("data"):
                    df = pd.DataFrame(result_json["data"])
                    return df, "success"
                time.sleep(1) # 若失敗，等一秒再試一次
            else:
                return None, f"HTTP 錯誤碼: {response.status_code}"
        
        return None, "伺服器目前無法提供資料，請稍後再試。"
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- 1. 使用者介面 ---

st.title("🛡️ 台股籌碼觀察站 (深度連線版)")
st.caption("版本：2026.01.13 | 解決 API 拒絕請求問題")

broker_dict = {
    "9268 凱基-台北": "9268",
    "9264 凱基-松山": "9264",
    "1470 摩根斯坦利": "1470",
    "8440 摩根大通": "8440",
    "1560 美商高盛": "1560"
}

target = st.selectbox("🎯 選擇追蹤分點：", list(broker_dict.keys()))

if st.button("🚀 執行深度掃描", use_container_width=True):
    with st.spinner('📡 正在建立加密連線並調用數據...'):
        raw_df, status = get_real_data(broker_dict[target])
        
        if raw_df is not None:
            # 資料處理
            raw_df['date'] = pd.to_datetime(raw_df['date'])
            latest_date = raw_df['date'].max()
            final_df = raw_df[raw_df['date'] == latest_date].copy()
            
            # 計算買超
            final_df['buy'] = pd.to_numeric(final_df['buy'], errors='coerce').fillna(0)
            final_df['sell'] = pd.to_numeric(final_df['sell'], errors='coerce').fillna(0)
            final_df['買超(張)'] = (final_df['buy'] - final_df['sell']) / 1000
            
            # 呈現
            st.success(f"✅ 資料連線成功！日期：{latest_date.strftime('%Y-%m-%d')}")
            
            # 簡易顯示 (不依賴外部對照表，確保表格一定能出得來)
            show_df = final_df[final_df['買超(張)'] != 0].sort_values("買超(張)", ascending=False)
            show_df = show_df[['stock_id', '買超(張)']].rename(columns={'stock_id':'股票代號'})
            
            st.dataframe(show_df.style.format({"買超(張)": "{:.1f}"}), use_container_width=True, hide_index=True)
        else:
            st.error(f"❌ 無法讀取資料")
            st.warning(f"診斷報告：{status}")
            st.info("提示：若頻繁出現此錯誤，可能是您的網路環境正在阻擋連線，或是 API 伺服器正在進行每日維護。")
