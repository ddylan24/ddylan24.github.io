import numpy as np, pandas as pd, sys
R=sys.argv[1]; rng=np.random.default_rng(7); out=[]
def fit_ou(x,dt=1/252):
    x=np.asarray(x); X,Y=x[:-1],x[1:]; b,a=np.polyfit(X,Y,1); e=Y-(a+b*X)
    th=-np.log(b)/dt; mu=a/(1-b); sig=e.std(ddof=2)*np.sqrt(2*th/(1-b**2))
    return th,mu,sig,np.log(2)/th*252,b   # half-life in trading days
def sim_ou(th,mu,sig,n,dt=1/252,x0=None):
    b=np.exp(-th*dt); s=sig*np.sqrt((1-b**2)/(2*th)); x=np.empty(n); x[0]=mu if x0 is None else x0
    for t in range(1,n): x[t]=mu+(x[t-1]-mu)*b+s*rng.standard_normal()
    return x
# 1) estimator check + small-sample bias
TH,MU,SIG=4.0,20,30   # half-life ln2/4 yr = 43.7 trading days
for yrs in [1,3,10,30]:
    est=[fit_ou(sim_ou(TH,MU,SIG,252*yrs))[3] for _ in range(400)]
    out.append(f"true half-life {np.log(2)/TH*252:.1f}d | {yrs:2d}y data: median est {np.median(est):.1f}d, 10–90% [{np.percentile(est,10):.1f}, {np.percentile(est,90):.1f}]")
# 2) real FRED series
def load(s):
    d=pd.read_csv(f'{R}/data/{s}.csv',index_col=0,parse_dates=True).iloc[:,0]; return pd.to_numeric(d,errors='coerce').dropna()
for s,lab in [('VIXCLS','VIX'),('T10Y2Y','10y–2y Treasury spread'),('BAMLH0A0HYM2','High-yield credit spread')]:
    x=load(s); th,mu,sig,hl,b=fit_ou(x.values)
    xl=np.log(x) if s=='VIXCLS' else None
    msg=f"{lab} ({x.index[0].date()}→{x.index[-1].date()}, n={len(x)}): AR1 b={b:.4f}, θ={th:.2f}/yr, mean={mu:.2f}, half-life={hl:.0f} trading days"
    if s=='VIXCLS':
        th2,mu2,sig2,hl2,_=fit_ou(np.log(x.values)); msg+=f" | log-VIX half-life={hl2:.0f}d, long-run level={np.exp(mu2):.1f}"
        # sub-period stability
        for a,bb in [('1990','2007'),('2008','2019'),('2020','2026')]:
            msg+=f"\n    {a}-{bb}: half-life {fit_ou(np.log(x[a:bb].values))[3]:.0f}d, mean {np.exp(fit_ou(np.log(x[a:bb].values))[1]):.1f}"
    out.append(msg)
# 3) stationarity sanity: ADF
from statsmodels.tsa.stattools import adfuller
for s in ['VIXCLS','T10Y2Y']:
    x=load(s); out.append(f"ADF {s}: stat={adfuller(x.values,maxlag=20)[0]:.2f}, p={adfuller(x.values,maxlag=20)[1]:.4f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/b2_out.txt','w').write(txt)
