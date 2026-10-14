import numpy as np, pandas as pd, sys, glob, warnings; warnings.filterwarnings('ignore')
from scipy.stats import norm
from scipy.optimize import brentq
R=sys.argv[1]; out=[]; rng=np.random.default_rng(19)
sm=pd.read_csv(sorted(glob.glob(f'{R}/data/spy_smile_*.csv'))[-1])
S,T,r=768.33,30/365,0.0425
def bs(S,K,T,r,s,call):
    d1=(np.log(S/K)+(r+s*s/2)*T)/(s*np.sqrt(T)); d2=d1-s*np.sqrt(T)
    return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2) if call else K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
def ivol(p,K,call):
    try: return brentq(lambda s: bs(S,K,T,r,s,call)-p,1e-4,3)
    except Exception: return np.nan
mgrid=np.array([0.85,0.90,0.95,0.975,1.0,1.025,1.05])
mkt=np.array([sm.iloc[(sm.m-m).abs().argsort()[:1]].iv.values[0] for m in mgrid])
n,steps=60000,60; dt=T/steps; Z1=rng.standard_normal((steps,n)); Z2=rng.standard_normal((steps,n))
def heston(v0,kap,th,sv,rho):
    lnS=np.full(n,np.log(S)); v=np.full(n,v0)
    for i in range(steps):
        vp=np.maximum(v,0); w2=rho*Z1[i]+np.sqrt(1-rho*rho)*Z2[i]
        lnS+= (r-0.5*vp)*dt+np.sqrt(vp*dt)*Z1[i]; v+= kap*(th-vp)*dt+sv*np.sqrt(vp*dt)*w2
    ST=np.exp(lnS); ivs=[]
    for m in mgrid:
        K=m*S; call=m>=1; pay=np.maximum(ST-K,0) if call else np.maximum(K-ST,0)
        ivs.append(ivol(np.exp(-r*T)*pay.mean(),K,call))
    return np.array(ivs)
out.append("Heston dS=rSdt+√v S dW1, dv=κ(θ−v)dt+σ_v√v dW2, corr(dW1,dW2)=ρ. MC 60k paths, 30-day expiry, full-truncation Euler.")
out.append("  market IV (SPY 2026-11-13): "+" ".join(f"{m:.3f}:{v:.1%}" for m,v in zip(mgrid,mkt)))
best=None
for rho in [0.0,-0.5,-0.7,-0.9]:
    for sv in [0.6,1.0,1.4]:
        for v0 in [0.016,0.021]:
            iv=heston(v0,3.0,0.04,sv,rho); e=np.sqrt(np.nanmean((iv-mkt)**2))
            if best is None or e<best[0]: best=(e,rho,sv,v0,iv)
            if sv==1.0 and v0==0.021: out.append(f"  ρ={rho:+.1f}, σv=1.0: "+" ".join(f"{v:.1%}" for v in iv)+f"  (RMSE {e:.1%})")
e,rho,sv,v0,iv=best
out.append(f"  best on grid: ρ={rho}, σv={sv}, v0={v0} (√v0={np.sqrt(v0):.1%}), κ=3, θ=.04 → "+" ".join(f"{v:.1%}" for v in iv)+f"  RMSE {e:.2%}")
out.append("  ρ=0 gives a symmetric smile; negative spot–vol correlation (leverage effect, C2) creates the put skew.")
# K2 yield curve PCA
def ld(s): return pd.to_numeric(pd.read_csv(f'{R}/data/{s}.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce')
Y=pd.concat({s:ld(s) for s in ['DGS3MO','DGS1','DGS2','DGS5','DGS10','DGS30']},axis=1).dropna()['1990':]
dY=Y.diff().dropna(); C=np.cov(dY.values.T); ev,evec=np.linalg.eigh(C); idx=ev.argsort()[::-1]; ev,evec=ev[idx],evec[:,idx]
out.append(f"Yield-curve PCA (FRED Treasury CMT 3m,1y,2y,5y,10y,30y), daily changes {dY.index[0].date()}→{dY.index[-1].date()} (n={len(dY)}): variance explained PC1 {ev[0]/ev.sum():.1%}, PC2 {ev[1]/ev.sum():.1%}, PC3 {ev[2]/ev.sum():.1%}")
for k,lab in enumerate(['level','slope','curvature']):
    l=evec[:,k]*np.sign(evec[3,k] if k<2 else evec[2,k]); out.append(f"  PC{k+1} ({lab}) loadings: "+" ".join(f"{c}:{x:+.2f}" for c,x in zip(['3m','1y','2y','5y','10y','30y'],l)))
# duration & convexity: 10y 4% annual coupon bond at 4% yield
def price(y,c=4,T=10): t=np.arange(1,T+1); return np.sum(c/(1+y)**t)+100/(1+y)**T
y0=0.04; P0=price(y0); h=1e-4
D=-(price(y0+h)-price(y0-h))/(2*h)/P0; Cx=(price(y0+h)-2*P0+price(y0-h))/h**2/P0
for dy in [0.01,-0.01,0.03]:
    exact=price(y0+dy)/P0-1; d1=-D*dy; d2=-D*dy+0.5*Cx*dy*dy
    out.append(f"  10y 4% bond, yield {dy*1e4:+.0f}bp: exact {exact:+.2%}, duration-only {d1:+.2%}, duration+convexity {d2:+.2%}")
out.append(f"  modified duration {D:.2f}, convexity {Cx:.1f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/k12_out.txt','w').write(txt)
