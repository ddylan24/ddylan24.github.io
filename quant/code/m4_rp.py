import numpy as np, pandas as pd, yfinance as yf, sys, warnings; warnings.filterwarnings('ignore')
R=sys.argv[1]; out=[]
px=yf.download(['SPY','IEF','TLT','GLD','DBC'],start='2006-03-01',end='2026-10-14',progress=False,auto_adjust=True)['Close'].dropna()
r=px.pct_change().dropna()
rf=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True).rf.reindex(r.index).ffill().fillna(0)
def stats_(x,lab):
    x=x.loc['2007-03-05':]
    eq=(1+x).cumprod(); yrs=len(x)/252; cagr=eq.iloc[-1]**(1/yrs)-1; e=x-rf
    dd=(1-eq/eq.cummax()).max(); y22=(1+x['2022']).prod()-1; y08=(1+x['2008']).prod()-1
    out.append(f"  {lab:<36} CAGR {cagr:5.1%}  vol {x.std()*np.sqrt(252):5.1%}  Sharpe {e.mean()/e.std()*np.sqrt(252):.2f}  maxDD {dd:5.1%}  2008 {y08:+.1%}  2022 {y22:+.1%}")
assets=['SPY','IEF','GLD','DBC']
me=r.resample('ME').last().index
def rebal(wfun,lev_target=None):
    w=pd.DataFrame(0.0,index=r.index,columns=assets); cur=None
    for i,d in enumerate(r.index):
        if i<252: continue
        if cur is None or d in me: cur=wfun(r.loc[:d].iloc[-252:])
        w.loc[d]=cur
    w=w.shift(1).iloc[253:]
    port=(w*r[assets].loc[w.index]).sum(1)
    if lev_target:
        vol=port.rolling(63).std().shift(1)*np.sqrt(252); L=(lev_target/vol).clip(upper=3).fillna(1)
        port=L*port-(L-1)*rf.loc[port.index]
    return port
out.append(f"Multi-asset ETFs (Yahoo adj. closes; financing at Ken French RF) {r.index[0].date()}→{r.index[-1].date()}, monthly rebalance, weights from prior 252 days")
stats_(r.SPY,'SPY (stocks only)')
stats_(rebal(lambda h:pd.Series([0.6,0.4,0,0],index=assets)),'60/40 SPY/IEF')
iv=lambda h:(1/h[assets].std())/(1/h[assets].std()).sum()
stats_(rebal(iv),'risk parity (inverse vol), unlevered')
stats_(rebal(iv,0.10),'risk parity levered to 10% vol')
# equal risk contribution with covariance
def erc(h):
    # Spinu (2013) convex formulation: min ½wᵀΣw − Σ (1/n) ln wᵢ, then normalize → equal risk contributions, robust to negative correlations
    from scipy.optimize import minimize
    S=h[assets].cov().values*252; n=len(assets)
    f=lambda y: 0.5*y@S@y-np.sum(np.log(y))/n
    g=lambda y: S@y-1/(n*y)
    y=minimize(f,np.ones(n)/np.sqrt(np.trace(S)),jac=g,bounds=[(1e-8,None)]*n,method='L-BFGS-B').x
    return pd.Series(y/y.sum(),index=assets)
stats_(rebal(erc,0.10),'equal-risk-contribution levered 10%')
corr=r.SPY.rolling(252).corr(r.IEF)
out.append(f"Rolling 1y SPY–IEF correlation: 2006–2020 avg {corr[:'2020'].mean():+.2f}; 2022 {corr['2022'].mean():+.2f}; 2023–2026 {corr['2023':].mean():+.2f}  (the diversification that risk parity relies on flipped in 2022)")
w=erc(r.iloc[-252:]); out.append("Current ERC weights: "+", ".join(f"{k} {v:.0%}" for k,v in w.items()))
txt="\n".join(out); print(txt); open(f'{R}/notes/m4_out.txt','w').write(txt)
