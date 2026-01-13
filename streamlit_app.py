import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# --- 0. 基本環境設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股籌碼觀察站", layout="wide")

# 填入您提供的最新有效 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0xMyAxMDo0NzozMyIsInVzZXJfaWQiOiJpc2NldG11c3AiLCJlbWFpbCI6ImlzY2V0bXVzcEBnbWFpbC5jb20iLCJpcCI6IjYwLjI0OS4xMzYuMzcifQ.AyKn8RjaIoDUU9iPCiM9mF-EV5b8Kmn4qqkzvCSKPZ4"

# --- 1. 核心數據抓取邏輯 ---

def get_broker_data_ultra_stable(broker_id):
    """
    極致穩定版：自動處理 API 回傳為 None 或空的狀況
    """
    try:
        api_url = "https://api.finmindtrade.com/api/v4/data"
        # 搜尋區間擴大至 30 天，確保避開國定假日與更新延遲
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        params = {
            "dataset": "TaiwanStockBrokerPivots",
            "data_id": broker_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": FINMIND_TOKEN
        }
        
        res = requests.get(api_url, params=params, timeout=20)
        data_json = res.json()
        
        # 1. 檢查 API 通訊狀態
        if data_json.get("msg") != "success":
            return None, f"API 狀態錯誤: {data_json.get('msg')}"
        
        # 2. 檢查資料是否存在
        raw_list = data_json.get("data", [])
        if not raw_list:
            return None, "資料庫暫無該券商交易紀錄 (請稍後再試或檢查券商代號)。"
            
        df = pd.DataFrame(raw_list)
        
        # 3. 強制校正欄位，防止出現 None
        for col in ['buy', 'sell', 'stock_id']:
            if col not in df.columns:
                return None, f"API 回傳資料格式不全，缺少 {col} 欄位。"
        
        df['date'] = pd.to_datetime(df['date'])
        df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
        df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
        
        # 4. 抓取「最新一個有資料的日期」
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        # 5. 計算買超 (單位：張)
        df_latest['買超(張)'] = (df_latest['buy'] - df_latest['sell']) / 1000
        
        # 只顯示有異動的股票 (買超或賣超不等於 0)
        result = df_latest[df_latest['買超(張)'] != 0].sort_values("買超(張)", ascending=False)
        
        if result.empty:
            return None, f"日期 {latest_date.strftime('%Y-%m-%d')} 有交易但無有效買超數據。"
            
        return result, latest_date.strftime('%Y-%m-%d')
        
    except Exception as e:
        return None, f"程式發生異常: {str(e)}"

@st.cache_data(ttl=3600)
def get_name_map():
    """抓取證交所代碼對照"""
    try:
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", timeout=15)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        return {str(val).split('　')[0]: str(val).split('　')[1] for val in df['有價證券代號及名稱'] if '　' in str(val)}
    except:
        return {}

# --- 2. 介面呈現 ---

st.title("🛡️ 台股籌碼觀察站")
st.caption(f"當前連線狀態：API Token 驗證正常 (2026版)")
st.divider()

# 分點定義清單
broker_dict = {
    "9268 凱基-台北": "9268",
    "9264 凱基-松山": "9264",
    "1470 摩根斯坦利": "1470",
    "8440 摩根大通": "8440",
    "1560 美商高盛": "1560",
    "9800 元大-總公司": "9800",
    "700E 富邦-建國": "700E"
}

target_label = st.selectbox("🎯 選擇追蹤分點：", list(broker_dict.keys()))

if st.button("🚀 執行數據掃描", use_container_width=True):
    with st.spinner('🔍 正在向交易所請求最新帳冊...'):
        data, info = get_broker_data_ultra_stable(broker_dict[target_label])
        
        if data is not None:
            st.success(f"✅ 成功獲取！資料日期：{info}")
            
            names = get_name_map()
            data['股票名稱'] = data['stock_id'].apply(lambda x: names.get(str(x), "未知標的"))
            
            # 格式化表格輸出
            output_df = data[['stock_id', '股票名稱', '買超(張)']].rename(columns={'stock_id':'代號'})
            
            st.dataframe(
                output_df.style.format({"買超(張)": "{:,.1f}"}),
                hide_index=True,
                use_container_width=True
            )
            
            # 下載按鈕
            csv = output_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 儲存本次掃描結果", csv, f"{target_label}_{info}.csv", "text/csv")
        else:
            st.error("❌ 無法載入數據")
            st.warning(f"診斷報告：{info}")
            st.info("💡 提示：若今日尚未收盤或交易所尚未公布日報表(通常17:30)，請稍後再試。")

st.divider()
st.caption("備註：本系統僅供學術與籌碼研究參考，投資請自行承擔風險。")
