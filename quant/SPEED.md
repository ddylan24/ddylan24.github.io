# How to be fast enough on Kalshi (and where speed actually matters)

Written 2026-10-15 from Kalshi's API docs (docs.kalshi.com: rate limits, environments, WebSockets, FIX, order groups, live data) and the measurements in `notes/Z2.md`, `X1.md`, `AA1.md`.

## 1. What the research says about speed
- **Fills come from cancellations, not queues** (Z2). Visits to a price trade ~10 contracts while 1,000+ rest at the touch. When the price moves, the resting makers *cancel*. The maker who cancels last gets filled at a stale price. So the race is **time from "information changes" to "my quote is gone"**.
- **Not all markets are a race** (AA1/AB1/AC2).
  - In weather, takers are mostly betting flow, and makers profit even on late fills.
  - In 15-minute crypto, large takers are informed: makers earn nothing against trades over 1k.
  - Speed matters most where the underlying is a fast public price (crypto, FX, indices) and least where information arrives slowly and on a schedule (temperature).
- **Weather information has a built-in lag for everyone.**
  - Kalshi's settlement index (`GET /live_data/weather/{city}`, public, 1-minute, 0.01°F) blends high-frequency ASOS stations (Miami: KMIA, KFXE, KOPF, KPMP, KFLL).
  - Station readings arrive a **median 87 seconds after the minute ends** (p10 77s, p90 146s; measured 2026-10-15). Everyone sees the same index at about the same time, so you win on **reaction time to the index** and on **anticipating** it.

## 2. The stack, from "good enough" to "fastest"
| level | what | why |
|---|---|---|
| 0 (now) | Polling REST every 10–30s from a home PC (`live/tempmiah_paper.py`) | Fine for paper trading and for weather. Too slow for crypto/FX 15m. |
| 1 | **WebSocket** (`wss://external-api-ws.kalshi.com/trade-api/ws/v2`): `orderbook_delta`, `trade`, `ticker`, `user_fills`, `user_orders` | Event-driven book and fills, no polling delay. The connection **requires an API key** even for public channels. |
| 2 | **Run in AWS** (Kalshi offers AWS PrivateLink, so its API lives in AWS; test RTT from us-east-1 first) | Cuts the network round trip from tens of ms (home internet) to ~1–2 ms. A small EC2 instance is ~$20–70/month. |
| 3 | **Amend instead of cancel-and-replace** (`Amend Order V2`), **batch cancel**, **Cancel All Orders** | Fewer round trips per quote change. Cancel-all is the panic button. |
| 4 | **Order groups** (auto-cancel when fills exceed N contracts in a rolling 15s) | A server-side kill switch: if you're being picked off, the exchange pulls everything without waiting for your code. |
| 5 | **Higher API tier**: Advanced is a permanent grant once 1 of your last 100 orders came via API; then Expert/Premier… by volume. Premier Write = 1,200 tokens/s ≈ 120 orders/s with 3s bursts | When the index moves, every strike needs re-quoting at once. Budget limits how fast you can cancel 10–40 quotes. |
| 6 | **FIX API**; **PrivateLink** (Premier+); **VPC peering** for WebSockets (Prime+) | Institutional latency. Only worth it at scale. |

## 3. Faster *information* (the real edge)
- **Weather:** the index is a published, reproducible formula. `GET /live_data/weather/{city}/calibrations` gives station weights and weekly offsets, and `detailed=true` shows each station's raw reading and arrival time. If you get the *station* readings sooner than Kalshi's aggregator (e.g., a paid real-time feed from Synoptic Data, the provider named in older rules, or NOAA high-frequency ASOS), you can **compute the next index value before it's published** and re-quote first. That's the single biggest speed edge for KXTEMPMIAH. Verify the feed's timeliness before paying.
- **Crypto 15m:** Kalshi's WebSocket carries **CF Benchmarks 5 Hz** and Pyth feeds. Direct exchange WebSockets (Coinbase, Kraken) can be faster still. Re-price on every tick, and pull before the settlement averaging window.
- **FX/commodities 15m:** price off a live FX/futures feed. The settlement source must match exactly (Y3 showed a near-substitute feed is worse than useless).

## 4. Smart beats fast (cheaper, and where we start)
- **Pull before predictable information.** In temperature, new index values land ~87s after each minute, and the last minutes before the hour decide the market. The SMART policy in `tempmiah_paper.py` pulls a strike when the index is within 1°F of it in the last 20 minutes, and pulls everything in the final 3. The paper trial measures what that saves versus always joining.
- **Step back one tick in risky windows.** LIP credit only halves per tick (DF 0.5), while fill risk drops much more. That often beats cancelling outright.
- **Quote small where large takers are informed** (crypto, AC2). Size matters little in weather.
- **Skew by inventory** (T2) and cap total inventory per hour across strikes (they're correlated).

## 5. Concrete plan
1. **Now (cloud, read-only):** `tempmiah_paper.py` (JOIN vs SMART) and `lip_paper.py` running, with results in the session notes.
2. **Home PC / AWS (read-only):** run both continuously for 2–4 weeks. Add a WebSocket market-data client (needs a Kalshi API key: Settings → API keys, RSA key pair; test in the **demo** environment first).
3. **Decide:** if SMART's net (reward + fill P&L) is positive across ≥2 weeks with fills checked against real book data, move to **demo-environment live orders**, then tiny production size. **Only with the user's explicit go-ahead for each step** (PLAYBOOK §4), with order groups and hard loss limits in code.
4. **Scale speed only if the data says latency is the binding constraint:** compare SMART's fill losses at a 10s cycle vs a 1s WebSocket version. If faster cancels materially cut losses, then move to AWS, apply for a higher tier, and build the station-feed index predictor.
