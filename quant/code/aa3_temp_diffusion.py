"""AA3: a diffusion model for hourly temperature contracts. From 1-min KMIA ASOS (integer °F), estimate for each clock hour h and
horizon τ (minutes) the drift μ_h(τ) = E[T_{t+τ} − T_t] and sd σ_h(τ) (empirical, 7 days, ±1h pooling).
Fair P(T_close > K | T_now) ≈ 1 − Φ((K − T_now − μ)/σ) (with a ±0.5°F rounding fudge). Compare with fill prices (Brier, calibration)
and test whether trading toward the model beats the market after the observed maker/taker structure."""
import sys, numpy as np, pandas as pd
from scipy.stats import norm
R = sys.argv[1]; D = f"{R}/data/aa1"; out = []
W = pd.read_csv(f"{D}/kmia_1min.csv", index_col=0, parse_dates=True).iloc[:, 0].astype(float)
W = W[~W.index.duplicated()].asfreq('1min').interpolate(limit=10)
F = pd.read_csv(f"{D}/fills.csv.gz"); F['ts'] = pd.to_datetime(F.ts, utc=True, format='mixed'); F['close'] = pd.to_datetime(F.close, utc=True, format='mixed')
F['tau'] = ((F.close - F.ts).dt.total_seconds() / 60).clip(1, 120).round()
F['obs'] = W.reindex(F.ts.dt.floor('min'), method='ffill').values
F = F.dropna(subset=['obs'])
# empirical moments of T(t+τ) − T(t) by hour-of-day of the TARGET time and τ
diffs = {}
for tau in range(1, 121):
    d = (W.shift(-tau) - W).dropna(); hr = (d.index + pd.Timedelta(minutes=tau)).hour
    diffs[tau] = pd.DataFrame({'d': d.values, 'h': hr})
def moments(tau, h):
    x = diffs[int(tau)]; x = x[x.h.isin([(h - 1) % 24, h, (h + 1) % 24])].d
    return x.mean(), max(x.std(), 0.35)
cache = {}
mu, sg = [], []
for tau, h in zip(F.tau, F.close.dt.hour):
    k = (int(tau), int(h))
    if k not in cache: cache[k] = moments(*k)
    mu.append(cache[k][0]); sg.append(cache[k][1])
F['mu'], F['sg'] = mu, sg
F['fair'] = 1 - norm.cdf((F.K - F.obs - F.mu) / np.sqrt(F.sg ** 2 + 0.29 ** 2))   # +uniform rounding variance (1/12)
w = F.n
out.append(f"{F.t.nunique()} markets, {len(F):,} fills; σ of 60-min temperature change (all hours): {diffs[60].d.std():.2f}°F, of 10-min: {diffs[10].d.std():.2f}°F")
out.append(f"  Brier (contract-weighted): model {np.average((F.fair - F.y) ** 2, weights=w):.4f} vs fill price {np.average((F.p - F.y) ** 2, weights=w):.4f}")
for lo, hi in ((0, 10), (10, 30), (30, 60), (60, 200)):
    g = F[(F.tau > lo) & (F.tau <= hi)]
    if len(g): out.append(f"  τ {lo:>3}–{hi:<3} min: n {len(g):6d}  Brier model {np.average((g.fair - g.y)**2, weights=g.n):.4f} vs price {np.average((g.p - g.y)**2, weights=g.n):.4f}")
# trading toward the model: buy YES at the fill price when fair − p > e (i.e. act like the taker whenever model disagrees)
for e in (0.05, 0.10, 0.20):
    b = F[F.fair - F.p > e]; s = F[F.p - F.fair > e]
    pnl = np.r_[(b.y - b.p).values, (s.p - s.y).values]; mk = np.r_[b.t.values, s.t.values]
    if len(pnl) > 10:
        g = pd.Series(pnl).groupby(mk).sum(); t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))
        out.append(f"  trade at fill prices when |model − price| > {e:.2f}: {len(pnl)} fills, mean {100*pnl.mean():+.2f}¢/contract, market-clustered t {t:+.1f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/aa3_out.txt", "w").write(txt)
