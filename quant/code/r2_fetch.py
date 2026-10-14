"""R2 data: resolved binary Polymarket markets (2026) and their taker trades with wallet ids."""
import json, sys, time, urllib.request, pandas as pd
R = sys.argv[1]; D = f"{R}/data/r2"
import subprocess
def get(u):
    for i in range(4):
        try:
            r = subprocess.run(['curl', '-s', '--max-time', '30', '-A', 'Mozilla/5.0', u], capture_output=True, timeout=40)
            return json.loads(r.stdout)
        except Exception: time.sleep(2 ** i)
ms = []
for off in range(0, 2000, 100):
    d = get(f"https://gamma-api.polymarket.com/markets?closed=true&limit=100&offset={off}&order=volumeNum&ascending=false&start_date_min=2026-01-01T00:00:00Z")
    if not d: break
    for m in d:
        try: pr = [float(x) for x in json.loads(m['outcomePrices'])]; tok = json.loads(m['clobTokenIds'])
        except Exception: continue
        if sorted(pr) != [0.0, 1.0] or len(tok) != 2 or not m.get('closedTime'): continue
        ms.append(dict(cid=m['conditionId'], q=m['question'], yes=tok[0], y=int(pr[0] == 1.0), closed=m['closedTime'], vol=m.get('volumeNum')))
    if len(d) < 100: break
M = pd.DataFrame(ms); M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed'); M = M[M.closed >= '2026-01-01'].sort_values('vol', ascending=False).head(400)
M.to_csv(f"{D}/markets.csv", index=False); print(len(M), "markets", M.closed.min(), M.closed.max(), flush=True)
out = []
for i, m in enumerate(M.itertuples()):
    for off in range(0, 4000, 500):
        d = get(f"https://data-api.polymarket.com/trades?market={m.cid}&limit=500&offset={off}")
        if not isinstance(d, list) or not d:
            if off and not isinstance(d, list): print("stop", m.cid[:10], off, str(d)[:80], flush=True)
            break
        for x in d: out.append((m.cid, x['proxyWallet'], x['side'], x['asset'] == m.yes, float(x['price']), float(x['size']), x['timestamp']))
        if len(d) < 500: break
    if i % 25 == 0: print(i, len(out), time.strftime('%H:%M:%S'), flush=True)
pd.DataFrame(out, columns=['cid', 'wallet', 'side', 'is_yes', 'price', 'size', 'ts']).to_csv(f"{D}/trades.csv.gz", index=False)
print("trades", len(out))
