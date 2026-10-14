import json, sys, numpy as np, pandas as pd, statsmodels.api as sm
R=sys.argv[1]; out=[]
df=pd.read_csv(f'{R}/data/pm/markets.csv',dtype={'tok':str}); H=json.load(open(f'{R}/data/pm/hist.json'))
df['endts']=pd.to_datetime(df.end,utc=True,errors='coerce',format='mixed'); df['closets']=pd.to_datetime(df.closed,utc=True,errors='coerce',format='mixed')
rec=[]
for _,m in df.iterrows():
    hh=H.get(m.tok) or []
    if len(hh)<3 or pd.isna(m.endts): continue
    cut=m.endts.timestamp()-7*86400
    if pd.notna(m.closets) and m.closets.timestamp()<=cut: continue
    pts=[p for p in hh if p['t']<=cut]
    if pts: rec.append((pts[-1]['p'],m.yes_won,m.event,m.endts,m.vol))
d=pd.DataFrame(rec,columns=['p','y','event','end','vol']); d=d[(d.p>0.01)&(d.p<0.99)]
split=pd.Timestamp('2025-07-01',tz='UTC'); tr=d[d.end<split]; te=d[d.end>=split]
out.append(f"N1 out-of-sample: price 7d before scheduled end; train = markets ending before {split.date()} (n={len(tr)}, {tr.event.nunique()} events), test = after (n={len(te)}, {te.event.nunique()} events)")
def stats_(g,cost):
    mid=g[(g.p>=.05)&(g.p<=.95)]; pay=mid.y/(mid.p+cost)-1   # return per $1 buying YES at price+cost
    ev=pay.groupby(mid.event).mean(); t=ev.mean()/(ev.std()/np.sqrt(len(ev)))
    return len(mid),(mid.y-mid.p).mean(),pay.mean(),t
for lab,g in [('train',tr),('test',te)]:
    for c in [0,0.01,0.03]:
        n,e,r,t=stats_(g,c); out.append(f"  {lab} buy every mid-priced YES at price+{c*100:.0f}¢: n={n}, outcome−price {e:+.3f}, mean return per $1 {r:+.1%}, event-clustered t {t:+.2f}")
# recalibration: fit logit on train, apply to test, compare Brier
X=lambda g: sm.add_constant(np.log(g.p/(1-g.p)))
fit=sm.Logit(tr.y,X(tr)).fit(disp=0); q=fit.predict(X(te))
out.append(f"  calibration fit on train: a={fit.params.iloc[0]:+.2f}, b={fit.params.iloc[1]:.2f}; test Brier raw price {np.mean((te.p-te.y)**2):.4f} vs recalibrated {np.mean((q-te.y)**2):.4f}")
# Kelly-style selective: only buy when recalibrated q exceeds price+cost by margin
for c in [0.01,0.03]:
    sel=te[(q>te.p+c+0.03)&(te.p>=.05)&(te.p<=.95)]
    if len(sel)>5:
        pay=sel.y/(sel.p+c)-1; ev=pay.groupby(sel.event).mean()
        out.append(f"  test, buy YES only where recalibrated prob > price+cost+3¢ (cost {c*100:.0f}¢): n={len(sel)} in {sel.event.nunique()} events, mean return {pay.mean():+.1%}, clustered t {ev.mean()/(ev.std()/np.sqrt(len(ev))):+.2f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/n1_out.txt','w').write(txt)
