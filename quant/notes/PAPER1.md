# PAPER1: first live paper trial (cloud, 2026-10-15 05:55–10:55 UTC, read-only)

Two simulators ran on live Kalshi data for 5 hours. They placed no orders. Raw report: `PAPER1_out.txt`. Event logs were not committed (they stayed in the cloud scratchpad).
- `live/tempmiah_paper.py --size 100 --interval 10`: Miami hourly temperature, JOIN vs SMART.
- `live/lip_paper.py --size 100 --interval 30`: three series, no pull rule.

## Results
| sim / policy | reward | fill P&L (settled) | net | contracts filled |
|---|---|---|---|---|
| tempmiah JOIN | $74.57 | −$211.41 | **−$136.84** | 11,445 |
| tempmiah SMART | $54.77 | −$256.75 | **−$201.98** | 7,387 |
| lip_paper KXTEMPMIAH | $79.13 | −$2,059.30 | **−$1,980.17** | 12,760 |
| lip_paper KXEURUSD15M | $122.00 | −$2,843.37 | **−$2,721.36** | 8,990 |
| lip_paper KXTRUMPAPPROVE | $68.61 | not settled yet | (+$68.61 reward only) | 11,209 |

Miami fill P&L by settlement hour (UTC):

| hour | JOIN | SMART | lip_paper |
|---|---|---|---|
| 02 | +656 | 0 | +338 |
| 03 | −546 | −68 | −1,389 |
| 06 | −322 | −189 | −1,008 |
| 07 | 0 | 0 | 0 |

## What it means
- **Paper fills lost money, which contradicts the +0.69¢ historical maker edge (AD2).** JOIN lost about −1.8¢/contract; lip_paper (30s cycle, no pull rule) lost about −16¢/contract.
- **Only 3 hours had fills, and one or two hours drive everything.** This is far too few to estimate an edge: the historical edge needed 14 days and clustering by market to reach z 3.1. Treat PAPER1 as a **warning sign, not a verdict**.
- **The simulator's fill model is adverse by construction.** A resting bid fills only when a trade prints *through* it or exceeds the queue ahead, using the quotes from the previous cycle. So the sim gets the picked-off fills and misses most of the benign ones. Positions also have **no inventory cap**: a whole hour's flow can pile onto one strike (hour 03, lip_paper −$1,389). The historical number averages over all makers' fills, so the two aren't directly comparable.
- **SMART helped in a bad hour** (03: −68 vs −546) but sat out the good one (02), and still lost in hour 06. The 20-minute / 1°F rule isn't enough on its own.
- **Reward accrual ≈ $15/hour per side-pair at 100 contracts** across ~10 Miami strikes, which is small next to the fill swings at this size.
- **EUR/USD 15m is confirmed bad** (as in X1/Y1): rewards don't cover fills.

## Next steps (for the home-PC session; folded into HANDOFF task A/B)
1. Settle the conflict with **history, not more cloud hours**: on stored trades and books, compute maker P&L *for a hypothetical quote at the touch* (fills only from trades at or through the price, as in this sim) and compare it with the all-maker average. If the touch-quote P&L is negative, the AD2 edge belongs to makers who quote off the touch or pull faster, and the strategy has to copy that.
2. Add an **inventory cap per strike and per hour** to both sims, and skew quotes by inventory (T2).
3. Test pull rules with a wider band / earlier window, and "step back one tick" instead of pulling (SPEED §4), on history with a hold-out.
