"""R5: Shin's insider-trading model for removing overround ('vig'), compared with other de-vig methods
on complete Kalshi weather events (6 temperature buckets per city-day, exactly one wins).
Shin (1993): a bookmaker facing a fraction z of insiders quotes π_i with Σπ = 1+overround; true probabilities
p_i = [sqrt(z² + 4(1−z) π_i²/Σπ) − z] / (2(1−z)),  z chosen so Σp = 1.  Longshots get shaded down MORE than favorites."""
import sys, numpy as np, pandas as pd
from scipy.optimize import brentq
R = sys.argv[1]; out = []
d = pd.read_csv(f"{R}/data/pm/kalshi_weather.csv")
g = d.groupby('event')
ok = g.filter(lambda e: e.p.notna().all() and len(e) >= 5 and e.y.sum() == 1)
def shin(pi):
    S = pi.sum()
    f = lambda z: (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z).sum() / (2 * (1 - z)) - 1
    if S <= 1: return pi / S, 0.0
    z = brentq(f, 0, 0.99); return (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z) / (2 * (1 - z)), z
def power(pi):
    k = brentq(lambda k: (pi ** k).sum() - 1, 0.2, 5); return pi ** k
def additive(pi): return np.clip(pi - (pi.sum() - 1) / len(pi), 1e-4, 1)
res = {m: [] for m in ['raw', 'multiplicative', 'additive', 'power', 'shin']}; zs = []; sums = []
for which in ['p', 'ask']:
    res = {m: [] for m in res}; zs = []; sums = []
    for ev, e in ok.groupby('event'):
        pi = e[which].values.astype(float); y = e.y.values
        if which == 'ask' and np.isnan(pi).any(): continue
        sums.append(pi.sum())
        sp, z = shin(pi); zs.append(z)
        for m, q in [('raw', pi), ('multiplicative', pi / pi.sum()), ('additive', additive(pi)), ('power', power(pi)), ('shin', sp)]:
            q = np.clip(q, 1e-4, 1 - 1e-4)
            res[m].append(dict(brier=((q - y) ** 2).sum(), logloss=-np.log(q[y == 1][0]), low=(q[pi < .1]).sum(), low_y=y[pi < .1].sum()))
    out.append(f"\nUsing {'mid' if which=='p' else 'ask'} prices: {len(sums)} complete city-day events; Σ prices median {np.median(sums):.3f}; Shin z median {np.median(zs):.3f}")
    out.append(f"  {'method':<15} {'Brier/event':>11} {'log loss':>9} {'Σ prob on <10¢ buckets':>23} (actual wins {sum(r['low_y'] for r in res['raw'])})")
    for m, r in res.items():
        r = pd.DataFrame(r); out.append(f"  {m:<15} {r.brier.mean():11.4f} {r.logloss.mean():9.4f} {r.low.sum():23.1f}")
    # paired test shin vs multiplicative log loss
    a = pd.DataFrame(res['shin']).logloss.values - pd.DataFrame(res['multiplicative']).logloss.values
    out.append(f"  Shin − multiplicative log loss: {a.mean():+.4f} ± {a.std(ddof=1)/np.sqrt(len(a)):.4f} (t {a.mean()/(a.std(ddof=1)/np.sqrt(len(a))):.1f})")
# illustration
pi = np.array([0.60, 0.25, 0.12, 0.05, 0.02]) * 1.08
sp, z = shin(pi)
out.append(f"\nIllustration, quotes {np.round(pi,3).tolist()} (Σ {pi.sum():.2f}): multiplicative {np.round(pi/pi.sum(),4).tolist()}; Shin (z={z:.3f}) {np.round(sp,4).tolist()}; power {np.round(power(pi),4).tolist()}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/r5_out.txt", "w").write(txt)
