import streamlit as st
import ccxt
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
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass
# ===================================================

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

st.title("🚀 Smart Crypto Pump Scanner Pro (Target Levels + RSI)")
st.write("Binance Spot Market එකේ Volume Spikes සහ නිවැරදි Entry/Exit Targets නිරීක්ෂණය.")

exchange = ccxt.binance({'enableRateLimit': True})

# Sidebar Settings
st.sidebar.header("Scanner Settings")
volume_threshold = st.sidebar.slider("Volume Spike Multiplier", 1.2, 5.0, 1.5)
price_threshold = st.sidebar.slider("අවම මිල වෙනස (%)", 0.5, 10.0, 1.2)

rsi_min = st.sidebar.slider("අවම RSI අගය", 30, 60, 45)
rsi_max = st.sidebar.slider("උපරිම RSI අගය", 65, 85, 75)

limit_pairs = st.sidebar.number_input("පරීක්ෂා කළ යුතු Pairs ගණන", min_value=10, max_value=100, value=50)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("ස්වයංක්‍රීයව Scan වන්න (Auto-Refresh)", value=False)
refresh_interval = st.sidebar.slider("නැවත Scan වන කාලය (මිනිත්තු)", 1, 10, 2)

if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()

def scan_market():
    markets = exchange.load_markets()
    all_tickers = exchange.fetch_tickers()
    
    active_usdt_pairs = []
    for symbol, ticker in all_tickers.items():
        if (
            symbol.endswith('/USDT') 
            and symbol in markets 
            and markets[symbol].get('spot', False) 
            and markets[symbol].get('active', True)
            and ticker.get('quoteVolume') is not None
        ):
            active_usdt_pairs.append({
                'symbol': symbol,
                'quoteVolume': ticker['quoteVolume'],
                'last': ticker.get('last'),
                'high': ticker.get('high'),
                'low': ticker.get('low')
            })
            
    sorted_pairs = sorted(active_usdt_pairs, key=lambda x: x['quoteVolume'], reverse=True)[:limit_pairs]
    
    alerts = []
    progress_bar = st.progress(0)
    
    for i, item in enumerate(sorted_pairs):
        symbol = item['symbol']
        real_time_price = item['last']
        
        if not real_time_price:
            continue
            
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=40)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            rsi_series = calculate_rsi(df['close'], period=14)
            ema_series = df['close'].ewm(span=20, adjust=False).mean()
            
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
                # Target සහ Stop Loss ගණනය කිරීම
                tp1_val = real_time_price * 1.025
                tp2_val = real_time_price * 1.050
                sl_val = real_time_price * 0.985
                
                fmt = ".4f" if real_time_price >= 1 else ".6f"
                price_str = format(real_time_price, fmt)
                tp1_str = format(tp1_val, fmt)
                tp2_str = format(tp2_val, fmt)
                sl_str = format(sl_val, fmt)
                
                high_str = format(item['high'], fmt) if item['high'] else "N/A"
                low_str = format(item['low'], fmt) if item['low'] else "N/A"
                
                change_str = f"{live_price_change:.2f}"
                spike_str = f"{round(current_volume / avg_volume, 1)}x"
                rsi_str = f"{current_rsi:.1f}"
                
                alerts.append({
                    "Coin": symbol,
                    "Live Price ($)": price_str,
                    "15m Change (%)": f"+{change_str}%",
                    "RSI (14)": rsi_str,
                    "Target 1 (+2.5%)": tp1_str,
                    "Stop Loss (-1.5%)": sl_str,
                    "Volume Spike": spike_str
                })
                
                if symbol not in st.session_state.sent_alerts:
                    send_telegram_alert(
                        symbol, price_str, change_str, spike_str, rsi_str, 
                        tp1_str, tp2_str, sl_str, high_str, low_str
                    )
                    st.session_state.sent_alerts.add(symbol)
                    
        except Exception:
            continue
        finally:
            progress_bar.progress((i + 1) / len(sorted_pairs))
            
    return pd.DataFrame(alerts)

# Sidebar Test Button
if st.sidebar.button("Test Telegram Message"):
    send_telegram_alert("BTC/USDT", "65000.00", "2.50", "2.2x", "58.4", "66625.00", "68250.00", "64025.00", "65500.00", "63200.00")
    st.sidebar.success("Test Alert එක Telegram වෙත යවන ලදී!")

if st.button("Manual Scan 🔍") or auto_refresh:
    with st.spinner("දත්ත සහ Target Levels විශ්ලේෂණය කරමින් පවතී..."):
        results = scan_market()
        if not results.empty:
            st.success(f"කාසි {len(results)} ක් හමුවිය! (Targets සමග Telegram Alert යවන ලදී)")
            st.dataframe(results, use_container_width=True)
        else:
            st.info("මේ මොහොතේ කොන්දේසි සපුරාලූ කාසි හමු නොවීය.")

if auto_refresh:
    time.sleep(refresh_interval * 60)
    st.rerun()
