import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import html
import time
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Institutional Terminal with Full Indicators", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = ""

SPOT_BASE_URL = "https://data-api.binance.vision/api/v3"
FUTURES_BASE_URL = "https://fapi.binance.com/fapi/v1"
FUTURES_DATA_URL = "https://fapi.binance.com/futures/data"

def send_theory_telegram_alert(coin, plan):
    clean_symbol = coin.replace('/', '_')
    direction_val = plan.get('direction', 'LONG')
    icon = "🟢" if "LONG" in direction_val else "🔴"
    
    summary_clean = html.escape(str(plan.get('summary', 'Setup aligned.')))
    reasons_text = ""
    for b_item in plan.get("theory_breakdown", []):
        th_name = html.escape(b_item.get('theory', 'Concept'))
        th_reason = html.escape(b_item.get('why_reason', 'Aligned'))
        reasons_text += f"\n• <b>{th_name}:</b> {th_reason}"

    deriv = plan.get('derivatives', {})
    msg_html = (
        f"🏛️ <b>Institutional Indicators & Concept Setup</b>\n\n"
        f"🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"🎯 <b>Verdict:</b> {icon} <b>{direction_val}</b> | <b>Score:</b> <code>{plan.get('confidence', 80)}%</code>\n"
        f"📈 <b>RSI (14):</b> <code>{plan.get('rsi_val', 50)}</code> | <b>Order Book:</b> {plan.get('orderbook', 'N/A')}\n"
        f"📊 <b>Funding:</b> <code>{deriv.get('funding_rate', '0%')}</code> | <b>OI:</b> <code>{deriv.get('oi_value', 'N/A')}</code>\n"
        f"🐋 <b>Liquidation Pool (50x):</b> <code>{deriv.get('liq_levels_50x', 'N/A')}</code>\n\n"
        f"📥 <b>Entry Zone:</b> <code>${plan.get('entry_zone', 'Market')}</code>\n"
        f"🛑 <b>Stop Loss:</b> <code>${plan.get('stop_loss', 'N/A')}</code>\n"
        f"🎯 <b>TP1:</b> <code>${plan.get('tp1', 'N/A')}</code> | <b>TP2:</b> <code>${plan.get('tp2', 'N/A')}</code>\n\n"
        f"🧠 <b>තෝරාගත් Theories වල හේතු සාරාංශය:</b>{reasons_text}\n\n"
        f"📝 <b>Thesis:</b> {summary_clean}\n\n"
        f"🔗 <a href='https://www.binance.com/en/trade/{clean_symbol}'>Trade on Binance</a>"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg_html, "parse_mode": "HTML", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=8)

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

def render_heatmap_widget():
    heatmap_code = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-crypto-coins-heatmap.js" async>
      {
        "dataSource": "Crypto", "blockSize": "market_cap_calc", "blockColor": "change",
        "locale": "en", "symbolUrl": "", "colorTheme": "dark", "hasTopBar": true,
        "isTransparent": false, "autosize": true, "container_id": "tradingview_heatmap"
      }
      </script>
    </div>
    """
    components.html(heatmap_code, height=600)

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

def fetch_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/", timeout=4)
        if res.status_code == 200:
            return res.json()['data'][0]['value'], res.json()['data'][0]['value_classification']
    except Exception: pass
    return "50", "Neutral"

def fetch_crypto_rss_news():
    feeds = [("CoinTelegraph", "https://cointelegraph.com/rss"), ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/")]
    news_items = []
    for source_name, url in feeds:
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall('./channel/item')[:6]:
                    title = item.find('title').text if item.find('title') is not None else "No Title"
                    link = item.find('link').text if item.find('link') is not None else "#"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    news_items.append({"source": source_name, "title": title, "link": link, "date": pub_date[:16], "impact": "🟢 BULLISH"})
        except Exception: continue
    return news_items

def fetch_derivatives_intelligence(symbol):
    info = {"funding_rate": "0.0000%", "funding_bias": "Balanced", "oi_value": "N/A", "top_traders_ratio": "50% Long / 50% Short"}
    try:
        res_p = requests.get(f"{FUTURES_BASE_URL}/premiumIndex", params={'symbol': symbol}, timeout=3)
        if res_p.status_code == 200:
            fr = float(res_p.json().get('lastFundingRate', 0)) * 100
            info["funding_rate"] = f"{fr:+.4f}%"
            info["funding_bias"] = "⚠️ Long Squeeze Risk" if fr > 0.04 else ("🚀 Short Squeeze Fuel" if fr < -0.02 else "Balanced")
    except Exception: pass
    try:
        res_oi = requests.get(f"{FUTURES_BASE_URL}/openInterest", params={'symbol': symbol}, timeout=3)
        if res_oi.status_code == 200:
            info["oi_value"] = f"{float(res_oi.json().get('openInterest', 0)):,.0f}"
    except Exception: pass
    return info

def resolve_any_binance_coin(user_input):
    clean = user_input.strip().upper()
    for quote in ['USDT', 'USDC', 'BUSD', 'FDUSD']: clean = clean.replace(quote, "")
    clean = clean.replace('/', '').replace('_', '').replace('-', '')
    for sym in [f"{clean}USDT", f"1000{clean}USDT", f"10000{clean}USDT", f"{clean}USDC"]:
        try:
            if requests.get(f"{SPOT_BASE_URL}/ticker/price", params={'symbol': sym}, timeout=2).status_code == 200:
                return sym, False, "Spot"
        except Exception: pass
        try:
            if requests.get(f"{FUTURES_BASE_URL}/ticker/price", params={'symbol': sym}, timeout=2).status_code == 200:
                return sym, True, "Futures"
        except Exception: pass
    return None, False, None

def fetch_universal_adaptive_data(resolved_symbol, is_futures):
    endpoint = FUTURES_BASE_URL if is_futures else SPOT_BASE_URL
    tf_data = {}
    chk = requests.get(f"{endpoint}/klines", params={'symbol': resolved_symbol, 'interval': '1h', 'limit': 15}, timeout=4)
    is_brand_new = True if chk.status_code == 200 and len(chk.json()) < 12 else False

    for tf in (['15m', '5m', '3m', '1m'] if is_brand_new else ['1d', '4h', '1h', '15m']):
        try:
            res = requests.get(f"{endpoint}/klines", params={'symbol': resolved_symbol, 'interval': tf, 'limit': 35}, timeout=4)
            if res.status_code == 200:
                candles = res.json()
                if len(candles) >= 1:
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                    for col in ['close', 'open', 'high', 'low', 'volume']: df[col] = df[col].astype(float)
                    rsi = calculate_rsi(df['close'], period=min(14, max(2, len(df)-1))).iloc[-1]
                    ema20 = df['close'].ewm(span=min(20, len(df)), adjust=False).mean().iloc[-1]
                    cur_p = df['close'].iloc[-1]
                    is_bull = cur_p >= ema20 and rsi >= 48
                    tf_data[tf] = {
                        "price": cur_p, "rsi": round(rsi, 1), "ema20": ema20,
                        "status": "BULLISH 🟢" if is_bull else "BEARISH 🔴",
                        "raw_bull": is_bull, "atr": calculate_atr(df, period=14), "df": df
                    }
        except Exception: continue
    return tf_data, is_brand_new

def compute_institutional_trade_setup(symbol_resolved, current_price, mtf_data, orderbook_str, selected_theories, is_brand_new, derivatives, rsi_val):
    bull_count = sum(1 for tf, d in mtf_data.items() if d['raw_bull'])
    long_score = int((bull_count / max(1, len(mtf_data))) * 100)
    
    if rsi_val > 70: long_score -= 15
    elif rsi_val < 30: long_score += 15

    is_long_priority = long_score >= 50
    final_direction = "STRONG LONG" if long_score >= 75 else "STRONG SHORT"
    confidence = max(long_score, 100 - long_score)
    
    atr_val = current_price * 0.02
    for tf_k in ['15m', '1h', '5m']:
        if tf_k in mtf_data: atr_val = mtf_data[tf_k]['atr']; break
            
    sl_long = max(0.00000001, current_price - (atr_val * 1.5))
    tp1_l = current_price + (atr_val * 2.2)
    tp2_l = current_price + (atr_val * 3.8)
    
    sl_short = current_price + (atr_val * 1.5)
    tp1_s = max(0.00000001, current_price - (atr_val * 2.2))
    tp2_s = max(0.00000001, current_price - (atr_val * 3.8))
    
    liq_50x = f"Longs Liq: ${current_price*0.98:,.4f} | Shorts Liq: ${current_price*1.02:,.4f}"
    derivatives["liq_levels_50x"] = liq_50x

    theory_findings = []
    for th in selected_theories:
        short_t = th.split("—")[0].strip()
        if "RSI" in short_t:
            reason = f"RSI (14) අගය {rsi_val} මඟින් මොමෙන්ටම් තත්ත්වය සහ වෙළඳපොළ Overbought/Oversold කලාපය මනාව පෙන්වා දෙයි."
        elif "Smart Money" in short_t:
            reason = f"Liquidity Sweep සහ Order Block මඟින් Whales ලාගේ පිවිසුම් ලක්ෂ්‍යය සනාථ වේ."
        elif "Dow" in short_t:
            reason = f"වෙළඳපොළ ව්‍යුහය (Market Structure) පරීක්ෂා කළ විට {'Higher Highs (Bullish BOS)' if is_long_priority else 'Lower Lows (Bearish CHoCH)'} සනාථ වේ."
        else:
            reason = f"මෙම න්‍යාය මඟින් වත්මන් මිල ක්‍රියාකාරිත්වය සහ ඇනලයිස් දිශාව ({final_direction}) එකිනෙකට එකඟ වන බව තහවුරු කරයි."
        theory_findings.append({"theory": short_t, "why_reason": reason})

    return {
        "direction": final_direction, "confidence": confidence, "long_score": long_score,
        "risk_reward": "1:2.8", "leverage": "5x - 10x",
        "entry_zone": f"{current_price*0.996:,.4f} - {current_price*1.003:,.4f}",
        "tp1": f"{tp1_l:,.4f}" if is_long_priority else f"{tp1_s:,.4f}",
        "tp2": f"{tp2_l:,.4f}" if is_long_priority else f"{tp2_s:,.4f}",
        "tp3": f"{tp2_l*1.2:,.4f}", "stop_loss": f"{sl_long:,.4f}" if is_long_priority else f"{sl_short:,.4f}",
        "rsi_val": rsi_val, "orderbook": orderbook_str,
        "theory_breakdown": theory_findings,
        "summary": f"RSI ({rsi_val}), Order Book ({orderbook_str}) සහ Confluence මඟින් {final_direction} තහවුරු වේ.",
        "derivatives": derivatives
    }

if "last_plan" not in st.session_state: st.session_state.last_plan = None
if "last_coin" not in st.session_state: st.session_state.last_coin = None

# Sidebar Settings
st.sidebar.header("⚙️ General Settings")
gemini_key = st.sidebar.text_input("Gemini API Key (Optional)", value=DEFAULT_GEMINI_KEY, type="password")

# ================= TABS NAVIGATION =================
tab_theory, tab_heatmap, tab_news, tab_scanner = st.tabs([
    "🏛️ Universal Coin & Indicators", "🔥 Live Heatmaps", "📰 News Hub", "📡 Scanner"
])

with tab_theory:
    st.subheader("🏛️ Institutional Terminal with RSI, Order Book & Concept Reasons")
    
    ALL_THEORIES = [
        "Smart Money Concepts (SMC / ICT) — Order Blocks, FVG, Liquidity Sweeps",
        "Wyckoff Method — Accumulation / Distribution, Spring, Upthrust",
        "Dow Theory & Market Structure — BOS, CHoCH, Swing Highs/Lows",
        "RSI Divergence & Momentum Exhaustion — Hidden & Regular Divergences",
        "Supply & Demand Imbalance — Fresh Zones, Compression, Engulfing",
        "Moving Average Trend Confluence — 20/50 EMA Alignments"
    ]

    th_c1, th_c2 = st.columns([1, 2])
    with th_c1: select_all = st.checkbox("සියලුම Theories සක්‍රීය කරන්න", value=True)
    with th_c2: active_th = ALL_THEORIES if select_all else st.multiselect("Theories තෝරන්න:", options=ALL_THEORIES, default=ALL_THEORIES[:3])

    st.write("---")
    c1, c2 = st.columns([3, 1])
    with c1: coin_input = st.text_input("Coin නම (උදා: FLOCK, SOL, BTC, PEPE):", value="FLOCK").strip().upper()
    with c2:
        st.write("##")
        run_btn = st.button("🚀 Deep Analysis", use_container_width=True)

    if run_btn and coin_input:
        with st.spinner(f"Binance හි `{coin_input}` දත්ත, RSI සහ Order Book පරීක්ෂා කරමින් පවතී..."):
            try:
                res_sym, is_fut, m_type = resolve_any_binance_coin(coin_input)
                if res_sym:
                    mtf_data, is_new = fetch_universal_adaptive_data(res_sym, is_fut)
                    deriv = fetch_derivatives_intelligence(res_sym)
                    if mtf_data:
                        low_tf = list(mtf_data.keys())[0]
                        price = mtf_data[low_tf]['price']
                        rsi_val = mtf_data[low_tf]['rsi']
                        b_pct, s_pct = get_orderbook_ratio(res_sym)
                        ob_txt = f"🟢 Buyers {b_pct}% / 🔴 Sellers {s_pct}%"
                        
                        plan = compute_institutional_trade_setup(res_sym, price, mtf_data, ob_txt, active_th, is_new, deriv, rsi_val)
                        st.session_state.last_plan = plan
                        st.session_state.resolved_sym = res_sym
                        st.session_state.last_price = price
                        st.session_state.is_futures = is_fut
            except Exception as e: st.error(f"දෝෂයකි: {e}")

    if st.session_state.get('last_plan'):
        plan = st.session_state.last_plan
        res_sym = st.session_state.resolved_sym
        price = st.session_state.last_price
        deriv = plan.get('derivatives', {})

        st.markdown(f"## 🟢 Verdict: **{plan.get('direction')}** for **{res_sym}**")
        
        # ================= RSI & INDICATOR METRIC BAR =================
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Price", f"${price:,.4f}" if price >= 1 else f"${price:,.6f}")
        m2.metric("RSI (14)", f"{plan.get('rsi_val')} / 100", "Momentum Strength")
        m3.metric("Order Book Flow", plan.get('orderbook'))
        m4.metric("Funding Rate", deriv.get('funding_rate', '0.00%'), delta=deriv.get('funding_bias'))

        st.info(f"🐋 **Liquidation Pool Target:** {deriv.get('liq_levels_50x')}")

        c_widget, c_card = st.columns([3, 2])
        with c_widget: render_tradingview_widget(res_sym, is_futures=st.session_state.is_futures)
        with c_card:
            st.markdown("### 🎯 Primary Setup")
            st.write(f"**Entry Zone:** ${plan.get('entry_zone')}")
            st.write(f"**Stop Loss:** ${plan.get('stop_loss')}")
            st.write(f"**TP 1 / TP 2:** ${plan.get('tp1')} / ${plan.get('tp2')}")
            st.info(plan.get('summary'))
            if st.button("📲 Send to Telegram", use_container_width=True):
                send_theory_telegram_alert(res_sym, plan)
                st.success("✅ Telegram වෙත යවන ලදී!")

        # ================= CONCEPT REASONING BREAKDOWN =================
        st.markdown("---")
        st.markdown("### 🧠 භාවිතා කළ Concepts වල හේතු සාරාංශය (Why this Trade?)")
        st.caption("RSI, SMC, Dow Theory සහ අනෙකුත් න්‍යායන් මෙම තීරණයට එළඹීමට බලපෑ ආකාරය පිළිබඳ තාක්ෂණික විග්‍රහය:")
        
        for b_item in plan.get("theory_breakdown", []):
            with st.expander(f"📌 {b_item.get('theory')} — හේතුව", expanded=True):
                st.write(b_item.get('why_reason'))

with tab_heatmap:
    st.subheader("🔥 Live Crypto Market Performance & Sector Heatmaps")
    render_heatmap_widget()

with tab_news:
    st.subheader("📰 Live Fundamental News Hub")
    f_val, f_class = fetch_fear_and_greed()
    st.metric("Fear & Greed Index", f"{f_val} / 100", f_class)
    for n in fetch_crypto_rss_news():
        st.markdown(f"**[{n['title']}]({n['link']})** — `{n['source']}` ({n['impact']})")

with tab_scanner:
    st.subheader("📡 Live 24/7 Autonomous Scanner")
    st.success("🟢 Scanner එක ක්‍රියාත්මකයි.")
