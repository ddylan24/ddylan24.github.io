"""W1: dynamics of the richest ≥1-day Kalshi LIP books over ~45 min (snapshots every 3 min).
Per market: share of snapshots that would be EXCLUDED (a side below Target), stability of best bids, depth churn,
and the newcomer share (Target-size order at best bid both sides) over time."""
import json, sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/ddylan24.github.io/quant/code'); from pm_toolkit import lip_side_share
R = sys.argv[1]; D = f"{R}/data/lip"; out = []
M = pd.read_csv(f"{D}/w1_markets.csv").set_index('market_ticker')
rows = []
for line in open(f"{D}/w1_books.jsonl"):
    x = json.loads(line); m = M.loc[x['t']]; T = float(m.target_size_fp); df = m.discount_factor_bps / 1e4
    yb = [(round(float(p) * 100), float(s)) for p, s in x['ob'].get('yes_dollars', [])]
    nb = [(round(float(p) * 100), float(s)) for p, s in x['ob'].get('no_dollars', [])]
    qy, _ = lip_side_share(yb, T, df) if yb else (False, 0); qn, _ = lip_side_share(nb, T, df) if nb else (False, 0)
    by = max(p for p, _ in yb) if yb else np.nan; bn = max(p for p, _ in nb) if nb else np.nan
    sh = np.nan
    if yb and nb:
        a, sy = lip_side_share(yb, T, df, by, T); b, sn = lip_side_share(nb, T, df, bn, T); sh = (sy + sn) / 2 if (a and b) else 0
    rows.append(dict(t=x['t'], ts=x['ts'], two_sided=qy and qn, best_yes=by, best_no=bn, spread=100 - by - bn, depth=sum(s for _, s in yb) + sum(s for _, s in nb), new_share=sh, per_day=m.per_day))
X = pd.DataFrame(rows); X['k'] = X.groupby('t').cumcount()
g = X.groupby('t').agg(n=('k', 'size'), excl=('two_sided', lambda s: 1 - s.mean()), by_changes=('best_yes', lambda s: (s.diff().fillna(0) != 0).sum()),
                       sp=('spread', 'median'), dep_cv=('depth', lambda s: s.std() / s.mean() if s.mean() else np.nan), sh_med=('new_share', 'median'), sh_sd=('new_share', 'std'), per_day=('per_day', 'first'))
out.append(f"{g.shape[0]} richest ≥1-day LIP markets, {int(g.n.median())} snapshots each (3-min spacing, ~{(X.ts.max()-X.ts.min())/60:.0f} min)")
out.append(f"  share of snapshots that would be excluded (a side below Target): median {g.excl.median():.0%}, mean {g.excl.mean():.0%}; markets never two-sided: {(g.excl==1).sum()}, always two-sided: {(g.excl==0).sum()}")
out.append(f"  best YES bid changed in {g.by_changes.median():.0f} of {int(g.n.median())-1} intervals (median); median spread {g.sp.median():.0f}¢; depth coefficient of variation median {g.dep_cv.median():.2f}")
out.append(f"  newcomer (Target size at best bid, both sides) share: median {g.sh_med.median():.1%}, within-market sd over time {g.sh_sd.median():.1%}")
ex = g.excl.mean(); out.append(f"  ⇒ expected payout haircut from excluded snapshots ≈ {ex:.0%} of the headline pool on average (pools-weighted {np.average(g.excl, weights=g.per_day):.0%})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/w1_out.txt", "w").write(txt)
