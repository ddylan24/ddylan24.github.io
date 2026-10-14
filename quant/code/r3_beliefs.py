"""R3: when does a prediction-market price equal the mean belief? (Manski 2006 vs Wolfers-Zitzewitz 2006 / Gjerstad 2005)
Traders with CRRA(γ) utility, beliefs q_i, wealth w_i, trade a binary contract in zero net supply.
Optimal YES demand: x = w (k−1)/(1−p+kp),  k = [q(1−p)/((1−q)p)]^(1/γ).   Log utility (γ=1): x = w(q−p)/(p(1−p)) ⇒ p = wealth-weighted mean q."""
import sys, numpy as np
from scipy.optimize import brentq
from scipy.stats import beta
R = sys.argv[1]; out = []; rng = np.random.default_rng(7)
def demand(q, p, w, g):
    k = (q * (1 - p) / ((1 - q) * p)) ** (1 / g); return w * (k - 1) / (1 - p + k * p)
def price(q, w, g):
    return brentq(lambda p: demand(q, p, w, g).sum(), 1e-6, 1 - 1e-6, xtol=1e-12)
def manski(q):           # risk-neutral, equal wealth: p = share of traders with q > p
    return brentq(lambda p: (q > p).mean() - p, 1e-9, 1 - 1e-9)
N = 20000
out.append("1) Log utility, equal wealth: price = mean belief exactly")
q = beta(2, 5).rvs(N, random_state=rng); out.append(f"   beliefs Beta(2,5): mean {q.mean():.4f}, price {price(q, np.ones(N), 1.0):.4f}")
out.append("\n2) Price − mean belief (¢) by risk aversion γ and belief dispersion (Beta beliefs with given mean, equal wealth):")
out.append("   mean  disp(sd) " + "".join(f"  γ={g:<5}" for g in [0.1, 0.5, 1, 2, 5]) + "  risk-neutral(Manski)")
for m in [0.05, 0.2, 0.5, 0.8]:
    for sd in [0.02, 0.1]:
        v = sd ** 2; c = m * (1 - m) / v - 1
        if c <= 0: continue
        q = np.clip(beta(m * c, (1 - m) * c).rvs(N, random_state=rng), 1e-4, 1 - 1e-4)
        row = [100 * (price(q, np.ones(N), g) - q.mean()) for g in [0.1, 0.5, 1, 2, 5]]
        out.append(f"   {m:.2f}  {sd:.2f}    " + "".join(f"  {x:+6.2f} " for x in row) + f"  {100*(manski(q)-q.mean()):+6.2f}")
out.append("\n3) Manski bound: with risk-neutral equal-wealth traders the price π is the (1−π) quantile of beliefs,")
out.append("   so the mean belief can be anywhere in (π², 2π − π²):")
for pi in [0.05, 0.1, 0.3, 0.5, 0.9]: out.append(f"   price {pi:.2f} → mean belief in ({pi*pi:.4f}, {2*pi-pi*pi:.4f})")
# extreme example: few optimists vs many mild pessimists
q = np.r_[np.full(1000, 0.9), np.full(9000, 0.02)]
out.append(f"   example: 10% believe 0.90, 90% believe 0.02 → mean {q.mean():.3f}; Manski price {manski(q):.3f}; log-utility price {price(q, np.ones(len(q)), 1):.3f}; γ=0.2 price {price(q, np.ones(len(q)), 0.2):.3f}")
out.append("\n4) Wealth matters: log-utility price = wealth-weighted mean. If wealth correlates with belief, price ≠ simple mean:")
q = beta(2, 5).rvs(N, random_state=rng); w = np.exp(rng.normal(0, 1, N) + 2.0 * (q - q.mean()) / q.std() * 0.5)
out.append(f"   corr(wealth, belief) {np.corrcoef(w, q)[0,1]:.2f}: simple mean {q.mean():.4f}, wealth-weighted {np.average(q, weights=w):.4f}, price {price(q, w, 1):.4f}")
out.append("\n5) Longshot pricing vs risk aversion (γ<1 = less risk-averse than log, trades more aggressively), beliefs mean 0.05:")
for g in [0.3, 1, 3]:
    q = np.clip(beta(0.05 * 20, 0.95 * 20).rvs(N, random_state=rng), 1e-4, 1 - 1e-4)
    out.append(f"   γ={g}: beliefs mean {q.mean():.4f} (sd {q.std():.3f}) → price {price(q, np.ones(N), g):.4f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/r3_out.txt", "w").write(txt)
