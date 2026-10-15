BTC/USDT SERVER-BASED SIGNAL LAB — STARTER

This is a starter package, not a hosted or already-running service.
It moves market-data requests from the phone browser to a Python web server.
It requests public OKX BTC-USDT 1m and 5m candles and displays POTENTIAL BUY,
POTENTIAL SELL, or WAIT using simple experimental EMA/MACD rules.

IMPORTANT: These rules are not backtested and are not financial advice. The app
does not connect to BTCDana, place orders, or guarantee profit. A reachable host
and reachable data provider are still required. Free hosting may sleep or impose limits.

DEPLOYMENT:
1. Upload app.py and requirements.txt to a Python hosting service supporting Flask.
2. Start command: python app.py
3. Configure the host to expose its assigned PORT.
4. Test /health, then open the home page and check /api/signal.
5. If data fails, inspect server logs; the server itself must reach OKX.

OPTIONAL TELEGRAM ALERTS:
1. Create a bot using Telegram's official BotFather.
2. Start a chat with your bot by sending /start.
3. Set private environment variables TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID on the host.
4. Restart/redeploy. The bot sends alerts on signal changes with a cooldown.
Never share your bot token in chat or public code.

ENVIRONMENT VARIABLES:
DATA_URL (default https://www.okx.com/api/v5/market/candles)
INST_ID (default BTC-USDT)
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optional)
POLL_SECONDS (default 60)
