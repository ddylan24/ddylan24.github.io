import json, sys, time, urllib.request, numpy as np, pandas as pd
R=sys.argv[1]; out=[]
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r: return json.load(r)
        except Exception: time.sleep(2**i)
ev=[]
for off in range(0,3000,100):
    d=get(f"https://gamma-api.polymarket.com/events?closed=false&active=true&limit=100&offset={off}&order=volume&ascending=false")
    if not d: break
    ev+=d
    if len(d)<100: break
rows=[]
for e in ev:
    if not e.get('negRisk'): continue
    ms=[m for m in e.get('markets',[]) if m.get('active') and not m.get('closed') and m.get('acceptingOrders',True)]
    if len(ms)<2: continue
    asks=[m.get('bestAsk') for m in ms]; bids=[m.get('bestBid') for m in ms]
    if any(a is None for a in asks) or any(b is None for b in bids): continue
    asks=np.array(asks,float); bids=np.array(bids,float)
    end=pd.to_datetime(e.get('endDate'),utc=True,errors='coerce')
    fee=any(m.get('feesEnabled') for m in ms)
    rows.append(dict(title=e['title'],n=len(ms),sum_ask=asks.sum(),sum_bid=bids.sum(),sum_mid=((asks+bids)/2).sum(),vol=e.get('volume') or 0,end=end,fees=fee,other=any(m.get('negRiskOther') for m in ms)))
d=pd.DataFrame(rows); now=pd.Timestamp('2026-10-14',tz='UTC'); d['years']=((d.end-now).dt.days/365).clip(lower=1/365)
out.append(f"Live Polymarket snapshot 2026-10-14: {len(ev)} active events scanned, {len(d)} multi-outcome (negRisk) events with quotes on every outcome")
out.append(f"  sum of mid prices across outcomes: median {d.sum_mid.median():.3f}, 5–95% [{d.sum_mid.quantile(.05):.3f}, {d.sum_mid.quantile(.95):.3f}]")
buy=d[d.sum_ask<1]; sell=d[d.sum_bid>1]
out.append(f"  'buy every YES' Dutch book (Σ best asks < $1): {len(buy)} events; median edge {(1-buy.sum_ask).median()*100 if len(buy) else 0:.2f}¢; max {(1-buy.sum_ask).max()*100 if len(buy) else 0:.2f}¢")
out.append(f"  'sell every YES / buy every NO' (Σ best bids > $1): {len(sell)} events; median edge {(sell.sum_bid-1).median()*100 if len(sell) else 0:.2f}¢; max {(sell.sum_bid-1).max()*100 if len(sell) else 0:.2f}¢")
for _,r in pd.concat([buy,sell]).sort_values('vol',ascending=False).head(6).iterrows():
    edge=max(1-r.sum_ask,r.sum_bid-1); ann=(1+edge)**(1/r.years)-1
    out.append(f"    {r.title[:60]:<60} n={r.n:3d} Σask {r.sum_ask:.3f} Σbid {r.sum_bid:.3f} ends {r.end.date() if pd.notna(r.end) else '?'} → edge {edge*100:.2f}¢, annualized {ann:.1%}{' (has fees)' if r.fees else ''}{' (has Other/placeholder)' if r.other else ''}")
out.append("  caveat: best-quote size is often tiny; touching all n books needs n fills; capital locked to resolution; resolution/UMA dispute risk")
d.to_csv(f'{R}/data/pm/negrisk_snapshot.csv',index=False)
# P3 LMSR math checks
def C(q,b): return b*np.log(np.sum(np.exp(np.array(q)/b)))
def price(q,b): e=np.exp(np.array(q)/b); return e/e.sum()
b=1000; q=[0,0]; out.append(f"LMSR b={b}, binary, start 50/50: worst-case MM loss b·ln2 = ${b*np.log(2):.2f}")
p0,p1=0.5,0.8; dq=b*np.log(p1*(1-p0)/(p0*(1-p1))); cost=C([dq,0],b)-C([0,0],b)
out.append(f"  move YES 50%→80%: buy {dq:.1f} YES shares for ${cost:.2f} (avg {cost/dq:.3f}/share); payoff if YES ${dq:.1f} → MM loss {dq-cost:.2f} = b·ln(1/0.5)−... check: b·ln(p1/p0)={b*np.log(p1/p0):.2f}")
# informed trader pushes to true prob; MM expected loss = b * KL-type term
for tp in [0.6,0.8,0.95,0.999]:
    dq=b*np.log(tp*(0.5)/(0.5*(1-tp))); cost=C([dq,0],b)-C([0,0],b); exp_loss=tp*dq-cost
    out.append(f"  informed trader moves price to true p={tp}: expected MM loss ${exp_loss:.2f} (= b·KL(p‖0.5) = {b*(tp*np.log(tp/0.5)+(1-tp)*np.log((1-tp)/0.5)):.2f})")
for n in [2,10,128]: out.append(f"  n={n} outcomes: max loss b·ln n = ${b*np.log(n):.0f} per $1000 of b")
txt="\n".join(out); print(txt); open(f'{R}/notes/p34_out.txt','w').write(txt)
