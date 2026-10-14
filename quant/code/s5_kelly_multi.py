"""S5: Kelly for mutually exclusive outcomes (one of n wins; YES contract i costs p_i, pays 1).
Kelly (1956) horse-race solution: sort by q_i/p_i; bet set S = outcomes with q_i/p_i > R, where
   R = (1 − Σ_S q_i) / (1 − Σ_S p_i)   (cash kept back, as a fraction of wealth),  stake_i = q_i − R·p_i  (fraction of wealth spent on i).
Check against numeric maximisation of E[ln W]; compare with treating each bucket as an independent binary bet."""
import sys, numpy as np, pandas as pd
from scipy.optimize import minimize
R_ = sys.argv[1]; out = []
def kelly_exclusive(q, p):
    q, p = np.asarray(q, float), np.asarray(p, float); order = np.argsort(-q / p); S = []
    R = 1.0
    for i in order:
        S2 = S + [i]; qs, ps = q[S2].sum(), p[S2].sum()
        if ps >= 1: break
        R2 = (1 - qs) / (1 - ps)
        if q[i] / p[i] > R2: S, R = S2, R2
        else: break
    f = np.zeros_like(q); f[S] = q[S] - R * p[S]; return f, R
def growth(f, q, p):
    cash = 1 - f.sum(); return float(np.sum(q * np.log(cash + f / p)))
def numeric(q, p):
    n = len(q); cons = [{'type': 'ineq', 'fun': lambda f: 1 - f.sum()}]
    r = minimize(lambda f: -growth(f, q, p), np.full(n, 0.01), bounds=[(0, 1)] * n, constraints=cons, method='SLSQP')
    return r.x
# example: 6 temperature buckets, prices sum 1.04 (Kalshi weather-like), my belief differs
p = np.array([0.03, 0.12, 0.35, 0.33, 0.15, 0.06]); q = np.array([0.02, 0.10, 0.30, 0.40, 0.15, 0.03])
f, R = kelly_exclusive(q, p); fn = numeric(q, p)
out.append(f"Example: prices {p.tolist()} (Σ {p.sum():.2f}), beliefs {q.tolist()}")
out.append(f"  closed form stakes {np.round(f,4).tolist()}, cash kept {R:.4f}, growth {growth(f,q,p):.5f}")
out.append(f"  numeric optimum   {np.round(fn,4).tolist()}, growth {growth(fn,q,p):.5f}")
# naive: independent binary Kelly on each bucket (YES if q>p: (q−p)/(1−p); NO if q<p: (p−q)/p on NO at 1−p)
ind = np.where(q > p, (q - p) / (1 - p), 0)
out.append(f"  independent-binary Kelly on YES legs {np.round(ind,4).tolist()} (Σ {ind.sum():.3f}) growth {growth(ind/ max(1,ind.sum()) if ind.sum()>1 else ind,q,p):.5f}")
# insight: with an overround, the exclusive solution only backs outcomes with q/p > R; selling (NO) legs: buying NO on i = buying all other YES.
# simulation: true probs q, many rounds, compare full-Kelly exclusive vs independent binary stakes vs half Kelly
rng = np.random.default_rng(3); T = 2000; res = {}
for name, stake in (('exclusive Kelly', f), ('½ exclusive Kelly', f / 2), ('independent binaries', ind)):
    W = []
    for s in range(400):
        w = 0.0; outc = rng.choice(len(q), T, p=q)
        for k in outc:
            w += np.log(max(1 - stake.sum() + stake[k] / p[k], 1e-12))
        W.append(w / T)
    res[name] = np.array(W)
    out.append(f"  sim {name:<22}: mean log-growth/round {np.mean(W):+.5f} (theory {growth(stake,q,p):+.5f}), P(lose money over {T}) {np.mean(np.array(W)<0):.0%}")
# noisy beliefs: estimate q with error; how often does exclusive Kelly lose?
out.append("\nWith noisy beliefs (true q, you estimate q̂ = normalize(q·e^{ε}), ε~N(0,σ)), stakes from q̂, growth under true q:")
for sig in (0.1, 0.25, 0.5):
    g = []
    for s in range(2000):
        qh = q * np.exp(rng.normal(0, sig, len(q))); qh /= qh.sum()
        fh, _ = kelly_exclusive(qh, p); g.append((growth(fh, q, p), growth(fh / 2, q, p)))
    g = np.array(g); out.append(f"  σ={sig}: full Kelly E[growth] {g[:,0].mean():+.5f} (neg {np.mean(g[:,0]<0):.0%}), half Kelly {g[:,1].mean():+.5f} (neg {np.mean(g[:,1]<0):.0%})")
txt = "\n".join(out); print(txt); open(f"{R_}/notes/s5_out.txt", "w").write(txt)
