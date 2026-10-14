import numpy as np, pandas as pd, yfinance as yf, sys, warnings; warnings.filterwarnings('ignore')
from statsmodels.tsa.stattools import adfuller
from scipy import stats
R=sys.argv[1]; out=[]
spy=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True).Close
lp=np.log(spy)
def fd_weights(d,thr=1e-4,maxlen=2000):
    w=[1.0]; k=1
    while k<maxlen:
        wk=-w[-1]*(d-k+1)/k
        if abs(wk)<thr: break
        w.append(wk); k+=1
    return np.array(w)
out.append("Fractional differentiation (fixed-width window, weight cutoff 1e-4) on log SPY 1999–2026:")
first=None
for d in [0,0.1,0.2,0.3,0.4,0.5,0.6,0.8,1.0]:
    w=fd_weights(d); W=len(w)
    x=np.convolve(lp.values,w,mode='valid') if W>1 else lp.values
    s=pd.Series(x,index=lp.index[W-1:])
    adf=adfuller(s.values,maxlag=1,regression='c',autolag=None)[0]; corr=np.corrcoef(s.values,lp.values[W-1:])[0,1]
    if first is None and adf<-2.86: first=d
    out.append(f"  d={d:.1f}: window {W:4d}, ADF {adf:6.2f} ({'stationary' if adf<-2.86 else 'not'} at 5%), corr with log price {corr:.3f}")
out.append(f"  minimum d passing ADF 5% on this grid: {first}")
# G2 CUSUM vs random baseline, BTC and SPY
btc=yf.download('BTC-USD',start='2015-01-01',end='2026-10-14',progress=False,auto_adjust=True)['Close'].squeeze()
btc.to_csv(f'{R}/data/btc.csv')
rng=np.random.default_rng(15)
for name,p in [('BTC-USD 2015–2026',btc),('SPY 1999–2026',spy)]:
    r=np.log(p).diff().dropna(); vol=r.rolling(20).std()
    for k in [2,3]:
        sp=sn=0; ev=[]
        for t in range(20,len(r)):
            h=k*vol.iloc[t-1]; sp=max(0,sp+r.iloc[t]); sn=min(0,sn+r.iloc[t])
            if sp>h: ev.append((r.index[t],1)); sp=0
            elif sn<-h: ev.append((r.index[t],-1)); sn=0
        e=pd.DataFrame(ev,columns=['d','dir']).set_index('d')
        lp2=np.log(p)
        msg=f"{name}, k={k}: {len(e)} events ({len(e)/(len(r)/365 if 'BTC' in name else len(r)/252):.0f}/yr)"
        for H in [1,5,20]:
            fwd=(lp2.shift(-H)-lp2).reindex(r.index)
            base=fwd.dropna()
            for dsg,lab in [(1,'up'),(-1,'down')]:
                x=fwd.reindex(e[e.dir==dsg].index).dropna()
                ex=x-base.mean(); t=ex.mean()/(x.std()/np.sqrt(len(x)))
                msg+=f"\n    {H:2d}d after {lab:4s}: mean {x.mean():+.2%} vs random day {base.mean():+.2%}, excess t={t:+.2f} (n={len(x)})"
        out.append(msg)
txt="\n".join(out); print(txt); open(f'{R}/notes/f3g2_out.txt','w').write(txt)
