import json, sys, urllib.request, numpy as np, pandas as pd, statsmodels.api as sm, re
R=sys.argv[1]; out=[]
# P7 horizon dependence
df=pd.read_csv(f'{R}/data/pm/markets.csv',dtype={'tok':str}); H=json.load(open(f'{R}/data/pm/hist.json'))
df['endts']=pd.to_datetime(df.end,utc=True,errors='coerce',format='mixed'); df['closets']=pd.to_datetime(df.closed,utc=True,errors='coerce',format='mixed')
out.append("P7 calibration vs horizon (Polymarket, scheduled end date, markets still open); logit(outcome) ~ a + b·logit(price): b>1 ⇒ prices too close to 50% (under-confident), b<1 ⇒ over-confident")
for h in [1,7,30,90,180]:
    rec=[]
    for _,m in df.iterrows():
        hh=H.get(m.tok) or []
        if len(hh)<3 or pd.isna(m.endts): continue
        cut=m.endts.timestamp()-h*86400
        if pd.notna(m.closets) and m.closets.timestamp()<=cut: continue
        pts=[p for p in hh if p['t']<=cut]
        if pts: rec.append((pts[-1]['p'],m.yes_won,m.event))
    d=pd.DataFrame(rec,columns=['p','y','event']); d=d[(d.p>0.01)&(d.p<0.99)]
    if len(d)<50: continue
    X=sm.add_constant(np.log(d.p/(1-d.p))); fit=sm.Logit(d.y,X).fit(disp=0,cov_type='cluster',cov_kwds={'groups':pd.factorize(d.event)[0]})
    mid=d[(d.p>=.05)&(d.p<=.95)]
    out.append(f"  {h:3d}d: n={len(d):4d} ({d.event.nunique()} events)  slope b={fit.params.iloc[1]:.2f} (se {fit.bse.iloc[1]:.2f}), intercept a={fit.params.iloc[0]:+.2f}; Brier {np.mean((d.p-d.y)**2):.4f}; mid-priced outcome−price {(mid.y-mid.p).mean():+.3f}")
# P8 cross-venue 2028 presidential winner
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r: return json.load(r)
kev=json.load(open(f'{R}/data/pm/kalshi_events.json'))
def kal(ticker):
    e=[x for x in kev if x['event_ticker']==ticker][0]; rows=[]
    for m in e['markets']:
        name=m.get('yes_sub_title') or m.get('subtitle') or m['ticker']
        b=float(m.get('yes_bid_dollars') or 0); a=float(m.get('yes_ask_dollars') or 0)
        rows.append(dict(name=name.strip(),k_bid=b,k_ask=a))
    return pd.DataFrame(rows)
pe=get("https://gamma-api.polymarket.com/events?closed=false&active=true&limit=100&order=volume&ascending=false")
def pmev(title):
    e=[x for x in pe if x['title']==title][0]
    return pd.DataFrame([dict(name=(m.get('groupItemTitle') or m['question']).strip(),p_bid=m.get('bestBid'),p_ask=m.get('bestAsk')) for m in e['markets'] if m.get('active') and not m.get('closed')])
def norm(s): return re.sub(r'[^a-z]','',s.lower().split('(')[0])
for kt,pt in [('KXPRESPERSON-28','Presidential Election Winner 2028'),('KXPRESPARTY-2028','Which party wins 2028 US Presidential Election?')]:
    try:
        K=kal(kt); P=pmev(pt)
    except Exception as ex:
        out.append(f"P8 {kt}: match failed ({ex})"); continue
    K['key']=K.name.map(norm); P['key']=P.name.map(norm)
    M=K.merge(P,on='key',suffixes=('_k','_p')).dropna(subset=['p_bid','p_ask'])
    M=M[(M.k_ask>0)&(M.p_ask>0)]
    M['k_mid']=(M.k_bid+M.k_ask)/2; M['p_mid']=(M.p_bid+M.p_ask)/2; M['diff']=M.k_mid-M.p_mid
    M['arb1']=1-(M.k_ask+(1-M.p_bid)); M['arb2']=1-(M.p_ask+(1-M.k_bid))   # buy YES on K + NO on P ; buy YES on P + NO on K
    out.append(f"P8 cross-venue {kt} vs Polymarket '{pt}': {len(M)} matched outcomes; mean |mid diff| {M['diff'].abs().mean()*100:.2f}¢, max {M['diff'].abs().max()*100:.2f}¢; correlation of mids {np.corrcoef(M.k_mid,M.p_mid)[0,1]:.3f}")
    top=M.sort_values('p_mid',ascending=False).head(8)
    for _,r in top.iterrows(): out.append(f"    {r.name_k[:28]:<28} Kalshi {r.k_bid:.2f}/{r.k_ask:.2f}  Polymarket {r.p_bid:.3f}/{r.p_ask:.3f}  mid diff {r['diff']*100:+.1f}¢")
    best=max(M.arb1.max(),M.arb2.max()); out.append(f"    best gross cross-venue lock (buy YES one venue + NO other, at quotes): {best*100:+.2f}¢ per $1 payout, before fees, capital locked to Nov 2028, and resolution rules may differ")
txt="\n".join(out); print(txt); open(f'{R}/notes/p78_out.txt','w').write(txt)
