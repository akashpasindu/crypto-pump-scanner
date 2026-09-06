import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import time

st.set_page_config(page_title="Crypto Scanner & Institutional AI Terminal", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = "AQ.Ab8RN6Kov34e2FAiapWmBpeAtkyAint2-EaxdTwngH8RxeagKQ"
BASE_URL = "https://data-api.binance.vision/api/v3"

def send_scanner_telegram_alert(signal_type, coin, price, change, volume_spike, rsi_val, tp1, tp2, sl, dominance_info, pattern_name, ai_verdict):
    clean_symbol = coin.replace('/', '_')
    icon = "🚨 *Smart Crypto Pump Alert (LONG)*" if signal_type == "PUMP" else "🩸 *Smart Crypto Dump Alert (SHORT)*"
    message = (
        f"{icon}\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"🤖 *AI Verdict:* `{ai_verdict}`\n"
        f"🕯️ *Pattern:* `{pattern_name}`\n"
        f"💵 *Entry Price:* `${price}`\n"
        f"📊 *15m Change:* `{change}%` | *Vol Spike:* `{volume_spike}`\n"
        f"🎯 *RSI (14):* `{rsi_val}` | {dominance_info}\n\n"
        f"🎯 *Dynamic ATR Targets:*\n"
        f"  ├ TP 1: `${tp1}`\n"
        f"  └ TP 2: `${tp2}`\n\n"
        f"🛑 *Dynamic ATR Stop Loss:* `${sl}`\n\n"
        f"🔗 [Trade on Binance](https://www.binance.com/en/trade/{clean_symbol})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=5)

def send_theory_telegram_alert(coin, plan):
    clean_symbol = coin.replace('/', '_')
    theories_used = ", ".join(plan.get("theories_evaluated", []))
    message = (
        f"🏛️ *Multi-Theory Institutional Trade Plan*\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"🎯 *Direction:* `{plan.get('direction', 'LONG')}` | *Confidence:* `{plan.get('confidence', 80)}%`\n"
        f"⚙️ *Leverage:* `{plan.get('leverage', '3x - 5x')}` | *R:R Ratio:* `{plan.get('risk_reward', '1:3')}`\n\n"
        f"📥 *Entry Zone:* `${plan.get('entry_zone', 'Market')}`\n"
        f"🛑 *Stop Loss:* `${plan.get('stop_loss', 'N/A')}`\n\n"
        f"🎯 *Targets:*\n"
        f"  ├ TP 1: `${plan.get('tp1', 'N/A')}`\n"
        f"  └ TP 2: `${plan.get('tp2', 'N/A')}`\n"
        f"  └ TP 3: `${plan.get('tp3', 'N/A')}`\n\n"
        f"🧠 *Theories:* `{theories_used}`\n"
        f"📝 *Thesis:* _{plan.get('summary', 'Setup aligned.')}_\n\n"
        f"🔗 [Trade on Binance](https://www.binance.com/en/trade/{clean_symbol})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=5)

def play_alert_sound():
    sound_code = """<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>"""
    components.html(sound_code, height=0, width=0)

def render_tradingview_widget(symbol_raw):
    widget_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol_raw}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%", "height": 450, "symbol": "BINANCE:{symbol_raw}",
        "interval": "15", "timezone": "Etc/UTC", "theme": "dark", "style": "1",
        "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false,
        "hide_top_toolbar": false, "save_image": false, "container_id": "tradingview_{symbol_raw}"
      }});
      </script>
    </div>
    """
    components.html(widget_code, height=470)

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
    if (c2 > o2) and (c1 < o1) and (c1 <= o2) and (o1 >= c2):
        return "Bearish Engulfing 🔴"
    if (upper_wick1 >= 2 * body1) and (lower_wick1 <= body1 * 0.5) and (c1 <= o1):
        return "Shooting Star 🌠"
    if (c1 < o1) and (c2 < o2) and (c3 < o3) and (c1 < c2 < c3):
        return "Three Black Crows 🩸"
    return "Volume Breakout ⚡"

# Universal Gemini Call Helper (Supports both query parameter and x-goog-api-key headers)
def call_gemini_api(prompt, api_key):
    key_clean = api_key.strip()
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': key_clean
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # Try v1beta first with header
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        if res.status_code == 200:
            return res.json()
        
        # Fallback to query parameter format
        url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key_clean}"
        res_fb = requests.post(url_fallback, headers={'Content-Type': 'application/json'}, json=payload, timeout=12)
        if res_fb.status_code == 200:
            return res_fb.json()
        return {"error_status": res_fb.status_code, "text": res_fb.text}
    except Exception as e:
        return {"exception": str(e)}

def analyze_scanner_ai(signal_type, coin, price, change, volume_spike, rsi, pattern, dom_info, btc_status, api_key):
    if not api_key:
        return "N/A"
    trade_side = "LONG / BUY" if signal_type == "PUMP" else "SHORT / SELL"
    prompt = (
        f"Act as a Crypto Trader. Analyze this 15-minute {signal_type} ({trade_side}) setup: "
        f"Coin: {coin}, Price: ${price}, 15m Change: {change}%, Vol Spike: {volume_spike}, RSI: {rsi}, "
        f"Pattern: {pattern}, Order Book: {dom_info}, Market: {btc_status}. "
        'Respond in JSON: {"verdict": "STRONG BUY" or "SCALP ONLY" or "AVOID", "confidence": 85}'
    )
    res_data = call_gemini_api(prompt, api_key)
    if "candidates" in res_data:
        try:
            match = re.search(r'\{.*\}', res_data['candidates'][0]['content']['parts'][0]['text'], re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return f"{data.get('verdict')} ({data.get('confidence')}%)"
        except Exception:
            pass
    return "Analyzed"

def run_universal_theory_analysis(coin, price, ohlcv_text, rsi, ema20, ema50, atr, dom_info, selected_theories, timeframe, api_key):
    if not api_key:
        return {"error": "API Key missing"}
    theories_list_str = "\n- ".join(selected_theories)
    prompt = f"""
    You are an elite Institutional Quantitative Fund Trader.
    Perform an exhaustive multi-theory analysis on {coin} using these exact theories:
    - {theories_list_str}

    DATA:
    - Pair: {coin} | Timeframe: {timeframe} | Current Price: ${price}
    - RSI (14): {rsi} | 20 EMA: ${ema20:,.4f} | 50 EMA: ${ema50:,.4f} | ATR: ${atr:,.4f} | {dom_info}
    - Recent Candles (OHLCV):
    {ohlcv_text}

    RESPOND ONLY IN STRICT JSON (No markdown ticks, no extra text):
    {{
      "direction": "STRONG LONG",
      "confidence": 85,
      "risk_reward": "1:3.2",
      "leverage": "3x - 5x (Max 10x with strict SL)",
      "entry_zone": "{price} - {price * 0.995:.4f}",
      "tp1": "{price * 1.02:.4f}",
      "tp2": "{price * 1.045:.4f}",
      "tp3": "{price * 1.08:.4f}",
      "stop_loss": "{price * 0.985:.4f}",
      "theories_evaluated": ["SMC", "Wyckoff"],
      "theory_breakdown": [
         {{"theory": "Selected Theory", "finding": "Specific technical finding"}}
      ],
      "summary": "2-sentence institutional trade thesis."
    }}
    """
    res_data = call_gemini_api(prompt, api_key)
    if "candidates" in res_data:
        try:
            match = re.search(r'\{.*\}', res_data['candidates'][0]['content']['parts'][0]['text'], re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            return {"error": f"Parse error: {e}"}
    elif "error_status" in res_data:
        return {"error": f"Google API Error {res_data['error_status']}: {res_data.get('text', '')}"}
    elif "exception" in res_data:
        return {"error": f"Network error: {res_data['exception']}"}
    return {"error": "Unknown API Response"}

@st.cache_resource
def get_global_state():
    return {"last_alert_time": {}}

global_state = get_global_state()

# Sidebar
st.sidebar.header("⚙️ General Settings")
gemini_key = st.sidebar.text_input("Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")

st.sidebar.header("📡 24/7 Scanner Filters")
scan_mode = st.sidebar.radio("Scanner Direction", ["Both (Pump & Dump)", "Pump Only (Long)", "Dump Only (Short)"])
volume_threshold = st.sidebar.slider("Volume Spike Multiplier", 1.2, 5.0, 1.5, step=0.1)
price_threshold = st.sidebar.slider("අවම මිල වෙනස (%)", 0.5, 5.0, 1.2, step=0.1)
pump_rsi_min = st.sidebar.slider("Pump: Min RSI", 30, 60, 45)
pump_rsi_max = st.sidebar.slider("Pump: Max RSI", 60, 85, 75)
dump_rsi_min = st.sidebar.slider("Dump: Min RSI", 15, 40, 25)
dump_rsi_max = st.sidebar.slider("Dump: Max RSI", 40, 60, 55)
limit_pairs = st.sidebar.number_input("Scan Pairs Limit", min_value=10, max_value=100, value=30, step=10)

def check_btc_trend():
    try:
        res = requests.get(f"{BASE_URL}/klines", params={'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 30}, timeout=5)
        if res.status_code != 200:
            return "NEUTRAL", "BTC Data Error"
        ohlcv = res.json()
        closes = pd.Series([float(x[4]) for x in ohlcv])
        ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
        is_bullish = closes.iloc[-1] >= ema20
        return ("BULLISH" if is_bullish else "BEARISH"), f"BTC: ${closes.iloc[-1]:,.1f} {'🟢 (Above 20 EMA)' if is_bullish else '🔴 (Below 20 EMA)'}"
    except Exception:
        return "NEUTRAL", "BTC Check Bypassed"

def check_1h_trend(raw_symbol, current_price, signal_type):
    try:
        res = requests.get(f"{BASE_URL}/klines", params={'symbol': raw_symbol, 'interval': '1h', 'limit': 60}, timeout=5)
        if res.status_code != 200:
            return True
        closes = pd.Series([float(x[4]) for x in res.json()])
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        return (current_price >= ema50) if signal_type == "PUMP" else (current_price <= ema50)
    except Exception:
        return True

# ================= TABS =================
tab_theory, tab_scanner = st.tabs(["🏛️ Multi-Theory Custom Analyzer", "📡 24/7 Autonomous Scanner"])

# ----------------- TAB 1: MULTI-THEORY CUSTOM ANALYZER -----------------
with tab_theory:
    st.subheader("🏛️ Universal Multi-Theory Analyzer (On-Demand Deep Dive)")
    st.write("ඕනෑම කාසියක් තෝරාගෙන ලොව ප්‍රමුඛ පෙළේ Technical Theories එකවර හෝ අවශ්‍ය ප්‍රමාණය තෝරා ගැඹුරු විශ්ලේෂණයක් සහ Actionable Trade Setup එකක් ලබාගන්න.")

    ALL_THEORIES = [
        "Smart Money Concepts (SMC / ICT) — Order Blocks, FVG, Liquidity Sweeps",
        "Wyckoff Method — Accumulation / Distribution, Spring, Upthrust",
        "Dow Theory & Market Structure — BOS, CHoCH, Swing Highs/Lows",
        "Elliott Wave Theory — Impulse Waves & Corrective ABC Patterns",
        "Supply & Demand Imbalance — Fresh Zones, Compression, Engulfing",
        "Market Profile & Volume Profile — Point of Control (POC), Value Area",
        "Harmonic Patterns & Fibonacci Levels — Gartley, Bat, 0.618 Golden Pocket",
        "Classical Chart Patterns — Head & Shoulders, Double Top/Bottom, Flags, Triangles",
        "Candlestick Patterns — Pinbars, Hammers, Morning/Evening Stars, Marubozu",
        "Gann Theory & Angular Support/Resistance",
        "Moving Average Trend Confluence — 20/50/200 EMA Alignments & Golden Cross",
        "RSI Divergence & Momentum Exhaustion — Hidden & Regular Divergences"
    ]

    th_col1, th_col2 = st.columns([1, 2])
    with th_col1:
        select_all_th = st.checkbox("සියලුම Theories 12ම එකවර තෝරන්න", value=True)
    with th_col2:
        if select_all_th:
            active_theories = ALL_THEORIES
            st.info("Theories 12ම සක්‍රීයයි (Full Multi-Confluence Mode)")
        else:
            active_theories = st.multiselect("අවශ්‍ය Theories තෝරන්න:", options=ALL_THEORIES, default=[ALL_THEORIES[0], ALL_THEORIES[1], ALL_THEORIES[2], ALL_THEORIES[4], ALL_THEORIES[11]])

    st.write("---")
    in_col1, in_col2, in_col3 = st.columns([2, 1, 1])
    with in_col1:
        custom_coin_symbol = st.text_input("කාසියේ නම (Coin Symbol):", value="SOL", placeholder="e.g. BTC, ETH, SOL, XRP, PEPE").strip().upper()
    with in_col2:
        custom_tf = st.selectbox("Timeframe:", ["15m", "1h", "4h", "1d"], index=0)
    with in_col3:
        st.write("##")
        run_theory_btn = st.button("🚀 Deep Theory Analysis", use_container_width=True)

    if run_theory_btn and custom_coin_symbol:
        custom_pair = f"{custom_coin_symbol}USDT"
        if not active_theories:
            st.warning("⚠️ කරුණාකර අවම වශයෙන් එක් Theory එකක් තෝරන්න.")
        else:
            with st.spinner(f"Binance දත්ත සහ Theories {len(active_theories)} ක් හරහා {custom_pair} විශ්ලේෂණය කරමින් පවතී..."):
                try:
                    t_res = requests.get(f"{BASE_URL}/ticker/24hr", params={'symbol': custom_pair}, timeout=5)
                    k_res = requests.get(f"{BASE_URL}/klines", params={'symbol': custom_pair, 'interval': custom_tf, 'limit': 45}, timeout=5)
                    if t_res.status_code == 200 and k_res.status_code == 200:
                        real_p = float(t_res.json().get('lastPrice', 0))
                        df_th = pd.DataFrame(k_res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                        for col in ['close', 'open', 'high', 'low', 'volume']:
                            df_th[col] = df_th[col].astype(float)
                        
                        th_rsi = calculate_rsi(df_th['close'], period=14).iloc[-1]
                        th_ema20 = df_th['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                        th_ema50 = df_th['close'].ewm(span=50, adjust=False).mean().iloc[-1]
                        th_atr = calculate_atr(df_th, period=14)
                        b_pct, s_pct = get_orderbook_ratio(custom_pair)
                        dom_info_str = f"Buyers: {b_pct}% | Sellers: {s_pct}%"
                        candles_txt = df_th[['open', 'high', 'low', 'close', 'volume']].tail(12).to_string(index=False)
                        
                        plan = run_universal_theory_analysis(custom_pair, real_p, candles_txt, round(th_rsi, 1), th_ema20, th_ema50, th_atr, dom_info_str, active_theories, custom_tf, gemini_key)
                        
                        if "error" in plan:
                            st.error(f"දෝෂය: {plan['error']}")
                        else:
                            st.markdown("---")
                            dir_label = plan.get('direction', 'NEUTRAL')
                            color_icon = "🟢" if "LONG" in dir_label else ("🔴" if "SHORT" in dir_label else "🟡")
                            st.markdown(f"## {color_icon} Institutional Setup: **{dir_label}** for **{custom_pair}**")
                            
                            pm1, pm2, pm3, pm4, pm5 = st.columns(5)
                            pm1.metric("Live Price", f"${real_p:,.4f}")
                            pm2.metric("Confidence", f"{plan.get('confidence', 80)}%")
                            pm3.metric("R:R Ratio", plan.get('risk_reward', '1:3'))
                            pm4.metric("Recommended Leverage", plan.get('leverage', '3x - 5x'))
                            pm5.metric("Whale Flow", f"🟢 {b_pct}% / 🔴 {s_pct}%")
                            
                            chart_c, card_c = st.columns([3, 2])
                            with chart_c:
                                st.markdown("### 📊 Interactive Technical Chart")
                                render_tradingview_widget(custom_pair)
                            with card_c:
                                st.markdown("### 🎯 Complete Actionable Trade Card")
                                plan_table = {
                                    "Trade Parameter": ["Direction", "Entry Zone", "Stop Loss (Invalidation)", "Take Profit 1", "Take Profit 2", "Take Profit 3 (Runner)", "Safe Leverage"],
                                    "Value": [
                                        dir_label, f"${plan.get('entry_zone', 'Market')}", f"${plan.get('stop_loss', 'N/A')}",
                                        f"${plan.get('tp1', 'N/A')}", f"${plan.get('tp2', 'N/A')}", f"${plan.get('tp3', 'N/A')}",
                                        plan.get('leverage', '3x - 5x')
                                    ]
                                }
                                st.dataframe(pd.DataFrame(plan_table), use_container_width=True, hide_index=True)
                                st.markdown("#### 📝 Trade Thesis")
                                st.info(plan.get('summary', 'Setup aligned.'))
                                if st.button("📲 Send Plan to Telegram", use_container_width=True):
                                    t_res_msg = send_theory_telegram_alert(f"{custom_coin_symbol}/USDT", plan)
                                    if t_res_msg.status_code == 200:
                                        st.success("✅ Trade Plan එක සාර්ථකව Telegram වෙත යවන ලදී!")
                            
                            st.markdown("---")
                            st.markdown("### 🧠 Theory-by-Theory Confluence Findings")
                            breakdown = plan.get("theory_breakdown", [])
                            if breakdown:
                                b_cols = st.columns(min(len(breakdown), 3))
                                for i_idx, b_item in enumerate(breakdown):
                                    with b_cols[i_idx % 3]:
                                        st.success(f"**{b_item.get('theory')}**")
                                        st.write(b_item.get('finding'))
                    else:
                        st.error(f"Binance හි `{custom_pair}` හමු නොවීය.")
                except Exception as ex:
                    st.error(f"දෝෂයක් ඇති විය: {ex}")

# ----------------- TAB 2: 24/7 MARKET SCANNER -----------------
with tab_scanner:
    btc_status, btc_msg = check_btc_trend()
    st.subheader("📡 Live Market Scanner")
    st.caption(f"🛡️ Market Context: {btc_msg}")

    run_scan_manual = st.button("🔍 Scan Market Now", use_container_width=True)

    def scan_market_now():
        alerts = []
        res = requests.get(f"{BASE_URL}/ticker/24hr", timeout=10)
        if res.status_code != 200:
            return alerts
        tickers = res.json()
        active_usdt_pairs = []
        for t in tickers:
            symbol = t.get('symbol', '')
            if symbol.endswith('USDT') and not symbol.endswith(('UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT')):
                active_usdt_pairs.append({'symbol': symbol, 'quoteVolume': float(t.get('quoteVolume', 0)), 'last': float(t.get('lastPrice', 0))})
        sorted_pairs = sorted(active_usdt_pairs, key=lambda x: x['quoteVolume'], reverse=True)[:limit_pairs]
        current_time = time.time()
        
        for item in sorted_pairs:
            raw_symbol = item['symbol']
            display_symbol = f"{raw_symbol[:-4]}/USDT"
            real_time_price = item['last']
            if not real_time_price or raw_symbol == 'BTCUSDT':
                continue
            try:
                kline_res = requests.get(f"{BASE_URL}/klines", params={'symbol': raw_symbol, 'interval': '15m', 'limit': 40}, timeout=5)
                if kline_res.status_code != 200:
                    continue
                df = pd.DataFrame(kline_res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
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
                is_vol_spike = current_volume > (avg_volume * volume_threshold)
                buyer_ratio, seller_ratio = get_orderbook_ratio(raw_symbol)
                
                signal = None
                if scan_mode in ["Both (Pump & Dump)", "Pump Only (Long)"]:
                    if is_vol_spike and live_price_change >= price_threshold and (pump_rsi_min <= current_rsi <= pump_rsi_max) and real_time_price > current_ema:
                        if not (btc_status == "BEARISH") and check_1h_trend(raw_symbol, real_time_price, "PUMP") and buyer_ratio >= 55.0:
                            signal = "PUMP"
                if not signal and scan_mode in ["Both (Pump & Dump)", "Dump Only (Short)"]:
                    if is_vol_spike and live_price_change <= -price_threshold and (dump_rsi_min <= current_rsi <= dump_rsi_max) and real_time_price < current_ema:
                        if not (btc_status == "BULLISH") and check_1h_trend(raw_symbol, real_time_price, "DUMP") and seller_ratio >= 55.0:
                            signal = "DUMP"
                
                if signal:
                    sl_val = max(0.000001, real_time_price - (atr_val * 1.5)) if signal == "PUMP" else (real_time_price + (atr_val * 1.5))
                    tp1_val = (real_time_price + (atr_val * 2.5)) if signal == "PUMP" else max(0.000001, real_time_price - (atr_val * 2.5))
                    tp2_val = (real_time_price + (atr_val * 4.0)) if signal == "PUMP" else max(0.000001, real_time_price - (atr_val * 4.0))
                    dom_str = f"Buyers {buyer_ratio}%" if signal == "PUMP" else f"Sellers {seller_ratio}%"
                    change_str = f"{live_price_change:+.2f}"
                    
                    fmt = ".4f" if real_time_price >= 1 else ".6f"
                    ai_v = analyze_scanner_ai(signal, display_symbol, real_time_price, change_str, f"{round(current_volume/avg_volume,1)}x", round(current_rsi,1), pattern_found, dom_str, btc_msg, gemini_key)
                    
                    alerts.append({
                        "raw_symbol": raw_symbol, "Type": "🟢 PUMP" if signal == "PUMP" else "🔴 DUMP",
                        "Coin": display_symbol, "Live Price ($)": format(real_time_price, fmt),
                        "15m Change": f"{change_str}%", "RSI": f"{current_rsi:.1f}", "Pattern": pattern_found,
                        "AI Verdict": ai_v, "TP 1": format(tp1_val, fmt), "Stop Loss": format(sl_val, fmt),
                        "Vol Spike": f"{round(current_volume/avg_volume,1)}x", "Dominance": dom_str
                    })
                    
                    last_sent = global_state["last_alert_time"].get(display_symbol, 0)
                    if current_time - last_sent > 3600:
                        send_scanner_telegram_alert(signal, display_symbol, format(real_time_price, fmt), change_str, f"{round(current_volume/avg_volume,1)}x", f"{current_rsi:.1f}", format(tp1_val, fmt), format(tp2_val, fmt), format(sl_val, fmt), dom_str, pattern_found, ai_v)
                        global_state["last_alert_time"][display_symbol] = current_time
            except Exception:
                continue
        return alerts

    if run_scan_manual:
        with st.spinner("Market එක Scan වෙමින් පවතී..."):
            results = scan_market_now()
            if results:
                st.success(f"🔥 කාසි {len(results)} ක් හමුවිය!")
                play_alert_sound()
                st.dataframe(pd.DataFrame(results).drop(columns=['raw_symbol']), use_container_width=True)
            else:
                st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි හමු නොවීය.")
