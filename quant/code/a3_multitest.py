import numpy as np, pandas as pd, sys
from scipy import stats
R=sys.argv[1]; rng=np.random.default_rng(3)
d=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True)
o,h,l,c,v=[d[k].values for k in ['Open','High','Low','Close','Volume']]; n=len(d)
tr=np.r_[h[0]-l[0],np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))]
atr=pd.Series(tr).rolling(14).mean().values
# outcome: 5-day forward return (non-overlap not enforced), event = bearish sweep
fwd=np.r_[c[5:]/c[:-5]-1,[np.nan]*5]
ev=np.zeros(n,bool); ev[1:]=(h[1:]>h[:-1])&(c[1:]<h[:-1])
ret1=np.r_[np.nan,c[1:]/c[:-1]-1]
F=pd.DataFrame(dict(fwd=fwd,ev=ev),index=d.index)
# ~50 context features (all plausible-looking)
feats={}
for w in [5,10,20,50,100,200]:
    sma=pd.Series(c).rolling(w).mean().values; feats[f'above_sma{w}']=c>sma
    feats[f'ret{w}_pos']=np.r_[[np.nan]*w,c[w:]/c[:-w]-1]>0
for w in [5,10,20,60]:
    rv=pd.Series(ret1).rolling(w).std().values; feats[f'rv{w}_high']=rv>pd.Series(rv).rolling(250).median().values
feats['atr_ratio_hi']=(pd.Series(tr).rolling(5).mean()/pd.Series(tr).rolling(50).mean()).values>1.2
for w in [10,20,50]:
    vr=v/pd.Series(v).rolling(w).mean().values; feats[f'vol{w}_hi']=vr>1.5; feats[f'vol{w}_lo']=vr<0.7
wick=(h-np.maximum(o,c))/(h-l+1e-9); feats['upper_wick_big']=wick>0.5; feats['upper_wick_small']=wick<0.2
body=(c-o)/(h-l+1e-9); feats['red_bar']=c<o; feats['strong_red']=body<-0.5
dow=d.index.dayofweek.values
for k,nm in enumerate(['mon','tue','wed','thu','fri']): feats[f'dow_{nm}']=dow==k
m=d.index.month.values
for q,(a,b) in enumerate([(1,3),(4,6),(7,9),(10,12)]): feats[f'q{q+1}']=(m>=a)&(m<=b)
feats['gap_up']=np.r_[False,o[1:]>c[:-1]*1.002]; feats['gap_down']=np.r_[False,o[1:]<c[:-1]*0.998]
feats['inside_prev_range']=np.r_[False,(h[1:]<h[:-1])&(l[1:]>l[:-1])]
for p in [10,20]:
    hh=pd.Series(h).rolling(p).max().values; feats[f'near_{p}d_high']=c>0.99*hh
feats['month_start']=d.index.day.values<=5; feats['month_end']=d.index.day.values>=25
base=F.fwd[F.ev].mean()
res=[]
for k,f in feats.items():
    f=np.asarray(f,bool); m1=F.ev.values&f&~np.isnan(fwd); m0=F.ev.values&~f&~np.isnan(fwd)
    if m1.sum()<30 or m0.sum()<30: continue
    t,p=stats.ttest_ind(fwd[m1],fwd[m0],equal_var=False); res.append((k,m1.sum(),fwd[m1].mean()-fwd[m0].mean(),t,p))
res=pd.DataFrame(res,columns=['feature','n','diff','t','p']).sort_values('p')
M=len(res); res['bonf']=np.minimum(res.p*M,1)
# Holm
ps=res.p.values; holm=np.maximum.accumulate(np.minimum((M-np.arange(M))*ps,1)); res['holm']=holm
# BH
bh=np.minimum.accumulate((ps*M/np.arange(1,M+1))[::-1])[::-1]; res['bh_q']=np.minimum(bh,1)
out=[f"bearish sweep events={F.ev.sum()}, context splits tested M={M}",
     f"naive p<0.05: {np.sum(res.p<0.05)}   |t|>3: {np.sum(abs(res.t)>3)}   Bonferroni<0.05: {np.sum(res.bonf<0.05)}   Holm<0.05: {np.sum(res.holm<0.05)}   BH q<0.10: {np.sum(res.bh_q<0.10)}",
     "top 6:", res.head(6).to_string(index=False,float_format=lambda x:f'{x:.4f}')]
# placebo: shuffle event dates many times, count naive hits -> null distribution
hits=[]
for _ in range(300):
    pe=np.zeros(n,bool); pe[rng.choice(np.arange(200,n-6),F.ev.sum(),replace=False)]=True
    cnt=0
    for k,f in feats.items():
        f=np.asarray(f,bool); m1=pe&f; m0=pe&~f
        if m1.sum()<30 or m0.sum()<30: continue
        cnt+=stats.ttest_ind(fwd[m1],fwd[m0],equal_var=False).pvalue<0.05
    hits.append(cnt)
out.append(f"placebo (random event dates, 300 runs): naive 'significant' splits per run mean={np.mean(hits):.1f}, 95th pct={np.percentile(hits,95):.0f}, max={max(hits)}  (expected under pure independence = {0.05*M:.1f})")
# expected false discoveries
out.append(f"P(at least one false positive at 5% among {M} independent tests) = {1-0.95**M:.3f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/a3_out.txt','w').write(txt)
