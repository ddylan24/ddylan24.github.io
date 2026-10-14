import numpy as np, pandas as pd, sys
R=sys.argv[1]; rng=np.random.default_rng(5)
def mdd(x):
    eq=np.cumprod(1+x); return (1-eq/np.maximum.accumulate(eq)).max()
def stat_idx(n,L):
    starts=rng.integers(0,n,n); newb=rng.random(n)<1/L; newb[0]=True
    idx=np.empty(n,int); cur=0
    for t in range(n):
        cur=starts[t] if newb[t] else (cur+1)%n; idx[t]=cur
    return idx
d=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True); x=d.Close.pct_change().dropna().loc['2000':].values
for L in [40,172]:
    s=[mdd(x[stat_idx(len(x),L)]) for _ in range(600)]; print(f"SPY stationary L={L}: median DD {np.median(s):.1%}, 95th {np.percentile(s,95):.1%}")
# Known-truth test: strategy whose MEAN return depends on a persistent regime (losses cluster)
def sim(n):
    st=0; out=np.empty(n)
    for t in range(n):
        if st==0 and rng.random()<0.01: st=1
        elif st==1 and rng.random()<0.03: st=0
        out[t]=(0.0012 if st==0 else -0.0025)+0.008*rng.standard_normal()
    return out
n=252*10
true=[mdd(sim(n)) for _ in range(600)]
path=sim(n)
iid=[mdd(path[rng.integers(0,n,n)]) for _ in range(600)]
blk=[mdd(path[stat_idx(n,60)]) for _ in range(600)]
f=lambda a:f"median {np.median(a):.1%}, 95th {np.percentile(a,95):.1%}"
print("Regime strategy (losses cluster), 10y daily:")
print("  TRUE drawdown distribution:", f(true))
print("  iid bootstrap of one path: ", f(iid))
print("  stationary bootstrap L=60:  ", f(blk))
print("  lag-1 autocorr of path returns: %.3f, of 20d sums: %.3f"%(np.corrcoef(path[:-1],path[1:])[0,1], pd.Series(path).rolling(20).sum().autocorr(20)))
