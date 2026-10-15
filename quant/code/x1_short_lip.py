"""X1: short LIP programs (≤1 day: hourly temperature, 15-min crypto/FX, etc.) — reward pools vs maker fill markouts.
Programs that ENDED in the last 24h for the top short-program series; fills from public trades during each program window;
markout vs the 1-min mid 5 min later (or the final settlement price if the market settles within 5 min)."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; D = f"{R}/data/lip"; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
A = pd.read_csv(f"{R}/../lip/programs_all_liquidity.csv", low_memory=False)
A['s'] = pd.to_datetime(A.s, utc=True, format='mixed'); A['e'] = pd.to_datetime(A.e, utc=True, format='mixed')
A['dur_h'] = (A.e - A.s).dt.total_seconds() / 3600; A['series'] = A.market_ticker.str.split('-').str[0]
now = pd.Timestamp.now(tz='UTC')
S = A[(A.dur_h <= 24) & (A.e <= now) & (A.e > now - pd.Timedelta(hours=24))]
top = S.groupby('series').usd.sum().sort_values(ascending=False).head(8).index
S = S[S.series.isin(top)]
out.append(f"Short programs (≤24h) ended in the last 24h, top 8 series: {len(S)} programs, pools ${S.usd.sum():,.0f}")
rows = []
for ser, g in S.groupby('series'):
    tks = g.market_ticker.unique()[:60]                 # cap per series for API politeness
    pool = g[g.market_ticker.isin(tks)].usd.sum(); mk = 0.0; vol = 0.0; nfill = 0
    for tk in tks:
        win = g[g.market_ticker == tk]; t0 = int(win.s.min().timestamp()); t1 = int(win.e.max().timestamp())
        tr = (get(f"{API}/markets/trades?ticker={tk}&limit=1000&min_ts={t0}&max_ts={t1}") or {}).get('trades', [])
        if not tr: continue
        c = (get(f"{API}/series/{ser}/markets/{tk}/candlesticks?start_ts={t0}&end_ts={t1 + 900}&period_interval=1") or {}).get('candlesticks', [])
        s = pd.Series({pd.to_datetime(x['end_period_ts'], unit='s', utc=True): (float(x['yes_bid']['close_dollars']) + float(x['yes_ask']['close_dollars'])) / 2
                       for x in c if x.get('yes_bid', {}).get('close_dollars') and x.get('yes_ask', {}).get('close_dollars')}).sort_index()
        m = (get(f"{API}/markets/{tk}") or {}).get('market', {})
        settle = {'yes': 1.0, 'no': 0.0}.get(m.get('result'))
        for x in tr:
            ts = pd.Timestamp(x['created_time']); p = float(x['yes_price_dollars']); n = float(x['count_fp'])
            f = s[s.index >= ts + pd.Timedelta(minutes=5)] if len(s) else s
            ref = f.iloc[0] if len(f) else settle
            if ref is None: continue
            mk += ((p - ref) if x['taker_side'] == 'yes' else (ref - p)) * n; vol += n; nfill += 1
        time.sleep(0.1)
    rows.append(dict(series=ser, markets=len(tks), pool=pool, fills=nfill, contracts=vol, markout=mk))
X = pd.DataFrame(rows).sort_values('pool', ascending=False); X.to_csv(f"{D}/x1_short.csv", index=False)
for r in X.itertuples():
    out.append(f"  {r.series:<22} markets {r.markets:3d}  pool ${r.pool:8,.0f}  fills {r.fills:5d}  contracts {r.contracts:9,.0f}  maker markout ${r.markout:+9,.0f} ({100*r.markout/max(r.contracts,1):+.2f}¢/ct)  pool/|markout| {r.pool/max(abs(r.markout),1):.1f}")
out.append(f"  TOTAL pool ${X.pool.sum():,.0f} vs maker markout ${X.markout.sum():+,.0f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/x1_out.txt", "w").write(txt)
