"""AA2: which series' maker fill edges survive partial pooling? Per series: mean maker P&L per contract with market-clustered SE
(ratio estimator: Σ pnl / Σ contracts, SE via cluster bootstrap over markets). Then DerSimonian–Laird τ² and posterior means
b̃ = μ̂ + τ²/(τ²+s²)(b̂ − μ̂) (U3 method). Data: AA1 (KXTEMPMIAH) + Y1 (FX/crypto 15m) fills, 7 days, settlement-marked."""
import sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []; rng = np.random.default_rng(0)
A = pd.read_csv(f"{R}/data/aa1/fills.csv.gz"); A['series'] = 'KXTEMPMIAH'; A['maker'] = np.where(A.side == 'yes', A.p - A.y, A.y - A.p) * A.n
A = A.rename(columns={'t': 'ticker'})[['series', 'ticker', 'maker', 'n']]
Y = pd.read_csv(f"{R}/data/y1/fills.csv.gz", usecols=['series', 'ticker', 'maker', 'n'])
F = pd.concat([A, Y])
rows = []
for s, g in F.groupby('series'):
    m = g.groupby('ticker').agg(p=('maker', 'sum'), n=('n', 'sum'))
    b = 100 * m.p.sum() / m.n.sum()
    boots = [100 * m.p.values[i].sum() / m.n.values[i].sum() for i in (rng.integers(0, len(m), len(m)) for _ in range(1000))]
    rows.append(dict(series=s, markets=len(m), contracts=m.n.sum(), b=b, s=np.std(boots)))
X = pd.DataFrame(rows)
w = 1 / X.s ** 2; mu_fe = (w * X.b).sum() / w.sum(); Q = (w * (X.b - mu_fe) ** 2).sum(); k = len(X)
tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum())); ws = 1 / (X.s ** 2 + tau2); mu = (ws * X.b).sum() / ws.sum()
X['shrunk'] = mu + tau2 / (tau2 + X.s ** 2) * (X.b - mu); X['z'] = X.b / X.s
out.append(f"Maker fill P&L to settlement (¢/contract), 7 days; pooled μ̂ {mu:+.2f}¢, between-series τ̂ {np.sqrt(tau2):.2f}¢, Cochran Q {Q:.1f} on {k-1} df")
for r in X.sort_values('shrunk', ascending=False).itertuples():
    out.append(f"  {r.series:<12} markets {r.markets:4d}  raw {r.b:+6.2f} ± {r.s:4.2f} (z {r.z:+.1f})  → shrunk {r.shrunk:+6.2f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/aa2_out.txt", "w").write(txt)
