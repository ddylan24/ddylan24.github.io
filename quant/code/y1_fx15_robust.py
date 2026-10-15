"""Y1: are makers really profitable in Kalshi 15-minute FX up/down markets? 7 days of settled markets per series; every public fill
marked to SETTLEMENT (maker P&L per contract: taker bought YES at P → maker P − y; taker bought NO → y − P). Cluster by market.
Control: KXCRYPTOLEAD15M-style crypto 15m series. Breakdown by UTC hour and by price bucket."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; D = f"{R}/data/y1"; out = []
import os; os.makedirs(D, exist_ok=True)
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
since = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
SER = ['KXEURUSD15M', 'KXUSDJPY15M', 'KXAUDUSD15M', 'KXBTC15M', 'KXETH15M']
rows = []
for ser in SER:
    ms, cur = [], ''
    for _ in range(20):
        d = get(f"{API}/markets?series_ticker={ser}&status=settled&limit=1000&min_close_ts={int(since.timestamp())}" + (f"&cursor={cur}" if cur else "")) or {}
        ms += d.get('markets', []); cur = d.get('cursor') or ''
        if not cur or not d.get('markets'): break
    out.append(f"{ser}: {len(ms)} settled markets in 7 days")
    for m in ms:
        y = {'yes': 1.0, 'no': 0.0}.get(m.get('result'))
        if y is None: continue
        tr, cur = [], ''
        for _ in range(5):
            d = get(f"{API}/markets/trades?ticker={m['ticker']}&limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
            tr += d.get('trades', []); cur = d.get('cursor') or ''
            if not cur or not d.get('trades'): break
        close = pd.Timestamp(m['close_time'])
        for x in tr:
            p = float(x['yes_price_dollars']); n = float(x['count_fp'])
            rows.append((ser, m['ticker'], close, pd.Timestamp(x['created_time']), x['taker_side'], p, n, y))
        time.sleep(0.05)
    print(ser, len(ms), len(rows), flush=True)
T = pd.DataFrame(rows, columns=['series', 'ticker', 'close', 'ts', 'side', 'p', 'n', 'y'])
T['maker'] = np.where(T.side == 'yes', T.p - T.y, T.y - T.p) * T.n       # maker $ P&L to settlement
T['mins_left'] = (T.close - T.ts).dt.total_seconds() / 60
T.to_csv(f"{D}/fills.csv.gz", index=False)
def ct(g):
    by = g.groupby('ticker').agg(m=('maker', 'sum'), n=('n', 'sum')); x = by.m.values
    return x.sum() / max(by.n.sum(), 1), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan, len(x)
out.append(f"\n{len(T):,} fills, {T.n.sum():,.0f} contracts")
for ser, g in T.groupby('series'):
    pc, t, nm = ct(g)
    late = g[g.mins_left <= 3]; early = g[g.mins_left > 3]
    out.append(f"  {ser:<12} contracts {g.n.sum():9,.0f}  maker P&L to settlement ${g.maker.sum():+10,.0f}  {100*pc:+.2f}¢/ct  (market-clustered t {t:+.1f}, {nm} mkts)  | fills >3 min before close {100*early.maker.sum()/max(early.n.sum(),1):+.2f}¢/ct, last 3 min {100*late.maker.sum()/max(late.n.sum(),1):+.2f}¢/ct")
for ser in ['KXEURUSD15M', 'KXUSDJPY15M']:
    g = T[T.series == ser]
    if not len(g): continue
    hr = g.groupby(g.ts.dt.hour).apply(lambda x: 100 * x.maker.sum() / max(x.n.sum(), 1), include_groups=False)
    out.append(f"  {ser} by UTC hour (¢/ct): " + " ".join(f"{h}:{v:+.1f}" for h, v in hr.items()))
    g = g.assign(pb=pd.cut(g.p, [0, .1, .3, .7, .9, 1]))
    out.append(f"  {ser} by trade price: " + ", ".join(f"{k}: {100*x.maker.sum()/max(x.n.sum(),1):+.2f}¢" for k, x in g.groupby('pb', observed=True)))
txt = "\n".join(out); print(txt); open(f"{R}/notes/y1_out.txt", "w").write(txt)
