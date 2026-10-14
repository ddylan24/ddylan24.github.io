"""Prediction-market data toolkit (Polymarket + Kalshi public APIs, no keys needed).

Every function here was used in the research notes (P2–N3) and checked against the
venues' own quotes. Import from the quant/ folder:

    import sys; sys.path.insert(0, 'code')
    from pm_toolkit import *
    m = polymarket_markets(closed=True, max_markets=500)
    h = polymarket_history(m.iloc[0].yes_token)
    b = polymarket_book(m.iloc[0].yes_token, m.iloc[0].no_token)

Lessons baked in:
  * Measure prices relative to the SCHEDULED end date, not the close time
    (by-date markets close early when YES happens -> look-ahead). See notes/P2.md.
  * Merge complementary books: a NO bid at q is a YES ask at 1-q. See notes/M3.md.
  * Cluster standard errors by event (outcomes within an event are dependent).
  * Kalshi's settled-market listing only reaches back ~2 months.
"""
import json
import time
import urllib.request

import numpy as np
import pandas as pd

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"


def _get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 ** i)
    return None


# ---------------------------------------------------------------- Polymarket
def polymarket_markets(closed=False, max_markets=1000, min_volume=0):
    """Markets ordered by volume. Paging is 100 per call; the API stops near ~2,100 closed markets."""
    rows = []
    for off in range(0, max_markets, 100):
        d = _get(f"{GAMMA}/markets?closed={'true' if closed else 'false'}&limit=100&offset={off}"
                 f"&order=volumeNum&ascending=false")
        if not d:
            break
        for m in d:
            try:
                tok = json.loads(m.get("clobTokenIds") or "[]")
                outs = json.loads(m.get("outcomes") or "[]")
                prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
            except Exception:
                continue
            if len(tok) != 2 or (m.get("volumeNum") or 0) < min_volume:
                continue
            ev = (m.get("events") or [{}])[0] if m.get("events") else {}
            rows.append(dict(id=m["id"], question=m["question"], event=ev.get("title", ""),
                             outcomes=outs, prices=prices, yes_token=tok[0], no_token=tok[1],
                             end=m.get("endDate"), closed_time=m.get("closedTime"),
                             volume=m.get("volumeNum"), best_bid=m.get("bestBid"), best_ask=m.get("bestAsk"),
                             neg_risk=m.get("negRisk")))
        if len(d) < 100:
            break
    df = pd.DataFrame(rows)
    if len(df):
        df["end"] = pd.to_datetime(df.end, utc=True, errors="coerce", format="mixed")
        df["closed_time"] = pd.to_datetime(df.closed_time, utc=True, errors="coerce", format="mixed")
        df["yes_won"] = df.prices.map(lambda p: int(p == [1.0, 0.0]) if sorted(p) == [0.0, 1.0] else np.nan)
    return df


def polymarket_history(token_id, fidelity_minutes=1440):
    """Price history of one outcome token -> Series indexed by UTC time. 1440 = daily (works for old markets).
    WARNING: at fidelity=1 the points lag the true state by ~1 minute (notes/R4.md); align with trades for lead-lag work.
    Hourly (60) requests must span <= ~7 days or the API returns 400."""
    d = _get(f"{CLOB}/prices-history?market={token_id}&interval=max&fidelity={fidelity_minutes}") or {}
    h = d.get("history", [])
    return pd.Series({pd.to_datetime(x["t"], unit="s", utc=True): float(x["p"]) for x in h}).sort_index()


def price_before_scheduled_end(market_row, days, history=None):
    """Last price `days` before the SCHEDULED end, or NaN if the market had already closed then (avoids look-ahead)."""
    h = history if history is not None else polymarket_history(market_row.yes_token)
    cut = market_row.end - pd.Timedelta(days=days)
    if pd.notna(market_row.closed_time) and market_row.closed_time <= cut:
        return np.nan
    h = h[h.index <= cut]
    return h.iloc[-1] if len(h) else np.nan


def polymarket_book(yes_token, no_token):
    """Merged YES book: returns (bids, asks) as lists of (price, size), best first."""
    b, n = _get(f"{CLOB}/book?token_id={yes_token}"), _get(f"{CLOB}/book?token_id={no_token}")
    if not b or not n:
        return [], []
    bids = [(float(x["price"]), float(x["size"])) for x in b.get("bids", [])] + \
           [(round(1 - float(x["price"]), 4), float(x["size"])) for x in n.get("asks", [])]
    asks = [(float(x["price"]), float(x["size"])) for x in b.get("asks", [])] + \
           [(round(1 - float(x["price"]), 4), float(x["size"])) for x in n.get("bids", [])]
    return sorted(bids, reverse=True), sorted(asks)


def fill_cost(asks, notional):
    """Average price to buy `notional` dollars walking the ask side; NaN if the book is too thin."""
    spent = shares = 0.0
    for p, s in asks:
        take = min(s * p, notional - spent)
        shares += take / p
        spent += take
        if spent >= notional - 1e-9:
            return spent / shares
    return np.nan


def polymarket_negrisk_events(max_events=3000):
    """Active multi-outcome events with sum of best bids/asks (Dutch-book check). See notes/P34.md."""
    rows = []
    for off in range(0, max_events, 100):
        d = _get(f"{GAMMA}/events?closed=false&active=true&limit=100&offset={off}&order=volume&ascending=false")
        if not d:
            break
        for e in d:
            if not e.get("negRisk"):
                continue
            ms = [m for m in e.get("markets", []) if m.get("active") and not m.get("closed")]
            asks = [m.get("bestAsk") for m in ms]
            bids = [m.get("bestBid") for m in ms]
            if len(ms) < 2 or None in asks or None in bids:
                continue
            rows.append(dict(title=e["title"], n=len(ms), sum_ask=float(np.sum(asks)), sum_bid=float(np.sum(bids)),
                             end=e.get("endDate")))
        if len(d) < 100:
            break
    return pd.DataFrame(rows)


def polymarket_trades(condition_id, max_trades=3000):
    """Taker trades (data-api default takerOnly=true, so `side` is the taker's side), newest first, paged by offset."""
    rows = []
    for off in range(0, max_trades, 500):
        d = _get(f"https://data-api.polymarket.com/trades?market={condition_id}&limit=500&offset={off}")
        if not d:
            break
        rows += d
        if len(d) < 500:
            break
    t = pd.DataFrame(rows)
    if len(t):
        t["ts"] = pd.to_datetime(t.timestamp, unit="s", utc=True)
    return t


# ---------------------------------------------------------------- Kalshi
def kalshi_open_events(max_pages=15):
    """Open events with nested markets (cursor paging, 200 per page)."""
    ev, cur = [], ""
    for _ in range(max_pages):
        d = _get(f"{KALSHI}/events?status=open&with_nested_markets=true&limit=200" + (f"&cursor={cur}" if cur else "")) or {}
        ev += d.get("events", [])
        cur = d.get("cursor") or ""
        if not cur:
            break
    return ev


def kalshi_settled(series_ticker):
    """Settled markets of a series (only ~2 months of history are listed)."""
    out, cur = [], ""
    while True:
        d = _get(f"{KALSHI}/markets?series_ticker={series_ticker}&status=settled&limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
        out += d.get("markets", [])
        cur = d.get("cursor") or ""
        if not cur or not d.get("markets"):
            break
    return out


def kalshi_candles(series_ticker, market_ticker, start_ts, end_ts, period_minutes=60):
    """Candlesticks: yes_bid/yes_ask/price OHLC in dollars."""
    d = _get(f"{KALSHI}/series/{series_ticker}/markets/{market_ticker}/candlesticks"
             f"?start_ts={int(start_ts)}&end_ts={int(end_ts)}&period_interval={period_minutes}") or {}
    return d.get("candlesticks", [])


def kalshi_taker_fee(price, contracts=1):
    """Kalshi general taker fee: 0.07 * C * P * (1-P), rounded up to the cent per order."""
    return np.ceil(0.07 * contracts * price * (1 - price) * 100) / 100


# ---------------------------------------------------------------- math helpers
def kelly_binary(q, p):
    """Kelly stake for buying YES at price p with belief q: (q-p)/(1-p); negative -> consider NO."""
    return (q - p) / (1 - p)


def lmsr_cost(q, b):
    """Hanson LMSR cost function C(q) = b ln sum exp(q_i/b)."""
    q = np.asarray(q, float)
    return b * np.log(np.sum(np.exp(q / b)))


def lmsr_prices(q, b):
    e = np.exp(np.asarray(q, float) / b)
    return e / e.sum()


def calibration_table(prices, outcomes, bins=(0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, 1.0001)):
    d = pd.DataFrame(dict(p=prices, y=outcomes))
    d["bin"] = pd.cut(d.p, bins, right=False)
    return d.groupby("bin", observed=True).agg(n=("y", "size"), avg_price=("p", "mean"), win_rate=("y", "mean"))


if __name__ == "__main__":
    m = polymarket_markets(closed=False, max_markets=100)
    print(len(m), "open Polymarket markets; top:", m.iloc[0].question)
    bids, asks = polymarket_book(m.iloc[0].yes_token, m.iloc[0].no_token)
    print("best bid/ask", bids[:1], asks[:1], "| gamma:", m.iloc[0].best_bid, m.iloc[0].best_ask,
          "| $1k fill avg", fill_cost(asks, 1000))
    print("Kelly q=.55 p=.50 ->", kelly_binary(.55, .5), "| Kalshi fee 100 @ 30c ->", kalshi_taker_fee(.3, 100))
