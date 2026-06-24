# ==============================================================================
# 🦅 GOD'S EYE - STANDALONE QUANT ENGINE (ZERO SLIPPAGE EDITION)
# ==============================================================================

import os
import time
import requests
import ccxt
import tweepy
import pandas as pd
import pandas_ta as ta
import numpy as np
import queue
import threading
import warnings
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

# SSL Warnings Hide Karein
warnings.simplefilter('ignore', InsecureRequestWarning)

# Flask Server (Render 24/7 Keep-Alive)
app = Flask('')

@app.route('/')
def home():
    return "🦅 GOD'S EYE ALGORITHMIC ENGINE IS ONLINE 24/7."

# Shared secret so randoms on the internet can't spam your Telegram through this endpoint.
# Set RELAY_SECRET as an env var on Render, and send the same value from HuggingFace.
RELAY_SECRET = os.environ.get("RELAY_SECRET", "")

@app.route('/webhook/relay', methods=['POST'])
def webhook_relay():
    """Receives trade alerts from the HuggingFace bot and forwards them to Telegram
    using Render's outbound network (which isn't throttled, unlike HuggingFace's)."""
    data = request.get_json(silent=True) or {}

    if RELAY_SECRET and data.get('secret') != RELAY_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    message = data.get('message')
    if not message:
        return jsonify({"error": "missing 'message' field"}), 400

    # Enqueue exactly like a native signal — same queue, same retry/DIAG logging
    send_telegram_alert(message)
    print(f"📨 DIAG: Relay received message from HuggingFace, queued for Telegram.", flush=True)
    return jsonify({"status": "queued"}), 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# 🔐 SECURE CREDENTIALS & PROXY (Loads from Render Environment Variables)
# ==============================================================================
load_dotenv()

# (Cloudflare proxy removed — calling Telegram directly is simpler and was the
# more reliable path when we diagnosed this exact pattern on the other bot)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

TELEGRAM_JOIN_URL = "https://t.me/+hQ7zz0wWfJ02YzFl"

# Shared session = connection reuse for all outbound telemetry calls
_telemetry_session = requests.Session()

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 
    'LINK/USDT', 'DOT/USDT', 'AVAX/USDT', 'ATOM/USDT'
]

# ==============================================================================
# 🔥 HOLY GRAIL PARAMETERS (Strict Risk Management)
# ==============================================================================
TIMEFRAME = '15m'  # Execution timeframe — matches gos-s_eye.py's freqtrade timeframe. 1h is fetched separately as informative.
HARD_SL_PCT = 0.13           # 13% Strict Chart SL
TRUE_RISK_PCT = 0.06         # 6% Max Portfolio Risk
TRAILING_START_PCT = 0.04    # Trailing activates at +4%
TRAILING_GAP_PCT = 0.001     # Native 0.1% breathing space below peak
TIME_BAILOUT_HOURS = 8.0     

STARTING_BALANCE = 1000.0
WALLET_FILE = "virtual_wallet.txt"
LEDGER_FILE = "signals_logged.txt"

market_states = {
    symbol: {
        'active_trade': False, 'side': None, 'entry_price': 0.0, 'sl_price': 0.0,
        'target': 0.0, 'peak_price': 0.0, 'risk_usd': 0.0, 'volume_usd': 0.0,
        'trailing_active': False, 'entry_time': None, 'notion_page_id': None
    } for symbol in SYMBOLS
}

# ==============================================================================
# 🚀 THE BULLETPROOF MESSAGE QUEUE ENGINE (ZERO SLIPPAGE)
# ==============================================================================
telemetry_queue = queue.Queue()

def telemetry_worker():
    """Background Worker: Executes API calls without freezing the trading loop"""
    print("📡 Background Telemetry Worker Online.", flush=True)
    while True:
        try:
            task = telemetry_queue.get()
            task_type = task[0]

            if task_type == 'telegram':
                _, message = task
                if TELEGRAM_TOKEN and CHAT_ID:
                    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
                    sent = False
                    for attempt in range(4):
                        try:
                            resp = _telemetry_session.post(url, json=payload, timeout=20.0)
                            if resp.status_code == 200:
                                print(f"✅ DIAG: Telegram sent OK (HTTP 200)", flush=True)
                                sent = True
                                break
                            else:
                                print(f"🚨 DIAG REJECTED: HTTP {resp.status_code} | Body: {resp.text[:300]}", flush=True)
                                break  # Telegram said no — retrying won't help, it's not a network issue
                        except requests.exceptions.SSLError as e:
                            print(f"🚨 DIAG SSL_HANDSHAKE_FAILED (attempt {attempt+1}/4): {e}", flush=True)
                        except requests.exceptions.ConnectTimeout as e:
                            print(f"🚨 DIAG CONNECT_TIMEOUT (attempt {attempt+1}/4): {e}", flush=True)
                        except requests.exceptions.ReadTimeout as e:
                            print(f"🚨 DIAG READ_TIMEOUT (attempt {attempt+1}/4): {e}", flush=True)
                        except requests.exceptions.ConnectionError as e:
                            print(f"🚨 DIAG CONNECTION_ERROR (attempt {attempt+1}/4): {e}", flush=True)
                        except Exception as e:
                            print(f"🚨 DIAG UNKNOWN_ERROR (attempt {attempt+1}/4): {type(e).__name__}: {e}", flush=True)
                        time.sleep(5 + attempt * 5)
                    if not sent:
                        print(f"❌ DIAG: Telegram send failed after 4 attempts.", flush=True)

            elif task_type == 'notion_open':
                _, trade_id, asset, side, entry_price, sl_price, target_price = task
                if NOTION_TOKEN and NOTION_DATABASE_ID:
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
                        res = requests.post(url, headers=headers, json=data, timeout=15.0)
                        if res.status_code == 200:
                            page_id = res.json().get("id")
                            market_states[asset]['notion_page_id'] = page_id
                    except: pass

            elif task_type == 'notion_patch':
                _, page_id, data = task
                if NOTION_TOKEN and page_id:
                    url = f"https://api.notion.com/v1/pages/{page_id}"
                    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
                    for attempt in range(3):
                        try:
                            requests.patch(url, headers=headers, json=data, timeout=15.0).raise_for_status()
                            break
                        except: time.sleep(3)

            elif task_type == 'twitter':
                _, tweet_text = task
                if all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
                    try:
                        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
                        client.create_tweet(text=tweet_text, user_auth=True)
                    except Exception as e:
                        print(f"Twitter Post Silently Failed: {e}", flush=True)

            telemetry_queue.task_done()
            time.sleep(1)
            
        except Exception as e:
            print(f"Telemetry Worker Crashed/Recovered: {e}", flush=True)
            time.sleep(2)

# Helpers to put tasks in Queue instantly (Zero Delay for Trading Engine)
def send_telegram_alert(message):
    telemetry_queue.put(('telegram', message))

def notion_open_trade_async(trade_id, asset, side, entry_price, sl_price, target_price):
    telemetry_queue.put(('notion_open', trade_id, asset, side, entry_price, sl_price, target_price))

def notion_update_trailing(page_id, dynamic_sl):
    if page_id:
        data = {"properties": {"Trailing Active": {"checkbox": True}, "Dynamic Floor SL": {"number": float(dynamic_sl)}}}
        telemetry_queue.put(('notion_patch', page_id, data))

def notion_close_trade(page_id, result_tag):
    if page_id:
        data = {"properties": {"Status": {"select": {"name": "CLOSED"}}, "Result": {"select": {"name": result_tag}}}}
        telemetry_queue.put(('notion_patch', page_id, data))

def delayed_twitter_post(tweet_text, delay_seconds=600):
    threading.Timer(delay_seconds, lambda: telemetry_queue.put(('twitter', tweet_text))).start()

# ==============================================================================
# 🗃️ VIRTUAL WALLET ENGINE
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
# 🧠 GOD'S EYE MASTER SCANNER (SMC / FVG LOGIC) — 15m execution + 1h informative
# Mirrors gos-s_eye.py's populate_indicators/populate_entry_trend exactly:
#   - 1h candles -> ema_50_1h, ema_200_1h, rsi_1h, adx_1h, res_24h_1h, ema_dynamic_1h
#   - 15m candles -> ema_50 (native), volume_ma, bb_width, bb_width_mean, FVG
#   - 1h values are merged onto 15m via forward-fill (same as freqtrade's
#     merge_informative_pair with ffill=True), so every 15m candle "sees" the
#     most recently CLOSED 1h candle's values — no lookahead.
# ==============================================================================
def scan_markets():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🦅 Scanning Core Matrices...", flush=True)

    for symbol in SYMBOLS:
        try:
            # --- Fetch 1h (informative) candles ---
            ohlcv_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=500)
            df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            df_1h['ema_50_1h'] = ta.ema(df_1h['close'], length=50)
            df_1h['ema_200_1h'] = ta.ema(df_1h['close'], length=200)
            df_1h['rsi_1h'] = ta.rsi(df_1h['close'], length=14)
            adx_1h_df = ta.adx(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
            df_1h['adx_1h'] = adx_1h_df['ADX_14'] if adx_1h_df is not None else np.nan
            df_1h['res_24h_1h'] = df_1h['high'].rolling(window=24).max().shift(1)
            df_1h['ema_dynamic_1h'] = df_1h['close'].ewm(span=150, adjust=False).mean()

            inf_cols = ['timestamp', 'ema_50_1h', 'ema_200_1h', 'rsi_1h', 'adx_1h', 'res_24h_1h', 'ema_dynamic_1h']
            df_1h_merge = df_1h[inf_cols].copy()

            # --- Fetch 15m (execution) candles ---
            ohlcv_15m = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=500)
            df = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            df['ema_50'] = ta.ema(df['close'], length=50)
            df['volume_ma'] = df['volume'].rolling(window=96).mean()

            bb = ta.bbands(df['close'], length=20, std=2)
            if bb is not None and not bb.empty:
                bbu = [c for c in bb.columns if 'BBU' in c][0]
                bbl = [c for c in bb.columns if 'BBL' in c][0]
                bbm = [c for c in bb.columns if 'BBM' in c][0]
                df['bb_width'] = (bb[bbu] - bb[bbl]) / bb[bbm]
                df['bb_width_mean'] = df['bb_width'].rolling(20).mean()
            else:
                df['bb_width'] = 0; df['bb_width_mean'] = 0

            bear_cond = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['open'].shift(1))
            df['bearish_fvg_bottom'] = np.where(bear_cond, df['high'], np.nan)
            df['bearish_fvg_top'] = np.where(bear_cond, df['low'].shift(2), np.nan)
            df['bearish_fvg_bottom'] = pd.Series(df['bearish_fvg_bottom']).ffill(limit=48).values
            df['bearish_fvg_top'] = pd.Series(df['bearish_fvg_top']).ffill(limit=48).values

            # --- Merge 1h onto 15m: as-of backward merge = forward-fill the
            # most recently CLOSED 1h candle onto each 15m candle (no lookahead) ---
            df = df.sort_values('timestamp')
            df_1h_merge = df_1h_merge.sort_values('timestamp')
            df = pd.merge_asof(df, df_1h_merge, on='timestamp', direction='backward')

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

                if profit_pct >= TRAILING_START_PCT:
                    if not state['trailing_active']:
                        state['trailing_active'] = True
                        msg = (f"🛡️ <b>GOD'S EYE: TRAILING PROTECTION ACTIVATED</b>\n\n"
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

                is_sl_hit = (side == 'LONG' and latest['low'] <= state['sl_price']) or (side == 'SHORT' and latest['high'] >= state['sl_price'])

                if is_sl_hit:
                    exit_price = state['sl_price']
                    actual_profit_pct = (exit_price - entry) / entry if side == 'LONG' else (entry - exit_price) / entry
                    pnl_usd = state['volume_usd'] * actual_profit_pct

                    set_virtual_balance(get_virtual_balance() + pnl_usd)

                    result_tag = "trailing_stop_loss" if state['trailing_active'] else "stop_loss"
                    notion_close_trade(state['notion_page_id'], result_tag)

                    if state['trailing_active']:
                        msg = (f"🎉 <b>GOD'S EYE: TRAILING PROFIT SECURED</b> 🎉\n\n"
                               f"🪙 Asset: {symbol} | {side}\n🎯 Entry: ${round(entry, 4)}\n"
                               f"💰 Exit: ${round(exit_price, 4)}\n📈 Net Profit: +{round(actual_profit_pct*100, 2)}%\n")
                        send_telegram_alert(msg)

                        t_msg = (f"🎉 GOD'S EYE: TRAILING PROFIT SECURED! 🎉\n\n🪙 Asset: #{clean_symbol} | {side}\n"
                                 f"📈 Net Profit: +{round(actual_profit_pct*100, 2)}% NET ✅\n\n"
                                 f"Automated 0.1% floor locked the peak flawlessly. 💸\n\nVIP: {TELEGRAM_JOIN_URL}")
                        delayed_twitter_post(t_msg, 600)

                    else:
                        msg = (f"💥 <b>GOD'S EYE: STOP LOSS EXECUTION</b> 💥\n\n"
                               f"🪙 Asset: {symbol} | {side}\n🛑 Exit Price: ${round(exit_price, 4)}\n"
                               f"📉 Net Chart Loss: {round(actual_profit_pct*100, 2)}%\n"
                               f"🛡️ Portfolio Impact: Protected.")
                        send_telegram_alert(msg)

                        t_msg = (f"💥 GOD'S EYE RISK SHIELD: POSITION TERMINATED 💥\n\n🪙 Asset: #{clean_symbol} | {side}\n"
                                 f"📉 Chart Drop: {round(actual_profit_pct*100, 2)}%\n🛡️ Exact Capital Control.\n\nVIP: {TELEGRAM_JOIN_URL}")
                        delayed_twitter_post(t_msg, 600)

                    market_states[symbol] = {k: False if type(v) == bool else None for k, v in state.items()}

                continue

            # 🔎 2. ENTRY SCANNER
            t_time = str(curr['timestamp'])
            signal_id = f"{symbol.replace('/', '_')}_{t_time}"
            trade_uid = str(int(time.time()))

            if is_signal_logged(signal_id): continue

            req_cols = ['ema_50', 'ema_50_1h', 'ema_200_1h', 'rsi_1h', 'bb_width', 'bb_width_mean',
                        'res_24h_1h', 'volume_ma', 'ema_dynamic_1h', 'adx_1h', 'bearish_fvg_top', 'bearish_fvg_bottom']
            if any(pd.isna(curr.get(col, np.nan)) for col in req_cols): continue

            risk_usd, volume_usd = calculate_true_risk_volume()

            # 🟢 LONG TRIGGER — matches gos-s_eye.py populate_entry_trend exactly
            if (curr['ema_50_1h'] > curr['ema_200_1h'] and curr['close'] > curr['ema_50_1h'] and
                curr['close'] > curr['res_24h_1h'] and curr['bb_width'] < (curr['bb_width_mean'] * 1.25) and
                curr['volume'] > (curr['volume_ma'] * 1.5) and 55 < curr['rsi_1h'] < 80 and
                curr['adx_1h'] > 22 and curr['close'] > curr['ema_50']):

                append_to_ledger(signal_id)
                sl_price = round(curr['close'] * (1 - HARD_SL_PCT), 4)
                target_price = round(curr['close'] * 1.04, 4)

                state.update({
                    'active_trade': True, 'side': 'LONG', 'entry_price': curr['close'],
                    'sl_price': sl_price, 'target': target_price, 'peak_price': curr['close'],
                    'risk_usd': risk_usd, 'volume_usd': volume_usd, 'trailing_active': False,
                    'entry_time': datetime.now()
                })

                notion_open_trade_async(trade_uid, symbol, "LONG", curr['close'], sl_price, target_price)

                msg = (f"🚨 <b>GOD'S EYE ALGO: NEW POSITION EXECUTED</b>\n\n"
                       f"🪙 Asset: {symbol}\n🟢 Direction: LONG\n⚡ Leverage: 5.0x\n"
                       f"🎯 Entry Price: ${curr['close']}\n🛑 Chart Stop-Loss: -13.0%\n")
                send_telegram_alert(msg)

                t_msg = (f"🚨 GOD'S EYE ALGO: NEW POSITION INJECTED 🚨\n\n🪙 Asset: #{clean_symbol}\n🟢 Type: LONG\n"
                         f"🎯 Entry: ${curr['close']}\n🛡️ Risk: Strict Protection\n\nVIP Alerts: {TELEGRAM_JOIN_URL}")
                delayed_twitter_post(t_msg, 600)

            # 🔴 SHORT TRIGGER (FVG retest) — matches gos-s_eye.py's fvg_retest_signal exactly
            else:
                fvg_retest_signal = (
                    (curr['close'] < curr['ema_dynamic_1h']) and
                    (curr['adx_1h'] > 25) and
                    (not pd.isna(curr['bearish_fvg_bottom'])) and
                    (curr['high'] >= curr['bearish_fvg_bottom']) and
                    (curr['close'] <= curr['bearish_fvg_top']) and
                    (curr['rsi_1h'] > 35) and
                    (curr['volume'] > 0)
                )
                prev_fvg_retest_signal = (
                    (prev['close'] < prev['ema_dynamic_1h']) and
                    (prev['adx_1h'] > 25) and
                    (not pd.isna(prev['bearish_fvg_bottom'])) and
                    (prev['high'] >= prev['bearish_fvg_bottom']) and
                    (prev['close'] <= prev['bearish_fvg_top']) and
                    (prev['rsi_1h'] > 35) and
                    (prev['volume'] > 0)
                )

                # Only trigger on the transition False -> True (same as .shift(1) check in gos-s_eye.py)
                if fvg_retest_signal and not prev_fvg_retest_signal:
                    append_to_ledger(signal_id)
                    sl_price = round(curr['close'] * (1 + HARD_SL_PCT), 4)
                    target_price = round(curr['close'] * 0.96, 4)

                    state.update({
                        'active_trade': True, 'side': 'SHORT', 'entry_price': curr['close'],
                        'sl_price': sl_price, 'target': target_price, 'peak_price': curr['close'],
                        'risk_usd': risk_usd, 'volume_usd': volume_usd, 'trailing_active': False,
                        'entry_time': datetime.now()
                    })

                    notion_open_trade_async(trade_uid, symbol, "SHORT", curr['close'], sl_price, target_price)

                    msg = (f"🚨 <b>GOD'S EYE ALGO: NEW POSITION EXECUTED</b>\n\n"
                           f"🪙 Asset: {symbol}\n🔴 Direction: SHORT\n⚡ Leverage: 5.0x\n"
                           f"🎯 Entry Price: ${curr['close']}\n🛑 Chart Stop-Loss: -13.0%\n")
                    send_telegram_alert(msg)

                    t_msg = (f"🚨 GOD'S EYE ALGO: NEW POSITION INJECTED 🚨\n\n🪙 Asset: #{clean_symbol}\n🔴 Type: SHORT\n"
                             f"🎯 Entry: ${curr['close']}\n🛡️ Risk: Strict Protection\n\nVIP Alerts: {TELEGRAM_JOIN_URL}")
                    delayed_twitter_post(t_msg, 600)

            time.sleep(1)

        except Exception as e:
            print(f"Error scanning {symbol}: {e}", flush=True)

def run_bot():
    print("\n🦅 GOD'S EYE MASTER ENGINE RUNNING SILENTLY...", flush=True)
    while True:
        scan_markets()
        time.sleep(15)

if __name__ == "__main__":
    # Start Flask to keep Render Web Service alive
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start the robust Telemetry Message Queue Worker
    threading.Thread(target=telemetry_worker, daemon=True).start()
    
    time.sleep(3)
    
    # Start the actual scanning engine
    run_bot()
