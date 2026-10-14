import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore')
from hmmlearn.hmm import GaussianHMM
from scipy.stats import norm
R=sys.argv[1]; out=[]
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True)
mkt=ff.mkt_rf+ff.rf; rf=ff.rf; x=np.log1p(mkt)
train=x[:'1999']; test=x['2000':]
best=None
for seed in range(8):
    m=GaussianHMM(2,covariance_type='full',n_iter=300,random_state=seed).fit(train.values.reshape(-1,1))
    ll=m.score(train.values.reshape(-1,1)); best=(ll,m) if best is None or ll>best[0] else best
m=best[1]; mu=m.means_.ravel(); sd=np.sqrt(m.covars_.ravel()); calm=int(np.argmin(sd)); A=m.transmat_
out.append(f"HMM fit on CRSP market (Ken French) 1926–1999 daily, n={len(train)}")
for s in (calm,1-calm):
    out.append(f"  state {'CALM' if s==calm else 'TURBULENT'}: mean {mu[s]*252:+.1%}/yr, vol {sd[s]*np.sqrt(252):.1%}/yr, stay prob {A[s,s]:.4f} → expected duration {1/(1-A[s,s]):.0f} days")
pi=np.linalg.eig(A.T)[1][:,np.argmin(abs(np.linalg.eig(A.T)[0]-1))].real; pi/=pi.sum()
out.append(f"  stationary distribution: calm {pi[calm]:.1%}, turbulent {pi[1-calm]:.1%}")
# forward filter (real-time) with frozen parameters on test set
def forward(obs):
    p=m.startprob_.copy(); res=[]
    for o in obs:
        lik=norm.pdf(o,mu,sd); p=lik*(p if not res else A.T@res[-1]); p/=p.sum(); res.append(p)
    return np.array(res)
filt=forward(test.values)[:,calm]
smooth=m.predict_proba(test.values.reshape(-1,1))[:,calm]
ex=(mkt-rf)['2000':]; r=mkt['2000':]; rft=rf['2000':]
def perf(w,lab):
    ret=w*r+(1-w)*rft; e=ret-rft; sr=np.sqrt(252)*e.mean()/e.std(); eq=(1+ret).cumprod(); dd=(1-eq/eq.cummax()).max()
    cagr=eq.iloc[-1]**(252/len(eq))-1; out.append(f"  {lab:<44} CAGR {cagr:6.1%}  Sharpe {sr:4.2f}  maxDD {dd:5.1%}  time invested {w.mean():.0%}")
out.append("Out-of-sample 2000–2026 (params frozen from 1926–1999); signal applied NEXT day:")
perf(pd.Series(1.0,index=r.index),'buy & hold market')
perf(pd.Series((filt>0.5).astype(float),index=r.index).shift(1).fillna(1),'HMM filtered P(calm)>0.5 (real-time)')
perf(pd.Series((smooth>0.5).astype(float),index=r.index).shift(1).fillna(1),'HMM SMOOTHED (uses future data = cheating)')
# vol-scaled alternative: weight = min(1, target/ filtered-state vol)
fv=np.sqrt(filt*sd[calm]**2+(1-filt)*sd[1-calm]**2)*np.sqrt(252)
perf(pd.Series(np.minimum(1,0.15/fv),index=r.index).shift(1).fillna(1),'HMM vol-scaled to 15% (cap 1x)')
# regime agreement
out.append(f"  filtered vs smoothed regime agree {np.mean((filt>0.5)==(smooth>0.5)):.1%} of days; filtered switches {np.sum(np.diff(filt>0.5)!=0)}x, smoothed {np.sum(np.diff(smooth>0.5)!=0)}x")
# 2008 & 2020 detection lag
for a,b in [('2008-09-01','2008-12-31'),('2020-02-15','2020-04-30')]:
    s=pd.Series(filt,index=test.index)[a:b]; first=s[s<0.5].index[:1]
    out.append(f"  {a[:7]}: filter first flagged turbulent on {first[0].date() if len(first) else 'never'}")
txt="\n".join(out); print(txt); open(f'{R}/notes/b3_out.txt','w').write(txt)
