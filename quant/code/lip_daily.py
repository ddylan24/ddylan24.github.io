"""Kalshi LIP: reconstruct total daily reward pools from ALL programs (active + upcoming + closed + paid_out), pro-rating each
program's period_reward (centi-cents = 1/10,000 $, per docs.kalshi.com openapi) over the UTC days it overlaps.
A one-time snapshot of 'active' programs misses rolling short programs (hourly/15-min) created through the day — don't use it."""
import json, subprocess, sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []
def get(u):
    r = subprocess.run(['curl', '-s', '--max-time', '120', '-A', 'Mozilla/5.0', u], capture_output=True, text=True); return json.loads(r.stdout)
rows = []
for st in ['active', 'upcoming', 'closed', 'paid_out']:
    cur = ''
    for _ in range(100):
        d = get(f"https://api.elections.kalshi.com/trade-api/v2/incentive_programs?limit=10000&status={st}&type=all" + (f"&cursor={cur}" if cur else ""))
        rows += d.get('incentive_programs', []); cur = d.get('next_cursor') or ''
        if not cur or not d.get('incentive_programs'): break
A = pd.DataFrame(rows).drop_duplicates('id')
A['s'] = pd.to_datetime(A.start_date, utc=True, format='mixed'); A['e'] = pd.to_datetime(A.end_date, utc=True, format='mixed')
A['usd'] = A.period_reward / 1e4; A['dur'] = (A.e - A.s).dt.total_seconds() / 86400; A['series'] = A.market_ticker.str.split('-').str[0]
out.append(f"{len(A):,} programs since {A.s.min():%Y-%m-%d}; total pools ${A.usd.sum():,.0f}; types {A.incentive_type.value_counts().to_dict()}")
def day_pool(d0):
    d1 = d0 + pd.Timedelta(days=1); ov = ((np.minimum(A.e, d1) - np.maximum(A.s, d0)).dt.total_seconds().clip(lower=0)) / (A.e - A.s).dt.total_seconds()
    return A.usd * ov
today = pd.Timestamp.now(tz='UTC').normalize()
days = pd.date_range(today - pd.Timedelta(days=30), today - pd.Timedelta(days=1), freq='D')
D = pd.DataFrame({'day': days.date, 'usd': [day_pool(d).sum() for d in days]})
out.append(f"Daily pools, last 30 complete days: mean ${D.usd.mean():,.0f}, last 7 ${D.usd.tail(7).mean():,.0f}, min ${D.usd.min():,.0f}, max ${D.usd.max():,.0f}")
w = sum(day_pool(d) for d in days[-7:]) / 7
b = pd.cut(A.dur, [0, 1 / 24 + 1e-9, 1, 7, 1e9], labels=['≤1h', '1h–1d', '1–7d', '>7d'])
out.append("  by program length ($/day, last 7d): " + ", ".join(f"{k} ${v:,.0f}" for k, v in w.groupby(b, observed=True).sum().items()))
out.append("  top series ($/day, last 7d): " + ", ".join(f"{k} ${v:,.0f}" for k, v in w.groupby(A.series).sum().sort_values(ascending=False).head(10).items()))
m = A.groupby(A.e.dt.strftime('%Y-%m')).usd.sum()
out.append("  pools by end month: " + ", ".join(f"{k} ${v/1e6:.2f}M" for k, v in m.items() if k >= '2025-10'))
out.append("NOTE: these are scheduled pool caps; actual payouts are lower by the share of snapshots excluded for lack of two-sided Target depth.")
D.to_csv(f"{R}/data/lip/daily_pools.csv", index=False)
txt = "\n".join(out); print(txt); open(f"{R}/notes/lip_daily_out.txt", "w").write(txt)
