"""S7: Polymarket October-2026 FOMC probabilities vs CBOT 30-day fed funds futures (ZQ, via Yahoo) and FRED EFFR.
ZQ settles to 100 − average daily EFFR over the contract month. Meeting Oct 27–28 → new rate effective Oct 29 (3 of 31 October days).
   Nov contract:  E[Δ] = (100 − ZQX) − EFFR_now            (whole month after the meeting)
   Oct contract:  E[Δ] = ((100 − ZQV) − EFFR_now) · 31/3"""
import json, sys, urllib.request, io, numpy as np, pandas as pd, yfinance as yf
R = sys.argv[1]; out = []
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r: return r.read()
import subprocess
effr = pd.read_csv(io.StringIO(subprocess.run(['curl', '-s', '--max-time', '30', "https://fred.stlouisfed.org/graph/fredgraph.csv?id=EFFR&cosd=2026-09-01"], capture_output=True, text=True).stdout)).dropna()
effr.columns = ['d', 'v']; effr = effr[effr.v != '.']; e_now = float(effr.v.iloc[-1])
zq = {t: yf.Ticker(t).history(period='5d').Close.iloc[-1] for t in ['ZQV26.CBT', 'ZQX26.CBT', 'ZQZ26.CBT']}
d_nov = (100 - zq['ZQX26.CBT']) - e_now; d_oct = ((100 - zq['ZQV26.CBT']) - e_now) * 31 / 3
out.append(f"EFFR {e_now:.2f}% ({effr.d.iloc[-1]}); ZQ Oct {zq['ZQV26.CBT']:.4f}, Nov {zq['ZQX26.CBT']:.4f}, Dec {zq['ZQZ26.CBT']:.4f}")
out.append(f"Futures-implied expected change at the Oct 28 meeting: Nov contract {100*d_nov:+.1f}bp, Oct contract {100*d_oct:+.1f}bp")
out.append(f"  → P(+25bp) ≈ E[Δ]/25bp = {d_nov/0.25:.2f} (Nov) / {d_oct/0.25:.2f} (Oct), if the only alternatives are hold or +25")
# Polymarket
s = None
for slug in ['fed-decision-in-october', 'fed-decision-in-october-2026']:
    try:
        ev = json.loads(get(f"https://gamma-api.polymarket.com/events?slug={slug}"))
        if ev and '2026' in (ev[0].get('endDate') or ''): s = ev[0]; break
    except Exception: pass
if s is None:
    ms = json.loads(get("https://gamma-api.polymarket.com/markets?closed=false&limit=40&order=volume24hr&ascending=false"))
    ms = [m for m in ms if 'after the October 2026 meeting' in m['question']]
else:
    ms = [m for m in s['markets'] if not m.get('closed')]
bk = {}
for m in ms:
    b, a = float(m.get('bestBid') or 0), float(m.get('bestAsk') or 0); bk[m.get('groupItemTitle') or m['question'][:50]] = (b, a, (a + b) / 2)
out.append("Polymarket Oct meeting (bid/ask/mid): " + "; ".join(f"{k} {v[0]:.3f}/{v[1]:.3f}" for k, v in bk.items()))
size = {'50+ bps decrease': -50, '25 bps decrease': -25, 'No change': 0, '25 bps increase': 25, '50+ bps increase': 50}
mids = {k: v[2] for k, v in bk.items() if k in size}; tot = sum(mids.values())
ev_pm = sum(size[k] * v for k, v in mids.items()) / tot
out.append(f"  Σ mids {tot:.3f}; Polymarket expected change {ev_pm:+.1f}bp (normalised mids)")
out.append(f"  Difference Polymarket − futures(Nov): {ev_pm - 100*d_nov:+.1f}bp ≈ {(ev_pm - 100*d_nov)/25:+.3f} in P(+25bp)")
txt = "\n".join(out); print(txt); open(f"{R}/notes/s7_out.txt", "w").write(txt)
