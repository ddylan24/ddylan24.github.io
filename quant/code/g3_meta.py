import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings('ignore')
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score
R=sys.argv[1]; out=[]; rng=np.random.default_rng(16)
spy=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True)
c=spy.Close; h=spy.High; l=spy.Low; r=np.log(c).diff(); vol=r.rolling(20).std()
vix=pd.to_numeric(pd.read_csv(f'{R}/data/VIXCLS.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce').reindex(c.index).ffill()
# primary model: CUSUM events (k=2) in BOTH directions -> bet on reversal (side = -direction)
sp=sn=0; ev=[]
for t in range(201,len(r)):
    hh=2*vol.iloc[t-1]; sp=max(0,sp+r.iloc[t]); sn=min(0,sn+r.iloc[t])
    if sp>hh: ev.append((t,-1)); sp=0
    elif sn<-hh: ev.append((t,1)); sn=0
H=10; rows=[]
for t,side in ev:
    if t+H>=len(c): break
    up=c.iloc[t]*(1+1.5*vol.iloc[t]*np.sqrt(H)); dn=c.iloc[t]*(1-1.5*vol.iloc[t]*np.sqrt(H)); end=t+H; lab=None
    for j in range(t+1,t+H+1):
        hu=h.iloc[j]>=up; hd=l.iloc[j]<=dn
        if hu or hd:
            ret=((up if hu and not hd else dn if hd and not hu else c.iloc[j])/c.iloc[t]-1); end=j; break
    else: ret=c.iloc[t+H]/c.iloc[t]-1
    pr=side*ret
    rows.append(dict(t=t,date=c.index[t],end=c.index[end],side=side,ret=pr,y=int(pr>0),
        vol_ratio=vol.iloc[t]/vol.iloc[t-60:t].mean(),dist200=c.iloc[t]/c.iloc[t-200:t].mean()-1,
        ret5=c.iloc[t]/c.iloc[t-5]-1,ret20=c.iloc[t]/c.iloc[t-20]-1,vix=vix.iloc[t],vix_chg=vix.iloc[t]/vix.iloc[t-5]-1,
        side_f=side,dow=c.index[t].dayofweek))
E=pd.DataFrame(rows).dropna(); X=E[['vol_ratio','dist200','ret5','ret20','vix','vix_chg','side_f','dow']].values; y=E.y.values
out.append(f"Primary model: SPY CUSUM(k=2) events, bet on reversal; triple barrier ±1.5σ√10, 10-day limit. Events {len(E)}, primary hit rate {y.mean():.1%}, mean return/trade {E.ret.mean():+.2%}")
# overlap stat
ov=np.mean([(E.end.iloc[i]>E.date.iloc[i+1]) for i in range(len(E)-1)]); out.append(f"  share of events whose label window overlaps the next event: {ov:.0%}")
rf=lambda: RandomForestClassifier(n_estimators=300,min_samples_leaf=20,max_features=3,random_state=0,n_jobs=-1)
# leakage demo: shuffled KFold vs purged+embargoed KFold
def purged_cv(shuffle):
    aucs=[]
    kf=KFold(5,shuffle=shuffle,random_state=0 if shuffle else None)
    for tr,te in kf.split(X):
        if not shuffle:
            t0,t1=E.date.iloc[te[0]],E.end.iloc[te].max()
            emb=t1+pd.Timedelta(days=14)
            keep=[i for i in tr if (E.end.iloc[i]<t0) or (E.date.iloc[i]>emb)]; tr=np.array(keep)
        m=rf().fit(X[tr],y[tr]); aucs.append(roc_auc_score(y[te],m.predict_proba(X[te])[:,1]))
    return np.mean(aucs)
# add a leaky feature to make leakage visible: 'future-ish' none; instead show with a near-duplicate-rich setup
out.append(f"  CV AUC, shuffled K-fold (no purge): {purged_cv(True):.3f} | purged+embargoed sequential K-fold: {purged_cv(False):.3f}")
# walk-forward meta-labeling
preds=pd.Series(np.nan,index=E.index)
for yr in range(2008,2027):
    te=E.date.dt.year==yr
    tr=(E.end<pd.Timestamp(f'{yr}-01-01'))
    if te.sum()==0 or tr.sum()<200: continue
    m=rf().fit(X[tr.values],y[tr.values]); preds[te]=m.predict_proba(X[te.values])[:,1]
W=E.loc[preds.notna()].copy(); W['p']=preds.dropna()
auc=roc_auc_score(W.y,W.p)
def summ(d,lab): return f"  {lab:<36} trades {len(d):4d}, hit {d.y.mean():.1%}, mean {d.ret.mean():+.2%}, per-trade Sharpe {d.ret.mean()/d.ret.std():.3f}"
out.append(f"Walk-forward 2008–2026 (train only on events whose labels ended before each test year), out-of-sample AUC {auc:.3f}")
out.append(summ(W,'primary: take every event'))
out.append(summ(W[W.p>0.5],'meta-filtered: take if P>0.5'))
out.append(summ(W[W.p>W.p.median()],'meta-filtered: top half by P'))
sized=W.ret*(2*W.p-1).clip(lower=0); out.append(f"  meta-sized (bet ∝ 2p−1): mean {sized.mean():+.3%}, per-trade Sharpe {sized.mean()/sized.std():.3f}")
for s in [1,-1]:
    d=W[W.side==s]; out.append(f"  by side {'long after down-move' if s==1 else 'short after up-move'}: primary hit {d.y.mean():.1%} mean {d.ret.mean():+.2%} (n={len(d)})")
m=rf().fit(X,y); imp=pd.Series(m.feature_importances_,index=['vol_ratio','dist200','ret5','ret20','vix','vix_chg','side','dow']).sort_values(ascending=False)
out.append("  feature importance (full fit, MDI): "+", ".join(f"{k} {v:.2f}" for k,v in imp.items()))
txt="\n".join(out); print(txt); open(f'{R}/notes/g3_out.txt','w').write(txt)
f=W[W.p>0.5]; out2=[f"meta-filtered trades that are longs: {np.mean(f.side==1):.0%} (all events: {np.mean(W.side==1):.0%})"]
L=W[W.side==1]; out2.append(f"simple rule 'longs only': trades {len(L)}, hit {L.y.mean():.1%}, mean {L.ret.mean():+.2%}, per-trade Sharpe {L.ret.mean()/L.ret.std():.3f}")
Lm=L[L.p>L.p.median()]; Ll=L[L.p<=L.p.median()]
out2.append(f"within longs: top-half P hit {Lm.y.mean():.1%} mean {Lm.ret.mean():+.2%} | bottom-half hit {Ll.y.mean():.1%} mean {Ll.ret.mean():+.2%}")
print("\n".join(out2)); open(f'{R}/notes/g3_out.txt','a').write("\n"+"\n".join(out2))
