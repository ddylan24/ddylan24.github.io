import numpy as np, sys
R=sys.argv[1]; rng=np.random.default_rng(22); out=[]
# Kelly for a binary contract: buy YES at price p with belief q. Win: each $ staked returns (1-p)/p. f* = (q-p)/(1-p)
def kelly(q,p): return max(0,(q-p)/(1-p))
def growth(f,q,p): return q*np.log(1+f*(1-p)/p)+(1-q)*np.log(1-f)
for q,p in [(0.55,0.50),(0.60,0.50),(0.10,0.05),(0.30,0.20),(0.97,0.95)]:
    f=kelly(q,p); out.append(f"belief {q:.2f}, price {p:.2f}: Kelly stake {f:.1%} of bankroll; expected log-growth per bet {growth(f,q,p):.4f}; half-Kelly keeps {growth(f/2,q,p)/growth(f,q,p):.0%} of growth")
# fees: Polymarket-style taker fee shrinks the effective payout; with fee φ on winnings approx price p_eff = p + φ(1-p)
for fee in [0,0.01,0.02]:
    q,p=0.55,0.50; pe=p+fee*(1-p); out.append(f"fee {fee:.0%} of payout: effective price {pe:.3f}, Kelly {kelly(q,pe):.1%}, growth {growth(kelly(q,pe),q,pe):.4f}")
# time value: contract resolving in T years; must beat T-bill: compare annualized log growth to r
r=0.0425
for T in [1/52,0.25,1,2]:
    q,p=0.55,0.50; f=kelly(q,p); g=growth(f,q,p); out.append(f"edge 5¢ on 50¢ resolving in {T*52:.0f} weeks: Kelly growth per bet {g:.4f} → annualized {g/T:.2%} vs T-bill {r:.2%} on the idle part")
# estimation error: true q = p + 0.03, but trader's estimate noisy sd 0.05; bets full/half/quarter Kelly on estimate
p=0.5; trueq=0.53; N=2000; paths=3000
for frac in [1,0.5,0.25]:
    lw=np.zeros(paths)
    for _ in range(N):
        qhat=np.clip(trueq+0.05*rng.standard_normal(paths),0.01,0.99); f=np.maximum(0,(qhat-p)/(1-p))*frac; f=np.minimum(f,0.99)
        win=rng.random(paths)<trueq; lw+=np.where(win,np.log1p(f*(1-p)/p),np.log1p(-f))
    out.append(f"true edge 3¢, belief noise ±5¢, {N} bets: {frac}× Kelly on estimates → median log-wealth {np.median(lw):+.2f}, P(lost money) {np.mean(lw<0):.0%}, P(lost 90%+) {np.mean(lw<np.log(0.1)):.0%}")
txt="\n".join(out); print(txt); open(f'{R}/notes/p5_out.txt','w').write(txt)
