import numpy as np
from scipy.stats import norm
rng=np.random.default_rng(7)

# 1) Expected max Sharpe of N zero-skill strategies (Bailey & Lopez de Prado eq.)
def exp_max_sr(n, years):
    emc=0.5772156649; sd=1/np.sqrt(years)   # std of annualized SR estimate under null
    z=(1-emc)*norm.ppf(1-1/n)+emc*norm.ppf(1-1/(n*np.e))
    return sd*z
print("Expected best annual Sharpe from pure noise (5y data):")
for n in [10,100,1000,10000]: print(f"  {n:>6} tries -> {exp_max_sr(n,5):.2f}")

# 2) Overfit a moving-average crossover on a random walk (no edge exists)
T=252*10; r=rng.normal(0,0.01,T); p=100*np.exp(np.cumsum(r))
def sharpe(x): return np.sqrt(252)*x.mean()/x.std() if x.std()>0 else 0
def ma_strat(p,r,f,s):
    pos=np.zeros(len(p))
    fm=np.convolve(p,np.ones(f)/f,'full')[:len(p)]; sm=np.convolve(p,np.ones(s)/s,'full')[:len(p)]
    pos[s:]=np.where(fm[s:]>sm[s:],1,-1)
    return pos[:-1]*r[1:]   # trade next bar: no look-ahead
half=T//2
best=None
for f in range(2,50,2):
    for s in range(f+5,200,5):
        ins=sharpe(ma_strat(p[:half],r[:half],f,s))
        if best is None or ins>best[0]: best=(ins,f,s)
ins,f,s=best
full=ma_strat(p,r,f,s); oos=sharpe(full[half:])
print(f"\nMA crossover on a RANDOM WALK: tried {len(range(2,50,2))*0+sum(1 for f in range(2,50,2) for s in range(f+5,200,5))} combos")
print(f"  best in-sample Sharpe {ins:.2f} (fast={f}, slow={s}); out-of-sample Sharpe {oos:.2f}")

# 3) Kelly: growth vs bet fraction, asset with 8% excess return, 20% vol
mu,sig=0.08,0.20; fk=mu/sig**2
print(f"\nKelly fraction f*=mu/sigma^2 = {fk:.1f}x leverage")
for k in [0.25,0.5,1,1.5,2,2.5]:
    f=k*fk; g=f*mu-0.5*(f*sig)**2
    print(f"  {k:>4}x Kelly: growth {g*100:5.2f}%/yr, vol {f*sig*100:5.1f}%")

# 4) Trading costs eat a small edge: 55% win rate, 1:1 payoff, cost per trade
for c in [0,0.05,0.1,0.15]:
    ev=0.55*1-0.45*1-2*c  # in units of R, cost both ways as fraction of R
    print(f"  cost {c:.2f}R per side -> EV per trade {ev:+.2f}R")
