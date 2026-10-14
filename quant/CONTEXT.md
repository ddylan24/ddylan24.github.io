# Quant research context: load this into a new session

This file is a condensed briefing of everything researched in the original session (Oct 13–14, 2026). Paste it, or point a new session at this folder, to continue without re-deriving anything. Every number here was computed from real data or verified by simulation. The topic notes in `notes/` hold the details, and the scripts in `code/` re-run them.

## 1. Goal and starting point

- The user asked to study the **DeltaTrend Trading** YouTube channel, learn quant trading in depth (with heavy emphasis on the **math**), use well-verified data, and build a course: the *Quant Trading Field Manual* (`course/quant-field-manual.html`, also published as a private claude.ai artifact).
- In later sessions the user added **prediction markets** as a research track.

## 2. DeltaTrend / Thomas (from video transcripts the user pasted)

- Thomas describes himself as an applied-physics student at Columbia whose father is an institutional trader. These claims are unverified. He built **QuantPad**, a paid AI tool that writes Pine Script and runs validation. Episode 01 of his series is largely a pitch for it.
- **QP01 "How Trading Is Actually Done":** the retail path (buy a strategy → manual backtest → "psychology" → "never give up") serves sellers. He says strategies made public lose their edge (alpha decay). He coded influencer strategies (TJR, Justin Werlein, ICT) and found them worse than advertised. He says he passed a Topstep challenge on the first try using a strategy he tuned with Monte Carlo to a 93% pass probability.
- **QP02 "Turning Data Into Meaning":** a feature is raw data collapsed into something meaningful.
  - Types by value: continuous, binary, ordinal.
  - Types by purpose: event-defining, contextual, reference, outcome.
  - Logic tree for building a feature: what do I care about → which raw data carries traces of it → which type → which transformation (normalize, ratio, difference, encoding/z-score) → visualize and validate.
  - "Discretion = features engineered mentally but never quantified."
  - Example: prior-day high/low sweeps on ES futures with ATR double-barrier outcomes. Significant in 2023, not over 2022–2025 (512 events).
- **QP03 "STOP Sampling EVERY CANDLE":** event-defining features. Sampling every bar means forecasting noise. Trade-off: event frequency vs sample size. CUSUM with an ATR-scaled threshold. Always compare against a **random-day baseline** (BTC's 2024 drift fooled the naive look). The next step in his series is contextual features.
- **His pipeline:** event → outcome → contextual features → model → signal processing → risk protocol → validate → deploy and monitor.
- Veritasium videos also used: "The Trillion Dollar Equation" (Thorp, Black-Scholes-Merton, Simons/Baum HMMs) and the Markov-chain video (law of large numbers with dependence, Ulam/von Neumann Monte Carlo, PageRank).

## 3. Key findings (all real data unless marked "sim")

### Testing edges
- **SPY sweep replication (daily, 1999–2026):** the bullish sweep had t = 2.18 vs 0, but **−0.006% vs an ordinary day** (it's the market's drift). No edge in any sub-period. Overlapping 10-day outcomes have lag-1 correlation 0.62, which inflates t-stats. Use n_eff ≈ n/(1+2Σρ) or a block bootstrap (≈30% wider confidence interval).
- **Multiple testing:** 42 context filters on 1,555 sweep days gave 6 "significant". Random dates gave 6.1 on average (dependence inflates false positives above α·M = 2.1). The single survivor (price above its 5-day SMA) is generic short-term reversal, present on all days and decaying (t −4.2 → −1.9).
- **Sharpe statistics:** SE(annual SR) ≈ 1/√years. Sampling more often doesn't help. Years needed to be 95% sure the Sharpe is above 0 (MinTRL): SR 0.5 → 10.8 yrs, SR 1 → 2.7, SR 2 → 0.7. SPY 1999–2026: SR 0.44 ± 0.19. Non-normality matters at low frequency and high SR. Lo's autocorrelation correction can be large for smoothed returns.
- **Deflated Sharpe / luck:** expected best Sharpe from N tries on 5 years of data: N=10 → 0.70, 100 → 1.13, 1,000 → 1.46, 10,000 → 1.73. Sim: the best of 826 MA crossovers on a random walk had in-sample SR 1.35 and out-of-sample −0.40.
- **Bootstrap:** iid vs block hardly matters for SPY itself. It matters a lot when the edge clusters by regime (sim: true median drawdown 41%, iid 22%, stationary block 36%).
- **Factor alpha:** industry momentum shows α 3.6% (t 4.4) against FF5, but 0.8% (t 1.5) once MOM is added. AQR TSMOM α 9.7% (t 5.3) for 1985–2026, but 3.7% (t 1.4) since 2010.
- **Fundamental Law** IR ≈ IC·√breadth is exact in sim, but optimistic in reality. Industry momentum: IC 0.067 predicts IR 1.27; realized 0.49. Use mean(IC)/std(IC).
- **James-Stein:** 30 industries' Sharpe dispersion (1927–76) is smaller than noise, so shrink 100% to the mean. The raw estimates predicted 1977–2026 worse than the grand mean.
- **Calendar anomalies:** Monday (t −10.9), turn-of-month (t 7.9) and January small-caps (t 8.0) were strong in 1926–89. **None survive 1990–2026.**

### Price dynamics
- **Itô / volatility drag:** typical growth = μ − ½σ². Leveraged ETFs 2009–2026: UPRO actual 33.0% vs 3×SPY 45.5%. A model of drag plus T-bill financing plus fee gives 34.6% (within 1.6%/yr).
- **OU / mean reversion:** short samples bias the half-life short (true 44 days: 1-year estimate 22, 10-year estimate 41). VIX half-life ~30 trading days (42 → 35 → 20 days across eras). 10y−2y spread: ~2.2 years.
- **HMM (CRSP 1926–1999 fit, tested 2000–2026):**
  - Calm state: +20.5%/yr, σ 9.6%, average length 73 days. Turbulent: −34%/yr, σ 31%, 18 days.
  - Real-time filter: Sharpe 0.36 vs buy-and-hold 0.42. **Smoothed (look-ahead) version: 1.43, which is fake.**
  - Vol-scaled version: 0.47.
- **Fat tails (CRSP 1926–2026):** kurtosis 20. 104 days beyond 5σ vs 0.015 expected under a normal distribution. 1987 was −17.8σ. Hill tail exponent α ≈ 3. 99% VaR breaches (expected 90): normal 216, historical 146, t 143, EWMA 183, GARCH-t 134.
- **GARCH:** α+β = 0.997 (half-life 216 days). Standardizing cuts kurtosis from 20 to 8.5. GJR leverage effect since 1990: up-shocks α ≈ 0.001, down-shocks α+γ ≈ 0.175.
- **Range volatility:** Parkinson is 5.2× and Garman-Klass ~8× more efficient (sim). SPY's overnight gap is 34% of variance. GK+overnight forecasts beat close-to-close by 17% (QLIKE).
- **Fractional differencing:** d = 0.3 makes SPY stationary while keeping 0.98 correlation with the price level (AFML finds ~0.35).

### Strategies replicated
- **Trend (TSMOM):**
  - 15-ETF version 2008–26, 12-month lookback, vol-scaled: Sharpe 0.43. It correlates 0.79 with AQR's published factor (AQR's Sharpe over the same window: 0.41).
  - AQR's Sharpe by era: 1.62 (1985–99) → 1.13 (2000–09) → 0.40 (2010–26).
  - Crisis returns: 2008 +26% (SPY −38%), 2022 +29% (SPY −19%).
  - DSR over 10 variants: 0.84.
- **Vol-managed market (Moreira-Muir, CRSP):** Sharpe 0.52 vs 0.45, α t 2.74 over 1926–2026. Since 2000 α t is only 1.20, and it needed up to 15× leverage.
- **Momentum crashes:**
  - UMD skew −3.0. Worst months: Aug 1932 −53%, Apr 2009 −34%, all during market rallies.
  - Beta is −0.64 after bear markets.
  - Constant-vol momentum: Sharpe 0.45 → 0.87, worst month −29%.
- **Low beta / low vol:** the SML slope is 3.4%/β vs a 7.2% premium. BAB +6.0%/yr (t 2.5). The highest-variance decile has α −10.3%/yr.
- **Value (HML):** −56% from 2006-12 to 2020-09, still below that peak as of 2026-08. Block bootstrap of pre-2007 history: P(drawdown ≥ 56%) = 13%.
- **Currency carry** (FRED FX + OECD 3m rates, 9 currencies vs USD, 2002–2025), long top-3 / short bottom-3:
  - 2.5%/yr, Sharpe 0.35, skew −0.63. 2008: −26.5%.
  - The rate gap earned +3.1%/yr; spot moved only −0.6%/yr.
  - Fama UIP slope −0.13 (t −0.35), vs UIP's −1: the forward-premium puzzle.
  - Correlation with ΔVIX −0.46 (it's short crash risk).
- **Crypto perp funding** (Hyperliquid POST /info fundingHistory, hourly 2023-05→2026-10):
  - BTC averaged 14.1%/yr, positive 87% of hours, lag-1 day autocorrelation 0.82.
  - By year (BTC): 2023 13.5%, 2024 24.1%, 2025 10.6%, 2026 5.2%, vs T-bills 5.3/5.2/4.2/3.8%. The excess over T-bills collapsed from ~19 points to ~1 (crowding).
  - It doesn't predict BTC returns (corr 0.05).
  - Binance is geo-blocked (451) and Bybit returns 403.
- **Pairs:** none of KO/PEP, XOM/CVX, EWA/EWC, GLD/GDX, HD/LOW, V/MA is cointegrated over 2008–26. They pass in only 0–18% of rolling 2-year windows. Spurious regression of independent random walks: "significant" 90% of the time.
- **Full QuantProcess pipeline on SPY** (CUSUM k=2 → reversal bet → triple barrier → RF meta-model, walk-forward 2008–26):
  - OOS AUC 0.60. Hit rate 47% → 56%, per-trade SR 0.027 → 0.129.
  - **But "longs only" (buy the dip) beat it:** 61% hit rate, SR 0.146. The model mostly learned "don't short SPY".
  - Purged and plain CV agreed here (0.593 vs 0.597).
- **CUSUM on real data:** BTC continues after events (k=3, 20-day t 2.4). SPY bounces after down events (5-day t 3.9).

### Portfolio / sizing / execution
- **Markowitz on 30 industries (rolling 10 years, OOS 1973–2026):**
  - Tangency 0.23 (10× leverage); 1/N 0.51; min-variance with Ledoit-Wolf 0.55 (best); in-sample tangency 0.90 (fantasy).
  - Random matrix theory: only 3 of 30 eigenvalues exceed the Marchenko-Pastur edge 1.55.
- **Risk parity vs 60/40** (SPY/IEF/GLD/DBC 2007–2026):
  - 60/40: Sharpe 0.65, max drawdown 31%, 2022 −16.4%.
  - Inverse vol levered to 10%: 0.67, 28%.
  - **ERC levered to 10%: 0.75, 23%, 2022 −9.9%.**
  - SPY–IEF correlation: −0.42 (2006–20) → +0.10 (2023–26).
  - Bug lesson: a naive ERC iteration gives NaN with negative correlations, which silently turned into 0 returns. Use Spinu's convex formulation and sanity-check weights.
- **Kelly:**
  - Drawdown law P(fall to x) = x^(2/c−1): full Kelly gives a 50% chance of halving.
  - CRSP 1926–2026: the Itô growth formula matches realized growth across leverage levels. Growth-optimal ~2.5× meant a 99.5% drawdown.
  - Trailing-10-year Kelly estimates ranged 0×–15.5×.
- **Prop challenge (+6%/−4%):**
  - No edge: 40% pass (29% with a trailing drawdown).
  - "Bold play": with negative edge, bigger size raises pass odds.
  - 93% requires Sharpe 5.2 at 1% daily vol, 2.6 at 0.5% (~60 days), 1.3 at 0.25% (~227 days).
- **Almgren-Chriss** closed form verified (0.004%).
- **Square-root impact:** $100M of SPY ≈ 2.7bp, of UPST ≈ 193bp. Retail-sized impact ≈ 0.
- **Avellaneda-Stoikov** reproduced: inventory-skewed quotes give 64.9 ± 6.8 vs symmetric 66.8 ± 13.4 (paper: 62.9 ± 5.9 vs 67.2 ± 13.4).
- **Glosten-Milgrom / Kyle** verified in sim. Kyle's λ = σ_v/2σ_u; half the information is revealed.
- **Roll's spread estimator fails on daily SPY:** it gives 54bp vs a true ~0.2bp.

### Options / rates
- **Black-Scholes check:** 9.925 vs MC 9.912. Simulating under real-world drift gives 14.07 (wrong). Put-call parity holds exactly.
- **Delta-hedged P&L ≈ vega × (σ_implied − σ_realized):** ±0.99 for ±5 vol points. Hedging error ∝ 1/√N.
- **VRP (FRED VIX vs realized SPY vol, 1999–2026):** VIX 20.0 vs realized 16.3. VIX is higher than what follows on 84% of days. Worst gap −69 points (Feb 2020).
- **SPY smile (Yahoo, 30-day, 2026-10-14):** IV 30.8% (85% strike) → 14.5% (ATM) → 10.4% (105%).
  - Breeden-Litzenberger P(−10%) = 2.6% vs 0.5% under Black-Scholes (historical frequency 2.2%).
  - Heston best fit: ρ = −0.7, error 1.3 points. Merton jumps calibrated to the smile: λ 1.1/yr, mean jump −10.7%, error 0.77 points.
  - Merton fitted to history instead gives a flat smile.
- **Yield-curve PCA (FRED 1990–2026):** level 75.6%, slope 14.2%, curvature 6.6%. 10-year bond duration 8.11, convexity 80.8.
- **Vasicek/CIR on 3-month T-bills:** θ 2.76%, half-life 2.7 years over 1981–2026. Mean reversion is negative over 2009–26 (regime break). The ZCB closed form matches MC to 5 decimals.

### Prediction markets (in progress)
- **Polymarket calibration:** 1,751 resolved binary markets with ≥ $50k volume, 2023–2026.
  - Brier skill 41–49%.
  - Mid-priced (5–95¢) YES contracts were **underpriced by ~4–5¢** (event-clustered t ≈ 3.5) when measured h days before the **scheduled** end date.
  - Pitfall: measuring relative to *close time* leaks the outcome ("by-date" markets that resolve YES close early), which inflated the bias to +8.9¢.
  - Caveats: top-volume selection, last-trade prices, no fees or spread, one venue.
- **LMSR (Hanson):**
  - C(q) = b·ln Σ e^(q_i/b); prices are a softmax and always sum to 1.
  - Worst-case market-maker loss = b·ln n.
  - An informed trader who moves the price to the truth costs the market maker exactly b·KL(p‖p₀) (verified numerically). The market maker is subsidizing information.
- **Arbitrage mechanics (Polymarket neg-risk):** a NO in one outcome converts to a YES in all the others, so n NOs become n−1 USDC immediately.
  - Buying every NO earns Σbids − 1 instantly.
  - Buying every YES only beats cash if Σasks < e^(−rT), so time value matters.
  - Live scan of 2,100 events / 632 multi-outcome events on 2026-10-14: Σmid median 0.995. Sell-side gaps in 15 events, median 0.8¢ and max 1.5¢, all fee-sized.
  - Buy-side gaps were mostly artifacts (incomplete outcome sets) or below the T-bill carry. Example: the 2028 market at Σask 0.990 earns 0.5%/yr vs 4.25% T-bills.
  - Literature: Saguillo et al. 2025 (arXiv:2508.03474) estimate ~$40M of realized Polymarket arbitrage, using LLMs to find dependent markets.
- **Kelly for binaries:** f* = (q−p)/(1−p).
  - A 5¢ edge at 50¢ means a 10% stake. q 0.97 vs p 0.95 says 40%, which is dangerous.
  - A 2% payout fee costs 36% of growth.
  - Time value: a 5¢ edge is worth 26%/yr if the market resolves in 1 week, but 0.25%/yr over 2 years (vs 4.25% T-bills).
  - Sim with a true 3¢ edge and beliefs noisy by ±5¢: full Kelly lost money 72% of the time; half Kelly 26%; quarter Kelly 10%.
- **Literature:**
  - Berg, Nelson & Rietz 2008: IEM beat polls 74% of the time.
  - Page & Clemen 2013: calibration degrades with horizon (pulled toward 50%), and time value limits exploitation.
  - Snowberg & Wolfers 2010: favorite-longshot bias comes from misperception, not risk-love.
- **Takeaway:** the edge is in short-dated markets, better models, fast arbitrage and market making.
- **Calibration vs horizon:** logit slope b ≈ 0.76–0.87 at 1/7/30/90/180 days (se ~0.08–0.11). That's a mild **reverse** favorite-longshot pattern (longshots cheap), the opposite of Page & Clemen. One hypothesis is the "buy NO at 97–99¢" yield trade. Tentative, about 2σ.
- **By category** (7 days before end, keyword-classified):
  - Politics: b 1.17, +2.2¢ (t 1.3). Well calibrated.
  - Sports: b 1.04, +5.5¢ (t 2.7).
  - "Other" (culture/tech): b 0.51, +13.2¢ (t 3.0). Worst calibrated.
  - Crypto: b 0.76, −5.1¢ (t −1.5).
  - Mispricing concentrates where attention and liquidity are thin.
- **Out-of-sample test of the YES underpricing:**
  - Train (ending before 2025-07): +1.8¢, t 0.7. Not significant; −8% with a 3¢ cost.
  - Test (after): +6.5¢, t 3.7.
  - Recalibration fitted on train didn't help on test (Brier 0.1914 vs 0.1905), and a selective rule lost 0.4%.
  - So the bias is recent and regime-dependent, not learnable in advance.
- **Kalshi weather** (daily high-temp buckets, 6 cities, 2,188 contracts, Aug–Oct 2026; the settled-history API reaches back only ~2 months):
  - Brier skill 27%. Slope b 1.18 ± 0.07 (classic favorite-longshot). Middle bias −0.3¢.
  - <5¢ buckets won 0.9% vs a 2.3¢ price. Each city-day sums to ~1.04.
  - Selling cheap buckets at the bid after fee (0.07·P·(1−P)) earned +0.74¢/contract, t 1.2, with 7 losses of ~98¢.
  - So the pattern is opposite to Polymarket's: biases are venue- and category-specific.
- **Market making a binary (sim):**
  - Profit per contract at 1¢ half-spread: 0% informed +1.06¢, 10% informed +0.66¢, 30% informed +0.22¢. At 0.5¢ with 30% informed: −0.33¢.
  - P&L sd ~±12, dominated by inventory at the 0/1 resolution. Pulling quotes 72h early cuts the sd to 10.3.
  - Polymarket liquidity rewards score each order S = ((v−s)/v)²·b, sampled each minute and paid daily.
- **Live order books** (CLOB /book, merging YES and complementary NO orders; matches gamma bestAsk), 412 markets:
  - Spread median 1.0¢. Depth within ±1¢ median $1.8k.
  - Cost to buy vs mid: $1k 0.9¢, $10k 3.4¢. In thin markets: $1k 2.3¢, $10k 18.6¢.
  - **The biases sit where costs are highest, so capacity is a few $k per market.**
- **Kalshi vs Polymarket, 2028 presidential winner, 24 matched candidates:**
  - Mids correlate 0.977. Mean |diff| 0.81¢, max 3.2¢ (AOC 10¢ vs 13.1¢).
  - Best gross cross-venue lock is 3.1¢, which isn't arbitrage after fees, two-year lockup (needs >8.4% to beat T-bills) and resolution-rule risk.
  - Kalshi API: `/trade-api/v2/events?status=open&with_nested_markets=true` (cursor paging; fields yes_bid_dollars/yes_ask_dollars, yes_sub_title).

- **Logical consistency across linked markets** (Polymarket 2028, live; notes/Q1.md):
  - Subset rule P(win) ≤ P(nominee): 52 candidates matched, with **one executable violation**, The Rock, winner bid > Dem-nominee ask by 0.4¢ (implied P(win|nom) 1.50). Everything else is at the 0.1¢ floor.
  - The winner market sums to only 0.919 (asks 0.947), so it's *incomplete*, not underpriced.
  - Additivity: Σ Rep candidate bids 0.371 vs Rep-party ask 0.350 (+2.1¢ over 24 legs). Not riskless (independent runs), the legs are at the tick floor, and capital is ~$23.6 per unit for 2 years, so ≈0.09% total. Worthless.
  - Rule: a gap g with capital K and lockup T needs g/K > e^{rT} − 1.

- **Speed of information, FOMC 2026-09-16** (25bp hike, FRED DFEDTARU 3.75→4.00; Polymarket $208M event; notes/Q2.md):
  - P(hike) went 0.87 → 0.99 within 10s of 18:00:00 UTC, with **90% of the move in 6s**. Stale-quote taker P&L was only ~$6k on $3.8M in 5 min.
  - Pre-meeting jumps came on data mornings (13:00 UTC on Sep 4, 10, 11). No leak in the last hour (0.86–0.88).
  - Cross-asset: bonds rallied in the first minute (TLT +0.17%). By 60 minutes, TNX +5.9bp and SPY −0.84%. The decision contract can't price guidance.
  - Tick trades: `data-api.polymarket.com/trades?market=<conditionId>&limit=500&offset=k`. Hourly prices-history needs ≤7-day ranges. Yahoo 1m bars only cover the last 30 days.

- **Crypto threshold markets = digital options** (notes/Q3.md, 2026-10-14 snapshot, BTC ≈ $81.6k):
  - Deribit surface (449 OTM options, 11 expiries) → smile-consistent digital −∂C/∂K, time-interpolated in total variance to venue settlement times.
  - RMSE of mids: Polymarket 1.74¢ / Kalshi 1.55¢ vs smile digital, compared with 3.4¢ / 3.2¢ vs flat N(d2). **The venues price the skew.**
  - Near ATM the venues sit 2–3¢ low. One forward shift per expiry gets RMSE to 0.4–1.2¢. Implied shift −$80…−$170 tracks Deribit carry (+$18…+$82), so **PM traders center on spot, not the forward.** That's a carry premium, not arbitrage.
  - Details worth cents (digital delta ≈ 4¢/$100 ATM at 2 days): Polymarket = Binance BTC/USDT at noon ET (USDT 0.9987); Kalshi KXBTCD = 60s avg CF BRTI before 5pm ET; Deribit expiry 08:00 UTC, API `public/get_book_summary_by_currency?currency=BTC&kind=option`.

- **Kalshi daily BTC (KXBTCD) vs DVOL lognormal** (notes/R1.md; 68 days Aug–Oct 2026, strikes ±6% of T−24h spot, day-clustered):
  - T−24h: market Brier 0.099 vs model 0.105 (t 3.7). Encompassing weights 1.82 market / −0.89 model. Fade-the-market rule −7.2¢/contract (t −2.5).
  - T−6h: tie. Market calibration slope 1.35 (under-confident: 5–15¢ won 4.2%). Suggestive, too few days.
  - **Trap:** Deribit chart bars are stamped at bar START. Using them as-of produced a fake +9.1¢ (t 3.6) edge.
  - Kalshi batch candles `GET /markets/candlesticks?market_tickers=a,b,...` avoids the ~1 call/3s rate limit.

### Math foundations (later waves)
- **Proper scoring:** with truth 0.7, Brier and log are maximized at 0.70; a linear score at 0.99 (improper). LMSR = market log score; a trader's payoff b·ln(p1/p0) is verified. Polymarket log-loss skill 38% vs Brier 45%.
- **MC variance reduction** (BS call, N=20k): plain sd 0.101, antithetic 0.068, control variate 0.039 (variance ÷6.8). Importance sampling for P(30-day −20%) = 4.42e-5: plain 3.0e-5 (3 hits), IS 4.41e-5.
- **Bayesian evaluation:**
  - 55/100 wins gives P(edge) 84%. With a skeptical Beta(1250,1250) prior: 57.8%.
  - SPRT 50% vs 55% (α=β=5%) needs a median ~434 trades.

- **Prices as beliefs** (notes/R3.md; Manski 2006, Wolfers–Zitzewitz 2006):
  - CRRA demand x = w(k−1)/(1−p+kp), k = [q(1−p)/((1−q)p)]^{1/γ}. Log utility gives p = wealth-weighted mean belief exactly.
  - Risk-neutral (Manski): p = (1−p)-quantile of beliefs, so the mean is only bounded in (p², 2p−p²).
  - Sim: the bias scales with belief dispersion, is 0 at 0.5, and is +6.8¢ (γ=0.1) / −4.0¢ (γ=5) at mean 0.05 with sd 0.10. γ<1 gives the classic FLB (cf. Kalshi weather), γ>1 the reverse FLB (cf. Polymarket).
  - Wealth–belief correlation 0.43 moved the price from 0.28 to 0.48.

- **De-vig / Shin model** (notes/R5.md; 199 complete Kalshi weather city-days, Σ mids 1.045, Σ asks 1.09):
  - Log loss: multiplicative 1.193, power 1.187, Shin 1.186 (z≈0.9–1.9%), additive 1.179.
  - <10¢ buckets: 14 wins vs predicted 18.9 (multiplicative) / 16.9 (Shin) / 15.5 (additive).
  - Shin beats multiplicative with t −3.4. Never de-vig by simple division when longshots are involved.

- **Order flow on Polymarket** (notes/R4.md; 8 most active markets, taker trades, 1-min):
  - Kyle λ median 0.03¢ per $1k (Fed +25bp 0.11, NFL 0.005). Next-minute predictability is negligible (≤20% of impact, below the spread).
  - **Trap:** CLOB prices-history fidelity=1 lags ~1 min (stamped :16–:20s). Raw data shows fake "flow predicts next minute" with t up to 40. Align with trade prices.
  - data-api /trades default takerOnly=true, so `side` = taker.

- **Excess movement** (notes/R6.md; Augenblick–Rabin 2021):
  - Rational-forecast identity E[Σ(Δπ)²] = π0(1−π0).
  - 1,625 resolved Polymarket markets (daily, to 1 day before close, then the outcome): Σm/Σr = **1.31 ± 0.06** (1.38 skipping the first 3–7 days). Simulated rational learner + 0.5¢ noise: 1.02.
  - Largest for longshots (1.48) and 2w–2m horizons (1.68). No volume gradient. Daily-change AC −0.08.

- **Early exit and "favorites as a bond"** (notes/S3.md):
  - Sell iff p − s > q·e^{−rτ}. Agreeing with the market at 95¢ with a 1¢ half-spread, sell if more than 91 days remain.
  - Buying first touch ≥0.95 and holding (1,340 trades) won 96.0% vs 97.8¢ paid: **−3.2% vs T-bills (t −3.7)**, negative every year 2024–26. ≥0.90: −4.9%; ≥0.97: −2.8%.

- **Fading big daily moves** (notes/S1.md; 393 events):
  - Gross reversal +0.9/+3.1/+5.2¢ at 5 days for ≥5/10/20¢ moves (t up to 6), about 25% of the move.
  - Net of 2¢ round trip: ≥20¢ 5-day +3.2¢ (t 2.5), below the Bonferroni bar (9 variants). Suggestive; re-test on tick and book data.

- **Multi-outcome Kelly** (notes/S5.md): bet set S where q/p > R = (1−Σ_S q)/(1−Σ_S p), stake f_i = q_i − R·p_i, keep R in cash.
  - It backs zero-edge outcomes as hedges. Growth is +10% vs per-bucket binary Kelly.
  - With 25% belief noise, full Kelly has negative expected growth; half Kelly stays positive.

## 4. Pitfalls checklist (learned the hard way)

1. Compare against a random or unconditional baseline, not against 0.
2. Overlapping outcome windows inflate t. Use effective n or a block bootstrap.
3. Count every trial. Use Bonferroni, Holm or BH, plus a placebo run on random dates.
4. **Look-ahead:** HMM smoothed/Viterbi states; measuring prediction-market prices relative to close time; a price series whose timestamps lag (Polymarket prices-history); bars stamped at their start (Deribit chart data). All four produced fake results.
5. Short samples bias mean-reversion speed upward.
6. Test a context effect on all days before crediting the event.
7. Benchmark ML against the simplest rule it might be rediscovering.
8. Include the right factors (MOM!) before claiming alpha.
9. Model assumptions must hold (Roll estimator; Vasicek across policy regimes).
10. Costs kill short horizons. Short-term reversal doesn't survive costs at scale.

## 5. Data sources and environment notes

- **Factors:** Ken French Data Library (CRSP-based) at mba.tuck.dartmouth.edu/pages/faculty/ken.french/.
- **Rates, VIX, credit:** FRED via `fredgraph.csv?id=SERIES` (no key needed).
- **AQR datasets:** TSMOM factor xlsx.
- **Prices:** Yahoo via `yfinance`. Cross-checked against CRSP: daily correlation 0.983, monthly 0.989.
- **Option chains:** `yfinance` `Ticker.option_chain`. Quotes are delayed, and the dividend wasn't adjusted.
- **Prediction markets:** Polymarket `gamma-api.polymarket.com/markets` (closed=true, limit 100/page; paging stopped ~2,100) and `clob.polymarket.com/prices-history?market=TOKEN&interval=max&fidelity=1440`. Kalshi `api.elections.kalshi.com/trade-api/v2/markets`. PredictIt `predictit.org/api/marketdata/all/`. All reachable.
- **Blocked or unavailable:** YouTube (bot block on cloud IPs; transcripts were pasted by the user), SSRN (403), CBOE site (403), Everygen video analysis (needs a paid plan).
- **Python libraries:** numpy, pandas, scipy, statsmodels, arch, hmmlearn, scikit-learn, yfinance, openpyxl.

## 5b. The user's home PC / Raspberry Pi (remember this)

The user has a **home PC or Pi with backtesting data and live access to prediction markets and trading markets**. This cloud session can't reach it (container, no Remote Control link). To use it, run Claude there (Claude Desktop, or `claude remote-control` in a terminal in the repo folder), pull this branch, and read this file. Work that belongs on that machine rather than in the cloud:
- **Continuous data capture** that the cloud can't keep: Yahoo 1-minute bars (they expire after 30 days, see Q2), Polymarket CLOB books/trades and Kalshi quotes around scheduled events (FOMC, CPI, NFP), and Deribit option snapshots aligned with Polymarket/Kalshi BTC threshold quotes (Q3).
- **Longer backtests** on the local historical data: re-run the topic scripts in `code/` against the longer local history (e.g., R1 calibration and R6 excess movement over more markets).
- **Live / paper trading** with real account access. Start with paper or small size only. Every edge found so far is about a spread wide (see Q3 carry gap, R4 flow, N2 weather longshots). Respect fees (Kalshi 0.07·P·(1−P)), lockup and the pitfalls list. Never trade real money without the user's explicit go-ahead per strategy.

## 6. Folder map

- `CONTEXT.md`: this file.
- `README.md`: how to use the folder.
- `agenda.md`: every topic and its status.
- `notes/`: one markdown file per topic (math, method, numbers, lessons), plus `*_out.txt` raw outputs.
- `code/`: the script for each topic. Run with `python3 -I code/<file>.py .` from `quant/` after `bash data/fetch_data.sh`.
- `course/quant-field-manual.html`: the full course (14 modules, 3 interactive labs, formula sheet).
- `data/`: small derived datasets (Polymarket calibration rows, SPY smile) plus `fetch_data.sh` for the raw data.
