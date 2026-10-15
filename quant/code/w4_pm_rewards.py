"""W4: census of Polymarket liquidity-reward configs (CLOB /rewards/markets/current, cursor paging) vs Kalshi LIP census."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2 ** i)
rows, cur = [], ""
for _ in range(400):
    d = get("https://clob.polymarket.com/rewards/markets/current" + (f"?next_cursor={cur}" if cur else "")) or {}
    rows += d.get('data', []); cur = d.get('next_cursor') or ""
    if not cur or cur == 'LTE=' or not d.get('data'): break
X = pd.DataFrame([dict(cid=r['condition_id'], rate=r.get('total_daily_rate') or 0, max_spread=r.get('rewards_max_spread'), min_size=r.get('rewards_min_size')) for r in rows])
X.to_csv(f"{R}/data/lip/pm_rewards.csv", index=False)
out.append(f"Polymarket markets with an active liquidity-reward config: {len(X):,}; total ≈ ${X.rate.sum():,.0f}/day")
out.append(f"  daily rate per market: median ${X.rate.median():.0f}, mean ${X.rate.mean():.1f}, 90th pct ${X.rate.quantile(.9):.0f}, max ${X.rate.max():,.0f}")
out.append(f"  rate distribution: " + ", ".join(f"${k}: {v}" for k, v in X.rate.round().value_counts().sort_index(ascending=False).head(8).items()))
out.append(f"  max qualifying spread (¢): {X.max_spread.value_counts().head(5).to_dict()}; min size: {X.min_size.value_counts().head(5).to_dict()}")
K = pd.read_csv(f"{R}/data/lip/programs_active.csv"); K['days'] = (pd.to_datetime(K.end_date, utc=True, format='mixed') - pd.to_datetime(K.start_date, utc=True, format='mixed')).dt.total_seconds() / 86400
K['per_day'] = K.period_reward / 1e4 / K.days.clip(lower=1 / 24); full = K[K.days >= 1]
out.append(f"\nKalshi LIP for comparison: {len(K):,} programs; programs lasting ≥1 day: {len(full):,}, ${full.per_day.sum():,.0f}/day (median ${full.per_day.median():.0f}/day)")
txt = "\n".join(out); print(txt); open(f"{R}/notes/w4_out.txt", "w").write(txt)
