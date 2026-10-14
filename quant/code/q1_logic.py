import json, sys, urllib.request, re, numpy as np, pandas as pd
R=sys.argv[1]; out=[]
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r: return json.load(r)
ev=[]
for off in range(0,600,100): ev+=get(f"https://gamma-api.polymarket.com/events?closed=false&active=true&limit=100&offset={off}&order=volume&ascending=false")
E={e['title']:e for e in ev}
def tab(title):
    rows=[]
    for m in E[title]['markets']:
        if not m.get('active') or m.get('closed') or m.get('bestAsk') is None: continue
        rows.append(dict(name=(m.get('groupItemTitle') or '').strip(),bid=float(m.get('bestBid') or 0),ask=float(m.get('bestAsk') or 0)))
    d=pd.DataFrame(rows); d['key']=d.name.str.lower().str.replace(r'[^a-z]','',regex=True); return d
W=tab('Presidential Election Winner 2028'); D=tab('Democratic Presidential Nominee 2028'); Rp=tab('Republican Presidential Nominee 2028'); P=tab('Which party wins 2028 US Presidential Election?')
out.append(f"Q1 logical consistency, live Polymarket 2026-10-14: winner market {len(W)} candidates, Dem nominee {len(D)}, GOP nominee {len(Rp)}, party market {len(P)} outcomes")
out.append("  party market: "+", ".join(f"{r['name']} {r.bid:.3f}/{r.ask:.3f}" for _,r in P.iterrows() if r.ask>0.005))
# constraint 1: P(win presidency) <= P(win own party's nomination) (ignoring third-party/independent paths)
viol=[]
for nomtab,party in [(D,'Democratic'),(Rp,'Republican')]:
    M=W.merge(nomtab,on='key',suffixes=('_w','_n'))
    M=M[(M.ask_w>0)&(M.ask_n>0)]
    M['gap']=M.bid_w-M.ask_n      # executable: sell winner YES at bid, buy nominee YES at ask → riskless if gap>0 (winner ⇒ nominee)
    M['ratio']=((M.bid_w+M.ask_w)/2)/((M.bid_n+M.ask_n)/2)
    for _,r in M.sort_values('ratio',ascending=False).head(4).iterrows():
        out.append(f"  {party[:3]} {r.name_w[:24]:<24} P(win) {(r.bid_w+r.ask_w)/2:.3f}  P(nominee) {(r.bid_n+r.ask_n)/2:.3f}  implied P(win | nominated) {r.ratio:.2f}")
    v=M[M.gap>0]; viol+= list(v.name_w)
    out.append(f"  {party}: {len(M)} matched; executable violations (winner bid > nominee ask): {len(v)}{' → '+', '.join(f'{a} +{g*100:.1f}¢' for a,g in zip(v.name_w,v.gap)) if len(v) else ''}")
# constraint 2: sum over candidates of each party in winner market ≈ party market price
for nomtab,label in [(D,'Democratic'),(Rp,'Republican')]:
    ks=set(nomtab.key); s=W[W.key.isin(ks)]; mid=((s.bid+s.ask)/2).sum()
    pm=P[P.name.str.contains(label[:5],case=False)]
    pp=((pm.bid+pm.ask)/2).iloc[0] if len(pm) else np.nan
    out.append(f"  Σ winner-market mids over {label} names = {mid:.3f} vs party market {pp:.3f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/q1_out.txt','w').write(txt)
# diagnostics: does the winner market cover everyone? overlap between nominee lists?
W['mid']=(W.bid+W.ask)/2
both=set(D.key)&set(Rp.key); unm=W[~W.key.isin(set(D.key)|set(Rp.key))]
out2=[f"  Σ all winner-market mids = {W.mid.sum():.3f} (Σ asks {W.ask.sum():.3f}, Σ bids {W.bid.sum():.3f}); names in both nominee lists: {len(both)}",
      f"  winner names in neither nominee list: {len(unm)}, Σ mid {unm.mid.sum():.3f}: "+", ".join(f'{a} {m:.3f}' for a,m in unm.sort_values('mid',ascending=False).head(6)[['name','mid']].values),
      "  top winner mids: "+", ".join(f'{a} {m:.3f}' for a,m in W.sort_values('mid',ascending=False).head(8)[['name','mid']].values)]
print("\n".join(out2)); open(f'{R}/notes/q1_out.txt','a').write("\n"+"\n".join(out2))
s=W[W.key.isin(set(Rp.key)-both)]; pa=P[P.name.str.contains('Repub',case=False)].ask.iloc[0]
line=f"  executable check GOP: Σ winner BIDS over Republican names = {s.bid.sum():.3f} vs party ASK {pa:.3f} → gap {100*(s.bid.sum()-pa):+.1f}¢ ({len(s)} legs; overlap name excluded: {', '.join(W[W.key.isin(both)].name)})"
print(line); open(f'{R}/notes/q1_out.txt','a').write("\n"+line)
