import numpy as np, pandas as pd, sys, statsmodels.api as sm
from scipy import stats
R=sys.argv[1]; D=f'{R}/data/fx'; out=[]
def ld(s): return pd.to_numeric(pd.read_csv(f'{D}/{s}.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce').dropna()
# USD per 1 unit of foreign currency
fx={'JPY':1/ld('DEXJPUS'),'EUR':ld('DEXUSEU'),'AUD':ld('DEXUSAL'),'CAD':1/ld('DEXCAUS'),'GBP':ld('DEXUSUK'),'CHF':1/ld('DEXSZUS'),'NZD':ld('DEXUSNZ'),'NOK':1/ld('DEXNOUS'),'SEK':1/ld('DEXSDUS')}
rc={'JPY':'JP','EUR':'EZ','AUD':'AU','CAD':'CA','GBP':'GB','CHF':'CH','NZD':'NZ','NOK':'NO','SEK':'SE'}
S=pd.DataFrame({k:v.resample('ME').last() for k,v in fx.items()})
I=pd.DataFrame({k:ld(f'IR3TIB01{c}M156N').resample('ME').last() for k,c in rc.items()})/100
us=ld('IR3TIB01USM156N').resample('ME').last()/100
idx=S.dropna().index.intersection(I.dropna().index).intersection(us.dropna().index); S,I,us=S.loc[idx],I.loc[idx],us.loc[idx]
# excess return of holding foreign deposit for next month, financed in USD
ex=(S.shift(-1)/S)*(1+I/12)-(1+us.values[:,None]/12)
diff=(I.sub(us,axis=0)).shift(1)   # use last month's published rate (avoid look-ahead)
out.append(f"G10 carry vs USD (FRED daily FX, OECD 3m rates), monthly {idx[0].date()}→{idx[-2].date()}, 9 currencies")
port=[]
for t in diff.index[1:-1]:
    d=diff.loc[t].dropna(); 
    if len(d)<6: continue
    hi=d.nlargest(3).index; lo=d.nsmallest(3).index
    port.append((t,ex.loc[t,hi].mean()-ex.loc[t,lo].mean()))
P=pd.Series(dict(port)).dropna()
eq=(1+P).cumprod(); dd=1-eq/eq.cummax()
out.append(f"  long top-3 / short bottom-3 rate currencies: {P.mean()*12:.1%}/yr, vol {P.std()*np.sqrt(12):.1%}, Sharpe {P.mean()/P.std()*np.sqrt(12):.2f}, skew {stats.skew(P):.2f}, worst month {P.min():.1%} ({P.idxmin().strftime('%Y-%m')}), max drawdown {dd.max():.0%}")
for a,b in [('2002','2007'),('2008','2008'),('2009','2026')]:
    x=P[a:b]; out.append(f"    {a}–{b}: {((1+x).prod()-1):+.1%} total, Sharpe {x.mean()/x.std()*np.sqrt(12) if len(x)>2 else float('nan'):.2f}")
# where carry return comes from: interest differential vs spot move
spot=(S.shift(-1)/S-1); inc=(I.sub(us,axis=0))/12
sp,ic=[],[]
for t,_ in port:
    d=diff.loc[t].dropna(); hi=d.nlargest(3).index; lo=d.nsmallest(3).index
    sp.append(spot.loc[t,hi].mean()-spot.loc[t,lo].mean()); ic.append(inc.loc[t,hi].mean()-inc.loc[t,lo].mean())
out.append(f"  decomposition: interest-rate differential {np.mean(ic)*12:+.1%}/yr, spot FX move {np.nanmean(sp)*12:+.1%}/yr (UIP predicts spot ≈ −differential)")
# Fama regression: Δs_{t+1} = α + β (i_f − i_us)_t ; UIP β = −1 in this sign convention (foreign currency should depreciate by the differential)
y=[];x=[]
for c in S.columns:
    s=np.log(S[c]).diff().shift(-1); d=(I[c]-us)/12
    m=pd.concat([s,d],axis=1).dropna(); y+=list(m.iloc[:,0]); x+=list(m.iloc[:,1])
fit=sm.OLS(np.array(y),sm.add_constant(np.array(x))).fit()
out.append(f"  Fama (1984) pooled regression of next-month FX appreciation on rate differential: β={fit.params[1]:+.2f} (t {fit.tvalues[1]:+.2f}); UIP predicts β=−1, 'random walk' β=0")
# crash risk vs VIX changes
vix=pd.to_numeric(pd.read_csv(f'{R}/data/VIXCLS.csv',index_col=0,parse_dates=True).iloc[:,0],errors='coerce').resample('ME').last()
dv=vix.diff().shift(-1).reindex(P.index)
out.append(f"  corr(carry return, VIX change same month) = {np.corrcoef(P,dv.fillna(0))[0,1]:+.2f} → carry loses when fear spikes")
txt="\n".join(out); print(txt); open(f'{R}/notes/l3_out.txt','w').write(txt)
