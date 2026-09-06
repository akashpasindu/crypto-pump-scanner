import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import time

st.set_page_config(page_title="Universal Multi-Theory Crypto AI Terminal", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = "AQ.Ab8RN6Kov34e2FAiapWmBpeAtkyAint2-EaxdTwngH8RxeagKQ"
BASE_URL = "https://data-api.binance.vision/api/v3"

def send_telegram_alert(coin, plan):
    clean_symbol = coin.replace('/', '_')
    direction_icon = "🟢 LONG" if "LONG" in plan.get("direction", "").upper() else "🔴 SHORT"
    
    theories_used = ", ".join(plan.get("theories_evaluated", []))
    message = (
        f"🏛️ *Institutional Trade Execution Plan*\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"🎯 *Direction:* `{direction_icon}` | *Confidence:* `{plan.get('confidence', 80)}%`\n"
        f"⚙️ *Leverage:* `{plan.get('leverage', '3x - 5x')}` | *R:R Ratio:* `{plan.get('risk_reward', '1:3')}`\n\n"
        f"📥 *Entry Zone:* `${plan.get('entry_zone', 'Market')}`\n"
        f"🛑 *Stop Loss:* `${plan.get('stop_loss', 'N/A')}`\n\n"
        f"🎯 *Take Profit Targets:*\n"
        f"  ├ TP 1: `${plan.get('tp1', 'N/A')}`\n"
        f"  ├ TP 2: `${plan.get('tp2', 'N/A')}`\n"
        f"  └ TP 3: `${plan.get('tp3', 'N/A')}`\n\n"
        f"🧠 *Theories Evaluated:* `{theories_used}`\n"
        f"📝 *Summary:* _{plan.get('summary', 'Setup validated.')}_\n\n"
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

def render_tradingview_widget(symbol_raw):
    widget_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol_raw}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 480,
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
    components.html(widget_code, height=500)

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

# ================= UNIVERSAL MULTI-THEORY AI ENGINE =================
def run_universal_theory_analysis(coin, price, ohlcv_text, rsi, ema20, ema50, atr, dom_info, selected_theories, timeframe, api_key):
    if not api_key:
        return {"error": "Gemini API Key missing"}
    
    theories_list_str = "\n- ".join(selected_theories)
    
    prompt = f"""
    You are an elite Chief Technical Analyst and Quantitative Fund Manager.
    Perform an exhaustive multi-theory technical analysis on {coin} using the user-selected technical theories.

    MARKET DATA:
    - Pair: {coin}
    - Timeframe: {timeframe}
    - Current Real-time Price: ${price}
    - RSI (14): {rsi}
    - 20 EMA: ${ema20:,.4f} | 50 EMA: ${ema50:,.4f}
    - ATR (14): ${atr:,.4f}
    - Order Book Dominance: {dom_info}
    - Recent Price Candles (Open, High, Low, Close, Volume):
    {ohlcv_text}

    THEORIES SELECTED BY TRADER TO EVALUATE:
    - {theories_list_str}

    INSTRUCTIONS:
    1. Cross-examine the price action through EACH of the selected theories.
    2. Check for confluence (whether the theories agree on direction).
    3. Formulate an actionable, institutional-grade execution plan with realistic targets, precise invalidation (Stop Loss), recommended leverage, and risk-to-reward ratio.

    RESPOND ONLY IN PURE VALID JSON FORMAT (Strictly no markdown blocks, no text before or after):
    {{
      "direction": "STRONG LONG" or "STRONG SHORT" or "WAIT / NEUTRAL",
      "confidence": 85,
      "quality_grade": "A+",
      "risk_reward": "1:3.2",
      "leverage": "3x - 5x (Max 10x with strict SL)",
      "entry_zone": "{price} - {price * 0.995:.4f}",
      "tp1": "{price * 1.02:.4f}",
      "tp2": "{price * 1.045:.4f}",
      "tp3": "{price * 1.08:.4f}",
      "stop_loss": "{price * 0.985:.4f}",
      "theories_evaluated": ["SMC", "Wyckoff"],
      "theory_breakdown": [
         {{"theory": "Smart Money Concepts", "finding": "Bullish Order Block retest with unmitigated FVG above"}},
         {{"theory": "Wyckoff Method", "finding": "Phase C Spring confirmed with volume absorption"}}
      ],
      "summary": "Detailed 2-sentence institutional trade thesis."
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        if res.status_code == 200:
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        return {"error": f"API responded with status {res.status_code}"}
    except Exception as e:
        return {"error": f"Engine execution error: {e}"}

# ================= UI & CONTROLS =================
st.title("🏛️ Universal Multi-Theory Crypto AI Terminal")
st.caption("Analyze any cryptocurrency across all institutional & retail trading theories simultaneously.")

# Sidebar Configuration
st.sidebar.header("🔑 API & Execution Settings")
gemini_key = st.sidebar.text_input("Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")

ALL_THEORIES = [
    "Smart Money Concepts (SMC / ICT) — Order Blocks, FVG, Liquidity Sweeps",
    "Wyckoff Method — Accumulation / Distribution, Spring, Upthrust",
    "Dow Theory & Market Structure — BOS, CHoCH, Swing Highs/Lows",
    "Elliott Wave Theory — Impulse Waves & Corrective Patterns",
    "Supply & Demand Zones — Imbalances, Compression & Engulfing",
    "Market Profile & Volume Profile — Point of Control (POC), Value Area",
    "Harmonic Patterns & Fibonacci Retracements — Gartley, Bat, Golden Pocket (0.618)",
    "Classical Chart Patterns — Double Top/Bottom, Triangles, Head & Shoulders, Flags",
    "Candlestick Patterns — Pinbars, Hammers, Morning/Evening Stars, Engulfing",
    "Gann Theory & Dynamic Support/Resistance",
    "Moving Average Trend Confluence — 20/50/200 EMA Crosses & Alignments",
    "RSI Divergence & Momentum Exhaustion (Bullish/Bearish Hidden Divergences)"
]

st.sidebar.header("📚 Theory Selection Engine")
select_all = st.sidebar.checkbox("සියලුම Theories එකවර තෝරන්න (Select All 12 Theories)", value=True)

if select_all:
    chosen_theories = ALL_THEORIES
else:
    chosen_theories = st.sidebar.multiselect(
        "විශ්ලේෂණය සඳහා අවශ්‍ය Theories තෝරන්න:",
        options=ALL_THEORIES,
        default=[
            ALL_THEORIES[0], # SMC
            ALL_THEORIES[1], # Wyckoff
            ALL_THEORIES[2], # Dow Theory
            ALL_THEORIES[4], # Supply & Demand
            ALL_THEORIES[11] # RSI Divergence
        ]
    )

# ================= CUSTOM COIN INPUT =================
c_in1, c_in2, c_in3 = st.columns([2, 1, 1])

with c_in1:
    target_coin_input = st.text_input("කාසියේ නම (Coin Symbol):", value="BTC", placeholder="e.g. BTC, ETH, SOL, XRP, SUI, DOGE").strip().upper()

with c_in2:
    selected_timeframe = st.selectbox("Timeframe (කාල පරාසය):", ["15m", "1h", "4h", "1d"], index=0)

with c_in3:
    st.write("##")
    execute_btn = st.button("🚀 Deep Analysis", use_container_width=True)

# ================= ANALYSIS EXECUTION =================
if execute_btn and target_coin_input:
    target_pair = f"{target_coin_input}USDT"
    
    if not chosen_theories:
        st.warning("⚠️ කරුණාකර අවම වශයෙන් එක් Theory එකක් හෝ තෝරන්න.")
    else:
        with st.spinner(f"Binance දත්ත සහ තෝරාගත් Theories {len(chosen_theories)} හරහා {target_pair} විශ්ලේෂණය කරමින් පවතී..."):
            try:
                t_res = requests.get(f"{BASE_URL}/ticker/24hr", params={'symbol': target_pair}, timeout=5)
                k_res = requests.get(f"{BASE_URL}/klines", params={'symbol': target_pair, 'interval': selected_timeframe, 'limit': 45}, timeout=5)
                
                if t_res.status_code == 200 and k_res.status_code == 200:
                    t_data = t_res.json()
                    k_data = k_res.json()
                    
                    real_time_price = float(t_data.get('lastPrice', 0))
                    df = pd.DataFrame(k_data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                        'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
                    ])
                    for col in ['close', 'open', 'high', 'low', 'volume']:
                        df[col] = df[col].astype(float)
                        
                    current_rsi = calculate_rsi(df['close'], period=14).iloc[-1]
                    current_ema20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                    current_ema50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
                    current_atr = calculate_atr(df, period=14)
                    buyers_pct, sellers_pct = get_orderbook_ratio(target_pair)
                    dom_str = f"Buyers: {buyers_pct}% | Sellers: {sellers_pct}%"
                    
                    # Candlestick summary formatted for AI
                    candles_summary = df[['open', 'high', 'low', 'close', 'volume']].tail(12).to_string(index=False)
                    
                    # Execute AI Deep Dive
                    analysis_plan = run_universal_theory_analysis(
                        target_pair, real_time_price, candles_summary, round(current_rsi, 1),
                        current_ema20, current_ema50, current_atr, dom_str, chosen_theories,
                        selected_timeframe, gemini_key
                    )
                    
                    if "error" in analysis_plan:
                        st.error(f"විශ්ලේෂණ දෝෂය: {analysis_plan['error']}")
                    else:
                        st.markdown("---")
                        
                        # Direction Header
                        dir_str = analysis_plan.get('direction', 'NEUTRAL')
                        color_box = "🟢" if "LONG" in dir_str else ("🔴" if "SHORT" in dir_str else "🟡")
                        
                        st.markdown(f"## {color_box} Institutional Setup: **{dir_str}** for **{target_pair}**")
                        
                        # Top Metrics Bar
                        m1, m2, m3, m4, m5 = st.columns(5)
                        m1.metric("Current Price", f"${real_time_price:,.4f}")
                        m1_delta = f"{analysis_plan.get('confidence', 80)}%"
                        m2.metric("Confidence Score", m1_delta, delta=f"Grade {analysis_plan.get('quality_grade', 'A')}")
                        m3.metric("R:R Ratio", analysis_plan.get('risk_reward', '1:3'))
                        m4.metric("Recommended Leverage", analysis_plan.get('leverage', '3x - 5x'))
                        m5.metric("Order Flow", f"🟢 {buyers_pct}% / 🔴 {sellers_pct}%")
                        
                        # Split Layout: Left Chart, Right Execution Plan
                        col_chart, col_plan = st.columns([3, 2])
                        
                        with col_chart:
                            st.markdown("### 📊 Interactive Technical Chart")
                            render_tradingview_widget(target_pair)
                            
                        with col_plan:
                            st.markdown("### 🎯 Actionable Execution Card")
                            
                            # Trade Plan Table
                            plan_data = {
                                "Parameter": ["Direction", "Entry Zone", "Stop Loss (Invalidation)", "Take Profit 1", "Take Profit 2", "Take Profit 3 (Runner)", "Max Safe Leverage"],
                                "Value": [
                                    dir_str,
                                    f"${analysis_plan.get('entry_zone', 'Market')}",
                                    f"${analysis_plan.get('stop_loss', 'N/A')}",
                                    f"${analysis_plan.get('tp1', 'N/A')}",
                                    f"${analysis_plan.get('tp2', 'N/A')}",
                                    f"${analysis_plan.get('tp3', 'N/A')}",
                                    analysis_plan.get('leverage', '3x - 5x')
                                ]
                            }
                            st.dataframe(pd.DataFrame(plan_data), use_container_width=True, hide_index=True)
                            
                            st.markdown("#### 📝 Trade Thesis")
                            st.info(analysis_plan.get('summary', 'Setup validated across technical structures.'))
                            
                            if st.button("📲 Send Plan to Telegram", use_container_width=True):
                                res = send_telegram_alert(f"{target_coin_input}/USDT", analysis_plan)
                                if res.status_code == 200:
                                    st.success("✅ Trade Plan එක සාර්ථකව Telegram වෙත යවන ලදී!")
                                else:
                                    st.error("Telegram Error: පණිවිඩය යැවීමට නොහැකි විය.")
                                    
                        # Bottom Section: Detailed Theory-by-Theory Findings
                        st.markdown("---")
                        st.markdown("### 🧠 Theory-by-Theory Confluence Findings")
                        breakdown_list = analysis_plan.get("theory_breakdown", [])
                        
                        if breakdown_list:
                            cols = st.columns(min(len(breakdown_list), 3))
                            for idx, item in enumerate(breakdown_list):
                                with cols[idx % 3]:
                                    st.success(f"**{item.get('theory')}**")
                                    st.write(item.get('finding'))
                        else:
                            st.write("Confluence theories evaluated directly in synthesis.")
                            
                else:
                    st.error(f"Binance හි `{target_pair}` නමින් Pair එකක් සොයාගත නොහැකි විය. කරුණාකර නිවැරදි Coin Symbol එකක් යොදන්න.")
            except Exception as e:
                st.error(f"දත්ත ලබාගැනීමේදී දෝෂයක් ඇති විය: {e}")
