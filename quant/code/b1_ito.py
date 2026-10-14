import numpy as np, pandas as pd, yfinance as yf, sys
R=sys.argv[1]; rng=np.random.default_rng(6); out=[]
# 1) quadratic variation: sum (ΔW)^2 -> T, sum |ΔW| -> inf, sum ΔW*Δt -> 0
for n in [10,1000,100000]:
    dW=rng.normal(0,np.sqrt(1/n),n); out.append(f"n={n:6d}: Σ(ΔW)²={np.sum(dW**2):.4f}  Σ|ΔW|={np.sum(abs(dW)):.1f}  ΣΔW·Δt={np.sum(dW)/n:.5f}")
# 2) GBM: mean vs median terminal wealth
mu,sig,T=0.08,0.40,10; Z=rng.standard_normal(200000)
ST=np.exp((mu-sig**2/2)*T+sig*np.sqrt(T)*Z)
out.append(f"GBM mu=8% sigma=40% 10y: E[S_T]={ST.mean():.2f} (theory e^(μT)={np.exp(mu*T):.2f}); median={np.median(ST):.2f} (theory e^((μ-σ²/2)T)={np.exp((mu-sig**2/2)*T):.2f}); P(S_T<1)={np.mean(ST<1):.2f}")
# 3) leveraged ETFs: real data test of volatility drag
px=yf.download(['SPY','SSO','UPRO'],start='2009-07-01',end='2026-10-14',progress=False,auto_adjust=True)['Close'].dropna()
px.to_csv(f'{R}/data/lev_etfs.csv'); r=px.pct_change().dropna()
yrs=len(r)/252; mu_s=r.SPY.mean()*252; var_s=r.SPY.var()*252
for tk,L in [('SPY',1),('SSO',2),('UPRO',3)]:
    actual=(1+r[tk]).prod()**(1/yrs)-1
    naive=(1+r.SPY).prod()**(L/yrs)-1    # "L times the index over the period"
    ito=np.exp(L*mu_s - L**2*var_s/2)-1   # continuous approx, no costs
    out.append(f"{tk} ({L}x) 2009-07→2026-10: actual CAGR {actual:.1%} | 'L× SPY compounded' {naive:.1%} | Itô Lμ−L²σ²/2 (no costs) {ito:.1%} | daily tracking: corr {np.corrcoef(r[tk],r.SPY)[0,1]:.4f}, mean ratio {r[tk].mean()/r.SPY.mean():.2f}")
out.append(f"SPY annual arithmetic mean μ={mu_s:.1%}, σ={np.sqrt(var_s):.1%}, drag σ²/2={var_s/2:.2%}")
# 4) where leverage stops helping: optimal L = μ/σ² (Kelly, ignoring costs)
out.append(f"growth-optimal leverage μ/σ² = {mu_s/var_s:.2f}x (before financing costs, using realized 2009-26 μ — hindsight)")
# 5) choppy vs trending: -10%,+11.11% round trip
out.append(f"round-trip example: index -10% then +11.11% → {0.9*1.1111-1:+.2%}; 3x → {(1-0.3)*(1+0.3333)-1:+.2%}")
txt="\n".join(out); print(txt); open(f'{R}/notes/b1_out.txt','w').write(txt)
