import json, sys, numpy as np, pandas as pd
from scipy import stats
R=sys.argv[1]; out=[]
df=pd.read_csv(f'{R}/data/pm/markets.csv',dtype={'tok':str}); H=json.load(open(f'{R}/data/pm/hist.json'))
df['endts']=pd.to_datetime(df.closed.fillna(df.end),utc=True,errors='coerce',format='mixed')
out.append(f"Polymarket resolved binary markets, volume ≥ $50k, top {len(df)} by volume (gamma + CLOB APIs); date range {df.endts.min().date()} → {df.endts.max().date()}; YES won {df.yes_won.mean():.1%}")
bins=[0,.05,.10,.20,.30,.40,.50,.60,.70,.80,.90,.95,1.0001]
for h in [1,7,30]:
    rec=[]
    for _,m in df.iterrows():
        hh=H.get(m.tok) or []
        if len(hh)<3 or pd.isna(m.endts): continue
        cut=m.endts.timestamp()-h*86400
        pts=[p for p in hh if p['t']<=cut]
        if not pts: continue
        rec.append((pts[-1]['p'],m.yes_won,m.event))
    d=pd.DataFrame(rec,columns=['p','y','event']); d=d[(d.p>0)&(d.p<1)]
    brier=np.mean((d.p-d.y)**2); base=np.mean((d.y.mean()-d.y)**2)
    out.append(f"\n{h} day(s) before resolution: n={len(d)} markets in {d.event.nunique()} events; Brier {brier:.4f} vs base-rate forecast {base:.4f} (skill {1-brier/base:.0%})")
    d['bin']=pd.cut(d.p,bins,right=False)
    for b,g in d.groupby('bin',observed=True):
        if len(g)<5: continue
        f=g.y.mean(); lo,hi=stats.beta.ppf([.025,.975],g.y.sum()+.5,len(g)-g.y.sum()+.5)
        out.append(f"  price {b.left:.2f}–{min(b.right,1):.2f}: n={len(g):4d}, avg price {g.p.mean():.3f}, won {f:.3f} [{lo:.3f},{hi:.3f}]  EV of $1 YES {f/g.p.mean()-1:+.0%}")
    lng=d[d.p<0.10]; fav=d[d.p>0.90]
    out.append(f"  longshots (<10¢): avg price {lng.p.mean():.3f} vs win rate {lng.y.mean():.3f}; favorites (>90¢): avg price {fav.p.mean():.3f} vs win rate {fav.y.mean():.3f}")
    d.to_csv(f'{R}/data/pm/calib_h{h}.csv',index=False)
txt="\n".join(out); print(txt); open(f'{R}/notes/p2_out.txt','w').write(txt)
