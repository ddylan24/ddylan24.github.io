"""AA1: is the informed flow in Kalshi hourly Miami temperature (KXTEMPMIAH) 'people reading the thermometer'?
7 days of settled markets (resolve on the temperature at the hour, Synoptic Data); every public fill marked to settlement (maker P&L).
Live information proxy: the latest NWS ASOS 1-minute temperature at KMIA (IEM asos1min archive) before each fill.
Tests: maker P&L by minutes-to-close; and by whether the taker's side AGREES with the latest observation vs the strike."""
import io, json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; D = f"{R}/data/aa1"; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '60', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return b
        time.sleep(2 ** i)
API = "https://api.elections.kalshi.com/trade-api/v2"
since = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
import os
if os.path.exists(f"{D}/fills.csv.gz"):
    F = pd.read_csv(f"{D}/fills.csv.gz")
else:
    ms, cur = [], ''
    for _ in range(20):
        d = json.loads(get(f"{API}/markets?series_ticker=KXTEMPMIAH&status=settled&limit=1000&min_close_ts={int(since.timestamp())}" + (f"&cursor={cur}" if cur else "")) or '{}')
        ms += d.get('markets', []); cur = d.get('cursor') or ''
        if not cur or not d.get('markets'): break
    rows = []
    for m in ms:
        y = {'yes': 1.0, 'no': 0.0}.get(m.get('result'))
        if y is None or m.get('floor_strike') is None: continue
        tr = json.loads(get(f"{API}/markets/trades?ticker={m['ticker']}&limit=1000") or '{}').get('trades', [])
        for x in tr:
            rows.append(dict(t=m['ticker'], K=float(m['floor_strike']), close=m['close_time'], settle=m.get('expiration_value'), y=y,
                             ts=x['created_time'], side=x['taker_side'], p=float(x['yes_price_dollars']), n=float(x['count_fp'])))
        time.sleep(0.05)
    F = pd.DataFrame(rows)
F['ts'] = pd.to_datetime(F.ts, utc=True, format='mixed'); F['close'] = pd.to_datetime(F.close, utc=True, format='mixed')
F.to_csv(f"{D}/fills.csv.gz", index=False)
s0 = (since - pd.Timedelta(days=1)).strftime('%Y-%m-%dT%H:%MZ'); s1 = pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%MZ')
txt = get(f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos1min.py?station=MIA&vars=tmpf&sts={s0}&ets={s1}&sample=1min&what=download&tz=UTC")
W = pd.read_csv(io.StringIO(txt)); W['valid'] = pd.to_datetime(W['valid(UTC)'], utc=True); W = pd.to_numeric(W.set_index('valid').tmpf, errors='coerce').dropna().sort_index()
W.to_csv(f"{D}/kmia_1min.csv")
F['obs'] = W.reindex(F.ts.dt.floor('min'), method='ffill').values
F['mins_left'] = (F.close - F.ts).dt.total_seconds() / 60
F['maker'] = np.where(F.side == 'yes', F.p - F.y, F.y - F.p) * F.n
out.append(f"KXTEMPMIAH: {F.t.nunique()} settled markets, {len(F):,} fills, {F.n.sum():,.0f} contracts in 7 days; 1-min KMIA obs {len(W):,}")
out.append(f"  maker P&L to settlement: ${F.maker.sum():+,.0f} ({100*F.maker.sum()/F.n.sum():+.2f}¢/contract)")
F['bucket'] = pd.cut(F.mins_left, [-1, 5, 15, 30, 61, 1e4], labels=['last 5m', '5–15m', '15–30m', '30–60m', '>60m'])
for k, g in F.groupby('bucket', observed=True):
    out.append(f"  {k:<7} contracts {g.n.sum():9,.0f}  maker {100*g.maker.sum()/g.n.sum():+6.2f}¢/ct  (${g.maker.sum():+,.0f})")
# informed-by-thermometer test: does the taker's side agree with obs vs strike?
F['d'] = F.obs - F.K
F['agree'] = np.where(F.side == 'yes', F.d > 0, F.d < 0)
for late in (True, False):
    g = F[(F.mins_left <= 15) == late].dropna(subset=['obs'])
    for a in (True, False):
        h = g[g.agree == a]
        out.append(f"  {'last 15m' if late else 'earlier '} taker side {'AGREES' if a else 'disagrees'} with latest obs: contracts {h.n.sum():9,.0f}, maker {100*h.maker.sum()/max(h.n.sum(),1):+6.2f}¢/ct")
# obs accuracy: how often does the latest obs at T-10min already decide the market?
g = F[(F.mins_left > 8) & (F.mins_left <= 12)].drop_duplicates('t').dropna(subset=['obs'])
out.append(f"  latest 1-min obs 10 min before close vs strike predicts outcome: {((g.d > 0) == (g.y == 1)).mean():.0%} of markets (n {len(g)})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/aa1_out.txt", "w").write(txt)
