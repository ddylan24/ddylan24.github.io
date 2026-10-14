"""R1: are Kalshi daily BTC threshold markets (KXBTCD, 'BTC above K at 5pm ET') calibrated, and does a plain
lognormal model with Deribit DVOL beat them?  Strikes chosen within ±6% of spot at T−24h (no look-ahead selection).
Errors clustered by event (all strikes of one day share one outcome path)."""
import json, sys, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm
R = sys.argv[1]; D = f"{R}/data/r1"; out = []
S = pd.read_csv(f"{D}/markets.csv", parse_dates=['close']).drop_duplicates('ticker')
C = json.load(open(f"{D}/candles.json"))
P = pd.read_csv(f"{D}/btc_perp_1h.csv", index_col=0, parse_dates=True).iloc[:, 0]
V = pd.read_csv(f"{D}/dvol_1h.csv", index_col=0, parse_dates=True).iloc[:, 0]
# Deribit chart bars are stamped at their START; the close is known only at start+1h. Re-stamp by close time
# (using start stamps leaks one hour of future BTC moves into the model: T−6h fake edge +9¢/contract, t 3.6).
LEAK = '--leak' in sys.argv
if not LEAK:
    P.index = P.index + pd.Timedelta(hours=1); V.index = V.index + pd.Timedelta(hours=1)
def at(s, t): s = s[s.index <= t]; return s.iloc[-1] if len(s) else np.nan
def quote(cs, ts):
    best = None
    for c in cs:
        if c['end_period_ts'] <= ts: best = c
    if not best: return np.nan, np.nan
    b, a = best.get('yes_bid', {}).get('close_dollars'), best.get('yes_ask', {}).get('close_dollars')
    return (float(b) if b else np.nan), (float(a) if a else np.nan)
rows = []
for r in S.itertuples():
    cs = C.get(r.ticker, [])
    for h in (24, 6):
        t = r.close - pd.Timedelta(hours=h)
        b, a = quote(cs, int(t.timestamp()))
        if np.isnan(b) or np.isnan(a) or a - b > 0.10 or a <= 0: continue
        spot, vol = at(P, t), at(V, t) / 100
        Ty = h / (365.25 * 24)
        p_model = norm.cdf((np.log(spot / r.K) - 0.5 * vol ** 2 * Ty) / (vol * np.sqrt(Ty)))
        rows.append(dict(event=r.event, ticker=r.ticker, h=h, K=r.K, y=r.y, bid=b, ask=a, mid=(a + b) / 2, model=p_model, spot=spot, dvol=vol))
X = pd.DataFrame(rows)
X.to_csv(f"{D}/panel.csv", index=False)
clip = lambda p: np.clip(p, 0.005, 0.995)
def ll(p, y): p = clip(p); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
def cl_t(d, ev):
    """mean / cluster-robust SE: se = sqrt(Σ_g (Σ_{i∈g} (d_i − d̄))²) / n"""
    d = np.asarray(d, float); dm = d.mean()
    g = pd.Series(d - dm).groupby(np.asarray(ev)).sum()
    return dm / (np.sqrt((g ** 2).sum() * len(g) / (len(g) - 1)) / len(d))
out.append(f"Kalshi KXBTCD settled daily 5pm-ET markets, {S.event.nunique()} days ({S.close.min():%Y-%m-%d} → {S.close.max():%Y-%m-%d}), strikes within ±6% of spot at T−24h")
for h in (24, 6):
    x = X[X.h == h].copy()
    x['ll_m'], x['ll_v'] = ll(x.mid, x.y), ll(x.model, x.y)
    x['b_m'], x['b_v'] = (x.mid - x.y) ** 2, (x.model - x.y) ** 2
    base = x.y.mean()
    d = (x.b_v - x.b_m).values; dl = (x.ll_v - x.ll_m).values
    out.append(f"\nT−{h}h: {len(x)} quotes, {x.event.nunique()} days, YES rate {base:.3f}, median spread {100*(x.ask-x.bid).median():.0f}¢, mean DVOL {x.dvol.mean():.0%}")
    out.append(f"  Brier market {x.b_m.mean():.4f} | DVOL-lognormal {x.b_v.mean():.4f}   (model − market {d.mean():+.4f}, clustered t {cl_t(d, x.event.values):+.1f})")
    out.append(f"  log loss market {x.ll_m.mean():.4f} | model {x.ll_v.mean():.4f}   (model − market {dl.mean():+.4f}, clustered t {cl_t(dl, x.event.values):+.1f})")
    # calibration slope / intercept, clustered by event
    lg = lambda p: np.log(clip(p) / (1 - clip(p)))
    for nm, col in (('market', 'mid'), ('model', 'model')):
        f = sm.GLM(x.y, sm.add_constant(lg(x[col])), family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(x.event)[0]})
        out.append(f"  calibration {nm:<6}: logit(y) = {f.params.iloc[0]:+.2f} + {f.params.iloc[1]:.2f}·logit(p)   (slope se {f.bse.iloc[1]:.2f})")
    f = sm.GLM(x.y, sm.add_constant(pd.DataFrame({'mkt': lg(x.mid), 'model': lg(x.model)})), family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(x.event)[0]})
    out.append(f"  encompassing: logit(y) ~ {f.params['mkt']:.2f}·mkt (t {f.tvalues['mkt']:.1f}) + {f.params['model']:.2f}·model (t {f.tvalues['model']:.1f})")
    x['bin'] = pd.cut(x.mid, [0, .05, .15, .35, .65, .85, .95, 1])
    t = x.groupby('bin', observed=True).agg(n=('y', 'size'), price=('mid', 'mean'), model=('model', 'mean'), win=('y', 'mean'))
    out.append("  bins: " + "; ".join(f"{k}: n {r.n}, px {r.price:.3f}, model {r.model:.3f}, won {r.win:.3f}" for k, r in t.iterrows()))
    # trading rule: take the side the model favours by > e after fees, pay the spread
    fee = lambda p: 0.07 * p * (1 - p)
    for e in (0.03, 0.05):
        buy = x.model - x.ask > e + fee(x.ask); sell = x.bid - x.model > e + fee(x.bid)
        pnl = np.where(buy, x.y - x.ask - fee(x.ask), 0) + np.where(sell, x.bid - x.y - fee(x.bid), 0)
        tr = buy | sell
        if tr.sum():
            out.append(f"  rule |model−quote|>{e:.2f}+fee: {tr.sum()} trades ({buy.sum()} buys, {sell.sum()} sells) on {x[tr].event.nunique()} days, "
                       f"mean P&L {100*pnl[tr].mean():+.2f}¢/contract, clustered t {cl_t(pnl[tr], x[tr].event.values):+.1f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/r1_out{'_leak' if LEAK else ''}.txt", "w").write(txt)
