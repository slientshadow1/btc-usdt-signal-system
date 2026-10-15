import os, time, threading
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
DATA_URL = os.getenv("DATA_URL", "https://www.okx.com/api/v5/market/candles")
INST_ID = os.getenv("INST_ID", "BTC-USDT")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
last_sent_signal, last_sent_at = None, 0
session = requests.Session()
session.headers.update({"User-Agent": "BTC-USDT-Signal-Lab/1.0"})

def candles(bar, limit=100):
    r = session.get(DATA_URL, params={"instId": INST_ID, "bar": bar, "limit": str(limit)}, timeout=12)
    r.raise_for_status()
    payload = r.json()
    if payload.get("code") not in (None, "0"):
        raise RuntimeError("Provider error: " + str(payload.get("msg", "unknown")))
    rows = payload.get("data") or []
    if len(rows) < 35:
        raise RuntimeError("Provider returned too few candles")
    rows = list(reversed(rows))[0:-1]  # remove newest possibly-forming candle
    closes = [float(row[4]) for row in rows]
    return closes

def ema(vals, period):
    a = 2 / (period + 1)
    out = vals[0]
    for v in vals[1:]:
        out = a * v + (1-a) * out
    return out

def macd_hist(vals):
    def series(period):
        a = 2 / (period + 1)
        out = [vals[0]]
        for v in vals[1:]:
            out.append(a*v + (1-a)*out[-1])
        return out
    fast, slow = series(12), series(26)
    line = [x-y for x,y in zip(fast,slow)]
    a = 2/(9+1)
    sig = [line[0]]
    for v in line[1:]:
        sig.append(a*v + (1-a)*sig[-1])
    return line[-1] - sig[-1]

def analyse():
    m1, m5 = candles("1m"), candles("5m")
    trend_fast, trend_slow = ema(m5,9), ema(m5,21)
    entry_fast, entry_slow = ema(m1,5), ema(m1,10)
    hist = macd_hist(m1)
    trend = "BULLISH" if trend_fast > trend_slow else "BEARISH" if trend_fast < trend_slow else "MIXED"
    signal = "POTENTIAL BUY" if trend == "BULLISH" and entry_fast > entry_slow and hist > 0 else "POTENTIAL SELL" if trend == "BEARISH" and entry_fast < entry_slow and hist < 0 else "WAIT"
    return {"symbol": INST_ID, "price": m1[-1], "trend_m5": trend, "ema5_m1": entry_fast, "ema10_m1": entry_slow, "macd_hist_m1": hist, "signal": signal, "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": "Experimental, unbacktested rules; not financial advice."}

def send_telegram(message):
    if not TOKEN or not CHAT_ID: return False
    r = session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": message}, timeout=12)
    r.raise_for_status()
    if not r.json().get("ok"): raise RuntimeError("Telegram rejected message")
    return True

def monitor():
    global last_sent_signal, last_sent_at
    while True:
        try:
            d = analyse()
            now = time.time()
            if d["signal"] != last_sent_signal and now-last_sent_at >= 600:
                if send_telegram("BTC/USDT SIGNAL LAB\nSignal: "+d["signal"]+"\nPrice: %.2f USDT\nM5 trend: "%d["price"]+d["trend_m5"]+"\nExperimental only; confirm independently."):
                    last_sent_signal, last_sent_at = d["signal"], now
        except Exception as e:
            app.logger.warning("Data/Telegram issue: %s", e)
        time.sleep(POLL_SECONDS)

@app.route("/")
def home():
    return render_template_string(PAGE)

@app.route("/api/signal")
def api_signal():
    try: return jsonify({"ok": True, "result": analyse()})
    except Exception as e:
        app.logger.exception("Market data unavailable")
        return jsonify({"ok": False, "error": str(e)}), 502

@app.route("/health")
def health(): return jsonify({"ok": True, "service": "BTC/USDT Signal Lab"})

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BTC/USDT Signal Lab</title><style>body{font-family:system-ui;margin:0;background:#101827;color:#f4f7fb}main{max-width:680px;margin:auto;padding:18px}.card{background:#1b2638;border-radius:16px;padding:16px;margin:12px 0}.muted{color:#b9c5d7;font-size:14px}.price{font-size:30px;font-weight:750}.signal{font-size:24px;font-weight:800}button{border:0;border-radius:10px;padding:12px 16px;font-weight:700}.warn{color:#ffd98a}.error{color:#ffaaa8}</style></head><body><main><h1>BTC/USDT Signal Lab</h1><div class="muted">Server-based data · M1 entry indicators · M5 trend filter</div><div class="card"><div class="muted">BTC/USDT price</div><div class="price" id="price">Loading…</div><div class="muted" id="updated"></div></div><div class="card"><div class="muted">Experimental signal</div><div class="signal" id="signal">Checking…</div><p>M5 trend: <b id="trend">—</b></p><p>M1 MACD histogram: <b id="macd">—</b></p><button onclick="refresh()">Refresh now</button><p id="status" class="muted">Connecting to server…</p></div><div class="card warn"><b>Risk notice</b><p>This is an experimental educational indicator, not a proven strategy or financial advice. It does not place trades. Never risk money based only on this signal.</p></div></main><script>async function refresh(){let s=document.getElementById('status');s.textContent='Updating…';s.className='muted';try{let r=await fetch('/api/signal',{cache:'no-store'});let j=await r.json();if(!r.ok||!j.ok)throw Error(j.error||'Server could not retrieve data');let d=j.result;document.getElementById('price').textContent=Number(d.price).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+' USDT';document.getElementById('signal').textContent=d.signal;document.getElementById('trend').textContent=d.trend_m5;document.getElementById('macd').textContent=Number(d.macd_hist_m1).toFixed(4);document.getElementById('updated').textContent='Updated UTC: '+d.updated_utc;s.textContent='Server received market data. Experimental signal only.'}catch(e){s.textContent='Data unavailable: '+e.message;s.className='error'}}refresh();setInterval(refresh,60000);</script></body></html>"""

if __name__ == "__main__":
    if TOKEN and CHAT_ID:
        threading.Thread(target=monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
