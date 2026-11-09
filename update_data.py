import json
import datetime as dt
import yfinance as yf

TICKERS = ["CIGI", "J", "WSPOF", "VEOEF"]
now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=730)

out = {"updated": now.isoformat(), "series": {}, "mcap": {}}

for t in TICKERS:
    tk = yf.Ticker(t)
    close = tk.history(period="max", interval="1d", auto_adjust=False)["Close"].dropna()
    close.index = close.index.tz_localize(None)
    cut = cutoff.replace(tzinfo=None)
    old = close[close.index < cut].resample("W").last().dropna()
    recent = close[close.index >= cut]
    merged = list(old.items()) + list(recent.items())
    out["series"][t] = [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in merged]
    try:
        out["mcap"][t] = float(tk.fast_info["market_cap"])
    except Exception:
        out["mcap"][t] = None

with open("data.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))
