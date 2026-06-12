import os
import time
import requests
import ccxt
import hmac
import hashlib
import base64
import urllib.parse
import secrets
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "GOD'S EYE Omni-Channel Enterprise Engine [V8] is active 24/7."

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

# V8 Mathematical Parameters
PIVOT_LOOKBACK = 3
SWEEP_LOOKBACK = 8
RVOL_MULT = 1.2
BODY_RATIO_MIN = 0.45
ZONE_BUFFER_PCT = 0.002 # 0.2%

market_states = {
    symbol: {
        'bull_ob': None, # Dict: {'low': float, 'high': float}
        'bear_ob': None,
        'last_signal_time': None
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
        "oauth_consumer_key": X_API_KEY,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_token": X_ACCESS_TOKEN,
        "oauth_version": "1.0"
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
    auth_header = "OAuth " + ", ".join(auth_header_parts)
    
    headers = {"Authorization": auth_header, "Content-Type": "application/json"}
    payload = {"text": tweet_text}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code == 201:
            print("[+] Automated Marketing Post successfully fired on X.com!")
    except Exception as e:
        pass

# ==============================================================================
# 📢 DISTRIBUTION CORES
# ==============================================================================
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        pass

def push_signal_to_notion_journal(asset, signal_type, entry_price, sl, tp):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
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
            "Stop Loss": {"number": float(sl)},
            "Take Profit": {"number": float(tp)},
            "Status": {"select": {"name": "Active"}}
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
        "⚡ *GOD'S EYE V8 ENGINE ONLINE*\n"
        "───────────────────────\n"
        "🌐 *Status:* Cloud Active\n"
        f"📊 *Execution:* {TIMEFRAME} Timeframe\n"
        f"🛡️ *Risk Target:* Strict 1:2 R:R\n"
        f"🎯 *Assets:* `{len(SYMBOLS)} Coins`\n"
        "───────────────────────\n"
        f"📡 _Monitoring: [{coins_str}]_"
    )
    send_telegram_alert(startup_msg)

# ==============================================================================
# 🧠 CORE MATHEMATICAL ENGINE (V8 TRANSLATION)
# ==============================================================================
def check_market_signals(symbol):
    state = market_states[symbol]
    
    try:
        # 1. Fetch HTF Daily EMA
        daily_bars = exchange.fetch_ohlcv(symbol, '1d', limit=100)
        if len(daily_bars) < 50: return
        daily_closes = [b[4] for b in daily_bars]
        daily_ema_50 = calc_ema(daily_closes, 50)
        
        # 2. Fetch 4H Execution Data
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        if len(bars) < 25: return
        
        # Array Mapping
        opens = [b[1] for b in bars]
        highs = [b[2] for b in bars]
        lows = [b[3] for b in bars]
        closes = [b[4] for b in bars]
        vols = [b[5] for b in bars]
        
        # Current Candle Stats
        curr_time = bars[-1][0]
        curr_open, curr_high, curr_low, curr_close, curr_vol = bars[-1][1:6]
        
        # HTF Trend Logic
        is_htf_bullish = curr_close > daily_ema_50
        is_htf_bearish = curr_close < daily_ema_50
        
        # 3. Pivot & OB Scanning (Looking backward from the finalized candle)
        # Using Index -2 as the current bar being checked to avoid repainting on active candle
        idx = -2 - PIVOT_LOOKBACK 
        
        pivot_high_val = highs[idx]
        pivot_low_val = lows[idx]
        
        # Check 3 bars left and 3 bars right
        is_pivot_low = all(pivot_low_val <= lows[idx-i] for i in range(1, PIVOT_LOOKBACK+1)) and \
                       all(pivot_low_val <= lows[idx+i] for i in range(1, PIVOT_LOOKBACK+1))
                       
        is_pivot_high = all(pivot_high_val >= highs[idx-i] for i in range(1, PIVOT_LOOKBACK+1)) and \
                        all(pivot_high_val >= highs[idx+i] for i in range(1, PIVOT_LOOKBACK+1))

        # Sweep & FVG Checks
        if is_pivot_low:
            lowest_recent = min(lows[idx-SWEEP_LOOKBACK:idx]) if len(lows[:idx]) >= SWEEP_LOOKBACK else pivot_low_val
            was_swept = pivot_low_val < lowest_recent
            has_fvg = lows[idx-2] > highs[idx] if len(lows) > abs(idx-2) else False
            
            if was_swept and has_fvg:
                state['bull_ob'] = {'low': pivot_low_val, 'high': max(opens[idx], closes[idx])}

        if is_pivot_high:
            highest_recent = max(highs[idx-SWEEP_LOOKBACK:idx]) if len(highs[:idx]) >= SWEEP_LOOKBACK else pivot_high_val
            was_swept = pivot_high_val > highest_recent
            has_fvg = highs[idx-2] < lows[idx] if len(highs) > abs(idx-2) else False
            
            if was_swept and has_fvg:
                state['bear_ob'] = {'high': pivot_high_val, 'low': min(opens[idx], closes[idx])}

        # 4. Confirmation Validation Math
        vol_sma = calc_sma(vols[:-1], 10) # 10-period SMA excluding current active candle
        rvol = (curr_vol / vol_sma) if vol_sma > 0 else 1.0
        is_high_vol = rvol >= RVOL_MULT
        
        candle_range = curr_high - curr_low
        candle_body = abs(curr_close - curr_open)
        body_ratio = (candle_body / candle_range) if candle_range > 0 else 0
        is_solid_body = body_ratio >= BODY_RATIO_MIN
        
        is_green = curr_close > curr_open
        is_red = curr_close < curr_open
        
        buffer_val = curr_close * ZONE_BUFFER_PCT
        
        # 5. Signal Triggers
        buy_triggered = False
        sell_triggered = False
        
        # LONG CHECK
        if state['bull_ob'] and is_htf_bullish:
            ob = state['bull_ob']
            touch_zone = (curr_low <= (ob['high'] + buffer_val)) and (curr_high >= ob['low'])
            
            if touch_zone and is_green and is_high_vol and is_solid_body:
                buy_triggered = True
                state['bull_ob'] = None # Clear OB on mitigation
                
        # SHORT CHECK
        if state['bear_ob'] and is_htf_bearish:
            ob = state['bear_ob']
            touch_zone = (curr_high >= (ob['low'] - buffer_val)) and (curr_low <= ob['high'])
            
            if touch_zone and is_red and is_high_vol and is_solid_body:
                sell_triggered = True
                state['bear_ob'] = None # Clear OB on mitigation

        # 6. Execution Logging & ATR Brackets
        if (buy_triggered or sell_triggered) and state['last_signal_time'] != curr_time:
            state['last_signal_time'] = curr_time
            coin_name = symbol.split('/')[0]
            current_atr = calc_atr(highs, lows, closes, 14)
            
            if buy_triggered:
                sl = curr_close - (current_atr * 2.0)
                tp = curr_close + (current_atr * 4.0)
                msg = f"🟢 *GOD'S EYE BUY TRIGGERED!*\nAsset: #{coin_name}\nPrice: {curr_close}\nStop Loss: {sl:.4f}\nTake Profit: {tp:.4f}\n📌 _Logged to Notion_"
                
                send_telegram_alert(msg)
                push_signal_to_notion_journal(coin_name, "LONG", curr_close, sl, tp)
                
                tweet = f"👁️ GOD'S EYE ALGO SETUP ALERT\n\n🟢 LONG (BUY) TRIGGERED: #{coin_name}\n📊 Entry: {curr_close}\n🎯 Target: {tp:.4f}\n\nStrict 1:2 R:R Execution."
                post_to_x_platform(tweet)
                
            elif sell_triggered:
                sl = curr_close + (current_atr * 2.0)
                tp = curr_close - (current_atr * 4.0)
                msg = f"🔴 *GOD'S EYE SELL TRIGGERED!*\nAsset: #{coin_name}\nPrice: {curr_close}\nStop Loss: {sl:.4f}\nTake Profit: {tp:.4f}\n📌 _Logged to Notion_"
                
                send_telegram_alert(msg)
                push_signal_to_notion_journal(coin_name, "SHORT", curr_close, sl, tp)
                
                tweet = f"👁️ GOD'S EYE ALGO SETUP ALERT\n\n🔴 SHORT (SELL) TRIGGERED: #{coin_name}\n📊 Entry: {curr_close}\n🎯 Target: {tp:.4f}\n\nStrict 1:2 R:R Execution."
                post_to_x_platform(tweet)
                
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")

def engine_loop():
    send_deployment_success()
    while True:
        for symbol in SYMBOLS:
            check_market_signals(symbol)
            time.sleep(2) # Prevent CCXT Rate Limiting
        time.sleep(60) # Array cycle rest

if __name__ == "__main__":
    print("Initializing Flask server thread...")
    t = Thread(target=run_flask)
    t.start()
    
    print("Launching Omni-Channel High-Volume Automated Array...")
    engine_loop()
