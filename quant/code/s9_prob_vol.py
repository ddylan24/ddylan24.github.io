"""S9: how volatile should a probability be?  If the outcome is 1{X_T > 0} with X a Brownian motion (unit variance per unit time),
the fair price is p_t = N(X_t/√τ), τ = T − t, and Itô gives dp = φ(N⁻¹(p))/√τ · dW  (drift-free: a martingale).
So the variance of a daily change is  Var(Δp) ≈ φ(N⁻¹(p))² · Δt/τ  — largest at p=0.5, exploding as τ → 0.
Test the shape on Polymarket daily paths: regress log E[(Δp)²] on log φ(N⁻¹(p))² and log(1/τ)."""
import json, sys, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm
R = sys.argv[1]; out = []
H = json.load(open(f"{R}/data/pm/hist.json")); M = pd.read_csv(f"{R}/data/pm/markets.csv", dtype={'tok': str})
M['end'] = pd.to_datetime(M.end, utc=True, format='mixed', errors='coerce'); M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed', errors='coerce')
rows = []
for m in M.itertuples():
    h = H.get(m.tok)
    if not h or pd.isna(m.end) or pd.isna(m.closed): continue
    s = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True): x['p'] for x in h}).sort_index()
    s = s[(s.index < m.closed - pd.Timedelta(days=1)) & (s.index < m.end)]
    if len(s) < 10: continue
    p = s.values[:-1]; dp = np.diff(s.values); tau = (m.end - s.index[:-1]).total_seconds().values / 86400
    for a, b, c in zip(p, dp, tau):
        if 0.02 < a < 0.98 and c >= 1: rows.append((m.event, a, b, c))
D = pd.DataFrame(rows, columns=['event', 'p', 'dp', 'tau'])
D['phi2'] = norm.pdf(norm.ppf(D.p)) ** 2
D['pb'] = pd.cut(D.p, [0.02, .1, .2, .35, .65, .8, .9, .98]); D['tb'] = pd.cut(D.tau, [1, 3, 7, 14, 30, 90, 365, 5000])
out.append(f"{len(D):,} daily changes from {D.event.nunique()} events (price 2–98%, ≥1 day to scheduled end)")
g = D.groupby(['pb', 'tb'], observed=True).agg(v=('dp', lambda x: (x ** 2).mean()), n=('dp', 'size'), phi2=('phi2', 'mean'), tau=('tau', 'mean')).reset_index()
g = g[g.n >= 30]
X = sm.add_constant(np.c_[np.log(g.phi2), np.log(1 / g.tau)]); f = sm.WLS(np.log(g.v), X, weights=g.n).fit()
out.append(f"Cell regression log E[Δp²] = a + β₁·log φ(N⁻¹p)² + β₂·log(1/τ):  β₁ {f.params.iloc[1]:.2f} ± {f.bse.iloc[1]:.2f} (theory 1),  β₂ {f.params.iloc[2]:.2f} ± {f.bse.iloc[2]:.2f} (theory 1),  R² {f.rsquared:.2f}")
out.append("\nMean squared daily change (¢²) by price bucket (rows) and days to end (cols):")
piv = g.pivot(index='pb', columns='tb', values='v') * 1e4
out.append(piv.round(1).to_string())
th = D.groupby('pb', observed=True).apply(lambda x: pd.Series({'actual_sd': np.sqrt((x.dp ** 2).mean()) * 100, 'theory_shape': np.sqrt(x.phi2.mean())}), include_groups=False)
th['theory_scaled'] = th.theory_shape / th.theory_shape.max() * th.actual_sd.max()
out.append("\nBy price: actual sd of daily change (¢) vs theory shape φ(N⁻¹p) scaled to the max\n" + th.round(2).to_string())
txt = "\n".join(out); print(txt); open(f"{R}/notes/s9_out.txt", "w").write(txt)
