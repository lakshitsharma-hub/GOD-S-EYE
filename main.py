import os
import time
import requests
import ccxt
import hmac
import hashlib
import base64
import urllib.parse
import secrets
from datetime import datetime, timezone
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "GOD'S EYE Omni-Channel Enterprise Engine [V9.0 Production] is active 24/7."

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
TIMEFRAME = '4h'

# V9 Core Strategic Rules
PIVOT_LOOKBACK = 3
SWEEP_LOOKBACK = 8
RVOL_MULT = 1.2
BODY_RATIO_MIN = 0.45
ZONE_BUFFER_PCT = 0.002 
LEDGER_FILE = "signals_logged.txt"

# V9 Telemetry State Framework
market_states = {
    symbol: {
        'bull_ob': None, 
        'bear_ob': None,
        'active_trade': None  # Dict: {'dir': STR, 'entry': FLT, 'sl': FLT, 'tp': FLT, 'be_trigger': FLT, 'stop_moved_to_be': BOOL}
    } for symbol in SYMBOLS
}

# ==============================================================================
# 🧮 LIGHTWEIGHT MATH & INDICATOR FUNCTIONS
# ==============================================================================
def calc_ema(prices, period=50):
    if len(prices) < period: return prices[-1] if prices else 0
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * k + ema
    return ema

def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1: return 0
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        tr_list.append(tr)
    return sum(tr_list[-period:]) / period

def calc_sma(values, period):
    if len(values) < period: return 0
    return sum(values[-period:]) / period

# ==============================================================================
# 💾 FLAT-FILE LEDGER DE-DUPLICATION ENGINE
# ==============================================================================
def is_signal_logged(signal_id):
    if not os.path.exists(LEDGER_FILE):
        return False
    try:
        with open(LEDGER_FILE, 'r') as f:
            return signal_id in f.read().splitlines()
    except:
        return False

def append_to_ledger(signal_id):
    try:
        with open(LEDGER_FILE, 'a') as f:
            f.write(f"{signal_id}\n")
    except:
        pass

# ==============================================================================
# 🐦 DIRECT X (TWITTER) OAUTH 1.0A HANDLER
# ==============================================================================
def post_to_x_platform(tweet_text):
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
        return
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
    
    try:
        requests.post(url, headers=headers, json={"text": tweet_text}, timeout=10)
    except:
        pass

# ==============================================================================
# 📢 DISTRIBUTION CORES
# ==============================================================================
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def push_signal_to_notion_journal(asset, signal_type, entry_price, sl, tp, status="Active"):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Asset": {"title": [{"text": {"content": asset}}]},
            "Signal": {"rich_text": [{"text": {"content": signal_type}}]},
            "Entry": {"number": float(entry_price)},
            "Stop Loss": {"number": float(sl)},
            "Take Profit": {"number": float(tp)},
            "Status": {"select": {"name": status}}
        }
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
        return True
    except:
        return False

def send_deployment_success():
    coins_str = ", ".join([s.split('/')[0] for s in SYMBOLS])
    startup_msg = (
        "⚡ *GOD'S EYE V9.0 PRODUCTION PLATFORM ONLINE*\n"
        "───────────────────────\n"
        "🌐 *Status:* Active & Guarded\n"
        f"📊 *Timeframe:* {TIMEFRAME} Matrix\n"
        "🔒 *Protection:* Dynamic Break-Even Enabled (1.5x ATR)\n"
        "⏱️ *Session Guard:* UTC 07:00-21:00 (Mon-Fri Only)\n"
        "───────────────────────\n"
        f"📡 _Safe Scanning: [{coins_str}]_"
    )
    send_telegram_alert(startup_msg)

# ==============================================================================
# 🧠 CORE MATHEMATICAL ENGINE (V9 ACTIVE LIFECYCLE MANAGEMENT)
# ==============================================================================
def check_market_signals(symbol):
    state = market_states[symbol]
    coin_name = symbol.split('/')[0]
    
    try:
        # 1. TEMPORAL FILTER GUARD (Instantly exit if outside parameters)
        now_utc = datetime.now(timezone.utc)
        current_utc_day = now_utc.isoweekday() # 1 = Monday, 7 = Sunday
        current_utc_hour = now_utc.hour
        
        is_weekday = 1 <= current_utc_day <= 5
        is_active_session = 7 <= current_utc_hour < 21
        
        # 2. FETCH TELEMETRY & TICKER FOR DYNAMIC INTERCEPTION
        ticker = exchange.fetch_ticker(symbol)
        last_price = ticker['last']
        
        # ACTIVE TRADE LIFECYCLE MANAGEMENT LOOP (Evaluates 24/7 once position is active)
        if state['active_trade'] is not None:
            trade = state['active_trade']
            
            if trade['dir'] == "LONG":
                # Check 1.5x ATR Profit Protection Threshold
                if last_price >= trade['be_trigger'] and not trade['stop_moved_to_be']:
                    trade['stop_moved_to_be'] = True
                    trade['sl'] = trade['entry']
                    send_telegram_alert(f"🔒 *PROFIT PROTECTED:* SL moved to Break-Even for #{coin_name} at {trade['entry']:.4f}")
                    push_signal_to_notion_journal(coin_name, "LONG [BE UPDATE]", trade['entry'], trade['sl'], trade['tp'], "Active")
                
                # Check Take-Profit Clear Condition
                elif last_price >= trade['tp']:
                    send_telegram_alert(f"🎉 *TAKE-PROFIT HIT:* #{coin_name} closed at 4.0x ATR Profit ({trade['tp']:.4f})")
                    push_signal_to_notion_journal(coin_name, "LONG [TP HIT]", trade['entry'], trade['sl'], trade['tp'], "Closed")
                    state['active_trade'] = None # Clear state
                    return
                
                # Check Stop-Loss/Break-Even Liquidation Condition
                elif last_price <= trade['sl']:
                    status_str = "Break-Even" if trade['stop_moved_to_be'] else "Initial SL"
                    send_telegram_alert(f"❌ *STOP-LOSS HIT:* #{coin_name} trade closed via {status_str} at {trade['sl']:.4f}")
                    push_signal_to_notion_journal(coin_name, f"LONG [SL HIT - {status_str.upper()}]", trade['entry'], trade['sl'], trade['tp'], "Closed")
                    state['active_trade'] = None
                    return
                    
            elif trade['dir'] == "SHORT":
                if last_price <= trade['be_trigger'] and not trade['stop_moved_to_be']:
                    trade['stop_moved_to_be'] = True
                    trade['sl'] = trade['entry']
                    send_telegram_alert(f"🔒 *PROFIT PROTECTED:* SL moved to Break-Even for #{coin_name} at {trade['entry']:.4f}")
                    push_signal_to_notion_journal(coin_name, "SHORT [BE UPDATE]", trade['entry'], trade['sl'], trade['tp'], "Active")
                
                elif last_price <= trade['tp']:
                    send_telegram_alert(f"🎉 *TAKE-PROFIT HIT:* #{coin_name} closed at 4.0x ATR Profit ({trade['tp']:.4f})")
                    push_signal_to_notion_journal(coin_name, "SHORT [TP HIT]", trade['entry'], trade['sl'], trade['tp'], "Closed")
                    state['active_trade'] = None
                    return
                
                elif last_price >= trade['sl']:
                    status_str = "Break-Even" if trade['stop_moved_to_be'] else "Initial SL"
                    send_telegram_alert(f"❌ *STOP-LOSS HIT:* #{coin_name} trade closed via {status_str} at {trade['sl']:.4f}")
                    push_signal_to_notion_journal(coin_name, f"SHORT [SL HIT - {status_str.upper()}]", trade['entry'], trade['sl'], trade['tp'], "Closed")
                    state['active_trade'] = None
                    return

        # Bypass structural scanning completely if outside core time parameters
        if not (is_weekday and is_active_session):
            return

        # 3. SCAN STRUCTURAL MATRIX (Executed only if inside Session Guards)
        daily_bars = exchange.fetch_ohlcv(symbol, '1d', limit=100)
        if len(daily_bars) < 50: return
        daily_closes = [b[4] for b in daily_bars]
        daily_ema_50 = calc_ema(daily_closes, 50)
        
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        if len(bars) < 30: return
        
        opens, highs, lows, closes, vols = [b[1] for b in bars], [b[2] for b in bars], [b[3] for b in bars], [b[4] for b in bars], [b[5] for b in bars]
        
        # Pivot Identification Indexing
        idx = -2 - PIVOT_LOOKBACK 
        pivot_high_val, pivot_low_val = highs[idx], lows[idx]
        
        is_pivot_low = all(pivot_low_val <= lows[idx-i] for i in range(1, PIVOT_LOOKBACK+1)) and all(pivot_low_val <= lows[idx+i] for i in range(1, PIVOT_LOOKBACK+1))
        is_pivot_high = all(pivot_high_val >= highs[idx-i] for i in range(1, PIVOT_LOOKBACK+1)) and all(pivot_high_val >= highs[idx+i] for i in range(1, PIVOT_LOOKBACK+1))

        # Sweep & FVG Checks with Forward Shift Index Tracking (idx + 2)
        if is_pivot_low:
            lowest_recent = min(lows[idx-SWEEP_LOOKBACK:idx]) if len(lows[:idx]) >= SWEEP_LOOKBACK else pivot_low_val
            if pivot_low_val < lowest_recent and (lows[idx+2] > highs[idx]):
                state['bull_ob'] = {'low': pivot_low_val, 'high': max(opens[idx], closes[idx])}

        if is_pivot_high:
            highest_recent = max(highs[idx-SWEEP_LOOKBACK:idx]) if len(highs[:idx]) >= SWEEP_LOOKBACK else pivot_high_val
            if pivot_high_val > highest_recent and (highs[idx+2] < lows[idx]):
                state['bear_ob'] = {'high': pivot_high_val, 'low': min(opens[idx], closes[idx])}

        # 4. Confirmation Mechanics On Last Finalized Candle (-2)
        t_open, t_high, t_low, t_close, t_vol = opens[-2], highs[-2], lows[-2], closes[-2], vols[-2]
        t_time = str(bars[-2][0]) 
        
        is_htf_bullish = t_close > daily_ema_50
        is_htf_bearish = t_close < daily_ema_50

        vol_sma = calc_sma(vols[:-2], 10) 
        is_high_vol = (t_vol / vol_sma) >= RVOL_MULT if vol_sma > 0 else True
        
        candle_range = t_high - t_low
        is_solid_body = (abs(t_close - t_open) / candle_range) >= BODY_RATIO_MIN if candle_range > 0 else False
        
        buffer_val = t_close * ZONE_BUFFER_PCT
        buy_triggered = False
        sell_triggered = False
        
        # LONG MITIGATION INTERSECTION
        if state['bull_ob'] and is_htf_bullish and state['active_trade'] is None:
            ob = state['bull_ob']
            if (t_low <= (ob['high'] + buffer_val)) and (t_high >= ob['low']) and (t_close > t_open) and is_high_vol and is_solid_body:
                buy_triggered = True
                state['bull_ob'] = None 
                
        # SHORT MITIGATION INTERSECTION
        if state['bear_ob'] and is_htf_bearish and state['active_trade'] is None:
            ob = state['bear_ob']
            if (t_high >= (ob['low'] - buffer_val)) and (t_low <= ob['high']) and (t_close < t_open) and is_high_vol and is_solid_body:
                sell_triggered = True
                state['bear_ob'] = None

        # 5. HARD STATE LEDGER LOCK & EXECUTIONS
        if buy_triggered or sell_triggered:
            signal_id = f"{symbol.replace('/', '_')}_{t_time}"
            if is_signal_logged(signal_id): return
            
            append_to_ledger(signal_id)
            current_atr = calc_atr(highs[:-1], lows[:-1], closes[:-1], 14)
            
            if buy_triggered:
                sl = t_close - (current_atr * 2.0)
                tp = t_close + (current_atr * 4.0)
                be_t = t_close + (current_atr * 1.5)
                
                # Lock telemetry directly into state for continuous tracking
                state['active_trade'] = {
                    'dir': "LONG", 'entry': t_close, 'sl': sl, 'tp': tp, 'be_trigger': be_t, 'stop_moved_to_be': False
                }
                
                send_telegram_alert(f"🟢 *GOD'S EYE BUY TRIGGERED!*\nAsset: #{coin_name}\nPrice: {t_close}\nStop Loss: {sl:.4f}\nTake Profit: {tp:.4f}\n📌 _Active V9 State Array Locked_")
                push_signal_to_notion_journal(coin_name, "LONG [BUY]", t_close, sl, tp, "Active")
                post_to_x_platform(f"👁️ GOD'S EYE ALGO SETUP ALERT\n\n🟢 LONG (BUY) TRIGGERED: #{coin_name}\n📊 Entry: {t_close}\n🎯 Target: {tp:.4f}\n\nV9 Risk Protocols Engaged.\n\n💎 VIP Access ($10 Fee):\nRequest Entry: https://t.me/+hQ7zz0wWfJ02YzFl")
                
            elif sell_triggered:
                sl = t_close + (current_atr * 2.0)
                tp = t_close - (current_atr * 4.0)
                be_t = t_close - (current_atr * 1.5)
                
                state['active_trade'] = {
                    'dir': "SHORT", 'entry': t_close, 'sl': sl, 'tp': tp, 'be_trigger': be_t, 'stop_moved_to_be': False
                }
                
                send_telegram_alert(f"🔴 *GOD'S EYE SELL TRIGGERED!*\nAsset: #{coin_name}\nPrice: {t_close}\nStop Loss: {sl:.4f}\nTake Profit: {tp:.4f}\n📌 _Active V9 State Array Locked_")
                push_signal_to_notion_journal(coin_name, "SHORT [SELL]", t_close, sl, tp, "Active")
                post_to_x_platform(f"👁️ GOD'S EYE ALGO SETUP ALERT\n\n🔴 SHORT (SELL) TRIGGERED: #{coin_name}\n📊 Entry: {t_close}\n🎯 Target: {tp:.4f}\n\nV9 Risk Protocols Engaged.\n\n💎 VIP Access ($10 Fee):\nRequest Entry: https://t.me/+hQ7zz0wWfJ02YzFl")
                
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
