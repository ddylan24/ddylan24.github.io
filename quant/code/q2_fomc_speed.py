"""Q2: speed of information. Polymarket 'Fed decision in September (2026)' vs Treasuries/equities, minute by minute.
FOMC statement 2026-09-16 18:00 UTC (2:00pm ET); outcome +25bp (FRED DFEDTARU 3.75 -> 4.00)."""
import json, sys, urllib.request, time, numpy as np, pandas as pd
R = sys.argv[1]; D = f"{R}/data/q2"; out = []
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r: return json.load(r)
        except Exception: time.sleep(2 ** i)
T_ANN = pd.Timestamp('2026-09-16 18:00', tz='UTC')
# ---- tick trades (data-api, newest first, paged by offset)
ev = get("https://gamma-api.polymarket.com/events?slug=fed-decision-in-september-762")[0]
trades = {}
for m in ev['markets']:
    k = m['groupItemTitle']; yes = json.loads(m['clobTokenIds'])[0]; rows = []
    for off in range(0, 10000, 500):
        d = get(f"https://data-api.polymarket.com/trades?market={m['conditionId']}&limit=500&offset={off}")
        if not d: break
        rows += d
        if d[-1]['timestamp'] < T_ANN.timestamp() - 3 * 3600 or len(d) < 500: break
    t = pd.DataFrame(rows)
    if len(t) == 0: continue
    t['ts'] = pd.to_datetime(t.timestamp, unit='s', utc=True)
    # express every trade as a YES price (a NO trade at q is YES at 1-q)
    t['p_yes'] = np.where(t.asset == yes, t.price, 1 - t.price)
    t['usd'] = t.size * t.price
    trades[k] = t.sort_values('ts')
    out.append(f"{k:<18} trades fetched {len(t):5d}  from {t.ts.min():%H:%M:%S} to {t.ts.max():%H:%M:%S} UTC")
pd.concat([v.assign(bucket=k) for k, v in trades.items()])[['bucket','ts','side','outcome','price','p_yes','size','usd','proxyWallet']].to_csv(f"{D}/trades.csv", index=False)
H = trades['25 bps increase']; N = trades['No change']
def last_before(t, ts): s = t[t.ts < ts]; return s.p_yes.iloc[-1] if len(s) else np.nan
out.append("\n25 bps increase (YES price) around 18:00:00 UTC statement:")
for sec in [-3600, -600, -60, -10, 0, 5, 10, 20, 30, 60, 120, 300, 900]:
    ts = T_ANN + pd.Timedelta(seconds=sec)
    out.append(f"  t{sec:+5d}s  hike {last_before(H, ts):.4f}   no-change {last_before(N, ts):.4f}")
post = H[H.ts >= T_ANN]
first = post.iloc[0]
p_pre = last_before(H, T_ANN)
hit = post[post.p_yes >= p_pre + 0.9 * (0.999 - p_pre)]
out.append(f"  first trade after statement: {first.ts:%H:%M:%S} at {first.p_yes:.3f} ({first.side} {first.outcome}, ${first.usd:,.0f})")
out.append(f"  90% of move (pre {p_pre:.3f} → 0.999) reached at {hit.ts.iloc[0]:%H:%M:%S} (+{(hit.ts.iloc[0]-T_ANN).total_seconds():.0f}s)" if len(hit) else "  never reached 90%")
# who traded at stale prices just after? volume traded below 0.99 after the statement
stale = post[(post.p_yes < 0.99) & (post.ts < T_ANN + pd.Timedelta(minutes=5))]
out.append(f"  trades after 18:00 at YES < 0.99 within 5 min: {len(stale)}, ${stale.usd.sum():,.0f}; prices {stale.p_yes.min():.3f}–{stale.p_yes.max():.3f}" if len(stale) else "  no trades below 0.99 after the statement")
# pre-announcement flow
for a, b in [(-3600, -600), (-600, -60), (-60, 0)]:
    w = H[(H.ts >= T_ANN + pd.Timedelta(seconds=a)) & (H.ts < T_ANN + pd.Timedelta(seconds=b))]
    out.append(f"  window {a:+5d}s..{b:+4d}s: {len(w)} trades, ${w.usd.sum():,.0f}, YES vwap {np.average(w.p_yes, weights=w['size']) if len(w) else np.nan:.3f}")
# ---- path over prior weeks (hourly) and since May (daily)
hh = pd.DataFrame(json.load(open(f"{D}/25_bps_increase_hour.json"))); hh['ts'] = pd.to_datetime(hh.t, unit='s', utc=True)
dd = pd.DataFrame(json.load(open(f"{D}/25_bps_increase_day.json"))); dd['ts'] = pd.to_datetime(dd.t, unit='s', utc=True)
out.append("\nHike probability path (daily): " + ", ".join(f"{r.ts:%m-%d} {r.p:.2f}" for r in dd.iloc[::14].itertuples()) + f", {dd.ts.iloc[-1]:%m-%d} {dd.p.iloc[-1]:.3f}")
big = hh.assign(dp=hh.p.diff()).dropna().sort_values('dp', key=abs, ascending=False).head(5)
out.append("Largest hourly jumps in the last 4 weeks: " + "; ".join(f"{r.ts:%m-%d %H:00} {r.dp:+.3f}→{r.p:.3f}" for r in big.itertuples()))
# ---- cross-asset: Yahoo 1-minute
def y(t):
    d = pd.read_csv(f"{D}/{t}_1m.csv", header=[0, 1], index_col=0)
    d.index = pd.to_datetime(d.index, utc=True); return d['Close'].iloc[:, 0]
out.append("\nCross-asset minute bars (Yahoo; bar labelled by start minute):")
for t in ['SPY', 'TLT', 'SHY', 'IRX', 'TNX']:
    s = y(t); pre = s[s.index < T_ANN].iloc[-1]
    rows = []
    for mnt in [1, 2, 5, 15, 60]:
        v = s[s.index < T_ANN + pd.Timedelta(minutes=mnt)].iloc[-1]
        rows.append(f"+{mnt}m {('%+.1fbp' % (100*(v-pre)) ) if t in ('IRX','TNX') else ('%+.2f%%' % (100*(v/pre-1)))}")
    out.append(f"  {t:<4} pre {pre:.3f}  " + "  ".join(rows))
# realized sd of 1-min returns before vs after
s = y('SHY'); r = np.log(s).diff().dropna()
out.append(f"  SHY 1-min return sd: 10:00-13:55 ET {r[(r.index<T_ANN-pd.Timedelta(minutes=5))].std()*1e4:.2f}bp, 14:00-14:30 ET {r[(r.index>=T_ANN)&(r.index<T_ANN+pd.Timedelta(minutes=30))].std()*1e4:.2f}bp")
# implied surprise: (1 - p_pre) * 25bp hike surprise
out.append(f"\nImplied policy surprise from Polymarket: (1 − {p_pre:.3f}) × 25bp ≈ {(1-p_pre)*25:.1f}bp of unexpected tightening (plus guidance effects).")
txt = "\n".join(out); print(txt); open(f"{R}/notes/q2_out.txt", "w").write(txt)
# ---- tick detail and picked-off losses
out2 = ["\nTick detail, all buckets, 17:59:50–18:00:30 UTC (YES-equivalent price):"]
allt = pd.read_csv(f"{D}/trades.csv", parse_dates=['ts'])
w = allt[(allt.ts >= T_ANN - pd.Timedelta(seconds=10)) & (allt.ts <= T_ANN + pd.Timedelta(seconds=30))].sort_values('ts')
for r in w.head(25).itertuples():
    out2.append(f"  {r.ts:%H:%M:%S} {r.bucket:<16} {r.side:<4} {r.outcome:<3} @ {r.price:.3f} (YES {r.p_yes:.3f}) ${r.usd:,.0f}")
# makers who were filled after the statement at stale prices: loss vs final value (hike=1, others=0)
fin = {'25 bps increase': 1.0}
po = allt[(allt.ts >= T_ANN) & (allt.ts < T_ANN + pd.Timedelta(minutes=5))].copy()
po['final'] = po.bucket.map(fin).fillna(0.0)
po['yes_shares'] = np.where(po.outcome == 'Yes', 1, -1) * np.where(po.side == 'BUY', 1, -1) * po['size']   # taker's YES exposure
po['taker_pnl'] = po.yes_shares * (po.final - po.p_yes)
out2.append(f"\nTakers in the first 5 min after the statement: {len(po)} trades, ${po.usd.sum():,.0f} notional, taker P&L vs resolution ${po.taker_pnl.sum():,.0f} (= makers' loss); "
            f"first 60s: ${po[po.ts < T_ANN + pd.Timedelta(seconds=60)].taker_pnl.sum():,.0f}")
out2.append("  by bucket: " + ", ".join(f"{k} ${v:,.0f}" for k, v in po.groupby('bucket').taker_pnl.sum().items()))
print("\n".join(out2)); open(f"{R}/notes/q2_out.txt", "a").write("\n" + "\n".join(out2))
