"""V2: BTC variance risk premium. DVOL (Deribit 30-day implied vol index, daily) vs the realized vol of the NEXT 30 days
(Deribit BTC-PERPETUAL daily closes, annualised with √365). VRP = DVOL − RV_fwd (vol points) and DVOL² − RV² (variance).
A short-variance position (sell 30d variance at DVOL², receive RV²) earns the variance VRP; report by year, hit rate, tails."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '60', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2 ** i)
now = int(time.time() * 1000); start = int(pd.Timestamp('2021-04-01', tz='UTC').timestamp() * 1000)
dv = []; a = start
while a < now:
    b = min(a + 900 * 86400 * 1000, now)
    d = get(f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp={a}&end_timestamp={b}&resolution=1D")['result']['data']
    dv += [(x[0], x[4]) for x in d]; a = b
V = pd.Series(dict(dv)).sort_index(); V.index = pd.to_datetime(V.index, unit='ms', utc=True).normalize(); V = V[~V.index.duplicated()]
px = []; a = start
while a < now:
    b = min(a + 900 * 86400 * 1000, now)
    d = get(f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&start_timestamp={a}&end_timestamp={b}&resolution=1D")['result']
    px += list(zip(d['ticks'], d['close'])); a = b
P = pd.Series(dict(px)).sort_index(); P.index = pd.to_datetime(P.index, unit='ms', utc=True).normalize() + pd.Timedelta(days=1)   # daily bar stamped at open → close known next day
r = np.log(P).diff()
rv_fwd = r[::-1].rolling(30).std()[::-1].shift(-1) * np.sqrt(365) * 100     # realized vol over the next 30 days
D = pd.DataFrame({'dvol': V, 'rv': rv_fwd}).dropna()
D['vrp'] = D.dvol - D.rv; D['vrp_var'] = (D.dvol ** 2 - D.rv ** 2) / 100      # variance points /100
out.append(f"DVOL vs next-30d realized vol, {D.index[0]:%Y-%m-%d} → {D.index[-1]:%Y-%m-%d} ({len(D)} days)")
out.append(f"  mean DVOL {D.dvol.mean():.1f}, mean fwd RV {D.rv.mean():.1f} → VRP {D.vrp.mean():+.1f} vol pts; DVOL > RV on {(D.vrp>0).mean():.0%} of days")
nonover = D.iloc[::30]
out.append(f"  non-overlapping 30-day windows: n {len(nonover)}, mean VRP {nonover.vrp.mean():+.1f} ± {nonover.vrp.std()/np.sqrt(len(nonover)):.1f} (t {nonover.vrp.mean()/(nonover.vrp.std()/np.sqrt(len(nonover))):.1f}); worst {nonover.vrp.min():+.1f}")
for y, g in D.groupby(D.index.year): out.append(f"  {y}: DVOL {g.dvol.mean():5.1f}  RV {g.rv.mean():5.1f}  VRP {g.vrp.mean():+5.1f}  share>0 {(g.vrp>0).mean():.0%}")
# predictive regression: does DVOL forecast RV (Mincer–Zarnowitz) — slope<1 means DVOL overreacts
import statsmodels.api as sm
f = sm.OLS(nonover.rv, sm.add_constant(nonover.dvol)).fit()
out.append(f"  Mincer–Zarnowitz on non-overlapping windows: RV = {f.params.iloc[0]:.1f} + {f.params.iloc[1]:.2f}·DVOL (R² {f.rsquared:.2f}); unbiased would be 0 + 1·DVOL")
txt = "\n".join(out); print(txt); open(f"{R}/notes/v2_out.txt", "w").write(txt)
