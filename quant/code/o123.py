import numpy as np, pandas as pd, sys
from scipy import stats
from scipy.stats import norm
R=sys.argv[1]; rng=np.random.default_rng(24); out=[]
# O1 proper scoring rules
q=0.7; rs=np.linspace(0.01,0.99,99)
brier=-(q*(rs-1)**2+(1-q)*rs**2); logs=q*np.log(rs)+(1-q)*np.log(1-rs); lin=q*rs+(1-q)*(1-rs)
out.append(f"O1 true prob 0.7: report maximizing expected Brier {rs[np.argmax(brier)]:.2f}, log {rs[np.argmax(logs)]:.2f}, LINEAR (improper) {rs[np.argmax(lin)]:.2f} ← linear score rewards exaggeration")
b=100; p0=np.array([0.5,0.5]); 
for pf in [0.6,0.9]:
    q_shares=b*np.log(pf/(1-pf)); cost=b*np.log(np.exp(q_shares/b)+1)-b*np.log(2)
    out.append(f"  LMSR = market log scoring rule: moving 0.5→{pf}, trader's net payoff if YES = {q_shares-cost:.3f} = b·[ln {pf} − ln 0.5] = {b*(np.log(pf)-np.log(0.5)):.3f}")
d=pd.read_csv(f'{R}/data/pm/calib_sched_h7.csv'); d=d[(d.p>0.001)&(d.p<0.999)]
ll=-np.mean(d.y*np.log(d.p)+(1-d.y)*np.log(1-d.p)); base=d.y.mean(); llb=-np.mean(d.y*np.log(base)+(1-d.y)*np.log(1-base))
out.append(f"  Polymarket 7d-before prices: log loss {ll:.4f} vs base rate {llb:.4f} (skill {1-ll/llb:.0%}); Brier skill (earlier) 45% — log loss punishes confident misses harder")
worst=d.assign(l=-(d.y*np.log(d.p)+(1-d.y)*np.log(1-d.p))).nlargest(3,'l'); out.append("  biggest log-loss misses (price, outcome): "+", ".join(f"({r.p:.3f},{int(r.y)})" for _,r in worst.iterrows()))
# O2 MC variance reduction: BS call S=K=100,T=1,r=.04,s=.2 ; true 9.9251
S0,K,T,r,s=100,100,1,0.04,0.2; true=9.925058; N=20000; reps=300
def plain(): Z=rng.standard_normal(N); ST=S0*np.exp((r-s*s/2)*T+s*np.sqrt(T)*Z); return np.exp(-r*T)*np.maximum(ST-K,0).mean()
def anti(): Z=rng.standard_normal(N//2); Z=np.r_[Z,-Z]; ST=S0*np.exp((r-s*s/2)*T+s*np.sqrt(T)*Z); x=np.exp(-r*T)*np.maximum(ST-K,0); return (x[:N//2]+x[N//2:]).mean()/2
def cv():
    Z=rng.standard_normal(N); ST=S0*np.exp((r-s*s/2)*T+s*np.sqrt(T)*Z); x=np.exp(-r*T)*np.maximum(ST-K,0); c=np.exp(-r*T)*ST
    beta=np.cov(x,c)[0,1]/c.var(); return (x-beta*(c-S0)).mean()
for nm,f in [('plain',plain),('antithetic',anti),('control variate (discounted S_T, known mean S0)',cv)]:
    est=np.array([f() for _ in range(reps)]); out.append(f"O2 BS call MC N={N}: {nm:<46} mean {est.mean():.4f} (true {true:.4f}), sd {est.std():.4f}")
# importance sampling tail: P(30-day return < -20%) with sigma 20%/yr
T2=30/365; thr=np.log(0.8); mu=(r-s*s/2)*T2; sd=s*np.sqrt(T2); truep=norm.cdf((thr-mu)/sd)
Z=rng.standard_normal(100000); plain_p=np.mean(mu+sd*Z<thr)
shift=(thr-mu)/sd; Zs=rng.standard_normal(100000)+shift; w=np.exp(-shift*Zs+shift**2/2); is_p=np.mean((mu+sd*Zs<thr)*w)
out.append(f"O2 importance sampling P(30-day drop >20%, σ=20%): true {truep:.2e}; plain MC (100k) {plain_p:.2e}; IS with mean shift (100k) {is_p:.2e} (relative error {abs(is_p/truep-1):.1%})")
# O3 Bayesian strategy evaluation
for w_,n_ in [(55,100),(110,200),(550,1000)]:
    a,b2=1+w_,1+n_-w_; out.append(f"O3 {w_}/{n_} winning trades (even payoff), flat prior: P(true win rate > 50%) = {1-stats.beta.cdf(0.5,a,b2):.1%}; 95% interval [{stats.beta.ppf(.025,a,b2):.3f}, {stats.beta.ppf(.975,a,b2):.3f}]")
# skeptical prior: most strategies have no edge — prior on win rate N(0.5, 0.01)
for w_,n_ in [(55,100),(550,1000)]:
    a0=b0=1250   # Beta(1250,1250): sd ≈ 0.01
    out.append(f"   with skeptical prior Beta(1250,1250) (sd 1pt around 50%): {w_}/{n_} → posterior mean {(a0+w_)/(a0+b0+n_):.3f}, P(>50%) {1-stats.beta.cdf(0.5,a0+w_,b0+n_-w_):.1%}")
# SPRT: detect that a strategy with edge 55% decayed to 50%
A,B=np.log((1-0.05)/0.05),np.log(0.05/(1-0.05))   # alpha=beta=5%
def sprt(true_p):
    llr=0;n=0
    while B<llr<A:
        x=rng.random()<true_p; n+=1; llr+=np.log((0.5 if x else 0.5)/(0.55 if x else 0.45))
    return n, llr>=A
res=[sprt(0.5) for _ in range(3000)]; res2=[sprt(0.55) for _ in range(3000)]
out.append(f"O3 SPRT 'edge gone (50%)' vs 'edge intact (55%)', α=β=5%: if edge really gone → flags after median {np.median([r[0] for r in res]):.0f} trades (correct {np.mean([r[1] for r in res]):.0%}); if edge intact → false alarm {np.mean([r[1] for r in res2]):.1%}, median {np.median([r[0] for r in res2]):.0f} trades")
txt="\n".join(out); print(txt); open(f'{R}/notes/o123_out.txt','w').write(txt)
