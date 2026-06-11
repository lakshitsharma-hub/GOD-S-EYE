import os
import time
import requests
import ccxt
import pandas as pd
import numpy as np
from flask import Flask
from threading import Thread

# ==============================================================================
# █ FLASK SERVER FOR RENDER ANTI-SLEEP PINGING
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "GOD'S EYE Enterprise Engine is running active 24/7."

def run_flask():
    # Render binds to port 10000 or the PORT environment variable by default
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# █ CONFIGURATION & SECURE CREDENTIALS
# ==============================================================================
# Best practice: Put these in Render Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_PREMIUM_CHANNEL_ID_HERE")

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'} # Spot/Futures trading context alignment
})

SYMBOL = 'BTC/USDT'
TIMEFRAME = '4h'
LEFT_BARS = 5
RIGHT_BARS = 5

# Global state tracker for Order Blocks (State Memory Matrix)
order_blocks = [] # List of dicts holding order block structural data
current_trend = "NEUTRAL"
last_signal_time = None

# ==============================================================================
# █ CORE MATHEMATICAL SIGNAL LOGIC
# ==============================================================================
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Delivery Failed: {e}")

def check_market_signals():
    global current_trend, order_blocks, last_signal_time
    
    try:
        # Fetch OHLCV candles
        bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        length = len(df)
        if length < 20:
            return

        # Check for Pivot High/Low (Strict 5-Bar Filter Matching Pine Script)
        idx = length - 1 - RIGHT_BARS
        if idx < LEFT_BARS:
            return
            
        current_candle_time = df.iloc[idx]['timestamp']
        
        # Math checks for structural swing execution
        is_pivot_high = True
        is_pivot_low = True
        
        for i in range(1, LEFT_BARS + 1):
            if df.iloc[idx]['high'] < df.iloc[idx - i]['high'] or df.iloc[idx]['low'] > df.iloc[idx - i]['low']:
                if df.iloc[idx]['high'] < df.iloc[idx - i]['high']: is_pivot_high = False
                if df.iloc[idx]['low'] > df.iloc[idx - i]['low']: is_pivot_low = False
        for i in range(1, RIGHT_BARS + 1):
            if df.iloc[idx]['high'] < df.iloc[idx + i]['high'] or df.iloc[idx]['low'] > df.iloc[idx + i]['low']:
                if df.iloc[idx]['high'] < df.iloc[idx + i]['high']: is_pivot_high = False
                if df.iloc[idx]['low'] > df.iloc[idx + i]['low']: is_pivot_low = False

        # Structural breakouts calculation (BOS/CHoCH mapping)
        latest_close = df.iloc[-1]['close']
        latest_open = df.iloc[-1]['open']
        latest_high = df.iloc[-1]['high']
        latest_low = df.iloc[-1]['low']
        
        # Dummy zone bounds generation logic based on active pivots to emulate array push
        if is_pivot_high:
            order_blocks.append({
                'top': df.iloc[idx]['high'],
                'bottom': df.iloc[idx]['low'],
                'is_bullish': False,
                'timestamp': current_candle_time
            })
        if is_pivot_low:
            order_blocks.append({
                'top': df.iloc[idx]['high'],
                'bottom': df.iloc[idx]['low'],
                'is_bullish': True,
                'timestamp': current_candle_time
            })

        # Process active Order Block intersections and auto-mitigation loops
        buy_triggered = False
        sell_triggered = False
        
        for ob in order_blocks[:]:
            if ob['is_bullish']:
                # Zone Entry Check
                if latest_low <= ob['top'] and latest_low >= ob['bottom']:
                    if current_trend == "BULLISH" or current_trend == "NEUTRAL":
                        if latest_close > latest_open: # Bullish confirmation candle close
                            buy_triggered = True
                    order_blocks.remove(ob) # Mitigated!
            else:
                if latest_high >= ob['bottom'] and latest_high <= ob['top']:
                    if current_trend == "BEARISH" or current_trend == "NEUTRAL":
                        if latest_close < latest_open: # Bearish confirmation candle close
                            sell_triggered = True
                    order_blocks.remove(ob) # Mitigated!

        # Trend setting simulation for raw mapping context
        if is_pivot_high: current_trend = "BEARISH"
        if is_pivot_low: current_trend = "BULLISH"

        # Fire alerts ensuring no multi-firing on a single closed timestamp bar
        if (buy_triggered or sell_triggered) and last_signal_time != current_candle_time:
            last_signal_time = current_candle_time
            if buy_triggered:
                msg = f"🟢 *GOD'S EYE BUY TRIGGERED!*\nAsset: {SYMBOL}\nPrice: {latest_close}\nTimeframe: {TIMEFRAME}"
                send_telegram_alert(msg)
            elif sell_triggered:
                msg = f"🔴 *GOD'S EYE SELL TRIGGERED!*\nAsset: {SYMBOL}\nPrice: {latest_close}\nTimeframe: {TIMEFRAME}"
                send_telegram_alert(msg)
                
    except Exception as e:
        print(f"Execution Error loop: {e}")

# ==============================================================================
# █ ENGINE MAIN CONTROL LOOP
# ==============================================================================
def engine_loop():
    while True:
        check_market_signals()
        time.sleep(60) # Scan every 1 minute for close updates

if __name__ == "__main__":
    print("Initializing Flask server thread...")
    t = Thread(target=run_flask)
    t.start()
    
    print("Launching Engine core automated loop...")
    engine_loop()
