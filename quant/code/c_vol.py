import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore')
from arch import arch_model
from scipy import stats
R=sys.argv[1]; out=[]
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True)
r=np.log1p(ff.mkt_rf+ff.rf)*100   # percent log returns, CRSP market
# --- GARCH(1,1) full sample
g=arch_model(r,mean='Constant',vol='GARCH',p=1,q=1,dist='t').fit(disp='off')
w,a,b=g.params['omega'],g.params['alpha[1]'],g.params['beta[1]']; nu=g.params['nu']
out.append(f"GARCH(1,1)-t on CRSP market 1926–2026: ω={w:.4f} α={a:.4f} β={b:.4f} ν={nu:.1f}; persistence α+β={a+b:.4f}; shock half-life={np.log(0.5)/np.log(a+b):.0f} days; long-run vol={np.sqrt(w/(1-a-b)*252):.1f}%/yr")
z=g.std_resid.dropna(); out.append(f"kurtosis raw returns {stats.kurtosis(r,fisher=False):.1f} → GARCH standardized residuals {stats.kurtosis(z,fisher=False):.1f}; |z|>5: {int((abs(z)>5).sum())} days (raw had 104)")
# --- rolling VaR backtest 1991–2026 with EWMA & GARCH (refit yearly, one-step forecasts)
x=r['1990':]; N=0; br={'EWMA(0.94) normal':0,'GARCH-t':0}
lam=0.94; v=x[:250].var()
ewma_sig=[]
for t in range(len(x)):
    ewma_sig.append(np.sqrt(v)); v=lam*v+(1-lam)*x.iloc[t]**2
ewma_sig=pd.Series(ewma_sig,index=x.index)
# garch: fit on expanding window each year-end, forecast through next year via filtering
gsig=pd.Series(index=x.index,dtype=float)
for yr in range(1991,2027):
    hist=r[:f'{yr-1}-12-31']; m=arch_model(hist,mean='Constant',vol='GARCH',p=1,q=1,dist='t').fit(disp='off')
    full=arch_model(r[:f'{yr}-12-31'],mean='Constant',vol='GARCH',p=1,q=1,dist='t').fix(m.params)
    cv=full.conditional_volatility[f'{yr}']; gsig[cv.index]=cv
    nu_y=m.params['nu']; mu_y=m.params['mu']
    q=stats.t.ppf(0.01,nu_y)*np.sqrt((nu_y-2)/nu_y)
    seg=x[f'{yr}']; br['GARCH-t']+=int((seg< mu_y+q*cv.reindex(seg.index)).sum())
xs=x['1991':]; N=len(xs)
br['EWMA(0.94) normal']=int((xs< -2.326*ewma_sig['1991':]).sum())
out.append(f"99% VaR backtest 1991–2026 (n={N}, expect {0.01*N:.0f}): "+", ".join(f"{k}: {v}" for k,v in br.items()))
for k,vv in br.items():
    p=0.01; ph=vv/N; lr=-2*((N-vv)*np.log(1-p)+vv*np.log(p)-(N-vv)*np.log(1-ph)-vv*np.log(ph)); out.append(f"   Kupiec {k}: {lr:.1f}")
# --- Moreira–Muir replication (monthly, CRSP market excess)
ex=ff.mkt_rf; rvm=(ex**2).resample('ME').sum(); exm=(1+ex).resample('ME').prod()-1
w_=1/rvm.shift(1); vm=w_*exm; vm=vm.dropna(); exm2=exm.loc[vm.index]
c=exm2.std()/vm.std(); vm=c*vm
import statsmodels.api as sm
reg=sm.OLS(vm,sm.add_constant(exm2)).fit(cov_type='HAC',cov_kwds={'maxlags':6})
sr=lambda s: s.mean()/s.std()*np.sqrt(12)
out.append(f"Moreira–Muir vol-managed market 1926–2026 (monthly, weight ∝ 1/last month's realized variance, scaled to same vol): Sharpe {sr(vm):.2f} vs market {sr(exm2):.2f}; alpha {reg.params['const']*1200:.2f}%/yr (t={reg.tvalues['const']:.2f}), beta {reg.params.iloc[1]:.2f}")
for a0,b0 in [('1926','1999'),('2000','2026')]:
    v2,e2=vm[a0:b0],exm2[a0:b0]; rg=sm.OLS(v2,sm.add_constant(e2)).fit(cov_type='HAC',cov_kwds={'maxlags':6})
    out.append(f"   {a0}–{b0}: Sharpe {sr(v2):.2f} vs {sr(e2):.2f}, alpha t={rg.tvalues['const']:.2f}; max leverage used {(c*w_.loc[v2.index]).max():.1f}x, median {(c*w_.loc[v2.index]).median():.2f}x")
txt="\n".join(out); print(txt); open(f'{R}/notes/c_vol_out.txt','w').write(txt)
