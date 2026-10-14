"""S8: does a public NWP forecast add information to Kalshi daily-high temperature markets?
Forecast: official NWS GFS MOS daytime max (n_x) from the 12Z run on the day before (published ~16Z, before the market
snapshot at local midnight), archived by Iowa Environmental Mesonet. (Open-Meteo hit its daily limit on this IP.)
Model: daily high T ~ N(F + μ, σ²) with integer rounding; bucket prob Φ((hi+½−m)/σ) − Φ((lo−½−m)/σ). μ, σ fitted by maximum
likelihood on the first half of days, evaluated on the second half vs the market (de-vigged by additive and multiplicative)."""
import json, re, subprocess, sys, numpy as np, pandas as pd
from scipy.stats import norm
from scipy.optimize import minimize
R = sys.argv[1]; out = []
ST = {'KXHIGHNY': 'KNYC', 'KXHIGHCHI': 'KMDW', 'KXHIGHMIA': 'KMIA', 'KXHIGHLAX': 'KLAX', 'KXHIGHAUS': 'KAUS', 'KXHIGHDEN': 'KDEN'}
W = pd.read_csv(f"{R}/data/pm/kalshi_weather.csv")
W['date'] = pd.to_datetime(W.event.str.split('-').str[1], format='%y%b%d')
F = {}
import io
for s, stn in ST.items():
    u = (f"https://mesonet.agron.iastate.edu/cgi-bin/request/mos.py?station={stn}&model=GFS"
         f"&sts={W.date.min() - pd.Timedelta(days=2):%Y-%m-%d}T00:00Z&ets={W.date.max() + pd.Timedelta(days=1):%Y-%m-%d}T00:00Z&format=csv")
    import os, time
    fn = f"{R}/data/s8/mos_{stn}.csv"
    for i in range(6):
        if os.path.exists(fn) and open(fn).readline().startswith('runtime'): break
        txt = subprocess.run(['curl', '-s', '--max-time', '120', u], capture_output=True, text=True).stdout
        if txt.startswith('runtime'): open(fn, 'w').write(txt); break
        print(stn, 'retry', txt[:80], flush=True); time.sleep(20 * (i + 1))
    m = pd.read_csv(fn, parse_dates=['runtime', 'ftime'])
    m = m[m.n_x.notna() & (m.runtime.dt.hour == 12)]
    for r in m.itertuples():
        day = (r.ftime - pd.Timedelta(hours=12)).normalize()          # 00Z valid time closes the daytime-max window of the previous date
        if (day - r.runtime.normalize()).days == 1: F[(s, day)] = float(r.n_x)   # 12Z run the day before
W['F'] = [F.get((s, d), np.nan) for s, d in zip(W.series, W.date)]
def bounds(sub):
    n = [int(x) for x in re.findall(r'-?\d+', sub)]
    if 'above' in sub: return n[0], np.inf
    if 'below' in sub: return -np.inf, n[0]
    return n[0], n[1]
W[['lo', 'hi']] = W['sub'].apply(lambda s: pd.Series(bounds(s)))
ok = W.groupby('event').filter(lambda e: e.p.notna().all() and e.y.sum() == 1 and e.F.notna().all() and len(e) >= 5).copy()
def probs(e, mu, sg):
    m = e.F + mu
    return (norm.cdf((e.hi + 0.5 - m) / sg) - norm.cdf((e.lo - 0.5 - m) / sg)).clip(1e-4, 1)
days = sorted(ok.date.unique()); cut = days[len(days) // 2]
tr, te = ok[ok.date < cut], ok[ok.date >= cut]
def nll(th, d):
    mu, ls = th; return -np.log(probs(d, mu, np.exp(ls))[d.y == 1]).sum()
fit = {}
for s, g in tr.groupby('series'):
    r = minimize(nll, [0, np.log(2.5)], args=(g,), method='Nelder-Mead'); fit[s] = (r.x[0], np.exp(r.x[1]))
out.append(f"{ok.event.nunique()} complete city-days ({days[0]:%m-%d} → {days[-1]:%m-%d}); train < {cut:%m-%d}, test ≥ {cut:%m-%d}")
out.append("Fitted forecast bias μ (actual − forecast, °F) and error sd σ by city (train): " + ", ".join(f"{s[6:]} μ {m:+.1f} σ {sg:.1f}" for s, (m, sg) in fit.items()))
te = te.copy(); te['model'] = np.nan
for s, g in te.groupby('series'): te.loc[g.index, "model"] = np.asarray(probs(g, *fit[s]))
te['model'] = te.model / te.groupby('event').model.transform('sum')
te['mkt'] = (te.p - (te.groupby('event').p.transform('sum') - 1) / te.groupby('event').p.transform('size')).clip(1e-3, 1)   # additive de-vig (best in R5)
te['mkt'] = te.mkt / te.groupby('event').mkt.transform('sum')
for w in (0.0, 0.25, 0.5, 0.75, 1.0):
    te[f'mix{w}'] = (1 - w) * te.mkt + w * te.model
def score(col):
    win = te[te.y == 1]; ll = -np.log(win[col].clip(1e-4)); br = te.assign(e=(te[col] - te.y) ** 2).groupby('event').e.sum()
    return ll.mean(), br.mean(), ll.values
ll_m, br_m, v_m = score('mkt')
out.append(f"\nTest set {te.event.nunique()} city-days:")
for col, nm in [('mkt', 'market (additive de-vig)'), ('model', 'NWP model'), ('mix0.25', '75% market + 25% model'), ('mix0.5', '50/50'), ('mix0.75', '25% market + 75% model')]:
    ll, br, v = score(col); d = v - v_m
    out.append(f"  {nm:<26} log loss {ll:.4f}  Brier {br:.4f}   Δlog loss vs market {d.mean():+.4f} (t {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))) if d.std()>0 else 0:+.1f})")
# trading: buy bucket at ask when model − ask > 5¢ + fee; sell at bid when bid − model > 5¢ + fee
fee = lambda p: 0.07 * p * (1 - p)
for e in (0.03, 0.05, 0.10):
    b = te[(te.model - te.ask) > e + fee(te.ask)]; s = te[(te.bid - te.model) > e + fee(te.bid)]
    pnl = pd.concat([b.y - b.ask - fee(b.ask), s.bid - s.y - fee(s.bid)]); ev = pd.concat([b.event, s.event])
    g = (pnl - pnl.mean()).groupby(ev.values).sum(); t = pnl.mean() / (np.sqrt((g ** 2).sum()) / len(pnl)) if len(pnl) > 2 else np.nan
    out.append(f"  trade when |model − quote| > {e:.2f}+fee: {len(b)} buys, {len(s)} sells, mean {100*pnl.mean():+.2f}¢/contract (event-clustered t {t:+.1f})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s8_out.txt", "w").write(txt)
