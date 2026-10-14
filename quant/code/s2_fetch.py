"""S2 data: settled Kalshi KXBTCD events of ALL hours (last ~14 days), strikes within ±4% of spot at T−12h, hourly candles via batch."""
import json, subprocess, sys, time, pandas as pd
R = sys.argv[1]; D = f"{R}/data/s2"; K = "https://api.elections.kalshi.com/trade-api/v2"
def get(u):
    for i in range(7):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code == '200': return json.loads(body)
        time.sleep(min(2 ** i, 30))
ev, cur = [], ""
for _ in range(10):
    d = get(f"{K}/events?series_ticker=KXBTCD&status=settled&with_nested_markets=true&limit=200" + (f"&cursor={cur}" if cur else "")) or {}
    ev += d.get('events', []); cur = d.get('cursor') or ""; time.sleep(1)
    print("events", len(ev), flush=True)
    if not cur or len(ev) >= 340: break
rows = []
for e in ev:
    for m in e.get('markets', []):
        if m.get('floor_strike') is None or m.get('cap_strike') is not None or m.get('result') not in ('yes', 'no'): continue
        rows.append(dict(event=e['event_ticker'], ticker=m['ticker'], K=float(m['floor_strike']), y=int(m['result'] == 'yes'), close=m['close_time'], open=m.get('open_time')))
M = pd.DataFrame(rows).drop_duplicates('ticker'); M['close'] = pd.to_datetime(M.close, utc=True); M['open'] = pd.to_datetime(M.open, utc=True)
P = pd.read_csv(f"{R}/data/r1/btc_perp_1h.csv", index_col=0, parse_dates=True).iloc[:, 0]; P.index = P.index + pd.Timedelta(hours=1)
t1 = int(M.close.max().timestamp()) * 1000; a = int(P.index.max().timestamp()) * 1000
d = get(f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&start_timestamp={a}&end_timestamp={t1}&resolution=60")['result']
P2 = pd.Series(d['close'], index=pd.to_datetime(d['ticks'], unit='ms', utc=True) + pd.Timedelta(hours=1)); P = pd.concat([P, P2]).sort_index(); P = P[~P.index.duplicated()]
P.to_csv(f"{D}/perp_close_stamped.csv")
def at(t): s = P[P.index <= t]; return s.iloc[-1]
M['spot12'] = [at(c - pd.Timedelta(hours=12)) for c in M.close]
S = M[(M.K / M.spot12 - 1).abs() < 0.04].copy(); S.to_csv(f"{D}/markets.csv", index=False)
print("events", M.event.nunique(), "selected markets", len(S), flush=True)
C = {}
for e, g in S.groupby('event'):
    ce = int(g.close.iloc[0].timestamp())
    for i in range(0, len(g), 40):
        tk = list(g.ticker.iloc[i:i + 40])
        d = get(f"{K}/markets/candlesticks?market_tickers={','.join(tk)}&start_ts={ce-14*3600}&end_ts={ce}&period_interval=60") or {}
        for t, m in zip(tk, d.get('markets', [])): C[m.get('market_ticker', t)] = m.get('candlesticks', [])
        time.sleep(0.6)
json.dump(C, open(f"{D}/candles.json", "w")); print("done", len(C), flush=True)
