# AA2: Which series' maker edges survive partial pooling?

**Method (`code/aa2_shrink.py`).**
- Maker fill P&L to settlement per contract, 7 days (AA1 for KXTEMPMIAH, Y1 for the 15-minute series).
- SE by cluster bootstrap over markets.
- DerSimonian–Laird τ² and empirical-Bayes posterior means b̃ = μ̂ + τ²/(τ²+s²)(b̂ − μ̂) (U3 method).

| series | markets | raw ¢/contract ± se | z | shrunk |
|---|---|---|---|---|
| **KXTEMPMIAH** | 1,085 | **+1.24 ± 0.33** | **+3.7** | **+0.58** |
| KXUSDJPY15M | 472 | +1.03 ± 1.01 | +1.0 | +0.27 |
| KXETH15M | 666 | +0.22 ± 0.09 | +2.3 | +0.22 |
| KXEURUSD15M | 471 | +0.09 ± 0.37 | +0.2 | +0.18 |
| KXAUDUSD15M | 472 | −0.36 ± 0.51 | −0.7 | +0.12 |
| KXBTC15M | 665 | −0.01 ± 0.01 | −0.5 | −0.01 |

- Pooled μ̂ = +0.23¢, τ̂ = 0.25¢, **Cochran Q = 20.7 on 5 df (p ≈ 0.001)**. Unlike the weather-city slopes (U3, τ = 0), the series really do differ.
- **KXTEMPMIAH stays on top after shrinkage (+0.58¢)** and is the only series individually significant (z 3.7). JPY's +1.03¢ is mostly noise and shrinks to +0.27¢. ETH is small but precise (+0.22¢).
- **Practical:** expect maker fills to be about break-even to slightly positive (≈ +0.2¢) across 15-minute series. Temperature is the stand-out. The LIP reward, not fill P&L, is the main income except in KXTEMPMIAH, where both contribute.
