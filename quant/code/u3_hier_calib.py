"""U3: partial pooling of calibration slopes across groups (empirical Bayes / normal-normal hierarchical model).
Per group g: logit(y) = a_g + b_g·logit(p), estimate b̂_g with SE s_g (cluster-robust by event).
Model: b̂_g ~ N(b_g, s_g²), b_g ~ N(μ, τ²). τ² by DerSimonian–Laird method of moments; posterior mean
   b̃_g = μ̂ + (τ²/(τ²+s_g²))·(b̂_g − μ̂)   (shrinks noisy groups toward the pooled slope).
Out-of-sample check: estimate on the first half of days, compare raw vs shrunk slopes against the second-half slopes."""
import sys, numpy as np, pandas as pd, statsmodels.api as sm
R = sys.argv[1]; out = []
clip = lambda p: np.clip(p, 0.01, 0.99); lg = lambda p: np.log(clip(p) / (1 - clip(p)))
W = pd.read_csv(f"{R}/data/pm/kalshi_weather.csv").dropna(subset=['p'])
W['date'] = pd.to_datetime(W.event.str.split('-').str[1], format='%y%b%d')
def slope(d):
    f = sm.GLM(d.y, sm.add_constant(lg(d.p)), family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.event)[0]})
    return f.params.iloc[1], f.bse.iloc[1]
def eb(b, s):
    w = 1 / s ** 2; mu_fe = np.sum(w * b) / w.sum(); Q = np.sum(w * (b - mu_fe) ** 2); k = len(b)
    tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    ws = 1 / (s ** 2 + tau2); mu = np.sum(ws * b) / ws.sum()
    return mu, tau2, mu + tau2 / (tau2 + s ** 2) * (b - mu), Q
def run(d, label):
    G = d.groupby('series').apply(lambda g: pd.Series(slope(g), index=['b', 's']), include_groups=False)
    mu, tau2, shr, Q = eb(G.b.values, G.s.values); G['shrunk'] = shr
    out.append(f"{label}: pooled μ̂ {mu:.2f}, between-city τ̂ {np.sqrt(tau2):.2f}, Cochran Q {Q:.1f} on {len(G)-1} df")
    for c, r in G.iterrows(): out.append(f"   {c[6:]:<4} raw b {r.b:.2f} ± {r.s:.2f} → shrunk {r.shrunk:.2f}")
    return G
days = sorted(W.date.unique()); cut = days[len(days) // 2]
A = run(W, "All days")
E = run(W[W.date < cut], f"First half (< {pd.Timestamp(cut):%m-%d})")
L = W[W.date >= cut].groupby('series').apply(lambda g: slope(g)[0], include_groups=False)
err_raw = ((E.b - L) ** 2).mean(); err_shr = ((E.shrunk - L) ** 2).mean(); err_pool = ((E.b.mean() * 0 + np.average(E.b, weights=1 / E.s ** 2) - L) ** 2).mean()
out.append(f"\nPredicting second-half city slopes: MSE raw {err_raw:.3f}, shrunk {err_shr:.3f}, fully pooled {err_pool:.3f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/u3_out.txt", "w").write(txt)
