import numpy as np, pandas as pd, sys
from scipy import stats
R=sys.argv[1]; rng=np.random.default_rng(1)
def mertens_se(sr,sk,ku,T): return np.sqrt((1+0.5*sr**2-sk*sr+(ku-3)/4*sr**2)/T)
def psr(sr,sk,ku,T,sr0=0): return stats.norm.cdf((sr-sr0)*np.sqrt(T-1)/np.sqrt(1-sk*sr+(ku-1)/4*sr**2))
def mintrl(sr,sk,ku,sr0=0,a=0.05): return 1+(1-sk*sr+(ku-1)/4*sr**2)*(stats.norm.ppf(1-a)/(sr-sr0))**2
out=[]
# 1) verify SE formula by simulation: normal and fat-tailed/skewed
T=1260
for name,gen in [('normal',lambda n: rng.normal(0.0004,0.01,n)),
                 ('skewed fat (short-vol like)',lambda n: 0.0008+0.006*rng.standard_t(4,n)-0.02*(rng.random(n)<0.02))]:
    big=gen(2_000_000); sr=big.mean()/big.std(); sk=stats.skew(big); ku=stats.kurtosis(big,fisher=False)
    srs=[ (x:=gen(T)).mean()/x.std(ddof=1) for _ in range(4000)]
    out.append(f"{name}: daily SR={sr:.4f} skew={sk:.2f} kurt={ku:.1f} | simulated SE(SR̂)={np.std(srs):.4f}  Lo iid-normal SE={np.sqrt((1+sr**2/2)/T):.4f}  Mertens SE={mertens_se(sr,sk,ku,T):.4f}")
# 2) SPY real data
d=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True); r=np.log(d.Close).diff().dropna()
for lab,x in [('SPY daily 1999-2026',r),('SPY daily 2017-2026',r['2017':])]:
    T=len(x); sr=x.mean()/x.std(); sk=stats.skew(x); ku=stats.kurtosis(x,fisher=False)
    out.append(f"{lab}: T={T} SR_daily={sr:.4f} (ann {sr*np.sqrt(252):.2f}) skew={sk:.2f} kurt={ku:.1f} SE_ann naive={np.sqrt(1/T)*np.sqrt(252):.2f} Mertens SE_ann={mertens_se(sr,sk,ku,T)*np.sqrt(252):.2f} PSR(SR>0)={psr(sr,sk,ku,T):.3f}  MinTRL(95%)={mintrl(sr,sk,ku)/252:.1f} yrs")
# 3) Min track record for hypothetical strategies (daily obs, normal)
for SRa in [0.5,1.0,2.0]:
    s=SRa/np.sqrt(252); out.append(f"annual SR {SRa}: years of daily data to be 95% sure SR>0 (normal) = {mintrl(s,0,3)/252:.1f}; with skew -1, kurt 10 = {mintrl(s,-1,10)/252:.1f}")
# 4) Lo autocorrelation-adjusted annualization on monthly series
m=d.Close.resample('ME').last().pct_change().dropna()
def lo_eta(x,q,K=None):
    rho=[x.autocorr(k) for k in range(1,q)]; return q/np.sqrt(q+2*sum((q-k)*rho[k-1] for k in range(1,q)))
sr_m=m.mean()/m.std()
out.append(f"SPY monthly SR={sr_m:.3f}; naive annual=√12·SR={np.sqrt(12)*sr_m:.2f}; Lo-adjusted={lo_eta(m,12)*sr_m:.2f}; lag1 autocorr={m.autocorr(1):.3f}")
# illustrate with positively autocorrelated (smoothed) returns
x=pd.Series(rng.normal(0.01,0.03,600)); y=0.5*x+0.5*x.shift(1).fillna(0.01)
out.append(f"smoothed series (like illiquid/stale prices): lag1 rho={y.autocorr(1):.2f}; naive ann SR={np.sqrt(12)*y.mean()/y.std():.2f} vs Lo-adjusted={lo_eta(y,12)*y.mean()/y.std():.2f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/a2_out.txt','w').write(txt)
