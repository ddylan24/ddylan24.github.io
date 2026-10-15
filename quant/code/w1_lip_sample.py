"""W1: sample order books of the richest ≥1-day Kalshi LIP markets every 3 min for 45 min; store raw books."""
import json, subprocess, sys, time, pandas as pd
R = sys.argv[1]; D = f"{R}/data/lip"
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '30', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
L = pd.read_csv(f"{D}/programs_active.csv")
L['start'] = pd.to_datetime(L.start_date, utc=True, format='mixed'); L['end'] = pd.to_datetime(L.end_date, utc=True, format='mixed')
L['days'] = (L.end - L.start).dt.total_seconds() / 86400; L['per_day'] = L.period_reward / 1e4 / L.days
now = pd.Timestamp.now(tz='UTC')
S = L[(L.start <= now) & (L.end > now + pd.Timedelta(hours=1)) & (L.days >= 1) & (L.incentive_type == 'liquidity')].sort_values('per_day', ascending=False).head(60)
S[['market_ticker', 'per_day', 'target_size_fp', 'discount_factor_bps', 'days']].to_csv(f"{D}/w1_markets.csv", index=False)
f = open(f"{D}/w1_books.jsonl", "w")
for k in range(16):
    t0 = time.time()
    for tk in S.market_ticker:
        ob = (get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{tk}/orderbook") or {}).get('orderbook_fp', {})
        f.write(json.dumps({'ts': time.time(), 't': tk, 'ob': ob}) + "\n"); f.flush(); time.sleep(0.1)
    print(k, time.strftime('%H:%M:%S'), flush=True)
    time.sleep(max(1, 180 - (time.time() - t0)))
print("done")
