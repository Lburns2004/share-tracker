
import json
import datetime as dt
from pathlib import Path
import yfinance as yf

TICKERS = ["CIGI", "J", "WSPOF", "VEOEF"]

now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=730)

out = {
    "updated": now.isoformat(),
    "series": {},
    "mcap": {}
}

for ticker in TICKERS:
    print(f"Downloading {ticker}...")

    stock = yf.Ticker(ticker)

    close = stock.history(
        period="max",
        interval="15m",
        auto_adjust=False
    )["Close"].dropna()

    if close.empty:
        raise RuntimeError(
            f"No price data returned for {ticker}"
        )

    # Convert index to timezone-naive UTC
    if close.index.tz is not None:
        close.index = close.index.tz_convert(None)

    close = close.sort_index()

    cut = cutoff.replace(tzinfo=None)

    # Older prices: weekly
    old = close[
        close.index < cut
    ].resample("W").last().dropna()

    # Recent prices: daily
    recent = close[
        close.index >= cut
    ]

    merged = list(old.items()) + list(recent.items())

    out["series"][ticker] = [
        [date.strftime("%Y-%m-%d"), round(float(value), 2)]
        for date, value in merged
    ]

    # Market capitalisation
    try:
        out["mcap"][ticker] = float(
            stock.fast_info["market_cap"]
        )
    except Exception:
        out["mcap"][ticker] = None

    print(f"Successfully downloaded {ticker}")

# Write JSON to repository root
Path("data.json").write_text(
    json.dumps(out, separators=(",", ":")),
    encoding="utf-8"
)

print("data.json successfully generated")
