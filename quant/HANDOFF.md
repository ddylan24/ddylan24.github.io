# HANDOFF: start here (for a new Claude session with more capabilities)

You're picking up a research project that ran in a cloud Claude Code session on 2026-10-13…15. That session could not reach the user's home PC/Pi, which has **months of settled Kalshi market data stored locally** and live market access. The user has given permission to use that data. Your job is to continue where the cloud session stopped: **validate and then build a Kalshi liquidity-providing algorithm, starting with hourly Miami temperature (KXTEMPMIAH).**

## 0. First 10 minutes
1. `git fetch origin && git checkout claude/adoring-bohr-2bzxvp`. Everything lives in `quant/`.
2. Read, in order:
   - this file
   - `quant/CONTEXT.md` §0 (top takeaways), then §3 for numbers as needed
   - `quant/LEDGER.md` (every hypothesis tested and its fate; don't re-test dead ideas)
   - `quant/PLAYBOOK.md` (operational rules; §4 = money rules)
   - `quant/SPEED.md`
   - `quant/notes/LIP.md`, `X2.md`, `Y1.md`, `Z1.md`, `Z2.md`, `AA1.md`, `AD2.md` (the LIP evidence chain)
3. `pip install numpy pandas scipy statsmodels` (plus `arch hmmlearn scikit-learn yfinance openpyxl` for the older topics).
4. Find the user's stored Kalshi data on this machine. Ask the user for its path and format if it isn't obvious.

## 1. Where things stand (one paragraph)
Kalshi's Liquidity Incentive Program (LIP) pays **≈ $290k/day** for resting depth (grew ~30× in a year; runs to Jan 1, 2027; scoring = whole-level walk to Target, reference at Target/5, DF^ticks, snapshot each second, counted only if both sides reach Target; see `notes/LIP.md`). Across eight series, maker fills roughly break even, so rewards ≈ profit. **KXTEMPMIAH is the best series found:** 4.2¢ of reward per filled contract **plus** makers +0.69 ± 0.22¢/contract on fills over 14 days (z 3.1; +1.24¢ over 7 days). Late takers who trade on the public thermometer lose to makers, and fills are betting flow, not informed flow. Kalshi publishes the **exact settlement index** (`GET /live_data/weather/miami`, public, 1-min, 0.01°F, `detailed=true` gives each station's reading and arrival time; arrives a median 87s after each minute). Queues get *cancelled*, not consumed (Z2), so risk comes from being slow to pull quotes when the index moves near a strike late in the hour. Extreme speed is **not** needed for weather; seconds-level reaction plus pull rules is enough (SPEED.md §4).

## 2. Immediate tasks, in priority order
### A. Backtest on the home-PC data (highest value; replaces weeks of paper trading)
Goal: confirm or kill the KXTEMPMIAH LIP strategy on months of history.
1. **Maker edge over months:** reproduce `code/ad_series_edge.py` / `code/aa1_tempmiah.py` logic on stored settled markets plus trades (maker P&L per contract to settlement: taker YES at P → P − y; taker NO → y − P; cluster SEs by market). Check stability by month and by hour of day. Expected ≈ +0.5–1.2¢.
2. **Reward share:** if order-book snapshots are stored, score a hypothetical quote with `code/pm_toolkit.lip_side_share` per snapshot; otherwise use `code/lip_daily.py` pools × typical newcomer share (20–35%, W1/LIP).
3. **SMART pull rule:** with the stored index/temperature history, simulate pulling both sides of a strike when minutes_left ≤ 20 and |index − K| ≤ 1°F, and everything in the final 3 minutes. Measure fill losses avoided vs reward forgone. Tune the band and windows, keeping a hold-out period untouched (multiple-testing rules in CONTEXT §4).
4. **Decision rule:** proceed only if net (reward share + fill P&L) is positive in the hold-out months with t > 2.

### B. Fix and run the paper traders on the home machine
- `live/tempmiah_paper.py` (JOIN vs SMART) and `live/lip_paper.py` (multi-series). Both are read-only, `--report` for P&L.
- **Known issue:** in the cloud run the index read stayed at 82.04°F for over 7 minutes. Add a **staleness check**: use the newest point's timestamp `t`; if it's older than ~3 minutes, treat it as stale and pull quotes. Also confirm the code reads the newest complete point (`status == "normal"`, field `v`).

### C. Execution layer (build and test in Kalshi's **demo** environment only)
- Auth: API key ID plus RSA private key; sign the request path (no query string). Hosts: `https://external-api.kalshi.com/trade-api/v2` (prod), `https://external-api.demo.kalshi.co/trade-api/v2` (demo). WS: `wss://external-api-ws.kalshi.com/trade-api/ws/v2` (auth required even for public channels).
- Endpoints: Create Order V2, **Amend Order V2**, Batch Cancel V2, **Cancel All Orders**, **Order Groups** (auto-cancel when fills exceed N contracts in a rolling 15s; use as a kill switch), WS channels `orderbook_delta`, `trade`, `user_fills`, `user_orders`.
- Rate limits: token buckets (read and write separate; default 10 tokens/request). Advanced tier is a permanent grant once 1 of the last 100 orders came via API.
- State: positions per strike, inventory skew (T2), **per-hour exposure cap across strikes** (they're correlated), and reconciliation from `user_fills` after a restart.
- Risk: daily loss limit, max contracts per market/hour, auto-pull on stale data or WS disconnect.

### D. Go-live gate (user's explicit approval at each step; PLAYBOOK §4)
Demo trading for ~1 week → tiny production size with the user watching → scale only if live slippage is within 50% of the backtest.

## 3. Facts that cost hours to learn (don't relearn them)
- Kalshi `period_reward` is in **centi-cents** (1/10,000 $). Daily LIP totals must be pro-rated from **all** programs (active/upcoming/closed/paid_out); a snapshot of "active" misses rolling hourly programs (that mistake gave $129k/day instead of $290k).
- Kalshi batch candles `GET /markets/candlesticks?market_tickers=…` avoid rate limits, but keep 1-minute requests to ~4 markets × 36h per call or they come back empty.
- Public fills: `GET /markets/trades?ticker=&min_ts=&cursor=` (`taker_side`, `yes_price_dollars`, `count_fp`).
- Data traps that faked results (CONTEXT §0 item 6): look-ahead from close time, lagging Polymarket price history, Deribit bars stamped at the open, previous-evening daily stamps, sorting date strings, per-trader nulls, averaging over vigged buckets, snapshot totals, one-day markouts, substitute feeds. **Always mark to settlement over ≥ 2 weeks and cluster by market.**
- Never `pkill -f` a pattern that's in your own command line (it kills your shell).

## 4. Also in the folder
- The course: `course/quant-field-manual.html`, also a private claude.ai artifact, https://claude.ai/artifact/ES6edvaMg8TQbCbyozPg2T.
- Topic notes `notes/*.md` with raw outputs `*_out.txt`; scripts `code/*.py`; the reusable toolkit `code/pm_toolkit.py`.
- Live tools: `live/capture.py` (continuous data logger), `live/lip_paper.py`, `live/tempmiah_paper.py`.

## 5. Suggested first prompt for the new session
> Read quant/HANDOFF.md and follow it. My stored Kalshi data is at <PATH>. Start with task A (backtest the KXTEMPMIAH LIP strategy on the stored history) and report the maker edge by month, the reward share and the SMART pull-rule results before building anything that trades.
