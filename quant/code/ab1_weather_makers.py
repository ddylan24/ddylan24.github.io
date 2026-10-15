"""AB1: does the KXTEMPMIAH maker edge generalize to other Kalshi weather series? 7 days of settled markets; all public fills
marked to settlement; maker P&L per contract with market-clustered bootstrap SE; split by minutes to close."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; out = []; rng = np.random.default_rng(1)
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
since = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
SER = ['KXHIGHNY', 'KXHIGHCHI', 'KXHIGHMIA', 'KXHIGHLAX', 'KXHIGHAUS', 'KXHIGHDEN', 'KXRAIN']
rows = []
for ser in SER:
    ms, cur = [], ''
    for _ in range(10):
        d = get(f"{API}/markets?series_ticker={ser}&status=settled&limit=1000&min_close_ts={int(since.timestamp())}" + (f"&cursor={cur}" if cur else "")) or {}
        ms += d.get('markets', []); cur = d.get('cursor') or ''
        if not cur or not d.get('markets'): break
    for m in ms:
        y = {'yes': 1.0, 'no': 0.0}.get(m.get('result'))
        if y is None: continue
        cur = ''
        for _ in range(10):
            d = get(f"{API}/markets/trades?ticker={m['ticker']}&limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
            for x in d.get('trades', []):
                p = float(x['yes_price_dollars']); n = float(x['count_fp'])
                rows.append((ser, m['ticker'], m['close_time'], x['created_time'], ((p - y) if x['taker_side'] == 'yes' else (y - p)) * n, n))
            cur = d.get('cursor') or ''
            if not cur or not d.get('trades'): break
        time.sleep(0.05)
    print(ser, len(ms), len(rows), flush=True)
F = pd.DataFrame(rows, columns=['series', 'ticker', 'close', 'ts', 'maker', 'n'])
F['close'] = pd.to_datetime(F.close, utc=True, format='mixed'); F['ts'] = pd.to_datetime(F.ts, utc=True, format='mixed')
F['hrs_left'] = (F.close - F.ts).dt.total_seconds() / 3600
F.to_csv(f"{R}/data/ab1_fills.csv.gz", index=False)
out.append("Maker P&L to settlement, 7 days (¢/contract, market-clustered bootstrap SE)")
for s, g in F.groupby('series'):
    m = g.groupby('ticker').agg(p=('maker', 'sum'), n=('n', 'sum'))
    b = 100 * m.p.sum() / m.n.sum(); bs = [100 * m.p.values[i].sum() / m.n.values[i].sum() for i in (rng.integers(0, len(m), len(m)) for _ in range(500))]
    late = g[g.hrs_left <= 3]; early = g[g.hrs_left > 3]
    out.append(f"  {s:<10} markets {len(m):4d}  contracts {m.n.sum():9,.0f}  maker {b:+.2f} ± {np.std(bs):.2f}¢  | last 3h {100*late.maker.sum()/max(late.n.sum(),1):+.2f}¢, earlier {100*early.maker.sum()/max(early.n.sum(),1):+.2f}¢")
txt = "\n".join(out); print(txt); open(f"{R}/notes/ab1_out.txt", "w").write(txt)
