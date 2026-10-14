import numpy as np, pandas as pd, sys
from scipy import stats
R=sys.argv[1]; d=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True)
c=d.Close.values; h=d.High.values; n=len(c)
fwd=np.r_[c[5:]/c[:-5]-1,[np.nan]*5]; sma=pd.Series(c).rolling(5).mean().values; a=c>sma
ev=np.r_[False,(h[1:]>h[:-1])&(c[1:]<h[:-1])]
ok=~np.isnan(fwd)&~np.isnan(sma)
for lab,mask in [('all days',ok),('sweep days',ok&ev)]:
    x1,x0=fwd[mask&a],fwd[mask&~a]; t=stats.ttest_ind(x1,x0,equal_var=False).statistic
    print(f"{lab}: above-SMA5 minus below = {100*(x1.mean()-x0.mean()):+.3f}%  t={t:.2f}  n={mask.sum()}")
# non-overlapping: use every 5th day only
idx=np.arange(0,n,5); m=np.zeros(n,bool); m[idx]=True
x1,x0=fwd[ok&a&m],fwd[ok&~a&m]; print(f"all days, non-overlapping: diff={100*(x1.mean()-x0.mean()):+.3f}% t={stats.ttest_ind(x1,x0,equal_var=False).statistic:.2f}")
for per in [('1999','2008'),('2009','2016'),('2017','2026')]:
    s=slice(*[np.searchsorted(d.index, pd.Timestamp(p)) for p in (per[0], str(int(per[1])+1))])
    mk=np.zeros(n,bool); mk[s]=True; x1,x0=fwd[ok&a&mk],fwd[ok&~a&mk]
    print(per, f"diff={100*(x1.mean()-x0.mean()):+.3f}% t={stats.ttest_ind(x1,x0,equal_var=False).statistic:.2f}")
