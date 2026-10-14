import numpy as np, pandas as pd, sys
from scipy import stats
R=sys.argv[1]; out=[]
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True)
r=np.log1p(ff.mkt_rf+ff.rf); n=len(r); z=(r-r.mean())/r.std()
out.append(f"CRSP market daily log returns {r.index[0].date()}→{r.index[-1].date()}, n={n}: skew {stats.skew(r):.2f}, kurtosis {stats.kurtosis(r,fisher=False):.1f} (normal = 3)")
for k in [3,4,5,7,10]:
    obs=int((abs(z)>k).sum()); exp=n*2*stats.norm.sf(k)
    out.append(f"  |move| > {k:2d}σ: observed {obs:4d}, normal predicts {exp:.3g}  (once every {1/(2*stats.norm.sf(k))/252:.3g} years under normal)")
w=z.abs().idxmax(); out.append(f"  worst day: {w.date()} {np.expm1(r[w]):.1%} = {z[w]:.1f}σ  (normal probability ~ {stats.norm.sf(abs(z[w])):.1e})")
# Student-t fit
df,loc,sc=stats.t.fit(r.values); out.append(f"  Student-t fit: ν={df:.2f} dof")
for k in [5,10]:
    p=2*stats.t.sf(k*r.std(),df,loc,sc); out.append(f"    t predicts |move|>{k}σ: {n*p:.1f} days (observed {int((abs(z)>k).sum())})")
# tail index (Hill estimator) on losses
L=np.sort(-r.values)[::-1]
for kk in [100,250,500]:
    a=1/np.mean(np.log(L[:kk]/L[kk])); out.append(f"  Hill tail index α (top {kk} losses) = {a:.2f}  → moments of order ≥ α infinite in the limit")
# VaR / ES backtest: 1-day 99% normal vs historical vs t, 1990+ rolling 1y window
x=r['1990':].values; dates=r['1990':].index; win=250; br={'normal':0,'hist':0,'t':0}; N=0
for t in range(win,len(x)):
    h=x[t-win:t]; m,s=h.mean(),h.std()
    v_n=m+s*stats.norm.ppf(0.01); v_h=np.percentile(h,1); v_t=m+s*stats.t.ppf(0.01,4)/np.sqrt(4/2)
    br['normal']+=x[t]<v_n; br['hist']+=x[t]<v_h; br['t']+=x[t]<v_t; N+=1
out.append(f"99% 1-day VaR backtest 1991–2026 (rolling 1y window, n={N}, expected breaches {0.01*N:.0f}): " + ", ".join(f"{k} {v}" for k,v in br.items()))
# Kupiec POF test
for k,v in br.items():
    p=0.01; ph=v/N; lr=-2*(np.log((1-p)**(N-v)*p**v)-np.log((1-ph)**(N-v)*ph**v)); out.append(f"  Kupiec LR {k}: {lr:.1f} (reject correct coverage if > 3.84)")
# aggregational gaussianity
for h in [1,5,21,63]:
    rh=r.rolling(h).sum().iloc[::h].dropna(); out.append(f"  horizon {h:2d}d: kurtosis {stats.kurtosis(rh,fisher=False):.1f}, skew {stats.skew(rh):.2f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/b4_out.txt','w').write(txt)
