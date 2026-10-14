import numpy as np, pandas as pd, sys; sys.path.insert(0,sys.argv[1])
from kf import read_kf
from sklearn.covariance import LedoitWolf
R=sys.argv[1]; out=[]
ind=read_kf(f'{R}/data/30_Industry_Portfolios.csv').dropna()
ff=read_kf(f'{R}/data/F-F_Research_Data_5_Factors_2x3.csv'); 
ff3m=(read_kf(f'{R}/data/F-F_Research_Data_Factors_daily.csv') if False else None)
# monthly RF from 5-factor file starts 1963; use it
rf=ff['RF']; ex=ind.sub(rf,axis=0).dropna()
out.append(f"30 industries (Ken French, value-weighted), monthly excess returns {ex.index[0].date()}→{ex.index[-1].date()}, n={len(ex)}")
W=120; strategies={k:[] for k in ['1/N','sample tangency (MV)','min-variance (sample)','min-variance (Ledoit-Wolf)','inverse-vol (risk-parity-lite)','tangency + LW cov']}
dates=[]
for t in range(W,len(ex)):
    h=ex.iloc[t-W:t].values; nxt=ex.iloc[t].values; n=h.shape[1]; mu=h.mean(0); S=np.cov(h.T); S_lw=LedoitWolf().fit(h).covariance_
    one=np.ones(n)
    def tang(Sig): w=np.linalg.solve(Sig,mu); return w/abs(w.sum()) if abs(w.sum())>1e-8 else w
    def mv(Sig): w=np.linalg.solve(Sig,one); return w/w.sum()
    iv=1/np.sqrt(np.diag(S)); iv/=iv.sum()
    ws={'1/N':one/n,'sample tangency (MV)':tang(S),'min-variance (sample)':mv(S),'min-variance (Ledoit-Wolf)':mv(S_lw),'inverse-vol (risk-parity-lite)':iv,'tangency + LW cov':tang(S_lw)}
    for k,w in ws.items(): strategies[k].append((w@nxt, np.abs(w).sum()))
    dates.append(ex.index[t])
out.append(f"Rolling {W}-month estimation, out-of-sample {dates[0].date()}→{dates[-1].date()} ({len(dates)} months):")
for k,v in strategies.items():
    r=np.array([a for a,b in v]); g=np.mean([b for a,b in v])
    out.append(f"  {k:<32} Sharpe {np.sqrt(12)*r.mean()/r.std():5.2f}  vol {r.std()*np.sqrt(12):6.1%}  worst month {r.min():7.1%}  avg gross leverage {g:5.2f}")
# In-sample tangency Sharpe (the fantasy)
mu=ex.mean().values; S=np.cov(ex.values.T); w=np.linalg.solve(S,mu); r=ex.values@w
out.append(f"  IN-SAMPLE tangency over full period (hindsight): Sharpe {np.sqrt(12)*r.mean()/r.std():.2f}")
# PCA + Marchenko-Pastur on daily industries, last 2y
d=read_kf(f'{R}/data/30_Industry_Portfolios_Daily.csv').dropna().iloc[-504:]
Z=(d-d.mean())/d.std(); C=np.corrcoef(Z.values.T); ev=np.sort(np.linalg.eigvalsh(C))[::-1]
T,N=Z.shape; q=N/T; lam_max=(1+np.sqrt(q))**2
out.append(f"PCA on 30 industries, daily, last {T} days: top eigenvalue {ev[0]:.1f} explains {ev[0]/N:.0%} of variance (the 'market mode'); next {np.round(ev[1:4],2)}")
out.append(f"  Marchenko–Pastur noise edge λ+=(1+√(N/T))² = {lam_max:.2f}; eigenvalues above it: {int((ev>lam_max).sum())} of {N} → only those carry structure, rest indistinguishable from noise")
# random data control
X=np.random.default_rng(0).standard_normal((T,N)); evr=np.sort(np.linalg.eigvalsh(np.corrcoef(X.T)))[::-1]
out.append(f"  control (pure noise, same N,T): largest eigenvalue {evr[0]:.2f}, smallest {evr[-1]:.2f}  (theory λ+={lam_max:.2f}, λ−={(1-np.sqrt(q))**2:.2f})")
txt="\n".join(out); print(txt); open(f'{R}/notes/e_out.txt','w').write(txt)
