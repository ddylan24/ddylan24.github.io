import numpy as np, pandas as pd, yfinance as yf, sys, datetime as dt, warnings; warnings.filterwarnings('ignore')
from scipy.stats import norm
from scipy.optimize import brentq
R=sys.argv[1]; out=[]
t=yf.Ticker('SPY'); exps=t.options; spot=t.history(period='5d').Close.iloc[-1]
today=pd.Timestamp('2026-10-14')
cands=[e for e in exps if 25<=(pd.Timestamp(e)-today).days<=45] or list(exps[3:4])
e=cands[0]; T=(pd.Timestamp(e)-today).days/365
rf=pd.to_numeric(pd.read_csv(f'{R}/data/DGS3MO.csv',index_col=0).iloc[:,0],errors='coerce').dropna().iloc[-1]/100
ch=t.option_chain(e); calls,puts=ch.calls,ch.puts
def bs(S,K,T,r,s,call):
    d1=(np.log(S/K)+(r+s*s/2)*T)/(s*np.sqrt(T)); d2=d1-s*np.sqrt(T)
    return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2) if call else K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
def iv(price,K,call):
    try: return brentq(lambda s: bs(spot,K,T,rf,s,call)-price,1e-4,3)
    except Exception: return np.nan
rows=[]
for df,call in [(puts,False),(calls,True)]:
    for _,r in df.iterrows():
        K=r.strike; mid=(r.bid+r.ask)/2 if r.bid>0 and r.ask>0 else np.nan
        if np.isnan(mid): continue
        otm=(K<spot and not call) or (K>=spot and call)   # use OTM options only
        if not otm: continue
        rows.append(dict(K=K,m=K/spot,iv=iv(mid,K,call),yiv=r.impliedVolatility,spread_pct=(r.ask-r.bid)/mid,oi=r.openInterest))
d=pd.DataFrame(rows).dropna().sort_values('K'); d=d[(d.m>0.80)&(d.m<1.10)&(d.spread_pct<0.5)]
out.append(f"SPY options chain (Yahoo), expiry {e} ({T*365:.0f} days), spot {spot:.2f}, r={rf:.2%} (FRED 3m T-bill); OTM puts below spot, OTM calls above; mid prices, spread<50%")
for mm in [0.85,0.90,0.95,0.975,1.0,1.025,1.05]:
    rr=d.iloc[(d.m-mm).abs().argsort()[:1]]
    out.append(f"  K/S={rr.m.values[0]:.3f}: my IV {rr.iv.values[0]:.1%} (Yahoo's {rr.yiv.values[0]:.1%})")
atm=d.iloc[(d.m-1).abs().argsort()[:1]].iv.values[0]; p90=d.iloc[(d.m-0.9).abs().argsort()[:1]].iv.values[0]; c105=d.iloc[(d.m-1.05).abs().argsort()[:1]].iv.values[0]
out.append(f"  skew: 90% put IV − ATM IV = {p90-atm:+.1%} vol pts; 105% call − ATM = {c105-atm:+.1%}")
# risk-neutral density via Breeden–Litzenberger from a smoothed IV curve
from numpy.polynomial import polynomial as P
c=np.polyfit(d.m,d.iv,4); Ks=np.linspace(0.82,1.08,400)*spot; ivs=np.polyval(c,Ks/spot)
C=np.array([bs(spot,K,T,rf,s,True) for K,s in zip(Ks,ivs)]); dK=Ks[1]-Ks[0]
dens=np.exp(rf*T)*np.gradient(np.gradient(C,dK),dK)
dens=np.clip(dens,0,None); dens/=np.trapezoid(dens,Ks)
mean=np.trapezoid(Ks*dens,Ks); sd=np.sqrt(np.trapezoid((Ks-mean)**2*dens,Ks)); sk=np.trapezoid(((Ks-mean)/sd)**3*dens,Ks)
lognorm_p10=norm.cdf((np.log(0.9)-(rf-atm**2/2)*T)/(atm*np.sqrt(T)))
p10=np.trapezoid(dens[Ks<0.9*spot],Ks[Ks<0.9*spot])
out.append(f"  Breeden–Litzenberger risk-neutral density (from smoothed smile): skew {sk:.2f}; P(SPY falls >10% by expiry) = {p10:.1%} vs {lognorm_p10:.1%} under flat-vol Black–Scholes at ATM IV")
txt="\n".join(out); print(txt); open(f'{R}/notes/j2_out.txt','w').write(txt); d.to_csv(f'{R}/data/spy_smile_{e}.csv',index=False)
