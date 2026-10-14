import numpy as np, pandas as pd, sys
from scipy.stats import norm
R=sys.argv[1]; rng=np.random.default_rng(9); out=[]
def bs(S,K,T,r,s,call=True):
    d1=(np.log(S/K)+(r+s*s/2)*T)/(s*np.sqrt(T)); d2=d1-s*np.sqrt(T)
    return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2) if call else K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
def delta(S,K,T,r,s): return norm.cdf((np.log(S/K)+(r+s*s/2)*T)/(s*np.sqrt(T)))
def gamma(S,K,T,r,s): d1=(np.log(S/K)+(r+s*s/2)*T)/(s*np.sqrt(T)); return norm.pdf(d1)/(S*s*np.sqrt(T))
S0,K,T,r,s=100,100,1.0,0.04,0.20
# D1: BS vs MC under risk-neutral and under real-world drift
Z=rng.standard_normal(2_000_000)
for lab,drift in [('risk-neutral (drift r=4%)',r),('real-world drift μ=10% (WRONG for pricing)',0.10)]:
    ST=S0*np.exp((drift-s*s/2)*T+s*np.sqrt(T)*Z); pay=np.exp(-r*T)*np.maximum(ST-K,0)
    out.append(f"MC call, {lab}: {pay.mean():.4f} ± {1.96*pay.std()/np.sqrt(len(Z)):.4f}")
c,p=bs(S0,K,T,r,s),bs(S0,K,T,r,s,False)
out.append(f"Black-Scholes call {c:.4f}, put {p:.4f}; parity C−P={c-p:.4f} vs S−Ke^(−rT)={S0-K*np.exp(-r*T):.4f}")
# D2: delta hedging P&L, sell 1 call at implied σi, hedge at σi, realized σr
def hedge_sim(sig_i,sig_r,steps,npaths=4000,T=0.25):
    dt=T/steps; S=np.full(npaths,S0); cash=bs(S0,K,T,r,sig_i)-delta(S0,K,T,r,sig_i)*S0
    d=delta(S0,K,T,r,sig_i)*np.ones(npaths)
    for i in range(1,steps+1):
        S=S*np.exp((0.08-sig_r**2/2)*dt+sig_r*np.sqrt(dt)*rng.standard_normal(npaths))  # real-world drift 8%
        cash*=np.exp(r*dt); tau=T-i*dt
        nd=delta(S,K,tau,r,sig_i) if tau>1e-9 else (S>K).astype(float)
        cash-= (nd-d)*S; d=nd
    pnl=cash+d*S-np.maximum(S-K,0); return pnl
for sr_ in [0.15,0.20,0.25]:
    pnl=hedge_sim(0.20,sr_,63)
    approx=0.5*(0.20**2-sr_**2)*0.25*S0*S0*gamma(S0,K,0.25,r,0.20)*1.0  # rough: Γ at start × T
    out.append(f"short 3m ATM call sold at 20% IV, daily hedge, realized {sr_:.0%}: mean P&L {pnl.mean():+.3f}, std {pnl.std():.3f}  (option premium {bs(S0,K,0.25,r,0.20):.3f})")
for steps in [13,63,252,1008]:
    pnl=hedge_sim(0.20,0.20,steps); out.append(f"  hedge {steps:4d}x over 3m (σi=σr): P&L std {pnl.std():.3f}")
# D3: variance risk premium: VIX (FRED) vs next-21d realized vol of SPY (Yahoo; cross-checked) 
vix=pd.to_numeric(pd.read_csv(f'{R}/data/VIXCLS.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce').dropna()
spy=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True).Close
lr=np.log(spy).diff()
fwd_rv=np.sqrt((lr**2).rolling(21).sum().shift(-21)*252/21)*100
j=pd.concat([vix.rename('vix'),fwd_rv.rename('rv')],axis=1,sort=True).dropna()
vrp=j.vix-j.rv
out.append(f"VIX vs next-21-day realized SPY vol, {j.index[0].date()}→{j.index[-1].date()} (n={len(j)}): mean VIX {j.vix.mean():.1f}, mean realized {j.rv.mean():.1f}, mean gap {vrp.mean():+.1f} vol pts; VIX > realized on {np.mean(vrp>0):.0%} of days; worst gap {vrp.min():+.1f} on {vrp.idxmin().date()}")
var_gap=(j.vix**2-j.rv**2)/100**2
out.append(f"  in variance terms: mean (VIX²−RV²) = {var_gap.mean():+.4f}; median {var_gap.median():+.4f}; 5th pct {var_gap.quantile(.05):+.4f} → short-variance payoff: frequent small gains, rare huge losses (skew {var_gap.skew():.1f})")
txt="\n".join(out); print(txt); open(f'{R}/notes/d_out.txt','w').write(txt)
