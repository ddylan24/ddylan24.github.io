# E1/E2 — Portfolio math (Ken French 30 value-weighted industries, monthly 1963-07→2026-08, RF from FF file)
Math: tangency w ∝ Σ⁻¹μ (max Sharpe); min-variance w ∝ Σ⁻¹1; inverse-vol w_i ∝ 1/σ_i; Ledoit–Wolf shrinkage Σ̂ = δF + (1−δ)S (optimal δ analytic).
Why MV fails: errors in μ dominate (Merton 1980: mean precision depends on calendar span; σ on frequency); Σ⁻¹ amplifies noise along small-eigenvalue directions → extreme long/short.
Rolling 120m estimation, OOS 1973-07→2026-08 (638 months):
- 1/N: Sharpe .51, vol 16.7%, worst −26.1%
- sample tangency (vol-matched to 1/N): .23, gross lev 9.98 (raw sum-normalized version blew up: avg gross 33.9)
- tangency w/ LW cov (vol-matched): .28, gross lev 6.85
- tangency clipped long-only (LW): .53
- min-variance sample: .47 (lev 4.14); min-variance LW: .55 (best), vol 12.5%, worst −12.2%, lev 2.93
- inverse-vol: .52
- IN-SAMPLE tangency (hindsight): .90 ← the fantasy
Matches DeMiguel, Garlappi & Uppal (2009): 1/N hard to beat; estimation error in means destroys MV gains. Structure that helps: shrink covariance, ignore expected returns (min-var), or constrain.
E2 PCA/RMT (30 industries daily, last 504 days): top eigenvalue 12.3 → 41% of variance (market mode); next 3.93, 1.81, 1.49. Marchenko–Pastur λ± = (1±√(N/T))²: λ+ = 1.55; only 3 of 30 eigenvalues exceed it. Pure-noise control: max 1.47, min 0.62 (theory 1.55/0.57) ✓. Laloux et al. 1999; Plerou et al. 2002: most of a sample correlation matrix is noise → clip eigenvalues below λ+ ("eigenvalue clipping") before inverting.
