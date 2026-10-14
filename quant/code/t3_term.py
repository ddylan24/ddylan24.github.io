"""T3: term structure of BTC distributions implied by Polymarket (noon ET, Binance USDT) and Kalshi (5pm ET, CF BRTI) threshold
contracts, vs Deribit. For each venue-expiry fit a lognormal (center F, total variance w) to mids: P(S>K) = N((ln F/K − w/2)/√w).
No-calendar-arbitrage: total variance w must be non-decreasing in T across ALL expiries of the same underlying."""
import sys, numpy as np, pandas as pd
from scipy.stats import norm
from scipy.optimize import least_squares
R = sys.argv[1]; out = []
D = pd.read_csv(f"{R}/data/q3/compare_smooth.csv", parse_dates=['expiry'])
D = D[(D.mid > 0.03) & (D.mid < 0.97)]
rows = []
for (v, e), g in D.groupby(['venue', 'expiry']):
    if len(g) < 4: continue
    def res(th): F, lw = th; w = np.exp(lw); return g.mid - norm.cdf((np.log(F / g.K_usd) - w / 2) / np.sqrt(w))
    f = least_squares(res, [g.K_usd.median(), np.log(0.0004)])
    F, w = f.x[0], np.exp(f.x[1]); T = g['T'].iloc[0]
    # options-implied lognormal fit to the same strikes (p_opt)
    def res2(th): F2, lw2 = th; w2 = np.exp(lw2); return g.p_opt - norm.cdf((np.log(F2 / g.K_usd) - w2 / 2) / np.sqrt(w2))
    f2 = least_squares(res2, [g.K_usd.median(), np.log(0.0004)])
    rows.append(dict(venue=v, expiry=e, T_days=T * 365.25, n=len(g), F=F, vol=np.sqrt(w / T), w=w, rmse=np.sqrt(np.mean(res(f.x) ** 2)),
                     F_opt=f2.x[0], vol_opt=np.sqrt(np.exp(f2.x[1]) / T)))
X = pd.DataFrame(rows).sort_values('T_days')
out.append(f"{'venue':<11} {'expiry (UTC)':<12} {'days':>5} {'n':>3} {'center':>8} {'vol':>5} {'w·1e4':>6} {'fit rmse':>8} | options: {'center':>8} {'vol':>5}")
for r in X.itertuples():
    out.append(f"{r.venue:<11} {r.expiry:%m-%d %H:%M} {r.T_days:5.2f} {r.n:3d} {r.F:8.0f} {r.vol:5.0%} {r.w*1e4:6.1f} {100*r.rmse:7.2f}¢ | {r.F_opt:8.0f} {r.vol_opt:5.0%}")
viol = [(a.venue, a.expiry, b.venue, b.expiry, a.w, b.w) for a, b in zip(X.itertuples(), X.iloc[1:].itertuples()) if b.w < a.w - 1e-6]
out.append(f"\nCalendar (total-variance) violations between consecutive expiries: {len(viol)}")
for a, ea, b, eb, wa, wb in viol: out.append(f"  {a} {ea:%m-%d %H:%M} w={wa*1e4:.1f}e-4  >  {b} {eb:%m-%d %H:%M} w={wb*1e4:.1f}e-4")
out.append(f"Mean implied vol: Polymarket {X[X.venue=='Polymarket'].vol.mean():.0%}, Kalshi {X[X.venue=='Kalshi'].vol.mean():.0%}, options on same strikes {X.vol_opt.mean():.0%}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/t3_out.txt", "w").write(txt)
