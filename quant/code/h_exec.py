import numpy as np, pandas as pd, sys
from scipy.optimize import minimize
R=sys.argv[1]; rng=np.random.default_rng(13); out=[]
# H1 Almgren–Chriss: discrete, linear temp impact eta, permanent gamma (doesn't affect optimum shape), risk aversion lam
X,T,N=1e6,1.0,50; tau=T/N; sig=0.95; eta=2.5e-6; lam=2e-6
def cost(n):  # n: shares traded each interval; holdings x_k
    x=X-np.cumsum(np.r_[0,n[:-1]]); E=eta/tau*np.sum(n**2); V=sig**2*tau*np.sum(x**2); return E,V
def obj(n): E,V=cost(n); return E+lam*V
cons={'type':'eq','fun':lambda n: n.sum()-X}
res=minimize(obj,np.full(N,X/N),constraints=cons,method='SLSQP',options={'maxiter':500})
kt=np.arccosh(1+lam*sig**2*tau**2/(2*eta))/tau   # discrete AC kappa (eta_tilde≈eta)
tgrid=np.arange(N+1)*tau; x_cf=X*np.sinh(kt*(T-tgrid))/np.sinh(kt*T); n_cf=-np.diff(x_cf)
out.append(f"Almgren–Chriss: numerical optimum vs closed form sinh trajectory: max trade-size diff {np.max(abs(res.x-n_cf))/X:.2e} of X; κ={kt:.2f}; first interval sells {n_cf[0]/X:.1%}, last {n_cf[-1]/X:.1%} (TWAP = {1/N:.1%})")
for l in [0,2e-7,2e-6,2e-5]:
    k_=np.arccosh(1+l*sig**2*tau**2/(2*eta))/tau if l>0 else 1e-9
    x=X*np.sinh(k_*(T-tgrid))/np.sinh(k_*T); E,V=cost(-np.diff(x))
    out.append(f"  λ={l:.0e}: expected impact cost ${E:,.0f}, risk (std) ${np.sqrt(V):,.0f}")
# square-root law: cost ≈ Y·σ_daily·sqrt(Q/ADV), Y≈0.5–1 (Tóth et al. 2011, Bouchaud et al.)
import yfinance as yf
px=yf.download(['SPY','IWM','UPST'],start='2026-04-01',end='2026-10-14',progress=False,auto_adjust=True)
for tk in ['SPY','IWM','UPST']:
    c=px['Close'][tk]; v=px['Volume'][tk]; adv=(c*v).tail(60).mean(); sd=np.log(c).diff().tail(60).std()
    s=" ".join(f"${q/1e3:,.0f}k→{0.7*sd*np.sqrt(q/adv)*1e4:.1f}bp" for q in [1e4,1e6,1e8])
    out.append(f"  sqrt law ({tk}: ADV ${adv/1e9:.2f}B, daily σ {sd:.2%}, Y=0.7): {s}")
# H2 Avellaneda–Stoikov simulation (paper parameters)
def mm(inventory_aware,gamma=0.1,paths=1000,T=1.0,dt=0.005,sig=2.0,k=1.5,A=140,s0=100):
    steps=int(T/dt); pnl=[];inv=[]
    spread=gamma*sig**2*T+2/gamma*np.log(1+gamma/k)
    for _ in range(paths):
        s=s0;q=0;cash=0.0
        for i in range(steps):
            tl=T-i*dt
            sp=gamma*sig**2*tl+2/gamma*np.log(1+gamma/k)
            rp=s-q*gamma*sig**2*tl if inventory_aware else s
            ask=rp+sp/2; bid=rp-sp/2
            if not inventory_aware: ask=s+spread/2; bid=s-spread/2
            da,db=ask-s,s-bid
            if rng.random()<A*np.exp(-k*da)*dt: q-=1; cash+=ask
            if rng.random()<A*np.exp(-k*db)*dt: q+=1; cash-=bid
            s+=sig*np.sqrt(dt)*(1 if rng.random()<0.5 else -1)
        pnl.append(cash+q*s); inv.append(q)
    return np.mean(pnl),np.std(pnl),np.std(inv)
for lab,f in [('inventory-skewed (AS)',True),('symmetric around mid',False)]:
    m,s,qi=mm(f); out.append(f"Avellaneda–Stoikov γ=0.1: {lab}: profit {m:.2f} ± {s:.2f} (std), final inventory std {qi:.1f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/h_out.txt','w').write(txt)
