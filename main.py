# ==============================================================================
# 🦅 GOD'S EYE - RENDER RELAY SERVER (DUMB POSTMAN)
# Only routes Telegram & Discord messages. ZERO trading logic inside.
# ==============================================================================

import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🟢 1. ANTI-SLEEP HEALTH CHECK (Render ko zinda rakhne ke liye)
@app.route('/')
def home():
    return "🦅 GOD'S EYE RELAY SERVER IS 100% ACTIVE. (Trading logic disabled)"

# 🔵 2. TELEGRAM ROUTER (Hugging Face se direct Telegram)
@app.route('/bot<token>/<method>', methods=['POST'])
def telegram_proxy(token, method):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        # Hugging Face se jo bhi JSON aaya, wahi exactly Telegram ko bhej do
        resp = requests.post(url, json=request.get_json(silent=True), timeout=10)
        return (resp.text, resp.status_code, resp.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔴 3. DISCORD ROUTER (Future-proof Discord routing)
@app.route('/discord/<path:webhook_path>', methods=['POST'])
def discord_proxy(webhook_path):
    # webhook_path will capture everything after /discord/ 
    # e.g., api/webhooks/1234/abcd
    url = f"https://discord.com/{webhook_path}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, json=request.get_json(silent=True), headers=headers, timeout=10)
        return (resp.text, resp.status_code, resp.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Render assigns a dynamic port via environment variables
    port = int(os.environ.get("PORT", 10000))
    # Flask runs continuously, keeping the server awake 24/7
    app.run(host='0.0.0.0', port=port)
