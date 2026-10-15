# AA1 + AA3: Kalshi hourly Miami temperature (KXTEMPMIAH). Who wins, and can a thermometer model price it?

**Contract.** "Temperature at Miami, FL at HH:00 (local) above K?", resolved on **Synoptic Data** to a tenth of a degree (e.g., 82.40°F) under Kalshi's Weather Index Methodology. Each market opens one hour before the hour. Several strikes per hour.

**Data.** 7 days: 1,085 settled markets, 111,790 public fills, 2.85M contracts, each marked to settlement. Live-information proxy: NWS ASOS **1-minute** temperatures at KMIA from the IEM archive (`asos1min.py`; integer °F; 'M' marks missing values, which must be coerced). Scripts: `code/aa1_tempmiah.py`, `code/aa3_temp_diffusion.py`.

## AA1: makers win, especially late
| minutes before close | contracts | maker P&L per contract |
|---|---|---|
| last 5 | 315k | **+2.73¢** |
| 5–15 | 566k | **+3.15¢** |
| 15–30 | 703k | +0.75¢ |
| 30–60 | 1.27M | +0.28¢ |
| **all** | 2.85M | **+1.24¢** ($+35k) |

- **Late takers "reading the thermometer" lose.** In the last 15 minutes, takers whose side *agrees* with the latest 1-minute reading vs the strike lose **4.7¢** per contract to makers; takers who disagree lose 2.6¢.
- The public reading is already in the price, and the residual (tenths vs integer degrees, the exact Synoptic timestamp, a degree of drift in the last minutes) favors the patient side.
- The latest 1-minute reading 10 minutes before the close called the outcome only **66%** of the time, so the public feed is a weak signal for these contracts.
- With Z1 (5.8¢ of LIP reward per filled contract), KXTEMPMIAH is the most attractive LIP series found so far: **makers earn on fills and on rewards**.

## AA3: a diffusion model of temperature fails
- Empirical model: ΔT over τ minutes by target hour, with σ(60 min) = 1.34°F and σ(10 min) = 0.66°F. P(YES) = 1 − Φ((K − T_now − μ)/√(σ² + 1/12)).
- **Brier: model 0.224 vs market fill prices 0.078.** It's worse at every horizon, and trading toward it loses 2.2–2.8¢ per contract.
- Why: the same lesson as Y3. The archived ASOS 1-minute feed (integer °F, gappy, a different sensor pipeline) isn't the settlement source (Synoptic, tenths). Near the hour, a few tenths of a degree decide the market. You need the exact settlement feed live.

## Lessons
1. In KXTEMPMIAH the informed side is *not* the takers. Makers profit, most of all in the final 15 minutes.
2. A model built from a near-substitute data feed can be dramatically worse than the market. Always check its calibration against outcomes first (two failures now: Y3 and AA3).
3. Practical: a home-PC LIP quoter on KXTEMPMIAH should earn rewards *and* positive fill P&L if it cancels on the Synoptic/ASOS readings near each hour. That's the top paper-trading candidate.
