import numpy as np, pandas as pd, sys, glob, warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,sys.argv[1])
from kf import read_kf
from scipy.stats import norm, poisson
from scipy.optimize import minimize, brentq
from math import factorial
R=sys.argv[1]; out=[]; rng=np.random.default_rng(20)
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True); x=np.log1p(ff.mkt_rf+ff.rf)['2000':].values; dt=1/252
def nll(p):
    mu,s,lam,mj,sj=p
    if s<=0 or sj<=0 or lam<=0: return 1e10
    L=0
    for k in range(5):
        L=L+poisson.pmf(k,lam*dt)*norm.pdf(x,mu*dt+k*mj,np.sqrt(s*s*dt+k*sj*sj))
    return -np.sum(np.log(L+1e-300))
res=minimize(nll,[0.08,0.15,10,-0.02,0.03],method='Nelder-Mead',options={'maxiter':6000,'xatol':1e-6,'fatol':1e-6})
mu,s,lam,mj,sj=res.x
out.append(f"Merton jump-diffusion MLE on CRSP daily 2000–2026: diffusion σ={s:.1%}/yr, jumps λ={lam:.1f}/yr, mean jump {mj:+.2%}, jump σ {sj:.2%}; jump share of variance {lam*(mj**2+sj**2)/(s*s+lam*(mj**2+sj**2)):.0%}")
from scipy.stats import norm as N
ll_n=-np.sum(N.logpdf(x,x.mean(),x.std())); out.append(f"  log-likelihood: normal {-ll_n:.0f} vs jump-diffusion {-res.fun:.0f} (Δ={ll_n-res.fun:.0f}, huge)")
# Merton option price (series)
sm=pd.read_csv(sorted(glob.glob(f'{R}/data/spy_smile_*.csv'))[-1]); S,T,r=768.33,30/365,0.0425
def bs(S,K,T,r,v,call):
    d1=(np.log(S/K)+(r+v*v/2)*T)/(v*np.sqrt(T)); d2=d1-v*np.sqrt(T)
    return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2) if call else K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
def merton(K,call,s,lam,mj,sj):
    k=np.exp(mj+sj*sj/2)-1; lp=lam*(1+k); tot=0
    for n in range(40):
        sn=np.sqrt(s*s+n*sj*sj/T); rn=r-lam*k+n*np.log(1+k)/T
        tot+=np.exp(-lp*T)*(lp*T)**n/factorial(n)*bs(S,K,T,rn,sn,call)
    return tot
def iv(p,K,call):
    try: return brentq(lambda v: bs(S,K,T,r,v,call)-p,1e-4,3)
    except Exception: return np.nan
mg=np.array([0.85,0.90,0.95,0.975,1.0,1.025,1.05]); mkt=np.array([sm.iloc[(sm.m-m).abs().argsort()[:1]].iv.values[0] for m in mg])
def smile(s,lam,mj,sj): return np.array([iv(merton(m*S,m>=1,s,lam,mj,sj),m*S,m>=1) for m in mg])
ph=smile(s,lam,mj,sj); out.append("  Merton smile with PHYSICAL (historical) params: "+" ".join(f"{v:.1%}" for v in ph)+f"  RMSE {np.sqrt(np.nanmean((ph-mkt)**2)):.2%}")
def obj(p):
    s_,lam_,mj_,sj_=p
    if s_<=0.01 or lam_<=0 or sj_<=0.001: return 1
    v=smile(s_,lam_,mj_,sj_); return np.nanmean((v-mkt)**2)
cal=minimize(obj,[0.10,1.0,-0.10,0.08],method='Nelder-Mead',options={'maxiter':800})
q=smile(*cal.x); out.append(f"  Merton CALIBRATED to smile: σ={cal.x[0]:.1%}, λ={cal.x[1]:.2f}/yr, mean jump {cal.x[2]:+.1%}, jump σ {cal.x[3]:.1%} → "+" ".join(f"{v:.1%}" for v in q)+f"  RMSE {np.sqrt(np.nanmean((q-mkt)**2)):.2%} (Heston best 1.31%)")
out.append(f"  market: "+" ".join(f"{v:.1%}" for v in mkt))
# L5 value drawdown
hml=read_kf(f'{R}/data/F-F_Research_Data_5_Factors_2x3.csv')['HML']
ffm=read_kf(f'{R}/data/F-F_Momentum_Factor.csv')  # just to ensure parser ok
# use long HML history from 3-factor monthly? daily file has HML from 1926 — aggregate
hd=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True).hml
h=(1+hd).resample('ME').prod()-1
eq=(1+h).cumprod(); dd=1-eq/eq.cummax()
pk=eq.loc[:'2020-12'].loc['2006':].idxmax(); tr=dd.loc['2007':'2021'].idxmax()
rec=eq.loc[tr:][eq.loc[tr:]>=eq[pk]].index
out.append(f"HML (value) 1926–2026 monthly: Sharpe {h.mean()/h.std()*np.sqrt(12):.2f}; 2007–2020 drawdown {dd[tr]:.0%} (peak {pk.strftime('%Y-%m')} → trough {tr.strftime('%Y-%m')}); recovered to peak: {rec[0].strftime('%Y-%m') if len(rec) else 'not yet'}")
out.append(f"  previous worst HML drawdown before 2007: {dd[:'2006'].max():.0%} ({dd[:'2006'].idxmax().strftime('%Y-%m')})")
pre=h[:'2006'].values; n=len(h); bigger=0; B=2000
for _ in range(B):
    idx=[]; 
    while len(idx)<n:
        s0=rng.integers(len(pre)); L=rng.geometric(1/24); idx+= [(s0+j)%len(pre) for j in range(L)]
    sim=pre[np.array(idx[:n])]; e=np.cumprod(1+sim); bigger+=(1-e/np.maximum.accumulate(e)).max()>=dd[tr]
out.append(f"  block bootstrap of pre-2007 HML history (100 yrs, blocks ~24m): P(max drawdown ≥ {dd[tr]:.0%}) = {bigger/B:.1%}")
sr_pre=pre.mean()/pre.std()*np.sqrt(12); yrs=(tr-pk).days/365
out.append(f"  for a strategy with Sharpe {sr_pre:.2f}, P(loss over a {yrs:.0f}-year window) = {norm.cdf(-sr_pre*np.sqrt(yrs)):.1%} (iid normal)")
txt="\n".join(out); print(txt); open(f'{R}/notes/l15_out.txt','w').write(txt)
