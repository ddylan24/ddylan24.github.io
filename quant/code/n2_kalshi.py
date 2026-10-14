import json, sys, time, urllib.request, numpy as np, pandas as pd, statsmodels.api as sm, concurrent.futures as cf
R=sys.argv[1]; out=[]
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=40) as r: return json.load(r)
        except Exception: time.sleep(1+2**i)
    return {}
series=['KXHIGHNY','KXHIGHCHI','KXHIGHMIA','KXHIGHLAX','KXHIGHAUS','KXHIGHDEN']
mk=[]
for s in series:
    cur=''
    while True:
        d=get(f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={s}&status=settled&limit=1000"+(f"&cursor={cur}" if cur else ''))
        for m in d.get('markets',[]):
            if m.get('result') in ('yes','no'): mk.append(dict(series=s,ticker=m['ticker'],event=m['event_ticker'],close=pd.Timestamp(m['close_time']),y=int(m['result']=='yes'),sub=m.get('yes_sub_title','')))
        cur=d.get('cursor') or ''
        if not cur or not d.get('markets'): break
M=pd.DataFrame(mk)
def px(row):
    end=int(row.close.timestamp()); target=end-24*3600
    d=get(f"https://api.elections.kalshi.com/trade-api/v2/series/{row.series}/markets/{row.ticker}/candlesticks?start_ts={target-6*3600}&end_ts={target}&period_interval=60")
    c=d.get('candlesticks',[])
    for k in reversed(c):
        b=float(k['yes_bid'].get('close_dollars') or 0); a=float(k['yes_ask'].get('close_dollars') or 0)
        if b>0 and a>0 and a-b<=0.10: return (b+a)/2,b,a
    return np.nan,np.nan,np.nan
with cf.ThreadPoolExecutor(6) as ex: res=list(ex.map(px,[r for _,r in M.iterrows()]))
M['p']=[x[0] for x in res]; M['bid']=[x[1] for x in res]; M['ask']=[x[2] for x in res]
M.to_csv(f'{R}/data/pm/kalshi_weather.csv',index=False)
F=M[(M.p>0.01)&(M.p<0.99)].dropna(subset=['p'])
out.append(f"N2 Kalshi daily high-temperature markets ({', '.join(series)}), settled {M.close.min().date()}→{M.close.max().date()}: {len(M)} markets in {M.event.nunique()} city-days; with a two-sided quote (spread ≤10¢) 24h before close and 1¢<p<99¢: n={len(F)} in {F.event.nunique()} city-days")
X=sm.add_constant(np.log(F.p/(1-F.p))); fit=sm.Logit(F.y,X).fit(disp=0,cov_type='cluster',cov_kwds={'groups':pd.factorize(F.event)[0]})
mid=F[(F.p>=.05)&(F.p<=.95)]; e=mid.y-mid.p; g=e.groupby(mid.event).mean()
out.append(f"  Brier {np.mean((F.p-F.y)**2):.4f} vs base-rate {np.mean((F.y.mean()-F.y)**2):.4f} (skill {1-np.mean((F.p-F.y)**2)/np.mean((F.y.mean()-F.y)**2):.0%}); calibration slope b {fit.params.iloc[1]:.2f} ± {fit.bse.iloc[1]:.2f}, intercept {fit.params.iloc[0]:+.2f}")
out.append(f"  mid-priced (5–95¢) outcome − price {e.mean():+.3f} (clustered t {g.mean()/(g.std()/np.sqrt(len(g))):+.2f}, n {len(mid)})")
F['bin']=pd.cut(F.p,[0,.05,.15,.3,.5,.7,.85,.95,1.0001],right=False)
for b,gg in F.groupby('bin',observed=True):
    if len(gg)>=15: out.append(f"    {b.left:.2f}–{min(b.right,1):.2f}: n={len(gg):4d}, avg price {gg.p.mean():.3f}, won {gg.y.mean():.3f}")
# each city-day: sum of bucket mids (should ≈1)
s=F.groupby('event').p.sum(); out.append(f"  sum of quoted bucket mids per city-day (where all buckets quoted may be incomplete): median {s.median():.3f}")
cheap=F[F.p<0.05]; fee=lambda q: np.ceil(0.07*q*(1-q)*100)/100   # Kalshi taker fee per contract (dollars), rounded up to cent
ev_sell=(cheap.bid-cheap.y)-cheap.bid.map(fee)   # sell YES at bid (= buy NO at 1-bid): gain bid, pay 1 if YES
out.append(f"  selling the cheapest buckets (<5¢ mid) at the BID: avg bid {cheap.bid.mean():.3f}, YES rate {cheap.y.mean():.3f}, EV per contract after Kalshi taker fee {ev_sell.mean()*100:+.2f}¢ (n {len(cheap)})")
txt="\n".join(out); print(txt); open(f'{R}/notes/n2_out.txt','w').write(txt)
