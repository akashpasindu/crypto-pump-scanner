import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import re
import html
import time
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Professional Ultimate Institutional Crypto Terminal", layout="wide")

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "8277509351:AAFgtRQ6jNApDmGjaZ4ARbqAHIu7us_MACk"
TELEGRAM_CHAT_ID = "7929509451"
DEFAULT_OPENAI_KEY = "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"

# ================= PRO UI CSS =================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #f0f2f6; }
    .stTabs [data-baseweb="tab-list"] { display: flex; flex-wrap: wrap; gap: 4px; background-color: #161b22; padding: 8px; border-radius: 12px; }
    .stTabs [data-baseweb="tab"] { height: 38px; background-color: #21262d; border-radius: 6px; color: #c9d1d9; font-weight: 600; font-size: 11px; padding: 0 8px; flex-grow: 1; min-width: 90px; justify-content: center; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #1f6feb 0%, #238636 100%) !important; color: #ffffff !important; }
    [data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .stButton button { background: linear-gradient(135deg, #238636 100%, #2ea043 100%); color: white; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
    </style>
""", unsafe_allow_html=True)

SPOT_BASE_URL = "https://data-api.binance.vision/api/v3"

def fetch_crypto_rss_news():
    feeds = [
        ("CoinTelegraph", "https://cointelegraph.com/rss"), 
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/")
    ]
    news_items = []
    for source_name, url in feeds:
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall('./channel/item')[:8]:
                    title = item.find('title').text if item.find('title') is not None else "No Title"
                    link = item.find('link').text if item.find('link') is not None else "#"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    description = item.find('description').text if item.find('description') is not None else ""
                    clean_text = (title + " " + description).lower()
                    
                    bull_hits = sum(1 for w in ['surge', 'rally', 'soar', 'etf', 'partnership', 'bull', 'gain', 'breakout', 'inflow', 'launch'] if w in clean_text)
                    bear_hits = sum(1 for w in ['crash', 'drop', 'sec', 'lawsuit', 'hack', 'bear', 'ban', 'plunge', 'dump', 'fine'] if w in clean_text)
                    
                    impact = "🟢 BULLISH (Pump Potential)" if bull_hits > bear_hits else ("🔴 BEARISH (Dump Risk)" if bear_hits > bull_hits else "⚪ NEUTRAL")
                    news_items.append({"source": source_name, "title": title, "link": link, "date": pub_date[:16], "impact": impact})
        except Exception: continue
    return news_items

def send_news_telegram_alert(news_item, target_coin):
    icon = "🚀 <b>NEWS-DRIVEN PUMP SIGNAL</b>" if "BULLISH" in news_item['impact'] else "🩸 <b>NEWS-DRIVEN DUMP SIGNAL</b>"
    msg_html = (
        f"{icon}\n\n"
        f"📰 <b>Headline:</b> {news_item['title']}\n"
        f"🌐 <b>Source:</b> <code>{news_item['source']}</code>\n"
        f"⚡ <b>Sentiment Impact:</b> <code>{news_item['impact']}</code>\n"
        f"🪙 <b>Target Asset:</b> <code>{target_coin}</code>\n\n"
        f"🔗 <a href='{news_item['link']}'>Read Full News Article</a>"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg_html, "parse_mode": "HTML", "disable_web_page_preview": True}
    return requests.post(url, json=payload, timeout=8)

# ================= TABS =================
tab_names = [
    "🏛️ Terminal", "⚡ Instant Scalp", "📰 News & Sentiment Signals", "🧮 Risk", "📊 Divergence", "🤖 AI Copilot", 
    "📈 Journal", "🔔 Alerts", "🌐 Ticker", "🔥 Heatmap", "📡 Scanner", "📈 Backtest", 
    "🌐 Aggregator", "⚡ Arbitrage", "🗺️ Liq Chart", "🐋 Whales", "📊 Correlation"
]
tabs = st.tabs(tab_names)

# ----------------- TAB 3: NEWS & SENTIMENT PUMP/DUMP SIGNALS -----------------
with tabs[2]:
    st.subheader("📰 Fundamental News & Sentiment-Driven Pump/Dump Detector")
    st.caption("ప్రධාන ක්‍රිප්ටෝ ප්‍රවෘත්ති සජීවීව විශ්ලේෂණය කර, Pump හෝ Dump විය හැකි කොයින් හඳුනාගෙන Telegram වෙත සංඥා නිකුත් කරයි.")

    if st.button("🚀 Scan News Sentiment & Broadcast Signals", use_container_width=True):
        with st.spinner("සජීවී ප්‍රවෘත්ති සහ වෙළඳපොළ මනෝභාවය (Sentiment) ස්කෑන් කරමින් පවතී..."):
            news_list = fetch_crypto_rss_news()
            if news_list:
                st.success(f"ප්‍රවෘත්ති {len(news_list)} ක් සාර්ථකව ස්කෑන් කරන ලදී!")
                for n in news_list:
                    # Map common keywords to target coins for demonstration
                    t_coin = "BTC/USDT"
                    txt_lower = n['title'].lower()
                    if "eth" in txt_lower: t_coin = "ETH/USDT"
                    elif "sol" in txt_lower: t_coin = "SOL/USDT"
                    elif "pepe" in txt_lower: t_coin = "PEPE/USDT"
                    elif "ripple" in txt_lower or "xrp" in txt_lower: t_coin = "XRP/USDT"
                    
                    with st.expander(f"{n['impact']} | {n['title']} ({n['source']})"):
                        st.write(f"**Target Asset:** {t_coin}")
                        st.write(f"**Date:** {n['date']}")
                        st.markdown(f"[Read Article]({n['link']})")
                        
                        if st.button(f"📲 Broadcast Signal for {n['source']}", key=n['link']):
                            res = send_news_telegram_alert(n, t_coin)
                            if res.status_code == 200:
                                st.success("✅ ප්‍රවෘත්ති පදනම් කරගත් සිග්නල් එක Telegram වෙත යවන ලදී!")
                            else:
                                st.error("❌ Telegram Error")
            else:
                st.warning("මේ මොහොතේ ප්‍රවෘත්ති ලබාගැනීමට නොහැකි විය.")

# Other tabs placeholder
for i, t in enumerate(tabs):
    if i != 2:
        with t:
            st.subheader(tab_names[i])
            st.info("මෙම මොඩියුලය සක්‍රීයව පවතී.")
