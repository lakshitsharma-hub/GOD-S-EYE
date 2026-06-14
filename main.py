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
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "⚡ GOD'S EYE V11.0 [Holy Grail 3% Compounding Engine] ONLINE 24/7."

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

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'BNB/USDT', 'DOGE/USDT', 'AVAX/USDT']

# 🔥 V11 STRATEGY & SHIELD PARAMS
TIMEFRAME = '1h'
HARD_SL_PCT = 0.065
BREAK_EVEN_TRIGGER_PCT = 0.025  
TRAILING_START_PCT = 0.040      
TRAILING_STEP_PCT = 0.010       

# 📊 THE "TRUE 3%" VIRTUAL COMPOUNDING ENGINE
STARTING_BALANCE = 1000.0
TRUE_RISK_PCT = 0.03  # Exact 3% capital risk per trade
WALLET_FILE = "virtual_wallet.txt"
LEDGER_FILE = "signals_logged.txt"

# V11 Telemetry State Framework
market_states = {
    symbol: {
        'active_trade': False,
        'side': None,
        'entry_price': 0.0,
        'sl_price': 0.0,
        'risk_usd': 0.0,
        'volume_usd': 0.0,
        'be_activated': False
    } for symbol in SYMBOLS
}

# ==============================================================================
# 🗃️ WALLET & LEDGER ENGINE (DE-DUPLICATION INCLUDED)
# ==============================================================================
def get_virtual_balance():
    if not os.path.exists(WALLET_FILE):
        set_virtual_balance(STARTING_BALANCE)
        return STARTING_BALANCE
    try:
        with open(WALLET_FILE, 'r') as f: return float(f.read().strip())
    except: return STARTING_BALANCE

def set_virtual_balance(amount):
    with open(WALLET_FILE, 'w') as f: f.write(str(round(amount, 2)))

def calculate_true_risk_volume():
    balance = get_virtual_balance()
    risk_usd = balance * TRUE_RISK_PCT
    # Volume needed so that a 6.5% drop equals exactly risk_usd
    volume_usd = risk_usd / HARD_SL_PCT 
    return round(risk_usd, 2), round(volume_usd, 2)

def is_signal_logged(signal_id):
    if not os.path.exists(LEDGER_FILE): return False
    try:
        with open(LEDGER_FILE, 'r') as f: return signal_id in f.read().splitlines()
    except: return False

def append_to_ledger(signal_id):
    try:
        with open(LEDGER_FILE, 'a') as f: f.write(f"{signal_id}\n")
    except: pass

# ==============================================================================
# 📢 DISTRIBUTION CORES
# ==============================================================================
def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def post_to_x_platform(tweet_text):
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]): return
    url = "https://api.twitter.com/2/tweets"
    nonce, timestamp = secrets.token_hex(16), str(int(time.time()))
    oauth_params = {"oauth_consumer_key": X_API_KEY, "oauth_nonce": nonce, "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": timestamp, "oauth_token": X_ACCESS_TOKEN, "oauth_version": "1.0"}
    
    encoded_params = {urllib.parse.quote(k, safe=''): urllib.parse.quote(v, safe='') for k, v in oauth_params.items()}
    param_string = "&".join([f"{k}={v}" for k, v in sorted(encoded_params.items())])
    base_string = f"POST&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    signing_key = f"{urllib.parse.quote(X_API_SECRET, safe='')}&{urllib.parse.quote(X_ACCESS_SECRET, safe='')}"
    
    signature = hmac.new(signing_key.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha1)
    oauth_params["oauth_signature"] = base64.b64encode(signature.digest()).decode('utf-8')
    auth_header = "OAuth " + ", ".join([f'{urllib.parse.quote(k)}="{urllib.parse.quote(v)}"' for k, v in oauth_params.items()])
    
    try: requests.post(url, headers={"Authorization": auth_header, "Content-Type": "application/json"}, json={"text": tweet_text}, timeout=10)
    except: pass

def push_signal_to_notion(asset, signal_type, entry_price, sl, risk_amount):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: return
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Asset": {"title": [{"text": {"content": asset}}]},
            "Signal": {"rich_text": [{"text": {"content": signal_type}}]},
            "Entry": {"number": entry_price},
            "Stop Loss": {"rich_text": [{"text": {"content": str(sl)}}]},
            "Status": {"select": {"name": "Active"}},
            "Risked Amount ($)": {"number": risk_amount}
        }
    }
    try: requests.post(url, headers=headers, json=data, timeout=10)
    except: pass

# ==============================================================================
# 🧠 CORE SCANNER & TRADE MANAGER (1-MINUTE LOOP)
# ==============================================================================
def scan_markets():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚡ Scanning & Managing Trades...")
    
    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['ema_150'] = ta.ema(df['close'], length=150)
            df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
            
            # BULLISH FVG ARRAY
            bull_cond = (df['low'] > df['high'].shift(2)) & (df['close'].shift(1) > df['open'].shift(1))
            df.loc[bull_cond, 'bull_fvg_top'] = df['low']
            df.loc[bull_cond, 'bull_fvg_bottom'] = df['high'].shift(2)
            df['bull_fvg_top'] = df['bull_fvg_top'].ffill()
            df['bull_fvg_bottom'] = df['bull_fvg_bottom'].ffill()

            # BEARISH FVG ARRAY
            bear_cond = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['open'].shift(1))
            df.loc[bear_cond, 'bear_fvg_top'] = df['low'].shift(2)
            df.loc[bear_cond, 'bear_fvg_bottom'] = df['high']
            df['bear_fvg_top'] = df['bear_fvg_top'].ffill()
            df['bear_fvg_bottom'] = df['bear_fvg_bottom'].ffill()

            latest = df.iloc[-1]
            curr = df.iloc[-2]   
            prev = df.iloc[-3]   
            
            state = market_states[symbol]

            # 🛡️ 1. TRADE MANAGEMENT (1-Min Precision Checking)
            if state['active_trade']:
                entry = state['entry_price']
                side = state['side']
                sl_price = state['sl_price']
                current_price = latest['close'] 
                
                profit_pct = (current_price - entry) / entry if side == 'LONG' else (entry - current_price) / entry

                # Trailing Stop Logic (Lock Profit)
                if profit_pct >= TRAILING_START_PCT:
                    new_sl = current_price * (1 - TRAILING_STEP_PCT) if side == 'LONG' else current_price * (1 + TRAILING_STEP_PCT)
                    if (side == 'LONG' and new_sl > sl_price) or (side == 'SHORT' and new_sl < sl_price):
                        state['sl_price'] = new_sl
                        send_telegram_alert(f"📈 *PROFIT LOCKED: {symbol}*\nTrailing Stop updated to: ${round(new_sl, 4)}")

                # Break-Even Shield Logic
                elif profit_pct >= BREAK_EVEN_TRIGGER_PCT and not state['be_activated']:
                    state['sl_price'] = entry
                    state['be_activated'] = True
                    send_telegram_alert(f"🛡️ *SHIELD ACTIVATED: {symbol}*\nTrade is Risk-Free. SL moved to Entry (${entry}).")
                
                # Exit Check using exact wicks (low for long, high for short)
                is_sl_hit = (side == 'LONG' and latest['low'] <= state['sl_price']) or (side == 'SHORT' and latest['high'] >= state['sl_price'])
                
                if is_sl_hit:
                    exit_price = state['sl_price']
                    actual_profit_pct = (exit_price - entry) / entry if side == 'LONG' else (entry - exit_price) / entry
                    pnl_usd = state['volume_usd'] * actual_profit_pct
                    
                    new_balance = get_virtual_balance() + pnl_usd
                    set_virtual_balance(new_balance)
                    
                    emoji = "✅" if pnl_usd > 0 else "❌" if pnl_usd < 0 else "🛡️"
                    msg = f"{emoji} *TRADE CLOSED: {symbol}*\nSide: {side}\nExit Price: ${round(exit_price, 4)}\nPnL: ${round(pnl_usd, 2)}\nNew Wallet: ${round(new_balance, 2)}"
                    send_telegram_alert(msg)
                    
                    # Reset State
                    market_states[symbol] = {'active_trade': False, 'side': None, 'entry_price': 0, 'sl_price': 0, 'risk_usd': 0, 'volume_usd': 0, 'be_activated': False}
                
                continue 

            # 🔎 2. ENTRY SCANNER (De-Duplication + True 3% Risk Engine)
            t_time = str(curr['timestamp'])
            signal_id = f"{symbol.replace('/', '_')}_{t_time}"
            
            if is_signal_logged(signal_id):
                continue

            wallet_balance = get_virtual_balance()
            risk_usd, volume_usd = calculate_true_risk_volume()

            # LONG TRIGGER
            if curr['close'] > curr['ema_150'] and curr['adx'] > 25 and curr['volume'] > 0:
                if prev['close'] > prev['bull_fvg_top'] and curr['close'] < curr['bull_fvg_top']:
                    if curr['close'] >= curr['bull_fvg_bottom']:
                        append_to_ledger(signal_id)
                        sl_price = round(curr['close'] * (1 - HARD_SL_PCT), 4)
                        
                        state['active_trade'] = True
                        state['side'] = 'LONG'
                        state['entry_price'] = curr['close']
                        state['sl_price'] = sl_price
                        state['risk_usd'] = risk_usd
                        state['volume_usd'] = volume_usd
                        
                        msg = f"🟢 *LONG TRIGGERED: {symbol}*\nEntry: ${curr['close']}\nHard SL: ${sl_price} (-6.5%)\nCapital Risked: ${risk_usd} (3%)\nVirtual Account: ${wallet_balance}"
                        send_telegram_alert(msg)
                        
                        # X (Twitter) Alert with Custom Funnel Link
                        post_to_x_platform(f"🚨 QUANT ALERT: Going LONG on {symbol} at {curr['close']}.\n\nCatch live SL/TP updates and join the VIP community here: https://t.me/+hQ7zz0wWfJ02YzFl\n\n#CryptoTrading #Algo")
                        
                        push_signal_to_notion(symbol, "LONG", curr['close'], sl_price, risk_usd)

            # SHORT TRIGGER
            elif curr['close'] < curr['ema_150'] and curr['adx'] > 25 and curr['volume'] > 0:
                if prev['close'] < prev['bear_fvg_bottom'] and curr['close'] > curr['bear_fvg_bottom']:
                    if curr['close'] <= curr['bear_fvg_top']:
                        append_to_ledger(signal_id)
                        sl_price = round(curr['close'] * (1 + HARD_SL_PCT), 4)
                        
                        state['active_trade'] = True
                        state['side'] = 'SHORT'
                        state['entry_price'] = curr['close']
                        state['sl_price'] = sl_price
                        state['risk_usd'] = risk_usd
                        state['volume_usd'] = volume_usd
                        
                        msg = f"🔴 *SHORT TRIGGERED: {symbol}*\nEntry: ${curr['close']}\nHard SL: ${sl_price} (+6.5%)\nCapital Risked: ${risk_usd} (3%)\nVirtual Account: ${wallet_balance}"
                        send_telegram_alert(msg)
                        
                        # X (Twitter) Alert with Custom Funnel Link
                        post_to_x_platform(f"🚨 QUANT ALERT: Going SHORT on {symbol} at {curr['close']}.\n\nCatch live SL/TP updates and join the VIP community here: https://t.me/+hQ7zz0wWfJ02YzFl\n\n#CryptoTrading #Algo")
                        
                        push_signal_to_notion(symbol, "SHORT", curr['close'], sl_price, risk_usd)

            time.sleep(1) # Binance rate limit protection
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

def run_bot():
    send_telegram_alert("⚡ *GOD'S EYE V11.0 [Holy Grail 3% Compounding Engine] ONLINE*\n\nStatus: Active\nStrategy: True 3% Risk + 1-Min Shield Tracking\nWallet Initiated: $1000.00")
    while True:
        scan_markets()
        time.sleep(60) # 1-Minute exact precision tracking

if __name__ == "__main__":
    Thread(target=run_flask).start()
    time.sleep(5)
    run_bot()
