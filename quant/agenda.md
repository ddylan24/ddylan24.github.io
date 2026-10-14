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
- [ ] R2 Skill vs luck among Polymarket traders: wallet-level P&L from data-api trades; persistence test (first half vs second half), multiple-testing correction.
- [x] R3 Prices as beliefs: Manski (2006) vs Wolfers–Zitzewitz (2006). When does a prediction-market price equal the mean belief? Simulation with heterogeneous beliefs and log/CRRA utility.
- [x] R4 Order-flow imbalance on Polymarket tick data: does signed taker flow predict the next-minute price move (Cont–Kukanov–Stoikov)?
- [x] R5 Shin's model of insider trading and vig removal: derive it, then apply it to multi-outcome prediction-market sums.
- [x] R6 Excess belief movement (Augenblick–Rabin): Σ(Δπ)² vs π0(1−π0) on resolved Polymarket paths.

## S. Eighth wave
- [ ] S1 Fade large daily moves on Polymarket (from R6's excess movement / −0.08 autocorrelation): event-clustered backtest with spread and fees.
- [ ] S2 Kalshi hourly BTC markets (KXBTCD non-5pm events): calibration slope vs horizon (1h–24h). Does under-confidence grow as expiry nears? Use batch candles.
- [x] S3 Optimal early exit + "favorites as a bond" backtest (buy ≥95¢, hold) on resolved Polymarket markets.
- [ ] S4 Polymarket maker vs taker P&L split (takerOnly=false rows): who earns the spread net of adverse selection?
- [ ] HOME-PC: tasks needing the user's home PC/Pi (local backtest data, live access) are listed in CONTEXT §5b.
