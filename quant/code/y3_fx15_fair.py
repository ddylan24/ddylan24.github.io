"""Y3: are Kalshi 15-minute FX up/down markets efficiently priced vs spot? Fair P(YES) at a fill = N( ln(S_t/K) / (σ √τ) ),
S_t = Yahoo 1-minute spot (EURUSD=X, JPY=X) at the fill minute, K = the market's official target (floor_strike), τ = minutes to close,
σ = per-minute vol (rolling 60-min std of 1-min log returns). Compare fill prices with fair value by taker side:
do takers pay above fair (makers' edge) and is the Kalshi price stale vs spot (lead/lag)?"""
import json, subprocess, sys, time, numpy as np, pandas as pd, yfinance as yf
from scipy.stats import norm
R = sys.argv[1]; out = []
def get(u):
    r = subprocess.run(['curl', '-s', '--max-time', '40', '-A', 'Mozilla/5.0', u], capture_output=True, text=True); return json.loads(r.stdout)
F = pd.read_csv(f"{R}/data/y1/fills.csv.gz")
F = F[F.series.isin(['KXEURUSD15M', 'KXUSDJPY15M'])].copy()
F['close'] = pd.to_datetime(F.close, utc=True, format='mixed'); F['ts'] = pd.to_datetime(F.ts, utc=True, format='mixed')
for ser, yt in (('KXEURUSD15M', 'EURUSD=X'), ('KXUSDJPY15M', 'JPY=X')):
    ms, cur = [], ''
    for _ in range(10):
        d = get(f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={ser}&status=settled&limit=1000&min_close_ts={int((pd.Timestamp.now(tz='UTC')-pd.Timedelta(days=8)).timestamp())}" + (f"&cursor={cur}" if cur else ""))
        ms += d.get('markets', []); cur = d.get('cursor') or ''
        if not cur: break
    K = {m['ticker']: m.get('floor_strike') for m in ms}
    px = yf.download(yt, period='8d', interval='1m', progress=False, auto_adjust=True)['Close'].iloc[:, 0].dropna()
    px.index = px.index.tz_convert('UTC'); lr = np.log(px).diff(); vol = lr.rolling(60).std()
    g = F[F.series == ser].copy(); g['K'] = g.ticker.map(K); g = g.dropna(subset=['K'])
    g['minute'] = g.ts.dt.floor('min')
    g['S'] = px.reindex(g.minute, method='ffill').values; g['sig'] = vol.reindex(g.minute, method='ffill').values
    g['tau'] = ((g.close - g.ts).dt.total_seconds() / 60).clip(lower=0.25)
    g = g.dropna(subset=['S', 'sig'])
    g['fair'] = norm.cdf(np.log(g.S / g.K) / (g.sig * np.sqrt(g.tau)))
    g['edge_taker'] = np.where(g.side == 'yes', g.fair - g.p, g.p - g.fair)        # taker's expected gain vs fair, per contract
    w = g.n
    out.append(f"{ser}: {len(g):,} fills with spot ({g.ticker.nunique()} markets); spot source Yahoo {yt}")
    out.append(f"  taker expected edge vs fair (contract-weighted): {100*np.average(g.edge_taker, weights=w):+.2f}¢; realized taker P&L to settlement {100*(-g.maker.sum()/w.sum()):+.2f}¢")
    out.append(f"  calibration of the FAIR model on outcomes: Brier fair {np.average((g.fair - g.y)**2, weights=w):.4f} vs fill price {np.average((g.p - g.y)**2, weights=w):.4f}")
    for lo, hi in ((0.25, 3), (3, 8), (8, 15.1)):
        s = g[(g.tau > lo) & (g.tau <= hi)]
        if len(s): out.append(f"  τ {lo:>4}–{hi:<4} min: n {len(s):6d}, taker edge vs fair {100*np.average(s.edge_taker, weights=s.n):+.2f}¢, realized taker {100*(-s.maker.sum()/s.n.sum()):+.2f}¢")
txt = "\n".join(out); print(txt); open(f"{R}/notes/y3_out.txt", "w").write(txt)
