# Prediction-market playbook (for the home PC / Pi)

Written 2026-10-14 from the research in `notes/`. Read `CONTEXT.md` first. This file is the *operational* summary: what to run, what to test next, and the rules for money.

## 1. Start capturing data now (cheap, irreplaceable)
Kalshi keeps only weeks of settled history, Polymarket's minute history lags, and Yahoo minute bars expire after 30 days. Most open questions below need data that nobody archives.
```bash
cd quant/live
nohup python3 capture.py --out ~/pmdata --interval 300 > capture.log 2>&1 &
```
- Every 5 minutes it saves: Polymarket top-200 markets (bid/ask/volume), merged books for the top 50, Kalshi KXBTCD and the six KXHIGH* weather series, and Deribit BTC options (hourly).
- About 20–40 MB/day. No keys needed; read-only.
- On a Pi, use `crontab @reboot` or a systemd unit so it survives restarts.
- Before scheduled events (FOMC, CPI, NFP), also save Yahoo 1-minute bars the same week (Q2).

## 2. Research queue that needs that data (highest value first)
0. **PRE-REGISTERED candidate (U4): Kalshi KXBTCD at T−6h.** Rule fixed on 2026-10-14, before any forward data:
   - p' = logit⁻¹(1.21·logit(mid)).
   - Buy YES at the ask if p' − ask > 0.01 + fee; sell at the bid if bid − p' > 0.01 + fee.
   - Only strikes within ±6% of spot at T−24h with spread ≤ 10¢.
   - Paper-trade for at least 4 weeks. Also log the short-dated VRP (Deribit ATM IV vs realized) to test the V2 mechanism: the edge should shrink when the VRP does. Success = mean > 0 with daily-P&L t > 2 and fills checked against captured books. Do NOT re-fit the slope on forward data until the evaluation is complete.
1. **Same-time weather information test (S8 follow-up).** Compare Kalshi weather mids with NWS NBM/HRRR/MOS forecasts *issued at the same time* (IEM archive), then a recalibrated blend. Only "resolution" can beat the market (S6).
2. **Short-horizon BTC calibration (R1/S2 follow-up).** Logit slope at T−1…12h over ≥3 months of KXBTCD. Hint so far: slope 1.15–1.35 (under-confident), not yet significant.
3. **Fade big moves with real books (S1 follow-up).** Re-test the ≥20¢ reversal (+3¢ net, t 2.5 on daily data) using captured books, to see if it's executable at the actual ask and bid.
4. **Spot-vs-forward carry trade (Q3/T3).** Venues center on spot and options on the forward (+$80–190). Track whether the gap is ever wide enough to beat fees plus basis risk via Deribit call spreads.
5. **Market-making paper trading (T2).** Quote with inventory skew and spreads scaled by φ(N⁻¹p)/τ^0.5. Pull quotes before scheduled news. Log hypothetical fills against captured books.

## 3. What NOT to do (each one already tested)
- Buy "safe" 90–98¢ favorites and hold: −3% vs T-bills (S3); 20¢ crash risk is 39× the diffusion estimate (S10).
- Trade a flat-vol N(d2) model against crypto threshold markets: −7¢/contract (R1). The venues price the skew (Q3).
- Trade public day-old forecasts against weather markets: the market wins (S8).
- Copy leaderboard wallets by total P&L: no wallet passes a skill test (R2). If copying at all, rank by ROI.
- Lock capital in long-dated "arbitrage": a 2¢ gap over 2 years loses to T-bills (Q1, P34). Sell agreed-upon positions with more than ~90 days left (S3).
- Trust a lead-lag signal before checking timestamps: Polymarket minute history lags ~1 min, Deribit bars are stamped at the open, daily stamps fall on the previous evening ET (R4, R1, T4).

## 4. Rules for real money (only with the user's explicit go-ahead per strategy)
1. **Paper first:** at least 4 weeks of logged paper trades with the realistic fill model (cross the spread, Kalshi fee 0.07·P·(1−P)).
2. **Out-of-sample:** a strategy must beat costs on data collected *after* it was designed, with event-clustered t > 2.8 if more than 5 variants were tried (Bonferroni).
3. **Size:** ≤ ¼ Kelly computed with *shrunk* probabilities; for multi-outcome events, use the joint Kelly formula (S5). Max 2% of bankroll per event, 10% per correlated cluster.
4. **Stop rules:** halt a strategy after a drawdown of 3× its expected monthly P&L sd, or if live slippage exceeds the backtest by more than 50%.
5. **Never** run unattended order placement without hard limits on order size, daily loss and open positions, enforced in code.
