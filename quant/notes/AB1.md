# AB1: Does the hourly-temperature maker edge generalize to other Kalshi weather series?

**Method (`code/ab1_weather_makers.py`).** The 7 most recent days of settled markets in the six daily-high series (KXHIGHNY/CHI/MIA/LAX/AUS/DEN, 42 bucket markets each) and KXRAIN (225 markets). Every public fill marked to settlement; market-clustered bootstrap SEs.

| series | contracts | maker ¢/contract ± se |
|---|---|---|
| KXHIGHLAX | 3.65M | +1.70 ± 0.80 |
| KXHIGHNY | 1.30M | +1.58 ± 1.99 |
| KXHIGHAUS | 0.42M | +1.50 ± 1.04 |
| KXHIGHCHI | 0.87M | +1.01 ± 0.85 |
| KXHIGHMIA | 0.97M | +0.57 ± 0.64 |
| KXHIGHDEN | 0.32M | −0.95 ± 0.96 |
| **pooled daily highs** | 7.5M | **+0.81 ± 0.36 (z 2.2)**, heterogeneity n.s. |
| KXRAIN | 7.89M | −0.50 ± 0.50 |

## Interpretation
- **Makers in Kalshi temperature markets earn about +0.8–1.2¢ per contract on fills** (daily highs pooled +0.81¢, z 2.2; hourly Miami +1.24¢, z 3.7). Takers in weather markets are on average *uninformed* betting flow. That's consistent with N2's classic favorite-longshot bias in weather buckets, since overpriced longshots get bought by takers and sold by makers.
- Rain markets show no maker edge (−0.5 ± 0.5¢).
- Only 42 markets per city (7 days × 6 buckets), so individual cities are noisy. The pooled result is the one to use.
- **Implication:** weather is the category where passive liquidity provision on Kalshi is paid twice, on fills and (where offered) via LIP. Daily-high series currently carry little LIP, so the fill edge alone is about 1¢ per contract before any reward.
