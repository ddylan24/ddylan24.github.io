"""R1 data: settled Kalshi KXBTCD daily (5pm ET) markets, their hourly candles near T-24h/T-6h, Deribit BTC perp + DVOL hourly."""
import json, sys, time, urllib.request, urllib.error, pandas as pd
R = sys.argv[1]; D = f"{R}/data/r1"
import subprocess, os
def get(u, tries=7):
    for i in range(tries):
        r = subprocess.run(['curl', '-s', '--max-time', '30', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code == '200':
            try: return json.loads(body)
            except Exception: pass
        time.sleep(min(2 ** i, 30))
K = "https://api.elections.kalshi.com/trade-api/v2"
# 1) events
ev, cur = [], ""
for _ in range(30):
    d = get(f"{K}/events?series_ticker=KXBTCD&status=settled&with_nested_markets=true&limit=200" + (f"&cursor={cur}" if cur else "")) or {}
    ev += [e for e in d.get('events', []) if e['event_ticker'].endswith('17')]
    cur = d.get('cursor') or ""; time.sleep(0.4)
    if not cur or not d.get('events'): break
rows = []
for e in ev:
    for m in e.get('markets', []):
        if m.get('floor_strike') is None or m.get('result') not in ('yes', 'no'): continue
        rows.append(dict(event=e['event_ticker'], ticker=m['ticker'], K=float(m['floor_strike']), cap=m.get('cap_strike'),
                         y=int(m['result'] == 'yes'), close=m['close_time'], settle=m.get('expiration_value'), vol=m.get('volume')))
M = pd.DataFrame(rows); M['close'] = pd.to_datetime(M.close, utc=True); M.to_csv(f"{D}/all_markets.csv", index=False)
M = M[M.cap.isna()]       # 'above K' contracts only
print(len(ev), "daily events", flush=True); print(len(ev), "daily events", len(M), "markets", M.close.min(), M.close.max())
# 2) Deribit perp + DVOL hourly
t0 = int(M.close.min().timestamp() - 3 * 86400) * 1000; t1 = int(M.close.max().timestamp()) * 1000
px = []
for a in range(t0, t1, 20 * 86400 * 1000):
    d = get(f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&start_timestamp={a}&end_timestamp={min(a+20*86400*1000,t1)}&resolution=60")['result']
    px += list(zip(d['ticks'], d['close']))
P = pd.Series(dict(px)).sort_index(); P.index = pd.to_datetime(P.index, unit='ms', utc=True); P.to_csv(f"{D}/btc_perp_1h.csv")
dv = []; a = t0
while a < t1:
    d = get(f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp={a}&end_timestamp={min(a+40*86400*1000,t1)}&resolution=3600")['result']['data']
    dv += [(x[0], x[4]) for x in d]; a += 40 * 86400 * 1000
V = pd.Series(dict(dv)).sort_index(); V.index = pd.to_datetime(V.index, unit='ms', utc=True); V.to_csv(f"{D}/dvol_1h.csv")
print("perp", len(P), "dvol", len(V))
# 3) strikes near spot at T-24h, candles
def at(s, t): s = s[s.index <= t]; return s.iloc[-1] if len(s) else float('nan')
M['spot24'] = [at(P, c - pd.Timedelta(hours=24)) for c in M.close]
S = M[(M.K / M.spot24 - 1).abs() < 0.06].copy()
print("selected", len(S), "markets near T-24h spot")
S.to_csv(f"{D}/markets.csv", index=False)
C = {}
if os.path.exists(f"{D}/candles.jsonl"):
    for line in open(f"{D}/candles.jsonl"): x = json.loads(line); C[x['t']] = x['c']
f = open(f"{D}/candles.jsonl", "a")
for i, r in enumerate(S.itertuples()):
    if r.ticker in C: continue
    ce = int(r.close.timestamp())
    d = get(f"{K}/series/KXBTCD/markets/{r.ticker}/candlesticks?start_ts={ce-30*3600}&end_ts={ce}&period_interval=60") or {}
    C[r.ticker] = d.get('candlesticks', []); f.write(json.dumps({'t': r.ticker, 'c': C[r.ticker]}) + "\n"); f.flush(); time.sleep(0.15)
    if i % 100 == 0: print(i, len(S), len(C[r.ticker]), time.strftime('%H:%M:%S'), flush=True)
print("done", len(C))
