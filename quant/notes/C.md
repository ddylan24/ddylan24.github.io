# C — Volatility models (CRSP market via Ken French; daily % log returns)
EWMA (RiskMetrics): σ²_t = λσ²_{t−1} + (1−λ)r²_{t−1}, λ=0.94.
GARCH(1,1): σ²_t = ω + α r²_{t−1} + β σ²_{t−1}. Persistence α+β; shock half-life ln(.5)/ln(α+β); long-run var ω/(1−α−β).
GJR: + γ·r²_{t−1}·1[r_{t−1}<0] (leverage effect).
Results:
- GARCH-t 1926–2026: α=.1007 β=.8961 (α+β=.9968), ν=5.5, shock half-life 216 days; implied long-run vol 26.4% (unstable when α+β≈1 and 1930s in sample).
- Standardization: kurtosis 20.0 → 8.5; |z|>5 days 104 → 31. Most, not all, fat-tailedness is volatility clustering; the rest = jumps (1987).
- GJR-skew-t 1990–2026: α=.0013, γ=.174, β=.895 → up-shocks barely move vol; down-shocks drive it. Strong leverage/asymmetry effect.
- 99% VaR 1991–2026 (expect 90): normal-1y 216, hist-1y 146, t-1y 143, EWMA-normal 183, GARCH-t (refit yearly, no look-ahead) 134 (Kupiec 19.1 – still rejects but best). Remaining misses = jumps and asymmetry.
Moreira–Muir replication (monthly, w ∝ 1/RV_{t−1}, scaled to market vol), CRSP 1926–2026: Sharpe .52 vs .45; alpha 4.36%/yr (HAC t=2.74), beta .62. 1926–1999: alpha t 2.55, max leverage 15.2x. 2000–2026: Sharpe .51 vs .48, alpha t 1.20 (not significant), max lev 6x. → Effect real in long sample but weaker recently and requires extreme leverage at times; Cederburg, O'Doherty, Wang & Yan (JFE 2020) found vol-managed portfolios often fail out-of-sample in real-time implementations.
