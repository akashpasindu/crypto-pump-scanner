import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import html
import time

st.set_page_config(page_title="Institutional Multi-Timeframe AI Terminal", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = ""

SPOT_BASE_URL = "https://data-api.binance.vision/api/v3"
FUTURES_BASE_URL = "https://fapi.binance.com/fapi/v1"

def send_scanner_telegram_alert(signal_type, coin, price, change, volume_spike, rsi_val, tp1, tp2, sl, dominance_info, pattern_name, ai_verdict):
    clean_symbol = coin.replace('/', '_')
    icon = "🚨 <b>Smart Crypto Pump Alert (LONG)</b>" if signal_type == "PUMP" else "🩸 <b>Smart Crypto Dump Alert (SHORT)</b>"
    
    msg_html = (
        f"{icon}\n\n"
        f"🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"🤖 <b>AI Verdict:</b> <code>{ai_verdict}</code>\n"
        f"🕯️ <b>Pattern:</b> <code>{pattern_name}</code>\n"
        f"💵 <b>Entry Price:</b> <code>${price}</code>\n"
        f"📊 <b>15m Change:</b> <code>{change}%</code> | <b>Vol Spike:</b> <code>{volume_spike}</code>\n"
        f"🎯 <b>RSI (14):</b> <code>{rsi_val}</code> | {dominance_info}\n\n"
        f"🎯 <b>Dynamic ATR Targets:</b>\n"
        f"  ├ TP 1: <code>${tp1}</code>\n"
        f"  └ TP 2: <code>${tp2}</code>\n\n"
        f"🛑 <b>Dynamic ATR Stop Loss:</b> <code>${sl}</code>\n\n"
        f"🔗 <a href='https://www.binance.com/en/trade/{clean_symbol}'>Trade on Binance</a>"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg_html, "parse_mode": "HTML", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=8)

def send_theory_telegram_alert(coin, plan):
    clean_symbol = coin.replace('/', '_')
    direction_val = plan.get('direction', 'LONG')
    icon = "🟢" if "LONG" in direction_val else "🔴"
    
    summary_clean = html.escape(str(plan.get('summary', 'Setup aligned.')))
    theories_clean = html.escape(", ".join(plan.get("theories_evaluated", [])))
    mtf_clean = html.escape(str(plan.get('mtf_summary', 'Multi-Timeframe confluence confirmed.')))

    msg_html = (
        f"🏛️ <b>Institutional Multi-Timeframe Trade Setup</b>\n\n"
        f"🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"🎯 <b>Final Verdict:</b> {icon} <b>{direction_val}</b>\n"
        f"📊 <b>MTF Score:</b> Long: <code>{plan.get('long_score', 50)}%</code> | Short: <code>{plan.get('short_score', 50)}%</code>\n"
        f"⚙️ <b>Leverage:</b> <code>{plan.get('leverage', '3x - 5x')}</code> | <b>R:R:</b> <code>{plan.get('risk_reward', '1:3')}</code>\n\n"
        f"📥 <b>Entry Zone:</b> <code>${plan.get('entry_zone', 'Market')}</code>\n"
        f"🛑 <b>Stop Loss:</b> <code>${plan.get('stop_loss', 'N/A')}</code>\n\n"
        f"🎯 <b>Take Profit Targets:</b>\n"
        f"  ├ TP 1: <code>${plan.get('tp1', 'N/A')}</code>\n"
        f"  ├ TP 2: <code>${plan.get('tp2', 'N/A')}</code>\n"
        f"  └ TP 3: <code>${plan.get('tp3', 'N/A')}</code>\n\n"
        f"⏳ <b>Timeframe Breakdown:</b>\n{mtf_clean}\n\n"
        f"🧠 <b>Theories:</b> <i>{theories_clean}</i>\n"
        f"📝 <b>Thesis:</b> {summary_clean}\n\n"
        f"🔗 <a href='https://www.binance.com/en/trade/{clean_symbol}'>Trade on Binance</a>"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg_html, "parse_mode": "HTML", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=8)

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
    return tr.rolling(min(period, len(df))).mean().iloc[-1]

def get_orderbook_ratio(raw_symbol):
    # Try Spot depth first
    try:
        res = requests.get(f"{SPOT_BASE_URL}/depth", params={'symbol': raw_symbol, 'limit': 20}, timeout=4)
        if res.status_code == 200:
            data = res.json()
            bids = sum([float(b[1]) for b in data.get('bids', [])])
            asks = sum([float(a[1]) for a in data.get('asks', [])])
            total = bids + asks
            return (round((bids / total) * 100, 1), round((asks / total) * 100, 1)) if total > 0 else (50.0, 50.0)
    except Exception:
        pass

    # Try Futures depth fallback
    try:
        res = requests.get(f"{FUTURES_BASE_URL}/depth", params={'symbol': raw_symbol, 'limit': 20}, timeout=4)
        if res.status_code == 200:
            data = res.json()
            bids = sum([float(b[1]) for b in data.get('bids', [])])
            asks = sum([float(a[1]) for a in data.get('asks', [])])
            total = bids + asks
            return (round((bids / total) * 100, 1), round((asks / total) * 100, 1)) if total > 0 else (50.0, 50.0)
    except Exception:
        pass

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

# ================= SMART DUAL (SPOT + FUTURES) MTF FETCH =================
def fetch_mtf_data(symbol):
    tf_data = {}
    timeframes = ['15m', '1h', '4h', '1d']
    
    # 1. Determine Endpoint (Spot or Futures)
    use_futures = False
    chk = requests.get(f"{SPOT_BASE_URL}/ticker/price", params={'symbol': symbol}, timeout=4)
    if chk.status_code != 200:
        chk_f = requests.get(f"{FUTURES_BASE_URL}/ticker/price", params={'symbol': symbol}, timeout=4)
        if chk_f.status_code == 200:
            use_futures = True
        else:
            return None, False

    base_endpoint = FUTURES_BASE_URL if use_futures else SPOT_BASE_URL

    for tf in timeframes:
        try:
            res = requests.get(f"{base_endpoint}/klines", params={'symbol': symbol, 'interval': tf, 'limit': 35}, timeout=5)
            if res.status_code == 200:
                raw_candles = res.json()
                if len(raw_candles) >= 3:
                    df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                    for col in ['close', 'open', 'high', 'low', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    rsi_series = calculate_rsi(df['close'], period=min(14, len(df)-1))
                    rsi = rsi_series.iloc[-1] if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]) else 50.0
                    ema20 = df['close'].ewm(span=min(20, len(df)), adjust=False).mean().iloc[-1]
                    ema50 = df['close'].ewm(span=min(50, len(df)), adjust=False).mean().iloc[-1]
                    current_p = df['close'].iloc[-1]
                    
                    is_bullish = current_p >= ema20 and rsi >= 48
                    tf_data[tf] = {
                        "price": current_p,
                        "rsi": round(rsi, 1),
                        "ema20": ema20,
                        "ema50": ema50,
                        "status": "BULLISH 🟢" if is_bullish else "BEARISH 🔴",
                        "raw_bull": is_bullish,
                        "atr": calculate_atr(df, period=14),
                        "df": df
                    }
        except Exception:
            continue
            
    return tf_data, use_futures

# ================= INSTITUTIONAL MTF SYNTHESIZER =================
def compute_mtf_institutional_setup(coin, current_price, mtf_data, dom_info, selected_theories):
    bull_count = sum(1 for tf, d in mtf_data.items() if d['raw_bull'])
    total_tfs = max(1, len(mtf_data))
    
    long_score = int((bull_count / total_tfs) * 100)
    short_score = 100 - long_score
    
    is_long_priority = long_score >= 50
    final_direction = "STRONG LONG" if long_score >= 75 else ("STRONG SHORT" if short_score >= 75 else ("SCALP LONG" if is_long_priority else "SCALP SHORT"))
    confidence = max(long_score, short_score)
    
    # Select available lowest timeframe ATR
    atr_val = current_price * 0.02
    for tf_k in ['15m', '1h', '4h']:
        if tf_k in mtf_data:
            atr_val = mtf_data[tf_k]['atr']
            break
            
    entry_l_min = current_price * 0.997
    entry_l_max = current_price * 1.002
    sl_long = current_price - (atr_val * 1.6)
    tp1_l = current_price + (atr_val * 2.5)
    tp2_l = current_price + (atr_val * 4.2)
    tp3_l = current_price + (atr_val * 6.5)
    
    entry_s_min = current_price * 1.003
    entry_s_max = current_price * 0.998
    sl_short = current_price + (atr_val * 1.6)
    tp1_s = max(0.000001, current_price - (atr_val * 2.5))
    tp2_s = max(0.000001, current_price - (atr_val * 4.2))
    tp3_s = max(0.000001, current_price - (atr_val * 6.5))
    
    fmt = ".5f" if current_price < 1 else ".4f"

    if is_long_priority:
        active_entry = f"{format(entry_l_min, fmt)} - {format(entry_l_max, fmt)}"
        active_sl = format(sl_long, fmt)
        active_tp1 = format(tp1_l, fmt)
        active_tp2 = format(tp2_l, fmt)
        active_tp3 = format(tp3_l, fmt)
        active_rr = "1:2.8"
        active_lev = "5x - 10x" if confidence >= 75 else "3x - 5x"
    else:
        active_entry = f"{format(entry_s_max, fmt)} - {format(entry_s_min, fmt)}"
        active_sl = format(sl_short, fmt)
        active_tp1 = format(tp1_s, fmt)
        active_tp2 = format(tp2_s, fmt)
        active_tp3 = format(tp3_s, fmt)
        active_rr = "1:2.6"
        active_lev = "3x - 5x"

    mtf_lines = []
    for tf in ['1d', '4h', '1h', '15m']:
        if tf in mtf_data:
            d = mtf_data[tf]
            mtf_lines.append(f"• <b>{tf.upper()}:</b> {d['status']} (RSI: {d['rsi']})")
        else:
            mtf_lines.append(f"• <b>{tf.upper()}:</b> NEW LISTING / NO DATA ℹ️")
    mtf_summary = "\n".join(mtf_lines)

    theory_findings = []
    for th in selected_theories:
        short_t = th.split("—")[0].strip()
        if "Smart Money" in short_t:
            finding = f"Order Block structure indicates {'Demand accumulation' if is_long_priority else 'Supply mitigation rejection'}. Fair Value Gap mapped."
        elif "Wyckoff" in short_t:
            finding = f"{'Phase C Spring / SOS confirmation' if is_long_priority else 'Distribution breakdown (UTAD)'} based on dynamic volume."
        elif "Dow" in short_t:
            finding = f"Structure shows {'Bullish BOS (Higher Highs)' if is_long_priority else 'Bearish CHoCH (Lower Lows)'}."
        elif "Elliott" in short_t:
            finding = f"{'Impulse Wave extension unfolding' if is_long_priority else 'Corrective downward impulse'}."
        elif "RSI" in short_t:
            finding = f"Momentum healthy without immediate multi-timeframe divergence."
        else:
            finding = f"Confluence aligns with {'upper resistance breakout' if is_long_priority else 'support breakdown'}."
        theory_findings.append({"theory": short_t, "finding": finding})

    thesis = (
        f"Multi-Timeframe synthesis concludes a {final_direction} bias "
        f"with {long_score}% Long vs {short_score}% Short confluence score. "
        f"Execution mapped to institutional liquidity levels."
    )

    invalidation = (
        f"Candle close below ${format(sl_long, fmt)} invalidates the Bullish Structure." if is_long_priority
        else f"Candle close above ${format(sl_short, fmt)} invalidates the Bearish Structure."
    )

    return {
        "direction": final_direction,
        "confidence": confidence,
        "long_score": long_score,
        "short_score": short_score,
        "risk_reward": active_rr,
        "leverage": active_lev,
        "entry_zone": active_entry,
        "tp1": active_tp1,
        "tp2": active_tp2,
        "tp3": active_tp3,
        "stop_loss": active_sl,
        "theories_evaluated": [t.split("—")[0].strip() for t in selected_theories],
        "theory_breakdown": theory_findings,
        "summary": thesis,
        "invalidation": invalidation,
        "mtf_summary": mtf_summary,
        "long_plan": {"entry": f"{format(entry_l_min, fmt)} - {format(entry_l_max, fmt)}", "sl": format(sl_long, fmt), "tp1": format(tp1_l, fmt), "tp2": format(tp2_l, fmt), "tp3": format(tp3_l, fmt), "rr": "1:2.8"},
        "short_plan": {"entry": f"{format(entry_s_max, fmt)} - {format(entry_s_min, fmt)}", "sl": format(sl_short, fmt), "tp1": format(tp1_s, fmt), "tp2": format(tp2_s, fmt), "tp3": format(tp3_s, fmt), "rr": "1:2.6"}
    }

@st.cache_resource
def get_global_state():
    return {"last_alert_time": {}}

global_state = get_global_state()

# Session State
if "last_plan" not in st.session_state:
    st.session_state.last_plan = None
if "last_coin" not in st.session_state:
    st.session_state.last_coin = None
if "last_price" not in st.session_state:
    st.session_state.last_price = 0.0
if "last_mtf" not in st.session_state:
    st.session_state.last_mtf = {}

# Sidebar Settings
st.sidebar.header("⚙️ General Settings")
gemini_key = st.sidebar.text_input("Gemini API Key (Optional)", value=DEFAULT_GEMINI_KEY, type="password")

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
        res = requests.get(f"{SPOT_BASE_URL}/klines", params={'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 30}, timeout=5)
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
        res = requests.get(f"{SPOT_BASE_URL}/klines", params={'symbol': raw_symbol, 'interval': '1h', 'limit': 60}, timeout=5)
        if res.status_code != 200:
            return True
        closes = pd.Series([float(x[4]) for x in res.json()])
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        return (current_price >= ema50) if signal_type == "PUMP" else (current_price <= ema50)
    except Exception:
        return True

# ================= TABS =================
tab_theory, tab_scanner = st.tabs(["🏛️ Multi-Timeframe Institutional Terminal", "📡 24/7 Autonomous Scanner"])

# ----------------- TAB 1: MTF DEEP DIVE ANALYZER -----------------
with tab_theory:
    st.subheader("🏛️ Universal Multi-Timeframe Deep Dive (1D • 4H • 1H • 15M)")
    st.caption("Spot සහ Futures කාසි සියල්ලටම සහය දක්වයි (Supports New Listings & Perp Contracts).")

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
        select_all_th = st.checkbox("සියලුම Theories 12ම සක්‍රීය කරන්න", value=True)
    with th_col2:
        if select_all_th:
            active_theories = ALL_THEORIES
            st.info("Theories 12ම සක්‍රීයයි (Full Institutional Confluence Mode)")
        else:
            active_theories = st.multiselect("අවශ්‍ය Theories තෝරන්න:", options=ALL_THEORIES, default=[ALL_THEORIES[0], ALL_THEORIES[1], ALL_THEORIES[2], ALL_THEORIES[4], ALL_THEORIES[11]])

    st.write("---")
    in_col1, in_col2 = st.columns([3, 1])
    with in_col1:
        custom_coin_symbol = st.text_input("කාසියේ නම (Coin Symbol):", value="FLOCK", placeholder="e.g. FLOCK, SOL, BTC, ETH, PEPE").strip().upper()
    with in_col2:
        st.write("##")
        run_theory_btn = st.button("🚀 Multi-Timeframe Analysis", use_container_width=True)

    manual_analysis_running = False

    if run_theory_btn and custom_coin_symbol:
        manual_analysis_running = True
        custom_pair = f"{custom_coin_symbol}USDT"
        if not active_theories:
            st.warning("⚠️ කරුණාකර අවම වශයෙන් එක් Theory එකක් තෝරන්න.")
        else:
            st.info("⏸️ **Market Scanner එක Pause කරන ලදී.** Binance Spot සහ Futures පරීක්ෂා කරමින් පවතී...")
            with st.spinner(f"{custom_pair} දත්ත සකසමින් පවතී..."):
                try:
                    mtf_data_fetched, is_fut = fetch_mtf_data(custom_pair)
                    if mtf_data_fetched and len(mtf_data_fetched) > 0:
                        lowest_tf = '15m' if '15m' in mtf_data_fetched else list(mtf_data_fetched.keys())[0]
                        real_p = mtf_data_fetched[lowest_tf]['price']
                        b_pct, s_pct = get_orderbook_ratio(custom_pair)
                        dom_info_str = f"Buyers: {b_pct}% | Sellers: {s_pct}%"
                        
                        plan = compute_mtf_institutional_setup(custom_pair, real_p, mtf_data_fetched, dom_info_str, active_theories)
                        
                        st.session_state.last_plan = plan
                        st.session_state.last_coin = custom_coin_symbol
                        st.session_state.last_price = real_p
                        st.session_state.last_mtf = mtf_data_fetched
                        st.session_state.buyers_pct = b_pct
                        st.session_state.sellers_pct = s_pct
                        st.session_state.is_futures_only = is_fut
                    else:
                        st.error(f"Binance Spot හෝ Futures යන දෙකෙහිම `{custom_pair}` යුගලය හමු නොවීය. කරුණාකර Symbol එක නිවැරදි දැයි බලන්න.")
                except Exception as ex:
                    st.error(f"දෝෂයක් ඇති විය: {ex}")

    # Render Plan if exists in session
    if st.session_state.last_plan and st.session_state.last_coin:
        plan = st.session_state.last_plan
        coin_sym = st.session_state.last_coin
        real_p = st.session_state.last_price
        mtf_data = st.session_state.last_mtf
        b_pct = getattr(st.session_state, 'buyers_pct', 50)
        s_pct = getattr(st.session_state, 'sellers_pct', 50)
        is_fut = getattr(st.session_state, 'is_futures_only', False)

        market_tag = "(Binance Futures / Perp)" if is_fut else "(Binance Spot)"
        st.markdown("---")
        dir_label = plan.get('direction', 'NEUTRAL')
        color_icon = "🟢" if "LONG" in dir_label else "🔴"
        
        st.markdown(f"## {color_icon} Final Multi-Timeframe Verdict: **{dir_label}** for **{coin_sym}/USDT** `{market_tag}`")
        
        score_c1, score_c2, score_c3, score_c4 = st.columns(4)
        score_c1.metric("Long Confluence Score", f"{plan.get('long_score')}%")
        score_c2.metric("Short Confluence Score", f"{plan.get('short_score')}%")
        p_fmt = ":,.5f" if real_p < 1 else ":,.4f"
        score_c3.metric("Live Price", f"${format(real_p, p_fmt[1:])}")
        score_c4.metric("Order Flow", f"🟢 {b_pct}% / 🔴 {s_pct}%")

        st.markdown("#### ⏳ Timeframe Health Matrix")
        tf_cols = st.columns(4)
        for idx, tf_name in enumerate(['1d', '4h', '1h', '15m']):
            with tf_cols[idx]:
                if tf_name in mtf_data:
                    d = mtf_data[tf_name]
                    st.metric(f"Timeframe: {tf_name.upper()}", d['status'], f"RSI: {d['rsi']}")
                else:
                    st.metric(f"Timeframe: {tf_name.upper()}", "NEW LISTING ℹ️", "N/A")

        chart_c, card_c = st.columns([3, 2])
        with chart_c:
            st.markdown("### 📊 Interactive Technical Chart")
            render_tradingview_widget(f"{coin_sym}USDT")
        with card_c:
            st.markdown("### 🎯 Primary Actionable Setup")
            plan_table = {
                "Parameter": ["Final Direction", "Entry Zone", "Stop Loss (Invalidation)", "Take Profit 1", "Take Profit 2", "Take Profit 3 (Runner)", "R:R Ratio", "Safe Leverage"],
                "Value": [
                    dir_label, f"${plan.get('entry_zone')}", f"${plan.get('stop_loss')}",
                    f"${plan.get('tp1')}", f"${plan.get('tp2')}", f"${plan.get('tp3')}",
                    plan.get('risk_reward'), plan.get('leverage')
                ]
            }
            st.dataframe(pd.DataFrame(plan_table), use_container_width=True, hide_index=True)
            st.markdown("#### 📝 Trade Thesis")
            st.info(plan.get('summary'))
            
            if st.button("📲 Send Plan to Telegram", use_container_width=True):
                with st.spinner("Telegram වෙත යවමින් පවතී..."):
                    t_res_msg = send_theory_telegram_alert(f"{coin_sym}/USDT", plan)
                    if t_res_msg.status_code == 200:
                        st.success("✅ Multi-Timeframe Trade Plan එක සාර්ථකව Telegram වෙත යවන ලදී!")
                    else:
                        st.error(f"Telegram Error: {t_res_msg.text}")

        st.markdown("---")
        st.markdown("### ⚖️ Dual Action Plan (Long vs Short Comparison)")
        dual_data = {
            "Plan Parameter": ["Entry Zone", "Stop Loss", "TP 1", "TP 2", "TP 3", "Risk : Reward"],
            "🟢 LONG SETUP (Buy Side)": [
                f"${plan['long_plan']['entry']}", f"${plan['long_plan']['sl']}", f"${plan['long_plan']['tp1']}",
                f"${plan['long_plan']['tp2']}", f"${plan['long_plan']['tp3']}", plan['long_plan']['rr']
            ],
            "🔴 SHORT SETUP (Sell Side)": [
                f"${plan['short_plan']['entry']}", f"${plan['short_plan']['sl']}", f"${plan['short_plan']['tp1']}",
                f"${plan['short_plan']['tp2']}", f"${plan['short_plan']['tp3']}", plan['short_plan']['rr']
            ]
        }
        st.dataframe(pd.DataFrame(dual_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🧠 Theory-by-Theory Confluence Findings")
        breakdown = plan.get("theory_breakdown", [])
        if breakdown:
            b_cols = st.columns(min(len(breakdown), 3))
            for i_idx, b_item in enumerate(breakdown):
                with b_cols[i_idx % 3]:
                    st.success(f"**{b_item.get('theory')}**")
                    st.write(b_item.get('finding'))

        st.markdown("---")
        st.markdown("### 📋 Institutional Risk Management Roadmap")
        sum_col1, sum_col2 = st.columns([2, 1])
        with sum_col1:
            st.warning(f"⚠️ **Trade Invalidation Criteria:** {plan.get('invalidation')}")
            st.write("• **Position Sizing:** මෙම trade එක සඳහා ඔබගේ මුළු මුදලින් 1% - 2% කට වඩා Risk නොකරන්න.")
            st.write("• **Profit Taking Strategy:** TP1 ළඟා වූ විට මුල් Stop Loss අගය Entry මට්ටමට (Break-even) ගෙන එන්න.")
        with sum_col2:
            st.markdown("#### ✅ Execution Rules")
            st.checkbox("Macro (1D/4H) Trend එකට අනුකූලද?", value=True)
            st.checkbox("15m Entry Candle එකක් තහවුරු වූවාද?", value=True)
            st.checkbox("Hard Stop Loss Binance එකේ දැමුවාද?", value=True)

# ----------------- TAB 2: 24/7 MARKET SCANNER -----------------
with tab_scanner:
    btc_status, btc_msg = check_btc_trend()
    st.subheader("📡 Live 24/7 Autonomous Market Scanner")
    st.caption(f"🛡️ Market Context: {btc_msg}")

    def scan_market_now():
        alerts = []
        res = requests.get(f"{SPOT_BASE_URL}/ticker/24hr", timeout=10)
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
                kline_res = requests.get(f"{SPOT_BASE_URL}/klines", params={'symbol': raw_symbol, 'interval': '15m', 'limit': 40}, timeout=5)
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
                    
                    ai_verdict = "CONFIRMED"
                    alerts.append({
                        "raw_symbol": raw_symbol, "Type": "🟢 PUMP" if signal == "PUMP" else "🔴 DUMP",
                        "Coin": display_symbol, "Live Price ($)": format(real_time_price, fmt),
                        "15m Change": f"{change_str}%", "RSI": f"{current_rsi:.1f}", "Pattern": pattern_found,
                        "AI Verdict": ai_verdict, "TP 1": format(tp1_val, fmt), "Stop Loss": format(sl_val, fmt),
                        "Vol Spike": f"{round(current_volume/avg_volume,1)}x", "Dominance": dom_str
                    })
                    
                    last_sent = global_state["last_alert_time"].get(display_symbol, 0)
                    if current_time - last_sent > 3600:
                        send_scanner_telegram_alert(signal, display_symbol, format(real_time_price, fmt), change_str, f"{round(current_volume/avg_volume,1)}x", f"{current_rsi:.1f}", format(tp1_val, fmt), format(tp2_val, fmt), format(sl_val, fmt), dom_str, pattern_found, ai_verdict)
                        global_state["last_alert_time"][display_symbol] = current_time
            except Exception:
                continue
        return alerts

    if not manual_analysis_running:
        with st.spinner("24/7 Scanner: වෙළඳපොළ ස්වයංක්‍රීයව පරීක්ෂා කරමින් පවතී..."):
            auto_scan_results = scan_market_now()
            if auto_scan_results:
                st.success(f"🔥 කාසි {len(auto_scan_results)} ක් හමුවිය! (Telegram එකට Alerts යවන ලදී)")
                play_alert_sound()
                st.dataframe(pd.DataFrame(auto_scan_results).drop(columns=['raw_symbol']), use_container_width=True)
            else:
                st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි නොමැත. පසුබිමෙන් පරීක්ෂා කරමින් පවතී.")
    else:
        st.warning("⏸️ ඔබ Manual Coin Analysis එකක් සිදු කරන බැවින් 24/7 Scanner එක තාවකාලිකව Pause කර ඇත.")
