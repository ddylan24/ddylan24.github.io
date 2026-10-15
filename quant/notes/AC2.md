# AC2: Are large takers informed? Maker P&L by fill size

**Data (`code/ac2_size.py`).** All settlement-marked public fills collected in Y1, AA1 and AB1: 7.4M fills, 719M contracts. Maker P&L per contract to settlement by fill size; market-clustered bootstrap SEs.

| group | 1–10 contracts | 10–100 | 100–1k | >1k |
|---|---|---|---|---|
| crypto 15m (BTC, ETH) | **+0.37 ± 0.06** (9.3M) | +0.16 ± 0.05 (92M) | +0.01 ± 0.03 (270M) | +0.00 ± 0.01 (324M) |
| temperature (hourly Miami + daily highs) | +1.41 ± 0.71 | +1.74 ± 0.73 | +1.04 ± 0.31 | +0.86 ± 0.35 |
| FX 15m | +0.35 ± 0.23 | +0.17 ± 0.25 | −0.35 ± 0.46 | +7.8 ± 6.7 (noisy) |
| rain | −0.64 ± 1.18 | −0.93 ± 0.77 | −0.46 ± 0.44 | +0.84 ± 0.77 |

## Interpretation
- **Crypto 15m has a clean size gradient.** Makers earn +0.37¢ per contract against small takers (t ≈ 6) and nothing against large ones. Small fills are retail betting; large fills are arbitrageurs and market makers trading on the spot BTC/ETH tick (cf. U2: Kalshi crypto reprices within a minute). It's the classic Glosten–Milgrom/Kyle picture: informed traders trade bigger.
- **Temperature makers profit at every size** (+0.9 to +1.7¢), slightly less against the largest takers. Weather flow is betting flow (AB1/AA1).
- FX and rain are too noisy at this sample size.
- **For an LP quoter:** quoting size is a lever. In crypto, small resting orders earn spread from retail, while large resting depth mostly trades against informed size. In weather, size matters less.
