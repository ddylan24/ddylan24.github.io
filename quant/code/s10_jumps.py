"""S10: jump risk in near-certain contracts. From a state p ≥ 0.90, how often does the price fall ≥10/20/40¢ in one day,
vs what the diffusion law of S9 (sd = c·φ(N⁻¹p)/τ^0.53, c fitted) predicts under normality? Also: how often do they resolve NO?"""
import json, sys, numpy as np, pandas as pd
from scipy.stats import norm
R = sys.argv[1]; out = []
H = json.load(open(f"{R}/data/pm/hist.json")); M = pd.read_csv(f"{R}/data/pm/markets.csv", dtype={'tok': str})
M['end'] = pd.to_datetime(M.end, utc=True, format='mixed', errors='coerce'); M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed', errors='coerce')
rows = []
for m in M.itertuples():
    h = H.get(m.tok)
    if not h or pd.isna(m.end) or pd.isna(m.closed) or pd.isna(m.yes_won): continue
    s = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True): x['p'] for x in h}).sort_index()
    s = s[(s.index < m.closed - pd.Timedelta(days=1)) & (s.index < m.end)]
    if len(s) < 10: continue
    for side, v, win in (('YES', s.values, m.yes_won == 1), ('NO', 1 - s.values, m.yes_won == 0)):
        tau = (m.end - s.index).total_seconds().values / 86400
        for i in range(len(v) - 1):
            if 0.02 < v[i] < 0.98 and tau[i] >= 1: rows.append((m.event, side, v[i], v[i + 1] - v[i], tau[i], win))
D = pd.DataFrame(rows, columns=['event', 'side', 'p', 'dp', 'tau', 'win'])
D = D[D.side == 'YES'].pipe(lambda x: pd.concat([x, D[(D.side == 'NO') & (D.p >= 0.9)]]))   # avoid double counting the middle
D['phi'] = norm.pdf(norm.ppf(D.p)); D['base'] = D.phi / D.tau ** 0.53
mid = D[(D.p > 0.2) & (D.p < 0.8)]; c = np.sqrt((mid.dp ** 2).mean() / (mid.base ** 2).mean())
out.append(f"Diffusion scale fitted on 20–80% states: daily sd = {c:.3f}·φ(N⁻¹p)/τ^0.53")
hi = D[D.p >= 0.90].copy(); hi['sd'] = c * hi.base
out.append(f"{len(hi):,} contract-days at ≥90¢ ({hi.event.nunique()} events); resolved NO (lost) eventually: {(~hi.win).mean():.1%} vs avg price {hi.p.mean():.3f}")
for drop in (0.10, 0.20, 0.40):
    act = (hi.dp <= -drop).mean(); pred = norm.cdf(-drop / hi.sd).mean()
    out.append(f"  one-day drop ≥{int(drop*100)}¢: actual {act:.4%} ({(hi.dp <= -drop).sum()} cases) vs normal-diffusion {pred:.4%} → ×{act/pred if pred>0 else np.inf:.0f}")
k = (hi.dp / hi.sd); out.append(f"  standardized changes at ≥90¢: kurtosis {k.kurt():.0f} (normal 0); share |z|>4: {(k.abs()>4).mean():.2%} (normal 0.006%)")
for lo_, hi_ in ((0.9, 0.95), (0.95, 0.98)):
    g = hi[(hi.p >= lo_) & (hi.p < hi_)]
    out.append(f"  price {lo_:.2f}–{hi_:.2f}: n {len(g)}, P(drop ≥20¢ next day) {(g.dp<=-0.2).mean():.3%}, eventual loss rate {(~g.win).mean():.1%} vs implied {1-g.p.mean():.1%}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s10_out.txt", "w").write(txt)
