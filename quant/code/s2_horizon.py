"""S2: calibration of Kalshi BTC threshold markets by time-to-expiry (1–12h), all hourly events, day-clustered."""
import json, sys, numpy as np, pandas as pd, statsmodels.api as sm
R = sys.argv[1]; D = f"{R}/data/s2"; out = []
S = pd.read_csv(f"{D}/markets.csv", parse_dates=['close']); C = json.load(open(f"{D}/candles.json"))
rows = []
for r in S.itertuples():
    cs = C.get(r.ticker, [])
    for h in (1, 2, 3, 6, 12):
        ts = int((r.close - pd.Timedelta(hours=h)).timestamp()); best = None
        for c in cs:
            if c['end_period_ts'] <= ts: best = c
        if not best or best['end_period_ts'] < ts - 3600: continue
        b, a = best.get('yes_bid', {}).get('close_dollars'), best.get('yes_ask', {}).get('close_dollars')
        if not b or not a: continue
        b, a = float(b), float(a)
        if a - b > 0.10 or a <= 0: continue
        rows.append(dict(event=r.event, day=r.close.strftime('%Y-%m-%d'), h=h, y=r.y, bid=b, ask=a, mid=(a + b) / 2))
X = pd.DataFrame(rows); X.to_csv(f"{D}/panel.csv", index=False)
clip = lambda p: np.clip(p, 0.005, 0.995); lg = lambda p: np.log(clip(p) / (1 - clip(p)))
fee = lambda p: 0.07 * p * (1 - p)        # Kalshi taker fee per contract (order-level rounding ignored)
out.append(f"Kalshi KXBTCD settled hourly events {S.event.nunique()} ({S.close.min():%m-%d} → {S.close.max():%m-%d}); strikes ±4% of spot at T−12h; quotes with spread ≤10¢")
out.append(f"{'h':>3} {'n':>6} {'days':>5} {'slope':>6} {'se':>5} {'icpt':>6} | {'5–20¢ px':>8} {'won':>6} | {'80–95¢ px':>9} {'won':>6} | sell 5–20¢ at bid net (¢, t)")
for h, x in X.groupby('h'):
    x = x[(x.mid > 0.02) & (x.mid < 0.98)]
    f = sm.GLM(x.y, sm.add_constant(lg(x.mid)), family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(x.day)[0]})
    lo = x[(x.mid >= .05) & (x.mid <= .20)]; hi = x[(x.mid >= .80) & (x.mid <= .95)]
    pnl = lo.bid - lo.y - fee(lo.bid)
    g = (pnl - pnl.mean()).groupby(lo.day.values).sum(); t = pnl.mean() / (np.sqrt((g ** 2).sum()) / len(pnl))
    out.append(f"{h:3d} {len(x):6d} {x.day.nunique():5d} {f.params.iloc[1]:6.2f} {f.bse.iloc[1]:5.2f} {f.params.iloc[0]:+6.2f} | {lo.mid.mean():8.3f} {lo.y.mean():6.3f} | {hi.mid.mean():9.3f} {hi.y.mean():6.3f} | {100*pnl.mean():+.2f} ({t:+.1f}, n {len(lo)})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s2_out.txt", "w").write(txt)
# pooled across horizons (one quote per market: the shortest available horizon to avoid double counting)
P = X[(X.mid > 0.02) & (X.mid < 0.98)].sort_values('h').drop_duplicates('ticker' if 'ticker' in X else ['event', 'bid', 'ask', 'y'])
f = sm.GLM(P.y, sm.add_constant(lg(P.mid)), family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(P.day)[0]})
lo = P[(P.mid >= .05) & (P.mid <= .20)]; pnl = lo.bid - lo.y - fee(lo.bid)
g = (pnl - pnl.mean()).groupby(lo.day.values).sum(); t = pnl.mean() / (np.sqrt((g ** 2).sum() * len(g) / (len(g) - 1)) / len(pnl))
line = (f"\nPooled (all horizons, n {len(P)}, {P.day.nunique()} days): slope {f.params.iloc[1]:.2f} ± {f.bse.iloc[1]:.2f} (day-clustered); "
        f"5–20¢ contracts won {lo.y.mean():.3f} vs {lo.mid.mean():.3f} priced; selling them at bid net {100*pnl.mean():+.2f}¢ (t {t:+.1f}, n {len(lo)}, {lo.day.nunique()} days)")
print(line); open(f"{R}/notes/s2_out.txt", "a").write(line)
