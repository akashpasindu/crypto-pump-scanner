import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import time

st.set_page_config(page_title="Crypto Pump Scanner Pro Max (AI Powered)", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = "AQ.Ab8RN6Kov34e2FAiapWmBpeAtkyAint2-EaxdTwngH8RxeagKQ"

def send_telegram_alert(coin, price, change, volume_spike, rsi_val, tp1, tp2, sl, high_24h, low_24h, buyer_ratio, pattern_name, ai_verdict):
    clean_symbol = coin.replace('/', '_')
    message = (
        f"🚨 *Smart Crypto Pump Alert (AI Analyzed)!*\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"🤖 *AI Verdict:* `{ai_verdict}`\n"
        f"🕯️ *Pattern:* `{pattern_name}`\n"
        f"💵 *Entry Price:* `${price}`\n"
        f"📈 *15m Change:* `+{change}%`\n"
        f"📊 *Volume Spike:* `{volume_spike}`\n"
        f"🎯 *RSI (14):* `{rsi_val}`\n"
        f"🐋 *Buyer Dominance:* `{buyer_ratio}%`\n\n"
        f"🎯 *Dynamic ATR Targets:*\n"
        f"  ├ TP 1: `${tp1}`\n"
        f"  └ TP 2: `${tp2}`\n\n"
        f"🛑 *Dynamic ATR Stop Loss:* `${sl}`\n\n"
        f"📊 *24h Range:* `${low_24h}` - `${high_24h}`\n\n"
        f"🔗 [Trade on Binance](https://www.binance.com/en/trade/{clean_symbol})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    return requests.post(url, json=payload, timeout=5)

# ================= AI ANALYZER ENGINE =================
def analyze_with_ai(coin, price, change, volume_spike, rsi, pattern, buyer_ratio, btc_status, api_key):
    if not api_key:
        return "⚠️ No API Key", "API Key ලබා දී නොමැත", "Medium"
    
    prompt = (
        "Act as a professional Crypto Day Trader. Analyze this 15-minute pump setup and decide if it is safe to enter:\n"
        f"- Coin: {coin}\n"
        f"- Live Price: ${price}\n"
        f"- 15m Price Surge: +{change}%\n"
        f"- Volume Multiplier: {volume_spike}\n"
        f"- RSI (14): {rsi}\n"
        f"- Candlestick Pattern: {pattern}\n"
        f"- Order Book Buyer Dominance: {buyer_ratio}%\n"
        f"- Overall Market (BTC) Status: {btc_status}\n\n"
        "Respond ONLY in valid JSON format: "
        '{"verdict": "STRONG BUY", "confidence": 85, "reason": "Clear breakout with high buyer volume", "risk": "Low"}'
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=6)
        if res.status_code == 200:
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                verdict = f"{data.get('verdict')} ({data.get('confidence')}%)"
                return verdict, data.get('reason'), data.get('risk')
        return "⚠️ Analysis Failed", f"HTTP {res.status_code}", "Medium"
    except Exception:
        return "⚠️ Analysis Error", "Timeout or Parse Error", "Medium"

def play_alert_sound():
    sound_code = """
    <audio autoplay>
      <source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg">
    </audio>
    """
    components.html(sound_code, height=0, width=0)

def render_tradingview_widget(symbol_raw):
    widget_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol_raw}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 400,
        "symbol": "BINANCE:{symbol_raw}",
        "interval": "15",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "save_image": false,
        "container_id": "tradingview_{symbol_raw}"
      }}
      );
      </script>
    </div>
    """
    components.html(widget_code, height=420)

def detect_candlestick_pattern(df):
    if len(df) < 5:
        return "Normal Breakout"
    c1, o1, h1, l1 = df['close'].iloc[-1], df['open'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
    c2, o2 = df['close'].iloc[-2], df['open'].iloc[-2]
    c3, o3 = df['close'].iloc[-3], df['open'].iloc[-3]
    body1 = abs(c1 - o1)
    lower_wick1 = min(c1, o1) - l1
    upper_wick1 = h1 - max(c1, o1)
    
    if (c2 < o2) and (c1 > o1) and (c1 >= o2) and (o1 <= c2):
        return "Bullish Engulfing 🟢"
    if (lower_wick1 >= 2 * body1) and (upper_wick1 <= body1 * 0.5) and (c1 >= o1):
        return "Bullish Hammer 🔨"
    if (c1 > o1) and (c2 > o2) and (c3 > o3) and (c1 > c2 > c3):
        return "Three White Soldiers 🚀"
    if (c3 < o3) and (abs(c2 - o2) < abs(c3 - o3) * 0.4) and (c1 > o1) and (c1 > (o3 + c3) / 2):
        return "Morning Star 🌟"
    return "Volume Breakout ⚡"

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift()).abs()
    low_cp = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

BASE_URL = "https://data-api.binance.vision/api/v3"

def get_orderbook_buyer_ratio(raw_symbol):
    try:
        res = requests.get(f"{BASE_URL}/depth", params={'symbol': raw_symbol, 'limit': 20}, timeout=4)
        if res.status_code != 200:
            return 50.0
        data = res.json()
        bids = sum([float(b[1]) for b in data.get('bids', [])])
        asks = sum([float(a[1]) for a in data.get('asks', [])])
        total = bids + asks
        return round((bids / total) * 100, 1) if total > 0 else 50.0
    except Exception:
        return 50.0

st.title("🚀 Smart Crypto Pump Scanner Pro Max (AI Enabled)")

# Global Background Alerts Tracking (Cache across sessions)
@st.cache_resource
def get_global_state():
    return {"last_alert_time": {}}

global_state = get_global_state()

# Default Settings (Hardcoded for Autonomous 24/7 Scanning)
volume_threshold = 1.5
price_threshold = 1.2
rsi_min = 45
rsi_max = 75
limit_pairs = 60

# Sidebar Settings
st.sidebar.header("Bot Configuration")
gemini_key = st.sidebar.text_input("Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")
enable_ai = st.sidebar.checkbox("🧠 Enable AI Trade Verifier", value=True)
enable_btc_filter = st.sidebar.checkbox("🛡️ BTC Market Safety Filter", value=True)
enable_1h_filter = st.sidebar.checkbox("📈 1h Trend (50 EMA) Filter", value=True)
enable_ob_filter = st.sidebar.checkbox("🐋 Whale Order Book Filter (>55% Buyers)", value=True)

if "paper_trades" not in st.session_state:
    st.session_state.paper_trades = []

def check_btc_trend():
    try:
        res = requests.get(f"{BASE_URL}/klines", params={'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 30}, timeout=5)
        if res.status_code != 200:
            return True, "BTC Data Error"
        ohlcv = res.json()
        closes = pd.Series([float(x[4]) for x in ohlcv])
        ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
        current_btc = closes.iloc[-1]
        is_safe = current_btc >= ema20
        msg = f"BTC: ${current_btc:,.1f} {'🟢 (Safe)' if is_safe else '🔴 (Dumping Risk)'}"
        return is_safe, msg
    except Exception:
        return True, "BTC Check Bypassed"

def check_1h_trend(raw_symbol, current_price):
    try:
        res = requests.get(f"{BASE_URL}/klines", params={'symbol': raw_symbol, 'interval': '1h', 'limit': 60}, timeout=5)
        if res.status_code != 200:
            return True
        ohlcv = res.json()
        closes = pd.Series([float(x[4]) for x in ohlcv])
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        return current_price >= ema50
    except Exception:
        return True

def scan_market_autonomous():
    btc_safe, btc_msg = check_btc_trend()
    if enable_btc_filter and not btc_safe:
        return [], btc_msg

    alerts = []
    res = requests.get(f"{BASE_URL}/ticker/24hr", timeout=10)
    if res.status_code != 200:
        return alerts, btc_msg
        
    tickers = res.json()
    active_usdt_pairs = []
    
    for t in tickers:
        symbol = t.get('symbol', '')
        if symbol.endswith('USDT') and not symbol.endswith(('UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT')):
            active_usdt_pairs.append({
                'symbol': symbol,
                'quoteVolume': float(t.get('quoteVolume', 0)),
                'last': float(t.get('lastPrice', 0)),
                'high': float(t.get('highPrice', 0)),
                'low': float(t.get('lowPrice', 0))
            })
            
    sorted_pairs = sorted(active_usdt_pairs, key=lambda x: x['quoteVolume'], reverse=True)[:limit_pairs]
    current_time = time.time()
    
    for item in sorted_pairs:
        raw_symbol = item['symbol']
        display_symbol = f"{raw_symbol[:-4]}/USDT"
        real_time_price = item['last']
        
        if not real_time_price or raw_symbol == 'BTCUSDT':
            continue
            
        try:
            kline_res = requests.get(
                f"{BASE_URL}/klines", 
                params={'symbol': raw_symbol, 'interval': '15m', 'limit': 40}, 
                timeout=5
            )
            if kline_res.status_code != 200:
                continue
                
            ohlcv = kline_res.json()
            df = pd.DataFrame(ohlcv, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
            ])
            for col in ['close', 'open', 'high', 'low', 'volume']:
                df[col] = df[col].astype(float)
            
            rsi_series = calculate_rsi(df['close'], period=14)
            ema_series = df['close'].ewm(span=20, adjust=False).mean()
            atr_val = calculate_atr(df, period=14)
            pattern_found = detect_candlestick_pattern(df)
            
            current_rsi = rsi_series.iloc[-1]
            current_ema = ema_series.iloc[-1]
            avg_volume = df['volume'][:-1].mean()
            current_volume = df['volume'].iloc[-1]
            open_price = df['open'].iloc[-1]
            live_price_change = ((real_time_price - open_price) / open_price) * 100
            
            if (
                current_volume > (avg_volume * volume_threshold)
                and live_price_change >= price_threshold
                and (rsi_min <= current_rsi <= rsi_max)
                and real_time_price > current_ema
            ):
                if enable_1h_filter and not check_1h_trend(raw_symbol, real_time_price):
                    continue

                buyer_ratio = get_orderbook_buyer_ratio(raw_symbol)
                if enable_ob_filter and buyer_ratio < 55.0:
                    continue

                ai_verdict = "N/A"
                if enable_ai and gemini_key:
                    ai_verdict, _, _ = analyze_with_ai(
                        display_symbol, real_time_price, round(live_price_change, 2),
                        f"{round(current_volume / avg_volume, 1)}x", round(current_rsi, 1),
                        pattern_found, buyer_ratio, btc_msg, gemini_key
                    )

                sl_val = max(0.000001, real_time_price - (atr_val * 1.5))
                tp1_val = real_time_price + (atr_val * 2.5)
                tp2_val = real_time_price + (atr_val * 4.0)
                
                fmt = ".4f" if real_time_price >= 1 else ".6f"
                price_str = format(real_time_price, fmt)
                tp1_str = format(tp1_val, fmt)
                tp2_str = format(tp2_val, fmt)
                sl_str = format(sl_val, fmt)
                high_str = format(item['high'], fmt)
                low_str = format(item['low'], fmt)
                change_str = f"{live_price_change:.2f}"
                spike_str = f"{round(current_volume / avg_volume, 1)}x"
                rsi_str = f"{current_rsi:.1f}"
                
                alerts.append({
                    "raw_symbol": raw_symbol,
                    "Coin": display_symbol,
                    "AI Verdict": ai_verdict,
                    "Pattern": pattern_found,
                    "Live Price ($)": price_str,
                    "15m Change (%)": f"+{change_str}%",
                    "RSI (14)": rsi_str,
                    "Buyers (%)": f"{buyer_ratio}%",
                    "Target 1 (ATR)": tp1_str,
                    "Stop Loss (ATR)": sl_str,
                    "Volume Spike": spike_str
                })
                
                # Cooldown check: පැයකට එක් වරක් Telegram Alert යැවීම
                last_sent = global_state["last_alert_time"].get(display_symbol, 0)
                if current_time - last_sent > 3600:
                    send_telegram_alert(
                        display_symbol, price_str, change_str, spike_str, rsi_str, 
                        tp1_str, tp2_str, sl_str, high_str, low_str, buyer_ratio, pattern_found, ai_verdict
                    )
                    global_state["last_alert_time"][display_symbol] = current_time
                    
        except Exception:
            continue
            
    return alerts, btc_msg

# ================= 24/7 AUTONOMOUS EXECUTION =================
# Cron-Job හෝ ඕනෑම Ping එකකින් පිටුව load වන සැණින් ස්වයංක්‍රීයව scan වේ
with st.spinner("24/7 ස්කෑනරය ක්‍රියාත්මකයි... දත්ත පරීක්ෂා කෙරේ"):
    results, btc_info = scan_market_autonomous()

st.caption(f"🛡️ Market Status: {btc_info} | Scanner Status: Active 24/7 Cloud")

if results:
    st.success(f"🔥 කාසි {len(results)} ක් හමුවිය! (Telegram එකට Alerts යවන ලදී)")
    play_alert_sound()
    df_display = pd.DataFrame(results).drop(columns=['raw_symbol'])
    st.dataframe(df_display, use_container_width=True)
    
    st.markdown("### 📊 Live Charts")
    for coin_data in results:
        st.write(f"**{coin_data['Coin']} — Pattern: `{coin_data['Pattern']}`**")
        render_tradingview_widget(coin_data['raw_symbol'])
else:
    st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි නොමැත. Cron-Job මඟින් පසුබිමෙන් පරීක්ෂා කරමින් පවතී.")
