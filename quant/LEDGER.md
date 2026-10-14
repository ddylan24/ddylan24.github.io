# Hypothesis ledger (multiple-testing accounting)

Every edge-style hypothesis tested in the session of Oct 13–14, 2026, with its fate. Use it to judge how many tries stand behind any surviving result. "Variants" is roughly how many specifications were tried for that hypothesis.

| # | Hypothesis | Data | Variants | Best in-sample | Fate |
|---|---|---|---|---|---|
| A1 | Prior-day-low sweep predicts up-move (DeltaTrend) | SPY 1999–2026 | ~10 | t 2.18 vs 0 | Dead: −0.006% vs a random day |
| A2 | Context filters on sweep days | SPY | 42 | 6 "significant" | Dead: random dates give 6.1 |
| B | Calendar anomalies (Monday, turn of month, January) | CRSP 1926–2026 | 3 | t up to 10.9 (pre-1990) | Dead after 1990 |
| C | Industry momentum alpha | Ken French | 2 | α t 4.4 (FF5) | t 1.5 with MOM |
| D | AQR TSMOM alpha | AQR | 2 | t 5.3 (1985–) | t 1.4 since 2010 |
| E | HMM regime timing | CRSP→2000s | 3 | Sharpe 1.43 | Look-ahead; honest 0.36 |
| F | ML meta-labeling | SPY sweeps | ~5 | AUC gain | Learned "longs only" |
| G | Vol targeting / constant-vol momentum | KF | 2 | Sharpe 0.87 vs 0.45 | **Survives** (published, replicated) |
| H | Crypto funding carry | Hyperliquid | 1 | 19 pts over T-bills (2024) | Decayed to ~1 pt (2026) |
| P2 | Polymarket YES underpriced | 1.6k markets | ~6 | +6.5¢ (t 3.7) post-2025 | Regime-dependent; not learnable OOS |
| N2 | Sell Kalshi weather longshots | 2.2k contracts | 2 | +0.74¢ | t 1.2, not significant |
| Q1 | Logical arbitrage (2028 election) | live | 3 | +2.1¢ gap | Worthless after lockup |
| Q3/T3 | Crypto binaries vs options (carry gap) | live | 3 | 2–3¢ | Basis risk, not arbitrage |
| R1 | DVOL model vs Kalshi BTC | 68 days | 4 | +9¢ (look-ahead!) | Honest: market wins (−7¢) |
| R4 | Order flow predicts next minute | 8 markets | 3 | t 40 (timestamp lag) | Dead after alignment |
| R2 | Leaderboard wallets are skilled | 236k wallets | 2 | — | 0 pass BH-FDR; weak ROI persistence |
| S1 | Fade big daily moves | 393 events | 9 | +3.2¢ (t 2.5) | Below Bonferroni; needs book data |
| S2 | Hourly BTC longshots overpriced | 17 days | 6 | t 9.6 (n 15!) | Pooled null |
| S3 | Buy ≥95¢ favorites | 1.3k trades | 3 | — | Negative: −3% vs T-bills |
| S8 | NWS MOS beats weather market | 116 days | 5 | — | Market wins (t 4.5) |
| U4 | **Kalshi BTC T−6h slope-only recalibration** | 34 OOS days | ~6 | DM t −4.0; +3.1¢ (t 3.0) | **Candidate**: pre-registered, verify forward |
| U1 | Recession contracts carry an insurance premium | 2 markets | 1 | ~3–5¢ (CAPM-implied) | Plausible; n = 1 resolution |

**Totals:** roughly 100+ specifications across about 22 hypotheses. One published effect survived (vol targeting), and one new candidate (U4) is awaiting forward data. At this test count, expect a few t ≈ 3 results by luck. That's why U4 is pre-registered rather than traded.
