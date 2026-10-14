"""R4: does signed taker order flow move / predict Polymarket prices? (Kyle lambda, Cont-Kukanov-Stoikov style)
Taker trades from data-api (default takerOnly=true, so `side` is the taker's side), 1-minute mids from prices-history."""
import json, sys, time, urllib.request, numpy as np, pandas as pd, statsmodels.api as sm
R = sys.argv[1]; out = []
def get(u):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r: return json.load(r)
        except Exception: time.sleep(2 ** i)
ms = get("https://gamma-api.polymarket.com/markets?closed=false&limit=40&order=volume24hr&ascending=false")
ms = [m for m in ms if 0.1 < float(m.get('bestBid') or 0) < 0.9][:8]
NOW = int(time.time()); rows = []; ALIGN = sys.argv[2] if len(sys.argv) > 2 else 'raw'
for m in ms:
    yes = json.loads(m['clobTokenIds'])[0]; T = []
    for off in range(0, 3000, 500):
        d = get(f"https://data-api.polymarket.com/trades?market={m['conditionId']}&limit=500&offset={off}")
        if not d: break
        T += d
        if len(d) < 500: break
    t = pd.DataFrame(T)
    if len(t) < 200: continue
    t['ts'] = pd.to_datetime(t.timestamp, unit='s', utc=True)
    # YES-equivalent signed dollars: buying YES or selling NO = +; selling YES or buying NO = −
    sgn = np.where((t.asset == yes) == (t.side == 'BUY'), 1, -1)
    t['flow'] = sgn * t['size'] * t.price
    start, end = int(t.timestamp.min()), int(t.timestamp.max())
    h = get(f"https://clob.polymarket.com/prices-history?market={yes}&startTs={start}&endTs={end}&fidelity=1") or {}
    P = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True).floor('min'): float(x['p']) for x in h.get('history', [])}).sort_index()
    if ALIGN == 'shift': P.index = P.index - pd.Timedelta(minutes=1)     # prices-history lags ~1 min (see notes/R4.md)
    t['pyes'] = np.where(t.asset == yes, t.price, 1 - t.price)
    if ALIGN == 'trade': P = t.set_index('ts').pyes.resample('1min').last().dropna()
    if len(P) < 100: continue
    F = t.set_index('ts').flow.resample('1min').sum()
    df = pd.DataFrame({'p': P.resample('1min').last().ffill(), 'flow': F}).dropna(subset=['p']).fillna({'flow': 0})
    df['dp'] = df.p.diff() * 100              # cents
    df['dp_next'] = df.dp.shift(-1); df['dp_next5'] = df.p.shift(-5).sub(df.p) * 100
    df['flow_k'] = df.flow / 1000            # $k
    df = df.dropna()
    name = m['question'][:48]
    res = {}
    for y in ['dp', 'dp_next', 'dp_next5']:
        X = sm.add_constant(df[['flow_k']] if y == 'dp' else df[['flow_k', 'dp']])
        f = sm.OLS(df[y], X).fit(cov_type='HAC', cov_kwds={'maxlags': 5})
        res[y] = (f.params['flow_k'], f.tvalues['flow_k'], f.rsquared)
    rows.append(dict(market=name, minutes=len(df), trades=len(t), usd=t['size'].mul(t.price).sum(), mid=df.p.mean(),
                     lam=res['dp'][0], lam_t=res['dp'][1], r2=res['dp'][2], pred1=res['dp_next'][0], pred1_t=res['dp_next'][1],
                     pred5=res['dp_next5'][0], pred5_t=res['dp_next5'][1], ac=df.dp.autocorr()))
    df.assign(market=name).to_csv(f"{R}/data/r4/{m['conditionId'][:10]}.csv")
D = pd.DataFrame(rows)
out.append(f"[price source: {ALIGN}] {len(D)} most-active two-sided Polymarket markets, 1-minute bars over the last ~{D.minutes.median()/1440:.0f} days of trades (HAC t-stats, 5 lags; next-minute regressions control for current dp)")
out.append(f"{'market':<48} {'min':>5} {'$k':>6} {'λ ¢/$k':>7} {'t':>5} {'R²':>5} | {'next-1m ¢/$k':>12} {'t':>5} | {'next-5m':>7} {'t':>5} | {'AC(dp)':>6}")
for r in D.itertuples():
    out.append(f"{r.market:<48} {r.minutes:5d} {r.usd/1e3:6.0f} {r.lam:7.3f} {r.lam_t:5.1f} {r.r2:5.2f} | {r.pred1:12.3f} {r.pred1_t:5.1f} | {r.pred5:7.3f} {r.pred5_t:5.1f} | {r.ac:6.2f}")
out.append(f"\nMedian λ {D.lam.median():.3f}¢ per $1k (contemporaneous), median t {D.lam_t.median():.1f}; next-minute coefficient median {D.pred1.median():+.3f} (median t {D.pred1_t.median():+.1f}); "
           f"share with |t|>2 for next-minute: {(D.pred1_t.abs()>2).mean():.0%}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/r4_out.txt", "a").write(txt); D.to_csv(f"{R}/data/r4/summary.csv", index=False)
