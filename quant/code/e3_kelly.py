import numpy as np, pandas as pd, sys
R=sys.argv[1]; rng=np.random.default_rng(11); out=[]
# discrete Kelly: p=0.55, b=1
p,b=0.55,1.0; f=p-(1-p)/b; out.append(f"discrete Kelly p=.55, even odds: f*={f:.2f}; growth/bet at f*: {p*np.log(1+f*b)+(1-p)*np.log(1-f):.5f}")
# drawdown law: P(wealth ever hits fraction x of start) = x^(2/c - 1), c = fraction of Kelly (continuous GBM)
mu,sig=0.08,0.20; fk=mu/sig**2; T=50; n=252*T; dt=1/252
for c in [0.5,1.0,2.0]:
    L=c*fk; paths=3000; hit={0.5:0,0.25:0}
    lw=np.zeros(paths); mn=np.zeros(paths)
    for t in range(n):
        lw+= (L*mu - 0.5*L*L*sig*sig)*dt + L*sig*np.sqrt(dt)*rng.standard_normal(paths); mn=np.minimum(mn,lw)
    for x in hit: hit[x]=np.mean(mn<=np.log(x))
    th={x:(x**(2/c-1) if c<2 else 1.0) for x in hit}
    out.append(f"{c}×Kelly ({L:.1f}x lev), 50y: P(ever lose 50%) sim {hit[0.5]:.2f} theory {th[0.5]:.2f}; P(ever lose 75%) sim {hit[0.25]:.2f} theory {th[0.25]:.2f}")
# real history: CRSP market excess daily, constant leverage L, financing at RF
ff=pd.read_csv(f'{R}/data/ff3_daily.csv',index_col=0,parse_dates=True)
ex,rf=ff.mkt_rf,ff.rf; yrs=len(ex)/252
mu_h,var_h=ex.mean()*252,ex.var()*252
out.append(f"CRSP 1926–2026: excess μ={mu_h:.1%}, σ={np.sqrt(var_h):.1%} → hindsight Kelly L*=μ/σ²={mu_h/var_h:.2f}x")
for L in [0.5,1,1.5,2,2.5,3,4]:
    r=L*ex+rf; eq=np.cumprod(1+r.values); g=np.log(eq[-1])/yrs; dd=(1-eq/np.maximum.accumulate(eq)).max()
    out.append(f"  L={L:3.1f}x daily-rebalanced: realized log growth {g:6.2%}/yr (Itô pred {np.mean(np.log1p(rf))*252+L*mu_h-0.5*L*L*var_h:6.2%}), max drawdown {dd:.1%}{'  (wiped out)' if eq.min()<0.01 else ''}")
# estimation error: Kelly from trailing 10y, applied next year
lev=[];g=[]
ann=ex.groupby(ex.index.year)
yrsl=sorted(set(ex.index.year))
for y in yrsl[10:]:
    h=ex[(ex.index.year>=y-10)&(ex.index.year<y)]; Lk=max(0,h.mean()/h.var()); lev.append(Lk)
out.append(f"trailing-10y Kelly estimate across years: median {np.median(lev):.1f}x, range {min(lev):.1f}x–{max(lev):.1f}x  → the input swings wildly")
txt="\n".join(out); print(txt); open(f'{R}/notes/e3_out.txt','w').write(txt)
