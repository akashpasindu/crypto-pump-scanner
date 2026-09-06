import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import time

st.set_page_config(page_title="Crypto Institutional AI Scanner", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = "AQ.Ab8RN6Kov34e2FAiapWmBpeAtkyAint2-EaxdTwngH8RxeagKQ"

def send_telegram_alert(signal_type, coin, price, change, volume_spike, rsi_val, tp1, tp2, sl, dominance_info, ai_data):
    clean_symbol = coin.replace('/', '_')
    icon = "🏛️ *Institutional SMC/ICT Alert (LONG)*" if signal_type == "PUMP" else "🩸 *Institutional SMC/ICT Alert (SHORT)*"
    
    confluences = ", ".join(ai_data.get('theories_confluent', ['Price Action']))
    
    message = (
        f"{icon}\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"🎖️ *AI Quality Grade:* `{ai_data.get('quality_grade', 'A')}` | Confidence: `{ai_data.get('confidence', 80)}%`\n"
        f"🎯 *Verdict:* `{ai_data.get('verdict', 'ENTER')}`\n"
        f"🧠 *Key Theories Aligned:* `{confluences}`\n"
        f"🧱 *SMC Structure:* `{ai_data.get('market_structure', 'BOS')}`\n"
        f"📝 *Analysis:* _{ai_data.get('trade_logic', 'Institutional setup aligned.')}_\n\n"
        f"💵 *Entry Price:* `${price}`\n"
        f"📊 *15m Change:* `{change}%` | *Vol Spike:* `{volume_spike}`\n"
        f"🎯 *RSI (14):* `{rsi_val}` | {dominance_info}\n\n"
        f"🎯 *Targets (ATR / FVG Mapped):*\n"
        f"  ├ TP 1: `${tp1}`\n"
        f"  └ TP 2: `${tp2}`\n"
        f"🛑 *Dynamic Invalidation (SL):* `${sl}`\n\n"
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

# ================= INSTITUTIONAL AI ANALYZER ENGINE =================
def analyze_with_institutional_ai(signal_type, coin, price, change, volume_spike, rsi, ohlcv_summary, dom_info, btc_status, api_key):
    if not api_key:
        return {
            "verdict": "NO API KEY",
            "quality_grade": "N/A",
            "confidence": 0,
            "theories_confluent": ["None"],
            "market_structure": "Unknown",
            "trade_logic": "API Key is missing",
            "risk": "High"
        }
    
    trade_side = "LONG" if signal_type == "PUMP" else "SHORT"
    
    prompt = f"""
    You are a Senior Institutional Crypto Fund Trader specializing in Wyckoff, Smart Money Concepts (SMC/ICT), Dow Theory, and Volume/Liquidity Profile.
    
    Analyze this potential {trade_side} setup for {coin}:
    - Signal Side: {trade_side}
    - Current Price: ${price}
    - 15m Price Momentum: {change}%
    - Volume Multiplier: {volume_spike}
    - RSI (14): {rsi}
    - Order Book Dominance: {dom_info}
    - BTC Market Context: {btc_status}
    - Recent 10 Candles Summary (Open, High, Low, Close, Volume):
    {ohlcv_summary}

    EVALUATE BASED ON THESE THEORIES:
    1. Dow Theory & Market Structure (BOS / CHoCH, Higher Highs/Lows)
    2. Smart Money Concepts (Order Block, FVG - Fair Value Gap, Liquidity Sweep)
    3. Wyckoff Method (Accumulation / Distribution / Spring / SOS)
    4. Supply / Demand Imbalance & Key Support/Resistance
    5. Candlestick & Classical Chart Patterns

    CRITICAL RULE:
    Only give a high rating if AT LEAST 3 theories confirm this setup (Multi-Confluence).
    
    Respond ONLY in strict, valid JSON without codeblocks or extra text:
    {{
      "verdict": "STRONG LONG" or "RISKY SCALP" or "AVOID",
      "quality_grade": "A+" or "A" or "B" or "REJECT",
      "confidence": 88,
      "theories_confluent": ["SMC Order Block", "Wyckoff Spring", "BOS Confirmation"],
      "market_structure": "Bullish BOS above 15m swing",
      "trade_logic": "Brief 1-sentence institutional trade thesis",
      "risk": "Low" or "Medium" or "High"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        return {"verdict": "ERROR", "quality_grade": "REJECT", "confidence": 0, "theories_confluent": [], "market_structure": "N/A", "trade_logic": f"HTTP {res.status_code}", "risk": "High"}
    except Exception as e:
        return {"verdict": "TIMEOUT", "quality_grade": "REJECT", "confidence": 0, "theories_confluent": [], "market_structure": "N/A", "trade_logic": "AI Timeout", "risk": "High"}

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
        "height": 420,
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
    components.html(widget_code, height=440)

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

def get_orderbook_ratio(raw_symbol):
    try:
        res = requests.get(f"{BASE_URL}/depth", params={'symbol': raw_symbol, 'limit': 20}, timeout=4)
        if res.status_code != 200:
            return 50.0, 50.0
        data = res.json()
        bids = sum([float(b[1]) for b in data.get('bids', [])])
        asks = sum([float(a[1]) for a in data.get('asks', [])])
        total = bids + asks
        return (round((bids / total) * 100, 1), round((asks / total) * 100, 1)) if total > 0 else (50.0, 50.0)
    except Exception:
        return 50.0, 50.0

st.title("🏛️ Crypto Institutional AI Scanner (SMC / Wyckoff / Multi-Theory)")

# Sidebar Configuration
st.sidebar.header("🎯 Mode & Confluence Settings")
scan_mode = st.sidebar.radio("Scan Direction", ["Both (Pump & Dump)", "Pump Only (Long)", "Dump Only (Short)"])
min_grade = st.sidebar.selectbox("අවම AI Quality Grade එක (Alerts සඳහා)", ["A+ Only (Strict Confluence)", "A and Above (Recommended)", "All Signals"], index=1)

st.sidebar.header("📊 Momentum Parameters")
volume_threshold = st.sidebar.slider("Volume Multiplier", 1.2, 5.0, 1.4, step=0.1)
price_threshold = st.sidebar.slider("අවම මිල වෙනස (%)", 0.5, 5.0, 1.0, step=0.1)
limit_pairs = st.sidebar.number_input("පරීක්ෂා කළ යුතු Pairs ගණන", min_value=10, max_value=150, value=60, step=10)

st.sidebar.header("🛡️ Filters")
enable_btc_filter = st.sidebar.checkbox("BTC Trend Protection", value=True)
enable_1h_filter = st.sidebar.checkbox("1h Trend (50 EMA) Confirmation", value=True)

st.sidebar.header("🤖 AI Engine")
gemini_key = st.sidebar.text_input("Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")

@st.cache_resource
def get_global_state():
    return {"last_alert_time": {}}

global_state = get_global_state()

def check_btc_trend():
    try:
        res = requests.get(f"{BASE_URL}/klines", params={'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 30}, timeout=5)
        if res.status_code != 200:
            return "NEUTRAL", "BTC Data Error"
        ohlcv = res.json()
        closes = pd.Series([float(x[4]) for x in ohlcv])
        ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
        current_btc = closes.iloc[-1]
        is_bullish = current_btc >= ema20
        status = "BULLISH" if is_bullish else "BEARISH"
        msg = f"BTC: ${current_btc:,.1f} {'🟢 (Bullish Market Structure)' if is_bullish else '🔴 (Bearish Pressure)'}"
        return status, msg
    except Exception:
        return "NEUTRAL", "BTC Check Bypassed"

def check_1h_trend(raw_symbol, current_price, signal_type):
    try:
        res = requests.get(f"{BASE_URL}/klines", params={'symbol': raw_symbol, 'interval': '1h', 'limit': 60}, timeout=5)
        if res.status_code != 200:
            return True
        ohlcv = res.json()
        closes = pd.Series([float(x[4]) for x in ohlcv])
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        return (current_price >= ema50) if signal_type == "PUMP" else (current_price <= ema50)
    except Exception:
        return True

btc_status, btc_msg = check_btc_trend()

# ================= 🔍 CUSTOM SINGLE COIN MULTI-THEORY ANALYZER =================
st.subheader("🔍 Institutional Coin Analyzer (On-Demand Deep Dive)")
custom_col1, custom_col2 = st.columns([3, 1])

with custom_col1:
    custom_symbol_input = st.text_input("පරීක්ෂා කිරීමට අවශ්‍ය Coin එක (උදා: SOL, BTC, ETH, DOGE, INJ):", value="SOL").strip().upper()

with custom_col2:
    st.write("##")
    analyze_custom_btn = st.button("Analyze Multi-Theories 🚀", use_container_width=True)

if analyze_custom_btn and custom_symbol_input:
    target_pair = f"{custom_symbol_input}USDT"
    with st.spinner(f"SMC, Wyckoff, Dow Theory සහ Candlestick රටා {target_pair} සඳහා ගණනය කරමින් පවතී..."):
        try:
            ticker_res = requests.get(f"{BASE_URL}/ticker/24hr", params={'symbol': target_pair}, timeout=5)
            kline_res = requests.get(f"{BASE_URL}/klines", params={'symbol': target_pair, 'interval': '15m', 'limit': 40}, timeout=5)
            
            if ticker_res.status_code == 200 and kline_res.status_code == 200:
                t_data = ticker_res.json()
                k_data = kline_res.json()
                
                real_time_price = float(t_data.get('lastPrice', 0))
                df_custom = pd.DataFrame(k_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                    'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
                ])
                for col in ['close', 'open', 'high', 'low', 'volume']:
                    df_custom[col] = df_custom[col].astype(float)
                
                c_rsi = calculate_rsi(df_custom['close'], period=14).iloc[-1]
                c_ema20 = df_custom['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                c_atr = calculate_atr(df_custom, period=14)
                c_buyer_pct, c_seller_pct = get_orderbook_ratio(target_pair)
                
                c_open = df_custom['open'].iloc[-1]
                c_change = ((real_time_price - c_open) / c_open) * 100
                c_avg_vol = df_custom['volume'][:-1].mean()
                c_cur_vol = df_custom['volume'].iloc[-1]
                c_vol_spike = f"{round(c_cur_vol / c_avg_vol, 1)}x" if c_avg_vol > 0 else "1.0x"
                
                # 10 Candle OHLC Summary for AI
                candles_summary = df_custom[['open', 'high', 'low', 'close', 'volume']].tail(10).to_string(index=False)
                signal_type_guess = "PUMP" if real_time_price >= c_ema20 else "DUMP"
                c_dom_str = f"Buyers {c_buyer_pct}% | Sellers {c_seller_pct}%"
                
                ai_res = analyze_with_institutional_ai(
                    signal_type_guess, f"{custom_symbol_input}/USDT", real_time_price, f"{c_change:+.2f}",
                    c_vol_spike, f"{c_rsi:.1f}", candles_summary, c_dom_str, btc_msg, gemini_key
                )
                
                # Targets
                sl_long = max(0.000001, real_time_price - (c_atr * 1.5))
                tp1_long = real_time_price + (c_atr * 2.5)
                sl_short = real_time_price + (c_atr * 1.5)
                tp1_short = max(0.000001, real_time_price - (c_atr * 2.5))
                
                # Render Results
                st.markdown(f"### 🏛️ Institutional Confluence Report: **{custom_symbol_input}/USDT**")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Live Price", f"${real_time_price:,.4f}")
                m2.metric("AI Quality Grade", ai_res.get('quality_grade', 'N/A'), f"{ai_res.get('confidence', 0)}% Confidence")
                m3.metric("RSI (14)", f"{c_rsi:.1f}")
                m4.metric("Volume Spike", c_vol_spike)
                m5.metric("Whale Flow", f"🟢 {c_buyer_pct}% / 🔴 {c_seller_pct}%")
                
                c_col_chart, c_col_ai = st.columns([3, 1])
                with c_col_chart:
                    render_tradingview_widget(target_pair)
                with c_col_ai:
                    st.markdown("#### 🧠 Institutional Breakdown")
                    st.success(f"**Verdict:** {ai_res.get('verdict')}")
                    st.info(f"**Theories Aligned:**\n- " + "\n- ".join(ai_res.get('theories_confluent', ['None'])))
                    st.write(f"**Market Structure:** `{ai_res.get('market_structure')}`")
                    st.write(f"**Fund Logic:** _{ai_res.get('trade_logic')}_")
                    st.write(f"**Risk Profile:** `{ai_res.get('risk')}`")
                    st.write(f"**Long Range:** TP1: `${tp1_long:,.4f}` | SL: `${sl_long:,.4f}`")
                    st.write(f"**Short Range:** TP1: `${tp1_short:,.4f}` | SL: `${sl_short:,.4f}`")
            else:
                st.error(f"Binance හි `{target_pair}` යුගලය හමු නොවීය.")
        except Exception as e:
            st.error(f"දෝෂයක් ඇති විය: {e}")

st.write("---")

# ================= 📡 24/7 AUTONOMOUS MARKET SCANNER =================
st.subheader("📡 Live 24/7 Multi-Theory Confluence Scanner")

def scan_market_autonomous():
    alerts = []
    res = requests.get(f"{BASE_URL}/ticker/24hr", timeout=10)
    if res.status_code != 200:
        return alerts
        
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
                params={'symbol': raw_symbol, 'interval': '15m', 'limit': 35}, 
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
            
            current_rsi = rsi_series.iloc[-1]
            current_ema = ema_series.iloc[-1]
            avg_volume = df['volume'][:-1].mean()
            current_volume = df['volume'].iloc[-1]
            open_price = df['open'].iloc[-1]
            live_price_change = ((real_time_price - open_price) / open_price) * 100
            
            is_volume_spike = current_volume > (avg_volume * volume_threshold)
            buyer_ratio, seller_ratio = get_orderbook_ratio(raw_symbol)
            
            signal_detected = None
            
            # Long Check
            if scan_mode in ["Both (Pump & Dump)", "Pump Only (Long)"]:
                if (
                    is_volume_spike
                    and live_price_change >= price_threshold
                    and (42 <= current_rsi <= 75)
                    and real_time_price > current_ema
                ):
                    if not (enable_btc_filter and btc_status == "BEARISH"):
                        if not (enable_1h_filter and not check_1h_trend(raw_symbol, real_time_price, "PUMP")):
                            signal_detected = "PUMP"
                            
            # Short Check
            if not signal_detected and scan_mode in ["Both (Pump & Dump)", "Dump Only (Short)"]:
                if (
                    is_volume_spike
                    and live_price_change <= -price_threshold
                    and (25 <= current_rsi <= 58)
                    and real_time_price < current_ema
                ):
                    if not (enable_btc_filter and btc_status == "BULLISH"):
                        if not (enable_1h_filter and not check_1h_trend(raw_symbol, real_time_price, "DUMP")):
                            signal_detected = "DUMP"

            if signal_detected:
                # Prepare summary for Gemini Institutional Engine
                candles_summary = df[['open', 'high', 'low', 'close', 'volume']].tail(8).to_string(index=False)
                dom_str = f"Buyers: {buyer_ratio}% | Sellers: {seller_ratio}%"
                change_str = f"{live_price_change:+.2f}"
                spike_str = f"{round(current_volume / avg_volume, 1)}x"
                
                ai_data = analyze_with_institutional_ai(
                    signal_detected, display_symbol, real_time_price, change_str,
                    spike_str, f"{current_rsi:.1f}", candles_summary, dom_str, btc_msg, gemini_key
                )
                
                # Quality Filter
                grade = ai_data.get('quality_grade', 'B')
                if min_grade == "A+ Only (Strict Confluence)" and grade != "A+":
                    continue
                elif min_grade == "A and Above (Recommended)" and grade not in ["A+", "A"]:
                    continue
                elif grade == "REJECT":
                    continue

                if signal_detected == "PUMP":
                    sl_val = max(0.000001, real_time_price - (atr_val * 1.5))
                    tp1_val = real_time_price + (atr_val * 2.5)
                    tp2_val = real_time_price + (atr_val * 4.0)
                else:
                    sl_val = real_time_price + (atr_val * 1.5)
                    tp1_val = max(0.000001, real_time_price - (atr_val * 2.5))
                    tp2_val = max(0.000001, real_time_price - (atr_val * 4.0))

                fmt = ".4f" if real_time_price >= 1 else ".6f"
                price_str = format(real_time_price, fmt)
                tp1_str = format(tp1_val, fmt)
                tp2_str = format(tp2_val, fmt)
                sl_str = format(sl_val, fmt)
                rsi_str = f"{current_rsi:.1f}"
                
                alerts.append({
                    "raw_symbol": raw_symbol,
                    "Type": "🟢 LONG" if signal_detected == "PUMP" else "🔴 SHORT",
                    "Coin": display_symbol,
                    "Grade": grade,
                    "Verdict": ai_data.get('verdict', 'ENTER'),
                    "Theories": ", ".join(ai_data.get('theories_confluent', [])),
                    "Live Price ($)": price_str,
                    "15m Change": f"{change_str}%",
                    "RSI (14)": rsi_str,
                    "TP1 (ATR/FVG)": tp1_str,
                    "SL (Invalidation)": sl_str,
                    "Logic": ai_data.get('trade_logic', '')
                })
                
                # Cooldown: පැයකට එක් alert එකක් පමණි
                last_sent = global_state["last_alert_time"].get(display_symbol, 0)
                if current_time - last_sent > 3600:
                    send_telegram_alert(
                        signal_detected, display_symbol, price_str, change_str, spike_str, rsi_str, 
                        tp1_str, tp2_str, sl_str, dom_str, ai_data
                    )
                    global_state["last_alert_time"][display_symbol] = current_time
                    
        except Exception:
            continue
            
    return alerts

with st.spinner("Market එක Multi-Theory Confluence (SMC, Wyckoff, Dow Theory) අනුව ස්කෑන් වෙමින් පවතී..."):
    results = scan_market_autonomous()

st.caption(f"🛡️ Market Context: {btc_msg} | Confluence Mode: {min_grade} | 24/7 Cloud Active")

if results:
    st.success(f"🏛️ Institutional Confluence කාසි {len(results)} ක් හමුවිය! (Telegram එකට Alerts යවන ලදී)")
    play_alert_sound()
    df_display = pd.DataFrame(results).drop(columns=['raw_symbol'])
    st.dataframe(df_display, use_container_width=True)
    
    st.markdown("### 📊 Live Charts & Structure")
    for coin_data in results:
        st.write(f"**{coin_data['Type']} — {coin_data['Coin']} | Grade: `{coin_data['Grade']}` | Theories: `{coin_data['Theories']}`**")
        render_tradingview_widget(coin_data['raw_symbol'])
else:
    st.info("මේ මොහොතේ Institutional Multi-Confluence සපුරාලූ (Grade A/A+) කාසි නොමැත. Cron-Job මඟින් පසුබිමෙන් පරීක්ෂා කරමින් පවතී.")
