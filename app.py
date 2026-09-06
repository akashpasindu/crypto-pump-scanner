import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import time

st.set_page_config(page_title="Crypto Pump Scanner Pro", layout="wide")

# ================= TELEGRAM CONFIG =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"

def send_telegram_alert(coin, price, change, volume_spike, rsi_val, tp1, tp2, sl, high_24h, low_24h):
    clean_symbol = coin.replace('/', '_')
    message = (
        f"🚨 *Smart Crypto Pump Alert!*\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"💵 *Entry Price:* `${price}`\n"
        f"📈 *15m Change:* `+{change}%`\n"
        f"📊 *Volume Spike:* `{volume_spike}`\n"
        f"🎯 *RSI (14):* `{rsi_val}`\n\n"
        f"🎯 *Targets (Take Profit):*\n"
        f"  ├ TP 1 (+2.5%): `${tp1}`\n"
        f"  └ TP 2 (+5.0%): `${tp2}`\n\n"
        f"🛑 *Stop Loss (-1.5%):* `${sl}`\n\n"
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
# ===================================================

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

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

st.title("🚀 Smart Crypto Pump Scanner Pro")

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("📲 Test Telegram Bot"):
        try:
            res = send_telegram_alert(
                "BTC/USDT", "65000.00", "2.50", "2.2x", "58.4", 
                "66625.00", "68250.00", "64025.00", "65500.00", "63200.00"
            )
            if res.status_code == 200:
                st.success("✅ Telegram එකට මැසේජ් එක සාර්ථකව ගියා!")
                play_alert_sound()
            else:
                st.error(f"Telegram Error: {res.text}")
        except Exception as e:
            st.error(f"Error: {e}")

st.write("---")

# Sidebar Settings
st.sidebar.header("Scanner Settings")
enable_btc_filter = st.sidebar.checkbox("🛡️ BTC Market Safety Filter", value=True)
enable_1h_filter = st.sidebar.checkbox("📈 1h Trend (50 EMA) Filter", value=True)
enable_sound = st.sidebar.checkbox("🔔 Play Sound on Alert", value=True)

volume_threshold = st.sidebar.slider("Volume Spike Multiplier", 1.2, 5.0, 1.5)
price_threshold = st.sidebar.slider("අවම මිල වෙනස (%)", 0.5, 10.0, 1.2)
rsi_min = st.sidebar.slider("අවම RSI අගය", 30, 60, 45)
rsi_max = st.sidebar.slider("උපරිම RSI අගය", 65, 85, 75)
limit_pairs = st.sidebar.number_input("පරීක්ෂා කළ යුතු Pairs ගණන", min_value=10, max_value=150, value=50, step=10)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("ස්වයංක්‍රීයව Scan වන්න (Auto-Refresh)", value=False)
refresh_interval = st.sidebar.slider("නැවත Scan වන කාලය (මිනිත්තු)", 1, 10, 2)

# Alert Cooldown Tracking (පැයකට එක් වරක් පමණක් alert යැවීම)
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = {}

BASE_URL = "https://data-api.binance.vision/api/v3"

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
        msg = f"BTC: ${current_btc:,.1f} {'🟢 (Above 20 EMA - Safe)' if is_safe else '🔴 (Below 20 EMA - Market Dumping Risk)'}"
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

def scan_market():
    # 1. BTC Safety Filter
    btc_safe, btc_msg = check_btc_trend()
    if enable_btc_filter:
        if not btc_safe:
            st.warning(f"⚠️ **Scan එක අත්හිටුවන ලදී:** {btc_msg}. වෙළඳපොළ පහත බසින බැවින් Alerts නිකුත් නොකෙරේ.")
            return []
        else:
            st.info(f"🛡️ {btc_msg}")

    alerts = []
    res = requests.get(f"{BASE_URL}/ticker/24hr", timeout=10)
    if res.status_code != 200:
        st.error("Binance Data API වෙත සම්බන්ධ වීමට නොහැකි විය.")
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
    progress_bar = st.progress(0)
    current_time = time.time()
    
    for i, item in enumerate(sorted_pairs):
        raw_symbol = item['symbol']
        display_symbol = f"{raw_symbol[:-4]}/USDT"
        real_time_price = item['last']
        
        if not real_time_price or raw_symbol == 'BTCUSDT':
            continue
            
        try:
            # 15m Klines
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
            
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            rsi_series = calculate_rsi(df['close'], period=14)
            ema_series = df['close'].ewm(span=20, adjust=False).mean()
            
            current_rsi = rsi_series.iloc[-1]
            current_ema = ema_series.iloc[-1]
            
            avg_volume = df['volume'][:-1].mean()
            current_volume = df['volume'].iloc[-1]
            
            open_price = df['open'].iloc[-1]
            live_price_change = ((real_time_price - open_price) / open_price) * 100
            
            # 15m Conditions
            if (
                current_volume > (avg_volume * volume_threshold)
                and live_price_change >= price_threshold
                and (rsi_min <= current_rsi <= rsi_max)
                and real_time_price > current_ema
            ):
                # 2. 1h Trend Confirmation (50 EMA)
                if enable_1h_filter and not check_1h_trend(raw_symbol, real_time_price):
                    continue

                tp1_val = real_time_price * 1.025
                tp2_val = real_time_price * 1.050
                sl_val = real_time_price * 0.985
                
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
                    "Live Price ($)": price_str,
                    "15m Change (%)": f"+{change_str}%",
                    "RSI (14)": rsi_str,
                    "Target 1 (+2.5%)": tp1_str,
                    "Stop Loss (-1.5%)": sl_str,
                    "Volume Spike": spike_str
                })
                
                # Cooldown Check: පසුගිය විනාඩි 60 (තත්පර 3600) තුළ alert එකක් ගොස් නොමැති නම් පමණක් යැවීම
                last_sent = st.session_state.last_alert_time.get(display_symbol, 0)
                if current_time - last_sent > 3600:
                    send_telegram_alert(
                        display_symbol, price_str, change_str, spike_str, rsi_str, 
                        tp1_str, tp2_str, sl_str, high_str, low_str
                    )
                    st.session_state.last_alert_time[display_symbol] = current_time
                    
        except Exception:
            continue
        finally:
            progress_bar.progress((i + 1) / len(sorted_pairs))
            time.sleep(0.02)
            
    return alerts

if st.button("Manual Scan 🔍") or auto_refresh:
    with st.spinner("දත්ත සහ 1h Trend විශ්ලේෂණය කරමින් පවතී..."):
        results = scan_market()
        if results:
            st.success(f"කාසි {len(results)} ක් හමුවිය!")
            if enable_sound:
                play_alert_sound()

            df_display = pd.DataFrame(results).drop(columns=['raw_symbol'])
            st.dataframe(df_display, use_container_width=True)
            
            st.markdown("### 📊 Live TradingView Charts")
            for coin_data in results:
                st.write(f"**{coin_data['Coin']} (15m Timeframe)**")
                render_tradingview_widget(coin_data['raw_symbol'])
        elif results is not None and len(results) == 0:
            st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි හමු නොවීය.")

if auto_refresh:
    time.sleep(refresh_interval * 60)
    st.rerun()
