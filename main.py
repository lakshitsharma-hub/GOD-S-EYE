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
    return "⚡ GOD'S EYE V30 [The Ultimate Engine] ONLINE 24/7."

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

NOTION_PUBLIC_URL = "https://app.notion.com/p/377450889e638092bdc5e04082836f13?v=377450889e6380c3b810000c0bb7edc0"
TELEGRAM_JOIN_URL = "https://t.me/+hQ7zz0wWfJ02YzFl"

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# V30 Optimized Pairs
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'BCH/USDT']

# 🔥 V30 HOLY GRAIL PARAMS (Strictly Trailing & Break-Even)
TIMEFRAME = '1h'
HARD_SL_PCT = 0.07  
BREAK_EVEN_TRIGGER_PCT = 0.025  
TRAILING_START_PCT = 0.040      
TRAILING_STEP_PCT = 0.010       

STARTING_BALANCE = 1000.0
TRUE_RISK_PCT = 0.03  
WALLET_FILE = "virtual_wallet.txt"
LEDGER_FILE = "signals_logged.txt"

# Telemetry State Framework
market_states = {
    symbol: {
        'active_trade': False,
        'side': None,
        'entry_price': 0.0,
        'sl_price': 0.0,
        'risk_usd': 0.0,
        'volume_usd': 0.0,
        'be_activated': False,
        'notion_page_id': None
    } for symbol in SYMBOLS
}

# ==============================================================================
# 🗃️ WALLET & LEDGER ENGINE
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
# 📢 DISTRIBUTION CORES (NOTION + TWITTER + TELEGRAM)
# ==============================================================================
def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def push_signal_to_notion(asset, signal_type, entry_price, sl):
    """Creates a Notion Page. Target is intentionally omitted to show 'Open' Trailing nature."""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: return None
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}", 
        "Content-Type": "application/json", 
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Asset": {"title": [{"text": {"content": asset}}]},
            "Signal": {"rich_text": [{"text": {"content": signal_type}}]},
            "Entry": {"rich_text": [{"text": {"content": str(entry_price)}}]},
            "SL": {"rich_text": [{"text": {"content": str(sl)}}]},
            "Status": {"select": {"name": "Active"}},
            "Result": {"rich_text": [{"text": {"content": "—"}}]}
        }
    }
    try: 
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("id")
        else:
            print(f"Notion Error: {response.text}", flush=True)
    except Exception as e: print(f"Notion Crash: {e}", flush=True)
    return None

def close_notion_trade(page_id, pnl_usd, pnl_pct):
    """Updates Notion Page Status to Closed and records real PnL in 'Result' column"""
    if not NOTION_TOKEN or not page_id: return
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}", 
        "Content-Type": "application/json", 
        "Notion-Version": "2022-06-28"
    }
    
    emoji = "✅" if pnl_usd > 0 else "🛡️" if pnl_usd == 0 else "❌"
    result_str = f"{emoji} {round(pnl_pct * 100, 2)}% (${round(pnl_usd, 2)})"
    
    data = {
        "properties": {
            "Status": {"select": {"name": "Closed"}},
            "Result": {"rich_text": [{"text": {"content": result_str}}]}
        }
    }
    try: requests.patch(url, headers=headers, json=data, timeout=10)
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

def delayed_twitter_post(tweet_text, delay_seconds=900):
    time.sleep(delay_seconds)
    post_to_x_platform(tweet_text)

# ==============================================================================
# 🧠 V30 MASTER SCANNER (1-MINUTE LOOP - STRICT ARCHITECTURE)
# ==============================================================================
def scan_markets():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚡ Scanning & Managing V30 Trades...", flush=True)
    
    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=300)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # --- V20 LONG INDICATORS ---
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'], length=200)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['volume_ma'] = df['volume'].rolling(24).mean()
            
            bb = ta.bbands(df['close'], length=20, std=2)
            if bb is not None and not bb.empty:
                bbu_col = [c for c in bb.columns if 'BBU' in c][0]
                bbl_col = [c for c in bb.columns if 'BBL' in c][0]
                bbm_col = [c for c in bb.columns if 'BBM' in c][0]
                
                df['bb_width'] = (bb[bbu_col] - bb[bbl_col]) / bb[bbm_col]
                df['bb_width_mean'] = df['bb_width'].rolling(20).mean()
            else:
                df['bb_width'] = 0
                df['bb_width_mean'] = 0
            
            df['res_24h'] = df['high'].rolling(24).max().shift(1)

            # --- ADX/FVG SHORT INDICATORS ---
            df['ema_150'] = ta.ema(df['close'], length=150)
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
            df['adx'] = adx_df['ADX_14'] if adx_df is not None else np.nan

            bear_cond = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['open'].shift(1))
            df['bear_fvg_top'] = np.where(bear_cond, df['low'].shift(2), np.nan)
            df['bear_fvg_bottom'] = np.where(bear_cond, df['high'], np.nan)
            df['bear_fvg_top'] = pd.Series(df['bear_fvg_top']).ffill().values
            df['bear_fvg_bottom'] = pd.Series(df['bear_fvg_bottom']).ffill().values

            latest = df.iloc[-1]
            curr = df.iloc[-2]   
            prev = df.iloc[-3]   
            
            state = market_states[symbol]

            # 🛡️ 1. TRADE MANAGEMENT (Live Profit Tracking)
            if state['active_trade']:
                entry = state['entry_price']
                side = state['side']
                current_price = latest['close'] 
                
                profit_pct = (current_price - entry) / entry if side == 'LONG' else (entry - current_price) / entry

                # Phase 2: Trailing SL (+4% and beyond)
                if profit_pct >= TRAILING_START_PCT:
                    new_sl = current_price * (1 - TRAILING_STEP_PCT) if side == 'LONG' else current_price * (1 + TRAILING_STEP_PCT)
                    sl_moved = (side == 'LONG' and new_sl > state['sl_price']) or (side == 'SHORT' and new_sl < state['sl_price'])
                    
                    if sl_moved:
                        state['sl_price'] = round(new_sl, 4)
                        send_telegram_alert(f"📈 *PROFIT LOCKED: {symbol}*\nTrailing Stop logically shifted up to: ${round(new_sl, 4)}\nFloating PnL: {round(profit_pct * 100, 2)}%")

                # Phase 1: Break Even Shield (+2.5%)
                elif profit_pct >= BREAK_EVEN_TRIGGER_PCT and not state['be_activated']:
                    state['sl_price'] = entry
                    state['be_activated'] = True
                    send_telegram_alert(f"🛡️ *SHIELD ACTIVATED: {symbol}*\nTrade is Risk-Free. SL moved to Entry (${entry}).")
                
                # Check Hit
                is_sl_hit = (side == 'LONG' and latest['low'] <= state['sl_price']) or (side == 'SHORT' and latest['high'] >= state['sl_price'])
                
                if is_sl_hit:
                    exit_price = state['sl_price']
                    actual_profit_pct = (exit_price - entry) / entry if side == 'LONG' else (entry - exit_price) / entry
                    pnl_usd = state['volume_usd'] * actual_profit_pct
                    
                    new_balance = get_virtual_balance() + pnl_usd
                    set_virtual_balance(new_balance)
                    
                    # Exact Sync: Close trade in Notion
                    if state['notion_page_id']:
                        close_notion_trade(state['notion_page_id'], pnl_usd, actual_profit_pct)

                    emoji = "✅" if pnl_usd > 0 else "🛡️" if pnl_usd == 0 else "❌"
                    msg = f"{emoji} *TRADE CLOSED: {symbol}*\nSide: {side}\nExit Price: ${round(exit_price, 4)}\nFinal Profit/Loss: {round(actual_profit_pct*100, 2)}%"
                    send_telegram_alert(msg)
                    
                    # Reset State
                    market_states[symbol] = {'active_trade': False, 'side': None, 'entry_price': 0, 'sl_price': 0, 'risk_usd': 0, 'volume_usd': 0, 'be_activated': False, 'notion_page_id': None}
                
                continue 

            # 🔎 2. V30 ENTRY SCANNER
            t_time = str(curr['timestamp'])
            signal_id = f"{symbol.replace('/', '_')}_{t_time}"
            
            if is_signal_logged(signal_id):
                continue

            # NaN Guard (Safety check)
            required_cols = ['ema_50', 'ema_200', 'rsi', 'bb_width', 'bb_width_mean', 'res_24h', 'volume_ma', 'ema_150', 'adx', 'bear_fvg_top', 'bear_fvg_bottom']
            if any(pd.isna(curr.get(col, np.nan)) for col in required_cols):
                continue

            risk_usd, volume_usd = calculate_true_risk_volume()
            clean_symbol = symbol.replace('/USDT', '')

            # 🟢 LONG TRIGGER 
            if (curr['ema_50'] > curr['ema_200'] and curr['close'] > curr['ema_50'] and 
                curr['close'] > curr['res_24h'] and curr['bb_width'] < (curr['bb_width_mean'] * 1.25) and 
                curr['volume'] > (curr['volume_ma'] * 1.5) and 55 < curr['rsi'] < 80):
                
                append_to_ledger(signal_id)
                sl_price = round(curr['close'] * (1 - HARD_SL_PCT), 4)
                
                state['active_trade'] = True
                state['side'] = 'LONG'
                state['entry_price'] = curr['close']
                state['sl_price'] = sl_price
                state['risk_usd'] = risk_usd
                state['volume_usd'] = volume_usd
                
                # Telegram Alert (Shows Target as Open)
                msg = f"🟢 *LONG TRIGGERED: {symbol}*\nEntry: ${curr['close']}\nTarget: OPEN (Trailing Engine Active)\nHard SL: ${sl_price} (-7%)"
                send_telegram_alert(msg) 
                
                # Push to Notion exactly as triggered
                state['notion_page_id'] = push_signal_to_notion(symbol, "LONG", curr['close'], sl_price) 
                
                # Twitter 
                tweet = f"🚨 𝐀𝐋𝐆𝐎 𝐀𝐋𝐄𝐑𝐓: Our V30 Engine fired a [LONG] on #{clean_symbol} 15 mins ago! 🚀\n\nEntry was nailed at ${curr['close']}.\n\n⏱️ You're seeing this late. VIP members got this instantly.\n\n📊 Live Public Tracker:\n🔗 {NOTION_PUBLIC_URL}\n\n⚡ Get Real-Time Execution:\n🔗 {TELEGRAM_JOIN_URL}"
                Thread(target=delayed_twitter_post, args=(tweet, 900)).start()

            # 🔴 SHORT TRIGGER 
            elif curr['close'] < curr['ema_150'] and curr['adx'] > 25 and curr['volume'] > 0:
                if not pd.isna(prev.get('bear_fvg_bottom', np.nan)) and prev['close'] < prev['bear_fvg_bottom'] and curr['close'] > curr['bear_fvg_bottom']:
                    if curr['close'] <= curr['bear_fvg_top']:
                        
                        append_to_ledger(signal_id)
                        sl_price = round(curr['close'] * (1 + HARD_SL_PCT), 4)
                        
                        state['active_trade'] = True
                        state['side'] = 'SHORT'
                        state['entry_price'] = curr['close']
                        state['sl_price'] = sl_price
                        state['risk_usd'] = risk_usd
                        state['volume_usd'] = volume_usd
                        
                        # Telegram Alert (Shows Target as Open)
                        msg = f"🔴 *SHORT TRIGGERED: {symbol}*\nEntry: ${curr['close']}\nTarget: OPEN (Trailing Engine Active)\nHard SL: ${sl_price} (+7%)"
                        send_telegram_alert(msg) 
                        
                        # Push to Notion exactly as triggered
                        state['notion_page_id'] = push_signal_to_notion(symbol, "SHORT", curr['close'], sl_price) 
                        
                        # Twitter
                        tweet = f"⚠️ 𝐈𝐍𝐒𝐓𝐈𝐓𝐔𝐓𝐈𝐎𝐍𝐀𝐋 𝐒𝐇𝐎𝐑𝐓: We caught the top on #{clean_symbol} 15 mins ago! 🩸\n\nShort Entry: ${curr['close']}.\n\n⏱️ Free feed is delayed. Our VIPs are already risk-free.\n\n📊 Live Public Tracker:\n🔗 {NOTION_PUBLIC_URL}\n\n⚡ Get Real-Time Execution:\n🔗 {TELEGRAM_JOIN_URL}"
                        Thread(target=delayed_twitter_post, args=(tweet, 900)).start()

            time.sleep(1) 
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}", flush=True)

def run_bot():
    print("GOD'S EYE V30 Initialized. Engine Running Silently...", flush=True)
    while True:
        scan_markets()
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    time.sleep(5)
    run_bot()
