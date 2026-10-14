"""T2: market making a binary contract, calibrated to Polymarket's measured dynamics.
Fair value: logit-space diffusion matching S9 (daily sd of p = 0.94·φ(N⁻¹p)/τ^0.53) plus jumps (S10: rare 20–50¢ moves).
Uninformed takers arrive per side with intensity A·e^(−k·δ) (δ = distance from fair value). At a jump, quotes are stale for one
step: the side now in the money is picked off for the full quote size (adverse selection).
Strategies: (a) fixed half-spread 1¢; (b) half-spread ∝ local vol; (c) (b) + Avellaneda–Stoikov inventory skew r = p − q·γ·σ²."""
import sys, numpy as np
from scipy.stats import norm
R = sys.argv[1]; out = []
rng = np.random.default_rng(11)
NP, DAYS, STEPS = 400, 30, 24 * 12            # 400 paths, 30 days, 5-minute steps
dt = 1 / STEPS; A, k, Q = 0.6, 120.0, 100.0   # arrivals/step at δ=0, decay per $ of distance, contracts per fill
LAM = 0.004                                    # jumps per day (S10: ~0.1% of days ≥20¢ near the edges; higher mid-range)
def run(strategy, jumps=True, seed=0):
    r = np.random.default_rng(seed)
    p = np.clip(r.uniform(0.2, 0.8, NP), 0.02, 0.98); x = norm.ppf(p)
    cash = np.zeros(NP); inv = np.zeros(NP); picked = np.zeros(NP)
    for i in range(DAYS * STEPS):
        tau = DAYS - i * dt + 0.5
        sd_day = 0.94 * norm.pdf(x) / tau ** 0.53                     # S9 law (probability units per day)
        sd_x = sd_day / np.maximum(norm.pdf(x), 1e-6)                 # same law in probit space
        sig = sd_day * np.sqrt(dt)                                    # per-step sd of p
        if strategy == 'fixed': h = np.full(NP, 0.01); res = p
        elif strategy == 'vol': h = np.maximum(0.005, 3.0 * sig); res = p
        else: h = np.maximum(0.005, 3.0 * sig); res = p - inv / Q * 0.5 * sig * 4
        bid, ask = np.clip(res - h, 0.001, 0.999), np.clip(res + h, 0.001, 0.999)
        # uninformed fills
        fb = r.random(NP) < A * np.exp(-k * np.maximum(p - bid, 0)) * dt * STEPS / STEPS
        fa = r.random(NP) < A * np.exp(-k * np.maximum(ask - p, 0)) * dt * STEPS / STEPS
        inv += Q * fb - Q * fa; cash += -Q * bid * fb + Q * ask * fa
        # fair-value move: diffusion + jumps
        x = x + sd_x * np.sqrt(dt) * r.standard_normal(NP)
        if jumps:
            J = r.random(NP) < LAM * dt
            if J.any():
                newp = np.where(norm.cdf(x[J]) > 0.5, norm.cdf(x[J]) - r.uniform(0.2, 0.5, J.sum()), norm.cdf(x[J]) + r.uniform(0.2, 0.5, J.sum()))
                newp = np.clip(newp, 0.01, 0.99)
                up = newp > norm.cdf(x[J])                             # stale ask hit on up-jumps, stale bid on down-jumps
                idx = np.where(J)[0]
                inv[idx] += np.where(up, -Q, Q); cash[idx] += np.where(up, Q * ask[idx], -Q * bid[idx])
                picked[idx] += Q * np.abs(newp - np.where(up, ask[idx], bid[idx]))
                x[idx] = norm.ppf(newp)
        x = np.clip(x, -3.5, 3.5); p = norm.cdf(x)
    y = (r.random(NP) < p).astype(float)
    pnl = cash + inv * y
    return pnl, picked
out.append(f"{NP} simulated 30-day binaries, 5-min steps; quote size {Q:.0f}; jump rate {LAM}/day (20–50¢); P&L in $ at resolution")
for strat in ('fixed', 'vol', 'vol+skew'):
    for J in (False, True):
        pnl, pk = run(strat, J, seed=1)
        out.append(f"  {strat:<9} jumps={str(J):<5}: mean ${pnl.mean():7.1f}  sd ${pnl.std():7.1f}  Sharpe/market {pnl.mean()/pnl.std():+.2f}  5% worst ${np.percentile(pnl,5):7.1f}  picked-off loss ${pk.mean():5.1f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/t2_out.txt", "w").write(txt)
