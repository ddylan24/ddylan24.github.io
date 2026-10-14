import json, sys, time, urllib.request, concurrent.futures as cf, pandas as pd
R=sys.argv[1]
def get(u,tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r: return json.load(r)
        except Exception as e: time.sleep(2**i)
    return None
mk=[]
for off in range(0,8000,100):
    d=get(f"https://gamma-api.polymarket.com/markets?closed=true&limit=100&offset={off}&order=volumeNum&ascending=false")
    if not d: break
    mk+=d
    if len(d)<100: break
rows=[]
for m in mk:
    try:
        oc=json.loads(m.get('outcomes') or '[]'); op=[float(x) for x in json.loads(m.get('outcomePrices') or '[]')]; tk=json.loads(m.get('clobTokenIds') or '[]')
    except Exception: continue
    if oc!=['Yes','No'] or len(op)!=2 or sorted(op)!=[0.0,1.0] or len(tk)!=2: continue
    if (m.get('volumeNum') or 0)<50000: continue
    rows.append(dict(id=m['id'],q=m['question'],end=m.get('endDate'),closed=m.get('closedTime'),vol=m['volumeNum'],yes_won=int(op[0]==1.0),tok=tk[0],cat=m.get('category') or '', event=(m.get('events') or [{}])[0].get('title','') if m.get('events') else ''))
df=pd.DataFrame(rows); print('markets fetched',len(mk),'clean binary resolved with vol>=50k:',len(df))
def hist(tok):
    d=get(f"https://clob.polymarket.com/prices-history?market={tok}&interval=max&fidelity=1440")
    return tok,(d or {}).get('history',[])
H={}
with cf.ThreadPoolExecutor(8) as ex:
    for tok,h in ex.map(hist,df.tok): H[tok]=h
json.dump(H,open(f'{R}/data/pm/hist.json','w')); df.to_csv(f'{R}/data/pm/markets.csv',index=False)
print('with history:',sum(1 for v in H.values() if len(v)>5))
