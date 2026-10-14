import numpy as np, sys
R=sys.argv[1]; rng=np.random.default_rng(23); out=[]
# Binary event: true probability follows logit random walk; resolves at T to Bernoulli(p_T). Market maker quotes mid = its estimate.
# Flow: uninformed traders arrive (buy/sell 50/50); informed traders know p_true (trade if mispriced beyond spread).
def run(half_spread, informed_share, withdraw_hours=0, steps=24*14, paths=4000, sig_logit=0.08, mm_lag=6):
    pnl=np.zeros(paths); vol=np.zeros(paths)
    for k in range(paths):
        x=rng.normal(0,0.5); hist=[x]; inv=0.0; cash=0.0
        for t in range(steps):
            x+=sig_logit*rng.standard_normal(); hist.append(x)
            p=1/(1+np.exp(-x)); est=1/(1+np.exp(-hist[max(0,len(hist)-1-mm_lag)]))  # MM's view lags true by mm_lag hours
            if steps-t<=withdraw_hours: continue
            for _ in range(rng.poisson(2)):
                bid,ask=est-half_spread,est+half_spread
                if rng.random()<informed_share:
                    if p>ask: inv-=1; cash+=ask
                    elif p<bid: inv+=1; cash-=bid
                else:
                    if rng.random()<0.5: inv-=1; cash+=ask
                    else: inv+=1; cash-=bid
                vol[k]+=1
        y=rng.random()<1/(1+np.exp(-x))
        pnl[k]=cash+inv*y
    return pnl.mean(),pnl.std(),pnl.mean()/vol.mean()*100
out.append("N3 market making a binary (2 weeks hourly; true prob = logit random walk; MM's estimate lags 6h; ~2 orders/hour; resolves to 0/1):")
for inf in [0.0,0.1,0.3]:
    for hs in [0.005,0.01,0.02,0.04]:
        m,s,pc=run(hs,inf,paths=1500)
        out.append(f"  informed {inf:.0%}, half-spread {hs*100:.1f}¢: P&L/market {m:+.2f} ± {s:.2f} (per contract traded {pc:+.2f}¢)")
for w in [0,24,72]:
    m,s,pc=run(0.01,0.1,withdraw_hours=w,paths=1500); out.append(f"  informed 10%, half-spread 1¢, stop quoting {w}h before resolution: P&L {m:+.2f} ± {s:.2f}")
txt="\n".join(out); print(txt); open(f'{R}/notes/n3_out.txt','w').write(txt)
