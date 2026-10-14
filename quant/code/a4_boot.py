import numpy as np, pandas as pd, sys
R=sys.argv[1]; rng=np.random.default_rng(4)
d=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True); c=d.Close
r=c.pct_change().dropna()
# simple trend strategy: long SPY when 200d SMA rising & price above it, else cash (signal lagged 1 day)
sig=((c>c.rolling(200).mean())).shift(1).reindex(r.index).fillna(False)
strat=(r*sig).loc['2000':]
def mdd(x):
    eq=np.cumprod(1+x); peak=np.maximum.accumulate(eq); return (1-eq/peak).max()
def stationary_idx(n,L):
    idx=np.empty(n,int); i=rng.integers(n)
    for t in range(n):
        if t==0 or rng.random()<1/L: i=rng.integers(n)
        else: i=(i+1)%n
        idx[t]=i
    return idx
out=[]
try:
    from arch.bootstrap import optimal_block_length
    obl=optimal_block_length(np.abs(strat.values)); out.append(f"Politis-White optimal block length on |returns|: stationary={obl['stationary'].iloc[0]:.1f}")
except Exception as e: out.append(f"arch unavailable: {e}")
for name,x in [('SPY buy&hold',r.loc['2000':].values),('SPY 200d trend filter',strat.values)]:
    n=len(x); actual=mdd(x)
    iid=[mdd(x[rng.integers(0,n,n)]) for _ in range(1000)]
    stb=[mdd(x[stationary_idx(n,40)]) for _ in range(1000)]
    sr=np.sqrt(252)*x.mean()/x.std()
    out.append(f"{name}: SR={sr:.2f} actual maxDD={actual:.1%} | iid bootstrap maxDD median={np.median(iid):.1%} 95th={np.percentile(iid,95):.1%} P(DD>=actual)={np.mean(np.array(iid)>=actual):.2f} | stationary(L=40) median={np.median(stb):.1%} 95th={np.percentile(stb,95):.1%} P(DD>=actual)={np.mean(np.array(stb)>=actual):.2f}")
# volatility clustering evidence
ac_r=[r.autocorr(k) for k in (1,5,20)]; ac_a=[r.abs().autocorr(k) for k in (1,5,20)]
out.append(f"SPY autocorr of returns lag1/5/20 = {np.round(ac_r,3)}; of |returns| = {np.round(ac_a,3)}  -> returns ~uncorrelated, volatility strongly persistent")
txt="\n".join(out); print(txt); open(f'{R}/notes/a4_out.txt','w').write(txt)
