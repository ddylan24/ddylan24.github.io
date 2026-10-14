"""S3: when to exit a binary early, and the 'high-probability bond' strategy (buy ≥95¢ favorites, hold to resolution).
Exit rule with belief q = market p, half-spread s, rate r, time left τ: sell iff p − s > q·e^(−rτ)  ⇔  s < p(1 − e^(−rτ)) (when q = p).
Empirical: first day a Polymarket contract (either side) trades ≥ threshold, buy at price + half-spread, hold to resolution."""
import json, sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []
r = 0.0425
out.append("Exit vs hold when you agree with the market (q = p), half-spread 1¢:")
for p in (0.80, 0.95, 0.99):
    out.append("  p=%.2f: " % p + ", ".join(f"τ={t}: hold PV {p*np.exp(-r*t):.4f} vs sell {p-0.01:.4f} → {'SELL' if p-0.01 > p*np.exp(-r*t) else 'hold'}" for t in (0.1, 0.25, 1, 2)))
out.append(f"  break-even horizon τ* = −ln(1 − s/p)/r: p=0.95 → {-np.log(1-0.01/0.95)/r*365:.0f} days; p=0.5 → {-np.log(1-0.01/0.5)/r*365:.0f} days")
H = json.load(open(f"{R}/data/pm/hist.json")); M = pd.read_csv(f"{R}/data/pm/markets.csv", dtype={'tok': str})
M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed', errors='coerce'); M['end'] = pd.to_datetime(M.end, utc=True, format='mixed', errors='coerce')
rows = []
for th in (0.90, 0.95, 0.97):
    for m in M.itertuples():
        h = H.get(m.tok)
        if not h or pd.isna(m.yes_won) or pd.isna(m.closed): continue
        s = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True): x['p'] for x in h}).sort_index()
        s = s[s.index < m.closed - pd.Timedelta(days=1)]          # avoid the post-outcome tail (P2 look-ahead lesson)
        for side, ser, win in (('YES', s, m.yes_won == 1), ('NO', 1 - s, m.yes_won == 0)):
            hit = ser[ser >= th]
            if not len(hit): continue
            t0 = hit.index[0]; px = min(hit.iloc[0] + 0.005, 0.999)
            days = max((m.closed - t0).total_seconds() / 86400, 1)
            ret = (1.0 if win else 0.0) / px - 1
            rows.append(dict(th=th, event=m.event, side=side, px=px, days=days, ret=ret, win=win, yr=t0.year))
D = pd.DataFrame(rows)
for th, g in D.groupby('th'):
    tb = (np.exp(r * g.days / 365) - 1)
    ex = g.ret - tb
    ev = g.assign(ex=ex).groupby('event').ex.mean()
    out.append(f"\nBuy first touch ≥{th:.2f} (+0.5¢), hold: n={len(g)}, win rate {g.win.mean():.3f} vs avg price {g.px.mean():.3f}, median hold {g.days.median():.0f}d")
    out.append(f"  mean return {100*g.ret.mean():+.2f}% vs T-bill over same holds {100*tb.mean():.2f}% → excess {100*ex.mean():+.2f}% (event-level t {ev.mean()/ev.std()*np.sqrt(len(ev)):.1f}, {len(ev)} events)")
    out.append(f"  capital-weighted annualized: {100*(g.ret.sum()/ (g.days.sum()/365)):.1f}%/yr vs T-bill {100*r:.2f}%; losses: {(~g.win).sum()} ({100*(~g.win).mean():.1f}%), each ≈ −100%")
    for yr, gy in g.groupby('yr'):
        if len(gy) > 30: out.append(f"    {yr}: n {len(gy)}, win {gy.win.mean():.3f} vs px {gy.px.mean():.3f}, excess {100*(gy.ret - (np.exp(r*gy.days/365)-1)).mean():+.2f}%")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s3_out.txt", "w").write(txt)
