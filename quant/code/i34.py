import numpy as np, pandas as pd, yfinance as yf, sys, warnings; warnings.filterwarnings('ignore')
R=sys.argv[1]; out=[]; rng=np.random.default_rng(18)
# --- Glosten–Milgrom
VH,VL,pi=101.0,99.0,0.3
def gm(true_high,steps=60):
    p=0.5; spreads=[]; mids=[]
    for t in range(steps):
        ask=(p*(1+pi)*VH+(1-p)*(1-pi)*VL)/(p*(1+pi)+(1-p)*(1-pi))
        bid=(p*(1-pi)*VH+(1-p)*(1+pi)*VL)/(p*(1-pi)+(1-p)*(1+pi))
        spreads.append(ask-bid); mids.append((ask+bid)/2)
        informed=rng.random()<pi; buy=(true_high if informed else rng.random()<0.5)
        p=p*(1+pi)/(p*(1+pi)+(1-p)*(1-pi)) if buy else p*(1-pi)/(p*(1-pi)+(1-p)*(1+pi))
    return np.array(spreads),np.array(mids)
S=np.mean([gm(True)[0] for _ in range(2000)],axis=0); M=np.mean([gm(True)[1] for _ in range(2000)],axis=0)
out.append(f"Glosten–Milgrom (V∈{{99,101}}, informed share π={pi}): initial spread {S[0]:.3f} (= π·(VH−VL) = {pi*(VH-VL):.3f}); after 10 trades {S[10]:.3f}, 30 trades {S[30]:.3f}; mid drifts to true value: {M[0]:.2f}→{M[10]:.2f}→{M[30]:.2f}")
for p_ in [0.1,0.3,0.6]: out.append(f"  initial spread with π={p_}: {p_*(VH-VL):.2f}  (spread ∝ share of informed traders)")
# --- Kyle (1985) one-period
sv,su,n=2.0,1.0,400000
v=rng.normal(0,sv,n); u=rng.normal(0,su,n); beta=su/sv; lam=sv/(2*su)
x=beta*v; y=x+u; p=lam*y
out.append(f"Kyle: β=σu/σv={beta:.2f}, λ=σv/(2σu)={lam:.2f}; sim: regression of p on order flow slope {np.polyfit(y,p,1)[0]:.2f}; E[p|y]≈E[v|y]? slope of v on y {np.polyfit(y,v,1)[0]:.2f}; Var(v|p)/Var(v) = {np.var(v-np.polyfit(p,v,1)[0]*p)/np.var(v):.3f} (theory 0.5); insider profit {np.mean(x*(v-p)):.3f} (theory σuσv/2={su*sv/2:.3f})")
# deviation check: insider trading more aggressively earns less
for b2 in [0.25,0.5,1.0]: out.append(f"  insider with β={b2}: expected profit {np.mean(b2*v*(v-lam*(b2*v+u))):.3f}")
# --- Roll spread estimator on real daily data
for tk in ['SPY','IWM','UPST']:
    c=yf.download(tk,start='2024-10-01',end='2026-10-14',progress=False,auto_adjust=False)['Close'].squeeze()
    d=c.diff().dropna(); cov=np.cov(d[1:],d[:-1])[0,1]
    out.append(f"Roll estimator {tk} (2y daily): autocov {cov:+.4f} → {'spread = 2√(−cov) = '+format(2*np.sqrt(-cov),'.3f')+' $ ('+format(2*np.sqrt(-cov)/c.mean()*1e4,'.1f')+' bp)' if cov<0 else 'positive autocov → estimator undefined (daily data dominated by real price moves, not bid-ask bounce)'}")
# --- I4 range-based vol estimators: efficiency via simulation (intraday GBM, no overnight gap)
def est(o,h,l,c,cprev):
    cc=np.log(c/cprev)**2
    pk=np.log(h/l)**2/(4*np.log(2))
    gk=0.5*np.log(h/l)**2-(2*np.log(2)-1)*np.log(c/o)**2
    rs=np.log(h/c)*np.log(h/o)+np.log(l/c)*np.log(l/o)
    return cc,pk,gk,rs
sig=0.01; days=20000; steps=390
z=rng.standard_normal((days,steps))*sig/np.sqrt(steps); path=np.cumsum(z,1)
o=np.ones(days); c=np.exp(path[:,-1]); h=np.exp(np.maximum(path.max(1),0)); l=np.exp(np.minimum(path.min(1),0))
cc,pk,gk,rs=est(o,h,l,c,o)
for lab,e in [('close-close',cc),('Parkinson',pk),('Garman–Klass',gk),('Rogers–Satchell',rs)]:
    out.append(f"  sim (no gaps) {lab:<16}: mean/σ² {e.mean()/sig**2:.3f}, efficiency vs close-close {cc.var()/e.var():.1f}x")
# real SPY: bias from overnight gaps
spy=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True)
O,Hh,L,C=spy.Open.values,spy.High.values,spy.Low.values,spy.Close.values
cc,pk,gk,rs=est(O[1:],Hh[1:],L[1:],C[1:],C[:-1]); ov=np.log(O[1:]/C[:-1])**2
out.append(f"Real SPY 1999–2026 annualized vol: close-close {np.sqrt(cc.mean()*252):.1%}, Parkinson {np.sqrt(pk.mean()*252):.1%}, Garman–Klass {np.sqrt(gk.mean()*252):.1%}, overnight-gap share of variance {ov.mean()/cc.mean():.0%} → range estimators miss the overnight part; Yang–Zhang adds it back")
# forecast test: predict next 21d close-close var using last 21d estimator (QLIKE)
cc_s=pd.Series(cc); fut=cc_s.rolling(21).mean().shift(-21)
for lab,e in [('close-close',cc),('Parkinson+overnight',pk+ov),('Garman–Klass+overnight',gk+ov)]:
    f=pd.Series(e).rolling(21).mean(); m=pd.concat([f,fut],axis=1).dropna(); a,b_=m.iloc[:,0],m.iloc[:,1]
    q=np.mean(b_/a-np.log(b_/a)-1); out.append(f"  next-month variance forecast QLIKE loss using {lab:<24}: {q:.4f} (lower is better)")
txt="\n".join(out); print(txt); open(f'{R}/notes/i34_out.txt','w').write(txt)
