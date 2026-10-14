"""U2: how fast do Kalshi and Polymarket BTC threshold prices respond to spot? (minute data, last ~6 hours)
Kalshi KXBTCD next-day 5pm-ET contracts (1-min candles, mid of bid/ask); Polymarket 'Bitcoin above X on <next day>' noon-ET contracts
(taker trades → YES-equivalent trade price per minute); BTC = Deribit BTC-PERPETUAL 1-min closes re-stamped to bar END.
Regress Δp_t on spot returns r_{t−k}, k = 0..5 (contemporaneous + lags), pooled over the near-the-money strikes of each venue.
Share of the total response arriving at lag 0 = speed."""
import json, subprocess, sys, time, numpy as np, pandas as pd, statsmodels.api as sm
R = sys.argv[1]; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(2 ** i)
now = int(time.time()); t0 = now - 6 * 3600
d = get(f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&start_timestamp={t0*1000}&end_timestamp={now*1000}&resolution=1")['result']
S = pd.Series(d['close'], index=pd.to_datetime(d['ticks'], unit='ms', utc=True) + pd.Timedelta(minutes=1)); spot = S.iloc[-1]
r = np.log(S).diff()
tom = pd.Timestamp.now(tz='UTC') + pd.Timedelta(days=1)
# Kalshi
ktk = f"KXBTCD-{tom:%y%b%d}17".upper()
ev = get(f"https://api.elections.kalshi.com/trade-api/v2/events/{ktk}?with_nested_markets=true") or {}
ms = (ev.get('event') or {}).get('markets') or ev.get('markets') or []
ks = sorted([m for m in ms if m.get('floor_strike') and abs(m['floor_strike'] / spot - 1) < 0.012], key=lambda m: abs(m['floor_strike'] - spot))[:8]
tk = ','.join(m['ticker'] for m in ks)
c = get(f"https://api.elections.kalshi.com/trade-api/v2/markets/candlesticks?market_tickers={tk}&start_ts={t0}&end_ts={now}&period_interval=1") or {}
K = {}
for m in c.get('markets', []):
    rows = [(x['end_period_ts'], x['yes_bid'].get('close_dollars'), x['yes_ask'].get('close_dollars')) for x in m.get('candlesticks', [])]
    s = pd.DataFrame(rows, columns=['t', 'b', 'a']).dropna()
    if len(s) < 30: continue
    s.index = pd.to_datetime(s.t, unit='s', utc=True); K[m['market_ticker']] = ((s.b.astype(float) + s.a.astype(float)) / 2)
# Polymarket
slug = f"bitcoin-above-on-{tom:%B}-{tom.day}-{tom:%Y}".lower()
pe = get(f"https://gamma-api.polymarket.com/events?slug={slug}")[0]
P = {}; pvol = {}
for m in pe['markets']:
    Kp = float(m['groupItemTitle'].replace(',', ''))
    if abs(Kp / spot - 1) > 0.02: continue
    yes = json.loads(m['clobTokenIds'])[0]; T = get(f"https://data-api.polymarket.com/trades?market={m['conditionId']}&limit=500") or []
    t = pd.DataFrame(T)
    if len(t) == 0: continue
    t['ts'] = pd.to_datetime(t.timestamp, unit='s', utc=True); t = t[t.ts >= pd.to_datetime(t0, unit='s', utc=True)]
    pvol[Kp] = (len(t), (t['size'] * t.price).sum())
    if len(t) < 30: continue
    t['p'] = np.where(t.asset == yes, t.price, 1 - t.price)
    P[Kp] = t.set_index('ts').p.resample('1min').last()
out.append(f"Window: last 6h to {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC; spot {spot:,.0f}; 1-min spot sd {r.std()*1e4:.1f}bp")
out.append(f"Kalshi {tom:%b %d} 5pm contracts with 1-min quotes: {len(K)}; Polymarket {tom:%b %d} noon strikes within 2%: trades/$ in window " + ", ".join(f"{k:,.0f}: {n} / ${v:,.0f}" for k, (n, v) in pvol.items()))
def resp(series_dict, label, ffill):
    rows = []
    for k, s in series_dict.items():
        s = s.reindex(r.index)
        if ffill: s = s.ffill()
        dp = s.diff() * 100
        X = pd.concat([r.shift(j).rename(f'l{j}') for j in range(6)], axis=1) * 1e4
        J = pd.concat([dp.rename('dp'), X], axis=1).dropna()
        if len(J) > 30: rows.append(J)
    if not rows: out.append(f"  {label}: insufficient data"); return
    J = pd.concat(rows); f = sm.OLS(J.dp, sm.add_constant(J.drop(columns='dp'))).fit(cov_type='HAC', cov_kwds={'maxlags': 5})
    b = f.params.drop('const'); tot = b.sum()
    out.append(f"  {label}: n {len(J)}; Δp (¢) per 1bp spot move at lags 0..5: " + ", ".join(f"{v:+.3f}" for v in b.values) + f"; total {tot:+.3f}; share at lag 0 {b.iloc[0]/tot:.0%}, by lag 1 {(b.iloc[0]+b.iloc[1])/tot:.0%}; R² {f.rsquared:.2f}")
resp(K, "Kalshi (quote mids)", ffill=False)
resp(P, "Polymarket (trade prices)", ffill=True)
txt = "\n".join(out); print(txt); open(f"{R}/notes/u2_out.txt", "w").write(txt)
