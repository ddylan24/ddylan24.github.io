import numpy as np, pandas as pd, yfinance as yf, sys
R=sys.argv[1]
d=yf.download('SPY',start='1999-01-01',end='2026-10-14',progress=False,auto_adjust=True)
d.columns=d.columns.get_level_values(0); d.to_csv(f'{R}/data/spy.csv')
o,h,l,c=d.Open.values,d.High.values,d.Low.values,d.Close.values; n=len(d)
tr=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1]))); tr=np.r_[h[0]-l[0],tr]
atr=pd.Series(tr).rolling(14).mean().values
M,H=1.5,10  # barrier = 1.5 ATR, max 10 days
def barrier(i):
    up,dn=c[i]+M*atr[i],c[i]-M*atr[i]
    for j in range(i+1,min(i+1+H,n)):
        hu,hd=h[j]>=up,l[j]<=dn
        if hu and hd: return 0.0, (c[j]/c[i]-1)   # ambiguous same-bar touch: score 0 label, close return
        if hu: return 1.0,(up/c[i]-1)
        if hd: return -1.0,(dn/c[i]-1)
    j=min(i+H,n-1); return 0.0,(c[j]/c[i]-1)
rows=[]
for i in range(15,n-H-1):
    bear=h[i]>h[i-1] and c[i]<h[i-1]; bull=l[i]<l[i-1] and c[i]>l[i-1]
    lab,ret=barrier(i)
    rows.append(dict(date=d.index[i],bear=bear and not bull,bull=bull and not bear,label=lab,ret=ret))
df=pd.DataFrame(rows).set_index('date')
def stats(x,name):
    x=np.asarray(x); m,s,k=x.mean(),x.std(ddof=1),len(x); se=s/np.sqrt(k)
    return f"{name:<28} n={k:5d}  mean={m*100:+.3f}%  95%CI=[{(m-1.96*se)*100:+.3f}, {(m+1.96*se)*100:+.3f}]  t={m/se:+.2f}"
def block_ci(x,b=10,B=4000,seed=0):
    rng=np.random.default_rng(seed); x=np.asarray(x); k=len(x); nb=int(np.ceil(k/b)); ms=[]
    for _ in range(B):
        starts=rng.integers(0,k-b+1,nb); ms.append(np.concatenate([x[s:s+b] for s in starts])[:k].mean())
    return np.percentile(ms,[2.5,97.5])*100
out=[]
for per,(a,b) in {'1999-2026':('1999','2026'),'2023 only':('2023','2023'),'2022-2025':('2022','2025'),'1999-2008':('1999','2008'),'2009-2016':('2009','2016'),'2017-2026':('2017','2026')}.items():
    s=df.loc[a:b]; out.append(f"--- {per}")
    out.append(stats(s.ret,'ALL days (baseline)'))
    out.append(stats(s[s.bull].ret,'bullish sweep (low swept)'))
    out.append(stats(s[s.bear].ret,'bearish sweep (high swept)'))
    for nm,mask in [('bull',s.bull),('bear',s.bear)]:
        x=s[mask].ret.values; ex=x-s.ret.mean()
        out.append(f"   {nm}: P(upper first)={np.mean(s[mask].label==1):.2f} vs baseline {np.mean(s.label==1):.2f};  excess vs baseline mean={ex.mean()*100:+.3f}%  t={ex.mean()/(ex.std(ddof=1)/np.sqrt(len(ex))):+.2f}")
# overlap-aware CI for full sample bear events
s=df; x=s[s.bear].ret.values
out.append(f"\nfull-sample bear: naive CI {stats(x,'')[-40:]}\n   block-bootstrap 95% CI (blocks of 10 events) = {np.round(block_ci(x),3)}")
r=s.ret.values; ac=[np.corrcoef(r[:-k],r[k:])[0,1] for k in (1,2,5)]
out.append(f"autocorr of 10-day barrier returns across consecutive days lag1/2/5: {np.round(ac,2)}  (overlapping windows => far fewer independent obs)")
txt="\n".join(out); print(txt); open(f'{R}/notes/a1_sweeps_out.txt','w').write(txt)
