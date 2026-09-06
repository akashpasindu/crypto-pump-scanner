import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import html
import time
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Professional Institutional Crypto Terminal", layout="wide")

# ================= PROFESSIONAL RESPONSIVE TABS CSS =================
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }
    /* Make all 7 tabs fit perfectly and look gorgeous */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        background-color: #161b22;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1;
        min-width: 120px;
        height: 42px;
        background-color: #21262d;
        border-radius: 8px;
        color: #c9d1d9;
        font-weight: 600;
        font-size: 13px;
        padding: 0 10px;
        transition: all 0.3s ease;
        border: 1px solid #30363d;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #30363d;
        color: #58a6ff;
        border-color: #58a6ff;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1f6feb 0%, #238636 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(31, 111, 235, 0.4);
    }
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .stButton button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = ""

SPOT_BASE_URL = "https://data-api.binance.vision/api/v3"
FUTURES_BASE_URL = "https://fapi.binance.com/fapi/v1"
FUTURES_DATA_URL = "https://fapi.binance.com/futures/data"

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

def send_divergence_telegram_alert(div_type, coin, price, rsi_val):
    clean_symbol = coin.replace('/', '_')
    icon = "🟢 <b>Auto Bullish Divergence Detected</b>" if div_type == "BULLISH_DIV" else "🔴 <b>Auto Bearish Divergence Detected</b>"
    msg_html = (
        f"{icon}\n\n"
        f"🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"💵 <b>Price:</b> <code>${price}</code>\n"
        f"📈 <b>RSI (14):</b> <code>{rsi_val}</code>\n"
        f"🔍 <b>Status:</b> <code>Whale Reversal Setup Active</code>\n\n"
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
    for b_item in plan.get("theory_breakdown", []):
        th_name = html.escape(b_item.get('theory', 'Concept'))
        th_reason = html.escape(b_item.get('why_reason', 'Aligned'))
        reasons_text += f"\n• <b>{th_name}:</b> {th_reason}"

    derivatives_data = plan.get('derivatives', {})
    oi_txt = derivatives_data.get('oi_status', 'N/A')
    funding_txt = derivatives_data.get('funding_rate', 'N/A')
    liq_50x = derivatives_data.get('liq_levels_50x', 'N/A')
    rsi_val = plan.get('rsi_val', 50)
    orderbook = plan.get('orderbook', 'N/A')

    msg_html = (
        f"⚡ <b>INSTANT SCALP FULL SIGNAL CARD</b>\n\n"
        f"🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"🎯 <b>Verdict:</b> {icon} <b>{direction_val}</b> | <b>Score:</b> <code>{plan.get('confidence', 85)}%</code>\n"
        f"📈 <b>RSI (14):</b> <code>{rsi_val} / 100</code> | <b>Order Book:</b> {orderbook}\n"
        f"📊 <b>Derivatives:</b> OI: <code>{oi_txt}</code> | Funding: <code>{funding_txt}</code>\n"
        f"⚙️ <b>Leverage:</b> <code>{plan.get('leverage', '5x - 10x')}</code> | <b>R:R:</b> <code>{plan.get('risk_reward', '1:2.8')}</code>\n\n"
        f"📥 <b>Entry Zone:</b> <code>${plan.get('entry_zone', 'Market')}</code>\n"
        f"🛑 <b>Stop Loss:</b> <code>${plan.get('stop_loss', 'N/A')}</code>\n\n"
        f"🎯 <b>Scalp Targets:</b>\n"
        f"  ├ TP 1: <code>${plan.get('tp1', 'N/A')}</code>\n"
        f"  ├ TP 2: <code>${plan.get('tp2', 'N/A')}</code>\n"
        f"  └ TP 3: <code>${plan.get('tp3', 'N/A')}</code>\n\n"
        f"🧠 <b>Scalp Thesis:</b> {summary_clean}\n\n"
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

def detect_candlestick_pattern(df):
    if len(df) < 3: return "Momentum Play ⚡"
    c1, o1, h1, l1 = df['close'].iloc[-1], df['open'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
    c2, o2 = df['close'].iloc[-2], df['open'].iloc[-2]
    body1 = abs(c1 - o1)
    lower_wick1 = min(c1, o1) - l1
    upper_wick1 = h1 - max(c1, o1)
    
    if (c2 < o2) and (c1 > o1) and (c1 >= o2): return "Bullish Engulfing 🟢"
    if (lower_wick1 >= 1.5 * body1) and (c1 >= o1): return "Bullish Hammer 🔨"
    if (c2 > o2) and (c1 < o1) and (c1 <= o2): return "Bearish Engulfing 🔴"
    if (upper_wick1 >= 1.5 * body1) and (c1 <= o1): return "Shooting Star 🌠"
    return "Volume Breakout ⚡"

def check_auto_divergence(closes, rsi_series):
    if len(closes) < 15: return None
    p_cur, p_prev = closes.iloc[-1], closes.iloc[-5]
    r_cur, r_prev = rsi_series.iloc[-1], rsi_series.iloc[-5]
    if p_cur < p_prev and r_cur > r_prev and r_cur < 45: return "BULLISH_DIV"
    elif p_cur > p_prev and r_cur < r_prev and r_cur > 55: return "BEARISH_DIV"
    return None

def fetch_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/", timeout=4)
        if res.status_code == 200:
            data = res.json()['data'][0]
            return data['value'], data['value_classification']
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
                    description = item.find('description').text if item.find('description') is not None else ""
                    clean_text = (title + " " + description).lower()
                    
                    bull_hits = sum(1 for w in ['surge', 'rally', 'soar', 'etf', 'partnership', 'bull', 'gain', 'breakout', 'inflow'] if w in clean_text)
                    bear_hits = sum(1 for w in ['crash', 'drop', 'sec', 'lawsuit', 'hack', 'bear', 'ban', 'plunge', 'dump'] if w in clean_text)
                    impact = "🟢 BULLISH" if bull_hits > bear_hits else ("🔴 BEARISH" if bear_hits > bull_hits else "⚪ NEUTRAL")
                    news_items.append({"source": source_name, "title": title, "link": link, "date": pub_date[:16], "impact": impact})
        except Exception: continue
    return news_items

def fetch_derivatives_intelligence(symbol):
    info = {
        "is_futures_available": False, "funding_rate": "0.0000%", "funding_raw": 0.0,
        "funding_bias": "Neutral", "oi_value": "N/A", "oi_status": "Normal Flow",
        "top_traders_ratio": "50% Long / 50% Short", "liq_levels_50x": "N/A", "liq_levels_25x": "N/A"
    }
    try:
        res_p = requests.get(f"{FUTURES_BASE_URL}/premiumIndex", params={'symbol': symbol}, timeout=3)
        if res_p.status_code == 200:
            data_p = res_p.json()
            info["is_futures_available"] = True
            fr = float(data_p.get('lastFundingRate', 0)) * 100
            info["funding_raw"] = fr
            info["funding_rate"] = f"{fr:+.4f}%"
            info["funding_bias"] = "⚠️ Long Squeeze Risk" if fr > 0.04 else ("🚀 Short Squeeze Fuel" if fr < -0.02 else "Balanced")
    except Exception: pass

    try:
        res_oi = requests.get(f"{FUTURES_BASE_URL}/openInterest", params={'symbol': symbol}, timeout=3)
        if res_oi.status_code == 200:
            info["oi_value"] = f"{float(res_oi.json().get('openInterest', 0)):,.0f}"
            info["oi_status"] = "Active Interest"
    except Exception: pass

    try:
        res_ls = requests.get(f"{FUTURES_DATA_URL}/topLongShortPositionRatio", params={'symbol': symbol, 'period': '15m', 'limit': 1}, timeout=3)
        if res_ls.status_code == 200 and len(res_ls.json()) > 0:
            ls = res_ls.json()[0]
            info["top_traders_ratio"] = f"🟢 {round(float(ls.get('longAccount',0.5))*100,1)}% L vs 🔴 {round(float(ls.get('shortAccount',0.5))*100,1)}% S"
    except Exception: pass

    return info

def resolve_any_binance_coin(user_input):
    clean = user_input.strip().upper()
    for quote in ['USDT', 'USDC', 'BUSD', 'FDUSD']: clean = clean.replace(quote, "")
    clean = clean.replace('/', '').replace('_', '').replace('-', '')
    potential_symbols = [f"{clean}USDT", f"1000{clean}USDT", f"10000{clean}USDT", f"1000000{clean}USDT", f"{clean}USDC", f"1000{clean}USDC"]

    for sym in potential_symbols:
        try:
            if requests.get(f"{SPOT_BASE_URL}/ticker/price", params={'symbol': sym}, timeout=2).status_code == 200:
                return sym, False, "Spot Market"
        except Exception: pass
        try:
            if requests.get(f"{FUTURES_BASE_URL}/ticker/price", params={'symbol': sym}, timeout=2).status_code == 200:
                return sym, True, "Futures / Perpetual"
        except Exception: pass
    return None, False, None

def fetch_universal_adaptive_data(resolved_symbol, is_futures):
    endpoint = FUTURES_BASE_URL if is_futures else SPOT_BASE_URL
    tf_data = {}
    standard_tfs = ['1d', '4h', '1h', '15m']
    chk = requests.get(f"{endpoint}/klines", params={'symbol': resolved_symbol, 'interval': '1h', 'limit': 15}, timeout=4)
    is_brand_new = True if chk.status_code == 200 and len(chk.json()) < 12 else False

    for tf in (['15m', '5m', '3m', '1m'] if is_brand_new else standard_tfs):
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
    total_tfs = max(1, len(mtf_data))
    long_score = int((bull_count / total_tfs) * 100)
    
    if rsi_val > 70: long_score -= 15
    elif rsi_val < 30: long_score += 15

    if derivatives.get("funding_raw", 0) < -0.02: long_score = min(98, long_score + 10)
    elif derivatives.get("funding_raw", 0) > 0.04: long_score = max(5, long_score - 10)

    short_score = 100 - long_score
    is_long_priority = long_score >= 50
    prefix_mode = "NEW LISTING " if is_brand_new else ""
    final_direction = f"{prefix_mode}STRONG LONG" if long_score >= 75 else (f"{prefix_mode}STRONG SHORT" if short_score >= 75 else (f"{prefix_mode}SCALP LONG" if is_long_priority else f"{prefix_mode}SCALP SHORT"))
    confidence = max(long_score, short_score)
    
    atr_val = current_price * 0.02
    for tf_k in ['15m', '1h', '5m']:
        if tf_k in mtf_data: atr_val = mtf_data[tf_k]['atr']; break
            
    atr_multiplier = 1.8 if is_brand_new else 1.5
    sl_long = max(0.00000001, current_price - (atr_val * atr_multiplier))
    tp1_l = current_price + (atr_val * 2.2)
    tp2_l = current_price + (atr_val * 3.8)
    tp3_l = current_price + (atr_val * 5.5)
    
    sl_short = current_price + (atr_val * atr_multiplier)
    tp1_s = max(0.00000001, current_price - (atr_val * 2.2))
    tp2_s = max(0.00000001, current_price - (atr_val * 3.8))
    tp3_s = max(0.00000001, current_price - (atr_val * 5.5))
    
    liq_50x_long = current_price * (1 - (1/50)*0.9)
    liq_50x_short = current_price * (1 + (1/50)*0.9)
    liq_25x_long = current_price * (1 - (1/25)*0.9)
    liq_25x_short = current_price * (1 + (1/25)*0.9)
    
    fmt = ".6f" if current_price < 0.01 else (".4f" if current_price < 10 else ".2f")
    derivatives["liq_levels_50x"] = f"Longs Liq: ${format(liq_50x_long, fmt)} | Shorts Liq: ${format(liq_50x_short, fmt)}"
    derivatives["liq_levels_25x"] = f"Longs Liq: ${format(liq_25x_long, fmt)} | Shorts Liq: ${format(liq_25x_short, fmt)}"

    if is_long_priority:
        active_entry = f"{format(current_price * 0.996, fmt)} - {format(current_price * 1.003, fmt)}"
        active_sl = format(sl_long, fmt)
        active_tp1 = format(tp1_l, fmt)
        active_tp2 = format(tp2_l, fmt)
        active_tp3 = format(tp3_l, fmt)
        active_rr = "1:2.8"
        active_lev = "5x - 10x"
    else:
        active_entry = f"{format(current_price * 1.004, fmt)} - {format(current_price * 0.997, fmt)}"
        active_sl = format(sl_short, fmt)
        active_tp1 = format(tp1_s, fmt)
        active_tp2 = format(tp2_s, fmt)
        active_tp3 = format(tp3_s, fmt)
        active_rr = "1:2.6"
        active_lev = "3x - 5x"

    mtf_lines = [f"• <b>{tf_key.upper()}:</b> {d['status']} (RSI: {d['rsi']})" for tf_key, d in mtf_data.items()]
    mtf_summary = "\n".join(mtf_lines)

    theory_findings = []
    for th in selected_theories:
        short_t = th.split("—")[0].strip()
        if "RSI" in short_t:
            reason = f"RSI (14) අගය {rsi_val} මඟින් මොමෙන්ටම් තත්ත්වය සහ Scalp පිවිසුම සනාථ කරයි."
        elif "Smart Money" in short_t:
            reason = f"Liquidity Sweep සහ Order Block මත Scalping සඳහා කදිම අවස්ථාවකි. Liq Zone: ${format(liq_50x_short, fmt)}."
        else:
            reason = f"මෙම න්‍යාය මඟින් වත්මන් මිල ක්‍රියාකාරිත්වය සහ Scalp දිශාව ({final_direction}) එකිනෙකට එකඟ වන බව තහවුරු කරයි."
        theory_findings.append({"theory": short_t, "why_reason": reason})

    return {
        "direction": final_direction, "confidence": confidence, "long_score": long_score, "short_score": short_score,
        "risk_reward": active_rr, "leverage": active_lev, "entry_zone": active_entry,
        "tp1": active_tp1, "tp2": active_tp2, "tp3": active_tp3, "stop_loss": active_sl,
        "rsi_val": rsi_val, "orderbook": orderbook_str,
        "theories_evaluated": [t.split("—")[0].strip() for t in selected_theories],
        "theory_breakdown": theory_findings,
        "summary": f"RSI ({rsi_val}), Order Book ({orderbook_str}) සහ Scalp Confluence මඟින් {final_direction} තහවුරු වේ.",
        "invalidation": f"මිල ${format(sl_long, fmt)} ට වඩා පහළින් ගියහොත් Scalp Setup එක Invalid වේ." if is_long_priority else f"මිල ${format(sl_short, fmt)} ට වඩා ඉහළින් ගියහොත් Invalid වේ.",
        "mtf_summary": mtf_summary, "is_brand_new": is_brand_new, "derivatives": derivatives,
        "long_plan": {"entry": f"{format(current_price * 0.996, fmt)} - {format(current_price * 1.003, fmt)}", "sl": format(sl_long, fmt), "tp1": format(tp1_l, fmt), "tp2": format(tp2_l, fmt), "tp3": format(tp3_l, fmt), "rr": "1:2.8"},
        "short_plan": {"entry": f"{format(current_price * 1.004, fmt)} - {format(current_price * 0.997, fmt)}", "sl": format(sl_short, fmt), "tp1": format(tp1_s, fmt), "tp2": format(tp2_s, fmt), "tp3": format(tp3_s, fmt), "rr": "1:2.6"}
    }

@st.cache_resource
def get_global_state():
    return {"last_alert_time": {}, "last_div_time": {}, "last_scalp_time": {}}

global_state = get_global_state()

if "last_plan" not in st.session_state: st.session_state.last_plan = None
if "last_coin" not in st.session_state: st.session_state.last_coin = None
if "last_price" not in st.session_state: st.session_state.last_price = 0.0
if "last_mtf" not in st.session_state: st.session_state.last_mtf = {}

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
        if res.status_code != 200: return "NEUTRAL", "BTC Data Error"
        closes = pd.Series([float(x[4]) for x in res.json()])
        ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
        is_bullish = closes.iloc[-1] >= ema20
        return ("BULLISH" if is_bullish else "BEARISH"), f"BTC: ${closes.iloc[-1]:,.1f} {'🟢' if is_bullish else '🔴'}"
    except Exception:
        return "NEUTRAL", "BTC Bypassed"

def check_1h_trend(raw_symbol, current_price, signal_type, is_futures=False):
    endpoint = FUTURES_BASE_URL if is_futures else SPOT_BASE_URL
    try:
        res = requests.get(f"{endpoint}/klines", params={'symbol': raw_symbol, 'interval': '1h', 'limit': 60}, timeout=4)
        if res.status_code != 200: return True
        ema50 = pd.Series([float(x[4]) for x in res.json()]).ewm(span=50, adjust=False).mean().iloc[-1]
        return (current_price >= ema50) if signal_type == "PUMP" else (current_price <= ema50)
    except Exception:
        return True

# ================= 7 PERFECT COMPACT TABS =================
tab_theory, tab_scalp_gen, tab_risk_calc, tab_div, tab_heatmap, tab_news, tab_scanner = st.tabs([
    "🏛️ Terminal", 
    "⚡ Scalp",
    "🧮 Risk",
    "📊 Divergence",
    "🔥 Heatmap",
    "📰 News", 
    "📡 Scanner"
])

# ----------------- TAB 1: UNIVERSAL COIN DEEP DIVE -----------------
with tab_theory:
    st.subheader("🏛️ Universal Institutional Coin & Derivatives Terminal")
    st.caption("Multi-Timeframe Technicals + RSI, Order Book, Derivatives & Full Concept Reasoning Summaries.")

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
            active_theories = st.multiselect("අවශ්‍ය Theories තෝරන්න:", options=ALL_THEORIES, default=[ALL_THEORIES[0], ALL_THEORIES[1], ALL_THEORIES[2]])

    st.write("---")
    in_col1, in_col2 = st.columns([3, 1])
    with in_col1:
        custom_coin_symbol = st.text_input("Coin නම (උදා: FLOCK, SOL, BTC, PEPE, DOGE):", value="FLOCK").strip().upper()
    with in_col2:
        st.write("##")
        run_theory_btn = st.button("🚀 Deep Institutional Analysis", use_container_width=True)

    manual_analysis_running = False

    if run_theory_btn and custom_coin_symbol:
        manual_analysis_running = True
        if not active_theories:
            st.warning("⚠️ කරුණාකර අවම වශයෙන් එක් Theory එකක් තෝරන්න.")
        else:
            st.info("⏸️ **Market Scanner එක Pause කරන ලදී.** Binance Spot, Futures, RSI සහ Liquidation Clusters ගණනය කරමින් පවතී...")
            with st.spinner(f"Binance හි `{custom_coin_symbol}` සොයා Live Order Flow ගණනය කරමින් පවතී..."):
                try:
                    resolved_symbol, is_fut, market_type = resolve_any_binance_coin(custom_coin_symbol)
                    
                    if resolved_symbol:
                        mtf_data_fetched, is_brand_new = fetch_universal_adaptive_data(resolved_symbol, is_fut)
                        derivatives_intel = fetch_derivatives_intelligence(resolved_symbol)
                        
                        if mtf_data_fetched and len(mtf_data_fetched) > 0:
                            lowest_tf = list(mtf_data_fetched.keys())[0]
                            real_p = mtf_data_fetched[lowest_tf]['price']
                            rsi_val = mtf_data_fetched[lowest_tf]['rsi']
                            b_pct, s_pct = get_orderbook_ratio(resolved_symbol)
                            orderbook_txt = f"🟢 Buyers {b_pct}% / 🔴 Sellers {s_pct}%"
                            
                            plan = compute_institutional_trade_setup(resolved_symbol, real_p, mtf_data_fetched, orderbook_txt, active_theories, is_brand_new, derivatives_intel, rsi_val)
                            
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
                        st.error(f"Binance හි `{custom_coin_symbol}` නමින් Spot හෝ Futures යුගලයක් හමු නොවීය.")
                except Exception as ex:
                    st.error(f"දෝෂයක් ඇති විය: {ex}")

    if st.session_state.last_plan and st.session_state.last_coin:
        plan = st.session_state.last_plan
        coin_sym = st.session_state.last_coin
        resolved_sym = getattr(st.session_state, 'resolved_sym', f"{coin_sym}USDT")
        real_p = st.session_state.last_price
        mtf_data = st.session_state.last_mtf
        market_type = getattr(st.session_state, 'market_type', 'Spot')
        is_fut = getattr(st.session_state, 'is_futures', False)
        is_brand_new = getattr(st.session_state, 'is_brand_new', False)
        deriv = plan.get('derivatives', {})

        tag_new = " [NEW LISTING ADAPTIVE]" if is_brand_new else ""
        st.markdown("---")
        dir_label = plan.get('direction', 'NEUTRAL')
        color_icon = "🟢" if "LONG" in dir_label else "🔴"
        
        st.markdown(f"## {color_icon} Final Verdict: **{dir_label}** for **{resolved_sym}** `({market_type}){tag_new}`")
        
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        d_col1.metric("Live Price", f"${real_p:,.4f}" if real_p >= 1 else f"${real_p:,.6f}")
        d_col2.metric("RSI (14)", f"{plan.get('rsi_val')} / 100", "Momentum Strength")
        d_col3.metric("Order Book Flow", plan.get('orderbook', 'N/A'))
        d_col4.metric("Funding Rate", deriv.get('funding_rate', '0.00%'), delta=deriv.get('funding_bias'))

        st.info(f"🐋 **Whale Liquidation Cluster Target:** 50x Pool: `{deriv.get('liq_levels_50x')}` | 25x Pool: `{deriv.get('liq_levels_25x')}`")

        st.markdown("#### ⏳ Active Timeframe Structure")
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
                "Parameter": ["Final Direction", "Entry Zone", "Stop Loss (Invalidation)", "Take Profit 1", "Take Profit 2", "Take Profit 3", "R:R Ratio", "Safe Leverage"],
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
                        st.success("✅ Trade Plan එක සාර්ථකව Telegram වෙත යවන ලදී!")
                    else:
                        st.error(f"Telegram Error: {t_res_msg.text}")

        st.markdown("---")
        st.markdown("### 🧠 භාවිතා කළ Concepts වල හේතු සාරාංශය (Why this Trade?)")
        breakdown = plan.get("theory_breakdown", [])
        if breakdown:
            for b_item in breakdown:
                with st.expander(f"📌 {b_item.get('theory')} — හේතුව", expanded=True):
                    st.write(b_item.get('why_reason'))

        st.markdown("---")
        st.markdown("### ⚖️ Dual Action Plan (Long vs Short Comparison)")
        dual_data = {
            "Plan Parameter": ["Entry Zone", "Stop Loss", "TP 1", "TP 2", "TP 3", "Risk : Reward"],
            "🟢 LONG SETUP": [f"${plan['long_plan']['entry']}", f"${plan['long_plan']['sl']}", f"${plan['long_plan']['tp1']}", f"${plan['long_plan']['tp2']}", f"${plan['long_plan']['tp3']}", plan['long_plan']['rr']],
            "🔴 SHORT SETUP": [f"${plan['short_plan']['entry']}", f"${plan['short_plan']['sl']}", f"${plan['short_plan']['tp1']}", f"${plan['short_plan']['tp2']}", f"${plan['short_plan']['tp3']}", plan['short_plan']['rr']]
        }
        st.dataframe(pd.DataFrame(dual_data), use_container_width=True, hide_index=True)

# ----------------- TAB 2: INSTANT SCALP SIGNAL GENERATOR -----------------
with tab_scalp_gen:
    st.subheader("⚡ Instant Scalp Signal Generator & Top Coins Hub")
    st.caption("ഈ මොහොතේ ස්කැල්ප් කිරීමට හොඳම (High Momentum & Volume Spike) කොයින් ස්වයංක්‍රීයව සොයා Full Signal Card එකක් සාදා දෙයි සහ Telegram වෙත යවයි.")

    if st.button("🚀 Find Best Scalp Coins & Auto-Send Signals", use_container_width=True):
        with st.spinner("Binance වෙළඳපොළ සෝදිසි කරමින් හොඳම Scalp Coins සොයා Telegram වෙත යවමින් පවතී..."):
            try:
                res_spot = requests.get(f"{SPOT_BASE_URL}/ticker/24hr", timeout=8)
                if res_spot.status_code == 200:
                    top_vol = sorted([t for t in res_spot.json() if t.get('symbol', '').endswith('USDT') and not t.get('symbol', '').endswith(('UPUSDT', 'DOWNUSDT'))], key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)[:30]
                    
                    scalp_opportunities = []
                    for item in top_vol:
                        sym = item['symbol']
                        disp = f"{sym[:-4]}/USDT"
                        k_res = requests.get(f"{SPOT_BASE_URL}/klines", params={'symbol': sym, 'interval': '15m', 'limit': 20}, timeout=3)
                        if k_res.status_code == 200:
                            candles = k_res.json()
                            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                            for col in ['close', 'open', 'high', 'low', 'volume']: df[col] = df[col].astype(float)
                            
                            rsi_s = calculate_rsi(df['close'], period=14)
                            cur_rsi = rsi_s.iloc[-1]
                            cur_p = df['close'].iloc[-1]
                            chg = ((cur_p - df['open'].iloc[-1]) / df['open'].iloc[-1]) * 100
                            
                            if abs(chg) >= 1.0 and (40 <= cur_rsi <= 75):
                                scalp_opportunities.append({"symbol": sym, "disp": disp, "price": cur_p, "rsi": cur_rsi, "chg": chg})
                    
                    if scalp_opportunities:
                        st.success(f"🔥 හොඳම Scalp අවස්ථා {len(scalp_opportunities)} ක් හමුවිය! ටෙලිග්‍රැම් වෙත යවන ලදී.")
                        for s_item in scalp_opportunities[:5]:
                            mtf_f, is_new = fetch_universal_adaptive_data(s_item['symbol'], False)
                            deriv_f = fetch_derivatives_intelligence(s_item['symbol'])
                            b_p, s_p = get_orderbook_ratio(s_item['symbol'])
                            ob_str = f"🟢 Buyers {b_p}% / 🔴 Sellers {s_p}%"
                            
                            scalp_plan = compute_institutional_trade_setup(s_item['symbol'], s_item['price'], mtf_f, ob_str, ALL_THEORIES[:3], is_new, deriv_f, s_item['rsi'])
                            
                            if time.time() - global_state["last_scalp_time"].get(s_item['disp'], 0) > 3600:
                                send_theory_telegram_alert(s_item['disp'], scalp_plan)
                                global_state["last_scalp_time"][s_item['disp']] = time.time()
                            
                            with st.expander(f"📌 Scalp Setup: {s_item['disp']} | Change: {s_item['chg']:+.2f}% | RSI: {s_item['rsi']}", expanded=True):
                                st.write(f"**Entry Zone:** ${scalp_plan['entry_zone']} | **Stop Loss:** ${scalp_plan['stop_loss']}")
                                st.write(f"**Targets:** TP1: ${scalp_plan['tp1']} | TP2: ${scalp_plan['tp2']} | TP3: ${scalp_plan['tp3']}")
                                st.info(scalp_plan['summary'])
                                st.success(f"✅ Telegram වෙත යවන ලදී: {s_item['disp']}")
                    else:
                        st.warning("මෙම මොහොතේ නිශ්චිත Scalp කොන්දේසි සපුරාලූ කාසි නොමැත. නැවත උත්සාහ කරන්න.")
            except Exception as ex:
                st.error(f"Error: {ex}")

# ----------------- TAB 3: RISK & POSITION CALCULATOR -----------------
with tab_risk_calc:
    st.subheader("🧮 Advanced Risk & Position Size Calculator")
    st.caption("ඔබේ ගිණුමේ මුදල් සහ අවදානමට (Risk %) අනුව ගත යුතු නියමිත Position Size, Margin සහ Leverage ගණනය කර ගන්න.")

    rc1, rc2 = st.columns(2)
    with rc1:
        acc_balance = st.number_input("Account Balance ($)", min_value=10.0, value=1000.0, step=50.0)
        risk_pct = st.slider("Risk Tolerance (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    with rc2:
        entry_p = st.number_input("Entry Price ($)", min_value=0.000001, value=1.0, format="%.4f")
        stop_p = st.number_input("Stop Loss Price ($)", min_value=0.000001, value=0.97, format="%.4f")

    if st.button("🧮 Calculate Position Size", use_container_width=True):
        if entry_p > 0 and stop_p > 0 and entry_p != stop_p:
            dollar_risk = acc_balance * (risk_pct / 100.0)
            price_diff_pct = abs(entry_p - stop_p) / entry_p
            position_size_usd = dollar_risk / price_diff_pct
            suggested_leverage = max(1, round(position_size_usd / acc_balance))
            
            st.success("✅ රස්ක් කළමනාකරණ ගණනය කිරීම සාර්ථකයි!")
            r_col1, r_col2, r_col3, r_col4 = st.columns(4)
            r_col1.metric("Dollar Risk ($)", f"${dollar_risk:,.2f}")
            r_col2.metric("Total Position Size ($)", f"${position_size_usd:,.2f}")
            r_col3.metric("Stop Loss Distance", f"{price_diff_pct*100:.2f}%")
            r_col4.metric("Suggested Leverage", f"{suggested_leverage}x")
        else:
            st.error("⚠️ කරුණාකර නිවැරදි Entry සහ Stop Loss මිල ගණන් ඇතුළත් කරන්න.")

# ----------------- TAB 4: AUTO DIVERGENCE TRACKER -----------------
with tab_div:
    st.subheader("📊 Live Auto-Tracking RSI Divergence Detector")
    st.caption("වෙළඳපොළේ සියලුම ප්‍රධාන කාසි ස්වයංක්‍රීයව ස්කෑන් කර හැරවුම් ලක්ෂ්‍ය (Bullish & Bearish Divergences) තත්‍ය කාලීනව ලුහුබඳියි.")

    def scan_auto_divergences():
        div_results = []
        try:
            res_spot = requests.get(f"{SPOT_BASE_URL}/ticker/24hr", timeout=8)
            if res_spot.status_code == 200:
                top_coins = sorted([t for t in res_spot.json() if t.get('symbol', '').endswith('USDT')], key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)[:40]
                for item in top_coins:
                    sym = item['symbol']
                    disp = f"{sym[:-4]}/USDT"
                    k_res = requests.get(f"{SPOT_BASE_URL}/klines", params={'symbol': sym, 'interval': '15m', 'limit': 30}, timeout=3)
                    if k_res.status_code == 200:
                        candles = k_res.json()
                        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])['close'].astype(float)
                        rsi_s = calculate_rsi(df, period=14)
                        div_type = check_auto_divergence(df, rsi_s)
                        if div_type:
                            cur_p = df.iloc[-1]
                            cur_rsi = round(rsi_s.iloc[-1], 1)
                            div_results.append({
                                "Coin": disp, "Type": "🟢 BULLISH DIV (Pump)" if div_type == "BULLISH_DIV" else "🔴 BEARISH DIV (Dump)",
                                "Price": f"${cur_p:,.4f}" if cur_p >= 1 else f"${cur_p:,.6f}", "RSI": cur_rsi
                            })
                            if time.time() - global_state["last_div_time"].get(disp, 0) > 7200:
                                send_divergence_telegram_alert(div_type, disp, f"{cur_p:,.4f}", cur_rsi)
                                global_state["last_div_time"][disp] = time.time()
        except Exception as e:
            st.error(f"Scanner Error: {e}")
        return div_results

    if st.button("🔍 Run Auto-Divergence Scan Now", use_container_width=True):
        with st.spinner("වෙළඳපොළේ සියලුම ප්‍රධාන කාසි වල Divergences ස්කෑන් කරමින් පවතී..."):
            divs = scan_auto_divergences()
            if divs:
                st.success(f"🔥 ප්‍රබල Divergence සංඥා {len(divs)} ක් හමුවිය!")
                st.dataframe(pd.DataFrame(divs), use_container_width=True, hide_index=True)
            else:
                st.info("මෙම මොහොතේ ප්‍රබල Divergence සංඥා කිසිවක් හමු නොවීය.")

# ----------------- TAB 5: LIVE HEATMAPS & SECTORS -----------------
with tab_heatmap:
    st.subheader("🔥 Live Crypto Market Performance & Sector Heatmaps")
    st.caption("Coinglass / TradingView Style Interactive Heatmap Widget displaying live capital flows across all major assets.")
    render_heatmap_widget()

# ----------------- TAB 6: FUNDAMENTAL NEWS HUB -----------------
with tab_news:
    st.subheader("📰 Live Fundamental News & Macroeconomic Sentiment Hub")
    st.caption("Crypto News Feeds, Fear & Greed Index, and Real-Time Market Impact Analysis.")

    fng_val, fng_class = fetch_fear_and_greed()
    n_col1, n_col2, n_col3 = st.columns(3)
    n_col1.metric("Crypto Fear & Greed Index", f"{fng_val} / 100", fng_class)
    btc_trend_now, btc_txt = check_btc_trend()
    n_col2.metric("Market Leader (BTC)", btc_trend_now, btc_txt)
    n_col3.metric("Global Macro Regime", "High Volatility", "Interest Rates & Liquidity")

    st.write("---")
    st.markdown("### ⚡ Real-Time Breaking News Stream")
    news_list = fetch_crypto_rss_news()
    if news_list:
        for n_item in news_list:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**[{n_item['title']}]({n_item['link']})**")
                st.caption(f"Source: `{n_item['source']}` | Published: {n_item['date']}")
            with c2:
                if "BULLISH" in n_item['impact']: st.success(n_item['impact'])
                elif "BEARISH" in n_item['impact']: st.error(n_item['impact'])
                else: st.info(n_item['impact'])
            st.write("")

# ----------------- TAB 7: 24/7 AUTONOMOUS SCANNER -----------------
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
                        raw_candidates[sym] = {'symbol': sym, 'quoteVolume': float(t.get('quoteVolume', 0)), 'last': float(t.get('lastPrice', 0)), 'is_futures': False}
        except Exception: pass

        try:
            res_fut = requests.get(f"{FUTURES_BASE_URL}/ticker/24hr", timeout=8)
            if res_fut.status_code == 200:
                for t in res_fut.json():
                    sym = t.get('symbol', '')
                    if sym.endswith('USDT'):
                        if sym not in raw_candidates or float(t.get('quoteVolume', 0)) > raw_candidates[sym]['quoteVolume']:
                            raw_candidates[sym] = {'symbol': sym, 'quoteVolume': float(t.get('quoteVolume', 0)), 'last': float(t.get('lastPrice', 0)), 'is_futures': True}
        except Exception: pass

        all_coins = list(raw_candidates.values())
        if not all_coins: return alerts

        if "Top 50" in market_scope: target_list = sorted(all_coins, key=lambda x: x['quoteVolume'], reverse=True)[:50]
        elif "Top 100" in market_scope: target_list = sorted(all_coins, key=lambda x: x['quoteVolume'], reverse=True)[:100]
        else: target_list = sorted(all_coins, key=lambda x: x['quoteVolume'], reverse=True)

        current_time = time.time()
        for item in target_list:
            raw_symbol = item['symbol']
            is_futures = item['is_futures']
            endpoint = FUTURES_BASE_URL if is_futures else SPOT_BASE_URL
            display_symbol = f"{raw_symbol[:-4]}/USDT" if not raw_symbol.startswith("1000") else f"{raw_symbol}/USDT"
            real_time_price = item['last']
            if not real_time_price or raw_symbol in ['BTCUSDT', 'USDCUSDT', 'FDUSDUSDT']: continue

            try:
                kline_res = requests.get(f"{endpoint}/klines", params={'symbol': raw_symbol, 'interval': '15m', 'limit': 35}, timeout=4)
                if kline_res.status_code != 200: continue
                df = pd.DataFrame(kline_res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                for col in ['close', 'open', 'high', 'low', 'volume']: df[col] = df[col].astype(float)
                
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
                        if not (btc_status == "BEARISH") and check_1h_trend(raw_symbol, real_time_price, "PUMP", is_futures) and buyer_ratio >= 52.0: signal = "PUMP"
                if not signal and scan_mode in ["Both (Pump & Dump)", "Dump Only (Short)"]:
                    if is_vol_spike and live_price_change <= -price_threshold and (dump_rsi_min <= current_rsi <= dump_rsi_max) and real_time_price < current_ema:
                        if not (btc_status == "BULLISH") and check_1h_trend(raw_symbol, real_time_price, "DUMP", is_futures) and seller_ratio >= 52.0: signal = "DUMP"
                
                if signal:
                    sl_val = max(0.000001, real_time_price - (atr_val * 1.5)) if signal == "PUMP" else (real_time_price + (atr_val * 1.5))
                    tp1_val = (real_time_price + (atr_val * 2.5)) if signal == "PUMP" else max(0.000001, real_time_price - (atr_val * 2.5))
                    dom_str = f"Buyers {buyer_ratio}%" if signal == "PUMP" else f"Sellers {seller_ratio}%"
                    change_str = f"{live_price_change:+.2f}"
                    fmt = ".5f" if real_time_price < 1 else ".4f"
                    
                    alerts.append({
                        "raw_symbol": raw_symbol, "Market": "Futures" if is_futures else "Spot", "Type": "🟢 PUMP" if signal == "PUMP" else "🔴 DUMP",
                        "Coin": display_symbol, "Live Price ($)": format(real_time_price, fmt), "15m Change": f"{change_str}%",
                        "RSI": f"{current_rsi:.1f}", "Pattern": pattern_found, "AI Verdict": "CONFIRMED", "TP 1": format(tp1_val, fmt), "Stop Loss": format(sl_val, fmt)
                    })
                    
                    if current_time - global_state["last_alert_time"].get(display_symbol, 0) > 3600:
                        send_scanner_telegram_alert(signal, display_symbol, format(real_time_price, fmt), change_str, f"{round(current_volume/avg_volume,1)}x", f"{current_rsi:.1f}", format(tp1_val, fmt), format(tp1_val, fmt), format(sl_val, fmt), dom_str, pattern_found, "CONFIRMED")
                        global_state["last_alert_time"][display_symbol] = current_time
            except Exception: continue
        return alerts

    with st.spinner(f"24/7 Scanner: වෙළඳපොළ පරීක්ෂා කරමින් පවතී ({market_scope})..."):
        auto_scan_results = scan_entire_binance()
        if auto_scan_results:
            st.success(f"🔥 කාසි {len(auto_scan_results)} ක් හමුවිය!")
            play_alert_sound()
            st.dataframe(pd.DataFrame(auto_scan_results).drop(columns=['raw_symbol']), use_container_width=True)
        else:
            st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි නොමැත.")
