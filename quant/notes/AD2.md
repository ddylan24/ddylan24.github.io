# AD2: Weather maker edge over 14 days (resolving the AC1 vs AA1/AB1 conflict)

**Method.** `code/ad_series_edge.py . 14 KXTEMPMIAH,KXHIGH*`: every settled market in 14 days, all public fills marked to settlement, market-clustered bootstrap SEs, LIP pools on the same markets.

| series | markets | contracts | maker ¢/contract ± se | LIP reward ¢/contract |
|---|---|---|---|---|
| **KXTEMPMIAH (hourly)** | 2,174 | 5.13M | **+0.69 ± 0.22 (z 3.1)** | **4.21** |
| KXHIGHLAX | 84 | 8.55M | +1.26 ± 0.56 | 0 |
| KXHIGHCHI | 84 | 1.55M | +1.00 ± 0.57 | 0 |
| KXHIGHNY | 84 | 2.37M | +0.94 ± 1.28 | 0 |
| KXHIGHAUS | 84 | 0.88M | +0.42 ± 0.90 | 0 |
| KXHIGHMIA | 84 | 1.78M | +0.02 ± 0.62 | 0 |
| KXHIGHDEN | 84 | 0.65M | **−1.47 ± 0.70** | 0 |
| daily highs pooled | 504 | 15.8M | +0.41 ± 0.28 (z 1.5), Q 11.2/5 df | |

## Conclusions
- **The hourly-temperature maker edge is robust over 14 days:** +0.69¢/contract (z 3.1), about half the 7-day estimate (+1.24¢), in line with the AA2 shrinkage (+0.58¢). Together with **4.2¢/contract of LIP reward**, it stays the best LIP candidate. Net per filled contract ≈ +4.9¢.
- **Daily highs are marginal and city-specific:** pooled +0.41¢ (z 1.5), with real heterogeneity (Denver negative, LA positive) and no LIP rewards. Not a priority.
- AC1's negative weather figure came from a 4-day top-volume sample. The longer, complete-series test supersedes it.
