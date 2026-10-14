import json, sys, time, urllib.request, numpy as np, pandas as pd
from scipy import stats
R=sys.argv[1]; out=[]
def post(body):
    for i in range(4):
        try:
            rq=urllib.request.Request('https://api.hyperliquid.xyz/info',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(rq,timeout=30) as r: return json.load(r)
        except Exception: time.sleep(2**i)
    return []
F={}
for coin in ['BTC','ETH','SOL']:
    t=1672531200000; rows=[]
    while True:
        d=post({"type":"fundingHistory","coin":coin,"startTime":t})
        if not d: break
        rows+=d; nt=d[-1]['time']+1
        if len(d)<500 or nt<=t: break
        t=nt
    s=pd.Series({pd.to_datetime(x['time'],unit='ms',utc=True):float(x['fundingRate']) for x in rows}).sort_index()
    F[coin]=s; s.to_csv(f'{R}/data/funding_{coin}.csv')
rf=pd.to_numeric(pd.read_csv(f'{R}/data/DGS3MO.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce').dropna()
for coin,s in F.items():
    ann=s.mean()*24*365; d=s.resample('D').sum()
    out.append(f"{coin} perp funding (Hyperliquid, hourly, {s.index[0].date()}→{s.index[-1].date()}, n={len(s)}): mean annualized {ann:.1%}; positive {np.mean(s>0):.0%} of hours; daily funding autocorr lag1 {d.autocorr(1):.2f}, lag7 {d.autocorr(7):.2f}")
    m=d.resample('ME').sum()*12
    out.append(f"   monthly annualized funding: median {m.median():.1%}, 10th pct {m.quantile(.1):.1%}, 90th pct {m.quantile(.9):.1%}, worst month {m.min():.1%} ({m.idxmin().strftime('%Y-%m')}), best {m.max():.1%} ({m.idxmax().strftime('%Y-%m')})")
    for y in sorted(set(d.index.year)): out.append(f"   {y}: annualized {d[str(y)].mean()*365:.1%} (T-bill avg {rf[str(y)].mean():.2f}%)")
# does high funding predict BTC returns? (crowded longs)
import yfinance as yf
px=yf.download('BTC-USD',start='2023-01-01',progress=False,auto_adjust=True)['Close'].squeeze(); px.index=px.index.tz_localize('UTC')
d=F['BTC'].resample('D').sum(); f7=d.rolling(7).sum()*365/7
fwd=np.log(px).shift(-7)-np.log(px); j=pd.concat([f7.rename('fund'),fwd.rename('fwd')],axis=1).dropna().iloc[::7]
q=pd.qcut(j.fund,3,labels=['low','mid','high'])
out.append("BTC: trailing-7d funding (annualized) vs next-7d BTC return (non-overlapping weeks): "+", ".join(f"{k} funding → {v:+.2%}" for k,v in j.groupby(q,observed=True).fwd.mean().items())+f"; corr {j.corr().iloc[0,1]:+.2f} (n={len(j)})")
# cash-and-carry P&L with delta-hedge: long spot, short perp; P&L = funding received (ignoring basis & fees)
s=F['BTC']; daily=s.resample('D').sum(); eq=daily.cumsum()
out.append(f"BTC cash-and-carry (long spot, short perp, collect funding; no fees/basis): cumulative {eq.iloc[-1]:.1%} over {(daily.index[-1]-daily.index[0]).days/365:.1f} yrs; worst 30-day funding {daily.rolling(30).sum().min():.2%}; Sharpe of daily funding {daily.mean()/daily.std()*np.sqrt(365):.1f} (understates risk: exchange, liquidation of short leg, basis)")
txt="\n".join(out); print(txt); open(f'{R}/notes/m2_out.txt','w').write(txt)
