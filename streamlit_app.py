import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3

# 關閉不安全連線的警告訊息（因為我們使用了 verify=False）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股強勢股篩選器", layout="wide")
st.title("🚀 台股全自動篩選器 (含股票名稱)")

# --- 1. 修改清單抓取邏輯：建立 {代號: 名稱} 對照表 ---
@st.cache_data(ttl=3600)
def get_tw_stock_map():
    headers = {'User-Agent': 'Mozilla/5.0'}
    urls = [
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", ".TW"), # 上市
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", ".TWO") # 上櫃
    ]
    
    stock_map = {}
    for url, suffix in urls:
        try:
            res = requests.get(url, headers=headers, verify=False)
            df = pd.read_html(res.text)[0]
            df.columns = df.iloc[0]
            df = df.iloc[2:]
            
            for val in df['有價證券代號及名稱']:
                if '　' in str(val):
                    code, name = str(val).split('　')
                    if len(code) == 4: # 只取四位數普通股
                        stock_map[code + suffix] = name
        except Exception as e:
            st.error(f"抓取清單失敗: {e}")
    return stock_map

# --- 2. 修改處理邏輯：帶入名稱 ---
def process_stock(ticker, name):
    try:
        stock = yf.Ticker(ticker)
        # 為了計算 60MA (季線)，我們抓取 100 天的資料
        hist = stock.history(period="100d")
        if len(hist) < 65: return None
        
        # 計算 60日移動平均線 (季線)
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        prev2_close = hist['Close'].iloc[-3]
        
        last_ma60 = hist['MA60'].iloc[-1]
        prev_ma60 = hist['MA60'].iloc[-2]
        
        volume_lots = hist['Volume'].iloc[-1] / 1000
        change_pct = ((last_close - prev_close) / prev_close) * 100
        
        # --- 篩選邏輯 ---
        # 1. 基本量能：成交量 > 1000張
        cond_vol = volume_lots > 1000
        # 2. 強勢：連兩日漲
        cond_strong = last_close > prev_close and prev_close > prev2_close
        # 3. 關鍵突破：今天收盤 > 季線 且 昨天收盤 <= 季線 (代表剛突破)
        # 或者你也可以選「站穩季線」：last_close > last_ma60
        cond_breakout = last_close > last_ma60 and prev_close <= prev_ma60
        
        if cond_vol and cond_strong and cond_breakout:
            return {
                "代號": ticker.split('.')[0],
                "名稱": name,
                "收盤價": round(last_close, 2),
                "漲幅(%)": round(change_pct, 2),
                "成交量(張)": int(volume_lots),
                "季線位置": round(last_ma60, 2)
            }
    except:
        return None
    return None

# --- 3. 主程式執行 ---
if st.button('執行全市場掃描'):
    stock_map = get_tw_stock_map()
    all_tickers = list(stock_map.keys())
    results = []
    
    with st.spinner(f'正在分析 {len(all_tickers)} 檔上市櫃股票...'):
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(process_stock, t, stock_map[t]) for t in all_tickers]
            for future in futures:
                res = future.result()
                if res: results.append(res)
    
    # 這裡的 if 必須與上面的「with st.spinner」最左邊對齊
    if results:
        df = pd.DataFrame(results).sort_values(by="漲幅(%)", ascending=False).head(20)
        st.success(f"掃描完成！符合條件共 {len(results)} 檔，以下顯示漲幅前 20 名：")
        st.dataframe(df, use_container_width=True, hide_index=True) # 這裡也順便幫你加上了隱藏索引
    else:
        st.warning("查無符合條件之股票。")
