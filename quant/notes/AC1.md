# AC1: Category map of maker edges on Kalshi (4 days, settlement-marked)

**Method (`code/ac1_categories.py`).**
- All markets settled in the last 4 days with volume (12,410, multivariate combos excluded), joined to series categories (15,105 series via `GET /series`).
- Per category, the **150 most-traded** markets. This tilts toward liquid markets, and some categories had fewer settled markets than that.
- All public fills marked to settlement; market-clustered bootstrap SEs.

| category | markets | contracts | maker ¢/contract ± se | top series |
|---|---|---|---|---|
| **Commodities** | 150 | 32.5M | **+0.98 ± 0.22** | KXGOLD15M, KXWTI15M, KXSILVER15M |
| Sports | 150 | 102M | +0.50 ± 0.82 | KXUCLGAME, ATP Challenger, ITF matches |
| Crypto | 150 | 89M | +0.13 ± 0.08 | KXBTC15M, KXBTCD, KXETH15M |
| Climate & Weather | 150 | 0.58M | −0.74 ± 0.76 | KXTEMPMIAH, KXTEMPNYCHS, KXTEMPLAXHS |
| Financials | 150 | 3.3M | −0.87 ± 3.47 | KXINXU, KXNASDAQ100U, KXEURUSD15M |
| Mentions | 150 | 2.3M | −1.06 ± 1.73 | Trump mentions, world-news mentions |
| Science & Tech | 52 | 0.19M | −2.58 ± 2.16 | Waymo cities, OpenAI, AI spend |
| Economics | 15 | 0.03M | −2.54 ± 2.78 | mortgage rate, unemployment |
| Politics | 34 | 0.44M | **−3.22 ± 1.88** | Trump approval, cabinet exits |

## Interpretation
- **Commodities 15-minute contracts (gold, WTI, silver) are the one category where makers clearly profit** on fills (z ≈ 4.5). That's consistent with retail-style betting flow on short commodity moves. It's worth adding to the LIP shortlist once its rewards are checked.
- **Event/information categories lean negative for makers**: politics (−3.2¢, z −1.7), science & tech, economics and mentions. Takers there plausibly hold information. Take care quoting them.
- **Weather is −0.7 ± 0.8 here** but +0.8 to +1.2¢ (z 2.2–3.7) in the 7-day series studies (AA1/AB1). This 4-day top-volume sample is smaller (0.58M contracts) and mixes in other cities' hourly series, so weight the 7-day, larger-sample results more. Even so, the weather maker edge deserves a longer test before money is committed.
- Sports and crypto (the biggest by volume) are about break-even for makers. Their flow is competitive.
- Entertainment didn't appear (no settled markets with volume in the 4-day window).
