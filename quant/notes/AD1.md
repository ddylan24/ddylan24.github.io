# AD1: commodity 15-minute markets (gold, WTI, silver), 7 days, marked to settlement

Script: `code/ad_series_edge.py . 7 KXGOLD15M,KXWTI15M,KXSILVER15M ad1` (raw output `AD1_out.txt`). Same method as AD2: every public fill in settled markets, maker P&L to settlement (taker YES at P → P − y; taker NO → y − P), SE clustered by market.

| series | markets | contracts | maker ¢/ct ± SE | z | LIP pool |
|---|---|---|---|---|---|
| KXGOLD15M | 447 | 174.5M | +0.47 ± 0.15 | 3.1 | $0 |
| KXWTI15M | 498 | 52.3M | +0.59 ± 0.16 | 3.7 | $0 |
| KXSILVER15M | 450 | 22.4M | −0.07 ± 0.23 | −0.3 | $0 |

Daily maker ¢/ct was positive on 6 of 7 days for gold and 6 of 8 for WTI; silver alternated in sign.

## Takeaways
- AC1's 4-day commodities +0.98 ± 0.22 shrinks to about +0.5 over 7 days but **survives** for gold and WTI. Silver does not.
- **There is no LIP pool on these series**, so this is pure spread capture. It's an *average over all makers*. The fast makers who pull before moves may be earning more, and a slow home-PC maker may be earning less (the crypto 15m lesson, AC2: large takers are informed). Unlike weather, this needs a fast, settlement-matching price feed (SPEED.md §3; Y3 showed substitute feeds fail).
- Ranking unchanged: KXTEMPMIAH (reward + edge, slow is fine) stays first. Gold/WTI 15m are a **second candidate** that needs speed infrastructure and a size test (edge by trade size) before any work.
