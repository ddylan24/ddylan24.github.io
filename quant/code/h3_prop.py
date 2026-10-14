import numpy as np, sys
from scipy.optimize import brentq
R=sys.argv[1]; rng=np.random.default_rng(14); out=[]
a,b=0.06,0.04   # profit target +6%, max loss -4% (of account)
def p_pass(mu,sig): 
    if abs(mu)<1e-12: return b/(a+b)
    k=2*mu/sig**2; return (1-np.exp(k*b))/(np.exp(-k*a)-np.exp(k*b))
def mc(mu,sig,trailing=False,days=2000,n=20000):
    x=np.zeros(n); peak=np.zeros(n); alive=np.ones(n,bool); passed=np.zeros(n,bool); t=np.zeros(n)
    for d in range(days):
        x[alive]+=mu+sig*rng.standard_normal(alive.sum()); t[alive]+=1
        peak=np.maximum(peak,x); floor=np.minimum(peak-b,0) if trailing else -b   # trailing EOD, locks at start balance
        win=alive&(x>=a); lose=alive&(x<=floor); passed|=win; alive&=~(win|lose)
        if not alive.any(): break
    return passed.mean(), np.median(t[passed]) if passed.any() else np.nan
out.append("Barrier formula P(hit +a before −b) for drift μ, vol σ per day: (1−e^{2μb/σ²})/(e^{−2μa/σ²}−e^{2μb/σ²}); μ=0 ⇒ b/(a+b)")
for lab,mu,sig in [('no edge',0,0.01),('no edge, 3x size',0,0.03),('costs only (−0.05%/day)',-0.0005,0.01),('costs only, 3x size',-0.0015,0.03),
                   ('Sharpe 1 strategy, 1% daily vol',0.01/np.sqrt(252)*1.0,0.01),('Sharpe 2, 1% daily vol',0.01/np.sqrt(252)*2,0.01),('Sharpe 2, 0.5% daily vol',0.005/np.sqrt(252)*2,0.005)]:
    f=p_pass(mu,sig); m,tm=mc(mu,sig); m2,_=mc(mu,sig,True)
    out.append(f"  {lab:<34} formula {f:.2f} | MC static {m:.2f} (median {tm:.0f} days) | MC trailing-DD {m2:.2f}")
# what Sharpe gives 93% (static) at 1% daily vol? at 0.5%?
for sig in [0.01,0.005,0.0025]:
    mu=brentq(lambda m:p_pass(m,sig)-0.93,1e-7,0.05); out.append(f"  need annual Sharpe {mu/sig*np.sqrt(252):.2f} for 93% pass at {sig:.2%} daily vol (static DD) — median days to pass ≈ {mc(mu,sig)[1]:.0f}")
out.append("  note: with true Sharpe S, P depends only on k·b = 2μb/σ² ⇒ lower vol raises pass prob for a positive edge (but slower); for a NEGATIVE edge, bigger size (more vol) RAISES pass prob — 'bold play' (Dubins–Savage)")
# EV of a challenge: fee F, payout if pass; assume $50k acct, fee $150, pass → expected withdrawals W
for P in [0.40,0.60,0.93]:
    out.append(f"  pass prob {P:.0%}: break-even expected payout per pass = fee/P = ${150/P:,.0f} per $150 attempt")
txt="\n".join(out); print(txt); open(f'{R}/notes/h3_out.txt','w').write(txt)
