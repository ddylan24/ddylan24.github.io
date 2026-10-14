import numpy as np, pandas as pd, yfinance as yf, sys, warnings; warnings.filterwarnings('ignore')
from scipy import stats
R=sys.argv[1]; out=[]
a=pd.read_excel(f'{R}/data/aqr_tsmom.xlsx','TSMOM Factors',header=None)
hr=a.index[a.iloc[:,1].astype(str).str.strip()=='TSMOM'][0]
aq=a.iloc[hr+1:].copy(); aq.columns=a.iloc[hr].astype(str).str.strip(); aq=aq.dropna(subset=[aq.columns[0]])
aq.index=pd.to_datetime(aq.iloc[:,0])+pd.offsets.MonthEnd(0); aq=aq.iloc[:,1:].apply(pd.to_numeric,errors='coerce')
out.append(f"AQR TSMOM factor file: columns {list(aq.columns)}, {aq.index[0].date()}→{aq.index[-1].date()}")
ts=aq['TSMOM'].dropna()
sr=lambda x:np.sqrt(12)*x.mean()/x.std()
for p0,p1 in [('1985','1999'),('2000','2009'),('2010','2026')]:
    s=ts[p0:p1]; out.append(f"  AQR TSMOM {p0}–{p1}: ann ret {s.mean()*12:.1%}, Sharpe {sr(s):.2f}")
# my ETF replication
tk=['SPY','EFA','EEM','IWM','TLT','IEF','LQD','GLD','SLV','DBC','USO','UUP','FXE','FXY','VNQ']
px=yf.download(tk,start='2006-01-01',end='2026-10-14',progress=False,auto_adjust=True)['Close']
px.to_csv(f'{R}/data/tsmom_etfs.csv')
d=px.pct_change(); rf_d=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True).rf
ex=d.sub(rf_d.reindex(d.index).fillna(0),axis=0)
vol=np.sqrt((ex**2).ewm(com=60).mean()*252)
m_ex=(1+ex).resample('ME').prod()-1; m_vol=vol.resample('ME').last()
res={}
for L in [1,3,6,9,12]:
    for vs in [True,False]:
        sig=np.sign((1+m_ex).rolling(L).apply(np.prod,raw=True)-1)
        w=(sig*(0.40/m_vol) if vs else sig).shift(1)
        n_av=w.notna().sum(1).replace(0,np.nan)
        port=(w*m_ex).sum(1)/n_av
        port=port.dropna().loc['2008':'2026-08']
        turn=(w.diff().abs().sum(1)/n_av).reindex(port.index)
        for c in [0,0.002]:
            r=port-c*turn; res[(L,vs,c)]=r
best=None
for (L,vs,c),r in res.items():
    if c==0: out.append(f"  ETF TSMOM lookback {L:2d}m, {'vol-scaled' if vs else 'equal-notional'}: Sharpe {sr(r):.2f} (with 20bp costs {sr(res[(L,vs,0.002)]):.2f})")
mine=res[(12,True,0)]; j=pd.concat([mine,ts],axis=1).dropna()
out.append(f"  correlation of my 12m vol-scaled ETF version with AQR TSMOM (2008–2026, monthly): {j.corr().iloc[0,1]:.2f}; AQR Sharpe same window {sr(j.iloc[:,1]):.2f}, mine {sr(j.iloc[:,0]):.2f}")
# Deflated Sharpe: 10 variants (gross)
srs=np.array([sr(r)/np.sqrt(12) for (L,vs,c),r in res.items() if c==0]); N=len(srs)
b=res[(12,True,0)]; T=len(b); s=b.mean()/b.std(); sk=stats.skew(b); ku=stats.kurtosis(b,fisher=False)
emc=0.5772156649; V=srs.var(ddof=1)
sr0=np.sqrt(V)*((1-emc)*stats.norm.ppf(1-1/N)+emc*stats.norm.ppf(1-1/(N*np.e)))
dsr=stats.norm.cdf((s-sr0)*np.sqrt(T-1)/np.sqrt(1-sk*s+(ku-1)/4*s*s))
psr=stats.norm.cdf((s)*np.sqrt(T-1)/np.sqrt(1-sk*s+(ku-1)/4*s*s))
out.append(f"  Deflated Sharpe for the 12m vol-scaled variant among {N} tried: monthly SR {s:.3f}, benchmark max-from-luck SR0 {sr0:.3f}; PSR(>0) {psr:.2f}, DSR {dsr:.2f}")
# crisis alpha
for a0,b0,lab in [('2008-01','2008-12','2008 GFC'),('2022-01','2022-12','2022 rates shock'),('2020-02','2020-04','COVID crash')]:
    out.append(f"  {lab}: my TSMOM {(1+mine[a0:b0]).prod()-1:+.1%}, AQR {(1+ts[a0:b0]).prod()-1:+.1%}, SPY {(1+m_ex['SPY'][a0:b0]).prod()-1:+.1%}")
txt="\n".join(out); print(txt); open(f'{R}/notes/g1_out.txt','w').write(txt)
