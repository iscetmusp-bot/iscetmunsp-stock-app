import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# --- 0. 基本設定 ---
# 停用安全檢查警告（針對某些環境的相容性）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股籌碼觀察站", layout="wide")

# 已填入您提供的最新 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

# --- 1. 核心數據處理 ---

def get_broker_data_final(broker_id):
    """
    使用 HTTP 直接請求 FinMind API，確保 100% 避開套件版本衝突
    """
    try:
        api_url = "https://api.finmindtrade.com/api/v4/data"
        # 搜尋範圍設定為 20 天，確保能抓到最近一個有開盤交易的數據
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        
        params = {
            "dataset": "TaiwanStockBrokerPivots",
            "data_id": broker_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": FINMIND_TOKEN
        }
        
        res = requests.get(api_url, params=params, timeout=15)
        data_json = res.json()
        
        # 檢查 API 回傳狀態
        if data_json.get("msg") != "success":
            return None, f"API 回應異常：{data_json.get('msg')}"
        
        raw_list = data_json.get("data", [])
        if not raw_list:
            return None, "此券商在搜尋區間內查無交易紀錄，請確認券商代號或稍後再試。"
            
        df = pd.DataFrame(raw_list)
        df['date'] = pd.to_datetime(df['date'])
        
        # 鎖定該券商「最近一個有交易的日期」
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 數值清理與買超計算
        df_latest['buy'] = pd.to_numeric(df_latest['buy'], errors='coerce').fillna(0)
        df_latest['sell'] = pd.to_numeric(df_latest['sell'], errors='coerce').fillna(0)
        df_latest['買超張數'] = (df_latest['buy'] - df_latest['sell']) / 1000
        
        # 排除買賣超合計為 0 的股票，並按買超張數降序排列
        result = df_latest[df_latest['買超張數'] != 0].sort_values("買超張數", ascending=False)
        return result, latest_date.strftime('%Y-%m-%d')
        
    except Exception as e:
        return None, f"連線異常：{str(e)}"

@st.cache_data(ttl=3600)
def get_stock_name_map():
    """抓取台股名稱對照表"""
    try:
        # 抓取上市股票清單
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", timeout=10)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        name_map = {}
        for val in df['有價證券代號及名稱']:
            if '　' in str(val):
                code, name = str(val).split('　')
                if len(code) == 4: name_map[code] = name
        return name_map
    except:
        return {}

# --- 2. 使用者介面 ---

st.title("🛡️ 台股籌碼觀察站")
st.caption("即時連線 FinMind API 資料庫")
st.divider()

# 定義熱門指標券商
broker_dict = {
    "9268 凱基-台北": "9268",
    "9264 凱基-松山": "9264",
    "1470 摩根斯坦利": "1470",
    "8440 摩根大通": "8440",
    "1560 美商高盛": "1560",
    "9800 元大-總公司": "9800",
    "700E 富邦-建國": "700E"
}

# 讓使用者選擇券商
selected_label = st.selectbox("🎯 請選擇要追蹤的指標分點：", list(broker_dict.keys()))

if st.button("🚀 開始數據掃描", use_container_width=True):
    bid = broker_dict[selected_label]
    with st.spinner(f'正在調閱 {selected_label} 的進出明細...'):
        data, info = get_broker_data_final(bid)
        
        if data is not None:
            st.success(f"✅ 抓取成功！最新交易日期：{info}")
            
            # 匹配股票名稱
            names = get_stock_name_map()
            data['股票名稱'] = data['stock_id'].apply(lambda x: names.get(str(x), "未知"))
            
            # 整理輸出表格
            final_df = data[['stock_id', '股票名稱', '買超張數']].copy()
            final_df.columns = ['代號', '股票名稱', '買超(張)']
            
            # 呈現表格並美化數值
            st.dataframe(
                final_df.style.format({"買超(張)": "{:,.1f}"}),
                hide_index=True,
                use_container_width=True
            )
            
            # 提供 CSV 下載
            csv = final_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表", csv, f"{selected_label}_{info}.csv", "text/csv")
        else:
            st.error("❌ 無法載入數據")
            st.warning(f"診斷報告：{info}")

st.info("💡 提醒：今日分點成交數據通常在 17:30 之後才會由交易所產出，若現在查無資料，系統會自動顯示前一交易日的數據。")
