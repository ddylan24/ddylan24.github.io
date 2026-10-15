"""AC2: are large takers informed? Maker P&L to settlement per contract by fill size, across all settlement-marked fills collected
(Y1: FX/crypto 15m; AA1: hourly temperature; AB1: daily highs + rain). Market-clustered bootstrap SE per (series group, size bucket)."""
import sys, numpy as np, pandas as pd
R = sys.argv[1]; out = []; rng = np.random.default_rng(2)
Y = pd.read_csv(f"{R}/data/y1/fills.csv.gz", usecols=['series', 'ticker', 'maker', 'n'])
A = pd.read_csv(f"{R}/data/aa1/fills.csv.gz"); A['maker'] = np.where(A.side == 'yes', A.p - A.y, A.y - A.p) * A.n; A['series'] = 'KXTEMPMIAH'
A = A.rename(columns={'t': 'ticker'})[['series', 'ticker', 'maker', 'n']]
B = pd.read_csv(f"{R}/data/ab1_fills.csv.gz", usecols=['series', 'ticker', 'maker', 'n'])
F = pd.concat([Y, A, B])
F['group'] = np.select([F.series.str.contains('USD'), F.series.isin(['KXBTC15M', 'KXETH15M']), F.series.str.contains('HIGH|TEMP'), F.series == 'KXRAIN'], ['FX 15m', 'crypto 15m', 'temperature', 'rain'], 'other')
F['size'] = pd.cut(F.n, [0, 10, 100, 1000, 1e9], labels=['1–10', '10–100', '100–1k', '>1k'])
out.append(f"{len(F):,} fills, {F.n.sum():,.0f} contracts")
out.append(f"{'group':<12}" + "".join(f"{s:>22}" for s in ['1–10', '10–100', '100–1k', '>1k']))
for gname, g in F.groupby('group'):
    cells = []
    for s in ['1–10', '10–100', '100–1k', '>1k']:
        h = g[g['size'] == s]
        if h.n.sum() < 1000: cells.append(f"{'—':>22}"); continue
        m = h.groupby('ticker').agg(p=('maker', 'sum'), n=('n', 'sum'))
        b = 100 * m.p.sum() / m.n.sum(); bs = [100 * m.p.values[i].sum() / m.n.values[i].sum() for i in (rng.integers(0, len(m), len(m)) for _ in range(300))]
        cells.append(f"{b:+6.2f} ± {np.std(bs):4.2f} ({h.n.sum()/1e6:4.1f}M)")
    out.append(f"{gname:<12}" + "".join(f"{c:>22}" for c in cells))
txt = "\n".join(out); print(txt); open(f"{R}/notes/ac2_out.txt", "w").write(txt)
