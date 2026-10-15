"""AC1: category map of maker edges on Kalshi. Recently settled markets (last 4 days, excluding multivariate combos 'KXMVE'),
joined to their series' category (GET /series); per category the 150 most-traded markets (biased toward liquid markets), mark every public
fill to settlement; maker ¢/contract with market-clustered bootstrap SE."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; out = []; rng = np.random.default_rng(3)
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '60', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
cat = {}; cur = ''
for _ in range(50):
    d = get(f"{API}/series?limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
    for s in d.get('series', []): cat[s['ticker']] = s.get('category')
    cur = d.get('cursor') or ''
    if not cur or not d.get('series'): break
since = int(time.time()) - 4 * 86400; ms = []; cur = ''
for _ in range(60):
    d = get(f"{API}/markets?status=settled&limit=1000&min_close_ts={since}&mve_filter=exclude" + (f"&cursor={cur}" if cur else "")) or {}
    ms += [m for m in d.get('markets', []) if not m['ticker'].startswith('KXMVE')]; cur = d.get('cursor') or ''
    if not cur or not d.get('markets'): break
M = pd.DataFrame([dict(t=m['ticker'], ser=m['event_ticker'].split('-')[0], res=m.get('result'), vol=float(m.get('volume_fp') or m.get('volume') or 0)) for m in ms])
M['cat'] = M.ser.map(cat).fillna('?'); M = M[M.res.isin(['yes', 'no']) & (M.vol > 0)]
out.append(f"{len(cat)} series; {len(M):,} settled markets with volume in 4 days; by category: " + ", ".join(f"{k} {v}" for k, v in M.cat.value_counts().items()))
rows = []
for c, g in M.groupby('cat'):
    samp = g.sort_values('vol', ascending=False).head(150)          # the 150 most-traded settled markets per category
    for m in samp.itertuples():
        y = 1.0 if m.res == 'yes' else 0.0; cur = ''
        for _ in range(5):
            d = get(f"{API}/markets/trades?ticker={m.t}&limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
            for x in d.get('trades', []):
                p = float(x['yes_price_dollars']); n = float(x['count_fp'])
                rows.append((c, m.ser, m.t, ((p - y) if x['taker_side'] == 'yes' else (y - p)) * n, n))
            cur = d.get('cursor') or ''
            if not cur or not d.get('trades'): break
        time.sleep(0.05)
    print(c, len(samp), len(rows), flush=True)
F = pd.DataFrame(rows, columns=['cat', 'ser', 't', 'maker', 'n']); F.to_csv(f"{R}/data/ac1_fills.csv.gz", index=False)
out.append("Maker P&L to settlement by category (¢/contract ± market-clustered SE)")
for c, g in F.groupby('cat'):
    m = g.groupby('t').agg(p=('maker', 'sum'), n=('n', 'sum'))
    b = 100 * m.p.sum() / m.n.sum(); bs = [100 * m.p.values[i].sum() / m.n.values[i].sum() for i in (rng.integers(0, len(m), len(m)) for _ in range(500))]
    top = g.groupby('ser').n.sum().sort_values(ascending=False).head(3).index.tolist()
    out.append(f"  {c:<26} markets {len(m):4d}  contracts {m.n.sum():11,.0f}  maker {b:+6.2f} ± {np.std(bs):4.2f}  (top series: {', '.join(top)})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/ac1_out.txt", "w").write(txt)
