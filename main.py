import os
import time
import requests
import ccxt
from flask import Flask
from threading import Thread
from datetime import datetime, timezone

app = Flask('')

@app.route('/')
def home():
    return "GOD'S EYE Enterprise Dual-Engine is active 24/7."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# 🔐 SECURE CREDENTIALS ARCHITECTURE
# ==============================================================================
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
TIMEFRAME = '4h'
LEFT_BARS = 5
RIGHT_BARS = 5

market_states = {
    symbol: {
        'order_blocks': [],
        'current_trend': 'NEUTRAL',
        'last_signal_time': None
    } for symbol in SYMBOLS
}

# ==============================================================================
# 🗣️ BROADCAST & LEDGER JOURNAL CONTROLLERS
# ==============================================================================
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Delivery Failed: {e}")

def push_signal_to_notion_journal(asset, signal_type, entry_price):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("[-] Skipping Notion log: Credentials missing in Environment.")
        return False
        
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Asset": {"title": [{"text": {"content": asset}}]},
            "Signal": {"rich_text": [{"text": {"content": signal_type}}]},
            "Entry": {"number": float(entry_price)},
            "Status": {"select": {"name": "Active"}},
            "Result": {"rich_text": [{"text": {"content": "Monitoring Live Crypto Framework..."}}]}
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[-] Notion Journal Logging Failed: {e}")
        return False

def send_deployment_success():
    coins_str = ", ".join([s.split('/')[0] for s in SYMBOLS])
    startup_msg = (
        "⚡ *GOD'S EYE DUAL-LEDGER ENGINE ONLINE*\n"
        "───────────────────────\n"
        "🌐 *Status:* Successfully Deployed on Cloud\n"
        f"📊 *Timeframe:* {TIMEFRAME}\n"
        f"📓 *Journal:* Notion Public Ledger Connected\n"
        f"🎯 *Scanning Assets:* [{coins_str}]\n"
        "───────────────────────\n"
        "📡 _Tracking BUY & SELL institutional zones with automated audit logs..._"
    )
    send_telegram_alert(startup_msg)

# ==============================================================================
# 🧠 CORE MATHEMATICAL ENGINE (DUAL EXECUTION LAYER)
# ==============================================================================
def check_market_signals(symbol):
    state = market_states[symbol]
    
    try:
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        length = len(bars)
        if length < 20:
            return

        idx = length - 1 - RIGHT_BARS
        if idx < LEFT_BARS:
            return
            
        current_candle_time = bars[idx][0]
        pivot_high_val = bars[idx][2]
        pivot_low_val = bars[idx][3]
        
        is_pivot_high = True
        is_pivot_low = True
        
        for i in range(1, LEFT_BARS + 1):
            if pivot_high_val < bars[idx - i][2]: is_pivot_high = False
            if pivot_low_val > bars[idx - i][3]: is_pivot_low = False
        for i in range(1, RIGHT_BARS + 1):
            if pivot_high_val < bars[idx + i][2]: is_pivot_high = False
            if pivot_low_val > bars[idx + i][3]: is_pivot_low = False

        latest_open = bars[-1][1]
        latest_high = bars[-1][2]
        latest_low = bars[-1][3]
        latest_close = bars[-1][4]
        
        if is_pivot_high:
            state['order_blocks'].append({
                'top': bars[idx][2],
                'bottom': bars[idx][3],
                'is_bullish': False,
                'timestamp': current_candle_time
            })
        if is_pivot_low:
            state['order_blocks'].append({
                'top': bars[idx][2],
                'bottom': bars[idx][3],
                'is_bullish': True,
                'timestamp': current_candle_time
            })

        buy_triggered = False
        sell_triggered = False
        
        for ob in state['order_blocks'][:]:
            if ob['is_bullish']:
                if latest_low <= ob['top'] and latest_low >= ob['bottom']:
                    if state['current_trend'] in ["BULLISH", "NEUTRAL"]:
                        if latest_close > latest_open:
                            buy_triggered = True
                    state['order_blocks'].remove(ob)
            else:
                if latest_high >= ob['bottom'] and latest_high <= ob['top']:
                    if state['current_trend'] in ["BEARISH", "NEUTRAL"]:
                        if latest_close < latest_open:
                            sell_triggered = True
                    state['order_blocks'].remove(ob)

        if is_pivot_high: state['current_trend'] = "BEARISH"
        if is_pivot_low: state['current_trend'] = "BULLISH"

        if (buy_triggered or sell_triggered) and state['last_signal_time'] != current_candle_time:
            state['last_signal_time'] = current_candle_time
            coin_name = symbol.split('/')[0]
            
            if buy_triggered:
                msg = f"🟢 *GOD'S EYE BUY TRIGGERED!*\nAsset: #{coin_name}\nPrice: {latest_close}\nTimeframe: {TIMEFRAME}\n📌 _Logged to Notion Journal_"
                push_signal_to_notion_journal(coin_name, "LONG [OB-MITIGATION]", latest_close)
                send_telegram_alert(msg)
                
            elif sell_triggered:
                msg = f"🔴 *GOD'S EYE SELL TRIGGERED!*\nAsset: #{coin_name}\nPrice: {latest_close}\nTimeframe: {TIMEFRAME}\n📌 _Logged to Notion Journal_"
                push_signal_to_notion_journal(coin_name, "SHORT [OB-MITIGATION]", latest_close)
                send_telegram_alert(msg)
                
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")

def engine_loop():
    send_deployment_success()
    while True:
        for symbol in SYMBOLS:
            check_market_signals(symbol)
            time.sleep(2)
        time.sleep(60)

if __name__ == "__main__":
    print("Initializing Flask server thread...")
    t = Thread(target=run_flask)
    t.start()
    
    print("Launching Integrated Multi-Asset Dual-Ledger loop...")
    engine_loop()
