"""AD1/AD2: generic settlement-marked maker edge for a list of series over N days, plus LIP pools on the same markets.
usage: ad_series_edge.py R DAYS SER1,SER2,... TAG"""
import json, subprocess, sys, time, numpy as np, pandas as pd
R, DAYS, SER, TAG = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(','), sys.argv[4]; out = []; rng = np.random.default_rng(4)
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
P = pd.read_csv(f"{R}/../lip/programs_all_liquidity.csv", low_memory=False); pool = P.groupby('market_ticker').usd.sum()
since = int(time.time()) - DAYS * 86400; rows = []
for ser in SER:
    ms, cur = [], ''
    for _ in range(20):
        d = get(f"{API}/markets?series_ticker={ser}&status=settled&limit=1000&min_close_ts={since}" + (f"&cursor={cur}" if cur else "")) or {}
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
                rows.append((ser, m['ticker'], m['close_time'][:10], ((p - y) if x['taker_side'] == 'yes' else (y - p)) * n, n))
            cur = d.get('cursor') or ''
            if not cur or not d.get('trades'): break
        time.sleep(0.04)
    print(ser, len(ms), len(rows), flush=True)
F = pd.DataFrame(rows, columns=['series', 'ticker', 'day', 'maker', 'n']); F.to_csv(f"{R}/data/{TAG}_fills.csv.gz", index=False)
out.append(f"[{TAG}] {DAYS} days, settlement-marked maker P&L (¢/contract ± market-clustered SE) and LIP pools on the same markets")
for s, g in F.groupby('series'):
    m = g.groupby('ticker').agg(p=('maker', 'sum'), n=('n', 'sum'))
    b = 100 * m.p.sum() / m.n.sum(); bs = [100 * m.p.values[i].sum() / m.n.values[i].sum() for i in (rng.integers(0, len(m), len(m)) for _ in range(500))]
    pl = pool.reindex(m.index).fillna(0).sum()
    daily = g.groupby('day').apply(lambda x: 100 * x.maker.sum() / x.n.sum(), include_groups=False)
    out.append(f"  {s:<14} markets {len(m):4d}  contracts {m.n.sum():11,.0f}  maker {b:+.2f} ± {np.std(bs):.2f}  fills ${m.p.sum():+10,.0f}  LIP pool ${pl:9,.0f}  reward {100*pl/m.n.sum():.2f}¢/ct  | daily maker ¢/ct: " + " ".join(f"{v:+.1f}" for v in daily.values))
txt = "\n".join(out); print(txt); open(f"{R}/notes/{TAG}_out.txt", "w").write(txt)
