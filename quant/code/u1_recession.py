"""U1: recession contracts as insurance. Daily Polymarket P(US recession) vs SPY (alignment as in T4: stamp 00:00 UTC = previous
evening ET → p.diff() at label D covers trading day D). A contract that pays in bad states (negative market beta) should trade
ABOVE the true probability: premium ≈ −β_$ · ERP · T, where β_$ = dollar beta of a $1-payoff contract to the market."""
import json, subprocess, sys, numpy as np, pandas as pd, statsmodels.api as sm, yfinance as yf
R = sys.argv[1]; out = []
def get(u):
    r = subprocess.run(['curl', '-s', '--max-time', '40', '-A', 'Mozilla/5.0', u], capture_output=True, text=True); return json.loads(r.stdout)
spy = yf.download('SPY', start='2024-06-01', end='2026-10-15', progress=False, auto_adjust=True)['Close'].iloc[:, 0]; rs = np.log(spy).diff()
for slug in ['us-recession-in-2025', 'us-recession-by-end-of-2026']:
    e = get(f"https://gamma-api.polymarket.com/events?slug={slug}")[0]; m = max(e['markets'], key=lambda m: float(m.get('volumeNum') or 0))
    yes = json.loads(m['clobTokenIds'])[0]; h = get(f"https://clob.polymarket.com/prices-history?market={yes}&interval=max&fidelity=1440")['history']
    p = pd.Series({pd.to_datetime(x['t'], unit='s', utc=True).tz_convert('America/New_York').normalize().tz_localize(None): x['p'] for x in h}).sort_index()
    J = pd.concat([p.diff().rename('dp'), rs.rename('r')], axis=1).dropna()
    f = sm.OLS(J.dp * 100, sm.add_constant(J.r * 100)).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    b = f.params.iloc[1]                                   # ¢ per 1% SPY move
    big = J[J.r.abs() > 0.02]
    T_left = max((pd.Timestamp(m['endDate']).tz_localize(None) if pd.Timestamp(m['endDate']).tzinfo is None else pd.Timestamp(m['endDate']).tz_convert(None)) - J.index[0], pd.Timedelta(days=1)).days / 365
    prem = -(100 * b) * 0.05 * T_left                     # ¢: price sensitivity per 100% market move (100·b ¢) × 5% ERP × years
    out.append(f"{m['question']}  outcome {m.get('outcomePrices')}  ({len(J)} days {J.index[0]:%Y-%m-%d}→{J.index[-1]:%Y-%m-%d}, mean price {p.mean():.3f})")
    out.append(f"  beta {b:+.3f}¢ per 1% SPY (t {f.tvalues.iloc[1]:+.1f}), corr {J.dp.corr(J.r):+.3f}, R² {f.rsquared:.2f}; on |SPY|>2% days (n {len(big)}): corr {big.dp.corr(big.r):+.2f}")
    out.append(f"  ⇒ dPrice/dMarket = {b:+.2f}¢ per 1% = {b:+.2f}$ per 100%; per $ invested at {p.mean()*100:.0f}¢: CAPM beta ≈ {b/(p.mean()):+.1f}")
    out.append(f"  CAPM insurance premium: −dPrice/dMarket × ERP 5%/yr × {T_left:.1f}y ≈ {prem:+.1f}¢ (price ABOVE true probability); as share of price {prem/(p.mean()*100):.0%}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/u1_out.txt", "w").write(txt)
