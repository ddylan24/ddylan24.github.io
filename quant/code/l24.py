import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore')
from scipy import stats
R=sys.argv[1]; out=[]; rng=np.random.default_rng(21)
r=pd.to_numeric(pd.read_csv(f'{R}/data/DGS3MO.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce').dropna()/100
rw=r.resample('W-FRI').last().dropna(); dt=1/52
def vas(x):
    b,a=np.polyfit(x[:-1],x[1:],1); e=x[1:]-(a+b*x[:-1]); k=-np.log(b)/dt; th=a/(1-b); s=e.std()*np.sqrt(2*k/(1-b*b)); return k,th,s
for a0,b0 in [('1981','2026'),('1981','2007'),('2009','2026')]:
    k,th,s=vas(rw[a0:b0].values); out.append(f"Vasicek fit to 3m T-bill (FRED, weekly) {a0}–{b0}: κ={k:.2f}/yr (half-life {np.log(2)/k:.1f} yrs), long-run mean θ={th:.2%}, σ={s:.2%}; stationary sd {s/np.sqrt(2*k):.2%}; P(r<0) under stationary dist {stats.norm.cdf(0,th,s/np.sqrt(2*k)):.1%}")
# CIR: dr = κ(θ−r)dt + σ√r dW  → regress (Δr)/√r on 1/√r and √r
x=rw['1981':].values; x=np.maximum(x,1e-4); y=np.diff(x)/np.sqrt(x[:-1]); X=np.column_stack([1/np.sqrt(x[:-1]),np.sqrt(x[:-1])])
c,*_=np.linalg.lstsq(X,y,rcond=None); kap=-c[1]/dt; th=c[0]/(kap*dt); sig=np.std(y-X@c)/np.sqrt(dt)
out.append(f"CIR fit 1981–2026: κ={kap:.2f}, θ={th:.2%}, σ={sig:.3f}; Feller 2κθ ≥ σ²? {2*kap*th:.4f} vs {sig**2:.4f} → {'yes (stays positive)' if 2*kap*th>=sig**2 else 'no (can touch zero)'}")
# Vasicek zero-coupon bond: closed form vs MC
k,th,s=0.3,0.04,0.015; r0=0.0425; Tm=5
B=(1-np.exp(-k*Tm))/k; A=np.exp((th-s*s/(2*k*k))*(B-Tm)-s*s*B*B/(4*k)); P_cf=A*np.exp(-B*r0)
n,steps=200000,500; d=Tm/steps; rr=np.full(n,r0); integ=np.zeros(n)
for _ in range(steps): integ+=rr*d; rr+=k*(th-rr)*d+s*np.sqrt(d)*rng.standard_normal(n)
P_mc=np.exp(-integ).mean()
out.append(f"Vasicek 5y zero-coupon bond (κ=.3, θ=4%, σ=1.5%, r0=4.25%): closed form {P_cf:.5f} vs Monte Carlo {P_mc:.5f}; yield {-np.log(P_cf)/Tm:.3%}")
# L4 calendar anomalies on CRSP daily market
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True); m=ff.mkt_rf+ff.rf
df=pd.DataFrame({'r':m}); df['ym']=df.index.to_period('M')
g=df.groupby('ym'); df['dpos']=g.cumcount()+1; df['dneg']=g['r'].transform('count')-df.dpos
tests=[]
def t(mask,lab,data=df):
    a=data.r[mask]; b=data.r[~mask]; tt=stats.ttest_ind(a,b,equal_var=False); tests.append((lab,a.mean()*1e4,b.mean()*1e4,tt.statistic,tt.pvalue,len(a)))
for per,(p0,p1) in {'1926–1989':('1926','1989'),'1990–2026':('1990','2026')}.items():
    d_=df[p0:p1]
    t((d_.dneg==0)|(d_.dpos<=3),f'turn-of-month (last day + first 3), {per}',d_)
    for k_,nm in enumerate(['Mon','Tue','Wed','Thu','Fri']): t(d_.index.dayofweek==k_,f'{nm}, {per}',d_)
    t(d_.index.month.isin([11,12,1,2,3,4]),f'Nov–Apr ("sell in May"), {per}',d_)
    t(d_.index.month==1,f'January, {per}',d_)
M=len(tests)
out.append(f"Calendar effects on CRSP daily market, {M} tests (Welch t vs all other days); Bonferroni p<{0.05/M:.4f}:")
for lab,a,b,tt,p,n_ in tests:
    out.append(f"  {lab:<44} {a:+.1f}bp vs {b:+.1f}bp, t={tt:+.2f}, p={p:.4f}{'  ✓ survives' if p<0.05/M else ''}")
smb=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True).smb
for p0,p1 in [('1926','1989'),('1990','2026')]:
    s_=smb[p0:p1]; j=s_[s_.index.month==1]; o=s_[s_.index.month!=1]; out.append(f"  small-minus-big in January {p0}–{p1}: {j.mean()*1e4*21:+.1f}bp/month vs {o.mean()*1e4*21:+.1f}bp other months (t={stats.ttest_ind(j,o,equal_var=False).statistic:+.2f})")
txt="\n".join(out); print(txt); open(f'{R}/notes/l24_out.txt','w').write(txt)
