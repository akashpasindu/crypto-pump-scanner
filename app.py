import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import html
import time

st.set_page_config(page_title="Universal Binance AI Terminal", layout="wide")

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
    reasons_text = ""
    for idx, b_item in enumerate(plan.get("theory_breakdown", [])[:4]):
        th_name = html.escape(b_item.get('theory', 'Concept'))
        th_reason = html.escape(b_item.get('why_reason', 'Aligned'))
        reasons_text += f"\n• <b>{th_name}:</b> {th_reason}"

    msg_html = (
        f"🏛️ <b>Institutional Multi-Theory Setup</b>\n\n"
        f"🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"🎯 <b>Final Verdict:</b> {icon} <b>{direction_val}</b> | <b>Score:</b> <code>{plan.get('confidence', 80)}%</code>\n"
        f"⚙️ <b>Leverage:</b> <code>{plan.get('leverage', '3x - 5x')}</code> | <b>R:R:</b> <code>{plan.get('risk_reward', '1:3')}</code>\n\n"
        f"📥 <b>Entry Zone:</b> <code>${plan.get('entry_zone', 'Market')}</code>\n"
        f"🛑 <b>Stop Loss:</b> <code>${plan.get('stop_loss', 'N/A')}</code>\n\n"
        f"🎯 <b>Targets:</b>\n"
        f"  ├ TP 1: <code>${plan.get('tp1', 'N/A')}</code>\n"
        f"  ├ TP 2: <code>${plan.get('tp2', 'N/A')}</code>\n"
        f"  └ TP 3: <code>${plan.get('tp3', 'N/A')}</code>\n\n"
        f"🧠 <b>Key Concept Reasons (හේතු සාරාංශය):</b>{reasons_text}\n\n"
        f"📝 <b>Thesis:</b> {summary_clean}\n\n"
        f"🔗 <a href='https://www.binance.com/en/trade/{clean_symbol}'>Trade on Binance</a>"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg_html, "parse_mode": "HTML", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=8)

def play_alert_sound():
    sound_code = """<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>"""
    components.html(sound_code, height=0, width=0)

def render_tradingview_widget(symbol_raw, is_futures=False):
    chart_symbol = f"BINANCE:{symbol_raw}.P" if is_futures else f"BINANCE:{symbol_raw}"
    widget_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol_raw}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%", "height": 450, "symbol": "{chart_symbol}",
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
    return tr.rolling(min(period, max(1, len(df)))).mean().iloc[-1]

def get_orderbook_ratio(raw_symbol):
    for base_ep in [SPOT_BASE_URL, FUTURES_BASE_URL]:
        try:
            res = requests.get(f"{base_ep}/depth", params={'symbol': raw_symbol, 'limit': 20}, timeout=3)
            if res.status_code == 200:
                data = res.json()
                bids = sum([float(b[1]) for b in data.get('bids', [])])
                asks = sum([float(a[1]) for a in data.get('asks', [])])
                total = bids + asks
                if total > 0:
                    return round((bids / total) * 100, 1), round((asks / total) * 100, 1)
        except Exception:
            continue
    return 50.0, 50.0

def detect_candlestick_pattern(df):
    if len(df) < 3:
        return "New Listing Launch 🚀"
    c1, o1, h1, l1 = df['close'].iloc[-1], df['open'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
    c2, o2 = df['close'].iloc[-2], df['open'].iloc[-2]
    body1 = abs(c1 - o1)
    lower_wick1 = min(c1, o1) - l1
    upper_wick1 = h1 - max(c1, o1)
    
    if (c2 < o2) and (c1 > o1) and (c1 >= o2):
        return "Bullish Engulfing 🟢"
    if (lower_wick1 >= 1.5 * body1) and (c1 >= o1):
        return "Bullish Hammer 🔨"
    if (c2 > o2) and (c1 < o1) and (c1 <= o2):
        return "Bearish Engulfing 🔴"
    if (upper_wick1 >= 1.5 * body1) and (c1 <= o1):
        return "Shooting Star 🌠"
    return "Momentum Continuation ⚡"

# ================= UNIVERSAL BINANCE SMART COIN DISCOVERY =================
def resolve_any_binance_coin(user_input):
    clean = user_input.strip().upper()
    for quote in ['USDT', 'USDC', 'BUSD', 'FDUSD']:
        clean = clean.replace(quote, "")
    clean = clean.replace('/', '').replace('_', '').replace('-', '')

    potential_symbols = [
        f"{clean}USDT",
        f"1000{clean}USDT",
        f"10000{clean}USDT",
        f"1000000{clean}USDT",
        f"{clean}USDC",
        f"1000{clean}USDC",
        f"{clean}FDUSD"
    ]

    for sym in potential_symbols:
        try:
            sp_res = requests.get(f"{SPOT_BASE_URL}/ticker/price", params={'symbol': sym}, timeout=2)
            if sp_res.status_code == 200:
                return sym, False, "Spot Market"
        except Exception:
            pass

        try:
            fu_res = requests.get(f"{FUTURES_BASE_URL}/ticker/price", params={'symbol': sym}, timeout=2)
            if fu_res.status_code == 200:
                return sym, True, "Futures / Perpetual"
        except Exception:
            pass

    return None, False, None

# ================= MULTI-TIMEFRAME / NEW LISTING ADAPTIVE FETCH =================
def fetch_universal_adaptive_data(resolved_symbol, is_futures):
    endpoint = FUTURES_BASE_URL if is_futures else SPOT_BASE_URL
    tf_data = {}
    
    # Priority timeframes (Macro down to Micro)
    standard_tfs = ['1d', '4h', '1h', '15m']
    new_listing_fallback_tfs = ['15m', '5m', '3m', '1m']

    # Check available history length
    chk = requests.get(f"{endpoint}/klines", params={'symbol': resolved_symbol, 'interval': '1h', 'limit': 15}, timeout=4)
    is_brand_new = False
    if chk.status_code == 200:
        candles = chk.json()
        if len(candles) < 12:  # Listed less than 12 hours ago!
            is_brand_new = True

    active_query_tfs = new_listing_fallback_tfs if is_brand_new else standard_tfs

    for tf in active_query_tfs:
        try:
            res = requests.get(f"{endpoint}/klines", params={'symbol': resolved_symbol, 'interval': tf, 'limit': 35}, timeout=4)
            if res.status_code == 200:
                raw_candles = res.json()
                if len(raw_candles) >= 1:
                    df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                    for col in ['close', 'open', 'high', 'low', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    c_len = len(df)
                    rsi_period = min(14, max(2, c_len - 1))
                    rsi_series = calculate_rsi(df['close'], period=rsi_period)
                    rsi = rsi_series.iloc[-1] if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]) else 50.0
                    
                    ema_span = min(20, c_len)
                    ema20 = df['close'].ewm(span=ema_span, adjust=False).mean().iloc[-1]
                    current_p = df['close'].iloc[-1]
                    
                    is_bullish = current_p >= ema20 and rsi >= 48
                    tf_data[tf] = {
                        "price": current_p,
                        "rsi": round(rsi, 1),
                        "ema20": ema20,
                        "status": "BULLISH 🟢" if is_bullish else "BEARISH 🔴",
                        "raw_bull": is_bullish,
                        "atr": calculate_atr(df, period=min(14, c_len)),
                        "df": df
                    }
        except Exception:
            continue
            
    return tf_data, is_brand_new

# ================= INSTITUTIONAL MTF & CONCEPT REASONING SYNTHESIZER =================
def compute_institutional_trade_setup(symbol_resolved, current_price, mtf_data, dom_info, selected_theories, is_brand_new):
    bull_count = sum(1 for tf, d in mtf_data.items() if d['raw_bull'])
    total_tfs = max(1, len(mtf_data))
    
    long_score = int((bull_count / total_tfs) * 100)
    short_score = 100 - long_score
    is_long_priority = long_score >= 50
    
    prefix_mode = "NEW LISTING " if is_brand_new else ""
    final_direction = f"{prefix_mode}STRONG LONG" if long_score >= 75 else (f"{prefix_mode}STRONG SHORT" if short_score >= 75 else (f"{prefix_mode}SCALP LONG" if is_long_priority else f"{prefix_mode}SCALP SHORT"))
    confidence = max(long_score, short_score)
    
    # Lowest timeframe ATR
    atr_val = current_price * 0.02
    for tf_k in ['1m', '3m', '5m', '15m', '1h']:
        if tf_k in mtf_data:
            atr_val = mtf_data[tf_k]['atr']
            break
            
    # Buffer Multipliers
    atr_multiplier = 1.8 if is_brand_new else 1.5
    sl_long = max(0.00000001, current_price - (atr_val * atr_multiplier))
    tp1_l = current_price + (atr_val * 2.2)
    tp2_l = current_price + (atr_val * 3.8)
    tp3_l = current_price + (atr_val * 5.5)
    
    sl_short = current_price + (atr_val * atr_multiplier)
    tp1_s = max(0.00000001, current_price - (atr_val * 2.2))
    tp2_s = max(0.00000001, current_price - (atr_val * 3.8))
    tp3_s = max(0.00000001, current_price - (atr_val * 5.5))
    
    fmt = ".6f" if current_price < 0.01 else (".4f" if current_price < 10 else ".2f")

    if is_long_priority:
        active_entry = f"{format(current_price * 0.996, fmt)} - {format(current_price * 1.003, fmt)}"
        active_sl = format(sl_long, fmt)
        active_tp1 = format(tp1_l, fmt)
        active_tp2 = format(tp2_l, fmt)
        active_tp3 = format(tp3_l, fmt)
        active_rr = "1:2.5" if is_brand_new else "1:2.8"
        active_lev = "2x - 3x (High Volatility)" if is_brand_new else ("5x - 10x" if confidence >= 75 else "3x - 5x")
    else:
        active_entry = f"{format(current_price * 1.004, fmt)} - {format(current_price * 0.997, fmt)}"
        active_sl = format(sl_short, fmt)
        active_tp1 = format(tp1_s, fmt)
        active_tp2 = format(tp2_s, fmt)
        active_tp3 = format(tp3_s, fmt)
        active_rr = "1:2.2" if is_brand_new else "1:2.6"
        active_lev = "2x - 3x (High Volatility)" if is_brand_new else "3x - 5x"

    # Timeframe Summary String
    mtf_lines = []
    for tf_key, d in mtf_data.items():
        mtf_lines.append(f"• <b>{tf_key.upper()}:</b> {d['status']} (RSI: {d['rsi']})")
    mtf_summary = "\n".join(mtf_lines)

    # Concept Reasoning Breakdown
    theory_findings = []
    for th in selected_theories:
        short_t = th.split("—")[0].strip()
        if "Smart Money" in short_t:
            reason = (
                f"මිල අවසන් Swing Liquidity එක sweep කර {'Demand Order Block එකක retest එකක්' if is_long_priority else 'Supply zone rejection එකක්'} සනාථ කර ඇත. ඉහළ Fair Value Gap (FVG) එක තවමත් mitigate වී නැති නිසා මිල ඉහළට ඇදී යාමේ සම්භාවිතාව වැඩිය."
                if is_long_priority else
                f"ඉහළ Buy-side liquidity grab එකකින් පසු Lower-timeframe Change of Character (CHoCH) එකක් පෙන්වමින් Bearish Order Block එකක් සාදා ඇති බැවින් Downside imbalance එක පිරවීමට පහත බසිනු ඇත."
            )
        elif "Wyckoff" in short_t:
            reason = (
                f"මෑත ඉටිපන්දම් වල Volume Absorption පෙනෙන්නට තිබේ. {'Phase C Spring (False breakdown) අවසන් වී Sign of Strength (SOS) සමඟ Smart Money එකතු වීමක්' if is_long_priority else 'Upthrust After Distribution (UTAD) මඟින් Smart Money විසින් Retailers ලාට විකිණීමක්'} සිදුවන බව පෙනේ."
            )
        elif "Dow" in short_t:
            reason = (
                f"Dow Theory ට අනුව මිල {'Higher Highs සහ Higher Lows (Bullish Break of Structure - BOS)' if is_long_priority else 'Lower Highs සහ Lower Lows (Bearish Market Structure Shift)'} සාදන බැවින් Trend Continuation එක තහවුරුයි."
            )
        elif "Elliott" in short_t:
            reason = (
                f"තරංග චලනය (Wave Structure) පරීක්ෂා කළ විට මෙය {'Impulse Wave 3 (උපරිම වේගවත් expansion එකක්)' if is_long_priority else 'Corrective C-wave impulse එකක්'} ලෙස හඳුනාගත හැක."
            )
        elif "Supply" in short_t:
            reason = (
                f"{'නැවුම් (Fresh) Demand Zone එකකින් ඉහළට මිල ප්‍රතික්ෂේප වී (Rejection wick) ඇත' if is_long_priority else 'ප්‍රබල Supply Zone එකක විකුණුම්කරුවන් මිල පාලනය ගෙන ඇත'}."
            )
        elif "RSI" in short_t:
            rsi_val = list(mtf_data.values())[0]['rsi']
            reason = (
                f"RSI අගය ({rsi_val}) මඟින් {'Healthy Momentum එකක් පෙන්වන අතර Hidden Bullish Divergence තත්ත්වයක්' if is_long_priority else 'Overbought වීමෙන් පසු Bearish Divergence සමඟ පහත වැටීමක්'} පෙන්වයි."
            )
        else:
            reason = f"Moving Averages සහ Candlestick රටා මඟින් {'මිල ඉහළ යාම සඳහා Volume Breakout එකක්' if is_long_priority else 'Support බිඳවැටීමක්'} තහවුරු කරයි."
            
        theory_findings.append({
            "theory": short_t,
            "why_reason": reason
        })

    market_condition_text = "අලුතින්ම List වූ අධික Volatility සහිත කාසියකි (Micro-Timeframe Scalp Mode)" if is_brand_new else "Multi-Timeframe Confluence Mode"
    thesis = (
        f"{symbol_resolved} සඳහා කාල පරාස {len(mtf_data)} ක් හරහා සිදු කළ පරීක්ෂාවේදී {final_direction} දිශාව "
        f"{long_score}% Long එදිරිව {short_score}% Short එකඟතාවයකින් තහවුරු විය. ({market_condition_text})"
    )

    invalidation = (
        f"මිල ${format(sl_long, fmt)} ට වඩා පහළින් Candle Close එකක් තැබුවහොත් මෙම Long Setup එක සම්පූර්ණයෙන්ම අවලංගු (Invalid) වේ." if is_long_priority
        else f"මිල ${format(sl_short, fmt)} ට වඩා ඉහළින් Candle Close එකක් තැබුවහොත් මෙම Short Setup එක අවලංගු (Invalid) වේ."
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
        "is_brand_new": is_brand_new,
        "long_plan": {"entry": f"{format(current_price * 0.996, fmt)} - {format(current_price * 1.003, fmt)}", "sl": format(sl_long, fmt), "tp1": format(tp1_l, fmt), "tp2": format(tp2_l, fmt), "tp3": format(tp3_l, fmt), "rr": "1:2.8"},
        "short_plan": {"entry": f"{format(current_price * 1.004, fmt)} - {format(current_price * 0.997, fmt)}", "sl": format(sl_short, fmt), "tp1": format(tp1_s, fmt), "tp2": format(tp2_s, fmt), "tp3": format(tp3_s, fmt), "rr": "1:2.6"}
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

st.sidebar.header("📡 24/7 Scanner Scope")
market_scope = st.sidebar.selectbox("ස්කෑන් කළ යුතු වෙළඳපොළ පරාසය:", [
    "🔥 High Volume Liquid Market (Top 50 Pairs)",
    "⚡ Mid & Large Cap Momentum (Top 100 Pairs)",
    "🌐 Entire Binance Market (All 400+ Coins - Full Scan)"
], index=1)

scan_mode = st.sidebar.radio("Scanner Direction", ["Both (Pump & Dump)", "Pump Only (Long)", "Dump Only (Short)"])
volume_threshold = st.sidebar.slider("Volume Spike Multiplier", 1.2, 5.0, 1.5, step=0.1)
price_threshold = st.sidebar.slider("අවම මිල වෙනස (%)", 0.5, 5.0, 1.2, step=0.1)
pump_rsi_min = st.sidebar.slider("Pump: Min RSI", 30, 60, 45)
pump_rsi_max = st.sidebar.slider("Pump: Max RSI", 60, 85, 75)
dump_rsi_min = st.sidebar.slider("Dump: Min RSI", 15, 40, 25)
dump_rsi_max = st.sidebar.slider("Dump: Max RSI", 40, 60, 55)

def check_btc_trend():
    try:
        res = requests.get(f"{SPOT_BASE_URL}/klines", params={'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 30}, timeout=4)
        if res.status_code != 200:
            return "NEUTRAL", "BTC Data Error"
        ohlcv = res.json()
        closes = pd.Series([float(x[4]) for x in ohlcv])
        ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
        is_bullish = closes.iloc[-1] >= ema20
        return ("BULLISH" if is_bullish else "BEARISH"), f"BTC: ${closes.iloc[-1]:,.1f} {'🟢 (Above 20 EMA)' if is_bullish else '🔴 (Below 20 EMA)'}"
    except Exception:
        return "NEUTRAL", "BTC Check Bypassed"

def check_1h_trend(raw_symbol, current_price, signal_type, is_futures=False):
    endpoint = FUTURES_BASE_URL if is_futures else SPOT_BASE_URL
    try:
        res = requests.get(f"{endpoint}/klines", params={'symbol': raw_symbol, 'interval': '1h', 'limit': 60}, timeout=4)
        if res.status_code != 200:
            return True
        closes = pd.Series([float(x[4]) for x in res.json()])
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        return (current_price >= ema50) if signal_type == "PUMP" else (current_price <= ema50)
    except Exception:
        return True

# ================= TABS =================
tab_theory, tab_scanner = st.tabs(["🏛️ Universal Coin & New Listing Terminal", "📡 24/7 Autonomous Scanner"])

# ----------------- TAB 1: UNIVERSAL COIN DEEP DIVE -----------------
with tab_theory:
    st.subheader("🏛️ Universal Binance Coin Analyzer (Brand New Listings & All Pairs)")
    st.caption("දැන් List වූ කාසියක් වුවද (1m, 3m, 5m Scalp Data හරහා) සහ පවතින සියලුම Spot/Futures කාසි සඳහා පරිපූර්ණ හේතු සාරාංශයක් ලබාදේ.")

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
            st.info("Theories 12ම සක්‍රීයයි (Full Multi-Confluence Engine)")
        else:
            active_theories = st.multiselect("අවශ්‍ය Theories තෝරන්න:", options=ALL_THEORIES, default=[ALL_THEORIES[0], ALL_THEORIES[1], ALL_THEORIES[2], ALL_THEORIES[4], ALL_THEORIES[11]])

    st.write("---")
    in_col1, in_col2 = st.columns([3, 1])
    with in_col1:
        custom_coin_symbol = st.text_input("Coin නම (උදා: FLOCK, SOL, BTC, PEPE, DOGE, 1000SATS):", value="FLOCK").strip().upper()
    with in_col2:
        st.write("##")
        run_theory_btn = st.button("🚀 Deep Theory Analysis", use_container_width=True)

    manual_analysis_running = False

    if run_theory_btn and custom_coin_symbol:
        manual_analysis_running = True
        if not active_theories:
            st.warning("⚠️ කරුණාකර අවම වශයෙන් එක් Theory එකක් තෝරන්න.")
        else:
            st.info("⏸️ **Market Scanner එක Pause කරන ලදී.** Binance Spot සහ Futures පරීක්ෂා කරමින් පවතී...")
            with st.spinner(f"Binance හි `{custom_coin_symbol}` සොයා දත්ත සකසමින් පවතී..."):
                try:
                    resolved_symbol, is_fut, market_type = resolve_any_binance_coin(custom_coin_symbol)
                    
                    if resolved_symbol:
                        mtf_data_fetched, is_brand_new = fetch_universal_adaptive_data(resolved_symbol, is_fut)
                        
                        if mtf_data_fetched and len(mtf_data_fetched) > 0:
                            lowest_tf = list(mtf_data_fetched.keys())[0]
                            real_p = mtf_data_fetched[lowest_tf]['price']
                            b_pct, s_pct = get_orderbook_ratio(resolved_symbol)
                            dom_info_str = f"Buyers: {b_pct}% | Sellers: {s_pct}%"
                            
                            plan = compute_institutional_trade_setup(resolved_symbol, real_p, mtf_data_fetched, dom_info_str, active_theories, is_brand_new)
                            
                            st.session_state.last_plan = plan
                            st.session_state.last_coin = custom_coin_symbol
                            st.session_state.resolved_sym = resolved_symbol
                            st.session_state.last_price = real_p
                            st.session_state.last_mtf = mtf_data_fetched
                            st.session_state.buyers_pct = b_pct
                            st.session_state.sellers_pct = s_pct
                            st.session_state.market_type = market_type
                            st.session_state.is_futures = is_fut
                            st.session_state.is_brand_new = is_brand_new
                        else:
                            st.error(f"Binance වෙතින් `{resolved_symbol}` සඳහා candlestick දත්ත ලබාගැනීමට නොහැකි විය.")
                    else:
                        st.error(f"Binance හි `{custom_coin_symbol}` නමින් Spot හෝ Futures යුගලයක් හමු නොවීය. නම නිවැරදිදැයි බලන්න.")
                except Exception as ex:
                    st.error(f"දෝෂයක් ඇති විය: {ex}")

    # Render Plan if exists in session
    if st.session_state.last_plan and st.session_state.last_coin:
        plan = st.session_state.last_plan
        coin_sym = st.session_state.last_coin
        resolved_sym = getattr(st.session_state, 'resolved_sym', f"{coin_sym}USDT")
        real_p = st.session_state.last_price
        mtf_data = st.session_state.last_mtf
        b_pct = getattr(st.session_state, 'buyers_pct', 50)
        s_pct = getattr(st.session_state, 'sellers_pct', 50)
        market_type = getattr(st.session_state, 'market_type', 'Spot')
        is_fut = getattr(st.session_state, 'is_futures', False)
        is_brand_new = getattr(st.session_state, 'is_brand_new', False)

        tag_new = " [NEW LISTING ADAPTIVE]" if is_brand_new else ""
        st.markdown("---")
        dir_label = plan.get('direction', 'NEUTRAL')
        color_icon = "🟢" if "LONG" in dir_label else "🔴"
        
        st.markdown(f"## {color_icon} Final Verdict: **{dir_label}** for **{resolved_sym}** `({market_type}){tag_new}`")
        
        score_c1, score_c2, score_c3, score_c4 = st.columns(4)
        score_c1.metric("Long Confluence Score", f"{plan.get('long_score')}%")
        score_c2.metric("Short Confluence Score", f"{plan.get('short_score')}%")
        p_fmt = ":,.6f" if real_p < 0.01 else (":,.4f" if real_p < 10 else ":,.2f")
        score_c3.metric("Live Price", f"${format(real_p, p_fmt[1:])}")
        score_c4.metric("Order Flow", f"🟢 {b_pct}% / 🔴 {s_pct}%")

        st.markdown("#### ⏳ Active Timeframe Health Matrix")
        tf_cols = st.columns(min(4, len(mtf_data)))
        for idx, (tf_name, d) in enumerate(list(mtf_data.items())[:4]):
            with tf_cols[idx]:
                st.metric(f"Timeframe: {tf_name.upper()}", d['status'], f"RSI: {d['rsi']}")

        chart_c, card_c = st.columns([3, 2])
        with chart_c:
            st.markdown("### 📊 Interactive Technical Chart")
            render_tradingview_widget(resolved_sym, is_futures=is_fut)
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
                    t_res_msg = send_theory_telegram_alert(resolved_sym, plan)
                    if t_res_msg.status_code == 200:
                        st.success("✅ Multi-Theory Trade Plan එක සාර්ථකව Telegram වෙත යවන ලදී!")
                    else:
                        st.error(f"Telegram Error: {t_res_msg.text}")

        # ================= NEW: DETAILED CONCEPT REASONING BREAKDOWN =================
        st.markdown("---")
        st.markdown("### 🧠 භාවිතා කළ Concepts වල හේතු සාරාංශය (Why this Trade?)")
        st.caption("තෝරාගත් Trading Concepts මඟින් මෙම Signal එක තහවුරු කිරීමට බලපෑ නිශ්චිත තාක්ෂණික හේතු:")

        breakdown = plan.get("theory_breakdown", [])
        if breakdown:
            for b_item in breakdown:
                with st.expander(f"📌 {b_item.get('theory')} — පදනම් වූ හේතුව", expanded=True):
                    st.write(b_item.get('why_reason'))

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
        st.markdown("### 📋 Institutional Risk Management Roadmap")
        sum_col1, sum_col2 = st.columns([2, 1])
        with sum_col1:
            st.warning(f"⚠️ **Trade Invalidation Criteria:** {plan.get('invalidation')}")
            st.write("• **Position Sizing:** මෙම trade එක සඳහා ඔබගේ මුළු මුදලින් 1% - 2% කට වඩා Risk නොකරන්න.")
            st.write("• **Profit Taking Strategy:** TP1 ළඟා වූ විට මුල් Stop Loss අගය Entry මට්ටමට (Break-even) ගෙන එන්න.")
        with sum_col2:
            st.markdown("#### ✅ Execution Rules")
            st.checkbox("Macro Trend / Volume Momentum එකට අනුකූලද?", value=True)
            st.checkbox("Entry Zone එකේදී Rejection Candle එකක් ලැබුණාද?", value=True)
            st.checkbox("Hard Stop Loss Binance එකේ දැමුවාද?", value=True)

# ----------------- TAB 2: 24/7 ENTIRE BINANCE MARKET SCANNER -----------------
with tab_scanner:
    btc_status, btc_msg = check_btc_trend()
    st.subheader("📡 Live 24/7 Autonomous Market Scanner")
    st.caption(f"🛡️ Market Context: {btc_msg} | Scope: `{market_scope}`")

    def scan_entire_binance():
        alerts = []
        raw_candidates = {}

        try:
            res_spot = requests.get(f"{SPOT_BASE_URL}/ticker/24hr", timeout=8)
            if res_spot.status_code == 200:
                for t in res_spot.json():
                    sym = t.get('symbol', '')
                    if sym.endswith('USDT') and not sym.endswith(('UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT')):
                        raw_candidates[sym] = {
                            'symbol': sym,
                            'quoteVolume': float(t.get('quoteVolume', 0)),
                            'last': float(t.get('lastPrice', 0)),
                            'is_futures': False
                        }
        except Exception:
            pass

        try:
            res_fut = requests.get(f"{FUTURES_BASE_URL}/ticker/24hr", timeout=8)
            if res_fut.status_code == 200:
                for t in res_fut.json():
                    sym = t.get('symbol', '')
                    if sym.endswith('USDT'):
                        if sym not in raw_candidates or float(t.get('quoteVolume', 0)) > raw_candidates[sym]['quoteVolume']:
                            raw_candidates[sym] = {
                                'symbol': sym,
                                'quoteVolume': float(t.get('quoteVolume', 0)),
                                'last': float(t.get('lastPrice', 0)),
                                'is_futures': True
                            }
        except Exception:
            pass

        all_coins = list(raw_candidates.values())
        if not all_coins:
            return alerts

        if "Top 50" in market_scope:
            target_list = sorted(all_coins, key=lambda x: x['quoteVolume'], reverse=True)[:50]
        elif "Top 100" in market_scope:
            target_list = sorted(all_coins, key=lambda x: x['quoteVolume'], reverse=True)[:100]
        else:
            target_list = sorted(all_coins, key=lambda x: x['quoteVolume'], reverse=True)

        current_time = time.time()

        for item in target_list:
            raw_symbol = item['symbol']
            is_fut = item['is_futures']
            endpoint = FUTURES_BASE_URL if is_fut else SPOT_BASE_URL
            display_symbol = f"{raw_symbol[:-4]}/USDT" if not raw_symbol.startswith("1000") else f"{raw_symbol}/USDT"
            real_time_price = item['last']

            if not real_time_price or raw_symbol in ['BTCUSDT', 'USDCUSDT', 'FDUSDUSDT']:
                continue

            try:
                kline_res = requests.get(f"{endpoint}/klines", params={'symbol': raw_symbol, 'interval': '15m', 'limit': 35}, timeout=4)
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
                        if not (btc_status == "BEARISH") and check_1h_trend(raw_symbol, real_time_price, "PUMP", is_fut) and buyer_ratio >= 52.0:
                            signal = "PUMP"
                if not signal and scan_mode in ["Both (Pump & Dump)", "Dump Only (Short)"]:
                    if is_vol_spike and live_price_change <= -price_threshold and (dump_rsi_min <= current_rsi <= dump_rsi_max) and real_time_price < current_ema:
                        if not (btc_status == "BULLISH") and check_1h_trend(raw_symbol, real_time_price, "DUMP", is_fut) and seller_ratio >= 52.0:
                            signal = "DUMP"
                
                if signal:
                    sl_val = max(0.000001, real_time_price - (atr_val * 1.5)) if signal == "PUMP" else (real_time_price + (atr_val * 1.5))
                    tp1_val = (real_time_price + (atr_val * 2.5)) if signal == "PUMP" else max(0.000001, real_time_price - (atr_val * 2.5))
                    tp2_val = (real_time_price + (atr_val * 4.0)) if signal == "PUMP" else max(0.000001, real_time_price - (atr_val * 4.0))
                    dom_str = f"Buyers {buyer_ratio}%" if signal == "PUMP" else f"Sellers {seller_ratio}%"
                    change_str = f"{live_price_change:+.2f}"
                    fmt = ".5f" if real_time_price < 1 else ".4f"
                    
                    ai_verdict = "CONFIRMED"
                    market_kind = "Futures" if is_fut else "Spot"
                    alerts.append({
                        "raw_symbol": raw_symbol, "Market": market_kind, "Type": "🟢 PUMP" if signal == "PUMP" else "🔴 DUMP",
                        "Coin": display_symbol, "Live Price ($)": format(real_time_price, fmt),
                        "15m Change": f"{change_str}%", "RSI": f"{current_rsi:.1f}", "Pattern": pattern_found,
                        "AI Verdict": ai_verdict, "TP 1": format(tp1_val, fmt), "Stop Loss": format(sl_val, fmt),
                        "Vol Spike": f"{round(current_volume/avg_volume,1)}x", "Dominance": dom_str
                    })
                    
                    last_sent = global_state["last_alert_time"].get(display_symbol, 0)
                    if current_time - last_sent > 3600:
                        send_scanner_telegram_alert(signal, f"{display_symbol} ({market_kind})", format(real_time_price, fmt), change_str, f"{round(current_volume/avg_volume,1)}x", f"{current_rsi:.1f}", format(tp1_val, fmt), format(tp2_val, fmt), format(sl_val, fmt), dom_str, pattern_found, ai_verdict)
                        global_state["last_alert_time"][display_symbol] = current_time
            except Exception:
                continue
        return alerts

    if not manual_analysis_running:
        with st.spinner(f"24/7 Scanner: වෙළඳපොළ පරීක්ෂා කරමින් පවතී ({market_scope})..."):
            auto_scan_results = scan_entire_binance()
            if auto_scan_results:
                st.success(f"🔥 කාසි {len(auto_scan_results)} ක් හමුවිය! (Telegram එකට Alerts යවන ලදී)")
                play_alert_sound()
                st.dataframe(pd.DataFrame(auto_scan_results).drop(columns=['raw_symbol']), use_container_width=True)
            else:
                st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි නොමැත. පසුබිමෙන් පරීක්ෂා කරමින් පවතී.")
    else:
        st.warning("⏸️ ඔබ Manual Coin Analysis එකක් සිදු කරන බැවින් 24/7 Scanner එක තාවකාලිකව Pause කර ඇත.")
