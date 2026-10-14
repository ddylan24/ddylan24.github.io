import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,sys.argv[1])
from kf import read_kf
import statsmodels.api as sm
from scipy import stats
R=sys.argv[1]; out=[]; rng=np.random.default_rng(17)
# I1 simulation of the Fundamental Law
for N,IC in [(30,0.05),(300,0.05),(3000,0.02),(300,0.02)]:
    irs=[]
    for _ in range(200):
        T=120; pr=[]
        for t in range(T):
            ret=rng.standard_normal(N); sig=IC*ret+np.sqrt(1-IC**2)*rng.standard_normal(N)
            w=(sig-sig.mean()); w/=np.abs(w).sum(); pr.append(w@ret)
        pr=np.array(pr); irs.append(pr.mean()/pr.std()*np.sqrt(12))
    out.append(f"FLAM sim N={N:5d}, IC={IC}: realized annual IR {np.mean(irs):.2f} vs IC·√(N·12) = {IC*np.sqrt(N*12):.2f}")
# real: industry momentum (12-1) on 30 Ken French industries
ind=read_kf(f'{R}/data/30_Industry_Portfolios.csv').dropna()
mom=(1+ind).rolling(11).apply(np.prod,raw=True).shift(2)-1   # months t-12..t-2
nxt=ind
ics=[];lsr=[]
for t in range(13,len(ind)):
    s=mom.iloc[t-1]; f=nxt.iloc[t]
    if s.isna().any(): continue
    ics.append(stats.spearmanr(s,f)[0])
    rk=s.rank(); w=rk-rk.mean(); w/=w.abs().sum(); lsr.append((w*f).sum())
ics=np.array(ics); lsr=pd.Series(lsr)
out.append(f"Industry momentum (30 KF industries, 12-1 month signal, monthly, {len(ics)} months): mean rank IC {ics.mean():.3f}, IC std {ics.std():.3f}, ICIR {ics.mean()/ics.std()*np.sqrt(12):.2f}/yr; rank-weighted long-short Sharpe {lsr.mean()/lsr.std()*np.sqrt(12):.2f}; naive FLAM IC·√(30·12) = {ics.mean()*np.sqrt(360):.2f}")
C=np.corrcoef(ind.values.T); ev=np.linalg.eigvalsh(C); eff=ev.sum()**2/(ev**2).sum()
out.append(f"  effective number of independent industries (participation ratio of correlation eigenvalues) ≈ {eff:.1f} of 30 → breadth is smaller than N")
# I2 factor regressions
ff5=read_kf(f'{R}/data/F-F_Research_Data_5_Factors_2x3.csv'); momf=read_kf(f'{R}/data/F-F_Momentum_Factor.csv'); momf.columns=['MOM']
F=ff5.join(momf,how='inner')
a=pd.read_excel(f'{R}/data/aqr_tsmom.xlsx','TSMOM Factors',header=None)
hr=a.index[a.iloc[:,1].astype(str).str.strip()=='TSMOM'][0]; aq=a.iloc[hr+1:,:2].dropna(); aq.index=pd.to_datetime(aq.iloc[:,0])+pd.offsets.MonthEnd(0); ts=pd.to_numeric(aq.iloc[:,1]).rename('TSMOM')
lsr.index=ind.index[-len(lsr):]
def reg(y,name,cols=['Mkt-RF','SMB','HML','RMW','CMA','MOM']):
    d=pd.concat([y,F[cols]],axis=1).dropna(); m=sm.OLS(d.iloc[:,0],sm.add_constant(d[cols])).fit(cov_type='HAC',cov_kwds={'maxlags':6})
    b=", ".join(f"{c} {m.params[c]:+.2f}(t{m.tvalues[c]:+.1f})" for c in cols)
    return f"{name} {d.index[0].year}–{d.index[-1].year}: alpha {m.params['const']*1200:+.2f}%/yr (t {m.tvalues['const']:+.2f}), R² {m.rsquared:.2f}; {b}"
out.append(reg(ts,'AQR TSMOM'))
out.append(reg(ts['2010':],'AQR TSMOM'))
out.append(reg(lsr,'Industry momentum L/S'))
out.append(reg(lsr,'Industry momentum L/S (FF5 only, no MOM)',['Mkt-RF','SMB','HML','RMW','CMA']))
txt="\n".join(out); print(txt); open(f'{R}/notes/i12_out.txt','w').write(txt)
