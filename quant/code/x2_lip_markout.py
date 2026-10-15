"""X2: adverse selection for makers at the touch in Kalshi LIP markets.
Public trades (GET /markets/trades?ticker=…, taker_side yes/no, yes_price, count) give every fill; the maker took the other side.
Maker markout per contract after h minutes: if taker bought YES at P → maker is short YES: P − mid_{t+h}; if taker bought NO
(i.e. sold YES at P) → maker long YES: mid_{t+h} − P. mid from 1-minute candles (batch endpoint, yes bid/ask close).
Compare per-contract-day reward available (pool / (2 × qualifying depth)) with markout × fills per resting contract-day."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; D = f"{R}/data/lip"; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
M = pd.read_csv(f"{D}/w1_markets.csv")
now = int(time.time()); t0 = now - 36 * 3600
rows = []; mids = {}
for i in range(0, len(M), 4):
    tk = list(M.market_ticker.iloc[i:i + 4])
    c = get(f"{API}/markets/candlesticks?market_tickers={','.join(tk)}&start_ts={t0}&end_ts={now}&period_interval=1") or {}
    for m in c.get('markets', []):
        s = pd.DataFrame([(x['end_period_ts'], x['yes_bid'].get('close_dollars'), x['yes_ask'].get('close_dollars')) for x in m.get('candlesticks', [])], columns=['t', 'b', 'a']).dropna()
        if len(s): mids[m['market_ticker']] = pd.Series(((s.b.astype(float) + s.a.astype(float)) / 2).values, index=pd.to_datetime(s.t, unit='s', utc=True))
for tk in M.market_ticker:
    cur, tr = '', []
    for _ in range(20):
        d = get(f"{API}/markets/trades?ticker={tk}&limit=1000&min_ts={t0}" + (f"&cursor={cur}" if cur else "")) or {}
        tr += d.get('trades', []); cur = d.get('cursor') or ''
        if not cur or not d.get('trades'): break
    for x in tr:
        rows.append(dict(t=tk, ts=pd.Timestamp(x['created_time']), side=x['taker_side'], p=float(x['yes_price_dollars']), n=float(x['count_fp'])))
    time.sleep(0.1)
T = pd.DataFrame(rows); T['ts'] = pd.to_datetime(T.ts, utc=True); T.to_csv(f"{D}/x2_trades.csv", index=False)
out.append(f"{T.t.nunique()} markets, {len(T):,} trades, {T.n.sum():,.0f} contracts in the last 36h; candles for {len(mids)} markets")
res = []
for h in (5, 30, 60):
    v = []
    for r in T.itertuples():
        s = mids.get(r.t)
        if s is None: continue
        f = s[s.index >= r.ts + pd.Timedelta(minutes=h)]
        if not len(f): continue
        m = f.iloc[0]; v.append(((r.p - m) if r.side == 'yes' else (m - r.p)) * r.n)
    tot = np.sum(v); n = T.n.sum()
    res.append((h, tot)); out.append(f"  maker markout after {h:2d} min: total ${tot:,.0f} on {n:,.0f} contracts → {100*tot/n:+.2f}¢ per filled contract")
# compare with rewards: per market, pool/day vs maker markout/day (36h window → per day ×(24/36))
mk = []
for tk, g in T.groupby('t'):
    s = mids.get(tk)
    if s is None: continue
    v = 0.0
    for r in g.itertuples():
        f = s[s.index >= r.ts + pd.Timedelta(minutes=30)]
        if len(f): v += ((r.p - f.iloc[0]) if r.side == 'yes' else (f.iloc[0] - r.p)) * r.n
    pd_ = M.set_index('market_ticker').per_day.get(tk)
    mk.append(dict(t=tk, markout_day=v * 24 / 36, vol_day=g.n.sum() * 24 / 36, reward_day=pd_))
K = pd.DataFrame(mk)
out.append(f"\nPer market per day (30-min markout): median maker markout ${K.markout_day.median():+,.1f} vs reward pool ${K.reward_day.median():,.0f}; "
           f"aggregate markout ${K.markout_day.sum():+,.0f}/day vs pools ${K.reward_day.sum():,.0f}/day across {len(K)} markets")
out.append(f"  median filled volume {K.vol_day.median():,.0f} contracts/day per market; markets where |markout| > reward: {(K.markout_day.abs() > K.reward_day).sum()} of {len(K)}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/x2_out.txt", "w").write(txt)
