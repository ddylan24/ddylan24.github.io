# Research agenda — goal: expert-level command of the math behind quant trading
Status: [ ] todo  [~] in progress  [x] done. Each item: derive, verify numerically, test on real data, fold into course.

## A. Statistics of trading results (foundation for everything)
- [x] A1 Hypothesis tests on event outcomes: CI of mean, t-test, why fat tails/serial dependence break them. Real data: replicate QP02 prior-day high/low sweeps on SPY daily (1999–2026), ATR double barrier, by sub-period.
- [x] A2 Sharpe ratio statistics: SE of SR (Lo 2002, Mertens 2002 w/ skew & kurtosis), Probabilistic SR, Minimum Track Record Length, Deflated SR. Verify by simulation.
- [x] A3 Multiple testing: Bonferroni, Holm, Benjamini-Hochberg FDR, Harvey-Liu-Zhu haircuts. Experiment: 50 context splits on sweep events.
- [x] A4 Bootstrap: iid vs stationary/block bootstrap (Politis-Romano), drawdown distributions on real strategy returns.

## B. Stochastic processes & calculus
- [x] B1 Random walk -> Brownian motion; Itô's lemma derivation; why GBM drift is mu - sigma^2/2 (volatility drag). Verify numerically.
- [x] B2 Ornstein-Uhlenbeck: exact discretization = AR(1), MLE of theta/mu/sigma, half-life. Real data: a pair/spread.
- [x] B3 Markov chains & HMMs: stationary distribution, Baum-Welch/forward algorithm, Viterbi. Real data: 2-state HMM on SPY.
- [x] B4 Jumps & fat tails: kurtosis of real returns, Student-t fits, why normal VaR fails.

## C. Volatility modeling
- [x] C1 (EWMA covered; range estimators deferred) Realized vol estimators (close-close, Parkinson, Garman-Klass, Yang-Zhang), EWMA (RiskMetrics).
- [x] C2 GARCH(1,1): MLE, persistence, half-life of vol shocks; real SPY fit. Vol forecasting -> vol targeting (Moreira-Muir replication on SPY).

## D. Derivatives math
- [x] D1 Black-Scholes derivation (delta hedge + Itô), risk-neutral pricing, Feynman-Kac; verify BS formula vs Monte Carlo.
- [x] D2 Greeks and P&L of a delta-hedged option: gamma-theta tradeoff, P&L = ½Γ S²(σ_realized² − σ_implied²)dt. Simulate.
- [x] D3 (skew deferred) Implied vol, skew, variance risk premium (VIX vs realized).

## E. Portfolio math
- [x] E1 Mean-variance (Markowitz), tangency portfolio, why estimation error kills it; shrinkage (Ledoit-Wolf); risk parity.
- [x] E2 (PCA+RMT; FF regression deferred) Factor models & PCA: CAPM beta, Fama-French regression, PCA on sector ETFs, random matrix theory (Marchenko-Pastur) for covariance cleaning.
- [x] E3 Kelly derivation (discrete & continuous), multi-asset Kelly = mean-variance; drawdown math.

## F. Time series & stat arb
- [x] F1 Stationarity tests (ADF, KPSS), cointegration (Engle-Granger, Johansen). Real pair test.
- [x] F2 (tuning-sensitive; noted) Kalman filter for dynamic hedge ratios.
- [x] F3 Fractional differentiation (López de Prado) — memory vs stationarity tradeoff on real data.

## G. Signals on real data (replications)
- [x] G1 Time-series momentum on ETF universe, vol-scaled, with costs; Deflated SR of the variants.
- [x] G2 QP03 CUSUM events on BTC & SPY vs random baseline.
- [x] G3 Triple-barrier labels + meta-labeling with purged CV.

## H. Microstructure & execution
- [x] H1 Almgren-Chriss solution (sinh trajectory), square-root impact law.
- [x] H2 (AS done; Kyle/GM deferred) Market making: Avellaneda-Stoikov reservation price & spread; adverse selection (Glosten-Milgrom, Kyle lambda).
- [x] H3 Prop-firm challenge as a barrier problem: pass probability via gambler's ruin / Brownian first passage, verified by Monte Carlo.

## I. Added after core agenda
- [x] I1 Fundamental Law of Active Management: IR ≈ IC·√breadth (Grinold 1989); verify by simulation; measure IC of a real signal.
- [x] I2 Factor regressions: alpha attribution with FF5 + momentum (Ken French) for strategies built today (TSMOM, vol-managed).
- [x] I3 Adverse selection: Glosten–Milgrom spread, Kyle's lambda.
- [x] I4 Range-based volatility estimators (Parkinson, Garman–Klass, Yang–Zhang) vs close-to-close efficiency.

## J. Evening additions
- [x] Formula sheet (Module 14) + full-page render check
- [x] J1 Momentum crashes (Daniel & Moskowitz 2016) on Ken French MOM: skew, crash timing, bear-market rebounds, dynamic scaling.
- [x] J2 Real implied-vol smile from a live SPY option chain (Yahoo) vs Black-Scholes flat vol; skew math.
- [x] J3 Low-volatility / betting-against-beta anomaly on Ken French portfolios.
- [x] J4 Bayesian shrinkage (James–Stein) of many strategies' Sharpe ratios.
- [x] K1 Heston stochastic volatility: simulate, price options, show it generates the SPY skew.
- [x] K2 Yield-curve PCA (level/slope/curvature) on FRED Treasury yields; duration & convexity.

## L. Second evening wave
- [x] L1 Jump-diffusion (Merton): fit jump intensity/size to CRSP daily returns; does it explain short-dated SPY skew better than Heston?
- [x] L2 Interest-rate models: Vasicek/CIR fit to FRED 3m T-bill; mean reversion of rates; bond pricing formula check.
- [x] L3 Carry: currency/bond carry with FRED rates; carry crash skew.
- [x] L4 Seasonality & calendar anomalies on CRSP (turn-of-month, January, day-of-week) with multiple-testing control.
- [x] L5 Value factor's 2007–2020 drawdown and recovery (Ken French HML): how unusual vs its own history (drawdown statistics math).

## P. Prediction markets (user request — prioritized)
- [x] P1 (covered within P2–P6) Market structure & venues: Kalshi (CFTC DCM), Polymarket (CLOB, USDC), PredictIt, Betfair; contract math (binary = probability), fees, capital lockup.
- [x] P2 Real-data calibration study: resolved markets (Polymarket/Kalshi public APIs) — price vs outcome, Brier score, favorite–longshot bias.
- [x] P3 Market-maker math: Hanson's LMSR (cost function, b, worst-case loss b·ln n); CLOB quoting; inventory risk on binaries.
- [x] P4 Arbitrage: Dutch books (outcomes summing ≠ 1), cross-venue, combinatorial; fees & resolution risk; literature on Polymarket arbitrage.
- [x] P5 Betting math for binaries: Kelly for prediction markets, edge vs fees, time value of capital (why longshots/long-dated markets misprice).
- [x] P6 Literature: Wolfers & Zitzewitz 2004; Iowa Electronic Markets vs polls (Berg et al.); Snowberg & Wolfers 2010 favorite–longshot; manipulation evidence.
- [x] P7 Calibration vs horizon on our Polymarket data (test Page & Clemen pull-toward-50%).
- [x] P8 Cross-venue: Kalshi vs Polymarket prices on the same live events.

## M. Third wave
- [x] M1 Polymarket calibration split by category (sports vs politics vs crypto vs other) — where are the biases?
- [x] M2 Crypto perpetual-futures funding rates as carry (exchange APIs), basis math.
- [x] M3 (replaced) Live Polymarket order-book liquidity: spreads, depth, capacity vs volume.
- [x] M4 Risk parity / all-weather across asset classes with real ETF data vs 60/40 (leverage, rates regime 2022).

## N. Fourth wave
- [x] N1 Out-of-sample test of Polymarket YES-underpricing: fit on markets ending before 2025-07, test after; include half-spread costs.
- [x] N2 Kalshi calibration on settled markets (candlesticks/market history API).
- [x] N3 Market-making economics on Polymarket: spread capture vs adverse selection, liquidity rewards.

## O. Fifth wave (math foundations)
- [x] O1 Proper scoring rules: Brier vs log score, why LMSR = log scoring rule; scoring traders/forecasters.
- [x] O2 Monte Carlo variance reduction: antithetic, control variates, importance sampling for tail probabilities.
- [x] O3 Bayesian inference for strategy evaluation: beta-binomial win rates, posterior of Sharpe, sequential testing (when to stop a strategy).

## Q. Sixth wave
- [x] Q1 Logical (combinatorial) consistency on Polymarket: P(president) ≤ P(party nominee); party-level vs candidate-level sums.
- [x] Q2 Speed of information: minute-level Polymarket prices around a scheduled event (FOMC 2026-09-16).
- [x] Q3 Binary options math: digital = e^{−rT}N(d2); compare crypto price-threshold prediction markets to options-implied / lognormal probabilities.

## R. Seventh wave (added when Q ran out)
- [x] R1 Calibration of Kalshi daily BTC threshold markets (KXBTCD, settled) vs a lognormal using Deribit DVOL at the time: is there a favorite-longshot bias, and does the options model beat the market?
- [x] R2 Skill vs luck: 0/38k wallets pass BH-FDR with a common-outcome null; top earners p 0.06–0.84; weak ROI persistence (Spearman +0.07; top quintile late ROI +1.3%).
- [x] R3 Prices as beliefs: Manski (2006) vs Wolfers–Zitzewitz (2006). When does a prediction-market price equal the mean belief? Simulation with heterogeneous beliefs and log/CRRA utility.
- [x] R4 Order-flow imbalance on Polymarket tick data: does signed taker flow predict the next-minute price move (Cont–Kukanov–Stoikov)?
- [x] R5 Shin's model of insider trading and vig removal: derive it, then apply it to multi-outcome prediction-market sums.
- [x] R6 Excess belief movement (Augenblick–Rabin): Σ(Δπ)² vs π0(1−π0) on resolved Polymarket paths.

## S. Eighth wave
- [x] S1 Fade large daily moves on Polymarket: gross reversal real (t 6), net marginal (≥20¢ moves +3.2¢, t 2.5).
- [x] S2 Kalshi hourly BTC calibration by horizon: pooled slope 1.15 ± 0.14 (n.s.); selling longshots −0.3¢. Needs longer collection.
- [x] S3 Optimal early exit + "favorites as a bond" backtest (buy ≥95¢, hold) on resolved Polymarket markets.
- [~] S4 Maker vs taker split: takers +$8.4M vs null $11.4M ± 16.2M (no detectable transfer); needs maker attribution (see R2).
- [x] S5 Kelly for mutually exclusive outcomes (horse-race solution), hedging bets, noisy beliefs.
- [x] S6 Murphy Brier decomposition (REL/RES/UNC) for all forecast datasets.
- [x] S7 Polymarket October FOMC odds vs CBOT fed funds futures (ZQ) and FRED EFFR.
- [x] S8 NWS GFS MOS (IEM archive) vs Kalshi daily-high markets: market wins easily; mixing hurts; trading loses.
- [x] S9 Diffusion of a probability: dp = φ(N⁻¹p)/√τ dW; Polymarket fits the price shape (β 0.99) but τ^−0.53; near-certainties jump.
- [x] S10 Jump risk at ≥90¢: 20¢ one-day drops 39× diffusion, kurtosis ~1000; 90–95¢ lose 9.1% vs 7.2% implied.
- [ ] HOME-PC: tasks needing the user's home PC/Pi (local backtest data, live access) are listed in CONTEXT §5b.

## T. Ninth wave
- [x] T1 Jump risk for ≥90¢ contracts: covered by S10 (jump rates) + T2 (pricing jumps into quotes).
- [x] T2 Binary market-making sim (S9 vol law + S10 jumps): inventory skew cuts P&L sd 3.6×, Sharpe/market 0.06→0.19; jumps cost ~$4/market.
- [x] T3 BTC term structure across Polymarket+Kalshi: no calendar arb (w monotone over 8 expiries); vols within 0–3 pts of options; centers flat at spot vs forward rising with carry.
- [x] T4 Election contract vs markets: SPY beta ≈0 (risk premium ≈0¢); Trump-trade signs (solar −, USD/MXN +, BTC +) marginal; off-by-one daily alignment flips signs.
- [x] T5 Home-PC playbook + live/capture.py (continuous Polymarket/Kalshi/Deribit logger, smoke-tested).

## U. Tenth wave
- [x] U1 Recession contracts: −0.96¢ per 1% SPY (2025, t −4.9; corr −0.83 on big days) → CAPM premium ≈ +3–5.5¢ above true probability; elections ≈0.1¢.
- [x] U2 BTC price discovery: Kalshi quotes respond 63% same-minute (R² 0.42, total 0.19¢/bp ≈ digital delta 0.22); Polymarket BTC binaries thin/stale (hourly ≈$15/strike).
- [x] U3 Empirical-Bayes pooling of calibration slopes (Kalshi weather cities): τ̂=0, Q 4.7/5df → one pooled slope 1.17; city differences are noise.
- [x] U4 Scoring tournament + DM tests. Additive/Shin de-vig confirmed OOS. Candidate edge: slope-only recal (b≈1.2) of Kalshi BTC at T−6h beats market OOS (DM t −4.0; +3.1¢/contract, t 3.0) — verify forward.

## V. Eleventh wave
- [ ] V1 Top-of-file "key takeaways" for CONTEXT.md (it has grown long), plus a ledger of every hypothesis tested today (multiple-testing accounting).
- [ ] V2 BTC variance risk premium: Deribit DVOL vs subsequent realized vol (perp), 2026; sign, size, and relation to prediction-market vol (T3).
- [ ] V3 Kalshi economic-data markets (CPI/jobs, KXCPI etc.): calibration of settled markets vs outcomes.
