"""Z2: passive fill probability vs queue position, from public trades (Y1 7-day fills).
A 'visit' = a maximal run of consecutive trades (same market) at the same YES price with the same taker side. If our order sits
behind A contracts at that level, it fills only when visit volume exceeds A (FIFO), and partially by (V − A).
Estimates P(V > A), E[(V − A)+], and how often price trades THROUGH the level (next visit at a worse price for the resting side),
which is when a one-tick-back order would also fill."""
import sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []
F = pd.read_csv(f"{R}/data/y1/fills.csv.gz", usecols=['series', 'ticker', 'ts', 'side', 'p', 'n'])
F = F[F.series.isin(['KXEURUSD15M', 'KXUSDJPY15M', 'KXBTC15M'])]
F['ts'] = pd.to_datetime(F.ts, utc=True, format='mixed'); F = F.sort_values(['ticker', 'ts'])
for ser, g in F.groupby('series'):
    key = (g.ticker != g.ticker.shift()) | (g.p != g.p.shift()) | (g.side != g.side.shift())
    g = g.assign(v=key.cumsum())
    V = g.groupby('v').agg(t=('ticker', 'first'), p=('p', 'first'), side=('side', 'first'), vol=('n', 'sum'), k=('n', 'size'))
    # trade-through: next visit in same market, same taker side, price worse for the passive side (taker sells YES at lower price / buys at higher)
    nxt = V.shift(-1)
    same = (nxt.t == V.t) & (nxt.side == V.side)
    through = same & (((V.side == 'no') & (nxt.p < V.p)) | ((V.side == 'yes') & (nxt.p > V.p)))
    out.append(f"{ser}: {len(V):,} visits; visit volume median {V.vol.median():,.0f}, mean {V.vol.mean():,.0f}, 90th pct {V.vol.quantile(.9):,.0f} contracts")
    out.append("  queue ahead A → P(fill)=P(V>A), expected fill E[(V−A)+] per visit: " + "; ".join(
        f"A={A}: {100*(V.vol > A).mean():.1f}%, {np.maximum(V.vol - A, 0).mean():,.0f}" for A in (0, 100, 500, 1000, 5000, 20000)))
    out.append(f"  price trades through to the next level after a visit: {100*through.mean():.1f}% of visits (≈ fill chance for an order one tick back, before re-quoting)")
txt = "\n".join(out); print(txt); open(f"{R}/notes/z2_out.txt", "w").write(txt)
