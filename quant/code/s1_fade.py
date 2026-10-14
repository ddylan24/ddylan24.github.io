"""S1: fade large daily moves on Polymarket (R6 found excess movement, daily-change AC −0.08).
Signal: |Δp| over one day > threshold. Trade against it at p_t paying a 1¢ half-spread (and again on exit for k-day holds).
Horizons: 1 day, 5 days, to resolution. Event-clustered t-stats; split by period."""
import json, sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []
H = json.load(open(f"{R}/data/pm/hist.json")); M = pd.read_csv(f"{R}/data/pm/markets.csv", dtype={'tok': str})
M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed', errors='coerce')
rows = []
for m in M.itertuples():
    h = H.get(m.tok)
    if not h or pd.isna(m.yes_won) or pd.isna(m.closed): continue
    s = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True): x['p'] for x in h}).sort_index()
    s = s[s.index < m.closed - pd.Timedelta(days=1)]
    if len(s) < 10: continue
    p = s.values; d = np.diff(p)
    for i in range(3, len(d)):               # skip opening days
        if abs(d[i]) < 0.05 or not (0.05 < p[i + 1] < 0.95): continue
        sg = -np.sign(d[i]); pt = p[i + 1]
        r1 = sg * (p[min(i + 2, len(p) - 1)] - pt) if i + 2 < len(p) else np.nan
        r5 = sg * (p[min(i + 6, len(p) - 1)] - pt) if i + 6 < len(p) else np.nan
        rT = sg * (m.yes_won - pt)
        rows.append(dict(event=m.event, t=s.index[i + 1], move=abs(d[i]), up=d[i] > 0, p=pt, r1=r1, r5=r5, rT=rT))
D = pd.DataFrame(rows)
def ct(x, ev):
    x = np.asarray(x, float); ok = ~np.isnan(x); x, ev = x[ok], np.asarray(ev)[ok]; g = pd.Series(x - x.mean()).groupby(ev).sum()
    return x.mean(), x.mean() / (np.sqrt((g ** 2).sum()) / len(x)), len(x)
out.append(f"{len(D)} large daily moves (|Δp| ≥ 5¢, price 5–95¢) in {D.event.nunique()} events; P&L in ¢ per $1 contract")
for th in (0.05, 0.10, 0.20):
    g = D[D.move >= th]
    for nm, col, cost in (('1 day', 'r1', 0.02), ('5 days', 'r5', 0.02), ('to resolution', 'rT', 0.01)):
        mu, t, n = ct(g[col] - cost, g.event)
        gross, tg, _ = ct(g[col], g.event)
        out.append(f"  |Δp|≥{th:.2f} fade, hold {nm:<13}: n {n:5d}  gross {100*gross:+.2f}¢ (t {tg:+.1f})  net {100*mu:+.2f}¢ (t {t:+.1f})")
g = D[D.move >= 0.10]
for nm, gg in (('up-moves', g[g.up]), ('down-moves', g[~g.up])):
    mu, t, n = ct(gg.rT - 0.01, gg.event); out.append(f"  ≥10¢ {nm:<10} fade to resolution: n {n}, net {100*mu:+.2f}¢ (t {t:+.1f})")
for per, gg in (('before 2025-07', g[g.t < '2025-07-01']), ('after 2025-07', g[g.t >= '2025-07-01'])):
    mu, t, n = ct(gg.r5 - 0.02, gg.event); out.append(f"  ≥10¢ {per}: 5-day fade net {100*mu:+.2f}¢ (t {t:+.1f}, n {n})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s1_out.txt", "w").write(txt)
