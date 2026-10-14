import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,sys.argv[1])
from kf import read_kf
import statsmodels.api as sm
R=sys.argv[1]; out=[]
ff=read_kf(f'{R}/data/F-F_Research_Data_5_Factors_2x3.csv'); mkt,rf=ff['Mkt-RF'],ff['RF']
for name,f in [('BETA',f'{R}/data/Portfolios_Formed_on_BETA.csv'),('VAR',f'{R}/data/Portfolios_Formed_on_VAR.csv')]:
    p=read_kf(f).dropna(); dec=[c for c in p.columns if c.startswith(('Lo 10','Dec','Hi 10'))]
    ex=p[dec].sub(rf,axis=0).dropna(); m=mkt.loc[ex.index]
    out.append(f"{name}-sorted deciles (Ken French/CRSP, value-weighted) {ex.index[0].year}–{ex.index[-1].year}:")
    rows=[]
    for c in dec:
        b=sm.OLS(ex[c],sm.add_constant(m)).fit(); rows.append((c,ex[c].mean()*12,b.params.iloc[1],b.params['const']*12,ex[c].mean()/ex[c].std()*np.sqrt(12)))
    for c,mu,beta,al,s in [rows[0],rows[4],rows[-1]]:
        out.append(f"  {c:<6}: excess {mu:5.1%}/yr, realized β {beta:.2f}, CAPM α {al:+.1%}/yr, Sharpe {s:.2f}")
    mus=np.array([r[1] for r in rows]); bs=np.array([r[2] for r in rows])
    slope=np.polyfit(bs,mus,1)[0]; out.append(f"  slope of avg excess return on beta across deciles: {slope:.1%} per unit β (CAPM predicts market premium {m.mean()*12:.1%})")
    if name=='BETA':
        lo,hi=ex[dec[0]],ex[dec[-1]]; blo,bhi=rows[0][2],rows[-1][2]
        bab=lo/blo-hi/bhi; out.append(f"  BAB-style (long low-β levered to β=1, short high-β scaled to β=1): {bab.mean()*12:+.1%}/yr, Sharpe {bab.mean()/bab.std()*np.sqrt(12):.2f}, t {bab.mean()/bab.std()*np.sqrt(len(bab)):.2f}")
# J4 James–Stein shrinkage of Sharpe ratios: 30 industries, estimate on 1927–1976, evaluate on 1977–2026
ind=read_kf(f'{R}/data/30_Industry_Portfolios.csv').dropna()
a,b_=ind[:'1976'],ind['1977':]
s1=a.mean()/a.std()*np.sqrt(12); s2=b_.mean()/b_.std()*np.sqrt(12); yrs=len(a)/12
noise=1/yrs; v=s1.var(); B=max(0,1-noise/v); js=s1.mean()+B*(s1-s1.mean())
mse=lambda e:np.mean((e-s2)**2)
out.append(f"James–Stein on 30 industries: first-half Sharpe dispersion var {v:.4f} vs pure sampling noise 1/years={noise:.4f} → keep {B:.0%} of each industry's deviation from the average")
out.append(f"  predicting 1977–2026 Sharpe: raw first-half estimate MSE {mse(s1):.4f}; grand mean only {mse(pd.Series(s1.mean(),index=s1.index)):.4f}; James–Stein {mse(js):.4f}; corr(first half, second half) {np.corrcoef(s1,s2)[0,1]:.2f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/j34_out.txt','w').write(txt)
