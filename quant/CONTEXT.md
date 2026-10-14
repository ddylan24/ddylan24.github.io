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
- **Kalshi vs Polymarket, 2028 presidential winner, 24 matched candidates:**
  - Mids correlate 0.977. Mean |diff| 0.81¢, max 3.2¢ (AOC 10¢ vs 13.1¢).
  - Best gross cross-venue lock is 3.1¢, which isn't arbitrage after fees, two-year lockup (needs >8.4% to beat T-bills) and resolution-rule risk.
  - Kalshi API: `/trade-api/v2/events?status=open&with_nested_markets=true` (cursor paging; fields yes_bid_dollars/yes_ask_dollars, yes_sub_title).

## 4. Pitfalls checklist (learned the hard way)

1. Compare against a random or unconditional baseline, not against 0.
2. Overlapping outcome windows inflate t. Use effective n or a block bootstrap.
3. Count every trial. Use Bonferroni, Holm or BH, plus a placebo run on random dates.
4. **Look-ahead:** HMM smoothed/Viterbi states; measuring prediction-market prices relative to close time. Both produced fake results today.
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

## 6. Folder map

- `CONTEXT.md`: this file.
- `README.md`: how to use the folder.
- `agenda.md`: every topic and its status.
- `notes/`: one markdown file per topic (math, method, numbers, lessons), plus `*_out.txt` raw outputs.
- `code/`: the script for each topic. Run with `python3 -I code/<file>.py .` from `quant/` after `bash data/fetch_data.sh`.
- `course/quant-field-manual.html`: the full course (14 modules, 3 interactive labs, formula sheet).
- `data/`: small derived datasets (Polymarket calibration rows, SPY smile) plus `fetch_data.sh` for the raw data.
