"""Z1: LIP net economics by series over 7 days = reward pools paid on a series' markets vs makers' fill P&L marked to SETTLEMENT.
Pools: all LIP programs (lip history CSV) on markets that settled in the window. Fills: public trades per settled market (Y1 method).
Reports pool, maker fill P&L, net, and per-contract figures. Net is what ALL makers together earned; a newcomer gets a share of both."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
P = pd.read_csv(f"{R}/../lip/programs_all_liquidity.csv", low_memory=False)
pool_by_mkt = P.groupby('market_ticker').usd.sum()
since = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
SER = ['KXTEMPMIAH', 'KXRT', 'KXTRUMPAPPROVE', 'KXEURUSD15M', 'KXUSDJPY15M', 'KXAUDUSD15M', 'KXAAAGASDFL', 'KXCRYPTOLEAD15M']
rows = []
for ser in SER:
    ms, cur = [], ''
    for _ in range(20):
        d = get(f"{API}/markets?series_ticker={ser}&status=settled&limit=1000&min_close_ts={int(since.timestamp())}" + (f"&cursor={cur}" if cur else "")) or {}
        ms += d.get('markets', []); cur = d.get('cursor') or ''
        if not cur or not d.get('markets'): break
    ms = [m for m in ms if m['ticker'] in pool_by_mkt.index]                  # only markets that carried LIP rewards
    if len(ms) > 400: ms = ms[::max(1, len(ms) // 400)]                      # sample for API politeness; scale pools identically
    pool = sum(pool_by_mkt[m['ticker']] for m in ms); mk = 0.0; vol = 0.0
    for m in ms:
        y = {'yes': 1.0, 'no': 0.0}.get(m.get('result'))
        if y is None: continue
        cur = ''
        for _ in range(10):
            d = get(f"{API}/markets/trades?ticker={m['ticker']}&limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
            for x in d.get('trades', []):
                p = float(x['yes_price_dollars']); n = float(x['count_fp'])
                mk += ((p - y) if x['taker_side'] == 'yes' else (y - p)) * n; vol += n
            cur = d.get('cursor') or ''
            if not cur or not d.get('trades'): break
        time.sleep(0.05)
    rows.append(dict(series=ser, markets=len(ms), pool=pool, maker_fill_pnl=mk, contracts=vol))
    print(ser, len(ms), round(pool), round(mk), flush=True)
X = pd.DataFrame(rows); X['net'] = X.pool + X.maker_fill_pnl
X['fill_c_per_ct'] = 100 * X.maker_fill_pnl / X.contracts.clip(lower=1); X['pool_c_per_ct'] = 100 * X.pool / X.contracts.clip(lower=1)
X.to_csv(f"{R}/data/lip/z1_net.csv", index=False)
out.append("7-day LIP net economics (markets that carried LIP and settled in the window; fills marked to settlement)")
for r in X.sort_values('net', ascending=False).itertuples():
    out.append(f"  {r.series:<16} mkts {r.markets:4d}  pool ${r.pool:9,.0f}  maker fill P&L ${r.maker_fill_pnl:+10,.0f}  NET ${r.net:+10,.0f}  | per filled contract: fills {r.fill_c_per_ct:+.2f}¢, reward {r.pool_c_per_ct:.2f}¢")
out.append(f"  TOTAL pool ${X.pool.sum():,.0f}, fills ${X.maker_fill_pnl.sum():+,.0f}, net ${X.net.sum():+,.0f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/z1_out.txt", "w").write(txt)
