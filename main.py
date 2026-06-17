# ==============================================================================
# 🦅 GOD'S EYE - THE ULTIMATE TRADING ENGINE (FULL MATRIX)
# ==============================================================================

import os
import time
import requests
import ccxt
import tweepy
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Initialize Flask Server (To keep the bot alive on Render 24/7)
app = Flask('')

@app.route('/')
def home():
    return "🦅 GOD'S EYE ALGORITHMIC ENGINE IS ONLINE 24/7."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# 🔐 SECURE CREDENTIALS ARCHITECTURE (Loads from .env)
# ==============================================================================
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

NOTION_PUBLIC_URL = "https://app.notion.com/p/377450889e638092bdc5e04082836f13?v=377450889e6380c3b810000c0bb7edc0"
TELEGRAM_JOIN_URL = "https://t.me/+hQ7zz0wWfJ02YzFl"

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# Combined & Optimized Institutional Pairs
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 
    'DOGE/USDT', 'LINK/USDT', 'DOT/USDT', 'AVAX/USDT', 'ATOM/USDT', 
    'UNI/USDT', 'LTC/USDT', 'BCH/USDT'
]

# ==============================================================================
# 🔥 HOLY GRAIL PARAMETERS (Strict Risk Management)
# ==============================================================================
TIMEFRAME = '1h'
HARD_SL_PCT = 0.15           # 15% Strict Chart SL
TRUE_RISK_PCT = 0.06         # 6% Max Portfolio Risk
TRAILING_START_PCT = 0.025   # Trailing activates at +2.5%
TRAILING_GAP_PCT = 0.001     # Native 0.1% breathing space below peak
TIME_BAILOUT_HOURS = 8.0     # Maximum stagnant time
TIME_BAILOUT_LOSS = -0.015   # Max loss allowed at 8 hours

STARTING_BALANCE = 1000.0
WALLET_FILE = "virtual_wallet.txt"
LEDGER_FILE = "signals_logged.txt"

# Telemetry State Framework
market_states = {
    symbol: {
        'active_trade': False,
        'side': None,
        'entry_price': 0.0,
        'sl_price': 0.0,
        'target': 0.0,
        'peak_price': 0.0,
        'risk_usd': 0.0,
        'volume_usd': 0.0,
        'trailing_active': False,
        'entry_time': None,
        'notion_page_id': None
    } for symbol in SYMBOLS
}

# ==============================================================================
# 🗃️ VIRTUAL WALLET & LEDGER ENGINE
# ==============================================================================
def get_virtual_balance():
    if not os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, 'w') as f: f.write(str(STARTING_BALANCE))
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
# 📢 DISTRIBUTION CORES (TELEGRAM, NOTION, TWITTER)
# ==============================================================================
def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=12)
    except Exception as e: print(f"Telegram Error: {e}", flush=True)

def notion_open_trade(trade_id, asset, side, entry_price, sl_price, target_price):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: return None
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Asset": {"title": [{"text": {"content": f"{asset} #{trade_id}"}}]},
            "Signal": {"select": {"name": side}},
            "Entry": {"number": float(entry_price)},
            "SL": {"number": float(sl_price)},
            "Target": {"number": float(target_price)},
            "Status": {"select": {"name": "OPEN"}},
            "Trailing Active": {"checkbox": False},
            "Dynamic Floor SL": {"number": 0.0}
        }
    }
    try: 
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200: return response.json().get("id")
    except: pass
    return None

def notion_update_trailing(page_id, dynamic_sl):
    if not NOTION_TOKEN or not page_id: return
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    data = {
        "properties": {
            "Trailing Active": {"checkbox": True},
            "Dynamic Floor SL": {"number": float(dynamic_sl)}
        }
    }
    try: requests.patch(url, headers=headers, json=data, timeout=10)
    except: pass

def notion_close_trade(page_id, result_tag):
    if not NOTION_TOKEN or not page_id: return
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    data = {
        "properties": {
            "Status": {"select": {"name": "CLOSED"}},
            "Result": {"select": {"name": result_tag}}
        }
    }
    try: requests.patch(url, headers=headers, json=data, timeout=10)
    except: pass

def post_to_twitter(tweet_text):
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]): return
    try:
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        client.create_tweet(text=tweet_text, user_auth=True)
    except Exception as e:
        print(f"Twitter Post Silently Failed (Awaiting Paid Tier): {e}")

def delayed_twitter_post(tweet_text, delay_seconds=600):
    """Executes exactly after 10 minutes (600s) to create FOMO."""
    time.sleep(delay_seconds)
    post_to_twitter(tweet_text)

# ==============================================================================
# 🧠 GOD'S EYE MASTER SCANNER (1-MINUTE EXECUTION LOOP)
# ==============================================================================
def scan_markets():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🦅 Scanning Core Matrices...", flush=True)
    
    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=300)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # --- INDICATOR CALCULATIONS ---
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_150'] = ta.ema(df['close'], length=150)
            df['ema_200'] = ta.ema(df['close'], length=200)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['volume_ma'] = df['volume'].rolling(24).mean()
            
            bb = ta.bbands(df['close'], length=20, std=2)
            if bb is not None and not bb.empty:
                bbu = [c for c in bb.columns if 'BBU' in c][0]
                bbl = [c for c in bb.columns if 'BBL' in c][0]
                bbm = [c for c in bb.columns if 'BBM' in c][0]
                df['bb_width'] = (bb[bbu] - bb[bbl]) / bb[bbm]
                df['bb_width_mean'] = df['bb_width'].rolling(20).mean()
            else:
                df['bb_width'] = 0; df['bb_width_mean'] = 0
            
            df['res_24h'] = df['high'].rolling(24).max().shift(1)
            
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
            clean_symbol = symbol.replace('/USDT', '')

            # 🛡️ 1. ACTIVE TRADE MANAGEMENT
            if state['active_trade']:
                entry = state['entry_price']
                side = state['side']
                current_price = latest['close']
                
                profit_pct = (current_price - entry) / entry if side == 'LONG' else (entry - current_price) / entry
                time_open_hours = (datetime.now() - state['entry_time']).total_seconds() / 3600

                # A. Time Bailout Logic (8 Hours Stagnation)
                if time_open_hours >= TIME_BAILOUT_HOURS and profit_pct <= TIME_BAILOUT_LOSS:
                    notion_close_trade(state['notion_page_id'], "time_bailout_loss")
                    
                    msg = (f"⏳ **GOD'S EYE: STRATEGY EXIT (TIME BAILOUT)**\n\n"
                           f"🪙 Asset: {symbol}\n🕒 Duration: 8 Hours (Stagnant Volume)\n"
                           f"📉 Exit PnL: {round(profit_pct * 100, 2)}%\n"
                           f"🔕 Status: Position closed via market order. The engine doesn't hope, it executes.")
                    send_telegram_alert(msg)
                    
                    market_states[symbol] = {'active_trade': False}
                    continue

                # B. Trailing Engine Activation (At +2.5%)
                if profit_pct >= TRAILING_START_PCT:
                    if not state['trailing_active']:
                        state['trailing_active'] = True
                        msg = (f"🛡️ **GOD'S EYE: TRAILING PROTECTION ACTIVATED**\n\n"
                               f"🪙 Asset: {symbol}\n📈 Current PnL: +{round(profit_pct*100, 2)}%\n"
                               f"🛡️ Status: Native Break-Even Shield Engaged. Dynamic floor locked.")
                        send_telegram_alert(msg)
                    
                    if side == 'LONG' and current_price > state['peak_price']: state['peak_price'] = current_price
                    if side == 'SHORT' and current_price < state['peak_price']: state['peak_price'] = current_price
                    
                    new_sl = state['peak_price'] * (1 - TRAILING_GAP_PCT) if side == 'LONG' else state['peak_price'] * (1 + TRAILING_GAP_PCT)
                    
                    sl_moved = (side == 'LONG' and new_sl > state['sl_price']) or (side == 'SHORT' and new_sl < state['sl_price'])
                    if sl_moved:
                        state['sl_price'] = round(new_sl, 4)
                        notion_update_trailing(state['notion_page_id'], state['sl_price'])

                # C. Stop Loss / Trailing Stop Hit Trigger
                is_sl_hit = (side == 'LONG' and latest['low'] <= state['sl_price']) or (side == 'SHORT' and latest['high'] >= state['sl_price'])
                
                if is_sl_hit:
                    exit_price = state['sl_price']
                    actual_profit_pct = (exit_price - entry) / entry if side == 'LONG' else (entry - exit_price) / entry
                    pnl_usd = state['volume_usd'] * actual_profit_pct
                    
                    set_virtual_balance(get_virtual_balance() + pnl_usd)
                    
                    result_tag = "trailing_stop_loss" if state['trailing_active'] else "stop_loss"
                    notion_close_trade(state['notion_page_id'], result_tag)

                    if state['trailing_active']:
                        msg = (f"🎉 **GOD'S EYE: TRAILING PROFIT SECURED** 🎉\n\n"
                               f"🪙 Asset: {symbol} | {side}\n🎯 Entry: ${round(entry, 4)}\n"
                               f"💰 Exit: ${round(exit_price, 4)}\n📈 Net Strategy Profit: +{round(actual_profit_pct*100, 2)}%\n\n"
                               f"Automated trailing engine maxed out the trend smoothly.")
                        send_telegram_alert(msg)
                        
                        # Twitter FOMO Post for Win
                        t_msg = (f"🎉 GOD'S EYE: TRAILING PROFIT SECURED! 🎉\n\n🪙 Asset: ${clean_symbol} | {side}\n"
                                 f"📈 Net Profit: +{round(actual_profit_pct*100, 2)}% NET ✅\n\n"
                                 f"While retail panic-sold, our native 0.1% floor locked the peak flawlessly. 💸\n\n"
                                 f"👥 Premium Access: {TELEGRAM_JOIN_URL}\n📊 Live Ledger: {NOTION_PUBLIC_URL}")
                        post_to_twitter(t_msg)
                        
                    else:
                        msg = (f"💥 **GOD'S EYE: STOP LOSS EXECUTION** 💥\n\n"
                               f"🪙 Asset: {symbol} | {side}\n🛑 Exit Price: ${round(exit_price, 4)}\n"
                               f"📉 Net Chart Loss: {round(actual_profit_pct*100, 2)}%\n"
                               f"🛡️ Account Impact: Exact -6.0% capital risk hit. Portfolio is protected.")
                        send_telegram_alert(msg)
                        
                        # Twitter Trust Post for Loss
                        t_msg = (f"💥 GOD'S EYE RISK SHIELD: POSITION TERMINATED 💥\n\n🪙 Asset: ${clean_symbol} | {side}\n"
                                 f"📉 Chart Drop: {round(actual_profit_pct*100, 2)}%\n🛡️ Portfolio Impact: Exact -6.0% Capital Control.\n\n"
                                 f"Retail blew their accounts here, but our elite math engine kept us safe. 🧠\n\n"
                                 f"👇 Join The 1%: {TELEGRAM_JOIN_URL}")
                        post_to_twitter(t_msg)
                    
                    market_states[symbol] = {k: False if type(v) == bool else None for k, v in state.items()}
                
                continue 

            # 🔎 2. ENTRY SCANNER
            t_time = str(curr['timestamp'])
            signal_id = f"{symbol.replace('/', '_')}_{t_time}"
            trade_uid = str(int(time.time()))
            
            if is_signal_logged(signal_id): continue

            req_cols = ['ema_50', 'ema_200', 'rsi', 'bb_width', 'bb_width_mean', 'res_24h', 'volume_ma', 'ema_150', 'adx', 'bear_fvg_top', 'bear_fvg_bottom']
            if any(pd.isna(curr.get(col, np.nan)) for col in req_cols): continue

            risk_usd, volume_usd = calculate_true_risk_volume()

            # 🟢 LONG TRIGGER 
            if (curr['ema_50'] > curr['ema_200'] and curr['close'] > curr['ema_50'] and 
                curr['close'] > curr['res_24h'] and curr['bb_width'] < (curr['bb_width_mean'] * 1.25) and 
                curr['volume'] > (curr['volume_ma'] * 1.5) and 55 < curr['rsi'] < 80):
                
                append_to_ledger(signal_id)
                sl_price = round(curr['close'] * (1 - HARD_SL_PCT), 4)
                target_price = round(curr['close'] * 1.05, 4) 
                
                state.update({
                    'active_trade': True, 'side': 'LONG', 'entry_price': curr['close'], 
                    'sl_price': sl_price, 'target': target_price, 'peak_price': curr['close'], 
                    'risk_usd': risk_usd, 'volume_usd': volume_usd, 'trailing_active': False,
                    'entry_time': datetime.now()
                })
                
                state['notion_page_id'] = notion_open_trade(trade_uid, symbol, "LONG", curr['close'], sl_price, target_price)
                
                # Telegram
                msg = (f"🚨 **GOD'S EYE ALGO: NEW POSITION EXECUTED**\n\n"
                       f"🪙 Asset: {symbol}\n🟢 Direction: LONG\n⚡ Leverage: 5.0x\n"
                       f"🎯 Entry Price: ${curr['close']}\n🛑 Chart Stop-Loss: -15.0%\n"
                       f"🛡️ Max Portfolio Risk: -6.0% of capital")
                send_telegram_alert(msg) 
                
                # Twitter Delayed Thread (10 Mins)
                t_msg = (f"🚨 GOD'S EYE ALGO: NEW POSITION INJECTED 🚨\n\n🪙 Asset: ${clean_symbol}\n🟢 Type: LONG\n"
                         f"🎯 Entry: ${curr['close']}\n🛡️ Risk: Strict 6.0% Wallet Protection\n\n"
                         f"Premium members already banked the early entry 10 mins ago! Don't chase green candles late. 🤫\n\n"
                         f"👇 VIP Alerts: {TELEGRAM_JOIN_URL}")
                Thread(target=delayed_twitter_post, args=(t_msg, 600)).start()

            # 🔴 SHORT TRIGGER
            elif curr['close'] < curr['ema_150'] and curr['adx'] > 25 and curr['volume'] > 0:
                if not pd.isna(prev.get('bear_fvg_bottom', np.nan)) and prev['close'] < prev['bear_fvg_bottom'] and curr['close'] > curr['bear_fvg_bottom']:
                    if curr['close'] <= curr['bear_fvg_top']:
                        
                        append_to_ledger(signal_id)
                        sl_price = round(curr['close'] * (1 + HARD_SL_PCT), 4)
                        target_price = round(curr['close'] * 0.95, 4)
                        
                        state.update({
                            'active_trade': True, 'side': 'SHORT', 'entry_price': curr['close'], 
                            'sl_price': sl_price, 'target': target_price, 'peak_price': curr['close'], 
                            'risk_usd': risk_usd, 'volume_usd': volume_usd, 'trailing_active': False,
                            'entry_time': datetime.now()
                        })
                        
                        state['notion_page_id'] = notion_open_trade(trade_uid, symbol, "SHORT", curr['close'], sl_price, target_price)
                        
                        # Telegram
                        msg = (f"🚨 **GOD'S EYE ALGO: NEW POSITION EXECUTED**\n\n"
                               f"🪙 Asset: {symbol}\n🔴 Direction: SHORT\n⚡ Leverage: 5.0x\n"
                               f"🎯 Entry Price: ${curr['close']}\n🛑 Chart Stop-Loss: -15.0%\n"
                               f"🛡️ Max Portfolio Risk: -6.0% of capital")
                        send_telegram_alert(msg)
                        
                        # Twitter Delayed Thread (10 Mins)
                        t_msg = (f"🚨 GOD'S EYE ALGO: NEW POSITION INJECTED 🚨\n\n🪙 Asset: ${clean_symbol}\n🔴 Type: SHORT\n"
                                 f"🎯 Entry: ${curr['close']}\n🛡️ Risk: Strict 6.0% Wallet Protection\n\n"
                                 f"Premium members already banked the early entry 10 mins ago! Don't chase trends late. 🤫\n\n"
                                 f"👇 VIP Alerts: {TELEGRAM_JOIN_URL}")
                        Thread(target=delayed_twitter_post, args=(t_msg, 600)).start()

            time.sleep(1) 
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}", flush=True)

def run_bot():
    print("\n🦅 GOD'S EYE INITIALIZED. MASTER ENGINE RUNNING SILENTLY...", flush=True)
    while True:
        scan_markets()
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    time.sleep(3)
    run_bot()
