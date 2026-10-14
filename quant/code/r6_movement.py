"""R6: excess belief movement (Augenblick & Rabin 2021, QJE). If prices π_t are a martingale ending at the outcome y∈{0,1}:
   E[movement m] = E[uncertainty reduction r],  m = Σ(π_{t+1}−π_t)²,  r = π_0(1−π_0) − y(1−y) = π_0(1−π_0).
Proof per step: E[(Δπ)²] = E[π_{t+1}²] − E[π_t²] = E[u_t − u_{t+1}] with u = π(1−π). Holds at any sampling frequency."""
import json, sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []; SKIP = int(sys.argv[2]) if len(sys.argv) > 2 else 0
H = json.load(open(f"{R}/data/pm/hist.json"))
M = pd.read_csv(f"{R}/data/pm/markets.csv", dtype={'tok': str})
M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed', errors='coerce')
rows = []
for r in M.itertuples():
    h = H.get(r.tok)
    if not h or len(h) < 5 or pd.isna(r.yes_won): continue
    s = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True): x['p'] for x in h}).sort_index()
    s = s[s.index < r.closed - pd.Timedelta(hours=24)] if pd.notna(r.closed) else s     # stop a day before close (look-ahead)
    s = s.iloc[SKIP:]
    if len(s) < 5: continue
    p = np.r_[s.values, r.yes_won]
    d = np.diff(p)
    rows.append(dict(vol=r.vol, event=r.event, cat=r.cat if isinstance(r.cat, str) else 'other', days=len(s), p0=p[0],
                     m=(d ** 2).sum(), m_path=(d[:-1] ** 2).sum(), jump=d[-1] ** 2, r=p[0] * (1 - p[0]),
                     ac=pd.Series(d[:-1]).autocorr() if len(d) > 10 else np.nan, y=r.yes_won))
D = pd.DataFrame(rows)
def ratio(g): return g.m.sum() / g.r.sum()
def boot(g, B=2000, rng=np.random.default_rng(1)):
    ev = g.event.fillna(g.index.to_series().astype(str)).values; u = pd.unique(ev); idx = {e: np.where(ev == e)[0] for e in u}
    v = []
    for _ in range(B):
        take = np.concatenate([idx[e] for e in rng.choice(u, len(u))]); v.append(g.m.values[take].sum() / g.r.values[take].sum())
    return np.std(v)
out.append(f"[skip first {SKIP} daily points] {len(D)} resolved Polymarket markets (daily prices, start → 1 day before close, then the outcome)")
out.append(f"  Σm / Σr = {ratio(D):.3f} ± {boot(D):.3f} (event-clustered bootstrap)   [rational benchmark 1.000]")
out.append(f"  movement split: path {D.m_path.sum()/D.r.sum():.3f} + final jump {D.jump.sum()/D.r.sum():.3f}")
out.append(f"  mean lag-1 autocorrelation of daily changes {D.ac.mean():+.3f} (negative ⇒ noise/overreaction that reverts)")
D['len'] = pd.cut(D.days, [0, 14, 60, 180, 2000], labels=['<2w', '2w–2m', '2–6m', '>6m'])
for k, g in D.groupby('len', observed=True): out.append(f"  horizon {k:<6} n={len(g):4d}  Σm/Σr {ratio(g):.3f} ± {boot(g, 500):.3f}   path share {g.m_path.sum()/g.m.sum():.0%}")
D['volq'] = pd.qcut(D.vol, 3, labels=['low vol', 'mid vol', 'high vol'])
for k, g in D.groupby('volq', observed=True): out.append(f"  volume tercile {k:<8} n={len(g):4d}  Σm/Σr {ratio(g):.3f} ± {boot(g, 500):.3f}")
D['p0b'] = pd.cut(D.p0, [0, .1, .3, .7, .9, 1], labels=['<10%', '10–30%', '30–70%', '70–90%', '>90%'])
for k, g in D.groupby('p0b', observed=True): out.append(f"  start price {k:<7} n={len(g):4d}  Σm/Σr {ratio(g):.3f}")
# noise check: simulate a true martingale with 0.5¢ i.i.d. quote noise at the same lengths
rng = np.random.default_rng(2); sim = []
for r in D.sample(min(800, len(D)), random_state=0).itertuples():
    n = r.days; p0 = r.p0
    x = np.log(p0 / (1 - p0)) if 0 < p0 < 1 else 0
    # logit random walk is not a martingale in p; use a bounded martingale: Beta-Bernoulli learning from signals
    a, b = p0 * 4, (1 - p0) * 4; th = rng.beta(a, b); path = [a / (a + b)]
    for t in range(n - 1):
        s = rng.random() < th; a += s * 0.3; b += (1 - s) * 0.3; path.append(a / (a + b))
    y = int(rng.random() < th); path = np.clip(np.array(path) + rng.normal(0, 0.005, n), 0, 1)
    sim.append(((np.diff(np.r_[path, y])) ** 2).sum() / (path[0] * (1 - path[0])) if 0 < path[0] < 1 else np.nan)
out.append(f"\nSanity check (simulated Bayesian learner, same lengths, +0.5¢ quote noise): mean m/r {np.nanmean(sim):.3f}; pooled ratio ~1 expected")
txt = "\n".join(out); print(txt); open(f"{R}/notes/r6_out.txt", "a").write(txt)
