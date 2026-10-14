import json, sys, time, urllib.request, numpy as np, pandas as pd, concurrent.futures as cf
R=sys.argv[1]; out=[]
def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r: return json.load(r)
        except Exception: time.sleep(1+i)
mk=[]
for off in range(0,1000,100):
    d=get(f"https://gamma-api.polymarket.com/markets?closed=false&active=true&limit=100&offset={off}&order=volumeNum&ascending=false")
    if not d: break
    mk+=d
rows=[]
for m in mk:
    try: tk,tn=json.loads(m['clobTokenIds'])[:2]
    except Exception: continue
    rows.append(dict(q=m['question'],tok=tk,tokno=tn,bestBid=m.get('bestBid'),bestAsk=m.get('bestAsk'),vol=m.get('volumeNum') or 0,vol24=m.get('volume24hr') or 0,liq=m.get('liquidityNum') or 0))
M=pd.DataFrame(rows)
def book(args):
    tok,tn=args
    b=get(f"https://clob.polymarket.com/book?token_id={tok}"); n=get(f"https://clob.polymarket.com/book?token_id={tn}")
    if not b or not n: return None
    # merge complementary NO orders: a NO bid at q is a YES ask at 1-q; a NO ask at q is a YES bid at 1-q
    bids=sorted([(float(x['price']),float(x['size'])) for x in b.get('bids',[])]+[(round(1-float(x['price']),4),float(x['size'])) for x in n.get('asks',[])],reverse=True)
    asks=sorted([(float(x['price']),float(x['size'])) for x in b.get('asks',[])]+[(round(1-float(x['price']),4),float(x['size'])) for x in n.get('bids',[])])
    if not bids or not asks: return None
    bb,ba=bids[0][0],asks[0][0]; mid=(bb+ba)/2
    dep=lambda side,lim: sum(p*s for p,s in side if abs(p-mid)<=lim)
    # cost to buy $1,000 / $10,000 of YES walking the book
    def slip(notional):
        spent=0; sh=0
        for p,s in asks:
            take=min(s*p,notional-spent); sh+=take/p; spent+=take
            if spent>=notional-1e-9: break
        return (spent/sh-mid)/mid if spent>=notional-1e-9 and sh>0 else np.nan
    return dict(tok=tok,bid=bb,ask=ba,mid=mid,spread=ba-bb,depth1=dep(bids,0.01)+dep(asks,0.01),slip1k=slip(1000),slip10k=slip(10000))
with cf.ThreadPoolExecutor(8) as ex: B=[x for x in ex.map(book,zip(M.tok,M.tokno)) if x]
B=pd.DataFrame(B).merge(M,on='tok'); B=B[(B.mid>0.03)&(B.mid<0.97)]
out.append(f"  check vs gamma bestBid/bestAsk: median |our best ask − gamma bestAsk| = {(B.ask-B.bestAsk).abs().median()*100:.2f}¢")
B.to_csv(f'{R}/data/pm/books_snapshot.csv',index=False)
out.append(f"Live Polymarket order books (CLOB /book), top {len(M)} active markets by volume → {len(B)} with two-sided books and 3¢<mid<97¢, snapshot 2026-10-14")
out.append(f"  spread: median {B.spread.median()*100:.1f}¢, 25–75% [{B.spread.quantile(.25)*100:.1f}, {B.spread.quantile(.75)*100:.1f}]¢; share at 1-tick (≤0.1¢) {np.mean(B.spread<=0.0011):.0%}")
out.append(f"  $ depth within ±1¢ of mid: median ${B.depth1.median():,.0f}, 25–75% [${B.depth1.quantile(.25):,.0f}, ${B.depth1.quantile(.75):,.0f}]")
out.append(f"  slippage vs mid to buy $1k YES: median {B.slip1k.median():.2%}; $10k: median {B.slip10k.median():.2%} (NaN = book too thin: {B.slip10k.isna().mean():.0%} of markets)")
B['vt']=pd.qcut(B.vol24.rank(method='first'),3,labels=['low 24h vol','mid','high 24h vol'])
for k,g in B.groupby('vt',observed=True): out.append(f"  {k:<12}: spread {g.spread.median()*100:.1f}¢, depth±1¢ ${g.depth1.median():,.0f}, $10k slippage {g.slip10k.median():.2%}")
txt="\n".join(out); print(txt); open(f'{R}/notes/m3_out.txt','w').write(txt)
