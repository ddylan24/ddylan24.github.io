"""S6: Murphy (1973) decomposition of the Brier score:  BS = REL − RES + UNC  (+ within-bin term when binning)
   REL = Σ_k n_k (p̄_k − ȳ_k)² / N    (calibration error; 0 is perfect)
   RES = Σ_k n_k (ȳ_k − ȳ)² / N       (how much forecasts separate outcomes; higher is better)
   UNC = ȳ(1 − ȳ)                      (base-rate difficulty)
Skill = 1 − BS/UNC = (RES − REL)/UNC. Applied to every forecast dataset in this project."""
import sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []
def murphy(p, y, bins=np.r_[0, .02, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, .98, 1.0001]):
    d = pd.DataFrame({'p': p, 'y': y}).dropna(); d['b'] = pd.cut(d.p, bins, right=False); N = len(d); yb = d.y.mean()
    g = d.groupby('b', observed=True).agg(n=('y', 'size'), pb=('p', 'mean'), ybar=('y', 'mean'))
    rel = (g.n * (g.pb - g.ybar) ** 2).sum() / N; res = (g.n * (g.ybar - yb) ** 2).sum() / N; unc = yb * (1 - yb)
    bs = ((d.p - d.y) ** 2).mean(); wb = bs - (rel - res + unc)
    return dict(N=N, BS=bs, REL=rel, RES=res, UNC=unc, within=wb, skill=1 - bs / unc)
sets = []
for h in (30, 7, 1):
    d = pd.read_csv(f"{R}/data/pm/calib_sched_h{h}.csv"); sets.append((f"Polymarket {h}d before scheduled end", d.p, d.y))
w = pd.read_csv(f"{R}/data/pm/kalshi_weather.csv"); sets.append(("Kalshi weather buckets (mid)", w.p, w.y))
try:
    k = pd.read_csv(f"{R}/data/r1/panel.csv")
    for h in (24, 6): kk = k[k.h == h]; sets.append((f"Kalshi BTC daily, T−{h}h market", kk.mid, kk.y)); sets.append((f"Kalshi BTC daily, T−{h}h DVOL model", kk.model, kk.y))
except Exception: pass
out.append(f"{'dataset':<36} {'N':>5} {'Brier':>7} {'REL':>7} {'RES':>7} {'UNC':>7} {'within':>7} {'skill':>6}")
for nm, p, y in sets:
    m = murphy(np.asarray(p, float), np.asarray(y, float))
    out.append(f"{nm:<36} {m['N']:5d} {m['BS']:7.4f} {m['REL']:7.4f} {m['RES']:7.4f} {m['UNC']:7.4f} {m['within']:+7.4f} {m['skill']:6.1%}")
out.append("\nReading: REL is the part a recalibration map could remove; RES is information. Skill ≈ (RES − REL)/UNC.")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s6_out.txt", "w").write(txt)
