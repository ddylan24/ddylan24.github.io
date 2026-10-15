# Kalshi Liquidity Incentive Program (LIP): rules, live census, and LP economics

**Sources (primary):**
- Kalshi help center, "Liquidity Incentive Program" (help.kalshi.com/en/articles/13823851, read 2026-10-15) and "Liquidity incentive programs: where to find them" (…/16076644).
- CFTC self-certifications by KalshiEX: Feb 11 2026 amendment (rules02112639183.pdf, full formula); Aug 2026 FOOTBALLSTATS component-legs LIP (rules08112615711/08122616003); Sep 15 2026 Deposit & Trading Reward program (rules09152625924, a separate program).
- Live public API `GET /trade-api/v2/incentive_programs?status=active`.

## Rules
- **Purpose:** pay members for *resting* orders that deepen the central limit order book, even if they never fill.
- **Dates:** the help center now says the program **ends January 1, 2027** (extended from September 1, 2026; the Aug-2026 FOOTBALLSTATS filing also says Jan 1, 2027). Kalshi can modify or terminate it at any time.
- **Eligibility:** most U.S. members. Excluded: Kalshi affiliates and employees, IBs/FCMs and their customers, non-U.S. users, and (per the filing) members with a Market Maker Agreement.
- **Per Time Period** (≤31 days, can overlap):
  - Target Size: 100 < T < 20,000 contracts. Live values: 300, 500, 1,000, 2,500.
  - Discount Factor DF ≤ 1. Live values 0.40–0.50.
  - Time Period Reward: $10–$1,000 per calendar day in the filing; the help center says $1–$1,000.
- **Snapshots:** once per second at a random moment within the second, only while the market is open.
  - A snapshot is **excluded unless both the YES side and the NO side reach Target Size** (two-sided). A YES ask counts as a NO bid.
- **Per side:**
  - **Qualifying bids:** walk down from the best bid, adding *whole price levels*, until cumulative size ≥ T. If the book runs out first, nothing on that side qualifies.
  - **Reference price.**
    - Feb-2026 filing: the best bid.
    - Current help center: the first level where cumulative size reaches **T/5** ("a small order alone at the top does not set it").
    - Orders at or better than the reference get full credit.
  - **Score(bid) = DF^(ticks below reference) × size**, normalized by the side's total. With DF = 0.5, an order one tick below the reference gets half credit and two ticks below a quarter.
- **Snapshot score per user** = YES-side share + NO-side share (≤ 2 summed over everyone).
- **Payout:** (user's Σ snapshot scores ÷ everyone's Σ) × Time Period Reward × (non-excluded snapshots ÷ total snapshots), rounded down to the cent. Paid only if ≥ $1, after the period ends, in a later processing run.
  - Help-center example: $100 reward, 8,000 of 10,000 snapshots two-sided, 20% share → $16.
- **API units:** `period_reward` is in 1/10,000 $ (1,000,000 = $100). `discount_factor_bps`/10⁴ = DF. `target_size_fp` = T.

## Live census (2026-10-15 00:14 UTC; `code/lip_kalshi.py`)
- **5,734 markets in 556 series** have live liquidity programs, **≈$129k/day from programs lasting ≥1 day** (the $324k/day first reported summed *rates* of 1-hour programs, which overstates them; see W4). The median pool is **$14/day** per market (mean $57, max $2,400/day as a rate).
- Program types: series_lip 4,864, new_event 761, others.
- Biggest series by $/day: KXTEMPMIAH (hourly Miami temperature) $24k, KXRT $21k, the state gas-price series (KXAAAGASD**) $7–11k each, KXTRUMPMENTIONB $7.5k.
- Typical period: 7 days. Hourly weather programs run about 1 hour at about $100 each.

## What would a new LP earn? (static-book simulation, top 250 programs by $/day)
- Method: add Q contracts at the current best bid on both sides, recompute the official score with level-based walks and the T/5 reference, and take your share × reward rate. Assumes the book stays as it is.
- **Bug caught:** an order-by-order walk cut off a new order at a shared price level, giving 0% share. The rule adds whole levels.
- 68% of these books were two-sided at Target. In the other 81 markets ($35k/day of rewards), whoever first makes the book two-sided collects almost the whole pool, but must post T on *both* sides.

| Q per side | median share | median $/day | capital | simple return |
|---|---|---|---|---|
| 100 | 4.3% | $12 | $90 | 18.7%/day |
| 500 | 19% | $61 | $450 | 18.0%/day |
| Target | 34% | $112 | $850 | 14.9%/day |
| *programs ≥ 1 day only (n = 15)* | 26% (Target) | $154 | $990 | 15.6%/day (25th pct 2.2%) |

## Why these numbers are an upper bound
1. **Static book.** Other LPs re-quote. Shares get competed down until the reward roughly equals LPs' costs (capital, adverse selection, inventory risk). The live books are already crowded where pools are rich: median spread 1¢ in the ≥1-day programs.
2. **Adverse selection.** A resting best bid fills exactly when the price is moving through it. The richest pools are hourly weather contracts, where takers can watch live station readings and you're the stale quote (cf. Q2, R4, T2: jumps cost about $4 per market-month in the sim; S10: favorites crash 39× more often than diffusion predicts).
3. **Inventory to resolution.** Fills turn into 0/1 positions. T2 showed inventory risk dominates a binary maker's P&L unless quotes are skewed.
4. **Short programs inflate a "per day" rate.** A 1-hour, $100 program is $2,400/day only during that hour.
5. Rounding below $1 (not paid), excluded one-sided snapshots, and possible rule changes before 2027.

## How to think about it (quant view)
- The LIP is a **subsidy for depth, not tightness**. Scoring is relative to the best bid and reference, not to fair value. In wide books (some gas-price markets show a 1¢ YES bid against a 60¢+ NO bid), an LP can earn full credit without quoting near fair value. Competitors then outbid by a tick and capture the reference, which drives quotes inward. That's the design intent.
- **The edge is market making plus rewards:** quote both sides (needed anyway for two-sided snapshots), skew by inventory (T2), widen or pull before scheduled information (Q2), avoid near-expiry contracts with live public data (weather), and size so that rewards exceed measured adverse selection.
- **Home-PC test (added to PLAYBOOK):** log `incentive_programs` and full order books (`live/capture.py`), then paper-quote with a queue-position fill model for ≥4 weeks. Compare simulated rewards vs fill losses per series. Only then consider small live size with the user's approval.
