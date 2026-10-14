"""T4: does the 2024 election contract co-move with stocks (hedging demand → risk premium)?
Daily Polymarket P(Trump wins 2024) changes vs daily returns of SPY and sector/thematic ETFs (Yahoo), Jan–Nov 5 2024.
If Δp has market beta β (per 1% market move), the CAPM-style risk premium in the price is ≈ −β_contract·ERP·T, tiny for small β."""
import json, sys, numpy as np, pandas as pd, statsmodels.api as sm, yfinance as yf
R = sys.argv[1]; out = []
H = json.load(open(f"{R}/data/pm/hist.json")); M = pd.read_csv(f"{R}/data/pm/markets.csv", dtype={'tok': str})
tok = M[M.q.str.contains('Donald Trump win the 2024 US Presidential', na=False)].tok.iloc[0]
p = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True).tz_convert('America/New_York').normalize().tz_localize(None): x['p'] for x in H[tok]}).sort_index()
p = p[(p.index >= '2024-01-15') & (p.index <= '2024-11-05')]
tick = ['SPY', 'IWM', 'XLE', 'XLF', 'TAN', 'ICLN', 'TLT', 'GLD', 'IBIT', 'MXN=X']
px = yf.download(tick, start='2024-01-01', end='2024-11-07', progress=False, auto_adjust=True)['Close']
ret = np.log(px).diff()
# Polymarket daily point is stamped ~00:00 UTC (= evening ET of the previous day) → align to the NEXT trading day's close? use same-date close vs change to next stamp
dp = p.diff()   # stamp 00:00 UTC = ~8pm ET of label date D → change from eve D−1 to eve D covers trading day D (a shift(−1) misaligns by a day)
J = pd.concat([dp.rename('dp'), ret], axis=1).dropna()
J2 = pd.concat([p.diff().shift(-1).rename('dp'), ret], axis=1).dropna()
out.append(f'Alignment check corr(dp, SPY): correct {J.dp.corr(J.SPY):+.3f} vs off-by-one {J2.dp.corr(J2.SPY):+.3f}')
out.append(f"Trump-2024 contract: {len(J)} trading days (Jan 15 → Nov 5 2024); daily sd of Δp {100*J.dp.std():.2f}¢")
for t in tick:
    f = sm.OLS(J.dp * 100, sm.add_constant(J[t] * 100)).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    out.append(f"  {t:<6} beta {f.params.iloc[1]:+.3f}¢ per 1% move (t {f.tvalues.iloc[1]:+.1f}), corr {J.dp.corr(J[t]):+.3f}")
# multivariate: which assets 'priced' the election
X = J[['SPY', 'TAN', 'XLE', 'MXN=X', 'IBIT', 'TLT']].dropna() * 100
f = sm.OLS(J.loc[X.index, 'dp'] * 100, sm.add_constant(X)).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
out.append("  joint: " + ", ".join(f"{k} {v:+.2f} (t {f.tvalues[k]:+.1f})" for k, v in f.params.items() if k != 'const') + f"; R² {f.rsquared:.3f}")
b = sm.OLS(J.dp * 100, sm.add_constant(J.SPY * 100)).fit().params.iloc[1]
out.append(f"\nRisk-premium bound: contract beta to SPY {b:+.3f}¢ per 1% → as a $1 position, beta ≈ {b/100/0.5:+.3f} (vs a 50¢ price).")
out.append(f"  With a 5%/yr equity premium and ~0.8 yr to expiry, required discount ≈ beta × 5% × 0.8 × price ≈ {abs(b/100/0.5)*0.05*0.8*50:.2f}¢ — negligible vs fees and spread.")
txt = "\n".join(out); print(txt); open(f"{R}/notes/t4_out.txt", "w").write(txt)
