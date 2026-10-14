import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,sys.argv[1])
from kf import read_kf
from scipy import stats
R=sys.argv[1]; out=[]
mm=read_kf(f'{R}/data/F-F_Momentum_Factor.csv').iloc[:,0].rename('MOM')
md=read_kf(f'{R}/data/F-F_Momentum_Factor_daily.csv').iloc[:,0].rename('MOM')
ffm=read_kf(f'{R}/data/F-F_Research_Data_5_Factors_2x3.csv')
ffd=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True)
mkt_d=ffd.mkt_rf; mkt_m=(1+mkt_d).resample('ME').prod()-1
m=pd.concat([mm,mkt_m.rename('MKT')],axis=1).dropna()
sr=lambda x:x.mean()/x.std()*np.sqrt(12)
out.append(f"MOM (Ken French UMD) monthly {m.index[0].date()}→{m.index[-1].date()}: mean {m.MOM.mean()*12:.1%}/yr, Sharpe {sr(m.MOM):.2f}, skew {stats.skew(m.MOM):.2f}, kurtosis {stats.kurtosis(m.MOM,fisher=False):.1f}")
w=m.MOM.nsmallest(6); out.append("  worst months: "+", ".join(f"{d.strftime('%Y-%m')} {v:+.1%} (mkt {m.MKT[d]:+.1%})" for d,v in w.items()))
bear=((1+m.MKT).rolling(24).apply(np.prod,raw=True)-1).shift(1)<0
up=m.MKT>0
for lab,mask in [('bear market (past 24m mkt<0) & market up this month',bear&up),('bear market & market down',bear&~up),('normal times',~bear)]:
    x=m.MOM[mask]; out.append(f"  {lab:<52} n={len(x):4d}: mean MOM {x.mean():+.2%}/month")
# market beta of MOM in bear states (short leg = past losers = high beta)
for lab,mask in [('bear',bear),('normal',~bear)]:
    b=np.polyfit(m.MKT[mask],m.MOM[mask],1)[0]; out.append(f"  MOM market beta in {lab} states: {b:+.2f}")
# Barroso–Santa-Clara constant-vol momentum: scale by 12% / realized vol of daily MOM over prior 126 days
rv=md.rolling(126).std()*np.sqrt(252); sc=(0.12/rv).resample('ME').last().shift(1)
cv=(sc.reindex(m.index)*m.MOM).dropna(); base=m.MOM.loc[cv.index]
out.append(f"Constant-vol momentum (scale = 12%/trailing 6m vol, lagged), {cv.index[0].year}–{cv.index[-1].year}: Sharpe {sr(cv):.2f} vs raw {sr(base):.2f}; skew {stats.skew(cv):.2f} vs {stats.skew(base):.2f}; worst month {cv.min():+.1%} vs {base.min():+.1%}; max leverage {sc.max():.1f}x")
for a,b_ in [('1927','1999'),('2000','2026')]:
    out.append(f"  {a}–{b_}: const-vol Sharpe {sr(cv[a:b_]):.2f} vs raw {sr(base[a:b_]):.2f}")
# drawdown of raw MOM 2009
eq=(1+m.MOM).cumprod(); dd=1-eq/eq.cummax(); out.append(f"  raw MOM max drawdown {dd.max():.0%} (trough {dd.idxmax().strftime('%Y-%m')}); 2009 Mar–May cumulative {((1+m.MOM['2009-03':'2009-05']).prod()-1):+.1%}")
txt="\n".join(out); print(txt); open(f'{R}/notes/j1_out.txt','w').write(txt)
