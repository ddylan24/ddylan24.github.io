"""W3: equilibrium of a proportional liquidity subsidy (Kalshi LIP ≈ Tullock contest).
LP i rests depth q_i; reward share q_i/Σq (all at the reference price); per-contract daily cost k (capital + adverse selection + risk).
  π_i = R·q_i/Q − k·q_i.  FOC: R(Q − q_i)/Q² = k.  Symmetric n LPs: Q* = R(n−1)/(n k), q* = Q*/n, π* = R/n²,
  return on cost = π*/(k q*) = 1/(n−1);  free entry (n→∞): R = k·Q  — the subsidy is fully dissipated into depth.
So observed depth Q_obs implies k ≈ R/Q_obs (an upper bound if few LPs compete). Uses the live LIP sample (sim.csv)."""
import sys, numpy as np, pandas as pd
from scipy.optimize import brentq
R_ = sys.argv[1]; out = []
# 1) numeric check of the symmetric Nash equilibrium by best-response iteration
R, k = 100.0, 0.02
for n in (2, 3, 5, 10):
    q = np.ones(n)
    for _ in range(500):
        for i in range(n):
            O = q.sum() - q[i]; q[i] = max(np.sqrt(R * O / k) - O, 0)       # best response: argmax R q/(q+O) − k q
    Q = q.sum(); pi = R * q / Q - k * q
    out.append(f"n={n:2d}: best-response Q {Q:8.1f} vs formula R(n−1)/(nk) {R*(n-1)/(n*k):8.1f}; profit/LP {pi.mean():6.2f} vs R/n² {R/n**2:6.2f}; return on cost {pi.mean()/(k*q.mean()):.2f} vs 1/(n−1) {1/(n-1):.2f}")
# 2) implied per-contract cost from live books
B = pd.read_csv(f"{R_}/data/lip/sim.csv")
B = B[B.both_now == True].copy()
# existing qualifying depth ≈ newcomer share relation: share s with q added ⇒ existing effective depth E = q(1−s)/s (per side, at reference)
B['E_T'] = B.target * (1 - B.share_T) / B.share_T.replace(0, np.nan)
B['k_implied'] = B.per_day / (2 * B.E_T)                       # $ per contract-day per side if free entry held
out.append(f"\nLive LIP books (two-sided, n {len(B)}): effective existing depth per side median {B.E_T.median():,.0f} contracts (target median {B.target.median():.0f})")
out.append(f"  implied free-entry cost k = reward/(2·depth): median {100*B.k_implied.median():.2f}¢ per contract-day; IQR {100*B.k_implied.quantile(.25):.2f}–{100*B.k_implied.quantile(.75):.2f}¢")
out.append(f"  compare capital cost alone at 10%/yr on ~$0.50 per contract: {100*0.5*0.10/365:.4f}¢/day → implied k is ~{B.k_implied.median()/(0.5*0.10/365):,.0f}× capital cost")
out.append("  ⇒ depth is NOT limited by capital: either LPs price large adverse-selection/inventory risk, the pool of active LPs is small (n low → return 1/(n−1)),")
out.append("    or rewards are short-lived (hourly programs) so few bother. With n LPs, R/(k·Q) = n/(n−1): observed returns ≫ cost ⇒ effectively small n.")
txt = "\n".join(out); print(txt); open(f"{R_}/notes/w3_out.txt", "w").write(txt)
