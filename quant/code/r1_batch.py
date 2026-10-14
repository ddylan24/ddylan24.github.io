"""R1 candles via Kalshi batch endpoint GET /markets/candlesticks?market_tickers=a,b,...  (one call per ~40 markets)."""
import json, subprocess, sys, time, pandas as pd
R = sys.argv[1]; D = f"{R}/data/r1"
S = pd.read_csv(f"{D}/markets.csv", parse_dates=['close'])
def get(u):
    for i in range(7):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code == '200': return json.loads(body)
        time.sleep(min(2 ** i, 30))
C = {}
for ev, g in S.groupby('event'):
    ce = int(g.close.iloc[0].timestamp())
    for i in range(0, len(g), 40):
        tk = list(g.ticker.iloc[i:i + 40])
        d = get(f"https://api.elections.kalshi.com/trade-api/v2/markets/candlesticks?market_tickers={','.join(tk)}&start_ts={ce-30*3600}&end_ts={ce}&period_interval=60") or {}
        for t, m in zip(tk, d.get('markets', [])):
            C[m.get('market_ticker', t)] = m.get('candlesticks', [])
        time.sleep(1.0)
    print(ev, len(C), time.strftime('%H:%M:%S'), flush=True)
json.dump(C, open(f"{D}/candles.json", "w")); print("done", len(C))
