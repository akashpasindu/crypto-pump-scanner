import streamlit as st
import ccxt
import pandas as pd
import requests
import time

st.set_page_config(page_title="Crypto Pump Scanner Pro", layout="wide")

# ================= TELEGRAM CONFIG =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"

def send_telegram_alert(coin, price, change, volume_spike, rsi_val):
    clean_symbol = coin.replace('/', '_')
    message = (
        f"🚨 *Smart Crypto Pump Alert!*\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"💵 *Price:* `${price}`\n"
        f"📈 *15m Change:* `+{change}%`\n"
        f"📊 *Volume Spike:* `{volume_spike}`\n"
        f"🎯 *RSI (14):* `{rsi_val}`\n\n"
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

# බාහිර ලයිබ්‍රරි නොමැතිව RSI ගණනය කිරීමේ ශ්‍රිතය (Native Pandas)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

st.title("🚀 Smart Crypto Pump Scanner (Native RSI + Volume)")
st.write("False Breakouts අවම කරමින් RSI සහ Volume Spike එකවර පරීක්ෂා කිරීම.")

exchange = ccxt.binance({'enableRateLimit': True})

# Sidebar Settings
st.sidebar.header("Scanner Settings")
volume_threshold = st.sidebar.slider("Volume Spike Multiplier", 1.2, 5.0, 1.5)
price_threshold = st.sidebar.slider("අවම මිල වෙනස (%)", 0.5, 10.0, 1.2)

# RSI Controls
rsi_min = st.sidebar.slider("අවම RSI අගය", 30, 60, 45)
rsi_max = st.sidebar.slider("උපරිම RSI අගය (Overbought නොවීමට)", 65, 85, 75)

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
                'last': ticker.get('last')
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
            # කෙන්ඩල් 40ක් ලබාගැනීම
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=40)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # RSI සහ 20 EMA ගණනය
            rsi_series = calculate_rsi(df['close'], period=14)
            ema_series = df['close'].ewm(span=20, adjust=False).mean()
            
            current_rsi = rsi_series.iloc[-1]
            current_ema = ema_series.iloc[-1]
            
            avg_volume = df['volume'][:-1].mean()
            current_volume = df['volume'].iloc[-1]
            
            open_price = df['open'].iloc[-1]
            live_price_change = ((real_time_price - open_price) / open_price) * 100
            
            # කොන්දේසි පරීක්ෂාව
            if (
                current_volume > (avg_volume * volume_threshold)
                and live_price_change >= price_threshold
                and (rsi_min <= current_rsi <= rsi_max)
                and real_time_price > current_ema
            ):
                price_str = f"{real_time_price:.4f}" if real_time_price >= 1 else f"{real_time_price:.6f}"
                change_str = f"{live_price_change:.2f}"
                spike_str = f"{round(current_volume / avg_volume, 1)}x"
                rsi_str = f"{current_rsi:.1f}"
                
                alerts.append({
                    "Coin": symbol,
                    "Live Price ($)": price_str,
                    "15m Change (%)": f"+{change_str}%",
                    "RSI (14)": rsi_str,
                    "Volume Spike": spike_str,
                    "24h Vol (USDT)": f"${item['quoteVolume']:,.0f}",
                    "Status": "✅ High Momentum"
                })
                
                if symbol not in st.session_state.sent_alerts:
                    send_telegram_alert(symbol, price_str, change_str, spike_str, rsi_str)
                    st.session_state.sent_alerts.add(symbol)
                    
        except Exception:
            continue
        finally:
            progress_bar.progress((i + 1) / len(sorted_pairs))
            
    return pd.DataFrame(alerts)

# ක්‍රියාත්මක කිරීම
if st.button("Manual Scan 🔍") or auto_refresh:
    with st.spinner("RSI, EMA සහ Volume දත්ත පරීක්ෂා කරමින් පවතී..."):
        results = scan_market()
        if not results.empty:
            st.success(f"හොඳ තත්ත්වයේ කාසි {len(results)} ක් හමුවිය! (Telegram එකට Alert යවන ලදී)")
            st.dataframe(results, use_container_width=True)
        else:
            st.info("RSI සහ Volume කොන්දේසි දෙකම සපුරාලූ කාසි හමු නොවීය. Settings වලින් අගයන් මදක් ලිහිල් කර උත්සාහ කරන්න.")

if auto_refresh:
    time.sleep(refresh_interval * 60)
    st.rerun()