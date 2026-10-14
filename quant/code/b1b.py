import numpy as np, pandas as pd, sys
R=sys.argv[1]
px=pd.read_csv(f'{R}/data/lev_etfs.csv',index_col=0,parse_dates=True); r=px.pct_change().dropna()
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True)
j=r.join(ff.rf,how='inner'); yrs=len(j)/252
print(f"window {j.index[0].date()}→{j.index[-1].date()} ({yrs:.1f}y), avg T-bill (Ken French RF) {j.rf.mean()*252:.2%}/yr")
cagr=lambda x:(1+x).prod()**(1/yrs)-1
s=cagr(j.SPY)
for tk,L,fee in [('SSO',2,0.0089),('UPRO',3,0.0091)]:
    model=L*j.SPY-(L-1)*j.rf-fee/252
    print(f"{tk}: actual {cagr(j[tk]):.1%} | model (L·SPY − (L−1)·Tbill − fee, daily rebalanced) {cagr(model):.1%} | {L}×SPY CAGR {L*s:.1%} | gap from drag ≈ {L*s-cagr(L*j.SPY):.1%}, from financing+fees ≈ {cagr(L*j.SPY)-cagr(model):.1%}")
