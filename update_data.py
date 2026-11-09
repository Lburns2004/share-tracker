
import json
import datetime as dt
import yfinance as yf

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

TICKERS = ["CIGI", "J", "WSPOF", "VEOEF"]

now = dt.datetime.now(dt.timezone.utc)

# Keep 2 years of historical daily data
history_cutoff = now - dt.timedelta(days=730)

# Use intraday data for the most recent 60 days
intraday_cutoff = now - dt.timedelta(days=60)

out = {
    "updated": now.isoformat(),
    "series": {},
    "mcap": {}
}


# --------------------------------------------------
# HELPER: FORMAT TIMESTAMPS
# --------------------------------------------------

def format_timestamp(timestamp):
    """Convert timestamps into UTC ISO format."""

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    else:
        timestamp = timestamp.astimezone(dt.timezone.utc)

    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------
# DOWNLOAD SHARE PRICE DATA
# --------------------------------------------------

for ticker in TICKERS:

    print(f"Downloading {ticker}...")

    stock = yf.Ticker(ticker)

    # ----------------------------------------------
    # 1. DOWNLOAD LONG-TERM DAILY HISTORY
    # ----------------------------------------------

    daily = stock.history(
        period="max",
        interval="1d",
        auto_adjust=False
    )["Close"].dropna()

    if daily.empty:
        raise RuntimeError(
            f"No historical price data returned for {ticker}"
        )

    # Convert index to timezone-aware UTC
    if daily.index.tz is None:
        daily.index = daily.index.tz_localize("UTC")
    else:
        daily.index = daily.index.tz_convert("UTC")

    daily = daily.sort_index()

    # ----------------------------------------------
    # 2. OLDER HISTORY: WEEKLY DATA
    # ----------------------------------------------

    old = daily[
        daily.index < history_cutoff
    ].copy()

    old = old.resample("W").last().dropna()

    # ----------------------------------------------
    # 3. RECENT HISTORY: DAILY DATA
    # ----------------------------------------------

    middle = daily[
        (daily.index >= history_cutoff) &
        (daily.index < intraday_cutoff)
    ].copy()

    # ----------------------------------------------
    # 4. DOWNLOAD INTRADAY DATA
    # ----------------------------------------------

    try:

        intraday = stock.history(
            period="60d",
            interval="5m",
            auto_adjust=False
        )["Close"].dropna()

        if not intraday.empty:

            if intraday.index.tz is None:
                intraday.index = intraday.index.tz_localize("UTC")
            else:
                intraday.index = intraday.index.tz_convert("UTC")

            intraday = intraday.sort_index()

            # Only retain observations within the latest 60 days
            intraday = intraday[
                intraday.index >= intraday_cutoff
            ]

            print(
                f"{ticker}: Using {len(intraday)} "
                "intraday observations"
            )

        else:
            raise RuntimeError("No intraday data returned")

    except Exception as e:

        print(
            f"WARNING: Intraday data unavailable for "
            f"{ticker}: {e}"
        )

        print(f"{ticker}: Falling back to daily prices")

        intraday = daily[
            daily.index >= intraday_cutoff
        ].copy()

    # ----------------------------------------------
    # 5. COMBINE ALL HISTORICAL DATA
    # ----------------------------------------------

    combined = []

    # Older weekly observations
    for timestamp, value in old.items():

        combined.append([
            format_timestamp(timestamp),
            round(float(value), 2)
        ])

    # Recent daily observations
    for timestamp, value in middle.items():

        combined.append([
            format_timestamp(timestamp),
            round(float(value), 2)
        ])

    # Latest intraday observations
    for timestamp, value in intraday.items():

        combined.append([
            format_timestamp(timestamp),
            round(float(value), 2)
        ])

    # Sort chronologically
    combined.sort(key=lambda x: x[0])

    # Remove duplicate timestamps
    unique = {}
    for timestamp, value in combined:
        unique[timestamp] = value

    out["series"][ticker] = [
        [timestamp, value]
        for timestamp, value in unique.items()
    ]

    # ----------------------------------------------
    # 6. GET CURRENT MARKET CAPITALISATION
    # ----------------------------------------------

    try:

        market_cap = stock.fast_info["market_cap"]

        out["mcap"][ticker] = (
            float(market_cap)
            if market_cap is not None
            else None
        )

    except Exception:

        out["mcap"][ticker] = None

    print(
        f"{ticker}: {len(out['series'][ticker])} "
        "total observations saved"
    )


# --------------------------------------------------
# 7. SAVE DATA TO JSON
# --------------------------------------------------

with open("data.json", "w") as f:

    json.dump(
        out,
        f,
        separators=(",", ":")
    )


print("--------------------------------")
print("SHARE PRICE UPDATE COMPLETE")
print(f"Updated: {out['updated']}")
print("--------------------------------")
