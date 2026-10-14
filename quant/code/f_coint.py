import numpy as np, pandas as pd, yfinance as yf, sys, warnings; warnings.filterwarnings('ignore')
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller
R=sys.argv[1]; rng=np.random.default_rng(12); out=[]
# spurious regression
ts=[];r2=[]
for _ in range(1000):
    a=np.cumsum(rng.standard_normal(500)); b=np.cumsum(rng.standard_normal(500)); m=sm.OLS(a,sm.add_constant(b)).fit(); ts.append(abs(m.tvalues[1])); r2.append(m.rsquared)
out.append(f"Spurious regression (two INDEPENDENT random walks, n=500, 1000 trials): |t|>1.96 in {np.mean(np.array(ts)>1.96):.0%} of trials; median R² {np.median(r2):.2f}")
tick=['KO','PEP','XOM','CVX','EWA','EWC','GLD','GDX','HD','LOW','V','MA']
px=yf.download(tick,start='2006-06-01',end='2026-10-14',progress=False,auto_adjust=True)['Close'].dropna()
px.to_csv(f'{R}/data/pairs.csv')
pairs=[('KO','PEP'),('XOM','CVX'),('EWA','EWC'),('GLD','GDX'),('HD','LOW'),('V','MA')]
lp=np.log(px)
for a,b in pairs:
    full_p=coint(lp[a],lp[b])[1]
    # rolling 2y windows, step 6 months
    idx=lp.index; res=[]
    for s in range(0,len(idx)-504,126):
        w=lp.iloc[s:s+504]; res.append(coint(w[a],w[b])[1]<0.05)
    # formation/trading: form 2y, trade next 1y with z-score rule; roll yearly
    pnl=[]; yrs=sorted(set(idx.year))
    for y in yrs[2:]:
        f=lp[(idx.year>=y-2)&(idx.year<y)]; t=lp[idx.year==y]
        if len(t)<50: continue
        if coint(f[a],f[b])[1]>=0.05: continue
        beta=sm.OLS(f[a],sm.add_constant(f[b])).fit().params
        spr_f=f[a]-beta.iloc[1]*f[b]; mu,sd=spr_f.mean(),spr_f.std()
        z=((t[a]-beta.iloc[1]*t[b])-mu)/sd
        pos=pd.Series(0.0,index=t.index); cur=0
        for i,zz in enumerate(z.values):
            if cur==0 and zz>2: cur=-1
            elif cur==0 and zz<-2: cur=1
            elif cur!=0 and abs(zz)<0.5: cur=0
            elif cur!=0 and abs(zz)>4: cur=0   # stop
            pos.iloc[i]=cur
        dspr=(t[a].diff()-beta.iloc[1]*t[b].diff()).fillna(0)
        pnl.append((pos.shift(1).fillna(0)*dspr).sum())
    out.append(f"{a}/{b}: full-sample Engle–Granger p={full_p:.3f}; cointegrated (p<.05) in {np.mean(res):.0%} of rolling 2y windows; tradable years {len(pnl)}, mean yearly spread P&L {np.mean(pnl) if pnl else 0:+.3f} log-units, positive in {np.mean(np.array(pnl)>0) if pnl else 0:.0%}")
# Kalman filter hedge ratio EWA/EWC
y=lp['EWA'].values; x=lp['EWC'].values; n=len(y)
delta=1e-5; Vw=delta/(1-delta)*np.eye(2); Ve=1e-3
th=np.zeros(2); P=np.zeros((2,2)); betas=[]; errs=[]; Qs=[]
for t in range(n):
    F=np.array([1,x[t]]); P=P+Vw; yhat=F@th; e=y[t]-yhat; Q=F@P@F+Ve; K=P@F/Q
    th=th+K*e; P=P-np.outer(K,F)@P; betas.append(th[1]); errs.append(e); Qs.append(Q)
betas=np.array(betas); z=np.array(errs)/np.sqrt(Qs)
out.append(f"Kalman hedge ratio EWA~EWC: β ranged {betas[500:].min():.2f}–{betas[500:].max():.2f} (static OLS β={sm.OLS(y,sm.add_constant(x)).fit().params[1]:.2f}); normalized innovations std {z[500:].std():.2f} (≈1 if model well-specified)")
txt="\n".join(out); print(txt); open(f'{R}/notes/f_out.txt','w').write(txt)
