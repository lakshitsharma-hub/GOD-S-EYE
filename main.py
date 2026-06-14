import os
import time
import requests
import ccxt
import hmac
import hashlib
import base64
import urllib.parse
import secrets
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timezone
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "GOD'S EYE Omni-Channel Enterprise Engine [V10.0 FVG Master] is active 24/7."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# 🔐 SECURE MULTI-CREDENTIALS ARCHITECTURE
# ==============================================================================
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOT/USDT', 'LINK/USDT', 'BNB/USDT', 'DOGE/USDT', 'AVAX/USDT'
]

# 🔥 V1 STRATEGY PARAMS
TIMEFRAME = '1h'
HARD_SL_PCT = 0.065
TRAILING_START_PCT = 0.040
TRAILING_STEP_PCT = 0.010
TIME_BAILOUT_HOURS = 12
TIME_BAILOUT_LOSS_PCT = -0.025

LEDGER_FILE = "signals_logged.txt"

# V10 Telemetry State Framework
market_states = {
    symbol: {
        'active_trade': None  
        # Dict format: {'dir': STR, 'entry': FLT, 'sl': FLT, 'max_price': FLT, 'min_price': FLT, 'trailing_active': BOOL, 'open_time': DATETIME}
    } for symbol in SYMBOLS
}

# ==============================================================================
# 💾 FLAT-FILE LEDGER DE-DUPLICATION ENGINE
# ==============================================================================
def is_signal_logged(signal_id):
    if not os.path.exists(LEDGER_FILE): return False
    try:
        with open(LEDGER_FILE, 'r') as f:
            return signal_id in f.read().splitlines()
    except: return False

def append_to_ledger(signal_id):
    try:
        with open(LEDGER_FILE, 'a') as f:
            f.write(f"{signal_id}\n")
    except: pass

# ==============================================================================
# 🐦 DIRECT X (TWITTER) OAUTH 1.0A HANDLER
# ==============================================================================
def post_to_x_platform(tweet_text):
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]): return
    url = "https://api.twitter.com/2/tweets"
    method = "POST"
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    
    oauth_params = {
        "oauth_consumer_key": X_API_KEY, "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": timestamp,
        "oauth_token": X_ACCESS_TOKEN, "oauth_version": "1.0"
    }
    
    combined_params = oauth_params.copy()
    encoded_params = {urllib.parse.quote(k, safe=''): urllib.parse.quote(v, safe='') for k, v in combined_params.items()}
    sorted_params = sorted(encoded_params.items())
    param_string = "&".join([f"{k}={v}" for k, v in sorted_params])
    
    base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    signing_key = f"{urllib.parse.quote(X_API_SECRET, safe='')}&{urllib.parse.quote(X_ACCESS_SECRET, safe='')}"
    
    signature = hmac.new(signing_key.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha1)
    oauth_params["oauth_signature"] = base64.b64encode(signature.digest()).decode('utf-8')
    
    auth_header_parts = [f'{urllib.parse.quote(k)}="{urllib.parse.quote(v)}"' for k, v in oauth_params.items()]
    headers = {"Authorization": "OAuth " + ", ".join(auth_header_parts), "Content-Type": "application/json"}
    
    try: requests.post(url, headers=headers, json={"text": tweet_text}, timeout=10)
    except: pass

# ==============================================================================
# 📢 DISTRIBUTION CORES
# ==============================================================================
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def push_signal_to_notion_journal(asset, signal_type, entry_price, sl, status="Active"):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: return False
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Asset": {"title": [{"text": {"content": asset}}]},
            "Signal": {"rich_text": [{"text": {"content": signal_type}}]},
            "Entry": {"number": float(entry_price)},
            "Stop Loss": {"number": float(sl)},
            "Status": {"select": {"name": status}}
        }
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
        return True
    except: return False

def send_deployment_success():
    coins_str = ", ".join([s.split('/')[0] for s in SYMBOLS])
    startup_msg = (
        "⚡ *GOD'S EYE V10.0 [FVG MASTER] ONLINE*\n"
        "───────────────────────\n"
        "🌐 *Status:* Active & Guarded\n"
        f"📊 *Timeframe:* {TIMEFRAME}\n"
        "🔒 *Risk:* 6.5% Hard SL | +4% Trailing Start\n"
        "⏱️ *Bailout:* 12H Dead Momentum Shield\n"
        "───────────────────────\n"
        f"📡 _Scanning Assets: [{coins_str}]_"
    )
    send_telegram_alert(startup_msg)

# ==============================================================================
# 🧠 V1 CORE MATHEMATICAL ENGINE (FVG + EMA + ADX)
# ==============================================================================
def check_market_signals(symbol):
    state = market_states[symbol]
    coin_name = symbol.split('/')[0]
    
    try:
        # Fetch current price for active trade management
        ticker = exchange.fetch_ticker(symbol)
        last_price = ticker['last']
        now_utc = datetime.now(timezone.utc)
        
        # 🟢 ACTIVE TRADE LIFECYCLE MANAGEMENT
        if state['active_trade'] is not None:
            trade = state['active_trade']
            time_open_hours = (now_utc - trade['open_time']).total_seconds() / 3600
            
            if trade['dir'] == "LONG":
                trade['max_price'] = max(trade['max_price'], last_price)
                current_profit_pct = (last_price - trade['entry']) / trade['entry']
                
                # 1. Time Bailout Rule
                if time_open_hours >= TIME_BAILOUT_HOURS and current_profit_pct <= TIME_BAILOUT_LOSS_PCT:
                    send_telegram_alert(f"⏱️ *TIME BAILOUT TRIGGERED:* #{coin_name} closed at {last_price:.4f} (Dead Momentum)")
                    push_signal_to_notion_journal(coin_name, "LONG [TIME BAILOUT]", trade['entry'], trade['sl'], "Closed")
                    state['active_trade'] = None
                    return
                
                # 2. Trailing Stop Logic
                if current_profit_pct >= TRAILING_START_PCT:
                    trade['trailing_active'] = True
                    new_sl = trade['max_price'] * (1 - TRAILING_STEP_PCT)
                    if new_sl > trade['sl']:
                        trade['sl'] = new_sl # Update SL upwards
                        
                # 3. Hit Stoploss (Hard or Trailing)
                if last_price <= trade['sl']:
                    status = "Trailing Stop" if trade['trailing_active'] else "Hard Stoploss"
                    profit_str = f"+{(current_profit_pct*100):.2f}%" if current_profit_pct > 0 else f"{(current_profit_pct*100):.2f}%"
                    send_telegram_alert(f"🏁 *TRADE CLOSED:* #{coin_name} hit {status} at {last_price:.4f}\n💰 *P&L:* {profit_str}")
                    push_signal_to_notion_journal(coin_name, f"LONG [{status.upper()}]", trade['entry'], trade['sl'], "Closed")
                    state['active_trade'] = None
                    return
                    
            elif trade['dir'] == "SHORT":
                trade['min_price'] = min(trade['min_price'], last_price)
                current_profit_pct = (trade['entry'] - last_price) / trade['entry']
                
                # 1. Time Bailout Rule
                if time_open_hours >= TIME_BAILOUT_HOURS and current_profit_pct <= TIME_BAILOUT_LOSS_PCT:
                    send_telegram_alert(f"⏱️ *TIME BAILOUT TRIGGERED:* #{coin_name} closed at {last_price:.4f} (Dead Momentum)")
                    push_signal_to_notion_journal(coin_name, "SHORT [TIME BAILOUT]", trade['entry'], trade['sl'], "Closed")
                    state['active_trade'] = None
                    return
                
                # 2. Trailing Stop Logic
                if current_profit_pct >= TRAILING_START_PCT:
                    trade['trailing_active'] = True
                    new_sl = trade['min_price'] * (1 + TRAILING_STEP_PCT)
                    if new_sl < trade['sl']:
                        trade['sl'] = new_sl # Update SL downwards
                        
                # 3. Hit Stoploss (Hard or Trailing)
                if last_price >= trade['sl']:
                    status = "Trailing Stop" if trade['trailing_active'] else "Hard Stoploss"
                    profit_str = f"+{(current_profit_pct*100):.2f}%" if current_profit_pct > 0 else f"{(current_profit_pct*100):.2f}%"
                    send_telegram_alert(f"🏁 *TRADE CLOSED:* #{coin_name} hit {status} at {last_price:.4f}\n💰 *P&L:* {profit_str}")
                    push_signal_to_notion_journal(coin_name, f"SHORT [{status.upper()}]", trade['entry'], trade['sl'], "Closed")
                    state['active_trade'] = None
                    return

        # 🔵 NEW SIGNAL SCANNING (If no active trade)
        if state['active_trade'] is None:
            bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=200) # Need 200 for EMA150
            if len(bars) < 150: return
            
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # V1 Indicators
            df['ema_150'] = ta.ema(df['close'], length=150)
            df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
            
            # Bullish FVG Array
            bull_cond = (df['low'] > df['high'].shift(2)) & (df['close'].shift(1) > df['open'].shift(1))
            df.loc[bull_cond, 'bull_fvg_top'] = df['low']
            df.loc[bull_cond, 'bull_fvg_bottom'] = df['high'].shift(2)
            df['bull_fvg_top'] = df['bull_fvg_top'].ffill()
            df['bull_fvg_bottom'] = df['bull_fvg_bottom'].ffill()
            
            # Bearish FVG Array
            bear_cond = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['open'].shift(1))
            df.loc[bear_cond, 'bear_fvg_top'] = df['low'].shift(2)
            df.loc[bear_cond, 'bear_fvg_bottom'] = df['high']
            df['bear_fvg_top'] = df['bear_fvg_top'].ffill()
            df['bear_fvg_bottom'] = df['bear_fvg_bottom'].ffill()
            
            # Get latest closed candle (-2) and the one before it (-3) to check crossover
            prev = df.iloc[-3]
            curr = df.iloc[-2]
            
            buy_triggered = False
            sell_triggered = False
            
            # LONG CONDITION
            if (curr['close'] > curr['ema_150'] and curr['adx'] > 25 and curr['volume'] > 0):
                # Crossed below FVG Top logic
                if prev['close'] > prev['bull_fvg_top'] and curr['close'] < curr['bull_fvg_top']:
                    if curr['close'] >= curr['bull_fvg_bottom']:
                        buy_triggered = True
                        
            # SHORT CONDITION
            if (curr['close'] < curr['ema_150'] and curr['adx'] > 25 and curr['volume'] > 0):
                # Crossed above FVG Bottom logic
                if prev['close'] < prev['bear_fvg_bottom'] and curr['close'] > curr['bear_fvg_bottom']:
                    if curr['close'] <= curr['bear_fvg_top']:
                        sell_triggered = True

            # 🚀 EXECUTE ALERTS & LOGGING
            if buy_triggered or sell_triggered:
                t_time = str(df.iloc[-2]['timestamp'])
                signal_id = f"{symbol.replace('/', '_')}_{t_time}"
                
                if is_signal_logged(signal_id): return
                append_to_ledger(signal_id)
                
                entry_price = curr['close']
                
                if buy_triggered:
                    hard_sl = entry_price * (1 - HARD_SL_PCT)
                    state['active_trade'] = {
                        'dir': "LONG", 'entry': entry_price, 'sl': hard_sl, 
                        'max_price': entry_price, 'min_price': entry_price,
                        'trailing_active': False, 'open_time': now_utc
                    }
                    
                    msg = (f"🟢 *INSTITUTIONAL LONG TRIGGERED*\n\n"
                           f"🪙 *Asset:* #{coin_name}\n"
                           f"💰 *Entry:* ${entry_price:.4f}\n"
                           f"🛑 *Hard SL:* ${hard_sl:.4f} (-6.5%)\n"
                           f"🚀 *Trailing Start:* ${entry_price * (1 + TRAILING_START_PCT):.4f} (+4.0%)\n\n"
                           f"📌 _Smart Money Liquidity Swept._")
                           
                    tw_msg = (f"🚨 V10 ALGO SETUP 🚨\n\n🟢 LONG TRIGGERED: #{coin_name}\n"
                              f"📊 Entry: ${entry_price:.4f}\n"
                              f"💼 Institutional FVG Detected.\n\n"
                              f"💎 VIP Premium Access:\nhttps://t.me/+hQ7zz0wWfJ02YzFl")
                              
                    send_telegram_alert(msg)
                    push_signal_to_notion_journal(coin_name, "LONG [ENTRY]", entry_price, hard_sl, "Active")
                    post_to_x_platform(tw_msg)

                elif sell_triggered:
                    hard_sl = entry_price * (1 + HARD_SL_PCT)
                    state['active_trade'] = {
                        'dir': "SHORT", 'entry': entry_price, 'sl': hard_sl, 
                        'max_price': entry_price, 'min_price': entry_price,
                        'trailing_active': False, 'open_time': now_utc
                    }
                    
                    msg = (f"🔴 *INSTITUTIONAL SHORT TRIGGERED*\n\n"
                           f"🪙 *Asset:* #{coin_name}\n"
                           f"💰 *Entry:* ${entry_price:.4f}\n"
                           f"🛑 *Hard SL:* ${hard_sl:.4f} (+6.5%)\n"
                           f"🚀 *Trailing Start:* ${entry_price * (1 - TRAILING_START_PCT):.4f} (+4.0%)\n\n"
                           f"📌 _Smart Money Liquidity Swept._")
                           
                    tw_msg = (f"🚨 V10 ALGO SETUP 🚨\n\n🔴 SHORT TRIGGERED: #{coin_name}\n"
                              f"📊 Entry: ${entry_price:.4f}\n"
                              f"💼 Institutional FVG Detected.\n\n"
                              f"💎 VIP Premium Access:\nhttps://t.me/+hQ7zz0wWfJ02YzFl")

                    send_telegram_alert(msg)
                    push_signal_to_notion_journal(coin_name, "SHORT [ENTRY]", entry_price, hard_sl, "Active")
                    post_to_x_platform(tw_msg)

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
    
    print("Launching Omni-Channel High-Volume Automated Array...")
    engine_loop()
