import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import time

st.set_page_config(page_title="Crypto Pump Scanner Pro Max (AI Powered)", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_GEMINI_KEY = "AQ.Ab8RN6Kov34e2FAiapWmBpeAtkyAint2-EaxdTwngH8RxeagKQ"

def send_telegram_alert(coin, price, change, volume_spike, rsi_val, tp1, tp2, sl, high_24h, low_24h, buyer_ratio, pattern_name, ai_verdict):
    clean_symbol = coin.replace('/', '_')
    message = (
        f"🚨 *Smart Crypto Pump Alert (AI Analyzed)!*\n\n"
        f"🪙 *Coin:* `{coin}`\n"
        f"🤖 *AI Verdict:* `{ai_verdict}`\n"
        f"🕯️ *Pattern:* `{pattern_name}`\n"
        f"💵 *Entry Price:* `${price}`\n"
        f"📈 *15m Change:* `+{change}%`\n"
        f"📊 *Volume Spike:* `{volume_spike}`\n"
        f"🎯 *RSI (14):* `{rsi_val}`\n"
        f"🐋 *Buyer Dominance:* `{buyer_ratio}%`\n\n"
        f"🎯 *Dynamic ATR Targets:*\n"
        f"  ├ TP 1: `${tp1}`\n"
        f"  └ TP 2: `${tp2}`\n\n"
        f"🛑 *Dynamic ATR Stop Loss:* `${sl}`\n\n"
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

# ================= AI ANALYZER ENGINE =================
def analyze_with_ai(coin, price, change, volume_spike, rsi, pattern, buyer_ratio, btc_status, api_key):
    if not api_key:
        return "⚠️ No API Key", "API Key ලබා දී නොමැත", "Medium"
    
    prompt = f"""
    Act as a professional Crypto Day Trader. Analyze this 15-minute pump setup and decide if it's safe to enter:
    - Coin: {coin}
    - Live Price: ${price}
    - 15m Price Surge: +{change}%
    - Volume Multiplier: {volume_spike}
    - RSI (14): {rsi}
    - Candlestick Pattern: {pattern}
    - Order Book Buyer Dominance: {buyer_ratio}%
    - Overall Market (BTC) Status: {btc_status}

    Respond ONLY in strict JSON format like this (no markdown ticks, no extra text):
    {{"verdict": "STRONG BUY", "confidence": 85, "reason": "brief 1 sentence reason", "risk": "Low"}}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=6)
        if res.status_code == 200:
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            clean_json = raw_text.replace('```json', '').replace('
